"""
Google Meet transcript SOURCE adapter.

First REAL provider adapter on top of the bounded MeetingSourceProtocol /
MeetingTransport seam. Transcript-only. Pull-based. Never raises.

Design intent
-------------
This adapter is intentionally pure: it does NOT spawn a browser, does NOT
hold a Playwright session, does NOT touch any meeting SDK. It is a branded,
mode-aware specialization of the existing LiveMeetingSourceStub contract.

Live transcript ingress is supplied by an *external* hook the operator (or
a future bridge) wires in. Acceptable hooks include:

  - a polling reader over a local file/socket fed by an out-of-process DOM
    scraper or caption-bridge process,
  - a webhook drainer over a bounded queue (Rev / Otter / third-party
    captioner relays),
  - a future in-process Playwright caption reader (env-gated, see below),
  - a deterministic FakeMeetingSource-style hook for tests.

The adapter exposes the *honest* state of attachment via ``mode`` so
operators and reports can tell live ingress apart from transcript-only
fallback without guessing.

Modes
-----
``unsupported``        no hook supplied AND env future-live disabled
``transcript_only``    no hook supplied (operator will inject manually)
``attached_degraded``  hook supplied but live future-live env not set
``attached_live``      hook supplied AND env ``EOS_GOOGLE_MEET_LIVE`` enabled

The adapter NEVER decides for itself that it is live; the operator opts in
via the env flag. This preserves the trust boundary: no uncontrolled
behavior, no surprise browser sessions.

Hot path
--------
This module imports nothing from eos_ai's hot path. It only depends on
``eos_ai.substrate.meeting_sources`` (the bounded protocol module).
"""

from __future__ import annotations

import os
import re
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from eos_ai.transport.meeting_sources import is_meeting_source

PROVIDER = "google_meet"

# Future-live env gate. When unset (default) a wired hook is reported as
# ``attached_degraded`` so operators know the bridge is unsupervised. When
# set to a truthy value the operator is explicitly accepting that the hook
# represents real Google Meet ingress.
LIVE_ENV_VAR = "EOS_GOOGLE_MEET_LIVE"

# Canonical Google Meet meeting code: three lowercase letters, dash, four,
# dash, three. e.g. ``abc-defg-hij``.
_MEET_CODE_RE = re.compile(r"([a-z]{3,4}-[a-z]{4}-[a-z]{3,4})", re.IGNORECASE)

_RECENT_EVENTS_CAP = 32


def _truthy_env(name: str) -> bool:
    val = os.environ.get(name, "")
    return val.strip().lower() in ("1", "true", "yes", "on")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_meet_url(url_or_code: Optional[str]) -> Optional[str]:
    """Extract a Google Meet meeting code from a URL or raw code.

    Returns the lowercase ``abc-defg-hij`` code, or ``None`` if no plausible
    code can be found. Never raises.

    Accepts:
      - ``https://meet.google.com/abc-defg-hij``
      - ``meet.google.com/abc-defg-hij?authuser=0``
      - ``abc-defg-hij``
    """
    if not isinstance(url_or_code, str):
        return None
    s = url_or_code.strip()
    if not s:
        return None
    # Strip query/fragment.
    s = s.split("?", 1)[0].split("#", 1)[0]
    m = _MEET_CODE_RE.search(s)
    if not m:
        return None
    return m.group(1).lower()


class GoogleMeetSource:
    """Real-provider transcript source for Google Meet.

    Implements MeetingSourceProtocol (duck-typed). Pull-only. Thread-safe.
    Never raises from ``read_utterance`` — hook errors are swallowed and
    recorded in ``last_error``.

    Construction is cheap and side-effect free; no network, no browser, no
    SDK. The optional ``hook`` is the only live-ingress seam.
    """

    def __init__(
        self,
        name: str,
        *,
        meeting_code: Optional[str] = None,
        meeting_url: Optional[str] = None,
        hook: Optional[Callable[[], Optional[dict]]] = None,
    ) -> None:
        self.name = str(name)
        self.provider = PROVIDER
        self._lock = threading.RLock()
        self._closed = False
        self._hook = hook
        self.meeting_code: Optional[str] = parse_meet_url(
            meeting_code
        ) or parse_meet_url(meeting_url)
        self.meeting_url: Optional[str] = (
            meeting_url
            if isinstance(meeting_url, str) and meeting_url.strip()
            else (
                f"https://meet.google.com/{self.meeting_code}"
                if self.meeting_code
                else None
            )
        )
        self.last_error: Optional[str] = None
        self.last_read_status: Optional[str] = (
            None  # "ok" | "empty" | "error" | "closed"
        )
        self.last_read_at: Optional[str] = None
        self.read_count: int = 0
        self.utterance_count: int = 0
        self._recent_events: deque[dict] = deque(maxlen=_RECENT_EVENTS_CAP)

    # ------------------------------------------------------------------
    # MeetingSourceProtocol
    # ------------------------------------------------------------------

    def read_utterance(self) -> Optional[dict]:
        with self._lock:
            if self._closed:
                self._record_event("read", status="closed")
                return None
            hook = self._hook
        if hook is None:
            with self._lock:
                self.last_read_status = "empty"
                self.last_read_at = _now_iso()
                self.read_count += 1
                self._record_event("read", status="empty", reason="no_hook")
            return None
        try:
            raw = hook()
        except Exception as e:  # noqa: BLE001
            with self._lock:
                self.last_error = str(e)
                self.last_read_status = "error"
                self.last_read_at = _now_iso()
                self.read_count += 1
                self._record_event("read", status="error", error=str(e))
            return None
        normalized = self._normalize(raw)
        with self._lock:
            self.last_read_at = _now_iso()
            self.read_count += 1
            if normalized is None:
                self.last_read_status = "empty"
                self._record_event("read", status="empty")
            else:
                self.last_read_status = "ok"
                self.utterance_count += 1
                self._record_event(
                    "read",
                    status="ok",
                    text_preview=normalized["text"][:80],
                    participant=normalized.get("participant_name"),
                )
        return normalized

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                self._record_event("close")

    # ------------------------------------------------------------------
    # Adapter-specific surface
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        """Honest attachment mode. See module docstring."""
        with self._lock:
            if self._closed:
                return "closed"
            if self._hook is None:
                # No live hook wired. We are still attachable for transcript-
                # only flows but cannot pump real ingress.
                if _truthy_env(LIVE_ENV_VAR):
                    return "unsupported"
                return "transcript_only"
            if _truthy_env(LIVE_ENV_VAR):
                return "attached_live"
            return "attached_degraded"

    def attach_hook(self, hook: Callable[[], Optional[dict]]) -> dict[str, Any]:
        """Wire a live transcript hook after construction.

        Returns a small JSON-friendly status dict. Never raises.
        """
        if not callable(hook):
            return {"status": "rejected", "reason": "hook_not_callable"}
        with self._lock:
            if self._closed:
                return {"status": "rejected", "reason": "closed"}
            self._hook = hook
            self._record_event("attach_hook", mode=self.mode)
            return {"status": "ok", "mode": self.mode}

    def detach_hook(self) -> dict[str, Any]:
        with self._lock:
            had = self._hook is not None
            self._hook = None
            self._record_event("detach_hook", had_hook=had)
            return {"status": "ok", "had_hook": had, "mode": self.mode}

    def status_snapshot(self) -> dict[str, Any]:
        """JSON-friendly snapshot for CLI/report surfaces."""
        with self._lock:
            return {
                "name": self.name,
                "provider": self.provider,
                "meeting_code": self.meeting_code,
                "meeting_url": self.meeting_url,
                "mode": self.mode,
                "hook_attached": self._hook is not None,
                "live_env_enabled": _truthy_env(LIVE_ENV_VAR),
                "closed": self._closed,
                "read_count": self.read_count,
                "utterance_count": self.utterance_count,
                "last_read_status": self.last_read_status,
                "last_read_at": self.last_read_at,
                "last_error": self.last_error,
                "recent_events": list(self._recent_events),
            }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _normalize(self, raw: Any) -> Optional[dict]:
        if raw is None or not isinstance(raw, dict):
            return None
        text = raw.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        meta = dict(raw.get("metadata") or {})
        # Stamp provider-specific metadata so downstream surfaces can tell
        # google_meet utterances apart from other providers.
        meta.setdefault("meeting_provider", PROVIDER)
        if self.meeting_code:
            meta.setdefault("google_meet_code", self.meeting_code)
        if self.meeting_url:
            meta.setdefault("google_meet_url", self.meeting_url)
        return {
            "text": text,
            "user_id": raw.get("user_id"),
            "participant_name": raw.get("participant_name"),
            "metadata": meta,
        }

    @classmethod
    def from_bridge(
        cls,
        name: str,
        *,
        meeting_code: str,
        root: Optional["Any"] = None,
        batch_size: int = 1,
        meeting_url: Optional[str] = None,
    ) -> "GoogleMeetSource":
        """Construct a GoogleMeetSource whose hook tails a JSONL caption bridge.

        The bridge is the canonical durable ingestion path written by
        ``meet_caption_bridge.CaptionWriter``. This classmethod wires a
        deduped, offset-based, bounded reader hook so the source can be
        attached to MeetingTransport via ``attach_source()``.

        Transcript-only fallback is preserved: if the bridge file doesn't
        exist yet, the hook simply returns None on each ``read_utterance``
        call and the source stays in its existing mode.
        """
        from eos_ai.transport.meet_caption_bridge import (  # local to avoid cycles
            make_bridge_hook,
        )

        hook = make_bridge_hook(
            meeting_code, root=root, batch_size=max(1, int(batch_size))
        )
        return cls(
            name,
            meeting_code=meeting_code,
            meeting_url=meeting_url,
            hook=hook,
        )

    def bridge_path(self) -> Optional[Any]:
        """Best-effort: returns the bridge JSONL path if this source is bridge-backed.

        Returns None if the source was not built from a bridge or if the
        meeting_code is unknown. Used by reporting surfaces to expose
        backlog/last-ingress info.
        """
        from eos_ai.transport.meet_caption_bridge import bridge_path_for

        if self.meeting_code is None:
            return None
        try:
            return bridge_path_for(self.meeting_code)
        except Exception:  # noqa: BLE001
            return None

    def _record_event(self, kind: str, **fields: Any) -> None:
        # Caller must hold self._lock.
        evt = {"at": _now_iso(), "kind": kind}
        evt.update(fields)
        self._recent_events.append(evt)


def is_google_meet_source(obj: Any) -> bool:
    """Convenience: structural + provider check."""
    return is_meeting_source(obj) and getattr(obj, "provider", None) == PROVIDER


__all__ = [
    "PROVIDER",
    "LIVE_ENV_VAR",
    "GoogleMeetSource",
    "parse_meet_url",
    "is_google_meet_source",
]
