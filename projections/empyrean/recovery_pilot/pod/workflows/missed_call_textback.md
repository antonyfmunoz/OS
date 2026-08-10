# WORKFLOW — Missed Call Textback

**Pool:** missed call · **Channel:** SMS · **Priority:** highest in the Pod.

The only workflow that runs 24/7. A homeowner who calls a roofer and gets no
answer calls the next roofer within minutes. This workflow answers in seconds
from the client's own number.

TEST MODE: specification only. Not built in a live sub-account.

---

## Trigger

**Inbound call to the client's business number that is not answered.**

GHL call status that fires the workflow: `no-answer`, `busy`, `failed`, and
`voicemail`. All four. A caller who reaches voicemail and hangs up without
leaving one is the single most common case and the easiest to miss.

**Does not fire on:** answered calls, outbound calls, calls from a number on
the suppression list, calls from a number already in an active workflow, and
calls from a recognized existing-job contact currently mid-project (those
route to the client, not to this sequence).

---

## Timing

| Step | Delay from missed call | Channel | Condition |
|---|---|---|---|
| 1 | **Immediate** (target <60s) | SMS | always |
| 2 | 15 minutes | SMS | no reply to step 1 |
| 3 | 4 hours *(business-hours-shifted)* | SMS | no reply to steps 1-2 |
| — | exit | — | — |

Three touches. Then stop. A homeowner who ignored three texts about their own
phone call does not want a fourth.

**Step 1 is the whole workflow.** Steps 2 and 3 recover a minority. If a
deliverability or latency problem forces a choice, protect step 1.

---

## Business-hours handling

**Step 1 fires 24/7, including nights, weekends, and holidays.** This is the
deliberate exception in the Pod. A homeowner calling a roofer at 9 p.m. has a
reason, and an immediate reply is expected because *they* just called. Silence
for eleven hours is the failure mode this workflow exists to remove.

**Steps 2 and 3 respect quiet hours** (default 20:00-08:00 client-local, a
per-client setting). A step scheduled inside quiet hours is held and released
at 08:00 local. The 4-hour delay in step 3 is measured in business hours.

**Storm exception:** during a declared storm window, quiet hours may be
extended to 21:00 for steps 2-3 on the client's written instruction only.
Never widened by default.

---

## Message copy

Client's voice. Client's number. Outcome language.

**Step 1 — immediate**

```
Hi — this is {{location.name}}. Sorry we couldn't get to the phone just now.
What's going on with your roof? Reply here and we'll get you on the
schedule.

Reply STOP to opt out.
```

**Step 2 — 15 minutes**

```
Still here if you need us. Quickest way is to tell us the address and
what you're seeing — we'll tell you what it takes and when we can be
out.

Reply STOP to opt out.
```

**Step 3 — 4 hours, business hours only**

```
Following up one last time. If you'd rather talk it through, call us
back at {{location.phone}} and ask for whoever's on the schedule —
we'll find you a slot this week.

Reply STOP to opt out.
```

**Copy rules, enforced:**
- First name of the business, never an agency name.
- No mention of anything being automatic, scheduled, or system-sent.
- "Schedule," "crew," "roof," "address," "out this week" — the words a
  homeowner uses.
- Every message ends with `Reply STOP to opt out.`
- Under 320 characters (two SMS segments) per message.

---

## Reply handling

**Any inbound reply immediately stops the sequence.** Every remaining step is
cancelled, not just delayed.

| Reply type | Action |
|---|---|
| Any human reply | Cancel remaining steps · notify client (SMS + in-app) · create A3 LEDGER row with `Response = yes` · start the two-way clock |
| `STOP`, `UNSUBSCRIBE`, `END`, `QUIT`, `CANCEL` | Suppress account-wide, permanently, across all four workflows · confirm once · never contact again |
| `HELP` | Standard help reply with the client's business name and callback number |
| Inbound call back | Treated as a reply — cancel the sequence |

**Notification to the client is part of the workflow, not a nicety.** A
homeowner who replies and then waits two hours for a human is worse off than
if nobody had texted. Target: client notified within 60 seconds of the reply.

---

## Exit conditions

The contact leaves this workflow when any one of these is true:

1. Any reply received (human, STOP, or callback).
2. All three steps sent with no reply.
3. Contact appears on the suppression list at any point.
4. The client's number changes mid-sequence (workflow halts; A6 EXCEPTION,
   type `send failure / deliverability`, owner Delivery).
5. An appointment is booked by any path.

**On exit, always:** write the A3 LEDGER row — `Pool = missed call`, the
origin, the touch history, and whether a response occurred. The ledger is what
the guarantee is adjudicated against, so a workflow that exits without writing
one has produced nothing, regardless of what was sent.

---

## Ledger mapping

- `Pool` → `missed call`
- `Origin` → `storm` or `retail`, inherited from the client's current window
- `Touch History` → step numbers and timestamps sent
- `Response` → yes on any human reply
- `Qualified` → yes only if the reply is a real two-way exchange about an
  agreed job type. A one-word "who is this" is a response, not a qualified
  opportunity.

---

## Gotchas

- **The unanswered-but-not-voicemail case.** Many systems only fire on
  voicemail. Most missed calls never reach it. Verify all four call statuses
  trigger the workflow before going live — this is the single most common
  misconfiguration.
- **Sub-60-second step 1 or it is not worth sending.** A textback that arrives
  ten minutes later reaches a homeowner already talking to a competitor. Alert
  if median step-1 latency exceeds 60 seconds.
- **Do not fire on the client's own outbound calls.** A client calling a
  supplier should not receive their own textback. Filter on direction.
- **Repeat callers.** A number that calls three times in an hour gets **one**
  sequence, not three. Deduplicate on the contact, with a 24-hour window.
- **STOP is account-wide and permanent.** Not per-workflow, not per-pool, not
  expiring. A homeowner who opts out of a missed-call text must never receive
  a past-customer message six months later.
