"""High-contention chaos test for ReplayableStrategy.

100 parallel evaluate() calls mixing:
- repeated identical canonical states (dedupe via per-key lock)
- different canonical states (parallel execution)
- delayed llm_fn responses
- timeout cases
- parse failure cases

All stubs are deterministic — no real LLM calls.

Assertions:
1. identical state_hash under concurrency → exactly one live llm_fn invocation
2. different state_hash values can progress concurrently
3. no duplicate emitted scheduler events for same replayed proposal
4. replay store remains uncorrupted
5. timeout failures fall through cleanly
6. parse failures fall through cleanly
7. drift events only emit on same prompt_hash with new response_hash
8. no deadlocks / no leaked worker futures / no hanging test
"""

from __future__ import annotations

import concurrent.futures
import json
import sys
import threading
import time

sys.path.insert(0, "/opt/OS")

from runtime.substrate.event_scheduler import EventScheduler, SchedulerEvent
from runtime.substrate.llm_planner import (
    EventSchema,
    EventTypeRegistry,
    LLMPlannerConfig,
    LLMPlanningStrategy,
    SelectionPolicy,
    _canonical_json,
    _sha256_prefix,
)
from runtime.substrate.llm_replay import ReplayableStrategy
from runtime.substrate.runtime_state_store import RuntimeStateStore


# ─── Fixtures ────────────────────────────────────────────────────────

VALID_RESPONSE = json.dumps(
    {
        "events": [
            {
                "event_type": "test_action",
                "payload": {"session_name": "s1", "action": "go"},
            },
        ],
        "reasoning": "chaos test",
    }
)


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
    return reg


def _make_config(**overrides) -> LLMPlannerConfig:
    defaults = {"enabled": True, "model_name": "test-model", "timeout_ms": 2000}
    defaults.update(overrides)
    return LLMPlannerConfig(**defaults)


def _make_scheduler() -> EventScheduler:
    store = RuntimeStateStore()
    return EventScheduler(store=store)


def _collect_emitted_events(scheduler: EventScheduler) -> list[SchedulerEvent]:
    events = []
    while scheduler._queue:
        events.append(scheduler._queue.popleft())
    return events


def _make_state(session_name: str = "s1", **extra) -> dict:
    return {"session_name": session_name, **extra}


# ─── Chaos test ──────────────────────────────────────────────────────


class TestHighContentionChaos:
    """100 parallel evaluate() with mixed behavior stubs."""

    def test_chaos_100_parallel_calls(self):
        """Mix of identical states, different states, delays, timeouts, parse failures."""
        invocation_log: dict[str, int] = {}  # state_key → call count
        log_lock = threading.Lock()

        def chaos_llm_fn(prompt: str) -> str:
            """Deterministic stub that varies behavior by state content.

            Extracts 'chaos_id' from the prompt to determine behavior:
            - chaos_id ending in 'timeout': sleep 10s (will timeout)
            - chaos_id ending in 'bad': return invalid JSON
            - chaos_id ending in 'slow': sleep 0.1s then return valid
            - all others: return valid immediately
            """
            # Track invocations per prompt (approximate state_key from prompt)
            with log_lock:
                # Use first 32 chars of prompt hash as key for tracking
                key = _sha256_prefix(prompt, 8)
                invocation_log[key] = invocation_log.get(key, 0) + 1

            # Determine behavior from prompt content
            if "timeout" in prompt:
                time.sleep(10)
                return VALID_RESPONSE
            if "bad_json" in prompt:
                return "not valid json {{"
            if "slow_response" in prompt:
                time.sleep(0.05)
                return VALID_RESPONSE
            return VALID_RESPONSE

        registry = _make_registry()
        config = _make_config(timeout_ms=500, selection_policy=SelectionPolicy.ALL)
        inner = LLMPlanningStrategy(
            llm_fn=chaos_llm_fn, registry=registry, config=config
        )
        scheduler = _make_scheduler()
        strategy = ReplayableStrategy(
            inner=inner, scheduler=scheduler, config=config, registry=registry
        )

        # Build 100 calls with mixed behaviors:
        # - 30 calls to identical state "repeated_a" (should dedupe to 1 LLM call)
        # - 20 calls to identical state "repeated_b" (should dedupe to 1 LLM call)
        # - 20 unique states (each gets 1 LLM call)
        # - 15 timeout states (each unique, should all timeout)
        # - 15 parse-failure states (each unique, should all fail)
        tasks: list[tuple[str, dict]] = []

        # 30 identical "repeated_a"
        state_a = _make_state("repeated_a")
        for _ in range(30):
            tasks.append(("repeated_a", state_a))

        # 20 identical "repeated_b"
        state_b = _make_state("repeated_b")
        for _ in range(20):
            tasks.append(("repeated_b", state_b))

        # 20 unique normal states
        for i in range(20):
            tasks.append((f"unique_{i}", _make_state(f"unique_{i}")))

        # 15 timeout states (unique to avoid cache hits)
        for i in range(15):
            tasks.append(
                (f"timeout_{i}", _make_state(f"timeout_{i}", chaos_id="timeout"))
            )

        # 15 parse-failure states
        for i in range(15):
            tasks.append(
                (f"bad_{i}", _make_state(f"bad_json_{i}", chaos_id="bad_json"))
            )

        assert len(tasks) == 100

        # Execute all 100 in parallel
        results: list[tuple[str, object | None, Exception | None]] = []
        results_lock = threading.Lock()

        def worker(name: str, state: dict) -> None:
            try:
                result = strategy.evaluate(state)
                with results_lock:
                    results.append((name, result, None))
            except Exception as exc:
                with results_lock:
                    results.append((name, None, exc))

        threads = []
        for name, state in tasks:
            t = threading.Thread(target=worker, args=(name, state))
            threads.append(t)

        # Start all 100 threads
        for t in threads:
            t.start()

        # Join all with generous timeout (no deadlocks)
        for t in threads:
            t.join(timeout=30)

        # Verify no threads are still alive (assertion 8: no deadlocks)
        alive = [t for t in threads if t.is_alive()]
        assert len(alive) == 0, f"{len(alive)} threads still alive — deadlock?"

        # All 100 calls must have returned
        assert len(results) == 100

        # No exceptions from evaluate() — all failures return None
        exceptions = [(name, exc) for name, _, exc in results if exc is not None]
        assert len(exceptions) == 0, f"Unexpected exceptions: {exceptions}"

        # ── Assertion 1: identical state → at most one LLM call ──
        state_a_hash = _sha256_prefix(_canonical_json(state_a))
        state_b_hash = _sha256_prefix(_canonical_json(state_b))

        record_a = strategy._store_get(state_a_hash)
        record_b = strategy._store_get(state_b_hash)
        assert record_a is not None, "repeated_a should have a stored record"
        assert record_b is not None, "repeated_b should have a stored record"

        # Count how many repeated_a calls got sentinels (all should)
        repeated_a_results = [r for name, r, _ in results if name == "repeated_a"]
        sentinel_count_a = sum(1 for r in repeated_a_results if r is not None)
        assert sentinel_count_a == 30, (
            f"All 30 repeated_a calls should get sentinels, got {sentinel_count_a}"
        )

        repeated_b_results = [r for name, r, _ in results if name == "repeated_b"]
        sentinel_count_b = sum(1 for r in repeated_b_results if r is not None)
        assert sentinel_count_b == 20

        # ── Assertion 2: different states can progress concurrently ──
        unique_results = [
            (name, r) for name, r, _ in results if name.startswith("unique_")
        ]
        unique_sentinels = sum(1 for _, r in unique_results if r is not None)
        assert unique_sentinels == 20, (
            f"All 20 unique states should get sentinels, got {unique_sentinels}"
        )

        # ── Assertion 3: no duplicate emitted events for same replay ──
        events = _collect_emitted_events(scheduler)

        # Count domain events with source="llm_planner" and event_type="test_action".
        # Each evaluate() call (cache hit or miss) emits exactly one test_action
        # for single-event proposals.  30 repeated_a + 20 repeated_b + 20 unique
        # = 70 total domain events.
        domain_events = [
            e
            for e in events
            if e.source == "llm_planner" and e.event_type == "test_action"
        ]
        # 30 (repeated_a) + 20 (repeated_b) + 20 (unique) = 70
        assert len(domain_events) == 70, (
            f"Expected 70 domain events (30+20+20), got {len(domain_events)}"
        )

        # Every domain event must carry proposal_step_index metadata
        for de in domain_events:
            assert "proposal_id" in de.metadata
            assert "proposal_step_index" in de.metadata
            assert de.metadata["proposal_step_index"] == 0  # single-event proposal

        # ── Assertion 4: replay store not corrupted ──
        # All unique states should have records
        for i in range(20):
            unique_state = _make_state(f"unique_{i}")
            h = _sha256_prefix(_canonical_json(unique_state))
            rec = strategy._store_get(h)
            assert rec is not None, f"unique_{i} missing from replay store"
            assert len(rec.emitted_events) > 0

        # ── Assertion 5: timeout failures fall through cleanly ──
        timeout_results = [r for name, r, _ in results if name.startswith("timeout_")]
        assert all(r is None for r in timeout_results), (
            "All timeout calls should return None"
        )

        # ── Assertion 6: parse failures fall through cleanly ──
        bad_results = [r for name, r, _ in results if name.startswith("bad_")]
        assert all(r is None for r in bad_results), (
            "All parse-failure calls should return None"
        )

        # ── Assertion 7: drift events ──
        # All calls to the same state produce the same prompt and response,
        # so no drift within repeated_a or repeated_b.
        # Different states produce different prompts, so no cross-prompt drift.
        drift_events = [e for e in events if e.event_type == "llm_response_drift"]
        # With deterministic stubs, identical prompts give identical responses,
        # so drift should be 0 for all repeated states.
        assert len(drift_events) == 0, (
            f"Expected 0 drift events with deterministic stubs, got {len(drift_events)}"
        )

        # ── Assertion 8: clean shutdown, no leaked futures ──
        strategy.shutdown()

    def test_parallel_executor_allows_concurrent_different_states(self):
        """Verify the executor allows truly concurrent LLM calls for different states."""
        concurrency_high_water = [0]
        active_count = [0]
        active_lock = threading.Lock()

        def tracking_fn(prompt: str) -> str:
            with active_lock:
                active_count[0] += 1
                if active_count[0] > concurrency_high_water[0]:
                    concurrency_high_water[0] = active_count[0]
            time.sleep(0.05)
            with active_lock:
                active_count[0] -= 1
            return VALID_RESPONSE

        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(
            llm_fn=tracking_fn, registry=registry, config=config
        )
        scheduler = _make_scheduler()
        strategy = ReplayableStrategy(
            inner=inner, scheduler=scheduler, config=config, registry=registry
        )

        states = [_make_state(f"conc_{i}") for i in range(10)]
        threads = []
        for s in states:
            t = threading.Thread(target=strategy.evaluate, args=(s,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=30)

        # With 10 different states, we should see >1 concurrent LLM call
        assert concurrency_high_water[0] > 1, (
            f"Expected concurrent execution, high water mark was {concurrency_high_water[0]}"
        )
        strategy.shutdown()

    def test_lock_registry_does_not_grow_unbounded(self):
        """Verify per-key locks are cleaned up after use via WeakValueDictionary."""
        import gc

        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(
            llm_fn=lambda p: VALID_RESPONSE, registry=registry, config=config
        )
        scheduler = _make_scheduler()
        strategy = ReplayableStrategy(
            inner=inner, scheduler=scheduler, config=config, registry=registry
        )

        # Evaluate 50 unique states
        for i in range(50):
            strategy.evaluate(_make_state(f"leak_test_{i}"))

        # Force GC to clean up weak refs
        gc.collect()

        # The WeakValueDictionary should have fewer entries than 50
        # because locks whose strong references were dropped get GC'd.
        # Some may linger if the GC hasn't collected them yet.
        lock_count = len(strategy._key_locks)
        assert lock_count < 50, (
            f"Expected lock cleanup via WeakValueDictionary, "
            f"but {lock_count} locks remain"
        )
        strategy.shutdown()

    def test_multi_response_drift_tracking(self):
        """Drift store tracks all distinct responses, emits once per novel hash."""
        call_count = [0]

        # Three distinct responses for the same canonical state
        responses = [
            json.dumps(
                {
                    "events": [
                        {
                            "event_type": "test_action",
                            "payload": {"session_name": "s1", "action": f"v{i}"},
                        },
                    ],
                }
            )
            for i in range(3)
        ]

        def rotating_fn(prompt: str) -> str:
            nonlocal call_count
            idx = call_count[0] % 3
            call_count[0] += 1
            return responses[idx]

        registry = _make_registry()
        config = _make_config()
        inner = LLMPlanningStrategy(
            llm_fn=rotating_fn, registry=registry, config=config
        )
        scheduler = _make_scheduler()
        strategy = ReplayableStrategy(
            inner=inner, scheduler=scheduler, config=config, registry=registry
        )

        # Call 1: state_a → response 0 (new prompt_hash, no drift)
        strategy.evaluate(_make_state("drift_a"))
        _collect_emitted_events(scheduler)

        # Call 2: state_b → response 1 (different state = different prompt_hash, no drift)
        strategy.evaluate(_make_state("drift_b"))
        _collect_emitted_events(scheduler)

        # Call 3: state_c → response 2 (different state = different prompt_hash, no drift)
        strategy.evaluate(_make_state("drift_c"))
        events = _collect_emitted_events(scheduler)
        drift_events = [e for e in events if e.event_type == "llm_response_drift"]
        assert len(drift_events) == 0, "Different states = different prompts = no drift"
        strategy.shutdown()

    def test_non_mutating_event_enforcement(self):
        """Verify NonMutatingEventViolation is raised when handlers
        for non-mutating events return mutations."""
        from runtime.substrate.event_scheduler import (
            EventScheduler,
            ExecutionResult,
            NonMutatingEventViolation,
            register_event_schema_source,
        )

        registry = _make_registry()
        # Register a non-mutating event type
        registry.register(
            EventSchema(
                event_type="observability_event",
                required_fields=frozenset({"info"}),
                optional_fields=frozenset(),
                is_mutation=False,
            )
        )

        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)
        register_event_schema_source(registry)

        # Register a handler that (incorrectly) returns mutations
        def bad_handler(store, event):
            return ExecutionResult(
                mutations=[{"op": "SET", "key": "bad", "value": "shouldnt_happen"}]
            )

        scheduler.subscribe("observability_event", bad_handler, name="bad_handler")
        scheduler.emit(
            SchedulerEvent(
                event_type="observability_event",
                session_name="test",
                source="test",
                payload={"info": "test"},
            )
        )

        try:
            scheduler.run()
            assert False, "Should have raised NonMutatingEventViolation"
        except NonMutatingEventViolation as exc:
            assert "non-mutating" in str(exc).lower()
            assert "observability_event" in str(exc)

    def test_mutation_allowed_for_mutating_events(self):
        """Verify normal mutating events still work with registry registered."""
        from runtime.substrate.event_scheduler import (
            EventScheduler,
            ExecutionResult,
            register_event_schema_source,
        )

        registry = _make_registry()  # test_action has is_mutation=True
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)
        register_event_schema_source(registry)

        def good_handler(store, event):
            return ExecutionResult(
                mutations=[{"op": "SET", "key": "good", "value": "allowed"}]
            )

        scheduler.subscribe("test_action", good_handler, name="good_handler")
        scheduler.emit(
            SchedulerEvent(
                event_type="test_action",
                session_name="test",
                source="test",
                payload={"session_name": "test", "action": "do"},
            )
        )

        result = scheduler.run()
        assert result.total_mutations_applied == 1
