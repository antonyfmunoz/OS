# TME UMH Substrate Doctrine v1

**Phase**: TME Scope Correction (pre-96.7)
**Status**: ACTIVE
**Date**: 2026-05-05

---

## Core Rule

The Tool Mastery Engine (TME) is a UMH substrate subsystem, not an EOS product subsystem. TME governs every external tool, SaaS, API, adapter, runtime, and capability UMH touches. EOS, LYFEOS, CreatorOS, and other platforms are consumers of TME — they do not own it.

## What TME Is

TME is the subsystem that creates, maintains, validates, and serves expert-level operational knowledge (Tool Mastery Packs) about external tools. It answers one question: "Does UMH know how to use this tool at creator level, right now?"

TME produces structured mastery packs containing:
- Best practices, workflows, and expert patterns
- Failure modes, anti-patterns, and traps
- Completeness requirements and validation checklists
- API defaults that cause silent data loss
- Recovery playbooks and edge cases

## What TME Is Not

- TME is not the Adapter Engine. The Adapter Engine integrates tools operationally. TME provides the knowledge that adapters need.
- TME is not a documentation system. TME encodes operational expertise — what breaks, what's hidden, what defaults are traps.
- TME is not EOS-specific. TME's 19-section research protocol, staleness thresholds, quality tiers, and decision tree are UMH-level concerns.

## Platform Consumer Model

Any platform built on UMH can consume TME outputs:

| Platform | How It Consumes TME |
|----------|-------------------|
| EOS | Loads tool skills via decision tree, syncs to Neon, populates Adapter Package Layer 4 |
| LYFEOS | (future) Can load same tool skills via same decision tree |
| CreatorOS | (future) Can load same tool skills via same decision tree |
| Custom UMH runtimes | (future) Can query TME via Control Plane's `ensure_tool_mastery()` |

## Allowed Phrasing

- "TME is a UMH substrate subsystem."
- "EOS is one platform consumer of TME."
- "TME-produced tool skills can be used by EOS workers, Adapter Packages, and other UMH runtimes."
- "TME is part of UMH and can be projected into EOS workflows."

## Disallowed Phrasing

- "TME is an EOS subsystem." (incorrect — TME is UMH substrate)
- "EOS owns TME." (incorrect — UMH substrate owns TME)
- "TME governs every build in EOS." (too narrow — TME governs all UMH tool usage)
- "TME is for EOS only." (incorrect — TME is platform-independent)

## Current Implementation Note

TME code currently lives under `/opt/OS/` alongside EOS code, and some paths use `eos_ai/substrate/` namespace. This is a legacy implementation path — TME logically belongs to UMH substrate. No directory renaming was performed in this correction phase. The semantic correction is immediate; the namespace correction is deferred.

## Hard Rules

- TME scope is UMH, not EOS.
- Any new TME documentation must use UMH framing, not EOS framing.
- Individual tool skills may have an "EOS Usage Patterns" section — this is correct because EOS is a valid consumer with specific integration patterns.
- TME's decision tree, create flow, re-research flow, and quality tiers apply to all UMH platform consumers equally.

## Phase 96.7A Additions

TME now has three enforcement subsystems:

1. **Mastery Assurance Gate** (`core/tool_mastery_manager/mastery_assurance.py`) — blocks tool execution without a fresh, complete, quality-sufficient mastery pack. Produces `MasteryAssuranceDecision` with `can_execute: bool`.

2. **Natural Language Resolver** (`core/tool_mastery_manager/tool_mastery_resolver.py`) — detects tools, capabilities, and runtimes from natural language text without slash commands.

3. **Active Tool Context** (`core/tool_mastery_manager/active_tool_context.py`) — tracks active tools/capabilities/runtimes during a task, persists until task change or tool switch.

All three are UMH substrate subsystems. They are consumed by EOS via `core/action_system/tme.py`.

## References

- `skills/meta/tool_mastery_engine/SKILL.md` — TME engine skill (v4.0)
- `docs/system/tool_mastery_engine_system.md` — TME system reference
- `docs/system/tme_scope_correction_umh_report_v1.md` — correction report
- `docs/operations/tme_adapter_engine_relationship_v1.md` — TME/Adapter Engine relationship
- `docs/operations/tme_no_tool_use_without_mastery_v1.md` — no-use-without-mastery doctrine
- `docs/operations/tme_mastery_assurance_gate_v1.md` — gate mechanics
- `docs/operations/tme_natural_language_resolver_v1.md` — NL resolver
- `docs/operations/tme_active_tool_context_v1.md` — active context
- `docs/operations/tme_adapter_package_relationship_v1.md` — TME ↔ Adapter Package
- `docs/system/phase967a_tme_mastery_assurance_resolver_report.md` — Phase 96.7A report
