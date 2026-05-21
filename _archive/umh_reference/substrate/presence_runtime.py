"""
Presence runtime — first-class presence modes, work profiles, and bootstrap
requirements as runtime modifiers.

Presence mode answers: WHERE is the operator, HOW interruptible are they?
Profile answers: WHAT kind of work is being done?

These are orthogonal dimensions. ACTIVE_LOCAL + builder is different from
ACTIVE_LOCAL + founder.

Required modes:
  - ACTIVE_LOCAL   — at the primary workstation, fully available
  - AWAY_LOCAL     — machine on but operator stepped away (AFK)
  - REMOTE_ACTIVE  — operating via mobile/remote device
  - OVERNIGHT      — day closed, autonomous execution

Design rules (mirror substrate conventions):
- Additive only. Composes on top of station_presence.
- Best-effort. All public functions catch and log.
- Deterministic. No LLM calls.
- User-instance-specific: modes and profiles are per-operator.
- Continuity and escalation remain global/system-wide.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


_LOG_PREFIX = "[substrate.presence_runtime]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Presence Mode ─────────────────────────────────────────────────────────────


class PresenceMode(str, Enum):
    """First-class operator presence modes.

    ACTIVE_LOCAL  — at the primary workstation, fully available
    AWAY_LOCAL    — machine on but operator stepped away (AFK)
    REMOTE_ACTIVE — operating via mobile/remote device
    OVERNIGHT     — day closed, autonomous execution
    """

    ACTIVE_LOCAL = "active_local"
    AWAY_LOCAL = "away_local"
    REMOTE_ACTIVE = "remote_active"
    OVERNIGHT = "overnight"


# ─── Behavioral Influence Matrix ───────────────────────────────────────────────


@dataclass(frozen=True)
class PresenceBehavior:
    """Runtime behavioral modifiers for a presence mode.

    These are the concrete effects of each mode on system behavior.
    Kept minimal and enforceable — no giant matrix.
    """

    mode: PresenceMode
    allow_interruptions: bool
    prefer_local_routing: bool
    tts_eligible: bool
    suppress_non_critical: bool
    auto_execute_overnight: bool
    routing_hint: str  # "local" | "vps" | "auto"
    lifecycle_modifier: str  # how this mode modifies day lifecycle

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "allow_interruptions": self.allow_interruptions,
            "prefer_local_routing": self.prefer_local_routing,
            "tts_eligible": self.tts_eligible,
            "suppress_non_critical": self.suppress_non_critical,
            "auto_execute_overnight": self.auto_execute_overnight,
            "routing_hint": self.routing_hint,
            "lifecycle_modifier": self.lifecycle_modifier,
        }


PRESENCE_BEHAVIORS: dict[PresenceMode, PresenceBehavior] = {
    PresenceMode.ACTIVE_LOCAL: PresenceBehavior(
        mode=PresenceMode.ACTIVE_LOCAL,
        allow_interruptions=True,
        prefer_local_routing=True,
        tts_eligible=True,
        suppress_non_critical=False,
        auto_execute_overnight=False,
        routing_hint="local",
        lifecycle_modifier="full_capability",
    ),
    PresenceMode.AWAY_LOCAL: PresenceBehavior(
        mode=PresenceMode.AWAY_LOCAL,
        allow_interruptions=False,
        prefer_local_routing=False,
        tts_eligible=False,
        suppress_non_critical=True,
        auto_execute_overnight=False,
        routing_hint="vps",
        lifecycle_modifier="queue_for_return",
    ),
    PresenceMode.REMOTE_ACTIVE: PresenceBehavior(
        mode=PresenceMode.REMOTE_ACTIVE,
        allow_interruptions=True,
        prefer_local_routing=False,
        tts_eligible=False,
        suppress_non_critical=False,
        auto_execute_overnight=False,
        routing_hint="vps",
        lifecycle_modifier="remote_optimized",
    ),
    PresenceMode.OVERNIGHT: PresenceBehavior(
        mode=PresenceMode.OVERNIGHT,
        allow_interruptions=False,
        prefer_local_routing=False,
        tts_eligible=False,
        suppress_non_critical=True,
        auto_execute_overnight=True,
        routing_hint="vps",
        lifecycle_modifier="autonomous",
    ),
}


def get_presence_behavior(mode: PresenceMode) -> PresenceBehavior:
    """Get the behavioral modifiers for a presence mode."""
    return PRESENCE_BEHAVIORS[mode]


# ─── Work Profile ─────────────────────────────────────────────────────────────


class WorkProfile(str, Enum):
    """Active work profiles — user-instance-specific."""

    BUILDER = "builder"
    PRODUCT = "product"


@dataclass(frozen=True)
class ProfileBehavior:
    """Runtime modifiers for a work profile."""

    profile: WorkProfile
    default_workspace: str
    default_scene: str
    focus_areas: tuple[str, ...]
    routing_bias: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.value,
            "default_workspace": self.default_workspace,
            "default_scene": self.default_scene,
            "focus_areas": list(self.focus_areas),
            "routing_bias": self.routing_bias,
        }


PROFILE_BEHAVIORS: dict[WorkProfile, ProfileBehavior] = {
    WorkProfile.BUILDER: ProfileBehavior(
        profile=WorkProfile.BUILDER,
        default_workspace="builder",
        default_scene="builder_mode",
        focus_areas=("code", "infrastructure", "debugging", "testing"),
        routing_bias="local",
    ),
    WorkProfile.PRODUCT: ProfileBehavior(
        profile=WorkProfile.PRODUCT,
        default_workspace="product",
        default_scene="operator_mode",
        focus_areas=("outreach", "CRM", "analytics", "content", "strategy"),
        routing_bias="vps",
    ),
}


def get_profile_behavior(profile: WorkProfile) -> ProfileBehavior:
    """Get the behavioral modifiers for a work profile."""
    return PROFILE_BEHAVIORS[profile]


# ─── Composed Runtime State ──────────────────────────────────────────────────


@dataclass
class OperatorRuntimeState:
    """Composed runtime state: presence + profile + resolved behavior.

    The single object that day_workflows and bootstrap query to determine
    actual system behavior. User-instance-specific.
    """

    presence: PresenceMode = PresenceMode.REMOTE_ACTIVE
    profile: WorkProfile = WorkProfile.BUILDER
    resolved_at: str = field(default_factory=_utcnow)

    @property
    def behavior(self) -> PresenceBehavior:
        return get_presence_behavior(self.presence)

    @property
    def profile_behavior(self) -> ProfileBehavior:
        return get_profile_behavior(self.profile)

    @property
    def effective_routing(self) -> str:
        """Presence overrides profile when specific."""
        pb = self.behavior
        if pb.routing_hint != "auto":
            return pb.routing_hint
        return self.profile_behavior.routing_bias

    @property
    def effective_workspace(self) -> str:
        return self.profile_behavior.default_workspace

    @property
    def effective_scene(self) -> str:
        return self.profile_behavior.default_scene

    def to_dict(self) -> dict[str, Any]:
        return {
            "presence": self.presence.value,
            "profile": self.profile.value,
            "resolved_at": self.resolved_at,
            "behavior": self.behavior.to_dict(),
            "profile_behavior": self.profile_behavior.to_dict(),
            "effective_routing": self.effective_routing,
            "effective_workspace": self.effective_workspace,
            "effective_scene": self.effective_scene,
        }


# ─── Control API ──────────────────────────────────────────────────────────────


_PRESENCE_TO_STATION: dict[PresenceMode, str] = {
    PresenceMode.ACTIVE_LOCAL: "local",
    PresenceMode.AWAY_LOCAL: "away",
    PresenceMode.REMOTE_ACTIVE: "remote",
    PresenceMode.OVERNIGHT: "overnight",
}


def set_presence(
    mode: PresenceMode,
    *,
    profile: Optional[WorkProfile] = None,
) -> OperatorRuntimeState:
    """Set the operator presence mode and optionally the active profile.

    Updates both the new OperatorRuntimeState and the existing
    StationPresence for backward compatibility.
    """
    state = _get_or_create_state()
    state.presence = mode
    if profile is not None:
        state.profile = profile
    state.resolved_at = _utcnow()

    # Sync to existing StationPresence (best-effort)
    try:
        from umh.substrate.station_presence import (
            StationPresenceMode,
            set_presence_mode,
        )

        station_mode_value = _PRESENCE_TO_STATION.get(mode, "away")
        set_presence_mode(StationPresenceMode(station_mode_value))
    except Exception as exc:
        _log(f"station_presence sync failed: {exc}")

    _persist_state(state)
    _log(f"presence={mode.value} profile={state.profile.value}")
    return state


def set_profile(profile: WorkProfile) -> OperatorRuntimeState:
    """Set the active work profile without changing presence."""
    state = _get_or_create_state()
    state.profile = profile
    state.resolved_at = _utcnow()
    _persist_state(state)
    _log(f"profile={profile.value}")
    return state


def get_runtime() -> OperatorRuntimeState:
    """Get the current operator runtime state."""
    return _get_or_create_state()


# ─── Bootstrap Requirements ──────────────────────────────────────────────────


@dataclass
class BootstrapRequirements:
    """What the system needs for a given presence + profile combo.

    Separates user-facing from system-required actions.
    """

    # User-facing
    user_scene: str = ""
    user_apps: list[str] = field(default_factory=list)
    user_urls: list[str] = field(default_factory=list)
    user_tts: bool = False
    user_wake: bool = False

    # System-required
    system_session_target: str = "vps"
    system_check_node_health: bool = True
    system_load_continuity: bool = True
    system_start_event_spine: bool = True
    system_verify_archive: bool = True
    system_ensure_git_clean: bool = False
    system_ensure_crm_accessible: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_facing": {
                "scene": self.user_scene,
                "apps": list(self.user_apps),
                "urls": list(self.user_urls),
                "tts": self.user_tts,
                "wake": self.user_wake,
            },
            "system_required": {
                "session_target": self.system_session_target,
                "check_node_health": self.system_check_node_health,
                "load_continuity": self.system_load_continuity,
                "start_event_spine": self.system_start_event_spine,
                "verify_archive": self.system_verify_archive,
                "ensure_git_clean": self.system_ensure_git_clean,
                "ensure_crm_accessible": self.system_ensure_crm_accessible,
            },
        }


def resolve_bootstrap(
    state: Optional[OperatorRuntimeState] = None,
) -> BootstrapRequirements:
    """Resolve bootstrap requirements for presence + profile."""
    if state is None:
        state = get_runtime()

    behavior = state.behavior
    profile_beh = state.profile_behavior
    reqs = BootstrapRequirements()

    # User-facing: scene from profile
    reqs.user_scene = profile_beh.default_scene
    reqs.user_tts = behavior.tts_eligible
    reqs.user_wake = behavior.tts_eligible

    # User-facing: apps depend on profile + presence
    if state.profile == WorkProfile.BUILDER:
        reqs.user_apps = ["vscode", "terminal"]
        if behavior.prefer_local_routing:
            reqs.user_apps.append("github")
    elif state.profile == WorkProfile.PRODUCT:
        reqs.user_apps = ["discord", "chrome"]
        if behavior.allow_interruptions:
            reqs.user_apps.append("notion")

    # System-required: routing
    reqs.system_session_target = state.effective_routing

    # System-required: profile-specific
    if state.profile == WorkProfile.BUILDER:
        reqs.system_ensure_git_clean = True
    elif state.profile == WorkProfile.PRODUCT:
        reqs.system_ensure_crm_accessible = True

    # Overnight: minimal user-facing
    if state.presence == PresenceMode.OVERNIGHT:
        reqs.user_scene = "overnight"
        reqs.user_apps = []
        reqs.user_urls = []
        reqs.user_tts = False
        reqs.user_wake = False

    # Away: disable voice
    if state.presence == PresenceMode.AWAY_LOCAL:
        reqs.user_tts = False
        reqs.user_wake = False

    return reqs


# ─── Lifecycle Modifiers ─────────────────────────────────────────────────────


def get_lifecycle_modifiers(
    state: Optional[OperatorRuntimeState] = None,
) -> dict[str, Any]:
    """Get modifiers for open_day/close_day based on current state."""
    if state is None:
        state = get_runtime()

    behavior = state.behavior
    profile_beh = state.profile_behavior

    return {
        "presence_mode": state.presence.value,
        "work_profile": state.profile.value,
        "workspace": state.effective_workspace,
        "routing": state.effective_routing,
        "scene": state.effective_scene,
        "allow_interruptions": behavior.allow_interruptions,
        "suppress_non_critical": behavior.suppress_non_critical,
        "auto_execute_overnight": behavior.auto_execute_overnight,
        "lifecycle_modifier": behavior.lifecycle_modifier,
        "focus_areas": list(profile_beh.focus_areas),
    }


# ─── Continuity Integration ──────────────────────────────────────────────────


def presence_for_continuity() -> dict[str, Any]:
    """Compact presence/profile summary for continuity consumers."""
    state = get_runtime()
    behavior = state.behavior
    return {
        "presence_mode": state.presence.value,
        "work_profile": state.profile.value,
        "effective_routing": state.effective_routing,
        "effective_workspace": state.effective_workspace,
        "allow_interruptions": behavior.allow_interruptions,
        "tts_eligible": behavior.tts_eligible,
        "resolved_at": state.resolved_at,
    }


# ─── Persistence ─────────────────────────────────────────────────────────────

_STORAGE_KEY = "operator_runtime_state"
_state_cache: Optional[OperatorRuntimeState] = None


def _get_or_create_state() -> OperatorRuntimeState:
    global _state_cache
    if _state_cache is not None:
        return _state_cache

    try:
        from umh.substrate.storage import get_storage

        raw = get_storage().get(_STORAGE_KEY, default=None)
        if isinstance(raw, dict):
            try:
                presence = PresenceMode(raw.get("presence", "remote_active"))
            except ValueError:
                presence = PresenceMode.REMOTE_ACTIVE
            try:
                profile = WorkProfile(raw.get("profile", "builder"))
            except ValueError:
                profile = WorkProfile.BUILDER

            _state_cache = OperatorRuntimeState(
                presence=presence,
                profile=profile,
                resolved_at=raw.get("resolved_at", _utcnow()),
            )
            return _state_cache
    except Exception as exc:
        _log(f"state load failed: {exc}")

    _state_cache = OperatorRuntimeState()
    return _state_cache


def _persist_state(state: OperatorRuntimeState) -> None:
    global _state_cache
    _state_cache = state
    try:
        from umh.substrate.storage import get_storage

        get_storage().put(
            _STORAGE_KEY,
            {
                "presence": state.presence.value,
                "profile": state.profile.value,
                "resolved_at": state.resolved_at,
            },
        )
    except Exception as exc:
        _log(f"state persist failed: {exc}")


def reset_for_tests() -> None:
    """Test hook — reset cached state."""
    global _state_cache
    _state_cache = None


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "PresenceMode",
    "PresenceBehavior",
    "PRESENCE_BEHAVIORS",
    "get_presence_behavior",
    "WorkProfile",
    "ProfileBehavior",
    "PROFILE_BEHAVIORS",
    "get_profile_behavior",
    "OperatorRuntimeState",
    "set_presence",
    "set_profile",
    "get_runtime",
    "BootstrapRequirements",
    "resolve_bootstrap",
    "get_lifecycle_modifiers",
    "presence_for_continuity",
    "reset_for_tests",
]
