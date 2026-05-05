"""
Event construction helpers for the LLM planning layer.

Centralises observability event construction for:
    - LLM_DECISION_REQUESTED
    - LLM_DECISION_RECEIVED
    - LLM_DECISION_ACCEPTED
    - LLM_DECISION_REJECTED
    - LLM_DECISION_SKIPPED
    - LLM_RESPONSE_DRIFT

All events are non-mutating (is_mutation=False in EventSchema).
Runtime must enforce that handlers for these events cannot return
mutations.  These are diagnostic events for tracing and auditing.

Usage:
    from umh.substrate.llm_decision_events import (
        build_llm_decision_requested_event,
        build_llm_decision_received_event,
        build_llm_decision_accepted_event,
        build_llm_decision_rejected_event,
        build_llm_decision_skipped_event,
        build_llm_response_drift_event,
    )
"""

from __future__ import annotations

from umh.substrate.event_scheduler import SchedulerEvent


def build_llm_decision_requested_event(
    state_hash: str,
    prompt_hash: str,
    active_intent_ids: list[str],
    session_name: str,
    decision_phase: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Emitted when the LLM is about to be called."""
    return SchedulerEvent(
        event_type="llm_decision_requested",
        session_name=session_name,
        source="llm_planner",
        run_id=run_id,
        payload={
            "state_hash": state_hash,
            "prompt_hash": prompt_hash,
            "active_intent_ids": active_intent_ids,
            "decision_phase": decision_phase,
        },
        metadata={
            "prompt_hash": prompt_hash,
            "state_hash": state_hash,
            "decision_phase": decision_phase,
        },
    )


def build_llm_decision_received_event(
    proposal_id: str,
    prompt_hash: str,
    response_hash: str,
    event_count: int,
    latency_ms: int,
    session_name: str,
    decision_phase: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Emitted when LLM response arrives and is parsed."""
    return SchedulerEvent(
        event_type="llm_decision_received",
        session_name=session_name,
        source="llm_planner",
        run_id=run_id,
        payload={
            "proposal_id": proposal_id,
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "event_count": event_count,
            "latency_ms": latency_ms,
            "decision_phase": decision_phase,
        },
        metadata={
            "proposal_id": proposal_id,
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "decision_phase": decision_phase,
        },
    )


def build_llm_decision_accepted_event(
    proposal_id: str,
    emitted_event_count: int,
    selection_policy: str,
    session_name: str,
    decision_phase: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Emitted when a proposal is validated and its events emitted."""
    return SchedulerEvent(
        event_type="llm_decision_accepted",
        session_name=session_name,
        source="llm_planner",
        run_id=run_id,
        payload={
            "proposal_id": proposal_id,
            "emitted_event_count": emitted_event_count,
            "selection_policy": selection_policy,
            "decision_phase": decision_phase,
        },
        metadata={
            "proposal_id": proposal_id,
            "decision_phase": decision_phase,
        },
    )


def build_llm_decision_rejected_event(
    proposal_id: str,
    prompt_hash: str,
    rejection_reason: str,
    rejected_event_count: int,
    session_name: str,
    decision_phase: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Emitted when validation rejects the proposal (partial or full)."""
    return SchedulerEvent(
        event_type="llm_decision_rejected",
        session_name=session_name,
        source="llm_planner",
        run_id=run_id,
        payload={
            "proposal_id": proposal_id,
            "prompt_hash": prompt_hash,
            "rejection_reason": rejection_reason,
            "rejected_event_count": rejected_event_count,
            "decision_phase": decision_phase,
        },
        metadata={
            "proposal_id": proposal_id,
            "prompt_hash": prompt_hash,
            "decision_phase": decision_phase,
        },
    )


def build_llm_decision_skipped_event(
    reason: str,
    state_hash: str,
    session_name: str,
    decision_phase: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Emitted when the LLM layer is bypassed for any reason."""
    return SchedulerEvent(
        event_type="llm_decision_skipped",
        session_name=session_name,
        source="llm_planner",
        run_id=run_id,
        payload={
            "reason": reason,
            "state_hash": state_hash,
            "decision_phase": decision_phase,
        },
        metadata={
            "state_hash": state_hash,
            "decision_phase": decision_phase,
        },
    )


def build_llm_response_drift_event(
    prompt_hash: str,
    response_hash_a: str,
    response_hash_b: str,
    session_name: str,
    decision_phase: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Emitted when same prompt_hash produces different response_hash.

    Drift detection only applies within identical execution context.
    prompt_hash is a composite of (prompt, model, temperature,
    config_version, registry_version).  Different prompt_hash values
    are NOT drift — they represent different execution contexts.
    """
    return SchedulerEvent(
        event_type="llm_response_drift",
        session_name=session_name,
        source="llm_planner",
        run_id=run_id,
        payload={
            "prompt_hash": prompt_hash,
            "response_hash_a": response_hash_a,
            "response_hash_b": response_hash_b,
            "decision_phase": decision_phase,
        },
        metadata={
            "prompt_hash": prompt_hash,
            "decision_phase": decision_phase,
        },
    )
