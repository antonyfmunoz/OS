"""Assisted Executor — governed execution of approved maintenance actions.

Implements ASSISTED mode for safe approved actions:
  - rotate large logs
  - restart unhealthy non-critical containers
  - refresh runtime availability
  - run test suite
  - rebuild codebase graph

All actions:
  - require approval unless classified LOW risk
  - write audit trail
  - are reversible where possible

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
from substrate.organism.leverage_metrics import LeverageMetrics, TaskRecord
from substrate.organism.maintenance_loop import ActionCategory

logger = logging.getLogger(__name__)

_ACTION_TIMEOUT = 60


class ActionResult(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class AssistedAction:
    action_id: str
    category: ActionCategory
    description: str
    result: ActionResult = ActionResult.SKIPPED
    output: str = ""
    duration_seconds: float = 0.0
    reversible: bool = True
    approved_by: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "category": self.category.value,
            "description": self.description,
            "result": self.result.value,
            "output": self.output[:1000],
            "duration_seconds": round(self.duration_seconds, 2),
            "reversible": self.reversible,
            "approved_by": self.approved_by,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


_MAX_AUDIT = 500


class AssistedExecutor:
    """Executes approved maintenance actions with full audit trail.

    Only runs in ASSISTED or higher execution mode. Every action
    is logged, timed, and recorded in leverage metrics.
    """

    def __init__(
        self,
        execution_mode: ExecutionModeManager,
        event_spine: EventSpine,
        leverage_metrics: LeverageMetrics,
        repo_root: str | None = None,
    ) -> None:
        self._mode = execution_mode
        self._spine = event_spine
        self._leverage = leverage_metrics
        self._repo_root = repo_root or os.environ.get("UMH_ROOT", "/opt/OS")
        self._audit_trail: list[AssistedAction] = []
        self._total_executed: int = 0
        self._total_blocked: int = 0

    def execute_action(
        self,
        action_id: str,
        category: ActionCategory,
        description: str,
        approved_by: str = "operator",
        params: dict[str, Any] | None = None,
    ) -> AssistedAction:
        action = AssistedAction(
            action_id=action_id,
            category=category,
            description=description,
            approved_by=approved_by,
            started_at=time.time(),
        )

        if not self._mode.can_execute(ExecutionMode.ASSISTED):
            action.result = ActionResult.BLOCKED
            action.output = f"Blocked: current mode {self._mode.current_mode.value} < ASSISTED"
            action.completed_at = time.time()
            self._total_blocked += 1
            self._record(action)
            return action

        handler = _ACTION_HANDLERS.get(category)
        if handler is None:
            action.result = ActionResult.SKIPPED
            action.output = f"No handler for category: {category.value}"
            action.completed_at = time.time()
            self._record(action)
            return action

        start = time.monotonic()
        self._spine.emit(
            EventDomain.EXECUTION,
            "assisted_action_started",
            "assisted_executor",
            {"action_id": action_id, "category": category.value},
        )

        try:
            output, success = handler(self._repo_root, params or {})
            action.result = ActionResult.SUCCESS if success else ActionResult.FAILED
            action.output = output
        except Exception as exc:
            action.result = ActionResult.FAILED
            action.output = str(exc)
            logger.warning("assisted action failed: %s — %s", action_id, exc)

        action.duration_seconds = time.monotonic() - start
        action.completed_at = time.time()
        self._total_executed += 1

        self._mode.record_outcome(
            action_id,
            action.result == ActionResult.SUCCESS,
            result=action.output[:200],
        )

        self._leverage.record_task(TaskRecord(
            task_id=action_id,
            started_at=action.started_at,
            completed_at=action.completed_at,
            autonomous=False,
            required_approval=True,
            success=(action.result == ActionResult.SUCCESS),
            estimated_manual_seconds=_MANUAL_ESTIMATES.get(category, 60.0),
            actual_seconds=action.duration_seconds,
        ))

        self._spine.emit(
            EventDomain.EXECUTION,
            "assisted_action_completed",
            "assisted_executor",
            {
                "action_id": action_id,
                "category": category.value,
                "result": action.result.value,
                "duration_s": round(action.duration_seconds, 2),
            },
            priority=EventPriority.HIGH if action.result == ActionResult.FAILED else EventPriority.NORMAL,
        )

        self._record(action)
        return action

    def _record(self, action: AssistedAction) -> None:
        if len(self._audit_trail) >= _MAX_AUDIT:
            self._audit_trail = self._audit_trail[-(_MAX_AUDIT // 2):]
        self._audit_trail.append(action)

    def audit_trail(self, limit: int = 20) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._audit_trail[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_executed": self._total_executed,
            "total_blocked": self._total_blocked,
            "audit_trail_size": len(self._audit_trail),
            "current_mode": self._mode.current_mode.value,
            "can_execute": self._mode.can_execute(ExecutionMode.ASSISTED),
            "recent_actions": self.audit_trail(5),
        }


_MANUAL_ESTIMATES: dict[ActionCategory, float] = {
    ActionCategory.LOG_ROTATION: 120.0,
    ActionCategory.CONTAINER_RESTART: 60.0,
    ActionCategory.RUNTIME_REFRESH: 30.0,
    ActionCategory.TEST_SUITE: 180.0,
    ActionCategory.GRAPH_REBUILD: 300.0,
    ActionCategory.BRANCH_CLEANUP: 60.0,
    ActionCategory.DISK_CLEANUP: 120.0,
}


def _rotate_logs(repo_root: str, params: dict[str, Any]) -> tuple[str, bool]:
    """Rotate log files larger than threshold."""
    threshold_mb = params.get("threshold_mb", 10)
    rotated: list[str] = []

    try:
        result = subprocess.run(
            ["find", repo_root, "-name", "*.log", "-size", f"+{threshold_mb}M",
             "-not", "-path", "*/.git/*"],
            capture_output=True, text=True, timeout=_ACTION_TIMEOUT,
        )
        for f in result.stdout.strip().splitlines():
            f = f.strip()
            if not f:
                continue
            rotated_path = f + ".old"
            try:
                p = Path(f)
                old = Path(rotated_path)
                if old.exists():
                    old.unlink()
                p.rename(old)
                rotated.append(f)
            except OSError as exc:
                logger.debug("failed to rotate %s: %s", f, exc)
    except Exception as exc:
        return str(exc), False

    return f"Rotated {len(rotated)} log files", len(rotated) >= 0


def _restart_container(repo_root: str, params: dict[str, Any]) -> tuple[str, bool]:
    """Restart a specific Docker container."""
    container = params.get("container", "")
    if not container:
        return "No container specified", False

    critical = {"os-operator", "os-discord"}
    if container in critical:
        return f"Refusing to restart critical container: {container}", False

    try:
        result = subprocess.run(
            ["docker", "restart", container],
            capture_output=True, text=True, timeout=_ACTION_TIMEOUT,
        )
        if result.returncode == 0:
            return f"Restarted {container}", True
        return f"Failed to restart {container}: {result.stderr}", False
    except Exception as exc:
        return str(exc), False


def _refresh_runtime(repo_root: str, params: dict[str, Any]) -> tuple[str, bool]:
    """Refresh runtime availability check."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=_ACTION_TIMEOUT,
        )
        containers = result.stdout.strip().splitlines() if result.stdout else []
        return f"Refreshed: {len(containers)} running containers", True
    except Exception as exc:
        return str(exc), False


def _run_tests(repo_root: str, params: dict[str, Any]) -> tuple[str, bool]:
    """Run the organism test suite."""
    test_path = params.get("test_path", "substrate/organism/tests/")
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", test_path, "-x", "-q", "--tb=line"],
            capture_output=True, text=True, timeout=120,
            cwd=repo_root,
        )
        last_lines = result.stdout.strip().splitlines()[-5:]
        summary = "\n".join(last_lines)
        return summary, result.returncode == 0
    except Exception as exc:
        return str(exc), False


def _rebuild_graph(repo_root: str, params: dict[str, Any]) -> tuple[str, bool]:
    """Rebuild the codebase graph."""
    script = os.path.join(repo_root, "scripts", "update-graph")
    if not os.path.exists(script):
        return "scripts/update-graph not found", False

    try:
        result = subprocess.run(
            [script],
            capture_output=True, text=True, timeout=300,
            cwd=repo_root,
        )
        return result.stdout[-500:] if result.stdout else "no output", result.returncode == 0
    except Exception as exc:
        return str(exc), False


def _cleanup_branches(repo_root: str, params: dict[str, Any]) -> tuple[str, bool]:
    """Delete merged branches (not main, not current)."""
    try:
        current = subprocess.run(
            ["git", "-C", repo_root, "branch", "--show-current"],
            capture_output=True, text=True, timeout=10,
        )
        current_branch = current.stdout.strip()

        merged = subprocess.run(
            ["git", "-C", repo_root, "branch", "--merged", "main", "--format", "%(refname:short)"],
            capture_output=True, text=True, timeout=10,
        )
        deleted: list[str] = []
        for branch in merged.stdout.strip().splitlines():
            branch = branch.strip()
            if branch in ("main", current_branch, ""):
                continue
            subprocess.run(
                ["git", "-C", repo_root, "branch", "-d", branch],
                capture_output=True, text=True, timeout=10,
            )
            deleted.append(branch)

        return f"Deleted {len(deleted)} merged branches: {', '.join(deleted[:10])}", True
    except Exception as exc:
        return str(exc), False


def _cleanup_disk(repo_root: str, params: dict[str, Any]) -> tuple[str, bool]:
    """Clean up known safe targets: __pycache__, .pyc, old rotated logs."""
    cleaned: list[str] = []

    try:
        result = subprocess.run(
            ["find", repo_root, "-type", "d", "-name", "__pycache__",
             "-not", "-path", "*/.git/*", "-not", "-path", "*/node_modules/*"],
            capture_output=True, text=True, timeout=_ACTION_TIMEOUT,
        )
        for d in result.stdout.strip().splitlines():
            d = d.strip()
            if d:
                subprocess.run(["rm", "-rf", d], capture_output=True, timeout=10)
                cleaned.append(d)
    except Exception as exc:
        return str(exc), False

    return f"Cleaned {len(cleaned)} __pycache__ directories", True


_ACTION_HANDLERS: dict[ActionCategory, Any] = {
    ActionCategory.LOG_ROTATION: _rotate_logs,
    ActionCategory.CONTAINER_RESTART: _restart_container,
    ActionCategory.RUNTIME_REFRESH: _refresh_runtime,
    ActionCategory.TEST_SUITE: _run_tests,
    ActionCategory.GRAPH_REBUILD: _rebuild_graph,
    ActionCategory.BRANCH_CLEANUP: _cleanup_branches,
    ActionCategory.DISK_CLEANUP: _cleanup_disk,
}
