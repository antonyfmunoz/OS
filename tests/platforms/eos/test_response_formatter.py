"""Tests for eos_ai.platforms.eos.response_formatter."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.response_formatter import (
    format_blocked_decision_summary,
    format_briefing,
    format_ea_response,
    format_execution_summary,
    format_portfolio_recommendation,
    format_strategic_recommendation,
)
from eos_ai.platforms.eos.roles import EOSRole


def _make_ea_context(**overrides):
    """Helper to create a minimal EA context dict."""
    ctx = {
        "meta": {
            "role": "ea",
            "timestamp": "2026-04-14T00:00:00Z",
            "session_id": None,
            "day_open": True,
            "day_mode": "local_active",
        },
        "state": {
            "operator_session": {
                "is_day_open": True,
                "day_mode": "local_active",
                "active_workspace": "builder",
                "node_preference": "auto",
            },
            "tasks": {
                "counts": {"in_progress": 2, "completed": 5, "waiting_on_operator": 1},
                "total": 8,
                "blocked_titles": ["Decide pricing"],
            },
            "pipelines": {
                "active_count": 1,
                "blocked_count": 0,
                "failed_count": 0,
                "active_titles": ["Landing page build"],
                "blocked_titles": [],
            },
            "perceptions": {
                "critical_count": 0,
                "warning_count": 1,
                "critical_summaries": [],
                "warning_summaries": ["Stale task detected"],
            },
            "station": {},
            "live_sessions": {"active_count": 0, "active_titles": []},
        },
        "insights": ["1 task(s) waiting on operator decision"],
        "suggestions": ["Review blocked tasks and provide decisions"],
    }
    ctx.update(overrides)
    return ctx


def _make_ceo_context(**overrides):
    ctx = {
        "meta": {
            "role": "ceo",
            "timestamp": "2026-04-14T00:00:00Z",
            "session_id": None,
        },
        "state": {
            "execution_health": {
                "total_tasks": 8,
                "tasks_blocked": 1,
                "tasks_in_progress": 2,
                "tasks_completed": 5,
                "pipelines_active": 1,
                "pipelines_failed": 0,
            },
            "continuity": {
                "unfinished_priorities": ["Close first sale"],
                "continuity_notes": None,
                "last_resume_context": None,
            },
            "perceptions": {"critical_count": 0, "warning_count": 1},
        },
        "insights": [
            "1 decision(s) blocking execution",
            "1 unfinished priority(ies) carried from previous session",
        ],
        "suggestions": ["Unblock waiting decisions to restore execution velocity"],
    }
    ctx.update(overrides)
    return ctx


def _make_portfolio_context(**overrides):
    ctx = {
        "meta": {
            "role": "portfolio_advisor",
            "timestamp": "2026-04-14T00:00:00Z",
            "session_id": None,
        },
        "state": {
            "system_health": {
                "total_tasks": 8,
                "tasks_blocked": 1,
                "critical_perceptions": 0,
                "warning_perceptions": 1,
            },
            "risk_indicators": {"execution_blocked": False, "critical_alerts": False},
        },
        "insights": [],
        "suggestions": [],
    }
    ctx.update(overrides)
    return ctx


class TestFormatBriefing:
    def test_includes_day_status(self):
        text = format_briefing(_make_ea_context())
        assert "Day is open" in text

    def test_includes_task_counts(self):
        text = format_briefing(_make_ea_context())
        assert "8 total" in text

    def test_includes_insights(self):
        text = format_briefing(_make_ea_context())
        assert "waiting on operator" in text

    def test_includes_suggestions(self):
        text = format_briefing(_make_ea_context())
        assert "Review blocked tasks" in text

    def test_closed_day(self):
        ctx = _make_ea_context()
        ctx["state"]["operator_session"]["is_day_open"] = False
        text = format_briefing(ctx)
        assert "Day is closed" in text


class TestFormatStrategicRecommendation:
    def test_includes_execution_health(self):
        text = format_strategic_recommendation(_make_ceo_context())
        assert "blocked" in text

    def test_includes_recommendation(self):
        text = format_strategic_recommendation(
            _make_ceo_context(), recommendation="Focus on closing first sale"
        )
        assert "Focus on closing first sale" in text

    def test_includes_carried_priorities(self):
        text = format_strategic_recommendation(_make_ceo_context())
        assert "Close first sale" in text


class TestFormatPortfolioRecommendation:
    def test_no_risk_flags_when_healthy(self):
        text = format_portfolio_recommendation(_make_portfolio_context())
        # Should not flag risk when indicators are False
        assert "resource risk" not in text

    def test_flags_risk_when_blocked(self):
        ctx = _make_portfolio_context()
        ctx["state"]["risk_indicators"]["execution_blocked"] = True
        text = format_portfolio_recommendation(ctx)
        assert "resource risk" in text

    def test_includes_recommendation(self):
        text = format_portfolio_recommendation(
            _make_portfolio_context(),
            recommendation="Reduce exposure to unvalidated ventures",
        )
        assert "Reduce exposure" in text


class TestFormatExecutionSummary:
    def test_shows_task_count(self):
        text = format_execution_summary(
            created_task_ids=["t1", "t2"],
            created_pipeline_ids=[],
            blocked_items=[],
        )
        assert "2 task(s)" in text

    def test_shows_pipeline_count(self):
        text = format_execution_summary(
            created_task_ids=[],
            created_pipeline_ids=["p1"],
            blocked_items=[],
        )
        assert "1 pipeline(s)" in text

    def test_shows_blocked(self):
        text = format_execution_summary(
            created_task_ids=[],
            created_pipeline_ids=[],
            blocked_items=["Need pricing decision"],
        )
        assert "Need pricing decision" in text

    def test_empty_shows_acknowledged(self):
        text = format_execution_summary(
            created_task_ids=[],
            created_pipeline_ids=[],
            blocked_items=[],
        )
        assert "Acknowledged" in text


class TestFormatBlockedDecisionSummary:
    def test_empty(self):
        text = format_blocked_decision_summary([])
        assert "No items" in text

    def test_with_items(self):
        text = format_blocked_decision_summary(["Pricing", "Hiring"])
        assert "2 item(s)" in text
        assert "Pricing" in text
        assert "Hiring" in text


class TestMasterFormatter:
    def test_briefing_route(self):
        text = format_ea_response(
            primary_role=EOSRole.EA,
            delegated_role=None,
            context=_make_ea_context(),
            summary_type="briefing",
        )
        assert "Day is open" in text

    def test_strategic_route(self):
        text = format_ea_response(
            primary_role=EOSRole.EA,
            delegated_role=EOSRole.CEO,
            context=_make_ceo_context(),
            summary_type="strategic_recommendation",
        )
        assert "blocked" in text

    def test_portfolio_route(self):
        text = format_ea_response(
            primary_role=EOSRole.EA,
            delegated_role=EOSRole.PORTFOLIO_ADVISOR,
            context=_make_portfolio_context(),
            summary_type="portfolio_recommendation",
        )
        assert isinstance(text, str)

    def test_execution_route(self):
        text = format_ea_response(
            primary_role=EOSRole.EA,
            delegated_role=None,
            context=_make_ea_context(),
            summary_type="execution_summary",
            created_task_ids=["t1"],
        )
        assert "1 task(s)" in text

    def test_fallback_route(self):
        text = format_ea_response(
            primary_role=EOSRole.EA,
            delegated_role=None,
            context=_make_ea_context(),
            summary_type="nonexistent_type",
        )
        # Falls back to briefing
        assert "Day is open" in text
