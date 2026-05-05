---
type: codebase-class
file: eos_ai/system_health.py
line: 33
generated: 2026-04-12
---

# EOSSystemHealth

**File:** [[eos_ai-system_health-py]] | **Line:** 33

EOS knows its own operational state at all times.

quality_level() — what intelligence is active
chain_health() — is every layer connected
feedback_health() — is the loop closing
...

## Methods

- [[eos_ai-system_health-py-EOSSystemHealth-__init__]]`(ctx)` — 
- [[eos_ai-system_health-py-EOSSystemHealth-quality_level]]`() → str` — Current output quality based on provider availability flags.
- [[eos_ai-system_health-py-EOSSystemHealth-provider_status]]`() → dict` — Which intelligence providers are currently available.
- [[eos_ai-system_health-py-EOSSystemHealth-chain_health]]`() → dict` — Verify every layer of the chain is connected and responding.
- [[eos_ai-system_health-py-EOSSystemHealth-feedback_health]]`() → dict` — Is the feedback loop closing?
- [[eos_ai-system_health-py-EOSSystemHealth-training_data_health]]`() → dict` — Quality of captured data for Stage 3 LLM.
- [[eos_ai-system_health-py-EOSSystemHealth-full_report]]`() → dict` — Complete system state report.
- [[eos_ai-system_health-py-EOSSystemHealth-alert_if_degraded]]`(threshold) → bool` — Send alert if quality is at or below threshold.
- [[eos_ai-system_health-py-EOSSystemHealth-system_check]]`() → str` — Human-readable system status for morning brief and SessionStart.
