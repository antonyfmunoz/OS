"""VPS ↔ Local Worker bridge for the Environment Bridge.

Orchestrates the connection between VPS orchestrator and local Windows
worker. Primary mode is LOCAL_PULL_PRIMARY — the local worker polls
for packets. SSH push exists as optional fallback.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .queue_paths import QueuePaths, build_vps_queue_paths, build_local_queue_paths
from .heartbeat import WorkerHeartbeat, WorkerHeartbeatStatus, heartbeat_is_stale


class BridgeMode(str, Enum):
    LOCAL_PULL_PRIMARY = "local_pull_primary"
    SSH_PUSH_OPTIONAL = "ssh_push_optional"
    MANUAL_FALLBACK = "manual_fallback"
    SHARED_FOLDER = "shared_folder"
    DISABLED = "disabled"


class VPSLocalBridgeStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    PUSH_BLOCKED_PULL_AVAILABLE = "push_blocked_pull_available"
    PULL_NOT_BOOTSTRAPPED = "pull_not_bootstrapped"
    MANUAL_REQUIRED = "manual_required"
    BLOCKED = "blocked"


@dataclass
class VPSLocalBridge:
    bridge_id: str = "vps-local-bridge-001"
    primary_mode: BridgeMode = BridgeMode.LOCAL_PULL_PRIMARY
    optional_modes: list[str] = field(default_factory=list)
    vps_queue_paths: QueuePaths = field(default_factory=build_vps_queue_paths)
    local_queue_paths: QueuePaths = field(default_factory=build_local_queue_paths)
    worker_heartbeat: WorkerHeartbeat | None = None
    tmux_surface: Any = None
    status: VPSLocalBridgeStatus = VPSLocalBridgeStatus.BLOCKED
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bridge_id": self.bridge_id,
            "primary_mode": self.primary_mode.value,
            "optional_modes": self.optional_modes,
            "vps_queue_paths": self.vps_queue_paths.to_dict(),
            "local_queue_paths": self.local_queue_paths.to_dict(),
            "worker_heartbeat": (
                self.worker_heartbeat.to_dict() if self.worker_heartbeat else None
            ),
            "status": self.status.value,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def build_vps_local_bridge(
    worker_heartbeat: WorkerHeartbeat | None = None,
    ssh_push_available: bool = False,
    tmux_surface: Any = None,
) -> VPSLocalBridge:
    optional = []
    if ssh_push_available:
        optional.append(BridgeMode.SSH_PUSH_OPTIONAL.value)
    optional.append(BridgeMode.MANUAL_FALLBACK.value)

    return VPSLocalBridge(
        primary_mode=BridgeMode.LOCAL_PULL_PRIMARY,
        optional_modes=optional,
        worker_heartbeat=worker_heartbeat,
        tmux_surface=tmux_surface,
    )


def evaluate_vps_local_bridge_status(
    bridge: VPSLocalBridge,
    ssh_reachable: bool = False,
    heartbeat_present: bool = False,
) -> VPSLocalBridge:
    if heartbeat_present and bridge.worker_heartbeat:
        if not heartbeat_is_stale(bridge.worker_heartbeat):
            if ssh_reachable:
                bridge.status = VPSLocalBridgeStatus.READY
            else:
                bridge.status = VPSLocalBridgeStatus.PUSH_BLOCKED_PULL_AVAILABLE
                bridge.notes.append(
                    "SSH push is blocked but local pull worker is online. "
                    "Packets placed in VPS outbox will be pulled by local worker."
                )
            return bridge

        bridge.status = VPSLocalBridgeStatus.PARTIAL
        bridge.blockers.append("HEARTBEAT_STALE")
        bridge.notes.append("Worker heartbeat is stale — worker may be offline.")
        return bridge

    if not heartbeat_present:
        bridge.status = VPSLocalBridgeStatus.PULL_NOT_BOOTSTRAPPED
        bridge.blockers.append("NO_HEARTBEAT")
        bridge.notes.append(
            "Local worker has not been bootstrapped. Founder must run one-time local setup."
        )
        return bridge

    bridge.status = VPSLocalBridgeStatus.MANUAL_REQUIRED
    bridge.blockers.append("MANUAL_SETUP_REQUIRED")
    return bridge


def bridge_can_dispatch_by_push(bridge: VPSLocalBridge) -> bool:
    return BridgeMode.SSH_PUSH_OPTIONAL.value in bridge.optional_modes


def bridge_can_dispatch_by_pull(bridge: VPSLocalBridge) -> bool:
    return bridge.primary_mode == BridgeMode.LOCAL_PULL_PRIMARY


def bridge_requires_manual_bootstrap(bridge: VPSLocalBridge) -> bool:
    return bridge.status in (
        VPSLocalBridgeStatus.PULL_NOT_BOOTSTRAPPED,
        VPSLocalBridgeStatus.MANUAL_REQUIRED,
    )


def summarize_vps_local_bridge(bridge: VPSLocalBridge) -> dict[str, Any]:
    return {
        "bridge_id": bridge.bridge_id,
        "primary_mode": bridge.primary_mode.value,
        "status": bridge.status.value,
        "can_push": bridge_can_dispatch_by_push(bridge),
        "can_pull": bridge_can_dispatch_by_pull(bridge),
        "requires_bootstrap": bridge_requires_manual_bootstrap(bridge),
        "blocker_count": len(bridge.blockers),
        "blockers": bridge.blockers,
    }
