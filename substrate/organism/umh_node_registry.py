"""UMH Node Registry — canonical registry of UMH organism nodes.

Single source of truth for which nodes compose the UMH organism,
what role each plays, what services each runs, and what workspaces
each serves. Loads seed data from infra/umh_node_registry.json.

Phase 28. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from substrate.organism.umh_node_topology import (
    UMHNodeRecord,
    UMHNodeTopology,
    UMHServiceActivation,
    UMHVersionInfo,
)

logger = logging.getLogger(__name__)


def _find_registry_path() -> str:
    """Locate umh_node_registry.json, checking UMH_ROOT and file-relative."""
    root = os.environ.get("UMH_ROOT", "/opt/OS")
    candidate = os.path.join(root, "infra", "umh_node_registry.json")
    if os.path.exists(candidate):
        return candidate
    here = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.normpath(os.path.join(here, "..", "..", "infra", "umh_node_registry.json"))
    return fallback


def _load_seed_nodes() -> list[UMHNodeRecord]:
    """Load node definitions from infra/umh_node_registry.json."""
    registry_path = _find_registry_path()
    try:
        with open(registry_path) as f:
            entries = json.load(f)
    except Exception:
        logger.debug("Could not load UMH node registry from %s", registry_path)
        return []

    nodes: list[UMHNodeRecord] = []
    for entry in entries:
        node_id = entry.get("node_id", "")
        if not node_id:
            continue

        service_names = entry.get("active_services", [])
        services: list[UMHServiceActivation] = []
        if isinstance(service_names, list):
            for svc in service_names:
                if isinstance(svc, str):
                    services.append(
                        UMHServiceActivation(
                            service_id=f"{node_id}-{svc}",
                            node_id=node_id,
                            service_role=svc,
                            active=True,
                        )
                    )
                elif isinstance(svc, dict):
                    services.append(UMHServiceActivation.from_dict(svc))

        version_data = entry.get("version", {})
        version = UMHVersionInfo.from_dict(version_data) if version_data else UMHVersionInfo()

        nodes.append(
            UMHNodeRecord(
                node_id=node_id,
                device_id=entry.get("device_id", ""),
                hostname=entry.get("hostname", ""),
                purpose=entry.get("purpose", ""),
                roles=entry.get("roles", []),
                status=entry.get("status", "unknown"),
                version=version,
                active_services=services,
                capability_ids=entry.get("capability_ids", []),
                workspace_ids=entry.get("workspace_ids", []),
                owned_state_domains=entry.get("owned_state_domains", []),
                primary=entry.get("primary", False),
                last_seen=entry.get("last_seen", 0.0),
                metadata=entry.get("metadata", {}),
            )
        )

    return nodes


class UMHNodeRegistry:
    """Single source of truth for UMH organism node topology."""

    def __init__(self, seed: bool = True) -> None:
        self._nodes: dict[str, UMHNodeRecord] = {}
        if seed:
            for node in _load_seed_nodes():
                self._nodes[node.node_id] = node

    def list_nodes(self) -> list[UMHNodeRecord]:
        return list(self._nodes.values())

    def get_node(self, node_id: str) -> UMHNodeRecord | None:
        return self._nodes.get(node_id)

    def nodes_for_device(self, device_id: str) -> list[UMHNodeRecord]:
        return [n for n in self._nodes.values() if n.device_id == device_id]

    def nodes_for_role(self, role: str) -> list[UMHNodeRecord]:
        return [n for n in self._nodes.values() if role in n.roles]

    def nodes_for_service(self, service_role: str) -> list[UMHNodeRecord]:
        return [
            n
            for n in self._nodes.values()
            if any(s.service_role == service_role for s in n.active_services)
        ]

    def nodes_for_workspace(self, workspace_id: str) -> list[UMHNodeRecord]:
        return [n for n in self._nodes.values() if workspace_id in n.workspace_ids]

    def primary_node(self) -> UMHNodeRecord | None:
        for n in self._nodes.values():
            if n.primary:
                return n
        return None

    def register_node(self, record: UMHNodeRecord) -> None:
        self._nodes[record.node_id] = record
        logger.info(
            "UMH node registered: %s (%s)",
            record.node_id,
            record.purpose,
        )

    def topology(self) -> UMHNodeTopology:
        return UMHNodeTopology(
            nodes=list(self._nodes.values()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": len(self._nodes),
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
        }
