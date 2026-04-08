"""Action executors — dispatch by action.type.

Each executor returns a JSON-serialisable dict. Failures are captured as
{"ok": False, "error": str(e)} rather than raised, so the Control Plane
can log them uniformly.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

from .actions import Action


def _run_shell(command: str, timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s"}
    except Exception as e:  # pragma: no cover - defensive
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _execute_shell_command(action: Action) -> dict[str, Any]:
    return _run_shell(action.inputs["command"], action.inputs.get("timeout", 60))


def _execute_run_script(action: Action) -> dict[str, Any]:
    path = action.inputs["path"]
    args = action.inputs.get("args", [])
    if path.endswith(".py"):
        cmd = ["python3", path, *[str(a) for a in args]]
    else:
        cmd = ["bash", path, *[str(a) for a in args]]
    return _run_shell(" ".join(cmd), action.inputs.get("timeout", 120))


def _execute_write_file(action: Action) -> dict[str, Any]:
    path = action.inputs["path"]
    content = action.inputs["content"]
    mode = action.inputs.get("mode", "w")
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, mode) as f:
            bytes_written = f.write(content)
        return {"ok": True, "path": path, "bytes_written": bytes_written}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _execute_call_api(action: Action) -> dict[str, Any]:
    # Minimal stub — full HTTP client can come later. We at least verify the
    # call site compiles and returns a uniform shape.
    try:
        import urllib.request
        import json as _json

        url = action.inputs["url"]
        method = action.inputs.get("method", "GET").upper()
        headers = action.inputs.get("headers", {})
        body = action.inputs.get("body")
        data = _json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=action.inputs.get("timeout", 30)) as r:
            payload = r.read(8192).decode("utf-8", errors="replace")
            return {"ok": 200 <= r.status < 300, "status": r.status, "body": payload}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


_DISPATCH = {
    "shell_command": _execute_shell_command,
    "run_script": _execute_run_script,
    "write_file": _execute_write_file,
    "call_api": _execute_call_api,
}


def execute_action(action: Action) -> dict[str, Any]:
    """Dispatch an approved action to its executor and record the result."""
    if action.status != "approved":
        result = {
            "ok": False,
            "error": f"cannot execute action in status {action.status!r}",
        }
        action.result = result
        return result

    handler = _DISPATCH.get(action.type)
    if handler is None:
        result = {"ok": False, "error": f"no executor for type {action.type!r}"}
        action.result = result
        action.status = "failed"
        return result

    result = handler(action)
    action.result = result
    action.status = "executed" if result.get("ok") else "failed"
    return result
