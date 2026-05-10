# eos_ai/platforms Archive Manifest

Archived during convergence Wave 4 — 2026-05-10.

## Why Archived

`eos_ai/platforms/eos/` contained platform-specific orchestration code
(context_builder, execution_bridge, ea_orchestrator, live_runtime, etc.).
Zero live service or script imports. Only imported by:
- 2 files in eos_ai/substrate/ (now eos_ai/transport/)
- 10 test files in tests/platforms/

## Contents

- 14 tracked files across eos_ai/platforms/eos/

## Associated Legacy Tests

- 12 test files moved to tests/legacy/platforms/eos/

## Rollback

```bash
git revert <wave-4-commit>
```
