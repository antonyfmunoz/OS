---
type: codebase-function
file: eos_ai/transaction_workflow.py
line: 27
generated: 2026-05-07
---

# TransactionWorkflow.create_lead

**File:** [[eos_ai-transaction_workflow-py]] | **Line:** 27
**Signature:** `create_lead(venture_id, name, email, source, phone, notes) → str`

**Class:** [[eos_ai-transaction_workflow-py-TransactionWorkflow]]

Insert a lead into clients table. Returns client_id.

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-transaction_workflow-py-TransactionWorkflow-run_synthetic_cycle]]
