# C4 — THE POD

**Status:** SPECD (docs-first). TEST MODE ONLY — nothing in this directory is
connected to a live GoHighLevel sub-account.

---

## What the Pod is

The Pod is **the delivery unit**. One Pod = one client. It is the GHL
sub-account snapshot that gets cloned the moment a client signs, containing
every pipeline, calendar, workflow, and message template needed to run The Job
Pipeline System for that client without building anything new.

The Pod exists so that delivery is **configuration, not construction**. When
client #2 signs, nobody designs a follow-up sequence — the Pod is cloned, the
declared service area and business hours are set, the client's message
templates are approved (A4), and the system runs.

The unit of sale is The Job Pipeline System: **$5,000 start (activation +
month one) + $2,500/mo**, 3-month initial term. The Pod is what that buys.

### What the Pod contains

| Component | File | Count |
|---|---|---|
| Pipelines | `pipelines.md` | 2 (SALES, DELIVERY) |
| Calendars | `calendar.md` | 5 types |
| Workflows | `workflows/*.md` | 4 |
| Message library | `template_library/messages.md` | 8 angles × 3 pools × 2 origins × 2 channels |

### What the Pod is NOT

- It is **not** the runtime. The Notion runtime (`runtime/notion_schema.py`)
  is the source of truth for prospect/client/ledger state. The Pod is the
  execution surface that touches the homeowner.
- It is **not** per-client custom work. Anything that differs per client is a
  **setting** (service area, business hours, phone number, voice), never a
  new workflow.
- It is **not** where math lives. Every number shown to anyone comes from
  `engine/pipeline_math.py` (C1). The Pod never computes.

---

## TEST MODE

**No GHL credential exists on this VPS. This has been verified.** Every
artifact here is a written configuration blueprint — the exact clicks,
triggers, delays, and copy — that a human or an authenticated agent applies
to a real sub-account later.

Consequences of TEST MODE, all deliberate:

1. Nothing in this directory sends a message to a real phone or inbox.
2. Message copy is final and approved-shaped, so that upgrade is
   transcription, not authorship.
3. The rails rehearsal (`fixtures/RAILS_CHECKLIST.md`) is how the send paths
   get proven — by AFM manually, with screenshot evidence, before a client's
   name is ever attached to a send.

---

## Upgrade path — when the GHL token lands

The token is expected at **1Password vault `UMH-Production`, item `GHL`,
field `token`**. It does not exist yet. When it does:

```bash
# 1. Verify the item exists (this currently returns nothing)
op item get GHL --vault UMH-Production --fields token

# 2. Export for the session — never hardcode, never commit
export GHL_TOKEN="$(op item get GHL --vault UMH-Production --fields token)"
```

Then, in order:

1. **Create the Pod sub-account** as a snapshot template, not a client
   account. Name it `POD — Job Pipeline System v1`.
2. **Build the two pipelines** exactly as `pipelines.md` specifies —
   stage names verbatim, because the Notion runtime's `PROSPECT_STAGES` and
   `CLIENT_STAGES` tuples mirror them and agents match on those strings.
3. **Create the five calendar types** per `calendar.md`.
4. **Build the four workflows** per `workflows/`. Each workflow doc is
   written as trigger → conditions → actions → exit, in the order GHL's
   builder asks for them.
5. **Load the message library** into A4 MESSAGE_TEMPLATES first (Notion), get
   the client's approval on their variants, and only then paste approved
   bodies into GHL. **Nothing sends without an approved A4 row.**
6. **Save as snapshot.** Clone per client from that point forward.

### Stage-name coupling (do not drift)

`runtime/notion_schema.py` defines the canonical stage strings. GHL stage
names must match them character for character:

- `PROSPECT_STAGES` → the SALES pipeline
- `CLIENT_STAGES` → the DELIVERY pipeline

If a GHL stage is renamed without updating the schema module, agents silently
stop matching and the ledger stops advancing. Rename in the schema first.

---

## Gotchas

- **The client's number, not ours.** Every outbound SMS in the Pod sends from
  the client's own business number. A homeowner who calls back must reach the
  client's phone. A Pod that texts from an agency number is misconfigured.
- **Business hours are a client setting, and they are load-bearing.** The
  missed-call textback is the one exception that fires 24/7; everything else
  respects quiet hours. Getting this backwards produces a 2 a.m. text and a
  complaint.
- **Opt-out is not optional.** Every SMS template ends with
  `Reply STOP to opt out.` A homeowner who replies STOP is suppressed
  account-wide, across all four workflows, permanently.
- **Two-way response is the guarantee unit.** An "activated qualified
  opportunity" requires a real two-way response evidenced in A3 LEDGER. A
  delivered message is not an opportunity. The Pod's job is to produce
  responses, and the ledger's job is to prove them.
- **Banned words apply to everything a homeowner or client sees.** Internal
  filenames may name mechanics; message copy may not. See
  `template_library/messages.md`.
