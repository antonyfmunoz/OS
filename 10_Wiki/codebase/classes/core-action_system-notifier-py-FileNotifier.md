---
type: codebase-class
file: core/action_system/notifier.py
line: 32
generated: 2026-05-07
---

# FileNotifier

**File:** [[core-action_system-notifier-py]] | **Line:** 32

Append deferred-action notifications to a JSONL queue file.

This is the always-on sink. Future Discord/Telegram workers can
drain it without needing to hook into the Control Plane directly.

## Methods

- [[core-action_system-notifier-py-FileNotifier-__init__]]`(path) → None` — 
- [[core-action_system-notifier-py-FileNotifier-notify]]`(action) → dict` — 
