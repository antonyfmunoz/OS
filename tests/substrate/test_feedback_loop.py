"""Tests for substrate.execution.feedback_loop — RLHF feedback ingestion + learning cycle.

The feedback_loop module imports substrate.state.storage.db at module level, which
requires DATABASE_URL env var. We mock the db module before importing feedback_loop.
"""

import sys
from datetime import datetime, timezone
from types import ModuleType
from unittest.mock import MagicMock, patch

# ─── Mock the db module before feedback_loop imports it ──────────────────────
_mock_db = ModuleType("substrate.state.storage.db")
_mock_db.get_conn = MagicMock()
_mock_db.ORG_ID = "test-org-id"
_mock_db.USER_ID = "test-user-id"
_mock_db.resolve_venture = MagicMock(return_value=None)
_mock_db.resolve_skill = MagicMock(return_value=None)
sys.modules["substrate.state.storage.db"] = _mock_db


from substrate.execution.feedback_loop import (  # noqa: E402
    _CATEGORY_TO_NEON,
    _RATING_SCORE,
    FeedbackEntry,
    FeedbackLoop,
    OutcomeCategory,
    Rating,
    get_feedback_loop,
)

# ─── Rating/Category mapping tests ──────────────────────────────────────────


class TestRating:
    def test_thumbs_up_score_is_1(self):
        assert _RATING_SCORE[Rating.THUMBS_UP] == 1.0

    def test_thumbs_down_score_is_0(self):
        assert _RATING_SCORE[Rating.THUMBS_DOWN] == 0.0

    def test_numeric_ratings_are_ordered(self):
        scores = [_RATING_SCORE[Rating(str(i))] for i in range(1, 6)]
        assert scores == sorted(scores)
        assert scores[0] == 0.2
        assert scores[-1] == 1.0

    def test_all_ratings_have_scores(self):
        for r in Rating:
            assert r in _RATING_SCORE


class TestOutcomeCategory:
    def test_helpful_maps_to_positive(self):
        assert _CATEGORY_TO_NEON[OutcomeCategory.HELPFUL] == "positive"

    def test_harmful_maps_to_negative(self):
        assert _CATEGORY_TO_NEON[OutcomeCategory.HARMFUL] == "negative"

    def test_incorrect_maps_to_negative(self):
        assert _CATEGORY_TO_NEON[OutcomeCategory.INCORRECT] == "negative"

    def test_unhelpful_maps_to_neutral(self):
        assert _CATEGORY_TO_NEON[OutcomeCategory.UNHELPFUL] == "neutral"

    def test_all_categories_mapped(self):
        for cat in OutcomeCategory:
            assert cat in _CATEGORY_TO_NEON


# ─── FeedbackEntry tests ────────────────────────────────────────────────────


class TestFeedbackEntry:
    def test_create_entry(self):
        entry = FeedbackEntry(
            interaction_id="abc-123",
            rating=Rating.THUMBS_UP,
            outcome_type=OutcomeCategory.HELPFUL,
        )
        assert entry.interaction_id == "abc-123"
        assert entry.rating == Rating.THUMBS_UP
        assert entry.outcome_type == OutcomeCategory.HELPFUL
        assert entry.notes == ""
        assert isinstance(entry.timestamp, datetime)

    def test_entry_with_notes(self):
        entry = FeedbackEntry(
            interaction_id="xyz-456",
            rating=Rating.NUMERIC_3,
            outcome_type=OutcomeCategory.UNHELPFUL,
            notes="Response was too generic",
        )
        assert entry.notes == "Response was too generic"
        assert entry.rating == Rating.NUMERIC_3

    def test_entry_timestamp_is_utc(self):
        entry = FeedbackEntry(
            interaction_id="test",
            rating=Rating.THUMBS_DOWN,
            outcome_type=OutcomeCategory.INCORRECT,
        )
        assert entry.timestamp.tzinfo == timezone.utc


# ─── FeedbackLoop.record_feedback tests ─────────────────────────────────────


class TestRecordFeedback:
    @patch("substrate.execution.feedback_loop.get_conn")
    def test_record_success(self, mock_get_conn):
        """record_feedback returns True when the interaction exists and insert succeeds."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"id": "abc-123"}
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        loop = FeedbackLoop()
        entry = FeedbackEntry(
            interaction_id="abc-123",
            rating=Rating.THUMBS_UP,
            outcome_type=OutcomeCategory.HELPFUL,
            notes="Great response",
        )
        result = loop.record_feedback(entry)
        assert result is True

        # Verify the SELECT check happened
        calls = mock_cur.execute.call_args_list
        assert len(calls) == 2
        assert "SELECT id FROM interactions" in calls[0][0][0]

        # Verify the INSERT happened with correct outcome_type mapping
        insert_sql = calls[1][0][0]
        assert "INSERT INTO outcomes" in insert_sql
        insert_params = calls[1][0][1]
        assert insert_params[2] == "positive"  # _CATEGORY_TO_NEON[HELPFUL]
        assert insert_params[3] == "helpful"  # outcome_label
        assert insert_params[4] == 1.0  # thumbs_up score

    @patch("substrate.execution.feedback_loop.get_conn")
    def test_record_missing_interaction(self, mock_get_conn):
        """record_feedback returns False when interaction not found."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        loop = FeedbackLoop()
        entry = FeedbackEntry(
            interaction_id="nonexistent",
            rating=Rating.THUMBS_DOWN,
            outcome_type=OutcomeCategory.HARMFUL,
        )
        result = loop.record_feedback(entry)
        assert result is False

    @patch("substrate.execution.feedback_loop.get_conn")
    def test_record_db_error_returns_false(self, mock_get_conn):
        """record_feedback returns False on database error."""
        mock_get_conn.side_effect = Exception("connection refused")

        loop = FeedbackLoop()
        entry = FeedbackEntry(
            interaction_id="abc",
            rating=Rating.NUMERIC_2,
            outcome_type=OutcomeCategory.INCORRECT,
        )
        result = loop.record_feedback(entry)
        assert result is False

    @patch("substrate.execution.feedback_loop.get_conn")
    def test_notes_include_rlhf_tag(self, mock_get_conn):
        """Notes saved to DB are prefixed with [rlhf:<rating>]."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"id": "abc"}
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        loop = FeedbackLoop()
        entry = FeedbackEntry(
            interaction_id="abc",
            rating=Rating.NUMERIC_4,
            outcome_type=OutcomeCategory.HELPFUL,
            notes="Solid answer",
        )
        loop.record_feedback(entry)

        insert_call = mock_cur.execute.call_args_list[1]
        notes_param = insert_call[0][1][5]  # 6th param is notes
        assert notes_param.startswith("[rlhf:4]")
        assert "Solid answer" in notes_param


# ─── FeedbackLoop.get_feedback_stats tests ───────────────────────────────────


class TestGetFeedbackStats:
    @patch("substrate.execution.feedback_loop.get_conn")
    def test_stats_structure(self, mock_get_conn):
        """get_feedback_stats returns expected keys."""
        mock_cur = MagicMock()
        # 3 queries: totals, by_agent, by_label
        mock_cur.fetchone.return_value = {
            "total": 10,
            "positive_count": 7,
            "negative_count": 2,
            "neutral_count": 1,
        }
        mock_cur.fetchall.side_effect = [
            [
                {
                    "agent_label": "eos-sales",
                    "total": 10,
                    "positive": 7,
                    "negative": 2,
                    "neutral": 1,
                }
            ],
            [{"outcome_label": "helpful", "count": 7}, {"outcome_label": "incorrect", "count": 2}],
        ]
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        loop = FeedbackLoop()
        stats = loop.get_feedback_stats()

        assert stats["total"] == 10
        assert stats["positive_rate"] == 0.7
        assert stats["positive"] == 7
        assert stats["negative"] == 2
        assert stats["neutral"] == 1
        assert "eos-sales" in stats["by_agent"]
        assert "helpful" in stats["by_outcome_type"]

    @patch("substrate.execution.feedback_loop.get_conn")
    def test_stats_on_error_returns_zeros(self, mock_get_conn):
        """get_feedback_stats returns zero-filled dict on error."""
        mock_get_conn.side_effect = Exception("db down")

        loop = FeedbackLoop()
        stats = loop.get_feedback_stats()

        assert stats["total"] == 0
        assert stats["positive_rate"] == 0.0
        assert "error" in stats


# ─── FeedbackLoop.skill_effectiveness tests ──────────────────────────────────


class TestSkillEffectiveness:
    @patch("substrate.execution.feedback_loop.get_conn")
    def test_skill_effectiveness_structure(self, mock_get_conn):
        """skill_effectiveness returns expected shape."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {
            "total_interactions": 20,
            "feedback_count": 8,
            "positive": 6,
            "negative": 1,
            "neutral": 1,
            "avg_score": 0.75,
        }
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        loop = FeedbackLoop()
        result = loop.skill_effectiveness("eos-sales", "analyze_icp_signal", 30)

        assert result["agent"] == "eos-sales"
        assert result["skill"] == "analyze_icp_signal"
        assert result["window_days"] == 30
        assert result["total_interactions"] == 20
        assert result["feedback_count"] == 8
        assert result["positive_rate"] == 0.75
        assert result["avg_score"] == 0.75
        assert result["outcome_distribution"]["positive"] == 6

    @patch("substrate.execution.feedback_loop.get_conn")
    def test_skill_effectiveness_on_error(self, mock_get_conn):
        """skill_effectiveness returns zeros on db failure."""
        mock_get_conn.side_effect = Exception("timeout")

        loop = FeedbackLoop()
        result = loop.skill_effectiveness("x", "y")
        assert result["total_interactions"] == 0
        assert "error" in result


# ─── FeedbackLoop.recommend_routing_adjustment tests ─────────────────────────


class TestRecommendRoutingAdjustment:
    @patch("substrate.execution.feedback_loop.get_conn")
    def test_underperforming_agent_detected(self, mock_get_conn):
        """Agent with < 40% positive rate triggers recommendation."""
        mock_cur = MagicMock()
        # 3 queries: rule1 agents, rule2 skills, rule3 no-feedback
        mock_cur.fetchall.side_effect = [
            [
                {
                    "agent_label": "bad-agent",
                    "feedback_count": 15,
                    "positive": 3,
                    "avg_score": 0.25,
                }
            ],
            [],
            [],
        ]
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        loop = FeedbackLoop()
        recs = loop.recommend_routing_adjustment()

        assert len(recs) == 1
        assert recs[0]["type"] == "agent_underperforming"
        assert recs[0]["agent"] == "bad-agent"
        assert recs[0]["positive_rate"] == 0.2

    @patch("substrate.execution.feedback_loop.get_conn")
    def test_no_feedback_agent_detected(self, mock_get_conn):
        """Agent with many interactions but 0 RLHF feedback triggers recommendation."""
        mock_cur = MagicMock()
        mock_cur.fetchall.side_effect = [
            [],
            [],
            [{"agent_label": "quiet-agent", "interaction_count": 50, "rlhf_count": 0}],
        ]
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        loop = FeedbackLoop()
        recs = loop.recommend_routing_adjustment()

        assert len(recs) == 1
        assert recs[0]["type"] == "no_feedback"
        assert recs[0]["agent"] == "quiet-agent"

    @patch("substrate.execution.feedback_loop.get_conn")
    def test_empty_when_all_good(self, mock_get_conn):
        """No recommendations when all agents perform well."""
        mock_cur = MagicMock()
        mock_cur.fetchall.side_effect = [[], [], []]
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        loop = FeedbackLoop()
        recs = loop.recommend_routing_adjustment()
        assert recs == []

    @patch("substrate.execution.feedback_loop.get_conn")
    def test_db_error_returns_error_recommendation(self, mock_get_conn):
        """DB failure produces an error recommendation instead of crashing."""
        mock_get_conn.side_effect = Exception("connection lost")

        loop = FeedbackLoop()
        recs = loop.recommend_routing_adjustment()
        assert len(recs) == 1
        assert recs[0]["type"] == "error"


# ─── Singleton tests ────────────────────────────────────────────────────────


class TestSingleton:
    def test_get_feedback_loop_returns_same_instance(self):
        """get_feedback_loop() returns the same object on repeated calls."""
        import substrate.execution.feedback_loop as mod

        mod._instance = None  # reset
        a = get_feedback_loop()
        b = get_feedback_loop()
        assert a is b
        mod._instance = None  # cleanup

    def test_singleton_is_feedback_loop(self):
        """Singleton is an instance of FeedbackLoop."""
        import substrate.execution.feedback_loop as mod

        mod._instance = None
        loop = get_feedback_loop()
        assert isinstance(loop, FeedbackLoop)
        mod._instance = None
