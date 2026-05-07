---
type: codebase-file
path: eos_ai/claude_skill_registry.py
module: eos_ai.claude_skill_registry
lines: 298
size: 11539
generated: 2026-05-07
---

# eos_ai/claude_skill_registry.py

ClaudeSkillRegistry — tracks all .claude/skills files, syncs them to Neon,
and flags skills that need reviewing against their source documentation.

Every skill Claude Code uses to build and operate EOS lives here:
  - Stored in Neon so agents can reference them at runtime
...

**Lines:** 298 | **Size:** 11,539 bytes

## Contains

- **class** [[eos_ai-claude_skill_registry-py-ClaudeSkill]] — 0 methods
- **class** [[eos_ai-claude_skill_registry-py-ClaudeSkillRegistryManager]] — 9 methods

## Import Statements

```python
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
```
