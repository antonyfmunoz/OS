---
name: content-calendar
description: "Plan a 7-day content schedule grounded in real ICP signals — run at the start of each content planning cycle when signal queue has been processed."
allowed-tools: "Read, Bash"
version: 1.0
effort: high
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# content_calendar

## Purpose
Plan a 7-day content schedule grounded in real ICP signals — not invented topics. Every piece must trace back to observed pain language, behavior, or archetype from the signal queue. Content is a filter, not a broadcast. The right person sees it and self-selects. The wrong person disqualifies themselves.

## Outcome
A 7-day content plan: platform, format, hook, body angle, CTA, and the specific signal each piece is derived from. No filler slots. If there is no signal for a day, that day is blank until one is found.

## Best-Practice Benchmark
Signal-fidelity model: publish content that attracts the exact person you want and repels everyone else. Volume without signal fidelity is noise. Every post should make the ICP reader feel "this was written for me." Signal-derived content converts because it uses the audience's own language back at them.

## Decision Criteria
- Is each piece traceable to a specific signal (post, comment, DM, keyword)?
- Does the hook contain language the ICP would actually say or think?
- Is the CTA one step — not a wall of options?
- Would a man 18-25 who is wasting his potential feel called out by this?
- Is the angle polarizing enough to make the right person stop scrolling?

## Execution Steps
1. Pull the top 5 highest-signal ICP observations from the signal queue this week
2. For each signal: extract the exact pain language, emotional state, and archetype
3. Translate each into a content angle — one angle per signal
4. Assign format (Reel, carousel, static, story) based on depth of idea
5. Write the hook using the ICP's own vocabulary — not your framing
6. Define the body angle: challenge the norm, reframe the problem, reveal the hidden cost
7. Assign a single CTA matched to funnel stage (follow, DM, apply, book)
8. Output the 7-day plan as a structured table: Day | Signal Source | Format | Hook | Angle | CTA

## Failure Modes
- Inventing topics not grounded in observed signals — creates content no one asked for
- Using your words instead of the ICP's words in hooks — breaks pattern interrupt
- Multiple CTAs on one post — dilutes action
- Publishing on a schedule instead of a signal cadence — forces filler
- Reusing the same angle 3 days in a row — kills novelty, drops reach
- Treating content as brand-building instead of a filter — wrong goal

## Measurement
- Signal traceability rate: what % of posts link to a specific ICP signal
- Hook stop rate (3-second view rate on Reels): target >40%
- Qualified DM rate: how many posts generate DMs from ICP-matched accounts
- Conversion rate: DMs from content → booked call → closed

## Improvement Opportunities
- After each post goes live, track which signal produced the highest engagement
- Feed top-performing post angles back into outreach openers
- Identify which formats produce the most qualified DMs, not just the most likes
- Build a running library of signal → hook pairings that can be reused in future cycles


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
