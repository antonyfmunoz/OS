---
type: codebase-function
file: eos_ai/system_health.py
line: 49
generated: 2026-05-07
---

# EOSSystemHealth.quality_level

**File:** [[eos_ai-system_health-py]] | **Line:** 49
**Signature:** `quality_level() → str`

**Class:** [[eos_ai-system_health-py-EOSSystemHealth]]

Current output quality based on provider availability flags.

OPTIMAL — CC subprocess (Opus) available
STANDARD — Anthropic SDK available
DEGRADED — Gemini Flash available
...

## Called By

- [[eos_ai-system_health-py-EOSSystemHealth-alert_if_degraded]]
- [[eos_ai-system_health-py-EOSSystemHealth-full_report]]
- [[eos_ai-system_health-py-EOSSystemHealth-system_check]]
- [[eos_ai-system_health-py-EOSSystemHealth-training_data_health]]
