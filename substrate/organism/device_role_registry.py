"""Device role registry — tracks device roles and capabilities in the UMH organism.

Phase 13.4M. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class DeviceRole(str, Enum):
    """Role a device plays in the UMH organism."""

    CONTROL_PLANE = "control_plane"
    HEAVY_WORKSTATION = "heavy_workstation"
    COCKPIT_UI = "cockpit_ui"
    MOBILE_OPERATOR = "mobile_operator"
    EXTERNAL_SERVICE = "external_service"
    STORAGE_SURFACE = "storage_surface"
    UNKNOWN = "unknown"


class DeviceCapability(str, Enum):
    """Capability a device can provide."""

    CPU_LIGHT = "cpu_light"
    CPU_HEAVY = "cpu_heavy"
    GPU_AVAILABLE = "gpu_available"
    BROWSER_AUTOMATION = "browser_automation"
    DESKTOP_AUTOMATION = "desktop_automation"
    CONTAINER_RUNTIME = "container_runtime"
    LOCAL_MODELS = "local_models"
    CODE_EXECUTION = "code_execution"
    MEDIA_GENERATION = "media_generation"
    FILE_ACCESS = "file_access"
    NETWORK_ACCESS = "network_access"
    LONG_RUNNING_SESSIONS = "long_running_sessions"
    LOW_LATENCY_UI = "low_latency_ui"
    CANONICAL_STATE = "canonical_state"
    PUBLIC_API = "public_api"
    PRIVATE_MESH = "private_mesh"


@dataclass
class DeviceNodeProfile:
    """Profile describing a device node in the organism."""

    node_id: str  # "dn-<8hex>"
    device_name: str
    role: DeviceRole
    os: str  # "linux", "windows", "web", "ios"
    location: str  # "vps", "home", "cloud", "mobile"
    trust_level: str  # "full", "high", "medium", "low"
    online_status: str  # "online", "offline", "unknown"
    capabilities: list[DeviceCapability] = field(default_factory=list)
    allowed_workloads: list[str] = field(default_factory=list)
    blocked_workloads: list[str] = field(default_factory=list)
    max_risk_class: str = "low"  # "low", "medium", "high", "critical"
    preferred_runtimes: list[str] = field(default_factory=list)
    resource_notes: str = ""
    last_seen_at: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON persistence."""
        return {
            "node_id": self.node_id,
            "device_name": self.device_name,
            "role": self.role.value,
            "os": self.os,
            "location": self.location,
            "trust_level": self.trust_level,
            "online_status": self.online_status,
            "capabilities": [c.value for c in self.capabilities],
            "allowed_workloads": list(self.allowed_workloads),
            "blocked_workloads": list(self.blocked_workloads),
            "max_risk_class": self.max_risk_class,
            "preferred_runtimes": list(self.preferred_runtimes),
            "resource_notes": self.resource_notes,
            "last_seen_at": self.last_seen_at,
            "evidence": dict(self.evidence),
        }


def node_from_dict(data: dict[str, Any]) -> DeviceNodeProfile:
    """Reconstruct a DeviceNodeProfile from a dict."""
    return DeviceNodeProfile(
        node_id=data["node_id"],
        device_name=data["device_name"],
        role=DeviceRole(data["role"]),
        os=data["os"],
        location=data["location"],
        trust_level=data["trust_level"],
        online_status=data["online_status"],
        capabilities=[DeviceCapability(c) for c in data.get("capabilities", [])],
        allowed_workloads=data.get("allowed_workloads", []),
        blocked_workloads=data.get("blocked_workloads", []),
        max_risk_class=data.get("max_risk_class", "low"),
        preferred_runtimes=data.get("preferred_runtimes", []),
        resource_notes=data.get("resource_notes", ""),
        last_seen_at=data.get("last_seen_at", ""),
        evidence=data.get("evidence", {}),
    )


def _default_registry_path(persist_dir: str | None = None) -> Path:
    """Return the canonical registry file path."""
    if persist_dir:
        return Path(persist_dir) / "device_role_registry.jsonl"
    return Path(_REPO_ROOT) / "data" / "umh" / "operational_truth" / "device_role_registry.jsonl"


def seed_known_nodes() -> list[DeviceNodeProfile]:
    """Return the three known UMH device nodes with their profiles."""
    vps = DeviceNodeProfile(
        node_id="dn-a1b2c3d4",
        device_name="VPS Control Plane",
        role=DeviceRole.CONTROL_PLANE,
        os="linux",
        location="vps",
        trust_level="full",
        online_status="online",
        capabilities=[
            DeviceCapability.CPU_LIGHT,
            DeviceCapability.CODE_EXECUTION,
            DeviceCapability.FILE_ACCESS,
            DeviceCapability.NETWORK_ACCESS,
            DeviceCapability.LONG_RUNNING_SESSIONS,
            DeviceCapability.CANONICAL_STATE,
            DeviceCapability.PUBLIC_API,
            DeviceCapability.PRIVATE_MESH,
        ],
        allowed_workloads=[
            "governance",
            "api",
            "scheduling",
            "lightweight_probes",
            "audit_persistence",
            "coordination",
            "eventbus",
        ],
        blocked_workloads=[
            "heavy_computation",
            "gpu_workloads",
            "browser_automation",
            "media_generation",
            "large_model_inference",
        ],
        max_risk_class="low",
        preferred_runtimes=["shell", "claude_code", "cc_sdk"],
        resource_notes="Lightweight orchestrator. No GPU. Avoid heavy compute.",
    )

    beast = DeviceNodeProfile(
        node_id="dn-e5f6a7b8",
        device_name="Windows Beast",
        role=DeviceRole.HEAVY_WORKSTATION,
        os="windows",
        location="home",
        trust_level="full",
        online_status="online",
        capabilities=[
            DeviceCapability.CPU_HEAVY,
            DeviceCapability.GPU_AVAILABLE,
            DeviceCapability.BROWSER_AUTOMATION,
            DeviceCapability.DESKTOP_AUTOMATION,
            DeviceCapability.CONTAINER_RUNTIME,
            DeviceCapability.LOCAL_MODELS,
            DeviceCapability.CODE_EXECUTION,
            DeviceCapability.MEDIA_GENERATION,
            DeviceCapability.FILE_ACCESS,
            DeviceCapability.NETWORK_ACCESS,
            DeviceCapability.LONG_RUNNING_SESSIONS,
            DeviceCapability.PRIVATE_MESH,
        ],
        allowed_workloads=[
            "heavy_execution",
            "coding_workcells",
            "browser_automation",
            "computer_use",
            "media_generation",
            "local_models",
            "containerized_workloads",
            "long_running_agents",
            "sandbox_runtime",
        ],
        blocked_workloads=[
            "canonical_state_ownership",
            "production_truth_mutations",
        ],
        max_risk_class="medium",
        preferred_runtimes=["claude_code", "codex", "opencode", "hermes", "shell", "browser"],
        resource_notes="GPU workhorse. Full compute. Not canonical state owner.",
    )

    cockpit = DeviceNodeProfile(
        node_id="dn-c9d0e1f2",
        device_name="Fly Cockpit",
        role=DeviceRole.COCKPIT_UI,
        os="web",
        location="cloud",
        trust_level="medium",
        online_status="online",
        capabilities=[
            DeviceCapability.LOW_LATENCY_UI,
            DeviceCapability.NETWORK_ACCESS,
            DeviceCapability.PUBLIC_API,
        ],
        allowed_workloads=[
            "operator_interface",
            "cockpit_rendering",
            "api_proxy",
        ],
        blocked_workloads=[
            "heavy_execution",
            "canonical_state",
            "source_of_truth",
            "runtime_execution",
        ],
        max_risk_class="low",
        preferred_runtimes=[],
        resource_notes="UI surface only. No execution capability.",
    )

    return [vps, beast, cockpit]


def persist_registry(
    nodes: list[DeviceNodeProfile],
    persist_dir: str | None = None,
) -> Path:
    """Write device node profiles to the registry JSONL file."""
    path = _default_registry_path(persist_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for node in nodes:
            f.write(json.dumps(node.to_dict()) + "\n")
    return path


def load_registry(persist_dir: str | None = None) -> list[DeviceNodeProfile]:
    """Load all device node profiles from the registry JSONL file."""
    path = _default_registry_path(persist_dir)
    if not path.exists():
        return []
    nodes: list[DeviceNodeProfile] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                nodes.append(node_from_dict(json.loads(line)))
    return nodes


def get_node(node_id: str, persist_dir: str | None = None) -> DeviceNodeProfile | None:
    """Look up a single node by its node_id."""
    for node in load_registry(persist_dir):
        if node.node_id == node_id:
            return node
    return None


def get_nodes_by_role(
    role: DeviceRole,
    persist_dir: str | None = None,
) -> list[DeviceNodeProfile]:
    """Return all nodes matching a given role."""
    return [n for n in load_registry(persist_dir) if n.role == role]
