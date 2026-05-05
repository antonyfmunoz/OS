"""
Intent memory — aggregate outcome tracking for deterministic learning.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STABLE CORE MODULE
# Changes require full replay + invariant validation.
# Breaking changes to the public API require a version bump.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Stores per-intent-type + goal aggregate records in RuntimeStateStore.
Each record tracks success/failure counts (with failure classification),
last outcome, execution count, and timestamps for decay.  Used by the
decision engine to block repeatedly failing intents.

Key format:
    intent_memory.{intent_type}.{goal_hash}

This is NOT a log.  It is an aggregate that gets SET-overwritten on
each terminal event.  No list mutations.  No scans.  No appends.

Stable public API (v1):
    score_intent(memory, meta=None) → float
    lookup_intent_memory(state, intent_type, goal) → dict | None
    build_memory_update_mutations(...) → list[dict]
    should_block_intent(...) → (bool, dict | None)
    should_decay(memory, current_timestamp) → bool
    compute_memory_key(intent_type, goal) → str

Breaking change to any of these signatures requires a version bump.

Design constraints:
- Deterministic: same sequence of terminal events → same memory state.
- Replay-safe: SET-only mutations, no APPEND or list patterns.
- Inspectable: memory records are plain dicts in RuntimeStateStore.
- Minimal: only stores what the decision guard needs.
- score_intent NEVER reads plan meta — scope isolation enforced.

Failure classification:
- execution_failed: real execution crash
- execution_timed_out: timeout (may be transient)
- execution_rejected: rejected by authority/policy
- driver_failure: plan disappeared or internal driver error

Decay:
- Read-time only — never mutates memory.
- After DECAY_WINDOW with no updates, stale blocks are treated as decayed.

Usage:
    from umh.substrate.intent_memory import (
        compute_memory_key,
        build_memory_update_mutations,
        lookup_intent_memory,
        should_decay,
    )
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


# ─── Constants ───────────────────────────────────────────────────────

# Fixed decay window: 24 hours in seconds.
# After this duration with no updates, stale failures are treated as
# decayed at read time.  Must be a constant — never dynamic.
DECAY_WINDOW: int = 86_400  # 24h

# The four failure type buckets.  No dynamic keys allowed.
FAILURE_TYPES: tuple[str, ...] = (
    "execution_failed",
    "execution_timed_out",
    "execution_rejected",
    "driver_failure",
)


# ─── Key computation ─────────────────────────────────────────────────


def _hash_goal(goal: dict[str, Any]) -> str:
    """Deterministic hash of goal dict. Same goal → same hash, always."""
    canonical = json.dumps(
        goal, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def compute_memory_key(intent_type: str, goal: dict[str, Any]) -> str:
    """Build the RuntimeStateStore key for an intent memory record.

    Format: intent_memory.{intent_type}.{goal_hash}
    Deterministic: same intent_type + goal always produces the same key.
    """
    return f"intent_memory.{intent_type}.{_hash_goal(goal)}"


# ─── Memory record schema ───────────────────────────────────────────


def _empty_failure_by_type() -> dict[str, int]:
    """Create zeroed failure classification dict.  Fixed keys only."""
    return {ft: 0 for ft in FAILURE_TYPES}


def _empty_memory(intent_type: str, goal: dict[str, Any]) -> dict[str, Any]:
    """Create a fresh memory record with zero counts."""
    return {
        "intent_type": intent_type,
        "goal": goal,
        "success_count": 0,
        "failure_count": 0,
        "failure_by_type": _empty_failure_by_type(),
        "last_outcome": "",
        "last_reason": "",
        "execution_count": 0,
        "last_updated_at": "",
        "last_success_at": None,
    }


# ─── Lookup ──────────────────────────────────────────────────────────


def lookup_intent_memory(
    state: dict[str, Any],
    intent_type: str,
    goal: dict[str, Any],
) -> dict[str, Any] | None:
    """Read an intent memory record from a state snapshot.

    Returns None if no memory exists for this intent_type + goal.
    Pure read — no side effects.
    """
    key = compute_memory_key(intent_type, goal)
    return state.get(key)


# ─── Mutation builders ───────────────────────────────────────────────


def build_memory_update_mutations(
    intent_type: str,
    goal: dict[str, Any],
    outcome: str,
    reason: str,
    timestamp: str,
    state: dict[str, Any],
    failure_type: str = "",
) -> list[dict[str, Any]]:
    """Build SET mutations to update an intent memory record.

    Args:
        intent_type: The intent type string (e.g., "lifecycle_finalize").
        goal: The intent goal dict.
        outcome: "completed" or "failed".
        reason: Human-readable reason string (empty for success).
        timestamp: ISO timestamp from the terminal event.
        state: Current state snapshot for reading existing memory.
        failure_type: Classification bucket for failures.  Must be one of
            FAILURE_TYPES when outcome is "failed".  Ignored on success.

    Returns:
        A single-element list containing one SET mutation.
        Always overwrites the full record — no incremental ops.
    """
    key = compute_memory_key(intent_type, goal)
    existing = state.get(key)

    if existing is not None:
        record = dict(existing)
        # Back-compat: ensure failure_by_type exists for pre-upgrade records
        if "failure_by_type" not in record:
            record["failure_by_type"] = _empty_failure_by_type()
        else:
            record["failure_by_type"] = dict(record["failure_by_type"])
        if "last_success_at" not in record:
            record["last_success_at"] = None
    else:
        record = _empty_memory(intent_type, goal)

    record["execution_count"] += 1
    record["last_outcome"] = outcome
    record["last_reason"] = reason
    record["last_updated_at"] = timestamp

    if outcome == "completed":
        record["success_count"] += 1
        record["last_success_at"] = timestamp
    elif outcome == "failed":
        record["failure_count"] += 1
        # Classify failure into the correct bucket
        if failure_type in FAILURE_TYPES:
            record["failure_by_type"][failure_type] += 1

    return [{"op": "SET", "key": key, "value": record}]


# ─── Intent scoring ────────────────────────────────────────────────


def score_intent(
    memory: dict[str, Any] | None,
    meta: dict[str, Any] | None = None,
) -> float:
    """Compute a deterministic score for an intent based on its memory.

    **Stable API v1 — breaking change requires version bump.**

    Formula:
        (success_count / execution_count) - (failure_count * penalty_weight)

    penalty_weight comes from meta["failure_penalty_weight"] when meta
    is provided, otherwise defaults to 0.1 (backward compatible).

    The success ratio (0.0–1.0) rewards consistency while the failure
    penalty is a raw count multiplier that accumulates permanent drag.

    Returns 0.0 when memory is None (unknown intent = neutral).
    Returns 0.0 when execution_count is 0 (defensive — should not happen
    in practice since memory is only created on terminal events).

    This is a pure function — no side effects, no state reads.
    Deterministic: same memory dict + same meta → same score, always.

    Coupling invariant: this function NEVER reads plan-scope meta.
    The meta argument, when provided, must be intent-scope meta.
    The function itself is scope-agnostic — the caller is responsible
    for passing the correct scope's meta.
    """
    if memory is None:
        return 0.0

    execution_count = memory.get("execution_count", 0)
    if execution_count == 0:
        return 0.0

    success_count = memory.get("success_count", 0)
    failure_count = memory.get("failure_count", 0)

    # Self-tuning: use meta penalty weight when available
    penalty_weight = 0.1
    if meta is not None:
        penalty_weight = meta.get("failure_penalty_weight", 0.1)

    return (success_count / execution_count) - (failure_count * penalty_weight)


# ─── Decay (read-time only) ─────────────────────────────────────────


def should_decay(memory: dict[str, Any], current_timestamp: str) -> bool:
    """Determine if a blocked memory record has decayed.

    Decay rule (deterministic):
        Decayed if failure_count >= 3 AND success_count == 0
        AND (current_timestamp - last_updated_at) > DECAY_WINDOW.

    This is a pure read-time interpretation.  It NEVER mutates memory.

    Args:
        memory: An intent memory record dict.
        current_timestamp: ISO-8601 timestamp of the current event.

    Returns:
        True if the memory should be treated as decayed.
    """
    from datetime import datetime, timezone

    failure_count = memory.get("failure_count", 0)
    success_count = memory.get("success_count", 0)
    last_updated = memory.get("last_updated_at", "")

    if failure_count < 3 or success_count > 0 or not last_updated:
        return False

    try:
        last_dt = datetime.fromisoformat(last_updated)
        current_dt = datetime.fromisoformat(current_timestamp)
        # Normalize to UTC for comparison
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        if current_dt.tzinfo is None:
            current_dt = current_dt.replace(tzinfo=timezone.utc)
        elapsed = (current_dt - last_dt).total_seconds()
        return elapsed > DECAY_WINDOW
    except (ValueError, TypeError):
        return False


# ─── Decision guard ─────────────────────────────────────────────────


def should_block_intent(
    state: dict[str, Any],
    intent_type: str,
    goal: dict[str, Any],
    failure_threshold: int = 3,
    current_timestamp: str = "",
) -> tuple[bool, dict[str, Any] | None]:
    """Check whether an intent should be blocked based on memory.

    Blocking rule (deterministic):
        Block if ALL of:
        1. failure_count >= failure_threshold
        2. success_count == 0
        3. NOT decayed (stale failures are forgiven)
        4. failure_by_type["execution_failed"] >= 2 (require real failures)

    Args:
        state: Current state snapshot.
        intent_type: The intent type to check.
        goal: The intent goal to check.
        failure_threshold: Minimum failures before blocking (default 3).
        current_timestamp: ISO timestamp for decay check.  Empty string
            disables decay (treats all as non-decayed).

    Returns:
        (should_block, memory_record) — memory_record is None if no
        memory exists.  should_block is False when no memory exists.
    """
    memory = lookup_intent_memory(state, intent_type, goal)
    if memory is None:
        return False, None

    failure_count = memory.get("failure_count", 0)
    success_count = memory.get("success_count", 0)

    # Success recovery: any success means don't block
    if success_count > 0:
        return False, memory

    # Below threshold: don't block
    if failure_count < failure_threshold:
        return False, memory

    # Decay check: stale failures are forgiven
    if current_timestamp and should_decay(memory, current_timestamp):
        return False, memory

    # Require real execution failures, not just timeouts/rejections
    failure_by_type = memory.get("failure_by_type", {})
    exec_failed_count = failure_by_type.get("execution_failed", 0)
    if exec_failed_count < 2:
        return False, memory

    return True, memory
