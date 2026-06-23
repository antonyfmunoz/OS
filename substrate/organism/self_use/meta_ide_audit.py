"""Meta IDE functional audit — manual operator testing of every subsystem.

Each subsystem gets manually exercised through the cockpit and rated
FUNCTIONAL / PARTIAL / BROKEN. The audit matrix is the evidence base
for Gate 3 of C27 certification.
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


class FunctionalStatus(str, Enum):
    FUNCTIONAL = "functional"
    PARTIAL = "partial"
    BROKEN = "broken"
    NOT_TESTED = "not_tested"


SUBSYSTEM_NAMES = (
    "planning",
    "work_packets",
    "proof_packages",
    "reality_systems",
    "organism_runtime",
    "governance",
    "execution",
)


@dataclass
class SubsystemOperation:
    """A single operation tested within a subsystem."""

    operation_id: str = field(default_factory=lambda: f"op-{uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    status: FunctionalStatus = FunctionalStatus.NOT_TESTED
    evidence: str = ""
    screenshot_path: str = ""
    notes: str = ""
    tested_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "evidence": self.evidence,
            "screenshot_path": self.screenshot_path,
            "notes": self.notes,
            "tested_at": self.tested_at.isoformat() if self.tested_at else None,
        }


@dataclass
class SubsystemAudit:
    """Audit results for one Meta IDE subsystem."""

    subsystem: str = ""
    operations: list[SubsystemOperation] = field(default_factory=list)
    overall_status: FunctionalStatus = FunctionalStatus.NOT_TESTED

    def compute_status(self) -> FunctionalStatus:
        if not self.operations:
            return FunctionalStatus.NOT_TESTED
        statuses = [op.status for op in self.operations]
        if all(s == FunctionalStatus.FUNCTIONAL for s in statuses):
            return FunctionalStatus.FUNCTIONAL
        if any(s == FunctionalStatus.BROKEN for s in statuses):
            return FunctionalStatus.BROKEN
        if any(s == FunctionalStatus.NOT_TESTED for s in statuses):
            if any(s == FunctionalStatus.FUNCTIONAL for s in statuses):
                return FunctionalStatus.PARTIAL
            return FunctionalStatus.NOT_TESTED
        return FunctionalStatus.PARTIAL

    def finalize(self) -> None:
        self.overall_status = self.compute_status()

    def to_dict(self) -> dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "overall_status": self.overall_status.value,
            "operations": [op.to_dict() for op in self.operations],
            "functional_count": sum(
                1 for op in self.operations if op.status == FunctionalStatus.FUNCTIONAL
            ),
            "total_operations": len(self.operations),
        }


class AuditMatrix:
    """Full Meta IDE functional audit — subsystem x operation x status."""

    def __init__(self) -> None:
        self._audits: dict[str, SubsystemAudit] = {}

    def add_subsystem(self, audit: SubsystemAudit) -> None:
        self._audits[audit.subsystem] = audit

    def get(self, subsystem: str) -> SubsystemAudit | None:
        return self._audits.get(subsystem)

    def record_operation(
        self,
        subsystem: str,
        operation: SubsystemOperation,
    ) -> None:
        if subsystem not in self._audits:
            self._audits[subsystem] = SubsystemAudit(subsystem=subsystem)
        self._audits[subsystem].operations.append(operation)

    def finalize_all(self) -> None:
        for audit in self._audits.values():
            audit.finalize()

    @property
    def audits(self) -> list[SubsystemAudit]:
        return list(self._audits.values())

    def broken_subsystems(self) -> list[SubsystemAudit]:
        return [a for a in self._audits.values() if a.overall_status == FunctionalStatus.BROKEN]

    def critical_path_broken(self) -> bool:
        """Check if any critical-path subsystem is BROKEN."""
        critical = {"planning", "work_packets", "proof_packages"}
        for name in critical:
            audit = self._audits.get(name)
            if audit and audit.overall_status == FunctionalStatus.BROKEN:
                return True
        return False

    def summary(self) -> dict[str, Any]:
        self.finalize_all()
        return {
            "subsystems_tested": len(self._audits),
            "subsystems_total": len(SUBSYSTEM_NAMES),
            "by_status": {
                s.value: sum(1 for a in self._audits.values() if a.overall_status == s)
                for s in FunctionalStatus
            },
            "critical_path_broken": self.critical_path_broken(),
            "details": {
                name: self._audits[name].to_dict()
                for name in SUBSYSTEM_NAMES
                if name in self._audits
            },
        }

    def to_markdown(self) -> str:
        self.finalize_all()
        lines = ["# Meta IDE Functional Audit", ""]
        lines.append("| Subsystem | Status | Functional | Total |")
        lines.append("|-----------|--------|------------|-------|")
        for name in SUBSYSTEM_NAMES:
            audit = self._audits.get(name)
            if audit:
                func = sum(1 for op in audit.operations if op.status == FunctionalStatus.FUNCTIONAL)
                lines.append(
                    f"| {name} | {audit.overall_status.value.upper()} "
                    f"| {func} | {len(audit.operations)} |"
                )
            else:
                lines.append(f"| {name} | NOT_TESTED | 0 | 0 |")
        lines.append("")
        broken = self.broken_subsystems()
        if broken:
            lines.append("## BROKEN Subsystems")
            for a in broken:
                lines.append(f"### {a.subsystem}")
                for op in a.operations:
                    if op.status == FunctionalStatus.BROKEN:
                        lines.append(f"- **{op.name}**: {op.evidence}")
        return "\n".join(lines)

    def save(self, path: str) -> None:
        data = {
            "audit": self.summary(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> AuditMatrix:
        matrix = cls()
        if not os.path.exists(path):
            return matrix
        with open(path) as f:
            data = json.load(f)
        for name, audit_data in data.get("audit", {}).get("details", {}).items():
            ops = [
                SubsystemOperation(
                    operation_id=op.get("operation_id", f"op-{uuid4().hex[:8]}"),
                    name=op.get("name", ""),
                    description=op.get("description", ""),
                    status=FunctionalStatus(op.get("status", "not_tested")),
                    evidence=op.get("evidence", ""),
                    screenshot_path=op.get("screenshot_path", ""),
                    notes=op.get("notes", ""),
                )
                for op in audit_data.get("operations", [])
            ]
            audit = SubsystemAudit(
                subsystem=name,
                operations=ops,
                overall_status=FunctionalStatus(audit_data.get("overall_status", "not_tested")),
            )
            matrix._audits[name] = audit
        return matrix
