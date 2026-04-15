---
type: codebase-function
file: scripts/action_system.py
line: 399
generated: 2026-04-12
---

# ActionSystem.evaluate_risk

**File:** [[scripts-action_system-py]] | **Line:** 399
**Signature:** `evaluate_risk(action) → RiskLevel`

**Class:** [[scripts-action_system-py-ActionSystem]]

Deterministic risk assignment. No LLM, no heuristics that
require network calls. The rules must be predictable so the
operator can trust the approval gate.

## Calls

- [[scripts-action_system-py-ActionSystem-assess_impact]]

## Called By

- [[scripts-action_system-py-ActionSystem-propose]]
