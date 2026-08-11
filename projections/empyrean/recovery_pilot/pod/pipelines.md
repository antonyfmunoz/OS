# C4 — POD PIPELINES

Two pipelines. One moves a prospect to signed. One moves a client through the
guarantee window to renewal. Stage names are **verbatim** from
`runtime/notion_schema.py` (`PROSPECT_STAGES`, `CLIENT_STAGES`) — agents match
on these exact strings.

TEST MODE: not yet built in a live sub-account.

---

## Pipeline 1 — SALES

Owner: AFM. Mirrors A1 PROSPECTS `Stage`. A prospect occupies exactly one
stage; movement is always forward or to Closed Lost, never sideways.

```
New → Snapshot Sent → Outreach Approved → Call 1 → Access Granted
    → Audit Delivered → Call 2 → Closed Won | Closed Lost
```

Note: `PROSPECT_STAGES` also contains **Outreach Drafted**, which is a Notion
runtime state between Snapshot Sent and Outreach Approved (the draft exists,
awaiting A5 approval). It is not a GHL card stage — a card sitting in a stage
nobody works is a lie. It lives in Notion only.

### New

- **Entry:** B1 Prospector writes an A1 row. Fit Score assigned (A/B/C).
- **Work:** verify the business is real and reachable; confirm declared
  service area; confirm they run crews (not a lead broker or a marketplace).
- **Exit:** Fit Score A or B **and** contact path identified.
- **Exit to Closed Lost:** Fit Score C, out of service area, or no owner reachable.
- **SLA:** 48h in stage.

### Snapshot Sent

- **Entry:** C2 Pipeline Snapshot rendered and delivered via signed link.
- **Work:** the snapshot is outside-in — built from public signals and
  self-reported inputs, never from their systems. It shows an estimated
  picture and states its assumptions on-page.
- **Exit:** snapshot link opened **or** any reply received.
- **Exit to Closed Lost:** no open and no reply after the full outreach
  sequence completes.
- **SLA:** 7 days in stage.
- **Instrumentation:** link opens land in `data/output/link_access.log.jsonl`
  via C0 signed links. An unopened snapshot is a delivery problem, not a
  disinterest signal — check that first.

### Outreach Approved

- **Entry:** A5 APPROVALS row for the outreach message set is `approved`.
- **Work:** the approved sequence runs. Nothing sends before this stage.
- **Exit:** a call is booked on the Call 1 calendar.
- **Exit to Closed Lost:** explicit no, or sequence exhausted with no response.
- **SLA:** 10 days in stage.
- **Hard rule:** if A5 is `pending` or `rejected`, no send occurs. A send with
  no approved row is an incident, not a shortcut.

### Call 1

- **Entry:** call booked (15-20 min, see `calendar.md`).
- **Work:** confirm the conditions precedent by asking, not assuming —
  **≥200 contactable past customers** and **≥50 open estimates ≤12 months
  old**. Capture their average job value and close rate for C1 inputs. Explain
  what access is needed and why (read-only).
- **Exit:** they agree to grant read-only access; access request sent.
- **Exit to Closed Lost:** conditions fail badly (below half either threshold →
  `FAIL` verdict) and they decline the no-guarantee variant.
- **SLA:** call held within 5 business days of booking.
- **Gotcha:** a prospect who says "about 200" has not passed. The verdict is
  computed from the export in the next stage, never from the call. Record what
  they said, mark the verdict `UNKNOWN`, move on.

### Access Granted

- **Entry:** CRM export received (read-only). Data-Handling Addendum terms in
  force from this moment — sole-purpose use, 7-day deletion on a no-go.
- **Work:** B3 Audit Agent runs. Verdict computed from the export:
  `PASS` / `PRO-RATE` / `FAIL`.
- **Exit:** audit rendered and the A5 approval for the delivery email exists.
- **Exit to Closed Lost:** verdict `FAIL` and they decline the alternative path.
- **SLA:** **≤2 hours** export → audit delivered (A9 par: audit turnaround).
- **Gotcha:** export unparseable → A6 EXCEPTION, type `technical question`,
  owner Delivery. Never guess a schema silently.

### Audit Delivered

- **Entry:** signed audit link sent.
- **Work:** the audit shows the verdict **before** the numbers, three pool
  sections, and the assumptions footnote. Every dollar figure is an estimate.
- **Exit:** Call 2 booked.
- **Exit to Closed Lost:** no booking after the follow-up sequence.
- **SLA:** 5 days in stage.

### Call 2

- **Entry:** 30-minute walkthrough booked.
- **Work:** walk the audit. Present the offer: $5,000 start + $2,500/mo,
  3-month initial term, the 20-25 in 30 days guarantee with its cap, and the
  exclusivity tier they are buying (base = shared market; Growth = narrow
  radius; Partner = full declared service area).
- **Exit:** agreement sent via DocuSign **and** Stripe activation invoice sent.
- **Exit to Closed Lost:** declined, or no decision after two follow-ups.
- **SLA:** decision within 7 days of the call.

### Closed Won

- **Entry:** agreement signed **and** the $5,000 start payment has cleared.
  Both. A signature without cleared payment is still Call 2.
- **Action on entry:** A2 CLIENTS row created; Pod cloned; the DELIVERY
  pipeline card is created at Onboarding. Declared service area recorded from
  the agreement's county/ZIP appendix.

### Closed Lost

- **Entry:** any terminal no.
- **Required field:** loss reason — one of `fit`, `conditions`, `timing`,
  `price`, `no-response`, `competitor`.
- **Action on entry:** if a CRM export was received, the 7-day deletion clock
  starts. Written deletion confirmation is owed to them.

---

## Pipeline 2 — DELIVERY

Owner: Delivery. Mirrors A2 CLIENTS `Stage`. The guarantee clock lives here.

```
Onboarding → Active → Day 14 Review → Day 30 Review → Renewal
```

Plus two off-track states from `CLIENT_STAGES`: **At Risk** and **Churned**.
At Risk is a flag-state a client can enter from Active, Day 14, or Day 30, and
can return from. Churned is terminal.

### Onboarding

- **Entry:** Closed Won. Day 0 of the engagement, but **not** day 0 of the
  guarantee clock.
- **Work:**
  1. Clone the Pod; set business hours, service area, and the client's own
     business number.
  2. Import the two pools: past customers (≥200 contactable) and open
     estimates (≤12 months, ≥50).
  3. Load the message library into A4; get the client's approval per template.
  4. Request access by **day 3** (cooperation clause).
- **Exit — all four required:**
  - access granted,
  - both pools imported and counted,
  - A4 templates approved for at least the first two angles per pool,
  - the client has named a decision-maker for 48h approvals.
- **SLA:** 5 business days.
- **The clock:** the 30-day guarantee window starts when this stage exits, not
  when they sign. **Cooperation tolling applies:** any period the client blocks
  on an approval past 48h, or access past day 3, pauses the clock. Every
  tolling event is logged on the A2 record with start and end timestamps —
  a tolling claim with no log entry does not exist.

### Active

- **Entry:** Onboarding exits. Guarantee clock running, day 1.
- **Work:** all four workflows live. Ledger accumulating. Scoreboard (C5)
  rendering and sending on schedule.
- **Exit:** day 14 of the running clock.
- **Monitored daily:** activated qualified opportunities vs par, approval
  latency, send failures, sentiment.
- **Entry to At Risk:** health score below 3.0 (A6 EXCEPTION, owner Owner, 48h
  phone-call SLA), or trailing par at day 14, or two consecutive approval
  overruns.

### Day 14 Review

- **Entry:** clock day 14.
- **Work:** 30-minute review against par. Par at day 14 is roughly half the
  guarantee band — **10-13 activated qualified opportunities**. Show the
  ledger, not a summary of the ledger.
- **Exit:** review held and next-14-day plan agreed.
- **If trailing par:** A6 EXCEPTION type `trailing par day 14`, owner Account,
  24h SLA. Diagnose in this order: (1) are sends landing (deliverability),
  (2) are approvals late (tolling), (3) is the pool thinner than the export
  claimed, (4) is the message set wrong. Change one variable.
- **SLA:** held within 2 business days of day 14.

### Day 30 Review

- **Entry:** clock day 30.
- **Work:** 45-minute review. **Adjudicate the guarantee against the ledger.**
  Count activated qualified opportunities: two-way response + agreed job types
  + ledger-evidenced. Present the count with evidence links.
- **Exit — met (≥20):** → Renewal.
- **Exit — not met (<20):** work continues at **no additional fee**, capped at
  **30 additional days**, then the parties revisit. The client is told this
  before they ask. Card stays in Day 30 Review with an extension flag and an
  extension-end date; it does not move to Renewal until adjudication passes or
  the cap expires.
- **SLA:** held within 2 business days of day 30.
- **Gotcha:** if a tolling log exists, day 30 is 30 *running* days, not 30
  calendar days from start. Compute from the log; do not eyeball a date.
  A guarantee adjudicated on the wrong day is an unforced error.

### Renewal

- **Entry:** guarantee met, or extension period closed and the parties agreed
  to continue.
- **Work:** month 2 and 3 of the initial term run here. Confirm the $2,500/mo
  is collecting. Auto-booked 60- and 90-day reviews. At the end of the 3-month
  initial term: continue, upgrade a rung (First Response System → Demand
  Engine → Growth Partner), or exit.
- **Rung-3+ note:** clients at Demand Engine or above carry the Right of First
  Offer clause. Flag it on the A2 record (`ROFO` field) so it is never
  discovered late.
- **Exit:** renewed (stays in Renewal for the next term) or → Churned.

### At Risk

- **Entry:** health below 3.0, trailing par, or repeated approval overruns.
- **Work:** owner-level call within 48h. One named problem, one named fix, one
  date.
- **Exit:** back to the stage it came from once health ≥3.0 for 7 consecutive
  days, or → Churned.

### Churned

- **Entry:** terminal. Non-renewal or termination.
- **Required:** churn reason, final ledger count, and — if they hold data
  rights under the addendum — deletion confirmation in writing within 7 days.

---

## Cross-pipeline rules

1. **A card exists in exactly one pipeline.** A prospect that becomes a client
   is Closed Won in SALES and Onboarding in DELIVERY — two cards, one entity,
   joined by the A2 `Prospect` relation.
2. **Stage changes are events, not edits.** Every transition writes to the
   runtime with a timestamp. The guarantee, the tolling log, and the SLA
   measurements all read that history.
3. **No stage advances on optimism.** Each exit criterion above is a fact that
   can be pointed at — a link opened, a payment cleared, a file received. If
   you cannot point at it, the card has not moved.
