---
name: generate-outreach-from-intel
description: "Turn market intelligence insights into high-converting DM outreach messages that mirror ICP language — run after a market intelligence report is generated to create the outreach batch for the next cycle."
allowed-tools: "Read, Bash"
trigger: scheduled
version: 1.0
effort: high
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


# Skill: Generate Outreach From Market Intelligence

## Purpose

Turn market intelligence insights into high-converting DM outreach messages that mirror ICP language and trigger honest conversations.

---

## Outcome

A ready-to-use set of DM openers, follow-up questions, reframes, and call invitations — grounded in real ICP language, saved to the CRM.

---

## Best-Practice Benchmark

Outreach that converts opens pain discovery first, not the offer. The message should feel like the sender understands the prospect's private experience — not like a template.

---

## Decision Criteria

- Use opener if: no prior contact with this lead
- Use follow-up question if: conversation is active but stalled on discovery
- Use reframe if: prospect is deflecting or blaming externals
- Use call invitation if: pain is confirmed, ownership language present, momentum is positive

---

## Execution Steps

1. Load market intelligence reports from: `07_Knowledge/Reports/Market_Reports`
2. Load ICP language patterns from: `07_Knowledge/ICP`
3. Extract from reports: frustrations, identity conflicts, emotional triggers, common language patterns
4. Generate 10 DM openers designed to start conversations
   - Example: "Random question — do you ever feel like you're capable of more but your weeks just disappear?"
5. Generate 10 follow-up questions designed to uncover pain
   - Example: "What usually pulls you away when you try to focus?"
6. Generate 5 reframes that connect their struggle to structure
   - Example: "It sounds like the real issue isn't motivation — it's that your week doesn't have structure protecting your time."
7. Generate 5 natural call invitations
   - Example: "If you're open to it, I'm building something for guys dealing with exactly this. Want to see if it's a fit?"
8. Save output to: `03_CRM/Outreach_Messages/outreach_messages_YYYY-MM-DD.md`

---

## Failure Modes

- Generic language that could apply to any audience → reject; must use exact ICP phrases from the intelligence
- Pitching the offer in the opener → reject; openers open conversations, not sales
- Invented frustrations not backed by signal data → reject; all output must trace to a real insight
- Follow-up questions with yes/no answers → reject; must require a real answer

---

## Measurement

- Reply rate per opener batch (track in `services/opener_stats.json`)
- Conversation advancement rate: what % of opener replies reach pain discovery stage
- Call booking rate from batches using this output

---

## Improvement Opportunities

- A/B test openers across different frustration categories
- Tag each message with the ICP insight that inspired it to close the feedback loop
- Retire openers with <10% reply rate after 20 sends

---

## Gotchas

- Generic openers that don't trace to a specific ICP insight will sound like templates. If the opener could apply to any 22-year-old, it's not specific enough.
- "Are you interested in…" and "I help people like you…" are disqualifying phrases. If they appear in any generated output, reject the batch.
- Call invitations must only appear after pain is confirmed and ownership language is present. Generating call invitations as openers is a mistake — they will not convert at this stage of the conversation.
- The intelligence driving this skill must be from the current cycle (< 30 days). If the most recent market report is older than 30 days, flag that before generating. Stale intelligence produces stale outreach.
- Follow-up questions must require a real answer — not yes/no. "Do you struggle with discipline?" is a yes/no question and it's useless for discovery.
- Don't generate all 10 openers from the same frustration category. Spread across the top 3-4 patterns to maximize the batting average across diverse segments of the ICP.
