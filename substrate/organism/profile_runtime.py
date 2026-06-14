"""Profile Runtime — canonical authority for operator work identity and system modes.

Phase 11. Separates and coordinates two orthogonal axes:

  Profile Modes — operator work identity (Engineer, Founder, Artist, etc.)
  System Modes  — environmental/system states (Day, Night, AFK, Focus, etc.)

A user may have one profile mode active while multiple system modes run
concurrently. Profile mode defines work identity context. System modes
define environmental behavior.

This runtime plans and contextualizes. It does NOT execute work, launch
applications, or approve actions. It composes existing subsystems:
  - Presence Runtime (P8) — attention/interruptibility
  - Workstation Runtime (P10) — workspace planning
  - ProfileMode/LifecycleMode enums from substrate.workstation
  - ProfileBehavior from substrate.workstation.profile_behavior

Governance boundary: may classify, plan, recommend. Never execute.
Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _profile_data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "profile")


def _ensure_dirs() -> None:
    d = _profile_data_dir()
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(d, "timeline"), exist_ok=True)


# ── Canonical Enums ──────────────────────────────────────────────


class ProfileModeEnum(str, Enum):
    """Operator work identity profiles.

    Extends the substrate.workstation.profile_modes.ProfileMode enum
    with spec-required profiles while preserving all existing values.
    """

    ENGINEER = "engineer"
    FOUNDER = "founder"
    ARTIST = "artist"
    CONTENT = "content"
    RESEARCH = "research"
    ADMIN = "admin"
    MUSIC = "music"
    DESIGN = "design"
    FINANCE = "finance"
    LEARNING = "learning"
    COMMAND_CENTER = "command_center"


class SystemModeEnum(str, Enum):
    """Environmental/system behavior modes.

    Extends LifecycleMode with spec-required modes (SECURITY, FOCUS)
    while preserving all existing lifecycle values.
    """

    DAY = "day"
    NIGHT = "night"
    AFK = "afk"
    MAINTENANCE = "maintenance"
    SECURITY = "security"
    FOCUS = "focus"
    EMERGENCY = "emergency"
    OVERNIGHT = "overnight"
    IDLE = "idle"
    REMOTE_WORK = "remote_work"
    END_OF_WORKDAY = "end_of_workday"


class ActivationSource(str, Enum):
    """How a profile or system mode was activated."""

    MANUAL = "manual"
    COMMAND = "command"
    COCKPIT = "cockpit"
    INFERRED = "inferred"
    SCHEDULE = "schedule"
    RESTORED = "restored"


class ProfileEventType(str, Enum):
    """Timeline event types for profile/system mode transitions."""

    PROFILE_ACTIVATED = "profile_activated"
    PROFILE_DEACTIVATED = "profile_deactivated"
    SYSTEM_MODE_ACTIVATED = "system_mode_activated"
    SYSTEM_MODE_DEACTIVATED = "system_mode_deactivated"
    CONFLICT_DETECTED = "conflict_detected"
    MANUAL_OVERRIDE = "manual_override"
    ACTIVATION_PLAN_GENERATED = "activation_plan_generated"


class ConflictSeverity(str, Enum):
    """Severity of a detected profile/system mode conflict."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ── Data Models ──────────────────────────────────────────────────


@dataclass
class Profile:
    """A single operator work identity profile.

    Loaded from data-driven JSON. No hardcoded behavior.
    """

    profile_id: str = ""
    name: str = ""
    description: str = ""
    default_workspace_template: str = ""
    preferred_domains: list[str] = field(default_factory=list)
    preferred_agents: list[str] = field(default_factory=list)
    preferred_cockpit_panels: list[str] = field(default_factory=list)
    preferred_tools: list[str] = field(default_factory=list)
    interruption_preference: str = "normal"
    risk_tolerance: str = "medium"
    default_session_preference: str = ""
    domain_weights: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.profile_id:
            self.profile_id = f"prof-{uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "default_workspace_template": self.default_workspace_template,
            "preferred_domains": self.preferred_domains,
            "preferred_agents": self.preferred_agents,
            "preferred_cockpit_panels": self.preferred_cockpit_panels,
            "preferred_tools": self.preferred_tools,
            "interruption_preference": self.interruption_preference,
            "risk_tolerance": self.risk_tolerance,
            "default_session_preference": self.default_session_preference,
            "domain_weights": self.domain_weights,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Profile:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SystemMode:
    """A single system/environmental mode definition.

    Loaded from data-driven JSON.
    """

    mode_id: str = ""
    name: str = ""
    description: str = ""
    exclusivity_group: str = ""
    priority: int = 0
    effects: dict[str, Any] = field(default_factory=dict)
    allowed_concurrency: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.mode_id:
            self.mode_id = f"smode-{uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_id": self.mode_id,
            "name": self.name,
            "description": self.description,
            "exclusivity_group": self.exclusivity_group,
            "priority": self.priority,
            "effects": self.effects,
            "allowed_concurrency": self.allowed_concurrency,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SystemMode:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfileModeState:
    """State machine state for the active profile mode."""

    active_profile_mode: str = ""
    previous_profile_mode: str = ""
    profile_started_at: float = 0.0
    profile_last_changed_at: float = 0.0
    activation_source: str = ""
    confidence: float = 1.0
    manual_override: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_profile_mode": self.active_profile_mode,
            "previous_profile_mode": self.previous_profile_mode,
            "profile_started_at": self.profile_started_at,
            "profile_last_changed_at": self.profile_last_changed_at,
            "activation_source": self.activation_source,
            "confidence": self.confidence,
            "manual_override": self.manual_override,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProfileModeState:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfileModeTransition:
    """A single profile mode transition event."""

    transition_id: str = ""
    from_mode: str = ""
    to_mode: str = ""
    timestamp: float = 0.0
    source: str = ""
    confidence: float = 1.0
    manual_override: bool = False

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = f"ptrans-{uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_mode": self.from_mode,
            "to_mode": self.to_mode,
            "timestamp": self.timestamp,
            "source": self.source,
            "confidence": self.confidence,
            "manual_override": self.manual_override,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProfileModeTransition:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfilePreference:
    """Operator's preference settings for a profile mode."""

    profile_mode: str = ""
    workspace_template_override: str = ""
    panel_overrides: list[str] = field(default_factory=list)
    domain_weight_overrides: dict[str, float] = field(default_factory=dict)
    tool_overrides: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_mode": self.profile_mode,
            "workspace_template_override": self.workspace_template_override,
            "panel_overrides": self.panel_overrides,
            "domain_weight_overrides": self.domain_weight_overrides,
            "tool_overrides": self.tool_overrides,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProfilePreference:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfileContext:
    """Assembled context for the current profile + system mode state."""

    active_profile: str = ""
    active_system_modes: list[str] = field(default_factory=list)
    workspace_template: str = ""
    preferred_panels: list[str] = field(default_factory=list)
    preferred_domains: list[str] = field(default_factory=list)
    domain_weights: dict[str, float] = field(default_factory=dict)
    interruption_preference: str = "normal"
    risk_tolerance: str = "medium"
    effective_notification_policy: str = "all"
    operator_present: bool = False
    attention_state: str = "offline"
    assembled_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.assembled_at:
            self.assembled_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_profile": self.active_profile,
            "active_system_modes": self.active_system_modes,
            "workspace_template": self.workspace_template,
            "preferred_panels": self.preferred_panels,
            "preferred_domains": self.preferred_domains,
            "domain_weights": self.domain_weights,
            "interruption_preference": self.interruption_preference,
            "risk_tolerance": self.risk_tolerance,
            "effective_notification_policy": self.effective_notification_policy,
            "operator_present": self.operator_present,
            "attention_state": self.attention_state,
            "assembled_at": self.assembled_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProfileContext:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfileActivationPlan:
    """Plan generated when a profile mode changes. Planning only — no execution."""

    plan_id: str = ""
    target_profile: str = ""
    workspace_template_suggestion: str = ""
    session_preference: str = ""
    cockpit_panel_preference: list[str] = field(default_factory=list)
    recommended_active_domains: list[str] = field(default_factory=list)
    recommended_work_packet_filters: list[str] = field(default_factory=list)
    interruption_behavior: str = "normal"
    continuity_context_to_load: list[str] = field(default_factory=list)
    projection_context_to_load: list[str] = field(default_factory=list)
    status: str = "planned"
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.plan_id:
            self.plan_id = f"pplan-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "target_profile": self.target_profile,
            "workspace_template_suggestion": self.workspace_template_suggestion,
            "session_preference": self.session_preference,
            "cockpit_panel_preference": self.cockpit_panel_preference,
            "recommended_active_domains": self.recommended_active_domains,
            "recommended_work_packet_filters": self.recommended_work_packet_filters,
            "interruption_behavior": self.interruption_behavior,
            "continuity_context_to_load": self.continuity_context_to_load,
            "projection_context_to_load": self.projection_context_to_load,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProfileActivationPlan:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfileRuntimeSnapshot:
    """Complete snapshot of profile runtime state."""

    snapshot_id: str = ""
    captured_at: float = 0.0
    profile_state: dict[str, Any] = field(default_factory=dict)
    active_system_modes: list[str] = field(default_factory=list)
    latest_activation_plan: dict[str, Any] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            self.snapshot_id = f"prsnap-{uuid4().hex[:12]}"
        if not self.captured_at:
            self.captured_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "profile_state": self.profile_state,
            "active_system_modes": self.active_system_modes,
            "latest_activation_plan": self.latest_activation_plan,
            "conflicts": self.conflicts,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProfileRuntimeSnapshot:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfileConflict:
    """A detected conflict between profile and/or system modes."""

    conflict_id: str = ""
    detected_at: float = 0.0
    conflict_type: str = ""
    severity: str = "warning"
    description: str = ""
    involved_modes: list[str] = field(default_factory=list)
    resolution: str = ""
    auto_resolved: bool = False

    def __post_init__(self) -> None:
        if not self.conflict_id:
            self.conflict_id = f"pconf-{uuid4().hex[:12]}"
        if not self.detected_at:
            self.detected_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "detected_at": self.detected_at,
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "description": self.description,
            "involved_modes": self.involved_modes,
            "resolution": self.resolution,
            "auto_resolved": self.auto_resolved,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProfileConflict:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfileRecommendation:
    """A recommendation sourced from profile context."""

    recommendation_id: str = ""
    recommendation_type: str = ""
    title: str = ""
    description: str = ""
    source: str = ""
    priority: int = 50
    target_profile: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.recommendation_id:
            self.recommendation_id = f"prec-{uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "recommendation_type": self.recommendation_type,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "priority": self.priority,
            "target_profile": self.target_profile,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProfileRecommendation:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Profile Registry ─────────────────────────────────────────────


class ProfileRegistry:
    """Data-driven profile registry. Loads from JSON, seeds defaults on first run."""

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = data_dir or _profile_data_dir()
        self._profiles_path = os.path.join(self._data_dir, "profiles.json")
        self._profiles: dict[str, Profile] = {}
        _ensure_dirs()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._profiles_path):
            try:
                with open(self._profiles_path) as f:
                    data = json.load(f)
                for item in data.get("profiles", []):
                    p = Profile.from_dict(item)
                    self._profiles[p.name] = p
            except Exception as exc:
                logger.error("failed to load profiles: %s", exc)
                self._seed_defaults()
        else:
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        for p in _default_profiles():
            self._profiles[p.name] = p
        self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._profiles_path), exist_ok=True)
        with open(self._profiles_path, "w") as f:
            json.dump(
                {"profiles": [p.to_dict() for p in self._profiles.values()]},
                f,
                indent=2,
            )

    def get(self, name: str) -> Profile | None:
        return self._profiles.get(name)

    def all_profiles(self) -> list[Profile]:
        return list(self._profiles.values())

    def add(self, profile: Profile) -> Profile:
        self._profiles[profile.name] = profile
        self._save()
        return profile

    def remove(self, name: str) -> bool:
        if name in self._profiles:
            del self._profiles[name]
            self._save()
            return True
        return False


def _default_profiles() -> list[Profile]:
    """Seed profiles — aligned with spec requirements."""
    return [
        Profile(
            name="engineer",
            description="Software engineering, debugging, deployment, infrastructure",
            default_workspace_template="engineering",
            preferred_domains=["engineering", "infrastructure", "operator", "vision"],
            preferred_agents=["developer", "reviewer", "executor"],
            preferred_cockpit_panels=["commandcenter", "editor", "workspace", "runtime"],
            preferred_tools=["claude-code", "git", "docker", "ssh"],
            interruption_preference="low",
            risk_tolerance="medium",
            default_session_preference="focused",
            domain_weights={
                "engineering": 1.0,
                "infrastructure": 0.8,
                "operator": 0.7,
                "vision": 0.5,
                "content": 0.2,
                "music": 0.1,
            },
        ),
        Profile(
            name="founder",
            description="Strategic oversight, business decisions, portfolio management",
            default_workspace_template="business",
            preferred_domains=["business", "strategy", "portfolio", "analytics"],
            preferred_agents=["advisor", "ceo", "analyst"],
            preferred_cockpit_panels=["commandcenter", "portfolio", "analytics", "strategy"],
            preferred_tools=["cockpit", "analytics-dashboard"],
            interruption_preference="normal",
            risk_tolerance="high",
            default_session_preference="executive",
            domain_weights={
                "business": 1.0,
                "strategy": 0.9,
                "portfolio": 0.8,
                "analytics": 0.7,
                "engineering": 0.3,
                "content": 0.4,
            },
        ),
        Profile(
            name="artist",
            description="Music production, composition, creative expression",
            default_workspace_template="music",
            preferred_domains=["music", "creative", "content"],
            preferred_agents=["advisor"],
            preferred_cockpit_panels=["advisor"],
            preferred_tools=["daw", "midi-controller"],
            interruption_preference="none",
            risk_tolerance="low",
            default_session_preference="creative",
            domain_weights={
                "music": 1.0,
                "creative": 0.8,
                "content": 0.5,
                "engineering": 0.1,
            },
        ),
        Profile(
            name="content",
            description="Content creation, writing, editing, publishing",
            default_workspace_template="content",
            preferred_domains=["content", "marketing", "brand", "social"],
            preferred_agents=["advisor", "writer"],
            preferred_cockpit_panels=["advisor", "knowledge"],
            preferred_tools=["editor", "canva", "social-scheduler"],
            interruption_preference="low",
            risk_tolerance="low",
            default_session_preference="creative",
            domain_weights={
                "content": 1.0,
                "marketing": 0.8,
                "brand": 0.7,
                "social": 0.6,
                "engineering": 0.1,
            },
        ),
        Profile(
            name="research",
            description="Investigation, analysis, reading, learning",
            default_workspace_template="research",
            preferred_domains=["research", "knowledge", "analysis"],
            preferred_agents=["researcher", "advisor"],
            preferred_cockpit_panels=["knowledge", "commandcenter", "worldmodel"],
            preferred_tools=["browser", "notebook", "search"],
            interruption_preference="low",
            risk_tolerance="low",
            default_session_preference="focused",
            domain_weights={
                "research": 1.0,
                "knowledge": 0.8,
                "analysis": 0.7,
                "engineering": 0.3,
            },
        ),
        Profile(
            name="admin",
            description="System administration, maintenance, operations",
            default_workspace_template="admin",
            preferred_domains=["infrastructure", "operations", "maintenance"],
            preferred_agents=["executor", "monitor"],
            preferred_cockpit_panels=["infrastructure", "runtime", "organism"],
            preferred_tools=["ssh", "docker", "monitoring"],
            interruption_preference="normal",
            risk_tolerance="medium",
            default_session_preference="operational",
            domain_weights={
                "infrastructure": 1.0,
                "operations": 0.9,
                "maintenance": 0.8,
                "engineering": 0.5,
            },
        ),
    ]


# ── System Mode Registry ─────────────────────────────────────────


class SystemModeRegistry:
    """Data-driven system mode registry. Loads from JSON, seeds defaults on first run."""

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = data_dir or _profile_data_dir()
        self._modes_path = os.path.join(self._data_dir, "system_modes.json")
        self._modes: dict[str, SystemMode] = {}
        _ensure_dirs()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._modes_path):
            try:
                with open(self._modes_path) as f:
                    data = json.load(f)
                for item in data.get("system_modes", []):
                    m = SystemMode.from_dict(item)
                    self._modes[m.name] = m
            except Exception as exc:
                logger.error("failed to load system modes: %s", exc)
                self._seed_defaults()
        else:
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        for m in _default_system_modes():
            self._modes[m.name] = m
        self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._modes_path), exist_ok=True)
        with open(self._modes_path, "w") as f:
            json.dump(
                {"system_modes": [m.to_dict() for m in self._modes.values()]},
                f,
                indent=2,
            )

    def get(self, name: str) -> SystemMode | None:
        return self._modes.get(name)

    def all_modes(self) -> list[SystemMode]:
        return list(self._modes.values())

    def get_exclusivity_group(self, name: str) -> str:
        m = self._modes.get(name)
        return m.exclusivity_group if m else ""


def _default_system_modes() -> list[SystemMode]:
    """Seed system modes — environmental/system states."""
    return [
        SystemMode(
            name="day",
            description="Normal daytime operation, full capability",
            exclusivity_group="time_of_day",
            priority=50,
            effects={"risk_ceiling": "HIGH", "notification_policy": "all"},
            allowed_concurrency=["maintenance", "security", "focus"],
        ),
        SystemMode(
            name="night",
            description="Nighttime operation, reduced risk ceiling, suppress noncritical",
            exclusivity_group="time_of_day",
            priority=50,
            effects={"risk_ceiling": "LOW", "notification_policy": "critical_only"},
            allowed_concurrency=["maintenance", "security"],
        ),
        SystemMode(
            name="afk",
            description="Operator away from keyboard, preserve state",
            exclusivity_group="",
            priority=40,
            effects={"notification_policy": "critical_only", "pause_interactive": True},
            allowed_concurrency=["day", "night", "maintenance"],
        ),
        SystemMode(
            name="maintenance",
            description="System maintenance window, restrict user-facing changes",
            exclusivity_group="",
            priority=60,
            effects={"risk_ceiling": "MEDIUM", "restrict_deploys": True},
            allowed_concurrency=["day", "night", "security"],
        ),
        SystemMode(
            name="security",
            description="Security-hardened mode, elevated monitoring",
            exclusivity_group="",
            priority=80,
            effects={"elevated_monitoring": True, "restrict_external": True},
            allowed_concurrency=["day", "night", "maintenance", "focus"],
        ),
        SystemMode(
            name="focus",
            description="Deep focus, suppress all non-critical interruptions",
            exclusivity_group="",
            priority=70,
            effects={"notification_policy": "critical_only", "suppress_recommendations": True},
            allowed_concurrency=["day", "night", "security"],
        ),
        SystemMode(
            name="emergency",
            description="Emergency degraded mode, critical-path-only execution",
            exclusivity_group="",
            priority=100,
            effects={
                "risk_ceiling": "CRITICAL",
                "notification_policy": "all",
                "critical_only": True,
            },
            allowed_concurrency=["security"],
        ),
    ]


# ── Exclusivity Rules ─────────────────────────────────────────────

_EXCLUSIVE_PAIRS: list[tuple[str, str]] = [
    ("day", "night"),
]

_UNSAFE_COMBINATIONS: list[tuple[str, str, str]] = [
    ("emergency", "focus", "Emergency overrides Focus — emergency requires full alertness"),
]


# ── Profile Mode State Machine ────────────────────────────────────


class ProfileModeStateMachine:
    """Deterministic state machine for the active profile mode.

    Only one profile mode is active at a time. Manual override always wins.
    """

    def __init__(self) -> None:
        self._state = ProfileModeState()
        self._transitions: list[ProfileModeTransition] = []

    @property
    def state(self) -> ProfileModeState:
        return self._state

    @property
    def transitions(self) -> list[ProfileModeTransition]:
        return list(self._transitions)

    def activate(
        self,
        profile_mode: str,
        source: str = "manual",
        confidence: float = 1.0,
        manual_override: bool = False,
    ) -> ProfileModeTransition:
        now = time.time()
        old_mode = self._state.active_profile_mode

        if old_mode and not manual_override and self._state.manual_override:
            if source != "manual":
                raise ValueError(
                    f"Cannot override manual profile '{old_mode}' with non-manual source '{source}'"
                )

        transition = ProfileModeTransition(
            from_mode=old_mode,
            to_mode=profile_mode,
            source=source,
            confidence=confidence,
            manual_override=manual_override,
        )

        self._state = ProfileModeState(
            active_profile_mode=profile_mode,
            previous_profile_mode=old_mode,
            profile_started_at=now,
            profile_last_changed_at=now,
            activation_source=source,
            confidence=confidence,
            manual_override=manual_override or source == "manual",
        )

        self._transitions.append(transition)
        return transition

    def deactivate(self) -> ProfileModeTransition | None:
        if not self._state.active_profile_mode:
            return None

        transition = ProfileModeTransition(
            from_mode=self._state.active_profile_mode,
            to_mode="",
            source="manual",
            confidence=1.0,
        )

        self._state = ProfileModeState(
            previous_profile_mode=self._state.active_profile_mode,
            profile_last_changed_at=time.time(),
        )

        self._transitions.append(transition)
        return transition

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self._state.to_dict(),
            "transition_count": len(self._transitions),
            "recent_transitions": [t.to_dict() for t in self._transitions[-10:]],
        }


# ── System Mode State Machine ─────────────────────────────────────


class SystemModeStateMachine:
    """Manages multiple concurrent system modes with exclusivity enforcement."""

    def __init__(self, registry: SystemModeRegistry) -> None:
        self._registry = registry
        self._active: dict[str, dict[str, Any]] = {}

    @property
    def active_modes(self) -> list[str]:
        return list(self._active.keys())

    def activate(
        self,
        mode_name: str,
        source: str = "manual",
    ) -> tuple[bool, list[str]]:
        """Activate a system mode. Returns (success, deactivated_modes)."""
        mode_def = self._registry.get(mode_name)
        if not mode_def:
            return False, []

        deactivated: list[str] = []

        if mode_def.exclusivity_group:
            for active_name in list(self._active.keys()):
                active_def = self._registry.get(active_name)
                if (
                    active_def
                    and active_def.exclusivity_group == mode_def.exclusivity_group
                    and active_name != mode_name
                ):
                    del self._active[active_name]
                    deactivated.append(active_name)

        self._active[mode_name] = {
            "activated_at": time.time(),
            "source": source,
        }

        return True, deactivated

    def deactivate(self, mode_name: str) -> bool:
        if mode_name in self._active:
            del self._active[mode_name]
            return True
        return False

    def is_active(self, mode_name: str) -> bool:
        return mode_name in self._active

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_modes": self.active_modes,
            "details": {name: info for name, info in self._active.items()},
        }


# ── Conflict Detector ──────────────────────────────────────────────


class ConflictDetector:
    """Detects invalid combinations of profile and system modes."""

    def __init__(self, registry: SystemModeRegistry) -> None:
        self._registry = registry

    def detect(
        self,
        active_profile: str,
        active_system_modes: list[str],
    ) -> list[ProfileConflict]:
        conflicts: list[ProfileConflict] = []

        for m1, m2 in _EXCLUSIVE_PAIRS:
            if m1 in active_system_modes and m2 in active_system_modes:
                conflicts.append(
                    ProfileConflict(
                        conflict_type="exclusive_violation",
                        severity=ConflictSeverity.ERROR.value,
                        description=f"{m1} and {m2} are mutually exclusive",
                        involved_modes=[m1, m2],
                    )
                )

        for m1, m2, desc in _UNSAFE_COMBINATIONS:
            if m1 in active_system_modes and m2 in active_system_modes:
                conflicts.append(
                    ProfileConflict(
                        conflict_type="unsafe_combination",
                        severity=ConflictSeverity.WARNING.value,
                        description=desc,
                        involved_modes=[m1, m2],
                    )
                )

        if "security" in active_system_modes:
            high_risk_profiles = ["admin"]
            if active_profile in high_risk_profiles:
                conflicts.append(
                    ProfileConflict(
                        conflict_type="risk_escalation",
                        severity=ConflictSeverity.WARNING.value,
                        description=(
                            f"Security mode active during high-risk profile "
                            f"'{active_profile}' — elevated monitoring required"
                        ),
                        involved_modes=["security", active_profile],
                    )
                )

        return conflicts


# ── Profile Activation Planner ─────────────────────────────────────


class ProfileActivationPlanner:
    """Generates a ProfileActivationPlan when profile mode changes.

    Composes context from the profile registry and existing subsystems
    to build a workspace/context preparation plan. Planning only.
    """

    def __init__(self, registry: ProfileRegistry) -> None:
        self._registry = registry

    def plan(
        self,
        target_profile: str,
        active_system_modes: list[str] | None = None,
    ) -> ProfileActivationPlan:
        profile = self._registry.get(target_profile)
        if not profile:
            return ProfileActivationPlan(
                target_profile=target_profile,
                status="error",
            )

        interruption = profile.interruption_preference
        if active_system_modes:
            if "focus" in active_system_modes:
                interruption = "none"
            elif "night" in active_system_modes:
                interruption = "critical_only"

        continuity_sources: list[str] = []
        projection_sources: list[str] = []
        try:
            from substrate.organism.continuity_runtime import get_continuity_runtime

            rt = get_continuity_runtime()
            state = rt.get_state()
            if state.get("objectives"):
                continuity_sources.append("active_objectives")
            if state.get("loops"):
                continuity_sources.append("active_loops")
        except Exception:
            logger.debug("continuity runtime unavailable for activation plan")

        try:
            from substrate.organism.projection_engine import get_projection_engine

            pe = get_projection_engine()
            proj_state = pe.get_state()
            if proj_state.get("domains"):
                for domain in profile.preferred_domains[:3]:
                    projection_sources.append(f"projection:{domain}")
        except Exception:
            logger.debug("projection engine unavailable for activation plan")

        return ProfileActivationPlan(
            target_profile=target_profile,
            workspace_template_suggestion=profile.default_workspace_template,
            session_preference=profile.default_session_preference,
            cockpit_panel_preference=list(profile.preferred_cockpit_panels),
            recommended_active_domains=list(profile.preferred_domains),
            recommended_work_packet_filters=list(profile.preferred_domains[:3]),
            interruption_behavior=interruption,
            continuity_context_to_load=continuity_sources,
            projection_context_to_load=projection_sources,
            status="planned",
        )


# ── Profile Timeline ─────────────────────────────────────────────


class ProfileTimeline:
    """Chronological timeline of profile and system mode events."""

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = data_dir or _profile_data_dir()
        self._timeline_path = os.path.join(self._data_dir, "timeline", "events.jsonl")
        _ensure_dirs()

    def emit(
        self,
        event_type: str,
        summary: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": f"pevt-{uuid4().hex[:12]}",
            "event_type": event_type,
            "timestamp": time.time(),
            "summary": summary,
            "details": details or {},
        }
        try:
            os.makedirs(os.path.dirname(self._timeline_path), exist_ok=True)
            with open(self._timeline_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as exc:
            logger.error("timeline write failed: %s", exc)
        return event

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not os.path.exists(self._timeline_path):
            return []
        events: list[dict[str, Any]] = []
        try:
            with open(self._timeline_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.error("timeline read failed: %s", exc)
        return events[-limit:]


# ── Profile Context Assembler ──────────────────────────────────────


class ProfileContextAssembler:
    """Assembles unified profile context from current state + subsystems.

    Pulls from Presence Runtime (P8) for attention/interruptibility.
    Pulls from the profile registry for domain weights and preferences.
    Does NOT duplicate any subsystem logic — only reads.
    """

    def __init__(self, registry: ProfileRegistry) -> None:
        self._registry = registry

    def assemble(
        self,
        active_profile: str,
        active_system_modes: list[str],
    ) -> ProfileContext:
        profile = self._registry.get(active_profile)

        ctx = ProfileContext(
            active_profile=active_profile,
            active_system_modes=list(active_system_modes),
        )

        if profile:
            ctx.workspace_template = profile.default_workspace_template
            ctx.preferred_panels = list(profile.preferred_cockpit_panels)
            ctx.preferred_domains = list(profile.preferred_domains)
            ctx.domain_weights = dict(profile.domain_weights)
            ctx.interruption_preference = profile.interruption_preference
            ctx.risk_tolerance = profile.risk_tolerance

        self._apply_presence(ctx)
        self._apply_system_mode_effects(ctx, active_system_modes)

        return ctx

    def _apply_presence(self, ctx: ProfileContext) -> None:
        try:
            from substrate.organism.presence_runtime import get_presence_runtime

            rt = get_presence_runtime()
            snapshot = rt.capture_snapshot()
            ctx.operator_present = snapshot.operator_present
            ctx.attention_state = snapshot.attention_state
        except Exception:
            logger.debug("presence runtime unavailable for profile context")

    def _apply_system_mode_effects(
        self,
        ctx: ProfileContext,
        active_modes: list[str],
    ) -> None:
        if "focus" in active_modes:
            ctx.interruption_preference = "none"
            ctx.effective_notification_policy = "critical_only"
        elif "night" in active_modes:
            ctx.effective_notification_policy = "critical_only"
        elif "emergency" in active_modes:
            ctx.effective_notification_policy = "all"
            ctx.risk_tolerance = "critical"


# ── Profile Runtime ──────────────────────────────────────────────


class ProfileRuntime:
    """Canonical authority for operator work identity and system modes.

    Orchestrates:
      - ProfileModeStateMachine — single active profile mode
      - SystemModeStateMachine — concurrent system modes
      - ConflictDetector — invalid combination detection
      - ProfileActivationPlanner — workspace/context plans
      - ProfileTimeline — chronological event recording
      - ProfileContextAssembler — unified context assembly

    Never executes work. Never launches applications. Never approves actions.
    """

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = data_dir or _profile_data_dir()
        self._profile_registry = ProfileRegistry(self._data_dir)
        self._system_mode_registry = SystemModeRegistry(self._data_dir)
        self._profile_sm = ProfileModeStateMachine()
        self._system_sm = SystemModeStateMachine(self._system_mode_registry)
        self._conflict_detector = ConflictDetector(self._system_mode_registry)
        self._planner = ProfileActivationPlanner(self._profile_registry)
        self._timeline = ProfileTimeline(self._data_dir)
        self._context_assembler = ProfileContextAssembler(self._profile_registry)
        self._latest_plan: ProfileActivationPlan | None = None
        self._state_path = os.path.join(self._data_dir, "runtime_state.json")
        _ensure_dirs()
        self._load_state()

    # ── Profile Mode Operations ──────────────────────────────────

    def activate_profile(
        self,
        profile_mode: str,
        source: str = "manual",
        confidence: float = 1.0,
        manual_override: bool = False,
    ) -> dict[str, Any]:
        """Activate a profile mode. Returns transition + activation plan."""
        profile = self._profile_registry.get(profile_mode)
        if not profile:
            return {"success": False, "error": f"Unknown profile: {profile_mode}"}

        try:
            transition = self._profile_sm.activate(
                profile_mode,
                source,
                confidence,
                manual_override or source == "manual",
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

        plan = self._planner.plan(
            profile_mode,
            self._system_sm.active_modes,
        )
        self._latest_plan = plan

        self._timeline.emit(
            ProfileEventType.PROFILE_ACTIVATED.value,
            f"Profile activated: {profile_mode}",
            {
                "profile": profile_mode,
                "source": source,
                "previous": transition.from_mode,
                "confidence": confidence,
                "manual_override": transition.manual_override,
            },
        )

        if transition.manual_override:
            self._timeline.emit(
                ProfileEventType.MANUAL_OVERRIDE.value,
                f"Manual override applied for {profile_mode}",
                {"profile": profile_mode, "source": source},
            )

        self._timeline.emit(
            ProfileEventType.ACTIVATION_PLAN_GENERATED.value,
            f"Activation plan generated for {profile_mode}",
            {"plan_id": plan.plan_id, "profile": profile_mode},
        )

        self._notify_presence(profile_mode)
        conflicts = self.detect_conflicts()
        self._save_state()

        return {
            "success": True,
            "transition": transition.to_dict(),
            "activation_plan": plan.to_dict(),
            "conflicts": [c.to_dict() for c in conflicts],
        }

    def deactivate_profile(self) -> dict[str, Any]:
        """Deactivate the current profile mode."""
        transition = self._profile_sm.deactivate()
        if not transition:
            return {"success": False, "error": "No active profile to deactivate"}

        self._timeline.emit(
            ProfileEventType.PROFILE_DEACTIVATED.value,
            f"Profile deactivated: {transition.from_mode}",
            {"profile": transition.from_mode},
        )

        self._notify_presence("")
        self._save_state()

        return {"success": True, "transition": transition.to_dict()}

    # ── System Mode Operations ───────────────────────────────────

    def activate_system_mode(
        self,
        mode_name: str,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Activate a system mode. Returns success + any deactivated exclusive modes."""
        success, deactivated = self._system_sm.activate(mode_name, source)
        if not success:
            return {"success": False, "error": f"Unknown system mode: {mode_name}"}

        self._timeline.emit(
            ProfileEventType.SYSTEM_MODE_ACTIVATED.value,
            f"System mode activated: {mode_name}",
            {"mode": mode_name, "source": source, "deactivated": deactivated},
        )

        for d in deactivated:
            self._timeline.emit(
                ProfileEventType.SYSTEM_MODE_DEACTIVATED.value,
                f"System mode deactivated (exclusive): {d}",
                {"mode": d, "reason": "exclusivity_replacement"},
            )

        conflicts = self.detect_conflicts()
        if conflicts:
            for c in conflicts:
                self._timeline.emit(
                    ProfileEventType.CONFLICT_DETECTED.value,
                    c.description,
                    c.to_dict(),
                )

        self._save_state()

        return {
            "success": True,
            "mode": mode_name,
            "deactivated_exclusive": deactivated,
            "conflicts": [c.to_dict() for c in conflicts],
        }

    def deactivate_system_mode(self, mode_name: str) -> dict[str, Any]:
        """Deactivate a system mode."""
        success = self._system_sm.deactivate(mode_name)
        if not success:
            return {"success": False, "error": f"System mode not active: {mode_name}"}

        self._timeline.emit(
            ProfileEventType.SYSTEM_MODE_DEACTIVATED.value,
            f"System mode deactivated: {mode_name}",
            {"mode": mode_name},
        )

        self._save_state()
        return {"success": True, "mode": mode_name}

    # ── Queries ──────────────────────────────────────────────────

    def get_active_profile(self) -> str:
        return self._profile_sm.state.active_profile_mode

    def get_active_system_modes(self) -> list[str]:
        return self._system_sm.active_modes

    def get_profiles(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._profile_registry.all_profiles()]

    def get_system_modes(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._system_mode_registry.all_modes()]

    def get_activation_plan(self) -> dict[str, Any]:
        if self._latest_plan:
            return self._latest_plan.to_dict()
        return {}

    def detect_conflicts(self) -> list[ProfileConflict]:
        return self._conflict_detector.detect(
            self._profile_sm.state.active_profile_mode,
            self._system_sm.active_modes,
        )

    def get_timeline(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._timeline.get_recent(limit)

    def get_context(self) -> ProfileContext:
        return self._context_assembler.assemble(
            self._profile_sm.state.active_profile_mode,
            self._system_sm.active_modes,
        )

    def get_domain_weights(self) -> dict[str, float]:
        """Get domain weights for the active profile — consumed by tick/gap/projection."""
        ctx = self.get_context()
        return ctx.domain_weights

    def get_state(self) -> dict[str, Any]:
        ctx = self.get_context()
        conflicts = self.detect_conflicts()
        return {
            "profile_state": self._profile_sm.to_dict(),
            "system_modes": self._system_sm.to_dict(),
            "context": ctx.to_dict(),
            "conflicts": [c.to_dict() for c in conflicts],
            "latest_plan": self._latest_plan.to_dict() if self._latest_plan else {},
        }

    def capture_snapshot(self) -> ProfileRuntimeSnapshot:
        ctx = self.get_context()
        conflicts = self.detect_conflicts()
        return ProfileRuntimeSnapshot(
            profile_state=self._profile_sm.state.to_dict(),
            active_system_modes=list(self._system_sm.active_modes),
            latest_activation_plan=(self._latest_plan.to_dict() if self._latest_plan else {}),
            conflicts=[c.to_dict() for c in conflicts],
            context=ctx.to_dict(),
        )

    # ── Integration Helpers ──────────────────────────────────────

    def _notify_presence(self, profile_mode: str) -> None:
        """Notify Presence Runtime of profile change. Does NOT duplicate attention logic."""
        try:
            from substrate.organism.presence_runtime import get_presence_runtime

            rt = get_presence_runtime()
            rt.change_profile(profile_mode)
        except Exception:
            logger.debug("presence runtime notification skipped")

    # ── Persistence ──────────────────────────────────────────────

    def _save_state(self) -> None:
        state = {
            "active_profile": self._profile_sm.state.active_profile_mode,
            "profile_state": self._profile_sm.state.to_dict(),
            "active_system_modes": self._system_sm.active_modes,
            "system_mode_details": self._system_sm.to_dict().get("details", {}),
            "saved_at": time.time(),
        }
        try:
            os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
            with open(self._state_path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            logger.error("profile runtime state save failed: %s", exc)

    def _load_state(self) -> None:
        if not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path) as f:
                state = json.load(f)

            profile = state.get("active_profile", "")
            if profile and self._profile_registry.get(profile):
                ps = state.get("profile_state", {})
                self._profile_sm._state = ProfileModeState.from_dict(ps)

            for mode_name in state.get("active_system_modes", []):
                if self._system_mode_registry.get(mode_name):
                    details = state.get("system_mode_details", {}).get(mode_name, {})
                    self._system_sm._active[mode_name] = details or {
                        "activated_at": time.time(),
                        "source": "restored",
                    }

        except Exception as exc:
            logger.error("profile runtime state load failed: %s", exc)


# ── Singleton ────────────────────────────────────────────────────

_runtime: ProfileRuntime | None = None


def get_profile_runtime() -> ProfileRuntime:
    global _runtime
    if _runtime is None:
        _runtime = ProfileRuntime()
    return _runtime


def reset_profile_runtime() -> None:
    global _runtime
    _runtime = None
