"""
STT producer — bounded local speech-to-text capture layer.

Purpose
-------
This module is the first REAL local mic/STT producer for the substrate.
It gives an operator a bounded, explicit way to turn a short window of
microphone audio into a transcript that enters the existing voice loop
through the already-sanctioned seam:

    eos_ai.substrate.transcript_inject.inject_transcript(
        node_id, text, source="local_stt", ...)

Everything downstream (voice session, audio loop, operator state,
SPEAK_TEXT emission, EOS responder) is untouched. This module only
produces transcripts.

It is NOT:
  - a streaming STT pipeline
  - an always-on microphone daemon
  - a freeform spoken command parser
  - a parallel voice pipeline
  - a replacement for voice_session / audio_loop / wake_producer

Design rules (mirror the rest of substrate)
-------------------------------------------
- Hot path (gateway/cognitive_loop/model_router/agent_runtime/primitives)
  is never imported.
- Dependencies on real audio/STT libraries are OPTIONAL. Every import of
  sounddevice / faster_whisper / whisper happens lazily inside a
  function, inside try/except. If the environment is unsupported, the
  runtime reports it and the simulated path still works.
- Bounded. Capture window is explicit (duration_s), hard-capped.
- Best-effort. Public entry points never raise into the caller; they
  return an SttCaptureEvent with status and detail.
- Deterministic. Storage layout is a single keyed JSON blob
  ("stt_capture_events") on substrate.storage.
- Backward compatible. Removing this file and its smoke test leaves the
  substrate exactly as it was.

Public surface
--------------
Enums / dataclasses:
    SttCaptureSource        — enum of producer kinds
    SttCaptureStatus        — enum of event outcomes
    SttCaptureEvent         — one bounded capture/transcript record
    SttRuntimeCapability    — what providers / modes are usable

Runtime:
    LocalSttRuntime         — the bounded capture runtime
    get_local_stt_runtime() — singleton accessor
    reset_local_stt_runtime_for_tests()

History:
    SttCaptureHistory       — ring buffer of SttCaptureEvent
    get_stt_capture_history()
    reset_stt_capture_history_for_tests()

Reporting helpers (JSON-friendly; used by CLI + smoke test):
    stt_runtime_status()    — capability / readiness report
    stt_capture_snapshot()  — latest event per node (or all)
    recent_stt_captures()   — time-ordered history slice
"""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "stt_capture_events"
_RETENTION_MAX = 200
_MAX_CAPTURE_DURATION_S = 30.0
_DEFAULT_CAPTURE_DURATION_S = 4.0
_DEFAULT_SAMPLE_RATE = 16000
_DEFAULT_NODE_FALLBACK_ROLE = "ea_orchestrator"


# ─── Environment-variable knobs (workstation-facing) ─────────────────────────
#
# These are read once per call (not cached) so operators can flip them
# between CLI invocations without touching code. All are OPTIONAL; absent
# env vars fall back to the existing defaults / behavior.
#
#   STT_MODE                 override capture mode ("simulated"/"manual"/"push_to_talk")
#   STT_FORCE_SIMULATED      "1"/"true" → force push_to_talk down simulated path
#   STT_REAL_CAPTURE_ENABLED "false"/"0" → disable real mic capture entirely
#   STT_PROVIDER             "faster_whisper"/"whisper" → pin preferred provider
#   STT_MODEL_SIZE           whisper model size ("tiny"/"base"/"small"/...), default "base"
#   STT_SAMPLE_RATE          int override of default sample rate
#   STT_DEFAULT_DURATION_S   float override of default capture duration
#   STT_MAX_DURATION_S       float override of hard cap
#   STT_CAPTURE_TIMEOUT_S    float wall-clock timeout on sd.wait() (default 15s)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


def _env_float(name: str, default: float) -> float:
    try:
        raw = os.getenv(name)
        return float(raw) if raw is not None and raw.strip() else default
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        raw = os.getenv(name)
        return int(raw) if raw is not None and raw.strip() else default
    except Exception:
        return default


def _log(msg: str) -> None:
    print(f"[substrate.stt_producer] {msg}", file=sys.stderr)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "stt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Enums ────────────────────────────────────────────────────────────────────


class SttCaptureSource(str, Enum):
    """How the transcript for a capture event was produced."""

    MANUAL_CAPTURE = "manual_capture"  # text provided directly by operator
    PUSH_TO_TALK = "push_to_talk"  # bounded mic window, real STT
    SIMULATED_STT = "simulated_stt"  # bounded window, no real STT avail
    FUTURE_STT = "future_stt"  # reserved for later streaming path


class SttCaptureStatus(str, Enum):
    """Outcome of a capture attempt."""

    INJECTED = "injected"  # transcript reached voice loop
    SKIPPED_EMPTY = "skipped_empty"  # no text after capture
    SKIPPED_NO_SESSION = "skipped_no_session"  # start_if_missing=False, no session
    DEGRADED = "degraded"  # real STT unavailable, fell back
    UNSUPPORTED = "unsupported"  # capture impossible in this env
    ERROR = "error"  # exception during capture/transcribe


class SttWorkstationReadiness(str, Enum):
    """Workstation-facing readiness classification for real push-to-talk.

    Meant for operator UX: if the operator presses PTT *right now*, what
    will happen? This is coarser than SttRuntimeCapability and communicates
    an actionable state.

        REAL_READY         — mic + STT provider both present, real PTT will run
        REAL_CAPTURE_READY — mic present & STT provider present but never exercised
                             (alias of REAL_READY today; reserved for a future
                             health-check pass that can distinguish the two)
        DEGRADED           — one of {mic, provider} present, the other missing;
                             push_to_talk will fall through to DEGRADED event
        SIMULATED_ONLY     — neither mic nor provider present (headless VPS / CI)
        UNSUPPORTED        — environment explicitly forbids real capture
                             (STT_REAL_CAPTURE_ENABLED=false or STT_FORCE_SIMULATED=1)
    """

    REAL_READY = "real_ready"
    REAL_CAPTURE_READY = "real_capture_ready"
    DEGRADED = "degraded"
    SIMULATED_ONLY = "simulated_only"
    UNSUPPORTED = "unsupported"


# ─── Capture event dataclass ──────────────────────────────────────────────────


@dataclass
class SttCaptureEvent:
    node_id: str
    source: SttCaptureSource = SttCaptureSource.MANUAL_CAPTURE
    status: SttCaptureStatus = SttCaptureStatus.INJECTED
    text: str = ""
    confidence: Optional[float] = None
    duration_s: Optional[float] = None
    sample_rate: Optional[int] = None
    provider: Optional[str] = None  # "faster_whisper"|"whisper"|"simulated"|None
    session_id: Optional[str] = None  # downstream voice session
    role_slug: Optional[str] = None
    inject_status: Optional[str] = None  # raw status from inject_transcript
    detail: str = ""
    event_id: str = field(default_factory=lambda: _new_id("stt"))
    occurred_at: str = field(default_factory=_utcnow_iso)
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "node_id": self.node_id,
            "source": self.source.value,
            "status": self.status.value,
            "text": self.text,
            "confidence": self.confidence,
            "duration_s": self.duration_s,
            "sample_rate": self.sample_rate,
            "provider": self.provider,
            "session_id": self.session_id,
            "role_slug": self.role_slug,
            "inject_status": self.inject_status,
            "detail": self.detail,
            "occurred_at": self.occurred_at,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "SttCaptureEvent":
        def _enum(enum_cls, value, default):
            try:
                return enum_cls(value)
            except Exception:
                return default

        return cls(
            node_id=str(raw.get("node_id", "")),
            source=_enum(
                SttCaptureSource,
                raw.get("source"),
                SttCaptureSource.MANUAL_CAPTURE,
            ),
            status=_enum(
                SttCaptureStatus,
                raw.get("status"),
                SttCaptureStatus.INJECTED,
            ),
            text=str(raw.get("text") or ""),
            confidence=raw.get("confidence"),
            duration_s=raw.get("duration_s"),
            sample_rate=raw.get("sample_rate"),
            provider=raw.get("provider"),
            session_id=raw.get("session_id"),
            role_slug=raw.get("role_slug"),
            inject_status=raw.get("inject_status"),
            detail=str(raw.get("detail") or ""),
            event_id=str(raw.get("event_id") or _new_id("stt")),
            occurred_at=str(raw.get("occurred_at") or _utcnow_iso()),
            metadata=dict(raw.get("metadata") or {}),
        )


# ─── Capability probe ─────────────────────────────────────────────────────────


@dataclass
class SttRuntimeCapability:
    real_stt_available: bool
    simulated_only: bool
    unsupported: bool
    mic_available: bool
    providers_available: list[str]
    providers_missing: list[str]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "real_stt_available": self.real_stt_available,
            "simulated_only": self.simulated_only,
            "unsupported": self.unsupported,
            "mic_available": self.mic_available,
            "providers_available": list(self.providers_available),
            "providers_missing": list(self.providers_missing),
            "reason": self.reason,
        }


def _probe_capability() -> SttRuntimeCapability:
    """Best-effort introspection of what this environment can do.

    Never raises. Safe to call from anywhere.
    """
    providers_available: list[str] = []
    providers_missing: list[str] = []

    # faster_whisper — preferred (CPU int8 viable)
    try:
        import faster_whisper  # noqa: F401

        providers_available.append("faster_whisper")
    except Exception:
        providers_missing.append("faster_whisper")

    # openai-whisper — heavy fallback
    try:
        import whisper  # noqa: F401

        providers_available.append("whisper")
    except Exception:
        providers_missing.append("whisper")

    # mic capture lib
    mic_available = False
    try:
        import sounddevice  # noqa: F401

        mic_available = True
    except Exception:
        mic_available = False

    real_stt_available = mic_available and bool(providers_available)
    simulated_only = not real_stt_available
    unsupported = False  # simulated path always runs
    if real_stt_available:
        reason = f"real STT available via {providers_available[0]} + sounddevice"
    elif providers_available and not mic_available:
        reason = (
            f"provider {providers_available[0]} present but no sounddevice "
            f"— simulated path only"
        )
    elif mic_available and not providers_available:
        reason = "sounddevice present but no STT provider — simulated path only"
    else:
        reason = "no STT provider and no sounddevice — simulated path only"
    return SttRuntimeCapability(
        real_stt_available=real_stt_available,
        simulated_only=simulated_only,
        unsupported=unsupported,
        mic_available=mic_available,
        providers_available=providers_available,
        providers_missing=providers_missing,
        reason=reason,
    )


def _detect_environment() -> str:
    """Classify the current process environment. Never raises.

    Returns one of: 'ci' | 'docker' | 'cloud' | 'workstation_linux'
    | 'workstation_darwin' | 'workstation_windows' | 'unknown'.
    """
    try:
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or os.getenv("GITLAB_CI"):
            return "ci"
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            return "cloud"
        if Path("/.dockerenv").exists():
            return "docker"
        if sys.platform == "darwin":
            return "workstation_darwin"
        if sys.platform == "win32":
            return "workstation_windows"
        if sys.platform.startswith("linux"):
            # Treat headless linux (no /dev/snd) as 'cloud'-ish; workstation otherwise.
            if Path("/dev/snd").exists():
                return "workstation_linux"
            return "cloud"
    except Exception:
        pass
    return "unknown"


def _enumerate_input_devices() -> list[dict[str, Any]]:
    """List available input-capable audio devices. Lazy import; never raises.

    Returns a list of small JSON-friendly dicts. Empty list means either no
    sounddevice, no hostapi, or no input devices are visible.
    """
    try:
        import sounddevice as sd  # noqa: F401
    except Exception:
        return []
    try:
        raw = sd.query_devices()  # list of dicts
    except Exception as e:  # noqa: BLE001
        _log(f"query_devices failed: {e}")
        return []
    out: list[dict[str, Any]] = []
    try:
        default_input = None
        try:
            default_input = sd.default.device[0]  # (input, output)
        except Exception:
            default_input = None
        for idx, d in enumerate(raw):
            try:
                ch = int(d.get("max_input_channels", 0))
            except Exception:
                ch = 0
            if ch <= 0:
                continue
            out.append(
                {
                    "index": idx,
                    "name": str(d.get("name", "")),
                    "max_input_channels": ch,
                    "default_samplerate": d.get("default_samplerate"),
                    "hostapi": d.get("hostapi"),
                    "is_default": (default_input == idx),
                }
            )
    except Exception as e:  # noqa: BLE001
        _log(f"device enumeration failed: {e}")
    return out


def _validate_audio_quality(audio) -> tuple[bool, Optional[str], dict[str, Any]]:
    """Post-capture sanity check on recorded audio.

    Returns (is_valid, reason_if_invalid, stats_dict). Safe and lazy;
    never raises into caller. If validation itself fails, we pass the
    audio through (prefer real capture over false negatives).
    """
    stats: dict[str, Any] = {}
    try:
        import numpy as np

        arr = np.asarray(audio, dtype="float32").reshape(-1)
        stats["frames"] = int(arr.size)
        if arr.size == 0:
            return False, "empty_recording", stats
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            return False, "nan_or_inf_in_audio", stats
        # sounddevice int16 path — we normalize by 32768 for rms range compare
        norm = arr / 32768.0 if np.max(np.abs(arr)) > 1.5 else arr
        rms = float(np.sqrt(np.mean(norm**2)))
        peak = float(np.max(np.abs(norm)))
        stats["rms"] = rms
        stats["peak"] = peak
        if rms < 1e-5 and peak < 1e-4:
            return False, "all_silent_mic_muted_or_dead", stats
        return True, None, stats
    except Exception as e:  # noqa: BLE001
        _log(f"audio quality check errored (passing through): {e}")
        return True, None, stats


def stt_workstation_readiness() -> dict[str, Any]:
    """Operator-facing readiness summary for real push-to-talk.

    Answers the question: "If I press PTT right now on this workstation,
    what will happen, and if it won't work — what should I do?"

    Returns a JSON-friendly dict. Bounded; never raises.
    """
    environment = _detect_environment()
    cap = _probe_capability()

    # Env-based explicit disablement wins over raw capability.
    force_simulated = _env_flag("STT_FORCE_SIMULATED", False)
    real_enabled = not _env_flag(
        "STT_REAL_CAPTURE_ENABLED", True
    ) is False and not _env_flag("STT_FORCE_SIMULATED", False)
    # The above double-negative is deliberately explicit:
    real_enabled = (not force_simulated) and (
        os.getenv("STT_REAL_CAPTURE_ENABLED", "true").strip().lower() != "false"
    )

    devices = _enumerate_input_devices() if cap.mic_available else []
    default_device = next((d for d in devices if d.get("is_default")), None)

    def _actions(items: list[str]) -> list[str]:
        return [s for s in items if s]

    # Classify
    if not real_enabled:
        classification = SttWorkstationReadiness.UNSUPPORTED
        reason = (
            "real capture disabled by environment "
            "(STT_REAL_CAPTURE_ENABLED=false or STT_FORCE_SIMULATED=1)"
        )
        next_actions = _actions(
            [
                "unset STT_FORCE_SIMULATED to allow real push-to-talk",
                "set STT_REAL_CAPTURE_ENABLED=true to re-enable real capture",
            ]
        )
    elif cap.real_stt_available and devices:
        classification = SttWorkstationReadiness.REAL_READY
        reason = (
            f"mic + {cap.providers_available[0]} ready; "
            f"{len(devices)} input device(s) visible"
        )
        next_actions = _actions(
            [
                "press ptt: run `capture --mode push_to_talk --duration 4`",
            ]
        )
    elif cap.real_stt_available and not devices:
        # libs present but no device enumerated — treat as REAL_CAPTURE_READY
        # (the code path will work if a device appears; reserved for the
        # future health-check to demote this to DEGRADED when tested).
        classification = SttWorkstationReadiness.REAL_CAPTURE_READY
        reason = (
            f"mic lib + {cap.providers_available[0]} present, "
            "but no input devices were enumerable"
        )
        next_actions = _actions(
            [
                "check mic is plugged in / not claimed by another app",
                "on linux: verify `/dev/snd` is accessible (groups: audio)",
            ]
        )
    elif cap.providers_available and not cap.mic_available:
        classification = SttWorkstationReadiness.DEGRADED
        reason = (
            f"{cap.providers_available[0]} installed but sounddevice is missing — "
            "push_to_talk will return DEGRADED"
        )
        next_actions = _actions(
            [
                "pip install sounddevice",
                "on linux: apt install libportaudio2",
            ]
        )
    elif cap.mic_available and not cap.providers_available:
        classification = SttWorkstationReadiness.DEGRADED
        reason = (
            "sounddevice present but no STT provider — "
            "push_to_talk will return DEGRADED"
        )
        next_actions = _actions(
            [
                "pip install faster-whisper  # preferred",
                "pip install openai-whisper  # fallback",
            ]
        )
    else:
        classification = SttWorkstationReadiness.SIMULATED_ONLY
        reason = (
            "no mic library and no STT provider available — "
            "only simulated/manual modes usable"
        )
        next_actions = _actions(
            [
                "pip install sounddevice faster-whisper",
                "plug in a USB mic if this is a workstation",
            ]
        )

    return {
        "classification": classification.value,
        "reason": reason,
        "next_actions": next_actions,
        "environment": environment,
        "real_capture_enabled": real_enabled,
        "force_simulated": force_simulated,
        "devices": devices,
        "default_device": default_device,
        "capability": cap.as_dict(),
        "generated_at": _utcnow_iso(),
    }


def stt_runtime_status() -> dict[str, Any]:
    """JSON-friendly snapshot of STT capability + runtime state."""
    cap = _probe_capability()
    rt = get_local_stt_runtime()
    hist = get_stt_capture_history()
    return {
        "capability": cap.as_dict(),
        "readiness": stt_workstation_readiness(),
        "runtime": {
            "default_duration_s": rt.default_duration_s,
            "default_sample_rate": rt.default_sample_rate,
            "max_duration_s": _MAX_CAPTURE_DURATION_S,
        },
        "history": {
            "total": len(hist.latest(limit=_RETENTION_MAX)),
            "retention_max": _RETENTION_MAX,
        },
        "generated_at": _utcnow_iso(),
    }


# ─── History ring buffer (dual-layer) ─────────────────────────────────────────


class SttCaptureHistory:
    """Thread-safe ring buffer for SttCaptureEvent, mirrors WakeProducerHistory."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: list[SttCaptureEvent] = []
        self._loaded = False

    # --- lifecycle ---

    def _load(self) -> None:
        if self._loaded:
            return
        try:
            from eos_ai.substrate.storage import get_storage

            raw = get_storage().get(_STORAGE_KEY, default=[]) or []
            if isinstance(raw, list):
                self._events = [
                    SttCaptureEvent.from_dict(r) for r in raw if isinstance(r, dict)
                ]
        except Exception as e:  # noqa: BLE001
            _log(f"history load failed: {e}")
            self._events = []
        self._loaded = True

    def _flush(self) -> None:
        try:
            from eos_ai.substrate.storage import get_storage

            get_storage().put(_STORAGE_KEY, [e.as_dict() for e in self._events])
        except Exception as e:  # noqa: BLE001
            _log(f"history flush failed: {e}")

    # --- public ---

    def record(self, event: SttCaptureEvent) -> SttCaptureEvent:
        with self._lock:
            self._load()
            self._events.append(event)
            if len(self._events) > _RETENTION_MAX:
                self._events = self._events[-_RETENTION_MAX:]
            self._flush()
            return event

    def latest(
        self,
        limit: int = 20,
        node_id: Optional[str] = None,
    ) -> list[SttCaptureEvent]:
        with self._lock:
            self._load()
            pool = self._events
            if node_id:
                pool = [e for e in pool if e.node_id == node_id]
            return list(reversed(pool[-max(1, int(limit)) :]))

    def clear(self) -> None:
        with self._lock:
            self._events = []
            self._loaded = True
            self._flush()


_history_singleton: Optional[SttCaptureHistory] = None
_history_lock = threading.RLock()


def get_stt_capture_history() -> SttCaptureHistory:
    global _history_singleton
    with _history_lock:
        if _history_singleton is None:
            _history_singleton = SttCaptureHistory()
        return _history_singleton


def reset_stt_capture_history_for_tests() -> None:
    global _history_singleton
    with _history_lock:
        _history_singleton = SttCaptureHistory()
        try:
            from eos_ai.substrate.storage import get_storage

            get_storage().put(_STORAGE_KEY, [])
        except Exception as e:  # noqa: BLE001
            _log(f"history reset flush failed: {e}")


# ─── Capture runtime ──────────────────────────────────────────────────────────


class LocalSttRuntime:
    """Bounded local STT capture runtime.

    Three capture modes:
        capture_once(..., simulated_text=...)     → SIMULATED_STT
        capture_once(..., mode="manual", text=)   → MANUAL_CAPTURE
        capture_once(..., mode="push_to_talk")    → real mic + STT if avail
    """

    def __init__(
        self,
        default_duration_s: float = _DEFAULT_CAPTURE_DURATION_S,
        default_sample_rate: int = _DEFAULT_SAMPLE_RATE,
    ) -> None:
        self.default_duration_s = float(default_duration_s)
        self.default_sample_rate = int(default_sample_rate)

    # --- primary public API ---

    def capture_once(
        self,
        node_id: str,
        *,
        mode: str = "push_to_talk",
        duration_s: Optional[float] = None,
        simulated_text: Optional[str] = None,
        manual_text: Optional[str] = None,
        role_slug: str = _DEFAULT_NODE_FALLBACK_ROLE,
        start_if_missing: bool = True,
        device: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> SttCaptureEvent:
        """Perform one bounded capture. Never raises.

        Returns a recorded SttCaptureEvent. The event is pushed into
        SttCaptureHistory regardless of outcome.

        Environment overrides honored on every call (no caching):
          STT_MODE                 overrides the `mode` argument
          STT_FORCE_SIMULATED      coerces push_to_talk → simulated
          STT_REAL_CAPTURE_ENABLED false → coerces push_to_talk → simulated (+ UNSUPPORTED detail)
          STT_DEFAULT_DURATION_S   overrides duration fallback
          STT_MAX_DURATION_S       overrides hard cap
        """
        meta = dict(metadata or {})

        # ---- Env-var overrides ----
        env_mode = _env_str("STT_MODE")
        if env_mode in ("simulated", "manual", "push_to_talk"):
            meta["mode_override_env"] = env_mode
            mode = env_mode
        force_simulated = _env_flag("STT_FORCE_SIMULATED", False)
        real_capture_disabled = (
            os.getenv("STT_REAL_CAPTURE_ENABLED", "true").strip().lower() == "false"
        )
        if mode == "push_to_talk" and (force_simulated or real_capture_disabled):
            meta["coerced_from"] = "push_to_talk"
            meta["coerced_reason"] = (
                "STT_FORCE_SIMULATED=1"
                if force_simulated
                else "STT_REAL_CAPTURE_ENABLED=false"
            )
            mode = "simulated"

        env_default_duration = _env_float(
            "STT_DEFAULT_DURATION_S", self.default_duration_s
        )
        env_max_duration = _env_float("STT_MAX_DURATION_S", _MAX_CAPTURE_DURATION_S)
        duration = min(
            float(duration_s or env_default_duration),
            env_max_duration,
        )
        duration = max(0.0, duration)

        # ---- Manual mode: text supplied directly ----
        if mode == "manual" or manual_text is not None:
            text = (manual_text or "").strip()
            event = SttCaptureEvent(
                node_id=node_id,
                source=SttCaptureSource.MANUAL_CAPTURE,
                text=text,
                duration_s=0.0,
                provider=None,
                metadata=meta,
            )
            if not text:
                event.status = SttCaptureStatus.SKIPPED_EMPTY
                event.detail = "manual mode: empty text"
                return self._record_and_return(event)
            return self._inject_and_record(
                event,
                role_slug=role_slug,
                start_if_missing=start_if_missing,
            )

        # ---- Simulated mode: explicit simulated_text (preferred in tests) ----
        if mode == "simulated" or simulated_text is not None:
            text = (simulated_text or "").strip()
            event = SttCaptureEvent(
                node_id=node_id,
                source=SttCaptureSource.SIMULATED_STT,
                text=text,
                duration_s=duration,
                sample_rate=self.default_sample_rate,
                provider="simulated",
                status=SttCaptureStatus.DEGRADED,
                metadata=meta,
            )
            if not text:
                event.status = SttCaptureStatus.SKIPPED_EMPTY
                event.detail = "simulated mode: no simulated_text provided"
                return self._record_and_return(event)
            event.detail = "simulated capture — no mic/STT actually used"
            return self._inject_and_record(
                event,
                role_slug=role_slug,
                start_if_missing=start_if_missing,
            )

        # ---- Push-to-talk: real mic + STT if available ----
        cap = _probe_capability()
        if not cap.real_stt_available:
            event = SttCaptureEvent(
                node_id=node_id,
                source=SttCaptureSource.SIMULATED_STT,
                text="",
                duration_s=duration,
                sample_rate=self.default_sample_rate,
                provider=None,
                status=SttCaptureStatus.DEGRADED,
                detail=(
                    f"push_to_talk requested but environment unsupported "
                    f"({cap.reason}); no transcript produced"
                ),
                metadata={**meta, "capability": cap.as_dict()},
            )
            return self._record_and_return(event)

        # Real capture path. All heavy imports are lazy.
        sample_rate = _env_int("STT_SAMPLE_RATE", self.default_sample_rate)
        capture_timeout = _env_float("STT_CAPTURE_TIMEOUT_S", 15.0)
        try:
            audio = self._record_mic(
                duration,
                sample_rate,
                device=device,
                timeout_s=max(duration + 2.0, capture_timeout),
            )
        except Exception as e:  # noqa: BLE001
            event = SttCaptureEvent(
                node_id=node_id,
                source=SttCaptureSource.PUSH_TO_TALK,
                text="",
                duration_s=duration,
                sample_rate=sample_rate,
                status=SttCaptureStatus.ERROR,
                detail=f"mic capture failed: {e}",
                metadata=meta,
            )
            return self._record_and_return(event)

        # Post-capture audio sanity check (all-silent / NaN / empty).
        ok, reason, audio_stats = _validate_audio_quality(audio)
        meta.setdefault("audio_stats", audio_stats)
        if not ok:
            event = SttCaptureEvent(
                node_id=node_id,
                source=SttCaptureSource.PUSH_TO_TALK,
                text="",
                duration_s=duration,
                sample_rate=sample_rate,
                status=SttCaptureStatus.DEGRADED,
                detail=f"captured audio rejected: {reason}",
                metadata=meta,
            )
            return self._record_and_return(event)

        try:
            text, confidence, provider = self._transcribe(
                audio, sample_rate, cap.providers_available
            )
        except Exception as e:  # noqa: BLE001
            event = SttCaptureEvent(
                node_id=node_id,
                source=SttCaptureSource.PUSH_TO_TALK,
                text="",
                duration_s=duration,
                sample_rate=sample_rate,
                status=SttCaptureStatus.ERROR,
                detail=f"transcription failed: {e}",
                metadata=meta,
            )
            return self._record_and_return(event)

        event = SttCaptureEvent(
            node_id=node_id,
            source=SttCaptureSource.PUSH_TO_TALK,
            text=text.strip(),
            confidence=confidence,
            duration_s=duration,
            sample_rate=sample_rate,
            provider=provider,
            metadata=meta,
        )
        if not event.text:
            event.status = SttCaptureStatus.SKIPPED_EMPTY
            event.detail = "transcription produced empty text"
            return self._record_and_return(event)

        return self._inject_and_record(
            event,
            role_slug=role_slug,
            start_if_missing=start_if_missing,
        )

    # --- internals ---

    def _record_mic(
        self,
        duration_s: float,
        sample_rate: int,
        *,
        device: Optional[int] = None,
        timeout_s: float = 15.0,
    ):
        """Record `duration_s` of mono audio. Bounded and timeout-guarded.

        Lazy imports; never runs in a background thread beyond the single
        `sd.rec` call (which sounddevice manages internally). The `sd.wait`
        call is wrapped in a wall-clock timeout so a dead/claimed device
        can never hang this process.
        """
        import numpy as np  # noqa: F401
        import sounddevice as sd  # noqa: F401

        frames = int(max(0.05, duration_s) * sample_rate)
        kwargs: dict[str, Any] = dict(samplerate=sample_rate, channels=1, dtype="int16")
        if device is not None:
            kwargs["device"] = int(device)

        recording = sd.rec(frames, **kwargs)

        # Bounded wait. sd.wait() accepts no timeout; we poll instead.
        deadline = time.monotonic() + max(0.5, float(timeout_s))
        while True:
            try:
                # sd.wait() returns once the most recent play/rec is done;
                # polling with a tiny sleep is cheap and lets us bail out.
                if not sd.get_stream().active:
                    break
            except Exception:
                # If stream lookup fails, fall through to a blocking wait+break.
                sd.wait()
                break
            if time.monotonic() > deadline:
                try:
                    sd.stop()
                except Exception:
                    pass
                raise TimeoutError(
                    f"mic capture exceeded {timeout_s:.1f}s wall-clock budget"
                )
            time.sleep(0.05)
        return recording

    def _transcribe(
        self,
        audio,
        sample_rate: int,
        providers_available: list[str],
    ) -> tuple[str, Optional[float], Optional[str]]:
        """Transcribe recorded int16 mono audio. Lazy import of provider.

        Honors STT_PROVIDER (pins preferred provider) and STT_MODEL_SIZE
        (whisper model size, default 'base').
        """
        model_size = _env_str("STT_MODEL_SIZE", "base") or "base"
        provider_pref = _env_str("STT_PROVIDER")

        ordered: list[str] = []
        if provider_pref and provider_pref in providers_available:
            ordered.append(provider_pref)
        for p in ("faster_whisper", "whisper"):
            if p in providers_available and p not in ordered:
                ordered.append(p)

        for provider in ordered:
            if provider == "faster_whisper":
                from faster_whisper import WhisperModel  # noqa: F401
                import numpy as np

                pcm = np.asarray(audio, dtype="float32").reshape(-1) / 32768.0
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                segments, info = model.transcribe(pcm, language="en", beam_size=1)
                text = " ".join(s.text.strip() for s in segments).strip()
                confidence = None
                try:
                    confidence = float(getattr(info, "language_probability", None))
                except Exception:
                    confidence = None
                return text, confidence, "faster_whisper"

            if provider == "whisper":
                import numpy as np
                import whisper  # noqa: F401

                pcm = np.asarray(audio, dtype="float32").reshape(-1) / 32768.0
                model = whisper.load_model(model_size)
                result = model.transcribe(pcm, language="en")
                return (
                    str(result.get("text", "")).strip(),
                    None,
                    "whisper",
                )

        # Should be unreachable; capability check gates this path.
        return "", None, None

    def _inject_and_record(
        self,
        event: SttCaptureEvent,
        *,
        role_slug: str,
        start_if_missing: bool,
    ) -> SttCaptureEvent:
        """Push event.text into the voice loop via inject_transcript."""
        try:
            from eos_ai.substrate.transcript_inject import inject_transcript

            result = inject_transcript(
                event.node_id,
                event.text,
                source="local_stt",
                start_if_missing=start_if_missing,
                role_slug=role_slug,
                metadata={
                    "stt_event_id": event.event_id,
                    "stt_source": event.source.value,
                    "stt_provider": event.provider,
                    **(event.metadata or {}),
                },
            )
        except Exception as e:  # noqa: BLE001
            event.status = SttCaptureStatus.ERROR
            event.detail = f"inject_transcript crashed: {e}"
            return self._record_and_return(event)

        event.inject_status = str(result.get("status", ""))
        event.session_id = result.get("session_id")
        event.role_slug = result.get("role_slug")

        status_raw = event.inject_status
        if status_raw == "ok":
            # Preserve DEGRADED if we were already simulated; otherwise INJECTED.
            if event.source is SttCaptureSource.SIMULATED_STT:
                event.status = SttCaptureStatus.DEGRADED
                event.detail = event.detail or (
                    "simulated text injected into voice loop"
                )
            else:
                event.status = SttCaptureStatus.INJECTED
                event.detail = event.detail or (
                    f"injected via inject_transcript (provider={event.provider})"
                )
        elif status_raw == "no_active_session":
            event.status = SttCaptureStatus.SKIPPED_NO_SESSION
            event.detail = result.get("detail") or "no active session"
        elif status_raw == "empty_text":
            event.status = SttCaptureStatus.SKIPPED_EMPTY
            event.detail = result.get("detail") or "empty text"
        else:
            event.status = SttCaptureStatus.ERROR
            event.detail = (
                result.get("detail") or f"inject_transcript status={status_raw}"
            )

        return self._record_and_return(event)

    def _record_and_return(self, event: SttCaptureEvent) -> SttCaptureEvent:
        try:
            get_stt_capture_history().record(event)
        except Exception as e:  # noqa: BLE001
            _log(f"history record failed: {e}")
        return event


_runtime_singleton: Optional[LocalSttRuntime] = None
_runtime_lock = threading.RLock()


def get_local_stt_runtime() -> LocalSttRuntime:
    global _runtime_singleton
    with _runtime_lock:
        if _runtime_singleton is None:
            _runtime_singleton = LocalSttRuntime()
        return _runtime_singleton


def reset_local_stt_runtime_for_tests() -> None:
    global _runtime_singleton
    with _runtime_lock:
        _runtime_singleton = LocalSttRuntime()


# ─── Reporting helpers ────────────────────────────────────────────────────────


def stt_capture_snapshot(node_id: Optional[str] = None) -> dict[str, Any]:
    """Return the most recent capture event per node as a JSON-friendly dict.

    If node_id is given, only events for that node are considered.
    """
    hist = get_stt_capture_history()
    events = hist.latest(limit=_RETENTION_MAX, node_id=node_id)

    latest_by_node: dict[str, SttCaptureEvent] = {}
    for ev in events:  # events are newest-first
        if ev.node_id not in latest_by_node:
            latest_by_node[ev.node_id] = ev

    states = [ev.as_dict() for ev in latest_by_node.values()]
    stats = {
        "events_total": len(events),
        "nodes_with_state": len(states),
    }
    return {
        "count": len(states),
        "states": states,
        "stats": stats,
        "generated_at": _utcnow_iso(),
    }


def recent_stt_captures(
    limit: int = 10,
    node_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return recent capture events as JSON-friendly dicts (newest-first)."""
    hist = get_stt_capture_history()
    return [e.as_dict() for e in hist.latest(limit=limit, node_id=node_id)]


__all__ = [
    "SttCaptureSource",
    "SttCaptureStatus",
    "SttWorkstationReadiness",
    "SttCaptureEvent",
    "SttRuntimeCapability",
    "LocalSttRuntime",
    "SttCaptureHistory",
    "get_local_stt_runtime",
    "reset_local_stt_runtime_for_tests",
    "get_stt_capture_history",
    "reset_stt_capture_history_for_tests",
    "stt_runtime_status",
    "stt_workstation_readiness",
    "stt_capture_snapshot",
    "recent_stt_captures",
]
