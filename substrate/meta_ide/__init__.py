"""Meta IDE — engineering reality awareness and planning for UMH.

Read-only layer providing repository, workspace, and roadmap awareness.
Phase 22 adds autonomous engineering planning and packetization.
No git mutations. No code execution. Observation and planning only.

Phases 21–22. UMH substrate subsystem. Instance-agnostic.
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
from substrate.meta_ide.engineering_intent import (
    EngineeringIntent,
    EngineeringIntentType,
    EngineeringPlan,
    EngineeringPlanReceipt,
    EngineeringTask,
)
from substrate.meta_ide.engineering_planner import EngineeringPlanner
from substrate.meta_ide.engineering_work_generator import EngineeringWorkGenerator
from substrate.meta_ide.roadmap_gap_engine import (
    GapAnalysis,
    GapRecommendation,
    RoadmapGap,
    RoadmapGapEngine,
)

__all__ = [
    "BranchSnapshot",
    "EngineeringIntent",
    "EngineeringIntentType",
    "EngineeringPlan",
    "EngineeringPlanner",
    "EngineeringPlanReceipt",
    "EngineeringRisk",
    "EngineeringTask",
    "EngineeringWorkGenerator",
    "GapAnalysis",
    "GapRecommendation",
    "MetaIDEWorkspaceEngine",
    "PhaseStatus",
    "RepositoryHealth",
    "RepositorySnapshot",
    "RoadmapGap",
    "RoadmapGapEngine",
    "RoadmapIntelligence",
    "RoadmapStatus",
    "WorkspaceSummary",
    "WorktreeSnapshot",
]
