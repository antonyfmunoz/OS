---
type: codebase-function
file: scripts/detemplatize_skills.py
line: 147
generated: 2026-05-07
---

# process_skill

**File:** [[scripts-detemplatize_skills-py]] | **Line:** 147
**Signature:** `process_skill(path) → tuple[bool, str]`

Process a single skill file. Returns (changed, reason).

## Calls

- [[scripts-detemplatize_skills-py-ensure_bis_block]]
- [[scripts-detemplatize_skills-py-has_bis_injection]]
- [[scripts-detemplatize_skills-py-has_hardcoded]]
- [[scripts-detemplatize_skills-py-has_old_bis]]
- [[scripts-detemplatize_skills-py-replace_hardcoded_in_body]]
- [[scripts-detemplatize_skills-py-update_description]]

## Called By

- [[scripts-detemplatize_skills-py-main]]
