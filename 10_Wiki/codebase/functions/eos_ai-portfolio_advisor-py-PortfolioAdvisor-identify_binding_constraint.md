---
type: codebase-function
file: eos_ai/portfolio_advisor.py
line: 641
generated: 2026-04-12
---

# PortfolioAdvisor.identify_binding_constraint

**File:** [[eos_ai-portfolio_advisor-py]] | **Line:** 641
**Signature:** `identify_binding_constraint(ventures) → Optional[VentureHealth]`

**Class:** [[eos_ai-portfolio_advisor-py-PortfolioAdvisor]]

The ONE venture that is the bottleneck across the entire portfolio.
Lowest health score = binding constraint.

## Called By

- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-generate_portfolio_brief]]
