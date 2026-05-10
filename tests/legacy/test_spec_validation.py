"""Smoke tests for spec-anchored validation.

Verifies:
  1. spec_increment_counter detects wrong deltas
  2. spec_state_transition detects illegal transitions
  3. spec_idempotency_key detects duplicate execution
  4. SpecRegistry lookup and batch replay validation
  5. ExtendedDriftClass priority ordering
  6. Precondition gating (skip, not violate)
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
    ExtendedDrift,
    ExtendedDriftClass,
    PrimitiveSpec,
    SpecRegistry,
    SpecReplayResult,
    SpecValidationResult,
    highest_priority_drift,
    spec_idempotency_key,
    spec_increment_counter,
    spec_state_transition,
    validate_against_spec,
    validate_entry_against_spec,
    validate_replay_against_specs,
)

# ─── Helpers ────────────────────────────────────────────────────────────────


def _entry(
    event_type: str,
    payload: dict,
    mutations: list[StateMutation],
    seq: int = 0,
) -> EventLogEntry:
    return EventLogEntry(
        sequence_number=seq,
        event_id=f"evt-{seq}",
        event_type=event_type,
        correlation_id="test",
        payload=payload,
        state_mutations=mutations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. INCREMENT COUNTER SPEC
# ═══════════════════════════════════════════════════════════════════════════


def test_increment_counter_correct():
    """Correct increment passes all conditions."""
    spec = spec_increment_counter("clicks", delta_field="delta")
    entry = _entry(
        event_type="increment_counter:clicks",
        payload={"delta": 5},
        mutations=[
            StateMutation(key="clicks", operation=MutationOp.INCREMENT, value=5)
        ],
    )
    state_before = {"clicks": 10}
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.valid, (
        f"expected valid, got violations: {[v.detail for v in result.violations]}"
    )
    assert not result.skipped
    print("  PASS: correct increment")


def test_increment_counter_wrong_delta():
    """Executors agree on delta=3 but spec says payload.delta=5 → SPEC_VIOLATION."""
    spec = spec_increment_counter("clicks", delta_field="delta")
    entry = _entry(
        event_type="increment_counter:clicks",
        payload={"delta": 5},
        mutations=[
            StateMutation(key="clicks", operation=MutationOp.INCREMENT, value=3)
        ],
    )
    state_before = {"clicks": 10}
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.violated
    names = [v.condition_name for v in result.violations]
    assert "counter_equals_previous_plus_delta" in names
    assert "single_increment_correct_delta" in names
    print(f"  PASS: wrong delta detected ({len(result.violations)} violations)")


def test_increment_counter_wrong_key():
    """Both executors increment the wrong key → spec detects missing mutation."""
    spec = spec_increment_counter("clicks", delta_field="delta")
    entry = _entry(
        event_type="increment_counter:clicks",
        payload={"delta": 5},
        mutations=[StateMutation(key="views", operation=MutationOp.INCREMENT, value=5)],
    )
    state_before = {"clicks": 10}
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.violated
    names = [v.condition_name for v in result.violations]
    assert "single_increment_correct_delta" in names
    print(f"  PASS: wrong key detected ({len(result.violations)} violations)")


def test_increment_counter_precondition_skip():
    """Key doesn't exist → spec skipped, not violated."""
    spec = spec_increment_counter("clicks", delta_field="delta")
    entry = _entry(
        event_type="increment_counter:clicks",
        payload={"delta": 5},
        mutations=[
            StateMutation(key="clicks", operation=MutationOp.INCREMENT, value=5)
        ],
    )
    state_before = {}  # no 'clicks' key
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.skipped
    assert not result.violated
    print("  PASS: missing key → skip, not violation")


# ═══════════════════════════════════════════════════════════════════════════
# 2. STATE TRANSITION SPEC
# ═══════════════════════════════════════════════════════════════════════════


def test_state_transition_correct():
    """Legal transition passes."""
    allowed = {"idle": {"active"}, "active": {"idle", "closed"}}
    spec = spec_state_transition("status", allowed, new_state_field="new_state")
    entry = _entry(
        event_type="state_transition:status",
        payload={"new_state": "active"},
        mutations=[
            StateMutation(key="status", operation=MutationOp.SET, value="active")
        ],
    )
    state_before = {"status": "idle"}
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.valid, f"violations: {[v.detail for v in result.violations]}"
    print("  PASS: legal transition")


def test_state_transition_illegal():
    """idle → closed is not allowed → SPEC_VIOLATION."""
    allowed = {"idle": {"active"}, "active": {"idle", "closed"}}
    spec = spec_state_transition("status", allowed, new_state_field="new_state")
    entry = _entry(
        event_type="state_transition:status",
        payload={"new_state": "closed"},
        mutations=[
            StateMutation(key="status", operation=MutationOp.SET, value="closed")
        ],
    )
    state_before = {"status": "idle"}
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.violated
    names = [v.condition_name for v in result.violations]
    assert "transition_allowed" in names
    print(f"  PASS: illegal transition detected ({len(result.violations)} violations)")


def test_state_transition_wrong_target():
    """Payload says 'active' but mutation sets 'closed' → intent mismatch."""
    allowed = {"idle": {"active", "closed"}, "active": {"idle", "closed"}}
    spec = spec_state_transition("status", allowed, new_state_field="new_state")
    entry = _entry(
        event_type="state_transition:status",
        payload={"new_state": "active"},
        mutations=[
            StateMutation(key="status", operation=MutationOp.SET, value="closed")
        ],
    )
    state_before = {"status": "idle"}
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.violated
    names = [v.condition_name for v in result.violations]
    assert "matches_payload_intent" in names
    print(f"  PASS: intent mismatch detected ({len(result.violations)} violations)")


# ═══════════════════════════════════════════════════════════════════════════
# 3. IDEMPOTENCY KEY SPEC
# ═══════════════════════════════════════════════════════════════════════════


def test_idempotency_correct():
    """First-time key execution passes."""
    spec = spec_idempotency_key()
    entry = _entry(
        event_type="idempotency_key",
        payload={"idempotency_key": "job-42"},
        mutations=[
            StateMutation(
                key="__completed_keys",
                operation=MutationOp.SET,
                value=["job-42"],
            )
        ],
    )
    state_before = {"__completed_keys": []}
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.valid, f"violations: {[v.detail for v in result.violations]}"
    print("  PASS: first-time idempotency")


def test_idempotency_duplicate():
    """Key already completed → SPEC_VIOLATION."""
    spec = spec_idempotency_key()
    entry = _entry(
        event_type="idempotency_key",
        payload={"idempotency_key": "job-42"},
        mutations=[
            StateMutation(
                key="__completed_keys",
                operation=MutationOp.SET,
                value=["job-42", "job-42"],
            )
        ],
    )
    state_before = {"__completed_keys": ["job-42"]}
    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)
    assert result.violated
    names = [v.condition_name for v in result.violations]
    assert "not_already_completed" in names
    print(f"  PASS: duplicate key detected ({len(result.violations)} violations)")


# ═══════════════════════════════════════════════════════════════════════════
# 4. REGISTRY + BATCH REPLAY
# ═══════════════════════════════════════════════════════════════════════════


def test_registry_and_batch():
    """Batch validation across multiple entries with different specs."""
    registry = SpecRegistry()
    registry.register(spec_increment_counter("clicks", delta_field="delta"))
    registry.register(
        spec_state_transition(
            "status",
            {"idle": {"active"}, "active": {"idle", "closed"}},
            new_state_field="new_state",
        )
    )

    assert len(registry) == 2
    assert registry.has("increment_counter:clicks")
    assert registry.has("state_transition:status")
    assert not registry.has("unknown_type")

    entries = [
        # Good increment
        _entry(
            "increment_counter:clicks",
            {"delta": 1},
            [StateMutation(key="clicks", operation=MutationOp.INCREMENT, value=1)],
            seq=0,
        ),
        # Bad increment (delta 3 instead of 5)
        _entry(
            "increment_counter:clicks",
            {"delta": 5},
            [StateMutation(key="clicks", operation=MutationOp.INCREMENT, value=3)],
            seq=1,
        ),
        # Unspecified event type (should be ignored)
        _entry(
            "some_other_event",
            {},
            [StateMutation(key="foo", operation=MutationOp.SET, value="bar")],
            seq=2,
        ),
    ]

    result = validate_replay_against_specs(
        entries, registry, initial_state={"clicks": 0}
    )
    assert result.entries_checked == 2
    assert result.entries_passed == 1
    assert result.entries_violated == 1
    assert len(result.violations) > 0
    assert not result.valid
    print(f"  PASS: batch replay ({result.summary()})")


# ═══════════════════════════════════════════════════════════════════════════
# 5. DRIFT PRIORITY
# ═══════════════════════════════════════════════════════════════════════════


def test_drift_priority():
    """EXECUTION_DIVERGENCE > SPEC_VIOLATION > TEMPORAL > SEMANTIC > STRUCTURE > HASH."""
    assert DRIFT_PRIORITY[0] == ExtendedDriftClass.EXECUTION_DIVERGENCE
    assert DRIFT_PRIORITY[1] == ExtendedDriftClass.SPEC_VIOLATION
    assert DRIFT_PRIORITY[2] == ExtendedDriftClass.TEMPORAL_VIOLATION
    assert DRIFT_PRIORITY[3] == ExtendedDriftClass.SEMANTIC_VIOLATION
    assert DRIFT_PRIORITY[4] == ExtendedDriftClass.STRUCTURE_INVALID
    assert DRIFT_PRIORITY[5] == ExtendedDriftClass.HASH_MISMATCH

    result = highest_priority_drift(
        [
            ExtendedDriftClass.HASH_MISMATCH,
            ExtendedDriftClass.SPEC_VIOLATION,
        ]
    )
    assert result == ExtendedDriftClass.SPEC_VIOLATION
    print("  PASS: priority ordering correct")


# ═══════════════════════════════════════════════════════════════════════════
# 6. INTEGRATED ENTRY VALIDATION
# ═══════════════════════════════════════════════════════════════════════════


def test_validate_entry_no_spec():
    """Event with no registered spec returns None."""
    registry = SpecRegistry()
    entry = _entry("unknown", {}, [], seq=0)
    result = validate_entry_against_spec(entry, {}, registry)
    assert result is None
    print("  PASS: no spec → None")


def test_validate_entry_spec_violation():
    """Entry that violates spec returns ExtendedDrift."""
    registry = SpecRegistry()
    registry.register(spec_increment_counter("clicks", delta_field="delta"))

    entry = _entry(
        "increment_counter:clicks",
        {"delta": 10},
        [StateMutation(key="clicks", operation=MutationOp.INCREMENT, value=3)],
        seq=7,
    )
    drift = validate_entry_against_spec(entry, {"clicks": 0}, registry)
    assert drift is not None
    assert drift.drift_class == ExtendedDriftClass.SPEC_VIOLATION
    assert drift.sequence_number == 7
    assert len(drift.spec_violations) > 0
    print(
        f"  PASS: entry spec violation → ExtendedDrift ({len(drift.spec_violations)} violations)"
    )


# ═══════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=== SPEC-ANCHORED VALIDATION TESTS ===\n")

    print("1. INCREMENT COUNTER")
    test_increment_counter_correct()
    test_increment_counter_wrong_delta()
    test_increment_counter_wrong_key()
    test_increment_counter_precondition_skip()

    print("\n2. STATE TRANSITION")
    test_state_transition_correct()
    test_state_transition_illegal()
    test_state_transition_wrong_target()

    print("\n3. IDEMPOTENCY KEY")
    test_idempotency_correct()
    test_idempotency_duplicate()

    print("\n4. REGISTRY + BATCH REPLAY")
    test_registry_and_batch()

    print("\n5. DRIFT PRIORITY")
    test_drift_priority()

    print("\n6. INTEGRATED ENTRY VALIDATION")
    test_validate_entry_no_spec()
    test_validate_entry_spec_violation()

    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    main()
