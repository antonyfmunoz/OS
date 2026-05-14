"""
Local listener — bounded wake/activation layer for the substrate.

Purpose
-------
Today the substrate only enters open_day via cron. This module adds a small,
safe, *additive* activation path: a local trigger event (manual button press,
hotkey, simulated wake word, simulated clap, scheduled fire) can cause the
substrate to start an open_day ritual on a specific node — *reusing* the
existing readiness / scene-policy / ritual-body logic.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path (gateway/cognitive_loop/model_router/agent_runtime/
  primitives) is never imported.
- Best-effort. A trigger never raises into the caller. Failures degrade to a
  recorded TriggerEvent with status="error".
- Bounded. Trigger kinds are an explicit enum. No freeform command parsing.
  No raw shell. No spoken-NLU. wake_word_detected and clap_detected are
  *stubs* — the runtime accepts them as bounded signals but does not own any
  audio framework.
- Deterministic. Same trigger + same readiness → same scene decision via the
  existing scene policy. The listener never bypasses readiness.
- Observable. Every trigger is recorded in a tiny ring buffer persisted via
  the substrate storage layer (key: "local_listener_triggers"), capped to
  RETENTION_MAX entries. The operator tick can show recent triggers.
- Reversible. Removing this file leaves the substrate exactly as it was; no
  other module imports from it.

What this module does NOT do
----------------------------
- No real wake-word engine. No real clap detector. No STT. No TTS loop.
- No Pikastream. No browser automation. No new station ActionKinds.
- No modification of station_daemon, ritual_runner, ritual_body, scene_policy,
  station_readiness, scenes — those stay clean.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Optional

from runtime.transport.nodes import NodeRegistry
from runtime.transport.ritual_body import RitualPolicy
from runtime.transport.ritual_runner import start_open_day
from runtime.transport.rituals import RitualRegistry
from runtime.transport.station_readiness import UNAVAILABLE, station_readiness
from runtime.transport.storage import get_storage

STORAGE_KEY = "local_listener_triggers"
RETENTION_MAX = 200


def _log(msg: str) -> None:
    print(f"[substrate.local_listener] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ─── Trigger model ────────────────────────────────────────────────────────────


class TriggerKind(str, Enum):
    """Bounded set of activation causes the listener will accept.

    wake_word_detected and clap_detected are intentionally *stubs* in this
    pass — the substrate accepts them as bounded events but the listener does
    not own any audio framework. Real detection plugs in later as a producer.
    """

    MANUAL_ACTIVATE = "manual_activate"
    HOTKEY_ACTIVATE = "hotkey_activate"
    WAKE_WORD_DETECTED = "wake_word_detected"
    CLAP_DETECTED = "clap_detected"
    SCHEDULED_ACTIVATE = "scheduled_activate"


class TriggerStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"  # ritual started
    SKIPPED = "skipped"  # readiness/policy refused safely
    ERROR = "error"  # unexpected failure (still recorded, never raised)


@dataclass
class LocalTrigger:
    """A single bounded activation event."""

    node_id: str
    kind: TriggerKind
    requested_mode: Optional[str] = (
        None  # builder | operator_mode | full_station | None
    )
    metadata: dict = field(default_factory=dict)
    issued_by: str = "local_listener"
    trigger_id: str = field(default_factory=_new_id)
    occurred_at: str = field(default_factory=_utcnow)
    status: TriggerStatus = TriggerStatus.PENDING
    ritual_id: Optional[str] = None
    decision_reason: Optional[str] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["status"] = self.status.value
        return d


# ─── History store (substrate-storage backed, ring buffered) ──────────────────


class TriggerHistory:
    """Bounded persistent history of trigger events.

    Backed by the existing substrate storage key/value layer (Neon → JSON file
    fallback). Ring-buffered: oldest events drop at RETENTION_MAX.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._storage = get_storage()

    def _load(self) -> list[dict]:
        data = self._storage.get(STORAGE_KEY, default=[])
        return list(data) if isinstance(data, list) else []

    def _save(self, events: list[dict]) -> None:
        if len(events) > RETENTION_MAX:
            events = events[-RETENTION_MAX:]
        self._storage.put(STORAGE_KEY, events)

    def record(self, trigger: LocalTrigger) -> None:
        with self._lock:
            try:
                events = self._load()
                events.append(trigger.as_dict())
                self._save(events)
            except Exception as e:  # noqa: BLE001
                _log(f"history record failed: {e}")

    def latest(self, limit: int = 20, node_id: Optional[str] = None) -> list[dict]:
        with self._lock:
            events = self._load()
            if node_id:
                events = [e for e in events if e.get("node_id") == node_id]
            return list(reversed(events[-limit:]))

    def clear(self) -> None:
        with self._lock:
            self._save([])


_history_singleton: Optional[TriggerHistory] = None


def get_trigger_history() -> TriggerHistory:
    global _history_singleton
    if _history_singleton is None:
        _history_singleton = TriggerHistory()
    return _history_singleton


# ─── Listener runtime ─────────────────────────────────────────────────────────


class LocalListener:
    """Bounded local activation runtime.

    The listener accepts a `LocalTrigger`, performs safety checks (node exists
    and isn't UNAVAILABLE), and delegates to `start_open_day(...)` so the
    existing ritual body computes readiness, infers a scene, and proposes only
    safe actions. The listener itself adds *no* new behavior to ritual_body.
    """

    def __init__(self, history: Optional[TriggerHistory] = None) -> None:
        self._history = history or get_trigger_history()

    # — public API —————————————————————————————————————————————————

    def emit(self, trigger: LocalTrigger) -> LocalTrigger:
        """Emit a trigger and attempt activation. Always returns the trigger
        with status/decision_reason filled in. Never raises."""
        try:
            self._activate(trigger)
        except Exception as e:  # noqa: BLE001
            trigger.status = TriggerStatus.ERROR
            trigger.decision_reason = f"unexpected: {e}"
            _log(f"emit error for {trigger.trigger_id}: {e}")
        finally:
            self._history.record(trigger)
        return trigger

    # convenience constructors --------------------------------------------------

    def manual_activate(
        self,
        node_id: str,
        requested_mode: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> LocalTrigger:
        return self.emit(
            LocalTrigger(
                node_id=node_id,
                kind=TriggerKind.MANUAL_ACTIVATE,
                requested_mode=requested_mode,
                metadata=metadata or {},
            )
        )

    def hotkey_activate(self, node_id: str, **kw) -> LocalTrigger:
        return self.emit(
            LocalTrigger(node_id=node_id, kind=TriggerKind.HOTKEY_ACTIVATE, **kw)
        )

    def simulate_wake_word(self, node_id: str, **kw) -> LocalTrigger:
        # NOTE: stub for future real wake-word producer.
        return self.emit(
            LocalTrigger(node_id=node_id, kind=TriggerKind.WAKE_WORD_DETECTED, **kw)
        )

    def simulate_clap(self, node_id: str, **kw) -> LocalTrigger:
        # NOTE: stub for future real clap-detector producer.
        return self.emit(
            LocalTrigger(node_id=node_id, kind=TriggerKind.CLAP_DETECTED, **kw)
        )

    # — bounded voice-presence bridge ——————————————————————————————
    #
    # Additive sibling path. Does NOT touch emit(), TriggerHistory, ritual
    # startup, or readiness gating. Lives here only because operators reach
    # for the listener as the canonical "wake EOS up" entry point — and a
    # voice session is conceptually another bounded activation.
    #
    # All session lifecycle, validation, and persistence stays in
    # runtime.transport.voice_session. Removing this method leaves the
    # listener exactly as it was.

    def start_voice_session(
        self,
        node_id: str,
        role_slug: str = "ea_orchestrator",
        *,
        metadata: Optional[dict] = None,
        use_eos_responder: bool = False,
    ):
        """Start a bounded voice session on `node_id` with `role_slug`.

        Returns the VoiceSession (always — failures are persisted as ERROR
        sessions, exactly like LocalTrigger ERROR statuses). Never raises.

        If `use_eos_responder=True`, lazily installs the EOS-backed
        responder via `voice_eos_responder.install_default_eos_voice_responder`
        before starting the session. This is idempotent — multiple calls
        with the flag are safe and only install once.
        """
        try:
            from runtime.transport.voice_session import VoiceSessionRuntime
        except Exception as e:  # noqa: BLE001
            _log(f"voice_session module unavailable: {e}")
            return None

        if use_eos_responder:
            try:
                from runtime.transport.voice_eos_responder import (
                    install_default_eos_voice_responder,
                )

                install_default_eos_voice_responder()
            except Exception as e:  # noqa: BLE001
                # Best-effort: fall through to the stub responder so the
                # session still works rather than failing the operator.
                _log(f"eos voice responder install failed (using stub): {e}")

        try:
            return VoiceSessionRuntime().start_session(
                node_id=node_id,
                role_slug=role_slug,
                metadata=metadata,
            )
        except Exception as e:  # noqa: BLE001
            _log(f"start_voice_session failed for {node_id}: {e}")
            return None

    # — internal —————————————————————————————————————————————————

    def _activate(self, trigger: LocalTrigger) -> None:
        # 1. Node must exist in registry. Don't auto-create — that would let a
        #    trigger materialize fake nodes and confuse readiness.
        try:
            node = NodeRegistry.default().get(trigger.node_id)
        except Exception as e:  # noqa: BLE001
            trigger.status = TriggerStatus.SKIPPED
            trigger.decision_reason = f"node lookup failed: {e}"
            return

        if node is None:
            trigger.status = TriggerStatus.SKIPPED
            trigger.decision_reason = f"node {trigger.node_id!r} not registered"
            return

        # 2. Don't double-fire if there's already an active open_day for any
        #    node. Active rituals are global; the registry tracks the few that
        #    matter, and re-entering would corrupt outputs.
        try:
            from runtime.transport.rituals import (
                RitualKind,
            )  # local import: keep top-level minimal

            active = RitualRegistry.default().active()
            for r in active:
                if r.kind == RitualKind.OPEN_DAY and not r.is_terminal():
                    trigger.status = TriggerStatus.SKIPPED
                    trigger.decision_reason = (
                        f"open_day already active ritual_id={r.ritual_id}"
                    )
                    return
        except Exception as e:  # noqa: BLE001
            _log(f"active-ritual check failed (continuing): {e}")

        # 3. Readiness gate. UNAVAILABLE → skip safely. DEGRADED is allowed
        #    through because scene_policy will downgrade to operator_mode.
        try:
            readiness = station_readiness(trigger.node_id)
            if readiness.classification == UNAVAILABLE:
                trigger.status = TriggerStatus.SKIPPED
                trigger.decision_reason = (
                    f"readiness UNAVAILABLE: {'; '.join(readiness.reasons[:2])}"
                )
                return
        except Exception as e:  # noqa: BLE001
            _log(f"readiness check failed (continuing): {e}")

        # 4. Build a minimal RitualPolicy. We pass requested_mode through
        #    open_scene; ritual_body's existing inference path will run when
        #    requested_mode is None. We DO NOT set open_speak here — the
        #    listener carries activation intent, not user-visible content.
        policy = RitualPolicy(
            station_node_id=trigger.node_id,
            open_scene=trigger.requested_mode,
            require_online=False,
        )

        try:
            ritual_id = start_open_day(policy=policy)
        except Exception as e:  # noqa: BLE001
            trigger.status = TriggerStatus.ERROR
            trigger.decision_reason = f"start_open_day failed: {e}"
            return

        trigger.ritual_id = ritual_id
        trigger.status = TriggerStatus.ACCEPTED

        # Pull a short reason from the ritual body output for observability.
        try:
            ritual = RitualRegistry.default().get(ritual_id)
            if ritual is not None:
                body = ritual.outputs.get("body_actions", [])
                decision = next(
                    (b for b in body if b.get("kind") == "scene_decision"), None
                )
                if decision:
                    trigger.decision_reason = (
                        f"scene_decision: {decision.get('detail')}"
                    )
                else:
                    trigger.decision_reason = (
                        "ritual started; no scene_decision recorded"
                    )
        except Exception as e:  # noqa: BLE001
            _log(f"post-start introspection failed: {e}")


# ─── Reporting helper (used by substrate_drain_station --report) ──────────────


def listener_report(node_id: Optional[str] = None, limit: int = 5) -> dict:
    """Compact report block describing recent listener activity."""
    history = get_trigger_history()
    recent = history.latest(limit=limit, node_id=node_id)
    last_accepted = next((e for e in recent if e.get("status") == "accepted"), None)
    return {
        "recent_triggers": recent,
        "last_activation": last_accepted,
        "count": len(recent),
    }
