# WORKFLOW — Past Customer Reactivation

**Pool:** past customer · **Channels:** SMS + email · **Window:** 14 days,
4 touches · **Order:** oldest roofs first.

The client already earned these homeowners. They have the client's crew in
their driveway once before, and they are the warmest audience the client owns.
This pool is the larger half of the conditions precedent (**≥200 contactable
past customers**) and it is what carries the guarantee when the estimate pool
runs thin.

TEST MODE: specification only. Not built in a live sub-account.

---

## Trigger

**Entry into the past-customer pool at onboarding import**, released in batches
on the reactivation schedule.

**Eligibility (all required):**
- a completed job on record
- a valid mobile or email — "contactable" is the word in the conditions
  precedent and it means reachable, not merely listed
- not suppressed
- no open estimate (that contact belongs to estimate follow-up instead)
- **not contacted by this workflow in the last 180 days**

**Excluded:** unresolved complaints or disputes, contacts inside another Pod
workflow, and any address outside the declared service area.

---

## Ordering — oldest roofs first

**Send order is by job completion date, oldest first.** This is the single
highest-signal ordering available and it is not negotiable.

A roof installed 14 years ago is near the end of its life. A roof installed
last year is not. The homeowner with the older roof has a real reason to hear
from the client, which is why the same message performs several times better
at the front of the list than the back.

Batch ordering within a release:

1. **Job age descending** — oldest completed job first.
2. **Then repair-history** — a homeowner with two or more past repairs before
   a homeowner with one clean install.
3. **Then job value ascending** — a past repair customer is a likelier
   full-replacement candidate than a past full-replacement customer.

**Batch size:** default **30 contacts/day**, adjustable per client, subject to
the same rule as every pool — the client must be able to answer every response
the same day.

---

## Timing — 14 days, 4 touches

| Step | Day | Channel | Condition |
|---|---|---|---|
| 1 | Day 1 | SMS | always |
| 2 | Day 4 | Email | no response |
| 3 | Day 8 | SMS | no response |
| 4 | Day 14 | Email | no response |
| — | exit | — | — |

Slower than estimate follow-up by design. There is no deadline here — the
homeowner is not waiting on the client — so the cadence has to feel like a
business checking in, not chasing. Business days, quiet hours respected, no
weekend sends.

---

## Message copy — RETAIL variant

The lead angle is the age of their roof and the fact that the client installed
it. Specific, verifiable, and impossible to mistake for a stranger.

**Step 1 — Day 1, SMS**

```
Hi {{contact.first_name}} — {{location.name}}. We put your roof on
back in {{job.year}}. We're out in {{contact.neighborhood}} this
month and offering free check-ups for roofs we've done. Want us to
take a look while we're nearby?

Reply STOP to opt out.
```

**Step 2 — Day 4, Email**

Subject: `Your roof from {{job.year}} — quick check-up?`

```
{{contact.first_name}},

We installed your roof at {{job.address}} in {{job.year}}. That puts
it at about {{job.age_years}} years.

Roofs that age don't usually fail all at once — it starts with
flashing, sealant around penetrations, and the valleys. Catching it
there is a small job. Catching it after it shows up on your ceiling is
not.

We have crews in {{contact.neighborhood}} this month, so if you want
us to get up there and tell you honestly where it stands, reply with
a good day and we'll come by.

No charge for the look.

{{location.name}}
{{location.phone}}
```

**Step 3 — Day 8, SMS**

```
Still happy to check that roof for you. Takes about 20 minutes and
you get photos of anything we find — no obligation either way.

Reply STOP to opt out.
```

**Step 4 — Day 14, Email**

Subject: `Whenever you're ready`

```
{{contact.first_name}},

We'll leave it here for now — just wanted you to know we're still
around and still working {{contact.neighborhood}}.

If anything ever comes up with the roof, call {{location.phone}} and
we'll get someone out. We keep records of every roof we've installed,
so we'll already know what's up there.

{{location.name}}
```

---

## Message copy — STORM variant

The lead angle is the specific weather event and the fact that their roof —
the one the client installed — sat through it. Concrete event, concrete
address, no fear.

**Step 1 — Day 1, SMS**

```
Hi {{contact.first_name}} — {{location.name}}. We did your roof in
{{job.year}}. After the {{storm.date}} storm we're checking roofs we
installed around {{contact.neighborhood}}. Want us to get up there
and look yours over?

Reply STOP to opt out.
```

**Step 2 — Day 4, Email**

Subject: `Checking roofs we installed after the {{storm.date}} storm`

```
{{contact.first_name}},

We installed your roof at {{job.address}} in {{job.year}}, and the
{{storm.date}} storm came right through {{contact.neighborhood}}.

Wind and hail damage usually isn't visible from the ground. Lifted
shingles, bruised granules, damaged flashing — you often don't know
until it shows up inside. And most carriers have a window on when
damage from a specific storm can be filed.

We're checking roofs we installed in the area. If you want yours
looked at, reply and we'll come by — we'll send you photos of
whatever we find either way.

{{location.name}}
{{location.phone}}
```

**Step 3 — Day 8, SMS**

```
Following up on the storm check for {{job.address}}. If you've
already had someone out, no problem — just let us know and we'll
leave you be.

Reply STOP to opt out.
```

**Step 4 — Day 14, Email**

Subject: `Last note about the {{storm.date}} storm`

```
{{contact.first_name}},

Last time we'll bring this up. If you decide you want your roof
checked after the {{storm.date}} storm, call {{location.phone}} and
we'll get you on the list.

We still have your file from {{job.year}}, so we know exactly what's
on your roof.

{{location.name}}
```

**Storm copy rules:** name a real storm the client can point to; never claim
their roof is damaged before anyone has looked; never state a carrier deadline
the client has not verified; never imply the inspection is required.

---

## Stop-on-response

**Any inbound response cancels every remaining step immediately.**

| Response | Action |
|---|---|
| Any human reply | Cancel remaining · notify client · A3 LEDGER `Response = yes` |
| "Yes, come look" | Cancel · book the check-up · this is the conversion path |
| "Already had it done" | Cancel · mark resolved · park 180 days |
| Complaint about past work | Cancel · **A6 EXCEPTION, type `angry reply / stop request`, owner Delivery, 1h SLA** · escalate to the client immediately |
| `STOP` / `UNSUBSCRIBE` / `END` / `QUIT` / `CANCEL` | Suppress account-wide, permanently |
| Inbound call | Treated as a response — cancel |

**The complaint path matters more than it looks.** Reaching back into a past
customer base surfaces old unresolved work. It happens on every client, and
handled inside an hour it usually ends well. Handled in two days it becomes a
review.

---

## Exit conditions

1. Any response received.
2. All four steps sent with no response.
3. Suppression.
4. Check-up booked.
5. Hard bounce on email **and** SMS failure (A6 EXCEPTION, type
   `send failure / deliverability`, owner Delivery).
6. The contact enters a different pool (an estimate written mid-sequence moves
   them to estimate follow-up).

**On exit, always write the A3 LEDGER row** — `Pool = past customer`, origin,
touch history, response, qualified.

---

## Gotchas

- **180-day cooldown, enforced.** The most common way to damage this pool is
  to run it twice in a quarter because par was trailing. The pool is finite;
  burning it in month one leaves nothing for month three.
- **"Contactable" is a verified reachable contact.** A CRM row with a
  disconnected number is not one of the 200. Validate at import — this
  directly changes the eligibility verdict, and discovering it at day 14 is
  discovering it too late.
- **Old data is wrong data.** Homeowners move. Expect a meaningful share of
  the pool to be a different family now. Copy is written so that a stranger
  receiving it reads as a polite mistake, not an accusation — keep it that way.
- **Never claim damage before an inspection.** Storm copy invites a look; it
  never asserts a finding. This is the difference between a roofer and the
  storm chasers the homeowner already distrusts.
- **A complaint is a one-hour SLA, not a next-day task.** See above.
- **Oldest-first is the ordering, not a suggestion.** Sorting by job value or
  alphabetically wastes the client's response capacity on the least likely
  half of the pool.
