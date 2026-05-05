"""Failover routing — health-aware node selection with retry policy.

Wraps the pure route_task function with health awareness and
configurable failover policy. Deterministic ordering for equal scores.

No imports from umh/cells, umh/adapters, subprocess, or shell.
No I/O — accepts all state as parameters.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from umh.environments.telemetry import NodeTelemetry
from umh.nodes.health import NodeHealthManager, NodeHealthState
from umh.nodes.registry import DeviceNode, DeviceType


@dataclass(frozen=True)
class FailoverPolicy:
    """Configuration for failover behavior."""

    max_attempts: int = 3
    allow_vps_fallback: bool = True
    allow_local_fallback: bool = True
    avoid_degraded_nodes: bool = False
    retry_delay_seconds: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "allow_vps_fallback": self.allow_vps_fallback,
            "allow_local_fallback": self.allow_local_fallback,
            "avoid_degraded_nodes": self.avoid_degraded_nodes,
            "retry_delay_seconds": self.retry_delay_seconds,
        }


_LOAD_THRESHOLD = 0.75
_DEFAULT_POLICY = FailoverPolicy()


class FailoverRouter:
    """Health-aware routing with failover support."""

    def __init__(
        self,
        health_manager: NodeHealthManager | None = None,
        policy: FailoverPolicy | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._health = health_manager or NodeHealthManager()
        self._policy = policy or _DEFAULT_POLICY
        self._failure_counts: dict[str, int] = {}
        self._success_counts: dict[str, int] = {}

    @property
    def policy(self) -> FailoverPolicy:
        return self._policy

    @property
    def health_manager(self) -> NodeHealthManager:
        return self._health

    def choose_initial_node(
        self,
        nodes: list[DeviceNode],
        telemetry: dict[str, NodeTelemetry] | None = None,
        *,
        prefer_local: bool = True,
        high_compute: bool = False,
    ) -> DeviceNode | None:
        """Select the best healthy node for initial task placement."""
        candidates = self._filter_available(nodes)
        if not candidates:
            return None
        return self._select_best(candidates, telemetry, prefer_local=prefer_local)

    def choose_fallback_node(
        self,
        failed_node_id: str,
        nodes: list[DeviceNode],
        telemetry: dict[str, NodeTelemetry] | None = None,
    ) -> DeviceNode | None:
        """Select a fallback node after a failure, excluding the failed node."""
        candidates = [n for n in self._filter_available(nodes) if n.node_id != failed_node_id]

        if not candidates and self._policy.allow_vps_fallback:
            vps = [
                n for n in nodes if n.node_id != failed_node_id and n.device_type == DeviceType.VPS
            ]
            vps = self._filter_by_health(vps, allow_degraded=True)
            candidates = vps

        if not candidates and self._policy.allow_local_fallback:
            local = [
                n
                for n in nodes
                if n.node_id != failed_node_id and n.device_type == DeviceType.LOCAL
            ]
            local = self._filter_by_health(local, allow_degraded=True)
            candidates = local

        if not candidates:
            return None
        return self._select_best(candidates, telemetry, prefer_local=False)

    def record_failure(self, node_id: str, reason: str = "") -> None:
        with self._lock:
            self._failure_counts[node_id] = self._failure_counts.get(node_id, 0) + 1

    def record_success(self, node_id: str) -> None:
        with self._lock:
            self._success_counts[node_id] = self._success_counts.get(node_id, 0) + 1

    def get_stats(self, node_id: str) -> dict[str, int]:
        with self._lock:
            return {
                "failures": self._failure_counts.get(node_id, 0),
                "successes": self._success_counts.get(node_id, 0),
            }

    def _filter_available(self, nodes: list[DeviceNode]) -> list[DeviceNode]:
        return self._filter_by_health(nodes, allow_degraded=not self._policy.avoid_degraded_nodes)

    def _filter_by_health(
        self, nodes: list[DeviceNode], *, allow_degraded: bool = True
    ) -> list[DeviceNode]:
        result = []
        for node in nodes:
            health = self._health.get_health(node.node_id)
            if health is None:
                result.append(node)
                continue
            if health.state == NodeHealthState.HEALTHY:
                result.append(node)
            elif health.state == NodeHealthState.DEGRADED and allow_degraded:
                result.append(node)
            elif health.state == NodeHealthState.RECOVERING and allow_degraded:
                result.append(node)
        return result

    def _select_best(
        self,
        candidates: list[DeviceNode],
        telemetry: dict[str, NodeTelemetry] | None,
        *,
        prefer_local: bool = True,
    ) -> DeviceNode | None:
        if not candidates:
            return None

        if prefer_local:
            local = [n for n in candidates if n.device_type == DeviceType.LOCAL]
            for node in sorted(local, key=lambda n: n.node_id):
                load = _get_load(node, telemetry)
                if load < _LOAD_THRESHOLD:
                    return node

        vps = [n for n in candidates if n.device_type == DeviceType.VPS]
        if vps:
            return min(vps, key=lambda n: (_get_load(n, telemetry), n.node_id))

        return min(candidates, key=lambda n: (_get_load(n, telemetry), n.node_id))

    def clear(self) -> None:
        with self._lock:
            self._failure_counts.clear()
            self._success_counts.clear()
        self._health.clear()


def _get_load(node: DeviceNode, telemetry: dict[str, NodeTelemetry] | None) -> float:
    if telemetry and node.node_id in telemetry:
        t = telemetry[node.node_id]
        return max(t.cpu_percent / 100.0, t.memory_percent / 100.0)
    if node.telemetry:
        return max(node.telemetry.cpu_percent / 100.0, node.telemetry.memory_percent / 100.0)
    return 0.5
