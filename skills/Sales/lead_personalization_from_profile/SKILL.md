---
name: lead-personalization-from-profile
description: "Extract one specific signal from a single lead's profile to anchor the outreach message in their reality — run for high-ICP-score leads where a personalized approach is warranted."
allowed-tools: "Read, Bash"
version: 1.0
effort: high
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Lead Personalization From Profile

## Purpose
Extract one specific signal from a single lead's profile to anchor the outreach message in their reality.

## Outcome
The opener reads like it was written specifically for this person, not from a template.

## Decision Criteria
- Single-lead outreach (not batch)
- When ICP score is high and a personalized approach is warranted

## Execution Steps
1. Review the lead's Instagram profile:
   - Most recent post topic and caption
   - Bio keywords and self-description
   - Content they engage with (from ICP data)
   - Highlights that reveal identity or aspiration
2. Identify ONE specific signal — the most specific, most recent, most relevant to the offer
3. Anchor the opener in that signal:
   - "I saw you posted about X" or "Your bio says Y"
   - Never "I noticed your content" (too vague)
4. Connect the anchor to the pain the ICP experiences — not the offer
5. End with a curiosity-opening question, not a pitch

## Failure Modes
- Using two signals instead of one (reads as surveillance, not observation)
- Connecting the signal to the offer rather than to the pain
- Using a signal older than 30 days
- Writing a pitch instead of opening a conversation

## Measurement
- Reply rate of personalized vs batch openers for the same ICP segment


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
