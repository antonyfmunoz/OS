# WORKFLOW — Estimate Follow-Up

**Pool:** open estimate · **Channels:** SMS + email · **Window:** 10 days,
4 touches.

An estimate written and never answered is a job the client already did the
work to earn. This workflow finishes it. This pool is half the conditions
precedent (**≥50 open estimates ≤12 months old**) and it is the fastest pool
to produce activated qualified opportunities inside the 30-day window.

TEST MODE: specification only. Not built in a live sub-account.

---

## Trigger

**Entry into the open-estimate pool at onboarding import**, and thereafter any
estimate that reaches `open` status with no homeowner response for 48 hours.

**Eligibility (all required):**
- estimate dated **within the last 12 months** (`OPEN_ESTIMATE_MAX_AGE_MONTHS`)
- status is genuinely open — not won, not lost, not withdrawn
- a valid mobile or email exists
- the contact is not suppressed
- the job type is on the client's agreed list

**Excluded:** estimates older than 12 months (the conditions precedent do not
count them, so neither does the workflow), resolved estimates, and any contact
already active in another Pod workflow.

---

## Timing — 10 days, 4 touches

| Step | Day | Channel | Condition |
|---|---|---|---|
| 1 | Day 1 | SMS | always |
| 2 | Day 3 | Email | no response |
| 3 | Day 6 | SMS | no response |
| 4 | Day 10 | Email | no response |
| — | exit | — | — |

Alternating channels. Days are **business days**; all sends respect quiet
hours (default 20:00-08:00 client-local). No step fires on a weekend — an
estimate follow-up on a Sunday morning reads as pressure.

**Batching:** at onboarding the pool can be large. Release in daily batches
sized to what the client can actually answer — default **40 contacts/day**,
adjustable per client. Two rules govern the cap: the client must be able to
answer every response the same day, and the number's reputation must not spike.
A pool of 300 released at once produces 30 responses in an hour and a client
who answers none of them.

---

## Message copy — RETAIL variant

Retail is planned work. The homeowner is deciding, not reacting. Tone is
patient and specific.

**Step 1 — Day 1, SMS**

```
Hi {{contact.first_name}} — {{location.name}}. We put together a
number for your roof back on {{estimate.date}} and never heard back.
Still want to get it on the schedule, or has the timing changed?

Reply STOP to opt out.
```

**Step 2 — Day 3, Email**

Subject: `Your roof estimate from {{estimate.date}}`

```
{{contact.first_name}},

Following up on the estimate we put together for
{{estimate.address}} — {{estimate.summary}}.

A few things worth knowing:
- The number still stands through {{estimate.valid_through}}.
- Materials have been moving, so waiting usually costs more, not less.
- We have crews working your area over the next few weeks, so getting
  you on the schedule is straightforward right now.

Reply with a good day and we'll get you booked. If you've gone
another direction, tell us and we'll close it out.

{{location.name}}
{{location.phone}}
```

**Step 3 — Day 6, SMS**

```
Quick one — anything about the estimate you want us to walk through?
Some of it comes down to material choice and we can talk you through
what actually matters for your roof.

Reply STOP to opt out.
```

**Step 4 — Day 10, Email**

Subject: `Closing out your file?`

```
{{contact.first_name}},

We haven't heard back, so we're going to close out the file on
{{estimate.address}} unless you tell us otherwise.

If you still want the work done — this year or next — reply and we'll
keep you on the list and check back when it makes sense.

Either way, thanks for having us out.

{{location.name}}
{{location.phone}}
```

---

## Message copy — STORM variant

Storm is time-boxed. There is a real deadline (carrier filing windows) and a
real crew-availability constraint. Tone is urgent but never alarmed, and never
manufactures a threat.

**Step 1 — Day 1, SMS**

```
Hi {{contact.first_name}} — {{location.name}}. We looked at your roof
after the {{storm.date}} storm and put a number together. Are you
still working through it with your carrier? We can help with that
part.

Reply STOP to opt out.
```

**Step 2 — Day 3, Email**

Subject: `Your roof from the {{storm.date}} storm`

```
{{contact.first_name}},

Following up on {{estimate.address}}.

Two things that matter on storm work:
- Carriers have filing windows. Waiting too long can close the door
  on covering it, and that timing is not something we control.
- Our crews are working {{storm.area}} now. Once they move on, the
  next opening is further out.

If you want, send us your claim number and we'll walk you through
what's next. If you've already had it handled, just say so and we'll
close it out.

{{location.name}}
{{location.phone}}
```

**Step 3 — Day 6, SMS**

```
Checking in on the storm work at {{estimate.address}}. If the carrier
came back low or confusing, send us what they sent you — we read
those all day and can tell you what it means.

Reply STOP to opt out.
```

**Step 4 — Day 10, Email**

Subject: `Last check on your storm claim`

```
{{contact.first_name}},

Last time we'll reach out about {{estimate.address}}.

If your claim is still open, we can still help — reply and we'll pick
it back up. If it's handled or you've gone another direction, that's
completely fine.

{{location.name}}
{{location.phone}}
```

**Storm copy rules:** never state a specific carrier deadline the client has
not verified; never imply a claim will be denied; never suggest the homeowner
will not owe a deductible. Urgency comes from crew availability and real
filing windows, never from fear.

---

## Ordering inside the pool

Send order within each daily batch:

1. **Highest estimate value first** — a $40,000 estimate deserves the first
   slot in the client's response capacity.
2. **Then most recent** — a 3-week-old estimate answers better than a
   10-month-old one.
3. Storm-origin estimates inside an open filing window jump the queue, since
   their window closes and a retail estimate's does not.

---

## Stop-on-response

**Any inbound response cancels every remaining step immediately.**

| Response | Action |
|---|---|
| Any human reply | Cancel remaining · notify client · A3 LEDGER `Response = yes` |
| "Already done" / "went with someone else" | Cancel · mark the estimate resolved · **never re-enter this contact into this pool** |
| "Not now, check back later" | Cancel · park with the stated date · hand to past-customer reactivation at that date |
| `STOP` / `UNSUBSCRIBE` / `END` / `QUIT` / `CANCEL` | Suppress account-wide, permanently |
| Inbound call | Treated as a response — cancel |

---

## Exit conditions

1. Any response received.
2. All four steps sent with no response.
3. Estimate status changes to won or lost by any path.
4. Suppression.
5. Appointment booked.
6. Hard bounce on email **and** SMS failure (A6 EXCEPTION, type
   `send failure / deliverability`, owner Delivery).

**On exit, always write the A3 LEDGER row** — `Pool = open estimate`, origin,
touch history, response, qualified, and the estimate value in `Job Value`.

---

## Gotchas

- **The 12-month boundary is the same one the guarantee uses.** If the
  workflow includes older estimates, the delivered count stops reconciling
  with the qualification math in `engine/pipeline_math.py`. Filter on age at
  entry, not at report time.
- **"Open" in a CRM is frequently wrong.** Many estimates marked open were
  verbally won or lost months ago. Expect this, and treat "already done"
  replies as data quality signal, not failure — but never let one produce a
  second message.
- **Never re-enter a resolved contact.** A homeowner who already told the
  client no, receiving the same sequence again, is the fastest route to an
  angry reply (A6 EXCEPTION, owner Delivery, 1h SLA).
- **Do not exceed the daily batch cap to hit par faster.** Volume spikes hurt
  deliverability, and an undelivered message cannot become a response.
- **Storm and retail must not be mixed in one batch.** They have different
  urgency and different copy; a mixed batch means one of them is wrong.
