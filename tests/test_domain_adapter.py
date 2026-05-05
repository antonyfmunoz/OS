"""Tests for DomainAdapter — mapping correctness, determinism, no regressions."""

import sys
import types
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.domain_adapter import (
    ActionPlan,
    ActionStep,
    AdaptedInput,
    DomainType,
    MetricMapping,
    adapt_input,
    adapt_output,
    format_observations_as_text,
    get_metric_table,
    list_supported_metrics,
    _extract_action_keywords,
    _resolve_domain,
)
from umh.world.types import Observation


# ─── Test: Domain type resolution ──────────────────────────────────


class TestDomainResolution:
    def test_valid_domains(self):
        assert _resolve_domain("business") == DomainType.BUSINESS
        assert _resolve_domain("creator") == DomainType.CREATOR
        assert _resolve_domain("life") == DomainType.LIFE
        assert _resolve_domain("finance") == DomainType.FINANCE

    def test_case_insensitive(self):
        assert _resolve_domain("BUSINESS") == DomainType.BUSINESS
        assert _resolve_domain("Creator") == DomainType.CREATOR
        assert _resolve_domain("  Life  ") == DomainType.LIFE

    def test_unknown_domain_returns_none(self):
        assert _resolve_domain("gaming") is None
        assert _resolve_domain("") is None
        assert _resolve_domain("unknown") is None


# ─── Test: Metric tables ──────────────────────────────────────────


class TestMetricTables:
    def test_business_has_expected_metrics(self):
        table = get_metric_table(DomainType.BUSINESS)
        assert "revenue" in table
        assert "leads" in table
        assert "churn_rate" in table
        assert "deals_closed" in table

    def test_creator_has_expected_metrics(self):
        table = get_metric_table(DomainType.CREATOR)
        assert "views" in table
        assert "engagement_rate" in table
        assert "followers" in table

    def test_life_has_expected_metrics(self):
        table = get_metric_table(DomainType.LIFE)
        assert "sleep_hours" in table
        assert "energy" in table
        assert "stress" in table

    def test_finance_has_expected_metrics(self):
        table = get_metric_table(DomainType.FINANCE)
        assert "cash_balance" in table
        assert "runway_months" in table

    def test_list_supported_metrics(self):
        metrics = list_supported_metrics(DomainType.BUSINESS)
        assert isinstance(metrics, tuple)
        assert "revenue" in metrics
        assert len(metrics) > 5

    def test_all_mappings_have_valid_fields(self):
        for domain in DomainType:
            table = get_metric_table(domain)
            for name, mapping in table.items():
                assert isinstance(mapping.signal_type, str)
                assert 0.0 <= mapping.base_confidence <= 1.0
                assert mapping.unit in (
                    "usd",
                    "count",
                    "ratio",
                    "score",
                    "hours",
                    "minutes",
                    "seconds",
                    "months",
                )
                assert mapping.direction in ("up_good", "down_good", "neutral")

    def test_no_duplicate_signal_types_within_domain(self):
        for domain in DomainType:
            table = get_metric_table(domain)
            signal_types = [m.signal_type for m in table.values()]
            assert len(signal_types) == len(set(signal_types)), (
                f"Duplicate signal_types in {domain.value}"
            )


# ─── Test: Input adapter ─────────────────────────────────────────


class TestAdaptInput:
    def test_business_metrics(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 5000, "leads": 12},
                "entity_id": "test_venture",
            }
        )
        assert isinstance(result, AdaptedInput)
        assert result.domain == "business"
        assert len(result.observations) == 2
        assert result.unmapped_metrics == ()
        assert "2/2" in result.summary

    def test_observations_are_valid(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 5000},
                "entity_id": "test",
            }
        )
        obs = result.observations[0]
        assert isinstance(obs, Observation)
        assert obs.entity_id == "test"
        assert obs.source == "domain_adapter:business"
        assert obs.signal_type == "financial_revenue"
        assert obs.value == 5000.0
        assert obs.confidence == 0.95
        assert obs.metadata["metric_name"] == "revenue"
        assert obs.metadata["unit"] == "usd"
        assert obs.metadata["direction"] == "up_good"

    def test_confidence_override(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 5000},
                "confidence_overrides": {"revenue": 0.99},
            }
        )
        assert result.observations[0].confidence == 0.99

    def test_confidence_clamped(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 5000},
                "confidence_overrides": {"revenue": 1.5},
            }
        )
        assert result.observations[0].confidence == 1.0

        result2 = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 5000},
                "confidence_overrides": {"revenue": -0.5},
            }
        )
        assert result2.observations[0].confidence == 0.0

    def test_unknown_domain(self):
        result = adapt_input(
            {
                "domain": "gaming",
                "metrics": {"score": 100},
            }
        )
        assert result.observations == ()
        assert result.unmapped_metrics == ("score",)
        assert "Unknown domain" in result.summary

    def test_unknown_metrics_reported(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 5000, "vibes": 100, "aura": 9000},
            }
        )
        assert len(result.observations) == 1
        assert "vibes" in result.unmapped_metrics
        assert "aura" in result.unmapped_metrics

    def test_non_numeric_metrics_skipped(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": "five thousand"},
            }
        )
        assert len(result.observations) == 0
        assert "revenue" in result.unmapped_metrics

    def test_default_entity_id(self):
        result = adapt_input(
            {
                "domain": "creator",
                "metrics": {"views": 1000},
            }
        )
        assert result.observations[0].entity_id == "creator"

    def test_timestamp_turn(self):
        result = adapt_input(
            {
                "domain": "life",
                "metrics": {"sleep_hours": 7.5},
            },
            timestamp_turn=42,
        )
        assert result.observations[0].timestamp_turn == 42

    def test_empty_metrics(self):
        result = adapt_input({"domain": "business", "metrics": {}})
        assert result.observations == ()
        assert result.unmapped_metrics == ()
        assert "0/0" in result.summary

    def test_all_domains_produce_observations(self):
        test_metrics = {
            "business": {"revenue": 1000},
            "creator": {"views": 500},
            "life": {"sleep_hours": 8},
            "finance": {"cash_balance": 10000},
        }
        for domain, metrics in test_metrics.items():
            result = adapt_input({"domain": domain, "metrics": metrics})
            assert len(result.observations) == 1, f"Failed for domain {domain}"

    def test_churn_rate_direction(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"churn_rate": 0.08},
            }
        )
        obs = result.observations[0]
        assert obs.metadata["direction"] == "down_good"

    def test_to_dict_roundtrip(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 5000, "leads": 12},
            }
        )
        d = result.to_dict()
        assert d["domain"] == "business"
        assert len(d["observations"]) == 2
        assert isinstance(d["observations"][0], dict)


# ─── Test: Output adapter ─────────────────────────────────────────


def _mock_decision(action_text, confidence=0.8, risk_score=0.2):
    return types.SimpleNamespace(
        action=action_text,
        confidence=confidence,
        risk_score=risk_score,
    )


class TestAdaptOutput:
    def test_business_explore(self):
        decision = _mock_decision("We should increase exploration in outreach")
        plan = adapt_output(decision, DomainType.BUSINESS)
        assert isinstance(plan, ActionPlan)
        assert plan.domain == "business"
        assert len(plan.steps) > 0
        instructions = [s.instruction for s in plan.steps]
        assert any("marketing channels" in i for i in instructions)

    def test_business_outreach(self):
        decision = _mock_decision("increase outreach volume")
        plan = adapt_output(decision, DomainType.BUSINESS)
        assert len(plan.steps) > 0
        assert any("outreach" in s.category for s in plan.steps)

    def test_creator_explore(self):
        decision = _mock_decision("explore new content formats")
        plan = adapt_output(decision, DomainType.CREATOR)
        assert len(plan.steps) > 0
        instructions = [s.instruction for s in plan.steps]
        assert any("content" in i.lower() for i in instructions)

    def test_life_stabilize(self):
        decision = _mock_decision("stabilize current routine")
        plan = adapt_output(decision, DomainType.LIFE)
        assert len(plan.steps) > 0
        assert any("sleep" in s.instruction.lower() for s in plan.steps)

    def test_finance_reduce_risk(self):
        decision = _mock_decision("reduce risk in portfolio")
        plan = adapt_output(decision, DomainType.FINANCE)
        assert len(plan.steps) > 0

    def test_no_matching_keywords(self):
        decision = _mock_decision("ponder the meaning of existence")
        plan = adapt_output(decision, DomainType.BUSINESS)
        assert len(plan.steps) == 0
        assert plan.raw_action == "ponder the meaning of existence"

    def test_multiple_keywords_matched(self):
        decision = _mock_decision("optimize outreach and reduce churn")
        plan = adapt_output(decision, DomainType.BUSINESS)
        keywords = [s.source_keyword for s in plan.steps]
        assert len(keywords) >= 2

    def test_steps_sorted_by_priority(self):
        decision = _mock_decision("stabilize and then increase outreach")
        plan = adapt_output(decision, DomainType.BUSINESS)
        if len(plan.steps) >= 2:
            priorities = [s.priority for s in plan.steps]
            assert priorities == sorted(priorities)

    def test_confidence_and_risk_passed_through(self):
        decision = _mock_decision("explore", confidence=0.9, risk_score=0.1)
        plan = adapt_output(decision, DomainType.BUSINESS)
        assert plan.confidence == 0.9
        assert plan.risk_score == 0.1

    def test_cross_domain_keyword_isolation(self):
        decision = _mock_decision("increase exploration")
        biz_plan = adapt_output(decision, DomainType.BUSINESS)
        creator_plan = adapt_output(decision, DomainType.CREATOR)
        assert biz_plan.steps[0].instruction != creator_plan.steps[0].instruction

    def test_to_dict_roundtrip(self):
        decision = _mock_decision("optimize and explore")
        plan = adapt_output(decision, DomainType.BUSINESS)
        d = plan.to_dict()
        assert d["domain"] == "business"
        assert isinstance(d["steps"], list)
        assert isinstance(d["raw_action"], str)

    def test_empty_action(self):
        decision = _mock_decision("")
        plan = adapt_output(decision, DomainType.BUSINESS)
        assert len(plan.steps) == 0

    def test_action_step_is_frozen(self):
        step = ActionStep(
            instruction="test",
            category="test",
            priority=1,
            source_keyword="test",
        )
        try:
            step.instruction = "modified"
            assert False, "Should not allow mutation"
        except AttributeError:
            pass


# ─── Test: Keyword extraction ─────────────────────────────────────


class TestKeywordExtraction:
    def test_multi_word_keywords(self):
        keywords = _extract_action_keywords("we should increase exploration now")
        assert "increase exploration" in keywords

    def test_single_word_keywords(self):
        keywords = _extract_action_keywords("optimize the funnel")
        assert "optimize" in keywords

    def test_longer_phrases_match_first(self):
        keywords = _extract_action_keywords("increase exploration in channels")
        assert keywords.index("increase exploration") < len(keywords)

    def test_no_duplicates(self):
        keywords = _extract_action_keywords("explore and explore more exploration")
        assert len(keywords) == len(set(keywords))

    def test_case_insensitive(self):
        keywords = _extract_action_keywords("OPTIMIZE Everything")
        assert "optimize" in keywords


# ─── Test: Text formatter ─────────────────────────────────────────


class TestFormatObservationsAsText:
    def test_business_formatting(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 5000, "churn_rate": 0.08},
            }
        )
        text = format_observations_as_text(result)
        assert "Domain: business" in text
        assert "$5,000.00" in text
        assert "8.0%" in text

    def test_life_formatting(self):
        result = adapt_input(
            {
                "domain": "life",
                "metrics": {"sleep_hours": 7.5, "energy": 8},
            }
        )
        text = format_observations_as_text(result)
        assert "7.5 hours" in text

    def test_direction_labels(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 1000, "churn_rate": 0.05},
            }
        )
        text = format_observations_as_text(result)
        assert "(higher is better)" in text
        assert "(lower is better)" in text

    def test_unmapped_mentioned(self):
        result = adapt_input(
            {
                "domain": "business",
                "metrics": {"revenue": 1000, "vibes": 100},
            }
        )
        text = format_observations_as_text(result)
        assert "vibes" in text

    def test_empty_observations(self):
        result = adapt_input({"domain": "unknown_domain", "metrics": {"x": 1}})
        text = format_observations_as_text(result)
        assert "Unknown domain" in text


# ─── Test: Determinism ────────────────────────────────────────────


class TestDeterminism:
    def test_input_adapter_deterministic_structure(self):
        """Same input produces same structure (observation_ids differ by design)."""
        raw = {
            "domain": "business",
            "metrics": {"revenue": 5000, "leads": 12},
            "entity_id": "test",
        }
        r1 = adapt_input(raw)
        r2 = adapt_input(raw)
        assert r1.domain == r2.domain
        assert r1.unmapped_metrics == r2.unmapped_metrics
        assert len(r1.observations) == len(r2.observations)
        for o1, o2 in zip(r1.observations, r2.observations):
            assert o1.signal_type == o2.signal_type
            assert o1.value == o2.value
            assert o1.confidence == o2.confidence
            assert o1.entity_id == o2.entity_id

    def test_output_adapter_deterministic(self):
        decision = _mock_decision("optimize and explore")
        p1 = adapt_output(decision, DomainType.BUSINESS)
        p2 = adapt_output(decision, DomainType.BUSINESS)
        assert p1.steps == p2.steps
        assert p1.unmapped_keywords == p2.unmapped_keywords

    def test_keyword_extraction_deterministic(self):
        text = "increase outreach and optimize the funnel"
        k1 = _extract_action_keywords(text)
        k2 = _extract_action_keywords(text)
        assert k1 == k2


# ─── Test: Integration with SessionInterface ──────────────────────


class TestSessionInterfaceIntegration:
    def _make_interface(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._session_id = "test-session"
        iface._ctx = MagicMock()
        iface._ctx.org_id = "org-123"
        iface._decisions = []
        iface._intent = None
        iface._last_adapted_input = None
        iface._control_enabled = True
        iface._calibration_enabled = True
        iface._convergence_enabled = True
        iface._persist_memory = False

        runtime = MagicMock()
        runtime.stats = MagicMock()
        runtime.stats.turns = 1
        runtime.stats.total_cost_usd = 0.0
        runtime.get_calibrated_thresholds = MagicMock(return_value=None)
        runtime.get_last_trace = MagicMock(return_value=None)
        runtime.get_last_control_decision = MagicMock(return_value=None)
        runtime._compiled_intent = None

        spine_result = MagicMock()
        spine_result.__str__ = lambda self: "Focus on outreach"
        spine_result.model_used = "test"
        spine_result.latency_ms = 100
        spine_result.tokens_used = {"input": 50, "output": 100, "total": 150}
        spine_result.cost_usd = 0.001
        runtime.run = MagicMock(return_value=spine_result)

        builder = MagicMock()
        builder.build = MagicMock(return_value=MagicMock())

        iface._runtime = runtime
        iface._builder = builder
        return iface

    def test_step_with_dict_input(self):
        iface = self._make_interface()
        output = iface.step(
            {
                "domain": "business",
                "metrics": {"revenue": 5000, "leads": 12},
                "entity_id": "lyfe_institute",
            }
        )
        assert output is not None
        assert output.action == "Focus on outreach"

        # Verify the runtime received a string, not a dict
        call_args = iface._runtime.run.call_args
        assert isinstance(call_args.kwargs["message"], str)
        assert "revenue" in call_args.kwargs["message"]

    def test_step_with_string_input_unchanged(self):
        iface = self._make_interface()
        output = iface.step("What should I do today?")
        assert output is not None

        call_args = iface._runtime.run.call_args
        assert call_args.kwargs["message"] == "What should I do today?"

    def test_adapted_input_stored(self):
        iface = self._make_interface()
        iface.step(
            {
                "domain": "business",
                "metrics": {"revenue": 5000},
            }
        )
        assert iface._last_adapted_input is not None
        assert iface._last_adapted_input.domain == "business"

    def test_string_step_clears_adapted_input(self):
        iface = self._make_interface()
        iface.step(
            {
                "domain": "business",
                "metrics": {"revenue": 5000},
            }
        )
        assert iface._last_adapted_input is not None
        iface._runtime.stats.turns = 2
        iface.step("plain text")
        assert iface._last_adapted_input is None


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
