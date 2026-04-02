---
name: objection-handling
description: "Identify and respond to specific objections that prevent Initiate Arena leads from booking or closing — run when a prospect raises any objection during a sales conversation or call."
allowed-tools: "Read, Bash"
trigger: conversational
version: 1.0
effort: medium
---

!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
try:
    from eos_ai.context import load_context_from_env
    ctx = load_context_from_env()
    print(f'Stage: {getattr(ctx,\"stage\",\"?\")}')
    print(f'ICP: {getattr(ctx,\"icp\",\"Men 18-25\")}')
    print(f'Constraint: {getattr(ctx,\"binding_constraint\",\"leads\")}')
except Exception as e:
    print(f'Context: {e}')
"`


# Skill: Objection Handling

## Purpose

Identify and respond to the specific objections that prevent Initiate Arena leads from booking or closing.

---

## Outcome

A response that addresses the real fear behind the stated objection, reframes it, and moves the conversation toward a decision.

---

## Best-Practice Benchmark

Hormozi: the real objection is never the stated one. Feel/felt/found is dated. Use: acknowledge → isolate → test → answer. The objection is never the blocker — insufficient certainty is the blocker. Your job is to build certainty, not defeat resistance.

---

## Decision Criteria

- What is the stated objection?
- What is the likely real fear beneath it?
- Is this a real objection or a brush-off?
- Has this objection appeared twice (two clear nos = stop)?

---

## Execution Steps

1. Acknowledge the objection without resistance — never argue with the words
2. Isolate: "Is that the only thing holding you back, or is there something else?"
3. Test: If they say yes, you have the real one. If no, find what's beneath it.
4. Answer the fear, not the words — use specific evidence or their own language back at them
5. Return to the decision point with a direct close, not a question

**Specific objection responses:**

"I need to think about it."
→ "Totally fair. What specifically would you need to think through? Let's think through it together right now so you have everything you need."
→ Real fear: not enough certainty. The ask: help them think, don't give them space to go cold.

"I can't afford it."
→ "If money weren't a factor, would this be a yes for you?" [wait]
→ If yes: "Then this is a priorities conversation, not a budget conversation. What are you currently spending on things that aren't moving you forward?"
→ If no: they're not bought in yet — go back to the pain diagnosis.
→ Real fear: fear of wasting money. The ask: confirm the value before the price makes sense.

"I need to talk to my partner/wife."
→ "That makes total sense. What would they want to know? Let me give you exactly what you'd need to have that conversation confidently."
→ Real fear: social risk. The ask: arm them, don't dismiss them.

"I need to see results first."
→ "That's exactly why the program is 90 days — you'll see results before the 30-day mark. The structure is designed so you're not waiting until the end to know if it's working."
→ Real fear: uncertainty about whether it actually works. The ask: front-load the evidence.

"I've tried things before and they didn't work."
→ "What specifically didn't work about them?" [listen]
→ "So the issue wasn't you — it was a system that wasn't built for your situation. What would need to be different this time for it to actually stick?"
→ Real fear: identity threat (I'm the kind of person who fails). The ask: separate the person from the past system.

---

## Failure Modes

- Arguing against the stated objection (never fight the words)
- Giving more information when a question is what's needed
- Skipping the acknowledge step — it signals you didn't hear them
- Treating every objection as solvable — two clear nos means stop
- Answering "I can't afford it" with payment plans before confirming they want it

---

## Measurement

- Objection-to-booking conversion rate per objection type
- Which objections convert most often (build from this)
- Which objections consistently signal unqualified leads (stop pursuing)

---

## Improvement Opportunities

Build objection library from real DM and call data. Track which exact responses convert vs lose. Flag when the same objection appears in 3+ conversations — it signals a positioning gap in the offer, not a sales gap.

---

## Gotchas

- "I'll think about it" is almost never about thinking — it's about not feeling certain enough. Giving them space almost always means losing them.
- "I can't afford it" followed by a yes to "if money weren't a factor" means you have a value framing problem, not a pricing problem. Don't drop the price — build the value.
- Never answer an objection before isolating it. If you answer the wrong objection, they have two objections now.
- Silence after your response is not the prospect deciding against you — it's them processing. Hold the silence.
- The moment you get defensive or explain yourself, you've broken the dynamic. Stay curious, not defensive.
- Don't run this skill if the person has given two clear signals they're out. Respect the no. A disqualified lead treated with dignity becomes a referral.
