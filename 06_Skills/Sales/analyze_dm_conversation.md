# Skill: Analyze DM Conversation

## Purpose

Read a DM conversation thread and determine the current stage, emotional state, and key signals — then generate a recommended next move to advance toward booking a call.

---

## Outcome

A structured analysis with conversation stage, pain points, signals, momentum assessment, and a single clear recommended next message — specific enough to draft from directly.

---

## Best-Practice Benchmark

Analysis must be grounded in exact quotes from the conversation, not assumptions or projections. The recommended response should feel like it came from a person who genuinely understands the prospect's situation — not a scripted sales process. Strategy drives the message, not templates.

---

## Decision Criteria

- Advance conversation if: positive momentum, pain expressed, or buying signal detected
- Hold/nurture if: neutral momentum with no resistance
- Apply pattern interrupt if: stalled for 4+ days
- Qualify for call if: all three qualification criteria are present and momentum is positive
- Disengage if: explicit rejection or repeated zero-response to two follow-ups
- Opening stage: focus on rapport and curiosity — no pain probing yet
- Pain discovery stage: ask open questions, listen for frustration or identity conflict
- Problem reframing stage: connect their described struggle to structure (not discipline)
- Offer introduction stage: only if pain is confirmed and self-awareness is present
- Call invitation stage: direct, casual, one sentence — only when momentum is positive

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
6. Generate:
   - Recommended next message
   - Follow-up question (if additional discovery needed)
   - Conversation strategy (one sentence — what this response is trying to accomplish)
7. Output:
   - `stage:` current conversation stage
   - `pain_points:` list of expressed frustrations (exact quotes)
   - `signals:` buying or resistance signals present
   - `momentum:` positive | neutral | stalled
   - `recommended_move:` what to do next
8. Append recommendations to the conversation file

---

## Failure Modes

- Assuming pain exists when none is explicitly stated
- Jumping to offer introduction before pain is fully confirmed
- Misreading deflection as engagement
- Asking too many questions in one message (pick one)
- Recommending "follow up" without specifying how and when
- Writing a response that sounds like a script
- Missing signals that the prospect is ready for the call invitation
- Treating a single message as a buying signal without supporting context
- Continuing past the call invitation stage without booking the call

---

## Measurement

- Advancement rate: % of analyzed conversations that move to the next stage after the recommended move
- Accuracy of stage classification (validated by actual conversation outcome)
- Call booking rate from conversations where this skill produced the invitation message
- Conversation abandonment rate after following this skill's recommendation

---

## Improvement Opportunities

- Build a pattern library of high-converting conversation transitions and message examples per stage
- Track which question types and pain statements accelerate stage advancement most reliably
- Identify patterns in conversations that stall after each specific stage
- Add time-since-last-message as a weighting factor for urgency of response
