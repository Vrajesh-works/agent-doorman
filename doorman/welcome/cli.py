"""Command-line entry point for Doorman Welcome.

Serve a JSON data file through the lane for one verified agent::

    python -m doorman.welcome serve --data fixtures/products.json \\
        --vendors fixtures/vendor_ips.json \\
        --agent-ua "ChatGPT-User/1.0" --agent-ip 203.0.113.10 \\
        --resource products --limit 10

The agent is verified the same way Watch verifies: the User-Agent claim
must match a vendor, and the client IP must sit inside that vendor's
published ranges. Anything else is rejected before the lane is touched.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from doorman.watch.verify import identify_claim, load_vendors, verify_claim
from doorman.welcome.lane import AgentRequest, Lane, LaneRejected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doorman-welcome",
        description="Serve data through the verified-agent-only lane.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Serve a JSON data file through the lane")
    serve.add_argument("--data", required=True, help="JSON file holding a list of records")
    serve.add_argument("--vendors", required=True, help="Vendor identity JSON file")
    serve.add_argument("--agent-ua", required=True, help="Agent User-Agent string")
    serve.add_argument("--agent-ip", required=True, help="Agent client IP")
    serve.add_argument("--resource", required=True, help="Resource type, e.g. products")
    serve.add_argument("--limit", type=int, default=50, help="Max records to serve")
    serve.add_argument("--max-requests", type=int, default=100, help="Quota per window")
    return parser


def _cmd_serve(args: argparse.Namespace) -> int:
    vendors = load_vendors(args.vendors)
    claimed = identify_claim(args.agent_ua, vendors.vendors)
    if claimed is None:
        print(f"Rejected: no vendor claim in User-Agent {args.agent_ua!r}")
        return 1
    verified, reason = verify_claim(args.agent_ip, claimed)
    if not verified:
        print(f"Rejected: {reason}")
        return 1

    with open(args.data, encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list):
        print("Data file must hold a JSON list of records")
        return 1

    lane = Lane(
        max_requests_per_window=args.max_requests,
        max_records_per_response=args.limit,
    )
    try:
        served = lane.serve(
            AgentRequest(agent_name=claimed.agent_name, verified=True),
            args.resource,
            records,
        )
    except LaneRejected as exc:
        print(f"Rejected: {exc}")
        return 1
    print(json.dumps(served, indent=2))
    entry = lane.audit[-1]
    print(
        f"Served {entry.records_served} record(s) of {entry.records_requested} "
        f"to {entry.agent_name} via the {entry.resource} lane.",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        return _cmd_serve(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
