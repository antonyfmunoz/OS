# UMH Runtime Execution Map

**Audit date:** 2026-04-26
**Scope:** All runtime entrypoints, execution flows, and LLM call paths in umh/

---

## 1. Service Entrypoints

| Service | Container | Entry Command | Python File | Main Function |
|---------|-----------|--------------|-------------|---------------|
| os-discord | os-discord | `python3 umh/interfaces/discord/bot.py` | `umh/interfaces/discord/bot.py` | Discord bot `on_ready()` / `on_message()` event loop |
| os-bot | os-bot | `python3 umh/interfaces/telegram/bot.py` | `umh/interfaces/telegram/bot.py` | Telegram `ApplicationBuilder` polling loop |
| os-monitor | os-monitor | `python3 -u umh/interfaces/discord/dm_monitor.py` | `umh/interfaces/discord/dm_monitor.py` | Instagram DM scraper main loop |
| os-webhook | os-webhook | `python3 umh/interfaces/webhooks/calendly.py` | `umh/interfaces/webhooks/calendly.py` | Flask app on port 8080 |
| os-scraper | os-scraper | `python3 tools/overnight_scrape.py` | `tools/overnight_scrape.py` | One-shot overnight lead scraping (restart: no) |
| CLI | n/a | `python -m umh <command>` | `umh/__main__.py` -> `umh/interfaces/cli.py` | `main()` -> dispatches to run/status/etc. |

---

## 2. Complete Execution Flow Map

There are **two parallel control planes** in the codebase. The runtime_engine
gateway (EOS-specific, production) and the UMH gateway (generic, newer). Both
reach the same model_router for actual LLM calls.

```
                         ┌─────────────────────────────────────────────────────────┐
                         │              EXTERNAL INTERFACES                        │
                         │  Discord Bot  │  Telegram Bot  │  Webhook  │  CLI       │
                         └──────┬────────┴───────┬────────┴─────┬─────┴─────┬──────┘
                                │                │              │           │
                    ┌───────────▼────────────────▼──────────────▼───┐  ┌────▼───────┐
                    │   EOS Gateway (runtime_engine/gateway.py)     │  │ UMH Gateway│
                    │   EOSGateway.handle()                         │  │ (gateway/  │
                    │                                               │  │  entry.py) │
                    │  ┌─ validate                                  │  │            │
                    │  ├─ approval gate                              │  │ translate_ │
                    │  ├─ automation handlers                       │  │ and_run()  │
                    │  ├─ input intelligence                        │  │            │
                    │  ├─ intent classification (LLM via utility)   │  │ utility_   │
                    │  ├─ agent routing                             │  │ llm_call() │
                    │  └─ context building                         │  │            │
                    └──────────────────────┬───────────────────────┘  └──────┬─────┘
                                           │                                │
                    ┌──────────────────────▼────────────────────────┐  ┌────▼──────────┐
                    │  SessionRuntime (session_runtime.py)          │  │  umh/run.py   │
                    │  session_store.get_session() -> .run()        │  │  run()        │
                    │  adds: compaction, goal blending, stats       │  │  9-stage loop │
                    └──────────────────────┬───────────────────────┘  └──────┬────────┘
                                           │                                │
                    ┌──────────────────────▼───────────────────────┐  ┌─────▼──────────────┐
                    │  MultiStrategy (multi_strategy.py)            │  │ execution/engine.py│
                    │  run_with_strategies()                        │  │ execute()          │
                    │  branches for GENERATE/ANALYZE tasks          │  │ dispatch_prompt()  │
                    │  direct call_with_fallback for candidates     │  │ lightweight_       │
                    └──────┬──────────────────────────┬────────────┘  │ execute()          │
                           │ (winner)                 │ (candidates)  └─────┬──────────────┘
                    ┌──────▼───────────┐       ┌──────▼──────────┐         │
                    │ run_via_umh()    │       │ call_with_      │         │
                    │ (execution_      │       │ fallback()      │         │
                    │  spine.py)       │       │ (direct)        │    ┌────▼──────────────┐
                    │  builds Exec-    │       │                 │    │ ExecutionBackend   │
                    │  utionRequest    │       │                 │    │ protocol           │
                    │  -> execute()    │       │                 │    │ (NullBackend —     │
                    └──────┬──────────┘       └────────┬────────┘    │  no adapter file)  │
                           │                           │             └────────────────────┘
                    ┌──────▼───────────────────────────▼────────────────────┐
                    │  ExecutionSpine.run()  (9-stage pipeline)             │
                    │  ┌─ Stage 1: AuthorityCheckStage                     │
                    │  ├─ Stage 2: PromptEnhancementStage                  │
                    │  ├─ Stage 3: ContextAssemblyStage                    │
                    │  ├─ Stage 4: LLMGenerationStage ─────────────────┐   │
                    │  ├─ Stage 5: QualityVerificationStage            │   │
                    │  ├─ Stage 6: StageFilterStage                    │   │
                    │  ├─ Stage 7: OutcomeEvaluationStage              │   │
                    │  ├─ Stage 8: CommitStage                         │   │
                    │  └─ Stage 9: ResponseFooterStage                 │   │
                    └──────────────────────────────────────────────────┘   │
                                                                          │
                    ┌─────────────────────────────────────────────────────▼┐
                    │  model_router (runtime_engine/model_router.py)       │
                    │  call_with_fallback()                                │
                    │                                                      │
                    │  Backend #0: Claude CLI tmux session                  │
                    │  Backend #1: CC SDK (query_cc_sync)                   │
                    │  Backend #2+: Registry providers (via adapters/       │
                    │               model_router.py ModelRouter.call())     │
                    └──────────────────────┬──────────────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────────────┐
                    │  Provider Implementations                           │
                    │  (adapters/model_router.py)                         │
                    │                                                      │
                    │  call_anthropic()   → anthropic.Anthropic()          │
                    │  call_gemini()      → genai.Client()                 │
                    │  call_openai_compatible() → openai.OpenAI()          │
                    │  call_ollama()      → urllib HTTP to /api/generate   │
                    │                                                      │
                    │  Provider priority: Claude CLI > CC SDK > Gemini >   │
                    │                     Groq > Anthropic > OpenAI >      │
                    │                     Perplexity > Ollama              │
                    └─────────────────────────────────────────────────────┘
```

---

## 3. All Entrypoints

### Gateway-level entrypoints

| Entrypoint | File:Line | Called By | Reaches execute()? | Notes |
|------------|-----------|-----------|---------------------|-------|
| `EOSGateway.handle()` | `umh/runtime_engine/gateway.py:608` | Discord bot, Telegram bot, scraper | Yes (via SessionRuntime -> ExecutionSpine -> model_router) | Primary production entrypoint. Routes agent_task/event/status/brief. |
| `EOSGateway.handle_ordered()` | `umh/runtime_engine/gateway.py:1699` | Telegram bot, Discord bot | Yes (calls handle() per part) | Multi-part prompt splitting wrapper. |
| `EOSGateway.classify_intent()` | `umh/runtime_engine/gateway.py:1720` | Discord bot, Telegram bot | No — calls utility_llm_call | Haiku intent classification. |
| `EOSGateway.approve()` | `umh/runtime_engine/gateway.py:1625` | Discord bot (approval commands) | Yes (re-routes through _route_agent_task etc.) | Dequeues and executes approved requests. |
| `translate_and_run()` | `umh/gateway/entry.py:98` | No production callers found | Yes (calls umh.run.run -> dispatch_prompt) | UMH generic entry. Not wired to any interface yet. |
| `utility_llm_call()` | `umh/gateway/entry.py:71` | gateway.py, intent_handler.py, cc_command_handler.py, dm_monitor.py, calendly.py, bot.py, business.py | Yes (calls lightweight_execute -> execute) | Utility LLM calls. Routes through execution engine. |

### Execution-level entrypoints

| Entrypoint | File:Line | Called By | Reaches execute()? | Notes |
|------------|-----------|-----------|---------------------|-------|
| `execute()` | `umh/execution/engine.py:69` | run_via_umh(), lightweight_execute(), umh.run.run() | Yes (IS execute) | The canonical execution function. Delegates to ExecutionBackend. |
| `lightweight_execute()` | `umh/execution/engine.py:140` | utility_llm_call() | Yes (calls execute) | Builds ExecutionRequest and routes through execute(). |
| `dispatch_prompt()` | `umh/execution/engine.py:113` | umh.run.run() Stage 8 | No — calls adapters.base.get_adapter("llm") directly | Used only by the UMH run loop (not production EOS path). |
| `run_via_umh()` | `umh/runtime_engine/execution_spine.py:213` | multi_strategy.py, Telegram bot (media, standup) | Yes (calls execute) | Wraps ExecutionSpine params into ExecutionRequest -> execute(). |
| `ExecutionSpine.run()` | `umh/runtime_engine/execution_spine.py:143` | Not directly called in production | No — runs 9-stage pipeline directly (stage 4 calls call_with_fallback) | Stateless pipeline entry. |
| `run_with_strategies()` | `umh/runtime_engine/multi_strategy.py:578` | SessionRuntime.run() | Partially — winner goes through run_via_umh -> execute; candidates call call_with_fallback directly | Multi-candidate branching layer. |
| `SessionRuntime.run()` | `umh/runtime_engine/session_runtime.py:214` | EOSGateway._route_agent_task() | Yes (via run_with_strategies -> run_via_umh -> execute) | Session-scoped wrapper. Production path for all agent tasks. |

### CLI entrypoints

| Entrypoint | File:Line | Called By | Reaches execute()? | Notes |
|------------|-----------|-----------|---------------------|-------|
| `umh` CLI | `umh/__main__.py:7` -> `umh/interfaces/cli.py:17` | `python -m umh` / pyproject.toml script | Yes (via umh.run.run -> dispatch_prompt) | Generic UMH CLI. |
| `cli._cmd_run()` | `umh/interfaces/cli.py:78` | `python -m umh run "..."` | Yes | Calls umh.run.run(). |

### Model router entrypoints

| Entrypoint | File:Line | Called By | Reaches execute()? | Notes |
|------------|-----------|-----------|---------------------|-------|
| `call_with_fallback()` (module-level) | `umh/runtime_engine/model_router.py:86` | LLMGenerationStage, AgentRuntime.run(), multi_strategy candidate gen, voice_eos_responder, meeting_intelligence | No — direct LLM call | The EOS-specific routing function with Claude CLI + CC SDK + registry chain. |
| `ModelRouter.call_with_fallback()` (instance) | `umh/adapters/model_router.py:579` | email_gps, ceo_agent, world_pulse, execution/runtime.py | No — direct LLM call | Generic router instance method. |
| `ModelRouter.call()` (instance) | `umh/adapters/model_router.py:539` | model_router.call_with_fallback internals, quality_gate, decision_log, daily_sync | No — direct LLM call | Low-level single-model call. |

---

## 4. All Bypass Paths

Bypass = code that reaches an LLM provider without going through the
canonical `execute()` function in `umh/execution/engine.py`.

### 4A. Intentional bypasses (call_with_fallback as the intended path)

| File:Line | What it calls | Why it bypasses execute() | Risk | Notes |
|-----------|--------------|---------------------------|------|-------|
| `umh/stages/llm_generation.py:24` | `call_with_fallback()` | Stage 4 of ExecutionSpine IS the LLM call — the spine is the alternative control plane | LOW | This is the canonical production LLM path. The spine never goes through execute(). |
| `umh/runtime_engine/agent_runtime.py:270` | `call_with_fallback()` | AgentRuntime.run() is the legacy per-module LLM call path | MEDIUM | Used by orchestrator, portfolio_advisor, human_intelligence, user_model, skill_improvement. Should migrate to gateway. |
| `umh/runtime_engine/multi_strategy.py:349` | `call_with_fallback()` | Candidate generation — intentionally side-effect-free | LOW | Only winner enters spine. Design is correct. |
| `umh/substrate/voice_eos_responder.py:244` | `call_with_fallback()` | Voice substrate pluggable responder | LOW | Intentional substrate-to-router bridge. |
| `umh/substrate/meeting_intelligence.py:502` | `call_with_fallback()` | Meeting transcript processing | LOW | Real-time meeting context. |
| `umh/substrate/meeting_intelligence.py:1280` | `call_with_fallback()` | Post-meeting summary phrasing | LOW | Fallback to template on failure. |

### 4B. Router instance method bypasses (use ModelRouter.call_with_fallback or .call directly)

| File:Line | What it calls | Why it bypasses execute() | Risk | Notes |
|-----------|--------------|---------------------------|------|-------|
| `umh/runtime_engine/email_gps.py:296` | `router.call_with_fallback()` | Email folder purpose update | MEDIUM | Uses ModelRouter instance, not the EOS module-level function. Misses Claude CLI backend. |
| `umh/runtime_engine/email_gps.py:529` | `router.call_with_fallback()` | Email classification | MEDIUM | Same as above. |
| `umh/runtime_engine/email_gps.py:597` | `router.call_with_fallback()` | Email draft generation | MEDIUM | Same. |
| `umh/runtime_engine/email_gps.py:633` | `router.call_with_fallback()` | Email action extraction | MEDIUM | Same. |
| `umh/runtime_engine/ceo_agent.py:193` | `router.call_with_fallback()` | CEO agent primitive detection | MEDIUM | Uses ModelRouter instance directly. |
| `umh/runtime_engine/world_pulse.py:206` | `router.call_with_fallback()` | World pulse signal analysis | MEDIUM | Same. |
| `umh/runtime_engine/daily_sync.py:223` | `router.call()` | Daily sync agenda generation | MEDIUM | Uses ModelRouter.call() (single model, no fallback chain). |
| `umh/runtime_engine/daily_sync.py:255` | `_router.call()` | Goal alignment generation | MEDIUM | Same. |
| `umh/runtime_engine/decision_log.py:129` | `router.call()` | Decision extraction from messages | MEDIUM | Uses ModelRouter.call() directly. |
| `umh/runtime_engine/quality_gate.py:51` | `router.call()` | Quality gate LLM evaluation | MEDIUM | Called from gateway._validate_output(). |

### 4C. Direct LLM client instantiation (complete bypass of all routing)

| File:Line | What it calls | Why it bypasses execute() | Risk | Notes |
|-----------|--------------|---------------------------|------|-------|
| `umh/interfaces/discord/dm_monitor.py:44` | `genai.Client(api_key=...)` | Instagram screenshot OCR via Gemini Vision | HIGH | Hardcoded `gemini-2.0-flash` model (deprecated). No rate limiting, no cost tracking, no fallback. No gateway, no execute(), no model_router. |
| `umh/interfaces/discord/dm_monitor.py:466` | `gemini_client.models.generate_content()` | Actual vision call for DM screenshot parsing | HIGH | Direct Gemini call bypassing entire control plane. |
| `umh/runtime_engine/embedding_engine.py:55` | `genai.Client(api_key=...)` | Embedding generation via Gemini | LOW | Embedding is not a generative LLM call. Different capability. Intentional. |
| `umh/runtime_engine/agent_runtime.py:115` | `anthropic.Anthropic(api_key=...)` | Deprecated `.client` property | LOW | Marked deprecated with warning. Only triggers if legacy code accesses `.client`. |
| `umh/adapters/model_router.py:337` | `anthropic.Anthropic(api_key=...)` | `call_anthropic()` provider impl | N/A | This IS the model_router internal — not a bypass. |
| `umh/adapters/model_router.py:379` | `OpenAI(api_key=...)` | `call_openai_compatible()` provider impl | N/A | Same — model_router internal. |
| `umh/adapters/model_router.py:460` | `genai.Client(api_key=...)` | `call_gemini()` provider impl | N/A | Same — model_router internal. |

### 4D. run_via_umh() direct calls (bypass gateway but use execute)

| File:Line | What it calls | Why it bypasses gateway | Risk | Notes |
|-----------|--------------|------------------------|------|-------|
| `umh/interfaces/telegram/bot.py:2316` | `run_via_umh()` | Media file processing — no gateway context needed | MEDIUM | Bypasses EOSGateway (no approval gate, no input intelligence, no intent classification). |
| `umh/interfaces/telegram/bot.py:3138` | `run_via_umh()` | Team standup generation | MEDIUM | Same — direct spine call bypasses gateway-level concerns. |

### 4E. AgentRuntime.run() bypasses (use call_with_fallback via AgentRuntime)

| File:Line | What it calls | Why it bypasses | Risk | Notes |
|-----------|--------------|-----------------|------|-------|
| `umh/runtime_engine/orchestrator.py:1382,1440` | `self._runtime.run()` | Morning cycle / orchestrator tasks | MEDIUM | Bypasses gateway + execute(). Goes AgentRuntime -> call_with_fallback directly. |
| `umh/runtime_engine/portfolio_advisor.py:264,297,366` | `self._runtime.run()` | Portfolio analysis | MEDIUM | Same path. |
| `umh/runtime_engine/human_intelligence.py:275,357,537,634` | `self._runtime.run()` | Human intelligence queries | MEDIUM | Same path. |
| `umh/runtime_engine/user_model.py:376` | `self._runtime.run()` | User model update | MEDIUM | Same path. |
| `umh/runtime_engine/skill_improvement.py:176,398` | `self._runtime.run()` | Skill evaluation/improvement | MEDIUM | Same path. |
| `umh/runtime_engine/session_interface.py:433` | `self._runtime.run()` | Session interface run | MEDIUM | Same path — note: this is SessionRuntime._runtime not the gateway SessionRuntime. |

---

## 5. Risk Classification

### HIGH Risk

| Item | File | Issue |
|------|------|-------|
| **dm_monitor Gemini direct call** | `umh/interfaces/discord/dm_monitor.py:44,466` | Direct `genai.Client()` instantiation with hardcoded `gemini-2.0-flash` (deprecated model). No rate limiting, no cost tracking, no fallback, no observability. Completely bypasses model_router, execute(), and gateway. |

### MEDIUM Risk

| Item | File | Issue |
|------|------|-------|
| **email_gps uses ModelRouter instance** | `umh/runtime_engine/email_gps.py:296,529,597,633` | Calls `get_router().call_with_fallback()` (adapters layer). Misses EOS-specific Claude CLI backend (#0) and CC SDK backend (#1). Gets only the generic provider chain. |
| **ceo_agent uses ModelRouter instance** | `umh/runtime_engine/ceo_agent.py:193` | Same — misses Claude CLI and CC SDK. |
| **world_pulse uses ModelRouter instance** | `umh/runtime_engine/world_pulse.py:206` | Same. |
| **daily_sync uses ModelRouter.call()** | `umh/runtime_engine/daily_sync.py:223,255` | Uses `.call()` not `.call_with_fallback()`. Single model attempt, no fallback chain at all. |
| **decision_log uses ModelRouter.call()** | `umh/runtime_engine/decision_log.py:129` | Same — single model, no fallback. |
| **quality_gate uses ModelRouter.call()** | `umh/runtime_engine/quality_gate.py:51` | Same — single model, no fallback. |
| **AgentRuntime.run() callers** | orchestrator, portfolio_advisor, human_intelligence, user_model, skill_improvement | These call AgentRuntime.run() which calls `call_with_fallback()` directly. Bypasses gateway (no approval gate, no input intelligence, no session management, no logging). Works but ungoverned. |
| **Telegram direct run_via_umh()** | `umh/interfaces/telegram/bot.py:2316,3138` | Bypasses EOSGateway for media processing and standup. No approval gate, no intent classification. |

### LOW Risk (Intentional Design)

| Item | File | Issue |
|------|------|-------|
| **LLMGenerationStage** | `umh/stages/llm_generation.py:24` | Calls call_with_fallback. This IS the production path — the spine is an alternative to execute(), not subordinate to it. |
| **multi_strategy candidates** | `umh/runtime_engine/multi_strategy.py:349` | Direct call_with_fallback for candidate generation. By design — no side effects for rejected candidates. |
| **voice_eos_responder** | `umh/substrate/voice_eos_responder.py:244` | Substrate voice hook. Intentional direct bridge to model_router. |
| **meeting_intelligence** | `umh/substrate/meeting_intelligence.py:502,1280` | Real-time meeting processing. Direct call_with_fallback is appropriate. |
| **embedding_engine** | `umh/runtime_engine/embedding_engine.py:55` | Embedding is not generative LLM. Different capability. |
| **AgentRuntime.client** | `umh/runtime_engine/agent_runtime.py:115` | Deprecated property with warning. No known active callers. |
| **utility_llm_call()** | `umh/gateway/entry.py:71` | Routes through lightweight_execute -> execute(). Properly governed. |

---

## 6. Structural Observations

### Two Parallel Control Planes

The codebase has TWO execution paths to LLM providers:

1. **EOS Production Path** (runtime_engine):
   ```
   Interface -> EOSGateway.handle() -> SessionRuntime.run()
     -> run_with_strategies() -> run_via_umh() -> execute()
     -> [NullBackend — no adapter exists]
     
   AND (parallel in the spine):
     -> ExecutionSpine.run() -> LLMGenerationStage
     -> call_with_fallback() -> providers
   ```

2. **UMH Generic Path** (not wired to production):
   ```
   CLI -> umh.run.run() -> dispatch_prompt() -> adapters.base.get_adapter("llm")
   
   OR:
   translate_and_run() -> umh.run.run() -> same
   ```

### The execute() Bypass Is By Design

The `umh/execution/engine.py:execute()` function delegates to an
`ExecutionBackend`. The file `umh/adapters/umh_execution.py` does NOT exist,
so `_default_backend()` returns `NullExecutionBackend` which rejects all
requests. This means:

- `run_via_umh()` calls `execute()` which hits NullBackend and fails
- The actual LLM call happens in `ExecutionSpine.run()` Stage 4 via
  `call_with_fallback()`, which never touches `execute()`
- `lightweight_execute()` -> `execute()` also hits NullBackend

**The entire execute() path is dead for LLM generation.** LLM calls flow
through the spine's LLMGenerationStage -> call_with_fallback() exclusively.

However, `run_via_umh()` ALSO calls `execute()` — the SpineResult it returns
likely comes from the `run_with_strategies()` path which internally uses
`ExecutionSpine.run()` (not `execute()`). The `execute()` call in
`run_via_umh()` returns a FAILED result (NullBackend), but the code at
line 296 checks for SUCCEEDED status. This means **run_via_umh() always
returns the error path** unless the backend is configured.

Wait — re-reading: `run_with_strategies()` calls `run_via_umh()` for the
winner. But `run_via_umh()` calls `execute()` which returns FAILED. So the
winning candidate's post-processing (memory, feedback) is lost because
run_via_umh always returns an error.

**Critical finding: run_via_umh() -> execute() is dead code.**

`run_via_umh()` calls `execute()` which delegates to `get_execution_backend()`.
No code anywhere calls `set_execution_backend()` with a real implementation.
The fallback `NullExecutionBackend` always returns `ExecutionStatus.REJECTED`.
Therefore `run_via_umh()` ALWAYS returns `SpineResult("No execution backend configured")`.

**Why production still works:**

The default task type in `EOSGateway._route_agent_task()` is `TaskType.ANALYZE`
(line 1220 and 1290-1294). The multi-strategy layer's `STRATEGY_ENABLED_TYPES`
is `{"generate", "analyze"}`. So for the default path:

1. `SessionRuntime.run()` calls `run_with_strategies(task_type=ANALYZE)`
2. `is_strategy_eligible("analyze")` returns True
3. Candidates are generated via **direct `call_with_fallback()`** (lines 673-685)
   — this WORKS because it bypasses execute() entirely
4. Winner is selected (line 703)
5. Winner is committed via `commit_pipeline.commit_winner()` (line 754)
6. A `SpineResult` is constructed directly from the winner output (line 776)
   — this NEVER calls run_via_umh()

So the common production path works. **But for non-eligible task types**
(score, classify, summarize, fast_response), `run_with_strategies()` falls
through to `run_via_umh()` at line 617 which returns the NullBackend error.

The system is largely protected by accident:
- The gateway defaults to `TaskType.ANALYZE` (strategy-eligible)
- `TaskType["STRATEGY"]` raises KeyError, caught at line 1293, falls back
  to ANALYZE (strategy-eligible)
- Most intents map to ANALYZE or GENERATE (both eligible)
- The only intent that maps to a non-eligible type is JOURNAL -> SUMMARIZE
- Valid non-eligible TaskType values: SCORE, CLASSIFY, SUMMARIZE, FAST_RESPONSE

**Affected path:** Any request that sets `task_type` to SUMMARIZE, SCORE,
CLASSIFY, or FAST_RESPONSE will silently receive "No execution backend
configured" as the response. JOURNAL intent from Discord is the most likely
trigger in production.

**The direct `run_via_umh()` calls in Telegram bot** (lines 2316, 3138) are
also affected — they pass `TaskType.ANALYZE` so they are strategy-eligible
and work correctly.

**Root cause:** `umh/adapters/umh_execution.py` was never created. The
`run_via_umh()` function was a migration entrypoint that was never fully
wired up.

### Missing ExecutionBackend Adapter

`umh/execution/interfaces.py:92` tries to import
`umh.adapters.umh_execution.get_execution_backend_adapter`. This module
does not exist. The fallback is `NullExecutionBackend` which rejects all
requests. This is the root cause of the broken execute() path.

---

## 7. Direct LLM Client Instantiation Summary

| Provider | File | Line | Context |
|----------|------|------|---------|
| Anthropic | `umh/adapters/model_router.py` | 337 | `call_anthropic()` — model_router internal (OK) |
| Anthropic | `umh/runtime_engine/agent_runtime.py` | 115 | Deprecated `.client` property (deprecated) |
| Gemini | `umh/adapters/model_router.py` | 460 | `call_gemini()` — model_router internal (OK) |
| Gemini | `umh/runtime_engine/embedding_engine.py` | 55 | Embedding only (OK — different capability) |
| Gemini | `umh/interfaces/discord/dm_monitor.py` | 44 | **Direct vision call — full bypass (HIGH risk)** |
| OpenAI | `umh/adapters/model_router.py` | 379 | `call_openai_compatible()` — model_router internal (OK) |
| Ollama | `umh/adapters/model_router.py` | 406-446 | `call_ollama()` via urllib — model_router internal (OK) |
| Ollama | `umh/adapters/llm.py` | 29-76 | OllamaLLMAdapter — UMH generic adapter (OK) |

---

## 8. File Reference Index

### Core Execution Files
- `umh/execution/engine.py` — execute(), dispatch_prompt(), lightweight_execute()
- `umh/execution/interfaces.py` — ExecutionBackend protocol, singleton management
- `umh/execution/contract.py` — ExecutionRequest, ExecutionResult dataclasses
- `umh/execution/pipeline.py` — ExecutionPipeline orchestrator
- `umh/execution/stages.py` — StageContext dataclass
- `umh/execution/runtime.py` — RuntimeResult, execute_with_fallback() (unused)

### Gateway Files
- `umh/gateway/entry.py` — UMHInput/UMHOutput, translate_and_run(), utility_llm_call()
- `umh/gateway/__init__.py` — re-exports
- `umh/runtime_engine/gateway.py` — EOSGateway (production gateway)

### Spine + Pipeline Files
- `umh/runtime_engine/execution_spine.py` — ExecutionSpine, run_via_umh(), SpineResult
- `umh/stages/llm_generation.py` — LLMGenerationStage (Stage 4)
- `umh/stages/authority.py` — AuthorityCheckStage (Stage 1)
- `umh/stages/enhancement.py` — PromptEnhancementStage (Stage 2)
- `umh/stages/context_assembly.py` — ContextAssemblyStage (Stage 3)
- `umh/stages/quality.py` — QualityVerificationStage (Stage 5)
- `umh/stages/stage_filter.py` — StageFilterStage (Stage 6)
- `umh/stages/outcome.py` — OutcomeEvaluationStage (Stage 7)
- `umh/stages/commit.py` — CommitStage (Stage 8)
- `umh/stages/footer.py` — ResponseFooterStage (Stage 9)

### Model Router Files
- `umh/adapters/model_router.py` — Generic ModelRouter, provider call implementations
- `umh/runtime_engine/model_router.py` — EOS-specific wrapper, call_with_fallback(), Claude CLI + CC SDK

### Session / Strategy Files
- `umh/runtime_engine/session_runtime.py` — SessionRuntime (session-scoped spine wrapper)
- `umh/runtime_engine/session_store.py` — SessionStore (in-memory session registry)
- `umh/runtime_engine/multi_strategy.py` — run_with_strategies() (multi-candidate branching)

### Run Loop
- `umh/run.py` — UMH 9-stage run loop (generic, not wired to production)
- `umh/interfaces/cli.py` — CLI interface

### Interface Files
- `umh/interfaces/discord/bot.py` — Discord bot (primary interface)
- `umh/interfaces/telegram/bot.py` — Telegram bot
- `umh/interfaces/discord/dm_monitor.py` — Instagram DM monitor
- `umh/interfaces/webhooks/calendly.py` — Calendly webhook
- `umh/interfaces/discord/handlers/intent_handler.py` — Discord intent routing

### Docker
- `runtime/docker-compose.yml` — All 5 service definitions
