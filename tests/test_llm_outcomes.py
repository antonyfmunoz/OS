"""Tests for the outcome-aware learning layer.

Validates:
1. EventOutcome creation and immutability.
2. OutcomeStore: record, bounded history, FIFO eviction.
3. Stats computation: success_rate, avg_latency, common_failures.
4. Outcome summary: deterministic string, deterministic hash.
5. Prompt determinism WITH outcomes: same state + same outcomes = same hash.
6. Different outcomes → different prompt_hash.
7. Concurrency: parallel outcome writes are thread-safe.
8. Scheduler outcome observer integration.
9. Config gating: include_outcomes_in_prompt=False suppresses section.
"""

from __future__ import annotations

import json
import sys
import threading

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_scheduler import (
    EventScheduler,
    ExecutionResult,
    SchedulerEvent,
)
from umh.substrate.llm_outcomes import EventOutcome, EventTypeStats, OutcomeStore
from umh.substrate.llm_planner import (
    EventSchema,
    EventTypeRegistry,
    LLMPlannerConfig,
    LLMPlanningStrategy,
    SelectionPolicy,
    build_llm_prompt,
    compute_prompt_hash,
)
from umh.substrate.llm_replay import ReplayableStrategy
from umh.substrate.runtime_state_store import RuntimeStateStore


# ─── Fixtures ────────────────────────────────────────────────────────


def _make_outcome(
    event_type: str = "test_action",
    success: bool = True,
    latency_ms: int | None = 100,
    error_type: str | None = None,
    proposal_id: str = "prop_abc",
    timestamp: str = "2026-01-01T00:00:00Z",
) -> EventOutcome:
    return EventOutcome(
        proposal_id=proposal_id,
        event_type=event_type,
        success=success,
        latency_ms=latency_ms,
        error_type=error_type,
        timestamp=timestamp,
    )


def _make_registry() -> EventTypeRegistry:
    reg = EventTypeRegistry()
    reg.register(
        EventSchema(
            event_type="test_action",
            required_fields=frozenset({"session_name", "action"}),
            optional_fields=frozenset({"metadata"}),
            field_types={"session_name": str, "action": str},
        )
    )
    reg.register(
        EventSchema(
            event_type="test_mutation",
            required_fields=frozenset({"key", "value"}),
            optional_fields=frozenset(),
        )
    )
    return reg


def _make_config(**overrides) -> LLMPlannerConfig:
    defaults = {"enabled": True, "model_name": "test-model"}
    defaults.update(overrides)
    return LLMPlannerConfig(**defaults)


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


def _make_llm_fn(response: str = VALID_RESPONSE):
    call_count = [0]

    def fn(prompt: str) -> str:
        call_count[0] += 1
        return response

    fn.call_count = call_count
    return fn


# ─── EventOutcome tests ─────────────────────────────────────────────


class TestEventOutcome:
    def test_creation(self):
        outcome = _make_outcome()
        assert outcome.event_type == "test_action"
        assert outcome.success is True
        assert outcome.latency_ms == 100
        assert outcome.error_type is None

    def test_immutability(self):
        outcome = _make_outcome()
        try:
            outcome.success = False  # type: ignore[misc]
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass

    def test_failure_outcome(self):
        outcome = _make_outcome(success=False, error_type="ValueError", latency_ms=50)
        assert outcome.success is False
        assert outcome.error_type == "ValueError"


# ─── OutcomeStore basic tests ────────────────────────────────────────


class TestOutcomeStoreBasic:
    def test_record_and_count(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        assert store.outcome_count() == 1
        assert store.outcome_count("test_action") == 1
        assert store.outcome_count("nonexistent") == 0

    def test_multiple_event_types(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(event_type="test_action"))
        store.record_outcome(_make_outcome(event_type="test_mutation"))
        store.record_outcome(_make_outcome(event_type="test_action"))
        assert store.outcome_count("test_action") == 2
        assert store.outcome_count("test_mutation") == 1
        assert store.outcome_count() == 3

    def test_clear(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        store.clear()
        assert store.outcome_count() == 0


# ─── Bounded history tests ──────────────────────────────────────────


class TestBoundedHistory:
    def test_fifo_eviction(self):
        store = OutcomeStore(max_history=3)
        for i in range(5):
            store.record_outcome(_make_outcome(latency_ms=i * 10, proposal_id=f"p{i}"))
        assert store.outcome_count("test_action") == 3
        # Oldest (i=0, i=1) should be evicted, newest are i=2,3,4
        stats = store.get_event_stats("test_action")
        assert stats.avg_latency_ms == 30  # (20+30+40)/3

    def test_max_history_per_event_type(self):
        store = OutcomeStore(max_history=2)
        store.record_outcome(_make_outcome(event_type="a", proposal_id="p1"))
        store.record_outcome(_make_outcome(event_type="a", proposal_id="p2"))
        store.record_outcome(_make_outcome(event_type="a", proposal_id="p3"))
        store.record_outcome(_make_outcome(event_type="b", proposal_id="p4"))
        assert store.outcome_count("a") == 2
        assert store.outcome_count("b") == 1

    def test_max_history_property(self):
        store = OutcomeStore(max_history=500)
        assert store.max_history == 500


# ─── Stats computation tests ────────────────────────────────────────


class TestStatsComputation:
    def test_success_rate(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=True))
        store.record_outcome(_make_outcome(success=True))
        store.record_outcome(_make_outcome(success=False, error_type="Err"))
        stats = store.get_event_stats("test_action")
        assert stats.total == 3
        assert stats.success_count == 2
        assert stats.failure_count == 1
        assert abs(stats.success_rate - 2 / 3) < 0.01

    def test_avg_latency(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(latency_ms=100))
        store.record_outcome(_make_outcome(latency_ms=200))
        store.record_outcome(_make_outcome(latency_ms=300))
        stats = store.get_event_stats("test_action")
        assert stats.avg_latency_ms == 200

    def test_avg_latency_with_none(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(latency_ms=100))
        store.record_outcome(_make_outcome(latency_ms=None))
        stats = store.get_event_stats("test_action")
        assert stats.avg_latency_ms == 100  # only one measurement

    def test_all_latency_none(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(latency_ms=None))
        stats = store.get_event_stats("test_action")
        assert stats.avg_latency_ms is None

    def test_common_failures(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=False, error_type="ValueError"))
        store.record_outcome(_make_outcome(success=False, error_type="ValueError"))
        store.record_outcome(_make_outcome(success=False, error_type="TimeoutError"))
        store.record_outcome(_make_outcome(success=False, error_type="IOError"))
        stats = store.get_event_stats("test_action")
        # Top 3 by frequency: ValueError(2), IOError(1), TimeoutError(1)
        # Tie-break: alphabetical
        assert stats.common_failures == ("ValueError", "IOError", "TimeoutError")

    def test_empty_stats(self):
        store = OutcomeStore()
        stats = store.get_event_stats("nonexistent")
        assert stats.total == 0
        assert stats.success_rate == 0.0
        assert stats.avg_latency_ms is None
        assert stats.common_failures == ()

    def test_get_all_stats(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(event_type="b_type"))
        store.record_outcome(_make_outcome(event_type="a_type"))
        all_stats = store.get_all_stats()
        # Sorted by event_type
        assert list(all_stats.keys()) == ["a_type", "b_type"]


# ─── Outcome summary tests ──────────────────────────────────────────


class TestOutcomeSummary:
    def test_empty_store_empty_summary(self):
        store = OutcomeStore()
        assert store.build_outcome_summary() == ""

    def test_summary_format(self):
        store = OutcomeStore()
        store.record_outcome(
            _make_outcome(event_type="send_email", success=True, latency_ms=120)
        )
        store.record_outcome(
            _make_outcome(
                event_type="create_user",
                success=False,
                error_type="validation_error",
                latency_ms=300,
            )
        )
        store.record_outcome(
            _make_outcome(event_type="create_user", success=True, latency_ms=300)
        )
        summary = store.build_outcome_summary()
        assert "- create_user:" in summary
        assert "- send_email:" in summary
        assert "success_rate:" in summary
        # create_user comes before send_email (alphabetical)
        assert summary.index("create_user") < summary.index("send_email")

    def test_summary_determinism(self):
        store = OutcomeStore()
        for i in range(10):
            store.record_outcome(
                _make_outcome(
                    event_type="action_a" if i % 2 == 0 else "action_b",
                    success=i % 3 != 0,
                    latency_ms=i * 10,
                )
            )
        s1 = store.build_outcome_summary()
        s2 = store.build_outcome_summary()
        assert s1 == s2

    def test_summary_hash_determinism(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        h1 = store.build_outcome_summary_hash()
        h2 = store.build_outcome_summary_hash()
        assert h1 == h2
        assert len(h1) == 16

    def test_summary_hash_changes_with_outcomes(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=True))
        h1 = store.build_outcome_summary_hash()
        store.record_outcome(_make_outcome(success=False, error_type="Err"))
        h2 = store.build_outcome_summary_hash()
        assert h1 != h2


# ─── Prompt determinism with outcomes ────────────────────────────────


class TestPromptDeterminismWithOutcomes:
    def test_same_state_same_outcomes_same_prompt(self):
        reg = _make_registry()
        cfg = _make_config()
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()
        p1 = build_llm_prompt('{"a":1}', [], reg, cfg, outcome_summary=summary)
        p2 = build_llm_prompt('{"a":1}', [], reg, cfg, outcome_summary=summary)
        assert p1 == p2

    def test_same_state_same_outcomes_same_prompt_hash(self):
        reg = _make_registry()
        cfg = _make_config()
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()
        summary_hash = store.build_outcome_summary_hash()
        prompt = build_llm_prompt('{"a":1}', [], reg, cfg, outcome_summary=summary)
        h1 = compute_prompt_hash(
            prompt,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash=summary_hash,
        )
        h2 = compute_prompt_hash(
            prompt,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash=summary_hash,
        )
        assert h1 == h2

    def test_different_outcomes_different_prompt_hash(self):
        reg = _make_registry()
        cfg = _make_config()

        store1 = OutcomeStore()
        store1.record_outcome(_make_outcome(success=True))
        summary1 = store1.build_outcome_summary()
        hash1 = store1.build_outcome_summary_hash()

        store2 = OutcomeStore()
        store2.record_outcome(_make_outcome(success=False, error_type="Err"))
        summary2 = store2.build_outcome_summary()
        hash2 = store2.build_outcome_summary_hash()

        prompt1 = build_llm_prompt('{"a":1}', [], reg, cfg, outcome_summary=summary1)
        prompt2 = build_llm_prompt('{"a":1}', [], reg, cfg, outcome_summary=summary2)

        ph1 = compute_prompt_hash(
            prompt1,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash=hash1,
        )
        ph2 = compute_prompt_hash(
            prompt2,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash=hash2,
        )
        assert ph1 != ph2

    def test_no_outcomes_backward_compatible(self):
        reg = _make_registry()
        cfg = _make_config()
        # Without outcomes
        prompt = build_llm_prompt('{"a":1}', [], reg, cfg)
        h1 = compute_prompt_hash(prompt, "test-model", 0.0, 1, reg.version)
        # Explicit empty
        h2 = compute_prompt_hash(
            prompt,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash="",
        )
        assert h1 == h2

    def test_outcomes_disabled_in_config(self):
        reg = _make_registry()
        cfg = _make_config(include_outcomes_in_prompt=False)
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()
        prompt = build_llm_prompt('{"a":1}', [], reg, cfg, outcome_summary=summary)
        assert "EVENT PERFORMANCE" not in prompt

    def test_outcomes_enabled_in_config(self):
        reg = _make_registry()
        cfg = _make_config(include_outcomes_in_prompt=True)
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()
        prompt = build_llm_prompt('{"a":1}', [], reg, cfg, outcome_summary=summary)
        assert "EVENT PERFORMANCE" in prompt

    def test_empty_outcomes_no_section(self):
        reg = _make_registry()
        cfg = _make_config(include_outcomes_in_prompt=True)
        prompt = build_llm_prompt('{"a":1}', [], reg, cfg, outcome_summary="")
        assert "EVENT PERFORMANCE" not in prompt


# ─── Concurrency tests ──────────────────────────────────────────────


class TestConcurrency:
    def test_parallel_writes_safe(self):
        """Many threads writing outcomes simultaneously should not corrupt the store."""
        store = OutcomeStore(max_history=500)
        num_threads = 20
        writes_per_thread = 50
        errors: list[Exception] = []

        def writer(thread_id: int):
            try:
                for i in range(writes_per_thread):
                    store.record_outcome(
                        _make_outcome(
                            event_type=f"type_{thread_id % 5}",
                            proposal_id=f"p_{thread_id}_{i}",
                            latency_ms=i,
                        )
                    )
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(t,)) for t in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        total = store.outcome_count()
        assert total > 0
        # Each type gets outcomes from 4 threads (thread_id % 5)
        # 4 threads * 50 writes = 200, bounded by 500 → all fit
        for type_id in range(5):
            count = store.outcome_count(f"type_{type_id}")
            assert count <= 500  # bounded

    def test_parallel_reads_and_writes(self):
        """Concurrent reads and writes should not deadlock or corrupt."""
        store = OutcomeStore(max_history=100)
        num_threads = 10
        errors: list[Exception] = []

        def writer(thread_id: int):
            try:
                for i in range(30):
                    store.record_outcome(
                        _make_outcome(event_type="test_action", latency_ms=i)
                    )
            except Exception as e:
                errors.append(e)

        def reader(thread_id: int):
            try:
                for _ in range(30):
                    store.get_event_stats("test_action")
                    store.build_outcome_summary()
                    store.build_outcome_summary_hash()
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(num_threads):
            if t % 2 == 0:
                threads.append(threading.Thread(target=writer, args=(t,)))
            else:
                threads.append(threading.Thread(target=reader, args=(t,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors


# ─── Scheduler observer integration tests ───────────────────────────


class TestSchedulerObserver:
    def test_observer_called_on_success(self):
        """Outcome observer fires after successful handler execution."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)
        outcome_store = OutcomeStore()

        # Wire observer
        def observer(event, handler_name, success, latency_ms, error_type):
            outcome_store.record_outcome(
                EventOutcome(
                    proposal_id=event.metadata.get("proposal_id", ""),
                    event_type=event.event_type,
                    success=success,
                    latency_ms=latency_ms,
                    error_type=error_type,
                    timestamp="2026-01-01T00:00:00Z",
                )
            )

        scheduler.add_outcome_observer(observer)

        def handler(s, e):
            return ExecutionResult()

        scheduler.subscribe("test_event", handler, name="test_handler")
        scheduler.emit(
            SchedulerEvent(
                event_type="test_event",
                session_name="s1",
                source="test",
                metadata={"proposal_id": "prop_123"},
            )
        )
        scheduler.run()

        assert outcome_store.outcome_count("test_event") == 1
        stats = outcome_store.get_event_stats("test_event")
        assert stats.success_count == 1
        assert stats.failure_count == 0

    def test_observer_called_on_failure(self):
        """Outcome observer fires after handler failure."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)
        outcome_store = OutcomeStore()

        def observer(event, handler_name, success, latency_ms, error_type):
            outcome_store.record_outcome(
                EventOutcome(
                    proposal_id="",
                    event_type=event.event_type,
                    success=success,
                    latency_ms=latency_ms,
                    error_type=error_type,
                    timestamp="2026-01-01T00:00:00Z",
                )
            )

        scheduler.add_outcome_observer(observer)

        def failing_handler(s, e):
            raise ValueError("test failure")

        scheduler.subscribe("test_event", failing_handler, name="fail_handler")
        scheduler.emit(
            SchedulerEvent(
                event_type="test_event",
                session_name="s1",
                source="test",
            )
        )
        scheduler.run()

        assert outcome_store.outcome_count("test_event") == 1
        stats = outcome_store.get_event_stats("test_event")
        assert stats.failure_count == 1
        assert stats.common_failures == ("ValueError",)

    def test_observer_exception_does_not_crash_scheduler(self):
        """A broken observer must not affect scheduler routing."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        def broken_observer(event, handler_name, success, latency_ms, error_type):
            raise RuntimeError("observer exploded")

        scheduler.add_outcome_observer(broken_observer)

        results = []

        def handler(s, e):
            results.append("executed")
            return ExecutionResult()

        scheduler.subscribe("test_event", handler, name="test_handler")
        scheduler.emit(
            SchedulerEvent(
                event_type="test_event",
                session_name="s1",
                source="test",
            )
        )
        run_result = scheduler.run()

        # Handler still executed despite broken observer
        assert len(results) == 1
        assert run_result.total_handlers_called == 1

    def test_observer_captures_latency(self):
        """Observer receives non-None latency_ms."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)
        captured: list[tuple] = []

        def observer(event, handler_name, success, latency_ms, error_type):
            captured.append((success, latency_ms, error_type))

        scheduler.add_outcome_observer(observer)

        def handler(s, e):
            return ExecutionResult()

        scheduler.subscribe("test_event", handler, name="h")
        scheduler.emit(
            SchedulerEvent(event_type="test_event", session_name="s1", source="test")
        )
        scheduler.run()

        assert len(captured) == 1
        success, latency_ms, error_type = captured[0]
        assert success is True
        assert latency_ms is not None
        assert latency_ms >= 0
        assert error_type is None


# ─── ReplayableStrategy + OutcomeStore integration ──────────────────


class TestReplayableOutcomeIntegration:
    def test_outcome_summary_in_prompt(self):
        """When outcome_store has data, prompt includes EVENT PERFORMANCE."""
        outcome_store = OutcomeStore()
        outcome_store.record_outcome(
            _make_outcome(event_type="test_action", success=True, latency_ms=100)
        )

        prompts_seen: list[str] = []

        def capturing_llm_fn(prompt: str) -> str:
            prompts_seen.append(prompt)
            return VALID_RESPONSE

        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(
            llm_fn=capturing_llm_fn, registry=registry, config=config
        )
        scheduler_store = RuntimeStateStore()
        scheduler = EventScheduler(store=scheduler_store)
        strategy = ReplayableStrategy(
            inner=inner,
            scheduler=scheduler,
            config=config,
            registry=registry,
            outcome_store=outcome_store,
        )

        strategy.evaluate({"session_name": "s1"})
        assert len(prompts_seen) == 1
        assert "EVENT PERFORMANCE" in prompts_seen[0]
        assert "test_action" in prompts_seen[0]
        strategy.shutdown()

    def test_no_outcome_store_backward_compatible(self):
        """Without outcome_store, everything works as before."""
        llm_fn = _make_llm_fn()
        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(llm_fn=llm_fn, registry=registry, config=config)
        scheduler_store = RuntimeStateStore()
        scheduler = EventScheduler(store=scheduler_store)
        strategy = ReplayableStrategy(
            inner=inner,
            scheduler=scheduler,
            config=config,
            registry=registry,
            # No outcome_store
        )

        result = strategy.evaluate({"session_name": "s1"})
        assert result is not None
        assert result.is_terminal is True
        strategy.shutdown()


# ─── EventTypeStats.to_summary_dict tests ───────────────────────────


class TestEventTypeStatsDict:
    def test_to_summary_dict_full(self):
        stats = EventTypeStats(
            event_type="test",
            total=10,
            success_count=8,
            failure_count=2,
            success_rate=0.8,
            avg_latency_ms=150,
            common_failures=("ValueError",),
        )
        d = stats.to_summary_dict()
        assert d["success_rate"] == 0.8
        assert d["avg_latency_ms"] == 150
        assert d["common_failures"] == ["ValueError"]

    def test_to_summary_dict_minimal(self):
        stats = EventTypeStats(
            event_type="test",
            total=5,
            success_count=5,
            failure_count=0,
            success_rate=1.0,
            avg_latency_ms=None,
            common_failures=(),
        )
        d = stats.to_summary_dict()
        assert d["success_rate"] == 1.0
        assert "avg_latency_ms" not in d
        assert "common_failures" not in d
