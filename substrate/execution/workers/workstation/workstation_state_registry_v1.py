"""Workstation State Registry v1.

Persists and retrieves workstation operational state:
  tmux sessions, runtime services, shell contexts, repositories,
  execution contexts, operational modes, relay status, connectivity,
  environment health.

Persist to: data/runtime/workstation_state/

UMH substrate subsystem.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from .workstation_contracts_v1 import (
    ConnectivityStatus,
    OperationalMode,
    WorkstationEnvironment,
    WorkstationRole,
    WorkstationSession,
    WorkstationState,
    _now_iso,
)


class WorkstationStateRegistry:
    """Tracks and persists workstation operational state."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/workstation_state",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self._state_dir / "workstation_state.json"
        self._history_path = self._state_dir / "state_history.jsonl"
        self._current_mode = OperationalMode.DEVELOPER

    def capture_state(self) -> WorkstationState:
        """Capture current workstation state from the live environment."""
        hostname = platform.node()
        tmux_sessions = self._get_tmux_sessions()
        services = self._get_docker_services()
        repo, branch = self._get_git_info()
        connectivity = self._check_connectivity()

        state = WorkstationState(
            role=WorkstationRole.VPS,
            hostname=hostname,
            operational_mode=self._current_mode,
            active_tmux_sessions=tmux_sessions,
            active_services=services,
            current_repository=repo,
            current_branch=branch,
            working_directory=os.getcwd(),
            connectivity=connectivity,
            environment_health="healthy",
            last_heartbeat=_now_iso(),
        )

        self._persist_state(state)
        return state

    def capture_environment(self) -> WorkstationEnvironment:
        """Capture the workstation environment descriptor."""
        hostname = platform.node()
        tools = self._detect_tools()
        containers = self._get_docker_services()

        return WorkstationEnvironment(
            role=WorkstationRole.VPS,
            hostname=hostname,
            platform=platform.system(),
            python_version=platform.python_version(),
            working_directory=os.getcwd(),
            available_tools=tools,
            docker_containers=containers,
            connectivity=self._check_connectivity(),
        )

    def get_current_state(self) -> WorkstationState | None:
        """Load the most recently persisted state."""
        if not self._state_path.exists():
            return None
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            return WorkstationState(
                state_id=data.get("state_id", ""),
                role=WorkstationRole(data.get("role", "vps")),
                hostname=data.get("hostname", ""),
                operational_mode=OperationalMode(data.get("operational_mode", "developer_mode")),
                active_tmux_sessions=data.get("active_tmux_sessions", []),
                active_services=data.get("active_services", []),
                current_repository=data.get("current_repository", ""),
                current_branch=data.get("current_branch", ""),
                working_directory=data.get("working_directory", ""),
                connectivity=ConnectivityStatus(data.get("connectivity", "connected")),
                relay_status=data.get("relay_status", ""),
                environment_health=data.get("environment_health", "healthy"),
                last_heartbeat=data.get("last_heartbeat", ""),
            )
        except (json.JSONDecodeError, ValueError):
            return None

    def set_mode(self, mode: OperationalMode) -> None:
        self._current_mode = mode

    def get_mode(self) -> OperationalMode:
        return self._current_mode

    def get_state_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Load recent state history."""
        if not self._history_path.exists():
            return []
        records = []
        with open(self._history_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]

    def get_stats(self) -> dict[str, Any]:
        state = self.get_current_state()
        return {
            "has_state": state is not None,
            "operational_mode": self._current_mode.value,
            "tmux_sessions": len(state.active_tmux_sessions) if state else 0,
            "services": len(state.active_services) if state else 0,
            "connectivity": state.connectivity.value if state else "unknown",
        }

    def _persist_state(self, state: WorkstationState) -> None:
        self._state_path.write_text(
            json.dumps(state.to_dict(), indent=2), encoding="utf-8"
        )
        with open(self._history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")

    def _get_tmux_sessions(self) -> list[str]:
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return [s.strip() for s in result.stdout.strip().splitlines() if s.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return []

    def _get_docker_services(self) -> list[str]:
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return [s.strip() for s in result.stdout.strip().splitlines() if s.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return []

    def _get_git_info(self) -> tuple[str, str]:
        try:
            repo = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return (
                repo.stdout.strip() if repo.returncode == 0 else "",
                branch.stdout.strip() if branch.returncode == 0 else "",
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "", ""

    def _check_connectivity(self) -> ConnectivityStatus:
        return ConnectivityStatus.CONNECTED

    def _detect_tools(self) -> list[str]:
        tools = []
        for tool in ["python3", "git", "docker", "tmux", "ruff", "pytest", "ssh", "curl"]:
            try:
                result = subprocess.run(
                    ["which", tool], capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    tools.append(tool)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return tools
