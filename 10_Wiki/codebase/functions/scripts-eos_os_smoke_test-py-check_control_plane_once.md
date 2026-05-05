---
type: codebase-function
file: scripts/eos_os_smoke_test.py
line: 188
generated: 2026-04-12
---

# check_control_plane_once

**File:** [[scripts-eos_os_smoke_test-py]] | **Line:** 188
**Signature:** `check_control_plane_once() → None`

Spawn `python3 -m core.control_plane start --once` as a subprocess.

We run this as a subprocess rather than in-process so signal handling
and thread lifecycle match how an operator actually runs it.
