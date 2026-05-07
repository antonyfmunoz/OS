---
type: codebase-class
file: core/security/context.py
line: 120
generated: 2026-05-07
---

# SecurityContext

**File:** [[core-security-context-py]] | **Line:** 120

Composes the six security subsystems into one object.

Typical use from ActionSystem:

    from core.security import SecurityContext
...

## Methods

- [[core-security-context-py-SecurityContext-__init__]]`() → None` — 
- [[core-security-context-py-SecurityContext-default]]`() → 'SecurityContext'` — Build a SecurityContext against the standard data layout.
- [[core-security-context-py-SecurityContext-for_env]]`(env) → 'SecurityContext'` — Build a context rooted at a specific SecurityEnv (useful for
- [[core-security-context-py-SecurityContext-verify_token]]`(token) → Token | None` — 
- [[core-security-context-py-SecurityContext-authorize_action]]`() → AuthorizationDecision` — Run the full authorization pipeline.
- [[core-security-context-py-SecurityContext-approve]]`() → ApprovalRequest` — Approve a pending request. Operator calls this.
- [[core-security-context-py-SecurityContext-reject]]`() → ApprovalRequest` — Reject a pending request. Any authenticated user may reject.
- [[core-security-context-py-SecurityContext-build_execution_context]]`() → ExecutionContext` — Build an ExecutionContext pre-wired to the current env.
- [[core-security-context-py-SecurityContext-_deny_and_audit]]`() → AuthorizationDecision` — 
- [[core-security-context-py-SecurityContext-_approve_and_audit]]`(token) → AuthorizationDecision` — 
- [[core-security-context-py-SecurityContext-_pending_and_audit]]`(token) → AuthorizationDecision` — 
