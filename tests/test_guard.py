"""Tests for Guard: rule generation, decisions, robots checker, CLI.

All tests are deterministic and offline, using the synthetic fixture.
"""

from __future__ import annotations

import json
import os

import pytest

from doorman.guard import (
    generate_rules,
    record_decision,
    save_decisions,
    load_decisions,
)
from doorman.guard.cli import main
from doorman.guard.robots import check_robots_txt
from doorman.watch import classify_all, load_vendors, parse_file

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def _classified():
    vendors = load_vendors(os.path.join(FIXTURES, "vendor_ips.json"))
    parsed = parse_file(os.path.join(FIXTURES, "access_small.log"))
    return classify_all(parsed.entries, vendors)


def test_spoofed_clients_get_block_rules():
    rules = generate_rules(_classified())
    blocks = [r for r in rules if r.kind == "block_ip"]
    assert len(blocks) == 3
    assert {r.evidence.claimed_agent for r in blocks} == {"ChatGPT-User", "ClaudeBot"}


def test_sensitive_path_gets_protect_rule():
    rules = generate_rules(_classified())
    protects = [r for r in rules if r.kind == "protect_path"]
    assert len(protects) == 1
    assert protects[0].target == "/admin"


def test_rule_ids_stable():
    first = generate_rules(_classified())
    second = generate_rules(_classified())
    assert [r.rule_id for r in first] == [r.rule_id for r in second]
    assert [r.rule_id for r in first] == [
        "block-001",
        "block-002",
        "block-003",
        "protect-001",
    ]


def test_ip_mode_none_exposes_raw_ip():
    rules = generate_rules(_classified(), ip_mode="none")
    targets = [r.target for r in rules]
    assert "203.0.113.200" in targets


def test_ip_mode_hash_hides_raw_ip():
    rules = generate_rules(_classified(), ip_mode="hash")
    targets = " ".join(r.target for r in rules)
    assert "203.0.113.200" not in targets


def test_decisions_roundtrip(tmp_path):
    decisions = record_decision({}, "block-001", "approve", note="Confirmed")
    decisions = record_decision(decisions, "protect-001", "reject")
    path = str(tmp_path / "decisions.json")
    save_decisions(path, decisions)
    loaded = load_decisions(path)
    assert loaded["block-001"].decision == "approve"
    assert loaded["protect-001"].decision == "reject"


def test_invalid_decision_rejected():
    with pytest.raises(ValueError):
        record_decision({}, "block-001", "maybe")


def test_robots_wildcard_block_flags_all_major_crawlers():
    findings = check_robots_txt("User-agent: *\nDisallow: /\n")
    assert len(findings) == 6
    assert "Googlebot" in {f.crawler for f in findings}


def test_robots_path_scoped_disallow_not_flagged():
    assert check_robots_txt("User-agent: Googlebot\nDisallow: /private\n") == []


def test_guard_cli_generate_and_decide(tmp_path):
    out = str(tmp_path)
    code = main(
        [
            "generate",
            "--log",
            os.path.join(FIXTURES, "access_small.log"),
            "--vendors",
            os.path.join(FIXTURES, "vendor_ips.json"),
            "--out",
            out,
        ]
    )
    assert code == 0
    with open(os.path.join(out, "guard-report.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    assert len(data["rules"]) == 4
    decisions_file = os.path.join(out, "guard-decisions.json")
    code = main(
        [
            "decide",
            "--decisions-file",
            decisions_file,
            "--rule",
            "block-001",
            "--decision",
            "approve",
        ]
    )
    assert code == 0
    loaded = load_decisions(decisions_file)
    assert loaded["block-001"].decision == "approve"
