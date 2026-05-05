---
type: codebase-function
file: eos_ai/world_pulse.py
line: 226
generated: 2026-04-12
---

# WorldPulse.run_market_intel_scan

**File:** [[eos_ai-world_pulse-py]] | **Line:** 226
**Signature:** `run_market_intel_scan() → dict`

**Class:** [[eos_ai-world_pulse-py-WorldPulse]]

Daily market intelligence scan — runs every morning at 6am.

Scans MONITORED_SOURCES (creators, market signals, business knowledge)
and checks Claude skills for updates. Does NOT rescan GWS documents —
that runs weekly on Saturdays via run_pulse_scan().
...

## Calls

- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate]]
- [[eos_ai-world_pulse-py-WorldPulse-_scan_with_perplexity]]
