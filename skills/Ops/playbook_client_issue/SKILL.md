---
name: playbook-client-issue
description: "Handle client complaints or issues with urgency, empathy, and professionalism — triggered when any existing client message expresses dissatisfaction, reports a problem, requests a refund, or signals churn risk."
allowed-tools: "Read, Bash"
version: 1.0
---

# Skill: Playbook — Client Issue or Complaint

## Name
playbook_client_issue

## Domain
Operations / Customer Success

## Purpose
Handle client complaints or issues with urgency, empathy, and professionalism — protect the relationship while keeping Antony informed.

---

## When to Use
Any message from an existing client expressing dissatisfaction, reporting a problem, requesting a refund, or threatening to leave.

---

## Inputs
- sender_name
- client_status (confirmed client or unknown)
- issue_type (complaint/refund_request/technical/churn_risk)
- message_content

---

## Process
1. Run person recognition — confirm they are an existing client
2. If not recognized as client → treat as unknown, standard flow
3. If confirmed client:
   a. Route to ANTONY folder immediately
   b. Alert Discord: "🔴 Client issue — [Name]. Needs attention today."
   c. Do NOT draft response yet — Antony must read first
   d. Research: what's their history, what did they purchase, any prior issues?
   e. Prepare context brief for Antony:
      - Who they are
      - What they purchased and when
      - What they're reporting
      - Recommended response approach
4. If Antony instructs DEX to handle:
   a. Draft empathetic, non-defensive response
   b. Never admit liability without legal review
   c. Offer specific resolution, not vague promises
   d. Queue for approval before sending

### Response Principles
- Acknowledge first, solve second
- Never be defensive
- Never promise what can't be delivered
- Never offer refund without Antony's approval

---

## Failure Modes
- Never auto-respond to a client complaint
- Never admit liability in writing
- Never offer refund without explicit approval
- Never send response without Antony reviewing first

---

## Trust Level
OBSERVE — surface immediately, draft only when instructed

---

## Outputs
- ANTONY folder routing
- Discord urgent alert
- Context brief prepared (purchase history, issue summary, recommended approach)
- Response drafted only on explicit instruction
