"""Canonical Type Registry — single source of truth for all UMH domain types.

Every Enum, BaseModel, and dataclass that defines a reusable domain concept
is registered here. New code MUST import from these canonical locations.
Creating a parallel type that overlaps with any registered type is a defect.

This registry is consumed by:
  - scripts/check_type_divergence.py (pre-commit gate)
  - CLAUDE.md (AI instruction)
  - Human code review

To add a new type: define it in the correct canonical module, then add
its name and module path here. The pre-commit hook will enforce it.

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

# ── Canonical Type Registry ─────────────────────────────────────────────────
# Maps type name → list of canonical module paths where it may be defined.
# Most types have exactly one canonical location. Types with multiple entries
# are homonyms: same name, genuinely different concepts (e.g., Capability as
# an Enum of job capability names vs Capability as a Pydantic model describing
# a capability instance).

CANONICAL_TYPES: dict[str, list[str]] = {
    # ── substrate/types.py ──────────────────────────────────────────────
    "SignalSource": ["substrate.types"],
    "SignalUrgency": ["substrate.types"],
    "Modality": ["substrate.types"],
    "Attachment": ["substrate.types"],
    "SignalEnvelope": ["substrate.types"],
    "Identity": ["substrate.types"],
    "MemoryType": ["substrate.types"],
    "MemoryEntry": ["substrate.types"],
    "MemoryQuery": ["substrate.types"],
    "ExecutionContext": ["substrate.types"],
    "PermissionTier": ["substrate.types"],
    "RiskClass": ["substrate.types"],
    "GovernanceDecision": ["substrate.types"],
    "GovernanceVerdict": ["substrate.types"],
    "PipelineGovernanceVerdict": ["substrate.types"],
    "ExecutionPlan": ["substrate.types"],
    "AdapterResponse": ["substrate.types"],
    "ExecutionOutcome": ["substrate.types"],
    "ExecutionResult": ["substrate.types"],
    "PipelineExecutionResult": ["substrate.types"],
    "TraceEventType": ["substrate.types"],
    "TraceEvent": ["substrate.types"],
    "TraceRecord": ["substrate.types"],
    "FeedbackType": ["substrate.types"],
    "FeedbackRecord": ["substrate.types"],
    "ComponentType": ["substrate.types"],
    "ComponentStatus": ["substrate.types"],
    "Component": ["substrate.types"],
    "RegistrationResult": ["substrate.types"],
    "PrimitiveType": ["substrate.types"],
    "OntologicalCategory": ["substrate.types"],
    "RelationshipType": ["substrate.types"],
    "TemporalMode": ["substrate.types"],
    "CausalRole": ["substrate.types"],
    "PrimitiveObservation": ["substrate.types"],
    "IngestionResult": ["substrate.types"],
    "SubstrateStatus": ["substrate.types"],
    "CapabilityStatus": ["substrate.types"],
    "CapabilityCategory": ["substrate.types"],
    "EnvironmentDomain": ["substrate.types"],
    "ResourceStatus": ["substrate.types"],
    "InterpretationType": ["substrate.types"],
    "OutcomeType": ["substrate.types"],
    "ProofType": ["substrate.types"],
    "ProofStatus": ["substrate.types"],
    "WorkPacketStatus": ["substrate.types"],
    "WorkPacketPriority": ["substrate.types"],
    "DecompositionComponentType": ["substrate.types"],
    "AdapterType": ["substrate.types"],
    "AdapterStatus": ["substrate.types"],
    "OperatorType": ["substrate.types"],
    "WorkflowStepType": ["substrate.types"],
    "WorkflowExecutionMode": ["substrate.types"],
    "WorkflowTriggerType": ["substrate.types"],
    "DashboardWidgetType": ["substrate.types"],
    "AutonomyLevel": ["substrate.types"],
    "WorldModelUpdateType": ["substrate.types"],
    # ── substrate/contracts/agent_types.py ──────────────────────────────
    "TaskType": ["substrate.contracts.agent_types"],
    "ModelProvider": ["substrate.contracts.agent_types"],
    # ── substrate/execution/runtime/capability_router.py ────────────────
    # Capability (Enum) lists job capability names: CODE_WRITE, REASON, etc.
    # Capability (BaseModel) in substrate.types describes a capability instance.
    # Both are canonical — different concepts, same name.
    "Capability": [
        "substrate.execution.runtime.capability_router",
        "substrate.types",
    ],
    # ── substrate/execution/runtime/worker_runtime_contracts.py ─────────
    "EnvironmentType": ["substrate.execution.runtime.worker_runtime_contracts"],
    "AuthorityDomain": ["substrate.execution.runtime.worker_runtime_contracts"],
    "MessageBusType": ["substrate.execution.runtime.worker_runtime_contracts"],
    # ── nodes/environments/work_packet.py ───────────────────────────────
    # WorkPacketStatus also in substrate.types — both canonical (different schemas)
    "WorkPacketRiskLevel": ["nodes.environments.work_packet"],
    "WorkPacketExecutionEnvironment": ["nodes.environments.work_packet"],
    # ── substrate/organism/runtime_graph.py ─────────────────────────────
    "AvailabilityStatus": ["substrate.organism.runtime_graph"],
    "RuntimeClass": ["substrate.organism.runtime_graph"],
    "RuntimeCapability": ["substrate.organism.runtime_graph"],
    # ── substrate/organism/coordinator.py ───────────────────────────────
    "WorkUnitStatus": ["substrate.organism.coordinator"],
    "ObjectiveStatus": ["substrate.organism.coordinator"],
    "WorkUnitType": ["substrate.organism.coordinator"],
    # ── substrate/organism/workcell_protocol.py ─────────────────────────
    "WorkcellStatus": ["substrate.organism.workcell_protocol"],
    "WorkcellRole": ["substrate.organism.workcell_protocol"],
    # ── substrate/organism/runtime_supervisor.py ────────────────────────
    "SupervisedHealth": ["substrate.organism.runtime_supervisor"],
    # ── substrate/organism/mission.py ─────────────────────────────────
    "MissionStatus": ["substrate.organism.mission"],
    # ── substrate/organism/workcell_daemon.py ──────────────────────────
    "DaemonStatus": ["substrate.organism.workcell_daemon"],
    # ── substrate/governance/policy/execution_authority_engine_v1.py ─────
    "AuthorityClass": ["substrate.governance.policy.execution_authority_engine_v1"],
    "ApprovalRequirement": ["substrate.governance.policy.execution_authority_engine_v1"],
    # ── substrate/organism/execution_economy.py ─────────────────────────
    "ExecutionClass": ["substrate.organism.execution_economy"],
    "VerificationResult": ["substrate.organism.execution_economy"],
    # ── substrate/organism/recursion_governance.py ─────────────────────
    "EscalationLevel": ["substrate.organism.recursion_governance"],
    "RecursionApproval": ["substrate.organism.recursion_governance"],
    # ── substrate/organism/advisor_hierarchy.py ────────────────────────
    "AdvisorScope": ["substrate.organism.advisor_hierarchy"],
    "AdvisorAuthority": ["substrate.organism.advisor_hierarchy"],
    "AdvisorStatus": ["substrate.organism.advisor_hierarchy"],
    # ── substrate/organism/work_packet.py (Phase 11.1) ─────────────────
    "PacketLifecycleStatus": ["substrate.organism.work_packet"],
    # ── substrate/organism/workcell.py (Phase 11.1) ────────────────────
    "PlanningWorkcellStatus": ["substrate.organism.workcell"],
    "AdvisorBranchStatus": ["substrate.organism.workcell"],
    # ── substrate/organism/leverage_assimilation.py ──────────────────
    "LeveragePrimitiveType": ["substrate.organism.leverage_assimilation"],
    # ── substrate/organism/event_spine.py ─────────────────────────────
    "EventDomain": ["substrate.organism.event_spine"],
    "EventPriority": ["substrate.organism.event_spine"],
    # ── substrate/organism/objective_queue.py ──────────────────────────
    "ObjectiveQueueStatus": ["substrate.organism.objective_queue"],
    # ── substrate/organism/allocation_loop.py ──────────────────────────
    "AllocationStrategy": ["substrate.organism.allocation_loop"],
    # ── substrate/organism/async_coordinator.py ───────────────────────
    "AsyncObjectiveStatus": ["substrate.organism.async_coordinator"],
    # ── substrate/organism/projection_port.py ────────────────────────
    "StateSlice": ["substrate.organism.projection_port"],
    # ── substrate/self_model.py ────────────────────────────────────────
    "Layer": ["substrate.self_model"],
    "ContextKind": ["substrate.self_model"],
    # ── substrate/organism/propagation_graph.py (Phase 12.0) ──────────
    "PropagationNodeType": ["substrate.organism.propagation_graph"],
    "PropagationEdgeType": ["substrate.organism.propagation_graph"],
    "PropagationMode": ["substrate.organism.propagation_graph"],
    "EdgeStrength": ["substrate.organism.propagation_graph"],
    # ── substrate/organism/change_event.py (Phase 12.0) ───────────────
    "ChangeType": ["substrate.organism.change_event"],
    "PropagationActionStatus": ["substrate.organism.change_event"],
    # ── substrate/organism/runtime_session.py (Phase 13.2) ───────────────
    "RuntimeStatus": ["substrate.organism.runtime_session"],
    "RuntimeType": ["substrate.organism.runtime_session"],
    "RuntimeEventType": ["substrate.organism.runtime_session"],
    # ── substrate/organism/operational_truth.py (Phase 13.3S) ────────────
    "OperationalReadinessStatus": ["substrate.organism.operational_truth"],
    "IssuePriority": ["substrate.organism.operational_truth"],
    "IssueStatus": ["substrate.organism.operational_truth"],
    "FixEffort": ["substrate.organism.operational_truth"],
    "OperationalIssue": ["substrate.organism.operational_truth"],
    "ContainerState": ["substrate.organism.operational_truth"],
    "ServiceState": ["substrate.organism.operational_truth"],
    "LLMProviderState": ["substrate.organism.operational_truth"],
    "OperationalTruthSnapshot": ["substrate.organism.operational_truth"],
    # ── substrate/organism/operator_readiness_gate.py (Phase 13.3S) ──────
    "OperatorReadinessReport": ["substrate.organism.operator_readiness_gate"],
    # ── substrate/organism/runtime_fleet.py (Phase 13.4M) ────────────────
    "RuntimeProvider": ["substrate.organism.runtime_fleet"],
    "RuntimeCostModel": ["substrate.organism.runtime_fleet"],
    "RuntimeReadiness": ["substrate.organism.runtime_fleet"],
    "RuntimeFleetMember": ["substrate.organism.runtime_fleet"],
    "RuntimeSelection": ["substrate.organism.runtime_fleet"],
    # ── substrate/organism/projection_source_registry.py (Phase 14.0) ──────
    "ProjectionSourceType": ["substrate.organism.projection_source_registry"],
    "ProjectionName": ["substrate.organism.projection_source_registry"],
    "SourceCanonicality": ["substrate.organism.projection_source_registry"],
    "ReadStatus": ["substrate.organism.projection_source_registry"],
    "ProjectionSource": ["substrate.organism.projection_source_registry"],
    "ProjectionSourceRegistry": ["substrate.organism.projection_source_registry"],
    # ── substrate/organism/projection_reconciliation_engine.py (Phase 14.0) ─
    "DivergenceType": ["substrate.organism.projection_reconciliation_engine"],
    "DivergenceSeverity": ["substrate.organism.projection_reconciliation_engine"],
    "ProjectionDivergence": ["substrate.organism.projection_reconciliation_engine"],
    "ProjectionReconciliationEngine": ["substrate.organism.projection_reconciliation_engine"],
    # ── substrate/workstation/ (Phase 14.15 — continuity layer) ──────────
    "ContinuityState": ["substrate.workstation.continuity"],
    "ContinuityStateMachine": ["substrate.workstation.continuity"],
    "ContinuityTransition": ["substrate.workstation.continuity"],
    "LifecycleMode": ["substrate.workstation.lifecycle_modes"],
    "ProfileMode": ["substrate.workstation.profile_modes"],
    "ProfileBehavior": ["substrate.workstation.profile_behavior"],
    "VoiceBehavior": ["substrate.workstation.profile_behavior"],
    "NotificationPolicy": ["substrate.workstation.profile_behavior"],
    "CameraPolicy": ["substrate.workstation.profile_behavior"],
    "ExecutionMode": ["substrate.workstation.profile_behavior"],
    "ReportingCadence": ["substrate.workstation.profile_behavior"],
    "ActivationSource": ["substrate.workstation.activation"],
    "ActivationSignal": ["substrate.workstation.activation"],
    "PresenceSession": ["substrate.workstation.activation"],
    "DeviceSession": ["substrate.workstation.device_presence"],
    "ContinuityCheckpoint": ["substrate.workstation.checkpoint"],
    "CheckpointManager": ["substrate.workstation.checkpoint"],
    "ReturnBrief": ["substrate.workstation.resume_brief"],
    "ReturnBriefGenerator": ["substrate.workstation.resume_brief"],
    "IntentContract": ["substrate.workstation.intent_contract"],
    "IntentContractManager": ["substrate.workstation.intent_contract"],
    "IntentStatus": ["substrate.workstation.intent_contract"],
    "CompositeState": ["substrate.workstation.continuity_engine"],
    "ContinuityEngine": ["substrate.workstation.continuity_engine"],
    "StartupResult": ["substrate.workstation.continuity_engine"],
    "ShutdownResult": ["substrate.workstation.continuity_engine"],
    "CommandIntent": ["substrate.workstation.command_router"],
    "LoopContract": ["substrate.workstation.loop_engine"],
    "LoopStatus": ["substrate.workstation.loop_engine"],
    "EndStateVerifier": ["substrate.workstation.loop_engine"],
    # ── substrate/organism/agent_execution_runner.py (Operator Loop Phase 2) ─
    "AgentExecutionPlan": ["substrate.organism.agent_execution_runner"],
    "ExecutionRecord": ["substrate.organism.agent_execution_runner"],
    "FailureReport": ["substrate.organism.agent_execution_runner"],
    # ── substrate/organism/domain_registry.py (Empire Engine Phase 3) ────
    "ProofRequirement": ["substrate.organism.domain_registry"],
    "DomainDefinition": ["substrate.organism.domain_registry"],
    "DomainRegistry": ["substrate.organism.domain_registry"],
    # ── substrate/organism/agent_registry.py (Empire Engine Phase 3) ─────
    "AgentType": ["substrate.organism.agent_registry"],
    "AgentRegistry": ["substrate.organism.agent_registry"],
    # ── substrate/organism/empire_router.py (Empire Engine Phase 3) ──────
    "RoutingResult": ["substrate.organism.empire_router"],
    "RealitySnapshot": ["substrate.organism.empire_router"],
    "EmpireRouter": ["substrate.organism.empire_router"],
    # ── substrate/organism/strategic_gap_engine.py (Strategic Gap Phase 4) ──
    "GoalStatus": ["substrate.organism.strategic_gap_engine"],
    "GoalType": ["substrate.organism.strategic_gap_engine"],
    "GapSeverity": ["substrate.organism.strategic_gap_engine"],
    "RecommendationStatus": ["substrate.organism.strategic_gap_engine"],
    "SuccessCriterion": ["substrate.organism.strategic_gap_engine"],
    "Goal": ["substrate.organism.strategic_gap_engine"],
    "Gap": ["substrate.organism.strategic_gap_engine"],
    "Recommendation": ["substrate.organism.strategic_gap_engine"],
    "DecisionRecord": ["substrate.organism.strategic_gap_engine"],
    "GoalRegistry": ["substrate.organism.strategic_gap_engine"],
    "GapDetector": ["substrate.organism.strategic_gap_engine"],
    "RecommendationEngine": ["substrate.organism.strategic_gap_engine"],
    "StrategicGapEngine": ["substrate.organism.strategic_gap_engine"],
    # Phase 5: Strategic Tick Loop
    "TickFrequency": ["substrate.organism.strategic_tick_loop"],
    "RecommendationLifecycle": ["substrate.organism.strategic_tick_loop"],
    "DriftSeverity": ["substrate.organism.strategic_tick_loop"],
    "RealityDelta": ["substrate.organism.strategic_tick_loop"],
    "ChangeDetector": ["substrate.organism.strategic_tick_loop"],
    "CandidateWorkItem": ["substrate.organism.strategic_tick_loop"],
    "CandidateWorkQueue": ["substrate.organism.strategic_tick_loop"],
    "DriftWarning": ["substrate.organism.strategic_tick_loop"],
    "DriftDetector": ["substrate.organism.strategic_tick_loop"],
    "TickRecord": ["substrate.organism.strategic_tick_loop"],
    "StrategicTickLoop": ["substrate.organism.strategic_tick_loop"],
    # Phase 6: Projection Engine
    "TimeHorizon": ["substrate.organism.projection_engine"],
    "TrendDirection": ["substrate.organism.projection_engine"],
    "RiskSeverity": ["substrate.organism.projection_engine"],
    "ProjectionConfidence": ["substrate.organism.projection_engine"],
    "TrendRecord": ["substrate.organism.projection_engine"],
    "TrendDetector": ["substrate.organism.projection_engine"],
    "Projection": ["substrate.organism.projection_engine"],
    "StrategicRisk": ["substrate.organism.projection_engine"],
    "StrategicOpportunity": ["substrate.organism.projection_engine"],
    "ProjectionOutcome": ["substrate.organism.projection_engine"],
    "AccuracyTracker": ["substrate.organism.projection_engine"],
    "RiskDetector": ["substrate.organism.projection_engine"],
    "OpportunityDetector": ["substrate.organism.projection_engine"],
    "ProjectionGenerator": ["substrate.organism.projection_engine"],
    "ProjectionEngine": ["substrate.organism.projection_engine"],
    # Phase 7: Continuity Runtime
    "AttentionState": ["substrate.organism.continuity_runtime"],
    "TimelineEventType": ["substrate.organism.continuity_runtime"],
    "ChangeCategory": ["substrate.organism.continuity_runtime"],
    "BriefSection": ["substrate.organism.continuity_runtime"],
    "ContinuitySnapshot": ["substrate.organism.continuity_runtime"],
    "TimelineEvent": ["substrate.organism.continuity_runtime"],
    "ResumeReport": ["substrate.organism.continuity_runtime"],
    "OperatorBrief": ["substrate.organism.continuity_runtime"],
    "WorkLineage": ["substrate.organism.continuity_runtime"],
    "SessionHandoff": ["substrate.organism.continuity_runtime"],
    "AttentionModel": ["substrate.organism.continuity_runtime"],
    "TimelineEngine": ["substrate.organism.continuity_runtime"],
    "ResumeStateEngine": ["substrate.organism.continuity_runtime"],
    "WorkContinuityGraph": ["substrate.organism.continuity_runtime"],
    "OperatorBriefGenerator": ["substrate.organism.continuity_runtime"],
    "SnapshotCollector": ["substrate.organism.continuity_runtime"],
    "ContinuityRuntime": ["substrate.organism.continuity_runtime"],
    # Phase 8: Presence Runtime
    "PresenceAttentionState": ["substrate.organism.presence_runtime"],
    "InterruptionLevel": ["substrate.organism.presence_runtime"],
    "PresenceEventType": ["substrate.organism.presence_runtime"],
    "InteractionSurface": ["substrate.organism.presence_runtime"],
    "DeviceInfo": ["substrate.organism.presence_runtime"],
    "SessionInfo": ["substrate.organism.presence_runtime"],
    "PresenceSnapshot": ["substrate.organism.presence_runtime"],
    "PresenceEvent": ["substrate.organism.presence_runtime"],
    "DeviceRegistry": ["substrate.organism.presence_runtime"],
    "SessionRegistry": ["substrate.organism.presence_runtime"],
    "AttentionEngine": ["substrate.organism.presence_runtime"],
    "InterruptibilityEngine": ["substrate.organism.presence_runtime"],
    "PresenceTimeline": ["substrate.organism.presence_runtime"],
    "PresenceRuntime": ["substrate.organism.presence_runtime"],
    # Phase 9: Command Runtime
    "CommandActionType": ["substrate.organism.command_runtime"],
    "CommandStatus": ["substrate.organism.command_runtime"],
    "CommandSource": ["substrate.organism.command_runtime"],
    "CommandEventType": ["substrate.organism.command_runtime"],
    "CommandContext": ["substrate.organism.command_runtime"],
    "Command": ["substrate.organism.command_runtime"],
    "CommandEvent": ["substrate.organism.command_runtime"],
    "CommandRoutingDecision": ["substrate.organism.command_runtime"],
    "CommandClassifier": ["substrate.organism.command_runtime"],
    "ContextAssembler": ["substrate.organism.command_runtime"],
    "CommandRouter": ["substrate.organism.command_runtime"],
    "CommandTimeline": ["substrate.organism.command_runtime"],
    "CommandHistory": ["substrate.organism.command_runtime"],
    "CommandRuntime": ["substrate.organism.command_runtime"],
    # Phase 10: Workstation Runtime
    "WorkstationMode": ["substrate.organism.workstation_runtime"],
    "WorkspaceStatus": ["substrate.organism.workstation_runtime"],
    "PreparationStepType": ["substrate.organism.workstation_runtime"],
    "SnapshotTrigger": ["substrate.organism.workstation_runtime"],
    "RecommendationType": ["substrate.organism.workstation_runtime"],
    "WorkspaceTemplate": ["substrate.organism.workstation_runtime"],
    "PreparationStep": ["substrate.organism.workstation_runtime"],
    "WorkspacePreparationPlan": ["substrate.organism.workstation_runtime"],
    "ApplicationState": ["substrate.organism.workstation_runtime"],
    "WorkspaceState": ["substrate.organism.workstation_runtime"],
    "WorkspaceSnapshot": ["substrate.organism.workstation_runtime"],
    "RestorationPlan": ["substrate.organism.workstation_runtime"],
    "WorkspaceSequence": ["substrate.organism.workstation_runtime"],
    "WorkstationProfile": ["substrate.organism.workstation_runtime"],
    "Workstation": ["substrate.organism.workstation_runtime"],
    "WorkstationRecommendation": ["substrate.organism.workstation_runtime"],
    "ModeClassifier": ["substrate.organism.workstation_runtime"],
    "WorkspaceTemplateRegistry": ["substrate.organism.workstation_runtime"],
    "WorkspaceContextAssembler": ["substrate.organism.workstation_runtime"],
    "SnapshotStore": ["substrate.organism.workstation_runtime"],
    "RecommendationEngine": ["substrate.organism.workstation_runtime"],
    "PreparationSequencer": ["substrate.organism.workstation_runtime"],
    "WorkstationRuntime": ["substrate.organism.workstation_runtime"],
    # Phase 11: Profile Runtime
    "ProfileModeEnum": ["substrate.organism.profile_runtime"],
    "SystemModeEnum": ["substrate.organism.profile_runtime"],
    "ActivationSource": ["substrate.organism.profile_runtime"],
    "ProfileEventType": ["substrate.organism.profile_runtime"],
    "ConflictSeverity": ["substrate.organism.profile_runtime"],
    "Profile": ["substrate.organism.profile_runtime"],
    "SystemMode": ["substrate.organism.profile_runtime"],
    "ProfileModeState": ["substrate.organism.profile_runtime"],
    "ProfileModeTransition": ["substrate.organism.profile_runtime"],
    "ProfilePreference": ["substrate.organism.profile_runtime"],
    "ProfileContext": ["substrate.organism.profile_runtime"],
    "ProfileActivationPlan": ["substrate.organism.profile_runtime"],
    "ProfileRuntimeSnapshot": ["substrate.organism.profile_runtime"],
    "ProfileConflict": ["substrate.organism.profile_runtime"],
    "ProfileRecommendation": ["substrate.organism.profile_runtime"],
    "ProfileRegistry": ["substrate.organism.profile_runtime"],
    "SystemModeRegistry": ["substrate.organism.profile_runtime"],
    "ProfileModeStateMachine": ["substrate.organism.profile_runtime"],
    "SystemModeStateMachine": ["substrate.organism.profile_runtime"],
    "ConflictDetector": ["substrate.organism.profile_runtime"],
    "ProfileActivationPlanner": ["substrate.organism.profile_runtime"],
    "ProfileTimeline": ["substrate.organism.profile_runtime"],
    "ProfileContextAssembler": ["substrate.organism.profile_runtime"],
    "ProfileRuntime": ["substrate.organism.profile_runtime"],
    # Phase 12: Session Runtime
    "SessionType": ["substrate.organism.session_runtime"],
    "SessionStatus": ["substrate.organism.session_runtime"],
    "SessionAuthority": ["substrate.organism.session_runtime"],
    "SessionEventType": ["substrate.organism.session_runtime"],
    "HandoffStatus": ["substrate.organism.session_runtime"],
    "Session": ["substrate.organism.session_runtime"],
    "SessionEvent": ["substrate.organism.session_runtime"],
    "SessionHandoff": ["substrate.organism.session_runtime"],
    "SessionContinuityLink": ["substrate.organism.session_runtime"],
    "SessionRuntimeSnapshot": ["substrate.organism.session_runtime"],
    "SessionRegistry": ["substrate.organism.session_runtime"],
    "SessionLifecycleEngine": ["substrate.organism.session_runtime"],
    "SessionHandoffRuntime": ["substrate.organism.session_runtime"],
    "SessionContinuityGraph": ["substrate.organism.session_runtime"],
    "SessionTimeline": ["substrate.organism.session_runtime"],
    "SessionRuntime": ["substrate.organism.session_runtime"],
    # Phase 13: Execution Coordinator Runtime
    "ExecutionPlanStatus": ["substrate.organism.execution_coordinator"],
    "ExecutionTargetType": ["substrate.organism.execution_coordinator"],
    "ExecutionMode": ["substrate.organism.execution_coordinator"],
    "ExecutionPriority": ["substrate.organism.execution_coordinator"],
    "CoordinatorApprovalState": ["substrate.organism.execution_coordinator"],
    "LifecycleEventType": ["substrate.organism.execution_coordinator"],
    "CoordinatorExecutionPlan": ["substrate.organism.execution_coordinator"],
    "ExecutorDefinition": ["substrate.organism.execution_coordinator"],
    "LifecycleEvent": ["substrate.organism.execution_coordinator"],
    "ExecutionCoordinatorSnapshot": ["substrate.organism.execution_coordinator"],
    "ExecutorRegistry": ["substrate.organism.execution_coordinator"],
    "ExecutionQueue": ["substrate.organism.execution_coordinator"],
    "ExecutionLifecycleTracker": ["substrate.organism.execution_coordinator"],
    "GovernanceGate": ["substrate.organism.execution_coordinator"],
    "PlanStore": ["substrate.organism.execution_coordinator"],
    "CrossRuntimeCompositor": ["substrate.organism.execution_coordinator"],
    "ExecutionCoordinator": ["substrate.organism.execution_coordinator"],
    # Phase 14: Executor Runtime
    "ExecutorLifecycleStatus": ["substrate.organism.executor_runtime"],
    "ExecutorType": ["substrate.organism.executor_runtime"],
    "ExecutorRequestStatus": ["substrate.organism.executor_runtime"],
    "ExecutorEventType": ["substrate.organism.executor_runtime"],
    "ExecutorApprovalState": ["substrate.organism.executor_runtime"],
    "ExecutorRuntimeContext": ["substrate.organism.executor_runtime"],
    "ExecutorRequest": ["substrate.organism.executor_runtime"],
    "ExecutorArtifact": ["substrate.organism.executor_runtime"],
    "ExecutorResult": ["substrate.organism.executor_runtime"],
    "ExecutorLifecycleEvent": ["substrate.organism.executor_runtime"],
    "ExecutorRuntimeSnapshot": ["substrate.organism.executor_runtime"],
    "ExecutorContract": ["substrate.organism.executor_runtime"],
    "SimulationExecutor": ["substrate.organism.executor_runtime"],
    "ExecutorImplementationRegistry": ["substrate.organism.executor_runtime"],
    "ExecutorRequestStore": ["substrate.organism.executor_runtime"],
    "ExecutorResultStore": ["substrate.organism.executor_runtime"],
    "ExecutorLifecycleTracker": ["substrate.organism.executor_runtime"],
    "ExecutorGovernanceGate": ["substrate.organism.executor_runtime"],
    "ExecutorContextAssembler": ["substrate.organism.executor_runtime"],
    "ExecutorRuntime": ["substrate.organism.executor_runtime"],
    # Phase 15A: Workstation Executor
    "ExecutionProof": ["substrate.organism.executors.workstation_executor"],
    "WorkstationExecutor": ["substrate.organism.executors.workstation_executor"],
    # Phase 15B: Execution Telemetry
    "TelemetryEventType": ["substrate.organism.executors.execution_telemetry"],
    "ExecutionTelemetryEvent": ["substrate.organism.executors.execution_telemetry"],
    "InMemoryExecutionTelemetryStore": ["substrate.organism.executors.execution_telemetry"],
    "ExecutionTelemetryEmitter": ["substrate.organism.executors.execution_telemetry"],
    # Phase 15C: Approval Intercepts
    "ApprovalInterceptStatus": ["substrate.organism.executors.approval_intercept"],
    "ApprovalInterceptRequest": ["substrate.organism.executors.approval_intercept"],
    "ApprovalInterceptStore": ["substrate.organism.executors.approval_intercept"],
    "ApprovalInterceptService": ["substrate.organism.executors.approval_intercept"],
    # Phase 16: Runtime State Registry
    "WorktreeInfo": ["substrate.organism.runtime_state_registry"],
    "GitRepoInfo": ["substrate.organism.runtime_state_registry"],
    "ProcessInfo": ["substrate.organism.runtime_state_registry"],
    "ContainerInfo": ["substrate.organism.runtime_state_registry"],
    "ExecutionInfo": ["substrate.organism.runtime_state_registry"],
    "RuntimeSnapshot": ["substrate.organism.runtime_state_registry"],
    "RuntimeStateStore": ["substrate.organism.runtime_state_registry"],
    "RuntimeStateRefresher": ["substrate.organism.runtime_state_registry"],
    "RuntimeStateRegistry": ["substrate.organism.runtime_state_registry"],
    # Phase 17A: Agent Executor
    "AgentTaskResult": ["substrate.organism.executors.agent_executor"],
    "AgentExecutionProof": ["substrate.organism.executors.agent_executor"],
    "AgentExecutor": ["substrate.organism.executors.agent_executor"],
}


# ── Legacy Duplicates ───────────────────────────────────────────────────────
# Pre-existing type definitions that duplicate canonical types. These existed
# before the divergence gate was installed (2026-05-27). Each entry is:
#   file_module_path → set of type names it's allowed to define despite
#   those names being owned by another module.
#
# These are TECHNICAL DEBT, not design. Each should be converged to import
# from the canonical source. New entries here require explicit justification.
# The gate blocks NEW divergence; this allowlist grandfathers OLD divergence.

LEGACY_DUPLICATES: dict[str, set[str]] = {
    # substrate.types defines both WorkPacketStatus (Enum) and references it
    # nodes.environments.work_packet also defines it — same semantics, needs merge
    "nodes.environments.work_packet": {"WorkPacketStatus"},
    # substrate.types.ProofStatus vs worker_runtime_contracts.ProofStatus
    "substrate.execution.runtime.worker_runtime_contracts": {"ProofStatus"},
    # Older contract modules that predate type centralization
    "substrate.execution.runtime.execution_contracts_v1": {"SignalSource", "GovernanceVerdict"},
    "substrate.execution.runtime.runtime_execution_result_v1": {"ExecutionOutcome"},
    "substrate.execution.bridge.capabilities": {"Capability"},
    "substrate.execution.loop.execution_loop": {"ExecutionResult"},
    "substrate.state.memory.contracts.canonical_memory_store_v1": {"MemoryEntry"},
    "substrate.sockets.envelopes": {"SignalEnvelope"},
    "substrate.foundation.primitives": {"Modality"},
    "substrate.understanding.ontology.primitive_decomposition_v1": {
        "PrimitiveType",
        "RelationshipType",
        "PrimitiveObservation",
    },
    "substrate.understanding.perception.orchestrator": {"IngestionResult"},
    "adapters.adapter_engine.substrate_candidate_gen_v1": {"MemoryType"},
    "nodes.environments.execution_binding_contracts": {"EnvironmentType"},
}


def lookup(type_name: str) -> list[str] | None:
    """Return the canonical import paths for a type name, or None if not registered."""
    return CANONICAL_TYPES.get(type_name)


def check_name(type_name: str, defining_module: str) -> str | None:
    """Return an error message if type_name is already registered elsewhere.

    Returns None if:
    - The name is not in the registry (genuinely new type)
    - The defining module is one of the canonical locations
    - The defining module is in the legacy duplicates allowlist
    """
    canonical_list = CANONICAL_TYPES.get(type_name)
    if canonical_list is None:
        return None
    for canonical in canonical_list:
        if defining_module == canonical or defining_module.endswith(canonical):
            return None
    legacy = LEGACY_DUPLICATES.get(defining_module, set())
    if type_name in legacy:
        return None
    return (
        f"DIVERGENCE BLOCKED: '{type_name}' already exists in "
        f"{canonical_list[0]}. "
        f"Import it: from {canonical_list[0]} import {type_name}"
    )
