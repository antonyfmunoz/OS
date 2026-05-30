"""Roadmap Engine — phase linkage model for self-build queue.

Maps roadmap phases to work items, tracks prerequisites, success criteria,
and blocked/unlocked relationships. Provides deterministic phase-level
status aggregation from linked work item states.

Phase 11.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class RoadmapPhase:
    phase_id: str = ""
    title: str = ""
    objective: str = ""
    status: str = "planned"
    prerequisites: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    linked_work_items: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    unlocks: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "title": self.title,
            "objective": self.objective,
            "status": self.status,
            "prerequisites": self.prerequisites,
            "success_criteria": self.success_criteria,
            "linked_work_items": self.linked_work_items,
            "blocked_by": self.blocked_by,
            "unlocks": self.unlocks,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RoadmapPhase:
        return cls(
            phase_id=d.get("phase_id", ""),
            title=d.get("title", ""),
            objective=d.get("objective", ""),
            status=d.get("status", "planned"),
            prerequisites=d.get("prerequisites", []),
            success_criteria=d.get("success_criteria", []),
            linked_work_items=d.get("linked_work_items", []),
            blocked_by=d.get("blocked_by", []),
            unlocks=d.get("unlocks", []),
            evidence=d.get("evidence", []),
            created_at=float(d.get("created_at", time.time())),
            updated_at=float(d.get("updated_at", time.time())),
        )


class RoadmapEngine:
    """Deterministic roadmap phase management linked to self-build queue."""

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = store_path or os.path.join(
            _REPO_ROOT, "data", "umh", "self_build", "roadmap_phases.jsonl",
        )
        self._phases: dict[str, RoadmapPhase] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            return
        parsed: dict[str, RoadmapPhase] = {}
        with open(self._store_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    phase = RoadmapPhase.from_dict(d)
                    parsed[phase.phase_id] = phase
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise ValueError(
                        f"Corrupt roadmap phase at line {line_num}: {exc}"
                    ) from exc
        self._phases = parsed

    def _save(self) -> None:
        dir_path = os.path.dirname(self._store_path)
        os.makedirs(dir_path, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                for phase in self._phases.values():
                    f.write(json.dumps(phase.to_dict()) + "\n")
            os.replace(tmp_path, self._store_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def add_phase(self, phase: RoadmapPhase) -> RoadmapPhase:
        self._phases[phase.phase_id] = phase
        self._save()
        return phase

    def get_phase(self, phase_id: str) -> RoadmapPhase | None:
        return self._phases.get(phase_id)

    def link_work_item(self, phase_id: str, work_item_id: str) -> bool:
        phase = self._phases.get(phase_id)
        if not phase:
            return False
        if work_item_id not in phase.linked_work_items:
            phase.linked_work_items.append(work_item_id)
            phase.updated_at = time.time()
            self._save()
        return True

    def update_status(self, phase_id: str, status: str) -> bool:
        phase = self._phases.get(phase_id)
        if not phase:
            return False
        phase.status = status
        phase.updated_at = time.time()
        self._save()
        return True

    def all_phases(self) -> list[RoadmapPhase]:
        return list(self._phases.values())

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for p in self._phases.values():
            status_counts[p.status] = status_counts.get(p.status, 0) + 1
        return {
            "total_phases": len(self._phases),
            "status_counts": status_counts,
            "phases": [
                {
                    "phase_id": p.phase_id,
                    "title": p.title,
                    "status": p.status,
                    "work_items": len(p.linked_work_items),
                    "unlocks": p.unlocks,
                }
                for p in self._phases.values()
            ],
        }
