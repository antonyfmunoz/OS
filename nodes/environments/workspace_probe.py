"""Workspace Probe — subprocess-based discovery of active workspace state.

Discovers tmux sessions, Docker containers, and dev server previews
via local subprocess calls. All calls are CPU-gated. Read-only.
No mutations. No execution authority.

Phase 25. UMH nodes layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)

_DEV_PORT_RANGE = range(3000, 10000)

_KNOWN_DEV_SERVERS = re.compile(
    r"(?i)\b(node|vite|next|webpack|esbuild|uvicorn|gunicorn|flask|fastapi|python)\b"
)


class WorkspaceProbe:
    """Discovers active workspace state via local subprocess calls.

    CPU-gated. Read-only. No mutations.
    """

    def probe_terminals(self) -> list[dict[str, Any]]:
        result = gated_subprocess_run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            caller="workspace_probe.terminals",
            timeout=5.0,
        )
        if result is None or result.returncode != 0:
            return []

        sessions = [s.strip() for s in result.stdout.strip().split("\n") if s.strip()]
        terminals: list[dict[str, Any]] = []

        for session_name in sessions:
            pane_result = gated_subprocess_run(
                [
                    "tmux",
                    "list-panes",
                    "-t",
                    session_name,
                    "-F",
                    "#{window_name}|#{pane_index}|#{pane_pid}|#{pane_current_command}|#{pane_current_path}|#{pane_active}",
                ],
                caller="workspace_probe.panes",
                timeout=5.0,
            )
            if pane_result is None or pane_result.returncode != 0:
                terminals.append(
                    {
                        "terminal_id": f"{session_name}:0.0",
                        "session_name": session_name,
                        "window_name": "",
                        "pane_index": 0,
                        "current_command": "",
                        "cwd": "",
                        "pid": 0,
                        "is_active": False,
                        "observed_at": time.time(),
                    }
                )
                continue

            for line in pane_result.stdout.strip().split("\n"):
                parts = line.split("|")
                if len(parts) < 6:
                    continue
                window_name = parts[0]
                pane_index = int(parts[1]) if parts[1].isdigit() else 0
                pid = int(parts[2]) if parts[2].isdigit() else 0
                command = parts[3]
                cwd = parts[4]
                is_active = parts[5] == "1"

                terminals.append(
                    {
                        "terminal_id": f"{session_name}:{window_name}.{pane_index}",
                        "session_name": session_name,
                        "window_name": window_name,
                        "pane_index": pane_index,
                        "current_command": command,
                        "cwd": cwd,
                        "pid": pid,
                        "is_active": is_active,
                        "observed_at": time.time(),
                    }
                )

        return terminals

    def probe_containers(self) -> list[dict[str, Any]]:
        result = gated_subprocess_run(
            [
                "docker",
                "ps",
                "-a",
                "--format",
                '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","ports":"{{.Ports}}"}',
            ],
            caller="workspace_probe.containers",
            timeout=10.0,
        )
        if result is None or result.returncode != 0:
            return []

        containers: list[dict[str, Any]] = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                status_str = raw.get("status", "").lower()
                health = "unknown"
                if "up" in status_str:
                    health = "healthy"
                    if "unhealthy" in status_str:
                        health = "degraded"
                elif "exited" in status_str:
                    health = "crashed"
                elif "restarting" in status_str:
                    health = "degraded"

                ports_raw = raw.get("ports", "")
                ports = [p.strip() for p in ports_raw.split(",") if p.strip()] if ports_raw else []

                restart_count = 0
                restart_match = re.search(r"Restarting \((\d+)\)", raw.get("status", ""))
                if restart_match:
                    restart_count = int(restart_match.group(1))

                containers.append(
                    {
                        "container_id": raw.get("id", ""),
                        "container_name": raw.get("name", ""),
                        "image": raw.get("image", ""),
                        "status": status_str,
                        "health": health,
                        "ports": ports,
                        "restart_count": restart_count,
                        "observed_at": time.time(),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        return containers

    def probe_previews(self) -> list[dict[str, Any]]:
        result = gated_subprocess_run(
            ["ss", "-tlnp"],
            caller="workspace_probe.previews",
            timeout=5.0,
        )
        if result is None or result.returncode != 0:
            return []

        previews: list[dict[str, Any]] = []
        seen_ports: set[int] = set()

        for line in result.stdout.strip().split("\n"):
            if line.startswith("State") or not line.strip():
                continue

            port_match = re.search(r":(\d+)\s", line)
            if not port_match:
                continue

            port = int(port_match.group(1))
            if port not in _DEV_PORT_RANGE or port in seen_ports:
                continue
            seen_ports.add(port)

            pid = 0
            process_name = ""
            pid_match = re.search(r"pid=(\d+)", line)
            if pid_match:
                pid = int(pid_match.group(1))
                process_name = self._pid_to_name(pid)

            health = "healthy"
            name = process_name or f"port-{port}"

            previews.append(
                {
                    "preview_id": f"preview-{port}",
                    "name": name,
                    "port": port,
                    "protocol": "http",
                    "url": f"http://localhost:{port}",
                    "pid": pid,
                    "process_name": process_name,
                    "health": health,
                    "observed_at": time.time(),
                }
            )

        return previews

    def probe_all(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "terminals": self.probe_terminals(),
            "containers": self.probe_containers(),
            "previews": self.probe_previews(),
        }

    @staticmethod
    def _pid_to_name(pid: int) -> str:
        try:
            cmdline_path = f"/proc/{pid}/cmdline"
            if os.path.exists(cmdline_path):
                with open(cmdline_path, "rb") as f:
                    cmdline = f.read().decode("utf-8", errors="replace")
                    parts = cmdline.split("\x00")
                    cmd = parts[0] if parts else ""
                    return os.path.basename(cmd) if cmd else ""
        except (OSError, PermissionError):
            pass
        return ""
