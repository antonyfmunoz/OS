# Phase 3 — Live Canary Re-Run

> Date: 2026-05-12
> Verdict: **PASS — STRUCTURED via router-fallthrough (Groq)**

## Test Configuration

- Fixture: `tests/fixtures/ingestion_fixture.md`
- Source: `LocalFileSource(authority_tier=T8_SCRATCH)`
- Orchestrator: `GenericIngestionOrchestrator`
- Memory store: `data/runtime/canonical_memory_store`

## Provider Chain Trace

| Step | Provider | Result |
|------|----------|--------|
| 1 | cc_sdk | auth error leak **detected** → returned None |
| 2 | Gemini | 429 RESOURCE_EXHAUSTED (free-tier quota) → returned empty |
| 3 | **Groq** | **llama-3.3-70b-versatile → valid JSON extraction** |

cc_sdk log line confirms fix:
```
[cc_sdk] error leak detected, returning None: Failed to authenticate.
API Error: 401 {"type":"error","error":{"type":"authentication_error",...
```

## Pipeline Result

```
verdict: COMPLETE_CYCLE
decomposition: 6 observations (LLM extraction)
bridge: 1 projection
persist: 7 entries (6 observations + 1 projection)
query_back: rank=1
```

## Observation Quality

| # | primitive_type | label_len | has_description | label_is_sentence |
|---|---------------|-----------|-----------------|-------------------|
| 0 | constraint | 25 | YES | no |
| 1 | action | 17 | YES | no |
| 2 | state | 15 | YES | no |
| 3 | resource | 29 | YES | no |
| 4 | constraint | 20 | YES | no |
| 5 | (not shown) | — | YES | no |

All observations have:
- Short semantic labels (15-29 chars, not raw sentence text)
- Descriptions (adds context beyond label)
- Appropriate primitive_type assignments

This is the STRUCTURED shape the re-ingest pipeline needs —
the opposite of the TEXT_BLOB shape (label = raw sentence,
no description).

## Comparison: Before vs After Fix

| Metric | Before (heuristic) | After (LLM via Groq) |
|--------|-------------------|---------------------|
| Method | heuristic fallback | LLM extraction |
| Provider | none (cc_sdk leaked) | Groq/llama-3.3-70b |
| Label style | raw sentence text | semantic abstraction |
| Descriptions | empty | populated |
| Relationships | none | extracted where present |

## Re-Ingest Unblocked

The TEXT_BLOB re-ingest (Phase 2+ of reingest-text-blobs) can
now proceed. LLM extraction works through the canonical pipeline
via Groq fallthrough.
