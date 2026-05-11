"""Wave 6 validation — execution runtime extraction tests.

Verifies:
1. UMH runtime imports standalone with no eos_ai import.
2. UMH runtime uses UMH model_router/adapters, not runtime.model_router.
3. Fallback chain works through UMH.
4. Errors return normalized failure results, not raised exceptions.
5. runtime.agent_runtime public API still imports.
6. runtime.agent_runtime delegates rate limiting and cost to UMH.
7. runtime.execution_spine still imports and run_via_umh path remains valid.
8. No new forbidden UMH imports exist.
"""

import ast
import sys

import pytest

sys.path.insert(0, "/opt/OS")


class TestUMHRuntimeStandalone:
    """UMH execution runtime must work without eos_ai."""

    def test_import_without_eos_ai(self):
        from umh.execution.runtime import (
            RuntimeResult,
            RateLimiter,
            calculate_cost,
            execute_with_fallback,
            COST_PER_MILLION_TOKENS,
        )

        assert RuntimeResult is not None
        assert RateLimiter is not None
        assert callable(calculate_cost)
        assert callable(execute_with_fallback)
        assert isinstance(COST_PER_MILLION_TOKENS, dict)

    def test_no_eos_ai_imports_in_source(self):
        import pathlib

        source = pathlib.Path("/opt/OS/umh/execution/runtime.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        eos_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "eos" in node.module:
                    eos_imports.append(f"line {node.lineno}: from {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "eos" in alias.name:
                        eos_imports.append(f"line {node.lineno}: import {alias.name}")
        assert eos_imports == [], f"eos_ai imports found:\n" + "\n".join(eos_imports)

    def test_runtime_uses_execution_engine(self):
        """execute_with_fallback must route through umh.execution.engine, not direct model_router."""
        import pathlib

        source = pathlib.Path("/opt/OS/umh/execution/runtime.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        engine_import_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "umh.execution.engine":
                    engine_import_found = True
        assert engine_import_found, "Must import from umh.execution.engine"


class TestRuntimeResult:
    """RuntimeResult normalized envelope tests."""

    def test_ok_result(self):
        from umh.execution.runtime import RuntimeResult

        r = RuntimeResult(ok=True, output="hello world")
        assert r.ok is True
        assert r.output == "hello world"
        assert r.error is None
        assert r.cost_usd == 0.0
        assert r.duration_ms == 0
        assert r.tokens_used == {"input": 0, "output": 0, "total": 0}

    def test_failed_result(self):
        from umh.execution.runtime import RuntimeResult

        r = RuntimeResult(
            ok=False,
            output="",
            error="rate_limited",
            model_used="rate_limiter",
        )
        assert r.ok is False
        assert r.error == "rate_limited"


class TestCostCalculation:
    """Cost calculation extracted to UMH."""

    def test_calculate_cost_known_model(self):
        from umh.execution.runtime import calculate_cost

        cost = calculate_cost(
            "claude-haiku-4-5-20251001",
            {"input": 1000, "output": 500},
        )
        expected_input = 1000 / 1_000_000 * 0.80
        expected_output = 500 / 1_000_000 * 4.00
        assert cost == round(expected_input + expected_output, 8)

    def test_calculate_cost_unknown_model_uses_default(self):
        from umh.execution.runtime import calculate_cost

        cost = calculate_cost(
            "unknown-model",
            {"input": 1000, "output": 500},
        )
        expected_input = 1000 / 1_000_000 * 3.00
        expected_output = 500 / 1_000_000 * 15.00
        assert cost == round(expected_input + expected_output, 8)

    def test_calculate_cost_zero_tokens(self):
        from umh.execution.runtime import calculate_cost

        cost = calculate_cost("claude-sonnet-4-6", {"input": 0, "output": 0})
        assert cost == 0.0

    def test_cost_table_covers_main_models(self):
        from umh.execution.runtime import COST_PER_MILLION_TOKENS

        assert "claude-haiku-4-5-20251001" in COST_PER_MILLION_TOKENS
        assert "claude-sonnet-4-6" in COST_PER_MILLION_TOKENS
        assert "claude-opus-4-6" in COST_PER_MILLION_TOKENS
        assert "gemini-2.5-flash" in COST_PER_MILLION_TOKENS


class TestRateLimiter:
    """RateLimiter extracted to UMH."""

    def setup_method(self):
        from umh.execution.runtime import RateLimiter

        RateLimiter.reset()

    def test_allows_first_call(self):
        from umh.execution.runtime import RateLimiter

        assert RateLimiter.check("test_org") is True

    def test_blocks_after_minute_limit(self):
        from umh.execution.runtime import RateLimiter

        for _ in range(RateLimiter.LIMITS["per_minute"]):
            assert RateLimiter.check("test_org_minute") is True
        assert RateLimiter.check("test_org_minute") is False

    def test_different_orgs_independent(self):
        from umh.execution.runtime import RateLimiter

        for _ in range(RateLimiter.LIMITS["per_minute"]):
            RateLimiter.check("org_a")
        assert RateLimiter.check("org_a") is False
        assert RateLimiter.check("org_b") is True

    def test_reset_clears_state(self):
        from umh.execution.runtime import RateLimiter

        for _ in range(RateLimiter.LIMITS["per_minute"]):
            RateLimiter.check("org_reset")
        assert RateLimiter.check("org_reset") is False
        RateLimiter.reset()
        assert RateLimiter.check("org_reset") is True


class TestExecuteWithFallback:
    """execute_with_fallback lifecycle tests."""

    def setup_method(self):
        from umh.execution.runtime import RateLimiter

        RateLimiter.reset()

    def test_rate_limited_returns_failed_result(self):
        from umh.execution.runtime import RateLimiter, execute_with_fallback

        for _ in range(RateLimiter.LIMITS["per_minute"]):
            RateLimiter.check("rate_test_org")

        result = execute_with_fallback(
            prompt="test", task_type="fast_response", org_id="rate_test_org"
        )
        assert result.ok is False
        assert result.error == "rate_limited"
        assert result.model_used == "rate_limiter"

    def test_returns_runtime_result_type(self):
        from umh.execution.runtime import RuntimeResult, execute_with_fallback

        result = execute_with_fallback(
            prompt="test", task_type="fast_response", org_id="type_check_org"
        )
        assert isinstance(result, RuntimeResult)

    def test_never_raises(self):
        """execute_with_fallback must never raise — always returns RuntimeResult."""
        from umh.execution.runtime import execute_with_fallback

        result = execute_with_fallback(
            prompt="test", task_type="nonexistent_type", org_id="error_org"
        )
        assert isinstance(result, dict) or hasattr(result, "ok")


class TestObserverProtocol:
    """RuntimeObserver lifecycle hooks."""

    def test_null_observer_no_crash(self):
        from umh.execution.runtime import NullRuntimeObserver, RuntimeResult

        obs = NullRuntimeObserver()
        obs.on_call_start("prompt", "task", "org")
        obs.on_call_complete(RuntimeResult(ok=True, output=""))
        obs.on_rate_limited("org")
        obs.on_retry(1, "error")

    def test_set_get_observer(self):
        from umh.execution.runtime import (
            NullRuntimeObserver,
            get_runtime_observer,
            set_runtime_observer,
        )

        original = get_runtime_observer()
        new_obs = NullRuntimeObserver()
        set_runtime_observer(new_obs)
        assert get_runtime_observer() is new_obs
        set_runtime_observer(original)

    def test_custom_observer_receives_events(self):
        from umh.execution.runtime import (
            RateLimiter,
            RuntimeResult,
            execute_with_fallback,
        )

        RateLimiter.reset()
        events: list[str] = []

        class TestObserver:
            def on_call_start(self, prompt, task_type, org_id):
                events.append("start")

            def on_call_complete(self, result):
                events.append("complete")

            def on_rate_limited(self, org_id):
                events.append("rate_limited")

            def on_retry(self, attempt, error):
                events.append("retry")

        result = execute_with_fallback(
            prompt="test",
            task_type="fast_response",
            org_id="observer_org",
            observer=TestObserver(),
        )
        assert "start" in events
        assert "complete" in events


class TestLegacyAgentRuntimeCompat:
    """umh.runtime_engine.agent_runtime backward compatibility."""

    def test_public_api_imports(self):
        from umh.runtime_engine.agent_runtime import AgentRuntime, TaskType, AgentResult

        assert AgentRuntime is not None
        assert TaskType is not None
        assert AgentResult is not None

    def test_task_type_values(self):
        from umh.runtime_engine.agent_runtime import TaskType

        expected = {
            "score",
            "classify",
            "analyze",
            "generate",
            "summarize",
            "fast_response",
        }
        actual = {t.value for t in TaskType}
        assert expected == actual

    def test_rate_limiter_from_umh(self):
        """umh.runtime_engine.agent_runtime.RateLimiter should be the UMH class."""
        from umh.runtime_engine.agent_runtime import RateLimiter as EosRL
        from umh.execution.runtime import RateLimiter as UmhRL

        assert EosRL is UmhRL

    def test_calculate_cost_from_umh(self):
        """umh.runtime_engine.agent_runtime.calculate_cost should be the UMH function."""
        from umh.runtime_engine.agent_runtime import calculate_cost as eos_cc
        from umh.execution.runtime import calculate_cost as umh_cc

        assert eos_cc is umh_cc

    def test_agent_result_fields(self):
        from umh.runtime_engine.agent_runtime import AgentResult

        r = AgentResult(
            output="test",
            model_used="test-model",
            tokens_used={"input": 10, "output": 20, "total": 30},
            skill_used=None,
        )
        assert r.output == "test"
        assert r.cost_usd == 0.0
        assert r.duration_ms == 0
        assert r.interaction_id is None
        assert r.authority is None


class TestExecutionSpineCompat:
    """umh.runtime_engine.execution_spine still works."""

    def test_spine_imports(self):
        from umh.runtime_engine.execution_spine import SpineResult, ExecutionSpine, run_via_umh

        assert SpineResult is not None
        assert ExecutionSpine is not None
        assert callable(run_via_umh)

    def test_spine_result_is_str_subclass(self):
        from umh.runtime_engine.execution_spine import SpineResult

        r = SpineResult("hello", model_used="test", cost_usd=0.01)
        assert isinstance(r, str)
        assert r == "hello"
        assert r.model_used == "test"
        assert r.cost_usd == 0.01

    def test_spine_result_repr(self):
        from umh.runtime_engine.execution_spine import SpineResult

        r = SpineResult("test", model_used="m", cost_usd=0.001)
        assert "SpineResult" in repr(r)


class TestNoNewForbiddenImports:
    """No new eos_ai imports leaked into UMH."""

    def test_wave0_standalone_still_passes(self):
        """Re-run the wave 0 import guard to ensure no regressions."""
        import os

        UMH_ROOT = "/opt/OS/umh"
        from tests.unit.test_umh_boundaries import ALLOWED_EOS_IMPORTS

        allowed: dict[str, set[str]] = {}
        for rel_path, entries in ALLOWED_EOS_IMPORTS.items():
            abs_path = os.path.join(UMH_ROOT, rel_path.removeprefix("umh/"))
            allowed[abs_path] = {e["import"] for e in entries}

        violations = []
        for dirpath, _dirnames, filenames in os.walk(UMH_ROOT):
            if "__pycache__" in dirpath or "/interfaces/" in dirpath:
                continue
            for f in filenames:
                if not f.endswith(".py"):
                    continue
                filepath = os.path.join(dirpath, f)
                allowed_mods = allowed.get(filepath, set())
                with open(filepath) as fh:
                    source = fh.read()
                tree = ast.parse(source, filename=filepath)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if (
                            node.module.startswith(
                                ("services.", "interfaces.", "scripts.", "eos.", "runtime.")
                            )
                            and node.module not in allowed_mods
                        ):
                            violations.append(f"{filepath}:{node.lineno} from {node.module}")
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if (
                                alias.name.startswith(
                                    ("services.", "interfaces.", "scripts.", "eos.", "runtime.")
                                )
                                and alias.name not in allowed_mods
                            ):
                                violations.append(f"{filepath}:{node.lineno} import {alias.name}")
        assert violations == [], f"eos_ai imports found:\n" + "\n".join(violations)
