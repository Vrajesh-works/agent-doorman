"""One-command demo: Watch, Guard, and Welcome on the synthetic fixture.

No real logs, no network, nothing leaves your machine. Run:

    python examples/demo.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from doorman.guard import generate_rules
from doorman.watch import aggregate, classify_all, load_vendors, parse_file
from doorman.welcome import AgentRequest, Lane

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
FIXTURES = os.path.join(ROOT, "fixtures")


def main() -> int:
    vendors = load_vendors(os.path.join(FIXTURES, "vendor_ips.json"))
    parsed = parse_file(os.path.join(FIXTURES, "access_small.log"))
    classified = classify_all(parsed.entries, vendors)
    report = aggregate(classified, malformed=parsed.malformed)

    print("Doorman demo: synthetic fixture")
    print(f"  Parsed {len(parsed.entries)} requests ({parsed.malformed} malformed skipped)")
    for label in ("human", "verified_agent", "spoofed_agent", "unknown_bot"):
        stats = report.by_class[label]
        print(f"  {label}: {stats.requests} requests, {stats.bytes} bytes")

    rules = generate_rules(classified)
    print(f"\nGuard recommended {len(rules)} rule(s):")
    for rule in rules:
        print(f"  {rule.rule_id}: {rule.action} -> {rule.target}")

    import json

    with open(os.path.join(FIXTURES, "products.json"), encoding="utf-8") as handle:
        products = json.load(handle)
    lane = Lane()
    served = lane.serve(
        AgentRequest(agent_name="ChatGPT-User", verified=True),
        "products",
        products,
    )
    print(f"\nWelcome served {len(served)} product(s) to verified ChatGPT-User:")
    for item in served:
        print(f"  {item['id']}: {item['name']} at ${item['price']} (cost field stripped: {'cost' not in item})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
