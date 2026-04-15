---
type: codebase-function
file: eos_ai/world_pulse.py
line: 523
generated: 2026-04-12
---

# WorldPulse.generate_pulse_report

**File:** [[eos_ai-world_pulse-py]] | **Line:** 523
**Signature:** `generate_pulse_report(gws_ingested, gws_skipped, skills_needing_review, sources_scanned) → str`

**Class:** [[eos_ai-world_pulse-py-WorldPulse]]

Generate a human-readable report of what world pulse learned.
Posted to Discord #agent-activity after every scan.

## Called By

- [[eos_ai-world_pulse-py-WorldPulse-run_pulse_scan]]
