---
type: codebase-class
file: eos_ai/proactive_engine.py
line: 82
generated: 2026-04-12
---

# ProactiveIntelligenceEngine

**File:** [[eos_ai-proactive_engine-py]] | **Line:** 82

*No docstring.*

## Methods

- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-__init__]]`(ctx)` — 
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-scan]]`() → list[ProactiveSignal]` — Full proactive scan. Returns all signals worth surfacing.
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-_scan_primitive_violations]]`() → list[ProactiveSignal]` — Detect when recent conversation shows founder discussing approaches
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-_scan_stage_transition]]`() → list[ProactiveSignal]` — Detect when recent conversation contains signals that a stage
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-_scan_inaction]]`() → list[ProactiveSignal]` — Detect when no founder activity for an extended period.
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-_scan_reality_divergence]]`() → list[ProactiveSignal]` — Detect when stated goals diverge from actual activity.
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-format_signal_for_telegram]]`(signal) → str` — Format a signal as a Telegram message.
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-format_signal_for_discord]]`(signal) → str` — Format a signal as a Discord message.
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-scan_and_deliver]]`(send_fn, min_urgency, send_telegram_fn) → int` — Scan for signals and deliver those above min_urgency.
