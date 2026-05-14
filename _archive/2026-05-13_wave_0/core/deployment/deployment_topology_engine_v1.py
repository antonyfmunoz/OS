"""Deployment Topology Engine v1.

Tracks deployment topology: environments, relationships,
trust tiers, dependencies. Supports 6 environment types.

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.deployment.platform_deployment_contracts_v1 import (
    DeploymentEnvironment,
    DeploymentEnvironmentType,
    DeploymentTopology,
    _now_iso,
)

KNOWN_ENVIRONMENTS: list[str] = [e.value for e in DeploymentEnvironmentType]

MAX_ENVIRONMENTS = 15
MAX_EDGES = 50


class DeploymentTopologyEngine:
    """Tracks deployment topology and environment relationships."""

    def __init__(self, state_dir: str | Path = "data/runtime/deployments") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._environments: dict[str, DeploymentEnvironment] = {}
        self._edges: list[dict[str, str]] = []

    def register_environment(
        self,
        environment_type: str,
        trust_tier: str = "development",
        capabilities: list[str] | None = None,
    ) -> DeploymentEnvironment | None:
        if environment_type not in KNOWN_ENVIRONMENTS:
            return None
        if len(self._environments) >= MAX_ENVIRONMENTS:
            return None

        for env in self._environments.values():
            if env.environment_type == environment_type:
                return env

        env = DeploymentEnvironment(
            environment_type=environment_type,
            trust_tier=trust_tier,
            capabilities=capabilities or [],
        )
        self._environments[env.environment_id] = env
        return env

    def add_edge(
        self,
        from_env: str,
        to_env: str,
        relationship: str = "depends_on",
    ) -> dict[str, str] | None:
        if from_env not in self._environments or to_env not in self._environments:
            return None
        if from_env == to_env:
            return None
        if len(self._edges) >= MAX_EDGES:
            return None

        for e in self._edges:
            if (e["from_env"] == from_env and e["to_env"] == to_env
                    and e["relationship"] == relationship):
                return e

        edge = {
            "from_env": from_env,
            "to_env": to_env,
            "relationship": relationship,
            "created_at": _now_iso(),
        }
        self._edges.append(edge)
        return edge

    def get_environment(self, env_id: str) -> dict[str, Any] | None:
        env = self._environments.get(env_id)
        return env.to_dict() if env else None

    def get_all_environments(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._environments.values()]

    def get_edges(self) -> list[dict[str, str]]:
        return list(self._edges)

    def get_topology_snapshot(self) -> DeploymentTopology:
        envs = sorted(self._environments.keys())
        return DeploymentTopology(
            environments=envs,
            edges=list(self._edges),
        )

    def get_topology_hash(self) -> str:
        envs = sorted(self._environments.keys())
        edges_str = ",".join(
            f"{e['from_env']}-{e['to_env']}" for e in sorted(
                self._edges, key=lambda x: (x["from_env"], x["to_env"])
            )
        )
        content = f"{','.join(envs)}:{edges_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def validate_topology(self) -> dict[str, Any]:
        issues: list[str] = []
        if not self._environments:
            issues.append("no environments registered")

        for edge in self._edges:
            if edge["from_env"] not in self._environments:
                issues.append(f"edge references missing env: {edge['from_env']}")
            if edge["to_env"] not in self._environments:
                issues.append(f"edge references missing env: {edge['to_env']}")

        return {
            "valid": len(issues) == 0,
            "environments": len(self._environments),
            "edges": len(self._edges),
            "issues": issues,
        }

    def get_stats(self) -> dict[str, object]:
        return {
            "total_environments": len(self._environments),
            "total_edges": len(self._edges),
            "known_environment_types": len(KNOWN_ENVIRONMENTS),
            "max_environments": MAX_ENVIRONMENTS,
        }
