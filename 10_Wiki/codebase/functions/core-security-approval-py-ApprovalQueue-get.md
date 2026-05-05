---
type: codebase-function
file: core/security/approval.py
line: 307
generated: 2026-04-12
---

# ApprovalQueue.get

**File:** [[core-security-approval-py]] | **Line:** 307
**Signature:** `get(request_id) → ApprovalRequest | None`

**Class:** [[core-security-approval-py-ApprovalQueue]]

*No docstring.*

## Calls

- [[core-security-approval-py-ApprovalQueue-_state_path]]
- [[core-security-approval-py-ApprovalRequest-from_dict]]

## Called By

- [[core-security-approval-py-ApprovalQueue-_decide]]
- [[core-security-approval-py-ApprovalQueue-cancel]]
- [[core-security-approval-py-ApprovalQueue-wait_for_decision]]
- [[core-security-approval-py-ApprovalRequest-from_dict]]
- [[core-security-cli-py-cmd_approval_show]]
