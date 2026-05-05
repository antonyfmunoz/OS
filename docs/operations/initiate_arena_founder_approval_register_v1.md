# Initiate Arena — Founder Approval Register v1

**Date**: 2026-05-04
**Phase**: 92 — Founder Approval Capture + Offer Lock v1
**Purpose**: Track every founder decision required before the offer goes live. This register is the control surface — update it when decisions are made, then propagate to the offer lock.

---

## Fast Approval Command

To approve all Phase 91/92 recommended defaults at once:

> **"I approve all Phase 91/92 recommended defaults for Initiate Arena v1."**

This sets all 13 DEFAULT_READY_FOR_APPROVAL fields to APPROVED and triggers:
1. Offer lock status → LOCKED_FINAL
2. Sales assets confirmed as-is
3. Setup tasks become the only remaining blocker

To approve with modifications:

> **"I approve all defaults except: [list specific changes]."**
> Example: "I approve all defaults except: price is $497, duration is 60 days."

To approve individually:

> **"Decision [#]: [APPROVED / MODIFIED: new value]."**
> Example: "Decision 1: APPROVED. Decision 3: MODIFIED: 60 days."

---

## Decision Register

| # | Decision | Recommended Default | Status | Founder Response | Date |
|---|----------|-------------------|--------|-----------------|------|
| 1 | Price | $750 founding cohort one-pay | DEFAULT_READY_FOR_APPROVAL | — | — |
| 2 | Payment structure | One-pay $750 + optional 2-pay $400 ($800 total) | DEFAULT_READY_FOR_APPROVAL | — | — |
| 3 | Duration | 90 days (12 weeks) | DEFAULT_READY_FOR_APPROVAL | — | — |
| 4 | Delivery container | Discord + weekly call + Notion/Doc hub | DEFAULT_READY_FOR_APPROVAL | — | — |
| 5 | Curriculum | 6-phase / 12-week structure | DEFAULT_READY_FOR_APPROVAL | — | — |
| 6 | Fulfillment model | Weekly call + mission + daily Discord accountability | DEFAULT_READY_FOR_APPROVAL | — | — |
| 7 | Call booking | Calendly free tier | DEFAULT_READY_FOR_APPROVAL | — | — |
| 8 | Payment path | Stripe payment link | DEFAULT_READY_FOR_APPROVAL | — | — |
| 9 | Refund / guarantee | No broad guarantee (founding cohort framing) | DEFAULT_READY_FOR_APPROVAL | — | — |
| 10 | Qualification criteria | 3-of-5 framework | CONFIRMED | Already confirmed | Pre-Phase 91 |
| 11 | First sale workflow | Post → DM → qualify → call → close → onboard | DEFAULT_READY_FOR_APPROVAL | — | — |
| 12 | Sales assets (voice) | 16 categories, 37 items — all drafts use $750/90-day framing | DEFAULT_READY_FOR_APPROVAL | — | — |
| 13 | Onboarding sequence | Discord invite + curriculum link + Day 0 baseline + start date | DEFAULT_READY_FOR_APPROVAL | — | — |

---

## Register Summary

| Status | Count | Details |
|--------|-------|---------|
| CONFIRMED | 1 | Decision 10 (qualification) |
| DEFAULT_READY_FOR_APPROVAL | 12 | Decisions 1–9, 11–13 |
| APPROVED | 0 | Awaiting founder review |
| MODIFIED | 0 | — |
| DEFERRED | 0 | — |
| BLOCKED | 0 | All blockers resolved |

**Total decisions**: 13
**Decisions requiring founder action**: 12
**Estimated review time**: 10–15 minutes (read + approve/modify)

---

## Decisions Most Likely to Generate Discussion

| # | Decision | Why |
|---|----------|-----|
| 3 | Duration (30 → 90 days) | Significant departure from original positioning. Rationale is strong (value perception, transformation depth, competitive positioning) but founder may have reasons to keep 30-day sprint. |
| 1 | Price ($750) | Only signal is CLAUDE.local.md reference. Founder may want higher ($997) or lower ($497) based on audience testing. |
| 5 | Curriculum (6-phase inferred) | Founder may have existing curriculum in Google Drive that supersedes this. |
| 6 | Fulfillment (~3–4 hrs/week) | Defines ongoing time commitment. Founder should explicitly accept this. |

---

## Propagation Rules

When a decision is APPROVED or MODIFIED, update these files in order:

| Step | File | What to Update |
|------|------|---------------|
| 1 | `initiate_arena_offer_lock_v1.md` | Change field status to APPROVED. If MODIFIED, update value. |
| 2 | `initiate_arena_minimum_sellable_offer_v1.md` | Update any changed values (price, duration, deliverables, etc.) |
| 3 | `initiate_arena_final_sales_assets_v1.md` | Update all assets that reference changed values ($750, 90 days, etc.) |
| 4 | `initiate_arena_first_sale_execution_plan_v1.md` | Update setup checklist and workflow references |
| 5 | `initiate_arena_setup_tasks_v1.md` | Update task parameters if values changed |
| 6 | `initiate_arena_execution_context_v1.md` | Update locked values in Phase 93 context packet |

**Critical**: If price or duration changes, every sales asset must be regenerated. The asset set uses $750 and 90 days throughout.

---

## Post-Approval Checklist

After all 12 decisions are APPROVED or MODIFIED:

| # | Action | Status |
|---|--------|--------|
| 1 | All offer lock fields updated to APPROVED | [ ] |
| 2 | Offer lock status changed to LOCKED_FINAL | [ ] |
| 3 | Modified values propagated to all 5 downstream files | [ ] |
| 4 | Sales assets re-confirmed with final values | [ ] |
| 5 | Setup tasks unblocked for execution | [ ] |
| 6 | Phase 93 execution context finalized | [ ] |
