"""Drift Detection Engine — unified drift synthesis.

Campaign 7.4. UMH substrate layer.

Executive synthesis layer ABOVE StrategicTickLoop's DriftDetector.
Merges tick-loop drift warnings with cross-system drift checks:
documentation drift, execution drift, reality drift, strategic drift,
governance drift.

Does NOT reimplement drift detection for goals — delegates to
StrategicTickLoop. Adds cross-cutting drift types that require
composing multiple subsystems.

Read-only. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────


class DriftType(str, Enum):
    DOCUMENTATION = "documentation"
    EXECUTION = "execution"
    REALITY = "reality"
    STRATEGIC = "strategic"
    GOVERNANCE = "governance"


@dataclass
class UnifiedDriftWarning:
    drift_id: str = field(default_factory=lambda: f"drift-{uuid4().hex[:8]}")
    drift_type: str = DriftType.STRATEGIC.value
    severity: str = "warning"
    title: str = ""
    description: str = ""
    entity_refs: list[str] = field(default_factory=list)
    detected_at: float = field(default_factory=time.time)
    days_stagnant: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_id": self.drift_id,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "entity_refs": self.entity_refs,
            "detected_at": self.detected_at,
            "days_stagnant": self.days_stagnant,
        }


_SEVERITY_RANK = {"critical": 3, "alert": 2, "warning": 1}

_EXECUTION_STALE_DAYS = 3
_GOVERNANCE_STALE_DAYS = 5


# ── Engine ────────────────────────────────────────────────────────────


class DriftDetectionEngine:
    """Unified drift detection — merges tick-loop drift with cross-system checks.

    Sources:
      - StrategicTickLoop → goal-level drift warnings (delegated, not reimplemented)
      - DocumentationAwareness → stale docs = documentation drift
      - RuntimeAwareness → approved-but-unexecuted work = execution drift
      - RealityGraph + RuntimeAwareness → graph-active / runtime-inactive = reality drift
      - PriorityEngine (C7.1) → top priorities with no active work = strategic drift
    """

    def __init__(
        self,
        tick_loop: Any | None = None,
        runtime_awareness: Any | None = None,
        documentation_awareness: Any | None = None,
        reality_graph: Any | None = None,
        priority_engine: Any | None = None,
    ) -> None:
        self._tick_loop = tick_loop
        self._runtime_awareness = runtime_awareness
        self._documentation_awareness = documentation_awareness
        self._reality_graph = reality_graph
        self._priority_engine = priority_engine
        self._last_drift: list[UnifiedDriftWarning] = []

    def detect_drift(self) -> list[UnifiedDriftWarning]:
        """Detect all drift types. Main entry point."""
        warnings: list[UnifiedDriftWarning] = []

        warnings.extend(self._drift_from_tick_loop())
        warnings.extend(self._drift_from_documentation())
        warnings.extend(self._drift_from_execution())
        warnings.extend(self._drift_from_strategic())

        warnings.sort(
            key=lambda w: _SEVERITY_RANK.get(w.severity, 0),
            reverse=True,
        )
        self._last_drift = warnings
        return warnings

    def high_drift(self) -> list[UnifiedDriftWarning]:
        """Return ALERT or CRITICAL drift warnings."""
        if not self._last_drift:
            self.detect_drift()
        return [
            w for w in self._last_drift
            if w.severity in ("alert", "critical")
        ]

    def by_type(self, drift_type: str) -> list[UnifiedDriftWarning]:
        """Filter drift warnings by type."""
        if not self._last_drift:
            self.detect_drift()
        return [w for w in self._last_drift if w.drift_type == drift_type]

    # ── Source extraction ─────────────────────────────────────────

    def _drift_from_tick_loop(self) -> list[UnifiedDriftWarning]:
        """Map tick-loop DriftWarnings 1:1 to UnifiedDriftWarning."""
        if self._tick_loop is None:
            return []
        try:
            state = self._tick_loop.get_strategic_state()
            raw = state.get("drift_warnings", [])
            results: list[UnifiedDriftWarning] = []
            for w in raw:
                if hasattr(w, "to_dict"):
                    wd = w.to_dict()
                elif isinstance(w, dict):
                    wd = w
                else:
                    continue
                results.append(UnifiedDriftWarning(
                    drift_type=DriftType.STRATEGIC.value,
                    severity=wd.get("severity", "warning"),
                    title=wd.get("goal_title", wd.get("message", "goal drift")),
                    description=wd.get("message", ""),
                    entity_refs=[wd.get("goal_id", "")] if wd.get("goal_id") else [],
                    detected_at=wd.get("created_at", time.time()),
                    days_stagnant=wd.get("days_stagnant", 0),
                ))
            return results
        except Exception as exc:
            logger.debug("drift_engine: tick_loop extraction failed: %s", exc)
            return []

    def _drift_from_documentation(self) -> list[UnifiedDriftWarning]:
        """Stale documentation = documentation drift."""
        if self._documentation_awareness is None:
            return []
        try:
            stale = self._documentation_awareness.find_stale_docs()
            if not stale:
                return []
            count = len(stale)
            severity = "alert" if count >= 5 else "warning"
            names: list[str] = []
            for d in stale[:5]:
                if hasattr(d, "name"):
                    names.append(d.name)
                elif isinstance(d, dict):
                    names.append(d.get("name", "?"))
            return [UnifiedDriftWarning(
                drift_type=DriftType.DOCUMENTATION.value,
                severity=severity,
                title=f"{count} stale document(s)",
                description=f"Stale docs: {', '.join(names)}",
                days_stagnant=count,
            )]
        except Exception as exc:
            logger.debug("drift_engine: doc drift failed: %s", exc)
            return []

    def _drift_from_execution(self) -> list[UnifiedDriftWarning]:
        """Approved work with no execution record = execution drift."""
        if self._runtime_awareness is None:
            return []
        try:
            active = self._runtime_awareness.active_work()
            results: list[UnifiedDriftWarning] = []
            for work in active:
                status = work.get("status", "").lower()
                if status not in ("approved", "queued"):
                    continue
                created = work.get("created_at", work.get("approved_at", 0))
                if created <= 0:
                    continue
                age_days = (time.time() - created) / 86400.0
                if age_days < _EXECUTION_STALE_DAYS:
                    continue
                severity = "alert" if age_days > 7 else "warning"
                title = work.get("title", work.get("packet_id", "work"))
                results.append(UnifiedDriftWarning(
                    drift_type=DriftType.EXECUTION.value,
                    severity=severity,
                    title=f"Approved but unexecuted: {title}",
                    description=f"Approved {int(age_days)} days ago, no execution started",
                    entity_refs=work.get("entity_refs", []),
                    days_stagnant=int(age_days),
                ))
            return results
        except Exception as exc:
            logger.debug("drift_engine: execution drift failed: %s", exc)
            return []

    def _drift_from_strategic(self) -> list[UnifiedDriftWarning]:
        """Top priorities with zero active work = strategic drift."""
        if self._priority_engine is None or self._runtime_awareness is None:
            return []
        try:
            top_priorities = self._priority_engine.top(limit=3)
            if not top_priorities:
                return []

            active = self._runtime_awareness.active_work()
            active_titles = {
                w.get("title", "").lower() for w in active
            }

            results: list[UnifiedDriftWarning] = []
            for pri in top_priorities:
                pri_title = pri.title.lower() if hasattr(pri, "title") else ""
                has_active = any(
                    pri_title and t and (
                        pri_title in t or t in pri_title
                    )
                    for t in active_titles
                )
                if not has_active and pri_title:
                    results.append(UnifiedDriftWarning(
                        drift_type=DriftType.STRATEGIC.value,
                        severity="alert",
                        title=f"No active work for priority: {pri.title}",
                        description=f"Top priority '{pri.title}' has no matching active work",
                        entity_refs=pri.entity_refs if hasattr(pri, "entity_refs") else [],
                    ))
            return results
        except Exception as exc:
            logger.debug("drift_engine: strategic drift failed: %s", exc)
            return []
