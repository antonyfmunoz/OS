"""
Control Layer v1 — Local Agent (Executor).

Polls the control_bridge queue for a node and runs whitelisted actions
inside a strict sandbox. NEVER raises. ALWAYS returns a result dict.

Hard rules (non-negotiable):
    * Only three actions: run_shell, write_file, run_python.
    * run_shell: argv[0] must be in SHELL_WHITELIST. shell=False always.
    * write_file: path must resolve under SANDBOX_ROOT. No path escape.
    * run_python: restricted snippet runner — no imports, tiny builtins.
    * No network. No background loops. Operator triggers process_pending.
"""

from __future__ import annotations

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
import subprocess
import time
from pathlib import Path
from typing import Any

from eos_ai.substrate import control_bridge as bridge
from eos_ai.substrate import control_commands as cc

LAYER_NAME = "local_executor"
LAYER_VERSION = "v1"

SANDBOX_ROOT = (Path(_ROOT) / "eos_ai" / ".substrate_sandbox").resolve()
SHELL_WHITELIST = ("ls", "pwd", "echo", "cat")
SHELL_TIMEOUT_SEC = 5
MAX_OUTPUT_CHARS = 4_000
MAX_FILE_BYTES = 64 * 1024
MAX_BATCH = 25  # process_pending hard cap


def _ensure_sandbox() -> None:
    try:
        SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:  # noqa: BLE001
        pass


def _truncate(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    return s if len(s) <= MAX_OUTPUT_CHARS else s[:MAX_OUTPUT_CHARS] + "…[truncated]"


def _result(cmd: cc.ControlCommand, ok: bool, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": bool(ok),
        "command_id": cmd.command_id,
        "action": cmd.action,
        "node_id": cmd.node_id,
        "executed_at": time.time(),
    }
    out.update(extra)
    return out


# ─── Action handlers ─────────────────────────────────────────────────────────


def _do_run_shell(cmd: cc.ControlCommand) -> dict[str, Any]:
    payload = cmd.payload or {}
    raw = payload.get("cmd")
    if not isinstance(raw, str) or not raw.strip():
        return _result(cmd, False, reason="missing_cmd")
    parts = raw.strip().split()
    if not parts:
        return _result(cmd, False, reason="empty_cmd")
    head = parts[0]
    if head not in SHELL_WHITELIST:
        return _result(cmd, False, reason=f"shell_not_whitelisted:{head}")
    _ensure_sandbox()
    try:
        proc = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT_SEC,
            cwd=str(SANDBOX_ROOT),
            shell=False,
            check=False,
        )
        return _result(
            cmd,
            True,
            exit_code=proc.returncode,
            stdout=_truncate(proc.stdout or ""),
            stderr=_truncate(proc.stderr or ""),
        )
    except subprocess.TimeoutExpired:
        return _result(cmd, False, reason="timeout")
    except Exception as e:  # noqa: BLE001
        return _result(cmd, False, reason=f"runner_error:{type(e).__name__}")


def _do_write_file(cmd: cc.ControlCommand) -> dict[str, Any]:
    payload = cmd.payload or {}
    rel = payload.get("path")
    content = payload.get("content", "")
    if not isinstance(rel, str) or not rel:
        return _result(cmd, False, reason="missing_path")
    if not isinstance(content, str):
        return _result(cmd, False, reason="content_not_str")
    if len(content.encode("utf-8", errors="replace")) > MAX_FILE_BYTES:
        return _result(cmd, False, reason="content_too_large")

    _ensure_sandbox()
    rel_clean = rel
    if rel_clean.startswith("sandbox/"):
        rel_clean = rel_clean[len("sandbox/") :]
    if rel_clean.startswith("/"):
        return _result(cmd, False, reason="absolute_path_not_allowed")
    try:
        target = (SANDBOX_ROOT / rel_clean).resolve()
        if not str(target).startswith(str(SANDBOX_ROOT) + os.sep) and target != SANDBOX_ROOT:
            return _result(cmd, False, reason="path_escape")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return _result(
            cmd, True, path=str(target), bytes_written=len(content.encode("utf-8"))
        )
    except Exception as e:  # noqa: BLE001
        return _result(cmd, False, reason=f"write_error:{type(e).__name__}")


# Tiny safe builtins surface for run_python.
_SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "sum": sum, "len": len,
    "range": range, "round": round, "sorted": sorted, "any": any, "all": all,
    "print": print, "str": str, "int": int, "float": float, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
}


def _do_run_python(cmd: cc.ControlCommand) -> dict[str, Any]:
    payload = cmd.payload or {}
    code = payload.get("code")
    if not isinstance(code, str) or not code.strip():
        return _result(cmd, False, reason="missing_code")
    if len(code) > 2_000:
        return _result(cmd, False, reason="code_too_long")
    forbidden = ("import ", "__", "open(", "globals(", "locals(")
    for token in forbidden:
        if token in code:
            return _result(cmd, False, reason=f"forbidden_token:{token.strip()}")
    import io
    import contextlib

    buf = io.StringIO()
    env_globals = {"__builtins__": _SAFE_BUILTINS}
    env_locals: dict[str, Any] = {}
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, env_globals, env_locals)  # noqa: S102
        return _result(
            cmd,
            True,
            stdout=_truncate(buf.getvalue()),
            locals_keys=sorted(k for k in env_locals.keys() if not k.startswith("_")),
        )
    except Exception as e:  # noqa: BLE001
        return _result(
            cmd, False, reason=f"python_error:{type(e).__name__}", detail=_truncate(str(e))
        )


# ─── Public API ──────────────────────────────────────────────────────────────


_DISPATCH = {
    "run_shell": _do_run_shell,
    "write_file": _do_write_file,
    "run_python": _do_run_python,
}


def execute_command(cmd: cc.ControlCommand) -> dict[str, Any]:
    """Run a single command. Never raises."""
    try:
        ok, reason = cc.validate(cmd)
        if not ok:
            return _result(cmd, False, reason=f"invalid_envelope:{reason}")
        handler = _DISPATCH.get(cmd.action)
        if handler is None:
            return _result(cmd, False, reason=f"no_handler:{cmd.action}")
        return handler(cmd)
    except Exception as e:  # noqa: BLE001
        return _result(cmd, False, reason=f"executor_exception:{type(e).__name__}")


def process_pending(node_id: str) -> dict[str, Any]:
    """
    Drain up to MAX_BATCH pending commands for `node_id`. Operator-triggered.
    Returns {"node_id", "processed", "results": [...]}.
    """
    out: dict[str, Any] = {"node_id": node_id, "processed": 0, "results": []}
    if not node_id:
        return out
    try:
        pending = bridge.get_pending_commands(node_id)
    except Exception:  # noqa: BLE001
        pending = []
    for cmd in pending[:MAX_BATCH]:
        result = execute_command(cmd)
        try:
            bridge.ack_command(cmd.command_id)
        except Exception:  # noqa: BLE001
            pass
        out["results"].append(result)
    out["processed"] = len(out["results"])
    return out
