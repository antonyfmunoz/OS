"""Phase 8B — Boundary and safety invariant tests."""

import sys

sys.path.insert(0, "/opt/OS")

import ast
import os
import pytest

from umh.strategy.models import Strategy, StrategyStep
from umh.strategy.validator import validate_strategy, MAX_STEPS


STRATEGY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "umh", "strategy")
STRATEGY_FILES = [
    os.path.join(STRATEGY_DIR, f)
    for f in ["models.py", "decomposer.py", "templates.py", "validator.py"]
    if os.path.exists(os.path.join(STRATEGY_DIR, f))
]


def _get_imports(filepath: str) -> set[str]:
    """Extract all import module names from a Python file."""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


def _get_full_imports(filepath: str) -> list[str]:
    """Extract all full import paths from a Python file."""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


class TestNoExecutionImports:
    """Verify strategy layer never imports execution/adapter/tool modules."""

    def test_no_execution_engine_import(self):
        for fpath in STRATEGY_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.execution.engine" not in imp, f"{fpath} imports umh.execution.engine"

    def test_no_adapter_import(self):
        for fpath in STRATEGY_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.adapters" not in imp, f"{fpath} imports umh.adapters"

    def test_no_tool_import(self):
        for fpath in STRATEGY_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.tools" not in imp, f"{fpath} imports umh.tools"


class TestNoExecuteCalls:
    """Verify strategy layer never calls execute()."""

    def test_no_execute_function_call(self):
        for fpath in STRATEGY_FILES:
            with open(fpath) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == "execute":
                        pytest.fail(f"{fpath} calls execute()")
                    if isinstance(func, ast.Attribute) and func.attr == "execute":
                        pytest.fail(f"{fpath} calls .execute()")


class TestNoGoalCreation:
    """Verify strategy layer never creates Goal objects (no recursion)."""

    def test_no_goal_instantiation(self):
        for fpath in STRATEGY_FILES:
            with open(fpath) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == "Goal":
                        # Allow in test files but not in strategy source
                        if "test" not in fpath:
                            pytest.fail(f"{fpath} instantiates Goal()")


class TestNoGoalEngineCall:
    """Verify strategy layer never calls GoalEngine (no recursion)."""

    def test_no_goal_engine_import(self):
        for fpath in STRATEGY_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "goal_engine" not in imp, f"{fpath} imports goal_engine — recursion risk"


class TestValidation:
    """Test strategy validation catches all constraint violations."""

    def test_valid_strategy(self):
        steps = [StrategyStep(description="a", id="s1")]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        errors = validate_strategy(s)
        assert errors == []

    def test_empty_steps(self):
        s = Strategy(goal_id="g1", objective="test")
        errors = validate_strategy(s)
        assert any("no steps" in e for e in errors)

    def test_too_many_steps(self):
        steps = [StrategyStep(description=f"step {i}", id=f"s{i}") for i in range(MAX_STEPS + 1)]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        errors = validate_strategy(s)
        assert any("max is" in e for e in errors)

    def test_duplicate_ids(self):
        steps = [
            StrategyStep(description="a", id="s1"),
            StrategyStep(description="b", id="s1"),
        ]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        errors = validate_strategy(s)
        assert any("duplicate" in e for e in errors)

    def test_invalid_dependency(self):
        steps = [
            StrategyStep(description="a", id="s1", dependencies=["nonexistent"]),
        ]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        errors = validate_strategy(s)
        assert any("unknown step" in e for e in errors)

    def test_self_dependency(self):
        steps = [
            StrategyStep(description="a", id="s1", dependencies=["s1"]),
        ]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        errors = validate_strategy(s)
        assert any("depends on itself" in e for e in errors)

    def test_circular_dependency(self):
        steps = [
            StrategyStep(description="a", id="s1", dependencies=["s2"]),
            StrategyStep(description="b", id="s2", dependencies=["s1"]),
        ]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        errors = validate_strategy(s)
        assert any("circular" in e for e in errors)

    def test_missing_goal_id(self):
        steps = [StrategyStep(description="a")]
        s = Strategy(goal_id="", objective="test", steps=steps)
        errors = validate_strategy(s)
        assert any("goal_id" in e for e in errors)

    def test_missing_objective(self):
        steps = [StrategyStep(description="a")]
        s = Strategy(goal_id="g1", objective="", steps=steps)
        errors = validate_strategy(s)
        assert any("objective" in e for e in errors)

    def test_confidence_out_of_range(self):
        steps = [StrategyStep(description="a")]
        s = Strategy(goal_id="g1", objective="test", confidence=1.5, steps=steps)
        errors = validate_strategy(s)
        assert any("confidence" in e for e in errors)

    def test_serializable(self):
        steps = [StrategyStep(description="a")]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        errors = validate_strategy(s)
        assert errors == []
        d = s.to_dict()
        assert isinstance(d, dict)


class TestStrategyPurity:
    """Verify the strategy layer has no side effects beyond events."""

    def test_decomposer_no_file_writes(self):
        """Decomposer should not write to filesystem."""
        for fpath in STRATEGY_FILES:
            with open(fpath) as f:
                content = f.read()
            # Check for file write operations
            assert (
                "open(" not in content or "open(fpath" in content or fpath.endswith("validator.py")
            ), f"{fpath} uses open() — potential file write"

    def test_models_are_dataclasses(self):
        """Strategy and StrategyStep must be dataclasses."""
        import dataclasses

        assert dataclasses.is_dataclass(Strategy)
        assert dataclasses.is_dataclass(StrategyStep)
