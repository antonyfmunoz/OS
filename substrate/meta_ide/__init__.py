"""Meta IDE — engineering reality awareness, planning, and proof loop.

Read-only layer providing repository, workspace, and roadmap awareness.
Phase 22 adds autonomous engineering planning and packetization.
Phase 23 adds governed execution coordination and proof review.
Phase 27 adds workspace runtime topology (read-only).
No git mutations. No auto-merge/push/deploy. Observation, planning, and proof only.

Phases 21–27. UMH substrate subsystem. Instance-agnostic.
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
from substrate.meta_ide.engineering_execution import (
    EngineeringArtifact,
    EngineeringArtifactType,
    EngineeringExecutionSession,
    EngineeringExecutionStatus,
    EngineeringProofPackage,
    OperatorRecommendation,
)
from substrate.meta_ide.engineering_session_coordinator import (
    EngineeringSessionCoordinator,
)
from substrate.meta_ide.review_package_builder import ReviewPackageBuilder
from substrate.meta_ide.workspace_observation import (
    ContainerObservation,
    EngineeringSessionObservation,
    ObservationDomain,
    PreviewObservation,
    ProcessHealth,
    TerminalObservation,
    WorkspaceObservationEngine,
    WorkspaceObservationSnapshot,
)
from substrate.meta_ide.workspace_runtime_graph import (
    BuildTargetType,
    RuntimeTargetType,
    WorkspaceBuildTarget,
    WorkspaceDefinition,
    WorkspaceHealth,
    WorkspaceRepository,
    WorkspaceRuntime,
    WorkspaceRuntimeGraph,
    WorkspaceType,
)
from substrate.meta_ide.workspace_registry import WorkspaceRegistry
from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

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
    # Phase 23: Engineering Proof Loop
    "EngineeringArtifact",
    "EngineeringArtifactType",
    "EngineeringExecutionSession",
    "EngineeringExecutionStatus",
    "EngineeringProofPackage",
    "EngineeringSessionCoordinator",
    "OperatorRecommendation",
    "ReviewPackageBuilder",
    # Phase 25: Workspace Observation
    "ContainerObservation",
    "EngineeringSessionObservation",
    "ObservationDomain",
    "PreviewObservation",
    "ProcessHealth",
    "TerminalObservation",
    "WorkspaceObservationEngine",
    "WorkspaceObservationSnapshot",
    # Phase 27: Workspace Runtime Graph
    "BuildTargetType",
    "RuntimeTargetType",
    "WorkspaceBuildTarget",
    "WorkspaceDefinition",
    "WorkspaceHealth",
    "WorkspaceRegistry",
    "WorkspaceRepository",
    "WorkspaceRuntime",
    "WorkspaceRuntimeGraph",
    "WorkspaceTopologyEngine",
    "WorkspaceType",
]
