"""C15.3 — Organism Portfolio Runtime.

Top-level organism health aggregation. Composes governance, coordination,
institutional memory, and all 5 portfolio runtimes into a single
coherence view.

No execution authority. No mutation authority. No direct mutation of
goals, work, decisions, memory, capabilities, allocations, or approvals.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────


class OrganismHealth(str, Enum):
    COHERENT = "coherent"
    ALIGNED = "aligned"
    STRAINED = "strained"
    FRAGMENTED = "fragmented"
    CRITICAL = "critical"


class OrganismDriftType(str, Enum):
    GOVERNANCE_DRIFT = "governance_drift"
    COORDINATION_DRIFT = "coordination_drift"
    INSTITUTIONAL_MEMORY_DRIFT = "institutional_memory_drift"
    EXECUTIVE_DRIFT = "executive_drift"
    PREDICTION_DRIFT = "prediction_drift"
    LEARNING_DRIFT = "learning_drift"
    WORK_DRIFT = "work_drift"
    CAPABILITY_DRIFT = "capability_drift"


@dataclass
class OrganismDriftWarning:
    drift_type: str = OrganismDriftType.GOVERNANCE_DRIFT.value
    severity: str = "low"
    description: str = ""
    affected_ids: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SubsystemHealthEntry:
    subsystem: str = ""
    health: str = "unknown"
    drift_count: int = 0
    score: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganismPortfolioSnapshot:
    organism_health: str = OrganismHealth.ALIGNED.value
    coherence_score: float = 0.5
    subsystem_health: list[dict[str, Any]] = field(default_factory=list)
    governance_health: str = "unknown"
    coordination_health: str = "unknown"
    institutional_memory_health: str = "unknown"
    executive_health: str = "unknown"
    prediction_health: str = "unknown"
    learning_health: str = "unknown"
    work_health: str = "unknown"
    capability_health: str = "unknown"
    drift_warnings: list[dict[str, Any]] = field(default_factory=list)
    total_drift_count: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Health Score Mapping ─────────────────────────────────────────────

_HEALTH_SCORE: dict[str, float] = {
    # Best tier
    "coherent": 1.0, "synchronized": 1.0, "optimized": 1.0,
    "thriving": 1.0, "high_confidence": 1.0,
    # Good tier
    "aligned": 0.7, "focused": 0.7, "healthy": 0.7,
    "growing": 0.7, "stable": 0.7, "balanced": 0.7,
    # Degraded tier
    "strained": 0.4, "fragmented": 0.4, "drifting": 0.4,
    "stagnant": 0.4, "uncertain": 0.4, "constrained": 0.4,
    # Bad tier
    "overcommitted": 0.2, "decaying": 0.2, "volatile": 0.2,
    "stalled": 0.2,
    # Critical tier
    "critical": 0.1, "blind": 0.1,
}

# Governance and coordination get 1.5x weight
_SUBSYSTEM_WEIGHTS: dict[str, float] = {
    "governance": 1.5,
    "coordination": 1.5,
    "institutional_memory": 1.0,
    "executive": 1.0,
    "prediction": 1.0,
    "learning": 1.0,
    "work": 1.0,
    "capability": 1.0,
}


def _health_to_score(health_str: str) -> float:
    return _HEALTH_SCORE.get(health_str, 0.5)


# ── Runtime ──────────────────────────────────────────────────────────


class OrganismPortfolioRuntime:
    """Top-level organism health aggregation.

    Composes 3 C15 runtimes + 5 campaign portfolio runtimes into
    a unified coherence view with drift aggregation.
    """

    def __init__(
        self,
        governance_runtime: Any | None = None,
        coordination_engine: Any | None = None,
        institutional_memory: Any | None = None,
        executive_portfolio: Any | None = None,
        prediction_portfolio: Any | None = None,
        work_portfolio: Any | None = None,
        learning_portfolio: Any | None = None,
        capability_portfolio: Any | None = None,
    ) -> None:
        self._governance_runtime = governance_runtime
        self._coordination_engine = coordination_engine
        self._institutional_memory = institutional_memory
        self._executive_portfolio = executive_portfolio
        self._prediction_portfolio = prediction_portfolio
        self._work_portfolio = work_portfolio
        self._learning_portfolio = learning_portfolio
        self._capability_portfolio = capability_portfolio

    # ── Lazy Properties ──────────────────────────────────────────────

    @property
    def _governance(self) -> Any:
        if self._governance_runtime is None:
            try:
                from substrate.organism.governance_runtime import GovernanceRuntime

                self._governance_runtime = GovernanceRuntime()
            except Exception:
                logger.debug("Failed to init GovernanceRuntime", exc_info=True)
        return self._governance_runtime

    @property
    def _coordination(self) -> Any:
        if self._coordination_engine is None:
            try:
                from substrate.organism.organism_coordination_engine import (
                    OrganismCoordinationEngine,
                )

                self._coordination_engine = OrganismCoordinationEngine()
            except Exception:
                logger.debug("Failed to init OrganismCoordinationEngine", exc_info=True)
        return self._coordination_engine

    @property
    def _institutional(self) -> Any:
        if self._institutional_memory is None:
            try:
                from substrate.organism.institutional_memory_runtime import (
                    InstitutionalMemoryRuntime,
                )

                self._institutional_memory = InstitutionalMemoryRuntime()
            except Exception:
                logger.debug("Failed to init InstitutionalMemoryRuntime", exc_info=True)
        return self._institutional_memory

    @property
    def _executive(self) -> Any:
        if self._executive_portfolio is None:
            try:
                from substrate.organism.executive_portfolio_runtime import (
                    ExecutivePortfolioRuntime,
                )

                self._executive_portfolio = ExecutivePortfolioRuntime()
            except Exception:
                logger.debug("Failed to init ExecutivePortfolioRuntime", exc_info=True)
        return self._executive_portfolio

    @property
    def _prediction(self) -> Any:
        if self._prediction_portfolio is None:
            try:
                from substrate.organism.prediction_portfolio_runtime import (
                    PredictionPortfolioRuntime,
                )

                self._prediction_portfolio = PredictionPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init PredictionPortfolioRuntime", exc_info=True)
        return self._prediction_portfolio

    @property
    def _work(self) -> Any:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import (
                    WorkPortfolioRuntime,
                )

                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init WorkPortfolioRuntime", exc_info=True)
        return self._work_portfolio

    @property
    def _learning(self) -> Any:
        if self._learning_portfolio is None:
            try:
                from substrate.organism.learning_portfolio_runtime import (
                    LearningPortfolioRuntime,
                )

                self._learning_portfolio = LearningPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init LearningPortfolioRuntime", exc_info=True)
        return self._learning_portfolio

    @property
    def _capability(self) -> Any:
        if self._capability_portfolio is None:
            try:
                from substrate.organism.capability_portfolio_runtime import (
                    CapabilityPortfolioRuntime,
                )

                self._capability_portfolio = CapabilityPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init CapabilityPortfolioRuntime", exc_info=True)
        return self._capability_portfolio

    # ── Public API ───────────────────────────────────────────────────

    def coherence_score(self) -> float:
        """Weighted average of all subsystem health scores (0.0-1.0)."""
        entries = self.subsystem_health()
        if not entries:
            return 0.5

        weighted_sum = 0.0
        weight_total = 0.0
        for entry in entries:
            w = _SUBSYSTEM_WEIGHTS.get(entry.subsystem, 1.0)
            weighted_sum += entry.score * w
            weight_total += w

        return round(weighted_sum / weight_total, 4) if weight_total > 0 else 0.5

    def subsystem_health(self) -> list[SubsystemHealthEntry]:
        """Health status of every subsystem."""
        entries: list[SubsystemHealthEntry] = []
        for name, subsys in self._subsystem_list():
            h_str = "unknown"
            drift_count = 0
            if subsys is not None:
                try:
                    h = subsys.health() if hasattr(subsys, "health") else None
                    h_str = h.value if hasattr(h, "value") else str(h) if h else "unknown"
                except Exception:
                    logger.debug("Error getting health for %s", name, exc_info=True)

                try:
                    drifts = self._get_drift_list(subsys)
                    drift_count = len(drifts)
                except Exception:
                    logger.debug("Error getting drift for %s", name, exc_info=True)

            entries.append(SubsystemHealthEntry(
                subsystem=name,
                health=h_str,
                drift_count=drift_count,
                score=_health_to_score(h_str),
            ))
        return entries

    def drift_warnings(self) -> list[OrganismDriftWarning]:
        """Aggregate drift warnings from all subsystems."""
        warnings: list[OrganismDriftWarning] = []

        drift_type_map = {
            "governance": OrganismDriftType.GOVERNANCE_DRIFT.value,
            "coordination": OrganismDriftType.COORDINATION_DRIFT.value,
            "institutional_memory": OrganismDriftType.INSTITUTIONAL_MEMORY_DRIFT.value,
            "executive": OrganismDriftType.EXECUTIVE_DRIFT.value,
            "prediction": OrganismDriftType.PREDICTION_DRIFT.value,
            "learning": OrganismDriftType.LEARNING_DRIFT.value,
            "work": OrganismDriftType.WORK_DRIFT.value,
            "capability": OrganismDriftType.CAPABILITY_DRIFT.value,
        }

        for name, subsys in self._subsystem_list():
            if subsys is None:
                continue
            try:
                drifts = self._get_drift_list(subsys)
                for d in drifts:
                    severity = "low"
                    description = ""
                    affected = []
                    if hasattr(d, "severity"):
                        severity = d.severity
                    elif isinstance(d, dict):
                        severity = d.get("severity", "low")
                    if hasattr(d, "description"):
                        description = d.description
                    elif isinstance(d, dict):
                        description = d.get("description", "")
                    if hasattr(d, "affected_ids"):
                        affected = d.affected_ids
                    elif isinstance(d, dict):
                        affected = d.get("affected_ids", [])

                    warnings.append(OrganismDriftWarning(
                        drift_type=drift_type_map.get(name, OrganismDriftType.GOVERNANCE_DRIFT.value),
                        severity=severity,
                        description=f"[{name}] {description}",
                        affected_ids=affected if isinstance(affected, list) else [],
                        recommendation=f"Review {name} subsystem drift",
                    ))
            except Exception:
                logger.debug("Error collecting drift from %s", name, exc_info=True)

        return warnings

    def health(self) -> OrganismHealth:
        """Classify overall organism health."""
        score = self.coherence_score()
        drift = self.drift_warnings()
        total_drift = len(drift)

        has_critical = any(w.severity == "critical" for w in drift)

        if has_critical or score < 0.3:
            return OrganismHealth.CRITICAL
        if score < 0.5 or total_drift >= 9:
            return OrganismHealth.FRAGMENTED
        if score < 0.7 or total_drift >= 4:
            return OrganismHealth.STRAINED
        if total_drift > 0:
            return OrganismHealth.ALIGNED
        return OrganismHealth.COHERENT

    def snapshot(self) -> OrganismPortfolioSnapshot:
        """Full organism portfolio snapshot."""
        entries = self.subsystem_health()
        drift = self.drift_warnings()
        health_map = {e.subsystem: e.health for e in entries}

        return OrganismPortfolioSnapshot(
            organism_health=self.health().value,
            coherence_score=self.coherence_score(),
            subsystem_health=[e.to_dict() for e in entries],
            governance_health=health_map.get("governance", "unknown"),
            coordination_health=health_map.get("coordination", "unknown"),
            institutional_memory_health=health_map.get("institutional_memory", "unknown"),
            executive_health=health_map.get("executive", "unknown"),
            prediction_health=health_map.get("prediction", "unknown"),
            learning_health=health_map.get("learning", "unknown"),
            work_health=health_map.get("work", "unknown"),
            capability_health=health_map.get("capability", "unknown"),
            drift_warnings=[w.to_dict() for w in drift],
            total_drift_count=len(drift),
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Quick summary dict."""
        return {
            "organism_health": self.health().value,
            "coherence_score": self.coherence_score(),
            "total_drift_count": len(self.drift_warnings()),
            "subsystem_count": len(self._subsystem_list()),
        }

    # ── Helpers ───────────────────────────────────────────────────────

    def _subsystem_list(self) -> list[tuple[str, Any]]:
        return [
            ("governance", self._governance),
            ("coordination", self._coordination),
            ("institutional_memory", self._institutional),
            ("executive", self._executive),
            ("prediction", self._prediction),
            ("learning", self._learning),
            ("work", self._work),
            ("capability", self._capability),
        ]

    def _get_drift_list(self, subsys: Any) -> list[Any]:
        """Get drift/issues from a subsystem, handling different method names."""
        if hasattr(subsys, "drift_warnings"):
            return subsys.drift_warnings()
        if hasattr(subsys, "detect_drift"):
            return subsys.detect_drift()
        if hasattr(subsys, "detect_issues"):
            return subsys.detect_issues()
        return []
