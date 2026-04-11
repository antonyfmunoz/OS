---
type: codebase-function
file: eos_ai/claude_skill_registry.py
line: 262
generated: 2026-04-11
---

# ClaudeSkillRegistryManager.check_for_updates

**File:** [[eos_ai-claude_skill_registry-py]] | **Line:** 262
**Signature:** `check_for_updates() → list[str]`

**Class:** [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager]]

Return list of skill IDs that need review against their source docs.
Criteria: never updated OR last updated > 7 days ago.
World pulse handles the actual doc fetching.

## Calls

- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-get_auto_update_skills]]
