"""Doorman Watch: offline access-log analysis for small websites.

Parses Common/Combined Log Format access logs, classifies each request as
``human``, ``verified_agent``, ``spoofed_agent`` or ``unknown_bot`` (never
trusting the User-Agent alone), aggregates cost and behaviour statistics,
and renders an owner-friendly Markdown report plus a machine-readable JSON
report.

Standard library only. Fully offline and deterministic: the same input and
config always produce the identical report.
"""

from doorman.watch.aggregate import aggregate, AggregateReport
from doorman.watch.classify import ClassificationResult, classify, classify_all
from doorman.watch.parser import LogEntry, ParseResult, parse_file, parse_lines
from doorman.watch.report import to_json, to_markdown
from doorman.watch.verify import VendorIdentity, identify_claim, ip_in_ranges, load_vendors

__all__ = [
    "AggregateReport",
    "ClassificationResult",
    "LogEntry",
    "ParseResult",
    "VendorIdentity",
    "aggregate",
    "classify",
    "classify_all",
    "identify_claim",
    "ip_in_ranges",
    "load_vendors",
    "parse_file",
    "parse_lines",
    "to_json",
    "to_markdown",
]
