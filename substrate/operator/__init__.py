"""UMH Operator — unified intent classification and routing layer.

Converges the two independent operator entry paths:
  Path A (Signal/Conversation): Substrate.execute(signal) -> ExecutionResult
  Path B (Work/Organism): Substrate.execute_work(intent) -> OrganismLoopResult

IntentRouter classifies operator input and routes to the correct path.
IntentReceipt provides a canonical audit trail for every operator interaction.

Phase 18. UMH substrate subsystem. Instance-agnostic.

Phase 31 — Operator Home & Context Engine:
  - OperatorContextEngine: aggregation façade composing 6+ subsystems
    (EventSpine, ServiceFailureEngine, StateCoherenceEngine,
    UMHNodeRegistry, ApprovalInterceptStore, WorkspaceObservationEngine)
    into a single operator-facing view (OperatorSnapshot)
  - OperatorSnapshot: full operator context (health, attention,
    workspaces, approvals, services, nodes, timeline)
  - OperatorAttentionItem: priority-sorted attention queue
  - OperatorHealthSummary: status cards across all subsystems
  - OperatorTimelineEvent: chronological event feed from EventSpine

Phase 32 — Presence & Continuity Runtime:
  - ContinuityEngine: aggregation façade composing
    WorkspaceObservationEngine, WorkspaceTopologyEngine, ActionBridge,
    OperatorContextEngine, UMHNodeRegistry into operator presence view
  - PresenceSnapshot: full operator presence state (device, workspace,
    session, checkpoints)
  - ContinuityCheckpoint: resumable checkpoint for continuity
  - PresenceTimeline: in-memory transition log (device/workspace/session)
  - DeviceContinuityTracker: per-device last-known state

Phase 33 — Screen Awareness Runtime:
  - ScreenObservationEngine: node-role-aware aggregation façade with
    three providers (Inferred/Observed/Reported) and preference ordering
  - ScreenSnapshot: visual workspace context with source provenance
    (source_node_id, source_device_id, source_device_role, source_confidence)
  - ScreenContextProvider: abstract contract + InferredScreenContextProvider
    (VPS), ObservedScreenContextProvider (Beast), ReportedScreenContextProvider
    (iPad/iPhone)
  - RepositoryContextResolver: workspace→repo context mapping
"""

from substrate.operator.intent_router import IntentRouter, RouteClassification, RouteType
from substrate.operator.intent_receipt import IntentReceipt, IntentReceiptStore, ReceiptStatus

__all__ = [
    "IntentRouter",
    "RouteClassification",
    "RouteType",
    "IntentReceipt",
    "IntentReceiptStore",
    "ReceiptStatus",
]
