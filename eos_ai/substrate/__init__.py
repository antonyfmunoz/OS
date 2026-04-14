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
]
