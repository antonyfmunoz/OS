"""
umh.substrate.runtime_continuity — Persistent, transport-agnostic
continuity primitives for runtime sessions and handoffs.

Extends the session model from runtime_session.py at the harness level.
All helpers are pure functions over bounded in-memory state keys.

Public API:
    RuntimeHandoff           — frozen snapshot for session handoff
    build_runtime_handoff    — build handoff from state dict
    list_active_intent_ids   — active intents from state
    list_pending_intent_ids  — pending intents from state
    list_recent_execution_ids — recent executions (bounded)
    list_recent_artifact_ids  — recent artifacts (bounded)
    build_runtime_snapshot_summary — harness-generic one-line summary

Separation note:
    This module is harness-only. It does not reference any transport
    (Discord, Notion, UI) or product-specific rendering.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.runtime_continuity]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key prefixes (must match intent_models, execution_contract, etc.)
# ---------------------------------------------------------------------------
_ACTIVE_INTENT_PREFIX = "active_intent."
_INTENT_PREFIX = "intent:"
_EXECUTION_RESULT_PREFIX = "execution_result:"
_RUNTIME_ARTIFACT_PREFIX = "runtime_artifact."


# ---------------------------------------------------------------------------
# RuntimeHandoff — frozen snapshot for session continuity
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RuntimeHandoff:
    """Immutable snapshot capturing everything needed for a session handoff.

    Fields:
        session_id:          current session identifier
        mode:                runtime mode (active, background, etc.)
        started_at:          session start timestamp
        last_active_at:      last activity timestamp
        open_task_count:     number of open tasks in session
        active_transport:    current transport identifier
        active_intent_ids:   intents currently being executed
        pending_intent_ids:  intents queued but not yet started
        latest_artifact_ids: recent artifact IDs (bounded)
        latest_execution_ids: recent execution IDs (bounded)
        summary:             harness-generic summary string
    """

    session_id: str
    mode: str = ""
    started_at: str = ""
    last_active_at: str = ""
    open_task_count: int = 0
    active_transport: str = ""
    active_intent_ids: tuple[str, ...] = ()
    pending_intent_ids: tuple[str, ...] = ()
    latest_artifact_ids: tuple[str, ...] = ()
    latest_execution_ids: tuple[str, ...] = ()
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "active_intent_ids": list(self.active_intent_ids),
            "active_transport": self.active_transport,
            "last_active_at": self.last_active_at,
            "latest_artifact_ids": list(self.latest_artifact_ids),
            "latest_execution_ids": list(self.latest_execution_ids),
            "mode": self.mode,
            "open_task_count": self.open_task_count,
            "pending_intent_ids": list(self.pending_intent_ids),
            "session_id": self.session_id,
            "started_at": self.started_at,
            "summary": self.summary,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> RuntimeHandoff:
        """Reconstruct from plain dict."""
        return RuntimeHandoff(
            session_id=str(d.get("session_id", "")),
            mode=str(d.get("mode", "")),
            started_at=str(d.get("started_at", "")),
            last_active_at=str(d.get("last_active_at", "")),
            open_task_count=int(d.get("open_task_count", 0)),
            active_transport=str(d.get("active_transport", "")),
            active_intent_ids=tuple(d.get("active_intent_ids", ())),
            pending_intent_ids=tuple(d.get("pending_intent_ids", ())),
            latest_artifact_ids=tuple(d.get("latest_artifact_ids", ())),
            latest_execution_ids=tuple(d.get("latest_execution_ids", ())),
            summary=str(d.get("summary", "")),
        )


# ---------------------------------------------------------------------------
# Pure helpers — scan bounded, namespaced keys from in-memory state
# ---------------------------------------------------------------------------


def list_active_intent_ids(state: dict[str, Any]) -> tuple[str, ...]:
    """Return sorted tuple of actively-executing intent IDs from state.

    Scans keys matching ``active_intent.{id}`` — these are bounded index
    entries maintained by intent_models mutation builders. Only returns
    intents whose status is ``active`` (not pending, completed, or failed).
    """
    ids = sorted(
        k[len(_ACTIVE_INTENT_PREFIX) :]
        for k in state
        if k.startswith(_ACTIVE_INTENT_PREFIX)
        and isinstance(state[k], dict)
        and state[k].get("status") == "active"
    )
    return tuple(ids)


def list_pending_intent_ids(state: dict[str, Any]) -> tuple[str, ...]:
    """Return sorted tuple of pending (not-yet-started) intent IDs.

    An intent is pending if its index entry has status == 'pending'.
    """
    ids = sorted(
        k[len(_ACTIVE_INTENT_PREFIX) :]
        for k in state
        if k.startswith(_ACTIVE_INTENT_PREFIX)
        and isinstance(state[k], dict)
        and state[k].get("status") == "pending"
    )
    return tuple(ids)


def list_recent_execution_ids(
    state: dict[str, Any],
    limit: int = 10,
) -> tuple[str, ...]:
    """Return most recent execution IDs from state (bounded).

    Scans ``execution_result:{id}`` keys and sorts by ``completed_at``
    descending, returning at most ``limit`` entries.
    """
    entries: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(_EXECUTION_RESULT_PREFIX):
            continue
        if not isinstance(v, dict):
            continue
        exec_id = k[len(_EXECUTION_RESULT_PREFIX) :]
        completed_at = str(v.get("completed_at", v.get("issued_at", "")))
        entries.append((completed_at, exec_id))
    entries.sort(reverse=True)
    return tuple(eid for _, eid in entries[:limit])


def list_recent_artifact_ids(
    state: dict[str, Any],
    limit: int = 10,
) -> tuple[str, ...]:
    """Return most recent artifact IDs from state (bounded).

    Scans ``runtime_artifact.{id}`` index keys and sorts by
    ``created_at`` descending, returning at most ``limit`` entries.
    """
    entries: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(_RUNTIME_ARTIFACT_PREFIX):
            continue
        if not isinstance(v, dict):
            continue
        art_id = k[len(_RUNTIME_ARTIFACT_PREFIX) :]
        created_at = str(v.get("created_at", ""))
        entries.append((created_at, art_id))
    entries.sort(reverse=True)
    return tuple(aid for _, aid in entries[:limit])


# ---------------------------------------------------------------------------
# Handoff builder
# ---------------------------------------------------------------------------


def build_runtime_handoff(
    state: dict[str, Any],
    session_id: str,
) -> RuntimeHandoff | None:
    """Build a RuntimeHandoff from current in-memory state.

    Returns None if session_id is empty.
    """
    if not session_id:
        return None

    # Pull session record if present
    session_raw = state.get("runtime_session")
    if isinstance(session_raw, dict):
        mode = str(session_raw.get("active_mode", ""))
        started_at = str(session_raw.get("started_at", ""))
        last_active_at = str(session_raw.get("last_active_at", ""))
        open_task_count = int(session_raw.get("open_task_count", 0))
        active_transport = str(session_raw.get("transport", ""))
    else:
        mode = ""
        started_at = ""
        last_active_at = ""
        open_task_count = 0
        active_transport = ""

    active = list_active_intent_ids(state)
    pending = list_pending_intent_ids(state)
    execs = list_recent_execution_ids(state)
    artifacts = list_recent_artifact_ids(state)

    summary = build_runtime_snapshot_summary(
        active_intent_count=len(active),
        pending_intent_count=len(pending),
        recent_execution_count=len(execs),
        recent_artifact_count=len(artifacts),
        open_task_count=open_task_count,
    )

    return RuntimeHandoff(
        session_id=session_id,
        mode=mode,
        started_at=started_at,
        last_active_at=last_active_at,
        open_task_count=open_task_count,
        active_transport=active_transport,
        active_intent_ids=active,
        pending_intent_ids=pending,
        latest_artifact_ids=artifacts,
        latest_execution_ids=execs,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Snapshot summary — harness-generic, no product copy
# ---------------------------------------------------------------------------


def build_runtime_snapshot_summary(
    *,
    active_intent_count: int = 0,
    pending_intent_count: int = 0,
    recent_execution_count: int = 0,
    recent_artifact_count: int = 0,
    open_task_count: int = 0,
) -> str:
    """Build a harness-generic, human-readable summary of session state.

    Good: "session has 2 active intents, 1 pending intent, 3 recent executions"
    Bad:  "DEX completed your work successfully"
    """
    parts: list[str] = []
    if active_intent_count:
        parts.append(
            f"{active_intent_count} active intent"
            f"{'s' if active_intent_count != 1 else ''}"
        )
    if pending_intent_count:
        parts.append(
            f"{pending_intent_count} pending intent"
            f"{'s' if pending_intent_count != 1 else ''}"
        )
    if recent_execution_count:
        parts.append(
            f"{recent_execution_count} recent execution"
            f"{'s' if recent_execution_count != 1 else ''}"
        )
    if recent_artifact_count:
        parts.append(
            f"{recent_artifact_count} recent artifact"
            f"{'s' if recent_artifact_count != 1 else ''}"
        )
    if open_task_count:
        parts.append(
            f"{open_task_count} open task{'s' if open_task_count != 1 else ''}"
        )
    if not parts:
        return "session is empty"
    return "session has " + ", ".join(parts)
