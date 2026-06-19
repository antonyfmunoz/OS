"""Tests for Organism State Runtime — Campaign 16.1."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import MagicMock

from substrate.organism.organism_state_runtime import (
    OrganismMode,
    OrganismStateRuntime,
    OrganismStateSnapshot,
)


# ── Enum Tests ───────────────────────────────────────────────────────


class TestOrganismModeEnum:
    def test_values(self) -> None:
        assert OrganismMode.IDLE.value == "idle"
        assert OrganismMode.EXECUTING.value == "executing"
        assert OrganismMode.GOVERNING.value == "governing"
        assert OrganismMode.LEARNING.value == "learning"
        assert OrganismMode.DEGRADED.value == "degraded"

    def test_count(self) -> None:
        assert len(OrganismMode) == 5


# ── Dataclass Tests ──────────────────────────────────────────────────


class TestOrganismStateSnapshot:
    def test_defaults(self) -> None:
        s = OrganismStateSnapshot()
        assert s.mode == "idle"
        assert s.health == "unknown"
        assert s.coherence_score == 0.0
        assert s.execution_state == "idle"
        assert s.active_concerns == 0
        assert s.subsystem_count == 8
        assert s.healthy_subsystems == 0
        assert s.drift_count == 0
        assert s.attention_items == []
        assert s.generated_at > 0

    def test_to_dict(self) -> None:
        s = OrganismStateSnapshot(mode="executing", health="coherent", coherence_score=0.9)
        d = s.to_dict()
        assert d["mode"] == "executing"
        assert d["health"] == "coherent"
        assert d["coherence_score"] == 0.9
        assert "attention_items" in d
        assert "generated_at" in d


# ── Fake subsystems ──────────────────────────────────────────────────


class _FakePortfolio:
    def __init__(self, health: str = "coherent", coherence: float = 0.9, drift: int = 0) -> None:
        self._health = health
        self._coherence = coherence
        self._drift = drift

    def health(self) -> MagicMock:
        m = MagicMock()
        m.value = self._health
        return m

    def coherence_score(self) -> float:
        return self._coherence

    def subsystem_health(self) -> list:
        return [
            type("E", (), {"health": self._health, "subsystem": f"sub-{i}"})()
            for i in range(8)
        ]

    def drift_warnings(self) -> list:
        return [{"severity": "medium"}] * self._drift


class _FakeExecution:
    def __init__(self, state: str = "idle") -> None:
        self._state = state

    def state(self) -> MagicMock:
        m = MagicMock()
        m.value = self._state
        return m


class _FakeBrief:
    def __init__(self, lessons: int = 0) -> None:
        self._lessons = lessons

    def generate(self) -> MagicMock:
        m = MagicMock()
        m.risks = ["risk-1"] if self._lessons > 0 else []
        m.blockers = []
        m.drift_warnings = []
        m.recent_lessons = [f"lesson-{i}" for i in range(self._lessons)]
        return m


# ── Runtime — No Dependencies ────────────────────────────────────────


class TestOrganismStateMinimalDeps:
    """Test with minimal fakes to avoid cascading lazy-load hangs on VPS."""

    @classmethod
    def setup_class(cls) -> None:
        cls.rt = OrganismStateRuntime(
            organism_portfolio=_FakePortfolio("coherent", 0.9),
            governed_execution=_FakeExecution("idle"),
            executive_brief=_FakeBrief(lessons=0),
        )

    def test_mode_returns_valid_enum(self) -> None:
        m = self.rt.mode()
        assert isinstance(m, OrganismMode)

    def test_health_returns_string(self) -> None:
        h = self.rt.health()
        assert isinstance(h, str)

    def test_is_degraded_returns_bool(self) -> None:
        assert isinstance(self.rt.is_degraded(), bool)

    def test_snapshot_returns_snapshot(self) -> None:
        snap = self.rt.snapshot()
        assert isinstance(snap, OrganismStateSnapshot)
        d = snap.to_dict()
        assert "mode" in d
        assert "health" in d

    def test_summary_has_keys(self) -> None:
        s = self.rt.summary()
        assert "mode" in s
        assert "health" in s
        assert "coherence_score" in s
        assert "execution_state" in s
        assert "is_degraded" in s


# ── Runtime — Mode Classification ────────────────────────────────────


class TestOrganismModeClassification:
    def test_degraded_critical_subsystem(self) -> None:
        portfolio = _FakePortfolio(health="critical", coherence=0.1)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("idle"),
        )
        assert rt.mode() == OrganismMode.DEGRADED

    def test_degraded_low_coherence(self) -> None:
        portfolio = _FakePortfolio(health="aligned", coherence=0.2)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("idle"),
        )
        assert rt.mode() == OrganismMode.DEGRADED

    def test_executing_mode(self) -> None:
        portfolio = _FakePortfolio(health="coherent", coherence=0.9)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("executing"),
        )
        assert rt.mode() == OrganismMode.EXECUTING

    def test_governing_mode(self) -> None:
        portfolio = _FakePortfolio(health="coherent", coherence=0.9)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("governed"),
        )
        assert rt.mode() == OrganismMode.GOVERNING

    def test_learning_mode(self) -> None:
        portfolio = _FakePortfolio(health="coherent", coherence=0.9)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("idle"),
            executive_brief=_FakeBrief(lessons=3),
        )
        assert rt.mode() == OrganismMode.LEARNING

    def test_idle_mode(self) -> None:
        portfolio = _FakePortfolio(health="coherent", coherence=0.9)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("idle"),
            executive_brief=_FakeBrief(lessons=0),
        )
        assert rt.mode() == OrganismMode.IDLE


class TestOrganismStateSnapshot:
    def test_snapshot_with_fakes(self) -> None:
        portfolio = _FakePortfolio(health="aligned", coherence=0.75, drift=2)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("executing"),
            executive_brief=_FakeBrief(lessons=1),
        )
        snap = rt.snapshot()
        d = snap.to_dict()
        assert d["mode"] == "executing"
        assert d["health"] == "aligned"
        assert d["coherence_score"] == 0.75
        assert d["drift_count"] == 2
        assert d["execution_state"] == "executing"

    def test_is_degraded_true(self) -> None:
        portfolio = _FakePortfolio(health="critical", coherence=0.1)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("idle"),
        )
        assert rt.is_degraded() is True

    def test_is_degraded_false(self) -> None:
        portfolio = _FakePortfolio(health="coherent", coherence=0.9)
        rt = OrganismStateRuntime(
            organism_portfolio=portfolio,
            governed_execution=_FakeExecution("idle"),
            executive_brief=_FakeBrief(lessons=0),
        )
        assert rt.is_degraded() is False


# ── Canonical Type Registration ──────────────────────────────────────


class TestCanonicalTypes:
    def test_organism_state_runtime_importable(self) -> None:
        from substrate.organism.organism_state_runtime import OrganismStateRuntime
        rt = OrganismStateRuntime()
        assert rt is not None
