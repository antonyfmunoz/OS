# UMH Model Router Architecture

Phase: 14.6B-UMH | Status: DRAFT | Provenance: CODE_RESOLVED_CURRENT_TRUTH

Location: adapters/models/model_router.py (1,442 lines)

## Architecture

ModelRouter is the central intelligence routing module. All LLM calls in UMH flow through call_with_fallback().

### Provider Chain (PROVIDER_PRIORITY)
0. CLAUDE_CLI -- tmux session backend (Backend #0)
1. CC_SDK -- Claude Code Agent SDK via Max subscription (Priority 0, no API cost)
2. GEMINI -- Google Gemini 2.5 Flash via Python SDK
3. GROQ -- Groq API
4. ANTHROPIC -- Anthropic API (when credits available)
5. PERPLEXITY -- Perplexity API
6. OLLAMA -- Local Ollama (gemma3:4b)
7. CODEX -- Codex CLI adapter
8. HERMES -- Hermes CLI adapter
9. OPENCODE -- OpenCode CLI adapter

### Fast Path (PROVIDER_PRIORITY_FAST)
For fast task types: fast_response, conversation, score, classify, summarize
Uses a different priority ordering optimized for latency.

### Dual-Path Routing
- Heavy tasks: Full provider chain with quality escalation
- Fast tasks: Fast priority chain, skip expensive providers

### Circuit Breaker
- Exponential backoff: 30s base, 300s cap
- Triggers after consecutive all-provider failures
- Auto-recovers after cooldown period

### Quality Escalation
- Threshold: 0.40
- Below threshold: escalate to cc_sdk for higher quality
- Tracks quality scores per provider

### Deterministic Fallback
- _deterministic_router_response() -- intent-aware responses when ALL LLMs fail
- Intent patterns: greeting, question, command, status, analysis, schedule, send
- Ensures system ALWAYS produces output, even with zero providers available

### Vision Support
- Images route to vision-capable providers (Gemini, Anthropic)
- Automatic detection from input content

### Adversarial Code Review
- adversarial_code_review() function
- CC writes code, Codex reviews adversarially, CC synthesizes patterns
- Used for code quality verification

### Claude CLI Backend (model_router.py lines 905-1100)
- Detects running tmux sessions
- Routes through host's Claude Code CLI
- Session targeting via EOS_ROUTER_CLAUDE_CLI_SESSION env var
- OAuth token injection from ancestor process

## CC SDK Adapter (adapters/models/cc_sdk.py, 464 lines)

- Uses claude-agent-sdk for subprocess transport
- OAuth token injection from /proc/<pid>/environ
- Error-leak detection (_is_error_leak()) catches auth/quota errors streamed as text
- Session persistence per agent (_agent_sessions)
- Nested session detection (skips if already inside Claude Code)
- Orphaned process cleanup (_kill_orphaned_claude_procs)
- Timeout: 120s default, configurable via CC_SDK_TIMEOUT_SECONDS
- Backpressure gate via get_system_state().allow_execution()

## Agent Runtime (adapters/models/agent_runtime.py, 580 lines)

- AgentRuntime class routing to Haiku/Sonnet based on task type
- RateLimiter: 30 calls/min, 500 calls/hour
- AuthorityEngine integration
- ModelPreferences from user profile
- Skill registry integration
- NAMING DEBT: imports EntrepreneurOSContext (should be SubstrateContext)

## LLM Adapter (adapters/models/llm_adapter.py, 91 lines)

- Thin substrate-compliant wrapper around call_with_fallback()
- Implements Adapter protocol from adapters/protocol.py
- Registered as boot adapter in Substrate.__init__

## Routing Config (adapters/models/routing/)

- config.py (128 lines) -- RoutingConfig with per-capability provider preferences
- capabilities.py (123 lines) -- Capability definitions for routing

## Naming Debt

| Location | Issue |
|----------|-------|
| model_router.py line 2 | Docstring says "for EOS" |
| model_router.py line 121 | [EOS] prefix in circuit breaker message |
| model_router.py lines 908, 912 | EOS_ROUTER_CLAUDE_CLI_ENABLED env var |
| model_router.py line 1083 | EOS_ROUTER_CLAUDE_CLI_TARGET env var |
| model_router.py line 1086 | EOS_ROUTER_CLAUDE_CLI_SESSION env var |
| model_router.py lines 893, 937 | Comments reference "EOS agent calls" |
| cc_sdk.py line 2 | Docstring says "for EOS" |
| agent_runtime.py | Imports EntrepreneurOSContext |

## Task Type Routing

TaskType enum (substrate/contracts/agent_types.py, 20 values):
CONVERSATION, COMMAND, ANALYSIS, QUESTION, STRATEGIC, BRIEF, REPORT, RESEARCH, CREATIVE, CODING, DATA_PROCESSING, DECISION, PLANNING, DELEGATION, FOLLOW_UP, EVALUATION, FAST_RESPONSE, STRUCTURED_DATA, SCORE, COORDINATE

Heavy tasks: STRATEGIC, ANALYSIS, DECISION, RESEARCH, PLANNING, CREATIVE, CODING
Fast tasks: FAST_RESPONSE, CONVERSATION, SCORE, STRUCTURED_DATA

## Cost Tracking

- COST_PER_MILLION_TOKENS dict in agent_types.py
- Per-provider cost tracking in routing results
- CC SDK: no API cost (Max subscription)
- Ollama: no cost (local)

## Gaps

1. EOS naming throughout model_router.py and cc_sdk.py
2. agent_runtime.py still imports EntrepreneurOSContext
3. No per-projection model routing (all projections share same routing config)
4. No model version pinning (uses latest from each provider)
5. Circuit breaker state is in-memory (resets on restart)
6. Quality scoring threshold (0.40) may need tuning
