"""Tests for CapabilityCompoundingRuntime — Campaign 22.4

Self-contained fakes for all 5 composed subsystems.
No conftest. No external dependencies.
"""
from __future__ import annotations

import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/OS")

from substrate.organism.capability_compounding_runtime import (
    CapabilityCompoundingRuntime,
    CompoundingHealth,
    CompoundingSnapshot,
    CompoundingStage,
    PipelineTrace,
    ReusableAsset,
    _next_stage,
    _stage_index,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fakes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class FakePatternSnapshot:
    total_patterns: int = 5


@dataclass
class FakeLessonSnapshot:
    total_lessons: int = 12


@dataclass
class FakeDetectedPattern:
    pattern_id: str = ""
    evidence: list[str] = field(default_factory=list)
    affected_goals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "evidence": self.evidence,
            "affected_goals": self.affected_goals,
        }


@dataclass
class FakeLesson:
    lesson_id: str = ""
    evidence_sources: list[str] = field(default_factory=list)
    related_outcome_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "evidence_sources": self.evidence_sources,
            "related_outcome_ids": self.related_outcome_ids,
        }


@dataclass
class FakeTrajectory:
    capability_id: str = ""
    trigger_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "trigger_patterns": self.trigger_patterns,
        }


@dataclass
class FakePromotionCandidate:
    candidate_id: str = ""
    source_id: str = ""
    source_description: str = ""
    promotion_type: str = "outcome_to_insight"
    confidence: float = 0.8
    evidence: list[str] = field(default_factory=list)
    resolved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_id": self.source_id,
            "source_description": self.source_description,
            "promotion_type": self.promotion_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "resolved_at": self.resolved_at,
        }


class FakeOutcomePatternEngine:
    def __init__(self, patterns: list[FakeDetectedPattern] | None = None):
        self._patterns = patterns or []

    def snapshot(self) -> FakePatternSnapshot:
        return FakePatternSnapshot(total_patterns=len(self._patterns))

    def top_patterns(self, limit: int = 10) -> list[FakeDetectedPattern]:
        return self._patterns[:limit]


class FakeLearningExtractionRuntime:
    def __init__(self, lessons: list[FakeLesson] | None = None):
        self._lessons = lessons or []

    def snapshot(self) -> FakeLessonSnapshot:
        return FakeLessonSnapshot(total_lessons=len(self._lessons))

    def recent_lessons(self, limit: int = 20) -> list[FakeLesson]:
        return self._lessons[:limit]


class FakeCapabilityEvolutionEngine:
    def __init__(self, trajectories: list[FakeTrajectory] | None = None):
        self._trajectories = trajectories or []

    def all_trajectories(self) -> list[FakeTrajectory]:
        return self._trajectories


class FakeInstitutionalMemoryRuntime:
    def __init__(self, health_val: str = "growing"):
        self._health_val = health_val

    def health(self) -> MagicMock:
        h = MagicMock()
        h.value = self._health_val
        return h

    def snapshot(self) -> MagicMock:
        s = MagicMock()
        s.memory_health = self._health_val
        return s


class FakeCompoundingEngine:
    def __init__(
        self,
        candidates: list[FakePromotionCandidate] | None = None,
        promoted: list[FakePromotionCandidate] | None = None,
    ):
        self._proposed = candidates or []
        self._promoted = promoted or []

    def list_candidates(self, status: str = "proposed") -> list[FakePromotionCandidate]:
        if status == "proposed":
            return self._proposed
        if status == "promoted":
            return self._promoted
        return []

    def compounding_report(self, days: int = 90) -> dict[str, Any]:
        total = len(self._proposed) + len(self._promoted)
        return {
            "total_candidates": total,
            "promoted_count": len(self._promoted),
        }

    def improvement_from_executions(self, n: int = 100) -> dict[str, Any]:
        return {
            "recent_promotions": len(self._promoted),
            "promotions": [p.to_dict() for p in self._promoted],
        }

    def summary(self) -> dict[str, Any]:
        return {
            "total_candidates": len(self._proposed) + len(self._promoted),
            "pending_approval": len(self._proposed),
        }


def _make_runtime(
    patterns: list[FakeDetectedPattern] | None = None,
    lessons: list[FakeLesson] | None = None,
    trajectories: list[FakeTrajectory] | None = None,
    inst_health: str = "growing",
    proposed: list[FakePromotionCandidate] | None = None,
    promoted: list[FakePromotionCandidate] | None = None,
) -> CapabilityCompoundingRuntime:
    return CapabilityCompoundingRuntime(
        learning_extraction=FakeLearningExtractionRuntime(lessons or []),
        institutional_memory=FakeInstitutionalMemoryRuntime(inst_health),
        capability_evolution=FakeCapabilityEvolutionEngine(trajectories or []),
        outcome_patterns=FakeOutcomePatternEngine(patterns or []),
        compounding_engine=FakeCompoundingEngine(proposed or [], promoted or []),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Stage helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStageHelpers(unittest.TestCase):

    def test_stage_index_outcome(self):
        self.assertEqual(_stage_index("outcome"), 0)

    def test_stage_index_operational(self):
        self.assertEqual(_stage_index("operational"), 4)

    def test_stage_index_invalid(self):
        self.assertEqual(_stage_index("nonexistent"), -1)

    def test_next_stage_outcome(self):
        self.assertEqual(_next_stage("outcome"), "lesson")

    def test_next_stage_capability(self):
        self.assertEqual(_next_stage("capability"), "operational")

    def test_next_stage_operational_is_none(self):
        self.assertIsNone(_next_stage("operational"))

    def test_next_stage_invalid(self):
        self.assertIsNone(_next_stage("nonexistent"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Enum types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEnums(unittest.TestCase):

    def test_compounding_stage_values(self):
        stages = [s.value for s in CompoundingStage]
        self.assertEqual(stages, ["outcome", "lesson", "pattern", "capability", "operational"])

    def test_compounding_health_values(self):
        health = [h.value for h in CompoundingHealth]
        self.assertEqual(health, ["thriving", "healthy", "stagnant", "degraded"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Snapshot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSnapshot(unittest.TestCase):

    def test_snapshot_empty(self):
        rt = _make_runtime()
        snap = rt.snapshot()
        self.assertIsInstance(snap, CompoundingSnapshot)
        self.assertEqual(snap.total_outcomes, 0)
        self.assertEqual(snap.total_lessons, 0)
        self.assertEqual(snap.total_patterns, 0)
        self.assertEqual(snap.capabilities_evolved, 0)
        self.assertEqual(snap.pending_promotions, 0)
        self.assertGreater(snap.generated_at, 0)

    def test_snapshot_with_data(self):
        patterns = [
            FakeDetectedPattern(pattern_id="p1"),
            FakeDetectedPattern(pattern_id="p2"),
        ]
        lessons = [
            FakeLesson(lesson_id="l1"),
            FakeLesson(lesson_id="l2"),
            FakeLesson(lesson_id="l3"),
        ]
        trajectories = [FakeTrajectory(capability_id="c1")]
        proposed = [FakePromotionCandidate(candidate_id="promo-1")]

        rt = _make_runtime(
            patterns=patterns,
            lessons=lessons,
            trajectories=trajectories,
            proposed=proposed,
        )
        snap = rt.snapshot()
        self.assertEqual(snap.total_patterns, 2)
        self.assertEqual(snap.total_lessons, 3)
        self.assertEqual(snap.capabilities_evolved, 1)
        self.assertEqual(snap.pending_promotions, 1)

    def test_snapshot_pipeline_stages(self):
        patterns = [FakeDetectedPattern(pattern_id="p1")]
        lessons = [FakeLesson(lesson_id="l1")]
        rt = _make_runtime(patterns=patterns, lessons=lessons)
        snap = rt.snapshot()
        self.assertIn("outcome", snap.pipeline_stages)
        self.assertIn("lesson", snap.pipeline_stages)
        self.assertIn("pattern", snap.pipeline_stages)
        self.assertIn("capability", snap.pipeline_stages)
        self.assertIn("operational", snap.pipeline_stages)

    def test_snapshot_to_dict(self):
        rt = _make_runtime()
        snap = rt.snapshot()
        d = snap.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("total_outcomes", d)
        self.assertIn("health", d)
        self.assertIn("generated_at", d)

    def test_snapshot_health_degraded_when_empty(self):
        rt = _make_runtime()
        snap = rt.snapshot()
        self.assertEqual(snap.health, CompoundingHealth.DEGRADED.value)

    def test_snapshot_health_stagnant_when_data_but_no_velocity(self):
        patterns = [FakeDetectedPattern(pattern_id="p1")]
        rt = _make_runtime(patterns=patterns, inst_health="stagnant")
        snap = rt.snapshot()
        self.assertEqual(snap.health, CompoundingHealth.STAGNANT.value)

    def test_snapshot_health_healthy_with_velocity(self):
        patterns = [FakeDetectedPattern(pattern_id="p1")]
        promoted = [FakePromotionCandidate(candidate_id="promo-1")]
        rt = _make_runtime(patterns=patterns, promoted=promoted)
        snap = rt.snapshot()
        self.assertIn(snap.health, [
            CompoundingHealth.HEALTHY.value,
            CompoundingHealth.THRIVING.value,
        ])

    def test_snapshot_health_thriving(self):
        patterns = [FakeDetectedPattern(pattern_id=f"p{i}") for i in range(3)]
        promoted = [FakePromotionCandidate(candidate_id=f"promo-{i}") for i in range(5)]
        rt = _make_runtime(
            patterns=patterns,
            promoted=promoted,
            inst_health="thriving",
        )
        snap = rt.snapshot()
        self.assertEqual(snap.health, CompoundingHealth.THRIVING.value)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Institutional health
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestInstitutionalHealth(unittest.TestCase):

    def test_health_growing(self):
        rt = _make_runtime(inst_health="growing")
        self.assertEqual(rt.institutional_health(), "growing")

    def test_health_thriving(self):
        rt = _make_runtime(inst_health="thriving")
        self.assertEqual(rt.institutional_health(), "thriving")

    def test_health_unknown_when_no_subsystem(self):
        class NoMemoryRuntime(CapabilityCompoundingRuntime):
            @property
            def _institutional_memory(self):
                return None

        rt = NoMemoryRuntime()
        result = rt.institutional_health()
        self.assertEqual(result, "unknown")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Pending promotions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPendingPromotions(unittest.TestCase):

    def test_no_pending_promotions(self):
        rt = _make_runtime()
        self.assertEqual(rt.pending_promotions(), [])

    def test_has_pending_promotions(self):
        proposed = [
            FakePromotionCandidate(candidate_id="promo-1", source_description="Lesson A"),
            FakePromotionCandidate(candidate_id="promo-2", source_description="Lesson B"),
        ]
        rt = _make_runtime(proposed=proposed)
        result = rt.pending_promotions()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["candidate_id"], "promo-1")
        self.assertEqual(result[1]["candidate_id"], "promo-2")

    def test_pending_returns_dicts(self):
        proposed = [FakePromotionCandidate(candidate_id="promo-1")]
        rt = _make_runtime(proposed=proposed)
        result = rt.pending_promotions()
        self.assertIsInstance(result[0], dict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Reusable assets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestReusableAssets(unittest.TestCase):

    def test_no_assets(self):
        rt = _make_runtime()
        self.assertEqual(rt.reusable_assets(), [])

    def test_has_assets(self):
        promoted = [
            FakePromotionCandidate(
                candidate_id="promo-1",
                source_description="Auth pattern",
                promotion_type="capability_to_operationalization",
                confidence=0.9,
                resolved_at=time.time(),
            ),
        ]
        rt = _make_runtime(promoted=promoted)
        assets = rt.reusable_assets()
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["title"], "Auth pattern")
        self.assertEqual(assets[0]["asset_type"], "capability_to_operationalization")
        self.assertEqual(assets[0]["confidence"], 0.9)

    def test_asset_has_correct_stage(self):
        promoted = [FakePromotionCandidate(candidate_id="promo-1")]
        rt = _make_runtime(promoted=promoted)
        assets = rt.reusable_assets()
        self.assertEqual(assets[0]["origin_stage"], "operational")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Pipeline trace
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPipelineTrace(unittest.TestCase):

    def test_trace_empty_production(self):
        rt = _make_runtime()
        trace = rt.production_to_asset_pipeline("prod-001")
        self.assertEqual(trace.production_id, "prod-001")
        self.assertIn("outcome", trace.stages_reached)
        self.assertFalse(trace.is_complete)

    def test_trace_with_outcomes_only(self):
        patterns = [
            FakeDetectedPattern(pattern_id="p1", evidence=["prod-001"]),
        ]
        rt = _make_runtime(patterns=patterns)
        trace = rt.production_to_asset_pipeline("prod-001")
        self.assertEqual(len(trace.outcomes), 1)
        self.assertEqual(trace.current_stage, "outcome")

    def test_trace_with_lessons(self):
        patterns = [
            FakeDetectedPattern(pattern_id="p1", evidence=["prod-002"]),
        ]
        lessons = [
            FakeLesson(lesson_id="l1", evidence_sources=["prod-002"]),
        ]
        rt = _make_runtime(patterns=patterns, lessons=lessons)
        trace = rt.production_to_asset_pipeline("prod-002")
        self.assertIn("lesson", trace.stages_reached)
        self.assertEqual(len(trace.lessons), 1)

    def test_trace_with_patterns(self):
        patterns = [
            FakeDetectedPattern(pattern_id="p1", evidence=["prod-003"]),
            FakeDetectedPattern(pattern_id="p2", evidence=["l1"]),
        ]
        lessons = [
            FakeLesson(lesson_id="l1", evidence_sources=["prod-003"]),
        ]
        rt = _make_runtime(patterns=patterns, lessons=lessons)
        trace = rt.production_to_asset_pipeline("prod-003")
        self.assertIn("lesson", trace.stages_reached)
        if trace.patterns:
            self.assertIn("pattern", trace.stages_reached)

    def test_trace_is_complete_false_by_default(self):
        rt = _make_runtime()
        trace = rt.production_to_asset_pipeline("prod-nope")
        self.assertFalse(trace.is_complete)

    def test_trace_to_dict(self):
        rt = _make_runtime()
        trace = rt.production_to_asset_pipeline("prod-x")
        d = trace.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["production_id"], "prod-x")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSummary(unittest.TestCase):

    def test_summary_keys(self):
        rt = _make_runtime()
        s = rt.summary()
        expected_keys = {
            "health", "total_outcomes", "total_lessons", "total_patterns",
            "capabilities_evolved", "pending_promotions", "institutional_health",
            "compounding_velocity", "reusable_asset_count", "pipeline_stages",
        }
        self.assertEqual(set(s.keys()), expected_keys)

    def test_summary_reflects_data(self):
        patterns = [FakeDetectedPattern(pattern_id="p1")]
        lessons = [FakeLesson(lesson_id="l1")]
        proposed = [FakePromotionCandidate(candidate_id="promo-1")]
        rt = _make_runtime(patterns=patterns, lessons=lessons, proposed=proposed)
        s = rt.summary()
        self.assertEqual(s["total_patterns"], 1)
        self.assertEqual(s["total_lessons"], 1)
        self.assertEqual(s["pending_promotions"], 1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Graceful degradation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGracefulDegradation(unittest.TestCase):

    def test_all_subsystems_none(self):
        class AllNoneRuntime(CapabilityCompoundingRuntime):
            @property
            def _learning_extraction(self):
                return None

            @property
            def _institutional_memory(self):
                return None

            @property
            def _capability_evolution(self):
                return None

            @property
            def _outcome_patterns(self):
                return None

            @property
            def _compounding(self):
                return None

        rt = AllNoneRuntime()
        snap = rt.snapshot()
        self.assertEqual(snap.health, CompoundingHealth.DEGRADED.value)
        self.assertEqual(snap.total_outcomes, 0)
        self.assertEqual(snap.total_lessons, 0)
        self.assertEqual(snap.pending_promotions, 0)
        self.assertEqual(rt.pending_promotions(), [])
        self.assertEqual(rt.reusable_assets(), [])
        self.assertEqual(rt.institutional_health(), "unknown")

    def test_partial_subsystems(self):
        rt = _make_runtime(
            patterns=[FakeDetectedPattern(pattern_id="p1")],
            lessons=None,
            trajectories=None,
        )
        snap = rt.snapshot()
        self.assertEqual(snap.total_patterns, 1)
        self.assertEqual(snap.total_lessons, 0)
        self.assertEqual(snap.capabilities_evolved, 0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — Velocity
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestVelocity(unittest.TestCase):

    def test_velocity_zero_when_no_candidates(self):
        rt = _make_runtime()
        snap = rt.snapshot()
        self.assertEqual(snap.compounding_velocity, 0.0)

    def test_velocity_positive_with_promotions(self):
        promoted = [FakePromotionCandidate(candidate_id="promo-1")]
        rt = _make_runtime(promoted=promoted)
        snap = rt.snapshot()
        self.assertGreater(snap.compounding_velocity, 0.0)

    def test_velocity_is_ratio(self):
        proposed = [FakePromotionCandidate(candidate_id=f"prop-{i}") for i in range(3)]
        promoted = [FakePromotionCandidate(candidate_id="promo-1")]
        rt = _make_runtime(proposed=proposed, promoted=promoted)
        snap = rt.snapshot()
        self.assertLessEqual(snap.compounding_velocity, 1.0)
        self.assertGreater(snap.compounding_velocity, 0.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests — ReusableAsset dataclass
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestReusableAssetType(unittest.TestCase):

    def test_to_dict(self):
        asset = ReusableAsset(
            asset_id="a1",
            title="Test asset",
            asset_type="capability_to_operationalization",
            confidence=0.95,
        )
        d = asset.to_dict()
        self.assertEqual(d["asset_id"], "a1")
        self.assertEqual(d["title"], "Test asset")
        self.assertEqual(d["confidence"], 0.95)

    def test_defaults(self):
        asset = ReusableAsset()
        self.assertEqual(asset.asset_id, "")
        self.assertEqual(asset.reuse_count, 0)
        self.assertEqual(asset.origin_stage, "operational")


if __name__ == "__main__":
    unittest.main()
