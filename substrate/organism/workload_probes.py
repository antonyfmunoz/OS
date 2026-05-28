"""Real Workload Probes — live operational pressure into the organism.

Probes that collect real operational state from the VPS environment:
  - Docker container lifecycle and health
  - Process/tmux session monitoring
  - Disk and memory pressure
  - Repository state (branches, stale worktrees)
  - Ingestion queue depth

Each probe returns structured data and emits events through the
EventSpine. The organism tick engine calls these probes each cycle
to maintain reality awareness.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROBE_TIMEOUT = 10


def _run(cmd: list[str], timeout: int = _PROBE_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.debug("probe command failed: %s — %s", cmd, exc)
        return ""


@dataclass
class DockerProbe:
    containers: list[dict[str, str]] = field(default_factory=list)
    running: int = 0
    stopped: int = 0
    unhealthy: int = 0
    probed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "stopped": self.stopped,
            "unhealthy": self.unhealthy,
            "containers": self.containers,
            "probed_at": self.probed_at,
        }


@dataclass
class DiskProbe:
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    usage_percent: float = 0.0
    pressure: str = "normal"
    probed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_gb": round(self.total_gb, 2),
            "used_gb": round(self.used_gb, 2),
            "free_gb": round(self.free_gb, 2),
            "usage_percent": round(self.usage_percent, 1),
            "pressure": self.pressure,
            "probed_at": self.probed_at,
        }


@dataclass
class MemoryProbe:
    total_mb: float = 0.0
    available_mb: float = 0.0
    usage_percent: float = 0.0
    pressure: str = "normal"
    probed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_mb": round(self.total_mb, 1),
            "available_mb": round(self.available_mb, 1),
            "usage_percent": round(self.usage_percent, 1),
            "pressure": self.pressure,
            "probed_at": self.probed_at,
        }


@dataclass
class RepoProbe:
    branch: str = ""
    stale_branches: list[str] = field(default_factory=list)
    stale_worktrees: list[str] = field(default_factory=list)
    uncommitted_files: int = 0
    probed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch": self.branch,
            "stale_branches": self.stale_branches[:10],
            "stale_worktrees": self.stale_worktrees[:10],
            "uncommitted_files": self.uncommitted_files,
            "probed_at": self.probed_at,
        }


@dataclass
class ProcessProbe:
    tmux_sessions: list[str] = field(default_factory=list)
    python_processes: int = 0
    node_processes: int = 0
    probed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tmux_sessions": self.tmux_sessions,
            "python_processes": self.python_processes,
            "node_processes": self.node_processes,
            "probed_at": self.probed_at,
        }


class WorkloadProbes:
    """Collects real operational state from the environment.

    Each probe method is safe to call on any tick — timeouts
    prevent hangs, failures are logged and return empty data.
    """

    def __init__(
        self,
        repo_root: str | None = None,
        event_spine: Any | None = None,
    ) -> None:
        self._repo_root = repo_root or os.environ.get("UMH_ROOT", "/opt/OS")
        self._event_spine = event_spine
        self._last_full_probe: float = 0.0
        self._cache: dict[str, Any] = {}

    def probe_docker(self) -> DockerProbe:
        result = DockerProbe(probed_at=time.time())
        output = _run(["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"])
        if not output:
            return result

        for line in output.splitlines():
            parts = line.strip().split("|", 1)
            if len(parts) != 2:
                continue
            name, status = parts
            status_lower = status.lower()
            entry = {"name": name, "status": status}
            result.containers.append(entry)
            if "up" in status_lower:
                result.running += 1
                if "unhealthy" in status_lower:
                    result.unhealthy += 1
            else:
                result.stopped += 1

        return result

    def probe_disk(self) -> DiskProbe:
        result = DiskProbe(probed_at=time.time())
        try:
            usage = shutil.disk_usage(self._repo_root)
            result.total_gb = usage.total / (1024 ** 3)
            result.used_gb = usage.used / (1024 ** 3)
            result.free_gb = usage.free / (1024 ** 3)
            result.usage_percent = (usage.used / usage.total) * 100 if usage.total > 0 else 0
            if result.usage_percent > 90:
                result.pressure = "critical"
            elif result.usage_percent > 80:
                result.pressure = "high"
            elif result.usage_percent > 70:
                result.pressure = "elevated"
        except OSError as exc:
            logger.debug("disk probe failed: %s", exc)
        return result

    def probe_memory(self) -> MemoryProbe:
        result = MemoryProbe(probed_at=time.time())
        meminfo_path = Path("/proc/meminfo")
        if not meminfo_path.exists():
            return result
        try:
            text = meminfo_path.read_text()
            values: dict[str, float] = {}
            for line in text.splitlines():
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val_parts = parts[1].strip().split()
                    if val_parts:
                        try:
                            values[key] = float(val_parts[0])
                        except ValueError:
                            pass

            total_kb = values.get("MemTotal", 0)
            available_kb = values.get("MemAvailable", 0)
            result.total_mb = total_kb / 1024
            result.available_mb = available_kb / 1024
            if total_kb > 0:
                result.usage_percent = ((total_kb - available_kb) / total_kb) * 100
            if result.usage_percent > 90:
                result.pressure = "critical"
            elif result.usage_percent > 80:
                result.pressure = "high"
            elif result.usage_percent > 70:
                result.pressure = "elevated"
        except OSError as exc:
            logger.debug("memory probe failed: %s", exc)
        return result

    def probe_repo(self) -> RepoProbe:
        result = RepoProbe(probed_at=time.time())
        branch = _run(["git", "-C", self._repo_root, "branch", "--show-current"])
        result.branch = branch

        status = _run(["git", "-C", self._repo_root, "status", "--porcelain", "-u"])
        if status:
            result.uncommitted_files = len(status.splitlines())

        branches_raw = _run(["git", "-C", self._repo_root, "branch", "--format", "%(refname:short)"])
        if branches_raw:
            for b in branches_raw.splitlines():
                b = b.strip()
                if b and b != "main" and b != branch:
                    result.stale_branches.append(b)

        worktree_raw = _run(["git", "-C", self._repo_root, "worktree", "list", "--porcelain"])
        if worktree_raw:
            for line in worktree_raw.splitlines():
                if line.startswith("worktree ") and ".claude/worktrees" in line:
                    wt_path = line.replace("worktree ", "").strip()
                    result.stale_worktrees.append(wt_path)

        return result

    def probe_processes(self) -> ProcessProbe:
        result = ProcessProbe(probed_at=time.time())

        tmux = _run(["tmux", "list-sessions", "-F", "#{session_name}"])
        if tmux:
            result.tmux_sessions = [s.strip() for s in tmux.splitlines() if s.strip()]

        ps_out = _run(["ps", "aux"])
        if ps_out:
            for line in ps_out.splitlines():
                if "python" in line.lower():
                    result.python_processes += 1
                if "node" in line.lower() and "nodejs" not in line.lower():
                    result.node_processes += 1

        return result

    def full_probe(self) -> dict[str, Any]:
        docker = self.probe_docker()
        disk = self.probe_disk()
        memory = self.probe_memory()
        repo = self.probe_repo()
        processes = self.probe_processes()

        self._last_full_probe = time.time()
        result = {
            "docker": docker.to_dict(),
            "disk": disk.to_dict(),
            "memory": memory.to_dict(),
            "repo": repo.to_dict(),
            "processes": processes.to_dict(),
            "probed_at": self._last_full_probe,
        }
        self._cache = result

        if self._event_spine is not None:
            from substrate.organism.event_spine import EventDomain, EventPriority

            pressure_level = EventPriority.NORMAL
            if disk.pressure == "critical" or memory.pressure == "critical":
                pressure_level = EventPriority.CRITICAL
            elif disk.pressure == "high" or memory.pressure == "high":
                pressure_level = EventPriority.HIGH

            self._event_spine.emit(
                EventDomain.OBSERVABILITY,
                "workload_probed",
                "workload_probes",
                {
                    "disk_pressure": disk.pressure,
                    "memory_pressure": memory.pressure,
                    "docker_running": docker.running,
                    "docker_stopped": docker.stopped,
                    "docker_unhealthy": docker.unhealthy,
                    "uncommitted_files": repo.uncommitted_files,
                },
                priority=pressure_level,
            )

        return result

    @property
    def cached(self) -> dict[str, Any]:
        return self._cache

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_full_probe": self._last_full_probe,
            "cache_available": bool(self._cache),
        }
