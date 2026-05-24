"""Perception router — unified orchestration of all perception sources.

Starts/stops webcam, workspace, and metrics monitors. Routes their events
into PerceptionStore and manages OperatorMode transitions:
  - Webcam face gone > auto_away_minutes → system mode → AWAY
  - Webcam face returns → system mode → ACTIVE + welcome-back summary
  - Metrics critical → WARNING perception record
  - Workspace changes → category tracking for mode suggestions
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from umh.modes import ModeState, SystemMode

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

AUTO_AWAY_SECONDS_DEFAULT = 300  # 5 minutes


class PerceptionRouter:
    """Unified perception orchestrator.

    Single entry point for boot.py to initialize all perception sources.
    Routes events to PerceptionStore and drives mode transitions.
    """

    def __init__(
        self,
        mode_state: ModeState,
        node_id: str = "workstation_local",
        auto_away_seconds: float = AUTO_AWAY_SECONDS_DEFAULT,
    ) -> None:
        self._mode_state = mode_state
        self._node_id = node_id
        self._auto_away_seconds = auto_away_seconds

        self._webcam: Any = None
        self._workspace: Any = None
        self._metrics: Any = None

        self._away_triggered = False
        self._welcome_back_callback: Any = None

    def set_welcome_back_callback(self, cb: Any) -> None:
        """Register a callback for when operator returns from AWAY."""
        self._welcome_back_callback = cb

    def start_all(self) -> dict[str, bool]:
        """Start all perception sources. Returns dict of source → started."""
        results: dict[str, bool] = {}

        results["webcam"] = self._start_webcam()
        results["workspace"] = self._start_workspace()
        results["metrics"] = self._start_metrics()

        started = [k for k, v in results.items() if v]
        if started:
            logger.info("Perception started: %s", ", ".join(started))
        else:
            logger.info("No perception sources available")

        return results

    def stop_all(self) -> None:
        """Stop all perception sources."""
        if self._webcam is not None:
            self._webcam.stop()
        if self._workspace is not None:
            self._workspace.stop()
        if self._metrics is not None:
            self._metrics.stop()
        logger.info("Perception stopped")

    def _start_webcam(self) -> bool:
        try:
            from umh.perception.webcam import WebcamMonitor

            self._webcam = WebcamMonitor(on_presence_change=self._on_presence_change)
            return self._webcam.start()
        except Exception as exc:
            logger.debug("Webcam start failed: %s", exc)
            return False

    def _start_workspace(self) -> bool:
        try:
            from umh.perception.workspace import WorkspaceTracker

            self._workspace = WorkspaceTracker(on_change=self._on_workspace_change)
            return self._workspace.start()
        except Exception as exc:
            logger.debug("Workspace tracker start failed: %s", exc)
            return False

    def _start_metrics(self) -> bool:
        try:
            from umh.perception.metrics import MetricsCollector

            self._metrics = MetricsCollector(on_alert=self._on_metrics_alert)
            return self._metrics.start()
        except Exception as exc:
            logger.debug("Metrics collector start failed: %s", exc)
            return False

    def _on_presence_change(self, state: Any) -> None:
        """Handle webcam presence state change."""
        if state.face_detected:
            self._handle_operator_returned()
        else:
            self._handle_operator_absent()

        self._emit_perception(
            source="webcam",
            summary=f"Face {'detected' if state.face_detected else 'lost'} (count={state.face_count})",
            severity="info",
            payload={"face_detected": state.face_detected, "face_count": state.face_count},
        )

        try:
            from umh.signals import emit_presence_change

            emit_presence_change(present=state.face_detected, previous=not state.face_detected)
        except Exception as exc:
            logger.debug("Presence signal emission failed: %s", exc)

    def _handle_operator_returned(self) -> None:
        """Operator face detected after being absent."""
        if not self._away_triggered:
            return

        self._away_triggered = False
        self._mode_state.system = SystemMode.ACTIVE

        self._emit_perception(
            source="webcam",
            summary="Operator returned — switching to ACTIVE",
            severity="info",
            payload={"transition": "away_to_active"},
        )

        self._sync_operator_return()

        if self._welcome_back_callback is not None:
            try:
                self._welcome_back_callback()
            except Exception as exc:
                logger.debug("Welcome back callback failed: %s", exc)

    def _handle_operator_absent(self) -> None:
        """Operator face lost — may trigger AWAY after timeout."""
        if self._away_triggered:
            return
        if self._mode_state.system != SystemMode.ACTIVE:
            return

        if self._webcam is not None:
            absent_s = self._webcam.state.seconds_absent
            if absent_s >= self._auto_away_seconds:
                self._away_triggered = True
                self._mode_state.system = SystemMode.AWAY

                self._emit_perception(
                    source="webcam",
                    summary=f"Operator absent {absent_s:.0f}s — switching to AWAY",
                    severity="info",
                    payload={"transition": "active_to_away", "absent_seconds": absent_s},
                )

                self._sync_operator_away()

    def _on_workspace_change(self, event: Any) -> None:
        """Handle active window change."""
        self._emit_perception(
            source="workspace",
            summary=f"Window: {event.title[:60]}",
            severity="info",
            payload=event.as_dict(),
        )

        try:
            from umh.signals import emit_workspace_change

            emit_workspace_change(
                window_title=getattr(event, "title", ""),
                app_name=getattr(event, "app_name", ""),
                category=getattr(event, "category", ""),
            )
        except Exception as exc:
            logger.debug("Workspace signal emission failed: %s", exc)

    def _on_metrics_alert(self, alert: Any) -> None:
        """Handle metrics threshold breach."""
        severity = "warning" if alert.severity == "warning" else "critical"
        self._emit_perception(
            source="metrics",
            summary=f"{alert.metric} at {alert.value:.1f}% (threshold {alert.threshold:.0f}%)",
            severity=severity,
            payload=alert.as_dict(),
        )

        try:
            from umh.signals import emit_system_metrics

            emit_system_metrics(
                cpu_percent=getattr(alert, "value", 0.0) if alert.metric == "cpu" else 0.0,
                memory_percent=getattr(alert, "value", 0.0) if alert.metric == "memory" else 0.0,
                disk_percent=getattr(alert, "value", 0.0) if alert.metric == "disk" else 0.0,
            )
        except Exception as exc:
            logger.debug("Metrics signal emission failed: %s", exc)

    def _emit_perception(
        self,
        source: str,
        summary: str,
        severity: str = "info",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Record a perception event in the substrate PerceptionStore."""
        try:
            from substrate.execution.bridge.perception import (
                PerceptionRecord,
                PerceptionSeverity,
                PerceptionSource,
                PerceptionStore,
            )

            _SOURCE_MAP = {
                "webcam": PerceptionSource.OPERATOR_SESSION,
                "metrics": PerceptionSource.LOCAL_NODE_STATUS,
            }
            source_enum = _SOURCE_MAP.get(source, PerceptionSource.STATION_PRESENCE)
            sev_enum = PerceptionSeverity(severity)

            record = PerceptionRecord.new(
                source=source_enum,
                summary=summary,
                severity=sev_enum,
                payload=payload or {},
            )
            PerceptionStore.default().put(record)
        except (ImportError, Exception) as exc:
            logger.debug("Perception recording failed: %s", exc)

    def _sync_operator_away(self) -> None:
        """Delegate to operator_sync for AWAY transition."""
        try:
            from umh.operator_sync import sync_away

            sync_away(self._node_id)
        except Exception as exc:
            logger.debug("Operator away sync failed: %s", exc)

    def _sync_operator_return(self) -> None:
        """Delegate to operator_sync for ACTIVE transition."""
        try:
            from umh.operator_sync import sync_return

            sync_return(self._node_id)
        except Exception as exc:
            logger.debug("Operator return sync failed: %s", exc)

    def check_away_timeout(self) -> None:
        """Poll-based check for auto-AWAY timeout.

        Called from the interaction loop to handle the case where the operator
        left but the webcam callback only fires on state change, not on
        timeout expiry. This method checks if enough time has passed.
        """
        if self._webcam is None or not self._webcam.is_running:
            return
        if self._away_triggered:
            return
        if self._mode_state.system != SystemMode.ACTIVE:
            return

        state = self._webcam.state
        if not state.face_detected and state.seconds_absent >= self._auto_away_seconds:
            self._handle_operator_absent()

    # ── Webcam control ──────────────────────────────────────────────────────

    def enable_webcam(self) -> str:
        """Start webcam if not running."""
        if self._webcam is not None and self._webcam.is_running:
            return "Webcam already active"
        ok = self._start_webcam()
        return "Webcam enabled" if ok else "Webcam not available (OpenCV or camera missing)"

    def disable_webcam(self) -> str:
        """Stop webcam."""
        if self._webcam is not None:
            self._webcam.stop()
            return "Webcam disabled"
        return "Webcam not running"

    @property
    def webcam_active(self) -> bool:
        return self._webcam is not None and self._webcam.is_running

    # ── Status ──────────────────────────────────────────────────────────────

    def get_snapshot(self) -> dict[str, Any]:
        """Return full perception state for status display."""
        snap: dict[str, Any] = {}
        if self._webcam is not None:
            snap["webcam"] = self._webcam.get_snapshot()
        if self._workspace is not None:
            snap["workspace"] = self._workspace.get_snapshot()
        if self._metrics is not None:
            snap["metrics"] = self._metrics.get_snapshot()
        return snap
