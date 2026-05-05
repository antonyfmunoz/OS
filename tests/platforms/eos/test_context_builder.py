"""Tests for eos_ai.platforms.eos.context_builder."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.context_builder import (
    build_ceo_context,
    build_context_for_role,
    build_ea_context,
    build_portfolio_context,
)
from eos_ai.platforms.eos.roles import EOSRole


class TestContextSchema:
    """All context builders return {meta, state, insights, suggestions}."""

    @pytest.mark.parametrize(
        "builder",
        [
            build_ea_context,
            build_ceo_context,
            build_portfolio_context,
        ],
    )
    def test_has_four_sections(self, builder):
        ctx = builder()
        assert "meta" in ctx
        assert "state" in ctx
        assert "insights" in ctx
        assert "suggestions" in ctx

    @pytest.mark.parametrize(
        "builder",
        [
            build_ea_context,
            build_ceo_context,
            build_portfolio_context,
        ],
    )
    def test_meta_has_role(self, builder):
        ctx = builder()
        assert "role" in ctx["meta"]

    @pytest.mark.parametrize(
        "builder",
        [
            build_ea_context,
            build_ceo_context,
            build_portfolio_context,
        ],
    )
    def test_meta_has_timestamp(self, builder):
        ctx = builder()
        assert "timestamp" in ctx["meta"]

    @pytest.mark.parametrize(
        "builder",
        [
            build_ea_context,
            build_ceo_context,
            build_portfolio_context,
        ],
    )
    def test_insights_is_list(self, builder):
        ctx = builder()
        assert isinstance(ctx["insights"], list)

    @pytest.mark.parametrize(
        "builder",
        [
            build_ea_context,
            build_ceo_context,
            build_portfolio_context,
        ],
    )
    def test_suggestions_is_list(self, builder):
        ctx = builder()
        assert isinstance(ctx["suggestions"], list)


class TestEAContext:
    def test_role_is_ea(self):
        ctx = build_ea_context()
        assert ctx["meta"]["role"] == "ea"

    def test_state_has_tasks(self):
        ctx = build_ea_context()
        assert "tasks" in ctx["state"]

    def test_state_has_pipelines(self):
        ctx = build_ea_context()
        assert "pipelines" in ctx["state"]

    def test_state_has_perceptions(self):
        ctx = build_ea_context()
        assert "perceptions" in ctx["state"]

    def test_state_has_station(self):
        ctx = build_ea_context()
        assert "station" in ctx["state"]

    def test_state_has_live_sessions(self):
        ctx = build_ea_context()
        assert "live_sessions" in ctx["state"]

    def test_state_has_operator_session(self):
        ctx = build_ea_context()
        assert "operator_session" in ctx["state"]

    def test_accepts_session_id(self):
        ctx = build_ea_context(session_id="test-123")
        assert ctx["meta"]["session_id"] == "test-123"


class TestCEOContext:
    def test_role_is_ceo(self):
        ctx = build_ceo_context()
        assert ctx["meta"]["role"] == "ceo"

    def test_state_has_execution_health(self):
        ctx = build_ceo_context()
        assert "execution_health" in ctx["state"]

    def test_state_has_continuity(self):
        ctx = build_ceo_context()
        assert "continuity" in ctx["state"]


class TestPortfolioContext:
    def test_role_is_portfolio(self):
        ctx = build_portfolio_context()
        assert ctx["meta"]["role"] == "portfolio_advisor"

    def test_state_has_system_health(self):
        ctx = build_portfolio_context()
        assert "system_health" in ctx["state"]

    def test_state_has_risk_indicators(self):
        ctx = build_portfolio_context()
        assert "risk_indicators" in ctx["state"]


class TestContextDispatcher:
    def test_ea_dispatches_to_ea(self):
        ctx = build_context_for_role(EOSRole.EA)
        assert ctx["meta"]["role"] == "ea"

    def test_ceo_dispatches_to_ceo(self):
        ctx = build_context_for_role(EOSRole.CEO)
        assert ctx["meta"]["role"] == "ceo"

    def test_portfolio_dispatches_to_portfolio(self):
        ctx = build_context_for_role(EOSRole.PORTFOLIO_ADVISOR)
        assert ctx["meta"]["role"] == "portfolio_advisor"

    def test_general_falls_back_to_ea(self):
        ctx = build_context_for_role(EOSRole.GENERAL)
        assert ctx["meta"]["role"] == "ea"


class TestNoFormatting:
    """Context builders return data, not formatted text."""

    def test_ea_state_is_dict(self):
        ctx = build_ea_context()
        assert isinstance(ctx["state"], dict)

    def test_ceo_state_is_dict(self):
        ctx = build_ceo_context()
        assert isinstance(ctx["state"], dict)

    def test_portfolio_state_is_dict(self):
        ctx = build_portfolio_context()
        assert isinstance(ctx["state"], dict)

    def test_meta_is_dict(self):
        ctx = build_ea_context()
        assert isinstance(ctx["meta"], dict)
