---
name: playbook-job-inquiry
description: "Handle inbound job applications or hiring inquiries efficiently — triggered when any message is about working for, joining, or collaborating with any Munoz Conglomerate venture."
allowed-tools: "Read, Bash"
version: 1.0
effort: low
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --founder`


# Skill: Playbook — Job Inquiry

## Name
playbook_job_inquiry

## Domain
Operations / HR

## Purpose
Handle inbound job applications or hiring inquiries appropriately — not dismissively, but efficiently.

---

## When to Use
Any email or message about working for, joining, or collaborating with any Munoz Conglomerate venture.

---

## Inputs
- sender_name
- sender_background (from research)
- inquiry_type (active_application/speculative/contractor)
- message_content

---

## Process
1. Classify: active candidate vs speculative inquiry
2. Research sender quickly — what's their background?
3. If clearly unqualified or spam → file, no response
4. If potentially interesting:
   a. Flag to the founder with brief on sender
   b. Draft holding response:
      "Thanks for reaching out. We don't have open positions right now but I've flagged your message for the founder."
5. If the founder wants to proceed → schedule intro call

---

## Failure Modes
- Never promise a role or opportunity that doesn't exist
- Never dismiss a strong candidate without flagging to the founder
- Never reveal org structure or headcount details

---

## Trust Level
ASSIST — filter, brief, and recommend

---

## Outputs
- Routed appropriately (filed or escalated)
- Discord flag with sender brief if interesting
- Holding response queued if relevant


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
