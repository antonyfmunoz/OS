"""Computer use capability adapter — observation and approved mutation operations.

Routes computer_* operations through the external capability interface.
Read-only operations execute freely:
  - computer_screenshot: Capture screen as base64 PNG
  - computer_get_screen_size: Return screen dimensions
  - computer_get_active_window: Return active window title/geometry

Mutation operations require approval and execute via xdotool:
  - computer_click: Mouse move + click at coordinates
  - computer_type: Type text via keyboard
  - computer_key: Send key combination
  - computer_scroll: Scroll up/down
  - computer_drag: Mouse drag between coordinates
"""

from __future__ import annotations

import base64
import io
import logging
import subprocess

from umh.core.clock import iso_now, now_ms
from umh.execution.contract import ExecutionRequest, ExecutionResult, ExecutionStatus
from umh.execution.environment import EnvironmentSpec
from umh.execution.external import ExternalCapabilityAdapter

_log = logging.getLogger(__name__)

_SAFE_OPS = frozenset(
    {"computer_screenshot", "computer_get_screen_size", "computer_get_active_window"}
)

_MUTATION_OPS = frozenset(
    {"computer_click", "computer_type", "computer_key", "computer_scroll", "computer_drag"}
)


class ComputerUseAdapter(ExternalCapabilityAdapter):
    """Adapter for computer use capabilities — observation + approved mutations."""

    @property
    def adapter_name(self) -> str:
        return "computer_use_adapter"

    @property
    def capability_type(self) -> str:
        return "computer_use"

    def execute(self, request: ExecutionRequest, environment: EnvironmentSpec) -> ExecutionResult:
        op = request.operation
        if op == "computer_screenshot":
            return self._screenshot(request)
        if op == "computer_get_screen_size":
            return self._get_screen_size(request)
        if op == "computer_get_active_window":
            return self._get_active_window(request)
        if op in _MUTATION_OPS:
            approved = request.context.metadata.get("approved_execution", False)
            if not approved:
                return self._requires_approval(request)
            return self._execute_mutation(request)
        return self._not_implemented(request, reason=f"Unknown computer_use operation: {op}")

    def _screenshot(self, request: ExecutionRequest) -> ExecutionResult:
        start = now_ms()
        try:
            from PIL import ImageGrab

            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()
            b64 = base64.b64encode(png_bytes).decode("ascii")
            elapsed = now_ms() - start
            _log.info(
                "[ComputerUseAdapter] screenshot: %dx%d, %d bytes, %dms",
                img.width,
                img.height,
                len(png_bytes),
                elapsed,
            )
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "image_base64": b64,
                    "width": img.width,
                    "height": img.height,
                    "format": "png",
                    "size_bytes": len(png_bytes),
                    "adapter": self.adapter_name,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[ComputerUseAdapter] screenshot failed: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"adapter": self.adapter_name},
                error=f"Screenshot failed: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _get_screen_size(self, request: ExecutionRequest) -> ExecutionResult:
        start = now_ms()
        try:
            result = subprocess.run(
                ["xdpyinfo"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            width, height = 0, 0
            for line in result.stdout.splitlines():
                if "dimensions:" in line:
                    parts = line.split()
                    idx = parts.index("dimensions:") + 1
                    dims = parts[idx].split("x")
                    width, height = int(dims[0]), int(dims[1])
                    break
            elapsed = now_ms() - start
            _log.info("[ComputerUseAdapter] screen_size: %dx%d", width, height)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "width": width,
                    "height": height,
                    "text": f"{width}x{height}",
                    "adapter": self.adapter_name,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[ComputerUseAdapter] get_screen_size failed: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"adapter": self.adapter_name},
                error=f"Screen size query failed: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _get_active_window(self, request: ExecutionRequest) -> ExecutionResult:
        start = now_ms()
        try:
            result = subprocess.run(
                ["xdpyinfo"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            focus_info = "unknown"
            for line in result.stdout.splitlines():
                if "focus:" in line.lower():
                    focus_info = line.strip()
                    break
            elapsed = now_ms() - start
            _log.info("[ComputerUseAdapter] active_window: %s", focus_info)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "text": focus_info,
                    "adapter": self.adapter_name,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[ComputerUseAdapter] get_active_window failed: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"adapter": self.adapter_name},
                error=f"Active window query failed: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _execute_mutation(self, request: ExecutionRequest) -> ExecutionResult:
        """Route to the appropriate mutation implementation."""
        op = request.operation
        if op == "computer_click":
            return self._click(request)
        if op == "computer_type":
            return self._type(request)
        if op == "computer_key":
            return self._key(request)
        if op == "computer_scroll":
            return self._scroll(request)
        if op == "computer_drag":
            return self._drag(request)
        return self._requires_approval(request)

    def _click(self, request: ExecutionRequest) -> ExecutionResult:
        start = now_ms()
        x = request.inputs.get("x", 0)
        y = request.inputs.get("y", 0)
        button = request.inputs.get("button", 1)
        try:
            subprocess.run(
                ["xdotool", "mousemove", str(x), str(y)],
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                ["xdotool", "click", str(button)],
                capture_output=True,
                timeout=5,
            )
            elapsed = now_ms() - start
            _log.info("[ComputerUseAdapter] click: (%d,%d) button=%d %dms", x, y, button, elapsed)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "x": x,
                    "y": y,
                    "button": button,
                    "adapter": self.adapter_name,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[ComputerUseAdapter] click failed: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"adapter": self.adapter_name},
                error=f"Click failed: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _type(self, request: ExecutionRequest) -> ExecutionResult:
        start = now_ms()
        text = request.inputs.get("text", "")
        try:
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", text],
                capture_output=True,
                timeout=10,
            )
            elapsed = now_ms() - start
            _log.info("[ComputerUseAdapter] type: %d chars %dms", len(text), elapsed)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "chars_typed": len(text),
                    "adapter": self.adapter_name,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[ComputerUseAdapter] type failed: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"adapter": self.adapter_name},
                error=f"Type failed: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _key(self, request: ExecutionRequest) -> ExecutionResult:
        start = now_ms()
        key_combo = request.inputs.get("key", "")
        try:
            subprocess.run(
                ["xdotool", "key", key_combo],
                capture_output=True,
                timeout=5,
            )
            elapsed = now_ms() - start
            _log.info("[ComputerUseAdapter] key: %s %dms", key_combo, elapsed)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "key": key_combo,
                    "adapter": self.adapter_name,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[ComputerUseAdapter] key failed: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"adapter": self.adapter_name},
                error=f"Key failed: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _scroll(self, request: ExecutionRequest) -> ExecutionResult:
        start = now_ms()
        direction = request.inputs.get("direction", "down")
        clicks = request.inputs.get("clicks", 3)
        # xdotool: button 4 = scroll up, button 5 = scroll down
        button = 4 if direction == "up" else 5
        try:
            for _ in range(clicks):
                subprocess.run(
                    ["xdotool", "click", str(button)],
                    capture_output=True,
                    timeout=5,
                )
            elapsed = now_ms() - start
            _log.info("[ComputerUseAdapter] scroll: %s x%d %dms", direction, clicks, elapsed)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "direction": direction,
                    "clicks": clicks,
                    "adapter": self.adapter_name,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[ComputerUseAdapter] scroll failed: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"adapter": self.adapter_name},
                error=f"Scroll failed: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _drag(self, request: ExecutionRequest) -> ExecutionResult:
        start = now_ms()
        x1 = request.inputs.get("x1", 0)
        y1 = request.inputs.get("y1", 0)
        x2 = request.inputs.get("x2", 0)
        y2 = request.inputs.get("y2", 0)
        try:
            subprocess.run(
                ["xdotool", "mousemove", str(x1), str(y1)],
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                ["xdotool", "mousedown", "1"],
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                ["xdotool", "mousemove", str(x2), str(y2)],
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                ["xdotool", "mouseup", "1"],
                capture_output=True,
                timeout=5,
            )
            elapsed = now_ms() - start
            _log.info(
                "[ComputerUseAdapter] drag: (%d,%d)→(%d,%d) %dms",
                x1,
                y1,
                x2,
                y2,
                elapsed,
            )
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "adapter": self.adapter_name,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = now_ms() - start
            _log.error("[ComputerUseAdapter] drag failed: %s", e)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={"adapter": self.adapter_name},
                error=f"Drag failed: {e}",
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=elapsed,
            )

    def _requires_approval(self, request: ExecutionRequest) -> ExecutionResult:
        msg = f"Computer mutation operation requires approval: {request.operation}"
        _log.info("[ComputerUseAdapter] requires_approval: %s", request.operation)
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.REJECTED,
            outputs={
                "requires_approval": True,
                "reason": msg,
                "adapter": self.adapter_name,
            },
            error=msg,
        )
