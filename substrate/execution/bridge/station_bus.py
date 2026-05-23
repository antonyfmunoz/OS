"""
StationBus — MVP transport between EOS and local Station Daemons.

This is the thinnest viable transport we can ship without opening network
ports or shipping raw shell. It is explicitly a placeholder that can be
replaced with WebSocket / HTTP / Tailscale-sidecar without changing the
caller API.

How it works:
  - EOS writes dispatched SafeActions to a per-node JSON outbox file:
        /opt/OS/runtime/.substrate_station/<node_id>.outbox.json
  - The local Station Daemon (running on the founder's workstation, either
    on the same host for development or shuttled via `tailscale file cp`
    in production) polls the outbox, executes, writes results/events to:
        /opt/OS/runtime/.substrate_station/<node_id>.inbox.json
  - EOS polls the inbox to collect ActionResults + StationEvents.

Design properties:
  - No network code in this module. The daemon side is the one that moves
    files between machines — usually a single `tailscale file get` call.
  - Files are plain JSON arrays. Writes are atomic via tempfile + os.replace.
  - Nothing here spawns processes, runs shell, or touches the OS outside
    these two files.
  - A fully in-memory mode is supported for tests and for the VPS-only
    deployment where no station exists yet.

When the real transport is chosen, replace _write_outbox/_drain_inbox and
keep the StationBus interface stable.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional

from substrate.execution.bridge.actions import SafeAction, ActionResult, ActionStatus
from substrate.execution.bridge.station import StationEvent
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



_BUS_DIR = Path(_ROOT) / "runtime" / ".substrate_station"


def _log(msg: str) -> None:
    print(f"[substrate.station_bus] {msg}", file=sys.stderr)


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        _log(f"{path} corrupt ({e}); treating as empty")
        return default


class StationBus:
    """
    Process-wide station transport hub.

    The bus is intentionally stateless across restarts — all state lives in
    the outbox/inbox files. This keeps the VPS side idempotent: a restart
    of EOS cannot lose pending actions, and a restart of the daemon cannot
    lose returned results.
    """

    def __init__(self, root: Path = _BUS_DIR) -> None:
        self._root = root
        self._lock = threading.RLock()
        self._root.mkdir(parents=True, exist_ok=True)

    # ─── Paths ────────────────────────────────────────────────────────────
    def _outbox(self, node_id: str) -> Path:
        return self._root / f"{node_id}.outbox.json"

    def _inbox(self, node_id: str) -> Path:
        return self._root / f"{node_id}.inbox.json"

    # ─── EOS side: dispatch + drain ───────────────────────────────────────
    def dispatch(self, node_id: str, action: SafeAction) -> None:
        """Append a SafeAction to the node's outbox."""
        with self._lock:
            current = _read_json(self._outbox(node_id), default=[])
            current.append(action.to_dict())
            _atomic_write_json(self._outbox(node_id), current)
            _log(f"dispatched {action.kind.value} → {node_id} ({action.action_id})")

    def pending_outbox(self, node_id: str) -> list[dict]:
        with self._lock:
            return list(_read_json(self._outbox(node_id), default=[]))

    def drain_inbox(self, node_id: str) -> list[dict]:
        """
        Read and clear the node's inbox, returning everything the daemon
        wrote since the last drain. Each entry has a `"type"` discriminator
        of either `"result"` or `"event"`.
        """
        with self._lock:
            messages = list(_read_json(self._inbox(node_id), default=[]))
            if messages:
                _atomic_write_json(self._inbox(node_id), [])
            return messages

    # ─── Daemon side helpers (for the eventual local process) ────────────
    # Kept here so both sides share one file-format contract. The daemon
    # imports this module and uses these helpers; it never constructs raw
    # paths.

    def daemon_take_outbox(self, node_id: str) -> list[dict]:
        """Daemon-side: read and clear the outbox in one atomic swap."""
        with self._lock:
            actions = list(_read_json(self._outbox(node_id), default=[]))
            if actions:
                _atomic_write_json(self._outbox(node_id), [])
            return actions

    def daemon_post_result(
        self,
        node_id: str,
        result: ActionResult,
        *,
        kind: Optional[str] = None,
    ) -> None:
        """
        Post an ActionResult back to EOS.

        `kind` is an optional action-kind slug (e.g. "speak_text"). When
        provided it is stamped at the top-level of the payload AND mirrored
        into `data["kind"]` so older consumers that only read `data` still
        see it. Older callers that omit `kind` remain fully supported — the
        drainer tolerates missing kind.
        """
        data = dict(result.data or {})
        if kind and "kind" not in data:
            data["kind"] = kind
        payload: dict = {
            "action_id": result.action_id,
            "status": result.status.value,
            "detail": result.detail,
            "returned_at": result.returned_at,
            "data": data,
        }
        if kind:
            payload["kind"] = kind
        self._inbox_append(node_id, {"type": "result", "payload": payload})

    def daemon_post_event(self, node_id: str, event: StationEvent) -> None:
        self._inbox_append(node_id, {"type": "event", "payload": {
            "node_id": event.node_id,
            "event_type": event.event_type,
            "payload": event.payload,
            "occurred_at": event.occurred_at,
        }})

    def _inbox_append(self, node_id: str, msg: dict) -> None:
        with self._lock:
            current = _read_json(self._inbox(node_id), default=[])
            current.append(msg)
            _atomic_write_json(self._inbox(node_id), current)


_bus_singleton: Optional[StationBus] = None


def get_station_bus() -> StationBus:
    global _bus_singleton
    if _bus_singleton is None:
        _bus_singleton = StationBus()
    return _bus_singleton


def reset_station_bus_for_tests() -> None:
    global _bus_singleton
    _bus_singleton = None
