---
name: binding-constraint-diagnosis
description: "Identify the one active business constraint from the four constraint systems — run at the start of every CEO morning cycle or whenever the founder asks what to focus on."
allowed-tools: "Read, Bash"
version: 1.0
effort: high
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Binding Constraint Diagnosis

## Purpose
Identify the one active business constraint
from the four constraint systems: Leads, Sales,
Delivery, Profit. Run this before generating
any CEO daily objective.

## Outcome
One constraint named with evidence.
Active agents identified.
Idle agents identified.
One recommendation for today.

## Best-Practice Benchmark
More → Better → New logic applied in order:
- Volume check first — never skip this
- Quality/conversion check second
- Unit economics check third
- Never run multiple constraints simultaneously

## Decision Criteria
- Run at the start of every CEO morning cycle
- Run whenever the founder asks "what should
  I focus on?"
- Run whenever a constraint shift is suspected

## Execution Steps
1. Check outreach volume this week — is it
   at target? If no → Leads constraint (MORE)
2. If volume at target — check reply rate.
   Below benchmark → Leads constraint (BETTER)
3. If reply rate acceptable — check call rate.
   Below benchmark → Sales constraint
4. If calls happening — check close rate.
   Below benchmark → Sales constraint
5. If sales happening — check LTV and retention.
   Low LTV → Delivery constraint
6. If revenue exists — check unit economics.
   CAC not recovering in 30 days → Profit constraint
7. Name the constraint. Name the evidence.
   Name the active agents. Name the idle agents.
   Generate one recommendation.

## Failure Modes
- Diagnosing multiple constraints simultaneously
- Changing strategy before checking volume
- Skipping the MORE check and going straight
  to BETTER diagnosis
- Activating agents for non-active constraints
- Using gut feel instead of funnel data

## Measurement
- Constraint correctly identified vs outcome
- Task completion rate of active agents
  this week vs idle agents (active should
  be higher)

## Improvement Opportunities
- Track constraint duration (how many weeks
  on the same constraint)
- Alert when constraint hasn't shifted after
  4 weeks — signals a deeper structural problem


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
