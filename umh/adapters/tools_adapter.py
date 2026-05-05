"""UMH Tools Adapter — external capability adapter for tool execution.

Routes tool_action requests through the tool registry. Validates inputs,
checks domain allowlists, and performs HTTP requests using stdlib only
(urllib.request). No third-party HTTP libraries.

Integration:
    Registered via umh.execution.external.register_adapter() in the
    execution backend's _register_external_adapters() call chain.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from socket import timeout as SocketTimeout
from typing import Any

from umh.core.clock import iso_now, now_ms
from umh.execution.contract import ExecutionRequest, ExecutionResult, ExecutionStatus
from umh.execution.environment import EnvironmentSpec
from umh.execution.external import ExternalCapabilityAdapter
from umh.tools.registry import get_tool, is_domain_allowed, validate_tool_inputs

_log = logging.getLogger(__name__)

_MAX_RESPONSE_BYTES = 1_048_576  # 1 MB
_USER_AGENT = "UMH-ToolsAdapter/1.0"

# Method mapping: tool_name -> HTTP method
_TOOL_METHOD_MAP: dict[str, str] = {
    "http_get": "GET",
    "http_post": "POST",
    "webhook": "POST",
}


class ToolsAdapter(ExternalCapabilityAdapter):
    """External capability adapter for tool-based actions (HTTP, webhooks)."""

    @property
    def adapter_name(self) -> str:
        return "tools_adapter"

    @property
    def capability_type(self) -> str:
        return "tool_action"

    def execute(self, request: ExecutionRequest, environment: EnvironmentSpec) -> ExecutionResult:
        """Execute a tool action request.

        Flow:
        1. Resolve tool_name from inputs or operation
        2. Look up tool definition in registry
        3. Validate inputs
        4. Check domain allowlist
        5. Perform HTTP request via urllib
        6. Return structured ExecutionResult
        """
        start = now_ms()

        # 1. Resolve tool name
        tool_name = request.inputs.get("tool_name") or self._infer_tool_name(request)
        if not tool_name:
            return self._reject(
                request,
                reason="Cannot determine tool_name from inputs or operation",
                start_ms=start,
            )

        # 2. Look up tool definition
        tool = get_tool(tool_name)
        if tool is None:
            return self._reject(
                request,
                reason=f"Unknown tool: {tool_name}",
                start_ms=start,
            )

        # 3. Validate inputs
        valid, err = validate_tool_inputs(tool_name, request.inputs)
        if not valid:
            return self._reject(request, reason=err, start_ms=start)

        # 4. Domain check
        url = request.inputs.get("url", "")
        if not is_domain_allowed(url, tool):
            return self._reject(
                request,
                reason=f"Domain not allowed for tool '{tool_name}': {url}",
                start_ms=start,
            )

        # 5. Route by operation
        if tool.operation == "http_request":
            return self._execute_http(request, tool_name, tool.timeout_s, start)

        return self._reject(
            request,
            reason=f"Unsupported tool operation: {tool.operation}",
            start_ms=start,
        )

    def _infer_tool_name(self, request: ExecutionRequest) -> str | None:
        """Infer tool name from request operation or inputs."""
        # Direct match: operation == tool name
        if get_tool(request.operation) is not None:
            return request.operation

        # Check for method hint in inputs
        method = request.inputs.get("method", "").upper()
        if request.operation == "http_request":
            if method == "GET":
                return "http_get"
            if method == "POST":
                return "http_post"
            # Default to GET for http_request without method
            return "http_get"

        return None

    def _execute_http(
        self,
        request: ExecutionRequest,
        tool_name: str,
        timeout_s: int,
        start_ms: int,
    ) -> ExecutionResult:
        """Perform an HTTP request using urllib.request."""
        url = request.inputs["url"]
        method = request.inputs.get("method") or _TOOL_METHOD_MAP.get(tool_name, "GET")
        method = method.upper()
        headers: dict[str, str] = dict(request.inputs.get("headers") or {})
        body: Any = request.inputs.get("body")

        # Ensure User-Agent
        if "User-Agent" not in headers:
            headers["User-Agent"] = _USER_AGENT

        _log.info(
            "[ToolsAdapter] http: method=%s url=%s tool=%s",
            method,
            url,
            tool_name,
        )

        # Encode body
        data: bytes | None = None
        if body is not None:
            if isinstance(body, str):
                data = body.encode("utf-8")
            elif isinstance(body, bytes):
                data = body
            else:
                # dict or other serializable
                data = json.dumps(body).encode("utf-8")
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            # Create a default SSL context for HTTPS
            ctx = ssl.create_default_context()
            response = urllib.request.urlopen(req, timeout=timeout_s, context=ctx)
            status_code = response.status
            response_headers = dict(response.headers)
            response_body = response.read(_MAX_RESPONSE_BYTES).decode("utf-8", errors="replace")

            elapsed = now_ms() - start_ms
            _log.info(
                "[ToolsAdapter] http succeeded: status=%d len=%d latency=%dms",
                status_code,
                len(response_body),
                elapsed,
            )

            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "status_code": status_code,
                    "response_body": response_body,
                    "response_headers": response_headers,
                    "url": url,
                    "method": method,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        except urllib.error.HTTPError as e:
            elapsed = now_ms() - start_ms
            try:
                err_body = e.read(_MAX_RESPONSE_BYTES).decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            _log.error(
                "[ToolsAdapter] http HTTPError: status=%d url=%s",
                e.code,
                url,
            )
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={
                    "status_code": e.code,
                    "response_body": err_body,
                    "response_headers": dict(e.headers) if e.headers else {},
                    "url": url,
                    "method": method,
                },
                error=f"HTTP {e.code}: {e.reason}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        except SocketTimeout:
            elapsed = now_ms() - start_ms
            _log.error("[ToolsAdapter] http timeout: url=%s after %ds", url, timeout_s)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.TIMED_OUT,
                outputs={"url": url, "method": method},
                error=f"Request timed out after {timeout_s}s",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        except urllib.error.URLError as e:
            elapsed = now_ms() - start_ms
            # URLError wraps timeout as well
            if isinstance(e.reason, SocketTimeout):
                _log.error("[ToolsAdapter] http timeout (URLError): url=%s", url)
                return ExecutionResult(
                    execution_id=request.execution_id,
                    correlation_id=request.correlation_id,
                    causal_event_id=request.causal_event_id,
                    operation=request.operation,
                    status=ExecutionStatus.TIMED_OUT,
                    outputs={"url": url, "method": method},
                    error=f"Request timed out after {timeout_s}s",
                    started_at=iso_now(),
                    completed_at=iso_now(),
                    latency_ms=elapsed,
                )
            _log.error("[ToolsAdapter] http URLError: %s url=%s", e, url)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"url": url, "method": method},
                error=f"HTTP error: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        except ssl.SSLError as e:
            elapsed = now_ms() - start_ms
            _log.error("[ToolsAdapter] SSL error: %s url=%s", e, url)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"url": url, "method": method},
                error=f"SSL error: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        except Exception as e:
            elapsed = now_ms() - start_ms
            _log.error("[ToolsAdapter] http unexpected error: %s url=%s", e, url)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"url": url, "method": method},
                error=str(e),
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _reject(
        self,
        request: ExecutionRequest,
        reason: str,
        start_ms: int,
    ) -> ExecutionResult:
        """Return a REJECTED result with timing info."""
        elapsed = now_ms() - start_ms
        _log.warning("[ToolsAdapter] rejected: %s", reason)
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.REJECTED,
            outputs={},
            error=reason,
            started_at=iso_now(),
            completed_at=iso_now(),
            latency_ms=elapsed,
        )
