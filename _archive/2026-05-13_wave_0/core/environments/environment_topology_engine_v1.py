"""Environment Topology Engine v1.

Tracks active environments, relationships, trust hierarchy,
health, availability, and synchronization state.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    EnvironmentCapabilityMap,
    EnvironmentHealthState,
    EnvironmentNode,
    EnvironmentTopology,
    EnvironmentTrustLevel,
    TrustTier,
    _content_hash,
    _new_id,
    _now_iso,
)


KNOWN_ENVIRONMENTS: dict[str, dict[str, Any]] = {
    "vps": {
        "type": "server",
        "trust": TrustTier.FULL.value,
        "capabilities": ["shell", "docker", "git", "python", "tmux", "filesystem"],
        "delegation": True,
    },
    "local_workstation": {
        "type": "workstation",
        "trust": TrustTier.GOVERNED.value,
        "capabilities": ["shell", "git", "python", "filesystem"],
        "delegation": False,
    },
    "browser_runtime": {
        "type": "browser",
        "trust": TrustTier.RESTRICTED.value,
        "capabilities": ["navigation", "inspection", "screenshot"],
        "delegation": False,
    },
    "tmux_runtime": {
        "type": "terminal",
        "trust": TrustTier.GOVERNED.value,
        "capabilities": ["shell", "tmux", "python"],
        "delegation": False,
    },
    "filesystem_runtime": {
        "type": "filesystem",
        "trust": TrustTier.GOVERNED.value,
        "capabilities": ["read", "write", "filesystem"],
        "delegation": False,
    },
    "sandbox_runtime": {
        "type": "sandbox",
        "trust": TrustTier.RESTRICTED.value,
        "capabilities": ["python", "filesystem"],
        "delegation": False,
    },
}


class EnvironmentTopologyEngine:
    """Manages the environment topology graph."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/environment_topology",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._nodes: dict[str, EnvironmentNode] = {}
        self._capabilities: dict[str, EnvironmentCapabilityMap] = {}
        self._health: dict[str, EnvironmentHealthState] = {}
        self._trust: dict[str, EnvironmentTrustLevel] = {}
        self._edges: list[dict[str, str]] = []

    def register_environment(
        self,
        name: str,
        environment_type: str = "",
        trust_tier: str = TrustTier.GOVERNED.value,
        capabilities: list[str] | None = None,
        parent_id: str = "",
    ) -> EnvironmentNode:
        known = KNOWN_ENVIRONMENTS.get(name, {})
        node = EnvironmentNode(
            name=name,
            environment_type=environment_type or known.get("type", "unknown"),
            trust_tier=trust_tier if trust_tier != TrustTier.GOVERNED.value else known.get("trust", trust_tier),
            capabilities=capabilities or known.get("capabilities", []),
            parent_id=parent_id,
        )
        self._nodes[node.environment_id] = node

        cap_map = EnvironmentCapabilityMap(
            environment_id=node.environment_id,
            capabilities={c: True for c in node.capabilities},
            supports_delegation=known.get("delegation", False),
        )
        self._capabilities[node.environment_id] = cap_map

        self._health[node.environment_id] = EnvironmentHealthState(
            environment_id=node.environment_id,
        )
        self._trust[node.environment_id] = EnvironmentTrustLevel(
            environment_id=node.environment_id,
            tier=node.trust_tier,
            can_delegate=known.get("delegation", False),
        )

        if parent_id:
            self._edges.append({
                "from_id": parent_id,
                "to_id": node.environment_id,
                "edge_type": "parent_of",
            })

        self._persist_registration(node)
        return node

    def get_node(self, environment_id: str) -> EnvironmentNode | None:
        return self._nodes.get(environment_id)

    def get_node_by_name(self, name: str) -> EnvironmentNode | None:
        for node in self._nodes.values():
            if node.name == name:
                return node
        return None

    def get_capabilities(self, environment_id: str) -> EnvironmentCapabilityMap | None:
        return self._capabilities.get(environment_id)

    def get_health(self, environment_id: str) -> EnvironmentHealthState | None:
        return self._health.get(environment_id)

    def get_trust(self, environment_id: str) -> EnvironmentTrustLevel | None:
        return self._trust.get(environment_id)

    def update_health(
        self,
        environment_id: str,
        healthy: bool,
        reason: str = "",
    ) -> bool:
        health = self._health.get(environment_id)
        if not health:
            return False

        health.healthy = healthy
        health.last_heartbeat = _now_iso()
        if not healthy:
            health.consecutive_failures += 1
            health.degraded = health.consecutive_failures >= 3
        else:
            health.consecutive_failures = 0
            health.degraded = False
        health.reason = reason
        return True

    def has_capability(self, environment_id: str, capability: str) -> bool:
        cap = self._capabilities.get(environment_id)
        if not cap:
            return False
        return cap.capabilities.get(capability, False)

    def get_environments_with_capability(self, capability: str) -> list[str]:
        result = []
        for env_id, cap in self._capabilities.items():
            if cap.capabilities.get(capability, False):
                health = self._health.get(env_id)
                if health and health.healthy:
                    result.append(env_id)
        return result

    def build_topology(self) -> EnvironmentTopology:
        topo = EnvironmentTopology(
            nodes=list(self._nodes.values()),
            edges=list(self._edges),
        )
        topo.content_hash = _content_hash(topo.to_dict())
        return topo

    def _persist_registration(self, node: EnvironmentNode) -> None:
        path = self._state_dir / "environment_registrations.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(node.to_dict(), default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_environments": len(self._nodes),
            "total_edges": len(self._edges),
            "healthy": sum(1 for h in self._health.values() if h.healthy),
            "degraded": sum(1 for h in self._health.values() if h.degraded),
        }
