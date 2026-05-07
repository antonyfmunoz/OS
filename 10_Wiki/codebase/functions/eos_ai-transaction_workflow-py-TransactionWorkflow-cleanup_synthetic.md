---
type: codebase-function
file: eos_ai/transaction_workflow.py
line: 204
generated: 2026-05-07
---

# TransactionWorkflow.cleanup_synthetic

**File:** [[eos_ai-transaction_workflow-py]] | **Line:** 204
**Signature:** `cleanup_synthetic(results) → int`

**Class:** [[eos_ai-transaction_workflow-py-TransactionWorkflow]]

Delete synthetic test data. Returns count of clients deleted (cascades to tx + events).

## Calls

- [[eos_ai-db-py-get_conn]]
