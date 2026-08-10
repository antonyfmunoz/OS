# B5 — ACTIVATION AGENT

**name:** activation
**trigger:** payment confirmed — Stripe webhook received, or A1 PROSPECTS `Stage = "Closed Won"`
**inputs:** prospect record ref · signed agreement terms (tier, MRR, declared service area, pools enabled, ROFO) · CRM access credentials · GHL Pod snapshot id
**tools:** `pod/` snapshot clone · tracking-number provisioning · `runtime/notion_client.py` · `runtime/notion_schema.py` (CLIENT_FIELDS, CLIENT_TIERS, CLIENT_STAGES)
**outputs:**
- A2 CLIENTS row created from the prospect: `Company`, `Prospect` (relation), `Declared Service Area`, `Tier`, `MRR`, `Start Date`, `Guarantee Status`, `Pools Enabled`, `Stage → "Onboarding"`, `ROFO`
- Cloned GHL Pod instance + provisioned tracking numbers, each step timestamped to the journal
- A3 LEDGER initialized for the client from the CRM export (one row per contact ref, `Client`, `Pool`, `Origin`, empty touch history)
- Kickoff doc + "What Happens Next" artifact rendered via C0 signed links
- Template library pushed to the approval portal (C0 link) as A4 rows, `Approval Status = "draft"`

**guardrails:**
- **Nothing goes client-facing until its A4 template carries `Approval Status = "approved"`.** The library is pushed for review; it is not armed. B6 enforces the gate at send time; this agent must not pre-approve its own output.
- Every provisioning step writes a timestamp — access granted, pod cloned, numbers live, ledger seeded, library pushed. These timestamps ARE the A9 "Access to live" measurement; an unstamped step is an unmeasured step.
- Target ≤ 24h access → live, **zero meetings**. If a step needs a human conversation, that is an exception to log, not a call to schedule.
- `Guarantee Status` is copied from the B3 eligibility verdict — never recomputed here, never upgraded.

**escalation:**
- ≥ 24h elapsed and not live → A6 EXCEPTION type "technical question", Owner=Delivery, 2h SLA, with the timestamp trail showing which step stalled
- CRM access fails or export is thin → A6 EXCEPTION, Owner=Delivery; do NOT seed a partial ledger and call the client live
- Tracking-number provisioning fails → A6 EXCEPTION type "send failure / deliverability", Owner=Delivery, immediate — no client sends from an unprovisioned number

**verification:** A2 row validates against `CLIENT_FIELDS` with `Tier ∈ CLIENT_TIERS` and `Stage ∈ CLIENT_STAGES`; A3 ledger row count matches the CRM export contact count; every A4 template row reads `draft` (zero pre-approved); journal contains a timestamp for all five provisioning steps.

**Gotchas:**
- "Closed Won" without a confirmed payment is not activation — the Stripe event is the trigger, the stage is the mirror
- Pod snapshot clone carries the previous client's numbers if not re-provisioned; re-provision before the ledger seed, never after
- `Pools Enabled` is a multi-select from `POOLS` — a pool absent here must produce zero sends even if the ledger has rows for it
- The kickoff artifact is client-facing copy: banned-word rules apply to it exactly as they do to outreach
