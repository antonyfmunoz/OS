"""Lightweight status tracking for deferred actions.

Status is stored as a sidecar JSON file next to each deferred action:

    /opt/OS/logs/deferred/<action_id>.json          # the action
    /opt/OS/logs/deferred/<action_id>.status.json   # optional sidecar

Absent sidecar = `pending`. This keeps the default path unchanged from
Phase 2 and means existing deferred actions get the correct default
without any migration. Operators only write a sidecar when they need
to annotate: acknowledged, snoozed, or stale.

Status values:

    pending        default, no sidecar
    acknowledged   operator has seen it, still waiting for action
    snoozed        intentionally deferred again; includes `snoozed_until`
    stale          older than the stale threshold; eligible for pruning

This module does not own the threshold — the caller (deferred CLI)
passes it in. That keeps the storage layer dumb and lets the policy
live with the operator interface.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .deferred import DEFERRED_DIR

VALID_STATUSES: tuple[str, ...] = ("pending", "acknowledged", "snoozed", "stale")
DEFAULT_STALE_HOURS = 72


def _status_path(action_id: str) -> str:
    return os.path.join(DEFERRED_DIR, f"{action_id}.status.json")


@dataclass
class DeferredStatus:
    action_id: str
    status: str = "pending"
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    note: str = ""
    snoozed_until: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "status": self.status,
            "updated_at": self.updated_at,
            "note": self.note,
            "snoozed_until": self.snoozed_until,
        }


def read_status(action_id: str) -> DeferredStatus:
    """Return the sidecar status for a deferred action, or the pending default."""
    path = _status_path(action_id)
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DeferredStatus(action_id=action_id)
    return DeferredStatus(
        action_id=action_id,
        status=data.get("status", "pending"),
        updated_at=data.get("updated_at", ""),
        note=data.get("note", ""),
        snoozed_until=data.get("snoozed_until"),
    )


def write_status(
    action_id: str,
    status: str,
    *,
    note: str = "",
    snoozed_until: str | None = None,
) -> DeferredStatus:
    """Persist a status sidecar for an action. Raises ValueError on bad status."""
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status {status!r}; must be one of {VALID_STATUSES}")
    os.makedirs(DEFERRED_DIR, exist_ok=True)
    rec = DeferredStatus(
        action_id=action_id,
        status=status,
        updated_at=datetime.now(timezone.utc).isoformat(),
        note=note,
        snoozed_until=snoozed_until,
    )
    with open(_status_path(action_id), "w") as f:
        json.dump(rec.to_dict(), f, indent=2)
    return rec


def clear_status(action_id: str) -> bool:
    """Remove the sidecar (used alongside delete_deferred on drop/approve)."""
    try:
        os.remove(_status_path(action_id))
        return True
    except FileNotFoundError:
        return False


def is_stale(deferred_at: str, *, threshold_hours: int) -> bool:
    """Return True if the given ISO timestamp is older than the threshold."""
    try:
        ts = datetime.fromisoformat(deferred_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - ts
    return age >= timedelta(hours=threshold_hours)


def mark_stale_over_threshold(threshold_hours: int = DEFAULT_STALE_HOURS) -> list[str]:
    """Scan the deferred queue and mark actions past the threshold as stale.

    Returns the list of action ids newly marked stale. Skips actions
    already in a non-pending status so operator annotations are not
    clobbered.
    """
    from .deferred import list_deferred  # local import to avoid cycle at tool time

    marked: list[str] = []
    for row in list_deferred():
        action_id = row.get("id") or ""
        if not action_id:
            continue
        current = read_status(action_id)
        if current.status not in ("pending", ""):
            continue
        if is_stale(row.get("deferred_at") or "", threshold_hours=threshold_hours):
            write_status(
                action_id,
                "stale",
                note=f"auto-marked stale after {threshold_hours}h",
            )
            marked.append(action_id)
    return marked


__all__ = [
    "VALID_STATUSES",
    "DEFAULT_STALE_HOURS",
    "DeferredStatus",
    "read_status",
    "write_status",
    "clear_status",
    "is_stale",
    "mark_stale_over_threshold",
]
