"""Tests for WorkPortfolioRuntime — Campaign 11.2."""

import sys
import os
import json
import tempfile

# Repo root is DERIVED from the active checkout, never hardcoded. The previous
# module-scope `sys.path.insert(...)` + `os.environ.setdefault("UMH_ROOT", ...)`
# pinned a foreign campaign worktree at IMPORT time and never restored it, so it
# leaked into every module collected afterwards and hard-aborted whole shards.
from tests.repo_root import ensure_repo_on_path

ensure_repo_on_path()

import pytest


@pytest.fixture(autouse=True)
def _isolated_runtime_state(tmp_path, monkeypatch):
    """Point runtime state at a per-test tmp dir — never the live tree.

    Most constructions here omit ``velocity_store_path``, so the runtime falls
    back to ``runtime_state_dir("work_portfolio")``, which resolves relative to
    ``UMH_ROOT``. While this module pinned ``UMH_ROOT`` to a retired campaign
    worktree, that near-empty directory ACCIDENTALLY shielded the live tree.
    Deriving the root correctly removed the shield and exposed the real defect:
    these tests were reading (and appending to) the REAL
    ``data/runtime/umh/work_portfolio/velocity.jsonl`` — 34k+ lines of live
    production state — which made ``health()`` hang and let tests mutate runtime
    data.

    ``monkeypatch.setenv`` is restored automatically, so this isolates without
    reintroducing the module-scope leak that caused the shard aborts.
    """
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))


from substrate.organism.work_portfolio_runtime import (  # noqa: E402
    WorkPortfolioHealth,
    WorkDriftType,
    WorkDriftWarning,
    WorkPortfolioSnapshot,
    WorkPortfolioRuntime,
    _VelocityTracker,
)


# ── Mock helpers ──────────────────────────────────────────────────────────


class _MockReadinessAssessment:
    def __init__(self, work_id="wp-1", status="ready", goal_ids=None):
        self.work_id = work_id
        self.status = status
        self.goal_ids = goal_ids or []

    def to_dict(self):
        return {"work_id": self.work_id, "status": self.status}


class _MockReadinessSnapshot:
    def __init__(self, total=0, by_status=None, ready_work=None, blocked_work=None):
        self.total = total
        self.by_status = by_status or {}
        self.ready_work = ready_work or []
        self.blocked_work = blocked_work or []


class _MockReadinessRuntime:
    def __init__(self, snapshot=None, assessments=None):
        self._snapshot = snapshot or _MockReadinessSnapshot()
        self._assessments = assessments or []

    def snapshot(self):
        return self._snapshot

    def assess_all(self):
        return self._assessments

    def work_for_goal(self, goal_id):
        return [a for a in self._assessments if goal_id in a.goal_ids]


class _MockDelegationSnapshot:
    def __init__(
        self, total_assessed=0, delegatable=0, not_delegatable=0, top_missing_capabilities=None
    ):
        self.total_assessed = total_assessed
        self.delegatable = delegatable
        self.not_delegatable = not_delegatable
        self.top_missing_capabilities = top_missing_capabilities or []


class _MockDelegationRuntime:
    def __init__(self, snapshot=None):
        self._snapshot = snapshot or _MockDelegationSnapshot()

    def snapshot(self):
        return self._snapshot


class _MockWGSnapshot:
    def __init__(self, completed=0):
        self.completed = completed


class _MockWorkGraph:
    def __init__(self, snap=None):
        self._snap = snap or _MockWGSnapshot()

    def snapshot(self):
        return self._snap


class _MockOutcome:
    def __init__(self, at_risk=None):
        self._at_risk = at_risk or []

    def goals_at_risk(self):
        return self._at_risk


class _MockGoalAtRisk:
    def __init__(self, goal_id="g-1"):
        self.goal_id = goal_id


class _MockCapPortfolio:
    def __init__(self, health_val="healthy"):
        self._health = health_val

    def health(self):
        return self._health


class _MockDriftWarning:
    def __init__(self, drift_type="context_drift", severity=0.6, description="test drift"):
        self.drift_type = drift_type
        self.severity = severity
        self.description = description


class _MockDriftEngine:
    def __init__(self, warnings=None):
        self._warnings = warnings or []

    def detect_drift(self):
        return self._warnings


class _MockGoalDriftEngine:
    def __init__(self, warnings=None):
        self._warnings = warnings or []

    def detect(self):
        return self._warnings


# ── WorkPortfolioHealth Tests ─────────────────────────────────────────────


class TestWorkPortfolioHealth:
    def test_values(self):
        assert WorkPortfolioHealth.THRIVING.value == "thriving"
        assert WorkPortfolioHealth.HEALTHY.value == "healthy"
        assert WorkPortfolioHealth.CONSTRAINED.value == "constrained"
        assert WorkPortfolioHealth.STALLED.value == "stalled"

    def test_is_str_enum(self):
        assert isinstance(WorkPortfolioHealth.THRIVING, str)

    def test_all_values(self):
        assert len(WorkPortfolioHealth) == 4


# ── WorkDriftType Tests ───────────────────────────────────────────────────


class TestWorkDriftType:
    def test_values(self):
        assert WorkDriftType.READINESS_DRIFT.value == "readiness_drift"
        assert WorkDriftType.DELEGATION_DRIFT.value == "delegation_drift"
        assert WorkDriftType.EXECUTION_DRIFT.value == "execution_drift"
        assert WorkDriftType.OUTCOME_DRIFT.value == "outcome_drift"

    def test_is_str_enum(self):
        assert isinstance(WorkDriftType.READINESS_DRIFT, str)

    def test_all_values(self):
        assert len(WorkDriftType) == 4


# ── WorkDriftWarning Tests ────────────────────────────────────────────────


class TestWorkDriftWarning:
    def test_defaults(self):
        w = WorkDriftWarning()
        assert w.drift_type == ""
        assert w.severity == 0.0

    def test_to_dict(self):
        w = WorkDriftWarning(
            drift_type="readiness_drift",
            severity=0.7,
            description="block rate increasing",
            evidence={"block_rate_change": 0.15},
            work_ids=["wp-1"],
        )
        d = w.to_dict()
        assert d["drift_type"] == "readiness_drift"
        assert d["severity"] == 0.7
        assert "wp-1" in d["work_ids"]

    def test_from_dict(self):
        d = {
            "drift_type": "execution_drift",
            "severity": 0.8,
            "description": "zero velocity",
        }
        w = WorkDriftWarning.from_dict(d)
        assert w.drift_type == "execution_drift"
        assert w.severity == 0.8

    def test_roundtrip(self):
        w = WorkDriftWarning(
            drift_type="outcome_drift",
            severity=0.5,
            description="goals at risk",
            work_ids=["wp-2", "wp-3"],
        )
        d = w.to_dict()
        w2 = WorkDriftWarning.from_dict(d)
        assert w2.drift_type == w.drift_type
        assert w2.severity == w.severity
        assert w2.work_ids == w.work_ids


# ── WorkPortfolioSnapshot Tests ───────────────────────────────────────────


class TestWorkPortfolioSnapshot:
    def test_defaults(self):
        snap = WorkPortfolioSnapshot()
        assert snap.total_work == 0
        assert snap.health == WorkPortfolioHealth.STALLED

    def test_to_dict(self):
        snap = WorkPortfolioSnapshot(
            total_work=10,
            ready=6,
            blocked=2,
            delegatable=5,
            health=WorkPortfolioHealth.HEALTHY,
            drift_warnings=[
                WorkDriftWarning(drift_type="test", severity=0.5),
            ],
        )
        d = snap.to_dict()
        assert d["total_work"] == 10
        assert d["health"] == "healthy"
        assert d["drift_warning_count"] == 1
        assert len(d["drift_warnings"]) == 1


# ── VelocityTracker Tests ────────────────────────────────────────────────


class TestVelocityTracker:
    @pytest.fixture
    def tracker(self, tmp_path):
        store_path = str(tmp_path / "velocity.jsonl")
        return _VelocityTracker(store_path=store_path)

    def test_empty_velocity(self, tracker):
        assert tracker.completions_per_day() == 0.0

    def test_record_and_load(self, tracker):
        tracker.record_snapshot(completed=5, blocked=2, total=10)
        events = tracker._load()
        assert len(events) == 1
        assert events[0]["completed"] == 5

    def test_completions_per_day(self, tmp_path):
        import time

        store_path = str(tmp_path / "velocity.jsonl")
        now = time.time()
        events = [
            {"ts": now - 86400 * 3, "completed": 0, "blocked": 2, "total": 10},
            {"ts": now - 86400 * 1, "completed": 4, "blocked": 1, "total": 10},
            {"ts": now, "completed": 8, "blocked": 0, "total": 10},
        ]
        with open(store_path, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
        tracker = _VelocityTracker(store_path=store_path)
        cpd = tracker.completions_per_day(window_days=7)
        assert cpd > 0

    def test_block_rate_change(self, tmp_path):
        import time

        store_path = str(tmp_path / "velocity.jsonl")
        now = time.time()
        events = [
            {"ts": now - 86400 * 2, "completed": 0, "blocked": 1, "total": 10},
            {"ts": now, "completed": 2, "blocked": 5, "total": 10},
        ]
        with open(store_path, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
        tracker = _VelocityTracker(store_path=store_path)
        change = tracker.block_rate_change(window_days=7)
        assert change > 0

    def test_single_event_no_velocity(self, tracker):
        tracker.record_snapshot(completed=5, blocked=0, total=10)
        assert tracker.completions_per_day() == 0.0

    def test_block_rate_decrease(self, tmp_path):
        import time

        store_path = str(tmp_path / "velocity.jsonl")
        now = time.time()
        events = [
            {"ts": now - 86400 * 2, "completed": 0, "blocked": 8, "total": 10},
            {"ts": now, "completed": 5, "blocked": 1, "total": 10},
        ]
        with open(store_path, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
        tracker = _VelocityTracker(store_path=store_path)
        change = tracker.block_rate_change(window_days=7)
        assert change < 0


# ── WorkPortfolioRuntime Tests ────────────────────────────────────────────


class TestWorkPortfolioRuntime:
    @pytest.fixture
    def runtime(self, tmp_path):
        return WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(
                snapshot=_MockReadinessSnapshot(
                    total=10,
                    by_status={"ready": 6, "blocked": 2, "waiting_approval": 2},
                    ready_work=[_MockReadinessAssessment(f"wp-{i}") for i in range(6)],
                    blocked_work=[
                        _MockReadinessAssessment(f"wp-b-{i}", "blocked") for i in range(4)
                    ],
                ),
            ),
            delegation_readiness=_MockDelegationRuntime(
                snapshot=_MockDelegationSnapshot(
                    total_assessed=10,
                    delegatable=7,
                    not_delegatable=3,
                ),
            ),
            work_graph=_MockWorkGraph(_MockWGSnapshot(completed=5)),
            outcome_tracking=_MockOutcome(),
            capability_portfolio=_MockCapPortfolio("healthy"),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )

    def test_snapshot(self, runtime):
        snap = runtime.snapshot()
        assert snap.total_work == 10
        assert snap.ready == 6
        assert snap.delegatable == 7
        assert snap.capability_health == "healthy"

    def test_health_classification_thriving(self, tmp_path):
        import time

        vel_path = str(tmp_path / "velocity.jsonl")
        now = time.time()
        with open(vel_path, "w") as f:
            f.write(
                json.dumps({"ts": now - 86400, "completed": 0, "blocked": 0, "total": 10}) + "\n"
            )
            f.write(json.dumps({"ts": now, "completed": 5, "blocked": 0, "total": 10}) + "\n")
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(
                snapshot=_MockReadinessSnapshot(
                    total=10,
                    ready_work=[_MockReadinessAssessment(f"wp-{i}") for i in range(8)],
                    blocked_work=[
                        _MockReadinessAssessment(f"wp-b-{i}", "blocked") for i in range(2)
                    ],
                ),
            ),
            delegation_readiness=_MockDelegationRuntime(),
            work_graph=_MockWorkGraph(_MockWGSnapshot(completed=5)),
            velocity_store_path=vel_path,
        )
        h = rt.health()
        assert h in (WorkPortfolioHealth.THRIVING, WorkPortfolioHealth.HEALTHY)

    def test_health_classification_stalled(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(
                snapshot=_MockReadinessSnapshot(
                    total=10,
                    ready_work=[],
                    blocked_work=[
                        _MockReadinessAssessment(f"wp-{i}", "blocked") for i in range(10)
                    ],
                ),
            ),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        h = rt.health()
        assert h == WorkPortfolioHealth.STALLED

    def test_velocity_dict(self, runtime):
        vel = runtime.velocity()
        assert "completions_per_day" in vel
        assert "block_rate_change_7d" in vel

    def test_detect_drift_empty(self, runtime):
        warnings = runtime.detect_drift()
        assert isinstance(warnings, list)

    def test_delegation_drift(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(),
            delegation_readiness=_MockDelegationRuntime(
                snapshot=_MockDelegationSnapshot(
                    total_assessed=10,
                    delegatable=3,
                    not_delegatable=7,
                ),
            ),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        warnings = rt.detect_drift()
        delegation_warnings = [w for w in warnings if w.drift_type == "delegation_drift"]
        assert len(delegation_warnings) == 1
        assert delegation_warnings[0].severity == 0.7

    def test_outcome_drift(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(),
            outcome_tracking=_MockOutcome(
                at_risk=[_MockGoalAtRisk("g-1"), _MockGoalAtRisk("g-2")],
            ),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        warnings = rt.detect_drift()
        outcome_warnings = [w for w in warnings if w.drift_type == "outcome_drift"]
        assert len(outcome_warnings) == 1
        assert "2 goals at risk" in outcome_warnings[0].description

    def test_upstream_drift_collected(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(),
            drift_detection=_MockDriftEngine(
                warnings=[_MockDriftWarning("context_drift", 0.7, "upstream drift")],
            ),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        warnings = rt.detect_drift()
        upstream = [w for w in warnings if "upstream:" in w.drift_type]
        assert len(upstream) == 1

    def test_goal_drift_collected(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(),
            goal_drift=_MockGoalDriftEngine(
                warnings=[_MockDriftWarning("goal_stale", 0.6, "goal stale")],
            ),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        warnings = rt.detect_drift()
        goal = [w for w in warnings if "goal:" in w.drift_type]
        assert len(goal) == 1

    def test_drift_by_type(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(),
            outcome_tracking=_MockOutcome(
                at_risk=[_MockGoalAtRisk("g-1")],
            ),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        outcome_only = rt.drift_by_type("outcome_drift")
        assert len(outcome_only) >= 1
        assert all(w.drift_type == "outcome_drift" for w in outcome_only)

    def test_at_risk_work(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(
                assessments=[
                    _MockReadinessAssessment("wp-1", "ready", ["g-1"]),
                    _MockReadinessAssessment("wp-2", "blocked", ["g-2"]),
                ],
            ),
            outcome_tracking=_MockOutcome(
                at_risk=[_MockGoalAtRisk("g-1")],
            ),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        at_risk = rt.at_risk_work()
        assert len(at_risk) == 1
        assert at_risk[0].work_id == "wp-1"

    def test_summary(self, runtime):
        s = runtime.summary()
        assert "total_work" in s
        assert "health" in s
        assert "drift_warning_count" in s
        assert "goals_at_risk_count" in s
        assert "capability_health" in s

    def test_snapshot_to_dict(self, runtime):
        snap = runtime.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "total_work" in d
        assert "health" in d
        assert "drift_warnings" in d

    def test_graceful_degradation_no_subsystems(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(),
            delegation_readiness=_MockDelegationRuntime(),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        snap = rt.snapshot()
        assert snap.total_work == 0
        assert snap.health == WorkPortfolioHealth.STALLED

    def test_health_constrained(self, tmp_path):
        rt = WorkPortfolioRuntime(
            work_readiness=_MockReadinessRuntime(
                snapshot=_MockReadinessSnapshot(
                    total=10,
                    ready_work=[_MockReadinessAssessment(f"wp-{i}") for i in range(3)],
                    blocked_work=[
                        _MockReadinessAssessment(f"wp-b-{i}", "blocked") for i in range(4)
                    ],
                ),
            ),
            velocity_store_path=str(tmp_path / "velocity.jsonl"),
        )
        snap = rt.snapshot()
        assert snap.health in (WorkPortfolioHealth.CONSTRAINED, WorkPortfolioHealth.STALLED)

    def test_classify_health_direct(self, runtime):
        assert runtime._classify_health(0, 0, 0, 0.0) == WorkPortfolioHealth.STALLED
        assert runtime._classify_health(10, 8, 0, 1.0) == WorkPortfolioHealth.THRIVING
        assert runtime._classify_health(10, 6, 1, 0.5) == WorkPortfolioHealth.HEALTHY
        assert runtime._classify_health(10, 2, 6, 0.5) == WorkPortfolioHealth.STALLED
        assert runtime._classify_health(10, 3, 3, 0.5) == WorkPortfolioHealth.CONSTRAINED
