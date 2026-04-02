---
name: playbook-new-inbound-lead
description: "Handle every new inbound lead from any channel with a consistent, world-class response that qualifies, captures, and advances the relationship — triggered on any first expression of interest in any Munoz Conglomerate venture."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
---

# Skill: Playbook — New Inbound Lead

## Name
playbook_new_inbound_lead

## Domain
Sales / Operations

## Purpose
Handle every new inbound lead from any channel (email, Calendly, Instagram, referral) with a consistent, world-class response that qualifies, captures, and advances the relationship.

---

## When to Use
Any time a new person expresses interest in any Munoz Conglomerate venture for the first time.

---

## Inputs
- person_name
- email
- company (if known)
- source (email/calendly/instagram/referral)
- venture (lyfe_institute/empyrean_creative/personal_brand)
- message_content (their original message if available)

---

## Process
1. Run person recognition — check memory, CRM, meetings DB
2. If known person → route to ANTONY folder immediately, flag, stop
3. If new person:
   a. Create lead file in 03_CRM/Leads/
   b. Research person and company (web search if available)
   c. Classify intent — what are they asking for?
   d. Draft response using venture-appropriate template
   e. Queue for approval before sending
   f. Create follow-up task for 48h if no response
4. Log interaction to Neon
5. Update Notion pipeline — stage: New Lead

### Response Templates by Venture

**Lyfe Institute (inbound interest in coaching)**
Subject: Re: [their subject]

Hi [Name],

This is DEX, Antony's assistant. Got to your message before him and wanted to make sure you heard back quickly.

Antony's running the Initiate Arena right now — a 90-day program for men who are done drifting and ready to build real structure around their ambition. [$750/program, limited spots].

I've flagged your message for him. Before I loop him in — what's the main thing you're trying to change in the next 90 days?

Best,
DEX
On behalf of Antony Munoz

---

**Empyrean Creative (inbound interest in AI systems)**
Subject: Re: [their subject]

Hi [Name],

DEX here — Antony's assistant. Caught your message first.

Empyrean builds AI infrastructure for founders and operators who need systems that actually run their business, not just assist it.

I'll flag this for Antony directly. To make sure he has context when he reviews — what's the main operational bottleneck you're trying to solve?

Best,
DEX
On behalf of Antony Munoz

---

## Failure Modes
- Never send template to a recognized person
- Never mention pricing before qualifying intent
- Never promise Antony's direct involvement without his approval
- Never advance past draft stage without approval

---

## Trust Level
ASSIST — draft and queue, never send without approval

---

## Outputs
- Lead file created in 03_CRM/Leads/
- Draft response queued for approval
- Follow-up task created (48h)
- Notion pipeline updated — stage: New Lead
- Interaction logged to Neon
