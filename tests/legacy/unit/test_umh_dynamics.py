"""Tests for umh.feedback.dynamics — delayed/nonlinear feedback modeling."""

from __future__ import annotations

import ast
import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.feedback.dynamics import (
    DelayedScore,
    FeedbackDynamics,
    content_dynamics,
    habit_dynamics,
    outreach_dynamics,
)


# ── Import boundary ─────────────────────────────────────────────


class TestImportBoundary:
    def test_no_forbidden_imports(self):
        with open("umh/feedback/dynamics.py") as f:
            tree = ast.parse(f.read())
        forbidden = {"eos", "core", "services", "scripts"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in forbidden, f"import {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in forbidden, f"from {node.module}"


# ── DelayedScore ─────────────────────────────────────────────────


class TestDelayedScore:
    def test_pending_is_inverse_of_matured(self):
        s = DelayedScore(
            immediate=0.5, projected=0.6, matured=False,
            elapsed_steps=1, lag_steps=3, confidence=0.5,
        )
        assert s.pending is True

        s2 = DelayedScore(
            immediate=0.5, projected=0.5, matured=True,
            elapsed_steps=3, lag_steps=3, confidence=0.95,
        )
        assert s2.pending is False

    def test_to_dict(self):
        s = DelayedScore(
            immediate=0.5, projected=0.6, matured=False,
            elapsed_steps=1, lag_steps=3, confidence=0.7,
            dynamics_applied={"compounding": True},
        )
        d = s.to_dict()
        assert d["immediate"] == 0.5
        assert d["projected"] == 0.6
        assert d["pending"] is True
        assert d["dynamics_applied"]["compounding"] is True


# ── FeedbackDynamics core ────────────────────────────────────────


class TestFeedbackDynamics:
    def test_no_lag_returns_immediate(self):
        dyn = FeedbackDynamics(lag_steps=0)
        result = dyn.project_score(0.7, elapsed_steps=0)
        assert result.matured is True
        assert result.projected == pytest.approx(0.7, abs=0.01)

    def test_within_lag_projects_forward(self):
        dyn = FeedbackDynamics(lag_steps=5, compounding_factor=1.1)
        result = dyn.project_score(0.4, elapsed_steps=1)
        assert result.matured is False
        assert result.projected > 0.4

    def test_matured_at_lag(self):
        dyn = FeedbackDynamics(lag_steps=3)
        result = dyn.project_score(0.5, elapsed_steps=3)
        assert result.matured is True

    def test_should_wait(self):
        dyn = FeedbackDynamics(lag_steps=3)
        assert dyn.should_wait(0) is True
        assert dyn.should_wait(2) is True
        assert dyn.should_wait(3) is False
        assert dyn.should_wait(5) is False

    def test_projected_clamped_to_unit(self):
        dyn = FeedbackDynamics(lag_steps=10, compounding_factor=2.0)
        result = dyn.project_score(0.5, elapsed_steps=0)
        assert 0.0 <= result.projected <= 1.0

    def test_to_dict(self):
        dyn = FeedbackDynamics(lag_steps=3, decay_rate=0.1)
        d = dyn.to_dict()
        assert d["lag_steps"] == 3
        assert d["decay_rate"] == 0.1


# ── Individual effects ───────────────────────────────────────────


class TestCompounding:
    def test_compounding_increases(self):
        dyn = FeedbackDynamics(compounding_factor=1.1)
        assert dyn.apply_compounding(0.5, 3) > 0.5

    def test_compounding_clamped(self):
        dyn = FeedbackDynamics(compounding_factor=2.0)
        assert dyn.apply_compounding(0.8, 10) == 1.0

    def test_no_compounding_at_one(self):
        dyn = FeedbackDynamics(compounding_factor=1.0)
        assert dyn.apply_compounding(0.5, 5) == pytest.approx(0.5)


class TestDecay:
    def test_decay_decreases(self):
        dyn = FeedbackDynamics(decay_rate=0.1)
        assert dyn.apply_decay(1.0, 5) < 1.0

    def test_no_decay_at_zero(self):
        dyn = FeedbackDynamics(decay_rate=0.0)
        assert dyn.apply_decay(0.8, 10) == pytest.approx(0.8)

    def test_decay_never_negative(self):
        dyn = FeedbackDynamics(decay_rate=0.5)
        assert dyn.apply_decay(0.1, 100) >= 0.0


class TestSaturation:
    def test_below_threshold_unchanged(self):
        dyn = FeedbackDynamics(saturation_threshold=0.8)
        assert dyn.apply_saturation(0.5) == 0.5

    def test_above_threshold_dampened(self):
        dyn = FeedbackDynamics(saturation_threshold=0.8)
        result = dyn.apply_saturation(1.5)
        assert result > 0.8
        assert result < 1.5


# ── Trend extrapolation ──────────────────────────────────────────


class TestTrend:
    def test_ascending_trajectory_increases_projection(self):
        dyn = FeedbackDynamics(lag_steps=5)
        ascending = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = dyn.project_score(0.5, elapsed_steps=1, historical_trajectory=ascending)
        assert result.projected > 0.5

    def test_flat_trajectory_no_trend(self):
        dyn = FeedbackDynamics(lag_steps=5)
        flat = [0.5, 0.5, 0.5, 0.5, 0.5]
        result = dyn.project_score(0.5, elapsed_steps=1, historical_trajectory=flat)
        assert result.projected == pytest.approx(0.5, abs=0.01)


# ── Confidence ───────────────────────────────────────────────────


class TestConfidence:
    def test_matured_high_confidence(self):
        dyn = FeedbackDynamics(lag_steps=3)
        result = dyn.project_score(0.5, elapsed_steps=3)
        assert result.confidence == 0.95

    def test_unmatured_lower_confidence(self):
        dyn = FeedbackDynamics(lag_steps=10)
        result = dyn.project_score(0.5, elapsed_steps=0)
        assert result.confidence < 0.95

    def test_high_volatility_reduces_confidence(self):
        low_vol = FeedbackDynamics(lag_steps=5, volatility=0.0)
        high_vol = FeedbackDynamics(lag_steps=5, volatility=1.0)
        r_low = low_vol.project_score(0.5, elapsed_steps=1)
        r_high = high_vol.project_score(0.5, elapsed_steps=1)
        assert r_low.confidence > r_high.confidence


# ── Pre-built profiles ───────────────────────────────────────────


class TestProfiles:
    def test_outreach_dynamics(self):
        dyn = outreach_dynamics()
        assert dyn.lag_steps == 3
        assert dyn.compounding_factor == 1.0

    def test_content_dynamics(self):
        dyn = content_dynamics()
        assert dyn.lag_steps == 5
        assert dyn.compounding_factor > 1.0

    def test_habit_dynamics(self):
        dyn = habit_dynamics()
        assert dyn.lag_steps == 14
        assert dyn.volatility < 0.2


# ── Dynamics applied tracking ────────────────────────────────────


class TestDynamicsApplied:
    def test_tracks_which_effects_applied(self):
        dyn = FeedbackDynamics(
            lag_steps=3, compounding_factor=1.1, decay_rate=0.05,
            saturation_threshold=0.9,
        )
        result = dyn.project_score(
            0.4, elapsed_steps=1,
            historical_trajectory=[0.2, 0.3, 0.35],
        )
        assert result.dynamics_applied["compounding"] is True
        assert result.dynamics_applied["decay"] is True
        assert result.dynamics_applied["saturation"] is True
        assert result.dynamics_applied["trend_extrapolation"] is True

    def test_no_effects_when_defaults(self):
        dyn = FeedbackDynamics(lag_steps=0)
        result = dyn.project_score(0.5)
        assert result.dynamics_applied["compounding"] is False
        assert result.dynamics_applied["decay"] is False
