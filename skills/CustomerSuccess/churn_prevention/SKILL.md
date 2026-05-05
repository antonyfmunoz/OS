---
name: churn-prevention
description: "Identify disengaging the active offer clients 4-6 weeks before they churn and intervene with a specific, personalized action — triggered when a client goes 7+ days without interaction or misses 2+ consecutive check-ins."
allowed-tools: "Read, Bash"
version: 1.0
effort: high
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# churn_prevention

## Purpose
Identify disengaging the active offer clients 4-6 weeks before they churn and intervene with a specific, personalized action — not a generic check-in. 70% of churn is predictable. The signals are behavioral, not stated. Clients do not say "I'm about to quit." They go quiet. Silence is the loudest signal.

## Outcome
An engagement monitoring protocol that flags at-risk clients by behavior, plus a tiered intervention playbook matched to disengagement severity. The output is a prioritized intervention list with specific actions, not a blanket "check-in with everyone."

## Best-Practice Benchmark
The research on B2C program churn is consistent: the #1 predictor of dropout is a 7+ day content gap in the first 30 days. The #2 predictor is skipping a scheduled touchpoint without re-engagement within 48 hours. By the time a client tells you they're leaving, the decision is already made. Intervention must happen while they are still in the pre-churn drift phase — where re-engagement is still emotionally accessible.

## Decision Criteria
When monitoring engagement:
- Has a client gone 7+ days without any interaction? (Tier 1 alert)
- Have they missed 2+ consecutive check-ins or assignments? (Tier 2 alert)
- Are their messages getting shorter and less specific? (Tier 2 alert)
- Have they stopped sharing wins or asking questions? (Tier 1 alert)
- Did they have a hard moment in intake and haven't referenced it since? (Tier 2 alert)
- Are they engaging but only consuming, never responding? (Tier 1 alert — passive drift)

## Execution Steps
**Monitoring (ongoing)**
1. Track last-interaction date for every active client — flag any with 7+ day gap
2. Track assignment completion rate — flag anyone who misses 2+ in a row
3. Review message quality: shorter, vaguer, fewer questions = disengagement signal
4. Cross-reference intake form: identify the specific fear or obstacle they named at start

**Tier 1 Intervention (7-10 day silence, first missed assignment)**
5. Send a voice note or personal DM — not a template
6. Reference something specific: "Last time we talked you mentioned [X]. Where are you with that?"
7. Give them one tiny action — something completable in 5 minutes
8. Do not acknowledge the silence as a problem — acknowledge them as a person
9. Create a micro-win opportunity: make it easy to say yes to something small

**Tier 2 Intervention (14+ day silence, pattern of missed assignments)**
10. Escalate to a direct honest conversation — not a soft nudge
11. Name what you observe: "I've noticed you've been quieter. That usually means something shifted. What's going on?"
12. Offer a re-entry point: "Let's reset your week. One thing. What's the one thing you'll do by Friday?"
13. Identify the real obstacle — not the stated reason
14. If they express doubt: surface the original commitment they made when they paid

**Tier 3 Intervention (30+ day ghost, no response to previous outreach)**
15. One final message: honest, no guilt, no pitch
16. "You invested in yourself. That was real. The door stays open. When you're ready, I'm here."
17. Log the outcome and the last engagement date for pattern analysis
18. Do not chase further — it costs the relationship

## Failure Modes
- Generic check-ins ("just checking in!") — too easy to ignore, signals you don't know them
- Waiting until a client says they want to quit — too late, decision is made
- Reaching out in response to silence with an offer or upsell — reads as transactional
- Treating all disengaged clients the same — ignores archetype and intake context
- Reacting to silence with intensity — pressure accelerates churn
- Not logging intervention outcomes — repeats the same failures

## Measurement
- At-risk detection rate: % of eventual churners who were flagged before leaving
- Intervention recovery rate: % of Tier 1/2 interventions that re-engage the client
- Churn prediction window: average days before churn that disengagement was first detected
- 90-day completion rate: % of clients who complete the full the active offer program
- Silence-to-intervention time: average hours between 7-day gap detected and outreach sent

## Improvement Opportunities
- After 20+ clients: build an archetype-specific disengagement fingerprint (when do different types go quiet?)
- Track which re-entry prompts produce the most durable re-engagement
- Identify if there is a specific week in the program where disengagement spikes and preemptively adjust the content or touchpoint at that week
- Feed churn data back into intake screening — are there signals at purchase that predict churn?


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
