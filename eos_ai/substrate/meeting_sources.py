"""
Meeting transcript SOURCE protocol + bounded fakes.

A "meeting source" is a PULL-style producer of utterances captured from a
meeting surface. The MeetingTransport can attach one or more sources and
periodically pump them; each utterance is then routed through the existing
bounded seam (transcript_inject → voice_session → responder → SPEAK_TEXT).

This file intentionally:
  - imports nothing from eos_ai's hot path
  - imports nothing from any real meeting SDK
  - defines a tiny duck-typed protocol so any future bridge can plug in
  - provides a deterministic FakeMeetingSource for tests
  - provides a LiveMeetingSourceStub wrapping a Callable for future bridges

A meeting source must expose:
    name: str
    provider: str
    read_utterance() -> Optional[dict]
    close() -> None

read_utterance() must NEVER raise. It returns either a dict shaped like
``{"text": str, "user_id": Optional[str], "participant_name": Optional[str],
"metadata": dict}`` or ``None`` when no utterance is currently available.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class MeetingSourceProtocol(Protocol):
    """Duck-typed contract for a meeting transcript source."""

    name: str
    provider: str

    def read_utterance(self) -> Optional[dict]: ...
    def close(self) -> None: ...


def is_meeting_source(obj: Any) -> bool:
    """Return True if `obj` quacks like a MeetingSourceProtocol.

    Cheap structural check — does NOT instantiate, does NOT call read_utterance.
    """
    if obj is None:
        return False
    if not hasattr(obj, "name") or not isinstance(getattr(obj, "name", None), str):
        return False
    if not hasattr(obj, "provider") or not isinstance(
        getattr(obj, "provider", None), str
    ):
        return False
    if not callable(getattr(obj, "read_utterance", None)):
        return False
    if not callable(getattr(obj, "close", None)):
        return False
    return True


class FakeMeetingSource:
    """Deterministic finite meeting source for tests.

    Pops one utterance per ``read_utterance()`` call from an internal deque.
    Returns ``None`` when empty. Thread-safe via an RLock. Never raises.
    """

    def __init__(
        self,
        name: str,
        provider: str = "fake",
        utterances: Optional[list[dict]] = None,
    ) -> None:
        self.name = str(name)
        self.provider = str(provider or "fake")
        self._lock = threading.RLock()
        self._queue: deque[dict] = deque(utterances or [])
        self._closed = False

    def read_utterance(self) -> Optional[dict]:
        with self._lock:
            if self._closed or not self._queue:
                return None
            try:
                u = self._queue.popleft()
            except IndexError:
                return None
            if not isinstance(u, dict):
                return None
            text = u.get("text")
            if not isinstance(text, str) or not text.strip():
                return None
            return {
                "text": text,
                "user_id": u.get("user_id"),
                "participant_name": u.get("participant_name"),
                "metadata": dict(u.get("metadata") or {}),
            }

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._queue.clear()

    def extend(self, utterances: list[dict]) -> None:
        """Test helper: append more utterances to the queue."""
        with self._lock:
            for u in utterances:
                if isinstance(u, dict):
                    self._queue.append(u)


class LiveMeetingSourceStub:
    """Wraps a Callable[[], Optional[dict]] as a meeting source.

    Designed for future real bridges (Google Meet captions WebSocket, Zoom
    webhook fan-out, etc.) — the bridge supplies a hook that returns the
    next utterance dict (or None). If the hook raises, the stub swallows
    the exception, records ``last_error``, and returns None.
    """

    def __init__(
        self,
        name: str,
        provider: str,
        hook: Callable[[], Optional[dict]],
    ) -> None:
        self.name = str(name)
        self.provider = str(provider or "generic_meeting")
        self._hook = hook
        self._lock = threading.RLock()
        self._closed = False
        self.last_error: Optional[str] = None

    def read_utterance(self) -> Optional[dict]:
        with self._lock:
            if self._closed:
                return None
        try:
            u = self._hook()
        except Exception as e:  # noqa: BLE001
            with self._lock:
                self.last_error = str(e)
            return None
        if u is None:
            return None
        if not isinstance(u, dict):
            return None
        text = u.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        return {
            "text": text,
            "user_id": u.get("user_id"),
            "participant_name": u.get("participant_name"),
            "metadata": dict(u.get("metadata") or {}),
        }

    def close(self) -> None:
        with self._lock:
            self._closed = True


__all__ = [
    "MeetingSourceProtocol",
    "is_meeting_source",
    "FakeMeetingSource",
    "LiveMeetingSourceStub",
]
