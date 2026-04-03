---
name: hook-performance-analysis
description: "Analyze which hook structures are stopping the scroll — run weekly once 10+ content pieces have been published to identify top patterns and retire underperformers."
allowed-tools: "Read, Bash"
version: 1.0
effort: high
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Hook Performance Analysis

## Purpose
Analyze which hook structures are stopping the scroll and which are losing viewers in the first 3 seconds.

## Outcome
Content Agent knows exactly which hook patterns to prioritize and which to retire.

## Decision Criteria
- Run after 10+ pieces of content have been published
- Run weekly once content is consistently live

## Execution Steps
1. Gather performance data for all published content (from platform analytics or Intelligence Agent report)
2. Isolate the hook (first line) for each piece
3. Sort by 3-second retention rate or highest engagement-to-reach ratio
4. Identify patterns in top performers:
   - Hook structure (question, statement, contradiction, number, story opening)
   - Specificity level
   - Emotional trigger (fear, curiosity, identity, aspiration)
5. Identify patterns in bottom performers
6. Generate the next 3 hook variations to test based on top performer patterns
7. Retire hook structures appearing consistently in bottom performers

## Failure Modes
- Analyzing engagement (likes) instead of reach-to-engagement ratio
- Sample size too small (fewer than 10 pieces)
- Changing hook strategy based on one outlier performance
- Confusing hook quality with topic quality

## Measurement
- Week-over-week 3-second retention rate
- Percentage of pieces that outperform the account average


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
