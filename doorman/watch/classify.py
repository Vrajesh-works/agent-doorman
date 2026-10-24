"""Request classification: human / verified_agent / spoofed_agent / unknown_bot.

Rules:

- A User-Agent that claims a known agent is **verified** only when the
  client IP sits inside that vendor's published ranges; otherwise it is
  **spoofed**. The User-Agent alone never verifies.
- A User-Agent matching generic bot/crawler patterns without a vendor
  claim is an **unknown_bot**.
- Everything else is **human**.

Every classification carries a human-readable reason so an owner or
developer can defend or dispute each label.
"""

from __future__ import annotations

from dataclasses import dataclass

from doorman.watch.parser import LogEntry
from doorman.watch.verify import VendorData, VendorIdentity, identify_claim, verify_claim

HUMAN = "human"
VERIFIED_AGENT = "verified_agent"
SPOOFED_AGENT = "spoofed_agent"
UNKNOWN_BOT = "unknown_bot"

LABELS = (HUMAN, VERIFIED_AGENT, SPOOFED_AGENT, UNKNOWN_BOT)

# Generic bot/crawler markers. A UA containing one of these, without a
# vendor claim, is an unknown bot rather than a human.
BOT_MARKERS = (
    "bot",
    "crawler",
    "spider",
    "scraper",
    "crawl",
    "archiver",
    "fetcher",
    "monitor",
    "slurp",
    "curl",
    "wget",
    "python-requests",
    "python-urllib",
)


@dataclass(frozen=True)
class ClassificationResult:
    """A log entry plus its label, agent and reason."""

    entry: LogEntry
    label: str
    agent: str | None
    reason: str


def _looks_like_bot(user_agent: str) -> bool:
    lowered = (user_agent or "").lower()
    return any(marker in lowered for marker in BOT_MARKERS)


def classify(entry: LogEntry, vendors: VendorData) -> ClassificationResult:
    """Classify one parsed log entry."""
    claimed: VendorIdentity | None = identify_claim(entry.user_agent, vendors.vendors)
    if claimed is not None:
        verified, reason = verify_claim(entry.ip, claimed)
        if verified:
            return ClassificationResult(entry, VERIFIED_AGENT, claimed.agent_name, reason)
        return ClassificationResult(entry, SPOOFED_AGENT, claimed.agent_name, reason)
    if _looks_like_bot(entry.user_agent):
        return ClassificationResult(
            entry,
            UNKNOWN_BOT,
            None,
            "User-Agent matches a generic bot/crawler pattern and claims no known vendor",
        )
    return ClassificationResult(
        entry,
        HUMAN,
        None,
        "User-Agent looks like a regular browser and claims no known agent",
    )


def classify_all(entries: list[LogEntry], vendors: VendorData) -> list[ClassificationResult]:
    """Classify every parsed entry, preserving input order."""
    return [classify(entry, vendors) for entry in entries]
