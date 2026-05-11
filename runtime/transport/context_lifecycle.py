"""
Context lifecycle — pressure-aware session maintenance with checkpoint/restore.

Purpose
-------
Replaces message-count-based ``/clear`` decisions with multi-signal context
pressure detection.  Provides checkpoint/restore so session continuity
survives clears.

Design rules
------------
- Composes on top of session_control for the actual clear.  Never duplicates
  tmux plumbing.
- No hot-path imports (gateway, cognitive_loop, model_router, agent_runtime,
  primitives).  This is a substrate leaf.
- No background threads, no daemons.  Pressure detection is triggered inside
  the request flow.
- All functions return JSON-safe dicts.  Never raises.
- Thread-safe.

Env vars
--------
  EOS_CONTEXT_PRESSURE_THRESHOLD   float 0-1  (default 0.75)
  EOS_CONTEXT_GUARD_ENABLED        "1" | "0"  (default "1")

Public API:
  - detect_context_pressure(session_name, *, message_count, reply_text, metadata) -> dict
  - build_context_checkpoint(session_name, *, mode, target, ...) -> dict
  - restore_from_checkpoint(checkpoint) -> dict
  - maybe_clear_and_restore(session_name, target, mode, ...) -> dict
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "detect_context_pressure",
    "build_context_checkpoint",
    "restore_from_checkpoint",
    "maybe_clear_and_restore",
]

_LIFECYCLE_VERSION = "1.0"

# ── Env thresholds ──────────────────────────────────────────────────────────

_ENV_PRESSURE_THRESHOLD = "EOS_CONTEXT_PRESSURE_THRESHOLD"
_ENV_GUARD_ENABLED = "EOS_CONTEXT_GUARD_ENABLED"

_DEFAULT_PRESSURE_THRESHOLD = 0.75


def _pressure_threshold() -> float:
    """Read pressure threshold from env.  Clamp to [0.0, 1.0]."""
    raw = os.getenv(_ENV_PRESSURE_THRESHOLD, "").strip()
    if not raw:
        return _DEFAULT_PRESSURE_THRESHOLD
    try:
        val = float(raw)
        return max(0.0, min(1.0, val))
    except ValueError:
        return _DEFAULT_PRESSURE_THRESHOLD


def _guard_enabled() -> bool:
    """Check whether the context guard is enabled (default True)."""
    raw = (os.getenv(_ENV_GUARD_ENABLED, "1") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _log(msg: str) -> None:
    print(f"[substrate.context_lifecycle] {msg}", file=sys.stderr)


# ── Degradation markers ────────────────────────────────────────────────────

_DEGRADATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"i don'?t have context", re.IGNORECASE),
    re.compile(r"i'?m not sure what you'?re referring to", re.IGNORECASE),
    re.compile(r"could you (please )?(clarify|explain|provide more)", re.IGNORECASE),
    re.compile(r"i don'?t have (enough )?information", re.IGNORECASE),
    re.compile(r"can you (please )?rephrase", re.IGNORECASE),
    re.compile(r"i'?m (not sure|unclear) (about |on )?what", re.IGNORECASE),
]


def _has_degradation_markers(text: str) -> bool:
    """Return True if reply text shows signs of context degradation."""
    if not text:
        return False
    for pat in _DEGRADATION_PATTERNS:
        if pat.search(text):
            return True
    return False


# ── Pressure detection ──────────────────────────────────────────────────────


def detect_context_pressure(
    session_name: str,
    *,
    message_count: int | None = None,
    reply_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect context pressure using multiple signals.

    Returns a dict with pressure_score, pressure_level, should_clear,
    individual signal contributions, threshold, and lifecycle_version.
    """
    meta = metadata or {}
    signals: dict[str, float] = {}

    # Signal 1: message count (weight 0.3)
    if message_count is not None:
        msg_w = min(1.0, message_count / 50) * 0.3
        signals["message_count"] = round(msg_w, 4)

    # Signal 2: total chars sent (weight 0.2)
    total_chars = meta.get("total_chars_sent")
    if total_chars is not None:
        chars_w = min(1.0, total_chars / 100_000) * 0.2
        signals["total_chars"] = round(chars_w, 4)

    # Signal 3: degradation markers in reply (weight 0.4)
    if reply_text and _has_degradation_markers(reply_text):
        signals["degradation"] = 0.4

    # Signal 4: session age (weight 0.1)
    age_minutes = meta.get("session_age_minutes")
    if age_minutes is not None:
        age_w = min(1.0, age_minutes / 120) * 0.1
        signals["session_age"] = round(age_w, 4)

    pressure_score = min(1.0, sum(signals.values()))
    pressure_score = round(pressure_score, 4)

    if pressure_score >= 0.7:
        pressure_level = "high"
    elif pressure_score >= 0.4:
        pressure_level = "moderate"
    else:
        pressure_level = "low"

    threshold = _pressure_threshold()
    guard = _guard_enabled()
    should_clear = guard and pressure_score >= threshold

    return {
        "session_name": session_name,
        "pressure_score": pressure_score,
        "pressure_level": pressure_level,
        "should_clear": should_clear,
        "signals": signals,
        "threshold": threshold,
        "guard_enabled": guard,
        "lifecycle_version": _LIFECYCLE_VERSION,
    }


# ── Checkpoint ──────────────────────────────────────────────────────────────


def build_context_checkpoint(
    session_name: str,
    *,
    mode: str,
    target: str,
    active_objective: str | None = None,
    workflow_kind: str | None = None,
    task_summary: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact checkpoint dict for session restoration after clear."""
    checkpoint_at = datetime.now(timezone.utc).isoformat()

    # Build restore prompt — compact, under 500 chars
    parts = [f"[Session restored] Mode: {mode}. Target: {target}."]
    if active_objective:
        parts.append(f"Last objective: {active_objective}.")
    if workflow_kind:
        parts.append(f"Workflow: {workflow_kind}.")
    if task_summary:
        parts.append(f"Task: {task_summary}.")
    parts.append("Continue from where we left off.")
    restore_prompt = " ".join(parts)

    # Truncate to 500 chars if needed
    if len(restore_prompt) > 500:
        restore_prompt = restore_prompt[:497] + "..."

    return {
        "session_name": session_name,
        "mode": mode,
        "target": target,
        "active_objective": active_objective,
        "workflow_kind": workflow_kind,
        "task_summary": task_summary,
        "checkpoint_at": checkpoint_at,
        "checkpoint_version": _LIFECYCLE_VERSION,
        "restore_prompt": restore_prompt,
        "metadata": metadata,
    }


# ── Restore ─────────────────────────────────────────────────────────────────


def restore_from_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    """Build a restoration dict from a previously saved checkpoint."""
    restored_at = datetime.now(timezone.utc).isoformat()

    return {
        "restore_prompt": checkpoint.get("restore_prompt", ""),
        "session_name": checkpoint.get("session_name", ""),
        "mode": checkpoint.get("mode", ""),
        "target": checkpoint.get("target", ""),
        "restored_at": restored_at,
        "lifecycle_version": _LIFECYCLE_VERSION,
    }


# ── Orchestrator ────────────────────────────────────────────────────────────


def maybe_clear_and_restore(
    session_name: str,
    target: str,
    mode: str,
    *,
    message_count: int | None = None,
    reply_text: str | None = None,
    active_objective: str | None = None,
    workflow_kind: str | None = None,
    task_summary: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Orchestrate pressure detection, checkpoint, clear, and restore.

    1. Detect context pressure.
    2. If below threshold, return early with cleared=False.
    3. Build checkpoint.
    4. Clear the session via session_control.
    5. Restore from checkpoint.
    6. Return full result.

    Imports session_control lazily to avoid circular imports.
    Fail-safe: if clear fails, still returns checkpoint for manual restore.
    """
    pressure = detect_context_pressure(
        session_name,
        message_count=message_count,
        reply_text=reply_text,
        metadata=metadata,
    )

    if not pressure["should_clear"]:
        return {
            "cleared": False,
            "pressure": pressure,
            "lifecycle_version": _LIFECYCLE_VERSION,
        }

    # Build checkpoint before clearing
    checkpoint = build_context_checkpoint(
        session_name,
        mode=mode,
        target=target,
        active_objective=active_objective,
        workflow_kind=workflow_kind,
        task_summary=task_summary,
        metadata=metadata,
    )

    # Lazy import to avoid circular dependency
    try:
        from eos_ai.transport.session_control import clear_session
    except Exception as exc:  # noqa: BLE001
        _log(f"session_control import failed: {exc}")
        restore = restore_from_checkpoint(checkpoint)
        return {
            "cleared": False,
            "clear_error": str(exc),
            "checkpoint": checkpoint,
            "restore": restore,
            "pressure": pressure,
            "lifecycle_version": _LIFECYCLE_VERSION,
        }

    # Attempt clear
    clear_result = clear_session(target, session_name)
    cleared = bool(clear_result.get("ok"))

    if not cleared:
        _log(f"clear failed for {session_name}: {clear_result.get('reason')}")

    # Restore regardless of clear success — checkpoint is always useful
    restore = restore_from_checkpoint(checkpoint)

    return {
        "cleared": cleared,
        "clear_result": clear_result,
        "checkpoint": checkpoint,
        "restore": restore,
        "pressure": pressure,
        "lifecycle_version": _LIFECYCLE_VERSION,
    }
