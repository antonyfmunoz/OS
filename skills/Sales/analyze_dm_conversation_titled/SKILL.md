---
name: analyze-dm-conversation-titled
description: "Read a DM conversation thread and extract the current stage, emotional state, and key signals to inform the next move — run on any active DM conversation to determine next action."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Analyze DM Conversation

## Purpose

Read a DM conversation thread and extract the current stage, emotional state, and key signals to inform the next move.

---

## Outcome

A structured analysis with conversation stage, pain points, signals, momentum assessment, and a single clear recommended next action.

---

## Best-Practice Benchmark

Analysis must be grounded in exact quotes from the conversation, not assumptions or projections. The recommended move should be specific enough to draft from directly.

---

## Decision Criteria

- Advance conversation if: positive momentum, pain expressed, or buying signal detected
- Hold/nurture if: neutral momentum with no resistance
- Apply pattern interrupt if: stalled for 4+ days
- Qualify for call if: all three qualification criteria are present and momentum is positive
- Disengage if: explicit rejection or repeated zero-response to two follow-ups

---

## Execution Steps

1. Load conversation file from: `03_CRM/Conversations/`
2. Read the full conversation chronologically — do not skim
3. Identify current stage: Cold → Engaged → Diagnosing → Qualifying → Ready → Booked
4. Extract signals:
   - Pain statements (exact language they used to describe struggle)
   - Resistance signals (deflection, skepticism, avoidance)
   - Buying signals (asking about cost, timeline, or what's included)
5. Assess momentum of last message: positive / neutral / stalled
6. Write recommended move — one sentence, specific enough to draft from
7. Output:
   - `stage:` current conversation stage
   - `pain_points:` list of expressed frustrations
   - `signals:` buying or resistance signals present
   - `momentum:` positive | neutral | stalled
   - `recommended_move:` what to do next

---

## Failure Modes

- Assuming pain exists when none is explicitly stated
- Misreading deflection as engagement
- Recommending "follow up" without specifying how and when
- Skipping to call invitation before pain is confirmed
- Treating a single message as a buying signal without supporting context

---

## Measurement

- Advancement rate: % of analyzed conversations that move to the next stage after the recommended move
- Accuracy of stage classification (validated by actual conversation outcome)

---

## Improvement Opportunities

- Build a pattern library of high-converting conversation transitions
- Track which types of pain statements most reliably advance to booked calls
- Add time-since-last-message as a weighting factor for urgency of response


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
