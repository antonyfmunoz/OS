---
type: codebase-function
file: eos_ai/substrate/browser_agent.py
line: 270
generated: 2026-05-07
---

# BrowserAgent.execute

**File:** [[eos_ai-substrate-browser_agent-py]] | **Line:** 270
**Signature:** `execute(action, payload) → BrowserActionResult`

**Class:** [[eos_ai-substrate-browser_agent-py-BrowserAgent]]

Thread-safe dispatch to the appropriate action handler.

Always returns a BrowserActionResult, never raises.
Emits streaming events for real-time narration.

## Calls

- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_dispatch]]
- [[eos_ai-substrate-browser_agent-py-_stream_browser_event]]
- [[eos_ai-substrate-browser_agent-py-_stream_browser_result]]

## Called By

- [[eos_ai-substrate-browser_agent-py-execute_browser_action]]
