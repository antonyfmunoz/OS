"""Workspace intelligence — engineering-state awareness.

Composes from RepositoryReader to produce workspace summaries,
engineering risk indicators, and stale-artifact detection.

Read-only. No mutations. No execution.

Phase 21. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.meta_ide.repository_model import (
    RepositoryReader,
    RepositorySnapshot,
)

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EngineeringRisk:
    risk_id: str
    level: RiskLevel
    category: str
    description: str
    repo_path: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkspaceSummary:
    repositories: list[RepositorySnapshot] = field(default_factory=list)
    total_dirty_files: int = 0
    total_staged_files: int = 0
    total_branches: int = 0
    total_worktrees: int = 0
    stale_branches: int = 0
    stale_worktrees: int = 0
    detached_worktrees: int = 0
    risks: list[EngineeringRisk] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.NONE
    generated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class MetaIDEWorkspaceEngine:
    """Read-only engineering workspace awareness engine."""

    def __init__(self, repo_paths: list[str] | None = None) -> None:
        import os
        default_root = os.environ.get("UMH_ROOT", "/opt/OS")
        self._repo_paths = repo_paths or [default_root]
        self._readers: list[RepositoryReader] = [
            RepositoryReader(p) for p in self._repo_paths
        ]

    def workspace_summary(self) -> WorkspaceSummary:
        summary = WorkspaceSummary()
        snapshots: list[RepositorySnapshot] = []

        for reader in self._readers:
            try:
                snap = reader.snapshot()
                snapshots.append(snap)
            except Exception as exc:
                logger.debug("Failed to snapshot repo: %s", exc)

        summary.repositories = snapshots
        summary.total_dirty_files = sum(len(s.dirty_files) for s in snapshots)
        summary.total_staged_files = sum(len(s.staged_files) for s in snapshots)
        summary.total_branches = sum(len(s.branches) for s in snapshots)
        summary.total_worktrees = sum(s.worktree_count for s in snapshots)
        summary.stale_branches = sum(s.health.stale_branch_count for s in snapshots)
        summary.stale_worktrees = sum(s.health.stale_worktree_count for s in snapshots)
        summary.detached_worktrees = sum(s.health.detached_worktrees for s in snapshots)

        risks = self._detect_risks(snapshots)
        summary.risks = risks
        summary.overall_risk = self._aggregate_risk(risks)
        summary.generated_at = time.time()

        return summary

    def repository_summary(self, repo_path: str | None = None) -> RepositorySnapshot | None:
        target = repo_path or (self._repo_paths[0] if self._repo_paths else None)
        if not target:
            return None
        reader = RepositoryReader(target)
        try:
            return reader.snapshot()
        except Exception as exc:
            logger.debug("Failed to snapshot repo %s: %s", target, exc)
            return None

    def branch_summary(self, repo_path: str | None = None) -> list[dict[str, Any]]:
        snap = self.repository_summary(repo_path)
        if not snap:
            return []
        return [
            {
                "name": b.branch_name,
                "last_commit": b.last_commit_hash,
                "last_message": b.last_commit_message,
                "age_hours": round((time.time() - b.last_commit_timestamp) / 3600, 1)
                if b.last_commit_timestamp > 0 else -1,
                "ahead": b.ahead_count,
                "behind": b.behind_count,
                "is_current": b.is_current,
                "stale": (time.time() - b.last_commit_timestamp) > 7 * 24 * 3600
                if b.last_commit_timestamp > 0 else False,
            }
            for b in snap.branches
        ]

    def worktree_summary(self, repo_path: str | None = None) -> list[dict[str, Any]]:
        snap = self.repository_summary(repo_path)
        if not snap:
            return []
        return [
            {
                "path": w.path,
                "branch": w.branch,
                "commit": w.commit_hash,
                "locked": w.is_locked,
                "detached": w.is_detached,
                "bare": w.is_bare,
            }
            for w in snap.worktrees
        ]

    def engineering_summary(self) -> dict[str, Any]:
        ws = self.workspace_summary()
        return {
            "repo_count": len(ws.repositories),
            "repos": [
                {
                    "name": r.repo_name,
                    "path": r.repo_path,
                    "branch": r.current_branch,
                    "dirty": len(r.dirty_files),
                    "staged": len(r.staged_files),
                    "branches": len(r.branches),
                    "worktrees": r.worktree_count,
                    "health": r.health.status.value,
                    "issues": r.health.issues,
                }
                for r in ws.repositories
            ],
            "totals": {
                "dirty_files": ws.total_dirty_files,
                "staged_files": ws.total_staged_files,
                "branches": ws.total_branches,
                "worktrees": ws.total_worktrees,
                "stale_branches": ws.stale_branches,
                "detached_worktrees": ws.detached_worktrees,
            },
            "risks": [
                {
                    "id": r.risk_id,
                    "level": r.level.value,
                    "category": r.category,
                    "description": r.description,
                }
                for r in ws.risks
            ],
            "overall_risk": ws.overall_risk.value,
            "generated_at": ws.generated_at,
        }

    def _detect_risks(self, snapshots: list[RepositorySnapshot]) -> list[EngineeringRisk]:
        risks: list[EngineeringRisk] = []
        risk_idx = 0

        for snap in snapshots:
            if len(snap.dirty_files) > 20:
                risk_idx += 1
                risks.append(EngineeringRisk(
                    risk_id=f"risk-{risk_idx}",
                    level=RiskLevel.HIGH,
                    category="dirty_state",
                    description=f"{snap.repo_name}: {len(snap.dirty_files)} dirty files",
                    repo_path=snap.repo_path,
                ))
            elif snap.dirty_files:
                risk_idx += 1
                risks.append(EngineeringRisk(
                    risk_id=f"risk-{risk_idx}",
                    level=RiskLevel.LOW,
                    category="dirty_state",
                    description=f"{snap.repo_name}: {len(snap.dirty_files)} dirty files",
                    repo_path=snap.repo_path,
                ))

            if snap.health.stale_branch_count > 5:
                risk_idx += 1
                risks.append(EngineeringRisk(
                    risk_id=f"risk-{risk_idx}",
                    level=RiskLevel.MEDIUM,
                    category="stale_branches",
                    description=f"{snap.repo_name}: {snap.health.stale_branch_count} stale branches",
                    repo_path=snap.repo_path,
                ))

            if snap.health.detached_worktrees > 0:
                risk_idx += 1
                risks.append(EngineeringRisk(
                    risk_id=f"risk-{risk_idx}",
                    level=RiskLevel.MEDIUM,
                    category="detached_worktrees",
                    description=f"{snap.repo_name}: {snap.health.detached_worktrees} detached worktrees",
                    repo_path=snap.repo_path,
                ))

            if snap.worktree_count > 10:
                risk_idx += 1
                risks.append(EngineeringRisk(
                    risk_id=f"risk-{risk_idx}",
                    level=RiskLevel.MEDIUM,
                    category="worktree_sprawl",
                    description=f"{snap.repo_name}: {snap.worktree_count} worktrees (sprawl risk)",
                    repo_path=snap.repo_path,
                ))

        return risks

    def _aggregate_risk(self, risks: list[EngineeringRisk]) -> RiskLevel:
        if not risks:
            return RiskLevel.NONE
        levels = [r.level for r in risks]
        if RiskLevel.CRITICAL in levels:
            return RiskLevel.CRITICAL
        if RiskLevel.HIGH in levels:
            return RiskLevel.HIGH
        if RiskLevel.MEDIUM in levels:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
