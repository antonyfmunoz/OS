"""UMH Screen Context Providers — three modes of screen awareness.

Phase 33. Provider contract with three implementations:
  - InferredScreenContextProvider: headless/control-plane (VPS)
  - ObservedScreenContextProvider: workstation (Beast/Windows)
  - ReportedScreenContextProvider: controller (iPad/iPhone)

UMH substrate subsystem. Instance-agnostic.
"""
from __future__ import annotations

import logging
import os
import socket
import time
from typing import Any

from substrate.operator.operator_presence import PresenceDeviceType
from substrate.operator.screen_awareness import (
    ActiveWindow,
    ApplicationCategory,
    BrowserContext,
    FileContext,
    FocusedApplication,
    RepositoryContext,
    ScreenContextStatus,
    ScreenSnapshot,
    ScreenSourceType,
)

logger = logging.getLogger(__name__)

_STALE_SECONDS = 60
_LOST_SECONDS = 300


def _classify_freshness(timestamp: float, now: float) -> ScreenContextStatus:
    age = now - timestamp
    if age < _STALE_SECONDS:
        return ScreenContextStatus.ACTIVE
    if age < _LOST_SECONDS:
        return ScreenContextStatus.STALE
    return ScreenContextStatus.UNKNOWN


class ScreenContextProvider:
    """Abstract contract for screen context providers."""

    provider_id: str = ""
    source_type: ScreenSourceType = ScreenSourceType.INFERRED
    node_id: str = ""
    device_id: str = ""

    def current_snapshot(self) -> ScreenSnapshot:
        return ScreenSnapshot()

    def is_available(self) -> bool:
        return False


class InferredScreenContextProvider(ScreenContextProvider):
    """Derives screen context from substrate state on headless nodes."""

    CONFIDENCE = 0.3

    def __init__(
        self,
        workspace_engine: Any = None,
        topology_engine: Any = None,
        continuity_engine: Any = None,
        node_id: str = "",
        device_id: str = "",
    ) -> None:
        self.provider_id = "inferred"
        self.source_type = ScreenSourceType.INFERRED
        self.node_id = node_id or "umh-vps"
        self.device_id = device_id or "vps"
        self._workspace_engine = workspace_engine
        self._topology_engine = topology_engine
        self._continuity_engine = continuity_engine

    @property
    def workspace_engine(self) -> Any:
        if self._workspace_engine is None:
            try:
                from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine
                self._workspace_engine = WorkspaceObservationEngine()
            except Exception:
                logger.debug("WorkspaceObservationEngine unavailable for inferred provider")
        return self._workspace_engine

    def current_snapshot(self) -> ScreenSnapshot:
        now = time.time()
        app = self._infer_active_application()
        win = self._infer_active_window(app)
        repo = self._infer_repository_context()
        file_ctx = self._infer_file_context(repo)

        has_data = any([app, win, repo, file_ctx])
        status = ScreenContextStatus.ACTIVE if has_data else ScreenContextStatus.UNKNOWN

        return ScreenSnapshot(
            source_type=ScreenSourceType.INFERRED,
            status=status,
            device_type=PresenceDeviceType.VPS,
            device_id=self.device_id,
            source_node_id=self.node_id,
            source_device_id=self.device_id,
            source_device_role="control_plane",
            source_confidence=self.CONFIDENCE,
            active_application=app,
            active_window=win,
            repository_context=repo,
            file_context=file_ctx,
            browser_context=None,
            applications=[app] if app else [],
            generated_at=now,
        )

    def is_available(self) -> bool:
        return True

    def _get_workspace_snapshot(self) -> Any:
        engine = self.workspace_engine
        if engine is None:
            return None
        try:
            return engine.latest()
        except Exception:
            return None

    def _infer_active_application(self) -> FocusedApplication | None:
        ws = self._get_workspace_snapshot()
        if ws is None:
            return None

        if hasattr(ws, "engineering_sessions") and ws.engineering_sessions:
            session = ws.engineering_sessions[0]
            harness = getattr(session, "harness", "")
            if "claude" in harness.lower() or "code" in harness.lower():
                return FocusedApplication(
                    app_name="Claude Code",
                    category=ApplicationCategory.IDE,
                    window_title=getattr(session, "session_id", ""),
                )
            return FocusedApplication(
                app_name=harness or "Engineering Session",
                category=ApplicationCategory.IDE,
            )

        if hasattr(ws, "terminals") and ws.terminals:
            term = ws.terminals[0]
            return FocusedApplication(
                app_name="Terminal",
                category=ApplicationCategory.TERMINAL,
                window_title=getattr(term, "title", "") or getattr(term, "terminal_id", ""),
            )

        return None

    def _infer_active_window(self, app: FocusedApplication | None) -> ActiveWindow | None:
        if app is None:
            return None
        return ActiveWindow(
            title=app.window_title or app.app_name,
            application=app.app_name,
            is_active=True,
        )

    def _infer_repository_context(self) -> RepositoryContext | None:
        ws = self._get_workspace_snapshot()
        if ws is None or not hasattr(ws, "repositories"):
            return None

        repos = ws.repositories
        if not repos:
            return None

        dirty = [r for r in repos if r.get("dirty_files", 0) > 0]
        chosen = dirty[0] if dirty else repos[0]

        return RepositoryContext(
            repo_name=chosen.get("repo_name", ""),
            repo_path=chosen.get("repo_path", ""),
            branch=chosen.get("current_branch", ""),
            head_commit=chosen.get("head_commit", ""),
            dirty_files=chosen.get("dirty_files", 0),
        )

    def _infer_file_context(self, repo: RepositoryContext | None) -> FileContext | None:
        if repo is None:
            return None
        ws = self._get_workspace_snapshot()
        if ws is None:
            return None
        if hasattr(ws, "engineering_sessions") and ws.engineering_sessions:
            session = ws.engineering_sessions[0]
            files_touched = getattr(session, "files_touched", [])
            if files_touched:
                fpath = files_touched[0] if isinstance(files_touched[0], str) else ""
                if fpath:
                    name = os.path.basename(fpath)
                    ext = os.path.splitext(name)[1].lstrip(".")
                    return FileContext(
                        file_path=fpath,
                        file_name=name,
                        repo_name=repo.repo_name,
                        language=ext,
                    )
        return None


class ObservedScreenContextProvider(ScreenContextProvider):
    """Accepts observed screen state from workstation nodes (Beast/Windows)."""

    CONFIDENCE = 0.9

    def __init__(self, node_id: str = "", device_id: str = "") -> None:
        self.provider_id = "observed"
        self.source_type = ScreenSourceType.OBSERVED
        self.node_id = node_id or "umh-windows"
        self.device_id = device_id or "beast"
        self._last_observed: ScreenSnapshot | None = None
        self._observed_at: float = 0.0

    def report_observed(self, snapshot: ScreenSnapshot) -> None:
        snapshot.source_type = ScreenSourceType.OBSERVED
        snapshot.source_confidence = self.CONFIDENCE
        snapshot.source_node_id = snapshot.source_node_id or self.node_id
        snapshot.source_device_id = snapshot.source_device_id or self.device_id
        snapshot.source_device_role = snapshot.source_device_role or "workstation"
        self._last_observed = snapshot
        self._observed_at = time.time()

    def current_snapshot(self) -> ScreenSnapshot:
        if self._last_observed is None:
            return ScreenSnapshot(
                source_type=ScreenSourceType.OBSERVED,
                status=ScreenContextStatus.UNKNOWN,
                source_node_id=self.node_id,
                source_device_id=self.device_id,
                source_device_role="workstation",
                source_confidence=0.0,
            )
        now = time.time()
        freshness = _classify_freshness(self._observed_at, now)
        self._last_observed.status = freshness
        return self._last_observed

    def is_available(self) -> bool:
        if self._last_observed is None:
            return False
        age = time.time() - self._observed_at
        return age < _LOST_SECONDS


class ReportedScreenContextProvider(ScreenContextProvider):
    """Accepts pushed context from controller devices (iPad/iPhone)."""

    CONFIDENCE = 0.6

    def __init__(self, node_id: str = "", device_id: str = "") -> None:
        self.provider_id = "reported"
        self.source_type = ScreenSourceType.REPORTED
        self.node_id = node_id
        self.device_id = device_id
        self._last_reported: ScreenSnapshot | None = None
        self._reported_at: float = 0.0

    def report_context(self, snapshot: ScreenSnapshot) -> None:
        snapshot.source_type = ScreenSourceType.REPORTED
        snapshot.source_confidence = self.CONFIDENCE
        snapshot.source_node_id = snapshot.source_node_id or self.node_id
        snapshot.source_device_id = snapshot.source_device_id or self.device_id
        self._last_reported = snapshot
        self._reported_at = time.time()

    def current_snapshot(self) -> ScreenSnapshot:
        if self._last_reported is None:
            return ScreenSnapshot(
                source_type=ScreenSourceType.REPORTED,
                status=ScreenContextStatus.UNKNOWN,
                source_node_id=self.node_id,
                source_device_id=self.device_id,
                source_confidence=0.0,
            )
        now = time.time()
        freshness = _classify_freshness(self._reported_at, now)
        self._last_reported.status = freshness
        return self._last_reported

    def is_available(self) -> bool:
        if self._last_reported is None:
            return False
        age = time.time() - self._reported_at
        return age < _LOST_SECONDS
