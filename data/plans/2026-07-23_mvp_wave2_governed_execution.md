# MVP Wave 2 — Governed Composition, Placement, and Execution Slice (Plan)

STATUS: FINAL + AMENDED (v1) — audit + design complete; all load-bearing seams verified on the
af14fde tree. Owner amendment v1 folded in; proceeding through C1–C7.

## BINDING WAVE 2 AMENDMENT v1 (owner order — PRECEDENCE over any conflicting plan text below)

Extends rather than revokes. Where this section conflicts with older plan text, THIS WINS.

**1. Decision/authorization separation.** `ApprovalRequest` remains the sole Decision identity +
lifecycle authority (owns pending/approved/rejected). **RENAME `ExecutionAuthorizationRecord` →
`ExecutionAuthorizationGrant`.** The Grant exists ONLY as the bounded effect of an APPROVED
execution_authorization Decision. Grant states = ACTIVATING | ACTIVE | EXPIRED | REVOKED |
INVALIDATED | FAILED_ACTIVATION. **No REQUESTED or DENIED grant state.** Rejected execution
requests live only in canonical ApprovalRequest history — never as a grant record.

**2. Canonical Task activation = ONE recoverable idempotent operation.** Applying an approved
execution authorization: verify exact latest accepted ObjectivePlanRecord version → resolve exact
authorized WorkPacket set → create/reuse ONE Grant in ACTIVATING → close the named
`execution_authorization` gate on those Tasks → transition PLANNED Tasks → APPROVED through
canonical WorkPacket authority → emit one canonical event chain → mark grant ACTIVE only AFTER
every required Task transition commits. APPROVED→DELEGATED only after a valid assignment + env lease
exist. **Scheduler admission requires: Task APPROVED|DELEGATED AND grant ACTIVE AND deps
satisfied.** Partial failure never creates an ACTIVE grant. Retry resumes idempotently — no
duplicate grants/Tasks/attempts/events.

**3. Dispatch spool = ephemeral transport ONLY.** `ExecutionAttemptStore` remains the sole current
execution truth. Every dispatch envelope carries: dispatch_id, attempt_id, authorization_ref,
package_hash, lease_id, nonce, sequence, created_at, expires_at, payload_hash, HMAC. Atomic
inbox→inflight ownership, replay quarantine, idempotent result handling. **Spool loss must be
recoverable by reconstruction from canonical attempt state. No operator status inferred from file
presence.** The model worker subprocess receives NO dispatch/result signing secret.

**4. ENFORCED host isolation (blocks qualification).** Before field qualification, preflight and use
bubblewrap / hardened systemd transient unit / nsjail / equivalent verified host sandbox. The worker
MUST NOT read: /opt/OS; candidate runtime state; another run's files; SSH/1Password/GitHub/Fly/
Discord credentials; unrelated home-dir data. Expose ONLY: the assigned writable worktree,
run-specific temp storage, required read-only runtime files, the minimal model credential path.
Post-hoc diff validation is additional verification, NOT isolation. Network-destination isolation
may remain a stated nonclaim, but **filesystem, credential, workspace and git-remote boundaries must
be mechanically enforced** — without that proof, Session 1 = INSUFFICIENT_EVIDENCE.

**5. Spine authorization consumption.** MutationRequest/ActionEnvelope gain first-class:
authorization_ref, authorization_effect, authorized_subject_ids, authorized_scope_hash,
authorization_expires_at. GovernedExecutionSpine validates the ACTIVE grant before ANY Wave 2
action; every action must be a subset of the authorized Tasks/risk/Role/tools/environment/
external-effect scope. This is CONSUMPTION of explicit HUD authority, not auto-approval — reliability
fast paths and require_approval=False cannot bypass it. Out-of-scope or expired authority pauses
execution and requires a new Decision.

**6. Two Proof classifications under one canonical Proof authority.** `AttemptProof` — required for
each Task attempt to become SUCCEEDED; produced by a verifier actor/process DISTINCT from the
implementation worker; validates diff scope, commits, tests, package hash, artifact hashes, policy.
`PlanExecutionProof` — produced by the final independent verification Task; validates reconvergence,
complete tests, live HTTP/UI/browser behavior, source integrity, zero production deploy. **C unlocks
only after A and B each have successful AttemptProof; D only after C has AttemptProof; the Plan
execution outcome completes only after PlanExecutionProof.**

**7. Single-writer scheduler.** Acquire an interprocess scheduler lease keyed
tenant_id + plan_record_id + plan_version. Every pass rereads canonical state AFTER lock
acquisition. Attempt creation/transitions remain CAS-protected. Losing concurrent ticks mutate
nothing. HUD authorization commits and REQUESTS a scheduler pass; it does not synchronously wait for
long-running workers. Scheduler/poller/host attempt-runner are run-scoped Wave 2 components, NOT the
Wave 3 persistent supervisor.

**8. Cost truth.** Wave 2 enforces max_turns, timeout, attempt count, output bounds, parallelism,
CPU limits. Record `cost_usd` ONLY when trustworthy provider usage is available; otherwise
cost_usd=null, cost_status=unknown, budget_enforcement=time_turn_attempt. **Do not claim USD
enforcement.** A requested hard monetary ceiling BLOCKS readiness when it cannot be enforced.

**9. Additional required tests / matrix rows** (deterministic): ApprovalRequest sole execution
Decision owner; no requested/denied grant state; activation unit-of-work recovery after each
intermediate failure; WorkPacket execution-gate closure + PLANNED→APPROVED; grant ACTIVE only after
all packet transitions; spool replay/expiry/corruption/loss/reconstruction; host filesystem/
credential isolation; worker cannot read /opt/OS; ActionEnvelope scope-subset validation; expired/
revoked grant rejected inside the governed spine; per-Task AttemptProof vs final PlanExecutionProof;
fan-in requires predecessor AttemptProof; single-writer scheduler race; cost_status=unknown
truthfulness; /opt/OS main untouched by Wave 2 candidate qualification.

**10. Live checkout boundary.** Do NOT fast-forward, deploy, or modify /opt/OS main as part of Wave 2
implementation or qualification without a separate explicit owner order. (This SUPERSEDES the earlier
"fast-forward /opt/OS" operational note below — it is now a nonclaim, not a hygiene action.) The Wave
2 candidate remains commit-bound and isolated. The final PR must state that candidate qualification
does not update the live Cockpit.

Stop condition unchanged: do not merge; end exactly `AWAITING MERGE ORDER`.

---

STATUS (pre-amendment): FINAL — audit + design complete; all load-bearing seams verified on the af14fde tree.

## Context

Wave 1 (merged PR #312, `af14fde8a288`) delivered the governed PLANNING slice: conversational
intent → Objective (Goal/GoalRegistry) → Plan (ObjectivePlanRecord) → plan-acceptance Decision
(ApprovalRequest via UnifiedApprovalRuntime) → canonical Tasks (WorkPacket) → WorkGraph → Cockpit
(Chat, Top HUD, Work, Work Detail). A pinned invariant closes it: **plan acceptance grants ZERO
execution authority — zero ExecutionAttempts exist**. The chat rail literally answers "Execution
authorization is a separate decision that does not exist yet (Wave 2)."

Wave 2 builds the governed EXECUTION slice that this invariant was holding the door open for:
"Execute the approved plan" → execution-readiness → bounded execution-authorization Decision in the
HUD → deterministic composition/placement from canonical Tasks → parallel governed real execution
in isolated worktrees → independent verification → Outcome + Proof → same-thread report. The
outcome is a field-qualified vertical slice, NOT full MVP, NOT persistent supervision (Wave 3), NOT
production deployment, NOT merge.

The audit found the planning half coherent and canonical, and the execution half fragmented: FIVE
rival plan lineages, ZERO attempt records (the pinned invariant), THREE fake-success paths
reachable in production (SimulationExecutor registered for every executor type; PlanExecutionAdapter
`_default_execute`; GovernedWorkRuntime dispatch-only receipt), real workers that exist but are
unbound from dispatch (AgentExecutionRunner + git worktree + Claude CLI is the one proven real
path), and a `WorkcellDaemon.run` loop that is the only concurrency primitive but is disjoint from
the coordinator and has no approval gate. Wave 2 converges these onto one new canonical slice
(`substrate/execution/attempts/`) and makes every fake/auto/fallback path unreachable from the
qualified execution path — fail closed.

## VERIFIED load-bearing seams (Phase 3 checks, af14fde tree)

- ✅ Intent stub at `objective_plan_routes.py:288` (REQUEST_EXECUTION → the Wave-2 refusal string).
  `IntentClass.REQUEST_EXECUTION` + `_EXECUTE_RE` already classify "execute the plan".
- ✅ `ApprovalRequest` (substrate/types.py) has expires_at (L407), decision_kind (L433),
  authorization_effect (L441), and generic `build_decision_ref` (L503). expires_at is inert today
  → Wave 2 activates it.
- ✅ Instruction seam real: `compile_instruction_package` (L105), `ModelExecutionPackage` with
  package_hash sealing (L77–85), `InstructionCompilationError` (L32). Zero production callers →
  Wave 2 execution packages are the first (closes ledger #11).
- ✅ `cc_sdk.py:254` refuses to run inside containers (`/.dockerenv` or `$container`) — this is the
  fact that forces the VPS-host execution topology (workers cannot run in the candidate container).
- ✅ Field harness reusable: `/var/lib/umh/candidates/wave1/<sha>/state/umh`, mesh node
  `windows-desktop`, tailscale serve 8443 (10000 free for fixture), snapshot/restore.
- ✅ `SandboxManager(repo_root=, worktree_base=, store_dir=, max_parallel=2)` accepts exactly the
  parameters design B/A need to point real workers at the fixture repo.
- ⚠️ **CONFIRMED GAP (design A uncertainty #2 resolved):** `planning/compiler.py` materializes
  each WorkPacket (L386–414) but **never copies plan-node `depends_on` onto
  `WorkPacket.dependencies`** (field exists at work_packet.py:194, defaults empty). Plan nodes DO
  carry `depends_on` + `node_id`. Without the copy, the dependency-aware scheduler's "Task C
  blocked until A and B succeed" silently never blocks. **Wave 2 MUST patch the compiler** to map
  each node's `depends_on` (node_ids) to the corresponding materialized `packet_id`s on
  `packet.dependencies`. This is a small, contained, high-leverage change — do it in C1 and pin it
  with a test (a 3-node plan A,B,C where C depends_on [A,B] must yield packet C with 2 deps).

## Ground truth established so far

- Canonical base: `af14fde8a288274e3c377420d7491b88dc633806` == `origin/main` HEAD (verified).
- `/opt/OS` local main checkout is STALE at the Wave 0 merge (6952687) — missing all 89 Wave 1
  files (~18k lines). The live runtime is therefore running pre-Wave-1 code. Wave 2 work must NOT
  read /opt/OS as ground truth; the wave1 worktree tree (52059a1aa) is byte-identical to af14fde.
- Wave 2 worktree to create: `/opt/OS/.claude/worktrees/OS-mvp-wave2-governed-execution`,
  branch `feat/mvp-wave2-governed-execution`, based on af14fde8a288 (fetched; present locally).
- Operational note: /opt/OS main is stale at Wave 0 (6952687). **Per amendment clause 10, DO NOT
  fast-forward/deploy/modify /opt/OS as part of Wave 2** — the candidate is commit-bound + isolated;
  worker cannot touch /opt/OS (clause 4). Live-checkout state is an owner decision outside this wave.

## Audit outputs (all three complete; findings in the Audit sections below)

1. ✅ Substrate execution machinery census — COMPLETE (findings below).
2. ✅ Wave 1 seam map — COMPLETE (findings below).
3. ✅ Repo-wide collision census — COMPLETE (findings below).

## Audit 3 — Repo-wide census (rivals, workers, scheduler, tests, gates)

### Plan lineages (5 + canonical; adjudication targets)
- `ExecutionPlan` (substrate/types.py:520, canonical Pydantic type, embedded in WorkPacket flows)
- `CoordinatorExecutionPlan` (execution_coordinator.py:144; PlanStore JSON files) — LIVE via
  GovernedWorkRuntime, execcoord_routes.py, action_bridge.py:408
- `ExecutablePlan` (plan_execution_adapter.py:168; in-memory) — LIVE via daemon.py:336,
  organism_bridge.py:784+, trial_runner.py
- `CompositionPlan` (composition_engine.py:150; hardcoded JSONL) — LIVE via
  cockpit_spine_router.py:700, organism_bridge.py:743+
- `AgentExecutionPlan` (agent_execution_runner.py:31) — LIVE via cockpit_operator_loop_routes.py:651
- `ObjectivePlanRecord` — Wave 1 canonical (the only operator Plan)
- NOTE: `ExecutionGraph` defined TWICE — plan_execution_adapter.py:263 vs execution_graph.py:186
  (different abstractions; adjudicate naming in ledger).

### Attempt-adjacent types
- `ExecutionReceipt` (governed_work_runtime.py:65) — dispatch record only, status defaults
  "dispatched", never carries real output.
- `ExecutionRecord` (agent_execution_runner.py:49) — immutable real-run record from the ONE real
  agent path; closest existing shape to an attempt, adapt/reference in ExecutionAttempt design.

### Fake-success paths reachable in production (must be unreachable from qualified path)
1. SimulationExecutor registered for ALL ExecutorTypes (executor_runtime.py:391, 412, 470–473).
2. PlanExecutionAdapter._default_execute (plan_execution_adapter.py:411–412).
3. GovernedWorkRuntime.execute_work returns ExecutionReceipt("dispatched") — mark_started/
   mark_completed (coordinator :978/:997) are manual transitions nothing calls in normal path.
4. cockpit_work_center_routes.py:114 default target_executor="simulation" (valid set
   {simulation,workstation,agent}).

### Real worker reality (what Wave 2 binds to dispatch)
- `AgentExecutionRunner` (agent_execution_runner.py:99): REAL — creates git worktree sandbox
  (worktree_sandbox.py, git worktree add @296), runs Claude Code CLI via gated_subprocess_run
  (`claude --print --permission-mode auto --max-turns 30` @291), captures diffs/commits @383,
  validates @430. Sole production caller: cockpit_operator_loop_routes.py:275.
- `AgentExecutor(ExecutorContract)` (executors/agent_executor.py:388): REAL — rejects repo root,
  requires worktree, risk always high; NOT registered in ExecutorImplementationRegistry (orphaned).
- `WorkPacketExecutor` + build_default_executor (substrate/execution/executor.py:48/177): REAL
  shell/filesystem/git/tmux adapters; used by organism_loop @248.
- Runtime adapter fleet (runtime_adapters.py): CCSDKAdapter(:29), CodexAdapter(:75),
  HermesAdapter, OpenCodeAdapter, GeminiAdapter, OllamaAdapter, DockerAdapter(:359),
  TmuxAdapter(:434), MeshNodeRuntimeAdapter(:511, governed HTTP relay :8095),
  BeastNodeAdapter(:601, Tailscale SSH). All real, CPU-gated, bound to Workcell via bind_adapter
  (workcell_protocol.py:171); prod instantiation mesh_reconciler.py:178, transports/api/app.py:234/247.
- `ClaudeCodeRuntimeAdapter` (claude_code_pty): CONFIRMED STUB (start() always started=False).
- Mesh: NodeMeshServer (transports/node_mesh/server.py, WS+HMAC), NodeTransportServer
  (execution/bridge/node_transport.py), mesh_dispatch_port (fail-closed without
  UMH_MESH_VERDICT_SECRET/UMH_MESH_RELAY_SECRET), browser_evidence_collector (real).
- Two-concurrent-workers gap: nothing binds real adapters to two parallel worktree-isolated
  workers; coordinator dispatch terminates at SimulationExecutor.

### Scheduler reality
- EXISTS: WorkGraph.executable_work() @406 ready frontier; WorkReadinessRuntime.ready_work @529 /
  next_unblockable @550; WorkcellDaemon.run @121 (max_concurrency @187, backoff, stale recovery)
  — the ONE capacity-aware loop, disjoint from coordinator; ExecutablePlan.ready_steps() @183
  (per-plan frontier with BLOCKED_BY_FAILURE propagation); coordinator PriorityQueue
  enqueue_plan @927 / dispatch_next @953.
- MISSING: cross-plan fan-out/fan-in; capacity/retry policy on coordinator; binding of
  WorkGraph/readiness frontier to real dispatch; attempt ledger to drive retries.

### Second-WorkPacket creators (census for "no new packet from raw intent" gate)
- Canonical factory: work_packet_engine.create_packet_from_intent (:76).
- Rivals: universal_work_queue.py:101/125/146/168; work_packet_engine.py:242/265 (parent/child);
  planning/compiler.py:385; execution/pipeline.py:341; intent/protocol.py:1065;
  transports/discord/interface_adapter_v1.py:182; transports/api/signal_router.py:163.
- submit_work callers: cockpit_work_center_routes.py:121, operator_loop_runtime.py:267,
  governed_work_runtime.py:453 (retry).

### Auto-approve census (full)
- coordinator GovernanceGate.auto_approve_eligible :603 (low/negligible);
  ExecutorGovernanceGate :738 (risk ≤ low); governed_work_runtime :282–284 (auto-policy);
  governed_spine fast path :190–193 (reliability>0.95, veto via block_auto_approval);
  agent_registry.can_auto_execute :30 (7 of 11 True); ApprovalState alias "auto_approved"
  (types.py:339, coordinator :853).

### Tests that pin invariants Wave 2 must deliberately lift or extend
- test_single_spine_architecture.py @93–99: routing guard consulted before dispatch_next reaches
  executor.
- test_wave1_matrix_completion.py:475 + wave1 field collector/matrix: "zero ExecutionAttempts",
  "drain executes nothing", "plan acceptance ≠ execution authority". Wave 2 keeps the
  acceptance≠execution rows and replaces zero-attempt rows with authorized-attempt rows.
- Other execution tests: test_execution_coordinator (dispatch_next @586–995),
  test_gate3_governed_work_runtime (submit_work @480–1039), test_agent_fleet_runtime
  (can_auto_execute fixture @48), test_plan_execution_adapter (auto_approve fixture @98),
  test_gate4_workstation_convergence, test_execution_fabric_runtime.

### Pre-commit gates constraining Wave 2 (14 active)
type_divergence, instance_leak, projection_leak, dependency_direction, cpu_gate (gated
subprocess only), ungoverned_mutations (all mutations via governed_mutation), credential_injection,
secret_patterns, mesh_relay_firewall, pytest_collection, ontology_layers,
projection_registry_reads, ontology_homes, voice_runtime_divergence. Plus CI-side:
operator_language (shrink-only), runtime_state_boundary (Gate 15 — runtime_state_path usage).

## Audit 2 — Wave 1 seams (extension points, all verified on af14fde tree)

### Intent seam (the entry point of the whole slice)
- `substrate/execution/intent/protocol.py`: `OperatorIntentProtocol` (L282), `IntentResolution`
  (L153), classifier `_classify` (L438). **`IntentClass.REQUEST_EXECUTION` already exists**
  (enum L77, matched at L471 via `_EXECUTE_RE`).
- Chat rail: `transports/api/objective_plan_routes.py::try_chat_planning_rail` (L76), invoked by
  `cockpit_chat_routes.py`. The REQUEST_EXECUTION branch (objective_plan_routes.py L288–294) is a
  stub refusal: "Execution authorization is a separate decision that does not exist yet (Wave 2)."
  → Wave 2 replaces exactly this stub: resolve accepted plan version → readiness assessment →
  emit execution-authorization Decision → HUD focus card → same-thread reporting. No classifier
  changes needed.

### Plan resolution
- `ObjectivePlanRecord` (records.py): plan_record_id `opr-*`, objective_id `goal-*`,
  status machine DRAFT/AWAITING_APPROVAL/APPROVED/REJECTED/CANCELLED/SUPERSEDED, immutable
  versions with supersedes chain. Store: `PlanningStore` JSONL at
  runtime-state `operator/objective_planning/objective_plans.jsonl`, fcntl lock +
  CAS (`update_plan_cas` L288, `append_revision_cas` L322). Accepted version via
  `latest_version_of()`/`versions_of()`.

### Decision seam
- `substrate/types.py::ApprovalRequest` (L369) already has typed decision fields (L432–441):
  decision_ref, decision_kind, subject_type/id/version, tenant/principal/membership, scope_ref,
  authorization_effect. `expires_at` (L407) exists but is INERT — Wave 2 implements expiry +
  revocation.
- `build_decision_ref` (L503) generic 4-part format `source_type:source_record_id:decision_kind:vN`.
- Only decision_kind today: `plan_acceptance` (authorization_effect `plan_acceptance_only`),
  applied via `planning/decisions.py::apply_plan_decision` (idempotent repeat = no-op; conflict
  raises PlanDecisionConflict; expected_version optimistic concurrency).
- HUD: `UnifiedApprovalRuntime` + `ApprovalSourceType.OBJECTIVE_PLAN` (L41) +
  `ObjectivePlanDecisionSource` auto-composition (L279–290), approve/reject routes L518/L573.
  → Wave 2 adds `ApprovalSourceType.EXECUTION_AUTH` + `ExecutionAuthorizationDecisionSource`
  mirroring the plan source, decision_kind `execution_authorization`, authorization_effect
  `execute_bounded_task_set`, plus expiry/revocation logic.

### Instruction compilation seam (zero callers — deliberate, ledger #11)
- `substrate/execution/planning/instruction_compilation.py`: `InstructionCompilationRequest`
  (L37) → `compile_instruction_package` (L105) → `ModelExecutionPackage` (L58) with
  `package_hash` sha256[:32] sealing operation_identity/governance_constraints/
  verification_requirements. Failure raises InstructionCompilationError → blocks dispatch.
  → Wave 2 execution packages are the first production consumer (extend, don't duplicate).

### EventSpine
- `EventDomain.EXECUTION` already exists (event_spine.py L49). Shared persisted spine
  `get_shared_event_spine()` → runtime-state `events/organism_events.jsonl`. Wave 1 planning
  emits `planning.*` events with correlation chain conversation_id → message_id → intent_id →
  ... → plan_record_id → workpacket_ids → approval_request_ids. Wave 2 extends the same chain
  with `execution.*` events on the shared spine.

### Cockpit surface reality
- Panel registry `cockpit/src/renderer/panels/registry.ts`: CANONICAL_PANEL_IDS includes
  `execution`; aliases already map `runtime→execution`. Execution-family components in
  PanelWindowContent.tsx: ExecutionPanel (`/execution/*`), UnifiedExecutionPanel
  (`/unified-execution/*`), RuntimePanel (`/organism/runtime-surface/*`), ExecutorPanel
  (`/agents/executions`, `/runtime/state`), DistributedRuntimePanel
  (`/organism/distributed-runtime/*`). No AgentFleet panel (routes exist unwired:
  cockpit_agent_fleet_routes.py `/fleet/*`).
  → Wave 2 converges on canonical `execution` panel; aliases `unifiedexecution/executor/
  distributedruntime→execution` after absorbing distinct diagnostics or proving equivalence.
- ControlPanel.tsx (Top HUD) + stores/unifiedApprovalStore.ts (`/unified-approval/by-urgency`,
  approve/reject). objective_plan rows have wg-approve-btn/wg-reject-btn testids — Wave 2 adds
  execution_authorization rendering + w2-execution-decision testid.
- WorkDetailPanel + objectivePlanStore (`/objective-plan/*`); WorkPanel
  (`/command-center/work-packets`); UniversalWorkPanel (`/organism/universal-work/packets`).
- Chat: PlanSummaryCard has no decision buttons (S3 RESOLVED) — Wave 2 execution cards follow
  the same pattern (status + Open Execution/Open Task + Proof link, no authorize buttons).

### Field qualification harness (reuse wholesale)
- `scripts/wave1_field_dispatch.py`: preflight/deploy-candidate/smoke/run/reconcile/teardown;
  candidate stack os-operator-candidate + os-nginx-candidate; Tailscale serve :8443 with
  snapshot/restore; governed mesh dispatch to windows-desktop executor; reconciliation vs
  candidate state + docker logs. Candidate state at /var/lib/umh/candidates/wave1/<sha>/state/umh.
- `scripts/wave1_field_collector.py`: executor-side, real visible Chrome (channel="chrome",
  headless=False), 21-step journey, per-stage screenshots/DOM/network, run-tag anchoring.
- `scripts/wave1_matrix_report.py`: 41-row A–AO matrix generator (template for Wave 2 matrix).
- `infra/candidate/make_candidate_env.py` + nginx.candidate.conf.template.
  → Wave 2 creates wave2_* variants extending the journey with the 30-step §XIV field protocol
  and /var/lib/umh/candidates/wave2/<sha>/targets/<run-id>/ for fixture targets.

### Docs to update
- `docs/cockpit-surface-convergence.md` = the convergence ledger (#1–11 + S1–S6; status vocab
  ACTIVE_DEBT/ADJUDICATED/RESOLVED).
- `docs/LEXICON.md`: Execution row already reserved = "ExecutionAttempt (Wave 2+; ZERO in
  Wave 1)"; post-approval status line "PLAN APPROVED — EXECUTION NOT STARTED". Wave 2 adds
  execution vocabulary + authorized/executing/verified status lines.
- Matrix/report template: `data/audits/2026-07-23_wave1_matrix_report_qualified.md`.

## Audit 1 — Substrate execution machinery (af14fde tree)

### Collision census (adjudication input)

- **Plan rivals (4):** `CoordinatorExecutionPlan` (execution_coordinator.py; persisted
  `runtime_state_dir("execution_coordinator")/plans/*.json`), `CompositionPlan`
  (composition_engine.py; HARDCODED `data/umh/composition/plans.jsonl`), `ExecutablePlan`/
  `ExecutionGraph` (plan_execution_adapter.py; in-memory), vs canonical `ObjectivePlanRecord`
  (execution/planning/records.py). Ruling per directive: first three become internal
  compatibility/composition representations or retire.
- **Attempt: GREEN FIELD.** No `ExecutionAttempt`/`AttemptRecord` type exists — only Wave-2
  forward references in docstrings (mutation_registry.py:629, planning/readiness.py:157,
  planning/decisions.py:125). `ExecutionReceipt` (governed_work_runtime.py:65) is a transient
  return shape, never persisted. `RuntimeExecutionResult`/`SpineExecutionResult` are result
  shapes. Wave 2 mints canonical `ExecutionAttempt`.
- **Assignment rivals (3), none durable:** `FleetAssignment` (agent_fleet_runtime.py:79,
  in-memory only; only `FleetDispatch` persists to `runtime_state_dir("fleet")/dispatches.jsonl`),
  `RoutingDecision` (compute_fabric_runtime.py:86, ephemeral), `EnvironmentSelection`
  (execution/runtime/execution_contracts_v1.py:282, typed but unwired). Wave 2 promotes
  FleetAssignment to durable canonical placement record enriched with Role/Skill/model/harness/
  env/verifier + rationale (per §IV.3).
- **Environment lease: GREEN FIELD.** No lease type exists. Nearest: `RuntimeSession`/
  `RuntimeSessionRegistry` (runtime_session_registry_v1.py:35, in-memory), plus REAL worktree
  sandbox machinery in `substrate/meta_ide/engineering_session_coordinator.py`
  (_create_sandbox_worktree:420, _cleanup_sandbox_worktree:451), `organism/worktree_sandbox.py`,
  `organism/sandbox_orchestrator.py`, `organism/workload_placement_policy.py`. Wave 2 creates
  `ExecutionEnvironmentLease` (narrow, per §IV.4), reusing worktree_sandbox mechanics.
- **Approval:** canonical = `substrate.types.ApprovalRequest` + `UnifiedApprovalRuntime` (HUD
  queue) + Wave-1 `ObjectivePlanDecisionSource` pattern (planning/decisions.py,
  `apply_plan_decision` = plan_acceptance_only). Legacy rivals: `CoordinatorApprovalState`,
  `ExecutorApprovalState`, `ApprovalPolicyRegistry`. Wave 2 adds decision_kind
  `execution_authorization` via a new decision source modeled on OBJECTIVE_PLAN source.
- **Events:** canonical = shared persisted EventSpine (`get_shared_event_spine()` →
  `runtime_state_path("events","organism_events.jsonl")`, Wave 1 §22.6). `ExecutionJournal` stays
  canonical for per-envelope phases. Coordinator `LifecycleEvent` JSONL = legacy, no new writes.
- **Executor definition rivals (3):** coordinator `ExecutorDefinition/ExecutorRegistry`
  (metadata), `ExecutorContract`+`SimulationExecutor`+`ExecutorImplementationRegistry`
  (executor_runtime.py — simulation pre-registered for ALL types at line 470), real Wave-1
  `execution/runtime` stack (executor.py, live_local_runtime_execution_v1.py) + workcell
  `RuntimeAdapter`. Wave 2 converges on ExecutorContract seam with real adapters; simulation
  executor must be unreachable from the qualified path.

### Fake/auto-approve/fallback paths to close (fail-closed per §V)

1. `governed_work_runtime.submit_work` default `target_executor="simulation"` (line 230); same
   default in `operator_loop_runtime.py:258`.
2. `SimulationExecutor` pre-registered for all executor types (executor_runtime.py:470).
3. `plan_execution_adapter._default_execute` fake success stub (line 411).
4. `execution_coordinator` auto-approves low/negligible plans (lines 563/603/840).
5. `governed_work_runtime` auto-approve via ApprovalPolicyRegistry (`approved_by="auto-policy"`,
   lines 282–284).
6. `governed_spine.submit` `approved_by="auto_governance"` when require_approval=False (line 280)
   + reliability fast-path skipping manual_approval_check (lines 164–195, driven by
   outcome_learning auto_approve_candidate reliability>0.95).
7. `execute_work` legacy fallback to `ExecutionCoordinator.dispatch_next()` when
   `canonical_runtime_routing_enabled()` is False OR no injected router (lines 397–406) —
   flag is OFF by default and daemon.py never injects a MutationRouter (only
   transports/api/governed.py:60 builds one). Wave 2: new execution path must fail closed, never
   fall back to coordinator dispatch.
8. `WorkcellDaemon.run` (workcell_daemon.py:121) + `Workcell.process_next`
   (workcell_protocol.py:267) — autonomous inbox execution with no per-message approval gate.
   Stays compatibility-only per §V.7; must not be Wave 2 supervisor.
9. `mutation_router.route_mutation_degraded` (line 306) — fail-closed by design (low risk/local/
   opted-in only); acceptable, not a hole.

### Hardcoded-path cleanup targets (migrate touched ones to runtime_state_path)

- composition_engine.py:440 (`data/umh/composition/plans.jsonl`)
- agent_capability_model.py:130 (`data/umh/agents/*.jsonl`)
- governed_execution_runtime.py:682 (workstation_state/latest_checkpoint.json)
- outcome_learning.py:30 (`_REPO_ROOT` non-signal-feed stores)
- compute_fabric_runtime.py:441 (relative `data/runtime/mesh_nodes.json`)

### Latent bugs found (fix in Wave 2 where touched)

- `execution_fabric_runtime.py:279–291` calls nonexistent methods
  (`list_plans_by_status`/`pending_approval_count`/`get_all_nodes`) — silently returns empties
  via `_safe_call`. Real names: `plans_by_status`/`awaiting_approval`/`nodes`.
- `compute_fabric_runtime._risk_acceptable` (line 426) always returns True — placement risk
  gating is a no-op today.

### Wiring reality

- daemon.py (live wiring, 19 service/transport imports): builds MutationRegistry (276),
  GovernedExecutionSpine (305, governed_spine.py — note file is governed_spine.py, NOT
  governed_execution_spine.py), WorkloadRunner, AssistedExecutor, PlanExecutionAdapter (~323),
  WorkcellDaemonV2 (351). Does NOT build MutationRouter; canonical path live only via
  transports/api/governed.py:60.
- Wave-1 real execution stack (substrate/execution/runtime/*) is imported by 8 service/transport
  files but NOT connected to governed-work dispatch — the parallel stack Wave 2 converges.
- Wave-1 planning path is live and clean: objective_plan_routes.py, cockpit_intent_loop_routes,
  intent/loop.py via route_mutation_degraded; planning/store.py →
  runtime_state_path("planning", ...). Plan acceptance provably grants zero execution authority.
- Role/skill seam already exists on RoleContract (Wave 1 §7 fields: required_skill_refs,
  permitted/prohibited_skill_ids, skill_mastery_requirements, separation_of_duty_rules).
- WorkPacket already carries typed work_scope/lineage/requirements (Wave 1 §4);
  `is_execution_ready()` gates APPROVED/DELEGATED + no blockers.

## Design B — Real execution + field qualification (COMPLETE)

### Execution topology (adjudicated)
- **Workers run ON THE VPS HOST** as a run-scoped Attempt Runner (`scripts/wave2_attempt_runner.py`)
  started/stopped by the field dispatcher. Deciding facts (verified in tree): `cc_sdk.py:254`
  fail-closes inside containers (/.dockerenv check) and OAuth injection walks the HOST process
  tree; candidate container has no claude binary/credentials; make_candidate_env.py deny-list
  (MESH/SSH/PRIVATE) correctly blocks what a container worker would need; 0.25–0.35 CPU caps make
  30–90s CLI runs pathological. Beast rejected for workers (60s mesh command timeouts, unproven
  worktrees+CLI on Windows, couples failure domains) — Beast keeps ONE job: visible-Chrome fixture
  probe. Runner is run-scoped, honest about no restart recovery (Wave 3 boundary).
- **Control-plane→worker seam = fail-closed signed dispatch spool** on the shared state mount
  (`state/umh/execution/dispatch/{inbox,inflight,processed,outbox}`, workcell_protocol
  atomic-rename FILE PATTERN only — not WorkcellDaemon). Dispatch file: attempt_id, task_id,
  plan_record_id, run_id, authorization_decision_ref, instruction package + hash, lease_id,
  allowlists, budgets, HMAC-SHA256 with per-run `UMH_W2_DISPATCH_SECRET`. Unsigned → quarantined.
  Runner verifies signature+decision ref+package hash → creates lease worktree → runs worker →
  outbox. Candidate-side poller consumes outbox, advances attempts + WorkGraph frontier, emits
  next dispatches (C after A∧B verified; D after C). SimulationExecutor unreachable: runner only
  binds the real CLI path and refuses unsigned/unauthorized dispatches.
- **Worker invocation:** refactored `AgentExecutionRunner.execute()` with
  `SandboxManager(repo_root=<fixture>, worktree_base=<targets>/<run>/leases, ...)` (constructor
  already accepts these; change = thread repo_root through instead of _repo_root()).
  `claude --print --output-format text --max-turns 30 --permission-mode auto` via
  gated_subprocess_run(timeout=600, cwd=<lease worktree>, env=allowlisted-minimal:
  PATH/HOME/CLAUDE_CODE_OAUTH_TOKEN via cc_sdk._get_subprocess_env()/GIT_*/FIXTURE_VENV; deny
  UMH_MESH_*/DISCORD_*/FLY_*/GITHUB_*/OP_*). Max 2 concurrent implementation workers; C and D
  run alone. cpu_gate block → attempt `blocked_cpu` requeue w/ backoff (max 5), not failed.
- **Artifacts per attempt** → `targets/<run>/artifacts/<attempt-id>/`: worker_stdout.txt,
  diff.patch, commits.txt, validation.json, assignment.json (role/adapter/package_hash/
  session-isolation proof), env_audit.json (names only); sha256 each recorded on the attempt.
  Candidate reads artifacts via read-only mount for Work Detail + Proof.
- Worker independence recorded (no provider-generality claim): adapter `cc_cli_worktree` for all
  four; fresh process per attempt (no --resume), separate worktrees/packages/hashes, distinct
  Roles: role-implementer-backend / role-implementer-frontend / role-integrator / role-verifier.

### Fixture app (targets/<run-id>/fixture/)
- **FastAPI + static vanilla JS + pytest/httpx. Zero npm.** One uvicorn serves API+frontend;
  pinned wheels installed once per candidate into shared `fixture-venv`. Generator:
  `infra/fixture/make_fixture_app.py --dest ... --variant clean|tools-revoked-A` (git init, one
  base commit, prints fixture_base_sha; spec-only — NEVER contains the solution patch).
- Tree: app/main.py (GET/POST /api/notes, /health, StaticFiles), app/store.py (JSON NoteStore),
  app/static/{index.html (data-testid="note-list"), app.js}, tests/{test_api.py,
  test_ui_served.py} green at base, seed/notes.json (6 deterministic notes), requirements.txt
  (pinned), OBJECTIVE.md (exact API contract quoted into A/B packages).
- Seeded objective: "Add note search: backend search endpoint + frontend search box, integrated
  and verified."
- **Task A** (backend): GET /api/notes/search?q= case-insensitive over title+body,
  {"query","results"}, 400 on empty q; tests/test_search_api.py. Accept: ≥1 commit; diff confined
  to app/main.py, app/store.py, tests/test_search_api.py; full pytest green in A's worktree.
- **Task B** (frontend, written against OBJECTIVE.md contract, not A's code): note-search-input +
  note-search-results testids in index.html + fetch logic in app.js; tests/test_ui_search.py
  asserts served HTML contains both testids (independent of A). Accept: diff confined to
  app/static/*, tests/test_ui_search.py; base+B tests green.
- **Task C** (integration, dep A∧B verified): fresh lease worktree, git merge attempt/<A> +
  attempt/<B> into integration/<run-id>, resolve conflicts, FULL suite green, merge commit with
  both branches as ancestors; then RUNNER (mechanical) launches preview: gated_popen uvicorn
  127.0.0.1:8377 + /health check.
- **Task D** (verification, dep C): see verifier below.
- Reset: each pass = new targets/<run-id>/ (never reset in place); prior run dirs retained as
  hashed evidence, gitignored by location.

### Environment lease
- `ExecutionEnvironmentLease` persisted at state/umh/execution/leases.jsonl: lease_id,
  attempt_id, task_id, run_id, worktree_path, branch attempt/<task>-<attempt-id>, base_commit,
  allowed/denied paths, env_allowlist_names, tool_policy, timestamps, status. Creation = git
  worktree add via SandboxManager; release = worktree remove --force, branch retained till
  teardown.
- **Honest enforcement split** (recorded on lease as enforced vs declared): ENFORCED — worker env
  allowlist, post-hoc diff-scope validation (attempt FAILS if diff touches outside
  allowed_paths), cwd confinement + no remote (cannot push), tool revocation via
  --disallowedTools. DECLARED-ONLY — full filesystem namespace confinement, network egress.
  No false isolation claims in Proof.
- Cleanup: teardown asserts `git worktree list` only main tree, preview pid killed, spool
  drained. Source integrity: candidate source mounted :ro + before/after rev-parse +
  status --porcelain empty + /opt/OS HEAD unchanged → source_integrity.json.

### Verifier (Task D)
- role-verifier RoleContract with separation_of_duty_rules excluding A/B/C authors; independent
  instruction package sealing verification_requirements; D runs with
  --disallowedTools "Edit,Write,MultiEdit,NotebookEdit" in a fresh read-intent worktree at the
  integration commit; post-hoc: D's diff must be empty.
- D independently runs: full pytest from scratch; HTTP checks vs LIVE preview (search JSON shape,
  HTML testids, ?q= → 400); diff/ancestry inspection; triggers browser evidence layer.
- Browser evidence: runner mesh-dispatches `scripts/wave2_fixture_browser_probe.py` to
  windows-desktop (wave1 detached Start-Process + op run + status.json polling). Session-1 proof
  first, then real visible Chrome navigates fixture origin, types "alpha", waits on
  /api/notes/search response, screenshots+DOM+console+network. SSH fallback prohibited.
- Fixture reachability for Beast: `tailscale serve --bg --https=10000 http://127.0.0.1:8377`
  wired at C-verified time (8443 stays cockpit candidate); extend snapshot/restore to :10000;
  preflight Beast→fixture-origin curl.
- Proof: ExecutionProof → state/umh/execution/proofs.jsonl {proof_id, attempt_id(D),
  plan_record_id, run_id, verdict, checks[{kind: pytest|http|diff|browser, ok, evidence_ref,
  sha256}], browser_evidence, integration_commit, fixture_base_sha}. Task completion is
  Proof-gated in the control-plane outbox poller, never runner discretion.

### Field harness (wave2 forks; wave1 stays frozen)
- `wave2_field_dispatch.py`: preflight | deploy-candidate | seed-fixture | start-runner | smoke |
  run | inject-failure | reconcile | teardown. deploy-candidate adds targets dir + fixture-venv
  build + `-v targets:/targets:ro` + UMH_W2_DISPATCH_SECRET (run-scoped, added to candidate env
  allowlist).
- `inject-failure` (before green passes): --variant tools-revoked-A — attempt A1 dispatched with
  Edit/Write revoked → real worker genuinely cannot commit → validation genuinely fails → C stays
  blocked, no Proof, HUD shows FailureReport → collector drives retry from UI (w2-execution-retry)
  → A2 minted without revocation → succeeds → graph continues. (Alt variant poisoned-store
  documented.)
- `reconcile`: wave1 formula (≥0.90, zero orphan 5xx) + Wave 2 predicates: exactly-2 concurrency
  overlap (max(started) < min(completed) for A/B), zero attempts started before authorization
  decided_at, zero duplicate active attempts per task, C.started > max(A,B verified), exact
  commit binding (attempt head == artifacts == merge parents), Proof-before-completion, zero
  unredacted secrets in evidence, source integrity, sandboxes cleaned, zero production deploy
  (no FLY_/GH_ key in any env audit).
- `wave2_field_collector.py`: 30-step journey w01–w30 (Session-1 proof; zero attempts; plan via
  Wave 1 rail; HUD plan approve; "Execute the approved plan"; prove no execution pre-HUD; HUD
  execution decision approve; A+B running concurrently (two w2-attempt-row[data-status=running]);
  C blocked→starts after both; preview live; D distinct role; browser probe; collector's own
  visible-Chrome fixture witness (types "alpha", sees results); Proof link; completion only
  after Proof; same-thread w2-report-msg; Work Detail lineage; refresh + Chrome restart
  persistence; zero-deploy/source-unchanged/cleanup proofs; Tailscale restore).
- Bar: smoke + failure-qualification + 3 consecutive green passes; heavy evidence gitignored +
  sha256 manifest; `wave2_matrix_report.py` cloned from wave1 exact-node-mapping pattern.

### Top risks + mitigations (from design B)
1. CLI auth/quota exhaustion → preflight smoke, budget caps, honest FailureReport, stagger.
2. Agent nondeterminism misses contract → OBJECTIVE.md seals exact contract into packages;
   retry-as-new-attempt is the designed path; one retry doesn't fail a pass.
3. CPU gate blocks → deploy completes before start-runner; blocked_cpu ≠ failed; cap 2.
4. :10000 serve/cert issues for Beast → wave1 cert-probe lessons, readiness waits, preflight curl.
5. Cross-pass bleed → per-pass fresh targets, teardown asserts, per-run secret rotation.

## Design A — Backend execution contracts (COMPLETE)

### Home + import law
- New canonical slice: **`substrate/execution/attempts/`** (sibling of planning/; same layer, same
  store pattern). Rejected `substrate/execution/runtime/` (unconverged rival stack) and
  `substrate/organism/` (fake-success territory).
- Hard import law (test-enforced, tests/test_wave2_convergence_gates.py): attempts/* NEVER imports
  execution_coordinator, executor_runtime (SimulationExecutor home), plan_execution_adapter,
  composition_engine, governed_work_runtime. MAY import planning/records|store|decisions,
  substrate.types, contracts.work_context, work_packet, role_contracts, agent_fleet_runtime,
  worktree_sandbox, event_spine, mutation_router, cpu_gate, credential_gate,
  planning.instruction_compilation.

### New modules
- `attempts/records.py`: `ExecutionAttempt` (identity fields attempt_id, task_id, objective_id,
  plan_record_id, plan_version, execution_authorization_ref, attempt_number, tenant/principal/
  membership_id, correlation_id; bindings assignment_id/lease_id/instruction_package_hash/
  worker_identity/verifier_*; result proof_id/files_changed/commits/cost; record_version CAS
  counter; transitions[] append-only). `AttemptTransition`. `ExecutionAttemptStatus`
  (created/ready/leased/dispatched/running/verifying/succeeded/failed/blocked/cancelled/
  rolled_back). `ExecutionAuthorizationRecord` (decision_ref, plan bound, bounds: task_frontier,
  max_attempts_per_task, risk_ceiling, role_ids, environment_classes, allowed_tools,
  credential_scope_refs (names only), not_before/expires_at LIVE, cost_limit_usd,
  verification/rollback_obligations, decision_log, record_version). `ExecutionAuthorizationStatus`
  (requested/granted/denied/expired/revoked/invalidated).
- `attempts/store.py`: `ExecutionAttemptStore` mirrors PlanningStore (fcntl, atomic rewrite,
  monkeypatch seam) at subsystem `operator/execution_attempts` (Gate 15 clean). Files:
  execution_attempts.jsonl, execution_authorizations.jsonl, readiness_assessments.jsonl,
  environment_leases.jsonl. **CAS lives in `transition_cas`** (single lifecycle write path:
  record_version + expected_statuses check → validate against TRANSITIONS → append transition →
  apply binding updates (identity fields immutable) → bump version → atomic rewrite).
  `create_attempt_idempotent` keyed (task_id, authorization_ref, attempt_number) → duplicate
  returns existing.
- `attempts/lifecycle.py`: TRANSITIONS table + guards. Load-bearing guards: ready→leased requires
  assignment_id + readiness AUTHORIZED; leased→dispatched requires package hash + lease ACTIVE +
  authorization re-validated at that instant; verifying→succeeded requires proof_id AND
  verifier_identity != worker_identity AND actor startswith "verifier:" (agent can never complete
  own task). Retry = NEW attempt, never a re-transition.
- `attempts/decisions.py`: execution-authorization authority mirroring planning/decisions.py.
  `execution_decision_ref` binds exact plan version by construction. `request_execution_authorization`
  (fail closed: plan APPROVED + latest + readiness pre-pass). `build_execution_approval_request`
  → ApprovalRequest(decision_kind=execution_authorization, effect=execute_bounded_task_set,
  risk HIGH, expires_at LIVE). `apply_execution_decision` (approve re-checks latest+approved+
  not-expired; the ONLY callers are UnifiedApprovalRuntime + HUD route — no policy/auto path).
  `is_authorization_valid`, `sweep_expired_authorizations`. `ExecutionAuthorizationDecisionSource`
  (UnifiedApproval source; approve() triggers ONE bounded scheduler pass).
- `attempts/readiness.py`: **NEW `ExecutionReadinessAssessment`** (ruled: do NOT retrofit organism
  WorkReadinessRuntime.ReadinessAssessment — it's a legacy read-surface over coordinator stores).
  9 states (not_required/investigating/blocked/authorization_required/ready/authorized/expired/
  prohibited/failed). 15 deterministic fail-closed checks (§VI): plan_accepted_exact_version,
  task_canonical_not_terminal, dependencies_satisfied (dep has SUCCEEDED attempt w/ proof),
  authorization_valid, tenant_match (→PROHIBITED), work_scope_complete, role_resolved,
  skills_role_authorized, tools_permitted, adapter_exists (real, never sim/pty stub),
  capacity_available, credentials_by_reference (names only), sandbox_rollback_defined,
  verifier_and_proof_contract, cost_bounded.
- `attempts/leases.py`: `ExecutionEnvironmentLease` (green field, narrow) + `LeaseManager`
  (acquire refuses if any ACTIVE lease for task_id — one active lease per task; SandboxManager
  worktree; guards worktree_path != repo root and not inside /opt/OS main; snapshot_ref =
  base_commit; heartbeat/release/revoke(always executable)/expire_stale).
- `attempts/placement.py`: `place_attempt` deterministic pipeline (role→skills→workers by
  AgentType-as-capability-class→model/harness/tool→compute node stable sort (headroom desc,
  node_id asc)→environment→verifier role distinct from worker). Records deterministic_scores +
  rejection_reasons; persisted via governed execution_placement_record.
- `attempts/dispatch.py`: `AttemptDispatcher.compile_package` (FIRST production consumer of
  compile_instruction_package; failure → BLOCKED, never dispatch). `dispatch` resolves REAL worker
  from harness_profile (claude_code_cli → worker_claude_cli.run_in_lease via gated_subprocess_run,
  scrubbed env, no /opt/OS cwd); NO fallback (unresolvable → BLOCKED("no_real_adapter"));
  SimulationExecutor not importable.
- `attempts/verification.py`: `verify_attempt` independent re-run + proof_generator; transition
  guard enforces verifier≠worker + proof present.
- `attempts/scheduler.py`: `AttemptScheduler.run_scheduler_pass` — bounded session-local (NOT a
  daemon). One pass: sweep expiry/stale + REVOKED cascade → frontier (dep truth = attempt ledger;
  chain/fan-out/fan-in/independent lanes) → failure propagation (max attempts → packet failed →
  dependents BLOCKED) → bounded retries (new attempt, linked) → admission (< max_concurrency=2:
  place→lease→leased CAS→compile→dispatched CAS(re-validate auth)→dispatch) → reconvergence.
  Invoked by: authorization approve, verify completion, POST /execution/scheduler/tick.
- `attempts/events.py`: `emit_execution_event` on the ONE shared EventSpine (EventDomain.EXECUTION);
  never raises; no new JSONL authority.

### Modified modules
- `objective_plan_routes.py` L288–294: REQUEST_EXECUTION stub → resolve accepted plan → readiness
  → request_execution_authorization → "decision surfaced in control panel" (chat NEVER authorizes).
  New read routes in `transports/api/execution_attempt_routes.py` (thin adapter, module-scope
  Pydantic models per PEP-563 lesson).
- `unified_approval_runtime.py`: ApprovalSourceType.EXECUTION_AUTH + auto-composed
  ExecutionAuthorizationDecisionSource; pending()/_route_approve/_route_reject branches. (cockpit
  unified_approval routes need ZERO changes — dispatch on source_type.)
- `mutation_registry.py`: new specs — execution_authorization_request (low/degraded-ok),
  execution_authorization_decision (HIGH/NO degraded/NO auto-approve — fail closed when control
  plane down), execution_authorization_revoke (always executable), execution_attempt_create
  (medium), execution_attempt_transition (medium), execution_placement_record (low),
  execution_lease_mutate (medium), execution_lease_revoke (always), execution_attempt_dispatch
  (high, PROCESS, 600s; grant IS the approval).
- `canonical_types.py`: register all new attempt types + promote FleetAssignment/AssignmentRationale.
- `governed_work_runtime.py`: submit_work drops target_executor="simulation" default (required
  param; explicit sim rejected unless UMH_ALLOW_SIMULATION_EXECUTOR=1); refuse raw-intent canonical
  submissions. execute_work: remove coordinator fallback → fail-closed rejected receipt when no
  canonical router; reject Wave-1-lineage packets → route via attempts. Mirror default fix at
  operator_loop_runtime.py:258, cockpit_work_center_routes.py:114.
- `agent_fleet_runtime.py`: FleetAssignment promotion (task_id, attempt_id, role_contract_id,
  skill_requirement_refs, worker_identity, model/harness/tool_profile, environment_lease_id,
  verifier_role_id, deterministic_scores, rejection_reasons; all defaulted). AssignmentStore
  (runtime_state_path fleet/assignments.jsonl). Deterministic assign() (stable sorts, no dict
  nondeterminism). can_auto_execute recorded as capability datum only, never execution authority.
- `plan_execution_adapter.py`: DELETE _default_execute; _build_envelope raises when no executor
  bound (fake success prohibited); compat banner.
- `composition_engine.py`: persist_plan → runtime_state_path; CompositionAuthorityError when
  intent maps to an APPROVED/AWAITING plan (can never re-plan accepted plan); compat banner.
- `execution_coordinator.py`: auto_approve_eligible returns False for plan_record_id/
  execution_authorization_ref lineage; compat banner (no new writes from canonical path).

### Legacy adjudication (ruling → enforcement)
- CoordinatorExecutionPlan/CompositionPlan/ExecutablePlan+local ExecutionGraph → COMPAT
  (import-law test + source-literal gates for _default_execute, data/umh/composition,
  target_executor="simulation").
- AgentExecutionPlan/ExecutionRecord → ADAPT (runner mechanics lifted into worker_claude_cli.py).
- ExecutionReceipt → RETIRE from canonical path. FleetAssignment → PROMOTE. RoutingDecision/
  EnvironmentSelection → RETIRE (unwired). organism ReadinessAssessment → COMPAT read-surface.
  Coordinator LifecycleEvent JSONL → RETIRE (no new writes; all events on shared spine).
  SimulationExecutor → COMPAT, unreachable from qualified path. WorkcellDaemon → COMPAT, NOT the
  Wave-2 supervisor.

### Tests that break → update
- test_single_spine_architecture.py @80–99: rewrite to assert guard + no dispatch_next in
  execute_work + add fail-closed-without-router test.
- test_wave1_matrix_completion.py:475: KEEP acceptance≠execution rows (plan approval still = zero
  attempts); replace global zero-attempt assertion with "zero before authorization, ≥1 with valid
  auth_ref after grant"; drain-executes-nothing → drain-executes-only-authorized-frontier.
- test_gate3_governed_work_runtime.py: fixtures set UMH_ALLOW_SIMULATION_EXECUTOR=1 + explicit
  executor; fallback expectations → rejected receipts.
- test_execution_coordinator.py: add plan_record_id-never-auto-approve case.
- test_agent_fleet_runtime.py: update FleetAssignment dict fixtures; add determinism + persistence
  tests.
- test_plan_execution_adapter.py: inject executors; add no-executor-raises test.
- New suites: test_execution_attempts_store, test_execution_authorization, test_execution_readiness,
  test_attempt_scheduler, test_wave2_convergence_gates, test_environment_lease.

### Design A open uncertainties (VERIFY at implementation start — some checked below)
1. Degraded-mode grant tension: execution_authorization_decision is HIGH/no-degraded, so
   authorization needs the daemon UP — Wave-2 field harness must run with candidate stack up
   (Wave-1 exercised degraded plan decisions).
2. Dependency truth: does planning/compiler.py:385 copy ObjectivePlanNode.depends_on into
   WorkPacket.dependencies? Scheduler assumes populated packet.dependencies. → VERIFY.
3. Verifier identity: no primitive distinguishes verifier vs worker principals; Wave 2 enforces at
   ledger/lifecycle level (RoleContract separation + recorded identities); independent verifier
   PROCESS is Wave-3 hardening.
4. Cost accounting: Claude CLI cost-output parsing format unverified; timeout+turn budgets enforce
   boundedness regardless; unparseable-cost-with-limit ruling needs owner decision.
5. Two concurrent real workers never run before; SandboxManager max_parallel=2 × CPU gate
   interaction unknown until field pass.
6. UnifiedApprovalRuntime constructed at multiple transports; audit call sites for positional-arg
   shadowing of new execution_auth param.

## Design C — Surface convergence + acceptance matrix (COMPLETE)

### Panel convergence
- Canonical `execution` panel stays; ADD aliases in registry.ts: unifiedexecution/executor/
  distributedruntime/agentfleet → execution (runtime→execution already exists). REMOVE those
  entries from PanelWindowContent.tsx PANEL_COMPONENTS so no rival panel is reachable by id.
- Retired panels (UnifiedExecutionPanel, RuntimePanel, ExecutorPanel, DistributedRuntimePanel)
  become non-executable redirect stubs (wave-1 pattern, surfaceAuthority-pinned). Their materially
  distinct diagnostics move as EXTRACTED components (provably equivalent — same JSX + routes) to
  components/execution/{WorkersTopology.tsx (from DistributedRuntime; w2-worker-status),
  RuntimeSessions.tsx (from Runtime; stop gated), ExecutionDiagnostics.tsx (from Executor;
  raw fetch()→fetchApi)}. Clean PanelType union (cockpitStore), viewContextStore labels,
  routes.ts sidebar entries in the same commit.
- Backend route disposition: /unified-execution/* GETs stay as diagnostic reads but POST
  approve/reject REFUSED ("decisions HUD-only"); /execution/* legacy GETs stay, POST
  approvals REFUSED; /organism/runtime-surface/* and /organism/distributed-runtime/* stay as THE
  canonical worker/device read contract (Workers tab reads distributed-runtime directly — no
  second read contract minted); /fleet/* GETs stay, POST assign/dispatch/wave fail-closed behind
  a decision_ref resolving to ACTIVE execution_authorization. ExecCoordPanel = ledger ACTIVE_DEBT,
  not converged this wave (keeps wave bounded).

### New/changed API + frontend
- `transports/api/execution_attempt_routes.py` (thin adapter, /execution prefix): GET
  /execution/attempts, /attempts/{id} (full detail: assignment, lease, phase_history, blockers,
  artifacts, verification, proof, retry_lineage, cancel/retry_allowed), /attempts/{id}/events,
  /frontier (authorized frontier ∩ WorkGraph.executable_work), /authorizations, /by-plan/{id},
  /overlay?packet_ids=. POST /attempts/{id}/cancel + /retry (governed, fail-closed). Tenant
  filtering mirrors objective_plan_routes _tenant_visible.
- Execution decisions through EXISTING /unified-approval/approve|reject (source_type
  execution_auth); pending item context.details carries full package for HUD render.
- New frontend: `stores/executionAttemptStore.ts` (Zustand; hydrate from /execution/* GETs;
  cancel/retry POST then canonical refetch only; POST echo never trusted; NO localStorage —
  persistence-by-refetch). `panels/ExecutionPanel.tsx` rewrite (root w2-execution-root; tabs
  Attempts/Frontier/Workers/Environments/Diagnostics/History; AttemptRow w2-execution-attempt;
  AttemptDrawer w2-assignment/w2-environment-lease/w2-verification-status/w2-proof-link/
  w2-execution-cancel/w2-execution-retry). ControlPanel.tsx exec rows w2-execution-decision +
  ExecutionDecisionPackage.tsx (full package); KEEP wg-approve/reject-btn plan-conditional —
  exec rows use w2-exec-approve/reject-btn so wave-1 anchors untouched. ChatExecutionCard.tsx
  (mirror PlanSummaryCard; status line, progress, Open Execution/Open Task, Proof link;
  ZERO authorize controls). WorkPanel overlay chips (attempt count/state/role/blocker/proof) +
  remove Overnight inline Approve. WorkDetailPanel Plan|Execution mode toggle (fetchByPlan,
  reuses AttemptRow/AttemptDrawer).

### Acceptance matrix (~53 rows, `scripts/wave2_matrix_report.py` cloned from wave1)
- A Ownership/convergence (6): A1 one attempt type; A2 legacy plan rivals zero new writes; A3
  FleetAssignment sole durable placement; A4 one lease type; A5 panel family converges (vitest);
  A6 legacy execution stores zero new writes.
- B Authorization (7): B1 chat mints decision runs nothing; B2 bounded task set only; B3 duplicate
  idempotent; B4 reject zero attempts; B5 expired blocks; B6 revocation removes frontier; B7 plan
  acceptance zero execution authority.
- C Canonical attempts (6): C1 attempt only from authorized frontier; C2 immutable/append-only;
  C3 cancel not delete; C4 retry new lineage + budget; C5 persist across restart; C6 no attempt
  from raw intent.
- D Dependencies (4): D1 blocked yields no attempt; D2 completion unlocks; D3 failure propagates;
  D4 fan-in waits all.
- E Role/skill/placement (5): E1 records role+skills+worker+model+harness+tools+rationale; E2
  prohibited/unauthorized skill rejected; E3 capability+capacity; E4 SoD verifier≠executor; E5
  durable across restart.
- F Environment (4): F1 lease per attempt worktree-isolated; F2 released on terminal; F3 repo-root
  rejected; F4 two concurrent distinct worktrees no collision.
- G Instructions (3): G1 dispatch consumes compile_instruction_package (ledger #11 closes); G2
  package_hash sealed tamper→blocked; G3 compilation failure blocks fail-closed.
- H Real execution (5): H1 SimulationExecutor unreachable; H2 real artifacts (diff/commit) (+field);
  H3 sim default rejected; H4 subprocess only via gated; H5 coordinator fallback unreachable.
- I Attribution/proof (4): I1 one correlation chain; I2 verification before proof; I3 proof linked
  + readable chat/overlay/drawer (+field); I4 execution.* on shared spine + restart reconstructs.
- J Surfaces (6, vitest+route): J1 chat no authorize; J2 decisions HUD-only + refused POSTs; J3
  alias resolution + non-executable stubs; J4 all 10 w2-* testids present; J5 persistence-by-
  refetch/POST echo never truth; J6 operator-language gate green with new surfaces.
- K Wave boundary (3): K1 no autonomous scheduling beyond authorized set; K2 chat can't start
  execution directly; K3 legacy write isolation (WorkcellDaemon/organism loop not supervisor).
- wave2_matrix_report.py generalizes vitest handling (per-file pass/fail, fixes wave1 all-or-
  nothing); field rows FIELD_PENDING→FIELD_QUALIFIED; PASS only when every mapped node passes.

### Vitest surface-authority extension
- executionSurfaceAuthority.test.tsx (no-authorize-in-chat, HUD-only decision testids, alias
  resolution, retired stubs non-executable, all 10 testids at mapped files, no localStorage).
- executionAttemptStore.test.ts (refetch-after-mutate, POST echo never truth, reread failure
  surfaces, 409 structural). Update surfaceAuthority.test.tsx file lists.

### LEXICON + ledger updates
- LEXICON Execution row → live ExecutionAttempt; new Layer-1 rows Assignment/Environment/Worker/
  Blocker/Verification/Model/Harness/Tool; new status lines (EXECUTION AUTHORIZED — NOT STARTED /
  RUNNING / BLOCKED — DECISION NEEDED / COMPLETE — PROOF ATTACHED / FAILED — RETRY AVAILABLE /
  CANCELLED). Layer-2 banned additions: ExecutionAttempt, FleetAssignment, Workcell,
  SimulationExecutor, dispatch. check_operator_language.py TOUCHED_SURFACES += new surfaces.
- Ledger: S7 panel convergence, S8 rival decision writes refused, S9 unifiedExecutionStore + raw
  fetch retired, S10 ungoverned execution entries removed + /fleet POST fail-closed, #12 legacy
  execution stores zero new writes, #13 ExecutionGraph double-def naming ruling, #11 update
  instruction_compilation gets first caller → RESOLVED.

### Design C surface risks (folded into implementation notes)
- Convert panels + tests in the SAME commit (retired-stub test fails until conversion).
- Keep wg-approve/reject-btn plan-conditional; exec uses w2-exec-* (wave-1 harness anchor safety).
- ControlPanel already in operator-language baseline — new HUD strings must be Layer-1; drop
  "spine"/"packets"/"Governed Execution Spine" wording in rewritten ExecutionPanel.
- executionSummaryStore HUD counters not converged — field-journey check HUD counter reconciles
  with attempt ledger (ledger note).
- RuntimeSessions stop button = execution-affecting POST on diagnostic tab → gate to authorized
  attempts or ungoverned_mutations gate flags it.

## Implementation sequence (C1–C7 — no opaque mega-commit; every commit passes its targeted tests)

Worktree: `/opt/OS/.claude/worktrees/OS-mvp-wave2-governed-execution`, branch
`feat/mvp-wave2-governed-execution`, based on `af14fde8a288`. (This session already runs in the
wave1 worktree, byte-identical to af14fde; create the wave2 worktree at execution start.)

**C1 — Ownership + convergence spine.** Authoritative plan doc
`data/plans/2026-07-23_mvp_wave2_governed_execution.md` (this plan, committed in-tree). Create
`substrate/execution/attempts/{records,store,lifecycle,events}.py` (ExecutionAttempt,
ExecutionAuthorizationRecord, transition table, CAS store, shared-spine emitter). Register in
canonical_types.py. **Patch compiler.py to copy depends_on → packet.dependencies** (+ test).
mutation_registry.py new specs. Import-law + source-literal convergence gate
(tests/test_wave2_convergence_gates.py). No-fake / no-fallback edits to governed_work_runtime,
plan_execution_adapter, composition_engine, execution_coordinator (fail closed). Tests:
test_execution_attempts_store, test_wave2_convergence_gates; fix test_single_spine_architecture,
test_gate3, test_plan_execution_adapter.

**C2 — Readiness + authorization.** attempts/readiness.py (ExecutionReadinessAssessment, 15
checks), attempts/decisions.py (request/apply/validate/sweep + ExecutionAuthorizationDecisionSource),
expiry/revocation activated, plan-revision invalidation. UnifiedApprovalRuntime EXECUTION_AUTH
source. objective_plan_routes.py L288 stub → live request (chat→HUD focus, never authorizes).
Tests: test_execution_authorization, test_execution_readiness; rescope wave1 zero-attempt rows.

**C3 — Composition + placement + lease + instructions.** attempts/placement.py (deterministic,
FleetAssignment promotion + AssignmentStore), attempts/leases.py (ExecutionEnvironmentLease +
LeaseManager over worktree_sandbox), attempts/dispatch.py compile_package (first
compile_instruction_package consumer). Tests: test_wave2_assignment_placement,
test_environment_lease; fix test_agent_fleet_runtime.

**C4 — Scheduler + real attempts.** attempts/scheduler.py (bounded pass: frontier/fan-out/fan-in/
retry/propagation/exactly-once CAS), attempts/dispatch.py dispatch + attempts/worker_claude_cli.py
(real Claude CLI in lease via gated_subprocess_run, no fallback). scripts/wave2_attempt_runner.py
(host runner over signed spool). Tests: test_attempt_scheduler (chain/fan-out/fan-in/retry/
exactly-once under simulated concurrent pass).

**C5 — Verification + Outcome + Proof.** attempts/verification.py (independent verifier, verifier≠
worker guard, proof_generator), Proof-gated completion in the outbox poller, same-thread execution
report turns (execution_status metadata). Tests: test_wave2_attribution_proof,
test_wave2_instruction_execution.

**C6 — Surface convergence.** registry.ts aliases + PanelWindowContent removals; retired panels →
stubs; extracted WorkersTopology/RuntimeSessions/ExecutionDiagnostics; executionAttemptStore;
ExecutionPanel rewrite (6 tabs, 10 testids); ControlPanel execution decision + ExecutionDecisionPackage;
ChatExecutionCard; WorkPanel overlay; WorkDetail Execution mode; execution_attempt_routes.py read
surface + governed cancel/retry; refuse rival decision POSTs; /fleet POST fail-closed. LEXICON +
operator-language TOUCHED_SURFACES + ledger entries. Tests: executionSurfaceAuthority.test.tsx,
executionAttemptStore.test.ts, update surfaceAuthority.test.tsx; vitest + npm build green.

**C7 — Qualification.** scripts/wave2_matrix_report.py (~53 rows A–K, exact node mapping);
infra/fixture/make_fixture_app.py; scripts/wave2_field_dispatch.py + wave2_field_collector.py +
wave2_fixture_browser_probe.py; candidate compose fixture-target mounts; pre-commit gates green;
adversarial divergence review (§XVI checklist); candidate deploy; ONE failure-qualification pass;
smoke; THREE consecutive green Session-1 passes (reconciliation ≥0.90); proof manifest;
ready-for-review PR. Any candidate-affecting change → requalify from pass 1.

## Adversarial blockers (§XVI — every answer must be NO before qualification)

Second Task/Plan/Decision/approval/event owner? Wave 2 create a WorkPacket from raw intent? Plan
acceptance trigger execution? Chat authorize execution? Execution bypass HUD? Canonical routing
fall back silently? Fake/default executor in qualified path? Agent mark own task complete? Task
complete without independent Proof? Duplicate request create a second active attempt? Stale plan
version execute? Unauthorized placement deviation continue? Role use unauthorized Skill/Tool? Task
identity bound to a worker/model/device/worktree? One tenant reach another's attempt/environment?
Worker access /opt/OS main or production secrets? Two parallel workers write the same workspace?
Dependent Task start before predecessors verified? Execution lifecycle only in process memory?
CoordinatorApprovalState / legacy lifecycle events still current truth? WorkcellDaemon claimed as
persistent supervision? Active restart recovery claimed? Production deployed? Wave 3 smuggled in?
Later waves need to REPLACE rather than extend these records? — Any YES blocks unless documented as
bounded compatibility debt with no current authority, explicit adapter boundary, retirement owner,
retirement wave.

## PR + stop condition (§XVII)

Ready-for-review PR "MVP Wave 2: governed composition, placement, parallel execution, and proof".
Body: authoritative base af14fde8a288 + final head; ownership adjudication; canonical contracts;
convergence changes; deterministic matrix; placements used; failure qualification; three Session-1
pass IDs; reconciliation scores; Proof manifest; source/target isolation evidence; review findings
+ resolutions; explicit nonclaims; production deployment status NOT PERFORMED. Do NOT merge.
Final permitted claim: QUALIFIED GOVERNED COMPOSITION AND EXECUTION SLICE. End state:
WAVE 0 CLOSED / WAVE 1 CLOSED / WAVE 2 DETERMINISTIC + SESSION-1 FIELD + REVIEW CLOSURE OPERATIONAL
/ PRODUCTION DEPLOYMENT NOT PERFORMED / MERGE NOT PERFORMED / WAVE 3 NOT STARTED. → AWAITING MERGE
ORDER.

## Verification (how the slice is proven end-to-end)

1. **Unit/contract (pytest):** the C1–C7 suites above + fixes to the six impacted wave1 tests.
   Every new store write goes through governed_mutation (ungoverned_mutations gate); every new
   store uses runtime_state_path (Gate 15); type coherence (canonical_types) and import-law
   (test_wave2_convergence_gates) green.
2. **Surface (vitest):** executionSurfaceAuthority + executionAttemptStore + updated
   surfaceAuthority; `npm run build` in cockpit/ green.
3. **Deterministic matrix:** `python3 scripts/wave2_matrix_report.py` → all ~53 rows PASS on the
   final head (field rows FIELD_QUALIFIED after passes).
4. **Field qualification (Session 1, real):** candidate deploy from commit-bound copy; ONE
   failure-qualification pass (injected genuine worker failure → C stays blocked, no false Proof,
   retry → new attempt → graph continues); smoke; THREE consecutive green passes via
   wave2_field_dispatch/collector with visible Chrome on windows-desktop; reconciliation ≥0.90;
   zero orphan 5xx; zero duplicate active attempts; exact commit binding; source_integrity
   unchanged; sandboxes cleaned; Tailscale restored; zero production deploy.
5. **Wall metric:** the §I scenario succeeds against the deployed candidate — "Execute the approved
   plan" → HUD decision → two concurrent real worktree workers (A backend, B frontend) → C
   reconverges only after both verified → D independently verifies incl. real-Chrome fixture check
   → Proof → same-thread report → survives refresh + Chrome restart.

### Operational note (amended — clause 10)
`/opt/OS` main is stale at Wave 0 (6952687). **Wave 2 does NOT fast-forward, deploy, or modify
/opt/OS** (amendment clause 10). Field passes deploy from commit-bound candidate copies only; the
worker is mechanically barred from /opt/OS (clause 4). Whether/when to update the live checkout is a
separate explicit owner order, outside this wave. The final PR states candidate qualification does
not update the live Cockpit.

## Amendment v1 — where each clause lands in C1–C7

- **C1:** rename `ExecutionAuthorizationRecord` → `ExecutionAuthorizationGrant`; grant states
  ACTIVATING/ACTIVE/EXPIRED/REVOKED/INVALIDATED/FAILED_ACTIVATION (no REQUESTED/DENIED — clause 1).
  ActionEnvelope/MutationRequest gain authorization_ref/effect/authorized_subject_ids/
  authorized_scope_hash/authorization_expires_at fields (clause 5). cost_usd/cost_status/
  budget_enforcement fields on attempt (clause 8). Convergence gate test + canonical_types register
  the renamed grant.
- **C2:** activation unit-of-work (clause 2) — apply-authorization is ONE idempotent recoverable op
  (verify version → resolve packet set → Grant ACTIVATING → close execution_authorization gate →
  PLANNED→APPROVED via WorkPacket authority → one event chain → Grant ACTIVE only after all Task
  transitions commit; partial failure → FAILED_ACTIVATION, never ACTIVE). ApprovalRequest stays the
  only Decision (rejected requests never become grants). Readiness blocks on unenforceable USD
  ceiling (clause 8).
- **C3:** spool envelope full field set + no signing secret to worker (clause 3). Placement records
  authorized_scope_hash for spine subset checks (clause 5).
- **C4:** single-writer scheduler lease keyed tenant+plan+version, reread-after-lock, losing ticks
  no-op (clause 7). Admission gate = APPROVED|DELEGATED AND grant ACTIVE AND deps satisfied
  (clause 2). Spool = ephemeral transport; ExecutionAttemptStore sole truth; spool loss recoverable
  by reconstruction; no status from file presence (clause 3). GovernedExecutionSpine consumes the
  ACTIVE grant and validates scope-subset before every action; fast-paths/require_approval=False
  cannot bypass; out-of-scope/expired → pause + new Decision (clause 5).
- **C5:** two Proof classes under one authority — AttemptProof (verifier≠worker) gates each
  attempt SUCCEEDED; PlanExecutionProof from the final verification Task gates Plan outcome; C after
  A∧B AttemptProof, D after C AttemptProof, outcome after PlanExecutionProof (clause 6).
- **C7:** ENFORCED host isolation (bubblewrap/systemd-transient/nsjail) preflighted + used, worker
  barred from /opt/OS/candidate-state/other-runs/all credentials — without mechanical proof Session 1
  = INSUFFICIENT_EVIDENCE (clause 4). New matrix rows for every clause-9 item. /opt/OS untouched
  (clause 10).
