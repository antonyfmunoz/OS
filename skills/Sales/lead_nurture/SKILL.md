---
name: lead-nurture
description: "Keep leads warm and moving through the pipeline when they are not yet ready to book but have shown genuine interest — run when a lead is engaged but not ready for a call invitation."
allowed-tools: "Read, Bash"
trigger: conversational
version: 1.0
effort: medium
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Lead Nurture

## Purpose

Keep leads warm and moving through the pipeline when they are not yet ready to book but have shown genuine interest.

---

## Outcome

A nurture touchpoint that delivers value, maintains relationship, and moves the lead toward readiness without pressure.

---

## Best-Practice Benchmark

Provide value proportional to where they are in their journey. Not-ready leads need content that builds belief, not offers that build resistance.

---

## Decision Criteria

- How long ago did they first engage?
- What content have they interacted with?
- What is their specific stated struggle?
- Are they cold or warm right now?

---

## Execution Steps

1. Identify lead's current belief gap
2. Select content angle that closes that gap
3. Deliver value with no ask attached
4. Reference something specific they said
5. Leave door open naturally

---

## Failure Modes

- Making an offer in a nurture message
- Sending generic content not tied to their situation
- Nurturing indefinitely without ever asking
- Losing track of where they are in the journey

---

## Measurement

- Re-engagement rate from nurture messages
- Time from first contact to booking
- Nurture-to-book conversion rate

---

## Improvement Opportunities

Build content library matched to specific belief gaps. Test value-only vs soft-ask nurture messages.

---

## Gotchas

- Nurture is not an indefinite state. A lead that has been in nurture for 30+ days without advancing needs to be disqualified or directly asked. Indefinite nurture is a CRM graveyard.
- Generic nurture ("thought you'd find this interesting") signals that you're treating them as a prospect, not a person. Every nurture message must reference something specific to their situation.
- Never make an implicit ask in a nurture message. If you're ending with "let me know if you want to talk," you've blurred the boundary between nurture and close. Nurture has no ask. Close has a direct ask. Separate them.
- The belief gap must be identified before the nurture message is written. Sending value content that doesn't address their specific gap is not nurture — it's broadcasting.
- Content that performs well publicly is not automatically good nurture content. Public content is designed for strangers. Nurture content is for someone who already knows you and is working through a specific hesitation.
