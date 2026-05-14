"""Tests for UMH real LLM adapters.

Covers:
  1. Import boundaries — no EOS imports in adapter modules
  2. OllamaLLMAdapter — protocol compliance, config, availability
  3. HttpLLMAdapter — protocol compliance, config, validation
  4. Auto-discovery — Ollama → HTTP → None chain
  5. Adapter registration — set/get/reset with real adapters
  6. Null fallback — still works when real adapters unavailable
  7. Run loop integration — umh.run() uses real adapter when registered
  8. Safety — no shell/browser execution enabled by real adapter
  9. No module-level EOS imports in new files
"""

import ast
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from unittest.mock import patch

import pytest

sys.path.insert(0, "/opt/OS")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Import Boundaries
# ═══════════════════════════════════════════════════════════════════════════════


class TestLLMAdapterImports:
    def test_llm_module_imports(self):
        from umh.adapters.llm import (
            OllamaLLMAdapter,
            HttpLLMAdapter,
            discover_llm_adapter,
        )

        assert callable(discover_llm_adapter)

    def test_no_eos_imports_in_llm_module(self):
        filepath = "/opt/OS/umh/adapters/llm.py"
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filepath)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("umh.runtime_engine."), (
                    f"llm.py has EOS import: {node.module} at line {node.lineno}"
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("umh.runtime_engine."), (
                        f"llm.py has EOS import: {alias.name} at line {node.lineno}"
                    )

    def test_no_eos_imports_in_base_module(self):
        filepath = "/opt/OS/umh/adapters/base.py"
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filepath)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("umh.runtime_engine."), (
                    f"base.py has top-level EOS import: {node.module}"
                )

    def test_llm_adapter_uses_only_stdlib(self):
        filepath = "/opt/OS/umh/adapters/llm.py"
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filepath)
        allowed_modules = {
            "__future__",
            "json",
            "os",
            "urllib",
            "urllib.error",
            "urllib.request",
            "typing",
        }
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                top_module = node.module.split(".")[0]
                assert top_module in allowed_modules, (
                    f"llm.py imports non-stdlib: {node.module}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. OllamaLLMAdapter
# ═══════════════════════════════════════════════════════════════════════════════


class TestOllamaLLMAdapter:
    def test_protocol_compliance(self):
        from umh.adapters.base import LLMAdapter
        from umh.adapters.llm import OllamaLLMAdapter

        adapter = OllamaLLMAdapter()
        assert isinstance(adapter, LLMAdapter)

    def test_default_config(self):
        from umh.adapters.llm import OllamaLLMAdapter

        adapter = OllamaLLMAdapter()
        assert adapter.host == "http://localhost:11434"
        assert adapter.model == "qwen2.5:0.5b"

    def test_custom_config(self):
        from umh.adapters.llm import OllamaLLMAdapter

        adapter = OllamaLLMAdapter(
            host="http://custom:1234",
            model="llama3:8b",
            timeout=60,
        )
        assert adapter.host == "http://custom:1234"
        assert adapter.model == "llama3:8b"

    def test_env_config(self):
        from umh.adapters.llm import OllamaLLMAdapter

        with patch.dict(
            os.environ,
            {
                "UMH_OLLAMA_HOST": "http://envhost:9999",
                "UMH_OLLAMA_MODEL": "gemma:2b",
            },
        ):
            adapter = OllamaLLMAdapter()
            assert adapter.host == "http://envhost:9999"
            assert adapter.model == "gemma:2b"

    def test_repr(self):
        from umh.adapters.llm import OllamaLLMAdapter

        adapter = OllamaLLMAdapter()
        r = repr(adapter)
        assert "OllamaLLMAdapter" in r
        assert "qwen2.5:0.5b" in r

    def test_unavailable_when_unreachable(self):
        from umh.adapters.llm import OllamaLLMAdapter

        adapter = OllamaLLMAdapter(host="http://127.0.0.1:59999")
        assert not adapter.available()

    def test_available_caches_result(self):
        from umh.adapters.llm import OllamaLLMAdapter

        adapter = OllamaLLMAdapter(host="http://127.0.0.1:59999")
        adapter.available()
        assert adapter._reachable is False
        adapter.available()
        assert adapter._reachable is False


# ═══════════════════════════════════════════════════════════════════════════════
# 3. HttpLLMAdapter
# ═══════════════════════════════════════════════════════════════════════════════


class TestHttpLLMAdapter:
    def test_protocol_compliance(self):
        from umh.adapters.base import LLMAdapter
        from umh.adapters.llm import HttpLLMAdapter

        adapter = HttpLLMAdapter(url="http://localhost:8080")
        assert isinstance(adapter, LLMAdapter)

    def test_requires_url(self):
        from umh.adapters.llm import HttpLLMAdapter

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("UMH_LLM_URL", None)
            with pytest.raises(ValueError, match="requires a URL"):
                HttpLLMAdapter()

    def test_url_normalization(self):
        from umh.adapters.llm import HttpLLMAdapter

        adapter = HttpLLMAdapter(url="http://localhost:8080")
        assert "/v1/chat/completions" in adapter._url

    def test_url_with_v1_already(self):
        from umh.adapters.llm import HttpLLMAdapter

        adapter = HttpLLMAdapter(url="http://localhost:8080/v1/chat/completions")
        assert adapter._url == "http://localhost:8080/v1/chat/completions"

    def test_custom_model_and_key(self):
        from umh.adapters.llm import HttpLLMAdapter

        adapter = HttpLLMAdapter(
            url="http://api.example.com",
            model="gpt-4o",
            api_key="sk-test123",
        )
        assert adapter.model == "gpt-4o"

    def test_always_available(self):
        from umh.adapters.llm import HttpLLMAdapter

        adapter = HttpLLMAdapter(url="http://localhost:8080")
        assert adapter.available()

    def test_repr(self):
        from umh.adapters.llm import HttpLLMAdapter

        adapter = HttpLLMAdapter(url="http://localhost:8080", model="test-model")
        r = repr(adapter)
        assert "HttpLLMAdapter" in r
        assert "test-model" in r


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Auto-discovery
# ═══════════════════════════════════════════════════════════════════════════════


class TestDiscovery:
    def test_returns_ollama_when_reachable(self):
        from umh.adapters.llm import OllamaLLMAdapter, discover_llm_adapter

        result = discover_llm_adapter()
        # On this system Ollama is running, so it should find it
        if result is not None:
            assert isinstance(result, OllamaLLMAdapter)
            assert result.available()

    def test_returns_http_when_ollama_down_and_url_set(self):
        from umh.adapters.llm import HttpLLMAdapter, discover_llm_adapter

        with patch.dict(
            os.environ,
            {
                "UMH_OLLAMA_HOST": "http://127.0.0.1:59999",
                "UMH_LLM_URL": "http://some-api.example.com",
            },
        ):
            result = discover_llm_adapter()
            assert isinstance(result, HttpLLMAdapter)

    def test_returns_none_when_nothing_available(self):
        from umh.adapters.llm import discover_llm_adapter

        with patch.dict(
            os.environ,
            {
                "UMH_OLLAMA_HOST": "http://127.0.0.1:59999",
            },
        ):
            os.environ.pop("UMH_LLM_URL", None)
            result = discover_llm_adapter()
            assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Adapter Registration
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdapterRegistration:
    def test_set_real_adapter(self):
        from umh.adapters.base import get_adapter, set_adapter, reset_adapters
        from umh.adapters.llm import OllamaLLMAdapter

        reset_adapters()
        real = OllamaLLMAdapter(host="http://127.0.0.1:59999")
        set_adapter("llm", real)
        got = get_adapter("llm")
        assert isinstance(got, OllamaLLMAdapter)
        reset_adapters()

    def test_reset_clears_real_adapter(self):
        from umh.adapters.base import (
            get_adapter,
            set_adapter,
            reset_adapters,
            NullLLMAdapter,
        )
        from umh.adapters.llm import OllamaLLMAdapter

        set_adapter("llm", OllamaLLMAdapter(host="http://127.0.0.1:59999"))
        reset_adapters()

        # After reset, auto-discovery runs again.
        # On this system Ollama is up, so it will find the real one.
        # Just verify it returns *something* that satisfies LLMAdapter.
        got = get_adapter("llm")
        assert got.available() or isinstance(got, NullLLMAdapter)

    def test_auto_discovery_on_first_access(self):
        from umh.adapters.base import get_adapter, reset_adapters

        reset_adapters()
        llm = get_adapter("llm")
        # Should be either OllamaLLMAdapter (if Ollama running) or NullLLMAdapter
        assert hasattr(llm, "generate")
        assert hasattr(llm, "available")
        reset_adapters()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Null Fallback
# ═══════════════════════════════════════════════════════════════════════════════


class TestNullFallback:
    def test_null_still_works(self):
        from umh.adapters.base import NullLLMAdapter

        null = NullLLMAdapter()
        assert null.available()
        result = null.generate("hello world")
        assert "hello" in result

    def test_force_null_via_set_adapter(self):
        from umh.adapters.base import (
            NullLLMAdapter,
            get_adapter,
            set_adapter,
            reset_adapters,
        )

        reset_adapters()
        set_adapter("llm", NullLLMAdapter())
        llm = get_adapter("llm")
        assert isinstance(llm, NullLLMAdapter)
        result = llm.generate("test prompt")
        assert "[null-llm]" in result
        reset_adapters()

    def test_run_with_null_adapter(self):
        from umh.adapters.base import NullLLMAdapter, set_adapter, reset_adapters
        from umh.capability.registry import (
            Capability,
            CapabilityRegistry,
            set_registry,
            reset_registry,
        )
        from umh.feedback.loop import clear_feedback_log
        from umh.governance.authority import reset_governance_policy
        from umh.memory.storage import reset_storage
        from umh.run import run

        reset_adapters()
        reset_governance_policy()
        reset_storage()
        clear_feedback_log()
        set_adapter("llm", NullLLMAdapter())

        reg = CapabilityRegistry()
        reg.register(
            Capability(
                name="null_llm",
                capability_type="llm",
                description="Null LLM for test",
                quality_score=0.9,
            )
        )
        set_registry(reg)

        result = run("What is the status?")
        assert result.success
        assert "[null-llm]" in result.response
        reset_adapters()
        reset_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Run Loop Integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestRunLoopIntegration:
    def _reset_all(self):
        from umh.adapters.base import reset_adapters
        from umh.capability.registry import reset_registry
        from umh.feedback.loop import clear_feedback_log
        from umh.governance.authority import reset_governance_policy
        from umh.memory.storage import reset_storage

        reset_adapters()
        reset_registry()
        reset_governance_policy()
        reset_storage()
        clear_feedback_log()

    def test_run_uses_discovered_adapter(self):
        self._reset_all()
        from umh.adapters.base import get_adapter
        from umh.run import run

        result = run("What is 2 + 2?")
        assert result.success
        llm = get_adapter("llm")
        adapter_type = type(llm).__name__
        assert adapter_type in ("OllamaLLMAdapter", "NullLLMAdapter")

    def test_run_with_explicitly_set_adapter(self):
        self._reset_all()
        from umh.adapters.base import set_adapter
        from umh.adapters.llm import OllamaLLMAdapter
        from umh.run import run

        # Set a deliberately unreachable adapter, verify run still handles it
        set_adapter("llm", OllamaLLMAdapter(host="http://127.0.0.1:59999"))
        result = run("test")
        # Should fail gracefully since adapter can't connect
        assert result.run_id.startswith("run_")
        from umh.adapters.base import reset_adapters

        reset_adapters()


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Safety Boundaries
# ═══════════════════════════════════════════════════════════════════════════════


class TestSafetyBoundaries:
    def test_shell_still_disabled(self):
        from umh.adapters.base import get_adapter, reset_adapters

        reset_adapters()
        shell = get_adapter("shell")
        assert not shell.available()
        code, out = shell.run("echo hi")
        assert code == 1
        reset_adapters()

    def test_browser_still_disabled(self):
        from umh.adapters.base import get_adapter, reset_adapters

        reset_adapters()
        browser = get_adapter("browser")
        assert not browser.available()
        reset_adapters()

    def test_real_llm_adapter_has_no_shell_access(self):
        from umh.adapters.llm import OllamaLLMAdapter

        adapter = OllamaLLMAdapter()
        assert not hasattr(adapter, "run")
        assert not hasattr(adapter, "execute")
        assert not hasattr(adapter, "shell")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Live Ollama Integration (only runs when Ollama is up)
# ═══════════════════════════════════════════════════════════════════════════════


class TestOllamaLive:
    """Tests that hit the real Ollama API. Skipped if Ollama is unreachable."""

    @pytest.fixture(autouse=True)
    def check_ollama(self):
        from umh.adapters.llm import OllamaLLMAdapter

        adapter = OllamaLLMAdapter()
        if not adapter.available():
            pytest.skip("Ollama not available")
        self.adapter = adapter

    def test_generate_returns_nonempty(self):
        result = self.adapter.generate("Say hello in one word.")
        assert len(result) > 0

    def test_generate_with_system_prompt(self):
        result = self.adapter.generate(
            "What is 2 + 2?",
            system="You are a math tutor. Answer briefly.",
        )
        assert len(result) > 0

    def test_available_is_true(self):
        assert self.adapter.available()

    def test_full_run_with_ollama(self):
        from umh.adapters.base import reset_adapters
        from umh.capability.registry import reset_registry
        from umh.feedback.loop import clear_feedback_log
        from umh.governance.authority import reset_governance_policy
        from umh.memory.storage import reset_storage
        from umh.run import run

        reset_adapters()
        reset_registry()
        reset_governance_policy()
        reset_storage()
        clear_feedback_log()

        result = run("What is the capital of France?")
        assert result.success
        assert result.capability_used in ("llm_generation", "null_llm", "local_python")
        assert len(result.response) > 0

        reset_adapters()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
