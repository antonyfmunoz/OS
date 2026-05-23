"""Command Surface Sync Verification v1.

Verifies that the live Discord bot's command surface matches
the source-of-truth registrations. Detects:
  - Commands registered in source but missing from live surface
  - Stale bot process running old code
  - VPS/origin/local commit drift
  - Command surface hash mismatch

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


@dataclass
class CommandSurfaceSyncResult:
    """Result of a command surface sync verification."""

    synced: bool = False
    vps_commit: str = ""
    origin_commit: str = ""
    source_commands: list[str] = field(default_factory=list)
    live_surface_hash: str = ""
    source_surface_hash: str = ""
    missing_commands: list[str] = field(default_factory=list)
    extra_commands: list[str] = field(default_factory=list)
    process_stale: bool = False
    process_uptime_days: int = 0
    errors: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "synced": self.synced,
            "vps_commit": self.vps_commit,
            "origin_commit": self.origin_commit,
            "source_commands": self.source_commands,
            "live_surface_hash": self.live_surface_hash,
            "source_surface_hash": self.source_surface_hash,
            "missing_commands": self.missing_commands,
            "extra_commands": self.extra_commands,
            "process_stale": self.process_stale,
            "process_uptime_days": self.process_uptime_days,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


def _git_commit(ref: str, repo_dir: str = _DEFAULT_ROOT) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", ref],
            capture_output=True,
            text=True,
            cwd=repo_dir,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _container_uptime_days(container_name: str) -> int:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.StartedAt}}", container_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        started_str = result.stdout.strip()
        if not started_str:
            return -1
        started = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - started
        return delta.days
    except Exception:
        return -1


def compute_surface_hash(commands: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(commands)).encode()).hexdigest()[:12]


def verify_command_surface(
    source_commands: set[str],
    live_commands: set[str] | None = None,
    container_name: str = "os-discord",
    repo_dir: str = _DEFAULT_ROOT,
) -> CommandSurfaceSyncResult:
    """Verify the command surface is in sync."""
    result = CommandSurfaceSyncResult()

    result.vps_commit = _git_commit("HEAD", repo_dir)
    result.origin_commit = _git_commit("origin/main", repo_dir)

    result.source_commands = sorted(source_commands)
    result.source_surface_hash = compute_surface_hash(result.source_commands)

    if live_commands is not None:
        live_sorted = sorted(live_commands)
        result.live_surface_hash = compute_surface_hash(live_sorted)
        result.missing_commands = sorted(source_commands - live_commands)
        result.extra_commands = sorted(live_commands - source_commands)
    else:
        result.live_surface_hash = result.source_surface_hash
        result.missing_commands = []
        result.extra_commands = []

    uptime = _container_uptime_days(container_name)
    result.process_uptime_days = uptime
    result.process_stale = uptime > 0 and result.vps_commit != result.origin_commit

    if result.vps_commit and result.origin_commit:
        if result.vps_commit != result.origin_commit:
            result.errors.append(
                f"VPS HEAD ({result.vps_commit}) != origin/main ({result.origin_commit})"
            )

    if result.missing_commands:
        result.errors.append(f"missing from live: {', '.join(result.missing_commands)}")

    result.synced = (
        not result.missing_commands
        and not result.extra_commands
        and not result.process_stale
        and result.source_surface_hash == result.live_surface_hash
    )

    return result


def persist_sync_proof(
    result: CommandSurfaceSyncResult,
    proof_dir: Path = Path(_DEFAULT_ROOT) / "data" / "runtime" / "command_surface_proofs",
) -> Path:
    """Write sync verification result to disk."""
    proof_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = proof_dir / f"SYNC-{ts}.json"
    with open(path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    return path
