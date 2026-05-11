"""Wave 0 validation — UMH standalone isolation tests.

Proves that UMH operates without eos_ai on the import path.
These tests MUST pass before any Wave 1+ work begins.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys

import pytest

sys.path.insert(0, "/opt/OS")

UMH_ROOT = "/opt/OS/umh"


class TestNoEosAiImports:
    """No Python file in umh/ may contain a direct eos_ai import
    unless documented in ALLOWED_EOS_IMPORTS (test_umh_boundaries.py)."""

    def _collect_umh_py_files(self) -> list[str]:
        result = []
        for dirpath, _dirnames, filenames in os.walk(UMH_ROOT):
            if "__pycache__" in dirpath:
                continue
            for f in filenames:
                if f.endswith(".py"):
                    result.append(os.path.join(dirpath, f))
        return result

    @staticmethod
    def _allowed_eos_imports() -> dict[str, set[str]]:
        from tests.unit.test_umh_boundaries import ALLOWED_EOS_IMPORTS

        allowed: dict[str, set[str]] = {}
        for rel_path, entries in ALLOWED_EOS_IMPORTS.items():
            abs_path = os.path.join(UMH_ROOT, rel_path.removeprefix("umh/"))
            allowed[abs_path] = {e["import"] for e in entries}
        return allowed

    def test_no_from_eos_ai_import(self):
        """No core file has 'from eos_ai' except documented transitional imports.

        umh/interfaces/ excluded — boundary layer legitimately references
        services/scripts for external system integration.
        """
        allowed = self._allowed_eos_imports()
        violations = []
        for filepath in self._collect_umh_py_files():
            if "/interfaces/" in filepath:
                continue
            allowed_mods = allowed.get(filepath, set())
            with open(filepath) as fh:
                source = fh.read()
            tree = ast.parse(source, filename=filepath)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if (
                        node.module.startswith(("services.", "interfaces.", "scripts."))
                        and node.module not in allowed_mods
                    ):
                        violations.append(
                            f"{filepath}:{node.lineno} from {node.module}"
                        )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if (
                            alias.name.startswith(("services.", "interfaces.", "scripts."))
                            and alias.name not in allowed_mods
                        ):
                            violations.append(
                                f"{filepath}:{node.lineno} import {alias.name}"
                            )
        assert violations == [], f"eos_ai imports found:\n" + "\n".join(violations)

    def test_bridge_is_only_eos_code_reference(self):
        """No file outside bridge.py has undocumented eos_ai imports."""
        allowed = self._allowed_eos_imports()
        violations = []
        for filepath in self._collect_umh_py_files():
            if filepath.endswith("bridge.py"):
                continue
            allowed_mods = allowed.get(filepath, set())
            with open(filepath) as fh:
                source = fh.read()
            tree = ast.parse(source, filename=filepath)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if (node.module.startswith("eos.") or node.module.startswith("runtime.")) and node.module not in allowed_mods:
                        violations.append(
                            f"{filepath}:{node.lineno} from {node.module}"
                        )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if (alias.name.startswith("eos.") or alias.name.startswith("runtime.")) and alias.name not in allowed_mods:
                            violations.append(
                                f"{filepath}:{node.lineno} import {alias.name}"
                            )
        assert violations == [], (
            f"eos_ai import references outside bridge.py:\n" + "\n".join(violations)
        )


class TestStandaloneImport:
    """UMH imports and runs without eos_ai available."""

    def test_umh_import_succeeds(self):
        from umh import run, RunResult, RunTrace

        assert callable(run)
        assert RunResult is not None
        assert RunTrace is not None

    def test_all_subsystems_importable(self):
        import umh.adapters.base
        import umh.adapters.bridge
        import umh.adapters.llm
        import umh.capability.registry
        import umh.capability.router
        import umh.context.builder
        import umh.context.budget
        import umh.context.types
        import umh.decision.trace
        import umh.execution.contract
        import umh.execution.engine
        import umh.execution.harness
        import umh.execution.interfaces
        import umh.execution.pipeline
        import umh.execution.quality
        import umh.execution.runtime
        import umh.execution.stages
        import umh.gateway
        import umh.gateway.entry
        import umh.feedback.dynamics
        import umh.feedback.loop
        import umh.goals.engine
        import umh.goals.interfaces
        import umh.goals.objective
        import umh.goals.state
        import umh.governance.authority
        import umh.governance.capability
        import umh.governance.governor
        import umh.intent.compiler
        import umh.memory.storage
        import umh.primitives.ontological
        import umh.signal.event_bus
        import umh.signal.ingest
        import umh.signal.types
        import umh.strategy.interfaces
        import umh.strategy.memory
        import umh.world.calibration
        import umh.world.dynamics_adapter
        import umh.world.model
        import umh.world.reasoning
        import umh.world.simulation
        import umh.world.state
        import umh.world.substrate
        import umh.world.types

    def test_bridge_returns_none_without_platform(self):
        from umh.adapters.bridge import discover_platform_adapter

        result = discover_platform_adapter("nonexistent.module.path", "factory_fn")
        assert result is None

    def test_bridge_returns_none_for_bad_factory(self):
        from umh.adapters.bridge import discover_platform_adapter

        result = discover_platform_adapter("os", "nonexistent_function")
        assert result is None


class TestControlPlaneInvariant:
    """run.py delegates execution through execution/engine, not directly."""

    def test_run_py_no_get_adapter_call(self):
        """run.py must not call get_adapter() directly."""
        run_path = os.path.join(UMH_ROOT, "run.py")
        with open(run_path) as fh:
            source = fh.read()
        tree = ast.parse(source, filename=run_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "get_adapter":
                    pytest.fail("run.py calls get_adapter() directly")
                if isinstance(func, ast.Attribute) and func.attr == "get_adapter":
                    pytest.fail("run.py calls get_adapter() directly")

    def test_run_py_no_execute_via_adapter(self):
        """run.py must not define _execute_via_adapter."""
        run_path = os.path.join(UMH_ROOT, "run.py")
        with open(run_path) as fh:
            source = fh.read()
        assert "_execute_via_adapter" not in source

    def test_dispatch_prompt_exists_in_engine(self):
        """execution/engine.py must export dispatch_prompt."""
        from umh.execution.engine import dispatch_prompt

        assert callable(dispatch_prompt)

    def test_run_uses_dispatch_prompt(self):
        """run.py must import dispatch_prompt from execution.engine."""
        run_path = os.path.join(UMH_ROOT, "run.py")
        with open(run_path) as fh:
            source = fh.read()
        assert "dispatch_prompt" in source


class TestAdapterBridgeCentralization:
    """All platform adapter discovery goes through bridge.py."""

    def test_goals_uses_bridge(self):
        from umh.goals import interfaces as mod

        with open(mod.__file__) as fh:
            source = fh.read()
        assert "discover_platform_adapter" in source
        assert "from eos_ai" not in source

    def test_strategy_uses_bridge(self):
        from umh.strategy import interfaces as mod

        with open(mod.__file__) as fh:
            source = fh.read()
        assert "discover_platform_adapter" in source
        assert "from eos_ai" not in source

    def test_storage_uses_bridge(self):
        from umh.memory import storage as mod

        with open(mod.__file__) as fh:
            source = fh.read()
        assert "discover_platform_adapter" in source
        assert "from eos_ai" not in source

    def test_execution_uses_bridge(self):
        from umh.execution import interfaces as mod

        with open(mod.__file__) as fh:
            source = fh.read()
        assert "discover_platform_adapter" in source
        assert "from eos_ai" not in source


class TestWorldStateDecontaminated:
    """world/state.py has no eos_ai dependency and accepts strategy data via params."""

    def test_no_eos_imports_in_state(self):
        from umh.world import state as mod

        with open(mod.__file__) as fh:
            source = fh.read()
        assert "from eos_ai" not in source
        assert "import eos_ai" not in source

    def test_extract_state_accepts_strategy_rankings(self):
        from umh.world.state import extract_state

        import inspect

        sig = inspect.signature(extract_state)
        assert "strategy_rankings" in sig.parameters
        assert "strategy_turn" in sig.parameters

    def test_extract_state_works_without_strategy(self):
        from umh.world.state import extract_state

        state = extract_state(current_turn=5)
        assert state.state_id.startswith("ws_")
        assert state.get_feature("strategy_variance") == 0.0

    def test_extract_state_works_with_strategy_rankings(self):
        from umh.world.state import extract_state
        from types import SimpleNamespace

        stats_a = SimpleNamespace(ema_score=0.8, uses=10)
        stats_a.effective_score = lambda turn: 0.8
        stats_b = SimpleNamespace(ema_score=0.3, uses=5)
        stats_b.effective_score = lambda turn: 0.3

        state = extract_state(
            current_turn=10,
            strategy_rankings=[("alpha", stats_a), ("beta", stats_b)],
            strategy_turn=10,
        )
        assert state.get_feature("strategy_variance") > 0.0
        strategy_entities = [e for e in state.entities if e.entity_type == "strategy"]
        assert len(strategy_entities) == 2

    def test_engine_extract_and_record_passes_strategy(self):
        from umh.world.state import WorldStateEngine
        from types import SimpleNamespace

        engine = WorldStateEngine()
        stats = SimpleNamespace(ema_score=0.5, uses=3)
        stats.effective_score = lambda turn: 0.5

        state = engine.extract_and_record(
            current_turn=1,
            strategy_rankings=[("only", stats)],
            strategy_turn=1,
        )
        assert state.state_id.startswith("ws_")
