---
type: codebase-function
file: eos_ai/substrate/chrome_profile_resolver.py
line: 86
generated: 2026-05-07
---

# build_profile_inventory_command

**File:** [[eos_ai-substrate-chrome_profile_resolver-py]] | **Line:** 86
**Signature:** `build_profile_inventory_command() → str`

Build a PowerShell command to read Chrome Local State metadata.

Reads ONLY the profile info block from Local State.
Does NOT read cookies, login data, history, or any credential store.
