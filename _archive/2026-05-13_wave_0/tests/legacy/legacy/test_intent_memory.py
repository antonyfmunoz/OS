"""Tests for intent memory — deterministic learning loop.

Validates:
1. Memory created on first completion.
2. Success increments correctly.
3. Failure increments correctly.
4. Repeated executions aggregate correctly.
5. Memory key is deterministic.
6. Memory persists across multiple runs.
7. Decision is blocked after 3 failures.
8. Decision is NOT blocked if at least 1 success exists.
9. Blocked decision emits correct observability event.
10. No state mutation occurs on block.
11. Replay safety: same inputs → same decisions.

Also:
- Decision engine integration: evaluate_and_emit respects memory guard.
- Existing decision_engine tests not broken (validated separately).
"""

from __future__ import annotations

import sys
import unittest
from typing import Any

sys.path.insert(0, "/opt/OS")

from umh.substrate.decision_engine import (
    DecisionEngine,
    DecisionOutput,
    Rule,
    RuleBasedStrategy,
    evaluate_and_emit,
)
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.intent_memory import (
    DECAY_WINDOW,
    FAILURE_TYPES,
    build_memory_update_mutations,
    compute_memory_key,
    lookup_intent_memory,
    should_block_intent,
    should_decay,
)
from umh.substrate.orchestration_mode import set_orchestration_mode_for_testing
from umh.substrate.runtime_state_store import RuntimeStateStore


# ── Helpers ──────────────────────────────────────────────────────────


def _make_store(state: dict | None = None) -> RuntimeStateStore:
    store = RuntimeStateStore()
    if state:
        for k, v in state.items():
            store.set(k, v)
    return store


GOAL_A = {"session_name": "s1", "task": "finalize"}
GOAL_B = {"session_name": "s2", "task": "publish"}
INTENT_TYPE = "lifecycle_finalize"
TIMESTAMP = "2026-04-17T00:00:00+00:00"


# ── A. Intent Memory Store Tests ────────────────────────────────────


class TestComputeMemoryKey(unittest.TestCase):
    """Test 5: memory key is deterministic."""

    def test_same_inputs_same_key(self):
        k1 = compute_memory_key(INTENT_TYPE, GOAL_A)
        k2 = compute_memory_key(INTENT_TYPE, GOAL_A)
        assert k1 == k2

    def test_different_goals_different_keys(self):
        k1 = compute_memory_key(INTENT_TYPE, GOAL_A)
        k2 = compute_memory_key(INTENT_TYPE, GOAL_B)
        assert k1 != k2

    def test_different_types_different_keys(self):
        k1 = compute_memory_key("lifecycle_finalize", GOAL_A)
        k2 = compute_memory_key("lifecycle_publish", GOAL_A)
        assert k1 != k2

    def test_key_format(self):
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        assert key.startswith("intent_memory.lifecycle_finalize.")
        # Hash portion is 12 hex chars
        parts = key.split(".")
        assert len(parts) == 3
        assert len(parts[2]) == 12


class TestLookupIntentMemory(unittest.TestCase):
    def test_returns_none_for_missing(self):
        result = lookup_intent_memory({}, INTENT_TYPE, GOAL_A)
        assert result is None

    def test_returns_record_when_present(self):
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {key: {"intent_type": INTENT_TYPE, "success_count": 1}}
        result = lookup_intent_memory(state, INTENT_TYPE, GOAL_A)
        assert result is not None
        assert result["success_count"] == 1


# ── B. Memory Mutation Tests ────────────────────────────────────────


class TestBuildMemoryUpdateMutations(unittest.TestCase):
    """Tests 1-4, 6: memory creation, increment, aggregation, persistence."""

    def test_creates_memory_on_first_completion(self):
        """Test 1: memory created on first completion."""
        mutations = build_memory_update_mutations(
            intent_type=INTENT_TYPE,
            goal=GOAL_A,
            outcome="completed",
            reason="",
            timestamp=TIMESTAMP,
            state={},
        )
        assert len(mutations) == 1
        m = mutations[0]
        assert m["op"] == "SET"
        assert m["key"] == compute_memory_key(INTENT_TYPE, GOAL_A)
        record = m["value"]
        assert record["execution_count"] == 1
        assert record["success_count"] == 1
        assert record["failure_count"] == 0
        assert record["last_outcome"] == "completed"
        assert record["last_reason"] == ""
        assert record["last_updated_at"] == TIMESTAMP
        assert record["intent_type"] == INTENT_TYPE
        assert record["goal"] == GOAL_A

    def test_success_increments_correctly(self):
        """Test 2: success increments correctly."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        existing_state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 2,
                "failure_count": 1,
                "last_outcome": "completed",
                "last_reason": "",
                "execution_count": 3,
                "last_updated_at": "2026-04-16T00:00:00+00:00",
            }
        }
        mutations = build_memory_update_mutations(
            intent_type=INTENT_TYPE,
            goal=GOAL_A,
            outcome="completed",
            reason="",
            timestamp=TIMESTAMP,
            state=existing_state,
        )
        record = mutations[0]["value"]
        assert record["success_count"] == 3
        assert record["failure_count"] == 1  # unchanged
        assert record["execution_count"] == 4

    def test_failure_increments_correctly(self):
        """Test 3: failure increments correctly."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        existing_state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 1,
                "last_outcome": "failed",
                "last_reason": "timeout",
                "execution_count": 1,
                "last_updated_at": "2026-04-16T00:00:00+00:00",
            }
        }
        mutations = build_memory_update_mutations(
            intent_type=INTENT_TYPE,
            goal=GOAL_A,
            outcome="failed",
            reason="connection_refused",
            timestamp=TIMESTAMP,
            state=existing_state,
        )
        record = mutations[0]["value"]
        assert record["failure_count"] == 2
        assert record["success_count"] == 0  # unchanged
        assert record["execution_count"] == 2
        assert record["last_reason"] == "connection_refused"
        assert record["last_outcome"] == "failed"

    def test_repeated_executions_aggregate(self):
        """Test 4: repeated executions aggregate correctly."""
        state: dict = {}
        key = compute_memory_key(INTENT_TYPE, GOAL_A)

        # Run 1: fail
        mutations = build_memory_update_mutations(
            INTENT_TYPE, GOAL_A, "failed", "err1", "t1", state
        )
        state[key] = mutations[0]["value"]

        # Run 2: fail
        mutations = build_memory_update_mutations(
            INTENT_TYPE, GOAL_A, "failed", "err2", "t2", state
        )
        state[key] = mutations[0]["value"]

        # Run 3: succeed
        mutations = build_memory_update_mutations(
            INTENT_TYPE, GOAL_A, "completed", "", "t3", state
        )
        state[key] = mutations[0]["value"]

        record = state[key]
        assert record["execution_count"] == 3
        assert record["failure_count"] == 2
        assert record["success_count"] == 1
        assert record["last_outcome"] == "completed"
        assert record["last_updated_at"] == "t3"

    def test_memory_persists_across_runs(self):
        """Test 6: memory persists across multiple runs via store."""
        store = _make_store()
        key = compute_memory_key(INTENT_TYPE, GOAL_A)

        # Simulate 3 sequential failures via store apply
        for i in range(3):
            snapshot = store.snapshot()
            mutations = build_memory_update_mutations(
                INTENT_TYPE, GOAL_A, "failed", f"err_{i}", f"t{i}", snapshot
            )
            store.apply_mutations(mutations)

        record = store.get(key)
        assert record is not None
        assert record["failure_count"] == 3
        assert record["execution_count"] == 3

    def test_mutation_is_set_only(self):
        """No list mutations, no APPEND, no INCREMENT — SET only."""
        mutations = build_memory_update_mutations(
            INTENT_TYPE, GOAL_A, "completed", "", TIMESTAMP, {}
        )
        for m in mutations:
            assert m["op"] == "SET"


# ── C. Decision Guard Tests ─────────────────────────────────────────


class TestShouldBlockIntent(unittest.TestCase):
    """Tests 7-8, 10."""

    def test_no_memory_does_not_block(self):
        blocked, memory = should_block_intent({}, INTENT_TYPE, GOAL_A)
        assert blocked is False
        assert memory is None

    def test_blocks_after_3_failures_zero_success(self):
        """Test 7: decision is blocked after 3 failures with real exec failures."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 3,
                "failure_by_type": {
                    "execution_failed": 2,
                    "execution_timed_out": 1,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 3,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            }
        }
        blocked, memory = should_block_intent(state, INTENT_TYPE, GOAL_A)
        assert blocked is True
        assert memory is not None

    def test_does_not_block_with_one_success(self):
        """Test 8: decision is NOT blocked if at least 1 success exists."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 1,
                "failure_count": 5,
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 6,
                "last_updated_at": TIMESTAMP,
            }
        }
        blocked, memory = should_block_intent(state, INTENT_TYPE, GOAL_A)
        assert blocked is False

    def test_does_not_block_below_threshold(self):
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 2,
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 2,
                "last_updated_at": TIMESTAMP,
            }
        }
        blocked, _ = should_block_intent(state, INTENT_TYPE, GOAL_A)
        assert blocked is False

    def test_custom_threshold(self):
        """Custom failure_threshold is respected (still needs exec_failed >= 2)."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 2,
                "failure_by_type": {
                    "execution_failed": 2,
                    "execution_timed_out": 0,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 2,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            }
        }
        blocked, _ = should_block_intent(
            state, INTENT_TYPE, GOAL_A, failure_threshold=1
        )
        assert blocked is True

    def test_no_state_mutation_on_block(self):
        """Test 10: no state mutation occurs on block."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        record = {
            "intent_type": INTENT_TYPE,
            "goal": GOAL_A,
            "success_count": 0,
            "failure_count": 3,
            "failure_by_type": {
                "execution_failed": 2,
                "execution_timed_out": 1,
                "execution_rejected": 0,
                "driver_failure": 0,
            },
            "last_outcome": "failed",
            "last_reason": "err",
            "execution_count": 3,
            "last_updated_at": TIMESTAMP,
            "last_success_at": None,
        }
        import copy

        state = {key: copy.deepcopy(record)}
        state_before = copy.deepcopy(state)

        blocked, _ = should_block_intent(state, INTENT_TYPE, GOAL_A)
        assert blocked is True
        # State must be identical after the check
        assert state == state_before


# ── D. Decision Engine Integration Tests ─────────────────────────────


def _needs_finalization(state: dict) -> bool:
    return (
        state.get("status") == "completion_proposed"
        and state.get("finalization_status") != "succeeded"
    )


def _build_finalization_payload(state: dict) -> dict:
    return {
        "session_name": state.get("session_name", "test"),
        "finalization_result": {"success": True},
    }


FINALIZATION_RULE = Rule(
    rule_id="finalize_ready",
    description="Trigger finalization when completion is proposed",
    condition=_needs_finalization,
    event_type="finalization_succeeded",
    build_payload=_build_finalization_payload,
    priority=10,
)


def _make_decision_engine() -> DecisionEngine:
    strategy = RuleBasedStrategy(rules=[FINALIZATION_RULE])
    return DecisionEngine(strategy=strategy, enabled=True)


class TestDecisionEngineMemoryGuard(unittest.TestCase):
    """Tests 9, 11: blocked decision observability + replay safety."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    @staticmethod
    def _get_queued_events(scheduler: EventScheduler) -> list[SchedulerEvent]:
        """Read events directly from the scheduler's internal queue."""
        return list(scheduler._queue)

    def test_blocked_decision_emits_observability_event(self):
        """Test 9: blocked decision emits correct observability event."""
        engine = _make_decision_engine()

        base_state = {
            "status": "completion_proposed",
            "session_name": "test",
        }

        # First, figure out what goal evaluate_and_emit will construct
        temp_store = _make_store(base_state)
        output = engine.evaluate(temp_store)
        assert output is not None

        constructed_goal = {
            **output.payload,
            "session_name": output.payload.get("session_name", ""),
        }
        memory_key = compute_memory_key("lifecycle_finalize", constructed_goal)

        # Build the real store with memory pre-populated
        store = _make_store(base_state)
        store.set(
            memory_key,
            {
                "intent_type": "lifecycle_finalize",
                "goal": constructed_goal,
                "success_count": 0,
                "failure_count": 3,
                "failure_by_type": {
                    "execution_failed": 2,
                    "execution_timed_out": 1,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "repeated",
                "execution_count": 3,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            },
        )

        scheduler = EventScheduler(store=store)
        result = evaluate_and_emit(engine, store, scheduler)
        assert result is not None

        events = self._get_queued_events(scheduler)
        event_types = [e.event_type for e in events]
        assert "decision_made" in event_types
        assert "decision_blocked_by_memory" in event_types
        assert "decision_intent_proposed" not in event_types

        # Validate the blocked event payload (enhanced)
        blocked_event = next(
            e for e in events if e.event_type == "decision_blocked_by_memory"
        )
        assert blocked_event.payload["intent_type"] == "lifecycle_finalize"
        assert blocked_event.payload["failure_count"] == 3
        assert blocked_event.payload["success_count"] == 0
        assert blocked_event.payload["reason"] == "repeated_failure"
        assert blocked_event.payload["failure_by_type"]["execution_failed"] == 2
        assert blocked_event.payload["decayed"] is False
        assert blocked_event.payload["last_updated_at"] == TIMESTAMP

    def test_unblocked_when_success_exists(self):
        """Decision proceeds when memory has at least 1 success."""
        engine = _make_decision_engine()
        base_state = {
            "status": "completion_proposed",
            "session_name": "test",
        }

        temp_store = _make_store(base_state)
        output = engine.evaluate(temp_store)
        assert output is not None

        constructed_goal = {
            **output.payload,
            "session_name": output.payload.get("session_name", ""),
        }
        memory_key = compute_memory_key("lifecycle_finalize", constructed_goal)

        store = _make_store(base_state)
        store.set(
            memory_key,
            {
                "intent_type": "lifecycle_finalize",
                "goal": constructed_goal,
                "success_count": 1,
                "failure_count": 5,
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 6,
                "last_updated_at": TIMESTAMP,
            },
        )

        scheduler = EventScheduler(store=store)
        result = evaluate_and_emit(engine, store, scheduler)
        assert result is not None

        events = self._get_queued_events(scheduler)
        event_types = [e.event_type for e in events]
        assert "decision_intent_proposed" in event_types
        assert "decision_blocked_by_memory" not in event_types

    def test_no_memory_proceeds_normally(self):
        """No memory record → decision proceeds normally."""
        engine = _make_decision_engine()
        store = _make_store({"status": "completion_proposed", "session_name": "test"})
        scheduler = EventScheduler(store=store)

        result = evaluate_and_emit(engine, store, scheduler)
        assert result is not None

        events = self._get_queued_events(scheduler)
        event_types = [e.event_type for e in events]
        assert "decision_intent_proposed" in event_types
        assert "decision_blocked_by_memory" not in event_types

    def test_no_block_on_inactive_mode(self):
        """When ORCHESTRATION_MODE is inactive, memory guard is skipped."""
        set_orchestration_mode_for_testing(False)

        engine = _make_decision_engine()
        store = _make_store({"status": "completion_proposed", "session_name": "test"})

        output = engine.evaluate(store)
        assert output is not None

        constructed_goal = {
            **output.payload,
            "session_name": output.payload.get("session_name", ""),
        }
        memory_key = compute_memory_key("lifecycle_finalize", constructed_goal)
        store.set(
            memory_key,
            {
                "intent_type": "lifecycle_finalize",
                "goal": constructed_goal,
                "success_count": 0,
                "failure_count": 10,
                "failure_by_type": {
                    "execution_failed": 8,
                    "execution_timed_out": 2,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 10,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            },
        )

        scheduler = EventScheduler(store=store)
        result = evaluate_and_emit(engine, store, scheduler)
        assert result is not None

        events = self._get_queued_events(scheduler)
        event_types = [e.event_type for e in events]
        # In inactive mode, the raw action event is emitted (legacy path)
        assert "finalization_succeeded" in event_types
        assert "decision_blocked_by_memory" not in event_types


class TestReplaySafety(unittest.TestCase):
    """Test 11: replay safety — same inputs → same decisions."""

    def test_same_state_same_block_decision(self):
        """Identical state produces identical block/unblock decisions."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 3,
                "failure_by_type": {
                    "execution_failed": 2,
                    "execution_timed_out": 1,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 3,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            }
        }

        # Run the check twice
        blocked1, mem1 = should_block_intent(state, INTENT_TYPE, GOAL_A)
        blocked2, mem2 = should_block_intent(state, INTENT_TYPE, GOAL_A)

        assert blocked1 == blocked2
        assert mem1 == mem2

    def test_same_mutations_same_memory(self):
        """Same sequence of mutations produces identical memory state."""
        outcomes = [
            ("failed", "err1", "t1"),
            ("failed", "err2", "t2"),
            ("completed", "", "t3"),
        ]

        # Run 1
        state1: dict = {}
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        for outcome, reason, ts in outcomes:
            mutations = build_memory_update_mutations(
                INTENT_TYPE, GOAL_A, outcome, reason, ts, state1
            )
            state1[key] = mutations[0]["value"]

        # Run 2 (replay)
        state2: dict = {}
        for outcome, reason, ts in outcomes:
            mutations = build_memory_update_mutations(
                INTENT_TYPE, GOAL_A, outcome, reason, ts, state2
            )
            state2[key] = mutations[0]["value"]

        assert state1[key] == state2[key]

    def test_memory_key_deterministic_across_runs(self):
        """Same intent_type + goal always produces same key."""
        keys = [compute_memory_key(INTENT_TYPE, GOAL_A) for _ in range(100)]
        assert len(set(keys)) == 1


# ── E. Failure Classification Tests ───────────────────────────────────


class TestFailureClassification(unittest.TestCase):
    """Tests for failure_by_type tracking."""

    def test_classification_increments_correct_bucket(self):
        """Each failure type increments its own bucket."""
        state: dict = {}
        key = compute_memory_key(INTENT_TYPE, GOAL_A)

        mutations = build_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "failed",
            "crash",
            "t1",
            state,
            failure_type="execution_failed",
        )
        state[key] = mutations[0]["value"]

        record = state[key]
        assert record["failure_by_type"]["execution_failed"] == 1
        assert record["failure_by_type"]["execution_timed_out"] == 0
        assert record["failure_by_type"]["execution_rejected"] == 0
        assert record["failure_by_type"]["driver_failure"] == 0
        assert record["failure_count"] == 1

    def test_mixed_failure_types_tracked_correctly(self):
        """Multiple failure types each increment independently."""
        state: dict = {}
        key = compute_memory_key(INTENT_TYPE, GOAL_A)

        # 2 execution_failed, 1 timed_out, 1 driver_failure
        for ft, reason in [
            ("execution_failed", "crash1"),
            ("execution_failed", "crash2"),
            ("execution_timed_out", "timeout"),
            ("driver_failure", "plan_gone"),
        ]:
            mutations = build_memory_update_mutations(
                INTENT_TYPE,
                GOAL_A,
                "failed",
                reason,
                f"t_{ft}_{reason}",
                state,
                failure_type=ft,
            )
            state[key] = mutations[0]["value"]

        record = state[key]
        assert record["failure_count"] == 4
        assert record["failure_by_type"]["execution_failed"] == 2
        assert record["failure_by_type"]["execution_timed_out"] == 1
        assert record["failure_by_type"]["execution_rejected"] == 0
        assert record["failure_by_type"]["driver_failure"] == 1

    def test_block_requires_execution_failed_gte_2(self):
        """Block requires at least 2 execution_failed, not just total >= 3."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 5,
                "failure_by_type": {
                    "execution_failed": 2,
                    "execution_timed_out": 2,
                    "execution_rejected": 1,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 5,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            }
        }
        blocked, _ = should_block_intent(state, INTENT_TYPE, GOAL_A)
        assert blocked is True

        # Now with only 1 execution_failed: should NOT block
        state[key]["failure_by_type"]["execution_failed"] = 1
        blocked, _ = should_block_intent(state, INTENT_TYPE, GOAL_A)
        assert blocked is False

    def test_timeouts_alone_do_not_trigger_block(self):
        """Edge case: failure_count=3 but all timed_out → NOT blocked."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 3,
                "failure_by_type": {
                    "execution_failed": 0,
                    "execution_timed_out": 3,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "timeout",
                "execution_count": 3,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            }
        }
        blocked, _ = should_block_intent(state, INTENT_TYPE, GOAL_A)
        assert blocked is False

    def test_success_records_last_success_at(self):
        """Success sets last_success_at timestamp."""
        mutations = build_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "completed",
            "",
            TIMESTAMP,
            {},
        )
        record = mutations[0]["value"]
        assert record["last_success_at"] == TIMESTAMP

    def test_failure_does_not_set_last_success_at(self):
        """Failure leaves last_success_at as None."""
        mutations = build_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "failed",
            "err",
            TIMESTAMP,
            {},
            failure_type="execution_failed",
        )
        record = mutations[0]["value"]
        assert record["last_success_at"] is None

    def test_all_failure_types_are_valid(self):
        """Verify FAILURE_TYPES constant matches expected buckets."""
        assert set(FAILURE_TYPES) == {
            "execution_failed",
            "execution_timed_out",
            "execution_rejected",
            "driver_failure",
        }

    def test_unknown_failure_type_ignored(self):
        """Unknown failure_type does not create dynamic key."""
        mutations = build_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "failed",
            "err",
            TIMESTAMP,
            {},
            failure_type="unknown_type",
        )
        record = mutations[0]["value"]
        assert record["failure_count"] == 1
        # All buckets still zero — unknown type is silently ignored
        assert all(v == 0 for v in record["failure_by_type"].values())
        assert "unknown_type" not in record["failure_by_type"]

    def test_backcompat_missing_failure_by_type(self):
        """Pre-upgrade records without failure_by_type get it on next update."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        # Simulate a pre-upgrade record: no failure_by_type, no last_success_at
        old_record = {
            "intent_type": INTENT_TYPE,
            "goal": GOAL_A,
            "success_count": 0,
            "failure_count": 2,
            "last_outcome": "failed",
            "last_reason": "err",
            "execution_count": 2,
            "last_updated_at": "2026-04-16T00:00:00+00:00",
        }
        state = {key: old_record}
        mutations = build_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "failed",
            "crash",
            TIMESTAMP,
            state,
            failure_type="execution_failed",
        )
        record = mutations[0]["value"]
        assert "failure_by_type" in record
        assert record["failure_by_type"]["execution_failed"] == 1
        assert record["last_success_at"] is None


# ── F. Decay Tests ────────────────────────────────────────────────────


class TestDecay(unittest.TestCase):
    """Tests for controlled forgetting (decay)."""

    def _make_blocked_memory(self, last_updated: str = TIMESTAMP) -> dict[str, Any]:
        """Helper: a memory record that would be blocked (pre-decay)."""
        return {
            "intent_type": INTENT_TYPE,
            "goal": GOAL_A,
            "success_count": 0,
            "failure_count": 3,
            "failure_by_type": {
                "execution_failed": 2,
                "execution_timed_out": 1,
                "execution_rejected": 0,
                "driver_failure": 0,
            },
            "last_outcome": "failed",
            "last_reason": "err",
            "execution_count": 3,
            "last_updated_at": last_updated,
            "last_success_at": None,
        }

    def test_decay_allows_previously_blocked_intent(self):
        """After DECAY_WINDOW, blocked intent becomes unblocked."""
        from datetime import datetime, timedelta, timezone

        old_ts = "2026-04-15T00:00:00+00:00"
        # Current time is >24h later
        current_ts = (
            datetime.fromisoformat(old_ts) + timedelta(seconds=DECAY_WINDOW + 1)
        ).isoformat()

        memory = self._make_blocked_memory(last_updated=old_ts)
        assert should_decay(memory, current_ts) is True

        # Verify the guard respects decay
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {key: memory}
        blocked, _ = should_block_intent(
            state, INTENT_TYPE, GOAL_A, current_timestamp=current_ts
        )
        assert blocked is False

    def test_decay_does_not_mutate_memory(self):
        """Decay is read-time only. Memory record stays identical."""
        import copy
        from datetime import datetime, timedelta, timezone

        old_ts = "2026-04-15T00:00:00+00:00"
        current_ts = (
            datetime.fromisoformat(old_ts) + timedelta(seconds=DECAY_WINDOW + 1)
        ).isoformat()

        memory = self._make_blocked_memory(last_updated=old_ts)
        memory_before = copy.deepcopy(memory)

        result = should_decay(memory, current_ts)
        assert result is True
        # Memory is IDENTICAL after the check
        assert memory == memory_before

    def test_no_decay_within_window(self):
        """Within DECAY_WINDOW, decay does not apply."""
        from datetime import datetime, timedelta

        old_ts = "2026-04-16T00:00:00+00:00"
        # Only 1 hour later — well within 24h window
        current_ts = (datetime.fromisoformat(old_ts) + timedelta(hours=1)).isoformat()

        memory = self._make_blocked_memory(last_updated=old_ts)
        assert should_decay(memory, current_ts) is False

        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {key: memory}
        blocked, _ = should_block_intent(
            state, INTENT_TYPE, GOAL_A, current_timestamp=current_ts
        )
        assert blocked is True

    def test_no_decay_when_success_exists(self):
        """Decay rule only applies to 0-success records."""
        memory = self._make_blocked_memory()
        memory["success_count"] = 1  # has a success
        assert should_decay(memory, "2026-04-20T00:00:00+00:00") is False

    def test_no_decay_below_failure_threshold(self):
        """Decay rule requires failure_count >= 3."""
        memory = self._make_blocked_memory()
        memory["failure_count"] = 2
        assert should_decay(memory, "2026-04-20T00:00:00+00:00") is False

    def test_decay_with_empty_timestamp_returns_false(self):
        """Empty current_timestamp disables decay in should_block_intent."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        # Old enough to decay, but empty timestamp disables check
        memory = self._make_blocked_memory(last_updated="2026-04-01T00:00:00+00:00")
        state = {key: memory}
        blocked, _ = should_block_intent(
            state, INTENT_TYPE, GOAL_A, current_timestamp=""
        )
        # Still blocked because decay is disabled
        assert blocked is True


# ── G. Success Recovery Tests ─────────────────────────────────────────


class TestSuccessRecovery(unittest.TestCase):
    """Tests for success-based recovery."""

    def test_success_allows_execution_after_failures(self):
        """Even with many failures, 1 success means NOT blocked."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 1,
                "failure_count": 10,
                "failure_by_type": {
                    "execution_failed": 8,
                    "execution_timed_out": 2,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 11,
                "last_updated_at": TIMESTAMP,
                "last_success_at": "2026-04-16T12:00:00+00:00",
            }
        }
        blocked, _ = should_block_intent(state, INTENT_TYPE, GOAL_A)
        assert blocked is False

    def test_success_does_not_reset_failure_count(self):
        """Success increments success_count but leaves failure_count."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 3,
                "failure_by_type": {
                    "execution_failed": 2,
                    "execution_timed_out": 1,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 3,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            }
        }
        mutations = build_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "completed",
            "",
            "t_success",
            state,
        )
        record = mutations[0]["value"]
        assert record["success_count"] == 1
        assert record["failure_count"] == 3  # preserved, not reset
        assert record["last_success_at"] == "t_success"


# ── H. Replay Determinism Tests (Extended) ────────────────────────────


class TestReplayDeterminismExtended(unittest.TestCase):
    """Replay safety with failure classification and decay."""

    def test_same_timestamps_same_decay_decision(self):
        """Identical timestamps produce identical decay results."""
        memory = {
            "intent_type": INTENT_TYPE,
            "goal": GOAL_A,
            "success_count": 0,
            "failure_count": 3,
            "failure_by_type": {
                "execution_failed": 2,
                "execution_timed_out": 1,
                "execution_rejected": 0,
                "driver_failure": 0,
            },
            "last_outcome": "failed",
            "last_reason": "err",
            "execution_count": 3,
            "last_updated_at": "2026-04-15T00:00:00+00:00",
            "last_success_at": None,
        }
        ts = "2026-04-17T00:00:00+00:00"  # >24h later

        results = [should_decay(memory, ts) for _ in range(50)]
        assert all(r is True for r in results)

    def test_same_failure_types_same_block_decision(self):
        """Same failure_by_type → same block decision on replay."""
        key = compute_memory_key(INTENT_TYPE, GOAL_A)
        state = {
            key: {
                "intent_type": INTENT_TYPE,
                "goal": GOAL_A,
                "success_count": 0,
                "failure_count": 3,
                "failure_by_type": {
                    "execution_failed": 2,
                    "execution_timed_out": 1,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "err",
                "execution_count": 3,
                "last_updated_at": TIMESTAMP,
                "last_success_at": None,
            }
        }
        results = [should_block_intent(state, INTENT_TYPE, GOAL_A) for _ in range(50)]
        assert all(r[0] is True for r in results)

    def test_classified_mutations_replay_identical(self):
        """Same sequence with failure_type → identical memory state."""
        events = [
            ("failed", "crash", "t1", "execution_failed"),
            ("failed", "timeout", "t2", "execution_timed_out"),
            ("failed", "crash2", "t3", "execution_failed"),
            ("completed", "", "t4", ""),
        ]

        key = compute_memory_key(INTENT_TYPE, GOAL_A)

        # Run 1
        state1: dict = {}
        for outcome, reason, ts, ft in events:
            mutations = build_memory_update_mutations(
                INTENT_TYPE,
                GOAL_A,
                outcome,
                reason,
                ts,
                state1,
                failure_type=ft,
            )
            state1[key] = mutations[0]["value"]

        # Run 2 (replay)
        state2: dict = {}
        for outcome, reason, ts, ft in events:
            mutations = build_memory_update_mutations(
                INTENT_TYPE,
                GOAL_A,
                outcome,
                reason,
                ts,
                state2,
                failure_type=ft,
            )
            state2[key] = mutations[0]["value"]

        assert state1[key] == state2[key]
        assert state1[key]["failure_by_type"]["execution_failed"] == 2
        assert state1[key]["failure_by_type"]["execution_timed_out"] == 1
        assert state1[key]["success_count"] == 1
        assert state1[key]["last_success_at"] == "t4"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
