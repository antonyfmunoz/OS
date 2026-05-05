"""EOS → UMH execution backend adapter.

Routes ExecutionRequests through model_router.call_with_fallback(),
replacing NullExecutionBackend so that execute() and all its callers
(lightweight_execute, utility_llm_call, run_via_umh) produce real results.

Discovered automatically by umh.execution.interfaces._default_backend()
via discover_platform_adapter("umh.adapters.umh_execution",
"get_execution_backend_adapter").
"""

from __future__ import annotations

import logging
from typing import Any

from umh.execution.contract import (
    ExecutionClass,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)

_log = logging.getLogger(__name__)

_LLM_OPERATIONS = frozenset(
    {
        "classify_intent",
        "extract_entities",
        "summarize",
        "short_response",
        "validation",
        "utility",
        "llm_generate",
        "fast_response",
        "analyze",
        "generate",
        "score",
        "journal",
    }
)

_SHELL_ALLOWLIST: dict[str, list[str]] = {
    "git status": ["git", "status"],
    "git log --oneline -10": ["git", "log", "--oneline", "-10"],
    "git diff --stat": ["git", "diff", "--stat"],
    "docker ps": ["docker", "ps"],
    "docker ps -a": ["docker", "ps", "-a"],
    "uptime": ["uptime"],
    "df -h": ["df", "-h"],
    "free -h": ["free", "-h"],
    "date": ["date"],
    "whoami": ["whoami"],
    "python3 --version": ["python3", "--version"],
    "pip list": ["pip", "list"],
}


class SpineExecutionBackend:
    """Routes LLM_CALL requests through model_router.call_with_fallback."""

    def can_handle(self, operation: str) -> bool:
        if operation in _LLM_OPERATIONS:
            return True
        if operation in _SHELL_ALLOWLIST:
            return True
        if operation in ("shell_command", "file_read", "file_write", "file_list", "file_stat"):
            return True
        if operation.startswith(("browser_", "computer_", "os_")):
            return True
        if operation in ("http_request", "http_get", "http_post", "webhook"):
            return True
        if operation.startswith("tool_"):
            return True
        return False

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if request.execution_class == ExecutionClass.LLM_CALL:
            return self._execute_llm(request)
        if request.execution_class == ExecutionClass.SIDE_EFFECT:
            return self._execute_side_effect(request)
        return self._not_implemented(request)

    def _execute_side_effect(self, request: ExecutionRequest) -> ExecutionResult:
        """Route side-effect requests based on operation type."""
        op = request.operation
        if op == "shell_command":
            return self._execute_shell(request)
        if op == "file_read":
            return self._execute_file_read(request)
        if op == "file_list":
            return self._execute_list_dir(request)
        if op == "file_stat":
            return self._execute_stat_file(request)
        if op in ("file_write", "file_delete"):
            return self._not_implemented(
                request, reason=f"Write operations not yet implemented: {op}"
            )
        # External capability routing — check adapter registry
        return self._execute_external(request)

    def _execute_external(self, request: ExecutionRequest) -> ExecutionResult:
        """Route to an external capability adapter if registered."""
        from umh.execution.environment import select_environment
        from umh.execution.external import get_adapter

        capability = self._classify_external(request.operation)
        adapter = get_adapter(capability)
        if adapter is not None:
            env = select_environment(request)
            _log.info(
                "[SpineExecutionBackend] external: adapter=%s op=%s env=%s",
                adapter.adapter_name,
                request.operation,
                env.id,
            )
            return adapter.execute(request, env)

        return self._not_implemented(
            request, reason=f"Unknown side-effect operation: {request.operation}"
        )

    @staticmethod
    def _classify_external(operation: str) -> str:
        """Map operation to external capability type."""
        if operation.startswith("browser_"):
            return "browser_action"
        if operation.startswith("computer_"):
            return "computer_use"
        if operation.startswith("os_"):
            return "os_interaction"
        if operation in ("http_request", "http_get", "http_post", "webhook"):
            return "tool_action"
        if operation.startswith("tool_"):
            return "tool_action"
        return operation

    def _execute_shell(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute an allowlisted shell command."""
        import subprocess

        from umh.core.clock import iso_now, now_ms

        command = request.inputs.get("command", "")
        _log.info("[SpineExecutionBackend] shell: command=%r", command)

        start = now_ms()

        # Security: strict allowlist
        allowed = _SHELL_ALLOWLIST.get(command.strip())
        if allowed is None:
            elapsed = now_ms() - start
            _log.warning("[SpineExecutionBackend] shell DENIED: %r not in allowlist", command)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.REJECTED,
                outputs={"text": f"Command not allowed: {command}"},
                error=f"Command '{command}' not in allowlist",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        try:
            result = subprocess.run(
                allowed,
                capture_output=True,
                text=True,
                timeout=request.constraints.timeout_s or 30,
                cwd="/opt/OS",
            )
            elapsed = now_ms() - start
            output = result.stdout.strip() or result.stderr.strip() or ""

            _log.info(
                "[SpineExecutionBackend] shell succeeded: exit=%d len=%d latency=%dms",
                result.returncode,
                len(output),
                elapsed,
            )

            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED
                if result.returncode == 0
                else ExecutionStatus.FAILED,
                outputs={
                    "text": output,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = now_ms() - start
            _log.error(
                "[SpineExecutionBackend] shell timeout: %r after %ds",
                command,
                request.constraints.timeout_s,
            )
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.TIMED_OUT,
                outputs={},
                error=f"Command timed out after {request.constraints.timeout_s}s",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[SpineExecutionBackend] shell error: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=str(e),
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _execute_file_read(self, request: ExecutionRequest) -> ExecutionResult:
        """Read a file within the sandbox."""
        import os

        from umh.core.clock import iso_now, now_ms
        from umh.security.execution_guard import GuardVerdict, check_file_operation

        path = request.inputs.get("path", "")
        _log.info("[SpineExecutionBackend] file_read: path=%r", path)
        start = now_ms()

        guard = check_file_operation("file_read", path)
        if guard.verdict != GuardVerdict.ALLOW:
            elapsed = now_ms() - start
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.REJECTED,
                outputs={"guard_denied": True, "reason": guard.reason},
                error=f"Guard denied: {guard.reason}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        resolved = (
            guard.sanitized_inputs["path"] if guard.sanitized_inputs else os.path.realpath(path)
        )
        try:
            max_bytes = request.inputs.get("max_bytes", 1_000_000)  # 1MB default limit
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
            elapsed = now_ms() - start
            file_size = os.path.getsize(resolved)
            _log.info(
                "[SpineExecutionBackend] file_read succeeded: %d bytes from %s",
                len(content),
                resolved,
            )
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "text": content,
                    "path": resolved,
                    "size_bytes": file_size,
                    "truncated": file_size > max_bytes,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except FileNotFoundError:
            elapsed = now_ms() - start
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=f"File not found: {resolved}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[SpineExecutionBackend] file_read error: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=str(e),
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _execute_list_dir(self, request: ExecutionRequest) -> ExecutionResult:
        """List directory contents within the sandbox."""
        import os

        from umh.core.clock import iso_now, now_ms
        from umh.security.execution_guard import GuardVerdict, check_file_operation

        path = request.inputs.get("path", "")
        _log.info("[SpineExecutionBackend] file_list: path=%r", path)
        start = now_ms()

        guard = check_file_operation("file_read", path)  # read permission for listing
        if guard.verdict != GuardVerdict.ALLOW:
            elapsed = now_ms() - start
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.REJECTED,
                outputs={"guard_denied": True, "reason": guard.reason},
                error=f"Guard denied: {guard.reason}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        resolved = (
            guard.sanitized_inputs["path"] if guard.sanitized_inputs else os.path.realpath(path)
        )
        try:
            entries = []
            for entry in os.scandir(resolved):
                entries.append(
                    {
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "is_file": entry.is_file(),
                        "size": entry.stat().st_size if entry.is_file() else 0,
                    }
                )
            elapsed = now_ms() - start
            _log.info(
                "[SpineExecutionBackend] file_list succeeded: %d entries in %s",
                len(entries),
                resolved,
            )
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "text": "\n".join(e["name"] for e in entries),
                    "entries": entries,
                    "path": resolved,
                    "count": len(entries),
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except FileNotFoundError:
            elapsed = now_ms() - start
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=f"Directory not found: {resolved}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[SpineExecutionBackend] file_list error: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=str(e),
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _execute_stat_file(self, request: ExecutionRequest) -> ExecutionResult:
        """Get file/directory metadata within the sandbox."""
        import os
        import time

        from umh.core.clock import iso_now, now_ms
        from umh.security.execution_guard import GuardVerdict, check_file_operation

        path = request.inputs.get("path", "")
        _log.info("[SpineExecutionBackend] file_stat: path=%r", path)
        start = now_ms()

        guard = check_file_operation("file_read", path)
        if guard.verdict != GuardVerdict.ALLOW:
            elapsed = now_ms() - start
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.REJECTED,
                outputs={"guard_denied": True, "reason": guard.reason},
                error=f"Guard denied: {guard.reason}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        resolved = (
            guard.sanitized_inputs["path"] if guard.sanitized_inputs else os.path.realpath(path)
        )
        try:
            st = os.stat(resolved)
            stat_info = {
                "path": resolved,
                "exists": True,
                "is_file": os.path.isfile(resolved),
                "is_dir": os.path.isdir(resolved),
                "size_bytes": st.st_size,
                "modified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime)),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_ctime)),
            }
            elapsed = now_ms() - start
            _log.info("[SpineExecutionBackend] file_stat succeeded: %s", resolved)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={"text": f"{resolved}: {st.st_size} bytes", **stat_info},
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except FileNotFoundError:
            elapsed = now_ms() - start
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "text": f"{resolved}: does not exist",
                    "path": resolved,
                    "exists": False,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[SpineExecutionBackend] file_stat error: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=str(e),
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _execute_llm(self, request: ExecutionRequest) -> ExecutionResult:
        from umh.core.clock import iso_now, now_ms
        from umh.runtime_engine.model_router import call_with_fallback

        prompt = request.inputs.get("prompt", "")
        system = request.inputs.get("system_prompt")
        max_tokens = request.inputs.get("max_tokens") or request.constraints.max_tokens or 1024
        metadata = request.context.metadata if request.context else {}
        task_type = metadata.get("task_type", "fast_response")
        agent_type = request.context.agent_type if request.context else "executive_assistant"

        _log.info(
            "[SpineExecutionBackend] execute: op=%s task=%s agent=%s prompt_len=%d",
            request.operation,
            task_type,
            agent_type or "default",
            len(prompt),
        )

        start = now_ms()
        try:
            routing_result = call_with_fallback(
                prompt=prompt,
                system=system or None,
                task_type=task_type,
                agent_type=agent_type or "executive_assistant",
                trigger_source=request.issued_by or "execution_backend",
                max_tokens=max_tokens,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[SpineExecutionBackend] call_with_fallback raised: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=str(e),
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        elapsed = now_ms() - start

        if not routing_result or not routing_result.output:
            _log.warning("[SpineExecutionBackend] empty response from model chain")
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"text": ""},
                error="Empty response from model chain",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

        _log.info(
            "[SpineExecutionBackend] succeeded: provider=%s model=%s tokens=%d latency=%dms",
            routing_result.provider,
            routing_result.model,
            routing_result.tokens_used,
            elapsed,
        )

        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.SUCCEEDED,
            outputs={"text": routing_result.output},
            started_at=iso_now(),
            completed_at=iso_now(),
            latency_ms=elapsed,
            model_used=f"{routing_result.provider}/{routing_result.model}",
            tokens_used={
                "input": routing_result.input_tokens,
                "output": routing_result.output_tokens,
                "total": routing_result.tokens_used,
            },
            cost_usd=routing_result.cost_usd,
        )

    def _not_implemented(self, request: ExecutionRequest, reason: str = "") -> ExecutionResult:
        """Return structured NOT_IMPLEMENTED for unimplemented capabilities."""
        msg = reason or (f"Not implemented: {request.execution_class.value}/{request.operation}")
        _log.info("[SpineExecutionBackend] not_implemented: %s", msg)
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.REJECTED,
            outputs={"not_implemented": True, "reason": msg},
            error=msg,
        )

    def _reject(self, request: ExecutionRequest, reason: str) -> ExecutionResult:
        _log.warning("[SpineExecutionBackend] rejected: %s", reason)
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.REJECTED,
            outputs={},
            error=reason,
        )


_BACKEND_INSTANCE: SpineExecutionBackend | None = None


def _register_external_adapters() -> None:
    """Register all external capability adapters."""
    from umh.execution.external import register_adapter

    from umh.adapters.browser_adapter import BrowserAdapter
    from umh.adapters.computer_use_adapter import ComputerUseAdapter
    from umh.adapters.tools_adapter import ToolsAdapter

    register_adapter(BrowserAdapter())
    register_adapter(ComputerUseAdapter())
    register_adapter(ToolsAdapter())


def get_execution_backend_adapter() -> SpineExecutionBackend:
    """Factory discovered by umh.adapters.bridge.discover_platform_adapter."""
    global _BACKEND_INSTANCE
    if _BACKEND_INSTANCE is None:
        _BACKEND_INSTANCE = SpineExecutionBackend()
        _register_external_adapters()
        _log.info("[SpineExecutionBackend] adapter activated")
    return _BACKEND_INSTANCE


class LoggingExecutionObserver:
    """Logs execution lifecycle events for observability."""

    def on_request(self, request: ExecutionRequest) -> None:
        try:
            _log.info(
                "[ExecutionObserver] request: id=%s op=%s class=%s issued_by=%s",
                request.execution_id,
                request.operation,
                request.execution_class.value,
                request.issued_by,
            )
        except Exception:
            pass

    def on_result(self, result: ExecutionResult) -> None:
        try:
            _log.info(
                "[ExecutionObserver] result: id=%s op=%s status=%s model=%s latency=%dms",
                result.execution_id,
                result.operation,
                result.status.value,
                result.model_used or "none",
                result.latency_ms,
            )
        except Exception:
            pass


_OBSERVER_INSTANCE: "EnhancedExecutionObserver | None" = None


def get_execution_observer_adapter() -> "EnhancedExecutionObserver":
    """Factory discovered by umh.adapters.bridge.discover_platform_adapter."""
    from umh.execution.observability import EnhancedExecutionObserver

    global _OBSERVER_INSTANCE
    if _OBSERVER_INSTANCE is None:
        _OBSERVER_INSTANCE = EnhancedExecutionObserver()
        _log.info("[EnhancedExecutionObserver] observer activated")
    return _OBSERVER_INSTANCE
