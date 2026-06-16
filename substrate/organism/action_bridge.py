"""Action Bridge — governed composition of catalog, observation, and execution.

Translates operator action requests into WorkPacket → ExecutionCoordinator →
WorkstationExecutor calls. No new execution paths — pure composition of
existing Phase 13/15A/25 infrastructure.

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import logging
import os
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from substrate.organism.action_catalog import (
    ActionCatalog,
    ActionDefinition,
    ActionRiskLevel,
    ActionStatus,
)

logger = logging.getLogger(__name__)

_PARAM_ALLOWLISTS: dict[str, re.Pattern[str]] = {
    "string": re.compile(r"^[A-Za-z0-9_./-]{1,128}$"),
    "integer": re.compile(r"^[0-9]{1,5}$"),
    "container_name": re.compile(r"^[A-Za-z0-9_.-]{1,128}$"),
    "path": re.compile(r"^[A-Za-z0-9_./-]{1,256}$"),
    "choice": re.compile(r"^[A-Za-z0-9_./-]{1,128}$"),
    "boolean": re.compile(r"^(true|false|1|0)$"),
}
_ALLOWED_PATH_ROOTS = ("/opt/OS", "/tmp")
_LEADING_DASH = re.compile(r"^-")


def _under_allowed_root(resolved: str) -> bool:
    for root in _ALLOWED_PATH_ROOTS:
        root_abs = os.path.realpath(root)
        if resolved == root_abs or resolved.startswith(root_abs + os.sep):
            return True
    return False


@dataclass
class ActionRequest:
    """Operator's request to perform a governed action."""

    request_id: str = field(default_factory=lambda: f"actreq-{uuid4().hex[:12]}")
    action_id: str = ""
    parameters: dict[str, str] = field(default_factory=dict)
    source: str = "cockpit"
    requested_by: str = "operator"
    requested_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_id": self.action_id,
            "parameters": self.parameters,
            "source": self.source,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
        }


@dataclass
class ActionResult:
    """Result of a governed action execution."""

    request_id: str = ""
    action_id: str = ""
    status: str = ActionStatus.PENDING.value
    execution_plan_id: str = ""
    precondition_results: list[dict[str, Any]] = field(default_factory=list)
    executor_result: dict[str, Any] = field(default_factory=dict)
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""
    requested_by: str = "operator"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_id": self.action_id,
            "status": self.status,
            "execution_plan_id": self.execution_plan_id,
            "precondition_results": self.precondition_results,
            "executor_result": self.executor_result,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "requested_by": self.requested_by,
        }


class ActionBridge:
    """Bridges action catalog to execution infrastructure.

    Composes:
      - ActionCatalog (action lookup)
      - WorkspaceObservationEngine (precondition checks — Phase 25)
      - ExecutionCoordinator (plan lifecycle — Phase 13)
      - WorkstationExecutor (actual execution — Phase 15A)

    No new execution paths. Every action routes through existing infrastructure.
    """

    def __init__(
        self,
        catalog: ActionCatalog | None = None,
        coordinator: Any | None = None,
    ) -> None:
        self._catalog = catalog or ActionCatalog()
        self._coordinator = coordinator
        self._results: deque[ActionResult] = deque(maxlen=100)
        self._results_by_id: dict[str, ActionResult] = {}

    def _get_coordinator(self) -> Any:
        if self._coordinator is None:
            try:
                from substrate.organism.execution_coordinator import (
                    get_execution_coordinator,
                )

                self._coordinator = get_execution_coordinator()
            except Exception:
                logger.debug("ExecutionCoordinator not available")
        return self._coordinator

    def execute_action(self, request: ActionRequest) -> ActionResult:
        """Full governed action lifecycle."""
        result = ActionResult(
            request_id=request.request_id,
            action_id=request.action_id,
            requested_by=request.requested_by,
            started_at=time.time(),
        )

        action = self._catalog.resolve_by_id(request.action_id)
        if not action:
            result.status = ActionStatus.FAILED.value
            result.error = f"Unknown action: {request.action_id}"
            result.completed_at = time.time()
            self._store_result(result)
            return result

        valid, reason = self._validate_parameters(action, request.parameters)
        if not valid:
            result.status = ActionStatus.FAILED.value
            result.error = reason
            result.completed_at = time.time()
            self._store_result(result)
            return result

        result.status = ActionStatus.PRECONDITION_CHECK.value
        preconditions = self.check_preconditions(action, request.parameters)
        result.precondition_results = preconditions
        failed_preconditions = [p for p in preconditions if not p.get("passed", False)]
        if failed_preconditions:
            result.status = ActionStatus.BLOCKED.value
            result.error = "; ".join(
                p.get("reason", "precondition failed") for p in failed_preconditions
            )
            result.completed_at = time.time()
            self._store_result(result)
            return result

        command = self._build_command(action, request.parameters)
        if command is None:
            result.status = ActionStatus.FAILED.value
            result.error = "Failed to build command from template"
            result.completed_at = time.time()
            self._store_result(result)
            return result

        coordinator = self._get_coordinator()
        if not coordinator:
            result.status = ActionStatus.FAILED.value
            result.error = "ExecutionCoordinator not available"
            result.completed_at = time.time()
            self._store_result(result)
            return result

        wp_id = f"action-wp-{request.request_id}"
        plan = coordinator.create_plan(
            source_workpacket_id=wp_id,
            target_executor="workstation",
            risk_class=action.risk_level,
            description=f"Action: {action.name} ({command[:80]})",
            metadata={
                "action_id": action.action_id,
                "action_request_id": request.request_id,
                "source": request.source,
                "operation": action.operation,
                "params": {"command": command},
            },
        )
        result.execution_plan_id = plan.execution_plan_id

        if plan.approval_state == "approved":
            return self._enqueue_and_dispatch(result, plan, coordinator)

        result.status = ActionStatus.AWAITING_APPROVAL.value
        self._store_result(result)
        logger.info(
            "Action %s awaiting approval (plan %s, risk %s)",
            request.action_id,
            plan.execution_plan_id[:12],
            action.risk_level,
        )
        return result

    def check_preconditions(
        self,
        action: ActionDefinition,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Check action preconditions against live workspace state."""
        if not action.preconditions:
            return []

        snapshot = self._get_workspace_snapshot()
        results = []

        for precond in action.preconditions:
            check_result = self._evaluate_precondition(precond, params, snapshot)
            results.append(check_result)

        return results

    def _evaluate_precondition(
        self,
        precond: Any,
        params: dict[str, str],
        snapshot: Any,
    ) -> dict[str, Any]:
        """Evaluate a single precondition against workspace state."""
        container_name = params.get("container_name", "")

        if precond.check_type == "container_running":
            if not snapshot:
                return {
                    "check_type": precond.check_type,
                    "passed": True,
                    "reason": "No observation data — assuming met",
                }
            containers = snapshot.get("containers", [])
            running = any(
                c.get("container_name") == container_name and c.get("status", "").startswith("Up")
                for c in containers
            )
            return {
                "check_type": precond.check_type,
                "passed": running == precond.expected,
                "reason": (
                    f"Container {container_name} is " + ("running" if running else "not running")
                ),
            }

        if precond.check_type == "container_stopped":
            if not snapshot:
                return {
                    "check_type": precond.check_type,
                    "passed": True,
                    "reason": "No observation data — assuming met",
                }
            containers = snapshot.get("containers", [])
            stopped = not any(
                c.get("container_name") == container_name and c.get("status", "").startswith("Up")
                for c in containers
            )
            return {
                "check_type": precond.check_type,
                "passed": stopped == precond.expected,
                "reason": (
                    f"Container {container_name} is " + ("stopped" if stopped else "running")
                ),
            }

        if precond.check_type == "container_exists":
            if not snapshot:
                return {
                    "check_type": precond.check_type,
                    "passed": True,
                    "reason": "No observation data — assuming met",
                }
            containers = snapshot.get("containers", [])
            exists = any(c.get("container_name") == container_name for c in containers)
            return {
                "check_type": precond.check_type,
                "passed": exists == precond.expected,
                "reason": (f"Container {container_name} " + ("exists" if exists else "not found")),
            }

        if precond.check_type == "port_free":
            port = params.get("port", precond.target)
            if not snapshot:
                return {
                    "check_type": precond.check_type,
                    "passed": True,
                    "reason": "No observation data — assuming met",
                }
            previews = snapshot.get("previews", [])
            in_use = any(str(p.get("port")) == str(port) for p in previews)
            return {
                "check_type": precond.check_type,
                "passed": (not in_use) == precond.expected,
                "reason": f"Port {port} is {'in use' if in_use else 'free'}",
            }

        return {
            "check_type": precond.check_type,
            "passed": True,
            "reason": f"Unknown check type: {precond.check_type} — assuming met",
        }

    def _get_workspace_snapshot(self) -> dict[str, Any] | None:
        """Get latest workspace observation snapshot."""
        try:
            from substrate.meta_ide.workspace_observation import (
                WorkspaceObservationEngine,
            )

            engine = WorkspaceObservationEngine()
            latest = engine.latest()
            if latest:
                return latest.to_dict()
        except Exception:
            logger.debug("WorkspaceObservationEngine not available")
        return None

    def _build_command(
        self,
        action: ActionDefinition,
        params: dict[str, str],
    ) -> str | None:
        """Substitute parameters into command template.

        Uses strict per-type allowlists instead of char denylists.
        Rejects leading dashes (argument injection) and validates
        paths resolve under allowed roots.
        """
        if not action.command_template:
            return None

        merged = {}
        for p in action.parameters:
            value = params.get(p.name, p.default)
            if not value and p.required:
                return None
            if not value:
                merged[p.name] = ""
                continue

            if _LEADING_DASH.match(value):
                logger.warning("Param %s starts with dash (arg injection): %s", p.name, value)
                return None

            allowlist = _PARAM_ALLOWLISTS.get(p.param_type, _PARAM_ALLOWLISTS["string"])
            if not allowlist.match(value):
                logger.warning("Param %s failed allowlist for type %s: %s", p.name, p.param_type, value)
                return None

            if p.param_type == "path" or p.name.endswith("_path"):
                resolved = os.path.realpath(value)
                if not _under_allowed_root(resolved):
                    logger.warning("Path param %s resolves outside allowed roots: %s", p.name, resolved)
                    return None

            merged[p.name] = value

        try:
            return action.command_template.format_map(merged)
        except (KeyError, ValueError) as exc:
            logger.warning("Template substitution failed: %s", exc)
            return None

    def _validate_parameters(
        self,
        action: ActionDefinition,
        params: dict[str, str],
    ) -> tuple[bool, str]:
        """Validate required params present and choices valid."""
        for p in action.parameters:
            value = params.get(p.name, p.default)
            if p.required and not value:
                return False, f"Missing required parameter: {p.name}"
            if value and p.choices and value not in p.choices:
                return False, (f"Invalid value for {p.name}: {value}. Valid: {p.choices}")
        return True, "ok"

    def _enqueue_and_dispatch(
        self,
        result: ActionResult,
        plan: Any,
        coordinator: Any,
    ) -> ActionResult:
        """Enqueue an approved plan and dispatch it."""
        result.status = ActionStatus.EXECUTING.value
        coordinator.enqueue_plan(plan.execution_plan_id)

        dispatched = coordinator.dispatch_next()
        if not dispatched:
            result.status = ActionStatus.FAILED.value
            result.error = "Dispatch failed — no executor available"
            result.completed_at = time.time()
            self._store_result(result)
            return result

        result.status = ActionStatus.COMPLETED.value
        result.completed_at = time.time()
        self._store_result(result)
        return result

    def approve_and_dispatch(
        self, execution_plan_id: str, operator_id: str = "operator"
    ) -> ActionResult | None:
        """Approve a pending action and dispatch it."""
        for r in self._results:
            if r.execution_plan_id == execution_plan_id and r.requested_by == operator_id:
                coordinator = self._get_coordinator()
                if not coordinator:
                    return None
                coordinator.approve_plan(execution_plan_id)
                return self._enqueue_and_dispatch(
                    r, type("P", (), {"execution_plan_id": execution_plan_id})(), coordinator
                )
        return None

    def list_available_actions(self, category: str | None = None) -> list[dict[str, Any]]:
        """Actions enriched with current precondition state."""
        actions = self._catalog.list_actions(category=category)
        result = []
        for action in actions:
            entry = action.to_dict()
            entry["precondition_state"] = self.check_preconditions(action, {})
            result.append(entry)
        return result

    def get_action_status(
        self, request_id: str, operator_id: str = "operator"
    ) -> ActionResult | None:
        result = self._results_by_id.get(request_id)
        if result and result.requested_by == operator_id:
            return result
        return None

    def history(
        self, limit: int = 20, operator_id: str = "operator"
    ) -> list[dict[str, Any]]:
        items = [r for r in self._results if r.requested_by == operator_id]
        items.reverse()
        return [r.to_dict() for r in items[:limit]]

    def _store_result(self, result: ActionResult) -> None:
        self._results.append(result)
        self._results_by_id[result.request_id] = result
