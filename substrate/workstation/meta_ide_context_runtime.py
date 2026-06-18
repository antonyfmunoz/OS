"""Meta IDE Context Runtime — read-only context binding for the build surface.

Answers: "What does UMH know about the current Meta IDE working context?"

When Meta IDE is open, resolves: device, repo, branch, directory, files,
projection, build target, related docs/decisions/goals. This is the
"system already knows" layer for the build surface.

Does NOT replace existing Meta IDE loop routes. This is read-only
context binding only — no submit/advance/review/merge.

Campaign 17.1. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class MetaIdeContextSnapshot:
    device: str = ""
    repo: str = ""
    branch: str = ""
    directory: str = ""
    active_files: list[str] = field(default_factory=list)
    projection: str = ""
    build_target: str = ""
    related_docs: list[dict[str, Any]] = field(default_factory=list)
    related_decisions: list[dict[str, Any]] = field(default_factory=list)
    related_goals: list[dict[str, Any]] = field(default_factory=list)
    active_requests: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "repo": self.repo,
            "branch": self.branch,
            "directory": self.directory,
            "active_files": self.active_files,
            "projection": self.projection,
            "build_target": self.build_target,
            "related_docs": self.related_docs,
            "related_decisions": self.related_decisions,
            "related_goals": self.related_goals,
            "active_requests": self.active_requests,
            "constraints": self.constraints,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────


class MetaIdeContextRuntime:
    """Read-only context binding for Meta IDE.

    Composes 5 subsystems:
    - ContextResolutionEngine: natural language → resolved context
    - WorkspaceAwarenessRuntime: active workspace/repo/branch
    - DeviceAwarenessRuntime: active device
    - MetaIDEProjectionLoopRuntime: active build requests
    - OrchestratorAwarenessRuntime: full orchestrator context

    No mutation. No build submission. Read-only context.
    """

    def __init__(
        self,
        context_resolution: Any | None = None,
        workspace_awareness: Any | None = None,
        device_awareness: Any | None = None,
        meta_ide_loop: Any | None = None,
        orchestrator_awareness: Any | None = None,
    ) -> None:
        self._context_resolution_dep = context_resolution
        self._workspace_awareness_dep = workspace_awareness
        self._device_awareness_dep = device_awareness
        self._meta_ide_loop_dep = meta_ide_loop
        self._orchestrator_awareness_dep = orchestrator_awareness

    # ── Lazy subsystem access ───────────────────────────────────────

    @property
    def _context_resolution(self) -> Any | None:
        if self._context_resolution_dep is not None:
            return self._context_resolution_dep
        try:
            from substrate.organism.context_resolution import (
                ContextResolutionEngine,
            )

            self._context_resolution_dep = ContextResolutionEngine()
        except Exception as exc:
            logger.debug("meta_ide_ctx: context_resolution init failed: %s", exc)
        return self._context_resolution_dep

    @property
    def _workspace_awareness(self) -> Any | None:
        if self._workspace_awareness_dep is not None:
            return self._workspace_awareness_dep
        try:
            from substrate.organism.workspace_awareness import (
                WorkspaceAwarenessRuntime,
            )

            self._workspace_awareness_dep = WorkspaceAwarenessRuntime()
        except Exception as exc:
            logger.debug("meta_ide_ctx: workspace_awareness init failed: %s", exc)
        return self._workspace_awareness_dep

    @property
    def _device_awareness(self) -> Any | None:
        if self._device_awareness_dep is not None:
            return self._device_awareness_dep
        try:
            from substrate.organism.device_awareness import (
                DeviceAwarenessRuntime,
            )

            self._device_awareness_dep = DeviceAwarenessRuntime()
        except Exception as exc:
            logger.debug("meta_ide_ctx: device_awareness init failed: %s", exc)
        return self._device_awareness_dep

    @property
    def _meta_ide_loop(self) -> Any | None:
        if self._meta_ide_loop_dep is not None:
            return self._meta_ide_loop_dep
        try:
            from substrate.workstation.meta_ide_projection_loop_runtime import (
                MetaIDEProjectionLoopRuntime,
            )

            self._meta_ide_loop_dep = MetaIDEProjectionLoopRuntime()
        except Exception as exc:
            logger.debug("meta_ide_ctx: meta_ide_loop init failed: %s", exc)
        return self._meta_ide_loop_dep

    @property
    def _orchestrator_awareness(self) -> Any | None:
        if self._orchestrator_awareness_dep is not None:
            return self._orchestrator_awareness_dep
        try:
            from substrate.organism.orchestrator_awareness_runtime import (
                OrchestratorAwarenessRuntime,
            )

            self._orchestrator_awareness_dep = OrchestratorAwarenessRuntime()
        except Exception as exc:
            logger.debug("meta_ide_ctx: orchestrator_awareness init failed: %s", exc)
        return self._orchestrator_awareness_dep

    # ── Data extraction helpers ─────────────────────────────────────

    def _get_device(self) -> str:
        try:
            if self._device_awareness is not None:
                return self._device_awareness.detect_active_device()
        except Exception as exc:
            logger.debug("meta_ide_ctx: device failed: %s", exc)
        return ""

    def _get_workspace(self) -> dict[str, Any]:
        try:
            if self._workspace_awareness is not None:
                snap = self._workspace_awareness.snapshot()
                return snap if isinstance(snap, dict) else {}
        except Exception as exc:
            logger.debug("meta_ide_ctx: workspace failed: %s", exc)
        return {}

    def _get_orchestrator_context(self) -> dict[str, Any]:
        try:
            if self._orchestrator_awareness is not None:
                ctx = self._orchestrator_awareness.context()
                if hasattr(ctx, "to_dict"):
                    return ctx.to_dict()
                return ctx if isinstance(ctx, dict) else {}
        except Exception as exc:
            logger.debug("meta_ide_ctx: orchestrator_context failed: %s", exc)
        return {}

    def _get_active_requests(self) -> list[dict[str, Any]]:
        try:
            if self._meta_ide_loop is not None:
                requests = self._meta_ide_loop.active_requests()
                result: list[dict[str, Any]] = []
                for r in requests[:10]:
                    if hasattr(r, "to_dict"):
                        result.append(r.to_dict())
                    elif isinstance(r, dict):
                        result.append(r)
                return result
        except Exception as exc:
            logger.debug("meta_ide_ctx: active_requests failed: %s", exc)
        return []

    def _resolve_context(self, text: str) -> dict[str, Any]:
        try:
            if self._context_resolution is not None:
                resolved = self._context_resolution.resolve(text)
                if hasattr(resolved, "to_dict"):
                    return resolved.to_dict()
        except Exception as exc:
            logger.debug("meta_ide_ctx: resolve failed: %s", exc)
        return {}

    # ── Public API ──────────────────────────────────────────────────

    def context(self) -> MetaIdeContextSnapshot:
        workspace = self._get_workspace()
        orch_ctx = self._get_orchestrator_context()
        active_reqs = self._get_active_requests()

        return MetaIdeContextSnapshot(
            device=self._get_device(),
            repo=orch_ctx.get("active_repo", workspace.get("repo", "")),
            branch=workspace.get("branch", ""),
            directory=orch_ctx.get("active_directory", workspace.get("directory", "")),
            active_files=orch_ctx.get("active_files", []),
            projection=orch_ctx.get("active_projection", ""),
            build_target=workspace.get("build_target", ""),
            related_docs=orch_ctx.get("documents", [])[:10],
            related_decisions=orch_ctx.get("decisions", [])[:10],
            related_goals=orch_ctx.get("goals", [])[:10] if "goals" in orch_ctx else [],
            active_requests=active_reqs,
            constraints=orch_ctx.get("constraints", [])[:10] if "constraints" in orch_ctx else [],
            generated_at=time.time(),
        )

    def active_files(self) -> list[str]:
        try:
            ctx = self._get_orchestrator_context()
            return ctx.get("active_files", [])
        except Exception as exc:
            logger.debug("meta_ide_ctx: active_files failed: %s", exc)
        return []

    def resolve_intent(self, text: str) -> dict[str, Any]:
        """Resolve work intent text in the current Meta IDE context."""
        resolved = self._resolve_context(text)
        workspace = self._get_workspace()
        resolved["meta_ide_workspace"] = workspace
        resolved["active_requests"] = self._get_active_requests()
        return resolved

    def snapshot(self) -> MetaIdeContextSnapshot:
        return self.context()

    def summary(self) -> dict[str, Any]:
        ctx = self.context()
        return {
            "device": ctx.device,
            "repo": ctx.repo,
            "branch": ctx.branch,
            "projection": ctx.projection,
            "active_file_count": len(ctx.active_files),
            "related_doc_count": len(ctx.related_docs),
            "related_goal_count": len(ctx.related_goals),
            "active_request_count": len(ctx.active_requests),
        }
