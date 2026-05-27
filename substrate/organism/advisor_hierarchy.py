"""Advisor Hierarchy — governed recursive advisory orchestration.

Terminology:
  PrimaryAdvisor  — single user-facing advisor for the instance
  DomainAdvisor   — scoped to a company/function
  TeamAdvisor     — scoped to a team/workcell
  TaskAdvisor     — temporary mission-scoped advisor
  WorkerCell      — execution unit (already exists)
  Runtime         — tool/model/process/node (already exists)

Every advisor has explicit scope, authority, budget, and recursion
limits. Sub-advisors are internal orchestration organs unless
explicitly promoted to user-facing.

The hierarchy enforces:
  - No unmanaged spawning (every advisor has a parent)
  - Budget cascading (child budget <= parent budget)
  - Scope narrowing (child scope <= parent scope)
  - Recursion limit inheritance
  - Reporting cadence
  - Shutdown conditions

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AdvisorScope(str, Enum):
    INSTANCE = "instance"
    DOMAIN = "domain"
    TEAM = "team"
    TASK = "task"


class AdvisorAuthority(str, Enum):
    PRIMARY = "primary"
    DOMAIN = "domain"
    TEAM = "team"
    TASK = "task"
    WORKER = "worker"


class AdvisorStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


@dataclass
class EscalationPolicy:
    escalate_on_failure: bool = True
    escalate_on_budget_exceed: bool = True
    escalate_on_scope_violation: bool = True
    max_retries_before_escalation: int = 2
    escalation_target: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "escalate_on_failure": self.escalate_on_failure,
            "escalate_on_budget_exceed": self.escalate_on_budget_exceed,
            "escalate_on_scope_violation": self.escalate_on_scope_violation,
            "max_retries_before_escalation": self.max_retries_before_escalation,
            "escalation_target": self.escalation_target,
        }


@dataclass
class AdvisorNode:
    id: str = ""
    parent_id: str = ""
    scope: AdvisorScope = AdvisorScope.TASK
    authority_class: AdvisorAuthority = AdvisorAuthority.TASK
    status: AdvisorStatus = AdvisorStatus.IDLE

    allowed_projects: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    allowed_runtimes: list[str] = field(default_factory=list)

    budget_usd: float = 1.0
    budget_spent_usd: float = 0.0
    recursion_limit: int = 3
    spawn_limit: int = 5
    spawned_count: int = 0

    reporting_cadence_seconds: int = 300
    last_report_at: float = 0.0

    success_criteria: str = ""
    shutdown_condition: str = ""
    escalation_policy: EscalationPolicy = field(default_factory=EscalationPolicy)

    created_at: float = 0.0
    last_active_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"adv-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.budget_usd - self.budget_spent_usd)

    @property
    def can_spawn(self) -> bool:
        return self.spawned_count < self.spawn_limit

    @property
    def is_active(self) -> bool:
        return self.status in {AdvisorStatus.ACTIVE, AdvisorStatus.IDLE}

    @property
    def report_overdue(self) -> bool:
        if self.reporting_cadence_seconds <= 0:
            return False
        return (time.time() - self.last_report_at) > self.reporting_cadence_seconds

    def record_spend(self, amount_usd: float) -> bool:
        if self.budget_spent_usd + amount_usd > self.budget_usd:
            return False
        self.budget_spent_usd += amount_usd
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "scope": self.scope.value,
            "authority_class": self.authority_class.value,
            "status": self.status.value,
            "allowed_projects": self.allowed_projects,
            "allowed_tools": self.allowed_tools,
            "allowed_runtimes": self.allowed_runtimes,
            "budget_usd": round(self.budget_usd, 4),
            "budget_spent_usd": round(self.budget_spent_usd, 4),
            "budget_remaining": round(self.budget_remaining, 4),
            "recursion_limit": self.recursion_limit,
            "spawn_limit": self.spawn_limit,
            "spawned_count": self.spawned_count,
            "can_spawn": self.can_spawn,
            "reporting_cadence_seconds": self.reporting_cadence_seconds,
            "report_overdue": self.report_overdue,
            "success_criteria": self.success_criteria,
            "shutdown_condition": self.shutdown_condition,
            "escalation_policy": self.escalation_policy.to_dict(),
            "created_at": self.created_at,
            "last_active_at": self.last_active_at,
        }


_SCOPE_RANK: dict[AdvisorScope, int] = {
    AdvisorScope.INSTANCE: 4,
    AdvisorScope.DOMAIN: 3,
    AdvisorScope.TEAM: 2,
    AdvisorScope.TASK: 1,
}


class AdvisorHierarchy:
    """Manages the tree of advisors with scope/budget/authority governance.

    Invariants:
      - Every non-primary advisor has a parent
      - Child scope <= parent scope
      - Child budget <= parent remaining budget
      - Child recursion limit <= parent recursion limit
      - No unmanaged spawning
    """

    def __init__(self) -> None:
        self._advisors: dict[str, AdvisorNode] = {}
        self._primary_id: str = ""

    @property
    def primary(self) -> AdvisorNode | None:
        return self._advisors.get(self._primary_id)

    def register_primary(
        self,
        allowed_projects: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        allowed_runtimes: list[str] | None = None,
        budget_usd: float = 100.0,
        recursion_limit: int = 5,
        spawn_limit: int = 20,
        metadata: dict[str, Any] | None = None,
    ) -> AdvisorNode:
        node = AdvisorNode(
            parent_id="",
            scope=AdvisorScope.INSTANCE,
            authority_class=AdvisorAuthority.PRIMARY,
            status=AdvisorStatus.ACTIVE,
            allowed_projects=allowed_projects or [],
            allowed_tools=allowed_tools or [],
            allowed_runtimes=allowed_runtimes or [],
            budget_usd=budget_usd,
            recursion_limit=recursion_limit,
            spawn_limit=spawn_limit,
            reporting_cadence_seconds=0,
            metadata=metadata or {},
        )
        self._advisors[node.id] = node
        self._primary_id = node.id

        logger.info("primary advisor registered: %s", node.id)
        return node

    def spawn(
        self,
        parent_id: str,
        scope: AdvisorScope,
        authority_class: AdvisorAuthority,
        allowed_projects: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        allowed_runtimes: list[str] | None = None,
        budget_usd: float = 1.0,
        recursion_limit: int = 3,
        spawn_limit: int = 3,
        success_criteria: str = "",
        shutdown_condition: str = "",
        reporting_cadence_seconds: int = 300,
        metadata: dict[str, Any] | None = None,
    ) -> AdvisorNode | None:
        parent = self._advisors.get(parent_id)
        if parent is None:
            logger.warning("spawn failed: parent %s not found", parent_id)
            return None

        if not parent.is_active:
            logger.warning("spawn failed: parent %s is %s", parent_id, parent.status.value)
            return None

        if not parent.can_spawn:
            logger.warning(
                "spawn failed: parent %s at spawn limit %d",
                parent_id,
                parent.spawn_limit,
            )
            return None

        parent_scope_rank = _SCOPE_RANK.get(parent.scope, 0)
        child_scope_rank = _SCOPE_RANK.get(scope, 0)
        if child_scope_rank >= parent_scope_rank:
            logger.warning(
                "spawn failed: child scope %s >= parent scope %s",
                scope.value,
                parent.scope.value,
            )
            return None

        if budget_usd > parent.budget_remaining:
            logger.warning(
                "spawn failed: budget $%.4f exceeds parent remaining $%.4f",
                budget_usd,
                parent.budget_remaining,
            )
            return None

        effective_recursion = min(recursion_limit, parent.recursion_limit - 1)
        if effective_recursion < 0:
            logger.warning("spawn failed: parent recursion limit exhausted")
            return None

        child = AdvisorNode(
            parent_id=parent_id,
            scope=scope,
            authority_class=authority_class,
            status=AdvisorStatus.IDLE,
            allowed_projects=allowed_projects or [],
            allowed_tools=allowed_tools or [],
            allowed_runtimes=allowed_runtimes or [],
            budget_usd=budget_usd,
            recursion_limit=effective_recursion,
            spawn_limit=min(spawn_limit, parent.spawn_limit - parent.spawned_count - 1),
            success_criteria=success_criteria,
            shutdown_condition=shutdown_condition,
            reporting_cadence_seconds=reporting_cadence_seconds,
            escalation_policy=EscalationPolicy(escalation_target=parent_id),
            metadata=metadata or {},
        )

        self._advisors[child.id] = child
        parent.spawned_count += 1
        parent.budget_spent_usd += budget_usd

        logger.info(
            "advisor spawned: %s (parent=%s, scope=%s, budget=$%.4f)",
            child.id,
            parent_id,
            scope.value,
            budget_usd,
        )
        return child

    def terminate(self, advisor_id: str) -> bool:
        node = self._advisors.get(advisor_id)
        if node is None:
            return False

        children = self.children_of(advisor_id)
        for child in children:
            self.terminate(child.id)

        if node.parent_id:
            parent = self._advisors.get(node.parent_id)
            if parent:
                refund = node.budget_remaining
                parent.budget_spent_usd = max(0.0, parent.budget_spent_usd - refund)

        node.status = AdvisorStatus.TERMINATED
        logger.info("advisor terminated: %s", advisor_id)
        return True

    def suspend(self, advisor_id: str) -> bool:
        node = self._advisors.get(advisor_id)
        if node is None:
            return False
        node.status = AdvisorStatus.SUSPENDED
        return True

    def resume(self, advisor_id: str) -> bool:
        node = self._advisors.get(advisor_id)
        if node is None or node.status != AdvisorStatus.SUSPENDED:
            return False
        node.status = AdvisorStatus.IDLE
        return True

    def get(self, advisor_id: str) -> AdvisorNode | None:
        return self._advisors.get(advisor_id)

    def children_of(self, advisor_id: str) -> list[AdvisorNode]:
        return [
            n for n in self._advisors.values()
            if n.parent_id == advisor_id and n.is_active
        ]

    def ancestors_of(self, advisor_id: str) -> list[AdvisorNode]:
        ancestors: list[AdvisorNode] = []
        node = self._advisors.get(advisor_id)
        while node and node.parent_id:
            parent = self._advisors.get(node.parent_id)
            if parent:
                ancestors.append(parent)
                node = parent
            else:
                break
        return ancestors

    def check_scope_violation(
        self, advisor_id: str, project: str
    ) -> bool:
        node = self._advisors.get(advisor_id)
        if node is None:
            return True
        if not node.allowed_projects:
            return False
        return project not in node.allowed_projects

    def overdue_reports(self) -> list[AdvisorNode]:
        return [
            n for n in self._advisors.values()
            if n.is_active and n.report_overdue
        ]

    def active_count(self) -> int:
        return sum(1 for n in self._advisors.values() if n.is_active)

    def hierarchy_tree(self) -> dict[str, Any]:
        def _build_tree(node_id: str) -> dict[str, Any]:
            node = self._advisors.get(node_id)
            if node is None:
                return {}
            children = self.children_of(node_id)
            return {
                **node.to_dict(),
                "children": [_build_tree(c.id) for c in children],
            }

        if self._primary_id:
            return _build_tree(self._primary_id)

        roots = [
            n for n in self._advisors.values()
            if not n.parent_id and n.is_active
        ]
        return {
            "roots": [_build_tree(r.id) for r in roots],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_id": self._primary_id,
            "total_advisors": len(self._advisors),
            "active_advisors": self.active_count(),
            "advisors": {k: v.to_dict() for k, v in self._advisors.items()},
        }
