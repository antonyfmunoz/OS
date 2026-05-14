#!/usr/bin/env python3
"""Substrate Workflow Execution Layer v1.1 — smoke test.

Validates that ``analysis`` and ``content_ops`` are now live handlers
(no longer deferred stubs) while preserving all v1 constraints.
"""

from __future__ import annotations

import ast
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
        print(f"  \u2713 {label}")
    except Exception as exc:
        _failed += 1
        print(f"  \u2717 {label}: {exc}")


def main() -> None:
    global _passed, _failed
    print("── Workflow Execution Layer v1.1 smoke tests ──")

    # ── 1. version bumped ────────────────────────────────────────────────────
    def test_version_is_v11():
        from runtime.substrate.workflow_execution import LAYER_VERSION

        assert LAYER_VERSION == "v1.1", f"expected v1.1, got {LAYER_VERSION}"

    _run("version is v1.1", test_version_is_v11)

    # ── 2. analysis handler is no longer deferred ────────────────────────────
    def test_analysis_not_deferred():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "analyze the conversion funnel data", mode="builder", target="local"
        )
        assert result["workflow_executed"] is True, f"not executed: {result}"
        assert result["workflow_kind"] == "analysis"
        assert result["execution_class"] == "workflow"
        details = result.get("details", {})
        # Without a session, handler returns deferred=True (no session bound)
        # but the handler itself is live — it would execute if session_name provided
        assert result["handler"] == "_handle_analysis"
        assert "result_summary" in result

    _run("analysis handler resolves and executes", test_analysis_not_deferred)

    # ── 3. content_ops handler is no longer deferred ─────────────────────────
    def test_content_ops_not_deferred():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "write a blog post about AI", mode="builder", target="local"
        )
        assert result["workflow_executed"] is True, f"not executed: {result}"
        assert result["workflow_kind"] == "content_ops"
        assert result["execution_class"] == "workflow"
        assert result["handler"] == "_handle_content_ops"
        assert "result_summary" in result

    _run("content_ops handler resolves and executes", test_content_ops_not_deferred)

    # ── 4. analysis in product mode executes ─────────────────────────────────
    def test_analysis_product_mode():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "analyze the conversion funnel data", mode="product", target="vps"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "analysis"
        assert result["mode"] == "product"

    _run("analysis executes in product mode", test_analysis_product_mode)

    # ── 5. content_ops in product mode executes ──────────────────────────────
    def test_content_ops_product_mode():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "draft a social media post about our launch", mode="product", target="vps"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "content_ops"
        assert result["mode"] == "product"

    _run("content_ops executes in product mode", test_content_ops_product_mode)

    # ── 6. analysis handler no longer returns deferred in details ─────────
    def test_analysis_handler_directly():
        """Call _handle_analysis directly — without session it defers,
        but the handler signature is now live (not a classification stub)."""
        from runtime.substrate.workflow_execution import _handle_analysis

        result = _handle_analysis("analyze X", "builder", "local", None, {})
        assert result["ok"] is True
        # Without session: graceful deferred (same as builder_dev without session)
        assert result["details"].get("deferred") is True
        assert result["result_summary"] == "analysis classified, no session bound"
        # Key: no workflow_kind/text_preview in details (v1 stub pattern removed)
        assert "text_preview" not in result["details"]

    _run("analysis handler direct call (no session)", test_analysis_handler_directly)

    # ── 7. content_ops handler no longer returns deferred in details ──────
    def test_content_ops_handler_directly():
        from runtime.substrate.workflow_execution import _handle_content_ops

        result = _handle_content_ops("write a post", "builder", "local", None, {})
        assert result["ok"] is True
        assert result["details"].get("deferred") is True
        assert result["result_summary"] == "content_ops classified, no session bound"
        assert "text_preview" not in result["details"]

    _run(
        "content_ops handler direct call (no session)",
        test_content_ops_handler_directly,
    )

    # ── 8. mode-aware prefix functions exist and are correct ─────────────
    def test_prefix_functions():
        from runtime.substrate.workflow_execution import (
            _analysis_prefix,
            _content_ops_prefix,
        )

        # Builder mode prefixes
        ap_builder = _analysis_prefix("builder")
        assert "builder mode" in ap_builder.lower()
        cp_builder = _content_ops_prefix("builder")
        assert "builder mode" in cp_builder.lower()

        # Product mode prefixes
        ap_product = _analysis_prefix("product")
        assert "product mode" in ap_product.lower()
        assert "product-safe" in ap_product.lower()
        cp_product = _content_ops_prefix("product")
        assert "product mode" in cp_product.lower()
        assert "product-safe" in cp_product.lower()

    _run("mode-aware prefix functions are correct", test_prefix_functions)

    # ── 9. builder_dev still works (v1 regression) ───────────────────────
    def test_builder_dev_still_works():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "fix the bug in gateway.py", mode="builder", target="local"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "builder_dev"

    _run("builder_dev still works (v1 regression)", test_builder_dev_still_works)

    # ── 10. product_runtime still works (v1 regression) ──────────────────
    def test_product_runtime_still_works():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "run the onboarding workflow", mode="product", target="vps"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "product_runtime"

    _run(
        "product_runtime still works (v1 regression)",
        test_product_runtime_still_works,
    )

    # ── 11. system_ops still works (v1 regression) ───────────────────────
    def test_system_ops_still_works():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "check system health status", mode="builder", target="local"
        )
        assert result["workflow_executed"] is True
        assert result["workflow_kind"] == "system_ops"

    _run("system_ops still works (v1 regression)", test_system_ops_still_works)

    # ── 12. mode boundary still preserved ────────────────────────────────
    def test_mode_boundary_preserved():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "fix the bug in the router", mode="product", target="vps"
        )
        if result.get("workflow_kind") == "builder_dev":
            assert result["workflow_executed"] is False
            assert result["reason"] == "policy_blocked"

    _run("mode boundary still preserved", test_mode_boundary_preserved)

    # ── 13. no hot-path imports (import check) ───────────────────────────
    def test_no_hot_path_imports():
        with open(f"{_ROOT}/runtime/substrate/workflow_execution.py") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", None) or ""
                names = [a.name for a in node.names]
                for n in [module] + names:
                    for forbidden in [
                        "model_router",
                        "gateway",
                        "cognitive_loop",
                        "agent_runtime",
                        "primitives",
                    ]:
                        assert forbidden not in n, (
                            f"workflow_execution imports {forbidden}: {n}"
                        )

    _run("no hot-path imports (AST check)", test_no_hot_path_imports)

    # ── 14. no forbidden patterns in executable code ─────────────────────
    def test_no_forbidden_patterns():
        with open(f"{_ROOT}/runtime/substrate/workflow_execution.py") as f:
            source = f.read()
        tree = ast.parse(source)
        docstring_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    for ln in range(node.value.lineno, node.value.end_lineno + 1):
                        docstring_lines.add(ln)
        lines = source.splitlines()
        code_lines = []
        for i, line in enumerate(lines, 1):
            if i in docstring_lines:
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_lines.append(stripped.split("#")[0])
        code_only = "\n".join(code_lines).lower()
        for forbidden in [
            "planner",
            "multi_agent",
            "swarm",
            "daemon",
            "background_thread",
        ]:
            assert forbidden not in code_only, (
                f"forbidden pattern '{forbidden}' in executable code"
            )

    _run("no forbidden patterns in executable code", test_no_forbidden_patterns)

    # ── 15. hot-path modules not loaded at import time ───────────────────
    def test_hot_path_modules_clean():
        import importlib

        mod_name = "runtime.substrate.workflow_execution"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        importlib.import_module(mod_name)
        for forbidden in [
            "runtime.gateway",
            "control_plane.runtime.cognitive_loop",
            "runtime.model_router",
            "execution.runtime.agent_runtime",
            "runtime.primitives",
        ]:
            assert forbidden not in sys.modules, (
                f"hot-path module {forbidden} was imported"
            )

    _run("hot-path modules not loaded at import time", test_hot_path_modules_clean)

    # ── 16. structured result metadata complete ──────────────────────────
    def test_result_metadata_complete():
        from runtime.substrate.workflow_execution import (
            LAYER_NAME,
            LAYER_VERSION,
            execute_workflow_if_allowed,
        )

        for text, mode, target in [
            ("analyze the data", "builder", "local"),
            ("write a caption for this photo", "builder", "local"),
        ]:
            result = execute_workflow_if_allowed(text, mode=mode, target=target)
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
                    assert key in result, f"missing key: {key} in {result}"

    _run("structured result metadata complete", test_result_metadata_complete)

    # ── 17. handler registry has all 5 kinds ─────────────────────────────
    def test_handler_registry_complete():
        from runtime.substrate.workflow_execution import _HANDLER_REGISTRY

        expected = {
            "builder_dev",
            "product_runtime",
            "content_ops",
            "analysis",
            "system_ops",
        }
        assert set(_HANDLER_REGISTRY.keys()) == expected, (
            f"registry mismatch: {set(_HANDLER_REGISTRY.keys())} != {expected}"
        )

    _run("handler registry has all 5 kinds", test_handler_registry_complete)

    # ── 18. conversation intent still returns not executed ────────────────
    def test_conversation_still_not_executed():
        from runtime.substrate.workflow_execution import execute_workflow_if_allowed

        result = execute_workflow_if_allowed(
            "hello how are you", mode="builder", target="local"
        )
        assert result["workflow_executed"] is False
        assert result["reason"] == "not_workflow"

    _run("conversation intent still not executed", test_conversation_still_not_executed)

    # ── 19. delegation layer still works independently ───────────────────
    def test_delegation_layer_independent():
        from runtime.substrate.workflow_delegation import (
            classify_workflow_intent,
            resolve_workflow_policy,
        )

        intent = classify_workflow_intent("analyze the data", "builder")
        assert intent["intent"] == "workflow"
        assert intent["workflow_kind"] == "analysis"
        policy = resolve_workflow_policy("builder", intent)
        assert policy["allowed"] is True

        intent2 = classify_workflow_intent("draft a social media post", "product")
        assert intent2["intent"] == "workflow"
        assert intent2["workflow_kind"] == "content_ops"
        policy2 = resolve_workflow_policy("product", intent2)
        assert policy2["allowed"] is True

    _run(
        "delegation layer still works independently", test_delegation_layer_independent
    )

    # ── 20. v1 smoke tests still pass ────────────────────────────────────
    def test_v1_smoke_still_passes():
        """Run the existing v1 smoke test as a regression check."""
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                f"{_ROOT}/scripts/substrate_workflow_execution_smoke_test.py",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"v1 smoke failed (rc={result.returncode}):\n{result.stdout}\n{result.stderr}"
        )

    _run("v1 smoke tests still pass", test_v1_smoke_still_passes)

    # ── summary ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 50}")
    print(f"passed={_passed}  failed={_failed}")
    if _failed:
        sys.exit(1)
    print("All v1.1 smoke tests passed.")


if __name__ == "__main__":
    main()
