"""Signals — filesystem-backed event layer for the orchestrator.

A signal is a named event. Handlers are bound workflow names. When a
signal is emitted, its payload is appended to a pending queue on disk.
The orchestrator loop drains the queue, dispatching each pending
signal to every registered handler via `run_workflow(name, context)`.

Design choices (keep it boring):
  - One directory per signal under /opt/OS/logs/signals/<name>/.
  - Pending emissions are JSON files: pending/<ts>-<uuid>.json.
  - On drain, each file is atomically moved to processed/ with a
    small outcome suffix. No database, no broker.
  - Handler bindings live in a single JSON file so bindings survive
    process restarts without forcing each caller to re-register.

This is deliberately NOT a pub/sub framework. It's a durable mailbox
that the loop checks periodically.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

SIGNALS_ROOT = "/opt/OS/logs/signals"
BINDINGS_PATH = os.path.join(SIGNALS_ROOT, "bindings.json")


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def _signal_dir(name: str) -> str:
    return os.path.join(SIGNALS_ROOT, name)


def _pending_dir(name: str) -> str:
    d = os.path.join(_signal_dir(name), "pending")
    os.makedirs(d, exist_ok=True)
    return d


def _processed_dir(name: str) -> str:
    d = os.path.join(_signal_dir(name), "processed")
    os.makedirs(d, exist_ok=True)
    return d


def _load_bindings() -> dict[str, list[str]]:
    if not os.path.isfile(BINDINGS_PATH):
        return {}
    try:
        with open(BINDINGS_PATH) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {k: list(v) for k, v in data.items()}


def _save_bindings(bindings: dict[str, list[str]]) -> None:
    os.makedirs(SIGNALS_ROOT, exist_ok=True)
    tmp = BINDINGS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(bindings, f, indent=2, sort_keys=True)
    os.replace(tmp, BINDINGS_PATH)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class SignalEmission:
    signal: str
    emission_id: str
    emitted_at: str
    payload: dict[str, Any] = field(default_factory=dict)
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "emission_id": self.emission_id,
            "emitted_at": self.emitted_at,
            "payload": self.payload,
        }


def define_signal(name: str) -> None:
    """Create the on-disk directories for a signal. Idempotent."""
    _pending_dir(name)
    _processed_dir(name)


def emit_signal(name: str, payload: dict[str, Any] | None = None) -> SignalEmission:
    """Record a new pending emission for this signal."""
    define_signal(name)
    emission_id = str(uuid.uuid4())
    emitted_at = datetime.now(timezone.utc).isoformat()
    record = {
        "signal": name,
        "emission_id": emission_id,
        "emitted_at": emitted_at,
        "payload": payload or {},
    }
    # Filename: <epoch-ms>-<short-uuid>.json so lexical sort == temporal sort.
    fname = f"{int(time.time() * 1000):013d}-{emission_id[:8]}.json"
    path = os.path.join(_pending_dir(name), fname)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(record, f, indent=2)
    os.replace(tmp, path)
    return SignalEmission(
        signal=name,
        emission_id=emission_id,
        emitted_at=emitted_at,
        payload=record["payload"],
        path=path,
    )


def register_handler(signal: str, workflow_name: str) -> None:
    """Bind a workflow name as a handler for the given signal."""
    define_signal(signal)
    bindings = _load_bindings()
    handlers = bindings.setdefault(signal, [])
    if workflow_name not in handlers:
        handlers.append(workflow_name)
        _save_bindings(bindings)


def unregister_handler(signal: str, workflow_name: str) -> None:
    bindings = _load_bindings()
    if signal in bindings and workflow_name in bindings[signal]:
        bindings[signal].remove(workflow_name)
        _save_bindings(bindings)


def get_handlers(signal: str) -> list[str]:
    return list(_load_bindings().get(signal, []))


def list_signals() -> list[str]:
    if not os.path.isdir(SIGNALS_ROOT):
        return []
    return sorted(
        d
        for d in os.listdir(SIGNALS_ROOT)
        if os.path.isdir(os.path.join(SIGNALS_ROOT, d))
    )


def list_pending(signal: str) -> list[SignalEmission]:
    pdir = _pending_dir(signal)
    results: list[SignalEmission] = []
    for fname in sorted(os.listdir(pdir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(pdir, fname)
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        results.append(
            SignalEmission(
                signal=data.get("signal", signal),
                emission_id=data.get("emission_id", ""),
                emitted_at=data.get("emitted_at", ""),
                payload=data.get("payload", {}),
                path=path,
            )
        )
    return results


def mark_processed(emission: SignalEmission, outcome: str) -> str:
    """Move a pending emission file into processed/ with an outcome tag."""
    if not emission.path or not os.path.isfile(emission.path):
        return ""
    base = os.path.basename(emission.path)
    stem = base[:-5] if base.endswith(".json") else base
    safe_outcome = "".join(c if c.isalnum() or c in "-_" else "_" for c in outcome)
    dest = os.path.join(_processed_dir(emission.signal), f"{stem}-{safe_outcome}.json")
    os.replace(emission.path, dest)
    return dest


__all__ = [
    "SignalEmission",
    "define_signal",
    "emit_signal",
    "register_handler",
    "unregister_handler",
    "get_handlers",
    "list_signals",
    "list_pending",
    "mark_processed",
    "SIGNALS_ROOT",
    "BINDINGS_PATH",
]
