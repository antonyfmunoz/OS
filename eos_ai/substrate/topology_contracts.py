"""
Setup-agnostic topology contracts for Phase 94D.4.

Defines topology, node, interface, and transport profiles that support
arbitrary user setups — not just the founder's VPS + local PC topology.

No hardcoded assumption that every user has a VPS.
No hardcoded assumption about which node is the orchestrator.
Topology is discovered during onboarding, not prescribed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    CLOUD_VPS = "cloud_vps"
    LOCAL_WORKSTATION = "local_workstation"
    PHONE = "phone"
    TABLET = "tablet"
    REMOTE_SERVER = "remote_server"
    EDGE_DEVICE = "edge_device"
    GPU_NODE = "gpu_node"
    EMBEDDED = "embedded"


class NodeRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    CONTROL_PLANE = "control_plane"
    WORKER = "worker"
    COMPUTER_USE_WORKER = "computer_use_worker"
    BROWSER_SESSION_NODE = "browser_session_node"
    LOCAL_FILE_NODE = "local_file_node"
    REPORTING_NODE = "reporting_node"
    INFERENCE_NODE = "inference_node"
    STORAGE_NODE = "storage_node"


class InterfaceRole(str, Enum):
    PRIMARY_COMMAND = "primary_command"
    SECONDARY_COMMAND = "secondary_command"
    VISUAL_SUPERVISION = "visual_supervision"
    NOTIFICATION_ONLY = "notification_only"
    READ_ONLY = "read_only"
    APPROVAL_CAPABLE = "approval_capable"


class TransportType(str, Enum):
    SSH = "ssh"
    TAILSCALE = "tailscale"
    HTTP_BRIDGE = "http_bridge"
    WEBSOCKET = "websocket"
    FILE_BUS = "file_bus"
    LOCAL_IPC = "local_ipc"
    DISCORD_API = "discord_api"
    TELEGRAM_API = "telegram_api"
    PUSH_NOTIFICATION = "push_notification"
    DIRECT_FUNCTION = "direct_function"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TransportProfile:
    transport_type: TransportType
    from_node: str
    to_node: str
    endpoint: str = ""
    port: int = 0
    authenticated: bool = False
    latency_ms: int | None = None
    healthy: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["transport_type"] = self.transport_type.value
        return d


@dataclass
class InterfaceProfile:
    interface_id: str
    interface_type: str
    role: InterfaceRole
    node_id: str
    capabilities: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    approval_capable: bool = False
    connected: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value
        return d


@dataclass
class NodeProfile:
    node_id: str
    node_type: NodeType
    roles: list[NodeRole]
    capabilities: list[str]
    hostname: str = ""
    os: str = ""
    ip: str = ""
    online: bool = False
    interfaces: list[InterfaceProfile] = field(default_factory=list)
    transports: list[TransportProfile] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: NodeRole) -> bool:
        return role in self.roles

    def has_capability(self, cap: str) -> bool:
        return cap in self.capabilities

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "roles": [r.value for r in self.roles],
            "capabilities": self.capabilities,
            "hostname": self.hostname,
            "os": self.os,
            "ip": self.ip,
            "online": self.online,
            "interfaces": [i.to_dict() for i in self.interfaces],
            "transports": [t.to_dict() for t in self.transports],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeProfile:
        return cls(
            node_id=data["node_id"],
            node_type=NodeType(data["node_type"]),
            roles=[NodeRole(r) for r in data.get("roles", [])],
            capabilities=data.get("capabilities", []),
            hostname=data.get("hostname", ""),
            os=data.get("os", ""),
            ip=data.get("ip", ""),
            online=data.get("online", False),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TopologyProfile:
    topology_id: str
    owner_id: str
    nodes: list[NodeProfile]
    discovered_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> NodeProfile | None:
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def nodes_with_role(self, role: NodeRole) -> list[NodeProfile]:
        return [n for n in self.nodes if n.has_role(role)]

    def nodes_with_capability(self, cap: str) -> list[NodeProfile]:
        return [n for n in self.nodes if n.has_capability(cap)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "owner_id": self.owner_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "discovered_at": self.discovered_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TopologyProfile:
        return cls(
            topology_id=data["topology_id"],
            owner_id=data["owner_id"],
            nodes=[NodeProfile.from_dict(n) for n in data.get("nodes", [])],
            discovered_at=data.get("discovered_at", _now_iso()),
            metadata=data.get("metadata", {}),
        )


def build_founder_current_topology() -> TopologyProfile:
    """Build the founder's actual current topology as a reference instance."""
    vps = NodeProfile(
        node_id="vps_orchestrator",
        node_type=NodeType.CLOUD_VPS,
        roles=[NodeRole.ORCHESTRATOR, NodeRole.CONTROL_PLANE, NodeRole.REPORTING_NODE],
        capabilities=[
            "llm_inference",
            "orchestration",
            "scheduling",
            "api_access",
            "file_storage",
            "docker",
        ],
        hostname="srv1500858",
        os="linux",
        ip="100.77.233.50",
        online=True,
    )
    local_pc = NodeProfile(
        node_id="local_pc_worker",
        node_type=NodeType.LOCAL_WORKSTATION,
        roles=[
            NodeRole.WORKER,
            NodeRole.COMPUTER_USE_WORKER,
            NodeRole.BROWSER_SESSION_NODE,
            NodeRole.LOCAL_FILE_NODE,
        ],
        capabilities=[
            "gui_computer_use",
            "browser_session",
            "local_files",
            "screen_control",
            "audio",
        ],
        hostname="desktop-lvguiq9",
        os="windows_wsl",
        ip="100.74.199.102",
        online=True,
    )
    return TopologyProfile(
        topology_id="founder_current",
        owner_id="antonyfm",
        nodes=[vps, local_pc],
    )


def build_single_local_topology(owner_id: str = "user") -> TopologyProfile:
    """Topology where one local machine does everything."""
    node = NodeProfile(
        node_id="local_machine",
        node_type=NodeType.LOCAL_WORKSTATION,
        roles=[
            NodeRole.ORCHESTRATOR,
            NodeRole.WORKER,
            NodeRole.COMPUTER_USE_WORKER,
            NodeRole.LOCAL_FILE_NODE,
        ],
        capabilities=[
            "gui_computer_use",
            "browser_session",
            "local_files",
            "llm_inference",
            "orchestration",
        ],
        online=True,
    )
    return TopologyProfile(
        topology_id="single_local",
        owner_id=owner_id,
        nodes=[node],
    )
