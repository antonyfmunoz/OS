"""
EOS Platform Layer — domain-specific orchestration for business execution.

The first platform projection onto the generic substrate harness.
Founder speaks only to EA.  EA delegates internally to CEO or
Portfolio Advisor.  All responses are EA-mediated.

Public API:
    from eos_ai.platforms.eos import (
        # Main entrypoint
        handle_founder_message,
        EAResponse,

        # Roles
        EOSRole,
        get_role_meta,
        is_founder_facing,

        # Intent
        FounderIntent,
        FounderIntentType,
        parse_founder_intent,

        # Delegation
        should_delegate,
        choose_delegate,

        # Context
        build_ea_context,
        build_ceo_context,
        build_portfolio_context,
        build_context_for_role,

        # Response formatting
        format_ea_response,
        format_briefing,
        format_execution_summary,

        # Decision log
        EOSDecisionRecord,
        DecisionLog,

        # Discord hook
        handle_eos_discord_message,

        # Live session bridge
        create_ea_live_session,
        attach_founder_issue_to_live_session,
    )
"""

# Roles
from eos_ai.platforms.eos.roles import (
    EOSRole,
    get_all_roles,
    get_role_meta,
    is_founder_facing,
    substrate_slug,
    ROLE_TO_SUBSTRATE_SLUG,
)

# Intent routing
from eos_ai.platforms.eos.intent_routing import (
    FounderIntent,
    FounderIntentType,
    parse_founder_intent,
)

# Delegation
from eos_ai.platforms.eos.delegation import (
    choose_delegate,
    should_delegate,
)

# Context builders
from eos_ai.platforms.eos.context_builder import (
    build_ceo_context,
    build_context_for_role,
    build_ea_context,
    build_portfolio_context,
)

# Response formatter
from eos_ai.platforms.eos.response_formatter import (
    format_blocked_decision_summary,
    format_briefing,
    format_ea_response,
    format_execution_summary,
    format_portfolio_recommendation,
    format_strategic_recommendation,
)

# EA orchestrator (main entrypoint)
from eos_ai.platforms.eos.ea_orchestrator import (
    EAResponse,
    handle_founder_message,
)

# Decision log
from eos_ai.platforms.eos.decision_log import (
    DecisionLog,
    EOSDecisionRecord,
)

# Discord hook + live session bridge
from eos_ai.platforms.eos.discord_hook import (
    attach_founder_issue_to_live_session,
    create_ea_live_session,
    handle_eos_discord_message,
    handle_eos_discord_live_message,
)

# Live runtime
from eos_ai.platforms.eos.live_runtime import (
    EALiveRuntime,
    LiveRuntimeResult,
    RuntimeState,
    get_live_runtime,
    handle_live_user_utterance,
    pause_live_runtime,
    resume_live_runtime,
    stop_live_runtime,
    interrupt_live_runtime,
    format_live_progress_update,
)

# Execution bridge
from eos_ai.platforms.eos.execution_bridge import (
    ExecutionBridgeResult,
    execute_created_work_immediately,
)

__all__ = [
    # Roles
    "EOSRole",
    "get_all_roles",
    "get_role_meta",
    "is_founder_facing",
    "substrate_slug",
    "ROLE_TO_SUBSTRATE_SLUG",
    # Intent
    "FounderIntent",
    "FounderIntentType",
    "parse_founder_intent",
    # Delegation
    "choose_delegate",
    "should_delegate",
    # Context
    "build_ceo_context",
    "build_context_for_role",
    "build_ea_context",
    "build_portfolio_context",
    # Response formatter
    "format_blocked_decision_summary",
    "format_briefing",
    "format_ea_response",
    "format_execution_summary",
    "format_portfolio_recommendation",
    "format_strategic_recommendation",
    # EA orchestrator
    "EAResponse",
    "handle_founder_message",
    # Decision log
    "DecisionLog",
    "EOSDecisionRecord",
    # Discord hook
    "attach_founder_issue_to_live_session",
    "create_ea_live_session",
    "handle_eos_discord_message",
    "handle_eos_discord_live_message",
    # Live runtime
    "EALiveRuntime",
    "LiveRuntimeResult",
    "RuntimeState",
    "get_live_runtime",
    "handle_live_user_utterance",
    "pause_live_runtime",
    "resume_live_runtime",
    "stop_live_runtime",
    "interrupt_live_runtime",
    "format_live_progress_update",
    # Execution bridge
    "ExecutionBridgeResult",
    "execute_created_work_immediately",
]
