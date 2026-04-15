---
type: codebase-class
file: core/security/environments.py
line: 56
generated: 2026-04-12
---

# EnvironmentPolicy

**File:** [[core-security-environments-py]] | **Line:** 56

Per-tier policy: what risk the environment auto-approves.

`auto_risk_ceiling` — any action at or below this tier runs without
                      human approval (RBAC still applies).
`allow_critical`    — if False, CRITICAL actions are hard-blocked
...

## Decorators

- `@dataclass`
