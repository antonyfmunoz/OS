# Type Divergence Debt Ledger — 2026-07-04 (WP-P2-001)

This ledger enumerates the **pre-existing** registered-name type-divergence sites
that exist on `main @ 566771265` when WP-P2-001 hardened the divergence gate.

These are accumulated technical debt from before the gate was made truthful.
WP-P2-001 does **not** converge them (that is follow-on work touching 40+ files
across every layer). Instead it makes them **visible, enumerated, and
non-expanding**:

- The gate's `--registry-audit` mode (new, fail-closed) enforces registry
  *truthfulness* (entries resolve, no duplicate keys, exemptions carry metadata
  and resolve) and is GREEN on this tree.
- The full-scan name-shadow count (`check_type_divergence.py --all`) is tracked
  by `tests/test_type_divergence.py::test_full_codebase_scan_no_growth`, which
  asserts the count does **not exceed** the baseline below. The baseline may
  only shrink — new divergence fails the test.

**Baseline divergence-site count: 40** (worktree full scan, corrected registry).

The gate's staged-scope pre-commit path already blocks any *new* divergence in
changed files. This ledger governs the *committed* backlog.

## Enumerated sites (type ← file)

| Type | File |
|---|---|
| ActionCategory | substrate/organism/maintenance_loop.py |
| ActionResult | substrate/organism/assisted_executor.py |
| AgentType | substrate/organism/template_registry.py |
| ArtifactType | substrate/organism/leverage_assimilation.py |
| CertificationReport | tests/certification/c28_certification.py |
| CoverageReport | substrate/composition/mastery/management/models.py |
| CoverageStatus | substrate/composition/mastery/management/models.py |
| DecisionRecord | substrate/intelligence/runtime.py |
| DependencyStrength | substrate/organism/dependency_graph.py |
| DimensionScore | substrate/organism/readiness_model.py |
| DimensionScore | substrate/organism/template_governance.py |
| ExecutionGraph | substrate/organism/plan_execution_adapter.py |
| ExecutionMode | substrate/execution/runtime/execution_contracts_v1.py |
| FileEntry | substrate/workstation/file_browser.py |
| GapEntry | substrate/organism/benchmarks/competitive.py |
| GapSeverity | substrate/organism/world_model.py |
| GapType | substrate/organism/qualification_harness.py |
| Goal | substrate/control_plane/goals/goal_selector.py |
| GovernanceDecision | substrate/organism/template_governance.py |
| HandoffStatus | substrate/organism/handoff.py |
| IntentClassification | substrate/organism/intent_classifier.py |
| IntentType | substrate/execution/runtime/execution_contracts_v1.py |
| IntentType | substrate/organism/operator_session.py |
| LineageNode | substrate/organism/source_truth_runtime.py |
| ProofPackage | substrate/organism/proof_store.py |
| RecoveryAction | substrate/execution/runtime/worker_supervisor_v1.py |
| RoutingDecision | substrate/execution/bridge/node_controller.py |
| RoutingResult | substrate/contracts/agent_types.py |
| RuntimeReadiness | substrate/execution/runtime/workpacket_execution_gate_v1.py |
| ServiceState | substrate/organism/audits/operational_awareness.py |
| SystemMode | substrate/organism/homeostasis.py |
| TaskResult | substrate/organism/benchmarks/external_adapters.py |
| TaskResult | tests/certification/c28_certification.py |
| TaskResult | tests/certification/c28_task_acceptance.py |
| TaskStatus | substrate/execution/bridge/task_system.py |
| TrustLevel | substrate/state/registries/skill_registry_v2.py |
| VoiceSessionStatus | substrate/execution/bridge/voice_session.py |
| WorkspaceSnapshot | substrate/organism/workspace_awareness.py |
| WorkstationProfile | substrate/workstation/state.py |
| WorkstationSession | substrate/execution/workers/workstation/workstation_contracts_v1.py |

## Convergence direction (future packets)

Each site should be converged by importing from the canonical location or, where
it is a legitimate homonym, adding a narrow `LEGACY_DUPLICATES_META` exemption
with owner/sunset/rationale. The unregistered homonyms (e.g. two `ApprovalStore`,
two `AgentStatus`) should be registered as homonyms or one converged away. This
backlog is out of scope for WP-P2-001 (gate hardening only).
