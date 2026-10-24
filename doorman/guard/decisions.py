"""Owner decisions on Guard recommendations.

Every Guard recommendation requires an explicit owner decision, approve or
reject, recorded with a timestamp. Doorman never applies rules itself;
this file is the audit trail of what the owner chose, and when.

Decisions are stored as JSON: ``{rule_id: {decision, timestamp, note}}``.
Re-deciding a rule overwrites its previous record, so the file always
shows the owner's latest position per rule.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

APPROVE = "approve"
REJECT = "reject"
DECISIONS = (APPROVE, REJECT)


@dataclass(frozen=True)
class Decision:
    """One owner's recorded choice on one rule."""

    rule_id: str
    decision: str
    timestamp: str
    note: str = ""


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def record_decision(
    decisions: dict[str, Decision],
    rule_id: str,
    decision: str,
    note: str = "",
    timestamp: str | None = None,
) -> dict[str, Decision]:
    """Return a new decisions map with this rule's decision recorded."""
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}, got {decision!r}")
    updated = dict(decisions)
    updated[rule_id] = Decision(
        rule_id=rule_id,
        decision=decision,
        timestamp=timestamp or utc_now_iso(),
        note=note,
    )
    return updated


def decisions_to_dict(decisions: dict[str, Decision]) -> dict:
    """Serialise decisions to a JSON-ready dict, sorted by rule ID."""
    return {
        rule_id: {
            "decision": d.decision,
            "timestamp": d.timestamp,
            "note": d.note,
        }
        for rule_id, d in sorted(decisions.items())
    }


def decisions_from_dict(data: dict) -> dict[str, Decision]:
    """Parse a decisions dict; unknown or malformed entries are skipped."""
    parsed: dict[str, Decision] = {}
    if not isinstance(data, dict):
        return parsed
    for rule_id, record in data.items():
        if not isinstance(record, dict):
            continue
        decision = record.get("decision")
        timestamp = record.get("timestamp")
        if decision not in DECISIONS or not isinstance(timestamp, str):
            continue
        parsed[rule_id] = Decision(
            rule_id=rule_id,
            decision=decision,
            timestamp=timestamp,
            note=record.get("note", "") if isinstance(record.get("note", ""), str) else "",
        )
    return parsed


def load_decisions(path: str) -> dict[str, Decision]:
    """Load decisions from a JSON file; missing file means no decisions."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return decisions_from_dict(json.load(handle))


def save_decisions(path: str, decisions: dict[str, Decision]) -> None:
    """Write decisions to a JSON file, sorted by rule ID."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(decisions_to_dict(decisions), handle, indent=2, sort_keys=True)
        handle.write("\n")
