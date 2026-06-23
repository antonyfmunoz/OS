"""Self-use certification — C27 Daily Driver Readiness.

Public API for task catalog, gap ledger, projection delta,
meta IDE audit, and certification report.
"""

from __future__ import annotations

from substrate.organism.self_use.certification_report import (
    CertificationGate,
    CertificationReport,
    CoherenceMetrics,
    GateResult,
    ReportBuilder,
)
from substrate.organism.self_use.gap_ledger import (
    GapEntry,
    GapLedger,
    GapType,
)
from substrate.organism.strategic_gap_engine import GapSeverity
from substrate.organism.self_use.meta_ide_audit import (
    AuditMatrix,
    FunctionalStatus,
    SubsystemAudit,
    SubsystemOperation,
)
from substrate.organism.self_use.projection_delta import (
    CapabilityState,
    DeltaReport,
    ProjectionDelta,
    ProjectionDeltaEngine,
)
from substrate.organism.self_use.task_catalog import (
    SelfUseTask,
    TaskCatalog,
    TaskResult,
    TaskStatus,
)
from substrate.organism.self_use.task_taxonomy import (
    CoherenceDomain,
    StreamType,
    TaskDomain,
)

__all__ = [
    "AuditMatrix",
    "CapabilityState",
    "CertificationGate",
    "CertificationReport",
    "CoherenceDomain",
    "CoherenceMetrics",
    "DeltaReport",
    "FunctionalStatus",
    "GapEntry",
    "GapLedger",
    "GapSeverity",
    "GapType",
    "GateResult",
    "ProjectionDelta",
    "ProjectionDeltaEngine",
    "ReportBuilder",
    "SelfUseTask",
    "StreamType",
    "SubsystemAudit",
    "SubsystemOperation",
    "TaskCatalog",
    "TaskDomain",
    "TaskResult",
    "TaskStatus",
]
