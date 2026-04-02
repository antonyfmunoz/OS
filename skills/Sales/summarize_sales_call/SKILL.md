---
name: summarize-sales-call
description: "Convert a sales call transcript or notes into a structured CRM summary that informs next steps — run immediately after every sales call."
allowed-tools: "Read, Bash"
version: 1.0
---

# Skill: Summarize Sales Call

## Purpose

Convert a sales call transcript or notes into a structured CRM summary that informs next steps.

---

## Outcome

A structured summary appended to the lead file — outcome, pain in their words, situation, objections, and one clear next action with owner.

---

## Best-Practice Benchmark

The pain field must use their exact words. Their language, not your interpretation. A summary that paraphrases their pain into coaching language has already lost the intelligence value.

---

## Decision Criteria

- Mark `booked` if: they committed to next step on the call
- Mark `follow-up needed` if: interested but objections unresolved or decision pending
- Mark `disqualified` if: no real pain, no fit, or explicit rejection
- The next action must be assigned — if owner is unclear, it defaults to AFM

---

## Execution Steps

1. Load call transcript or notes from: direct input or `03_CRM/Conversations/`
2. Read in full — do not skim
3. Extract core information:
   - Pain expressed (use their exact language)
   - Current situation
   - Desired outcome
   - Objections raised
   - Call outcome: booked / follow-up needed / disqualified
4. Assess ICP fit: frustration present? self-awareness present? ownership language present?
5. Identify the single most important next action
6. Append structured summary to lead file:
   - `outcome:` booked | follow-up | disqualified
   - `pain:` their primary expressed pain (their words)
   - `situation:` where they are now
   - `objections:` what came up
   - `next_action:` what happens next and who owns it

---

## Failure Modes

- Paraphrasing their pain into interpreted coaching language
- Leaving `next_action` blank or vague ("follow up with them")
- Missing objections that were soft or implicit
- Over-classifying as `booked` when they said "maybe" or "let me think"
- Ignoring disqualification signals because the call felt positive

---

## Measurement

- Show rate: % of `booked` outcomes that actually show to next step
- Objection accuracy: do the documented objections match what comes up in the follow-up?
- Conversion rate from `follow-up needed` to `booked` within 7 days

---

## Improvement Opportunities

- Build an objection library from recurring patterns across summaries
- Track which objections are most commonly overcome vs. most commonly terminal
- Use pain field data to refine ICP targeting and content strategy
