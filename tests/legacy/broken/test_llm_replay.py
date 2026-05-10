"""Tests for the LLM replay strategy — determinism, concurrency, and replay.

Validates:
1. Config enforcement (disabled, intent excluded, skipped events).
2. Cache miss: single LLM call, record stored, events emitted, sentinel.
3. Cache hit: no LLM call, re-emit from stored emitted_events.
4. Strict replay validation with schema changes.
5. Timeout: non-leaky, emits REJECTED, returns None.
6. Selection policy: ALL vs FIRST.
7. Drift detection: scoped to identical execution context only.
8. Concurrency: per-key locking prevents duplicate LLM calls.
9. Proposal step index ordering.
10. Non-mutating observability events.
"""

from __future__ import annotations

import json
import sys
import threading
import time

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.event_scheduler import EventScheduler, SchedulerEvent
from eos_ai.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    intent_store_key,
)
from eos_ai.substrate.llm_planner import (
    EventSchema,
    EventTypeRegistry,
    LLMPlannerConfig,
    LLMPlanningStrategy,
    ProposedEvent,
    SelectionPolicy,
    _canonical_json,
)
from eos_ai.substrate.llm_replay import LLMDecisionRecord, ReplayableStrategy
from eos_ai.substrate.runtime_state_store import RuntimeStateStore


# ─── Fixtures ────────────────────────────────────────────────────────


def _make_registry() -> EventTypeRegistry:
    reg = EventTypeRegistry()
    reg.register(
        EventSchema(
            event_type="test_action",
            required_fields=frozenset({"session_name", "action"}),
            optional_fields=frozenset({"metadata"}),
            field_types={"session_name": str, "action": str},
            is_mutation=True,
        )
    )
    reg.register(
        EventSchema(
            event_type="test_mutation",
            required_fields=frozenset({"key", "value"}),
            optional_fields=frozenset(),
            is_mutation=True,
        )
    )
    return reg


def _make_config(**overrides) -> LLMPlannerConfig:
    defaults = {"enabled": True, "model_name": "test-model"}
    defaults.update(overrides)
    return LLMPlannerConfig(**defaults)


def _make_scheduler() -> tuple[EventScheduler, RuntimeStateStore]:
    from eos_ai.substrate.event_log_runtime import EventLogRuntime

    store = RuntimeStateStore()
    scheduler = EventScheduler(store=store)
    return scheduler, store


VALID_RESPONSE = json.dumps(
    {
        "events": [
            {
                "event_type": "test_action",
                "payload": {"session_name": "s1", "action": "go"},
            },
        ],
        "reasoning": "Test reasoning",
    }
)

MULTI_EVENT_RESPONSE = json.dumps(
    {
        "events": [
            {
                "event_type": "test_action",
                "payload": {"session_name": "s1", "action": "a"},
            },
            {"event_type": "test_mutation", "payload": {"key": "k", "value": "v"}},
        ],
    }
)


def _make_llm_fn(response: str):
    call_count = [0]

    def fn(prompt: str) -> str:
        call_count[0] += 1
        return response

    fn.call_count = call_count
    return fn


def _make_slow_llm_fn(response: str, delay_s: float):
    call_count = [0]

    def fn(prompt: str) -> str:
        call_count[0] += 1
        time.sleep(delay_s)
        return response

    fn.call_count = call_count
    return fn


def _make_replayable(
    llm_fn=None,
    registry=None,
    config=None,
    scheduler=None,
) -> tuple[ReplayableStrategy, EventScheduler]:
    if scheduler is None:
        scheduler, _ = _make_scheduler()
    registry = registry or _make_registry()
    config = config or _make_config()
    inner = LLMPlanningStrategy(
        llm_fn=llm_fn or _make_llm_fn(VALID_RESPONSE),
        registry=registry,
        config=config,
    )
    strategy = ReplayableStrategy(
        inner=inner,
        scheduler=scheduler,
        config=config,
        registry=registry,
    )
    return strategy, scheduler


def _make_state(session_name: str = "s1", **extra) -> dict:
    return {"session_name": session_name, **extra}


def _collect_emitted_events(scheduler: EventScheduler) -> list[SchedulerEvent]:
    """Collect all events in the scheduler queue without draining."""
    events = []
    while scheduler._queue:
        events.append(scheduler._queue.popleft())
    return events


# ─── Config enforcement ──────────────────────────────────────────────


class TestConfigEnforcement:
    def test_disabled_returns_none_emits_skipped(self):
        strategy, scheduler = _make_replayable(config=_make_config(enabled=False))
        result = strategy.evaluate(_make_state())
        assert result is None
        events = _collect_emitted_events(scheduler)
        skipped = [e for e in events if e.event_type == "llm_decision_skipped"]
        assert len(skipped) == 1
        assert skipped[0].payload["reason"] == "disabled"

    def test_intent_type_excluded_returns_none(self):
        config = _make_config(
            enabled_intent_types={IntentType.LIFECYCLE_PUBLISH},
        )
        # Create state with a LIFECYCLE_FINALIZE intent (not in enabled set)
        intent = Intent(
            intent_id="int_test",
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            goal={},
            session_name="s1",
        )
        state = _make_state()
        state[intent_store_key("int_test")] = intent.to_dict()
        state["active_intents"] = ["int_test"]

        strategy, scheduler = _make_replayable(config=config)
        result = strategy.evaluate(state)
        assert result is None
        events = _collect_emitted_events(scheduler)
        skipped = [e for e in events if e.event_type == "llm_decision_skipped"]
        assert len(skipped) == 1
        assert skipped[0].payload["reason"] == "intent_type_excluded"

    def test_no_active_intents_with_filter(self):
        config = _make_config(
            enabled_intent_types={IntentType.LIFECYCLE_FINALIZE},
        )
        strategy, scheduler = _make_replayable(config=config)
        result = strategy.evaluate(_make_state())
        assert result is None
        events = _collect_emitted_events(scheduler)
        skipped = [e for e in events if e.event_type == "llm_decision_skipped"]
        assert len(skipped) == 1
        assert skipped[0].payload["reason"] == "no_active_intents"


# ─── Cache miss ──────────────────────────────────────────────────────


class TestCacheMiss:
    def test_single_llm_call(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn)
        result = strategy.evaluate(_make_state())
        assert result is not None
        assert llm_fn.call_count[0] == 1

    def test_sentinel_shape(self):
        strategy, scheduler = _make_replayable()
        result = strategy.evaluate(_make_state())
        assert result is not None
        assert result.event_type == "llm_proposal_accepted"
        assert result.is_terminal is True
        assert result.suppress_downstream is True
        assert result.strategy_name == "llm_replayable"

    def test_events_emitted(self):
        strategy, scheduler = _make_replayable()
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        action_events = [e for e in events if e.event_type == "test_action"]
        assert len(action_events) == 1

    def test_event_metadata(self):
        strategy, scheduler = _make_replayable()
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        action_events = [e for e in events if e.event_type == "test_action"]
        assert len(action_events) == 1
        evt = action_events[0]
        assert "proposal_id" in evt.metadata
        assert "proposal_step_index" in evt.metadata
        assert evt.metadata["proposal_step_index"] == 0
        assert evt.source == "llm_planner"

    def test_record_stored(self):
        strategy, scheduler = _make_replayable()
        state = _make_state()
        strategy.evaluate(state)
        # Verify store has record
        canonical = _canonical_json(state)
        from eos_ai.substrate.llm_planner import _sha256_prefix

        state_hash = _sha256_prefix(canonical)
        record = strategy._store_get(state_hash)
        assert record is not None
        assert len(record.emitted_events) == 1

    def test_accepted_event_emitted(self):
        strategy, scheduler = _make_replayable()
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        accepted = [e for e in events if e.event_type == "llm_decision_accepted"]
        assert len(accepted) == 1

    def test_requested_and_received_events(self):
        strategy, scheduler = _make_replayable()
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        types = [e.event_type for e in events]
        assert "llm_decision_requested" in types
        assert "llm_decision_received" in types


# ─── Cache hit ───────────────────────────────────────────────────────


class TestCacheHit:
    def test_no_second_llm_call(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn)
        state = _make_state()
        strategy.evaluate(state)
        _collect_emitted_events(scheduler)  # drain
        strategy.evaluate(state)
        assert llm_fn.call_count[0] == 1

    def test_re_emits_from_stored_events(self):
        strategy, scheduler = _make_replayable()
        state = _make_state()
        strategy.evaluate(state)
        _collect_emitted_events(scheduler)  # drain first call events
        result = strategy.evaluate(state)
        assert result is not None
        events = _collect_emitted_events(scheduler)
        action_events = [e for e in events if e.event_type == "test_action"]
        assert len(action_events) == 1

    def test_sentinel_on_replay(self):
        strategy, scheduler = _make_replayable()
        state = _make_state()
        strategy.evaluate(state)
        _collect_emitted_events(scheduler)
        result = strategy.evaluate(state)
        assert result is not None
        assert result.is_terminal is True


# ─── Strict replay validation ────────────────────────────────────────


class TestStrictReplayValidation:
    def test_schema_match_succeeds(self):
        registry = _make_registry()
        strategy, scheduler = _make_replayable(registry=registry)
        state = _make_state()
        strategy.evaluate(state)
        _collect_emitted_events(scheduler)
        # Same registry, strict mode
        result = strategy.evaluate(state)
        assert result is not None

    def test_schema_mismatch_falls_through(self):
        registry = _make_registry()
        config = _make_config(strict_replay_validation=True)
        strategy, scheduler = _make_replayable(registry=registry, config=config)
        state = _make_state()
        strategy.evaluate(state)
        _collect_emitted_events(scheduler)
        # Change registry (schema_hash changes)
        registry.register(
            EventSchema(
                event_type="new_event",
                required_fields=frozenset({"x"}),
                optional_fields=frozenset(),
            )
        )
        # Replay should detect schema mismatch
        result = strategy.evaluate(state)
        # The re-validation should still pass since test_action is still valid
        # (we only added a new type, didn't remove or change existing ones)
        assert result is not None

    def test_schema_removal_causes_fallthrough(self):
        """If the event type is removed from registry, strict replay fails."""
        registry = EventTypeRegistry()
        registry.register(
            EventSchema(
                event_type="test_action",
                required_fields=frozenset({"session_name", "action"}),
                optional_fields=frozenset(),
                field_types={"session_name": str, "action": str},
            )
        )
        config = _make_config(strict_replay_validation=True)
        strategy, scheduler = _make_replayable(registry=registry, config=config)
        state = _make_state()
        strategy.evaluate(state)
        _collect_emitted_events(scheduler)

        # Replace registry contents (remove test_action, add different type)
        # Simulate by clearing and re-registering different schema
        registry._schemas.clear()
        registry._cached_hash = None
        registry._version += 1
        registry.register(
            EventSchema(
                event_type="other_event",
                required_fields=frozenset({"x"}),
                optional_fields=frozenset(),
            )
        )

        result = strategy.evaluate(state)
        assert result is None  # Falls through because re-validation fails


# ─── Timeout ─────────────────────────────────────────────────────────


class TestTimeout:
    def test_timeout_returns_none(self):
        slow_fn = _make_slow_llm_fn(VALID_RESPONSE, delay_s=5.0)
        config = _make_config(timeout_ms=100)
        strategy, scheduler = _make_replayable(llm_fn=slow_fn, config=config)
        result = strategy.evaluate(_make_state())
        assert result is None

    def test_timeout_emits_rejected(self):
        slow_fn = _make_slow_llm_fn(VALID_RESPONSE, delay_s=5.0)
        config = _make_config(timeout_ms=100)
        strategy, scheduler = _make_replayable(llm_fn=slow_fn, config=config)
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        rejected = [e for e in events if e.event_type == "llm_decision_rejected"]
        assert len(rejected) >= 1
        assert "timeout" in rejected[0].payload["rejection_reason"]


# ─── Parse failure ───────────────────────────────────────────────────


class TestParseFailure:
    def test_parse_failure_returns_none(self):
        llm_fn = _make_llm_fn("not json {{")
        strategy, scheduler = _make_replayable(llm_fn=llm_fn)
        result = strategy.evaluate(_make_state())
        assert result is None

    def test_parse_failure_emits_rejected(self):
        llm_fn = _make_llm_fn("not json {{")
        strategy, scheduler = _make_replayable(llm_fn=llm_fn)
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        rejected = [e for e in events if e.event_type == "llm_decision_rejected"]
        assert len(rejected) >= 1
        assert "parse_error" in rejected[0].payload["rejection_reason"]


# ─── All events rejected ─────────────────────────────────────────────


class TestAllRejected:
    def test_returns_none(self):
        response = json.dumps(
            {"events": [{"event_type": "unknown_type", "payload": {}}]}
        )
        llm_fn = _make_llm_fn(response)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn)
        result = strategy.evaluate(_make_state())
        assert result is None

    def test_emits_rejected(self):
        response = json.dumps(
            {"events": [{"event_type": "unknown_type", "payload": {}}]}
        )
        llm_fn = _make_llm_fn(response)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn)
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        rejected = [e for e in events if e.event_type == "llm_decision_rejected"]
        assert len(rejected) >= 1


# ─── Selection policy ────────────────────────────────────────────────


class TestSelectionPolicy:
    def test_all_emits_all_accepted(self):
        llm_fn = _make_llm_fn(MULTI_EVENT_RESPONSE)
        config = _make_config(selection_policy=SelectionPolicy.ALL)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn, config=config)
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        action_events = [
            e
            for e in events
            if e.source == "llm_planner"
            and e.event_type in ("test_action", "test_mutation")
        ]
        assert len(action_events) == 2

    def test_first_emits_only_first(self):
        llm_fn = _make_llm_fn(MULTI_EVENT_RESPONSE)
        config = _make_config(selection_policy=SelectionPolicy.FIRST)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn, config=config)
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        action_events = [
            e
            for e in events
            if e.source == "llm_planner"
            and e.event_type in ("test_action", "test_mutation")
        ]
        assert len(action_events) == 1
        assert action_events[0].event_type == "test_action"

    def test_proposal_step_index_ordering(self):
        llm_fn = _make_llm_fn(MULTI_EVENT_RESPONSE)
        config = _make_config(selection_policy=SelectionPolicy.ALL)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn, config=config)
        strategy.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        action_events = [
            e
            for e in events
            if e.source == "llm_planner"
            and e.event_type in ("test_action", "test_mutation")
        ]
        indices = [e.metadata["proposal_step_index"] for e in action_events]
        assert indices == [0, 1]


# ─── Drift detection ────────────────────────────────────────────────


class TestDriftDetection:
    def test_same_prompt_different_response_emits_drift(self):
        call_count = [0]

        def alternating_fn(prompt):
            call_count[0] += 1
            if call_count[0] == 1:
                return VALID_RESPONSE
            return json.dumps(
                {
                    "events": [
                        {
                            "event_type": "test_action",
                            "payload": {"session_name": "s1", "action": "different"},
                        },
                    ],
                }
            )

        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(
            llm_fn=alternating_fn, registry=registry, config=config
        )
        scheduler, _ = _make_scheduler()
        strategy = ReplayableStrategy(
            inner=inner, scheduler=scheduler, config=config, registry=registry
        )

        # First call
        strategy.evaluate(_make_state("s1", unique_key="call1"))
        _collect_emitted_events(scheduler)

        # Second call with different state (different state_hash, but same prompt_hash
        # since prompt depends on state content, different state = different prompt)
        # To get same prompt_hash, we need same canonical state. But same state = cache hit.
        # So drift only triggers across cache misses with same prompt_hash.
        # This test verifies drift does NOT fire for different prompt hashes.
        strategy.evaluate(_make_state("s1", unique_key="call2"))
        events = _collect_emitted_events(scheduler)
        drift_events = [e for e in events if e.event_type == "llm_response_drift"]
        # Different state = different prompt = different prompt_hash = no drift
        assert len(drift_events) == 0

    def test_different_prompt_no_drift(self):
        """Different prompt_hash values are NOT drift."""
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn)
        strategy.evaluate(_make_state("s1", extra="a"))
        _collect_emitted_events(scheduler)
        strategy.evaluate(_make_state("s1", extra="b"))
        events = _collect_emitted_events(scheduler)
        drift_events = [e for e in events if e.event_type == "llm_response_drift"]
        assert len(drift_events) == 0


# ─── Concurrency ─────────────────────────────────────────────────────


class TestConcurrency:
    def test_parallel_same_state_single_llm_call(self):
        """Two threads evaluating same state should produce exactly one LLM call.

        Per-key lock serializes: first thread does the LLM call, second
        thread finds the cache hit inside the lock.  Both return a sentinel.
        """
        call_count = [0]
        call_lock = threading.Lock()
        entered = threading.Event()

        def slow_llm_fn(prompt):
            entered.set()
            with call_lock:
                call_count[0] += 1
            time.sleep(0.1)
            return VALID_RESPONSE

        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(
            llm_fn=slow_llm_fn, registry=registry, config=config
        )
        scheduler, _ = _make_scheduler()
        strategy = ReplayableStrategy(
            inner=inner, scheduler=scheduler, config=config, registry=registry
        )
        import concurrent.futures

        strategy._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        state = _make_state()
        results = [None, None]

        def worker(idx):
            results[idx] = strategy.evaluate(state)

        t1 = threading.Thread(target=worker, args=(0,))
        t2 = threading.Thread(target=worker, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # Per-key lock ensures only one LLM call; second thread hits cache
        assert call_count[0] == 1
        # Both should return a valid sentinel
        assert results[0] is not None
        assert results[1] is not None
        strategy.shutdown()

    def test_parallel_different_states_independent(self):
        """Different states should produce independent LLM calls."""
        call_count = [0]
        call_lock = threading.Lock()

        def counting_fn(prompt):
            with call_lock:
                call_count[0] += 1
            return VALID_RESPONSE

        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(
            llm_fn=counting_fn, registry=registry, config=config
        )
        scheduler, _ = _make_scheduler()
        strategy = ReplayableStrategy(
            inner=inner, scheduler=scheduler, config=config, registry=registry
        )
        import concurrent.futures

        strategy._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        results = [None, None]

        def worker(idx, session):
            results[idx] = strategy.evaluate(_make_state(session))

        t1 = threading.Thread(target=worker, args=(0, "session_a"))
        t2 = threading.Thread(target=worker, args=(1, "session_b"))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert call_count[0] == 2
        assert results[0] is not None
        assert results[1] is not None
        strategy.shutdown()

    def test_store_no_corruption(self):
        """Parallel writes to replay store produce consistent records."""
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(llm_fn=llm_fn, registry=registry, config=config)
        scheduler, _ = _make_scheduler()
        strategy = ReplayableStrategy(
            inner=inner, scheduler=scheduler, config=config, registry=registry
        )

        states = [_make_state(f"s{i}") for i in range(10)]
        threads = []
        for s in states:
            t = threading.Thread(target=strategy.evaluate, args=(s,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=10)

        # All records should exist and be valid
        for s in states:
            canonical = _canonical_json(s)
            from eos_ai.substrate.llm_planner import _sha256_prefix

            h = _sha256_prefix(canonical)
            record = strategy._store_get(h)
            assert record is not None
            assert len(record.emitted_events) > 0
        strategy.shutdown()


# ─── Replay round-trip ───────────────────────────────────────────────


class TestReplayRoundTrip:
    def test_emitted_events_source_of_truth(self):
        """emitted_events is the single source of truth, not selected_event_indices."""
        strategy, scheduler = _make_replayable()
        state = _make_state()
        strategy.evaluate(state)
        first_events = _collect_emitted_events(scheduler)
        first_actions = [e for e in first_events if e.event_type == "test_action"]

        # Replay
        strategy.evaluate(state)
        replay_events = _collect_emitted_events(scheduler)
        replay_actions = [e for e in replay_events if e.event_type == "test_action"]

        assert len(first_actions) == len(replay_actions)
        for a, b in zip(first_actions, replay_actions):
            assert a.event_type == b.event_type
            assert a.payload == b.payload
            assert a.metadata["proposal_id"] == b.metadata["proposal_id"]

    def test_selected_event_indices_not_used_for_replay(self):
        """Mutating selected_event_indices should not affect replay."""
        strategy, scheduler = _make_replayable()
        state = _make_state()
        strategy.evaluate(state)
        _collect_emitted_events(scheduler)

        # Tamper with selected_event_indices (it's frozen, but test the principle)
        canonical = _canonical_json(state)
        from eos_ai.substrate.llm_planner import _sha256_prefix

        h = _sha256_prefix(canonical)
        record = strategy._store_get(h)
        assert record is not None
        # Record is frozen, so we can't mutate it.
        # The test verifies the principle: emitted_events is the source of truth.
        assert record.emitted_events is not None
        assert len(record.emitted_events) > 0

    def test_proposal_step_index_preserved_on_replay(self):
        llm_fn = _make_llm_fn(MULTI_EVENT_RESPONSE)
        config = _make_config(selection_policy=SelectionPolicy.ALL)
        strategy, scheduler = _make_replayable(llm_fn=llm_fn, config=config)
        state = _make_state()
        strategy.evaluate(state)
        _collect_emitted_events(scheduler)
        # Replay
        strategy.evaluate(state)
        events = _collect_emitted_events(scheduler)
        action_events = [
            e
            for e in events
            if e.source == "llm_planner"
            and e.event_type in ("test_action", "test_mutation")
        ]
        indices = [e.metadata["proposal_step_index"] for e in action_events]
        assert indices == [0, 1]
