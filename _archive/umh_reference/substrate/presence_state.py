"""
umh.substrate.presence_state — Human/operator presence state model,
tracked independently from runtime mode.

Represents where the human is in relation to the system: off, remote,
at the station, in deep work, or absent during overnight autonomy. Each
runtime session has at most one current presence record (single overwrite,
no history lists).

All state transitions expressed as SET-only mutations for replay safety.

Public API:
    PRESENCE_OFF                  — human disconnected
    PRESENCE_REMOTE_LIGHT         — remote / mobile, low-bandwidth
    PRESENCE_ACTIVE_STATION       — seated at the workstation
    PRESENCE_DEEP_WORK            — at the station, interruptions suppressed
    PRESENCE_OVERNIGHT_AUTONOMOUS — human absent, system autonomous
    PresenceState                 — frozen presence record
    compute_presence_state_id     — deterministic presence state ID
    build_presence_state          — construct a new presence state
    build_presence_state_mutations — persistence mutations
    load_presence_state           — reconstruct from state
    set_presence                  — overwrite current presence for session
    summarize_presence_state      — harness-generic summary

Separation note:
    This module is harness-only. No Discord, Notion, UI, or product
    persona logic. Adapters consume presence state — they do not live here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.presence_state]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Presence constants
# ---------------------------------------------------------------------------
PRESENCE_OFF = "off"
PRESENCE_REMOTE_LIGHT = "remote_light"
PRESENCE_ACTIVE_STATION = "active_station"
PRESENCE_DEEP_WORK = "deep_work"
PRESENCE_OVERNIGHT_AUTONOMOUS = "overnight_autonomous"

_VALID_PRESENCES = frozenset(
    {
        PRESENCE_OFF,
        PRESENCE_REMOTE_LIGHT,
        PRESENCE_ACTIVE_STATION,
        PRESENCE_DEEP_WORK,
        PRESENCE_OVERNIGHT_AUTONOMOUS,
    }
)


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_PRESENCE_KEY_PREFIX = "runtime_presence."


def _presence_key(runtime_session_id: str) -> str:
    return f"{_PRESENCE_KEY_PREFIX}{runtime_session_id}"


# ---------------------------------------------------------------------------
# PresenceState — frozen presence record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PresenceState:
    """Immutable record of human presence relative to a runtime session.

    Fields:
        state_id:           deterministic presence state identifier
        runtime_session_id: owning session
        presence:           one of the PRESENCE_* constants
        mode:               current runtime mode at time of setting
        transport:          active transport at time of setting
        set_at:             ISO timestamp of when presence was set
        reason:             optional human-readable reason for transition
        correlation_id:     links to upstream event chain
    """

    state_id: str
    runtime_session_id: str
    presence: str
    mode: str
    transport: str
    set_at: str
    reason: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.set_at:
            object.__setattr__(self, "set_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "correlation_id": self.correlation_id,
            "mode": self.mode,
            "presence": self.presence,
            "reason": self.reason,
            "runtime_session_id": self.runtime_session_id,
            "set_at": self.set_at,
            "state_id": self.state_id,
            "transport": self.transport,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> PresenceState:
        """Reconstruct from plain dict."""
        return PresenceState(
            state_id=str(d.get("state_id", "")),
            runtime_session_id=str(d.get("runtime_session_id", "")),
            presence=str(d.get("presence", "")),
            mode=str(d.get("mode", "")),
            transport=str(d.get("transport", "")),
            set_at=str(d.get("set_at", "")),
            reason=str(d.get("reason", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_presence_state_id(
    runtime_session_id: str,
    set_at: str,
    presence: str,
) -> str:
    """Deterministic presence state ID: same inputs -> same ID.

    Uses SHA-256 of canonical JSON (sorted keys, compact separators).
    """
    canonical = json.dumps(
        {
            "presence": presence,
            "runtime_session_id": runtime_session_id,
            "set_at": set_at,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"prs_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_presence_state(
    *,
    runtime_session_id: str,
    presence: str,
    mode: str = "",
    transport: str = "",
    reason: str = "",
    correlation_id: str = "",
    set_at: str = "",
    state_id: str | None = None,
) -> PresenceState:
    """Construct a new PresenceState with deterministic ID."""
    ts = set_at or _utcnow()
    sid = state_id or compute_presence_state_id(
        runtime_session_id,
        ts,
        presence,
    )
    return PresenceState(
        state_id=sid,
        runtime_session_id=runtime_session_id,
        presence=presence,
        mode=mode,
        transport=transport,
        set_at=ts,
        reason=reason,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Mutation builders — SET only
# ---------------------------------------------------------------------------


def build_presence_state_mutations(
    ps: PresenceState,
) -> list[dict[str, Any]]:
    """Build mutations to persist presence state.

    Writes single key: runtime_presence.{runtime_session_id}
    This is a SET-only overwrite — one current record per session.
    """
    return [
        {
            "op": "SET",
            "key": _presence_key(ps.runtime_session_id),
            "value": ps.to_dict(),
        },
    ]


# ---------------------------------------------------------------------------
# Load helper
# ---------------------------------------------------------------------------


def load_presence_state(
    state: dict[str, Any],
    runtime_session_id: str,
) -> PresenceState | None:
    """Reconstruct current PresenceState from state, or None if missing."""
    raw = state.get(_presence_key(runtime_session_id))
    if not isinstance(raw, dict):
        return None
    return PresenceState.from_dict(raw)


# ---------------------------------------------------------------------------
# Set presence — convenience wrapper
# ---------------------------------------------------------------------------


def set_presence(
    state: dict[str, Any],
    *,
    runtime_session_id: str,
    presence: str,
    mode: str = "",
    transport: str = "",
    reason: str = "",
    correlation_id: str = "",
    set_at: str = "",
) -> tuple[PresenceState, list[dict[str, Any]]]:
    """Build a new PresenceState and its mutations for a session.

    Returns (presence_state, mutations). The caller is responsible for
    applying the mutations to state.
    """
    ps = build_presence_state(
        runtime_session_id=runtime_session_id,
        presence=presence,
        mode=mode,
        transport=transport,
        reason=reason,
        correlation_id=correlation_id,
        set_at=set_at,
    )
    mutations = build_presence_state_mutations(ps)
    return ps, mutations


# ---------------------------------------------------------------------------
# Summary — harness-generic, no product copy
# ---------------------------------------------------------------------------


def summarize_presence_state(presence_state: PresenceState) -> str:
    """Build a harness-generic, human-readable summary of presence state.

    Good: "session sess_abc: active_station via discord (deep focus block)"
    Bad:  "DEX is watching the station"
    """
    parts = [f"session {presence_state.runtime_session_id}:"]
    parts.append(presence_state.presence)
    if presence_state.transport:
        parts.append(f"via {presence_state.transport}")
    if presence_state.mode:
        parts.append(f"in mode {presence_state.mode}")
    if presence_state.reason:
        parts.append(f"({presence_state.reason})")
    return " ".join(parts)
