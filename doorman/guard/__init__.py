"""Doorman Guard: recommended protection rules, owner-approved.

Guard turns Watch classifications into recommended rules (block spoofed
clients, rate-limit unidentified bots, protect sensitive paths), checks
robots.txt for accidental search-crawler blocks, and records the owner's
explicit approve/reject decision on every rule with a timestamp. Guard
only recommends; it never applies a rule itself.

Standard library only. Fully offline and deterministic: the same input
and config always produce the identical report.
"""

from doorman.guard.decisions import (
    APPROVE,
    REJECT,
    Decision,
    load_decisions,
    record_decision,
    save_decisions,
)
from doorman.guard.report import GuardReport, to_json, to_markdown
from doorman.guard.robots import (
    MAJOR_SEARCH_CRAWLERS,
    RobotsFinding,
    check_robots_file,
    check_robots_txt,
)
from doorman.guard.rules import (
    BLOCK_IP,
    PROTECT_PATH,
    RATE_LIMIT,
    Evidence,
    Rule,
    generate_rules,
)

__all__ = [
    "APPROVE",
    "BLOCK_IP",
    "MAJOR_SEARCH_CRAWLERS",
    "PROTECT_PATH",
    "RATE_LIMIT",
    "REJECT",
    "Decision",
    "Evidence",
    "GuardReport",
    "RobotsFinding",
    "Rule",
    "check_robots_file",
    "check_robots_txt",
    "generate_rules",
    "load_decisions",
    "record_decision",
    "save_decisions",
    "to_json",
    "to_markdown",
]
