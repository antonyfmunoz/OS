---
type: codebase-function
file: eos_ai/gateway.py
line: 1846
generated: 2026-04-12
---

# ingest_external_context

**File:** [[eos_ai-gateway-py]] | **Line:** 1846
**Signature:** `ingest_external_context(source, content, context_type, venture_id) → str`

Capture context from any external source into Neon + embed immediately.

source:       'telegram_manual' | 'claude_ai' | 'voice_note' | 'document' | 'manual'
context_type: 'design_decision' | 'architectural_spec' | 'user_feedback'
              | 'strategic_insight' | 'correction' | 'user_note'
...
