"""Phase 7B — Boundary audit tests.

Verifies architectural invariants through code inspection and import checks:
- No direct HTTP calls in planner, orchestrator, or memory
- Tools adapter uses only stdlib
- Tool registry does not import execution
- Guard correctly gates mutating vs non-mutating tools
- Templates produce plans, not execution
- Template steps use correct execution_class
"""

from __future__ import annotations

import subprocess
import sys

sys.path.insert(0, "/opt/OS")

import pytest


# ── 1. No direct HTTP calls in planner ────────────────────────────────


def test_no_http_imports_in_planning():
    """umh/planning/ must not import urllib, requests, or http.client."""
    result = subprocess.run(
        [
            "grep",
            "-rn",
            r"urllib\.request\|import requests\|http\.client",
            "umh/planning/",
        ],
        capture_output=True,
        text=True,
        cwd="/opt/OS",
    )
    assert result.stdout.strip() == "", f"Found HTTP calls in planning:\n{result.stdout}"


# ── 2. No direct HTTP calls in orchestrator ───────────────────────────


def test_no_http_imports_in_orchestrator():
    """umh/orchestrator/ must not import urllib, requests, or http.client."""
    result = subprocess.run(
        [
            "grep",
            "-rn",
            r"urllib\.request\|import requests\|http\.client",
            "umh/orchestrator/",
        ],
        capture_output=True,
        text=True,
        cwd="/opt/OS",
    )
    assert result.stdout.strip() == "", f"Found HTTP calls in orchestrator:\n{result.stdout}"


# ── 3. No direct HTTP calls in memory ─────────────────────────────────


def test_no_http_imports_in_memory():
    """umh/memory/ must not import urllib, requests, or http.client."""
    result = subprocess.run(
        [
            "grep",
            "-rn",
            r"urllib\.request\|import requests\|http\.client",
            "umh/memory/",
        ],
        capture_output=True,
        text=True,
        cwd="/opt/OS",
    )
    assert result.stdout.strip() == "", f"Found HTTP calls in memory:\n{result.stdout}"


# ── 4. Tools adapter uses only stdlib ─────────────────────────────────


def test_tools_adapter_no_requests_import():
    """umh/adapters/tools_adapter.py must not import 'requests'."""
    result = subprocess.run(
        [
            "grep",
            "-n",
            r"import requests",
            "umh/adapters/tools_adapter.py",
        ],
        capture_output=True,
        text=True,
        cwd="/opt/OS",
    )
    assert result.stdout.strip() == "", f"tools_adapter.py imports requests:\n{result.stdout}"


# ── 5. Tool registry does not import execution ────────────────────────


def test_tool_registry_no_execution_import():
    """umh/tools/registry.py must not import from umh.execution."""
    result = subprocess.run(
        [
            "grep",
            "-n",
            r"from umh\.execution\|import umh\.execution",
            "umh/tools/registry.py",
        ],
        capture_output=True,
        text=True,
        cwd="/opt/OS",
    )
    assert result.stdout.strip() == "", f"Tool registry imports execution layer:\n{result.stdout}"


# ── 6. Guard returns REQUIRES_APPROVAL for mutating tools ─────────────


def test_guard_requires_approval_for_mutating_tool():
    """check_tool_operation returns REQUIRES_APPROVAL for webhook (mutating)."""
    from umh.security.execution_guard import GuardVerdict, check_tool_operation

    result = check_tool_operation(
        "http_request",
        {
            "tool_name": "webhook",
            "url": "https://hooks.slack.com/services/test",
            "body": '{"text": "test"}',
        },
    )
    assert result.verdict == GuardVerdict.REQUIRES_APPROVAL, (
        f"Expected REQUIRES_APPROVAL for mutating tool, got {result.verdict}: {result.reason}"
    )


def test_guard_requires_approval_for_http_post():
    """check_tool_operation returns REQUIRES_APPROVAL for http_post (mutating)."""
    from umh.security.execution_guard import GuardVerdict, check_tool_operation

    result = check_tool_operation(
        "http_request",
        {"tool_name": "http_post", "url": "https://httpbin.org/post"},
    )
    assert result.verdict == GuardVerdict.REQUIRES_APPROVAL, (
        f"Expected REQUIRES_APPROVAL for http_post, got {result.verdict}: {result.reason}"
    )


# ── 7. Guard returns ALLOW for non-mutating tools ─────────────────────


def test_guard_allows_non_mutating_tool():
    """check_tool_operation returns ALLOW for http_get (non-mutating)."""
    from umh.security.execution_guard import GuardVerdict, check_tool_operation

    result = check_tool_operation(
        "http_request",
        {"tool_name": "http_get", "url": "https://httpbin.org/get"},
    )
    assert result.verdict == GuardVerdict.ALLOW, (
        f"Expected ALLOW for non-mutating tool, got {result.verdict}: {result.reason}"
    )


# ── 8. Templates produce plans, not execution ─────────────────────────


def test_templates_return_execution_plan():
    """All tool templates return ExecutionPlan, not ExecutionResult."""
    from umh.execution.contract import ExecutionResult
    from umh.planning.models import ExecutionPlan, PlanObjective
    from umh.planning.templates import get_template

    for name in ("fetch_data", "send_webhook"):
        fn = get_template(name)
        assert fn is not None, f"Template '{name}' not registered"
        plan = fn(
            PlanObjective(
                title=name,
                context={"url": "https://example.com", "body": "{}"},
            )
        )
        assert isinstance(plan, ExecutionPlan), (
            f"Template '{name}' returned {type(plan).__name__}, expected ExecutionPlan"
        )
        assert not isinstance(plan, ExecutionResult), (
            f"Template '{name}' returned ExecutionResult — templates must not execute"
        )


# ── 9. Template steps use correct execution_class ─────────────────────


def test_tool_template_steps_are_side_effect():
    """All steps in tool templates use execution_class='side_effect'."""
    from umh.planning.models import PlanObjective
    from umh.planning.templates import get_template

    for name in ("fetch_data", "send_webhook"):
        fn = get_template(name)
        plan = fn(
            PlanObjective(
                title=name,
                context={"url": "https://example.com", "body": "{}"},
            )
        )
        for step in plan.steps:
            assert step.execution_class == "side_effect", (
                f"Template '{name}' step '{step.name}' has execution_class "
                f"'{step.execution_class}', expected 'side_effect'"
            )


# ── 10. No http_request operations in planning module ─────────────────


def test_no_http_request_execution_in_planning_module():
    """umh/planning/ must not directly execute HTTP requests (no urllib/requests/http.client)."""
    # This is a superset check: the planning module must never contain
    # actual HTTP execution code — only template definitions that
    # reference http_request as an operation string.
    result = subprocess.run(
        [
            "grep",
            "-rn",
            r"urllib\.request\.urlopen\|requests\.get\|requests\.post\|http\.client\.HTTP",
            "umh/planning/",
        ],
        capture_output=True,
        text=True,
        cwd="/opt/OS",
    )
    assert result.stdout.strip() == "", f"Found HTTP execution in planning module:\n{result.stdout}"
