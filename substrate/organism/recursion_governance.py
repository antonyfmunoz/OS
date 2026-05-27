"""Recursion Governance — bounded recursive execution control.

All recursive orchestration must be bounded. The RecursionGovernor
enforces hard limits on:
  - recursion depth
  - spawned objectives
  - work units per mission
  - runtime budget (USD)
  - wall-clock time
  - autonomous execution scope

Each execution class has distinct authority rules. The governor
acts as a circuit breaker: every recursive operation checks limits
before proceeding. If a limit is exceeded, the operation is blocked
and an escalation is triggered.

Kill-switch support: the governor can be externally signaled to
halt all autonomous execution immediately.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.execution_economy import ExecutionClass

logger = logging.getLogger(__name__)


class EscalationLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCK = "block"
    KILL = "kill"


class RecursionApproval(str, Enum):
    NONE = "none"
    NOTIFY = "notify"
    APPROVE = "approve"
    BLOCK = "block"


_DEFAULT_APPROVAL_MAP: dict[ExecutionClass, RecursionApproval] = {
    ExecutionClass.DETERMINISTIC: RecursionApproval.NONE,
    ExecutionClass.AGENT: RecursionApproval.NOTIFY,
    ExecutionClass.ADVISOR_DELEGATION: RecursionApproval.NOTIFY,
    ExecutionClass.RECURSIVE_IMPROVEMENT: RecursionApproval.APPROVE,
    ExecutionClass.EXTERNAL_LEVERAGE: RecursionApproval.APPROVE,
    ExecutionClass.PRODUCTION_IMPACT: RecursionApproval.BLOCK,
}


@dataclass
class RecursionLimits:
    max_depth: int = 5
    max_spawned_objectives: int = 20
    max_work_units_per_mission: int = 50
    max_budget_usd: float = 10.0
    max_wall_clock_seconds: int = 3600
    max_autonomous_scope: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_depth": self.max_depth,
            "max_spawned_objectives": self.max_spawned_objectives,
            "max_work_units_per_mission": self.max_work_units_per_mission,
            "max_budget_usd": self.max_budget_usd,
            "max_wall_clock_seconds": self.max_wall_clock_seconds,
            "max_autonomous_scope": self.max_autonomous_scope,
        }


@dataclass
class RecursionState:
    current_depth: int = 0
    spawned_objectives: int = 0
    work_units_created: int = 0
    budget_spent_usd: float = 0.0
    start_time: float = 0.0
    autonomous_operations: int = 0

    def __post_init__(self) -> None:
        if not self.start_time:
            self.start_time = time.time()

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_depth": self.current_depth,
            "spawned_objectives": self.spawned_objectives,
            "work_units_created": self.work_units_created,
            "budget_spent_usd": round(self.budget_spent_usd, 6),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "autonomous_operations": self.autonomous_operations,
        }


@dataclass
class EscalationEvent:
    level: EscalationLevel
    reason: str
    execution_class: ExecutionClass
    limit_name: str
    current_value: float
    limit_value: float
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "reason": self.reason,
            "execution_class": self.execution_class.value,
            "limit_name": self.limit_name,
            "current_value": self.current_value,
            "limit_value": self.limit_value,
            "timestamp": self.timestamp,
        }


@dataclass
class GovernanceCheckResult:
    allowed: bool = True
    approval_required: RecursionApproval = RecursionApproval.NONE
    escalations: list[EscalationEvent] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "approval_required": self.approval_required.value,
            "escalations": [e.to_dict() for e in self.escalations],
            "reason": self.reason,
        }


class RecursionGovernor:
    """Enforces bounded recursive execution across the organism.

    Every recursive operation must call check_before_execution()
    before proceeding. The governor tracks cumulative resource
    usage and blocks operations that exceed configured limits.
    """

    def __init__(
        self,
        limits: RecursionLimits | None = None,
        approval_map: dict[ExecutionClass, RecursionApproval] | None = None,
    ) -> None:
        self._limits = limits or RecursionLimits()
        self._approval_map = approval_map or dict(_DEFAULT_APPROVAL_MAP)
        self._state = RecursionState()
        self._kill_switch = False
        self._escalation_log: list[EscalationEvent] = []
        self._max_escalation_log = 500

    @property
    def limits(self) -> RecursionLimits:
        return self._limits

    @property
    def state(self) -> RecursionState:
        return self._state

    @property
    def is_killed(self) -> bool:
        return self._kill_switch

    def kill(self) -> None:
        self._kill_switch = True
        logger.warning("KILL SWITCH ACTIVATED — all autonomous execution halted")
        self._escalate(
            EscalationLevel.KILL,
            "Kill switch activated",
            ExecutionClass.DETERMINISTIC,
            "kill_switch",
            1,
            0,
        )

    def resume(self) -> None:
        self._kill_switch = False
        logger.info("Kill switch deactivated — autonomous execution resumed")

    def reset_state(self) -> None:
        self._state = RecursionState()

    def check_before_execution(
        self,
        execution_class: ExecutionClass,
        depth_increment: int = 0,
        work_units: int = 0,
        estimated_cost_usd: float = 0.0,
    ) -> GovernanceCheckResult:
        if self._kill_switch:
            return GovernanceCheckResult(
                allowed=False,
                approval_required=RecursionApproval.BLOCK,
                reason="Kill switch is active",
            )

        result = GovernanceCheckResult()
        escalations: list[EscalationEvent] = []

        new_depth = self._state.current_depth + depth_increment
        if new_depth > self._limits.max_depth:
            escalations.append(self._make_escalation(
                EscalationLevel.BLOCK,
                f"Recursion depth {new_depth} exceeds limit {self._limits.max_depth}",
                execution_class,
                "max_depth",
                new_depth,
                self._limits.max_depth,
            ))

        if self._state.spawned_objectives >= self._limits.max_spawned_objectives:
            escalations.append(self._make_escalation(
                EscalationLevel.BLOCK,
                f"Spawned objectives {self._state.spawned_objectives} at limit",
                execution_class,
                "max_spawned_objectives",
                self._state.spawned_objectives,
                self._limits.max_spawned_objectives,
            ))

        new_wu = self._state.work_units_created + work_units
        if new_wu > self._limits.max_work_units_per_mission:
            escalations.append(self._make_escalation(
                EscalationLevel.BLOCK,
                f"Work units {new_wu} exceeds limit {self._limits.max_work_units_per_mission}",
                execution_class,
                "max_work_units_per_mission",
                new_wu,
                self._limits.max_work_units_per_mission,
            ))

        projected_cost = self._state.budget_spent_usd + estimated_cost_usd
        if projected_cost > self._limits.max_budget_usd:
            escalations.append(self._make_escalation(
                EscalationLevel.BLOCK,
                f"Budget ${projected_cost:.4f} exceeds limit ${self._limits.max_budget_usd:.2f}",
                execution_class,
                "max_budget_usd",
                projected_cost,
                self._limits.max_budget_usd,
            ))

        if self._state.elapsed_seconds > self._limits.max_wall_clock_seconds:
            escalations.append(self._make_escalation(
                EscalationLevel.BLOCK,
                f"Wall clock {self._state.elapsed_seconds:.0f}s exceeds limit {self._limits.max_wall_clock_seconds}s",
                execution_class,
                "max_wall_clock_seconds",
                self._state.elapsed_seconds,
                self._limits.max_wall_clock_seconds,
            ))

        if execution_class in {
            ExecutionClass.RECURSIVE_IMPROVEMENT,
            ExecutionClass.ADVISOR_DELEGATION,
            ExecutionClass.AGENT,
        }:
            new_auto = self._state.autonomous_operations + 1
            if new_auto > self._limits.max_autonomous_scope:
                escalations.append(self._make_escalation(
                    EscalationLevel.BLOCK,
                    f"Autonomous operations {new_auto} exceeds limit",
                    execution_class,
                    "max_autonomous_scope",
                    new_auto,
                    self._limits.max_autonomous_scope,
                ))

        approval = self._approval_map.get(execution_class, RecursionApproval.APPROVE)

        _WARN_THRESHOLDS = {
            "max_depth": 0.8,
            "max_spawned_objectives": 0.8,
            "max_work_units_per_mission": 0.8,
            "max_budget_usd": 0.8,
            "max_wall_clock_seconds": 0.8,
        }
        if not escalations:
            self._check_warning_thresholds(execution_class, escalations, _WARN_THRESHOLDS)

        blocked = any(e.level == EscalationLevel.BLOCK for e in escalations)

        result.allowed = not blocked
        result.approval_required = RecursionApproval.BLOCK if blocked else approval
        result.escalations = escalations
        if blocked:
            result.reason = escalations[0].reason if escalations else "Limit exceeded"

        return result

    def record_execution(
        self,
        depth_increment: int = 0,
        objectives_spawned: int = 0,
        work_units: int = 0,
        cost_usd: float = 0.0,
        is_autonomous: bool = False,
    ) -> None:
        self._state.current_depth += depth_increment
        self._state.spawned_objectives += objectives_spawned
        self._state.work_units_created += work_units
        self._state.budget_spent_usd += cost_usd
        if is_autonomous:
            self._state.autonomous_operations += 1

    def unwind_depth(self, levels: int = 1) -> None:
        self._state.current_depth = max(0, self._state.current_depth - levels)

    def escalation_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._escalation_log[-limit:]]

    def _check_warning_thresholds(
        self,
        execution_class: ExecutionClass,
        escalations: list[EscalationEvent],
        thresholds: dict[str, float],
    ) -> None:
        checks = [
            ("max_depth", self._state.current_depth, self._limits.max_depth),
            ("max_spawned_objectives", self._state.spawned_objectives, self._limits.max_spawned_objectives),
            ("max_work_units_per_mission", self._state.work_units_created, self._limits.max_work_units_per_mission),
            ("max_budget_usd", self._state.budget_spent_usd, self._limits.max_budget_usd),
            ("max_wall_clock_seconds", self._state.elapsed_seconds, self._limits.max_wall_clock_seconds),
        ]
        for name, current, limit in checks:
            threshold = thresholds.get(name, 0.8)
            if limit > 0 and current / limit >= threshold:
                escalations.append(self._make_escalation(
                    EscalationLevel.WARNING,
                    f"{name}: {current}/{limit} ({current/limit:.0%} of limit)",
                    execution_class,
                    name,
                    current,
                    limit,
                ))

    def _make_escalation(
        self,
        level: EscalationLevel,
        reason: str,
        execution_class: ExecutionClass,
        limit_name: str,
        current: float,
        limit: float,
    ) -> EscalationEvent:
        event = EscalationEvent(
            level=level,
            reason=reason,
            execution_class=execution_class,
            limit_name=limit_name,
            current_value=current,
            limit_value=limit,
        )
        self._escalation_log.append(event)
        if len(self._escalation_log) > self._max_escalation_log:
            self._escalation_log = self._escalation_log[-self._max_escalation_log:]

        if level in {EscalationLevel.BLOCK, EscalationLevel.KILL}:
            logger.warning("recursion governance %s: %s", level.value, reason)
        else:
            logger.info("recursion governance %s: %s", level.value, reason)

        self._escalate(level, reason, execution_class, limit_name, current, limit)
        return event

    def _escalate(
        self,
        level: EscalationLevel,
        reason: str,
        execution_class: ExecutionClass,
        limit_name: str,
        current: float,
        limit: float,
    ) -> None:
        pass

    def to_dict(self) -> dict[str, Any]:
        return {
            "limits": self._limits.to_dict(),
            "state": self._state.to_dict(),
            "kill_switch": self._kill_switch,
            "approval_map": {
                k.value: v.value for k, v in self._approval_map.items()
            },
            "escalation_count": len(self._escalation_log),
        }
