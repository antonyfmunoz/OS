---
type: codebase-class
file: eos_ai/strategy_engine.py
line: 128
generated: 2026-04-12
---

# StrategyEngine

**File:** [[eos_ai-strategy_engine-py]] | **Line:** 128

Reasons about company and portfolio strategy from real data.
Never generic. Every output is grounded in actual metrics.

## Methods

- [[eos_ai-strategy_engine-py-StrategyEngine-__init__]]`(ctx)` — 
- [[eos_ai-strategy_engine-py-StrategyEngine-analyze_company_position]]`(org_id) → dict` — Load all venture data + 30-day activity for the org.
- [[eos_ai-strategy_engine-py-StrategyEngine-analyze_portfolio_strategy]]`() → dict` — Run company position analysis for every company in the portfolio,
- [[eos_ai-strategy_engine-py-StrategyEngine-run_decision_analysis]]`(decision, venture_id) → dict` — Structured analysis of a founder decision.
- [[eos_ai-strategy_engine-py-StrategyEngine-weekly_strategy_review]]`() → str` — Full Sunday strategy review. Analyzes portfolio, compares signals,
