# GUI Computer-Use Backend Healthcheck v1

**Phase**: 94D.5 — Relay Wiring + GUI Healthcheck + W0-001 Relaunch
**Status**: READY
**Date**: 2026-05-04

---

## 1. Required Backend for W0-001

`GUI_COMPUTER_USE` — visible screen interaction the founder can watch.

## 2. What Counts as GUI Computer-Use

- Visible desktop screen (Windows desktop running)
- Mouse/keyboard control (pyautogui, Anthropic computer-use, etc.)
- Screenshot/observation capability
- Human can watch in real-time (in person or via screen share)

## 3. What Does NOT Count

- Hidden Playwright/Chromium automation (separate browser instance)
- API-only connector (no visual component)
- Headless browser execution

## 4. Safe Healthcheck Commands

These commands detect backend availability without performing any
mouse/keyboard/browser actions:

| Check | Command | What It Detects |
|-------|---------|----------------|
| Visible display | `python3 -c "import os; print('DISPLAY' if os.environ.get('DISPLAY') or os.name == 'nt' else 'NO_DISPLAY')"` | Is there a screen? |
| pyautogui | `python3 -c "import pyautogui; print('pyautogui OK')"` | Screen control library |
| Anthropic SDK | `python3 -c "import anthropic; print('anthropic SDK OK')"` | Computer-use API |
| Windows UI | `python3 -c "import subprocess; subprocess.run(['powershell', '-Command', 'Get-Process explorer'], capture_output=True); print('WinUI OK')"` | Desktop environment |
| Playwright | `python3 -c "import playwright; print('playwright installed')"` | Playwright (requires approval) |
| Manual fallback | `echo 'manual fallback always available'` | Human operator |

## 5. Backend Status Values

| Status | Meaning |
|--------|---------|
| `AVAILABLE` | Backend installed and display available |
| `MISSING` | Backend not installed or not importable |
| `PARTIAL` | Backend installed but display not available |
| `NEEDS_INSTALL` | Specific package needs to be installed |
| `NEEDS_FOUNDER_DECISION` | Multiple options, founder must choose |

## 6. If GUI Backend Unavailable

Worker sends advisor question:

```
GUI computer-use backend is not available on this machine.
The work order requires visible screen control for supervised execution.

Options:
A. Install GUI computer-use backend (pyautogui + anthropic SDK)
B. Switch to Playwright browser automation (not recommended for pilot)
C. Use manual fallback (founder performs steps, worker records)
D. Cancel this work order
```

Worker STOPS and waits for advisor response. Does NOT fall back silently.

## File

`eos_ai/substrate/gui_backend_healthcheck.py`
