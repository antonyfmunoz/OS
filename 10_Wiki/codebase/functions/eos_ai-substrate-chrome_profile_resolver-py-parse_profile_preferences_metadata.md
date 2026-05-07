---
type: codebase-function
file: eos_ai/substrate/chrome_profile_resolver.py
line: 135
generated: 2026-05-07
---

# parse_profile_preferences_metadata

**File:** [[eos_ai-substrate-chrome_profile_resolver-py]] | **Line:** 135
**Signature:** `parse_profile_preferences_metadata(json_text) → dict[str, Any]`

Parse safe metadata from a Chrome profile's Preferences file.

Extracts ONLY: account_info email, profile name, gaia info.
Does NOT extract: cookies, tokens, passwords, history.
