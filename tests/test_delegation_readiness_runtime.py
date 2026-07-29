"""Tests for DelegationReadinessRuntime — Campaign 11.1."""

import sys
import os

# Repo root is DERIVED from the active checkout, never hardcoded. The previous
# module-scope `sys.path.insert(...)` + `os.environ.setdefault("UMH_ROOT", ...)`
# pinned a foreign campaign worktree at IMPORT time and never restored it, so it
# leaked into every module collected afterwards and hard-aborted whole shards.
from tests.repo_root import ensure_repo_on_path

ensure_repo_on_path()

import pytest
from substrate.organism.delegation_readiness_runtime import (
    DelegationReadiness,
    DelegationReadinessSnapshot,
    DelegationReadinessRuntime,
)


# ── Mock helpers ──────────────────────────────────────────────────────────


class _MockFleetAssignment:
    def __init__(
        self,
        agent_type_id="agent-A",
        agent_label="Agent A",
        score=0.8,
        matched_capabilities=None,
        alternatives=None,
        rationale=None,
    ):
        self.agent_type_id = agent_type_id
        self.agent_label = agent_label
        self.score = score
        self.matched_capabilities = matched_capabilities or ["python", "git"]
        self.alternatives = alternatives or ["agent-B"]
        self.rationale = rationale


class _MockRationale:
    def __init__(self, summary="good match"):
        self.summary = summary


class _MockFleetRuntime:
    def __init__(self, assignment=None, fail=False):
        self._assignment = assignment or _MockFleetAssignment()
        self._fail = fail

    def assign(self, capabilities_required=None, risk_class="low"):
        if self._fail:
            raise RuntimeError("fleet unavailable")
        return self._assignment


class _MockCapProfile:
    def __init__(self, total_attempts=10, overall_reliability=0.9):
        self.total_attempts = total_attempts
        self.overall_reliability = overall_reliability


class _MockCapModel:
    def __init__(self, profile=None):
        self._profile = profile or _MockCapProfile()

    def get_profile(self, executor_type):
        return self._profile


class _MockCapGap:
    def __init__(self, gaps=None):
        self._gaps = gaps or {}

    def gaps_for_goal(self, goal_id):
        return self._gaps.get(goal_id, [])


class _MockGapItem:
    def __init__(self, required_capability="advanced-ml"):
        self.required_capability = required_capability


class _MockDecisionValidity:
    def __init__(self, at_risk_list=None, invalid_list=None):
        self._at_risk = at_risk_list or []
        self._invalid = invalid_list or []

    def at_risk(self):
        return self._at_risk

    def invalid(self):
        return self._invalid


class _MockAtRiskDecision:
    def __init__(self, decision_id="d-1", recommendation="revisit"):
        self.decision_id = decision_id
        self.recommendation = recommendation


class _MockOutcome:
    def __init__(self, at_risk_goals=None):
        self._at_risk = at_risk_goals or []

    def goals_at_risk(self):
        return self._at_risk


class _MockAtRiskGoal:
    def __init__(self, goal_id="g-1"):
        self.goal_id = goal_id


class _MockReadinessAssessment:
    def __init__(self, work_id="wp-1", goal_ids=None):
        self.work_id = work_id
        self.goal_ids = goal_ids or []


class _MockReadinessRuntime:
    def __init__(self, assessments=None):
        self._assessments = assessments or []

    def assess_all(self):
        return self._assessments


# ── DelegationReadiness Tests ─────────────────────────────────────────────


class TestDelegationReadiness:
    def test_defaults(self):
        dr = DelegationReadiness()
        assert dr.work_id == ""
        assert dr.delegatable is False
        assert dr.confidence == 0.0
        assert dr.success_probability == 0.0

    def test_to_dict(self):
        dr = DelegationReadiness(
            work_id="wp-1",
            delegatable=True,
            recommended_executor="agent-A",
            confidence=0.85,
            success_probability=0.72,
            capabilities_required=["python"],
            capabilities_matched=["python"],
            rationale="good match",
        )
        d = dr.to_dict()
        assert d["work_id"] == "wp-1"
        assert d["delegatable"] is True
        assert d["confidence"] == 0.85
        assert d["success_probability"] == 0.72
        assert d["rationale"] == "good match"

    def test_from_dict(self):
        d = {
            "work_id": "wp-2",
            "delegatable": False,
            "recommended_executor": "agent-B",
            "confidence": 0.1,
            "risk_factors": ["projection: overdue"],
        }
        dr = DelegationReadiness.from_dict(d)
        assert dr.work_id == "wp-2"
        assert dr.delegatable is False
        assert dr.recommended_executor == "agent-B"
        assert len(dr.risk_factors) == 1

    def test_roundtrip(self):
        dr = DelegationReadiness(
            work_id="wp-3",
            delegatable=True,
            confidence=0.9,
            success_probability=0.75,
            capabilities_required=["git"],
            capabilities_missing=["docker"],
            alternatives=["agent-C"],
        )
        d = dr.to_dict()
        dr2 = DelegationReadiness.from_dict(d)
        assert dr2.work_id == dr.work_id
        assert dr2.delegatable == dr.delegatable
        assert dr2.confidence == dr.confidence

    def test_confidence_rounding(self):
        dr = DelegationReadiness(confidence=0.33333333)
        d = dr.to_dict()
        assert d["confidence"] == 0.3333


# ── DelegationReadinessSnapshot Tests ─────────────────────────────────────


class TestDelegationReadinessSnapshot:
    def test_defaults(self):
        snap = DelegationReadinessSnapshot()
        assert snap.total_assessed == 0
        assert snap.delegatable == 0

    def test_to_dict(self):
        snap = DelegationReadinessSnapshot(
            total_assessed=10,
            delegatable=7,
            not_delegatable=3,
            avg_confidence=0.75,
            top_missing_capabilities=["docker", "k8s"],
        )
        d = snap.to_dict()
        assert d["total_assessed"] == 10
        assert d["delegatable"] == 7
        assert d["avg_confidence"] == 0.75
        assert "docker" in d["top_missing_capabilities"]


# ── DelegationReadinessRuntime Tests ──────────────────────────────────────


class TestDelegationReadinessRuntime:
    @pytest.fixture
    def runtime(self):
        return DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            capability_model=_MockCapModel(),
            capability_gap=_MockCapGap(),
            decision_validity=_MockDecisionValidity(),
            outcome_tracking=_MockOutcome(),
            work_readiness=_MockReadinessRuntime(),
        )

    def test_assess_delegatable(self, runtime):
        dr = runtime.assess("wp-1", capabilities_required=["python"], risk_class="low")
        assert dr.delegatable is True
        assert dr.recommended_executor == "agent-A"
        assert dr.confidence == 0.8
        assert dr.success_probability > 0

    def test_assess_not_delegatable_missing_caps(self):
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            capability_model=_MockCapModel(),
            capability_gap=_MockCapGap(gaps={
                "g-1": [_MockGapItem("advanced-ml")],
            }),
        )
        dr = rt.assess("wp-1", goal_id="g-1")
        assert dr.delegatable is False
        assert "advanced-ml" in dr.capabilities_missing

    def test_assess_not_delegatable_low_confidence(self):
        low_assignment = _MockFleetAssignment(score=0.1)
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(assignment=low_assignment),
        )
        dr = rt.assess("wp-1")
        assert dr.delegatable is False
        assert "low confidence" in dr.rationale

    def test_assess_fleet_unavailable(self):
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(fail=True),
        )
        dr = rt.assess("wp-1")
        assert dr.delegatable is False
        assert dr.recommended_executor == ""

    def test_success_probability_formula(self, runtime):
        prob = runtime._compute_success_probability(
            confidence=0.8,
            reliability=0.9,
            risk_factor_count=0,
            blocking_decision_count=0,
            capability_gap_count=0,
        )
        expected = (0.8 * 0.3) + (0.9 * 0.4) + 0.3
        assert abs(prob - expected) < 0.001

    def test_success_probability_with_penalties(self, runtime):
        prob = runtime._compute_success_probability(
            confidence=0.8,
            reliability=0.9,
            risk_factor_count=2,
            blocking_decision_count=1,
            capability_gap_count=1,
        )
        base = (0.8 * 0.3) + (0.9 * 0.4) + 0.3
        penalty = 2 * 0.1 + 1 * 0.15 + 1 * 0.2
        assert abs(prob - max(0, base - penalty)) < 0.001

    def test_success_probability_floor(self, runtime):
        prob = runtime._compute_success_probability(
            confidence=0.0,
            reliability=0.0,
            risk_factor_count=10,
            blocking_decision_count=10,
            capability_gap_count=10,
        )
        assert prob == 0.0

    def test_success_probability_ceiling(self, runtime):
        prob = runtime._compute_success_probability(
            confidence=1.0,
            reliability=1.0,
            risk_factor_count=0,
            blocking_decision_count=0,
            capability_gap_count=0,
        )
        assert prob == 1.0

    def test_risk_factors_from_decisions(self):
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            decision_validity=_MockDecisionValidity(
                at_risk_list=[_MockAtRiskDecision("d-1")],
            ),
        )
        dr = rt.assess("wp-1")
        assert any("d-1" in rf for rf in dr.risk_factors)

    def test_blocking_decisions(self):
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            decision_validity=_MockDecisionValidity(
                invalid_list=[_MockAtRiskDecision("d-invalid")],
            ),
        )
        dr = rt.assess("wp-1")
        assert "d-invalid" in dr.blocking_decisions

    def test_outcome_risk_factors(self):
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            outcome_tracking=_MockOutcome(
                at_risk_goals=[_MockAtRiskGoal("g-1")],
            ),
        )
        dr = rt.assess("wp-1", goal_id="g-1")
        assert any("g-1" in rf for rf in dr.risk_factors)

    def test_assess_batch(self, runtime):
        results = runtime.assess_batch(["wp-1", "wp-2", "wp-3"])
        assert len(results) == 3
        assert all(isinstance(r, DelegationReadiness) for r in results)

    def test_best_executor_for(self, runtime):
        dr = runtime.best_executor_for(["python", "git"])
        assert dr.work_id == ""
        assert dr.recommended_executor == "agent-A"

    def test_success_probability_api(self, runtime):
        prob = runtime.success_probability("wp-1")
        assert 0.0 <= prob <= 1.0

    def test_snapshot_empty(self):
        rt = DelegationReadinessRuntime(
            work_readiness=_MockReadinessRuntime(assessments=[]),
        )
        snap = rt.snapshot()
        assert snap.total_assessed == 0

    def test_snapshot_with_work(self):
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            capability_model=_MockCapModel(),
            work_readiness=_MockReadinessRuntime(
                assessments=[_MockReadinessAssessment("wp-1", ["g-1"])],
            ),
        )
        snap = rt.snapshot()
        assert snap.total_assessed == 1

    def test_summary(self, runtime):
        s = runtime.summary()
        assert "total_assessed" in s
        assert "delegatable" in s
        assert "avg_confidence" in s

    def test_graceful_degradation_no_subsystems(self):
        rt = DelegationReadinessRuntime()
        dr = rt.assess("wp-1")
        assert dr.delegatable is False
        assert dr.success_probability > 0

    def test_rationale_generated_for_delegatable(self):
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            capability_model=_MockCapModel(),
        )
        dr = rt.assess("wp-1", capabilities_required=["python"])
        assert "executor=" in dr.rationale or "agent-A" in dr.rationale

    def test_alternatives_propagated(self, runtime):
        dr = runtime.assess("wp-1")
        assert isinstance(dr.alternatives, list)

    def test_executor_reliability_used(self):
        high_rel = _MockCapProfile(total_attempts=100, overall_reliability=0.95)
        low_rel = _MockCapProfile(total_attempts=100, overall_reliability=0.1)
        rt_high = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            capability_model=_MockCapModel(profile=high_rel),
        )
        rt_low = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(),
            capability_model=_MockCapModel(profile=low_rel),
        )
        dr_high = rt_high.assess("wp-1")
        dr_low = rt_low.assess("wp-1")
        assert dr_high.success_probability > dr_low.success_probability

    def test_fleet_rationale_object(self):
        assign = _MockFleetAssignment(rationale=_MockRationale("great fit"))
        rt = DelegationReadinessRuntime(
            fleet_runtime=_MockFleetRuntime(assignment=assign),
        )
        dr = rt.assess("wp-1", capabilities_required=["python"])
        assert "great fit" in dr.rationale
