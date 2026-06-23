"""C26D — Correspondence Ledger tests.

Tests CorrespondenceResult, CorrespondenceChecker, CorrespondenceScheduler,
regression detection, ring buffer, and journal entry types.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from datetime import datetime, timezone
from dataclasses import dataclass

from substrate.organism.production_truth_delta import (
    CorrespondenceChecker,
    CorrespondenceResult,
    CorrespondenceStatus,
)
from substrate.organism.correspondence_scheduler import (
    CorrespondenceScheduler,
    RegressionAlert,
)
from substrate.organism.execution_journal import JournalPhase


# ── Mock certification types ─────────────────────────────────────────────

@dataclass
class MockCertification:
    current_level: int = 5
    failure_level: int | None = None
    failure_detail: str = ""
    is_fully_certified: bool = True


class MockCertificationEngine:
    def __init__(self, results: dict[str, MockCertification] | None = None):
        self._results = results or {}

    def certify(self, projection_name: str) -> MockCertification:
        if projection_name in self._results:
            return self._results[projection_name]
        raise ValueError(f"Unknown projection: {projection_name}")


class MockRegistry:
    def __init__(self, names: list[str] | None = None):
        self._configs = {n: {} for n in (names or [])}

    def list_projections(self) -> list[str]:
        return list(self._configs.keys())


# ── CorrespondenceResult tests ───────────────────────────────────────────


class TestCorrespondenceResult:
    def test_creation_defaults(self):
        r = CorrespondenceResult()
        assert r.correspondence == CorrespondenceStatus.UNKNOWN
        assert r.projection_name == ""
        assert r.divergences == []
        assert r.certification_before is None
        assert r.certification_after is None

    def test_to_dict_contains_all_fields(self):
        r = CorrespondenceResult(
            projection_name="eos",
            claimed_state="L5",
            observed_state="L2",
            correspondence=CorrespondenceStatus.DIVERGED,
            divergences=["Regression: L5 → L2"],
            certification_before=5,
            certification_after=2,
        )
        d = r.to_dict()
        assert d["projection_name"] == "eos"
        assert d["correspondence"] == "diverged"
        assert d["is_regression"] is True
        assert d["is_critical"] is True
        assert "checked_at" in d

    def test_is_regression_true(self):
        r = CorrespondenceResult(
            certification_before=5, certification_after=2
        )
        assert r.is_regression is True

    def test_is_regression_false_same_level(self):
        r = CorrespondenceResult(
            certification_before=5, certification_after=5
        )
        assert r.is_regression is False

    def test_is_regression_false_improvement(self):
        r = CorrespondenceResult(
            certification_before=2, certification_after=5
        )
        assert r.is_regression is False

    def test_is_regression_false_when_none(self):
        r = CorrespondenceResult(
            certification_before=None, certification_after=5
        )
        assert r.is_regression is False

    def test_is_critical_on_diverged(self):
        r = CorrespondenceResult(
            correspondence=CorrespondenceStatus.DIVERGED
        )
        assert r.is_critical is True

    def test_not_critical_on_match(self):
        r = CorrespondenceResult(
            correspondence=CorrespondenceStatus.MATCH,
            certification_before=5,
            certification_after=5,
        )
        assert r.is_critical is False


# ── CorrespondenceChecker tests ──────────────────────────────────────────


class TestCorrespondenceChecker:
    def test_match_same_level(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(current_level=5)
        })
        result = CorrespondenceChecker.check("eos", engine, last_known_level=5)
        assert result.correspondence == CorrespondenceStatus.MATCH
        assert result.certification_after == 5
        assert result.is_regression is False

    def test_match_improvement(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(current_level=5)
        })
        result = CorrespondenceChecker.check("eos", engine, last_known_level=2)
        assert result.correspondence == CorrespondenceStatus.MATCH
        assert len(result.divergences) == 1
        assert "Improved" in result.divergences[0]

    def test_diverged_regression(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(
                current_level=2,
                failure_detail="Bundle missing pk_test",
            )
        })
        result = CorrespondenceChecker.check("eos", engine, last_known_level=5)
        assert result.correspondence == CorrespondenceStatus.DIVERGED
        assert result.is_regression is True
        assert result.certification_before == 5
        assert result.certification_after == 2
        assert any("Regression" in d for d in result.divergences)
        assert any("Bundle" in d for d in result.divergences)

    def test_unknown_on_engine_error(self):
        engine = MockCertificationEngine({})  # "eos" not registered
        result = CorrespondenceChecker.check("eos", engine, last_known_level=5)
        assert result.correspondence == CorrespondenceStatus.UNKNOWN
        assert "error" in result.observed_state

    def test_no_prior_level(self):
        engine = MockCertificationEngine({
            "cos": MockCertification(current_level=3)
        })
        result = CorrespondenceChecker.check("cos", engine, last_known_level=None)
        assert result.correspondence == CorrespondenceStatus.MATCH
        assert result.claimed_state == "no prior"
        assert result.certification_after == 3


# ── CorrespondenceScheduler tests ────────────────────────────────────────


class TestCorrespondenceScheduler:
    def test_check_all_returns_results(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(current_level=5),
            "cos": MockCertification(current_level=3),
        })
        registry = MockRegistry(["eos", "cos"])
        scheduler = CorrespondenceScheduler(
            certification_engine=engine,
            projection_registry=registry,
        )
        results = scheduler.check_all()
        assert len(results) == 2
        names = {r.projection_name for r in results}
        assert names == {"eos", "cos"}

    def test_check_all_empty_without_engine(self):
        scheduler = CorrespondenceScheduler()
        results = scheduler.check_all()
        assert results == []

    def test_regression_detected(self):
        engine_pass = MockCertificationEngine({
            "eos": MockCertification(current_level=5),
        })
        registry = MockRegistry(["eos"])
        scheduler = CorrespondenceScheduler(
            certification_engine=engine_pass,
            projection_registry=registry,
        )
        scheduler.check_all()

        # Now switch to a failing engine
        engine_fail = MockCertificationEngine({
            "eos": MockCertification(current_level=2),
        })
        scheduler._engine = engine_fail
        scheduler.check_all()

        alerts = scheduler.alerts
        assert len(alerts) == 1
        assert alerts[0].projection_name == "eos"
        assert alerts[0].level_before == 5
        assert alerts[0].level_after == 2

    def test_no_regression_on_stable(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(current_level=5),
        })
        registry = MockRegistry(["eos"])
        scheduler = CorrespondenceScheduler(
            certification_engine=engine,
            projection_registry=registry,
        )
        scheduler.check_all()
        scheduler.check_all()
        assert scheduler.alerts == []

    def test_ring_buffer_max_size(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(current_level=5),
        })
        registry = MockRegistry(["eos"])
        scheduler = CorrespondenceScheduler(
            certification_engine=engine,
            projection_registry=registry,
            max_history=5,
        )
        for _ in range(10):
            scheduler.check_all()
        history = scheduler.get_history("eos")
        assert len(history) == 5

    def test_get_latest(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(current_level=5),
        })
        registry = MockRegistry(["eos"])
        scheduler = CorrespondenceScheduler(
            certification_engine=engine,
            projection_registry=registry,
        )
        assert scheduler.get_latest("eos") is None
        scheduler.check_all()
        latest = scheduler.get_latest("eos")
        assert latest is not None
        assert latest.certification_after == 5

    def test_summary(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(current_level=5),
        })
        registry = MockRegistry(["eos"])
        scheduler = CorrespondenceScheduler(
            certification_engine=engine,
            projection_registry=registry,
        )
        scheduler.check_all()
        s = scheduler.summary()
        assert "eos" in s["projections"]
        assert s["projections"]["eos"]["certification_level"] == 5
        assert s["total_regressions"] == 0

    def test_is_due_initially(self):
        scheduler = CorrespondenceScheduler(interval_seconds=3600)
        assert scheduler.is_due() is True

    def test_is_due_false_after_check(self):
        engine = MockCertificationEngine({
            "eos": MockCertification(current_level=5),
        })
        registry = MockRegistry(["eos"])
        scheduler = CorrespondenceScheduler(
            certification_engine=engine,
            projection_registry=registry,
            interval_seconds=3600,
        )
        scheduler.check_all()
        assert scheduler.is_due() is False


# ── Journal entry types ──────────────────────────────────────────────────


class TestJournalEntryTypes:
    def test_verification_completed_exists(self):
        assert JournalPhase.VERIFICATION_COMPLETED.value == "verification_completed"

    def test_correspondence_checked_exists(self):
        assert JournalPhase.CORRESPONDENCE_CHECKED.value == "correspondence_checked"


# ── RegressionAlert tests ────────────────────────────────────────────────


class TestRegressionAlert:
    def test_to_dict(self):
        alert = RegressionAlert(
            projection_name="eos",
            level_before=5,
            level_after=2,
            detail="eos: L5 → L2",
        )
        d = alert.to_dict()
        assert d["projection_name"] == "eos"
        assert d["severity"] == "critical"
        assert "detected_at" in d


# ── Canonical type registration ──────────────────────────────────────────


class TestCanonicalTypes:
    def test_c26d_types_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES
        expected = [
            "CorrespondenceStatus",
            "CorrespondenceResult",
            "CorrespondenceChecker",
            "RegressionAlert",
            "CorrespondenceScheduler",
        ]
        for name in expected:
            assert name in CANONICAL_TYPES, (
                f"{name} not registered in canonical_types.py"
            )
