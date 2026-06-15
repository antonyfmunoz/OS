"""Meta IDE — engineering reality awareness for UMH.

Read-only layer providing repository, workspace, and roadmap awareness.
No git mutations. No code execution. Observation only.

Phase 21. UMH substrate subsystem. Instance-agnostic.
"""

from substrate.meta_ide.repository_model import (
    BranchSnapshot,
    RepositoryHealth,
    RepositorySnapshot,
    WorktreeSnapshot,
)
from substrate.meta_ide.workspace_intelligence import (
    EngineeringRisk,
    MetaIDEWorkspaceEngine,
    WorkspaceSummary,
)
from substrate.meta_ide.roadmap_intelligence import (
    PhaseStatus,
    RoadmapIntelligence,
    RoadmapStatus,
)

__all__ = [
    "BranchSnapshot",
    "EngineeringRisk",
    "MetaIDEWorkspaceEngine",
    "PhaseStatus",
    "RepositoryHealth",
    "RepositorySnapshot",
    "RoadmapIntelligence",
    "RoadmapStatus",
    "WorkspaceSummary",
    "WorktreeSnapshot",
]
