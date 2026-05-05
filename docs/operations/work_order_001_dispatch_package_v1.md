# Work Order 001 — Dispatch Package v1

**Date**: 2026-05-04
**Phase**: 94R — Existing Local Bridge Healthcheck + Work Order Dispatch Readiness v1
**Dispatch Status**: READY_TO_DISPATCH_AFTER_LOCAL_HEALTHCHECK

---

> **This package is not executed until local worker healthcheck passes.**

---

## Work Order Identity

| Field | Value |
|-------|-------|
| Work Order ID | `wo_gws_001_discovery` (from work_order_001.md) or factory-generated `wo_{uuid12}` |
| Task Type | `GOOGLE_WORKSPACE_DISCOVERY` + `GOOGLE_DOCS_READ_EXPORT` (two-phase) |
| Assigned Node | `antony-workstation` |
| Created By Node | `vps-orchestrator` |

---

## Objective

Discover all Google Drive folders and documents relevant to Munoz Conglomerate ventures. Selectively read/export key documents with founder approval.

---

## Source Targets (14)

### Tier 1 — Critical (discover + request read approval)

1. Initiate Arena materials
2. Lyfe Institute documents
3. Game of Lyfe documents
4. UMH (Unleash My Hustle) materials
5. EntrepreneurOS / EOS documents
6. AI Agents documentation
7. Coaching Frameworks
8. Antony Munoz Email Sequences

### Tier 2 — High (discover + metadata unless founder approves read)

9. Content strategy / content calendar
10. Business templates
11. Automations documentation
12. Whop / course references
13. Empyrean Studio documents
14. Lyfe Spectrum materials

---

## Allowed Actions

### Phase 1 — Discovery (READ_ONLY)

| # | Action |
|---|--------|
| 1 | Navigate to Google Drive root |
| 2 | List all top-level folders |
| 3 | Open folders to view contents |
| 4 | Read folder names and document titles |
| 5 | Read document metadata (owner, modified date, type, size) |
| 6 | Count documents per folder |
| 7 | Take screenshots of folder structures |
| 8 | Record folder hierarchy as structured data |

### Phase 2 — Selective Read/Export (APPROVAL_REQUIRED per document)

| # | Action | Approval Gate |
|---|--------|---------------|
| 9 | Open specific document to read content | YES |
| 10 | Export document as PDF or plain text | YES |
| 11 | Copy text content from document | YES |
| 12 | Take screenshot of document content | YES |

---

## Blocked Actions (16 universal + 4 work-order-specific)

### Universal (enforced by WorkOrder.__post_init__)

1. edit_documents
2. delete_files
3. change_permissions
4. send_emails
5. send_dms
6. post_content
7. change_account_settings
8. capture_credentials
9. process_payments
10. subscribe_unsubscribe
11. purchase
12. install_software
13. modify_system_settings
14. autonomous_social_actions
15. promote_memory_without_governance
16. run_arbitrary_shell_commands

### Work-Order-Specific

17. Download files larger than 50MB
18. Access Google Admin Console
19. Access Gmail content (inbox, sent, drafts)
20. Access Google Calendar content

---

## Approval Requirements

| # | Action Requiring Approval | Approval Channel |
|---|--------------------------|-----------------|
| 1 | Read content of any specific document | Discord via /cc-prompt |
| 2 | Export/download any document | Discord via /cc-prompt |
| 3 | Access any folder marked SENSITIVE | Discord via /cc-prompt |
| 4 | Take screenshot of document content | Discord via /cc-prompt |
| 5 | Batch approval: read all docs in a folder | Discord via /cc-prompt |

---

## Expected Outputs

| # | Output | Format | Required |
|---|--------|--------|----------|
| 1 | Google Drive folder tree | JSON | YES |
| 2 | Document inventory with metadata | JSON | YES |
| 3 | Folder screenshots | PNG | YES |
| 4 | Read document summaries | JSON | YES (for approved docs) |
| 5 | Exported document files | PDF/TXT | CONDITIONAL |
| 6 | Sensitivity flags | JSON | YES |
| 7 | Venture relevance tags | JSON | YES |
| 8 | Safety confirmation | JSON | YES |
| 9 | Approval log | JSON | YES |

---

## Result Delivery

| Field | Value |
|-------|-------|
| Result Schema | `gws_ingestion_result_v1` |
| Result Endpoint | `POST http://100.77.233.50:8765/work-order-result` (Phase 94L adds this) |
| VPS Result Path | `docs/operations/results/wo_gws_001_discovery_result.json` |
| Local Result Path | `~/eos_work_orders/wo_gws_001_discovery_result.json` |
| Evidence Path | `~/eos_work_orders/evidence/wo_gws_001/` |
| Evidence Transfer | `tailscale file cp` or base64 if <100KB |

---

## Safety Confirmation Required

The local worker must produce a safety attestation confirming:

- No documents edited
- No files deleted
- No permissions changed
- No emails sent
- No DMs sent
- No posts made
- No credentials captured
- No payments processed
- No unapproved reads performed
- All actions logged

---

## Authority Configuration

| Field | Value |
|-------|-------|
| Authority Mode (Phase 1) | READ_ONLY |
| Authority Mode (Phase 2) | APPROVAL_REQUIRED |
| Sensitivity Level | MIXED |
| Evidence Required | true |
| Timeout | 120 minutes (approval pauses not counted) |

---

## Dispatch Prerequisites

| # | Prerequisite | Status |
|---|-------------|--------|
| 1 | VPS healthcheck complete | PASS (16/17, 1 NEEDS_LOCAL_VERIFICATION) |
| 2 | Local healthcheck complete | PENDING — founder must run |
| 3 | Work order contract importable | PASS |
| 4 | Factory builds valid work order | PASS |
| 5 | Result schema documented | PASS |
| 6 | Binding plan documented | PASS |
| 7 | `/work-order` endpoint on local | NOT YET IMPLEMENTED (Phase 94L) |
| 8 | `dispatch_work_order()` on VPS | NOT YET IMPLEMENTED (Phase 94L) |
| 9 | `/work-order-result` endpoint on VPS | NOT YET IMPLEMENTED (Phase 94L) |

---

## Dispatch Readiness

**Status**: `READY_TO_DISPATCH_AFTER_LOCAL_HEALTHCHECK`

This package contains the complete specification for Work Order 001. It is ready to be converted to a JSON payload and dispatched via the local bridge once:

1. Founder runs local healthcheck (all CRITICAL checks pass)
2. Phase 94L implements the 3 missing endpoints (`/work-order`, `dispatch_work_order()`, `/work-order-result`)
3. VPS confirms bridge health: `curl -s http://100.74.199.102:8766/health` returns OK

**This package is not executed until all prerequisites are met.**
