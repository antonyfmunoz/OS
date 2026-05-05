"""
umh.substrate.live_turn — Transport-agnostic conversational turn model
within a live session.

Pure bookkeeping for individual turns — no Discord, Meet, STT, TTS, or UI.
All state transitions expressed as SET/REMOVE mutations for replay safety.

Public API:
    LiveTurn                    — frozen turn record
    compute_live_turn_id        — deterministic turn ID
    build_live_turn             — construct a new turn
    load_live_turn              — reconstruct from state
    list_session_turns          — enumerate turn IDs for a session (bounded)
    update_partial_input        — update streaming input text
    update_partial_output       — update streaming output text
    finalize_turn               — transition to finalized
    interrupt_turn              — transition to interrupted
    attach_execution_ids        — attach execution references
    build_live_turn_mutations   — persistence mutations for new turn

Separation note:
    This module is harness-only. No Discord, Meet, STT, TTS, or UI code.
    It models a single conversational turn (input → processing → output)
    within a live session, supporting partial/streaming updates.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.live_turn]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_TURN_KEY_PREFIX = "live_turn."
_SESSION_TURN_INDEX_PREFIX = "live_turn_index.session."


def _turn_key(turn_id: str) -> str:
    return f"{_TURN_KEY_PREFIX}{turn_id}"


def _session_turn_key(session_id: str, turn_id: str) -> str:
    return f"{_SESSION_TURN_INDEX_PREFIX}{session_id}.{turn_id}"


# ---------------------------------------------------------------------------
# LiveTurn — frozen turn record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LiveTurn:
    """Immutable record of one conversational turn within a live session.

    Fields:
        turn_id:             deterministic turn identifier
        session_id:          owning live session
        transport:           source transport
        operator_id:         who initiated the turn
        created_at:          ISO timestamp of creation
        finalized_at:        ISO timestamp when turn completed
        status:              open | interrupted | finalized
        input_text:          final/full input text
        partial_input_text:  latest partial streaming input
        output_text:         final/full output text
        partial_output_text: latest partial streaming output
        artifact_id:         associated artifact (if any)
        execution_ids:       execution references from this turn
        interruption_count:  times this turn was interrupted
        correlation_id:      links turn to upstream event chain
    """

    turn_id: str
    session_id: str
    transport: str
    operator_id: str
    created_at: str
    finalized_at: str = ""
    status: str = "open"
    input_text: str = ""
    partial_input_text: str = ""
    output_text: str = ""
    partial_output_text: str = ""
    artifact_id: str = ""
    execution_ids: tuple[str, ...] = ()
    interruption_count: int = 0
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "artifact_id": self.artifact_id,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "execution_ids": list(self.execution_ids),
            "finalized_at": self.finalized_at,
            "input_text": self.input_text,
            "interruption_count": self.interruption_count,
            "operator_id": self.operator_id,
            "output_text": self.output_text,
            "partial_input_text": self.partial_input_text,
            "partial_output_text": self.partial_output_text,
            "session_id": self.session_id,
            "status": self.status,
            "transport": self.transport,
            "turn_id": self.turn_id,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> LiveTurn:
        """Reconstruct from plain dict with backward-safe defaults."""
        return LiveTurn(
            turn_id=str(d.get("turn_id", "")),
            session_id=str(d.get("session_id", "")),
            transport=str(d.get("transport", "")),
            operator_id=str(d.get("operator_id", "")),
            created_at=str(d.get("created_at", "")),
            finalized_at=str(d.get("finalized_at", "")),
            status=str(d.get("status", "open")),
            input_text=str(d.get("input_text", "")),
            partial_input_text=str(d.get("partial_input_text", "")),
            output_text=str(d.get("output_text", "")),
            partial_output_text=str(d.get("partial_output_text", "")),
            artifact_id=str(d.get("artifact_id", "")),
            execution_ids=tuple(d.get("execution_ids", ())),
            interruption_count=int(d.get("interruption_count", 0)),
            correlation_id=str(d.get("correlation_id", "")),
        )

    def _replace(self, **overrides: Any) -> LiveTurn:
        """Return a copy with field overrides."""
        d = self.to_dict()
        d.update(overrides)
        return LiveTurn.from_dict(d)


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_live_turn_id(
    session_id: str,
    turn_index: int,
    input_text: str,
) -> str:
    """Deterministic turn ID: same session + index + input → same ID.

    Uses SHA-256 of canonical JSON. Prefix: ``ltu_``.
    """
    canonical = json.dumps(
        {
            "input_text": input_text,
            "session_id": session_id,
            "turn_index": turn_index,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"ltu_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_live_turn(
    *,
    session_id: str,
    transport: str,
    operator_id: str,
    input_text: str,
    turn_index: int,
    created_at: str = "",
    correlation_id: str = "",
    turn_id: str | None = None,
) -> LiveTurn:
    """Construct a new LiveTurn with deterministic ID."""
    ts = created_at or _utcnow()
    tid = turn_id or compute_live_turn_id(session_id, turn_index, input_text)
    return LiveTurn(
        turn_id=tid,
        session_id=session_id,
        transport=transport,
        operator_id=operator_id,
        created_at=ts,
        input_text=input_text,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Load / list helpers
# ---------------------------------------------------------------------------


def load_live_turn(
    state: dict[str, Any],
    turn_id: str,
) -> LiveTurn | None:
    """Reconstruct a LiveTurn from state, or None if missing."""
    raw = state.get(_turn_key(turn_id))
    if not isinstance(raw, dict):
        return None
    return LiveTurn.from_dict(raw)


def list_session_turns(
    state: dict[str, Any],
    session_id: str,
    limit: int = 50,
) -> tuple[str, ...]:
    """Return turn IDs for a session, ordered by created_at ascending.

    Bounded by limit. Uses prefix scan on session turn index.
    """
    prefix = f"{_SESSION_TURN_INDEX_PREFIX}{session_id}."
    entries: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(prefix):
            continue
        if not isinstance(v, dict):
            continue
        tid = k[len(prefix) :]
        created = str(v.get("created_at", ""))
        entries.append((created, tid))
    entries.sort()
    return tuple(tid for _, tid in entries[:limit])


# ---------------------------------------------------------------------------
# Mutation builders — SET / REMOVE only
# ---------------------------------------------------------------------------


def build_live_turn_mutations(
    turn: LiveTurn,
    turn_index: int,
) -> list[dict[str, Any]]:
    """Build mutations to persist a new live turn.

    Writes:
        1. Turn record:     live_turn.{turn_id}
        2. Session index:   live_turn_index.session.{session_id}.{turn_id}
    """
    return [
        {
            "op": "SET",
            "key": _turn_key(turn.turn_id),
            "value": turn.to_dict(),
        },
        {
            "op": "SET",
            "key": _session_turn_key(turn.session_id, turn.turn_id),
            "value": {
                "created_at": turn.created_at,
                "turn_index": turn_index,
                "status": turn.status,
            },
        },
    ]


# ---------------------------------------------------------------------------
# State transitions — return updated turn (immutable)
# ---------------------------------------------------------------------------


def update_partial_input(
    turn: LiveTurn,
    partial_text: str,
) -> LiveTurn:
    """Update partial streaming input text. Returns new turn."""
    return turn._replace(partial_input_text=partial_text)


def update_partial_output(
    turn: LiveTurn,
    partial_text: str,
) -> LiveTurn:
    """Update partial streaming output text. Returns new turn."""
    return turn._replace(partial_output_text=partial_text)


def finalize_turn(
    turn: LiveTurn,
    output_text: str,
    finalized_at: str,
    artifact_id: str = "",
) -> LiveTurn:
    """Transition turn to finalized with output. Returns new turn."""
    return turn._replace(
        status="finalized",
        output_text=output_text,
        finalized_at=finalized_at,
        artifact_id=artifact_id,
        partial_input_text="",
        partial_output_text="",
    )


def interrupt_turn(
    turn: LiveTurn,
    at: str,
) -> LiveTurn:
    """Transition turn to interrupted. Returns new turn."""
    return turn._replace(
        status="interrupted",
        finalized_at=at,
        interruption_count=turn.interruption_count + 1,
    )


def attach_execution_ids(
    turn: LiveTurn,
    execution_ids: tuple[str, ...],
) -> LiveTurn:
    """Attach execution references to a turn. Returns new turn."""
    merged = turn.execution_ids + execution_ids
    return turn._replace(execution_ids=list(merged))
