"""Phase 87A distributed node registry — default node profiles.

Registers the VPS and Local PC as the initial two-node topology.
Future nodes (mobile, cloud GPU, edge, robotics) are registered
with FUTURE availability.

No execution. No mutation. No adapter calls. No LLM calls.
No network listeners. No secrets.
"""

from __future__ import annotations

from typing import Any

from umh.distributed.contracts import (
    CapabilityDomain,
    NodeAvailability,
    NodeRole,
    RuntimeNodeProfile,
    RuntimeNodeType,
    _dist_id,
    normalize_node_type,
)


def create_node_profile(
    name: str,
    node_type: str | RuntimeNodeType,
    roles: list[NodeRole] | None = None,
    availability: NodeAvailability = NodeAvailability.UNKNOWN,
    capabilities: list[CapabilityDomain] | None = None,
    description: str = "",
    hostname: str = "",
    os_family: str = "",
    cpu_cores: float = 0.0,
    memory_gb: float = 0.0,
    gpu: bool = False,
    storage_gb: float = 0.0,
    network_policy: str = "",
    safe_roots: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RuntimeNodeProfile:
    return RuntimeNodeProfile(
        node_id=_dist_id("node"),
        name=name,
        node_type=normalize_node_type(node_type),
        roles=roles or [],
        availability=availability,
        capabilities=capabilities or [],
        description=description,
        hostname=hostname,
        os_family=os_family,
        cpu_cores=cpu_cores,
        memory_gb=memory_gb,
        gpu=gpu,
        storage_gb=storage_gb,
        network_policy=network_policy,
        safe_roots=safe_roots or [],
        metadata=metadata or {},
    )


def build_default_node_profiles() -> list[RuntimeNodeProfile]:
    return [
        create_node_profile(
            name="Primary VPS",
            node_type=RuntimeNodeType.VPS,
            roles=[
                NodeRole.PRIMARY_COMPUTE,
                NodeRole.DEVELOPMENT,
                NodeRole.MONITORING,
            ],
            availability=NodeAvailability.ALWAYS_ON,
            capabilities=[
                CapabilityDomain.COMPUTE,
                CapabilityDomain.STORAGE,
                CapabilityDomain.NETWORK,
                CapabilityDomain.DOCKER,
                CapabilityDomain.SSH,
                CapabilityDomain.FILESYSTEM,
            ],
            description="Hetzner VPS — primary compute, Docker host, Claude Code runtime, all services",
            hostname="100.77.233.50",
            os_family="linux",
            cpu_cores=4.0,
            memory_gb=8.0,
            storage_gb=80.0,
            network_policy="allow_https",
            safe_roots=["/opt/OS", "/tmp/umh"],
        ),
        create_node_profile(
            name="Local PC (Windows)",
            node_type=RuntimeNodeType.LOCAL_PC,
            roles=[
                NodeRole.LOCAL_EMBODIMENT,
                NodeRole.DEVELOPMENT,
                NodeRole.INGESTION,
            ],
            availability=NodeAvailability.INTERMITTENT,
            capabilities=[
                CapabilityDomain.COMPUTE,
                CapabilityDomain.STORAGE,
                CapabilityDomain.NETWORK,
                CapabilityDomain.BROWSER,
                CapabilityDomain.DISPLAY,
                CapabilityDomain.AUDIO,
                CapabilityDomain.FILESYSTEM,
                CapabilityDomain.LOCAL_ACCOUNTS,
                CapabilityDomain.USB,
            ],
            description="Windows desktop — VS Code, browser, local files, logged-in accounts, media production",
            os_family="windows",
            cpu_cores=8.0,
            memory_gb=32.0,
            gpu=True,
            storage_gb=1000.0,
            network_policy="allow_all",
            safe_roots=["C:\\Users\\Antony\\Projects", "C:\\Users\\Antony\\Documents"],
        ),
        create_node_profile(
            name="iPhone (Termius)",
            node_type=RuntimeNodeType.MOBILE,
            roles=[NodeRole.EDGE_SENSOR, NodeRole.MONITORING],
            availability=NodeAvailability.INTERMITTENT,
            capabilities=[
                CapabilityDomain.SSH,
                CapabilityDomain.DISPLAY,
                CapabilityDomain.CAMERA,
                CapabilityDomain.LOCATION,
                CapabilityDomain.BLUETOOTH,
                CapabilityDomain.AUDIO,
            ],
            description="iPhone — SSH into VPS via Termius, quick commands, monitoring",
            os_family="ios",
            metadata={"status": "active", "access_method": "termius_ssh"},
        ),
        create_node_profile(
            name="iPad (code-server)",
            node_type=RuntimeNodeType.TABLET,
            roles=[NodeRole.DEVELOPMENT, NodeRole.LOCAL_EMBODIMENT],
            availability=NodeAvailability.INTERMITTENT,
            capabilities=[
                CapabilityDomain.BROWSER,
                CapabilityDomain.DISPLAY,
                CapabilityDomain.NETWORK,
            ],
            description="iPad — full VS Code via code-server on VPS, browser-based development",
            os_family="ipados",
            metadata={"status": "active", "access_method": "code_server_browser"},
        ),
        create_node_profile(
            name="Future Cloud GPU",
            node_type=RuntimeNodeType.CLOUD_GPU,
            roles=[NodeRole.GPU_BURST],
            availability=NodeAvailability.FUTURE,
            capabilities=[
                CapabilityDomain.COMPUTE,
                CapabilityDomain.GPU,
                CapabilityDomain.STORAGE,
                CapabilityDomain.NETWORK,
            ],
            description="Future cloud GPU instance for model training, inference, media processing",
            metadata={"status": "future"},
        ),
        create_node_profile(
            name="Future Cloud CPU Burst",
            node_type=RuntimeNodeType.CLOUD_CPU,
            roles=[NodeRole.PRIMARY_COMPUTE, NodeRole.STORAGE_ARCHIVE],
            availability=NodeAvailability.FUTURE,
            capabilities=[
                CapabilityDomain.COMPUTE,
                CapabilityDomain.STORAGE,
                CapabilityDomain.NETWORK,
                CapabilityDomain.DOCKER,
            ],
            description="Future cloud CPU burst for scale-out compute and archival",
            metadata={"status": "future"},
        ),
        create_node_profile(
            name="Future Edge Devices",
            node_type=RuntimeNodeType.EDGE_DEVICE,
            roles=[NodeRole.EDGE_SENSOR, NodeRole.MONITORING],
            availability=NodeAvailability.FUTURE,
            capabilities=[
                CapabilityDomain.NETWORK,
                CapabilityDomain.BLUETOOTH,
                CapabilityDomain.LOCATION,
            ],
            description="Future IoT/edge devices for environment sensing, home automation",
            metadata={"status": "future"},
        ),
        create_node_profile(
            name="Future Robotics Node",
            node_type=RuntimeNodeType.ROBOTICS,
            roles=[NodeRole.EDGE_SENSOR],
            availability=NodeAvailability.FUTURE,
            capabilities=[
                CapabilityDomain.COMPUTE,
                CapabilityDomain.CAMERA,
                CapabilityDomain.USB,
                CapabilityDomain.BLUETOOTH,
            ],
            description="Future robotics/3D-printing/CNC node for physical product sovereignty",
            metadata={"status": "future"},
        ),
    ]


def classify_node(
    name: str,
    description: str | None = None,
    context: str | None = None,
) -> RuntimeNodeType:
    key = (name + " " + (description or "") + " " + (context or "")).lower()

    _MAP: list[tuple[list[str], RuntimeNodeType]] = [
        (["gpu", "cuda", "tensor", "training", "inference"], RuntimeNodeType.CLOUD_GPU),
        (["robot", "cnc", "3d print", "actuator"], RuntimeNodeType.ROBOTICS),
        (["edge", "iot", "sensor", "raspberry"], RuntimeNodeType.EDGE_DEVICE),
        (["cloud", "aws", "gcp", "azure", "hetzner cloud"], RuntimeNodeType.CLOUD_CPU),
        (["mobile", "iphone", "android", "phone"], RuntimeNodeType.MOBILE),
        (["tablet", "ipad"], RuntimeNodeType.TABLET),
        (["vps", "server", "dedicated", "hetzner"], RuntimeNodeType.VPS),
        (["local", "desktop", "workstation", "pc", "windows", "mac"], RuntimeNodeType.LOCAL_PC),
    ]

    for keywords, ntype in _MAP:
        if any(kw in key for kw in keywords):
            return ntype
    return RuntimeNodeType.UNKNOWN


def get_active_nodes(profiles: list[RuntimeNodeProfile] | None = None) -> list[RuntimeNodeProfile]:
    if profiles is None:
        profiles = build_default_node_profiles()
    return [
        p
        for p in profiles
        if p.availability
        in (
            NodeAvailability.ALWAYS_ON,
            NodeAvailability.ON_DEMAND,
            NodeAvailability.INTERMITTENT,
            NodeAvailability.SCHEDULED,
        )
    ]


def get_future_nodes(profiles: list[RuntimeNodeProfile] | None = None) -> list[RuntimeNodeProfile]:
    if profiles is None:
        profiles = build_default_node_profiles()
    return [p for p in profiles if p.availability == NodeAvailability.FUTURE]


def node_profile_to_dict(p: RuntimeNodeProfile) -> dict[str, Any]:
    return p.to_dict()


def node_profile_from_dict(d: dict[str, Any]) -> RuntimeNodeProfile:
    return RuntimeNodeProfile.from_dict(d)
