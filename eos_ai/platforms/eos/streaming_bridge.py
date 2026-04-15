"""
StreamingBridge — real-time execution narration for the immersive runtime.

Bridges execution events into human-consumable feedback: TTS speech,
Discord messages, and live session attachment.  Every action in the system
can emit a streaming event and the bridge routes it to all active outputs.

Design rules:
- Additive only.  Removing this file leaves the platform intact.
- Best-effort.  TTS and Discord failures are logged, never raised.
- Non-blocking.  TTS runs in a background thread; callers never wait.
- Interruptible.  cancel_speech() stops current TTS immediately.
- Observable.  All events stored in a bounded ring buffer for replay.
"""

from __future__ import annotations

import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


# ─── Constants ──────────────────────────────────────────────────────────────

_MAX_EVENT_HISTORY = 200


def _log(msg: str) -> None:
    print(f"[platform.eos.streaming_bridge] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "se") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Event Types ────────────────────────────────────────────────────────────


class StreamEventType(str, Enum):
    """Categories of streaming execution events."""

    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    ACTION_EXECUTED = "action_executed"
    ACTION_RESULT = "action_result"
    ERROR = "error"
    COMPLETED = "completed"
    INFO = "info"


# ─── Event Dataclass ────────────────────────────────────────────────────────


@dataclass
class StreamEvent:
    """A single streaming execution event."""

    event_id: str
    event_type: StreamEventType
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    session_id: Optional[str] = None
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "message": self.message,
            "payload": self.payload,
            "source": self.source,
            "session_id": self.session_id,
            "created_at": self.created_at,
        }


# ─── TTS Engine Wrapper ────────────────────────────────────────────────────


class _TTSEngine:
    """Non-blocking, interruptible TTS wrapper.

    Uses pyttsx3 (local) with espeak fallback.  Speech runs in a
    background thread so callers never block.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._speaking = threading.Event()
        self._cancel_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._engine: Any = None
        self._engine_ready = False

    def _ensure_engine(self) -> bool:
        """Lazily init pyttsx3.  Returns True if ready."""
        if self._engine_ready:
            return True
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 175)
            self._engine_ready = True
            return True
        except Exception as exc:
            _log(f"pyttsx3 init failed: {exc}")
            self._engine = None
            self._engine_ready = False
            return False

    def speak(self, text: str) -> None:
        """Speak text in a background thread.  Non-blocking."""
        if not text or not text.strip():
            return

        self._cancel_flag.clear()

        def _run() -> None:
            self._speaking.set()
            try:
                if self._cancel_flag.is_set():
                    return
                if self._ensure_engine():
                    self._engine.say(text)
                    self._engine.runAndWait()
                else:
                    self._speak_espeak(text)
            except Exception as exc:
                _log(f"TTS speak error: {exc}")
            finally:
                self._speaking.clear()

        with self._lock:
            # Cancel any in-flight speech first
            if self._speaking.is_set():
                self.cancel()
            self._thread = threading.Thread(target=_run, daemon=True)
            self._thread.start()

    def _speak_espeak(self, text: str) -> None:
        """Fallback: use espeak subprocess."""
        import shutil
        import subprocess

        espeak = shutil.which("espeak") or shutil.which("espeak-ng")
        if not espeak:
            _log("no TTS engine available (pyttsx3 + espeak both missing)")
            return
        try:
            subprocess.run(
                [espeak, text],
                capture_output=True,
                timeout=30,
            )
        except Exception as exc:
            _log(f"espeak fallback failed: {exc}")

    def cancel(self) -> None:
        """Cancel current speech immediately."""
        self._cancel_flag.set()
        if self._engine_ready and self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._speaking.clear()

    @property
    def is_speaking(self) -> bool:
        """True if TTS is currently producing audio."""
        return self._speaking.is_set()


# ─── StreamingBridge ────────────────────────────────────────────────────────


class StreamingBridge:
    """Singleton event bridge for real-time execution narration.

    Accepts events from execution_bridge, pipeline_execution, browser_agent,
    and os_controller.  Routes each event to:
    1. TTS (non-blocking, interruptible)
    2. Discord (optional, best-effort)
    3. Live session attachment
    4. Subscriber callbacks
    5. Internal ring buffer for replay
    """

    _default: Optional["StreamingBridge"] = None
    _default_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tts = _TTSEngine()
        self._history: deque[StreamEvent] = deque(maxlen=_MAX_EVENT_HISTORY)
        self._subscribers: list[Callable[[StreamEvent], None]] = []
        self._discord_enabled = False
        self._tts_enabled = True
        self._session_id: Optional[str] = None

    # ── Singleton ────────────────────────────────────────────────────────

    @classmethod
    def default(cls) -> "StreamingBridge":
        """Return the process-wide singleton."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down singleton for test isolation."""
        with cls._default_lock:
            if cls._default is not None:
                cls._default._tts.cancel()
            cls._default = None

    # ── Configuration ────────────────────────────────────────────────────

    def set_session(self, session_id: Optional[str]) -> None:
        """Bind events to a live session."""
        with self._lock:
            self._session_id = session_id

    def set_discord_enabled(self, enabled: bool) -> None:
        """Toggle Discord forwarding."""
        with self._lock:
            self._discord_enabled = enabled

    def set_tts_enabled(self, enabled: bool) -> None:
        """Toggle TTS narration."""
        with self._lock:
            self._tts_enabled = enabled

    def subscribe(self, callback: Callable[[StreamEvent], None]) -> None:
        """Register a callback for all future events."""
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[StreamEvent], None]) -> None:
        """Remove a previously registered callback."""
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s != callback]

    # ── Core: stream_event ───────────────────────────────────────────────

    def stream_event(
        self,
        event_type: StreamEventType,
        message: str,
        *,
        payload: dict[str, Any] | None = None,
        source: str = "",
        speak: bool = True,
    ) -> StreamEvent:
        """Emit a streaming event to all outputs.

        Args:
            event_type: Category of the event.
            message: Human-readable narration text.
            payload: Optional structured data.
            source: Component that generated the event.
            speak: If True and TTS is enabled, narrate via TTS.

        Returns:
            The created StreamEvent.
        """
        event = StreamEvent(
            event_id=_new_id(),
            event_type=event_type,
            message=message,
            payload=payload or {},
            source=source,
            session_id=self._session_id,
        )

        with self._lock:
            self._history.append(event)
            subscribers = list(self._subscribers)

        _log(f"[{event_type.value}] {message}")

        # 1. TTS (non-blocking)
        if speak and self._tts_enabled:
            self._tts.speak(message)

        # 2. Discord (best-effort)
        if self._discord_enabled:
            self._forward_to_discord(event)

        # 3. Subscriber callbacks (best-effort)
        for cb in subscribers:
            try:
                cb(event)
            except Exception as exc:
                _log(f"subscriber callback error: {exc}")

        return event

    def _forward_to_discord(self, event: StreamEvent) -> None:
        """Best-effort Discord forwarding."""
        try:
            import os

            webhook_url = os.getenv("DISCORD_STREAMING_WEBHOOK")
            if not webhook_url:
                return

            import json
            import urllib.request

            data = json.dumps(
                {
                    "content": f"**[{event.event_type.value}]** {event.message}",
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as exc:
            _log(f"discord forward failed: {exc}")

    # ── TTS Control ──────────────────────────────────────────────────────

    def cancel_speech(self) -> None:
        """Cancel current TTS playback immediately."""
        self._tts.cancel()

    @property
    def is_speaking(self) -> bool:
        """True if TTS is currently producing audio."""
        return self._tts.is_speaking

    # ── History ──────────────────────────────────────────────────────────

    def recent_events(self, limit: int = 20) -> list[StreamEvent]:
        """Return the most recent events from the ring buffer."""
        with self._lock:
            items = list(self._history)
        return items[-limit:]

    def events_since(self, event_id: str) -> list[StreamEvent]:
        """Return all events after the given event_id."""
        with self._lock:
            items = list(self._history)
        found = False
        result: list[StreamEvent] = []
        for e in items:
            if found:
                result.append(e)
            elif e.event_id == event_id:
                found = True
        return result

    def clear_history(self) -> None:
        """Clear the event ring buffer."""
        with self._lock:
            self._history.clear()


# ─── Module-Level API ───────────────────────────────────────────────────────


def get_streaming_bridge() -> StreamingBridge:
    """Return the singleton StreamingBridge."""
    return StreamingBridge.default()


def stream_event(
    event_type: StreamEventType,
    message: str,
    *,
    payload: dict[str, Any] | None = None,
    source: str = "",
    speak: bool = True,
) -> StreamEvent:
    """Convenience: emit a streaming event via the singleton bridge."""
    return StreamingBridge.default().stream_event(
        event_type,
        message,
        payload=payload,
        source=source,
        speak=speak,
    )


def cancel_speech() -> None:
    """Cancel current TTS playback."""
    StreamingBridge.default().cancel_speech()


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = [
    "StreamEventType",
    "StreamEvent",
    "StreamingBridge",
    "get_streaming_bridge",
    "stream_event",
    "cancel_speech",
]
