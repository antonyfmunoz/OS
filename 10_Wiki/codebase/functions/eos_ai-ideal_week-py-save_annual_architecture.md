---
type: codebase-function
file: eos_ai/ideal_week.py
line: 195
generated: 2026-04-11
---

# save_annual_architecture

**File:** [[eos_ai-ideal_week-py]] | **Line:** 195
**Signature:** `save_annual_architecture(year_plan, ctx) → bool`

Save the annual plan to Neon. Structure:
{
  'q1': {'rocks': [], 'revenue_target': 0, 'key_dates': []},
  'q2': {...}, 'q3': {...}, 'q4': {...},
  'vacation_blocks': ['2026-07-01 to 2026-07-14'],
...
