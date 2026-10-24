# Interview guide: do owners feel the agent-traffic pain?

Goal: establish whether website owners (or the developers who maintain
their sites) feel the AI-agent and bot problem *without being prompted*,
who the real buyer is, and what they would pay or pilot. This is the
PRD Phase 0 validation. Target: 10 interviews. Go/no-go: at least 3 of
10 describe agent/bot pain unprompted.

## Rules for the interviewer

- Do not pitch Doorman first. Do not mention agents, bots, or Doorman
  until the discovery section is done. Leading questions invalidate
  the go/no-go signal.
- Record whether each pain was volunteered or prompted. That
  distinction is the data.
- 30 minutes max. Owners are busy; respect it.

## 1. Warm-up (5 min)

- What does the site sell or publish? How many people run it?
- Who maintains the site day to day: you, an employee, a freelancer,
  an agency?
- What hosting do you use, and roughly what does it cost per month?

## 2. Discovery: unprompted pain (10 min)

Ask open questions. Do not say "bots" or "AI agents" yet.

- What surprises have you had with the site in the last year?
- Have hosting bills, performance, or analytics ever behaved in a way
  you could not explain?
- What eats your time on the site that should not?

If they mention bots, crawlers, scrapers, AI, traffic spikes, or bills
on their own: that counts as unprompted. Follow up:

- When did you first notice it? What did you do about it?
- What did it cost you, in money, time, or lost sales?
- Is it still happening?

## 3. Prompted pain (10 min)

Only now name the problem. Keep each question concrete.

- AI crawlers (ChatGPT, Claude, Perplexity, Google) visit sites to
  train models and answer questions. Have you noticed them in your
  traffic or bills?
- Some bots pretend to be those AI crawlers. Have you ever suspected
  fake traffic, or found your content copied elsewhere?
- Do you trust your analytics numbers (sessions, conversion rate)? Do
  you know how much of your traffic is bots?
- Have you ever blocked bots and worried you blocked real visitors or
  search engines by accident?

## 4. Buyer and willingness (5 min)

- If a tool showed you exactly which visitors are real AI agents,
  which are fakes, and what each costs you, would that be useful?
  What would you do with it?
- Would you let a tool recommend blocking or throttling rules, if you
  approved each one first? Or would you want it to act on its own?
- Would you run a 2-week pilot on exported logs (no changes to your
  site, aggregate numbers only)? What would you need to agree?
- Who decides on tools like this: you, or your developer/agency?
- What would you pay, if anything, for a monthly report like this?
  (Do not anchor on a price. Let them answer, then probe: free?
  one-time? monthly?)

## 5. Close

- Can I send you a one-page summary of what we discussed, and follow
  up in two weeks?
- Is there another owner or developer you think I should talk to?

## Recording template (one per interview)

- Date, persona (owner P1 / developer-agency P2), site type, size.
- Pain volunteered unprompted? Yes/No, and the exact words.
- Pain after prompting? Yes/No, and which questions triggered it.
- Cost awareness: knows bot cost / suspects / unaware.
- Current defences: Cloudflare / robots.txt / nothing / other.
- Pilot agreed? Yes/No, and conditions.
- Willingness to pay: number or range, or "free only".
- Buyer: owner / developer / agency / unclear.
