"""
umh.substrate.daily_rituals — Harness-side contracts and pure builders
for canonical open-day and close-day ritual sequences.

Provides request/plan dataclasses and deterministic builders only.
Symbolic steps represent harness-level operations — adapters consume
these to decide what product-specific actions to take.

No side effects. No Discord/Notion/UI rendering. No app launching.

Public API:
    OpenDayRequest              — frozen request to open the day
    CloseDayRequest             — frozen request to close the day
    OpenDayPlan                 — frozen plan for open-day sequence
    CloseDayPlan                — frozen plan for close-day sequence
    compute_open_day_request_id — deterministic request ID
    compute_close_day_request_id — deterministic request ID
    build_open_day_request      — construct open-day request
    build_close_day_request     — construct close-day request
    build_open_day_plan         — derive open-day plan from state + request
    build_close_day_plan        — derive close-day plan from state + request
    summarize_open_day_plan     — harness-generic plan summary
    summarize_close_day_plan    — harness-generic plan summary

Separation note:
    This module is harness-only. Product layers (Discord greeting,
    Notion publishing, workstation boot) consume plans as symbolic
    step lists — they do not live here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from umh.substrate.runtime_profile import RuntimeProfile

_LOG_PREFIX = "[substrate.daily_rituals]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Canonical symbolic step constants — open sequence
# ---------------------------------------------------------------------------
OPEN_STEP_IDENTIFY_SESSION_START = "identify_session_start"
OPEN_STEP_DETECT_ENTRY_TRANSPORT = "detect_entry_transport"
OPEN_STEP_LOAD_PRESENCE_STATE = "load_presence_state"
OPEN_STEP_LOAD_RUNTIME_PROFILE = "load_runtime_profile"
OPEN_STEP_BUILD_BRIEFING = "build_briefing"
OPEN_STEP_RESTORE_CONTINUITY = "restore_continuity"
OPEN_STEP_ACTIVATE_RUNTIME_MODE = "activate_runtime_mode"
OPEN_STEP_EXPOSE_RECOMMENDED_NEXT_ACTION = "expose_recommended_next_action"

CANONICAL_OPEN_STEPS: tuple[str, ...] = (
    OPEN_STEP_IDENTIFY_SESSION_START,
    OPEN_STEP_DETECT_ENTRY_TRANSPORT,
    OPEN_STEP_LOAD_PRESENCE_STATE,
    OPEN_STEP_LOAD_RUNTIME_PROFILE,
    OPEN_STEP_BUILD_BRIEFING,
    OPEN_STEP_RESTORE_CONTINUITY,
    OPEN_STEP_ACTIVATE_RUNTIME_MODE,
    OPEN_STEP_EXPOSE_RECOMMENDED_NEXT_ACTION,
)

# ---------------------------------------------------------------------------
# Canonical symbolic step constants — close sequence
# ---------------------------------------------------------------------------
CLOSE_STEP_IDENTIFY_SESSION_CLOSE = "identify_session_close"
CLOSE_STEP_SUMMARIZE_WORK_DONE = "summarize_work_done"
CLOSE_STEP_CAPTURE_UNRESOLVED_ITEMS = "capture_unresolved_items"
CLOSE_STEP_BUILD_HANDOFF = "build_handoff"
CLOSE_STEP_SHIFT_PRESENCE_STATE = "shift_presence_state"
CLOSE_STEP_SHIFT_RUNTIME_MODE = "shift_runtime_mode"
CLOSE_STEP_PRESERVE_OR_SUSPEND_SURFACES = "preserve_or_suspend_surfaces"
CLOSE_STEP_FINALIZE_OVERNIGHT_STATE = "finalize_overnight_state"

CANONICAL_CLOSE_STEPS: tuple[str, ...] = (
    CLOSE_STEP_IDENTIFY_SESSION_CLOSE,
    CLOSE_STEP_SUMMARIZE_WORK_DONE,
    CLOSE_STEP_CAPTURE_UNRESOLVED_ITEMS,
    CLOSE_STEP_BUILD_HANDOFF,
    CLOSE_STEP_SHIFT_PRESENCE_STATE,
    CLOSE_STEP_SHIFT_RUNTIME_MODE,
    CLOSE_STEP_PRESERVE_OR_SUSPEND_SURFACES,
    CLOSE_STEP_FINALIZE_OVERNIGHT_STATE,
)


# ---------------------------------------------------------------------------
# OpenDayRequest
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OpenDayRequest:
    """Frozen request to open the day for a runtime session.

    Fields:
        request_id:           deterministic request identifier
        runtime_session_id:   owning session
        entry_transport:      transport through which the day is opened
        requested_profile_id: profile to activate (empty = use default)
        requested_mode:       mode override (empty = use profile default)
        requested_presence:   presence override (empty = use profile default)
        requested_at:         ISO timestamp of request
        correlation_id:       links to upstream event chain
    """

    request_id: str
    runtime_session_id: str
    entry_transport: str
    requested_profile_id: str = ""
    requested_mode: str = ""
    requested_presence: str = ""
    requested_at: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.requested_at:
            object.__setattr__(self, "requested_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "correlation_id": self.correlation_id,
            "entry_transport": self.entry_transport,
            "request_id": self.request_id,
            "requested_at": self.requested_at,
            "requested_mode": self.requested_mode,
            "requested_presence": self.requested_presence,
            "requested_profile_id": self.requested_profile_id,
            "runtime_session_id": self.runtime_session_id,
        }


# ---------------------------------------------------------------------------
# CloseDayRequest
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CloseDayRequest:
    """Frozen request to close the day for a runtime session.

    Fields:
        request_id:                 deterministic request identifier
        runtime_session_id:         owning session
        requested_mode_after_close: mode to transition to after close
        requested_at:               ISO timestamp of request
        correlation_id:             links to upstream event chain
    """

    request_id: str
    runtime_session_id: str
    requested_mode_after_close: str = ""
    requested_at: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.requested_at:
            object.__setattr__(self, "requested_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "requested_at": self.requested_at,
            "requested_mode_after_close": self.requested_mode_after_close,
            "runtime_session_id": self.runtime_session_id,
        }


# ---------------------------------------------------------------------------
# OpenDayPlan
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OpenDayPlan:
    """Frozen plan for executing an open-day sequence.

    Fields:
        plan_id:            deterministic plan identifier
        runtime_session_id: owning session
        profile_id:         resolved profile for this plan
        mode:               resolved mode for this plan
        presence:           resolved presence for this plan
        steps:              ordered symbolic step identifiers
        created_at:         ISO timestamp of plan creation
        summary:            harness-generic plan summary
    """

    plan_id: str
    runtime_session_id: str
    profile_id: str
    mode: str
    presence: str
    steps: tuple[str, ...]
    created_at: str
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "created_at": self.created_at,
            "mode": self.mode,
            "plan_id": self.plan_id,
            "presence": self.presence,
            "profile_id": self.profile_id,
            "runtime_session_id": self.runtime_session_id,
            "steps": list(self.steps),
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# CloseDayPlan
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CloseDayPlan:
    """Frozen plan for executing a close-day sequence.

    Fields:
        plan_id:            deterministic plan identifier
        runtime_session_id: owning session
        mode_after_close:   mode to transition to after closing
        overnight_enabled:  whether overnight autonomy is enabled
        steps:              ordered symbolic step identifiers
        created_at:         ISO timestamp of plan creation
        summary:            harness-generic plan summary
    """

    plan_id: str
    runtime_session_id: str
    mode_after_close: str
    overnight_enabled: bool
    steps: tuple[str, ...]
    created_at: str
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "created_at": self.created_at,
            "mode_after_close": self.mode_after_close,
            "overnight_enabled": self.overnight_enabled,
            "plan_id": self.plan_id,
            "runtime_session_id": self.runtime_session_id,
            "steps": list(self.steps),
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Deterministic IDs
# ---------------------------------------------------------------------------


def compute_open_day_request_id(
    runtime_session_id: str,
    requested_at: str,
) -> str:
    """Deterministic open-day request ID."""
    canonical = json.dumps(
        {
            "kind": "open_day",
            "requested_at": requested_at,
            "runtime_session_id": runtime_session_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"odr_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def compute_close_day_request_id(
    runtime_session_id: str,
    requested_at: str,
) -> str:
    """Deterministic close-day request ID."""
    canonical = json.dumps(
        {
            "kind": "close_day",
            "requested_at": requested_at,
            "runtime_session_id": runtime_session_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"cdr_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def _compute_plan_id(kind: str, runtime_session_id: str, created_at: str) -> str:
    """Deterministic plan ID for open/close day plans."""
    canonical = json.dumps(
        {
            "created_at": created_at,
            "kind": kind,
            "runtime_session_id": runtime_session_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"dp_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Request builders
# ---------------------------------------------------------------------------


def build_open_day_request(
    *,
    runtime_session_id: str,
    entry_transport: str,
    requested_profile_id: str = "",
    requested_mode: str = "",
    requested_presence: str = "",
    correlation_id: str = "",
    requested_at: str = "",
) -> OpenDayRequest:
    """Construct an OpenDayRequest with deterministic ID."""
    ts = requested_at or _utcnow()
    rid = compute_open_day_request_id(runtime_session_id, ts)
    return OpenDayRequest(
        request_id=rid,
        runtime_session_id=runtime_session_id,
        entry_transport=entry_transport,
        requested_profile_id=requested_profile_id,
        requested_mode=requested_mode,
        requested_presence=requested_presence,
        requested_at=ts,
        correlation_id=correlation_id,
    )


def build_close_day_request(
    *,
    runtime_session_id: str,
    requested_mode_after_close: str = "",
    correlation_id: str = "",
    requested_at: str = "",
) -> CloseDayRequest:
    """Construct a CloseDayRequest with deterministic ID."""
    ts = requested_at or _utcnow()
    rid = compute_close_day_request_id(runtime_session_id, ts)
    return CloseDayRequest(
        request_id=rid,
        runtime_session_id=runtime_session_id,
        requested_mode_after_close=requested_mode_after_close,
        requested_at=ts,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Plan builders — pure functions, no side effects
# ---------------------------------------------------------------------------


def build_open_day_plan(
    state: dict[str, Any],
    request: OpenDayRequest,
    profile: RuntimeProfile | None = None,
) -> OpenDayPlan:
    """Derive an OpenDayPlan from state, request, and optional profile.

    Resolves mode and presence from: request overrides -> profile defaults
    -> fallback empty string. Steps are always the canonical open sequence.
    """
    now = _utcnow()
    plan_id = _compute_plan_id("open_day", request.runtime_session_id, now)

    # Resolve mode: explicit request > profile default > empty
    mode = request.requested_mode
    if not mode and profile:
        mode = profile.default_mode

    # Resolve presence: explicit request > profile default > empty
    presence = request.requested_presence
    if not presence and profile:
        presence = profile.default_presence

    # Resolve profile_id
    profile_id = request.requested_profile_id
    if not profile_id and profile:
        profile_id = profile.profile_id

    summary = _build_open_summary(
        profile_id=profile_id,
        mode=mode,
        presence=presence,
        transport=request.entry_transport,
    )

    return OpenDayPlan(
        plan_id=plan_id,
        runtime_session_id=request.runtime_session_id,
        profile_id=profile_id,
        mode=mode,
        presence=presence,
        steps=CANONICAL_OPEN_STEPS,
        created_at=now,
        summary=summary,
    )


def build_close_day_plan(
    state: dict[str, Any],
    request: CloseDayRequest,
) -> CloseDayPlan:
    """Derive a CloseDayPlan from state and request.

    Overnight autonomy is enabled when mode_after_close indicates
    overnight operation (contains 'overnight' or 'autonomous').
    """
    now = _utcnow()
    plan_id = _compute_plan_id("close_day", request.runtime_session_id, now)

    mode_after = request.requested_mode_after_close
    overnight = "overnight" in mode_after.lower() or "autonomous" in mode_after.lower()

    summary = _build_close_summary(
        mode_after_close=mode_after,
        overnight_enabled=overnight,
    )

    return CloseDayPlan(
        plan_id=plan_id,
        runtime_session_id=request.runtime_session_id,
        mode_after_close=mode_after,
        overnight_enabled=overnight,
        steps=CANONICAL_CLOSE_STEPS,
        created_at=now,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Summaries — harness-generic, no product copy
# ---------------------------------------------------------------------------


def _build_open_summary(
    *,
    profile_id: str,
    mode: str,
    presence: str,
    transport: str,
) -> str:
    """Internal: build open-day plan summary."""
    parts = ["open day:"]
    if profile_id:
        parts.append(f"profile={profile_id}")
    if mode:
        parts.append(f"mode={mode}")
    if presence:
        parts.append(f"presence={presence}")
    if transport:
        parts.append(f"transport={transport}")
    parts.append(f"{len(CANONICAL_OPEN_STEPS)} steps")
    return " ".join(parts)


def _build_close_summary(
    *,
    mode_after_close: str,
    overnight_enabled: bool,
) -> str:
    """Internal: build close-day plan summary."""
    parts = ["close day:"]
    if mode_after_close:
        parts.append(f"mode_after={mode_after_close}")
    parts.append(f"overnight={'enabled' if overnight_enabled else 'disabled'}")
    parts.append(f"{len(CANONICAL_CLOSE_STEPS)} steps")
    return " ".join(parts)


def summarize_open_day_plan(plan: OpenDayPlan) -> str:
    """Build harness-generic summary for an open-day plan.

    Returns the stored summary if present, otherwise builds one.
    """
    if plan.summary:
        return plan.summary
    return _build_open_summary(
        profile_id=plan.profile_id,
        mode=plan.mode,
        presence=plan.presence,
        transport="",
    )


def summarize_close_day_plan(plan: CloseDayPlan) -> str:
    """Build harness-generic summary for a close-day plan.

    Returns the stored summary if present, otherwise builds one.
    """
    if plan.summary:
        return plan.summary
    return _build_close_summary(
        mode_after_close=plan.mode_after_close,
        overnight_enabled=plan.overnight_enabled,
    )
