"""Per-purpose policy: training vs search vs live fetch are different bots.

One vendor runs several agents with different purposes. GPTBot trains
models; OAI-SearchBot answers search queries; ChatGPT-User fetches pages
for a live user. A company may want to block training crawls while
allowing search indexing, or vice versa. A policy file expresses that
per (agent, purpose) pair; the first matching rule wins, else the
default applies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

ALLOW = "allow"
BLOCK = "block"
RATE_LIMIT = "rate_limit"
ACTIONS = (ALLOW, BLOCK, RATE_LIMIT)

TRAINING = "training"
SEARCH = "search"
AGENT_FETCH = "agent-fetch"
PURPOSES = (TRAINING, SEARCH, AGENT_FETCH)

# Default purpose per known agent. Owners override via policy files.
DEFAULT_PURPOSES: dict[str, str] = {
    "GPTBot": TRAINING,
    "OAI-SearchBot": SEARCH,
    "ChatGPT-User": AGENT_FETCH,
    "ClaudeBot": TRAINING,
    "Claude-Web": SEARCH,
    "PerplexityBot": SEARCH,
    "Perplexity-User": AGENT_FETCH,
    "CCBot": TRAINING,
    "Google-Extended": TRAINING,
}


@dataclass(frozen=True)
class PolicyRule:
    """One rule: this agent, for this purpose, gets this action.

    Either field may be ``*`` to match everything.
    """

    agent: str
    purpose: str
    action: str


@dataclass
class Policy:
    """An ordered rule list plus a default action."""

    rules: list[PolicyRule] = field(default_factory=list)
    default: str = ALLOW
    purposes: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PURPOSES))

    def purpose_for(self, agent_name: str) -> str | None:
        """The purpose of a known agent, or None when unknown."""
        return self.purposes.get(agent_name)

    def evaluate(self, agent_name: str, purpose: str | None = None) -> str:
        """Decide an action for an agent and purpose.

        When purpose is None, the agent's default purpose is used;
        unknown agents with no purpose fall through to the default.
        """
        resolved = purpose or self.purpose_for(agent_name)
        for rule in self.rules:
            agent_match = rule.agent == "*" or rule.agent == agent_name
            purpose_match = rule.purpose == "*" or (
                resolved is not None and rule.purpose == resolved
            )
            if agent_match and purpose_match:
                return rule.action
        return self.default


def load_policy(path: str) -> Policy:
    """Load a policy JSON file.

    Format::

        {
          "default": "allow",
          "purposes": {"MyBot": "search"},
          "rules": [
            {"agent": "GPTBot", "purpose": "training", "action": "block"},
            {"agent": "*", "purpose": "search", "action": "allow"}
          ]
        }
    """
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    rules = []
    for entry in data.get("rules", []):
        action = entry.get("action", ALLOW)
        if action not in ACTIONS:
            continue
        rules.append(
            PolicyRule(
                agent=entry.get("agent", "*"),
                purpose=entry.get("purpose", "*"),
                action=action,
            )
        )
    default = data.get("default", ALLOW)
    if default not in ACTIONS:
        default = ALLOW
    purposes = dict(DEFAULT_PURPOSES)
    purposes.update(data.get("purposes", {}))
    return Policy(rules=rules, default=default, purposes=purposes)
