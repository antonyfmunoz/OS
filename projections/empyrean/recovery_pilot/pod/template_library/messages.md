# MESSAGE LIBRARY — 8 angles × 3 pools × storm/retail (artifact 4.1)

Nothing sends without a row in A4 MESSAGE TEMPLATES with Approval Status = approved.
Every message: client's voice, from the client's number, under the client's own
customer relationship. Every SMS ends with the opt-out line. Quiet hours 8am–8pm
recipient local. Merge fields: `{first_name}` `{client_company}` `{owner_first}`
`{estimate_month}` `{estimate_amount}` `{year_roofed}` `{city}`.

Angles: 1 check-in · 2 price-move · 3 season/weather · 4 neighbor proof ·
5 expiration · 6 question · 7 value-add · 8 last-call.
Storm variants exist where hail/wind framing changes the message; otherwise retail text is used for both.

**Two channels.** Each pool below carries an SMS layer and an EMAIL layer. The
email layer is load-bearing, not decorative: `estimate_followup.md` sends email
on day 3 and day 10, and `past_customer_reactivation.md` sends email on day 4
and day 14. Those touches have no approved copy without it.

---

## A4 field mapping

Each message below is one row in A4 MESSAGE_TEMPLATES
(`runtime/notion_schema.py`).

| A4 field | Values |
|---|---|
| `Pool` | `missed call` · `open estimate` · `past customer` |
| `Origin` | `storm` · `retail` |
| `Angle` | check-in · price-move · season/weather · neighbor proof · expiration · question · value-add · last-call |
| `Channel` | `sms` · `email` |
| `Body` | the copy below, localized to the client's voice |
| `Approval Status` | `draft` → `pending` → `approved` |
| `Approved Date` / `Approver` | recorded at approval |

**Template naming:** `{pool}-{origin}-{angle}-{channel}`, e.g.
`open-estimate-storm-expiration-email`.

---

## POOL: Open estimates

### SMS

**1 · check-in (retail/storm)**
> Hi {first_name}, it's {owner_first} at {client_company}. We still have your estimate from {estimate_month} — want us to get you on the calendar, or has the timing changed? Reply STOP to opt out.

**2 · price-move (retail)**
> {first_name}, {owner_first} here at {client_company}. Material prices moved since your {estimate_month} estimate — if you'd like, we'll re-quote it free so you're working with real numbers. Reply STOP to opt out.

**2 · price-move (storm)**
> {first_name}, {owner_first} at {client_company}. If your insurance settlement is still open, we'll re-check your {estimate_month} estimate against it free — most change after adjuster review. Reply STOP to opt out.

**3 · season/weather (retail)**
> Hi {first_name} — {owner_first}, {client_company}. Rain season's coming and our calendar for {city} is filling. Your estimate from {estimate_month} still stands — want a spot before the weather turns? Reply STOP to opt out.

**3 · season/weather (storm)**
> {first_name}, {owner_first} at {client_company}. Another storm season is close, and the damage we quoted in {estimate_month} won't wait it out well. Want us to hold you a crew slot? Reply STOP to opt out.

**4 · neighbor proof (retail/storm)**
> Hi {first_name}, {owner_first} at {client_company}. We just wrapped two roofs near you in {city} — while the crew's in the area we can honor your {estimate_month} estimate. Worth a quick call? Reply STOP to opt out.

**5 · expiration (retail/storm)**
> {first_name}, quick heads-up from {client_company}: your estimate from {estimate_month} expires soon. If it's still on your mind, reply here and we'll lock the number in. Reply STOP to opt out.

**6 · question (retail/storm)**
> Hi {first_name}, {owner_first} at {client_company}. Honest question — what held things up after our estimate in {estimate_month}? Price, timing, or something we could have done better? A one-word reply helps. Reply STOP to opt out.

**7 · value-add (retail)**
> {first_name}, {owner_first} here. Even if you're not ready, we'll do a free gutter-and-flashing check while your estimate's on file — keeps small things from becoming big ones. Want it this week? Reply STOP to opt out.

**7 · value-add (storm)**
> {first_name}, {owner_first} at {client_company}. Free 10-minute weather check for homes we quoted after the storm — no obligation, keeps your interior dry while you decide. Want it? Reply STOP to opt out.

**8 · last-call (retail/storm)**
> Hi {first_name} — last note from {client_company} on your {estimate_month} estimate. If the project's off, no hard feelings; reply CLOSED and we'll file it. If it's still on, reply YES and we'll take it from there. Reply STOP to opt out.

### EMAIL

Used on the day 3 and day 10 touches of `estimate_followup.md`.

**1 · check-in (retail/storm)**
> **Subject:** Your estimate from {estimate_month}
>
> {first_name},
>
> Following up on the estimate we put together for your roof back in
> {estimate_month}. We never heard back and wanted to check whether you still
> want the work done or the timing shifted.
>
> Either answer is fine — we'd just rather know where you stand than keep
> wondering. Reply and we'll take it from there.
>
> {owner_first}
> {client_company}

**2 · price-move (retail)**
> **Subject:** Your number from {estimate_month} still holds
>
> {first_name},
>
> The estimate we wrote in {estimate_month} is still good, but material
> pricing has moved more than once since then. If you book it now we hold that
> number. If we have to write it fresh later, it will be a different one.
>
> Reply with a good week and we'll get you on the calendar.
>
> {owner_first}
> {client_company}

**2 · price-move (storm)**
> **Subject:** If the carrier came back low
>
> {first_name},
>
> On the storm work we quoted in {estimate_month}: if your carrier's number
> came back under what the roof actually takes, that happens constantly and it
> doesn't have to be the final word.
>
> Forward us what they sent and we'll tell you what's missing from it. We read
> these every day.
>
> {owner_first}
> {client_company}

**3 · season/weather (retail)**
> **Subject:** Good window coming for your roof
>
> {first_name},
>
> We're scheduling work around {city} now and your estimate from
> {estimate_month} came up. This is the stretch where crews move fastest and
> the weather cooperates.
>
> Once the calendar commits, the next opening moves out several weeks. Want us
> to hold you a slot?
>
> {owner_first}
> {client_company}

**3 · season/weather (storm)**
> **Subject:** More weather coming to {city}
>
> {first_name},
>
> There's more weather moving through the area, and the damage we quoted in
> {estimate_month} is still open on our board. A roof already knocked around
> by one storm handles the next one worse.
>
> If you want us back out, reply and we'll get you scheduled.
>
> {owner_first}
> {client_company}

**4 · neighbor proof (retail/storm)**
> **Subject:** Crews on your street this month
>
> {first_name},
>
> We have crews working {city} over the next few weeks — a couple of your
> neighbors have us out.
>
> Since we already priced your roof in {estimate_month}, adding you while
> we're right there is straightforward. Reply and we'll fit you in.
>
> {owner_first}
> {client_company}

**5 · expiration (retail)**
> **Subject:** Your estimate expires soon
>
> {first_name},
>
> Quick heads-up: the estimate we wrote in {estimate_month} is coming up on
> its expiration. After that we have to price it against current material,
> which is running higher.
>
> If you want to lock the number you already have, reply and we'll get you on
> the calendar.
>
> {owner_first}
> {client_company}

**5 · expiration (storm)**
> **Subject:** The filing window on your claim
>
> {first_name},
>
> Carriers generally limit how long after a specific storm damage can be
> filed, and that timing isn't ours to control. Your roof is still open on our
> end from {estimate_month}.
>
> If the claim hasn't been settled, it's worth moving now rather than later.
> Reply and we'll help you through it.
>
> {owner_first}
> {client_company}

**6 · question (retail/storm)**
> **Subject:** Price, timing, or someone else?
>
> {first_name},
>
> We'd rather know than guess. On the estimate from {estimate_month}: was it
> the price, the timing, or did you go with someone else?
>
> If it's price, we can talk through options. If it's timing, we'll check back
> when you say. If it's someone else, no hard feelings — just tell us and
> we'll close it out.
>
> {owner_first}
> {client_company}

**7 · value-add (retail)**
> **Subject:** Want to walk through the estimate?
>
> {first_name},
>
> Roofing estimates are hard to compare because everyone writes them
> differently.
>
> Happy to get on the phone for ten minutes and walk through ours line by
> line — what's structural, what's optional, and where the real cost sits.
> Useful even if you end up using someone else.
>
> Reply with a good time.
>
> {owner_first}
> {client_company}

**7 · value-add (storm)**
> **Subject:** Send us the carrier paperwork
>
> {first_name},
>
> Carrier documents are written to be hard to read.
>
> Forward us what they sent and we'll tell you in plain language what they
> covered, what they left out, and whether the number matches the roof. No
> charge and no obligation.
>
> {owner_first}
> {client_company}

**8 · last-call (retail/storm)**
> **Subject:** Closing out your file?
>
> {first_name},
>
> We haven't heard back, so we're going to close out your file from
> {estimate_month} unless you tell us otherwise.
>
> If you still want the work done — this year or next — reply and we'll keep
> you on the list and check back when it makes sense.
>
> Either way, thanks for having us out.
>
> {owner_first}
> {client_company}

---

## POOL: Past customers

### SMS

**1 · check-in (retail/storm)**
> Hi {first_name}, {owner_first} at {client_company} — we did your roof in {year_roofed}. Just checking in: everything holding up the way it should? Reply STOP to opt out.

**2 · price-move (retail/storm)**
> {first_name}, {owner_first} at {client_company}. Roofs we installed around {year_roofed} are hitting the age where small repairs cost hundreds, not thousands. Want a free condition report on yours? Reply STOP to opt out.

**3 · season/weather (retail)**
> Hi {first_name} — {owner_first}, {client_company}. Before rain season: want us to do a quick check on the roof we put on in {year_roofed}? Free for past customers. Reply STOP to opt out.

**3 · season/weather (storm)**
> {first_name}, {owner_first} at {client_company}. That last storm hit {city} hard. We know your roof — we installed it in {year_roofed}. Want a free storm check before insurance windows close? Reply STOP to opt out.

**4 · neighbor proof (retail/storm)**
> Hi {first_name}, {owner_first} at {client_company}. We're back in your neighborhood this month. Since we know your {year_roofed} roof, a check-up takes us 15 minutes — free. Want one? Reply STOP to opt out.

**5 · expiration (retail/storm)**
> {first_name}, a note from {client_company}: workmanship coverage on your {year_roofed} roof has a review window coming up. A quick inspection keeps everything on record. Want us to book it? Reply STOP to opt out.

**6 · question (retail/storm)**
> Hi {first_name}, {owner_first} here at {client_company}. Anything about the house you've been putting off — gutters, vents, a slow drip somewhere? We handle more than roofs for past customers. Reply STOP to opt out.

**7 · value-add (retail/storm)**
> {first_name}, {owner_first} at {client_company}. Free annual roof check for everyone we've built for — photos included, so you have a record for insurance. Want yours scheduled? Reply STOP to opt out.

**8 · last-call (retail/storm)**
> Hi {first_name} — {client_company} here. We keep our past-customer list tight. Want to stay on it for free check-ups and first-in-line scheduling, or should we close your file? Reply YES or CLOSED. Reply STOP to opt out.

### EMAIL

Used on the day 4 and day 14 touches of `past_customer_reactivation.md`.
Sent oldest roofs first — see that workflow for the ordering rule.

**1 · check-in (retail/storm)**
> **Subject:** How's the roof holding up?
>
> {first_name},
>
> We installed your roof back in {year_roofed}. Just checking in — anything
> you've noticed since?
>
> If you want us to come take a look, reply and we'll set it up. No charge for
> the look.
>
> {owner_first}
> {client_company}

**2 · price-move (retail/storm)**
> **Subject:** Cheaper now than later — your {year_roofed} roof
>
> {first_name},
>
> Roofs we installed around {year_roofed} are hitting the age where it's
> usually flashing and sealant. That's a small job.
>
> Left alone it becomes decking, which is not. We'd rather catch it while it's
> still the small version. Reply and we'll come look — free for past
> customers.
>
> {owner_first}
> {client_company}

**3 · season/weather (retail)**
> **Subject:** Before the weather turns
>
> {first_name},
>
> This is the season that finds every weak spot on a roof. We're going around
> checking roofs we installed in {city} before it sets in.
>
> Yours went on in {year_roofed}. Want it on the list? Free for past
> customers.
>
> {owner_first}
> {client_company}

**3 · season/weather (storm)**
> **Subject:** Checking roofs we installed after the storm
>
> {first_name},
>
> That last storm hit {city} hard, and we know your roof — we installed it in
> {year_roofed}.
>
> Wind and hail damage usually isn't visible from the ground. We're checking
> roofs we put on in the area, and there's no charge for the look. Reply and
> we'll add yours.
>
> {owner_first}
> {client_company}

**4 · neighbor proof (retail/storm)**
> **Subject:** We're back in your neighborhood
>
> {first_name},
>
> We're working {city} this month doing check-ups on roofs we installed — a
> few of your neighbors are already on the list.
>
> We put yours on in {year_roofed}, so a check-up takes us about 15 minutes.
> Easy to add you while we're right there.
>
> {owner_first}
> {client_company}

**5 · expiration (retail/storm)**
> **Subject:** Where your {year_roofed} roof stands
>
> {first_name},
>
> Your roof is coming up on the age where manufacturer coverage has time
> limits and conditions, and some of them depend on the roof having been
> looked at.
>
> We're happy to get up there, tell you honestly where it stands, and what's
> still covered. Reply and we'll come by.
>
> {owner_first}
> {client_company}

**6 · question (retail/storm)**
> **Subject:** Noticed anything up there?
>
> {first_name},
>
> One question about the roof we put on in {year_roofed}: have you seen
> anything in the attic or on the ceilings — staining, daylight, anything at
> all?
>
> Small marks tell us a lot and they're cheap to handle early. Reply either
> way and we'll tell you whether it's worth a look.
>
> {owner_first}
> {client_company}

**7 · value-add (retail/storm)**
> **Subject:** Free annual check on your roof
>
> {first_name},
>
> We do free annual checks on every roof we've built.
>
> Takes about 20 minutes: we get up there, photograph everything, and send you
> the pictures with a plain-language read on where it stands. You keep the
> photos — useful to have on file for insurance.
>
> Yours went on in {year_roofed}. Reply with a good day.
>
> {owner_first}
> {client_company}

**8 · last-call (retail/storm)**
> **Subject:** Whenever you're ready
>
> {first_name},
>
> We'll leave it here for now — just wanted you to know we're still around and
> still working {city}.
>
> If anything ever comes up with the roof, reply or call and we'll get someone
> out. We keep records of every roof we've installed, so we'll already know
> what's up there.
>
> {owner_first}
> {client_company}

---

## POOL: Unanswered calls (textback)

### SMS

**1 · check-in / instant textback (retail/storm)** — fires within 60 seconds
> Hi, this is {client_company} — sorry we couldn't get to the phone. How can we help with your roof? Reply here and {owner_first} will get right back to you. Reply STOP to opt out.

**2 · price-move (retail/storm)** — same-day follow-up if no reply
> {client_company} again — if you were calling about an estimate, we can usually get eyes on your roof within 48 hours. Want us to set that up? Reply STOP to opt out.

**3 · season/weather (storm)**
> This is {client_company}. If your call was about storm damage: we're prioritizing {city} homes this week and can document everything for your insurance. Reply and we'll call you back. Reply STOP to opt out.

**4 · neighbor proof (retail/storm)**
> {client_company} here — we're working several homes in {city} right now, which is probably why you found us. Reply with a good time and {owner_first} will call you personally. Reply STOP to opt out.

**5 · expiration (retail/storm)** — day 2
> Hi, {client_company}. We hold callback slots for 48 hours — yours is still open today. Reply with a time that works and we'll take it from there. Reply STOP to opt out.

**6 · question (retail/storm)**
> {client_company} — quick question so we route you right: is this about a repair, a full roof, or an inspection? One word is plenty. Reply STOP to opt out.

**7 · value-add (retail/storm)**
> This is {client_company}. Whatever you were calling about, the first step is free: a photo inspection so you know exactly what you're dealing with. Want it this week? Reply STOP to opt out.

**8 · last-call (retail/storm)** — day 4, closes the loop
> Hi, {client_company} one last time — we don't like leaving a call unanswered. If you still need a roofer, reply YES. If you're all set, no reply needed and we'll close this out. Reply STOP to opt out.

### EMAIL

Email is the **secondary** channel for this pool — used only when a form
submission supplied an email address (the speed-to-lead path in
`speed_to_lead.md`). A homeowner who only ever called has no email on file,
and the SMS layer above carries that case alone.

**1 · check-in (retail/storm)**
> **Subject:** We got your request — {client_company}
>
> {first_name},
>
> Thanks for reaching out. We have your request and someone from our crew is
> calling you shortly.
>
> If it's easier, reply to this email with your address and a photo of what
> you're seeing, and we'll tell you what it takes and when we can be out.
>
> {owner_first}
> {client_company}

**3 · season/weather (storm)**
> **Subject:** Storm work in {city} this week
>
> {first_name},
>
> If your message was about storm damage, we're prioritizing {city} homes this
> week and can document everything you'd need for your carrier.
>
> Reply with your address and we'll get someone out to look.
>
> {owner_first}
> {client_company}

**6 · question (retail/storm)**
> **Subject:** One quick question
>
> {first_name},
>
> So we send the right person: is this a repair, a full roof, or an
> inspection?
>
> One word is plenty, and we'll take it from there.
>
> {owner_first}
> {client_company}

**7 · value-add (retail/storm)**
> **Subject:** The first step is free
>
> {first_name},
>
> Whatever you reached out about, the first step costs nothing: a photo
> inspection so you know exactly what you're dealing with before you decide
> anything.
>
> Want it this week? Reply and we'll set it up.
>
> {owner_first}
> {client_company}

**8 · last-call (retail/storm)**
> **Subject:** Still want us to take a look?
>
> {first_name},
>
> Checking in one more time. If the timing isn't right, no trouble at all —
> just reply and tell us when to check back.
>
> If you'd rather talk it through, call us any time.
>
> {owner_first}
> {client_company}

---

## Angle rotation per pool

Never repeat an angle on consecutive touches. Never open on expiration or
last-call. Channels alternate per the workflow docs.

| Pool | Touch 1 | Touch 2 | Touch 3 | Touch 4 |
|---|---|---|---|---|
| Unanswered calls (3 touches, SMS only) | check-in | question | value-add | — |
| Open estimates — retail | check-in (SMS d1) | price-move (email d3) | question (SMS d6) | last-call (email d10) |
| Open estimates — storm | check-in (SMS d1) | expiration (email d3) | value-add (SMS d6) | last-call (email d10) |
| Past customers — retail | check-in (SMS d1) | value-add (email d4) | neighbor proof (SMS d8) | last-call (email d14) |
| Past customers — storm | check-in (SMS d1) | neighbor proof (email d4) | expiration (SMS d8) | last-call (email d14) |

The remaining angles are the substitution bench. When a client rejects a
variant during A4 approval, swap in an unused angle at the same touch position
rather than rewriting the rejected one — the rejection is usually about the
angle, not the wording.

---

## Approval gate (B6)

1. Load every message above into A4 MESSAGE_TEMPLATES as `draft`.
2. Localize merge fields and voice to the client, then set `pending`.
3. Client approves per template → `approved`, with `Approved Date` and
   `Approver` recorded.
4. **A workflow may only send from an `approved` row.** A send with no approved
   row is an incident, not a shortcut. This gate covers **both channels** — an
   approved SMS row does not authorize the email variant of the same angle.

**Minimum to go live:** the first two angles per pool per origin, in both
channels. The rest can be approved during the window as the rotation reaches
them.

---

### Compliance furniture (applies to every template above)

**Both channels**
- Identity: always from the client's own business identity, never an agency name
- Approval: template must be Approval Status = approved in A4 before any send (B6 hard gate)
- Quiet hours: sends 8am–8pm recipient local; queued otherwise
- Language: outcome language only — banned in anything a homeowner sees:
  recovery, leak, lost, missed, broken, fix, problem, leads, AI, automation,
  CRM, sequences, funnels

**SMS**
- Opt-out: every SMS ends "Reply STOP to opt out"; STOP suppresses immediately (A6 exception, 1h SLA, client notified same day)
- Origination: always from the client's number, always names {client_company}
- Length: under 320 characters including the opt-out line

**Email**
- Unsubscribe line on every send, one click, honored immediately
- Sends from the client's identity and domain; reply-to is an address the client actually reads
- Client's physical business address in the footer, as commercial email requires
- Subject lines under 50 characters, obey the same banned-word list, no all-caps, no exclamation marks
- Plain text first — no template chrome, no banner image, no multi-column layout
- An email unsubscribe suppresses **email only**; a texted STOP suppresses **both channels**

---

## Gotchas

- **The client's voice beats our copy every time.** These are the starting
  point. When a client rewrites one in their own words, that version wins —
  put it in A4 and use it.
- **A blank merge field kills the message**, and kills an email faster than an
  SMS because there is more surrounding text to make it obvious. Validate that
  every merge field has data for every contact in the batch before release;
  drop contacts with missing critical fields to a simpler angle.
- **Storm copy never asserts damage before an inspection**, never states a
  carrier deadline the client has not verified, and never implies the
  homeowner will not owe a deductible.
- **Never send the SMS and email variant of the same angle on the same day.**
  The workflows alternate channels across days for exactly this reason.
- **Sending the same angle to the same contact twice reads as a mistake**, and
  homeowners forgive it exactly once.
