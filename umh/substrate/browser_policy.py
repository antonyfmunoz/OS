"""
Browser Execution Policy — local-first browser target resolution with
fallback traceability.

Default: LOCAL_WORKSTATION.
VPS headless browser is fallback ONLY when local is unavailable.
Every resolution records intent, target preference, resolved target,
and fallback metadata for downstream traceability.

Design rules (mirror substrate conventions):
- Deterministic — no LLM, no heuristics.
- Additive — does not modify node_controller or station_daemon.
- Traceable — every resolution produces a BrowserActionRecord.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ─── Constants ──────────────────────────────────────────────────────────────

_LOG_PREFIX = "[substrate.browser_policy]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Browser Target ─────────────────────────────────────────────────────────


class BrowserTarget(str, Enum):
    """Where a browser action should physically execute."""

    LOCAL_WORKSTATION = "local_workstation"
    VPS_FALLBACK = "vps_fallback"


class FallbackReason(str, Enum):
    """Why the system fell back to VPS browser."""

    NONE = "none"  # no fallback — local was used
    LOCAL_OFFLINE = "local_offline"
    HTTP_TRANSPORT_DOWN = "http_transport_down"
    PRESENCE_UNAVAILABLE = "presence_unavailable"
    EXPLICIT_VPS_REQUEST = "explicit_vps_request"
    CAPABILITY_MISSING = "capability_missing"


# ─── Browser Action Record ──────────────────────────────────────────────────


@dataclass
class BrowserActionRecord:
    """Traceability record for every browser action resolution.

    Logged to workstation_log and optionally to event_spine.
    """

    record_id: str = field(default_factory=lambda: f"bar_{uuid.uuid4().hex[:10]}")
    timestamp: str = field(default_factory=_utcnow)
    requested_intent: str = ""
    requested_target: BrowserTarget = BrowserTarget.LOCAL_WORKSTATION
    resolved_target: BrowserTarget = BrowserTarget.LOCAL_WORKSTATION
    fallback_used: bool = False
    fallback_reason: FallbackReason = FallbackReason.NONE
    url: str = ""
    action_kind: str = ""  # ActionKind.value if applicable
    routing_node_id: str = ""
    transport: str = ""
    correlation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "requested_intent": self.requested_intent,
            "requested_target": self.requested_target.value,
            "resolved_target": self.resolved_target.value,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason.value,
            "url": self.url,
            "action_kind": self.action_kind,
            "routing_node_id": self.routing_node_id,
            "transport": self.transport,
            "correlation_id": self.correlation_id,
        }


# ─── Resolution ─────────────────────────────────────────────────────────────


def resolve_browser_target(
    *,
    intent: str = "",
    url: str = "",
    force_vps: bool = False,
    correlation_id: str = "",
) -> BrowserActionRecord:
    """Resolve the browser execution target with local-first preference.

    Checks local workstation availability (node online, HTTP transport,
    presence store) before falling back to VPS headless.

    Args:
        intent: The user's original intent string.
        url: The URL to open (if known).
        force_vps: If True, skip local checks and use VPS directly.
        correlation_id: Optional correlation ID for event spine.

    Returns:
        BrowserActionRecord with resolved target and fallback metadata.
    """
    record = BrowserActionRecord(
        requested_intent=intent,
        requested_target=BrowserTarget.LOCAL_WORKSTATION,
        url=url,
        correlation_id=correlation_id,
    )

    # Explicit VPS request — no local check needed
    if force_vps:
        record.resolved_target = BrowserTarget.VPS_FALLBACK
        record.fallback_used = True
        record.fallback_reason = FallbackReason.EXPLICIT_VPS_REQUEST
        _log(f"browser target: VPS (forced) for {url or intent!r}")
        _emit_record(record)
        return record

    # Check local workstation availability (same probes as node_controller)
    try:
        from umh.substrate.node_controller import (
            LOCAL_NODE_ID,
            _is_http_transport_available,
            _is_local_available_via_presence,
            _is_local_node_online,
        )

        node_online = _is_local_node_online()
        http_up = _is_http_transport_available() if node_online else False
        presence_ok = _is_local_available_via_presence() if not http_up else True

        if node_online and (http_up or presence_ok):
            # Local workstation is available — use it
            record.resolved_target = BrowserTarget.LOCAL_WORKSTATION
            record.routing_node_id = LOCAL_NODE_ID
            record.transport = "http" if http_up else "file_bus"
            _log(f"browser target: LOCAL ({record.transport}) for {url or intent!r}")
            _emit_record(record)
            return record

        # Local unavailable — determine specific reason
        record.resolved_target = BrowserTarget.VPS_FALLBACK
        record.fallback_used = True

        if not node_online:
            record.fallback_reason = FallbackReason.LOCAL_OFFLINE
        elif not http_up:
            record.fallback_reason = FallbackReason.HTTP_TRANSPORT_DOWN
        else:
            record.fallback_reason = FallbackReason.PRESENCE_UNAVAILABLE

        _log(
            f"browser target: VPS fallback ({record.fallback_reason.value}) "
            f"for {url or intent!r}"
        )
        _emit_record(record)
        return record

    except Exception as exc:
        # Import/probe failure — fall back to VPS safely
        _log(f"browser target resolution error: {exc} — using VPS fallback")
        record.resolved_target = BrowserTarget.VPS_FALLBACK
        record.fallback_used = True
        record.fallback_reason = FallbackReason.LOCAL_OFFLINE
        _emit_record(record)
        return record


# ─── Traceability ───────────────────────────────────────────────────────────


def _emit_record(record: BrowserActionRecord) -> None:
    """Emit browser action record to workstation log. Best-effort."""
    try:
        from umh.substrate.workstation_log import log_event

        log_event("browser_target_resolved", record.to_dict(), to_stderr=False)
    except Exception:
        pass


# ─── Playwright Suppression ─────────────────────────────────────────────────


def is_playwright_suppressed_for_intent(intent: str) -> bool:
    """Return True if Playwright should NOT handle this intent.

    Simple browser navigation (open URL, play media, search) must go
    through the OPEN_URL SafeAction path, not Playwright MCP tools.
    Playwright is only appropriate for:
      - Complex browser automation (scraping, form-filling sequences)
      - Explicit VPS fallback after local execution failure

    This function is deterministic — regex only, no LLM.
    """
    # Import here to avoid circular dependency
    try:
        from umh.substrate.conversation_router import is_browser_intent

        if is_browser_intent(intent):
            return True
    except ImportError:
        pass

    # Fallback: basic pattern check if conversation_router unavailable
    import re

    _simple_nav_re = re.compile(
        r"\b(open|go to|navigate to|visit|launch|browse|play|put on|"
        r"listen to|search|look up|pull up)\b",
        re.IGNORECASE,
    )
    return bool(_simple_nav_re.search(intent))


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = [
    "BrowserTarget",
    "FallbackReason",
    "BrowserActionRecord",
    "resolve_browser_target",
    "is_playwright_suppressed_for_intent",
]
