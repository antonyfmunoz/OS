# Substrate Compatibility Strategy

> Phase 96.8BK — 2026-05-09

## Current State

Active runtime code lives in `eos_ai/` and `core/`, not here.
This directory (`substrate/`) is the canonical target for staged migration.

## Why Not Move Everything Now

1. `services/discord_bot.py` imports 50+ modules from `eos_ai.*`
2. `services/handlers/substrate_command_handler.py` imports 25+ modules from `core.*`
3. Moving without shims breaks the running Discord bot
4. Moving with shims requires testing every import path

## Compatibility Shim Pattern

When a module moves from `eos_ai/foo.py` to `substrate/bar/foo.py`:

```python
# eos_ai/foo.py becomes a shim:
from substrate.bar.foo import *  # re-export everything
```

This allows existing imports to continue working while new code imports
from the canonical location.

## Migration Sequence

1. Create target package in `substrate/`
2. Copy module to new location
3. Replace original with re-export shim
4. Run `python3 -m py_compile` on both
5. Verify Discord bot starts correctly
6. Update tests to import from new location
7. After full migration, remove shims (Stage 5)

## When to Start

Stage 2 of the convergence plan — after Stage 1 cleanup is complete.
See `docs/system/staged_convergence_migration_plan.md`.
