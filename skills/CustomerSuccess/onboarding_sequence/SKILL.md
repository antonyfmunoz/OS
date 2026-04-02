---
name: onboarding-sequence
description: "Move a new Initiate Arena client from payment confirmation to their first visible win within 7 days — triggered immediately when payment is confirmed."
allowed-tools: "Read, Bash"
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


# onboarding_sequence

## Purpose
Move a new Initiate Arena client from payment confirmation to their first visible win within 7 days — without overwhelming them. One action at a time. Personal contact within 1 hour of payment. The moment someone pays is the moment their buyer's remorse clock starts. Speed and specificity at that moment converts payment into commitment.

## Outcome
A step-by-step 7-day onboarding flow: who does what, when, and what the client should experience at each stage. Day 1 action is personal, not automated. Day 3 is a real check-in. Day 7 is a milestone moment that makes them feel the decision was right.

## Best-Practice Benchmark
The critical insight: most churn starts at onboarding. Clients who feel welcomed, clear on their first action, and heard in the first 48 hours have 3x retention vs. those dropped into a course portal. The wall of content is the enemy. Give them one thing. Completion of that one thing is the first win. First win creates momentum. Momentum creates retention.

## Decision Criteria
- Was personal contact made within 1 hour of payment?
- Does the client know exactly one action to take right now — not three?
- Is the Day 3 check-in specific to their intake information — not generic?
- Has the client achieved something measurable by Day 7?
- Does the onboarding feel like a coach is watching, not a system running?

## Execution Steps
**Hour 0-1 (Payment confirmation)**
1. Personal DM or voice note within 60 minutes — not a template, reference their name and why they joined
2. Confirm access to course portal (Notion)
3. Give one instruction: "First thing: complete the intake form — link here. That's your only job today."

**Day 1 (within 24 hours)**
4. Follow up on intake form completion — if done, acknowledge specifically
5. If not done: send a 2-line nudge, not a lecture
6. Set expectation: "We start properly on Day 2 — I want to know where you're at first"

**Day 2**
7. Send the Week 1 focus — one module, one framework, one identity shift to anchor on
8. Do not dump the entire curriculum — one thing only
9. Assign the Day 2 task: specific, measurable, completable in under 30 minutes

**Day 3 (Check-in)**
10. Real check-in via DM — ask how the Day 2 task went
11. Address friction immediately: if they got stuck, find out where
12. Do not ask "how's it going" — ask "did you complete X? What stopped you if not?"

**Day 5**
13. Share a win from another client (anonymized) relevant to where they are in Week 1
14. Reinforce identity: "You're the kind of person who does this. Most don't."
15. Preview what Day 7 looks like — build anticipation

**Day 7 (Milestone)**
16. Check-in: confirm they've completed Week 1 module
17. Celebrate the specific thing they did — not generic "great job"
18. Introduce Week 2: one sentence on what changes now
19. Ask for one piece of feedback: "What was the hardest moment so far?"
20. Log the feedback for product improvement

## Failure Modes
- Generic welcome message that looks automated — destroys trust immediately
- Sending the full curriculum on Day 1 — overwhelms and creates decision paralysis
- No contact between payment and Day 3 — silence reads as abandonment
- Day 3 check-in that asks "how's everything going?" — too vague to surface real friction
- Skipping the Day 7 milestone — misses the momentum window
- Not logging feedback — wastes the most honest data point you'll ever get

## Measurement
- Hour-1 contact rate: % of new clients who receive personal outreach within 60 minutes
- Day-2 task completion rate: % who complete the first assigned action
- Day-7 milestone rate: % who complete Week 1 and report feeling on track
- 30-day retention: % still active and engaged at the end of Month 1
- Early churn rate: % who disengage in first 14 days

## Improvement Opportunities
- Analyze Day 3 check-in responses to identify which intake profiles need more early support
- Build archetype-specific onboarding variations once you have 10+ clients (patterns emerge)
- Track which Day 2 tasks have highest completion rates and make those the standard
- Feed Day 7 feedback into course content updates — clients reveal real friction
- Identify the single onboarding moment most correlated with 90-day completion
