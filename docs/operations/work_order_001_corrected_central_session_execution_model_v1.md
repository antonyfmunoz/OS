# Work Order 001 — Corrected Central Session Execution Model v1

**Date**: 2026-05-04
**Phase**: 94D.3 — Central Advisor Session + Interface-Agnostic Communication Bus Correction v1

---

## 1. What Was Wrong

### Problem A: Local-only approvals
The work order execution instructions told the local worker to ask for approval in the local terminal. This means the founder must be typing in that specific terminal to approve. If the founder is on the VPS, on Discord, on the phone, or using voice — approvals are unreachable.

### Problem B: Playwright as default
The local worker used Playwright/Chromium browser automation. This runs a separate browser instance that is not visible on the real screen. The founder cannot observe what the worker is doing. The pilot's purpose is supervised, observable computer use.

---

## 2. Corrected Model

| Property | Before (Wrong) | After (Correct) |
|----------|---------------|-----------------|
| Approval interface | Local terminal only | Central advisor session via message bus |
| Founder location | Must be at local terminal | Can be anywhere (VPS, phone, Discord, voice) |
| Execution backend | Playwright (invisible) | GUI computer use (visible screen) |
| Observation | Founder cannot see actions | Founder watches real screen |
| Communication | Terminal prompt/response | Message bus envelope routing |

---

## 3. Corrected Execution Flow

### Step 0: Dispatch (VPS)
```
VPS advisor session dispatches WO-LOCAL-PILOT-GDRIVE-GDOCS-001 to local PC
  → via HTTP bridge (forward_to_local) or SSH
  → work order arrives at local worker
```

### Step 1: Claim (Local)
```
Local worker → Message Bus → Advisor:
  WORK_ORDER_CLAIMED {
    work_order_id: "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
    node_id: "local_pc_worker",
    execution_backend: "GUI_COMPUTER_USE"
  }
```

### Step 2: Backend Check (Local)
```
Local worker checks GUI computer-use availability:
  → Display visible? → Screen control tool installed? → Test screenshot works?
  → If NO: sends APPROVAL_NEEDED with fallback options (A/B/C/D)
  → If YES: proceeds
```

### Step 3: First Approval (Local → Advisor → Founder)
```
Local worker → Message Bus → Advisor → Founder's active interface:
  APPROVAL_NEEDED {
    action: "open_google_drive",
    target: "https://drive.google.com",
    context: "Phase 1 Discovery — opening Google Drive for account antonyfm@empyreanstudios.co using GUI computer-use (visible screen)",
    risk_level: "LOW"
  }

Founder (from ANY interface) → Advisor → Message Bus → Local worker:
  APPROVAL_RESPONSE {
    decision: "APPROVE"
  }
```

### Step 4: Execute (Local, visible)
```
Local worker uses GUI computer-use to:
  → Move mouse to browser
  → Navigate to drive.google.com
  → Founder watches the real screen
  → Takes screenshot of result
  → Sends WORK_ORDER_STATUS update to advisor
```

### Step 5: Account Verification (Local → Advisor)
```
Local worker → Advisor:
  WORK_ORDER_STATUS {
    phase: "account_verification",
    detail: "Checking logged-in Google account"
  }

If wrong account:
  Local worker → Advisor:
    ERROR {
      error_type: "AUTH",
      description: "Wrong Google account active. Expected antonyfm@empyreanstudios.co, found [other]",
      recoverable: false
    }
  → Worker PAUSES
  → Founder must resolve (switch account manually or cancel)
```

### Step 6: Discovery Loop (Local, with approvals via bus)
```
For each folder:
  Local worker → Advisor:
    APPROVAL_NEEDED {
      action: "open_folder",
      target: "Coaching Frameworks",
      context: "Phase 1 Discovery — inventorying folder contents"
    }

  Founder → Advisor → Local worker:
    APPROVAL_RESPONSE { decision: "APPROVE" }

  Local worker opens folder using GUI computer-use (visible click)
  Local worker records metadata
  Local worker → Advisor:
    WORK_ORDER_STATUS { detail: "Folder 'Coaching Frameworks' — 12 items found" }
```

### Step 7: Deep Read Loop (Local, approval per document)
```
For each document to read:
  Local worker → Advisor:
    APPROVAL_NEEDED {
      action: "read_document",
      target: "Coaching Framework v3.docx",
      context: "Phase 2 Selective Read — opening document for content summary"
    }

  Founder → Advisor → Local worker:
    APPROVAL_RESPONSE { decision: "APPROVE" }

  Local worker opens document using GUI computer-use (visible)
  Local worker reads and summarizes content
  Local worker → Advisor:
    EVIDENCE_AVAILABLE {
      evidence_type: "SCREENSHOT",
      description: "Screenshot of Coaching Framework v3.docx first page"
    }
```

### Step 8: Completion (Local → Advisor)
```
Local worker → Advisor:
  APPROVAL_NEEDED {
    action: "end_pilot",
    target: "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
    context: "All approved folders inventoried, all approved documents read. End pilot?"
  }

Founder → Advisor → Local worker:
  APPROVAL_RESPONSE { decision: "APPROVE" }

Local worker writes result report
Local worker → Advisor:
  COMPLETION_REPORT {
    status: "COMPLETE",
    actions_taken: 47,
    approvals_requested: 23,
    approvals_granted: 21,
    approvals_denied: 2,
    safety_attestation: { all_checks_passed: true },
    result_path: "~/eos_work_orders/WO-LOCAL-PILOT-GDRIVE-GDOCS-001_result.md"
  }

Local worker → Advisor:
  RESULT {
    status: "COMPLETE",
    result_path: "docs/operations/google_drive_docs_full_archive_pilot_results_v1.md",
    summary: "24 folders, 87 documents inventoried. 15 documents read. Full classification produced."
  }
```

---

## 4. Interface Projection During Execution

The founder can observe and approve from ANY connected interface:

| Scenario | Interface | How |
|----------|-----------|-----|
| Founder at local PC | Workstation UI or CLI | Direct screen observation + bus approval |
| Founder at VPS (Termius/SSH) | CLI | Receives approval prompts as text, types APPROVE |
| Founder on phone | Telegram or mobile app | Receives push notification, taps APPROVE button |
| Founder on Discord | Discord | Receives embed with APPROVE/DENY buttons |
| Founder using voice | Voice | Hears "Do you approve opening Coaching Frameworks?" → says "Yes" |

All approvals route through the same message bus. The local worker never knows which interface the founder is using.

---

## 5. Safety Model (Unchanged)

| Rule | Enforcement |
|------|-------------|
| Single account only | Worker checks on every page load |
| Read-only | Worker never clicks edit/delete/move |
| Approval per folder/doc | Every action goes through bus |
| No Gmail | Worker never navigates to Gmail |
| No credential capture | Worker flags sensitive content, does not capture |
| Founder can STOP anytime | STOP message halts all execution immediately |
| Audit trail | Every message logged with timestamp |

---

## 6. What Changes in the Work Order Instructions

The existing `work_order_001_local_execution_instructions_v1.md` must be updated (in a future phase) to:

1. Replace "ask the founder before proceeding" with "send APPROVAL_NEEDED to advisor session"
2. Replace Playwright/browser automation with GUI computer-use as the execution backend
3. Add message bus integration instructions
4. Add backend availability check as first step
5. Add fallback protocol if bus is unreachable

These changes are DEFINED here but NOT YET APPLIED to the instructions file. The instructions will be updated in Phase 94D.4 when the message bus relay is implemented.
