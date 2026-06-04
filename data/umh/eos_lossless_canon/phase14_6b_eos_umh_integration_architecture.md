---
phase: "14.6B-EOS (revised 14.6F)"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "CODE_RESOLVED_CURRENT_TRUTH"
description: "How EOS connects to and uses the UMH substrate — integration model, signal/capability/outcome flows, data boundaries, agent runtime, governance, and implementation gaps"
revision_note: "Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04)."
---

# EOS-UMH Integration Architecture

How EntrepreneurOS connects to, registers with, and operates on the Universal Meta Harness substrate — a reality-isomorphic intelligence harness (DEC-146C-001, DEC-146B-UMH-001).

---

## 1. Integration Model: EOS as UMH Projection

EOS is an **application projection** built on the UMH substrate. UMH (Universal Meta Harness) is a reality-isomorphic intelligence harness whose core functional purpose is to build, maintain, and act through a reality-isomorphic approximation of reality (DEC-146C-001). EOS is not a plugin, not a microservice, not a tenant. It is a first-class projection that registers its agents, signals, capabilities, and outcome receivers with the substrate at startup, then operates through the substrate's execution pipeline and governance engine.

### Architectural Position

```
projections/eos/       (EOS-specific code — agents, views, workflows, integration)
    |
    |  imports from (downward only)
    v
substrate/             (universal platform — types, execution, governance, sockets)
adapters/              (external system adapters — model_router, browser, GWS)
transports/            (I/O surfaces — Discord, HTTP API, node mesh)
```

EOS code lives in `projections/eos/`. It imports from `substrate/` and `adapters/` but substrate never imports from projections. This is enforced by the Architecture Layer Law and `scripts/check_dependency_direction.py` pre-commit hook.

### Registration Protocol

EOS registers with UMH through three abstract port systems in `substrate/sockets/`:

| Port | File | EOS Registers | Purpose |
|------|------|---------------|---------|
| `projection_port` | `substrate/sockets/projection_port.py` | `register_projection("eos", config)` | Declares EOS exists as a projection |
| `SignalSocket` | `substrate/sockets/signal_socket.py` | `EOSSignalEmitter` via `register_emitter()` | Declares what signal types EOS can emit |
| `CapabilitySocket` | `substrate/sockets/capability_socket.py` | `EOSCapabilityHandler` via `register_handler()` | Declares what capabilities EOS provides |
| `OutcomeSocket` | `substrate/sockets/outcome_socket.py` | `EOSOutcomeReceiver` via `register_receiver()` | Receives pipeline outcome notifications |

The `projection_port` is a simple dict registry (`_projections: dict[str, dict[str, Any]]`). It supports `register_projection()`, `get_projection()`, `list_projections()`, and `unregister_projection()`. No schema enforcement — the config dict is opaque to substrate.

### Integration Identity

EOS uses the integration ID `"eos"` everywhere. This string appears in:

- `manifest.py`: `INTEGRATION_ID = "eos"`
- Every `SignalEnvelope.integration_id`
- Every `CapabilityRequest.integration_id`
- Every `OutcomeEnvelope.integration_id`
- Correlation map entries: `EOSWritebackTarget.integration = "eos"`

---

## 2. Signal Flow (EOS to UMH)

### Signal Types Declared

EOS declares exactly 3 signal types in `projections/eos/integration/manifest.py`:

| content_type | Description | Default Urgency | Default Risk Class |
|---|---|---|---|
| `eos_contact_created` | New CRM contact created | NORMAL | READ_ONLY |
| `eos_deal_created` | New CRM deal created | HIGH | READ_ONLY |
| `eos_activity_logged` | CRM activity logged | LOW | READ_ONLY |

All three are READ_ONLY risk class. None trigger external mutations by default.

### Signal Emission Mechanism

EOS does **not** use the `SignalSocket.emit()` path directly. Instead, the `EOSPoller` polls the EOS Postgres database on a background thread, builds `IntegrationSignalEnvelope` objects via `EOSSignalEmitter`, and submits them to the pipeline via a `pipeline_submit_fn` callback.

The flow:

```
EOS Postgres DB (crm_contacts, crm_deals, crm_activities)
    |
    | poll every 15s (configurable via EOS_POLL_INTERVAL)
    v
EOSPoller._poll_table_user()
    |
    | fetch rows with created_at > watermark
    v
EOSPoller._process_row()
    |
    | build signal envelope + writeback target
    v
EOSSignalEmitter.build_*_signal()
    |
    | register correlation_id -> EOSWritebackTarget
    v
EOSCorrelationMap.register()
    |
    | submit to UMH execution pipeline
    v
pipeline_submit_fn(content, risk_class=READ_ONLY, adapter_name="eos", operation="noop", params=envelope.payload, pre_approved=True)
```

### Signal Envelope Structure

Each signal envelope carries:

- `integration_id`: `"eos"`
- `content_type`: one of the 3 declared types
- `payload`: full row data as dict (table_name, row_id, user_id, all fields, adapter_name, operation)
- `raw_content`: human-readable summary string (e.g., `"[crm_contacts] John Smith (john@example.com): lead @ Acme"`)
- `source_identifier`: `"eos:{table}:{row_id}"`
- `correlation_id`: UUID for outcome writeback tracking
- `urgency`: per signal type
- `metadata`: `{"user_id": ..., "table_name": ...}`

### Frequency and Volume

- Poll interval: 15 seconds default, configurable via `EOS_POLL_INTERVAL` env var
- Batch size: 100 rows per (table, user) per poll cycle
- Tables polled: `crm_contacts`, `crm_deals`, `crm_activities`
- User scope: whitelist via `EOS_USER_IDS` env var, or discover all users from the `users` table
- Watermark: high-water mark per (table, user_id) persisted to JSONL file via `WatermarkStore`

---

## 3. Capability Flow (UMH to EOS)

### Capabilities Declared

EOS declares exactly 5 capabilities in `projections/eos/integration/manifest.py`:

| Name | Category | Risk Class | Description |
|---|---|---|---|
| `noop` | RETRIEVE | READ_ONLY | Acknowledge a signal without action |
| `create_contact` | COMMUNICATE | EXTERNAL_COMMUNICATION | Insert a new CRM contact |
| `create_deal` | COMMUNICATE | EXTERNAL_COMMUNICATION | Insert a new CRM deal |
| `update_deal_stage` | COMMUNICATE | EXTERNAL_COMMUNICATION | Update deal stage or probability |
| `log_activity` | COMMUNICATE | EXTERNAL_COMMUNICATION | Log a CRM activity |

Four of five capabilities write to the EOS Postgres database. Only `noop` is read-only.

### Execution Model

When the UMH execution pipeline reaches Stage 5 (execute) and the work packet targets the "eos" adapter, the `CapabilitySocket` routes the `CapabilityRequest` to `EOSCapabilityHandler.handle_capability()`.

The handler:

1. Looks up the capability name in a dispatch map (`_noop`, `_create_contact`, `_create_deal`, `_update_deal_stage`, `_log_activity`)
2. Validates parameters (required fields, enum values, decimal ranges)
3. Executes the SQL via `tables.py` helper functions
4. Returns a `CapabilityResponse` with `success=True` and result data, or `success=False` with error details

Connection management: single persistent `psycopg2` connection with reconnect-on-failure. `autocommit=False` — each operation explicitly commits.

### Input/Output Schemas

Each capability declares typed schemas in the manifest:

- **create_contact** — requires `user_id`, `name`, `email`; optional `status` (lead|prospect|customer|churned), `company`, `title`, `phone`, `notes`
- **create_deal** — requires `user_id`, `title`, `company`, `value` (decimal), `contact_id`; optional `stage` (discovery|proposal|negotiation|closed-won|closed-lost), `probability` (0-100)
- **update_deal_stage** — requires `user_id`, `deal_id`; optional `stage`, `probability` (at least one required)
- **log_activity** — requires `user_id`, `type` (email|call|meeting|task|note), `subject`, `date`, `related_to_type` (contact|deal), `related_to_id`

### Health Check

`EOSCapabilityHandler.health()` attempts a `SELECT 1` against the EOS database. Returns `CapabilityHealth` with status "healthy" or "unavailable". If no `database_url` is configured, returns "healthy" (graceful degradation for environments without EOS DB).

---

## 4. Outcome Writeback

### Dual Writeback Model

`EOSOutcomeReceiver` writes outcomes back to EOS Postgres through two paths:

**Path 1 — Source Row Update:**
Updates `umh_status` column on the original CRM row (crm_contacts, crm_deals, crm_activities, tasks, or agent_actions). Uses severity-based progression — a row's status only advances to higher severity:

| Status | Severity |
|---|---|
| success | 0 |
| timeout | 1 |
| governance_denied | 2 |
| error | 3 |

Only `success`, `timeout`, and `governance_denied` trigger source row updates. `error` does not update the source row (goes to audit only).

**Path 2 — Audit Table Insert:**
Every outcome inserts a row into `umh_outcomes` table with: `user_id`, `trace_id`, `source_table`, `source_row_id`, `outcome_type`, `severity`, and a JSONB `payload` containing signal_id, summary, confidence, duration_ms, governance_decision, result_data, and metadata.

### Correlation Map

The `EOSCorrelationMap` (thread-safe, in-memory) maps `correlation_id: UUID -> EOSWritebackTarget`. Registered when a signal is emitted, looked up when an outcome arrives, removed after successful writeback.

`EOSWritebackTarget` carries: `user_id`, `table_name`, `row_id`, `integration="eos"`.

### Outcome Flow

```
UMH Pipeline completes (Stage 7: outcome classification)
    |
    v
EOSPoller._process_row() checks result for outcome_type
    |
    | builds OutcomeEnvelope with correlation_id
    v
EOSOutcomeReceiver.on_outcome()
    |
    | lookup correlation_id in EOSCorrelationMap
    v
EOSWritebackTarget found? (user_id, table_name, row_id)
    |
    | yes: dual writeback
    v
1. UPDATE source_table SET umh_status = mapped_status WHERE id = row_id (severity-gated)
2. INSERT INTO umh_outcomes (trace_id, source_table, source_row_id, ...)
    |
    | cleanup
    v
EOSCorrelationMap.remove(correlation_id)
```

---

## 5. Data Boundary

### What EOS Owns

EOS owns its entire Postgres schema. All data in these tables belongs to the EOS projection:

| Table | Description | Rows Are |
|---|---|---|
| `crm_contacts` | Leads, prospects, customers | EOS-owned, UMH reads via poller |
| `crm_deals` | Pipeline deals | EOS-owned, UMH reads via poller |
| `crm_activities` | Interaction log | EOS-owned, UMH reads via poller |
| `tasks` | Agent task management | EOS-owned |
| `agents` | AI agent roster | EOS-owned |
| `agent_actions` | Governed agent actions | EOS-owned |
| `agent_metrics` | Daily agent performance | EOS-owned |
| `users` | EOS user accounts | EOS-owned |
| `umh_outcomes` | UMH outcome audit trail | Written by UMH, EOS-owned table |

EOS also owns the `umh_status` column on source tables — this is the single touchpoint where UMH writes into EOS-owned data.

### What UMH Owns

UMH owns:

- Signal envelopes and their lifecycle
- Execution traces (trace_id, signal_id)
- Governance decisions and verdicts
- Pipeline state and stage progression
- Agent registry (Component registrations)
- Correlation state (in-memory, not persisted to EOS)
- Watermarks (stored in `data/eos_watermarks.jsonl`, not in EOS DB)

### Boundary Rules

1. UMH never queries EOS tables directly from substrate code — only through the poller in `projections/eos/integration/`
2. UMH writes to EOS only through `EOSOutcomeReceiver` (umh_status updates + umh_outcomes inserts)
3. EOS never writes to UMH tables or state — it submits signals and receives outcomes through defined protocols
4. Watermark state lives on the UMH side (`data/eos_watermarks.jsonl`), not in EOS
5. Correlation state is in-memory only — lost on restart, which is safe because pending correlations simply never get writeback

---

## 6. Agent Integration

### Registration

EOS registers 10 department agents as `Component` objects via `projections/eos/__init__.py`:

| Agent Name | Department | Permission Tier | Capabilities |
|---|---|---|---|
| `eos-ceo` | executive | commit | strategy, decision, delegation, approval |
| `eos-sales` | sales | execute | outreach, lead_qualification, pipeline, call_booking |
| `eos-marketing` | marketing | execute | content, brand, audience_growth, publishing |
| `eos-finance` | finance | commit | expense_tracking, revenue_monitoring, forecasting, payments |
| `eos-customer-success` | customer_success | execute | ticket_routing, satisfaction, churn_detection, messaging |
| `eos-hr` | hr | execute | hiring, onboarding, team_performance, outreach |
| `eos-legal` | legal | commit | contract_review, compliance, entity_management, contract_execution |
| `eos-operations` | operations | execute | workflow_optimization, process_automation, monitoring, reporting |
| `eos-product` | product | draft | roadmap, feature_prioritization, user_feedback, spec_drafting |
| `eos-engineering` | engineering | execute | code_review, architecture, deployment, incident_response |

Registration uses the public `Substrate.register()` API:

```python
async def register_eos_agents(substrate: Substrate) -> list[Component]:
    registered = []
    for agent in EOS_AGENTS:
        result = await substrate.register(agent)
        if result.success:
            registered.append(agent)
    return registered
```

### Agent Runtime

Each agent inherits from `DepartmentAgent` (in `projections/eos/agents/base.py`), which provides:

- **Skill registry**: agents register named skills with action_type, description, handler function, and minimum permission tier
- **Tier enforcement**: `execute_skill()` checks `PERMISSION_TIER.permits(skill.min_tier)` before executing
- **Browser capabilities**: every agent gets `browser_research` and `browser_act` skills via `_register_browser_skills()`, using `substrate.run_browser_task()`
- **Metadata**: `metadata()` returns projection, department, tier, skill count, and browser capability flag

The CEO agent (`projections/eos/agents/ceo.py`) is the most developed, with 6 skills:

1. `strategic_analysis` — uses `call_with_fallback()` with `agent_type="ceo"` for best model
2. `decision_brief` — evaluates options against north star framework
3. `delegation` — assigns tasks to department agents
4. `pipeline_review` — pulls data from `PipelineView`
5. `morning_brief` — generates CEO briefing
6. `approve_action` — COMMIT tier approval

The CEO also registers with the substrate as a `Component` via `register_ceo_agent()`:

```python
component = Component(
    component_type=ComponentType.AGENT,
    name="eos-ceo",
    capabilities=["strategic_analysis", "decision_making", "delegation", ...],
    metadata=agent.metadata(),
)
return await substrate.register(component)
```

### Skill Allocation

`projections/eos/entities.py` maps skills to departments via `SKILL_ALLOCATION`:

- Sales: 26 skills (outreach, lead analysis, CRM, research)
- Marketing: 9 skills (content, campaigns, performance analysis)
- Operations: 11 skills (playbooks, scheduling, communication)
- Customer Success: 2 skills (churn prevention, onboarding)
- Engineering: 1 skill (adversarial review)
- Executive: 4 skills (CEO/portfolio frameworks, reporting)
- Finance, HR, Legal, Product: 0 skills (not yet populated)

---

## 7. Intelligence Routing

### How EOS Agents Use model_router

EOS agents use `adapters/models/model_router.py` via `call_with_fallback()` — the single module-level entry point for all LLM calls.

Key parameters EOS agents use:

| Parameter | EOS Usage | Effect |
|---|---|---|
| `agent_type="ceo"` | CEO agent strategic calls | Forces best available model (Opus via cc_sdk) |
| `task_type="fast_response"` | All department agent skill calls | Routes to fastest adequate model |
| `force_opus=True` | Not currently used but available | Bypasses economy mode for critical calls |

### Routing Chain

Current chain (in order of preference):

1. **cc_sdk** — Claude Opus 4.6 via Max subscription CLI, no API cost, 120s timeout
2. **Gemini 2.5 Flash** — Python SDK, fast, API cost
3. **Groq** — fast inference, API cost
4. **Ollama** — local fallback (gemma3:4b on VPS)

### Deterministic-First Pattern

Every EOS agent skill follows the deterministic-first principle:

1. Build a deterministic result first (template, lookup table, rule-based)
2. Try AI enhancement via `call_with_fallback()`
3. If AI succeeds and output is better, use it
4. If AI fails, return the deterministic result

Example from `OutreachWorkflow._draft_message()`:

```python
# Deterministic template first
template = f"Hey {name} — I noticed your interest in {hook}..."

# Try AI enhancement
try:
    result = call_with_fallback(prompt=..., task_type="fast_response")
    if result.output and len(result.output.strip()) > 20:
        return result.output.strip()[:500]
except Exception:
    pass

# Fallback to template
return template
```

---

## 8. Governance Integration

### How EOS Uses Substrate Governance

EOS integrates with the `GovernanceEngine` (in `substrate/control_plane/governance.py`) at two levels:

**Level 1 — Signal Classification:**
When EOS signals enter the pipeline, the governance engine classifies them by risk class and determines autonomy level. All current EOS signals are `READ_ONLY`, which means:

- Autonomy threshold: 0 (fully autonomous, no approval needed)
- No human-in-the-loop gate required
- `pre_approved=True` is passed by the poller for all submissions

**Level 2 — Capability Governance:**
When capabilities are invoked, the risk class on each `CapabilityDescriptor` determines governance behavior:

| Capability | Risk Class | Governance Behavior |
|---|---|---|
| `noop` | READ_ONLY | No governance gate |
| `create_contact` | EXTERNAL_COMMUNICATION | Requires autonomy level >= 3 or pre-approval |
| `create_deal` | EXTERNAL_COMMUNICATION | Requires autonomy level >= 3 or pre-approval |
| `update_deal_stage` | EXTERNAL_COMMUNICATION | Requires autonomy level >= 3 or pre-approval |
| `log_activity` | EXTERNAL_COMMUNICATION | Requires autonomy level >= 3 or pre-approval |

### Permission Tier Enforcement

EOS agents enforce permission tiers locally via `DepartmentAgent.execute_skill()`:

```python
if not self.PERMISSION_TIER.permits(skill.min_tier):
    return SkillResult(success=False, error="Agent tier ... cannot execute ...")
```

Tier hierarchy (from `substrate/types.py`):

- `READ` — view data only
- `DRAFT` — create drafts, no external effect
- `EXECUTE` — take actions within defined scope
- `COMMIT` — approve, finalize, external commitments

The `required_tier_for_action()` function maps action types to minimum tiers, used to auto-assign `min_tier` when registering skills.

### Governance Denial Writeback

When governance denies an EOS action, the outcome writeback maps `"governance_denied"` to severity 2 and writes:

1. Source row: `umh_status = "governance_denied"` (if severity is higher than current)
2. Audit row: full governance_decision in the JSONB payload

---

## 9. Current Code Truth

### File Inventory (projections/eos/)

Total: 30 Python files across 5 packages.

**projections/eos/ (root)**

| File | Lines | Purpose |
|---|---|---|
| `__init__.py` | 93 | 10 Component declarations + `register_eos_agents()` |
| `entities.py` | 880 | Full entity hierarchy: departments, roles, companies, portfolios, users, workflows, dashboards, skill allocation |

**projections/eos/agents/ (10 agents + base)**

| File | Purpose |
|---|---|
| `base.py` | `DepartmentAgent` base class — skill registry, tier enforcement, browser capabilities |
| `ceo.py` | CEO agent — 6 skills, COMMIT tier, uses `call_with_fallback(agent_type="ceo")` |
| `sales.py` | Sales agent — outreach, qualification, pipeline skills |
| `marketing.py` | Marketing agent — content, brand, growth skills |
| `finance.py` | Finance agent — expense, revenue, forecast skills |
| `customer_success.py` | CS agent — tickets, satisfaction, churn skills |
| `hr.py` | HR agent — hiring, onboarding, performance skills |
| `legal.py` | Legal agent — contracts, compliance, entity management skills |
| `operations.py` | Ops agent — workflow, process, monitoring skills |
| `product.py` | Product agent — roadmap, features, feedback skills |
| `engineering.py` | Engineering agent — code review, deploy, incident skills |

**projections/eos/integration/ (7 files, UMH bridge)**

| File | Lines | Purpose |
|---|---|---|
| `manifest.py` | 157 | Integration ID, 3 signal descriptors, 5 capability descriptors, config loader |
| `signals.py` | 158 | `EOSSignalEmitter` — builds `IntegrationSignalEnvelope` from polled rows |
| `handlers.py` | 158 | `EOSCapabilityHandler` — handles capability requests, dispatches to tables.py |
| `outcomes.py` | 183 | `EOSOutcomeReceiver` — dual writeback (source row + audit table) |
| `tables.py` | 583 | Typed row dataclasses, SQL queries, insert/update helpers, validation |
| `correlation.py` | 42 | `EOSCorrelationMap` + `EOSWritebackTarget` — thread-safe in-memory |
| `poller.py` | 257 | `EOSPoller` — background thread, watermark-based polling, submit to pipeline |

**projections/eos/views/ (3 views)**

| File | Purpose |
|---|---|
| `pipeline.py` | `PipelineView` — projects CRM data into 6-stage pipeline snapshot |
| `kpis.py` | KPI aggregation view |
| `activity.py` | Activity feed view |

**projections/eos/workflows/ (3 workflows)**

| File | Purpose |
|---|---|
| `outreach.py` | `OutreachWorkflow` — 5-step prospect outreach with deterministic qualification + AI message drafting |
| `followup.py` | Follow-up sequence workflow |
| `content.py` | Content calendar workflow |

### Substrate Types Used by EOS

EOS imports these types from `substrate/types.py`:

- `Component`, `ComponentType`, `RegistrationResult` — agent registration
- `PermissionTier`, `required_tier_for_action` — tier enforcement
- `ActionRiskClass` (aliased as `RiskClass`) — capability risk classification
- `CapabilityCategory`, `CapabilityDescriptor`, `SignalDescriptor`, `SignalUrgency` — manifest declarations
- `CapabilityHealth`, `CapabilityRequest`, `CapabilityResponse` — capability protocol
- `IntegrationSignalEnvelope` (aliased as `SignalEnvelope`) — signal emission
- `OutcomeEnvelope` — outcome writeback
- `Company`, `Department`, `Portfolio`, `Role`, `User` — entity model
- `Dashboard`, `DashboardWidget`, `DashboardWidgetType` — dashboard model
- `Workflow`, `WorkflowStep`, `WorkflowStepType`, `WorkflowTriggerType`, `WorkflowExecutionMode` — workflow model
- `OperatorType` — human/AI/hybrid role classification

### Protocol Conformance

EOS classes structurally satisfy (but do not inherit from) the protocols in `substrate/sockets/protocols.py`:

| Protocol | EOS Implementation | Verified By |
|---|---|---|
| `SignalEmitter` | `EOSSignalEmitter` | Has `integration_id` property + `describe_signals()` |
| `CapabilityHandler` | `EOSCapabilityHandler` | Has `integration_id` + `describe_capabilities()` + `handle_capability()` + `health()` |
| `OutcomeReceiver` | `EOSOutcomeReceiver` | Has `integration_id` + `on_outcome()` + `accepts_outcomes()` |

The protocols are `@runtime_checkable`, so `isinstance(emitter, SignalEmitter)` returns True at runtime without inheritance.

---

## 10. Implementation Gaps

### Gap 1: No Startup Wiring

There is no single `boot_eos()` function that:
- Calls `register_projection("eos", config)` on the projection port
- Registers `EOSSignalEmitter` on the `SignalSocket`
- Registers `EOSCapabilityHandler` on the `CapabilitySocket`
- Registers `EOSOutcomeReceiver` on the `OutcomeSocket`
- Starts the `EOSPoller`
- Registers all 10 agents via `register_eos_agents()`

Each piece exists, but there is no orchestrated startup sequence that wires them together.

**Provenance: INFERRED_PROFESSIONAL_GAP**

### Gap 2: Poller Does Not Use SignalSocket

The `EOSPoller` calls `pipeline_submit_fn()` directly, bypassing `SignalSocket.emit()`. This means signal validation against the catalog is skipped, and the `SignalSocket` does not know about EOS signals passing through the system. The emitter is built but never registered with the socket.

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

### Gap 3: Limited Signal Types

Only 3 signal types (contacts, deals, activities) out of 7 known EOS tables (crm_contacts, crm_deals, crm_activities, tasks, agents, agent_actions, agent_metrics). The poller only handles the 3 CRM tables. `tasks`, `agent_actions`, and `agent_metrics` have typed row dataclasses (`TaskRow`, `AgentActionRow`) and fetch functions in `tables.py` but no signal types, emitter methods, or poller support.

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

### Gap 4: No ViewSubscriber Implementation

EOS has no implementation of the `ViewSubscriber` protocol from `substrate/sockets/protocols.py`. This means EOS cannot receive real-time pipeline state frames. The `ViewFrame` envelope type exists but EOS does not subscribe to it.

**Provenance: INFERRED_PROFESSIONAL_GAP**

### Gap 5: Agent Skills Not Wired to Capabilities

The 10 department agents have rich skill registries (browser research, strategic analysis, outreach, etc.) but these are not exposed through the `CapabilitySocket`. The only capabilities registered are the 5 CRM CRUD operations. An agent's skill cannot be invoked via the substrate capability protocol.

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

### Gap 6: Workflow Engine Not Integrated

The 3 workflow implementations (`outreach.py`, `followup.py`, `content.py`) and the 10 workflow definitions in `entities.py` exist as standalone Python classes. They are not triggered by the UMH execution pipeline, not governed by the governance engine, and not visible to the substrate. The workflow trigger types (SCHEDULED, MANUAL, EVENT) are declared but no scheduler or event dispatcher connects them.

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

### Gap 7: Entity Model Not Persisted

`entities.py` defines the full EOS entity hierarchy (departments, roles, companies, portfolios, users, dashboards, skill allocations, workflows) as factory functions that return Pydantic/substrate types. But these are not persisted anywhere. Calling `default_departments(org_id)` returns fresh objects each time. No Neon registration, no substrate state persistence.

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

### Gap 8: Correlation Map Not Persistent

`EOSCorrelationMap` is in-memory only. If the process restarts, all pending correlations are lost. Outcomes for in-flight signals will silently fail to writeback (the lookup returns None and the outcome is skipped with a debug log).

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

### Gap 9: No Multi-Tenant Isolation

The EOS integration uses a single `EOS_DATABASE_URL` for all operations. There is no per-tenant/per-org database routing. The `user_ids` whitelist provides some scoping, but it is a flat list, not an org-aware hierarchy.

**Provenance: INFERRED_PROFESSIONAL_GAP**

### Gap 10: SaaS Codebase Divergence

The saas/ codebase (TypeScript/React) has its own schema, routes, and entity definitions that overlap with `projections/eos/`. The Drizzle ORM pgTable definitions in saas/ are the actual source of truth for the EOS database schema, but `tables.py` in projections/eos/ writes raw SQL against those tables. Schema drift between the two is currently undetected.

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

---

## 11. Open Questions

### Q1: Should EOS signals route through SignalSocket or continue with direct pipeline submission?

The current pattern (poller calls `pipeline_submit_fn` directly) is simpler and avoids one level of indirection. But it bypasses signal catalog validation and makes the SignalSocket unaware of EOS traffic. If other projections need to observe EOS signals (e.g., CreatorOS cross-referencing contacts), the socket pattern is required.

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

### Q2: Should agent skills be exposed as substrate capabilities?

Currently, agent skills (strategic_analysis, outreach, content drafting) are only callable by directly instantiating the agent class. Exposing them as capabilities would allow the substrate execution pipeline to invoke any agent skill through the standard governance and execution path. This adds governance coverage but also complexity.

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

### Q3: How should EOS entity state be persisted?

Options:
1. Persist to EOS Postgres (matches SaaS schema, keeps EOS self-contained)
2. Persist to Neon via substrate state layer (integrates with UMH state management)
3. Hybrid: EOS Postgres for operational data, Neon for agent/workflow registration

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

### Q4: What is the target schema reconciliation path between saas/ Drizzle ORM and projections/eos/ raw SQL?

The saas/ TypeScript codebase defines the canonical EOS schema via Drizzle ORM. The Python integration writes raw SQL against those tables. A schema migration in saas/ could silently break the Python integration. Options: generate Python types from Drizzle schema, shared SQL migration system, or runtime schema validation.

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

### Q5: When should the poller evolve to event-driven (CDC/webhooks)?

Polling every 15s is simple and reliable but has latency (up to 15s) and creates unnecessary DB load when no changes exist. Postgres LISTEN/NOTIFY or a CDC tool (Debezium) could provide real-time signal emission. The watermark pattern in the poller is already designed for exactly-once semantics, so migration to CDC would be a transport change, not a semantic change.

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

### Q6: How should cross-projection signal visibility work?

If CreatorOS needs to react to EOS signals (e.g., a new client in EOS triggers a CreatorOS content campaign), the current direct-submit pattern does not support it. The SignalSocket has the infrastructure for this (multiple emitters, catalog-based routing), but the wiring does not exist.

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

---

## Summary

EOS connects to UMH through a well-defined integration layer in `projections/eos/integration/` that declares 3 signal types, 5 capabilities, and an outcome receiver with dual writeback. Ten department agents register as Components with skill registries and browser capabilities. All LLM calls route through `adapters/models/model_router.py` with deterministic fallbacks. Governance integration covers signal classification and capability risk assessment.

The integration code is structurally sound — correct protocol conformance, proper layering, typed data boundaries — but operationally incomplete. The startup wiring, signal socket integration, workflow engine connection, and entity persistence are the primary gaps between the current code and a production-ready EOS-on-UMH deployment.

---

*Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).*
