# C4 — POD CALENDARS

Five calendar types. Two sell, three deliver. Every one exists so a specific
pipeline stage has a booking surface — a calendar with no stage that feeds it
does not belong in the Pod.

TEST MODE: not yet built in a live sub-account.

---

## Summary

| # | Calendar | Duration | Feeds stage | Booked by | Auto-booked |
|---|---|---|---|---|---|
| 1 | Call 1 — Fit Call | 20 min | SALES: Call 1 | Prospect | No |
| 2 | Call 2 — Audit Walkthrough | 30 min | SALES: Call 2 | Prospect | No |
| 3 | Day 14 Review | 30 min | DELIVERY: Day 14 Review | System | Yes |
| 4 | Day 30 Review | 45 min | DELIVERY: Day 30 Review | System | Yes |
| 5 | 60/90-Day Review | 30 min | DELIVERY: Renewal | System | Yes |

---

## 1. Call 1 — Fit Call (20 min)

- **Slot length:** 20 minutes, with a 15-minute minimum honored if the
  prospect's own calendar is tight. Book 20; it usually runs 17.
- **Buffer:** 10 min after. **Notice:** 2 hours minimum. **Window:** 10
  business days out.
- **Availability:** business hours only, in the **prospect's** timezone.
- **Booking form fields:** company, name, mobile, email, declared service
  area, approximate past-customer count, approximate open-estimate count.
- **Confirmation + reminders:** confirmation immediately; reminder 24h before
  (email + SMS); reminder 1h before (SMS).
- **Purpose:** establish fit and the conditions precedent, and get agreement
  to read-only access. Not a pitch.

**Outcome recorded on the A1 row:** stated past-customer count, stated
open-estimate count, average job value, close rate, access agreed yes/no.
Those first two are *stated*, not verified — the verdict comes from the export.

**Gotcha:** the counts a prospect gives on this call are consistently
optimistic. Record them as stated and set `Eligibility Verdict` to `UNKNOWN`
until B3 computes it. Never move to Closed Won on stated numbers.

---

## 2. Call 2 — Audit Walkthrough (30 min)

- **Slot length:** 30 minutes. **Buffer:** 15 min after.
- **Notice:** 4 hours. **Window:** 7 days out — this call goes stale fast.
- **Availability:** business hours, prospect's timezone.
- **Prerequisite:** the audit is rendered and the link has been sent. Never
  offer this calendar before Audit Delivered.
- **Reminders:** 24h before (email, with the audit link again); 1h before (SMS).

**Purpose:** walk the audit, present the offer, name the exclusivity tier, and
ask for the decision. The agreement and the Stripe invoice go out from this
call — not "later this week."

**Gotcha:** if the audit link has not been opened before this call, open it
together on the call rather than presenting from memory. The verdict must be
on screen before any dollar figure is discussed.

---

## 3. Day 14 Review (30 min)

- **Auto-booked** when the DELIVERY card enters **Active**, scheduled for
  clock day 14.
- **Buffer:** 15 min after. **Reschedule window:** ±2 business days.
- **Attendees:** client decision-maker (required), Delivery, Account.
- **Reminders:** 48h before (email, with the current scoreboard link); 2h
  before (SMS).

**Purpose:** progress against par. Par at day 14 is **10-13 activated
qualified opportunities** — roughly half the 20-25 band.

**Agenda, in order:** ledger count vs par · what has been sent and delivered ·
approval latency (theirs) · one change for the next 14 days.

**Gotcha:** this booking must move with the clock. If a tolling event pauses
the guarantee clock, the Day 14 review reschedules to the new clock day 14.
A review held on calendar day 14 after a 4-day tolling pause is a review held
on clock day 10, and it will read as trailing par when it is not.

---

## 4. Day 30 Review (45 min)

- **Auto-booked** at Active entry for clock day 30. Longest slot in the Pod —
  this is the adjudication.
- **Buffer:** 30 min after. **Reschedule window:** ±2 business days.
- **Attendees:** client decision-maker (required), Delivery, Account, Owner.
- **Reminders:** 72h before (email, with the full ledger export attached); 24h
  before (email); 2h before (SMS).

**Purpose:** adjudicate the guarantee against the ledger, in front of them.

**Agenda, in order:**
1. The count: activated qualified opportunities, each with evidence.
2. The verdict against 20-25.
3. If met → renewal terms and the rung above.
4. If not met → the extension is stated plainly: work continues at no
   additional fee for up to 30 more days, then the parties revisit.
5. Jobs booked and job value — reported, never guaranteed.

**Gotcha:** compute clock day 30 from the tolling log, not the calendar. And
never open this meeting with jobs booked — the guarantee is opportunities. The
moment revenue leads the meeting, the guarantee is silently redefined into
something we did not sell.

---

## 5. 60/90-Day Review (30 min)

- **Auto-booked** on entry to **Renewal**, at clock days 60 and 90.
- **Buffer:** 15 min. **Attendees:** client decision-maker, Account.
- **Reminders:** 48h before (email, scoreboard link); 2h before (SMS).

**Purpose:** hold the initial term together and set up the term decision at
day 90. Day 60 is a check. Day 90 is the decision: continue, move up a rung
(First Response System → Demand Engine → Growth Partner), or exit.

**At the 90-day review, always confirm:** the declared service area is
unchanged, the exclusivity tier is the tier being paid for, and — for Demand
Engine and above — that the Right of First Offer clause is understood.

---

## Pod-wide calendar settings

- **Timezone:** every prospect-facing calendar renders in the *prospect's*
  timezone; every client-facing calendar renders in the *client's*. Never the
  agency's.
- **Business hours:** a per-client setting. The default is Mon-Fri 8:00-17:00
  local. Reviews never auto-book outside it.
- **Blackout:** no auto-booked review lands on a US federal holiday — it rolls
  to the next business day, and the guarantee clock does **not** pause for it
  (a holiday is not a tolling event).
- **Round-robin:** off. Single assigned owner per calendar. A homeowner-facing
  business buying a guarantee should meet the same person each time.
- **Cancellation:** any cancellation of an auto-booked review writes an A6
  EXCEPTION (type `approval overdue 48h`, owner Account) if it is not rebooked
  within 48 hours. A review that quietly disappears is how a guarantee gets
  adjudicated by surprise.
- **Recording:** reviews are recorded only with explicit consent, captured on
  the booking form.
