# Pilot runbook: prove Doorman on real traffic

This runbook turns a consenting company's exported access logs into a
Doorman result in under an hour. It is the Phase 2 validation step:
Watch and Guard were built on synthetic fixtures, and fixtures cannot
prove a real company feels the pain or will act on a recommendation.

## What to ask the pilot for

- **Logs:** 7-30 days of access logs in Common or Combined Log Format
  (Apache/Nginx default). One file, or one file per day.
- **Consent, in writing:** permission to analyse the logs, what may be
  quoted (aggregate numbers only, never raw lines or IPs), and a
  retention limit (default: delete the raw logs within 30 days).
- **Cost inputs (optional but valuable):** their hosting cost per GB and
  per million requests, or their monthly hosting bill, so cost estimates
  use their numbers instead of the example pricing.
- **robots.txt:** a copy of the live file, for the Guard robots check.
- **One contact:** the person who can approve or reject Guard rules.

## Privacy rules (non-negotiable)

- Run Doorman on the pilot's machine or on a machine they control when
  possible. Raw logs never leave their infrastructure unless they
  explicitly agree.
- Default `--ip-mode hash`: reports show anonymized client IDs, never
  raw IPs. Use `--ip-mode none` only on the pilot's own machine, only
  with their explicit consent, and only so block rules are actionable.
- Never commit, paste, or publish raw log lines, raw IPs, or anything
  that identifies a visitor. Quote aggregate numbers only.
- Delete raw logs at the end of the retention window, and confirm the
  deletion to the pilot.

## Steps

### 1. Run Watch

```bash
python -m doorman.watch \
  --log pilot-access.log \
  --vendors fixtures/vendor_ips.json \
  --out pilot-reports/ \
  --cost-per-gb <their number, or 0.09> \
  --cost-per-million-requests <their number, or 0.40>
```

Read `pilot-reports/watch-report.md` and record:

- Share of traffic by class: human, verified agent, spoofed agent,
  unknown bot.
- Spoofed share: how many requests claimed a vendor identity and failed
  verification, and which agents were impersonated.
- Cost per class and per agent, in their numbers where supplied.
- Top paths hit by non-human traffic, and any behaviour flags.

### 2. Run Guard

```bash
python -m doorman.guard generate \
  --log pilot-access.log \
  --vendors fixtures/vendor_ips.json \
  --out pilot-reports/ \
  --robots-txt pilot-robots.txt
```

Read `pilot-reports/guard-report.md` and record:

- How many block, rate-limit, and protect rules were recommended.
- Which robots.txt findings fired, if any.

### 3. Owner review (the decision that matters)

Walk the owner through the Watch report, then the Guard rules, one by
one. For each rule, record their decision with the CLI:

```bash
python -m doorman.guard decide \
  --decisions-file pilot-reports/guard-decisions.json \
  --rule block-001 --decision approve --note "Confirmed spoof, blocking"
```

Success criteria (from the PRD):

- The owner can answer "what share of my traffic is AI agents?" after
  reading the report, without help.
- The owner acts on at least one Guard recommendation.
- The owner agrees to a 2-week follow-up: re-run on fresh logs and
  check whether approved rules reduced the targeted traffic.

### 4. Report back (aggregate numbers only)

Write up, with no raw lines and no raw IPs:

- Traffic mix before and after (if a follow-up run happened).
- Cost attributed to spoofed and unknown traffic.
- Rules approved, rejected, and why (one line each).
- One quote from the owner, with permission, on whether the report
  changed a decision.

## What "good" looks like

- A spoofed share above zero surprises most owners; the number itself
  is the pitch.
- An owner approving even one rule proves the recommendation engine is
  trusted enough to act on.
- A follow-up run showing reduced spoofed traffic after approval is
  the strongest proof Doorman works, and the best material for the
  product page.

## What to do if the pilot shows nothing

- Zero spoofed traffic on a small, low-traffic site is a real result,
  not a failure. Record it, and check whether the site sits behind
  Cloudflare or a host bot filter that already strips this traffic.
- If the owner does not feel the pain unprompted, that is the PRD
  go/no-go signal: pause Welcome, re-scope to Watch-only, or pivot to
  the developer/agency buyer (P2), who runs this audit for clients.
