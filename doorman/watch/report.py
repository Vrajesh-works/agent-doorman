"""Watch reports: Markdown for owners, JSON for machines."""

from __future__ import annotations

import json

from doorman.watch.aggregate import AggregateReport


def to_json(report: AggregateReport) -> str:
    """Serialise the report as sorted, indented JSON."""
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def to_markdown(report: AggregateReport) -> str:
    """Render the report as an owner-friendly Markdown document."""
    lines: list[str] = []
    lines.append("# Doorman Watch: who is visiting your site?")
    lines.append("")
    if report.fixture_label:
        lines.append(f"> Label: {report.fixture_label}")
        lines.append("")
    lines.append(f"**{report.total_requests} requests analysed**")
    if report.malformed:
        lines.append(f"({report.malformed} malformed lines skipped)")
    if report.time_start:
        lines.append(f"from {report.time_start} to {report.time_end}")
    lines.append("")
    lines.append("## Traffic by class")
    lines.append("")
    lines.append("| Class | Requests | Bytes | Estimated cost (USD) |")
    lines.append("| --- | ---: | ---: | ---: |")
    for label, stats in sorted(report.by_class.items()):
        cost = report.cost_by_class.get(label, 0.0)
        lines.append(f"| {label} | {stats.requests} | {stats.bytes} | {cost:.4f} |")
    lines.append("")
    lines.append(f"**Total estimated cost: ${report.total_cost:.4f}**")
    lines.append(f"(pricing model: {report.cost_model.label})")
    lines.append("")
    if report.by_agent:
        lines.append("## Traffic by agent")
        lines.append("")
        for agent, stats in sorted(report.by_agent.items()):
            lines.append(f"- **{agent}**: {stats.requests} requests, {stats.bytes} bytes")
            for path, count in stats.top_paths:
                lines.append(f"  - `{path}` ({count})")
        lines.append("")
    if report.top_paths:
        lines.append("## Top paths")
        lines.append("")
        for path, count in report.top_paths:
            lines.append(f"- `{path}` ({count})")
        lines.append("")
    if report.flags:
        lines.append("## Behaviour flags")
        lines.append("")
        for flag in report.flags:
            lines.append(
                f"- {flag.client} ({flag.label}): {flag.detail}"
            )
        lines.append("")
    return "\n".join(lines)
