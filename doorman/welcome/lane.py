"""Welcome lane: a read-only fast lane for verified agents only.

Welcome never ships without Guard: only agents Watch classified as
``verified_agent`` may use the lane. Everyone else (human, spoofed,
unknown bot) is rejected outright. The lane is read-only: it serves
data, it never writes, and it never exports bulk data.

Three guarantees, enforced on every request:

- **Allowlisted fields only.** Each resource type declares exactly which
  fields an agent may see. Everything else (cost, supplier, internal
  notes, emails) is stripped, even if the source record contains it.
- **Quotas.** Each verified agent gets a bounded number of requests
  per window. Past the quota, the lane refuses until the window resets.
- **No bulk export.** Each response is capped at a maximum number of
  records, so the lane cannot be used to drain a catalogue.

Every served request produces an audit entry: who, what resource, how
many records, and when. Nothing is served without a trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class AgentRequest:
    """Who is asking, and whether Watch verified them."""

    agent_name: str
    verified: bool
    client_id: str = ""


@dataclass(frozen=True)
class AuditEntry:
    """One served (or refused) lane request, for the owner's records."""

    timestamp: str
    agent_name: str
    resource: str
    records_requested: int
    records_served: int
    outcome: str


class LaneRejected(Exception):
    """The lane refused a request: unverified agent, unknown resource, quota, or cap."""


# Default field allowlists per resource type. Add a resource type here
# only when the owner explicitly approves its fields.
DEFAULT_ALLOWLISTS: dict[str, frozenset[str]] = {
    "products": frozenset({"id", "name", "price", "description", "url"}),
    "articles": frozenset({"id", "title", "summary", "url", "published"}),
}


@dataclass
class Lane:
    """A read-only lane serving allowlisted fields to verified agents."""

    allowlists: dict[str, frozenset[str]] = field(
        default_factory=lambda: dict(DEFAULT_ALLOWLISTS)
    )
    max_requests_per_window: int = 100
    window_seconds: int = 3600
    max_records_per_response: int = 50
    _request_counts: dict[tuple[str, int], int] = field(default_factory=dict, repr=False)
    audit: list[AuditEntry] = field(default_factory=list, repr=False)

    def _window_key(self, agent_name: str, now: datetime) -> tuple[str, int]:
        epoch = int(now.timestamp())
        return (agent_name, epoch // self.window_seconds)

    def _check_quota(self, agent_name: str, now: datetime) -> None:
        key = self._window_key(agent_name, now)
        used = self._request_counts.get(key, 0)
        if used >= self.max_requests_per_window:
            raise LaneRejected(
                f"Quota exceeded for {agent_name}: "
                f"{used} requests in the current window "
                f"(limit {self.max_requests_per_window})"
            )
        self._request_counts[key] = used + 1

    def serve(
        self,
        agent: AgentRequest,
        resource: str,
        records: list[dict],
        now: datetime | None = None,
    ) -> list[dict]:
        """Serve records through the lane, filtered and capped.

        Raises LaneRejected for unverified agents, unknown resources,
        quota breaches, and anything that would leak non-allowlisted
        fields. Returns only allowlisted fields, at most
        ``max_records_per_response`` records.
        """
        moment = now or datetime.now(timezone.utc)
        timestamp = moment.isoformat()
        if not agent.verified:
            self.audit.append(
                AuditEntry(timestamp, agent.agent_name, resource, len(records), 0, "rejected_unverified")
            )
            raise LaneRejected(
                f"Agent {agent.agent_name} is not verified; "
                f"the lane serves verified agents only"
            )
        allowed = self.allowlists.get(resource)
        if allowed is None:
            self.audit.append(
                AuditEntry(timestamp, agent.agent_name, resource, len(records), 0, "rejected_unknown_resource")
            )
            raise LaneRejected(f"Unknown resource type: {resource!r}")
        self._check_quota(agent.agent_name, moment)
        served = [
            {key: value for key, value in record.items() if key in allowed}
            for record in records[: self.max_records_per_response]
        ]
        self.audit.append(
            AuditEntry(timestamp, agent.agent_name, resource, len(records), len(served), "served")
        )
        return served
