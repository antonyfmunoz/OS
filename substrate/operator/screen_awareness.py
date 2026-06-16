"""UMH Screen Awareness — types for operator visual workspace context.

Phase 33. Models the operator's visual reality across a distributed organism.
Three source modes: INFERRED (VPS/headless), OBSERVED (Beast/workstation),
REPORTED (iPad/iPhone/controller).

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from substrate.operator.operator_presence import PresenceDeviceType


class ScreenSourceType(str, Enum):
    """How visual context was obtained."""

    INFERRED = "inferred"
    REPORTED = "reported"
    OBSERVED = "observed"


class ScreenContextStatus(str, Enum):
    """Freshness of screen context."""

    ACTIVE = "active"
    STALE = "stale"
    UNKNOWN = "unknown"


class ApplicationCategory(str, Enum):
    """Category of the active application."""

    IDE = "ide"
    TERMINAL = "terminal"
    BROWSER = "browser"
    COMMUNICATION = "communication"
    DESIGN = "design"
    OTHER = "other"


@dataclass
class FocusedApplication:
    """Application the operator is currently using."""

    app_name: str
    category: ApplicationCategory = ApplicationCategory.OTHER
    pid: int = 0
    window_title: str = ""
    is_focused: bool = True
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_name": self.app_name,
            "category": self.category.value,
            "pid": self.pid,
            "window_title": self.window_title,
            "is_focused": self.is_focused,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FocusedApplication:
        cat = data.get("category", "other")
        return cls(
            app_name=data.get("app_name", ""),
            category=ApplicationCategory(cat) if cat else ApplicationCategory.OTHER,
            pid=data.get("pid", 0),
            window_title=data.get("window_title", ""),
            is_focused=data.get("is_focused", True),
            detected_at=data.get("detected_at", time.time()),
        )


@dataclass
class ActiveWindow:
    """Window-level detail for the active workspace."""

    window_id: str = field(default_factory=lambda: f"win-{uuid4().hex[:8]}")
    title: str = ""
    application: str = ""
    is_active: bool = True
    workspace_id: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "title": self.title,
            "application": self.application,
            "is_active": self.is_active,
            "workspace_id": self.workspace_id,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActiveWindow:
        return cls(
            window_id=data.get("window_id", f"win-{uuid4().hex[:8]}"),
            title=data.get("title", ""),
            application=data.get("application", ""),
            is_active=data.get("is_active", True),
            workspace_id=data.get("workspace_id", ""),
            detected_at=data.get("detected_at", time.time()),
        )


@dataclass
class RepositoryContext:
    """Which repository the operator is working in."""

    repo_name: str
    repo_path: str
    workspace_id: str = ""
    branch: str = ""
    head_commit: str = ""
    dirty_files: int = 0
    active_file: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "workspace_id": self.workspace_id,
            "branch": self.branch,
            "head_commit": self.head_commit,
            "dirty_files": self.dirty_files,
            "active_file": self.active_file,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepositoryContext:
        return cls(
            repo_name=data.get("repo_name", ""),
            repo_path=data.get("repo_path", ""),
            workspace_id=data.get("workspace_id", ""),
            branch=data.get("branch", ""),
            head_commit=data.get("head_commit", ""),
            dirty_files=data.get("dirty_files", 0),
            active_file=data.get("active_file", ""),
            detected_at=data.get("detected_at", time.time()),
        )


@dataclass
class FileContext:
    """Which file the operator is currently editing."""

    file_path: str
    file_name: str
    repo_name: str = ""
    language: str = ""
    line_number: int = 0
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "repo_name": self.repo_name,
            "language": self.language,
            "line_number": self.line_number,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileContext:
        return cls(
            file_path=data.get("file_path", ""),
            file_name=data.get("file_name", ""),
            repo_name=data.get("repo_name", ""),
            language=data.get("language", ""),
            line_number=data.get("line_number", 0),
            detected_at=data.get("detected_at", time.time()),
        )


@dataclass
class BrowserContext:
    """Browser tab the operator is viewing."""

    url: str = ""
    title: str = ""
    domain: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "domain": self.domain,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrowserContext:
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            domain=data.get("domain", ""),
            detected_at=data.get("detected_at", time.time()),
        )


@dataclass
class ScreenSnapshot:
    """Complete visual workspace context from any source."""

    source_type: ScreenSourceType = ScreenSourceType.INFERRED
    status: ScreenContextStatus = ScreenContextStatus.UNKNOWN
    device_type: PresenceDeviceType = PresenceDeviceType.UNKNOWN
    device_id: str = ""
    source_node_id: str = ""
    source_device_id: str = ""
    source_device_role: str = ""
    source_confidence: float = 0.0
    active_application: FocusedApplication | None = None
    active_window: ActiveWindow | None = None
    repository_context: RepositoryContext | None = None
    file_context: FileContext | None = None
    browser_context: BrowserContext | None = None
    applications: list[FocusedApplication] = field(default_factory=list)
    workstation_detail: dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "status": self.status.value,
            "device_type": self.device_type.value
            if isinstance(self.device_type, Enum)
            else self.device_type,
            "device_id": self.device_id,
            "source_node_id": self.source_node_id,
            "source_device_id": self.source_device_id,
            "source_device_role": self.source_device_role,
            "source_confidence": self.source_confidence,
            "active_application": self.active_application.to_dict()
            if self.active_application
            else None,
            "active_window": self.active_window.to_dict() if self.active_window else None,
            "repository_context": self.repository_context.to_dict()
            if self.repository_context
            else None,
            "file_context": self.file_context.to_dict() if self.file_context else None,
            "browser_context": self.browser_context.to_dict() if self.browser_context else None,
            "applications": [a.to_dict() for a in self.applications],
            "workstation_detail": self.workstation_detail,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScreenSnapshot:
        src = data.get("source_type", "inferred")
        st = data.get("status", "unknown")
        dt = data.get("device_type", "unknown")

        app_data = data.get("active_application")
        win_data = data.get("active_window")
        repo_data = data.get("repository_context")
        file_data = data.get("file_context")
        browser_data = data.get("browser_context")
        apps_data = data.get("applications", [])

        return cls(
            source_type=ScreenSourceType(src) if src else ScreenSourceType.INFERRED,
            status=ScreenContextStatus(st) if st else ScreenContextStatus.UNKNOWN,
            device_type=PresenceDeviceType(dt) if dt else PresenceDeviceType.UNKNOWN,
            device_id=data.get("device_id", ""),
            source_node_id=data.get("source_node_id", ""),
            source_device_id=data.get("source_device_id", ""),
            source_device_role=data.get("source_device_role", ""),
            source_confidence=data.get("source_confidence", 0.0),
            active_application=FocusedApplication.from_dict(app_data) if app_data else None,
            active_window=ActiveWindow.from_dict(win_data) if win_data else None,
            repository_context=RepositoryContext.from_dict(repo_data) if repo_data else None,
            file_context=FileContext.from_dict(file_data) if file_data else None,
            browser_context=BrowserContext.from_dict(browser_data) if browser_data else None,
            applications=[FocusedApplication.from_dict(a) for a in apps_data] if apps_data else [],
            workstation_detail=data.get("workstation_detail", {}),
            generated_at=data.get("generated_at", time.time()),
        )
