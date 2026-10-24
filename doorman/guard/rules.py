"""Guard rule generation.

Guard consumes classified requests and turns them into recommended
protection rules, each with the evidence behind it. Guard only
recommends: it never applies a rule itself. Owner decisions live in
:mod:`doorman.guard.decisions`.

Privacy rule: block rules name a client by its anonymized ID unless the
operator explicitly runs with ``--ip-mode none`` on their own machine,
in which case the raw IP is included so the rule is directly actionable.
Anonymized IDs are never reversed; the owner resolves them from their
own logs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from doorman.watch.aggregate import CostModel, anonymize_ip
from doorman.watch.classify import (
    HUMAN,
    SPOOFED_AGENT,
    UNKNOWN_BOT,
    ClassificationResult,
)

BLOCK_IP = "block_ip"
RATE_LIMIT = "rate_limit"
PROTECT_PATH = "protect_path"

RULE_KINDS = (BLOCK_IP, RATE_LIMIT, PROTECT_PATH)

# Paths that should never serve automated traffic. A non-human request
# here is evidence of probing, whatever label it carries.
SENSITIVE_PATHS = ("/account", "/admin", "/login", "/wp-admin", "/wp-login.php")


@dataclass(frozen=True)
class Evidence:
    """The facts behind a rule, so an owner can judge it."""

    requests: int
    bytes: int
    estimated_cost_usd: float
    example_paths: tuple[str, ...] = ()
    claimed_agent: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class Rule:
    """One recommended protection rule."""

    rule_id: str
    kind: str
    target: str
    action: str
    evidence: Evidence
    reason: str


def _cost(requests: int, size: int, model: CostModel) -> float:
    gb = size / (1024**3)
    return round(gb * model.cost_per_gb + (requests / 1_000_000) * model.cost_per_million_requests, 4)


def _top_paths(counter: Counter[str], limit: int = 3) -> tuple[str, ...]:
    return tuple(path for path, _ in counter.most_common(limit))


def _block_rules(
    classified: list[ClassificationResult],
    block_threshold: int,
    model: CostModel,
    ip_mode: str,
) -> list[Rule]:
    """One block rule per spoofed client at or above the threshold."""
    by_ip: dict[str, list[ClassificationResult]] = {}
    for result in classified:
        if result.label == SPOOFED_AGENT:
            by_ip.setdefault(result.entry.ip, []).append(result)
    rules: list[Rule] = []
    for ip in sorted(by_ip):
        group = by_ip[ip]
        if len(group) < block_threshold:
            continue
        agents = sorted({r.agent for r in group if r.agent})
        paths = Counter(r.entry.path for r in group)
        total_bytes = sum(r.entry.size for r in group)
        target = ip if ip_mode == "none" else anonymize_ip(ip, ip_mode)
        rules.append(
            Rule(
                rule_id="",
                kind=BLOCK_IP,
                target=target,
                action="Block all requests from this client",
                evidence=Evidence(
                    requests=len(group),
                    bytes=total_bytes,
                    estimated_cost_usd=_cost(len(group), total_bytes, model),
                    example_paths=_top_paths(paths),
                    claimed_agent=agents[0] if agents else None,
                    detail=(
                        f"Claimed to be {', '.join(agents) if agents else 'a known agent'} "
                        f"but the client IP failed vendor verification on "
                        f"{len(group)} request(s)"
                    ),
                ),
                reason=(
                    "Spoofed agent traffic: the User-Agent claimed a vendor "
                    "identity the IP could not prove"
                ),
            )
        )
    return rules


def _rate_limit_rules(
    classified: list[ClassificationResult],
    rate_limit_threshold: int,
    model: CostModel,
    ip_mode: str,
) -> list[Rule]:
    """One rate-limit rule per unknown-bot client at or above the threshold."""
    by_ip: dict[str, list[ClassificationResult]] = {}
    for result in classified:
        if result.label == UNKNOWN_BOT:
            by_ip.setdefault(result.entry.ip, []).append(result)
    rules: list[Rule] = []
    for ip in sorted(by_ip):
        group = by_ip[ip]
        if len(group) < rate_limit_threshold:
            continue
        paths = Counter(r.entry.path for r in group)
        total_bytes = sum(r.entry.size for r in group)
        target = ip if ip_mode == "none" else anonymize_ip(ip, ip_mode)
        rules.append(
            Rule(
                rule_id="",
                kind=RATE_LIMIT,
                target=target,
                action="Rate-limit this client to a low requests-per-minute cap",
                evidence=Evidence(
                    requests=len(group),
                    bytes=total_bytes,
                    estimated_cost_usd=_cost(len(group), total_bytes, model),
                    example_paths=_top_paths(paths),
                    claimed_agent=None,
                    detail=(
                        f"Unidentified bot made {len(group)} request(s); "
                        f"no vendor claim to verify"
                    ),
                ),
                reason=(
                    "Unidentified automated traffic at volume: throttle it "
                    "instead of blocking outright, so a mislabelled client "
                    "is slowed, not cut off"
                ),
            )
        )
    return rules


def _protect_path_rules(
    classified: list[ClassificationResult],
    model: CostModel,
) -> list[Rule]:
    """One protect rule per sensitive path hit by non-human traffic."""
    by_path: dict[str, list[ClassificationResult]] = {}
    for result in classified:
        if result.label != HUMAN and result.entry.path in SENSITIVE_PATHS:
            by_path.setdefault(result.entry.path, []).append(result)
    rules: list[Rule] = []
    for path in sorted(by_path):
        group = by_path[path]
        labels = sorted({r.label for r in group})
        total_bytes = sum(r.entry.size for r in group)
        rules.append(
            Rule(
                rule_id="",
                kind=PROTECT_PATH,
                target=path,
                action="Require human verification (login, CAPTCHA, or allowlist) on this path",
                evidence=Evidence(
                    requests=len(group),
                    bytes=total_bytes,
                    estimated_cost_usd=_cost(len(group), total_bytes, model),
                    example_paths=(path,),
                    claimed_agent=None,
                    detail=(
                        f"{len(group)} non-human request(s) hit this path "
                        f"with labels: {', '.join(labels)}"
                    ),
                ),
                reason=(
                    "Sensitive path probed by automated traffic: it should "
                    "never serve bots without a human check"
                ),
            )
        )
    return rules


def _assign_ids(rules: list[Rule]) -> list[Rule]:
    """Stable, deterministic rule IDs in sorted (kind, target) order."""
    ordered = sorted(rules, key=lambda r: (r.kind, r.target))
    counters: dict[str, int] = {}
    assigned: list[Rule] = []
    prefixes = {BLOCK_IP: "block", RATE_LIMIT: "ratelimit", PROTECT_PATH: "protect"}
    for rule in ordered:
        counters[rule.kind] = counters.get(rule.kind, 0) + 1
        assigned.append(
            Rule(
                rule_id=f"{prefixes[rule.kind]}-{counters[rule.kind]:03d}",
                kind=rule.kind,
                target=rule.target,
                action=rule.action,
                evidence=rule.evidence,
                reason=rule.reason,
            )
        )
    return assigned


def generate_rules(
    classified: list[ClassificationResult],
    block_threshold: int = 1,
    rate_limit_threshold: int = 100,
    cost_model: CostModel | None = None,
    ip_mode: str = "hash",
) -> list[Rule]:
    """Generate recommended rules from classified requests.

    A single spoofed request is already proof of impersonation, so the
    default block threshold is 1. Rate limiting defaults to 100 requests,
    matching Watch's anomaly threshold semantics. Rule IDs are stable:
    the same input and config always produce the same IDs.
    """
    model = cost_model or CostModel()
    rules: list[Rule] = []
    rules.extend(_block_rules(classified, block_threshold, model, ip_mode))
    rules.extend(_rate_limit_rules(classified, rate_limit_threshold, model, ip_mode))
    rules.extend(_protect_path_rules(classified, model))
    return _assign_ids(rules)
