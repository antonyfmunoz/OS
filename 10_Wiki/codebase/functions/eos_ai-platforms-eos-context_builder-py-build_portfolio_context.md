---
type: codebase-function
file: eos_ai/platforms/eos/context_builder.py
line: 288
generated: 2026-05-07
---

# build_portfolio_context

**File:** [[eos_ai-platforms-eos-context_builder-py]] | **Line:** 288
**Signature:** `build_portfolio_context() → dict[str, Any]`

Build Portfolio Advisor context — investment, capital, risk state.

Portfolio Advisor sees: high-level execution health (as risk signal),
perception anomalies (as risk indicators), and continuity state.
This is intentionally thin for v1 — no real financial data sources yet.

## Calls

- [[eos_ai-platforms-eos-context_builder-py-_safe]]
- [[eos_ai-platforms-eos-context_builder-py-_utcnow]]
