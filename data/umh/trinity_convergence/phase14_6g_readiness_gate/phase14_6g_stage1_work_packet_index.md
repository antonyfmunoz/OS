---
phase: "14.6G"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "READINESS_GATE"
sources:
  - "Phase 14.6G dependency graph"
  - "Phase 14.6G acceptance criteria"
  - "Codebase survey of existing infrastructure"
---

# Phase 14.6G: Stage 1 Work Packet Index

## What This Is

Implementation-ready work packets for UMH Stage 1. These packets are defined but NOT executed. Execution requires operator approval of Phase 14.7A.

## Work Packet Format

Each packet specifies: objective, affected files/modules, required context, acceptance criteria, tests/checks, risk level, approval requirement, rollback expectation, and dependency links.

---

## Wave 1: Foundation Wiring

### WP-1.1: Reality Model HTTP Routes

**Objective:** Expose CanonicalRealityModel and InstanceRealityModel through HTTP API endpoints so Cockpit can read and update reality model state.

**Affected Files/Modules:**
- `transports/api/cockpit.py` (extend with reality model routes)
- `substrate/reality_model/canonical.py` (read -- already production)
- `substrate/reality_model/instance.py` (read -- already production)
- `substrate/reality_model/simulation.py` (read -- already production)

**Required Context:**
- `CanonicalRealityModel` persists to JSON, has `observe()`, `search()`, `get_observations()`
- `InstanceRealityModel` persists to JSONL, has `observe()`, `search()`, capacity management
- `SimulationReality` has `simulate_path()`, `evaluate_gaps()`
- Existing cockpit routes at `/api/umh/` pattern

**Acceptance Criteria:**
- GET `/api/umh/reality-model/canonical` returns canonical observations
- GET `/api/umh/reality-model/instance` returns instance observations
- POST `/api/umh/reality-model/observe` writes new observation (governance-gated)
- GET `/api/umh/reality-model/search?q=<term>` returns scored search results
- POST `/api/umh/reality-model/simulate` runs simulation and returns gap analysis

**Tests/Checks:**
- Unit test: each endpoint returns correct schema
- Integration test: observation persists across restart
- Governance test: canonical mutation requires HIGH risk approval
- Load test: search returns within 500ms for 1000 observations

**Risk Level:** MEDIUM (adding routes to existing router, no schema migration)

**Approval Requirement:** YES -- new API surface

**Rollback Expectation:** Remove route registration from cockpit.py; no data loss

**Dependency Links:** None (can start immediately)

---

### WP-1.2: Cockpit WorldModelPanel Wiring

**Objective:** Connect WorldModelPanel.tsx to the reality model HTTP endpoints from WP-1.1 so the panel displays real reality model data instead of store-based state.

**Affected Files/Modules:**
- `cockpit/src/renderer/panels/WorldModelPanel.tsx` (603 lines)
- `cockpit/src/renderer/stores/` (world model store)
- `cockpit/src/renderer/services/` (API client layer)

**Required Context:**
- WorldModelPanel currently polls `useWorldModelStore`
- No API calls to reality model endpoints exist in frontend
- Panel should display: canonical observations, instance observations, confidence scores, decay
- Must follow existing Cockpit component patterns

**Acceptance Criteria:**
- WorldModelPanel fetches from `/api/umh/reality-model/canonical` and `/api/umh/reality-model/instance`
- Observations render with confidence scores and timestamps
- Search input queries `/api/umh/reality-model/search`
- Panel updates on polling interval (configurable, default 30s)
- Graceful degradation: shows "backend unreachable" when API unavailable

**Tests/Checks:**
- Component renders without errors
- API calls fire on mount
- Graceful degradation renders fallback message
- Search input debounces and triggers API call

**Risk Level:** MEDIUM (modifying existing UI component)

**Approval Requirement:** YES -- modifying operator-facing interface

**Rollback Expectation:** Revert WorldModelPanel.tsx to previous version; store-based state still works

**Dependency Links:** WP-1.1 (needs HTTP endpoints to call)

---

### WP-1.3: Memory Route Upgrade

**Objective:** Upgrade existing memory routes from raw JSONL access to typed ConversationMemory and AgentMemory class integration.

**Affected Files/Modules:**
- `transports/api/cockpit.py` (existing `/api/umh/memory` routes)
- `substrate/state/memory/memory.py` (read -- already production)
- `substrate/state/memory/contracts/` (read -- already production)

**Required Context:**
- Current memory routes read/write JSONL directly via `MEMORY_STORE` path
- `ConversationMemory` has Neon persistence, semantic search, session management
- `AgentMemory` has Neon persistence, embedding storage, milestone alerts
- Goal: routes should use typed memory classes, not raw file I/O

**Acceptance Criteria:**
- GET `/api/umh/memory/conversations` queries ConversationMemory, not JSONL
- GET `/api/umh/memory/agents` queries AgentMemory
- POST `/api/umh/memory/search` uses `semantic_search()` method
- GET `/api/umh/memory/recent` uses `get_recent()` method
- Backward compatibility: existing Cockpit memory panels still work

**Tests/Checks:**
- Unit test: each endpoint returns correct schema
- Integration test: memory persists to Neon (not just JSONL)
- Backward compatibility: existing memory panel components render without errors
- Semantic search returns relevant results for known queries

**Risk Level:** MEDIUM (changing data source for existing routes)

**Approval Requirement:** YES -- changing memory access pattern

**Rollback Expectation:** Revert route handlers to JSONL-based access; no data loss (Neon data persists independently)

**Dependency Links:** None (can start in parallel with WP-1.1)

---

### WP-1.4: Execution Control Wiring

**Objective:** Wire the 4 execution control endpoints from static `{"ok": true}` stubs to actual ExecutionSpine control.

**Affected Files/Modules:**
- `transports/api/cockpit.py` (execution control endpoints)
- `transports/api/cockpit_spine_router.py` (existing spine router)
- `substrate/execution/spine.py` (read -- already production)
- `substrate/control_plane/governance.py` (read -- already production)

**Required Context:**
- 4 execution control endpoints currently return static responses
- ExecutionSpine has full 8-stage pipeline with risk classification
- Governance stack has RiskClass, ActionRiskCategory, policy engine
- Goal: Cockpit can start/stop/pause/resume execution through these endpoints

**Acceptance Criteria:**
- POST `/api/umh/execution/start` initiates spine execution for a given signal
- POST `/api/umh/execution/pause` pauses current execution
- POST `/api/umh/execution/resume` resumes paused execution
- POST `/api/umh/execution/stop` stops current execution
- Each endpoint returns actual execution state, not static JSON
- Governance gating applies: CRITICAL actions require approval

**Tests/Checks:**
- Unit test: start returns execution ID
- Integration test: start → pause → resume → stop lifecycle works
- Governance test: CRITICAL execution requires approval before proceeding
- Error test: stop on non-existent execution returns appropriate error

**Risk Level:** MEDIUM (wiring stubs to production code)

**Approval Requirement:** YES -- enabling execution control

**Rollback Expectation:** Revert endpoints to static stubs; no data loss

**Dependency Links:** WP-1.1 (execution needs reality model context), WP-1.3 (execution needs memory context)

---

## Wave 2: Organism Loop

### WP-2.1: Intent Capture Pipeline

**Objective:** Build the pipeline from Cockpit text/voice input through intent classification to memory persistence.

**Affected Files/Modules:**
- `transports/api/cockpit.py` (intent submission endpoint)
- `substrate/execution/spine.py` (stage 1: Interpret)
- `substrate/state/memory/memory.py` (ConversationMemory persistence)
- `cockpit/src/renderer/` (input component)

**Required Context:**
- Spine stage 1 (`_classify_intent`) already exists
- ConversationMemory has `log()` and `log_event()` methods
- Cockpit has text input components
- Intent types defined in substrate/types.py

**Acceptance Criteria:**
- Operator types intent in Cockpit text input
- POST `/api/umh/intent` receives text, classifies via spine stage 1
- Classified intent persisted to ConversationMemory
- Response includes intent type, confidence, and memory reference
- Intent retrievable via GET `/api/umh/memory/recent`

**Tests/Checks:**
- Unit test: intent classification returns valid type for sample inputs
- Integration test: full pipeline from HTTP POST to Neon persistence
- Edge case: empty input returns validation error
- Edge case: very long input truncates gracefully

**Risk Level:** MEDIUM (new endpoint + pipeline wiring)

**Approval Requirement:** YES -- new input pipeline

**Rollback Expectation:** Remove intent endpoint; no data loss (memory entries persist)

**Dependency Links:** WP-1.3 (needs memory routes), WP-1.4 (needs execution spine wired)

---

### WP-2.2: Work Packet Lifecycle

**Objective:** Build the complete work packet lifecycle: creation from intent, persistence, status tracking, and Cockpit visibility.

**Affected Files/Modules:**
- `transports/api/cockpit_universal_work_routes.py` (extend)
- `substrate/organism/work_packet.py` (read -- already production)
- `substrate/organism/work_packet_engine.py` (read -- already production)
- `cockpit/src/renderer/panels/` (work packet panel)

**Required Context:**
- WorkPacket dataclass exists with full field set
- `persist_packets()` and `load_packets()` exist
- `requires_operator_approval()` and `can_delegate()` exist
- Work packet routes may partially exist in universal_work_routes.py

**Acceptance Criteria:**
- POST `/api/umh/work-packets/generate` accepts intent and produces work packets
- GET `/api/umh/work-packets` lists all work packets with status
- GET `/api/umh/work-packets/<id>` returns single packet with full detail
- PATCH `/api/umh/work-packets/<id>/status` updates packet status
- Cockpit panel renders work packet list with status indicators
- Complex intent decomposes into multiple linked packets

**Tests/Checks:**
- Unit test: work packet generation from sample intent
- Integration test: create → list → get → update lifecycle
- Persistence test: packets survive service restart
- Decomposition test: multi-step intent produces linked packets

**Risk Level:** MEDIUM (extending existing infrastructure)

**Approval Requirement:** YES -- new work packet management surface

**Rollback Expectation:** Remove route extensions; existing work packet engine unaffected

**Dependency Links:** WP-2.1 (needs intent capture to generate packets from)

---

### WP-2.3: Approval UI Wiring

**Objective:** Wire the Cockpit ApprovalsPanel to the governance stack so operators can approve/deny risky actions through the UI.

**Affected Files/Modules:**
- `cockpit/src/renderer/panels/ApprovalsPanel.tsx` (251 lines -- extend)
- `transports/api/cockpit.py` (existing approval routes)
- `substrate/sockets/approval_port.py` (read -- register_approval_handler, submit_approval)
- `substrate/governance/risk_classes.py` (read -- ActionRiskCategory)

**Required Context:**
- ApprovalsPanel.tsx exists (251 lines)
- approval_port.py exports `register_approval_handler` and `submit_approval` as functions
- Approval routes may partially exist in cockpit.py
- Risk classification already works in governance stack

**Acceptance Criteria:**
- Pending approvals appear in ApprovalsPanel with: action description, risk level, timestamp
- Operator can click Approve → action executes
- Operator can click Deny → action is blocked with denial reason
- Approval history is persisted and queryable
- Risk level badge shows MEDIUM/HIGH/CRITICAL with appropriate visual weight

**Tests/Checks:**
- Component test: ApprovalsPanel renders pending items
- Integration test: approve → action executes
- Integration test: deny → action blocked
- Persistence test: approval history survives restart

**Risk Level:** MEDIUM (wiring existing UI to existing governance)

**Approval Requirement:** YES -- this IS the approval mechanism

**Rollback Expectation:** Revert panel to previous state; governance stack unaffected

**Dependency Links:** None within Wave 2 (can start in parallel with WP-2.1, WP-2.2)

---

### WP-2.4: Agent/Tool Routing from Work Packets

**Objective:** Route approved work packets to appropriate agents/tools through the existing model_router and capability infrastructure.

**Affected Files/Modules:**
- `substrate/organism/work_packet_engine.py` (extend with routing logic)
- `adapters/models/model_router.py` (read -- already production)
- `substrate/sockets/capability_socket.py` (read -- capability registration)
- `substrate/execution/spine.py` (stage 5: Route, stage 6: Execute)

**Required Context:**
- `call_with_fallback()` is the single entry point for LLM calls
- Capability routing exists in spine stage 5
- Work packets have `affected_files` and objective that determine routing
- Available capabilities: Claude Code (cc_sdk), shell, GitHub, documentation

**Acceptance Criteria:**
- Approved work packet with code task routes to cc_sdk capability
- Approved work packet with shell task routes to subprocess
- Approved work packet with GitHub task routes to GitHub adapter
- Routing decision logged with rationale
- Failed routing produces typed gap (UNAVAILABLE) not silent failure
- Fallback chain activates when primary capability unavailable

**Tests/Checks:**
- Unit test: routing decision for code/shell/GitHub/doc task types
- Integration test: approved packet → capability activation → result returned
- Fallback test: primary capability down → fallback activates
- Gap test: no capability available → typed UNAVAILABLE gap returned

**Risk Level:** MEDIUM (extending existing routing with work packet awareness)

**Approval Requirement:** YES -- enabling automated execution from UI

**Rollback Expectation:** Remove routing extension; work packet engine still persists/loads packets

**Dependency Links:** WP-2.1 (intent), WP-2.2 (packets), WP-2.3 (approval)

---

## Wave 3: Feedback Loop

### WP-3.1: Outcome Recording to Reality Model

**Objective:** After work packet execution completes (success or failure), record the outcome as an observation in the appropriate reality model.

**Affected Files/Modules:**
- `substrate/organism/work_packet_engine.py` (extend with outcome recording)
- `substrate/reality_model/canonical.py` (observe method)
- `substrate/reality_model/instance.py` (observe method)
- `substrate/state/memory/memory.py` (log_outcome method)

**Required Context:**
- Both reality model classes have `observe()` for adding observations
- Canonical model mutations are HIGH risk (governance-gated)
- Instance model updates are LOW risk (free updates)
- ConversationMemory has `log_outcome()` for outcome persistence
- Outcomes should capture: what was done, result, confidence, affected artifacts

**Acceptance Criteria:**
- Successful work packet → instance reality model observation with outcome details
- Failed work packet → instance reality model observation with failure details
- Canonical model update proposals → HIGH risk approval required
- Memory log_outcome called for all outcomes
- Updated observations visible in Cockpit WorldModelPanel

**Tests/Checks:**
- Unit test: success outcome produces correct observation schema
- Unit test: failure outcome produces correct observation schema
- Governance test: canonical update requires approval
- Integration test: outcome → observe → Cockpit panel refresh shows new data

**Risk Level:** MEDIUM (extending existing outcome recording)

**Approval Requirement:** YES -- connects execution outputs to reality model

**Rollback Expectation:** Remove outcome recording extension; reality model retains existing data

**Dependency Links:** WP-1.1 (reality model routes), WP-2.4 (needs execution results to record)

---

### WP-3.2: Self-Improvement Cadence Wiring

**Objective:** Wire the existing AutonomousCadence and SelfBuildQueueEngine to Cockpit so operators can view, approve, and control self-improvement cycles.

**Affected Files/Modules:**
- `transports/api/cockpit_autonomous_routes.py` (586 lines -- verify wiring)
- `transports/api/cockpit_self_build_routes.py` (191 lines -- verify wiring)
- `substrate/organism/autonomous_cadence.py` (read -- already production)
- `substrate/organism/self_build_queue.py` (read -- already production)
- `cockpit/src/renderer/panels/SelfBuildPanel.tsx` (243 lines -- verify data binding)

**Required Context:**
- AutonomousCadence has `run_cycle()`, candidate discovery, dry-run enforcement
- SelfBuildQueueEngine manages the self-build proposal queue
- Routes may already be partially wired
- SelfBuildPanel.tsx exists but data binding may be incomplete
- `dry_run_only` MUST remain true until operator explicitly enables

**Acceptance Criteria:**
- GET `/api/umh/autonomous/status` returns cadence state (active, idle, cycle count)
- GET `/api/umh/autonomous/candidates` returns discovered improvement candidates
- POST `/api/umh/autonomous/run-cycle` triggers one cadence cycle (dry-run only)
- SelfBuildPanel shows candidates, proposals, and cycle history
- Operator can approve individual proposals through ApprovalsPanel
- `dry_run_only = true` is enforced and cannot be overridden via API

**Tests/Checks:**
- Unit test: cadence cycle discovers candidates from template registry
- Integration test: full cycle → candidate → proposal → approval → execution
- Safety test: `dry_run_only` cannot be set to false via API endpoint
- UI test: SelfBuildPanel renders candidate list with status

**Risk Level:** LOW (wiring existing production code to existing UI)

**Approval Requirement:** YES -- self-improvement is inherently governance-sensitive

**Rollback Expectation:** Revert route wiring; cadence engine continues operating independently

**Dependency Links:** WP-2.3 (approval UI for self-improvement proposals)

---

### WP-3.3: Verification Pipeline Integration

**Objective:** Connect the verification/audit infrastructure to the work packet lifecycle so completed packets trigger automated verification.

**Affected Files/Modules:**
- `substrate/organism/work_packet_engine.py` (extend with verification triggers)
- `scripts/check_dependency_direction.py` (read -- existing gate)
- `scripts/check_type_divergence.py` (read -- existing gate)
- `scripts/check_instance_leak.py` (read -- existing gate)
- `scripts/check_projection_leak.py` (read -- existing gate)

**Required Context:**
- 4 pre-commit gate scripts exist and are production
- Work packets have `acceptance_criteria` and `tests` fields
- Verification should run: relevant gate scripts, specified tests, diff generation
- Failed verification should block packet completion

**Acceptance Criteria:**
- Completed work packet triggers verification step automatically
- Code changes trigger relevant pre-commit gate scripts
- Test files trigger pytest for affected test modules
- Verification result attached to work packet record
- Failed verification: packet status = VERIFICATION_FAILED, not COMPLETE
- Verification results visible in Cockpit

**Tests/Checks:**
- Unit test: verification trigger fires on packet completion
- Integration test: code change → gate scripts → pass/fail result
- Blocking test: failed verification prevents COMPLETE status
- Result test: verification result persisted with packet

**Risk Level:** LOW (connecting existing scripts to existing lifecycle)

**Approval Requirement:** NO -- verification is read-only, non-destructive

**Rollback Expectation:** Remove verification trigger; packets complete without automated checks

**Dependency Links:** WP-2.2 (work packet lifecycle), WP-2.4 (execution produces results to verify)

---

### WP-3.4: Projection Build Loop

**Objective:** Enable the operator to build EOS, CreatorOS, and LyfeOS projection apps from inside the UMH operating loop using work packets, governed execution, and verification.

**Affected Files/Modules:**
- `substrate/organism/work_packet_engine.py` (ensure projection awareness)
- `projections/` (read -- projection configs)
- `saas/` (read -- EOS projection)
- `scripts/check_dependency_direction.py` (enforces architecture layers)

**Required Context:**
- Architecture Layer Law: projections → transports → adapters → substrate (one-way)
- Work packets targeting saas/ or projections/ are projection-specific work
- Projection work should be classified MEDIUM+ risk (modifies user-facing code)
- check_dependency_direction.py blocks architecture violations
- Work packet routing must be projection-agnostic (not hardcoded to EOS)

**Acceptance Criteria:**
- Operator submits "build EOS feature X" → work packets generated targeting saas/
- Operator submits "build CreatorOS feature Y" → work packets generated targeting projections/creatoros/ or creatoros repo
- Work packets respect architecture layer law (verified by gate script)
- Projection work classified as MEDIUM+ risk with approval required
- Routing is projection-agnostic: same mechanism for EOS, CreatorOS, LyfeOS
- No projection-specific logic in substrate/ code

**Tests/Checks:**
- Unit test: work packet for EOS targets correct directory
- Unit test: work packet for CreatorOS targets correct directory
- Architecture test: generated packets pass dependency direction check
- Governance test: projection work requires approval
- Agnosticism test: routing logic contains no projection-specific branching

**Risk Level:** MEDIUM (enabling projection builds through governed loop)

**Approval Requirement:** YES -- projection code modification

**Rollback Expectation:** Disable projection awareness in routing; work packets still function for substrate work

**Dependency Links:** WP-3.1 (outcomes update model), WP-3.2 (self-improvement can target projections), WP-3.3 (verification catches violations)

---

## Summary

| Wave | Packet | Objective | Risk | Gap Type | Est. Complexity |
|------|--------|-----------|------|----------|----------------|
| 1 | WP-1.1 | Reality Model HTTP Routes | MEDIUM | WIRE | Low |
| 1 | WP-1.2 | Cockpit WorldModelPanel Wiring | MEDIUM | WIRE | Low |
| 1 | WP-1.3 | Memory Route Upgrade | MEDIUM | WIRE | Low |
| 1 | WP-1.4 | Execution Control Wiring | MEDIUM | WIRE | Medium |
| 2 | WP-2.1 | Intent Capture Pipeline | MEDIUM | WIRE | Medium |
| 2 | WP-2.2 | Work Packet Lifecycle | MEDIUM | WIRE+BUILD | Medium |
| 2 | WP-2.3 | Approval UI Wiring | MEDIUM | WIRE | Low |
| 2 | WP-2.4 | Agent/Tool Routing | MEDIUM | WIRE | Medium |
| 3 | WP-3.1 | Outcome → Reality Model | MEDIUM | WIRE | Low |
| 3 | WP-3.2 | Self-Improvement Cadence | LOW | WIRE | Low |
| 3 | WP-3.3 | Verification Pipeline | LOW | WIRE+EXTEND | Low |
| 3 | WP-3.4 | Projection Build Loop | MEDIUM | WIRE | Medium |

**Total: 12 work packets across 3 waves.**
- 9 WIRE (connecting existing production code)
- 2 WIRE+BUILD (partial new code needed)
- 1 WIRE+EXTEND (extending existing infrastructure)
- 0 BUILD (no major new engines from scratch)
