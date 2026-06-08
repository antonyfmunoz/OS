# Phase 14.13K — Provider Router Priority Correction

**Date:** 2026-06-07
**Status:** SHIPPED
**Scope:** adapters/models/model_router.py, scripts/router_claude_runtime_debug.py

---

## Bug

Claude CLI was registered as global Backend #0 in `call_with_fallback()`. Every task type — including `fast_response`, `classify`, `score`, `summarize` — attempted the Claude CLI tmux session first. If CLI was unavailable (Docker, no tmux, session missing), the router waited for the full timeout before falling through to purpose-based routing where Groq and Beast were already correctly positioned as first-choice providers for fast tasks.

This violated the provider doctrine: use the best essential runtime for the job, not a global default.

## Fix

### `_CLI_ELIGIBLE_PURPOSES` gate

Added a frozenset of purposes that warrant Claude CLI as Backend #0:

```
advise_founder, plan_architecture, build_code, autonomous_execution, decompose_goal
```

The `purpose` is now resolved **before** the CLI gate check (moved `_resolve_purpose()` earlier in `call_with_fallback()`). CLI only fires when `purpose in _CLI_ELIGIBLE_PURPOSES`.

### Fast tasks skip CLI entirely

| Task Type | Purpose | CLI? | Provider Chain |
|-----------|---------|------|----------------|
| fast_response | quick_triage | No | Groq -> Beast -> VPS Ollama |
| classify | classify_intent | No | Groq -> Beast -> VPS Ollama |
| score | score_quality | No | Groq -> Beast -> VPS Ollama |
| summarize | summarize | No | Groq -> Beast -> VPS Ollama -> CC SDK |
| research | research_grounding | No | Perplexity -> Groq -> Beast |
| conversation | advise_founder | Yes | CLI -> CC SDK -> Beast -> Groq |
| code | build_code | Yes | CC SDK -> Beast -> VPS Ollama -> Groq |
| strategic | advise_founder | Yes | CLI -> CC SDK -> Beast -> Groq |
| plan | plan_architecture | Yes | CLI -> CC SDK -> Beast |
| CEO override | advise_founder | Yes | CLI -> CC SDK -> Beast -> Groq |

### Quality scoring per-model granularity

`PROVIDER_QUALITY` now distinguishes Beast from VPS Ollama:

- `beast-ollama`: 0.55 (14B parameter model, competitive with Groq)
- `ollama` (VPS): 0.35 (0.5B emergency model)

`_should_escalate()` and `_estimate_quality_score()` now accept the registry key (`beast-ollama`) instead of the provider enum value (`ollama`), enabling per-model quality baselines.

### Skip length penalty for fast purposes

For `quick_triage`, `classify_intent`, `score_quality`, and `status_report` purposes, the length-based quality penalty is skipped. Short answers (e.g., "4" for "what is 2+2?") are expected and correct for these task types.

Previously, a 1-character correct answer from Beast scored 0.30 (below the 0.40 escalation threshold) and triggered unnecessary escalation through the entire provider chain.

### Dead code removed

- `PROVIDER_PRIORITY_FAST`: defined but never referenced after purpose-based routing was added.
- `_HAIKU_TOKEN_CAPS`: defined but never referenced (legacy from Anthropic API routing era).

### Last-resort priority reordered

`PROVIDER_PRIORITY` (used only for the sweep of remaining untried providers after purpose routing exhausts) now puts Groq (fast/free) and Ollama (always-on) first, instead of Claude CLI which was redundant in the sweep.

---

## Verification

### Docker restart

```
docker restart os-discord
```

Container started clean. New code confirmed live via `inspect.signature(_should_escalate)` showing the updated `['output', 'provider_key', 'purpose']` parameter list.

### Fast path test (inside Docker)

```
task_type=fast_response -> purpose=quick_triage
CLI gate: skipped (quick_triage not in _CLI_ELIGIBLE_PURPOSES)
Provider chain: groq-llama -> beast-ollama -> ollama-qwen
Result: Groq responded "4" in 3202ms
```

No CLI timeout. No escalation. Correct answer from Groq on first try.

### Heavy path test (inside Docker)

```
task_type=conversation -> purpose=advise_founder
CLI gate: eligible but env-disabled in Docker
Provider chain: claude_cli (skipped) -> cc_sdk (no OAuth) -> beast-ollama (responded)
Result: Beast responded "The capital of France is Paris." in 152s (cold model load)
```

Routing resolved correctly. CLI was eligible but disabled in Docker (no tmux). CC SDK failed (no OAuth token in container). Beast handled the fallback.

### Routing table verification

All 8 tested task types resolve to correct purposes with correct CLI eligibility and correct provider chains. Verified via assertion-based test and Docker `exec` inspection.

---

## Known Provider Blockers (expected, not bugs)

| Provider | Status | Reason |
|----------|--------|--------|
| Perplexity | quota_exhausted | Free tier billing cap hit |
| CC SDK (Docker) | unavailable | No OAuth token inside containers |
| Claude CLI (Docker) | disabled | No tmux session in container environment |
| Anthropic API | auth_failed | API key invalid (no credits on account) |
| Gemini | rate_limited | Free tier 20 req/day exhausted |

These are infrastructure constraints, not routing bugs. The router correctly falls through each and reaches a working provider.

## Provider Health Fresh-Import Caveat

`MODEL_REGISTRY` entries default to `available=False`. Availability is set by `ModelRouter.__init__()` which runs `_check_availability()`. A fresh Python import that reads `MODEL_REGISTRY` without calling `get_router()` or `call_with_fallback()` will see all providers as unavailable. This is correct — the singleton pattern ensures the check runs once per process, and `call_with_fallback()` re-checks on every call for dynamic recovery.

## Beast Operational Notes

- Model: qwen2.5-coder:14b (8.4GB, Q4_K_M quantization)
- Cold load from disk: ~60-150s (model loads into 11GB VRAM on first request after boot)
- Warm inference: ~1.5 tok/s (GTX 1080 Ti Pascal, no tensor cores)
- Quality baseline: 0.55 (above 0.40 escalation threshold for all purposes)

---

## Files Changed

| File | Change |
|------|--------|
| `adapters/models/model_router.py` | CLI purpose gate, quality per-model, length penalty skip, dead code removal |
| `scripts/router_claude_runtime_debug.py` | Updated to reference new exports (`_CLI_ELIGIBLE_PURPOSES` replaces removed `PROVIDER_PRIORITY_FAST`) |

## Verdict

**SHIPPED.** Fast tasks no longer wait on Claude CLI timeout. Provider routing is purpose-driven. Quality scoring is model-aware. Dead code removed. Docker-verified.
