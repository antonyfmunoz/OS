---
name: claude_agent_sdk
description: "Use when building or modifying programmatic Claude Code invocations, cc_sdk wrapper calls, scheduled claude -p scripts, agent orchestration via subprocess, or debugging CC SDK failures."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.anthropic.com/en/docs/claude-code/sdk"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Claude Code CLI v1.x"
sdk_version: "claude-agent-sdk>=0.1.55"
speed_category: slow
trigger: both
effort: high
context: fork
---

# Tool: Claude Agent SDK (CC SDK)

## What This Tool Does

The Claude Agent SDK provides programmatic access to Claude Code as a subprocess.
It enables two modes of invocation:

1. **Python SDK** (`claude-agent-sdk` package) — async streaming interface that
   spawns `claude` CLI as a child process, streams structured messages
   (AssistantMessage, ResultMessage), and manages sessions. Used by EOS as a
   provider in model_router alongside Gemini, Ollama, etc.

2. **CLI direct** (`claude -p`) — pipe a prompt to the Claude Code CLI with
   `--allowedTools`, `--max-budget-usd`, and `--add-dir` flags. Used by EOS
   cron scripts for scheduled maintenance, morning prep, and weekly review.

Core capabilities:
- **Subprocess orchestration** — Claude Code runs as a separate process with
  full tool access (Bash, Read, Write, Edit, Glob, Grep)
- **Session persistence** — sessions can be resumed by ID, preserving context
  across multiple calls within the same agent
- **Budget control** — hard per-call USD budget caps prevent runaway spending
- **Permission modes** — `auto` (no human approval), `allowedTools` whitelist
- **Streaming output** — AssistantMessage blocks arrive as they are generated,
  enabling timeout-with-partial-output patterns

## EOS Integration

### Primary wrapper
`eos_ai/cc_sdk.py` — the single entry point for all Python-side CC SDK usage.
Exposes `query_cc_sync()` (sync) and `query_cc()` (async). Returns `CCResult`
dataclass with output, session_id, latency_ms, provider, model.

### Model router integration
`eos_ai/model_router.py` registers CC SDK as `ModelProvider.CC_SDK` with quality
score 0.85 (highest in the system). Two routing paths:

- **Heavy path** (analysis, generation, code): CC SDK first, then registry
  fallback (Haiku -> Gemini -> Ollama)
- **Fast path** (conversation, classify, score): Haiku first, escalate to
  CC SDK only if quality score < 0.40 (escalation threshold)

Router checks `self._cc_sdk_available` at init time via `shutil.which("claude")`.

### Scheduled scripts (claude -p via cron)
| Script | Schedule | Budget | Tools |
|--------|----------|--------|-------|
| `nightly_maintenance.sh` | 2:00am daily | $0.50 | Bash Read Write Edit Glob Grep |
| `morning_prep.sh` | 5:30am daily | $0.30 | Bash Read Glob Grep |
| `weekly_review.sh` | Sunday 6:00am | $1.00 | Bash Read Write Glob Grep |

All scripts use: `claude -p --allowedTools "..." --add-dir /opt/OS --max-budget-usd N.NN`

### Agent task executor
`scripts/agent_task_executor.py` runs every 5 minutes via cron. It polls Neon
for pending agent tasks, executes them through the cognitive loop (which may
route to CC SDK for heavy tasks), and posts results to Discord.

### Warmup pattern
`services/discord_bot.py` runs `_warmup_cc_sdk()` on startup — sends a minimal
"Ready." prompt with $0.01 budget to pre-load the CC SDK session, reducing
cold start latency for the first real query.

### Nested session guard
`_is_nested_cc_session()` checks `CLAUDE_CODE_SESSION` env var. When EOS is
already running inside a Claude Code session (e.g., during `claude -p` cron
jobs), CC SDK calls are skipped to avoid recursive subprocess spawning.

## Authentication

### Claude Code CLI auth
The `claude` binary authenticates via Anthropic account credentials stored in
`~/.claude/`. This is a one-time interactive login (`claude login`). The CLI
manages its own token refresh.

### API key (Anthropic SDK, separate)
`ANTHROPIC_API_KEY` in `eos_ai/.env` is for direct Anthropic API calls via the
Python SDK. CC SDK does NOT use this key — it uses the CLI's own auth.

### System health check
`eos_ai/system_health.py` verifies CLI availability:
```python
infrastructure["cc_subprocess"] = bool(shutil.which("claude"))
```

### Env vars
```
CLAUDE_CODE_SESSION          — set by CLI when running inside a session
CLAUDE_CODE_STREAM_CLOSE_TIMEOUT — SDK reads from os.environ (default 120000ms)
ANTHROPIC_API_KEY            — NOT used by CC SDK, used by direct Anthropic SDK
```

## Quick Reference

### Python SDK call (sync, via cc_sdk wrapper)
```python
from eos_ai.cc_sdk import query_cc_sync

result = query_cc_sync(
    prompt="Analyze this business situation",
    system="You are a strategic advisor.",
    task_type="analyze",       # analyze|fast_response|generate|code
    agent_id="research_agent", # for session persistence
    max_budget_usd=0.10,       # hard cap per call
    timeout=30.0,              # seconds
)
if result:
    print(result.output)       # str
    print(result.session_id)   # for resume
    print(result.latency_ms)   # int
    print(result.model)        # e.g. "claude-opus-4-6"
```

### Python SDK call (async, direct)
```python
from eos_ai.cc_sdk import query_cc

result = await query_cc(
    prompt="Draft an outreach message",
    task_type="generate",
    agent_id="sales_agent",
    max_budget_usd=0.05,
)
```

### CLI invocation (bash scripts)
```bash
claude -p --allowedTools "Bash Read Write Edit Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.50 \
  "Your prompt here" >> "$LOG" 2>&1
```

### Budget caps by task type (EOS convention)
| Task Type | Budget | Rationale |
|-----------|--------|-----------|
| fast_response | $0.01-0.05 | Quick lookups, classification |
| analyze | $0.05 | Capped in query_cc_sync to force faster completion |
| generate | $0.10 | Standard generation tasks |
| code | $0.10 | Code generation |
| warmup | $0.01 | Session pre-load only |
| nightly cron | $0.50 | Multi-step maintenance |
| weekly cron | $1.00 | Full health audit |

### Concurrent call pattern
```python
# cc_sdk.py uses ThreadPoolExecutor for sync-in-async contexts
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    future = pool.submit(asyncio.run, coro)
    try:
        return future.result(timeout=timeout + 5)
    except concurrent.futures.TimeoutError:
        _kill_orphaned_claude_procs(before_pids)
        future.cancel()
        return None
```

### Error handling pattern
```python
result = query_cc_sync(prompt=prompt, task_type="analyze")
if result is None:
    # CC SDK failed — fall through to next provider
    logger.info("cc_sdk failed, falling back")
```
CC SDK never raises — it returns None on any failure. The caller decides fallback.

## Conceptual Model

```
EOS Intelligence Layer
  |
  +-- model_router.py
  |     |-- HEAVY PATH: cc_sdk → Haiku → Gemini → Ollama
  |     |-- FAST PATH: Haiku → (escalate) cc_sdk → Gemini → Ollama
  |     +-- quality gate: escalate if score < 0.40
  |
  +-- cc_sdk.py (Python wrapper)
  |     |-- query_cc() — async, streams AssistantMessage/ResultMessage
  |     |-- query_cc_sync() — sync wrapper, ThreadPoolExecutor for async contexts
  |     |-- _agent_sessions — dict[agent_id, session_id] for resume
  |     |-- _kill_orphaned_claude_procs() — PID tracking + SIGKILL cleanup
  |     +-- _is_nested_cc_session() — prevent recursive spawning
  |
  +-- claude -p (CLI direct, cron scripts)
        |-- nightly_maintenance.sh — health check, memory compression, cleanup
        |-- morning_prep.sh — pre-day system verification
        +-- weekly_review.sh — full audit + Discord report
```

See references/best_practices.md for rate limits, error codes, and anti-patterns.

## Gotchas

### Exit code 1 = success with warnings (CRITICAL)
The Claude CLI returns exit code 1 when MCP server shutdown produces stderr
noise, even though the response was fully delivered. The SDK raises an exception
on non-zero exit. Before the fix (commit `3b0a87a`), EOS discarded valid Opus
4.6 responses and fell through to Ollama 0.5b. Fix: catch the exception inside
`_stream()` so `output_parts` are preserved. The error arrives via the stream
AFTER valid messages have been yielded.

### Concurrent session blocking
The original `max_workers=1` in ThreadPoolExecutor caused serial blocking when
multiple agents called CC SDK simultaneously. Fix (commit `d0c6ffb`): bumped to
`max_workers=3` and added PID tracking + SIGKILL for orphaned processes on
timeout.

### Nested session infinite recursion
If CC SDK is called from within a `claude -p` session (e.g., a cron script
triggers gateway code that routes to CC SDK), it would spawn a new subprocess
inside the existing one. Guard: `_is_nested_cc_session()` checks
`CLAUDE_CODE_SESSION` env var and returns None immediately.

### Orphaned claude processes on timeout
When `query_cc_sync()` times out, the subprocess may still be running. Without
cleanup, orphaned `claude --print-messages` processes accumulate and consume
memory. The `_kill_orphaned_claude_procs()` function snapshots PIDs before the
call, diffs after timeout, and SIGKILLs any new ones.

### Budget caps silently limit output quality
If `max_budget_usd` is too low for the task complexity, Claude may produce
truncated or shallow output without any error signal. EOS caps analyze tasks
at $0.05 in `query_cc_sync()` to force faster completion, but this means
complex analyses may need to route through cron scripts with higher budgets.

### CLAUDE_CODE_STREAM_CLOSE_TIMEOUT must be set in parent env
The SDK reads `os.environ` in the parent process, not the child. Setting it
via subprocess env dict has no effect. EOS sets it via
`os.environ.setdefault("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "120000")`.

### Warmup latency
First CC SDK call after a fresh CLI install or reboot takes 5-15 seconds
(loading model, MCP servers, etc.). The `_warmup_cc_sdk()` pattern in
discord_bot.py mitigates this by pre-loading during startup with a throwaway
prompt.

### Session state is in-memory only
`_agent_sessions` dict lives in process memory. Docker restarts, cron script
exits, and process crashes lose all session IDs. Sessions cannot be resumed
across process boundaries unless the session_id is persisted externally.
