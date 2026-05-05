# TME Mastery Assurance Gate

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Purpose

The Mastery Assurance Gate evaluates whether a tool's mastery pack
meets the bar for worker execution. It is a pure decision function
with no I/O — callers supply pack metadata and text content.

## Module

`core/tool_mastery_manager/mastery_assurance.py`

## Decision Statuses

| Status | can_execute | Meaning |
|--------|-------------|---------|
| ASSURED | True | Pack is fresh, complete, and meets quality tier |
| WAIVED_BY_FOUNDER | True | Founder explicitly waived the requirement |
| MISSING_PACK | False | No mastery pack exists |
| STALE_PACK | False | Pack exists but exceeds staleness threshold |
| INCOMPLETE_PACK | False | Pack exists but missing required sections |
| QUALITY_BELOW_THRESHOLD | False | Pack exists but below minimum character count for its tier |
| BLOCKED | False | Default — no evaluation has run |

## Recommended Flows

When a pack is not ASSURED, the gate recommends a flow:

| Flow | When |
|------|------|
| CREATE_FLOW | Pack does not exist |
| RE_RESEARCH_FLOW | Pack is stale or has no date |
| INCREMENTAL_UPDATE_FLOW | Pack is incomplete or below quality threshold |
| PROCEED | Pack passes all checks |

## Quality Tiers

| Tier | Minimum Characters |
|------|--------------------|
| Critical | 20,000 |
| Core | 15,000 |
| Standard | 8,000 |
| Light | 5,000 |

## Integration

The Control Plane calls `ensure_mastery_before_tool_execution()` in
`core/action_system/tme.py`, which wraps the gate with error handling
and returns a dict. Workers inspect `can_execute` before proceeding.

## Alias Resolution

Tool names are normalized via `normalize_tool_name()`.
Aliases (e.g., "postgres" → "neon_postgres") are resolved before
any evaluation.
