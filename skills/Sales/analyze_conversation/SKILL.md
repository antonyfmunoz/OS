---
name: analyze-conversation
description: "Analyze a DM conversation and determine the best next response to move toward identifying pain and booking a call — run on any active sales conversation to generate the recommended next message."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Analyze Sales Conversation

## Purpose

Analyze a DM conversation and determine the best next response to move toward identifying pain and booking a call.

---

## Outcome

A recommended next message, follow-up question, and conversation strategy — ready to act on immediately.

---

## Best-Practice Benchmark

The recommended response should feel like it came from a person who genuinely understands the prospect's situation — not a scripted sales process. Strategy drives the message, not templates.

---

## Decision Criteria

- Opening stage: focus on rapport and curiosity, no pain probing yet
- Pain discovery stage: ask open questions, listen for frustration or identity conflict
- Problem reframing stage: connect their described struggle to structure (not discipline)
- Offer introduction stage: only if pain is confirmed and self-awareness is present
- Call invitation stage: direct, casual, one sentence — only when momentum is positive

---

## Execution Steps

1. Load conversation log from: `03_CRM/Conversations`
2. Read the full conversation chronologically
3. Identify emotional signals: frustration level, self-awareness, readiness for change
4. Determine current stage:
   1. Opening
   2. Pain discovery
   3. Problem reframing
   4. Offer introduction
   5. Call invitation
5. Generate:
   - Recommended next message
   - Follow-up question (if additional discovery needed)
   - Conversation strategy (one sentence — what this response is trying to accomplish)
6. Append recommendations to the conversation file

---

## Failure Modes

- Jumping to offer introduction before pain is fully confirmed
- Asking too many questions in one message (pick one)
- Writing a response that sounds like a script
- Missing signals that the prospect is ready for the call invitation
- Continuing past the call invitation stage without booking the call

---

## Measurement

- Stage advancement rate per recommendation type
- Call booking rate from conversations where this skill produced the invitation message
- Conversation abandonment rate after following this skill's recommendation

---

## Improvement Opportunities

- Build a library of high-converting message examples per stage
- Track which question types accelerate stage advancement most reliably
- Identify patterns in conversations that stall after each specific stage


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
