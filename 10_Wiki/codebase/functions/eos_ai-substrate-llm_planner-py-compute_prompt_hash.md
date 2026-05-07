---
type: codebase-function
file: eos_ai/substrate/llm_planner.py
line: 575
generated: 2026-05-07
---

# compute_prompt_hash

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 575
**Signature:** `compute_prompt_hash(prompt, model_name, temperature, config_version, registry_version) → str`

Composite prompt hash over all inputs that affect LLM output.

Includes prompt string, model, temperature, config version,
and registry version.  Not just the prompt string alone.

## Calls

- [[eos_ai-substrate-llm_planner-py-_canonical_json]]
- [[eos_ai-substrate-llm_planner-py-_sha256_prefix]]

## Called By

- [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy-propose]]
