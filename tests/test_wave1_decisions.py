"""Wave 1 decision tests — 4-part decision_ref, HUD-only authority, acceptance ≠ execution.

Covers: test AG (typed Decision contract — first-class fields, identities,
plan_acceptance_only, metadata removal preserves semantics), test AB (plan
acceptance never authorizes execution; packets stay non-executable; drain
finds nothing), test H core (chat decision language surfaces the HUD item and
commits NOTHING), test AK decision side (atomic capture never creates a HUD
Decision; a plan creates one only after readiness), double-decision safety,
and the unified-approval objective_plan source (stable ids, no per-poll
minting).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.contracts.work_context import PrincipalContext, WorkScope
from substrate.execution.intent.context_frame import ContextFrame
from substrate.execution.intent.protocol import IntentClass, OperatorIntentProtocol
from substrate.execution.planning.decisions import (
    PLAN_APPROVED_STATUS_MESSAGE,
    ObjectivePlanDecisionSource,
    PlanDecisionConflict,
    apply_plan_decision,
    build_plan_approval_request,
    derive_decision_fields,
    plan_decision_ref,
)
from substrate.execution.planning.records import ObjectivePlanStatus
from substrate.execution.planning.store import PlanningStore
from substrate.organism.event_spine import EventSpine
from substrate.organism.strategic_gap_engine import GoalRegistry
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import PacketLifecycleStatus
from substrate.workstation.unified_approval_runtime import (
    ApprovalSourceType,
    UnifiedApprovalRuntime,
)

DOGFOOD_OBJECTIVE = (
    "Migrate the remaining nine legacy runtime subsystems under data/umh "
    "to the runtime-state boundary: heartbeats, queues, snapshots, journals, "
    "receipts, consent_grants, sessions, traces, approvals"
)


class Runner:
    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, mutation_name, intent, execute_fn, source="", metadata=None):
        self.calls.append(mutation_name)
        output, ok = execute_fn()
        return SimpleNamespace(success=ok, output=output, envelope_id="env-test")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir()
    store = PlanningStore(
        sessions_path=str(tmp_path / "p" / "sessions.jsonl"),
        plans_path=str(tmp_path / "p" / "plans.jsonl"),
        grounding_path=str(tmp_path / "p" / "grounding.jsonl"),
        current_path=str(tmp_path / "p" / "current.jsonl"),
        desired_path=str(tmp_path / "p" / "desired.jsonl"),
        gaps_path=str(tmp_path / "p" / "gaps.jsonl"),
    )
    goals = GoalRegistry(store_path=str(tmp_path / "goals.jsonl"))
    queue = UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))
    runner = Runner()
    protocol = OperatorIntentProtocol(
        store=store, goal_registry=goals, event_spine=EventSpine(), mutation_runner=runner
    )
    principal = PrincipalContext(
        principal_id="user-1", tenant_id="tenant-a", membership_id="mem-abc"
    )
    scope = WorkScope(tenant_id="tenant-a", conversation_id="conv-1", target_kind="umh_substrate")
    return SimpleNamespace(
        store=store,
        goals=goals,
        queue=queue,
        runner=runner,
        protocol=protocol,
        principal=principal,
        scope=scope,
    )


def _compiled_plan(env, cmid: str = "m1"):
    frame = ContextFrame(tenant_id="tenant-a", principal_id="user-1", conversation_id="conv-1")
    resolution = env.protocol.resolve(
        DOGFOOD_OBJECTIVE, env.principal, env.scope, frame, client_message_id=cmid
    )
    _, plan = env.protocol.plan_objective(
        resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id=cmid, work_queue=env.queue
    )
    return plan


# ── Test AG: typed Decision contract ─────────────────────────────────────────


class TestTypedDecisionContract:
    def test_first_class_fields_never_metadata_only(self, env):
        plan = _compiled_plan(env)
        approval = build_plan_approval_request(plan)
        assert approval.decision_ref == f"objective_plan:{plan.plan_record_id}:plan_acceptance:v1"
        assert approval.decision_kind == "plan_acceptance"
        assert approval.subject_type == "objective_plan"
        assert approval.subject_id == plan.plan_record_id
        assert approval.subject_version == "v1"
        assert approval.tenant_id == "tenant-a"
        assert approval.authorization_effect == "plan_acceptance_only"
        # Metadata removal preserves semantics — the typed fields carry them.
        approval.metadata = {}
        d = approval.to_dict()
        assert d["decision_ref"] and d["authorization_effect"] == "plan_acceptance_only"

    def test_decision_ref_stable_across_polls(self, env):
        plan = _compiled_plan(env)
        source = ObjectivePlanDecisionSource(store=env.store, mutation_runner=env.runner)
        first = source.pending_decisions()
        second = source.pending_decisions()
        assert first and second
        assert first[0].approval_id == second[0].approval_id == plan_decision_ref(plan)

    def test_legacy_adapter_fails_closed(self):
        from substrate.types import ApprovalRequest

        legacy = ApprovalRequest(title="old record")  # no typed fields
        derived = derive_decision_fields(legacy)
        assert derived["decision_ref"]  # deterministically derived
        assert derived["authorization_effect"] == "none_fail_closed"


# ── Test AB: plan acceptance ≠ execution authorization ───────────────────────


class TestAcceptanceNotExecution:
    def test_approval_flips_plan_only_packets_untouched(self, env):
        plan = _compiled_plan(env)
        packet_statuses_before = {
            pid: env.queue.get_packet(pid).status for pid in plan.workpacket_ids
        }
        decided = apply_plan_decision(
            env.store,
            plan.plan_record_id,
            "approve",
            decided_by="operator",
            mutation_runner=env.runner,
        )
        assert decided.status == ObjectivePlanStatus.APPROVED.value
        assert decided.decision_log[-1]["status_message"] == PLAN_APPROVED_STATUS_MESSAGE
        assert decided.decision_log[-1]["authorization_effect"] == "plan_acceptance_only"

        env.queue._load()  # re-read disk truth
        for pid in plan.workpacket_ids:
            packet = env.queue.get_packet(pid)
            assert packet.status == packet_statuses_before[pid] == PacketLifecycleStatus.PLANNED
            assert packet.approval_gates
            assert not packet.is_execution_ready()

    def test_drain_finds_nothing_executable(self, env):
        plan = _compiled_plan(env)
        apply_plan_decision(env.store, plan.plan_record_id, "approve", mutation_runner=env.runner)
        env.queue._load()
        # The orchestration drain only executes APPROVED/DELEGATED packets
        # (is_execution_ready). Zero such packets exist after plan acceptance.
        executable = [p for p in env.queue.all_packets() if p.is_execution_ready()]
        assert executable == []

    def test_double_decision_safe(self, env):
        plan = _compiled_plan(env)
        apply_plan_decision(env.store, plan.plan_record_id, "approve", mutation_runner=env.runner)
        # Same decision again → idempotent no-op.
        again = apply_plan_decision(
            env.store, plan.plan_record_id, "approve", mutation_runner=env.runner
        )
        assert again.status == ObjectivePlanStatus.APPROVED.value
        # Conflicting decision → explicit conflict, no silent flip.
        with pytest.raises(PlanDecisionConflict):
            apply_plan_decision(
                env.store, plan.plan_record_id, "reject", mutation_runner=env.runner
            )

    def test_stale_client_version_rejected(self, env):
        # Optimistic concurrency (adversarial-review fix): a decision made
        # against a stale view (older graph_version) is rejected explicitly.
        plan = _compiled_plan(env)
        with pytest.raises(PlanDecisionConflict, match="caller saw"):
            apply_plan_decision(
                env.store,
                plan.plan_record_id,
                "approve",
                mutation_runner=env.runner,
                expected_version=plan.graph_version + 1,
            )
        # Correct version proceeds.
        decided = apply_plan_decision(
            env.store,
            plan.plan_record_id,
            "approve",
            mutation_runner=env.runner,
            expected_version=plan.graph_version,
        )
        assert decided.status == ObjectivePlanStatus.APPROVED.value

    def test_cancel_preserves_record(self, env):
        plan = _compiled_plan(env)
        cancelled = apply_plan_decision(
            env.store, plan.plan_record_id, "cancel", mutation_runner=env.runner
        )
        assert cancelled.status == ObjectivePlanStatus.CANCELLED.value
        assert env.store.get_plan(plan.plan_record_id) is not None


# ── Test H core: chat decision language commits nothing ─────────────────────


class TestChatDecisionLanguage:
    def test_provide_decision_resolves_but_does_not_transition(self, env):
        plan = _compiled_plan(env)
        frame = ContextFrame(
            tenant_id="tenant-a",
            principal_id="user-1",
            conversation_id="conv-1",
            current_plans=[
                {
                    "plan_record_id": plan.plan_record_id,
                    "objective_id": plan.objective_id,
                    "objective_text": plan.objective_text,
                    "status": plan.status,
                    "graph_version": plan.graph_version,
                }
            ],
        )
        resolution = env.protocol.resolve(
            "Approve that plan.", env.principal, env.scope, frame, client_message_id="m2"
        )
        assert resolution.intent_class == IntentClass.PROVIDE_DECISION.value
        assert resolution.reference_resolution["selected"]["plan_record_id"] == plan.plan_record_id
        # The resolution itself changed NOTHING: plan still awaiting approval.
        on_disk = env.store.get_plan(plan.plan_record_id)
        assert on_disk.status == ObjectivePlanStatus.AWAITING_APPROVAL.value
        # Only the HUD decision path (apply_plan_decision) may transition it.


# ── Test AK: DecisionRequirement routing ─────────────────────────────────────


class TestDecisionRequirementRouting:
    def test_atomic_capture_creates_no_hud_decision(self, env):
        frame = ContextFrame(tenant_id="tenant-a", principal_id="user-1", conversation_id="conv-1")
        resolution = env.protocol.resolve(
            "Fix the failing import in transports/api/voice.py",
            env.principal,
            env.scope,
            frame,
            client_message_id="t1",
        )
        env.protocol.capture_task(
            resolution,
            "Fix the failing import in transports/api/voice.py",
            "conv-1",
            client_message_id="t1",
            work_queue=env.queue,
        )
        source = ObjectivePlanDecisionSource(store=env.store, mutation_runner=env.runner)
        assert source.pending_decisions() == []  # no approval fatigue

    def test_plan_creates_decision_only_when_ready(self, env):
        source = ObjectivePlanDecisionSource(store=env.store, mutation_runner=env.runner)
        assert source.pending_decisions() == []
        plan = _compiled_plan(env)
        rows = source.pending_decisions()
        assert len(rows) == 1
        assert rows[0].work_id == plan.plan_record_id
        assert rows[0].risk_class == "high"  # HUD top-slice guarantee
        assert rows[0].context["authorization_effect"] == "plan_acceptance_only"


# ── Unified approval integration (one decision path) ─────────────────────────


class TestUnifiedApprovalIntegration:
    def test_objective_plan_source_composes_and_routes(self, env):
        plan = _compiled_plan(env)
        source = ObjectivePlanDecisionSource(store=env.store, mutation_runner=env.runner)
        runtime = UnifiedApprovalRuntime(objective_plan=source)

        pending = runtime.pending(source_type=ApprovalSourceType.OBJECTIVE_PLAN.value)
        assert len(pending) == 1
        assert pending[0].approval_id == plan_decision_ref(plan)

        action = runtime.approve(
            pending[0].approval_id, ApprovalSourceType.OBJECTIVE_PLAN.value, "operator"
        )
        assert action.action == "approved"
        on_disk = env.store.get_plan(plan.plan_record_id)
        assert on_disk.status == ObjectivePlanStatus.APPROVED.value
        # After the decision, the pending row disappears.
        assert runtime.pending(source_type=ApprovalSourceType.OBJECTIVE_PLAN.value) == []

    def test_reject_routes_through_same_path(self, env):
        plan = _compiled_plan(env)
        source = ObjectivePlanDecisionSource(store=env.store, mutation_runner=env.runner)
        runtime = UnifiedApprovalRuntime(objective_plan=source)
        action = runtime.reject(
            plan_decision_ref(plan), ApprovalSourceType.OBJECTIVE_PLAN.value, "not now"
        )
        assert action.action == "rejected"
        assert env.store.get_plan(plan.plan_record_id).status == ObjectivePlanStatus.REJECTED.value
