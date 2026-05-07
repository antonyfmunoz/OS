---
type: codebase-class
file: eos_ai/model_preferences.py
line: 106
generated: 2026-05-07
---

# ModelPreferences

**File:** [[eos_ai-model_preferences-py]] | **Line:** 106

*No docstring.*

## Methods

- [[eos_ai-model_preferences-py-ModelPreferences-__init__]]`(ctx) → None` — 
- [[eos_ai-model_preferences-py-ModelPreferences-_load]]`() → dict` — Load model_preferences row for this org. INSERT default if missing.
- [[eos_ai-model_preferences-py-ModelPreferences-_load_business_context]]`() → dict` — Query ventures + org to determine business stage and auto cost mode.
- [[eos_ai-model_preferences-py-ModelPreferences-get_business_context]]`() → dict` — 
- [[eos_ai-model_preferences-py-ModelPreferences-resolve_model]]`(task_type, modality, data_tier, require_realtime, forced_model, task_criticality) → dict` — Return a provider config dict for the given task parameters.
- [[eos_ai-model_preferences-py-ModelPreferences-_find_config]]`(model_name) → dict | None` — Search PROVIDER_CONFIGS by key or by model field value.
- [[eos_ai-model_preferences-py-ModelPreferences-_key_available]]`(env_key) → bool` — 
- [[eos_ai-model_preferences-py-ModelPreferences-_check_availability]]`(config) → dict` — If provider needs an API key and it's missing, fall back to gemma-local.
- [[eos_ai-model_preferences-py-ModelPreferences-set_cost_mode]]`(mode) → None` — 
- [[eos_ai-model_preferences-py-ModelPreferences-set_prefer_local]]`(prefer) → None` — 
- [[eos_ai-model_preferences-py-ModelPreferences-set_session_override]]`(model) → None` — 
- [[eos_ai-model_preferences-py-ModelPreferences-set_task_override]]`(task_type, model) → None` — 
- [[eos_ai-model_preferences-py-ModelPreferences-clear_task_override]]`(task_type) → None` — 
- [[eos_ai-model_preferences-py-ModelPreferences-get_current_summary]]`() → str` — 
