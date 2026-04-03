---
name: stage-transition-assessment
description: "Evaluate whether the current stage proof gate has been genuinely met — run when revenue crosses a stage threshold or before activating any Stage 2 agents."
allowed-tools: "Read, Bash"
version: 1.0
effort: high
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Stage Transition Assessment

## Purpose
Evaluate whether the current stage proof gate
has been genuinely met — not just numerically
crossed. One sale is not Stage 2.
The same channel working three times
with the same ICP is Stage 2.

## Outcome
Clear yes/no on whether stage advancement
is warranted with evidence and the one
condition that remains unmet if no.

## Best-Practice Benchmark
Repeatability is the gate, not revenue alone.
Three signals from the same channel + same ICP
constitutes proof of repeatability.

## Decision Criteria
- Run when revenue crosses a stage threshold
- Run when the founder says "I think we're
  ready to scale"
- Run before activating any Stage 2 agents

## Stage Gates
Stage 1 → 2: First sale closed
Stage 2 → 3: 3 sales from same channel
Stage 3 → 4: 10 sales, ops documented
Stage 4 → 5: 30 sales, team handling ops
Stage 5 → 6: $10K/month sustained 3 months

## Execution Steps
1. Pull current revenue and sales count
2. Check against stage gate threshold
3. If threshold crossed numerically —
   check repeatability:
   - Did the same channel produce the sales?
   - Was the ICP consistent across sales?
   - Is the conversion rate holding or
     was it a lucky run?
4. If repeatable → advancement warranted.
   Notify DEX. Stage manager handles transition.
5. If not repeatable → name what's missing.
   One more successful close from same channel
   before reassessing.

## Failure Modes
- Advancing on one data point
- Advancing because the founder wants to
- Calling a lucky close proof of repeatability
- Skipping the repeatability check
- Activating Stage 2 systems (upsell, content
  at scale) before Stage 1 proof is solid

## Measurement
- Conversion rate held after advancement
- Same channel still producing at Stage 2
- No regression to Stage 1 behavior after
  transition

## Improvement Opportunities
- Track channel consistency across all closes
- Flag if ICP shifted between sales (may
  signal accidental market pivot)


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
