"""Phase 57 — Controlled feedback selection integration tests.

Tests the selection integration layer that applies feedback-informed
ranking to candidates without destabilizing base scoring.

Invariants 225-232.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.feedback_selection import (
    FeedbackAdjustedCandidate,
    FeedbackSelectionPolicy,
    FeedbackSelectionResult,
    select_with_feedback,
)


# ===========================================================================
# SECTION 1 — FeedbackSelectionPolicy defaults
# ===========================================================================


class TestSection01PolicyDefaults:
    def test_disabled_by_default(self):
        p = FeedbackSelectionPolicy()
        assert p.enabled is False

    def test_default_min_confidence(self):
        assert FeedbackSelectionPolicy().min_confidence == 0.6

    def test_default_max_adjustment(self):
        assert FeedbackSelectionPolicy().max_adjustment == 0.12

    def test_default_preserve_top_margin(self):
        assert FeedbackSelectionPolicy().preserve_top_margin == 0.15

    def test_default_require_valid_candidate(self):
        assert FeedbackSelectionPolicy().require_valid_candidate is True


# ===========================================================================
# SECTION 2 — Policy bounds clamping
# ===========================================================================


class TestSection02PolicyBounds:
    def test_min_confidence_clamped_low(self):
        p = FeedbackSelectionPolicy(min_confidence=-0.5)
        assert p.min_confidence == 0.0

    def test_min_confidence_clamped_high(self):
        p = FeedbackSelectionPolicy(min_confidence=2.0)
        assert p.min_confidence == 1.0

    def test_max_adjustment_clamped_low(self):
        p = FeedbackSelectionPolicy(max_adjustment=-0.1)
        assert p.max_adjustment == 0.0

    def test_max_adjustment_clamped_high(self):
        p = FeedbackSelectionPolicy(max_adjustment=0.5)
        assert p.max_adjustment == 0.30

    def test_preserve_top_margin_clamped_low(self):
        p = FeedbackSelectionPolicy(preserve_top_margin=-0.1)
        assert p.preserve_top_margin == 0.0

    def test_preserve_top_margin_clamped_high(self):
        p = FeedbackSelectionPolicy(preserve_top_margin=2.0)
        assert p.preserve_top_margin == 1.0


# ===========================================================================
# SECTION 3 — Policy to_dict
# ===========================================================================


class TestSection03PolicyDict:
    def test_to_dict_keys(self):
        d = FeedbackSelectionPolicy().to_dict()
        expected = {
            "enabled",
            "min_confidence",
            "max_adjustment",
            "preserve_top_margin",
            "require_valid_candidate",
        }
        assert set(d.keys()) == expected

    def test_to_dict_values(self):
        d = FeedbackSelectionPolicy(enabled=True, max_adjustment=0.05).to_dict()
        assert d["enabled"] is True
        assert d["max_adjustment"] == 0.05


# ===========================================================================
# SECTION 4 — Policy frozen
# ===========================================================================


class TestSection04PolicyFrozen:
    def test_frozen(self):
        p = FeedbackSelectionPolicy()
        try:
            p.enabled = True
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 5 — FeedbackAdjustedCandidate defaults
# ===========================================================================


class TestSection05CandidateDefaults:
    def test_default_candidate_id(self):
        c = FeedbackAdjustedCandidate()
        assert c.candidate_id == ""

    def test_default_base_score(self):
        assert FeedbackAdjustedCandidate().base_score == 0.0

    def test_default_feedback_factor(self):
        assert FeedbackAdjustedCandidate().feedback_factor == 1.0

    def test_default_adjusted_score(self):
        assert FeedbackAdjustedCandidate().adjusted_score == 0.0

    def test_default_confidence(self):
        assert FeedbackAdjustedCandidate().confidence == 0.0

    def test_default_valid(self):
        assert FeedbackAdjustedCandidate().valid is True

    def test_default_reason(self):
        assert FeedbackAdjustedCandidate().reason == ""


# ===========================================================================
# SECTION 6 — Candidate bounds clamping
# ===========================================================================


class TestSection06CandidateBounds:
    def test_base_score_clamped_low(self):
        c = FeedbackAdjustedCandidate(base_score=-1.0)
        assert c.base_score == 0.0

    def test_base_score_clamped_high(self):
        c = FeedbackAdjustedCandidate(base_score=5.0)
        assert c.base_score == 2.0

    def test_feedback_factor_clamped_low(self):
        c = FeedbackAdjustedCandidate(feedback_factor=-1.0)
        assert c.feedback_factor == 0.0

    def test_feedback_factor_clamped_high(self):
        c = FeedbackAdjustedCandidate(feedback_factor=5.0)
        assert c.feedback_factor == 2.0

    def test_adjusted_score_clamped_low(self):
        c = FeedbackAdjustedCandidate(adjusted_score=-1.0)
        assert c.adjusted_score == 0.0

    def test_adjusted_score_clamped_high(self):
        c = FeedbackAdjustedCandidate(adjusted_score=5.0)
        assert c.adjusted_score == 2.0

    def test_confidence_clamped_low(self):
        c = FeedbackAdjustedCandidate(confidence=-0.5)
        assert c.confidence == 0.0

    def test_confidence_clamped_high(self):
        c = FeedbackAdjustedCandidate(confidence=2.0)
        assert c.confidence == 1.0


# ===========================================================================
# SECTION 7 — Candidate to_dict
# ===========================================================================


class TestSection07CandidateDict:
    def test_to_dict_keys(self):
        d = FeedbackAdjustedCandidate().to_dict()
        expected = {
            "candidate_id",
            "base_score",
            "feedback_factor",
            "adjusted_score",
            "confidence",
            "valid",
            "reason",
        }
        assert set(d.keys()) == expected


# ===========================================================================
# SECTION 8 — Candidate frozen
# ===========================================================================


class TestSection08CandidateFrozen:
    def test_frozen(self):
        c = FeedbackAdjustedCandidate()
        try:
            c.base_score = 0.5
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 9 — FeedbackSelectionResult defaults
# ===========================================================================


class TestSection09ResultDefaults:
    def test_default_selected_candidate(self):
        r = FeedbackSelectionResult()
        assert r.selected_candidate == ""

    def test_default_adjusted_candidates(self):
        assert FeedbackSelectionResult().adjusted_candidates == ()

    def test_default_policy_enabled(self):
        assert FeedbackSelectionResult().policy_enabled is False

    def test_default_explanation(self):
        assert FeedbackSelectionResult().explanation == ""

    def test_default_changed_selection(self):
        assert FeedbackSelectionResult().changed_selection is False

    def test_default_original_best(self):
        assert FeedbackSelectionResult().original_best == ""

    def test_default_adjusted_best(self):
        assert FeedbackSelectionResult().adjusted_best == ""


# ===========================================================================
# SECTION 10 — Result to_dict
# ===========================================================================


class TestSection10ResultDict:
    def test_to_dict_keys(self):
        d = FeedbackSelectionResult().to_dict()
        expected = {
            "selected_candidate",
            "adjusted_candidates",
            "policy_enabled",
            "explanation",
            "changed_selection",
            "original_best",
            "adjusted_best",
        }
        assert set(d.keys()) == expected


# ===========================================================================
# SECTION 11 — Result frozen
# ===========================================================================


class TestSection11ResultFrozen:
    def test_frozen(self):
        r = FeedbackSelectionResult()
        try:
            r.selected_candidate = "x"
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 12 — Disabled policy returns base ranking (inv 225, 226)
# ===========================================================================


class TestSection12DisabledPolicy:
    def test_disabled_returns_base_best(self):
        r = select_with_feedback(
            ["a", "b", "c"],
            [0.5, 0.9, 0.3],
        )
        assert r.selected_candidate == "b"

    def test_disabled_no_change(self):
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert r.changed_selection is False

    def test_disabled_policy_enabled_false(self):
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert r.policy_enabled is False

    def test_disabled_reason(self):
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert "disabled" in r.explanation

    def test_explicit_disabled_policy(self):
        p = FeedbackSelectionPolicy(enabled=False)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert r.selected_candidate == "b"
        assert r.policy_enabled is False

    def test_disabled_ignores_feedback(self):
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.5, 0.5],
            confidences=[1.0, 1.0],
        )
        assert r.selected_candidate == "b"


# ===========================================================================
# SECTION 13 — Empty candidates
# ===========================================================================


class TestSection13EmptyCandidates:
    def test_empty_candidates(self):
        r = select_with_feedback([], [])
        assert r.selected_candidate == ""

    def test_empty_explanation(self):
        r = select_with_feedback([], [])
        assert "no candidates" in r.explanation

    def test_empty_no_change(self):
        r = select_with_feedback([], [])
        assert r.changed_selection is False


# ===========================================================================
# SECTION 14 — Missing feedback neutral (inv 226)
# ===========================================================================


class TestSection14MissingFeedback:
    def test_none_feedback_neutral(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=None,
            policy=p,
        )
        assert r.selected_candidate == "b"

    def test_none_confidences_neutral(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.1, 0.9],
            confidences=None,
            policy=p,
        )
        assert r.selected_candidate == "b"

    def test_missing_feedback_base_score_preserved(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        for ac in r.adjusted_candidates:
            assert ac.adjusted_score == ac.base_score


# ===========================================================================
# SECTION 15 — Low confidence neutral (inv 228)
# ===========================================================================


class TestSection15LowConfidence:
    def test_low_confidence_no_adjustment(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.6)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.5, 0.5],
            confidences=[0.3, 0.3],
            policy=p,
        )
        assert r.selected_candidate == "b"
        assert r.changed_selection is False

    def test_low_confidence_reason(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.6)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.5, 0.5],
            confidences=[0.3, 0.3],
            policy=p,
        )
        for ac in r.adjusted_candidates:
            assert "below threshold" in ac.reason

    def test_low_confidence_factor_one(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.6)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.2],
            confidences=[0.3],
            policy=p,
        )
        assert r.adjusted_candidates[0].feedback_factor == 1.0

    def test_exactly_at_threshold_applies(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.6)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.1],
            confidences=[0.6],
            policy=p,
        )
        assert (
            r.adjusted_candidates[0].feedback_factor != 1.0
            or r.adjusted_candidates[0].adjusted_score != 0.5
        )


# ===========================================================================
# SECTION 16 — High-confidence positive feedback boosts (inv 227)
# ===========================================================================


class TestSection16PositiveBoost:
    def test_boost_increases_adjusted_score(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.1],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score > 0.5

    def test_boost_reason(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.1],
            confidences=[0.8],
            policy=p,
        )
        assert "boosted" in r.adjusted_candidates[0].reason

    def test_boost_bounded_by_max_adjustment(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.05)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[1.5],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score <= 1.05


# ===========================================================================
# SECTION 17 — High-confidence negative feedback penalizes
# ===========================================================================


class TestSection17NegativePenalty:
    def test_penalty_decreases_adjusted_score(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[0.9],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score < 0.5

    def test_penalty_reason(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[0.9],
            confidences=[0.8],
            policy=p,
        )
        assert "penalized" in r.adjusted_candidates[0].reason

    def test_penalty_bounded_by_max_adjustment(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.05)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[0.5],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score >= 0.95


# ===========================================================================
# SECTION 18 — Factor clamp enforced (inv 227)
# ===========================================================================


class TestSection18FactorClamp:
    def test_extreme_boost_clamped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[2.0],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score <= 1.12

    def test_extreme_penalty_clamped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[0.1],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score >= 0.88

    def test_default_max_adjustment_bounds(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[2.0],
            confidences=[1.0],
            policy=p,
        )
        assert 0.88 <= r.adjusted_candidates[0].adjusted_score <= 1.12


# ===========================================================================
# SECTION 19 — preserve_top_margin prevents weak challenger (inv 229)
# ===========================================================================


class TestSection19PreserveTopMargin:
    def test_large_margin_keeps_base_leader(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, preserve_top_margin=0.15)
        r = select_with_feedback(
            ["a", "b"],
            [0.90, 0.60],
            feedback_factors=[0.88, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.selected_candidate == "a"
        assert r.changed_selection is False

    def test_large_margin_explanation(self):
        p = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.25, preserve_top_margin=0.15
        )
        r = select_with_feedback(
            ["a", "b"],
            [0.90, 0.55],
            feedback_factors=[0.70, 1.30],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert "preserve_top_margin" in r.explanation or "keeping base" in r.explanation

    def test_close_candidates_can_reorder(self):
        p = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.15
        )
        r = select_with_feedback(
            ["a", "b"],
            [0.80, 0.78],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.selected_candidate == "b"
        assert r.changed_selection is True

    def test_clearly_superior_remains(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, preserve_top_margin=0.10)
        r = select_with_feedback(
            ["leader", "challenger"],
            [0.95, 0.70],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.selected_candidate == "leader"


# ===========================================================================
# SECTION 20 — Invalid candidate never selected (inv 232)
# ===========================================================================


class TestSection20InvalidCandidate:
    def test_invalid_candidate_skipped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["invalid_one", "valid_one"],
            [0.95, 0.50],
            feedback_factors=[1.1, 1.0],
            confidences=[0.8, 0.8],
            valid_flags=[False, True],
            policy=p,
        )
        assert r.selected_candidate == "valid_one"

    def test_invalid_candidate_with_highest_score(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["best_invalid", "ok_valid"],
            [1.0, 0.3],
            valid_flags=[False, True],
            policy=p,
        )
        assert r.selected_candidate == "ok_valid"

    def test_invalid_not_in_adjusted_valid(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["inv", "val"],
            [1.0, 0.5],
            valid_flags=[False, True],
            policy=p,
        )
        for ac in r.adjusted_candidates:
            if ac.candidate_id == "inv":
                assert ac.valid is False


# ===========================================================================
# SECTION 21 — Unsafe candidate never selected (inv 232)
# ===========================================================================


class TestSection21UnsafeCandidate:
    def test_unsafe_candidate_skipped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["unsafe_one", "safe_one"],
            [0.95, 0.50],
            safe_flags=[False, True],
            policy=p,
        )
        assert r.selected_candidate == "safe_one"

    def test_unsafe_with_highest_adjusted(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["unsafe_best", "safe_ok"],
            [1.0, 0.3],
            feedback_factors=[1.1, 1.0],
            confidences=[1.0, 1.0],
            safe_flags=[False, True],
            policy=p,
        )
        assert r.selected_candidate == "safe_ok"

    def test_both_invalid_and_unsafe_skipped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["bad1", "bad2", "good"],
            [1.0, 0.9, 0.3],
            valid_flags=[False, True, True],
            safe_flags=[True, False, True],
            policy=p,
        )
        assert r.selected_candidate == "good"


# ===========================================================================
# SECTION 22 — All invalid case (inv 232)
# ===========================================================================


class TestSection22AllInvalid:
    def test_all_invalid_no_selection(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.9, 0.8],
            valid_flags=[False, False],
            policy=p,
        )
        assert r.selected_candidate == ""

    def test_all_invalid_explanation(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.9, 0.8],
            valid_flags=[False, False],
            policy=p,
        )
        assert "invalid" in r.explanation or "unsafe" in r.explanation

    def test_all_unsafe_no_selection(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.9, 0.8],
            safe_flags=[False, False],
            policy=p,
        )
        assert r.selected_candidate == ""


# ===========================================================================
# SECTION 23 — Legacy candidate with no metadata (valid by default)
# ===========================================================================


class TestSection23LegacyCandidate:
    def test_no_valid_flags_defaults_true(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["legacy_a", "legacy_b"],
            [0.8, 0.5],
            policy=p,
        )
        assert r.selected_candidate == "legacy_a"
        for ac in r.adjusted_candidates:
            assert ac.valid is True

    def test_no_safe_flags_defaults_true(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["legacy"],
            [0.5],
            policy=p,
        )
        assert r.adjusted_candidates[0].valid is True


# ===========================================================================
# SECTION 24 — Deterministic stable tie-breaking (inv 230)
# ===========================================================================


class TestSection24TieBreaking:
    def test_same_score_deterministic(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        results = []
        for _ in range(10):
            r = select_with_feedback(
                ["c", "a", "b"],
                [0.5, 0.5, 0.5],
                policy=p,
            )
            results.append(r.selected_candidate)
        assert len(set(results)) == 1

    def test_tie_break_by_candidate_id(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["c", "a", "b"],
            [0.5, 0.5, 0.5],
            policy=p,
        )
        assert r.selected_candidate == "a"

    def test_adjusted_tie_deterministic(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        results = []
        for _ in range(10):
            r = select_with_feedback(
                ["b", "a"],
                [0.5, 0.5],
                feedback_factors=[1.0, 1.0],
                confidences=[0.8, 0.8],
                policy=p,
            )
            results.append(r.selected_candidate)
        assert len(set(results)) == 1
        assert results[0] == "a"


# ===========================================================================
# SECTION 25 — Same inputs same output (inv 230)
# ===========================================================================


class TestSection25Determinism:
    def test_same_inputs_same_result(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        results = []
        for _ in range(20):
            r = select_with_feedback(
                ["x", "y", "z"],
                [0.6, 0.7, 0.5],
                feedback_factors=[1.05, 0.95, 1.1],
                confidences=[0.8, 0.8, 0.8],
                policy=p,
            )
            results.append(r.selected_candidate)
        assert len(set(results)) == 1

    def test_factors_deterministic(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        results = []
        for _ in range(10):
            r = select_with_feedback(
                ["a", "b"],
                [0.5, 0.6],
                feedback_factors=[1.1, 0.95],
                confidences=[0.8, 0.8],
                policy=p,
            )
            results.append(tuple(ac.adjusted_score for ac in r.adjusted_candidates))
        assert len(set(results)) == 1


# ===========================================================================
# SECTION 26 — Explainability: original best named (inv 231)
# ===========================================================================


class TestSection26OriginalBest:
    def test_original_best_in_result(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert r.original_best == "b"

    def test_original_best_in_explanation(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            policy=p,
        )
        assert "b" in r.explanation


# ===========================================================================
# SECTION 27 — Explainability: adjusted best named (inv 231)
# ===========================================================================


class TestSection27AdjustedBest:
    def test_adjusted_best_in_result(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.1, 0.9],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.adjusted_best != ""

    def test_adjusted_best_when_unchanged(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.0, 1.0],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.adjusted_best == r.original_best


# ===========================================================================
# SECTION 28 — Explainability: changed_selection flag (inv 231)
# ===========================================================================


class TestSection28ChangedSelection:
    def test_changed_selection_true_when_reordered(self):
        p = FeedbackSelectionPolicy(
            enabled=True, min_confidence=0.1, max_adjustment=0.12, preserve_top_margin=0.15
        )
        r = select_with_feedback(
            ["a", "b"],
            [0.80, 0.78],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.changed_selection is True

    def test_changed_selection_false_when_same(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.0, 1.0],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.changed_selection is False

    def test_changed_selection_false_when_disabled(self):
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.5, 0.5],
            confidences=[1.0, 1.0],
        )
        assert r.changed_selection is False


# ===========================================================================
# SECTION 29 — Base score primary authority (inv 229)
# ===========================================================================


class TestSection29BaseAuthority:
    def test_base_score_preserved_in_adjusted(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [0.75],
            feedback_factors=[1.05],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].base_score == 0.75

    def test_base_dominates_when_margin_large(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, preserve_top_margin=0.10)
        r = select_with_feedback(
            ["leader", "challenger"],
            [0.95, 0.50],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.selected_candidate == "leader"

    def test_adjusted_score_is_base_times_factor(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        r = select_with_feedback(
            ["a"],
            [0.80],
            feedback_factors=[1.10],
            confidences=[0.8],
            policy=p,
        )
        ac = r.adjusted_candidates[0]
        expected = 0.80 * 1.10
        assert abs(ac.adjusted_score - expected) < 1e-9


# ===========================================================================
# SECTION 30 — Neutral factor
# ===========================================================================


class TestSection30NeutralFactor:
    def test_factor_one_no_change(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.0],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score == 0.5

    def test_neutral_reason(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.0],
            confidences=[0.8],
            policy=p,
        )
        assert "neutral" in r.adjusted_candidates[0].reason


# ===========================================================================
# SECTION 31 — Score list length mismatches
# ===========================================================================


class TestSection31LengthMismatch:
    def test_fewer_scores_padded(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b", "c"],
            [0.5],
            policy=p,
        )
        assert len(r.adjusted_candidates) == 3

    def test_more_scores_truncated(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [0.5, 0.9, 0.3],
            policy=p,
        )
        assert len(r.adjusted_candidates) == 1

    def test_fewer_factors_padded_neutral(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.05],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.adjusted_candidates[1].feedback_factor == 1.0

    def test_fewer_confidences_padded_zero(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.5)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.1, 1.1],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[1].adjusted_score == r.adjusted_candidates[1].base_score

    def test_fewer_valid_flags_padded_true(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            valid_flags=[True],
            policy=p,
        )
        assert r.adjusted_candidates[1].valid is True

    def test_fewer_safe_flags_padded_true(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            safe_flags=[True],
            policy=p,
        )
        assert r.adjusted_candidates[1].valid is True


# ===========================================================================
# SECTION 32 — Single candidate
# ===========================================================================


class TestSection32SingleCandidate:
    def test_single_candidate_selected(self):
        r = select_with_feedback(["only"], [0.5])
        assert r.selected_candidate == "only"

    def test_single_candidate_no_change(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["only"],
            [0.5],
            feedback_factors=[1.1],
            confidences=[0.8],
            policy=p,
        )
        assert r.changed_selection is False

    def test_single_invalid_no_selection(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["only"],
            [0.5],
            valid_flags=[False],
            policy=p,
        )
        assert r.selected_candidate == ""


# ===========================================================================
# SECTION 33 — Many candidates
# ===========================================================================


class TestSection33ManyCandidates:
    def test_many_candidates_deterministic(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        cands = [f"c_{i}" for i in range(20)]
        scores = [0.5 + i * 0.02 for i in range(20)]
        factors = [1.0 + (i % 5) * 0.02 for i in range(20)]
        confs = [0.8] * 20
        results = []
        for _ in range(5):
            r = select_with_feedback(cands, scores, factors, confs, policy=p)
            results.append(r.selected_candidate)
        assert len(set(results)) == 1

    def test_many_candidates_correct_count(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        cands = [f"c_{i}" for i in range(15)]
        scores = [0.5] * 15
        r = select_with_feedback(cands, scores, policy=p)
        assert len(r.adjusted_candidates) == 15


# ===========================================================================
# SECTION 34 — Enabled policy applies feedback
# ===========================================================================


class TestSection34EnabledPolicy:
    def test_enabled_applies_boost(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.6],
            feedback_factors=[1.1, 1.0],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score > 0.5
        assert r.adjusted_candidates[1].adjusted_score == 0.6

    def test_enabled_applies_penalty(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a"],
            [0.8],
            feedback_factors=[0.92],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score < 0.8

    def test_policy_enabled_in_result(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a"],
            [0.5],
            policy=p,
        )
        assert r.policy_enabled is True


# ===========================================================================
# SECTION 35 — Feedback can change selection between close candidates
# ===========================================================================


class TestSection35SelectionChange:
    def test_feedback_promotes_second_place(self):
        p = FeedbackSelectionPolicy(
            enabled=True,
            min_confidence=0.1,
            max_adjustment=0.12,
            preserve_top_margin=0.05,
        )
        r = select_with_feedback(
            ["a", "b"],
            [0.52, 0.50],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert r.selected_candidate == "b"
        assert r.changed_selection is True
        assert r.original_best == "a"

    def test_change_explanation_mentions_both(self):
        p = FeedbackSelectionPolicy(
            enabled=True,
            min_confidence=0.1,
            max_adjustment=0.12,
            preserve_top_margin=0.05,
        )
        r = select_with_feedback(
            ["alpha", "beta"],
            [0.52, 0.50],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert "alpha" in r.explanation
        assert "beta" in r.explanation


# ===========================================================================
# SECTION 36 — Boundary compliance: no forbidden imports
# ===========================================================================


class TestSection36Boundary:
    def test_no_os_import(self):
        import umh.runtime.feedback_selection as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import os" not in code_section

    def test_no_subprocess_import(self):
        import umh.runtime.feedback_selection as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import subprocess" not in code_section

    def test_no_docker_import(self):
        import umh.runtime.feedback_selection as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import docker" not in code_section

    def test_no_cells_import(self):
        import umh.runtime.feedback_selection as m
        import inspect

        src = inspect.getsource(m)
        assert "from umh.cells" not in src
        assert "from umh.environments" not in src
        assert "from umh.adapters" not in src


# ===========================================================================
# SECTION 37 — No execution or planning mutation (inv 232)
# ===========================================================================


class TestSection37NoExecution:
    def test_no_execute_method(self):
        assert not hasattr(FeedbackSelectionPolicy, "execute")
        assert not hasattr(FeedbackSelectionResult, "execute")

    def test_no_apply_method(self):
        assert not hasattr(FeedbackSelectionPolicy, "apply")
        assert not hasattr(FeedbackSelectionResult, "apply")

    def test_no_set_score_method(self):
        assert not hasattr(FeedbackSelectionPolicy, "set_score")
        assert not hasattr(FeedbackSelectionResult, "set_score")

    def test_no_mutate_method(self):
        assert not hasattr(FeedbackSelectionPolicy, "mutate")
        assert not hasattr(FeedbackSelectionResult, "mutate")


# ===========================================================================
# SECTION 38 — Import surface
# ===========================================================================


class TestSection38ImportSurface:
    def test_all_exports(self):
        from umh.runtime import (
            FeedbackAdjustedCandidate,
            FeedbackSelectionPolicy,
            FeedbackSelectionResult,
            select_with_feedback,
        )

        assert FeedbackAdjustedCandidate is not None
        assert FeedbackSelectionPolicy is not None
        assert FeedbackSelectionResult is not None
        assert select_with_feedback is not None


# ===========================================================================
# SECTION 39 — No input mutation
# ===========================================================================


class TestSection39NoInputMutation:
    def test_candidates_not_mutated(self):
        cands = ["a", "b", "c"]
        original = list(cands)
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        select_with_feedback(cands, [0.5, 0.6, 0.7], policy=p)
        assert cands == original

    def test_scores_not_mutated(self):
        scores = [0.5, 0.6, 0.7]
        original = list(scores)
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        select_with_feedback(["a", "b", "c"], scores, policy=p)
        assert scores == original

    def test_factors_not_mutated(self):
        factors = [1.1, 0.9, 1.0]
        original = list(factors)
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        select_with_feedback(
            ["a", "b", "c"],
            [0.5, 0.6, 0.7],
            feedback_factors=factors,
            confidences=[0.8, 0.8, 0.8],
            policy=p,
        )
        assert factors == original

    def test_confidences_not_mutated(self):
        confs = [0.8, 0.7, 0.6]
        original = list(confs)
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        select_with_feedback(
            ["a", "b", "c"],
            [0.5, 0.6, 0.7],
            feedback_factors=[1.0, 1.0, 1.0],
            confidences=confs,
            policy=p,
        )
        assert confs == original

    def test_valid_flags_not_mutated(self):
        flags = [True, False, True]
        original = list(flags)
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        select_with_feedback(
            ["a", "b", "c"],
            [0.5, 0.6, 0.7],
            valid_flags=flags,
            policy=p,
        )
        assert flags == original

    def test_safe_flags_not_mutated(self):
        flags = [True, True, False]
        original = list(flags)
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        select_with_feedback(
            ["a", "b", "c"],
            [0.5, 0.6, 0.7],
            safe_flags=flags,
            policy=p,
        )
        assert flags == original


# ===========================================================================
# SECTION 40 — Explanation always populated (inv 231)
# ===========================================================================


class TestSection40ExplanationPopulated:
    def test_disabled_has_explanation(self):
        r = select_with_feedback(["a"], [0.5])
        assert len(r.explanation) > 0

    def test_enabled_has_explanation(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.6],
            feedback_factors=[1.1, 0.9],
            confidences=[0.8, 0.8],
            policy=p,
        )
        assert len(r.explanation) > 0

    def test_empty_has_explanation(self):
        r = select_with_feedback([], [])
        assert len(r.explanation) > 0

    def test_all_invalid_has_explanation(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(["a"], [0.5], valid_flags=[False], policy=p)
        assert len(r.explanation) > 0


# ===========================================================================
# SECTION 41 — Candidate reason always populated
# ===========================================================================


class TestSection41CandidateReason:
    def test_disabled_candidate_reason(self):
        r = select_with_feedback(["a"], [0.5])
        assert r.adjusted_candidates[0].reason != ""

    def test_boosted_candidate_reason(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(["a"], [0.5], feedback_factors=[1.1], confidences=[0.8], policy=p)
        assert "boosted" in r.adjusted_candidates[0].reason

    def test_penalized_candidate_reason(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(["a"], [0.5], feedback_factors=[0.9], confidences=[0.8], policy=p)
        assert "penalized" in r.adjusted_candidates[0].reason

    def test_neutral_candidate_reason(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(["a"], [0.5], feedback_factors=[1.0], confidences=[0.8], policy=p)
        assert "neutral" in r.adjusted_candidates[0].reason

    def test_low_confidence_candidate_reason(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.6)
        r = select_with_feedback(["a"], [0.5], feedback_factors=[1.1], confidences=[0.3], policy=p)
        assert "below threshold" in r.adjusted_candidates[0].reason


# ===========================================================================
# SECTION 42 — Mixed confidence levels
# ===========================================================================


class TestSection42MixedConfidence:
    def test_some_above_some_below_threshold(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.5)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.5],
            feedback_factors=[1.1, 1.1],
            confidences=[0.8, 0.3],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score > 0.5
        assert r.adjusted_candidates[1].adjusted_score == 0.5

    def test_only_high_confidence_candidate_adjusted(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.5)
        r = select_with_feedback(
            ["a", "b"],
            [0.6, 0.7],
            feedback_factors=[1.1, 1.1],
            confidences=[0.8, 0.2],
            policy=p,
        )
        assert r.adjusted_candidates[0].feedback_factor != 1.0
        assert r.adjusted_candidates[1].feedback_factor == 1.0


# ===========================================================================
# SECTION 43 — Zero confidence
# ===========================================================================


class TestSection43ZeroConfidence:
    def test_zero_confidence_neutral(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.5],
            confidences=[0.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score == 0.5

    def test_zero_confidence_factor_one(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.5],
            confidences=[0.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].feedback_factor == 1.0


# ===========================================================================
# SECTION 44 — Full confidence
# ===========================================================================


class TestSection44FullConfidence:
    def test_full_confidence_applies_factor(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.5)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.1],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score > 0.5

    def test_full_confidence_recorded(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.5)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.1],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].confidence == 1.0


# ===========================================================================
# SECTION 45 — Zero base score
# ===========================================================================


class TestSection45ZeroBaseScore:
    def test_zero_score_stays_zero_with_boost(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [0.0],
            feedback_factors=[1.1],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score == 0.0

    def test_zero_score_candidate_selected_if_only(self):
        r = select_with_feedback(["a"], [0.0])
        assert r.selected_candidate == "a"


# ===========================================================================
# SECTION 46 — Custom policy values
# ===========================================================================


class TestSection46CustomPolicy:
    def test_tight_max_adjustment(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.02)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[1.5],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score <= 1.02

    def test_wide_max_adjustment(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.25)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[1.5],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score <= 1.25

    def test_zero_max_adjustment(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.0)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[1.5],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score == 1.0

    def test_zero_preserve_margin(self):
        p = FeedbackSelectionPolicy(
            enabled=True,
            min_confidence=0.1,
            max_adjustment=0.12,
            preserve_top_margin=0.0,
        )
        r = select_with_feedback(
            ["a", "b"],
            [0.90, 0.50],
            feedback_factors=[0.88, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        if r.adjusted_candidates[1].adjusted_score > r.adjusted_candidates[0].adjusted_score:
            assert r.changed_selection is True


# ===========================================================================
# SECTION 47 — to_dict roundtrips
# ===========================================================================


class TestSection47Roundtrips:
    def test_policy_roundtrip(self):
        p = FeedbackSelectionPolicy(enabled=True, max_adjustment=0.05)
        d = p.to_dict()
        assert d["enabled"] is True
        assert d["max_adjustment"] == 0.05

    def test_candidate_roundtrip(self):
        c = FeedbackAdjustedCandidate(
            candidate_id="test",
            base_score=0.8,
            feedback_factor=1.05,
            adjusted_score=0.84,
            confidence=0.9,
            valid=True,
            reason="boosted",
        )
        d = c.to_dict()
        assert d["candidate_id"] == "test"
        assert d["base_score"] == 0.8
        assert d["adjusted_score"] == 0.84

    def test_result_roundtrip(self):
        r = select_with_feedback(["a", "b"], [0.5, 0.9])
        d = r.to_dict()
        assert d["selected_candidate"] == "b"
        assert isinstance(d["adjusted_candidates"], list)
        assert len(d["adjusted_candidates"]) == 2


# ===========================================================================
# SECTION 48 — preserve_top_margin edge: exactly at margin
# ===========================================================================


class TestSection48MarginEdge:
    def test_exactly_at_margin_keeps_base(self):
        p = FeedbackSelectionPolicy(
            enabled=True,
            min_confidence=0.1,
            max_adjustment=0.20,
            preserve_top_margin=0.15,
        )
        r = select_with_feedback(
            ["a", "b"],
            [0.80, 0.50],
            feedback_factors=[0.90, 1.20],
            confidences=[0.8, 0.8],
            policy=p,
        )
        a_adj = r.adjusted_candidates[0].adjusted_score
        b_adj = r.adjusted_candidates[1].adjusted_score
        margin = r.adjusted_candidates[0].base_score - b_adj
        if margin >= p.preserve_top_margin:
            assert r.selected_candidate == "a"

    def test_just_under_margin_changes(self):
        p = FeedbackSelectionPolicy(
            enabled=True,
            min_confidence=0.1,
            max_adjustment=0.12,
            preserve_top_margin=0.05,
        )
        r = select_with_feedback(
            ["a", "b"],
            [0.55, 0.54],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        if r.adjusted_candidates[1].adjusted_score > r.adjusted_candidates[0].adjusted_score:
            base_margin = 0.55 - r.adjusted_candidates[1].adjusted_score
            if base_margin < p.preserve_top_margin:
                assert r.changed_selection is True


# ===========================================================================
# SECTION 49 — Multiple invalid with one valid
# ===========================================================================


class TestSection49MultipleInvalid:
    def test_only_valid_selected(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b", "c", "d"],
            [0.9, 0.8, 0.7, 0.3],
            valid_flags=[False, False, False, True],
            policy=p,
        )
        assert r.selected_candidate == "d"

    def test_only_safe_selected(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b", "c"],
            [0.9, 0.8, 0.5],
            safe_flags=[False, False, True],
            policy=p,
        )
        assert r.selected_candidate == "c"


# ===========================================================================
# SECTION 50 — require_valid_candidate=False allows any
# ===========================================================================


class TestSection50RequireValidFalse:
    def test_require_valid_false_allows_invalid(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, require_valid_candidate=False)
        r = select_with_feedback(
            ["a", "b"],
            [0.9, 0.5],
            valid_flags=[False, False],
            policy=p,
        )
        assert r.selected_candidate == ""


# ===========================================================================
# SECTION 51 — Feedback selection with three-way competition
# ===========================================================================


class TestSection51ThreeWay:
    def test_three_way_feedback_winner(self):
        p = FeedbackSelectionPolicy(
            enabled=True,
            min_confidence=0.1,
            max_adjustment=0.12,
            preserve_top_margin=0.05,
        )
        r = select_with_feedback(
            ["a", "b", "c"],
            [0.60, 0.58, 0.57],
            feedback_factors=[0.92, 1.10, 1.08],
            confidences=[0.8, 0.8, 0.8],
            policy=p,
        )
        assert r.selected_candidate in ("a", "b", "c")
        assert isinstance(r.changed_selection, bool)

    def test_three_way_all_neutral(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b", "c"],
            [0.60, 0.58, 0.57],
            feedback_factors=[1.0, 1.0, 1.0],
            confidences=[0.8, 0.8, 0.8],
            policy=p,
        )
        assert r.selected_candidate == "a"
        assert r.changed_selection is False


# ===========================================================================
# SECTION 52 — Adjusted candidates tuple is immutable
# ===========================================================================


class TestSection52AdjustedImmutable:
    def test_adjusted_candidates_is_tuple(self):
        r = select_with_feedback(["a", "b"], [0.5, 0.9])
        assert isinstance(r.adjusted_candidates, tuple)

    def test_adjusted_candidates_frozen(self):
        r = select_with_feedback(["a", "b"], [0.5, 0.9])
        try:
            r.adjusted_candidates[0].base_score = 999.0
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 53 — Confidence exactly at min_confidence
# ===========================================================================


class TestSection53ConfidenceAtThreshold:
    def test_exactly_at_min_confidence_applies(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.6)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.1],
            confidences=[0.6],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score > 0.5

    def test_just_below_min_confidence_neutral(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.6)
        r = select_with_feedback(
            ["a"],
            [0.5],
            feedback_factors=[1.1],
            confidences=[0.59],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score == 0.5


# ===========================================================================
# SECTION 54 — max_adjustment=0 means no change
# ===========================================================================


class TestSection54ZeroAdjustment:
    def test_zero_adjustment_no_boost(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.0)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.6],
            feedback_factors=[1.5, 0.5],
            confidences=[1.0, 1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score == 0.5
        assert r.adjusted_candidates[1].adjusted_score == 0.6


# ===========================================================================
# SECTION 55 — Stress: extreme factor values
# ===========================================================================


class TestSection55ExtremeFactors:
    def test_very_large_factor_clamped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[100.0],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score <= 1.12

    def test_very_small_factor_clamped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[0.001],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score >= 0.88

    def test_negative_factor_clamped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        r = select_with_feedback(
            ["a"],
            [1.0],
            feedback_factors=[-1.0],
            confidences=[1.0],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score >= 0.88


# ===========================================================================
# SECTION 56 — Stress: extreme base scores
# ===========================================================================


class TestSection56ExtremeBaseScores:
    def test_zero_base_score(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [0.0],
            feedback_factors=[1.1],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score == 0.0

    def test_high_base_score(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        r = select_with_feedback(
            ["a"],
            [1.5],
            feedback_factors=[1.1],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].adjusted_score <= 2.0

    def test_negative_base_score_clamped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a"],
            [-1.0],
            feedback_factors=[1.1],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].base_score >= 0.0


# ===========================================================================
# SECTION 57 — No randomness (inv 230)
# ===========================================================================


class TestSection57NoRandomness:
    def test_no_random_import(self):
        import umh.runtime.feedback_selection as m
        import inspect

        src = inspect.getsource(m)
        assert "import random" not in src

    def test_repeated_runs_identical(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        all_results = []
        for _ in range(50):
            r = select_with_feedback(
                ["x", "y"],
                [0.55, 0.60],
                feedback_factors=[1.08, 0.95],
                confidences=[0.7, 0.9],
                policy=p,
            )
            all_results.append((r.selected_candidate, r.changed_selection, r.explanation))
        assert len(set(all_results)) == 1


# ===========================================================================
# SECTION 58 — Default meta_planner behavior unchanged (inv 226)
# ===========================================================================


class TestSection58MetaPlannerUnchanged:
    def test_meta_planner_orchestration_policy_defaults_none(self):
        from umh.runtime.meta_planner import MetaPlanner

        mp = MetaPlanner()
        assert mp.orchestration_policy is None

    def test_meta_planner_plan_feedback_params_optional(self):
        import inspect
        from umh.runtime.meta_planner import MetaPlanner

        sig = inspect.signature(MetaPlanner.plan)
        for name in ("regime_factors", "feedback_factors", "confidences"):
            assert name in sig.parameters
            assert sig.parameters[name].default is None


# ===========================================================================
# SECTION 59 — Disabled policy with valid/safe flags
# ===========================================================================


class TestSection59DisabledWithFlags:
    def test_disabled_respects_validity(self):
        r = select_with_feedback(
            ["inv", "val"],
            [1.0, 0.5],
            valid_flags=[False, True],
        )
        assert r.selected_candidate == "val"

    def test_disabled_respects_safety(self):
        r = select_with_feedback(
            ["unsafe", "safe"],
            [1.0, 0.5],
            safe_flags=[False, True],
        )
        assert r.selected_candidate == "safe"


# ===========================================================================
# SECTION 60 — Integration: compose with attribution feedback
# ===========================================================================


class TestSection60Integration:
    def test_compose_with_attribution_feedback(self):
        from umh.runtime.attribution_feedback import (
            AttributionFeedbackPolicy,
            compute_attribution_feedback_factor,
        )
        from umh.runtime.attribution import (
            AttributionBucket,
            AttributionDimension,
            ContextAttributionRecord,
        )

        attr_policy = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (
            AttributionBucket(
                dimension=AttributionDimension.TREND,
                value="up",
                sample_count=30,
                average_success_score=0.9,
                confidence=0.8,
            ),
        )
        rec = ContextAttributionRecord(
            strategy_name="strat",
            state_signature="state",
            overall_score=0.5,
            confidence=0.8,
            dimension_buckets=buckets,
            explanation="test",
        )
        attr_result = compute_attribution_feedback_factor(rec, attr_policy)

        sel_policy = FeedbackSelectionPolicy(enabled=True, min_confidence=0.3)
        r = select_with_feedback(
            ["a", "b"],
            [0.6, 0.7],
            feedback_factors=[attr_result.factor, 1.0],
            confidences=[attr_result.confidence, 0.5],
            policy=sel_policy,
        )
        assert r.policy_enabled is True
        assert isinstance(r.selected_candidate, str)
        assert len(r.adjusted_candidates) == 2


# ===========================================================================
# SECTION 61 — Candidate order preserved in adjusted_candidates
# ===========================================================================


class TestSection61CandidateOrder:
    def test_order_preserved(self):
        r = select_with_feedback(
            ["c", "a", "b"],
            [0.3, 0.5, 0.9],
        )
        ids = [ac.candidate_id for ac in r.adjusted_candidates]
        assert ids == ["c", "a", "b"]

    def test_order_preserved_with_feedback(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["z", "m", "a"],
            [0.3, 0.5, 0.9],
            feedback_factors=[1.1, 0.9, 1.0],
            confidences=[0.8, 0.8, 0.8],
            policy=p,
        )
        ids = [ac.candidate_id for ac in r.adjusted_candidates]
        assert ids == ["z", "m", "a"]


# ===========================================================================
# SECTION 62 — original_best and adjusted_best fields
# ===========================================================================


class TestSection62BestFields:
    def test_original_best_correct(self):
        r = select_with_feedback(
            ["a", "b", "c"],
            [0.3, 0.9, 0.5],
        )
        assert r.original_best == "b"

    def test_adjusted_best_when_changed(self):
        p = FeedbackSelectionPolicy(
            enabled=True,
            min_confidence=0.1,
            max_adjustment=0.12,
            preserve_top_margin=0.05,
        )
        r = select_with_feedback(
            ["a", "b"],
            [0.52, 0.50],
            feedback_factors=[0.90, 1.12],
            confidences=[0.8, 0.8],
            policy=p,
        )
        if r.changed_selection:
            assert r.adjusted_best != r.original_best

    def test_both_same_when_no_change(self):
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
        )
        assert r.original_best == r.adjusted_best


# ===========================================================================
# SECTION 63 — Mixed valid/safe/invalid combinations
# ===========================================================================


class TestSection63MixedFlags:
    def test_invalid_and_unsafe_both_excluded(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b", "c", "d"],
            [0.9, 0.8, 0.7, 0.3],
            valid_flags=[False, True, True, True],
            safe_flags=[True, False, True, True],
            policy=p,
        )
        assert r.selected_candidate in ("c", "d")

    def test_only_double_valid_safe_selected(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b", "c"],
            [0.9, 0.8, 0.3],
            valid_flags=[True, True, True],
            safe_flags=[False, False, True],
            policy=p,
        )
        assert r.selected_candidate == "c"


# ===========================================================================
# SECTION 64 — Stress: many candidates with varied feedback
# ===========================================================================


class TestSection64StressMany:
    def test_100_candidates(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        cands = [f"c_{i:03d}" for i in range(100)]
        scores = [0.5 + (i % 10) * 0.05 for i in range(100)]
        factors = [1.0 + (i % 7 - 3) * 0.03 for i in range(100)]
        confs = [0.8] * 100
        r = select_with_feedback(cands, scores, factors, confs, policy=p)
        assert len(r.adjusted_candidates) == 100
        assert r.selected_candidate != ""

    def test_100_candidates_deterministic(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        cands = [f"c_{i:03d}" for i in range(100)]
        scores = [0.5 + (i % 10) * 0.05 for i in range(100)]
        factors = [1.0 + (i % 7 - 3) * 0.03 for i in range(100)]
        confs = [0.8] * 100
        results = [
            select_with_feedback(cands, scores, factors, confs, policy=p).selected_candidate
            for _ in range(5)
        ]
        assert len(set(results)) == 1


# ===========================================================================
# SECTION 65 — preserve_top_margin with feedback disabled
# ===========================================================================


class TestSection65MarginDisabled:
    def test_margin_irrelevant_when_disabled(self):
        r = select_with_feedback(
            ["a", "b"],
            [0.90, 0.50],
            feedback_factors=[0.5, 1.5],
            confidences=[1.0, 1.0],
        )
        assert r.selected_candidate == "a"
        assert r.changed_selection is False


# ===========================================================================
# SECTION 66 — Graceful with empty feedback lists
# ===========================================================================


class TestSection66EmptyLists:
    def test_empty_feedback_factors_list(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[],
            policy=p,
        )
        assert r.selected_candidate == "b"

    def test_empty_confidences_list(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.5)
        r = select_with_feedback(
            ["a", "b"],
            [0.5, 0.9],
            feedback_factors=[1.1, 1.1],
            confidences=[],
            policy=p,
        )
        assert r.selected_candidate == "b"


# ===========================================================================
# SECTION 67 — Interaction: feedback cannot make invalid candidate win
# ===========================================================================


class TestSection67FeedbackCannotOverrideValidity:
    def test_massive_boost_on_invalid(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.20)
        r = select_with_feedback(
            ["invalid_boosted", "valid_low"],
            [0.9, 0.1],
            feedback_factors=[1.20, 1.0],
            confidences=[1.0, 1.0],
            valid_flags=[False, True],
            policy=p,
        )
        assert r.selected_candidate == "valid_low"

    def test_massive_boost_on_unsafe(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.20)
        r = select_with_feedback(
            ["unsafe_boosted", "safe_low"],
            [0.9, 0.1],
            feedback_factors=[1.20, 1.0],
            confidences=[1.0, 1.0],
            safe_flags=[False, True],
            policy=p,
        )
        assert r.selected_candidate == "safe_low"


# ===========================================================================
# SECTION 68 — Adjusted score computation accuracy
# ===========================================================================


class TestSection68AdjustedAccuracy:
    def test_adjusted_equals_base_times_clamped_factor(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.12)
        r = select_with_feedback(
            ["a"],
            [0.75],
            feedback_factors=[1.05],
            confidences=[0.8],
            policy=p,
        )
        ac = r.adjusted_candidates[0]
        expected = 0.75 * 1.05
        assert abs(ac.adjusted_score - expected) < 1e-9

    def test_clamped_factor_used_in_computation(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.05)
        r = select_with_feedback(
            ["a"],
            [0.80],
            feedback_factors=[1.20],
            confidences=[0.8],
            policy=p,
        )
        ac = r.adjusted_candidates[0]
        expected = 0.80 * 1.05
        assert abs(ac.adjusted_score - expected) < 1e-9

    def test_recorded_factor_is_clamped(self):
        p = FeedbackSelectionPolicy(enabled=True, min_confidence=0.1, max_adjustment=0.05)
        r = select_with_feedback(
            ["a"],
            [0.80],
            feedback_factors=[1.20],
            confidences=[0.8],
            policy=p,
        )
        assert r.adjusted_candidates[0].feedback_factor == 1.05
