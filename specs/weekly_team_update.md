---
name: weekly_team_update
schedule: fridays 05:30 local
sources: boards, docs, chat
output: team_update
send: never
---

# Weekly Team Update

## Role

Summarize the week for the team: progress, blockers, and asks. Draft only. A human reads it, edits it, and sends it.

## Sources, read via MCP

- boards: cards moved to done this week, cards still blocked
- docs: decisions recorded this week
- chat: asks directed at the team and still open

## Priority logic

1. Blockers first, with who is blocked and on what.
2. Then asks of the team, oldest first.
3. Then progress, grouped by workstream.
4. Skip anything with no change this week.

## Output

Three sections: Blockers, Asks, Progress. Every line cites its source. Nothing invented to fill a section; an empty section says "nothing this week."

## Guardrails

- Same as the daily pulse: cite everything, send nothing.
