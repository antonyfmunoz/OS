"""Wave 1 matrix extras — tests M (capability generality), Q core (tenant
isolation of identical names), and AI (event-lineage durability across
restart on ONE shared persisted spine).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.contracts.work_context import PrincipalContext, WorkScope
from substrate.execution.intent.context_frame import ContextFrame
from substrate.execution.intent.protocol import (
    IntentClass,
    OperatorIntentProtocol,
    planning_operation_key,
)
from substrate.execution.planning.store import PlanningStore
from substrate.organism.event_spine import (
    EventSpine,
    get_shared_event_spine,
    reset_shared_event_spine,
)
from substrate.organism.strategic_gap_engine import GoalRegistry
from substrate.organism.universal_work_queue import UniversalWorkQueue


class Runner:
    def __call__(self, mutation_name, intent, execute_fn, source="", metadata=None):
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
    protocol = OperatorIntentProtocol(
        store=store, goal_registry=goals, event_spine=EventSpine(), mutation_runner=Runner()
    )
    return SimpleNamespace(store=store, goals=goals, queue=queue, protocol=protocol)


def _principal(tenant: str) -> PrincipalContext:
    return PrincipalContext(principal_id="user-1", tenant_id=tenant, membership_id=f"mem-{tenant}")


def _frame(conv: str) -> ContextFrame:
    return ContextFrame(tenant_id="tenant-a", principal_id="user-1", conversation_id=conv)


# ── Test M: capability generality (non-development objective) ────────────────


class TestCapabilityGenerality:
    OBJECTIVE = (
        "Research the top competing arena offers, compare their pricing and "
        "positioning, and map where our offer wins: pricing, guarantees, "
        "onboarding, community, proof"
    )

    def test_non_development_objective_same_protocol(self, env):
        principal = _principal("tenant-a")
        scope = WorkScope(tenant_id="tenant-a", conversation_id="conv-m")
        resolution = env.protocol.resolve(
            self.OBJECTIVE, principal, scope, _frame("conv-m"), client_message_id="m-1"
        )
        assert resolution.intent_class == IntentClass.CREATE_OBJECTIVE.value
        _, plan = env.protocol.plan_objective(
            resolution, self.OBJECTIVE, "conv-m", client_message_id="m-1", work_queue=env.queue
        )
        # Same protocol, same canonical artifacts — research archetype policy.
        assert plan.archetype_resolution["archetype_id"] == "research"
        assert plan.archetype_resolution["environment_class"] == "read_only"
        assert plan.workpacket_ids
        assert env.goals.get(plan.objective_id) is not None


# ── Test Q core: identical names in different tenants stay distinct ──────────


class TestTenantIsolation:
    TEXT = "Migrate the runtime subsystems to the boundary: queues, journals, traces"

    def test_identical_objectives_distinct_per_tenant(self, env):
        for tenant, conv, cmid in (("tenant-a", "conv-a", "q1"), ("tenant-b", "conv-b", "q2")):
            principal = _principal(tenant)
            scope = WorkScope(tenant_id=tenant, conversation_id=conv)
            resolution = env.protocol.resolve(
                self.TEXT,
                principal,
                scope,
                ContextFrame(tenant_id=tenant, principal_id="user-1", conversation_id=conv),
                client_message_id=cmid,
            )
            env.protocol.begin_planning_operation(
                resolution, self.TEXT, conv, client_message_id=cmid
            )
        goals = env.goals.all_goals()
        assert len(goals) == 2  # never merged across tenants
        assert {g.tenant_id for g in goals} == {"tenant-a", "tenant-b"}

    def test_cross_tenant_task_scope_rejected(self):
        plan_scope = WorkScope(tenant_id="tenant-a")
        task_scope = WorkScope(tenant_id="tenant-b")
        assert not task_scope.is_within(plan_scope)


# ── Test AI: event-lineage durability on ONE shared persisted spine ──────────


class TestEventDurability:
    def test_shared_spine_persists_and_recovers_lineage(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        reset_shared_event_spine()
        try:
            spine = get_shared_event_spine()
            correlation = planning_operation_key("tenant-a", "conv-1", "m1")
            from substrate.organism.event_spine import EventDomain

            for event_type in (
                "planning.intent_resolved",
                "planning.objective_created",
                "planning.plan_compiled",
                "planning.decision_recorded",
            ):
                spine.emit(
                    domain=EventDomain.OPERATOR,
                    event_type=event_type,
                    source="test",
                    data={"tenant_id": "tenant-a"},
                    correlation_id=correlation,
                )

            # Same accessor returns the SAME instance (one spine, §22.6).
            assert get_shared_event_spine() is spine

            # Restart: a fresh instance recovers the full chain from disk.
            reset_shared_event_spine()
            recovered = get_shared_event_spine()
            assert recovered is not spine
            chain = [e for e in recovered.recent(100) if e.correlation_id == correlation]
            assert [e.event_type for e in chain] == [
                "planning.intent_resolved",
                "planning.objective_created",
                "planning.plan_compiled",
                "planning.decision_recorded",
            ]
        finally:
            reset_shared_event_spine()
