---
type: codebase-function
file: eos_ai/claude_skill_registry.py
line: 220
generated: 2026-04-12
---

# ClaudeSkillRegistryManager.sync_to_neon

**File:** [[eos_ai-claude_skill_registry-py]] | **Line:** 220
**Signature:** `sync_to_neon(ctx) → int`

**Class:** [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager]]

Sync all skills that have content to Neon database.
Skills without files are skipped silently.
Returns count of skills synced.

## Calls

- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-read_skill]]
