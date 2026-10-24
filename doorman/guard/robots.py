"""robots.txt checker.

Flags rules that block major search crawlers. A site that blocks Googlebot
or Bingbot by accident loses search traffic it never meant to give up.
This checker reads the declared policy only; it cannot see firewall or
server-level blocks.

Parsing follows the robots.txt convention: ``User-agent`` lines open a
group, ``Disallow``/``Allow`` lines belong to the current group, ``#``
starts a comment, and matching is case-insensitive. A group applies to a
crawler when its User-agent is ``*`` or names that crawler.
"""

from __future__ import annotations

from dataclasses import dataclass

# Major search crawlers whose accidental blocking costs real traffic.
MAJOR_SEARCH_CRAWLERS = (
    "Googlebot",
    "Bingbot",
    "Applebot",
    "DuckDuckBot",
    "Baiduspider",
    "YandexBot",
)


@dataclass(frozen=True)
class RobotsFinding:
    """One rule that blocks a major search crawler."""

    crawler: str
    rule: str
    detail: str


def _parse_groups(text: str) -> list[tuple[list[str], list[str]]]:
    """Split robots.txt into (user-agents, disallow-rules) groups.

    Consecutive User-agent lines belong to one group; a new group starts
    only when a User-agent line follows at least one rule. Rules before
    any User-agent line are ignored, per the convention.
    """
    groups: list[tuple[list[str], list[str]]] = []
    agents: list[str] = []
    disallows: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if disallows:
                groups.append((agents, disallows))
                agents, disallows = [], []
            agents.append(value.lower())
        elif key == "disallow" and agents:
            disallows.append(value)
    if agents or disallows:
        groups.append((agents, disallows))
    return groups


def check_robots_txt(text: str) -> list[RobotsFinding]:
    """Find rules blocking major search crawlers.

    A finding fires when a group applying to a major crawler disallows
    ``/`` (the whole site). Path-scoped disallows are not flagged:
    blocking a crawler from one directory is usually intentional.
    """
    findings: list[RobotsFinding] = []
    for agents, disallows in _parse_groups(text):
        for disallow in disallows:
            if disallow != "/":
                continue
            for crawler in MAJOR_SEARCH_CRAWLERS:
                lowered = crawler.lower()
                if "*" in agents or lowered in agents:
                    findings.append(
                        RobotsFinding(
                            crawler=crawler,
                            rule=f"Disallow: {disallow}",
                            detail=(
                                f"Group for '{', '.join(agents)}' disallows the "
                                f"whole site for {crawler}"
                            ),
                        )
                    )
    findings.sort(key=lambda f: (f.crawler, f.rule))
    return findings


def check_robots_file(path: str) -> list[RobotsFinding]:
    """Check a robots.txt file on disk."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return check_robots_txt(handle.read())
