---
name: dm-opener
description: "Write a cold DM opener for an the active offer prospect — run when a qualified lead has been identified and first contact message needs to be drafted."
allowed-tools: "Read"
trigger: both
version: 1.0
effort: medium
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: DM Opener Framework

## Purpose

Write a cold DM that starts a real conversation with a qualified the active offer prospect. Not a pitch — a conversation starter that makes them feel specifically seen.

---

## Outcome

A single DM under 3 lines that references something specific to this person, bridges to a pain they've expressed, and ends with a single open question. Ready to send or batch for ManyChat.

---

## Best-Practice Benchmark

The best cold DM doesn't feel cold. It feels like someone noticed something real and was curious enough to ask. Specificity is trust. A message that could have been sent to anyone gets treated like spam. A message that only makes sense for this person gets a reply.

---

## Decision Criteria

- Is the lead qualified (HIGH or MEDIUM from qualify_lead skill)?
- Has there been prior contact? (If yes, use reply_handler or follow_up_sequence instead)
- Is there a specific signal to reference from their content or profile?
- Is this manual outreach or a ManyChat automation batch?

Manual outreach requires a fully personalized opener.
ManyChat batch allows a semi-personalized template tied to a specific content type or pain signal.

---

## Execution Steps

**The Three-Line Structure:**

Line 1 — Specific Observation
Reference something real and specific from their content, bio, or a comment they made.
- NOT: "Love your content." (generic — could be anyone)
- NOT: "I saw your post about discipline." (vague)
- YES: "Your post about starting over for the third time this year hit different." (specific to what they said)
- YES: "The comment you left about always having the plan but losing it by week two — that's an exact pattern I've seen." (quotes their language)

Line 2 — Bridge
One sentence connecting their situation to a result. Not a pitch. An observation that opens a door.
- NOT: "I help people like you achieve their goals."
- NOT: "I have a program that fixes this."
- YES: "That gap between knowing what to do and actually doing it for 90 days straight is almost always a structure problem, not a motivation problem."
- YES: "Most guys I've seen who describe that cycle say the same thing — it's not commitment they're missing."

Line 3 — Single Question
End with one question that requires a real answer. Not a yes/no. Not a pitch.
- NOT: "Are you interested in learning more?"
- NOT: "Would you like to check out my program?"
- YES: "What usually breaks the streak for you?"
- YES: "What's the one thing you'd fix first if you could?"
- YES: "How long has that pattern been running?"

**Full Example:**
"Your post about starting over every few weeks — I've seen that pattern in a lot of guys your age. It's almost never a motivation problem, it's that there's no external structure making it hard to quit. What usually triggers the reset for you?"

---

## ManyChat Batch Adaptation

For automation batches, the opener must still be signal-specific. Tie the opener to the specific content type the ManyChat trigger fires on (e.g., a comment on a discipline reel triggers an opener about the struggle they expressed in that comment).

Batch openers follow the same 3-line structure but use [SPECIFIC_DETAIL] as a placeholder for the signal that triggered the message — not generic filler.

---

## Failure Modes

- "I help people like you" — disqualifying phrase, never use
- "Are you interested in" — positions as a pitch before a conversation exists
- "Check out my program" — rejected immediately, conversation never starts
- Openers longer than 3 lines — too long signals marketing content, not genuine curiosity
- Referencing something not actually visible in their content — if you can't cite the source, don't reference it
- Sending the same opener to someone who has already received it
- Personalizing from assumptions rather than verified profile signals

---

## Measurement

- Reply rate per opener (tracked in `services/opener_stats.json`)
- Reply rate segmented by observation type (post reference vs. comment reference vs. bio reference)
- Conversation advancement rate: what % of replies reach discovery stage

---

## Improvement Opportunities

- Retire openers below 10% reply rate after 50 sends
- Run 70% volume on best performer, 20% variation, 10% new angle (max 3 simultaneous)
- Build an opener library indexed by ICP signal type — different observation types for different pain expressions
- Track which observation types (post / comment / bio) produce the highest reply rate

---

## Gotchas

- The observation in Line 1 must be verifiable. If you're referencing a feeling you inferred rather than a thing they said, you're personalizing from assumption. That reads as weird and presumptuous.
- "Love your content" plus any question is not an opener — it's a compliment with a question attached. Compliments don't create conversations. Observations do.
- The question in Line 3 must be genuinely answerable in a few sentences. Avoid compound questions ("what's your goal and what's stopping you?") — they overwhelm and reduce reply rate.
- Openers to the wrong ICP (wrong age, wrong situation, wrong pain) waste a slot and can't be walked back. Qualify first, open second.
- The bridge in Line 2 should not use the word "discipline" unless they used it first. It's a trigger word that signals "fitness motivation content" and makes people feel pitched.
- Never run more than 3 opener variants simultaneously. You can't learn from data you can't isolate.