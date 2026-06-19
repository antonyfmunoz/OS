"""Workspace Awareness Runtime — deterministic active-context detection.

Detects what the operator is currently working on — active device,
workspace, directory, repo, branch — without asking.

Reads from RuntimeStateRegistry (live env snapshots) and RealityGraph
(cross-domain entity resolution) to populate OrchestratorContext fields.

Read-only. Never mutates any state.

Campaign 5.1. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import platform
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"


@dataclass
class WorkspaceSnapshot:
    device: str = ""
    workspace: str = ""
    project: str = ""
    projection: str = ""
    repo: str = ""
    branch: str = ""
    directory: str = ""
    active_files: list[str] = field(default_factory=list)
    dirty: bool = False
    detected_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "workspace": self.workspace,
            "project": self.project,
            "projection": self.projection,
            "repo": self.repo,
            "branch": self.branch,
            "directory": self.directory,
            "active_files": self.active_files,
            "dirty": self.dirty,
            "detected_at": self.detected_at,
        }


class WorkspaceAwarenessRuntime:
    """Deterministic workspace detection from live signals."""

    def __init__(
        self,
        reality_graph: Any | None = None,
        runtime_state: Any | None = None,
    ) -> None:
        self._reality_graph = reality_graph
        self._runtime_state = runtime_state
        self._last_snapshot: WorkspaceSnapshot | None = None

    # ── Public API ────────────────────────────────────────────────────

    def detect_active_workspace(self) -> WorkspaceSnapshot:
        now = time.time()
        snap = WorkspaceSnapshot(detected_at=now)

        snap.device = self._detect_device()
        self._fill_from_runtime_state(snap)
        self._resolve_from_graph(snap)

        self._last_snapshot = snap
        return snap

    def populate_context(self, ctx: Any) -> None:
        snap = self.detect_active_workspace()
        if hasattr(ctx, "active_device") and snap.device:
            ctx.active_device = snap.device
        if hasattr(ctx, "active_repo") and snap.repo:
            ctx.active_repo = snap.repo
        if hasattr(ctx, "active_directory") and snap.directory:
            ctx.active_directory = snap.directory
        if hasattr(ctx, "active_files") and snap.active_files:
            ctx.active_files = snap.active_files
        if hasattr(ctx, "active_projection") and snap.projection:
            ctx.active_projection = snap.projection
        if hasattr(ctx, "active_project") and snap.project:
            ctx.active_project = snap.project

    def snapshot(self) -> dict[str, Any]:
        if self._last_snapshot is None:
            self.detect_active_workspace()
        snap = self._last_snapshot
        return snap.to_dict() if snap else {}

    # ── Device Detection ──────────────────────────────────────────────

    def _detect_device(self) -> str:
        device_id = os.environ.get("UMH_DEVICE_ID", "")
        if device_id:
            return device_id

        hostname = platform.node()
        if not hostname:
            return ""

        if self._reality_graph is not None:
            try:
                from substrate.organism.reality_graph import RealityEntityType
                devices = self._reality_graph.find_by_type(RealityEntityType.DEVICE)
                for dev in devices:
                    dev_hostname = dev.properties.get("tailscale_name", "")
                    if dev_hostname and dev_hostname == hostname:
                        return dev.source_id
                    if dev.name and hostname in dev.name:
                        return dev.source_id
            except Exception as exc:
                logger.debug("Device detection from graph failed: %s", exc)

        return hostname

    # ── Runtime State Detection ───────────────────────────────────────

    def _fill_from_runtime_state(self, snap: WorkspaceSnapshot) -> None:
        if self._runtime_state is None:
            snap.directory = os.getcwd()
            return

        rt_snap = None
        if hasattr(self._runtime_state, "snapshot"):
            rt_snap = self._runtime_state.snapshot()
        if rt_snap is None:
            snap.directory = os.getcwd()
            return

        best_repo = self._pick_best_repo(rt_snap)
        if best_repo is not None:
            snap.repo = getattr(best_repo, "repository", "")
            snap.branch = getattr(best_repo, "current_branch", "")
            snap.dirty = getattr(best_repo, "dirty", False)

        best_worktree = self._pick_best_worktree(rt_snap)
        if best_worktree is not None:
            snap.directory = getattr(best_worktree, "path", "")
        elif not snap.directory:
            snap.directory = os.getcwd()

    def _pick_best_repo(self, rt_snap: Any) -> Any:
        repos = getattr(rt_snap, "repositories", ())
        if not repos:
            return None
        cwd = os.getcwd()
        for repo in repos:
            repo_name = getattr(repo, "repository", "")
            if repo_name and repo_name in cwd:
                return repo
        if getattr(repos[0], "dirty", False):
            return repos[0]
        return repos[0]

    def _pick_best_worktree(self, rt_snap: Any) -> Any:
        worktrees = getattr(rt_snap, "worktrees", ())
        if not worktrees:
            return None
        cwd = os.getcwd()
        for wt in worktrees:
            wt_path = getattr(wt, "path", "")
            if wt_path and cwd.startswith(wt_path):
                return wt
        non_bare = [wt for wt in worktrees if not getattr(wt, "is_bare", False)]
        return non_bare[0] if non_bare else worktrees[0]

    # ── Graph Resolution ──────────────────────────────────────────────

    def _resolve_from_graph(self, snap: WorkspaceSnapshot) -> None:
        if self._reality_graph is None:
            return

        try:
            from substrate.organism.reality_graph import (
                RealityEntityType,
                RealityRelationType,
            )
        except ImportError:
            return

        if snap.repo:
            self._resolve_repo_chain(snap)
        elif snap.directory:
            self._resolve_directory_chain(snap)

    def _resolve_repo_chain(self, snap: WorkspaceSnapshot) -> None:
        from substrate.organism.reality_graph import (
            RealityEntityType,
            RealityRelationType,
        )

        repo_entities = self._reality_graph.find_by_name(snap.repo)
        repo_entity = None
        for r in repo_entities:
            if r.entity_type == RealityEntityType.REPOSITORY:
                repo_entity = r
                break

        if repo_entity is None:
            return

        ws_neighbors = self._reality_graph.neighbors(
            repo_entity.entity_id, RealityRelationType.CONTAINS
        )
        for ws in ws_neighbors:
            if ws.entity_type == RealityEntityType.WORKSPACE:
                snap.workspace = ws.source_id or ws.name
                break

        proj_neighbors = self._reality_graph.neighbors(
            repo_entity.entity_id, RealityRelationType.CONTAINS
        )
        for proj in proj_neighbors:
            if proj.entity_type == RealityEntityType.PROJECT:
                snap.project = proj.source_id or proj.name
                proj_props = proj.properties or {}
                snap.projection = proj_props.get("projection", "")
                break

    def _resolve_directory_chain(self, snap: WorkspaceSnapshot) -> None:
        from substrate.organism.reality_graph import (
            RealityEntityType,
            RealityRelationType,
        )

        workspaces = self._reality_graph.find_by_type(RealityEntityType.WORKSPACE)
        for ws in workspaces:
            ws_name = ws.name.lower()
            dir_lower = snap.directory.lower()
            if ws_name in dir_lower:
                snap.workspace = ws.source_id or ws.name
                proj_neighbors = self._reality_graph.neighbors(
                    ws.entity_id, RealityRelationType.CONTAINS
                )
                for proj in proj_neighbors:
                    if proj.entity_type == RealityEntityType.PROJECT:
                        snap.project = proj.source_id or proj.name
                        break
                break
