---
name: playbook-investor-inquiry
description: "Handle inbound investor interest with appropriate gravity — triggered when any message signals investor intent with keywords like 'investing', 'fund', 'portfolio', 'term sheet', or 'cap table'."
allowed-tools: "Read, Bash"
version: 1.0
effort: low
---

# Skill: Playbook — Investor Inquiry

## Name
playbook_investor_inquiry

## Domain
Operations / Executive

## Purpose
Handle inbound investor interest or outreach with appropriate gravity — never auto-respond, always escalate to Antony.

---

## When to Use
Any email or message that signals investor intent: "interested in investing," "looking at opportunities," "fund," "portfolio," "term sheet," "cap table," "due diligence."

---

## Inputs
- sender_name
- sender_company
- message_content
- source (email/linkedin/referral)

---

## Process
1. Run person recognition immediately
2. Route to ANTONY folder regardless of recognition status
3. Flag in Discord: "⚠️ Investor inquiry from [Name] — [Company]. Your eyes only. Do not auto-respond."
4. Research person and fund if not known
5. Draft a holding response for Antony's review:
   "Hi [Name], Thank you for reaching out. Antony will review this personally and be in touch shortly."
6. Do NOT send until Antony explicitly approves
7. Log to Neon as high-priority event

---

## Failure Modes
- Never auto-respond to investor inquiries
- Never reveal financial details
- Never confirm or deny fundraising status
- Never schedule a call without Antony's explicit instruction

---

## Trust Level
OBSERVE — surface immediately, take no action without approval

---

## Outputs
- ANTONY folder routing
- Discord alert with full context
- Research brief on sender
- Holding response drafted and queued, not sent
- High-priority event logged to Neon
