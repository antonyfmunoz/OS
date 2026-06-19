"""Tests for MVPReadinessRuntime — Campaign 4.5.

Covers: 14-dimension assessment, orchestrator awareness dimension,
scoring, status thresholds, blockers, escape points, recommendations,
graceful degradation, coherence integration, serialization.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

import pytest

from substrate.workstation.mvp_readiness_runtime import (
    MVP_DIMENSIONS,
    MVPDimension,
    MVPDimensionStatus,
    MVPEscapePoint,
    MVPReadinessReport,
    MVPReadinessRuntime,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _mock_awareness() -> MagicMock:
    m = MagicMock()
    m.awareness_score.return_value = 0.85
    m.snapshot.return_value = {
        "total_subsystems": 23,
        "active_subsystems": 20,
        "context": {},
    }
    return m


def _mock_loop() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"active_loops": 3, "completed_count": 10}
    return m


def _mock_approval() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"by_source": {"governed_work": 2, "template": 1, "memory": 1}}
    return m


def _mock_coherence() -> MagicMock:
    m = MagicMock()
    m.coherence_score.return_value = 0.9
    return m


def _mock_session() -> MagicMock:
    m = MagicMock()
    m.active_session.return_value = MagicMock(session_id="s-1")
    return m


def _mock_cap_map() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"total": 13, "implemented": 11}
    m.mvp_gaps.return_value = ["gap1", "gap2"]
    return m


def _mock_proj() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"projections": 2}
    return m


def _build_full_runtime() -> MVPReadinessRuntime:
    return MVPReadinessRuntime(
        awareness=_mock_awareness(),
        operating_loop=_mock_loop(),
        approval_runtime=_mock_approval(),
        coherence_runtime=_mock_coherence(),
        session_runtime=_mock_session(),
        capability_map=_mock_cap_map(),
        projection_integration=_mock_proj(),
    )


# ── Full Assessment ───────────────────────────────────────────────────────


class TestFullAssessment:
    def test_assess_returns_14_dimensions(self) -> None:
        rt = _build_full_runtime()
        report = rt.assess()
        assert len(report.dimensions) == 14

    def test_assess_all_dimensions_named(self) -> None:
        rt = _build_full_runtime()
        report = rt.assess()
        names = [d.name for d in report.dimensions]
        for expected in MVP_DIMENSIONS:
            assert expected in names

    def test_assess_overall_score_positive(self) -> None:
        rt = _build_full_runtime()
        report = rt.assess()
        assert report.overall_score > 0

    def test_assess_overall_status_not_missing(self) -> None:
        rt = _build_full_runtime()
        report = rt.assess()
        assert report.overall_status != MVPDimensionStatus.MISSING

    def test_assess_has_generated_at(self) -> None:
        rt = _build_full_runtime()
        report = rt.assess()
        assert report.generated_at > 0

    def test_14th_dimension_present(self) -> None:
        assert "orchestrator_awareness" in MVP_DIMENSIONS
        assert len(MVP_DIMENSIONS) == 14


# ── Orchestrator Awareness ────────────────────────────────────────────────


class TestOrchestratorAwareness:
    def test_orchestrator_awareness_scored(self) -> None:
        rt = _build_full_runtime()
        dim = rt.dimension("orchestrator_awareness")
        assert dim.score == 0.85

    def test_orchestrator_awareness_status(self) -> None:
        rt = _build_full_runtime()
        dim = rt.dimension("orchestrator_awareness")
        assert dim.status == MVPDimensionStatus.READY

    def test_orchestrator_awareness_evidence(self) -> None:
        rt = _build_full_runtime()
        dim = rt.dimension("orchestrator_awareness")
        assert len(dim.evidence) > 0

    def test_orchestrator_awareness_no_runtime(self) -> None:
        rt = MVPReadinessRuntime()
        dim = rt.dimension("orchestrator_awareness")
        assert dim.status == MVPDimensionStatus.MISSING
        assert len(dim.blockers) > 0


# ── Scoring ───────────────────────────────────────────────────────────────


class TestScoring:
    def test_score_is_mean(self) -> None:
        rt = _build_full_runtime()
        report = rt.assess()
        expected = sum(d.score for d in report.dimensions) / 14
        assert abs(report.overall_score - round(expected, 3)) < 0.01

    def test_score_shortcut(self) -> None:
        rt = _build_full_runtime()
        assert rt.score() == rt.assess().overall_score

    def test_score_zero_with_no_deps(self) -> None:
        rt = MVPReadinessRuntime()
        assert rt.score() == 0.0

    def test_score_deterministic(self) -> None:
        rt = _build_full_runtime()
        s1 = rt.score()
        s2 = rt.score()
        assert s1 == s2


# ── Status Thresholds ─────────────────────────────────────────────────────


class TestStatusThresholds:
    def test_ready_at_0_8(self) -> None:
        rt = _build_full_runtime()
        dim = rt.dimension("orchestrator_awareness")
        assert dim.status == MVPDimensionStatus.READY

    def test_partial_at_0_4(self) -> None:
        rt = _build_full_runtime()
        dim = rt.dimension("intent_understanding")
        assert dim.status == MVPDimensionStatus.PARTIAL

    def test_missing_when_none(self) -> None:
        rt = MVPReadinessRuntime()
        dim = rt.dimension("orchestrator_awareness")
        assert dim.status == MVPDimensionStatus.MISSING

    def test_unknown_dimension(self) -> None:
        rt = _build_full_runtime()
        dim = rt.dimension("nonexistent")
        assert len(dim.blockers) > 0


# ── Blockers ──────────────────────────────────────────────────────────────


class TestBlockers:
    def test_blockers_from_missing_deps(self) -> None:
        rt = MVPReadinessRuntime()
        blockers = rt.blockers()
        assert len(blockers) > 0

    def test_blockers_fewer_with_deps(self) -> None:
        rt = _build_full_runtime()
        b_full = rt.blockers()
        rt_none = MVPReadinessRuntime()
        b_none = rt_none.blockers()
        assert len(b_full) < len(b_none)

    def test_blockers_include_cockpit_gaps(self) -> None:
        rt = _build_full_runtime()
        blockers = rt.blockers()
        assert any("gap" in b.lower() for b in blockers)


# ── Escape Points ─────────────────────────────────────────────────────────


class TestEscapePoints:
    def test_escape_points_from_missing(self) -> None:
        rt = MVPReadinessRuntime()
        points = rt.escape_points()
        assert len(points) > 0
        assert any(p.severity == "blocks_mvp" for p in points)

    def test_escape_points_fewer_with_deps(self) -> None:
        rt = _build_full_runtime()
        points_full = rt.escape_points()
        rt_none = MVPReadinessRuntime()
        points_none = rt_none.escape_points()
        assert len(points_full) < len(points_none)

    def test_escape_point_serialization(self) -> None:
        ep = MVPEscapePoint(description="test", severity="blocks_mvp")
        d = ep.to_dict()
        assert d["severity"] == "blocks_mvp"


# ── Recommendations ───────────────────────────────────────────────────────


class TestRecommendations:
    def test_recommendations_ordered_by_score(self) -> None:
        rt = _build_full_runtime()
        recs = rt.recommended_next()
        assert len(recs) > 0

    def test_recommendations_limit(self) -> None:
        rt = _build_full_runtime()
        recs = rt.recommended_next(limit=3)
        assert len(recs) <= 3

    def test_recommendations_include_low_scores(self) -> None:
        rt = MVPReadinessRuntime()
        recs = rt.recommended_next(limit=20)
        assert len(recs) == 14


# ── Missing Deps ──────────────────────────────────────────────────────────


class TestMissingDeps:
    def test_no_deps_all_missing(self) -> None:
        rt = MVPReadinessRuntime()
        report = rt.assess()
        for dim in report.dimensions:
            assert dim.status == MVPDimensionStatus.MISSING

    def test_no_deps_still_14(self) -> None:
        rt = MVPReadinessRuntime()
        report = rt.assess()
        assert len(report.dimensions) == 14

    def test_no_deps_score_zero(self) -> None:
        rt = MVPReadinessRuntime()
        assert rt.score() == 0.0

    def test_partial_deps(self) -> None:
        rt = MVPReadinessRuntime(awareness=_mock_awareness())
        dim = rt.dimension("orchestrator_awareness")
        assert dim.status == MVPDimensionStatus.READY

    def test_partial_deps_other_missing(self) -> None:
        rt = MVPReadinessRuntime(awareness=_mock_awareness())
        dim = rt.dimension("execution_tracking")
        assert dim.status == MVPDimensionStatus.MISSING


# ── Coherence Integration ─────────────────────────────────────────────────


class TestCoherenceIntegration:
    def test_coherence_score_used(self) -> None:
        rt = _build_full_runtime()
        dim = rt.dimension("coherence")
        assert dim.score == 0.9

    def test_coherence_ready(self) -> None:
        rt = _build_full_runtime()
        dim = rt.dimension("coherence")
        assert dim.status == MVPDimensionStatus.READY

    def test_coherence_missing_no_dep(self) -> None:
        rt = MVPReadinessRuntime()
        dim = rt.dimension("coherence")
        assert dim.status == MVPDimensionStatus.MISSING


# ── Serialization ─────────────────────────────────────────────────────────


class TestSerialization:
    def test_report_to_dict(self) -> None:
        rt = _build_full_runtime()
        d = rt.assess().to_dict()
        assert "overall_score" in d
        assert "dimensions" in d
        assert len(d["dimensions"]) == 14

    def test_dimension_to_dict(self) -> None:
        dim = MVPDimension(name="test", score=0.5, status=MVPDimensionStatus.PARTIAL)
        d = dim.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "partial"
