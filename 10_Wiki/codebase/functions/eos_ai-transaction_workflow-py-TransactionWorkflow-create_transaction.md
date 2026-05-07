---
type: codebase-function
file: eos_ai/transaction_workflow.py
line: 57
generated: 2026-05-07
---

# TransactionWorkflow.create_transaction

**File:** [[eos_ai-transaction_workflow-py]] | **Line:** 57
**Signature:** `create_transaction(venture_id, client_id, product_name, amount_cents, template_instance_id, notes) → str`

**Class:** [[eos_ai-transaction_workflow-py-TransactionWorkflow]]

Record a transaction. Returns transaction_id.

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-transaction_workflow-py-TransactionWorkflow-run_synthetic_cycle]]
