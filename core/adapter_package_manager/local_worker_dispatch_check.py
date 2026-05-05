"""Local Worker Dispatch Check.

Evaluates whether the VPS can dispatch a CU rerun packet to the local
Windows worker. Checks SSH reachability, station directory state, and
local inbox availability. Produces manual fallback instructions when
automated dispatch is unavailable.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


VPS_STATION_DIR = Path("/opt/OS/eos_ai/.substrate_station")
RERUN_PACKET_DIR = Path("/opt/OS/data/cu_rerun_packets")
DEFAULT_RERUN_PACKET = "w0_001_cu_rerun_while_present.json"

SSH_HOST = "100.74.199.102"
SSH_USER = r"DESKTOP-LVGUIQ9\antonys beast pc"
SSH_KEY = "/root/.ssh/id_ed25519"
LOCAL_INBOX = "~/eos_advisor_messages/inbox/"


class LocalWorkerDispatchStatus(str, Enum):
    DISPATCH_READY = "dispatch_ready"
    DISPATCH_SENT = "dispatch_sent"
    SSH_UNREACHABLE = "ssh_unreachable"
    STATION_DIR_MISSING = "station_dir_missing"
    PACKET_MISSING = "packet_missing"
    WORKER_NOT_POLLING = "worker_not_polling"
    MANUAL_RUN_REQUIRED = "manual_run_required"
    BLOCKED = "blocked"


@dataclass
class LocalWorkerDispatchCheck:
    station_dir_exists: bool = False
    station_dir_path: str = ""
    workstation_inbox_exists: bool = False
    workstation_outbox_exists: bool = False
    rerun_packet_exists: bool = False
    rerun_packet_path: str = ""
    ssh_key_exists: bool = False
    ssh_host: str = SSH_HOST
    ssh_user: str = SSH_USER
    can_dispatch_via_ssh: bool = False
    can_dispatch_via_station: bool = False
    manual_run_required: bool = False
    dispatch_status: LocalWorkerDispatchStatus = LocalWorkerDispatchStatus.BLOCKED
    blockers: list[str] = field(default_factory=list)
    manual_instructions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "station_dir_exists": self.station_dir_exists,
            "station_dir_path": self.station_dir_path,
            "workstation_inbox_exists": self.workstation_inbox_exists,
            "workstation_outbox_exists": self.workstation_outbox_exists,
            "rerun_packet_exists": self.rerun_packet_exists,
            "rerun_packet_path": self.rerun_packet_path,
            "ssh_key_exists": self.ssh_key_exists,
            "ssh_host": self.ssh_host,
            "ssh_user": self.ssh_user,
            "can_dispatch_via_ssh": self.can_dispatch_via_ssh,
            "can_dispatch_via_station": self.can_dispatch_via_station,
            "manual_run_required": self.manual_run_required,
            "dispatch_status": self.dispatch_status.value,
            "blockers": self.blockers,
            "manual_instructions": self.manual_instructions,
            "notes": self.notes,
        }


def check_local_worker_dispatch_readiness(
    force_station_dir: bool | None = None,
    force_inbox: bool | None = None,
    force_outbox: bool | None = None,
    force_ssh_key: bool | None = None,
    force_packet: bool | None = None,
) -> LocalWorkerDispatchCheck:
    result = LocalWorkerDispatchCheck()

    result.station_dir_path = str(VPS_STATION_DIR)
    if force_station_dir is not None:
        result.station_dir_exists = force_station_dir
    else:
        result.station_dir_exists = VPS_STATION_DIR.is_dir()

    inbox_path = VPS_STATION_DIR / "antony-workstation.inbox.json"
    outbox_path = VPS_STATION_DIR / "antony-workstation.outbox.json"

    if force_inbox is not None:
        result.workstation_inbox_exists = force_inbox
    else:
        result.workstation_inbox_exists = inbox_path.is_file()

    if force_outbox is not None:
        result.workstation_outbox_exists = force_outbox
    else:
        result.workstation_outbox_exists = outbox_path.is_file()

    packet_path = RERUN_PACKET_DIR / DEFAULT_RERUN_PACKET
    result.rerun_packet_path = str(packet_path)
    if force_packet is not None:
        result.rerun_packet_exists = force_packet
    else:
        result.rerun_packet_exists = packet_path.is_file()

    ssh_key_path = Path(SSH_KEY)
    if force_ssh_key is not None:
        result.ssh_key_exists = force_ssh_key
    else:
        result.ssh_key_exists = ssh_key_path.is_file()

    if not result.rerun_packet_exists:
        result.blockers.append("RERUN_PACKET_MISSING")
        result.dispatch_status = LocalWorkerDispatchStatus.PACKET_MISSING
        return result

    if not result.station_dir_exists:
        result.blockers.append("STATION_DIR_MISSING")

    station_dispatch_possible = (
        result.station_dir_exists
        and result.workstation_inbox_exists
        and result.workstation_outbox_exists
    )
    result.can_dispatch_via_station = station_dispatch_possible

    ssh_dispatch_possible = result.ssh_key_exists
    result.can_dispatch_via_ssh = ssh_dispatch_possible

    if station_dispatch_possible or ssh_dispatch_possible:
        result.dispatch_status = LocalWorkerDispatchStatus.DISPATCH_READY
        result.notes.append(
            "Dispatch is possible via "
            + (
                "station + SSH"
                if station_dispatch_possible and ssh_dispatch_possible
                else "station"
                if station_dispatch_possible
                else "SSH"
            )
            + ". Founder must be present on local PC during execution."
        )
    else:
        result.dispatch_status = LocalWorkerDispatchStatus.MANUAL_RUN_REQUIRED
        result.manual_run_required = True
        if not result.ssh_key_exists:
            result.blockers.append("SSH_KEY_MISSING")
        if not station_dispatch_possible:
            if not result.workstation_inbox_exists:
                result.blockers.append("WORKSTATION_INBOX_MISSING")
            if not result.workstation_outbox_exists:
                result.blockers.append("WORKSTATION_OUTBOX_MISSING")

        result.manual_instructions = _build_manual_instructions()
        result.notes.append(
            "Automated dispatch unavailable. Founder must copy the rerun "
            "packet to local PC and run manually. See manual_instructions."
        )

    return result


def build_w0_001_cu_dispatch_packet() -> dict[str, Any]:
    packet_path = RERUN_PACKET_DIR / DEFAULT_RERUN_PACKET
    if not packet_path.is_file():
        return {
            "error": "Rerun packet not found",
            "expected_path": str(packet_path),
        }
    with open(packet_path) as f:
        return json.load(f)


def local_worker_dispatch_blocks_run(
    check: LocalWorkerDispatchCheck,
) -> bool:
    return check.dispatch_status in (
        LocalWorkerDispatchStatus.PACKET_MISSING,
        LocalWorkerDispatchStatus.STATION_DIR_MISSING,
        LocalWorkerDispatchStatus.BLOCKED,
    )


def summarize_dispatch_check(
    check: LocalWorkerDispatchCheck,
) -> dict[str, Any]:
    return {
        "dispatch_status": check.dispatch_status.value,
        "station_dir_exists": check.station_dir_exists,
        "rerun_packet_exists": check.rerun_packet_exists,
        "can_dispatch_via_ssh": check.can_dispatch_via_ssh,
        "can_dispatch_via_station": check.can_dispatch_via_station,
        "manual_run_required": check.manual_run_required,
        "blocker_count": len(check.blockers),
        "blockers": check.blockers,
    }


def _build_manual_instructions() -> list[str]:
    return [
        "1. Copy data/cu_rerun_packets/w0_001_cu_rerun_while_present.json to local PC",
        "2. Place in ~/eos_advisor_messages/inbox/ on local Windows PC",
        "3. Open WSL terminal on local PC",
        "4. Be physically present at the screen",
        "5. Run: python3 /opt/OS/eos_ai/substrate/local_worker_auto_loop.py",
        "6. Watch Chrome open Google Drive — confirm 26 My Drive files",
        "7. Watch Chrome open Google Docs — confirm tab detection and content extraction",
        "8. Results will be written to ~/eos_advisor_messages/outbox/",
        "9. Report back to Developer Agent with CONFIRM_DRIVE_CU_ONLY, CONFIRM_DOCS_CU_ONLY, or CONFIRM_BOTH",
    ]
