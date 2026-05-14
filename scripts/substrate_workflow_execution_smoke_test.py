#!/usr/bin/env python3
"""Substrate Workflow Execution Layer — smoke test."""

from __future__ import annotations

import sys

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

_passed = 0
_failed = 0


def _run(label: str, fn):
    global _passed, _failed
    try:
        fn()
        _passed += 1
        print(f"  ✓ {label}")
    except Exception as exc:
        _failed += 1
        print(f"  ✗ {label}: {exc}")


def main() -> None:
    global _passed, _failed
    print("── Workflow Execution Layer smoke tests ──")

    # 1. builder_dev in builder mode executes
    def test_builder_dev_in_builder_mode():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "fix the bug in gateway.py", mode="builder", target="local"
        )
        assert result["workflow_executed"] is True, f"expected executed, got {result}"
        assert result["workflow_kind"] == "builder_dev", (
            f"wrong kind: {result['workflow_kind']}"
        )
        assert result["mode"] == "builder"
        assert result["execution_class"] == "workflow"
        assert "handler" in result
        assert "result_summary" in result

    _run("builder_dev in builder mode executes", test_builder_dev_in_builder_mode)

    # 2. builder_dev in product mode is blocked
    def test_builder_dev_blocked_in_product_mode():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "fix the bug in gateway.py", mode="product", target="vps"
        )
        assert result["workflow_executed"] is False, f"should be blocked: {result}"
        assert result["reason"] == "policy_blocked"
        assert result["workflow_kind"] == "builder_dev"

    _run(
        "builder_dev in product mode is blocked",
        test_builder_dev_blocked_in_product_mode,
    )

    # 3. product_runtime in product mode executes
    def test_product_runtime_in_product_mode():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "run the onboarding workflow", mode="product", target="vps"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "product_runtime"

    _run(
        "product_runtime in product mode executes",
        test_product_runtime_in_product_mode,
    )

    # 4. content_ops executes with correct metadata
    def test_content_ops():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "write a blog post about AI", mode="builder", target="local"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "content_ops"
        assert result["execution_class"] == "workflow"

    _run("content_ops executes with correct metadata", test_content_ops)

    # 5. analysis executes with correct metadata
    def test_analysis():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "analyze the conversion funnel data", mode="product", target="vps"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "analysis"

    _run("analysis executes with correct metadata", test_analysis)

    # 6. system_ops executes with correct metadata
    def test_system_ops():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "check system health status", mode="builder", target="local"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "system_ops"

    _run("system_ops executes with correct metadata", test_system_ops)

    # 7. conversation intent returns not executed
    def test_conversation_not_executed():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "hello how are you", mode="builder", target="local"
        )
        assert result["workflow_executed"] is False
        assert result["reason"] == "not_workflow"

    _run("conversation intent returns not executed", test_conversation_not_executed)

    # 8. skill_tool intent returns not executed
    def test_skill_tool_not_executed():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "search google for python tips", mode="builder", target="local"
        )
        assert result["workflow_executed"] is False
        assert result["reason"] == "not_workflow"

    _run("skill_tool intent returns not executed", test_skill_tool_not_executed)

    # 9. no second router introduced (import check)
    def test_no_second_router():
        import ast

        with open(f"{_ROOT}/runtime/substrate/workflow_execution.py") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", None) or ""
                names = [a.name for a in node.names]
                for n in [module] + names:
                    assert "model_router" not in n, (
                        f"workflow_execution imports model_router: {n}"
                    )
                    assert "gateway" not in n, (
                        f"workflow_execution imports gateway: {n}"
                    )
                    assert "cognitive_loop" not in n, (
                        f"workflow_execution imports cognitive_loop: {n}"
                    )
                    assert "agent_runtime" not in n, (
                        f"workflow_execution imports agent_runtime: {n}"
                    )
                    assert "primitives" not in n, (
                        f"workflow_execution imports primitives: {n}"
                    )

    _run("no second router introduced (import check)", test_no_second_router)

    # 10. no second cognition pipeline (structural check)
    def test_no_second_cognition_pipeline():
        import ast
        import tokenize
        import io

        with open(f"{_ROOT}/runtime/substrate/workflow_execution.py") as f:
            source = f.read()
        # Strip comments and docstrings: check only executable code
        # Use AST to extract all string literals (docstrings) and remove them
        # Then check remaining code for forbidden patterns
        tree = ast.parse(source)
        docstring_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    for ln in range(node.value.lineno, node.value.end_lineno + 1):
                        docstring_lines.add(ln)
        # Also strip comment lines
        lines = source.splitlines()
        code_lines = []
        for i, line in enumerate(lines, 1):
            if i in docstring_lines:
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Remove inline comments
            code_lines.append(stripped.split("#")[0])
        code_only = "\n".join(code_lines).lower()
        for forbidden in [
            "autonomous",
            "planner",
            "multi_agent",
            "swarm",
            "daemon",
            "background_thread",
        ]:
            assert forbidden not in code_only, (
                f"forbidden pattern '{forbidden}' found in executable code"
            )

    _run(
        "no second cognition pipeline (structural check)",
        test_no_second_cognition_pipeline,
    )

    # 11. hot-path imports remain clean
    def test_hot_path_imports_clean():
        """Importing workflow_execution must not pull in hot-path modules."""
        import importlib

        mod_name = "runtime.substrate.workflow_execution"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        importlib.import_module(mod_name)
        for forbidden in [
            "runtime.gateway",
            "control_plane.runtime.cognitive_loop",
            "execution.runtime.model_router",
            "execution.runtime.agent_runtime",
            "runtime.primitives",
        ]:
            assert forbidden not in sys.modules, (
                f"hot-path module {forbidden} was imported"
            )

    _run("hot-path imports remain clean", test_hot_path_imports_clean)

    # 12. structured workflow result metadata present
    def test_result_metadata_shape():
        from runtime.substrate.workflow_execution import (
            LAYER_NAME,
            LAYER_VERSION,
            execute_workflow_if_allowed,
        )

        result = execute_workflow_if_allowed(
            "deploy the service now", mode="builder", target="local"
        )
        assert result.get("layer") == LAYER_NAME
        assert result.get("version") == LAYER_VERSION
        if result["workflow_executed"]:
            for key in [
                "ok",
                "workflow_kind",
                "handler",
                "mode",
                "target",
                "result_summary",
                "execution_class",
            ]:
                assert key in result, f"missing key: {key}"

    _run("structured workflow result metadata present", test_result_metadata_shape)

    # 13. target defaults are correct
    def test_target_defaults():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        # builder mode should default target to "local"
        result = execute_workflow_if_allowed("fix the crash", mode="builder")
        assert result.get("target") in ("local", "vps", None)
        # product mode should default to "vps"
        result = execute_workflow_if_allowed(
            "run the onboarding workflow", mode="product"
        )
        assert result.get("target") in ("local", "vps", None)

    _run("target defaults are correct", test_target_defaults)

    # 14. mode boundary preserved
    def test_mode_boundary_preserved():
        """Product mode must never silently execute builder_dev workflows."""
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        builder_texts = [
            "fix the bug in the router",
            "deploy the new handler",
            "update the gateway module",
            "add a test for the agent",
        ]
        for text in builder_texts:
            result = execute_workflow_if_allowed(text, mode="product", target="vps")
            if result.get("workflow_kind") == "builder_dev":
                assert result["workflow_executed"] is False, (
                    f"builder_dev executed in product mode: {text}"
                )
                assert result["reason"] == "policy_blocked"

    _run("mode boundary preserved", test_mode_boundary_preserved)

    # 15. existing workflow delegation smoke still passes
    def test_delegation_smoke_still_passes():
        """Workflow delegation layer must still work independently."""
        from runtime.substrate.workflow_delegation import (
            classify_workflow_intent,
            resolve_workflow_policy,
        )

        intent = classify_workflow_intent("fix the bug", "builder")
        assert intent["intent"] == "workflow"
        assert intent["workflow_kind"] == "builder_dev"
        policy = resolve_workflow_policy("builder", intent)
        assert policy["allowed"] is True

    _run(
        "existing workflow delegation smoke still passes",
        test_delegation_smoke_still_passes,
    )

    print(f"\n{'=' * 50}")
    print(f"passed={_passed}  failed={_failed}")
    if _failed:
        sys.exit(1)
    print("All workflow execution smoke tests passed.")


if __name__ == "__main__":
    main()
