# Local GUI Observation Policy v1

**Phase**: 95.0
**Status**: ACTIVE
**Date**: 2026-05-04

---

## 1. Temporary Observation

Temporary observation of the visible GUI is **allowed** for:
- Reading Drive file list items
- Reading file names, types, dates
- Reading navigation state (which page is active)
- Confirming account identity from UI
- Detecting login/error/wrong-account states

## 2. Persistent Screenshots

Persistent screenshot storage is **blocked** unless separately approved.
Temporary working observations are discarded after processing.

## 3. Credential Fields

Observation of credential fields is **always blocked**:
- Password input fields
- 2FA code fields
- Login forms
- Token displays
- Cookie/session stores

## 4. Login Screens

If a login screen is detected:
- Worker PAUSES immediately
- Worker reports LOGIN_REQUIRED
- Worker does NOT attempt to read or interact with login fields
- Worker waits for founder decision (manual login or secret-assisted)

## 5. Wrong Account

If the wrong account is detected:
- Worker PAUSES immediately
- Worker reports WRONG_ACCOUNT_PAUSE
- Worker does NOT switch accounts
- Worker does NOT interact with account picker

## 6. Document Opening

Opening documents through the GUI is **blocked** in this phase.
The worker may only read the file list metadata.
Double-clicking or navigating into a document is not permitted.

## 7. Observation Methods (Priority Order)

1. **Windows UI Automation** — structured accessibility tree, preferred
2. **Accessibility tree** — browser-provided a11y data
3. **Temporary screen observation** — pixel-level, needs approval for storage
4. **OCR** — last resort, lower accuracy
5. **Human visual confirmation** — founder describes what they see

## 8. Data Handling

- Observation data is processed immediately
- Only extracted metadata (file names, types, dates) is persisted
- Raw accessibility tree dumps are working data, not permanent artifacts
- Output files on remote machine are cleaned up after extraction
