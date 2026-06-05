"""Workstation mode resolver — read-only composite of all mode systems.

Reads OperatorDayMode, OperationalMode, StationPresenceMode, and OperatorMode
without replacing any of them. Returns a unified snapshot for the cockpit.

Phase 14.11A. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def resolve_composite_mode() -> dict[str, Any]:
    """Read all four mode systems and return a unified composite.

    Never mutates state. Pure read-only aggregation.
    """
    result: dict[str, Any] = {
        "operator_day_mode": _read_operator_day_mode(),
        "operational_mode": _read_operational_mode(),
        "station_presence_mode": _read_station_presence_mode(),
        "operator_mode": _read_operator_mode(),
    }

    result["effective_posture"] = _derive_posture(result)
    return result


def _read_operator_day_mode() -> dict[str, Any]:
    try:
        from substrate.execution.bridge.operator_session import (
            OperatorDayMode,
            OperatorSession,
        )
        import json
        import os

        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data", "umh", "operator_experience", "sessions.jsonl",
        )
        if not os.path.exists(path):
            return {"mode": "unknown", "source": "no session file"}

        last_line = ""
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
        if not last_line:
            return {"mode": "unknown", "source": "empty session file"}

        data = json.loads(last_line)
        return {
            "mode": data.get("day_mode", "unknown"),
            "source": "operator_session",
        }
    except Exception as exc:
        logger.debug("operator_day_mode read failed: %s", exc)
        return {"mode": "unknown", "source": f"error: {type(exc).__name__}"}


def _read_operational_mode() -> dict[str, Any]:
    try:
        from substrate.execution.workers.workstation.workstation_operational_modes_v1 import (
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
