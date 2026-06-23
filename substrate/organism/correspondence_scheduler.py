"""Correspondence Scheduler — periodic drift detection for projections.

Runs correspondence checks on all active projections at configurable
intervals. Detects regressions (L5→L2) and emits CRITICAL attention
items when divergence is found.

C26D: Reality Correspondence Certification — Phase 2.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from substrate.organism.production_truth_delta import (
    CorrespondenceChecker,
    CorrespondenceResult,
    CorrespondenceStatus,
)

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_SECONDS = 6 * 3600  # 6 hours
_MAX_HISTORY = 100


@dataclass
class RegressionAlert:
    """A detected certification regression."""

    projection_name: str = ""
    level_before: int = 0
    level_after: int = 0
    severity: str = "critical"
    detail: str = ""
    detected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_name": self.projection_name,
            "level_before": self.level_before,
            "level_after": self.level_after,
            "severity": self.severity,
            "detail": self.detail,
            "detected_at": self.detected_at.isoformat(),
        }


class CorrespondenceScheduler:
    """Periodic correspondence checker for all projections.

    Maintains a ring buffer of check history per projection.
    Detects regressions by comparing the latest check against
    the previous one.
    """

    def __init__(
        self,
        certification_engine: Any = None,
        projection_registry: Any = None,
        interval_seconds: float = _DEFAULT_INTERVAL_SECONDS,
        max_history: int = _MAX_HISTORY,
        attention_emitter: Any = None,
    ) -> None:
        self._engine = certification_engine
        self._registry = projection_registry
        self._interval = interval_seconds
        self._max_history = max_history
        self._attention = attention_emitter
        self._history: dict[str, deque[CorrespondenceResult]] = {}
        self._last_check_time: float = 0.0
        self._alerts: list[RegressionAlert] = []

    @property
    def interval_seconds(self) -> float:
        return self._interval

    @property
    def last_check_time(self) -> float:
        return self._last_check_time

    @property
    def alerts(self) -> list[RegressionAlert]:
        return list(self._alerts)

    def is_due(self) -> bool:
        """Whether enough time has passed since the last check."""
        if self._last_check_time == 0.0:
            return True
        return (time.monotonic() - self._last_check_time) >= self._interval

    def check_all(self) -> list[CorrespondenceResult]:
        """Run correspondence check for all registered projections.

        Returns list of CorrespondenceResult, one per projection.
        """
        if self._engine is None or self._registry is None:
            logger.warning("CorrespondenceScheduler: engine or registry not set")
            return []

        results: list[CorrespondenceResult] = []
        projection_names = self._get_projection_names()

        for name in projection_names:
            last_level = self._get_last_known_level(name)
            result = CorrespondenceChecker.check(
                projection_name=name,
                certification_engine=self._engine,
                last_known_level=last_level,
            )
            self._record(name, result)
            results.append(result)

        self._last_check_time = time.monotonic()

        regressions = self.detect_regressions()
        for alert in regressions:
            self._emit_alert(alert)

        return results

    def detect_regressions(self) -> list[RegressionAlert]:
        """Compare latest check vs previous for each projection.

        Returns list of RegressionAlert for any detected regressions.
        """
        alerts: list[RegressionAlert] = []

        for name, history in self._history.items():
            if len(history) < 2:
                continue
            latest = history[-1]
            previous = history[-2]

            if (
                latest.certification_after is not None
                and previous.certification_after is not None
                and latest.certification_after < previous.certification_after
            ):
                alert = RegressionAlert(
                    projection_name=name,
                    level_before=previous.certification_after,
                    level_after=latest.certification_after,
                    detail=(
                        f"{name}: L{previous.certification_after} → "
                        f"L{latest.certification_after}"
                    ),
                )
                alerts.append(alert)
                self._alerts.append(alert)

        return alerts

    def get_history(self, projection_name: str) -> list[CorrespondenceResult]:
        """Get check history for a projection (oldest first)."""
        if projection_name not in self._history:
            return []
        return list(self._history[projection_name])

    def get_latest(self, projection_name: str) -> CorrespondenceResult | None:
        """Get the most recent check for a projection."""
        history = self._history.get(projection_name)
        if not history:
            return None
        return history[-1]

    def summary(self) -> dict[str, Any]:
        """Summary of all projections' latest correspondence status."""
        result: dict[str, Any] = {
            "last_check_time": self._last_check_time,
            "interval_seconds": self._interval,
            "projections": {},
            "total_regressions": len(self._alerts),
        }
        for name, history in self._history.items():
            if history:
                latest = history[-1]
                result["projections"][name] = {
                    "correspondence": latest.correspondence.value,
                    "certification_level": latest.certification_after,
                    "check_count": len(history),
                    "last_checked": latest.checked_at.isoformat(),
                }
        return result

    def _get_projection_names(self) -> list[str]:
        """Get projection names from registry."""
        if hasattr(self._registry, "list_projections"):
            return self._registry.list_projections()
        if hasattr(self._registry, "_configs"):
            return list(self._registry._configs.keys())
        return []

    def _get_last_known_level(self, name: str) -> int | None:
        """Get the last known certification level for a projection."""
        history = self._history.get(name)
        if not history:
            return None
        return history[-1].certification_after

    def _record(self, name: str, result: CorrespondenceResult) -> None:
        """Record a check result in the ring buffer."""
        if name not in self._history:
            self._history[name] = deque(maxlen=self._max_history)
        self._history[name].append(result)

    def _emit_alert(self, alert: RegressionAlert) -> None:
        """Emit a CRITICAL attention item for a regression."""
        logger.critical(
            "PROJECTION REGRESSION: %s (L%d → L%d)",
            alert.projection_name,
            alert.level_before,
            alert.level_after,
        )
        if self._attention is not None:
            try:
                self._attention.emit_critical(
                    source="correspondence_scheduler",
                    title=f"Projection regression: {alert.projection_name}",
                    detail=alert.detail,
                )
            except Exception as exc:
                logger.debug("Failed to emit attention alert: %s", exc)
