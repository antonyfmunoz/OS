# TME Doctrine: No Tool Use Without Mastery

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Core Rule

A tool must not be used in any worker execution unless TME has verified
a complete, fresh, up-to-date Tool Mastery Pack for that tool.

This is not advisory. This is a gate.

## What "complete" means

A mastery pack must contain at minimum:
- Authentication patterns
- Rate limit documentation
- Error codes and handling
- SDK idioms
- Anti-patterns
- Design intent
- Gotchas / edge cases

## What "fresh" means

Freshness is evaluated against staleness thresholds by tool speed category:
- **Fast** (14 days): Tools with frequent API changes (e.g., Claude Code CLI)
- **Medium** (45 days): Most SaaS tools
- **Stable** (90 days): Mature platforms
- **Slow** (120 days): Legacy or rarely-changing tools

## What "up-to-date" means

The pack must reflect the tool's current version and behavior.
A pack researched against v1 of an API is not valid for v2.

## Exceptions

The founder may explicitly waive the mastery requirement.
A waiver is logged in the `MasteryAssuranceDecision` and does not
set a precedent — each waiver is per-tool, per-task.

## Enforcement

`ensure_mastery_before_execution()` in `core/tool_mastery_manager/mastery_assurance.py`
produces a `MasteryAssuranceDecision` with `can_execute: bool`.

Workers check this before proceeding. If `can_execute` is False,
the decision includes `block_reason`, `action_required`, and
`recommended_flow` to resolve the gap.

## Relationship to Adapter Packages

Tool Mastery Packs are Layer 4 of the 8-layer Adapter Package.
An adapter package without a mature mastery pack cannot be promoted
to AVAILABLE or PREFERRED status.
