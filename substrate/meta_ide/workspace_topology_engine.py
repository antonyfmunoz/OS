"""Workspace Topology Engine — live workspace topology with health.

Composes WorkspaceRegistry + WorkspaceObservationEngine (Phase 25) +
DistributedRuntime (Phase 24) into a unified topology view with
computed health status.

Read-only. No execution authority. No deployment.

Phase 27. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from substrate.meta_ide.workspace_registry import WorkspaceRegistry
from substrate.meta_ide.workspace_runtime_graph import (
    WorkspaceBuildTarget,
    WorkspaceDefinition,
    WorkspaceHealth,
    WorkspaceRuntimeGraph,
)

logger = logging.getLogger(__name__)


class WorkspaceTopologyEngine:
    """Composes workspace registry with live observation and runtime data.

    Produces WorkspaceRuntimeGraph snapshots enriched with live health.
    """

    def __init__(
        self,
        registry: WorkspaceRegistry | None = None,
        observation_engine: Any | None = None,
        distributed_runtime: Any | None = None,
    ) -> None:
        self._registry = registry or WorkspaceRegistry()
        self._observation_engine = observation_engine
        self._distributed_runtime = distributed_runtime

    def _get_observation_engine(self) -> Any | None:
        if self._observation_engine is not None:
            return self._observation_engine
        try:
            from substrate.meta_ide.workspace_observation import (
                WorkspaceObservationEngine,
            )

            self._observation_engine = WorkspaceObservationEngine()
            return self._observation_engine
        except Exception:
            logger.debug("WorkspaceObservationEngine not available")
            return None

    def _get_distributed_runtime(self) -> Any | None:
        if self._distributed_runtime is not None:
            return self._distributed_runtime
        try:
            from substrate.organism.distributed_runtime import DistributedRuntime

            self._distributed_runtime = DistributedRuntime()
            return self._distributed_runtime
        except Exception:
            logger.debug("DistributedRuntime not available")
            return None

    def topology(self) -> WorkspaceRuntimeGraph:
        workspaces = self._registry.list_workspaces()
        enriched = []
        for ws in workspaces:
            health = self._compute_health(ws)
            enriched_ws = WorkspaceDefinition(
                workspace_id=ws.workspace_id,
                name=ws.name,
                workspace_type=ws.workspace_type,
                repositories=ws.repositories,
                runtimes=ws.runtimes,
                build_targets=ws.build_targets,
                device_ids=ws.device_ids,
                primary_umh_node_id=ws.primary_umh_node_id,
                supporting_umh_node_ids=ws.supporting_umh_node_ids,
                health=health,
            )
            enriched.append(enriched_ws)

        return WorkspaceRuntimeGraph(workspaces=enriched)

    def workspace_health(self, workspace_id: str) -> WorkspaceHealth:
        ws = self._registry.get(workspace_id)
        if not ws:
            return WorkspaceHealth.UNKNOWN
        return self._compute_health(ws)

    def workspace_summary(self, workspace_id: str) -> dict[str, Any] | None:
        ws = self._registry.get(workspace_id)
        if not ws:
            return None

        health = self._compute_health(ws)
        summary = ws.to_dict()
        summary["computed_health"] = health.value
        summary["device_status"] = self._device_status(ws)
        summary["observation"] = self._latest_observation_for(ws)
        return summary

    def preferred_build_target(self, workspace_id: str) -> WorkspaceBuildTarget | None:
        ws = self._registry.get(workspace_id)
        if not ws:
            return None
        for bt in ws.build_targets:
            if bt.preferred:
                return bt
        return ws.build_targets[0] if ws.build_targets else None

    def _compute_health(self, ws: WorkspaceDefinition) -> WorkspaceHealth:
        obs_engine = self._get_observation_engine()
        if obs_engine is None:
            return WorkspaceHealth.UNKNOWN

        snapshot = obs_engine.latest()
        if snapshot is None:
            return WorkspaceHealth.UNKNOWN

        snap_dict = snapshot.to_dict()
        containers = snap_dict.get("containers", [])
        if not containers and not ws.runtimes:
            return WorkspaceHealth.UNKNOWN

        ws_runtime_ids = {r.runtime_id for r in ws.runtimes}
        ws_device_ids = set(ws.device_ids)

        relevant_containers = [
            c
            for c in containers
            if c.get("container_name", "") in ws_runtime_ids
            or any(did in ws_device_ids for did in [c.get("host_id", "")])
        ]

        if not relevant_containers:
            device_info = self._device_status(ws)
            if device_info:
                online_count = sum(1 for d in device_info if d.get("online", False))
                if online_count == 0:
                    return WorkspaceHealth.BLOCKED
                if online_count < len(device_info):
                    return WorkspaceHealth.DEGRADED
                return WorkspaceHealth.HEALTHY
            return WorkspaceHealth.UNKNOWN

        unhealthy = 0
        for c in relevant_containers:
            status = c.get("status", "")
            health = c.get("health", "unknown")
            if not status.startswith("Up"):
                unhealthy += 1
            elif health in ("crashed", "unhealthy"):
                unhealthy += 1

        if unhealthy == len(relevant_containers):
            return WorkspaceHealth.BLOCKED
        if unhealthy > 0:
            return WorkspaceHealth.DEGRADED
        return WorkspaceHealth.HEALTHY

    def _device_status(self, ws: WorkspaceDefinition) -> list[dict[str, Any]]:
        dr = self._get_distributed_runtime()
        if dr is None:
            return []
        result = []
        for device_id in ws.device_ids:
            try:
                summary = dr.device_summary(device_id)
                if summary:
                    result.append(summary)
                else:
                    result.append({"device_id": device_id, "online": False})
            except Exception:
                result.append({"device_id": device_id, "online": False})
        return result

    def _latest_observation_for(self, ws: WorkspaceDefinition) -> dict[str, Any] | None:
        obs_engine = self._get_observation_engine()
        if obs_engine is None:
            return None
        snapshot = obs_engine.latest()
        if snapshot is None:
            return None

        snap_dict = snapshot.to_dict()
        ws_device_ids = set(ws.device_ids)
        filtered = {
            "containers": [
                c for c in snap_dict.get("containers", []) if c.get("host_id", "") in ws_device_ids
            ],
            "terminals": [
                t for t in snap_dict.get("terminals", []) if t.get("host_id", "") in ws_device_ids
            ],
            "previews": snap_dict.get("previews", []),
            "observed_at": snap_dict.get("observed_at", 0),
        }
        return filtered

    def workspace_nodes(self, workspace_id: str) -> dict[str, Any] | None:
        """Return primary and supporting UMH node info for a workspace."""
        ws = self._registry.get(workspace_id)
        if not ws:
            return None

        result: dict[str, Any] = {
            "workspace_id": workspace_id,
            "primary_umh_node_id": ws.primary_umh_node_id,
            "supporting_umh_node_ids": ws.supporting_umh_node_ids,
        }

        try:
            from substrate.organism.umh_node_registry import UMHNodeRegistry

            node_reg = UMHNodeRegistry()
            primary = node_reg.get_node(ws.primary_umh_node_id) if ws.primary_umh_node_id else None
            result["primary_node"] = primary.to_dict() if primary else None
            supporting = []
            for nid in ws.supporting_umh_node_ids:
                node = node_reg.get_node(nid)
                if node:
                    supporting.append(node.to_dict())
            result["supporting_nodes"] = supporting
        except Exception:
            logger.debug("UMHNodeRegistry not available for workspace_nodes")
            result["primary_node"] = None
            result["supporting_nodes"] = []

        return result

    @property
    def registry(self) -> WorkspaceRegistry:
        return self._registry
