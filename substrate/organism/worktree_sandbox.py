"""Worktree Sandbox Manager — isolated execution environments for autonomous improvements.

Creates git worktrees as sandboxes so autonomous improvements never
mutate the primary checkout or main branch. Each sandbox gets a
deterministic branch name, file locks to prevent concurrent overlap,
and cleanup policies.

Doctrine:
  - Main is production truth.
  - A sandbox result is a hypothesis.
  - No direct mutation to /opt/OS primary checkout.
  - Worktrees live under .claude/worktrees/.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_WORKTREE_BASE = os.path.join(_REPO_ROOT, ".claude", "worktrees")


class SandboxStatus(str, Enum):
    CREATED = "created"
    EXECUTING = "executing"
    VALIDATION_FAILED = "validation_failed"
    VALIDATED = "validated"
    PR_CREATED = "pr_created"
    MERGED = "merged"
    ABANDONED = "abandoned"
    CLEANED = "cleaned"


class SandboxCleanupPolicy(str, Enum):
    ON_MERGE = "on_merge"
    ON_ABANDON = "on_abandon"
    MANUAL = "manual"
    TTL_HOURS = "ttl_hours"


@dataclass
class SandboxLock:
    file_path: str
    sandbox_id: str
    acquired_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "sandbox_id": self.sandbox_id,
            "acquired_at": self.acquired_at,
        }


@dataclass
class SandboxValidationResult:
    passed: bool = False
    command: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_seconds: float = 0.0
    validated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "command": self.command,
            "stdout": self.stdout[:500],
            "stderr": self.stderr[:500],
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 2),
            "validated_at": self.validated_at,
        }


@dataclass
class WorktreeSandbox:
    sandbox_id: str = field(default_factory=lambda: f"sb-{uuid4().hex[:8]}")
    branch_name: str = ""
    worktree_path: str = ""
    base_commit: str = ""
    candidate_id: str = ""
    template_id: str = ""
    agent_type: str = "developer_agent"
    created_at: float = field(default_factory=time.time)
    status: SandboxStatus = SandboxStatus.CREATED
    affected_files: list[str] = field(default_factory=list)
    locks: list[SandboxLock] = field(default_factory=list)
    validation_results: list[SandboxValidationResult] = field(default_factory=list)
    cleanup_policy: SandboxCleanupPolicy = SandboxCleanupPolicy.ON_MERGE
    pr_url: str = ""
    pr_number: int = 0
    head_commit: str = ""
    error: str = ""
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "branch_name": self.branch_name,
            "worktree_path": self.worktree_path,
            "base_commit": self.base_commit,
            "head_commit": self.head_commit,
            "candidate_id": self.candidate_id,
            "template_id": self.template_id,
            "agent_type": self.agent_type,
            "created_at": self.created_at,
            "status": self.status.value,
            "affected_files": self.affected_files,
            "locks": [lk.to_dict() for lk in self.locks],
            "validation_results": [v.to_dict() for v in self.validation_results],
            "cleanup_policy": self.cleanup_policy.value,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "error": self.error,
            "completed_at": self.completed_at,
        }


def make_branch_name(candidate_slug: str, short_id: str) -> str:
    slug = candidate_slug[:40].lower()
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug)
    slug = slug.strip("-")
    return f"auto/low-risk/{slug}-{short_id[:8]}"


def _run_git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd or _REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


class SandboxManager:
    """Manages worktree sandboxes for autonomous improvements."""

    def __init__(
        self,
        repo_root: str | None = None,
        worktree_base: str | None = None,
        store_dir: str | None = None,
        max_parallel: int = 2,
        ttl_hours: int = 24,
    ) -> None:
        self._repo_root = repo_root or _REPO_ROOT
        self._worktree_base = worktree_base or _WORKTREE_BASE
        self._store_dir = store_dir or os.path.join(
            self._repo_root, "data", "umh", "autonomous_lane", "sandboxes"
        )
        self._max_parallel = max_parallel
        self._ttl_hours = ttl_hours
        self._sandboxes: dict[str, WorktreeSandbox] = {}
        self._file_locks: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        index_path = os.path.join(self._store_dir, "index.json")
        if not os.path.isfile(index_path):
            return
        try:
            with open(index_path) as f:
                data = json.load(f)
            for entry in data.get("sandboxes", []):
                sb = WorktreeSandbox(
                    sandbox_id=entry["sandbox_id"],
                    branch_name=entry.get("branch_name", ""),
                    worktree_path=entry.get("worktree_path", ""),
                    base_commit=entry.get("base_commit", ""),
                    head_commit=entry.get("head_commit", ""),
                    candidate_id=entry.get("candidate_id", ""),
                    template_id=entry.get("template_id", ""),
                    agent_type=entry.get("agent_type", "developer_agent"),
                    created_at=entry.get("created_at", 0),
                    status=SandboxStatus(entry.get("status", "created")),
                    affected_files=entry.get("affected_files", []),
                    cleanup_policy=SandboxCleanupPolicy(
                        entry.get("cleanup_policy", "on_merge")
                    ),
                    pr_url=entry.get("pr_url", ""),
                    pr_number=entry.get("pr_number", 0),
                    error=entry.get("error", ""),
                    completed_at=entry.get("completed_at", 0),
                )
                self._sandboxes[sb.sandbox_id] = sb
                for fp in sb.affected_files:
                    if sb.status in (
                        SandboxStatus.CREATED,
                        SandboxStatus.EXECUTING,
                        SandboxStatus.VALIDATED,
                    ):
                        self._file_locks[fp] = sb.sandbox_id
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("Failed to load sandbox index: %s", e)

    def _persist(self) -> None:
        os.makedirs(self._store_dir, exist_ok=True)
        index_path = os.path.join(self._store_dir, "index.json")
        data = {
            "sandboxes": [sb.to_dict() for sb in self._sandboxes.values()],
            "file_locks": self._file_locks,
            "updated_at": time.time(),
        }
        with open(index_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @property
    def active_sandboxes(self) -> list[WorktreeSandbox]:
        active_statuses = {
            SandboxStatus.CREATED,
            SandboxStatus.EXECUTING,
            SandboxStatus.VALIDATED,
            SandboxStatus.PR_CREATED,
        }
        return [
            sb for sb in self._sandboxes.values()
            if sb.status in active_statuses
        ]

    @property
    def all_sandboxes(self) -> list[WorktreeSandbox]:
        return list(self._sandboxes.values())

    def get_sandbox(self, sandbox_id: str) -> WorktreeSandbox | None:
        return self._sandboxes.get(sandbox_id)

    def check_file_conflicts(self, affected_files: list[str]) -> list[str]:
        conflicts = []
        for fp in affected_files:
            if fp in self._file_locks:
                owner = self._file_locks[fp]
                owner_sb = self._sandboxes.get(owner)
                if owner_sb and owner_sb.status in (
                    SandboxStatus.CREATED,
                    SandboxStatus.EXECUTING,
                    SandboxStatus.VALIDATED,
                ):
                    conflicts.append(fp)
        return conflicts

    def create_sandbox(
        self,
        candidate_id: str,
        candidate_slug: str,
        template_id: str = "",
        agent_type: str = "developer_agent",
        affected_files: list[str] | None = None,
        cleanup_policy: SandboxCleanupPolicy = SandboxCleanupPolicy.ON_MERGE,
    ) -> WorktreeSandbox:
        if len(self.active_sandboxes) >= self._max_parallel:
            raise RuntimeError(
                f"Max parallel sandboxes ({self._max_parallel}) reached. "
                f"Active: {len(self.active_sandboxes)}"
            )

        affected = affected_files or []
        conflicts = self.check_file_conflicts(affected)
        if conflicts:
            raise RuntimeError(
                f"File lock conflict on: {', '.join(conflicts[:5])}"
            )

        short_id = uuid4().hex[:8]
        sandbox_id = f"sb-{short_id}"
        branch_name = make_branch_name(candidate_slug, short_id)
        worktree_path = os.path.join(self._worktree_base, f"auto-{short_id}")

        result = _run_git(["rev-parse", "HEAD"], cwd=self._repo_root)
        if result.returncode != 0:
            raise RuntimeError(f"git rev-parse failed: {result.stderr}")
        base_commit = result.stdout.strip()

        os.makedirs(self._worktree_base, exist_ok=True)
        result = _run_git(
            ["worktree", "add", "-b", branch_name, worktree_path],
            cwd=self._repo_root,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git worktree add failed: {result.stderr}")

        sandbox = WorktreeSandbox(
            sandbox_id=sandbox_id,
            branch_name=branch_name,
            worktree_path=worktree_path,
            base_commit=base_commit,
            candidate_id=candidate_id,
            template_id=template_id,
            agent_type=agent_type,
            affected_files=affected,
            cleanup_policy=cleanup_policy,
        )

        for fp in affected:
            lock = SandboxLock(file_path=fp, sandbox_id=sandbox_id)
            sandbox.locks.append(lock)
            self._file_locks[fp] = sandbox_id

        self._sandboxes[sandbox_id] = sandbox
        self._persist()
        logger.info(
            "Created sandbox %s on branch %s at %s",
            sandbox_id, branch_name, worktree_path,
        )
        return sandbox

    def update_status(
        self,
        sandbox_id: str,
        status: SandboxStatus,
        error: str = "",
        head_commit: str = "",
        pr_url: str = "",
        pr_number: int = 0,
    ) -> WorktreeSandbox:
        sb = self._sandboxes.get(sandbox_id)
        if not sb:
            raise KeyError(f"Unknown sandbox: {sandbox_id}")

        sb.status = status
        if error:
            sb.error = error
        if head_commit:
            sb.head_commit = head_commit
        if pr_url:
            sb.pr_url = pr_url
        if pr_number:
            sb.pr_number = pr_number

        terminal = {
            SandboxStatus.MERGED,
            SandboxStatus.ABANDONED,
            SandboxStatus.CLEANED,
        }
        if status in terminal:
            sb.completed_at = time.time()
            for fp in sb.affected_files:
                if self._file_locks.get(fp) == sandbox_id:
                    del self._file_locks[fp]

        self._persist()
        return sb

    def add_validation_result(
        self, sandbox_id: str, result: SandboxValidationResult
    ) -> None:
        sb = self._sandboxes.get(sandbox_id)
        if not sb:
            raise KeyError(f"Unknown sandbox: {sandbox_id}")
        sb.validation_results.append(result)
        self._persist()

    def cleanup_sandbox(self, sandbox_id: str) -> bool:
        sb = self._sandboxes.get(sandbox_id)
        if not sb:
            return False

        if os.path.isdir(sb.worktree_path):
            git_result = _run_git(
                ["worktree", "remove", "--force", sb.worktree_path],
                cwd=self._repo_root,
            )
            if git_result.returncode != 0:
                try:
                    shutil.rmtree(sb.worktree_path)
                except OSError as e:
                    logger.warning("Worktree cleanup failed for %s: %s", sandbox_id, e)
                    return False

        if sb.branch_name:
            _run_git(
                ["branch", "-D", sb.branch_name],
                cwd=self._repo_root,
            )

        for fp in sb.affected_files:
            if self._file_locks.get(fp) == sandbox_id:
                del self._file_locks[fp]

        sb.status = SandboxStatus.CLEANED
        sb.completed_at = time.time()
        self._persist()
        logger.info("Cleaned sandbox %s", sandbox_id)
        return True

    def cleanup_expired(self) -> list[str]:
        cleaned = []
        now = time.time()
        threshold = self._ttl_hours * 3600

        for sb in list(self._sandboxes.values()):
            if sb.status in (SandboxStatus.CLEANED, SandboxStatus.MERGED):
                continue
            age = now - sb.created_at
            if age > threshold and sb.status == SandboxStatus.ABANDONED:
                if self.cleanup_sandbox(sb.sandbox_id):
                    cleaned.append(sb.sandbox_id)

        return cleaned

    def abandon_sandbox(self, sandbox_id: str, reason: str = "") -> WorktreeSandbox:
        return self.update_status(
            sandbox_id,
            SandboxStatus.ABANDONED,
            error=reason or "abandoned by operator",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sandboxes": len(self._sandboxes),
            "active_sandboxes": len(self.active_sandboxes),
            "max_parallel": self._max_parallel,
            "ttl_hours": self._ttl_hours,
            "file_locks": dict(self._file_locks),
            "sandboxes": [sb.to_dict() for sb in self._sandboxes.values()],
        }

    def production_truth(self) -> dict[str, Any]:
        result = _run_git(["rev-parse", "HEAD"], cwd=self._repo_root)
        main_commit = result.stdout.strip() if result.returncode == 0 else "unknown"

        result = _run_git(
            ["log", "--oneline", "-1", "main"], cwd=self._repo_root
        )
        main_log = result.stdout.strip() if result.returncode == 0 else "unknown"

        pending_prs = [
            sb.to_dict()
            for sb in self._sandboxes.values()
            if sb.status == SandboxStatus.PR_CREATED
        ]

        return {
            "main_commit": main_commit,
            "main_log": main_log,
            "pending_prs": pending_prs,
            "active_sandboxes": len(self.active_sandboxes),
            "total_sandboxes": len(self._sandboxes),
        }
