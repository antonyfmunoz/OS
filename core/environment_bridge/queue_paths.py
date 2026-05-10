"""Queue paths for the Environment Bridge.

Canonical filesystem paths for work packet queues on VPS and local
worker environments. Pure path construction — no I/O in tests.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



@dataclass
class QueuePaths:
    root: str = ""
    outbox: str = ""
    inbox: str = ""
    archive: str = ""
    heartbeats: str = ""
    results: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "outbox": self.outbox,
            "inbox": self.inbox,
            "archive": self.archive,
            "heartbeats": self.heartbeats,
            "results": self.results,
        }


def build_vps_queue_paths() -> QueuePaths:
    root = f"{_ROOT}/data/work_queue"
    return QueuePaths(
        root=root,
        outbox=f"{root}/outbox",
        inbox=f"{root}/inbox",
        archive=f"{root}/archive",
        heartbeats=f"{root}/heartbeats",
        results=f"{root}/results",
    )


def build_local_queue_paths() -> QueuePaths:
    home = str(Path.home())
    root = f"{home}/eos_advisor_messages"
    return QueuePaths(
        root=root,
        outbox=f"{root}/outbox",
        inbox=f"{root}/inbox",
        archive=f"{root}/archive",
        heartbeats=f"{root}/heartbeats",
        results=f"{root}/results",
    )


def ensure_queue_paths(paths: QueuePaths) -> list[str]:
    created: list[str] = []
    for dir_path in [
        paths.outbox,
        paths.inbox,
        paths.archive,
        paths.heartbeats,
        paths.results,
    ]:
        p = Path(dir_path)
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(dir_path)
    return created


def queue_paths_are_valid(paths: QueuePaths) -> bool:
    return all(
        [
            paths.root,
            paths.outbox,
            paths.inbox,
            paths.archive,
            paths.heartbeats,
            paths.results,
        ]
    )


def summarize_queue_paths(paths: QueuePaths) -> dict[str, Any]:
    return {
        "root": paths.root,
        "valid": queue_paths_are_valid(paths),
        "dirs": {
            "outbox": paths.outbox,
            "inbox": paths.inbox,
            "archive": paths.archive,
            "heartbeats": paths.heartbeats,
            "results": paths.results,
        },
    }
