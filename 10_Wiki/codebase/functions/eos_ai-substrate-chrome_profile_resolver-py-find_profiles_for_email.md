---
type: codebase-function
file: eos_ai/substrate/chrome_profile_resolver.py
line: 163
generated: 2026-05-07
---

# find_profiles_for_email

**File:** [[eos_ai-substrate-chrome_profile_resolver-py]] | **Line:** 163
**Signature:** `find_profiles_for_email(profile_metadata, target_email) → list[str]`

Find which profile directories match the target email.

Searches user_name and gaia_name fields from Local State info_cache.
Returns list of matching profile directory names.
