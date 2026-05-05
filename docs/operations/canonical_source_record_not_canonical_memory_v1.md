# Canonical Source Record ≠ Canonical Memory — Doctrine v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
"Canonical" in CanonicalSourceRecord means normalized schema and format. It does NOT mean universal truth or global canon. Every canonical record starts as instance memory. Global promotion is a separate, gated process. This naming clarification prevents scope creep.

## Details
### The Naming Problem
- "Canonical" is overloaded — it can mean "standard format" or "authoritative truth"
- CanonicalSourceRecord uses the first meaning: a standard, normalized schema
- Without this clarification, developers may assume canonical records are global truth
- This assumption leads to premature promotion and scope violations

### What "Canonical" Means Here
- The record follows a defined, consistent schema (CanonicalSourceRecord)
- Fields are normalized to predictable types and formats
- The record is machine-parseable and comparable across backends
- Multiple backends extracting the same source produce schema-compatible output
- The format is canonical; the content is scoped

### What "Canonical" Does NOT Mean Here
- The content is not universal truth
- The content is not automatically global
- The content is not authoritative beyond its source instance
- The content is not promoted by virtue of being in canonical format
- The record is not "more true" than non-canonical records

### Scope Lifecycle of a Canonical Record
1. Source extracted by backend → raw data
2. Raw data normalized to CanonicalSourceRecord schema → canonical format
3. Canonical record placed in staging → RAW_STAGING scope
4. Review determines memory scope → typically INSTANCE_MEMORY
5. Global promotion is a separate, explicit, founder-approved process
6. Most canonical records never leave INSTANCE_MEMORY — and that is correct

### Why This Matters
- Prevents AI agents from treating "canonical" as permission to globalize
- Prevents scope creep where instance data leaks into platform-level memory
- Maintains clear separation between format standardization and truth claims
- Protects privacy by keeping instance data at instance scope by default

## Constraints
- CanonicalSourceRecord MUST NOT be interpreted as globally authoritative
- Format canonicalization MUST NOT trigger scope promotion
- Code comments and docstrings MUST clarify "canonical = normalized format"
- Any new use of "canonical" in the codebase MUST specify which meaning is intended
- Global canon (GLOBAL_CANON scope) is a different concept from canonical format
- These two uses of "canonical" MUST NOT be conflated in documentation or code

## References
- `docs/operations/global_canon_vs_instance_memory_doctrine_v1.md` — scope hierarchy
- `docs/operations/ingest_first_review_after_lifecycle_v1.md` — lifecycle stages
- `docs/operations/canonical_source_extraction_contract_v1.md` — the extraction contract itself
