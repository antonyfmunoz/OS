"""
umh.substrate.ritual_execution_driver — Step-walker for OpenDayPlan
and CloseDayPlan execution.

Pure functions only. No adapter imports, no Discord/Notion/voice code.
All side effects expressed as mutations or events. Replay-safe and
deterministic given fixed timestamps.

This module turns symbolic day-ritual plans into:
    1. State mutations (presence, mode, profile binding, artifacts)
    2. Scheduler events (step events, started/completed events)
    3. A frozen RitualExecutionResult summarizing what happened

Adapters consume the mutations and events — they are never called here.

Public API:
    RitualExecutionResult            — frozen execution summary
    execute_open_day                 — walk OpenDayPlan steps
    execute_close_day                — walk CloseDayPlan steps
    build_open_day_started_event     — event builder
    build_close_day_started_event    — event builder
    build_ritual_step_event          — per-step event builder
    build_ritual_completed_event     — completion event builder
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from umh.substrate.daily_rituals import (
    CloseDayPlan,
    CloseDayRequest,
    OpenDayPlan,
    OpenDayRequest,
    build_close_day_plan,
    build_open_day_plan,
)
from umh.substrate.event_scheduler import SchedulerEvent
from umh.substrate.handoff_artifact import (
    build_close_day_handoff_artifact,
    build_open_day_handoff_artifact,
    handoff_artifact_to_mutations,
)
from umh.substrate.presence_state import (
    PRESENCE_ACTIVE_STATION,
    PRESENCE_OFF,
    PRESENCE_OVERNIGHT_AUTONOMOUS,
    PRESENCE_REMOTE_LIGHT,
    build_presence_state_mutations,
    set_presence,
)
from umh.substrate.profile_resolution import (
    build_active_profile_mutations,
    resolve_active_profile,
)

_LOG_PREFIX = "[substrate.ritual_execution_driver]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_RUNTIME_MODE_KEY_PREFIX = "runtime_mode."
_RITUAL_EXECUTION_KEY_PREFIX = "ritual_execution."


def _runtime_mode_key(runtime_session_id: str) -> str:
    return f"{_RUNTIME_MODE_KEY_PREFIX}{runtime_session_id}"


def _ritual_execution_key(plan_id: str) -> str:
    return f"{_RITUAL_EXECUTION_KEY_PREFIX}{plan_id}"


# ---------------------------------------------------------------------------
# RitualExecutionResult — frozen execution summary
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RitualExecutionResult:
    """Immutable summary of a ritual execution (open or close day).

    Fields:
        runtime_session_id: owning session
        plan_id:            plan that was executed
        steps_executed:     ordered tuple of step identifiers walked
        presence_after:     presence state after execution
        mode_after:         runtime mode after execution
        profile_id:         resolved profile used (empty if none)
        artifact_id:        handoff artifact created
        correlation_id:     links to upstream event chain
    """

    runtime_session_id: str
    plan_id: str
    steps_executed: tuple[str, ...]
    presence_after: str
    mode_after: str
    profile_id: str
    artifact_id: str
    correlation_id: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "artifact_id": self.artifact_id,
            "correlation_id": self.correlation_id,
            "mode_after": self.mode_after,
            "plan_id": self.plan_id,
            "presence_after": self.presence_after,
            "profile_id": self.profile_id,
            "runtime_session_id": self.runtime_session_id,
            "steps_executed": list(self.steps_executed),
        }


# ---------------------------------------------------------------------------
# Event builders
# ---------------------------------------------------------------------------

_EVENT_SOURCE = "ritual_execution_driver"


def build_open_day_started_event(
    plan: OpenDayPlan,
    session_name: str,
    correlation_id: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build event: open day ritual started."""
    return SchedulerEvent(
        event_type="open_day_started",
        session_name=session_name,
        source=_EVENT_SOURCE,
        run_id=run_id,
        payload={"plan": plan.to_dict()},
        metadata={
            "plan_id": plan.plan_id,
            "profile_id": plan.profile_id,
            "correlation_id": correlation_id,
        },
    )


def build_close_day_started_event(
    plan: CloseDayPlan,
    session_name: str,
    correlation_id: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build event: close day ritual started."""
    return SchedulerEvent(
        event_type="close_day_started",
        session_name=session_name,
        source=_EVENT_SOURCE,
        run_id=run_id,
        payload={"plan": plan.to_dict()},
        metadata={
            "plan_id": plan.plan_id,
            "overnight_enabled": plan.overnight_enabled,
            "correlation_id": correlation_id,
        },
    )


def build_ritual_step_event(
    plan_id: str,
    step_name: str,
    step_index: int,
    session_name: str,
    ritual_kind: str,
    correlation_id: str = "",
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build event: individual ritual step executed."""
    return SchedulerEvent(
        event_type="ritual_step_executed",
        session_name=session_name,
        source=_EVENT_SOURCE,
        run_id=run_id,
        payload={
            "plan_id": plan_id,
            "step_name": step_name,
            "step_index": step_index,
            "ritual_kind": ritual_kind,
        },
        metadata={
            "correlation_id": correlation_id,
        },
    )


def build_ritual_completed_event(
    result: RitualExecutionResult,
    session_name: str,
    ritual_kind: str,
    run_id: str | None = None,
) -> SchedulerEvent:
    """Build event: ritual execution completed."""
    return SchedulerEvent(
        event_type="ritual_completed",
        session_name=session_name,
        source=_EVENT_SOURCE,
        run_id=run_id,
        payload={"result": result.to_dict()},
        metadata={
            "plan_id": result.plan_id,
            "ritual_kind": ritual_kind,
            "correlation_id": result.correlation_id,
        },
    )


# ---------------------------------------------------------------------------
# Mode mutation helper
# ---------------------------------------------------------------------------


def _build_mode_mutation(
    runtime_session_id: str,
    mode: str,
    set_at: str,
) -> dict[str, Any]:
    """Build a SET mutation for runtime mode."""
    return {
        "op": "SET",
        "key": _runtime_mode_key(runtime_session_id),
        "value": {
            "mode": mode,
            "runtime_session_id": runtime_session_id,
            "set_at": set_at,
        },
    }


def _build_execution_record_mutation(
    plan_id: str,
    result: RitualExecutionResult,
    completed_at: str,
) -> dict[str, Any]:
    """Build a SET mutation recording execution completion."""
    return {
        "op": "SET",
        "key": _ritual_execution_key(plan_id),
        "value": {
            **result.to_dict(),
            "completed_at": completed_at,
        },
    }


# ---------------------------------------------------------------------------
# Presence resolution helpers
# ---------------------------------------------------------------------------


def _resolve_open_presence(
    entry_transport: str,
    plan_presence: str,
) -> str:
    """Resolve presence for open-day based on transport and plan.

    If the plan specifies presence, use it. Otherwise infer from transport.
    """
    if plan_presence:
        return plan_presence
    # Infer: discord/ssh/remote → remote_light, otherwise → active_station
    remote_transports = frozenset({"discord", "ssh", "mobile", "remote", "termius"})
    transport_lower = entry_transport.lower()
    for rt in remote_transports:
        if rt in transport_lower:
            return PRESENCE_REMOTE_LIGHT
    return PRESENCE_ACTIVE_STATION


def _resolve_close_presence(
    overnight_enabled: bool,
) -> str:
    """Resolve presence for close-day."""
    if overnight_enabled:
        return PRESENCE_OVERNIGHT_AUTONOMOUS
    return PRESENCE_OFF


# ---------------------------------------------------------------------------
# Open day execution
# ---------------------------------------------------------------------------


def execute_open_day(
    state: dict[str, Any],
    request: OpenDayRequest,
    timestamp: str = "",
) -> tuple[list[dict[str, Any]], list[SchedulerEvent], RitualExecutionResult]:
    """Execute an open-day ritual: walk plan steps, emit mutations + events.

    Returns:
        (mutations, events, result)

    All side effects are expressed as mutations or events — the caller
    applies them. This function reads state but never writes to it.
    """
    ts = timestamp or _utcnow()
    session_id = request.runtime_session_id
    correlation_id = request.correlation_id

    mutations: list[dict[str, Any]] = []
    events: list[SchedulerEvent] = []

    # Step 1: resolve profile
    profile, active_binding = resolve_active_profile(
        state,
        session_id,
        requested_profile_id=request.requested_profile_id,
        resolved_at=ts,
    )
    profile_id = ""
    default_mode = ""
    if profile is not None and active_binding is not None:
        profile_id = profile.profile_id
        default_mode = profile.default_mode
        mutations.extend(build_active_profile_mutations(active_binding))

    # Step 2: build plan
    plan = build_open_day_plan(state, request, profile)

    # Step 3: emit started event
    events.append(
        build_open_day_started_event(plan, session_id, correlation_id=correlation_id)
    )

    # Step 4: walk each step, emit step events
    for idx, step_name in enumerate(plan.steps):
        events.append(
            build_ritual_step_event(
                plan_id=plan.plan_id,
                step_name=step_name,
                step_index=idx,
                session_name=session_id,
                ritual_kind="open_day",
                correlation_id=correlation_id,
            )
        )

    # Step 5: set presence
    resolved_presence = _resolve_open_presence(request.entry_transport, plan.presence)
    resolved_mode = plan.mode or default_mode

    ps, ps_mutations = set_presence(
        state,
        runtime_session_id=session_id,
        presence=resolved_presence,
        mode=resolved_mode,
        transport=request.entry_transport,
        reason="open_day",
        correlation_id=correlation_id,
        set_at=ts,
    )
    mutations.extend(ps_mutations)

    # Step 6: set runtime mode
    if resolved_mode:
        mutations.append(_build_mode_mutation(session_id, resolved_mode, ts))

    # Step 7: build handoff artifact
    artifact = build_open_day_handoff_artifact(
        state,
        session_id,
        created_at=ts,
        correlation_id=correlation_id,
    )
    mutations.extend(handoff_artifact_to_mutations(artifact))

    # Step 8: build result
    result = RitualExecutionResult(
        runtime_session_id=session_id,
        plan_id=plan.plan_id,
        steps_executed=plan.steps,
        presence_after=resolved_presence,
        mode_after=resolved_mode,
        profile_id=profile_id,
        artifact_id=artifact.artifact_id,
        correlation_id=correlation_id,
    )

    # Step 9: record execution + emit completed event
    mutations.append(_build_execution_record_mutation(plan.plan_id, result, ts))
    events.append(
        build_ritual_completed_event(result, session_id, ritual_kind="open_day")
    )

    return mutations, events, result


# ---------------------------------------------------------------------------
# Resume day execution (lightweight open — reuses previous session context)
# ---------------------------------------------------------------------------


def execute_resume_day(
    state: dict[str, Any],
    request: OpenDayRequest,
    previous_session: dict[str, Any],
    timestamp: str = "",
) -> tuple[list[dict[str, Any]], list[SchedulerEvent], RitualExecutionResult]:
    """Execute a resume-day ritual — lighter than open_day.

    Skips full profile resolution and plan building. Carries forward
    mode and presence from the previous session. Emits session_resumed
    instead of open_day_started.

    Returns:
        (mutations, events, result)
    """
    ts = timestamp or _utcnow()
    session_id = request.runtime_session_id
    correlation_id = request.correlation_id

    mutations: list[dict[str, Any]] = []
    events: list[SchedulerEvent] = []

    prev_mode = previous_session.get("mode", "")
    prev_duration = previous_session.get("duration_s", 0.0)
    prev_session_id = previous_session.get("session_id", "")

    plan_id = f"resume_{hashlib.sha256(f'{session_id}:{ts}'.encode()).hexdigest()[:12]}"

    resolved_presence = _resolve_open_presence(request.entry_transport, "")
    resolved_mode = prev_mode or "builder"

    # Step 1: set presence (reuse existing helper)
    ps, ps_mutations = set_presence(
        state,
        runtime_session_id=session_id,
        presence=resolved_presence,
        mode=resolved_mode,
        transport=request.entry_transport,
        reason="resume_day",
        correlation_id=correlation_id,
        set_at=ts,
    )
    mutations.extend(ps_mutations)

    # Step 2: set runtime mode
    if resolved_mode:
        mutations.append(_build_mode_mutation(session_id, resolved_mode, ts))

    # Step 3: emit session_resumed event
    events.append(
        SchedulerEvent(
            event_type="session_resumed",
            session_name=session_id,
            source=_EVENT_SOURCE,
            payload={
                "previous_session_id": prev_session_id,
                "previous_duration_s": prev_duration,
                "resumed_mode": resolved_mode,
            },
            metadata={
                "plan_id": plan_id,
                "correlation_id": correlation_id,
            },
        )
    )

    # Step 4: build result
    result = RitualExecutionResult(
        runtime_session_id=session_id,
        plan_id=plan_id,
        steps_executed=("restore_presence", "restore_mode", "session_resumed"),
        presence_after=resolved_presence,
        mode_after=resolved_mode,
        profile_id="",
        artifact_id="",
        correlation_id=correlation_id,
    )

    # Step 5: record execution + emit completed event
    mutations.append(_build_execution_record_mutation(plan_id, result, ts))
    events.append(
        build_ritual_completed_event(result, session_id, ritual_kind="resume_day")
    )

    return mutations, events, result


# ---------------------------------------------------------------------------
# Close day execution
# ---------------------------------------------------------------------------


def execute_close_day(
    state: dict[str, Any],
    request: CloseDayRequest,
    timestamp: str = "",
) -> tuple[list[dict[str, Any]], list[SchedulerEvent], RitualExecutionResult]:
    """Execute a close-day ritual: walk plan steps, emit mutations + events.

    Returns:
        (mutations, events, result)

    All side effects are expressed as mutations or events — the caller
    applies them. This function reads state but never writes to it.
    """
    ts = timestamp or _utcnow()
    session_id = request.runtime_session_id
    correlation_id = request.correlation_id

    mutations: list[dict[str, Any]] = []
    events: list[SchedulerEvent] = []

    # Step 1: build plan
    plan = build_close_day_plan(state, request)

    # Step 2: emit started event
    events.append(
        build_close_day_started_event(plan, session_id, correlation_id=correlation_id)
    )

    # Step 3: walk each step, emit step events
    for idx, step_name in enumerate(plan.steps):
        events.append(
            build_ritual_step_event(
                plan_id=plan.plan_id,
                step_name=step_name,
                step_index=idx,
                session_name=session_id,
                ritual_kind="close_day",
                correlation_id=correlation_id,
            )
        )

    # Step 4: build handoff artifact
    artifact = build_close_day_handoff_artifact(
        state,
        session_id,
        created_at=ts,
        correlation_id=correlation_id,
    )
    mutations.extend(handoff_artifact_to_mutations(artifact))

    # Step 5: set presence
    resolved_presence = _resolve_close_presence(plan.overnight_enabled)
    resolved_mode = plan.mode_after_close or "passive"

    ps, ps_mutations = set_presence(
        state,
        runtime_session_id=session_id,
        presence=resolved_presence,
        mode=resolved_mode,
        transport="",
        reason="close_day",
        correlation_id=correlation_id,
        set_at=ts,
    )
    mutations.extend(ps_mutations)

    # Step 6: set runtime mode
    mutations.append(_build_mode_mutation(session_id, resolved_mode, ts))

    # Step 7: build result
    result = RitualExecutionResult(
        runtime_session_id=session_id,
        plan_id=plan.plan_id,
        steps_executed=plan.steps,
        presence_after=resolved_presence,
        mode_after=resolved_mode,
        profile_id="",
        artifact_id=artifact.artifact_id,
        correlation_id=correlation_id,
    )

    # Step 8: record execution + emit completed event
    mutations.append(_build_execution_record_mutation(plan.plan_id, result, ts))
    events.append(
        build_ritual_completed_event(result, session_id, ritual_kind="close_day")
    )

    return mutations, events, result
