"""
Plan scoring — deterministic strategy selection from stored outcomes.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STABLE CORE MODULE
# Changes require full replay + invariant validation.
# Breaking changes to the public API require a version bump.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enables the system to choose between multiple candidate plans for the
same intent_type based on past performance.  All functions are pure,
deterministic, and replay-safe.

Stable public API (v1):
    score_plan(memory, meta=None) → float
    lookup_plan_memory(state, intent_type, goal, plan_id) → dict | None
    build_plan_memory_update_mutations(...) → list[dict]
    compute_plan_memory_key(intent_type, goal, plan_id) → str
    select_best_plan(plan_ids, intent_type, goal, state, meta=None) → str | None
    compute_state_signature(state) → str

Breaking change to any of these signatures requires a version bump.

Plan memory key format:
    plan_memory.{intent_type}.{goal_hash}.{plan_id}

Each plan memory record tracks per-plan success/failure counts.
Separate from intent-level memory — intent memory tracks aggregate
outcomes for the decision guard; plan memory tracks per-plan outcomes
for strategy selection.

Scoring rule (deterministic, no randomness):
    score = success_rate - (failure_count * penalty_weight)
    Untried plans score 0.0 (neutral — not penalized, not boosted).
    Tie-breaker: lexicographic plan_id (stable, deterministic).

Staleness rule (context-aware):
    A plan is stale when BOTH conditions hold:
      1. Time elapsed > STALE_WINDOW_SECONDS
      2. State signature has changed since last execution
    If the state signature is missing (backward compat), falls back
    to time-only staleness.

Design constraints:
- SET-only mutations (no APPEND, no list patterns).
- O(1) lookup per plan (key-based, no scans).
- Pure functions: no side effects, no hidden state.
- Replay-safe: same inputs always produce same outputs.
- score_plan NEVER reads intent meta — scope isolation enforced.

Usage:
    from umh.substrate.plan_scoring import (
        compute_plan_memory_key,
        lookup_plan_memory,
        build_plan_memory_update_mutations,
        compute_state_signature,
        score_plan,
        select_best_plan,
    )
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


# ─── Key computation ─────────────────────────────────────────────────


def _hash_goal(goal: dict[str, Any]) -> str:
    """Deterministic hash of goal dict.  Same goal → same hash, always."""
    canonical = json.dumps(
        goal, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def compute_plan_memory_key(
    intent_type: str, goal: dict[str, Any], plan_id: str
) -> str:
    """Build the RuntimeStateStore key for a plan memory record.

    Format: plan_memory.{intent_type}.{goal_hash}.{plan_id}
    Deterministic: same inputs always produce the same key.
    """
    return f"plan_memory.{intent_type}.{_hash_goal(goal)}.{plan_id}"


# ─── State signature ────────────────────────────────────────────────

# Key prefixes that represent plan-relevant state.  Only keys matching
# these prefixes contribute to the state signature.  This keeps the
# signature stable when unrelated state (logs, ephemeral counters)
# changes, while still detecting meaningful environment shifts.
_SIGNATURE_KEY_PREFIXES: tuple[str, ...] = (
    "intent:",
    "active_intent.",
    "intent_memory.",
    "lifecycle.",
    "session_state.",
)


def compute_state_signature(state: dict[str, Any]) -> str:
    """Compute a deterministic signature of plan-relevant state.

    Properties:
    - Deterministic: same state dict always produces the same hash.
    - Stable: ignores keys outside _SIGNATURE_KEY_PREFIXES, so
      unrelated state changes do not alter the signature.
    - Lightweight: filters keys by prefix, then hashes the sorted
      canonical JSON.  No deep traversal beyond json.dumps.
    - Replay-safe: pure function, no side effects.

    Returns a hex digest string (SHA-256, truncated to 16 chars).
    Returns "" if no relevant keys are found in state.
    """
    relevant: dict[str, Any] = {}
    for key in state:
        for prefix in _SIGNATURE_KEY_PREFIXES:
            if key.startswith(prefix):
                relevant[key] = state[key]
                break

    if not relevant:
        return ""

    canonical = json.dumps(
        relevant,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ─── Plan memory record ─────────────────────────────────────────────


def _empty_plan_memory(plan_id: str) -> dict[str, Any]:
    """Create a fresh plan memory record with zero counts."""
    return {
        "plan_id": plan_id,
        "success_count": 0,
        "failure_count": 0,
        "last_outcome": "",
        "execution_count": 0,
        "last_executed_at": "",
        "last_state_signature": "",
        "last_failure_step_index": None,
        "last_failure_type": "",
    }


# ─── Lookup ──────────────────────────────────────────────────────────


def lookup_plan_memory(
    state: dict[str, Any],
    intent_type: str,
    goal: dict[str, Any],
    plan_id: str,
) -> dict[str, Any] | None:
    """Read a plan memory record from a state snapshot.

    Returns None if no memory exists for this plan.
    Pure read — no side effects.
    """
    key = compute_plan_memory_key(intent_type, goal, plan_id)
    return state.get(key)


# ─── Mutation builders ───────────────────────────────────────────────


def build_plan_memory_update_mutations(
    intent_type: str,
    goal: dict[str, Any],
    plan_id: str,
    outcome: str,
    timestamp: str,
    state: dict[str, Any],
    state_signature: str = "",
    failed_step_index: int | None = None,
    failure_type: str = "",
) -> list[dict[str, Any]]:
    """Build SET mutations to update a plan memory record.

    Args:
        intent_type: The intent type string.
        goal: The intent goal dict.
        plan_id: The plan identifier (deterministic, from compute_plan_id).
        outcome: "completed" or "failed".
        timestamp: ISO timestamp from the terminal event.
        state: Current state snapshot for reading existing memory.
        state_signature: Deterministic hash of plan-relevant state at
            execution time.  Stored in record for context-aware staleness.
            If empty, the existing signature (or "") is preserved.
        failed_step_index: The step index where failure occurred.
            Stored for causal mutation.  None clears on success.
        failure_type: Classification of the failure (execution_failed,
            execution_timed_out, execution_rejected, driver_failure).
            Stored for causal mutation.  Empty string clears on success.

    Returns:
        A single-element list containing one SET mutation.
        Always overwrites the full record — no incremental ops.
    """
    key = compute_plan_memory_key(intent_type, goal, plan_id)
    existing = state.get(key)

    if existing is not None:
        record = dict(existing)
    else:
        record = _empty_plan_memory(plan_id)

    record["execution_count"] += 1
    record["last_outcome"] = outcome
    record["last_executed_at"] = timestamp

    # Store the state signature at execution time.  If caller did not
    # provide one, preserve whatever was already stored (backward compat).
    if state_signature:
        record["last_state_signature"] = state_signature
    elif "last_state_signature" not in record:
        record["last_state_signature"] = ""

    if outcome == "completed":
        record["success_count"] += 1
        # Clear failure context on success — no longer relevant.
        record["last_failure_step_index"] = None
        record["last_failure_type"] = ""
    elif outcome == "failed":
        record["failure_count"] += 1
        # Store failure context for causal mutation.
        if failed_step_index is not None:
            record["last_failure_step_index"] = failed_step_index
        elif "last_failure_step_index" not in record:
            record["last_failure_step_index"] = None
        if failure_type:
            record["last_failure_type"] = failure_type
        elif "last_failure_type" not in record:
            record["last_failure_type"] = ""

    return [{"op": "SET", "key": key, "value": record}]


# ─── Exploration constants ───────────────────────────────────────────

# Minimum number of executions before a plan's score is trusted.
# Plans below this threshold are prioritised for exploration.
MIN_EXECUTIONS_PER_PLAN: int = 2


def get_execution_count(memory: dict[str, Any] | None) -> int:
    """Extract execution_count from a plan memory record.

    Returns 0 for None or missing execution_count.
    Pure, deterministic, no side effects.
    """
    if memory is None:
        return 0
    return memory.get("execution_count", 0)


# ─── Staleness constants ────────────────────────────────────────────

# Plans not executed within this window are considered stale and
# eligible for deterministic re-exploration.  Default: 1 hour.
STALE_WINDOW_SECONDS: int = 3600


def _parse_iso_timestamp(ts: str) -> datetime | None:
    """Parse an ISO 8601 timestamp string to a timezone-aware datetime.

    Returns None if the string is empty or unparseable.
    Pure, no side effects.
    """
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        # Ensure timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def is_stale(
    memory: dict[str, Any] | None,
    current_timestamp: str,
    current_state_signature: str = "",
) -> bool:
    """Determine if a plan is stale and the environment has changed.

    Context-aware staleness rule:
        stale = (time_elapsed > STALE_WINDOW_SECONDS)
                AND (state_signature has changed)

    Safe fallback to time-only staleness when:
    - current_state_signature is empty (caller cannot compute it)
    - last_state_signature is missing from memory (pre-upgrade record)

    Returns False (not stale) when:
    - memory is None (untried — handled by exploration phase)
    - last_executed_at is empty or missing
    - current_timestamp is empty or unparseable
    - either timestamp fails to parse
    - time is stale BUT state signature is unchanged

    Pure function.  No mutation.  No side effects.
    """
    if memory is None:
        return False

    if not current_timestamp:
        return False

    last_str = memory.get("last_executed_at", "")
    if not last_str:
        return False

    current_dt = _parse_iso_timestamp(current_timestamp)
    last_dt = _parse_iso_timestamp(last_str)

    if current_dt is None or last_dt is None:
        return False

    elapsed = (current_dt - last_dt).total_seconds()
    if elapsed <= STALE_WINDOW_SECONDS:
        return False

    # Time threshold crossed — now check state signature.
    last_sig = memory.get("last_state_signature", "")

    # Fallback: if either signature is unavailable, use time-only
    # staleness (backward compatible with pre-upgrade records).
    if not current_state_signature or not last_sig:
        return True

    # Context-aware: only stale if the environment actually changed.
    return current_state_signature != last_sig


def staleness_seconds(
    memory: dict[str, Any] | None,
    current_timestamp: str,
) -> float:
    """Compute seconds since last execution for a plan.

    Returns 0.0 if memory is None, timestamps are missing/unparseable,
    or current_timestamp is empty.  Used for sorting stale plans by
    most-stale-first.

    Pure function.  No mutation.  No side effects.
    """
    if memory is None or not current_timestamp:
        return 0.0

    last_str = memory.get("last_executed_at", "")
    if not last_str:
        return 0.0

    current_dt = _parse_iso_timestamp(current_timestamp)
    last_dt = _parse_iso_timestamp(last_str)

    if current_dt is None or last_dt is None:
        return 0.0

    return max(0.0, (current_dt - last_dt).total_seconds())


# ─── Scoring ─────────────────────────────────────────────────────────

# Default failure penalty coefficient.  Used when no score meta exists.
_FAILURE_PENALTY: float = 0.1


def score_plan(
    memory: dict[str, Any] | None,
    meta: dict[str, Any] | None = None,
) -> float:
    """Compute a deterministic score for a plan based on its memory.

    **Stable API v1 — breaking change requires version bump.**

    Scoring rule:
        If execution_count == 0 (untried): score = 0.0
        Else: score = (success_count / execution_count) - (failure_count * penalty_weight)

    penalty_weight comes from meta["failure_penalty_weight"] when meta
    is provided, otherwise defaults to 0.1 (backward compatible).

    No randomness.  No time weighting.  Pure arithmetic.

    Coupling invariant: this function NEVER reads intent-scope meta.
    The meta argument, when provided, must be plan-scope meta.
    The function itself is scope-agnostic — the caller is responsible
    for passing the correct scope's meta.

    Args:
        memory: A plan memory record dict, or None if no memory exists.
        meta: Score meta record, or None to use default penalty weight.

    Returns:
        A float score.  Higher is better.
    """
    if memory is None:
        return 0.0

    execution_count = memory.get("execution_count", 0)
    if execution_count == 0:
        return 0.0

    success_count = memory.get("success_count", 0)
    failure_count = memory.get("failure_count", 0)

    # Self-tuning: use meta penalty weight when available
    penalty_weight = _FAILURE_PENALTY
    if meta is not None:
        penalty_weight = meta.get("failure_penalty_weight", _FAILURE_PENALTY)

    success_rate = success_count / execution_count
    penalty = failure_count * penalty_weight

    return success_rate - penalty


# ─── Selection ───────────────────────────────────────────────────────


def select_best_plan(
    plan_ids: list[str],
    intent_type: str,
    goal: dict[str, Any],
    state: dict[str, Any],
    meta: dict[str, Any] | None = None,
) -> str | None:
    """Select the best plan from candidates using stored outcomes.

    Selection rule (deterministic):
    1. Score each plan by looking up its plan memory.
    2. Choose the highest score.
    3. Tie-breaker: lexicographic plan_id (stable, deterministic).

    Fallback:
    - No candidates → None.
    - No memory for any plan → first plan (lexicographic order).

    Args:
        plan_ids: List of candidate plan IDs.
        intent_type: The intent type string.
        goal: The intent goal dict.
        state: Current state snapshot for reading plan memory.
        meta: Score meta record for plan scope, or None to use
            default penalty weight.

    Returns:
        The selected plan_id, or None if no candidates.
    """
    if not plan_ids:
        return None

    best_id: str | None = None
    best_score: float = float("-inf")

    for pid in sorted(plan_ids):
        memory = lookup_plan_memory(state, intent_type, goal, pid)
        s = score_plan(memory, meta)
        # Strict greater-than: ties resolved by sort order (lexicographic)
        if s > best_score:
            best_score = s
            best_id = pid
        elif s == best_score and (best_id is None or pid < best_id):
            best_id = pid

    return best_id
