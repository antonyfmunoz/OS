---
type: codebase-function
file: eos_ai/cognitive_loop.py
line: 152
generated: 2026-04-11
---

# format_response_footer

**File:** [[eos_ai-cognitive_loop-py]] | **Line:** 152
**Signature:** `format_response_footer(result, iterations, was_enhanced, original_prompt, enhanced_prompt, org_id) → str`

Build a stats footer for any AgentResult or CognitiveResult.

Appended to the output string so every response surfaced through
Telegram or the gateway carries model, cost, latency, and (when
the prompt was enhanced) the optimized version.

## Calls

- [[eos_ai-agent_runtime-py-calculate_cost]]
- [[eos_ai-cognitive_loop-py-_get_neon_spend]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]

## Called By

- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
