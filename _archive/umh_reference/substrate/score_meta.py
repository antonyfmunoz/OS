"""
Score meta — self-tuning scoring parameters via deterministic adaptation.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STABLE CORE MODULE
# Changes require full replay + invariant validation.
# Breaking changes to the public API require a version bump.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## What this IS

A deterministic adaptive control loop for failure penalty weights.
"Learning" here means: parameter adjustment via observed outcome ratios.
- Memory = facts (success_count, failure_count, timestamps).
- Meta = interpretation weight (how heavily to penalize failures).

The system observes terminal outcomes, computes rate imbalances,
and adjusts a single scalar (failure_penalty_weight) within fixed
bounds using fixed step sizes.  That is all it does.

## What this is NOT

- NOT machine learning.  No gradient descent.  No loss function.
- NOT probabilistic.  No randomness.  No exploration/exploitation.
- NOT stateful history.  No lists, no sliding windows, no logs.

There is no randomness, no gradient descent, and no probabilistic
exploration anywhere in this module.  Every output is a deterministic
function of its inputs.

## Module contract

INPUT:
    - memory (dict): intent or plan memory record containing
      success_count, failure_count.  Must be the UPDATED record
      (after terminal event applied).
    - meta (dict | None): current score_meta record, or None if
      first time.  Optional.

OUTPUT:
    - score (float): from score_intent / score_plan.
    - optional SET mutation(s) for score_meta state.

GUARANTEES:
    - Deterministic: same inputs → same outputs, always.
    - Bounded: weights ∈ [MIN_PENALTY_WEIGHT, MAX_PENALTY_WEIGHT].
    - Monotonic: single-signal sequences produce monotonic weight
      trajectories (failure-only → non-decreasing, success-only →
      non-increasing).
    - No side effects: pure functions only.  No I/O, no logging,
      no state mutation.
    - SET-only: all mutations are full-record overwrites.  No APPEND,
      no incremental ops, no list patterns.
    - Max step: weight changes by at most 2 * scope_delta per call
      (recovery boost ceiling).

## Stable public API (v1)

    lookup_score_meta(state, scope) → dict | None
    build_score_meta_adjustment(scope, memory, meta) → list[dict]
    get_penalty_weight(meta) → float
    compute_score_meta_key(scope) → str

Breaking change to any of these signatures requires a version bump.

## Extension boundaries

ALLOWED future extensions:
    - Cross-intent coordination layer (reads meta, does not write).
    - Higher-level arbitration (selects between scopes externally).
    - External policy injection (overrides via coordinator, not here).

NOT ALLOWED:
    - Modifying score_meta record internals (add fields → version bump).
    - Introducing non-determinism (randomness, time-dependent logic).
    - Adding stateful history (lists, sliding windows, append patterns).
    - Reading plan meta from intent scoring or vice versa.
    - Writing meta from anywhere except the intent coordinator.

## Key format

    score_meta.{scope}      scope ∈ {"intent", "plan"}

## Record schema

    {
        "failure_penalty_weight": float,   # [0.05, 0.3], default 0.1
        "last_updated_at": str,            # observability only
        "adjustment_count": int,           # total adjustments applied
        "last_direction": str,             # "up" | "down" | ""
        "saturation_count": int,           # consecutive eligible at clamp
        "version": int                     # schema version (currently 1)
    }

    All fields are scalars.  No lists, no nested dynamic structures.
    version is always present (defaulted to 1 on read for pre-upgrade
    records).

## Adjustment algorithm

    1. Recompute execution_count = success_count + failure_count.
    2. Guard: execution_count == 0 → no adjustment (div-zero).
    3. Guard: execution_count < 5 → no adjustment.
    4. Compute success_rate, failure_rate from recomputed count.
    5. Guard: |success_rate - failure_rate| < 0.1 → no adjustment (deadband).
    6. Guard: steady-state lock after 20+ executions with delta < 0.05.
    7. Hysteresis: if direction flipped, require delta_rate >= 0.2.
    8. Guard: at boundary moving same direction → saturation
       (emit event, no weight change, saturation_count++).
    9. Recovery boost: if success dominates by >= 0.3, use 2x delta.
    10. Adjust penalty_weight by scope-specific delta:
        intent → 0.005, plan → 0.01 (doubled under recovery).
    11. Clamp to [0.05, 0.3].
    12. Guard: abs(new - current) < 1e-9 → no adjustment (epsilon).

## Usage

    from umh.substrate.score_meta import (
        lookup_score_meta,
        build_score_meta_adjustment,
        get_penalty_weight,
    )
"""

from __future__ import annotations

from typing import Any


# ─── Constants ──────────────────────────────────────────────────────

SCOPES: tuple[str, ...] = ("intent", "plan")

DEFAULT_PENALTY_WEIGHT: float = 0.1

# Scope-specific step sizes for penalty adjustment.
INTENT_DELTA: float = 0.005
PLAN_DELTA: float = 0.01

_DELTA: dict[str, float] = {
    "intent": INTENT_DELTA,
    "plan": PLAN_DELTA,
}

# Deadband: no adjustment when |success_rate - failure_rate| < this.
DEADBAND: float = 0.1

# Minimum executions before adjustment is allowed.
MIN_EXECUTIONS: int = 5

# Clamp bounds for failure_penalty_weight.
MIN_PENALTY_WEIGHT: float = 0.05
MAX_PENALTY_WEIGHT: float = 0.30

# Hysteresis: direction flip requires stronger signal than normal deadband.
HYSTERESIS_DEADBAND: float = 0.2

# Recovery boost: when success dominates by this margin, use 2x delta.
RECOVERY_THRESHOLD: float = 0.3

# Steady-state lock: stricter deadband after sufficient data.
# Prevents micro-adjustments in mature, stable environments.
STEADY_STATE_DEADBAND: float = 0.05
STEADY_STATE_MIN_EXECUTIONS: int = 20

# Saturation: consecutive eligible adjustments at a clamp boundary
# before emitting a saturation warning event.
SATURATION_WARN_THRESHOLD: int = 3

# Schema version for forward migration ability.
META_VERSION: int = 1


# ─── Key computation ────────────────────────────────────────────────


def compute_score_meta_key(scope: str) -> str:
    """Build the RuntimeStateStore key for a score meta record.

    Args:
        scope: "intent" or "plan".

    Returns:
        Key string: score_meta.{scope}
    """
    return f"score_meta.{scope}"


# ─── Record schema ──────────────────────────────────────────────────


def _empty_meta() -> dict[str, Any]:
    """Create a fresh score meta record with default values."""
    return {
        "failure_penalty_weight": DEFAULT_PENALTY_WEIGHT,
        "last_updated_at": "",
        "adjustment_count": 0,
        "last_direction": "",
        "saturation_count": 0,
        "version": META_VERSION,
    }


# ─── Lookup ─────────────────────────────────────────────────────────


def lookup_score_meta(
    state: dict[str, Any],
    scope: str,
) -> dict[str, Any] | None:
    """Read a score meta record from a state snapshot.

    **Stable API v1 — breaking change requires version bump.**

    Returns None if no meta exists for this scope.
    If the stored record is malformed (missing required fields or
    wrong types), returns a default meta to prevent silent corruption
    from propagating into scoring.

    Pure read — no side effects.
    """
    key = compute_score_meta_key(scope)
    raw = state.get(key)
    if raw is None:
        return None

    # Schema validation: required fields with correct types
    weight = raw.get("failure_penalty_weight")
    count = raw.get("adjustment_count")

    if not isinstance(weight, (int, float)) or not isinstance(count, int):
        # Corrupted record — return safe defaults
        return _empty_meta()

    # Back-compat: ensure new fields exist for pre-upgrade records
    needs_patch = (
        "last_direction" not in raw
        or "saturation_count" not in raw
        or "version" not in raw
    )
    if needs_patch:
        patched = dict(raw)
        patched.setdefault("last_direction", "")
        patched.setdefault("saturation_count", 0)
        patched.setdefault("version", META_VERSION)
        return patched

    return raw


def get_penalty_weight(meta: dict[str, Any] | None) -> float:
    """Extract failure_penalty_weight from a meta record.

    **Stable API v1 — breaking change requires version bump.**

    Returns DEFAULT_PENALTY_WEIGHT when meta is None or key is missing.
    Defensive sanity clamp: if stored weight is outside [0.0, 1.0],
    returns DEFAULT_PENALTY_WEIGHT.  Never trust state blindly.

    Pure, deterministic, no side effects.
    """
    if meta is None:
        return DEFAULT_PENALTY_WEIGHT
    weight = meta.get("failure_penalty_weight", DEFAULT_PENALTY_WEIGHT)
    if not isinstance(weight, (int, float)) or weight < 0.0 or weight > 1.0:
        return DEFAULT_PENALTY_WEIGHT
    return weight


# ─── Adjustment builder ────────────────────────────────────────────


def build_score_meta_adjustment(
    scope: str,
    memory: dict[str, Any],
    meta: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build SET mutations to adjust the score meta for a scope.

    **Stable API v1 — breaking change requires version bump.**

    Reads normalized outcome signals from the UPDATED memory record
    and adjusts failure_penalty_weight by the scope-specific delta.

    Guards (return empty list — no adjustment):
    1. execution_count == 0 (div-zero hardening).
    2. execution_count < MIN_EXECUTIONS (insufficient sample).
    3. |success_rate - failure_rate| < DEADBAND (signal too weak).
    4. Direction flip with delta_rate < HYSTERESIS_DEADBAND (hysteresis).
    5. abs(new - current) < 1e-9 (epsilon no-op, replay idempotency).

    Boundary behavior:
    - At clamp moving same direction: weight unchanged, saturation_count
      incremented.  Returns a SET mutation so callers can detect
      saturation (saturation_count >= SATURATION_WARN_THRESHOLD).
    - At clamp with reversed signal: normal adjustment (decrease/increase).

    Recovery boost:
    - When success_rate - failure_rate >= RECOVERY_THRESHOLD, uses 2x
      delta to escape pessimism faster.

    Timestamp is NOT used in adjustment logic.  Callers write
    last_updated_at into the returned record for observability.

    Args:
        scope: "intent" or "plan".
        memory: The UPDATED memory record (after the terminal event
            has been applied).  Must contain success_count, failure_count.
        meta: The current score meta record, or None if first time.

    Returns:
        A single-element list with one SET mutation, or an empty list
        if no adjustment is warranted.

    Pure function.  Deterministic.  No side effects.
    """
    success_count = memory.get("success_count", 0)
    failure_count = memory.get("failure_count", 0)

    # Recompute execution_count from counts — never trust stored value.
    execution_count = success_count + failure_count

    # Guard: explicit div-zero
    if execution_count == 0:
        return []

    # Guard: insufficient sample
    if execution_count < MIN_EXECUTIONS:
        return []

    success_rate = success_count / execution_count
    failure_rate = failure_count / execution_count

    delta_rate = abs(success_rate - failure_rate)

    # Guard: deadband — signal too weak
    if delta_rate < DEADBAND:
        return []

    # Guard: steady-state lock — stricter filter for mature systems.
    # After sufficient data, even moderate imbalances should not trigger
    # adjustment if the delta is small.  Prevents micro-adjustments and
    # guarantees convergence freeze in stable environments.
    if (
        execution_count >= STEADY_STATE_MIN_EXECUTIONS
        and delta_rate < STEADY_STATE_DEADBAND
    ):
        return []

    # Read current state from meta
    current_weight = get_penalty_weight(meta)
    current_count = 0
    last_direction = ""
    saturation_count = 0
    if meta is not None:
        current_count = meta.get("adjustment_count", 0)
        last_direction = meta.get("last_direction", "")
        saturation_count = meta.get("saturation_count", 0)

    # Determine intended direction
    if failure_rate > success_rate:
        new_direction = "up"
    else:
        new_direction = "down"

    # Hysteresis: direction flip requires stronger signal
    if last_direction and new_direction != last_direction:
        if delta_rate < HYSTERESIS_DEADBAND:
            return []

    # Boundary saturation detection: at clamp moving same direction
    # Weight stays unchanged, saturation_count increments.
    if current_weight >= MAX_PENALTY_WEIGHT and new_direction == "up":
        new_sat = saturation_count + 1
        record: dict[str, Any] = {
            "failure_penalty_weight": current_weight,
            "last_updated_at": "",
            "adjustment_count": current_count,
            "last_direction": last_direction,
            "saturation_count": new_sat,
            "version": META_VERSION,
        }
        key = compute_score_meta_key(scope)
        return [{"op": "SET", "key": key, "value": record}]

    if current_weight <= MIN_PENALTY_WEIGHT and new_direction == "down":
        new_sat = saturation_count + 1
        record = {
            "failure_penalty_weight": current_weight,
            "last_updated_at": "",
            "adjustment_count": current_count,
            "last_direction": last_direction,
            "saturation_count": new_sat,
            "version": META_VERSION,
        }
        key = compute_score_meta_key(scope)
        return [{"op": "SET", "key": key, "value": record}]

    # Determine delta (scope-specific)
    delta = _DELTA.get(scope, PLAN_DELTA)

    # Recovery boost: strong success dominance → 2x delta for faster
    # escape from pessimism.  Only applies when decreasing penalty.
    if new_direction == "down" and (success_rate - failure_rate) >= RECOVERY_THRESHOLD:
        delta = delta * 2

    # Apply adjustment
    if new_direction == "up":
        new_weight = min(current_weight + delta, MAX_PENALTY_WEIGHT)
    else:
        new_weight = max(current_weight - delta, MIN_PENALTY_WEIGHT)

    # Epsilon no-op guard — prevent silent state churn
    if abs(new_weight - current_weight) < 1e-9:
        return []

    # Build updated record (full overwrite).  Reset saturation_count
    # since weight actually changed.
    record = {
        "failure_penalty_weight": new_weight,
        "last_updated_at": "",
        "adjustment_count": current_count + 1,
        "last_direction": new_direction,
        "saturation_count": 0,
        "version": META_VERSION,
    }

    key = compute_score_meta_key(scope)
    return [{"op": "SET", "key": key, "value": record}]
