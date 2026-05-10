"""Node routing — pure function for LOCAL vs VPS task placement.

Priority:
  1. LOCAL if available + load < threshold
  2. VPS as fallback
  3. ANY available node as last resort

Pure function — no global state, no I/O, no side effects.
Accepts telemetry as input.

No imports from umh/cells, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from umh.environments.telemetry import NodeTelemetry
from umh.nodes.registry import DeviceNode, DeviceType

_LOAD_THRESHOLD = 0.75


def route_task(
    nodes: list[DeviceNode],
    telemetry: dict[str, NodeTelemetry] | None = None,
    *,
    prefer_local: bool = True,
    high_compute: bool = False,
) -> DeviceNode | None:
    """Select the best node for a task. Pure function.

    Args:
        nodes: available device nodes
        telemetry: optional per-node telemetry
        prefer_local: prefer LOCAL node when possible
        high_compute: task requires significant resources (stay local if capable)
    """
    if not nodes:
        return None

    if prefer_local:
        local_nodes = [n for n in nodes if n.device_type == DeviceType.LOCAL]
        for node in local_nodes:
            load = _get_load(node, telemetry)
            if load < _LOAD_THRESHOLD:
                return node

    vps_nodes = [n for n in nodes if n.device_type == DeviceType.VPS]
    if vps_nodes:
        best_vps = min(vps_nodes, key=lambda n: _get_load(n, telemetry))
        return best_vps

    return min(nodes, key=lambda n: _get_load(n, telemetry))


def _get_load(node: DeviceNode, telemetry: dict[str, NodeTelemetry] | None) -> float:
    if telemetry and node.node_id in telemetry:
        t = telemetry[node.node_id]
        return max(t.cpu_percent / 100.0, t.memory_percent / 100.0)
    if node.telemetry:
        return max(node.telemetry.cpu_percent / 100.0, node.telemetry.memory_percent / 100.0)
    return 0.5
