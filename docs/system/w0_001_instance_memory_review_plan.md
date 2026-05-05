# W0-001 Instance Memory Review Plan

**Phase**: 96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Summary

The W0-001 tab-aware corpus (283,831 words, 28 docs) must be reviewed by the founder before any memory promotion occurs. All data currently defaults to INSTANCE_MEMORY. No document advances to global canon without abstraction and explicit approval.

## Review Scope

The founder reviews every ingested document and assigns one of four dispositions:

| Disposition | Meaning | Memory Scope |
|-------------|---------|-------------|
| PROMOTE | Document contains reusable knowledge worth retaining | INSTANCE_MEMORY (confirmed) |
| ARCHIVE | Document is historical/completed — retain but deprioritize | INSTANCE_ARCHIVE |
| DEFER | Document needs deeper review before decision | INSTANCE_MEMORY (pending) |
| DISCARD | Document is noise, duplicate, or outdated — exclude from memory | EPHEMERAL (purge candidate) |

## Review Constraints

- **Default scope**: INSTANCE_MEMORY. Every document starts here. No exceptions.
- **No global canon without abstraction**: Raw instance data never promotes directly to global. Must first be abstracted (raw details removed, entity names generalized, privacy reviewed).
- **Founder approval required**: No automated promotion. The founder makes every scope assignment.
- **Per-document granularity**: Each of the 28 documents gets its own disposition. Batch "approve all" is not allowed.

## Review Output

The review produces a scope assignment register:

```
document_id | document_title | tabs | words | disposition | scope | notes
```

This register becomes the authoritative record for what W0-001 data is retained, archived, deferred, or discarded.

## Review Criteria (Guidance for Founder)

- **PROMOTE if**: Document contains operational knowledge, decisions, frameworks, or patterns that will be referenced again.
- **ARCHIVE if**: Document was useful in its context but that context is complete (e.g., a completed project plan).
- **DEFER if**: Document is ambiguous — might contain value but needs closer reading.
- **DISCARD if**: Document is a draft that was superseded, a duplicate, or contains only transient information.

## Timeline

- Review is blocked on founder availability.
- No artificial deadline — quality of scope assignment matters more than speed.
- After review, the promotion pipeline in `template_promotion.py` handles the mechanical work.

## What Happens After Review

1. Documents with PROMOTE disposition remain in INSTANCE_MEMORY, confirmed.
2. Documents with ARCHIVE disposition move to INSTANCE_ARCHIVE scope.
3. Documents with DEFER disposition stay in INSTANCE_MEMORY with a PENDING flag for re-review.
4. Documents with DISCARD disposition are marked EPHEMERAL and become purge candidates.
5. Any document identified as containing a reusable pattern enters the template candidate pipeline (separate review).

## References

- `eos_ai/memory_scope.py` — scope definitions
- `eos_ai/instance_ingestion.py` — ingestion records
- `eos_ai/template_promotion.py` — promotion pipeline
- `docs/system/w0_001_ingestion_lifecycle_status_correction.md`
- `docs/system/w0_001_template_pattern_candidate_review.md`
