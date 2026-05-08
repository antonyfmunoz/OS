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


def build_w0_drive_safe_test_doc_request(
    safe_doc_url: str = "",
    trace_id: str = "",
) -> WindowsDesktopActionRequest:
    """Build a request to open a safe test document in Chrome.

    Uses the configured safe doc URL. Falls back to Google Drive
    homepage if no specific doc URL is provided. This is an
    interaction proof — no content extraction.
    """
    if not safe_doc_url:
        safe_doc_url = GOOGLE_DRIVE_URL

    if not trace_id:
        trace_id = f"W0-doc-{uuid.uuid4().hex[:12]}"

    return WindowsDesktopActionRequest(
        request_id=f"REQ-W0-DOC-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        work_order_id="WO-LOCAL-PILOT-GDRIVE-DOC-INTERACTION-001",
        action_type=WindowsDesktopActionType.OPEN_APPLICATION_URL.value,
        environment_id="local_windows_desktop",
        execution_surface_id="windows_interactive_desktop_adapter",
        application_id="google_chrome_windows",
        executable_path=CHROME_EXECUTABLE_PATH_WINDOWS,
        launch_method="direct_executable",
        url=safe_doc_url,
        blocked_launch_methods=sorted(BLOCKED_LAUNCH_METHODS),
        proof_required="founder_visual_confirmation",
        no_secret_capture=True,
        no_mutation=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
        notes=[
            "Drive/Docs interaction proof only",
            "No content extraction",
            "No screenshots or OCR",
            "Founder visual confirmation required",
        ],
    )


def build_w0_doc_extract_safe_test_doc_request(
    safe_doc_url: str = "",
    safe_doc_title: str = "EOS W0 Test Document",
    extraction_preview_max: int = 500,
    trace_id: str = "",
) -> WindowsDesktopActionRequest:
    """Build a bounded extraction request for the safe test document."""
    if not safe_doc_url:
        safe_doc_url = GOOGLE_DRIVE_URL

    if not trace_id:
        trace_id = f"W0-extract-{uuid.uuid4().hex[:12]}"

    return WindowsDesktopActionRequest(
        request_id=f"REQ-W0-EXTRACT-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        work_order_id="WO-LOCAL-PILOT-GDRIVE-DOC-EXTRACTION-001",
        action_type="doc_extract_safe_test_doc",
        environment_id="local_windows_desktop",
        execution_surface_id="windows_interactive_desktop_adapter",
        application_id="google_chrome_windows",
        executable_path=CHROME_EXECUTABLE_PATH_WINDOWS,
        launch_method="direct_executable",
        url=safe_doc_url,
        blocked_launch_methods=sorted(BLOCKED_LAUNCH_METHODS),
        proof_required="founder_visual_confirmation",
        no_secret_capture=True,
        no_mutation=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
        notes=[
            "Bounded extraction from one safe test document only",
            "No Drive-wide search",
            "No arbitrary URLs",
            "No screenshots or OCR",
            "No mutation",
            "No memory promotion",
            f"Preview bounded to {extraction_preview_max} characters",
            f"Target document: {safe_doc_title}",
            "Founder visual confirmation required",
        ],
    )


def build_w0_doc_ingestion_candidate_request(
    safe_doc_url: str = "",
    safe_doc_title: str = "EOS W0 Test Document",
    extraction_reference_id: str = "",
    trace_id: str = "",
) -> WindowsDesktopActionRequest:
    """Build an ingestion candidate request from a safe test doc extraction."""
    if not safe_doc_url:
        safe_doc_url = GOOGLE_DRIVE_URL

    if not trace_id:
        trace_id = f"W0-ingest-cand-{uuid.uuid4().hex[:12]}"

    return WindowsDesktopActionRequest(
        request_id=f"REQ-W0-INGEST-CAND-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        work_order_id="WO-LOCAL-PILOT-GDRIVE-DOC-INGESTION-CANDIDATE-001",
        action_type="doc_ingestion_candidate_safe_test_doc",
        environment_id="local_windows_desktop",
        execution_surface_id="windows_interactive_desktop_adapter",
        application_id="google_chrome_windows",
        executable_path=CHROME_EXECUTABLE_PATH_WINDOWS,
        launch_method="direct_executable",
        url=safe_doc_url,
        blocked_launch_methods=sorted(BLOCKED_LAUNCH_METHODS),
        proof_required="founder_visual_confirmation",
        no_secret_capture=True,
        no_mutation=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
        notes=[
            "Ingestion candidate creation from bounded extraction only",
            "No memory promotion",
            "No canonical writes",
            "No world-model updates",
            "No embeddings",
            "No interpretation or summarization",
            "Candidate only — governance approval required before promotion",
            f"Source document: {safe_doc_title}",
            f"Extraction reference: {extraction_reference_id or 'pending'}",
            "Founder visual confirmation required",
        ],
    )


def build_w0_promote_safe_memory_candidate_request(
    candidate_id: str = "",
    governance_review_id: str = "",
    safe_doc_url: str = "",
    safe_doc_title: str = "EOS W0 Test Document",
    trace_id: str = "",
) -> WindowsDesktopActionRequest:
    """Build a governed memory promotion request for a safe candidate."""
    if not safe_doc_url:
        safe_doc_url = GOOGLE_DRIVE_URL

    if not trace_id:
        trace_id = f"W0-promote-{uuid.uuid4().hex[:12]}"

    return WindowsDesktopActionRequest(
        request_id=f"REQ-W0-PROMOTE-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        work_order_id="WO-LOCAL-PILOT-GDRIVE-DOC-MEMORY-PROMOTION-001",
        action_type="promote_safe_memory_candidate",
        environment_id="local_windows_desktop",
        execution_surface_id="windows_interactive_desktop_adapter",
        application_id="google_chrome_windows",
        executable_path=CHROME_EXECUTABLE_PATH_WINDOWS,
        launch_method="direct_executable",
        url=safe_doc_url,
        blocked_launch_methods=sorted(BLOCKED_LAUNCH_METHODS),
        proof_required="founder_visual_confirmation",
        no_secret_capture=True,
        no_mutation=False,
        timestamp=datetime.now(timezone.utc).isoformat(),
        notes=[
            "Governed memory promotion from reviewed candidate",
            "Requires explicit governance review approval",
            "No autonomous promotion",
            "No recursive promotion",
            "No embeddings generation",
            "No semantic interpretation",
            "Bounded canonical write only",
            "Audit artifact required",
            "Rollback reference required",
            f"Source document: {safe_doc_title}",
            f"Candidate: {candidate_id or 'pending'}",
            f"Governance review: {governance_review_id or 'pending'}",
        ],
    )


def request_to_json(request: WindowsDesktopActionRequest) -> dict[str, Any]:
    """Convert request to JSON-serializable dict."""
    return request.to_dict()
