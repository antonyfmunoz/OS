---
type: codebase-function
file: eos_ai/portfolio_advisor.py
line: 454
generated: 2026-04-12
---

# PortfolioAdvisor.scan_all_ventures

**File:** [[eos_ai-portfolio_advisor-py]] | **Line:** 454
**Signature:** `scan_all_ventures() → list[VentureHealth]`

**Class:** [[eos_ai-portfolio_advisor-py-PortfolioAdvisor]]

Read health of every venture from Neon + BIS data.
Returns a VentureHealth for each venture found.
Silently skips any venture that errors — portfolio scan never crashes.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-_score_venture]]

## Called By

- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-detect_cross_venture_patterns]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-generate_weekly_report]]
