---
type: codebase-function
file: eos_ai/substrate/chrome_profile_resolver.py
line: 103
generated: 2026-05-07
---

# parse_local_state_profile_info

**File:** [[eos_ai-substrate-chrome_profile_resolver-py]] | **Line:** 103
**Signature:** `parse_local_state_profile_info(json_text) → dict[str, Any]`

Parse the profile info_cache from Chrome Local State.

Returns dict of profile_directory -> profile_metadata.
Only extracts safe metadata (name, email, display picture URL).
