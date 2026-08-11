# B6 — SEQUENCE AGENT

**name:** sequence
**trigger:** active client with `Stage = "Active"` and at least one A4 template at `Approval Status = "approved"`; runs per send window
**inputs:** A2 client record (`Pools Enabled`, `Declared Service Area`) · A3 LEDGER rows · A4 MESSAGE TEMPLATES filtered to approved · recipient local timezone
**tools:** `runtime/notion_client.py` (`assert_approved`, `execute_outbound`) · `pod/template_library` · `runtime/notion_schema.py` (POOLS, ORIGINS, CHANNELS, TEMPLATE_STATUSES)
**outputs:**
- A3 LEDGER row updated per send: `Touch History` appended (template name, channel, timestamp), `Response`, `Qualified`, `Appointment`, `Booked Job`, `Job Value`, `Evidence Link`
- Journal entry per send with the template ref and the approval ref that authorized it
- A6 EXCEPTION rows on stop requests and send failures

**template selection:** by `Pool` AND `Origin` together — a storm-origin past-customer contact gets the storm/past-customer template, never the retail one. No template matching both dimensions means no send, not a fallback.

**guardrails:**
- **Executes ONLY templates at `Approval Status = "approved"`.** An unapproved or draft template is a hard refusal via `assert_approved()` — the agent raises `ApprovalRequired` and stops. Never "send the approved version of a similar template."
- Opt-out language on every single message, every channel, no exceptions for follow-ups.
- Quiet hours enforced 8am–8pm **recipient local time**, computed from the contact, not from the client's office or the server clock.
- Sends from the CLIENT's provisioned number, under the client's own existing customer relationship. Never from an Empyrean number, never to a contact with no prior relationship to the client.
- **Suppress on STOP immediately** — first matching reply halts all future sends to that contact ref across all pools, before anything else is written.

**escalation:**
- STOP / angry reply → suppress, then A6 EXCEPTION type "angry reply / stop request", Owner=Delivery, 1h SLA
- Send failure or deliverability signal → A6 EXCEPTION type "send failure / deliverability", Owner=Delivery, immediate (0h SLA); pause the pool, don't drain it into a dead number
- Recipient asks something outside the client's service scope → A6 EXCEPTION type "out of scope request", Owner=Account, 24h SLA

**verification:** every journaled send carries an approval ref resolving to an approved A4 row; zero sends land outside 8am–8pm recipient local; a seeded STOP fixture produces suppression before any subsequent send and an A6 row with a 1h `SLA Due`; touch history is append-only (no overwritten history in the ledger).

**Gotchas:**
- Quiet hours are recipient-local — a Portland client texting an out-of-state past customer must respect the recipient's clock
- Suppression is per contact ref, not per pool row: the same person can appear in past-customer AND open-estimate pools
- An approved template that is later edited returns to `draft` — re-check status at send time, never cache the approval from the run start
- `Qualified` is set from the reply content, not from the fact of a reply; `Response = true, Qualified = false` is a normal and common outcome
