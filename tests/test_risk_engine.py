"""Campaign 7.2 — Risk Engine tests.

Tests unified risk register: projection risk mapping, blocker detection,
stale doc risk, constraint density, severity ranking, graceful degradation.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.risk_engine import (
    RiskCategory,
    RiskEngine,
    UnifiedRisk,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockProjectionEngine:
    def __init__(self, risks: list | None = None) -> None:
        self._risks = risks or []

    def get_projection_state(self) -> dict:
        return {"risks": self._risks}


class _MockRuntimeAwareness:
    def __init__(self, blocked: list | None = None) -> None:
        self._blocked = blocked or []

    def blocked_work(self) -> list:
        return self._blocked


class _MockDocEntry:
    def __init__(self, name: str = "") -> None:
        self.name = name


class _MockDocAwareness:
    def __init__(self, stale: list | None = None) -> None:
        self._stale = stale or []

    def find_stale_docs(self) -> list:
        return self._stale


class _MockKnowledgeEntry:
    def __init__(self, summary: str = "") -> None:
        self.summary = summary


class _MockKnowledgeAwareness:
    def __init__(self, constraints: list | None = None) -> None:
        self._constraints = constraints or []

    def find_constraints(self) -> list:
        return self._constraints


def _make_engine(**kwargs) -> RiskEngine:
    return RiskEngine(**kwargs)


# ── UnifiedRisk tests ────────────────────────────────────────────────


class TestUnifiedRisk:
    def test_default_risk_score_computed(self) -> None:
        risk = UnifiedRisk(probability=0.8, impact=0.6)
        assert risk.risk_score == pytest.approx(0.48, abs=0.01)

    def test_explicit_risk_score_preserved(self) -> None:
        risk = UnifiedRisk(probability=0.8, impact=0.6, risk_score=0.99)
        assert risk.risk_score == 0.99

    def test_to_dict_keys(self) -> None:
        risk = UnifiedRisk(title="test")
        d = risk.to_dict()
        expected = {
            "risk_id", "title", "description", "category", "severity",
            "probability", "impact", "risk_score", "source_engine",
            "entity_refs", "mitigation", "detected_at",
        }
        assert set(d.keys()) == expected

    def test_risk_id_prefix(self) -> None:
        risk = UnifiedRisk()
        assert risk.risk_id.startswith("risk-")


class TestRiskCategory:
    def test_values(self) -> None:
        assert RiskCategory.BLOCKER.value == "blocker"
        assert RiskCategory.DOCUMENTATION.value == "documentation"
        assert len(RiskCategory) == 7


# ── Projection risk mapping tests ────────────────────────────────────


class TestProjectionRisks:
    def test_maps_projection_risks(self) -> None:
        risks = [{"title": "auth-risk", "severity": "high", "probability": 0.8, "impact": 0.9}]
        engine = _make_engine(projection_engine=_MockProjectionEngine(risks=risks))
        result = engine.detect_risks()
        assert len(result) == 1
        assert result[0].source_engine == "projection_engine"
        assert result[0].severity == "high"

    def test_maps_to_dict_risks(self) -> None:
        class _RiskObj:
            def to_dict(self):
                return {"title": "obj-risk", "severity": "critical", "probability": 0.9, "impact": 0.8}
        engine = _make_engine(projection_engine=_MockProjectionEngine(risks=[_RiskObj()]))
        result = engine.detect_risks()
        assert len(result) == 1
        assert result[0].title == "obj-risk"

    def test_empty_projection_risks(self) -> None:
        engine = _make_engine(projection_engine=_MockProjectionEngine(risks=[]))
        assert engine.detect_risks() == []


# ── Blocker risk tests ───────────────────────────────────────────────


class TestBlockerRisks:
    def test_single_blocker_medium(self) -> None:
        blocked = [{"title": "blocked-1", "packet_id": "wp-1"}]
        engine = _make_engine(runtime_awareness=_MockRuntimeAwareness(blocked=blocked))
        risks = engine.detect_risks()
        assert len(risks) == 1
        assert risks[0].category == "blocker"
        assert risks[0].severity == "medium"

    def test_multiple_blockers_escalate(self) -> None:
        blocked = [{"title": f"b-{i}"} for i in range(3)]
        engine = _make_engine(runtime_awareness=_MockRuntimeAwareness(blocked=blocked))
        risks = engine.detect_risks()
        assert risks[0].severity == "critical"

    def test_no_blockers_no_risk(self) -> None:
        engine = _make_engine(runtime_awareness=_MockRuntimeAwareness(blocked=[]))
        assert engine.detect_risks() == []


# ── Stale doc risk tests ────────────────────────────────────────────


class TestStaleDocRisks:
    def test_stale_docs_create_risk(self) -> None:
        stale = [_MockDocEntry("doc-1"), _MockDocEntry("doc-2")]
        engine = _make_engine(documentation_awareness=_MockDocAwareness(stale=stale))
        risks = engine.detect_risks()
        assert len(risks) == 1
        assert risks[0].category == "documentation"
        assert risks[0].severity == "medium"

    def test_many_stale_docs_high_severity(self) -> None:
        stale = [_MockDocEntry(f"doc-{i}") for i in range(6)]
        engine = _make_engine(documentation_awareness=_MockDocAwareness(stale=stale))
        risks = engine.detect_risks()
        assert risks[0].severity == "high"

    def test_no_stale_docs_no_risk(self) -> None:
        engine = _make_engine(documentation_awareness=_MockDocAwareness(stale=[]))
        assert engine.detect_risks() == []


# ── Constraint risk tests ───────────────────────────────────────────


class TestConstraintRisks:
    def test_many_constraints_create_risk(self) -> None:
        constraints = [_MockKnowledgeEntry(f"c-{i}") for i in range(5)]
        engine = _make_engine(knowledge_awareness=_MockKnowledgeAwareness(constraints=constraints))
        risks = engine.detect_risks()
        assert len(risks) == 1
        assert risks[0].category == "execution"

    def test_few_constraints_no_risk(self) -> None:
        constraints = [_MockKnowledgeEntry("c-1")]
        engine = _make_engine(knowledge_awareness=_MockKnowledgeAwareness(constraints=constraints))
        assert engine.detect_risks() == []

    def test_ten_plus_constraints_high(self) -> None:
        constraints = [_MockKnowledgeEntry(f"c-{i}") for i in range(12)]
        engine = _make_engine(knowledge_awareness=_MockKnowledgeAwareness(constraints=constraints))
        risks = engine.detect_risks()
        assert risks[0].severity == "high"


# ── Filtering tests ─────────────────────────────────────────────────


class TestFiltering:
    def test_high_risks_filter(self) -> None:
        proj_risks = [{"title": "r1", "severity": "high", "probability": 0.8, "impact": 0.9}]
        stale = [_MockDocEntry("d1")]
        engine = _make_engine(
            projection_engine=_MockProjectionEngine(risks=proj_risks),
            documentation_awareness=_MockDocAwareness(stale=stale),
        )
        engine.detect_risks()
        high = engine.high_risks()
        assert all(r.severity in ("high", "critical") for r in high)

    def test_by_category(self) -> None:
        blocked = [{"title": "b1"}]
        stale = [_MockDocEntry("d1"), _MockDocEntry("d2")]
        engine = _make_engine(
            runtime_awareness=_MockRuntimeAwareness(blocked=blocked),
            documentation_awareness=_MockDocAwareness(stale=stale),
        )
        engine.detect_risks()
        blockers = engine.by_category("blocker")
        docs = engine.by_category("documentation")
        assert len(blockers) == 1
        assert len(docs) == 1


# ── Sorting and graceful degradation ────────────────────────────────


class TestSortingAndDegradation:
    def test_sorted_by_risk_score(self) -> None:
        proj_risks = [
            {"title": "low", "severity": "low", "probability": 0.2, "impact": 0.2},
            {"title": "high", "severity": "high", "probability": 0.9, "impact": 0.9},
        ]
        engine = _make_engine(projection_engine=_MockProjectionEngine(risks=proj_risks))
        risks = engine.detect_risks()
        scores = [r.risk_score for r in risks]
        assert scores == sorted(scores, reverse=True)

    def test_no_engines(self) -> None:
        engine = _make_engine()
        assert engine.detect_risks() == []

    def test_broken_engine(self) -> None:
        class _Broken:
            def get_projection_state(self):
                raise RuntimeError("down")
        engine = _make_engine(projection_engine=_Broken())
        assert engine.detect_risks() == []
