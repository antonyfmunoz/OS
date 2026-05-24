"""Health monitoring — subsystem status checks for the workstation.

Aggregates health from: scheduler, perception, transport, operator state,
signal socket, continuity bridge, inference checker, voice engine.

Each subsystem returns UP / DEGRADED / DOWN with optional detail.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SubsystemHealth:
    name: str
    status: str  # UP, DEGRADED, DOWN
    detail: str = ""


def check_scheduler(scheduler: Any = None) -> SubsystemHealth:
    if scheduler is None:
        return SubsystemHealth("scheduler", "DOWN", "not initialized")
    if scheduler.is_running:
        return SubsystemHealth("scheduler", "UP", f"{scheduler.trigger_count} triggers configured")
    return SubsystemHealth("scheduler", "DOWN", "stopped")


def check_perception(perception: Any = None) -> SubsystemHealth:
    if perception is None:
        return SubsystemHealth("perception", "DOWN", "not initialized")
    snap = perception.get_snapshot()
    active = [k for k, v in snap.items() if v.get("running", False)]
    if active:
        return SubsystemHealth("perception", "UP", ", ".join(active))
    return SubsystemHealth("perception", "DEGRADED", "no active sources")


def check_transport() -> SubsystemHealth:
    try:
        from umh.transport import INTEGRATION_ID

        return SubsystemHealth("transport", "UP", INTEGRATION_ID)
    except Exception as exc:
        logger.debug("Transport health check failed: %s", exc)
        return SubsystemHealth("transport", "DOWN", "not registered")


def check_signal_socket() -> SubsystemHealth:
    from umh.signals import get_signal_socket

    if get_signal_socket() is not None:
        return SubsystemHealth("signal_socket", "UP")
    return SubsystemHealth("signal_socket", "DOWN", "not connected")


def check_operator_state(node_id: str = "workstation_local") -> SubsystemHealth:
    try:
        from substrate.execution.bridge.operator_state import get_operator_state_store

        store = get_operator_state_store()
        state = store.get_or_create(node_id)
        return SubsystemHealth("operator_state", "UP", state.mode.value)
    except ImportError:
        return SubsystemHealth("operator_state", "DOWN", "substrate unavailable")
    except Exception as exc:
        return SubsystemHealth("operator_state", "DEGRADED", str(exc))


def check_continuity(continuity: Any = None) -> SubsystemHealth:
    if continuity is None:
        return SubsystemHealth("continuity", "DOWN", "not initialized")
    return SubsystemHealth("continuity", "UP")


def check_voice() -> SubsystemHealth:
    try:
        from umh.voice import VoiceOutput

        v = VoiceOutput(text_only=False)
        if v.tts_available:
            return SubsystemHealth("voice", "UP", "TTS ready")
        return SubsystemHealth("voice", "DEGRADED", "TTS unavailable — text output only")
    except Exception as exc:
        return SubsystemHealth("voice", "DEGRADED", str(exc))


def check_inference(inference_checker: Any = None) -> SubsystemHealth:
    if inference_checker is None:
        return SubsystemHealth("inference", "DOWN", "not initialized")
    interval = getattr(inference_checker, "_interval_s", 0)
    return SubsystemHealth("inference", "UP", f"{interval}s interval")


def run_health_check(
    scheduler: Any = None,
    perception: Any = None,
    continuity: Any = None,
    inference_checker: Any = None,
    node_id: str = "workstation_local",
) -> list[SubsystemHealth]:
    """Run all health checks and return results."""
    return [
        check_scheduler(scheduler),
        check_perception(perception),
        check_transport(),
        check_signal_socket(),
        check_operator_state(node_id),
        check_continuity(continuity),
        check_voice(),
        check_inference(inference_checker),
    ]


def format_health(results: list[SubsystemHealth]) -> str:
    """Format health check results for display."""
    lines = ["Subsystem Health:"]
    for r in results:
        icon = {"UP": "+", "DEGRADED": "~", "DOWN": "-"}.get(r.status, "?")
        detail = f" ({r.detail})" if r.detail else ""
        lines.append(f"  [{icon}] {r.name:<16s} {r.status}{detail}")

    up = sum(1 for r in results if r.status == "UP")
    total = len(results)
    lines.append(f"\n  {up}/{total} subsystems healthy")
    return "\n".join(lines)


def show_health(
    scheduler: Any = None,
    perception: Any = None,
    continuity: Any = None,
    inference_checker: Any = None,
    node_id: str = "workstation_local",
) -> None:
    """Print health check results."""
    results = run_health_check(
        scheduler=scheduler,
        perception=perception,
        continuity=continuity,
        inference_checker=inference_checker,
        node_id=node_id,
    )
    print(format_health(results))
