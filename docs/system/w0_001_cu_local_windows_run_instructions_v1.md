# W0-001 CU Local Windows Run Instructions v1

Phase: 96.7H
Date: 2026-05-05
Purpose: Step-by-step instructions for founder to run CU on local Windows PC

---

## Prerequisites

1. Be physically present at your Windows desktop
2. Chrome installed with profile "Antony (empyreanstudios.co)"
3. WSL terminal available
4. Network connection to Google Drive and Google Docs

## Option A: Automated Dispatch (VPS → Local)

If the VPS has SSH access to your local PC:

1. VPS pushes the rerun packet to `~/eos_advisor_messages/inbox/`
2. Open WSL terminal
3. Run: `python3 /opt/OS/eos_ai/substrate/local_worker_auto_loop.py`
4. Watch Chrome open — do NOT interact until each task completes
5. Confirm output matches expectations

## Option B: Manual Dispatch

If SSH is unavailable:

1. Copy `data/cu_rerun_packets/w0_001_cu_rerun_while_present.json` to local PC
2. Place the file in `~/eos_advisor_messages/inbox/`
3. Open WSL terminal
4. Run: `python3 /opt/OS/eos_ai/substrate/local_worker_auto_loop.py`
5. Watch Chrome open — do NOT interact until each task completes
6. Confirm output matches expectations

## Drive CU Task (DRIVE-CU-RERUN-001)

What you should see:
- Chrome opens with Google Drive (drive.google.com)
- Correct account visible: antonyfm@empyreanstudios.co
- Correct profile: Antony (empyreanstudios.co)
- My Drive view loads with your files
- Accessibility tree reads 26 items
- No Gmail opens, no account switching occurs
- No files are modified in any way

What to confirm:
- The 26 files shown are YOUR files
- The account is correct
- Nothing unexpected happened

## Docs CU Task (DOCS-CU-RERUN-001)

What you should see:
- Chrome opens Google Docs documents one by one
- Tab panel is visible in each document
- Content is extracted via foreground-aware method
- 28 documents processed, 321 tabs detected
- Child tabs navigated (134 expected)
- Content word count matches ~283,831

What to confirm:
- Documents are YOUR documents
- Tab detection is accurate
- Content extraction captured real content
- No documents were modified

## After Completion

Results will be written to `~/eos_advisor_messages/outbox/`

Report one of:
- **CONFIRM_DRIVE_CU_ONLY** — Drive CU becomes final 100%
- **CONFIRM_DOCS_CU_ONLY** — Docs CU proof confirmed (maturity depends on gaps closed)
- **CONFIRM_BOTH** — Both confirmed
- **DO_NOT_CONFIRM** — No change
- **PARTIAL** — Some tasks succeeded, others did not (explain which)

## Governance Checklist

Before confirming, verify:
- [ ] No Gmail was opened
- [ ] No account switching occurred
- [ ] No files were downloaded, exported, moved, deleted, or edited
- [ ] No screenshots were taken
- [ ] No Playwright or CDP automation was visible
- [ ] No credentials were exposed or captured
