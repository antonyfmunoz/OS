# Skill: Weekly CEO Report

## Purpose
Generate the CEO's weekly report to the
Portfolio Agent. Structured, data-driven,
honest about failures.

## Outcome
A complete weekly report covering:
constraint status, offer stage, key metric
movement, what worked, what didn't,
what changes next week, stage transition
status.

## Best-Practice Benchmark
One thing worked. One thing didn't.
One variable changes. No softening.
Portfolio Agent reads this to calibrate
resource allocation — it needs the truth.

## Decision Criteria
- Run every Sunday evening
- Run on demand when Portfolio Agent requests

## Execution Steps
1. Pull 7-day funnel metrics
2. Pull last week's active constraint
   and this week's active constraint
   — did it change?
3. Pull agent performance scores this week
4. Identify one thing that worked:
   a metric that moved in the right direction
5. Identify one thing that didn't:
   a metric that missed benchmark
6. Generate one change for next week:
   one variable to test or fix
7. Check stage transition status:
   are we closer to proof gate than last week?
8. Format as structured report:

   VENTURE: [name]
   WEEK: [date range]
   CONSTRAINT: [active] | [same/changed]
   OFFER STAGE: [I/II/III] | proof [met/not met]

   FUNNEL:
   DMs: [actual] vs [target] [↑↓→]
   Reply rate: [actual]% vs [target]% [↑↓→]
   Calls: [actual] vs [target] [↑↓→]
   Close rate: [actual]% vs [target]% [↑↓→]

   WHAT WORKED: [one thing]
   WHAT DIDN'T: [one thing]
   WHAT CHANGES: [one variable next week]

   STAGE GATE: [X] of [Y] condition met.
   [condition remaining if not met]

## Failure Modes
- Reporting activity instead of outcomes
- Softening bad news
- Listing multiple things that didn't work
  (pick the most important one)
- Not naming what specifically changes
- Reporting the same "what changes" two
  weeks in a row without execution

## Measurement
- Portfolio Agent constraint diagnosis
  matches CEO report constraint
- Changes named week-over-week are actually
  implemented
- Stage gate progress moves forward each week

## Improvement Opportunities
- Track week-over-week delta on each metric
- Flag when the same constraint holds for
  more than 3 weeks
- Surface the one highest-leverage action
  for the founder specifically (not agents)
