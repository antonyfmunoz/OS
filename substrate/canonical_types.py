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
    # WP-P2-002: authority-role canonicals (verified present, now registered so
    # the registry audit polices them). RoleScope is the scope enum; AgentRole /
    # RoleRegistry the role type + registry, all in the roles bridge module.
    "AgentRole": ["substrate.execution.bridge.roles"],
    "RoleScope": ["substrate.execution.bridge.roles"],
    "RoleRegistry": ["substrate.execution.bridge.roles"],
    "RiskClass": ["substrate.types"],
    # WP-P2-002: the side-effect CATEGORY axis (8 members), bridges to the
    # severity RiskClass via to_risk_class(). The canonical risk vocabulary is
    # the pair (RiskClass severity x ActionRiskCategory category).
    "ActionRiskCategory": ["substrate.governance.risk_classes"],
    "GovernanceDecision": ["substrate.types"],
    "GovernanceVerdict": ["substrate.types"],
    "PipelineGovernanceVerdict": ["substrate.types"],
    # WP-P1-007: one canonical approval authority
    "ApprovalState": ["substrate.types"],
    "ApprovalOrigin": ["substrate.types"],
    "ApprovalRequest": ["substrate.types"],
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
    "RouterWorkPacket": ["substrate.control_plane.router.router_contracts"],
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
    # ── substrate/contracts/work_context.py (Wave 1 constitutional contracts) ──
    # WorkLineageContext is deliberately NOT named WorkLineage: that name is the
    # canonical continuity aggregate in substrate.organism.continuity_runtime
    # (a different concept). See docs/cockpit-surface-convergence.md.
    "PrincipalContext": ["substrate.contracts.work_context"],
    "PrincipalKind": ["substrate.contracts.work_context"],
    "EpistemicStatus": ["substrate.contracts.work_context"],
    "WorkScope": ["substrate.contracts.work_context"],
    "WorkLineageContext": ["substrate.contracts.work_context"],
    "EvidenceRef": ["substrate.contracts.work_context"],
    "SkillRequirementRef": ["substrate.contracts.work_context"],
    "WorkRequirements": ["substrate.contracts.work_context"],
    # ── substrate/execution/intent/ (Wave 1 canonical Operator Intent Protocol) ──
    "IntentClass": ["substrate.execution.intent.protocol"],
    "PlanningScale": ["substrate.execution.intent.protocol"],
    "DecisionRequirement": ["substrate.execution.intent.protocol"],
    "IntentResolution": ["substrate.execution.intent.protocol"],
    "ReferenceResolution": ["substrate.execution.intent.protocol"],
    "ExistingWorkRelationshipResolution": ["substrate.execution.intent.protocol"],
    "MaterialAmbiguity": ["substrate.execution.intent.protocol"],
    "ContextFrame": ["substrate.execution.intent.context_frame"],
    "SourceCorrespondenceResolution": ["substrate.execution.intent.correspondence"],
    "GroundingAdjudication": ["substrate.execution.intent.correspondence"],
    # ── substrate/execution/planning/records.py (Wave 1 planning records) ──
    "PlanningSession": ["substrate.execution.planning.records"],
    "PlanningStageMarker": ["substrate.execution.planning.records"],
    "ObjectivePlanRecord": ["substrate.execution.planning.records"],
    "ObjectivePlanNode": ["substrate.execution.planning.records"],
    "ObjectiveLane": ["substrate.execution.planning.records"],
    "LaneDeclarationError": ["substrate.execution.planning.records"],
    "DecompositionMode": ["substrate.execution.planning.records"],
    "ObjectivePlanStatus": ["substrate.execution.planning.records"],
    "IntentAssessment": ["substrate.execution.planning.records"],
    "IntentAssessmentState": ["substrate.execution.planning.records"],
    "GroundingSnapshot": ["substrate.execution.planning.records"],
    "CurrentStateRecord": ["substrate.execution.planning.records"],
    "DesiredStateRecord": ["substrate.execution.planning.records"],
    "RevisionEditSet": ["substrate.execution.planning.records"],
    "GapAssessmentSnapshot": ["substrate.execution.planning.records"],
    # ── substrate/execution/planning/ (Wave 1 composition) ──
    "WorkArchetypeResolution": ["substrate.execution.planning.archetypes"],
    "DevelopmentPlanningProfile": ["substrate.execution.planning.dev_profile"],
    "DecisionReadiness": ["substrate.execution.planning.readiness"],
    "DecisionReadinessAssessment": ["substrate.execution.planning.readiness"],
    "InstructionCompilationRequest": ["substrate.execution.planning.instruction_compilation"],
    "ModelExecutionPackage": ["substrate.execution.planning.instruction_compilation"],
    # ── substrate/execution/attempts/ (Wave 2 canonical execution slice) ──
    # ExecutionAttempt is the ONE canonical concrete execution object. The
    # ExecutionAuthorizationGrant is the persisted bounded EFFECT of an APPROVED
    # execution_authorization Decision — NOT a rival Decision (ApprovalRequest
    # remains the sole Decision authority; the grant carries no requested/denied
    # state). ExecutionReadinessAssessment is distinct from the organism
    # WorkReadinessRuntime.ReadinessAssessment (a legacy read-surface), and from
    # planning.readiness.DecisionReadinessAssessment (plan-acceptance readiness).
    "GraphShapeVerdict": ["substrate.execution.attempts.graph_shape_gate"],
    "AttemptExecutionKind": ["substrate.execution.attempts.records"],
    "CanonicalRecordSourceError": ["substrate.execution.attempts.field_control_plane"],
    "CompositionAuthorityUnresolved": ["substrate.execution.attempts.records"],
    "CompositionConflict": ["substrate.execution.attempts.composition"],
    "CompositionError": ["substrate.execution.attempts.composition"],
    "CompositionResult": ["substrate.execution.attempts.composition"],
    # THE single declaration authority: what execution class each Task of one
    # run is. Built once from canonical lineage, immutable for the run, carried
    # into Attempt creation. Never re-derived from a mutable file by a consumer.
    "VerifiedExecutionDeclaration": ["substrate.execution.attempts.records"],
    # The THREE-STATE declaration outcome. DECLARED / NO_COMPOSITION /
    # UNANSWERABLE must stay distinguishable: collapsing the last two into one
    # absence is what let five reproduced bypasses persist an immutable
    # `Task C + worker` row. UNKNOWN MUST NEVER MEAN WORKER.
    "DeclarationOutcome": ["substrate.execution.attempts.records"],
    "DeclarationResult": ["substrate.execution.attempts.records"],
    "ExecutionAttempt": ["substrate.execution.attempts.records"],
    "ExecutionAttemptStatus": ["substrate.execution.attempts.records"],
    "AttemptTransition": ["substrate.execution.attempts.records"],
    "ExecutionAuthorizationGrant": ["substrate.execution.attempts.records"],
    "ExecutionAuthorizationGrantStatus": ["substrate.execution.attempts.records"],
    "ExecutionAttemptStore": ["substrate.execution.attempts.store"],
    "AttemptStoreConflict": ["substrate.execution.attempts.store"],
    "AttemptLifecycleError": ["substrate.execution.attempts.lifecycle"],
    # C2 readiness + authorization. ExecutionReadinessAssessment is the
    # execution-gating readiness type (distinct from organism ReadinessAssessment
    # and planning DecisionReadinessAssessment). ExecutionDecisionConflict guards
    # the one execution-authorization write path.
    "ExecutionReadinessAssessment": ["substrate.execution.attempts.readiness"],
    "ExecutionReadinessState": ["substrate.execution.attempts.readiness"],
    # R3: AdmissionVerdict is the ONE canonical admission answer, produced by
    # `admission.authorize_admission` and consumed atomically by the scheduler
    # at the final attempt-admission boundary. It does NOT rival
    # ExecutionReadinessAssessment: readiness is the pre-grant advisory
    # assessment surface; AdmissionVerdict is the enforcing authority. Exactly
    # one component decides admission, and this is its verdict type.
    "AdmissionVerdict": ["substrate.execution.attempts.admission"],
    "ExecutionDecisionConflict": ["substrate.execution.attempts.decisions"],
    "ExecutionAuthorizationDecisionSource": ["substrate.execution.attempts.decisions"],
    # C3 placement + lease + instruction compilation. ExecutionAssignment is the
    # durable canonical placement record; ExecutionEnvironmentLease is the one
    # writable-window record (no prior owner). DispatchBlocked / PlacementError /
    # LeaseError are the fail-closed guards on each stage.
    "ExecutionAssignment": ["substrate.execution.attempts.placement"],
    "PlacementError": ["substrate.execution.attempts.placement"],
    "ExecutionEnvironmentLease": ["substrate.execution.attempts.leases"],
    "LeaseManager": ["substrate.execution.attempts.leases"],
    "LeaseError": ["substrate.execution.attempts.leases"],
    "DispatchBlocked": ["substrate.execution.attempts.dispatch"],
    # C4 scheduler. AttemptScheduler is the bounded, single-writer, dependency-
    # aware admission core (NOT a persistent supervisor — Wave 3).
    "AttemptScheduler": ["substrate.execution.attempts.scheduler"],
    "SchedulerPassReport": ["substrate.execution.attempts.scheduler"],
    # C4 part 2: real worker, enforced host isolation, signed dispatch spool.
    "WorkerResult": ["substrate.execution.attempts.worker_claude_cli"],
    "IsolationProfile": ["substrate.execution.attempts.host_isolation"],
    "IsolationUnavailable": ["substrate.execution.attempts.host_isolation"],
    "DispatchEnvelope": ["substrate.execution.attempts.spool"],
    "DispatchSpool": ["substrate.execution.attempts.spool"],
    # C5 verification + the two Proof classifications under the one canonical
    # Proof authority (ProofPackage). VerificationVerdict carries an AttemptProof
    # or PlanExecutionProof classification; it is NOT a rival Proof type.
    "VerificationVerdict": ["substrate.execution.attempts.verification"],
    "VerificationCheck": ["substrate.execution.attempts.verification"],
    # ── substrate/execution/runtime/capability_router.py ────────────────
    # Capability (Enum) lists job capability names: CODE_WRITE, REASON, etc.
    # Capability (BaseModel) in substrate.types describes a capability instance.
    # Both are canonical — different concepts, same name.
    "Capability": [
        "substrate.execution.runtime.capability_router",
        "substrate.types",
    ],
    # ── substrate/execution/credential_gate.py ──────────────────────────
    # WP-P4-ADAPTERCALL-TOKEN-SEAM-001: fail-closed provider-token seam.
    # Names/paths only — token values never transit these types.
    "CredentialGateResult": ["substrate.execution.credential_gate"],
    "ProviderTokenRequirement": ["substrate.execution.credential_gate"],
    "AdapterCallCredentialDecision": ["substrate.execution.credential_gate"],
    "ProviderTokenUnavailableError": ["substrate.execution.credential_gate"],
    # ── substrate/execution/intent/ (P4S-31 MVP operating-loop skeleton) ─
    # New types: thin intent→proof loop records. IntentSpec was unregistered
    # and unused anywhere before this packet. WorkPacketDraft is the PRE-
    # governance draft, distinct from substrate.types.WorkPacket (the heavy
    # runtime packet) — it reuses WorkPacketStatus/Priority for its lifecycle.
    "IntentSpec": ["substrate.execution.intent.intent_spec"],
    "IntentKind": ["substrate.execution.intent.intent_spec"],
    "IntentLoopStage": ["substrate.execution.intent.intent_spec"],
    "WorkPacketDraft": ["substrate.execution.intent.intent_spec"],
    "IntentLoop": ["substrate.execution.intent.loop"],
    "IntentLoopRecord": ["substrate.execution.intent.loop"],
    "IntentLoopStore": ["substrate.execution.intent.loop"],
    "ProofRecord": ["substrate.execution.intent.loop"],
    # ── substrate/execution/runtime/worker_runtime_contracts.py ─────────
    "EnvironmentType": ["substrate.execution.runtime.worker_runtime_contracts"],
    "AuthorityDomain": ["substrate.execution.runtime.worker_runtime_contracts"],
    "MessageBusType": ["substrate.execution.runtime.worker_runtime_contracts"],
    # ── nodes/environments/work_packet.py ───────────────────────────────
    # WP-P2-001: names follow the real source symbols. A prior rename doubled
    # the "Environment" prefix in work_packet.py; the registry now matches the
    # actual class names so entries resolve (was EnvironmentPacket* — stale).
    "EnvironmentEnvironmentPacketStatus": ["nodes.environments.work_packet"],
    "EnvironmentEnvironmentPacketRiskLevel": ["nodes.environments.work_packet"],
    "EnvironmentEnvironmentPacketExecutionTarget": ["nodes.environments.work_packet"],
    "EnvironmentWorkPacket": ["nodes.environments.work_packet"],
    # ── substrate/templates/ (P4S-12: RealityTemplate metamodel) ─────────
    # The L2 ontology of provable patterns. Distinct from the runtime
    # executable-action-pattern store in substrate/organism/template_registry.py
    # (whose TemplateStatus/TemplateRegistry are a different concern and are NOT
    # registered here). These names are new to the codebase.
    "RealityTemplateStatus": ["substrate.templates.reality_template"],
    "TemplateInvariant": ["substrate.templates.reality_template"],
    "TemplateVariable": ["substrate.templates.reality_template"],
    "TemplateProofRequirement": ["substrate.templates.reality_template"],
    "RealityTemplate": ["substrate.templates.reality_template"],
    "TemplateInstance": ["substrate.templates.reality_template"],
    "TemplateEdge": ["substrate.templates.reality_template"],
    "TemplateGraph": ["substrate.templates.reality_template"],
    "CapabilityRevision": ["substrate.templates.reality_template"],
    "RealityTemplateRegistry": ["substrate.templates.registry"],
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
    # WP-P3-004: this is the organism STATE-BROADCAST port (OrganismStatePort +
    # ProjectionSubscriber), a DIFFERENT concern from the projection REGISTRATION
    # port in substrate.sockets.projection_port. Registered explicitly so the two
    # same-named files are unambiguous in the canonical registry.
    "StateSlice": ["substrate.organism.projection_port"],
    "OrganismStatePort": ["substrate.organism.projection_port"],
    "ProjectionSubscriber": ["substrate.organism.projection_port"],
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
    "ProfileExecutionMode": ["substrate.workstation.profile_behavior"],
    "ReportingCadence": ["substrate.workstation.profile_behavior"],
    "ActivationSource": ["substrate.workstation.activation", "substrate.organism.profile_runtime"],
    "ActivationSignal": ["substrate.workstation.activation"],
    "PresenceSession": ["substrate.workstation.activation"],
    "DeviceSession": ["substrate.workstation.device_presence"],
    "ContinuityCheckpoint": [
        "substrate.workstation.checkpoint",
        "substrate.operator.operator_presence",
    ],
    "CheckpointManager": ["substrate.workstation.checkpoint"],
    "ReturnBrief": ["substrate.workstation.resume_brief"],
    "ReturnBriefGenerator": ["substrate.workstation.resume_brief"],
    "IntentContract": ["substrate.workstation.intent_contract"],
    "IntentContractManager": ["substrate.workstation.intent_contract"],
    "IntentStatus": ["substrate.workstation.intent_contract"],
    "CompositeState": ["substrate.workstation.continuity_engine"],
    "ContinuityEngine": [
        "substrate.workstation.continuity_engine",
        "substrate.operator.continuity_engine",
    ],
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
    "RecommendationEngine": [
        "substrate.organism.strategic_gap_engine",
        "substrate.organism.workstation_runtime",
    ],
    "StrategicGapEngine": ["substrate.organism.strategic_gap_engine"],
    # Campaign 8: Goal Systems & Strategic Planning
    "GoalHierarchyEngine": ["substrate.organism.goal_hierarchy_engine"],
    "HierarchyValidation": ["substrate.organism.goal_hierarchy_engine"],
    "OutcomeProgress": ["substrate.organism.outcome_tracking_runtime"],
    "OutcomeSnapshot": ["substrate.organism.outcome_tracking_runtime"],
    "OutcomeTrackingRuntime": ["substrate.organism.outcome_tracking_runtime"],
    "PlanningStatus": ["substrate.organism.strategic_planning_engine"],
    "StrategicMilestone": ["substrate.organism.strategic_planning_engine"],
    "StrategicPlan": ["substrate.organism.strategic_planning_engine"],
    "StrategicPlanningEngine": ["substrate.organism.strategic_planning_engine"],
    "AlignmentReport": ["substrate.organism.goal_alignment_engine"],
    "GoalAlignmentEngine": ["substrate.organism.goal_alignment_engine"],
    "GoalDriftType": ["substrate.organism.goal_drift_engine"],
    "GoalDriftWarning": ["substrate.organism.goal_drift_engine"],
    "GoalDriftSnapshot": ["substrate.organism.goal_drift_engine"],
    "GoalDriftEngine": ["substrate.organism.goal_drift_engine"],
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
    # Campaign 7: Strategic Context & Executive Reasoning
    "StrategicHealth": ["substrate.organism.strategic_context_runtime"],
    "StrategicContext": ["substrate.organism.strategic_context_runtime"],
    "StrategicContextRuntime": ["substrate.organism.strategic_context_runtime"],
    "PrioritizedItem": ["substrate.organism.priority_engine"],
    "PriorityEngine": ["substrate.organism.priority_engine"],
    "RiskCategory": ["substrate.organism.risk_engine"],
    "UnifiedRisk": ["substrate.organism.risk_engine"],
    "RiskEngine": ["substrate.organism.risk_engine"],
    "UnifiedRecommendation": ["substrate.organism.recommendation_engine"],
    "DriftType": ["substrate.organism.drift_detection_engine"],
    "UnifiedDriftWarning": ["substrate.organism.drift_detection_engine"],
    "DriftDetectionEngine": ["substrate.organism.drift_detection_engine"],
    "ExecutiveBrief": ["substrate.organism.executive_brief_runtime"],
    "ExecutiveBriefRuntime": ["substrate.organism.executive_brief_runtime"],
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
    "SessionHandoff": [
        "substrate.organism.continuity_runtime",
        "substrate.organism.session_runtime",
    ],
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
    "PresenceSnapshot": [
        "substrate.organism.presence_runtime",
        "substrate.operator.operator_presence",
    ],
    "PresenceEvent": ["substrate.organism.presence_runtime"],
    "DeviceRegistry": ["substrate.organism.presence_runtime"],
    "SessionRegistry": [
        "substrate.organism.presence_runtime",
        "substrate.organism.session_runtime",
    ],
    "AttentionEngine": ["substrate.organism.presence_runtime"],
    "InterruptibilityEngine": ["substrate.organism.presence_runtime"],
    "PresenceTimeline": [
        "substrate.organism.presence_runtime",
        "substrate.operator.presence_timeline",
    ],
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
    "WorkspaceSnapshot": [
        "substrate.organism.workstation_runtime",
        "substrate.organism.meta_ide_runtime",
    ],
    "RestorationPlan": ["substrate.organism.workstation_runtime"],
    "WorkspaceSequence": ["substrate.organism.workstation_runtime"],
    "WorkstationProfile": ["substrate.organism.workstation_runtime"],
    "Workstation": ["substrate.organism.workstation_runtime"],
    "WorkstationRecommendation": ["substrate.organism.workstation_runtime"],
    "ModeClassifier": ["substrate.organism.workstation_runtime"],
    "WorkspaceTemplateRegistry": ["substrate.organism.workstation_runtime"],
    "WorkspaceContextAssembler": ["substrate.organism.workstation_runtime"],
    "SnapshotStore": ["substrate.organism.workstation_runtime"],
    "PreparationSequencer": ["substrate.organism.workstation_runtime"],
    "WorkstationRuntime": ["substrate.organism.workstation_runtime"],
    # Phase 11: Profile Runtime
    "ProfileModeEnum": ["substrate.organism.profile_runtime"],
    "SystemModeEnum": ["substrate.organism.profile_runtime"],
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
    "DevSessionStatus": ["substrate.organism.dev_session_tracker"],
    "ReconciliationStatus": ["substrate.organism.reconciliation_session"],
    "OperatorSessionStatus": ["substrate.organism.operator_session"],
    "VoiceSessionStatus": ["substrate.execution.voice.session"],
    "SessionAuthority": ["substrate.organism.session_runtime"],
    "SessionEventType": ["substrate.organism.session_runtime"],
    "HandoffStatus": ["substrate.organism.session_runtime"],
    "Session": ["substrate.organism.session_runtime"],
    "SessionEvent": ["substrate.organism.session_runtime"],
    "SessionContinuityLink": ["substrate.organism.session_runtime"],
    "SessionRuntimeSnapshot": ["substrate.organism.session_runtime"],
    "SessionLifecycleEngine": ["substrate.organism.session_runtime"],
    "SessionHandoffRuntime": ["substrate.organism.session_runtime"],
    "SessionContinuityGraph": ["substrate.organism.session_runtime"],
    "SessionTimeline": ["substrate.organism.session_runtime"],
    "SessionRuntime": ["substrate.organism.session_runtime"],
    # Phase 13: Execution Coordinator Runtime
    "ExecutionPlanStatus": ["substrate.organism.execution_coordinator"],
    "ExecutionTargetType": ["substrate.organism.execution_coordinator"],
    "ExecutionTiming": ["substrate.organism.execution_coordinator"],
    "ExecutionMode": ["substrate.organism.execution_modes"],
    "CommandExecutionMode": ["substrate.composition.registries.canonical_command_registry_v1"],
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
    # Phase 17B: Canonical Memory Write Path
    "MemoryWriteReceipt": ["substrate.memory.canonical_write"],
    "CanonicalWritePath": ["substrate.memory.canonical_write"],
    # Phase 17C: Organism Loop Engine
    "OrganismLoopResult": ["substrate.organism.organism_loop"],
    "OrganismLoopEngine": ["substrate.organism.organism_loop"],
    # Phase 18: Operator Convergence
    "RouteType": ["substrate.operator.intent_router"],
    "RouteClassification": ["substrate.operator.intent_router"],
    "IntentRouter": ["substrate.operator.intent_router"],
    "ReceiptStatus": ["substrate.operator.intent_receipt"],
    "IntentReceipt": ["substrate.operator.intent_receipt"],
    "IntentReceiptStore": ["substrate.operator.intent_receipt"],
    # Phase 19: Reality Canonicalization
    "MutationSource": ["substrate.reality_model.reality_mutation"],
    "MutationType": ["substrate.reality_model.reality_mutation"],
    "RealityMutation": ["substrate.reality_model.reality_mutation"],
    "RealityMutationReceipt": ["substrate.reality_model.reality_mutation"],
    "CanonicalRealityWritePath": ["substrate.reality_model.canonical_reality_write"],
    # Phase 20: Reality Intelligence
    "RealityQueryType": ["substrate.reality_model.reality_query"],
    "RealityQuery": ["substrate.reality_model.reality_query"],
    "RealityEvidence": ["substrate.reality_model.reality_query"],
    "RealityQueryResult": ["substrate.reality_model.reality_query"],
    "RealityIntelligenceEngine": ["substrate.reality_model.reality_intelligence"],
    # Phase 21: Meta IDE Convergence
    "RepositoryHealthStatus": ["substrate.meta_ide.repository_model"],
    "BranchSnapshot": ["substrate.meta_ide.repository_model"],
    "WorktreeSnapshot": ["substrate.meta_ide.repository_model"],
    "RepositoryHealth": ["substrate.meta_ide.repository_model"],
    "RepositorySnapshot": [
        "substrate.meta_ide.repository_model",
        "substrate.organism.repository_awareness_runtime",
    ],
    "RepositoryReader": ["substrate.meta_ide.repository_model"],
    "MetaIDEWorkspaceEngine": ["substrate.meta_ide.workspace_intelligence"],
    "EngineeringRisk": ["substrate.meta_ide.workspace_intelligence"],
    "WorkspaceSummary": ["substrate.meta_ide.workspace_intelligence"],
    "PhaseState": ["substrate.meta_ide.roadmap_intelligence"],
    "PhaseStatus": ["substrate.meta_ide.roadmap_intelligence"],
    "RoadmapStatus": ["substrate.meta_ide.roadmap_intelligence"],
    "RoadmapIntelligence": ["substrate.meta_ide.roadmap_intelligence"],
    # Phase 22: Autonomous Engineering Loop
    "EngineeringIntentType": ["substrate.meta_ide.engineering_intent"],
    "EngineeringIntent": ["substrate.meta_ide.engineering_intent"],
    "EngineeringTask": ["substrate.meta_ide.engineering_intent"],
    "EngineeringPlan": ["substrate.meta_ide.engineering_intent"],
    "EngineeringPlanReceipt": ["substrate.meta_ide.engineering_intent"],
    "EngineeringPlanner": ["substrate.meta_ide.engineering_planner"],
    "EngineeringWorkGenerator": ["substrate.meta_ide.engineering_work_generator"],
    "RoadmapGapEngine": ["substrate.meta_ide.roadmap_gap_engine"],
    "GapAnalysis": ["substrate.meta_ide.roadmap_gap_engine"],
    "RoadmapGap": ["substrate.meta_ide.roadmap_gap_engine"],
    "GapRecommendation": ["substrate.meta_ide.roadmap_gap_engine"],
    # Phase 23: Engineering Proof Loop
    "EngineeringExecutionStatus": ["substrate.meta_ide.engineering_execution"],
    "EngineeringArtifactType": ["substrate.meta_ide.engineering_execution"],
    "OperatorRecommendation": ["substrate.meta_ide.engineering_execution"],
    "EngineeringExecutionSession": ["substrate.meta_ide.engineering_execution"],
    "EngineeringArtifact": ["substrate.meta_ide.engineering_execution"],
    "EngineeringProofPackage": ["substrate.meta_ide.engineering_execution"],
    "EngineeringSessionCoordinator": ["substrate.meta_ide.engineering_session_coordinator"],
    "ReviewPackageBuilder": ["substrate.meta_ide.review_package_builder"],
    # Browser Verification Gate
    "LogCrossReference": ["substrate.meta_ide.browser_verification_gate"],
    "LogLayerResult": ["substrate.meta_ide.browser_verification_gate"],
    "BrowserLayerResult": ["substrate.meta_ide.browser_verification_gate"],
    "NetworkLayerResult": ["substrate.meta_ide.browser_verification_gate"],
    "ConsoleLayerResult": ["substrate.meta_ide.browser_verification_gate"],
    "VerificationPass": ["substrate.meta_ide.browser_verification_gate"],
    "BrowserVerificationResult": ["substrate.meta_ide.browser_verification_gate"],
    "BrowserVerificationGate": ["substrate.meta_ide.browser_verification_gate"],
    # Phase 24: Distributed Worker Runtime
    "WorkerStatus": ["substrate.organism.worker_registry"],
    "WorkerInstance": ["substrate.organism.worker_registry"],
    "DeviceCapacity": ["substrate.organism.device_capacity"],
    "PacketPlacement": ["substrate.organism.packet_router"],
    "WorkerEventType": ["substrate.organism.worker_lifecycle"],
    # Phase 25: Workspace Observation
    "ObservationDomain": ["substrate.meta_ide.workspace_observation"],
    "ProcessHealth": ["substrate.meta_ide.workspace_observation"],
    "TerminalObservation": ["substrate.meta_ide.workspace_observation"],
    "ContainerObservation": ["substrate.meta_ide.workspace_observation"],
    "PreviewObservation": ["substrate.meta_ide.workspace_observation"],
    "EngineeringSessionObservation": ["substrate.meta_ide.workspace_observation"],
    "WorkspaceObservationSnapshot": ["substrate.meta_ide.workspace_observation"],
    # Phase 26: Governed Action Bridge
    "ActionRiskLevel": ["substrate.organism.action_catalog"],
    "ActionCategory": ["substrate.organism.action_catalog"],
    "ActionStatus": ["substrate.organism.action_catalog"],
    "ActionDefinition": ["substrate.organism.action_catalog"],
    "ActionParameter": ["substrate.organism.action_catalog"],
    "ActionPrecondition": ["substrate.organism.action_catalog"],
    "ActionRequest": ["substrate.organism.action_bridge"],
    "ActionResult": ["substrate.organism.action_bridge"],
    "IntentActionRequest": ["substrate.organism.action_voice_contract"],
    # Phase 27: Workspace Runtime Graph
    "WorkspaceType": ["substrate.meta_ide.workspace_runtime_graph"],
    "RuntimeTargetType": ["substrate.meta_ide.workspace_runtime_graph"],
    "BuildTargetType": ["substrate.meta_ide.workspace_runtime_graph"],
    "WorkspaceHealth": ["substrate.meta_ide.workspace_runtime_graph"],
    "WorkspaceRepository": ["substrate.meta_ide.workspace_runtime_graph"],
    "WorkspaceRuntime": ["substrate.meta_ide.workspace_runtime_graph"],
    "WorkspaceBuildTarget": ["substrate.meta_ide.workspace_runtime_graph"],
    "WorkspaceDefinition": ["substrate.meta_ide.workspace_runtime_graph"],
    "WorkspaceRuntimeGraph": ["substrate.meta_ide.workspace_runtime_graph"],
    # Phase 28: UMH Node Role & Version Topology
    "UMHNodeRole": ["substrate.organism.umh_node_topology"],
    "UMHNodeStatus": ["substrate.organism.umh_node_topology"],
    "UMHServiceRole": ["substrate.organism.umh_node_topology"],
    "UMHVersionStatus": ["substrate.organism.umh_node_topology"],
    "UMHVersionInfo": ["substrate.organism.umh_node_topology"],
    "UMHServiceActivation": ["substrate.organism.umh_node_topology"],
    "UMHNodeRecord": ["substrate.organism.umh_node_topology"],
    "UMHNodeTopology": ["substrate.organism.umh_node_topology"],
    "UMHNodeRegistry": ["substrate.organism.umh_node_registry"],
    "UMHVersionCoherenceEngine": ["substrate.organism.umh_version_coherence"],
    # W1: Unified Compute Fabric
    "ComputeNodeType": ["substrate.organism.compute_fabric_runtime"],
    "ComputeNodeHealth": ["substrate.organism.compute_fabric_runtime"],
    "ComputeNode": ["substrate.organism.compute_fabric_runtime"],
    "RoutingDecision": ["substrate.organism.compute_fabric_runtime"],
    "ComputeFabricRuntime": ["substrate.organism.compute_fabric_runtime"],
    # W3: Agent Fleet Runtime
    "FleetDispatchStatus": ["substrate.organism.agent_fleet_runtime"],
    "AssignmentRationale": ["substrate.organism.agent_fleet_runtime"],
    "FleetAssignment": ["substrate.organism.agent_fleet_runtime"],
    "FleetDispatch": ["substrate.organism.agent_fleet_runtime"],
    "FleetDispatchResult": ["substrate.organism.agent_fleet_runtime"],
    "FleetSnapshot": ["substrate.organism.agent_fleet_runtime"],
    "FleetHealth": ["substrate.organism.agent_fleet_runtime"],
    "WaveResult": ["substrate.organism.agent_fleet_runtime"],
    "AgentFleetRuntime": ["substrate.organism.agent_fleet_runtime"],
    # W2: Meta IDE Runtime
    "ReviewStatus": ["substrate.organism.meta_ide_runtime"],
    "DevelopmentPhase": ["substrate.organism.meta_ide_runtime"],
    "IDEPlan": ["substrate.organism.meta_ide_runtime"],
    "DevelopmentStream": ["substrate.organism.meta_ide_runtime"],
    "ReviewDetail": ["substrate.organism.meta_ide_runtime"],
    "MergeResult": ["substrate.organism.meta_ide_runtime"],
    "IDEStatusSnapshot": ["substrate.organism.meta_ide_runtime"],
    "MetaIDERuntime": ["substrate.organism.meta_ide_runtime"],
    # W4: Embodiment Runtime
    "IntentType": ["substrate.organism.embodiment_runtime"],
    "IntentClassification": ["substrate.organism.embodiment_runtime"],
    "EmbodimentContext": ["substrate.organism.embodiment_runtime"],
    "EmbodimentResponse": ["substrate.organism.embodiment_runtime"],
    "ProcessedIntent": ["substrate.organism.embodiment_runtime"],
    "RoutingAccuracyReport": ["substrate.organism.embodiment_runtime"],
    "EmbodimentRuntime": ["substrate.organism.embodiment_runtime"],
    # W5: Operator Migration Runtime
    "ExitReason": ["substrate.organism.operator_migration_runtime"],
    "MigrationStatus": ["substrate.organism.operator_migration_runtime"],
    "ExitEvent": ["substrate.organism.operator_migration_runtime"],
    "ExitClassification": ["substrate.organism.operator_migration_runtime"],
    "MigrationPriority": ["substrate.organism.operator_migration_runtime"],
    "CoverageReport": ["substrate.organism.operator_migration_runtime"],
    "OperationalizationSuggestion": ["substrate.organism.operator_migration_runtime"],
    "Migration": ["substrate.organism.operator_migration_runtime"],
    "MigrationStatusSnapshot": ["substrate.organism.operator_migration_runtime"],
    "OperatorMigrationRuntime": ["substrate.organism.operator_migration_runtime"],
    # Phase 29: State Authority Graph
    "StateDomain": ["substrate.organism.state_authority_graph"],
    "StateAuthorityLevel": ["substrate.organism.state_authority_graph"],
    "StateCoherenceStatus": ["substrate.organism.state_authority_graph"],
    "StateAuthority": ["substrate.organism.state_authority_graph"],
    "StateDomainStatus": ["substrate.organism.state_authority_graph"],
    "OrganismStateGraph": ["substrate.organism.state_authority_graph"],
    "StateRegistry": ["substrate.organism.state_registry"],
    "StateCoherenceEngine": ["substrate.organism.state_coherence_engine"],
    # Phase 30: Service Dependency Graph
    "DependencyStrength": ["substrate.organism.service_dependency_graph"],
    "ServiceCriticality": ["substrate.organism.service_dependency_graph"],
    "ServiceHealthImpact": ["substrate.organism.service_dependency_graph"],
    "ServiceDependency": ["substrate.organism.service_dependency_graph"],
    "ServiceNode": ["substrate.organism.service_dependency_graph"],
    "FailureImpact": ["substrate.organism.service_dependency_graph"],
    "ServiceDependencyTopology": ["substrate.organism.service_dependency_graph"],
    "ServiceDependencyRegistry": ["substrate.organism.service_dependency_registry"],
    "ServiceFailureEngine": ["substrate.organism.service_failure_engine"],
    # Phase 31: Operator Home & Context Engine
    "OperatorSeverity": ["substrate.operator.operator_context"],
    "OperatorAttentionType": ["substrate.operator.operator_context"],
    "OperatorAttentionItem": ["substrate.operator.operator_context"],
    "OperatorStatusCard": ["substrate.operator.operator_context"],
    "OperatorHealthSummary": ["substrate.operator.operator_context"],
    "OperatorTimelineEvent": ["substrate.operator.operator_context"],
    "OperatorSnapshot": ["substrate.operator.operator_context"],
    "OperatorContextEngine": ["substrate.operator.operator_context_engine"],
    # Phase 32: Presence & Continuity Runtime
    "PresenceState": ["substrate.operator.operator_presence"],
    "PresenceDeviceType": ["substrate.operator.operator_presence"],
    "ContinuityStatus": ["substrate.operator.operator_presence"],
    "OperatorPresence": ["substrate.operator.operator_presence"],
    "ActiveContext": ["substrate.operator.operator_presence"],
    "PresenceTransition": ["substrate.operator.presence_timeline"],
    "DevicePresenceState": ["substrate.operator.device_continuity"],
    "DeviceContinuityTracker": ["substrate.operator.device_continuity"],
    # Phase 33: Screen Awareness Runtime
    "ScreenSourceType": ["substrate.operator.screen_awareness"],
    "ScreenContextStatus": ["substrate.operator.screen_awareness"],
    "ApplicationCategory": ["substrate.operator.screen_awareness"],
    "FocusedApplication": ["substrate.operator.screen_awareness"],
    "ActiveWindow": ["substrate.operator.screen_awareness"],
    "RepositoryContext": ["substrate.operator.screen_awareness"],
    "FileContext": ["substrate.operator.screen_awareness"],
    "BrowserContext": ["substrate.operator.screen_awareness"],
    "ScreenSnapshot": ["substrate.operator.screen_awareness"],
    "ScreenContextProvider": ["substrate.operator.screen_context_providers"],
    "InferredScreenContextProvider": ["substrate.operator.screen_context_providers"],
    "ObservedScreenContextProvider": ["substrate.operator.screen_context_providers"],
    "ReportedScreenContextProvider": ["substrate.operator.screen_context_providers"],
    "ScreenObservationEngine": ["substrate.operator.screen_observation_engine"],
    "RepositoryContextResolver": ["substrate.operator.repository_context_resolver"],
    # Phase 34: Workstation Observation Runtime
    "WorkstationTranslator": ["substrate.operator.workstation_translator"],
    # Phase 35: Voice Query Engine
    "QueryDomain": ["substrate.operator.voice_query_engine"],
    "QueryResolution": ["substrate.operator.voice_query_engine"],
    "VoiceQueryEngine": ["substrate.operator.voice_query_engine"],
    "ActionResolution": ["substrate.operator.voice_query_engine"],
    # ── Voice Session & Wake Producer (pre-C20) ─────────────────────
    # P4S31 Voice Convergence: the record store + turn types now live in the
    # canonical home substrate.execution.voice.store; the runtime VoiceSession
    # (operational, audio-bearing) is substrate.execution.voice.session. The old
    # bridge names are re-exported from bridge/voice_session.py for compat.
    "VoiceErrorCode": ["substrate.execution.voice.error_codes"],
    "VoiceTurnSource": ["substrate.execution.voice.store"],
    "VoiceTurn": ["substrate.execution.voice.store"],
    "VoiceSessionRecord": ["substrate.execution.voice.store"],
    "VoiceSessionRecordStatus": ["substrate.execution.voice.store"],
    "VoiceSessionStore": ["substrate.execution.voice.store"],
    "VoiceSessionRuntime": ["substrate.execution.bridge.voice_session"],
    "WakeProducerKind": ["substrate.execution.bridge.wake_producer"],
    "WakeProducerEvent": ["substrate.execution.bridge.wake_producer"],
    "WakeProducerHistory": ["substrate.execution.bridge.wake_producer"],
    "WakeProducerRuntime": ["substrate.execution.bridge.wake_producer"],
    "VoiceRoute": ["substrate.workstation.voice_route_resolver"],
    # Gate 3: Governed Work Runtime
    "WorkNodeType": ["substrate.organism.work_graph"],
    "BlockerType": ["substrate.organism.work_graph"],
    "WorkBlocker": ["substrate.organism.work_graph"],
    "WorkResult": ["substrate.organism.work_graph"],
    "WorkGraphNode": ["substrate.organism.work_graph"],
    "WorkGraphSnapshot": ["substrate.organism.work_graph"],
    "WorkGraph": ["substrate.organism.work_graph"],
    "ApprovalScope": ["substrate.organism.executors.approval_intercept"],
    "ApprovalPolicy": ["substrate.organism.executors.approval_intercept"],
    "ApprovalDecision": ["substrate.organism.executors.approval_intercept"],
    "ApprovalPolicyRegistry": ["substrate.organism.executors.approval_intercept"],
    "ProofEvidence": ["substrate.organism.proof_runtime"],
    "ProofPackage": ["substrate.organism.proof_runtime"],
    "ProofRuntime": ["substrate.organism.proof_runtime"],
    "RecoveryState": ["substrate.organism.work_recovery_runtime"],
    "RecoveryActionType": ["substrate.organism.work_recovery_runtime"],
    "RecoveryAction": ["substrate.organism.work_recovery_runtime"],
    "RecoveryAssessment": ["substrate.organism.work_recovery_runtime"],
    "WorkRecoveryRuntime": ["substrate.organism.work_recovery_runtime"],
    "WorkSubmission": ["substrate.organism.governed_work_runtime"],
    "ExecutionReceipt": ["substrate.organism.governed_work_runtime"],
    "WorkStatus": ["substrate.organism.governed_work_runtime"],
    "GovernedWorkRuntime": ["substrate.organism.governed_work_runtime"],
    "OperatorLoopPhase": ["substrate.organism.operator_loop_runtime"],
    "OperatorLoopState": ["substrate.organism.operator_loop_runtime"],
    "OperatorLoopRuntime": ["substrate.organism.operator_loop_runtime"],
    # Gate 4 — Intent Runtime (Workstation Convergence)
    "IntentScope": ["substrate.operator.intent_runtime"],
    "CanonicalIntentStatus": ["substrate.operator.intent_runtime"],
    "ConflictType": ["substrate.operator.intent_runtime"],
    "CanonicalIntent": ["substrate.operator.intent_runtime"],
    "IntentConflict": ["substrate.operator.intent_runtime"],
    "IntentRuntime": ["substrate.operator.intent_runtime"],
    # Gate 4 — Operator Snapshot Runtime
    "SituationSnapshot": ["substrate.operator.operator_snapshot_runtime"],
    "ChangeEntry": ["substrate.operator.operator_snapshot_runtime"],
    "DecisionItem": ["substrate.operator.operator_snapshot_runtime"],
    "OperatorNextAction": ["substrate.operator.operator_snapshot_runtime"],
    "NextAction": ["substrate.organism.next_action_engine"],
    "OperatorQuestionSnapshot": ["substrate.operator.operator_snapshot_runtime"],
    "OperatorSnapshotRuntime": ["substrate.operator.operator_snapshot_runtime"],
    # Gate 4 — Operator Attention Engine
    "AttentionItem": ["substrate.operator.operator_attention_engine"],
    "OperatorAttentionEngine": ["substrate.operator.operator_attention_engine"],
    # Gate 5 — Capability Runtime
    "CapabilityMaturity": ["substrate.organism.capability_runtime"],
    "CapabilityEvidenceType": ["substrate.organism.capability_runtime"],
    "CapabilityEvidence": ["substrate.organism.capability_runtime"],
    "EmergentCapability": ["substrate.organism.capability_runtime"],
    "CapabilityRuntime": ["substrate.organism.capability_runtime"],
    # Campaign 10 — Capability Intelligence
    "CapabilityRelationType": ["substrate.organism.capability_graph_engine"],
    "CapabilityEdge": ["substrate.organism.capability_graph_engine"],
    "CapabilityGraphEngine": ["substrate.organism.capability_graph_engine"],
    "CapabilityGapSeverity": ["substrate.organism.capability_gap_engine"],
    "CapabilityGap": ["substrate.organism.capability_gap_engine"],
    "CapabilityGapEngine": ["substrate.organism.capability_gap_engine"],
    "PortfolioHealth": ["substrate.organism.capability_portfolio_runtime"],
    "CapabilityPortfolioSnapshot": ["substrate.organism.capability_portfolio_runtime"],
    "CapabilityPortfolioRuntime": ["substrate.organism.capability_portfolio_runtime"],
    # Gate 6 — Operationalization Runtime
    "OperationalizationForm": ["substrate.organism.operationalization_runtime"],
    "OperationalizationStatus": ["substrate.organism.operationalization_runtime"],
    "Operationalization": ["substrate.organism.operationalization_runtime"],
    "OperationalizationRuntime": ["substrate.organism.operationalization_runtime"],
    # Gate 8 — Execution Graph
    "ExecutionNodeType": ["substrate.organism.execution_graph"],
    "LineageGap": ["substrate.organism.execution_graph"],
    "ExecutionGraphNode": ["substrate.organism.execution_graph"],
    "ExecutionGraph": ["substrate.organism.execution_graph"],
    # Gate 7 — Infrastructure Runtime
    "InfrastructureType": ["substrate.organism.infrastructure_runtime"],
    "InfrastructureHealth": ["substrate.organism.infrastructure_runtime"],
    "InfrastructureEntity": ["substrate.organism.infrastructure_runtime"],
    "InfrastructureRuntime": ["substrate.organism.infrastructure_runtime"],
    # Gate 9 — Compounding Engine
    "PromotionType": ["substrate.organism.compounding_engine"],
    "PromotionStatus": ["substrate.organism.compounding_engine"],
    "PromotionCandidate": ["substrate.organism.compounding_engine"],
    "CompoundingEngine": ["substrate.organism.compounding_engine"],
    # Gate 10 — Projection Consumption Layer
    "ProjectionRegistration": ["substrate.sockets.projection_port"],
    "ProjectionPortProtocol": ["substrate.sockets.projection_port"],
    "ProjectionPort": ["substrate.sockets.projection_port"],
    # Campaign 3.1 — Cockpit Capability Map
    "SurfaceCategory": ["substrate.workstation.cockpit_capability_map"],
    "MVPStatus": ["substrate.workstation.cockpit_capability_map"],
    "CoverageStatus": ["substrate.workstation.cockpit_capability_map"],
    "CockpitSurface": ["substrate.workstation.cockpit_capability_map"],
    "DuplicationFinding": ["substrate.workstation.cockpit_capability_map"],
    "CockpitCapabilitySnapshot": ["substrate.workstation.cockpit_capability_map"],
    "CockpitCapabilityMap": ["substrate.workstation.cockpit_capability_map"],
    # Campaign 3.2 — Command Center MVP Convergence
    "CommandCenterSection": ["substrate.workstation.command_center_mvp_runtime"],
    "ExecutionPulse": ["substrate.workstation.command_center_mvp_runtime"],
    "CapabilityPulse": ["substrate.workstation.command_center_mvp_runtime"],
    "MigrationPulse": ["substrate.workstation.command_center_mvp_runtime"],
    "CommandCenterRecommendation": ["substrate.workstation.command_center_mvp_runtime"],
    "CommandCenterSnapshot": ["substrate.workstation.command_center_mvp_runtime"],
    "CommandCenterMVPRuntime": ["substrate.workstation.command_center_mvp_runtime"],
    # Campaign 3.3 — Unified Execution Surface
    "ExecutionStreamType": ["substrate.workstation.unified_execution_surface_runtime"],
    "ExecutionStreamStatus": ["substrate.workstation.unified_execution_surface_runtime"],
    "UnifiedExecutionStream": ["substrate.workstation.unified_execution_surface_runtime"],
    "UnifiedApprovalItem": ["substrate.workstation.unified_execution_surface_runtime"],
    "UnifiedExecutionSurfaceRuntime": ["substrate.workstation.unified_execution_surface_runtime"],
    # Campaign 3.4 — Meta IDE Build Loop
    "BuildLoopPhase": ["substrate.workstation.meta_ide_projection_loop_runtime"],
    "BuildRequest": ["substrate.workstation.meta_ide_projection_loop_runtime"],
    "BuildLoopStatus": ["substrate.workstation.meta_ide_projection_loop_runtime"],
    "MetaIDEProjectionLoopRuntime": ["substrate.workstation.meta_ide_projection_loop_runtime"],
    # Campaign 3.5 — Projection Integration Runtime
    "ProjectionMachineType": ["substrate.organism.projection_integration_runtime"],
    "ProjectionAvailability": ["substrate.organism.projection_integration_runtime"],
    "ProjectionMaturityLevel": ["substrate.organism.projection_integration_runtime"],
    "IntegrationGapType": ["substrate.organism.projection_integration_runtime"],
    "ProjectionCodeLocation": ["substrate.organism.projection_integration_runtime"],
    "ProjectionIntegrationProfile": ["substrate.organism.projection_integration_runtime"],
    "ProjectionIntegrationGap": ["substrate.organism.projection_integration_runtime"],
    "ProjectionBuildReadiness": ["substrate.organism.projection_integration_runtime"],
    "ProjectionIntegrationSnapshot": ["substrate.organism.projection_integration_runtime"],
    "ProjectionIntegrationRuntime": ["substrate.organism.projection_integration_runtime"],
    # Campaign 4.0 — Orchestrator Awareness Runtime
    "AwarenessDomain": ["substrate.organism.orchestrator_awareness_runtime"],
    "OrchestratorContext": ["substrate.organism.orchestrator_awareness_runtime"],
    "DomainAwareness": ["substrate.organism.orchestrator_awareness_runtime"],
    "OrchestratorAwarenessSnapshot": ["substrate.organism.orchestrator_awareness_runtime"],
    "OrchestratorAwarenessRuntime": ["substrate.organism.orchestrator_awareness_runtime"],
    # Campaign 4.1 — Operating Loop Runtime
    "OperatingLoopStage": ["substrate.workstation.operating_loop_runtime"],
    "OperatingLoopTransition": ["substrate.workstation.operating_loop_runtime"],
    "OperatingLoop": ["substrate.workstation.operating_loop_runtime"],
    "OperatingLoopSnapshot": ["substrate.workstation.operating_loop_runtime"],
    "OperatingLoopRuntime": ["substrate.workstation.operating_loop_runtime"],
    # Campaign 4.2 — Unified Approval Runtime
    "ApprovalSourceType": ["substrate.workstation.unified_approval_runtime"],
    "UnifiedApproval": ["substrate.workstation.unified_approval_runtime"],
    "ApprovalAction": ["substrate.workstation.unified_approval_runtime"],
    "UnifiedApprovalSnapshot": ["substrate.workstation.unified_approval_runtime"],
    "UnifiedApprovalRuntime": ["substrate.workstation.unified_approval_runtime"],
    # Campaign 4.3 — Operating Loop Coherence Runtime
    "LoopCoherenceStatus": ["substrate.organism.operating_loop_coherence_runtime"],
    "LoopCoherenceIssueType": ["substrate.organism.operating_loop_coherence_runtime"],
    "LoopCoherenceIssue": ["substrate.organism.operating_loop_coherence_runtime"],
    "LoopCoherenceReport": ["substrate.organism.operating_loop_coherence_runtime"],
    "OperatingLoopCoherenceRuntime": ["substrate.organism.operating_loop_coherence_runtime"],
    # Campaign 4.4 — Workstation Session Runtime
    "WorkstationSessionStatus": ["substrate.operator.workstation_session_runtime"],
    "WorkstationSessionCheckpoint": ["substrate.operator.workstation_session_runtime"],
    "WorkstationSessionResume": ["substrate.operator.workstation_session_runtime"],
    "WorkstationSession": ["substrate.operator.workstation_session_runtime"],
    "WorkstationSessionRuntime": ["substrate.operator.workstation_session_runtime"],
    # Campaign 4.5 — MVP Readiness Runtime
    "MVPDimensionStatus": ["substrate.workstation.mvp_readiness_runtime"],
    "MVPDimension": ["substrate.workstation.mvp_readiness_runtime"],
    "MVPEscapePoint": ["substrate.workstation.mvp_readiness_runtime"],
    "MVPReadinessReport": ["substrate.workstation.mvp_readiness_runtime"],
    "MVPReadinessRuntime": ["substrate.workstation.mvp_readiness_runtime"],
    # Campaign 4.7 — Delegation Runtime
    "OperatorIntentType": ["substrate.organism.delegation_runtime"],
    "DelegationMissionStatus": ["substrate.organism.delegation_runtime"],
    "DelegationMission": ["substrate.organism.delegation_runtime"],
    "DelegationProposal": ["substrate.organism.delegation_runtime"],
    "NestedOrchestratorState": ["substrate.organism.delegation_runtime"],
    # Campaign 5.0 — Reality Graph
    "RealityEntityType": ["substrate.organism.reality_graph"],
    "RealityRelationType": ["substrate.organism.reality_graph"],
    "RealityEntityStatus": ["substrate.organism.reality_graph"],
    "RealityEntity": ["substrate.organism.reality_graph"],
    "RealityRelation": ["substrate.organism.reality_graph"],
    "RealityGraph": ["substrate.organism.reality_graph"],
    # Campaign 5.2 — Project Registry
    "ProjectDefinition": ["substrate.organism.project_registry"],
    "ProjectRegistry": ["substrate.organism.project_registry"],
    # Campaign 5.5 — Context Resolution
    "ResolutionStrategy": ["substrate.organism.context_resolution"],
    "ResolvedContext": ["substrate.organism.context_resolution"],
    "ContextResolutionEngine": ["substrate.organism.context_resolution"],
    # Campaign 6.0 — Artifact Registry
    "ArtifactType": ["substrate.organism.artifact_registry"],
    "ArtifactStatus": ["substrate.organism.artifact_registry"],
    "ArtifactEntry": ["substrate.organism.artifact_registry"],
    "ArtifactRegistry": ["substrate.organism.artifact_registry"],
    # Campaign 6.1 — Repository Awareness
    "FileCategory": ["substrate.organism.repository_awareness_runtime"],
    "FileEntry": ["substrate.organism.repository_awareness_runtime"],
    "RepositoryAwarenessRuntime": ["substrate.organism.repository_awareness_runtime"],
    # Campaign 6.2 — Documentation Awareness
    "DocumentStatus": ["substrate.organism.documentation_awareness_runtime"],
    "DocumentEntry": ["substrate.organism.documentation_awareness_runtime"],
    "DocumentationSnapshot": ["substrate.organism.documentation_awareness_runtime"],
    "DocumentationAwarenessRuntime": ["substrate.organism.documentation_awareness_runtime"],
    # Campaign 6.3 — Runtime Awareness
    "RuntimeAwarenessSnapshot": ["substrate.organism.runtime_awareness_runtime"],
    "RuntimeAwarenessRuntime": ["substrate.organism.runtime_awareness_runtime"],
    # Campaign 6.4 — Knowledge Awareness
    "KnowledgeType": ["substrate.organism.knowledge_awareness_runtime"],
    "KnowledgeEntry": ["substrate.organism.knowledge_awareness_runtime"],
    "KnowledgeSnapshot": ["substrate.organism.knowledge_awareness_runtime"],
    "KnowledgeAwarenessRuntime": ["substrate.organism.knowledge_awareness_runtime"],
    # Campaign 9 — Decision Intelligence & Strategic Memory
    # C9.0 — Decision Registry
    "DecisionStatus": ["substrate.organism.decision_registry"],
    "StrategicDecision": ["substrate.organism.decision_registry"],
    "DecisionRegistry": ["substrate.organism.decision_registry"],
    # C9.1 — Decision Lineage
    "LineageNode": ["substrate.organism.decision_lineage_engine"],
    "DecisionLineage": ["substrate.organism.decision_lineage_engine"],
    "DecisionLineageEngine": ["substrate.organism.decision_lineage_engine"],
    # C9.2 — Assumption Tracking
    "AssumptionStatus": ["substrate.organism.assumption_tracking_runtime"],
    "AssumptionRecord": ["substrate.organism.assumption_tracking_runtime"],
    "AssumptionTrackingRuntime": ["substrate.organism.assumption_tracking_runtime"],
    # C9.3 — Decision Validity
    "ValidityStatus": ["substrate.organism.decision_validity_engine"],
    "DecisionValidity": ["substrate.organism.decision_validity_engine"],
    "DecisionValidityEngine": ["substrate.organism.decision_validity_engine"],
    # C9.4 — Strategic Memory
    "MemorySnapshot": ["substrate.organism.strategic_memory_engine"],
    "StrategicMemory": ["substrate.organism.strategic_memory_engine"],
    "StrategicMemoryEngine": ["substrate.organism.strategic_memory_engine"],
    # C9.5 — Decision Impact
    "DecisionImpact": ["substrate.organism.decision_impact_engine"],
    "DecisionImpactEngine": ["substrate.organism.decision_impact_engine"],
    # Campaign 11 — Work Intelligence & Execution Readiness
    # C11.0 — Work Readiness Runtime
    "ReadinessStatus": ["substrate.organism.work_readiness_runtime"],
    "ReadinessAssessment": ["substrate.organism.work_readiness_runtime"],
    "WorkReadinessSnapshot": ["substrate.organism.work_readiness_runtime"],
    "WorkReadinessRuntime": ["substrate.organism.work_readiness_runtime"],
    # C11.1 — Delegation Readiness Runtime
    "DelegationReadiness": ["substrate.organism.delegation_readiness_runtime"],
    "DelegationReadinessSnapshot": ["substrate.organism.delegation_readiness_runtime"],
    "DelegationReadinessRuntime": ["substrate.organism.delegation_readiness_runtime"],
    # C11.2 — Work Portfolio Runtime
    "WorkPortfolioHealth": ["substrate.organism.work_portfolio_runtime"],
    "WorkDriftType": ["substrate.organism.work_portfolio_runtime"],
    "WorkDriftWarning": ["substrate.organism.work_portfolio_runtime"],
    "WorkPortfolioSnapshot": ["substrate.organism.work_portfolio_runtime"],
    "WorkPortfolioRuntime": ["substrate.organism.work_portfolio_runtime"],
    # ── Campaign 12: Learning Intelligence ────────────────────────────
    "LessonCategory": ["substrate.organism.learning_extraction_runtime"],
    "ExtractedLesson": ["substrate.organism.learning_extraction_runtime"],
    "LessonExtractionSnapshot": ["substrate.organism.learning_extraction_runtime"],
    "LearningExtractionRuntime": ["substrate.organism.learning_extraction_runtime"],
    "PatternType": ["substrate.organism.outcome_pattern_engine"],
    "DetectedPattern": ["substrate.organism.outcome_pattern_engine"],
    "AttributionLink": ["substrate.organism.outcome_pattern_engine"],
    "PatternSnapshot": ["substrate.organism.outcome_pattern_engine"],
    "OutcomePatternEngine": ["substrate.organism.outcome_pattern_engine"],
    "EvolutionEventType": ["substrate.organism.capability_evolution_engine"],
    "EvolutionEvent": ["substrate.organism.capability_evolution_engine"],
    "CapabilityTrajectory": ["substrate.organism.capability_evolution_engine"],
    "EvolutionSnapshot": ["substrate.organism.capability_evolution_engine"],
    "CapabilityEvolutionEngine": ["substrate.organism.capability_evolution_engine"],
    "LearningHealth": ["substrate.organism.learning_portfolio_runtime"],
    "LearningDriftType": ["substrate.organism.learning_portfolio_runtime"],
    "LearningDriftWarning": ["substrate.organism.learning_portfolio_runtime"],
    "LearningPortfolioSnapshot": ["substrate.organism.learning_portfolio_runtime"],
    "LearningPortfolioRuntime": ["substrate.organism.learning_portfolio_runtime"],
    # ── Campaign 13: Prediction Intelligence ──────────────────────────
    "TrajectoryStatus": ["substrate.organism.trajectory_intelligence_runtime"],
    "TrajectoryForecast": ["substrate.organism.trajectory_intelligence_runtime"],
    "TrajectoryIntelligenceRuntime": ["substrate.organism.trajectory_intelligence_runtime"],
    "ScenarioType": ["substrate.organism.scenario_intelligence_engine"],
    "FutureScenario": ["substrate.organism.scenario_intelligence_engine"],
    "ScenarioIntelligenceEngine": ["substrate.organism.scenario_intelligence_engine"],
    "PredictionHealth": ["substrate.organism.prediction_portfolio_runtime"],
    "PredictionDriftType": ["substrate.organism.prediction_portfolio_runtime"],
    "PredictionDriftWarning": ["substrate.organism.prediction_portfolio_runtime"],
    "PredictionPortfolioSnapshot": ["substrate.organism.prediction_portfolio_runtime"],
    "PredictionPortfolioRuntime": ["substrate.organism.prediction_portfolio_runtime"],
    # ── Campaign 14: Executive Intelligence ──────────────────────────
    # C14.0
    "ResourceType": ["substrate.organism.resource_allocation_runtime"],
    "AllocationPriority": ["substrate.organism.resource_allocation_runtime"],
    "AllocationHealth": ["substrate.organism.resource_allocation_runtime"],
    "AllocationRecommendation": ["substrate.organism.resource_allocation_runtime"],
    "ResourceBudget": ["substrate.organism.resource_allocation_runtime"],
    "AllocationSnapshot": ["substrate.organism.resource_allocation_runtime"],
    "ResourceAllocationRuntime": ["substrate.organism.resource_allocation_runtime"],
    # C14.1
    "TradeoffSeverity": ["substrate.organism.tradeoff_intelligence_engine"],
    "TradeoffOption": ["substrate.organism.tradeoff_intelligence_engine"],
    "TradeoffAnalysis": ["substrate.organism.tradeoff_intelligence_engine"],
    "TradeoffSnapshot": ["substrate.organism.tradeoff_intelligence_engine"],
    "TradeoffIntelligenceEngine": ["substrate.organism.tradeoff_intelligence_engine"],
    # C14.2
    "ExecutiveHealth": ["substrate.organism.executive_portfolio_runtime"],
    "ExecutiveDriftType": ["substrate.organism.executive_portfolio_runtime"],
    "ExecutiveDriftWarning": ["substrate.organism.executive_portfolio_runtime"],
    "ExecutivePortfolioSnapshot": ["substrate.organism.executive_portfolio_runtime"],
    "ExecutivePortfolioRuntime": ["substrate.organism.executive_portfolio_runtime"],
    # ── Campaign 15: Organism Governance & Coordination ──────────────
    # C15.0 — Governance Runtime
    "GovernanceAuthority": ["substrate.organism.governance_runtime"],
    "ConflictStatus": ["substrate.organism.governance_runtime"],
    "ConflictSeverityLevel": ["substrate.organism.governance_runtime"],
    "GovernanceHealth": ["substrate.organism.governance_runtime"],
    "SubsystemConflict": ["substrate.organism.governance_runtime"],
    "GovernancePolicy": ["substrate.organism.governance_runtime"],
    "GovernanceDriftType": ["substrate.organism.governance_runtime"],
    "GovernanceDriftWarning": ["substrate.organism.governance_runtime"],
    "GovernanceRuntimeSnapshot": ["substrate.organism.governance_runtime"],
    "GovernanceRuntime": ["substrate.organism.governance_runtime"],
    # C15.1 — Organism Coordination Engine
    "CoordinationIssueType": ["substrate.organism.organism_coordination_engine"],
    "CoordinationHealth": ["substrate.organism.organism_coordination_engine"],
    "CoordinationIssue": ["substrate.organism.organism_coordination_engine"],
    "CoordinationSnapshot": ["substrate.organism.organism_coordination_engine"],
    "OrganismCoordinationEngine": ["substrate.organism.organism_coordination_engine"],
    # C15.2 — Institutional Memory Runtime
    "KnowledgeState": ["substrate.organism.institutional_memory_runtime"],
    "InstitutionalMemoryHealth": ["substrate.organism.institutional_memory_runtime"],
    "MemoryDriftType": ["substrate.organism.institutional_memory_runtime"],
    "InstitutionalKnowledge": ["substrate.organism.institutional_memory_runtime"],
    "InstitutionalMemoryDriftWarning": ["substrate.organism.institutional_memory_runtime"],
    "InstitutionalMemorySnapshot": ["substrate.organism.institutional_memory_runtime"],
    "InstitutionalMemoryRuntime": ["substrate.organism.institutional_memory_runtime"],
    # C15.3 — Organism Portfolio Runtime
    "OrganismHealth": ["substrate.organism.organism_portfolio_runtime"],
    "OrganismDriftType": ["substrate.organism.organism_portfolio_runtime"],
    "OrganismDriftWarning": ["substrate.organism.organism_portfolio_runtime"],
    "SubsystemHealthEntry": ["substrate.organism.organism_portfolio_runtime"],
    "OrganismPortfolioSnapshot": ["substrate.organism.organism_portfolio_runtime"],
    "OrganismPortfolioRuntime": ["substrate.organism.organism_portfolio_runtime"],
    # C16.0 — Governed Execution Runtime
    "ExecutionState": ["substrate.organism.governed_execution_runtime"],
    "ExecutionBlocker": ["substrate.organism.governed_execution_runtime"],
    "GovernedExecutionHealth": ["substrate.organism.governed_execution_runtime"],
    "ExecutionStateAssessment": ["substrate.organism.governed_execution_runtime"],
    "GovernedExecutionSnapshot": ["substrate.organism.governed_execution_runtime"],
    "GovernedExecutionRuntime": ["substrate.organism.governed_execution_runtime"],
    # C16.1 — Organism State Runtime
    "OrganismMode": ["substrate.organism.organism_state_runtime"],
    "OrganismStateSnapshot": ["substrate.organism.organism_state_runtime"],
    "OrganismStateRuntime": ["substrate.organism.organism_state_runtime"],
    # C16.2 — Execution Lifecycle Runtime
    "LifecycleStage": ["substrate.organism.execution_lifecycle_runtime"],
    "LifecycleArc": ["substrate.organism.execution_lifecycle_runtime"],
    "ExecutionLifecycleSnapshot": ["substrate.organism.execution_lifecycle_runtime"],
    "ExecutionLifecycleRuntime": ["substrate.organism.execution_lifecycle_runtime"],
    # C17.0 — Orchestrator Presence Runtime
    "PresenceMode": ["substrate.workstation.orchestrator_presence_runtime"],
    "OrchestratorPresenceSnapshot": ["substrate.workstation.orchestrator_presence_runtime"],
    "OrchestratorPresenceRuntime": ["substrate.workstation.orchestrator_presence_runtime"],
    # C17.1 — Meta IDE Context Runtime
    "MetaIdeContextSnapshot": ["substrate.workstation.meta_ide_context_runtime"],
    "MetaIdeContextRuntime": ["substrate.workstation.meta_ide_context_runtime"],
    # C17.2 — Workstation Presence Runtime
    "WorkstationPresenceSnapshot": ["substrate.workstation.workstation_presence_runtime"],
    "WorkstationPresenceRuntime": ["substrate.workstation.workstation_presence_runtime"],
    # C18.0 — Unified Workstation Runtime
    "UnifiedWorkstationState": ["substrate.workstation.unified_workstation_runtime"],
    "UnifiedWorkstationSnapshot": ["substrate.workstation.unified_workstation_runtime"],
    "UnifiedWorkstationRuntime": ["substrate.workstation.unified_workstation_runtime"],
    # C18.2 — Attention Aggregation Runtime
    "AttentionQueueSnapshot": ["substrate.workstation.attention_aggregation_runtime"],
    "AttentionAggregationRuntime": ["substrate.workstation.attention_aggregation_runtime"],
    # C19.0 — Execution Fabric Runtime
    "ExecutionFabricState": ["substrate.workstation.execution_fabric_runtime"],
    "ExecutionFabricSnapshot": ["substrate.workstation.execution_fabric_runtime"],
    "ExecutionFabricRuntime": ["substrate.workstation.execution_fabric_runtime"],
    # C19.1 — Agent Workforce Runtime
    "WorkforceHealth": ["substrate.workstation.agent_workforce_runtime"],
    "AgentWorkforceSnapshot": ["substrate.workstation.agent_workforce_runtime"],
    "AgentWorkforceRuntime": ["substrate.workstation.agent_workforce_runtime"],
    # C19.2 — Session Machine Runtime
    "MachineSessionBinding": ["substrate.workstation.session_machine_runtime"],
    "SessionMachineSnapshot": ["substrate.workstation.session_machine_runtime"],
    "SessionMachineRuntime": ["substrate.workstation.session_machine_runtime"],
    # ── Campaign 20: Voice Operations & Ambient Jarvis ──────────────
    # C20.0 — Voice Ingress Runtime
    "VoiceSourceType": ["substrate.workstation.voice_ingress_runtime"],
    "ActivationMode": ["substrate.workstation.voice_ingress_runtime"],
    "VoiceChannelContext": ["substrate.workstation.voice_ingress_runtime"],
    "VoicePermissionScope": ["substrate.workstation.voice_ingress_runtime"],
    "VoiceIngressEvent": ["substrate.workstation.voice_ingress_runtime"],
    "VoiceIngressSnapshot": ["substrate.workstation.voice_ingress_runtime"],
    "VoiceIngressRuntime": ["substrate.workstation.voice_ingress_runtime"],
    # P4S-31D-1 — Voice Consent (VoiceIntentContract consent gate)
    "VoiceConsentGrant": ["substrate.workstation.voice_consent"],
    "VoiceConsentStore": ["substrate.workstation.voice_consent"],
    "VoiceConsentRefused": ["substrate.workstation.voice_consent"],
    # C20.1 — Voice Session Manager
    "VoiceSessionType": ["substrate.workstation.voice_session_manager"],
    "VoiceSessionPriority": ["substrate.workstation.voice_session_manager"],
    "ManagedVoiceSession": ["substrate.workstation.voice_session_manager"],
    "SessionConflictResolution": ["substrate.workstation.voice_session_manager"],
    "VoiceSessionManagerSnapshot": ["substrate.workstation.voice_session_manager"],
    "VoiceSessionManager": ["substrate.workstation.voice_session_manager"],
    # C20.2 — Ambient Wake Runtime
    "AmbientState": ["substrate.workstation.ambient_wake_runtime"],
    "WakeTransition": ["substrate.workstation.ambient_wake_runtime"],
    "AmbientWakeSnapshot": ["substrate.workstation.ambient_wake_runtime"],
    "AmbientWakeRuntime": ["substrate.workstation.ambient_wake_runtime"],
    # C20.3 — Voice Output Runtime
    "VoiceOutputTarget": ["substrate.workstation.voice_output_runtime"],
    "OutputRoutingDecision": ["substrate.workstation.voice_output_runtime"],
    "VoiceOutputSnapshot": ["substrate.workstation.voice_output_runtime"],
    "VoiceOutputRuntime": ["substrate.workstation.voice_output_runtime"],
    # C20.4 — Voice Operations Runtime
    "VoiceOperationsHealth": ["substrate.workstation.voice_operations_runtime"],
    "VoiceCapabilityStatus": ["substrate.workstation.voice_operations_runtime"],
    "VoiceOperationsSnapshot": ["substrate.workstation.voice_operations_runtime"],
    "VoiceOperationsRuntime": ["substrate.workstation.voice_operations_runtime"],
    # ── Campaign 21: Visual Awareness & Environmental Context ───────
    # C21.0 — Screen Awareness Runtime
    "ScreenAwarenessHealth": ["substrate.workstation.screen_awareness_runtime"],
    "DeviceScreenBinding": ["substrate.workstation.screen_awareness_runtime"],
    "ScreenAwarenessSnapshot": ["substrate.workstation.screen_awareness_runtime"],
    "ScreenAwarenessRuntime": ["substrate.workstation.screen_awareness_runtime"],
    # C21.1 — Environment Awareness Runtime
    "SurfaceType": ["substrate.workstation.environment_awareness_runtime"],
    "SurfaceHealth": ["substrate.workstation.environment_awareness_runtime"],
    "ObservedSurface": ["substrate.workstation.environment_awareness_runtime"],
    "EnvironmentAwarenessSnapshot": ["substrate.workstation.environment_awareness_runtime"],
    "EnvironmentAwarenessRuntime": ["substrate.workstation.environment_awareness_runtime"],
    # C21.2 — Visual Context Runtime
    "ContextBindingDepth": ["substrate.workstation.visual_context_runtime"],
    "ContextBinding": ["substrate.workstation.visual_context_runtime"],
    "VisualContextSnapshot": ["substrate.workstation.visual_context_runtime"],
    "VisualContextRuntime": ["substrate.workstation.visual_context_runtime"],
    # C21.3 — Attention Vision Runtime
    "VisualSignalType": ["substrate.workstation.attention_vision_runtime"],
    "VisualSignalSeverity": ["substrate.workstation.attention_vision_runtime"],
    "VisualAttentionSignal": ["substrate.workstation.attention_vision_runtime"],
    "AttentionVisionSnapshot": ["substrate.workstation.attention_vision_runtime"],
    "AttentionVisionRuntime": ["substrate.workstation.attention_vision_runtime"],
    # C21.4 — Visual Operations Runtime
    "VisualOperationsHealth": ["substrate.workstation.visual_operations_runtime"],
    "VisualCapabilityStatus": ["substrate.workstation.visual_operations_runtime"],
    "VisualOperationsSnapshot": ["substrate.workstation.visual_operations_runtime"],
    "VisualOperationsRuntime": ["substrate.workstation.visual_operations_runtime"],
    # ── C22 — Software Production Organism ─────────────────────────────
    # C22.0 — Production Operations Runtime
    "ProductionPhase": ["substrate.organism.production_ops_runtime"],
    "ProductionTarget": ["substrate.organism.production_ops_runtime"],
    "ProductionHealth": ["substrate.organism.production_ops_runtime"],
    # C22.1 — Production Planning Runtime
    "ProductionDiscipline": ["substrate.organism.production_planning_runtime"],
    "ProductionType": ["substrate.organism.production_planning_runtime"],
    # C22.2 — Production Workforce Runtime
    "ProductionRole": ["substrate.organism.production_workforce_runtime"],
    "ProductionAuthority": ["substrate.organism.production_workforce_runtime"],
    # C22.3 — Production Review Runtime
    "ReviewVerdict": ["substrate.organism.production_review_runtime"],
    "QualityDimension": ["substrate.organism.production_review_runtime"],
    # C22.4 — Capability Compounding Runtime
    "CompoundingStage": ["substrate.organism.capability_compounding_runtime"],
    "CompoundingHealth": ["substrate.organism.capability_compounding_runtime"],
    # C22.5 — Product Factory Runtime
    "ProductGoalType": ["substrate.organism.product_factory_runtime"],
    "ProductReadiness": ["substrate.organism.product_factory_runtime"],
    # C22.6 — Source Truth Runtime
    "LineageNodeType": ["substrate.organism.source_truth_runtime"],
    "LineageTerminalState": ["substrate.organism.source_truth_runtime"],
    # C26B — Deploy Verification Worker
    "DeployCheckStatus": ["substrate.organism.deploy_verification_worker"],
    "DeployCheckResult": ["substrate.organism.deploy_verification_worker"],
    "DeployVerificationResult": ["substrate.organism.deploy_verification_worker"],
    # C26A — Outcome Verification Runtime
    "VerificationLevel": ["substrate.organism.outcome_verification"],
    "OutcomeVerificationStatus": ["substrate.organism.outcome_verification"],
    "VerificationMethod": ["substrate.organism.outcome_verification"],
    "VerificationStepResult": ["substrate.organism.outcome_verification"],
    "VerificationPlan": ["substrate.organism.outcome_verification"],
    "OutcomeVerification": ["substrate.organism.outcome_verification"],
    # C26C — Projection Certification Framework
    "CertificationLevel": ["substrate.organism.projection_certification"],
    "LevelCheckResult": ["substrate.organism.projection_certification"],
    "ProjectionCertification": ["substrate.organism.projection_certification"],
    "ProjectionConfig": ["substrate.organism.projection_certification"],
    # C26E — Trust Engine
    "TrustDimension": ["substrate.organism.trust_score"],
    "TrustLevel": ["substrate.organism.trust_score"],
    "DimensionScore": ["substrate.organism.trust_score"],
    "TrustScore": ["substrate.organism.trust_score"],
    # C26D — Correspondence Ledger
    "CorrespondenceStatus": ["substrate.organism.production_truth_delta"],
    "CorrespondenceResult": ["substrate.organism.production_truth_delta"],
    "CorrespondenceChecker": ["substrate.organism.production_truth_delta"],
    "RegressionAlert": ["substrate.organism.correspondence_scheduler"],
    "CorrespondenceScheduler": ["substrate.organism.correspondence_scheduler"],
    # C26F — Reality Challenge Benchmark
    "BenchmarkDomain": ["substrate.organism.benchmarks.reality_correspondence"],
    "BenchmarkScenario": ["substrate.organism.benchmarks.reality_correspondence"],
    "BenchmarkResult": ["substrate.organism.benchmarks.reality_correspondence"],
    # ── substrate/organism/device_provisioner.py (Device Onboarding) ────
    "DeviceDiagnosis": ["substrate.organism.device_provisioner"],
    "ProvisionStep": ["substrate.organism.device_provisioner"],
    "ProvisionResult": ["substrate.organism.device_provisioner"],
    # ── substrate/organism/self_use/ (C27 Daily Driver Readiness) ──────
    "StreamType": ["substrate.organism.self_use.task_taxonomy"],
    "TaskDomain": ["substrate.organism.self_use.task_taxonomy"],
    "CoherenceDomain": ["substrate.organism.self_use.task_taxonomy"],
    "TaskStatus": ["substrate.organism.self_use.task_catalog"],
    "SelfUseTask": ["substrate.organism.self_use.task_catalog"],
    "TaskResult": ["substrate.organism.self_use.task_catalog"],
    "TaskCatalog": ["substrate.organism.self_use.task_catalog"],
    "GapType": ["substrate.organism.self_use.gap_ledger"],
    "GapEntry": ["substrate.organism.self_use.gap_ledger"],
    "GapLedger": ["substrate.organism.self_use.gap_ledger"],
    "CapabilityState": ["substrate.organism.self_use.projection_delta"],
    "ProjectionCapability": ["substrate.organism.self_use.projection_delta"],
    "ProjectionDelta": ["substrate.organism.self_use.projection_delta"],
    "DeltaReport": ["substrate.organism.self_use.projection_delta"],
    "ProjectionDeltaEngine": ["substrate.organism.self_use.projection_delta"],
    "FunctionalStatus": ["substrate.organism.self_use.meta_ide_audit"],
    "SubsystemOperation": ["substrate.organism.self_use.meta_ide_audit"],
    "SubsystemAudit": ["substrate.organism.self_use.meta_ide_audit"],
    "AuditMatrix": ["substrate.organism.self_use.meta_ide_audit"],
    "CertificationGate": ["substrate.organism.self_use.certification_report"],
    "CoherenceMetrics": ["substrate.organism.self_use.certification_report"],
    "GateResult": ["substrate.organism.self_use.certification_report"],
    "CertificationReport": ["substrate.organism.self_use.certification_report"],
    "ReportBuilder": ["substrate.organism.self_use.certification_report"],
    # ── transports/node_mesh/integration/types.py (peripheral inventory) ──
    "PeripheralType": ["transports.node_mesh.integration.types"],
    "Peripheral": ["transports.node_mesh.integration.types"],
    # ── substrate/understanding/reconstruction/ (evidence/claim data layer) ──
    "SourceRecord": ["substrate.understanding.reconstruction.contracts"],
    "ObservationRecord": ["substrate.understanding.reconstruction.contracts"],
    "ClaimLedgerEntry": ["substrate.understanding.reconstruction.contracts"],
    "DerivedBelief": ["substrate.understanding.reconstruction.contracts"],
    "IdentityResolution": ["substrate.understanding.reconstruction.contracts"],
    "CausalSupportRecord": ["substrate.understanding.reconstruction.contracts"],
    "ValidTime": ["substrate.understanding.reconstruction.contracts"],
    "ActivityRecord": ["substrate.understanding.reconstruction.provenance"],
    "JsonlAppender": ["substrate.understanding.reconstruction.provenance"],
    "RunLayout": ["substrate.understanding.reconstruction.provenance"],
    "ClaimLedger": ["substrate.understanding.reconstruction.ledger"],
    "IdentityResolutionLog": ["substrate.understanding.reconstruction.identity"],
    "ImportEvidenceResult": ["substrate.understanding.reconstruction.import_evidence"],
    "TestEvidenceResult": ["substrate.understanding.reconstruction.test_evidence"],
}


# ── Legacy Duplicates ───────────────────────────────────────────────────────
# Pre-existing type definitions that duplicate canonical types. These existed
# before the divergence gate was installed (2026-05-27). They are TECHNICAL
# DEBT, not design — each should be converged to import from the canonical
# source. The gate blocks NEW divergence; this allowlist grandfathers OLD.
#
# WP-P2-001: each exemption now carries required metadata (owner, sunset,
# rationale) and is validated to resolve to a real symbol by
# `scripts/check_type_divergence.py --registry-audit`. An exemption that points
# to a missing module/symbol, or lacks metadata, or is past its sunset, FAILS
# the audit — so this list cannot silently grandfather a symbol that no longer
# exists, and cannot be padded without accountability. The list must SHRINK.
#
# Shape: {module_path: {type_name: {"owner", "sunset" (YYYY-MM-DD), "rationale"}}}

LEGACY_DUPLICATES_META: dict[str, dict[str, dict[str, str]]] = {
    # ── MVP Wave 2 (2026-07-23) ────────────────────────────────────────────
    # Pre-existing homonym surfaced (not introduced) when the Wave 2 C1
    # fail-closed edit touched plan_execution_adapter.py: Gate 1 blocks any
    # STAGED file carrying a divergence, even a long-standing one. The adapter's
    # local ``ExecutionGraph`` (a dict of ExecutablePlan for spine execution)
    # predates and is distinct from the canonical
    # ``substrate.organism.execution_graph.ExecutionGraph`` (an ExecutionGraphNode
    # DAG). It is ruled a Wave 2 compatibility representation (convergence ledger
    # #13); registered here rather than weakening the gate — must SHRINK, retired
    # when plan_execution_adapter is converged off the legacy execution path.
    "substrate.organism.plan_execution_adapter": {
        "ExecutionGraph": {
            "owner": "organism",
            "sunset": "2026-12-31",
            "rationale": (
                "adapter-local ExecutablePlan DAG predates canonical "
                "execution_graph.ExecutionGraph; Wave 2 compat representation "
                "(ledger #13), retired when the adapter leaves the legacy path"
            ),
        },
    },
    # ── MVP Wave 0 (2026-07-20) ────────────────────────────────────────────
    # Pre-existing homonyms surfaced (not introduced) when the runtime-state
    # boundary packet touched these modules: Gate 1 blocks any STAGED file
    # carrying a divergence, even a long-standing one. Each name below predates
    # this packet and is verifiably unchanged on main. Registered here rather
    # than weakening the gate; they must SHRINK, never grow.
    "substrate.organism.dependency_graph": {
        "DependencyStrength": {
            "owner": "organism",
            "sunset": "2026-12-31",
            "rationale": "graph-local strength enum predates type centralization",
        },
    },
    "substrate.organism.operator_session": {
        "IntentType": {
            "owner": "organism",
            "sunset": "2026-12-31",
            "rationale": "operator-session intent taxonomy predates canonical IntentType",
        },
    },
    "substrate.organism.qualification_harness": {
        "GapType": {
            "owner": "organism",
            "sunset": "2026-12-31",
            "rationale": "qualification gap taxonomy predates type centralization",
        },
    },
    "substrate.organism.template_registry": {
        "AgentType": {
            "owner": "organism",
            "sunset": "2026-12-31",
            "rationale": "template-registry agent taxonomy predates canonical AgentType",
        },
    },
    "substrate.organism.world_model": {
        "GapSeverity": {
            "owner": "organism",
            "sunset": "2026-12-31",
            "rationale": "organism self-model gap severity predates type centralization",
        },
    },
    "substrate.execution.runtime.worker_runtime_contracts": {
        "ProofStatus": {
            "owner": "execution-runtime",
            "sunset": "2026-12-31",
            "rationale": "worker contract ProofStatus predates substrate.types centralization",
        },
    },
    "substrate.execution.runtime.execution_contracts_v1": {
        "SignalSource": {
            "owner": "execution-runtime",
            "sunset": "2026-12-31",
            "rationale": "v1 contract module predates type centralization",
        },
        "GovernanceVerdict": {
            "owner": "execution-runtime",
            "sunset": "2026-12-31",
            "rationale": "v1 contract module predates type centralization",
        },
    },
    "substrate.execution.runtime.runtime_execution_result_v1": {
        "ExecutionOutcome": {
            "owner": "execution-runtime",
            "sunset": "2026-12-31",
            "rationale": "v1 result contract predates type centralization",
        },
    },
    "substrate.execution.bridge.capabilities": {
        "Capability": {
            "owner": "execution-bridge",
            "sunset": "2026-12-31",
            "rationale": "bridge Capability enum is a legitimate homonym of the BaseModel Capability",
        },
    },
    "substrate.execution.loop.execution_loop": {
        "ExecutionResult": {
            "owner": "execution-loop",
            "sunset": "2026-12-31",
            "rationale": "loop-local ExecutionResult predates centralization",
        },
    },
    "substrate.state.memory.contracts.canonical_memory_store_v1": {
        "MemoryEntry": {
            "owner": "state-memory",
            "sunset": "2026-12-31",
            "rationale": "v1 memory store contract predates centralization",
        },
    },
    "substrate.sockets.envelopes": {
        "SignalEnvelope": {
            "owner": "sockets",
            "sunset": "2026-12-31",
            "rationale": "sockets envelope predates substrate.types.SignalEnvelope",
        },
    },
    "substrate.understanding.perception.primitive_decomposition_v1": {
        # WP-P3 rehome: the PrimitiveType/RelationshipType enum fork was removed —
        # this module now imports both from substrate.types (single metamodel enum
        # source), so they are no longer duplicates and are dropped from this ledger.
        # PrimitiveObservation remains a v1 perception dataclass (str observation_id,
        # to_dict, is_inferred) distinct from the canonical Pydantic
        # substrate.types.PrimitiveObservation; kept here as a name-homonym duplicate,
        # re-anchored to the new perception path. A later naming-cleanup packet may
        # rename it (→ PerceptionPrimitiveObservation), which would retire this entry.
        "PrimitiveObservation": {
            "owner": "understanding-perception",
            "sunset": "2026-12-31",
            "rationale": "v1 perception decomposition observation predates centralization; distinct shape from canonical PrimitiveObservation",
        },
    },
    "substrate.understanding.perception.orchestrator": {
        "IngestionResult": {
            "owner": "understanding-perception",
            "sunset": "2026-12-31",
            "rationale": "perception orchestrator IngestionResult predates centralization",
        },
    },
    "adapters.adapter_engine.substrate_candidate_gen_v1": {
        "MemoryType": {
            "owner": "adapters",
            "sunset": "2026-12-31",
            "rationale": "candidate-gen v1 MemoryType predates centralization",
        },
    },
    "nodes.environments.execution_binding_contracts": {
        "EnvironmentType": {
            "owner": "nodes-environments",
            "sunset": "2026-12-31",
            "rationale": "environment binding contract EnvironmentType predates centralization",
        },
    },
    "substrate.organism.next_action_engine": {
        "ActionCategory": {
            "owner": "organism-actions",
            "sunset": "2026-12-31",
            "rationale": "pre-Phase-26 ActionCategory shares name with canonical action types",
        },
    },
    "substrate.organism.recommendation_engine": {
        "RecommendationEngine": {
            "owner": "organism-recommendation",
            "sunset": "2026-12-31",
            "rationale": "legacy RecommendationEngine homonym predates centralization",
        },
    },
    "substrate.execution.bridge.actions": {
        "ActionStatus": {
            "owner": "execution-bridge",
            "sunset": "2026-12-31",
            "rationale": "pre-Phase-26 bridge action types share names with canonical",
        },
        "ActionResult": {
            "owner": "execution-bridge",
            "sunset": "2026-12-31",
            "rationale": "pre-Phase-26 bridge action types share names with canonical",
        },
    },
    "substrate.contracts.agent_types": {
        "RoutingResult": {
            "owner": "contracts",
            "sunset": "2026-12-31",
            "rationale": "model-routing RoutingResult (output/provider/model/tokens) is a distinct concept from empire_router RoutingResult (domain/objective/scope/urgency)",
        },
    },
    # Removed 2026-07-04 (WP-P2-001) — dead exemptions masking nothing:
    #   substrate.foundation.primitives::Modality  (module no longer exists)
    #   substrate.organism.next_action_engine::ActionResult  (symbol removed)
    #   substrate.composition.mastery.research.extraction::ActionCategory  (symbol removed)
}


def legacy_names_for(module: str) -> set[str]:
    """Back-compat accessor: the set of legacy-exempted type names for a module.

    Preserves the old `LEGACY_DUPLICATES.get(module, set())` contract for
    consumers, now sourced from the metadata-carrying registry.
    """
    return set(LEGACY_DUPLICATES_META.get(module, {}).keys())


# Back-compat alias so existing `from ... import LEGACY_DUPLICATES` keeps working
# and behaves like the old `dict[str, set[str]]`.
LEGACY_DUPLICATES: dict[str, set[str]] = {
    module: set(names.keys()) for module, names in LEGACY_DUPLICATES_META.items()
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
    if type_name in legacy_names_for(defining_module):
        return None
    return (
        f"DIVERGENCE BLOCKED: '{type_name}' already exists in "
        f"{canonical_list[0]}. "
        f"Import it: from {canonical_list[0]} import {type_name}"
    )
