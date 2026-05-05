---
type: codebase-class
file: eos_ai/portfolio_advisor.py
line: 56
generated: 2026-04-12
---

# PortfolioAdvisor

**File:** [[eos_ai-portfolio_advisor-py]] | **Line:** 56

*No docstring.*

## Methods

- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-__init__]]`(ctx) → None` — 
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-_load_portfolio]]`() → None` — Load portfolio metadata and all orgs that belong to it.
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-get_all_orgs]]`() → list[dict]` — Return all orgs loaded into this portfolio [{id, name, slug, ventures}].
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-get_portfolio_status]]`() → dict` — For each org in the portfolio return:
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-morning_advisory]]`() → str` — Board-level morning advisory across all portfolio companies.
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-cross_company_intelligence]]`(topic) → str` — Load all company contexts simultaneously and produce a board-level
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-run_weekly_review]]`() → str` — Deeper version of morning_advisory with week-over-week delta,
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-scan_all_ventures]]`() → list[VentureHealth]` — Read health of every venture from Neon + BIS data.
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-_score_venture]]`(bis, lead_count) → dict` — Score venture health 0-1 and identify binding constraint.
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-identify_binding_constraint]]`(ventures) → Optional[VentureHealth]` — The ONE venture that is the bottleneck across the entire portfolio.
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-generate_portfolio_brief]]`(ventures) → str` — Full portfolio status brief.
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-generate_weekly_report]]`() → str` — Sunday portfolio report — scans all ventures, returns full brief.
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-detect_cross_venture_patterns]]`() → list[dict]` — Detect patterns appearing across
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-inform_ceos_of_pattern]]`(pattern) → str` — Generate directive to CEO agents
- [[eos_ai-portfolio_advisor-py-PortfolioAdvisor-_format_status_block]]`(status) → str` — 
