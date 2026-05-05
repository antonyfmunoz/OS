"""Tests for eos_ai.platforms.eos.delegation."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.delegation import choose_delegate, should_delegate
from eos_ai.platforms.eos.intent_routing import (
    FounderIntentType,
    parse_founder_intent,
)
from eos_ai.platforms.eos.roles import EOSRole


class TestShouldDelegate:
    """Only STRATEGY and PORTFOLIO intents trigger delegation."""

    def test_strategy_delegates(self):
        intent = parse_founder_intent("What's our business strategy?")
        assert intent.intent_type == FounderIntentType.STRATEGY
        assert should_delegate(intent) is True

    def test_portfolio_delegates(self):
        intent = parse_founder_intent("How is my portfolio?")
        assert intent.intent_type == FounderIntentType.PORTFOLIO
        assert should_delegate(intent) is True

    def test_status_does_not_delegate(self):
        intent = parse_founder_intent("What's the status?")
        assert should_delegate(intent) is False

    def test_review_does_not_delegate(self):
        intent = parse_founder_intent("Review the output")
        assert should_delegate(intent) is False

    def test_execution_does_not_delegate(self):
        intent = parse_founder_intent("Build the feature")
        assert should_delegate(intent) is False

    def test_direct_ea_does_not_delegate(self):
        intent = parse_founder_intent("Schedule a reminder")
        assert should_delegate(intent) is False

    def test_unknown_does_not_delegate(self):
        intent = parse_founder_intent("something random")
        assert should_delegate(intent) is False


class TestChooseDelegate:
    """Delegation targets are CEO or Portfolio Advisor — never builder."""

    def test_strategy_to_ceo(self):
        intent = parse_founder_intent("Reprioritize business direction")
        assert choose_delegate(intent) == EOSRole.CEO

    def test_portfolio_to_portfolio_advisor(self):
        intent = parse_founder_intent("Capital allocation review")
        assert choose_delegate(intent) == EOSRole.PORTFOLIO_ADVISOR

    def test_status_returns_none(self):
        intent = parse_founder_intent("Catch me up")
        assert choose_delegate(intent) is None

    def test_execution_returns_none(self):
        intent = parse_founder_intent("Deploy the bot")
        assert choose_delegate(intent) is None

    def test_never_returns_general(self):
        """GENERAL is never a delegation target."""
        for text in [
            "strategy update",
            "portfolio review",
            "status",
            "build it",
            "random text",
        ]:
            intent = parse_founder_intent(text)
            delegate = choose_delegate(intent)
            if delegate is not None:
                assert delegate != EOSRole.GENERAL


class TestBuilderNeverFounderFacing:
    """Builder must never appear as a delegation target in EOS platform routing."""

    def test_builder_not_in_eos_roles(self):
        role_values = [r.value for r in EOSRole]
        assert "builder" not in role_values

    def test_no_delegation_to_builder(self):
        test_messages = [
            "Build the landing page",
            "Fix the code",
            "Deploy the service",
            "Create a new module",
            "Refactor the pipeline",
        ]
        for text in test_messages:
            intent = parse_founder_intent(text)
            delegate = choose_delegate(intent)
            # Builder is not an EOSRole, so it can never be returned
            if delegate is not None:
                assert delegate.value != "builder"
