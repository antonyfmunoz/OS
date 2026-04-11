---
type: codebase-function
file: eos_ai/expense_tracker.py
line: 139
generated: 2026-04-11
---

# process_receipt_emails

**File:** [[eos_ai-expense_tracker-py]] | **Line:** 139
**Signature:** `process_receipt_emails(ctx) → int`

Pull unprocessed emails from RECEIPTS folder, extract expenses, store them.
Returns count of processed expenses.

## Calls

- [[eos_ai-expense_tracker-py-extract_expense_from_email]]
- [[eos_ai-expense_tracker-py-store_expense]]
