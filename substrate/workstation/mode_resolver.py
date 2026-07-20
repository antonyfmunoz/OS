"""Workstation mode resolver — authoritative composite of all mode systems.

Reads OperatorDayMode, OperationalMode, StationPresenceMode, OperatorMode,
the continuity state machine, lifecycle modes, and profile modes. Returns
a unified snapshot for the cockpit and governance layers.

Phase 14.11A: read-only aggregator of 4 legacy systems.
Phase 14.11B: upgraded to compose continuity + lifecycle + profile.

Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _oe_sessions_path() -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path("operator_experience", "sessions.jsonl", create_parent=False))


def resolve_composite_mode(
    continuity_state: str = "",
    lifecycle_mode: str = "",
    active_profile_modes: list[str] | None = None,
) -> dict[str, Any]:
    """Read all mode systems and return a unified composite.

    Never mutates state. Pure read-only aggregation.
    New 14.11B fields are additive — all 14.11A fields preserved.
    """
    result: dict[str, Any] = {
        "operator_day_mode": _read_operator_day_mode(),
        "operational_mode": _read_operational_mode(),
        "station_presence_mode": _read_station_presence_mode(),
        "operator_mode": _read_operator_mode(),
    }

    result["effective_posture"] = _derive_posture(result)

    result["continuity_state"] = continuity_state or _read_continuity_state()
    result["lifecycle_mode"] = lifecycle_mode or _derive_lifecycle_mode(result)
    result["active_profile_modes"] = active_profile_modes or _read_profile_modes()
    result["risk_ceiling"] = _derive_risk_ceiling(result.get("lifecycle_mode", "day_cycle"))

    return result


def _read_operator_day_mode() -> dict[str, Any]:
    try:
        import json as _json

        from substrate.state.runtime_paths import runtime_state_path

        path = str(runtime_state_path("operator_experience", "sessions.jsonl", create_parent=False))
        if not os.path.exists(path):
            return {"mode": "unknown", "source": "no session file"}

        last_line = ""
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
        if not last_line:
            return {"mode": "unknown", "source": "empty session file"}

        data = _json.loads(last_line)
        return {
            "mode": data.get("day_mode", "unknown"),
            "source": "operator_session",
        }
    except Exception as exc:
        logger.debug("operator_day_mode read failed: %s", exc)
        return {"mode": "unknown", "source": f"error: {type(exc).__name__}"}


def _read_operational_mode() -> dict[str, Any]:
    try:
        from substrate.execution.workers.workstation.workstation_contracts_v1 import (
            OperationalMode,
        )

        return {
            "mode": OperationalMode.DEVELOPER.value,
            "source": "default",
            "available_modes": [m.value for m in OperationalMode],
        }
    except Exception as exc:
        logger.debug("operational_mode read failed: %s", exc)
        return {"mode": "unknown", "source": f"error: {type(exc).__name__}"}


def _read_station_presence_mode() -> dict[str, Any]:
    try:
        from substrate.execution.bridge.station_presence import StationPresenceMode

        return {
            "mode": StationPresenceMode.LOCAL.value,
            "source": "default",
            "available_modes": [m.value for m in StationPresenceMode],
        }
    except Exception as exc:
        logger.debug("station_presence_mode read failed: %s", exc)
        return {"mode": "unknown", "source": f"error: {type(exc).__name__}"}


def _read_operator_mode() -> dict[str, Any]:
    try:
        from substrate.execution.bridge.operator_state import OperatorMode

        return {
            "mode": OperatorMode.IDLE.value,
            "source": "default",
            "available_modes": [m.value for m in OperatorMode],
        }
    except Exception as exc:
        logger.debug("operator_mode read failed: %s", exc)
        return {"mode": "unknown", "source": f"error: {type(exc).__name__}"}


def _read_continuity_state() -> str:
    """Read persisted continuity state, default to 'active'."""
    try:
        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "umh",
            "workstation_state",
            "continuity.json",
        )
        if os.path.exists(path):
            data = json.loads(open(path, encoding="utf-8").read())
            return data.get("current_state", "active")
    except Exception as exc:
        logger.debug("continuity_state read failed: %s", exc)
    return "active"


def _read_profile_modes() -> list[str]:
    """Read active profile modes, default to ['developer']."""
    try:
        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "umh",
            "workstation_state",
            "profile_modes.json",
        )
        if os.path.exists(path):
            data = json.loads(open(path, encoding="utf-8").read())
            modes = data.get("active_modes", [])
            if modes:
                return modes
    except Exception as exc:
        logger.debug("profile_modes read failed: %s", exc)
    return ["developer"]


def _derive_lifecycle_mode(modes: dict[str, Any]) -> str:
    """Derive lifecycle mode from continuity state + day mode."""
    continuity = modes.get("continuity_state", "active")
    day = modes.get("operator_day_mode", {}).get("mode", "unknown")

    if continuity == "night_sleeping" or day == "overnight":
        return "night_cycle"
    if continuity == "extended_absence":
        return "overnight"
    if continuity in ("returning", "resume_brief"):
        return "day_cycle"
    if continuity == "away":
        return "away"
    if continuity == "remote":
        return "remote_work"
    if continuity == "idle":
        return "idle"
    if day == "deep_work":
        return "day_cycle"
    if day == "inactive":
        return "idle"
    return "day_cycle"


def _derive_risk_ceiling(lifecycle_mode: str) -> str:
    """Map lifecycle mode to maximum permitted risk level."""
    ceilings = {
        "day_cycle": "HIGH",
        "night_cycle": "LOW",
        "overnight": "LOW",
        "maintenance": "MEDIUM",
        "idle": "LOW",
        "away": "LOW",
        "remote_work": "MEDIUM",
        "end_of_workday": "LOW",
        "emergency": "CRITICAL",
    }
    return ceilings.get(lifecycle_mode, "LOW")


def _derive_posture(modes: dict[str, Any]) -> str:
    """Derive a single effective posture from the four mode readings."""
    day = modes.get("operator_day_mode", {}).get("mode", "unknown")
    if day == "overnight":
        return "overnight_autonomous"
    if day == "deep_work":
        return "deep_work"
    if day == "inactive":
        return "inactive"
    if day == "remote_active":
        return "remote"
    return "active"
