"""Session Runtime — canonical session architecture for UMH.

Phase 12. Makes Session a first-class runtime entity. UMH understands
WHO is operating (Profile Runtime), HOW available they are (Presence
Runtime), and WHERE they are operating (Session Runtime).

Session types: desktop, laptop, phone, tablet, vps, server, container,
browser, remote-desktop, agent-session.

Statuses: active, background, idle, suspended, disconnected.

Authority model: primary (one), secondary (many), background (many).

This runtime tracks, classifies, and records. It does NOT execute work,
launch applications, or control devices.

Composes existing subsystems:
  - Presence Runtime (P8) — attention/interruptibility
  - Continuity Runtime (P7) — snapshot for handoffs
  - Profile Runtime (P11) — active profile binding
  - Projection Engine (P6) — projection snapshot for handoffs
  - Workstation Runtime (P10) — workspace mode binding
  - device_registry.json (infra/) — canonical device definitions

Governance boundary: may observe, classify, record, assemble handoffs.
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


# ── Helpers ──────────────────────────────────────────────────────


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _session_data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "session")


def _ensure_dirs() -> None:
    d = _session_data_dir()
    for sub in ("timeline", "handoffs", "snapshots"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)


# ── Canonical Enums ──────────────────────────────────────────────


class SessionType(str, Enum):
    """Canonical session types."""
    DESKTOP = "desktop"
    LAPTOP = "laptop"
    PHONE = "phone"
    TABLET = "tablet"
    VPS = "vps"
    SERVER = "server"
    CONTAINER = "container"
    BROWSER = "browser"
    REMOTE_DESKTOP = "remote-desktop"
    AGENT_SESSION = "agent-session"


class SessionStatus(str, Enum):
    """Canonical session lifecycle statuses."""
    ACTIVE = "active"
    BACKGROUND = "background"
    IDLE = "idle"
    SUSPENDED = "suspended"
    DISCONNECTED = "disconnected"

    @property
    def is_alive(self) -> bool:
        return self in (
            SessionStatus.ACTIVE,
            SessionStatus.BACKGROUND,
            SessionStatus.IDLE,
        )


class SessionAuthority(str, Enum):
    """Session authority classification."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BACKGROUND = "background"


class SessionEventType(str, Enum):
    """Canonical session lifecycle events."""
    SESSION_STARTED = "session_started"
    SESSION_RESUMED = "session_resumed"
    SESSION_SUSPENDED = "session_suspended"
    SESSION_DISCONNECTED = "session_disconnected"
    SESSION_RESTORED = "session_restored"
    SESSION_PROMOTED = "session_promoted"
    SESSION_DEMOTED = "session_demoted"
    HANDOFF_INITIATED = "handoff_initiated"
    HANDOFF_COMPLETED = "handoff_completed"
    AUTHORITY_CHANGED = "authority_changed"
    WORK_BOUND = "work_bound"
    WORK_UNBOUND = "work_unbound"


class HandoffStatus(str, Enum):
    """Status of a session handoff."""
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"


# ── Data Models ──────────────────────────────────────────────────


@dataclass
class Session:
    """Canonical session model."""

    session_id: str = ""
    session_type: str = "desktop"
    host_id: str = ""
    device_id: str = ""
    profile_id: str = ""
    created_at: float = 0.0
    last_seen_at: float = 0.0
    status: str = "active"
    attention_state: str = "available"
    active_workstation_mode: str = ""
    authority: str = "secondary"
    bound_work_packets: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = f"sess-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.last_seen_at:
            self.last_seen_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "host_id": self.host_id,
            "device_id": self.device_id,
            "profile_id": self.profile_id,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "status": self.status,
            "attention_state": self.attention_state,
            "active_workstation_mode": self.active_workstation_mode,
            "authority": self.authority,
            "bound_work_packets": self.bound_work_packets,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        mapped = {}
        for k, v in data.items():
            if k in cls.__dataclass_fields__:
                mapped[k] = v
        return cls(**mapped)


@dataclass
class SessionEvent:
    """A lifecycle event for a session."""

    event_id: str = ""
    event_type: str = ""
    session_id: str = ""
    timestamp: float = 0.0
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = f"sevt-{uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionEvent:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SessionHandoff:
    """A handoff package for session transfer between devices."""

    handoff_id: str = ""
    source_session_id: str = ""
    target_session_id: str = ""
    source_device_id: str = ""
    target_device_id: str = ""
    status: str = "pending"
    created_at: float = 0.0
    completed_at: float = 0.0
    active_objectives: list[dict[str, Any]] = field(default_factory=list)
    active_work_packets: list[dict[str, Any]] = field(default_factory=list)
    recent_commands: list[dict[str, Any]] = field(default_factory=list)
    continuity_snapshot: dict[str, Any] = field(default_factory=dict)
    projection_snapshot: dict[str, Any] = field(default_factory=dict)
    workstation_state: dict[str, Any] = field(default_factory=dict)
    profile_context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.handoff_id:
            self.handoff_id = f"hoff-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "source_session_id": self.source_session_id,
            "target_session_id": self.target_session_id,
            "source_device_id": self.source_device_id,
            "target_device_id": self.target_device_id,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "active_objectives": self.active_objectives,
            "active_work_packets": self.active_work_packets,
            "recent_commands": self.recent_commands,
            "continuity_snapshot": self.continuity_snapshot,
            "projection_snapshot": self.projection_snapshot,
            "workstation_state": self.workstation_state,
            "profile_context": self.profile_context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionHandoff:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SessionContinuityLink:
    """A link in the session continuity graph: Profile → Session → Objective → WorkPacket → Outcome."""

    link_id: str = ""
    profile_id: str = ""
    session_id: str = ""
    objective_id: str = ""
    work_packet_id: str = ""
    outcome_id: str = ""
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.link_id:
            self.link_id = f"slink-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "profile_id": self.profile_id,
            "session_id": self.session_id,
            "objective_id": self.objective_id,
            "work_packet_id": self.work_packet_id,
            "outcome_id": self.outcome_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionContinuityLink:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SessionRuntimeSnapshot:
    """Complete snapshot of session runtime state."""

    snapshot_id: str = ""
    captured_at: float = 0.0
    primary_session: dict[str, Any] | None = None
    secondary_sessions: list[dict[str, Any]] = field(default_factory=list)
    background_sessions: list[dict[str, Any]] = field(default_factory=list)
    recent_handoffs: list[dict[str, Any]] = field(default_factory=list)
    continuity_links: list[dict[str, Any]] = field(default_factory=list)
    total_active: int = 0
    total_all: int = 0

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            self.snapshot_id = f"sssnap-{uuid4().hex[:12]}"
        if not self.captured_at:
            self.captured_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "primary_session": self.primary_session,
            "secondary_sessions": self.secondary_sessions,
            "background_sessions": self.background_sessions,
            "recent_handoffs": self.recent_handoffs,
            "continuity_links": self.continuity_links,
            "total_active": self.total_active,
            "total_all": self.total_all,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionRuntimeSnapshot:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ── Session Registry ─────────────────────────────────────────────


class SessionRegistry:
    """Canonical session registry with authority classification.

    Manages active sessions, tracks authority hierarchy (primary/secondary/
    background), and persists session state to disk.

    Authority rules:
      - Exactly one primary session at any time (or none).
      - Promoting a session to primary demotes the current primary to secondary.
      - background sessions are non-interactive (agent sessions, containers).
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        _ensure_dirs()
        self._state_path = os.path.join(_session_data_dir(), "registry_state.json")
        self._load_state()

    def _load_state(self) -> None:
        if os.path.exists(self._state_path):
            try:
                with open(self._state_path) as f:
                    data = json.load(f)
                for sd in data.get("sessions", []):
                    s = Session.from_dict(sd)
                    self._sessions[s.session_id] = s
                logger.debug("session_registry: loaded %d sessions", len(self._sessions))
            except Exception as e:
                logger.warning("session_registry: failed to load state: %s", e)

    def _save_state(self) -> None:
        try:
            data = {"sessions": [s.to_dict() for s in self._sessions.values()]}
            with open(self._state_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning("session_registry: failed to save state: %s", e)

    def register(self, session: Session) -> Session:
        """Register a new session. Persists immediately."""
        self._sessions[session.session_id] = session
        self._save_state()
        logger.debug(
            "session_registry: registered %s type=%s device=%s",
            session.session_id, session.session_type, session.device_id,
        )
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def remove(self, session_id: str) -> Session | None:
        s = self._sessions.pop(session_id, None)
        if s:
            self._save_state()
        return s

    def all_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def active_sessions(self) -> list[Session]:
        return [
            s for s in self._sessions.values()
            if SessionStatus(s.status).is_alive
        ]

    def get_primary(self) -> Session | None:
        for s in self._sessions.values():
            if s.authority == SessionAuthority.PRIMARY.value and SessionStatus(s.status).is_alive:
                return s
        return None

    def get_secondary(self) -> list[Session]:
        return [
            s for s in self._sessions.values()
            if s.authority == SessionAuthority.SECONDARY.value and SessionStatus(s.status).is_alive
        ]

    def get_background(self) -> list[Session]:
        return [
            s for s in self._sessions.values()
            if s.authority == SessionAuthority.BACKGROUND.value and SessionStatus(s.status).is_alive
        ]

    def promote_to_primary(self, session_id: str) -> tuple[bool, str | None]:
        """Promote a session to primary. Demotes current primary to secondary.

        Returns (success, demoted_session_id).
        """
        target = self._sessions.get(session_id)
        if not target:
            return False, None

        demoted_id = None
        current_primary = self.get_primary()
        if current_primary and current_primary.session_id != session_id:
            current_primary.authority = SessionAuthority.SECONDARY.value
            demoted_id = current_primary.session_id

        target.authority = SessionAuthority.PRIMARY.value
        target.status = SessionStatus.ACTIVE.value
        target.last_seen_at = time.time()
        self._save_state()
        return True, demoted_id

    def update_status(self, session_id: str, status: str) -> bool:
        s = self._sessions.get(session_id)
        if not s:
            return False
        s.status = status
        s.last_seen_at = time.time()
        self._save_state()
        return True

    def heartbeat(self, session_id: str) -> bool:
        s = self._sessions.get(session_id)
        if not s:
            return False
        s.last_seen_at = time.time()
        self._save_state()
        return True

    def bind_work_packet(self, session_id: str, work_packet_id: str) -> bool:
        s = self._sessions.get(session_id)
        if not s:
            return False
        if work_packet_id not in s.bound_work_packets:
            s.bound_work_packets.append(work_packet_id)
            self._save_state()
        return True

    def unbind_work_packet(self, session_id: str, work_packet_id: str) -> bool:
        s = self._sessions.get(session_id)
        if not s:
            return False
        if work_packet_id in s.bound_work_packets:
            s.bound_work_packets.remove(work_packet_id)
            self._save_state()
        return True


# ── Session Lifecycle Engine ─────────────────────────────────────


class SessionLifecycleEngine:
    """Detects and records session lifecycle transitions.

    Transitions:
      started → active
      active → idle (timeout)
      active → suspended (operator leaves)
      active → disconnected (connection lost)
      suspended → resumed (operator returns)
      disconnected → restored (reconnection)

    All transitions are deterministic.
    """

    IDLE_TIMEOUT = 300.0  # 5 minutes
    DISCONNECT_TIMEOUT = 600.0  # 10 minutes

    def __init__(self, registry: SessionRegistry) -> None:
        self._registry = registry

    def start_session(
        self,
        session_type: str = "desktop",
        host_id: str = "",
        device_id: str = "",
        profile_id: str = "",
        workstation_mode: str = "",
        authority: str = "secondary",
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Create and register a new session."""
        session = Session(
            session_type=session_type,
            host_id=host_id,
            device_id=device_id,
            profile_id=profile_id,
            status=SessionStatus.ACTIVE.value,
            active_workstation_mode=workstation_mode,
            authority=authority,
            metadata=metadata or {},
        )
        return self._registry.register(session)

    def suspend_session(self, session_id: str) -> bool:
        return self._registry.update_status(session_id, SessionStatus.SUSPENDED.value)

    def resume_session(self, session_id: str) -> bool:
        s = self._registry.get(session_id)
        if not s:
            return False
        if s.status in (SessionStatus.SUSPENDED.value, SessionStatus.IDLE.value):
            return self._registry.update_status(session_id, SessionStatus.ACTIVE.value)
        return False

    def disconnect_session(self, session_id: str) -> bool:
        return self._registry.update_status(session_id, SessionStatus.DISCONNECTED.value)

    def restore_session(self, session_id: str) -> bool:
        s = self._registry.get(session_id)
        if not s:
            return False
        if s.status == SessionStatus.DISCONNECTED.value:
            return self._registry.update_status(session_id, SessionStatus.ACTIVE.value)
        return False

    def background_session(self, session_id: str) -> bool:
        return self._registry.update_status(session_id, SessionStatus.BACKGROUND.value)

    def check_timeouts(self) -> list[tuple[str, str]]:
        """Check all active sessions for idle/disconnect timeouts.

        Returns list of (session_id, new_status) transitions applied.
        """
        transitions = []
        now = time.time()
        for s in self._registry.active_sessions():
            if s.status == SessionStatus.ACTIVE.value:
                elapsed = now - s.last_seen_at
                if elapsed > self.DISCONNECT_TIMEOUT:
                    self._registry.update_status(s.session_id, SessionStatus.DISCONNECTED.value)
                    transitions.append((s.session_id, SessionStatus.DISCONNECTED.value))
                elif elapsed > self.IDLE_TIMEOUT:
                    self._registry.update_status(s.session_id, SessionStatus.IDLE.value)
                    transitions.append((s.session_id, SessionStatus.IDLE.value))
        return transitions


# ── Session Handoff Runtime ──────────────────────────────────────


class SessionHandoffRuntime:
    """Assembles handoff packages for session transfer between devices.

    A handoff captures the operator's full operational context so they
    can move from one device to another without losing context.

    Handoff package contains:
      - Active objectives (from continuity snapshot)
      - Active WorkPackets (from continuity snapshot)
      - Recent commands (from command history)
      - Continuity snapshot (P7)
      - Projection snapshot (P6)
      - Workstation state (P10)
      - Profile context (P11)
    """

    def __init__(self, registry: SessionRegistry) -> None:
        self._registry = registry
        self._handoffs: list[SessionHandoff] = []
        _ensure_dirs()
        self._handoffs_dir = os.path.join(_session_data_dir(), "handoffs")

    def initiate_handoff(
        self,
        source_session_id: str,
        target_session_id: str,
    ) -> SessionHandoff | None:
        """Create a handoff package from source to target session."""
        source = self._registry.get(source_session_id)
        target = self._registry.get(target_session_id)
        if not source or not target:
            logger.warning(
                "session_handoff: cannot create handoff — source=%s target=%s",
                source_session_id, target_session_id,
            )
            return None

        handoff = SessionHandoff(
            source_session_id=source_session_id,
            target_session_id=target_session_id,
            source_device_id=source.device_id,
            target_device_id=target.device_id,
        )

        handoff.active_work_packets = [
            {"work_packet_id": wp_id} for wp_id in source.bound_work_packets
        ]

        handoff.continuity_snapshot = self._get_continuity_snapshot()
        handoff.projection_snapshot = self._get_projection_snapshot()
        handoff.workstation_state = self._get_workstation_state()
        handoff.profile_context = self._get_profile_context()

        self._handoffs.append(handoff)
        self._persist_handoff(handoff)
        return handoff

    def complete_handoff(self, handoff_id: str) -> bool:
        """Mark a handoff as completed."""
        for h in self._handoffs:
            if h.handoff_id == handoff_id:
                h.status = HandoffStatus.COMPLETED.value
                h.completed_at = time.time()
                self._persist_handoff(h)
                return True
        return False

    def get_handoff(self, handoff_id: str) -> SessionHandoff | None:
        for h in self._handoffs:
            if h.handoff_id == handoff_id:
                return h
        return None

    def get_recent_handoffs(self, limit: int = 20) -> list[SessionHandoff]:
        return sorted(self._handoffs, key=lambda h: h.created_at, reverse=True)[:limit]

    def get_pending_handoffs(self) -> list[SessionHandoff]:
        return [h for h in self._handoffs if h.status == HandoffStatus.PENDING.value]

    def _persist_handoff(self, handoff: SessionHandoff) -> None:
        try:
            path = os.path.join(self._handoffs_dir, f"{handoff.handoff_id}.json")
            with open(path, "w") as f:
                json.dump(handoff.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.warning("session_handoff: persist failed: %s", e)

    def _get_continuity_snapshot(self) -> dict[str, Any]:
        try:
            from substrate.organism.continuity_runtime import get_continuity_runtime
            cr = get_continuity_runtime()
            snap = cr.capture_snapshot()
            return snap.to_dict()
        except Exception as e:
            logger.debug("session_handoff: continuity snapshot unavailable: %s", e)
            return {}

    def _get_projection_snapshot(self) -> dict[str, Any]:
        try:
            from substrate.organism.projection_engine import get_projection_engine
            pe = get_projection_engine()
            snap = pe.capture_snapshot()
            return snap.to_dict()
        except Exception as e:
            logger.debug("session_handoff: projection snapshot unavailable: %s", e)
            return {}

    def _get_workstation_state(self) -> dict[str, Any]:
        try:
            from substrate.organism.workstation_runtime import get_workstation_runtime
            wr = get_workstation_runtime()
            state = wr.get_state()
            return state
        except Exception as e:
            logger.debug("session_handoff: workstation state unavailable: %s", e)
            return {}

    def _get_profile_context(self) -> dict[str, Any]:
        try:
            from substrate.organism.profile_runtime import get_profile_runtime
            pr = get_profile_runtime()
            ctx = pr.get_context()
            return ctx.to_dict() if hasattr(ctx, "to_dict") else ctx
        except Exception as e:
            logger.debug("session_handoff: profile context unavailable: %s", e)
            return {}


# ── Session Continuity Graph ─────────────────────────────────────


class SessionContinuityGraph:
    """Tracks the lineage: Profile → Session → Objective → WorkPacket → Outcome.

    Preserves the full chain so any work can be traced back to the
    session and profile that originated it.
    """

    def __init__(self) -> None:
        self._links: list[SessionContinuityLink] = []
        _ensure_dirs()
        self._path = os.path.join(_session_data_dir(), "continuity_graph.jsonl")
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._links.append(
                                SessionContinuityLink.from_dict(json.loads(line))
                            )
            except Exception as e:
                logger.warning("session_continuity_graph: load failed: %s", e)

    def add_link(
        self,
        profile_id: str = "",
        session_id: str = "",
        objective_id: str = "",
        work_packet_id: str = "",
        outcome_id: str = "",
    ) -> SessionContinuityLink:
        link = SessionContinuityLink(
            profile_id=profile_id,
            session_id=session_id,
            objective_id=objective_id,
            work_packet_id=work_packet_id,
            outcome_id=outcome_id,
        )
        self._links.append(link)
        self._persist(link)
        return link

    def get_links_for_session(self, session_id: str) -> list[SessionContinuityLink]:
        return [l for l in self._links if l.session_id == session_id]

    def get_links_for_profile(self, profile_id: str) -> list[SessionContinuityLink]:
        return [l for l in self._links if l.profile_id == profile_id]

    def get_links_for_work_packet(self, work_packet_id: str) -> list[SessionContinuityLink]:
        return [l for l in self._links if l.work_packet_id == work_packet_id]

    def get_all_links(self) -> list[SessionContinuityLink]:
        return list(self._links)

    def _persist(self, link: SessionContinuityLink) -> None:
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(link.to_dict(), default=str) + "\n")
        except Exception as e:
            logger.warning("session_continuity_graph: persist failed: %s", e)


# ── Session Timeline ─────────────────────────────────────────────


class SessionTimeline:
    """Chronological event recording for session lifecycle events."""

    def __init__(self) -> None:
        _ensure_dirs()
        self._path = os.path.join(_session_data_dir(), "timeline", "events.jsonl")
        self._events: list[SessionEvent] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._events.append(SessionEvent.from_dict(json.loads(line)))
            except Exception as e:
                logger.warning("session_timeline: load failed: %s", e)

    def emit(self, event_type: str, session_id: str, summary: str,
             details: dict[str, Any] | None = None) -> SessionEvent:
        event = SessionEvent(
            event_type=event_type,
            session_id=session_id,
            summary=summary,
            details=details or {},
        )
        self._events.append(event)
        self._persist(event)
        return event

    def get_recent(self, limit: int = 50) -> list[SessionEvent]:
        return sorted(self._events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_for_session(self, session_id: str) -> list[SessionEvent]:
        return [e for e in self._events if e.session_id == session_id]

    def _persist(self, event: SessionEvent) -> None:
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        except Exception as e:
            logger.warning("session_timeline: persist failed: %s", e)


# ── Session Runtime (top-level orchestrator) ─────────────────────


class SessionRuntime:
    """Top-level orchestrator for session management.

    Composes:
      - SessionRegistry — session state and authority
      - SessionLifecycleEngine — lifecycle transitions
      - SessionHandoffRuntime — handoff assembly
      - SessionContinuityGraph — lineage tracking
      - SessionTimeline — event recording

    Integrates with:
      - Presence Runtime (P8) — session presence notifications
      - Profile Runtime (P11) — profile binding
      - Continuity Runtime (P7) — snapshot for handoffs
      - Workstation Runtime (P10) — workspace mode
    """

    def __init__(self) -> None:
        self._registry = SessionRegistry()
        self._lifecycle = SessionLifecycleEngine(self._registry)
        self._handoff = SessionHandoffRuntime(self._registry)
        self._graph = SessionContinuityGraph()
        self._timeline = SessionTimeline()

    # ── Session CRUD ──────────────────────────────────────────────

    def start_session(
        self,
        session_type: str = "desktop",
        host_id: str = "",
        device_id: str = "",
        profile_id: str = "",
        workstation_mode: str = "",
        authority: str = "secondary",
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Start a new session. Emits timeline event and notifies presence."""
        session = self._lifecycle.start_session(
            session_type=session_type,
            host_id=host_id,
            device_id=device_id,
            profile_id=profile_id,
            workstation_mode=workstation_mode,
            authority=authority,
            metadata=metadata,
        )

        if authority == SessionAuthority.PRIMARY.value:
            self._registry.promote_to_primary(session.session_id)

        self._timeline.emit(
            SessionEventType.SESSION_STARTED.value,
            session.session_id,
            f"Session started: {session_type} on {device_id or host_id}",
            {"session_type": session_type, "device_id": device_id, "profile_id": profile_id},
        )

        if profile_id:
            self._graph.add_link(profile_id=profile_id, session_id=session.session_id)

        self._notify_presence_session_start(session)
        return session

    def suspend_session(self, session_id: str) -> bool:
        result = self._lifecycle.suspend_session(session_id)
        if result:
            self._timeline.emit(
                SessionEventType.SESSION_SUSPENDED.value,
                session_id,
                "Session suspended",
            )
        return result

    def resume_session(self, session_id: str) -> bool:
        result = self._lifecycle.resume_session(session_id)
        if result:
            self._timeline.emit(
                SessionEventType.SESSION_RESUMED.value,
                session_id,
                "Session resumed",
            )
        return result

    def disconnect_session(self, session_id: str) -> bool:
        result = self._lifecycle.disconnect_session(session_id)
        if result:
            self._timeline.emit(
                SessionEventType.SESSION_DISCONNECTED.value,
                session_id,
                "Session disconnected",
            )
        return result

    def restore_session(self, session_id: str) -> bool:
        result = self._lifecycle.restore_session(session_id)
        if result:
            self._timeline.emit(
                SessionEventType.SESSION_RESTORED.value,
                session_id,
                "Session restored",
            )
        return result

    # ── Authority ─────────────────────────────────────────────────

    def promote_to_primary(self, session_id: str) -> tuple[bool, str | None]:
        success, demoted = self._registry.promote_to_primary(session_id)
        if success:
            self._timeline.emit(
                SessionEventType.SESSION_PROMOTED.value,
                session_id,
                f"Session promoted to primary (demoted: {demoted or 'none'})",
                {"demoted_session_id": demoted},
            )
            if demoted:
                self._timeline.emit(
                    SessionEventType.SESSION_DEMOTED.value,
                    demoted,
                    "Session demoted to secondary",
                )
        return success, demoted

    # ── Handoff ───────────────────────────────────────────────────

    def initiate_handoff(
        self, source_session_id: str, target_session_id: str
    ) -> SessionHandoff | None:
        handoff = self._handoff.initiate_handoff(source_session_id, target_session_id)
        if handoff:
            self._timeline.emit(
                SessionEventType.HANDOFF_INITIATED.value,
                source_session_id,
                f"Handoff initiated to {target_session_id}",
                {"handoff_id": handoff.handoff_id, "target": target_session_id},
            )
        return handoff

    def complete_handoff(self, handoff_id: str) -> bool:
        result = self._handoff.complete_handoff(handoff_id)
        if result:
            handoff = self._handoff.get_handoff(handoff_id)
            if handoff:
                self._timeline.emit(
                    SessionEventType.HANDOFF_COMPLETED.value,
                    handoff.target_session_id,
                    f"Handoff completed from {handoff.source_session_id}",
                    {"handoff_id": handoff_id},
                )
        return result

    # ── Work binding ──────────────────────────────────────────────

    def bind_work_packet(self, session_id: str, work_packet_id: str) -> bool:
        result = self._registry.bind_work_packet(session_id, work_packet_id)
        if result:
            session = self._registry.get(session_id)
            self._timeline.emit(
                SessionEventType.WORK_BOUND.value,
                session_id,
                f"WorkPacket {work_packet_id} bound",
                {"work_packet_id": work_packet_id},
            )
            if session:
                self._graph.add_link(
                    profile_id=session.profile_id,
                    session_id=session_id,
                    work_packet_id=work_packet_id,
                )
        return result

    def unbind_work_packet(self, session_id: str, work_packet_id: str) -> bool:
        result = self._registry.unbind_work_packet(session_id, work_packet_id)
        if result:
            self._timeline.emit(
                SessionEventType.WORK_UNBOUND.value,
                session_id,
                f"WorkPacket {work_packet_id} unbound",
                {"work_packet_id": work_packet_id},
            )
        return result

    # ── Query ─────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> Session | None:
        return self._registry.get(session_id)

    def list_sessions(self) -> list[Session]:
        return self._registry.all_sessions()

    def list_active_sessions(self) -> list[Session]:
        return self._registry.active_sessions()

    def get_primary_session(self) -> Session | None:
        return self._registry.get_primary()

    def get_secondary_sessions(self) -> list[Session]:
        return self._registry.get_secondary()

    def get_background_sessions(self) -> list[Session]:
        return self._registry.get_background()

    def get_handoff(self, handoff_id: str) -> SessionHandoff | None:
        return self._handoff.get_handoff(handoff_id)

    def get_recent_handoffs(self, limit: int = 20) -> list[SessionHandoff]:
        return self._handoff.get_recent_handoffs(limit)

    def get_pending_handoffs(self) -> list[SessionHandoff]:
        return self._handoff.get_pending_handoffs()

    def get_timeline(self, limit: int = 50) -> list[SessionEvent]:
        return self._timeline.get_recent(limit)

    def get_session_timeline(self, session_id: str) -> list[SessionEvent]:
        return self._timeline.get_for_session(session_id)

    def get_continuity_links(self, session_id: str) -> list[SessionContinuityLink]:
        return self._graph.get_links_for_session(session_id)

    def get_all_continuity_links(self) -> list[SessionContinuityLink]:
        return self._graph.get_all_links()

    # ── Tick integration ──────────────────────────────────────────

    def check_timeouts(self) -> list[tuple[str, str]]:
        """Check for idle/disconnected sessions. Called by tick loop."""
        transitions = self._lifecycle.check_timeouts()
        for session_id, new_status in transitions:
            event_type = (
                SessionEventType.SESSION_DISCONNECTED.value
                if new_status == SessionStatus.DISCONNECTED.value
                else SessionEventType.SESSION_SUSPENDED.value
            )
            self._timeline.emit(event_type, session_id, f"Timeout → {new_status}")
        return transitions

    # ── State ─────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        primary = self._registry.get_primary()
        secondary = self._registry.get_secondary()
        background = self._registry.get_background()
        return {
            "primary_session": primary.to_dict() if primary else None,
            "secondary_sessions": [s.to_dict() for s in secondary],
            "background_sessions": [s.to_dict() for s in background],
            "total_active": len(self._registry.active_sessions()),
            "total_all": len(self._registry.all_sessions()),
            "recent_handoffs": [h.to_dict() for h in self._handoff.get_recent_handoffs(5)],
        }

    def capture_snapshot(self) -> SessionRuntimeSnapshot:
        primary = self._registry.get_primary()
        return SessionRuntimeSnapshot(
            primary_session=primary.to_dict() if primary else None,
            secondary_sessions=[s.to_dict() for s in self._registry.get_secondary()],
            background_sessions=[s.to_dict() for s in self._registry.get_background()],
            recent_handoffs=[h.to_dict() for h in self._handoff.get_recent_handoffs(5)],
            continuity_links=[l.to_dict() for l in self._graph.get_all_links()[-10:]],
            total_active=len(self._registry.active_sessions()),
            total_all=len(self._registry.all_sessions()),
        )

    # ── Presence integration ──────────────────────────────────────

    def _notify_presence_session_start(self, session: Session) -> None:
        try:
            from substrate.organism.presence_runtime import get_presence_runtime
            pr = get_presence_runtime()
            pr.register_session(
                session_id=session.session_id,
                host=session.host_id,
                device_id=session.device_id,
                profile_mode=session.profile_id,
                client_type=session.session_type,
            )
        except Exception as e:
            logger.debug("session_runtime: presence notification failed: %s", e)


# ── Singleton ────────────────────────────────────────────────────

_session_runtime: SessionRuntime | None = None


def get_session_runtime() -> SessionRuntime:
    global _session_runtime
    if _session_runtime is None:
        _session_runtime = SessionRuntime()
    return _session_runtime


def reset_session_runtime() -> None:
    global _session_runtime
    _session_runtime = None
