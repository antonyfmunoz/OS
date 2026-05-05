---
type: codebase-function
file: eos_ai/model_preferences.py
line: 218
generated: 2026-04-12
---

# ModelPreferences.resolve_model

**File:** [[eos_ai-model_preferences-py]] | **Line:** 218
**Signature:** `resolve_model(task_type, modality, data_tier, require_realtime, forced_model, task_criticality) → dict`

**Class:** [[eos_ai-model_preferences-py-ModelPreferences]]

Return a provider config dict for the given task parameters.

Priority order (highest wins):
  1. forced_model        — per-call human override
  2. session_override    — session-level human override
...

## Calls

- [[eos_ai-model_preferences-py-ModelPreferences-_check_availability]]
- [[eos_ai-model_preferences-py-ModelPreferences-_find_config]]
- [[eos_ai-model_preferences-py-ModelPreferences-_key_available]]

## Called By

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-model_preferences-py-ModelPreferences-get_current_summary]]
