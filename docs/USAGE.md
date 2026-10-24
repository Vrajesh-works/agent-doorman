# Doorman usage guide

This guide walks through the full workflow: find out who is visiting,
decide what to do about it, give verified agents a fast lane, and
enforce the decision in real time. Everything runs offline with the
Python standard library only.

## Install

```bash
pip install agent-doorman
```

Or run from a checkout, no install needed:

```bash
python -m doorman.watch --help
```

## 1. Watch: who is visiting?

Analyse an access log in Common or Combined Log Format:

```bash
python -m doorman.watch --log /var/log/nginx/access.log \
  --vendors fixtures/vendor_ips.json --out reports/
```

This writes `reports/watch-report.md` (owner-friendly) and
`reports/watch-report.json` (machine-readable). Every request is
labelled `human`, `verified_agent`, `spoofed_agent`, or
`unknown_bot`, with a reason per label. A User-Agent claim is trusted
only when the client IP sits inside that vendor's published ranges.

Vendor data lives in a JSON file you own and version. Update it when
vendors publish new ranges; no code changes needed. The bundled
`fixtures/vendor_ips.json` uses TEST-NET ranges for demos only.

Options that matter:

- `--cost-per-gb` and `--cost-per-million-requests`: your real hosting
  prices, so cost estimates use your numbers instead of the examples.
- `--ip-mode`: `hash` (default, anonymized client IDs), `truncate`
  (network prefix), or `none` (raw IPs, only on your own machine with
  explicit consent).
- `--anomaly-threshold` and `--anomaly-window-minutes`: volume flags.

## 2. Guard: what should you do about it?

Turn classifications into recommended rules with evidence:

```bash
python -m doorman.guard generate --log /var/log/nginx/access.log \
  --vendors fixtures/vendor_ips.json --out reports/ \
  --robots-txt /var/www/html/robots.txt
```

Rules cover: block spoofed clients, rate-limit unidentified bots, and
protect sensitive paths (`/account`, `/admin`, `/login`, `/wp-admin`).
The robots.txt check flags whole-site blocks of major search crawlers.

Guard only recommends. Approve or reject each rule yourself:

```bash
python -m doorman.guard decide \
  --decisions-file reports/guard-decisions.json \
  --rule block-001 --decision approve --note "Confirmed spoof"
```

Re-generate the report with `--decisions-file` to see each rule's
status. Nothing changes on your site until you apply an approved rule
in your own firewall, CDN, or server config.

## 3. Welcome: give verified agents a fast lane

Serve data to verified agents only, with allowlisted fields, quotas,
and a bulk-export cap:

```bash
python -m doorman.welcome serve --data products.json \
  --vendors fixtures/vendor_ips.json \
  --agent-ua "ChatGPT-User/1.0" --agent-ip 203.0.113.10 \
  --resource products
```

The agent is verified the same way Watch verifies (UA claim plus IP
range). Spoofed, unknown, and human visitors are rejected before the
lane is touched. Fields outside the resource allowlist (cost, supplier,
internal notes) are stripped even when the source record has them.
Every request writes an audit entry.

## 4. Middleware: enforce in real time

Wrap any WSGI application:

```python
from doorman.middleware import DoormanMiddleware
from doorman.watch import load_vendors
from doorman.policy import load_policy

app = DoormanMiddleware(
    my_wsgi_app,
    vendors=load_vendors("vendor_ips.json"),
    policy=load_policy("policy.json"),
)
```

Spoofed agents get 403, unidentified bots over the cap get 429, and
verified agents pass through stamped with `X-Doorman-Label` and
`X-Doorman-Agent` headers. Per-purpose policy blocks or throttles by
(agent, purpose): training, search, or live fetch.

## 5. Web Bot Auth: verify signatures, not just IPs

When a crawler signs requests per the Web Bot Auth draft, verify the
Ed25519 signature instead of trusting IP ranges:

```python
from doorman.webauth import verify_bot_auth

verified, reason = verify_bot_auth(headers, message, resolve_key)
```

`resolve_key` maps a key id from the `Signature-Agent` header to 32
raw public key bytes. The caller builds the signed message per its
RFC 9421 base-string construction. The Ed25519 math is pure Python,
no dependencies, verified against OpenSSL-generated vectors.

## 6. Demo

Run the whole pipeline on the bundled synthetic fixture in one go:

```bash
python examples/demo.py
```

It runs Watch, Guard, and Welcome on the fixture and prints the
headline numbers. No real logs, no network, nothing leaves your machine.

## Privacy

Reports show anonymized client IDs by default. Raw IPs appear only
with `--ip-mode none` on your own machine. Never commit raw logs or
real visitor data. Fixtures in this repo are synthetic TEST-NET data.
