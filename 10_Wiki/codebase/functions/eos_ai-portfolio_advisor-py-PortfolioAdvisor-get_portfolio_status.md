---
type: codebase-function
file: eos_ai/portfolio_advisor.py
line: 135
generated: 2026-04-12
---

# PortfolioAdvisor.get_portfolio_status

**File:** [[eos_ai-portfolio_advisor-py]] | **Line:** 135
**Signature:** `get_portfolio_status() → dict`

**Class:** [[eos_ai-portfolio_advisor-py-PortfolioAdvisor]]

For each org in the portfolio return:
  - interactions_7d: count of agent interactions last 7 days
  - reply_rate:       % of outcomes with positive outcome_type
  - ventures:         list of {name, monthly_revenue, monthly_target, progress_pct}

...

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-cross_company_intelligence]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-morning_advisory]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-run_weekly_review]]
