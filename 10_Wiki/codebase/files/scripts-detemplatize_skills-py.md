---
type: codebase-file
path: scripts/detemplatize_skills.py
module: scripts.detemplatize_skills
lines: 204
size: 6440
tags: [entry-point]
generated: 2026-04-12
---

# scripts/detemplatize_skills.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Removes hardcoded venture data from all skills.
Replaces with BIS injection !`command` block.
Replaces inline hardcoded references with generic placeholders.
Run once. Idempotent.

**Lines:** 204 | **Size:** 6,440 bytes

## Contains

- **fn** [[scripts-detemplatize_skills-py-has_hardcoded]]`(content) → bool`
- **fn** [[scripts-detemplatize_skills-py-has_bis_injection]]`(content) → bool`
- **fn** [[scripts-detemplatize_skills-py-has_old_bis]]`(content) → bool`
- **fn** [[scripts-detemplatize_skills-py-replace_old_bis_block]]`(content) → str`
- **fn** [[scripts-detemplatize_skills-py-replace_hardcoded_in_body]]`(content) → str`
- **fn** [[scripts-detemplatize_skills-py-update_description]]`(content) → str`
- **fn** [[scripts-detemplatize_skills-py-ensure_bis_block]]`(content) → str`
- **fn** [[scripts-detemplatize_skills-py-process_skill]]`(path) → tuple[bool, str]`
- **fn** [[scripts-detemplatize_skills-py-main]]`() → None`

## Import Statements

```python
import os
import re
```
