"""Smoke tests for temporal (multi-event) validation.

Verifies:
  1. temporal_init_before_use — detects use before initialization
  2. temporal_single_transition_per_cycle — detects double state change
  3. temporal_idempotency_scope — detects cross-scope key reuse
  4. TemporalRegistry and validate_sequence
  5. build_state_trace correctness
  6. validate_replay_temporal end-to-end
  7. temporal_violations_to_drifts classification
  8. TEMPORAL_VIOLATION priority in ExtendedDriftClass
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.replay_validation import (
    EventLogEntry,
    MutationOp,
    StateMutation,
)
from umh.substrate.spec_validation import (
    DRIFT_PRIORITY,
    ExtendedDriftClass,
    TemporalRegistry,
    TemporalValidationResult,
    build_state_trace,
    highest_priority_drift,
    temporal_idempotency_scope,
    temporal_init_before_use,
    temporal_single_transition_per_cycle,
    temporal_violations_to_drifts,
    validate_replay_temporal,
    validate_sequence,
)

# ─── Helpers ────────────────────────────────────────────────────────────────


def _entry(
    event_type: str,
    payload: dict,
    mutations: list[StateMutation],
    seq: int = 0,
    event_time: str = "2026-04-16T12:00:00Z",
) -> EventLogEntry:
    return EventLogEntry(
        sequence_number=seq,
        event_id=f"evt-{seq}",
        event_type=event_type,
        correlation_id="test",
        payload=payload,
        state_mutations=mutations,
        event_time=event_time,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. INIT BEFORE USE
# ═══════════════════════════════════════════════════════════════════════════


def test_init_before_use_correct():
    """SET before INCREMENT passes."""
    spec = temporal_init_before_use("counter")
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry(
            "init",
            {},
            [StateMutation(key="counter", operation=MutationOp.SET, value=0)],
            seq=0,
        ),
        _entry(
            "increment",
            {},
            [StateMutation(key="counter", operation=MutationOp.INCREMENT, value=1)],
            seq=1,
        ),
    ]
    trace = build_state_trace(entries)
    result = validate_sequence(trace, registry)
    assert result.valid, (
        f"unexpected violations: {[v.detail for v in result.violations]}"
    )
    print("  PASS: init before use — correct order")


def test_init_before_use_violation():
    """INCREMENT before SET is a temporal violation."""
    spec = temporal_init_before_use("counter")
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry(
            "increment",
            {},
            [StateMutation(key="counter", operation=MutationOp.INCREMENT, value=1)],
            seq=0,
        ),
        _entry(
            "init",
            {},
            [StateMutation(key="counter", operation=MutationOp.SET, value=0)],
            seq=1,
        ),
    ]
    trace = build_state_trace(entries)
    result = validate_sequence(trace, registry)
    assert not result.valid
    assert result.specs_violated == 1
    assert len(result.violations) == 1
    v = result.violations[0]
    assert v.spec_name == "init_before_use:counter"
    assert v.first_sequence == 0
    print(f"  PASS: init before use — violation detected: {v.detail}")


def test_init_before_use_no_mutations():
    """Trace with no relevant mutations passes (nothing to violate)."""
    spec = temporal_init_before_use("counter")
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry(
            "unrelated",
            {},
            [StateMutation(key="other_key", operation=MutationOp.SET, value="x")],
            seq=0,
        ),
    ]
    trace = build_state_trace(entries)
    result = validate_sequence(trace, registry)
    assert result.valid
    print("  PASS: init before use — irrelevant mutations pass")


# ═══════════════════════════════════════════════════════════════════════════
# 2. SINGLE TRANSITION PER CYCLE
# ═══════════════════════════════════════════════════════════════════════════


def test_single_transition_correct():
    """One status change per cycle passes."""
    spec = temporal_single_transition_per_cycle("status", cycle_field="cycle_id")
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry(
            "transition",
            {"cycle_id": "c1"},
            [StateMutation(key="status", operation=MutationOp.SET, value="active")],
            seq=0,
        ),
        _entry(
            "transition",
            {"cycle_id": "c2"},
            [StateMutation(key="status", operation=MutationOp.SET, value="closed")],
            seq=1,
        ),
    ]
    trace = build_state_trace(entries, {"status": "idle"})
    result = validate_sequence(trace, registry)
    assert result.valid
    print("  PASS: single transition per cycle — one change per cycle")


def test_single_transition_violation():
    """Two status changes in same cycle is a temporal violation."""
    spec = temporal_single_transition_per_cycle("status", cycle_field="cycle_id")
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry(
            "transition",
            {"cycle_id": "c1"},
            [StateMutation(key="status", operation=MutationOp.SET, value="active")],
            seq=0,
        ),
        _entry(
            "transition",
            {"cycle_id": "c1"},
            [StateMutation(key="status", operation=MutationOp.SET, value="closed")],
            seq=1,
        ),
    ]
    trace = build_state_trace(entries, {"status": "idle"})
    result = validate_sequence(trace, registry)
    assert not result.valid
    assert len(result.violations) == 1
    v = result.violations[0]
    assert "c1" in v.detail
    assert len(v.involved_events) == 2
    assert v.first_sequence == 0
    assert v.last_sequence == 1
    print(f"  PASS: single transition per cycle — violation: {v.detail}")


def test_single_transition_no_cycle_field():
    """Events without cycle_id in payload are ignored."""
    spec = temporal_single_transition_per_cycle("status", cycle_field="cycle_id")
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry(
            "transition",
            {},  # no cycle_id
            [StateMutation(key="status", operation=MutationOp.SET, value="active")],
            seq=0,
        ),
        _entry(
            "transition",
            {},  # no cycle_id
            [StateMutation(key="status", operation=MutationOp.SET, value="closed")],
            seq=1,
        ),
    ]
    trace = build_state_trace(entries, {"status": "idle"})
    result = validate_sequence(trace, registry)
    assert result.valid
    print("  PASS: single transition per cycle — no cycle_id → skip")


# ═══════════════════════════════════════════════════════════════════════════
# 3. IDEMPOTENCY SCOPE
# ═══════════════════════════════════════════════════════════════════════════


def test_idempotency_scope_correct():
    """Different keys across sessions passes."""
    spec = temporal_idempotency_scope(
        idempotency_field="idem_key", scope_field="session_id"
    )
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry("op", {"idem_key": "k1", "session_id": "s1"}, [], seq=0),
        _entry("op", {"idem_key": "k2", "session_id": "s2"}, [], seq=1),
    ]
    trace = build_state_trace(entries)
    result = validate_sequence(trace, registry)
    assert result.valid
    print("  PASS: idempotency scope — different keys pass")


def test_idempotency_scope_same_scope_ok():
    """Same key in same scope is allowed (within-scope, not cross-scope)."""
    spec = temporal_idempotency_scope(
        idempotency_field="idem_key", scope_field="session_id"
    )
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry("op", {"idem_key": "k1", "session_id": "s1"}, [], seq=0),
        _entry("op", {"idem_key": "k1", "session_id": "s1"}, [], seq=1),
    ]
    trace = build_state_trace(entries)
    result = validate_sequence(trace, registry)
    assert result.valid
    print("  PASS: idempotency scope — same scope reuse allowed")


def test_idempotency_scope_violation():
    """Same key across different sessions is a temporal violation."""
    spec = temporal_idempotency_scope(
        idempotency_field="idem_key", scope_field="session_id"
    )
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry("op", {"idem_key": "k1", "session_id": "s1"}, [], seq=0),
        _entry("op", {"idem_key": "k1", "session_id": "s2"}, [], seq=1),
    ]
    trace = build_state_trace(entries)
    result = validate_sequence(trace, registry)
    assert not result.valid
    assert len(result.violations) == 1
    v = result.violations[0]
    assert "k1" in v.detail
    assert "s1" in v.detail and "s2" in v.detail
    print(f"  PASS: idempotency scope — cross-scope violation: {v.detail}")


def test_idempotency_scope_window():
    """Cross-scope reuse outside time window is allowed."""
    spec = temporal_idempotency_scope(
        idempotency_field="idem_key",
        scope_field="session_id",
        window_seconds=60,
    )
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry(
            "op",
            {"idem_key": "k1", "session_id": "s1"},
            [],
            seq=0,
            event_time="2026-04-16T12:00:00Z",
        ),
        _entry(
            "op",
            {"idem_key": "k1", "session_id": "s2"},
            [],
            seq=1,
            event_time="2026-04-16T12:05:00Z",  # 5 min later, outside 60s window
        ),
    ]
    trace = build_state_trace(entries)
    result = validate_sequence(trace, registry)
    assert result.valid
    print("  PASS: idempotency scope — outside time window passes")


def test_idempotency_scope_within_window():
    """Cross-scope reuse within time window is violation."""
    spec = temporal_idempotency_scope(
        idempotency_field="idem_key",
        scope_field="session_id",
        window_seconds=120,
    )
    registry = TemporalRegistry()
    registry.register(spec)

    entries = [
        _entry(
            "op",
            {"idem_key": "k1", "session_id": "s1"},
            [],
            seq=0,
            event_time="2026-04-16T12:00:00Z",
        ),
        _entry(
            "op",
            {"idem_key": "k1", "session_id": "s2"},
            [],
            seq=1,
            event_time="2026-04-16T12:01:00Z",  # 60s later, inside 120s window
        ),
    ]
    trace = build_state_trace(entries)
    result = validate_sequence(trace, registry)
    assert not result.valid
    print("  PASS: idempotency scope — within time window is violation")


# ═══════════════════════════════════════════════════════════════════════════
# 4. BUILD STATE TRACE
# ═══════════════════════════════════════════════════════════════════════════


def test_build_state_trace():
    """State trace captures before/after correctly."""
    entries = [
        _entry(
            "init",
            {},
            [StateMutation(key="x", operation=MutationOp.SET, value=10)],
            seq=0,
        ),
        _entry(
            "inc",
            {},
            [StateMutation(key="x", operation=MutationOp.INCREMENT, value=5)],
            seq=1,
        ),
    ]
    trace = build_state_trace(entries)

    assert len(trace) == 2

    # First entry: {} -> {x: 10}
    e0, before0, after0 = trace[0]
    assert before0 == {}
    assert after0 == {"x": 10}
    assert e0.sequence_number == 0

    # Second entry: {x: 10} -> {x: 15}
    e1, before1, after1 = trace[1]
    assert before1 == {"x": 10}
    assert after1 == {"x": 15}
    assert e1.sequence_number == 1

    print("  PASS: state trace captures before/after correctly")


def test_build_state_trace_with_initial():
    """State trace respects initial_state."""
    entries = [
        _entry(
            "inc",
            {},
            [StateMutation(key="x", operation=MutationOp.INCREMENT, value=1)],
            seq=0,
        ),
    ]
    trace = build_state_trace(entries, initial_state={"x": 100, "y": "kept"})

    e0, before0, after0 = trace[0]
    assert before0 == {"x": 100, "y": "kept"}
    assert after0 == {"x": 101, "y": "kept"}
    print("  PASS: state trace with initial_state")


# ═══════════════════════════════════════════════════════════════════════════
# 5. END-TO-END REPLAY TEMPORAL
# ═══════════════════════════════════════════════════════════════════════════


def test_validate_replay_temporal_e2e():
    """Full replay with temporal validation catches init-before-use."""
    temporal_reg = TemporalRegistry()
    temporal_reg.register(temporal_init_before_use("counter"))

    entries = [
        # INCREMENT without prior SET
        _entry(
            "inc",
            {},
            [StateMutation(key="counter", operation=MutationOp.INCREMENT, value=1)],
            seq=0,
        ),
    ]
    result = validate_replay_temporal(entries, temporal_reg)
    assert not result.valid
    assert len(result.violations) == 1
    print(f"  PASS: e2e replay temporal ({result.summary()})")


# ═══════════════════════════════════════════════════════════════════════════
# 6. TEMPORAL VIOLATIONS TO DRIFTS
# ═══════════════════════════════════════════════════════════════════════════


def test_temporal_violations_to_drifts():
    """Temporal violations convert to ExtendedDrift with TEMPORAL_VIOLATION."""
    temporal_reg = TemporalRegistry()
    temporal_reg.register(temporal_init_before_use("counter"))

    entries = [
        _entry(
            "inc",
            {},
            [StateMutation(key="counter", operation=MutationOp.INCREMENT, value=1)],
            seq=3,
        ),
    ]
    result = validate_replay_temporal(entries, temporal_reg)
    drifts = temporal_violations_to_drifts(result)
    assert len(drifts) == 1
    d = drifts[0]
    assert d.drift_class == ExtendedDriftClass.TEMPORAL_VIOLATION
    assert d.sequence_number == 3
    assert d.event_id == "evt-3"
    print("  PASS: violations → ExtendedDrift with TEMPORAL_VIOLATION")


# ═══════════════════════════════════════════════════════════════════════════
# 7. DRIFT PRIORITY WITH TEMPORAL
# ═══════════════════════════════════════════════════════════════════════════


def test_temporal_priority():
    """TEMPORAL_VIOLATION sits between SPEC_VIOLATION and SEMANTIC."""
    assert DRIFT_PRIORITY.index(
        ExtendedDriftClass.SPEC_VIOLATION
    ) < DRIFT_PRIORITY.index(ExtendedDriftClass.TEMPORAL_VIOLATION)
    assert DRIFT_PRIORITY.index(
        ExtendedDriftClass.TEMPORAL_VIOLATION
    ) < DRIFT_PRIORITY.index(ExtendedDriftClass.SEMANTIC_VIOLATION)

    result = highest_priority_drift(
        [
            ExtendedDriftClass.TEMPORAL_VIOLATION,
            ExtendedDriftClass.HASH_MISMATCH,
        ]
    )
    assert result == ExtendedDriftClass.TEMPORAL_VIOLATION
    print("  PASS: TEMPORAL_VIOLATION priority correct")


# ═══════════════════════════════════════════════════════════════════════════
# 8. MULTIPLE TEMPORAL SPECS TOGETHER
# ═══════════════════════════════════════════════════════════════════════════


def test_multiple_temporal_specs():
    """Multiple temporal specs run in one pass, violations aggregate."""
    registry = TemporalRegistry()
    registry.register(temporal_init_before_use("counter"))
    registry.register(
        temporal_single_transition_per_cycle("status", cycle_field="cycle_id")
    )
    assert len(registry) == 2

    entries = [
        # INCREMENT without SET (init_before_use violation)
        _entry(
            "inc",
            {"cycle_id": "c1"},
            [StateMutation(key="counter", operation=MutationOp.INCREMENT, value=1)],
            seq=0,
        ),
        # Two status changes in same cycle (single_transition violation)
        _entry(
            "trans1",
            {"cycle_id": "c1"},
            [StateMutation(key="status", operation=MutationOp.SET, value="active")],
            seq=1,
        ),
        _entry(
            "trans2",
            {"cycle_id": "c1"},
            [StateMutation(key="status", operation=MutationOp.SET, value="closed")],
            seq=2,
        ),
    ]
    result = validate_replay_temporal(
        entries, registry, initial_state={"status": "idle"}
    )
    assert not result.valid
    assert result.specs_violated == 2
    assert result.specs_checked == 2
    assert len(result.violations) == 2
    print(f"  PASS: multiple specs aggregated ({result.summary()})")


# ═══════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=== TEMPORAL VALIDATION TESTS ===\n")

    print("1. INIT BEFORE USE")
    test_init_before_use_correct()
    test_init_before_use_violation()
    test_init_before_use_no_mutations()

    print("\n2. SINGLE TRANSITION PER CYCLE")
    test_single_transition_correct()
    test_single_transition_violation()
    test_single_transition_no_cycle_field()

    print("\n3. IDEMPOTENCY SCOPE")
    test_idempotency_scope_correct()
    test_idempotency_scope_same_scope_ok()
    test_idempotency_scope_violation()
    test_idempotency_scope_window()
    test_idempotency_scope_within_window()

    print("\n4. STATE TRACE")
    test_build_state_trace()
    test_build_state_trace_with_initial()

    print("\n5. END-TO-END REPLAY")
    test_validate_replay_temporal_e2e()

    print("\n6. VIOLATIONS TO DRIFTS")
    test_temporal_violations_to_drifts()

    print("\n7. DRIFT PRIORITY")
    test_temporal_priority()

    print("\n8. MULTIPLE SPECS TOGETHER")
    test_multiple_temporal_specs()

    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    main()
