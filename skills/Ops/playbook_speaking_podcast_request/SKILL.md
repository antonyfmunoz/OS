---
name: playbook-speaking-podcast-request
description: "Handle inbound speaking or podcast requests by qualifying the opportunity before escalating — triggered when any message invites Antony to speak, appear on a podcast, join a panel, or be interviewed."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
trigger: both
context: fork
---

# Skill: Playbook — Speaking or Podcast Request

## Name
playbook_speaking_podcast_request

## Domain
Operations / Personal Brand

## Purpose
Handle inbound speaking or podcast requests — qualify the opportunity before escalating.

---

## When to Use
Any invitation to speak at an event, appear on a podcast, join a panel, contribute to a publication, or be interviewed.

---

## Inputs
- sender_name
- show_or_event_name
- estimated_audience_size (if known)
- topic
- format (podcast/speaking/panel/interview/publication)
- is_paid (yes/no/unknown)

---

## Qualification Criteria
Route to Antony if ANY of:
- Audience > 10K or highly targeted to ICP
- Direct alignment with Vigilante Architect brand
- Known/respected host or organizer
- Paid opportunity

Decline gracefully if ALL of:
- Small/unclear audience
- Misaligned topic
- No clear brand value

---

## Process
1. Research the show/event and host
2. Estimate audience size and alignment
3. Apply qualification criteria
4. If qualified:
   a. Flag to Antony with research brief
   b. Draft holding response: "Thank you for the invitation. I've flagged this for Antony and will follow up within 48h."
5. If not qualified:
   a. Draft polite decline
   b. Queue for approval before sending

### Decline Template
Hi [Name],

DEX here, on behalf of Antony Munoz.

Thank you for the invitation — we appreciate you thinking of Antony. His calendar is fully committed through [timeframe] and he won't be able to participate in this one.

We'll keep your show/event in mind for the future.

Best,
DEX
On behalf of Antony Munoz

---

## Failure Modes
- Never confirm participation without Antony's approval
- Never decline a high-signal opportunity without flagging first
- Never send a decline for a paid opportunity without Antony's review

---

## Trust Level
ASSIST — qualify, draft, and recommend. Antony decides on qualified opportunities.

---

## Outputs
- Qualification assessment (qualified/not qualified + rationale)
- Discord flag with research brief if qualified
- Holding response or decline queued for approval


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
