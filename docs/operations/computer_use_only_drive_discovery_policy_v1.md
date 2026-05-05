# Computer-Use-Only Drive Discovery Policy v1

**Phase**: 95.0
**Status**: ACTIVE
**Date**: 2026-05-04

---

## 1. Definition

Computer-use-only discovery means:
- User-visible browser window (Chrome Profile 5)
- UI observation via Windows UI Automation / accessibility tree
- Mouse/keyboard/scroll actions via Task Scheduler /IT
- No API calls to Google Drive/Docs
- No hidden automation (Playwright, CDP)
- No token/cache/cookie access
- No document content access

## 2. Purpose

- Worst-case fallback proof when APIs are unavailable
- Not the preferred production path when API exists
- Validates local worker "hands and eyes" capability
- Proves the system can operate like a human at the desktop

## 3. When to Use

- API auth is expired/revoked and cannot be refreshed
- API is rate-limited or blocked
- Network policy blocks API but allows browser
- Testing computer-use capability in isolation
- Fallback validation for resilience

## 4. When NOT to Use

- API is available and authenticated (use API for reliability)
- Need to inventory more than visible page (API is complete)
- Need structured metadata like file IDs (API provides this)
- Production bulk operations

## 5. Technical Requirements

- Chrome launched with `--force-renderer-accessibility`
- Windows UI Automation assembly available
- Task Scheduler /IT for interactive session execution
- PowerShell script execution allowed (without -ExecutionPolicy Bypass)

## 6. Constraints

- Only reads what's visible in the Drive UI
- May miss files below the scroll fold
- Cannot read file IDs (these are internal to the API)
- "Untitled document" entries are ambiguous without dates
- File type inference is based on UI text labels
- Modified dates are relative ("Mar 18") not absolute ISO dates
