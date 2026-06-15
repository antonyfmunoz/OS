"""Cockpit Meta IDE routes — engineering reality awareness.

Mounted under /api/umh/ via include_router in cockpit.py.
All routes are GET (read-only). No mutations, no execution.

Phase 21. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)

meta_ide_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, meta_ide_router
    _configured = True
    meta_ide_router = _build_router(require_operator_dep)


def _get_engine():
    from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine

    root = os.environ.get("UMH_ROOT", "/opt/OS")
    return MetaIDEWorkspaceEngine(repo_paths=[root])


def _get_roadmap():
    from substrate.meta_ide.roadmap_intelligence import RoadmapIntelligence

    root = os.environ.get("UMH_ROOT", "/opt/OS")
    return RoadmapIntelligence(root_path=root)


def _repo_snap_to_dict(snap: Any) -> dict[str, Any]:
    return {
        "repo_name": snap.repo_name,
        "repo_path": snap.repo_path,
        "current_branch": snap.current_branch,
        "head_commit": snap.head_commit,
        "head_commit_message": snap.head_commit_message,
        "head_commit_timestamp": snap.head_commit_timestamp,
        "dirty_files": snap.dirty_files,
        "staged_files": snap.staged_files,
        "worktree_count": snap.worktree_count,
        "health": {
            "status": snap.health.status.value,
            "dirty_file_count": snap.health.dirty_file_count,
            "stale_branch_count": snap.health.stale_branch_count,
            "detached_worktrees": snap.health.detached_worktrees,
            "issues": snap.health.issues,
        },
        "branches": [
            {
                "name": b.branch_name,
                "last_commit": b.last_commit_hash,
                "message": b.last_commit_message,
                "timestamp": b.last_commit_timestamp,
                "ahead": b.ahead_count,
                "behind": b.behind_count,
                "is_current": b.is_current,
            }
            for b in snap.branches
        ],
        "worktrees": [
            {
                "path": w.path,
                "branch": w.branch,
                "commit": w.commit_hash,
                "locked": w.is_locked,
                "detached": w.is_detached,
            }
            for w in snap.worktrees
        ],
        "snapshot_at": snap.snapshot_at,
    }


def _phase_to_dict(p: Any) -> dict[str, Any]:
    return {
        "phase_number": p.phase_number,
        "phase_name": p.phase_name,
        "state": p.state.value,
        "completed_at": p.completed_at,
        "description": p.description,
        "key_files": p.key_files,
        "blockers": p.blockers,
    }


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/meta-ide/repositories", dependencies=auth)
    async def _repositories() -> dict[str, Any]:
        engine = _get_engine()
        summary = engine.workspace_summary()
        return {
            "repositories": [_repo_snap_to_dict(s) for s in summary.repositories],
            "generated_at": summary.generated_at,
        }

    @r.get("/meta-ide/workspace", dependencies=auth)
    async def _workspace() -> dict[str, Any]:
        engine = _get_engine()
        return engine.engineering_summary()

    @r.get("/meta-ide/roadmap", dependencies=auth)
    async def _roadmap() -> dict[str, Any]:
        ri = _get_roadmap()
        status = ri.status()
        return {
            "current_phase": _phase_to_dict(status.current_phase) if status.current_phase else None,
            "completed_phases": [_phase_to_dict(p) for p in status.completed_phases],
            "planned_phases": [_phase_to_dict(p) for p in status.planned_phases],
            "blocked_phases": [_phase_to_dict(p) for p in status.blocked_phases],
            "total_phases": status.total_phases,
            "completion_ratio": status.completion_ratio,
            "sources_checked": status.sources_checked,
            "generated_at": status.generated_at,
        }

    def _validate_repo_path(engine: Any, repo_path: str) -> str | None:
        if not repo_path:
            return None
        allowed = {os.path.realpath(p) for p in engine._repo_paths}
        target = os.path.realpath(repo_path)
        if target not in allowed:
            raise HTTPException(
                status_code=403,
                detail="repo_path not in configured repositories",
            )
        return target

    @r.get("/meta-ide/worktrees", dependencies=auth)
    async def _worktrees(
        repo_path: str = Query("", description="Repository path"),
    ) -> dict[str, Any]:
        engine = _get_engine()
        validated = _validate_repo_path(engine, repo_path)
        wts = engine.worktree_summary(repo_path=validated)
        return {"worktrees": wts}

    @r.get("/meta-ide/branches", dependencies=auth)
    async def _branches(
        repo_path: str = Query("", description="Repository path"),
    ) -> dict[str, Any]:
        engine = _get_engine()
        validated = _validate_repo_path(engine, repo_path)
        branches = engine.branch_summary(repo_path=validated)
        return {"branches": branches}

    @r.get("/meta-ide/risks", dependencies=auth)
    async def _risks() -> dict[str, Any]:
        engine = _get_engine()
        summary = engine.workspace_summary()
        return {
            "risks": [
                {
                    "id": r.risk_id,
                    "level": r.level.value,
                    "category": r.category,
                    "description": r.description,
                    "repo_path": r.repo_path,
                }
                for r in summary.risks
            ],
            "overall_risk": summary.overall_risk.value,
        }

    return r
