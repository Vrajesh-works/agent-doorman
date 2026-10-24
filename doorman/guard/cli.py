"""Command-line entry point for Doorman Guard.

Generate recommendations::

    python -m doorman.guard generate --log fixtures/access_small.log \\
        --vendors fixtures/vendor_ips.json --out reports/

Record an owner decision::

    python -m doorman.guard decide --decisions-file reports/guard-decisions.json \\
        --rule block-001 --decision approve --note "Confirmed spoof, blocking"

Guard only recommends. It never applies a rule itself.
"""

from __future__ import annotations

import argparse
import os
import sys

from doorman.guard import (
    GuardReport,
    generate_rules,
    load_decisions,
    record_decision,
    save_decisions,
    to_json,
    to_markdown,
)
from doorman.guard.robots import check_robots_file
from doorman.watch import classify_all, load_vendors, parse_file
from doorman.watch.aggregate import CostModel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doorman-guard",
        description="Recommend protection rules from classified log traffic. "
        "Guard only recommends; it never applies rules itself.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate recommended rules")
    gen.add_argument("--log", required=True, help="Access log in Combined Log Format")
    gen.add_argument("--vendors", required=True, help="Vendor identity JSON file")
    gen.add_argument("--out", default="reports", help="Output directory")
    gen.add_argument("--robots-txt", default="", help="Optional robots.txt file to check")
    gen.add_argument("--decisions-file", default="", help="Optional decisions file to show status")
    gen.add_argument("--cost-per-gb", type=float, default=0.09)
    gen.add_argument("--cost-per-million-requests", type=float, default=0.40)
    gen.add_argument(
        "--ip-mode",
        choices=("hash", "truncate", "none"),
        default="hash",
        help="IP privacy mode for rules (default: hash)",
    )
    gen.add_argument("--block-threshold", type=int, default=1)
    gen.add_argument("--rate-limit-threshold", type=int, default=100)
    gen.add_argument("--fixture-label", default="")

    dec = sub.add_parser("decide", help="Record an owner decision on a rule")
    dec.add_argument("--decisions-file", required=True, help="Decisions JSON file")
    dec.add_argument("--rule", required=True, help="Rule ID, e.g. block-001")
    dec.add_argument("--decision", required=True, choices=("approve", "reject"))
    dec.add_argument("--note", default="")
    return parser


def _cmd_generate(args: argparse.Namespace) -> int:
    vendors = load_vendors(args.vendors)
    parsed = parse_file(args.log)
    classified = classify_all(parsed.entries, vendors)
    rules = generate_rules(
        classified,
        block_threshold=args.block_threshold,
        rate_limit_threshold=args.rate_limit_threshold,
        cost_model=CostModel(
            cost_per_gb=args.cost_per_gb,
            cost_per_million_requests=args.cost_per_million_requests,
        ),
        ip_mode=args.ip_mode,
    )
    robots_findings = check_robots_file(args.robots_txt) if args.robots_txt else []
    decisions = load_decisions(args.decisions_file) if args.decisions_file else {}
    report = GuardReport(
        rules=rules,
        decisions=decisions,
        robots_findings=robots_findings,
        ip_mode=args.ip_mode,
        fixture_label=args.fixture_label,
    )

    os.makedirs(args.out, exist_ok=True)
    md_path = os.path.join(args.out, "guard-report.md")
    json_path = os.path.join(args.out, "guard-report.json")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(to_markdown(report))
    with open(json_path, "w", encoding="utf-8") as handle:
        handle.write(to_json(report))

    print(f"Classified {len(classified)} requests ({parsed.malformed} malformed skipped).")
    print(f"Recommended {len(rules)} rule(s).")
    if robots_findings:
        print(f"robots.txt warnings: {len(robots_findings)}.")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


def _cmd_decide(args: argparse.Namespace) -> int:
    decisions = load_decisions(args.decisions_file)
    decisions = record_decision(decisions, args.rule, args.decision, note=args.note)
    save_decisions(args.decisions_file, decisions)
    print(f"Recorded {args.decision} for {args.rule} in {args.decisions_file}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        return _cmd_generate(args)
    return _cmd_decide(args)


if __name__ == "__main__":
    sys.exit(main())
