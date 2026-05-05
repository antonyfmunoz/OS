# TME Active Tool Context

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Purpose

Tracks active tools, capabilities, mastery packs, runtimes, and
governance constraints for an ongoing task. Persists until the task
changes or a better tool is selected.

## Module

`core/tool_mastery_manager/active_tool_context.py`

## Lifecycle

1. **Create** — `create_active_tool_context()` initializes from a
   `ToolMasteryResolution` when a new task begins
2. **Update** — `update_active_tool_context()` adds new tools/capabilities
   from a new resolution without losing existing ones
3. **Continue or Switch** — decision functions determine whether the
   current context should persist or be replaced:
   - `should_continue_context()` — True when user intent doesn't introduce
     tools outside the current context
   - `should_switch_context()` — True when new tools/capabilities are
     fully disjoint from current context

## Fields

| Field | Type | Purpose |
|-------|------|---------|
| task_id | str | Unique task identifier |
| task_summary | str | Human-readable task description |
| active_tools | list[str] | Currently active tool slugs |
| active_capabilities | list[str] | Currently active capabilities |
| active_adapter_packages | list[str] | Active adapter package refs |
| active_access_paths | list[str] | Active access path refs |
| active_mastery_packs | list[str] | Active mastery pack IDs |
| active_runtimes | list[str] | Active runtime environments |
| active_governance_constraints | list[str] | Applied constraints |
| started_at | str | ISO timestamp of context creation |
| last_updated_at | str | ISO timestamp of last update |
| reuse_until_condition | str | When to invalidate (default: task_change_or_tool_switch) |

## Design Principle

The context accumulates — tools are added, never removed within a task.
A full switch creates a new context. This prevents premature invalidation
when a user mentions a tool they're already using.
