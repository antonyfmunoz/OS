"""
umh.substrate.live_session_controller — Transport-agnostic controller
for live session and turn state transitions.

Pure state-machine controller — no Discord, Meet, STT, TTS, or UI code.
All methods consume state + params and produce (result, mutations).
Deterministic given identical inputs.

Public API:
    LiveTurnResult              — frozen result of a turn operation
    LiveSessionController       — stateless controller
    build_live_continuity_summary — pure summary helper

Separation note:
    This controller is harness-only. It may NOT call Discord, Meet,
    STT, TTS, or any transport API. It consumes contracts and produces
    state mutations and pure results only.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from umh.substrate.live_session import (
    LiveSession,
    build_live_session,
    build_live_session_mutations,
    compute_live_session_id,
    end_live_session as _end_session,
    interrupt_live_session as _interrupt_session,
    load_live_session,
    touch_live_session as _touch_session,
)
from umh.substrate.live_turn import (
    LiveTurn,
    attach_execution_ids as _attach_execution_ids,
    build_live_turn,
    build_live_turn_mutations,
    finalize_turn as _finalize_turn,
    interrupt_turn as _interrupt_turn,
    load_live_turn,
    update_partial_input as _update_partial_input,
    update_partial_output as _update_partial_output,
)

_LOG_PREFIX = "[substrate.live_session_controller]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# State key helpers (shared with live_session.py / live_turn.py)
# ---------------------------------------------------------------------------
_SESSION_KEY_PREFIX = "live_session."
_ACTIVE_INDEX_PREFIX = "live_session_index.active."
_RECENT_INDEX_PREFIX = "live_session_index.recent."
_TURN_KEY_PREFIX = "live_turn."
_SESSION_TURN_INDEX_PREFIX = "live_turn_index.session."


def _session_key(session_id: str) -> str:
    return f"{_SESSION_KEY_PREFIX}{session_id}"


def _active_key(session_id: str) -> str:
    return f"{_ACTIVE_INDEX_PREFIX}{session_id}"


def _recent_key(session_id: str) -> str:
    return f"{_RECENT_INDEX_PREFIX}{session_id}"


def _turn_key(turn_id: str) -> str:
    return f"{_TURN_KEY_PREFIX}{turn_id}"


def _session_turn_key(session_id: str, turn_id: str) -> str:
    return f"{_SESSION_TURN_INDEX_PREFIX}{session_id}.{turn_id}"


# ---------------------------------------------------------------------------
# LiveTurnResult — frozen result of a turn operation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LiveTurnResult:
    """Immutable result of a live turn state transition.

    Fields:
        session:             updated session state
        turn:                updated turn state (or current turn)
        mutations:           state mutations to apply
        continuity_summary:  human-readable summary for handoff/continuity
        requires_artifact:   whether an artifact should be produced
    """

    session: LiveSession
    turn: LiveTurn
    mutations: tuple[dict[str, Any], ...]
    continuity_summary: str = ""
    requires_artifact: bool = False


# ---------------------------------------------------------------------------
# Pure summary helpers
# ---------------------------------------------------------------------------


def build_live_continuity_summary(
    session: LiveSession,
    turn: LiveTurn | None = None,
) -> str:
    """Build a transport-agnostic continuity summary.

    Describes session state in harness-generic terms.
    No product branding, no transport-specific language.
    """
    parts: list[str] = []

    # Session state
    if session.status == "active":
        parts.append("live session active")
    elif session.status == "interrupted":
        parts.append("live session interrupted")
    elif session.status == "ended":
        parts.append("live session ended")
    else:
        parts.append(f"live session {session.status}")

    # Turn counts
    if session.turn_count > 0:
        completed = session.turn_count
        if session.current_turn_id:
            completed -= 1
        if completed == 1:
            parts.append("1 completed turn")
        elif completed > 1:
            parts.append(f"{completed} completed turns")

    # Interruptions
    if session.interruption_count == 1:
        parts.append("1 interruption")
    elif session.interruption_count > 1:
        parts.append(f"{session.interruption_count} interruptions")

    # Open executions
    if session.open_execution_count > 0:
        parts.append(
            f"{session.open_execution_count} open execution"
            + ("s" if session.open_execution_count > 1 else "")
        )

    # Current turn detail
    if turn is not None and turn.status == "open":
        parts.append("current turn open")

    return (
        " with ".join(parts[:1] + [", ".join(parts[1:])])
        if len(parts) > 1
        else (parts[0] if parts else "")
    )


# ---------------------------------------------------------------------------
# LiveSessionController — stateless, pure controller
# ---------------------------------------------------------------------------
class LiveSessionController:
    """Transport-agnostic controller for live session state transitions.

    All methods are pure: they take state + params, return results + mutations.
    No network I/O, no audio, no provider code, no hidden reads.
    """

    def start_session(
        self,
        state: dict[str, Any],
        runtime_session_id: str,
        mode: str,
        transport: str,
        operator_id: str,
        started_at: str,
        correlation_id: str = "",
    ) -> tuple[LiveSession, tuple[dict[str, Any], ...]]:
        """Start or resume an existing live session.

        If a session with the same deterministic ID already exists and is
        active, returns it with no-op mutations (idempotent).
        Otherwise creates a new session.

        Returns (session, mutations).
        """
        session_id = compute_live_session_id(runtime_session_id, transport, operator_id)
        existing = load_live_session(state, session_id)
        if existing is not None and existing.status == "active":
            return existing, ()

        session = build_live_session(
            runtime_session_id=runtime_session_id,
            mode=mode,
            transport=transport,
            operator_id=operator_id,
            started_at=started_at,
            correlation_id=correlation_id,
            session_id=session_id,
        )
        mutations = build_live_session_mutations(session)
        return session, tuple(mutations)

    def start_turn(
        self,
        state: dict[str, Any],
        session_id: str,
        input_text: str,
        created_at: str,
        correlation_id: str = "",
    ) -> LiveTurnResult:
        """Start a new turn within an active session.

        Increments turn_count, creates a new turn, and sets it as current.

        Returns LiveTurnResult with session, turn, and mutations.
        """
        session = load_live_session(state, session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")

        new_turn_count = session.turn_count + 1
        turn = build_live_turn(
            session_id=session_id,
            transport=session.transport,
            operator_id=session.operator_id,
            input_text=input_text,
            turn_index=new_turn_count,
            created_at=created_at,
            correlation_id=correlation_id,
        )

        updated_session = session._replace(
            turn_count=new_turn_count,
            current_turn_id=turn.turn_id,
            last_active_at=created_at,
            status="active",
        )

        mutations: list[dict[str, Any]] = []

        # Session record update
        mutations.append(
            {
                "op": "SET",
                "key": _session_key(session_id),
                "value": updated_session.to_dict(),
            }
        )
        # Active index update
        mutations.append(
            {
                "op": "SET",
                "key": _active_key(session_id),
                "value": {
                    "operator_id": updated_session.operator_id,
                    "started_at": updated_session.started_at,
                    "transport": updated_session.transport,
                    "mode": updated_session.mode,
                    "last_active_at": created_at,
                    "correlation_id": updated_session.correlation_id,
                },
            }
        )
        # Turn mutations
        mutations.extend(build_live_turn_mutations(turn, new_turn_count))

        return LiveTurnResult(
            session=updated_session,
            turn=turn,
            mutations=tuple(mutations),
        )

    def update_turn_input_partial(
        self,
        state: dict[str, Any],
        session_id: str,
        partial_text: str,
        at: str,
    ) -> LiveTurnResult:
        """Update partial input text on the current open turn.

        Returns LiveTurnResult with updated session, turn, and mutations.
        """
        session = load_live_session(state, session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")
        if not session.current_turn_id:
            raise ValueError(f"session {session_id} has no open turn")

        turn = load_live_turn(state, session.current_turn_id)
        if turn is None:
            raise ValueError(f"turn {session.current_turn_id} not found")

        updated_turn = _update_partial_input(turn, partial_text)
        updated_session, session_mutations = _touch_session(session, at)

        mutations: list[dict[str, Any]] = list(session_mutations)
        mutations.append(
            {
                "op": "SET",
                "key": _turn_key(turn.turn_id),
                "value": updated_turn.to_dict(),
            }
        )

        return LiveTurnResult(
            session=updated_session,
            turn=updated_turn,
            mutations=tuple(mutations),
        )

    def update_turn_output_partial(
        self,
        state: dict[str, Any],
        session_id: str,
        partial_text: str,
        at: str,
    ) -> LiveTurnResult:
        """Update partial output text on the current open turn.

        Returns LiveTurnResult with updated session, turn, and mutations.
        """
        session = load_live_session(state, session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")
        if not session.current_turn_id:
            raise ValueError(f"session {session_id} has no open turn")

        turn = load_live_turn(state, session.current_turn_id)
        if turn is None:
            raise ValueError(f"turn {session.current_turn_id} not found")

        updated_turn = _update_partial_output(turn, partial_text)
        updated_session, session_mutations = _touch_session(session, at)

        mutations: list[dict[str, Any]] = list(session_mutations)
        mutations.append(
            {
                "op": "SET",
                "key": _turn_key(turn.turn_id),
                "value": updated_turn.to_dict(),
            }
        )

        return LiveTurnResult(
            session=updated_session,
            turn=updated_turn,
            mutations=tuple(mutations),
        )

    def finalize_turn(
        self,
        state: dict[str, Any],
        session_id: str,
        output_text: str,
        finalized_at: str,
        artifact_id: str = "",
        execution_ids: tuple[str, ...] = (),
    ) -> LiveTurnResult:
        """Finalize the current open turn with output.

        Clears current_turn_id on session, updates last_active_at,
        produces a continuity summary.

        Returns LiveTurnResult.
        """
        session = load_live_session(state, session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")
        if not session.current_turn_id:
            raise ValueError(f"session {session_id} has no open turn")

        turn = load_live_turn(state, session.current_turn_id)
        if turn is None:
            raise ValueError(f"turn {session.current_turn_id} not found")

        finalized = _finalize_turn(turn, output_text, finalized_at, artifact_id)
        if execution_ids:
            finalized = _attach_execution_ids(finalized, execution_ids)

        updated_session = session._replace(
            current_turn_id="",
            last_active_at=finalized_at,
            last_artifact_id=artifact_id or session.last_artifact_id,
            open_execution_count=session.open_execution_count + len(execution_ids),
        )

        mutations: list[dict[str, Any]] = [
            {
                "op": "SET",
                "key": _session_key(session_id),
                "value": updated_session.to_dict(),
            },
            {
                "op": "SET",
                "key": _active_key(session_id),
                "value": {
                    "operator_id": updated_session.operator_id,
                    "started_at": updated_session.started_at,
                    "transport": updated_session.transport,
                    "mode": updated_session.mode,
                    "last_active_at": finalized_at,
                    "correlation_id": updated_session.correlation_id,
                },
            },
            {
                "op": "SET",
                "key": _turn_key(turn.turn_id),
                "value": finalized.to_dict(),
            },
            {
                "op": "SET",
                "key": _session_turn_key(session_id, turn.turn_id),
                "value": {
                    "created_at": finalized.created_at,
                    "turn_index": session.turn_count,
                    "status": "finalized",
                },
            },
        ]

        summary = build_live_continuity_summary(updated_session, finalized)

        return LiveTurnResult(
            session=updated_session,
            turn=finalized,
            mutations=tuple(mutations),
            continuity_summary=summary,
            requires_artifact=bool(artifact_id),
        )

    def interrupt_current_turn(
        self,
        state: dict[str, Any],
        session_id: str,
        at: str,
    ) -> LiveTurnResult:
        """Interrupt the current open turn.

        Increments interruption counts on both turn and session.
        Session status becomes interrupted if it was active.

        Returns LiveTurnResult.
        """
        session = load_live_session(state, session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")

        if not session.current_turn_id:
            # No open turn — just interrupt the session
            updated_session, session_mutations = _interrupt_session(session, at)
            # Return a sentinel turn
            sentinel_turn = LiveTurn(
                turn_id="",
                session_id=session_id,
                transport=session.transport,
                operator_id=session.operator_id,
                created_at=at,
                status="interrupted",
            )
            return LiveTurnResult(
                session=updated_session,
                turn=sentinel_turn,
                mutations=tuple(session_mutations),
            )

        turn = load_live_turn(state, session.current_turn_id)
        if turn is None:
            raise ValueError(f"turn {session.current_turn_id} not found")

        interrupted_turn = _interrupt_turn(turn, at)
        updated_session, session_mutations = _interrupt_session(session, at)
        # Clear current_turn_id since the turn is now interrupted
        updated_session = updated_session._replace(current_turn_id="")

        mutations: list[dict[str, Any]] = list(session_mutations)
        mutations.extend(
            [
                {
                    "op": "SET",
                    "key": _turn_key(turn.turn_id),
                    "value": interrupted_turn.to_dict(),
                },
                {
                    "op": "SET",
                    "key": _session_turn_key(session_id, turn.turn_id),
                    "value": {
                        "created_at": interrupted_turn.created_at,
                        "turn_index": session.turn_count,
                        "status": "interrupted",
                    },
                },
            ]
        )
        # Update session record to reflect cleared current_turn_id
        mutations.append(
            {
                "op": "SET",
                "key": _session_key(session_id),
                "value": updated_session.to_dict(),
            }
        )

        return LiveTurnResult(
            session=updated_session,
            turn=interrupted_turn,
            mutations=tuple(mutations),
        )

    def resume_session(
        self,
        state: dict[str, Any],
        session_id: str,
        at: str,
    ) -> tuple[LiveSession, tuple[dict[str, Any], ...]]:
        """Resume an interrupted session back to active.

        Does not create a new turn — just restores session state.

        Returns (session, mutations).
        """
        session = load_live_session(state, session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")

        updated = session._replace(
            status="active",
            last_active_at=at,
        )
        mutations: list[dict[str, Any]] = [
            {
                "op": "SET",
                "key": _session_key(session_id),
                "value": updated.to_dict(),
            },
            {
                "op": "SET",
                "key": _active_key(session_id),
                "value": {
                    "operator_id": updated.operator_id,
                    "started_at": updated.started_at,
                    "transport": updated.transport,
                    "mode": updated.mode,
                    "last_active_at": at,
                    "correlation_id": updated.correlation_id,
                },
            },
        ]
        return updated, tuple(mutations)

    def end_session(
        self,
        state: dict[str, Any],
        session_id: str,
        ended_at: str,
    ) -> tuple[LiveSession, tuple[dict[str, Any], ...]]:
        """End a live session.

        Removes active index, preserves recent index.

        Returns (session, mutations).
        """
        session = load_live_session(state, session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")

        updated, mutations = _end_session(session, ended_at)
        return updated, tuple(mutations)
