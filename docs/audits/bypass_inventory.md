# UMH Execution Bypass Inventory

**Date:** 2026-04-26
**Scope:** All Python files under `/opt/OS/umh/`
**Auditor:** Developer Agent
**Status:** Read-only analysis, no files modified

---

## Core Invariant

No signal, decision, action, tool call, device operation, workflow, memory write, or learning update may bypass the UMH control plane. The canonical path is:

```
interface -> gateway -> execute() -> pipeline stages -> model_router -> LLM provider
```

---

## Bypass Inventory

| # | File:Line | Pattern | What It Does | Invariant Violated | Risk | Should Redirect to execute()? | Suggested Fix |
|---|---|---|---|---|---|---|---|
| **1** | `interfaces/discord/dm_monitor.py:44` | `genai.Client(api_key=...)` | Creates a direct Gemini client at module scope for vision/DOM extraction fallback | Direct LLM provider instantiation outside model_router | **CRITICAL** | Yes | Route through model_router with a vision task type, or register as an adapter |
| **2** | `runtime_engine/agent_runtime.py:115` | `anthropic.Anthropic(api_key=...)` | Deprecated `.client` property still returns a raw Anthropic client | Direct LLM provider instantiation outside model_router | **CRITICAL** | Yes | Remove deprecated property entirely; callers should use model_router |
| **3** | `runtime_engine/embedding_engine.py:55` | `genai.Client(api_key=...)` | Direct Gemini client for embedding generation (Tier 2) | Direct LLM provider instantiation outside model_router | **HIGH** | No (embeddings are not generative LLM calls) | Register as an embedding adapter in adapters/base.py; acceptable short-term |
| **4** | `runtime_engine/embedding_engine.py:60` | `google.generativeai` import | Legacy Gemini SDK fallback for embeddings | Direct LLM provider instantiation outside model_router | **HIGH** | No (embeddings) | Same as #3 |
| **5** | `adapters/model_router.py:337` | `anthropic.Anthropic(api_key=...)` | Anthropic API call inside `call_anthropic()` | None -- this IS the canonical provider layer | **INFO** | No | Already correct; this is where provider calls belong |
| **6** | `adapters/model_router.py:460` | `genai.Client(api_key=...)` | Gemini API call inside `call_gemini()` | None -- this IS the canonical provider layer | **INFO** | No | Already correct |
| **7** | `adapters/llm.py:166` | `ollama.available()` | Discovery probe for Ollama adapter registration | None -- adapter discovery layer | **INFO** | No | Already correct; adapter pattern |
| **8** | `runtime_engine/email_gps.py:296` | `router.call_with_fallback(TaskType.ANALYSIS, ...)` | AI-generated folder purpose update | Bypasses execute() pipeline; calls model_router directly | **HIGH** | Yes | Route through gateway.utility_llm_call or full execute() |
| **9** | `runtime_engine/email_gps.py:529` | `router.call_with_fallback(TaskType.FAST_RESPONSE, ...)` | AI email classification into folders | Bypasses execute() pipeline | **HIGH** | Yes | Route through gateway.utility_llm_call |
| **10** | `runtime_engine/email_gps.py:597` | `router.call_with_fallback(TaskType.CONVERSATION, ...)` | AI-drafted email response | Bypasses execute() pipeline | **HIGH** | Yes | Route through gateway.utility_llm_call |
| **11** | `runtime_engine/email_gps.py:633` | `router.call_with_fallback(TaskType.FAST_RESPONSE, ...)` | Extract action items from email | Bypasses execute() pipeline | **HIGH** | Yes | Route through gateway.utility_llm_call |
| **12** | `runtime_engine/world_pulse.py:206` | `router.call_with_fallback(RouterTaskType.MARKET_INTEL, ...)` | Market intelligence signal generation | Bypasses execute() pipeline | **HIGH** | Yes | Route through gateway or execute() with MARKET_INTEL operation |
| **13** | `runtime_engine/ceo_agent.py:193` | `router.call_with_fallback(TaskType.ANALYSIS, ...)` | CEO agent determines which agent roles to spawn | Bypasses execute() pipeline | **HIGH** | Yes | Route through execute() with agent_spawn operation |
| **14** | `runtime_engine/multi_strategy.py:349` | `call_with_fallback(prompt=..., agent_type=...)` | Multi-strategy candidate generation (LLM call per strategy) | Bypasses execute() pipeline | **HIGH** | Partially -- by design it generates candidates pre-selection | Keep but add observer/trace hooks; this is an inner loop of the execution engine |
| **15** | `runtime_engine/agent_runtime.py:270` | `call_with_fallback as _router_call` | AgentRuntime.run() calls model_router directly | Bypasses execute() pipeline | **HIGH** | Yes | AgentRuntime.run() should route through execute() |
| **16** | `substrate/voice_eos_responder.py:244` | `call_with_fallback(prompt=..., task_type=...)` | Voice session responses via model_router | Bypasses execute() pipeline | **HIGH** | Yes | Route through gateway or execute() with voice operation type |
| **17** | `substrate/meeting_intelligence.py:502` | `call_with_fallback(prompt=..., task_type="summarize")` | Meeting transcript summarization | Bypasses execute() pipeline | **HIGH** | Yes | Route through gateway.utility_llm_call |
| **18** | `substrate/meeting_intelligence.py:1280` | `call_with_fallback(prompt=..., task_type="summarize")` | Meeting intervention message refinement | Bypasses execute() pipeline | **HIGH** | Yes | Route through gateway.utility_llm_call |
| **19** | `execution/runtime.py:247` | `router.call_with_fallback(router_task, prompt, ...)` | execute_with_fallback() routing -- part of execution infrastructure | None -- this is a legitimate execution path | **INFO** | No | Already correct; execution runtime calling model_router |
| **20** | `runtime_engine/gateway.py:429` | `utility_llm_call(prompt=..., operation="email_extract")` | Extract email folder instruction from user message | Uses lightweight execute path | **MEDIUM** | Acceptable | utility_llm_call routes through lightweight_execute(); acceptable for utility ops |
| **21** | `runtime_engine/gateway.py:870` | `utility_llm_call(prompt=..., operation="web_search")` | Web search synthesis | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **22** | `runtime_engine/gateway.py:1764` | `utility_llm_call(prompt=..., operation="classify_intent")` | Intent classification | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **23** | `workstation/business.py:372` | `utility_llm_call(prompt=..., operation="bis_gap_fill")` | BIS gap-fill for missing business fields | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **24** | `interfaces/discord/dm_monitor.py:550` | `utility_llm_call(prompt=..., operation="dm_reply_draft")` | DM sales reply draft | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **25** | `interfaces/discord/handlers/intent_handler.py:238` | `utility_llm_call(prompt=..., operation="cloning_loop_check")` | Check if message answers a cloning loop question | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **26** | `interfaces/discord/handlers/cc_command_handler.py:38` | `utility_llm_call(prompt=..., operation="followup_draft")` | Draft follow-up email via !followup command | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **27** | `interfaces/discord/handlers/cc_command_handler.py:102` | `utility_llm_call(prompt=..., operation="date_parse")` | Natural language date parsing | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **28** | `interfaces/discord/handlers/cc_command_handler.py:479` | `utility_llm_call(prompt=..., operation="calendar_extract")` | Extract calendar event details from message | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **29** | `interfaces/webhooks/calendly.py:408` | `utility_llm_call(prompt=..., operation="cancellation_recovery")` | Draft re-engagement email on Calendly cancellation | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **30** | `interfaces/discord/bot.py:3240` | `utility_llm_call(prompt=..., operation="nurture_draft")` | Draft nurture check-in message | Uses lightweight execute path | **MEDIUM** | Acceptable | Same as #20 |
| **31** | `runtime_engine/voice_engine.py:572` | `requests.post(self._ollama_url, json=payload, ...)` | Direct Ollama HTTP call for local LLM queries | Direct LLM provider access outside model_router | **CRITICAL** | Yes | Route through model_router with Ollama backend |
| **32** | `runtime_engine/voice_engine.py:527` | `subprocess.run(['espeak', ...])` | TTS synthesis via espeak CLI | OS operation outside execute() | **LOW** | No | Acceptable; TTS is a non-LLM device operation |
| **33** | `runtime_engine/voice_engine.py:627` | `requests.get('http://localhost:11434/api/tags', ...)` | Ollama health check | Health probe, not inference | **LOW** | No | Acceptable; read-only health check |
| **34** | `interfaces/telegram/bot.py:242` | `subprocess.run(command, shell=True, ...)` | Run arbitrary shell commands from Telegram | OS operation bypassing all safety layers | **CRITICAL** | Yes | Must route through execute() with authority checks, or restrict to allowlisted commands |
| **35** | `interfaces/telegram/bot.py:2238` | `subprocess.run(["ffmpeg", ...])` | FFmpeg voice conversion (OGG to WAV) | OS operation | **LOW** | No | Acceptable; media format conversion is a utility operation |
| **36** | `interfaces/discord/bot.py:2725` | `subprocess.Popen(["python3", ".../portfolio_brief.py"])` | Fire-and-forget script launch from Discord !portfolio | OS operation bypassing execute() | **MEDIUM** | Ideally yes | Should be an execute() operation or at minimum logged |
| **37** | `interfaces/discord/bot.py:2820` | `subprocess.Popen(["python3", ".../eod_sync.py"])` | Fire-and-forget EOD sync from Discord !eod | OS operation bypassing execute() | **MEDIUM** | Ideally yes | Same as #36 |
| **38** | `interfaces/discord/dm_monitor.py:87` | `requests.post(telegram_url, ...)` | Send Telegram notification | External HTTP call (notification) | **LOW** | No | Acceptable; outbound notification, not a decision path |
| **39** | `interfaces/discord/dm_monitor.py:630` | `requests.post(telegram_url, ...)` | Send Telegram alert | External HTTP call (notification) | **LOW** | No | Same as #38 |
| **40** | `interfaces/discord/dm_monitor.py:746` | `requests.get(telegram_url, ...)` | Poll Telegram for updates (approval flow) | External HTTP call (input polling) | **LOW** | No | Acceptable; input collection, not decision-making |
| **41** | `interfaces/webhooks/calendly.py:82` | `requests.post(telegram_url, ...)` | Send Telegram notification on Calendly event | External HTTP call (notification) | **LOW** | No | Same as #38 |
| **42** | `interfaces/webhooks/calendly.py:169` | `requests.post(notion_url, ...)` | Query Notion DB for duplicate check | External HTTP call (data lookup) | **LOW** | No | Acceptable; read-only data query |
| **43** | `interfaces/webhooks/higgsfield.py:39` | `requests.get(url, stream=True, ...)` | Download generated media from Higgsfield | External HTTP call (media download) | **LOW** | No | Acceptable; file download, not decision-making |
| **44** | `runtime_engine/discord_utils.py:130` | `requests.post(webhook_url, ...)` | Post message to Discord webhook | External HTTP call (notification) | **LOW** | No | Acceptable; outbound notification |
| **45** | `runtime_engine/gws_connector.py:82` | `subprocess.run(["npx", "@googleworkspace/cli", ...])` | Google Workspace CLI commands | External service via subprocess | **LOW** | No | Acceptable; GWS is a tooling adapter, not LLM inference |
| **46** | `runtime_engine/cc_sdk.py:222` | `subprocess.run(["pgrep", ...])` | Process management for Claude CLI | OS utility operation | **LOW** | No | Acceptable; process lifecycle management |
| **47** | `runtime_engine/notebooklm_sync.py:58` | `subprocess.run(["nlm", "source", "add", ...])` | NotebookLM CLI source sync | External tool integration | **LOW** | No | Acceptable; sync utility |
| **48** | `substrate/station_daemon.py:360+` | `subprocess.run(["say"/"espeak"/"spd-say", ...])` | TTS playback on workstation | OS device operation | **LOW** | No | Acceptable; local device control |
| **49** | `substrate/station_daemon.py:569` | `subprocess.Popen([app_path, ...])` | Launch applications on workstation | OS device operation | **MEDIUM** | Ideally yes | Should have authority check before launching apps |
| **50** | `substrate/perception.py:629` | `subprocess.run(["git", "status", ...])` | Git status check for perception layer | OS read-only operation | **LOW** | No | Acceptable; read-only system inspection |
| **51** | `substrate/os_controller.py:216+` | `subprocess.run(["xdotool"/"wmctrl"/...])` | Window/keyboard/mouse control on workstation | OS device operations | **MEDIUM** | Partially | Should route through execution_authority for risk gating |
| **52** | `substrate/dispatch_enforcement.py:244` | `subprocess.run(...)` | Subprocess execution with enforcement | Part of enforcement layer | **INFO** | No | Already in enforcement pipeline |
| **53** | `substrate/claude_session_bridge.py:151` | `subprocess.run(["tmux", ...])` | tmux session management for Claude CLI | OS utility | **LOW** | No | Acceptable; infrastructure management |
| **54** | `substrate/local_control.py:609+` | `subprocess.run(["docker"/"systemctl"/...])` | System service management | OS operations | **MEDIUM** | Ideally yes | Should have authority check; service restarts affect production |
| **55** | `substrate/discord_voice_playback.py:211` | `subprocess.run(["espeak", ...])` | TTS synthesis fallback | OS device operation | **LOW** | No | Acceptable; media utility |
| **56** | `adapters/provider_health.py:85` | `requests.post(gemini_url, ...)` | Gemini health probe (1-token inference) | Direct LLM call for health check | **MEDIUM** | No | Acceptable; health probes are infrastructure, not decision paths |
| **57** | `adapters/provider_health.py:116` | `requests.get(groq_url, ...)` | Groq health probe (model list) | Health check HTTP call | **LOW** | No | Acceptable |
| **58** | `adapters/provider_health.py:132` | `requests.get(ollama_url, ...)` | Ollama health probe (tag list) | Health check HTTP call | **LOW** | No | Acceptable |
| **59** | `adapters/workstation_adapter.py:81` | `subprocess.run(...)` | Workstation adapter command execution | Adapter layer | **INFO** | No | Already in adapter pattern |
| **60** | `runtime_engine/cognitive_loop.py:379` | `FeedbackLoop` import + `log_outcome()` | Log feedback outcome in deprecated CognitiveLoop | Feedback write outside commit pipeline | **MEDIUM** | Yes | Should route through stages/commit.py log_feedback or be removed with CognitiveLoop deprecation |
| **61** | `runtime_engine/session_runtime.py:886` | `strategy_pattern_memory.record_outcome(...)` | Record strategy outcome | Internal memory write within session | **INFO** | No | Part of the designed learning pipeline within SessionRuntime |
| **62** | `runtime_engine/session_runtime.py:930` | `world_calibration.record_outcome(...)` | Record world calibration outcome | Internal memory write within session | **INFO** | No | Same as #61 |
| **63** | `runtime_engine/session_runtime.py:1174` | `ws_engine.record_outcome(...)` | Record world state outcome | Internal memory write within session | **INFO** | No | Same as #61 |
| **64** | `runtime_engine/session_runtime.py:2047` | `meta_weight_engine.record_outcome(...)` | Record meta-weight learning signal | Internal memory write within session | **INFO** | No | Same as #61 |
| **65** | `runtime_engine/session_runtime.py:3276` | `save_memory_fabric(...)` | Persist memory fabric to disk | Internal persistence at session end | **INFO** | No | Part of designed persistence pipeline |
| **66** | `runtime_engine/session_runtime.py:3521` | `record_outcome(...)` | External outcome signal application | Internal feedback recording | **INFO** | No | Part of designed feedback pipeline |
| **67** | `run.py:228` | `record_outcome(...)` | Stage 9 feedback recording in canonical run loop | None -- this IS the canonical pipeline | **INFO** | No | Already correct |
| **68** | `runtime_engine/commit_pipeline.py:152` | `log_feedback(...)` | Feedback logging in commit pipeline | None -- this IS the commit pipeline | **INFO** | No | Already correct |
| **69** | `stages/commit.py:49` | `log_feedback()` definition | Feedback function definition | None -- this IS the canonical path | **INFO** | No | Already correct |
| **70** | `world/calibration.py:540` | `self._memory.add_summary(...)` | Calibration memory write | Internal learning update | **INFO** | No | Part of designed learning pipeline |
| **71** | `interfaces/cli.py:132` | `get_adapter(name)` | CLI adapter inspection | Diagnostic/admin tool | **INFO** | No | CLI diagnostics, not production path |

---

## Summary Counts by Risk Level

| Risk Level | Count | Description |
|---|---|---|
| **CRITICAL** | **4** | Direct LLM provider access or dangerous OS operations outside all control |
| **HIGH** | **11** | Direct model_router.call_with_fallback() calls bypassing execute() pipeline |
| **MEDIUM** | **15** | utility_llm_call (lightweight execute), subprocess ops needing authority checks |
| **LOW** | **19** | Health checks, notifications, read-only ops, media utilities |
| **INFO** | **22** | Canonical pipeline components, designed internal memory writes |
| **Total** | **71** | |

---

## Top 5 Most Dangerous Bypasses

### 1. `interfaces/telegram/bot.py:242` -- Arbitrary shell execution (CRITICAL)

`subprocess.run(command, shell=True, ...)` executes any command sent via Telegram with `shell=True`. No authority check, no allowlist, no execute() routing. An attacker with Telegram access (or a social engineering attack on the bot token) can run any command on the VPS as root.

**Impact:** Full system compromise.
**Fix:** Remove `shell=True`, implement a strict command allowlist, and route through execute() with CRITICAL authority level.

### 2. `interfaces/discord/dm_monitor.py:44` -- Direct Gemini client at module scope (CRITICAL)

A raw `genai.Client` is instantiated at import time and used for vision/DOM extraction. This bypasses model_router entirely -- no fallback chain, no rate limiting, no cost tracking, no execution trace.

**Impact:** Untracked LLM spending, no observability, no fallback if Gemini fails.
**Fix:** Route vision calls through model_router with a vision task type, or register a vision adapter.

### 3. `runtime_engine/voice_engine.py:572` -- Direct Ollama HTTP POST (CRITICAL)

`VoiceEngine.query_local()` makes raw HTTP requests to Ollama, completely bypassing model_router. This is a full LLM inference call with no trace, no cost tracking, and no fallback.

**Impact:** Invisible LLM usage, no execution trace, divergent routing logic.
**Fix:** Route through model_router with TaskType.FAST_RESPONSE and let the router handle Ollama.

### 4. `runtime_engine/agent_runtime.py:115` -- Deprecated raw Anthropic client (CRITICAL)

The `.client` property still returns `anthropic.Anthropic()`. While marked deprecated, any caller using this property gets a raw API client with no routing, no fallback, no cost tracking.

**Impact:** If any code still calls `.client`, it makes untracked API calls.
**Fix:** Raise `RuntimeError` instead of returning the client. Force migration.

### 5. `runtime_engine/email_gps.py` -- Four direct router calls (HIGH x4)

Lines 296, 529, 597, 633 all call `router.call_with_fallback()` directly. EmailGPS is a complete LLM-powered subsystem (classify, draft, extract) that operates entirely outside execute(). No pipeline stages, no authority checks, no feedback logging.

**Impact:** All email AI operations are invisible to the execution pipeline. No learning signal, no observability.
**Fix:** Route each operation through `gateway.utility_llm_call()` or create an email execution operation in the run loop.

---

## Files That Should Never Be Modified Without Routing Through execute()

These files contain the canonical execution pipeline. Modifying them incorrectly breaks the control plane for everything:

1. **`umh/run.py`** -- The 9-stage canonical run loop
2. **`umh/execution/engine.py`** -- execute_step() and lightweight_execute()
3. **`umh/execution/harness.py`** -- Execution harness with capability routing
4. **`umh/gateway/entry.py`** -- translate_and_run() and utility_llm_call()
5. **`umh/adapters/model_router.py`** -- Provider-level routing (the bottom of the stack)
6. **`umh/runtime_engine/model_router.py`** -- EOS-specific routing wrapper
7. **`umh/stages/llm_generation.py`** -- The stage that legitimately calls model_router
8. **`umh/stages/commit.py`** -- Feedback and knowledge integration stage
9. **`umh/runtime_engine/commit_pipeline.py`** -- Commit pipeline orchestration
10. **`umh/feedback/loop.py`** -- Outcome recording

---

## Bypasses That Are Intentional/Acceptable and Why

### 1. `adapters/model_router.py` provider calls (Items #5, #6)
These ARE the canonical provider layer. `call_anthropic()` and `call_gemini()` are the functions that model_router dispatches to. They are the bottom of the legitimate call stack.

### 2. `utility_llm_call()` usage (Items #20-30)
`utility_llm_call()` in `gateway/entry.py` routes through `lightweight_execute()` which calls `execute_step()` in `execution/engine.py`. This IS going through the execution engine, just via a lighter path that skips the full 9-stage run loop. Acceptable for classification, extraction, and utility operations that don't need intent compilation, goal tracking, or world model updates.

### 3. `adapters/provider_health.py` probes (Items #56-58)
Health probes are infrastructure operations that test whether providers are reachable. They must work independently of the routing chain (since they inform the routing chain). The Gemini probe does use 1 token of inference, but this is a diagnostic cost, not a decision path.

### 4. SessionRuntime internal memory writes (Items #61-66)
`strategy_pattern_memory.record_outcome()`, `world_calibration.record_outcome()`, `meta_weight_engine.record_outcome()`, and `save_memory_fabric()` are all internal to the SessionRuntime's learning pipeline. They are called as part of the turn lifecycle within the session, which is itself invoked through the execution pipeline. These are the designed learning infrastructure, not bypasses.

### 5. Notification HTTP calls (Items #38-44)
Outbound Telegram notifications, Discord webhooks, and similar are notification delivery, not decisions or LLM calls. They don't affect the control plane or decision-making. Routing them through execute() would add latency and complexity with no safety benefit.

### 6. `run.py:228` and `commit_pipeline.py:152` (Items #67-68)
These ARE the canonical pipeline. `record_outcome()` in run.py is Stage 9 of the 9-stage loop. `log_feedback()` in commit_pipeline.py is the feedback stage of the commit pipeline. These are correct by definition.

### 7. Subprocess calls for media/TTS/git (Items #32, #35, #48, #50, #55)
espeak/ffmpeg/git commands are OS utility operations for media conversion, TTS synthesis, and repository inspection. They do not make decisions, call LLMs, or write to memory. Routing them through execute() would be over-engineering.

### 8. `multi_strategy.py:349` (Item #14)
This is a candidate generation inner loop that runs within the multi-strategy execution engine. It calls model_router directly because it IS part of the execution infrastructure -- it generates strategy candidates that the engine then evaluates. Adding execute() nesting here would create infinite recursion. However, it should have observer/trace hooks added.

---

## Remediation Priority

### Immediate (CRITICAL -- fix before next deploy)
1. **telegram/bot.py:242** -- Replace `shell=True` arbitrary command execution with allowlisted commands behind authority checks
2. **voice_engine.py:572** -- Replace direct Ollama HTTP calls with model_router
3. **agent_runtime.py:115** -- Replace deprecated `.client` property with `raise RuntimeError`

### Short-term (HIGH -- fix within 1 week)
4. **dm_monitor.py:44** -- Remove module-scope Gemini client; route vision through model_router
5. **email_gps.py (4 sites)** -- Route all operations through utility_llm_call
6. **world_pulse.py:206** -- Route through utility_llm_call
7. **ceo_agent.py:193** -- Route through utility_llm_call or execute()
8. **voice_eos_responder.py:244** -- Route through utility_llm_call
9. **meeting_intelligence.py (2 sites)** -- Route through utility_llm_call
10. **agent_runtime.py:270** -- Route AgentRuntime.run() through execute()

### Medium-term (MEDIUM -- as part of next refactor)
11. **station_daemon.py:569** -- Add authority check before app launches
12. **os_controller.py** -- Route through execution_authority for risk gating
13. **local_control.py** -- Add authority check for service management operations
14. **bot.py:2725,2820** -- Replace fire-and-forget Popen with execute() invocations
15. **cognitive_loop.py:379** -- Remove feedback path when CognitiveLoop is fully retired
