---
name: proof-promise-plan-close
description: "Run the Proof-Promise-Plan close framework at the decision moment of a sales conversation — run after diagnosis is complete and objections are resolved."
allowed-tools: "Read"
trigger: conversational
version: 1.0
effort: medium
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Proof-Promise-Plan Close

## Purpose

Run a structured close at the decision moment of a sales conversation. Moves the prospect from "interested" to "yes" by giving them proof it works, a specific promise for their situation, and an exact plan for what happens next.

---

## Outcome

A closed sale, or a clear next-step commitment with a specific decision timeline attached. Never ends with "think it over" as a final state.

---

## Best-Practice Benchmark

Close structure: give people a reason to believe (proof), a specific outcome to want (promise), and an exact path that removes friction (plan). The close isn't persuasion — it's removing the remaining uncertainty that's preventing a decision.

---

## Decision Criteria

- Has diagnosis been completed? (They've articulated their pain in their own words)
- Has cost-of-inaction been established?
- Are remaining objections resolved or isolated?
- Is this the right moment to run the close, or is there still unresolved uncertainty?

Only run this skill when the diagnostic phase is complete. Running the close before diagnosis fails.

---

## Execution Steps

**Step 1 — PROOF**
Share a concrete result that demonstrates the program works for someone in their situation.
- Use a real client result if one exists. Use a structured hypothetical only if no real case exists.
- Match the proof to their specific situation. Not generic results — their specific pain.
- Example: "Someone who started in the same place you're describing — constantly starting over, losing momentum after week two — hit a 60-day unbroken execution streak inside the first 90 days."
- Keep it one sentence. Don't over-explain. Let it land.

**Step 2 — PROMISE**
State a specific outcome for THIS person based on their situation as they described it.
- Not a generic program promise. Their specific transformation based on what they told you.
- Example: "Based on what you've described — the pattern of starting and stopping, the weeks disappearing — what the active offer is specifically built to break is that cycle. By day 30 you'll have more consistent execution than you've had in the last year."
- Be specific. Be direct. Don't hedge.

**Step 3 — PLAN**
Walk them through exactly what happens next. Eliminate uncertainty about the path.
- Step 1: "You'd get the link now and complete the registration today."
- Step 2: "You'd get access to the program immediately — the onboarding takes about 20 minutes."
- Step 3: "The first week is the foundation phase — building the system before the execution starts."
- Make it feel inevitable and frictionless, not complex.

**Step 4 — Handle the pause**
After laying out the plan, make the direct ask:
"You ready to get started?"
Then stop. Hold the silence. The next person to speak loses this moment.
Do not fill the silence. Do not add features. Do not offer alternatives.

**Step 5 — If they pause and it stretches**
If silence extends beyond 10 seconds and they haven't spoken: "What's coming up for you right now?"
This invites the real blocker to surface without pressure.

**Step 6 — Next step is always the link**
When they say yes: "Let me send you the link right now."
Not: "Great, I'll follow up with details."
Not: "What do you think about the payment options?"
The immediate next step is the link. Send it while they're present.

---

## Failure Modes

- Running the close before diagnosis is complete — the promise won't land because it isn't specific to their situation
- Making the promise generic ("you'll achieve your goals") rather than tied to what they said
- Filling the silence after the ask with additional features or reassurance
- Saying "let me send you details later" instead of sending the link immediately
- Offering alternatives at the close moment ("or you could try X instead") — this reopens uncertainty
- Running this skill on an unqualified lead — close framework only works when the lead is a real fit

---

## Measurement

- Proof-Promise-Plan close rate vs. standard close rate
- Average time from plan delivery to "yes"
- Rate of immediate link sends vs. delayed follow-up

---

## Improvement Opportunities

- Build a proof library as real client results accumulate. Each result indexed by pain type for fast retrieval.
- Track which specific proof stories convert highest by ICP segment.
- Refine promise language as ICP language patterns deepen from intelligence cycles.

---

## Gotchas

- The PROOF must match their situation. Generic social proof ("hundreds of people have done this") is weaker than a single specific case that mirrors their experience exactly.
- The PROMISE must use language they used. If they said "I keep losing momentum," the promise should reference "momentum" — not "consistency" or "discipline." Mirror their language.
- If you send the link and they go silent for more than 48 hours, hand to `follow_up_sequence`. The close window is still open but needs a different angle — don't re-run this skill.
- The plan should feel short and frictionless. Three steps maximum. If the plan you're describing takes more than a minute to explain, it's too complex and you're creating new friction.
- This skill runs after objections are handled, not before. If an objection is still active when you run this, the prospect will use the close moment to raise it again.