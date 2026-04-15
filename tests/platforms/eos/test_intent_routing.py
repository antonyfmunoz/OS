"""Tests for eos_ai.platforms.eos.intent_routing."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.intent_routing import (
    FounderIntent,
    FounderIntentType,
    parse_founder_intent,
)
from eos_ai.platforms.eos.roles import EOSRole


class TestPortfolioClassification:
    """Portfolio keywords → PORTFOLIO intent, PORTFOLIO_ADVISOR role."""

    @pytest.mark.parametrize(
        "text",
        [
            "How is my portfolio looking?",
            "Review the capital allocation across companies",
            "What's the risk assessment on Initiate Arena?",
            "Investment returns this quarter",
            "Net worth update",
            "Diversification strategy for the conglomerate",
        ],
    )
    def test_portfolio_messages(self, text):
        intent = parse_founder_intent(text)
        assert intent.intent_type == FounderIntentType.PORTFOLIO
        assert intent.suggested_role == EOSRole.PORTFOLIO_ADVISOR
        assert intent.confidence == 1.0


class TestStrategyClassification:
    """Strategy keywords → STRATEGY intent, CEO role."""

    @pytest.mark.parametrize(
        "text",
        [
            "What's our strategy for Q3?",
            "Reprioritize the business direction",
            "Revenue model needs to change",
            "Update the roadmap for Lyfe Institute",
            "Competitive analysis on the market position",
            "What milestone should we hit next?",
        ],
    )
    def test_strategy_messages(self, text):
        intent = parse_founder_intent(text)
        assert intent.intent_type == FounderIntentType.STRATEGY
        assert intent.suggested_role == EOSRole.CEO
        assert intent.confidence == 1.0


class TestStatusClassification:
    """Status keywords → STATUS intent, EA role."""

    @pytest.mark.parametrize(
        "text",
        [
            "Catch me up",
            "What's happening right now?",
            "Give me a status update",
            "Morning brief",
            "What's blocked?",
            "Summarize the overnight work",
        ],
    )
    def test_status_messages(self, text):
        intent = parse_founder_intent(text)
        assert intent.intent_type == FounderIntentType.STATUS
        assert intent.suggested_role == EOSRole.EA
        assert intent.confidence == 1.0


class TestReviewClassification:
    """Review keywords → REVIEW intent, EA role."""

    @pytest.mark.parametrize(
        "text",
        [
            "Review the latest changes",
            "Approve the deployment",
            "Check this output for quality",
            "Audit the pipeline results",
        ],
    )
    def test_review_messages(self, text):
        intent = parse_founder_intent(text)
        assert intent.intent_type == FounderIntentType.REVIEW
        assert intent.suggested_role == EOSRole.EA


class TestExecutionClassification:
    """Execution keywords → EXECUTION intent, EA role."""

    @pytest.mark.parametrize(
        "text",
        [
            "Build the landing page",
            "Deploy the Discord bot",
            "Fix the authentication bug",
            "Create a new outreach template",
            "Set up the new outreach automation",
        ],
    )
    def test_execution_messages(self, text):
        intent = parse_founder_intent(text)
        assert intent.intent_type == FounderIntentType.EXECUTION
        assert intent.suggested_role == EOSRole.EA


class TestDirectEAClassification:
    """Direct EA keywords → DIRECT_EA intent."""

    @pytest.mark.parametrize(
        "text",
        [
            "Schedule a follow-up for Thursday",
            "Remind me about the meeting at 3pm",
            "Send a notification to the team",
        ],
    )
    def test_direct_ea_messages(self, text):
        intent = parse_founder_intent(text)
        assert intent.intent_type == FounderIntentType.DIRECT_EA
        assert intent.suggested_role == EOSRole.EA


class TestUnknownClassification:
    """Unclassifiable text → UNKNOWN, falls to EA."""

    def test_empty_string(self):
        intent = parse_founder_intent("")
        assert intent.intent_type == FounderIntentType.UNKNOWN
        assert intent.suggested_role == EOSRole.EA
        assert intent.confidence == 0.0

    def test_nonsense(self):
        intent = parse_founder_intent("hello there general kenobi")
        assert intent.intent_type == FounderIntentType.UNKNOWN
        assert intent.suggested_role == EOSRole.EA
        assert intent.confidence == 0.5


class TestFounderIntentModel:
    """FounderIntent data model correctness."""

    def test_has_intent_id(self):
        intent = parse_founder_intent("status update")
        assert intent.intent_id.startswith("intent_")

    def test_preserves_raw_text(self):
        intent = parse_founder_intent("What is our strategy?")
        assert intent.raw_text == "What is our strategy?"

    def test_has_created_at(self):
        intent = parse_founder_intent("hello")
        assert intent.created_at is not None

    def test_to_dict_round_trip(self):
        intent = parse_founder_intent("Review the capital allocation")
        d = intent.to_dict()
        restored = FounderIntent.from_dict(d)
        assert restored.intent_type == intent.intent_type
        assert restored.suggested_role == intent.suggested_role
        assert restored.confidence == intent.confidence
        assert restored.raw_text == intent.raw_text

    def test_directives_extracted(self):
        text = "Build the landing page. Deploy it to production. Fix the CSS."
        intent = parse_founder_intent(text)
        # Should extract some directives (capitalized sentences)
        assert isinstance(intent.extracted_directives, list)


class TestFounderNeverDirectlyAddressesCEO:
    """
    The parser suggests roles but the founder never 'speaks to' CEO directly.
    Even STRATEGY intent has suggested_role=CEO but is always routed through EA.
    """

    def test_strategy_suggested_role_is_ceo(self):
        intent = parse_founder_intent("What's our growth strategy?")
        assert intent.suggested_role == EOSRole.CEO
        # But this is advisory — EA mediates (tested in ea_orchestrator tests)

    def test_portfolio_suggested_role_is_portfolio(self):
        intent = parse_founder_intent("Portfolio risk assessment")
        assert intent.suggested_role == EOSRole.PORTFOLIO_ADVISOR
