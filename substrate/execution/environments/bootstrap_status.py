"""Bootstrap status checker for the Environment Bridge.

Evaluates whether the local worker bridge has been bootstrapped by
checking for queue directories, heartbeat, and worker readiness on
both VPS and local sides.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .queue_paths import build_vps_queue_paths


class BootstrapCheckStatus(str, Enum):
    READY = "ready"
    NOT_BOOTSTRAPPED = "not_bootstrapped"
    VPS_QUEUE_MISSING = "vps_queue_missing"
    PACKET_MISSING = "packet_missing"
    PACKET_NOT_APPROVED = "packet_not_approved"
    LOCAL_UNKNOWN = "local_unknown"


@dataclass
class BootstrapStatusReport:
    vps_queue_exists: bool = False
    vps_outbox_exists: bool = False
    packet_found: bool = False
    packet_id: str = ""
    packet_approved: bool = False
    packet_executed: bool = False
    local_bootstrapped: bool = False
    heartbeat_present: bool = False
    status: BootstrapCheckStatus = BootstrapCheckStatus.NOT_BOOTSTRAPPED
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vps_queue_exists": self.vps_queue_exists,
            "vps_outbox_exists": self.vps_outbox_exists,
            "packet_found": self.packet_found,
            "packet_id": self.packet_id,
            "packet_approved": self.packet_approved,
            "packet_executed": self.packet_executed,
            "local_bootstrapped": self.local_bootstrapped,
            "heartbeat_present": self.heartbeat_present,
            "status": self.status.value,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def check_vps_bootstrap_readiness(
    packet_filename: str = "w0_001_cu_rerun_while_present_packet.json",
) -> BootstrapStatusReport:
    """Check VPS-side readiness for local worker bootstrap."""
    report = BootstrapStatusReport()
    paths = build_vps_queue_paths()

    queue_root = Path(paths.root)
    if queue_root.exists():
        report.vps_queue_exists = True
    else:
        report.blockers.append(f"VPS queue root missing: {paths.root}")
        report.status = BootstrapCheckStatus.VPS_QUEUE_MISSING
        return report

    outbox = Path(paths.outbox)
    if outbox.exists():
        report.vps_outbox_exists = True
    else:
        report.blockers.append(f"VPS outbox missing: {paths.outbox}")
        report.status = BootstrapCheckStatus.VPS_QUEUE_MISSING
        return report

    packet_path = outbox / packet_filename
    if packet_path.exists():
        report.packet_found = True
        report.packet_id = "WP-W0-001-CU-RERUN-001"
    else:
        report.blockers.append(f"Packet not found: {packet_path}")
        report.status = BootstrapCheckStatus.PACKET_MISSING
        return report

    import json

    try:
        with open(packet_path) as f:
            data = json.load(f)
        if data.get("approval_status") == "approved":
            report.packet_approved = True
        else:
            report.blockers.append(f"Packet not approved: {data.get('approval_status')}")
            report.status = BootstrapCheckStatus.PACKET_NOT_APPROVED
            return report
        if data.get("status") in ("completed", "running"):
            report.packet_executed = True
    except (json.JSONDecodeError, OSError) as e:
        report.blockers.append(f"Cannot read packet: {e}")
        report.status = BootstrapCheckStatus.PACKET_MISSING
        return report

    heartbeat_dir = Path(paths.heartbeats)
    if heartbeat_dir.exists():
        heartbeat_files = list(heartbeat_dir.glob("*.json"))
        if heartbeat_files:
            report.heartbeat_present = True

    if report.packet_approved and not report.packet_executed:
        report.status = BootstrapCheckStatus.READY
        report.notes.append("VPS ready. Packet approved. Awaiting local bootstrap.")
    elif report.packet_executed:
        report.status = BootstrapCheckStatus.READY
        report.notes.append("Packet already executed.")
    else:
        report.status = BootstrapCheckStatus.LOCAL_UNKNOWN

    return report


def bootstrap_status_blocks_dispatch(report: BootstrapStatusReport) -> bool:
    return report.status in (
        BootstrapCheckStatus.VPS_QUEUE_MISSING,
        BootstrapCheckStatus.PACKET_MISSING,
        BootstrapCheckStatus.PACKET_NOT_APPROVED,
    )


def summarize_bootstrap_status(report: BootstrapStatusReport) -> dict[str, Any]:
    return {
        "status": report.status.value,
        "packet_id": report.packet_id,
        "packet_approved": report.packet_approved,
        "packet_executed": report.packet_executed,
        "heartbeat_present": report.heartbeat_present,
        "blocker_count": len(report.blockers),
        "can_dispatch": not bootstrap_status_blocks_dispatch(report),
    }
