"""
Workstation push-to-talk (PTT) binding + REAL_READY proof path.

Purpose
-------
This module is a thin, bounded orchestrator on top of the existing STT
producer. It exists to make the workstation path *physically usable today*
by giving operators a single function that:

  1. Probes workstation readiness (`stt_workstation_readiness()`).
  2. Selects an input device (explicit, default, or first enumerated).
  3. Performs ONE bounded `capture_once(mode="push_to_talk", ...)`.
  4. Validates audio quality + transcription via the same producer path.
  5. Injects the resulting text into the bounded voice loop seam
     (`transcript_inject.inject_transcript`) with `source="push_to_talk"`.
  6. Returns a single JSON-friendly RealCaptureValidation dict that
     classifies the attempt as REAL_READY / DEGRADED / SIMULATED / etc.

This is NOT:
  - an always-on mic loop
  - a hotkey daemon
  - a freeform command parser
  - a new STT/audio pipeline (it reuses stt_producer entirely)

Design rules
------------
- Additive only. Hot path is never imported.
- Bounded. ONE capture per call. No background threads.
- Best-effort. Never raises into the caller.
- Reversible. Removing this file leaves the substrate exactly as it was.
- Reuses the bounded seam: capture_once → inject_transcript → voice session.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _log(msg: str) -> None:
    print(f"[substrate.ptt_binding] {msg}", file=sys.stderr)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "ptt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Result model ─────────────────────────────────────────────────────────────


@dataclass
class RealCaptureValidation:
    """Single bounded record of one workstation push-to-talk attempt."""

    validation_id: str
    node_id: str
    classification: str  # "real_ready" | "real_capture_ready" | "degraded" |
    #                     "simulated_only" | "unsupported" | "skipped" | "error"
    attempted: bool  # True if a capture_once() was actually invoked
    captured: bool  # True if audio was captured AND validated
    transcribed: bool  # True if transcription returned non-empty text
    injected: bool  # True if the text was injected into the voice loop
    degradation_reason: Optional[str] = None
    selected_device: Optional[int] = None
    duration_s: Optional[float] = None
    text: str = ""
    capture_event_id: Optional[str] = None
    capture_status: Optional[str] = None
    session_id: Optional[str] = None
    role_slug: Optional[str] = None
    inject_status: Optional[str] = None
    audio_loop: Optional[dict] = None
    readiness: Optional[dict] = None
    occurred_at: str = field(default_factory=_utcnow_iso)
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── Bounded history ──────────────────────────────────────────────────────────


_HISTORY_CAP = 50


class _ValidationHistory:
    """In-memory ring buffer of recent validation attempts. Bounded."""

    def __init__(self, cap: int = _HISTORY_CAP) -> None:
        self._lock = threading.RLock()
        self._rows: list[RealCaptureValidation] = []
        self._cap = cap

    def record(self, row: RealCaptureValidation) -> RealCaptureValidation:
        with self._lock:
            self._rows.append(row)
            if len(self._rows) > self._cap:
                drop = len(self._rows) - self._cap
                self._rows = self._rows[drop:]
        return row

    def latest(
        self, limit: int = 10, node_id: Optional[str] = None
    ) -> list[RealCaptureValidation]:
        with self._lock:
            rows = list(self._rows)
        if node_id is not None:
            rows = [r for r in rows if r.node_id == node_id]
        rows.sort(key=lambda r: r.occurred_at or "", reverse=True)
        return rows[: max(0, int(limit))]

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()


_history_singleton: Optional[_ValidationHistory] = None
_history_singleton_lock = threading.Lock()


def get_validation_history() -> _ValidationHistory:
    global _history_singleton
    if _history_singleton is None:
        with _history_singleton_lock:
            if _history_singleton is None:
                _history_singleton = _ValidationHistory()
    return _history_singleton


def reset_validation_history_for_tests() -> None:
    global _history_singleton
    with _history_singleton_lock:
        _history_singleton = None


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _safe_readiness() -> dict[str, Any]:
    try:
        from eos_ai.transport.stt_producer import stt_workstation_readiness

        return stt_workstation_readiness()
    except Exception as e:  # noqa: BLE001
        _log(f"readiness probe failed: {e}")
        return {
            "classification": "unsupported",
            "reason": f"readiness probe failed: {e}",
            "next_actions": [],
            "devices": [],
        }


def _pick_device(
    readiness: dict[str, Any], explicit_device: Optional[int]
) -> Optional[int]:
    if explicit_device is not None:
        return int(explicit_device)
    default = readiness.get("default_device") or {}
    if isinstance(default, dict) and "index" in default:
        try:
            return int(default["index"])
        except Exception:
            pass
    devices = readiness.get("devices") or []
    if isinstance(devices, list) and devices:
        first = devices[0]
        if isinstance(first, dict) and "index" in first:
            try:
                return int(first["index"])
            except Exception:
                pass
    return None


# ─── Public API ───────────────────────────────────────────────────────────────


def validate_real_capture(
    node_id: str,
    *,
    duration_s: float = 4.0,
    device: Optional[int] = None,
    role_slug: str = "ea_orchestrator",
    simulated_fallback_text: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict[str, Any]:
    """Run one bounded REAL_READY proof attempt and return its classification.

    Flow:
      1. Probe `stt_workstation_readiness()`.
      2. If real capture is unsupported AND a `simulated_fallback_text` was
         provided, perform a simulated capture so the seam still gets exercised
         (and reports `classification="simulated_only"`).
      3. Otherwise call `LocalSttRuntime.capture_once(mode="push_to_talk", ...)`.
      4. Inspect the resulting `SttCaptureEvent`:
            - INJECTED  → captured=True, transcribed=True, injected=True
            - DEGRADED  → captured=False, classification reflects readiness
            - SKIPPED_* → captured=False with reason
            - ERROR     → classification="error" with detail
      5. Snapshot `audio_loop_snapshot(node_id)` so the caller has full context.

    Never raises. Always returns a `RealCaptureValidation.as_dict()`.
    """
    meta = dict(metadata or {})
    meta.setdefault("issued_by", "ptt_binding.validate_real_capture")

    row = RealCaptureValidation(
        validation_id=_new_id(),
        node_id=node_id,
        classification="error",
        attempted=False,
        captured=False,
        transcribed=False,
        injected=False,
        duration_s=float(duration_s),
        role_slug=role_slug,
        metadata=meta,
    )

    readiness = _safe_readiness()
    row.readiness = readiness
    classification = (readiness.get("classification") or "").strip().lower()

    selected_device = _pick_device(readiness, device)
    row.selected_device = selected_device

    # ── Branch: real capture cannot run on this workstation ──────────────
    real_capture_possible = classification in ("real_ready", "real_capture_ready")

    if not real_capture_possible and simulated_fallback_text is None:
        row.classification = classification or "unsupported"
        row.degradation_reason = readiness.get("reason") or "real capture unavailable"
        get_validation_history().record(row)
        return row.as_dict()

    # ── Perform exactly one bounded capture (real or simulated) ──────────
    try:
        from eos_ai.transport.stt_producer import get_local_stt_runtime
    except Exception as e:  # noqa: BLE001
        row.degradation_reason = f"stt_producer import failed: {e}"
        get_validation_history().record(row)
        return row.as_dict()

    rt = get_local_stt_runtime()
    row.attempted = True

    try:
        if real_capture_possible:
            event = rt.capture_once(
                node_id,
                mode="push_to_talk",
                duration_s=duration_s,
                role_slug=role_slug,
                start_if_missing=True,
                device=selected_device,
                metadata={**meta, "validation_id": row.validation_id},
            )
        else:
            event = rt.capture_once(
                node_id,
                mode="simulated",
                duration_s=duration_s,
                simulated_text=simulated_fallback_text,
                role_slug=role_slug,
                start_if_missing=True,
                metadata={
                    **meta,
                    "validation_id": row.validation_id,
                    "simulated_fallback": True,
                },
            )
    except Exception as e:  # noqa: BLE001
        row.degradation_reason = f"capture_once raised: {e}"
        get_validation_history().record(row)
        return row.as_dict()

    # ── Translate SttCaptureEvent → validation row ───────────────────────
    try:
        row.capture_event_id = getattr(event, "event_id", None)
        status_value = getattr(getattr(event, "status", None), "value", None) or str(
            getattr(event, "status", "")
        )
        row.capture_status = status_value
        row.text = getattr(event, "text", "") or ""
        row.session_id = getattr(event, "session_id", None)
        row.role_slug = getattr(event, "role_slug", None) or role_slug
        row.inject_status = getattr(event, "inject_status", None)

        # The producer marks simulated-mode events as `status=DEGRADED` even
        # when the injection succeeds (the "degradation" describes the audio
        # path, not the seam). The authoritative signal that the bounded
        # inject actually happened is `event.inject_status == "ok"`.
        inject_ok = (row.inject_status or "").lower() == "ok"

        if status_value == "injected" or inject_ok:
            row.captured = True
            row.transcribed = bool(row.text.strip())
            row.injected = True
            if real_capture_possible and status_value == "injected":
                row.classification = "real_ready"
            else:
                row.classification = "simulated_only"
            if status_value == "degraded":
                # Carry the degradation reason for visibility, but don't
                # mark the row as failed — the seam succeeded.
                row.degradation_reason = (
                    getattr(event, "detail", None) or "simulated path"
                )
        elif status_value == "degraded":
            row.classification = classification or "degraded"
            row.degradation_reason = getattr(event, "detail", None) or "degraded"
        elif status_value in ("skipped_empty", "skipped_no_session"):
            row.classification = "degraded"
            row.degradation_reason = getattr(event, "detail", None) or status_value
        elif status_value == "unsupported":
            row.classification = "unsupported"
            row.degradation_reason = getattr(event, "detail", None) or "unsupported"
        else:
            row.classification = "error"
            row.degradation_reason = getattr(event, "detail", None) or status_value
    except Exception as e:  # noqa: BLE001
        row.degradation_reason = f"event translation failed: {e}"

    # ── Audio loop snapshot ──────────────────────────────────────────────
    try:
        from eos_ai.transport.audio_loop import snapshot as audio_snapshot

        row.audio_loop = audio_snapshot(node_id=node_id)
    except Exception as e:  # noqa: BLE001
        _log(f"audio_loop snapshot failed: {e}")
        row.audio_loop = None

    get_validation_history().record(row)
    return row.as_dict()


def real_capture_report(
    node_id: Optional[str] = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Bounded operator-facing summary of recent real-capture attempts.

    Combines:
      - current workstation readiness
      - last N validation attempts (filtered by node if given)
      - small aggregate counters (by classification)
    """
    readiness = _safe_readiness()
    history = get_validation_history().latest(limit=limit, node_id=node_id)
    by_class: dict[str, int] = {}
    for row in history:
        key = row.classification or "unknown"
        by_class[key] = by_class.get(key, 0) + 1
    return {
        "node_id": node_id,
        "readiness": readiness,
        "history": [r.as_dict() for r in history],
        "history_count": len(history),
        "by_classification": by_class,
        "generated_at": _utcnow_iso(),
    }


__all__ = [
    "RealCaptureValidation",
    "validate_real_capture",
    "real_capture_report",
    "get_validation_history",
    "reset_validation_history_for_tests",
]
