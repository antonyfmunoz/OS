# Instance-Specific Ingestion — Policy v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
Work order W0-001 is instance-specific to `antony_empyrean`. All ingested data defaults to INSTANCE_MEMORY scope. Global canon promotion is not allowed by default. Privacy classification is private.

## Details
### Instance Context
- **Instance ID**: `antony_empyrean`
- **Source system**: Google Drive / Google Docs
- **Account owner**: Antony F. Munoz (Empyrean Studios)
- **Privacy classification**: PRIVATE
- **Default memory scope**: INSTANCE_MEMORY
- **Global canon allowed**: NO (by default)

### Ingestion Characteristics
- All documents belong to a single Google account
- Content includes business plans, strategies, operational docs
- Documents may contain PII, financial data, and proprietary strategy
- Multi-tab Google Docs are expected and must be fully captured
- Drive folder structure carries organizational meaning — preserve it

### Scope Assignment Rules
- Every record from this instance → INSTANCE_MEMORY unless explicitly overridden
- No automatic promotion to VENTURE_MEMORY, ORG_MEMORY, or GLOBAL_CANON
- Template extraction allowed only after abstraction + privacy review
- Cross-instance pattern detection does not override default scope

### Promotion Path (If Needed)
1. Identify a pattern or principle worth generalizing
2. Remove all instance-specific details (names, accounts, amounts, dates)
3. Privacy review: confirm no PII, no account identifiers, no proprietary strategy
4. Abstraction review: confirm the pattern holds without instance context
5. Founder explicitly approves promotion
6. Promoted record links back to source instance for provenance

### Data Handling
- Raw documents stored as-is in staging
- Extraction follows CanonicalSourceRecord schema
- Metadata includes: source_path, doc_id, tab_count, extraction_backend, timestamp
- No content transformation beyond normalization to canonical format
- Original formatting hints preserved where schema supports it

## Constraints
- Global canon MUST NOT be created from this instance without explicit approval
- PII MUST NOT leave INSTANCE_MEMORY scope under any circumstance
- Financial data MUST NOT be promoted beyond INSTANCE_MEMORY
- Proprietary strategy documents MUST NOT be used as template source material
- All access to this instance's data requires matching auth context
- Extraction backends MUST NOT cache or retain content outside the staging layer

## References
- `docs/operations/global_canon_vs_instance_memory_doctrine_v1.md` — scope hierarchy
- `docs/operations/ingest_first_review_after_lifecycle_v1.md` — lifecycle stages
- `docs/operations/source_ingestion_staging_layer_policy_v1.md` — staging behavior
- `docs/operations/template_pattern_promotion_policy_v1.md` — template extraction rules
