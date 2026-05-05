---
name: generate-content-script
description: "Turn a content angle into a complete filming brief and caption. Use after a content angle is approved."
allowed-tools: "Read"
version: 1.0
effort: medium
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Generate Content Script

## Purpose
Turn an approved angle into a complete filming brief The founder can film from immediately.

## Outcome
Complete package: hook (exact words), filming brief (sequence), caption (ready to post), CTA (exact words), platform format, mood direction.

## Decision Criteria
- Run after content angle is selected and approved
- One brief per content piece
- Do not run without an approved angle

## Execution Steps
1. Take the approved angle and hook direction
2. Write the exact hook — first line spoken on camera.
   Must create curiosity, friction, or pattern interruption. Must be specific to the ICP.
3. Build filming brief:
   - Opening (the hook, spoken)
   - Body: 3-4 beats in sequence
   - The turn: counterintuitive insight
   - Close: what this means for the viewer
4. Write caption:
   - First line = hook (same as filming hook)
   - 2-3 lines expanding the idea
   - CTA (exact words, specific action)
5. Specify platform and format:
   - Vertical short / horizontal long
   - Duration guidance
   - Energy: calm/intense/direct/personal

## Failure Modes
- Vague hook that could be anyone's content
- Brief that requires the founder to think while filming
- Caption without a specific CTA
- Missing the Vigilante Architect tone check

## Measurement
- Filming time from brief (target: under 1 hour)
- Hook performance in first 3 seconds
- CTA conversion rate (DMs received)


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
