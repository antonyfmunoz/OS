# ExecutionSpine Diagnosis Report
**Date:** 2026-05-16
**Tester:** Claude (automated)

## Finding: ExecutionSpine is FUNCTIONAL

Tested both outside and inside Docker (os-discord container):
- VPS direct: 55.2s, response "Hey Antony — DEX is locked in and ready to build."
- Docker: 169.6s, response "Hi" (cc_sdk timeout hit, retried successfully)
- ContextBuilder: 0 failed sources with real org ID, ~1800 tokens assembled

## Root Cause of Gateway Fallback

The `except Exception` at gateway.py:1062 is a blanket catch. In production (Discord bot),
the spine occasionally:
1. Times out via cc_sdk (120s default) — returns error string, doesn't crash
2. Hits transient Neon connection errors during ContextBuilder (e.g., world_model seed writes)
3. Hits import-time errors if a dependency hasn't been loaded yet in the worker process

The spine itself never raises (by design — it catches everything and returns a string).
The exception comes from ContextBuilder.build() or the imports above it.

## Proposed Fix (Requires Approval — touches gateway.py)

Option A (minimal, recommended):
- Wrap only the ContextBuilder.build() call in its own try/except
- If it fails, build a minimal UnifiedContext with just ai_identity
- Let spine.run() always execute (it handles its own errors)

Option B (aggressive):
- Remove the blanket try/except entirely
- Since spine.run() never raises, the only failure point is ContextBuilder
- Make ContextBuilder itself never raise (it already catches per-source, just needs
  a top-level wrapper around the full method)

## Recommended Next Steps

1. In ContextBuilder.build(), add a top-level try/except that returns a minimal
   UnifiedContext on catastrophic failure (does NOT touch gateway.py)
2. Increase CC_SDK_TIMEOUT_SECONDS to 180 in Docker compose env
3. After both confirmed stable, get approval to remove the CognitiveLoop fallback
   from gateway.py

## Evidence
- Test command VPS: `python3 -c "from execution.runtime.execution_spine import ExecutionSpine; ..."`
- Test command Docker: `docker exec os-discord python3 -c "..."`
- Both produced valid LLM responses via cc_sdk → Opus 4.6
