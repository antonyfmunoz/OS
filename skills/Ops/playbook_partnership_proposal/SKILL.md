---
name: playbook-partnership-proposal
description: "Handle inbound partnership proposals consistently — triggered when any message proposes collaboration, joint venture, affiliate arrangement, co-marketing, referral partnership, white-label, or integration."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --founder`


# Skill: Playbook — Partnership Proposal

## Name
playbook_partnership_proposal

## Domain
Operations / Sales

## Purpose
Handle inbound partnership proposals consistently — qualify before escalating, never commit without approval.

---

## When to Use
Any message proposing collaboration, joint venture, affiliate arrangement, co-marketing, referral partnership, white-label, or integration.

---

## Inputs
- sender_name
- sender_company
- proposal_type (affiliate/JV/integration/referral/other)
- message_content

---

## Process
1. Run person recognition
2. Research sender and their company
3. Classify proposal type (affiliate/JV/integration/referral/other)
4. Apply quick filter:
   - Does this align with any active venture's ICP or channel?
   - Is there a clear value exchange?
   - Is the sender credible?
5. If clearly spam/irrelevant → file in NEWSLETTERS, no response
6. If potentially relevant:
   a. Draft qualifying response asking for specifics
   b. Queue for approval
   c. Flag in Discord with context and recommendation
7. If high-signal → FOUNDER folder with full research brief

### Qualifying Response Template
Hi [Name],

DEX here, the founder's assistant.

Thanks for reaching out about a potential partnership. To make sure I route this to the right place — can you share a bit more about what you have in mind and what you're looking for from our side?

Best,
DEX
On behalf of the founder

---

## Failure Modes
- Never commit to any partnership arrangement
- Never share revenue data or business metrics
- Never schedule intro call without qualifying first

---

## Trust Level
ASSIST — draft and recommend, the founder decides

---

## Outputs
- Qualifying response queued or spam-filed
- Discord flag with recommendation
- Lead file created if qualified


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
