"""Visual Context Runtime — Campaign 21.2.

Converts screen state into operational context. The 'continue this work'
resolver: screen → app → repo → branch → file → work packet → goals →
decisions. Deterministic waterfall — each step deepens the binding if
data is available.

Composes:
  - ScreenAwarenessRuntime (C21.0)
  - MetaIdeContextRuntime (C17.1)
  - WorkspaceAwarenessRuntime (organism)

C21 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class ContextBindingDepth(str, Enum):
    """How deeply the visual context was resolved."""

    SCREEN = "screen"
    APPLICATION = "application"
    REPOSITORY = "repository"
    FILE = "file"
    WORK = "work"


_DEPTH_ORDER = [
    ContextBindingDepth.SCREEN,
    ContextBindingDepth.APPLICATION,
    ContextBindingDepth.REPOSITORY,
    ContextBindingDepth.FILE,
    ContextBindingDepth.WORK,
]


@dataclass
class ContextBinding:
    """Result of resolving screen state into operational context."""

    depth: str = ContextBindingDepth.SCREEN.value
    screen_summary: str = ""
    application: str = ""
    repository: str = ""
    branch: str = ""
    directory: str = ""
    file_path: str = ""
    work_packet_id: str = ""
    campaign: str = ""
    goals: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    resolved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "screen_summary": self.screen_summary,
            "application": self.application,
            "repository": self.repository,
            "branch": self.branch,
            "directory": self.directory,
            "file_path": self.file_path,
            "work_packet_id": self.work_packet_id,
            "campaign": self.campaign,
            "goals": self.goals,
            "decisions": self.decisions,
            "confidence": self.confidence,
            "resolved_at": self.resolved_at,
        }


@dataclass
class VisualContextSnapshot:
    """Full visual context state."""

    binding: dict[str, Any] = field(default_factory=dict)
    binding_depth: str = ContextBindingDepth.SCREEN.value
    meta_ide_context: dict[str, Any] = field(default_factory=dict)
    screen_source: dict[str, Any] = field(default_factory=dict)
    workspace: dict[str, Any] = field(default_factory=dict)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding": self.binding,
            "binding_depth": self.binding_depth,
            "meta_ide_context": self.meta_ide_context,
            "screen_source": self.screen_source,
            "workspace": self.workspace,
            "generated_at": self.generated_at,
        }


# ── Runtime ───────────────────────────────────────────────────────────────


class VisualContextRuntime:
    """Converts screen state to operational context.

    Deterministic waterfall resolution:
      screen → application → repository → file → work context

    Each step deepens the binding. If a step fails, resolution
    stops at the achieved depth and returns what was resolved.
    """

    def __init__(
        self,
        screen_awareness_runtime: Any | None = None,
        meta_ide_context_runtime: Any | None = None,
        workspace_awareness_runtime: Any | None = None,
    ) -> None:
        self._screen_awareness_runtime = screen_awareness_runtime
        self._meta_ide_context_runtime = meta_ide_context_runtime
        self._workspace_awareness_runtime = workspace_awareness_runtime

    # ── Lazy accessors ─────────────────────────────────────────────

    @property
    def screen_awareness_runtime(self) -> Any | None:
        if self._screen_awareness_runtime is None:
            try:
                from substrate.workstation.screen_awareness_runtime import (
                    ScreenAwarenessRuntime,
                )

                self._screen_awareness_runtime = ScreenAwarenessRuntime()
            except Exception:
                logger.debug("ScreenAwarenessRuntime unavailable")
        return self._screen_awareness_runtime

    @property
    def meta_ide_context_runtime(self) -> Any | None:
        if self._meta_ide_context_runtime is None:
            try:
                from substrate.workstation.meta_ide_context_runtime import (
                    MetaIdeContextRuntime,
                )

                self._meta_ide_context_runtime = MetaIdeContextRuntime()
            except Exception:
                logger.debug("MetaIdeContextRuntime unavailable")
        return self._meta_ide_context_runtime

    @property
    def workspace_awareness_runtime(self) -> Any | None:
        if self._workspace_awareness_runtime is None:
            try:
                from substrate.organism.workspace_awareness import (
                    WorkspaceAwarenessRuntime,
                )

                self._workspace_awareness_runtime = WorkspaceAwarenessRuntime()
            except Exception:
                logger.debug("WorkspaceAwarenessRuntime unavailable")
        return self._workspace_awareness_runtime

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _safe_call(fn: Any, default: Any = None) -> Any:
        try:
            return fn()
        except Exception:
            logger.debug("_safe_call failed for %s", fn)
            return default

    # ── Core resolution ────────────────────────────────────────────

    def resolve_context(self) -> ContextBinding:
        """Deterministic waterfall: screen → app → repo → file → work."""
        binding = ContextBinding(resolved_at=time.time())
        depth_index = 0  # SCREEN

        # Step 1 — Screen
        screen = {}
        if self.screen_awareness_runtime is not None:
            screen = (
                self._safe_call(lambda: self.screen_awareness_runtime.current_screen(), {}) or {}
            )
        if not screen:
            workspace = self._workspace_snapshot()
            if workspace:
                binding.screen_summary = workspace.get("repo", "unknown workspace")
                binding.confidence = 0.2
            return binding

        window_title = self._extract_window_title(screen)
        binding.screen_summary = window_title or "active screen"
        binding.confidence = 0.3
        depth_index = 0  # SCREEN

        # Step 2 — Application
        app_info = screen.get("focused_application") or screen.get("application") or {}
        app_name = ""
        if isinstance(app_info, dict):
            app_name = app_info.get("app_name", "")
        elif isinstance(app_info, str):
            app_name = app_info
        if app_name:
            binding.application = app_name
            binding.confidence = 0.5
            depth_index = 1  # APPLICATION

        # Step 3 — Repository
        repo_info = screen.get("repository_context") or screen.get("repository") or {}
        if isinstance(repo_info, dict) and repo_info.get("repo_name"):
            binding.repository = repo_info.get("repo_name", "")
            binding.branch = repo_info.get("branch", "")
            binding.directory = repo_info.get("working_directory", "")
            binding.confidence = 0.7
            depth_index = 2  # REPOSITORY
        else:
            workspace = self._workspace_snapshot()
            if workspace and workspace.get("repo"):
                binding.repository = workspace.get("repo", "")
                binding.branch = workspace.get("branch", "")
                binding.directory = workspace.get("directory", "")
                binding.confidence = 0.6
                depth_index = 2  # REPOSITORY

        # Step 4 — File
        file_info = screen.get("file_context") or screen.get("file") or {}
        if isinstance(file_info, dict) and file_info.get("file_path"):
            binding.file_path = file_info.get("file_path", "")
            binding.confidence = 0.8
            depth_index = 3  # FILE

        # Step 5 — Work context (goals, decisions, campaign)
        if depth_index >= 2 and self.meta_ide_context_runtime is not None:
            ide_ctx = self._safe_call(lambda: self.meta_ide_context_runtime.context(), None)
            if ide_ctx is not None:
                ctx_dict = (
                    self._safe_call(lambda: ide_ctx.to_dict(), {})
                    if hasattr(ide_ctx, "to_dict")
                    else (ide_ctx if isinstance(ide_ctx, dict) else {})
                )
                if ctx_dict:
                    goals_raw = ctx_dict.get("related_goals", [])
                    decisions_raw = ctx_dict.get("related_decisions", [])
                    binding.goals = self._extract_labels(goals_raw)
                    binding.decisions = self._extract_labels(decisions_raw)
                    if binding.goals or binding.decisions:
                        binding.confidence = 0.9
                        depth_index = 4  # WORK

        binding.campaign = self._infer_campaign(binding.file_path or binding.directory)
        binding.depth = _DEPTH_ORDER[depth_index].value
        return binding

    def binding_depth(self) -> ContextBindingDepth:
        """Return the depth of the current context binding."""
        binding = self.resolve_context()
        return ContextBindingDepth(binding.depth)

    def continue_work(self) -> dict[str, Any]:
        """Resolve what the operator is working on and suggest continuation."""
        binding = self.resolve_context()
        suggestion = self._build_suggestion(binding)
        return {
            "action": "continue",
            "binding": binding.to_dict(),
            "suggestion": suggestion,
        }

    def snapshot(self) -> VisualContextSnapshot:
        """Full visual context state."""
        binding = self.resolve_context()

        meta_ctx: dict[str, Any] = {}
        if self.meta_ide_context_runtime is not None:
            raw = self._safe_call(lambda: self.meta_ide_context_runtime.context(), None)
            if raw is not None:
                meta_ctx = (
                    self._safe_call(lambda: raw.to_dict(), {})
                    if hasattr(raw, "to_dict")
                    else (raw if isinstance(raw, dict) else {})
                )

        screen_src: dict[str, Any] = {}
        if self.screen_awareness_runtime is not None:
            screen_src = (
                self._safe_call(lambda: self.screen_awareness_runtime.current_screen(), {}) or {}
            )

        workspace: dict[str, Any] = self._workspace_snapshot() or {}

        return VisualContextSnapshot(
            binding=binding.to_dict(),
            binding_depth=binding.depth,
            meta_ide_context=meta_ctx,
            screen_source=screen_src,
            workspace=workspace,
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Compact summary of visual context."""
        binding = self.resolve_context()
        return {
            "depth": binding.depth,
            "application": binding.application,
            "repository": binding.repository,
            "branch": binding.branch,
            "file": binding.file_path,
            "campaign": binding.campaign,
            "goal_count": len(binding.goals),
            "decision_count": len(binding.decisions),
            "confidence": binding.confidence,
        }

    # ── Private helpers ────────────────────────────────────────────

    def _workspace_snapshot(self) -> dict[str, Any] | None:
        if self.workspace_awareness_runtime is None:
            return None
        raw = self._safe_call(
            lambda: self.workspace_awareness_runtime.detect_active_workspace(),
            None,
        )
        if raw is None:
            return None
        if hasattr(raw, "to_dict"):
            return self._safe_call(lambda: raw.to_dict(), None)
        if isinstance(raw, dict):
            return raw
        return None

    @staticmethod
    def _extract_window_title(screen: dict[str, Any]) -> str:
        active_window = screen.get("active_window") or {}
        if isinstance(active_window, dict):
            return active_window.get("title", "")
        app = screen.get("focused_application") or {}
        if isinstance(app, dict):
            return app.get("window_title", "")
        return ""

    @staticmethod
    def _extract_labels(items: list[Any]) -> list[str]:
        labels: list[str] = []
        for item in items:
            if isinstance(item, dict):
                label = item.get("title") or item.get("label") or item.get("name", "")
                if label:
                    labels.append(str(label))
            elif isinstance(item, str):
                labels.append(item)
        return labels

    @staticmethod
    def _infer_campaign(path: str) -> str:
        if not path:
            return ""
        parts = path.lower().replace("\\", "/").split("/")
        for part in parts:
            if part.startswith("c") and len(part) >= 2 and part[1:].replace(".", "").isdigit():
                return part.upper()
        return ""

    @staticmethod
    def _build_suggestion(binding: ContextBinding) -> str:
        depth = binding.depth
        if depth == ContextBindingDepth.WORK.value:
            goals_str = ", ".join(binding.goals[:3]) if binding.goals else "no goals found"
            return (
                f"Continue working on {binding.file_path or binding.repository} "
                f"({binding.campaign or 'current campaign'}). "
                f"Related goals: {goals_str}."
            )
        if depth == ContextBindingDepth.FILE.value:
            return f"Continue editing {binding.file_path} in {binding.repository}@{binding.branch}."
        if depth == ContextBindingDepth.REPOSITORY.value:
            return (
                f"Continue working in {binding.repository}@{binding.branch} ({binding.directory})."
            )
        if depth == ContextBindingDepth.APPLICATION.value:
            return f"Currently in {binding.application}. Open a project to bind to work context."
        return "Screen visible but no application context resolved."
