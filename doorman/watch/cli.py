"""Command-line entry point for Doorman Watch.

Example::

    python -m doorman.watch --log fixtures/access_small.log \\
        --vendors fixtures/vendor_ips.json --out reports/ \\
        --cost-per-gb 0.09 --ip-mode hash
"""

from __future__ import annotations

import argparse
import os
import sys

from doorman.watch import (
    aggregate,
    classify_all,
    load_vendors,
    parse_file,
    to_json,
    to_markdown,
)
from doorman.watch.aggregate import CostModel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doorman-watch",
        description="Analyse access logs: separate humans, verified AI agents, "
        "spoofed agents and unknown bots.",
    )
    parser.add_argument("--log", required=True, help="Access log in Combined Log Format")
    parser.add_argument("--vendors", required=True, help="Vendor identity JSON file")
    parser.add_argument("--out", default="reports", help="Output directory")
    parser.add_argument("--cost-per-gb", type=float, default=0.09)
    parser.add_argument("--cost-per-million-requests", type=float, default=0.40)
    parser.add_argument(
        "--ip-mode",
        choices=("hash", "truncate", "none"),
        default="hash",
        help="IP privacy mode for reports (default: hash)",
    )
    parser.add_argument("--anomaly-threshold", type=int, default=100)
    parser.add_argument("--anomaly-window-minutes", type=int, default=10)
    parser.add_argument(
        "--fixture-label",
        default="",
        help="Label stamped on the report, e.g. 'synthetic fixture'",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    vendors = load_vendors(args.vendors)
    parsed = parse_file(args.log)
    classified = classify_all(parsed.entries, vendors)
    report = aggregate(
        classified,
        malformed=parsed.malformed,
        cost_model=CostModel(
            cost_per_gb=args.cost_per_gb,
            cost_per_million_requests=args.cost_per_million_requests,
        ),
        vendor_label=vendors.label,
        vendor_version=vendors.version,
        fixture_label=args.fixture_label,
        anomaly_window_minutes=args.anomaly_window_minutes,
        anomaly_threshold=args.anomaly_threshold,
        ip_mode=args.ip_mode,
    )

    os.makedirs(args.out, exist_ok=True)
    md_path = os.path.join(args.out, "watch-report.md")
    json_path = os.path.join(args.out, "watch-report.json")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(to_markdown(report))
    with open(json_path, "w", encoding="utf-8") as handle:
        handle.write(to_json(report))

    print(f"Parsed {len(parsed.entries)} requests "
          f"({parsed.malformed} malformed lines skipped).")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
