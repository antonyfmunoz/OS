"""
Learning Portfolio Runtime — Campaign 12.3

Composition façade aggregating all learning subsystems into a single
portfolio health model with drift detection.

Operator questions answered:
  - Is the system becoming smarter?
  - Is learning converting to capability?
  - Where is the learning pipeline stalled?
  - What's the compounding velocity?
  - Are there blind spots in our learning?

Composes:
  - LearningExtractionRuntime (C12.0)
  - OutcomePatternEngine (C12.1)
  - CapabilityEvolutionEngine (C12.2)
  - OutcomeLearningLoop (mechanical authority)
  - CompoundingEngine (promotion pipeline)
  - WorkPortfolioRuntime (C11.2) — cross-portfolio signals
  - CapabilityPortfolioRuntime (C10.2)

No persistence — pure read-only composition.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class LearningHealth(str, Enum):
    """Portfolio-level learning health classification."""
    THRIVING = "thriving"
    HEALTHY = "healthy"
    STAGNANT = "stagnant"
    DECLINING = "declining"
    CRITICAL = "critical"


class LearningDriftType(str, Enum):
    """Types of learning drift that indicate pipeline problems."""
    LESSON_STALENESS = "lesson_staleness"
    PATTERN_BLINDNESS = "pattern_blindness"
    CAPABILITY_STALL = "capability_stall"
    OUTCOME_LOOP_SILENCE = "outcome_loop_silence"
    COMPOUNDING_BLOCKAGE = "compounding_blockage"


@dataclass
class LearningDriftWarning:
    """A specific drift warning with severity and recommendation."""
    drift_type: str = LearningDriftType.LESSON_STALENESS.value
    severity: str = "low"
    description: str = ""
    affected_ids: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearningPortfolioSnapshot:
    """Full portfolio snapshot across all learning subsystems."""
    lesson_count: int = 0
    actionable_lesson_count: int = 0
    pattern_count: int = 0
    active_trajectories: int = 0
    advancing_capabilities: int = 0
    declining_capabilities: int = 0
    stalled_capabilities: int = 0
    compounding_score: float = 0.0
    lesson_velocity: float = 0.0
    pattern_velocity: float = 0.0
    evolution_velocity: float = 0.0
    outcome_loop_health: str = "unknown"
    drift_warnings: list[dict[str, Any]] = field(default_factory=list)
    health: str = LearningHealth.STAGNANT.value
    top_lessons: list[dict[str, Any]] = field(default_factory=list)
    top_patterns: list[dict[str, Any]] = field(default_factory=list)
    top_trajectories: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["compounding_score"] = round(self.compounding_score, 4)
        d["lesson_velocity"] = round(self.lesson_velocity, 4)
        d["pattern_velocity"] = round(self.pattern_velocity, 4)
        d["evolution_velocity"] = round(self.evolution_velocity, 4)
        return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Drift thresholds
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_LESSON_STALE_DAYS = 7
_OUTCOME_SILENCE_DAYS = 3
_COMPOUNDING_BLOCK_DAYS = 14
_CAPABILITY_STALL_RATIO = 0.7


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class LearningPortfolioRuntime:
    """Composition façade for all learning subsystems."""

    def __init__(
        self,
        learning_extraction: Any | None = None,
        outcome_patterns: Any | None = None,
        capability_evolution: Any | None = None,
        outcome_learning: Any | None = None,
        compounding_engine: Any | None = None,
        work_portfolio: Any | None = None,
        capability_portfolio: Any | None = None,
    ) -> None:
        self._learning_extraction = learning_extraction
        self._outcome_patterns = outcome_patterns
        self._capability_evolution = capability_evolution
        self._outcome_learning = outcome_learning
        self._compounding_engine = compounding_engine
        self._work_portfolio = work_portfolio
        self._capability_portfolio = capability_portfolio

    # ── Lazy subsystem access ────────────────────────────────────────────

    @property
    def learning_extraction(self) -> Any | None:
        if self._learning_extraction is None:
            try:
                from substrate.organism.learning_extraction_runtime import LearningExtractionRuntime
                self._learning_extraction = LearningExtractionRuntime()
            except Exception:
                logger.debug("LearningExtractionRuntime unavailable")
        return self._learning_extraction

    @property
    def outcome_patterns(self) -> Any | None:
        if self._outcome_patterns is None:
            try:
                from substrate.organism.outcome_pattern_engine import OutcomePatternEngine
                self._outcome_patterns = OutcomePatternEngine()
            except Exception:
                logger.debug("OutcomePatternEngine unavailable")
        return self._outcome_patterns

    @property
    def capability_evolution(self) -> Any | None:
        if self._capability_evolution is None:
            try:
                from substrate.organism.capability_evolution_engine import CapabilityEvolutionEngine
                self._capability_evolution = CapabilityEvolutionEngine()
            except Exception:
                logger.debug("CapabilityEvolutionEngine unavailable")
        return self._capability_evolution

    @property
    def outcome_learning(self) -> Any | None:
        if self._outcome_learning is None:
            try:
                from substrate.organism.outcome_learning import OutcomeLearningLoop
                self._outcome_learning = OutcomeLearningLoop()
            except Exception:
                logger.debug("OutcomeLearningLoop unavailable")
        return self._outcome_learning

    @property
    def compounding_engine(self) -> Any | None:
        if self._compounding_engine is None:
            try:
                from substrate.organism.compounding_engine import CompoundingEngine
                self._compounding_engine = CompoundingEngine()
            except Exception:
                logger.debug("CompoundingEngine unavailable")
        return self._compounding_engine

    @property
    def work_portfolio(self) -> Any | None:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime
                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("WorkPortfolioRuntime unavailable")
        return self._work_portfolio

    @property
    def capability_portfolio(self) -> Any | None:
        if self._capability_portfolio is None:
            try:
                from substrate.organism.capability_portfolio_runtime import CapabilityPortfolioRuntime
                self._capability_portfolio = CapabilityPortfolioRuntime()
            except Exception:
                logger.debug("CapabilityPortfolioRuntime unavailable")
        return self._capability_portfolio

    # ── Drift detection ──────────────────────────────────────────────────

    def drift_warnings(self) -> list[LearningDriftWarning]:
        """Detect learning pipeline drift across all subsystems."""
        warnings: list[LearningDriftWarning] = []

        self._check_lesson_staleness(warnings)
        self._check_pattern_blindness(warnings)
        self._check_capability_stall(warnings)
        self._check_outcome_silence(warnings)
        self._check_compounding_blockage(warnings)

        return warnings

    def _check_lesson_staleness(self, warnings: list[LearningDriftWarning]) -> None:
        le = self.learning_extraction
        if le is None:
            return
        try:
            snap = le.snapshot()
            if snap.staleness_score > 0.8:
                warnings.append(LearningDriftWarning(
                    drift_type=LearningDriftType.LESSON_STALENESS.value,
                    severity="high" if snap.staleness_score > 0.95 else "medium",
                    description=f"No new lessons in {_LESSON_STALE_DAYS}+ days; {snap.staleness_score:.0%} of lessons are stale",
                    recommendation="Run extract_batch() to search for new learning opportunities",
                ))
        except Exception:
            logger.debug("Failed to check lesson staleness")

    def _check_pattern_blindness(self, warnings: list[LearningDriftWarning]) -> None:
        ol = self.outcome_learning
        op = self.outcome_patterns
        if ol is None or op is None:
            return
        try:
            outcomes = ol.recent_outcomes(limit=20)
            pat_snap = op.snapshot()
            if len(outcomes) > 5 and pat_snap.total_patterns == 0:
                warnings.append(LearningDriftWarning(
                    drift_type=LearningDriftType.PATTERN_BLINDNESS.value,
                    severity="medium",
                    description=f"{len(outcomes)} outcomes recorded but zero patterns detected",
                    recommendation="Run detect_patterns() — outcomes exist but patterns are not being extracted",
                ))
        except Exception:
            logger.debug("Failed to check pattern blindness")

    def _check_capability_stall(self, warnings: list[LearningDriftWarning]) -> None:
        ce = self.capability_evolution
        if ce is None:
            return
        try:
            snap = ce.snapshot()
            total = snap.total_capabilities
            if total > 0 and snap.stalled_count / total > _CAPABILITY_STALL_RATIO:
                warnings.append(LearningDriftWarning(
                    drift_type=LearningDriftType.CAPABILITY_STALL.value,
                    severity="high",
                    description=f"{snap.stalled_count}/{total} capabilities stalled (>{_CAPABILITY_STALL_RATIO:.0%} threshold)",
                    recommendation="Review stalled capabilities — they may need active investment or retirement",
                ))
        except Exception:
            logger.debug("Failed to check capability stall")

    def _check_outcome_silence(self, warnings: list[LearningDriftWarning]) -> None:
        ol = self.outcome_learning
        if ol is None:
            return
        try:
            outcomes = ol.recent_outcomes(limit=5)
            if not outcomes:
                warnings.append(LearningDriftWarning(
                    drift_type=LearningDriftType.OUTCOME_LOOP_SILENCE.value,
                    severity="high",
                    description="No outcomes recorded — the learning pipeline has no input",
                    recommendation="Verify OutcomeLearningLoop is receiving execution results",
                ))
            else:
                most_recent_ts = max(getattr(o, "timestamp", 0.0) for o in outcomes)
                age_days = (time.time() - most_recent_ts) / 86400
                if age_days > _OUTCOME_SILENCE_DAYS:
                    warnings.append(LearningDriftWarning(
                        drift_type=LearningDriftType.OUTCOME_LOOP_SILENCE.value,
                        severity="medium",
                        description=f"Last outcome was {age_days:.1f} days ago",
                        recommendation="Check if execution is occurring — outcomes should flow continuously",
                    ))
        except Exception:
            logger.debug("Failed to check outcome silence")

    def _check_compounding_blockage(self, warnings: list[LearningDriftWarning]) -> None:
        ce = self.compounding_engine
        if ce is None:
            return
        try:
            report = ce.compounding_report(days=_COMPOUNDING_BLOCK_DAYS)
            pending = report.get("pending_count", 0)
            promoted = report.get("promoted_count", 0)
            if pending > 3 and promoted == 0:
                warnings.append(LearningDriftWarning(
                    drift_type=LearningDriftType.COMPOUNDING_BLOCKAGE.value,
                    severity="medium",
                    description=f"{pending} promotion candidates pending but 0 promoted in {_COMPOUNDING_BLOCK_DAYS}d",
                    recommendation="Review pending candidates — learning exists but is not converting to capability",
                ))
        except Exception:
            logger.debug("Failed to check compounding blockage")

    # ── Compounding score ────────────────────────────────────────────────

    def compounding_score(self) -> float:
        """Weighted score of how well learning converts to capability growth."""
        scores: list[float] = []
        weights: list[float] = []

        # Outcome learning reliability growth
        ol = self.outcome_learning
        if ol is not None:
            try:
                summary = ol.summary()
                reliabilities = summary.get("reliability_scores", {})
                if reliabilities:
                    avg_rel = sum(reliabilities.values()) / len(reliabilities)
                    scores.append(avg_rel)
                    weights.append(0.2)
            except Exception:
                pass

        # Lesson velocity
        le = self.learning_extraction
        if le is not None:
            try:
                snap = le.snapshot()
                vel = min(snap.extraction_velocity / 2.0, 1.0)
                scores.append(vel)
                weights.append(0.25)
            except Exception:
                pass

        # Pattern detection rate
        op = self.outcome_patterns
        if op is not None:
            try:
                snap = op.snapshot()
                pvel = min(snap.pattern_velocity / 1.0, 1.0)
                scores.append(pvel)
                weights.append(0.2)
            except Exception:
                pass

        # Capability evolution rate
        ce = self.capability_evolution
        if ce is not None:
            try:
                snap = ce.snapshot()
                total = snap.total_capabilities
                if total > 0:
                    advance_ratio = snap.advancing_count / total
                    scores.append(advance_ratio)
                    weights.append(0.2)
            except Exception:
                pass

        # CompoundingEngine promotion rate
        comp = self.compounding_engine
        if comp is not None:
            try:
                report = comp.compounding_report(days=30)
                total = report.get("promoted_count", 0) + report.get("pending_count", 0) + report.get("rejected_count", 0)
                if total > 0:
                    promo_rate = report.get("promoted_count", 0) / total
                    scores.append(promo_rate)
                    weights.append(0.15)
            except Exception:
                pass

        if not scores:
            return 0.0

        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        return sum(s * w for s, w in zip(scores, weights)) / total_weight

    # ── Public API ────────────────────────────────────────────────────────

    def lesson_velocity(self, window_days: float = 7.0) -> float:
        """Lessons extracted per day over the window."""
        le = self.learning_extraction
        if le is None:
            return 0.0
        try:
            snap = le.snapshot()
            return snap.extraction_velocity
        except Exception:
            return 0.0

    def learning_effectiveness(self) -> dict[str, Any]:
        """Ratio of actionable lessons to total, pattern→action conversion."""
        result: dict[str, Any] = {
            "actionable_ratio": 0.0,
            "pattern_to_recommendation_ratio": 0.0,
            "compounding_score": 0.0,
        }

        le = self.learning_extraction
        if le is not None:
            try:
                snap = le.snapshot()
                if snap.total_lessons > 0:
                    result["actionable_ratio"] = round(
                        snap.actionable_count / snap.total_lessons, 4
                    )
            except Exception:
                pass

        op = self.outcome_patterns
        if op is not None:
            try:
                snap = op.snapshot()
                if snap.total_patterns > 0:
                    with_rec = sum(
                        1 for p in op.top_patterns(limit=100)
                        if getattr(p, "recommendation", "")
                    )
                    result["pattern_to_recommendation_ratio"] = round(
                        with_rec / snap.total_patterns, 4
                    )
            except Exception:
                pass

        result["compounding_score"] = round(self.compounding_score(), 4)
        return result

    def health(self) -> LearningHealth:
        """Portfolio-level learning health classification."""
        cs = self.compounding_score()
        lv = self.lesson_velocity()
        drift = self.drift_warnings()

        high_severity = sum(1 for w in drift if w.severity == "high")

        if high_severity >= 3:
            return LearningHealth.CRITICAL
        if cs > 0.6 and lv > 0.5 and high_severity == 0:
            return LearningHealth.THRIVING
        if cs > 0.3 and lv > 0:
            return LearningHealth.HEALTHY
        if cs < 0.1 and lv == 0:
            return LearningHealth.DECLINING
        return LearningHealth.STAGNANT

    def snapshot(self) -> LearningPortfolioSnapshot:
        """Full portfolio snapshot."""
        now = time.time()

        # Lesson data
        lesson_count = 0
        actionable_count = 0
        lesson_vel = 0.0
        top_lessons: list[dict[str, Any]] = []
        le = self.learning_extraction
        if le is not None:
            try:
                snap = le.snapshot()
                lesson_count = snap.total_lessons
                actionable_count = snap.actionable_count
                lesson_vel = snap.extraction_velocity
                top_lessons = snap.top_lessons[:5]
            except Exception:
                pass

        # Pattern data
        pattern_count = 0
        pattern_vel = 0.0
        top_patterns: list[dict[str, Any]] = []
        op = self.outcome_patterns
        if op is not None:
            try:
                snap = op.snapshot()
                pattern_count = snap.total_patterns
                pattern_vel = snap.pattern_velocity
                top_patterns = snap.top_patterns[:5]
            except Exception:
                pass

        # Evolution data
        active_traj = 0
        advancing = 0
        declining = 0
        stalled = 0
        evo_vel = 0.0
        top_trajectories: list[dict[str, Any]] = []
        ce = self.capability_evolution
        if ce is not None:
            try:
                snap = ce.snapshot()
                active_traj = snap.total_capabilities
                advancing = snap.advancing_count
                declining = snap.declining_count
                stalled = snap.stalled_count
                evo_vel = snap.evolution_velocity
                top_trajectories = snap.top_advancing[:3] + snap.top_declining[:2]
            except Exception:
                pass

        # Outcome loop health
        ol_health = "unknown"
        ol = self.outcome_learning
        if ol is not None:
            try:
                summary = ol.summary()
                total = summary.get("total_outcomes", 0)
                if total > 0:
                    ol_health = "active"
                else:
                    ol_health = "silent"
            except Exception:
                pass

        # Drift + health
        drift = self.drift_warnings()
        health_val = self.health()
        cs = self.compounding_score()

        return LearningPortfolioSnapshot(
            lesson_count=lesson_count,
            actionable_lesson_count=actionable_count,
            pattern_count=pattern_count,
            active_trajectories=active_traj,
            advancing_capabilities=advancing,
            declining_capabilities=declining,
            stalled_capabilities=stalled,
            compounding_score=cs,
            lesson_velocity=lesson_vel,
            pattern_velocity=pattern_vel,
            evolution_velocity=evo_vel,
            outcome_loop_health=ol_health,
            drift_warnings=[w.to_dict() for w in drift],
            health=health_val.value,
            top_lessons=top_lessons,
            top_patterns=top_patterns,
            top_trajectories=top_trajectories,
            generated_at=now,
        )

    def summary(self) -> dict[str, Any]:
        """Compact summary for API consumption."""
        snap = self.snapshot()
        return snap.to_dict()
