"""Runtime State Registry — live environment awareness for the workstation.

Maintains a continuously refreshed view of the workstation environment:
worktrees, git repositories, processes, containers, and active executions.

This is observation only — no mutation, no process control.

Components:
  - WorktreeInfo, GitRepoInfo, ProcessInfo, ContainerInfo, ExecutionInfo
  - RuntimeSnapshot: immutable point-in-time environment state
  - RuntimeStateStore: bounded snapshot ring buffer (100 max)
  - RuntimeStateRefresher: periodic refresh engine (5s default)
  - RuntimeStateRegistry: unified query surface + singleton accessor

Design constraints:
  - Read-only: never kills processes, stops containers, or mutates state
  - Bounded: max 100 snapshots retained (FIFO eviction)
  - Thread-safe: threading.Lock on all mutable state
  - Non-blocking: refresh failures are logged, never raised
  - CPU-gated: all subprocess calls go through cpu_gate

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# State Domain Models (immutable)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass(frozen=True)
class WorktreeInfo:
    worktree_id: str
    path: str
    branch: str
    is_bare: bool = False
    executor_owner: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "worktree_id": self.worktree_id,
            "path": self.path,
            "branch": self.branch,
            "is_bare": self.is_bare,
            "executor_owner": self.executor_owner,
        }


@dataclass(frozen=True)
class GitRepoInfo:
    repository: str
    current_branch: str
    dirty: bool
    untracked_count: int
    last_commit_hash: str
    last_commit_message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "current_branch": self.current_branch,
            "dirty": self.dirty,
            "untracked_count": self.untracked_count,
            "last_commit_hash": self.last_commit_hash,
            "last_commit_message": self.last_commit_message,
        }


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    command: str
    started_at: float
    cpu_percent: float
    memory_mb: float
    executor_owner: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "command": self.command,
            "started_at": self.started_at,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "executor_owner": self.executor_owner,
        }


@dataclass(frozen=True)
class ContainerInfo:
    container_id: str
    name: str
    status: str
    image: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "container_id": self.container_id,
            "name": self.name,
            "status": self.status,
            "image": self.image,
        }


@dataclass(frozen=True)
class ExecutionInfo:
    execution_id: str
    status: str
    executor_type: str
    started_at: float
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "status": self.status,
            "executor_type": self.executor_type,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class RuntimeSnapshot:
    snapshot_id: str
    timestamp: float
    worktrees: tuple[WorktreeInfo, ...]
    repositories: tuple[GitRepoInfo, ...]
    processes: tuple[ProcessInfo, ...]
    containers: tuple[ContainerInfo, ...]
    executions: tuple[ExecutionInfo, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "worktrees": [w.to_dict() for w in self.worktrees],
            "repositories": [r.to_dict() for r in self.repositories],
            "processes": [p.to_dict() for p in self.processes],
            "containers": [c.to_dict() for c in self.containers],
            "executions": [e.to_dict() for e in self.executions],
            "summary": {
                "worktree_count": len(self.worktrees),
                "repository_count": len(self.repositories),
                "process_count": len(self.processes),
                "container_count": len(self.containers),
                "execution_count": len(self.executions),
            },
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Collectors — each returns a tuple of domain models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _safe_run(cmd: list[str], timeout: int = 5) -> str:
    """Run a subprocess safely through the CPU gate. Returns stdout or empty."""
    try:
        from substrate.execution.cpu_gate import gated_subprocess_run

        result = gated_subprocess_run(
            cmd,
            caller="runtime_state_registry",
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result is None:
            logger.debug("CPU gate blocked: %s", " ".join(cmd))
            return ""
        return result.stdout.strip()
    except Exception as exc:
        logger.debug("subprocess failed (%s): %s", " ".join(cmd), exc)
        return ""


def collect_worktrees() -> tuple[WorktreeInfo, ...]:
    """Discover git worktrees in the repository."""
    raw = _safe_run(["git", "-C", _REPO_ROOT, "worktree", "list", "--porcelain"])
    if not raw:
        return ()
    worktrees: list[WorktreeInfo] = []
    current: dict[str, str] = {}
    for line in raw.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(_parse_worktree(current))
            current = {"path": line[9:]}
        elif line.startswith("branch "):
            current["branch"] = line[7:]
        elif line == "bare":
            current["bare"] = "true"
        elif not line.strip() and current:
            pass
    if current:
        worktrees.append(_parse_worktree(current))
    return tuple(worktrees)


def _parse_worktree(data: dict[str, str]) -> WorktreeInfo:
    path = data.get("path", "")
    branch_ref = data.get("branch", "")
    branch = branch_ref.replace("refs/heads/", "") if branch_ref else "(detached)"
    return WorktreeInfo(
        worktree_id=str(uuid4())[:8],
        path=path,
        branch=branch,
        is_bare=data.get("bare") == "true",
    )


def collect_git_info() -> tuple[GitRepoInfo, ...]:
    """Collect git repository state."""
    branch = _safe_run(["git", "-C", _REPO_ROOT, "rev-parse", "--abbrev-ref", "HEAD"])
    if not branch:
        return ()
    dirty_out = _safe_run(["git", "-C", _REPO_ROOT, "status", "--porcelain"])
    dirty = bool(dirty_out)
    untracked = sum(1 for line in dirty_out.splitlines() if line.startswith("??")) if dirty_out else 0
    log_out = _safe_run(["git", "-C", _REPO_ROOT, "log", "-1", "--format=%H|%s"])
    commit_hash, commit_msg = "", ""
    if log_out and "|" in log_out:
        parts = log_out.split("|", 1)
        commit_hash, commit_msg = parts[0], parts[1]
    return (
        GitRepoInfo(
            repository=_REPO_ROOT,
            current_branch=branch,
            dirty=dirty,
            untracked_count=untracked,
            last_commit_hash=commit_hash,
            last_commit_message=commit_msg,
        ),
    )


def collect_processes() -> tuple[ProcessInfo, ...]:
    """Discover relevant running processes."""
    raw = _safe_run(
        ["ps", "aux", "--sort=-pcpu"],
        timeout=3,
    )
    if not raw:
        return ()
    processes: list[ProcessInfo] = []
    lines = raw.splitlines()
    for line in lines[1:50]:
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        try:
            pid = int(parts[1])
            cpu = float(parts[2])
            mem_pct = float(parts[3])
            rss_kb = int(parts[5]) if parts[5].isdigit() else 0
            command = parts[10]
            if _is_interesting_process(command):
                processes.append(ProcessInfo(
                    pid=pid,
                    command=command[:200],
                    started_at=0.0,
                    cpu_percent=cpu,
                    memory_mb=round(rss_kb / 1024, 1),
                    executor_owner="",
                ))
        except (ValueError, IndexError):
            continue
    return tuple(processes)


def _is_interesting_process(command: str) -> bool:
    """Filter to UMH-relevant processes only."""
    keywords = (
        "python", "node", "docker", "claude", "git",
        "ollama", "flyctl", "npm", "uvicorn", "gunicorn",
    )
    cmd_lower = command.lower()
    return any(kw in cmd_lower for kw in keywords)


def collect_containers() -> tuple[ContainerInfo, ...]:
    """Discover running Docker containers."""
    raw = _safe_run(
        ["docker", "ps", "--format", "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}"],
        timeout=5,
    )
    if not raw:
        return ()
    containers: list[ContainerInfo] = []
    for line in raw.splitlines():
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        containers.append(ContainerInfo(
            container_id=parts[0],
            name=parts[1],
            status=parts[2],
            image=parts[3],
        ))
    return tuple(containers)


def collect_executions() -> tuple[ExecutionInfo, ...]:
    """Collect active executions from the executor runtime."""
    try:
        from substrate.organism.executor_runtime import get_executor_runtime

        runtime = get_executor_runtime()
        now = time.time()
        active = runtime.active_requests()
        executions: list[ExecutionInfo] = []
        for req in active:
            executions.append(ExecutionInfo(
                execution_id=req.request_id,
                status=req.status.value if hasattr(req.status, "value") else str(req.status),
                executor_type=req.executor_type.value if hasattr(req.executor_type, "value") else str(req.executor_type),
                started_at=req.created_at,
                duration_seconds=round(now - req.created_at, 2),
            ))
        return tuple(executions)
    except Exception as exc:
        logger.debug("execution collection failed: %s", exc)
        return ()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Snapshot Store (bounded ring buffer)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


_MAX_SNAPSHOTS = 100


class RuntimeStateStore:
    """Thread-safe bounded ring buffer for runtime snapshots."""

    def __init__(self, max_size: int = _MAX_SNAPSHOTS) -> None:
        self._lock = threading.Lock()
        self._snapshots: list[RuntimeSnapshot] = []
        self._max_size = max_size

    def append(self, snapshot: RuntimeSnapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._max_size:
                self._snapshots = self._snapshots[-self._max_size:]

    def latest(self) -> RuntimeSnapshot | None:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def all(self) -> list[RuntimeSnapshot]:
        with self._lock:
            return list(self._snapshots)

    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Refresher (periodic background thread)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


_DEFAULT_INTERVAL = 5.0


class RuntimeStateRefresher:
    """Periodically collects environment state into snapshots."""

    def __init__(
        self,
        store: RuntimeStateStore,
        interval: float = _DEFAULT_INTERVAL,
    ) -> None:
        self._store = store
        self._interval = interval
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="runtime-state-refresher",
        )
        self._thread.start()
        logger.info("RuntimeStateRefresher started (interval=%.1fs)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval + 2)
            self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def refresh_once(self) -> RuntimeSnapshot:
        """Run a single refresh cycle and return the snapshot."""
        snapshot = self._collect()
        self._store.append(snapshot)
        self._emit_telemetry(snapshot)
        return snapshot

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.refresh_once()
            except Exception as exc:
                logger.warning("refresh cycle failed: %s", exc)
            self._stop_event.wait(timeout=self._interval)

    def _collect(self) -> RuntimeSnapshot:
        worktrees = collect_worktrees()
        repos = collect_git_info()
        processes = collect_processes()
        containers = collect_containers()
        executions = collect_executions()
        return RuntimeSnapshot(
            snapshot_id=str(uuid4())[:12],
            timestamp=time.time(),
            worktrees=worktrees,
            repositories=repos,
            processes=processes,
            containers=containers,
            executions=executions,
        )

    def _emit_telemetry(self, snap: RuntimeSnapshot) -> None:
        """Emit telemetry events for the snapshot."""
        try:
            from substrate.organism.executors.execution_telemetry import (
                get_telemetry_emitter,
            )

            emitter = get_telemetry_emitter()
            emitter.emit(
                "runtime_snapshot_created",
                execution_id=snap.snapshot_id,
                status="collected",
                payload={
                    "worktree_count": len(snap.worktrees),
                    "process_count": len(snap.processes),
                    "container_count": len(snap.containers),
                    "execution_count": len(snap.executions),
                    "repository_count": len(snap.repositories),
                },
            )
        except Exception as exc:
            logger.debug("telemetry emit failed: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Registry (unified query surface)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RuntimeStateRegistry:
    """Unified query surface for runtime environment state."""

    def __init__(self) -> None:
        self._store = RuntimeStateStore()
        self._refresher = RuntimeStateRefresher(self._store)

    def start(self) -> None:
        self._refresher.start()

    def stop(self) -> None:
        self._refresher.stop()

    @property
    def running(self) -> bool:
        return self._refresher.running

    def refresh(self) -> RuntimeSnapshot:
        return self._refresher.refresh_once()

    def get_runtime_state(self) -> dict[str, Any]:
        snap = self._store.latest()
        if snap is None:
            snap = self.refresh()
        return snap.to_dict()

    def snapshot(self) -> RuntimeSnapshot | None:
        return self._store.latest()

    def get_worktrees(self) -> list[dict[str, Any]]:
        snap = self._store.latest()
        if snap is None:
            return []
        return [w.to_dict() for w in snap.worktrees]

    def get_processes(self) -> list[dict[str, Any]]:
        snap = self._store.latest()
        if snap is None:
            return []
        return [p.to_dict() for p in snap.processes]

    def get_containers(self) -> list[dict[str, Any]]:
        snap = self._store.latest()
        if snap is None:
            return []
        return [c.to_dict() for c in snap.containers]

    def get_executions(self) -> list[dict[str, Any]]:
        snap = self._store.latest()
        if snap is None:
            return []
        return [e.to_dict() for e in snap.executions]

    def get_repositories(self) -> list[dict[str, Any]]:
        snap = self._store.latest()
        if snap is None:
            return []
        return [r.to_dict() for r in snap.repositories]

    def snapshot_count(self) -> int:
        return self._store.count()

    def snapshot_history(self, limit: int = 10) -> list[dict[str, Any]]:
        all_snaps = self._store.all()
        recent = all_snaps[-limit:] if limit < len(all_snaps) else all_snaps
        return [
            {
                "snapshot_id": s.snapshot_id,
                "timestamp": s.timestamp,
                "summary": {
                    "worktree_count": len(s.worktrees),
                    "process_count": len(s.processes),
                    "container_count": len(s.containers),
                    "execution_count": len(s.executions),
                },
            }
            for s in recent
        ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_singleton: RuntimeStateRegistry | None = None
_singleton_lock = threading.Lock()


def get_runtime_state_registry() -> RuntimeStateRegistry:
    """Get the global RuntimeStateRegistry singleton."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = RuntimeStateRegistry()
    return _singleton


def reset_runtime_state_registry() -> None:
    """Reset the singleton (for testing)."""
    global _singleton
    if _singleton is not None:
        _singleton.stop()
    _singleton = None
