"""Wave 8 validation — Context Assembly Collapse tests.

Proves that:
1. All LLM calls go through the execution engine (no direct adapter calls)
2. utility_llm_call routes through lightweight_execute → execute()
3. ContextBuilder is used for BOTH full runs and lightweight runs
4. No runtime.context_builder imports in UMH
5. LightweightTaskType enum defines canonical task types
6. No new eos_ai imports leaked into UMH
"""

from __future__ import annotations

import ast
import inspect
import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")

UMH_ROOT = "/opt/OS/umh"


class TestLightweightExecute:
    """lightweight_execute() routes through the full engine pipeline."""

    def test_importable(self):
        from umh.execution.engine import lightweight_execute

        assert callable(lightweight_execute)

    def test_signature(self):
        from umh.execution.engine import lightweight_execute

        sig = inspect.signature(lightweight_execute)
        params = list(sig.parameters.keys())
        assert "operation" in params
        assert "prompt" in params
        assert "system" in params
        assert "task_type" in params

    def test_returns_execution_result(self):
        from umh.execution.engine import lightweight_execute
        from umh.execution.contract import ExecutionResult

        result = lightweight_execute("test_op", "hello world")
        assert isinstance(result, ExecutionResult)

    def test_uses_context_builder(self):
        src_path = os.path.join(UMH_ROOT, "execution", "engine.py")
        with open(src_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "lightweight_execute":
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None
                assert "ContextBuilder" in func_source
                assert "ContextSection" in func_source
                return
        pytest.fail("lightweight_execute function not found")

    def test_calls_execute_not_dispatch_prompt(self):
        src_path = os.path.join(UMH_ROOT, "execution", "engine.py")
        with open(src_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "lightweight_execute":
                assert "return execute(request)" in ast.get_source_segment(source, node)
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        name = ""
                        if isinstance(func, ast.Name):
                            name = func.id
                        elif isinstance(func, ast.Attribute):
                            name = func.attr
                        assert name != "dispatch_prompt", (
                            "lightweight_execute should call execute(), not dispatch_prompt()"
                        )
                return
        pytest.fail("lightweight_execute function not found")

    def test_sets_execution_class_llm_call(self):
        src_path = os.path.join(UMH_ROOT, "execution", "engine.py")
        with open(src_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "lightweight_execute":
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None
                assert "ExecutionClass.LLM_CALL" in func_source
                return
        pytest.fail("lightweight_execute function not found")


class TestLightweightTaskType:
    """Canonical lightweight task types are defined in the engine."""

    def test_importable(self):
        from umh.execution.engine import LightweightTaskType

        assert LightweightTaskType is not None

    def test_expected_members(self):
        from umh.execution.engine import LightweightTaskType

        expected = {
            "CLASSIFY_INTENT",
            "EXTRACT_ENTITIES",
            "SUMMARIZE",
            "SHORT_RESPONSE",
            "VALIDATION",
        }
        actual = {m.name for m in LightweightTaskType}
        assert expected == actual

    def test_values_are_strings(self):
        from umh.execution.engine import LightweightTaskType

        for member in LightweightTaskType:
            assert isinstance(member.value, str)

    def test_is_str_enum(self):
        from umh.execution.engine import LightweightTaskType

        assert issubclass(LightweightTaskType, str)


class TestUtilityLLMCallRoutesCorrectly:
    """utility_llm_call goes through lightweight_execute, not dispatch_prompt."""

    def test_uses_lightweight_execute(self):
        src_path = os.path.join(UMH_ROOT, "gateway", "entry.py")
        with open(src_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "utility_llm_call":
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None
                assert "lightweight_execute" in func_source
                assert "dispatch_prompt" not in func_source
                return
        pytest.fail("utility_llm_call function not found")

    def test_no_direct_adapter_call(self):
        src_path = os.path.join(UMH_ROOT, "gateway", "entry.py")
        with open(src_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "utility_llm_call":
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None
                assert "get_adapter" not in func_source
                assert "llm.generate" not in func_source
                return
        pytest.fail("utility_llm_call function not found")

    def test_returns_string(self):
        from umh.gateway.entry import utility_llm_call

        result = utility_llm_call("hello")
        assert isinstance(result, str)


class TestContextBuilderUsedByBothPaths:
    """ContextBuilder is the ONLY context assembly mechanism in UMH."""

    def test_run_py_uses_context_builder(self):
        run_path = os.path.join(UMH_ROOT, "run.py")
        with open(run_path) as f:
            source = f.read()
        assert "from umh.context.builder import ContextBuilder" in source

    def test_lightweight_execute_uses_context_builder(self):
        engine_path = os.path.join(UMH_ROOT, "execution", "engine.py")
        with open(engine_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "lightweight_execute":
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None
                assert "ContextBuilder" in func_source
                return
        pytest.fail("lightweight_execute not found in engine.py")

    def test_context_builder_is_umh_native(self):
        builder_path = os.path.join(UMH_ROOT, "context", "builder.py")
        with open(builder_path) as f:
            source = f.read()
        assert "from eos_ai" not in source
        assert "import eos_ai" not in source


class TestNoEosContextBuilderInUMH:
    """Post Phase 14: context_builder is part of UMH runtime_engine. No eos/eos_ai refs."""

    def test_no_legacy_context_builder_imports(self):
        violations = []
        for dirpath, _, filenames in os.walk(UMH_ROOT):
            if "__pycache__" in dirpath:
                continue
            for f in filenames:
                if not f.endswith(".py"):
                    continue
                filepath = os.path.join(dirpath, f)
                with open(filepath) as fh:
                    source = fh.read()
                if "from eos.context_builder" in source or "from runtime.context_builder" in source:
                    violations.append(filepath)
        assert violations == [], "Legacy context_builder refs:\n" + "\n".join(violations)


class TestNoDirectAdapterCallsOutsideEngine:
    """No UMH module outside execution/ calls adapters directly."""

    def test_gateway_entry_no_adapter_import(self):
        entry_path = os.path.join(UMH_ROOT, "gateway", "entry.py")
        with open(entry_path) as f:
            source = f.read()
        assert "from umh.adapters.base import" not in source
        assert "get_adapter" not in source

    def test_gateway_no_dispatch_prompt(self):
        entry_path = os.path.join(UMH_ROOT, "gateway", "entry.py")
        with open(entry_path) as f:
            source = f.read()
        assert "dispatch_prompt" not in source


class TestExecutionEngineStructure:
    """Engine has two entry points, one pipeline."""

    def test_execute_exists(self):
        from umh.execution.engine import execute

        assert callable(execute)

    def test_dispatch_prompt_exists(self):
        from umh.execution.engine import dispatch_prompt

        assert callable(dispatch_prompt)

    def test_lightweight_execute_exists(self):
        from umh.execution.engine import lightweight_execute

        assert callable(lightweight_execute)

    def test_lightweight_task_type_exists(self):
        from umh.execution.engine import LightweightTaskType

        assert len(LightweightTaskType) == 5


class TestNoNewEosImportsInUMH:
    """Full UMH scan — no new eos_ai imports leaked during Wave 8."""

    def test_no_eos_ai_imports_in_umh(self):
        from tests.unit.test_umh_boundaries import ALLOWED_EOS_IMPORTS

        allowed: dict[str, set[str]] = {}
        for rel_path, entries in ALLOWED_EOS_IMPORTS.items():
            abs_path = os.path.join(UMH_ROOT, rel_path.removeprefix("umh/"))
            allowed[abs_path] = {e["import"] for e in entries}

        violations = []
        for dirpath, _, filenames in os.walk(UMH_ROOT):
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
                            node.module.startswith(("services.", "interfaces.", "scripts.", "eos.", "runtime."))
                            and node.module not in allowed_mods
                        ):
                            violations.append(
                                f"{filepath}:{node.lineno} from {node.module}"
                            )
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if (
                                alias.name.startswith(("services.", "interfaces.", "scripts.", "eos.", "runtime."))
                                and alias.name not in allowed_mods
                            ):
                                violations.append(
                                    f"{filepath}:{node.lineno} import {alias.name}"
                                )
        assert violations == [], "eos_ai imports found in UMH:\n" + "\n".join(
            violations
        )
