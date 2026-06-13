"""Presence Runtime — operator presence awareness for UMH.

Phase 8. Makes the operator a first-class entity in UMH. The system
understands where the operator is, which device and session are active,
what profile mode is engaged, whether to interrupt, and what attention
state applies.

This is NOT voice, NOT meetings, NOT workstation preparation.
This is presence awareness: the foundational layer that all future
interaction runtimes (voice, workstation, meeting, Jarvis) build on.

Deterministic-first: all presence logic uses state comparison, time
thresholds, and classification rules. No LLM dependency in core path.

Composes existing primitives:
  - DevicePresenceRegistry / DeviceSession (workstation/device_presence)
  - ProfileMode (workstation/profile_modes)
  - AttentionModel / AttentionState (continuity_runtime)
  - TimelineEngine / TimelineEventType (continuity_runtime)
  - ContinuityRuntime (continuity_runtime) — snapshot integration
  - StrategicTickLoop (strategic_tick_loop) — recommendation filtering
  - ProjectionEngine (projection_engine) — risk/opportunity filtering
  - device_registry.json (infra/) — canonical device definitions

Governance boundary: may observe, classify, recommend.
May NOT execute, approve, modify goals, or override governance.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _presence_data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "presence")


def _ensure_dirs() -> None:
    base = _presence_data_dir()
    for sub in ("snapshots", "timeline", "sessions"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)


# ── Enums ──────────────────────────────────────────────────────────────


class PresenceAttentionState(str, Enum):
    """Fine-grained attention states for presence-aware logic."""
    FOCUSED = "focused"
    AVAILABLE = "available"
    AWAY = "away"
    OFFLINE = "offline"
    SLEEPING = "sleeping"

    @property
    def is_present(self) -> bool:
        return self in (PresenceAttentionState.FOCUSED, PresenceAttentionState.AVAILABLE)

    @property
    def is_absent(self) -> bool:
        return self in (
            PresenceAttentionState.AWAY,
            PresenceAttentionState.OFFLINE,
            PresenceAttentionState.SLEEPING,
        )


class InterruptionLevel(str, Enum):
    """What class of notification should be surfaced."""
    CRITICAL_ONLY = "critical_only"
    NORMAL = "normal"
    QUEUE = "queue"
    DEFER = "defer"


class PresenceEventType(str, Enum):
    """Canonical presence event types."""
    OPERATOR_PRESENT = "operator_present"
    OPERATOR_ABSENT = "operator_absent"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    PROFILE_CHANGED = "profile_changed"
    ATTENTION_CHANGED = "attention_changed"
    DEVICE_CHANGED = "device_changed"
    DEVICE_ONLINE = "device_online"
    DEVICE_OFFLINE = "device_offline"
    INTERRUPTION_BUDGET_CHANGED = "interruption_budget_changed"


class InteractionSurface(str, Enum):
    """Where the operator is currently interacting."""
    COCKPIT_BROWSER = "cockpit_browser"
    TERMINAL_SSH = "terminal_ssh"
    MOBILE_APP = "mobile_app"
    TABLET_BROWSER = "tablet_browser"
    ELECTRON_APP = "electron_app"
    VOICE_SESSION = "voice_session"
    MEETING_SESSION = "meeting_session"
    NONE = "none"


# ── Data Models ────────────────────────────────────────────────────────


@dataclass
class DeviceInfo:
    """Enriched device record combining registry + live presence."""

    device_id: str = ""
    tailscale_name: str = ""
    device_type: str = ""
    display_name: str = ""
    os_type: str = ""
    role: str = ""
    online: bool = False
    active: bool = False
    last_seen: float = 0.0
    session_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "tailscale_name": self.tailscale_name,
            "device_type": self.device_type,
            "display_name": self.display_name,
            "os": self.os_type,
            "role": self.role,
            "online": self.online,
            "active": self.active,
            "last_seen": self.last_seen,
            "session_count": self.session_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceInfo:
        mapped = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        if "os" in data and "os_type" not in data:
            mapped["os_type"] = data["os"]
        return cls(**mapped)


@dataclass
class SessionInfo:
    """First-class session model with host, profile, and status tracking."""

    session_id: str = ""
    host: str = ""
    device_id: str = ""
    profile_mode: str = ""
    status: str = "active"
    started_at: float = 0.0
    last_activity: float = 0.0
    client_type: str = ""
    control_surface: str = ""
    interaction_surface: str = "none"

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = f"ses-{uuid4().hex[:12]}"
        if not self.started_at:
            self.started_at = time.time()
        if not self.last_activity:
            self.last_activity = self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "host": self.host,
            "device_id": self.device_id,
            "profile_mode": self.profile_mode,
            "status": self.status,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "client_type": self.client_type,
            "control_surface": self.control_surface,
            "interaction_surface": self.interaction_surface,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionInfo:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PresenceSnapshot:
    """Canonical presence snapshot — complete operator location awareness."""

    snapshot_id: str = ""
    captured_at: float = 0.0
    operator_present: bool = False
    active_device: str = ""
    active_host: str = ""
    active_session: str = ""
    active_profile_mode: str = ""
    active_system_modes: list[str] = field(default_factory=list)
    attention_state: str = "offline"
    last_activity_timestamp: float = 0.0
    interaction_surface: str = "none"
    interruption_budget: str = "defer"
    devices: list[dict[str, Any]] = field(default_factory=list)
    sessions: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            self.snapshot_id = f"psnap-{uuid4().hex[:12]}"
        if not self.captured_at:
            self.captured_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "operator_present": self.operator_present,
            "active_device": self.active_device,
            "active_host": self.active_host,
            "active_session": self.active_session,
            "active_profile_mode": self.active_profile_mode,
            "active_system_modes": self.active_system_modes,
            "attention_state": self.attention_state,
            "last_activity_timestamp": self.last_activity_timestamp,
            "interaction_surface": self.interaction_surface,
            "interruption_budget": self.interruption_budget,
            "devices": self.devices,
            "sessions": self.sessions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresenceSnapshot:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PresenceEvent:
    """A single presence event in the timeline."""

    event_id: str = ""
    event_type: str = ""
    timestamp: float = 0.0
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = f"pevt-{uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresenceEvent:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ── Device Registry ───────────────────────────────────────────────────


class DeviceRegistry:
    """Registry of operator surfaces.

    Loads static device definitions from infra/device_registry.json and
    merges with live session presence from DevicePresenceRegistry.
    """

    def __init__(self) -> None:
        self._static_devices: list[dict[str, Any]] = []
        self._load_static()

    def _load_static(self) -> None:
        path = os.path.join(_repo_root(), "infra", "device_registry.json")
        try:
            with open(path) as f:
                self._static_devices = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("presence: device_registry.json load failed: %s", e)
            self._static_devices = []

    def get_all_devices(self) -> list[DeviceInfo]:
        live_sessions = self._get_live_sessions()

        devices = []
        for dev in self._static_devices:
            device_id = dev.get("id", "")
            matching = [s for s in live_sessions if s.device_id == device_id]
            active_sessions = [s for s in matching if s.status == "active"]

            last_seen = 0.0
            for s in matching:
                if s.last_seen:
                    try:
                        from datetime import datetime, timezone
                        dt = datetime.fromisoformat(s.last_seen.replace("Z", "+00:00"))
                        ts = dt.timestamp()
                        if ts > last_seen:
                            last_seen = ts
                    except Exception:
                        pass

            devices.append(DeviceInfo(
                device_id=device_id,
                tailscale_name=dev.get("tailscale_name", ""),
                device_type=dev.get("device_type", ""),
                display_name=dev.get("display_name", ""),
                os_type=dev.get("os", ""),
                role=dev.get("role", ""),
                online=len(active_sessions) > 0,
                active=len(active_sessions) > 0,
                last_seen=last_seen,
                session_count=len(active_sessions),
            ))

        return devices

    def get_device(self, device_id: str) -> DeviceInfo | None:
        for d in self.get_all_devices():
            if d.device_id == device_id:
                return d
        return None

    def get_online_devices(self) -> list[DeviceInfo]:
        return [d for d in self.get_all_devices() if d.online]

    def _get_live_sessions(self) -> list:
        try:
            from substrate.workstation.device_presence import get_registry
            registry = get_registry()
            return registry.get_active_sessions()
        except Exception:
            return []


# ── Session Registry ──────────────────────────────────────────────────


class SessionRegistry:
    """First-class session registry supporting multiple concurrent sessions.

    Wraps DevicePresenceRegistry sessions with higher-level semantics:
    profile modes, interaction surfaces, and proper lifecycle tracking.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionInfo] = {}
        self._session_history: list[dict[str, Any]] = []
        self._max_history = 100

    def register_session(
        self,
        session_id: str,
        host: str = "",
        device_id: str = "",
        profile_mode: str = "",
        client_type: str = "",
        control_surface: str = "",
        interaction_surface: str = "none",
    ) -> SessionInfo:
        session = SessionInfo(
            session_id=session_id,
            host=host,
            device_id=device_id,
            profile_mode=profile_mode,
            status="active",
            client_type=client_type,
            control_surface=control_surface,
            interaction_surface=interaction_surface,
        )
        self._sessions[session_id] = session
        logger.debug("presence: session registered: %s on %s", session_id, device_id)
        return session

    def end_session(self, session_id: str) -> SessionInfo | None:
        session = self._sessions.get(session_id)
        if session:
            session.status = "ended"
            session.last_activity = time.time()
            self._session_history.append(session.to_dict())
            if len(self._session_history) > self._max_history:
                self._session_history = self._session_history[-self._max_history:]
            del self._sessions[session_id]
            logger.debug("presence: session ended: %s", session_id)
        return session

    def heartbeat(self, session_id: str, updates: dict[str, Any] | None = None) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.last_activity = time.time()
        if updates:
            for key, value in updates.items():
                if hasattr(session, key) and key not in ("session_id",):
                    setattr(session, key, value)
        return True

    def get_session(self, session_id: str) -> SessionInfo | None:
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[SessionInfo]:
        return [s for s in self._sessions.values() if s.status == "active"]

    def get_all_sessions(self) -> list[SessionInfo]:
        return list(self._sessions.values())

    def get_primary_session(self) -> SessionInfo | None:
        active = self.get_active_sessions()
        if not active:
            return None
        active.sort(key=lambda s: s.last_activity, reverse=True)
        return active[0]

    def get_session_history(self) -> list[dict[str, Any]]:
        return list(self._session_history)


# ── Attention Engine ──────────────────────────────────────────────────


class AttentionEngine:
    """Presence-aware attention state machine.

    Refines Phase 7's AttentionModel with fine-grained FOCUSED state and
    integration with profile modes and session activity.

    States:
      FOCUSED — operator actively working (recent interaction + known profile)
      AVAILABLE — operator present but not actively engaged
      AWAY — no interaction for >5 minutes
      OFFLINE — no active sessions
      SLEEPING — no interaction for >6 hours

    All transitions are deterministic. No LLMs.
    """

    AWAY_THRESHOLD = 300.0
    FOCUSED_THRESHOLD = 60.0
    SLEEPING_THRESHOLD = 21600.0

    def __init__(self) -> None:
        self._state = PresenceAttentionState.OFFLINE
        self._last_interaction: float = 0.0
        self._last_state_change: float = time.time()
        self._active_profile: str = ""

    @property
    def state(self) -> PresenceAttentionState:
        return self._state

    @property
    def last_interaction(self) -> float:
        return self._last_interaction

    @property
    def seconds_since_interaction(self) -> float:
        if self._last_interaction == 0:
            return 0.0
        return time.time() - self._last_interaction

    def record_interaction(self, profile_mode: str = "") -> PresenceAttentionState:
        self._last_interaction = time.time()
        if profile_mode:
            self._active_profile = profile_mode
        if self._active_profile:
            self._transition(PresenceAttentionState.FOCUSED)
        else:
            self._transition(PresenceAttentionState.AVAILABLE)
        return self._state

    def update(self, has_active_sessions: bool, profile_mode: str = "") -> PresenceAttentionState:
        if profile_mode:
            self._active_profile = profile_mode

        if not has_active_sessions:
            self._transition(PresenceAttentionState.OFFLINE)
            return self._state

        elapsed = self.seconds_since_interaction

        if elapsed == 0 or elapsed < self.FOCUSED_THRESHOLD:
            if self._active_profile:
                self._transition(PresenceAttentionState.FOCUSED)
            else:
                self._transition(PresenceAttentionState.AVAILABLE)
        elif elapsed < self.AWAY_THRESHOLD:
            self._transition(PresenceAttentionState.AVAILABLE)
        elif elapsed >= self.SLEEPING_THRESHOLD:
            self._transition(PresenceAttentionState.SLEEPING)
        else:
            self._transition(PresenceAttentionState.AWAY)

        return self._state

    def _transition(self, new_state: PresenceAttentionState) -> None:
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        self._last_state_change = time.time()
        logger.debug("presence attention: %s → %s", old.value, new_state.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "last_interaction": self._last_interaction,
            "seconds_since_interaction": self.seconds_since_interaction,
            "last_state_change": self._last_state_change,
            "active_profile": self._active_profile,
        }


# ── Interruptibility Engine ──────────────────────────────────────────


class InterruptibilityEngine:
    """Determines whether UMH should surface notifications.

    Rules are deterministic state-machine lookups:
      FOCUSED  → CRITICAL_ONLY (only critical alerts)
      AVAILABLE → NORMAL (all notifications)
      AWAY     → QUEUE (accumulate for return)
      OFFLINE  → DEFER (hold until next session)
      SLEEPING → DEFER (hold until wake)
    """

    _RULES: dict[PresenceAttentionState, InterruptionLevel] = {
        PresenceAttentionState.FOCUSED: InterruptionLevel.CRITICAL_ONLY,
        PresenceAttentionState.AVAILABLE: InterruptionLevel.NORMAL,
        PresenceAttentionState.AWAY: InterruptionLevel.QUEUE,
        PresenceAttentionState.OFFLINE: InterruptionLevel.DEFER,
        PresenceAttentionState.SLEEPING: InterruptionLevel.DEFER,
    }

    def get_interruption_level(self, attention: PresenceAttentionState) -> InterruptionLevel:
        return self._RULES.get(attention, InterruptionLevel.DEFER)

    def should_surface(
        self,
        attention: PresenceAttentionState,
        is_critical: bool = False,
    ) -> bool:
        level = self.get_interruption_level(attention)
        if level == InterruptionLevel.NORMAL:
            return True
        if level == InterruptionLevel.CRITICAL_ONLY:
            return is_critical
        return False

    def get_recommendation_filter(
        self,
        attention: PresenceAttentionState,
    ) -> str:
        if attention == PresenceAttentionState.FOCUSED:
            return "suppress"
        elif attention == PresenceAttentionState.AVAILABLE:
            return "normal"
        elif attention == PresenceAttentionState.AWAY:
            return "accumulate"
        else:
            return "defer"


# ── Presence Timeline ─────────────────────────────────────────────────


class PresenceTimeline:
    """Records presence events in chronological order.

    JSONL-backed. Records device changes, session lifecycle, attention
    transitions, and profile changes.
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or os.path.join(_presence_data_dir(), "timeline")
        os.makedirs(self._data_dir, exist_ok=True)
        self._timeline_path = os.path.join(self._data_dir, "events.jsonl")
        self._events: list[PresenceEvent] = []
        self._max_memory_events = 500

    def record(self, event: PresenceEvent) -> None:
        self._events.append(event)
        if len(self._events) > self._max_memory_events:
            self._events = self._events[-self._max_memory_events:]
        self._persist(event)

    def emit(
        self,
        event_type: str,
        summary: str,
        details: dict[str, Any] | None = None,
    ) -> PresenceEvent:
        event = PresenceEvent(
            event_type=event_type,
            summary=summary,
            details=details or {},
        )
        self.record(event)
        return event

    def get_events(
        self,
        since: float = 0.0,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        filtered = self._events
        if since > 0:
            filtered = [e for e in filtered if e.timestamp >= since]
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_events_between(
        self,
        start: float,
        end: float,
    ) -> list[dict[str, Any]]:
        return [
            e.to_dict() for e in self._events
            if start <= e.timestamp <= end
        ]

    def _persist(self, event: PresenceEvent) -> None:
        try:
            with open(self._timeline_path, "a") as f:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        except OSError as e:
            logger.debug("presence: timeline persist failed: %s", e)

    def _load_from_disk(self) -> None:
        if not os.path.exists(self._timeline_path):
            return
        try:
            with open(self._timeline_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        self._events.append(PresenceEvent.from_dict(data))
            if len(self._events) > self._max_memory_events:
                self._events = self._events[-self._max_memory_events:]
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("presence: timeline load failed: %s", e)


# ── Presence Runtime (Orchestrator) ───────────────────────────────────


class PresenceRuntime:
    """Top-level orchestrator for operator presence awareness.

    Composes: DeviceRegistry, SessionRegistry, AttentionEngine,
    InterruptibilityEngine, PresenceTimeline.

    Provides:
      - capture_snapshot() → PresenceSnapshot
      - record_interaction(profile_mode) → attention state
      - register/end sessions
      - device awareness
      - interruptibility decisions
      - timeline of presence events
      - integration hooks for Phase 5/6/7
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or _presence_data_dir()
        _ensure_dirs()
        self.devices = DeviceRegistry()
        self.sessions = SessionRegistry()
        self.attention = AttentionEngine()
        self.interruptibility = InterruptibilityEngine()
        self.timeline = PresenceTimeline(
            os.path.join(self._data_dir, "timeline")
        )
        self._snapshots: list[PresenceSnapshot] = []
        self._max_snapshots = 50
        self._last_snapshot: PresenceSnapshot | None = None

    # ── Snapshot ──────────────────────────────────────────────────

    def capture_snapshot(self) -> PresenceSnapshot:
        devices = self.devices.get_all_devices()
        sessions = self.sessions.get_active_sessions()
        primary = self.sessions.get_primary_session()

        has_sessions = len(sessions) > 0
        profile = primary.profile_mode if primary else ""
        attention = self.attention.update(has_sessions, profile)
        interruption = self.interruptibility.get_interruption_level(attention)

        active_device = ""
        active_host = ""
        interaction_surface = InteractionSurface.NONE.value

        if primary:
            active_device = primary.device_id
            active_host = primary.host
            interaction_surface = primary.interaction_surface

        snapshot = PresenceSnapshot(
            operator_present=has_sessions,
            active_device=active_device,
            active_host=active_host,
            active_session=primary.session_id if primary else "",
            active_profile_mode=profile,
            active_system_modes=[],
            attention_state=attention.value,
            last_activity_timestamp=self.attention.last_interaction,
            interaction_surface=interaction_surface,
            interruption_budget=interruption.value,
            devices=[d.to_dict() for d in devices],
            sessions=[s.to_dict() for s in sessions],
        )

        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        self._last_snapshot = snapshot
        self._persist_snapshot(snapshot)

        return snapshot

    def get_snapshot(self) -> dict[str, Any] | None:
        if self._last_snapshot:
            return self._last_snapshot.to_dict()
        return None

    # ── Session Management ────────────────────────────────────────

    def register_session(
        self,
        session_id: str,
        host: str = "",
        device_id: str = "",
        profile_mode: str = "",
        client_type: str = "",
        control_surface: str = "",
        interaction_surface: str = "none",
    ) -> SessionInfo:
        session = self.sessions.register_session(
            session_id=session_id,
            host=host,
            device_id=device_id,
            profile_mode=profile_mode,
            client_type=client_type,
            control_surface=control_surface,
            interaction_surface=interaction_surface,
        )

        self.timeline.emit(
            PresenceEventType.SESSION_STARTED.value,
            f"Session {session_id} started on {device_id}",
            {"session_id": session_id, "device_id": device_id, "host": host},
        )

        if not self._was_present_before():
            self.timeline.emit(
                PresenceEventType.OPERATOR_PRESENT.value,
                "Operator became present",
                {"device_id": device_id, "session_id": session_id},
            )

        self.attention.record_interaction(profile_mode)
        return session

    def end_session(self, session_id: str) -> SessionInfo | None:
        session = self.sessions.end_session(session_id)
        if session:
            self.timeline.emit(
                PresenceEventType.SESSION_ENDED.value,
                f"Session {session_id} ended",
                {"session_id": session_id, "device_id": session.device_id},
            )

            remaining = self.sessions.get_active_sessions()
            if not remaining:
                self.timeline.emit(
                    PresenceEventType.OPERATOR_ABSENT.value,
                    "Operator became absent (no active sessions)",
                    {},
                )
                self.attention.update(False)

        return session

    def heartbeat(self, session_id: str, updates: dict[str, Any] | None = None) -> bool:
        result = self.sessions.heartbeat(session_id, updates)
        if result:
            self.attention.record_interaction()
        return result

    # ── Interaction ───────────────────────────────────────────────

    def record_interaction(self, profile_mode: str = "") -> dict[str, Any]:
        old_state = self.attention.state
        new_state = self.attention.record_interaction(profile_mode)

        if old_state != new_state:
            self.timeline.emit(
                PresenceEventType.ATTENTION_CHANGED.value,
                f"Attention: {old_state.value} → {new_state.value}",
                {"from": old_state.value, "to": new_state.value},
            )

        return self.attention.to_dict()

    def change_profile(self, profile_mode: str) -> dict[str, Any]:
        old_attention = self.attention.state
        self.attention.record_interaction(profile_mode)

        primary = self.sessions.get_primary_session()
        if primary:
            primary.profile_mode = profile_mode

        self.timeline.emit(
            PresenceEventType.PROFILE_CHANGED.value,
            f"Profile changed to {profile_mode}",
            {"profile_mode": profile_mode},
        )

        if self.attention.state != old_attention:
            self.timeline.emit(
                PresenceEventType.ATTENTION_CHANGED.value,
                f"Attention: {old_attention.value} → {self.attention.state.value}",
                {"from": old_attention.value, "to": self.attention.state.value},
            )

        return {
            "profile_mode": profile_mode,
            "attention": self.attention.to_dict(),
            "interruption_level": self.interruptibility.get_interruption_level(
                self.attention.state
            ).value,
        }

    # ── Queries ───────────────────────────────────────────────────

    def get_attention_state(self) -> dict[str, Any]:
        return self.attention.to_dict()

    def get_interruption_level(self) -> str:
        return self.interruptibility.get_interruption_level(self.attention.state).value

    def should_interrupt(self, is_critical: bool = False) -> bool:
        return self.interruptibility.should_surface(self.attention.state, is_critical)

    def get_recommendation_filter(self) -> str:
        return self.interruptibility.get_recommendation_filter(self.attention.state)

    def get_devices(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self.devices.get_all_devices()]

    def get_online_devices(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self.devices.get_online_devices()]

    def get_sessions(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.sessions.get_all_sessions()]

    def get_active_sessions(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.sessions.get_active_sessions()]

    def get_timeline(
        self,
        since: float = 0.0,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self.timeline.get_events(since, event_type, limit)

    def get_session_history(self) -> list[dict[str, Any]]:
        return self.sessions.get_session_history()

    def get_status(self) -> dict[str, Any]:
        sessions = self.sessions.get_active_sessions()
        primary = self.sessions.get_primary_session()
        devices = self.devices.get_online_devices()

        return {
            "operator_present": len(sessions) > 0,
            "attention_state": self.attention.state.value,
            "interruption_level": self.interruptibility.get_interruption_level(
                self.attention.state
            ).value,
            "active_session_count": len(sessions),
            "online_device_count": len(devices),
            "active_device": primary.device_id if primary else "",
            "active_profile_mode": primary.profile_mode if primary else "",
            "interaction_surface": primary.interaction_surface if primary else "none",
            "last_interaction": self.attention.last_interaction,
            "snapshot_count": len(self._snapshots),
        }

    # ── Integration Hooks ─────────────────────────────────────────

    def get_continuity_presence_input(self) -> dict[str, Any]:
        return {
            "operator_present": self.attention.state.is_present,
            "attention_state": self.attention.state.value,
            "active_profile_mode": self.sessions.get_primary_session().profile_mode
            if self.sessions.get_primary_session() else "",
            "interruption_budget": self.interruptibility.get_interruption_level(
                self.attention.state
            ).value,
        }

    def get_tick_loop_filter(self) -> dict[str, Any]:
        return {
            "recommendation_filter": self.get_recommendation_filter(),
            "should_surface_normal": self.should_interrupt(is_critical=False),
            "should_surface_critical": self.should_interrupt(is_critical=True),
        }

    def get_projection_context(self) -> dict[str, Any]:
        return {
            "operator_state": self.attention.state.value,
            "profile_mode": self.sessions.get_primary_session().profile_mode
            if self.sessions.get_primary_session() else "",
            "interaction_surface": self.sessions.get_primary_session().interaction_surface
            if self.sessions.get_primary_session() else "none",
        }

    # ── Internal ──────────────────────────────────────────────────

    def _was_present_before(self) -> bool:
        sessions = self.sessions.get_active_sessions()
        return len(sessions) > 1

    def _persist_snapshot(self, snapshot: PresenceSnapshot) -> None:
        snap_dir = os.path.join(self._data_dir, "snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        path = os.path.join(snap_dir, f"{snapshot.snapshot_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(snapshot.to_dict(), f, indent=2, default=str)
        except OSError as e:
            logger.error("presence: snapshot persist failed: %s", e)


# ── Singleton ──────────────────────────────────────────────────────────


_instance: PresenceRuntime | None = None


def get_presence_runtime() -> PresenceRuntime:
    global _instance
    if _instance is None:
        _instance = PresenceRuntime()
    return _instance


def reset_presence_runtime() -> None:
    global _instance
    _instance = None
