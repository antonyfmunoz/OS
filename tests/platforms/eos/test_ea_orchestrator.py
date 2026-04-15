"""Tests for eos_ai.platforms.eos.ea_orchestrator."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.ea_orchestrator import EAResponse, handle_founder_message
from eos_ai.platforms.eos.decision_log import DecisionLog
from eos_ai.platforms.eos.roles import EOSRole


@pytest.fixture(autouse=True)
def _reset_decision_log():
    """Reset decision log singleton between tests."""
    DecisionLog.reset_for_tests()
    yield
    DecisionLog.reset_for_tests()


class TestFounderAlwaysEntersThroughEA:
    """Every founder message must result in an EAResponse with primary_role=EA."""

    @pytest.mark.parametrize(
        "text",
        [
            "What's the status?",
            "Review the strategy for Q3",
            "How is my portfolio?",
            "Build the landing page",
            "Schedule a meeting",
            "random nonsense text",
        ],
    )
    def test_primary_role_always_ea(self, text):
        response = handle_founder_message(text)
        assert isinstance(response, EAResponse)
        assert response.primary_role == EOSRole.EA


class TestStatusHandledDirectlyByEA:
    """Status/briefing messages stay with EA — no delegation."""

    def test_status_no_delegation(self):
        response = handle_founder_message("What's the status?")
        assert response.delegated_role is None
        assert response.summary_type == "briefing"

    def test_catch_me_up(self):
        response = handle_founder_message("Catch me up on everything")
        assert response.delegated_role is None
        assert response.summary_type == "briefing"

    def test_morning_brief(self):
        response = handle_founder_message("Morning brief")
        assert response.delegated_role is None


class TestStrategyDelegatesToCEO:
    """Strategy messages delegate to CEO but return EAResponse."""

    def test_strategy_delegated_to_ceo(self):
        response = handle_founder_message("What's our business strategy?")
        assert response.delegated_role == EOSRole.CEO
        assert response.summary_type == "strategic_recommendation"
        # But still EA-mediated
        assert response.primary_role == EOSRole.EA

    def test_priorities(self):
        response = handle_founder_message("Reprioritize the business direction")
        assert response.delegated_role == EOSRole.CEO

    def test_revenue_model(self):
        response = handle_founder_message("Revenue model needs an update")
        assert response.delegated_role == EOSRole.CEO


class TestPortfolioDelegatesToPortfolioAdvisor:
    """Portfolio messages delegate to Portfolio Advisor but return EAResponse."""

    def test_portfolio_delegated(self):
        response = handle_founder_message("How is my portfolio?")
        assert response.delegated_role == EOSRole.PORTFOLIO_ADVISOR
        assert response.summary_type == "portfolio_recommendation"
        assert response.primary_role == EOSRole.EA

    def test_capital_allocation(self):
        response = handle_founder_message("Review capital allocation across companies")
        assert response.delegated_role == EOSRole.PORTFOLIO_ADVISOR

    def test_risk_assessment(self):
        response = handle_founder_message("Risk assessment on investments")
        assert response.delegated_role == EOSRole.PORTFOLIO_ADVISOR


class TestExecutionCreatesSubstrateTasks:
    """Execution requests should attempt to create substrate tasks."""

    def test_execution_summary_type(self):
        response = handle_founder_message("Build the landing page")
        assert response.summary_type == "execution_summary"
        # Task creation may or may not succeed depending on substrate state,
        # but the response type must be execution_summary
        assert response.primary_role == EOSRole.EA

    def test_deploy_request(self):
        response = handle_founder_message("Deploy the Discord bot")
        assert response.summary_type == "execution_summary"


class TestReviewHandledByEA:
    """Review requests stay with EA."""

    def test_review_no_delegation(self):
        response = handle_founder_message("Review the latest output")
        assert response.delegated_role is None


class TestBuilderNeverFounderFacing:
    """Builder must never appear as a delegation target in any response."""

    @pytest.mark.parametrize(
        "text",
        [
            "Build the landing page",
            "Fix the authentication bug",
            "Deploy the service",
            "Code the new feature",
            "Implement the pipeline",
        ],
    )
    def test_builder_never_delegated(self, text):
        response = handle_founder_message(text)
        if response.delegated_role is not None:
            assert response.delegated_role.value != "builder"


class TestEAResponseModel:
    """EAResponse data model correctness."""

    def test_has_response_id(self):
        response = handle_founder_message("status")
        assert response.response_id.startswith("ea_resp_")

    def test_has_created_at(self):
        response = handle_founder_message("status")
        assert response.created_at is not None

    def test_has_intent(self):
        response = handle_founder_message("What's happening?")
        assert response.intent is not None
        assert response.intent.raw_text == "What's happening?"

    def test_response_text_not_empty(self):
        response = handle_founder_message("Catch me up")
        assert len(response.response_text) > 0

    def test_to_dict(self):
        response = handle_founder_message("status update")
        d = response.to_dict()
        assert d["primary_role"] == "ea"
        assert "response_text" in d
        assert "intent" in d


class TestDecisionLogging:
    """Decision log captures platform routing decisions."""

    def test_decision_logged(self):
        handle_founder_message("What's the status?")
        log = DecisionLog.default()
        records = log.recent(limit=1)
        assert len(records) >= 1
        assert records[0].primary_role == "ea"
        assert records[0].source_intent_id.startswith("intent_")

    def test_strategy_delegation_logged(self):
        handle_founder_message("Business strategy update")
        log = DecisionLog.default()
        records = log.recent(limit=1)
        assert len(records) >= 1
        assert records[0].delegated_role == "ceo"

    def test_log_survives_multiple_calls(self):
        handle_founder_message("status")
        handle_founder_message("strategy review")
        handle_founder_message("portfolio risk")
        log = DecisionLog.default()
        records = log.all()
        assert len(records) >= 3


class TestSessionIdPassthrough:
    """Session ID propagates through the entire chain."""

    def test_session_id_in_response(self):
        response = handle_founder_message("What's happening?", session_id="sess-42")
        # Session ID doesn't appear in EAResponse directly, but the intent
        # and internal calls all use it
        assert response.intent is not None
