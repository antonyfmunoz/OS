"""
runtime.transport — Lazy-import package.

All symbols are available via ``from runtime.transport import X`` or
``from runtime.transport.submodule import Y``. Submodules are loaded
on first access (PEP 562 __getattr__), not at package import time.

Previously this file was 570+ lines of eager imports that pulled in
40 submodules transitively — blocking 151 deferred migration items.
See: data/audits/2026-05-13_triage_manifest.md (Wave 0.5 thread).
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

_log = logging.getLogger(__name__)

# ── Symbol → (submodule, attribute) mapping ───────────────────────────
# Every entry here was previously an eager ``from runtime.transport.X import Y``
# at the top of this file.  Now resolved lazily on first access.

_LAZY_MAP: dict[str, tuple[str, str]] = {}


def _m(submodule: str, *names: str) -> None:
    """Register symbols from a submodule for lazy import."""
    for name in names:
        _LAZY_MAP[name] = (f"runtime.transport.{submodule}", name)


# ── Core registries ───────────────────────────────────────────────────

_m("nodes", "Node", "NodeRole", "NodeType", "NodeStatus", "NodeRegistry")
_m("capabilities", "Capability", "CapabilityRegistry")
_m("station", "StationContract", "StationHeartbeat", "StationEvent", "ControlMode")
_m("actions", "SafeAction", "ActionKind", "ActionResult", "ActionStatus")
_m("rituals", "Ritual", "RitualKind", "RitualState", "RitualRegistry")
_m("roles", "AgentRole", "RoleScope", "RoleRegistry")
_m("storage", "SubstrateStorage", "JSONFileStorage", "NeonStorage", "get_storage")
_m("station_bus", "StationBus", "get_station_bus")
_m("capability_tagging", "tag_request")
_m("station_daemon", "StationDaemon")
_m(
    "station_helpers",
    "propose_play_sound",
    "propose_speak_text",
    "propose_open_url",
    "propose_launch_app",
    "propose_open_scene",
)
_m("scenes", "Scene", "SceneStep", "SCENE_REGISTRY", "get_scene", "list_scenes")
_m("app_allowlist", "APP_ALLOWLIST", "AllowedApp", "resolve_app")
_m("ritual_body", "RitualPolicy", "run_close_day_body", "run_open_day_body")
_m("role_resolver", "resolve_role", "substrate_slug_for")

# ── Task system ───────────────────────────────────────────────────────

_m(
    "task_system",
    "Task",
    "TaskExecutionPolicy",
    "TaskStatus",
    "TaskStore",
    "classify_task",
    "create_task",
    "get_task_summary",
    "process_task",
    "run_overnight_tasks",
)
_m(
    "capability_routing",
    "TaskCapability",
    "ExecutionTarget",
    "infer_task_capabilities",
    "choose_execution_target",
    "route_task",
)
_m(
    "task_queue",
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
)
_m("task_execution", "execute_task", "detect_human_block", "run_overnight_execution")
_m(
    "task_pipeline",
    "PipelineStatus",
    "StepStatus",
    "PipelineAgentRole",
    "PipelineStep",
    "TaskPipeline",
    "PipelineStore",
)
_m("task_decomposition", "infer_agent_role", "decompose_task")
_m(
    "pipeline_execution",
    "execute_pipeline",
    "retry_step",
    "resume_pipeline",
    "get_pipeline_summary",
    "format_blocked_summary",
    "format_pipeline_summary",
)

# ── Voice / session ──────────────────────────────────────────────────

_m(
    "voice_session",
    "VoiceSession",
    "VoiceSessionStatus",
    "VoiceSessionRuntime",
    "VoiceTurn",
    "VoiceTurnSource",
    "VoiceSessionStore",
    "get_voice_session_store",
    "set_voice_responder",
    "voice_session_report",
)

# ── Perception + auto-task ────────────────────────────────────────────

_m(
    "perception",
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
)
_m(
    "auto_task_generation",
    "generate_tasks_from_perceptions",
    "run_perception_cycle",
    "get_perception_summary",
)

# ── Station presence + triggers ──────────────────────────────────────

_m(
    "station_presence",
    "StationPresenceMode",
    "StationPresence",
    "StationPresenceStore",
    "get_station_presence",
    "update_station_presence",
    "set_presence_mode",
    "mark_local_available",
    "mark_local_unavailable",
    "get_station_summary",
)
_m(
    "station_triggers",
    "StationTriggerType",
    "StationTriggerEvent",
    "StationTriggerStore",
    "register_station_trigger",
    "handle_station_trigger",
)

# ── Voice / wake ─────────────────────────────────────────────────────

_m(
    "voice_wake",
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
)

# ── Local machine control ────────────────────────────────────────────

_m(
    "local_control",
    "LocalControlAction",
    "LocalControlMode",
    "RequestStatus",
    "LocalControlRequest",
    "LocalControlStore",
    "is_action_allowed",
    "submit_control_request",
    "execute_control_request",
    "get_local_control_summary",
)

# Renamed alias: local_control.open_scene → open_scene_request
_ALIASES: dict[str, tuple[str, str]] = {
    "open_scene_request": ("runtime.transport.local_control", "open_scene"),
}

# ── Live agent sessions ──────────────────────────────────────────────

_m(
    "live_sessions",
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
)


# ── Deferred / experimental modules ─────────────────────────────────
# These modules may not exist or may have broken imports.  They are
# resolved lazily just like the rest, but failures are silently logged
# instead of raising.

_DEFERRED: dict[str, tuple[str, str]] = {}


def _d(submodule: str, *names: str) -> None:
    """Register symbols from a deferred submodule (import errors suppressed)."""
    for name in names:
        _DEFERRED[name] = (f"runtime.transport.{submodule}", name)


_d(
    "execution_contract",
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
)
_d(
    "execution_adapter",
    "ExecutionAdapter",
    "AdapterHealth",
    "LocalRuntimeAdapter",
    "WorkstationAdapter",
)
_d("execution_router", "ExecutionRouter")
_d(
    "execution_events",
    "build_execution_requested_event",
    "build_execution_completed_event",
    "build_execution_failed_event",
    "build_execution_timed_out_event",
    "build_execution_rejected_event",
    "build_execution_retried_event",
)
_d("execution_worker", "ExecutionWorker")
_d("execution_authority", "ExecutionAuthority")
_d("execution_result_handler", "ExecutionResultHandler")
_d(
    "decision_engine",
    "DecisionEngine",
    "DecisionOutput",
    "DecisionStrategy",
    "Rule",
    "RuleBasedStrategy",
    "evaluate_and_emit",
)
_d(
    "planner",
    "IntentAwareStrategy",
    "PlannerStrategy",
    "build_intent_complete_mutations",
    "build_intent_fail_mutations",
    "build_step_advance_mutations",
    "derive_plan",
    "register_plan_generator",
)
_d("event_scheduler", "NonMutatingEventViolation", "register_event_schema_source")
_d(
    "llm_planner",
    "EventSchema",
    "EventTypeRegistry",
    "LLMEventProposal",
    "LLMPlannerConfig",
    "LLMPlanningStrategy",
    "LLMProposalResult",
    "ProposedEvent",
    "SelectionPolicy",
    "ValidationResult",
)
_d(
    "llm_decision_events",
    "build_llm_decision_accepted_event",
    "build_llm_decision_received_event",
    "build_llm_decision_rejected_event",
    "build_llm_decision_requested_event",
    "build_llm_decision_skipped_event",
    "build_llm_response_drift_event",
)
_d("llm_replay", "LLMDecisionRecord", "ReplayableStrategy")
_d(
    "interaction_archive",
    "Direction",
    "Interface",
    "ArchivedInteraction",
    "InteractionArchive",
    "get_interaction_archive",
    "archive_inbound",
    "archive_outbound",
    "create_clear_checkpoint",
)
_d(
    "task_record",
    "TaskRecordStatus",
    "TaskRecord",
    "TaskRecordStore",
    "get_task_record_store",
    "record_task_start",
    "record_task_complete",
    "record_task_failure",
)
_d(
    "query_brain",
    "QueryIntent",
    "QueryResult",
    "classify_query",
    "execute_query",
    "is_query",
    "parse_time_reference",
)
_d("conversation_router", "route_message", "detect_high_context_risk", "is_browser_intent")
_d(
    "browser_policy",
    "BrowserTarget",
    "FallbackReason",
    "BrowserActionRecord",
    "resolve_browser_target",
)
_d(
    "task_checkpoint",
    "AutoClearPolicy",
    "TaskCheckpointResult",
    "checkpoint_task_boundary",
    "checkpoint_from_task",
    "checkpoint_from_pipeline",
)
_d(
    "presence_runtime",
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
)
_d(
    "plan_executor",
    "ExecutionOutcome",
    "PhaseResult",
    "PlanExecutionResult",
    "execute_with_plan",
    "execute_sequential_phases",
    "execute_parallel_subagents",
    "execute_planner_executor_verifier",
)
_d("decision_events", "build_decision_made_event")
_d(
    "intent_models",
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
)
_d(
    "planner_events",
    "build_intent_completed_event",
    "build_intent_created_event",
    "build_plan_created_event",
    "build_plan_step_emitted_event",
)


# ── PEP 562 lazy loader ─────────────────────────────────────────────


def __getattr__(name: str) -> Any:
    # Core lazy symbols
    if name in _LAZY_MAP:
        module_path, attr = _LAZY_MAP[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value

    # Renamed aliases (e.g. open_scene → open_scene_request)
    if name in _ALIASES:
        module_path, attr = _ALIASES[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value

    # Deferred / experimental (suppress import errors)
    if name in _DEFERRED:
        module_path, attr = _DEFERRED[name]
        try:
            mod = importlib.import_module(module_path)
            value = getattr(mod, attr)
            globals()[name] = value
            return value
        except Exception as exc:
            _log.debug("deferred import %s.%s skipped: %s", module_path, attr, exc)
            raise AttributeError(
                f"module 'runtime.transport' has no attribute {name!r} "
                f"(deferred import failed: {exc})"
            ) from exc

    raise AttributeError(f"module 'runtime.transport' has no attribute {name!r}")


# ── __all__ ──────────────────────────────────────────────────────────

__all__ = list(_LAZY_MAP.keys()) + list(_ALIASES.keys()) + list(_DEFERRED.keys())
