---
name: generate-follow-up-message
description: "Write a follow-up DM for a lead who has gone quiet after initial contact — run when a lead has not responded within 1-3 days and follow-up count is below 2."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Generate Follow-Up Message

## Purpose

Write a follow-up DM for a lead who has gone quiet after initial contact, without sounding desperate or salesy.

---

## Outcome

One ready-to-send DM message — 1-2 sentences max, ending with an open question that requires a real answer. No pitch, no mention of the program.

---

## Best-Practice Benchmark

The best follow-up feels like the sender remembered something interesting and thought of the prospect. It opens a new thread of conversation, not a reminder about the previous one.

---

## Decision Criteria

- 1-3 days since last contact: light value add — share a relevant insight or question
- 4-7 days: pattern interrupt — open with something unexpected
- 8+ days: re-engagement — acknowledge the gap, ask a direct question
- Do not follow up more than twice without a reply — disengage and mark as stalled

---

## Execution Steps

1. Load lead file: `03_CRM/Leads/lead_[username]_*.md`
2. Load last conversation context from: `03_CRM/Conversations/` (if available)
3. Check qualification score and calculate days since last contact
4. Select angle based on recency (see Decision Criteria)
5. Write one message — 1-2 sentences maximum
6. End with an open question that requires a real answer (not yes/no)
7. Review: does the message mention the program, price, or pitch anything? If yes, rewrite.

---

## Failure Modes

- Mentioning the program, price, or any pitch in the follow-up
- Sending a third follow-up after two unanswered messages
- Using a yes/no closing question
- Writing more than 2 sentences (kills the casual tone)
- Following up too quickly after initial outreach (signals desperation)

---

## Measurement

- Re-engagement rate: % of follow-up messages that receive a reply
- Advancement rate: % of re-engaged leads that reach qualifying stage
- Disqualification accuracy: leads marked stalled that never return

---

## Improvement Opportunities

- Track which follow-up angles (value add vs. pattern interrupt vs. re-engagement) convert best by time bracket
- Build a library of high-performing follow-up templates per time bracket
- A/B test question types: curiosity questions vs. pain-focused questions vs. observation-based questions


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
