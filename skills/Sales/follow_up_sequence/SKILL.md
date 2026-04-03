---
name: follow-up-sequence
description: "Generate a multi-touch follow-up sequence for leads who have been contacted but not yet responded or booked — run when a lead requires a structured multi-touch outreach plan."
allowed-tools: "Read, Bash"
trigger: conversational
version: 1.0
effort: medium
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Follow-Up Sequence

## Purpose

Generate a multi-touch follow-up sequence for leads who have been contacted but not yet responded or booked.

---

## Outcome

A 3-5 message follow-up sequence with specific timing, channel, and angle for each touch. Each message builds on the previous without repeating it.

---

## Best-Practice Benchmark

Charlie Morgan follow-up methodology: each touch changes the angle, not just repeats the ask. Touch 1: value add. Touch 2: social proof. Touch 3: pattern interrupt. Touch 4: direct close attempt. Touch 5: breakup message.

---

## Decision Criteria

- Has the lead engaged at all (opened, replied)?
- How many days since last contact?
- What was the last message about?
- What stage is the lead in?

---

## Execution Steps

1. Review lead's last interaction and stage
2. Determine which touch number this is
3. Select the appropriate angle for this touch
4. Write message matching lead's ICP profile
5. Schedule timing (day 1, 3, 7, 14, 21)

---

## Failure Modes

- Repeating the same angle twice
- Following up too fast (< 24h)
- Following up without value on touch 1
- Sending breakup message too early (< touch 4)

---

## Measurement

- Reply rate per touch number
- Booking rate per sequence
- Optimal touch count before conversion

---

## Improvement Opportunities

Track which touch number produces most bookings. Optimize angle order based on reply patterns. Test timing intervals.

---

## Gotchas

- Never repeat the same angle. If Touch 1 was a question, Touch 2 must be value, not another question. Repetition kills conversations faster than silence.
- The breakup message is not a threat — it is a genuine close of the loop. It must feel real. "I'll remove you from my list" only works if it's true.
- Following up in under 24 hours signals desperation. The minimum gap between touches is 24 hours. Day 1, 3, 7, 14, 21 is the default timing framework.
- If the lead went silent after a positive reply, do not treat them the same as a lead who never replied. A positive-then-silent lead gets a softer pattern-interrupt, not a standard touch sequence.
- Touch 4 is a direct close attempt. If it doesn't feel like a close, it isn't working. Be explicit about the decision being invited.
- Running this skill on a lead who already said a clear no is a mistake. This skill is for non-responses and ambiguous responses, not for re-engaging someone who opted out.
