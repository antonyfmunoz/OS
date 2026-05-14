"""Migration pin: salience pipeline (scripts/).

Pins §34 item: Salience pipeline for EOS memory (conversation
logging, salience scoring, consolidation, promotion thresholds,
Neon metadata).

The pipeline lives in scripts/ (operator tooling), not runtime/.
This is architecturally correct — salience is a batch concern.
Discovered via 2026-05-13 salience audit.
"""

import os
import sys

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

pytestmark = pytest.mark.migration


class TestSalienceImports:
    def test_salience_module_importable(self):
        from operations.memory.salience import score_summary, score_cross_session

        assert score_summary is not None
        assert score_cross_session is not None

    def test_salience_result_class(self):
        from operations.memory.salience import SalienceResult

        result = SalienceResult(score=50, label="medium")
        assert result.score == 50
        assert result.label == "medium"
        assert result.promotion_recommendation == "skip"
        assert result.consolidation_recommendation == "index"

    def test_cross_session_result_class(self):
        from operations.memory.salience import CrossSessionResult

        result = CrossSessionResult(score=0)
        assert result.score == 0
        assert result.compounded_recommendation == "none"


class TestSalienceScoring:
    def test_empty_parsed_scores_zero(self):
        from operations.memory.salience import score_summary

        result = score_summary({})
        assert result.score == 0
        assert result.label == "low"

    def test_decisions_boost_score(self):
        from operations.memory.salience import score_summary

        parsed = {"decisions": ["switched to Groq", "disabled Anthropic"]}
        result = score_summary(parsed)
        assert result.score >= 20
        assert "decision" in result.reasons[0].lower()

    def test_high_score_gets_promote_recommendation(self):
        from operations.memory.salience import score_summary

        parsed = {
            "decisions": ["a", "b", "c"],
            "constraints": ["x", "y"],
            "wiki_candidates": [{"title": "test"}],
        }
        result = score_summary(parsed)
        assert result.label in ("high", "critical")
        assert result.promotion_recommendation in ("promote", "must_promote")

    def test_score_bands(self):
        from operations.memory.salience import BANDS

        assert BANDS[0][1] == "critical"
        assert BANDS[-1][1] == "low"

    def test_consolidation_recommendations(self):
        from operations.memory.salience import _consolidation_recommendation

        assert _consolidation_recommendation("critical") == "promote"
        assert _consolidation_recommendation("high") == "promote"
        assert _consolidation_recommendation("medium") == "summarize"
        assert _consolidation_recommendation("low") == "index"


class TestFindRepeatedNoneGuard:
    def test_none_current_items_returns_empty(self):
        from operations.memory.salience import _find_repeated

        result = _find_repeated(None, [{"entities": ["foo"]}], "entities")
        assert result == []

    def test_empty_current_items_returns_empty(self):
        from operations.memory.salience import _find_repeated

        result = _find_repeated([], [{"entities": ["foo"]}], "entities")
        assert result == []

    def test_finds_repeated_entity(self):
        from operations.memory.salience import _find_repeated

        past = [{"entities": ["model_router", "gateway"]}]
        current = ["model_router"]
        result = _find_repeated(current, past, "entities")
        assert "model_router" in result


class TestNightlyConsolidation:
    def test_nightly_consolidation_importable(self):
        from operations.memory.nightly_consolidation import run_summarization, run_promotion

        assert run_summarization is not None
        assert run_promotion is not None


class TestPromoteToWiki:
    def test_should_promote_importable(self):
        from operations.memory.promote_to_wiki import should_promote

        assert should_promote is not None

    def test_low_salience_not_promoted(self):
        from operations.memory.promote_to_wiki import should_promote

        candidate = {"name": "test-entity", "page_type": "entity"}
        ok, reason = should_promote(
            candidate, existing_pages=set(), already_promoted=[],
            salience_label="low",
        )
        assert ok is False
        assert "low" in reason


class TestMemoryNeon:
    def test_memory_neon_importable(self):
        from operations.memory.memory_neon import record_summary_created

        assert record_summary_created is not None

    def test_search_summaries_importable(self):
        from operations.memory.memory_neon import search_summaries

        assert search_summaries is not None
