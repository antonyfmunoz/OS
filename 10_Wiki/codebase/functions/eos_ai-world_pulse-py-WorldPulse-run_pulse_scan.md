---
type: codebase-function
file: eos_ai/world_pulse.py
line: 362
generated: 2026-04-11
---

# WorldPulse.run_pulse_scan

**File:** [[eos_ai-world_pulse-py]] | **Line:** 362
**Signature:** `run_pulse_scan() → dict`

**Class:** [[eos_ai-world_pulse-py-WorldPulse]]

Scan all monitored sources and permanently integrate findings.

Returns:
    {
        'total_integrated': int,
...

## Calls

- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate]]
- [[eos_ai-world_pulse-py-WorldPulse-_scan_with_perplexity]]
- [[eos_ai-world_pulse-py-WorldPulse-generate_pulse_report]]
