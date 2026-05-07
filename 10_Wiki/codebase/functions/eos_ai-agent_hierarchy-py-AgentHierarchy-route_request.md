---
type: codebase-function
file: eos_ai/agent_hierarchy.py
line: 305
generated: 2026-05-07
---

# AgentHierarchy.route_request

**File:** [[eos_ai-agent_hierarchy-py]] | **Line:** 305
**Signature:** `route_request(text) → str`

**Class:** [[eos_ai-agent_hierarchy-py-AgentHierarchy]]

Determine which agent should handle a natural language request.

EA handles 90% of cases directly. Only escalates to CEO agents for
company-specific deep questions, or to Portfolio Advisor for
portfolio-level decisions.
...
