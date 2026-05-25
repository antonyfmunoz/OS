"""Homeostasis — the organism's immune/self-regulation system.

Monitors system health across multiple dimensions and takes corrective
action when things go wrong. The biological equivalent: your body
maintains temperature, blood pressure, and immune response without
you thinking about it.

Dimensions monitored:
  1. Pipeline throughput   — signals processed per minute
  2. Error rate            — failures per total executions
  3. Queue depth           — pending signals awaiting processing
  4. Memory pressure       — observation count vs. capacity
  5. Heartbeat freshness   — are workers alive
  6. Budget consumption    — API cost tracking
  7. Stuck loop detection  — repeated identical failures
  8. Governance overrides  — founder bypasses accumulating
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SystemMode(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    PROTECTIVE = "protective"
    CRITICAL = "critical"


class HealthDimension(str, Enum):
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    QUEUE_DEPTH = "queue_depth"
    MEMORY_PRESSURE = "memory_pressure"
    HEARTBEAT = "heartbeat"
    BUDGET = "budget"
    STUCK_LOOP = "stuck_loop"
    GOVERNANCE_OVERRIDES = "governance_overrides"


@dataclass
class DimensionStatus:
    dimension: HealthDimension
    value: float = 0.0
    threshold: float = 0.0
    healthy: bool = True
    detail: str = ""


@dataclass
class HomeostasisReport:
    mode: SystemMode = SystemMode.HEALTHY
    dimensions: list[DimensionStatus] = field(default_factory=list)
    unhealthy: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "unhealthy": self.unhealthy,
            "actions_taken": self.actions_taken,
            "checked_at": self.checked_at,
            "dimensions": [
                {
                    "dimension": d.dimension.value,
                    "value": round(d.value, 3),
                    "threshold": d.threshold,
                    "healthy": d.healthy,
                    "detail": d.detail,
                }
                for d in self.dimensions
            ],
        }


class HomeostasisEngine:
    """Self-regulation engine monitoring 8 health dimensions."""

    def __init__(
        self,
        error_rate_threshold: float = 0.3,
        queue_depth_max: int = 100,
        memory_capacity: int = 5000,
        budget_limit_usd: float = 50.0,
        stuck_loop_threshold: int = 3,
        governance_override_max: int = 10,
    ) -> None:
        self._error_rate_threshold = error_rate_threshold
        self._queue_depth_max = queue_depth_max
        self._memory_capacity = memory_capacity
        self._budget_limit = budget_limit_usd
        self._stuck_threshold = stuck_loop_threshold
        self._override_max = governance_override_max

        self._executions: deque[tuple[float, bool]] = deque(maxlen=1000)
        self._recent_errors: deque[str] = deque(maxlen=100)
        self._queue_depth: int = 0
        self._observation_count: int = 0
        self._budget_spent: float = 0.0
        self._override_count: int = 0
        self._mode: SystemMode = SystemMode.HEALTHY
        self._last_check: float = 0.0

    def record_execution(self, success: bool, error_detail: str = "") -> None:
        self._executions.append((time.time(), success))
        if not success and error_detail:
            self._recent_errors.append(error_detail)

    def record_budget(self, cost_usd: float) -> None:
        self._budget_spent += cost_usd

    def record_override(self) -> None:
        self._override_count += 1

    def set_queue_depth(self, depth: int) -> None:
        self._queue_depth = depth

    def set_observation_count(self, count: int) -> None:
        self._observation_count = count

    def check(self) -> HomeostasisReport:
        """Run all health checks and determine system mode."""
        report = HomeostasisReport(
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

        checks = [
            self._check_error_rate(),
            self._check_queue_depth(),
            self._check_memory_pressure(),
            self._check_budget(),
            self._check_stuck_loop(),
            self._check_governance_overrides(),
            self._check_throughput(),
        ]

        report.dimensions = checks
        report.unhealthy = [d.dimension.value for d in checks if not d.healthy]

        unhealthy_count = len(report.unhealthy)
        if unhealthy_count == 0:
            report.mode = SystemMode.HEALTHY
        elif unhealthy_count <= 2:
            report.mode = SystemMode.DEGRADED
        elif unhealthy_count <= 4:
            report.mode = SystemMode.PROTECTIVE
        else:
            report.mode = SystemMode.CRITICAL

        report.actions_taken = self._take_corrective_action(report)
        self._mode = report.mode
        self._last_check = time.time()

        return report

    @property
    def current_mode(self) -> SystemMode:
        return self._mode

    def _check_error_rate(self) -> DimensionStatus:
        if not self._executions:
            return DimensionStatus(
                dimension=HealthDimension.ERROR_RATE,
                value=0.0,
                threshold=self._error_rate_threshold,
                healthy=True,
                detail="No executions recorded",
            )

        window = time.time() - 300
        recent = [(t, s) for t, s in self._executions if t > window]
        if not recent:
            return DimensionStatus(
                dimension=HealthDimension.ERROR_RATE,
                healthy=True,
                detail="No recent executions",
            )

        failures = sum(1 for _, s in recent if not s)
        rate = failures / len(recent)

        return DimensionStatus(
            dimension=HealthDimension.ERROR_RATE,
            value=rate,
            threshold=self._error_rate_threshold,
            healthy=rate < self._error_rate_threshold,
            detail=f"{failures}/{len(recent)} failed in last 5min",
        )

    def _check_queue_depth(self) -> DimensionStatus:
        ratio = self._queue_depth / self._queue_depth_max if self._queue_depth_max > 0 else 0
        return DimensionStatus(
            dimension=HealthDimension.QUEUE_DEPTH,
            value=ratio,
            threshold=1.0,
            healthy=self._queue_depth < self._queue_depth_max,
            detail=f"{self._queue_depth}/{self._queue_depth_max} pending",
        )

    def _check_memory_pressure(self) -> DimensionStatus:
        ratio = self._observation_count / self._memory_capacity if self._memory_capacity > 0 else 0
        return DimensionStatus(
            dimension=HealthDimension.MEMORY_PRESSURE,
            value=ratio,
            threshold=0.9,
            healthy=ratio < 0.9,
            detail=f"{self._observation_count}/{self._memory_capacity} observations",
        )

    def _check_budget(self) -> DimensionStatus:
        ratio = self._budget_spent / self._budget_limit if self._budget_limit > 0 else 0
        return DimensionStatus(
            dimension=HealthDimension.BUDGET,
            value=ratio,
            threshold=1.0,
            healthy=self._budget_spent < self._budget_limit,
            detail=f"${self._budget_spent:.2f}/${self._budget_limit:.2f} spent",
        )

    def _check_stuck_loop(self) -> DimensionStatus:
        if len(self._recent_errors) < self._stuck_threshold:
            return DimensionStatus(
                dimension=HealthDimension.STUCK_LOOP,
                healthy=True,
                detail="No stuck loop detected",
            )

        recent = list(self._recent_errors)[-self._stuck_threshold:]
        if len(set(recent)) == 1:
            return DimensionStatus(
                dimension=HealthDimension.STUCK_LOOP,
                value=1.0,
                threshold=0.5,
                healthy=False,
                detail=f"Same error repeated {self._stuck_threshold}x: {recent[0][:100]}",
            )

        return DimensionStatus(
            dimension=HealthDimension.STUCK_LOOP,
            healthy=True,
            detail=f"{len(self._recent_errors)} errors, no identical repeats",
        )

    def _check_governance_overrides(self) -> DimensionStatus:
        return DimensionStatus(
            dimension=HealthDimension.GOVERNANCE_OVERRIDES,
            value=self._override_count,
            threshold=self._override_max,
            healthy=self._override_count < self._override_max,
            detail=f"{self._override_count}/{self._override_max} founder overrides",
        )

    def _check_throughput(self) -> DimensionStatus:
        if not self._executions:
            return DimensionStatus(
                dimension=HealthDimension.THROUGHPUT,
                healthy=True,
                detail="No executions to measure",
            )

        window = time.time() - 60
        recent_count = sum(1 for t, _ in self._executions if t > window)

        return DimensionStatus(
            dimension=HealthDimension.THROUGHPUT,
            value=recent_count,
            healthy=True,
            detail=f"{recent_count} executions in last 60s",
        )

    def _take_corrective_action(self, report: HomeostasisReport) -> list[str]:
        """Determine and log corrective actions for unhealthy dimensions."""
        actions: list[str] = []

        for dim in report.dimensions:
            if dim.healthy:
                continue

            if dim.dimension == HealthDimension.ERROR_RATE:
                actions.append("Throttle execution rate — high error rate")

            elif dim.dimension == HealthDimension.QUEUE_DEPTH:
                actions.append("Apply backpressure — queue at capacity")

            elif dim.dimension == HealthDimension.MEMORY_PRESSURE:
                actions.append("Prune oldest observations — memory at capacity")

            elif dim.dimension == HealthDimension.BUDGET:
                actions.append("Switch to local models only — budget exhausted")

            elif dim.dimension == HealthDimension.STUCK_LOOP:
                actions.append("Break stuck loop — clear error queue and pause")
                self._recent_errors.clear()

            elif dim.dimension == HealthDimension.GOVERNANCE_OVERRIDES:
                actions.append("Flag governance override accumulation to founder")

        if actions:
            logger.warning("homeostasis corrective actions: %s", actions)

        return actions
