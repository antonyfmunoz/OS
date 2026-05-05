"""Wave 7 validation — Gateway Collapse tests.

Proves that:
1. UMH gateway entry contract works standalone (no eos_ai)
2. All service/gateway LLM calls route through UMH, not model_router directly
3. Compatibility wrappers preserve existing import paths
4. No new eos_ai imports leaked into UMH
"""

from __future__ import annotations

import ast
import inspect
import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")

UMH_ROOT = "/opt/OS/umh"
INTERFACES_ROOT = "/opt/OS/umh/interfaces"
GATEWAY_FILE = "/opt/OS/umh/runtime_engine/gateway.py"


class TestUMHGatewayStandalone:
    """UMH gateway module has zero eos_ai dependencies."""

    def test_imports_without_eos_ai(self):
        from umh.gateway import UMHInput, UMHOutput, translate_and_run, utility_llm_call

        assert UMHInput is not None
        assert UMHOutput is not None
        assert callable(translate_and_run)
        assert callable(utility_llm_call)

    def test_no_eos_ai_in_gateway_source(self):
        entry_path = os.path.join(UMH_ROOT, "gateway", "entry.py")
        with open(entry_path) as f:
            source = f.read()
        assert "from eos_ai" not in source
        assert "import eos_ai" not in source

    def test_gateway_entry_uses_umh_execution_engine(self):
        entry_path = os.path.join(UMH_ROOT, "gateway", "entry.py")
        with open(entry_path) as f:
            source = f.read()
        assert "lightweight_execute" in source

    def test_gateway_init_exports(self):
        import umh.gateway

        assert hasattr(umh.gateway, "UMHInput")
        assert hasattr(umh.gateway, "UMHOutput")
        assert hasattr(umh.gateway, "translate_and_run")
        assert hasattr(umh.gateway, "utility_llm_call")


class TestUMHInput:
    """UMHInput contract validation."""

    def test_minimal_construction(self):
        from umh.gateway import UMHInput

        inp = UMHInput(source="discord", raw_input="hello")
        assert inp.source == "discord"
        assert inp.raw_input == "hello"
        assert inp.metadata == {}
        assert inp.attachments == []
        assert inp.org_id == "default"

    def test_full_construction(self):
        from umh.gateway import UMHInput
        from umh.governance.authority import AuthorityLevel

        inp = UMHInput(
            source="telegram",
            raw_input="run report",
            metadata={"user_id": "u123", "channel_id": "c456"},
            attachments=[{"type": "image", "url": "https://example.com/img.png"}],
            authority=AuthorityLevel.EXECUTE,
            org_id="org_test",
            constraints={"max_tokens": 500},
        )
        assert inp.source == "telegram"
        assert inp.metadata["user_id"] == "u123"
        assert len(inp.attachments) == 1
        assert inp.authority == AuthorityLevel.EXECUTE
        assert inp.org_id == "org_test"

    def test_required_fields(self):
        from umh.gateway import UMHInput

        sig = inspect.signature(UMHInput)
        params = sig.parameters
        required = [
            n for n, p in params.items() if p.default is inspect.Parameter.empty
        ]
        assert "source" in required
        assert "raw_input" in required

    def test_optional_fields_have_defaults(self):
        from umh.gateway import UMHInput

        sig = inspect.signature(UMHInput)
        params = sig.parameters
        for name in ["metadata", "attachments", "authority", "org_id", "constraints"]:
            assert (
                params[name].default is not inspect.Parameter.empty
                or name == "authority"
            )


class TestUMHOutput:
    """UMHOutput contract validation."""

    def test_from_run_result(self):
        from umh.gateway import UMHOutput
        from umh.run import RunResult, RunTrace

        trace = RunTrace(run_id="r1", started_at="2026-01-01T00:00:00Z")
        result = RunResult(
            run_id="r1",
            response="done",
            success=True,
            operation="test_op",
            capability_used="llm",
            trace=trace,
            metadata={"key": "val"},
        )
        output = UMHOutput.from_run_result(result)
        assert output.success is True
        assert output.response == "done"
        assert output.run_id == "r1"
        assert output.operation == "test_op"

    def test_error_factory(self):
        from umh.gateway import UMHOutput

        output = UMHOutput.error("something broke", source="test")
        assert output.success is False
        assert "something broke" in output.response
        assert output.metadata["error_source"] == "test"


class TestUtilityLLMCall:
    """utility_llm_call routes through UMH execution engine."""

    def test_callable(self):
        from umh.gateway.entry import utility_llm_call

        assert callable(utility_llm_call)

    def test_signature(self):
        from umh.gateway.entry import utility_llm_call

        sig = inspect.signature(utility_llm_call)
        params = list(sig.parameters.keys())
        assert "prompt" in params
        assert "system" in params
        assert "operation" in params

    def test_uses_execution_engine(self):
        src_path = os.path.join(UMH_ROOT, "gateway", "entry.py")
        with open(src_path) as f:
            source = f.read()
        assert "from umh.execution.engine import lightweight_execute" in source


class TestGatewayBypassesEliminated:
    """All LLM bypasses in gateway.py now route through UMH."""

    def test_no_model_router_imports_in_gateway(self):
        with open(GATEWAY_FILE) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "model_router" in node.module:
                    pytest.fail(
                        f"gateway.py still imports model_router at line {node.lineno}: "
                        f"from {node.module}"
                    )

    def test_classify_intent_uses_umh(self):
        with open(GATEWAY_FILE) as f:
            source = f.read()
        assert "utility_llm_call" in source

    def test_web_search_uses_umh(self):
        with open(GATEWAY_FILE) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_web_search":
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None, "_web_search not found"
                assert "utility_llm_call" in func_source, (
                    "_web_search does not use utility_llm_call"
                )
                return
        pytest.fail("_web_search function not found in gateway.py")

    def test_email_instruction_uses_umh(self):
        with open(GATEWAY_FILE) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_handle_email_instruction"
            ):
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None
                assert "utility_llm_call" in func_source, (
                    "_handle_email_instruction does not use utility_llm_call"
                )
                return
        pytest.fail("_handle_email_instruction not found in gateway.py")


class TestServiceBypassesEliminated:
    """Services no longer call model_router directly for LLM operations."""

    def _check_no_model_router_calls(self, filepath: str, label: str):
        """Verify a file has no direct model_router import-for-call patterns."""
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "model_router" in node.module:
                    names = [a.name for a in node.names] if node.names else []
                    call_imports = {"call_with_fallback", "get_router"}
                    if call_imports & set(names):
                        pytest.fail(
                            f"{label} imports model_router call functions at "
                            f"line {node.lineno}: {names}"
                        )

    def test_intent_handler_clean(self):
        self._check_no_model_router_calls(
            os.path.join(INTERFACES_ROOT, "discord", "handlers", "intent_handler.py"),
            "intent_handler.py",
        )

    def test_cc_command_handler_clean(self):
        self._check_no_model_router_calls(
            os.path.join(INTERFACES_ROOT, "discord", "handlers", "cc_command_handler.py"),
            "cc_command_handler.py",
        )

    def test_calendly_webhook_clean(self):
        self._check_no_model_router_calls(
            os.path.join(INTERFACES_ROOT, "webhooks", "calendly.py"),
            "calendly.py",
        )

    def test_dm_monitor_clean(self):
        self._check_no_model_router_calls(
            os.path.join(INTERFACES_ROOT, "discord", "dm_monitor.py"),
            "dm_monitor.py",
        )

    def test_discord_bot_no_call_site(self):
        filepath = os.path.join(INTERFACES_ROOT, "discord", "bot.py")
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "model_router" in node.module:
                    names = [a.name for a in node.names] if node.names else []
                    call_imports = {"call_with_fallback", "get_router"}
                    if call_imports & set(names):
                        pytest.fail(
                            f"discord_bot.py imports model_router call functions at "
                            f"line {node.lineno}: {names}"
                        )


class TestTranslateAndRun:
    """translate_and_run wraps umh.run() correctly."""

    def test_callable(self):
        from umh.gateway.entry import translate_and_run

        assert callable(translate_and_run)

    def test_returns_umh_output(self):
        from umh.gateway.entry import UMHInput, UMHOutput, translate_and_run

        inp = UMHInput(source="test", raw_input="hello world")
        result = translate_and_run(inp)
        assert isinstance(result, UMHOutput)

    def test_error_returns_umh_output(self):
        from umh.gateway.entry import UMHInput, UMHOutput, translate_and_run

        inp = UMHInput(source="test", raw_input="")
        result = translate_and_run(inp)
        assert isinstance(result, UMHOutput)


class TestNoNewEosImportsInUMH:
    """Full UMH scan — no new eos_ai imports leaked during Wave 7."""

    def test_no_eos_ai_imports_in_umh(self):
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
                            node.module.startswith(("services.", "interfaces.", "scripts.", "eos.", "eos_ai."))
                            and node.module not in allowed_mods
                        ):
                            violations.append(
                                f"{filepath}:{node.lineno} from {node.module}"
                            )
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if (
                                alias.name.startswith(("services.", "interfaces.", "scripts.", "eos.", "eos_ai."))
                                and alias.name not in allowed_mods
                            ):
                                violations.append(
                                    f"{filepath}:{node.lineno} import {alias.name}"
                                )
        assert violations == [], "eos_ai imports found in UMH:\n" + "\n".join(
            violations
        )
