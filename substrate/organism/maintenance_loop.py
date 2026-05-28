"""Autonomous Maintenance Loop — OBSERVE-mode infrastructure health cycle.

Wires a safe read-only maintenance cycle into the AutonomousTick:
  - repo state probe
  - docker state probe
  - runtime/workcell drift check
  - disk/log pressure check
  - stale data detection
  - produce recommended actions

No destructive actions — only OBSERVE + RECOMMEND.
Approved ASSISTED actions are dispatched via AssistedExecutor.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
from substrate.organism.workload_runner import WorkloadRunner, WorkloadType

logger = logging.getLogger(__name__)


class ActionSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ACTION_NEEDED = "action_needed"
    URGENT = "urgent"


class ActionCategory(str, Enum):
    LOG_ROTATION = "log_rotation"
    CONTAINER_RESTART = "container_restart"
    RUNTIME_REFRESH = "runtime_refresh"
    TEST_SUITE = "test_suite"
    GRAPH_REBUILD = "graph_rebuild"
    BRANCH_CLEANUP = "branch_cleanup"
    DISK_CLEANUP = "disk_cleanup"


@dataclass
class MaintenanceRecommendation:
    action_id: str
    category: ActionCategory
    severity: ActionSeverity
    description: str
    required_mode: ExecutionMode
    reversible: bool = True
    auto_approvable: bool = False
    evidence: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "required_mode": self.required_mode.value,
            "reversible": self.reversible,
            "auto_approvable": self.auto_approvable,
            "evidence": self.evidence[:500],
            "timestamp": self.timestamp,
        }


@dataclass
class MaintenanceCycleReport:
    cycle_number: int
    workloads_run: int = 0
    findings: list[str] = field(default_factory=list)
    recommendations: list[MaintenanceRecommendation] = field(default_factory=list)
    assisted_actions_taken: int = 0
    elapsed_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_number": self.cycle_number,
            "workloads_run": self.workloads_run,
            "findings": self.findings[:30],
            "recommendations": [r.to_dict() for r in self.recommendations[:20]],
            "assisted_actions_taken": self.assisted_actions_taken,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "timestamp": self.timestamp,
        }


_MAX_REPORTS = 100


class MaintenanceLoop:
    """Autonomous maintenance cycle that runs during organism ticks.

    Phase 1 (OBSERVE): runs all read-only probes and generates
    recommendations. No mutations.

    Phase 2 (ASSISTED): executes approved safe actions with
    audit trail.
    """

    def __init__(
        self,
        workload_runner: WorkloadRunner,
        execution_mode: ExecutionModeManager,
        event_spine: EventSpine,
    ) -> None:
        self._runner = workload_runner
        self._mode = execution_mode
        self._spine = event_spine
        self._cycle_count: int = 0
        self._reports: list[MaintenanceCycleReport] = []
        self._pending_recommendations: list[MaintenanceRecommendation] = []
        self._completed_actions: list[dict[str, Any]] = []
        self._autonomous_gateway: Any = None

    def set_autonomous_gateway(self, gateway: Any) -> None:
        self._autonomous_gateway = gateway

    def maintenance_tick(self) -> dict[str, Any]:
        """Execute one maintenance cycle. Registered as a tick stage."""
        self._cycle_count += 1
        start = time.monotonic()
        report = MaintenanceCycleReport(cycle_number=self._cycle_count)

        outcomes = self._runner.run_all_observe()
        report.workloads_run = len(outcomes)

        for outcome in outcomes:
            report.findings.extend(outcome.findings)
            recommendations = self._derive_recommendations(outcome)
            report.recommendations.extend(recommendations)
            self._pending_recommendations.extend(recommendations)

        report.elapsed_seconds = time.monotonic() - start

        if len(self._reports) >= _MAX_REPORTS:
            self._reports = self._reports[-(_MAX_REPORTS // 2):]
        self._reports.append(report)

        self._spine.emit(
            EventDomain.OBSERVABILITY,
            "maintenance_cycle_completed",
            "maintenance_loop",
            {
                "cycle": self._cycle_count,
                "workloads": report.workloads_run,
                "findings": len(report.findings),
                "recommendations": len(report.recommendations),
            },
            priority=EventPriority.NORMAL,
        )

        return report.to_dict()

    def _derive_recommendations(self, outcome: Any) -> list[MaintenanceRecommendation]:
        recs: list[MaintenanceRecommendation] = []
        wtype = outcome.workload_type
        ts = int(time.time())

        if wtype == WorkloadType.DISK_PRESSURE:
            pressure = outcome.metrics.get("pressure", "normal")
            if pressure in ("high", "critical"):
                recs.append(MaintenanceRecommendation(
                    action_id=f"maint-disk-{ts}",
                    category=ActionCategory.DISK_CLEANUP,
                    severity=ActionSeverity.URGENT if pressure == "critical" else ActionSeverity.ACTION_NEEDED,
                    description=f"Disk pressure is {pressure} ({outcome.metrics.get('usage_percent', 0):.1f}% used)",
                    required_mode=ExecutionMode.ASSISTED,
                    evidence="; ".join(outcome.findings[:3]),
                ))
            large_logs = outcome.metrics.get("large_logs", [])
            if large_logs:
                recs.append(MaintenanceRecommendation(
                    action_id=f"maint-logrot-{ts}",
                    category=ActionCategory.LOG_ROTATION,
                    severity=ActionSeverity.WARNING,
                    description=f"{len(large_logs)} large log files detected",
                    required_mode=ExecutionMode.ASSISTED,
                    reversible=True,
                    auto_approvable=True,
                    evidence=str(large_logs[:3]),
                ))

        elif wtype == WorkloadType.DOCKER_HEALTH:
            unhealthy = outcome.metrics.get("unhealthy", 0)
            stopped = outcome.metrics.get("stopped", 0)
            if unhealthy > 0:
                recs.append(MaintenanceRecommendation(
                    action_id=f"maint-docker-unhealthy-{ts}",
                    category=ActionCategory.CONTAINER_RESTART,
                    severity=ActionSeverity.ACTION_NEEDED,
                    description=f"{unhealthy} unhealthy containers need attention",
                    required_mode=ExecutionMode.ASSISTED,
                    reversible=True,
                    evidence="; ".join(outcome.findings[:3]),
                ))
            if stopped > 2:
                recs.append(MaintenanceRecommendation(
                    action_id=f"maint-docker-stopped-{ts}",
                    category=ActionCategory.CONTAINER_RESTART,
                    severity=ActionSeverity.WARNING,
                    description=f"{stopped} stopped containers",
                    required_mode=ExecutionMode.ASSISTED,
                    evidence="; ".join(outcome.findings[:3]),
                ))

        elif wtype == WorkloadType.STALE_BRANCH_SCAN:
            stale = outcome.metrics.get("stale_branches", [])
            if len(stale) > 5:
                recs.append(MaintenanceRecommendation(
                    action_id=f"maint-branches-{ts}",
                    category=ActionCategory.BRANCH_CLEANUP,
                    severity=ActionSeverity.INFO,
                    description=f"{len(stale)} non-main branches could be cleaned",
                    required_mode=ExecutionMode.ASSISTED,
                    reversible=False,
                    evidence=", ".join(stale[:5]),
                ))

        elif wtype == WorkloadType.LOG_ROTATION:
            large_count = outcome.metrics.get("large_files_count", 0)
            total_mb = outcome.metrics.get("total_large_mb", 0)
            if total_mb > 100:
                recs.append(MaintenanceRecommendation(
                    action_id=f"maint-logfiles-{ts}",
                    category=ActionCategory.LOG_ROTATION,
                    severity=ActionSeverity.ACTION_NEEDED,
                    description=f"{large_count} large files totaling {total_mb:.0f} MB",
                    required_mode=ExecutionMode.ASSISTED,
                    auto_approvable=True,
                    evidence=str(outcome.metrics.get("large_files", [])[:5]),
                ))

        return recs

    def submit_recommendation_via_gateway(
        self,
        recommendation: MaintenanceRecommendation,
    ) -> dict[str, Any]:
        """Convert a MaintenanceRecommendation to an ActionEnvelope and submit via gateway.

        Returns the envelope dict with its status.
        """
        if self._autonomous_gateway is None:
            return {"error": "no gateway configured", "recommendation": recommendation.to_dict()}

        from substrate.organism.action_envelope import (
            ActionEnvelope,
            ActionType,
            BlastRadius,
            ExecutionConstraints,
            ReversibilityClass,
        )

        risk_map = {
            ActionSeverity.INFO: "low",
            ActionSeverity.WARNING: "low",
            ActionSeverity.ACTION_NEEDED: "medium",
            ActionSeverity.URGENT: "high",
        }
        risk = risk_map.get(recommendation.severity, "medium")

        envelope = ActionEnvelope(
            intent=recommendation.description,
            action_type=ActionType.STATE,
            source="maintenance_loop",
            execute_fn=lambda: (recommendation.description, True),
            risk_level=risk,
            blast_radius=BlastRadius.LOCAL_RUNTIME,
            reversibility=(
                ReversibilityClass.FULLY_REVERSIBLE if recommendation.reversible
                else ReversibilityClass.IRREVERSIBLE
            ),
            constraints=ExecutionConstraints(
                require_approval=not recommendation.auto_approvable,
            ),
            metadata={
                "mutation_name": recommendation.category.value,
                "action_id": recommendation.action_id,
                "category": recommendation.category.value,
            },
        )

        result = self._autonomous_gateway.submit_envelope(envelope)
        return result.to_dict()

    @property
    def pending_recommendations(self) -> list[MaintenanceRecommendation]:
        return list(self._pending_recommendations)

    def clear_recommendations(self) -> None:
        self._pending_recommendations.clear()

    def recent_reports(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._reports[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_count": self._cycle_count,
            "pending_recommendations": len(self._pending_recommendations),
            "total_reports": len(self._reports),
            "completed_actions": len(self._completed_actions),
            "last_cycle": self._reports[-1].to_dict() if self._reports else None,
        }
