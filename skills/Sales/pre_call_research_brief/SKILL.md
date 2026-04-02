---
name: pre-call-research-brief
description: "Generate a complete brief on a prospect before every sales call — run after a call is booked and before the call begins."
allowed-tools: "Read, Bash"
version: 1.0
---

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
   - Offer aware — knows about Initiate Arena specifically
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
