---
name: playbook-deal-closed
description: "Execute the full deal-closed workflow — celebrate, onboard, document, and set the relationship up for success — triggered when a lead confirms payment or Antony marks a deal closed."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
trigger: both
---

# Skill: Playbook — Deal Closed

## Name
playbook_deal_closed

## Domain
Operations / Sales / Customer Success

## Purpose
Execute the full deal-closed workflow — celebrate, onboard, document, and set the relationship up for success.

---

## When to Use
When a lead confirms they're in, payment is received, or Antony marks a deal as closed in Discord or Notion.

---

## Inputs
- client_name
- client_email
- venture (lyfe_institute/empyrean_creative/personal_brand)
- amount
- payment_confirmed (yes/no)
- onboarding_steps (venture-specific)

---

## Process
1. Update Notion pipeline → Stage: Closed Won
2. Update lead file → status: Client
3. Log win to #wins channel in Discord:
   "🏆 Deal closed: [Name] — [Venture] — $[Amount]"
4. Draft welcome email to new client:
   - Warm, personal, not corporate
   - What happens next (onboarding steps)
   - Who to contact with questions
   - Sets expectations for the engagement
5. Queue welcome email for Antony's approval
6. Create onboarding tasks in Notion
7. Schedule kickoff call (if applicable)
8. Update Neon — log as revenue event

### Welcome Email Template
Subject: Welcome — let's get started

Hi [Name],

This is [Antony/DEX on behalf of Antony] — and I'm genuinely excited to work with you.

Here's what happens next:
[onboarding steps specific to venture]

If you have any questions before we start, reply here or reach out directly.

Let's build something.

[Antony/DEX]

---

## Failure Modes
- Never skip the #wins post — every closed deal gets acknowledged
- Never send welcome email without Antony's approval
- Never promise onboarding timeline without confirming capacity
- Never log as revenue event until payment is confirmed

---

## Trust Level
EXECUTE with oversight — post to #wins immediately, queue everything else for approval

---

## Outputs
- Notion pipeline updated to Closed Won
- Lead file updated to Client
- #wins Discord post sent
- Welcome email queued for approval
- Onboarding tasks created in Notion
- Revenue event logged to Neon


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
