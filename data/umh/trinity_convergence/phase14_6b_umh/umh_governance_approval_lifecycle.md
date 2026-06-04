# UMH Governance and Approval Lifecycle

Phase: 14.6B-UMH (revised 14.6D) | Status: DRAFT -- awaiting operator ratification | Provenance: CODE_RESOLVED_CURRENT_TRUTH + DEC-146C-002/003 ratification

**Governance Scope Expansion (DEC-146C-001/002):** Governance must cover not just signal/action governance, but reality-model mutation governance. The reality model is the central organizing model of UMH -- mutations to source truth, canonical state, and instance reality models are governed actions with risk classification. The materialization principle (DEC-146C-002) adds gap-classification governance: when UMH encounters missing capability, it must classify the gap type (unavailable, under-resourced, unproven, not-yet-acquired, time-bound, impossible, illegal, unsafe) and generate a typed acquisition path rather than treating it as terminal failure.

---

## Permission Tiers (substrate/types.py)

| Tier | Level | Permits | Examples |
|------|-------|---------|----------|
| READ | 1 | Read-only operations | Query memory, view status, list agents |
| DRAFT | 2 | READ + draft operations | Compose messages, plan workflows, generate reports |
| EXECUTE | 3 | DRAFT + execution | Run workflows, execute tasks, call LLMs |
| COMMIT | 4 | EXECUTE + commit operations | Send external messages, make payments, delete data, deploy |

Implementation: PermissionTier.permits(required_tier) -- cumulative (COMMIT permits everything).

## Risk Classes (substrate/types.py + substrate/governance/risk_classes.py)

### Risk Levels

| Risk Class | Level | Requires | Auto-execute threshold |
|------------|-------|----------|----------------------|
| NEGLIGIBLE | 0 | Nothing | Autonomy 0+ |
| LOW | 1 | Nothing | Autonomy 0+ |
| MEDIUM | 2 | Logging | Autonomy 1+ |
| HIGH | 3 | Approval for certain actions | Autonomy 3+ |
| CRITICAL | 4 | Explicit approval always | Autonomy 999 (never) |
| FORBIDDEN | 5 | Always denied | Never |

### Action Risk Categories (substrate/governance/risk_classes.py)

| Category | Risk Class | Blocking |
|----------|-----------|----------|
| READ_ONLY | NEGLIGIBLE | No |
| SAFE_WRITE | LOW | No |
| REVERSIBLE_WRITE | MEDIUM | No |
| IRREVERSIBLE_WRITE | HIGH | Yes |
| EXTERNAL_COMMUNICATION | HIGH | Yes |
| FINANCIAL | CRITICAL | Yes |
| SECURITY_SENSITIVE | CRITICAL | Yes |
| PHYSICAL_WORLD | CRITICAL | Yes |

Blocking = requires explicit approval without bypass.

## Approval Logic (substrate/control_plane/runtime/gateway.py)

### Never Approve (auto-execute)
- Informational messages
- Read-only queries
- Internal writes (memory, logs)
- Analysis without external side effects

### Always Approve (require operator confirmation)
- External sends (DM, email, social post)
- Payment/financial actions
- Delete/irreversible actions
- Security-sensitive actions
- External API mutations

### Approval Flow
1. Gateway receives request
2. Intent classified, action flags checked
3. If approval required: request queued to file (pending/ directory)
4. Approval notification sent (Discord, cockpit WebSocket)
5. Operator reviews in Cockpit ApprovalsPanel or Discord
6. Operator approves/denies via API or Discord command
7. If approved: queued request executed with audit trail
8. If denied: request dropped with audit trail

### Approval Queue (file-based)
Location: substrate/control_plane/orchestrator/approvals/
- pending/ -- awaiting operator decision
- approved/ -- executed after approval

### Cockpit Approval Endpoints
- GET /api/umh/approvals -- list pending approvals
- POST /api/umh/approvals/{id}/approve -- approve (requires operator token, rate-limited 30s)
- POST /api/umh/approvals/{id}/deny -- deny (requires operator token, rate-limited 30s)

## Simulation / Dry-Run (substrate/execution/spine.py)

For HIGH and CRITICAL risk signals:
1. SimulationReality.simulate(content) -> SimulationResult
2. If safe_to_execute=false -> BLOCKED with risk_factors
3. If safe_to_execute=true -> continue to execution

SimulationReality location: substrate/reality_model/simulation.py

## Deliberation Council (substrate/understanding/deliberation/council.py)

For HIGH and CRITICAL risk signals (runs after simulation):
1. DeliberationCouncil.deliberate(content, context) -> DeliberationResult
2. Multi-perspective analysis (multiple viewpoints)
3. Verdict: APPROVE, REJECT, DEFER
4. If REJECT -> BLOCKED with rationale
5. If APPROVE -> continue to execution

## Organism Governance

### Autonomous Action Gateway (substrate/organism/autonomous_action_gateway.py)
- Gate for organism-initiated autonomous actions
- Checks permission level, risk class, operator acceptance mode

### Spine Guard (substrate/organism/spine_guard.py)
- Pre-execution validation for governed execution spine
- Validates work packet authorization before spine execution

### Permission Dialogue (substrate/organism/permission_dialogue.py)
- Interactive permission negotiation between organism and operator
- Used when an action requires clarification or partial approval

### Operator Acceptance Mode (substrate/organism/operator_acceptance_mode.py)
- Configurable acceptance mode for autonomous operations
- Controls how much autonomy the organism has

### Approval Store (substrate/organism/approval_store.py)
- Persistent approval history for organism decisions

## Execution Authority Engine

Location: substrate/governance/policy/execution_authority_engine_v1.py

Types:
- AuthorityClass: classification of execution authority
- ApprovalRequirement: what approval is needed

Location: substrate/governance/policy/authority_engine.py
- AuthorityEngine: evaluates business actions against authority chain

## Rate Limiting (transports/api/cockpit.py)

In-memory per-action rate limiting:
- promote: 60-second window
- execute: 30-second window
- approve: 30-second window

Per client_id. Returns HTTP 429 when exceeded.

## Audit Trail

Every action produces:
- TraceRecord with TraceEvents (substrate/execution/trace.py)
- Error recording via fix-forever pattern (substrate/observability/error_recorder.py)
- JSONL logs with rotation (substrate/observability/jsonl_rotation.py)
- Proof store for governance proofs (substrate/observability/proof_store.py)
- Organism event spine (substrate/organism/event_spine.py)

## Reality-Model Mutation Governance (DEC-146C-001)

| Reality-Model Mutation | Risk Class | Approval Required |
|----------------------|------------|-------------------|
| Observation recording (new signal → reality model) | LOW | No |
| Memory update (execution outcome → memory) | LOW | No |
| Instance reality model update (runtime config) | MEDIUM | No (logged) |
| Source truth promotion (observation → canonical) | HIGH | Yes |
| Canonical reality model correction (manual override) | CRITICAL | Yes |
| Reality layer schema change | CRITICAL | Yes |

## Gaps and Open Questions

### P0 Gaps (must resolve before Stage 1 organism governs implementation — DEC-146C-003)
1. Execution control stubs -- /execution/start, /stop, /pause, /resume return static {ok: true}
2. No cross-projection data access control mechanism
3. SimulationReality needs runtime verification -- does it actually block?
4. Dev bypass allows unauthenticated access from private IPs -- acceptable for single-operator but not for multi-user
5. Reality-model mutation governance not yet implemented -- no risk classification on canonical state changes

### P1 Gaps (must resolve before Trinity feature build)
1. Rate limiting is in-memory -- resets on restart
2. No financial action integration (Stripe not connected)
3. Deliberation council needs runtime verification
4. No automated rollback mechanism

### Operator Decisions Required
1. Should dev bypass be removed before production?
2. What is the maximum autonomy level for overnight/unattended operation?
3. Should financial actions ever be auto-approved above a threshold?
4. Should cross-projection data access be opt-in per projection or globally configured?
