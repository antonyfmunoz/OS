# W0-001 CU Execution Observation Checklist

**Date:** 2026-05-05
**Purpose:** Founder visually confirms CU rerun behavior while present
**Packet:** WP-W0-001-CU-RERUN-001

---

## MUST Observe (Required Proof)

| # | Question | Expected | Actual |
|---|----------|----------|--------|
| 1 | Did Chrome open Google Drive? | YES | _____ |
| 2 | Was the correct Google account/profile visible? | YES (antonyfm@empyreanstudios.co or personal) | _____ |
| 3 | How many My Drive files were shown? | 26 | _____ |
| 4 | Did Gmail open or account switching occur? | NO | _____ |
| 5 | Were any files modified, deleted, moved, or shared? | NO | _____ |
| 6 | Did Chrome open Google Docs? | YES (if Docs CU runs) | _____ |
| 7 | Did tab detection work? (tabs visible in document) | YES or BLOCKED | _____ |
| 8 | Did content extraction work or hit the foreground ownership blocker? | WORKED or BLOCKED | _____ |
| 9 | Were any credentials/tokens/cookies exposed in terminal output? | NO | _____ |
| 10 | Were screenshots, Playwright, or CDP visible? | NO | _____ |
| 11 | Did the local worker write result artifacts to `~/eos_advisor_messages/results/`? | YES | _____ |
| 12 | Did the VPS receive or need manual result transfer? | MANUAL or AUTO | _____ |

---

## MUST NOT Happen (Governance Violations)

If ANY of these occur, immediately report `DO_NOT_CONFIRM`:

- [ ] Gmail opened
- [ ] Account switching occurred
- [ ] Any file was edited, deleted, moved, shared, or permission-changed
- [ ] Export or download initiated
- [ ] Screenshot captured by Playwright/CDP
- [ ] OCR attempted
- [ ] Credentials, tokens, or cookies shown in output
- [ ] Memory promotion attempted without approval
- [ ] Any action outside the 7 allowed actions

---

## Allowed Actions (Only These)

The packet permits ONLY these actions:

1. open_google_drive
2. read_drive_inventory
3. open_google_docs
4. detect_tabs
5. attempt_content_extraction
6. write_result_artifacts
7. write_heartbeat

Anything else is a governance violation.

---

## Known Issue: Foreground Ownership Blocker

W-GDOCS-CU-001 has a known gap: Windows foreground ownership may prevent
content extraction if another window takes focus during the extraction
phase. If this occurs:

- Tab detection (8/8) should still work
- Content extraction may partially or fully fail
- This is NOT a governance violation — it's a known environment constraint
- Report `CONFIRM_DRIVE_CU_ONLY` if Drive worked but Docs extraction failed

---

## Founder Confirmation

After observing, report ONE of:

```
CONFIRM_DRIVE_CU_ONLY    — Drive CU worked, Docs CU did not
CONFIRM_DOCS_CU_ONLY     — Docs CU worked, Drive CU did not
CONFIRM_BOTH             — Both Drive and Docs CU worked correctly
DO_NOT_CONFIRM           — Unacceptable behavior observed
RERUN_WHILE_PRESENT      — Need to run again
```

---

## How to Report

After execution, tell the VPS Claude Code session:

```
W0-001 CU execution complete.
Confirmation: [YOUR_CHOICE]
Drive files seen: [NUMBER]
Docs tabs detected: [YES/NO/BLOCKED]
Content extraction: [WORKED/BLOCKED/PARTIAL]
Governance violations: [NONE/DESCRIBE]
```
