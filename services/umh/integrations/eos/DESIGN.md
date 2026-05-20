# EOS Integration — Design Report

Phase 0 = design. No code yet.

EOS (EntrepreneurOS) is the SaaS product built on UMH. Codebase at `/opt/OS/saas/`. Stack: Hono (Express-like), Drizzle ORM, Neon Postgres, Clerk auth (future), Zod validation.

UMH is the substrate. EOS is the first application projection. This integration connects them bidirectionally through the same socket pattern (Signal/Capability/Outcome/View) used by Notion — but both sides are under our control.

---

## 1. Process Model + Auth

### Architecture Decision: Shared-Process via Direct Postgres

EOS (Hono/TS) and UMH (FastAPI/Python) are separate processes, separate languages — but they share the same Neon Postgres database. This is the load-bearing fact that determines the integration architecture.

| Dimension | Direct Postgres (Recommended) | EOS REST API | In-Process |
|---|---|---|---|
| **Data access** | Python reads/writes EOS tables directly via psycopg2. Same DB, same connection string (`DATABASE_URL`). | UMH calls EOS's Hono API over HTTP. Adds network hop, serialization, error surface. | Impossible — TS and Python can't share a process. |
| **Auth complexity** | Postgres role auth. UMH connects as `neondb_owner` (existing) or a dedicated `umh_app` role. No HTTP auth needed. | Needs auth mechanism: API key, Clerk JWT, or internal token. EOS currently uses `x-org-id` header — no real auth, just org scoping. | N/A |
| **RLS alignment** | UMH can set `app.current_org_id` in a transaction, same as EOS's `withOrg()`. RLS policies apply identically. | RLS is EOS's concern — UMH gets pre-filtered data from API responses. UMH can't verify RLS enforcement. | N/A |
| **Latency** | Sub-millisecond for local reads. Neon Postgres is the only network hop, same as EOS itself. | Two network hops: UMH → EOS → Postgres. Plus Hono request overhead (~2-5ms). | N/A |
| **Operational coupling** | UMH works even if EOS process is down (Postgres is the source of truth, not Hono). | UMH blocked if EOS process is down. EOS becomes a hard dependency for UMH pipeline. | N/A |
| **Schema coupling** | UMH must know EOS table shapes. Schema changes require coordinated updates. Mitigated: Drizzle migrations are versioned, UMH queries are read-heavy and column-specific. | EOS API is the contract surface. Schema changes are EOS's problem. Cleaner boundary. | N/A |
| **Existing pattern** | `agent_bridge.py` already connects to Neon from Python. `runtime/db.py` uses the same connection string. UMH already reads Neon tables. | EOS REST API exists but is designed for cockpit UI, not machine-to-machine. Would need new routes for UMH-specific operations. | N/A |

### Recommendation: Direct Postgres

Direct Postgres wins because:

1. **UMH already connects to Neon.** `runtime/db.py` has the connection pool. No new auth surface.
2. **Both systems share the same database.** EOS tables are 10 feet away in the same Postgres cluster. Adding an HTTP round-trip to reach them is artificial complexity.
3. **RLS works identically.** UMH sets `app.current_org_id` in a transaction and gets the same row-level filtering as EOS.
4. **EOS process independence.** UMH can read EOS data even when the Hono server is stopped. This matters for background processing (polling, morning briefs, agent tasks).
5. **The bridge pattern is established.** `saas/bridge/agent_bridge.py` already crosses the Python-TS boundary via Postgres, not HTTP.

### Auth Mechanism

No new auth mechanism needed. Both systems authenticate to Postgres with the same connection string. For org-scoped queries, UMH sets `app.current_org_id` via `SET LOCAL` (same as EOS's `withOrg()`). The RLS policies are the enforcement layer — same policies, same database, same trust.

The deferred-auth decision from the socket design is resolved: **auth is Postgres role-based, not HTTP-based.** When EOS moves to multi-tenant SaaS with Clerk, the auth boundary is at the Hono layer (user → EOS). UMH sits behind EOS, inside the trust boundary, accessing data as a system-level consumer — not as an end user.

### Hybrid Escape Hatch

For operations that EOS should own (e.g., sending user-facing notifications, triggering Clerk webhooks), UMH can call EOS's REST API. This is the exception path, not the default. When used, UMH passes an internal API key (`EOS_INTERNAL_API_KEY` env var) rather than a user JWT. This key is shared-secret between co-located processes — acceptable for single-VPS deployment, replaced by mTLS or Tailscale ACLs when scaling.

---

## 2. Data Model

### How UMH Accesses EOS Data

UMH reads and writes EOS tables via psycopg2 using `runtime/db.py`'s existing connection pool. The EOS schema (defined in `saas/db/schema.ts`) defines the table shapes. UMH queries specific columns, not `SELECT *`, to minimize coupling to schema evolution.

### EOS Tables Relevant to UMH

| Table | UMH Access | Purpose |
|---|---|---|
| `users` | READ | Resolve user identity for signals and outcomes |
| `organizations` | READ | Org context for multi-tenant scoping |
| `ventures` | READ/WRITE | Revenue tracking, stage transitions, config |
| `agents` | READ/WRITE | Agent lifecycle, activation, hierarchy |
| `interactions` | WRITE | Log UMH pipeline executions as EOS interactions |
| `outcomes` | WRITE | Log pipeline outcomes for skill performance tracking |
| `events` | WRITE | Publish domain events (signal-equivalent for EOS) |
| `approvals` | READ/WRITE | Create agent action proposals, read approval status |
| `clients` | READ/WRITE | CRM: lead capture, status transitions |
| `transactions` | READ/WRITE | Revenue: payment status, fulfillment |
| `fulfillment_events` | WRITE | Delivery milestones for client fulfillment |
| `offers` | READ | Offer ladder context for triage decisions |
| `skills` | READ | Skill content for agent execution |
| `workflows` | READ | Workflow definitions for automated execution |

### Python Table Access Layer

UMH does NOT import Drizzle ORM (that's TypeScript). Instead, a thin Python module (`services/umh/integrations/eos/tables.py`) defines table names and column constants, plus typed query/insert helpers using psycopg2. This is the single file that changes when EOS schema evolves.

```python
# Pattern: typed query helpers, not ORM
def get_venture(org_id: str, venture_id: str) -> dict | None:
    with _org_scoped_connection(org_id) as conn:
        row = conn.execute(
            "SELECT id, name, stage, monthly_revenue, monthly_target "
            "FROM ventures WHERE id = %s AND org_id = %s",
            (venture_id, org_id),
        ).fetchone()
        return dict(row) if row else None
```

### LISTEN/NOTIFY (Future — Not Phase 1)

Postgres LISTEN/NOTIFY could replace polling for EOS signals. A trigger on `INSERT INTO events` fires a NOTIFY, and UMH's listener thread receives it in real-time. This eliminates poll latency for critical signals (e.g., approval decisions). Deferred because:
1. Requires Neon Postgres support for persistent LISTEN connections (connection pooling complicates this)
2. Polling is sufficient for Phase 1 latency requirements
3. Can be added as an optimization without changing the socket contract

---

## 3. Signal Flow (EOS → UMH)

### Signal Catalog

EOS events that become UMH signals. These are the domain events that UMH needs to observe to provide intelligent automation.

| EOS Event | UMH `content_type` | Default Urgency | Default Risk Class | Source |
|---|---|---|---|---|
| New user registered | `user_signup` | NORMAL | READ_ONLY | `users` INSERT |
| Organization created | `org_created` | NORMAL | READ_ONLY | `organizations` INSERT |
| Venture created | `venture_created` | NORMAL | READ_ONLY | `ventures` INSERT |
| Venture stage changed | `venture_stage_changed` | NORMAL | READ_ONLY | `ventures` UPDATE (stage) |
| Revenue recorded | `revenue_recorded` | HIGH | READ_ONLY | `transactions` INSERT (status=paid) |
| Client status changed | `client_status_changed` | NORMAL | READ_ONLY | `clients` UPDATE (status) |
| Agent action proposal submitted | `proposal_submitted` | HIGH | READ_ONLY | `approvals` INSERT |
| Approval resolved | `approval_resolved` | HIGH | READ_ONLY | `approvals` UPDATE (status) |
| Interaction completed | `interaction_completed` | LOW | READ_ONLY | `interactions` INSERT |
| Event published | `event_published` | NORMAL | READ_ONLY | `events` INSERT |
| Offer created/updated | `offer_changed` | LOW | READ_ONLY | `offers` INSERT/UPDATE |
| Fulfillment milestone | `fulfillment_milestone` | NORMAL | READ_ONLY | `fulfillment_events` INSERT |

### Emission Mechanism

**Phase 1: Polling** (same pattern as Notion Phase 3)

An `EOSPoller` thread queries EOS tables on an interval, using watermarks to detect new/changed rows. The `events` table is the primary signal source — EOS already publishes domain events there. Secondary sources: `approvals` (status changes), `transactions` (payments), `clients` (status changes).

Watermarks:
- `events` table: watermark on `created_at` (append-only, no updates)
- `approvals` table: watermark on `resolved_at` for approval decisions
- `clients` table: watermark on `updated_at` for status transitions
- `transactions` table: watermark on `created_at` for new payments

**Phase 2+: LISTEN/NOTIFY** (optional upgrade, no API change)

EOS inserts a trigger: `AFTER INSERT ON events PERFORM pg_notify('eos_events', NEW.id)`. UMH replaces the polling loop with a LISTEN connection. SignalEnvelope shape is identical.

### SignalEnvelope Schema

```python
SignalEnvelope(
    integration_id="eos",
    content_type="proposal_submitted",
    payload={
        "event_id": "uuid",           # events.id or source row ID
        "org_id": "uuid",             # tenant scope
        "event_type": "approval.created",
        "entity_type": "approval",     # table/domain object
        "entity_id": "uuid",          # row ID
        "entity_data": { ... },       # relevant columns (not full row)
        "actor_id": "uuid",           # user who triggered the event
    },
    raw_content="Agent proposal: [summary from request_json]",
    source_identifier="eos:approval:uuid",
    correlation_id=None,               # set if this is a response to a prior UMH action
    urgency=SignalUrgency.HIGH,
    metadata={
        "eos_table": "approvals",
        "poll_cycle_id": "cycle-nnn",
    },
)
```

---

## 4. Capability Flow (UMH → EOS)

### Operations EOS Exposes to UMH

These are the write operations UMH can perform on EOS data. Each maps to a CapabilityDescriptor in the manifest and a handler method.

| Capability | Category | Risk Class | Input | Output | Notes |
|---|---|---|---|---|---|
| `create_event` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, event_type, payload_json}` | `{event_id}` | Publish a domain event into EOS's event stream |
| `create_client` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, venture_id, name, email, source}` | `{client_id}` | Lead capture |
| `update_client_status` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, client_id, status, notes}` | `{client_id, updated}` | Status transition (lead→prospect→client) |
| `create_approval` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, request_json}` | `{approval_id, status}` | Agent action proposal |
| `resolve_approval` | COMMUNICATE | GOVERNANCE_REQUIRED | `{org_id, approval_id, status, resolved_by}` | `{approval_id, status}` | Approve/reject (requires governance) |
| `create_interaction` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, task_type, model_used, input_summary, output_summary, tokens_json}` | `{interaction_id}` | Log AI execution |
| `create_outcome` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, interaction_id, outcome_type, score, notes}` | `{outcome_id}` | Log execution outcome |
| `update_venture` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, venture_id, monthly_revenue?, stage?}` | `{venture_id, updated}` | Revenue/stage update |
| `create_transaction` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, venture_id, client_id, product_name, amount_cents}` | `{transaction_id}` | Record sale |
| `create_fulfillment_event` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{org_id, transaction_id, description, completed_by}` | `{fulfillment_event_id}` | Delivery milestone |
| `query_clients` | RETRIEVE | READ_ONLY | `{org_id, venture_id?, status?, limit?}` | `{clients: list, count}` | CRM query |
| `query_ventures` | RETRIEVE | READ_ONLY | `{org_id}` | `{ventures: list}` | Venture list with revenue |
| `query_approvals_pending` | RETRIEVE | READ_ONLY | `{org_id}` | `{approvals: list, count}` | Pending proposals |
| `query_interactions` | RETRIEVE | READ_ONLY | `{org_id, limit?, agent_id?}` | `{interactions: list, count}` | Recent AI executions |

### Handler Implementation Pattern

```python
class EOSCapabilityHandler:
    """Implements CapabilityHandler Protocol via direct Postgres access."""

    @property
    def integration_id(self) -> str:
        return "eos"

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        handler = self._handlers.get(request.capability_name)
        if not handler:
            return CapabilityResponse(request_id=request.request_id, success=False,
                                      error=f"unknown capability: {request.capability_name}")
        return handler(request)

    def _create_client(self, request: CapabilityRequest) -> CapabilityResponse:
        params = request.params
        org_id = params["org_id"]
        with org_scoped_connection(org_id) as conn:
            row = conn.execute(
                "INSERT INTO clients (org_id, venture_id, name, email, source, status) "
                "VALUES (%s, %s, %s, %s, %s, 'lead') RETURNING id",
                (org_id, params["venture_id"], params["name"],
                 params["email"], params.get("source", "umh")),
            ).fetchone()
        return CapabilityResponse(
            request_id=request.request_id, success=True,
            result_data={"client_id": str(row["id"])},
        )
```

### Health Check

`EOSCapabilityHandler.health()` runs `SELECT 1` against Neon Postgres (same as existing `runtime/db.py` health path). Returns healthy/degraded/unavailable based on connection state.

---

## 5. Outcome Flow (UMH → EOS)

### `EOSOutcomeReceiver.on_outcome(envelope)`

UMH pipeline outcomes map to EOS-side effects. Unlike Notion (which gets a status property + callout block), EOS outcomes are persisted as structured data in EOS tables.

### Outcome → EOS Mapping

| `outcome_type` | EOS Side Effect | Target Table |
|---|---|---|
| `success` | Insert outcome row (positive) + update event `handled_by` | `outcomes` + `events` |
| `failure` | Insert outcome row (negative) + insert error event | `outcomes` + `events` |
| `governance_denied` | Update approval status to "rejected" if correlation exists | `approvals` |
| `timeout` | Insert outcome row (negative) + insert timeout event | `outcomes` + `events` |

### Audit Trail

Every UMH outcome that touches EOS data also inserts an `events` row with `event_type="umh.outcome"` and `payload_json` containing the full `OutcomeEnvelope` summary. This creates a queryable audit trail visible in the EOS cockpit's event stream.

### Correlation Handling

When UMH creates an EOS entity (e.g., `create_client` returns `client_id`), the correlation map stores `correlation_id → {entity_type, entity_id, org_id}`. When the outcome arrives, the receiver uses the correlation to update the specific entity (e.g., mark the client's first interaction as successful).

---

## 6. View Flow (UMH → EOS)

### Decision: Not Needed for Phase 1

EOS has its own React cockpit UI with its own data fetching (Hono API → Drizzle → Postgres). ViewFrames are designed for real-time pipeline observability — the cockpit-in-cockpit pattern.

### Why Skip

1. **EOS already has its own event stream.** The `events` table + `/events` API route serves the same purpose as ViewFrames for the EOS context.
2. **ViewFrames are UMH-internal.** They track pipeline stages (signal → governance → execution → outcome). EOS cares about domain events (client created, revenue recorded), not pipeline internals.
3. **The WebSocket is available.** If EOS ever wants real-time pipeline frames, it subscribes to UMH's `/ws` endpoint and filters by `integration_id="eos"`. No new code on the UMH side.

### Future: Cockpit-in-Cockpit

If EOS wants to embed a live UMH trace view (show the user what UMH is doing in real-time), EOS's React frontend connects to `ws://localhost:8093/ws` and renders `ViewFrame` objects as a trace stream. This is a frontend concern — no EOS integration code needed, just a React component that consumes the existing WebSocket.

---

## 7. EOS-Side Code Structure

### Important Realization: No Separate `/opt/EOS` Repo

EOS lives at `/opt/OS/saas/`. It's a subdirectory of the UMH monorepo, not a separate repo. This simplifies the "two-repo integration" to a "two-directory integration" within the same git repo.

### EOS-Side Changes (Minimal for Phase 1)

Because UMH accesses EOS data via direct Postgres (not EOS API), the EOS-side changes are minimal:

```
saas/
├── (existing files unchanged)
└── umh/                              # NEW directory
    ├── types.ts                      # Shared types for UMH ↔ EOS contract
    └── README.md                     # Integration documentation
```

The heavy lifting is on the UMH side (Python). EOS-side only needs:
- **Type definitions** for the UMH ↔ EOS data contract (what columns UMH reads/writes)
- **README** documenting which tables UMH accesses and the migration coordination protocol

### Why Not More EOS-Side Code

In the Notion integration, the "EOS-side" would be Notion's API — something we don't control. But here, we control both sides. And since UMH accesses EOS data via Postgres, not via EOS's Hono API, there's no EOS-side "client" or "signal emitter" to write. The database IS the integration boundary.

If we later add EOS REST API calls (for operations EOS must own), we'd add:
```
saas/
└── umh/
    ├── routes.ts                     # UMH-specific API routes (internal endpoints)
    └── middleware.ts                  # Internal API key validation
```

---

## 8. UMH-Side Code Structure

```
services/umh/integrations/eos/
├── __init__.py                       # Module docstring
├── DESIGN.md                         # This file
├── manifest.py                       # Signal + Capability descriptors, INTEGRATION_ID
├── tables.py                         # EOS table names, column constants, query helpers
├── handlers.py                       # EOSCapabilityHandler (direct Postgres)
├── signals.py                        # EOSSignalEmitter (declare signal types)
├── outcomes.py                       # EOSOutcomeReceiver (write outcomes to EOS tables)
├── poller.py                         # EOSPoller (poll events/approvals/transactions tables)
├── watermarks.py                     # WatermarkStore (reuse Notion pattern, separate file)
└── auth.py                           # Org-scoped Postgres connection helper
```

### Pattern Alignment with Notion

| Notion | EOS | Difference |
|---|---|---|
| `notion_client.Client` (HTTP SDK) | `psycopg2` connection pool | Transport layer only |
| `auth.py` loads `NOTION_API_KEY` | `auth.py` loads `DATABASE_URL`, provides `org_scoped_connection()` | Postgres auth vs API key |
| `transforms.py` (Notion JSON ↔ UMH) | `tables.py` (SQL rows ↔ UMH dicts) | Shape translation |
| `handlers.py` calls SDK methods | `handlers.py` runs SQL queries | Same pattern, different backend |
| `poller.py` queries Notion API | `poller.py` queries Postgres tables | Same watermark pattern |
| `watermarks.py` (JSONL append-log) | Same file, separate instance | Shared implementation possible |

### Key Design Choice: `tables.py`

This file is the **single coupling point** between UMH and the EOS schema. It contains:
1. Table name constants (`CLIENTS = "clients"`, `VENTURES = "ventures"`, etc.)
2. Column name constants for each table (only the columns UMH uses)
3. Typed query helpers (`get_venture()`, `list_clients()`, etc.)
4. Typed insert helpers (`insert_client()`, `insert_event()`, etc.)

When EOS runs a migration that renames a column, `tables.py` is the only file that changes on the UMH side. Handler and poller code reference the helpers, not raw SQL.

---

## 9. Bootstrapping

### Registration at UMH Startup

Same pattern as Notion. In `app.py`'s `_register_eos_integration()`:

```python
def _register_eos_integration() -> None:
    from ..integrations.eos.handlers import EOSCapabilityHandler
    from ..integrations.eos.manifest import load_signal_sources
    from ..integrations.eos.outcomes import EOSOutcomeReceiver
    from ..integrations.eos.poller import EOSPoller
    from ..integrations.eos.signals import EOSSignalEmitter

    emitter = EOSSignalEmitter()
    handler = EOSCapabilityHandler()
    outcome_receiver = EOSOutcomeReceiver()

    manifest = IntegrationManifest(
        integration_id="eos",
        signal_emitter=emitter,
        capability_handler=handler,
        outcome_receiver=outcome_receiver,
    )

    adapter = registry.register(manifest)
    if adapter:
        _executor.register_adapter(adapter)

    signal_sources = load_signal_sources()
    if signal_sources:
        _eos_poller = EOSPoller(
            correlation_map=_correlation_map,
            signal_emitter=emitter,
            pipeline_submit_fn=_pipeline.submit_signal,
            outcome_receiver=outcome_receiver,
            signal_sources=signal_sources,
        )
```

### No Cross-Process Registration

Because both systems share Postgres, there's no registration RPC. UMH imports its own `eos/` integration package at startup. EOS doesn't know UMH is reading its tables — the database is the shared interface. This is intentional: UMH is infrastructure, not an EOS dependency.

### Env Var Configuration

```
# services/.env
EOS_SIGNAL_SOURCES=events,approvals,transactions,clients
EOS_ORG_ID=<uuid>           # Single-org for Phase 1
EOS_POLL_INTERVAL=15         # Seconds (lower than Notion — same-DB queries are cheap)
```

---

## 10. Initiate Arena Flow (North-Star Validation Use Case)

The $10K/month net profit goal flows through EOS. UMH enables intelligent automation of the pipeline.

### Lead Capture → Triage → Enrollment → 90-Day Tracking

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LEAD CAPTURE                                                           │
│                                                                        │
│ Source: Instagram DM, Calendly booking, manual entry, referral         │
│                                                                        │
│ Signal: client_status_changed (status='lead')                          │
│ Capability: create_client (org_id, venture_id, name, email, source)    │
│ EOS table: clients INSERT                                              │
│                                                                        │
│ UMH auto-action: create triage event with lead context                 │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TRIAGE                                                                 │
│                                                                        │
│ Signal: event_published (event_type='lead.triage_needed')              │
│ UMH pipeline: assess lead → match to offer → score urgency            │
│ Capability: create_approval (request_json={recommendation, reasoning}) │
│ EOS table: approvals INSERT (status='pending')                         │
│                                                                        │
│ Cockpit: founder sees pending approval with AI recommendation          │
│ Signal: approval_resolved (approved/rejected)                          │
│                                                                        │
│ If approved → update_client_status to 'prospect'                       │
│ Capability: update_client_status (status='prospect')                   │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ENROLLMENT                                                             │
│                                                                        │
│ Signal: client_status_changed (status='prospect')                      │
│ UMH pipeline: match prospect to offer → generate enrollment plan       │
│ Capability: create_transaction (client_id, offer, amount_cents)        │
│ Capability: create_approval (enrollment plan for founder review)       │
│ EOS table: transactions INSERT                                         │
│                                                                        │
│ Cockpit: founder reviews enrollment, approves/rejects                  │
│ Signal: approval_resolved → update_client_status to 'client'           │
│                                                                        │
│ Outcome: UMH logs success/failure → events audit trail                 │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 90-DAY TRACKING                                                        │
│                                                                        │
│ Signal: fulfillment_milestone (periodic check-ins)                     │
│ UMH pipeline: assess progress → generate status report                 │
│ Capability: create_fulfillment_event (milestone description)           │
│ Capability: update_venture (monthly_revenue from transactions)         │
│                                                                        │
│ Signals the design must support:                                       │
│   - revenue_recorded (payment received)                                │
│   - client_status_changed (churn detection: client → churned)          │
│   - venture_stage_changed (idea → pre_revenue → early)                 │
│                                                                        │
│ Outcome writeback: update events table with progress summary           │
│ View: cockpit shows revenue trajectory vs monthly_target               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Required Signals for Initiate Arena

1. `client_status_changed` — every status transition in the pipeline
2. `proposal_submitted` — agent recommends an action, needs founder approval
3. `approval_resolved` — founder approved/rejected, triggers next step
4. `revenue_recorded` — payment landed, update revenue metrics
5. `fulfillment_milestone` — delivery progress checkpoint
6. `venture_stage_changed` — venture graduated (pre_revenue → early)
7. `event_published` — catch-all for domain events EOS publishes

### Required Capabilities for Initiate Arena

1. `create_client` — lead capture from any source
2. `update_client_status` — pipeline stage transitions
3. `create_approval` — agent action proposals
4. `create_transaction` — record sales
5. `create_fulfillment_event` — delivery milestones
6. `update_venture` — revenue and stage updates
7. `query_clients` — pipeline visibility
8. `query_approvals_pending` — founder decision queue

### Phase 1 Scope Boundary

Phase 1 implements the signal + capability + outcome framework. Intelligent routing (which signals trigger which capabilities) is Phase 2+. Phase 1 signals dispatch to `operation="noop"` — same pattern as Notion Phase 3 — to prove the full loop works before adding business logic.

---

## 11. Open Decisions

### 1. Postgres Role for UMH Access — **RESOLVED: A**

Uses `neondb_owner` via `EOS_DATABASE_URL`. Phase 1.

**Options:**
- **A. Use existing `neondb_owner` role (BYPASSRLS). Simple. UMH is a trusted system process.** ← CHOSEN
- B. Create a dedicated `umh_app` role with specific table grants. Least-privilege. Requires migration.
- C. Use existing `eos_app` role (same as EOS). RLS enforced. Requires `SET LOCAL app.current_org_id`.

**Trade-off:** A is fastest, B is most correct, C reuses existing infrastructure. Single-org Phase 1 makes A acceptable. Multi-tenant Phase 2 requires B or C.

### 2. Org Scoping Strategy — **RESOLVED: B (multi-org)**

Multi-org from day 1. `EOS_ORG_IDS` (comma-separated) whitelists orgs; empty/unset = all orgs discovered from the `organizations` table. Poller iterates `tables × org_ids` with per-(table, org) watermarks.

**Options:**
- A. Hardcode `EOS_ORG_ID` env var. Single-org. Phase 1 only.
- **B. UMH discovers all orgs and processes signals per-org. Multi-tenant from day 1.** ← CHOSEN
- C. EOS registers org IDs with UMH at startup via a manifest call.

**Trade-off:** A is honest about current reality (one founder, one org). B is premature — adds complexity with no user. Recommend A with clear migration path to B.

### 3. Watermark Storage Location — **RESOLVED: B**

Imports `WatermarkStore` from `services.umh.integrations.notion.watermarks`. Path: `services/umh/data/eos_watermarks.jsonl`. Composite key: `{table}:{org_id}`.

**Options:**
- A. Separate JSONL file per integration (`services/umh/data/eos_watermarks.jsonl`). Matches Notion pattern.
- **B. Shared `WatermarkStore` class from Notion, parameterized by path. Code reuse.** ← CHOSEN
- C. Watermarks in Postgres (`umh_watermarks` table). Survives disk loss. Adds schema.

**Trade-off:** B is cleanest — Notion's `WatermarkStore` is already generic. Just instantiate with a different path. C is better long-term but adds a migration for a simple key-value store.

### 4. Polling Granularity — **RESOLVED: A**

Single poller thread, all configured tables × all in-scope orgs, 15s interval (configurable via `EOS_POLL_INTERVAL`).

**Options:**
- **A. Single poller polls all EOS tables (`events`, `approvals`, `clients`, `transactions`). Simple.** ← CHOSEN
- B. Per-table pollers with independent intervals. `approvals` at 5s, `events` at 15s, `transactions` at 30s.
- C. Single poller with per-table intervals in a priority queue.

**Trade-off:** A is Phase 1. Same-DB queries are sub-millisecond, so polling 4 tables every 15s is negligible. B/C are optimizations for when latency matters (e.g., approval decisions need <5s response).

### 5. `tables.py` vs Direct SQL in Handlers — **RESOLVED: A**

`tables.py` with typed helpers. `EventRow` dataclass. `fetch_events_since()` accepts `org_id` + `since` watermark. `fetch_org_ids()` discovers all orgs.

**Options:**
- **A. `tables.py` with typed helpers (recommended above). Single coupling point. Clean separation.** ← CHOSEN
- B. Raw SQL directly in handlers. Fewer files. Direct visibility of queries.
- C. SQLAlchemy models. Full ORM. Heavier dependency.

**Trade-off:** A is the right balance. B scatters schema knowledge across handlers. C is overkill — we don't need an ORM when the queries are simple SELECTs and INSERTs.

### 6. EOS REST API Fallback — **RESOLVED: A**

Pure Postgres. No EOS REST API calls.

**Options:**
- **A. Pure Postgres. Never call EOS REST API. Maximum independence.** ← CHOSEN
- B. Postgres for reads, EOS REST API for writes. Lets EOS own validation logic.
- C. Postgres for everything except user-facing operations (notifications, emails).

**Trade-off:** A for Phase 1. EOS's Zod validation is replicated in Python-side input validation. If validation logic becomes complex, B is the escape hatch. C is the long-term pattern when EOS has side effects UMH can't replicate (e.g., sending Clerk-authenticated emails).

### 7. Event Deduplication — **RESOLVED: A**

Watermark-only on monotonic `created_at` column. Per-(table, org).

**Options:**
- **A. Watermark-only. Same as Notion. Simple. Assumes `created_at` is monotonically increasing.** ← CHOSEN
- B. Watermark + seen-set (event_id cache). Handles clock skew and out-of-order inserts.
- C. Postgres sequence number. Guarantees ordering. Requires schema addition.

**Trade-off:** A for Phase 1. EOS events use `defaultNow()` timestamps, and Postgres clock is authoritative. Out-of-order inserts are theoretically possible under concurrent writes but practically unlikely in single-org Phase 1.

### 8. Phase 1 Scope — **RESOLVED: C (IMPLEMENTED)**

`events` table polled across all in-scope orgs, noop dispatch. One table proves the full signal→pipeline→outcome loop. Capabilities are Phase 2.

**Options:**
- A. Full signal catalog + full capability catalog + outcome writeback. Comprehensive but large.
- B. `events` table polling + `create_event` + `create_client` capabilities only. Minimal viable.
- **C. Read-only: poll events, emit signals, noop operation. Prove the loop. Same as Notion Phase 3.** ← CHOSEN

**Trade-off:** C is safest. Prove EOS signals flow through UMH pipeline before adding write operations. Add capabilities in Phase 2. This matches the proven Notion cadence.

### 9. Target Database + Schema Migration Coordination — **RESOLVED: A + C + D**

Manual `tables.py` updates + `@pytest.mark.integration` test in `test_eos_integration.py` that validates expected columns exist against the real EOS schema. Run with `EOS_DATABASE_URL + EOS_INTEGRATION_TEST=1`.

**Target database for Phase 2:** ep-dark-poetry (us-east-1, OS Neon), where the current `/opt/OS/saas/db/schema.ts` Drizzle schema has been migrated. This is UMH's operational target for Phase 2/4 development. Production EntrepreneurOS Neon (ep-winter-sea, us-west-2) currently runs an older v1 schema (`companies`, `crm_contacts`, `crm_deals`, `agent_actions`, `pipeline_runs`) that predates the v2 events-driven architecture. Production cutover plan: after Phase 2 + Phase 4 are validated against ep-dark-poetry, migrate v2 Drizzle schema to ep-winter-sea (with v1 backup), then swap `EOS_DATABASE_URL` there. Until cutover, ep-dark-poetry is the operational target. EOS is pre-launch (founder is sole user), so even the eventual production target will have bounded blast radius.

Watermarks seeded to NOW via `scripts/seed_eos_watermarks_to_now.py` to skip historical replay. This script will be reused during production cutover.

**Options:**
- **A. Manual. Developer updates `tables.py` after every EOS migration. Verified by test.** ← CHOSEN
- B. Codegen. A script reads `saas/db/schema.ts` and generates Python constants. Fragile.
- **C. Integration test. A test queries `information_schema` and compares to `tables.py` constants. CI catches drift.** ← CHOSEN
- **D. Watermark seed-to-NOW on database switch. `scripts/seed_eos_watermarks_to_now.py` discovers orgs and seeds watermarks to current timestamp, preventing historical replay.** ← CHOSEN

**Trade-off:** A + C for schema drift detection. D for database switchovers. The Phase 0 "shared Postgres" assumption (sub-millisecond local reads) was invalidated when ep-winter-sea was discovered to have a different schema. Corrected: ep-dark-poetry hosts the v2 schema. Cross-region latency is not a factor (both UMH and the target DB are in the same Neon cluster).

### 10. Correlation Map Scope — **RESOLVED: B**

`EOSCorrelationMap` — per-integration, in-memory, thread-safe. Mirrors `notion/correlation.py` with `EOSWritebackTarget(org_id, table_name, row_id)`.

**Options:**
- A. Same in-memory `CorrelationMap` as Notion. Simple. Process restart clears it.
- **B. Per-integration correlation maps. EOS and Notion don't share.** ← CHOSEN
- C. Postgres-backed correlation map. Survives restart. Queryable.

**Trade-off:** B for Phase 1 (each integration gets its own `CorrelationMap` instance — this is already how Notion works). C when correlation needs to survive restarts (e.g., long-running fulfillment tracking).

---

## Phase 2 Design (Capabilities)

Phase 2 adds three write capabilities: `create_event`, `create_client`, `update_venture`.
Each performs a single INSERT or UPDATE against the EOS Neon database via psycopg2,
dispatched through the existing `EOSCapabilityHandler.handle_capability()` path.

Phase 0 for this phase = surface open decisions before writing code.

### Drizzle Schema Excerpts (source of truth: `saas/db/schema.ts`)

These are the three target tables. Quoted verbatim from Drizzle so reviewers
can verify the Python mapping without leaving this file.

#### `events` (lines 264-278)

```typescript
export const events = pgTable('events', {
  id:          uuid('id').primaryKey().defaultRandom(),
  orgId:       uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  eventType:   text('event_type').notNull(),
  payloadJson: jsonb('payload_json').notNull().default({}),
  handledBy:   text('handled_by'),
  createdAt:   timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:     index('idx_events_org_id').on(t.orgId),
  orgType:    index('idx_events_org_type').on(t.orgId, t.eventType),
  orgCreated: index('idx_events_org_created').on(t.orgId, t.createdAt),
}))
```

- `org_id`: **uuid**, NOT NULL, FK → organizations(id) ON DELETE CASCADE
- `event_type`: text, NOT NULL
- `payload_json`: jsonb, NOT NULL, default `{}`
- `handled_by`: text, nullable
- `created_at`: timestamptz, NOT NULL, default now()

#### `clients` (lines 442-461)

```typescript
export const clients = pgTable('clients', {
  id:        uuid('id').primaryKey().defaultRandom(),
  orgId:     text('org_id').notNull(),
  ventureId: text('venture_id').notNull(),
  name:      text('name').notNull(),
  email:     text('email').notNull(),
  phone:     text('phone'),
  status:    text('status').notNull().default('lead'),
  source:    text('source').notNull().default('unknown'),
  notes:     text('notes').default(''),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:     index('idx_clients_org_id').on(t.orgId),
  ventureIdx: index('idx_clients_venture_id').on(t.ventureId),
  statusIdx:  index('idx_clients_status').on(t.orgId, t.status),
}))
```

- `org_id`: **text** (NOT uuid), NOT NULL, **no FK constraint**
- `venture_id`: **text** (NOT uuid), NOT NULL, **no FK constraint**
- `name`: text, NOT NULL
- `email`: text, NOT NULL
- `phone`: text, nullable
- `status`: text, NOT NULL, default `'lead'`
- `source`: text, NOT NULL, default `'unknown'`
- `notes`: text, nullable, default `''`
- `created_at`: timestamptz, NOT NULL, default now()
- `updated_at`: timestamptz, NOT NULL, default now()

**Schema asymmetry note:** `clients.org_id` and `clients.venture_id` are `text`,
not `uuid` with FK constraints. This means Postgres will NOT reject an INSERT with
a nonexistent org_id. The `events` table uses `uuid` org_id with a FK. This split
affects validation strategy (Decision 3).

#### `ventures` (lines 169-183)

```typescript
export const ventures = pgTable('ventures', {
  id:             uuid('id').primaryKey().defaultRandom(),
  orgId:          uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  name:           text('name').notNull(),
  stage:          ventureStageEnum('stage').notNull().default('idea'),
  configJson:     jsonb('config_json').notNull().default({}),
  monthlyRevenue: numeric('monthly_revenue', { precision: 12, scale: 2 }).notNull().default('0'),
  monthlyTarget:  numeric('monthly_target', { precision: 12, scale: 2 }).notNull().default('0'),
  createdAt:      timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx: index('idx_ventures_org_id').on(t.orgId),
}))
```

- `org_id`: **uuid**, NOT NULL, FK → organizations(id) ON DELETE CASCADE
- `name`: text, NOT NULL
- `stage`: enum `venture_stage` (`idea`|`pre_revenue`|`early`|`growth`|`scale`), NOT NULL, default `'idea'`
- `config_json`: jsonb, NOT NULL, default `{}`
- `monthly_revenue`: numeric(12,2), NOT NULL, default `'0'`
- `monthly_target`: numeric(12,2), NOT NULL, default `'0'`
- `created_at`: timestamptz, NOT NULL, default now()

**Note:** `monthly_revenue` and `monthly_target` are `numeric(12,2)`, which maps
to Python `Decimal`. Drizzle stores as string (`'0'`). The `update_venture` handler
must accept numeric or string values and pass them correctly.

---

### Open Decision 1: Org Scoping for Writes

**Question:** How does `org_id` flow from `CapabilityRequest` → handler → INSERT?

`CapabilityRequest.params` is `dict[str, Any]` (untyped). For poll-originated signals,
the poller already stuffs `org_id` into the signal envelope payload (see `signals.py:build_signal`).
But for UMH-initiated capability calls (e.g., the cognitive loop decides to create a client),
there's no poller in the path — the pipeline must supply `org_id` in `params`.

**Options:**

- **A. Required in params (Recommended).** Every write capability requires `params["org_id"]`.
  Handler validates presence before touching SQL. Callers (pipeline, cognitive loop,
  external SubmitRequest) must supply it. This is explicit, traceable, and matches how
  EOS's Hono API scopes every mutation with `x-org-id`.

- B. Session/context wrapper. A `CurrentOrg` thread-local or contextvar that gets set
  at pipeline entry. Handlers read from context, not params. Reduces boilerplate but
  hides the dependency and makes testing harder.

- C. Default to the poller's current org. Only works for poll-driven flows. Breaks
  for UMH-initiated calls.

**Recommendation: A.** `org_id` is always required in `params`. Fail loud if missing.
This adds one key to every request but prevents silent cross-tenant writes.
Matches Notion's pattern where `database_id` is always required in params.

---

### Open Decision 2: Schema Authority and Drizzle Mapping

**Question:** `tables.py` currently has one read helper (`fetch_events_since`) and one test
helper (`insert_test_event`). Adding `insert_event()`, `insert_client()`, `update_venture()`
means mirroring three Drizzle tables' write schemas. What's the drift detection story?

**Options:**

- **A. Extend `test_eos_integration.py` with column-type assertions (Recommended).**
  Add `@pytest.mark.integration` tests that query `information_schema.columns` for each
  target table, asserting column names, data types, and NOT NULL constraints match
  what `tables.py` assumes. These run with `EOS_INTEGRATION_TEST=1`. This extends
  Decision 9's existing approach.

- B. Codegen from `schema.ts`. Parse Drizzle definitions and generate Python constants.
  Fragile — Drizzle's TypeScript DSL is not trivially parseable.

- C. Manual coordination only. Developer reads `schema.ts` and updates `tables.py`.
  No automated check.

**Recommendation: A.** Add three new integration tests:
1. `test_clients_schema_matches` — assert columns, types, nullability for clients table
2. `test_ventures_schema_matches` — same for ventures
3. `test_events_write_columns_match` — verify events INSERT assumptions

This catches drift on the next integration test run after a Drizzle migration.

---

### Open Decision 3: Validation Strategy

**Question:** Notion's `create_page` accepts arbitrary properties — Notion validates them.
EOS schema is typed (UUIDs, enums, NOT NULL constraints). Where does validation happen?

The schema asymmetry matters here: `events.org_id` is `uuid` with FK (Postgres rejects bad values),
but `clients.org_id` is `text` with no FK (Postgres accepts anything).

**Options:**

- **A. Validate in `tables.py` helpers (Recommended).** Each insert/update helper validates
  required fields, types, and enum values before executing SQL. `insert_client()` checks
  that `org_id`, `venture_id`, `name`, and `email` are non-empty strings; `status` is
  one of `lead|prospect|client|fulfilled|churned`. `update_venture()` checks `stage` is
  a valid `venture_stage` enum value. Postgres errors are a second defense layer, not primary.

- B. Validate in handler methods. `_create_client()` validates before calling `tables.py`.
  Keeps `tables.py` as pure SQL. Scatters validation across handler methods.

- C. Rely on Postgres errors. Let the INSERT/UPDATE fail and surface the Postgres error
  message as a `CapabilityResponse(success=False)`. Minimal code but exposes raw DB errors
  to the pipeline, and the `clients` table won't catch bad org_ids.

**Recommendation: A.** `tables.py` is the single coupling point — it should enforce the
contract, not just execute SQL. This keeps handlers thin (same pattern as Notion's
`transforms.py` which builds validated payloads). For `clients`, Python-side validation
is the ONLY defense since the table lacks FK constraints.

Enum values to validate:
- `clients.status`: `lead`, `prospect`, `client`, `fulfilled`, `churned`
- `ventures.stage`: `idea`, `pre_revenue`, `early`, `growth`, `scale`

---

### Open Decision 4: Idempotency

**Question:** If handler crashes between INSERT and outcome emission, retry duplicates
the row. What's the dedup strategy?

**Options:**

- **A. Accept duplicates for Phase 2 (Recommended).** `create_event` is append-only
  (event-log semantics — duplicates are tolerable). `create_client` could duplicate
  a lead row, but the cockpit can filter or merge. `update_venture` is idempotent
  by nature (UPDATE with same values is a no-op). Revisit for Phase 3+ when
  `create_transaction` (money) enters scope.

- B. Client-supplied `idempotency_key` column. Caller passes a UUID, handler does
  `INSERT ... ON CONFLICT (org_id, idempotency_key) DO NOTHING`. Requires schema
  migration to add the column and unique index.

- C. Handler-side seen-set. Track `(capability_name, hash(params))` in memory for
  the last N minutes. Fragile — doesn't survive restart, and hash collisions are
  theoretically possible.

**Recommendation: A.** Phase 2 capabilities are low-stakes writes. `create_event` is
an event log (dupes are noise, not corruption). `create_client` at worst creates a
duplicate lead (visible in cockpit, manually mergeable). `update_venture` is naturally
idempotent. Add `idempotency_key` in Phase 3 when `create_transaction` brings money
into scope.

---

### Open Decision 5: Atomicity

**Question:** Each capability = single INSERT/UPDATE in its own transaction?
Or multi-table mutations?

**Options:**

- **A. Single-statement transactions (Recommended).** `create_event` = one INSERT
  into `events`. `create_client` = one INSERT into `clients`. `update_venture` =
  one UPDATE on `ventures`. Each runs in its own autocommit-off transaction
  (psycopg2 default), committed on success, rolled back on exception.

- B. Multi-table mutations. `create_event` also updates a parent table's
  `last_activity_at`. `update_venture` recalculates `monthly_revenue` from
  `transactions`. Adds coupling and partial-failure risk.

**Recommendation: A.** One capability = one statement = one transaction.
No cross-table side effects in Phase 2. If a future capability needs to
atomically touch two tables (e.g., `create_transaction` + update
`ventures.monthly_revenue`), that's a Phase 3 design question — solve it
then with explicit multi-statement transactions, not by overloading Phase 2
capabilities.

---

### Open Decision 6: Outcome Shape

**Question:** Notion outcomes write back to the source page (status property + callout
block). EOS write capabilities have no source page — they CREATE new rows.
What does the outcome look like?

**Options:**

- **A. OutcomeSocket emission + log, carry inserted row_id (Recommended).**
  The `CapabilityResponse.result_data` already returns `{event_id}`, `{client_id}`,
  or `{venture_id, updated: true}`. The outcome receiver logs this. The correlation
  map stores the mapping `correlation_id → (entity_type, entity_id, org_id)`.
  No writeback to EOS tables in Phase 2 — that's Phase 4's job (update `events.handled_by`,
  insert audit trail events, etc.).

- B. Immediate writeback. After `create_event`, update the new event's `handled_by`
  field to `"umh"`. After `create_client`, insert an `events` row recording the
  creation. Adds complexity and couples outcome to capability.

- C. No outcome at all. Fire-and-forget. Breaks the socket contract and loses
  audit trail.

**Recommendation: A.** Phase 2 outcomes are `CapabilityResponse` → `OutcomeEnvelope`
→ `EOSOutcomeReceiver.on_outcome()` → log + correlation cleanup. The inserted
row_id flows through `result_data` so the pipeline knows what was created.
Phase 4 adds writeback (same as Notion Phase 4 pattern).

Outcome payload shape for each capability:

| Capability | `result_data` |
|---|---|
| `create_event` | `{event_id: uuid}` |
| `create_client` | `{client_id: uuid}` |
| `update_venture` | `{venture_id: uuid, updated: true, fields_changed: [...]}` |

---

### Open Decision 7: Permission Model

**Question:** Phase 1 uses `neondb_owner` (BYPASSRLS, full DDL/DML). Phase 2
adds writes. Should it constrain to a dedicated role?

**Options:**

- **A. Stay with `neondb_owner` for Phase 2 (Recommended).** The system is
  single-founder, single-VPS. UMH is a trusted system process running on
  the same machine. The writes are three specific INSERT/UPDATE statements
  behind Python validation. Adding a `umh_writer` role requires a migration
  + GRANT statements + testing — overhead that doesn't reduce actual risk
  in the current deployment topology.

- B. Create `umh_writer` role now. `GRANT INSERT ON events, clients TO umh_writer`.
  `GRANT UPDATE (monthly_revenue, stage) ON ventures TO umh_writer`. Least-privilege.
  Prevents accidental DDL or writes to other tables.

- C. Use `eos_app` role (if it exists) with RLS. Requires `SET LOCAL app.current_org_id`
  per transaction. Most correct but heaviest.

**Recommendation: A.** Defer to Phase 3 or multi-tenant milestone. Document the
future migration path: create `umh_writer` role, grant specific table + column
permissions, update `EOS_DATABASE_URL` connection string. The `tables.py` helpers
already constrain which tables and columns UMH touches — the role would be a
defense-in-depth layer, not a functional change.

---

### Open Decision 8: Failure Modes

**Question:** Notion Phase 2 returns `success:false` with the API error
(rate limit, not found, validation). EOS errors are local Postgres, not
transient external API. Same pattern, or different?

**Options:**

- **A. Same CapabilityResponse pattern, no retry (Recommended).** Postgres
  errors from the same Neon cluster are either:
  - Constraint violations (bad data) → not retryable, return `success:false` + error
  - Connection failures → infrastructure problem, not transient API throttling

  Unlike Notion's 429 (retry after backoff), a local Postgres error means
  something is structurally wrong. Handler catches `psycopg2.Error`, wraps
  it in `CapabilityResponse(success=False, error=..., raw_error=...)`.
  No automatic retry. No circuit breaker.

- B. Add retry with backoff. Treat connection errors as transient (Neon
  cold-start, network blip). Retry once after 1s.

- C. Circuit breaker. After N consecutive Postgres failures, mark EOS
  integration as `degraded` and stop accepting capability requests for
  a cooldown period.

**Recommendation: A for Phase 2.** The connection retry already exists in
`poller.py:_get_connection()` (reconnect on `OperationalError`). For
capability handlers, a failed INSERT is almost always bad data, not a
transient network issue. Surface the error, let the pipeline/governance
layer decide whether to retry.

Exception: if `_get_connection()` (or equivalent) fails for the handler,
it should attempt ONE reconnect (same pattern as the poller) before
returning `success:false`. This is a connection-level retry, not a
statement-level retry.

---

### Implementation Plan (not yet started)

Pending resolution of the 8 decisions above. Expected scope:

**Files modified:**
- `services/umh/integrations/eos/manifest.py` — add 3 capability descriptors
- `services/umh/integrations/eos/tables.py` — add `insert_event()`, `insert_client()`, `update_venture()` with validation
- `services/umh/integrations/eos/handlers.py` — add `_create_event()`, `_create_client()`, `_update_venture()` handler methods
- `services/umh/integrations/eos/outcomes.py` — no change (Phase 4)
- `services/umh/control_plane/app.py` — no change (handler already registered)

**Files created:**
- None expected (all additions go into existing files)

**Tests:**
- `services/umh/tests/test_eos_tables.py` — add insert/update helper tests
- `services/umh/tests/test_eos_handlers.py` — new file, handler unit tests for 3 capabilities
- `services/umh/tests/test_eos_integration.py` — add schema assertion tests (Decision 2)

---

## 12. Implementation Status

### Phase 1: Postgres Poll + Noop Dispatch — **IMPLEMENTED**

**Env vars:**
- `EOS_DATABASE_URL` — required. Postgres connection string for the EOS Neon database.
- `EOS_ORG_IDS` — optional. Comma-separated org UUIDs to whitelist. Empty/unset = poll all orgs.
- `EOS_POLL_INTERVAL` — optional. Seconds between poll cycles (default 15.0).

**Files created:**
- `services/umh/integrations/eos/__init__.py`
- `services/umh/integrations/eos/manifest.py` — config loader, signal/capability descriptors
- `services/umh/integrations/eos/tables.py` — typed query helpers for `events` table
- `services/umh/integrations/eos/signals.py` — `EOSSignalEmitter`
- `services/umh/integrations/eos/poller.py` — `EOSPoller` daemon thread
- `services/umh/integrations/eos/handlers.py` — `EOSCapabilityHandler` (noop)
- `services/umh/integrations/eos/outcomes.py` — `EOSOutcomeReceiver` (log-only stub)
- `services/umh/integrations/eos/correlation.py` — `EOSCorrelationMap`

**Files modified:**
- `services/umh/control_plane/app.py` — `_register_eos_integration()` + lifespan start/stop

**Tests:**
- `services/umh/tests/test_eos_tables.py` — 11 tests
- `services/umh/tests/test_eos_signal_emitter.py` — 12 tests
- `services/umh/tests/test_eos_poller.py` — 13 tests
- `services/umh/tests/test_eos_integration.py` — 6 tests (@pytest.mark.integration, skipped by default)

**Smoke test:**
- `scripts/smoke_eos.py` — insert test event → poll → verify signal → cleanup
