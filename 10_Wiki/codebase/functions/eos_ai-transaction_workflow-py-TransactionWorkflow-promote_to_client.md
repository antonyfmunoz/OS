---
type: codebase-function
file: eos_ai/transaction_workflow.py
line: 47
generated: 2026-05-07
---

# TransactionWorkflow.promote_to_client

**File:** [[eos_ai-transaction_workflow-py]] | **Line:** 47
**Signature:** `promote_to_client(client_id) → bool`

**Class:** [[eos_ai-transaction_workflow-py-TransactionWorkflow]]

Move a lead to client status. Returns True on success.

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-transaction_workflow-py-TransactionWorkflow-run_synthetic_cycle]]
