---
type: codebase-class
file: core/security/environments.py
line: 99
generated: 2026-05-07
---

# SecurityEnv

**File:** [[core-security-environments-py]] | **Line:** 99

Wraps a core.environment.Environment with a security policy.

All path operations delegate to `self.env` — this object never
duplicates path logic. It only adds policy metadata and the
`authorize_risk(risk)` helper the SecurityContext uses.

## Methods

- [[core-security-environments-py-SecurityEnv-is_production]]`() → bool` — 
- [[core-security-environments-py-SecurityEnv-is_isolated]]`() → bool` — 
- [[core-security-environments-py-SecurityEnv-label]]`() → str` — 
- [[core-security-environments-py-SecurityEnv-needs_approval]]`(risk) → bool` — True if the policy gates this risk behind a human approval.
- [[core-security-environments-py-SecurityEnv-blocks]]`(risk) → bool` — Hard-block check. Returns True if the env refuses this risk
- [[core-security-environments-py-SecurityEnv-guard_write]]`(target) → None` — Delegate to core.environment's write guard.
- [[core-security-environments-py-SecurityEnv-resolve]]`(target) → 'object'` — Delegate path resolution.
- [[core-security-environments-py-SecurityEnv-log_dir]]`() → 'object'` — 
- [[core-security-environments-py-SecurityEnv-to_dict]]`() → dict` — 

## Decorators

- `@dataclass`
