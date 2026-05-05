# Initiate Arena — Setup Tasks v1

**Date**: 2026-05-04
**Phase**: 92 — Founder Approval Capture + Offer Lock v1
**Purpose**: Every external setup task required before the first sale can close. Organized by blocking priority.
**Prerequisite**: Founder must approve offer lock decisions before beginning setup.

---

## Tier 1 — Must Complete Before Payment Can Be Accepted

These tasks block revenue. No sale can close without them.

### Task 1.1 — Create Stripe Payment Link

| Field | Value |
|-------|-------|
| **What** | Create Stripe payment link with two options: $750 one-pay and $400×2 payment plan |
| **Owner** | Founder |
| **Platform** | Stripe dashboard |
| **Estimated time** | 15 minutes |
| **Dependency** | Decision 1 (price) and Decision 2 (payment structure) must be APPROVED |
| **Status** | NOT_STARTED |
| **AI-draftable** | NO — requires Stripe account access |
| **Founder-approval-needed** | YES — revenue transaction |
| **Computer-use-eligible** | YES (future) — supervised Stripe navigation |
| **Output** | Live Stripe payment link URL |
| **Insert into** | All sales assets that reference [Stripe payment link], payment message (Asset 15), closing language (Asset 14) |

### Task 1.2 — Create Calendly Booking Page

| Field | Value |
|-------|-------|
| **What** | Create 15-minute "Initiate Arena Call" event type on Calendly free tier |
| **Owner** | Founder |
| **Platform** | Calendly |
| **Estimated time** | 10 minutes |
| **Dependency** | Decision 7 (call booking) must be APPROVED |
| **Status** | NOT_STARTED |
| **AI-draftable** | NO — requires Calendly account access |
| **Founder-approval-needed** | YES — availability and scheduling |
| **Computer-use-eligible** | YES (future) — supervised Calendly setup |
| **Output** | Live Calendly booking link URL |
| **Insert into** | CTA (Asset 7 secondary), call-booking prompt (Asset 12), follow-up after interest (Asset 9) |

### Task 1.3 — Insert Payment Link into Sales Assets

| Field | Value |
|-------|-------|
| **What** | Replace all `[Stripe payment link]` placeholders in sales assets with live URL |
| **Owner** | Founder (or AI with founder approval) |
| **Platform** | Local file editing |
| **Estimated time** | 5 minutes |
| **Dependency** | Task 1.1 complete |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — find-and-replace operation |
| **Founder-approval-needed** | YES — verify correct link |
| **Computer-use-eligible** | NO — local file operation |
| **Output** | Updated `initiate_arena_final_sales_assets_v1.md` |

### Task 1.4 — Insert Calendly Link into Sales Assets

| Field | Value |
|-------|-------|
| **What** | Replace all `[Calendly link]` placeholders in sales assets with live URL |
| **Owner** | Founder (or AI with founder approval) |
| **Platform** | Local file editing |
| **Estimated time** | 5 minutes |
| **Dependency** | Task 1.2 complete |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — find-and-replace operation |
| **Founder-approval-needed** | YES — verify correct link |
| **Computer-use-eligible** | NO — local file operation |
| **Output** | Updated `initiate_arena_final_sales_assets_v1.md` |

---

## Tier 2 — Must Complete Before First Student Onboards

These tasks don't block the sale itself but block onboarding after payment.

### Task 2.1 — Create Discord Server

| Field | Value |
|-------|-------|
| **What** | Create private Discord server with channels: #welcome, #accountability, #missions, #general, #wins |
| **Owner** | Founder |
| **Platform** | Discord |
| **Estimated time** | 20 minutes |
| **Dependency** | Decision 4 (delivery container) must be APPROVED |
| **Status** | NOT_STARTED |
| **AI-draftable** | NO — requires Discord account |
| **Founder-approval-needed** | YES — community ownership |
| **Computer-use-eligible** | YES (future) — supervised Discord setup |
| **Output** | Discord invite link (permanent, limited uses) |
| **Insert into** | Onboarding message (Asset 16) |

### Task 2.2 — Create Curriculum Hub

| Field | Value |
|-------|-------|
| **What** | Create Notion page or Google Doc with 12-week curriculum outline (6 phases, weekly missions placeholder, program rules) |
| **Owner** | Founder |
| **Platform** | Notion or Google Docs |
| **Estimated time** | 30 minutes |
| **Dependency** | Decision 5 (curriculum) must be APPROVED |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — AI can draft full outline for founder review |
| **Founder-approval-needed** | YES — curriculum content |
| **Computer-use-eligible** | YES (future) — supervised doc creation |
| **Output** | Shareable curriculum hub URL |
| **Insert into** | Onboarding message (Asset 16) |
| **Note** | Founder may have existing curriculum in Google Drive "Coaching Frameworks" folder. Check before creating from scratch. |

### Task 2.3 — Insert Discord + Curriculum Links into Onboarding

| Field | Value |
|-------|-------|
| **What** | Replace `[Discord invite link]` and `[Notion/Doc link]` placeholders in onboarding message |
| **Owner** | Founder (or AI with founder approval) |
| **Platform** | Local file editing |
| **Estimated time** | 5 minutes |
| **Dependency** | Tasks 2.1 and 2.2 complete |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — find-and-replace |
| **Founder-approval-needed** | YES — verify correct links |
| **Computer-use-eligible** | NO — local file operation |
| **Output** | Updated onboarding message in `initiate_arena_final_sales_assets_v1.md` |

---

## Tier 3 — Should Complete Before Active Outreach

These improve execution quality but don't block the first sale.

### Task 3.1 — Create Lead Tracking Google Sheet

| Field | Value |
|-------|-------|
| **What** | Create Google Sheet with 12 columns: Name, Platform, First Contact Date, Source, Stage, Objections, Follow-Ups Sent, Call Date, Call Outcome, Payment Received, Payment Date, Notes |
| **Owner** | Founder (or AI with founder approval) |
| **Platform** | Google Sheets |
| **Estimated time** | 10 minutes |
| **Dependency** | None |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — AI can create template for founder to copy |
| **Founder-approval-needed** | NO — operational tool |
| **Computer-use-eligible** | YES (future) — supervised sheet creation |
| **Output** | Google Sheet URL |

### Task 3.2 — Review and Personalize Sales Assets

| Field | Value |
|-------|-------|
| **What** | Founder reads all 16 asset categories (37 items) in `initiate_arena_final_sales_assets_v1.md` and adjusts language to match their natural voice |
| **Owner** | Founder |
| **Platform** | Local file or voice-to-text |
| **Estimated time** | 20 minutes |
| **Dependency** | All offer lock decisions APPROVED |
| **Status** | NOT_STARTED |
| **AI-draftable** | PARTIAL — AI can suggest voice edits based on existing content samples |
| **Founder-approval-needed** | YES — voice authenticity is critical |
| **Computer-use-eligible** | NO — subjective judgment |
| **Output** | Updated `initiate_arena_final_sales_assets_v1.md` with founder-approved voice |

### Task 3.3 — Set Up KPI Tracker

| Field | Value |
|-------|-------|
| **What** | Add KPI tracking tab to lead sheet or create separate tracker with 14 daily + 12 pipeline metrics from `first_sale_execution_plan_v1.md` |
| **Owner** | Founder (or AI with founder approval) |
| **Platform** | Google Sheets |
| **Estimated time** | 10 minutes |
| **Dependency** | Task 3.1 complete |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — AI can create full template |
| **Founder-approval-needed** | NO — operational tool |
| **Computer-use-eligible** | YES (future) |
| **Output** | KPI tracker tab or sheet |

### Task 3.4 — Prepare First Content Post

| Field | Value |
|-------|-------|
| **What** | Draft and publish first content piece using short-form script (Asset 5) or content angle (Asset 4) |
| **Owner** | Founder |
| **Platform** | Instagram / X / LinkedIn |
| **Estimated time** | 20 minutes |
| **Dependency** | Task 3.2 complete (voice personalized) |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — AI can draft for founder review |
| **Founder-approval-needed** | YES — all content requires founder approval before posting |
| **Computer-use-eligible** | YES (future) — draft display for approval |
| **Output** | Published content post |

### Task 3.5 — Prepare Day 0 Baseline Assessment

| Field | Value |
|-------|-------|
| **What** | Create the onboarding assessment that new students complete before their start date |
| **Owner** | Founder |
| **Platform** | Google Form or Discord message template |
| **Estimated time** | 15 minutes |
| **Dependency** | Decision 5 (curriculum) APPROVED |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — AI can draft assessment questions |
| **Founder-approval-needed** | YES — student experience |
| **Computer-use-eligible** | YES (future) |
| **Output** | Baseline assessment form or template |

### Task 3.6 — Prepare Week 1 Mission

| Field | Value |
|-------|-------|
| **What** | Write the first weekly mission (Discipline Reset phase) that will be posted in #missions on Day 1 |
| **Owner** | Founder |
| **Platform** | Local doc or Discord draft |
| **Estimated time** | 15 minutes |
| **Dependency** | Decision 5 (curriculum) APPROVED |
| **Status** | NOT_STARTED |
| **AI-draftable** | YES — AI can draft based on curriculum Phase 1 |
| **Founder-approval-needed** | YES — curriculum content |
| **Computer-use-eligible** | NO — content judgment |
| **Output** | Week 1 mission document |

---

## Task Summary

| Tier | Tasks | Total Time | Blocks |
|------|-------|-----------|--------|
| 1 — Before payment | 4 tasks | ~35 min | Revenue |
| 2 — Before onboarding | 3 tasks | ~55 min | Student delivery |
| 3 — Before outreach | 6 tasks | ~90 min | Execution quality |
| **Total** | **13 tasks** | **~3 hours** | — |

### Minimum viable setup (first sale only)

Tier 1 (35 min) + Tier 2 (55 min) = **~1.5 hours** to accept payment and onboard a student.

Tier 3 improves execution quality but the first sale can technically close with only Tiers 1 and 2 complete.

---

## AI-Draftable Tasks

These tasks can be partially or fully drafted by AI, reducing founder time:

| Task | AI Can Do | Founder Must Do |
|------|-----------|----------------|
| 1.3 — Insert payment link | Find-and-replace all placeholders | Verify correct link |
| 1.4 — Insert Calendly link | Find-and-replace all placeholders | Verify correct link |
| 2.2 — Curriculum hub | Draft full 12-week outline | Review, modify, publish |
| 2.3 — Insert onboarding links | Find-and-replace all placeholders | Verify correct links |
| 3.1 — Lead tracking sheet | Create full template | Copy to own Google account |
| 3.3 — KPI tracker | Create full template | Copy to own Google account |
| 3.4 — First content post | Draft post from approved assets | Review voice, publish |
| 3.5 — Day 0 assessment | Draft assessment questions | Review, publish |
| 3.6 — Week 1 mission | Draft mission from curriculum | Review, publish |

**AI-draftable**: 9/13 tasks
**Founder-only**: 4/13 tasks (Stripe, Calendly, Discord server, asset voice review)
