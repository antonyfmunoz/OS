# Source Ingestion Staging Layer — Policy v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
All raw ingested data lives in staging until explicitly promoted. Staging is the mandatory holding zone between ingestion and memory placement.

## Details
### Staging Behavior
- Raw data enters staging immediately after ingestion and normalization
- No automatic promotion — every record requires a review decision
- Staging is queryable but not part of active memory or canon
- Records remain in staging indefinitely until reviewed

### Validation Requirements
- **Coverage validation** — confirm all expected fields/sections were captured before normalization
- **Parity validation** — if multiple backends can extract the same source, compare outputs for consistency
- **Schema validation** — normalized record must conform to CanonicalSourceRecord schema
- **Source provenance** — backend, timestamp, auth context, and extraction method recorded

### Review Outcomes (5 Promotion Paths)
1. **INSTANCE_MEMORY** — promote to instance-scoped memory (default for account-specific data)
2. **ARCHIVE** — retain for reference but do not surface in active queries
3. **DEFER** — not ready to decide; leave in staging with a review-after date
4. **REQUIRES_FOUNDER_DECISION** — escalate; material is ambiguous or high-impact
5. **DO_NOT_PROMOTE** — terminal; record stays in staging permanently, never surfaces

### Staging Metadata
- `ingested_at` — UTC timestamp of raw capture
- `backend_id` — which backend performed extraction
- `coverage_score` — percentage of expected fields populated
- `parity_status` — PASS / FAIL / NOT_APPLICABLE (single-backend sources)
- `review_status` — PENDING / REVIEWED / ESCALATED
- `promotion_path` — one of the 5 outcomes above, null until reviewed

## Constraints
- Staging records MUST NOT appear in active memory queries
- Promotion MUST NOT occur without review_status = REVIEWED
- Coverage score below 80% triggers manual inspection before normalization
- Parity failures block promotion until discrepancy is resolved
- No batch promotions — each record reviewed individually unless explicitly batched by founder

## References
- `docs/operations/ingest_first_review_after_lifecycle_v1.md` — lifecycle stages
- `docs/operations/extraction_backend_parity_doctrine_v1.md` — parity validation
- `docs/operations/canonical_source_extraction_contract_v1.md` — extraction contract
