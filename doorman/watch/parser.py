"""Parse access logs in Common / Combined Log Format.

Malformed lines are counted and reported, never fatal. IPv6 addresses
are supported. A ``-`` byte count is treated as 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

# Combined Log Format:
#   127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /a.gif HTTP/1.0" 200 2326
#       "http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"
# Common Log Format is the same without the last two quoted fields.
_COMBINED_RE = re.compile(
    r'(?P<ip>\S+) (?P<ident>\S+) (?P<user>\S+) '
    r'\[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) (?P<protocol>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\S+)'
    r'(?: "(?P<referrer>[^"]*)" "(?P<agent>[^"]*)")?'
)

_TIME_FORMATS = (
    "%d/%b/%Y:%H:%M:%S %z",
    "%d/%b/%Y:%H:%M:%S",
)


@dataclass(frozen=True)
class LogEntry:
    """One successfully parsed log line."""

    line_no: int
    ip: str
    time: datetime | None
    method: str
    path: str
    protocol: str
    status: int
    size: int
    referrer: str
    user_agent: str
    raw: str


@dataclass
class ParseResult:
    """Outcome of parsing a log source."""

    entries: list[LogEntry] = field(default_factory=list)
    malformed: int = 0
    malformed_lines: list[int] = field(default_factory=list)


def _parse_time(value: str) -> datetime | None:
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_line(line: str, line_no: int) -> LogEntry | None:
    """Parse one log line; return None when the line is malformed."""
    match = _COMBINED_RE.fullmatch(line.strip())
    if not match:
        return None
    parts = match.groupdict()
    try:
        status = int(parts["status"])
    except (TypeError, ValueError):
        return None
    size_raw = parts["size"]
    size = int(size_raw) if size_raw.isdigit() else 0
    return LogEntry(
        line_no=line_no,
        ip=parts["ip"],
        time=_parse_time(parts["time"]),
        method=parts["method"],
        path=parts["path"],
        protocol=parts["protocol"],
        status=status,
        size=size,
        referrer=parts["referrer"] or "",
        user_agent=parts["agent"] or "",
        raw=line.rstrip("\n"),
    )


def parse_lines(lines) -> ParseResult:
    """Parse an iterable of log lines."""
    result = ParseResult()
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        entry = parse_line(line, line_no)
        if entry is None:
            result.malformed += 1
            result.malformed_lines.append(line_no)
        else:
            result.entries.append(entry)
    return result


def parse_file(path: str, encoding: str = "utf-8") -> ParseResult:
    """Parse a log file on disk."""
    with open(path, encoding=encoding, errors="replace") as handle:
        return parse_lines(handle)
