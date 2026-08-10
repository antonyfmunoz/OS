# WORKFLOW — Speed to Lead

**Pool:** missed call (form-origin subtype) · **Channels:** SMS + task ·
**Standard:** first contact inside **5 minutes**, always.

A homeowner who fills out a roofing form has usually filled out three. The
first business to reply in a human voice gets the walkthrough. This workflow
guarantees the client is that business.

TEST MODE: specification only. Not built in a live sub-account.

---

## Trigger

**Any inbound form submission** on the client's surfaces:

- website contact / estimate request form
- landing page forms (storm and retail)
- Google Business Profile message
- Facebook / Instagram inbound message form
- any embedded quote widget

**Does not fire on:** submissions from a suppressed number or email, obvious
spam (see filter below), test submissions from the client's own contact
details, or resubmissions from a contact already inside this workflow within
the last 24 hours.

---

## Timing — the 5-minute standard

| Step | Delay from submission | Channel | Condition |
|---|---|---|---|
| 1 | **Immediate** (target <120s) | SMS | valid mobile present |
| 2 | Immediate | Email | email present |
| 3 | **+5 min** | **Call task** to the client, high priority | no reply yet |
| 4 | +1 hour | SMS | no reply, no call connected |
| 5 | +1 business day | SMS | no reply |
| 6 | +3 business days | Email | no reply |
| — | exit | — | — |

**Step 3 is the point of the workflow.** The texts open the door; a human
calling within five minutes is what converts. The task carries the form
contents so the caller opens with context, not "someone filled out a form."

**Overdue call task:** if step 3 is untouched after 15 minutes, escalate —
re-notify the client, and if still untouched at 60 minutes write an A6
EXCEPTION (type `technical question`, owner Delivery) because a client who
does not work their call tasks will not hit par no matter how well the sends
perform. Catch it in week one, not at day 14.

---

## Business-hours handling

**Steps 1 and 2 fire 24/7.** They are direct replies to something the
homeowner did seconds ago.

**Step 3 (the call task)** is created immediately but flagged
`call at open` when raised outside business hours, and surfaces at the top of
the client's queue at 08:00 local. Nobody calls a homeowner at 11 p.m.

**Steps 4-6** respect quiet hours (default 20:00-08:00 client-local); delays
are measured in business hours.

**After-hours copy differs** — see step 1 below. Promising an immediate call
at midnight and not making one is worse than saying "first thing."

---

## Message copy

Client's voice. Client's number. Outcome language.

**Step 1 — immediate, business hours**

```
Hi {{contact.first_name}} — {{location.name}} here. Got your request
about your roof. Someone's calling you in the next few minutes. If now
is bad, reply with a better time.

Reply STOP to opt out.
```

**Step 1 — immediate, after hours**

```
Hi {{contact.first_name}} — {{location.name}} here. Got your request
about your roof. We'll call you first thing in the morning. If it's
urgent tonight, reply URGENT and we'll get someone on it.

Reply STOP to opt out.
```

**Step 2 — immediate, email**

Subject: `We got your request — {{location.name}}`

```
{{contact.first_name}},

Thanks for reaching out. We have your request and someone from our
crew is calling you shortly.

What you sent us:
{{form.summary}}

If it's easier, reply to this email with your address and a photo of
what you're seeing and we'll tell you what it takes and when we can be
out.

{{location.name}}
{{location.phone}}
```

**Step 4 — +1 hour**

```
Tried reaching you about your roof. Still want to get you on the
schedule — what's the address and what are you seeing?

Reply STOP to opt out.
```

**Step 5 — +1 business day**

```
Following up on your request. We have crews out in your area this week
— want us to take a look while we're nearby?

Reply STOP to opt out.
```

**Step 6 — +3 business days, email**

Subject: `Still want us to take a look?`

```
{{contact.first_name}},

Checking in one more time about your roof. If the timing isn't right,
no trouble at all — just reply and tell us when to check back.

If you'd rather talk, call {{location.phone}}.

{{location.name}}
```

**Copy rules, enforced:** every SMS ends with `Reply STOP to opt out.`; under
320 characters; the client's business name in the first line; no reference to
anything automatic or system-sent.

---

## Reply handling

**Any inbound reply cancels every remaining step.**

| Reply | Action |
|---|---|
| Any human reply | Cancel remaining · notify client immediately · A3 LEDGER `Response = yes` |
| `URGENT` (after-hours path) | Notify the client by SMS **and** call; escalate to on-call |
| `STOP` / `UNSUBSCRIBE` / `END` / `QUIT` / `CANCEL` | Suppress account-wide, permanently |
| `HELP` | Standard help reply with business name and callback number |
| Answered call from step 3 | Cancel remaining · log the outcome on the task |

---

## Spam and validity filter

Runs before step 1. A workflow that texts spam submissions burns the client's
number reputation and, with it, every other workflow in the Pod.

Suppress the sequence (log, do not send) when:

- the phone is invalid, not mobile, or fails carrier lookup
- the submission contains a URL in a name or address field
- name and message are identical strings, or either is a single character
- three or more submissions from the same IP within 60 seconds
- the address is outside the declared service area by more than 50 miles
  (flag for the client rather than discarding — service areas have edges)

Filtered submissions still write an A3 LEDGER row, marked filtered. They never
count toward the guarantee.

---

## Exit conditions

1. Any reply received.
2. All six steps sent with no reply.
3. Suppression at any point.
4. Appointment booked by any path.
5. Call task completed with a "reached" outcome.
6. Send failure on both SMS and email (A6 EXCEPTION, type
   `send failure / deliverability`, owner Delivery, 0h SLA).

**On exit, always write the A3 LEDGER row.**

---

## Ledger mapping

- `Pool` → `missed call` (form-origin subtype recorded in `Touch History`)
- `Origin` → `storm` or `retail` from the current client window
- `Response` → yes on any human reply or connected call
- `Qualified` → yes only on a two-way exchange about an agreed job type

---

## Gotchas

- **Five minutes is measured to first *human* contact, not first send.** A
  text in 30 seconds and a call in two hours is a failed speed-to-lead. Measure
  and alert on step-3 completion, not step-1 delivery.
- **After-hours copy must not promise an immediate call.** Use the after-hours
  variant. A broken small promise at midnight costs the appointment.
- **Do not double-fire with missed-call textback.** A homeowner who submits a
  form and then calls should get one sequence. Deduplicate on the contact
  across both workflows with a 24-hour window; speed-to-lead wins, because it
  has the form contents.
- **The call task must carry the form contents.** A task that says only "call
  this lead" produces a cold-sounding call and wastes the five minutes it took
  to earn.
- **Validate mobile before texting.** Landline submissions are common; texting
  one produces a silent failure that looks like disinterest in the ledger.
