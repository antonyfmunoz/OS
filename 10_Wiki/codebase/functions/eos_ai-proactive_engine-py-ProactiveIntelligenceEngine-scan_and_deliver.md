---
type: codebase-function
file: eos_ai/proactive_engine.py
line: 402
generated: 2026-05-07
---

# ProactiveIntelligenceEngine.scan_and_deliver

**File:** [[eos_ai-proactive_engine-py]] | **Line:** 402
**Signature:** `scan_and_deliver(send_fn, min_urgency, send_telegram_fn) → int`

**Class:** [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine]]

Scan for signals and deliver those above min_urgency.
send_fn: callable(str) — synchronous send function.
Returns count of signals delivered.

## Calls

- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-format_signal_for_telegram]]
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-scan]]
