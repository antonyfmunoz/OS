---
type: codebase-function
file: eos_ai/expense_tracker.py
line: 193
generated: 2026-04-12
---

# create_invoice

**File:** [[eos_ai-expense_tracker-py]] | **Line:** 193
**Signature:** `create_invoice(client_name, client_email, items, venture, due_days, ctx) → dict`

Create an invoice record in the events table.
items: [{'description': str, 'amount': float, 'quantity': int}]
Returns invoice dict with id, total, due_date.
