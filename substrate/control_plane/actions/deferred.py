"""Durable persistence for deferred actions.

When a medium/high-risk action passes validation but has no explicit
approval, the Control Plane defers it. Deferred actions are persisted
as one JSON file per action under /opt/OS/logs/deferred/ so they can
be listed, approved, and resumed later without re-proposing.

One file per action (not a single JSONL) so approval = `os.remove` —
no rewrites, no races on a shared file.
"""

from __future__ import annotations

import json
import os
from dataclasses import fields
from datetime import datetime, timezone
from typing import Any

from .actions import Action
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


DEFERRED_DIR = f"{_ROOT}/logs/deferred"


def _path_for(action_id: str) -> str:
    os.makedirs(DEFERRED_DIR, exist_ok=True)
    return os.path.join(DEFERRED_DIR, f"{action_id}.json")


def save_deferred(action: Action) -> str:
    """Persist a deferred action. Returns the file path written."""
    path = _path_for(action.id)
    payload = {
        "deferred_at": datetime.now(timezone.utc).isoformat(),
        "action": action.to_dict(),
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return path


def load_deferred(action_id: str) -> Action:
    """Load a deferred action by id. Raises FileNotFoundError if missing."""
    path = _path_for(action_id)
    with open(path) as f:
        payload = json.load(f)
    data = payload["action"]
    # Only pass keys that exist on Action so we don't break on schema drift.
    valid_keys = {f.name for f in fields(Action)}
    return Action(**{k: v for k, v in data.items() if k in valid_keys})


def delete_deferred(action_id: str) -> bool:
    """Remove the deferred file. Returns True if removed, False if not present."""
    path = _path_for(action_id)
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False


def list_deferred() -> list[dict[str, Any]]:
    """Return summary dicts for every currently deferred action.

    Summary includes id, type, description, risk_level, source_agent,
    and deferred_at — enough to render a CLI table without loading
    every full payload.
    """
    if not os.path.isdir(DEFERRED_DIR):
        return []
    out: list[dict[str, Any]] = []
    for name in sorted(os.listdir(DEFERRED_DIR)):
        if not name.endswith(".json"):
            continue
        # Skip status sidecars written by deferred_status.py
        if name.endswith(".status.json"):
            continue
        path = os.path.join(DEFERRED_DIR, name)
        try:
            with open(path) as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        a = payload.get("action", {})
        out.append(
            {
                "id": a.get("id"),
                "type": a.get("type"),
                "description": a.get("description"),
                "risk_level": a.get("risk_level"),
                "source_agent": a.get("source_agent"),
                "deferred_at": payload.get("deferred_at"),
            }
        )
    return out
