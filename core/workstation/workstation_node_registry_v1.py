"""Workstation Node Registry v1.

Tracks known workstation relay nodes and provides lookups
for the control plane. Currently single-node (founder's workstation).

UMH substrate subsystem. Phase 96.8AO.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.workstation.workstation_relay_heartbeat_v1 import (
    evaluate_relay_health,
    read_relay_heartbeat,
)
from core.workstation.workstation_relay_node_v1 import (
    WorkstationRelayNode,
    load_relay_node_from_heartbeat,
)
from core.runtime.runtime_heartbeat_v1 import HeartbeatHealth


RELAY_HEARTBEAT_PATH = Path("data/runtime/workstation_relay/heartbeat.json")


class WorkstationNodeRegistry:
    """Registry of known workstation relay nodes."""

    def __init__(self, base_dir: Path = Path("/opt/OS")) -> None:
        self._base_dir = base_dir
        self._heartbeat_path = base_dir / RELAY_HEARTBEAT_PATH

    def get_primary_node(self) -> WorkstationRelayNode | None:
        """Get the primary (and currently only) relay node."""
        return load_relay_node_from_heartbeat(self._heartbeat_path)

    def get_relay_health(self) -> HeartbeatHealth:
        """Get the health of the primary relay node."""
        hb = read_relay_heartbeat(self._base_dir)
        return evaluate_relay_health(hb)

    def is_relay_available(self) -> bool:
        """Check if a relay node is available for execution."""
        node = self.get_primary_node()
        if node is None:
            return False
        health = self.get_relay_health()
        return health in (HeartbeatHealth.ALIVE, HeartbeatHealth.DEGRADED)

    def get_relay_status(self) -> dict[str, Any]:
        """Get a structured relay status report for !relay-status."""
        node = self.get_primary_node()
        hb = read_relay_heartbeat(self._base_dir)
        health = evaluate_relay_health(hb)

        if node is None:
            return {
                "online": False,
                "health": "dead",
                "reason": "no_heartbeat",
                "last_heartbeat": None,
                "machine_name": None,
                "relay_version": None,
                "desktop_active": False,
                "chrome_available": False,
                "maturity_ceiling": "L0_SIMULATED",
                "maturity_ceiling_reason": "relay_offline",
            }

        from core.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            maturity_ceiling,
        )

        if not node.is_execution_capable:
            ceiling = ActuatorMaturityLevel.L0_SIMULATED
        else:
            ceiling = maturity_ceiling(
                has_window_handle=True,
                has_screenshot=True,
                has_founder_confirmation=False,
            )

        return {
            "online": health in (HeartbeatHealth.ALIVE, HeartbeatHealth.DEGRADED),
            "health": health.value,
            "node_id": node.node_id,
            "last_heartbeat": node.last_heartbeat_at,
            "machine_name": node.machine_name,
            "user_name": node.user_name,
            "relay_version": node.relay_version,
            "relay_pid": node.relay_pid,
            "desktop_active": node.desktop_session_active,
            "desktop_unlocked": node.desktop_unlocked,
            "chrome_available": node.chrome_available,
            "monitor_detected": node.monitor_detected,
            "capabilities": node.capabilities,
            "maturity_ceiling": ceiling.name,
            "maturity_ceiling_reason": node.maturity_ceiling_reason,
            "is_execution_capable": node.is_execution_capable,
        }
