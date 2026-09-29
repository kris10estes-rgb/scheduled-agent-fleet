# Scheduled Agent Fleet

Scheduled AI agents read the tools, apply priority logic, and draft leadership-ready status before anyone logs on. This repo is the standard they run on, the priority logic as code, and the eval harness proving two rules hold on every run: every claim cites a source, and nothing sends without a human.

Built by Kristen Estes, a Director of Content Operations with 20 years in creative and content ops and a PMP, as a public proof-of-work for senior AI Product and AI Operations roles. [LinkedIn](https://www.linkedin.com/in/kris10estes)

**For AI enablement teams:** the spec standard is how a team adopts agents safely. Anyone can read an agent's contract, and the two rules are enforced in code instead of left to training.

This is the agent fleet from my systems portfolio, pulled out into code. Sources and outputs are sanitized. The production version reads project boards, a calendar, a docs wiki, and chat over MCP; here they are a JSON file so the whole pipeline runs with no credentials and no tokens.

## The two rules

**Cite everything.** Every line in the pulse ends with a reference to a source record the agent actually read. A claim with no source, or a source that does not exist, fails the run.

**Send nothing.** The scheduled run produces a draft and stops. Sending lives in a separate module that requires a named human, and the harness checks by reading the code that no scheduled module imports it. A change that wires the agent to a send button fails CI before it ships.

## What's in the box

**Agent specs** in `specs/`. Three agents, each a Markdown file with a small front-matter block (schedule, sources, output, send) and a prompt standard a human can read. The front matter is the contract; `send: never` is enforced at load time. The daily pulse spec is the one drawn out on the portfolio page.

**Priority logic** in `agent_fleet/priority.py`. Four rules from the spec, in order: anything blocking a client first, every deadline inside 48 hours flagged, no status with no change, and lead with what leadership must act on.

**The pulse** in `agent_fleet/pulse.py`. Three sections, a footer saying what was read, and a status line saying it is unsent.

**The human gate** in `agent_fleet/approval.py`. One function. Refuses an empty approver and refuses to send twice.

**The eval harness** in `agent_fleet/evals.py`. Five checks, E1 through E5. The tests include six deliberately broken pulses to prove each check catches what it claims to.

## Try it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m agent_fleet run   specs/daily_pulse.md examples/sources_weekday.json
python -m agent_fleet eval  specs/daily_pulse.md examples/sources_weekday.json
python -m agent_fleet specs specs/
python -m pytest
```

The eval command prints the pulse, then the five checks. Any FAIL is a non-zero exit, and CI runs the same command on every push.

## What one morning looks like

```
DAILY OPERATIONAL PULSE · 2026-09-16 6:00 AM

NEEDS A DECISION (2)
1. Rollout blocked: hardware ETA slipped 3 days. Approve overtime staging? [board:rollout-04]
2. New deal wants a custom SLA beyond standard tiers: Capacity review first [chat:sla-thread]

ON TRACK (4)
- Migration batch 2 finished overnight: zero errors [board:migration-b2]
- 40-site menu refresh staged: QA passed [board:menu-refresh-40]
- Two escalations closed since yesterday [chat:escalations]
- Weekly newsletter drafted: ready for review [doc:newsletter-draft]

DEADLINES INSIDE 48H (1)
- Network-wide pricing update due Thursday [cal:pricing-update]

read: 4 boards, 2 calendar, 2 docs, 2 chat
drafted by the agent, unsent
```

## What it is not

The model call is not here. In production a model reads the raw sources and writes the phrasing; here the phrasing is deterministic so the priority logic and the guardrails can be tested without spending a token. The point of the repo is the standard and the checks around the model, which is where most agent deployments go wrong.

## Built with

Claude Code and Claude in Cowork. The rules, the spec standard, and the eval checks are mine, lifted from a fleet I designed and ran, and every line got read before it landed here. Directing the tool is the job.
