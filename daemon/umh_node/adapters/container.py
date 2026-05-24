"""Container adapter — Docker container lifecycle and execution.

Manages sandboxed execution environments for computer-use agents.
Each container runs Xvfb + x11vnc + noVNC for visual automation.
"""

from __future__ import annotations

import base64
import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_IMAGE = "umh-computer-use:latest"
DEFAULT_MEM_LIMIT = "2g"
BASE_VNC_PORT = 6080


class ContainerAdapter:
    """Docker container orchestration for sandboxed execution."""

    def handle(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        ops = {
            "container.spawn": self._spawn,
            "container.run_cmd": self._run_cmd,
            "container.screenshot": self._screenshot,
            "container.stop": self._stop,
            "container.list": self._list,
        }
        handler = ops.get(operation)
        if handler is None:
            return {"success": False, "error": f"unknown operation: {operation}"}
        try:
            return handler(params)
        except FileNotFoundError:
            return {"success": False, "error": "docker not found in PATH"}
        except Exception as exc:
            logger.debug("container adapter error: %s", exc)
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    def _spawn(self, params: dict[str, Any]) -> dict[str, Any]:
        image = params.get("image", DEFAULT_IMAGE)
        slot = int(params.get("slot", 0))
        mem_limit = params.get("mem_limit", DEFAULT_MEM_LIMIT)
        vnc_port = BASE_VNC_PORT + slot
        container_name = f"umh-cu-agent-{slot}"

        result = subprocess.run(
            [
                "docker", "run", "-d",
                "--name", container_name,
                "--memory", mem_limit,
                "-p", f"{vnc_port}:6080",
                "--rm",
                image,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}

        container_id = result.stdout.strip()[:12]
        return {
            "success": True,
            "container_id": container_id,
            "container_name": container_name,
            "vnc_port": vnc_port,
        }

    def _run_cmd(self, params: dict[str, Any]) -> dict[str, Any]:
        container = params.get("container_id") or params.get("container_name", "")
        cmd = params.get("cmd", "")
        if not container or not cmd:
            return {"success": False, "error": "container_id/container_name and cmd required"}

        cmd_parts = cmd if isinstance(cmd, list) else cmd.split()
        result = subprocess.run(
            ["docker", "exec", container] + cmd_parts,
            capture_output=True,
            text=True,
            timeout=30,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }

    def _screenshot(self, params: dict[str, Any]) -> dict[str, Any]:
        container = params.get("container_id") or params.get("container_name", "")
        if not container:
            return {"success": False, "error": "container_id or container_name required"}

        result = subprocess.run(
            [
                "docker", "exec", container,
                "scrot", "-o", "/tmp/screenshot.png",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return {"success": False, "error": f"scrot failed: {result.stderr.strip()}"}

        cat_result = subprocess.run(
            ["docker", "exec", container, "cat", "/tmp/screenshot.png"],
            capture_output=True,
            timeout=10,
        )

        if cat_result.returncode != 0:
            return {"success": False, "error": "failed to read screenshot"}

        b64 = base64.b64encode(cat_result.stdout).decode("ascii")
        return {
            "success": True,
            "image_base64": b64,
            "format": "png",
        }

    def _stop(self, params: dict[str, Any]) -> dict[str, Any]:
        container = params.get("container_id") or params.get("container_name", "")
        if not container:
            return {"success": False, "error": "container_id or container_name required"}

        result = subprocess.run(
            ["docker", "stop", container],
            capture_output=True,
            text=True,
            timeout=15,
        )

        return {
            "success": result.returncode == 0,
            "error": result.stderr.strip() if result.returncode != 0 else "",
        }

    def _list(self, params: dict[str, Any]) -> dict[str, Any]:
        result = subprocess.run(
            [
                "docker", "ps",
                "--filter", "name=umh-cu-agent-",
                "--format",
                '{"id":"{{.ID}}","name":"{{.Names}}",'
                '"status":"{{.Status}}","ports":"{{.Ports}}"}',
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        containers = []
        for line in result.stdout.strip().splitlines():
            if line:
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        return {"success": True, "containers": containers}
