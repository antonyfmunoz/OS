---
type: codebase-function
file: eos_ai/transaction_workflow.py
line: 137
generated: 2026-05-07
---

# TransactionWorkflow.run_synthetic_cycle

**File:** [[eos_ai-transaction_workflow-py]] | **Line:** 137
**Signature:** `run_synthetic_cycle(venture_id, client_name, client_email, product_name, amount_cents, fulfillment_desc, template_instance_id) → dict`

**Class:** [[eos_ai-transaction_workflow-py-TransactionWorkflow]]

Execute a complete lead→client→transaction→fulfillment cycle. Returns all IDs.

## Calls

- [[eos_ai-transaction_workflow-py-TransactionWorkflow-complete_fulfillment]]
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-create_lead]]
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-create_transaction]]
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-promote_to_client]]
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-record_fulfillment]]
