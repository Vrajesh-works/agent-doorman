"""Vendor identity: published IP ranges and User-Agent claims.

A vendor claim is verified by IP range, never by the User-Agent string
alone. Vendor data is a JSON file the owner supplies and versions, so
ranges can be updated as vendors publish new ones without changing code.

Vendor JSON format::

    {
      "label": "example-vendors",
      "version": "2026-10-24",
      "vendors": [
        {
          "agent_name": "ChatGPT-User",
          "user_agent_patterns": ["ChatGPT-User"],
          "ipv4_ranges": ["203.0.113.0/25"],
          "ipv6_ranges": []
        }
      ]
    }
"""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class VendorIdentity:
    """One vendor's published identity: name, UA markers, IP ranges."""

    agent_name: str
    user_agent_patterns: tuple[str, ...] = ()
    ipv4_ranges: tuple[str, ...] = ()
    ipv6_ranges: tuple[str, ...] = ()


@dataclass
class VendorData:
    """A loaded vendor file, with its label and version."""

    label: str = ""
    version: str = ""
    vendors: list[VendorIdentity] = field(default_factory=list)


def load_vendors(path: str) -> VendorData:
    """Load a vendor identity JSON file."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    vendors = [
        VendorIdentity(
            agent_name=v["agent_name"],
            user_agent_patterns=tuple(v.get("user_agent_patterns", [])),
            ipv4_ranges=tuple(v.get("ipv4_ranges", [])),
            ipv6_ranges=tuple(v.get("ipv6_ranges", [])),
        )
        for v in data.get("vendors", [])
    ]
    return VendorData(
        label=data.get("label", ""),
        version=data.get("version", ""),
        vendors=vendors,
    )


def ip_in_ranges(ip: str, ranges: tuple[str, ...]) -> bool:
    """True when the IP falls inside any of the CIDR ranges."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for network in ranges:
        try:
            if address in ipaddress.ip_network(network, strict=False):
                return True
        except ValueError:
            continue
    return False


def identify_claim(user_agent: str, vendors: list[VendorIdentity]) -> VendorIdentity | None:
    """Find the vendor whose UA pattern appears in this User-Agent."""
    lowered = (user_agent or "").lower()
    for vendor in vendors:
        for pattern in vendor.user_agent_patterns:
            if pattern.lower() in lowered:
                return vendor
    return None


def verify_claim(ip: str, vendor: VendorIdentity) -> tuple[bool, str]:
    """Verify a claimed vendor identity against published IP ranges.

    Returns (verified, reason). The User-Agent alone never verifies.
    """
    ranges = vendor.ipv4_ranges + vendor.ipv6_ranges
    if ip_in_ranges(ip, ranges):
        return True, (
            f"Client IP {ip} is inside {vendor.agent_name}'s published ranges"
        )
    return False, (
        f"Client IP {ip} is NOT inside {vendor.agent_name}'s published "
        f"ranges; the User-Agent claim is unverified"
    )
