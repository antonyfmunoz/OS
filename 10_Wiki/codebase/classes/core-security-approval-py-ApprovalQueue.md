---
type: codebase-class
file: core/security/approval.py
line: 135
generated: 2026-04-12
---

# ApprovalQueue

**File:** [[core-security-approval-py]] | **Line:** 135

File-backed approval queue.

One instance per process is fine. All reads replay from disk; all
writes are idempotent appends to the history log plus an atomic
write of the per-request JSON.

## Methods

- [[core-security-approval-py-ApprovalQueue-__init__]]`() → None` — 
- [[core-security-approval-py-ApprovalQueue-create_request]]`() → ApprovalRequest` — 
- [[core-security-approval-py-ApprovalQueue-approve]]`(request_id) → ApprovalRequest` — Flip a pending request to APPROVED.
- [[core-security-approval-py-ApprovalQueue-reject]]`(request_id) → ApprovalRequest` — Flip a pending request to REJECTED. Any role can reject a
- [[core-security-approval-py-ApprovalQueue-cancel]]`(request_id) → ApprovalRequest` — The original requester withdraws a pending request.
- [[core-security-approval-py-ApprovalQueue-_decide]]`(request_id) → ApprovalRequest` — 
- [[core-security-approval-py-ApprovalQueue-get]]`(request_id) → ApprovalRequest | None` — 
- [[core-security-approval-py-ApprovalQueue-list_pending]]`() → list[ApprovalRequest]` — 
- [[core-security-approval-py-ApprovalQueue-wait_for_decision]]`(request_id) → ApprovalRequest | None` — Block until the request is decided or `timeout` elapses.
- [[core-security-approval-py-ApprovalQueue-iter_history]]`() → Iterable[ApprovalRequest]` — 
- [[core-security-approval-py-ApprovalQueue-_state_path]]`(request_id) → Path` — 
- [[core-security-approval-py-ApprovalQueue-_write_state]]`(req) → None` — 
- [[core-security-approval-py-ApprovalQueue-_append]]`(path, row) → None` — 
- [[core-security-approval-py-ApprovalQueue-_iter_rows]]`(path) → Iterable[dict]` — 
- [[core-security-approval-py-ApprovalQueue-_is_expired]]`(req) → bool` — 
