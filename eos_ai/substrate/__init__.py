"""
eos_ai.substrate — Bridging layer between current VPS-centric EOS and the
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

    from eos_ai.substrate import (
        Node, NodeType, NodeStatus, NodeRegistry,
        Capability, CapabilityRegistry,
        StationContract, StationHeartbeat, StationEvent,
        SafeAction, ActionKind, ActionResult,
        Ritual, RitualKind, RitualState, RitualRegistry,
        AgentRole, RoleScope, RoleRegistry,
    )
"""

from eos_ai.substrate.nodes import (
    Node,
    NodeRole,
    NodeType,
    NodeStatus,
    NodeRegistry,
)
from eos_ai.substrate.capabilities import (
    Capability,
    CapabilityRegistry,
)
from eos_ai.substrate.station import (
    StationContract,
    StationHeartbeat,
    StationEvent,
    ControlMode,
)
from eos_ai.substrate.actions import (
    SafeAction,
    ActionKind,
    ActionResult,
    ActionStatus,
)
from eos_ai.substrate.rituals import (
    Ritual,
    RitualKind,
    RitualState,
    RitualRegistry,
)
from eos_ai.substrate.roles import (
    AgentRole,
    RoleScope,
    RoleRegistry,
)
from eos_ai.substrate.storage import (
    SubstrateStorage,
    JSONFileStorage,
    NeonStorage,
    get_storage,
)
from eos_ai.substrate.station_bus import (
    StationBus,
    get_station_bus,
)
from eos_ai.substrate.capability_tagging import tag_request
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.station_helpers import (
    propose_play_sound,
    propose_speak_text,
    propose_open_url,
    propose_launch_app,
    propose_open_scene,
)
from eos_ai.substrate.scenes import (
    Scene,
    SceneStep,
    SCENE_REGISTRY,
    get_scene,
    list_scenes,
)
from eos_ai.substrate.app_allowlist import APP_ALLOWLIST, AllowedApp, resolve_app
from eos_ai.substrate.ritual_body import (
    RitualPolicy,
    run_close_day_body,
    run_open_day_body,
)
from eos_ai.substrate.role_resolver import (
    resolve_role,
    substrate_slug_for,
)
from eos_ai.substrate.task_system import (
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
from eos_ai.substrate.capability_routing import (
    TaskCapability,
    ExecutionTarget,
    infer_task_capabilities,
    choose_execution_target,
    route_task,
)
from eos_ai.substrate.task_queue import (
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
from eos_ai.substrate.task_execution import (
    execute_task,
    detect_human_block,
    run_overnight_execution,
)
from eos_ai.substrate.task_pipeline import (
    PipelineStatus,
    StepStatus,
    PipelineAgentRole,
    PipelineStep,
    TaskPipeline,
    PipelineStore,
)
from eos_ai.substrate.task_decomposition import (
    infer_agent_role,
    decompose_task,
)
from eos_ai.substrate.pipeline_execution import (
    execute_pipeline,
    retry_step,
    resume_pipeline,
    get_pipeline_summary,
    format_blocked_summary,
    format_pipeline_summary,
)
from eos_ai.substrate.voice_session import (
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
from eos_ai.substrate.perception import (
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
from eos_ai.substrate.auto_task_generation import (
    generate_tasks_from_perceptions,
    run_perception_cycle,
    get_perception_summary,
)

# v4: station presence + triggers
from eos_ai.substrate.station_presence import (
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
from eos_ai.substrate.station_triggers import (
    StationTriggerType,
    StationTriggerEvent,
    StationTriggerStore,
    register_station_trigger,
    handle_station_trigger,
)

# v4: voice / wake layer
from eos_ai.substrate.voice_wake import (
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
from eos_ai.substrate.local_control import (
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
from eos_ai.substrate.live_sessions import (
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
        "eos_ai.substrate.execution_contract",
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
        "eos_ai.substrate.execution_adapter",
        [
            "ExecutionAdapter",
            "AdapterHealth",
            "LocalRuntimeAdapter",
            "WorkstationAdapter",
        ],
    ),
    ("eos_ai.substrate.execution_router", ["ExecutionRouter"]),
    (
        "eos_ai.substrate.execution_events",
        [
            "build_execution_requested_event",
            "build_execution_completed_event",
            "build_execution_failed_event",
            "build_execution_timed_out_event",
            "build_execution_rejected_event",
            "build_execution_retried_event",
        ],
    ),
    ("eos_ai.substrate.execution_worker", ["ExecutionWorker"]),
    ("eos_ai.substrate.execution_authority", ["ExecutionAuthority"]),
    ("eos_ai.substrate.execution_result_handler", ["ExecutionResultHandler"]),
    (
        "eos_ai.substrate.decision_engine",
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
        "eos_ai.substrate.planner",
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
        "eos_ai.substrate.event_scheduler",
        [
            "NonMutatingEventViolation",
            "register_event_schema_source",
        ],
    ),
    (
        "eos_ai.substrate.llm_planner",
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
        "eos_ai.substrate.llm_decision_events",
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
        "eos_ai.substrate.llm_replay",
        [
            "LLMDecisionRecord",
            "ReplayableStrategy",
        ],
    ),
    # Not-yet-implemented modules — will silently skip
    (
        "eos_ai.substrate.interaction_archive",
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
        "eos_ai.substrate.task_record",
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
        "eos_ai.substrate.query_brain",
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
        "eos_ai.substrate.conversation_router",
        [
            "route_message",
            "detect_high_context_risk",
            "is_browser_intent",
        ],
    ),
    (
        "eos_ai.substrate.browser_policy",
        [
            "BrowserTarget",
            "FallbackReason",
            "BrowserActionRecord",
            "resolve_browser_target",
        ],
    ),
    (
        "eos_ai.substrate.task_checkpoint",
        [
            "AutoClearPolicy",
            "TaskCheckpointResult",
            "checkpoint_task_boundary",
            "checkpoint_from_task",
            "checkpoint_from_pipeline",
        ],
    ),
    (
        "eos_ai.substrate.presence_runtime",
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
        "eos_ai.substrate.plan_executor",
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
    ("eos_ai.substrate.decision_events", ["build_decision_made_event"]),
    (
        "eos_ai.substrate.intent_models",
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
        "eos_ai.substrate.planner_events",
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
