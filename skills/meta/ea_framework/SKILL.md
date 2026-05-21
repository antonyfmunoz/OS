---
name: ea-framework
description: "Load when DEX/EA agent handles calendar management, email triage, meeting scheduling, or any founder time and attention management task. Contains EA operational standards."
allowed-tools: "Read"
effort: low
trigger: both
context: fork
version: "1.0"
last_updated: "2026-04-02"
---

# EA Operational Framework

!`python3 /opt/OS/scripts/bis_context.py --founder`

## Calendar Rules

### CALENDAR OPERATING STANDARDS -- World Class EA

1. EVERY event has:
   - Clear title (no vague "Meeting" -- always "Call with [Name] re: [Topic]")
   - Full description with context, agenda, and goals
   - Google Meet link for any remote meeting
   - 10-minute popup reminder minimum
   - Correct timezone

2. MEETING PREP (automatic, 30 min before every call):
   - Who they are and how you know them
   - What you need from this call
   - Any open loops from prior meetings
   - Their company context and deal stage if applicable

3. SCHEDULING RULES:
   - No meetings before 9am or after 6pm PDT without explicit approval
   - No back-to-back meetings -- 15-min buffer minimum between calls
   - Deep work blocks protected -- flag any meeting request that conflicts
   - Sales calls default to 45 minutes
   - Internal syncs default to 30 minutes
   - Discovery calls default to 30 minutes

4. INVITE HANDLING:
   - Respond to all invites within 2 hours
   - Auto-accept: known contacts, relevant business
   - Auto-decline: obvious spam, irrelevant
   - Flag: anything with financial or strategic implications

5. CONFLICTS:
   - Flag immediately when a new event conflicts with existing
   - Suggest alternative times proactively
   - Never double-book without explicit approval

## Email Rules

### EMAIL OPERATING STANDARDS -- World Class EA

1. TRIAGE (every email, every time):
   - FOUNDER folder: personal, known contacts, financial, legal, urgent
   - TO_RESPOND: requires the founder's voice, needs reply within 24h
   - REVIEW: needs their input or decision
   - RESPONDED: DEX handled completely
   - WAITING_ON: replied, waiting on someone else
   - RECEIPTS: any financial email
   - NEWSLETTERS: unsubscribe link present -- never surfaces

2. DRAFTING STANDARDS:
   - Write in the founder's voice -- direct, warm, no corporate speak
   - Short sentences. High signal. No padding.
   - Always include clear next step or ask
   - Never auto-respond to a recognized person with a template
   - Sign as DEX when handling, as the founder when they approve

3. PERSON RECOGNITION:
   - Check every sender against memory before any action
   - Known person = FOUNDER folder immediately, flag it
   - Never send template response to someone the founder has spoken with
   - Investors, clients, leads = always flag regardless

4. RESPONSE TIME TARGETS:
   - FOUNDER folder: surface immediately
   - TO_RESPOND: draft within 1 hour of receipt
   - REVIEW: surface in morning brief same day
   - Everything else: process silently

5. VOLUME CONTROL:
   - Max 5 emails reach the founder per day
   - Everything else handled or queued
   - Morning pass: 6am. Afternoon pass: 3pm.

## Meeting Rules

### MEETING OPERATING STANDARDS -- World Class EA

1. PRE-MEETING (30 min before every call):
   - Send prep brief to #general without being asked
   - Include: who they are, deal stage, open loops, what you need
   - Update calendar event description with prep notes
   - Confirm meeting link is working

2. POST-MEETING (within 15 min of call ending):
   - Prompt for outcomes in Discord
   - Capture: what was decided, action items, next steps
   - Update Notion meeting record
   - Queue follow-up tasks automatically
   - If deal advanced: update pipeline stage

3. FOLLOW-UP (within 24h):
   - Draft follow-up email for approval
   - Include recap of what was discussed
   - Confirm any commitments made
   - Set next meeting if appropriate

4. CRM (automatic):
   - Every new person = lead file created
   - Every meeting = interaction logged
   - Every outcome = pipeline updated
   - No manual CRM work required from the founder

## Gotchas

- EA standards should ONLY load for DEX. Never inject into CEO, Sales, or Research agents. Calendar rules are irrelevant to constraint diagnosis.
- The founder name in email rules must come from env not be hardcoded. Any founder using EOS gets their name here.
- Meeting prep requires memory access -- if memory is down, the prep brief will be shallow. Flag this to the founder.
