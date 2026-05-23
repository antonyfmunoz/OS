"""
Operator transitions — deterministic state transition layer.

This is the brain of the operator state engine. It is intentionally tiny:

  - one pure function `decide_transition(state, trigger)` that returns the
    next mode and a short reason string
  - small `apply_*` helpers that other modules call to push raw signals into
    the state store

Other substrate modules NEVER reason about operator state directly. They
just call `apply_wake_event(event)` / `apply_voice_session(session)` /
`apply_ritual(...)` and let this layer compute the transition.

Why a separate file?
--------------------
operator_state.py owns *shape* and *persistence*. operator_transitions.py
owns *meaning* — when does IDLE become STARTING, when does STARTING become
ACTIVE, when does anything become CLOSING. Splitting them keeps the data
model auditable independently of policy.

Design rules
------------
- Pure function for the actual decision (no I/O, no side effects).
- apply_* wrappers are best-effort — they catch and log, never raise.
- Hot path is never imported.
- No autonomy, no scheduling, no autonomous loops. The transitions just
  *describe* what already happened.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from substrate.execution.bridge.operator_state import (
    OperatorMode,
    OperatorState,
    OperatorTransition,
    get_operator_state_store,
)


def _log(msg: str) -> None:
    print(f"[substrate.operator_transitions] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_transition_id() -> str:
    import uuid

    return f"ot_{uuid.uuid4().hex[:12]}"


# ─── Trigger model ────────────────────────────────────────────────────────────


@dataclass
class TransitionTrigger:
    """Bounded trigger record passed to decide_transition.

    `kind` is a short closed-set tag. `payload` carries the small set of
    fields the decision function needs (action_taken, ritual_state, etc.).
    """

    kind: str  # "wake_word"|"clap"|"voice_started"|"voice_turn"|"voice_ended"
    #         | "ritual_open_start"|"ritual_open_finish"
    #         | "ritual_close_start"|"ritual_close_finish"
    #         | "readiness_unavailable"
    payload: dict


@dataclass
class TransitionDecision:
    """Result of decide_transition. Pure data, no side effects."""

    next_mode: OperatorMode
    reason: str
    intended_action: Optional[str] = None  # short tag for reporting


# ─── Pure transition function ─────────────────────────────────────────────────


def decide_transition(
    state: OperatorState, trigger: TransitionTrigger
) -> TransitionDecision:
    """Pure decision: given current state + trigger, what mode comes next?

    This is intentionally a small `if` ladder, NOT a rules engine. Each
    branch is one explicit, explainable transition. Adding behavior means
    adding a branch here, not registering a callback anywhere.
    """
    current = state.mode
    kind = trigger.kind
    payload = trigger.payload or {}

    # — wake word ————————————————————————————————————————————————
    if kind == "wake_word":
        action = payload.get("action_taken")
        if action == "resume_voice_session":
            return TransitionDecision(
                next_mode=OperatorMode.ACTIVE,
                reason="wake word resumed active voice session",
                intended_action="resume_voice_session",
            )
        if action == "start_voice_session":
            return TransitionDecision(
                next_mode=OperatorMode.STARTING,
                reason="wake word started new voice session",
                intended_action="start_voice_session",
            )
        # skipped or unknown — stay put
        return TransitionDecision(
            next_mode=current,
            reason=f"wake word skipped ({payload.get('decision_reason') or 'no action'})",
            intended_action=None,
        )

    # — clap ————————————————————————————————————————————————————
    if kind == "clap":
        action = payload.get("action_taken")
        if action == "open_day":
            return TransitionDecision(
                next_mode=OperatorMode.STARTING,
                reason="clap accepted as open_day activation",
                intended_action="start_open_day",
            )
        return TransitionDecision(
            next_mode=current,
            reason=f"clap skipped ({payload.get('decision_reason') or 'no action'})",
            intended_action=None,
        )

    # — voice session lifecycle ——————————————————————————————————
    if kind == "voice_started":
        return TransitionDecision(
            next_mode=OperatorMode.ACTIVE,
            reason="voice session became active",
            intended_action="enter_active",
        )
    if kind == "voice_turn":
        # First turn coming after STARTING → ACTIVE; otherwise stay
        if current in (OperatorMode.STARTING, OperatorMode.IDLE):
            return TransitionDecision(
                next_mode=OperatorMode.ACTIVE,
                reason="voice turn observed",
                intended_action="enter_active",
            )
        return TransitionDecision(
            next_mode=current,
            reason="voice turn observed (no mode change)",
            intended_action=None,
        )
    if kind == "voice_ended":
        # If we are FOCUSED and voice ends, drop back to IDLE; if a ritual
        # is still in flight the ritual signal will move us elsewhere.
        return TransitionDecision(
            next_mode=OperatorMode.IDLE,
            reason="voice session ended",
            intended_action="enter_idle",
        )

    # — rituals ——————————————————————————————————————————————————
    if kind == "ritual_open_start":
        # An open_day ritual taking us into a focused scene
        return TransitionDecision(
            next_mode=OperatorMode.FOCUSED,
            reason="open_day ritual started — entering focused scene",
            intended_action="enter_focused",
        )
    if kind == "ritual_open_finish":
        # Open ritual completed — drop to ACTIVE if voice still present, else IDLE
        if state.active_voice_session_id:
            return TransitionDecision(
                next_mode=OperatorMode.ACTIVE,
                reason="open_day finished, voice session still active",
                intended_action=None,
            )
        return TransitionDecision(
            next_mode=OperatorMode.IDLE,
            reason="open_day finished, no voice session",
            intended_action=None,
        )
    if kind == "ritual_close_start":
        return TransitionDecision(
            next_mode=OperatorMode.CLOSING,
            reason="close_day ritual started",
            intended_action="enter_closing",
        )
    if kind == "ritual_close_finish":
        return TransitionDecision(
            next_mode=OperatorMode.IDLE,
            reason="close_day finished",
            intended_action="enter_idle",
        )

    # — readiness ————————————————————————————————————————————————
    if kind == "readiness_unavailable":
        return TransitionDecision(
            next_mode=OperatorMode.UNAVAILABLE,
            reason="readiness UNAVAILABLE",
            intended_action=None,
        )

    # default: no change
    return TransitionDecision(
        next_mode=current, reason=f"unknown trigger {kind!r}", intended_action=None
    )


# ─── Wiring helpers (best-effort) ─────────────────────────────────────────────


def _record_transition(
    state: OperatorState,
    decision: TransitionDecision,
    trigger_kind: str,
    metadata: Optional[dict] = None,
) -> None:
    """Append a transition record only if the mode actually changed.

    The state itself may be mutated regardless (caller updates fields like
    active_voice_session_id) — this just decides whether to add to the
    explainability ring buffer.
    """
    from_mode = state.mode
    if decision.next_mode == from_mode:
        return
    transition = OperatorTransition(
        transition_id=_new_transition_id(),
        node_id=state.node_id,
        from_mode=from_mode.value,
        to_mode=decision.next_mode.value,
        trigger=trigger_kind,
        reason=decision.reason,
        occurred_at=_utcnow(),
        metadata=dict(metadata or {}),
    )
    state.append_transition(transition)
    state.mode = decision.next_mode
    # Best-effort: emit the bounded spoken presence line for this
    # transition. Dedupe and dispatch are owned by the helper; failures
    # log and are swallowed so they never break the transition recorder.
    _emit_presence_if_needed(state, transition)


def _emit_presence_if_needed(
    state: OperatorState, transition: OperatorTransition
) -> None:
    """Speak a short operator_presence line for this mode transition.

    Bounded, deterministic, best-effort. Dedupe is delegated to the
    audio_loop cooldown helper so a spammy stream of transitions with
    the same (from_mode, to_mode) does not produce spoken duplicates.
    """
    try:
        from substrate.execution.bridge.operator_presence import intro_for_transition

        line = intro_for_transition(transition)
        if not line:
            return
    except Exception as e:  # noqa: BLE001
        _log(f"presence lookup failed: {e}")
        return

    # Cooldown / dedupe via audio_loop.
    try:
        from substrate.execution.bridge.audio_loop import (
            record_spoken_line,
            should_speak_presence_line,
        )

        if not should_speak_presence_line(
            state.node_id,
            from_mode=transition.from_mode,
            to_mode=transition.to_mode,
        ):
            return
    except Exception as e:  # noqa: BLE001
        _log(f"presence cooldown check failed: {e}")
        record_spoken_line = None  # type: ignore[assignment]

    # Dispatch through the canonical SPEAK_TEXT seam. Hot path is not
    # imported — station_helpers is part of substrate.
    try:
        from substrate.execution.bridge.station_helpers import propose_speak_text

        propose_speak_text(
            state.node_id,
            line,
            issued_by="operator_presence",
        )
    except Exception as e:  # noqa: BLE001
        _log(f"propose_speak_text for presence failed: {e}")
        return

    # Record the spoken line on the audio_loop state for dedupe + report.
    try:
        if record_spoken_line is not None:
            record_spoken_line(
                state.node_id,
                from_mode=transition.from_mode,
                to_mode=transition.to_mode,
                line=line,
            )
    except Exception as e:  # noqa: BLE001
        _log(f"record_spoken_line failed: {e}")


def apply_wake_event(event) -> None:
    """Push a WakeProducerEvent into the operator state. Best-effort."""
    try:
        store = get_operator_state_store()
        state = store.get_or_create(event.node_id)
        # Update raw fields first (always)
        state.last_wake_event_id = event.event_id
        state.last_wake_kind = (
            event.producer_kind.value
            if hasattr(event.producer_kind, "value")
            else str(event.producer_kind)
        )
        state.last_wake_action = event.action_taken
        state.last_wake_at = event.occurred_at
        if event.voice_session_id:
            state.active_voice_session_id = event.voice_session_id
        # Decide transition
        kind = "wake_word" if state.last_wake_kind == "wake_word" else "clap"
        trigger = TransitionTrigger(
            kind=kind,
            payload={
                "action_taken": event.action_taken,
                "decision_reason": event.decision_reason,
            },
        )
        decision = decide_transition(state, trigger)
        _record_transition(
            state,
            decision,
            trigger_kind=kind,
            metadata={
                "wake_event_id": event.event_id,
                "intended_action": decision.intended_action,
            },
        )
        store.put(state)
    except Exception as e:  # noqa: BLE001
        _log(f"apply_wake_event failed: {e}")


def apply_voice_session(session, *, lifecycle: str = "turn") -> None:
    """Push a VoiceSession update into operator state.

    `lifecycle` is one of: "started", "turn", "ended".
    """
    try:
        store = get_operator_state_store()
        state = store.get_or_create(session.node_id)
        # Always update raw fields
        if lifecycle == "ended":
            # Only clear if this was the active one
            if state.active_voice_session_id == session.session_id:
                state.active_voice_session_id = None
                state.active_voice_role = None
        else:
            state.active_voice_session_id = session.session_id
            state.active_voice_role = session.role_slug
            state.last_voice_turn_at = session.last_activity_at

        kind = {
            "started": "voice_started",
            "turn": "voice_turn",
            "ended": "voice_ended",
        }.get(lifecycle, "voice_turn")
        trigger = TransitionTrigger(
            kind=kind,
            payload={
                "session_id": session.session_id,
                "role": session.role_slug,
            },
        )
        decision = decide_transition(state, trigger)
        _record_transition(
            state,
            decision,
            trigger_kind=kind,
            metadata={
                "session_id": session.session_id,
                "role": session.role_slug,
            },
        )
        store.put(state)
    except Exception as e:  # noqa: BLE001
        _log(f"apply_voice_session failed: {e}")


def apply_ritual(
    node_id: Optional[str],
    *,
    ritual_id: str,
    ritual_kind: str,  # "open_day" | "close_day"
    ritual_state: str,  # "started" | "finished" | "failed"
    scene: Optional[str] = None,
    scene_reason: Optional[str] = None,
    readiness_classification: Optional[str] = None,
    readiness_age_s: Optional[float] = None,
) -> None:
    """Push a ritual lifecycle update into operator state. Best-effort.

    `node_id` may be None if the ritual is not bound to a station; in that
    case we no-op (operator state is per-node).
    """
    try:
        if not node_id:
            return
        store = get_operator_state_store()
        state = store.get_or_create(node_id)

        # Always update raw fields
        state.current_ritual_id = ritual_id
        state.current_ritual_kind = ritual_kind
        state.current_ritual_state = ritual_state
        if scene is not None:
            state.current_scene = scene
        if scene_reason is not None:
            state.scene_decision_reason = scene_reason
        if readiness_classification is not None:
            state.readiness_classification = readiness_classification
        if readiness_age_s is not None:
            state.readiness_age_s = readiness_age_s

        # Decide trigger kind
        if ritual_kind == "open_day" and ritual_state == "started":
            kind = "ritual_open_start"
        elif ritual_kind == "open_day" and ritual_state in ("finished", "completed"):
            kind = "ritual_open_finish"
        elif ritual_kind == "close_day" and ritual_state == "started":
            kind = "ritual_close_start"
        elif ritual_kind == "close_day" and ritual_state in ("finished", "completed"):
            kind = "ritual_close_finish"
        else:
            # Just persist field updates without forcing a transition
            store.put(state)
            return

        # If readiness says UNAVAILABLE, override the transition
        if readiness_classification == "UNAVAILABLE":
            trigger = TransitionTrigger(kind="readiness_unavailable", payload={})
        else:
            trigger = TransitionTrigger(
                kind=kind, payload={"ritual_id": ritual_id, "ritual_kind": ritual_kind}
            )
        decision = decide_transition(state, trigger)
        _record_transition(
            state,
            decision,
            trigger_kind=kind,
            metadata={
                "ritual_id": ritual_id,
                "ritual_kind": ritual_kind,
                "ritual_state": ritual_state,
            },
        )
        store.put(state)
    except Exception as e:  # noqa: BLE001
        _log(f"apply_ritual failed: {e}")


__all__ = [
    "TransitionTrigger",
    "TransitionDecision",
    "decide_transition",
    "apply_wake_event",
    "apply_voice_session",
    "apply_ritual",
]
