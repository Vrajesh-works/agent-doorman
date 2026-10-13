# PRD — Doorman v1

> The front desk for AI agents on small online stores.

| | |
|---|---|
| **Owner** | Vrajesh N |
| **Status** | Draft v0.1 — pre-validation (no customer interviews yet) |
| **Date** | 2026-10-13 |
| **Audience** | Engineering, design, leadership (course instructor / reviewers) |
| **Related** | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — research, threat model, sources |

**Decisions this PRD is built on:**
- **Segment:** small custom and WooCommerce stores
- **v1 delivery:** offline log analyzer + local MCP lane
- **Horizon:** semester capstone, then post-course continuation
- **Pilot owner:** none yet

---

## 1. Executive summary

**Problem.** Small online stores are visited more and more by AI agents and by scrapers *pretending* to be AI agents. Owners cannot tell the two apart, can't see what this traffic costs or does, and have no safe way to make their store easy for legitimate agents that could bring sales. Large platforms block agents outright. Small stores can't afford to, and mostly don't want to.

**Proposal.** Doorman is a Python tool that:
1. analyzes a store's access logs and separates **humans, verified agents, spoofed agents and unknown bots** (*Watch*);
2. recommends protective rules (*Guard*);
3. serves a **read-only, quota-limited MCP lane** of the public catalog to **verified** agents only (*Welcome*).

**v1 bet:** an owner who can *see* agent traffic clearly will act on it. Verification, not user-agent strings, should decide who gets privileged access.

**Status:** desk research and a Reddit scan (~530 relevant posts/comments) support the identity and visibility pain. They do **not** yet show that small store owners will adopt or pay. Validation is Phase 0 of the rollout.

## 2. Background

- **Agent traffic is growing fast from a small base.**
  - Agentic traffic is up ~7,851% year over year (HUMAN Security, 2026).
  - AI traffic is ≈1.7% of all traffic (DataDome, June 2026).
  - Only ~3% of agent activity reaches checkout. Most of it is product browsing and search (HUMAN, April 2026).
- **Large platforms are restricting agents.**
  - Amazon blocked Meta's Muse (Sept 2026) because it browsed without identifying itself.
  - Amazon v. Perplexity (Comet) remains in litigation on contract grounds.
- **The infrastructure is fragmented and early.**
  - Cloudflare offers free agent/crawler controls and a signed-agent program (Web Bot Auth, an IETF draft).
  - Few agents sign their requests yet.
  - Shopify and BigCommerce are building native agent channels, so this PRD targets stores **outside** those platforms.
- **Existing tools solve single pieces.**
  - Blocking: Cloudflare.
  - Analytics: Known Agents, formerly Dark Visitors.
  - Exposing stores to agents: BigCommerce Storefront MCP, Pomerado, WebMCP (draft).
  - None of them ties *verification* to *privileged access*.

## 3. Customer problem

### 3.1 Problem statement
> *"I run a small online store. Bots that say they're ChatGPT hit my site constantly. I can't tell which are real AI shoppers and which are scrapers. I don't know what they cost me or what they take. I'd like real AI assistants to recommend and sell my products, but I'm afraid that opening the door lets the fakes in too."*

*This is a composite built from the Reddit evidence. It is not a quote, and no owner has confirmed it yet.*

### 3.2 Evidence

| Problem | Evidence | Strength |
|---|---|---|
| Identity is spoofed | 394 IPs claimed to be ChatGPT, all fake (r/webdev). Grok fetched from 59 IPs disguised as Chrome (r/SEO). A store owner can't tell real shopping agents from bots farming stock or discount codes (r/ecommerce). | Strong |
| Cost and load | Meta's crawler made 11M requests in 30 days, billed by Vercel (r/webdev, score 3,236) | Strong (mostly content sites) |
| Stores want agent visibility and sales | ~85 GEO/AEO mentions. Owners push back on blanket blocking. | Strong |
| Analytics are polluted | Owners can't separate bot and human traffic in GA4/Clarity | Moderate |
| Owners want to approve outside agents' purchases | **None found** | Absent → excluded from v1 |

### 3.3 Problem gaps (not yet known)
- Whether small-store owners *notice* this pain without being prompted.
- Whether the owner or their **freelance developer/agency** is the real buyer.
- Willingness to pay. Free tools (Cloudflare, Clarity) set the bar.

### 3.4 Solution challenge
The PRD tests each part of the proposed solution against the problem:

| Component | Addresses the problem? | Challenge |
|---|---|---|
| **Watch** (classification + report) | ✅ Directly: identity, cost and analytics | Must beat free Cloudflare/Clarity on *clarity*, not only on data |
| **Guard** (rules) | ⚠️ Partially | In an **offline** v1, Guard can only *recommend* rules, not enforce them. Present it honestly as a recommendation engine. |
| **Welcome** (MCP lane) | ⚠️ **Unproven** | Owners want agent *sales*, but mainstream agents don't yet discover per-site MCP endpoints by default (WebMCP is in origin trial; NLWeb is early). Welcome may serve few real agents today. **v1 treats Welcome as an experiment measured by task success, not as a proven value driver.** |
| Approval gates for outside agents' checkout | ❌ No evidence | Out of scope. Revisit if interviews surface it. |

## 4. Goals

### 4.1 Goals (v1)
1. **G1 — Visibility:** an owner can see, in one report, how much traffic is human, verified agent, spoofed agent and unknown bot, plus what each costs.
2. **G2 — Trustworthy identity:** classification never relies on the user agent alone. Every label has a stated reason.
3. **G3 — Safe agent access:** verified agents can get structured catalog data that exposes **nothing beyond the public site**, within quotas.
4. **G4 — Evidence:** measure whether the structured lane improves agent task success versus HTML.
5. **G5 — Validation:** establish whether small-store owners have this problem (Phase 0).

### 4.2 Non-goals (v1)
- Real-time blocking or traffic enforcement
- Payments, checkout or order actions by agents
- ML-based bot detection
- Sales attribution
- Supporting Shopify or BigCommerce stores
- Any write access to the store

## 5. Success metrics

All targets are **proposed** and need review. Metrics are measured on labelled data, and every fixture is marked as one.

| Goal | Metric | Proposed target |
|---|---|---|
| G1 | Owner correctly answers "what share of my traffic is AI agents?" after reading the report | Pilot owner answers correctly without help |
| G2 | Spoof detection on a labelled fixture: share of known-spoofed requests labelled spoofed | ≥ 95% |
| G2 | False spoof rate: verified requests wrongly labelled spoofed | ≤ 1% |
| G2 | Classifications with a human-readable reason | 100% |
| G3 | VIP-lane responses containing data absent from the public HTML | 0 |
| G3 | Requests over quota that are served | 0 |
| G4 | Claude shopping-task success, MCP lane vs HTML (same tasks, same budget) | Report measured delta. No target until a baseline exists. |
| G4 | Median tool calls / tokens per successful task, MCP vs HTML | Report measured delta |
| G5 | Owners interviewed | ≥ 10 |
| G5 | Owners describing agent/bot pain **unprompted** | ≥ 3 of 10 (go/no-go signal) |
| G5 | Owners agreeing to a 2-week pilot | ≥ 1 |
| Post-pilot | Owner acts on ≥ 1 Doorman recommendation | Yes/No |

**Go/no-go:** if fewer than 3 of 10 owners describe the pain unprompted, pause Welcome. Re-scope to Watch-only, or pivot (see PROJECT_CONTEXT §9).

## 6. User personas

*These are hypotheses until Phase 0 interviews confirm or replace them.*

| Persona | Description | Needs | Technical skill |
|---|---|---|---|
| **P1 — Store owner ("Maya")** | Runs a 1–10 person WooCommerce or custom store | Know what bots cost and take; get found by AI assistants; not break the site | Low–medium |
| **P2 — Freelance developer/agency ("Dev")** | Maintains several small-store sites for clients | A tool to run on client logs, explain results to clients, and recommend rules | High. **Likely the real installer and buyer.** |
| **P3 — Agent operator (secondary)** | Builds or runs a legitimate shopping agent | Fast, structured, reliable product data; a clear way to be recognized as legitimate | High |

## 7. User stories

| ID | Persona | Story | Priority |
|---|---|---|---|
| US-1 | P1 | As a store owner, I want a plain-language weekly summary of who visited my store (humans vs AI agents vs fakes), so I know what's happening without reading logs. | P0 |
| US-2 | P1 | As a store owner, I want to see which bots cost me the most bandwidth and requests, so I can decide what to limit. | P0 |
| US-3 | P2 | As a developer, I want to run Doorman on an exported access log and get a repeatable report, so I can audit a client's site in minutes. | P0 |
| US-4 | P2 | As a developer, I want to know *why* a visitor was labelled spoofed, so I can defend the recommendation to my client. | P0 |
| US-5 | P1/P2 | As an owner, I want recommended protection rules I can approve or reject, so nothing changes without my decision. | P1 |
| US-6 | P3 | As an agent operator, I want a structured catalog endpoint for verified agents, so my agent finds the right product with fewer steps. | P1 |
| US-7 | P1 | As an owner, I want the agent lane to expose only what my public site already shows, so it can't be used to copy more than a human could see. | P0 (if Welcome ships) |
| US-8 | P1 | As an owner, I want to be told when my own settings block legitimate search crawlers like Googlebot, so I don't lose traffic by accident. | P2 |

## 8. Functional requirements

### Watch
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Parse access logs in Common/Combined Log Format (Apache/Nginx). Reject malformed lines with a count, not a crash. | P0 |
| FR-2 | Classify each request as `human`, `verified_agent`, `spoofed_agent`, `unknown_bot`. | P0 |
| FR-3 | Verify claimed agents against vendor-published IP ranges and/or reverse-then-forward DNS. A claimed agent that fails is `spoofed_agent`. | P0 |
| FR-4 | Attach a reason to every classification (e.g. "UA claims ChatGPT-User; IP not in OpenAI published ranges"). | P0 |
| FR-5 | Aggregate by class and agent: requests, bytes, top paths, time pattern, estimated cost from a user-supplied cost-per-GB/request. | P0 |
| FR-6 | Generate the report as Markdown and JSON. | P0 |
| FR-7 | Behaviour flags: per-client volume and rate anomalies (e.g. > N product pages in M minutes). Thresholds are configurable. | P1 |

### Guard (recommendations only in v1)
| ID | Requirement | Priority |
|---|---|---|
| FR-8 | Produce recommended rules (block spoofed IPs, rate-limit named crawlers, protect `/account`, `/admin`) with the evidence behind each. | P1 |
| FR-9 | Each recommendation requires an explicit owner decision (approve/reject), recorded with a timestamp. Doorman never applies rules itself in v1. | P1 |
| FR-10 | Check robots.txt and exported settings for rules that block major search crawlers. | P2 |

### Welcome (experimental)
| ID | Requirement | Priority |
|---|---|---|
| FR-11 | Read-only MCP server (stdio, JSON-RPC) exposing `search_products`, `get_product`, `check_stock` over a public catalog file. | P1 |
| FR-12 | Serve only clients marked verified. Unverified clients get a defined refusal. | P1 |
| FR-13 | Field allowlist: tools return only fields present on the public product page. | P0 (if Welcome ships) |
| FR-14 | Per-client quotas and pagination caps. No bulk-export tool. | P0 (if Welcome ships) |
| FR-15 | Detect instruction-like text in catalog content (prompt injection) and flag or neutralize it before serving. | P1 |

### Evaluation
| ID | Requirement | Priority |
|---|---|---|
| FR-16 | Eval harness: the same set of shopping tasks executed by Claude via (a) HTML pages and (b) the MCP lane, with identical turn and token budgets. Records success, tool calls and tokens. | P1 |
| FR-17 | Eval runs are opt-in, labelled live, and record model ID and date. Offline fixture runs are labelled fixtures. | P0 |

## 9. Non-functional requirements

| Category | Requirement |
|---|---|
| **Runtime** | Python 3, standard library first. Claude is the only model provider. Runs fully offline; live Claude calls only in the explicitly opt-in eval. |
| **Determinism** | Same input and config → identical report. Tests have no network access. |
| **Privacy** | IPs are personal data: hash or truncate them in reports by default. Configurable retention with a deletion command. No raw logs leave the owner's machine. |
| **Security** | MCP lane is read-only, allowlisted tools only, no filesystem access outside the catalog. Signed-request verification uses expiry + nonce when implemented. |
| **Explainability** | Every label and recommendation is traceable to rule + evidence. |
| **Performance** | *Proposed:* process a 1M-line log in < 5 minutes on a student laptop. To be benchmarked. |
| **Honesty** | Fixtures, simulations and unverified claims are labelled in output and docs. |
| **Testing** | ≥ 5 deterministic tests per module, including boundary cases: spoofed UA, malformed line, IPv6, quota edge, injection text. |
| **Portability** | Windows, macOS, Linux. No POSIX-only assumptions. |

## 10. Dependencies

| Dependency | Type | Status / risk |
|---|---|---|
| Vendor-published agent IP ranges and DNS conventions | External data | Coverage varies by vendor and changes. Must be versioned and dated. |
| Web Bot Auth (signed agents) | External standard | IETF draft, low adoption. Needs Ed25519. |
| `cryptography` package (Ed25519) | Library | **Needs instructor approval**. Otherwise signature checks are labelled simulated. |
| MCP specification (stdio JSON-RPC subset) | Protocol | Lesson 8 subset is not conformance-certified |
| Claude access (Claude Code; optional API for eval) | Model provider | NEU-provided Claude Code. API use is opt-in. |
| Pilot store owner with consent and log export | Customer | **Not yet secured — critical path** |
| Public catalog data for the pilot | Data | From pilot owner, or a labelled synthetic catalog |

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Small owners don't feel the pain | Medium | High | Phase 0 go/no-go; pivot options pre-identified |
| No pilot owner found | Medium | High | Recruit via student orgs, local Boston shops, freelance devs (P2). Fall back to labelled synthetic data and state it. |
| Welcome lane gets little real agent traffic (discovery gap) | High | Medium | Position as an experiment; measure task success, not adoption |
| Platforms bundle the features (Cloudflare, Shopify) | High | Medium | Focus on non-platform stores and the verification-to-access link |
| Verification can't cover unsigned agents | High | Medium | Keep `unknown` as an honest class; never over-claim |
| False spoof labels damage real agent traffic | Medium | High | v1 only recommends; owner approves; false-spoof metric ≤ 1% |
| IP data mishandled | Low | High | Hashing by default, retention limits, Lesson 14 review |
| VIP lane becomes a scraping surface | Medium | High | Field allowlist, quotas, no bulk export, behaviour flags |

## 12. Rollout plan

| Phase | When | Scope | Exit criteria |
|---|---|---|---|
| **0 — Validate** | Weeks of 2026-10-13 → early Nov | 10 owner/dev interviews; pitch film | Go/no-go per §5; ≥ 1 pilot consent |
| **1 — Build on fixtures** | Nov 2026 | Watch (FR-1–6), labelled synthetic logs, tests | Spoof and false-spoof targets met on fixtures |
| **2 — Welcome + eval** | Nov 2026 | FR-11–17; HTML vs MCP eval | Eval results recorded, labelled live/fixture |
| **3 — Pilot** | Late Nov → Week 15 | One consenting owner's exported logs + public catalog; Guard recommendations (FR-8–9) | Owner reviews report; decision recorded |
| **4 — Capstone handoff** | Week 15 (Dec 2026; date per Canvas) | Ten-artifact packet, final human decision (ship / narrow / defer / stop) | Packet complete; decision owned by the owner, not the packet |
| **5 — Post-course** | 2027+ | Open-source release; live middleware; Guard enforcement; signed-request verification; WordPress plugin as a separate non-course project; Agent Order Health | Based on pilot evidence |

## 13. Open questions

1. **Buyer:** is it the owner (P1) or the developer/agency (P2)? This changes the report's language and distribution.
2. **Pricing:** what is the willingness to pay against free Cloudflare/Clarity? Is there a free tier, an agency license, or open source only?
3. **Pilot:** which owner, which log format, and what retention terms will they consent to?
4. **Crypto:** is the `cryptography` package allowed for Ed25519 in the course? If not, are simulated signature checks acceptable?
5. **Welcome demand:** how will real agents discover the MCP lane in practice (WebMCP, `llms.txt`, `agent-permissions.json`)? Is any agent operator (P3) willing to test?
6. **Cost model:** which hosting cost inputs should we support (per-GB, per-request, serverless invocations)?
7. **Thresholds:** what behaviour thresholds separate a shopper from a scraper for a small catalog? These need pilot data.
8. **Policy format:** should Doorman read `agent-permissions.json` (arXiv 2601.02371) as its policy file from v1?
9. **Pitch film:** what runtime and format does the Canvas brief require?
10. **Governance:** who is the named incident contact and approver for the pilot (Lesson 14 register)?
