# Global Canon vs Instance Memory — Doctrine v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
Raw account data defaults to INSTANCE_MEMORY scope. CanonicalSourceRecord is a normalized format, not universal truth. Global canon requires both abstraction from instance specifics AND founder approval. Instance facts cannot go directly to global.

## Details
### 9 Memory Scopes
1. **RAW_STAGING** — unreviewed ingested data, not yet in any memory
2. **INSTANCE_MEMORY** — scoped to a specific instance (user, org, workspace)
3. **INSTANCE_ARCHIVE** — instance-scoped, retained but not actively surfaced
4. **VENTURE_MEMORY** — shared across a single venture's agents and workflows
5. **ORG_MEMORY** — shared across all ventures in an organization
6. **PLATFORM_MEMORY** — shared across all orgs on the platform (rare)
7. **GLOBAL_CANON** — universal truth, abstracted, founder-approved
8. **TEMPLATE_LIBRARY** — reusable patterns derived from instance experience
9. **DO_NOT_PROMOTE** — terminal scope; record stays where it is permanently

### Default Scope Rules
- All raw account data → INSTANCE_MEMORY (default)
- All ingested documents → INSTANCE_MEMORY (default)
- All extracted facts from personal accounts → INSTANCE_MEMORY
- Patterns observed across instances → TEMPLATE_LIBRARY (after abstraction)
- Universal principles proven across contexts → GLOBAL_CANON (after approval)

### Promotion Path: Instance → Global
1. Raw data enters as INSTANCE_MEMORY
2. Pattern is identified across multiple instances or contexts
3. Instance-specific details are removed (abstraction step)
4. Privacy review confirms no PII or account-specific data remains
5. Founder reviews and explicitly approves global promotion
6. Record moves to GLOBAL_CANON with provenance chain intact

### CanonicalSourceRecord Clarification
- "Canonical" means normalized schema and format
- It does NOT mean the content is universal truth
- Every CanonicalSourceRecord starts in INSTANCE_MEMORY
- The record format is global; the content scope is instance

## Constraints
- Instance facts MUST NOT be promoted directly to GLOBAL_CANON
- Abstraction step MUST remove all instance-specific identifiers
- Founder approval MUST be explicit — no automated global promotion
- DO_NOT_PROMOTE is terminal — no further promotion attempts allowed
- PLATFORM_MEMORY requires extraordinary justification and founder approval
- Memory scope MUST be assigned at staging review, not at ingestion
- Scope escalation (instance → venture → org → global) must follow the chain — no skipping

## References
- `docs/operations/canonical_source_record_not_canonical_memory_v1.md` — naming doctrine
- `docs/operations/instance_specific_ingestion_policy_v1.md` — instance scoping
- `docs/operations/template_pattern_promotion_policy_v1.md` — template promotion
- `docs/operations/ingest_first_review_after_lifecycle_v1.md` — lifecycle stages
