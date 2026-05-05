---
name: pre-call-research-brief
description: "Generate a complete brief on a prospect before every sales call — run after a call is booked and before the call begins."
allowed-tools: "Read, Bash"
trigger: conversational
effort: high
context: fork
version: 1.0
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Pre-Call Research Brief

## Purpose
Generate a complete brief on a prospect before every sales call. Who they are, what they said in DMs, their ICP score, their expressed pain in their own words, their likely objections, their stage of awareness.

## Outcome
Sales Agent walks into every call with full context. Never cold. Never generic.

## Decision Criteria
- A call is booked
- Run this skill before the call, not during

## Execution Steps
1. Pull full DM conversation history for this prospect from memory
2. Pull their ICP score and scoring rationale
3. Extract exact phrases they used to describe their pain — quote verbatim
4. Identify their stage of awareness:
   - Problem aware — knows something is wrong, doesn't know the solution
   - Solution aware — knows solutions exist, hasn't chosen one
   - Offer aware — knows about the active offer specifically
5. Predict top 2 objections based on their language and profile
6. Generate one-page brief:
   - Who they are (name, context, how they found us)
   - Their pain in their words (exact quotes)
   - Their awareness stage
   - ICP fit score and key signals
   - Likely objections and framing
   - Recommended opening question

## Failure Modes
- Running from memory without checking DM history
- Using paraphrased pain instead of exact quotes
- Skipping the awareness stage assessment
- Generating the brief during the call instead of before

## Measurement
- Show rate on calls with brief vs without brief
- Close rate on calls with brief vs without brief

---

## Gotchas

- The brief must be generated before the call — not reviewed during it. Running this on your phone while on the call defeats the purpose.
- Exact pain quotes from DMs are the most valuable part of the brief. If the DM history doesn't exist or is sparse, the recommended opening question becomes critical — start the call creating the context you're missing.
- The awareness stage assessment changes the entire opening strategy. Problem-aware prospects need their pain validated before the solution is mentioned. Offer-aware prospects need specifics about fit and ROI, not education.
- Objection predictions are hypotheses, not guarantees. If a different objection surfaces on the call, don't abandon the prepared response — but adjust to what's actually in front of you.
- A brief based on a DM conversation where you asked questions and they answered is a real brief. A brief based on an Instagram bio alone is a starting point, not a brief. Know which you're working with.
