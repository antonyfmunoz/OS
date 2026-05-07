---
type: codebase-class
file: eos_ai/runtime/provider_state.py
line: 138
generated: 2026-05-07
---

# SystemProviderState

**File:** [[eos_ai-runtime-provider_state-py]] | **Line:** 138

Process-wide singleton tracking all provider health + resource pressure.

## Methods

- [[eos_ai-runtime-provider_state-py-SystemProviderState-__init__]]`() → None` — 
- [[eos_ai-runtime-provider_state-py-SystemProviderState-_get_provider]]`(name) → ProviderState` — 
- [[eos_ai-runtime-provider_state-py-SystemProviderState-record_provider_success]]`(provider) → None` — 
- [[eos_ai-runtime-provider_state-py-SystemProviderState-record_provider_failure]]`(provider) → None` — 
- [[eos_ai-runtime-provider_state-py-SystemProviderState-record_all_providers_failed]]`() → None` — 
- [[eos_ai-runtime-provider_state-py-SystemProviderState-global_status]]`() → SystemStatus` — 
- [[eos_ai-runtime-provider_state-py-SystemProviderState-allow_execution]]`() → bool` — Check if the system should allow a new execution cycle.
- [[eos_ai-runtime-provider_state-py-SystemProviderState-allow_agent_spawn]]`() → bool` — Check if a new agent/subagent can be spawned.
- [[eos_ai-runtime-provider_state-py-SystemProviderState-_check_resource_pressure]]`() → str` — Return 'low', 'moderate', 'high', or 'critical'.
- [[eos_ai-runtime-provider_state-py-SystemProviderState-summary]]`() → dict` — Snapshot for logging/debugging.
