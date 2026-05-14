"""Phase 8B — Decomposition and template tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from unittest.mock import patch, MagicMock

from umh.goals.models import Goal, GoalPriority
from umh.strategy.decomposer import (
    _generic_fallback,
    _parse_llm_steps,
    cache_strategy,
    decompose_goal,
    get_cached_strategy,
    invalidate_strategy,
    reset_strategy_cache,
)
from umh.strategy.models import (
    ApproachType,
    StepComplexity,
    StepType,
    Strategy,
    StrategyStep,
)
from umh.strategy.templates import list_templates, match_template


class TestTemplateMatching:
    def test_build_template(self):
        s = match_template("g1", "build a monitoring system")
        assert s is not None
        assert s.template_used == "build_system"
        assert len(s.steps) == 5

    def test_monitor_template(self):
        s = match_template("g1", "monitor API latency")
        assert s is not None
        assert s.template_used == "monitor"
        assert len(s.steps) == 4

    def test_automate_template(self):
        s = match_template("g1", "automate report generation")
        assert s is not None
        assert s.template_used == "automate"
        assert len(s.steps) == 4

    def test_analyze_template(self):
        s = match_template("g1", "analyze user behavior patterns")
        assert s is not None
        assert s.template_used == "analyze"

    def test_fix_template(self):
        s = match_template("g1", "fix the memory leak in worker")
        assert s is not None
        assert s.template_used == "fix"

    def test_migrate_template(self):
        s = match_template("g1", "migrate database to new schema")
        assert s is not None
        assert s.template_used == "migrate"
        assert s.approach_type == ApproachType.PHASED

    def test_optimize_template(self):
        s = match_template("g1", "optimize query performance")
        assert s is not None
        assert s.template_used == "optimize"

    def test_no_template_match(self):
        s = match_template("g1", "something completely unique and random xyz")
        assert s is None

    def test_template_determinism(self):
        s1 = match_template("g1", "build a notification system")
        s2 = match_template("g1", "build a notification system")
        assert s1 is not None and s2 is not None
        assert s1.template_used == s2.template_used
        assert len(s1.steps) == len(s2.steps)
        for a, b in zip(s1.steps, s2.steps):
            assert a.description == b.description
            assert a.type == b.type

    def test_linear_dependencies_wired(self):
        s = match_template("g1", "build a system")
        assert s is not None
        assert s.steps[0].dependencies == []
        for i in range(1, len(s.steps)):
            assert s.steps[i].dependencies == [s.steps[i - 1].id]

    def test_list_templates(self):
        templates = list_templates()
        assert len(templates) >= 7
        names = [t["name"] for t in templates]
        assert "build_system" in names
        assert "monitor" in names
        assert "automate" in names

    def test_case_insensitive(self):
        s = match_template("g1", "BUILD a reporting system")
        assert s is not None
        assert s.template_used == "build_system"


class TestLLMParsing:
    def test_parse_valid_steps(self):
        raw = (
            "STEP|Research existing solutions|research|low\n"
            "STEP|Implement the core module|execution|high\n"
            "STEP|Validate results|validation|medium\n"
        )
        steps = _parse_llm_steps(raw)
        assert len(steps) == 3
        assert steps[0].type == StepType.RESEARCH
        assert steps[1].estimated_complexity == StepComplexity.HIGH
        assert steps[2].type == StepType.VALIDATION

    def test_parse_ignores_non_step_lines(self):
        raw = "Here is the plan:\nSTEP|Do the thing|execution|medium\nSome extra text\n"
        steps = _parse_llm_steps(raw)
        assert len(steps) == 1

    def test_parse_caps_at_six(self):
        lines = "\n".join([f"STEP|Step {i}|execution|low" for i in range(10)])
        steps = _parse_llm_steps(lines)
        assert len(steps) == 6

    def test_parse_invalid_format(self):
        raw = "STEP|only two parts"
        steps = _parse_llm_steps(raw)
        assert len(steps) == 0

    def test_parse_empty_description(self):
        raw = "STEP||execution|medium"
        steps = _parse_llm_steps(raw)
        assert len(steps) == 0

    def test_parse_unknown_type_defaults(self):
        raw = "STEP|Do something|unknown_type|medium"
        steps = _parse_llm_steps(raw)
        assert len(steps) == 1
        assert steps[0].type == StepType.EXECUTION


class TestGenericFallback:
    def test_fallback_returns_strategy(self):
        goal = Goal(name="test", objective="something unique")
        s = _generic_fallback(goal)
        assert isinstance(s, Strategy)
        assert len(s.steps) == 3
        assert s.template_used == "generic_fallback"
        assert s.confidence == 0.5

    def test_fallback_has_research_execute_validate(self):
        goal = Goal(name="test", objective="anything")
        s = _generic_fallback(goal)
        types = [step.type for step in s.steps]
        assert StepType.RESEARCH in types
        assert StepType.EXECUTION in types
        assert StepType.VALIDATION in types


class TestDecomposeGoal:
    def setup_method(self):
        reset_strategy_cache()

    def test_template_match(self):
        goal = Goal(name="test", objective="build a dashboard system")
        s = decompose_goal(goal)
        assert s.template_used == "build_system"

    @patch("umh.strategy.decomposer.match_template", return_value=None)
    @patch("umh.strategy.decomposer._llm_decompose")
    def test_llm_fallback(self, mock_llm, mock_tmpl):
        goal = Goal(name="test", objective="unique xyz 123")
        fallback = _generic_fallback(goal)
        mock_llm.return_value = fallback
        s = decompose_goal(goal)
        mock_llm.assert_called_once()
        assert isinstance(s, Strategy)

    def test_decompose_emits_event(self):
        from umh.events.stream import reset_event_stream, get_event_stream

        reset_event_stream()
        stream = get_event_stream()
        goal = Goal(name="test", objective="build a monitoring system")
        decompose_goal(goal)
        events = stream.list_events()
        types = [e.type for e in events]
        assert "strategy.created" in types


class TestStrategyCache:
    def setup_method(self):
        reset_strategy_cache()

    def test_cache_and_retrieve(self):
        s = Strategy(goal_id="g1", objective="test")
        cache_strategy(s)
        cached = get_cached_strategy("g1")
        assert cached is not None
        assert cached.id == s.id

    def test_cache_miss(self):
        assert get_cached_strategy("nonexistent") is None

    def test_invalidate(self):
        s = Strategy(goal_id="g1", objective="test")
        cache_strategy(s)
        assert invalidate_strategy("g1") is True
        assert get_cached_strategy("g1") is None

    def test_invalidate_nonexistent(self):
        assert invalidate_strategy("nonexistent") is False

    def test_reset_cache(self):
        s = Strategy(goal_id="g1", objective="test")
        cache_strategy(s)
        reset_strategy_cache()
        assert get_cached_strategy("g1") is None
