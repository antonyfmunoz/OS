"""Repository reality model — read-only git awareness.

Provides snapshot contracts and a reader that queries git state
without ever mutating it. No git push, no git commit, no git checkout.

Phase 21. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)


class RepositoryHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DIRTY = "dirty"
    STALE = "stale"
    DETACHED = "detached"
    UNKNOWN = "unknown"


@dataclass
class BranchSnapshot:
    branch_name: str
    last_commit_hash: str = ""
    last_commit_message: str = ""
    last_commit_timestamp: float = 0.0
    ahead_count: int = 0
    behind_count: int = 0
    is_current: bool = False
    is_remote_only: bool = False


@dataclass
class WorktreeSnapshot:
    path: str
    branch: str = ""
    commit_hash: str = ""
    is_locked: bool = False
    is_detached: bool = False
    is_bare: bool = False


@dataclass
class RepositoryHealth:
    status: RepositoryHealthStatus = RepositoryHealthStatus.UNKNOWN
    dirty_file_count: int = 0
    stale_branch_count: int = 0
    stale_worktree_count: int = 0
    detached_worktrees: int = 0
    issues: list[str] = field(default_factory=list)


@dataclass
class RepositorySnapshot:
    repo_name: str
    repo_path: str
    current_branch: str = ""
    head_commit: str = ""
    head_commit_message: str = ""
    head_commit_timestamp: float = 0.0
    dirty_files: list[str] = field(default_factory=list)
    staged_files: list[str] = field(default_factory=list)
    branches: list[BranchSnapshot] = field(default_factory=list)
    worktrees: list[WorktreeSnapshot] = field(default_factory=list)
    worktree_count: int = 0
    health: RepositoryHealth = field(default_factory=RepositoryHealth)
    snapshot_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class RepositoryReader:
    """Read-only git repository observer. Never mutates."""

    def __init__(self, repo_path: str | None = None) -> None:
        self._repo_path = repo_path or os.environ.get("UMH_ROOT", "/opt/OS")

    def snapshot(self) -> RepositorySnapshot:
        repo_name = os.path.basename(self._repo_path)
        snap = RepositorySnapshot(
            repo_name=repo_name,
            repo_path=self._repo_path,
        )

        snap.current_branch = self._get_current_branch()
        head_info = self._get_head_info()
        snap.head_commit = head_info.get("hash", "")
        snap.head_commit_message = head_info.get("message", "")
        snap.head_commit_timestamp = head_info.get("timestamp", 0.0)
        snap.dirty_files = self._get_dirty_files()
        snap.staged_files = self._get_staged_files()
        snap.branches = self._get_branches()
        snap.worktrees = self._get_worktrees()
        snap.worktree_count = len(snap.worktrees)
        snap.health = self._assess_health(snap)
        snap.snapshot_at = time.time()

        return snap

    def _git(self, *args: str) -> str:
        cmd = ["git", "-C", self._repo_path] + list(args)
        result = gated_subprocess_run(
            cmd,
            caller="meta_ide.repository_model",
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result is None:
            return ""
        return result.stdout.rstrip() if result.returncode == 0 else ""

    def _get_current_branch(self) -> str:
        branch = self._git("rev-parse", "--abbrev-ref", "HEAD")
        return branch if branch != "HEAD" else "(detached)"

    def _get_head_info(self) -> dict[str, Any]:
        log_line = self._git(
            "log", "-1", "--format=%H%n%s%n%ct",
        )
        if not log_line:
            return {}
        parts = log_line.split("\n", 2)
        result: dict[str, Any] = {"hash": parts[0] if len(parts) > 0 else ""}
        result["message"] = parts[1] if len(parts) > 1 else ""
        try:
            result["timestamp"] = float(parts[2]) if len(parts) > 2 else 0.0
        except ValueError:
            result["timestamp"] = 0.0
        return result

    def _get_dirty_files(self) -> list[str]:
        output = self._git("status", "--porcelain", "-u")
        if not output:
            return []
        files = []
        for line in output.split("\n"):
            if line and len(line) > 3:
                status = line[:2]
                if status[1] in ("M", "D", "?"):
                    files.append(line[3:].strip())
        return files

    def _get_staged_files(self) -> list[str]:
        output = self._git("status", "--porcelain")
        if not output:
            return []
        files = []
        for line in output.split("\n"):
            if line and len(line) > 3:
                if line[0] in ("M", "A", "D", "R"):
                    files.append(line[3:].strip())
        return files

    def _get_branches(self) -> list[BranchSnapshot]:
        output = self._git(
            "for-each-ref",
            "--format=%(refname:short)\t%(objectname:short)\t%(subject)\t%(committerdate:unix)\t%(HEAD)",
            "refs/heads/",
        )
        if not output:
            return []
        branches = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            try:
                ts = float(parts[3])
            except ValueError:
                ts = 0.0
            bs = BranchSnapshot(
                branch_name=parts[0],
                last_commit_hash=parts[1],
                last_commit_message=parts[2],
                last_commit_timestamp=ts,
                is_current=(parts[4].strip() == "*" if len(parts) > 4 else False),
            )
            ahead_behind = self._get_ahead_behind(parts[0])
            bs.ahead_count = ahead_behind[0]
            bs.behind_count = ahead_behind[1]
            branches.append(bs)
        return branches

    def _get_ahead_behind(self, branch: str) -> tuple[int, int]:
        output = self._git(
            "rev-list", "--left-right", "--count",
            f"{branch}...origin/{branch}",
        )
        if not output:
            return (0, 0)
        m = re.match(r"(\d+)\s+(\d+)", output)
        if m:
            return (int(m.group(1)), int(m.group(2)))
        return (0, 0)

    def _get_worktrees(self) -> list[WorktreeSnapshot]:
        output = self._git("worktree", "list", "--porcelain")
        if not output:
            return []
        worktrees = []
        current: dict[str, str] = {}
        for line in output.split("\n"):
            if line.startswith("worktree "):
                if current.get("path"):
                    worktrees.append(self._parse_worktree(current))
                current = {"path": line[9:].strip()}
            elif line.startswith("HEAD "):
                current["commit"] = line[5:].strip()
            elif line.startswith("branch "):
                current["branch"] = line[7:].strip()
            elif line == "detached":
                current["detached"] = "true"
            elif line == "locked":
                current["locked"] = "true"
            elif line == "bare":
                current["bare"] = "true"
        if current.get("path"):
            worktrees.append(self._parse_worktree(current))
        return worktrees

    def _parse_worktree(self, data: dict[str, str]) -> WorktreeSnapshot:
        branch_raw = data.get("branch", "")
        branch = branch_raw.replace("refs/heads/", "") if branch_raw else ""
        return WorktreeSnapshot(
            path=data.get("path", ""),
            branch=branch,
            commit_hash=data.get("commit", ""),
            is_locked=data.get("locked") == "true",
            is_detached=data.get("detached") == "true",
            is_bare=data.get("bare") == "true",
        )

    def _assess_health(self, snap: RepositorySnapshot) -> RepositoryHealth:
        health = RepositoryHealth()
        issues: list[str] = []

        if snap.dirty_files:
            health.dirty_file_count = len(snap.dirty_files)
            health.status = RepositoryHealthStatus.DIRTY
            issues.append(f"{health.dirty_file_count} dirty files")

        if snap.current_branch == "(detached)":
            health.status = RepositoryHealthStatus.DETACHED
            issues.append("HEAD is detached")

        now = time.time()
        stale_threshold = 7 * 24 * 3600
        stale_branches = 0
        for b in snap.branches:
            if b.last_commit_timestamp > 0 and (now - b.last_commit_timestamp) > stale_threshold:
                stale_branches += 1
        health.stale_branch_count = stale_branches
        if stale_branches > 0:
            issues.append(f"{stale_branches} stale branches (>7d)")

        detached_wt = sum(1 for w in snap.worktrees if w.is_detached)
        health.detached_worktrees = detached_wt
        if detached_wt > 0:
            issues.append(f"{detached_wt} detached worktrees")

        health.issues = issues
        if not issues:
            health.status = RepositoryHealthStatus.HEALTHY

        return health
