"""Objective planning — Cockpit intent → grounded, versioned plan records.

MVP Wave 1. Turns one operator objective (a Cockpit chat/voice message) into:

    IntentSpec (reused, deterministic)
    → bounded GroundingSnapshot
    → CurrentStateRecord / DesiredStateRecord / GapAssessmentSnapshot (kept separate)
    → versioned ObjectivePlanRecord (dependency-aware node/edge/lane graph)
    → canonical WorkPackets (materialized via WorkPacketEngine — NO new packet model)
    → plan decision (approve/reject/cancel) that NEVER starts execution.

The persisted ObjectivePlanRecord is a planning SOURCE, not a graph authority:
``substrate.organism.work_graph.WorkGraph`` remains the sole canonical WorkGraph
projection; it composes the packets this package materializes without changes.

All writes route through the canonical governed-mutation runtime under the
registered ``objective_plan_*`` MutationSpecs. All state lives under the
runtime-state boundary at ``<runtime-state>/operator/objective_planning/``.

UMH substrate subsystem. Instance-agnostic. Deterministic-first: every stage has
a deterministic spine; LLM enhancement is optional and validated.
"""

from substrate.execution.planning.records import (
    CurrentStateRecord,
    DesiredStateRecord,
    GapAssessmentSnapshot,
    GroundingSnapshot,
    IntentAssessment,
    IntentAssessmentState,
    ObjectivePlanNode,
    ObjectivePlanRecord,
    ObjectivePlanStatus,
    PlanningSession,
    PlanningStageMarker,
    RevisionEditSet,
)
from substrate.execution.planning.store import PlanningStore, PlanningStoreConflict

__all__ = [
    "CurrentStateRecord",
    "DesiredStateRecord",
    "GapAssessmentSnapshot",
    "GroundingSnapshot",
    "IntentAssessment",
    "IntentAssessmentState",
    "ObjectivePlanNode",
    "ObjectivePlanRecord",
    "ObjectivePlanStatus",
    "PlanningSession",
    "PlanningStageMarker",
    "PlanningStore",
    "PlanningStoreConflict",
    "RevisionEditSet",
]
