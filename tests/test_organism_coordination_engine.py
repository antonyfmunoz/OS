"""Tests for Organism Coordination Engine — Campaign 15.1."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from unittest.mock import MagicMock

from substrate.organism.organism_coordination_engine import (
    CoordinationHealth,
    CoordinationIssue,
    CoordinationIssueType,
    CoordinationSnapshot,
    OrganismCoordinationEngine,
    _health_to_score,
)


# ── Enum Tests ───────────────────────────────────────────────────────


class TestEnums:
    def test_coordination_issue_type_values(self) -> None:
        assert CoordinationIssueType.GOAL_CONFLICT.value == "goal_conflict"
        assert CoordinationIssueType.RESOURCE_CONFLICT.value == "resource_conflict"
        assert CoordinationIssueType.PREDICTION_CONFLICT.value == "prediction_conflict"
        assert CoordinationIssueType.CAPABILITY_BOTTLENECK.value == "capability_bottleneck"
        assert CoordinationIssueType.EXECUTION_BOTTLENECK.value == "execution_bottleneck"
        assert CoordinationIssueType.LEARNING_GAP.value == "learning_gap"
        assert len(CoordinationIssueType) == 6

    def test_coordination_health_values(self) -> None:
        assert CoordinationHealth.SYNCHRONIZED.value == "synchronized"
        assert CoordinationHealth.ALIGNED.value == "aligned"
        assert CoordinationHealth.DRIFTING.value == "drifting"
        assert CoordinationHealth.FRAGMENTED.value == "fragmented"
        assert CoordinationHealth.CRITICAL.value == "critical"
        assert len(CoordinationHealth) == 5


# ── Dataclass Tests ──────────────────────────────────────────────────


class TestDataclasses:
    def test_coordination_issue_defaults(self) -> None:
        i = CoordinationIssue()
        assert i.issue_id == ""
        assert i.issue_type == "goal_conflict"
        assert i.severity == "low"
        assert i.affected_subsystems == []
        assert i.description == ""
        assert i.recommendation == ""

    def test_coordination_issue_to_dict(self) -> None:
        i = CoordinationIssue(
            issue_id="iss-1",
            issue_type="resource_conflict",
            severity="high",
            affected_subsystems=["executive", "work"],
            description="test issue",
        )
        d = i.to_dict()
        assert d["issue_id"] == "iss-1"
        assert d["issue_type"] == "resource_conflict"
        assert d["severity"] == "high"
        assert d["affected_subsystems"] == ["executive", "work"]
        assert d["description"] == "test issue"
        assert "recommendation" in d
        assert "detected_at" in d

    def test_coordination_snapshot_defaults(self) -> None:
        s = CoordinationSnapshot()
        assert s.coordination_health == "aligned"
        assert s.issues == []
        assert s.subsystem_alignment == {}
        assert s.synchronization_score == 0.5
        assert s.bottleneck_count == 0

    def test_coordination_snapshot_to_dict(self) -> None:
        s = CoordinationSnapshot(
            coordination_health="synchronized",
            synchronization_score=0.95,
            bottleneck_count=2,
        )
        d = s.to_dict()
        assert d["coordination_health"] == "synchronized"
        assert d["synchronization_score"] == 0.95
        assert d["bottleneck_count"] == 2
        assert "issues" in d
        assert "subsystem_alignment" in d
        assert "generated_at" in d


# ── Health Score Mapping ─────────────────────────────────────────────


class TestHealthScoreMapping:
    def test_best_tier_scores(self) -> None:
        assert _health_to_score("coherent") == 1.0
        assert _health_to_score("synchronized") == 1.0
        assert _health_to_score("optimized") == 1.0
        assert _health_to_score("thriving") == 1.0

    def test_good_tier_scores(self) -> None:
        assert _health_to_score("aligned") == 0.7
        assert _health_to_score("focused") == 0.7
        assert _health_to_score("growing") == 0.7

    def test_degraded_tier_scores(self) -> None:
        assert _health_to_score("strained") == 0.4
        assert _health_to_score("fragmented") == 0.4
        assert _health_to_score("stagnant") == 0.4

    def test_critical_tier_scores(self) -> None:
        assert _health_to_score("critical") == 0.1
        assert _health_to_score("blind") == 0.1

    def test_unknown_defaults_to_half(self) -> None:
        assert _health_to_score("unknown") == 0.5
        assert _health_to_score("something_else") == 0.5


# ── Runtime Tests ────────────────────────────────────────────────────


class TestOrganismCoordinationEngine:
    @classmethod
    def setup_class(cls) -> None:
        cls.rt = OrganismCoordinationEngine()

    def test_no_deps_graceful_degradation(self) -> None:
        assert isinstance(self.rt.detect_issues(), list)
        assert isinstance(self.rt.subsystem_alignment(), dict)
        score = self.rt.synchronization_score()
        assert 0.0 <= score <= 1.0

    def test_detect_issues_returns_list(self) -> None:
        issues = self.rt.detect_issues()
        assert isinstance(issues, list)

    def test_subsystem_alignment_has_names(self) -> None:
        alignment = self.rt.subsystem_alignment()
        assert isinstance(alignment, dict)
        expected_names = {"governance", "executive", "prediction", "work", "learning", "capability"}
        assert expected_names.issubset(set(alignment.keys()))

    def test_synchronization_score_bounded(self) -> None:
        score = self.rt.synchronization_score()
        assert 0.0 <= score <= 1.0

    def test_health_with_no_deps(self) -> None:
        h = self.rt.health()
        assert isinstance(h, CoordinationHealth)

    def test_health_synchronized_with_healthy_subsystems(self) -> None:
        """All healthy subsystems and no issues → SYNCHRONIZED."""
        mock_subsys = MagicMock()
        mock_subsys.health.return_value = MagicMock(value="coherent")
        mock_subsys.drift_warnings.return_value = []
        mock_subsys.detect_drift.return_value = []
        mock_subsys.at_risk_work.return_value = []
        mock_subsys.unallocated_goals.return_value = []
        mock_subsys.contention_map.return_value = {}
        mock_subsys.compounding_score.return_value = 0.9
        mock_subsys.highest_risk_forecasts.return_value = []
        mock_subsys.budgets.return_value = []

        rt = OrganismCoordinationEngine(
            governance_runtime=mock_subsys,
            executive_portfolio=mock_subsys,
            prediction_portfolio=mock_subsys,
            work_portfolio=mock_subsys,
            learning_portfolio=mock_subsys,
            capability_portfolio=mock_subsys,
            resource_allocation=mock_subsys,
            tradeoff_engine=mock_subsys,
        )
        h = rt.health()
        assert h == CoordinationHealth.SYNCHRONIZED

    def test_health_critical_with_low_score(self) -> None:
        """All critical subsystems → score < 0.3 → CRITICAL."""
        mock_subsys = MagicMock()
        mock_subsys.health.return_value = MagicMock(value="critical")
        mock_subsys.drift_warnings.return_value = []
        mock_subsys.detect_drift.return_value = []
        mock_subsys.at_risk_work.return_value = []
        mock_subsys.unallocated_goals.return_value = []
        mock_subsys.contention_map.return_value = {}
        mock_subsys.compounding_score.return_value = 0.0
        mock_subsys.highest_risk_forecasts.return_value = []
        mock_subsys.budgets.return_value = []

        rt = OrganismCoordinationEngine(
            governance_runtime=mock_subsys,
            executive_portfolio=mock_subsys,
            prediction_portfolio=mock_subsys,
            work_portfolio=mock_subsys,
            learning_portfolio=mock_subsys,
            capability_portfolio=mock_subsys,
            resource_allocation=mock_subsys,
            tradeoff_engine=mock_subsys,
        )
        h = rt.health()
        assert h == CoordinationHealth.CRITICAL

    def test_snapshot_fields(self) -> None:
        snap = self.rt.snapshot()
        assert isinstance(snap, CoordinationSnapshot)
        d = snap.to_dict()
        assert "coordination_health" in d
        assert "issues" in d
        assert "subsystem_alignment" in d
        assert "synchronization_score" in d
        assert "bottleneck_count" in d
        assert "generated_at" in d

    def test_summary_keys(self) -> None:
        s = self.rt.summary()
        assert "coordination_health" in s
        assert "synchronization_score" in s
        assert "issue_count" in s
        assert "subsystem_alignment" in s

    def test_issue_id_uniqueness(self) -> None:
        from substrate.organism.organism_coordination_engine import _issue_id
        id1 = _issue_id("goal_conflict")
        id2 = _issue_id("goal_conflict")
        assert id1 != id2

    def test_goal_conflict_detection_with_many_unallocated(self) -> None:
        """4+ unallocated goals triggers a goal_conflict issue."""
        mock_alloc = MagicMock()
        mock_alloc.unallocated_goals.return_value = ["g1", "g2", "g3", "g4"]
        mock_alloc.health.return_value = MagicMock(value="balanced")
        mock_alloc.drift_warnings.return_value = []

        rt = OrganismCoordinationEngine(resource_allocation=mock_alloc)
        issues = rt.detect_issues()
        goal_issues = [i for i in issues if i.issue_type == "goal_conflict"]
        assert len(goal_issues) >= 1

    def test_resource_conflict_with_contention(self) -> None:
        """3+ targets contending for same resource triggers resource_conflict."""
        mock_tradeoff = MagicMock()
        mock_tradeoff.contention_map.return_value = {
            "time": ["t1", "t2", "t3"],
        }
        mock_tradeoff.health.return_value = MagicMock(value="balanced")
        mock_tradeoff.drift_warnings.return_value = []

        rt = OrganismCoordinationEngine(tradeoff_engine=mock_tradeoff)
        issues = rt.detect_issues()
        resource_issues = [i for i in issues if i.issue_type == "resource_conflict"]
        assert len(resource_issues) >= 1

    def test_capability_bottleneck_detection(self) -> None:
        """Degraded capability health + at-risk work → bottleneck."""
        mock_cap = MagicMock()
        mock_cap.health.return_value = MagicMock(value="stalled")
        mock_cap.drift_warnings.return_value = []
        mock_cap.compounding_score.return_value = 0.1

        mock_work = MagicMock()
        mock_work.health.return_value = MagicMock(value="constrained")
        mock_work.at_risk_work.return_value = [{"id": "w1"}]
        mock_work.detect_drift.return_value = []
        mock_work.drift_warnings.return_value = []

        rt = OrganismCoordinationEngine(
            capability_portfolio=mock_cap,
            work_portfolio=mock_work,
        )
        issues = rt.detect_issues()
        bottleneck_issues = [i for i in issues if i.issue_type == "capability_bottleneck"]
        assert len(bottleneck_issues) >= 1
