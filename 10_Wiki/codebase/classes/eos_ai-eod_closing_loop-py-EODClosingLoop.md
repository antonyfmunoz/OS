---
type: codebase-class
file: eos_ai/eod_closing_loop.py
line: 36
generated: 2026-05-07
---

# EODClosingLoop

**File:** [[eos_ai-eod_closing_loop-py]] | **Line:** 36

*No docstring.*

## Methods

- [[eos_ai-eod_closing_loop-py-EODClosingLoop-__init__]]`(ctx)` — 
- [[eos_ai-eod_closing_loop-py-EODClosingLoop-run]]`() → str` — 
- [[eos_ai-eod_closing_loop-py-EODClosingLoop-run_and_publish]]`() → str` — Run EOD closing loop, write to Notion, post link to Discord.
- [[eos_ai-eod_closing_loop-py-EODClosingLoop-_get_todays_meetings]]`() → list[str]` — 
- [[eos_ai-eod_closing_loop-py-EODClosingLoop-_get_todays_purchases]]`() → list[str]` — Pull receipts/financials from GPS RECEIPTS label for today.
- [[eos_ai-eod_closing_loop-py-EODClosingLoop-_get_todays_project_updates]]`() → list[str]` — 
- [[eos_ai-eod_closing_loop-py-EODClosingLoop-_get_todays_decisions]]`() → list[str]` — Decisions = dex_question events answered today.
