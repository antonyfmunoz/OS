"""
umh.substrate — Bridging layer between current VPS-centric EOS and the
target distributed, capability-aware AI operating system.

This package is ADDITIVE. It does not modify the hot path
(gateway, cognitive_loop, model_router, agent_runtime). Instead it introduces
typed contracts and lightweight registries that future code can route through:

    nodes         — execution targets beyond "the VPS"
    capabilities  — what a node can do (reasoning, browser_control, mic, etc.)
    station       — contract for a future local Station Daemon
    actions       — SafeAction intent schema for local computer control
    rituals       — open_day / close_day workflow scaffold
    roles         — multi-agent role registry (ea, ceo, portfolio_advisor)

Everything here is intentionally minimal. Registries are in-memory; DB
persistence hooks are marked `# FUTURE:` so they can be wired to Neon later
without changing call sites.

Import surface (stable):

    from umh.world.substrate import (
        Node, NodeType, NodeStatus, NodeRegistry,
        Capability, CapabilityRegistry,
        StationContract, StationHeartbeat, StationEvent,
        SafeAction, ActionKind, ActionResult,
        Ritual, RitualKind, RitualState, RitualRegistry,
        AgentRole, RoleScope, RoleRegistry,
    )
"""

from umh.substrate.nodes import (
    Node,
    NodeType,
    NodeStatus,
    NodeRegistry,
)
from umh.substrate.capabilities import (
    Capability,
    CapabilityRegistry,
)
from umh.substrate.station import (
    StationContract,
    StationHeartbeat,
    StationEvent,
    ControlMode,
)
from umh.substrate.actions import (
    SafeAction,
    ActionKind,
    ActionResult,
    ActionStatus,
)
from umh.substrate.rituals import (
    Ritual,
    RitualKind,
    RitualState,
    RitualRegistry,
)
from umh.substrate.roles import (
    AgentRole,
    RoleScope,
    RoleRegistry,
)
from umh.substrate.storage import (
    SubstrateStorage,
    JSONFileStorage,
    NeonStorage,
    get_storage,
)
from umh.substrate.station_bus import (
    StationBus,
    get_station_bus,
)
from umh.substrate.capability_tagging import tag_request
from umh.substrate.station_daemon import StationDaemon
from umh.substrate.station_helpers import (
    propose_play_sound,
    propose_speak_text,
    propose_open_url,
    propose_launch_app,
    propose_open_scene,
)
from umh.substrate.scenes import (
    Scene,
    SceneStep,
    SCENE_REGISTRY,
    get_scene,
    list_scenes,
)
from umh.substrate.app_allowlist import APP_ALLOWLIST, AllowedApp, resolve_app
from umh.substrate.ritual_body import (
    RitualPolicy,
    run_close_day_body,
    run_open_day_body,
)
from umh.substrate.role_resolver import (
    resolve_role,
    substrate_slug_for,
)
from umh.substrate.task_system import (
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
    classify_task,
    create_task,
    get_task_summary,
    process_task,
    run_overnight_tasks,
)
from umh.substrate.capability_routing import (
    TaskCapability,
    ExecutionTarget,
    infer_task_capabilities,
    choose_execution_target,
    route_task,
)
from umh.substrate.task_queue import (
    TaskPriority,
    QUEUE_OPERATOR_BLOCKED,
    QUEUE_AUTONOMOUS_DAY,
    QUEUE_AUTONOMOUS_OVERNIGHT,
    QUEUE_APPROVAL_WAITING,
    infer_task_priority,
    assign_queue,
    prioritize_and_queue,
    get_ready_tasks,
    get_overnight_tasks,
    get_waiting_on_operator_tasks,
    get_tasks_sorted_for_execution,
    get_enhanced_task_summary,
    prepare_overnight_queue,
)
from umh.substrate.task_execution import (
    execute_task,
    detect_human_block,
    run_overnight_execution,
)
from umh.substrate.task_pipeline import (
    PipelineStatus,
    StepStatus,
    PipelineAgentRole,
    PipelineStep,
    TaskPipeline,
    PipelineStore,
)
from umh.substrate.task_decomposition import (
    infer_agent_role,
    decompose_task,
)
from umh.substrate.pipeline_execution import (
    execute_pipeline,
    retry_step,
    resume_pipeline,
    get_pipeline_summary,
    format_blocked_summary,
    format_pipeline_summary,
)
from umh.substrate.voice_session import (
    VoiceSession,
    VoiceSessionStatus,
    VoiceSessionRuntime,
    VoiceTurn,
    VoiceTurnSource,
    VoiceSessionStore,
    get_voice_session_store,
    set_voice_responder,
    voice_session_report,
)

# v4: perception + auto task generation
from umh.substrate.perception import (
    PerceptionSource,
    PerceptionSeverity,
    PerceptionRecord,
    PerceptionStore,
    collect_task_perception,
    collect_pipeline_perception,
    collect_operator_session_perception,
    collect_node_status_perception,
    collect_git_perception,
    collect_runtime_log_perception,
    collect_station_presence_perception,
    collect_local_control_perception,
    collect_live_session_perception,
    collect_all_perceptions,
)
from umh.substrate.auto_task_generation import (
    generate_tasks_from_perceptions,
    run_perception_cycle,
    get_perception_summary,
)

# v4: station presence + triggers
from umh.substrate.station_presence import (
    StationPresenceMode,
    StationPresence,
    StationPresenceStore,
    get_station_presence,
    update_station_presence,
    set_presence_mode,
    mark_local_available,
    mark_local_unavailable,
    get_station_summary,
)
from umh.substrate.station_triggers import (
    StationTriggerType,
    StationTriggerEvent,
    StationTriggerStore,
    register_station_trigger,
    handle_station_trigger,
)

# v4: voice / wake layer
from umh.substrate.voice_wake import (
    WakeTrigger,
    StationMode,
    VoiceWakeState,
    VoiceWakeStore,
    WakeWordAdapter,
    ClapAdapter,
    enable_wake,
    disable_wake,
    enable_clap,
    disable_clap,
    enable_tts,
    disable_tts,
    register_trigger,
    get_voice_wake_summary,
)

# v4: local machine control
from umh.substrate.local_control import (
    LocalControlAction,
    LocalControlMode,
    RequestStatus,
    LocalControlRequest,
    LocalControlStore,
    is_action_allowed,
    submit_control_request,
    execute_control_request,
    open_scene as open_scene_request,
    get_local_control_summary,
)

# v4: live agent sessions
from umh.substrate.live_sessions import (
    LiveSessionState,
    LiveSessionType,
    LiveSession,
    LiveSessionStore,
    create_live_session,
    start_live_session,
    pause_live_session,
    resume_live_session,
    end_live_session,
    fail_live_session,
    attach_task_to_live_session,
    attach_pipeline_to_live_session,
    detach_task_from_live_session,
    detach_pipeline_from_live_session,
    get_live_session_summary,
)

try:
    # Interaction archive (verbatim conversation continuity)
    from umh.substrate.interaction_archive import (
        Direction,
        Interface,
        ArchivedInteraction,
        InteractionArchive,
        get_interaction_archive,
        archive_inbound,
        archive_outbound,
        create_clear_checkpoint,
    )
except ImportError:
    pass

try:
    # v10: task record (lifecycle indexing)
    from umh.substrate.task_record import (
        TaskRecordStatus,
        TaskRecord,
        TaskRecordStore,
        get_task_record_store,
        record_task_start,
        record_task_complete,
        record_task_failure,
    )
except ImportError:
    pass

try:
    # v10: query brain (conversational retrieval)
    from umh.substrate.query_brain import (
        QueryIntent,
        QueryResult,
        classify_query,
        execute_query,
        is_query,
        parse_time_reference,
    )
except ImportError:
    pass

try:
    # v10: conversation router
    from umh.substrate.conversation_router import (
        route_message,
        detect_high_context_risk,
        is_browser_intent,
    )
except ImportError:
    pass

try:
    # v11: browser execution policy
    from umh.substrate.browser_policy import (
        BrowserTarget,
        FallbackReason,
        BrowserActionRecord,
        resolve_browser_target,
    )
except ImportError:
    pass

try:
    # v9: task checkpoint
    from umh.substrate.task_checkpoint import (
        AutoClearPolicy,
        TaskCheckpointResult,
        checkpoint_task_boundary,
        checkpoint_from_task,
        checkpoint_from_pipeline,
    )
except ImportError:
    pass

try:
    # v9: presence runtime
    from umh.substrate.presence_runtime import (
        PresenceMode,
        PresenceBehavior,
        PRESENCE_BEHAVIORS,
        WorkProfile,
        ProfileBehavior,
        PROFILE_BEHAVIORS,
        OperatorRuntimeState,
        BootstrapRequirements,
        set_presence,
        set_profile,
        get_runtime,
        resolve_bootstrap,
        get_lifecycle_modifiers,
        presence_for_continuity,
    )
except ImportError:
    pass
try:
    from umh.substrate.plan_executor import (
        ExecutionOutcome,
        PhaseResult,
        PlanExecutionResult,
        execute_with_plan,
        execute_sequential_phases,
        execute_parallel_subagents,
        execute_planner_executor_verifier,
    )
except ImportError:
    pass

# v22: event-native execution fabric
from umh.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget as FabricExecutionTarget,
    NodeCapability,
    NodeHealthSnapshot,
    RoutingContext,
    RoutingDecision,
    RoutingReasonCode,
)
from umh.substrate.execution_adapter import (
    ExecutionAdapter,
    AdapterHealth,
    LocalRuntimeAdapter,
    WorkstationAdapter,
)
from umh.substrate.execution_router import (
    ExecutionRouter,
)
from umh.substrate.execution_events import (
    build_execution_requested_event,
    build_execution_completed_event,
    build_execution_failed_event,
    build_execution_timed_out_event,
    build_execution_rejected_event,
    build_execution_retried_event,
)
from umh.substrate.execution_worker import (
    ExecutionWorker,
)
from umh.substrate.execution_authority import (
    ExecutionAuthority,
)
from umh.substrate.execution_result_handler import (
    ExecutionResultHandler,
)
try:
    from umh.substrate.decision_events import (
        build_decision_made_event,
    )
except ImportError:
    pass
from umh.substrate.decision_engine import (
    DecisionEngine,
    DecisionOutput,
    DecisionStrategy,
    Rule,
    RuleBasedStrategy,
    evaluate_and_emit,
)
try:
    from umh.substrate.intent_models import (
        Intent,
        IntentStatus,
        IntentType,
        Plan,
        PlanStep,
        build_intent_create_mutations,
        build_intent_update_mutations,
        compute_intent_id,
        compute_plan_id,
        get_active_intents_from_state,
        get_intent_from_state,
        intent_store_key,
    )
except ImportError:
    pass
try:
    from umh.substrate.planner_events import (
        build_intent_completed_event,
        build_intent_created_event,
        build_plan_created_event,
        build_plan_step_emitted_event,
    )
except ImportError:
    pass
from umh.substrate.planner import (
    IntentAwareStrategy,
    PlannerStrategy,
    build_intent_complete_mutations,
    build_intent_fail_mutations,
    build_step_advance_mutations,
    derive_plan,
    register_plan_generator,
)

# Event scheduler runtime enforcement
from umh.substrate.event_scheduler import (
    NonMutatingEventViolation,
    register_event_schema_source,
)

# LLM planning layer
from umh.substrate.llm_planner import (
    EventSchema,
    EventTypeRegistry,
    LLMEventProposal,
    LLMPlannerConfig,
    LLMPlanningStrategy,
    LLMProposalResult,
    ProposedEvent,
    SelectionPolicy,
    ValidationResult,
)
from umh.substrate.llm_decision_events import (
    build_llm_decision_accepted_event,
    build_llm_decision_received_event,
    build_llm_decision_rejected_event,
    build_llm_decision_requested_event,
    build_llm_decision_skipped_event,
    build_llm_response_drift_event,
)
from umh.substrate.llm_replay import (
    LLMDecisionRecord,
    ReplayableStrategy,
)

__all__ = [
    "Node",
    "NodeType",
    "NodeStatus",
    "NodeRegistry",
    "Capability",
    "CapabilityRegistry",
    "StationContract",
    "StationHeartbeat",
    "StationEvent",
    "ControlMode",
    "SafeAction",
    "ActionKind",
    "ActionResult",
    "ActionStatus",
    "Ritual",
    "RitualKind",
    "RitualState",
    "RitualRegistry",
    "AgentRole",
    "RoleScope",
    "RoleRegistry",
    "SubstrateStorage",
    "JSONFileStorage",
    "NeonStorage",
    "get_storage",
    "StationBus",
    "get_station_bus",
    "tag_request",
    "resolve_role",
    "substrate_slug_for",
    "StationDaemon",
    "propose_play_sound",
    "propose_speak_text",
    "propose_open_url",
    "propose_launch_app",
    "propose_open_scene",
    "Scene",
    "SceneStep",
    "SCENE_REGISTRY",
    "get_scene",
    "list_scenes",
    "APP_ALLOWLIST",
    "AllowedApp",
    "resolve_app",
    "RitualPolicy",
    "run_open_day_body",
    "run_close_day_body",
    "VoiceSession",
    "VoiceSessionStatus",
    "VoiceSessionRuntime",
    "VoiceTurn",
    "VoiceTurnSource",
    "VoiceSessionStore",
    "get_voice_session_store",
    "set_voice_responder",
    "voice_session_report",
    "Task",
    "TaskExecutionPolicy",
    "TaskStatus",
    "TaskStore",
    "classify_task",
    "create_task",
    "get_task_summary",
    "process_task",
    "run_overnight_tasks",
    # capability routing (v2)
    "TaskCapability",
    "ExecutionTarget",
    "infer_task_capabilities",
    "choose_execution_target",
    "route_task",
    # task queue (v2)
    "TaskPriority",
    "QUEUE_OPERATOR_BLOCKED",
    "QUEUE_AUTONOMOUS_DAY",
    "QUEUE_AUTONOMOUS_OVERNIGHT",
    "QUEUE_APPROVAL_WAITING",
    "infer_task_priority",
    "assign_queue",
    "prioritize_and_queue",
    "get_ready_tasks",
    "get_overnight_tasks",
    "get_waiting_on_operator_tasks",
    "get_tasks_sorted_for_execution",
    "get_enhanced_task_summary",
    "prepare_overnight_queue",
    # task execution (v2)
    "execute_task",
    "detect_human_block",
    "run_overnight_execution",
    # task pipeline (v3)
    "PipelineStatus",
    "StepStatus",
    "PipelineAgentRole",
    "PipelineStep",
    "TaskPipeline",
    "PipelineStore",
    # task decomposition (v3)
    "infer_agent_role",
    "decompose_task",
    # pipeline execution (v3)
    "execute_pipeline",
    "retry_step",
    "resume_pipeline",
    "get_pipeline_summary",
    "format_blocked_summary",
    "format_pipeline_summary",
    # perception + auto task generation (v4)
    "PerceptionSource",
    "PerceptionSeverity",
    "PerceptionRecord",
    "PerceptionStore",
    "collect_task_perception",
    "collect_pipeline_perception",
    "collect_operator_session_perception",
    "collect_node_status_perception",
    "collect_git_perception",
    "collect_runtime_log_perception",
    "collect_station_presence_perception",
    "collect_local_control_perception",
    "collect_live_session_perception",
    "collect_all_perceptions",
    "generate_tasks_from_perceptions",
    "run_perception_cycle",
    "get_perception_summary",
    # station presence + triggers (v4)
    "StationPresenceMode",
    "StationPresence",
    "StationPresenceStore",
    "get_station_presence",
    "update_station_presence",
    "set_presence_mode",
    "mark_local_available",
    "mark_local_unavailable",
    "get_station_summary",
    "StationTriggerType",
    "StationTriggerEvent",
    "StationTriggerStore",
    "register_station_trigger",
    "handle_station_trigger",
    # voice / wake layer (v4)
    "WakeTrigger",
    "StationMode",
    "VoiceWakeState",
    "VoiceWakeStore",
    "WakeWordAdapter",
    "ClapAdapter",
    "enable_wake",
    "disable_wake",
    "enable_clap",
    "disable_clap",
    "enable_tts",
    "disable_tts",
    "register_trigger",
    "get_voice_wake_summary",
    # local machine control (v4)
    "LocalControlAction",
    "LocalControlMode",
    "RequestStatus",
    "LocalControlRequest",
    "LocalControlStore",
    "is_action_allowed",
    "submit_control_request",
    "execute_control_request",
    "open_scene_request",
    "get_local_control_summary",
    # live agent sessions (v4)
    "LiveSessionState",
    "LiveSessionType",
    "LiveSession",
    "LiveSessionStore",
    "create_live_session",
    "start_live_session",
    "pause_live_session",
    "resume_live_session",
    "end_live_session",
    "fail_live_session",
    "attach_task_to_live_session",
    "attach_pipeline_to_live_session",
    "detach_task_from_live_session",
    "detach_pipeline_from_live_session",
    "get_live_session_summary",
    # interaction archive (verbatim conversation continuity)
    "Direction",
    "Interface",
    "ArchivedInteraction",
    "InteractionArchive",
    "get_interaction_archive",
    "archive_inbound",
    "archive_outbound",
    "create_clear_checkpoint",
    # task record (v10)
    "TaskRecordStatus",
    "TaskRecord",
    "TaskRecordStore",
    "get_task_record_store",
    "record_task_start",
    "record_task_complete",
    "record_task_failure",
    # query brain (v10)
    "QueryIntent",
    "QueryResult",
    "classify_query",
    "execute_query",
    "is_query",
    "parse_time_reference",
    # conversation router (v10)
    "route_message",
    "detect_high_context_risk",
    "is_browser_intent",
    # browser execution policy (v11)
    "BrowserTarget",
    "FallbackReason",
    "BrowserActionRecord",
    "resolve_browser_target",
    # task checkpoint (v9)
    "AutoClearPolicy",
    "TaskCheckpointResult",
    "checkpoint_task_boundary",
    "checkpoint_from_task",
    "checkpoint_from_pipeline",
    # presence runtime (v9)
    "PresenceMode",
    "PresenceBehavior",
    "PRESENCE_BEHAVIORS",
    "WorkProfile",
    "ProfileBehavior",
    "PROFILE_BEHAVIORS",
    "OperatorRuntimeState",
    "BootstrapRequirements",
    "set_presence",
    "set_profile",
    "get_runtime",
    "resolve_bootstrap",
    "get_lifecycle_modifiers",
    "presence_for_continuity",
    # plan executor (execution-aware orchestration)
    "ExecutionOutcome",
    "PhaseResult",
    "PlanExecutionResult",
    "execute_with_plan",
    "execute_sequential_phases",
    "execute_parallel_subagents",
    "execute_planner_executor_verifier",
    # event-native execution fabric (v22)
    "ExecutionClass",
    "ExecutionConstraints",
    "ExecutionMode",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
    "FabricExecutionTarget",
    "NodeCapability",
    "NodeHealthSnapshot",
    "RoutingContext",
    "RoutingDecision",
    "RoutingReasonCode",
    "ExecutionAdapter",
    "AdapterHealth",
    "LocalRuntimeAdapter",
    "WorkstationAdapter",
    "ExecutionRouter",
    "build_execution_requested_event",
    "build_execution_completed_event",
    "build_execution_failed_event",
    "build_execution_timed_out_event",
    "build_execution_rejected_event",
    "build_execution_retried_event",
    "ExecutionWorker",
    "ExecutionAuthority",
    "ExecutionResultHandler",
    "get_execution_mode",
    # decision engine (intelligence layer)
    "build_decision_made_event",
    "DecisionEngine",
    "DecisionOutput",
    "DecisionStrategy",
    "Rule",
    "RuleBasedStrategy",
    "evaluate_and_emit",
    # intent + planning layer (intelligence layer)
    "Intent",
    "IntentStatus",
    "IntentType",
    "Plan",
    "PlanStep",
    "build_intent_create_mutations",
    "build_intent_update_mutations",
    "compute_intent_id",
    "compute_plan_id",
    "get_active_intents_from_state",
    "get_intent_from_state",
    "intent_store_key",
    "build_intent_completed_event",
    "build_intent_created_event",
    "build_plan_created_event",
    "build_plan_step_emitted_event",
    "IntentAwareStrategy",
    "PlannerStrategy",
    "build_intent_complete_mutations",
    "build_intent_fail_mutations",
    "build_step_advance_mutations",
    "derive_plan",
    "register_plan_generator",
    # Event scheduler runtime enforcement
    "NonMutatingEventViolation",
    "register_event_schema_source",
    # LLM planning layer
    "EventSchema",
    "EventTypeRegistry",
    "LLMEventProposal",
    "LLMPlannerConfig",
    "LLMPlanningStrategy",
    "LLMProposalResult",
    "ProposedEvent",
    "SelectionPolicy",
    "ValidationResult",
    "LLMDecisionRecord",
    "ReplayableStrategy",
    "build_llm_decision_accepted_event",
    "build_llm_decision_received_event",
    "build_llm_decision_rejected_event",
    "build_llm_decision_requested_event",
    "build_llm_decision_skipped_event",
    "build_llm_response_drift_event",
]
