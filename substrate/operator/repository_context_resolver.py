"""UMH Repository Context Resolver — maps workspace state to repo context.

Phase 33. Composes WorkspaceObservationEngine and WorkspaceTopologyEngine
to produce structured RepositoryContext objects from live workspace state.

UMH substrate subsystem. Instance-agnostic.
"""
from __future__ import annotations

import logging
from typing import Any

from substrate.operator.screen_awareness import RepositoryContext

logger = logging.getLogger(__name__)


class RepositoryContextResolver:
    """Maps workspace/topology data into structured repository context."""

    def __init__(
        self,
        workspace_engine: Any = None,
        topology_engine: Any = None,
    ) -> None:
        self._workspace_engine = workspace_engine
        self._topology_engine = topology_engine

    @property
    def workspace_engine(self) -> Any:
        if self._workspace_engine is None:
            try:
                from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine
                self._workspace_engine = WorkspaceObservationEngine()
            except Exception:
                logger.debug("WorkspaceObservationEngine unavailable for resolver")
        return self._workspace_engine

    @property
    def topology_engine(self) -> Any:
        if self._topology_engine is None:
            try:
                from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine
                self._topology_engine = WorkspaceTopologyEngine()
            except Exception:
                logger.debug("WorkspaceTopologyEngine unavailable for resolver")
        return self._topology_engine

    def resolve(self, repo_path: str) -> RepositoryContext | None:
        """Resolve a filesystem path to full repository context."""
        repos = self._get_observed_repos()
        for repo in repos:
            if repo.get("repo_path", "") == repo_path:
                return self._repo_dict_to_context(repo)
        for repo in repos:
            rp = repo.get("repo_path", "")
            if rp and repo_path.startswith(rp):
                return self._repo_dict_to_context(repo)
        return None

    def resolve_workspace(self, workspace_id: str) -> list[RepositoryContext]:
        """All repositories associated with a workspace."""
        engine = self.topology_engine
        if engine is None:
            return []
        try:
            summary = engine.workspace_summary(workspace_id)
            if summary is None:
                return []
            repos_data = summary.get("repositories", [])
            return [self._repo_dict_to_context(r) for r in repos_data if r]
        except Exception:
            logger.debug("Failed to resolve workspace %s", workspace_id)
            return []

    def active_repositories(self) -> list[RepositoryContext]:
        """Repositories with recent activity (dirty files > 0)."""
        repos = self._get_observed_repos()
        result = []
        for repo in repos:
            if repo.get("dirty_files", 0) > 0:
                result.append(self._repo_dict_to_context(repo))
        return result

    def _get_observed_repos(self) -> list[dict[str, Any]]:
        engine = self.workspace_engine
        if engine is None:
            return []
        try:
            snapshot = engine.latest()
            if snapshot is None:
                return []
            return getattr(snapshot, "repositories", []) or []
        except Exception:
            return []

    @staticmethod
    def _repo_dict_to_context(data: dict[str, Any]) -> RepositoryContext:
        return RepositoryContext(
            repo_name=data.get("repo_name", ""),
            repo_path=data.get("repo_path", ""),
            workspace_id=data.get("workspace_id", ""),
            branch=data.get("current_branch", data.get("branch", "")),
            head_commit=data.get("head_commit", ""),
            dirty_files=data.get("dirty_files", 0),
            active_file=data.get("active_file", ""),
        )
