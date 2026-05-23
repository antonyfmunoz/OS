"""Tool Mastery Manager — unification layer over the Tool Mastery Engine.

The Manager composes existing TME utilities (_tme_common, verify_tool_skill,
check_skill_staleness) into a single entry point that can:

    - discover tools in the environment
    - classify each into a unified coverage status
    - scaffold a missing skill skeleton (honest: no fabricated research)
    - queue research / refresh / repair work via the Control Plane
    - report backlog + bootstrap status for a fresh environment
    - maintain freshness of existing skills over time

It does NOT duplicate TME logic and does NOT fabricate best-practices content.
Research remains a separate step handled by the TME decision tree.
"""

from __future__ import annotations

from .models import (
    CoverageReport,
    CoverageStatus,
    EnsureResult,
    ManagerPlan,
    ToolRef,
)

from .mastery_assurance import (
    MasteryAssuranceDecision,
    MasteryAssuranceStatus,
    RecommendedFlow,
    ensure_mastery_before_execution,
    mastery_assurance_blocks_execution,
)

from .tool_mastery_resolver import (
    ResolvedCapabilityMention,
    ResolvedMasteryPack,
    ResolvedToolMention,
    ToolMasteryResolution,
    resolve_mastery_for_task,
)

from .active_tool_context import (
    ActiveToolContext,
    create_active_tool_context,
    update_active_tool_context,
    should_continue_context,
    should_switch_context,
    summarize_active_tool_context,
)

__all__ = [
    "CoverageReport",
    "CoverageStatus",
    "EnsureResult",
    "ManagerPlan",
    "ToolRef",
    "MasteryAssuranceDecision",
    "MasteryAssuranceStatus",
    "RecommendedFlow",
    "ensure_mastery_before_execution",
    "mastery_assurance_blocks_execution",
    "ResolvedCapabilityMention",
    "ResolvedMasteryPack",
    "ResolvedToolMention",
    "ToolMasteryResolution",
    "resolve_mastery_for_task",
    "ActiveToolContext",
    "create_active_tool_context",
    "update_active_tool_context",
    "should_continue_context",
    "should_switch_context",
    "summarize_active_tool_context",
]
