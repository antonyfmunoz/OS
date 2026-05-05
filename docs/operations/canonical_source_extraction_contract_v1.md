# Canonical Source Extraction Contract v1

**Phase**: 96.0
**Date**: 2026-05-04
**Status**: ACTIVE

---

## Purpose

Every extraction backend (API, CLI, Computer Use) must produce
the same canonical output. This document defines that output.

## DocumentSourceRecord

Every extracted document produces one `DocumentSourceRecord`:

| Field | Type | Required |
|-------|------|----------|
| file_id | string | YES |
| title | string | YES |
| mime_type | string | YES |
| source_account | string | recommended |
| web_view_link | string | recommended |
| modified_time | ISO datetime | recommended |
| created_time | ISO datetime | recommended |
| owner_metadata | dict | recommended |
| parent_metadata | dict | recommended |
| backend_type | ExtractionBackendType | YES |
| extraction_timestamp | ISO datetime | YES (auto-set) |
| extraction_method | string | YES |
| extraction_coverage_status | ExtractionCoverageStatus | YES |
| tabs | list[TabSourceRecord] | YES |
| provenance | ProvenanceRecord | YES |

## TabSourceRecord

Every tab within a document produces one `TabSourceRecord`:

| Field | Type | Required |
|-------|------|----------|
| tab_id | string | YES |
| tab_title | string | YES |
| tab_path | string | YES (hierarchical) |
| parent_tab_id | string | null for top-level |
| tab_order | int | YES |
| is_empty | bool | YES |
| text_content | string | YES (empty string for empty tabs) |
| word_count | int | YES |
| character_count | int | YES |
| extraction_coverage_status | ExtractionCoverageStatus | YES |
| extraction_notes | string | optional |

## ProvenanceRecord

Every extraction must record how content was obtained:

| Field | Type | Required |
|-------|------|----------|
| backend_type | ExtractionBackendType | YES |
| extraction_method | string | YES |
| source_observed_from | string | YES |
| content_came_from_api | bool | YES |
| content_came_from_cli | bool | YES |
| content_came_from_visible_ui | bool | YES |
| any_content_inaccessible | bool | YES |
| inaccessible_reason | string | if inaccessible |
| fallback_used | bool | YES |
| fallback_backend | ExtractionBackendType | if fallback used |

## Completeness Validation Rules

A record is NOT complete if:
1. `file_id` is missing
2. `title` is missing
3. `tabs` is empty (no tabs extracted)
4. `extraction_coverage_status` is UNKNOWN
5. `provenance` is missing
6. Any tab claims COMPLETE but has 0 words and is not marked empty

## Coverage Status Values

| Status | Meaning |
|--------|---------|
| COMPLETE | All content captured per contract |
| PARTIAL | Some content captured, gaps exist |
| FAILED | Extraction attempted and failed entirely |
| BLOCKED | Known blocker prevents extraction |
| UNKNOWN | Not yet evaluated |

## Hard Rule

No backend-specific schema drift.
API/CLI/CU outputs must normalize into this same record format.
If a backend cannot fill a required field, it must set the
appropriate coverage status and explain in extraction_notes.
