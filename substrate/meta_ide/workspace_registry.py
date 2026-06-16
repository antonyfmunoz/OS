"""Workspace Registry — single source of truth for workspace topology.

Maintains canonical workspace definitions: which repositories, runtimes,
build targets, and devices compose each engineering workspace.
Loads seed data from infra/workspace_registry.json — no projection names
in substrate code.

Phase 27. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from substrate.meta_ide.workspace_runtime_graph import (
    WorkspaceBuildTarget,
    WorkspaceDefinition,
    WorkspaceRepository,
    WorkspaceRuntime,
    WorkspaceType,
)

logger = logging.getLogger(__name__)


def _find_registry_path() -> str:
    """Locate workspace_registry.json, checking UMH_ROOT and file-relative."""
    root = os.environ.get("UMH_ROOT", "/opt/OS")
    candidate = os.path.join(root, "infra", "workspace_registry.json")
    if os.path.exists(candidate):
        return candidate
    # Fallback: relative to this file (substrate/meta_ide/ → ../../infra/)
    here = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.normpath(os.path.join(here, "..", "..", "infra", "workspace_registry.json"))
    return fallback


def _load_seed_workspaces() -> list[WorkspaceDefinition]:
    """Load workspace definitions from infra/workspace_registry.json."""
    root = os.environ.get("UMH_ROOT", "/opt/OS")
    registry_path = _find_registry_path()
    try:
        with open(registry_path) as f:
            entries = json.load(f)
    except Exception:
        logger.debug("Could not load workspace registry from %s", registry_path)
        return []

    workspaces: list[WorkspaceDefinition] = []
    for entry in entries:
        ws_id = entry.get("workspace_id", "")
        if not ws_id:
            continue

        repos = [
            WorkspaceRepository(
                repository_id=r.get("repository_id", ""),
                name=r.get("name", ""),
                path=r.get("path", "") or "",
                branch=r.get("branch", "main"),
                workspace_id=ws_id,
            )
            for r in entry.get("repositories", [])
        ]

        # UMH core workspace gets repo path from UMH_ROOT
        if ws_id == "umh":
            for repo in repos:
                if not repo.path:
                    repo.path = root

        runtimes = [
            WorkspaceRuntime(
                runtime_id=r.get("runtime_id", ""),
                workspace_id=ws_id,
                runtime_type=r.get("runtime_type", ""),
                host_device_id=r.get("host_device_id", ""),
                ports=r.get("ports", []),
            )
            for r in entry.get("runtimes", [])
        ]

        build_targets = [
            WorkspaceBuildTarget(
                target_id=b.get("target_id", ""),
                workspace_id=ws_id,
                build_type=b.get("build_type", ""),
                device_id=b.get("device_id", ""),
                preferred=b.get("preferred", False),
            )
            for b in entry.get("build_targets", [])
        ]

        wtype_str = entry.get("workspace_type", "core")
        try:
            wtype = WorkspaceType(wtype_str)
        except ValueError:
            wtype = WorkspaceType.CORE

        workspaces.append(
            WorkspaceDefinition(
                workspace_id=ws_id,
                name=entry.get("name", ws_id),
                workspace_type=wtype,
                repositories=repos,
                runtimes=runtimes,
                build_targets=build_targets,
                device_ids=entry.get("device_ids", []),
            )
        )

    return workspaces


class WorkspaceRegistry:
    """Single source of truth for workspace topology definitions."""

    def __init__(self, seed: bool = True) -> None:
        self._workspaces: dict[str, WorkspaceDefinition] = {}
        if seed:
            for ws in _load_seed_workspaces():
                self._workspaces[ws.workspace_id] = ws

    def get(self, workspace_id: str) -> WorkspaceDefinition | None:
        return self._workspaces.get(workspace_id)

    def list_workspaces(self) -> list[WorkspaceDefinition]:
        return list(self._workspaces.values())

    def workspace_for_repository(self, repo_path: str) -> WorkspaceDefinition | None:
        for ws in self._workspaces.values():
            for repo in ws.repositories:
                if repo.path and repo.path == repo_path:
                    return ws
        return None

    def workspace_for_device(self, device_id: str) -> list[WorkspaceDefinition]:
        return [ws for ws in self._workspaces.values() if device_id in ws.device_ids]

    def register(self, definition: WorkspaceDefinition) -> None:
        self._workspaces[definition.workspace_id] = definition
        logger.info(
            "workspace registered: %s (%s)",
            definition.workspace_id,
            definition.name,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_count": len(self._workspaces),
            "workspaces": {wid: ws.to_dict() for wid, ws in self._workspaces.items()},
        }
