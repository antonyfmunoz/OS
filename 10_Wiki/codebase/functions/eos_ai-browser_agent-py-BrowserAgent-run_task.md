---
type: codebase-function
file: eos_ai/browser_agent.py
line: 269
generated: 2026-05-07
---

# BrowserAgent.run_task

**File:** [[eos_ai-browser_agent-py]] | **Line:** 269
**Signature:** `run_task(task_description, ctx) → dict`

**Class:** [[eos_ai-browser_agent-py-BrowserAgent]]

Higher-level: describe what to do, agent reasons about how.

Uses AgentRuntime to plan steps, then executes each one.
After every navigation, extracts full page state as structured text.
Screenshots are taken only on exception/failure.
...

## Calls

- [[eos_ai-browser_agent-py-BrowserAgent-click]]
- [[eos_ai-browser_agent-py-BrowserAgent-extract_page_state]]
- [[eos_ai-browser_agent-py-BrowserAgent-extract_table]]
- [[eos_ai-browser_agent-py-BrowserAgent-navigate]]
- [[eos_ai-browser_agent-py-BrowserAgent-screenshot]]
- [[eos_ai-browser_agent-py-BrowserAgent-type_into]]
- [[eos_ai-browser_agent-py-BrowserAgent-wait_for]]
- [[eos_ai-browser_agent-py-_synthesize_findings]]

## Called By

- [[eos_ai-browser_agent-py-InstagramAgent-send_dm]]
- [[eos_ai-browser_agent-py-ManusAgent-submit_task]]
- [[eos_ai-browser_agent-py-run_browser_task]]
