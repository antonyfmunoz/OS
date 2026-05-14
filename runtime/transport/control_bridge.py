"""
Control Layer v1 — Control Bridge (VPS side).

A bounded, file-backed queue of ControlCommand envelopes addressed to a node.
No networking. The bridge is a queue, not a transport. Local-first by design.

Design rules (non-negotiable):
    * No background loops. No daemons. No automatic dispatch.
    * Bounded queue per node (MAX_QUEUE_PER_NODE).
    * Persistent via the existing substrate JSON KV store.
    * Never raises. All errors return as result dicts.
"""

from __future__ import annotations

import threading
from typing import Any

from runtime.transport import control_commands as cc
from runtime.transport.storage import get_storage

LAYER_NAME = "control_bridge"
LAYER_VERSION = "v1"

_STORAGE_KEY = "control_bridge_queue_v1"
MAX_QUEUE_PER_NODE = 100

_lock = threading.Lock()


def _load_state() -> dict[str, Any]:
    try:
        data = get_storage().get(_STORAGE_KEY, default={})
        if not isinstance(data, dict):
            return {"pending": {}, "acked": {}}
        data.setdefault("pending", {})
        data.setdefault("acked", {})
        return data
    except Exception:  # noqa: BLE001
        return {"pending": {}, "acked": {}}


def _save_state(state: dict[str, Any]) -> None:
    try:
        get_storage().put(_STORAGE_KEY, state)
    except Exception:  # noqa: BLE001
        pass


def send_command(command: cc.ControlCommand) -> dict[str, Any]:
    """
    Enqueue a command for the target node. Bounded and validated.
    Returns {"ok": bool, "reason": str, "command_id": str|None}.
    """
    ok, reason = cc.validate(command)
    if not ok:
        return {"ok": False, "reason": reason, "command_id": None}

    with _lock:
        state = _load_state()
        pending = state["pending"]
        node_q = pending.setdefault(command.node_id, [])
        if len(node_q) >= MAX_QUEUE_PER_NODE:
            return {
                "ok": False,
                "reason": "queue_full",
                "command_id": command.command_id,
            }
        node_q.append(command.to_dict())
        _save_state(state)

    return {"ok": True, "reason": "queued", "command_id": command.command_id}


def get_pending_commands(
    node_id: str, limit: int | None = None
) -> list[cc.ControlCommand]:
    """
    Return pending commands for a node, in FIFO order. Never raises.

    `limit` is an optional bound (Control Layer v2). When provided, the
    returned list is truncated to at most `limit` envelopes. Hard cap is
    enforced at 10 to keep batches bounded for the remote daemon.
    """
    if not node_id:
        return []
    with _lock:
        state = _load_state()
        rows = list(state.get("pending", {}).get(node_id, []) or [])
    out: list[cc.ControlCommand] = []
    for row in rows:
        try:
            out.append(cc.ControlCommand.from_dict(row))
        except Exception:  # noqa: BLE001
            continue
    if limit is not None:
        try:
            cap = max(0, min(int(limit), 10))
        except Exception:  # noqa: BLE001
            cap = 10
        out = out[:cap]
    return out


def ack_command(
    command_id: str, result: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Mark a command as completed: removes from pending across nodes,
    moves into a small bounded 'acked' ring per node.
    """
    if not command_id:
        return {"ok": False, "reason": "missing_command_id"}
    with _lock:
        state = _load_state()
        pending = state.get("pending", {}) or {}
        acked = state.get("acked", {}) or {}
        found_node = None
        found_row = None
        for node_id, rows in pending.items():
            for i, row in enumerate(rows):
                if row.get("command_id") == command_id:
                    found_node = node_id
                    found_row = rows.pop(i)
                    break
            if found_node:
                break
        if found_row is None:
            # Idempotency: if this command_id is already in any acked ring,
            # treat as success no-op (Control Layer v2 requirement).
            for _node, ring in acked.items():
                for prior in ring:
                    if prior.get("command_id") == command_id:
                        return {
                            "ok": True,
                            "reason": "already_acked",
                            "command_id": command_id,
                        }
            return {"ok": False, "reason": "not_found"}
        if isinstance(result, dict):
            try:
                found_row["result"] = result
            except Exception:  # noqa: BLE001
                pass
        ring = acked.setdefault(found_node, [])
        ring.append(found_row)
        # Bounded history: keep last 100 acks per node.
        if len(ring) > 100:
            del ring[:-100]
        state["pending"] = pending
        state["acked"] = acked
        _save_state(state)
    return {"ok": True, "reason": "acked", "command_id": command_id}


def queue_depth(node_id: str) -> int:
    """Inspect-only helper. Never raises."""
    with _lock:
        state = _load_state()
        return len(state.get("pending", {}).get(node_id, []) or [])


def clear_queue(node_id: str) -> dict[str, Any]:
    """Operator-explicit reset. Never used implicitly."""
    with _lock:
        state = _load_state()
        pending = state.get("pending", {}) or {}
        removed = len(pending.get(node_id, []) or [])
        pending[node_id] = []
        state["pending"] = pending
        _save_state(state)
    return {"ok": True, "removed": removed}
