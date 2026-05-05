"""Tests for umh.execution.quality — QualityGate extraction from legacy."""

import ast
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.execution.quality import QualityGate, TransformationResult


# ── Import boundary ─────────────────────────────────────────────────────


class TestImportBoundary:
    """No eos_ai imports allowed in the UMH quality module."""

    def test_no_eos_ai_imports_in_ast(self):
        with open("/opt/OS/umh/execution/quality.py") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("umh.runtime_engine."), (
                        f"Forbidden import: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert not node.module.startswith("umh.runtime_engine."), (
                        f"Forbidden import from: {node.module}"
                    )


# ── TransformationResult ────────────────────────────────────────────────


class TestTransformationResult:
    def test_construction(self):
        r = TransformationResult(
            original="hello",
            transformed="hello",
            reality_score=0.8,
            intelligence_score=0.7,
            personalization_score=0.6,
            execution_score=0.5,
            overall_score=0.65,
            transformations_applied=["test"],
            is_world_class=False,
        )
        assert r.original == "hello"
        assert r.overall_score == 0.65
        assert r.transformations_applied == ["test"]
        assert r.is_world_class is False


# ── QualityGate.transform ───────────────────────────────────────────────


class TestTransform:
    def test_empty_output_returns_zero_scores(self):
        gate = QualityGate()
        result = gate.transform(
            output="",
            input_text="anything",
            classified_signal={"primary_tier": "reality"},
        )
        assert result.overall_score == 0.0
        assert result.reality_score == 0.0
        assert result.is_world_class is False
        assert result.transformations_applied == []

    def test_generic_output_penalized(self):
        gate = QualityGate()
        generic_output = (
            "Generally speaking, in most cases, you should typically "
            "consider your options. It depends on many factors. "
            "Most businesses usually you should think about this."
        )
        result = gate.transform(
            output=generic_output,
            input_text="How do I grow?",
            classified_signal={"primary_tier": "other", "domain": "universal"},
        )
        # 7 generic patterns should tank the reality score
        assert result.reality_score < 0.3
        assert result.is_world_class is False

    def test_reasoning_rich_output_scores_higher(self):
        gate = QualityGate()
        rich_output = (
            "Based on what you said about your situation, here is my analysis. "
            "Because your pipeline is empty, this matters because you need "
            "outreach before revenue. Therefore the reason to focus on DMs "
            "this week is that means you get direct validation. As a result, "
            "which means your first step is to send 10 DMs today. "
            "Start with your warmest leads now. Your offer needs validation "
            "and your business depends on this next step immediately."
        )
        result = gate.transform(
            output=rich_output,
            input_text="What should I focus on?",
            classified_signal={"primary_tier": "reality", "domain": "business"},
            stage_context=None,
        )
        # Should score well on intelligence (many reasoning signals)
        assert result.intelligence_score > 0.7
        # Should score well on execution (many action signals)
        assert result.execution_score > 0.6
        # Should score well on reality (situated signals present)
        assert result.reality_score > 0.7
        # Should score well on personalization (business specifics)
        assert result.personalization_score > 0.6

    def test_leverage_tier_without_action_penalized(self):
        gate = QualityGate()
        philosophical = (
            "Business is a complex interplay of many factors that "
            "require deep consideration and reflection on your part."
        )
        result = gate.transform(
            output=philosophical,
            input_text="What is my highest leverage move?",
            classified_signal={"primary_tier": "leverage", "domain": "business"},
        )
        # Leverage query with no action signals should be penalized
        assert result.execution_score < 0.5

    def test_stage_context_boosts_personalization(self):
        gate = QualityGate()
        output = (
            "At stage 2, your focus should shift to scaling your offer. "
            "Because you've validated demand, the reason to invest in "
            "automation now is clear. Start with your highest-converting channel."
        )
        result = gate.transform(
            output=output,
            input_text="What's next?",
            classified_signal={"primary_tier": "other", "domain": "business"},
            stage_context={"current_stage": 2},
        )
        assert any("stage 2 referenced" in t for t in result.transformations_applied)
        assert result.personalization_score >= 0.7


# ── QualityGate.get_enhancement_prompt ──────────────────────────────────


class TestGetEnhancementPrompt:
    def test_returns_prompt_when_scores_low(self):
        gate = QualityGate()
        result = TransformationResult(
            original="x",
            transformed="x",
            reality_score=0.3,
            intelligence_score=0.4,
            personalization_score=0.2,
            execution_score=0.1,
            overall_score=0.25,
            transformations_applied=[],
            is_world_class=False,
        )
        prompt = gate.get_enhancement_prompt(result, classified={})
        assert "QUALITY REQUIREMENTS" in prompt
        assert "Ground your response" in prompt
        assert "Explain your reasoning" in prompt
        assert "specific to their stage" in prompt
        assert "clear action" in prompt

    def test_returns_empty_when_scores_high(self):
        gate = QualityGate()
        result = TransformationResult(
            original="x",
            transformed="x",
            reality_score=0.9,
            intelligence_score=0.8,
            personalization_score=0.85,
            execution_score=0.75,
            overall_score=0.83,
            transformations_applied=[],
            is_world_class=True,
        )
        prompt = gate.get_enhancement_prompt(result, classified={})
        assert prompt == ""

    def test_partial_prompt_for_mixed_scores(self):
        gate = QualityGate()
        result = TransformationResult(
            original="x",
            transformed="x",
            reality_score=0.9,
            intelligence_score=0.3,
            personalization_score=0.8,
            execution_score=0.2,
            overall_score=0.55,
            transformations_applied=[],
            is_world_class=False,
        )
        prompt = gate.get_enhancement_prompt(result, classified={})
        assert "QUALITY REQUIREMENTS" in prompt
        # Only intelligence and execution should be flagged
        assert "Explain your reasoning" in prompt
        assert "clear action" in prompt
        # Reality and personalization should NOT be flagged
        assert "Ground your response" not in prompt
        assert "specific to their stage" not in prompt


# ── Optional ctx ────────────────────────────────────────────────────────


class TestOptionalCtx:
    def test_gate_works_without_ctx(self):
        gate = QualityGate()
        assert gate.ctx is None
        result = gate.transform(
            output="Do this today. Send your first DM now.",
            input_text="help",
            classified_signal={"primary_tier": "other"},
        )
        assert result.overall_score > 0

    def test_gate_accepts_ctx(self):
        gate = QualityGate(ctx={"some": "context"})
        assert gate.ctx == {"some": "context"}
