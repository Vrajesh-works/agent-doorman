# Doorman

> The front desk for AI agents on small websites.
> See every AI agent, stop the fakes, and give the real ones a fast, safe lane.

**Status:** pre-validation. Docs only; no implementation yet.

Doorman analyzes a small store's access logs to separate humans, verified AI
agents, spoofed agents and unknown bots (**Watch**), recommends protective
rules (**Guard**), and serves a read-only, quota-limited MCP lane of the public
catalog to verified agents only (**Welcome**).

## Docs

- [Project context](docs/PROJECT_CONTEXT.md): problem, evidence, threat model, sources
- [PRD](docs/PRD.md): goals, metrics, requirements, rollout

## Layout

```text
doorman/    Python package (watch, guard, welcome)
tests/      deterministic, offline tests
fixtures/   labelled synthetic logs and catalog (never real traffic)
docs/       project context and PRD
```

## Principles

- Python standard library first; Claude is the only model provider.
- Runs offline by default; live Claude calls only in an opt-in, labelled eval.
- Fixtures, simulations and unverified claims are always labelled.
- No raw logs or personal data are committed.

Built as the INFO 7375 (Northeastern, Fall 2026) capstone by Vrajesh N.
