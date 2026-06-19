"""Capability Compounding Runtime — Campaign 22.4

Operationalized learning composition layer. Unifies the five learning
subsystems into a single view of how production outcomes compound into
reusable organizational assets.

Pipeline:  Outcome → Lesson → Pattern → Capability → Operational Asset

Composes (never replaces):
  - LearningExtractionRuntime (C12.0) — semantic lesson extraction
  - InstitutionalMemoryRuntime (C15.2) — knowledge promotion lifecycle
  - CapabilityEvolutionEngine (C12.2) — capability trajectory tracking
  - OutcomePatternEngine (C12.1) — pattern detection + attribution
  - CompoundingEngine (Gate 9) — 4-tier promotion pipeline

This runtime is read-only composition. It never mutates any source
subsystem directly — it reads across them to build the compounding view.

No LLM calls. All deterministic.
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


class CompoundingStage(str, Enum):
    """Stages in the outcome-to-asset compounding pipeline."""
    OUTCOME = "outcome"
    LESSON = "lesson"
    PATTERN = "pattern"
    CAPABILITY = "capability"
    OPERATIONAL = "operational"


class CompoundingHealth(str, Enum):
    """Overall health of the compounding pipeline."""
    THRIVING = "thriving"
    HEALTHY = "healthy"
    STAGNANT = "stagnant"
    DEGRADED = "degraded"


@dataclass
class CompoundingSnapshot:
    """Full view of the compounding pipeline state."""
    total_outcomes: int = 0
    total_lessons: int = 0
    total_patterns: int = 0
    capabilities_evolved: int = 0
    pending_promotions: int = 0
    institutional_health: str = ""
    compounding_velocity: float = 0.0
    reusable_assets: list[dict[str, Any]] = field(default_factory=list)
    pipeline_stages: dict[str, int] = field(default_factory=dict)
    health: str = CompoundingHealth.STAGNANT.value
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineTrace:
    """Traces a single production through the compounding pipeline."""
    production_id: str = ""
    stages_reached: list[str] = field(default_factory=list)
    current_stage: str = CompoundingStage.OUTCOME.value
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    lessons: list[dict[str, Any]] = field(default_factory=list)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    operational_assets: list[dict[str, Any]] = field(default_factory=list)
    promotions_pending: list[dict[str, Any]] = field(default_factory=list)
    is_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReusableAsset:
    """An asset that has reached operational status through compounding."""
    asset_id: str = ""
    title: str = ""
    asset_type: str = ""
    origin_stage: str = CompoundingStage.OPERATIONAL.value
    source_id: str = ""
    confidence: float = 0.0
    reuse_count: int = 0
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stage Progression Map
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_STAGE_ORDER: list[str] = [
    CompoundingStage.OUTCOME.value,
    CompoundingStage.LESSON.value,
    CompoundingStage.PATTERN.value,
    CompoundingStage.CAPABILITY.value,
    CompoundingStage.OPERATIONAL.value,
]


def _stage_index(stage: str) -> int:
    try:
        return _STAGE_ORDER.index(stage)
    except ValueError:
        return -1


def _next_stage(stage: str) -> str | None:
    idx = _stage_index(stage)
    if idx < 0 or idx >= len(_STAGE_ORDER) - 1:
        return None
    return _STAGE_ORDER[idx + 1]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CapabilityCompoundingRuntime:
    """Composes five learning subsystems into a unified compounding view.

    Reads across LearningExtraction, InstitutionalMemory, CapabilityEvolution,
    OutcomePatterns, and CompoundingEngine to answer:
      - How is production work compounding into organizational capability?
      - What promotions are pending?
      - What reusable assets exist?
      - What is the health of the compounding pipeline?
    """

    def __init__(
        self,
        learning_extraction: Any | None = None,
        institutional_memory: Any | None = None,
        capability_evolution: Any | None = None,
        outcome_patterns: Any | None = None,
        compounding_engine: Any | None = None,
    ) -> None:
        self._learning_extraction_instance = learning_extraction
        self._institutional_memory_instance = institutional_memory
        self._capability_evolution_instance = capability_evolution
        self._outcome_patterns_instance = outcome_patterns
        self._compounding_engine_instance = compounding_engine

    # ── Lazy subsystem access ─────────────────────────────────────────

    @property
    def _learning_extraction(self) -> Any | None:
        if self._learning_extraction_instance is not None:
            return self._learning_extraction_instance
        try:
            from substrate.organism.learning_extraction_runtime import (
                LearningExtractionRuntime,
            )
            self._learning_extraction_instance = LearningExtractionRuntime()
            return self._learning_extraction_instance
        except Exception:
            logger.debug("LearningExtractionRuntime unavailable")
            return None

    @property
    def _institutional_memory(self) -> Any | None:
        if self._institutional_memory_instance is not None:
            return self._institutional_memory_instance
        try:
            from substrate.organism.institutional_memory_runtime import (
                InstitutionalMemoryRuntime,
            )
            self._institutional_memory_instance = InstitutionalMemoryRuntime()
            return self._institutional_memory_instance
        except Exception:
            logger.debug("InstitutionalMemoryRuntime unavailable")
            return None

    @property
    def _capability_evolution(self) -> Any | None:
        if self._capability_evolution_instance is not None:
            return self._capability_evolution_instance
        try:
            from substrate.organism.capability_evolution_engine import (
                CapabilityEvolutionEngine,
            )
            self._capability_evolution_instance = CapabilityEvolutionEngine()
            return self._capability_evolution_instance
        except Exception:
            logger.debug("CapabilityEvolutionEngine unavailable")
            return None

    @property
    def _outcome_patterns(self) -> Any | None:
        if self._outcome_patterns_instance is not None:
            return self._outcome_patterns_instance
        try:
            from substrate.organism.outcome_pattern_engine import (
                OutcomePatternEngine,
            )
            self._outcome_patterns_instance = OutcomePatternEngine()
            return self._outcome_patterns_instance
        except Exception:
            logger.debug("OutcomePatternEngine unavailable")
            return None

    @property
    def _compounding(self) -> Any | None:
        if self._compounding_engine_instance is not None:
            return self._compounding_engine_instance
        try:
            from substrate.organism.compounding_engine import CompoundingEngine
            self._compounding_engine_instance = CompoundingEngine()
            return self._compounding_engine_instance
        except Exception:
            logger.debug("CompoundingEngine unavailable")
            return None

    # ── Pipeline stage counts ─────────────────────────────────────────

    def _count_outcomes(self) -> int:
        """Count outcomes from outcome pattern engine."""
        eng = self._outcome_patterns
        if eng is None:
            return 0
        try:
            snap = eng.snapshot()
            return getattr(snap, "total_patterns", 0)
        except Exception:
            logger.debug("Failed to count outcomes")
            return 0

    def _count_lessons(self) -> int:
        """Count extracted lessons."""
        ext = self._learning_extraction
        if ext is None:
            return 0
        try:
            snap = ext.snapshot()
            return getattr(snap, "total_lessons", 0)
        except Exception:
            logger.debug("Failed to count lessons")
            return 0

    def _count_patterns(self) -> int:
        """Count detected patterns."""
        eng = self._outcome_patterns
        if eng is None:
            return 0
        try:
            snap = eng.snapshot()
            return getattr(snap, "total_patterns", 0)
        except Exception:
            logger.debug("Failed to count patterns")
            return 0

    def _count_capabilities_evolved(self) -> int:
        """Count capabilities that have evolution events."""
        evo = self._capability_evolution
        if evo is None:
            return 0
        try:
            trajectories = evo.all_trajectories()
            return len(trajectories)
        except Exception:
            logger.debug("Failed to count capability evolutions")
            return 0

    def _count_pending_promotions(self) -> int:
        """Count pending promotion candidates."""
        comp = self._compounding
        if comp is None:
            return 0
        try:
            candidates = comp.list_candidates(status="proposed")
            return len(candidates)
        except Exception:
            logger.debug("Failed to count pending promotions")
            return 0

    # ── Institutional health ──────────────────────────────────────────

    def institutional_health(self) -> str:
        """Return health assessment from institutional memory."""
        mem = self._institutional_memory
        if mem is None:
            return "unknown"
        try:
            h = mem.health()
            if hasattr(h, "value"):
                return h.value
            return str(h)
        except Exception:
            logger.debug("Failed to get institutional health")
            return "unknown"

    # ── Compounding velocity ──────────────────────────────────────────

    def _compute_velocity(self) -> float:
        """Compute the rate at which outcomes become operational assets.

        Velocity = promoted_count / total_candidates over last 90 days.
        Higher is better — means the pipeline converts more outcomes.
        """
        comp = self._compounding
        if comp is None:
            return 0.0
        try:
            report = comp.compounding_report(days=90)
            total = report.get("total_candidates", 0)
            promoted = report.get("promoted_count", 0)
            if total == 0:
                return 0.0
            return round(promoted / total, 4)
        except Exception:
            logger.debug("Failed to compute compounding velocity")
            return 0.0

    # ── Reusable assets ───────────────────────────────────────────────

    def reusable_assets(self) -> list[dict[str, Any]]:
        """Return operationalized assets from the compounding pipeline.

        These are promotion candidates that reached PROMOTED status,
        meaning they've been approved and operationalized.
        """
        comp = self._compounding
        if comp is None:
            return []
        try:
            report = comp.improvement_from_executions(n=50)
            promotions = report.get("promotions", [])
            assets: list[dict[str, Any]] = []
            for p in promotions:
                assets.append(ReusableAsset(
                    asset_id=p.get("candidate_id", ""),
                    title=p.get("source_description", ""),
                    asset_type=p.get("promotion_type", ""),
                    origin_stage=CompoundingStage.OPERATIONAL.value,
                    source_id=p.get("source_id", ""),
                    confidence=p.get("confidence", 0.0),
                    reuse_count=0,
                    created_at=p.get("resolved_at", 0.0),
                ).to_dict())
            return assets
        except Exception:
            logger.debug("Failed to list reusable assets")
            return []

    # ── Pipeline trace ────────────────────────────────────────────────

    def production_to_asset_pipeline(self, production_id: str) -> PipelineTrace:
        """Trace a production through the compounding pipeline.

        Given a production_id, find:
          1. Outcomes related to this production
          2. Lessons extracted from those outcomes
          3. Patterns detected from those lessons
          4. Capabilities evolved from those patterns
          5. Operational assets promoted from those capabilities

        Each stage may or may not have data — the trace shows how far
        the production has progressed through the pipeline.
        """
        trace = PipelineTrace(production_id=production_id)
        stages_reached: list[str] = [CompoundingStage.OUTCOME.value]
        current_stage = CompoundingStage.OUTCOME.value

        # Stage 1: Outcomes — check outcome patterns for this production
        eng = self._outcome_patterns
        if eng is not None:
            try:
                all_patterns = eng.top_patterns(limit=100)
                related = [
                    p.to_dict() for p in all_patterns
                    if production_id in p.evidence
                    or production_id in getattr(p, "affected_goals", [])
                ]
                trace.outcomes = related
            except Exception:
                logger.debug("Failed to trace outcomes for %s", production_id)

        # Stage 2: Lessons — check learning extraction
        ext = self._learning_extraction
        if ext is not None:
            try:
                recent = ext.recent_lessons(limit=100)
                related = [
                    l.to_dict() for l in recent
                    if production_id in l.evidence_sources
                    or production_id in l.related_outcome_ids
                ]
                if related:
                    trace.lessons = related
                    stages_reached.append(CompoundingStage.LESSON.value)
                    current_stage = CompoundingStage.LESSON.value
            except Exception:
                logger.debug("Failed to trace lessons for %s", production_id)

        # Stage 3: Patterns — check detected patterns for related lessons
        if eng is not None and trace.lessons:
            try:
                lesson_ids = [
                    l.get("lesson_id", "") for l in trace.lessons
                ]
                all_patterns = eng.top_patterns(limit=200)
                related = [
                    p.to_dict() for p in all_patterns
                    if any(lid in p.evidence for lid in lesson_ids if lid)
                ]
                if related:
                    trace.patterns = related
                    stages_reached.append(CompoundingStage.PATTERN.value)
                    current_stage = CompoundingStage.PATTERN.value
            except Exception:
                logger.debug("Failed to trace patterns for %s", production_id)

        # Stage 4: Capabilities — check evolution for related patterns
        evo = self._capability_evolution
        if evo is not None and trace.patterns:
            try:
                pattern_ids = [
                    p.get("pattern_id", "") for p in trace.patterns
                ]
                trajectories = evo.all_trajectories()
                related = [
                    t.to_dict() for t in trajectories
                    if any(
                        pid in getattr(t, "trigger_patterns", [])
                        for pid in pattern_ids if pid
                    )
                ]
                if related:
                    trace.capabilities = related
                    stages_reached.append(CompoundingStage.CAPABILITY.value)
                    current_stage = CompoundingStage.CAPABILITY.value
            except Exception:
                logger.debug("Failed to trace capabilities for %s", production_id)

        # Stage 5: Operational assets — check promotions
        comp = self._compounding
        if comp is not None:
            try:
                candidates = comp.list_candidates(status="promoted")
                cap_ids = [c.get("capability_id", "") for c in trace.capabilities]
                related = [
                    c.to_dict() for c in candidates
                    if c.source_id in cap_ids
                    or production_id in c.evidence
                ]
                if related:
                    trace.operational_assets = related
                    stages_reached.append(CompoundingStage.OPERATIONAL.value)
                    current_stage = CompoundingStage.OPERATIONAL.value

                # Also check for pending promotions
                pending = comp.list_candidates(status="proposed")
                pending_related = [
                    c.to_dict() for c in pending
                    if production_id in c.evidence
                ]
                trace.promotions_pending = pending_related
            except Exception:
                logger.debug("Failed to trace operational assets for %s", production_id)

        trace.stages_reached = stages_reached
        trace.current_stage = current_stage
        trace.is_complete = current_stage == CompoundingStage.OPERATIONAL.value

        return trace

    # ── Pending promotions ────────────────────────────────────────────

    def pending_promotions(self) -> list[dict[str, Any]]:
        """Return all promotion candidates awaiting approval."""
        comp = self._compounding
        if comp is None:
            return []
        try:
            candidates = comp.list_candidates(status="proposed")
            return [c.to_dict() for c in candidates]
        except Exception:
            logger.debug("Failed to list pending promotions")
            return []

    # ── Health classification ─────────────────────────────────────────

    def _classify_health(self) -> CompoundingHealth:
        """Deterministic health classification based on pipeline metrics.

        THRIVING: velocity > 0.3, institutional health is thriving/growing
        HEALTHY: velocity > 0.1 or institutional health is growing+
        STAGNANT: velocity == 0 but pipeline has data
        DEGRADED: no data in pipeline at all
        """
        velocity = self._compute_velocity()
        inst_health = self.institutional_health()

        total_data = (
            self._count_outcomes()
            + self._count_lessons()
            + self._count_patterns()
        )

        if total_data == 0:
            return CompoundingHealth.DEGRADED

        if velocity > 0.3 and inst_health in ("thriving", "growing"):
            return CompoundingHealth.THRIVING

        if velocity > 0.1 or inst_health in ("thriving", "growing"):
            return CompoundingHealth.HEALTHY

        if velocity == 0.0:
            return CompoundingHealth.STAGNANT

        return CompoundingHealth.HEALTHY

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> CompoundingSnapshot:
        """Full compounding pipeline snapshot composing all 5 subsystems."""
        outcomes = self._count_outcomes()
        lessons = self._count_lessons()
        patterns = self._count_patterns()
        capabilities = self._count_capabilities_evolved()
        pending = self._count_pending_promotions()
        velocity = self._compute_velocity()
        inst_health = self.institutional_health()
        health = self._classify_health()
        assets = self.reusable_assets()

        return CompoundingSnapshot(
            total_outcomes=outcomes,
            total_lessons=lessons,
            total_patterns=patterns,
            capabilities_evolved=capabilities,
            pending_promotions=pending,
            institutional_health=inst_health,
            compounding_velocity=velocity,
            reusable_assets=assets,
            pipeline_stages={
                CompoundingStage.OUTCOME.value: outcomes,
                CompoundingStage.LESSON.value: lessons,
                CompoundingStage.PATTERN.value: patterns,
                CompoundingStage.CAPABILITY.value: capabilities,
                CompoundingStage.OPERATIONAL.value: len(assets),
            },
            health=health.value,
            generated_at=time.time(),
        )

    # ── Summary ───────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Quick summary dict for API responses."""
        snap = self.snapshot()
        return {
            "health": snap.health,
            "total_outcomes": snap.total_outcomes,
            "total_lessons": snap.total_lessons,
            "total_patterns": snap.total_patterns,
            "capabilities_evolved": snap.capabilities_evolved,
            "pending_promotions": snap.pending_promotions,
            "institutional_health": snap.institutional_health,
            "compounding_velocity": snap.compounding_velocity,
            "reusable_asset_count": len(snap.reusable_assets),
            "pipeline_stages": snap.pipeline_stages,
        }
