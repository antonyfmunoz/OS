"""Campaign 7.5 — Executive Brief Runtime tests.

Tests structured operator briefing generation: situation synthesis,
progress/blockers/risks/priorities/recommendations/drift population,
text formatting, graceful degradation.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.executive_brief_runtime import (
    ExecutiveBrief,
    ExecutiveBriefRuntime,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockStrategicContext:
    def __init__(
        self,
        health: str = "healthy",
        active_projects: list | None = None,
        active_work: list | None = None,
        blocked_work: list | None = None,
    ) -> None:
        self._health = health
        self._active_projects = active_projects or []
        self._active_work = active_work or []
        self._blocked_work = blocked_work or []

    def context(self) -> "_FakeCtx":
        return _FakeCtx(
            self._health,
            self._active_projects,
            self._active_work,
            self._blocked_work,
        )


class _FakeCtx:
    def __init__(
        self,
        health: str,
        active_projects: list,
        active_work: list,
        blocked_work: list,
    ) -> None:
        self.health = health
        self.active_projects = active_projects
        self.active_work = active_work
        self.blocked_work = blocked_work


class _MockPrioritizedItem:
    def __init__(self, title: str = "", score: float = 0.5) -> None:
        self.title = title
        self.score = score


class _MockPriorityEngine:
    def __init__(self, priorities: list | None = None) -> None:
        self._priorities = priorities or []

    def top(self, limit: int = 5) -> list:
        return self._priorities[:limit]


class _MockRisk:
    def __init__(self, title: str = "", severity: str = "medium") -> None:
        self.title = title
        self.severity = severity


class _MockRiskEngine:
    def __init__(self, risks: list | None = None) -> None:
        self._risks = risks or []

    def high_risks(self) -> list:
        return self._risks


class _MockRecommendation:
    def __init__(self, action: str = "", reason: str = "") -> None:
        self.action = action
        self.reason = reason


class _MockRecommendationEngine:
    def __init__(self, recs: list | None = None) -> None:
        self._recs = recs or []

    def top(self, limit: int = 3) -> list:
        return self._recs[:limit]


class _MockDrift:
    def __init__(self, title: str = "", drift_type: str = "strategic") -> None:
        self.title = title
        self.drift_type = drift_type


class _MockDriftEngine:
    def __init__(self, drifts: list | None = None) -> None:
        self._drifts = drifts or []

    def high_drift(self) -> list:
        return self._drifts


def _make_runtime(**kwargs) -> ExecutiveBriefRuntime:
    return ExecutiveBriefRuntime(**kwargs)


# ── ExecutiveBrief dataclass tests ──────────────────────────────────


class TestExecutiveBrief:
    def test_default_values(self) -> None:
        b = ExecutiveBrief()
        assert b.situation == ""
        assert b.health == "healthy"
        assert b.progress == []
        assert b.blockers == []
        assert b.risks == []
        assert b.priorities == []
        assert b.recommendations == []
        assert b.drift_warnings == []

    def test_to_dict_keys(self) -> None:
        b = ExecutiveBrief(situation="test")
        d = b.to_dict()
        expected = {
            "situation", "progress", "blockers", "risks",
            "priorities", "recommendations", "drift_warnings",
            "health", "generated_at",
        }
        assert set(d.keys()) == expected

    def test_to_text_health_header(self) -> None:
        b = ExecutiveBrief(health="critical")
        text = b.to_text()
        assert text.startswith("Health: CRITICAL")

    def test_to_text_sections(self) -> None:
        b = ExecutiveBrief(
            health="watch",
            situation="2 projects active",
            progress=["auth (active)"],
            blockers=["deploy: config missing"],
            risks=["[HIGH] auth risk"],
            priorities=["fix auth (score: 0.85)"],
            drift_warnings=["[strategic] stale goal"],
            recommendations=["deploy system"],
        )
        text = b.to_text()
        assert "Situation:" in text
        assert "Progress:" in text
        assert "Blockers:" in text
        assert "Risks:" in text
        assert "Priorities:" in text
        assert "Drift:" in text
        assert "Recommended Actions:" in text

    def test_to_text_empty_sections_omitted(self) -> None:
        b = ExecutiveBrief(health="healthy")
        text = b.to_text()
        assert "Progress:" not in text
        assert "Blockers:" not in text
        assert "Risks:" not in text


# ── Situation fill tests ────────────────────────────────────────────


class TestSituationFill:
    def test_situation_from_context(self) -> None:
        ctx = _MockStrategicContext(
            health="watch",
            active_projects=["p1", "p2"],
            active_work=[{"title": "w1"}],
        )
        runtime = _make_runtime(strategic_context=ctx)
        brief = runtime.generate()
        assert "2 active project(s)" in brief.situation
        assert "1 work item(s)" in brief.situation
        assert brief.health == "watch"

    def test_situation_with_blocked(self) -> None:
        ctx = _MockStrategicContext(
            health="degraded",
            blocked_work=[{"title": "b1"}, {"title": "b2"}],
        )
        runtime = _make_runtime(strategic_context=ctx)
        brief = runtime.generate()
        assert "2 blocked" in brief.situation

    def test_no_context_fallback(self) -> None:
        runtime = _make_runtime()
        brief = runtime.generate()
        assert brief.situation == "No strategic context available"

    def test_broken_context_fallback(self) -> None:
        class _Broken:
            def context(self):
                raise RuntimeError("down")
        runtime = _make_runtime(strategic_context=_Broken())
        brief = runtime.generate()
        assert brief.situation == "Strategic context unavailable"


# ── Progress fill tests ─────────────────────────────────────────────


class TestProgressFill:
    def test_progress_from_active_work(self) -> None:
        ctx = _MockStrategicContext(
            active_work=[
                {"title": "auth migration", "status": "executing"},
                {"title": "deploy", "status": "queued"},
            ],
        )
        runtime = _make_runtime(strategic_context=ctx)
        brief = runtime.generate()
        assert len(brief.progress) == 2
        assert "auth migration (executing)" in brief.progress[0]

    def test_progress_caps_at_5(self) -> None:
        ctx = _MockStrategicContext(
            active_work=[{"title": f"w-{i}"} for i in range(10)],
        )
        runtime = _make_runtime(strategic_context=ctx)
        brief = runtime.generate()
        assert len(brief.progress) == 5


# ── Blockers fill tests ─────────────────────────────────────────────


class TestBlockersFill:
    def test_blockers_from_blocked_work(self) -> None:
        ctx = _MockStrategicContext(
            blocked_work=[{"title": "deploy", "reason": "config missing"}],
        )
        runtime = _make_runtime(strategic_context=ctx)
        brief = runtime.generate()
        assert len(brief.blockers) == 1
        assert "deploy" in brief.blockers[0]
        assert "config missing" in brief.blockers[0]


# ── Risk fill tests ─────────────────────────────────────────────────


class TestRiskFill:
    def test_risks_from_engine(self) -> None:
        risk_engine = _MockRiskEngine(
            risks=[_MockRisk("auth risk", "high")],
        )
        runtime = _make_runtime(risk_engine=risk_engine)
        brief = runtime.generate()
        assert len(brief.risks) == 1
        assert "[HIGH]" in brief.risks[0]
        assert "auth risk" in brief.risks[0]

    def test_risks_capped_at_3(self) -> None:
        risk_engine = _MockRiskEngine(
            risks=[_MockRisk(f"r-{i}") for i in range(5)],
        )
        runtime = _make_runtime(risk_engine=risk_engine)
        brief = runtime.generate()
        assert len(brief.risks) == 3

    def test_no_risk_engine(self) -> None:
        runtime = _make_runtime()
        brief = runtime.generate()
        assert brief.risks == []


# ── Priority fill tests ─────────────────────────────────────────────


class TestPriorityFill:
    def test_priorities_from_engine(self) -> None:
        priority_engine = _MockPriorityEngine(
            priorities=[_MockPrioritizedItem("fix auth", 0.85)],
        )
        runtime = _make_runtime(priority_engine=priority_engine)
        brief = runtime.generate()
        assert len(brief.priorities) == 1
        assert "fix auth" in brief.priorities[0]
        assert "0.85" in brief.priorities[0]

    def test_priorities_capped_at_5(self) -> None:
        priority_engine = _MockPriorityEngine(
            priorities=[_MockPrioritizedItem(f"p-{i}") for i in range(8)],
        )
        runtime = _make_runtime(priority_engine=priority_engine)
        brief = runtime.generate()
        assert len(brief.priorities) == 5


# ── Recommendation fill tests ───────────────────────────────────────


class TestRecommendationFill:
    def test_recommendations_from_engine(self) -> None:
        rec_engine = _MockRecommendationEngine(
            recs=[_MockRecommendation("deploy system", "stability")],
        )
        runtime = _make_runtime(recommendation_engine=rec_engine)
        brief = runtime.generate()
        assert len(brief.recommendations) == 1
        assert "deploy system" in brief.recommendations[0]
        assert "stability" in brief.recommendations[0]

    def test_recommendation_without_reason(self) -> None:
        rec_engine = _MockRecommendationEngine(
            recs=[_MockRecommendation("quick fix")],
        )
        runtime = _make_runtime(recommendation_engine=rec_engine)
        brief = runtime.generate()
        assert brief.recommendations[0] == "quick fix"

    def test_recommendations_capped_at_3(self) -> None:
        rec_engine = _MockRecommendationEngine(
            recs=[_MockRecommendation(f"r-{i}") for i in range(5)],
        )
        runtime = _make_runtime(recommendation_engine=rec_engine)
        brief = runtime.generate()
        assert len(brief.recommendations) == 3


# ── Drift fill tests ────────────────────────────────────────────────


class TestDriftFill:
    def test_drift_from_engine(self) -> None:
        drift_engine = _MockDriftEngine(
            drifts=[_MockDrift("stale goal", "strategic")],
        )
        runtime = _make_runtime(drift_engine=drift_engine)
        brief = runtime.generate()
        assert len(brief.drift_warnings) == 1
        assert "[strategic]" in brief.drift_warnings[0]
        assert "stale goal" in brief.drift_warnings[0]

    def test_drift_capped_at_5(self) -> None:
        drift_engine = _MockDriftEngine(
            drifts=[_MockDrift(f"d-{i}") for i in range(8)],
        )
        runtime = _make_runtime(drift_engine=drift_engine)
        brief = runtime.generate()
        assert len(brief.drift_warnings) == 5


# ── summary() and snapshot() tests ──────────────────────────────────


class TestSummaryAndSnapshot:
    def test_summary_keys(self) -> None:
        runtime = _make_runtime()
        s = runtime.summary()
        expected = {
            "health", "situation", "priority_count", "risk_count",
            "blocker_count", "drift_count", "recommendation_count",
            "generated_at",
        }
        assert set(s.keys()) == expected

    def test_summary_counts(self) -> None:
        ctx = _MockStrategicContext(blocked_work=[{"title": "b1", "reason": "x"}])
        priority_engine = _MockPriorityEngine([_MockPrioritizedItem("p1")])
        runtime = _make_runtime(
            strategic_context=ctx,
            priority_engine=priority_engine,
        )
        s = runtime.summary()
        assert s["blocker_count"] == 1
        assert s["priority_count"] == 1

    def test_snapshot_matches_to_dict(self) -> None:
        ctx = _MockStrategicContext(health="watch")
        runtime = _make_runtime(strategic_context=ctx)
        snap = runtime.snapshot()
        assert snap["health"] == "watch"
        assert "situation" in snap


# ── Full composition tests ──────────────────────────────────────────


class TestFullComposition:
    def test_all_engines_compose(self) -> None:
        runtime = _make_runtime(
            strategic_context=_MockStrategicContext(
                health="degraded",
                active_projects=["p1"],
                active_work=[{"title": "w1", "status": "active"}],
                blocked_work=[{"title": "b1", "reason": "config"}],
            ),
            priority_engine=_MockPriorityEngine([_MockPrioritizedItem("fix auth", 0.9)]),
            risk_engine=_MockRiskEngine([_MockRisk("auth risk", "critical")]),
            recommendation_engine=_MockRecommendationEngine([
                _MockRecommendation("deploy", "stability"),
            ]),
            drift_engine=_MockDriftEngine([_MockDrift("stale goal", "strategic")]),
        )
        brief = runtime.generate()
        assert brief.health == "degraded"
        assert len(brief.progress) == 1
        assert len(brief.blockers) == 1
        assert len(brief.risks) == 1
        assert len(brief.priorities) == 1
        assert len(brief.recommendations) == 1
        assert len(brief.drift_warnings) == 1

    def test_generated_at_set(self) -> None:
        runtime = _make_runtime()
        brief = runtime.generate()
        assert brief.generated_at > 0


# ── Graceful degradation ───────────────────────────────────────────


class TestGracefulDegradation:
    def test_no_engines(self) -> None:
        runtime = _make_runtime()
        brief = runtime.generate()
        assert brief.health == "healthy"
        assert brief.situation == "No strategic context available"
        assert brief.progress == []
        assert brief.risks == []

    def test_broken_risk_engine(self) -> None:
        class _Broken:
            def high_risks(self):
                raise RuntimeError("down")
        runtime = _make_runtime(risk_engine=_Broken())
        brief = runtime.generate()
        assert brief.risks == []

    def test_broken_priority_engine(self) -> None:
        class _Broken:
            def top(self, limit=5):
                raise RuntimeError("down")
        runtime = _make_runtime(priority_engine=_Broken())
        brief = runtime.generate()
        assert brief.priorities == []

    def test_broken_recommendation_engine(self) -> None:
        class _Broken:
            def top(self, limit=3):
                raise RuntimeError("down")
        runtime = _make_runtime(recommendation_engine=_Broken())
        brief = runtime.generate()
        assert brief.recommendations == []

    def test_broken_drift_engine(self) -> None:
        class _Broken:
            def high_drift(self):
                raise RuntimeError("down")
        runtime = _make_runtime(drift_engine=_Broken())
        brief = runtime.generate()
        assert brief.drift_warnings == []

    def test_mixed_working_and_broken(self) -> None:
        class _BrokenRisk:
            def high_risks(self):
                raise RuntimeError("down")
        runtime = _make_runtime(
            strategic_context=_MockStrategicContext(health="watch"),
            risk_engine=_BrokenRisk(),
            priority_engine=_MockPriorityEngine([_MockPrioritizedItem("p1")]),
        )
        brief = runtime.generate()
        assert brief.health == "watch"
        assert brief.risks == []
        assert len(brief.priorities) == 1
