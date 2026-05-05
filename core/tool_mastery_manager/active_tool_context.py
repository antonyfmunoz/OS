"""Active Tool Context for the Tool Mastery Engine.

Tracks active tools, capabilities, mastery packs, runtimes, and
governance constraints for an ongoing task. Persists until the task
changes or a better tool is selected.

TME is a UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .tool_mastery_resolver import (
    ToolMasteryResolution,
    detect_tool_mentions,
)


@dataclass
class ActiveToolContext:
    task_id: str = ""
    task_summary: str = ""
    active_tools: list[str] = field(default_factory=list)
    active_capabilities: list[str] = field(default_factory=list)
    active_adapter_packages: list[str] = field(default_factory=list)
    active_access_paths: list[str] = field(default_factory=list)
    active_mastery_packs: list[str] = field(default_factory=list)
    active_runtimes: list[str] = field(default_factory=list)
    active_governance_constraints: list[str] = field(default_factory=list)
    started_at: str = ""
    last_updated_at: str = ""
    reuse_until_condition: str = "task_change_or_tool_switch"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_summary": self.task_summary,
            "active_tools": self.active_tools,
            "active_capabilities": self.active_capabilities,
            "active_adapter_packages": self.active_adapter_packages,
            "active_access_paths": self.active_access_paths,
            "active_mastery_packs": self.active_mastery_packs,
            "active_runtimes": self.active_runtimes,
            "active_governance_constraints": self.active_governance_constraints,
            "started_at": self.started_at,
            "last_updated_at": self.last_updated_at,
            "reuse_until_condition": self.reuse_until_condition,
            "notes": self.notes,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_active_tool_context(
    task_summary: str,
    resolution: ToolMasteryResolution,
    task_id: str = "",
) -> ActiveToolContext:
    now = _now_iso()
    return ActiveToolContext(
        task_id=task_id,
        task_summary=task_summary,
        active_tools=[t.normalized_tool_name for t in resolution.detected_tools],
        active_capabilities=[c.capability_name for c in resolution.detected_capabilities],
        active_mastery_packs=[p.pack_id for p in resolution.required_mastery_packs],
        active_runtimes=list(resolution.detected_runtimes),
        started_at=now,
        last_updated_at=now,
    )


def update_active_tool_context(
    context: ActiveToolContext,
    new_resolution: ToolMasteryResolution,
) -> ActiveToolContext:
    new_tools = [t.normalized_tool_name for t in new_resolution.detected_tools]
    new_caps = [c.capability_name for c in new_resolution.detected_capabilities]
    new_packs = [p.pack_id for p in new_resolution.required_mastery_packs]
    new_runtimes = list(new_resolution.detected_runtimes)

    for t in new_tools:
        if t not in context.active_tools:
            context.active_tools.append(t)
    for c in new_caps:
        if c not in context.active_capabilities:
            context.active_capabilities.append(c)
    for p in new_packs:
        if p not in context.active_mastery_packs:
            context.active_mastery_packs.append(p)
    for r in new_runtimes:
        if r not in context.active_runtimes:
            context.active_runtimes.append(r)

    context.last_updated_at = _now_iso()
    return context


def should_continue_context(
    context: ActiveToolContext,
    new_user_intent: str,
) -> bool:
    if not context.active_tools:
        return False
    new_tools = detect_tool_mentions(new_user_intent)
    if not new_tools:
        return True
    new_tool_names = {t.normalized_tool_name for t in new_tools}
    if new_tool_names.issubset(set(context.active_tools)):
        return True
    return False


def should_switch_context(
    context: ActiveToolContext,
    new_resolution: ToolMasteryResolution,
) -> bool:
    if not new_resolution.detected_tools:
        return False
    new_tool_names = {t.normalized_tool_name for t in new_resolution.detected_tools}
    current_tool_names = set(context.active_tools)
    if not new_tool_names.intersection(current_tool_names):
        return True
    new_cap_names = {c.capability_name for c in new_resolution.detected_capabilities}
    current_cap_names = set(context.active_capabilities)
    if new_cap_names and not new_cap_names.intersection(current_cap_names):
        return True
    return False


def summarize_active_tool_context(context: ActiveToolContext) -> str:
    parts: list[str] = []
    if context.task_summary:
        parts.append(f"Task: {context.task_summary}")
    if context.active_tools:
        parts.append(f"Tools: {', '.join(context.active_tools)}")
    if context.active_capabilities:
        parts.append(f"Capabilities: {', '.join(context.active_capabilities)}")
    if context.active_mastery_packs:
        parts.append(f"Mastery packs: {', '.join(context.active_mastery_packs)}")
    if context.active_runtimes:
        parts.append(f"Runtimes: {', '.join(context.active_runtimes)}")
    if context.active_governance_constraints:
        parts.append(f"Governance: {', '.join(context.active_governance_constraints)}")
    return "; ".join(parts) if parts else "No active context"
