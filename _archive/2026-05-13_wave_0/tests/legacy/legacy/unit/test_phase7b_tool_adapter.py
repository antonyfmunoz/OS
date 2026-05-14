"""Phase 7B — Tool Integration Layer tests.

Tests for:
- umh.tools.registry (ToolDefinition, registry CRUD, validation, domain checks)
- umh.adapters.tools_adapter (ToolsAdapter execute flow, HTTP mocking)
"""

from __future__ import annotations

import http.client
import io
import sys
import urllib.error
import urllib.request
from socket import timeout as SocketTimeout
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")

from umh.execution.contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionTarget,
)
from umh.execution.environment import (
    EnvironmentSpec,
    EnvironmentType,
    ExecutionMode,
    SecurityLevel,
)
from umh.tools.registry import (
    BUILT_IN_TOOLS,
    DEFAULT_ALLOWED_DOMAINS,
    ToolDefinition,
    get_tool,
    is_domain_allowed,
    list_tools,
    register_tool,
    validate_tool_inputs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOCAL_ENV = EnvironmentSpec(
    id="local",
    env_type=EnvironmentType.LOCAL,
    supported_capabilities=frozenset({"tool_action", "llm_call"}),
    security_level=SecurityLevel.TRUSTED,
    execution_mode=ExecutionMode.REAL,
)


def _make_request(
    operation: str = "http_request",
    inputs: dict | None = None,
    execution_class: ExecutionClass = ExecutionClass.SIDE_EFFECT,
) -> ExecutionRequest:
    """Build a minimal ExecutionRequest for testing."""
    return ExecutionRequest(
        execution_id="exec_test_001",
        correlation_id="corr_test_001",
        causal_event_id="evt_test_001",
        session_id="sess_test",
        operation=operation,
        inputs=inputs or {},
        execution_class=execution_class,
        constraints=ExecutionConstraints(timeout_s=10),
        target=ExecutionTarget(node_id="local", transport="direct"),
        context=ExecutionContext(),
        issued_at="2026-04-27T00:00:00Z",
        issued_by="test_harness",
        idempotency_key="idem_test_001",
    )


def _mock_http_response(
    body: str = '{"ok": true}',
    status: int = 200,
    headers: dict | None = None,
) -> MagicMock:
    """Create a mock urllib response object."""
    resp = MagicMock()
    resp.status = status
    resp.headers = http.client.HTTPMessage()
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    resp.read.return_value = body.encode("utf-8")
    # Make it work as a context manager (urlopen)
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ===========================================================================
# 1. Registry: get_tool returns correct definition
# ===========================================================================


class TestToolRegistry:
    def test_get_tool_returns_correct_definition(self) -> None:
        tool = get_tool("http_get")
        assert tool is not None
        assert tool.name == "http_get"
        assert tool.operation == "http_request"
        assert "url" in tool.required_inputs
        assert tool.mutating is False

    # -----------------------------------------------------------------------
    # 2. list_tools returns all built-in tools
    # -----------------------------------------------------------------------

    def test_list_tools_returns_all_built_in(self) -> None:
        tools = list_tools()
        names = {t.name for t in tools}
        assert "http_get" in names
        assert "http_post" in names
        assert "webhook" in names
        assert len(tools) >= 3

    # -----------------------------------------------------------------------
    # 3. register_tool adds a custom tool
    # -----------------------------------------------------------------------

    def test_register_tool_adds_custom(self) -> None:
        custom = ToolDefinition(
            name="custom_ping",
            operation="http_request",
            description="Ping a URL",
            required_inputs=["url"],
            timeout_s=5,
        )
        register_tool(custom)
        retrieved = get_tool("custom_ping")
        assert retrieved is not None
        assert retrieved.name == "custom_ping"
        assert retrieved.timeout_s == 5

    # -----------------------------------------------------------------------
    # 4. validate_tool_inputs with valid inputs
    # -----------------------------------------------------------------------

    def test_validate_valid_inputs(self) -> None:
        valid, err = validate_tool_inputs("http_get", {"url": "https://httpbin.org/get"})
        assert valid is True
        assert err == ""

    # -----------------------------------------------------------------------
    # 5. validate_tool_inputs missing required input
    # -----------------------------------------------------------------------

    def test_validate_missing_required(self) -> None:
        valid, err = validate_tool_inputs("http_get", {})
        assert valid is False
        assert "url" in err

    # -----------------------------------------------------------------------
    # 6. is_domain_allowed with allowed domain
    # -----------------------------------------------------------------------

    def test_domain_allowed(self) -> None:
        tool = get_tool("http_get")
        assert tool is not None
        assert is_domain_allowed("https://api.github.com/repos", tool) is True

    # -----------------------------------------------------------------------
    # 7. is_domain_allowed with blocked domain
    # -----------------------------------------------------------------------

    def test_domain_blocked(self) -> None:
        tool = get_tool("http_get")
        assert tool is not None
        assert is_domain_allowed("https://evil.example.com/data", tool) is False

    # -----------------------------------------------------------------------
    # 8. is_domain_allowed with empty allowed_domains uses default
    # -----------------------------------------------------------------------

    def test_domain_empty_uses_default(self) -> None:
        # Built-in http_get has empty allowed_domains -> falls back to DEFAULT_ALLOWED_DOMAINS
        tool = get_tool("http_get")
        assert tool is not None
        assert tool.allowed_domains == frozenset()

        for domain in DEFAULT_ALLOWED_DOMAINS:
            assert is_domain_allowed(f"https://{domain}/test", tool) is True

    # -----------------------------------------------------------------------
    # 8b. is_domain_allowed with explicit allowed_domains uses those
    # -----------------------------------------------------------------------

    def test_domain_explicit_uses_tool_domains(self) -> None:
        custom = ToolDefinition(
            name="restricted_tool",
            operation="http_request",
            description="Restricted",
            required_inputs=["url"],
            allowed_domains=frozenset({"internal.example.com"}),
        )
        assert is_domain_allowed("https://internal.example.com/api", custom) is True
        assert is_domain_allowed("https://api.github.com/repos", custom) is False

    # -----------------------------------------------------------------------
    # Validate unknown tool
    # -----------------------------------------------------------------------

    def test_validate_unknown_tool(self) -> None:
        valid, err = validate_tool_inputs("nonexistent_tool", {"url": "x"})
        assert valid is False
        assert "Unknown tool" in err


# ===========================================================================
# ToolsAdapter tests
# ===========================================================================


class TestToolsAdapter:
    """Tests for umh.adapters.tools_adapter.ToolsAdapter."""

    def _get_adapter(self):
        from umh.adapters.tools_adapter import ToolsAdapter

        return ToolsAdapter()

    # -----------------------------------------------------------------------
    # 9. adapter_name and capability_type correct
    # -----------------------------------------------------------------------

    def test_adapter_identity(self) -> None:
        adapter = self._get_adapter()
        assert adapter.adapter_name == "tools_adapter"
        assert adapter.capability_type == "tool_action"

    # -----------------------------------------------------------------------
    # 10. execute http_get (mocked)
    # -----------------------------------------------------------------------

    @patch("umh.adapters.tools_adapter.urllib.request.urlopen")
    def test_execute_http_get(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_http_response(
            body='{"status": "ok"}',
            status=200,
            headers={"Content-Type": "application/json"},
        )

        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={
                "tool_name": "http_get",
                "url": "https://httpbin.org/get",
            },
        )
        result = adapter.execute(req, _LOCAL_ENV)

        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs["status_code"] == 200
        assert "ok" in result.outputs["response_body"]
        assert result.outputs["url"] == "https://httpbin.org/get"
        assert result.outputs["method"] == "GET"
        mock_urlopen.assert_called_once()

    # -----------------------------------------------------------------------
    # 11. execute with invalid tool returns REJECTED
    # -----------------------------------------------------------------------

    def test_execute_invalid_tool_rejected(self) -> None:
        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={"tool_name": "nonexistent_tool", "url": "https://httpbin.org"},
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.REJECTED
        assert "Unknown tool" in (result.error or "")

    # -----------------------------------------------------------------------
    # 12. execute with missing inputs returns REJECTED
    # -----------------------------------------------------------------------

    def test_execute_missing_inputs_rejected(self) -> None:
        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={"tool_name": "http_get"},  # missing "url"
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.REJECTED
        assert "Missing required" in (result.error or "")

    # -----------------------------------------------------------------------
    # 13. execute with blocked domain returns REJECTED
    # -----------------------------------------------------------------------

    def test_execute_blocked_domain_rejected(self) -> None:
        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={
                "tool_name": "http_get",
                "url": "https://evil.example.com/steal-data",
            },
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.REJECTED
        assert "Domain not allowed" in (result.error or "")

    # -----------------------------------------------------------------------
    # 14. execute timeout handling
    # -----------------------------------------------------------------------

    @patch("umh.adapters.tools_adapter.urllib.request.urlopen")
    def test_execute_timeout_handling(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = SocketTimeout("timed out")

        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={
                "tool_name": "http_get",
                "url": "https://httpbin.org/delay/60",
            },
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.TIMED_OUT
        assert "timed out" in (result.error or "").lower()

    # -----------------------------------------------------------------------
    # 14b. URLError wrapping timeout also returns TIMED_OUT
    # -----------------------------------------------------------------------

    @patch("umh.adapters.tools_adapter.urllib.request.urlopen")
    def test_execute_urlerror_timeout(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = urllib.error.URLError(reason=SocketTimeout("timed out"))

        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={
                "tool_name": "http_get",
                "url": "https://httpbin.org/delay/60",
            },
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.TIMED_OUT

    # -----------------------------------------------------------------------
    # 15. execute returns proper outputs structure
    # -----------------------------------------------------------------------

    @patch("umh.adapters.tools_adapter.urllib.request.urlopen")
    def test_execute_output_structure(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_http_response(
            body="hello world",
            status=200,
            headers={"X-Custom": "value"},
        )

        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={
                "tool_name": "http_get",
                "url": "https://httpbin.org/get",
            },
        )
        result = adapter.execute(req, _LOCAL_ENV)

        assert result.status == ExecutionStatus.SUCCEEDED
        outputs = result.outputs
        assert "status_code" in outputs
        assert "response_body" in outputs
        assert "response_headers" in outputs
        assert "url" in outputs
        assert "method" in outputs
        assert isinstance(outputs["status_code"], int)
        assert isinstance(outputs["response_body"], str)
        assert isinstance(outputs["response_headers"], dict)

    # -----------------------------------------------------------------------
    # 16. http_post marked as mutating
    # -----------------------------------------------------------------------

    def test_http_post_is_mutating(self) -> None:
        tool = get_tool("http_post")
        assert tool is not None
        assert tool.mutating is True

    # -----------------------------------------------------------------------
    # 17. webhook tool exists and is mutating
    # -----------------------------------------------------------------------

    def test_webhook_exists_and_mutating(self) -> None:
        tool = get_tool("webhook")
        assert tool is not None
        assert tool.mutating is True
        assert "url" in tool.required_inputs
        assert "body" in tool.required_inputs

    # -----------------------------------------------------------------------
    # 18. response body truncation at 1MB limit
    # -----------------------------------------------------------------------

    @patch("umh.adapters.tools_adapter.urllib.request.urlopen")
    def test_response_body_truncation(self, mock_urlopen: MagicMock) -> None:
        # The adapter calls response.read(_MAX_RESPONSE_BYTES) which limits to 1MB.
        # We verify that .read() is called with the 1MB limit.
        large_body = "x" * 2_000_000
        resp = _mock_http_response(body="", status=200)
        # Override read to return the truncated amount
        resp.read.return_value = large_body[:1_048_576].encode("utf-8")
        mock_urlopen.return_value = resp

        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={
                "tool_name": "http_get",
                "url": "https://httpbin.org/bytes/2000000",
            },
        )
        result = adapter.execute(req, _LOCAL_ENV)

        assert result.status == ExecutionStatus.SUCCEEDED
        # read was called with the 1MB limit
        resp.read.assert_called_once_with(1_048_576)
        assert len(result.outputs["response_body"]) == 1_048_576

    # -----------------------------------------------------------------------
    # Extra: tool name inference from operation
    # -----------------------------------------------------------------------

    @patch("umh.adapters.tools_adapter.urllib.request.urlopen")
    def test_infer_tool_name_from_operation(self, mock_urlopen: MagicMock) -> None:
        """When operation matches a tool name directly, it should be used."""
        mock_urlopen.return_value = _mock_http_response()

        adapter = self._get_adapter()
        req = _make_request(
            operation="http_get",  # operation == tool name
            inputs={"url": "https://httpbin.org/get"},
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.SUCCEEDED

    # -----------------------------------------------------------------------
    # Extra: no tool name resolvable returns REJECTED
    # -----------------------------------------------------------------------

    def test_no_tool_name_resolvable(self) -> None:
        adapter = self._get_adapter()
        req = _make_request(
            operation="unknown_operation",
            inputs={"url": "https://httpbin.org"},
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.REJECTED
        assert "Cannot determine tool_name" in (result.error or "")

    # -----------------------------------------------------------------------
    # Extra: POST with body sends data correctly
    # -----------------------------------------------------------------------

    @patch("umh.adapters.tools_adapter.urllib.request.urlopen")
    def test_post_with_body(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_http_response(body='{"created": true}', status=201)

        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={
                "tool_name": "http_post",
                "url": "https://httpbin.org/post",
                "body": {"key": "value"},
            },
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs["method"] == "POST"

        # Verify the Request object was constructed with data
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        assert request_obj.data is not None

    # -----------------------------------------------------------------------
    # Extra: HTTPError returns FAILED with status code
    # -----------------------------------------------------------------------

    @patch("umh.adapters.tools_adapter.urllib.request.urlopen")
    def test_http_error_returns_failed(self, mock_urlopen: MagicMock) -> None:
        err = urllib.error.HTTPError(
            url="https://httpbin.org/status/404",
            code=404,
            msg="Not Found",
            hdrs=http.client.HTTPMessage(),
            fp=io.BytesIO(b"not found"),
        )
        mock_urlopen.side_effect = err

        adapter = self._get_adapter()
        req = _make_request(
            operation="http_request",
            inputs={
                "tool_name": "http_get",
                "url": "https://httpbin.org/status/404",
            },
        )
        result = adapter.execute(req, _LOCAL_ENV)
        assert result.status == ExecutionStatus.FAILED
        assert result.outputs.get("status_code") == 404
        assert "404" in (result.error or "")
