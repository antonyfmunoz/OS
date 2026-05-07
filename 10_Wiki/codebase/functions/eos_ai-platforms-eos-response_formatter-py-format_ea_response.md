---
type: codebase-function
file: eos_ai/platforms/eos/response_formatter.py
line: 230
generated: 2026-05-07
---

# format_ea_response

**File:** [[eos_ai-platforms-eos-response_formatter-py]] | **Line:** 230
**Signature:** `format_ea_response() → str`

Master response formatter — routes to the appropriate shape formatter
based on summary_type.

Always returns EA-voiced text regardless of which specialist produced
the underlying analysis.

## Calls

- [[eos_ai-platforms-eos-response_formatter-py-format_blocked_decision_summary]]
- [[eos_ai-platforms-eos-response_formatter-py-format_briefing]]
- [[eos_ai-platforms-eos-response_formatter-py-format_execution_summary]]
- [[eos_ai-platforms-eos-response_formatter-py-format_portfolio_recommendation]]
- [[eos_ai-platforms-eos-response_formatter-py-format_strategic_recommendation]]

## Called By

- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_direct_ea]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_execution]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_portfolio]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_review]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_status]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_strategy]]
