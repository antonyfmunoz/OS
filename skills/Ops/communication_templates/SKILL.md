---
name: communication-templates
description: "Pre-approved voice-matched response templates for DEX. Use when drafting any standard communication scenario (follow-ups, declines, confirmations, boundaries) to avoid generating from scratch."
allowed-tools: "Read"
version: 1.0
effort: medium
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`

# Skill: Communication Templates Library

## Name
communication_templates

## Domain
Operations / All

## Purpose
Pre-approved, voice-matched response templates for every common communication scenario. DEX pulls from these instead of generating from scratch.

---

## When to Use
Any time DEX needs to draft a response and a standard scenario applies. Always personalize before sending. Never send a template verbatim.

---

## Inputs
- scenario (see template list below)
- recipient_name
- context_fields (meeting title, date, person referenced, etc.)

---

## The Founder's Voice Principles
- Direct. Warm. No corporate speak.
- Short sentences. High signal.
- Always a clear next step.
- Never formal salutations ("I hope this email finds you well")
- Never passive ("it would be great if we could")
- Always active ("let's do X by Y")

---

## Process
1. Identify scenario from list below
2. Select matching template
3. Personalize all [bracketed] fields
4. Review for voice — should feel like the founder wrote it
5. Queue for approval unless trust level is EXECUTE

---

## Templates

### General Acknowledgment (buying time)
Hi [Name],

Got your message. I'll review and get back to you within [24h/48h].

[the founder/DEX]

---

### Meeting Confirmation
Hi [Name],

Confirmed for [Day, Date] at [Time] [Timezone].

[Meet link if applicable]

Looking forward to it.

[the founder/DEX]

---

### Reschedule Request
Hi [Name],

Something came up on my end — need to move our [Day] call. Are you available [Option 1] or [Option 2]?

Sorry for the change.

[the founder/DEX]

---

### Polite Decline (generic)
Hi [Name],

Thanks for reaching out. Not the right fit for where we are right now, but appreciate you thinking of us.

[the founder/DEX]

---

### Follow-Up After No Response (1st)
Hi [Name],

Just circling back on my message from [X days ago]. Still relevant on your end?

[the founder/DEX]

---

### Follow-Up After No Response (2nd, final)
Hi [Name],

Last follow-up on this — if the timing's not right, no problem at all. Just let me know either way.

[the founder/DEX]

---

### Meeting Recap
Hi [Name],

Good talking today. Quick recap:

What we covered: [summary]
Next steps: [what you're doing / what they're doing]
Next conversation: [date if set]

[the founder/DEX]

---

### Intro / Referral Thank You
Hi [Name],

Thanks for the intro to [person] — I'll reach out to them directly.

Appreciate it.

[the founder/DEX]

---

### Payment Received Confirmation
Hi [Name],

Payment received — thank you.

[Next steps / what to expect]

[the founder/DEX]

---

### Waiting on Something
Hi [Name],

Following up on [specific thing] from [date]. Where does this stand?

[the founder/DEX]

---

## Failure Modes
- Never send a template verbatim without personalizing all fields
- Never use a template for a recognized person — write fresh
- Never use corporate language ("I hope this finds you well", "per my last email")
- Never sign as the founder unless he has approved the message

---

## Trust Level
ASSIST — templates are drafts, not sends. All require approval unless previously authorized.

---

## Outputs
- Personalized draft ready for approval queue
- Voice-consistent communication across all scenarios

---

## Usage Rules
- DEX signature when DEX handled the thread
- the founder signature when the founder approves and wants his name on it
- When in doubt — DEX signature with "On behalf of the founder"


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
