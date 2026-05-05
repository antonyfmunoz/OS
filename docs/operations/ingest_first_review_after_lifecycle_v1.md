# Ingest-First / Review-After Lifecycle — Doctrine v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
Raw data enters the system immediately upon discovery. Review gates control promotion, not ingestion. No data is lost or filtered at intake.

## Details
### 11 Lifecycle Stages
1. **DISCOVERED** — source identified, not yet ingested
2. **INGESTION_QUEUED** — scheduled for raw capture
3. **INGESTED_RAW** — raw record written, immutable from this point
4. **SAFETY_CHECKED** — safety/scope/auth validation passed
5. **NORMALIZED** — converted to CanonicalSourceRecord format
6. **STAGED** — sitting in staging layer, awaiting review
7. **REVIEW_PENDING** — review gate active, blocking promotion
8. **REVIEWED** — human or automated review completed
9. **PROMOTED** — moved to target memory scope (instance or global)
10. **ARCHIVED** — retained but not actively referenced
11. **REQUIRES_FOUNDER_DECISION** — escalated; cannot proceed without founder input

### Principles
- Review gates block promotion, never ingestion
- Raw records are immutable once written — no edits, no deletes
- Interpretations (summaries, extractions, tags) are stored separately from raw
- Safety, scope, and auth checks run before ingestion begins
- Promotion from staging requires explicit review completion
- Memory promotion (instance → global) requires founder sign-off
- Every stage transition is logged with timestamp and actor

## Constraints
- Raw records MUST NOT be modified after INGESTED_RAW
- Automated systems MUST NOT promote past STAGED without review
- No stage may be skipped — transitions are sequential
- REQUIRES_FOUNDER_DECISION is terminal until founder acts
- Interpretations MUST NOT be stored in the raw record itself
- Safety check failure halts the pipeline — does not silently drop

## References
- `docs/operations/source_ingestion_staging_layer_policy_v1.md` — staging layer details
- `docs/operations/global_canon_vs_instance_memory_doctrine_v1.md` — promotion rules
- `docs/operations/canonical_source_record_not_canonical_memory_v1.md` — naming clarification
