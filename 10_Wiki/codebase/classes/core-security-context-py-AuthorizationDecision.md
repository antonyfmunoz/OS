---
type: codebase-class
file: core/security/context.py
line: 61
generated: 2026-04-12
---

# AuthorizationDecision

**File:** [[core-security-context-py]] | **Line:** 61

Outcome of SecurityContext.authorize_action.

Fields
------
status            — "approved" | "pending" | "denied"
...

## Methods

- [[core-security-context-py-AuthorizationDecision-is_approved]]`() → bool` — 
- [[core-security-context-py-AuthorizationDecision-is_pending]]`() → bool` — 
- [[core-security-context-py-AuthorizationDecision-is_denied]]`() → bool` — 
- [[core-security-context-py-AuthorizationDecision-as_dict]]`() → dict` — 

## Decorators

- `@dataclass`
