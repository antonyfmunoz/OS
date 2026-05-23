# Phase 1 — LLM Sanity Check (STOP CONDITION)

> Date: 2026-05-12
> Verdict: **HEURISTIC FALLBACK — STOP**

## Canary Test

**Input:** `tests/fixtures/ingestion_fixture.md` via
`LocalFileSource(authority_tier=T8_SCRATCH)`

**Expected:** LLM extraction produces structured observations
(primitive_type, label, description, evidence, relationships).

**Actual:** Heuristic fallback fired. Observations have
label = raw sentence text. No descriptions. No relationships.
This is the same TEXT_BLOB shape we are trying to replace.

## Root Cause Trace

### 1. cc_sdk returns auth error as valid output

`runtime/cc_sdk.py:155-176` — the `_stream()` inner function catches
all exceptions at line 169 and suppresses them:

```python
except Exception as e:
    logger.debug("cc_sdk _stream: caught %s (output_parts=%d)", e, len(output_parts))
```

When Claude CLI exits with Anthropic 401, the error text
("Failed to authenticate with the API...") arrives as an
`AssistantMessage` with `TextBlock` content BEFORE the exception
propagates. So `output_parts` has the error text, the exception
is caught and logged at DEBUG, and execution continues.

At line 213, `output = "\n".join(output_parts).strip()` produces
a non-empty string (373 chars of error message). Since it's
non-empty, cc_sdk returns a `CCResult(output=<error text>)` at
line 220 instead of `None`.

### 2. model_router treats non-empty cc_sdk output as success

`runtime/model_router.py:1053` (heavy path):

```python
if cc_result and cc_result.output:
    # ... returns RoutingResult with output=cc_result.output
```

The check is `cc_result.output` — truthy for any non-empty string.
The 373-char auth error is truthy, so `call_with_fallback()` returns
it as a successful `RoutingResult`. Gemini, Groq, Ollama are never
tried.

### 3. Decomposer fails to parse, falls back to heuristic

`runtime/ingestion/orchestrator.py` `_decompose_llm()` receives
the auth error text as `result.output`. Calls
`_parse_extraction_output()` which tries `json.loads()` on
`"Failed to authenticate with the API..."` — raises
`json.JSONDecodeError`. After 2 failed attempts, falls to
heuristic extraction.

### 4. Heuristic produces TEXT_BLOBs

Heuristic extraction splits text into sentences and maps each to
a `PrimitiveObservation` with `label = sentence text`. No
descriptions, no relationships, no semantic abstraction. This is
exactly the shape the re-ingest is supposed to eliminate.

## Provider State at Time of Test

| Provider | Priority | Status | Why |
|----------|----------|--------|-----|
| CLAUDE_CLI | 0 | Nested | Running inside CC session → skipped |
| CC_SDK | 1 | **LEAKING** | Returns 401 error text as valid output |
| GEMINI | 2 | Exhausted | Free-tier 20 req/day quota hit (429) |
| GROQ | 3 | Available | Never reached — cc_sdk returns first |
| ANTHROPIC | 4 | 401 | Credit balance error |
| PERPLEXITY | 5 | Available | Never reached |
| OLLAMA | 6 | Available | Never reached |

## The Config Gap

**cc_sdk does not validate that its output is a real response
vs. an error message.** The `_stream()` exception handler was
designed for a legitimate case: CLI exits non-zero after MCP
server shutdown, but valid messages were already streamed. The
comment at line 170-175 explains this intent. However, it also
catches auth errors where the "output" is an error message, not
a model response.

The fix location is `runtime/cc_sdk.py:213-226`. Before returning
a `CCResult`, the function should check whether `output` contains
known error signatures (e.g. "Failed to authenticate",
"authentication_error", "credit balance").

## Resolution Options

**A. Fix cc_sdk (code change — MEDIUM risk)**
Add error-text detection to `query_cc()` before line 213:
```python
ERROR_SIGNATURES = ["failed to authenticate", "authentication_error",
                    "credit balance", "invalid x-api-key"]
if any(sig in output.lower() for sig in ERROR_SIGNATURES):
    logger.warning("cc_sdk: auth error leaked as output: %s", output[:100])
    return None
```
cc_sdk returns None → model_router falls through to Gemini/Groq.

**B. Upgrade Gemini to paid tier (infra change — LOW risk)**
Pay-as-you-go removes the 20 req/day cap. ~$0.02/day at current
usage. cc_sdk still leaks, but Gemini serves before cc_sdk on the
heavy path if we reorder priorities (or it serves after cc_sdk
fails if we fix A).

**C. Temporarily disable cc_sdk (config change — LOW risk)**
Set `router._cc_sdk_available = False` or add cc_sdk to the
skip list in model_router. Groq serves immediately. Quality
score 0.55 vs Gemini 0.65 — acceptable for batch re-ingest.

**D. Wait for Gemini quota reset (no change)**
Free tier resets daily. Run re-ingest within 20-request budget.
At 3-10 LLM calls per document, this limits to 2-6 documents/day.
The 10 TEXT_BLOBs come from 1 document, so 1 re-ingest run
should fit within quota — IF cc_sdk is also fixed (option A)
or disabled (option C) to prevent it from intercepting first.

## Recommendation

**Option A (fix cc_sdk) is the right fix.** It's a 4-line change
in a single function. The error-signature check is defensive and
won't affect valid responses. Once cc_sdk returns None on auth
errors, the router falls through to Gemini/Groq/Ollama naturally.

Combined with option B (Gemini paid tier) for sustained usage
beyond the re-ingest.

## Build Status

- Phase 0 (inventory): COMPLETE
- Phase 1 (LLM canary): **STOP — heuristic fallback**
- Phase 2 (bulk re-ingest): BLOCKED
- Phase 3 (verification): BLOCKED
- Phase 4 (cleanup): BLOCKED

Re-ingest cannot proceed until at least one LLM provider is
reachable through `call_with_fallback()`. The cc_sdk auth error
leak must be fixed first.
