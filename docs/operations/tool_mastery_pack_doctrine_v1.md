# Tool Mastery Pack — Doctrine v1

**Phase**: 96.6
**Status**: ACTIVE
**Date**: 2026-05-05

---

## Core Rule

A Tool Mastery Pack encodes expert operational knowledge that prevents amateur tool use. It is Layer 4 of the 8-layer Adapter Package — an internal component of the Adapter Engine, not a separate system. A mastery pack that exists but lacks critical sections is operationally incomplete and blocks adapter promotion.

## What a Mastery Pack Must Include

- **Tool-specific data model** — entities, relationships, quirks (e.g., Google Docs tabs, child tabs)
- **Hidden/non-obvious features** — capabilities not prominent in vendor docs
- **API defaults and traps** — default parameter values that cause silent data loss
- **Pagination and rate limits** — batch sizes, throttling behavior, quota scopes
- **Auth and scopes** — minimum required scopes, scope escalation patterns
- **Export limitations** — format restrictions, size limits, lossy conversions
- **UI quirks** — behavior differences between API and UI
- **Failure modes** — what breaks, how it breaks, symptoms, remediation
- **Version changes** — breaking changes across API versions
- **Completeness tests** — how to verify all data was extracted
- **Anti-patterns** — common mistakes that look correct but produce incomplete results
- **Recovery playbooks** — what to do when things go wrong
- **Expert workflows** — optimal sequences for complex operations
- **Validation checklist** — step-by-step verification of correct usage

## 4 Critical Sections for Maturity

A mastery pack is not mature unless it has ALL of these:

1. **completeness_requirements** — what "complete" means for this tool
2. **failure_modes** — documented ways the tool fails, with symptoms and fixes
3. **anti_patterns** — mistakes that produce wrong results silently
4. **validation_checklist** — ordered checks proving correct operation

The `tool_mastery_is_mature()` helper validates all 4. An adapter with `has_tool_mastery=True` but an empty or incomplete mastery pack fails the maturity check and is not promotable.

## Why This Matters

Example: Google Docs. A basic adapter calls `documents.get` and extracts text. It works. It passes smoke tests. But it silently misses tab content because `includeTabsContent=true` was not set. The extraction looks complete — one document, some text — but entire tabs of content are missing.

A Tool Mastery Pack for Google Docs encodes this knowledge: tabs exist, child tabs exist, `includeTabsContent=true` is required, tab traversal must be recursive, completeness requires per-tab validation. Without this mastery, the adapter is a liability that produces confident but incomplete results.

## Mastery Pack Is Not Documentation

- Vendor READMEs describe happy paths. Mastery packs encode operational reality.
- API reference lists parameters. Mastery packs explain which defaults are traps.
- Tutorials show basic usage. Mastery packs show expert-level completeness.

A mastery pack that is a copy of vendor docs fails the quality gate.

## Hard Rules

- A mastery pack without completeness_requirements, failure_modes, anti_patterns, or validation_checklist is incomplete.
- An incomplete mastery pack blocks adapter promotion even if all other checks pass.
- Mastery packs live inside adapters (Layer 4), not alongside them.
- Mastery is not static — update when new failure modes are discovered.

## References

- `eos_ai/adapter_engine_contracts.py` — ToolMasteryPack dataclass
- `eos_ai/adapter_quality_gate.py` — maturity validation
- `docs/operations/google_docs_tool_mastery_pack_v1.md` — reference example
- `docs/operations/mature_adapter_requires_tool_mastery_v1.md` — maturity doctrine
- `docs/operations/adapter_package_doctrine_v1.md` — 8-layer bundle
