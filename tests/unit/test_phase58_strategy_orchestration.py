"""Phase 58 — Regime-aware strategy orchestration tests.

Tests the unified decision pipeline that combines base scores,
regime weights, and optional feedback selection.

Invariants 233-241.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.feedback_selection import FeedbackSelectionPolicy
from umh.runtime.strategy_orchestrator import (
    StrategyCandidate,
    StrategyOrchestrationPolicy,
    StrategySelectionResult,
    orchestrate_selection,
)


# ===========================================================================
# SECTION 1 — StrategyOrchestrationPolicy defaults
# ===========================================================================


class TestSection01PolicyDefaults:
    def test_default_use_regime(self):
        p = StrategyOrchestrationPolicy()
        assert p.use_regime_weighting is True

    def test_default_use_feedback(self):
        assert StrategyOrchestrationPolicy().use_feedback_selection is False

    def test_default_feedback_policy_none(self):
        assert StrategyOrchestrationPolicy().feedback_policy is None

    def test_default_require_valid(self):
        assert StrategyOrchestrationPolicy().require_valid is True


# ===========================================================================
# SECTION 2 — Policy to_dict
# ===========================================================================


class TestSection02PolicyDict:
    def test_to_dict_keys(self):
        d = StrategyOrchestrationPolicy().to_dict()
        expected = {
            "use_regime_weighting",
            "use_feedback_selection",
            "feedback_policy",
            "require_valid",
        }
        assert set(d.keys()) == expected

    def test_to_dict_feedback_none(self):
        d = StrategyOrchestrationPolicy().to_dict()
        assert d["feedback_policy"] is None

    def test_to_dict_with_feedback_policy(self):
        fp = FeedbackSelectionPolicy(enabled=True)
        p = StrategyOrchestrationPolicy(feedback_policy=fp)
        d = p.to_dict()
        assert d["feedback_policy"] is not None
        assert d["feedback_policy"]["enabled"] is True


# ===========================================================================
# SECTION 3 — Policy frozen
# ===========================================================================


class TestSection03PolicyFrozen:
    def test_frozen(self):
        p = StrategyOrchestrationPolicy()
        try:
            p.use_regime_weighting = False
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 4 — StrategyCandidate defaults
# ===========================================================================


class TestSection04CandidateDefaults:
    def test_default_strategy_id(self):
        c = StrategyCandidate()
        assert c.strategy_id == ""

    def test_default_base_score(self):
        assert StrategyCandidate().base_score == 0.0

    def test_default_regime_factor(self):
        assert StrategyCandidate().regime_factor == 1.0

    def test_default_feedback_factor(self):
        assert StrategyCandidate().feedback_factor == 1.0

    def test_default_confidence(self):
        assert StrategyCandidate().confidence == 0.0

    def test_default_valid(self):
        assert StrategyCandidate().valid is True

    def test_default_safe(self):
        assert StrategyCandidate().safe is True


# ===========================================================================
# SECTION 5 — Candidate bounds clamping
# ===========================================================================


class TestSection05CandidateBounds:
    def test_base_score_clamped_low(self):
        c = StrategyCandidate(base_score=-1.0)
        assert c.base_score == 0.0

    def test_base_score_clamped_high(self):
        c = StrategyCandidate(base_score=5.0)
        assert c.base_score == 2.0

    def test_regime_factor_clamped_low(self):
        c = StrategyCandidate(regime_factor=0.5)
        assert c.regime_factor == 0.85

    def test_regime_factor_clamped_high(self):
        c = StrategyCandidate(regime_factor=2.0)
        assert c.regime_factor == 1.15

    def test_feedback_factor_clamped_low(self):
        c = StrategyCandidate(feedback_factor=-1.0)
        assert c.feedback_factor == 0.0

    def test_feedback_factor_clamped_high(self):
        c = StrategyCandidate(feedback_factor=5.0)
        assert c.feedback_factor == 2.0

    def test_confidence_clamped_low(self):
        c = StrategyCandidate(confidence=-0.5)
        assert c.confidence == 0.0

    def test_confidence_clamped_high(self):
        c = StrategyCandidate(confidence=2.0)
        assert c.confidence == 1.0


# ===========================================================================
# SECTION 6 — Candidate computed properties
# ===========================================================================


class TestSection06CandidateComputed:
    def test_regime_adjusted_score(self):
        c = StrategyCandidate(base_score=0.80, regime_factor=1.10)
        expected = 0.80 * 1.10
        assert abs(c.regime_adjusted_score - expected) < 1e-9

    def test_final_score(self):
        c = StrategyCandidate(base_score=0.80, regime_factor=1.10, feedback_factor=1.05)
        expected = 0.80 * 1.10 * 1.05
        assert abs(c.final_score - expected) < 1e-9

    def test_neutral_factors_preserve_base(self):
        c = StrategyCandidate(base_score=0.75)
        assert c.regime_adjusted_score == 0.75
        assert c.final_score == 0.75


# ===========================================================================
# SECTION 7 — Candidate to_dict
# ===========================================================================


class TestSection07CandidateDict:
    def test_to_dict_keys(self):
        d = StrategyCandidate().to_dict()
        expected = {
            "strategy_id",
            "base_score",
            "regime_factor",
            "feedback_factor",
            "weight_factor",
            "interaction_factor",
            "pattern_factor",
            "confidence",
            "regime_adjusted_score",
            "final_score",
            "valid",
            "safe",
        }
        assert set(d.keys()) == expected

    def test_to_dict_computed_fields(self):
        c = StrategyCandidate(base_score=0.80, regime_factor=1.10)
        d = c.to_dict()
        assert "regime_adjusted_score" in d
        assert "final_score" in d


# ===========================================================================
# SECTION 8 — Candidate frozen
# ===========================================================================


class TestSection08CandidateFrozen:
    def test_frozen(self):
        c = StrategyCandidate()
        try:
            c.base_score = 0.5
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 9 — StrategySelectionResult defaults
# ===========================================================================


class TestSection09ResultDefaults:
    def test_default_selected(self):
        r = StrategySelectionResult()
        assert r.selected_strategy == ""

    def test_default_candidates(self):
        assert StrategySelectionResult().candidates == ()

    def test_default_explanation(self):
        assert StrategySelectionResult().explanation == ""

    def test_default_used_regime(self):
        assert StrategySelectionResult().used_regime is False

    def test_default_used_feedback(self):
        assert StrategySelectionResult().used_feedback is False

    def test_default_base_winner(self):
        assert StrategySelectionResult().base_winner == ""

    def test_default_regime_winner(self):
        assert StrategySelectionResult().regime_winner == ""

    def test_default_feedback_winner(self):
        assert StrategySelectionResult().feedback_winner == ""

    def test_default_changed_from_base(self):
        assert StrategySelectionResult().changed_from_base is False

    def test_default_changed_from_regime(self):
        assert StrategySelectionResult().changed_from_regime is False


# ===========================================================================
# SECTION 10 — Result to_dict
# ===========================================================================


class TestSection10ResultDict:
    def test_to_dict_keys(self):
        d = StrategySelectionResult().to_dict()
        expected = {
            "selected_strategy",
            "candidates",
            "explanation",
            "used_regime",
            "used_feedback",
            "used_weights",
            "used_interactions",
            "used_pattern",
            "base_winner",
            "regime_winner",
            "feedback_winner",
            "weight_winner",
            "interaction_winner",
            "pattern_winner",
            "changed_from_base",
            "changed_from_regime",
            "changed_from_feedback",
            "changed_from_weights",
            "changed_from_interactions",
        }
        assert set(d.keys()) == expected


# ===========================================================================
# SECTION 11 — Result frozen
# ===========================================================================


class TestSection11ResultFrozen:
    def test_frozen(self):
        r = StrategySelectionResult()
        try:
            r.selected_strategy = "x"
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 12 — Default behavior: base scoring only (inv 236)
# ===========================================================================


class TestSection12DefaultBehavior:
    def test_default_selects_base_best(self):
        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.5, 0.9, 0.3],
        )
        assert r.selected_strategy == "b"

    def test_default_no_feedback(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert r.used_feedback is False

    def test_default_uses_regime(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert r.used_regime is True

    def test_default_no_change(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert r.changed_from_base is False

    def test_default_neutral_regime_same_as_base(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            regime_factors=[1.0, 1.0],
        )
        assert r.selected_strategy == "b"
        assert r.base_winner == "b"
        assert r.regime_winner == "b"


# ===========================================================================
# SECTION 13 — Empty strategies
# ===========================================================================


class TestSection13EmptyStrategies:
    def test_empty_returns_no_selection(self):
        r = orchestrate_selection([], [])
        assert r.selected_strategy == ""

    def test_empty_explanation(self):
        r = orchestrate_selection([], [])
        assert "no strategies" in r.explanation


# ===========================================================================
# SECTION 14 — Regime factor boosts correct candidate (inv 234)
# ===========================================================================


class TestSection14RegimeBoost:
    def test_regime_boost_changes_winner(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.80, 0.78],
            regime_factors=[0.90, 1.15],
        )
        assert r.selected_strategy == "b"
        assert r.changed_from_base is True

    def test_regime_boost_recorded(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.50, 0.90],
            regime_factors=[1.10, 1.0],
        )
        for c in r.candidates:
            if c.strategy_id == "a":
                assert c.regime_factor == 1.10

    def test_regime_boost_base_winner_preserved(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.50, 0.90],
            regime_factors=[1.10, 1.0],
        )
        assert r.base_winner == "b"


# ===========================================================================
# SECTION 15 — Regime factor penalizes correctly (inv 234)
# ===========================================================================


class TestSection15RegimePenalty:
    def test_regime_penalty_changes_winner(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.82, 0.80],
            regime_factors=[0.85, 1.0],
        )
        assert r.selected_strategy == "b"

    def test_regime_penalty_recorded(self):
        r = orchestrate_selection(
            ["a"],
            [0.90],
            regime_factors=[0.90],
        )
        assert r.candidates[0].regime_factor == 0.90


# ===========================================================================
# SECTION 16 — Neutral regime = no change
# ===========================================================================


class TestSection16NeutralRegime:
    def test_neutral_regime_no_change(self):
        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.5, 0.9, 0.3],
            regime_factors=[1.0, 1.0, 1.0],
        )
        assert r.selected_strategy == "b"
        assert r.changed_from_base is False

    def test_neutral_regime_factor_preserved(self):
        r = orchestrate_selection(
            ["a"],
            [0.5],
            regime_factors=[1.0],
        )
        assert r.candidates[0].regime_factor == 1.0


# ===========================================================================
# SECTION 17 — Regime factor bounded (inv 234)
# ===========================================================================


class TestSection17RegimeBounded:
    def test_regime_factor_clamped_high(self):
        r = orchestrate_selection(
            ["a"],
            [1.0],
            regime_factors=[2.0],
        )
        assert r.candidates[0].regime_factor == 1.15

    def test_regime_factor_clamped_low(self):
        r = orchestrate_selection(
            ["a"],
            [1.0],
            regime_factors=[0.5],
        )
        assert r.candidates[0].regime_factor == 0.85

    def test_regime_score_bounded(self):
        r = orchestrate_selection(
            ["a"],
            [1.0],
            regime_factors=[2.0],
        )
        assert r.candidates[0].regime_adjusted_score <= 1.15


# ===========================================================================
# SECTION 18 — Feedback disabled = no effect (inv 235)
# ===========================================================================


class TestSection18FeedbackDisabled:
    def test_feedback_disabled_by_default(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.5, 0.5],
            confidences=[1.0, 1.0],
        )
        assert r.selected_strategy == "b"
        assert r.used_feedback is False

    def test_feedback_factors_ignored(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[2.0, 0.1],
            confidences=[1.0, 1.0],
        )
        assert r.selected_strategy == "b"

    def test_explicit_disabled(self):
        p = StrategyOrchestrationPolicy(use_feedback_selection=False)
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[2.0, 0.1],
            confidences=[1.0, 1.0],
            policy=p,
        )
        assert r.used_feedback is False


# ===========================================================================
# SECTION 19 — Feedback enabled integrates Phase 57 (inv 235)
# ===========================================================================


class TestSection19FeedbackEnabled:
    def test_feedback_enabled_uses_feedback(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.80, 0.78],
            regime_factors=[1.0, 1.0],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.used_feedback is True

    def test_feedback_can_change_selection(self):
        fp = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.05
        )
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.52, 0.50],
            regime_factors=[1.0, 1.0],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.selected_strategy == "b"
        assert r.used_feedback is True


# ===========================================================================
# SECTION 20 — Low-confidence feedback ignored (inv 228 via 235)
# ===========================================================================


class TestSection20LowConfidenceFeedback:
    def test_low_confidence_no_effect(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.6)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.5, 0.5],
            confidences=[0.3, 0.3],
            policy=p,
        )
        assert r.selected_strategy == "b"


# ===========================================================================
# SECTION 21 — Composition: regime + feedback both applied
# ===========================================================================


class TestSection21Composition:
    def test_regime_then_feedback(self):
        fp = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.05
        )
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.55, 0.50],
            regime_factors=[0.90, 1.10],
            feedback_factors=[0.95, 1.10],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.used_regime is True
        assert r.used_feedback is True
        assert r.selected_strategy != ""

    def test_regime_applied_before_feedback(self):
        fp = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.05
        )
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.60, 0.55],
            regime_factors=[0.85, 1.15],
            feedback_factors=[1.0, 1.0],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.regime_winner == "b"


# ===========================================================================
# SECTION 22 — Ordering preserved (base → regime → feedback)
# ===========================================================================


class TestSection22Ordering:
    def test_base_winner_correct(self):
        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.3, 0.9, 0.5],
        )
        assert r.base_winner == "b"

    def test_regime_winner_differs_from_base(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.82, 0.80],
            regime_factors=[0.85, 1.15],
        )
        assert r.base_winner == "a"
        assert r.regime_winner == "b"

    def test_all_three_winners_tracked(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            regime_factors=[1.0, 1.0],
            policy=p,
        )
        assert r.base_winner != ""
        assert r.regime_winner != ""
        assert r.feedback_winner != ""


# ===========================================================================
# SECTION 23 — Invalid candidate never selected (inv 240)
# ===========================================================================


class TestSection23InvalidCandidate:
    def test_invalid_skipped(self):
        r = orchestrate_selection(
            ["invalid", "valid"],
            [0.95, 0.50],
            valid_flags=[False, True],
        )
        assert r.selected_strategy == "valid"

    def test_invalid_with_regime_boost(self):
        r = orchestrate_selection(
            ["invalid", "valid"],
            [0.90, 0.50],
            regime_factors=[1.15, 1.0],
            valid_flags=[False, True],
        )
        assert r.selected_strategy == "valid"

    def test_invalid_with_feedback_boost(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["invalid", "valid"],
            [0.90, 0.50],
            feedback_factors=[1.12, 1.0],
            confidences=[1.0, 1.0],
            valid_flags=[False, True],
            policy=p,
        )
        assert r.selected_strategy == "valid"


# ===========================================================================
# SECTION 24 — Unsafe candidate never selected (inv 240)
# ===========================================================================


class TestSection24UnsafeCandidate:
    def test_unsafe_skipped(self):
        r = orchestrate_selection(
            ["unsafe", "safe"],
            [0.95, 0.50],
            safe_flags=[False, True],
        )
        assert r.selected_strategy == "safe"

    def test_unsafe_with_both_boosts(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["unsafe", "safe"],
            [0.95, 0.30],
            regime_factors=[1.15, 1.0],
            feedback_factors=[1.12, 1.0],
            confidences=[1.0, 1.0],
            safe_flags=[False, True],
            policy=p,
        )
        assert r.selected_strategy == "safe"


# ===========================================================================
# SECTION 25 — All invalid case (inv 240)
# ===========================================================================


class TestSection25AllInvalid:
    def test_all_invalid_no_selection(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.9, 0.8],
            valid_flags=[False, False],
        )
        assert r.selected_strategy == ""

    def test_all_invalid_explanation(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.9, 0.8],
            valid_flags=[False, False],
        )
        assert "invalid" in r.explanation or "unsafe" in r.explanation

    def test_all_unsafe_no_selection(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.9, 0.8],
            safe_flags=[False, False],
        )
        assert r.selected_strategy == ""


# ===========================================================================
# SECTION 26 — Determinism (inv 237)
# ===========================================================================


class TestSection26Determinism:
    def test_same_inputs_same_output(self):
        results = []
        for _ in range(20):
            r = orchestrate_selection(
                ["x", "y", "z"],
                [0.6, 0.7, 0.5],
                regime_factors=[1.05, 0.95, 1.10],
            )
            results.append(r.selected_strategy)
        assert len(set(results)) == 1

    def test_same_with_feedback(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        results = []
        for _ in range(20):
            r = orchestrate_selection(
                ["a", "b"],
                [0.5, 0.6],
                regime_factors=[1.05, 0.95],
                feedback_factors=[1.1, 0.95],
                confidences=[0.8, 0.8],
                policy=p,
            )
            results.append(r.selected_strategy)
        assert len(set(results)) == 1


# ===========================================================================
# SECTION 27 — Stable tie-breaking (inv 237)
# ===========================================================================


class TestSection27TieBreaking:
    def test_tie_break_by_strategy_id(self):
        r = orchestrate_selection(
            ["c", "a", "b"],
            [0.5, 0.5, 0.5],
        )
        assert r.selected_strategy == "a"

    def test_tie_deterministic(self):
        results = []
        for _ in range(10):
            r = orchestrate_selection(
                ["z", "m", "a"],
                [0.5, 0.5, 0.5],
            )
            results.append(r.selected_strategy)
        assert len(set(results)) == 1
        assert results[0] == "a"


# ===========================================================================
# SECTION 28 — No randomness (inv 237)
# ===========================================================================


class TestSection28NoRandomness:
    def test_no_random_import(self):
        import umh.runtime.strategy_orchestrator as m
        import inspect

        src = inspect.getsource(m)
        assert "import random" not in src

    def test_repeated_runs_identical(self):
        all_results = []
        for _ in range(50):
            r = orchestrate_selection(
                ["s1", "s2"],
                [0.55, 0.60],
                regime_factors=[1.05, 0.95],
            )
            all_results.append((r.selected_strategy, r.changed_from_base, r.explanation))
        assert len(set(all_results)) == 1


# ===========================================================================
# SECTION 29 — Explainability: base winner named (inv 239)
# ===========================================================================


class TestSection29BaseWinnerExplained:
    def test_base_winner_in_result(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert r.base_winner == "b"

    def test_base_winner_in_explanation(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert "b" in r.explanation


# ===========================================================================
# SECTION 30 — Explainability: regime winner named (inv 239)
# ===========================================================================


class TestSection30RegimeWinnerExplained:
    def test_regime_winner_in_result(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.82, 0.80],
            regime_factors=[0.85, 1.15],
        )
        assert r.regime_winner == "b"

    def test_regime_change_in_explanation(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.82, 0.80],
            regime_factors=[0.85, 1.15],
        )
        assert "regime" in r.explanation.lower()


# ===========================================================================
# SECTION 31 — Explainability: feedback winner named (inv 239)
# ===========================================================================


class TestSection31FeedbackWinnerExplained:
    def test_feedback_winner_in_result(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert r.feedback_winner != ""

    def test_feedback_in_explanation(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert "feedback" in r.explanation.lower()


# ===========================================================================
# SECTION 32 — Explainability: changed_from_base (inv 239)
# ===========================================================================


class TestSection32ChangedFromBase:
    def test_changed_true_when_regime_reorders(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.82, 0.80],
            regime_factors=[0.85, 1.15],
        )
        assert r.changed_from_base is True

    def test_changed_false_when_same(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert r.changed_from_base is False

    def test_changed_explanation(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.82, 0.80],
            regime_factors=[0.85, 1.15],
        )
        assert "changed" in r.explanation or "selection" in r.explanation


# ===========================================================================
# SECTION 33 — Explainability: changed_from_regime
# ===========================================================================


class TestSection33ChangedFromRegime:
    def test_changed_from_regime_tracked(self):
        fp = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.05
        )
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.52, 0.50],
            regime_factors=[1.0, 1.0],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        if r.feedback_winner != r.regime_winner:
            assert r.changed_from_regime is True


# ===========================================================================
# SECTION 34 — Missing inputs degrade to neutral (inv 241)
# ===========================================================================


class TestSection34MissingInputs:
    def test_missing_regime_factors_neutral(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        for c in r.candidates:
            assert c.regime_factor == 1.0

    def test_missing_feedback_factors_neutral(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert r.selected_strategy == "b"

    def test_missing_confidences_neutral(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.5)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.5, 0.5],
            policy=p,
        )
        assert r.selected_strategy == "b"

    def test_missing_valid_flags_default_true(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        for c in r.candidates:
            assert c.valid is True

    def test_missing_safe_flags_default_true(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        for c in r.candidates:
            assert c.safe is True


# ===========================================================================
# SECTION 35 — No scoring mutation (inv 233)
# ===========================================================================


class TestSection35NoScoringMutation:
    def test_scores_not_mutated(self):
        scores = [0.5, 0.9, 0.3]
        original = list(scores)
        orchestrate_selection(["a", "b", "c"], scores)
        assert scores == original

    def test_regime_factors_not_mutated(self):
        factors = [1.05, 0.95, 1.0]
        original = list(factors)
        orchestrate_selection(
            ["a", "b", "c"],
            [0.5, 0.6, 0.7],
            regime_factors=factors,
        )
        assert factors == original

    def test_feedback_factors_not_mutated(self):
        factors = [1.1, 0.9, 1.0]
        original = list(factors)
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        orchestrate_selection(
            ["a", "b", "c"],
            [0.5, 0.6, 0.7],
            feedback_factors=factors,
            confidences=[0.8, 0.8, 0.8],
            policy=p,
        )
        assert factors == original

    def test_candidates_not_mutated(self):
        ids = ["a", "b", "c"]
        original = list(ids)
        orchestrate_selection(ids, [0.5, 0.6, 0.7])
        assert ids == original


# ===========================================================================
# SECTION 36 — Boundary compliance
# ===========================================================================


class TestSection36Boundary:
    def test_no_os_import(self):
        import umh.runtime.strategy_orchestrator as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import os" not in code_section

    def test_no_subprocess_import(self):
        import umh.runtime.strategy_orchestrator as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import subprocess" not in code_section

    def test_no_docker_import(self):
        import umh.runtime.strategy_orchestrator as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import docker" not in code_section

    def test_no_cells_import(self):
        import umh.runtime.strategy_orchestrator as m
        import inspect

        src = inspect.getsource(m)
        assert "from umh.cells" not in src
        assert "from umh.environments" not in src
        assert "from umh.adapters" not in src


# ===========================================================================
# SECTION 37 — No execution methods (inv 233)
# ===========================================================================


class TestSection37NoExecution:
    def test_no_execute_method(self):
        assert not hasattr(StrategyOrchestrationPolicy, "execute")
        assert not hasattr(StrategySelectionResult, "execute")
        assert not hasattr(StrategyCandidate, "execute")

    def test_no_apply_method(self):
        assert not hasattr(StrategyOrchestrationPolicy, "apply")
        assert not hasattr(StrategySelectionResult, "apply")

    def test_no_mutate_method(self):
        assert not hasattr(StrategyOrchestrationPolicy, "mutate")
        assert not hasattr(StrategyCandidate, "mutate")


# ===========================================================================
# SECTION 38 — Import surface
# ===========================================================================


class TestSection38ImportSurface:
    def test_all_exports(self):
        from umh.runtime import (
            StrategyCandidate,
            StrategyOrchestrationPolicy,
            StrategySelectionResult,
            orchestrate_selection,
        )

        assert StrategyCandidate is not None
        assert StrategyOrchestrationPolicy is not None
        assert StrategySelectionResult is not None
        assert orchestrate_selection is not None


# ===========================================================================
# SECTION 39 — Regime disabled path
# ===========================================================================


class TestSection39RegimeDisabled:
    def test_regime_disabled_ignores_factors(self):
        p = StrategyOrchestrationPolicy(use_regime_weighting=False)
        r = orchestrate_selection(
            ["a", "b"],
            [0.50, 0.90],
            regime_factors=[1.15, 0.85],
            policy=p,
        )
        assert r.selected_strategy == "b"
        assert r.used_regime is False

    def test_regime_disabled_factors_one(self):
        p = StrategyOrchestrationPolicy(use_regime_weighting=False)
        r = orchestrate_selection(
            ["a"],
            [0.50],
            regime_factors=[1.15],
            policy=p,
        )
        assert r.candidates[0].regime_factor == 1.0

    def test_regime_disabled_explanation(self):
        p = StrategyOrchestrationPolicy(use_regime_weighting=False)
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert "regime" in r.explanation.lower()


# ===========================================================================
# SECTION 40 — Length mismatches handled
# ===========================================================================


class TestSection40LengthMismatch:
    def test_fewer_scores_padded(self):
        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.5],
        )
        assert len(r.candidates) == 3

    def test_more_scores_truncated(self):
        r = orchestrate_selection(
            ["a"],
            [0.5, 0.9, 0.3],
        )
        assert len(r.candidates) == 1

    def test_fewer_regime_factors_padded(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            regime_factors=[1.10],
        )
        assert r.candidates[1].regime_factor == 1.0

    def test_fewer_valid_flags_padded(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            valid_flags=[True],
        )
        assert r.candidates[1].valid is True


# ===========================================================================
# SECTION 41 — Single strategy
# ===========================================================================


class TestSection41SingleStrategy:
    def test_single_selected(self):
        r = orchestrate_selection(["only"], [0.5])
        assert r.selected_strategy == "only"

    def test_single_invalid(self):
        r = orchestrate_selection(
            ["only"],
            [0.5],
            valid_flags=[False],
        )
        assert r.selected_strategy == ""

    def test_single_with_regime(self):
        r = orchestrate_selection(
            ["only"],
            [0.5],
            regime_factors=[1.10],
        )
        assert r.selected_strategy == "only"
        assert r.candidates[0].regime_factor == 1.10


# ===========================================================================
# SECTION 42 — Many strategies stress test
# ===========================================================================


class TestSection42ManyStrategies:
    def test_100_strategies(self):
        ids = [f"s_{i:03d}" for i in range(100)]
        scores = [0.5 + (i % 10) * 0.05 for i in range(100)]
        factors = [1.0 + (i % 5 - 2) * 0.03 for i in range(100)]
        r = orchestrate_selection(ids, scores, regime_factors=factors)
        assert len(r.candidates) == 100
        assert r.selected_strategy != ""

    def test_100_strategies_deterministic(self):
        ids = [f"s_{i:03d}" for i in range(100)]
        scores = [0.5 + (i % 10) * 0.05 for i in range(100)]
        factors = [1.0 + (i % 5 - 2) * 0.03 for i in range(100)]
        results = [
            orchestrate_selection(ids, scores, regime_factors=factors).selected_strategy
            for _ in range(5)
        ]
        assert len(set(results)) == 1


# ===========================================================================
# SECTION 43 — Candidate order preserved
# ===========================================================================


class TestSection43CandidateOrder:
    def test_order_preserved(self):
        r = orchestrate_selection(
            ["c", "a", "b"],
            [0.3, 0.5, 0.9],
        )
        ids = [c.strategy_id for c in r.candidates]
        assert ids == ["c", "a", "b"]


# ===========================================================================
# SECTION 44 — No circular dependency (inv 238)
# ===========================================================================


class TestSection44NoCircular:
    def test_orchestrator_does_not_import_scoring(self):
        import umh.runtime.strategy_orchestrator as m
        import inspect

        src = inspect.getsource(m)
        assert "from umh.runtime.evaluator" not in src
        assert "from umh.runtime.planner" not in src

    def test_orchestrator_imports_only_allowed_modules(self):
        import umh.runtime.strategy_orchestrator as m
        import inspect

        src = inspect.getsource(m)
        allowed = {
            "feedback_selection",
            "regime_aggregation",
            "dimension_weighting",
            "weighted_decision",
            "dimension_interactions",
            "pattern_influence",
            "pattern_matching",
            "pattern_aggregation",
        }
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed)


# ===========================================================================
# SECTION 45 — Meta planner default unchanged (inv 236)
# ===========================================================================


class TestSection45MetaPlannerDefault:
    def test_no_orchestration_by_default(self):
        from umh.runtime.meta_planner import MetaPlanner

        mp = MetaPlanner()
        assert mp.orchestration_policy is None

    def test_plan_works_without_orchestration(self):
        from umh.runtime.meta_planner import MetaPlanner, SequenceEvaluator, SequenceGenerator
        from umh.runtime.arbitration import Objective

        objectives = [
            Objective(
                objective_id=f"obj_{i}",
                description=f"test {i}",
                priority=5,
                effort_estimate=1.0,
            )
            for i in range(3)
        ]
        mp = MetaPlanner()
        result = mp.plan(objectives)
        assert result is not None
        assert result.next_objective is not None

    def test_plan_signature_accepts_regime_factors(self):
        import inspect
        from umh.runtime.meta_planner import MetaPlanner

        sig = inspect.signature(MetaPlanner.plan)
        params = list(sig.parameters.keys())
        assert "regime_factors" in params

    def test_plan_signature_accepts_feedback_factors(self):
        import inspect
        from umh.runtime.meta_planner import MetaPlanner

        sig = inspect.signature(MetaPlanner.plan)
        params = list(sig.parameters.keys())
        assert "feedback_factors" in params


# ===========================================================================
# SECTION 46 — Meta planner with orchestration
# ===========================================================================


class TestSection46MetaPlannerWithOrchestration:
    def test_orchestration_activates_with_policy(self):
        from umh.runtime.meta_planner import MetaPlanner
        from umh.runtime.arbitration import Objective

        objectives = [
            Objective(
                objective_id=f"obj_{i}",
                description=f"test {i}",
                priority=5 + i,
                effort_estimate=1.0,
            )
            for i in range(3)
        ]
        p = StrategyOrchestrationPolicy(use_regime_weighting=True)
        mp = MetaPlanner(orchestration_policy=p)
        result = mp.plan(objectives)
        assert result is not None

    def test_orchestration_with_regime_factors(self):
        from umh.runtime.meta_planner import MetaPlanner
        from umh.runtime.arbitration import Objective

        objectives = [
            Objective(
                objective_id=f"obj_{i}",
                description=f"test {i}",
                priority=5,
                effort_estimate=1.0,
            )
            for i in range(3)
        ]
        p = StrategyOrchestrationPolicy(use_regime_weighting=True)
        mp = MetaPlanner(orchestration_policy=p)
        result = mp.plan(objectives, regime_factors={"seq-0": 1.10})
        assert result is not None


# ===========================================================================
# SECTION 47 — Regime weight composition
# ===========================================================================


class TestSection47RegimeWeightComposition:
    def test_regime_boost_and_penalty_together(self):
        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.70, 0.80, 0.60],
            regime_factors=[1.15, 0.85, 1.10],
        )
        assert r.selected_strategy != ""
        assert r.used_regime is True

    def test_all_regime_penalties(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.80, 0.90],
            regime_factors=[0.85, 0.90],
        )
        assert r.selected_strategy == "b"


# ===========================================================================
# SECTION 48 — Feedback without regime
# ===========================================================================


class TestSection48FeedbackWithoutRegime:
    def test_feedback_only(self):
        fp = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.05
        )
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=False,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.52, 0.50],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.used_regime is False
        assert r.used_feedback is True

    def test_feedback_only_base_preserved(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=False,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a"],
            [0.80],
            feedback_factors=[1.0],
            confidences=[0.8],
            policy=p,
        )
        assert r.candidates[0].regime_factor == 1.0


# ===========================================================================
# SECTION 49 — Explanation always populated (inv 239)
# ===========================================================================


class TestSection49ExplanationPopulated:
    def test_empty_has_explanation(self):
        r = orchestrate_selection([], [])
        assert len(r.explanation) > 0

    def test_default_has_explanation(self):
        r = orchestrate_selection(["a", "b"], [0.5, 0.9])
        assert len(r.explanation) > 0

    def test_with_regime_has_explanation(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            regime_factors=[1.10, 0.90],
        )
        assert len(r.explanation) > 0

    def test_with_feedback_has_explanation(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert len(r.explanation) > 0


# ===========================================================================
# SECTION 50 — Explanation includes selected strategy
# ===========================================================================


class TestSection50ExplanationSelected:
    def test_selected_in_explanation(self):
        r = orchestrate_selection(
            ["alpha", "beta"],
            [0.5, 0.9],
        )
        assert "beta" in r.explanation


# ===========================================================================
# SECTION 51 — Candidates tuple immutable
# ===========================================================================


class TestSection51ImmutableCandidates:
    def test_candidates_is_tuple(self):
        r = orchestrate_selection(["a", "b"], [0.5, 0.9])
        assert isinstance(r.candidates, tuple)

    def test_candidates_frozen(self):
        r = orchestrate_selection(["a", "b"], [0.5, 0.9])
        try:
            r.candidates[0].base_score = 999.0
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 52 — Zero base scores
# ===========================================================================


class TestSection52ZeroBaseScores:
    def test_all_zero(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.0, 0.0],
        )
        assert r.selected_strategy != ""

    def test_zero_with_regime_boost(self):
        r = orchestrate_selection(
            ["a"],
            [0.0],
            regime_factors=[1.15],
        )
        assert r.candidates[0].regime_adjusted_score == 0.0


# ===========================================================================
# SECTION 53 — Mixed valid/safe flags
# ===========================================================================


class TestSection53MixedFlags:
    def test_invalid_and_unsafe_excluded(self):
        r = orchestrate_selection(
            ["a", "b", "c", "d"],
            [0.9, 0.8, 0.7, 0.3],
            valid_flags=[False, True, True, True],
            safe_flags=[True, False, True, True],
        )
        assert r.selected_strategy in ("c", "d")

    def test_only_fully_valid_safe(self):
        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.9, 0.8, 0.3],
            valid_flags=[True, True, True],
            safe_flags=[False, False, True],
        )
        assert r.selected_strategy == "c"


# ===========================================================================
# SECTION 54 — Policy with custom feedback policy
# ===========================================================================


class TestSection54CustomFeedbackPolicy:
    def test_tight_feedback_bounds(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.02)
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a"],
            [1.0],
            feedback_factors=[1.5],
            confidences=[1.0],
            policy=p,
        )
        assert r.selected_strategy == "a"

    def test_default_feedback_policy_created(self):
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert r.used_feedback is True


# ===========================================================================
# SECTION 55 — Both regime and feedback disabled
# ===========================================================================


class TestSection55BothDisabled:
    def test_pure_base_scoring(self):
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=False,
            use_feedback_selection=False,
        )
        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.3, 0.9, 0.5],
            regime_factors=[1.15, 0.85, 1.10],
            feedback_factors=[1.5, 0.5, 1.0],
            confidences=[1.0, 1.0, 1.0],
            policy=p,
        )
        assert r.selected_strategy == "b"
        assert r.used_regime is False
        assert r.used_feedback is False


# ===========================================================================
# SECTION 56 — Regime changes leader but feedback reverts
# ===========================================================================


class TestSection56RegimeChangeFeedbackRevert:
    def test_regime_then_feedback_revert(self):
        fp = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.05
        )
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.80, 0.75],
            regime_factors=[0.90, 1.10],
            feedback_factors=[1.12, 0.90],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.selected_strategy != ""
        assert r.used_regime is True
        assert r.used_feedback is True


# ===========================================================================
# SECTION 57 — Explanation includes all pipeline stages
# ===========================================================================


class TestSection57FullPipelineExplanation:
    def test_all_stages_mentioned(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["alpha", "beta"],
            [0.5, 0.9],
            regime_factors=[1.05, 0.95],
            feedback_factors=[1.0, 1.0],
            confidences=[0.8, 0.8],
            policy=p,
        )
        explanation = r.explanation.lower()
        assert "base" in explanation
        assert "regime" in explanation
        assert "feedback" in explanation
        assert "selected" in explanation


# ===========================================================================
# SECTION 58 — to_dict roundtrips
# ===========================================================================


class TestSection58Roundtrips:
    def test_policy_roundtrip(self):
        fp = FeedbackSelectionPolicy(enabled=True, max_adjustment=0.05)
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        d = p.to_dict()
        assert d["use_regime_weighting"] is True
        assert d["use_feedback_selection"] is True
        assert d["feedback_policy"]["max_adjustment"] == 0.05

    def test_candidate_roundtrip(self):
        c = StrategyCandidate(
            strategy_id="test",
            base_score=0.8,
            regime_factor=1.05,
            feedback_factor=1.02,
        )
        d = c.to_dict()
        assert d["strategy_id"] == "test"
        assert d["base_score"] == 0.8
        assert d["regime_factor"] == 1.05

    def test_result_roundtrip(self):
        r = orchestrate_selection(["a", "b"], [0.5, 0.9])
        d = r.to_dict()
        assert d["selected_strategy"] == "b"
        assert len(d["candidates"]) == 2


# ===========================================================================
# SECTION 59 — Regime factor exactly at bounds
# ===========================================================================


class TestSection59RegimeBoundsEdge:
    def test_exactly_at_max(self):
        r = orchestrate_selection(
            ["a"],
            [1.0],
            regime_factors=[1.15],
        )
        assert r.candidates[0].regime_factor == 1.15

    def test_exactly_at_min(self):
        r = orchestrate_selection(
            ["a"],
            [1.0],
            regime_factors=[0.85],
        )
        assert r.candidates[0].regime_factor == 0.85


# ===========================================================================
# SECTION 60 — Three-way competition with full pipeline
# ===========================================================================


class TestSection60ThreeWay:
    def test_three_way_full_pipeline(self):
        fp = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.05
        )
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.60, 0.58, 0.57],
            regime_factors=[0.92, 1.10, 1.05],
            feedback_factors=[0.95, 1.05, 1.10],
            confidences=[0.8, 0.8, 0.8],
            policy=p,
        )
        assert r.selected_strategy in ("a", "b", "c")
        assert r.used_regime is True
        assert r.used_feedback is True

    def test_three_way_deterministic(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        results = []
        for _ in range(10):
            r = orchestrate_selection(
                ["a", "b", "c"],
                [0.60, 0.58, 0.57],
                regime_factors=[0.92, 1.10, 1.05],
                feedback_factors=[0.95, 1.05, 1.10],
                confidences=[0.8, 0.8, 0.8],
                policy=p,
            )
            results.append(r.selected_strategy)
        assert len(set(results)) == 1


# ===========================================================================
# SECTION 61 — Regime weight does not modify base scoring functions (inv 233)
# ===========================================================================


class TestSection61NoScoringModification:
    def test_base_score_preserved(self):
        r = orchestrate_selection(
            ["a"],
            [0.75],
            regime_factors=[1.10],
        )
        assert r.candidates[0].base_score == 0.75

    def test_base_winner_reflects_base_scores(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.80, 0.50],
            regime_factors=[0.85, 1.15],
        )
        assert r.base_winner == "a"


# ===========================================================================
# SECTION 62 — End-to-end integration with Phase 57
# ===========================================================================


class TestSection62EndToEnd:
    def test_full_pipeline_integration(self):
        fp = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3, max_adjustment=0.08)
        p = StrategyOrchestrationPolicy(
            use_regime_weighting=True,
            use_feedback_selection=True,
            feedback_policy=fp,
        )
        r = orchestrate_selection(
            ["strat_a", "strat_b", "strat_c"],
            [0.70, 0.75, 0.60],
            regime_factors=[1.05, 0.95, 1.10],
            feedback_factors=[1.02, 1.05, 0.98],
            confidences=[0.7, 0.8, 0.5],
            valid_flags=[True, True, True],
            safe_flags=[True, True, True],
            policy=p,
        )
        assert r.selected_strategy != ""
        assert r.used_regime is True
        assert r.used_feedback is True
        assert len(r.candidates) == 3
        assert r.explanation != ""
        assert r.base_winner != ""
        assert r.regime_winner != ""
        assert r.feedback_winner != ""


# ===========================================================================
# SECTION 63 — Require valid = False path
# ===========================================================================


class TestSection63RequireValidFalse:
    def test_require_valid_false(self):
        p = StrategyOrchestrationPolicy(require_valid=False)
        r = orchestrate_selection(
            ["a", "b"],
            [0.9, 0.8],
            valid_flags=[False, False],
            policy=p,
        )
        assert r.selected_strategy == ""


# ===========================================================================
# SECTION 64 — Explanation mentions disabled features
# ===========================================================================


class TestSection64DisabledExplanation:
    def test_regime_disabled_mentioned(self):
        p = StrategyOrchestrationPolicy(use_regime_weighting=False)
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert "disabled" in r.explanation.lower()

    def test_feedback_disabled_mentioned(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert "disabled" in r.explanation.lower()


# ===========================================================================
# SECTION 65 — Feedback default policy when none provided
# ===========================================================================


class TestSection65DefaultFeedbackPolicy:
    def test_no_feedback_policy_creates_enabled(self):
        p = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=None,
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert r.used_feedback is True


# ===========================================================================
# SECTION 66 — valid_flags and safe_flags interaction
# ===========================================================================


class TestSection66ValidSafeInteraction:
    def test_valid_but_unsafe_excluded(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.9, 0.5],
            valid_flags=[True, True],
            safe_flags=[False, True],
        )
        assert r.selected_strategy == "b"

    def test_safe_but_invalid_excluded(self):
        r = orchestrate_selection(
            ["a", "b"],
            [0.9, 0.5],
            valid_flags=[False, True],
            safe_flags=[True, True],
        )
        assert r.selected_strategy == "b"
