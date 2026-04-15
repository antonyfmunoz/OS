---
type: codebase-function
file: services/dm_monitor.py
line: 404
generated: 2026-04-12
---

# extract_messages_from_screenshot

**File:** [[services-dm_monitor-py]] | **Line:** 404
**Signature:** `extract_messages_from_screenshot(screenshot_path)`

Use Gemini Vision to extract conversation from screenshot.
Returns list of message dicts: [{"sender": "me"|"them", "text": "..."}]
Falls back gracefully if Gemini unavailable.

## Called By

- [[services-dm_monitor-py-check_inbox]]
