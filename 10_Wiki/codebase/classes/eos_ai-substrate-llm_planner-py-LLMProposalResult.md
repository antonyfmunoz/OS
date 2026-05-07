---
type: codebase-class
file: eos_ai/substrate/llm_planner.py
line: 420
generated: 2026-05-07
---

# LLMProposalResult

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 420

Full pipeline output from LLMPlanningStrategy.propose().

Attributes:
    prompt_hash: Composite hash of (prompt, model, temp, config_v, registry_v).
    raw_response: Raw LLM output string.
...

## Decorators

- `@dataclass`
