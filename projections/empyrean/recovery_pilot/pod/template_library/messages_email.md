# MESSAGE LIBRARY — EMAIL VARIANTS (artifact 4.1, email layer)

Companion to `messages.md`, which holds the SMS layer. This file holds the
**email** variant for each angle × pool × origin.

**Why this file exists separately:** two workflows specify email touches that
SMS copy cannot serve — `estimate_followup.md` (day 3 and day 10 are email)
and `past_customer_reactivation.md` (day 4 and day 14 are email). The A4
MESSAGE_TEMPLATES schema in `runtime/notion_schema.py` carries a `Channel`
field with both `sms` and `email`, so each channel needs its own approved row.

**Pending a merge decision** — these may be folded into `messages.md` as a
single library. Until then, treat both files together as artifact 4.1.

TEST MODE: written and final in shape. Not loaded into a live sub-account.

---

## Rules (identical to the SMS layer)

- Client's voice, from the client's own business identity. Never an agency name.
- Outcome language only. Banned in anything a homeowner sees: `recovery`,
  `leak`, `lost`, `missed`, `broken`, `fix`, `problem`, `leads`, `AI`,
  `automation`, `CRM`, `sequences`, `funnels`.
- Email carries no `Reply STOP to opt out.` line (that is the SMS
  requirement); it carries a standard unsubscribe footer instead, plus the
  client's real business address as required for commercial email.
- Subject lines under 50 characters. No all-caps, no exclamation marks.
- Every email must survive the "would a homeowner believe their roofer's
  office typed this" test.

**A4 mapping:** `Pool` · `Origin` · `Angle` · `Channel = email` ·
`Approval Status`. Template naming: `{pool}-{origin}-{angle}-email`.

**Merge fields** match the SMS layer: `{first_name}` `{client_company}`
`{owner_first}` `{estimate_month}` `{estimate_amount}` `{year_roofed}`
`{city}`.

---

# POOL: OPEN ESTIMATES

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

# POOL: PAST CUSTOMERS

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

# POOL: UNANSWERED CALLS

Email is the **secondary** channel for this pool — used only when a form
submission supplied an email address (the speed-to-lead path). A homeowner who
only ever called has no email on file, and the SMS layer carries that pool
alone.

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

## Email compliance furniture

Applies to every template above:

- **Unsubscribe footer** on every send, one click, honored immediately and
  account-wide. An email unsubscribe suppresses the contact for **email only**
  unless the homeowner also texts STOP; a texted STOP suppresses **both**.
- **Physical mailing address** of the client's business in the footer, as
  commercial email requires.
- **From name** is the client's business; **reply-to** is an address the
  client actually reads. A reply that lands nowhere is worse than no email.
- **Quiet hours** 8am-8pm recipient local; queued outside that window.
- **No tracking pixel language** in the visible body.
- **Plain text first.** These read as though the client's office typed them,
  which is the entire point. No template chrome, no banner image, no
  multi-column layout.

## Gotchas

- **A blank merge field kills an email faster than an SMS**, because there is
  more surrounding text to make it obvious. Validate `{year_roofed}` and
  `{estimate_month}` have data for every contact in the batch before release.
- **Subject lines are the whole game on the email touches.** The body only
  matters if the subject earns the open. Keep them short, specific, and
  free of anything that reads like a promotion.
- **Never send the email and SMS variant of the same angle on the same day.**
  The workflows alternate channels across days for exactly this reason.
