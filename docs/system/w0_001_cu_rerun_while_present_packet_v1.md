# W0-001 CU Rerun While Present Packet v1

Phase: 96.7H
Date: 2026-05-05
Purpose: Dispatch a live CU rerun on local Windows desktop with founder present

---

## What This Packet Does

This packet instructs the local Windows worker to re-execute Computer Use
inventory tasks for both Google Drive and Google Docs while the founder is
physically present at the screen. This produces the strongest proof level:
AUDITABLE_PROOF_CONFIRMED.

## Packet Location

`data/cu_rerun_packets/w0_001_cu_rerun_while_present.json`

## Run ID

W0-001-CU-RERUN-WHILE-PRESENT-001

## Tasks

### Task 1: DRIVE-CU-RERUN-001 (W-GDRIVE-CU-001)

- Open Chrome with Google Drive
- Run accessibility tree inventory
- Confirm 26 My Drive files
- Confirm account: antonyfm@empyreanstudios.co
- Confirm profile: Antony (empyreanstudios.co)

### Task 2: DOCS-CU-RERUN-001 (W-GDOCS-CU-001)

- Open Chrome with Google Docs
- Run tab detection + content extraction
- Solve foreground ownership to unblock content extraction
- Confirm: 28 docs, 321 tabs, 134 child tabs, 283,831 words
- Close all 7 hardening gaps

## Dispatch Method

1. VPS writes packet to `.substrate_station/`
2. SSH pushes to local `~/eos_advisor_messages/inbox/`
3. Local worker polls inbox and claims packet
4. OR: founder manually copies packet to local PC

## Founder Requirements

- Must be physically present at the Windows desktop
- Must watch Chrome open and execute
- Must confirm output matches expectations
- Must report confirmation to Developer Agent

## Governance

- No Playwright, CDP, or screenshots
- No Gmail, no account switching
- No file mutation (edit/delete/move/share/export/download)
- No credential capture
- Method: COMPUTER_USE_ONLY
