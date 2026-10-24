"""Tests for Watch: parser, verifier, classifier, aggregator, CLI.

All tests are deterministic and offline, using the synthetic fixture.
"""

from __future__ import annotations

import json
import os

from doorman.watch import (
    aggregate,
    classify_all,
    load_vendors,
    parse_file,
    parse_lines,
    to_json,
    to_markdown,
)
from doorman.watch.cli import main

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def _vendors():
    return load_vendors(os.path.join(FIXTURES, "vendor_ips.json"))


def _parsed():
    return parse_file(os.path.join(FIXTURES, "access_small.log"))


def test_parser_counts_entries_and_malformed():
    parsed = _parsed()
    assert len(parsed.entries) == 14
    assert parsed.malformed == 2
    assert parsed.malformed_lines == [15, 16]


def test_parser_handles_ipv6_and_dash_size():
    result = parse_lines(
        ['2001:db8::1 - - [14/Oct/2026:09:02:44 +0000] "GET /x HTTP/1.1" 200 - "-" "curl/1.0"']
    )
    assert len(result.entries) == 1
    assert result.entries[0].ip == "2001:db8::1"
    assert result.entries[0].size == 0


def test_vendor_ip_in_range():
    from doorman.watch.verify import ip_in_ranges

    assert ip_in_ranges("203.0.113.10", ("203.0.113.0/25",))
    assert not ip_in_ranges("203.0.113.200", ("203.0.113.0/25",))
    assert not ip_in_ranges("not-an-ip", ("203.0.113.0/25",))


def test_classification_matches_fixture_labels():
    vendors = _vendors()
    parsed = _parsed()
    classified = classify_all(parsed.entries, vendors)
    with open(os.path.join(FIXTURES, "access_labels.json"), encoding="utf-8") as handle:
        expected = json.load(handle)
    for result in classified:
        label = expected[str(result.entry.line_no)]
        assert result.label == label["label"], f"line {result.entry.line_no}"
        assert result.agent == label["agent"], f"line {result.entry.line_no}"


def test_every_classification_has_reason():
    vendors = _vendors()
    parsed = _parsed()
    for result in classify_all(parsed.entries, vendors):
        assert result.reason


def test_spoofed_never_trusted_on_user_agent_alone():
    vendors = _vendors()
    parsed = _parsed()
    spoofed = [c for c in classify_all(parsed.entries, vendors) if c.label == "spoofed_agent"]
    assert len(spoofed) == 3
    assert all(c.agent in ("ChatGPT-User", "ClaudeBot") for c in spoofed)


def test_aggregation_counts_by_class():
    vendors = _vendors()
    parsed = _parsed()
    report = aggregate(classify_all(parsed.entries, vendors), malformed=parsed.malformed)
    assert report.by_class["human"].requests == 4
    assert report.by_class["verified_agent"].requests == 5
    assert report.by_class["spoofed_agent"].requests == 3
    assert report.by_class["unknown_bot"].requests == 2
    assert report.total_requests == 14


def test_aggregation_is_deterministic():
    vendors = _vendors()
    parsed = _parsed()
    first = aggregate(classify_all(parsed.entries, vendors))
    second = aggregate(classify_all(parsed.entries, vendors))
    assert to_json(first) == to_json(second)


def test_markdown_and_json_reports():
    vendors = _vendors()
    parsed = _parsed()
    report = aggregate(classify_all(parsed.entries, vendors), malformed=parsed.malformed)
    md = to_markdown(report)
    assert "spoofed_agent" in md
    data = json.loads(to_json(report))
    assert data["total_requests"] == 14
    assert data["malformed_lines"] == 2


def test_cli_writes_reports(tmp_path):
    out = str(tmp_path)
    code = main(
        [
            "--log",
            os.path.join(FIXTURES, "access_small.log"),
            "--vendors",
            os.path.join(FIXTURES, "vendor_ips.json"),
            "--out",
            out,
            "--fixture-label",
            "synthetic fixture",
        ]
    )
    assert code == 0
    assert os.path.exists(os.path.join(out, "watch-report.md"))
    assert os.path.exists(os.path.join(out, "watch-report.json"))
