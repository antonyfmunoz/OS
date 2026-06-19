"""Campaign 7.0 — Strategic Context Runtime tests.

Tests the executive synthesis facade: health classification,
engine composition, graceful degradation, serialization.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.strategic_context_runtime import (
    StrategicContext,
    StrategicContextRuntime,
    StrategicHealth,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockGapEngine:
    def __init__(self, gaps: list | None = None, recs: list | None = None) -> None:
        self._gaps = gaps or []
        self._recs = recs or []

    def analyze(self) -> dict:
        return {
            "gaps": self._gaps,
            "gap_count": len(self._gaps),
            "recommendations": self._recs,
            "recommendation_count": len(self._recs),
        }


class _MockTickLoop:
    def __init__(
        self,
        drift: list | None = None,
        candidates: list | None = None,
    ) -> None:
        self._drift = drift or []
        self._candidates = candidates or []

    def get_strategic_state(self) -> dict:
        return {
            "drift_warnings": self._drift,
            "candidate_queue": {"items": self._candidates},
        }


class _MockProjectionEngine:
    def __init__(self, risks: list | None = None) -> None:
        self._risks = risks or []

    def get_projection_state(self) -> dict:
        return {"risks": self._risks}


class _MockOperatorContext:
    def __init__(self, approvals: list | None = None) -> None:
        self._approvals = approvals or []

    def pending_approvals(self) -> dict:
        return {"items": self._approvals}


class _MockNextActionEngine:
    def __init__(self, actions: list | None = None) -> None:
        self._actions = actions or []

    @property
    def actions(self) -> list:
        return self._actions


class _MockAction:
    def __init__(self, action: str = "", priority_score: float = 0.5) -> None:
        self.action = action
        self.priority_score = priority_score

    def to_dict(self) -> dict:
        return {"action": self.action, "priority_score": self.priority_score}


class _MockRuntimeAwareness:
    def __init__(
        self,
        active: list | None = None,
        blocked: list | None = None,
    ) -> None:
        self._active = active or []
        self._blocked = blocked or []

    def active_work(self) -> list:
        return self._active

    def blocked_work(self) -> list:
        return self._blocked


class _MockKnowledgeAwareness:
    def __init__(self, constraints: list | None = None) -> None:
        self._constraints = constraints or []

    def find_constraints(self) -> list:
        return self._constraints


class _MockKnowledgeEntry:
    def __init__(self, summary: str = "") -> None:
        self.summary = summary

    def to_dict(self) -> dict:
        return {"summary": self.summary}


class _MockRealityGraph:
    def __init__(self, projects: list | None = None) -> None:
        self._projects = projects or []

    def find_by_type(self, entity_type: str) -> list:
        return self._projects


class _MockEntity:
    def __init__(self, name: str = "", status: str = "active") -> None:
        self.name = name
        self.status = status


def _make_runtime(**kwargs) -> StrategicContextRuntime:
    return StrategicContextRuntime(**kwargs)


# ── StrategicContext dataclass tests ─────────────────────────────────


class TestStrategicContext:
    def test_default_values(self) -> None:
        ctx = StrategicContext()
        assert ctx.active_projects == []
        assert ctx.health == "healthy"
        assert ctx.generated_at == 0.0

    def test_to_dict_keys(self) -> None:
        ctx = StrategicContext(generated_at=1.0)
        d = ctx.to_dict()
        expected_keys = {
            "active_projects", "active_work", "blocked_work",
            "pending_approvals", "critical_constraints",
            "strategic_priorities", "risks", "recommendations",
            "drift_warnings", "goal_summary", "goal_alignment",
            "decision_health", "memory_health",
            "capability_health", "capability_gaps",
            "health", "generated_at",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_round_trip(self) -> None:
        ctx = StrategicContext(
            active_projects=["proj-a"],
            health="degraded",
            generated_at=100.0,
        )
        d = ctx.to_dict()
        assert d["active_projects"] == ["proj-a"]
        assert d["health"] == "degraded"
        assert d["generated_at"] == 100.0


# ── StrategicHealth enum tests ───────────────────────────────────────


class TestStrategicHealth:
    def test_values(self) -> None:
        assert StrategicHealth.HEALTHY.value == "healthy"
        assert StrategicHealth.WATCH.value == "watch"
        assert StrategicHealth.DEGRADED.value == "degraded"
        assert StrategicHealth.CRITICAL.value == "critical"

    def test_from_string(self) -> None:
        assert StrategicHealth("critical") == StrategicHealth.CRITICAL


# ── Health classification tests ──────────────────────────────────────


class TestHealthClassification:
    def test_healthy_no_engines(self) -> None:
        rt = _make_runtime()
        assert rt.health() == StrategicHealth.HEALTHY

    def test_critical_from_gap_severity(self) -> None:
        gaps = [{"severity": "critical", "priority_score": 0.95}]
        rt = _make_runtime(gap_engine=_MockGapEngine(gaps=gaps))
        assert rt.health() == StrategicHealth.CRITICAL

    def test_critical_from_gap_score(self) -> None:
        gaps = [{"severity": "high", "priority_score": 0.95}]
        rt = _make_runtime(gap_engine=_MockGapEngine(gaps=gaps))
        assert rt.health() == StrategicHealth.CRITICAL

    def test_critical_from_drift(self) -> None:
        drift = [{"severity": "critical"}]
        rt = _make_runtime(tick_loop=_MockTickLoop(drift=drift))
        assert rt.health() == StrategicHealth.CRITICAL

    def test_critical_from_blocked_high(self) -> None:
        blocked = [{"priority": "high", "priority_score": 0.8}]
        rt = _make_runtime(
            runtime_awareness=_MockRuntimeAwareness(blocked=blocked),
        )
        assert rt.health() == StrategicHealth.CRITICAL

    def test_degraded_from_high_gaps(self) -> None:
        gaps = [{"severity": "high", "priority_score": 0.75}]
        rt = _make_runtime(gap_engine=_MockGapEngine(gaps=gaps))
        assert rt.health() == StrategicHealth.DEGRADED

    def test_degraded_from_alert_drift(self) -> None:
        drift = [{"severity": "alert"}]
        rt = _make_runtime(tick_loop=_MockTickLoop(drift=drift))
        assert rt.health() == StrategicHealth.DEGRADED

    def test_degraded_from_many_approvals(self) -> None:
        approvals = [{"id": f"a-{i}"} for i in range(5)]
        rt = _make_runtime(
            operator_context=_MockOperatorContext(approvals=approvals),
        )
        assert rt.health() == StrategicHealth.DEGRADED

    def test_watch_from_medium_gaps(self) -> None:
        gaps = [{"severity": "medium", "priority_score": 0.5}]
        rt = _make_runtime(gap_engine=_MockGapEngine(gaps=gaps))
        assert rt.health() == StrategicHealth.WATCH

    def test_watch_from_warning_drift(self) -> None:
        drift = [{"severity": "warning"}]
        rt = _make_runtime(tick_loop=_MockTickLoop(drift=drift))
        assert rt.health() == StrategicHealth.WATCH

    def test_healthy_with_low_gaps(self) -> None:
        gaps = [{"severity": "low", "priority_score": 0.2}]
        rt = _make_runtime(gap_engine=_MockGapEngine(gaps=gaps))
        assert rt.health() == StrategicHealth.HEALTHY


# ── Engine composition tests ─────────────────────────────────────────


class TestEngineComposition:
    def test_gap_engine_fills_priorities(self) -> None:
        gaps = [{"severity": "medium", "title": "gap-1"}]
        recs = [{"title": "rec-1", "priority_score": 0.8}]
        rt = _make_runtime(gap_engine=_MockGapEngine(gaps=gaps, recs=recs))
        ctx = rt.context()
        assert len(ctx.strategic_priorities) == 1
        assert ctx.strategic_priorities[0]["title"] == "gap-1"
        assert len(ctx.recommendations) >= 1

    def test_tick_loop_fills_drift(self) -> None:
        drift = [{"severity": "warning", "title": "stale-docs"}]
        rt = _make_runtime(tick_loop=_MockTickLoop(drift=drift))
        ctx = rt.context()
        assert len(ctx.drift_warnings) == 1
        assert ctx.drift_warnings[0]["title"] == "stale-docs"

    def test_tick_candidates_become_recommendations(self) -> None:
        candidates = [{"title": "candidate-1", "priority_score": 0.6}]
        rt = _make_runtime(tick_loop=_MockTickLoop(candidates=candidates))
        ctx = rt.context()
        tick_recs = [r for r in ctx.recommendations if r.get("source") == "tick_candidate"]
        assert len(tick_recs) == 1

    def test_projection_engine_fills_risks(self) -> None:
        risks = [{"title": "auth-risk", "severity": "high"}]
        rt = _make_runtime(projection_engine=_MockProjectionEngine(risks=risks))
        ctx = rt.context()
        assert len(ctx.risks) == 1

    def test_operator_context_fills_approvals(self) -> None:
        approvals = [{"id": "a-1"}, {"id": "a-2"}]
        rt = _make_runtime(
            operator_context=_MockOperatorContext(approvals=approvals),
        )
        ctx = rt.context()
        assert len(ctx.pending_approvals) == 2

    def test_next_action_fills_recommendations(self) -> None:
        actions = [_MockAction("deploy auth", 0.9)]
        rt = _make_runtime(
            next_action_engine=_MockNextActionEngine(actions=actions),
        )
        ctx = rt.context()
        assert any("deploy auth" in str(r) for r in ctx.recommendations)

    def test_runtime_awareness_fills_work(self) -> None:
        active = [{"packet_id": "wp-1"}]
        blocked = [{"packet_id": "wp-2", "reason": "missing dep"}]
        rt = _make_runtime(
            runtime_awareness=_MockRuntimeAwareness(active=active, blocked=blocked),
        )
        ctx = rt.context()
        assert len(ctx.active_work) == 1
        assert len(ctx.blocked_work) == 1

    def test_knowledge_fills_constraints(self) -> None:
        constraints = [_MockKnowledgeEntry("no-deploy-friday")]
        rt = _make_runtime(
            knowledge_awareness=_MockKnowledgeAwareness(constraints=constraints),
        )
        ctx = rt.context()
        assert len(ctx.critical_constraints) == 1

    def test_reality_graph_fills_projects(self) -> None:
        projects = [_MockEntity("CreatorOS", "active"), _MockEntity("OldProj", "inactive")]
        rt = _make_runtime(reality_graph=_MockRealityGraph(projects=projects))
        ctx = rt.context()
        assert "CreatorOS" in ctx.active_projects
        assert "OldProj" not in ctx.active_projects


# ── Graceful degradation tests ───────────────────────────────────────


class TestGracefulDegradation:
    def test_no_engines_returns_empty_context(self) -> None:
        rt = _make_runtime()
        ctx = rt.context()
        assert ctx.active_projects == []
        assert ctx.active_work == []
        assert ctx.risks == []
        assert ctx.health == "healthy"
        assert ctx.generated_at > 0

    def test_partial_engines(self) -> None:
        rt = _make_runtime(
            gap_engine=_MockGapEngine(gaps=[{"severity": "low"}]),
        )
        ctx = rt.context()
        assert len(ctx.strategic_priorities) == 1
        assert ctx.risks == []
        assert ctx.drift_warnings == []

    def test_engine_raises_exception(self) -> None:
        class _BrokenEngine:
            def analyze(self):
                raise RuntimeError("engine down")

        rt = _make_runtime(gap_engine=_BrokenEngine())
        ctx = rt.context()
        assert ctx.strategic_priorities == []
        assert ctx.health == "healthy"


# ── Summary and snapshot tests ───────────────────────────────────────


class TestSummaryAndSnapshot:
    def test_summary_keys(self) -> None:
        rt = _make_runtime()
        s = rt.summary()
        expected = {
            "health", "active_project_count", "active_work_count",
            "blocked_count", "approval_count", "risk_count",
            "drift_count", "recommendation_count", "generated_at",
        }
        assert set(s.keys()) == expected

    def test_summary_counts_match_context(self) -> None:
        gaps = [{"severity": "medium"}]
        risks_data = [{"severity": "low"}]
        rt = _make_runtime(
            gap_engine=_MockGapEngine(gaps=gaps),
            projection_engine=_MockProjectionEngine(risks=risks_data),
        )
        s = rt.summary()
        assert s["risk_count"] == 1

    def test_snapshot_is_full_context(self) -> None:
        rt = _make_runtime()
        snap = rt.snapshot()
        assert "health" in snap
        assert "active_projects" in snap
        assert "generated_at" in snap

    def test_generated_at_is_recent(self) -> None:
        rt = _make_runtime()
        before = time.time()
        ctx = rt.context()
        after = time.time()
        assert before <= ctx.generated_at <= after
