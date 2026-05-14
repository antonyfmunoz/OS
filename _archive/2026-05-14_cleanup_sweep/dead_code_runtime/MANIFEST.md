# Dead-Code Runtime Modules — 2026-05-14

## Reason

These 15 modules at runtime/ top level have 0 external live callers.
Identified as UNREACHABLE during Phase C runtime layer migration.
All reachable modules were migrated to canonical §24 homes (commit 30f86495).

## Verification

Every module confirmed 0 callers outside itself via:
```
grep -rln "from runtime.<module>\|import runtime.<module>" --include="*.py" --exclude-dir=_archive .
```

## Files (15)

- agent_messages.py
- company_instantiator.py
- email_reviewer.py
- eod_closing_loop.py
- error_handler.py
- harness_registry.py
- integration_test.py
- knowledge_layers.py
- onboarding_backfill.py
- primitive_registry.py
- system_context.py
- template_library.py
- transaction_workflow.py
- trinity.py
- voice_interface.py

## Notes

7 of these files referenced `runtime.context` (the Phase B shim).
Archiving them clears all remaining shim callers.
