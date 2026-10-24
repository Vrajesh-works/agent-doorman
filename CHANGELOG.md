# Changelog

## 0.3.0 (2026-10-24) - Hardening

- Real-time WSGI middleware: blocks spoofed agents, rate-limits
  unidentified bots, applies per-purpose policy, stamps verified
  requests with `X-Doorman-Label` and `X-Doorman-Agent`.
- Web Bot Auth: pure-Python Ed25519 signature verification (RFC 8032),
  no dependencies, tested against OpenSSL-generated vectors.
- Per-purpose policy engine: training, search, and live fetch get
  different rules per agent, first match wins, configurable default.
- Pip packaging via pyproject.toml (`pip install agent-doorman`).

## 0.2.0 (2026-10-24) - Guard and Welcome

- Guard: recommended rules with evidence (block spoofed clients,
  rate-limit unidentified bots, protect sensitive paths), owner
  approve/reject decisions with timestamps, robots.txt checker for
  accidental search-crawler blocks.
- Welcome: read-only lane for verified agents only, with allowlisted
  fields, quotas, bulk-export caps, and audit entries.
- Validation kit: pilot runbook and interview guide for proving the
  tool on real traffic.

## 0.1.0 (2026-10-24) - Watch

- Combined/Common Log Format parsing, vendor IP-range verification,
  4-way classification (human, verified agent, spoofed agent, unknown
  bot) with a reason per label, aggregation with cost estimates,
  Markdown and JSON reports, CLI.
- Synthetic fixtures on RFC 5737 TEST-NET ranges, deterministic
  offline tests.
