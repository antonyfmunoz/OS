"""Tests for the autonomy/safety control layer.

Validates:
1.  Policy disabled → current behavior preserved (no rejection).
2.  Decision ingress blocked when allow_decision_ingress=False.
3.  Operator ingress blocked when allow_operator_ingress=False.
4.  Cron ingress blocked when allow_cron_ingress=False.
5.  Result ingress blocked when allow_result_follow_on=False.
6.  Result follow_on rejected when chain_depth exceeds max_chain_depth.
7.  Result follow_on rejected when follow_on_count exceeds max_follow_on_per_root.
8.  Accepted result follow_on correctly inherits lineage fields.
9.  orch_intent_rejected emitted with full provenance payload.
10. Rejection path writes no intent state and no active_intent index.
11. Replay-safety: decisions derived only from persisted parent intent state.
12. Inactive/legacy mode regression safety.
"""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.substrate.autonomy_policy import AutonomyPolicy, IngressSource
from umh.substrate.event_scheduler import (
    ExecutionResult as SchedulerExecutionResult,
    SchedulerEvent,
)
from umh.substrate.intent_coordinator import IntentCoordinator
from umh.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    PlanStep,
    compute_intent_id,
    intent_store_key,
)
from umh.substrate.plan_registry import PlanRegistry
from umh.substrate.runtime_state_store import RuntimeStateStore
from umh.substrate.workflow_driver import WorkflowDriver


# ── Helpers ──────────────────────────────────────────────────────────


def _one_step_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return (PlanStep(step_index=0, event_type="only_step", payload={}),)


def _make_registry() -> PlanRegistry:
    reg = PlanRegistry()
    reg.register(IntentType.LIFECYCLE_FINALIZE, _one_step_generator)
    reg.register(IntentType.CUSTOM, _one_step_generator)
    return reg


def _make_coordinator(
    policy: AutonomyPolicy | None = None,
    max_active: int = 1,
) -> IntentCoordinator:
    reg = _make_registry()
    driver = WorkflowDriver(reg)
    return IntentCoordinator(reg, driver, max_active=max_active, autonomy_policy=policy)


def _make_store(state: dict | None = None) -> RuntimeStateStore:
    store = RuntimeStateStore()
    if state:
        for k, v in state.items():
            store.set(k, v)
    return store


def _make_ingress_event(
    intent_type: str = "lifecycle_finalize",
    goal: dict | None = None,
    priority: int = 100,
    session_name: str = "test_session",
    event_type: str = "operator_intent_requested",
    source_context: dict | None = None,
) -> SchedulerEvent:
    payload: dict = {
        "intent_type": intent_type,
        "goal": goal or {"session_name": session_name},
        "priority": priority,
    }
    if source_context is not None:
        payload["source_context"] = source_context
    return SchedulerEvent(
        event_type=event_type,
        session_name=session_name,
        source="test",
        payload=payload,
    )


def _apply_mutations(store: RuntimeStateStore, mutations: list[dict]) -> None:
    """Apply mutations to store for test state setup."""
    for m in mutations:
        op = m["op"]
        key = m["key"]
        if op == "SET":
            store.set(key, m["value"])
        elif op == "REMOVE":
            with store._lock:
                store._state.pop(key, None)


def _seed_parent_intent(
    store: RuntimeStateStore,
    parent_id: str = "int_parent_abc",
    chain_depth: int = 0,
    follow_on_count: int = 0,
    root_intent_id: str = "",
) -> None:
    """Write a completed parent intent into the store with lineage metadata."""
    store.set(
        intent_store_key(parent_id),
        {
            "intent_id": parent_id,
            "intent_type": "lifecycle_finalize",
            "goal": {"session_name": "test_session"},
            "status": "completed",
            "priority": 100,
            "created_at": "2026-04-17T00:00:00+00:00",
            "session_name": "test_session",
            "current_step": 0,
            "total_steps": 1,
            "metadata": {
                "source_type": "operator",
                "root_intent_id": root_intent_id,
                "parent_intent_id": "",
                "chain_depth": chain_depth,
                "follow_on_count_from_root": follow_on_count,
            },
        },
    )


# ── 1. Policy disabled preserves behavior ────────────────────────────


class TestPolicyDisabledPreservesBehavior(unittest.TestCase):
    """When policy is disabled (default), all ingress types pass through."""

    def test_decision_ingress_allowed(self):
        coord = _make_coordinator(policy=AutonomyPolicy(enabled=False))
        store = _make_store()
        event = _make_ingress_event(event_type="decision_intent_proposed")
        result = coord._handle_intent_ingress(store, event)
        self.assertNotIn("rejected", result.metadata)
        self.assertIn("intent_id", result.metadata)

    def test_operator_ingress_allowed(self):
        coord = _make_coordinator(policy=AutonomyPolicy(enabled=False))
        store = _make_store()
        event = _make_ingress_event(event_type="operator_intent_requested")
        result = coord._handle_intent_ingress(store, event)
        self.assertNotIn("rejected", result.metadata)
        self.assertIn("intent_id", result.metadata)

    def test_cron_ingress_allowed(self):
        coord = _make_coordinator(policy=AutonomyPolicy(enabled=False))
        store = _make_store()
        event = _make_ingress_event(event_type="cron_intent_requested")
        result = coord._handle_intent_ingress(store, event)
        self.assertNotIn("rejected", result.metadata)
        self.assertIn("intent_id", result.metadata)

    def test_result_ingress_allowed(self):
        coord = _make_coordinator(policy=AutonomyPolicy(enabled=False))
        store = _make_store()
        _seed_parent_intent(store, parent_id="int_parent_abc")
        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "follow_on"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_abc"},
        )
        result = coord._handle_intent_ingress(store, event)
        self.assertNotIn("rejected", result.metadata)
        self.assertIn("intent_id", result.metadata)

    def test_no_policy_means_disabled(self):
        """Coordinator constructed without policy arg behaves as disabled."""
        coord = _make_coordinator(policy=None)
        store = _make_store()
        event = _make_ingress_event(event_type="decision_intent_proposed")
        result = coord._handle_intent_ingress(store, event)
        self.assertNotIn("rejected", result.metadata)


# ── 2-5. Source type gating ──────────────────────────────────────────


class TestSourceTypeGating(unittest.TestCase):
    """Each ingress source can be independently blocked by policy."""

    def test_decision_ingress_blocked(self):
        policy = AutonomyPolicy(enabled=True, allow_decision_ingress=False)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        event = _make_ingress_event(event_type="decision_intent_proposed")
        result = coord._handle_intent_ingress(store, event)
        self.assertTrue(result.metadata.get("rejected"))
        self.assertIn("source_type_disabled:decision", result.metadata["reason"])

    def test_operator_ingress_blocked(self):
        policy = AutonomyPolicy(enabled=True, allow_operator_ingress=False)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        event = _make_ingress_event(event_type="operator_intent_requested")
        result = coord._handle_intent_ingress(store, event)
        self.assertTrue(result.metadata.get("rejected"))
        self.assertIn("source_type_disabled:operator", result.metadata["reason"])

    def test_cron_ingress_blocked(self):
        policy = AutonomyPolicy(enabled=True, allow_cron_ingress=False)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        event = _make_ingress_event(event_type="cron_intent_requested")
        result = coord._handle_intent_ingress(store, event)
        self.assertTrue(result.metadata.get("rejected"))
        self.assertIn("source_type_disabled:cron", result.metadata["reason"])

    def test_result_ingress_blocked(self):
        policy = AutonomyPolicy(enabled=True, allow_result_follow_on=False)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        event = _make_ingress_event(event_type="result_intent_requested")
        result = coord._handle_intent_ingress(store, event)
        self.assertTrue(result.metadata.get("rejected"))
        self.assertIn("source_type_disabled:result", result.metadata["reason"])


# ── 6. Chain depth enforcement ───────────────────────────────────────


class TestChainDepthEnforcement(unittest.TestCase):
    def test_depth_within_limit_accepted(self):
        policy = AutonomyPolicy(enabled=True, max_chain_depth=3)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        _seed_parent_intent(store, chain_depth=2)  # child depth=3
        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "depth_test"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_abc"},
        )
        result = coord._handle_intent_ingress(store, event)
        self.assertNotIn("rejected", result.metadata)
        self.assertIn("intent_id", result.metadata)

    def test_depth_exceeds_limit_rejected(self):
        policy = AutonomyPolicy(enabled=True, max_chain_depth=2)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        _seed_parent_intent(store, chain_depth=2)  # child depth=3
        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "depth_test"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_abc"},
        )
        result = coord._handle_intent_ingress(store, event)
        self.assertTrue(result.metadata.get("rejected"))
        self.assertIn("chain_depth_exceeded", result.metadata["reason"])

    def test_depth_at_exact_limit_accepted(self):
        """Depth exactly at max_chain_depth is allowed (<=, not <)."""
        policy = AutonomyPolicy(enabled=True, max_chain_depth=2)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        _seed_parent_intent(store, chain_depth=1)  # child depth=2
        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "exact_depth"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_abc"},
        )
        result = coord._handle_intent_ingress(store, event)
        self.assertNotIn("rejected", result.metadata)


# ── 7. Follow-on count enforcement ──────────────────────────────────


class TestFollowOnCountEnforcement(unittest.TestCase):
    def test_count_within_limit_accepted(self):
        policy = AutonomyPolicy(enabled=True, max_follow_on_per_root=5)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        _seed_parent_intent(store, follow_on_count=4)  # child count=5
        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "count_test"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_abc"},
        )
        result = coord._handle_intent_ingress(store, event)
        self.assertNotIn("rejected", result.metadata)

    def test_count_exceeds_limit_rejected(self):
        policy = AutonomyPolicy(enabled=True, max_follow_on_per_root=3)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        _seed_parent_intent(store, follow_on_count=3)  # child count=4
        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "count_test"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_abc"},
        )
        result = coord._handle_intent_ingress(store, event)
        self.assertTrue(result.metadata.get("rejected"))
        self.assertIn("follow_on_count_exceeded", result.metadata["reason"])


# ── 8. Lineage inheritance ───────────────────────────────────────────


class TestLineageInheritance(unittest.TestCase):
    """Result-driven intents inherit root_intent_id, parent_intent_id,
    chain_depth, and follow_on_count_from_root from persisted parent state."""

    def test_first_generation_lineage(self):
        """Non-result ingress gets default lineage (depth=0, no parent)."""
        coord = _make_coordinator(policy=AutonomyPolicy(enabled=True))
        store = _make_store()
        event = _make_ingress_event(event_type="operator_intent_requested")
        result = coord._handle_intent_ingress(store, event)
        _apply_mutations(store, result.mutations)

        intent_id = result.metadata["intent_id"]
        intent_raw = store.get(intent_store_key(intent_id))
        meta = intent_raw["metadata"]

        self.assertEqual(meta["source_type"], "operator")
        self.assertEqual(meta["root_intent_id"], "")
        self.assertEqual(meta["parent_intent_id"], "")
        self.assertEqual(meta["chain_depth"], 0)
        self.assertEqual(meta["follow_on_count_from_root"], 0)

    def test_result_inherits_from_parent(self):
        """Result-driven intent inherits lineage from persisted parent."""
        coord = _make_coordinator(policy=AutonomyPolicy(enabled=True))
        store = _make_store()
        _seed_parent_intent(
            store,
            parent_id="int_root_000",
            chain_depth=1,
            follow_on_count=2,
            root_intent_id="int_root_000",
        )
        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "child"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_root_000"},
        )
        result = coord._handle_intent_ingress(store, event)
        _apply_mutations(store, result.mutations)

        intent_id = result.metadata["intent_id"]
        intent_raw = store.get(intent_store_key(intent_id))
        meta = intent_raw["metadata"]

        self.assertEqual(meta["source_type"], "result")
        self.assertEqual(meta["root_intent_id"], "int_root_000")
        self.assertEqual(meta["parent_intent_id"], "int_root_000")
        self.assertEqual(meta["chain_depth"], 2)
        self.assertEqual(meta["follow_on_count_from_root"], 3)

    def test_root_derived_from_parent_without_root(self):
        """If parent has no root_intent_id, parent IS the root."""
        coord = _make_coordinator(policy=AutonomyPolicy(enabled=True))
        store = _make_store()
        _seed_parent_intent(
            store,
            parent_id="int_first_gen",
            chain_depth=0,
            follow_on_count=0,
            root_intent_id="",  # first generation — no root
        )
        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "second_gen"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_first_gen"},
        )
        result = coord._handle_intent_ingress(store, event)
        _apply_mutations(store, result.mutations)

        intent_id = result.metadata["intent_id"]
        intent_raw = store.get(intent_store_key(intent_id))
        meta = intent_raw["metadata"]

        self.assertEqual(meta["root_intent_id"], "int_first_gen")
        self.assertEqual(meta["parent_intent_id"], "int_first_gen")
        self.assertEqual(meta["chain_depth"], 1)
        self.assertEqual(meta["follow_on_count_from_root"], 1)


# ── 9. Rejection event payload ───────────────────────────────────────


class TestRejectionEventPayload(unittest.TestCase):
    """orch_intent_rejected event carries full provenance for debugging."""

    def test_rejection_event_has_full_provenance(self):
        policy = AutonomyPolicy(enabled=True, max_chain_depth=1)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        _seed_parent_intent(store, chain_depth=1, root_intent_id="int_root_x")

        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "deep_chain"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_abc"},
        )
        result = coord._handle_intent_ingress(store, event)

        self.assertTrue(result.metadata.get("rejected"))

        # Exactly one rejection event, no others
        self.assertEqual(len(result.emitted_events), 1)
        rej = result.emitted_events[0]
        self.assertEqual(rej.event_type, "orch_intent_rejected")
        self.assertEqual(rej.source, "intent_coordinator")

        payload = rej.payload
        self.assertEqual(payload["attempted_intent_type"], "custom")
        self.assertIn("chain_depth_exceeded", payload["reason"])
        self.assertEqual(payload["source_type"], "result")
        self.assertEqual(payload["root_intent_id"], "int_root_x")
        self.assertEqual(payload["parent_intent_id"], "int_parent_abc")
        self.assertEqual(payload["attempted_chain_depth"], 2)
        self.assertEqual(payload["attempted_follow_on_count"], 1)
        self.assertEqual(payload["goal_summary"], {"task": "deep_chain"})
        self.assertEqual(payload["raw_trigger_event_type"], "result_intent_requested")
        self.assertNotEqual(payload["raw_trigger_event_id"], "")


# ── 10. No state on rejection ────────────────────────────────────────


class TestNoStateOnRejection(unittest.TestCase):
    """Rejected intents must not create any state mutations."""

    def test_no_mutations_on_rejection(self):
        policy = AutonomyPolicy(enabled=True, allow_operator_ingress=False)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        event = _make_ingress_event(event_type="operator_intent_requested")
        result = coord._handle_intent_ingress(store, event)

        self.assertEqual(len(result.mutations), 0)

    def test_no_intent_state_written(self):
        policy = AutonomyPolicy(enabled=True, allow_cron_ingress=False)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        event = _make_ingress_event(event_type="cron_intent_requested")
        result = coord._handle_intent_ingress(store, event)
        _apply_mutations(store, result.mutations)

        # Store should have no intent: keys
        intent_keys = [k for k in store.keys() if k.startswith("intent:")]
        self.assertEqual(len(intent_keys), 0)

        # Store should have no active_intent. keys
        active_keys = [k for k in store.keys() if k.startswith("active_intent.")]
        self.assertEqual(len(active_keys), 0)

    def test_parent_completion_unaffected_by_child_rejection(self):
        """Parent stays completed even when follow-on child is rejected."""
        policy = AutonomyPolicy(enabled=True, max_chain_depth=0)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        _seed_parent_intent(store, parent_id="int_parent_stays", chain_depth=0)

        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "rejected_child"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_stays"},
        )
        result = coord._handle_intent_ingress(store, event)

        # Child rejected
        self.assertTrue(result.metadata.get("rejected"))

        # Parent still completed
        parent_raw = store.get(intent_store_key("int_parent_stays"))
        self.assertEqual(parent_raw["status"], "completed")


# ── 11. Replay safety ────────────────────────────────────────────────


class TestReplaySafety(unittest.TestCase):
    """Enforcement decisions are derived from persisted state only."""

    def test_lineage_from_store_not_memory(self):
        """Two independent calls with same event produce identical lineage
        because both read from the same persisted parent state."""
        policy = AutonomyPolicy(enabled=True, max_chain_depth=5)
        coord = _make_coordinator(policy=policy)
        store = _make_store()
        _seed_parent_intent(store, chain_depth=2, follow_on_count=3)

        event = _make_ingress_event(
            intent_type="custom",
            goal={"task": "replay_test"},
            event_type="result_intent_requested",
            source_context={"triggering_intent_id": "int_parent_abc"},
        )

        result1 = coord._handle_intent_ingress(store, event)
        _apply_mutations(store, result1.mutations)

        # Reset store (simulate replay from scratch)
        store.reset()
        _seed_parent_intent(store, chain_depth=2, follow_on_count=3)

        result2 = coord._handle_intent_ingress(store, event)

        # Both should produce same intent_id and same lineage
        self.assertEqual(result1.metadata["intent_id"], result2.metadata["intent_id"])


# ── 12. Legacy/inactive regression ───────────────────────────────────


class TestLegacyRegression(unittest.TestCase):
    """Existing coordinator tests must still pass with default policy."""

    def test_dedup_still_works(self):
        coord = _make_coordinator()
        store = _make_store()
        event = _make_ingress_event(event_type="operator_intent_requested")
        result1 = coord._handle_intent_ingress(store, event)
        _apply_mutations(store, result1.mutations)

        # Same event again
        result2 = coord._handle_intent_ingress(store, event)
        self.assertTrue(result2.metadata.get("skipped"))
        self.assertEqual(result2.metadata.get("reason"), "intent_already_exists")

    def test_unknown_intent_type_still_dropped(self):
        coord = _make_coordinator()
        store = _make_store()
        event = _make_ingress_event(
            intent_type="nonexistent_type",
            event_type="operator_intent_requested",
        )
        result = coord._handle_intent_ingress(store, event)
        self.assertTrue(result.metadata.get("skipped"))
        self.assertEqual(result.metadata.get("reason"), "unknown_intent_type")

    def test_pending_queuing_still_works(self):
        coord = _make_coordinator(max_active=1)
        store = _make_store()

        # First fills active slot
        event1 = _make_ingress_event(
            goal={"session_name": "s1"},
            event_type="operator_intent_requested",
        )
        result1 = coord._handle_intent_ingress(store, event1)
        _apply_mutations(store, result1.mutations)

        # Second should queue as PENDING
        event2 = _make_ingress_event(
            goal={"session_name": "s2"},
            event_type="operator_intent_requested",
        )
        result2 = coord._handle_intent_ingress(store, event2)

        intent_id2 = result2.metadata["intent_id"]
        set_keys = [m["key"] for m in result2.mutations if m["op"] == "SET"]
        self.assertIn(intent_store_key(intent_id2), set_keys)
        self.assertNotIn(f"active_intent.{intent_id2}", set_keys)


# ── Policy model unit tests ──────────────────────────────────────────


class TestAutonomyPolicyModel(unittest.TestCase):
    """Unit tests for AutonomyPolicy dataclass methods."""

    def test_default_is_disabled(self):
        policy = AutonomyPolicy()
        self.assertFalse(policy.enabled)

    def test_disabled_allows_all_sources(self):
        policy = AutonomyPolicy(
            enabled=False,
            allow_decision_ingress=False,
            allow_operator_ingress=False,
        )
        # Even with flags False, disabled policy allows all
        self.assertTrue(policy.is_source_allowed(IngressSource.DECISION))
        self.assertTrue(policy.is_source_allowed(IngressSource.OPERATOR))

    def test_enabled_respects_flags(self):
        policy = AutonomyPolicy(enabled=True, allow_cron_ingress=False)
        self.assertFalse(policy.is_source_allowed(IngressSource.CRON))
        self.assertTrue(policy.is_source_allowed(IngressSource.DECISION))

    def test_check_chain_depth_disabled(self):
        policy = AutonomyPolicy(enabled=False, max_chain_depth=0)
        self.assertTrue(policy.check_chain_depth(100))

    def test_check_chain_depth_enabled(self):
        policy = AutonomyPolicy(enabled=True, max_chain_depth=3)
        self.assertTrue(policy.check_chain_depth(3))
        self.assertFalse(policy.check_chain_depth(4))

    def test_check_follow_on_count_disabled(self):
        policy = AutonomyPolicy(enabled=False, max_follow_on_per_root=0)
        self.assertTrue(policy.check_follow_on_count(100))

    def test_check_follow_on_count_enabled(self):
        policy = AutonomyPolicy(enabled=True, max_follow_on_per_root=5)
        self.assertTrue(policy.check_follow_on_count(5))
        self.assertFalse(policy.check_follow_on_count(6))

    def test_frozen_immutable(self):
        policy = AutonomyPolicy(enabled=True)
        with self.assertRaises(AttributeError):
            policy.enabled = False  # type: ignore[misc]


class TestIngressSourceMapping(unittest.TestCase):
    """IngressSource.from_event_type maps correctly."""

    def test_all_four_types_mapped(self):
        self.assertEqual(
            IngressSource.from_event_type("decision_intent_proposed"),
            IngressSource.DECISION,
        )
        self.assertEqual(
            IngressSource.from_event_type("operator_intent_requested"),
            IngressSource.OPERATOR,
        )
        self.assertEqual(
            IngressSource.from_event_type("cron_intent_requested"),
            IngressSource.CRON,
        )
        self.assertEqual(
            IngressSource.from_event_type("result_intent_requested"),
            IngressSource.RESULT,
        )

    def test_unknown_type_returns_none(self):
        self.assertIsNone(IngressSource.from_event_type("unknown_event"))


if __name__ == "__main__":
    unittest.main()
