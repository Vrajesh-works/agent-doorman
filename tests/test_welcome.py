"""Tests for the Welcome lane: verified agents only, allowlisted fields,
quotas, bulk caps, and audit entries."""

from __future__ import annotations

import json
import os

import pytest

from doorman.welcome import AgentRequest, Lane, LaneRejected
from doorman.welcome.cli import main

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")

RECORDS = [
    {
        "id": "widget-a",
        "name": "Widget A",
        "price": 19.99,
        "description": "A widget",
        "url": "/products/widget-a",
        "cost": 12.5,
        "supplier": "Supplier X",
        "internal_notes": "Do not share",
    }
]

VERIFIED = AgentRequest(agent_name="ChatGPT-User", verified=True)
UNVERIFIED = AgentRequest(agent_name="ChatGPT-User", verified=False)


def test_verified_agent_gets_only_allowlisted_fields():
    lane = Lane()
    served = lane.serve(VERIFIED, "products", RECORDS)
    assert len(served) == 1
    assert set(served[0]) == {"id", "name", "price", "description", "url"}
    assert "cost" not in served[0]
    assert "supplier" not in served[0]
    assert "internal_notes" not in served[0]


def test_unverified_agent_rejected():
    lane = Lane()
    with pytest.raises(LaneRejected):
        lane.serve(UNVERIFIED, "products", RECORDS)
    assert lane.audit[-1].outcome == "rejected_unverified"
    assert lane.audit[-1].records_served == 0


def test_unknown_resource_rejected():
    lane = Lane()
    with pytest.raises(LaneRejected):
        lane.serve(VERIFIED, "secret-sauce", RECORDS)


def test_bulk_export_capped():
    lane = Lane(max_records_per_response=2)
    records = [dict(RECORDS[0], id=f"item-{i}") for i in range(10)]
    served = lane.serve(VERIFIED, "products", records)
    assert len(served) == 2


def test_quota_enforced():
    lane = Lane(max_requests_per_window=2)
    lane.serve(VERIFIED, "products", RECORDS)
    lane.serve(VERIFIED, "products", RECORDS)
    with pytest.raises(LaneRejected):
        lane.serve(VERIFIED, "products", RECORDS)


def test_audit_entry_per_request():
    lane = Lane()
    lane.serve(VERIFIED, "products", RECORDS)
    entry = lane.audit[-1]
    assert entry.agent_name == "ChatGPT-User"
    assert entry.resource == "products"
    assert entry.records_served == 1
    assert entry.outcome == "served"
    assert entry.timestamp


def test_cli_serves_verified_agent(tmp_path):
    code = main(
        [
            "serve",
            "--data",
            os.path.join(FIXTURES, "products.json"),
            "--vendors",
            os.path.join(FIXTURES, "vendor_ips.json"),
            "--agent-ua",
            "ChatGPT-User/1.0",
            "--agent-ip",
            "203.0.113.10",
            "--resource",
            "products",
        ]
    )
    assert code == 0


def test_cli_rejects_spoofed_agent():
    code = main(
        [
            "serve",
            "--data",
            os.path.join(FIXTURES, "products.json"),
            "--vendors",
            os.path.join(FIXTURES, "vendor_ips.json"),
            "--agent-ua",
            "ChatGPT-User/1.0",
            "--agent-ip",
            "203.0.113.200",
            "--resource",
            "products",
        ]
    )
    assert code == 1
