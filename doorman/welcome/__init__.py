"""Doorman Welcome: a read-only lane for verified agents only.

Welcome serves allowlisted fields to agents Watch verified, under quota
and bulk-export caps, with an audit entry per request. It never serves
unverified agents, never writes, and never exports bulk data.

Standard library only. Fully offline.
"""

from doorman.welcome.lane import (
    AgentRequest,
    AuditEntry,
    Lane,
    LaneRejected,
    DEFAULT_ALLOWLISTS,
)

__all__ = [
    "AgentRequest",
    "AuditEntry",
    "DEFAULT_ALLOWLISTS",
    "Lane",
    "LaneRejected",
]
