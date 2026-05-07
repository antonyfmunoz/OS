---
type: codebase-class
file: eos_ai/claude_skill_registry.py
line: 176
generated: 2026-05-07
---

# ClaudeSkillRegistryManager

**File:** [[eos_ai-claude_skill_registry-py]] | **Line:** 176

*No docstring.*

## Methods

- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-__init__]]`(base_path)` — 
- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-get_all]]`() → list[ClaudeSkill]` — 
- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-get_by_category]]`(category) → list[ClaudeSkill]` — 
- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-get_auto_update_skills]]`() → list[ClaudeSkill]` — 
- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-read_skill]]`(skill_id) → str` — 
- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-update_skill]]`(skill_id, new_content) → bool` — 
- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-sync_to_neon]]`(ctx) → int` — Sync all skills that have content to Neon database.
- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-check_for_updates]]`() → list[str]` — Return list of skill IDs that need review against their source docs.
- [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager-format_status]]`() → str` — 
