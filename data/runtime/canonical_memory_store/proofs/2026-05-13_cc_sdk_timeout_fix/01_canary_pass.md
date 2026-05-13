# Phase 3 — Live Canary Pass

> Date: 2026-05-13
> Verdict: **PASS — STRUCTURED via cc_sdk (Opus 4.6)**

## Test Configuration

- Fixture: `tests/fixtures/ingestion_fixture.md`
- Source: `LocalFileSource(authority_tier=T8_SCRATCH)`
- Orchestrator: `GenericIngestionOrchestrator`
- cc_sdk timeout: 120s (new default, was 30s)

## Result

```
verdict: COMPLETE_CYCLE
wall-clock: 73.1s
provider: cc_sdk (confirmed by log: "[cc_sdk] returning output (7702 chars)")
model: Opus 4.6 (via Max subscription, no API cost)
observations: 10 (all with descriptions)
projections: 2
persisted: 12 entries
query_back: rank=1
```

## Why 30s Failed, 120s Succeeded

The cc_sdk call chain took 73.1s total:
- CLI startup + version check: ~3s
- MCP server connection attempts: ~5s (non-blocking errors)
- OAuth handshake: ~2s
- Opus 4.6 inference: ~55s (7,702 chars of structured JSON)
- Response streaming: ~8s

The old 30s timeout would have fired at the start of LLM
inference, returning None with "timed out after 30.0s with no
output." The 120s default gives 47s of margin.

## Quality Comparison

| Metric | Groq (30s timeout fallthrough) | cc_sdk/Opus (120s timeout) |
|--------|-------------------------------|--------------------------|
| Provider | groq/llama-3.3-70b | cc_sdk/opus-4.6 |
| Observations | 6 | **10** |
| Output size | ~2K chars | **7,702 chars** |
| Label quality | semantic, short | semantic, descriptive |
| All have descriptions | yes | yes |
| API cost | Groq free tier | **$0 (Max subscription)** |

## cc_sdk Is Now Option 0 in Production

The three-phase fix is complete:
1. Error-leak detection (_is_error_leak) — auth errors return None
2. Subprocess env (_get_subprocess_env) — OAuth injected, API key blanked
3. Timeout (120s default) — CLI has time to complete

cc_sdk now serves as the primary LLM provider through the
orchestrator. Groq/Gemini/Ollama are safety-net fallbacks.
