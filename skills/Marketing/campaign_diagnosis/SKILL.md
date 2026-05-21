---
name: campaign-diagnosis
description: "Identify the single constraint limiting marketing performance — run when content metrics are underperforming or when reach and conversion trends diverge."
allowed-tools: "Read, Bash"
version: 1.0
effort: high
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# campaign_diagnosis

## Purpose
Identify the single constraint limiting marketing performance. Not a list of improvements — one root cause, one highest-leverage fix. Marketing underperformance collapses into two categories: reach is broken or conversion is broken. Mixing the fix for one into the other wastes resources and obscures the real problem.

## Outcome
A structured diagnosis: confirmed root cause, evidence that isolates it from alternatives, and the single highest-leverage intervention. One action, not a list.

## Best-Practice Benchmark
Constraint theory applied to marketing: the system has one bottleneck. Optimizing non-bottlenecks does not improve throughput. The diagnostic: if reach is up but conversions are flat, the message is wrong. If reach is down, the distribution is wrong. Never improve both simultaneously — you lose the ability to measure causation.

## Decision Criteria
Diagnose in this order:
1. Is reach broken? (impressions, accounts reached, follower growth — are they trending down?)
2. Is hook failing? (does the content stop the scroll? 3-second view rate, saves)
3. Is conversion broken? (reach is there but no DMs, no clicks, no replies)
4. Is the CTA failing? (DMs from content but wrong ask or wrong stage)
5. Is the audience wrong? (engagement is from non-ICP accounts)
6. Is the message wrong? (right audience but wrong framing, wrong pain addressed)

## Execution Steps
1. Pull the last 14 days of content performance metrics
2. Separate reach metrics from conversion metrics — do not mix them
3. Identify the first metric in the diagnostic chain that is broken
4. Form a hypothesis: "Reach is fine. Hook is failing. Evidence: 3-second view rate is 18%."
5. Test the hypothesis against at least one counter-explanation and rule it out
6. Name the single fix: change the hook format, change the CTA, change the distribution channel, change the audience targeting
7. Define what success looks like in 7 days with this fix applied
8. Output: root cause + evidence + single fix + success metric

## Failure Modes
- Diagnosing reach and conversion simultaneously — obscures the real constraint
- Recommending 3-5 changes at once — removes ability to measure what worked
- Treating low likes as low performance when DMs and saves are high
- Optimizing for vanity metrics (likes, followers) instead of qualified DMs
- Assuming the audience is wrong before testing the message first
- Blaming the platform algorithm before checking if the hook is working

## Measurement
- Diagnostic accuracy: was the identified constraint actually the bottleneck? (validate after 7 days)
- Time to root cause: how many data points needed before confident diagnosis
- Fix leverage: improvement in target metric after applying the single intervention

## Improvement Opportunities
- Build a diagnostic reference: common symptoms → likely root cause (running log)
- After each 7-day fix cycle, record which constraint was most common that month
- Identify leading indicators that predict which constraint will emerge next week
- Track whether content performance variance correlates with signal quality in the queue


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
