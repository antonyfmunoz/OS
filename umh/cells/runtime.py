"""Cell runtime — lifecycle management for cognitive cells.

Manages cell spawning, hydration, checkpointing, and termination.
Cells NEVER execute directly — they produce CellExecutionRequests
that the bridge routes to the control plane.

No imports from execution, adapters, tools, or shell.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

from umh.brains.profile import AuthorityLevel
from umh.cells.models import (
    CellCheckpoint,
    CellContext,
    CellExecutionRequest,
    CellIdentity,
    CellResult,
    CellStatus,
    CellType,
    InvalidTransitionError,
    RequestStatus,
    _gen_id,
    validate_transition,
)
from umh.core.clock import iso_now as _iso_now


# ─── Internal cell state ───────────────────────────────────────────


class _CellState:
    """Mutable internal state for a live cell. Not exposed directly."""

    __slots__ = ("identity", "status", "context", "checkpoints", "version", "updated_at")

    def __init__(self, identity: CellIdentity) -> None:
        self.identity = identity
        self.status = CellStatus.CREATED
        self.context: CellContext | None = None
        self.checkpoints: list[CellCheckpoint] = []
        self.version: int = 0
        self.updated_at: str = _iso_now()

    def transition(self, target: CellStatus) -> None:
        validate_transition(self.identity.cell_id, self.status, target)
        self.status = target
        self.version += 1
        self.updated_at = _iso_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "status": self.status.value,
            "context": self.context.to_dict() if self.context else None,
            "checkpoint_count": len(self.checkpoints),
            "version": self.version,
            "updated_at": self.updated_at,
        }


# ─── Signal emission ──────────────────────────────────────────────


def _emit(signal_type: str, payload: dict[str, Any]) -> None:
    """Best-effort signal emission — never crashes."""
    try:
        from umh.brains.signals import emit_signal

        emit_signal("cell_runtime", signal_type, payload)
    except Exception:
        pass


def _publish_event(event_type: str, payload: dict[str, Any]) -> None:
    """Best-effort event publishing — never crashes."""
    try:
        from umh.events.stream import publish

        publish(event_type, payload=payload, actor_id="cell_runtime")
    except Exception:
        pass


# ─── CellRuntime ───────────────────────────────────────────────────


_lock = threading.Lock()
_cells: dict[str, _CellState] = {}
_execution_requests: list[CellExecutionRequest] = []


def spawn_cell(
    cell_type: CellType,
    *,
    parent_cell_id: str | None = None,
    profile_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> CellIdentity:
    """Spawn a new cell. Returns its immutable identity."""
    cell_id = _gen_id("cell")

    lineage: tuple[str, ...] = ()
    if parent_cell_id:
        with _lock:
            parent = _cells.get(parent_cell_id)
        if parent:
            lineage = parent.identity.lineage + (parent_cell_id,)

    identity = CellIdentity(
        cell_id=cell_id,
        cell_type=cell_type,
        parent_cell_id=parent_cell_id,
        profile_id=profile_id,
        lineage=lineage,
        metadata=metadata or {},
    )

    state = _CellState(identity)

    with _lock:
        _cells[cell_id] = state

    _emit("cell.spawned", {"cell_id": cell_id, "cell_type": cell_type.value})
    _publish_event(
        "cell.spawned",
        {"cell_id": cell_id, "cell_type": cell_type.value, "parent": parent_cell_id},
    )
    return identity


def hydrate_cell(cell_id: str, context: CellContext) -> None:
    """Hydrate a cell with context, transitioning CREATED → HYDRATED."""
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            raise ValueError(f"Cell '{cell_id}' not found")
        state.transition(CellStatus.HYDRATED)
        state.context = context

    _emit("cell.hydrated", {"cell_id": cell_id, "objective": context.objective})
    _publish_event("cell.hydrated", {"cell_id": cell_id})


def activate_cell(cell_id: str) -> None:
    """Activate a hydrated cell, transitioning HYDRATED → ACTIVE."""
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            raise ValueError(f"Cell '{cell_id}' not found")
        state.transition(CellStatus.ACTIVE)

    _publish_event("cell.activated", {"cell_id": cell_id})


def checkpoint_cell(cell_id: str, metadata: dict[str, Any] | None = None) -> CellCheckpoint:
    """Checkpoint a cell's current state. ACTIVE → CHECKPOINTED."""
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            raise ValueError(f"Cell '{cell_id}' not found")
        state.transition(CellStatus.CHECKPOINTED)

        checkpoint = CellCheckpoint(
            checkpoint_id=_gen_id("ckpt"),
            cell_id=cell_id,
            status=CellStatus.CHECKPOINTED,
            context=state.context.to_dict() if state.context else {},
            version=state.version,
            metadata=metadata or {},
        )
        state.checkpoints.append(checkpoint)

    _emit(
        "cell.checkpointed",
        {
            "cell_id": cell_id,
            "checkpoint_id": checkpoint.checkpoint_id,
            "version": checkpoint.version,
        },
    )
    _publish_event(
        "cell.checkpointed",
        {"cell_id": cell_id, "checkpoint_id": checkpoint.checkpoint_id},
    )
    return checkpoint


def terminate_cell(cell_id: str, reason: str = "") -> None:
    """Terminate a cell. Terminal state — no further transitions."""
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            raise ValueError(f"Cell '{cell_id}' not found")
        state.transition(CellStatus.TERMINATED)

    _emit("cell.terminated", {"cell_id": cell_id, "reason": reason})
    _publish_event("cell.terminated", {"cell_id": cell_id, "reason": reason})


def fail_cell(cell_id: str, error: str = "") -> None:
    """Mark a cell as failed. Terminal state."""
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            raise ValueError(f"Cell '{cell_id}' not found")
        state.transition(CellStatus.FAILED)

    _emit("cell.failed", {"cell_id": cell_id, "error": error})
    _publish_event("cell.failed", {"cell_id": cell_id, "error": error})


def request_execution(
    cell_id: str,
    objective: str,
    operation: str,
    *,
    inputs: dict[str, Any] | None = None,
    constraints: tuple[str, ...] = (),
    required_capabilities: tuple[str, ...] = (),
    environment: str = "default",
    metadata: dict[str, Any] | None = None,
) -> CellExecutionRequest:
    """Create an execution request from a cell.

    This does NOT execute anything. It creates a structured request
    that the CellControlBridge can route to the control plane.
    The cell transitions to WAITING status.
    """
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            raise ValueError(f"Cell '{cell_id}' not found")
        if state.status != CellStatus.ACTIVE:
            raise ValueError(
                f"Cell '{cell_id}' must be ACTIVE to request execution, got {state.status.value}"
            )

        authority = state.context.authority_level if state.context else AuthorityLevel.PROPOSE

        request = CellExecutionRequest(
            request_id=_gen_id("creq"),
            cell_id=cell_id,
            objective=objective,
            operation=operation,
            inputs=inputs or {},
            constraints=constraints,
            required_capabilities=required_capabilities,
            environment=environment,
            authority_level=authority,
            metadata=metadata or {},
        )

        _execution_requests.append(request)
        state.transition(CellStatus.WAITING)

    _emit(
        "cell.execution_requested",
        {"cell_id": cell_id, "request_id": request.request_id, "operation": operation},
    )
    _publish_event(
        "cell.execution_requested",
        {"cell_id": cell_id, "request_id": request.request_id, "objective": objective},
    )
    return request


def resume_cell(cell_id: str, result: dict[str, Any] | None = None) -> None:
    """Resume a WAITING cell back to ACTIVE when a result arrives.

    Only cells in WAITING status can be resumed. Terminal cells
    (TERMINATED/FAILED) will raise InvalidTransitionError.
    """
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            raise ValueError(f"Cell '{cell_id}' not found")
        state.transition(CellStatus.ACTIVE)

    _emit(
        "cell.resumed",
        {"cell_id": cell_id, "has_result": result is not None},
    )
    _publish_event(
        "cell.resumed",
        {"cell_id": cell_id, "result_keys": list((result or {}).keys())},
    )


# ─── Queries ───────────────────────────────────────────────────────


def get_cell(cell_id: str) -> dict[str, Any] | None:
    """Get cell state as a dict. Returns None if not found."""
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            return None
        return state.to_dict()


def get_cell_status(cell_id: str) -> CellStatus | None:
    with _lock:
        state = _cells.get(cell_id)
        return state.status if state else None


def list_cells(
    *,
    cell_type: CellType | None = None,
    status: CellStatus | None = None,
) -> list[dict[str, Any]]:
    """List cells, optionally filtered by type or status."""
    with _lock:
        cells = list(_cells.values())

    if cell_type:
        cells = [c for c in cells if c.identity.cell_type == cell_type]
    if status:
        cells = [c for c in cells if c.status == status]

    return [c.to_dict() for c in cells]


def list_execution_requests(cell_id: str | None = None) -> list[CellExecutionRequest]:
    """List execution requests, optionally filtered by cell_id."""
    with _lock:
        if cell_id:
            return [r for r in _execution_requests if r.cell_id == cell_id]
        return list(_execution_requests)


def get_checkpoints(cell_id: str) -> list[CellCheckpoint]:
    """Get all checkpoints for a cell."""
    with _lock:
        state = _cells.get(cell_id)
        if state is None:
            return []
        return list(state.checkpoints)


# ─── Test helper ───────────────────────────────────────────────────


def clear() -> None:
    """Reset all cell state — for testing only."""
    with _lock:
        _cells.clear()
        _execution_requests.clear()
