"""Projection delta engine — desired vs implemented vs certified.

Compares three states for each projection:
  Drive    → Desired State    (what we want)
  GitHub   → Implemented State (what exists in code)
  Cert     → Operational State (what actually works in production)

Produces a delta report answering: "How far from the vision?"
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

logger = logging.getLogger(__name__)


class CapabilityState(str, Enum):
    """State of a single capability across the three layers."""

    DESIRED = "desired"
    IMPLEMENTED = "implemented"
    OPERATIONAL = "operational"
    MISSING = "missing"


@dataclass
class ProjectionCapability:
    """A single capability tracked for a projection."""

    name: str = ""
    description: str = ""
    desired: bool = True
    implemented: bool = False
    operational: bool = False
    source: str = ""

    @property
    def state(self) -> CapabilityState:
        if self.operational:
            return CapabilityState.OPERATIONAL
        if self.implemented:
            return CapabilityState.IMPLEMENTED
        if self.desired:
            return CapabilityState.DESIRED
        return CapabilityState.MISSING

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "desired": self.desired,
            "implemented": self.implemented,
            "operational": self.operational,
            "state": self.state.value,
            "source": self.source,
        }


@dataclass
class ProjectionDelta:
    """Delta report for a single projection."""

    projection_name: str = ""
    capabilities: list[ProjectionCapability] = field(default_factory=list)
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def desired_count(self) -> int:
        return sum(1 for c in self.capabilities if c.desired)

    @property
    def implemented_count(self) -> int:
        return sum(1 for c in self.capabilities if c.implemented)

    @property
    def operational_count(self) -> int:
        return sum(1 for c in self.capabilities if c.operational)

    @property
    def missing_count(self) -> int:
        return self.desired_count - self.operational_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_name": self.projection_name,
            "desired": self.desired_count,
            "implemented": self.implemented_count,
            "operational": self.operational_count,
            "missing": self.missing_count,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "measured_at": self.measured_at.isoformat(),
        }


@dataclass
class DeltaReport:
    """Multi-projection delta report — baseline or measurement."""

    report_id: str = field(default_factory=lambda: f"dr-{uuid4().hex[:8]}")
    label: str = ""
    projections: list[ProjectionDelta] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "label": self.label,
            "projections": [p.to_dict() for p in self.projections],
            "generated_at": self.generated_at.isoformat(),
        }

    def to_markdown(self) -> str:
        lines = [f"# Projection Delta Report — {self.label}", ""]
        for p in self.projections:
            lines.append(f"## {p.projection_name}")
            lines.append(f"  Desired capabilities:     {p.desired_count}")
            lines.append(f"  Implemented:              {p.implemented_count}")
            lines.append(f"  Operational (certified):  {p.operational_count}")
            lines.append(f"  Missing:                  {p.missing_count}")
            lines.append("")
        lines.append(f"Generated: {self.generated_at.isoformat()}")
        return "\n".join(lines)


class ProjectionDeltaEngine:
    """Computes and compares delta reports across time."""

    def __init__(self) -> None:
        self._reports: dict[str, DeltaReport] = {}

    def add_report(self, report: DeltaReport) -> str:
        self._reports[report.report_id] = report
        logger.info(
            "Delta report recorded: %s (%d projections)", report.label, len(report.projections)
        )
        return report.report_id

    def get(self, report_id: str) -> DeltaReport | None:
        return self._reports.get(report_id)

    @property
    def reports(self) -> list[DeltaReport]:
        return sorted(self._reports.values(), key=lambda r: r.generated_at)

    def compare(self, baseline_id: str, current_id: str) -> dict[str, Any]:
        """Compare two delta reports — shows advancement."""
        baseline = self._reports.get(baseline_id)
        current = self._reports.get(current_id)
        if not baseline or not current:
            return {"error": "Report not found"}

        comparisons: list[dict[str, Any]] = []
        baseline_map = {p.projection_name: p for p in baseline.projections}
        for proj in current.projections:
            base_proj = baseline_map.get(proj.projection_name)
            if not base_proj:
                comparisons.append(
                    {
                        "projection": proj.projection_name,
                        "note": "not in baseline",
                    }
                )
                continue
            comparisons.append(
                {
                    "projection": proj.projection_name,
                    "operational_before": base_proj.operational_count,
                    "operational_after": proj.operational_count,
                    "delta": proj.operational_count - base_proj.operational_count,
                    "implemented_before": base_proj.implemented_count,
                    "implemented_after": proj.implemented_count,
                }
            )
        return {
            "baseline": baseline.label,
            "current": current.label,
            "comparisons": comparisons,
        }

    def save(self, path: str) -> None:
        data = {
            "reports": [r.to_dict() for r in self.reports],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> ProjectionDeltaEngine:
        engine = cls()
        if not os.path.exists(path):
            return engine
        with open(path) as f:
            data = json.load(f)
        for rd in data.get("reports", []):
            projections = []
            for pd in rd.get("projections", []):
                caps = [
                    ProjectionCapability(
                        name=c.get("name", ""),
                        description=c.get("description", ""),
                        desired=c.get("desired", True),
                        implemented=c.get("implemented", False),
                        operational=c.get("operational", False),
                        source=c.get("source", ""),
                    )
                    for c in pd.get("capabilities", [])
                ]
                projections.append(
                    ProjectionDelta(
                        projection_name=pd.get("projection_name", ""),
                        capabilities=caps,
                    )
                )
            report = DeltaReport(
                report_id=rd.get("report_id", f"dr-{uuid4().hex[:8]}"),
                label=rd.get("label", ""),
                projections=projections,
            )
            engine._reports[report.report_id] = report
        return engine
