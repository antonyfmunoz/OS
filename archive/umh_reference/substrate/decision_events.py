"""
Event construction helpers for the decision engine.

Centralises DECISION_MADE event construction to prevent payload-schema
drift.  Every decision emits exactly one DECISION_MADE event containing
the input state hash, chosen action, reasoning, and a decision_id for
tracing.

Also provides decision_blocked_by_memory for the intent memory guard,
intent_competition_resolved for the competitive selection layer, and
decision_meta_adjusted for self-tuning scoring parameter changes.

Usage:
    from umh.substrate.decision_events import (
        build_decision_made_event,
        build_decision_blocked_by_memory_event,
        build_intent_competition_event,
        build_meta_adjusted_event,
    )
"""

from __future__ import annotations

import hashlib

from umh.substrate.event_scheduler import SchedulerEvent


def build_decision_made_event(
    decision_id: str,
    session_name: str,
    strategy_name: str,
    state_hash: str,
    chosen_event_type: str,
    chosen_payload: dict,
    reasoning: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build a DECISION_MADE observability event.

    This event is purely diagnostic — it records what the decision
    engine chose and why.  Handlers may subscribe to it for logging
    or auditing, but it must never trigger further state mutations
    in the lifecycle chain.
    """
    return SchedulerEvent(
        event_type="decision_made",
        session_name=session_name,
        source=f"decision_engine:{strategy_name}",
        run_id=run_id,
        payload={
            "decision_id": decision_id,
            "state_hash": state_hash,
            "chosen_event_type": chosen_event_type,
            "chosen_payload": chosen_payload,
            "reasoning": reasoning,
        },
        metadata={
            "decision_id": decision_id,
            "strategy": strategy_name,
            "state_hash": state_hash,
        },
    )


def build_decision_blocked_by_memory_event(
    intent_type: str,
    goal: dict,
    success_count: int,
    failure_count: int,
    reason: str,
    session_name: str,
    decision_id: str = "",
    run_id: str | None = None,
    failure_by_type: dict | None = None,
    decayed: bool = False,
    last_updated_at: str = "",
) -> SchedulerEvent:
    """Build a decision_blocked_by_memory observability event.

    Emitted when the intent memory guard blocks a decision from
    proposing an intent that has repeatedly failed.  Non-mutating —
    no state changes, purely diagnostic.

    Enhanced payload includes failure classification, decay status,
    and last update timestamp for full observability.
    """
    return SchedulerEvent(
        event_type="decision_blocked_by_memory",
        session_name=session_name,
        source="decision_engine:memory_guard",
        run_id=run_id,
        payload={
            "intent_type": intent_type,
            "goal": goal,
            "success_count": success_count,
            "failure_count": failure_count,
            "failure_by_type": failure_by_type or {},
            "decayed": decayed,
            "last_updated_at": last_updated_at,
            "reason": reason,
        },
        metadata={
            "decision_id": decision_id,
            "intent_type": intent_type,
            "reason": reason,
        },
    )


def build_intent_competition_event(
    winner_decision_id: str,
    winner_event_type: str,
    winner_score: float,
    candidate_count: int,
    candidate_scores: list[dict],
    session_name: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build an intent_competition_resolved observability event.

    Emitted when multiple candidate intents were scored and a winner
    was selected via competitive evaluation.  Non-mutating — purely
    diagnostic for tracing and auditing selection decisions.

    Args:
        candidate_scores: List of dicts with keys: decision_id,
            event_type, intent_type, score, blocked.
    """
    return SchedulerEvent(
        event_type="intent_competition_resolved",
        session_name=session_name,
        source="decision_engine:intent_competition",
        run_id=run_id,
        payload={
            "winner_decision_id": winner_decision_id,
            "winner_event_type": winner_event_type,
            "winner_score": winner_score,
            "candidate_count": candidate_count,
            "candidate_scores": candidate_scores,
        },
        metadata={
            "decision_id": winner_decision_id,
            "candidate_count": candidate_count,
        },
    )


def build_meta_saturation_event(
    scope: str,
    current_weight: float,
    saturation_count: int,
    success_rate: float,
    failure_rate: float,
    execution_count: int,
    session_name: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build a meta_saturation_detected observability event.

    Emitted when a score meta parameter has been at a clamp boundary
    for >= SATURATION_WARN_THRESHOLD consecutive eligible adjustments.
    Signals that the system is pushing against its configured limits.
    Non-mutating — purely diagnostic.
    """
    return SchedulerEvent(
        event_type="meta_saturation_detected",
        session_name=session_name,
        source=f"score_meta:{scope}",
        run_id=run_id,
        payload={
            "scope": scope,
            "current_weight": current_weight,
            "saturation_count": saturation_count,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "execution_count": execution_count,
            "boundary": "upper" if current_weight >= 0.3 else "lower",
        },
        metadata={
            "scope": scope,
            "saturation_count": saturation_count,
        },
    )


def _compute_meta_event_id(
    scope: str,
    old_weight: float,
    new_weight: float,
    execution_count: int,
) -> str:
    """Deterministic dedup hint for meta adjustment events.

    Downstream consumers can use this to recognize replayed events
    without maintaining their own dedup state.
    """
    raw = f"{scope}:{old_weight}:{new_weight}:{execution_count}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_meta_adjusted_event(
    scope: str,
    old_weight: float,
    new_weight: float,
    success_rate: float,
    failure_rate: float,
    execution_count: int,
    delta_applied: float,
    adjustment_count: int = 0,
    cumulative_delta: float = 0.0,
    failure_count: int = 0,
    session_name: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build a decision_meta_adjusted observability event.

    Emitted when self-tuning scoring adjusts a failure penalty weight.
    Non-mutating — purely diagnostic for tracing parameter evolution.

    Derived fields (not stored, computed inline):
    - confidence: min(1.0, execution_count / 20) — signal reliability
    - effective_penalty: failure_count * new_weight — actual scoring impact
    - event_id: deterministic hash for downstream deduplication
    """
    return SchedulerEvent(
        event_type="decision_meta_adjusted",
        session_name=session_name,
        source=f"score_meta:{scope}",
        run_id=run_id,
        payload={
            "scope": scope,
            "old_weight": old_weight,
            "new_weight": new_weight,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "execution_count": execution_count,
            "delta_applied": delta_applied,
            "adjustment_count": adjustment_count,
            "cumulative_delta": cumulative_delta,
            "confidence": min(1.0, execution_count / 20)
            if execution_count > 0
            else 0.0,
            "effective_penalty": failure_count * new_weight,
            "event_id": _compute_meta_event_id(
                scope, old_weight, new_weight, execution_count
            ),
        },
        metadata={
            "scope": scope,
            "event_id": _compute_meta_event_id(
                scope, old_weight, new_weight, execution_count
            ),
        },
    )
