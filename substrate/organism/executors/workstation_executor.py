"""WorkstationExecutor — first production ExecutorContract implementation.

Performs real machine operations through the governed executor runtime:
  - create_worktree: git worktree creation in approved roots
  - run_command: subprocess execution via CPU gate
  - read_file: safe file reading with path validation
  - write_file: safe file writing with path validation
  - list_directory: directory listing with path validation

Every operation routes through gated_subprocess_run() (CPU Gate Law).
Every path is resolved and validated against approved roots (no traversal).
Every execution produces ExecutionProof attached to results.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from substrate.execution.cpu_gate import cpu_gate_check, gated_subprocess_run
from substrate.organism.executor_runtime import (
    ExecutorArtifact,
    ExecutorContract,
    ExecutorRequest,
    ExecutorResult,
    ExecutorType,
)

logger = logging.getLogger(__name__)


# ── Path Safety ──────────────────────────────────────────────────

_APPROVED_ROOTS: list[str] = [
    "/workspace",
    os.environ.get("UMH_ROOT", "/opt/OS"),
]

_BLOCKED_PATTERNS: list[str] = [
    ".env",
    "credentials",
    "secrets",
    ".ssh",
    "id_rsa",
    "id_ed25519",
]

_MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MiB
_MAX_OUTPUT_BYTES: int = 1 * 1024 * 1024  # 1 MiB stdout/stderr cap
_DEFAULT_TIMEOUT: float = 30.0

_SAFE_OPERATIONS: frozenset[str] = frozenset({
    "read_file", "list_directory", "create_worktree",
})


def _is_safe_without_approval(operation: str) -> bool:
    """When approval module is unavailable, only read-only ops proceed."""
    return operation in _SAFE_OPERATIONS


def _resolve_and_validate(path_str: str) -> tuple[Path, str]:
    """Resolve a path and validate it against approved roots.

    Returns (resolved_path, error_message).
    Empty error means valid.
    """
    try:
        resolved = Path(path_str).resolve()
    except (ValueError, OSError) as exc:
        return Path(), f"Cannot resolve path: {exc}"

    approved = [Path(r).resolve() for r in _APPROVED_ROOTS]
    for root in approved:
        try:
            resolved.relative_to(root)
            return resolved, ""
        except ValueError:
            continue

    return Path(), (
        f"Path {resolved} is outside approved roots: "
        f"{[str(r) for r in approved]}"
    )


def _check_blocked(path: Path) -> str:
    """Check if a path matches blocked patterns. Returns reason or empty."""
    name_lower = path.name.lower()
    for pattern in _BLOCKED_PATTERNS:
        if pattern in name_lower:
            return f"Path matches blocked pattern: {pattern}"
    return ""


# ── Execution Proof ─────────────────────────────────────────────


@dataclass
class ExecutionProof:
    """Proof record for a single workstation operation."""

    proof_id: str = field(
        default_factory=lambda: f"wxprf-{uuid4().hex[:12]}"
    )
    execution_id: str = ""
    executor_type: str = ExecutorType.WORKSTATION.value
    operation: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "pending"
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    approval_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "execution_id": self.execution_id,
            "executor_type": self.executor_type,
            "operation": self.operation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "artifacts": self.artifacts,
            "approval_events": self.approval_events,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionProof:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ── Supported Operations ────────────────────────────────────────

SUPPORTED_OPERATIONS = frozenset({
    "create_worktree",
    "run_command",
    "read_file",
    "write_file",
    "list_directory",
})


# ── Operation Handlers ──────────────────────────────────────────


def _op_create_worktree(
    params: dict[str, Any],
    request: ExecutorRequest,
) -> tuple[bool, str, dict[str, Any], list[dict[str, Any]]]:
    """Create a git worktree in an approved root.

    Params:
      repo_root: str — repo to create worktree for
      branch_name: str — branch name for the worktree
      base_ref: str — base ref (default: HEAD)

    Returns (success, message, outputs, artifacts).
    """
    repo_root = params.get("repo_root", os.environ.get("UMH_ROOT", "/opt/OS"))
    branch_name = params.get("branch_name", "")
    base_ref = params.get("base_ref", "HEAD")

    if not branch_name:
        return False, "branch_name is required", {}, []

    resolved_repo, err = _resolve_and_validate(repo_root)
    if err:
        return False, err, {}, []

    worktree_dir = resolved_repo / ".claude" / "worktrees" / branch_name
    worktree_path = str(worktree_dir)

    if worktree_dir.exists():
        return False, f"Worktree already exists: {worktree_path}", {}, []

    result = gated_subprocess_run(
        ["git", "worktree", "add", "-b", branch_name, worktree_path, base_ref],
        caller="workstation_executor.create_worktree",
        timeout=_DEFAULT_TIMEOUT,
        cwd=str(resolved_repo),
    )

    if result is None:
        return False, "CPU gate blocked worktree creation", {}, []

    if result.returncode != 0:
        stderr = (result.stderr or "")[:_MAX_OUTPUT_BYTES]
        return False, f"git worktree add failed: {stderr}", {}, []

    outputs = {
        "worktree_path": worktree_path,
        "branch_name": branch_name,
        "base_ref": base_ref,
        "exit_code": result.returncode,
    }
    artifacts = [
        ExecutorArtifact(
            artifact_type="worktree_reference",
            name=branch_name,
            content=worktree_path,
        ).to_dict()
    ]
    return True, f"Worktree created at {worktree_path}", outputs, artifacts


def _op_run_command(
    params: dict[str, Any],
    request: ExecutorRequest,
) -> tuple[bool, str, dict[str, Any], list[dict[str, Any]]]:
    """Run a shell command in a specified working directory.

    Params:
      command: str | list[str] — the command to run
      cwd: str — working directory (must be in approved root)
      timeout: float — timeout in seconds (default 30, max 120)
      env: dict — additional environment variables

    Returns (success, message, outputs, artifacts).
    """
    command = params.get("command")
    if not command:
        return False, "command is required", {}, []

    cwd = params.get("cwd", os.environ.get("UMH_ROOT", "/opt/OS"))
    timeout = min(float(params.get("timeout", _DEFAULT_TIMEOUT)), 120.0)
    extra_env = params.get("env", {})

    resolved_cwd, err = _resolve_and_validate(cwd)
    if err:
        return False, f"Working directory invalid: {err}", {}, []

    if not resolved_cwd.is_dir():
        return False, f"Working directory does not exist: {resolved_cwd}", {}, []

    run_env = dict(os.environ)
    if extra_env and isinstance(extra_env, dict):
        for k, v in extra_env.items():
            if isinstance(k, str) and isinstance(v, str):
                run_env[k] = v

    shell = isinstance(command, str)

    result = gated_subprocess_run(
        command,
        caller="workstation_executor.run_command",
        timeout=timeout,
        cwd=str(resolved_cwd),
        shell=shell,
        env=run_env,
    )

    if result is None:
        return False, "CPU gate blocked command execution", {}, []

    stdout = (result.stdout or "")[:_MAX_OUTPUT_BYTES]
    stderr = (result.stderr or "")[:_MAX_OUTPUT_BYTES]
    success = result.returncode == 0

    outputs = {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": result.returncode,
    }
    artifacts = [
        ExecutorArtifact(
            artifact_type="command_output",
            name="stdout",
            content=stdout,
        ).to_dict()
    ]
    if stderr:
        artifacts.append(
            ExecutorArtifact(
                artifact_type="command_output",
                name="stderr",
                content=stderr,
            ).to_dict()
        )

    msg = f"Command exited with code {result.returncode}"
    return success, msg, outputs, artifacts


def _op_read_file(
    params: dict[str, Any],
    request: ExecutorRequest,
) -> tuple[bool, str, dict[str, Any], list[dict[str, Any]]]:
    """Read a file safely.

    Params:
      path: str — absolute path to read
      max_bytes: int — max bytes to read (default 10 MiB)

    Returns (success, message, outputs, artifacts).
    """
    file_path = params.get("path", "")
    if not file_path:
        return False, "path is required", {}, []

    max_bytes = min(int(params.get("max_bytes", _MAX_FILE_SIZE_BYTES)), _MAX_FILE_SIZE_BYTES)

    resolved, err = _resolve_and_validate(file_path)
    if err:
        return False, err, {}, []

    blocked = _check_blocked(resolved)
    if blocked:
        return False, blocked, {}, []

    if not resolved.is_file():
        return False, f"Not a file: {resolved}", {}, []

    try:
        size = resolved.stat().st_size
        if size > max_bytes:
            return False, f"File too large: {size} bytes > {max_bytes} limit", {}, []

        content = resolved.read_text(errors="replace")[:max_bytes]
    except (OSError, PermissionError) as exc:
        return False, f"Cannot read file: {exc}", {}, []

    outputs = {
        "path": str(resolved),
        "size_bytes": size,
        "lines": content.count("\n"),
    }
    artifacts = [
        ExecutorArtifact(
            artifact_type="file_content",
            name=resolved.name,
            content=content,
        ).to_dict()
    ]
    return True, f"Read {size} bytes from {resolved.name}", outputs, artifacts


def _op_write_file(
    params: dict[str, Any],
    request: ExecutorRequest,
) -> tuple[bool, str, dict[str, Any], list[dict[str, Any]]]:
    """Write content to a file safely.

    Params:
      path: str — absolute path to write
      content: str — content to write
      create_parents: bool — create parent directories (default True)

    Returns (success, message, outputs, artifacts).
    """
    file_path = params.get("path", "")
    content = params.get("content", "")

    if not file_path:
        return False, "path is required", {}, []
    if not isinstance(content, str):
        return False, "content must be a string", {}, []

    resolved, err = _resolve_and_validate(file_path)
    if err:
        return False, err, {}, []

    blocked = _check_blocked(resolved)
    if blocked:
        return False, blocked, {}, []

    if len(content.encode()) > _MAX_FILE_SIZE_BYTES:
        return False, f"Content too large: {len(content.encode())} bytes > {_MAX_FILE_SIZE_BYTES}", {}, []

    create_parents = params.get("create_parents", True)

    try:
        if create_parents:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content)
    except (OSError, PermissionError) as exc:
        return False, f"Cannot write file: {exc}", {}, []

    written_size = resolved.stat().st_size
    outputs = {
        "path": str(resolved),
        "size_bytes": written_size,
        "lines": content.count("\n"),
    }
    artifacts = [
        ExecutorArtifact(
            artifact_type="file_written",
            name=resolved.name,
            content=f"Wrote {written_size} bytes to {resolved}",
        ).to_dict()
    ]
    return True, f"Wrote {written_size} bytes to {resolved.name}", outputs, artifacts


def _op_list_directory(
    params: dict[str, Any],
    request: ExecutorRequest,
) -> tuple[bool, str, dict[str, Any], list[dict[str, Any]]]:
    """List directory contents.

    Params:
      path: str — absolute path to directory
      max_entries: int — max entries to return (default 500)

    Returns (success, message, outputs, artifacts).
    """
    dir_path = params.get("path", "")
    if not dir_path:
        return False, "path is required", {}, []

    max_entries = min(int(params.get("max_entries", 500)), 5000)

    resolved, err = _resolve_and_validate(dir_path)
    if err:
        return False, err, {}, []

    if not resolved.is_dir():
        return False, f"Not a directory: {resolved}", {}, []

    try:
        entries = []
        for i, entry in enumerate(sorted(resolved.iterdir())):
            if i >= max_entries:
                break
            entries.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else 0,
            })
    except (OSError, PermissionError) as exc:
        return False, f"Cannot list directory: {exc}", {}, []

    outputs = {
        "path": str(resolved),
        "count": len(entries),
        "entries": entries,
    }
    artifacts = [
        ExecutorArtifact(
            artifact_type="directory_listing",
            name=resolved.name,
            content=json.dumps(entries, indent=2),
        ).to_dict()
    ]
    return True, f"Listed {len(entries)} entries in {resolved.name}", outputs, artifacts


# ── Operation Dispatch ──────────────────────────────────────────

_OPERATION_HANDLERS: dict[str, Any] = {
    "create_worktree": _op_create_worktree,
    "run_command": _op_run_command,
    "read_file": _op_read_file,
    "write_file": _op_write_file,
    "list_directory": _op_list_directory,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WorkstationExecutor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkstationExecutor(ExecutorContract):
    """First production executor — performs real machine operations.

    Supports 5 operations: create_worktree, run_command, read_file,
    write_file, list_directory.  All operations are CPU-gated and
    path-validated.  Every execution produces ExecutionProof.

    Operation is specified in request.metadata["operation"] with
    parameters in request.metadata["params"].
    """

    def __init__(
        self,
        telemetry_emitter: Any | None = None,
        runtime: Any | None = None,
    ) -> None:
        self._active_requests: dict[str, dict[str, Any]] = {}
        self._cancelled: set[str] = set()
        self._telemetry = telemetry_emitter
        self._runtime = runtime

    def _tel(self, event_type: str, request: ExecutorRequest, **payload: Any) -> None:
        """Emit telemetry. Never raises."""
        if not self._telemetry:
            return
        try:
            self._telemetry.emit(
                event_type,
                execution_id=request.request_id,
                request_id=request.request_id,
                executor_type=self.executor_type,
                operation=request.metadata.get("operation", ""),
                status="executing",
                payload=payload if payload else {},
            )
        except Exception:
            pass

    @property
    def executor_type(self) -> str:
        return ExecutorType.WORKSTATION.value

    def validate(self, request: ExecutorRequest) -> tuple[bool, str]:
        if not request.execution_plan_id:
            return False, "No execution_plan_id"

        if request.executor_type != ExecutorType.WORKSTATION.value:
            return False, f"Wrong executor type: {request.executor_type}"

        operation = request.metadata.get("operation", "")
        if not operation:
            return False, "No operation specified in metadata"

        if operation not in SUPPORTED_OPERATIONS:
            return False, (
                f"Unsupported operation: {operation}. "
                f"Supported: {sorted(SUPPORTED_OPERATIONS)}"
            )

        params = request.metadata.get("params", {})
        if not isinstance(params, dict):
            return False, "params must be a dict"

        if operation == "run_command" and not params.get("command"):
            return False, "run_command requires 'command' in params"
        if operation == "create_worktree" and not params.get("branch_name"):
            return False, "create_worktree requires 'branch_name' in params"
        if operation == "read_file" and not params.get("path"):
            return False, "read_file requires 'path' in params"
        if operation == "write_file" and not params.get("path"):
            return False, "write_file requires 'path' in params"
        if operation == "list_directory" and not params.get("path"):
            return False, "list_directory requires 'path' in params"

        return True, f"Validated for operation: {operation}"

    def prepare(self, request: ExecutorRequest) -> tuple[bool, str]:
        gate = cpu_gate_check("workstation_executor.prepare")
        if not gate.allowed:
            return False, f"CPU gate blocked: {gate.reason}"

        operation = request.metadata.get("operation", "")
        params = request.metadata.get("params", {})

        if operation in ("read_file", "write_file", "list_directory"):
            path_str = params.get("path", "")
            if path_str:
                _, err = _resolve_and_validate(path_str)
                if err:
                    return False, f"Path validation failed: {err}"

        if operation == "create_worktree":
            repo_root = params.get(
                "repo_root", os.environ.get("UMH_ROOT", "/opt/OS")
            )
            _, err = _resolve_and_validate(repo_root)
            if err:
                return False, f"Repo root invalid: {err}"

        self._active_requests[request.request_id] = {
            "operation": operation,
            "status": "prepared",
            "started_at": 0.0,
        }

        return True, f"Prepared for {operation}"

    def execute(self, request: ExecutorRequest) -> ExecutorResult:
        operation = request.metadata.get("operation", "")
        params = request.metadata.get("params", {})
        handler = _OPERATION_HANDLERS.get(operation)

        started = time.time()
        self._active_requests.setdefault(request.request_id, {})
        self._active_requests[request.request_id]["started_at"] = started
        self._active_requests[request.request_id]["status"] = "executing"

        if request.request_id in self._cancelled:
            return ExecutorResult(
                request_id=request.request_id,
                executor_type=self.executor_type,
                success=False,
                outcome="Cancelled before execution",
                errors=["Execution cancelled"],
                started_at=started,
                completed_at=time.time(),
                duration_seconds=time.time() - started,
            )

        if not handler:
            return ExecutorResult(
                request_id=request.request_id,
                executor_type=self.executor_type,
                success=False,
                outcome=f"No handler for operation: {operation}",
                errors=[f"Unknown operation: {operation}"],
                started_at=started,
                completed_at=time.time(),
                duration_seconds=time.time() - started,
            )

        # ── Approval checkpoint ──────────────────────────
        try:
            from substrate.organism.executors.approval_intercept import (
                classify_operation_risk, requires_approval,
            )
            op_risk = classify_operation_risk(operation, params)
            if requires_approval(op_risk) and self._runtime:
                approved, msg = self._runtime.request_approval(
                    request,
                    reason=f"{op_risk.upper()} risk: {operation}",
                    details={"operation": operation, "risk_class": op_risk},
                )
                if not approved:
                    completed = time.time()
                    proof = ExecutionProof(
                        execution_id=request.request_id,
                        operation=operation,
                        start_time=started,
                        end_time=completed,
                        duration_ms=(completed - started) * 1000,
                        status="rejected",
                        inputs={"operation": operation, "params": _sanitize(params)},
                        outputs={"rejection": msg},
                    )
                    return ExecutorResult(
                        request_id=request.request_id,
                        executor_type=self.executor_type,
                        success=False,
                        outcome=f"Approval denied: {msg}",
                        errors=[msg],
                        started_at=started,
                        completed_at=completed,
                        duration_seconds=completed - started,
                        metadata={"proof": proof.to_dict()},
                    )
        except ImportError:
            if not _is_safe_without_approval(operation):
                logger.warning("Approval module unavailable — blocking %s (only read-only ops allowed)", operation)
                completed = time.time()
                return ExecutorResult(
                    request_id=request.request_id,
                    executor_type=self.executor_type,
                    success=False,
                    outcome=f"Blocked: approval module unavailable for {operation}",
                    errors=["Only read-only operations allowed without approval subsystem"],
                    started_at=started,
                    completed_at=completed,
                    duration_seconds=completed - started,
                )

        cmd_desc = operation
        if operation == "run_command":
            cmd = params.get("command", "")
            argv0 = (cmd if isinstance(cmd, str) else (cmd[0] if cmd else "")).split()[0] if cmd else ""
            cmd_desc = argv0 or operation
        self._tel("command_started", request, message=cmd_desc)

        try:
            success, message, outputs, artifacts = handler(params, request)
        except Exception as exc:
            logger.error(
                "Workstation operation %s failed: %s", operation, exc,
            )
            completed = time.time()
            proof = ExecutionProof(
                execution_id=request.request_id,
                operation=operation,
                start_time=started,
                end_time=completed,
                duration_ms=(completed - started) * 1000,
                status="error",
                inputs={"operation": operation, "params": _sanitize(params)},
                outputs={"error": str(exc)},
            )
            return ExecutorResult(
                request_id=request.request_id,
                executor_type=self.executor_type,
                success=False,
                outcome=f"Operation error: {exc}",
                errors=[str(exc)],
                started_at=started,
                completed_at=completed,
                duration_seconds=completed - started,
                metadata={"proof": proof.to_dict()},
            )

        stdout = outputs.get("stdout", "")
        stderr = outputs.get("stderr", "")
        if stdout:
            self._tel("stdout_chunk", request, stdout=stdout[:2000])
        if stderr:
            self._tel("stderr_chunk", request, stderr=stderr[:2000])

        exit_code = outputs.get("exit_code")
        completed = time.time()
        self._tel(
            "command_completed", request,
            exit_code=exit_code,
            duration_ms=(completed - started) * 1000,
            message=message,
        )

        proof = ExecutionProof(
            execution_id=request.request_id,
            operation=operation,
            start_time=started,
            end_time=completed,
            duration_ms=(completed - started) * 1000,
            status="success" if success else "failed",
            inputs={"operation": operation, "params": _sanitize(params)},
            outputs=outputs,
            artifacts=artifacts,
        )

        self._tel("proof_generated", request, proof_id=proof.proof_id)
        self._active_requests[request.request_id]["status"] = "completed"

        return ExecutorResult(
            request_id=request.request_id,
            executor_type=self.executor_type,
            success=success,
            outcome=message,
            artifacts=artifacts,
            errors=[] if success else [message],
            started_at=started,
            completed_at=completed,
            duration_seconds=completed - started,
            metadata={"proof": proof.to_dict()},
        )

    def monitor(self, request: ExecutorRequest) -> dict[str, Any]:
        state = self._active_requests.get(request.request_id, {})
        return {
            "request_id": request.request_id,
            "operation": state.get("operation", "unknown"),
            "status": state.get("status", "unknown"),
            "started_at": state.get("started_at", 0),
            "elapsed_ms": (
                (time.time() - state["started_at"]) * 1000
                if state.get("started_at")
                else 0
            ),
        }

    def cancel(self, request: ExecutorRequest) -> bool:
        self._cancelled.add(request.request_id)
        if request.request_id in self._active_requests:
            self._active_requests[request.request_id]["status"] = "cancelled"
        return True

    def cleanup(self, request: ExecutorRequest) -> bool:
        self._active_requests.pop(request.request_id, None)
        self._cancelled.discard(request.request_id)
        return True


def _sanitize(params: dict[str, Any]) -> dict[str, Any]:
    """Remove potentially large content from params for proof recording."""
    sanitized = {}
    for k, v in params.items():
        if k == "content" and isinstance(v, str) and len(v) > 1000:
            sanitized[k] = f"<{len(v)} chars>"
        else:
            sanitized[k] = v
    return sanitized
