---
type: codebase-class
file: eos_ai/world_pulse.py
line: 158
generated: 2026-04-11
---

# WorldPulse

**File:** [[eos_ai-world_pulse-py]] | **Line:** 158

Continuous market and creator intelligence scanner.

run_pulse_scan() is the primary entry point — scans all monitored
sources, fetches live pages, and integrates everything permanently
into the knowledge base.

## Methods

- [[eos_ai-world_pulse-py-WorldPulse-__init__]]`(ctx)` — 
- [[eos_ai-world_pulse-py-WorldPulse-_scan_with_perplexity]]`(queries) → list[dict]` — Use Perplexity for real-time market intelligence.
- [[eos_ai-world_pulse-py-WorldPulse-run_market_intel_scan]]`() → dict` — Daily market intelligence scan — runs every morning at 6am.
- [[eos_ai-world_pulse-py-WorldPulse-run_pulse_scan]]`() → dict` — Scan all monitored sources and permanently integrate findings.
- [[eos_ai-world_pulse-py-WorldPulse-generate_pulse_report]]`(gws_ingested, gws_skipped, skills_needing_review, sources_scanned) → str` — Generate a human-readable report of what world pulse learned.
- [[eos_ai-world_pulse-py-WorldPulse-get_pulse_summary]]`() → str` — Returns a summary of recent world knowledge stored in the knowledge base.
