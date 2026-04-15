---
type: codebase-class
file: eos_ai/intent_router.py
line: 29
generated: 2026-04-12
---

# IntentRouter

**File:** [[eos_ai-intent_router-py]] | **Line:** 29

Keyword-based intent classifier.
Fast — no LLM call. Runs on every gateway message.

## Methods

- [[eos_ai-intent_router-py-IntentRouter-__init__]]`(ctx) → None` — 
- [[eos_ai-intent_router-py-IntentRouter-route]]`(text) → IntentDomain` — Classify text into the most specific matching domain.
- [[eos_ai-intent_router-py-IntentRouter-get_agent]]`(domain) → str` — Map domain to canonical agent_id.
