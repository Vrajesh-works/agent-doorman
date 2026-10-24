"""Aggregation: per-class and per-agent stats, cost estimates, behaviour flags.

Aggregation is deterministic: identical input and config always produce
the identical result.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from doorman.watch.classify import (
    HUMAN,
    LABELS,
    SPOOFED_AGENT,
    UNKNOWN_BOT,
    VERIFIED_AGENT,
    ClassificationResult,
)


@dataclass(frozen=True)
class CostModel:
    """User-supplied pricing. Defaults are labelled examples, not quotes."""

    label: str = "example-pricing"
    cost_per_gb: float = 0.09
    cost_per_million_requests: float = 0.40


@dataclass
class ClassStats:
    requests: int = 0
    bytes: int = 0

    @property
    def gb(self) -> float:
        return self.bytes / (1024**3)


@dataclass
class AgentStats:
    requests: int = 0
    bytes: int = 0
    top_paths: list[tuple[str, int]] = field(default_factory=list)


@dataclass(frozen=True)
class BehaviourFlag:
    """A volume/rate anomaly worth the owner's attention."""

    client: str
    label: str
    window_minutes: int
    requests: int
    threshold: int
    detail: str


@dataclass
class AggregateReport:
    """Everything the reporters need; JSON-serialisable via ``to_dict``."""

    total_requests: int = 0
    malformed: int = 0
    time_start: str = ""
    time_end: str = ""
    by_class: dict[str, ClassStats] = field(default_factory=dict)
    by_agent: dict[str, AgentStats] = field(default_factory=dict)
    top_paths: list[tuple[str, int]] = field(default_factory=list)
    hourly: list[int] = field(default_factory=lambda: [0] * 24)
    cost_by_class: dict[str, float] = field(default_factory=dict)
    total_cost: float = 0.0
    cost_model: CostModel = field(default_factory=CostModel)
    flags: list[BehaviourFlag] = field(default_factory=list)
    vendor_label: str = ""
    vendor_version: str = ""
    fixture_label: str = ""

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "malformed_lines": self.malformed,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "by_class": {
                label: {
                    "requests": stats.requests,
                    "bytes": stats.bytes,
                    "gb": round(stats.gb, 4),
                    "estimated_cost_usd": round(self.cost_by_class.get(label, 0.0), 4),
                }
                for label, stats in sorted(self.by_class.items())
            },
            "by_agent": {
                agent: {
                    "requests": stats.requests,
                    "bytes": stats.bytes,
                    "top_paths": [
                        {"path": path, "requests": count}
                        for path, count in stats.top_paths
                    ],
                }
                for agent, stats in sorted(self.by_agent.items())
            },
            "top_paths": [
                {"path": path, "requests": count} for path, count in self.top_paths
            ],
            "hourly_requests": self.hourly,
            "total_estimated_cost_usd": round(self.total_cost, 4),
            "cost_model": {
                "label": self.cost_model.label,
                "cost_per_gb": self.cost_model.cost_per_gb,
                "cost_per_million_requests": self.cost_model.cost_per_million_requests,
            },
            "behaviour_flags": [
                {
                    "client": flag.client,
                    "label": flag.label,
                    "window_minutes": flag.window_minutes,
                    "requests": flag.requests,
                    "threshold": flag.threshold,
                    "detail": flag.detail,
                }
                for flag in self.flags
            ],
            "vendor_data": {"label": self.vendor_label, "version": self.vendor_version},
            "fixture_label": self.fixture_label,
        }


def anonymize_ip(ip: str, mode: str = "hash") -> str:
    """Privacy default: never expose raw IPs in reports.

    Modes: ``hash`` (truncated SHA-256, stable per IP), ``truncate``
    (network prefix), ``none`` (raw, only with explicit owner consent).
    """
    if mode == "none":
        return ip
    if mode == "truncate":
        if ":" in ip:
            return ip.split(":")[0] + "::/32"
        parts = ip.split(".")
        return ".".join(parts[:3] + ["0"]) + "/24" if len(parts) == 4 else ip
    digest = hashlib.sha256(ip.encode("utf-8")).hexdigest()[:12]
    return f"client-{digest}"


def _estimate_cost(class_stats: dict[str, ClassStats], model: CostModel) -> tuple[dict[str, float], float]:
    by_class: dict[str, float] = {}
    total = 0.0
    for label, stats in class_stats.items():
        cost = stats.gb * model.cost_per_gb + (stats.requests / 1_000_000) * model.cost_per_million_requests
        by_class[label] = cost
        total += cost
    return by_class, total


def _detect_anomalies(
    classified: list[ClassificationResult],
    window_minutes: int = 10,
    threshold: int = 100,
    ip_mode: str = "hash",
) -> list[BehaviourFlag]:
    """Flag clients with abnormal volume inside a sliding window."""
    timed = [c for c in classified if c.entry.time is not None]
    timed.sort(key=lambda c: c.entry.time)
    by_client: dict[str, list[datetime]] = {}
    for result in timed:
        by_client.setdefault(result.entry.ip, []).append(result.entry.time)

    flags: list[BehaviourFlag] = []
    window = timedelta(minutes=window_minutes)
    for ip, times in sorted(by_client.items()):
        start = 0
        for end, moment in enumerate(times):
            while moment - times[start] > window:
                start += 1
            count = end - start + 1
            if count >= threshold:
                label = next(c.label for c in timed if c.entry.ip == ip)
                flags.append(
                    BehaviourFlag(
                        client=anonymize_ip(ip, ip_mode),
                        label=label,
                        window_minutes=window_minutes,
                        requests=count,
                        threshold=threshold,
                        detail=(
                            f"{count} requests in {window_minutes} minutes "
                            f"(threshold {threshold})"
                        ),
                    )
                )
                break
    return flags


def aggregate(
    classified: list[ClassificationResult],
    malformed: int = 0,
    cost_model: CostModel | None = None,
    vendor_label: str = "",
    vendor_version: str = "",
    fixture_label: str = "",
    anomaly_window_minutes: int = 10,
    anomaly_threshold: int = 100,
    ip_mode: str = "hash",
    top_n_paths: int = 10,
    top_n_agent_paths: int = 5,
) -> AggregateReport:
    """Aggregate classified requests into report-ready statistics."""
    model = cost_model or CostModel()
    report = AggregateReport(
        total_requests=len(classified),
        malformed=malformed,
        cost_model=model,
        vendor_label=vendor_label,
        vendor_version=vendor_version,
        fixture_label=fixture_label,
        by_class={label: ClassStats() for label in LABELS},
    )

    times = [c.entry.time for c in classified if c.entry.time is not None]
    if times:
        report.time_start = min(times).isoformat()
        report.time_end = max(times).isoformat()

    path_counter: Counter[str] = Counter()
    agent_paths: dict[str, Counter[str]] = {}
    for result in classified:
        stats = report.by_class[result.label]
        stats.requests += 1
        stats.bytes += result.entry.size
        path_counter[result.entry.path] += 1
        key = result.agent or result.label
        agent_entry = report.by_agent.setdefault(key, AgentStats())
        agent_entry.requests += 1
        agent_entry.bytes += result.entry.size
        agent_paths.setdefault(key, Counter())[result.entry.path] += 1
        if result.entry.time is not None:
            report.hourly[result.entry.time.hour] += 1

    report.top_paths = path_counter.most_common(top_n_paths)
    for agent, counter in agent_paths.items():
        report.by_agent[agent].top_paths = counter.most_common(top_n_agent_paths)

    report.cost_by_class, report.total_cost = _estimate_cost(report.by_class, model)
    report.flags = _detect_anomalies(
        classified,
        window_minutes=anomaly_window_minutes,
        threshold=anomaly_threshold,
        ip_mode=ip_mode,
    )
    return report
