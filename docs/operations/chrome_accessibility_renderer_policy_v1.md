# Chrome Accessibility Renderer Policy v1

**Status**: ACTIVE
**Date**: 2026-05-04
**Applies to**: All computer-use observations of Chrome web content

---

## Core Requirement

Chrome must be launched with `--force-renderer-accessibility` for Windows UI
Automation to read web page content (DOM elements, text, controls).

Without this flag, UIAutomation only sees browser chrome (address bar, buttons,
tabs) — NOT the web page itself.

## Allowed Chrome Flags

| Flag | Purpose | Required |
|------|---------|----------|
| `--force-renderer-accessibility` | Expose DOM to accessibility API | YES |
| `--profile-directory="Profile N"` | Use correct Chrome profile | YES |

## Blocked Chrome Flags

These flags are NEVER used for CU observation:

| Flag | Reason |
|------|--------|
| `--remote-debugging-port` | CDP — violates computer-use-only |
| `--headless` | No visible UI — violates observation model |
| `--enable-automation` | Automation detection flag |
| `--disable-extensions` | Modifies user environment |
| `--user-data-dir` | Custom data directory (not user's profile) |
| `--no-sandbox` | Security weakening |
| `--remote-allow-origins` | CDP remote access |
| `--auto-open-devtools-for-tabs` | DevTools — violates CU-only |
| `--disable-gpu` | Unnecessary for observation |

## Execution Method

Chrome MUST be launched via Task Scheduler /IT to run in the user's
interactive desktop session. Direct SSH launch runs in Session 0
where UIAutomation cannot see desktop windows.

```
schtasks /create /tn "TaskName" /tr "chrome.exe --force-renderer-accessibility --profile-directory=\"Profile 5\" https://target.url" /sc once /st 00:00 /f /rl highest /it
schtasks /run /tn "TaskName"
schtasks /delete /tn "TaskName" /f
```

## What the Accessibility Tree Exposes

With `--force-renderer-accessibility`, UIAutomation can read:
- Web page text content (headings, paragraphs, links)
- Interactive controls (buttons, inputs, dropdowns)
- Data items (list rows, table cells)
- Navigation elements (tree items, tabs)
- ARIA roles and labels

## What It Does NOT Expose

- Internal Google IDs (file IDs, folder IDs)
- Hidden DOM attributes (data-* attributes)
- Network requests or responses
- Cookie/session data
- JavaScript state

## Verification

Before any CU observation task, validate:
1. Chrome was launched with `--force-renderer-accessibility`
2. No blocked flags are present
3. Execution is via Task Scheduler /IT (not direct SSH)
4. The target URL is within allowed scope
