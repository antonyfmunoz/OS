---
type: workflow
department: sales
status: active
owner: Antony
trigger: Lead booked via Calendly or manually moved to Booked stage
outcome: Closed, Follow-up, or No-show logged
tags:
  - workflow
  - sales
  - meeting
---
# Sales Call Workflow

## Purpose
Move a booked lead from call confirmed to outcome logged. AI handles all pre/post automation. Founder focuses on the conversation.

## Trigger
Lead moved to Booked stage in pipeline, or `/meeting start [lead-name]` typed in Telegram.

## Inputs
- Lead name (Instagram handle)
- DM history (from knowledge graph)
- ICP score and archetype (from Neon)

## Steps
1. Lead booked via Calendly webhook → moves to Booked stage in Pipeline.md
2. 1h before call: pre-meeting automation fires (see Meeting Facilitation below)
3. Founder starts call with agenda prepared
4. Founder activates meeting mode: `/meeting start [lead-name]`
5. Call happens — AI on standby for real-time queries
6. Founder ends session: `/meeting end`
7. Post-meeting automation fires within 5 min
8. Founder logs outcome: `/outcome closed | noshow | follow_up`

## Output
- Meeting summary in Telegram
- Follow-up message draft in Telegram
- CRM lead file updated with meeting notes
- Outcome logged to Neon (RLHF signal)

## Failure Points
- Pre-meeting agenda arrives too late (calendar event already exists — agent skips)
- Voice transcription fails (no audio sent — summary will be empty)
- Follow-up draft not actioned by founder

## Improvements
- Connect Calendly webhook to auto-trigger pre-meeting at T-60min
- Add outcome → email send automation for follow_up/closed outcomes
- Build archetype-specific close scripts into the agenda generator

---

## Meeting Facilitation

### Pre-Meeting Automation (AI executes on /meeting start)

**Step 0a — Calendar event creation**
  Agent: Operations Agent
  Tool: `gws_connector.create_calendar_event()`
  - Creates event if not already scheduled
  - Adds Google Meet link automatically
  - Sets 10-min popup reminder for founder
  - Invites lead email if available in lead file

**Step 0b — Agenda preparation**
  Agent: Sales Agent (closer sub-agent)
  Output: structured agenda sent to founder via Telegram on `/meeting start`:

  ```
  CALL AGENDA: [Lead Name]
  ICP Score: [score]
  DM history: [last conversation summary]
  [AI-generated call guidance: opener, problem to diagnose, objection, close move]
  Meeting link: [Google Meet URL]
  ```

---

### During Meeting (voice_interface active)

**Step 3a — Activate meeting mode**
  Founder types: `/meeting start [lead-name]`
  System:
  - Starts VoiceInterface session
  - Transcription begins on voice messages
  - Lead profile loaded into context
  - Pre-meeting automation runs immediately

**Step 3b — Real-time assistance available**
  Founder can query mid-call (text only, silent — lead doesn't hear):
  - `score [lead]` → ICP score from knowledge graph
  - `history [lead]` → full DM history summary
  - `/decide [question]` → structured decision analysis
  - Any natural language → routes through CEO agent

  All responses are text only — not spoken aloud.

**Step 3c — End meeting**
  Founder types: `/meeting end`
  Triggers post-meeting automation chain immediately.

---

### Post-Meeting Automation (AI executes on /meeting end)

**Step 8a — Summary generation**
  `voice_interface.end_meeting_session()` called automatically.
  Output sent to Telegram:
  - Summary (2-3 sentences)
  - Decisions made
  - Action items with owners
  - Next steps

**Step 8b — Outcome logging prompt**
  AI sends to Telegram immediately after summary:
  ```
  CALL OUTCOME — @[lead]
  Reply with one command:
    /outcome closed 1.0 [notes]
    /outcome follow_up 0.5 [notes]
    /outcome noshow 0.0
  ```

**Step 8c — Follow-up draft**
  Agent: Sales Agent (follow_up_sequencer sub-agent)
  Skill: `follow_up_sequence`
  Input: meeting summary + next steps
  Output: personalized follow-up message drafted and sent to Telegram
  Founder copies and sends manually (or `/approve [id]` if gateway-queued)

**Step 8d — CRM update**
  AI appends meeting notes to `03_CRM/Leads/lead_[username]_*.md`:
  - Meeting summary
  - Action items
  - Next steps
  - Timestamp

**Step 8e — Meeting summary email (future)**
  Agent: Operations Agent
  Tool: Gmail via GWS connector
  Triggered by: `/outcome closed` or `/outcome follow_up`
  Content: what was discussed, next steps, any resources mentioned
  Status: deferred until `gws_connector.send_email()` is implemented

---

### Team Meeting Support

**`/standup`** — AI-generated structured team standup
  - Pipeline state across all stages
  - Active task queue per department (Sales, Research, Marketing, CS, Ops)
  - Per-department: completed yesterday / focus today / blockers
  - Compiled into a tight briefing
  - Logged to Neon as `standup` event

**`/review`** — Weekly business review
  - Portfolio Advisor generates venture-level KPIs and advisory
  - Strategy Engine identifies this week's binding constraint
  - Capital allocation analysis
  - Pending high-priority decisions from task queue
  - Pipeline snapshot
  - Logged to Neon as `weekly_review` event
