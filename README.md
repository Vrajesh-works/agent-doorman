# agent-doorman

The front desk for AI agents on small websites. It answers one question
from your access logs: which visitors are real AI agents, which are
fakes, and what is each one costing you.

## Modes

- **Watch:** analyse access logs and classify every request as `human`,
  `verified_agent`, `spoofed_agent`, or `unknown_bot`. A User-Agent
  claim is trusted only when the client IP sits inside that vendor's
  published ranges. Reports include per-class and per-agent stats and
  cost estimates.
- **Guard:** turn classifications into recommended protection rules
  (block spoofed clients, rate-limit unidentified bots, protect
  sensitive paths), each with the evidence behind it. Guard only
  recommends; the owner approves or rejects each rule, and Doorman
  never applies rules itself.
- **Welcome:** read-only lane for verified agents only, with allowlisted fields, quotas, bulk-export caps, and an audit entry per request. Spoofed and unknown agents are rejected before the lane is touched.
- **Hardening:** real-time WSGI middleware that blocks spoofed agents, rate-limits unidentified bots, and applies per-purpose policy (training vs search vs live fetch are different rules, even from one vendor). Web Bot Auth Ed25519 signature verification in pure Python, no dependencies. Pip-installable packaging via pyproject.toml.

## Quickstart

```bash
python -m doorman.watch --log fixtures/access_small.log \
  --vendors fixtures/vendor_ips.json --out reports/

python -m doorman.guard generate --log fixtures/access_small.log \
  --vendors fixtures/vendor_ips.json --out reports/
```

## Run the tests

```bash
python -m pytest tests/ -v
```

## Demo and docs

```bash
python examples/demo.py
```

Full usage guide: `docs/USAGE.md`. Release history: `CHANGELOG.md`.

## Principles

- Python standard library only. No dependencies to install.
- Offline by default. Nothing leaves your machine.
- Deterministic: the same input and config always produce the
  identical report.
- Privacy first: reports show anonymized client IDs unless you
  explicitly pass `--ip-mode none` on your own machine.
- Fixtures and simulations are always labelled as synthetic. Never
  trust a User-Agent string alone.
