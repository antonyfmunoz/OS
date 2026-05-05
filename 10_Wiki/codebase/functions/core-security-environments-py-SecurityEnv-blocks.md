---
type: codebase-function
file: core/security/environments.py
line: 137
generated: 2026-04-12
---

# SecurityEnv.blocks

**File:** [[core-security-environments-py]] | **Line:** 137
**Signature:** `blocks(risk) → bool`

**Class:** [[core-security-environments-py-SecurityEnv]]

Hard-block check. Returns True if the env refuses this risk
entirely (dev blocks CRITICAL).

## Calls

- [[core-capability-py-coerce_risk]]
