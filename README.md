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
- **Welcome:** read-only MCP lane for verified agents only. Planned.

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

## Principles

- Python standard library only. No dependencies to install.
- Offline by default. Nothing leaves your machine.
- Deterministic: the same input and config always produce the
  identical report.
- Privacy first: reports show anonymized client IDs unless you
  explicitly pass `--ip-mode none` on your own machine.
- Fixtures and simulations are always labelled as synthetic. Never
  trust a User-Agent string alone.
