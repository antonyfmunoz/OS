# W0-001 Template Pattern Candidate Review

**Phase**: 96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Summary

Four patterns from the W0-001 corpus are candidates for reusable templates. None are promoted yet — all are at REQUIRES_REVIEW status. Each must pass raw detail removal, privacy review, and founder approval before becoming a template.

## Candidate Patterns

### 1. Extraction Contract Pattern

| Attribute | Value |
|-----------|-------|
| Source | W0-001 Google Docs API extraction workflow |
| Pattern | Typed contract defining source, tabs, expected output format, validation rules, and error handling for document extraction |
| Reuse potential | Any future document extraction from any backend |
| Status | REQUIRES_REVIEW |

**What makes it a template candidate**: The extraction contract used for W0-001 is not specific to Google Docs. The structure (source definition, tab enumeration, output schema, validation rules) applies to any document source.

### 2. Backend Parity Testing Pattern

| Attribute | Value |
|-----------|-------|
| Source | W0-001 API vs CU comparison methodology |
| Pattern | Reference backend produces canonical output; alternative backends are compared word-by-word with structured diff reporting |
| Reuse potential | Any multi-backend system where output equivalence matters |
| Status | REQUIRES_REVIEW |

**What makes it a template candidate**: The parity testing methodology (reference output, structured comparison, gap reporting) is backend-agnostic. Works for any scenario where two systems should produce equivalent results.

### 3. Tab-Aware Traversal Pattern

| Attribute | Value |
|-----------|-------|
| Source | W0-001 multi-tab document handling |
| Pattern | Enumerate all tabs in a document, extract each independently, reassemble with tab metadata preserved, validate no tabs lost |
| Reuse potential | Any multi-section document extraction (Google Docs tabs, Excel sheets, multi-page PDFs) |
| Status | REQUIRES_REVIEW |

**What makes it a template candidate**: Tab-aware traversal solved a real problem (prior extractions missed tabs silently). The pattern of enumerate-extract-reassemble-validate applies to any compound document format.

### 4. Canonical Record Schema

| Attribute | Value |
|-----------|-------|
| Source | W0-001 normalized extraction output |
| Pattern | Standardized record format: source metadata, content blocks, tab/section identifiers, word counts, extraction timestamp, backend identifier |
| Reuse potential | Any ingestion pipeline producing structured records from unstructured sources |
| Status | REQUIRES_REVIEW |

**What makes it a template candidate**: The canonical record schema normalizes output regardless of source format or extraction backend. Any future ingestion pipeline needs the same structure.

## Promotion Requirements

Each candidate must pass three gates before becoming a reusable template:

1. **Raw detail removal** — All W0-001-specific references (document IDs, workspace names, specific content) stripped. Template contains only the abstract pattern.
2. **Privacy review** — No personally identifiable information, no credentials, no internal URLs remain in the template.
3. **Founder approval** — The founder reviews the abstracted template and explicitly approves promotion.

## Current Status

| Candidate | Raw Detail Removal | Privacy Review | Founder Approval | Overall |
|-----------|-------------------|---------------|-----------------|---------|
| Extraction Contract | NOT STARTED | NOT STARTED | NOT STARTED | REQUIRES_REVIEW |
| Backend Parity Testing | NOT STARTED | NOT STARTED | NOT STARTED | REQUIRES_REVIEW |
| Tab-Aware Traversal | NOT STARTED | NOT STARTED | NOT STARTED | REQUIRES_REVIEW |
| Canonical Record Schema | NOT STARTED | NOT STARTED | NOT STARTED | REQUIRES_REVIEW |

## References

- `eos_ai/template_promotion.py` — promotion pipeline
- `eos_ai/memory_scope.py` — scope assignments
- `docs/operations/canonical_source_extraction_contract_v1.md`
- `docs/operations/extraction_backend_parity_doctrine_v1.md`
- `docs/system/w0_001_instance_memory_review_plan.md`
