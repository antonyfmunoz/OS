"""Session Continuity Bridges v1.

Bridges between substrate sessions and each substrate layer:
  ingress ↔ session
  cognition ↔ session
  workflows ↔ session
  embodiment ↔ session
  observability ↔ session
  replay ↔ session

Each bridge captures layer-specific state into the unified
session continuity model and restores it on resume.

UMH substrate subsystem. Phase 96.8BV.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.sessions.persistent_substrate_session_contracts_v1 import (
    SessionCognitionState,
    SessionEmbodimentState,
    SessionIngressState,
    SessionWorkflowState,
    _content_hash,
    _new_id,
    _now_iso,
)


class SessionIngressBridge:
    """Bridges ingress layer state into substrate sessions."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/session_lineage",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def capture_ingress_state(
        self,
        session_id: str,
        active_sources: list[str] | None = None,
        total_signals: int = 0,
        last_signal_id: str = "",
        ingress_session_ids: list[str] | None = None,
    ) -> SessionIngressState:
        state = SessionIngressState(
            session_id=session_id,
            active_sources=active_sources or [],
            total_signals=total_signals,
            last_signal_id=last_signal_id,
            ingress_session_ids=ingress_session_ids or [],
        )
        self._total_captures += 1
        self._persist("ingress_bridge", session_id, state.to_dict())
        return state

    def _persist(self, bridge_type: str, session_id: str, data: dict[str, Any]) -> None:
        path = self._state_dir / f"{bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "bridge_id": _new_id("ssbr"),
                "bridge_type": bridge_type,
                "session_id": session_id,
                "data": data,
                "timestamp": _now_iso(),
            }, default=str) + "\n")


class SessionCognitionBridge:
    """Bridges cognition layer state into substrate sessions."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/session_lineage",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def capture_cognition_state(
        self,
        session_id: str,
        operator_mode: str = "",
        cognition_phase: str = "",
        open_loops: int = 0,
        focus_id: str = "",
        attention_hash: str = "",
    ) -> SessionCognitionState:
        state = SessionCognitionState(
            session_id=session_id,
            operator_mode=operator_mode,
            cognition_phase=cognition_phase,
            open_loops=open_loops,
            focus_id=focus_id,
            attention_hash=attention_hash,
        )
        self._total_captures += 1
        self._persist("cognition_bridge", session_id, state.to_dict())
        return state

    def _persist(self, bridge_type: str, session_id: str, data: dict[str, Any]) -> None:
        path = self._state_dir / f"{bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "bridge_id": _new_id("ssbr"),
                "bridge_type": bridge_type,
                "session_id": session_id,
                "data": data,
                "timestamp": _now_iso(),
            }, default=str) + "\n")


class SessionWorkflowBridge:
    """Bridges workflow layer state into substrate sessions."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/session_lineage",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def capture_workflow_state(
        self,
        session_id: str,
        active_workflows: int = 0,
        completed_workflows: int = 0,
        checkpointed_workflows: int = 0,
        workflow_ids: list[str] | None = None,
    ) -> SessionWorkflowState:
        state = SessionWorkflowState(
            session_id=session_id,
            active_workflows=active_workflows,
            completed_workflows=completed_workflows,
            checkpointed_workflows=checkpointed_workflows,
            workflow_ids=workflow_ids or [],
        )
        self._total_captures += 1
        self._persist("workflow_bridge", session_id, state.to_dict())
        return state

    def _persist(self, bridge_type: str, session_id: str, data: dict[str, Any]) -> None:
        path = self._state_dir / f"{bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "bridge_id": _new_id("ssbr"),
                "bridge_type": bridge_type,
                "session_id": session_id,
                "data": data,
                "timestamp": _now_iso(),
            }, default=str) + "\n")


class SessionEmbodimentBridge:
    """Bridges embodiment layer state into substrate sessions."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/session_lineage",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def capture_embodiment_state(
        self,
        session_id: str,
        workstation_mode: str = "",
        browser_mode: str = "",
        active_adapters: list[str] | None = None,
        embodiment_hash: str = "",
    ) -> SessionEmbodimentState:
        state = SessionEmbodimentState(
            session_id=session_id,
            workstation_mode=workstation_mode,
            browser_mode=browser_mode,
            active_adapters=active_adapters or [],
            embodiment_hash=embodiment_hash,
        )
        self._total_captures += 1
        self._persist("embodiment_bridge", session_id, state.to_dict())
        return state

    def _persist(self, bridge_type: str, session_id: str, data: dict[str, Any]) -> None:
        path = self._state_dir / f"{bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "bridge_id": _new_id("ssbr"),
                "bridge_type": bridge_type,
                "session_id": session_id,
                "data": data,
                "timestamp": _now_iso(),
            }, default=str) + "\n")


class SessionObservabilityBridge:
    """Bridges observability events into session context."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/session_lineage",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def capture_observability_summary(
        self,
        session_id: str,
        total_events: int = 0,
        event_types: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        summary = {
            "session_id": session_id,
            "total_events": total_events,
            "event_types": event_types or {},
            "timestamp": _now_iso(),
        }
        self._total_captures += 1
        self._persist("observability_bridge", session_id, summary)
        return summary

    def _persist(self, bridge_type: str, session_id: str, data: dict[str, Any]) -> None:
        path = self._state_dir / f"{bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "bridge_id": _new_id("ssbr"),
                "bridge_type": bridge_type,
                "session_id": session_id,
                "data": data,
                "timestamp": _now_iso(),
            }, default=str) + "\n")


class SessionReplayBridge:
    """Bridges replay validation into session context."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/session_lineage",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def capture_replay_summary(
        self,
        session_id: str,
        total_validations: int = 0,
        total_passes: int = 0,
        total_failures: int = 0,
    ) -> dict[str, Any]:
        summary = {
            "session_id": session_id,
            "total_validations": total_validations,
            "total_passes": total_passes,
            "total_failures": total_failures,
            "timestamp": _now_iso(),
        }
        self._total_captures += 1
        self._persist("replay_bridge", session_id, summary)
        return summary

    def _persist(self, bridge_type: str, session_id: str, data: dict[str, Any]) -> None:
        path = self._state_dir / f"{bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "bridge_id": _new_id("ssbr"),
                "bridge_type": bridge_type,
                "session_id": session_id,
                "data": data,
                "timestamp": _now_iso(),
            }, default=str) + "\n")
