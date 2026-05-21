"""
umh.substrate.workstation_runtime — Workstation-bound execution
continuity and handoff state tracking.

Pure bookkeeping for workstation runs — no transport, routing, or UI logic.
All state transitions expressed as SET/REMOVE mutations for replay safety.

Public API:
    WorkstationRun                  — frozen run record
    compute_workstation_run_id      — deterministic run ID
    build_workstation_run           — construct a new run
    build_workstation_run_mutations — persistence mutations for new run
    start_workstation_run           — transition to active
    complete_workstation_run        — transition to completed
    fail_workstation_run            — transition to failed
    load_workstation_run            — reconstruct from state
    list_active_workstation_runs    — enumerate active run IDs
    list_recent_workstation_runs    — enumerate recent run IDs (bounded)

Separation note:
    This module is harness-only. No Discord, Notion, or UI code.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.workstation_runtime]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_RUN_KEY_PREFIX = "workstation_run."
_ACTIVE_INDEX_PREFIX = "workstation_run_index.active."
_RECENT_INDEX_PREFIX = "workstation_run_index.recent."


def _run_key(run_id: str) -> str:
    return f"{_RUN_KEY_PREFIX}{run_id}"


def _active_key(run_id: str) -> str:
    return f"{_ACTIVE_INDEX_PREFIX}{run_id}"


def _recent_key(run_id: str) -> str:
    return f"{_RECENT_INDEX_PREFIX}{run_id}"


# ---------------------------------------------------------------------------
# WorkstationRun — frozen run record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WorkstationRun:
    """Immutable record of a workstation-bound execution run.

    Fields:
        run_id:          deterministic run identifier
        session_id:      owning session
        node_id:         target workstation node
        created_at:      ISO timestamp of creation
        started_at:      ISO timestamp when run began executing
        completed_at:    ISO timestamp when run finished
        status:          pending | active | completed | failed
        execution_ids:   execution IDs processed in this run
        batch_id:        optional associated batch
        correlation_id:  links run to upstream intent/event
    """

    run_id: str
    session_id: str
    node_id: str
    created_at: str
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"
    execution_ids: tuple[str, ...] = ()
    batch_id: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "batch_id": self.batch_id,
            "completed_at": self.completed_at,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "execution_ids": list(self.execution_ids),
            "node_id": self.node_id,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "status": self.status,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> WorkstationRun:
        """Reconstruct from plain dict."""
        return WorkstationRun(
            run_id=str(d.get("run_id", "")),
            session_id=str(d.get("session_id", "")),
            node_id=str(d.get("node_id", "")),
            created_at=str(d.get("created_at", "")),
            started_at=str(d.get("started_at", "")),
            completed_at=str(d.get("completed_at", "")),
            status=str(d.get("status", "pending")),
            execution_ids=tuple(d.get("execution_ids", ())),
            batch_id=str(d.get("batch_id", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )

    def with_status(self, status: str, **overrides: Any) -> WorkstationRun:
        """Return a copy with updated status and optional field overrides."""
        d = self.to_dict()
        d["status"] = status
        d.update(overrides)
        return WorkstationRun.from_dict(d)


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_workstation_run_id(
    session_id: str,
    correlation_id: str,
) -> str:
    """Deterministic run ID: same session + correlation → same ID.

    Uses SHA-256 of canonical JSON.
    """
    canonical = json.dumps(
        {"session_id": session_id, "correlation_id": correlation_id},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"wkr_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_workstation_run(
    *,
    session_id: str,
    node_id: str,
    correlation_id: str,
    batch_id: str = "",
    execution_ids: tuple[str, ...] = (),
    run_id: str | None = None,
) -> WorkstationRun:
    """Construct a new WorkstationRun with deterministic ID."""
    rid = run_id or compute_workstation_run_id(session_id, correlation_id)
    return WorkstationRun(
        run_id=rid,
        session_id=session_id,
        node_id=node_id,
        created_at=_utcnow(),
        correlation_id=correlation_id,
        batch_id=batch_id,
        execution_ids=execution_ids,
    )


# ---------------------------------------------------------------------------
# Mutation builders — SET / REMOVE only
# ---------------------------------------------------------------------------


def build_workstation_run_mutations(
    run: WorkstationRun,
) -> list[dict[str, Any]]:
    """Build mutations to persist a new workstation run.

    Writes:
        1. Run record: workstation_run.{run_id}
        2. Active index: workstation_run_index.active.{run_id}
        3. Recent index: workstation_run_index.recent.{run_id}
    """
    return [
        {
            "op": "SET",
            "key": _run_key(run.run_id),
            "value": run.to_dict(),
        },
        {
            "op": "SET",
            "key": _active_key(run.run_id),
            "value": {
                "session_id": run.session_id,
                "node_id": run.node_id,
                "created_at": run.created_at,
                "correlation_id": run.correlation_id,
            },
        },
        {
            "op": "SET",
            "key": _recent_key(run.run_id),
            "value": {
                "session_id": run.session_id,
                "node_id": run.node_id,
                "created_at": run.created_at,
                "status": run.status,
            },
        },
    ]


def start_workstation_run(
    run: WorkstationRun,
) -> tuple[WorkstationRun, list[dict[str, Any]]]:
    """Transition run from pending to active.

    Returns (updated_run, mutations).
    """
    now = _utcnow()
    updated = run.with_status("active", started_at=now)
    mutations = [
        {
            "op": "SET",
            "key": _run_key(run.run_id),
            "value": updated.to_dict(),
        },
        {
            "op": "SET",
            "key": _active_key(run.run_id),
            "value": {
                "session_id": run.session_id,
                "node_id": run.node_id,
                "started_at": now,
                "correlation_id": run.correlation_id,
            },
        },
        {
            "op": "SET",
            "key": _recent_key(run.run_id),
            "value": {
                "session_id": run.session_id,
                "node_id": run.node_id,
                "created_at": run.created_at,
                "started_at": now,
                "status": "active",
            },
        },
    ]
    return updated, mutations


def complete_workstation_run(
    run: WorkstationRun,
    *,
    execution_ids: tuple[str, ...] = (),
) -> tuple[WorkstationRun, list[dict[str, Any]]]:
    """Transition run to completed.

    Returns (updated_run, mutations).
    """
    now = _utcnow()
    merged_execs = run.execution_ids + execution_ids
    updated = run.with_status(
        "completed",
        completed_at=now,
        execution_ids=list(merged_execs),
    )
    mutations = [
        {
            "op": "SET",
            "key": _run_key(run.run_id),
            "value": updated.to_dict(),
        },
        {"op": "REMOVE", "key": _active_key(run.run_id)},
        {
            "op": "SET",
            "key": _recent_key(run.run_id),
            "value": {
                "session_id": run.session_id,
                "node_id": run.node_id,
                "completed_at": now,
                "status": "completed",
            },
        },
    ]
    return updated, mutations


def fail_workstation_run(
    run: WorkstationRun,
    *,
    reason: str = "",
) -> tuple[WorkstationRun, list[dict[str, Any]]]:
    """Transition run to failed.

    Returns (updated_run, mutations).
    """
    now = _utcnow()
    updated = run.with_status("failed", completed_at=now)
    mutations = [
        {
            "op": "SET",
            "key": _run_key(run.run_id),
            "value": updated.to_dict(),
        },
        {"op": "REMOVE", "key": _active_key(run.run_id)},
        {
            "op": "SET",
            "key": _recent_key(run.run_id),
            "value": {
                "session_id": run.session_id,
                "node_id": run.node_id,
                "completed_at": now,
                "status": "failed",
                "reason": reason,
            },
        },
    ]
    return updated, mutations


# ---------------------------------------------------------------------------
# Load / list helpers
# ---------------------------------------------------------------------------


def load_workstation_run(
    state: dict[str, Any],
    run_id: str,
) -> WorkstationRun | None:
    """Reconstruct a WorkstationRun from state, or None if missing."""
    raw = state.get(_run_key(run_id))
    if not isinstance(raw, dict):
        return None
    return WorkstationRun.from_dict(raw)


def list_active_workstation_runs(
    state: dict[str, Any],
) -> tuple[str, ...]:
    """Return sorted tuple of active workstation run IDs."""
    ids = sorted(
        k[len(_ACTIVE_INDEX_PREFIX) :]
        for k in state
        if k.startswith(_ACTIVE_INDEX_PREFIX)
    )
    return tuple(ids)


def list_recent_workstation_runs(
    state: dict[str, Any],
    limit: int = 10,
) -> tuple[str, ...]:
    """Return most recent workstation run IDs (bounded).

    Sorts by created_at descending from the recent index entries.
    """
    entries: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(_RECENT_INDEX_PREFIX):
            continue
        if not isinstance(v, dict):
            continue
        rid = k[len(_RECENT_INDEX_PREFIX) :]
        created = str(v.get("created_at", v.get("completed_at", "")))
        entries.append((created, rid))
    entries.sort(reverse=True)
    return tuple(rid for _, rid in entries[:limit])
