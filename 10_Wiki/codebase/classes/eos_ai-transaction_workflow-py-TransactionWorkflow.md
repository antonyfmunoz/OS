---
type: codebase-class
file: eos_ai/transaction_workflow.py
line: 21
generated: 2026-05-07
---

# TransactionWorkflow

**File:** [[eos_ai-transaction_workflow-py]] | **Line:** 21

Executes and verifies the full transaction lifecycle for a venture.

## Methods

- [[eos_ai-transaction_workflow-py-TransactionWorkflow-__init__]]`(org_id)` — 
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-create_lead]]`(venture_id, name, email, source, phone, notes) → str` — Insert a lead into clients table. Returns client_id.
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-promote_to_client]]`(client_id) → bool` — Move a lead to client status. Returns True on success.
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-create_transaction]]`(venture_id, client_id, product_name, amount_cents, template_instance_id, notes) → str` — Record a transaction. Returns transaction_id.
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-record_fulfillment]]`(venture_id, transaction_id, description, completed_by, evidence_url) → str` — Record a fulfillment event. Returns event_id.
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-complete_fulfillment]]`(transaction_id) → bool` — Mark a transaction as fully fulfilled. Updates client to 'fulfilled'.
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-run_synthetic_cycle]]`(venture_id, client_name, client_email, product_name, amount_cents, fulfillment_desc, template_instance_id) → dict` — Execute a complete lead→client→transaction→fulfillment cycle. Returns all IDs.
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-verify_cycle]]`(result) → dict` — Verify all rows exist and have correct statuses.
- [[eos_ai-transaction_workflow-py-TransactionWorkflow-cleanup_synthetic]]`(results) → int` — Delete synthetic test data. Returns count of clients deleted (cascades to tx + e
