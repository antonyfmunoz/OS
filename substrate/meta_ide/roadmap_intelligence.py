"""Roadmap intelligence — phase and planning awareness.

Scans planning files, audit reports, and organism events to answer:
what phase are we on, what completed, what remains, what is blocked.

Read-only. No mutations. No execution.

Phase 21. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PhaseState(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    PLANNED = "planned"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class PhaseStatus:
    phase_number: str
    phase_name: str
    state: PhaseState = PhaseState.UNKNOWN
    completed_at: str = ""
    description: str = ""
    key_files: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoadmapStatus:
    current_phase: PhaseStatus | None = None
    completed_phases: list[PhaseStatus] = field(default_factory=list)
    planned_phases: list[PhaseStatus] = field(default_factory=list)
    blocked_phases: list[PhaseStatus] = field(default_factory=list)
    total_phases: int = 0
    completion_ratio: float = 0.0
    generated_at: float = field(default_factory=time.time)
    sources_checked: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


_AUDIT_PHASE_RE = re.compile(
    r"phase[\s_-]*(\d+[a-zA-Z]?)\b[:\s—-]*(.{0,80})",
    re.IGNORECASE,
)

_COMPLETION_MARKERS = re.compile(
    r"\b(shipped|complete|merged|done|completion report)\b",
    re.IGNORECASE,
)


class RoadmapIntelligence:
    """Read-only roadmap and planning awareness engine."""

    def __init__(self, root_path: str | None = None) -> None:
        self._root = root_path or os.environ.get("UMH_ROOT", "/opt/OS")

    def status(self) -> RoadmapStatus:
        rs = RoadmapStatus()
        sources: list[str] = []

        audit_phases = self._scan_audits()
        sources.append("data/audits/")

        memory_phases = self._scan_memory_files()
        sources.append("memory/MEMORY.md")

        all_phases = self._merge_phases(audit_phases, memory_phases)

        completed = [p for p in all_phases if p.state == PhaseState.COMPLETED]
        planned = [p for p in all_phases if p.state == PhaseState.PLANNED]
        blocked = [p for p in all_phases if p.state == PhaseState.BLOCKED]
        in_progress = [p for p in all_phases if p.state == PhaseState.IN_PROGRESS]

        rs.completed_phases = sorted(completed, key=lambda p: p.phase_number)
        rs.planned_phases = sorted(planned, key=lambda p: p.phase_number)
        rs.blocked_phases = blocked
        rs.current_phase = in_progress[0] if in_progress else None
        rs.total_phases = len(all_phases)
        rs.completion_ratio = len(completed) / max(len(all_phases), 1)
        rs.generated_at = time.time()
        rs.sources_checked = sources

        return rs

    def current_phase(self) -> PhaseStatus | None:
        return self.status().current_phase

    def completed_phases(self) -> list[PhaseStatus]:
        return self.status().completed_phases

    def what_remains(self) -> list[PhaseStatus]:
        s = self.status()
        return s.planned_phases + s.blocked_phases

    def what_is_blocked(self) -> list[PhaseStatus]:
        return self.status().blocked_phases

    def phase_detail(self, phase_number: str) -> PhaseStatus | None:
        s = self.status()
        all_phases = (
            s.completed_phases
            + s.planned_phases
            + s.blocked_phases
            + ([s.current_phase] if s.current_phase else [])
        )
        for p in all_phases:
            if p.phase_number == phase_number:
                return p
        return None

    def _scan_audits(self) -> list[PhaseStatus]:
        audit_dir = os.path.join(self._root, "data", "audits")
        if not os.path.isdir(audit_dir):
            return []

        phases: list[PhaseStatus] = []
        seen: set[str] = set()

        for fname in sorted(os.listdir(audit_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(audit_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read(4096)
            except Exception:
                continue

            for m in _AUDIT_PHASE_RE.finditer(content):
                pnum = m.group(1)
                pname = m.group(2).strip().rstrip("—-: ")
                if pnum in seen:
                    continue
                seen.add(pnum)
                state = PhaseState.COMPLETED if _COMPLETION_MARKERS.search(content) else PhaseState.UNKNOWN
                phases.append(PhaseStatus(
                    phase_number=pnum,
                    phase_name=pname,
                    state=state,
                    key_files=[fpath],
                ))

        return phases

    def _scan_memory_files(self) -> list[PhaseStatus]:
        memory_dir = os.path.join(
            os.path.expanduser("~"),
            ".claude", "projects", "-opt-OS", "memory",
        )
        memory_index = os.path.join(memory_dir, "MEMORY.md")
        if not os.path.isfile(memory_index):
            return []

        phases: list[PhaseStatus] = []
        seen: set[str] = set()

        try:
            with open(memory_index, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []

        phase_re = re.compile(
            r"Phase\s+(\d+[A-Za-z]?)[\s:—-]+(.+?)(?:\s+—\s+|\s*$)",
            re.MULTILINE,
        )
        for m in phase_re.finditer(content):
            pnum = m.group(1)
            desc = m.group(2).strip()
            if pnum in seen:
                continue
            seen.add(pnum)
            state = PhaseState.COMPLETED
            phases.append(PhaseStatus(
                phase_number=pnum,
                phase_name=desc,
                state=state,
            ))

        return phases

    def _merge_phases(
        self,
        audit_phases: list[PhaseStatus],
        memory_phases: list[PhaseStatus],
    ) -> list[PhaseStatus]:
        merged: dict[str, PhaseStatus] = {}

        for p in memory_phases:
            merged[p.phase_number] = p
        for p in audit_phases:
            if p.phase_number in merged:
                existing = merged[p.phase_number]
                if p.key_files:
                    existing.key_files.extend(p.key_files)
                if p.state != PhaseState.UNKNOWN and existing.state == PhaseState.UNKNOWN:
                    existing.state = p.state
            else:
                merged[p.phase_number] = p

        return list(merged.values())
