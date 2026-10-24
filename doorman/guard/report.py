"""Guard reports: Markdown for owners, JSON for machines.

Reports never claim a rule is applied. Every rule shows its decision
status: pending, approved, or rejected. A pending rule is a suggestion,
not an action.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from doorman.guard.decisions import Decision
from doorman.guard.robots import RobotsFinding
from doorman.guard.rules import Rule


@dataclass
class GuardReport:
    """Everything the reporters need; JSON-serialisable via ``to_dict``."""

    rules: list[Rule] = field(default_factory=list)
    decisions: dict[str, Decision] = field(default_factory=dict)
    robots_findings: list[RobotsFinding] = field(default_factory=list)
    ip_mode: str = "hash"
    fixture_label: str = ""

    def decision_status(self, rule_id: str) -> str:
        decision = self.decisions.get(rule_id)
        return decision.decision if decision else "pending"

    def to_dict(self) -> dict:
        return {
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "kind": rule.kind,
                    "target": rule.target,
                    "action": rule.action,
                    "reason": rule.reason,
                    "decision": self.decision_status(rule.rule_id),
                    "evidence": {
                        "requests": rule.evidence.requests,
                        "bytes": rule.evidence.bytes,
                        "estimated_cost_usd": rule.evidence.estimated_cost_usd,
                        "example_paths": list(rule.evidence.example_paths),
                        "claimed_agent": rule.evidence.claimed_agent,
                        "detail": rule.evidence.detail,
                    },
                }
                for rule in self.rules
            ],
            "robots_findings": [
                {
                    "crawler": f.crawler,
                    "rule": f.rule,
                    "detail": f.detail,
                }
                for f in self.robots_findings
            ],
            "ip_mode": self.ip_mode,
            "fixture_label": self.fixture_label,
        }


def to_json(report: GuardReport) -> str:
    """Serialise the report as sorted, indented JSON."""
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def to_markdown(report: GuardReport) -> str:
    """Render the report as an owner-friendly Markdown document."""
    lines: list[str] = []
    lines.append("# Doorman Guard: recommended protection rules")
    lines.append("")
    if report.fixture_label:
        lines.append(f"> Label: {report.fixture_label}")
        lines.append("")
    lines.append(
        "These are **recommendations, not actions**. Nothing changes on "
        "your site until you approve a rule, and Doorman never applies "
        "rules itself."
    )
    lines.append("")
    if report.ip_mode != "none":
        lines.append(
            "> Client IDs below are anonymized. Resolve one to an IP in "
            "your own logs before applying its rule, or re-run Guard with "
            "`--ip-mode none` on your own machine."
        )
        lines.append("")
    if not report.rules:
        lines.append("No rules recommended from this log.")
        lines.append("")
    else:
        lines.append(f"## Recommended rules ({len(report.rules)})")
        lines.append("")
        for rule in report.rules:
            status = report.decision_status(rule.rule_id)
            lines.append(f"### {rule.rule_id}: {rule.action}")
            lines.append("")
            lines.append(f"- **Type:** {rule.kind}")
            lines.append(f"- **Target:** `{rule.target}`")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **Why:** {rule.reason}")
            lines.append(
                f"- **Evidence:** {rule.evidence.requests} request(s), "
                f"{rule.evidence.bytes} bytes, "
                f"~${rule.evidence.estimated_cost_usd:.4f} estimated cost"
            )
            if rule.evidence.claimed_agent:
                lines.append(f"- **Claimed agent:** {rule.evidence.claimed_agent}")
            if rule.evidence.example_paths:
                lines.append(
                    "- **Example paths:** "
                    + ", ".join(f"`{p}`" for p in rule.evidence.example_paths)
                )
            lines.append(f"- **Detail:** {rule.evidence.detail}")
            lines.append("")
    if report.robots_findings:
        lines.append("## robots.txt warnings")
        lines.append("")
        lines.append(
            "These rules block major search crawlers. Check whether each "
            "one is intentional before you lose search traffic."
        )
        lines.append("")
        for finding in report.robots_findings:
            lines.append(f"- **{finding.crawler}**: `{finding.rule}` ({finding.detail})")
        lines.append("")
    return "\n".join(lines)
