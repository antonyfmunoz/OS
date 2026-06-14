"""AgentExecutor — first governed LLM/Claude Code executor (Phase 17A).

Runs cognitive tasks through Claude Code CLI inside the full ExecutorContract
lifecycle: validate → prepare → execute → monitor → cancel → cleanup.

No special runtime path. No bypass. No direct ungated subprocess.
The agent operates inside UMH governance exactly like WorkstationExecutor.

Supported operation:
  - run_task: execute a bounded coding/analysis task via Claude Code CLI

Stubs (future phases):
  - continue_task, get_status, cancel_task

Security:
  - All subprocess calls through gated_subprocess_run() (CPU Gate Law)
  - Path validation against approved roots
  - Telemetry redaction on all output
  - Approval intercepts for high/critical operations
  - Bounded output capture (1 MiB)
  - Process cleanup on cancel/timeout

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from substrate.execution.cpu_gate import cpu_gate_check, gated_popen, gated_subprocess_run
from substrate.organism.executor_runtime import (
    ExecutorArtifact,
    ExecutorContract,
    ExecutorRequest,
    ExecutorResult,
    ExecutorType,
)

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_APPROVED_ROOTS: list[str] = [
    "/workspace",
    os.environ.get("UMH_ROOT", "/opt/OS"),
]

_MAX_OUTPUT_BYTES: int = 1 * 1024 * 1024  # 1 MiB
_DEFAULT_TIMEOUT: float = 300.0  # 5 minutes
_MAX_TIMEOUT: float = 900.0  # 15 minutes
_MAX_TASK_LENGTH: int = 10_000  # chars
_MAX_CONTEXT_LINES: int = 40

_HIGH_RISK_PATTERNS: tuple[str, ...] = (
    r"git\s+push",
    r"--force",
    r"git\s+branch\s+-[dD]",
    r"\brm\s+-r",
    r"\brm\s+-f",
    r"DROP\s+TABLE",
    r"flyctl\s+deploy",
    r"docker\s+rm",
    r"docker\s+stop",
    r"chmod\s+777",
    r"\.env",
    r"credentials",
    r"\.ssh",
)

_HIGH_RISK_RE = re.compile("|".join(_HIGH_RISK_PATTERNS), re.IGNORECASE)

SUPPORTED_OPERATIONS = frozenset({"run_task"})

_STUB_OPERATIONS = frozenset({"continue_task", "get_status", "cancel_task"})


# ── Path Validation ────────────────────────────────────────────


_FORBIDDEN_PATH_SEGMENTS = frozenset({
    ".env", ".ssh", "credentials", ".git/config",
    "secrets", ".gnupg", ".aws",
})


def _validate_working_dir(path_str: str) -> tuple[Path, str]:
    """Validate a working directory is in approved roots. Returns (path, error).

    Rejects the repo root itself — agents must work in a worktree or subdir.
    Rejects paths containing secrets directories.
    """
    try:
        resolved = Path(path_str).resolve()
    except (ValueError, OSError) as exc:
        return Path(), f"Cannot resolve path: {exc}"

    repo_root = Path(os.environ.get("UMH_ROOT", "/opt/OS")).resolve()
    if resolved == repo_root:
        return Path(), (
            f"Cannot use repo root {repo_root} as working directory. "
            "Use a worktree or subdirectory."
        )

    path_parts = str(resolved).lower()
    for forbidden in _FORBIDDEN_PATH_SEGMENTS:
        if forbidden in path_parts:
            return Path(), f"Path contains forbidden segment '{forbidden}'"

    approved = [Path(r).resolve() for r in _APPROVED_ROOTS]
    for root in approved:
        try:
            resolved.relative_to(root)
            if resolved.is_dir():
                return resolved, ""
            return Path(), f"Not a directory: {resolved}"
        except ValueError:
            continue

    return Path(), f"Path {resolved} outside approved roots: {[str(r) for r in approved]}"


# ── Risk Classification ────────────────────────────────────────


_RISK_LEVELS = ("low", "medium", "high", "critical")


def classify_agent_task_risk(task: str) -> str:
    """Classify agent task risk from the task description text.

    All agent tasks are minimum "medium" — LLM execution is inherently
    higher risk than deterministic operations. The regex patterns escalate
    to "high" as defense-in-depth; approval intercepts are the real gate.

    Returns: "medium", "high", or "critical".
    """
    if _HIGH_RISK_RE.search(task):
        return "high"

    mutating_keywords = ("delete", "remove", "drop", "destroy", "overwrite", "reset")
    task_lower = task.lower()
    if any(kw in task_lower for kw in mutating_keywords):
        return "high"

    return "medium"


# ── Runtime Context Builder ───────────────────────────────────


def build_agent_runtime_context(
    snapshot_dict: dict[str, Any] | None,
    request: ExecutorRequest,
) -> str:
    """Build a bounded context block for the agent prompt.

    Summarizes the runtime state into a compact string the agent
    can reference without being overwhelmed.
    """
    lines: list[str] = [
        "=== UMH RUNTIME CONTEXT ===",
        f"Execution ID: {request.request_id}",
        f"Risk Class: {request.risk_class}",
    ]

    if not snapshot_dict:
        lines.append("Runtime state: unavailable")
        return "\n".join(lines[:_MAX_CONTEXT_LINES])

    summary = snapshot_dict.get("summary", {})
    lines.append(
        f"Worktrees: {summary.get('worktree_count', 0)} | "
        f"Processes: {summary.get('process_count', 0)} | "
        f"Containers: {summary.get('container_count', 0)} | "
        f"Executions: {summary.get('execution_count', 0)}"
    )

    repos = snapshot_dict.get("repositories", [])
    if repos:
        repo = repos[0]
        lines.append(
            f"Git: {repo.get('current_branch', '?')} | "
            f"Dirty: {repo.get('dirty', False)} | "
            f"Untracked: {repo.get('untracked_count', 0)}"
        )

    worktrees = snapshot_dict.get("worktrees", [])
    if worktrees:
        lines.append("Active worktrees:")
        for wt in worktrees[:5]:
            lines.append(f"  - {wt.get('branch', '?')} @ {wt.get('path', '?')}")
        if len(worktrees) > 5:
            lines.append(f"  ... +{len(worktrees) - 5} more")

    containers = snapshot_dict.get("containers", [])
    if containers:
        lines.append("Containers:")
        for c in containers[:8]:
            lines.append(f"  - {c.get('name', '?')}: {c.get('status', '?')}")

    lines.append("=== END CONTEXT ===")
    return "\n".join(lines[:_MAX_CONTEXT_LINES])


# ── Agent Prompt Assembly ─────────────────────────────────────

_AGENT_SYSTEM_PROMPT = """\
You are executing a governed task inside UMH (Universal Meta Harness).
You must follow these rules:

GOVERNANCE:
- Only modify files within the approved working directory.
- Do not access .env, credentials, .ssh, or any secret files.
- Do not run git push, force push, or branch delete without explicit approval.
- Do not deploy to production.
- Do not kill processes or stop containers.
- If you encounter something requiring elevated privileges, STOP and report it.

OUTPUT FORMAT (required — always end your response with this block):
AGENT_RESULT:
status: success|failed|needs_approval|blocked
summary: <one-line summary>
files_changed: <comma-separated list or none>
commands_run: <comma-separated list or none>
proof_notes: <what was verified>
remaining_blockers: <any blockers or none>

Do not output chain-of-thought. Only summaries, actions, and results.
"""


def _build_agent_prompt(
    task: str,
    runtime_context: str,
    working_dir: str,
) -> str:
    """Assemble the full agent prompt with task + context + rules."""
    return f"""{_AGENT_SYSTEM_PROMPT}

WORKING DIRECTORY: {working_dir}

{runtime_context}

TASK:
{task}
"""


# ── Output Parser ─────────────────────────────────────────────

_RESULT_PATTERN = re.compile(
    r"AGENT_RESULT:\s*\n"
    r"status:\s*(.+)\n"
    r"summary:\s*(.+)\n"
    r"files_changed:\s*(.+)\n"
    r"commands_run:\s*(.+)\n"
    r"proof_notes:\s*(.+)\n"
    r"remaining_blockers:\s*(.+)",
    re.MULTILINE,
)


@dataclass
class AgentTaskResult:
    """Parsed result from agent output."""
    status: str = "unknown"
    summary: str = ""
    files_changed: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    proof_notes: str = ""
    remaining_blockers: str = ""
    raw_output: str = ""
    exit_code: int = -1

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "files_changed": self.files_changed,
            "commands_run": self.commands_run,
            "proof_notes": self.proof_notes,
            "remaining_blockers": self.remaining_blockers,
            "exit_code": self.exit_code,
        }


def parse_agent_output(raw: str, exit_code: int = 0) -> AgentTaskResult:
    """Parse agent output into structured result."""
    result = AgentTaskResult(raw_output=raw, exit_code=exit_code)

    if exit_code != 0:
        result.status = "failed"
        result.summary = f"Agent exited with code {exit_code}"
        return result

    match = _RESULT_PATTERN.search(raw)
    if match:
        result.status = match.group(1).strip()
        result.summary = match.group(2).strip()
        files_str = match.group(3).strip()
        result.files_changed = (
            [f.strip() for f in files_str.split(",") if f.strip() and f.strip() != "none"]
        )
        cmds_str = match.group(4).strip()
        result.commands_run = (
            [c.strip() for c in cmds_str.split(",") if c.strip() and c.strip() != "none"]
        )
        result.proof_notes = match.group(5).strip()
        result.remaining_blockers = match.group(6).strip()
    else:
        result.status = "success" if exit_code == 0 else "failed"
        result.summary = raw[-500:] if len(raw) > 500 else raw

    return result


# ── Agent Execution Proof ─────────────────────────────────────


@dataclass
class AgentExecutionProof:
    """Proof record for an agent execution."""

    proof_id: str = field(
        default_factory=lambda: f"agprf-{uuid4().hex[:12]}"
    )
    execution_id: str = ""
    executor_type: str = ExecutorType.AGENT.value
    agent_backend: str = "claude_code"
    task: str = ""
    runtime_snapshot_id: str = ""
    agent_summary: str = ""
    commands_run: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    approval_events: list[dict[str, Any]] = field(default_factory=list)
    exit_code: int = -1
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "execution_id": self.execution_id,
            "executor_type": self.executor_type,
            "agent_backend": self.agent_backend,
            "task": self.task[:500],
            "runtime_snapshot_id": self.runtime_snapshot_id,
            "agent_summary": self.agent_summary,
            "commands_run": self.commands_run,
            "files_changed": self.files_changed,
            "approval_events": self.approval_events,
            "exit_code": self.exit_code,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
        }


# ── Telemetry Helpers ─────────────────────────────────────────


def _redact_output(text: str) -> str:
    """Strip potential secrets from agent output before telemetry.

    Fail-closed: on any redaction failure, suppress the output entirely.
    """
    try:
        from substrate.organism.executors.execution_telemetry import (
            redact_telemetry_payload,
        )
        redacted = redact_telemetry_payload({"output": text})
        return str(redacted.get("output", "<redaction failed — output suppressed>"))
    except Exception:
        logger.warning("Telemetry redaction unavailable — suppressing agent output")
        return "<redaction unavailable — output suppressed>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AgentExecutor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AgentExecutor(ExecutorContract):
    """First governed cognitive worker — executes tasks via Claude Code CLI.

    Operation is specified in request.metadata["operation"] ("run_task")
    with parameters in request.metadata["params"]:
      - task (str, required): the task description
      - worktree_path (str, required): worktree or subdir to work in
      - timeout_seconds (float, optional): max execution time

    Security invariants:
      - risk_class always computed server-side, never from request body
      - All tasks require operator approval (minimum risk: medium)
      - CLI invoked with --disallowedTools to mechanically block destructive ops
      - Working directory must be a worktree/subdir, never repo root
      - Subprocess via gated_popen for cancellability
      - Output redaction fail-closed (suppressed on error)
    """

    def __init__(
        self,
        telemetry_emitter: Any | None = None,
        runtime: Any | None = None,
    ) -> None:
        self._active_requests: dict[str, dict[str, Any]] = {}
        self._cancelled: set[str] = set()
        self._active_pids: dict[str, int] = {}
        self._telemetry = telemetry_emitter
        self._runtime = runtime

    def _tel(self, event_type: str, request: ExecutorRequest, **payload: Any) -> None:
        """Emit telemetry event. Never raises."""
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
        return ExecutorType.AGENT.value

    # ── Lifecycle: validate ──────────────────────────

    def validate(self, request: ExecutorRequest) -> tuple[bool, str]:
        if not request.execution_plan_id:
            return False, "No execution_plan_id"

        if request.executor_type != ExecutorType.AGENT.value:
            return False, f"Wrong executor type: {request.executor_type}"

        operation = request.metadata.get("operation", "")
        if not operation:
            return False, "No operation specified in metadata"

        if operation in _STUB_OPERATIONS:
            return False, f"Operation '{operation}' is stub-only (not yet implemented)"

        if operation not in SUPPORTED_OPERATIONS:
            return False, (
                f"Unsupported operation: {operation}. "
                f"Supported: {sorted(SUPPORTED_OPERATIONS)}"
            )

        params = request.metadata.get("params", {})
        if not isinstance(params, dict):
            return False, "params must be a dict"

        task = params.get("task", "")
        if not task or not task.strip():
            return False, "Empty task"

        if len(task) > _MAX_TASK_LENGTH:
            return False, f"Task too long: {len(task)} chars > {_MAX_TASK_LENGTH} limit"

        return True, f"Validated for agent operation: {operation}"

    # ── Lifecycle: prepare ───────────────────────────

    def prepare(self, request: ExecutorRequest) -> tuple[bool, str]:
        gate = cpu_gate_check("agent_executor.prepare")
        if not gate.allowed:
            return False, f"CPU gate blocked: {gate.reason}"

        params = request.metadata.get("params", {})
        working_dir = params.get("worktree_path") or params.get("repo_path", "")

        if not working_dir:
            return False, (
                "No working directory specified. "
                "Provide worktree_path — repo root is not allowed."
            )

        resolved, err = _validate_working_dir(working_dir)
        if err:
            return False, f"Working directory invalid: {err}"

        self._active_requests[request.request_id] = {
            "operation": "run_task",
            "status": "prepared",
            "started_at": 0.0,
            "working_dir": str(resolved),
        }

        self._tel("agent_task_requested", request, task=params.get("task", "")[:200])
        return True, f"Prepared agent execution in {resolved}"

    # ── Lifecycle: execute ───────────────────────────

    def execute(self, request: ExecutorRequest) -> ExecutorResult:
        params = request.metadata.get("params", {})
        task = params.get("task", "")
        operation = request.metadata.get("operation", "run_task")

        started = time.time()
        state = self._active_requests.setdefault(request.request_id, {})
        state["started_at"] = started
        state["status"] = "executing"

        # ── Cancel check ──
        if request.request_id in self._cancelled:
            self._tel("agent_task_cancelled", request)
            return self._fail_result(request, started, "Cancelled before execution", ["Cancelled"])

        # ── Fetch runtime snapshot ──
        snapshot_dict, snapshot_id = self._get_runtime_snapshot()
        runtime_context = build_agent_runtime_context(snapshot_dict, request)
        self._tel("agent_context_built", request, snapshot_id=snapshot_id)

        # ── Risk assessment + approval ──
        task_risk = classify_agent_task_risk(task)
        request.risk_class = task_risk

        # All agent tasks require approval — LLM execution is never auto-approved
        approval_events: list[dict[str, Any]] = []
        if self._runtime:
            try:
                approved, msg = self._runtime.request_approval(
                    request,
                    reason=f"{task_risk.upper()} risk agent task",
                    details={"operation": operation, "risk_class": task_risk, "task": task[:200]},
                )
                approval_events.append({
                    "action": "approval_requested",
                    "risk_class": task_risk,
                    "approved": approved,
                    "message": msg,
                    "timestamp": time.time(),
                })
                if not approved:
                    self._tel("agent_approval_required", request, decision="denied")
                    proof = self._build_proof(
                        request, task, snapshot_id, started,
                        status="rejected", approval_events=approval_events,
                    )
                    return self._fail_result(
                        request, started, f"Approval denied: {msg}", [msg],
                        proof=proof,
                    )
                self._tel("agent_approval_required", request, decision="approved")
            except Exception as exc:
                logger.warning("Approval check failed — blocking agent task: %s", exc)
                return self._fail_result(
                    request, started,
                    f"Blocked: approval check failed: {exc}",
                    ["Approval subsystem error"],
                )
        else:
            logger.warning("No runtime for approval — blocking agent task")
            return self._fail_result(
                request, started,
                "Blocked: no runtime available for approval",
                ["Approval subsystem unavailable"],
            )

        # ── Build prompt ──
        working_dir = state.get("working_dir", _REPO_ROOT)
        prompt = _build_agent_prompt(task, runtime_context, working_dir)

        # ── Invoke Claude Code CLI ──
        self._tel("agent_task_started", request, working_dir=working_dir)

        timeout = min(
            float(params.get("timeout_seconds", _DEFAULT_TIMEOUT)),
            _MAX_TIMEOUT,
        )

        cmd = [
            "claude", "--print",
            "--disallowedTools",
            "Bash(rm *),Bash(git push*),Bash(git branch -D*),Bash(flyctl*),Bash(docker rm*),Bash(docker stop*)",
            "--add-dir", working_dir,
            prompt,
        ]

        import subprocess as _subprocess

        proc = gated_popen(
            cmd,
            caller="agent_executor.run_task",
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            text=True,
            cwd=working_dir,
        )

        if proc is None:
            proof = self._build_proof(
                request, task, snapshot_id, started,
                status="blocked", approval_events=approval_events,
            )
            return self._fail_result(
                request, started, "CPU gate blocked agent execution",
                ["CPU gate denied"], proof=proof,
            )

        self._active_pids[request.request_id] = proc.pid

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except _subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            self._active_pids.pop(request.request_id, None)
            proof = self._build_proof(
                request, task, snapshot_id, started,
                status="timeout", approval_events=approval_events,
            )
            return self._fail_result(
                request, started,
                f"Agent timed out after {timeout}s",
                [f"Timeout after {timeout}s"],
                proof=proof,
            )

        result_returncode = proc.returncode

        # ── Parse output ──
        stdout = (stdout or "")[:_MAX_OUTPUT_BYTES]
        stderr = (stderr or "")[:_MAX_OUTPUT_BYTES]
        exit_code = result_returncode

        if request.request_id in self._cancelled:
            self._tel("agent_task_cancelled", request)
            proof = self._build_proof(
                request, task, snapshot_id, started,
                status="cancelled", exit_code=exit_code,
                approval_events=approval_events,
            )
            return self._fail_result(
                request, started, "Cancelled during execution", ["Cancelled"],
                proof=proof,
            )

        # Emit output telemetry (redacted)
        if stdout:
            self._tel("agent_output_chunk", request, output=_redact_output(stdout[:2000]))
        if stderr:
            self._tel("agent_output_chunk", request, stream="stderr", output=_redact_output(stderr[:1000]))

        # ── Detect high-risk actions in output ──
        if _HIGH_RISK_RE.search(stdout):
            self._tel("agent_action_detected", request, risk="high", snippet=_redact_output(stdout[:500]))

        # ── Parse structured result ──
        parsed = parse_agent_output(stdout, exit_code)

        completed = time.time()
        proof = self._build_proof(
            request, task, snapshot_id, started,
            status=parsed.status,
            exit_code=exit_code,
            agent_summary=parsed.summary,
            commands_run=parsed.commands_run,
            files_changed=parsed.files_changed,
            approval_events=approval_events,
        )

        success = exit_code == 0 and parsed.status in ("success", "unknown")

        event_type = "agent_task_completed" if success else "agent_task_failed"
        self._tel(
            event_type, request,
            exit_code=exit_code,
            status=parsed.status,
            summary=parsed.summary[:200],
            duration_ms=(completed - started) * 1000,
        )

        state["status"] = "completed" if success else "failed"
        self._active_pids.pop(request.request_id, None)

        artifacts = [
            ExecutorArtifact(
                artifact_type="agent_result",
                name="agent_output",
                content=_redact_output(stdout[:5000]),
            ).to_dict(),
        ]

        return ExecutorResult(
            request_id=request.request_id,
            executor_type=self.executor_type,
            success=success,
            outcome=parsed.summary or f"Agent exited with code {exit_code}",
            artifacts=artifacts,
            errors=[] if success else [parsed.summary or f"exit code {exit_code}"],
            started_at=started,
            completed_at=completed,
            duration_seconds=completed - started,
            metadata={
                "proof": proof.to_dict(),
                "agent_result": parsed.to_dict(),
                "runtime_snapshot_id": snapshot_id,
            },
        )

    # ── Lifecycle: monitor ───────────────────────────

    def monitor(self, request: ExecutorRequest) -> dict[str, Any]:
        state = self._active_requests.get(request.request_id, {})
        elapsed = 0.0
        if state.get("started_at"):
            elapsed = (time.time() - state["started_at"]) * 1000
        return {
            "request_id": request.request_id,
            "operation": "run_task",
            "status": state.get("status", "unknown"),
            "started_at": state.get("started_at", 0),
            "elapsed_ms": elapsed,
            "agent_backend": "claude_code",
            "working_dir": state.get("working_dir", ""),
        }

    # ── Lifecycle: cancel ────────────────────────────

    def cancel(self, request: ExecutorRequest) -> bool:
        self._cancelled.add(request.request_id)
        if request.request_id in self._active_requests:
            self._active_requests[request.request_id]["status"] = "cancelled"

        pid = self._active_pids.get(request.request_id)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                logger.info("Sent SIGTERM to agent process %d", pid)
            except ProcessLookupError:
                pass
            except OSError as exc:
                logger.warning("Failed to kill agent process %d: %s", pid, exc)
            self._active_pids.pop(request.request_id, None)

        self._tel("agent_task_cancelled", request)
        return True

    # ── Lifecycle: cleanup ───────────────────────────

    def cleanup(self, request: ExecutorRequest) -> bool:
        self._active_requests.pop(request.request_id, None)
        self._cancelled.discard(request.request_id)
        self._active_pids.pop(request.request_id, None)
        return True

    # ── Internal helpers ─────────────────────────────

    def _get_runtime_snapshot(self) -> tuple[dict[str, Any] | None, str]:
        """Fetch latest runtime snapshot. Returns (dict, snapshot_id)."""
        try:
            from substrate.organism.runtime_state_registry import (
                get_runtime_state_registry,
            )
            registry = get_runtime_state_registry()
            state = registry.get_runtime_state()
            return state, state.get("snapshot_id", "")
        except Exception as exc:
            logger.debug("Runtime snapshot unavailable: %s", exc)
            return None, ""

    def _build_proof(
        self,
        request: ExecutorRequest,
        task: str,
        snapshot_id: str,
        started: float,
        status: str = "pending",
        exit_code: int = -1,
        agent_summary: str = "",
        commands_run: list[str] | None = None,
        files_changed: list[str] | None = None,
        approval_events: list[dict[str, Any]] | None = None,
    ) -> AgentExecutionProof:
        completed = time.time()
        return AgentExecutionProof(
            execution_id=request.request_id,
            task=task[:500],
            runtime_snapshot_id=snapshot_id,
            agent_summary=agent_summary,
            commands_run=commands_run or [],
            files_changed=files_changed or [],
            approval_events=approval_events or [],
            exit_code=exit_code,
            start_time=started,
            end_time=completed,
            duration_ms=(completed - started) * 1000,
            status=status,
        )

    def _fail_result(
        self,
        request: ExecutorRequest,
        started: float,
        outcome: str,
        errors: list[str],
        proof: AgentExecutionProof | None = None,
    ) -> ExecutorResult:
        completed = time.time()
        metadata: dict[str, Any] = {}
        if proof:
            metadata["proof"] = proof.to_dict()
        return ExecutorResult(
            request_id=request.request_id,
            executor_type=self.executor_type,
            success=False,
            outcome=outcome,
            errors=errors,
            started_at=started,
            completed_at=completed,
            duration_seconds=completed - started,
            metadata=metadata,
        )
