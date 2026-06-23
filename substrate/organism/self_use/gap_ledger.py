"""Gap ledger — structured log of every friction point, missing capability, and failure.

Each gap has a type, severity, and ecosystem surface association.
The ledger is the prerequisite roadmap for C28.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from substrate.organism.strategic_gap_engine import GapSeverity

logger = logging.getLogger(__name__)


class GapType(str, Enum):
    """Types of gaps discovered during certification."""

    SURFACE_UNREACHABLE = "surface_unreachable"
    SURFACE_DEGRADED = "surface_degraded"
    FEATURE_MISSING = "feature_missing"
    FEATURE_BROKEN = "feature_broken"
    COHERENCE_FAILURE = "coherence_failure"
    CONTEXT_LOST = "context_lost"
    PRIORITY_INVERSION = "priority_inversion"
    FALSE_HISTORY_ACCEPTED = "false_history_accepted"
    REALITY_DRIFT = "reality_drift"
    GOVERNANCE_BYPASS = "governance_bypass"
    DEPLOYMENT_FAILURE = "deployment_failure"
    INTEGRATION_MISSING = "integration_missing"
    PERFORMANCE_DEGRADED = "performance_degraded"
    UX_FRICTION = "ux_friction"
    DATA_INCONSISTENCY = "data_inconsistency"


SURFACE_NAMES = frozenset(
    {
        "cockpit",
        "meta_ide",
        "beast",
        "github",
        "google_drive",
        "stitch",
        "cc_skills",
    }
)


@dataclass
class GapEntry:
    """A single gap discovered during certification."""

    gap_id: str = field(default_factory=lambda: f"gap-{uuid4().hex[:8]}")
    gap_type: GapType = GapType.FEATURE_MISSING
    severity: GapSeverity = GapSeverity.MEDIUM
    surface: str = ""
    title: str = ""
    description: str = ""
    task_id: str = ""
    projection: str = ""
    evidence: str = ""
    remediation: str = ""
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type.value,
            "severity": self.severity.value,
            "surface": self.surface,
            "title": self.title,
            "description": self.description,
            "task_id": self.task_id,
            "projection": self.projection,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "discovered_at": self.discovered_at.isoformat(),
            "resolved": self.resolved,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GapEntry:
        return cls(
            gap_id=data.get("gap_id", f"gap-{uuid4().hex[:8]}"),
            gap_type=GapType(data.get("gap_type", "feature_missing")),
            severity=GapSeverity(data.get("severity", "medium")),
            surface=data.get("surface", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            task_id=data.get("task_id", ""),
            projection=data.get("projection", ""),
            evidence=data.get("evidence", ""),
            remediation=data.get("remediation", ""),
            resolved=data.get("resolved", False),
        )


class GapLedger:
    """Accumulates gaps discovered across the certification campaign."""

    def __init__(self) -> None:
        self._gaps: dict[str, GapEntry] = {}

    def add(self, gap: GapEntry) -> str:
        self._gaps[gap.gap_id] = gap
        logger.info("Gap recorded: [%s] %s — %s", gap.severity.value, gap.title, gap.surface)
        return gap.gap_id

    def resolve(self, gap_id: str) -> bool:
        gap = self._gaps.get(gap_id)
        if gap:
            gap.resolved = True
            return True
        return False

    @property
    def gaps(self) -> list[GapEntry]:
        return list(self._gaps.values())

    def get(self, gap_id: str) -> GapEntry | None:
        return self._gaps.get(gap_id)

    def by_severity(self, severity: GapSeverity) -> list[GapEntry]:
        return [g for g in self._gaps.values() if g.severity == severity]

    def by_surface(self, surface: str) -> list[GapEntry]:
        return [g for g in self._gaps.values() if g.surface == surface]

    def by_type(self, gap_type: GapType) -> list[GapEntry]:
        return [g for g in self._gaps.values() if g.gap_type == gap_type]

    def unresolved(self) -> list[GapEntry]:
        return [g for g in self._gaps.values() if not g.resolved]

    def coherence_gaps(self) -> list[GapEntry]:
        coherence_types = frozenset(
            {
                GapType.COHERENCE_FAILURE,
                GapType.CONTEXT_LOST,
                GapType.PRIORITY_INVERSION,
                GapType.FALSE_HISTORY_ACCEPTED,
                GapType.REALITY_DRIFT,
                GapType.GOVERNANCE_BYPASS,
            }
        )
        return [g for g in self._gaps.values() if g.gap_type in coherence_types]

    def summary(self) -> dict[str, Any]:
        return {
            "total": len(self._gaps),
            "unresolved": len(self.unresolved()),
            "by_severity": {s.value: len(self.by_severity(s)) for s in GapSeverity},
            "by_surface": {s: len(self.by_surface(s)) for s in SURFACE_NAMES if self.by_surface(s)},
            "coherence_gaps": len(self.coherence_gaps()),
        }

    def to_json(self, path: str) -> None:
        data = {
            "gaps": [g.to_dict() for g in self._gaps.values()],
            "summary": self.summary(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Gap ledger exported: %s (%d gaps)", path, len(self._gaps))

    @classmethod
    def from_json(cls, path: str) -> GapLedger:
        ledger = cls()
        if not os.path.exists(path):
            return ledger
        with open(path) as f:
            data = json.load(f)
        for g in data.get("gaps", []):
            entry = GapEntry.from_dict(g)
            ledger._gaps[entry.gap_id] = entry
        return ledger
