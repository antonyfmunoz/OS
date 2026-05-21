"""Browser capability adapter — stub for future browser automation.

Routes browser_* operations through the external capability interface.
Currently returns NOT_IMPLEMENTED for all operations. Future implementation
will integrate with Playwright/Puppeteer via container execution.

Operations:
  - browser_navigate: Navigate to URL
  - browser_click: Click element
  - browser_type: Type text into element
  - browser_screenshot: Capture page screenshot
  - browser_extract: Extract content from page
"""

from __future__ import annotations

from umh.execution.contract import ExecutionRequest, ExecutionResult
from umh.execution.environment import EnvironmentSpec
from umh.execution.external import ExternalCapabilityAdapter


class BrowserAdapter(ExternalCapabilityAdapter):
    """Stub adapter for browser automation capabilities."""

    @property
    def adapter_name(self) -> str:
        return "browser_adapter"

    @property
    def capability_type(self) -> str:
        return "browser_action"

    def execute(self, request: ExecutionRequest, environment: EnvironmentSpec) -> ExecutionResult:
        return self._not_implemented(
            request,
            reason=f"Browser automation not yet implemented: {request.operation}",
        )
