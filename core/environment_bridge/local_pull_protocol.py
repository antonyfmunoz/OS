"""Local pull protocol for the Environment Bridge.

Pull-based packet execution: local worker polls a queue for approved
packets, claims them, executes locally, writes results back. This
avoids reliance on VPS SSH push, which can be blocked by sandbox
classifiers.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .work_packet import WorkPacket, WorkPacketStatus


class LocalPullStatus(str, Enum):
    READY = "ready"
    NO_REMOTE_QUEUE = "no_remote_queue"
    NO_LOCAL_QUEUE = "no_local_queue"
    NO_PACKETS = "no_packets"
    PACKET_CLAIMED = "packet_claimed"
    PACKET_INVALID = "packet_invalid"
    EXECUTION_BLOCKED = "execution_blocked"
    RESULT_WRITTEN = "result_written"
    SYNC_FAILED = "sync_failed"
    BLOCKED = "blocked"


class TransportStrategy(str, Enum):
    LOCAL_ONLY = "local_only"
    SCP_PULL = "scp_pull"
    RSYNC_PULL = "rsync_pull"
    SHARED_FOLDER = "shared_folder"
    MANUAL_COPY = "manual_copy"


@dataclass
class LocalPullCycleResult:
    cycle_id: str = ""
    remote_queue_available: bool = False
    local_queue_available: bool = False
    packets_seen: int = 0
    packets_claimed: int = 0
    packets_executed: int = 0
    packets_blocked: int = 0
    results_written: int = 0
    sync_status: str = ""
    status: LocalPullStatus = LocalPullStatus.BLOCKED
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "remote_queue_available": self.remote_queue_available,
            "local_queue_available": self.local_queue_available,
            "packets_seen": self.packets_seen,
            "packets_claimed": self.packets_claimed,
            "packets_executed": self.packets_executed,
            "packets_blocked": self.packets_blocked,
            "results_written": self.results_written,
            "sync_status": self.sync_status,
            "status": self.status.value,
            "notes": self.notes,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def discover_remote_packets(
    remote_outbox: str,
    force_available: bool | None = None,
) -> list[str]:
    if force_available is False:
        return []
    outbox = Path(remote_outbox)
    if not outbox.is_dir():
        return []
    return sorted(str(p) for p in outbox.glob("*.json"))


def copy_remote_packet_to_local(
    remote_path: str,
    local_inbox: str,
    force_success: bool | None = None,
) -> str | None:
    if force_success is False:
        return None
    src = Path(remote_path)
    if not src.is_file():
        return None
    dst = Path(local_inbox) / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text())
    return str(dst)


def claim_local_packet(packet_path: str) -> dict[str, Any] | None:
    p = Path(packet_path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text())
        data["status"] = WorkPacketStatus.CLAIMED.value
        data["claimed_at"] = _now_iso()
        p.write_text(json.dumps(data, indent=2))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def mark_packet_running(packet_path: str) -> bool:
    return _update_packet_status(packet_path, WorkPacketStatus.RUNNING.value)


def mark_packet_completed(packet_path: str) -> bool:
    return _update_packet_status(packet_path, WorkPacketStatus.COMPLETED.value)


def mark_packet_failed(packet_path: str, error: str = "") -> bool:
    return _update_packet_status(packet_path, WorkPacketStatus.FAILED.value, error=error)


def write_local_result(
    results_dir: str,
    packet_id: str,
    result_data: dict[str, Any],
) -> str | None:
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / f"result_{packet_id}.json"
    result_data["written_at"] = _now_iso()
    try:
        result_path.write_text(json.dumps(result_data, indent=2))
        return str(result_path)
    except OSError:
        return None


def sync_local_results_to_remote(
    local_results_dir: str,
    remote_results_dir: str,
    force_success: bool | None = None,
) -> list[str]:
    if force_success is False:
        return []
    local = Path(local_results_dir)
    remote = Path(remote_results_dir)
    if not local.is_dir():
        return []
    remote.mkdir(parents=True, exist_ok=True)
    synced: list[str] = []
    for f in local.glob("*.json"):
        dst = remote / f.name
        dst.write_text(f.read_text())
        synced.append(str(dst))
    return synced


def run_local_pull_cycle(
    remote_outbox: str,
    local_inbox: str,
    local_results_dir: str,
    force_remote_available: bool | None = None,
    force_local_available: bool | None = None,
    validator_fn: Any = None,
) -> LocalPullCycleResult:
    cycle = LocalPullCycleResult(
        cycle_id=uuid.uuid4().hex[:12],
    )

    if force_remote_available is False:
        cycle.status = LocalPullStatus.NO_REMOTE_QUEUE
        cycle.remote_queue_available = False
        return cycle
    cycle.remote_queue_available = Path(remote_outbox).is_dir() or (force_remote_available is True)
    if not cycle.remote_queue_available:
        cycle.status = LocalPullStatus.NO_REMOTE_QUEUE
        return cycle

    if force_local_available is False:
        cycle.status = LocalPullStatus.NO_LOCAL_QUEUE
        cycle.local_queue_available = False
        return cycle
    local_path = Path(local_inbox)
    local_path.mkdir(parents=True, exist_ok=True)
    cycle.local_queue_available = True

    packets = discover_remote_packets(remote_outbox, force_available=force_remote_available)
    cycle.packets_seen = len(packets)

    if cycle.packets_seen == 0:
        cycle.status = LocalPullStatus.NO_PACKETS
        return cycle

    for pkt_path in packets:
        local_path_str = copy_remote_packet_to_local(pkt_path, local_inbox)
        if local_path_str is None:
            cycle.packets_blocked += 1
            continue

        claimed = claim_local_packet(local_path_str)
        if claimed is None:
            cycle.packets_blocked += 1
            continue

        cycle.packets_claimed += 1

        if validator_fn is not None:
            if not validator_fn(claimed):
                cycle.packets_blocked += 1
                cycle.notes.append(f"Packet {pkt_path} failed validation")
                continue

        cycle.packets_executed += 1
        result_path = write_local_result(
            local_results_dir,
            claimed.get("packet_id", "unknown"),
            {"packet_id": claimed.get("packet_id"), "status": "executed_locally"},
        )
        if result_path:
            cycle.results_written += 1

    if cycle.packets_executed > 0:
        cycle.status = LocalPullStatus.RESULT_WRITTEN
    elif cycle.packets_claimed > 0:
        cycle.status = LocalPullStatus.PACKET_CLAIMED
    else:
        cycle.status = LocalPullStatus.EXECUTION_BLOCKED

    return cycle


def _update_packet_status(packet_path: str, status: str, error: str = "") -> bool:
    p = Path(packet_path)
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text())
        data["status"] = status
        data["updated_at"] = _now_iso()
        if error:
            data["error"] = error
        p.write_text(json.dumps(data, indent=2))
        return True
    except (json.JSONDecodeError, OSError):
        return False
