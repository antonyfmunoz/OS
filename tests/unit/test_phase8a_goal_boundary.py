"""Tests for Phase 8A: Persistent Goal System — boundary verification.

Uses AST inspection to verify architectural boundaries:
- Goals module does not import execution engine directly
- Goals module does not import adapters or tools
- GoalEngine routes through planning pipeline (not execute directly)
- No recursive goal creation
"""

from __future__ import annotations

import ast
import os
import sys

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase8a")

import pytest

_GOAL_DIR = "/opt/OS/umh/goals"


def _get_imports(filepath: str) -> list[str]:
    """Extract all import module names from a Python file via AST."""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
    return imports


def _get_file_source(filepath: str) -> str:
    """Read file source as string."""
    with open(filepath) as f:
        return f.read()


def _goal_files() -> list[str]:
    """Return all .py files in the goals directory."""
    return [
        os.path.join(_GOAL_DIR, f)
        for f in os.listdir(_GOAL_DIR)
        if f.endswith(".py") and f != "__init__.py"
    ]


# ── A. No Direct Execution Imports ───────────────────────────────────


class TestNoExecutionImports:
    def test_no_execute_import_in_models(self):
        """models.py must not import from umh.execution.engine."""
        path = os.path.join(_GOAL_DIR, "models.py")
        imports = _get_imports(path)
        for imp in imports:
            assert not imp.startswith("umh.execution.engine"), (
                f"models.py imports {imp} — goals must not depend on execution engine"
            )

    def test_no_execute_import_in_store(self):
        """store.py must not import from umh.execution.engine."""
        path = os.path.join(_GOAL_DIR, "store.py")
        imports = _get_imports(path)
        for imp in imports:
            assert not imp.startswith("umh.execution.engine"), (
                f"store.py imports {imp} — goals must not depend on execution engine"
            )

    def test_no_execute_import_in_engine(self):
        """goal_engine.py must not import from umh.execution.engine."""
        path = os.path.join(_GOAL_DIR, "goal_engine.py")
        imports = _get_imports(path)
        for imp in imports:
            assert not imp.startswith("umh.execution.engine"), (
                f"goal_engine.py imports {imp} — goals must route through planning"
            )

    def test_no_execute_import_in_policy(self):
        """policy.py must not import from umh.execution.engine."""
        path = os.path.join(_GOAL_DIR, "policy.py")
        imports = _get_imports(path)
        for imp in imports:
            assert not imp.startswith("umh.execution.engine"), (
                f"policy.py imports {imp} — policy must not depend on execution engine"
            )


# ── B. No Adapter or Tool Imports ────────────────────────────────────


class TestNoAdapterOrToolImports:
    def test_no_adapter_import_in_goals(self):
        """No goals/ file should import from umh.adapters."""
        for filepath in _goal_files():
            imports = _get_imports(filepath)
            fname = os.path.basename(filepath)
            # Allow interfaces.py to reference adapters (it's the bridge)
            if fname == "interfaces.py":
                continue
            for imp in imports:
                assert not imp.startswith("umh.adapters"), (
                    f"{fname} imports {imp} — goals must not depend on adapters"
                )

    def test_no_tool_import_in_goals(self):
        """No goals/ file should import from umh.tools."""
        for filepath in _goal_files():
            imports = _get_imports(filepath)
            fname = os.path.basename(filepath)
            for imp in imports:
                assert not imp.startswith("umh.tools"), (
                    f"{fname} imports {imp} — goals must not depend on tools"
                )


# ── C. Engine Routes Through Planning ─────────────────────────────────


class TestEnginePlanningRoute:
    def test_engine_uses_planning_pipeline(self):
        """goal_engine.py must contain 'create_plan_from_raw' — routes through planning."""
        path = os.path.join(_GOAL_DIR, "goal_engine.py")
        source = _get_file_source(path)
        assert "create_plan_from_raw" in source, (
            "goal_engine.py must use create_plan_from_raw from the planning pipeline"
        )

    def test_engine_does_not_call_execute_directly(self):
        """goal_engine.py must not call execute() directly (only execute_plan)."""
        path = os.path.join(_GOAL_DIR, "goal_engine.py")
        tree = ast.parse(_get_file_source(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for bare execute() calls
                if isinstance(node.func, ast.Name) and node.func.id == "execute":
                    pytest.fail(
                        "goal_engine.py calls execute() directly — must use execute_plan"
                    )

    def test_goal_default_active(self):
        """Goal() creates with ACTIVE status by default."""
        from umh.goals.models import Goal, GoalStatus

        goal = Goal(name="test", objective="test")
        assert goal.status == GoalStatus.ACTIVE

    def test_no_recursive_goal_creation(self):
        """goal_engine.py must not contain 'Goal(' — goals don't create goals."""
        path = os.path.join(_GOAL_DIR, "goal_engine.py")
        source = _get_file_source(path)
        # Check for Goal instantiation (not import or type hint)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "Goal":
                    pytest.fail(
                        "goal_engine.py instantiates Goal() — goals must not create goals"
                    )


# ── D. CLI Boundary Check ────────────────────────────────────────────


class TestCLIBoundary:
    def test_cli_no_execute_import(self):
        """CLI goal commands must not import from umh.execution.engine directly."""
        path = "/opt/OS/umh/control/cli.py"
        source = _get_file_source(path)

        # Parse and check only the goal command functions
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("cmd_goal"):
                func_source = ast.get_source_segment(source, node)
                if func_source and "from umh.execution.engine import" in func_source:
                    pytest.fail(
                        f"{node.name} imports from umh.execution.engine — "
                        "goal CLI commands must route through goal_engine/planning"
                    )

    def test_goal_produces_plan_objectives(self):
        """Verify engine routes goals through planning by checking function calls."""
        path = os.path.join(_GOAL_DIR, "goal_engine.py")
        source = _get_file_source(path)

        # Must reference planning planner module
        assert "umh.planning.planner" in source, (
            "goal_engine.py must import from umh.planning.planner"
        )
        # Must call execute_plan
        assert "execute_plan" in source, (
            "goal_engine.py must call execute_plan from planning pipeline"
        )
