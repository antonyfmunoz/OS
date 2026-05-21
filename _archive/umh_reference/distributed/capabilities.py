"""Phase 87A capability taxonomy — maps capabilities to nodes and sources.

Defines what each node can do, what each source requires, and
maps source ingestion requirements to capable nodes.

No execution. No mutation. No adapter calls. No LLM calls.
No network listeners. No secrets.
"""

from __future__ import annotations

from typing import Any

from umh.distributed.contracts import (
    CapabilityDomain,
    NodeCapability,
    RuntimeNodeType,
    SourceAffinity,
    _dist_id,
    normalize_capability_domain,
)


def build_default_capabilities() -> list[NodeCapability]:
    return [
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.COMPUTE,
            name="General Compute",
            description="CPU-based task execution",
            required_node_types=[
                RuntimeNodeType.VPS,
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.CLOUD_CPU,
                RuntimeNodeType.CLOUD_GPU,
            ],
            source_affinity=SourceAffinity.ANY_NODE,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.GPU,
            name="GPU Compute",
            description="GPU-accelerated processing — training, inference, media rendering",
            required_node_types=[
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.CLOUD_GPU,
            ],
            source_affinity=SourceAffinity.GPU_REQUIRED,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.BROWSER,
            name="Browser Interaction",
            description="Web browser with logged-in sessions, cookies, saved passwords",
            required_node_types=[
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.TABLET,
            ],
            source_affinity=SourceAffinity.LOCAL_ONLY,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.LOCAL_ACCOUNTS,
            name="Local Account Access",
            description="Access to logged-in social media, email, banking, SaaS accounts",
            required_node_types=[RuntimeNodeType.LOCAL_PC],
            source_affinity=SourceAffinity.LOCAL_ONLY,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.DOCKER,
            name="Docker Containers",
            description="Container-based execution and service orchestration",
            required_node_types=[
                RuntimeNodeType.VPS,
                RuntimeNodeType.CLOUD_CPU,
            ],
            source_affinity=SourceAffinity.VPS_PREFERRED,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.SSH,
            name="SSH Access",
            description="Remote shell access to other nodes",
            required_node_types=[
                RuntimeNodeType.VPS,
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.MOBILE,
            ],
            source_affinity=SourceAffinity.ANY_NODE,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.FILESYSTEM,
            name="Filesystem Access",
            description="Read/write access to local or remote filesystems",
            required_node_types=[
                RuntimeNodeType.VPS,
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.CLOUD_CPU,
            ],
            source_affinity=SourceAffinity.ANY_NODE,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.STORAGE,
            name="Persistent Storage",
            description="Durable data storage for artifacts, databases, archives",
            required_node_types=[
                RuntimeNodeType.VPS,
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.CLOUD_CPU,
            ],
            source_affinity=SourceAffinity.VPS_PREFERRED,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.NETWORK,
            name="Network Access",
            description="HTTP/HTTPS outbound requests, API calls",
            required_node_types=[
                RuntimeNodeType.VPS,
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.CLOUD_CPU,
                RuntimeNodeType.CLOUD_GPU,
                RuntimeNodeType.MOBILE,
            ],
            source_affinity=SourceAffinity.ANY_NODE,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.DISPLAY,
            name="Display / Screen",
            description="Visual output — GUI applications, browser rendering",
            required_node_types=[
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.MOBILE,
                RuntimeNodeType.TABLET,
            ],
            source_affinity=SourceAffinity.LOCAL_PREFERRED,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.AUDIO,
            name="Audio I/O",
            description="Audio input/output — microphone, speakers, audio processing",
            required_node_types=[
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.MOBILE,
            ],
            source_affinity=SourceAffinity.LOCAL_ONLY,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.CAMERA,
            name="Camera Access",
            description="Camera/webcam — photo/video capture, scanning",
            required_node_types=[
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.MOBILE,
            ],
            source_affinity=SourceAffinity.LOCAL_ONLY,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.LOCATION,
            name="Location Services",
            description="GPS/location data from mobile devices",
            required_node_types=[RuntimeNodeType.MOBILE],
            source_affinity=SourceAffinity.LOCAL_ONLY,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.BLUETOOTH,
            name="Bluetooth",
            description="Bluetooth connectivity for peripherals and IoT",
            required_node_types=[
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.MOBILE,
                RuntimeNodeType.EDGE_DEVICE,
            ],
            source_affinity=SourceAffinity.LOCAL_ONLY,
        ),
        NodeCapability(
            capability_id=_dist_id("cap"),
            domain=CapabilityDomain.USB,
            name="USB Peripherals",
            description="USB device access — external drives, cameras, instruments",
            required_node_types=[
                RuntimeNodeType.LOCAL_PC,
                RuntimeNodeType.ROBOTICS,
            ],
            source_affinity=SourceAffinity.LOCAL_ONLY,
        ),
    ]


_SOURCE_TO_CAPABILITIES: dict[str, list[CapabilityDomain]] = {
    "instagram": [CapabilityDomain.BROWSER, CapabilityDomain.LOCAL_ACCOUNTS],
    "tiktok": [CapabilityDomain.BROWSER, CapabilityDomain.LOCAL_ACCOUNTS],
    "youtube": [CapabilityDomain.NETWORK],
    "twitter": [CapabilityDomain.BROWSER, CapabilityDomain.LOCAL_ACCOUNTS],
    "linkedin": [CapabilityDomain.BROWSER, CapabilityDomain.LOCAL_ACCOUNTS],
    "discord": [CapabilityDomain.NETWORK],
    "telegram": [CapabilityDomain.NETWORK],
    "gmail": [CapabilityDomain.NETWORK],
    "google_drive": [CapabilityDomain.NETWORK],
    "notion": [CapabilityDomain.NETWORK],
    "obsidian": [CapabilityDomain.FILESYSTEM],
    "local_files": [CapabilityDomain.FILESYSTEM],
    "screenshots": [CapabilityDomain.FILESYSTEM, CapabilityDomain.DISPLAY],
    "voice_notes": [CapabilityDomain.AUDIO, CapabilityDomain.FILESYSTEM],
    "camera_capture": [CapabilityDomain.CAMERA],
    "github": [CapabilityDomain.NETWORK, CapabilityDomain.SSH],
    "docker_logs": [CapabilityDomain.DOCKER],
    "claude_code_logs": [CapabilityDomain.FILESYSTEM],
    "stripe": [CapabilityDomain.NETWORK],
    "calendly": [CapabilityDomain.NETWORK],
    "apple_notes": [CapabilityDomain.LOCAL_ACCOUNTS, CapabilityDomain.FILESYSTEM],
    "saved_videos": [CapabilityDomain.BROWSER, CapabilityDomain.LOCAL_ACCOUNTS],
    "model_training": [CapabilityDomain.GPU, CapabilityDomain.COMPUTE],
    "media_rendering": [CapabilityDomain.GPU, CapabilityDomain.COMPUTE],
    "3d_printing": [CapabilityDomain.USB, CapabilityDomain.COMPUTE],
}

_SOURCE_AFFINITY: dict[str, SourceAffinity] = {
    "instagram": SourceAffinity.LOCAL_ONLY,
    "tiktok": SourceAffinity.LOCAL_ONLY,
    "twitter": SourceAffinity.LOCAL_ONLY,
    "linkedin": SourceAffinity.LOCAL_ONLY,
    "apple_notes": SourceAffinity.LOCAL_ONLY,
    "saved_videos": SourceAffinity.LOCAL_ONLY,
    "camera_capture": SourceAffinity.LOCAL_ONLY,
    "voice_notes": SourceAffinity.LOCAL_ONLY,
    "youtube": SourceAffinity.ANY_NODE,
    "discord": SourceAffinity.VPS_PREFERRED,
    "telegram": SourceAffinity.VPS_PREFERRED,
    "gmail": SourceAffinity.ANY_NODE,
    "google_drive": SourceAffinity.ANY_NODE,
    "notion": SourceAffinity.ANY_NODE,
    "obsidian": SourceAffinity.VPS_PREFERRED,
    "local_files": SourceAffinity.LOCAL_PREFERRED,
    "screenshots": SourceAffinity.LOCAL_PREFERRED,
    "github": SourceAffinity.VPS_PREFERRED,
    "docker_logs": SourceAffinity.VPS_ONLY,
    "claude_code_logs": SourceAffinity.VPS_ONLY,
    "stripe": SourceAffinity.ANY_NODE,
    "calendly": SourceAffinity.ANY_NODE,
    "model_training": SourceAffinity.GPU_REQUIRED,
    "media_rendering": SourceAffinity.GPU_REQUIRED,
    "3d_printing": SourceAffinity.LOCAL_ONLY,
}


def get_source_capabilities(source_name: str) -> list[CapabilityDomain]:
    return _SOURCE_TO_CAPABILITIES.get(source_name.lower(), [])


def get_source_affinity(source_name: str) -> SourceAffinity:
    return _SOURCE_AFFINITY.get(source_name.lower(), SourceAffinity.UNKNOWN)


def classify_capability(name: str, description: str | None = None) -> CapabilityDomain:
    key = (name + " " + (description or "")).lower()

    _MAP: list[tuple[list[str], CapabilityDomain]] = [
        (["gpu", "cuda", "tensor", "training"], CapabilityDomain.GPU),
        (["browser", "web", "chrome", "firefox", "safari"], CapabilityDomain.BROWSER),
        (["docker", "container", "kubernetes"], CapabilityDomain.DOCKER),
        (["ssh", "remote shell", "terminal"], CapabilityDomain.SSH),
        (["camera", "webcam", "photo", "scan"], CapabilityDomain.CAMERA),
        (["audio", "microphone", "speaker", "voice"], CapabilityDomain.AUDIO),
        (["display", "screen", "gui", "monitor"], CapabilityDomain.DISPLAY),
        (["bluetooth", "ble", "wireless peripheral"], CapabilityDomain.BLUETOOTH),
        (["usb", "serial", "peripheral"], CapabilityDomain.USB),
        (["location", "gps", "geolocation"], CapabilityDomain.LOCATION),
        (["account", "login", "session", "cookie"], CapabilityDomain.LOCAL_ACCOUNTS),
        (["file", "disk", "directory", "path"], CapabilityDomain.FILESYSTEM),
        (["storage", "database", "archive", "backup"], CapabilityDomain.STORAGE),
        (["network", "http", "api", "socket"], CapabilityDomain.NETWORK),
        (["compute", "cpu", "process", "execute"], CapabilityDomain.COMPUTE),
    ]

    for keywords, domain in _MAP:
        if any(kw in key for kw in keywords):
            return domain
    return CapabilityDomain.UNKNOWN


def list_source_names() -> list[str]:
    return sorted(_SOURCE_TO_CAPABILITIES.keys())


def map_sources_to_nodes(
    sources: list[str],
    nodes: list[Any] | None = None,
) -> dict[str, list[str]]:
    from umh.distributed.registry import build_default_node_profiles

    if nodes is None:
        nodes = build_default_node_profiles()

    node_caps: dict[str, set[CapabilityDomain]] = {}
    for n in nodes:
        node_caps[n.name] = set(n.capabilities)

    result: dict[str, list[str]] = {}
    for source in sources:
        required = set(get_source_capabilities(source))
        affinity = get_source_affinity(source)
        matched: list[str] = []
        for n in nodes:
            caps = node_caps.get(n.name, set())
            if required.issubset(caps):
                if (
                    affinity == SourceAffinity.LOCAL_ONLY
                    and n.node_type != RuntimeNodeType.LOCAL_PC
                ):
                    continue
                if affinity == SourceAffinity.VPS_ONLY and n.node_type != RuntimeNodeType.VPS:
                    continue
                if affinity == SourceAffinity.GPU_REQUIRED and not n.gpu:
                    continue
                matched.append(n.name)
        result[source] = matched

    return result


# Prevent circular import at module level
from umh.distributed.contracts import RuntimeNodeType  # noqa: E402
