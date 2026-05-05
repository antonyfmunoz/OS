# Google Workspace Ingestion Result Schema v1

**Date**: 2026-05-04
**Phase**: 93R.1 — Bind Existing Local Bridge to Work Order Contract v1
**Purpose**: Define the required structure for results returned by Google Workspace ingestion work orders.

---

## Schema Version

| Field | Value |
|-------|-------|
| Schema ID | `gws_ingestion_result_v1` |
| Compatible work order types | `GOOGLE_WORKSPACE_DISCOVERY`, `GOOGLE_DOCS_READ_EXPORT` |
| Transport | JSON via HTTP POST to `/work-order-result` |
| Max payload size | 10MB (text results). Binary evidence via `tailscale file cp`. |

---

## Result Fields

### Core Identity (fields 1-4)

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 1 | `work_order_id` | str | YES | Links this result to the originating work order. Format: `wo_{identifier}` |
| 2 | `result_id` | str | YES | Unique result identifier. Format: `result_{work_order_id}_{timestamp}` |
| 3 | `schema_version` | str | YES | Schema this result conforms to. Value: `gws_ingestion_result_v1` |
| 4 | `executing_node` | str | YES | Node that produced this result. Value: `antony-workstation` |

### Execution Metadata (fields 5-8)

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 5 | `execution_start` | str (ISO 8601) | YES | When execution began |
| 6 | `execution_end` | str (ISO 8601) | YES | When execution completed |
| 7 | `execution_duration_minutes` | int | YES | Wall-clock duration (including approval waits) |
| 8 | `status` | str | YES | `COMPLETE` / `PARTIAL` / `FAILED` |

### Discovery Results (fields 9-12)

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 9 | `folder_tree` | object | YES | Nested JSON representing Google Drive folder hierarchy. Each node: `{"name": str, "id": str, "type": "folder", "children": [...], "doc_count": int}` |
| 10 | `document_inventory` | list[object] | YES | Flat list of all discovered documents. Each entry: see Document Inventory Entry below. |
| 11 | `total_folders_discovered` | int | YES | Count of unique folders found |
| 12 | `total_documents_discovered` | int | YES | Count of unique documents found |

### Read/Export Results (fields 13-15)

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 13 | `documents_read` | list[object] | YES | Documents whose content was read. Each entry: see Document Read Entry below. Empty list if no reads were approved. |
| 14 | `documents_exported` | list[object] | CONDITIONAL | Documents that were exported/downloaded. Each entry: see Document Export Entry below. Only present if exports were approved. |
| 15 | `documents_skipped` | list[object] | YES | Documents that were not read (denied, skipped, or not requested). Each entry: `{"title": str, "folder": str, "reason": str}` |

### Categorization (fields 16-17)

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 16 | `sensitivity_flags` | list[object] | YES | Documents flagged as potentially sensitive. Each entry: `{"title": str, "folder": str, "sensitivity_reason": str, "recommended_level": str}` |
| 17 | `venture_relevance_tags` | list[object] | YES | Per-document mapping to Munoz Conglomerate ventures. Each entry: `{"title": str, "ventures": list[str], "relevance_notes": str}` |

### Evidence (fields 18-19)

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 18 | `evidence_paths` | list[str] | CONDITIONAL | Local file paths to screenshot evidence. Only required if `evidence_required=true` on the work order. |
| 19 | `evidence_transferred` | bool | CONDITIONAL | Whether evidence files have been transferred to VPS via `tailscale file cp`. |

### Safety and Audit (fields 20-22)

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 20 | `safety_confirmation` | object | YES | Explicit attestation. See Safety Confirmation below. |
| 21 | `approval_log` | list[object] | YES | Every approval request, response, and timestamp. Each entry: see Approval Log Entry below. |
| 22 | `audit_notes` | list[str] | YES | Timestamped log of all actions taken during execution. Same format as work order `audit_notes`. |

---

## Nested Object Schemas

### Document Inventory Entry

```json
{
    "title": "Document Title",
    "document_id": "google_doc_id_or_null",
    "type": "document | spreadsheet | presentation | form | pdf | image | video | other",
    "folder": "Parent Folder Name",
    "folder_path": "My Drive/Folder/Subfolder",
    "owner": "owner@email.com",
    "last_modified": "2026-05-01T12:00:00Z",
    "created": "2025-01-15T08:00:00Z",
    "size_bytes": 12345,
    "shared": true,
    "sensitivity_flag": "none | private | sensitive"
}
```

### Document Read Entry

```json
{
    "title": "Document Title",
    "document_id": "google_doc_id",
    "folder_path": "My Drive/Folder/Subfolder",
    "content_summary": "2-5 sentence summary of document content",
    "content_length_chars": 15000,
    "key_topics": ["topic1", "topic2"],
    "venture_relevance": ["Initiate Arena", "Lyfe Institute"],
    "sensitivity_assessment": "none | private | sensitive",
    "read_approved_by": "founder",
    "read_approved_at": "2026-05-04T10:05:30Z"
}
```

### Document Export Entry

```json
{
    "title": "Document Title",
    "document_id": "google_doc_id",
    "export_format": "pdf | txt | html | csv",
    "export_path_local": "~/eos_work_orders/evidence/wo_gws_001/exports/filename.pdf",
    "export_size_bytes": 45000,
    "export_approved_by": "founder",
    "export_approved_at": "2026-05-04T10:10:00Z",
    "transferred_to_vps": false
}
```

### Safety Confirmation

```json
{
    "no_documents_edited": true,
    "no_files_deleted": true,
    "no_permissions_changed": true,
    "no_emails_sent": true,
    "no_dms_sent": true,
    "no_posts_made": true,
    "no_credentials_captured": true,
    "no_payments_processed": true,
    "no_unapproved_reads": true,
    "all_actions_logged": true,
    "attested_by": "local-worker",
    "attested_at": "2026-05-04T11:00:00Z"
}
```

### Approval Log Entry

```json
{
    "approval_id": "appr_001",
    "action_requested": "Read document 'Coaching Frameworks Overview' in folder 'Lyfe Institute'",
    "requested_at": "2026-05-04T10:05:00Z",
    "response": "APPROVED | DENIED",
    "responded_at": "2026-05-04T10:05:30Z",
    "responded_by": "founder",
    "response_channel": "discord"
}
```

---

## Validation Rules

A result is valid if and only if:

| # | Rule | Error if violated |
|---|------|-------------------|
| 1 | `work_order_id` matches the originating work order | `RESULT_MISMATCH` |
| 2 | `schema_version` equals `gws_ingestion_result_v1` | `SCHEMA_MISMATCH` |
| 3 | `execution_start` < `execution_end` | `INVALID_TIMESTAMPS` |
| 4 | `status` is one of `COMPLETE`, `PARTIAL`, `FAILED` | `INVALID_STATUS` |
| 5 | `folder_tree` is a non-empty object | `EMPTY_DISCOVERY` |
| 6 | `document_inventory` is a list (may be empty if Drive is empty) | `INVALID_INVENTORY` |
| 7 | `total_folders_discovered` >= 0 | `NEGATIVE_COUNT` |
| 8 | `total_documents_discovered` >= 0 | `NEGATIVE_COUNT` |
| 9 | Every entry in `documents_read` has a matching `APPROVED` entry in `approval_log` | `UNAPPROVED_READ` |
| 10 | `safety_confirmation` has all 10 boolean fields set to `true` | `SAFETY_VIOLATION` |
| 11 | `audit_notes` is a non-empty list | `NO_AUDIT_TRAIL` |
| 12 | If `evidence_required=true` on work order, `evidence_paths` is non-empty | `MISSING_EVIDENCE` |

---

## Result Status Definitions

| Status | Meaning | When to use |
|--------|---------|-------------|
| `COMPLETE` | All expected outputs produced, all Tier 1 targets discovered, safety confirmed | Full discovery completed, all approved reads completed |
| `PARTIAL` | Some outputs produced but not all | Discovery completed but some reads denied or skipped, or execution timed out |
| `FAILED` | No usable outputs | Browser failed to load, Google login expired, bridge disconnected, or critical error |

---

## Transport

### Via HTTP Bridge

```
POST http://100.77.233.50:8765/work-order-result
Content-Type: application/json

{
    "work_order_id": "wo_gws_001_discovery",
    "result_id": "result_wo_gws_001_discovery_20260504T110000Z",
    "schema_version": "gws_ingestion_result_v1",
    ...all fields...
}
```

### VPS Storage

Result JSON is written to:
- `docs/operations/results/wo_gws_001_discovery_result.json`

Evidence files (if transferred) are stored at:
- `docs/operations/results/evidence/wo_gws_001/`

### Size Limits

| Content | Limit | If exceeded |
|---------|-------|-------------|
| Result JSON payload | 10 MB | Split into multiple POSTs with `part_number` field |
| Individual evidence file | 100 KB inline (base64) | Use `tailscale file cp` instead |
| Total evidence per work order | 500 MB | Transfer in batches via `tailscale file cp` |
