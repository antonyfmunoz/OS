"""
Wake producer — bounded wake-word / clap activation layer for the substrate.

Purpose
-------
Sits one level above `local_listener` and `voice_session`. A wake producer
converts a *bounded signal* (wake-word detected, clap detected) into the
existing substrate activation primitives:

    wake word on node
        → resume active voice session if one exists (SYSTEM audit marker only)
        → else start a new voice session on that node with a role hint

    clap on node
        → emit a CLAP_DETECTED trigger through LocalListener (bounded path)

Real audio frameworks plug in later as producers of these bounded events.
This module owns no audio framework, no DSP, no STT, no freeform parsing.
It is a tiny deterministic bridge between (wake phrase / clap) and the
already-bounded activation paths.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path never imported.
- Best-effort. submit() never raises into the caller; failures degrade into
  a recorded WakeProducerEvent with action_taken="skipped" and a reason.
- Bounded. Producer kinds and action_taken values come from a tiny closed set.
  No freeform commands. No raw shell. No auto-submitted utterances.
- Deterministic. Role hints resolved via a tiny static dict. No NLP.
- Observable. Every event is recorded in a ring buffer persisted via substrate
  storage (key: "wake_producer_events"), capped at RETENTION_MAX entries.
- Reversible. Removing this file leaves the substrate exactly as it was; no
  other module imports from it.

Confirmed behavior (wake word on an already-active voice session)
-----------------------------------------------------------------
OPTION 2: resume the existing voice session, append a bounded SYSTEM turn
("wake: <phrase>" / "wake_detected"). DO NOT auto-submit an utterance, DO NOT
invoke the responder, DO NOT widen behavior beyond resume + transcript marker.

The SYSTEM turn is metadata / audit only, not semantic user input.

What this module does NOT do
----------------------------
- No real STT. No real wake-word engine dependency by default.
- No clap DSP framework.
- No freeform commands.
- No Discord / meeting transports.
- No new station ActionKinds.
- No hot-path edits.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Optional

from execution.transport.local_listener import (
    LocalListener,
    LocalTrigger,
    TriggerKind,
    TriggerStatus,
)
from execution.transport.storage import get_storage
from execution.transport.voice_session import (
    VoiceSession,
    VoiceSessionRuntime,
    VoiceSessionStatus,
    VoiceTurn,
    VoiceTurnSource,
    get_voice_session_store,
)

STORAGE_KEY = "wake_producer_events"
RETENTION_MAX = 200


def _log(msg: str) -> None:
    print(f"[substrate.wake_producer] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "wp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Model ────────────────────────────────────────────────────────────────────


class WakeProducerKind(str, Enum):
    """Bounded set of wake producer signals."""

    WAKE_WORD = "wake_word"
    CLAP = "clap"


# Tiny deterministic phrase → role slug mapping. No NLP, no fuzzy matching.
# A phrase matches if any key appears as a substring (case-insensitive).
WAKE_PHRASE_ROLE_HINTS: dict[str, str] = {
    "ceo": "ceo",
    "portfolio": "portfolio_advisor",
    "ea": "ea_orchestrator",
    "orchestrator": "ea_orchestrator",
}


def resolve_role_hint(phrase: Optional[str]) -> Optional[str]:
    """Deterministic phrase → role slug mapping. Tiny, no NLP."""
    if not phrase:
        return None
    p = phrase.lower()
    for needle, role in WAKE_PHRASE_ROLE_HINTS.items():
        if needle in p:
            return role
    return None


@dataclass
class WakeProducerEvent:
    """A single bounded wake producer event.

    `action_taken` is constrained to a small set of strings:
      - "start_voice_session"
      - "resume_voice_session"
      - "open_day"
      - "skipped"
    """

    node_id: str
    producer_kind: WakeProducerKind
    detected_phrase: Optional[str] = None
    confidence: Optional[float] = None
    role_hint: Optional[str] = None
    action_taken: str = "skipped"
    decision_reason: str = ""
    voice_session_id: Optional[str] = None
    local_trigger_id: Optional[str] = None
    issued_by: str = "wake_producer"
    event_id: str = field(default_factory=lambda: _new_id("wp"))
    occurred_at: str = field(default_factory=_utcnow)
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["producer_kind"] = self.producer_kind.value
        return d


# ─── History store (substrate-storage backed, ring buffered) ──────────────────


class WakeProducerHistory:
    """Bounded persistent history of wake producer events.

    Mirrors TriggerHistory exactly: substrate KV, ring buffer at RETENTION_MAX,
    thread-safe, best-effort.
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

    def record(self, event: WakeProducerEvent) -> None:
        with self._lock:
            try:
                events = self._load()
                events.append(event.as_dict())
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


_history_singleton: Optional[WakeProducerHistory] = None


def get_wake_producer_history() -> WakeProducerHistory:
    global _history_singleton
    if _history_singleton is None:
        _history_singleton = WakeProducerHistory()
    return _history_singleton


# ─── Runtime ──────────────────────────────────────────────────────────────────


class WakeProducerRuntime:
    """Bounded wake producer runtime.

    TODO / provider seam:
        Real wake-word engines (Porcupine, openWakeWord) and real clap
        detectors plug in here as *producers* that call `submit(...)` with
        a pre-built WakeProducerEvent shell or via the simulate_* helpers.
        This runtime intentionally owns no audio framework.
    """

    runtime_mode = "simulated"

    def __init__(
        self,
        listener: Optional[LocalListener] = None,
        voice_runtime: Optional[VoiceSessionRuntime] = None,
        history: Optional[WakeProducerHistory] = None,
    ) -> None:
        self._listener = listener or LocalListener()
        self._voice = voice_runtime or VoiceSessionRuntime()
        self._history = history or get_wake_producer_history()

    # — simulators —————————————————————————————————————————————————

    def simulate_wake_word(
        self,
        node_id: str,
        phrase: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[dict] = None,
        issued_by: str = "wake_producer_sim",
    ) -> WakeProducerEvent:
        shell = WakeProducerEvent(
            node_id=node_id,
            producer_kind=WakeProducerKind.WAKE_WORD,
            detected_phrase=phrase,
            confidence=confidence,
            issued_by=issued_by,
            metadata=dict(metadata or {}),
        )
        return self.submit(shell)

    def simulate_clap(
        self,
        node_id: str,
        confidence: Optional[float] = None,
        metadata: Optional[dict] = None,
        issued_by: str = "wake_producer_sim",
    ) -> WakeProducerEvent:
        shell = WakeProducerEvent(
            node_id=node_id,
            producer_kind=WakeProducerKind.CLAP,
            confidence=confidence,
            issued_by=issued_by,
            metadata=dict(metadata or {}),
        )
        return self.submit(shell)

    # — core dispatch —————————————————————————————————————————————

    def submit(self, event: WakeProducerEvent) -> WakeProducerEvent:
        """Dispatch a wake producer event. Never raises."""
        try:
            if event.producer_kind == WakeProducerKind.WAKE_WORD:
                self._handle_wake_word(event)
            elif event.producer_kind == WakeProducerKind.CLAP:
                self._handle_clap(event)
            else:
                event.action_taken = "skipped"
                event.decision_reason = f"unknown producer_kind {event.producer_kind!r}"
        except Exception as e:  # noqa: BLE001
            event.action_taken = "skipped"
            event.decision_reason = f"unexpected: {e}"
            _log(f"submit error for {event.event_id}: {e}")
        finally:
            self._history.record(event)
            # Operator state engine: best-effort observation. Never raises.
            try:
                from execution.transport.operator_transitions import apply_wake_event

                apply_wake_event(event)
            except Exception as e:  # noqa: BLE001
                _log(f"operator_state apply_wake_event failed: {e}")
            # Audio loop: mark node as primed so downstream transcript
            # injection / STT can land in a coherent window. Best-effort.
            try:
                if event.action_taken in (
                    "start_voice_session",
                    "resume_voice_session",
                    "open_day",
                ):
                    from execution.transport.audio_loop import mark_primed

                    mark_primed(
                        event.node_id,
                        wake_event_id=event.event_id,
                        voice_session_id=event.voice_session_id,
                    )
            except Exception as e:  # noqa: BLE001
                _log(f"audio_loop mark_primed failed: {e}")
        return event

    # — wake word path ————————————————————————————————————————————

    def _handle_wake_word(self, event: WakeProducerEvent) -> None:
        # 1. Check for an active voice session on this node.
        active: list[VoiceSession] = []
        try:
            active = get_voice_session_store().active(node_id=event.node_id)
        except Exception as e:  # noqa: BLE001
            _log(f"active-session lookup failed (continuing): {e}")

        if active:
            # OPTION 2: resume existing session, SYSTEM audit marker only.
            session = active[0]
            event.voice_session_id = session.session_id
            event.action_taken = "resume_voice_session"
            event.decision_reason = f"active voice session {session.session_id} resumed"
            marker_text = (
                f"wake: {event.detected_phrase}"
                if event.detected_phrase
                else "wake_detected"
            )
            try:
                # If session had gone IDLE, flip it back to ACTIVE.
                if session.status == VoiceSessionStatus.IDLE:
                    session.status = VoiceSessionStatus.ACTIVE
                session.append_turn(
                    VoiceTurn(
                        turn_id=_new_id("vt"),
                        source=VoiceTurnSource.SYSTEM,
                        text=marker_text,
                        occurred_at=_utcnow(),
                        role_slug=session.role_slug,
                        metadata={
                            "wake_event_id": event.event_id,
                            "wake_kind": WakeProducerKind.WAKE_WORD.value,
                        },
                    )
                )
                get_voice_session_store().put(session)
            except Exception as e:  # noqa: BLE001
                _log(f"append SYSTEM wake marker failed for {session.session_id}: {e}")
                event.decision_reason = (
                    f"resume_voice_session (marker append failed: {e})"
                )
            # DO NOT call responder. DO NOT submit utterance.
            return

        # 2. No active session → resolve role hint and start a fresh one.
        role_slug = resolve_role_hint(event.detected_phrase) or "ea_orchestrator"
        event.role_hint = role_slug

        meta = dict(event.metadata)
        meta.update(
            {
                "wake_event_id": event.event_id,
                "wake_phrase": event.detected_phrase,
                "wake_kind": WakeProducerKind.WAKE_WORD.value,
            }
        )
        try:
            session = self._voice.start_session(
                node_id=event.node_id,
                role_slug=role_slug,
                metadata=meta,
            )
        except Exception as e:  # noqa: BLE001
            event.action_taken = "skipped"
            event.decision_reason = f"start_session crashed: {e}"
            return

        if session is None:
            event.action_taken = "skipped"
            event.decision_reason = "voice runtime returned None"
            return

        event.voice_session_id = session.session_id
        if session.status == VoiceSessionStatus.ERROR:
            event.action_taken = "skipped"
            event.decision_reason = (
                f"voice session ERROR: {session.error_reason or 'unknown'}"
            )
            return

        event.action_taken = "start_voice_session"
        event.decision_reason = (
            f"started voice session {session.session_id} role={role_slug}"
        )

    # — clap path —————————————————————————————————————————————————

    def _handle_clap(self, event: WakeProducerEvent) -> None:
        meta = dict(event.metadata)
        meta.update(
            {
                "wake_event_id": event.event_id,
                "wake_kind": WakeProducerKind.CLAP.value,
            }
        )
        trigger = LocalTrigger(
            node_id=event.node_id,
            kind=TriggerKind.CLAP_DETECTED,
            metadata=meta,
            issued_by=event.issued_by,
        )
        try:
            result = self._listener.emit(trigger)
        except Exception as e:  # noqa: BLE001
            event.action_taken = "skipped"
            event.decision_reason = f"listener emit crashed: {e}"
            return

        event.local_trigger_id = result.trigger_id
        status = result.status
        if status == TriggerStatus.ACCEPTED:
            event.action_taken = "open_day"
            event.decision_reason = result.decision_reason or "open_day ritual started"
        else:
            event.action_taken = "skipped"
            event.decision_reason = (
                result.decision_reason or f"trigger status {status.value}"
            )

    # — reporting ——————————————————————————————————————————————————

    def report(self, node_id: Optional[str] = None, limit: int = 5) -> dict:
        recent = self._history.latest(limit=limit, node_id=node_id)
        last = recent[0] if recent else None
        by_kind: dict[str, int] = {}
        by_action: dict[str, int] = {}
        for e in recent:
            k = str(e.get("producer_kind") or "")
            a = str(e.get("action_taken") or "")
            by_kind[k] = by_kind.get(k, 0) + 1
            by_action[a] = by_action.get(a, 0) + 1
        return {
            "runtime_mode": self.runtime_mode,
            "node_id": node_id,
            "count": len(recent),
            "last_event": last,
            "recent_events": recent,
            "by_kind": by_kind,
            "by_action_taken": by_action,
        }


# ─── Singletons ───────────────────────────────────────────────────────────────


_runtime_singleton: Optional[WakeProducerRuntime] = None


def get_wake_producer_runtime() -> WakeProducerRuntime:
    global _runtime_singleton
    if _runtime_singleton is None:
        _runtime_singleton = WakeProducerRuntime()
    return _runtime_singleton


def reset_wake_producer_runtime_for_tests() -> None:
    """Test helper. Drops the singleton so a fresh runtime is built next call."""
    global _runtime_singleton
    _runtime_singleton = None


__all__ = [
    "WakeProducerKind",
    "WakeProducerEvent",
    "WakeProducerHistory",
    "WakeProducerRuntime",
    "WAKE_PHRASE_ROLE_HINTS",
    "resolve_role_hint",
    "get_wake_producer_history",
    "get_wake_producer_runtime",
    "reset_wake_producer_runtime_for_tests",
]
