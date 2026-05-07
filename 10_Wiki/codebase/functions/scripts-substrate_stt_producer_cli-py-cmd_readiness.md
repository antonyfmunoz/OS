---
type: codebase-function
file: scripts/substrate_stt_producer_cli.py
line: 65
generated: 2026-05-07
---

# cmd_readiness

**File:** [[scripts-substrate_stt_producer_cli-py]] | **Line:** 65
**Signature:** `cmd_readiness(args) → int`

Workstation-facing readiness probe.

Exits 0 if the workstation can do REAL push-to-talk right now,
1 otherwise. The JSON payload always includes actionable next steps.

## Calls

- [[scripts-substrate_stt_producer_cli-py-_print_json]]
