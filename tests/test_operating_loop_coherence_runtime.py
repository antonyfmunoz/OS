"""Tests for OperatingLoopCoherenceRuntime — Campaign 4.3.

Covers: coherent loop, orphan detection, broken chains, missing lineage,
missing learning, stale approvals, contradictions, coherence scoring,
full report, graceful degradation, awareness score integration.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

import pytest

from substrate.organism.operating_loop_coherence_runtime import (
    LoopCoherenceIssue,
    LoopCoherenceIssueType,
    LoopCoherenceReport,
    LoopCoherenceStatus,
    OperatingLoopCoherenceRuntime,
)
from substrate.workstation.operating_loop_runtime import (
    OperatingLoop,
    OperatingLoopStage,
    OperatingLoopTransition,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _mock_intent_runtime(intents: list[dict[str, Any]] | None = None) -> MagicMock:
    m = MagicMock()
    m.active_by_scope.return_value = intents or []
    return m


def _mock_governed_work(active: list[dict[str, Any]] | None = None, blocked: list[Any] | None = None) -> MagicMock:
    m = MagicMock()
    m.active.return_value = active or []
    m.blocked.return_value = blocked or []
    return m


def _mock_loop_runtime(loops: list[Any] | None = None) -> MagicMock:
    m = MagicMock()
    m.active_loops.return_value = loops or []
    m.snapshot.return_value = MagicMock(to_dict=lambda: {"active_loops": len(loops or [])})
    return m


def _mock_approval_runtime(pending: list[dict[str, Any]] | None = None) -> MagicMock:
    m = MagicMock()
    m.pending.return_value = pending or []
    m.snapshot.return_value = MagicMock(to_dict=lambda: {"pending": len(pending or [])})
    return m


def _mock_contradiction_engine(contradictions: list[dict[str, Any]] | None = None) -> MagicMock:
    m = MagicMock()
    m.detect_contradictions.return_value = contradictions or []
    return m


def _mock_state_coherence() -> MagicMock:
    m = MagicMock()
    m.coherence_report.return_value = {"coherent": True, "score": 0.95}
    m.organism_health.return_value = {"status": "healthy"}
    return m


def _mock_execution_graph(has_lineage: bool = True) -> MagicMock:
    m = MagicMock()
    if has_lineage:
        m.trace_from_intent.return_value = {"nodes": [{"id": "n1"}]}
    else:
        m.trace_from_intent.return_value = None
    m.audit_completeness.return_value = {"complete": 5}
    m.validate_lineage.return_value = True
    m.validate_chain.return_value = True
    return m


def _mock_learning_loop(outcomes: list[dict[str, Any]] | None = None) -> MagicMock:
    m = MagicMock()
    m.recent_outcomes.return_value = outcomes or []
    return m


def _mock_awareness(score: float = 0.85) -> MagicMock:
    m = MagicMock()
    m.awareness_score.return_value = score
    return m


def _make_loop(
    loop_id: str = "oloop-test1",
    intent_id: str = "int-1",
    stage: OperatingLoopStage = OperatingLoopStage.EXECUTE,
    lineage: list[OperatingLoopTransition] | None = None,
    work_ids: list[str] | None = None,
) -> OperatingLoop:
    return OperatingLoop(
        loop_id=loop_id,
        intent_id=intent_id,
        intent_text="Test loop",
        current_stage=stage,
        work_ids=work_ids or [],
        lineage=lineage or [],
    )


def _full_runtime(**overrides: Any) -> OperatingLoopCoherenceRuntime:
    defaults: dict[str, Any] = {
        "state_coherence": _mock_state_coherence(),
        "execution_graph": _mock_execution_graph(),
        "contradiction_engine": _mock_contradiction_engine(),
        "learning_loop": _mock_learning_loop(),
        "intent_runtime": _mock_intent_runtime(),
        "governed_work": _mock_governed_work(),
        "approval_runtime": _mock_approval_runtime(),
        "loop_runtime": _mock_loop_runtime(),
        "awareness": _mock_awareness(),
    }
    defaults.update(overrides)
    return OperatingLoopCoherenceRuntime(**defaults)


# ── Coherent Loop ─────────────────────────────────────────────────────────


class TestCoherentLoop:
    def test_no_issues_returns_coherent(self) -> None:
        rt = _full_runtime()
        report = rt.full_report()
        assert report.overall_status == LoopCoherenceStatus.COHERENT

    def test_coherent_score_is_1(self) -> None:
        rt = _full_runtime()
        assert rt.coherence_score() == 1.0

    def test_coherent_report_has_no_issues(self) -> None:
        rt = _full_runtime()
        report = rt.full_report()
        assert len(report.issues) == 0

    def test_coherent_report_has_state_coherence(self) -> None:
        rt = _full_runtime()
        report = rt.full_report()
        assert report.state_coherence.get("coherent") is True


# ── Orphan Detection ──────────────────────────────────────────────────────


class TestOrphanDetection:
    def test_orphan_intent_detected(self) -> None:
        rt = _full_runtime(
            intent_runtime=_mock_intent_runtime([{"intent_id": "int-orphan"}]),
            loop_runtime=_mock_loop_runtime([]),
        )
        orphans = rt.detect_orphans()
        assert len(orphans) == 1
        assert orphans[0].issue_type == LoopCoherenceIssueType.ORPHAN_INTENT

    def test_orphan_work_detected(self) -> None:
        rt = _full_runtime(
            governed_work=_mock_governed_work(active=[{"work_id": "wk-orphan"}]),
            loop_runtime=_mock_loop_runtime([_make_loop(work_ids=[])]),
        )
        orphans = rt.detect_orphans()
        work_orphans = [o for o in orphans if o.issue_type == LoopCoherenceIssueType.ORPHAN_WORK]
        assert len(work_orphans) == 1

    def test_intent_matched_to_loop_no_orphan(self) -> None:
        loop = _make_loop(intent_id="int-1")
        rt = _full_runtime(
            intent_runtime=_mock_intent_runtime([{"intent_id": "int-1"}]),
            loop_runtime=_mock_loop_runtime([loop]),
        )
        orphans = rt.detect_orphans()
        intent_orphans = [o for o in orphans if o.issue_type == LoopCoherenceIssueType.ORPHAN_INTENT]
        assert len(intent_orphans) == 0

    def test_work_matched_to_loop_no_orphan(self) -> None:
        loop = _make_loop(work_ids=["wk-1"])
        rt = _full_runtime(
            governed_work=_mock_governed_work(active=[{"work_id": "wk-1"}]),
            loop_runtime=_mock_loop_runtime([loop]),
        )
        orphans = rt.detect_orphans()
        work_orphans = [o for o in orphans if o.issue_type == LoopCoherenceIssueType.ORPHAN_WORK]
        assert len(work_orphans) == 0

    def test_orphan_status_in_report(self) -> None:
        rt = _full_runtime(
            intent_runtime=_mock_intent_runtime([{"intent_id": "int-orphan"}]),
            loop_runtime=_mock_loop_runtime([]),
        )
        report = rt.full_report()
        assert report.overall_status == LoopCoherenceStatus.ORPHANED

    def test_multiple_orphan_intents(self) -> None:
        rt = _full_runtime(
            intent_runtime=_mock_intent_runtime([
                {"intent_id": "int-a"},
                {"intent_id": "int-b"},
            ]),
            loop_runtime=_mock_loop_runtime([]),
        )
        orphans = rt.detect_orphans()
        assert len([o for o in orphans if o.issue_type == LoopCoherenceIssueType.ORPHAN_INTENT]) == 2


# ── Broken Chain ──────────────────────────────────────────────────────────


class TestBrokenChain:
    def test_gap_detected(self) -> None:
        lineage = [
            OperatingLoopTransition(
                from_stage=OperatingLoopStage.INTENT,
                to_stage=OperatingLoopStage.PLAN,
            ),
            OperatingLoopTransition(
                from_stage=OperatingLoopStage.EXECUTE,
                to_stage=OperatingLoopStage.REVIEW,
            ),
        ]
        loop = _make_loop(lineage=lineage)
        rt = _full_runtime(loop_runtime=_mock_loop_runtime([loop]))
        chains = rt.detect_broken_chains()
        assert len(chains) == 1
        assert chains[0].issue_type == LoopCoherenceIssueType.BROKEN_CHAIN

    def test_no_gap_no_issue(self) -> None:
        lineage = [
            OperatingLoopTransition(
                from_stage=OperatingLoopStage.INTENT,
                to_stage=OperatingLoopStage.PLAN,
            ),
            OperatingLoopTransition(
                from_stage=OperatingLoopStage.PLAN,
                to_stage=OperatingLoopStage.ASSIGN,
            ),
        ]
        loop = _make_loop(lineage=lineage)
        rt = _full_runtime(loop_runtime=_mock_loop_runtime([loop]))
        chains = rt.detect_broken_chains()
        assert len(chains) == 0

    def test_single_transition_no_issue(self) -> None:
        lineage = [
            OperatingLoopTransition(
                from_stage=OperatingLoopStage.INTENT,
                to_stage=OperatingLoopStage.PLAN,
            ),
        ]
        loop = _make_loop(lineage=lineage)
        rt = _full_runtime(loop_runtime=_mock_loop_runtime([loop]))
        assert len(rt.detect_broken_chains()) == 0

    def test_broken_chain_severity_is_high(self) -> None:
        lineage = [
            OperatingLoopTransition(
                from_stage=OperatingLoopStage.INTENT,
                to_stage=OperatingLoopStage.PLAN,
            ),
            OperatingLoopTransition(
                from_stage=OperatingLoopStage.REVIEW,
                to_stage=OperatingLoopStage.APPROVE,
            ),
        ]
        loop = _make_loop(lineage=lineage)
        rt = _full_runtime(loop_runtime=_mock_loop_runtime([loop]))
        chains = rt.detect_broken_chains()
        assert chains[0].severity == "high"


# ── Missing Lineage ──────────────────────────────────────────────────────


class TestMissingLineage:
    def test_completed_without_graph_entry(self) -> None:
        loop = _make_loop(stage=OperatingLoopStage.COMPLETE, intent_id="int-1")
        rt = _full_runtime(execution_graph=_mock_execution_graph(has_lineage=False))
        report = rt.validate_loop(loop)
        lineage_issues = [i for i in report.issues if i.issue_type == LoopCoherenceIssueType.MISSING_LINEAGE]
        assert len(lineage_issues) == 1

    def test_completed_with_graph_entry_no_issue(self) -> None:
        loop = _make_loop(stage=OperatingLoopStage.COMPLETE, intent_id="int-1")
        rt = _full_runtime(execution_graph=_mock_execution_graph(has_lineage=True))
        report = rt.validate_loop(loop)
        lineage_issues = [i for i in report.issues if i.issue_type == LoopCoherenceIssueType.MISSING_LINEAGE]
        assert len(lineage_issues) == 0

    def test_active_loop_no_lineage_check(self) -> None:
        loop = _make_loop(stage=OperatingLoopStage.EXECUTE, intent_id="int-1")
        rt = _full_runtime(execution_graph=_mock_execution_graph(has_lineage=False))
        report = rt.validate_loop(loop)
        lineage_issues = [i for i in report.issues if i.issue_type == LoopCoherenceIssueType.MISSING_LINEAGE]
        assert len(lineage_issues) == 0

    def test_completed_no_graph_dep_no_crash(self) -> None:
        loop = _make_loop(stage=OperatingLoopStage.COMPLETE, intent_id="int-1")
        rt = OperatingLoopCoherenceRuntime()
        report = rt.validate_loop(loop)
        assert isinstance(report, LoopCoherenceReport)


# ── Missing Learning ─────────────────────────────────────────────────────


class TestMissingLearning:
    def test_completed_without_outcome(self) -> None:
        loop = _make_loop(stage=OperatingLoopStage.COMPLETE, intent_id="int-1")
        rt = _full_runtime(learning_loop=_mock_learning_loop([]))
        report = rt.validate_loop(loop)
        learning = [i for i in report.issues if i.issue_type == LoopCoherenceIssueType.MISSING_LEARNING]
        assert len(learning) == 1

    def test_completed_with_outcome_no_issue(self) -> None:
        loop = _make_loop(stage=OperatingLoopStage.COMPLETE, intent_id="int-1")
        rt = _full_runtime(
            learning_loop=_mock_learning_loop([{"intent_id": "int-1", "outcome": "success"}])
        )
        report = rt.validate_loop(loop)
        learning = [i for i in report.issues if i.issue_type == LoopCoherenceIssueType.MISSING_LEARNING]
        assert len(learning) == 0

    def test_active_loop_no_learning_check(self) -> None:
        loop = _make_loop(stage=OperatingLoopStage.PLAN, intent_id="int-1")
        rt = _full_runtime(learning_loop=_mock_learning_loop([]))
        report = rt.validate_loop(loop)
        learning = [i for i in report.issues if i.issue_type == LoopCoherenceIssueType.MISSING_LEARNING]
        assert len(learning) == 0

    def test_missing_learning_severity_is_low(self) -> None:
        loop = _make_loop(stage=OperatingLoopStage.COMPLETE, intent_id="int-1")
        rt = _full_runtime(learning_loop=_mock_learning_loop([]))
        report = rt.validate_loop(loop)
        learning = [i for i in report.issues if i.issue_type == LoopCoherenceIssueType.MISSING_LEARNING]
        assert learning[0].severity == "low"


# ── Stale Approvals ──────────────────────────────────────────────────────


class TestStaleApprovals:
    def test_stale_approval_detected(self) -> None:
        old_time = time.time() - 100000  # > 24h
        rt = _full_runtime(
            approval_runtime=_mock_approval_runtime([
                {"approval_id": "ap-1", "waiting_since": old_time}
            ])
        )
        stale = rt.detect_stale_approvals()
        assert len(stale) == 1
        assert stale[0].issue_type == LoopCoherenceIssueType.STALE_APPROVAL

    def test_fresh_approval_no_issue(self) -> None:
        rt = _full_runtime(
            approval_runtime=_mock_approval_runtime([
                {"approval_id": "ap-1", "waiting_since": time.time() - 100}
            ])
        )
        stale = rt.detect_stale_approvals()
        assert len(stale) == 0

    def test_no_approvals_no_issues(self) -> None:
        rt = _full_runtime(approval_runtime=_mock_approval_runtime([]))
        assert len(rt.detect_stale_approvals()) == 0


# ── Contradictions ────────────────────────────────────────────────────────


class TestContradictions:
    def test_contradiction_detected(self) -> None:
        rt = _full_runtime(
            contradiction_engine=_mock_contradiction_engine([
                {"type": "state_vs_declared", "description": "CPU reported idle but load is 3.5"}
            ])
        )
        issues = rt.detect_contradictions()
        assert len(issues) == 1
        assert issues[0].issue_type == LoopCoherenceIssueType.CONTRADICTION_DETECTED

    def test_no_contradictions(self) -> None:
        rt = _full_runtime(contradiction_engine=_mock_contradiction_engine([]))
        assert len(rt.detect_contradictions()) == 0

    def test_contradiction_description_includes_type(self) -> None:
        rt = _full_runtime(
            contradiction_engine=_mock_contradiction_engine([
                {"type": "declared_vs_observed", "description": "Node offline but responding"}
            ])
        )
        issues = rt.detect_contradictions()
        assert "declared_vs_observed" in issues[0].description

    def test_contradiction_severity_is_high(self) -> None:
        rt = _full_runtime(
            contradiction_engine=_mock_contradiction_engine([
                {"type": "x", "description": "y"}
            ])
        )
        issues = rt.detect_contradictions()
        assert issues[0].severity == "high"


# ── Coherence Scoring ────────────────────────────────────────────────────


class TestCoherenceScoring:
    def test_perfect_score_no_issues(self) -> None:
        rt = _full_runtime()
        assert rt.coherence_score() == 1.0

    def test_score_decreases_with_issues(self) -> None:
        rt = _full_runtime(
            intent_runtime=_mock_intent_runtime([{"intent_id": "orphan-1"}]),
            loop_runtime=_mock_loop_runtime([]),
        )
        score = rt.coherence_score()
        assert score < 1.0

    def test_high_severity_penalizes_more(self) -> None:
        rt1 = _full_runtime(
            contradiction_engine=_mock_contradiction_engine([
                {"type": "x", "description": "y"}
            ])
        )
        rt2 = _full_runtime(
            intent_runtime=_mock_intent_runtime([{"intent_id": "orph"}]),
            loop_runtime=_mock_loop_runtime([]),
        )
        score_contradiction = rt1.coherence_score()
        score_orphan = rt2.coherence_score()
        assert score_contradiction < 1.0
        assert score_orphan < 1.0

    def test_score_never_below_zero(self) -> None:
        many_contradictions = [{"type": "x", "description": f"c{i}"} for i in range(20)]
        rt = _full_runtime(
            contradiction_engine=_mock_contradiction_engine(many_contradictions)
        )
        assert rt.coherence_score() >= 0.0


# ── Full Report ───────────────────────────────────────────────────────────


class TestFullReport:
    def test_report_aggregates_all_detectors(self) -> None:
        old_time = time.time() - 100000
        rt = _full_runtime(
            intent_runtime=_mock_intent_runtime([{"intent_id": "orphan-1"}]),
            loop_runtime=_mock_loop_runtime([]),
            approval_runtime=_mock_approval_runtime([{"approval_id": "ap-1", "waiting_since": old_time}]),
            contradiction_engine=_mock_contradiction_engine([{"type": "x", "description": "y"}]),
        )
        report = rt.full_report()
        types = {i.issue_type for i in report.issues}
        assert LoopCoherenceIssueType.ORPHAN_INTENT in types
        assert LoopCoherenceIssueType.STALE_APPROVAL in types
        assert LoopCoherenceIssueType.CONTRADICTION_DETECTED in types

    def test_report_includes_generated_at(self) -> None:
        rt = _full_runtime()
        report = rt.full_report()
        assert report.generated_at > 0

    def test_report_includes_subsystem_health(self) -> None:
        rt = _full_runtime()
        report = rt.full_report()
        assert report.subsystem_health.get("awareness") == "available"
        assert report.subsystem_health.get("state_coherence") == "available"

    def test_report_to_dict(self) -> None:
        rt = _full_runtime()
        d = rt.full_report().to_dict()
        assert "overall_status" in d
        assert "coherence_score" in d
        assert "issues" in d
        assert "subsystem_health" in d


# ── No Deps ──────────────────────────────────────────────────────────────


class TestNoDeps:
    def test_all_none_no_crash(self) -> None:
        rt = OperatingLoopCoherenceRuntime()
        report = rt.full_report()
        assert report.overall_status == LoopCoherenceStatus.COHERENT

    def test_all_none_score_is_1(self) -> None:
        rt = OperatingLoopCoherenceRuntime()
        assert rt.coherence_score() == 1.0

    def test_all_none_detectors_return_empty(self) -> None:
        rt = OperatingLoopCoherenceRuntime()
        assert rt.detect_orphans() == []
        assert rt.detect_broken_chains() == []
        assert rt.detect_stale_approvals() == []
        assert rt.detect_contradictions() == []

    def test_subsystem_health_shows_unavailable(self) -> None:
        rt = OperatingLoopCoherenceRuntime()
        report = rt.full_report()
        assert all(v == "unavailable" for v in report.subsystem_health.values())


# ── Awareness Score Integration ───────────────────────────────────────────


class TestAwarenessIntegration:
    def test_awareness_score_in_report(self) -> None:
        rt = _full_runtime(awareness=_mock_awareness(0.92))
        report = rt.full_report()
        assert report.awareness_score == 0.92

    def test_awareness_none_returns_zero(self) -> None:
        rt = _full_runtime(awareness=None)
        report = rt.full_report()
        assert report.awareness_score == 0.0

    def test_awareness_error_returns_zero(self) -> None:
        bad = MagicMock()
        bad.awareness_score.side_effect = RuntimeError("boom")
        rt = _full_runtime(awareness=bad)
        report = rt.full_report()
        assert report.awareness_score == 0.0

    def test_awareness_non_numeric_returns_zero(self) -> None:
        bad = MagicMock()
        bad.awareness_score.return_value = "not a number"
        rt = _full_runtime(awareness=bad)
        report = rt.full_report()
        assert report.awareness_score == 0.0
