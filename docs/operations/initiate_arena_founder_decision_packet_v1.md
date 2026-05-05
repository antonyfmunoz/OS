# Initiate Arena — Founder Decision Packet v1

**Date**: 2026-05-04
**Phase**: 91 — Offer Closure Decision Packet + Sales Asset Finalization v1
**Purpose**: Close every open decision required before the first Initiate Arena sale
**How to use**: Read each decision. Accept the recommended default, pick an alternative, or write your own. Mark each as APPROVED, MODIFIED, or DEFERRED. When all 11 are resolved, the offer is sale-ready.

**Confidence tags**:
- **RECOMMENDED_DEFAULT** — best available option given evidence; founder can approve as-is
- **ALTERNATIVE** — viable option with different trade-offs
- **NEEDS_FOUNDER_APPROVAL** — cannot proceed without explicit founder sign-off
- **CONFIRMED** — already decided or documented
- **BLOCKED** — cannot resolve without external dependency

---

## Decision 1 — Price

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: $750 one-pay (Founding Cohort)

**Evidence**:
- `CLAUDE.local.md` references "first $750 sale" as the binding constraint milestone
- At $750 × 14 sales/month = $10,500/month — clears the $10K/month north star target
- $750 is accessible for the 18–35 ambitious demographic without being perceived as low-value
- "Founding cohort" framing justifies the price while creating urgency and exclusivity
- 90-day container at $750 = $250/month effective rate — competitive for coaching + community + accountability

### ALTERNATIVE A: $497 one-pay

- Lower barrier, higher volume needed (~20/month for $10K)
- Risks being perceived as "another cheap course"
- Better if audience is younger/lower-income

### ALTERNATIVE B: $997 one-pay

- Higher perceived value, fewer sales needed (~10/month)
- Higher objection rate on first conversations
- Better if Antony has strong proof/testimonials (not yet)

### ALTERNATIVE C: $97/month membership

- Recurring revenue model, low barrier
- Requires ~103 active members for $10K/month — harder to manage solo
- Better for scale, worse for first-sale velocity

**Founder decision**: [ ] $750 founding cohort / [ ] $497 / [ ] $997 / [ ] $97/mo / [ ] Other: ______

---

## Decision 2 — Payment Structure

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: One-pay $750 + optional 2-pay of $400 ($800 total)

**Evidence**:
- One-pay is simplest to manage and has no payment-default risk
- 2-pay option increases accessibility by ~30% in coaching market
- $400 × 2 = $800 total (slight premium for payment plan) is standard practice
- Stripe handles both natively with payment links

### ALTERNATIVE A: One-pay only ($750)

- Simplest possible. No payment tracking, no follow-up on second payment.
- Filters for highest-commitment buyers.

### ALTERNATIVE B: 3-pay of $275 ($825 total)

- More accessible, higher administrative overhead
- Greater risk of payment default after month 1

**Founder decision**: [ ] One-pay + 2-pay / [ ] One-pay only / [ ] 3-pay / [ ] Other: ______

---

## Decision 3 — Program Duration

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: 90 days (12 weeks)

**Evidence**:
- Prior docs referenced 30 days, but 30 days is extremely tight for meaningful transformation at $750
- 90 days allows a real behavioral arc: reset → build → test → integrate
- 90 days at $750 = ~$8.33/day — easy to justify in sales conversations
- 12-week structure gives room for 6 two-week modules, each building on the last
- Most successful coaching programs in this space run 8–12 weeks
- 30-day version can be repositioned as the "sprint" within the 90-day arc

### ALTERNATIVE A: 30 days

- Original positioning from `business_test_001_packet.md`
- Harder to justify $750 for 30 days without strong proof
- Faster cycle = faster testimonials = faster iteration

### ALTERNATIVE B: 60 days

- Middle ground — 8 weeks, 4 two-week modules
- Reasonable value perception at $750

**Founder decision**: [ ] 90 days / [ ] 30 days / [ ] 60 days / [ ] Other: ______

---

## Decision 4 — Delivery Container

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: Discord community + weekly group call + simple Notion or Google Doc curriculum hub

**Evidence**:
- Discord is referenced in `first_operating_workflow.md` Stages 10–11 as community platform
- Discord is free, supports channels, voice, roles, and bots
- Weekly group call via Discord voice or Google Meet keeps fulfillment lightweight
- Curriculum hub (Notion or Google Doc) keeps course materials accessible without building a platform
- This stack costs $0 and can be set up in under 1 hour

### ALTERNATIVE A: Discord only

- Curriculum delivered as pinned messages or channel posts
- Simpler but less organized

### ALTERNATIVE B: Notion only

- Clean, organized, professional
- Lacks real-time community (can supplement with group chat app)

### ALTERNATIVE C: Skool or WHOP (future)

- Purpose-built for community + courses
- Monthly cost, more setup
- Better after first 5+ students validate the offer

**Founder decision**: [ ] Discord + call + doc hub / [ ] Discord only / [ ] Notion only / [ ] Other: ______

---

## Decision 5 — Curriculum

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: 6-phase curriculum across 90 days

| Phase | Weeks | Focus | Core Activities |
|-------|-------|-------|----------------|
| **0. Onboarding** | Pre-start | Baseline assessment, set expectations, join community | Intro questionnaire, community access, rules review |
| **1. Discipline Reset** | 1–2 | Strip away bad habits, establish non-negotiable daily structure | Morning routine commitment, daily check-in, eliminate one distraction |
| **2. Identity & Environment** | 3–4 | Redefine self-image, optimize environment for execution | Identity statement writing, environment audit, accountability partner pairing |
| **3. Fitness / Energy / Routine** | 5–6 | Physical foundation for execution capacity | Training commitment, sleep protocol, energy management, nutrition basics |
| **4. Skill / Money / Execution Focus** | 7–8 | Apply execution ability to highest-leverage domain | Skill selection, daily execution block, revenue-generating activity identification |
| **5. Brotherhood & Challenge** | 9–10 | Community accountability at maximum intensity | Group challenges, peer accountability pairings, public commitment |
| **6. Integration & Next Path** | 11–12 | Review, cement habits, decide next level | 90-day reflection, progress evidence compilation, Game of Lyfe introduction |

**This is an inferred curriculum based on positioning and brand philosophy.** Actual curriculum may exist in Google Drive "Coaching Frameworks" folder.

### ALTERNATIVE A: 4-phase curriculum across 30 days

| Phase | Week | Focus |
|-------|------|-------|
| 1 | 1 | Foundation — assessment, structure setup |
| 2 | 2 | Execution — daily execution with accountability |
| 3 | 3 | Resistance — handling dips under pressure |
| 4 | 4 | Proof — demonstrating transformation |

### ALTERNATIVE B: Founder writes custom curriculum

- May exist in Google Drive. If so, ingest and use.
- If not, write from scratch based on Antony's methodology.

**Founder decision**: [ ] 6-phase / 90-day / [ ] 4-phase / 30-day / [ ] Custom: ______

---

## Decision 6 — Fulfillment

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: Weekly group call + weekly mission + daily Discord accountability + simple progress tracker

| Component | Frequency | Time Investment |
|-----------|-----------|----------------|
| Group call (Zoom/Discord voice) | Weekly, 60 min | 1 hr/week |
| Weekly mission / check-in | Released weekly | 15 min to prepare |
| Daily Discord accountability | Daily (students post, Antony reviews) | 15–30 min/day |
| Progress tracker | Weekly self-report | 5 min to review per student |
| **Total founder time** | | ~3–4 hrs/week per cohort of 5–10 |

### ALTERNATIVE A: Lighter touch

- Bi-weekly group call, weekly mission, no daily accountability
- ~1.5 hrs/week — better for scaling, worse for results

### ALTERNATIVE B: Heavier touch

- Weekly 1:1 + group call + daily check-in
- ~6–8 hrs/week for 5 students — intensive, highest results, hardest to scale

**Founder decision**: [ ] Default (group call + mission + daily + tracker) / [ ] Lighter / [ ] Heavier / [ ] Custom: ______

---

## Decision 7 — Call Booking

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: Calendly free tier for first test

**Evidence**:
- Referenced in `first_operating_workflow.md` Stage 8
- Free tier supports 1 event type with unlimited bookings
- Integrates with Google Calendar
- Professional and frictionless for prospects

### ALTERNATIVE A: Manual DM scheduling

- "When works for you?" → agree on time → Google Meet link
- Zero setup, maximum friction, fine for first 1–3 calls

### ALTERNATIVE B: Google Calendar appointment scheduling

- Built into Google Workspace
- Free, functional, less polished than Calendly

**Founder decision**: [ ] Calendly / [ ] Manual DM scheduling / [ ] Google Calendar / [ ] Other: ______

---

## Decision 8 — Payment Path

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: Stripe payment link

**Evidence**:
- Referenced in `first_operating_workflow.md` Stage 9
- Professional checkout page, instant confirmation, handles receipts
- Supports one-pay and subscriptions
- 2.9% + $0.30 per transaction
- Can create payment link in <5 minutes from Stripe dashboard

### ALTERNATIVE A: Manual invoice + Cash App/Zelle

- Zero processing fees, maximum trust friction
- Acceptable for first 1–2 sales if Stripe not ready
- No professional checkout experience

### ALTERNATIVE B: Gumroad

- Built-in checkout + delivery
- Higher fees (10%)
- Good if digital product delivery is needed

**Founder decision**: [ ] Stripe payment link / [ ] Manual/Cash App/Zelle / [ ] Gumroad / [ ] Other: ______

---

## Decision 9 — Refund / Guarantee Stance

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: No broad guarantee for founding cohort; clear expectations and fit-based acceptance

**Evidence**:
- Founding cohort framing sets expectations: "You're getting in early. The price reflects that. This is for people who are ready."
- Fit-based acceptance (qualification criteria) reduces refund risk by filtering bad-fit buyers
- Explicit "no refund" stance is acceptable when combined with a thorough qualification conversation
- Avoids creating an incentive for tire-kickers

### ALTERNATIVE A: 7-day refund if they have not accessed onboarding/calls

- Reduces buyer risk without unlimited exposure
- Standard in coaching industry
- Must track access to enforce

### ALTERNATIVE B: Full conditional guarantee

- "Complete all assignments for 90 days. If you don't see results, full refund."
- High trust signal, effectively unclaimable if they do the work
- More complex to administer

**Founder decision**: [ ] No guarantee (founding cohort) / [ ] 7-day refund / [ ] Conditional guarantee / [ ] Other: ______

---

## Decision 10 — Qualification Criteria

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |

### Already decided: 3-of-5 qualification framework

| # | Criterion | Signal |
|---|-----------|--------|
| 1 | Pain intensity — knows they have an execution problem | "I know what to do but can't stick to it" |
| 2 | Urgency — ready now, not someday | "I need to start" language |
| 3 | Willingness to change — wants transformation, not just information | Asks about solutions |
| 4 | Coachability — open to structure and accountability | Responds to suggestions, not defensive |
| 5 | Ability to invest — can invest time and money | No immediate price objection |

Source: `business_test_001_packet.md` — CONFIRMED.

**Founder decision**: [ ] Approve as-is / [ ] Modify: ______

---

## Decision 11 — First Sale Workflow

| Field | Value |
|-------|-------|
| **Status** | NEEDS_FOUNDER_APPROVAL |

### RECOMMENDED_DEFAULT: Manual DM-first workflow

| Step | Action | Tool |
|------|--------|------|
| 1 | Post content (1/day) | Instagram / X / LinkedIn |
| 2 | Engage with comments and adjacent creators | Platform native |
| 3 | DM 5–20 prospects | Platform DMs |
| 4 | Qualify using 3-of-5 framework | Conversation |
| 5 | Book call | Calendly link in DM |
| 6 | Run 20-min sales call | Zoom / Discord voice / Phone |
| 7 | Send payment link | Stripe link in DM |
| 8 | Confirm payment | Stripe notification |
| 9 | Send onboarding message | DM / Email |
| 10 | Grant Discord + curriculum access | Manual |

### ALTERNATIVE: Skip call, close in DMs

- Some coaches close $500–$1000 offers directly in DMs
- Higher friction per conversation, lower conversion
- Acceptable if Antony prefers not to do calls initially

**Founder decision**: [ ] Default workflow (post → DM → qualify → call → close → onboard) / [ ] DM-only close / [ ] Custom: ______

---

## Decision Summary

| # | Decision | Recommended Default | Status |
|---|----------|-------------------|--------|
| 1 | Price | $750 founding cohort | NEEDS_FOUNDER_APPROVAL |
| 2 | Payment structure | One-pay $750 + optional 2-pay $400 | NEEDS_FOUNDER_APPROVAL |
| 3 | Duration | 90 days | NEEDS_FOUNDER_APPROVAL |
| 4 | Delivery container | Discord + weekly call + doc hub | NEEDS_FOUNDER_APPROVAL |
| 5 | Curriculum | 6-phase / 12-week structure | NEEDS_FOUNDER_APPROVAL |
| 6 | Fulfillment | Weekly call + mission + daily accountability | NEEDS_FOUNDER_APPROVAL |
| 7 | Call booking | Calendly free tier | NEEDS_FOUNDER_APPROVAL |
| 8 | Payment path | Stripe payment link | NEEDS_FOUNDER_APPROVAL |
| 9 | Refund/guarantee | No broad guarantee (founding cohort) | NEEDS_FOUNDER_APPROVAL |
| 10 | Qualification | 3-of-5 framework | CONFIRMED |
| 11 | First sale workflow | Post → DM → qualify → call → close → onboard | NEEDS_FOUNDER_APPROVAL |

**Decisions confirmed**: 1/11
**Decisions with recommended defaults**: 10/11
**Decisions blocked**: 0/11

**If all recommended defaults are approved, the offer is sale-ready with zero remaining blockers.**

---

## How to Approve

Option A — approve all defaults at once:
> "Approve all defaults."

Option B — approve with modifications:
> "Approve all except: price is $497, duration is 60 days, no payment plan."

Option C — approve individually:
> "Decision 1: $750 approved. Decision 3: 60 days instead."

After approval, the system will:
1. Update the minimum sellable offer document with final values
2. Finalize all sales assets with approved price, links, and details
3. Generate the first sale-ready execution plan
