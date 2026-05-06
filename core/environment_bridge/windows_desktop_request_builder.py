"""Windows Interactive Desktop Request Builder.

Builds typed JSON requests for the Windows Interactive Desktop Adapter
relay. Requests are validated before being emitted.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .windows_desktop_adapter_contracts import (
    BLOCKED_LAUNCH_METHODS,
    WindowsDesktopActionRequest,
    WindowsDesktopActionType,
)


CHROME_EXECUTABLE_PATH_WINDOWS = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
GOOGLE_DRIVE_URL = "https://drive.google.com/drive/my-drive"


def build_w0_chrome_open_request(
    work_order_id: str = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
    trace_id: str = "",
    url: str = GOOGLE_DRIVE_URL,
) -> WindowsDesktopActionRequest:
    """Build a W0 Chrome URL open request for the relay."""
    if not trace_id:
        trace_id = f"W0-relay-{uuid.uuid4().hex[:12]}"

    return WindowsDesktopActionRequest(
        request_id=f"REQ-W0-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        work_order_id=work_order_id,
        action_type=WindowsDesktopActionType.OPEN_APPLICATION_URL.value,
        environment_id="local_windows_desktop",
        execution_surface_id="windows_interactive_desktop_adapter",
        application_id="google_chrome_windows",
        executable_path=CHROME_EXECUTABLE_PATH_WINDOWS,
        launch_method="direct_executable",
        url=url,
        blocked_launch_methods=sorted(BLOCKED_LAUNCH_METHODS),
        proof_required="founder_visual_confirmation",
        no_secret_capture=True,
        no_mutation=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
        notes=[
            "Direct Chrome executable launch only",
            "No explorer.exe, no default-browser routing",
            "Founder visual confirmation required before advancing",
        ],
    )


def build_ping_request(
    trace_id: str = "",
) -> WindowsDesktopActionRequest:
    """Build a relay ping request."""
    if not trace_id:
        trace_id = f"ping-{uuid.uuid4().hex[:12]}"

    return WindowsDesktopActionRequest(
        request_id=f"REQ-PING-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        action_type=WindowsDesktopActionType.PING.value,
        environment_id="local_windows_desktop",
        execution_surface_id="windows_interactive_desktop_adapter",
        proof_required="none",
        no_secret_capture=True,
        no_mutation=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def request_to_json(request: WindowsDesktopActionRequest) -> dict[str, Any]:
    """Convert request to JSON-serializable dict."""
    return request.to_dict()
