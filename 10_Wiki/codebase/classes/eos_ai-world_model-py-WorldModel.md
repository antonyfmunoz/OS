---
type: codebase-class
file: eos_ai/world_model.py
line: 134
generated: 2026-05-07
---

# WorldModel

**File:** [[eos_ai-world_model-py]] | **Line:** 134

Unified access to both canonical and instance world models.

## Methods

- [[eos_ai-world_model-py-WorldModel-__init__]]`(org_id)` — 
- [[eos_ai-world_model-py-WorldModel-_ensure_seeded]]`() → None` — Seed canonical model if empty.
- [[eos_ai-world_model-py-WorldModel-update_from_interaction]]`(message, response, outcome) → None` — Extract learnings from an interaction and store in instance model.
- [[eos_ai-world_model-py-WorldModel-get_context_for_prompt]]`(query) → str` — Build a world model context string for injection into the system prompt.
