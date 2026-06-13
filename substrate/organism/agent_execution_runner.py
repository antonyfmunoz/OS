"""Agent Execution Runner — invokes coding agents inside governed sandboxes.

Takes an approved WorkPacket through:
  Plan → Implement → Validate → (Review) → Complete

Execution modes:
  VALIDATE_ONLY        — run validation commands only (Phase 1 behavior)
  IMPLEMENT            — invoke coding agent, skip validation
  IMPLEMENT_AND_VALIDATE — full loop: agent implements, then validate

All execution artifacts are persisted as immutable records.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class AgentExecutionPlan:
    """Generated before any implementation begins."""

    plan_id: str = field(default_factory=lambda: f"plan-{uuid4().hex[:8]}")
    packet_id: str = ""
    objectives: list[str] = field(default_factory=list)
    files_expected: list[str] = field(default_factory=list)
    validation_strategy: str = ""
    rollback_strategy: str = ""
    risk_assessment: str = ""
    created_at: float = field(default_factory=time.time)
    approved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionRecord:
    """Immutable record of a single execution run."""

    record_id: str = field(default_factory=lambda: f"exec-{uuid4().hex[:8]}")
    packet_id: str = ""
    sandbox_id: str = ""
    mode: str = "validate_only"
    plan: AgentExecutionPlan | None = None

    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    duration_seconds: float = 0.0

    agent_output: str = ""
    files_changed: list[str] = field(default_factory=list)
    diff_summary: str = ""
    commits: list[str] = field(default_factory=list)

    validation_results: list[dict[str, Any]] = field(default_factory=list)
    all_validations_passed: bool = False

    outcome: str = ""
    success: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.plan:
            result["plan"] = self.plan.to_dict()
        return result


@dataclass
class FailureReport:
    """Created when implementation fails."""

    report_id: str = field(default_factory=lambda: f"fail-{uuid4().hex[:8]}")
    packet_id: str = ""
    root_cause: str = ""
    failing_command: str = ""
    logs: str = ""
    recommended_action: str = ""
    retry_count: int = 0
    max_retries: int = 2
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentExecutionRunner:
    """Orchestrates coding agent execution inside governed sandboxes."""

    MAX_RETRIES = 2
    AGENT_TIMEOUT = 300

    def __init__(self) -> None:
        self._records: dict[str, ExecutionRecord] = {}
        self._plans: dict[str, AgentExecutionPlan] = {}
        self._failures: dict[str, FailureReport] = {}

    def generate_plan(self, packet) -> AgentExecutionPlan:
        """Generate an execution plan from a WorkPacket."""
        objectives = []
        if packet.user_intent:
            objectives.append(packet.user_intent)
        if packet.desired_end_state:
            objectives.append(f"End state: {packet.desired_end_state}")

        files_expected = []
        if packet.constraints:
            for c in packet.constraints:
                if c.startswith("file:"):
                    files_expected.append(c[5:].strip())

        validation_strategy = packet.validation_plan or "run pytest, check imports"
        rollback_strategy = packet.rollback_plan or "git reset to base commit in sandbox"
        risk_assessment = packet.risk_class or "low"

        plan = AgentExecutionPlan(
            packet_id=packet.packet_id,
            objectives=objectives,
            files_expected=files_expected,
            validation_strategy=validation_strategy,
            rollback_strategy=rollback_strategy,
            risk_assessment=risk_assessment,
        )

        if packet.success_criteria:
            plan.objectives.extend(
                [f"Acceptance: {c}" for c in packet.success_criteria]
            )

        self._plans[plan.plan_id] = plan
        self._persist_plan(plan)
        return plan

    def execute(
        self,
        packet,
        mode: str = "validate_only",
        plan: AgentExecutionPlan | None = None,
    ) -> ExecutionRecord:
        """Execute a work packet in the specified mode.

        Modes:
          validate_only          — run validation commands only
          implement              — invoke coding agent only
          implement_and_validate — agent implements, then validate
        """
        from substrate.organism.worktree_sandbox import (
            SandboxManager, SandboxStatus, SandboxValidationResult,
        )
        from substrate.execution.cpu_gate import gated_subprocess_run

        record = ExecutionRecord(
            packet_id=packet.packet_id,
            mode=mode,
            plan=plan,
        )

        sandbox_mgr = SandboxManager()

        try:
            slug = (packet.title or packet.packet_id)[:30]
            sandbox = sandbox_mgr.create_sandbox(
                candidate_id=packet.packet_id,
                candidate_slug=slug,
                agent_type="operator_loop",
            )
            record.sandbox_id = sandbox.sandbox_id
            sandbox_mgr.update_status(
                sandbox.sandbox_id, SandboxStatus("executing")
            )

            if mode in ("implement", "implement_and_validate"):
                agent_result = self._run_coding_agent(
                    packet, sandbox.worktree_path, plan
                )
                record.agent_output = agent_result.get("output", "")

                if agent_result.get("error"):
                    record.error = agent_result["error"]
                    record.success = False
                    self._create_failure_report(
                        packet.packet_id,
                        root_cause=agent_result["error"],
                        failing_command="coding agent invocation",
                        logs=record.agent_output[:2000],
                    )
                    sandbox_mgr.update_status(
                        sandbox.sandbox_id, SandboxStatus.VALIDATION_FAILED
                    )
                    record.completed_at = time.time()
                    record.duration_seconds = round(
                        record.completed_at - record.started_at, 2
                    )
                    self._records[record.record_id] = record
                    self._persist_record(record)
                    return record

            changed, diff, commits = self._capture_changes(
                sandbox.worktree_path
            )
            record.files_changed = changed
            record.diff_summary = diff
            record.commits = commits

            if mode in ("validate_only", "implement_and_validate"):
                results = self._run_validation(
                    packet, sandbox.worktree_path, sandbox_mgr,
                    sandbox.sandbox_id,
                )
                record.validation_results = results
                record.all_validations_passed = all(
                    r.get("passed", False) for r in results
                )

                if record.all_validations_passed:
                    sandbox_mgr.update_status(
                        sandbox.sandbox_id, SandboxStatus.VALIDATED
                    )
                else:
                    sandbox_mgr.update_status(
                        sandbox.sandbox_id, SandboxStatus.VALIDATION_FAILED
                    )
                    self._create_failure_report(
                        packet.packet_id,
                        root_cause="validation failed",
                        failing_command=next(
                            (r["command"] for r in results if not r.get("passed")),
                            "unknown",
                        ),
                        logs="\n".join(
                            r.get("stderr", "") for r in results if not r.get("passed")
                        )[:2000],
                    )
            else:
                sandbox_mgr.update_status(
                    sandbox.sandbox_id, SandboxStatus.VALIDATED
                )

            if mode in ("implement", "implement_and_validate"):
                if record.all_validations_passed or mode == "implement":
                    record.success = True
                    record.outcome = (
                        f"Implementation complete. "
                        f"{len(changed)} files changed, "
                        f"{len(commits)} commits."
                    )
                else:
                    record.success = False
                    record.outcome = "Implementation complete but validation failed."
            else:
                record.success = record.all_validations_passed
                record.outcome = (
                    "Validation passed." if record.success
                    else "Validation failed."
                )

        except Exception as e:
            record.error = str(e)
            record.success = False
            logger.warning(
                "AgentExecutionRunner failed for %s: %s",
                packet.packet_id, e,
            )
            self._create_failure_report(
                packet.packet_id,
                root_cause=str(e),
                failing_command="execution runner",
                logs="",
            )

        record.completed_at = time.time()
        record.duration_seconds = round(
            record.completed_at - record.started_at, 2
        )
        self._records[record.record_id] = record
        self._persist_record(record)
        return record

    def _run_coding_agent(
        self, packet, worktree_path: str, plan: AgentExecutionPlan | None
    ) -> dict[str, str]:
        """Invoke Claude Code in the sandbox worktree."""
        from substrate.execution.cpu_gate import gated_subprocess_run

        prompt_parts = [
            f"Task: {packet.user_intent}",
        ]
        if packet.desired_end_state:
            prompt_parts.append(f"Desired end state: {packet.desired_end_state}")
        if packet.success_criteria:
            prompt_parts.append(
                "Acceptance criteria:\n" +
                "\n".join(f"- {c}" for c in packet.success_criteria)
            )
        if packet.constraints:
            prompt_parts.append(
                "Constraints:\n" +
                "\n".join(f"- {c}" for c in packet.constraints)
            )
        if packet.failure_criteria:
            prompt_parts.append(
                "Non-goals:\n" +
                "\n".join(f"- {c}" for c in packet.failure_criteria)
            )
        if plan and plan.objectives:
            prompt_parts.append(
                "Plan objectives:\n" +
                "\n".join(f"- {o}" for o in plan.objectives)
            )

        prompt_parts.append(
            "After making changes, commit them with a descriptive message. "
            "Do not push. Do not create PRs."
        )

        full_prompt = "\n\n".join(prompt_parts)

        cli_path = self._resolve_cli_path()
        if not cli_path:
            return {
                "output": "",
                "error": "Claude Code CLI not found — cannot invoke coding agent",
            }

        env = self._get_agent_env()

        cmd = [
            cli_path,
            "--print",
            "--output-format", "text",
            "--max-turns", "30",
            "--permission-mode", "auto",
            "--verbose",
            full_prompt,
        ]

        logger.info(
            "[AgentExecutionRunner] invoking agent in %s", worktree_path
        )

        result = gated_subprocess_run(
            cmd,
            caller="agent_execution_runner",
            timeout=self.AGENT_TIMEOUT,
            cwd=worktree_path,
            env=env,
            capture_output=True,
            text=True,
        )

        if result is None:
            return {
                "output": "",
                "error": "CPU gate blocked agent execution",
            }

        output = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode != 0:
            return {
                "output": output[:5000],
                "error": (
                    f"Agent exited with code {result.returncode}. "
                    f"stderr: {stderr[:1000]}"
                ),
            }

        return {"output": output[:5000], "error": ""}

    def _capture_changes(
        self, worktree_path: str
    ) -> tuple[list[str], str, list[str]]:
        """Capture files changed, diff summary, and commits in the sandbox."""
        from substrate.execution.cpu_gate import gated_subprocess_run

        changed_files: list[str] = []
        diff_summary = ""
        commits: list[str] = []

        result = gated_subprocess_run(
            "git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only HEAD",
            shell=True, cwd=worktree_path,
            caller="agent_runner_diff", timeout=15,
        )
        if result and result.returncode == 0:
            changed_files = [f for f in result.stdout.strip().split("\n") if f]

        if not changed_files:
            result = gated_subprocess_run(
                "git diff --name-only",
                shell=True, cwd=worktree_path,
                caller="agent_runner_unstaged", timeout=15,
            )
            if result and result.returncode == 0:
                changed_files = [
                    f for f in result.stdout.strip().split("\n") if f
                ]

        result = gated_subprocess_run(
            "git diff --stat HEAD~1 HEAD 2>/dev/null || git diff --stat",
            shell=True, cwd=worktree_path,
            caller="agent_runner_stat", timeout=15,
        )
        if result and result.returncode == 0:
            diff_summary = result.stdout[:3000]

        result = gated_subprocess_run(
            "git log --oneline --no-walk HEAD 2>/dev/null",
            shell=True, cwd=worktree_path,
            caller="agent_runner_log", timeout=10,
        )
        if result and result.returncode == 0 and result.stdout.strip():
            commits = [result.stdout.strip()]

        return changed_files, diff_summary, commits

    def _run_validation(
        self, packet, worktree_path: str, sandbox_mgr, sandbox_id: str,
    ) -> list[dict[str, Any]]:
        """Run validation commands and track results."""
        from substrate.organism.worktree_sandbox import SandboxValidationResult
        from substrate.execution.cpu_gate import gated_subprocess_run

        commands = self._derive_validation_commands(packet)
        results: list[dict[str, Any]] = []

        for cmd_entry in commands:
            cmd = cmd_entry["command"]
            label = cmd_entry.get("label", cmd[:60])
            t0 = time.time()

            result = gated_subprocess_run(
                cmd, shell=True, cwd=worktree_path,
                capture_output=True, text=True,
                timeout=120, caller="agent_runner_validate",
            )

            duration = round(time.time() - t0, 2)
            passed = result is not None and result.returncode == 0

            step = {
                "command": cmd,
                "label": label,
                "exit_code": result.returncode if result else -1,
                "stdout": (result.stdout[:2000] if result else "")[:2000],
                "stderr": (result.stderr[:2000] if result else "blocked")[:2000],
                "passed": passed,
                "duration_seconds": duration,
                "timestamp": time.time(),
            }
            results.append(step)

            sandbox_mgr.add_validation_result(
                sandbox_id,
                SandboxValidationResult(
                    passed=passed,
                    command=cmd,
                    stdout=(result.stdout[:500] if result else ""),
                    stderr=(result.stderr[:500] if result else "blocked"),
                    exit_code=result.returncode if result else -1,
                    duration_seconds=duration,
                ),
            )

        return results

    def _derive_validation_commands(self, packet) -> list[dict[str, str]]:
        """Derive validation commands from work packet context."""
        commands: list[dict[str, str]] = []

        commands.append({
            "command": (
                "python3 -c \"import sys; sys.path.insert(0,'/opt/OS'); "
                "import substrate; print('substrate import ok')\""
            ),
            "label": "substrate import check",
        })

        if packet.validation_plan:
            plan_lower = packet.validation_plan.lower()
            if "test" in plan_lower or "pytest" in plan_lower:
                commands.append({
                    "command": "python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -30",
                    "label": "run test suite",
                })
            if "lint" in plan_lower or "ruff" in plan_lower:
                commands.append({
                    "command": "python3 -m ruff check . --select E,F --ignore E501 2>&1 | tail -20",
                    "label": "ruff lint check",
                })
            if "typecheck" in plan_lower or "mypy" in plan_lower:
                commands.append({
                    "command": "python3 -m mypy substrate/ --ignore-missing-imports 2>&1 | tail -20",
                    "label": "type check",
                })
            if "build" in plan_lower:
                commands.append({
                    "command": "cd cockpit && npx tsc --noEmit 2>&1 | tail -20",
                    "label": "TypeScript build",
                })

        if len(commands) <= 1:
            commands.append({
                "command": "python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -30",
                "label": "default test suite",
            })

        return commands

    def _create_failure_report(
        self,
        packet_id: str,
        root_cause: str,
        failing_command: str,
        logs: str,
    ) -> FailureReport:
        """Create and persist a failure report."""
        existing = self._failures.get(packet_id)
        retry_count = (existing.retry_count + 1) if existing else 0

        report = FailureReport(
            packet_id=packet_id,
            root_cause=root_cause,
            failing_command=failing_command,
            logs=logs[:3000],
            retry_count=retry_count,
            max_retries=self.MAX_RETRIES,
            recommended_action=(
                "retry" if retry_count < self.MAX_RETRIES
                else "escalate to operator"
            ),
        )
        self._failures[packet_id] = report
        self._persist_failure(report)
        return report

    def get_plan(self, plan_id: str) -> AgentExecutionPlan | None:
        return self._plans.get(plan_id)

    def get_record(self, record_id: str) -> ExecutionRecord | None:
        return self._records.get(record_id)

    def get_failure(self, packet_id: str) -> FailureReport | None:
        return self._failures.get(packet_id)

    def get_records_for_packet(
        self, packet_id: str
    ) -> list[ExecutionRecord]:
        return [
            r for r in self._records.values()
            if r.packet_id == packet_id
        ]

    def _resolve_cli_path(self) -> str:
        """Find the Claude Code CLI binary."""
        candidates = [
            os.path.expanduser("~/.claude/local/claude"),
            "/usr/local/bin/claude",
            os.path.expanduser("~/.npm-global/bin/claude"),
        ]
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c

        from shutil import which
        found = which("claude")
        if found:
            return found

        return ""

    def _get_agent_env(self) -> dict[str, str]:
        """Build environment for the agent subprocess."""
        env = dict(os.environ)
        env["CLAUDE_CODE_ENTRYPOINT"] = "agent-execution-runner"

        try:
            from adapters.models.cc_sdk import _get_subprocess_env
            sdk_env = _get_subprocess_env()
            env.update(sdk_env)
        except Exception:
            pass

        return env

    def _persist_plan(self, plan: AgentExecutionPlan) -> None:
        """Write plan to disk."""
        plan_dir = os.path.join(
            _repo_root(), "data", "umh", "execution", "plans"
        )
        os.makedirs(plan_dir, exist_ok=True)
        path = os.path.join(plan_dir, f"{plan.plan_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(plan.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.debug("persist plan failed: %s", e)

    def _persist_record(self, record: ExecutionRecord) -> None:
        """Write execution record to disk."""
        record_dir = os.path.join(
            _repo_root(), "data", "umh", "execution", "records"
        )
        os.makedirs(record_dir, exist_ok=True)
        path = os.path.join(record_dir, f"{record.record_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(record.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.debug("persist record failed: %s", e)

    def _persist_failure(self, report: FailureReport) -> None:
        """Write failure report to disk."""
        fail_dir = os.path.join(
            _repo_root(), "data", "umh", "execution", "failures"
        )
        os.makedirs(fail_dir, exist_ok=True)
        path = os.path.join(fail_dir, f"{report.report_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.debug("persist failure failed: %s", e)
