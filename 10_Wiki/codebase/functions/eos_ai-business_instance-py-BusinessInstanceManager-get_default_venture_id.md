---
type: codebase-function
file: eos_ai/business_instance.py
line: 244
generated: 2026-05-07
---

# BusinessInstanceManager.get_default_venture_id

**File:** [[eos_ai-business_instance-py]] | **Line:** 244
**Signature:** `get_default_venture_id() → Optional[str]`

**Class:** [[eos_ai-business_instance-py-BusinessInstanceManager]]

Return the default venture_id for the current org — substrate-neutral.

Resolution order:
1. EOS_DEFAULT_VENTURE env var (operator override)
2. First venture row for this org_id (alphabetical for determinism)
...
