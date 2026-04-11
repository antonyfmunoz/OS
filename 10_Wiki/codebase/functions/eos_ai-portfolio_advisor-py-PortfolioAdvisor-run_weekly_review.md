---
type: codebase-function
file: eos_ai/portfolio_advisor.py
line: 308
generated: 2026-04-11
---

# PortfolioAdvisor.run_weekly_review

**File:** [[eos_ai-portfolio_advisor-py]] | **Line:** 308
**Signature:** `run_weekly_review() → str`

**Class:** [[eos_ai-portfolio_advisor-py-PortfolioAdvisor]]

Deeper version of morning_advisory with week-over-week delta,
compounding vs decaying signals, cross-company leverage opportunities,
and updated north star trajectory.

Writes output to /opt/OS/orchestrator/portfolio/YYYY-WW.md
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-_format_status_block]]
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-get_portfolio_status]]
