---
name: analyze-content-performance
description: "Determine what worked, what didn't, and what one thing changes next batch. Use after 10+ pieces published or weekly once content is live."
allowed-tools: "Read"
version: 1.0
effort: high
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Analyze Content Performance

## Purpose
One signal, one decision from content data. Not a comprehensive audit.

## Outcome
One clear directive: what to do more of, what to retire, what single variable to test next.

## Decision Criteria
- Run after 10+ pieces published
- Run weekly once content is live
- Run when performance has plateaued
- Do not run with fewer than 10 data points

## Execution Steps
1. Gather performance data for all published content (reach, engagement, DMs, saves)
2. Sort by the metric that matters at current stage:
   Stage 1: DMs received (leads)
   Stage 2: Profile visits (awareness)
   Stage 3: Saves and shares (reach)
3. Identify top 20% — what patterns appear?
   Hook structure, topic, format, tone
4. Identify bottom 20% — what pattern fails?
5. Generate ONE directive:
   Do more of [X]. Retire [Y]. Test [Z].

## Failure Modes
- Analyzing all metrics equally
- Multiple directives instead of one
- Changing more than one variable
- Sample size under 10 pieces

## Measurement
- Direction improves performance next batch
- Content DM rate week-over-week


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
