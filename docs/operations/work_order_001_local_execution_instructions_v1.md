# Work Order WO-LOCAL-PILOT-GDRIVE-GDOCS-001 — Local Execution Instructions

**Issued by**: VPS orchestrator (vps_orchestrator)
**Assigned to**: Local PC worker (local_pc_worker / antony-workstation)
**Date**: 2026-05-04
**Status**: AWAITING_LOCAL_WORKER

---

## WORK ORDER

```
Work Order ID:       WO-LOCAL-PILOT-GDRIVE-GDOCS-001
Created by:          vps_orchestrator
Assigned to:         local_pc_worker
Task type:           GOOGLE_DRIVE_DOCS_FULL_ARCHIVE_PILOT
Google account:      antonyfm@empyreanstudios.co
Account scope:       single_account_only
Source class:        Google Drive / Google Docs only
Authority mode:      READ_ONLY + APPROVAL_REQUIRED for deep actions
Sensitivity level:   MIXED
Timeout:             120 minutes (approval pauses excluded)
Result path:         docs/operations/google_drive_docs_full_archive_pilot_results_v1.md
```

---

## PRE-EXECUTION CHECKLIST (local worker must confirm)

Before executing any action, confirm ALL of the following:

- [ ] 1. I am running on the **local PC** (not VPS)
- [ ] 2. The **founder is present and watching** the screen
- [ ] 3. A **browser window is visible** and accessible
- [ ] 4. The founder has **approved opening Google Drive**
- [ ] 5. The active Google account is **antonyfm@empyreanstudios.co**
- [ ] 6. If wrong account → **PAUSE immediately** — do not continue

---

## EXECUTION STEPS

### Phase 1 — Discovery (READ_ONLY, no approval needed per folder browse)

After founder gives initial approval to begin:

1. **Open Google Drive** at `https://drive.google.com`
2. **Verify account** — confirm the logged-in account is `antonyfm@empyreanstudios.co`
   - If wrong account: STOP. Report to founder. Do not switch accounts.
3. **Inventory the top-level Drive structure:**
   - List all visible folders in "My Drive"
   - List all items in "Shared with me" (top-level only)
   - For each folder: record name, approximate item count if visible
4. **For each top-level folder**, record:
   - Folder name
   - Approximate number of items (if shown)
   - Whether it appears to relate to a known venture (Initiate Arena, Lyfe Institute, Game of Lyfe, UMH, EntrepreneurOS, Empyrean Studio, Lyfe Spectrum, coaching, content, automations)
5. **Do NOT open individual documents yet** — that requires Phase 2 approval

### Phase 2 — Selective Read (APPROVAL_REQUIRED per action)

For each of the following actions, **ASK the founder before proceeding**:

| Action | Approval prompt |
|--------|----------------|
| Open a folder to view its contents | "Open folder '[name]'?" |
| Open a document to read it | "Open and read '[title]' in '[folder]'?" |
| Read/summarize document content | "Summarize content of '[title]'?" |
| Export or download a document | "Export '[title]' as [format]?" |
| Take a screenshot as evidence | "Screenshot '[title]' content?" |
| Follow an external link in a document | "Follow link '[url]' found in '[title]'?" |
| Continue to the next batch of documents | "Continue to next batch? [N remaining]" |
| End the pilot | "End pilot and write results?" |

### Phase 3 — Classification and Result Report

After the founder approves ending the pilot:

1. **Classify all discovered documents** by:
   - Venture relevance (which company/project does it serve)
   - Document type (strategy, curriculum, template, notes, financial, personal, other)
   - Staleness (actively maintained vs. stale/abandoned)
   - Sensitivity (public, private, sensitive)
2. **Identify source leads** — documents or folders that suggest other sources to ingest later
3. **Detect stale assumptions** — anything that contradicts current EOS knowledge
4. **Write result report** to the path specified below

---

## BLOCKED ACTIONS (NEVER perform these)

| # | Blocked Action |
|---|---------------|
| 1 | Access Gmail (inbox, sent, drafts) |
| 2 | Access other Google accounts |
| 3 | Edit any document |
| 4 | Delete any file or folder |
| 5 | Move any file or folder |
| 6 | Change sharing/permissions |
| 7 | Send emails |
| 8 | Send DMs |
| 9 | Post content anywhere |
| 10 | Open account settings |
| 11 | Enter passwords |
| 12 | Capture credentials/tokens/API keys/cookies/secrets |
| 13 | Process payments |
| 14 | Subscribe/unsubscribe |
| 15 | Install software |
| 16 | Modify system settings |
| 17 | Promote memory without governance |
| 18 | Run arbitrary shell commands beyond what's needed for the report |

---

## REQUIRED APPROVALS (must ask founder before each)

1. Open Google Drive (initial)
2. Verify account identity
3. Open any folder to browse contents
4. Open any document to read
5. Deep-read / summarize document content
6. Export or download any document
7. Take screenshot of document content
8. Follow any external link found in a document
9. Continue to next batch of items
10. End the pilot and write results

---

## RESULT REPORT

When the pilot ends, write a result report containing:

### Required fields:

- `work_order_id`: WO-LOCAL-PILOT-GDRIVE-GDOCS-001
- `executing_node`: local_pc_worker
- `google_account`: antonyfm@empyreanstudios.co
- `execution_start`: ISO 8601 timestamp
- `execution_end`: ISO 8601 timestamp
- `status`: COMPLETE / PARTIAL / FAILED
- `folder_tree`: Nested structure of all discovered folders
- `document_inventory`: List of all discovered documents with metadata
  - For each: title, type, folder path, last modified (if visible), owner (if visible)
- `documents_read`: List of documents whose content was read (only approved ones)
  - For each: title, summary, key topics, venture relevance
- `documents_skipped`: List of documents not read (with reason: denied, not requested, scope)
- `sensitivity_flags`: Documents that appear to contain sensitive data
- `venture_relevance_tags`: Per-document mapping to ventures
- `source_leads`: Other sources suggested by what was found
- `stale_assumptions`: Anything contradicting current EOS knowledge
- `safety_confirmation`: Explicit attestation that no blocked actions were performed
- `approval_log`: Every approval request and response with timestamps

### Result delivery:

- Write to: `docs/operations/google_drive_docs_full_archive_pilot_results_v1.md` (on VPS after transfer)
- Local copy: `~/eos_work_orders/WO-LOCAL-PILOT-GDRIVE-GDOCS-001_result.md`
- Transfer method: paste into VPS session, or `scp`, or `tailscale file cp`

---

## SAFETY ATTESTATION (complete at end)

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
| Was Gmail accessed? | ☐ NO |
| Were other accounts accessed? | ☐ NO |

---

## IF SOMETHING GOES WRONG

- **Wrong account**: STOP immediately. Do not attempt to switch. Report.
- **Permission error**: Note it, skip the item, continue.
- **Unexpected content (credentials, financial)**: Do NOT capture. Note existence only. Flag as SENSITIVE.
- **Browser crash**: Note where you stopped. Resume from that point after restart.
- **Founder unavailable**: PAUSE. Do not continue without approval.
- **Scope creep temptation**: If you see something interesting outside Google Drive/Docs (Gmail, Calendar, other apps) — do NOT access it. Note its existence for future work orders.

---

## DISPATCH STATUS

This work order is ready to execute when:
1. This file has been received by the local worker (via bridge, paste, or file transfer)
2. The founder is present at the local PC
3. The pre-execution checklist above is complete
4. The founder gives initial approval to begin

**The VPS does not execute this work order. The local PC worker does.**
