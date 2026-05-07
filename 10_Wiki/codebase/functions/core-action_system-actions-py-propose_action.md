---
type: codebase-function
file: core/action_system/actions.py
line: 60
generated: 2026-05-07
---

# propose_action

**File:** [[core-action_system-actions-py]] | **Line:** 60
**Signature:** `propose_action(type, description) → Action`

Build an Action object in the `proposed` state.

This does not log anything by itself — the Control Plane logs on
every lifecycle transition. Splitting construction from logging keeps
the Action pure and testable.
