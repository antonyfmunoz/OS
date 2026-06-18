"""Campaign 10.1 — Capability Gap Engine tests.

Tests goal→capability gap analysis, severity classification, fuzzy matching,
next-to-build recommendations, graceful degradation.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.capability_gap_engine import (
    CapabilityGap,
    CapabilityGapEngine,
    CapabilityGapSeverity,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockMaturity:
    def __init__(self, value: str = "emerging") -> None:
        self.value = value


class _MockCap:
    def __init__(self, capability_id: str = "", name: str = "", maturity: str = "emerging") -> None:
        self.capability_id = capability_id
        self.name = name
        self.maturity = _MockMaturity(maturity)


class _MockCapabilityRuntime:
    def __init__(self, caps: list | None = None) -> None:
        self._caps = caps or []

    def list_capabilities(self) -> list:
        return self._caps

    def get(self, capability_id: str):
        for c in self._caps:
            if c.capability_id == capability_id:
                return c
        return None


class _MockGoal:
    def __init__(
        self,
        goal_id: str = "",
        title: str = "",
        required_capabilities: list | None = None,
    ) -> None:
        self.goal_id = goal_id
        self.title = title
        self.required_capabilities = required_capabilities or []


class _MockGoalRegistry:
    def __init__(self, goals: list | None = None) -> None:
        self._goals = {g.goal_id: g for g in (goals or [])}

    def list_goals(self, status=None) -> list:
        return list(self._goals.values())

    def get(self, goal_id: str):
        return self._goals.get(goal_id)


def _make_engine(**kwargs) -> CapabilityGapEngine:
    return CapabilityGapEngine(**kwargs)


# ── CapabilityGap dataclass tests ────────────────────────────────────


class TestCapabilityGap:
    def test_defaults(self) -> None:
        g = CapabilityGap()
        assert g.gap_id.startswith("cgap-")
        assert g.severity == CapabilityGapSeverity.CRITICAL

    def test_to_dict_keys(self) -> None:
        g = CapabilityGap(goal_id="g1")
        d = g.to_dict()
        expected = {
            "gap_id", "goal_id", "goal_title", "required_capability",
            "matched_capability_id", "matched_capability_name",
            "matched_maturity", "severity", "recommendation", "created_at",
        }
        assert set(d.keys()) == expected

    def test_round_trip(self) -> None:
        g = CapabilityGap(goal_id="g1", severity=CapabilityGapSeverity.HIGH)
        d = g.to_dict()
        g2 = CapabilityGap.from_dict(d)
        assert g2.goal_id == "g1"
        assert g2.severity == CapabilityGapSeverity.HIGH


class TestCapabilityGapSeverity:
    def test_values(self) -> None:
        assert CapabilityGapSeverity.CRITICAL.value == "critical"
        assert CapabilityGapSeverity.HIGH.value == "high"
        assert CapabilityGapSeverity.MEDIUM.value == "medium"
        assert CapabilityGapSeverity.LOW.value == "low"


# ── Acceptance test: the 4 questions ─────────────────────────────────


class TestAcceptanceQuestions:
    """Given a goal with required_capabilities, UMH answers:
    1. Which capabilities already satisfy it?
    2. Which capabilities are missing?
    3. Which capabilities exist but are too immature?
    4. Which capability should be matured or built next?
    """

    def _setup(self):
        caps = [
            _MockCap("c1", "Strategic Planning", "operational"),
            _MockCap("c2", "Risk Analysis", "emerging"),
            _MockCap("c3", "Code Review", "institutional"),
        ]
        goals = [
            _MockGoal("g1", "Launch Product", [
                "Strategic Planning",    # satisfied (operational)
                "Risk Analysis",         # immature (emerging)
                "Release Coordination",  # missing entirely
            ]),
        ]
        return _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )

    def test_q1_satisfied_capabilities(self) -> None:
        eng = self._setup()
        satisfied = eng.satisfied()
        names = [g.matched_capability_name for g in satisfied]
        assert "Strategic Planning" in names

    def test_q2_missing_capabilities(self) -> None:
        eng = self._setup()
        critical = eng.critical_gaps()
        required = [g.required_capability for g in critical]
        assert "Release Coordination" in required

    def test_q3_immature_capabilities(self) -> None:
        eng = self._setup()
        immature = eng.immature_gaps()
        names = [g.matched_capability_name for g in immature]
        assert "Risk Analysis" in names

    def test_q4_next_to_build(self) -> None:
        eng = self._setup()
        recs = eng.next_to_build(5)
        assert len(recs) >= 1
        assert recs[0]["severity"] == "critical"
        assert recs[0]["required_capability"] == "Release Coordination"


# ── analyze_gaps tests ───────────────────────────────────────────────


class TestAnalyzeGaps:
    def test_no_goal_registry(self) -> None:
        eng = _make_engine()
        assert eng.analyze_gaps() == []

    def test_goal_with_no_required(self) -> None:
        goals = [_MockGoal("g1", "Simple Goal")]
        eng = _make_engine(goal_registry=_MockGoalRegistry(goals))
        assert eng.analyze_gaps() == []

    def test_all_missing(self) -> None:
        goals = [_MockGoal("g1", "Goal", ["Cap A", "Cap B"])]
        eng = _make_engine(
            goal_registry=_MockGoalRegistry(goals),
            capability_runtime=_MockCapabilityRuntime([]),
        )
        gaps = eng.analyze_gaps()
        assert len(gaps) == 2
        assert all(g.severity == CapabilityGapSeverity.CRITICAL for g in gaps)

    def test_all_satisfied(self) -> None:
        caps = [_MockCap("c1", "Auth System", "operational")]
        goals = [_MockGoal("g1", "Secure System", ["Auth System"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        gaps = eng.analyze_gaps()
        assert len(gaps) == 1
        assert gaps[0].severity == CapabilityGapSeverity.LOW

    def test_sorted_by_severity(self) -> None:
        caps = [_MockCap("c1", "Existing Cap", "emerging")]
        goals = [_MockGoal("g1", "Goal", ["Existing Cap", "Missing Cap"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        gaps = eng.analyze_gaps()
        assert len(gaps) == 2
        assert gaps[0].severity.value <= gaps[1].severity.value or gaps[0].severity == CapabilityGapSeverity.CRITICAL


# ── Fuzzy matching tests ─────────────────────────────────────────────


class TestFuzzyMatching:
    def test_exact_match(self) -> None:
        caps = [_MockCap("c1", "Strategic Planning", "operational")]
        goals = [_MockGoal("g1", "Goal", ["Strategic Planning"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        gaps = eng.analyze_gaps()
        assert gaps[0].matched_capability_name == "Strategic Planning"

    def test_case_insensitive(self) -> None:
        caps = [_MockCap("c1", "strategic planning", "operational")]
        goals = [_MockGoal("g1", "Goal", ["Strategic Planning"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        gaps = eng.analyze_gaps()
        assert gaps[0].matched_capability_id == "c1"

    def test_substring_match(self) -> None:
        caps = [_MockCap("c1", "Advanced Strategic Planning Engine", "validated")]
        goals = [_MockGoal("g1", "Goal", ["Strategic Planning"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        gaps = eng.analyze_gaps()
        assert gaps[0].matched_capability_id == "c1"

    def test_no_match(self) -> None:
        caps = [_MockCap("c1", "Completely Different", "operational")]
        goals = [_MockGoal("g1", "Goal", ["Video Editing"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        gaps = eng.analyze_gaps()
        assert gaps[0].severity == CapabilityGapSeverity.CRITICAL
        assert gaps[0].matched_capability_id == ""


# ── Severity classification tests ────────────────────────────────────


class TestSeverityClassification:
    def test_institutional_is_low(self) -> None:
        caps = [_MockCap("c1", "Cap", "institutional")]
        goals = [_MockGoal("g1", "Goal", ["Cap"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        assert eng.analyze_gaps()[0].severity == CapabilityGapSeverity.LOW

    def test_operational_is_low(self) -> None:
        caps = [_MockCap("c1", "Cap", "operational")]
        goals = [_MockGoal("g1", "Goal", ["Cap"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        assert eng.analyze_gaps()[0].severity == CapabilityGapSeverity.LOW

    def test_validated_is_medium(self) -> None:
        caps = [_MockCap("c1", "Cap", "validated")]
        goals = [_MockGoal("g1", "Goal", ["Cap"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        assert eng.analyze_gaps()[0].severity == CapabilityGapSeverity.MEDIUM

    def test_emerging_is_high(self) -> None:
        caps = [_MockCap("c1", "Cap", "emerging")]
        goals = [_MockGoal("g1", "Goal", ["Cap"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        assert eng.analyze_gaps()[0].severity == CapabilityGapSeverity.HIGH


# ── gaps_for_goal tests ──────────────────────────────────────────────


class TestGapsForGoal:
    def test_specific_goal(self) -> None:
        caps = [_MockCap("c1", "Planning", "operational")]
        goals = [
            _MockGoal("g1", "Goal A", ["Planning"]),
            _MockGoal("g2", "Goal B", ["Missing"]),
        ]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        g1_gaps = eng.gaps_for_goal("g1")
        assert len(g1_gaps) == 1
        assert g1_gaps[0].severity == CapabilityGapSeverity.LOW

    def test_nonexistent_goal(self) -> None:
        eng = _make_engine(goal_registry=_MockGoalRegistry([]))
        assert eng.gaps_for_goal("nonexistent") == []


# ── gap_summary tests ────────────────────────────────────────────────


class TestGapSummary:
    def test_summary_keys(self) -> None:
        eng = _make_engine()
        s = eng.gap_summary()
        expected = {"total_gaps", "by_severity", "critical_count", "next_to_build", "generated_at"}
        assert set(s.keys()) == expected

    def test_summary_counts(self) -> None:
        caps = [_MockCap("c1", "Cap", "emerging")]
        goals = [_MockGoal("g1", "Goal", ["Cap", "Missing"])]
        eng = _make_engine(
            capability_runtime=_MockCapabilityRuntime(caps),
            goal_registry=_MockGoalRegistry(goals),
        )
        s = eng.gap_summary()
        assert s["total_gaps"] == 2
        assert s["critical_count"] == 1


# ── Graceful degradation ─────────────────────────────────────────────


class TestGracefulDegradation:
    def test_no_engines(self) -> None:
        eng = _make_engine()
        assert eng.analyze_gaps() == []
        assert eng.critical_gaps() == []
        assert eng.gap_summary()["total_gaps"] == 0

    def test_broken_goal_registry(self) -> None:
        class _Broken:
            def list_goals(self, status=None):
                raise RuntimeError("down")
        eng = _make_engine(goal_registry=_Broken())
        assert eng.analyze_gaps() == []

    def test_no_capability_runtime(self) -> None:
        goals = [_MockGoal("g1", "Goal", ["Some Cap"])]
        eng = _make_engine(goal_registry=_MockGoalRegistry(goals))
        gaps = eng.analyze_gaps()
        assert all(g.severity == CapabilityGapSeverity.CRITICAL for g in gaps)
