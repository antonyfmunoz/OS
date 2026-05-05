# Work Order 001 — Google Workspace Discovery + Selective Read/Export

**Work Order ID**: `wo_gws_001_discovery`
**Date**: 2026-05-04
**Phase**: 93R.1 — Bind Existing Local Bridge to Work Order Contract v1
**Status**: CREATED

---

## Work Order Fields

| Field | Value |
|-------|-------|
| `work_order_id` | `wo_gws_001_discovery` |
| `created_by_node` | `vps-orchestrator` |
| `assigned_to_node` | `antony-workstation` |
| `task_type` | `GOOGLE_WORKSPACE_DISCOVERY` + `GOOGLE_DOCS_READ_EXPORT` (two-phase) |
| `objective` | Discover all Google Drive folders and documents relevant to Munoz Conglomerate ventures. Selectively read/export key documents with founder approval. |
| `authority_mode` | Phase 1: `READ_ONLY` (discovery). Phase 2: `APPROVAL_REQUIRED` (read/export). |
| `sensitivity_level` | `MIXED` — contains both public and private business data |
| `evidence_required` | `true` — screenshot evidence of folder structures discovered |
| `timeout_minutes` | `120` (2 hours — founder approval pauses do not count against timeout) |
| `created_at` | `2026-05-04T00:00:00Z` |
| `status` | `CREATED` |
| `result_path` | `docs/operations/results/wo_gws_001_discovery_result.json` |
| `audit_notes` | `["2026-05-04T00:00:00Z | CREATED by vps-orchestrator — Phase 93R.1 first work order"]` |

---

## Source Targets

These are the Google Drive locations and document categories to discover and optionally read.

### Tier 1 — Critical (discover + request read approval)

| # | Source Target | Expected Location | Why Critical |
|---|--------------|-------------------|-------------|
| 1 | Initiate Arena materials | Google Drive folder or docs | Primary revenue product — offer lock depends on these |
| 2 | Lyfe Institute documents | Google Drive folder | Parent entity for Initiate Arena |
| 3 | Game of Lyfe documents | Google Drive folder | Next offer rung after Initiate Arena |
| 4 | UMH (Unleash My Hustle) materials | Google Drive folder or docs | Legacy content that may inform current strategy |
| 5 | EntrepreneurOS / EOS documents | Google Drive folder | Platform strategy and architecture docs |
| 6 | AI Agents documentation | Google Drive folder or docs | Agent designs, prompts, configurations |
| 7 | Coaching Frameworks | Google Drive folder | Delivery methodology for coaching offers |
| 8 | Antony Munoz Email Sequences | Google Drive or Docs | Sales copy, nurture sequences, outreach templates |

### Tier 2 — High (discover + metadata only unless founder approves)

| # | Source Target | Expected Location | Why High |
|---|--------------|-------------------|---------|
| 9 | Content strategy / content calendar | Google Sheets or Docs | Marketing execution planning |
| 10 | Business templates | Google Drive folder | Reusable assets for offers |
| 11 | Automations documentation | Google Docs | Workflow and system documentation |
| 12 | Whop / course references | Google Docs or Sheets | Platform-specific configuration and content |
| 13 | Empyrean Studio documents | Google Drive folder | Service business strategy |
| 14 | Lyfe Spectrum materials | Google Drive folder | Product line documentation |

### Tier 3 — Medium (discover only, no read)

| # | Source Target | Expected Location | Why Medium |
|---|--------------|-------------------|-----------|
| 15 | Personal documents | Google Drive | Awareness of what exists — do not read without explicit approval |
| 16 | Shared-with-me documents | Google Drive | Third-party content — metadata only |
| 17 | Google Sheets (financial) | Google Sheets | Awareness of financial data locations — do not read |

---

## Allowed Actions

These actions are permitted during execution of this work order.

### Phase 1 — Discovery (READ_ONLY)

| # | Action | Scope |
|---|--------|-------|
| 1 | Navigate to Google Drive root | Browser |
| 2 | List all top-level folders | Google Drive |
| 3 | Open folders to view contents | Google Drive |
| 4 | Read folder names and document titles | Google Drive |
| 5 | Read document metadata (owner, modified date, type, size) | Google Drive |
| 6 | Count documents per folder | Google Drive |
| 7 | Take screenshots of folder structures | Browser — as evidence |
| 8 | Record folder hierarchy as structured data | Local notes |

### Phase 2 — Selective Read/Export (APPROVAL_REQUIRED)

| # | Action | Scope | Approval Gate |
|---|--------|-------|---------------|
| 9 | Open specific document to read content | Google Docs | YES — per document or per folder |
| 10 | Export document as PDF or plain text | Google Docs | YES — per document |
| 11 | Copy text content from document | Google Docs | YES — per document |
| 12 | Take screenshot of document content | Browser | YES — per document |

---

## Blocked Actions (Universal + Work-Order-Specific)

These actions are NEVER permitted during this work order.

| # | Blocked Action | Category |
|---|---------------|----------|
| 1 | Edit or modify any Google document | Destructive |
| 2 | Delete any file or folder | Destructive |
| 3 | Change sharing permissions on any document | Access modification |
| 4 | Move files between folders | State modification |
| 5 | Rename files or folders | State modification |
| 6 | Create new Google documents | State modification |
| 7 | Send emails from Gmail | Outbound communication |
| 8 | Send DMs on any platform | Outbound communication |
| 9 | Post content to any platform | Public-facing action |
| 10 | Change Google account settings | Account modification |
| 11 | Capture passwords, tokens, or API keys | Credential capture |
| 12 | Process payments or subscriptions | Financial action |
| 13 | Install software or extensions | System modification |
| 14 | Modify system settings | System modification |
| 15 | Run arbitrary shell commands | Safety boundary |
| 16 | Access documents marked SENSITIVE without approval | Sensitivity boundary |
| 17 | Download files larger than 50MB | Resource constraint |
| 18 | Access Google Admin Console | Scope creep |
| 19 | Access Gmail content (inbox, sent, drafts) | Scope boundary — email is separate work order |
| 20 | Access Google Calendar content | Scope boundary — calendar is separate work order |

---

## Required Approvals

These actions pause execution and request founder sign-off via Discord.

| # | Action Requiring Approval | Approval Prompt |
|---|--------------------------|-----------------|
| 1 | Read content of any specific document | "Work order wo_gws_001: Read document '[title]' in folder '[folder]'?" |
| 2 | Export/download any document | "Work order wo_gws_001: Export '[title]' as [format]?" |
| 3 | Access any folder marked SENSITIVE by founder | "Work order wo_gws_001: Open SENSITIVE folder '[folder]'?" |
| 4 | Take screenshot of document content | "Work order wo_gws_001: Screenshot content of '[title]'?" |
| 5 | Batch approval: read all documents in a folder | "Work order wo_gws_001: Read all [N] documents in '[folder]'? (List: [titles])" |

### Approval mechanism

```
Local worker encounters approval-required action
  → Sets status to WAITING_FOR_USER_APPROVAL
  → POSTs to VPS /cc-prompt: {
      session_name: "dex_local",
      text: "[approval prompt from table above]",
      prompt_type: "permission"
    }
  → VPS sends to Discord with Approve/Deny buttons
  → Founder clicks Approve or Deny
  → Response routes back to local via session_discord_bridge
  → If Approved: execute action, log approval, continue
  → If Denied: skip action, log denial, continue to next
```

---

## Expected Outputs

The completed work order must produce:

| # | Output | Format | Required |
|---|--------|--------|----------|
| 1 | Complete Google Drive folder tree | JSON — nested folder/file structure | YES |
| 2 | Document inventory | JSON — list of all documents with metadata (title, type, folder, owner, modified date) | YES |
| 3 | Folder screenshots | PNG files — evidence of folder structures | YES (if evidence_required) |
| 4 | Read document summaries | JSON — per-document summary of content read (only for approved documents) | YES (for Phase 2 documents) |
| 5 | Exported document files | PDF/TXT — only for approved exports | CONDITIONAL (only if export approved) |
| 6 | Sensitivity flags | JSON — documents that appear to contain sensitive data | YES |
| 7 | Relevance tags | JSON — per-document tags mapping to Munoz Conglomerate ventures | YES |
| 8 | Safety confirmation | Text — explicit attestation that no blocked actions were taken | YES |
| 9 | Approval log | JSON — list of all approval requests, responses, and timestamps | YES |

---

## Execution Plan

### Phase 1 — Discovery (estimated 20-30 minutes)

```
Step 1: Open browser → navigate to https://drive.google.com
Step 2: Screenshot the root "My Drive" view
Step 3: List all top-level folders with names
Step 4: For each folder:
  a. Open folder
  b. Count documents
  c. Record document titles, types, modified dates
  d. Screenshot folder contents
  e. Note any sub-folders → recurse (max depth 3)
Step 5: List "Shared with me" top-level items (metadata only)
Step 6: Compile folder tree JSON
Step 7: Compile document inventory JSON
Step 8: POST discovery results to VPS via /work-order-result (partial)
```

### Phase 2 — Selective Read/Export (estimated 30-60 minutes, approval-gated)

```
Step 1: Review discovery results
Step 2: For each Tier 1 source target:
  a. Identify matching folder/documents from discovery
  b. Request batch approval: "Read all [N] docs in [folder]?"
  c. If approved: open each document, extract content summary
  d. If denied: skip, log as skipped
Step 3: For Tier 2 targets: only read if founder proactively approves
Step 4: For Tier 3 targets: no read — discovery metadata only
Step 5: Compile read summaries JSON
Step 6: Flag documents containing sensitive content
Step 7: Tag documents with venture relevance
Step 8: POST final results to VPS via /work-order-result (complete)
```

---

## Result Delivery

| Field | Value |
|-------|-------|
| **Result format** | JSON conforming to `local_google_workspace_ingestion_result_schema_v1.md` |
| **Result delivery** | POST to `http://100.77.233.50:8765/work-order-result` |
| **Result storage (VPS)** | `docs/operations/results/wo_gws_001_discovery_result.json` |
| **Result storage (local)** | `~/eos_work_orders/wo_gws_001_discovery_result.json` |
| **Evidence storage (local)** | `~/eos_work_orders/evidence/wo_gws_001/` (screenshots) |
| **Evidence transfer** | `tailscale file cp` to VPS, or base64 in result JSON if <100KB each |

---

## Safety Attestation (to be completed by local worker)

| Question | Answer |
|----------|--------|
| Were any documents edited? | ☐ NO |
| Were any files deleted? | ☐ NO |
| Were any permissions changed? | ☐ NO |
| Were any emails sent? | ☐ NO |
| Were any DMs sent? | ☐ NO |
| Were any posts made? | ☐ NO |
| Were any credentials captured? | ☐ NO |
| Were any payments processed? | ☐ NO |
| Were any unapproved reads performed? | ☐ NO |
| Was any content accessed without logging? | ☐ NO |

**This work order is CREATED but not yet dispatched. Dispatch occurs in Phase 94L after healthcheck passes.**
