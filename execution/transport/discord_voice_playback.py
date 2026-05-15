"""
Discord voice playback — bounded TTS adapter on top of the transport.

Purpose
-------
Take a single piece of EOS reply text and play it back into an attached
`discord.VoiceClient` in a bounded, observable, fail-safe way.

This module is the SECOND half of the Discord voice transport. The FIRST
half (discord_voice_transport.py) handles transcript ingestion only. This
module handles the OUTPUT side: bounded TTS playback.

Design rules
------------
1. Never raises. Every entry point returns a `PlaybackResult` dict.
2. Reuses `runtime.voice_engine.VoiceEngine.speak()` (lazy import) — no
   parallel TTS pipeline. If voice_engine isn't importable or returns
   nothing, we degrade to a structured "tts_unavailable" result.
3. Bounded queue: at most ONE item plays at a time per VoiceClient. New
   requests while busy are SKIPPED with a structured reason
   ("busy_skipped"). The transport stays responsive — no buffering
   storms, no background workers, no asyncio loops.
4. Bounded history ring (size 50) for observability. Operators can read
   recent playback attempts via `get_playback_history()`.
5. Safe when discord/py-cord, ffmpeg, or VoiceClient are absent. The
   adapter probes capability and returns "vc_unavailable" / "ffmpeg_missing"
   instead of crashing.
6. Transcript-only mode (no attached VC) ALWAYS works — this module is
   only consulted when a real VoiceClient is attached AND playback is
   explicitly enabled on the transport.

Trust posture
-------------
This module never executes voice as a command. Playback only renders text
that has already been emitted by the EOS responder via the existing
SPEAK_TEXT seam. No freeform spoken-command parsing happens here.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ─── Logging + clock ─────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[substrate.discord_voice_playback] {msg}", file=sys.stderr)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Capability probe ────────────────────────────────────────────────────────


def probe_playback_capability() -> dict[str, Any]:
    """Side-effect-free probe of playback dependencies."""
    out: dict[str, Any] = {
        "discord_lib_present": False,
        "voice_extras_present": False,
        "ffmpeg_present": False,
        "voice_engine_importable": False,
    }
    try:
        import discord  # type: ignore  # noqa: F401

        out["discord_lib_present"] = True
        try:
            from discord import FFmpegPCMAudio  # type: ignore  # noqa: F401
            from discord import VoiceClient  # type: ignore  # noqa: F401

            out["voice_extras_present"] = True
        except Exception:
            out["voice_extras_present"] = False
    except Exception:
        out["discord_lib_present"] = False

    out["ffmpeg_present"] = shutil.which("ffmpeg") is not None

    try:
        import importlib

        importlib.import_module("runtime.voice_engine")
        out["voice_engine_importable"] = True
    except Exception:
        out["voice_engine_importable"] = False

    return out


# ─── Models ──────────────────────────────────────────────────────────────────


@dataclass
class PlaybackResult:
    """Outcome of one bounded playback attempt."""

    status: str  # ok | busy_skipped | tts_unavailable | vc_unavailable |
    #                ffmpeg_missing | playback_error | empty_text | disabled
    detail: str = ""
    text_preview: str = ""
    audio_path: Optional[str] = None
    node_id: Optional[str] = None
    queued_depth: int = 0
    occurred_at: str = field(default_factory=_utcnow_iso)
    reason: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── Bounded history ring ────────────────────────────────────────────────────


_HISTORY_CAP = 50


class _PlaybackHistory:
    def __init__(self, cap: int = _HISTORY_CAP) -> None:
        self._lock = threading.RLock()
        self._rows: list[PlaybackResult] = []
        self._cap = cap

    def record(self, r: PlaybackResult) -> PlaybackResult:
        with self._lock:
            self._rows.append(r)
            if len(self._rows) > self._cap:
                self._rows = self._rows[len(self._rows) - self._cap :]
        return r

    def latest(
        self, limit: int = 10, node_id: Optional[str] = None
    ) -> list[PlaybackResult]:
        with self._lock:
            rows = list(self._rows)
        if node_id is not None:
            rows = [r for r in rows if r.node_id == node_id]
        rows.sort(key=lambda r: r.occurred_at or "", reverse=True)
        return rows[: max(0, int(limit))]

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()


_history_singleton: Optional[_PlaybackHistory] = None
_history_lock = threading.Lock()


def get_playback_history() -> _PlaybackHistory:
    global _history_singleton
    if _history_singleton is None:
        with _history_lock:
            if _history_singleton is None:
                _history_singleton = _PlaybackHistory()
    return _history_singleton


def reset_playback_history_for_tests() -> None:
    global _history_singleton
    with _history_lock:
        _history_singleton = None


# ─── TTS rendering (lazy, bounded) ───────────────────────────────────────────


_MAX_TEXT_CHARS = 500


def _render_tts_to_wav(text: str) -> Optional[str]:
    """Render `text` to a WAV file. Returns path or None.

    Strategy:
      1. Try `runtime.voice_engine.VoiceEngine.speak()` (Coqui TTS → espeak).
      2. If that fails, try a direct espeak shell-out as a final fallback.
      3. Otherwise return None.

    Bounded to MAX_TEXT_CHARS. Never raises.
    """
    clean = (text or "").strip()[:_MAX_TEXT_CHARS]
    if not clean:
        return None

    # Primary: VoiceEngine.speak()
    try:
        from execution.voice.voice_engine import VoiceEngine  # type: ignore

        ve = VoiceEngine()
        path = ve.speak(clean)
        if path and os.path.exists(path):
            return path
    except Exception as e:  # noqa: BLE001
        _log(f"VoiceEngine.speak failed: {e}")

    # Final fallback: bare espeak
    try:
        if shutil.which("espeak") is None:
            return None
        out_path = tempfile.mktemp(suffix=".wav")
        result = subprocess.run(
            ["espeak", "-w", out_path, clean],
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0 and os.path.exists(out_path):
            return out_path
    except Exception as e:  # noqa: BLE001
        _log(f"espeak fallback failed: {e}")

    return None


# ─── Playback adapter (one per attached VoiceClient) ─────────────────────────


class DiscordVoicePlayback:
    """Bounded playback adapter for ONE attached VoiceClient.

    Lifecycle is owned by `DiscordVoiceTransport.attach_voice_client()`. The
    transport constructs / discards instances of this class as VoiceClients
    come and go. This class never starts background threads or event loops.
    """

    def __init__(self, *, node_id: Optional[str] = None) -> None:
        self.node_id = node_id
        self._lock = threading.RLock()
        self._voice_client: Any = None
        self._enabled: bool = False
        self._busy: bool = False
        self._last_result: Optional[PlaybackResult] = None
        self._attempt_count: int = 0

    # ── Attachment ─────────────────────────────────────────────────────────

    def attach(self, voice_client: Any, *, enabled: bool = True) -> None:
        with self._lock:
            self._voice_client = voice_client
            self._enabled = bool(enabled)

    def detach(self) -> None:
        with self._lock:
            self._voice_client = None
            self._enabled = False
            self._busy = False

    def is_attached(self) -> bool:
        with self._lock:
            return self._voice_client is not None

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled and self._voice_client is not None

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = bool(enabled)

    # ── Busy/idle state introspection ──────────────────────────────────────

    def busy(self) -> bool:
        """True if the attached VC is currently playing audio.

        Combines our own playback flag with the VC's `is_playing()` if it
        exposes one. Defensive against fakes that lack the method.
        """
        with self._lock:
            if self._busy:
                return True
            vc = self._voice_client
        if vc is None:
            return False
        try:
            is_playing = getattr(vc, "is_playing", None)
            if callable(is_playing) and is_playing():
                return True
        except Exception:
            return False
        return False

    # ── Core playback entry ────────────────────────────────────────────────

    def play_text(self, text: str) -> PlaybackResult:
        """Bounded entry: synthesize `text` and play it on the attached VC.

        Returns a PlaybackResult. Never raises. Every result is recorded in
        the playback history ring for observability.
        """
        preview = (text or "").strip()[:120]
        node_id = self.node_id

        # Disabled / unattached → no-op result.
        if not self.is_enabled():
            return get_playback_history().record(
                PlaybackResult(
                    status="disabled",
                    detail="playback disabled or no voice client attached",
                    text_preview=preview,
                    node_id=node_id,
                    reason="disabled_by_env",
                )
            )

        if not (text or "").strip():
            return get_playback_history().record(
                PlaybackResult(
                    status="empty_text",
                    detail="no text to speak",
                    text_preview=preview,
                    node_id=node_id,
                    reason="empty_text",
                )
            )

        # Busy guard — skip on overlap, structured reason.
        if self.busy():
            return get_playback_history().record(
                PlaybackResult(
                    status="busy_skipped",
                    detail="another utterance is already playing",
                    text_preview=preview,
                    node_id=node_id,
                    queued_depth=1,
                    reason="another_utterance_playing",
                )
            )

        # Render TTS to WAV.
        wav_path = _render_tts_to_wav(text)
        if not wav_path:
            return get_playback_history().record(
                PlaybackResult(
                    status="tts_unavailable",
                    detail="VoiceEngine + espeak both failed to render audio",
                    text_preview=preview,
                    node_id=node_id,
                    reason="tts_unavailable",
                )
            )

        # Play via the attached voice client.
        try:
            vc = self._voice_client

            # Build a source. Real py-cord: discord.FFmpegPCMAudio(path).
            # Fakes: any object exposing the path is fine; we hand it the path
            # via a dict so test fakes can introspect.
            source: Any
            try:
                from discord import FFmpegPCMAudio  # type: ignore

                if shutil.which("ffmpeg") is None:
                    return get_playback_history().record(
                        PlaybackResult(
                            status="ffmpeg_missing",
                            detail="ffmpeg not on PATH; cannot transcode WAV",
                            text_preview=preview,
                            audio_path=wav_path,
                            node_id=node_id,
                            reason="ffmpeg_missing",
                        )
                    )
                source = FFmpegPCMAudio(wav_path)
            except Exception:
                # Fake / test path: hand the raw path through.
                source = {"audio_path": wav_path}

            with self._lock:
                self._busy = True
                self._attempt_count += 1

            # Defensive: VC may not implement `play()` (e.g. some fakes).
            play_fn = getattr(vc, "play", None)
            if not callable(play_fn):
                with self._lock:
                    self._busy = False
                return get_playback_history().record(
                    PlaybackResult(
                        status="vc_unavailable",
                        detail="attached object has no play() method",
                        text_preview=preview,
                        audio_path=wav_path,
                        node_id=node_id,
                        reason="vc_unavailable",
                    )
                )

            # Optional after-callback so we know when playback finishes. py-cord
            # invokes this with an Optional[Exception]. Fakes may ignore it.
            def _after(err: Optional[BaseException] = None) -> None:
                with self._lock:
                    self._busy = False
                if err is not None:
                    _log(f"playback after-callback error: {err}")

            try:
                play_fn(source, after=_after)
            except TypeError:
                # Some fakes don't accept `after=`.
                try:
                    play_fn(source)
                    with self._lock:
                        self._busy = False
                except Exception as e:  # noqa: BLE001
                    with self._lock:
                        self._busy = False
                    return get_playback_history().record(
                        PlaybackResult(
                            status="playback_error",
                            detail=f"play() raised: {e}",
                            text_preview=preview,
                            audio_path=wav_path,
                            node_id=node_id,
                            reason="playback_error",
                        )
                    )

            result = PlaybackResult(
                status="ok",
                detail="dispatched to voice client",
                text_preview=preview,
                audio_path=wav_path,
                node_id=node_id,
                reason="ok",
            )
            with self._lock:
                self._last_result = result
            return get_playback_history().record(result)

        except Exception as e:  # noqa: BLE001
            with self._lock:
                self._busy = False
            return get_playback_history().record(
                PlaybackResult(
                    status="playback_error",
                    detail=f"unexpected: {e}",
                    text_preview=preview,
                    audio_path=wav_path,
                    node_id=node_id,
                    reason="playback_error",
                )
            )

    # ── Reporting snapshot ─────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "attached": self._voice_client is not None,
                "enabled": self._enabled,
                "busy": self.busy(),
                "attempt_count": self._attempt_count,
                "last_result": (
                    self._last_result.as_dict() if self._last_result else None
                ),
            }

    def playback_status_snapshot(self) -> dict[str, Any]:
        """Return the shared PlaybackStatusSnapshot shape as a dict.

        Transport-tagged "discord". Pulls from this adapter's own snapshot
        plus an aggregation of the bounded playback history ring filtered
        to this adapter's node_id. Never raises.
        """
        try:
            from execution.transport.playback_status import (
                aggregate_by_status,
                make_playback_status_snapshot,
            )

            snap = self.snapshot()
            attached = bool(snap.get("attached"))
            enabled = bool(snap.get("enabled"))
            busy = bool(snap.get("busy"))
            if attached and enabled:
                mode = "attached"
            elif attached:
                mode = "attached_degraded"
            else:
                mode = "transcript_only"

            recent_rows: list[dict] = []
            try:
                recent_rows = [
                    r.as_dict()
                    for r in get_playback_history().latest(
                        limit=50, node_id=self.node_id
                    )
                ]
            except Exception as e:  # noqa: BLE001
                _log(f"playback_status_snapshot history failed: {e}")

            by_status = aggregate_by_status(recent_rows)
            return make_playback_status_snapshot(
                transport="discord",
                mode=mode,
                attached=attached,
                enabled=enabled,
                busy=busy,
                depth=1 if busy else 0,
                max_depth=1,
                attempt_count=int(snap.get("attempt_count") or 0),
                by_status=by_status,
                last_result=snap.get("last_result"),
                recent=recent_rows[:10],
            ).as_dict()
        except Exception as e:  # noqa: BLE001
            _log(f"playback_status_snapshot failed: {e}")
            return {
                "transport": "discord",
                "mode": "transcript_only",
                "attached": False,
                "enabled": False,
                "busy": False,
                "depth": 0,
                "max_depth": 1,
                "attempt_count": 0,
                "by_status": {},
                "last_result": None,
                "recent": [],
            }


# ─── Env gate for the bot integration ────────────────────────────────────────


_PLAYBACK_ENV_VAR = "EOS_DISCORD_VOICE_PLAYBACK_ENABLED"


def playback_env_enabled() -> bool:
    val = os.getenv(_PLAYBACK_ENV_VAR, "").strip().lower()
    return val in ("1", "true", "yes", "on")


# === SHARED PLAYBACK STATUS CONTRACT (Subagent C) ===

# Canonical reason codes — used by Discord native playback AND by
# MeetingTransport.play_reply() normalization. Adding a new code here
# requires updating both sites.
PLAYBACK_REASONS: dict[str, str] = {
    "ok": "playback accepted",
    "queued": "accepted into bounded queue",
    "busy_skipped": "another utterance already playing and queue full",
    "tts_unavailable": "no usable TTS engine",
    "vc_unavailable": "no voice client / sink attached",
    "ffmpeg_missing": "ffmpeg not in PATH",
    "playback_error": "downstream playback raised",
    "empty_text": "no text to play",
    "disabled": "playback disabled by env or operator",
    "sink_error": "attached sink raised",
}


def normalize_playback_result(
    raw: Any,
    *,
    transport: str,
    text_preview: Optional[str] = None,
) -> dict[str, Any]:
    """Coerce any playback result into the canonical envelope.

    Canonical shape:
        {
          "transport": "discord" | "meeting" | "<other>",
          "status": <one of PLAYBACK_REASONS keys>,
          "reason": <human string>,
          "detail": <free-form>,
          "text_preview": <str or None>,
          "queued_depth": <int or None>,
          "occurred_at": <ISO-8601 UTC Z>,
        }

    Never raises. Unknown statuses fall through to "playback_error" with
    the original status preserved in detail.
    """
    envelope: dict[str, Any] = {
        "transport": str(transport or "unknown"),
        "status": "playback_error",
        "reason": PLAYBACK_REASONS["playback_error"],
        "detail": "",
        "text_preview": text_preview,
        "queued_depth": None,
        "occurred_at": _utcnow_iso(),
    }

    try:
        if isinstance(raw, PlaybackResult):
            raw = raw.as_dict()

        if raw is None:
            envelope["detail"] = "no result (None)"
            return envelope

        if isinstance(raw, BaseException):
            envelope["detail"] = f"{type(raw).__name__}: {raw}"
            return envelope

        if isinstance(raw, str):
            envelope["detail"] = f"raw string result: {raw}"
            return envelope

        if isinstance(raw, dict):
            status = str(raw.get("status") or "").strip()
            if status in PLAYBACK_REASONS:
                envelope["status"] = status
                envelope["reason"] = raw.get("reason") or PLAYBACK_REASONS[status]
                envelope["detail"] = raw.get("detail", "") or ""
            else:
                envelope["detail"] = (
                    f"unknown status '{status}': {raw.get('detail', '')}".strip()
                )
            qd = raw.get("queued_depth")
            if qd is not None:
                try:
                    envelope["queued_depth"] = int(qd)
                except Exception:
                    envelope["queued_depth"] = None
            if text_preview is None and raw.get("text_preview"):
                envelope["text_preview"] = raw.get("text_preview")
            if raw.get("occurred_at"):
                envelope["occurred_at"] = raw.get("occurred_at")
            return envelope

        envelope["detail"] = f"unknown result type: {type(raw).__name__}"
        return envelope
    except Exception as e:  # noqa: BLE001
        envelope["detail"] = f"normalize failed: {e}"
        return envelope


__all__ = [
    "DiscordVoicePlayback",
    "PlaybackResult",
    "PLAYBACK_REASONS",
    "normalize_playback_result",
    "probe_playback_capability",
    "get_playback_history",
    "reset_playback_history_for_tests",
    "playback_env_enabled",
]
