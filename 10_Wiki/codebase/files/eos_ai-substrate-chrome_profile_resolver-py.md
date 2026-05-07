---
type: codebase-file
path: eos_ai/substrate/chrome_profile_resolver.py
module: eos_ai.substrate.chrome_profile_resolver
lines: 240
size: 7448
generated: 2026-05-07
---

# eos_ai/substrate/chrome_profile_resolver.py

Chrome profile resolver for Phase 94D.9.

Safely inspects Chrome profile metadata to find which profile is
associated with a target email/account. Does NOT read credentials,
cookies, tokens, or sensitive browser data.
...

**Lines:** 240 | **Size:** 7,448 bytes

## Contains

- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-is_file_allowed]]`(filename) → bool`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-is_file_blocked]]`(filename) → bool`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-get_chrome_user_data_dir]]`(username) → str`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-build_profile_inventory_command]]`() → str`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-parse_local_state_profile_info]]`(json_text) → dict[str, Any]`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-parse_profile_preferences_metadata]]`(json_text) → dict[str, Any]`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-find_profiles_for_email]]`(profile_metadata, target_email) → list[str]`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-build_safe_profile_inventory_result]]`(profiles, target_email, matches) → dict[str, Any]`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-classify_profile_resolution_status]]`(matches, profiles) → str`
- **fn** [[eos_ai-substrate-chrome_profile_resolver-py-build_no_match_options]]`() → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
from typing import Any
```
