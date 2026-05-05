# Initiate Arena — Offer Lock v1

**Date**: 2026-05-04
**Phase**: 92 — Founder Approval Capture + Offer Lock v1
**Status**: LOCKED_PENDING_APPROVAL — all fields populated, awaiting founder sign-off
**Predecessor**: Phase 91 (Offer Closure Decision Packet + Sales Asset Finalization v1)
**Purpose**: Single source of truth for every sellable field in the Initiate Arena offer. No other document is authoritative after this file is locked.

---

## Status Legend

| Tag | Meaning |
|-----|---------|
| APPROVED | Founder explicitly approved this value |
| DEFAULT_READY_FOR_APPROVAL | Phase 91 recommended default — founder has not yet reviewed |
| CONFIRMED | Previously confirmed across multiple sources — no approval needed |
| NEEDS_SETUP | Value is decided but requires external tool/account creation |
| NEEDS_EXTERNAL_CONFIRMATION | Depends on third-party availability or verification |
| BLOCKED | Cannot proceed without resolving a dependency |

---

## Offer Identity

### 1. Offer Name

| Field | Value |
|-------|-------|
| **Value** | Initiate Arena — Founding Cohort |
| **Status** | CONFIRMED |
| **Source** | business_test_001_packet.md, revenue_context_v1, multiple brand docs |
| **Lock note** | Name is stable across all sources. No approval needed. |

### 2. Target Avatar

| Field | Value |
|-------|-------|
| **Value** | Men aged 18–35 who know what they should be doing but cannot execute consistently |
| **Status** | CONFIRMED |
| **Source** | business_test_001_packet.md, revenue_context_v1, brand identity docs |
| **Lock note** | Avatar confirmed across 5+ documents. No approval needed. |

### 3. Anti-Target

| Field | Value |
|-------|-------|
| **Value** | Free content seekers, anti-discipline mindset, not ready to invest, passive consumers, defensive about feedback, bots/engagement pods |
| **Status** | CONFIRMED |
| **Source** | business_test_001_packet.md, minimum_sellable_offer_v1 |
| **Lock note** | Disqualification criteria stable. No approval needed. |

### 4. Core Pain

| Field | Value |
|-------|-------|
| **Value** | Knowing what to do but being unable to execute consistently |
| **Status** | CONFIRMED |
| **Source** | business_test_001_packet.md, brand identity, content positioning |
| **Lock note** | Core pain is the anchor of all messaging. Confirmed. |

### 5. Core Promise

| Field | Value |
|-------|-------|
| **Value** | You will go from knowing what to do to actually doing it — every day — for 90 days. You will come out with proof of your own execution ability. |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | minimum_sellable_offer_v1 (Phase 91 recommended) |
| **Lock note** | Promise updated to reflect 90-day duration. Requires approval since duration changed from 30 days. |

### 6. Mechanism

| Field | Value |
|-------|-------|
| **Value** | Structure + accountability over 90 days. Training camp, not a course. Daily execution framework + brotherhood + weekly calls. |
| **Status** | CONFIRMED |
| **Source** | business_test_001_packet.md, revenue_context_v1 |
| **Lock note** | Mechanism is stable. Duration parameter updated to 90 days per Phase 91 recommendation. |

---

## Offer Economics

### 7. Price

| Field | Value |
|-------|-------|
| **Value** | $750 one-pay (Founding Cohort) |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 Decision 1 recommended default |
| **Evidence** | CLAUDE.local.md "first $750 sale" reference; $750 × 14/mo = $10,500 clears north star |
| **Alternatives** | $497, $997, $97/mo |
| **Lock note** | Strongest price signal available. Requires founder approval. |

### 8. Payment Structure

| Field | Value |
|-------|-------|
| **Value** | One-pay $750 + optional 2-pay of $400 ($800 total) |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 Decision 2 recommended default |
| **Evidence** | 2-pay increases accessibility ~30%; $50 premium is industry standard |
| **Alternatives** | One-pay only; 3-pay of $275 ($825 total) |
| **Lock note** | Requires founder approval. |

### 9. Refund / Guarantee

| Field | Value |
|-------|-------|
| **Value** | No broad guarantee for founding cohort. Fit-based acceptance via qualification conversation. |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 Decision 9 recommended default |
| **Alternatives** | 7-day refund; conditional "complete all assignments" guarantee |
| **Lock note** | Requires founder approval. |

---

## Offer Structure

### 10. Duration

| Field | Value |
|-------|-------|
| **Value** | 90 days (12 weeks) |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 Decision 3 recommended default |
| **Evidence** | 30 days too tight for $750 value perception; 90 days = 6 two-week phases; industry norm 8–12 weeks |
| **Alternatives** | 30 days (original), 60 days |
| **Lock note** | Most significant change from prior positioning. Requires explicit founder approval. |

### 11. Curriculum

| Field | Value |
|-------|-------|
| **Value** | 6-phase / 12-week structure: Onboarding → Discipline Reset → Identity & Environment → Fitness/Energy → Skill/Money/Execution → Brotherhood & Challenge → Integration |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 Decision 5 recommended default |
| **Lock note** | Inferred curriculum. Founder may have existing framework in Google Drive. Requires approval. |

### 12. Weekly Structure

| Field | Value |
|-------|-------|
| **Value** | Mon: new mission + review. Tue–Fri: daily execution + Discord check-in. Sat: group call (60 min). Sun: rest + weekly self-report. |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | minimum_sellable_offer_v1 (Phase 91) |
| **Lock note** | Requires founder approval as part of fulfillment model. |

### 13. Deliverables

| Field | Value |
|-------|-------|
| **Value** | (1) 90-day structured execution framework, (2) weekly group call with Antony, (3) weekly mission, (4) daily Discord accountability, (5) progress tracker, (6) direct access to Antony, (7) brotherhood community, (8) 90-day execution proof |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | minimum_sellable_offer_v1 (Phase 91) |
| **Lock note** | 8 deliverables. Requires founder approval. |

---

## Delivery & Fulfillment

### 14. Delivery Container

| Field | Value |
|-------|-------|
| **Value** | Discord (private server) + weekly group call (Discord voice or Google Meet) + Notion page or Google Doc curriculum hub |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 Decision 4 recommended default |
| **Alternatives** | Discord only; Notion only; Skool/WHOP (future) |
| **Lock note** | $0 stack. Requires founder approval. |

### 15. Fulfillment Model

| Field | Value |
|-------|-------|
| **Value** | Weekly group call (60 min) + weekly mission release + daily Discord accountability + weekly self-report. ~3–4 hrs/week founder time per cohort of 5–10. |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 Decision 6 recommended default |
| **Alternatives** | Lighter (bi-weekly call, ~1.5 hrs/week); Heavier (weekly 1:1 + group, ~6–8 hrs/week) |
| **Lock note** | Defines founder's ongoing time commitment. Requires explicit approval. |

### 16. Participant Commitment

| Field | Value |
|-------|-------|
| **Value** | 30–60 min/day execution + check-in. 60 min/week call. 10 min/week self-report. Responsive in Discord within 24 hours. |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | minimum_sellable_offer_v1 (Phase 91) |
| **Lock note** | Sets student expectations. Requires approval. |

---

## Sales Infrastructure

### 17. Payment Path

| Field | Value |
|-------|-------|
| **Value** | Stripe payment link |
| **Status** | NEEDS_SETUP |
| **Source** | Phase 91 Decision 8 recommended default |
| **Setup required** | Create Stripe payment link: $750 one-pay + $400×2 plan (~15 min) |
| **Lock note** | Decision made. Link not yet created. |

### 18. Call Booking

| Field | Value |
|-------|-------|
| **Value** | Calendly free tier — 15-min "Initiate Arena Call" |
| **Status** | NEEDS_SETUP |
| **Source** | Phase 91 Decision 7 recommended default |
| **Setup required** | Create Calendly booking page (~10 min) |
| **Lock note** | Decision made. Page not yet created. |

### 19. Discord Server

| Field | Value |
|-------|-------|
| **Value** | Private Discord server: #welcome, #accountability, #missions, #general, #wins |
| **Status** | NEEDS_SETUP |
| **Source** | Phase 91 Decision 4, first_sale_execution_plan_v1 |
| **Setup required** | Create server and channels (~20 min) |
| **Lock note** | Decision made. Server not yet created. |

### 20. Curriculum Hub

| Field | Value |
|-------|-------|
| **Value** | Notion page or Google Doc with 12-week outline |
| **Status** | NEEDS_SETUP |
| **Source** | Phase 91 Decision 5, minimum_sellable_offer_v1 |
| **Setup required** | Create document with curriculum phases (~30 min) |
| **Lock note** | Decision made. Document not yet created. |

### 21. Lead Tracker

| Field | Value |
|-------|-------|
| **Value** | Google Sheet with 12 columns (Name, Platform, First Contact Date, Source, Stage, Objections, Follow-Ups Sent, Call Date, Call Outcome, Payment Received, Payment Date, Notes) |
| **Status** | NEEDS_SETUP |
| **Source** | first_sale_execution_plan_v1 |
| **Setup required** | Create Google Sheet (~10 min) |
| **Lock note** | Decision made. Sheet not yet created. |

---

## Sales Workflow

### 22. Qualification Criteria

| Field | Value |
|-------|-------|
| **Value** | 3-of-5 framework: (1) Pain intensity, (2) Urgency, (3) Willingness to change, (4) Coachability, (5) Ability to invest |
| **Status** | CONFIRMED |
| **Source** | business_test_001_packet.md — confirmed across Phases 89–91 |
| **Lock note** | Only decision confirmed before Phase 91. No approval needed. |

### 23. First Sale Workflow

| Field | Value |
|-------|-------|
| **Value** | Post content (1/day) → Engage → DM 5–20 prospects → Qualify (3-of-5) → Book call (Calendly) → Run 20-min call → Send payment link (Stripe) → Confirm payment → Send onboarding → Grant Discord + curriculum access |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 Decision 11 recommended default |
| **Alternative** | Skip call, close in DMs |
| **Lock note** | Full 10-step workflow. Requires founder approval. |

### 24. Sales Assets

| Field | Value |
|-------|-------|
| **Value** | 16 categories, 37 items. See `initiate_arena_final_sales_assets_v1.md` |
| **Status** | DEFAULT_READY_FOR_APPROVAL |
| **Source** | Phase 91 final sales assets |
| **Lock note** | All assets use recommended defaults ($750, 90 days). Must be updated if founder modifies price or duration. Requires voice review + approval. |

---

## Lock Summary

| Category | Count | Status |
|----------|-------|--------|
| CONFIRMED | 6 | Fields 1, 2, 3, 4, 6, 22 |
| DEFAULT_READY_FOR_APPROVAL | 13 | Fields 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 23, 24 |
| NEEDS_SETUP | 5 | Fields 17, 18, 19, 20, 21 |
| APPROVED | 0 | None — awaiting founder review |
| BLOCKED | 0 | All blockers resolved by Phase 91 defaults |

**Total fields**: 24
**Ready for sale after**: Founder approves 13 DEFAULT fields + completes 5 NEEDS_SETUP tasks (~1.75 hours)

---

## How to Finalize This Lock

1. Founder reviews and approves/modifies all 13 DEFAULT_READY_FOR_APPROVAL fields
2. Update each approved field's status to APPROVED
3. If any field is modified, propagate the change to: minimum_sellable_offer_v1, final_sales_assets_v1, first_sale_execution_plan_v1
4. Complete all 5 NEEDS_SETUP tasks (see `initiate_arena_setup_tasks_v1.md`)
5. Insert live links (Stripe, Calendly, Discord invite) into all asset templates
6. Change document status from LOCKED_PENDING_APPROVAL to LOCKED_FINAL
7. This document becomes the sole authoritative reference for the Initiate Arena offer
