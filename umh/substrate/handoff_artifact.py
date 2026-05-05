"""
umh.substrate.handoff_artifact — Reusable artifact contracts for
start-of-day briefing and end-of-day handoff.

Deterministic, inspectable, adapter-agnostic. Content is structured,
not branded. No Discord/Notion/UI rendering — product layers consume
these artifacts.

All state transitions expressed as SET-only mutations for replay safety.

Public API:
    HandoffArtifact                   — frozen handoff/briefing artifact
    compute_handoff_artifact_id       — deterministic artifact ID
    build_open_day_handoff_artifact   — build start-of-day briefing artifact
    build_close_day_handoff_artifact  — build end-of-day handoff artifact
    handoff_artifact_to_mutations     — persistence mutations
    load_handoff_artifact             — reconstruct from state
    list_recent_handoff_artifacts     — enumerate recent artifact IDs (bounded)

Separation note:
    This module is harness-only. Publication layers consume HandoffArtifact
    to render branded briefings/reports — that logic does not live here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.handoff_artifact]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Artifact kinds
# ---------------------------------------------------------------------------
ARTIFACT_KIND_OPEN_DAY_BRIEF = "open_day_brief"
ARTIFACT_KIND_CLOSE_DAY_HANDOFF = "close_day_handoff"


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_ARTIFACT_KEY_PREFIX = "handoff_artifact."
_ARTIFACT_INDEX_PREFIX = "handoff_artifact_index.session."


def _artifact_key(artifact_id: str) -> str:
    return f"{_ARTIFACT_KEY_PREFIX}{artifact_id}"


def _index_key(runtime_session_id: str, artifact_id: str) -> str:
    return f"{_ARTIFACT_INDEX_PREFIX}{runtime_session_id}.{artifact_id}"


# ---------------------------------------------------------------------------
# HandoffArtifact — frozen handoff/briefing record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class HandoffArtifact:
    """Immutable artifact for day-open briefings and day-close handoffs.

    Fields:
        artifact_id:            deterministic artifact identifier
        runtime_session_id:     owning session
        artifact_kind:          open_day_brief | close_day_handoff
        created_at:             ISO timestamp
        title:                  human-readable title
        summary:                brief overview
        completed_items:        items completed since last handoff
        failed_items:           items that failed
        open_items:             items still in progress
        pending_approvals:      approvals waiting for human resolution
        active_batches:         execution batches currently active
        active_runs:            workstation runs currently active
        next_recommended_action: harness-suggested next action
        correlation_id:         links to upstream event chain
    """

    artifact_id: str
    runtime_session_id: str
    artifact_kind: str
    created_at: str
    title: str
    summary: str
    completed_items: tuple[str, ...] = ()
    failed_items: tuple[str, ...] = ()
    open_items: tuple[str, ...] = ()
    pending_approvals: tuple[str, ...] = ()
    active_batches: tuple[str, ...] = ()
    active_runs: tuple[str, ...] = ()
    next_recommended_action: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "active_batches": list(self.active_batches),
            "active_runs": list(self.active_runs),
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind,
            "completed_items": list(self.completed_items),
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "failed_items": list(self.failed_items),
            "next_recommended_action": self.next_recommended_action,
            "open_items": list(self.open_items),
            "pending_approvals": list(self.pending_approvals),
            "runtime_session_id": self.runtime_session_id,
            "summary": self.summary,
            "title": self.title,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> HandoffArtifact:
        """Reconstruct from plain dict."""
        return HandoffArtifact(
            artifact_id=str(d.get("artifact_id", "")),
            runtime_session_id=str(d.get("runtime_session_id", "")),
            artifact_kind=str(d.get("artifact_kind", "")),
            created_at=str(d.get("created_at", "")),
            title=str(d.get("title", "")),
            summary=str(d.get("summary", "")),
            completed_items=tuple(d.get("completed_items", ())),
            failed_items=tuple(d.get("failed_items", ())),
            open_items=tuple(d.get("open_items", ())),
            pending_approvals=tuple(d.get("pending_approvals", ())),
            active_batches=tuple(d.get("active_batches", ())),
            active_runs=tuple(d.get("active_runs", ())),
            next_recommended_action=str(d.get("next_recommended_action", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_handoff_artifact_id(
    runtime_session_id: str,
    artifact_kind: str,
    created_at: str,
) -> str:
    """Deterministic handoff artifact ID: same inputs -> same ID.

    Uses SHA-256 of canonical JSON.
    """
    canonical = json.dumps(
        {
            "artifact_kind": artifact_kind,
            "created_at": created_at,
            "runtime_session_id": runtime_session_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"hda_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# State scanning helpers (bounded, namespaced)
# ---------------------------------------------------------------------------

# Reuse key prefixes from existing substrate modules for cross-module queries
_ACTIVE_INTENT_PREFIX = "active_intent."
_EXECUTION_BATCH_PREFIX = "execution_batch."
_EXECUTION_BATCH_STATUS_KEY = "status"
_WORKSTATION_RUN_ACTIVE_PREFIX = "workstation_run_index.active."
_APPROVAL_PREFIX = "approval_request."
_EXECUTION_RESULT_PREFIX = "execution_result:"
_RUNTIME_ARTIFACT_PREFIX = "runtime_artifact."


def _scan_completed_items(state: dict[str, Any], limit: int = 50) -> tuple[str, ...]:
    """Scan state for recently completed execution results (bounded)."""
    items: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(_EXECUTION_RESULT_PREFIX):
            continue
        if not isinstance(v, dict):
            continue
        if v.get("status") != "completed":
            continue
        eid = k[len(_EXECUTION_RESULT_PREFIX) :]
        completed_at = str(v.get("completed_at", ""))
        items.append((completed_at, eid))
    items.sort(reverse=True)
    return tuple(eid for _, eid in items[:limit])


def _scan_failed_items(state: dict[str, Any], limit: int = 50) -> tuple[str, ...]:
    """Scan state for recently failed execution results (bounded)."""
    items: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(_EXECUTION_RESULT_PREFIX):
            continue
        if not isinstance(v, dict):
            continue
        if v.get("status") != "failed":
            continue
        eid = k[len(_EXECUTION_RESULT_PREFIX) :]
        items.append((str(v.get("completed_at", "")), eid))
    items.sort(reverse=True)
    return tuple(eid for _, eid in items[:limit])


def _scan_open_intents(state: dict[str, Any]) -> tuple[str, ...]:
    """Scan state for active/pending intent IDs."""
    ids = sorted(
        k[len(_ACTIVE_INTENT_PREFIX) :]
        for k in state
        if k.startswith(_ACTIVE_INTENT_PREFIX)
        and isinstance(state[k], dict)
        and state[k].get("status") in ("active", "pending")
    )
    return tuple(ids)


def _scan_pending_approvals(state: dict[str, Any]) -> tuple[str, ...]:
    """Scan state for pending approval request IDs."""
    ids = sorted(
        k[len(_APPROVAL_PREFIX) :]
        for k in state
        if k.startswith(_APPROVAL_PREFIX)
        and isinstance(state[k], dict)
        and state[k].get("status") == "pending"
    )
    return tuple(ids)


def _scan_active_batches(state: dict[str, Any]) -> tuple[str, ...]:
    """Scan state for active execution batch IDs."""
    ids = sorted(
        k[len(_EXECUTION_BATCH_PREFIX) :]
        for k in state
        if k.startswith(_EXECUTION_BATCH_PREFIX)
        and isinstance(state[k], dict)
        and state[k].get(_EXECUTION_BATCH_STATUS_KEY) in ("pending", "active")
    )
    return tuple(ids)


def _scan_active_runs(state: dict[str, Any]) -> tuple[str, ...]:
    """Scan state for active workstation run IDs."""
    ids = sorted(
        k[len(_WORKSTATION_RUN_ACTIVE_PREFIX) :]
        for k in state
        if k.startswith(_WORKSTATION_RUN_ACTIVE_PREFIX)
    )
    return tuple(ids)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def build_open_day_handoff_artifact(
    state: dict[str, Any],
    runtime_session_id: str,
    created_at: str,
    correlation_id: str = "",
) -> HandoffArtifact:
    """Build a start-of-day briefing artifact from current state.

    Scans state for completed/failed/open items, pending approvals,
    active batches and runs. Content is structured — not product copy.
    """
    ts = created_at or _utcnow()
    aid = compute_handoff_artifact_id(
        runtime_session_id,
        ARTIFACT_KIND_OPEN_DAY_BRIEF,
        ts,
    )

    completed = _scan_completed_items(state)
    failed = _scan_failed_items(state)
    open_items = _scan_open_intents(state)
    approvals = _scan_pending_approvals(state)
    batches = _scan_active_batches(state)
    runs = _scan_active_runs(state)

    # Derive recommended action
    if approvals:
        next_action = f"resolve {len(approvals)} pending approval(s)"
    elif failed:
        next_action = f"review {len(failed)} failed execution(s)"
    elif open_items:
        next_action = f"continue {len(open_items)} open intent(s)"
    else:
        next_action = "no pending items"

    summary = (
        f"briefing: {len(completed)} completed, {len(failed)} failed, "
        f"{len(open_items)} open, {len(approvals)} approvals pending"
    )

    return HandoffArtifact(
        artifact_id=aid,
        runtime_session_id=runtime_session_id,
        artifact_kind=ARTIFACT_KIND_OPEN_DAY_BRIEF,
        created_at=ts,
        title="day-open briefing",
        summary=summary,
        completed_items=completed,
        failed_items=failed,
        open_items=open_items,
        pending_approvals=approvals,
        active_batches=batches,
        active_runs=runs,
        next_recommended_action=next_action,
        correlation_id=correlation_id,
    )


def build_close_day_handoff_artifact(
    state: dict[str, Any],
    runtime_session_id: str,
    created_at: str,
    correlation_id: str = "",
) -> HandoffArtifact:
    """Build an end-of-day handoff artifact from current state.

    Same scanning as open-day brief but titled/summarized for handoff.
    """
    ts = created_at or _utcnow()
    aid = compute_handoff_artifact_id(
        runtime_session_id,
        ARTIFACT_KIND_CLOSE_DAY_HANDOFF,
        ts,
    )

    completed = _scan_completed_items(state)
    failed = _scan_failed_items(state)
    open_items = _scan_open_intents(state)
    approvals = _scan_pending_approvals(state)
    batches = _scan_active_batches(state)
    runs = _scan_active_runs(state)

    # Derive recommended action for overnight/next-day
    if batches or runs:
        next_action = f"monitor {len(batches)} batch(es), {len(runs)} run(s) overnight"
    elif open_items:
        next_action = f"resume {len(open_items)} open intent(s) tomorrow"
    else:
        next_action = "clean state for next session"

    summary = (
        f"handoff: {len(completed)} completed, {len(failed)} failed, "
        f"{len(open_items)} open, {len(batches)} batches active"
    )

    return HandoffArtifact(
        artifact_id=aid,
        runtime_session_id=runtime_session_id,
        artifact_kind=ARTIFACT_KIND_CLOSE_DAY_HANDOFF,
        created_at=ts,
        title="day-close handoff",
        summary=summary,
        completed_items=completed,
        failed_items=failed,
        open_items=open_items,
        pending_approvals=approvals,
        active_batches=batches,
        active_runs=runs,
        next_recommended_action=next_action,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Mutation builders — SET only
# ---------------------------------------------------------------------------


def handoff_artifact_to_mutations(
    artifact: HandoffArtifact,
) -> list[dict[str, Any]]:
    """Build mutations to persist a handoff artifact.

    Writes:
        1. Artifact record: handoff_artifact.{artifact_id}
        2. Session index: handoff_artifact_index.session.{session_id}.{artifact_id}
    """
    return [
        {
            "op": "SET",
            "key": _artifact_key(artifact.artifact_id),
            "value": artifact.to_dict(),
        },
        {
            "op": "SET",
            "key": _index_key(artifact.runtime_session_id, artifact.artifact_id),
            "value": {
                "artifact_kind": artifact.artifact_kind,
                "created_at": artifact.created_at,
                "title": artifact.title,
            },
        },
    ]


# ---------------------------------------------------------------------------
# Load / list helpers
# ---------------------------------------------------------------------------


def load_handoff_artifact(
    state: dict[str, Any],
    artifact_id: str,
) -> HandoffArtifact | None:
    """Reconstruct a HandoffArtifact from state, or None if missing."""
    raw = state.get(_artifact_key(artifact_id))
    if not isinstance(raw, dict):
        return None
    return HandoffArtifact.from_dict(raw)


def list_recent_handoff_artifacts(
    state: dict[str, Any],
    runtime_session_id: str,
    limit: int = 20,
) -> tuple[str, ...]:
    """Return most recent handoff artifact IDs for a session (bounded).

    Scans session index keys and sorts by created_at descending.
    """
    prefix = f"{_ARTIFACT_INDEX_PREFIX}{runtime_session_id}."
    entries: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(prefix):
            continue
        if not isinstance(v, dict):
            continue
        aid = k[len(prefix) :]
        created = str(v.get("created_at", ""))
        entries.append((created, aid))
    entries.sort(reverse=True)
    return tuple(aid for _, aid in entries[:limit])
