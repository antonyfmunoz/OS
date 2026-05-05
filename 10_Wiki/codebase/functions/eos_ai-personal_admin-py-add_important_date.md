---
type: codebase-function
file: eos_ai/personal_admin.py
line: 17
generated: 2026-04-12
---

# add_important_date

**File:** [[eos_ai-personal_admin-py]] | **Line:** 17
**Signature:** `add_important_date(person, date, date_type, notes, ctx) → bool`

Add an important date to the events table.
date_type: birthday | anniversary | work_anniversary | other
date format: MM-DD (recurring yearly) or YYYY-MM-DD (one-time)
