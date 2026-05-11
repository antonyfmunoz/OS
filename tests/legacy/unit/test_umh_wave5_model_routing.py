"""Wave 5 validation — model routing extraction tests.

Verifies:
1. UMH model router imports without eos_ai
2. Null/standalone fallback works
3. Provider failure normalizes to empty string
4. Fallback chain attempts next provider
5. runtime.model_router old import path works
6. runtime.agent_runtime old import path works
7. Quality estimation and escalation logic
8. No hard eos_ai imports inside umh/adapters/model_router.py
"""

import ast
import sys

sys.path.insert(0, "/opt/OS")


class TestUMHModelRouterStandalone:
    """UMH model router must work without eos_ai."""

    def test_import_without_eos_ai(self):
        from umh.adapters.model_router import (
            ModelRouter,
            ModelProvider,
            TaskType,
            RoutingResult,
            ModelConfig,
        )

        assert ModelRouter is not None
        assert ModelProvider is not None
        assert TaskType is not None
        assert RoutingResult is not None
        assert ModelConfig is not None

    def test_no_eos_ai_imports_in_source(self):
        import pathlib

        source = pathlib.Path("/opt/OS/umh/adapters/model_router.py").read_text(
            encoding="utf-8"
        )
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

    def test_task_type_enum_complete(self):
        from umh.adapters.model_router import TaskType

        expected = {
            "conversation",
            "analysis",
            "web_search",
            "market_intel",
            "fast_response",
            "long_context",
            "autonomous",
            "multimodal",
            "browser_control",
            "score",
            "classify",
            "analyze",
            "generate",
            "summarize",
            "strategic",
            "code",
            "research",
            "self_improve",
            "plan",
            "coordinate",
        }
        actual = {t.value for t in TaskType}
        assert expected == actual

    def test_model_provider_enum_complete(self):
        from umh.adapters.model_router import ModelProvider

        expected = {
            "claude_cli",
            "cc_sdk",
            "anthropic",
            "perplexity",
            "openai",
            "groq",
            "ollama",
            "gemini",
            "manus",
        }
        actual = {p.value for p in ModelProvider}
        assert expected == actual


class TestModelRouterCore:
    """Core routing logic tests."""

    def test_build_default_registry(self):
        from umh.adapters.model_router import build_default_registry

        registry = build_default_registry()
        assert len(registry) == 7
        assert "claude-haiku" in registry
        assert "gemini-pro" in registry
        assert "ollama-qwen" in registry

    def test_route_returns_none_when_nothing_available(self):
        from umh.adapters.model_router import ModelRouter, TaskType

        router = ModelRouter(registry={})
        result = router.route(TaskType.ANALYSIS)
        assert result is None

    def test_route_returns_config_when_available(self):
        from umh.adapters.model_router import (
            ModelConfig,
            ModelProvider,
            ModelRouter,
            TaskType,
        )

        registry = {
            "test-model": ModelConfig(
                provider=ModelProvider.OLLAMA,
                model_id="test:latest",
                api_key_env="",
                strengths=[TaskType.ANALYSIS],
                cost_per_1k=0.0,
                available=True,
            ),
        }
        router = ModelRouter(registry=registry)
        result = router.route(TaskType.ANALYSIS)
        assert result is not None
        assert result.model_id == "test:latest"

    def test_fallback_exhausts_then_returns_empty(self):
        from umh.adapters.model_router import ModelRouter, TaskType

        router = ModelRouter(registry={})
        result = router.call_with_fallback(TaskType.ANALYSIS, "test prompt")
        assert result == ""

    def test_routing_result_dataclass(self):
        from umh.adapters.model_router import RoutingResult

        r = RoutingResult(
            output="hello",
            provider="test",
            model="test-model",
            task_type="analysis",
        )
        assert r.output == "hello"
        assert r.tokens_used == 0
        assert r.latency_ms == 0

    def test_get_status_format(self):
        from umh.adapters.model_router import ModelRouter

        router = ModelRouter(registry={})
        status = router.get_status()
        assert "MODEL REGISTRY:" in status


class TestQualityEstimation:
    """Quality estimation and escalation tests."""

    def test_empty_output_scores_zero(self):
        from umh.adapters.model_router import estimate_quality_score

        assert estimate_quality_score("", "anthropic") == 0.0
        assert estimate_quality_score("   ", "anthropic") == 0.0

    def test_short_output_capped(self):
        from umh.adapters.model_router import estimate_quality_score

        score = estimate_quality_score("hi", "anthropic")
        assert score <= 0.3

    def test_refusal_pattern_capped(self):
        from umh.adapters.model_router import estimate_quality_score

        score = estimate_quality_score(
            "I cannot help with that request because it violates policy.",
            "anthropic",
        )
        assert score <= 0.4

    def test_normal_output_uses_provider_baseline(self):
        from umh.adapters.model_router import estimate_quality_score, PROVIDER_QUALITY

        long_output = "This is a detailed analysis of the market trends. " * 10
        score = estimate_quality_score(long_output, "anthropic")
        assert score == PROVIDER_QUALITY["anthropic"]

    def test_should_escalate_on_low_quality(self):
        from umh.adapters.model_router import should_escalate

        assert should_escalate("", "ollama") is True
        assert should_escalate("x", "ollama") is True

    def test_should_not_escalate_on_good_quality(self):
        from umh.adapters.model_router import should_escalate

        good = "This is a thorough and comprehensive analysis of the situation." * 5
        assert should_escalate(good, "anthropic") is False


class TestSingleton:
    """Module-level singleton behavior."""

    def test_get_router_returns_same_instance(self):
        from umh.adapters.model_router import get_router

        a = get_router()
        b = get_router()
        assert a is b

    def test_reset_router_clears_singleton(self):
        from umh.adapters.model_router import get_router, reset_router

        a = get_router()
        reset_router()
        b = get_router()
        assert a is not b
        reset_router()


class TestCCModelMap:
    """CC model map tests."""

    def test_cc_model_map_covers_all_task_types(self):
        from umh.adapters.model_router import CC_MODEL_MAP, TaskType

        for tt in TaskType:
            if tt.value in (
                "autonomous",
                "multimodal",
                "browser_control",
            ):
                continue
            assert tt.value in CC_MODEL_MAP, (
                f"Missing CC_MODEL_MAP entry for {tt.value}"
            )

    def test_strategic_maps_to_opus(self):
        from umh.adapters.model_router import CC_MODEL_MAP

        assert "opus" in CC_MODEL_MAP["strategic"]

    def test_fast_maps_to_haiku(self):
        from umh.adapters.model_router import CC_MODEL_MAP

        assert "haiku" in CC_MODEL_MAP["fast_response"]


class TestLegacyCompatibility:
    """umh.runtime_engine.model_router backward compatibility."""

    def test_legacy_import_path(self):
        from umh.runtime_engine.model_router import (
            TaskType,
            ModelProvider,
            RoutingResult,
            call_with_fallback,
            get_router,
        )

        assert TaskType is not None
        assert ModelProvider is not None
        assert RoutingResult is not None
        assert callable(call_with_fallback)
        assert callable(get_router)

    def test_legacy_types_are_umh_types(self):
        from umh.runtime_engine.model_router import TaskType as LegacyTT
        from umh.adapters.model_router import TaskType as UmhTT

        assert LegacyTT is UmhTT

    def test_agent_runtime_import(self):
        from umh.runtime_engine.agent_runtime import AgentRuntime, TaskType

        assert AgentRuntime is not None
        assert TaskType is not None

    def test_adversarial_code_review_passthrough(self):
        from umh.runtime_engine.model_router import adversarial_code_review

        code = "def hello(): return 42"
        assert adversarial_code_review(code) == code


class TestProviderPriority:
    """Provider priority tables."""

    def test_default_priority_has_all_providers(self):
        from umh.adapters.model_router import PROVIDER_PRIORITY, ModelProvider

        for p in ModelProvider:
            assert p in PROVIDER_PRIORITY, f"Missing {p} in PROVIDER_PRIORITY"

    def test_fast_priority_has_all_providers(self):
        from umh.adapters.model_router import PROVIDER_PRIORITY_FAST, ModelProvider

        for p in ModelProvider:
            assert p in PROVIDER_PRIORITY_FAST, f"Missing {p} in PROVIDER_PRIORITY_FAST"

    def test_fast_task_types_defined(self):
        from umh.adapters.model_router import FAST_TASK_TYPES

        assert "fast_response" in FAST_TASK_TYPES
        assert "conversation" in FAST_TASK_TYPES
        assert "strategic" not in FAST_TASK_TYPES
