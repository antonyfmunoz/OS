"""Tests for Phase 7B: Tool Integration Layer.

Verifies:
- check_tool_operation: allow/deny/requires_approval for tool ops
- check_execution routes http_request and tool_* to check_tool_operation
- SpineExecutionBackend.can_handle returns True for tool operations
- SpineExecutionBackend._classify_external maps tool ops to tool_action
- Full path guard checks for http_get and http_post
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.security.execution_guard import (
    GuardVerdict,
    check_execution,
    check_tool_operation,
)
from umh.adapters.umh_execution import SpineExecutionBackend

# Use domains from registry's DEFAULT_ALLOWED_DOMAINS for valid-domain tests
_ALLOWED_URL = "https://api.github.com/repos/test"
_ALLOWED_SLACK_URL = "https://hooks.slack.com/services/test"


# ── A. check_tool_operation ──────────────────────────────────────────


class TestCheckToolOperation:
    def test_http_get_allowed(self):
        """Non-mutating tool with allowed domain → ALLOW."""
        result = check_tool_operation(
            "http_get",
            {"url": _ALLOWED_URL},
        )
        assert result.verdict == GuardVerdict.ALLOW

    def test_http_post_requires_approval(self):
        """Mutating tool without approval → REQUIRES_APPROVAL."""
        result = check_tool_operation(
            "http_post",
            {"url": _ALLOWED_URL},
        )
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL
        assert "mutating" in result.reason.lower() or "approval" in result.reason.lower()

    def test_http_post_allowed_when_approved(self):
        """Mutating tool with approval → ALLOW."""
        result = check_tool_operation(
            "http_post",
            {"url": _ALLOWED_URL},
            approved_execution=True,
        )
        assert result.verdict == GuardVerdict.ALLOW

    def test_blocked_domain_denied(self):
        """URL pointing to domain not in allowlist → DENY."""
        result = check_tool_operation(
            "http_get",
            {"url": "http://evil.example.com/steal-data"},
        )
        assert result.verdict == GuardVerdict.DENY
        assert "domain" in result.reason.lower()

    def test_unknown_tool_denied(self):
        """Tool not in registry → DENY."""
        result = check_tool_operation(
            "nonexistent_tool",
            {"url": _ALLOWED_URL},
        )
        assert result.verdict == GuardVerdict.DENY
        assert "unknown tool" in result.reason.lower()

    def test_missing_required_inputs_denied(self):
        """Missing required inputs → DENY."""
        result = check_tool_operation(
            "http_get",
            {},  # missing 'url'
        )
        assert result.verdict == GuardVerdict.DENY
        assert "missing" in result.reason.lower()

    def test_webhook_requires_approval(self):
        """Webhook is mutating → REQUIRES_APPROVAL."""
        result = check_tool_operation(
            "webhook",
            {"url": _ALLOWED_SLACK_URL, "body": '{"text": "hello"}'},
        )
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL

    def test_disallowed_domain_denied(self):
        """Domain not in allowlist → DENY."""
        result = check_tool_operation(
            "http_get",
            {"url": "http://localhost:8080/api"},
        )
        assert result.verdict == GuardVerdict.DENY

    def test_tool_name_from_inputs(self):
        """tool_name in inputs overrides operation for registry lookup."""
        result = check_tool_operation(
            "tool_custom",
            {"tool_name": "http_get", "url": _ALLOWED_URL},
        )
        assert result.verdict == GuardVerdict.ALLOW


# ── B. check_execution routing ──────────────────────────────────────


class TestCheckExecutionRouting:
    def test_http_request_routes_to_tool(self):
        """http_request operation routes to check_tool_operation.

        http_request is not a registered tool name, so the guard denies it
        as unknown. The important thing is that it routes through the tool
        check path (not the generic unknown-operation fallthrough).
        """
        result = check_execution(
            "http_request",
            {"url": _ALLOWED_URL, "method": "GET"},
        )
        # http_request not in registry → DENY with "Unknown tool" reason
        assert result.verdict == GuardVerdict.DENY
        assert "unknown tool" in result.reason.lower()

    def test_tool_prefix_routes_to_tool(self):
        """tool_* operations route to check_tool_operation."""
        # tool_nonexistent is not in registry → DENY
        result = check_execution(
            "tool_nonexistent",
            {},
        )
        assert result.verdict == GuardVerdict.DENY
        assert "unknown tool" in result.reason.lower()

    def test_tool_prefix_with_known_tool(self):
        """tool_* with tool_name pointing to known tool."""
        result = check_execution(
            "tool_custom",
            {"tool_name": "http_get", "url": _ALLOWED_URL},
        )
        assert result.verdict == GuardVerdict.ALLOW


# ── C. SpineExecutionBackend.can_handle ─────────────────────────────


class TestCanHandle:
    def setup_method(self):
        self.backend = SpineExecutionBackend()

    def test_http_request_handled(self):
        assert self.backend.can_handle("http_request") is True

    def test_http_get_handled(self):
        assert self.backend.can_handle("http_get") is True

    def test_http_post_handled(self):
        assert self.backend.can_handle("http_post") is True

    def test_webhook_handled(self):
        assert self.backend.can_handle("webhook") is True

    def test_tool_prefix_handled(self):
        assert self.backend.can_handle("tool_custom") is True

    def test_tool_send_email_handled(self):
        assert self.backend.can_handle("tool_send_email") is True

    def test_unknown_not_handled(self):
        assert self.backend.can_handle("totally_unknown_op") is False


# ── D. SpineExecutionBackend._classify_external ─────────────────────


class TestClassifyExternal:
    def test_http_request_maps_to_tool_action(self):
        assert SpineExecutionBackend._classify_external("http_request") == "tool_action"

    def test_http_get_maps_to_tool_action(self):
        assert SpineExecutionBackend._classify_external("http_get") == "tool_action"

    def test_http_post_maps_to_tool_action(self):
        assert SpineExecutionBackend._classify_external("http_post") == "tool_action"

    def test_webhook_maps_to_tool_action(self):
        assert SpineExecutionBackend._classify_external("webhook") == "tool_action"

    def test_tool_prefix_maps_to_tool_action(self):
        assert SpineExecutionBackend._classify_external("tool_custom") == "tool_action"

    def test_browser_still_maps_correctly(self):
        assert SpineExecutionBackend._classify_external("browser_navigate") == "browser_action"

    def test_computer_still_maps_correctly(self):
        assert SpineExecutionBackend._classify_external("computer_click") == "computer_use"


# ── E. Full path guard checks ───────────────────────────────────────


class TestFullPath:
    def test_http_get_through_guard_allow(self):
        """http_get with allowed domain through check_tool_operation → ALLOW."""
        result = check_tool_operation(
            "http_get",
            {"url": _ALLOWED_URL},
        )
        assert result.verdict == GuardVerdict.ALLOW
        assert result.sanitized_inputs is not None

    def test_http_post_through_guard_requires_approval(self):
        """http_post mutating without approval through guard → REQUIRES_APPROVAL."""
        result = check_tool_operation(
            "http_post",
            {"url": _ALLOWED_URL},
        )
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL
        assert "mutating" in result.reason.lower() or "approval" in result.reason.lower()
