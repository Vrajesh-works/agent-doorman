"""Real-time request middleware: enforce verified identity at the edge.

Watch analyses logs after the fact; this middleware acts during the
request. It wraps any WSGI application and, for each request:

- Classifies the visitor with Watch's verifier (IP ranges, never the
  User-Agent alone).
- Blocks spoofed agents outright (403).
- Rate-limits unidentified bots per IP (429 past the cap).
- Applies the per-purpose policy to verified agents (block or
  rate-limit per policy).
- Passes everything else through, stamped with ``X-Doorman-Label`` and
  ``X-Doorman-Agent`` headers so downstream code can see the verdict.

Standard library only. The in-memory rate limiter suits a single
process; multi-process deployments should replace it with shared
storage.
"""

from __future__ import annotations

import time
from collections import defaultdict

from doorman.policy import ALLOW, BLOCK, RATE_LIMIT, Policy
from doorman.watch.classify import (
    HUMAN,
    SPOOFED_AGENT,
    UNKNOWN_BOT,
    VERIFIED_AGENT,
    ClassificationResult,
    classify,
)
from doorman.watch.parser import LogEntry
from doorman.watch.verify import VendorData


def _synthetic_entry(ip: str, user_agent: str) -> LogEntry:
    """A LogEntry carrying only what classification reads: IP and UA."""
    return LogEntry(
        line_no=0,
        ip=ip,
        time=None,
        method="GET",
        path="/",
        protocol="HTTP/1.1",
        status=200,
        size=0,
        referrer="",
        user_agent=user_agent,
        raw="",
    )


def decide(
    ip: str,
    user_agent: str,
    vendors: VendorData,
    policy: Policy | None = None,
) -> tuple[str, ClassificationResult]:
    """Decide an action for one request without running a server.

    Returns (action, classification) where action is one of ``allow``,
    ``block``, or ``rate_limit``. Rate limiting needs call state, so
    this pure function never returns ``rate_limit`` for unknown bots;
    the middleware applies the cap on top of this decision.
    """
    result = classify(_synthetic_entry(ip, user_agent), vendors)
    if result.label == SPOOFED_AGENT:
        return BLOCK, result
    if result.label == VERIFIED_AGENT and policy is not None:
        action = policy.evaluate(result.agent or "", None)
        if action in (BLOCK, RATE_LIMIT):
            return action, result
    return ALLOW, result


class DoormanMiddleware:
    """WSGI middleware enforcing verified-agent identity in real time."""

    def __init__(
        self,
        app,
        vendors: VendorData,
        policy: Policy | None = None,
        rate_limit_max: int = 100,
        rate_limit_window_seconds: int = 60,
    ):
        self.app = app
        self.vendors = vendors
        self.policy = policy
        self.rate_limit_max = rate_limit_max
        self.rate_limit_window_seconds = rate_limit_window_seconds
        self._counts: dict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))

    def _over_rate_limit(self, ip: str, now: float) -> bool:
        window_start, count = self._counts[ip]
        if now - window_start >= self.rate_limit_window_seconds:
            self._counts[ip] = (now, 1)
            return False
        if count >= self.rate_limit_max:
            return True
        self._counts[ip] = (window_start, count + 1)
        return False

    def __call__(self, environ, start_response):
        ip = environ.get("REMOTE_ADDR", "")
        user_agent = environ.get("HTTP_USER_AGENT", "")
        action, result = decide(ip, user_agent, self.vendors, self.policy)
        now = time.time()

        if action == BLOCK:
            status = "403 Forbidden"
            body = f"Blocked by Doorman: {result.reason}".encode("utf-8")
            headers = [
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(body))),
                ("X-Doorman-Label", result.label),
            ]
            start_response(status, headers)
            return [body]

        if result.label == UNKNOWN_BOT and self._over_rate_limit(ip, now):
            status = "429 Too Many Requests"
            body = b"Rate limited by Doorman: unidentified bot over cap"
            headers = [
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(body))),
                ("X-Doorman-Label", result.label),
            ]
            start_response(status, headers)
            return [body]

        if action == RATE_LIMIT and self._over_rate_limit(ip, now):
            status = "429 Too Many Requests"
            body = b"Rate limited by Doorman: policy rate limit"
            headers = [
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(body))),
                ("X-Doorman-Label", result.label),
            ]
            start_response(status, headers)
            return [body]

        def _start_response_with_headers(status, headers, exc_info=None):
            headers = list(headers) + [
                ("X-Doorman-Label", result.label),
                ("X-Doorman-Agent", result.agent or ""),
            ]
            return start_response(status, headers, exc_info)

        return self.app(environ, _start_response_with_headers)
