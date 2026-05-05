"""
Spec-Anchored Validation — correctness measured against defined behavior.

Extends the verification system with a new correctness dimension:

  Current system: "Do two executors agree?" (agreement-based)
  This module:    "Does the output match the defined spec?" (spec-based)

The gap this fills:

  Both executors produce the same wrong answer → no EXECUTION_DIVERGENCE.
  Mutations match the log → no HASH_MISMATCH.
  Types and schema valid → no STRUCTURE_INVALID.
  Counters didn't decrease → no SEMANTIC_VIOLATION.
  But the counter incremented by 3 when the spec says 5.
  **SPEC_VIOLATION.**

Design:

  A PrimitiveSpec is a declarative definition of what a primitive
  MUST produce given specific preconditions. It defines:
    - preconditions: state must satisfy before the primitive runs
    - postconditions: state must satisfy after mutations apply
    - mutation_invariants: constraints on the mutations themselves
    - examples: concrete input/output pairs for documentation

  The spec validator runs AFTER both executors and AFTER semantic guards.
  It checks the agreed-upon mutations against the defined spec.
  This catches correlated failures — when both executors are wrong
  in the same way.

Integration point:

  replay_advanced_verify → structural → primary → cross-check → hash →
  semantic guards → **spec_validation** (this module)

No external dependencies. Pure data operations.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from umh.substrate.replay_validation import (
    EventLogEntry,
    MutationOp,
    StateMutation,
    apply_mutations,
)

# ─── Logging ────────────────────────────────────────────────────────────────

_LOG_PREFIX = "[substrate.spec_validation]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr, flush=True)


# ═══════════════════════════════════════════════════════════════════════════
# 1. PRIMITIVE SPEC DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════


class SpecConditionResult(str, Enum):
    """Result of evaluating a single spec condition."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"  # precondition not met, spec doesn't apply


@dataclass(frozen=True)
class SpecViolation:
    """A single violation of a primitive spec.

    Attributes:
        spec_name: Which spec was violated.
        condition_name: Which condition within the spec.
        expected: What the spec requires.
        actual: What was observed.
        detail: Human-readable explanation.
    """

    spec_name: str
    condition_name: str
    expected: str
    actual: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_name": self.spec_name,
            "condition_name": self.condition_name,
            "expected": self.expected,
            "actual": self.actual,
            "detail": self.detail,
        }


# Condition callables receive (state_before, mutations, state_after, event_payload)
# and return None (pass) or a violation description string (fail).
SpecCondition = Callable[
    [dict[str, Any], list[StateMutation], dict[str, Any], dict[str, Any]],
    Optional[str],
]


@dataclass
class PrimitiveSpec:
    """Declarative specification of a primitive's correct behavior.

    A spec defines WHAT a primitive must do, not HOW. Two independent
    executors can both produce mutations that hash-match, pass schema
    validation, and satisfy semantic guards — but still violate the spec.

    Attributes:
        name: Unique identifier matching the event_type or primitive name.
        description: What this primitive is supposed to do.
        preconditions: Conditions on state_before + payload that must be
            true for this spec to apply. If any precondition fails,
            the spec is SKIPPED (not violated). This prevents false
            positives when a primitive runs in a context outside its spec.
        postconditions: Conditions on state_after that must hold after
            mutations are applied. These define correct output.
        mutation_invariants: Constraints on the mutation list itself
            (e.g. "must contain exactly one INCREMENT on key X").
    """

    name: str
    description: str = ""
    preconditions: list[tuple[str, SpecCondition]] = field(default_factory=list)
    postconditions: list[tuple[str, SpecCondition]] = field(default_factory=list)
    mutation_invariants: list[tuple[str, SpecCondition]] = field(default_factory=list)

    def add_precondition(self, name: str, condition: SpecCondition) -> "PrimitiveSpec":
        """Add a precondition. Fluent API."""
        self.preconditions.append((name, condition))
        return self

    def add_postcondition(self, name: str, condition: SpecCondition) -> "PrimitiveSpec":
        """Add a postcondition. Fluent API."""
        self.postconditions.append((name, condition))
        return self

    def add_mutation_invariant(
        self, name: str, condition: SpecCondition
    ) -> "PrimitiveSpec":
        """Add a mutation invariant. Fluent API."""
        self.mutation_invariants.append((name, condition))
        return self


# ═══════════════════════════════════════════════════════════════════════════
# 2. SPEC REGISTRY
# ═══════════════════════════════════════════════════════════════════════════


class SpecRegistry:
    """Registry of primitive specs, keyed by event_type.

    Specs are registered once at startup and looked up per-event
    during validation. An event with no registered spec is silently
    skipped — the system is opt-in, not opt-out.
    """

    def __init__(self) -> None:
        self._specs: dict[str, PrimitiveSpec] = {}

    def register(self, spec: PrimitiveSpec) -> None:
        """Register a primitive spec."""
        self._specs[spec.name] = spec
        _log(f"registered spec: {spec.name}")

    def get(self, event_type: str) -> Optional[PrimitiveSpec]:
        """Look up a spec by event type."""
        return self._specs.get(event_type)

    def has(self, event_type: str) -> bool:
        """Check if a spec exists for an event type."""
        return event_type in self._specs

    @property
    def registered_names(self) -> list[str]:
        """All registered spec names."""
        return list(self._specs.keys())

    def __len__(self) -> int:
        return len(self._specs)


# ═══════════════════════════════════════════════════════════════════════════
# 3. SPEC VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class SpecValidationResult:
    """Result of validating one event against its spec.

    Attributes:
        event_id: The event that was validated.
        spec_name: Which spec was applied.
        preconditions_met: Whether all preconditions passed.
        violations: Spec violations found.
        skipped: True if preconditions were not met (spec doesn't apply).
    """

    event_id: str
    spec_name: str
    preconditions_met: bool = True
    violations: list[SpecViolation] = field(default_factory=list)
    skipped: bool = False

    @property
    def valid(self) -> bool:
        """True if no violations and not skipped."""
        return len(self.violations) == 0 and not self.skipped

    @property
    def violated(self) -> bool:
        """True if any violations found."""
        return len(self.violations) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "spec_name": self.spec_name,
            "preconditions_met": self.preconditions_met,
            "skipped": self.skipped,
            "valid": self.valid,
            "violation_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
        }


def validate_against_spec(
    entry: EventLogEntry,
    state_before: dict[str, Any],
    mutations: list[StateMutation],
    spec: PrimitiveSpec,
) -> SpecValidationResult:
    """Validate an event's mutations against its primitive spec.

    Evaluation order:
    1. Check preconditions. If any fail, SKIP (spec doesn't apply).
    2. Apply mutations to state_before to get state_after.
    3. Check postconditions against state_after.
    4. Check mutation invariants against the mutation list.

    Args:
        entry: The event log entry.
        state_before: State snapshot before mutations were applied.
        mutations: The mutations to validate (from the agreed execution).
        spec: The primitive spec to validate against.

    Returns:
        SpecValidationResult with any violations found.
    """
    result = SpecValidationResult(
        event_id=entry.event_id,
        spec_name=spec.name,
    )

    # Compute state_after by applying mutations to a copy
    state_after = dict(state_before)
    apply_mutations(state_after, mutations)

    payload = entry.payload

    # ── Phase 1: Preconditions ──
    for cond_name, condition in spec.preconditions:
        try:
            violation_msg = condition(state_before, mutations, state_after, payload)
        except Exception as exc:
            _log(f"precondition {cond_name!r} error: {exc}")
            violation_msg = f"precondition error: {exc}"

        if violation_msg is not None:
            # Precondition not met — skip this spec entirely
            result.preconditions_met = False
            result.skipped = True
            return result

    # ── Phase 2: Postconditions ──
    for cond_name, condition in spec.postconditions:
        try:
            violation_msg = condition(state_before, mutations, state_after, payload)
        except Exception as exc:
            violation_msg = f"postcondition error: {exc}"

        if violation_msg is not None:
            result.violations.append(
                SpecViolation(
                    spec_name=spec.name,
                    condition_name=cond_name,
                    expected=f"postcondition {cond_name!r} to pass",
                    actual=violation_msg,
                    detail=violation_msg,
                )
            )

    # ── Phase 3: Mutation invariants ──
    for cond_name, condition in spec.mutation_invariants:
        try:
            violation_msg = condition(state_before, mutations, state_after, payload)
        except Exception as exc:
            violation_msg = f"invariant error: {exc}"

        if violation_msg is not None:
            result.violations.append(
                SpecViolation(
                    spec_name=spec.name,
                    condition_name=cond_name,
                    expected=f"invariant {cond_name!r} to hold",
                    actual=violation_msg,
                    detail=violation_msg,
                )
            )

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 4. BATCH VALIDATION (for replay integration)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class SpecReplayResult:
    """Aggregate result of spec validation across a replay pass.

    Attributes:
        entries_checked: Number of entries that had a matching spec.
        entries_skipped: Entries where preconditions were not met.
        entries_passed: Entries that passed all spec conditions.
        entries_violated: Entries with at least one spec violation.
        violations: All violations across all entries.
        duration_ms: Wall-clock time for spec validation pass.
    """

    entries_checked: int = 0
    entries_skipped: int = 0
    entries_passed: int = 0
    entries_violated: int = 0
    violations: list[SpecViolation] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def valid(self) -> bool:
        """True if no violations found."""
        return self.entries_violated == 0

    def summary(self) -> str:
        """One-line summary for logging."""
        if self.valid:
            return (
                f"SPEC-VALID: {self.entries_checked} checked, "
                f"{self.entries_skipped} skipped, "
                f"{self.entries_passed} passed "
                f"in {self.duration_ms:.1f}ms"
            )
        return (
            f"SPEC-VIOLATED: {self.entries_violated} entries, "
            f"{len(self.violations)} violations "
            f"({self.entries_checked} checked, {self.duration_ms:.1f}ms)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "entries_checked": self.entries_checked,
            "entries_skipped": self.entries_skipped,
            "entries_passed": self.entries_passed,
            "entries_violated": self.entries_violated,
            "violation_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
            "duration_ms": round(self.duration_ms, 3),
        }


def validate_replay_against_specs(
    entries: list[EventLogEntry],
    registry: SpecRegistry,
    initial_state: Optional[dict[str, Any]] = None,
) -> SpecReplayResult:
    """Run spec validation across a sequence of replay entries.

    Replays state forward entry by entry, validating each entry
    that has a registered spec. Entries without specs are silently
    ignored.

    This function is designed to run as a post-pass after
    replay_advanced_verify completes, using the same entry sequence.

    Args:
        entries: Ordered event log entries (from replay).
        registry: Spec registry with registered primitive specs.
        initial_state: Starting state (from checkpoint).

    Returns:
        SpecReplayResult with aggregate violations.
    """
    start_time = time.monotonic()
    state = dict(initial_state) if initial_state else {}
    result = SpecReplayResult()

    for entry in entries:
        spec = registry.get(entry.event_type)
        if spec is None:
            # No spec for this event type — apply mutations and continue
            apply_mutations(state, entry.state_mutations)
            continue

        result.entries_checked += 1
        state_before = dict(state)

        # Validate against spec
        validation = validate_against_spec(
            entry, state_before, entry.state_mutations, spec
        )

        if validation.skipped:
            result.entries_skipped += 1
        elif validation.violated:
            result.entries_violated += 1
            result.violations.extend(validation.violations)
        else:
            result.entries_passed += 1

        # Advance state
        apply_mutations(state, entry.state_mutations)

    result.duration_ms = (time.monotonic() - start_time) * 1000
    _log(f"spec replay: {result.summary()}")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 5. SPEC BUILDER FACTORIES — the three starter primitives
# ═══════════════════════════════════════════════════════════════════════════
#
# Start minimal: counters, state transitions, idempotency keys.
# These three cover the most common correctness failures.


def spec_increment_counter(
    key: str,
    *,
    delta_field: str = "delta",
    require_numeric: bool = True,
) -> PrimitiveSpec:
    """Build a spec for INCREMENT_COUNTER primitives.

    Defines:
      precondition: key exists in state and is numeric
      postcondition: state[key] == previous + payload[delta_field]
      mutation_invariant: exactly one INCREMENT mutation on key

    Args:
        key: The state key being incremented.
        delta_field: Payload field containing the expected delta.
        require_numeric: If True, precondition checks key is numeric.

    Returns:
        A PrimitiveSpec ready for registration.
    """
    spec = PrimitiveSpec(
        name=f"increment_counter:{key}",
        description=f"Increment counter {key!r} by payload[{delta_field!r}]",
    )

    # Precondition: key exists and is numeric
    if require_numeric:

        def _pre_numeric(
            before: dict[str, Any],
            mutations: list[StateMutation],
            after: dict[str, Any],
            payload: dict[str, Any],
        ) -> Optional[str]:
            val = before.get(key)
            if val is None:
                return f"key {key!r} does not exist in state"
            if not isinstance(val, (int, float)):
                return f"key {key!r} is {type(val).__name__}, not numeric"
            return None

        spec.add_precondition("key_exists_numeric", _pre_numeric)

    # Precondition: delta exists in payload
    def _pre_delta(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        if delta_field not in payload:
            return f"payload missing {delta_field!r}"
        if not isinstance(payload[delta_field], (int, float)):
            return f"payload[{delta_field!r}] is not numeric"
        return None

    spec.add_precondition("delta_in_payload", _pre_delta)

    # Postcondition: counter == previous + delta
    def _post_value(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        expected = before.get(key, 0) + payload.get(delta_field, 0)
        actual = after.get(key)
        if actual != expected:
            return (
                f"counter {key!r}: expected {expected} "
                f"(was {before.get(key, 0)} + delta {payload.get(delta_field, 0)}), "
                f"got {actual}"
            )
        return None

    spec.add_postcondition("counter_equals_previous_plus_delta", _post_value)

    # Postcondition: counter >= previous (monotonic)
    def _post_monotonic(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        old = before.get(key, 0)
        new = after.get(key, 0)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            if new < old:
                return f"counter {key!r}: decreased from {old} to {new}"
        return None

    spec.add_postcondition("counter_monotonic", _post_monotonic)

    # Mutation invariant: exactly one INCREMENT on this key
    def _inv_single_increment(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        increments = [
            m for m in mutations if m.key == key and m.operation == MutationOp.INCREMENT
        ]
        if len(increments) == 0:
            return f"no INCREMENT mutation on {key!r}"
        if len(increments) > 1:
            return f"multiple INCREMENT mutations on {key!r}: {len(increments)}"
        # Verify the delta value matches payload
        actual_delta = increments[0].value
        expected_delta = payload.get(delta_field)
        if actual_delta != expected_delta:
            return (
                f"INCREMENT delta mismatch on {key!r}: "
                f"mutation has {actual_delta}, payload says {expected_delta}"
            )
        return None

    spec.add_mutation_invariant("single_increment_correct_delta", _inv_single_increment)

    return spec


def spec_state_transition(
    key: str,
    allowed_transitions: dict[str, set[str]],
    *,
    new_state_field: str = "new_state",
) -> PrimitiveSpec:
    """Build a spec for STATE_TRANSITION primitives.

    Defines:
      precondition: key exists, current value is in allowed_transitions
      postcondition: state[key] is in allowed_transitions[old_value]
      postcondition: state[key] == payload[new_state_field]
      mutation_invariant: exactly one SET mutation on key

    Args:
        key: The state key holding the state value.
        allowed_transitions: Map from current state to valid next states.
        new_state_field: Payload field with the intended new state.

    Returns:
        A PrimitiveSpec ready for registration.
    """
    spec = PrimitiveSpec(
        name=f"state_transition:{key}",
        description=(
            f"Transition {key!r} between states: "
            f"{', '.join(f'{k}->{sorted(v)}' for k, v in allowed_transitions.items())}"
        ),
    )

    # Precondition: key exists and is in a known state
    def _pre_known_state(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        val = before.get(key)
        if val is None:
            return f"key {key!r} does not exist"
        if str(val) not in allowed_transitions:
            return f"key {key!r} in unknown state {val!r}"
        return None

    spec.add_precondition("key_in_known_state", _pre_known_state)

    # Precondition: new_state in payload
    def _pre_new_state(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        if new_state_field not in payload:
            return f"payload missing {new_state_field!r}"
        return None

    spec.add_precondition("new_state_in_payload", _pre_new_state)

    # Postcondition: transition is allowed
    def _post_transition_allowed(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        old_val = str(before.get(key, ""))
        new_val = str(after.get(key, ""))
        if old_val == new_val:
            return None  # no-op is always valid
        allowed = allowed_transitions.get(old_val, set())
        if new_val not in allowed:
            return (
                f"transition {key!r}: {old_val!r} -> {new_val!r} "
                f"not in allowed {sorted(allowed)}"
            )
        return None

    spec.add_postcondition("transition_allowed", _post_transition_allowed)

    # Postcondition: matches payload intent
    def _post_matches_intent(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        intended = payload.get(new_state_field)
        actual = after.get(key)
        if str(actual) != str(intended):
            return f"state {key!r}: intended {intended!r} but got {actual!r}"
        return None

    spec.add_postcondition("matches_payload_intent", _post_matches_intent)

    # Mutation invariant: exactly one SET on this key
    def _inv_single_set(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        sets = [m for m in mutations if m.key == key and m.operation == MutationOp.SET]
        if len(sets) == 0:
            return f"no SET mutation on {key!r}"
        if len(sets) > 1:
            return f"multiple SET mutations on {key!r}: {len(sets)}"
        return None

    spec.add_mutation_invariant("single_set", _inv_single_set)

    return spec


def spec_idempotency_key(
    *,
    completed_key: str = "__completed_keys",
    idempotency_field: str = "idempotency_key",
) -> PrimitiveSpec:
    """Build a spec for IDEMPOTENCY_KEY primitives.

    Defines:
      precondition: idempotency_key present in payload
      postcondition: key is in completed set after execution
      postcondition: key was NOT in completed set before execution
      mutation_invariant: completed set modified exactly once

    Args:
        completed_key: State key holding the list of completed keys.
        idempotency_field: Payload field containing the idempotency key.

    Returns:
        A PrimitiveSpec ready for registration.
    """
    spec = PrimitiveSpec(
        name="idempotency_key",
        description="Ensure idempotency key is recorded exactly once",
    )

    # Precondition: idempotency key in payload
    def _pre_key_present(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        if idempotency_field not in payload:
            return f"payload missing {idempotency_field!r}"
        return None

    spec.add_precondition("key_in_payload", _pre_key_present)

    # Postcondition: key is now in completed set
    def _post_key_recorded(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        idem_key = str(payload.get(idempotency_field, ""))
        completed = after.get(completed_key, [])
        if not isinstance(completed, list):
            return f"{completed_key!r} is not a list"
        if idem_key not in [str(k) for k in completed]:
            return (
                f"idempotency key {idem_key!r} not in {completed_key!r} after execution"
            )
        return None

    spec.add_postcondition("key_in_completed_set", _post_key_recorded)

    # Postcondition: key was NOT already completed (no double execution)
    def _post_not_duplicate(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        idem_key = str(payload.get(idempotency_field, ""))
        completed_before = before.get(completed_key, [])
        if not isinstance(completed_before, list):
            return None  # no completed set yet — fine
        if idem_key in [str(k) for k in completed_before]:
            return (
                f"idempotency key {idem_key!r} already in {completed_key!r} "
                f"before execution — duplicate"
            )
        return None

    spec.add_postcondition("not_already_completed", _post_not_duplicate)

    # Mutation invariant: completed_key modified
    def _inv_completed_modified(
        before: dict[str, Any],
        mutations: list[StateMutation],
        after: dict[str, Any],
        payload: dict[str, Any],
    ) -> Optional[str]:
        mods = [m for m in mutations if m.key == completed_key]
        if len(mods) == 0:
            return f"no mutation on {completed_key!r}"
        return None

    spec.add_mutation_invariant("completed_key_modified", _inv_completed_modified)

    return spec


# ═══════════════════════════════════════════════════════════════════════════
# 6. DRIFT CLASS EXTENSION — SPEC_VIOLATION
# ═══════════════════════════════════════════════════════════════════════════
#
# This extends the existing DriftClass enum conceptually.
# Since Python enums are closed, we define the extended classification
# here and provide a mapping function.


class ExtendedDriftClass(str, Enum):
    """Extended drift classification including spec and temporal violations.

    Priority (highest to lowest):
      EXECUTION_DIVERGENCE — executors disagree
      SPEC_VIOLATION       — executors agree but violate defined behavior
      TEMPORAL_VIOLATION   — correct locally, incorrect across time
      SEMANTIC_VIOLATION   — breaks domain invariant
      STRUCTURE_INVALID    — violates state schema
      HASH_MISMATCH        — mutations differ, structure/semantics OK
    """

    EXECUTION_DIVERGENCE = "execution_divergence"
    SPEC_VIOLATION = "spec_violation"
    TEMPORAL_VIOLATION = "temporal_violation"
    SEMANTIC_VIOLATION = "semantic_violation"
    STRUCTURE_INVALID = "structure_invalid"
    HASH_MISMATCH = "hash_mismatch"


# Priority ordering — lower index = higher priority
DRIFT_PRIORITY: list[ExtendedDriftClass] = [
    ExtendedDriftClass.EXECUTION_DIVERGENCE,
    ExtendedDriftClass.SPEC_VIOLATION,
    ExtendedDriftClass.TEMPORAL_VIOLATION,
    ExtendedDriftClass.SEMANTIC_VIOLATION,
    ExtendedDriftClass.STRUCTURE_INVALID,
    ExtendedDriftClass.HASH_MISMATCH,
]


def highest_priority_drift(classes: list[ExtendedDriftClass]) -> ExtendedDriftClass:
    """Return the highest-priority drift class from a list."""
    if not classes:
        raise ValueError("empty drift class list")
    for priority in DRIFT_PRIORITY:
        if priority in classes:
            return priority
    return classes[0]


@dataclass(frozen=True)
class ExtendedDrift:
    """A drift detection with the extended classification.

    Mirrors ClassifiedDrift but supports SPEC_VIOLATION.

    Attributes:
        event_id: The event where drift was detected.
        sequence_number: Log position.
        drift_class: Extended root-cause category.
        detail: Human-readable explanation.
        spec_violations: Specific spec violations (empty if not SPEC_VIOLATION).
    """

    event_id: str
    sequence_number: int
    drift_class: ExtendedDriftClass
    detail: str
    spec_violations: tuple[SpecViolation, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "sequence_number": self.sequence_number,
            "drift_class": self.drift_class.value,
            "detail": self.detail,
            "spec_violations": [v.to_dict() for v in self.spec_violations],
        }


# ═══════════════════════════════════════════════════════════════════════════
# 7. INTEGRATED VALIDATION — wires spec checks into replay results
# ═══════════════════════════════════════════════════════════════════════════


def validate_entry_against_spec(
    entry: EventLogEntry,
    state_before: dict[str, Any],
    registry: SpecRegistry,
) -> Optional[ExtendedDrift]:
    """Validate a single entry against its spec, if one exists.

    Returns None if no spec exists or spec passes.
    Returns ExtendedDrift with SPEC_VIOLATION if violations found.
    Returns None if preconditions not met (spec doesn't apply).
    """
    spec = registry.get(entry.event_type)
    if spec is None:
        return None

    result = validate_against_spec(entry, state_before, entry.state_mutations, spec)

    if result.skipped or not result.violated:
        return None

    return ExtendedDrift(
        event_id=entry.event_id,
        sequence_number=entry.sequence_number,
        drift_class=ExtendedDriftClass.SPEC_VIOLATION,
        detail=f"{len(result.violations)} spec violations in {spec.name}",
        spec_violations=tuple(result.violations),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 8. TEMPORAL (MULTI-EVENT) SPECIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════
#
# Per-event specs validate that ONE event did what it should.
# Temporal specs validate that a SEQUENCE of events maintains invariants
# across time:
#
#   - ordering constraints (X must happen before Y)
#   - frequency constraints (Z must not happen twice per cycle)
#   - scope constraints (key K must not repeat within window W)
#
# Temporal specs run as a post-pass after the full replay completes.
# They receive the complete state_trace built during replay:
#
#   state_trace = [(entry, state_before, state_after), ...]
#
# This gives each temporal spec the full causal chain without
# re-projecting state.

# A state trace entry: the event, the state before it, and the state after.
StateTraceEntry = tuple[EventLogEntry, dict[str, Any], dict[str, Any]]


@dataclass(frozen=True)
class TemporalViolation:
    """A single temporal violation spanning multiple events.

    Attributes:
        spec_name: Which temporal spec was violated.
        detail: Human-readable explanation.
        involved_events: Event IDs that participate in the violation.
        first_sequence: Sequence number of the earliest involved event.
        last_sequence: Sequence number of the latest involved event.
    """

    spec_name: str
    detail: str
    involved_events: tuple[str, ...] = ()
    first_sequence: int = 0
    last_sequence: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_name": self.spec_name,
            "detail": self.detail,
            "involved_events": list(self.involved_events),
            "first_sequence": self.first_sequence,
            "last_sequence": self.last_sequence,
        }


# A TemporalCondition receives the full state trace and returns
# a list of violations (empty = pass).
TemporalCondition = Callable[
    [list[StateTraceEntry]],
    list[TemporalViolation],
]


@dataclass
class TemporalSpec:
    """Declarative specification of a multi-event correctness property.

    Unlike PrimitiveSpec which validates one event at a time,
    TemporalSpec validates properties that only become visible
    across a sequence of events.

    Attributes:
        name: Unique identifier for this temporal spec.
        description: What this spec enforces across time.
        conditions: Named temporal conditions to evaluate.
    """

    name: str
    description: str = ""
    conditions: list[tuple[str, TemporalCondition]] = field(default_factory=list)

    def add_condition(self, name: str, condition: TemporalCondition) -> "TemporalSpec":
        """Add a temporal condition. Fluent API."""
        self.conditions.append((name, condition))
        return self


class TemporalRegistry:
    """Registry of temporal specs.

    All registered temporal specs run on every replay — they are not
    keyed by event_type since they span multiple event types.
    """

    def __init__(self) -> None:
        self._specs: list[TemporalSpec] = []
        self._by_name: dict[str, TemporalSpec] = {}

    def register(self, spec: TemporalSpec) -> None:
        """Register a temporal spec."""
        self._specs.append(spec)
        self._by_name[spec.name] = spec
        _log(f"registered temporal spec: {spec.name}")

    def get(self, name: str) -> Optional[TemporalSpec]:
        """Look up a temporal spec by name."""
        return self._by_name.get(name)

    @property
    def specs(self) -> list[TemporalSpec]:
        """All registered temporal specs."""
        return list(self._specs)

    def __len__(self) -> int:
        return len(self._specs)


# ═══════════════════════════════════════════════════════════════════════════
# 9. TEMPORAL SPEC VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class TemporalValidationResult:
    """Result of running temporal specs across a full replay trace.

    Attributes:
        specs_checked: Number of temporal specs evaluated.
        specs_passed: Specs with no violations.
        specs_violated: Specs with at least one violation.
        violations: All temporal violations across all specs.
        duration_ms: Wall-clock time for temporal validation.
    """

    specs_checked: int = 0
    specs_passed: int = 0
    specs_violated: int = 0
    violations: list[TemporalViolation] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def valid(self) -> bool:
        """True if no temporal violations found."""
        return len(self.violations) == 0

    def summary(self) -> str:
        """One-line summary for logging."""
        if self.valid:
            return (
                f"TEMPORAL-VALID: {self.specs_checked} specs checked, "
                f"all passed in {self.duration_ms:.1f}ms"
            )
        return (
            f"TEMPORAL-VIOLATED: {self.specs_violated} specs, "
            f"{len(self.violations)} violations "
            f"({self.specs_checked} checked, {self.duration_ms:.1f}ms)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "specs_checked": self.specs_checked,
            "specs_passed": self.specs_passed,
            "specs_violated": self.specs_violated,
            "violation_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
            "duration_ms": round(self.duration_ms, 3),
        }


def validate_sequence(
    state_trace: list[StateTraceEntry],
    registry: TemporalRegistry,
) -> TemporalValidationResult:
    """Run all temporal specs against a full state trace.

    Each temporal spec receives the complete trace and returns
    any violations it finds. This is the core temporal validation
    entry point.

    Args:
        state_trace: Ordered list of (entry, state_before, state_after).
        registry: Temporal registry with registered specs.

    Returns:
        TemporalValidationResult with aggregate violations.
    """
    start_time = time.monotonic()
    result = TemporalValidationResult()

    for spec in registry.specs:
        result.specs_checked += 1
        spec_violations: list[TemporalViolation] = []

        for cond_name, condition in spec.conditions:
            try:
                violations = condition(state_trace)
            except Exception as exc:
                _log(f"temporal condition {spec.name}/{cond_name} error: {exc}")
                violations = [
                    TemporalViolation(
                        spec_name=spec.name,
                        detail=f"condition {cond_name!r} error: {exc}",
                    )
                ]
            spec_violations.extend(violations)

        if spec_violations:
            result.specs_violated += 1
            result.violations.extend(spec_violations)
        else:
            result.specs_passed += 1

    result.duration_ms = (time.monotonic() - start_time) * 1000
    _log(f"temporal validation: {result.summary()}")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 10. TEMPORAL SPEC FACTORIES — three starter temporal properties
# ═══════════════════════════════════════════════════════════════════════════


def temporal_init_before_use(
    key: str,
    *,
    init_operation: MutationOp = MutationOp.SET,
    use_operation: MutationOp = MutationOp.INCREMENT,
) -> TemporalSpec:
    """Build a temporal spec: key must be initialized before first use.

    Scans the trace for the first mutation that uses the key
    (e.g. INCREMENT) and verifies that a prior mutation initialized it
    (e.g. SET). If the first mutation on the key is a use without
    prior init, that's a temporal violation.

    Args:
        key: The state key to track.
        init_operation: The operation that counts as initialization.
        use_operation: The operation that counts as use.

    Returns:
        A TemporalSpec ready for registration.
    """
    spec = TemporalSpec(
        name=f"init_before_use:{key}",
        description=f"{key!r} must be {init_operation.value} before first {use_operation.value}",
    )

    def _check(trace: list[StateTraceEntry]) -> list[TemporalViolation]:
        initialized = False
        violations: list[TemporalViolation] = []

        for entry, _state_before, _state_after in trace:
            for m in entry.state_mutations:
                if m.key != key:
                    continue
                if m.operation == init_operation:
                    initialized = True
                elif m.operation == use_operation and not initialized:
                    violations.append(
                        TemporalViolation(
                            spec_name=spec.name,
                            detail=(
                                f"{key!r} used ({use_operation.value}) at "
                                f"seq={entry.sequence_number} before "
                                f"initialization ({init_operation.value})"
                            ),
                            involved_events=(entry.event_id,),
                            first_sequence=entry.sequence_number,
                            last_sequence=entry.sequence_number,
                        )
                    )
                    return violations  # first violation is definitive

        return violations

    spec.add_condition("init_precedes_use", _check)
    return spec


def temporal_single_transition_per_cycle(
    key: str,
    *,
    cycle_field: str = "cycle_id",
) -> TemporalSpec:
    """Build a temporal spec: state key cannot change twice within same cycle.

    Groups events by payload[cycle_field]. Within each cycle, the key
    must not undergo more than one state change (SET mutation).

    Args:
        key: The state key to track.
        cycle_field: Payload field that identifies the cycle.

    Returns:
        A TemporalSpec ready for registration.
    """
    spec = TemporalSpec(
        name=f"single_transition_per_cycle:{key}",
        description=f"{key!r} cannot change twice within same {cycle_field!r}",
    )

    def _check(trace: list[StateTraceEntry]) -> list[TemporalViolation]:
        # Track: cycle_id -> list of (entry, mutation) for SET on this key
        cycle_mutations: dict[str, list[tuple[EventLogEntry, StateMutation]]] = {}

        for entry, _state_before, _state_after in trace:
            cycle_id = entry.payload.get(cycle_field)
            if cycle_id is None:
                continue
            cycle_str = str(cycle_id)

            for m in entry.state_mutations:
                if m.key == key and m.operation == MutationOp.SET:
                    if cycle_str not in cycle_mutations:
                        cycle_mutations[cycle_str] = []
                    cycle_mutations[cycle_str].append((entry, m))

        violations: list[TemporalViolation] = []
        for cycle_id, mutations in cycle_mutations.items():
            if len(mutations) > 1:
                event_ids = tuple(e.event_id for e, _m in mutations)
                seqs = [e.sequence_number for e, _m in mutations]
                violations.append(
                    TemporalViolation(
                        spec_name=spec.name,
                        detail=(
                            f"{key!r} changed {len(mutations)} times in "
                            f"cycle {cycle_id!r} at sequences {seqs}"
                        ),
                        involved_events=event_ids,
                        first_sequence=min(seqs),
                        last_sequence=max(seqs),
                    )
                )

        return violations

    spec.add_condition("single_change_per_cycle", _check)
    return spec


def temporal_idempotency_scope(
    *,
    idempotency_field: str = "idempotency_key",
    scope_field: str = "session_id",
    window_seconds: float = 0,
) -> TemporalSpec:
    """Build a temporal spec: idempotency key must not repeat across scopes.

    Scans the trace for duplicate idempotency keys across different
    scope values (e.g. different sessions). If window_seconds > 0,
    only flags duplicates within the time window (based on event_time).

    Args:
        idempotency_field: Payload field containing the idempotency key.
        scope_field: Payload field that defines the scope boundary.
        window_seconds: Time window in seconds (0 = unlimited).

    Returns:
        A TemporalSpec ready for registration.
    """
    spec = TemporalSpec(
        name="idempotency_scope",
        description=(
            f"idempotency key ({idempotency_field!r}) must not repeat "
            f"across {scope_field!r} scopes"
            + (f" within {window_seconds}s" if window_seconds > 0 else "")
        ),
    )

    def _parse_time(iso_str: str) -> Optional[float]:
        """Best-effort parse of ISO8601 to epoch seconds."""
        try:
            import datetime

            dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.timestamp()
        except (ValueError, AttributeError):
            return None

    def _check(trace: list[StateTraceEntry]) -> list[TemporalViolation]:
        # Track: idem_key -> list of (entry, scope)
        seen: dict[str, list[tuple[EventLogEntry, str]]] = {}

        for entry, _state_before, _state_after in trace:
            idem_key = entry.payload.get(idempotency_field)
            scope = entry.payload.get(scope_field)
            if idem_key is None:
                continue

            idem_str = str(idem_key)
            scope_str = str(scope) if scope is not None else "__no_scope__"

            if idem_str not in seen:
                seen[idem_str] = []
            seen[idem_str].append((entry, scope_str))

        violations: list[TemporalViolation] = []
        for idem_key, occurrences in seen.items():
            if len(occurrences) < 2:
                continue

            # Check for cross-scope duplicates
            scopes_seen: dict[str, EventLogEntry] = {}
            for entry, scope in occurrences:
                if scope in scopes_seen:
                    # Same scope, same key — that's within-scope (not our concern)
                    continue
                if scope not in scopes_seen:
                    # First time seeing this scope for this key
                    scopes_seen[scope] = entry

            # Now look for the actual cross-scope pairs
            scope_entries: dict[str, list[EventLogEntry]] = {}
            for entry, scope in occurrences:
                if scope not in scope_entries:
                    scope_entries[scope] = []
                scope_entries[scope].append(entry)

            if len(scope_entries) < 2:
                # All occurrences in same scope — not a cross-scope violation
                continue

            # We have cross-scope reuse
            all_entries = [e for e, _s in occurrences]

            # Apply time window filter if configured
            if window_seconds > 0:
                times = [(e, _parse_time(e.event_time)) for e in all_entries]
                valid_times = [(e, t) for e, t in times if t is not None]
                if len(valid_times) >= 2:
                    valid_times.sort(key=lambda x: x[1])  # type: ignore[arg-type]
                    first_t = valid_times[0][1]
                    last_t = valid_times[-1][1]
                    assert first_t is not None and last_t is not None
                    if last_t - first_t > window_seconds:
                        continue  # outside window

            event_ids = tuple(e.event_id for e in all_entries)
            seqs = [e.sequence_number for e in all_entries]
            scope_list = list(scope_entries.keys())
            violations.append(
                TemporalViolation(
                    spec_name=spec.name,
                    detail=(
                        f"idempotency key {idem_key!r} reused across "
                        f"scopes {scope_list} at sequences {seqs}"
                    ),
                    involved_events=event_ids,
                    first_sequence=min(seqs),
                    last_sequence=max(seqs),
                )
            )

        return violations

    spec.add_condition("no_cross_scope_reuse", _check)
    return spec


# ═══════════════════════════════════════════════════════════════════════════
# 11. TEMPORAL REPLAY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════


def build_state_trace(
    entries: list[EventLogEntry],
    initial_state: Optional[dict[str, Any]] = None,
) -> list[StateTraceEntry]:
    """Build a state trace from replay entries.

    Replays state forward and captures (entry, before, after) at each step.
    This is the data structure temporal specs consume.

    Args:
        entries: Ordered event log entries.
        initial_state: Starting state (from checkpoint).

    Returns:
        List of (entry, state_before, state_after) tuples.
    """
    state = dict(initial_state) if initial_state else {}
    trace: list[StateTraceEntry] = []

    for entry in entries:
        state_before = dict(state)
        apply_mutations(state, entry.state_mutations)
        state_after = dict(state)
        trace.append((entry, state_before, state_after))

    return trace


def validate_replay_temporal(
    entries: list[EventLogEntry],
    temporal_registry: TemporalRegistry,
    initial_state: Optional[dict[str, Any]] = None,
) -> TemporalValidationResult:
    """Run temporal validation across a complete replay.

    Builds the state trace from entries, then runs all temporal specs.
    Designed to run as a post-pass after replay_advanced_verify and
    validate_replay_against_specs complete.

    Args:
        entries: Ordered event log entries (same as other validators).
        temporal_registry: Registry of temporal specs.
        initial_state: Starting state (from checkpoint).

    Returns:
        TemporalValidationResult with aggregate violations.
    """
    trace = build_state_trace(entries, initial_state)
    return validate_sequence(trace, temporal_registry)


def temporal_violations_to_drifts(
    result: TemporalValidationResult,
) -> list[ExtendedDrift]:
    """Convert temporal violations to ExtendedDrift records.

    Maps each TemporalViolation to an ExtendedDrift with
    TEMPORAL_VIOLATION classification, enabling unified
    drift reporting across all validation layers.

    Args:
        result: Temporal validation result.

    Returns:
        List of ExtendedDrift records.
    """
    drifts: list[ExtendedDrift] = []
    for v in result.violations:
        drifts.append(
            ExtendedDrift(
                event_id=v.involved_events[0] if v.involved_events else "unknown",
                sequence_number=v.first_sequence,
                drift_class=ExtendedDriftClass.TEMPORAL_VIOLATION,
                detail=v.detail,
            )
        )
    return drifts


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = [
    # Core types
    "SpecConditionResult",
    "SpecViolation",
    "SpecCondition",
    "PrimitiveSpec",
    # Registry
    "SpecRegistry",
    # Validation
    "SpecValidationResult",
    "validate_against_spec",
    # Batch
    "SpecReplayResult",
    "validate_replay_against_specs",
    # Spec builders
    "spec_increment_counter",
    "spec_state_transition",
    "spec_idempotency_key",
    # Extended classification
    "ExtendedDriftClass",
    "DRIFT_PRIORITY",
    "highest_priority_drift",
    "ExtendedDrift",
    # Integrated
    "validate_entry_against_spec",
    # Temporal types
    "StateTraceEntry",
    "TemporalViolation",
    "TemporalCondition",
    "TemporalSpec",
    "TemporalRegistry",
    # Temporal validation
    "TemporalValidationResult",
    "validate_sequence",
    # Temporal spec builders
    "temporal_init_before_use",
    "temporal_single_transition_per_cycle",
    "temporal_idempotency_scope",
    # Temporal replay integration
    "build_state_trace",
    "validate_replay_temporal",
    "temporal_violations_to_drifts",
]
