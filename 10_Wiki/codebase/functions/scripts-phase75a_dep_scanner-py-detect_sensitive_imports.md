---
type: codebase-function
file: scripts/phase75a_dep_scanner.py
line: 90
generated: 2026-05-07
---

# detect_sensitive_imports

**File:** [[scripts-phase75a_dep_scanner-py]] | **Line:** 90
**Signature:** `detect_sensitive_imports(files, mod_map) → list[dict]`

Check for subprocess/docker imports outside allowed layers.

## Calls

- [[scripts-phase75a_dep_scanner-py-module_from_path]]
- [[scripts-phase75a_dep_scanner-py-normalize_to_package]]

## Called By

- [[scripts-phase75a_dep_scanner-py-main]]
