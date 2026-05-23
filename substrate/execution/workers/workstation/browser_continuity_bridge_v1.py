"""Browser Continuity Bridge v1.

Bridges browser/GUI operational state into the continuity pipeline.
Feeds browser actions, governance decisions, navigation events,
and visible actuation into the continuity store.

Persist to: data/runtime/browser_continuity/

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .browser_gui_contracts_v1 import (
    BrowserExecutionResult,
    BrowserOperationalMode,
    BrowserState,
    GUIState,
    VisibleActuationEvent,
    _new_id,
    _now_iso,
)


class BrowserContinuityBridge:
    """Bridges browser/GUI state into the continuity pipeline."""

    def __init__(
        self,
        continuity_dir: str | Path = "data/runtime/browser_continuity",
    ) -> None:
        self._dir = Path(continuity_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self._dir / "browser_continuity_events.jsonl"
        self._lineage_path = self._dir / "browser_execution_lineage.jsonl"
        self._snapshot_path = self._dir / "browser_continuity_snapshot.json"

        self._session_id = ""
        self._events_bridged = 0
        self._executions_tracked = 0
        self._mode_transitions = 0
        self._current_mode = BrowserOperationalMode.INSPECTION
        self._recent_urls: list[str] = []
        self._total_successes = 0
        self._total_denials = 0
        self._last_action = ""
        self._last_outcome = ""

    def start_session(self, session_id: str = "") -> str:
        """Begin a new browser continuity session."""
        self._session_id = session_id or _new_id("bcsess")
        self._events_bridged = 0
        self._executions_tracked = 0
        self._mode_transitions = 0
        self._recent_urls = []
        self._total_successes = 0
        self._total_denials = 0
        self._last_action = ""
        self._last_outcome = ""

        self._persist_event(
            {
                "event_type": "browser_session_started",
                "session_id": self._session_id,
                "operational_mode": self._current_mode.value,
                "timestamp": _now_iso(),
            }
        )

        return self._session_id

    def bridge_execution(
        self,
        result: BrowserExecutionResult,
        governance_rules: list[str] | None = None,
    ) -> dict[str, Any]:
        """Bridge a browser execution result into continuity."""
        self._executions_tracked += 1
        self._last_action = result.action_type.value
        self._last_outcome = result.outcome.value

        if result.url_after and result.url_after not in self._recent_urls:
            if len(self._recent_urls) >= 50:
                self._recent_urls = self._recent_urls[-49:]
            self._recent_urls.append(result.url_after)

        if result.succeeded:
            self._total_successes += 1
        elif result.outcome.value == "denied":
            self._total_denials += 1

        lineage_record = {
            "lineage_id": _new_id("blin"),
            "session_id": self._session_id,
            "result_id": result.result_id,
            "action_type": result.action_type.value,
            "outcome": result.outcome.value,
            "url_before": result.url_before,
            "url_after": result.url_after,
            "adapter_used": result.adapter_used,
            "governance_verdict": result.governance_verdict,
            "governance_rules": governance_rules or [],
            "duration_ms": result.duration_ms,
            "error_message": result.error_message,
            "correlation_id": result.correlation_id,
            "timestamp": _now_iso(),
        }
        self._persist_lineage(lineage_record)

        event = {
            "event_type": "browser_execution",
            "session_id": self._session_id,
            "action_type": result.action_type.value,
            "outcome": result.outcome.value,
            "adapter_used": result.adapter_used,
            "governance_verdict": result.governance_verdict,
            "url_after": result.url_after,
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1

        return lineage_record

    def bridge_governance_decision(
        self,
        action_type: str,
        target_url: str,
        verdict: str,
        rules_applied: list[str],
        risk_class: str = "safe",
        denial_reason: str = "",
    ) -> dict[str, Any]:
        """Bridge a governance decision into continuity."""
        event = {
            "event_type": "browser_governance_decision",
            "session_id": self._session_id,
            "action_type": action_type,
            "target_url": target_url,
            "verdict": verdict,
            "rules_applied": rules_applied,
            "risk_class": risk_class,
            "denial_reason": denial_reason,
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1
        return event

    def bridge_mode_transition(
        self,
        old_mode: BrowserOperationalMode,
        new_mode: BrowserOperationalMode,
        reason: str = "",
    ) -> dict[str, Any]:
        """Bridge a mode transition into continuity."""
        self._mode_transitions += 1
        self._current_mode = new_mode

        event = {
            "event_type": "browser_mode_transition",
            "session_id": self._session_id,
            "old_mode": old_mode.value,
            "new_mode": new_mode.value,
            "reason": reason,
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1
        return event

    def bridge_actuation_event(self, event: VisibleActuationEvent) -> None:
        """Bridge a visible actuation event into continuity."""
        self._persist_event(
            {
                "event_type": "visible_actuation",
                "session_id": self._session_id,
                "event_id": event.event_id,
                "action_type": event.action_type.value,
                "url": event.url,
                "governance_verdict": event.governance_verdict,
                "outcome": event.outcome,
                "visibility_confirmed": event.visibility_confirmed,
                "timestamp": _now_iso(),
            }
        )
        self._events_bridged += 1

    def bridge_browser_state(self, state: BrowserState) -> dict[str, Any]:
        """Bridge browser state change into continuity."""
        event = {
            "event_type": "browser_state_change",
            "session_id": self._session_id,
            "state_id": state.state_id,
            "browser_type": state.browser_type,
            "is_running": state.is_running,
            "active_tabs": state.active_tabs,
            "current_url": state.current_url,
            "operational_mode": state.operational_mode.value,
            "content_hash": state.content_hash(),
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1
        return event

    def bridge_gui_state(self, state: GUIState) -> dict[str, Any]:
        """Bridge GUI state change into continuity."""
        event = {
            "event_type": "gui_state_change",
            "session_id": self._session_id,
            "state_id": state.state_id,
            "desktop_session_active": state.desktop_session_active,
            "display_available": state.display_available,
            "active_window_title": state.active_window_title,
            "content_hash": state.content_hash(),
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1
        return event

    def take_snapshot(self) -> dict[str, Any]:
        """Take a continuity snapshot."""
        snapshot = {
            "session_id": self._session_id,
            "operational_mode": self._current_mode.value,
            "executions_tracked": self._executions_tracked,
            "total_successes": self._total_successes,
            "total_denials": self._total_denials,
            "mode_transitions": self._mode_transitions,
            "recent_urls": list(self._recent_urls[-20:]),
            "last_action": self._last_action,
            "last_outcome": self._last_outcome,
            "timestamp": _now_iso(),
        }
        self._snapshot_path.write_text(
            json.dumps(snapshot, indent=2, default=str), encoding="utf-8"
        )
        return snapshot

    def get_execution_lineage(self, limit: int = 20) -> list[dict[str, Any]]:
        """Load recent execution lineage records."""
        if not self._lineage_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(self._lineage_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "events_bridged": self._events_bridged,
            "executions_tracked": self._executions_tracked,
            "mode_transitions": self._mode_transitions,
            "total_successes": self._total_successes,
            "total_denials": self._total_denials,
            "current_mode": self._current_mode.value,
        }

    def _persist_event(self, event: dict[str, Any]) -> None:
        with open(self._events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def _persist_lineage(self, record: dict[str, Any]) -> None:
        with open(self._lineage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
