# GUI Computer-Use Backend Policy v1

**Date**: 2026-05-04
**Phase**: 94D.3 — Central Advisor Session + Interface-Agnostic Communication Bus Correction v1

---

## 1. Problem Being Corrected

When the local worker received WO-LOCAL-PILOT-GDRIVE-GDOCS-001, it defaulted to Playwright/Chromium browser automation. This is wrong for a live supervised pilot because:

1. Playwright runs a headless or separate browser instance — the founder cannot see what's happening on the visible screen
2. The pilot's purpose is observable, supervised computer use — the founder watches the screen and approves actions
3. Browser automation bypasses the visual observation model that makes supervised computer use safe

---

## 2. Backend Classes

### GUI_COMPUTER_USE (Preferred for supervised pilots)

| Property | Value |
|----------|-------|
| Description | Visible screen interaction via mouse, keyboard, and screen observation |
| Implementation | Anthropic computer-use tool, or equivalent screen control API |
| Visibility | Founder sees every action on the actual screen |
| Control | Mouse movements, clicks, keyboard input on the real desktop |
| Observation | Screenshots of the actual screen, real browser visible |
| Safety | Founder can physically intervene (move mouse, close window) |
| Best for | Live supervised pilots, sensitive data access, first-time source ingestion |

**Requirements:**
- Local PC must have a visible desktop (not headless)
- Screen control backend installed (Anthropic computer-use, pyautogui, etc.)
- Founder must be watching (in person or via screen share / workstation UI)

### BROWSER_AUTOMATION (Disabled by default)

| Property | Value |
|----------|-------|
| Description | Programmatic browser control via Playwright, Selenium, or Puppeteer |
| Implementation | Playwright with Chromium, or Selenium WebDriver |
| Visibility | NOT visible on the actual screen (separate browser instance) |
| Control | DOM manipulation, JavaScript execution, headless rendering |
| Observation | Programmatic screenshots (not real screen) |
| Safety | Founder cannot see what's happening without extra tooling |
| Best for | Bulk operations after initial pilot, repetitive scraping, API-unavailable sites |

**Restrictions:**
- NOT the default for any work order
- Must be explicitly approved by founder via MODIFY_CONSTRAINTS message
- Must be logged as `execution_backend: BROWSER_AUTOMATION` in audit trail
- NOT allowed for first-time access to any source

### API_CONNECTOR (When official APIs exist)

| Property | Value |
|----------|-------|
| Description | Direct API calls to official service endpoints |
| Implementation | Google Drive API, Google Docs API, etc. |
| Visibility | Not visual — API requests/responses only |
| Control | Programmatic, scoped by API permissions |
| Observation | API response data, not screen content |
| Safety | Scoped by OAuth/API key permissions |
| Best for | Bulk exports, metadata queries, structured data access |

**Restrictions:**
- Requires valid API credentials (OAuth tokens, API keys)
- Scoped to specific API permissions — cannot exceed granted scope
- NOT the same as computer use — does not interact with the UI

### MANUAL_FALLBACK (Human performs the action)

| Property | Value |
|----------|-------|
| Description | Founder or operator manually performs the step |
| Implementation | Human at keyboard |
| Visibility | Human sees everything |
| Control | Human controls everything |
| Observation | Human reports what happened |
| Safety | Maximum safety — human in full control |
| Best for | Actions that cannot be automated, sensitive steps, fallback |

**Restrictions:**
- Used ONLY when automation is unavailable, unsafe, or explicitly chosen
- Must be logged as `execution_backend: MANUAL_FALLBACK` in audit trail

---

## 3. Default Backend Per Work Order Type

| Work Order Type | Default Backend | Reason |
|----------------|----------------|--------|
| GOOGLE_WORKSPACE_DISCOVERY | GUI_COMPUTER_USE | First-time access, founder must observe |
| GOOGLE_DOCS_READ_EXPORT | GUI_COMPUTER_USE | Sensitive content, approval per document |
| AI_CHAT_EXPORT | GUI_COMPUTER_USE | Sensitive content, approval per chat |
| CUSTOM_GPT_CONFIG_CAPTURE | GUI_COMPUTER_USE | Configuration data, approval per GPT |
| OBSIDIAN_VAULT_READ | API_CONNECTOR | File system access, no GUI needed |
| BROWSER_READ_ONLY_NAVIGATION | GUI_COMPUTER_USE | General browsing, founder observes |
| SCREENSHOT_EVIDENCE_CAPTURE | GUI_COMPUTER_USE | Visual evidence, must use real screen |
| RESULT_WRITEBACK | API_CONNECTOR | File write, no GUI needed |

---

## 4. Backend Selection Protocol

```
Work order received by local worker
  → Check default backend for task type
  → Check if work order specifies override
  → If GUI_COMPUTER_USE:
      → Check: is screen control backend available?
      → YES → use GUI_COMPUTER_USE
      → NO → send APPROVAL_NEEDED to advisor:
          "GUI computer-use backend unavailable.
           A. Install/enable GUI backend
           B. Use Playwright fallback
           C. Use manual fallback
           D. Cancel work order"
      → Wait for founder response
  → If BROWSER_AUTOMATION explicitly approved:
      → Log: execution_backend=BROWSER_AUTOMATION, approved_by=founder
      → Use Playwright/Selenium
  → If API_CONNECTOR:
      → Check: are API credentials valid?
      → YES → use API
      → NO → send ERROR to advisor
  → If MANUAL_FALLBACK:
      → Log: execution_backend=MANUAL_FALLBACK
      → Provide step-by-step instructions for founder
```

---

## 5. WO-001 Specific Policy

| Setting | Value |
|---------|-------|
| Work Order | WO-LOCAL-PILOT-GDRIVE-GDOCS-001 |
| Required backend | GUI_COMPUTER_USE |
| Playwright allowed | NO (unless founder explicitly approves via MODIFY_CONSTRAINTS) |
| API connector allowed | NO (this is a computer-use pilot, not an API integration) |
| Manual fallback allowed | YES (if GUI backend unavailable and founder chooses) |

### If GUI computer-use backend is not available on local PC

The local worker MUST NOT silently fall back to Playwright. Instead:

```
Worker → APPROVAL_NEEDED → Advisor:
  "GUI computer-use backend is not available on this machine.
   The work order WO-LOCAL-PILOT-GDRIVE-GDOCS-001 requires visible
   screen control for supervised execution.

   Options:
   A. Install GUI computer-use backend (requires: [specific package])
   B. Switch to Playwright browser automation (not recommended for pilot)
   C. Use manual fallback (founder performs steps, worker records)
   D. Cancel this work order

   Awaiting your decision."

Founder responds with option A, B, C, or D.
```

---

## 6. Backend Availability Check

Before executing any work order, the local worker checks backend availability:

```python
def check_gui_computer_use_available() -> tuple[bool, str]:
    """Check if GUI computer-use backend is available."""
    # Check 1: Is there a visible display?
    # Check 2: Is screen control tool installed?
    # Check 3: Can we take a test screenshot?
    # Returns (available, detail)

def check_browser_automation_available() -> tuple[bool, str]:
    """Check if Playwright/Selenium is available."""
    # Check 1: Is playwright installed?
    # Check 2: Is chromium binary present?
    # Returns (available, detail)

def check_api_connector_available(service: str) -> tuple[bool, str]:
    """Check if API credentials are valid for a service."""
    # Check 1: Are credentials present?
    # Check 2: Are credentials valid (test call)?
    # Returns (available, detail)
```

---

## 7. Audit Requirements

Every action must log:

```
execution_backend: GUI_COMPUTER_USE | BROWSER_AUTOMATION | API_CONNECTOR | MANUAL_FALLBACK
backend_selected_by: default | founder_override | fallback
backend_approval_message_id: str | None  (if founder explicitly chose)
```

Backend switches during execution require:
1. PAUSE current execution
2. Send MODIFY_CONSTRAINTS request to advisor
3. Wait for founder approval
4. Log the switch in audit trail
5. RESUME with new backend
