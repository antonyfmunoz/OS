"""Workspace Observation — live engineering runtime observation.

Pure data models + composition engine. Observes active terminals,
containers, previews, and engineering sessions. No subprocess calls.
No transport imports. No execution authority.

Phase 25. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ObservationDomain(str, Enum):
    TERMINAL = "terminal"
    CONTAINER = "container"
    PREVIEW = "preview"
    REPOSITORY = "repository"
    ENGINEERING_SESSION = "engineering_session"


class ProcessHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRASHED = "crashed"
    UNKNOWN = "unknown"


@dataclass
class TerminalObservation:
    terminal_id: str
    host_id: str = ""
    session_name: str = ""
    window_name: str = ""
    pane_index: int = 0
    current_command: str = ""
    cwd: str = ""
    pid: int = 0
    is_active: bool = False
    last_output_at: float = 0.0
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "terminal_id": self.terminal_id,
            "host_id": self.host_id,
            "session_name": self.session_name,
            "window_name": self.window_name,
            "pane_index": self.pane_index,
            "current_command": self.current_command,
            "cwd": self.cwd,
            "pid": self.pid,
            "is_active": self.is_active,
            "last_output_at": self.last_output_at,
            "observed_at": self.observed_at,
        }


@dataclass
class ContainerObservation:
    container_id: str
    container_name: str = ""
    image: str = ""
    status: str = ""
    health: ProcessHealth = ProcessHealth.UNKNOWN
    ports: list[str] = field(default_factory=list)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    restart_count: int = 0
    started_at: float = 0.0
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "container_id": self.container_id,
            "container_name": self.container_name,
            "image": self.image,
            "status": self.status,
            "health": self.health.value if isinstance(self.health, ProcessHealth) else self.health,
            "ports": self.ports,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "restart_count": self.restart_count,
            "started_at": self.started_at,
            "observed_at": self.observed_at,
        }


@dataclass
class PreviewObservation:
    preview_id: str
    name: str = ""
    port: int = 0
    protocol: str = "http"
    url: str = ""
    pid: int = 0
    process_name: str = ""
    health: ProcessHealth = ProcessHealth.UNKNOWN
    restart_count: int = 0
    started_at: float = 0.0
    last_checked_at: float = 0.0
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preview_id": self.preview_id,
            "name": self.name,
            "port": self.port,
            "protocol": self.protocol,
            "url": self.url or f"{self.protocol}://localhost:{self.port}",
            "pid": self.pid,
            "process_name": self.process_name,
            "health": self.health.value if isinstance(self.health, ProcessHealth) else self.health,
            "restart_count": self.restart_count,
            "started_at": self.started_at,
            "last_checked_at": self.last_checked_at,
            "observed_at": self.observed_at,
        }


@dataclass
class EngineeringSessionObservation:
    session_id: str
    harness: str = ""
    status: str = ""
    duration_seconds: float = 0.0
    events_count: int = 0
    decisions_count: int = 0
    files_touched: int = 0
    coherence_issues: int = 0
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "harness": self.harness,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "events_count": self.events_count,
            "decisions_count": self.decisions_count,
            "files_touched": self.files_touched,
            "coherence_issues": self.coherence_issues,
            "observed_at": self.observed_at,
        }


@dataclass
class WorkspaceObservationSnapshot:
    snapshot_id: str = field(default_factory=lambda: f"wobs-{uuid4().hex[:12]}")
    terminals: list[TerminalObservation] = field(default_factory=list)
    containers: list[ContainerObservation] = field(default_factory=list)
    previews: list[PreviewObservation] = field(default_factory=list)
    engineering_sessions: list[EngineeringSessionObservation] = field(default_factory=list)
    repositories: list[dict[str, Any]] = field(default_factory=list)
    observed_at: float = field(default_factory=time.time)
    host_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "terminals": [t.to_dict() for t in self.terminals],
            "containers": [c.to_dict() for c in self.containers],
            "previews": [p.to_dict() for p in self.previews],
            "engineering_sessions": [e.to_dict() for e in self.engineering_sessions],
            "repositories": self.repositories,
            "observed_at": self.observed_at,
            "host_id": self.host_id,
            "metadata": self.metadata,
            "summary": {
                "terminal_count": len(self.terminals),
                "container_count": len(self.containers),
                "preview_count": len(self.previews),
                "engineering_session_count": len(self.engineering_sessions),
                "repository_count": len(self.repositories),
            },
        }


def _safe_parse(raw: dict[str, Any], cls: type) -> Any:
    known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    filtered = {k: v for k, v in raw.items() if k in known}
    return cls(**filtered)


class WorkspaceObservationEngine:
    """Composes probe data + existing subsystems into unified observation.

    Pure composition. No subprocess calls. Takes probe output as input.
    """

    def __init__(
        self,
        repo_paths: list[str] | None = None,
        event_spine: Any = None,
    ) -> None:
        self._repo_paths = repo_paths or [os.environ.get("UMH_ROOT", "/opt/OS")]
        self._event_spine = event_spine
        self._snapshots: deque[WorkspaceObservationSnapshot] = deque(maxlen=100)

    def observe(
        self,
        terminal_data: list[dict[str, Any]] | None = None,
        container_data: list[dict[str, Any]] | None = None,
        preview_data: list[dict[str, Any]] | None = None,
    ) -> WorkspaceObservationSnapshot:
        terminals = [_safe_parse(t, TerminalObservation) for t in (terminal_data or [])]
        containers = [_safe_parse(c, ContainerObservation) for c in (container_data or [])]
        previews = [_safe_parse(p, PreviewObservation) for p in (preview_data or [])]
        eng_sessions = self._observe_engineering_sessions()
        repo_snaps = self._observe_repositories()

        snap = WorkspaceObservationSnapshot(
            terminals=terminals,
            containers=containers,
            previews=previews,
            engineering_sessions=eng_sessions,
            repositories=repo_snaps,
        )
        self._snapshots.append(snap)
        self._emit_to_spine(snap)
        return snap

    def latest(self) -> WorkspaceObservationSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def history(self, limit: int = 20) -> list[WorkspaceObservationSnapshot]:
        items = list(self._snapshots)
        return items[-limit:] if limit else items

    def _observe_engineering_sessions(self) -> list[EngineeringSessionObservation]:
        root = os.environ.get("UMH_ROOT", "/opt/OS")
        active_path = os.path.join(root, "data", "umh", "sessions", "active_sessions.jsonl")
        sessions: list[EngineeringSessionObservation] = []
        try:
            if not os.path.exists(active_path):
                return sessions
            with open(active_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        sessions.append(
                            EngineeringSessionObservation(
                                session_id=record.get("session_id", ""),
                                harness=record.get("harness", ""),
                                status=record.get("status", "active"),
                                duration_seconds=record.get("duration_seconds", 0.0),
                                events_count=record.get("events_count", 0),
                                decisions_count=record.get("decisions_count", 0),
                                files_touched=record.get("files_touched", 0),
                                coherence_issues=record.get("coherence_issues", 0),
                            )
                        )
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as exc:
            logger.debug("Failed to read engineering sessions: %s", exc)
        return sessions

    def _observe_repositories(self) -> list[dict[str, Any]]:
        try:
            from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine

            engine = MetaIDEWorkspaceEngine(repo_paths=self._repo_paths)
            summary = engine.workspace_summary()
            return [
                {
                    "repo_name": r.repo_name,
                    "repo_path": r.repo_path,
                    "current_branch": r.current_branch,
                    "head_commit": r.head_commit,
                    "dirty_files": len(r.dirty_files),
                    "staged_files": len(r.staged_files),
                    "branch_count": len(r.branches),
                    "worktree_count": r.worktree_count,
                    "health_status": r.health.status.value
                    if hasattr(r.health.status, "value")
                    else str(r.health.status),
                }
                for r in summary.repositories
            ]
        except Exception as exc:
            logger.debug("Failed to observe repositories: %s", exc)
            return []

    def _emit_to_spine(self, snap: WorkspaceObservationSnapshot) -> None:
        if self._event_spine is None:
            return
        try:
            from substrate.organism.event_spine import EventDomain

            self._event_spine.emit(
                domain=EventDomain.RUNTIME,
                event_type="workspace_observation",
                source="workspace_observation_engine",
                data={
                    "snapshot_id": snap.snapshot_id,
                    "terminal_count": len(snap.terminals),
                    "container_count": len(snap.containers),
                    "preview_count": len(snap.previews),
                    "engineering_session_count": len(snap.engineering_sessions),
                    "repository_count": len(snap.repositories),
                },
            )
        except Exception as exc:
            logger.debug("Failed to emit workspace observation event: %s", exc)
