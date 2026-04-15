---
type: codebase-file
path: eos_ai/expense_tracker.py
module: eos_ai.expense_tracker
lines: 451
size: 14398
generated: 2026-04-12
---

# eos_ai/expense_tracker.py

Expense Tracker — processes receipts from Gmail RECEIPTS-FINANCIALS folder,
categorizes, stores in Neon, surfaces in EOD and monthly reports.

**Lines:** 451 | **Size:** 14,398 bytes

## Contains

- **fn** [[eos_ai-expense_tracker-py-extract_expense_from_email]]`(subject, sender, body, ctx) → dict`
- **fn** [[eos_ai-expense_tracker-py-store_expense]]`(expense, ctx) → bool`
- **fn** [[eos_ai-expense_tracker-py-get_monthly_summary]]`(ctx) → dict`
- **fn** [[eos_ai-expense_tracker-py-process_receipt_emails]]`(ctx) → int`
- **fn** [[eos_ai-expense_tracker-py-create_invoice]]`(client_name, client_email, items, venture, due_days, ctx) → dict`
- **fn** [[eos_ai-expense_tracker-py-get_invoices]]`(status, ctx) → list[dict]`
- **fn** [[eos_ai-expense_tracker-py-get_overdue_invoices]]`(ctx) → list[dict]`
- **fn** [[eos_ai-expense_tracker-py-generate_invoice_text]]`(invoice) → str`
- **fn** [[eos_ai-expense_tracker-py-generate_expense_report]]`(month, ctx) → str`
- **fn** [[eos_ai-expense_tracker-py-generate_budget_vs_actual]]`(revenue_target, month, ctx) → str`

## Import Statements

```python
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
