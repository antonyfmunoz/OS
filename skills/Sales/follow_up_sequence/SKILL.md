---
name: follow-up-sequence
description: "Generate a multi-touch follow-up sequence for leads who have been contacted but not yet responded or booked — run when a lead requires a structured multi-touch outreach plan."
allowed-tools: "Read, Bash"
version: 1.0
---

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
