---
name: playbook-no-show-recovery
description: "Recover no-show meetings professionally and re-engage the prospect without burning the relationship — triggered when a Calendly or calendar meeting is marked as no-show."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --founder`


# Skill: Playbook — No-Show Recovery

## Name
playbook_no_show_recovery

## Domain
Operations / Sales

## Purpose
Recover no-show meetings professionally and re-engage the prospect without burning the relationship.

---

## When to Use
When a Calendly or calendar meeting is marked as no-show or the post-meeting capture detects no activity at meeting time.

---

## Inputs
- person_name
- person_email
- meeting_title
- scheduled_time
- no_show_count (1st or 2nd)
- calendly_link

---

## Process
1. Wait 30 minutes past scheduled start before triggering
2. Update meeting record in Notion → Status: No-show
3. Draft recovery email:

Subject: Missed you — [original meeting title]

Hi [Name],

DEX here, the founder's assistant. Looks like we missed each other for [meeting title] today.

No worries at all — things come up. Here's a link to reschedule when you're ready: [Calendly link]

Best,
DEX
On behalf of the founder

4. Queue for approval before sending
5. Create follow-up task: "Follow up with [Name] if no response in 48h"
6. If second no-show → flag to the founder, do not auto-reschedule

---

## Failure Modes
- Never send recovery email immediately — wait 30 minutes
- Never assume they're disinterested after one no-show
- Never auto-reschedule twice without approval
- Never send second no-show recovery without the founder's review

---

## Trust Level
ASSIST — draft and queue, the founder approves

---

## Outputs
- Meeting status updated to No-show in Notion
- Recovery email queued for approval
- Follow-up task created (48h)


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
