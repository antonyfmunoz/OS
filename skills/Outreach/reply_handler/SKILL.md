---
name: reply-handler
description: "Handle an incoming DM reply from a prospect and determine the next action — run when a prospect replies to an opener or follow-up message."
allowed-tools: "Read"
trigger: conversational
version: 1.0
---

# Skill: Reply Handler

## Purpose

Evaluate an incoming DM reply, classify the response type, and generate the appropriate next message or action to advance the conversation toward a booked call or qualification decision.

---

## Outcome

A classified reply (Positive / Curious / Negative / Ghost) with the next action defined: response message drafted, or conversation closed and logged in CRM.

---

## Best-Practice Benchmark

Speed and precision. Reply within 2 hours during work hours. The response quality is determined by how well it continues the conversation — not by how much information it provides. Give just enough to advance one step. Every response should either deepen the discovery or invite a specific next step. Never do both simultaneously.

---

## Decision Criteria

**Reply classification:**

- **Positive**: They answered the question, shared their situation, expressed interest, or asked about the program. Advance to qualification or call booking.
- **Curious**: They engaged but indirectly — asked a question back, said something ambiguous, gave a one-liner. Give value, then ask one qualifying question.
- **Negative**: Clear disinterest, pushback, or "no thanks." Acknowledge, close gracefully, log in CRM. Do not argue.
- **Ghost (no reply)**: Follow up once at 48 hours with a new value angle. After the second ghost, hand to `follow_up_sequence`. After a third ghost, mark as dormant in CRM.

---

## Execution Steps

**Positive Reply:**
1. Validate what they shared with one sentence that uses their exact language back
2. Ask one deepening question that gets closer to the root pain
3. If pain is clearly established: move to call invitation ("Want to see if Initiate Arena is a fit for where you're at?")
4. Never provide a link before qualifying. Curiosity is not qualification.

**Example:**
Their reply: "Yeah honestly every Sunday I plan out my week and by Wednesday it's gone."
Your response: "That Sunday reset pattern is one of the most common things I hear. The plan isn't the problem — what's usually missing is what makes Wednesday harder to quit on than to coast through. What does Wednesday usually look like when it goes sideways?"

**Curious Reply:**
1. Give one short value statement that directly addresses what they asked or implied
2. Follow with one qualifying question
3. Do not pitch. Do not provide program details. One question.

**Example:**
Their reply: "What do you mean by structure problem?"
Your response: "Most discipline failures aren't about wanting it enough — they're about having no environment that makes execution the path of least resistance. The system does that work so willpower doesn't have to. What's the thing you keep trying to build that keeps breaking down?"

**Negative Reply:**
1. One sentence acknowledging without arguing: "Totally fair — good luck with it."
2. No follow-up after a clear no. Log it as Disqualified in CRM.
3. Exception: if the negative reply includes new pain signal ("I'm good, just overwhelmed right now"), treat as Curious and re-engage with a single empathetic question.

**Ghost (48-hour follow-up):**
- Send one new value-angle message (not a repeat of the opener)
- Example: "Thinking about you reaching out after your Sunday was probably enough context. Quick question — do you usually restart on Mondays or just push through?"
- If no reply after this touch: hand to `follow_up_sequence` for structured multi-touch

---

## Reply Timing

- Within 2 hours during work hours (9am–9pm local)
- Within 12 hours maximum
- Ghost follow-up at exactly 48 hours — not 24, not 72

---

## Qualifying Questions to Use

Use these to deepen discovery when a positive reply is received. Never use more than one per message.
- "What's your main challenge right now?"
- "What's one thing you'd fix first?"
- "How long has that been the pattern?"
- "What have you already tried?"
- "What does a week look like when it goes well vs when it falls apart?"

---

## Failure Modes

- Providing program details before qualifying (giving a sales pitch to a curious reply)
- Not using their exact language back in the validation step
- Sending a follow-up in under 24 hours (desperation signal)
- Continuing after two clear nos (disrespects them and wastes time)
- Asking two questions in one message (splits their attention, reduces reply quality)
- Using the word "program" or "offer" in any message before the prospect has asked about it

---

## Measurement

- Reply-to-qualification rate: % of positive replies that reach a qualifying question answered
- Reply-to-booked-call rate: % of positive conversations that result in a booked call
- Response time average (target: under 2 hours during work hours)

---

## Improvement Opportunities

- Build a response template library indexed by reply type and pain category
- Track which qualifying questions produce the most discovery-rich replies
- Log every conversation hand-off point to Sales Agent to understand where the transition works vs. breaks

---

## Gotchas

- Using their language back is not flattery — it's a mirroring technique that signals you actually heard them. Skip it and they feel processed, not heard.
- "Curious" replies that get pitched to immediately convert at near-zero. Curiosity must be fed, not capitalized on. Give value first.
- If the prospect goes silent after a genuinely positive conversation (not a ghost — they engaged and then stopped), the reason is almost always timing, not disinterest. The 48-hour follow-up should reference the conversation, not start a new one.
- Don't classify a "that's interesting" reply as Positive. Positive means they answered something. "Interesting" is Curious.
- When handing to Sales Agent after qualification, pass the full conversation context — not just a name. The handoff is only as good as the context it carries.
- Never use "Just checking in" as a follow-up opener. It has zero value and signals that you have nothing new to offer.