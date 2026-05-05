# Mature Adapter Requires Tool Mastery — Doctrine v1

**Phase**: 96.6
**Status**: ACTIVE
**Date**: 2026-05-05

---

## Core Rule

A tool adapter is not mature merely because it can connect. Technical connectivity is necessary but insufficient. An adapter achieves maturity only when it includes a complete Tool Mastery Pack — expert operational knowledge that prevents silent failures, data loss, and false completeness.

## The Gap Between Connected and Mature

A basic Google Docs adapter can:
- Authenticate via OAuth2 or service account
- Call `documents.get` and receive a response
- Extract text from `document.body`
- Pass a smoke test ("got some text, no errors")

A master-level Google Docs adapter also knows:
- Documents can have tabs and child tabs
- `includeTabsContent=true` is required to see tab content
- `document.body` only contains the first tab's text
- Tab traversal must be recursive for child tabs
- Empty tabs are valid, not extraction failures
- Completeness requires per-tab validation, not just "got text"

The basic adapter produces confident but incomplete results. The master-level adapter produces verified, complete results. The difference is the Tool Mastery Pack.

## Quality Gate Enforcement

The Adapter Quality Gate includes 7 checks. Check #7 (`tool_mastery_is_mature`) validates that the mastery pack contains all 4 critical sections:

1. **completeness_requirements** — what "done" actually means
2. **failure_modes** — how the tool breaks and how to detect it
3. **anti_patterns** — mistakes that look correct but produce wrong results
4. **validation_checklist** — ordered steps proving correct operation

An adapter with `has_tool_mastery=True` but an incomplete mastery pack fails this check. The flag says "mastery exists" — the maturity check says "mastery is operationally sufficient."

## Maturity Validation

```python
def tool_mastery_is_mature(pack: ToolMasteryPack) -> bool:
    return all([
        pack.completeness_requirements,
        pack.failure_modes,
        pack.anti_patterns,
        pack.validation_checklist,
    ])
```

This is a hard gate, not a score. All 4 sections must be non-empty. Partial mastery is not mature.

## Why This Cannot Be Deferred

"We'll add mastery later" means the adapter runs in production without knowing its own failure modes. Every extraction it performs between "connected" and "mastered" is unvalidated. If the tool has traps (and most do), those traps are silently triggered on every run.

Google Docs tabs are the proof case. Without mastery, every multi-tab document extraction silently loses content. The adapter reports success. The data is incomplete. No error is raised.

## Hard Rules

- An adapter without a complete mastery pack is not promotable to production.
- `has_tool_mastery=True` with an empty pack is worse than `has_tool_mastery=False` — it creates false confidence.
- Mastery maturity is checked at promotion time via `tool_mastery_is_mature()`.
- New failure modes discovered in production must be added to the mastery pack immediately.

## References

- `eos_ai/adapter_quality_gate.py` — `evaluate_adapter_maturity()` with mastery check
- `eos_ai/adapter_engine_contracts.py` — `ToolMasteryPack` dataclass, `tool_mastery_is_mature()`
- `docs/operations/tool_mastery_pack_doctrine_v1.md` — mastery pack requirements
- `docs/operations/google_docs_tool_mastery_pack_v1.md` — reference example
- `docs/operations/adapter_quality_gate_v1.md` — full quality gate policy
