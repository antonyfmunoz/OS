---
name: call-to-close
description: "Guide a sales conversation from the discovery phase through to a closed sale for the active offer at its price point — run on every qualified sales call."
allowed-tools: "Read, Bash"
trigger: conversational
version: 1.0
effort: medium
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Call to Close

## Purpose

Guide a sales conversation from the discovery phase through to a closed sale for the active offer at its price point.

---

## Outcome

A closed sale or a clear next step. Never ends with "I'll think about it" without a specific follow-up commitment.

---

## Best-Practice Benchmark

Alex Hormozi $100M Offers close framework:
1. Diagnose the problem they can't solve
2. Agitate the cost of staying stuck
3. Present the solution as the obvious choice
4. Handle objections before they arise
5. Make the ask directly and shut up

---

## Decision Criteria

- Has the lead been qualified (ICP fit confirmed)?
- Has the problem been clearly established?
- Has the cost of inaction been articulated?
- Is the ask being made directly?

---

## Execution Steps

1. Open with their specific situation
2. Diagnose: what have they tried, what failed
3. Agitate: what does staying stuck cost them
4. Present the active offer as the specific fix
5. Price anchor: what would it cost not to fix it
6. Ask directly: "Are you ready to start?"
7. Handle one objection maximum
8. Close or schedule follow-up

---

## Failure Modes

- Presenting before diagnosing
- Not making a direct ask
- Accepting "I'll think about it" as an answer
- Talking after making the ask (silence wins)

---

## Measurement

- Show rate → close rate
- Average call length for closes vs no-closes
- Revenue per call

---

## Improvement Opportunities

Record close rate by opener type. Track which discovery questions predict closes.

---

## Gotchas

- The most common failure: presenting before the prospect has fully articulated their own pain. If they can't say the problem in their own words, the solution won't land.
- Never skip the cost-of-inaction step. Without it, the offer price feels like a cost. With it, the offer price feels like relief.
- Silence after "Are you ready to start?" is the close working. The first person to speak loses this moment. Hold it.
- Don't handle more than one objection per call. If they raise a second after the first is answered, the problem is the diagnosis, not the objections.
- Price should be revealed after the value frame is set, never before. Sequence: pain → cost of staying stuck → solution → price.
- "Are you ready to start?" is the ask. Not "Does that sound good?" Not "What do you think?" The specific language matters.
- If a call goes over 45 minutes without a decision, something went wrong in the diagnosis phase. Length is not persuasion.
- Never book a follow-up call without a specific decision point attached to it — "Let's talk again" without "and at that point you'll decide yes or no" is not a next step, it's a delay.
