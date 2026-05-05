# W0-001 Browser Backend Selection Policy v1

**Phase**: 94D.7R
**Status**: ACTIVE
**Date**: 2026-05-04

---

## For W0-001: Preferred Backend

**VISIBLE_CHROME_LAUNCH**

## Reason

- Founder uses Chrome primarily
- Likely relevant Google session (antonyfm@empyreanstudios.co) is in Chrome
- Watched local PC test requires visible browser behavior
- Playwright does not satisfy this specific test intention unless explicitly approved
- Explorer/default handler may open in Edge, IE, or other non-Chrome browser

## Fallback Order (requires advisor approval at each step)

| Priority | Backend | Condition |
|----------|---------|-----------|
| 1 | VISIBLE_CHROME_LAUNCH | Default — no approval needed |
| 2 | VISIBLE_DEFAULT_BROWSER_LAUNCH | Only if advisor explicitly approves |
| 3 | VISIBLE_EDGE_LAUNCH | Only if advisor explicitly approves |
| 4 | Playwright / structured automation | Only if advisor explicitly approves |
| 5 | Manual fallback | Only if advisor selects it |

## Silent Fallback: BLOCKED

If Chrome is not found:
- Do NOT silently fall back to Explorer, Edge, or default handler
- Emit `BACKEND_MISSING` / `CHROME_NOT_FOUND`
- Wait for advisor decision

## Capability Doctrine

UMH is universally adaptable.

- It CAN use anything (Chrome, Edge, Playwright, default browser, GUI automation)
- It SHOULD NOT use everything simultaneously
- It SELECTS the best implementation for the task based on constraints and context
- Redundant tools should not be maintained unless they provide distinct fallback value

For this test phase:
- Chrome is the right tool because the founder's Google session lives there
- The system must prove it can target a specific browser, not just "any browser"
- Future phases may select different backends for different tasks

## Backend Registry

| Backend | Classification | When to Use |
|---------|---------------|-------------|
| VISIBLE_CHROME_LAUNCH | Preferred for W0-001 | Google account access, founder session |
| VISIBLE_DEFAULT_BROWSER_LAUNCH | Fallback | When Chrome unavailable + approved |
| VISIBLE_EDGE_LAUNCH | Fallback | When Chrome + default unavailable + approved |
| Playwright | Structured automation | DOM interaction, form filling (not this phase) |
| LOCAL_GUI_CONTROL | Full computer use | Screenshot + mouse + keyboard (future) |

## Decision Authority

Backend selection for W0-001 is NOT the worker's decision.
The advisor (VPS) selects the backend based on:
1. Task requirements
2. Available backends on the target node
3. Security constraints
4. Founder preference

The worker executes what the advisor approves.
