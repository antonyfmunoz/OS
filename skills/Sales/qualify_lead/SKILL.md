---
name: qualify-lead
description: "Evaluate a prospect against the the active offer ICP to determine if they are worth pursuing for a sales conversation — run on every new lead signal before outreach is drafted."
allowed-tools: "Read, Bash"
trigger: both
version: 1.0
effort: medium
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Qualify Lead

## Purpose

Evaluate a prospect against the the active offer ICP to determine if they are worth pursuing for a sales conversation.

---

## Outcome

Lead file updated with qualification score (HIGH / MEDIUM / LOW / DISQUALIFIED) and a one-sentence reason — ready for the next action decision.

---

## Best-Practice Benchmark

A qualified lead has all three criteria present and in their own words, not your interpretation. If you have to stretch to find ownership language, it isn't there.

---

## Decision Criteria

- HIGH: all three criteria clearly present
- MEDIUM: two criteria present, one ambiguous
- LOW: one criterion present or all weak
- DISQUALIFIED: spam account, bot signals, pure negativity, or zero pain expressed

Do not mark HIGH without explicit ownership language. Ever.

---

## Execution Steps

1. Load the lead signal file from: `03_CRM/Leads/` or `01_Inbox/processed_signals/`
2. Read the lead's comment, bio, and any available context in full
3. Score against three criteria:
   - **Frustration** — do they express being stuck, wasting potential, or lack of execution?
   - **Self-awareness** — do they acknowledge they are the problem, not external factors?
   - **Ownership language** — do they use words like "I need to", "I want to change", "I keep failing"?
4. Assign: HIGH / MEDIUM / LOW / DISQUALIFIED
5. Write one-sentence qualification reason using their actual language
6. Append to lead file frontmatter:
   - `qualification: HIGH | MEDIUM | LOW | DISQUALIFIED`
   - `qualification_reason: [one sentence]`

---

## Failure Modes

- Marking HIGH because the account looks promising, not because all 3 criteria are confirmed
- Interpreting ambiguous language as ownership language
- Qualifying based on follower count or aesthetics — irrelevant
- Missing DISQUALIFIED signals (bot behavior, engagement farming patterns)

---

## Measurement

- Conversion rate from HIGH leads to booked calls
- False positive rate: HIGH leads who go cold after first reply (signals over-qualification)
- DISQUALIFIED accuracy: % of disqualified leads later confirmed as non-ICP

---

## Improvement Opportunities

- Build a calibration log of edge cases — leads that were borderline and what happened
- Refine ownership language dictionary as new ICP phrases are collected
- Add Instagram engagement pattern scoring to catch bots earlier

---

## Gotchas

- The most common error: marking HIGH because the account looks promising aesthetically. Follower count, good photos, and inspirational captions are not qualification criteria.
- Absence of external blame is not the same as presence of ownership language. "I want to improve" is not ownership language. "I keep quitting on myself" is.
- Engagement farming accounts have high activity but zero ownership signal. Look for comments that are self-referential, not accounts that comment frequently on other people's content.
- MEDIUM does not mean pursue immediately. MEDIUM means build a small watch list — see if another signal arrives before sending outreach.
- If you're reading a signal and interpreting their words as ownership language rather than quoting the actual words — that's a red flag. Quote directly or don't qualify at that level.
- A private account with no visible signal is LOW by default — not DISQUALIFIED. Reach decision is different from disqualify decision.
