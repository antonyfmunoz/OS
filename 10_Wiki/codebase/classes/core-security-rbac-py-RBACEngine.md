---
type: codebase-class
file: core/security/rbac.py
line: 196
generated: 2026-04-12
---

# RBACEngine

**File:** [[core-security-rbac-py]] | **Line:** 196

Policy object for role → operation lookups.

The engine holds a dict of roles by name and answers two questions:
    check(role, op, risk)      — can this role request this operation?
    can_approve(role, risk)    — can this role approve this risk tier?
...

## Methods

- [[core-security-rbac-py-RBACEngine-__init__]]`(roles) → None` — 
- [[core-security-rbac-py-RBACEngine-register]]`(role) → None` — 
- [[core-security-rbac-py-RBACEngine-get]]`(name) → Role` — 
- [[core-security-rbac-py-RBACEngine-list_roles]]`() → list[Role]` — 
- [[core-security-rbac-py-RBACEngine-check]]`(role_name, op, risk) → RBACCheck` — Evaluate whether `role_name` may request `op` at `risk`.
- [[core-security-rbac-py-RBACEngine-can_approve]]`(role_name, risk) → bool` — True if this role's approval authority covers `risk`.
