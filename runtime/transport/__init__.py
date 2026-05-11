"""
runtime.transport — Bridging layer between current VPS-centric EOS and the
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

    from runtime.substrate import (
        Node, NodeType, NodeStatus, NodeRegistry,
        Capability, CapabilityRegistry,
        StationContract, StationHeartbeat, StationEvent,
        SafeAction, ActionKind, ActionResult,
        Ritual, RitualKind, RitualState, RitualRegistry,
        AgentRole, RoleScope, RoleRegistry,
    )
"""

from runtime.transport.nodes import (
    Node,
    NodeRole,
    NodeType,
    NodeStatus,
    NodeRegistry,
)
from runtime.transport.capabilities import (
    Capability,
    CapabilityRegistry,
)
from runtime.transport.station import (
    StationContract,
    StationHeartbeat,
    StationEvent,
    ControlMode,
)
from runtime.transport.actions import (
    SafeAction,
    ActionKind,
    ActionResult,
    ActionStatus,
)
from runtime.transport.rituals import (
    Ritual,
    RitualKind,
    RitualState,
    RitualRegistry,
)
from runtime.transport.roles import (
    AgentRole,
    RoleScope,
    RoleRegistry,
)
from runtime.transport.storage import (
    SubstrateStorage,
    JSONFileStorage,
    NeonStorage,
    get_storage,
)
from runtime.transport.station_bus import (
    StationBus,
    get_station_bus,
)
from runtime.transport.capability_tagging import tag_request
from runtime.transport.station_daemon import StationDaemon
from runtime.transport.station_helpers import (
    propose_play_sound,
    propose_speak_text,
    propose_open_url,
    propose_launch_app,
    propose_open_scene,
)
from runtime.transport.scenes import (
    Scene,
    SceneStep,
    SCENE_REGISTRY,
    get_scene,
    list_scenes,
)
from runtime.transport.app_allowlist import APP_ALLOWLIST, AllowedApp, resolve_app
from runtime.transport.ritual_body import (
    RitualPolicy,
    run_close_day_body,
    run_open_day_body,
)
from runtime.transport.role_resolver import (
    resolve_role,
    substrate_slug_for,
)
from runtime.transport.task_system import (
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
from runtime.transport.capability_routing import (
    TaskCapability,
    ExecutionTarget,
    infer_task_capabilities,
    choose_execution_target,
    route_task,
)
from runtime.transport.task_queue import (
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
from runtime.transport.task_execution import (
    execute_task,
    detect_human_block,
    run_overnight_execution,
)
from runtime.transport.task_pipeline import (
    PipelineStatus,
    StepStatus,
    PipelineAgentRole,
    PipelineStep,
    TaskPipeline,
    PipelineStore,
)
from runtime.transport.task_decomposition import (
    infer_agent_role,
    decompose_task,
)
from runtime.transport.pipeline_execution import (
    execute_pipeline,
    retry_step,
    resume_pipeline,
    get_pipeline_summary,
    format_blocked_summary,
    format_pipeline_summary,
)
from runtime.transport.voice_session import (
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
from runtime.transport.perception import (
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
from runtime.transport.auto_task_generation import (
    generate_tasks_from_perceptions,
    run_perception_cycle,
    get_perception_summary,
)

# v4: station presence + triggers
from runtime.transport.station_presence import (
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
from runtime.transport.station_triggers import (
    StationTriggerType,
    StationTriggerEvent,
    StationTriggerStore,
    register_station_trigger,
    handle_station_trigger,
)

# v4: voice / wake layer
from runtime.transport.voice_wake import (
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
from runtime.transport.local_control import (
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
from runtime.transport.live_sessions import (
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

# ─── Experimental / partially-implemented modules ───────────────────────────
# Wrapped in try/except to prevent crash-loops when files are missing or
# export lists have drifted from the source modules.
import importlib as _il
import logging as _lg

_log = _lg.getLogger(__name__)


def _safe_import(mod_path: str, names: list[str]) -> dict:
    """Import *names* from *mod_path*, returning what was found."""
    found: dict = {}
    try:
        mod = _il.import_module(mod_path)
        for name in names:
            obj = getattr(mod, name, None)
            if obj is not None:
                found[name] = obj
    except Exception as exc:
        _log.debug("[substrate] deferred import %s skipped: %s", mod_path, exc)
    return found


_deferred_blocks = [
    (
        "runtime.transport.execution_contract",
        [
            "ExecutionClass",
            "ExecutionConstraints",
            "ExecutionMode",
            "ExecutionRequest",
            "ExecutionResult",
            "ExecutionStatus",
            "NodeCapability",
            "NodeHealthSnapshot",
            "RoutingContext",
            "RoutingDecision",
            "RoutingReasonCode",
            "get_execution_mode",
        ],
    ),
    (
        "runtime.transport.execution_adapter",
        [
            "ExecutionAdapter",
            "AdapterHealth",
            "LocalRuntimeAdapter",
            "WorkstationAdapter",
        ],
    ),
    ("runtime.transport.execution_router", ["ExecutionRouter"]),
    (
        "runtime.transport.execution_events",
        [
            "build_execution_requested_event",
            "build_execution_completed_event",
            "build_execution_failed_event",
            "build_execution_timed_out_event",
            "build_execution_rejected_event",
            "build_execution_retried_event",
        ],
    ),
    ("runtime.transport.execution_worker", ["ExecutionWorker"]),
    ("runtime.transport.execution_authority", ["ExecutionAuthority"]),
    ("runtime.transport.execution_result_handler", ["ExecutionResultHandler"]),
    (
        "runtime.transport.decision_engine",
        [
            "DecisionEngine",
            "DecisionOutput",
            "DecisionStrategy",
            "Rule",
            "RuleBasedStrategy",
            "evaluate_and_emit",
        ],
    ),
    (
        "runtime.transport.planner",
        [
            "IntentAwareStrategy",
            "PlannerStrategy",
            "build_intent_complete_mutations",
            "build_intent_fail_mutations",
            "build_step_advance_mutations",
            "derive_plan",
            "register_plan_generator",
        ],
    ),
    (
        "runtime.transport.event_scheduler",
        [
            "NonMutatingEventViolation",
            "register_event_schema_source",
        ],
    ),
    (
        "runtime.transport.llm_planner",
        [
            "EventSchema",
            "EventTypeRegistry",
            "LLMEventProposal",
            "LLMPlannerConfig",
            "LLMPlanningStrategy",
            "LLMProposalResult",
            "ProposedEvent",
            "SelectionPolicy",
            "ValidationResult",
        ],
    ),
    (
        "runtime.transport.llm_decision_events",
        [
            "build_llm_decision_accepted_event",
            "build_llm_decision_received_event",
            "build_llm_decision_rejected_event",
            "build_llm_decision_requested_event",
            "build_llm_decision_skipped_event",
            "build_llm_response_drift_event",
        ],
    ),
    (
        "runtime.transport.llm_replay",
        [
            "LLMDecisionRecord",
            "ReplayableStrategy",
        ],
    ),
    # Not-yet-implemented modules — will silently skip
    (
        "runtime.transport.interaction_archive",
        [
            "Direction",
            "Interface",
            "ArchivedInteraction",
            "InteractionArchive",
            "get_interaction_archive",
            "archive_inbound",
            "archive_outbound",
            "create_clear_checkpoint",
        ],
    ),
    (
        "runtime.transport.task_record",
        [
            "TaskRecordStatus",
            "TaskRecord",
            "TaskRecordStore",
            "get_task_record_store",
            "record_task_start",
            "record_task_complete",
            "record_task_failure",
        ],
    ),
    (
        "runtime.transport.query_brain",
        [
            "QueryIntent",
            "QueryResult",
            "classify_query",
            "execute_query",
            "is_query",
            "parse_time_reference",
        ],
    ),
    (
        "runtime.transport.conversation_router",
        [
            "route_message",
            "detect_high_context_risk",
            "is_browser_intent",
        ],
    ),
    (
        "runtime.transport.browser_policy",
        [
            "BrowserTarget",
            "FallbackReason",
            "BrowserActionRecord",
            "resolve_browser_target",
        ],
    ),
    (
        "runtime.transport.task_checkpoint",
        [
            "AutoClearPolicy",
            "TaskCheckpointResult",
            "checkpoint_task_boundary",
            "checkpoint_from_task",
            "checkpoint_from_pipeline",
        ],
    ),
    (
        "runtime.transport.presence_runtime",
        [
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
        ],
    ),
    (
        "runtime.transport.plan_executor",
        [
            "ExecutionOutcome",
            "PhaseResult",
            "PlanExecutionResult",
            "execute_with_plan",
            "execute_sequential_phases",
            "execute_parallel_subagents",
            "execute_planner_executor_verifier",
        ],
    ),
    ("runtime.transport.decision_events", ["build_decision_made_event"]),
    (
        "runtime.transport.intent_models",
        [
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
        ],
    ),
    (
        "runtime.transport.planner_events",
        [
            "build_intent_completed_event",
            "build_intent_created_event",
            "build_plan_created_event",
            "build_plan_step_emitted_event",
        ],
    ),
]

for _mod_path, _names in _deferred_blocks:
    _found = _safe_import(_mod_path, _names)
    globals().update(_found)

_CORE_EXPORTS = [
    "Node",
    "NodeRole",
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
    "resolve_role",
    "substrate_slug_for",
]

# Deferred exports: only include what actually loaded
_all_deferred_names = [n for _mp, _ns in _deferred_blocks for n in _ns]
__all__ = _CORE_EXPORTS + [n for n in _all_deferred_names if n in globals()]
