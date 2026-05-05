---
name: playbook-vendor-contract
description: "Handle inbound contracts, NDAs, service agreements, and vendor documents with appropriate caution — triggered when any email contains an attached contract, NDA, service agreement, invoice, or legal document."
allowed-tools: "Read, Bash"
version: 1.0
effort: low
trigger: both
---

!`python3 /opt/OS/scripts/bis_context.py --founder`


# Skill: Playbook — Vendor or Contract Received

## Name
playbook_vendor_contract

## Domain
Operations / Legal / Finance

## Purpose
Handle inbound contracts, NDAs, service agreements, and vendor documents with appropriate caution.

---

## When to Use
Any email containing an attached contract, NDA, service agreement, invoice, or legal document.

---

## Inputs
- sender_name
- sender_company
- document_type (contract/NDA/invoice/service_agreement/other)
- attachment (file reference)
- deadline (if stated)

---

## Process
1. Identify document type (contract/NDA/invoice/agreement)
2. Route to FOUNDER folder immediately
3. Alert Discord: "📄 [Document type] received from [Sender]. Your review required."
4. Save attachment to Drive: /Legal/Pending_Review/
5. Extract key terms if possible:
   - Parties involved
   - Key obligations
   - Financial terms
   - Termination clauses
   - Deadlines
6. Include key terms summary in Discord alert
7. NEVER sign, agree, or acknowledge receipt of legal documents without the founder's explicit instruction

---

## Failure Modes
- Never acknowledge receipt of a legal document without instruction
- Never summarize in a way that implies agreement or acceptance
- Never miss a deadline field — always surface it prominently
- Never save to a location other than /Legal/Pending_Review/

---

## Trust Level
OBSERVE — surface and brief only, no action

---

## Outputs
- FOUNDER folder routing
- Discord alert with document type, sender, key terms summary, and any deadline
- Attachment saved to Drive: /Legal/Pending_Review/
- No response sent without explicit instruction


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
