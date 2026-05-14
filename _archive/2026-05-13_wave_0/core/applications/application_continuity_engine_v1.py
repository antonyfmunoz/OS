"""Application Continuity Engine v1.

Manages cross-application continuity, domain state transitions,
projection restoration, checkpoint coordination, and session bridging.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.applications.application_projection_contracts_v1 import (
    ApplicationContinuityState,
    _now_iso,
)

MAX_CHECKPOINTS_PER_APP = 20
MAX_SESSION_CHAIN = 50


class ApplicationContinuityEngine:
    """Manages application continuity across projections."""

    def __init__(self, state_dir: str | Path = "data/runtime/applications") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._states: dict[str, ApplicationContinuityState] = {}
        self._checkpoints: list[dict[str, Any]] = []

    def create_checkpoint(
        self,
        app_id: str,
        session_id: str = "",
        state_data: str = "",
    ) -> dict[str, Any]:
        app_checkpoints = [
            c for c in self._checkpoints if c["app_id"] == app_id
        ]
        if len(app_checkpoints) >= MAX_CHECKPOINTS_PER_APP:
            self._checkpoints = [
                c for c in self._checkpoints if c["app_id"] != app_id
            ][-MAX_CHECKPOINTS_PER_APP + 1:] + [
                c for c in self._checkpoints if c["app_id"] != app_id
            ]
            app_checkpoints = [
                c for c in self._checkpoints if c["app_id"] == app_id
            ]

        content_hash = hashlib.sha256(
            f"{app_id}:{session_id}:{state_data}".encode()
        ).hexdigest()[:16]

        checkpoint = {
            "app_id": app_id,
            "session_id": session_id,
            "content_hash": content_hash,
            "state_data": state_data,
            "created_at": _now_iso(),
        }
        self._checkpoints.append(checkpoint)

        if app_id not in self._states:
            self._states[app_id] = ApplicationContinuityState(
                application_id=app_id,
            )
        state = self._states[app_id]
        state.last_checkpoint = content_hash
        if session_id and session_id not in state.session_chain:
            if len(state.session_chain) < MAX_SESSION_CHAIN:
                state.session_chain.append(session_id)

        path = self._state_dir / "continuity_checkpoints.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(checkpoint, default=str) + "\n")

        return checkpoint

    def restore(self, app_id: str) -> dict[str, Any] | None:
        state = self._states.get(app_id)
        if state is None:
            return None
        return state.to_dict()

    def get_checkpoints(
        self,
        app_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        app_checkpoints = [
            c for c in self._checkpoints if c["app_id"] == app_id
        ]
        return app_checkpoints[-limit:]

    def get_session_chain(self, app_id: str) -> list[str]:
        state = self._states.get(app_id)
        if state is None:
            return []
        return list(state.session_chain)

    def get_stats(self) -> dict[str, object]:
        return {
            "total_checkpoints": len(self._checkpoints),
            "tracked_applications": len(self._states),
            "max_checkpoints_per_app": MAX_CHECKPOINTS_PER_APP,
        }
