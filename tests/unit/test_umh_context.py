"""Tests for umh.context — the context composition layer.

Covers:
  - Context sections assemble correctly
  - Token budget truncates lower-priority sections first
  - Faulty section provider does not break run
  - LLM prompt gets system/user separation
  - No EOS/core/services/scripts imports
  - Builder fallback in run.py
  - ContextResult metadata and serialization
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.context import (
    ContextBuilder,
    ContextPriority,
    ContextResult,
    ContextSection,
    TokenBudget,
)


# ── Section assembly ────────────────────────────────────────────────────


class TestSectionAssembly:
    """Context sections assemble in priority order."""

    def test_empty_builder_returns_empty_result(self):
        builder = ContextBuilder()
        result = builder.build()
        assert result.system_prompt == ""
        assert result.user_prompt == ""
        assert result.sections_used == ()
        assert result.was_truncated is False

    def test_single_section_assembles(self):
        builder = ContextBuilder()
        builder.add_section(
            ContextSection(name="identity", content="You are an assistant.")
        )
        result = builder.build(user_prompt="Hello")
        assert "You are an assistant." in result.system_prompt
        assert result.user_prompt == "Hello"
        assert "identity" in result.sections_used

    def test_multiple_sections_join_with_double_newline(self):
        builder = ContextBuilder()
        builder.add_section(ContextSection(name="a", content="AAA"))
        builder.add_section(ContextSection(name="b", content="BBB"))
        result = builder.build()
        assert result.system_prompt == "AAA\n\nBBB"

    def test_sections_ordered_by_priority(self):
        builder = ContextBuilder()
        builder.add_section(
            ContextSection(name="low", content="LOW", priority=ContextPriority.LOW)
        )
        builder.add_section(
            ContextSection(
                name="critical", content="CRITICAL", priority=ContextPriority.CRITICAL
            )
        )
        builder.add_section(
            ContextSection(name="high", content="HIGH", priority=ContextPriority.HIGH)
        )
        result = builder.build()
        parts = result.system_prompt.split("\n\n")
        assert parts == ["CRITICAL", "HIGH", "LOW"]

    def test_extra_sections_included(self):
        builder = ContextBuilder()
        builder.add_section(ContextSection(name="base", content="Base."))
        extra = [ContextSection(name="extra", content="Extra.")]
        result = builder.build(extra_sections=extra)
        assert "extra" in result.sections_used
        assert "Extra." in result.system_prompt

    def test_section_with_empty_content_excluded(self):
        """Providers returning empty content are silently dropped."""
        builder = ContextBuilder()
        builder.add_provider("empty", lambda: ContextSection(name="empty", content=""))
        builder.add_section(ContextSection(name="real", content="Real."))
        result = builder.build()
        assert "empty" not in result.sections_used
        assert "real" in result.sections_used

    def test_provider_returning_none_excluded(self):
        builder = ContextBuilder()
        builder.add_provider("nothing", lambda: None)
        builder.add_section(ContextSection(name="real", content="Real."))
        result = builder.build()
        assert "nothing" not in result.sections_used


# ── Token budget ────────────────────────────────────────────────────────


class TestTokenBudget:
    """Token budget truncates lower-priority sections first."""

    def test_all_sections_fit_within_budget(self):
        budget = TokenBudget(max_tokens=10_000)
        sections = [
            ContextSection(name="a", content="x" * 100),
            ContextSection(name="b", content="x" * 100),
        ]
        kept, dropped = budget.fit(sections)
        assert len(kept) == 2
        assert len(dropped) == 0

    def test_lowest_priority_dropped_first(self):
        budget = TokenBudget(max_tokens=20)
        sections = [
            ContextSection(
                name="critical",
                content="x" * 40,
                priority=ContextPriority.CRITICAL,
            ),
            ContextSection(name="low", content="x" * 40, priority=ContextPriority.LOW),
            ContextSection(
                name="supplementary",
                content="x" * 40,
                priority=ContextPriority.SUPPLEMENTARY,
            ),
        ]
        kept, dropped = budget.fit(sections)
        kept_names = [s.name for s in kept]
        dropped_names = [s.name for s in dropped]
        assert "critical" in kept_names
        assert "supplementary" in dropped_names

    def test_same_priority_drops_largest_first(self):
        budget = TokenBudget(max_tokens=8)
        sections = [
            ContextSection(
                name="small", content="x" * 20, priority=ContextPriority.STANDARD
            ),
            ContextSection(
                name="big", content="x" * 40, priority=ContextPriority.STANDARD
            ),
        ]
        kept, dropped = budget.fit(sections)
        kept_names = [s.name for s in kept]
        dropped_names = [s.name for s in dropped]
        assert "small" in kept_names
        assert "big" in dropped_names

    def test_budget_of_zero_drops_large_sections(self):
        budget = TokenBudget(max_tokens=0)
        sections = [ContextSection(name="a", content="x" * 100)]
        kept, dropped = budget.fit(sections)
        assert len(kept) == 0
        assert len(dropped) == 1

    def test_empty_sections_always_fit(self):
        budget = TokenBudget(max_tokens=1)
        kept, dropped = budget.fit([])
        assert kept == []
        assert dropped == []

    def test_builder_reports_truncation(self):
        builder = ContextBuilder(max_tokens=5)
        builder.add_section(
            ContextSection(
                name="big",
                content="x" * 100,
                priority=ContextPriority.SUPPLEMENTARY,
            )
        )
        builder.add_section(
            ContextSection(name="tiny", content="hi", priority=ContextPriority.CRITICAL)
        )
        result = builder.build()
        assert result.was_truncated is True
        assert "big" in result.sections_dropped
        assert "tiny" in result.sections_used

    def test_estimate_tokens(self):
        budget = TokenBudget()
        assert budget.estimate_tokens("x" * 400) == 100

    def test_negative_max_tokens_clamped(self):
        budget = TokenBudget(max_tokens=-5)
        assert budget.max_tokens == 1


# ── Fault isolation ─────────────────────────────────────────────────────


class TestFaultIsolation:
    """Faulty section provider does not break the build."""

    def test_raising_provider_recorded_in_failed_sources(self):
        builder = ContextBuilder()
        builder.add_section(ContextSection(name="good", content="Good."))

        def bad_provider():
            raise ValueError("database timeout")

        builder.add_provider("bad_source", bad_provider)
        result = builder.build()
        assert "good" in result.sections_used
        assert any("bad_source" in f for f in result.failed_sources)
        assert "database timeout" in result.failed_sources[0]

    def test_multiple_failures_all_recorded(self):
        builder = ContextBuilder()

        def fail_one():
            raise RuntimeError("one")

        def fail_two():
            raise RuntimeError("two")

        builder.add_provider("fail_1", fail_one)
        builder.add_provider("fail_2", fail_two)

        result = builder.build()
        assert len(result.failed_sources) == 2

    def test_failure_does_not_prevent_other_sections(self):
        builder = ContextBuilder()
        builder.add_section(ContextSection(name="before", content="Before."))
        builder.add_provider("crash", lambda: 1 / 0)
        builder.add_section(ContextSection(name="after", content="After."))
        result = builder.build()
        assert "before" in result.sections_used
        assert "after" in result.sections_used
        assert len(result.failed_sources) == 1


# ── LLM system/user separation ─────────────────────────────────────────


class TestLLMSeparation:
    """LLM prompt gets proper system/user separation."""

    def test_system_prompt_separate_from_user(self):
        builder = ContextBuilder()
        builder.add_section(ContextSection(name="sys", content="System context."))
        result = builder.build(user_prompt="User question?")
        assert result.system_prompt == "System context."
        assert result.user_prompt == "User question?"
        assert "User question?" not in result.system_prompt

    def test_flat_prompt_combines_both(self):
        builder = ContextBuilder()
        builder.add_section(ContextSection(name="sys", content="System."))
        result = builder.build(user_prompt="User.")
        assert "System." in result.flat_prompt
        assert "User." in result.flat_prompt

    def test_flat_prompt_no_system(self):
        builder = ContextBuilder()
        result = builder.build(user_prompt="Just user.")
        assert result.flat_prompt == "Just user."


# ── ContextResult serialization ─────────────────────────────────────────


class TestContextResult:
    """ContextResult metadata and serialization."""

    def test_to_dict_keys(self):
        result = ContextResult(
            system_prompt="sys",
            user_prompt="usr",
            sections_used=("a",),
            sections_dropped=("b",),
            failed_sources=("c: err",),
            estimated_tokens=42,
            was_truncated=True,
        )
        d = result.to_dict()
        assert d["system_prompt_length"] == 3
        assert d["user_prompt_length"] == 3
        assert d["sections_used"] == ["a"]
        assert d["sections_dropped"] == ["b"]
        assert d["failed_sources"] == ["c: err"]
        assert d["estimated_tokens"] == 42
        assert d["was_truncated"] is True

    def test_frozen_sections(self):
        section = ContextSection(name="x", content="y")
        with pytest.raises(AttributeError):
            section.name = "z"

    def test_frozen_result(self):
        result = ContextResult(
            system_prompt="",
            user_prompt="",
            sections_used=(),
            sections_dropped=(),
            failed_sources=(),
            estimated_tokens=0,
            was_truncated=False,
        )
        with pytest.raises(AttributeError):
            result.system_prompt = "new"

    def test_section_estimated_tokens(self):
        section = ContextSection(name="x", content="x" * 80)
        assert section.estimated_tokens == 20


# ── run.py integration ──────────────────────────────────────────────────


class TestRunIntegration:
    """run.py uses the context builder without breaking behavior."""

    def test_run_still_works(self):
        from umh import run

        result = run("What should I focus on?")
        assert result.run_id.startswith("run_")
        assert isinstance(result.response, str)
        assert result.trace.stages.get("compose") is not None

    def test_compose_stage_has_prompt_length(self):
        from umh import run

        result = run("Test input")
        compose = result.trace.stages["compose"]
        assert "prompt_length" in compose
        assert compose["prompt_length"] > 0

    def test_compose_stage_has_system_prompt_flag(self):
        from umh import run

        result = run("Another test")
        compose = result.trace.stages["compose"]
        assert "has_system_prompt" in compose


# ── Import isolation ────────────────────────────────────────────────────


class TestImportIsolation:
    """No EOS/core/services/scripts imports in umh.context."""

    FORBIDDEN_PREFIXES = (
        "eos",
        "services",
        "scripts",
        "core",
        "substrate",
    )

    def _scan_imports(self, filepath: str) -> list[str]:
        with open(filepath) as f:
            tree = ast.parse(f.read(), filename=filepath)

        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(self.FORBIDDEN_PREFIXES):
                        violations.append(f"{filepath}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(self.FORBIDDEN_PREFIXES):
                    violations.append(f"{filepath}: from {node.module}")
        return violations

    def test_context_types_no_eos_imports(self):
        violations = self._scan_imports("/opt/OS/umh/context/types.py")
        assert violations == [], f"Forbidden imports: {violations}"

    def test_context_budget_no_eos_imports(self):
        violations = self._scan_imports("/opt/OS/umh/context/budget.py")
        assert violations == [], f"Forbidden imports: {violations}"

    def test_context_builder_no_eos_imports(self):
        violations = self._scan_imports("/opt/OS/umh/context/builder.py")
        assert violations == [], f"Forbidden imports: {violations}"

    def test_context_init_no_eos_imports(self):
        violations = self._scan_imports("/opt/OS/umh/context/__init__.py")
        assert violations == [], f"Forbidden imports: {violations}"

    def test_context_imports_only_from_umh(self):
        """All imports must be from umh or stdlib."""
        context_dir = "/opt/OS/umh/context"
        for fname in os.listdir(context_dir):
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(context_dir, fname)
            with open(filepath) as f:
                tree = ast.parse(f.read(), filename=filepath)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if not node.module.startswith(("umh.", "__future__")):
                        root = node.module.split(".")[0]
                        try:
                            __import__(root)
                        except ImportError:
                            pytest.fail(f"{filepath}: non-stdlib import {node.module}")
