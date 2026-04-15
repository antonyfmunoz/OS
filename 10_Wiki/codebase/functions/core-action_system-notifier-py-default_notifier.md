---
type: codebase-function
file: core/action_system/notifier.py
line: 111
generated: 2026-04-12
---

# default_notifier

**File:** [[core-action_system-notifier-py]] | **Line:** 111
**Signature:** `default_notifier() → Notifier`

Return the default notifier stack: File always, Discord if configured.

This is what run_action uses when no notifier is passed explicitly.
