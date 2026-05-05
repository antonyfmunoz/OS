# Claude Agent SDK — Creator-Level Best Practices
Source: https://docs.anthropic.com/en/docs/claude-code/sdk
API Version: Claude Code CLI v1.x
SDK Version: claude-agent-sdk>=0.1.55
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

The Claude Agent SDK authenticates through the Claude Code CLI's own credential
store, NOT through `ANTHROPIC_API_KEY`. Authentication is handled by:

1. **CLI login** — `claude login` performs an interactive OAuth-like flow and
   stores credentials in `~/.claude/`. This is a one-time setup per machine.
2. **Max subscription** — CC SDK uses the Claude Code subscription tier (Pro/Max).
   Max plan provides higher rate limits and is what EOS runs on.
3. **No API key needed** — the SDK spawns `claude` as a subprocess. The subprocess
   handles its own auth from the stored credentials.

Env vars relevant to auth:
- `CLAUDE_CODE_SESSION` — set automatically when inside a CC session. Used to
  detect nested sessions.
- `CLAUDE_CODE_STREAM_CLOSE_TIMEOUT` — timeout for stream cleanup (ms). Must be
  set in parent process env (SDK reads os.environ, not subprocess env).
- `ANTHROPIC_API_KEY` — NOT used by CC SDK. Used by direct Anthropic SDK calls.

Token refresh is automatic and handled by the CLI binary. No manual rotation
needed. If auth expires, the CLI prints an error to stderr and exits non-zero.

EOS stores no CC SDK secrets in `.env` — auth lives in the CLI's own config dir.

## Core Operations with Exact Signatures

### Python SDK — ClaudeAgentOptions
```python
from claude_agent_sdk import ClaudeAgentOptions, query

options = ClaudeAgentOptions(
    system_prompt: str | None = None,      # system message prepended to conversation
    max_budget_usd: float = 0.0,           # hard USD cap; 0 = unlimited
    permission_mode: str = "auto",         # "auto" | "allowedTools" | "default"
    max_turns: int = 0,                    # 0 = unlimited, 1 = single-shot
    cli_path: str = "claude",              # path to claude binary
    setting_sources: list[str] = [],       # config sources to load
    resume: str | None = None,             # session_id to resume
)
```

### Python SDK — query() async generator
```python
async for message in query(prompt="...", options=options):
    # message is one of:
    #   AssistantMessage — contains content blocks (TextBlock, ToolUseBlock)
    #   ResultMessage — final message with session_id and result summary
    pass
```

### Python SDK — Message types
```python
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

# AssistantMessage
message.content: list[TextBlock | ToolUseBlock]  # content blocks
message.model: str                                # e.g. "claude-opus-4-6"

# TextBlock
block.text: str  # the actual text content

# ResultMessage
message.session_id: str   # session ID for resume
message.result: str       # final result summary (may be empty)
```

### CLI invocation
```bash
claude -p "prompt"                           # basic prompt
claude -p --allowedTools "Bash Read" "..."   # tool whitelist
claude -p --max-budget-usd 0.50 "..."       # budget cap
claude -p --add-dir /opt/OS "..."            # additional context dir
claude -p --output-format json "..."         # structured JSON output
claude -p --model opus "..."                 # model selection
```

### EOS wrapper — query_cc_sync()
```python
def query_cc_sync(
    prompt: str,
    system: str = "",
    task_type: str = "analyze",         # maps to effort via EFFORT_MAP
    session_id: str | None = None,      # explicit session to resume
    max_budget_usd: float = 0.10,       # hard cap
    agent_id: str | None = None,        # for session persistence
    timeout: float = 30.0,              # seconds
) -> CCResult | None:
    """Returns CCResult on success, None on any failure. Never raises."""
```

### EOS wrapper — CCResult
```python
@dataclass
class CCResult:
    output: str            # combined text from all AssistantMessage TextBlocks
    session_id: str        # for resume
    latency_ms: int        # wall clock time
    provider: str = "cc_sdk"
    model: str = ""        # e.g. "claude-opus-4-6"
```

## Pagination Patterns

N/A — The Claude Agent SDK is not a paginated API. Each call returns a single
streamed response. For multi-turn conversations, use session resume:

```python
# First call
result = query_cc_sync(prompt="Start analysis", agent_id="analyst")
# Second call resumes the same session automatically
result = query_cc_sync(prompt="Continue with part 2", agent_id="analyst")
```

Session IDs are persisted per-agent in `_agent_sessions` dict. The SDK handles
context window management internally.

## Rate Limits

### CLI-level limits (Claude Code subscription)
- **Pro plan**: ~20 Opus messages per hour, ~100 Sonnet messages per hour
- **Max plan** (EOS uses this): ~200 Opus messages per hour, unlimited Sonnet
- Rate limit errors surface as exit code non-zero with stderr containing "rate"
- No explicit rate limit headers — the CLI binary manages retries internally

### Subprocess concurrency limits
- EOS caps at `max_workers=3` in ThreadPoolExecutor
- Each CC SDK call spawns a separate `claude` process (~200-500MB RSS)
- On a 4GB VPS, 2 concurrent calls is the practical limit before OOM
- The `--print-messages` flag is used internally by the SDK for streaming

### Budget-based limits
- `max_budget_usd` is a hard cap — Claude stops mid-response if exceeded
- EOS convention: $0.01 warmup, $0.05 fast/analyze, $0.10 generate/code
- Cron scripts: $0.30-$1.00 for multi-step operations

### Backoff strategy
CC SDK returns None on rate limits. Model router falls through to the next
provider (Gemini, Ollama). No explicit retry loop — the provider chain IS
the retry strategy.

## Error Codes and Recovery

### CLI exit codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 0 | Success | Use output |
| 1 | Warning (e.g. MCP server shutdown noise) | **Trust output if output_parts is non-empty** — this was the exit-code-1 bug |
| 2 | Hard failure (auth, crash, no output) | Return None, fall through to next provider |

### SDK exceptions
The `claude-agent-sdk` raises exceptions on non-zero exit codes. EOS catches
these inside `_stream()`:
```python
except Exception as e:
    logger.debug("cc_sdk _stream: caught %s (output_parts=%d)", e, len(output_parts))
```
The key insight: exceptions arrive AFTER valid messages have already been yielded.
So `output_parts` will contain the real response even when the exception fires.

### Error classification in cc_sdk.py
```python
if "rate" in err_str or "429" in err_str:    # Rate limited
elif "auth" in err_str or "401" in err_str:  # Auth error (expired login)
elif "timeout" in err_str:                    # Timeout
else:                                         # Generic failure
```
All paths return None. The model router handles fallback.

### Stderr patterns
- `MCP server shutdown` — benign, exit code 1, output is valid
- `authentication_error` — CLI login expired, run `claude login`
- `rate_limit_exceeded` — Max plan quota hit, wait or fall through
- `SIGKILL` — EOS killed orphaned process, no output available

## SDK Idioms

### Import pattern (lazy, inside function)
```python
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ResultMessage,
        AssistantMessage,
        TextBlock,
        query,
    )
except ImportError:
    logger.error("claude-agent-sdk not installed")
    return None
```
EOS imports lazily inside `query_cc()` so the module loads even when the SDK
is not installed. This is critical — services that don't need CC SDK shouldn't
fail on import.

### Async streaming with sync wrapper
The SDK's `query()` is an async generator. EOS wraps it:
1. `query_cc()` — async, uses `asyncio.wait_for()` for timeout
2. `query_cc_sync()` — sync, uses `asyncio.run()` or `ThreadPoolExecutor`
   depending on whether an event loop is already running

### Session persistence pattern
```python
_agent_sessions: dict[str, str] = {}  # agent_id -> session_id

# After successful call:
if agent_id and result_session_id:
    _agent_sessions[agent_id] = result_session_id

# On next call for same agent:
resolved_session = _agent_sessions.get(agent_id)
if resolved_session:
    options.resume = resolved_session
```

### Never-raise pattern
CC SDK wrapper NEVER raises exceptions. Every failure path returns None.
This is intentional — the model router treats None as "try next provider."

### Effort mapping
```python
EFFORT_MAP = {
    "analyze": "high",
    "fast_response": "low",
    "generate": "medium",
    "code": "high",
}
```

## Anti-Patterns

### 1. Discarding output on exit code 1
**Wrong:**
```python
async for message in query(prompt=prompt, options=options):
    output_parts.append(...)
# If query() raises on exit code 1, output_parts lost
```
**Right:**
```python
async def _stream():
    try:
        async for message in query(prompt=prompt, options=options):
            output_parts.append(...)
    except Exception as e:
        logger.debug("caught %s (output_parts=%d)", e, len(output_parts))
# output_parts preserved even on exception
```
This was the actual bug fixed in commit `3b0a87a`. Exit code 1 from MCP server
shutdown was causing EOS to discard valid Opus 4.6 responses.

### 2. Single-threaded concurrent calls
**Wrong:**
```python
with ThreadPoolExecutor(max_workers=1) as pool:  # serial!
    future = pool.submit(asyncio.run, coro)
```
**Right:**
```python
with ThreadPoolExecutor(max_workers=3) as pool:
    future = pool.submit(asyncio.run, coro)
```
Fixed in commit `d0c6ffb`. max_workers=1 caused all CC SDK calls to serialize,
creating a bottleneck when multiple agents called simultaneously.

### 3. No orphan cleanup on timeout
**Wrong:**
```python
try:
    return future.result(timeout=timeout)
except TimeoutError:
    return None  # orphaned claude process still running!
```
**Right:**
```python
before_pids = _get_claude_pids()
try:
    return future.result(timeout=timeout + 5)
except TimeoutError:
    _kill_orphaned_claude_procs(before_pids)
    future.cancel()
    return None
```

### 4. Calling CC SDK inside a CC session
**Wrong:**
```python
# Inside a claude -p cron script that triggers gateway code
result = query_cc_sync(prompt=...)  # spawns subprocess inside subprocess!
```
**Right:**
```python
if _is_nested_cc_session():
    return None  # skip, let caller use a different provider
```

### 5. Setting CLAUDE_CODE_STREAM_CLOSE_TIMEOUT in subprocess env
**Wrong:**
```python
subprocess.run(["claude", ...], env={"CLAUDE_CODE_STREAM_CLOSE_TIMEOUT": "120000"})
```
**Right:**
```python
os.environ.setdefault("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "120000")
# SDK reads os.environ in the PARENT process
```

### 6. Hardcoding claude binary path
**Wrong:**
```python
options = ClaudeAgentOptions(cli_path="claude")  # may not be in PATH
```
**Right:**
```python
options = ClaudeAgentOptions(cli_path="/usr/bin/claude")  # absolute path
```
EOS uses `/usr/bin/claude` because Docker containers may have a different PATH.

### 7. Unlimited budget on automated calls
**Wrong:**
```python
result = query_cc_sync(prompt=long_prompt, max_budget_usd=5.00)
```
**Right:**
```python
result = query_cc_sync(prompt=long_prompt, max_budget_usd=0.10)
```
Automated calls should always have tight budgets. Complex tasks should route
through cron scripts with higher (but still capped) budgets.

## Data Model

### Message stream
```
query() yields:
  AssistantMessage
    .content: list[TextBlock | ToolUseBlock]
    .model: str
  ResultMessage
    .session_id: str
    .result: str (final summary)
```

### CCResult (EOS wrapper)
```
CCResult
  .output: str          — joined TextBlock.text from all AssistantMessages
  .session_id: str      — from ResultMessage.session_id
  .latency_ms: int      — wall clock time
  .provider: "cc_sdk"
  .model: str           — from AssistantMessage.model
```

### Session persistence
```
_agent_sessions: dict[str, str]
  key: agent_id (e.g. "dex", "research_agent")
  value: session_id (UUID from ResultMessage)
  lifetime: process memory only (lost on restart)
```

### Model router integration
```
ModelProvider.CC_SDK — enum value "cc_sdk"
PROVIDER_QUALITY["cc_sdk"] = 0.85 — highest quality score
_ESCALATION_QUALITY_THRESHOLD = 0.40 — trigger for fast path escalation
```

## Webhooks and Events

N/A — The Claude Agent SDK does not have webhooks or event subscriptions.
It is a request-response (streaming) interface. The SDK's async generator
IS the event stream — each yielded message is an event.

For EOS, the "event" equivalent is the model router logging:
```python
logger.info("[Router] cc_sdk/%s responded (%dms)", cc_result.model, latency_ms)
```

## Limits

### Per-call limits
- **Budget**: hard cap via `max_budget_usd` — Claude stops mid-response if hit
- **Timeout**: `asyncio.wait_for()` with configurable seconds (EOS default: 30s)
- **Max turns**: `max_turns=1` in EOS (single-shot, no tool loops)
- **Context window**: inherited from the underlying model (200K tokens for Opus)

### Process-level limits
- **Memory**: each `claude` subprocess uses ~200-500MB RSS
- **Concurrent processes**: EOS caps at 3 via ThreadPoolExecutor
- **VPS constraint**: 4GB RAM means 2 concurrent calls max before OOM risk
- **Session resume**: unlimited within the CLI's session TTL

### CLI-level limits (cron scripts)
- **--allowedTools**: whitelist caps which tools Claude can use
- **--max-budget-usd**: hard cap per invocation
- **--add-dir**: single additional directory for context
- **Prompt length**: limited by shell argument size (typically 2MB on Linux)

## Cost Model

### Pricing structure
CC SDK uses the Claude Code subscription, not per-API-call pricing:
- **Pro plan**: $20/month — limited Opus, moderate Sonnet
- **Max plan**: $200/month — high Opus quota, unlimited Sonnet (EOS uses this)

Within-session costs are tracked by `max_budget_usd` but charged against the
subscription, not billed separately. The budget is a governance mechanism, not
a billing boundary.

### EOS cost governance
| Context | Budget | Daily max |
|---------|--------|-----------|
| Model router calls | $0.01-0.10 | ~$2.00 |
| Nightly maintenance | $0.50 | $0.50 |
| Morning prep | $0.30 | $0.30 |
| Weekly review | $1.00 | $0.14 (amortized) |
| Agent task executor | Routes through cognitive loop | Variable |
| Warmup | $0.01 | $0.01 |

Estimated total: ~$3/day, well within Max plan quota.

### Monitoring
No built-in usage dashboard for CC SDK. EOS tracks via:
- `CCResult.latency_ms` per call
- Logger warnings with output char counts
- Budget caps prevent runaway calls

## Version Pinning

### SDK version
`claude-agent-sdk>=0.1.55` in `services/requirements.txt`.
No upper bound pin — the SDK is pre-1.0 and evolving rapidly.

### CLI version
The `claude` binary auto-updates. No version pinning mechanism exists for the
CLI itself. Breaking changes in the CLI can break the SDK without warning.

### Known evolution
- The SDK is in active development (pre-1.0)
- Message types (AssistantMessage, ResultMessage, TextBlock) may change
- `permission_mode` values may expand
- `setting_sources` parameter may be deprecated in favor of project configs

### Deprecation risk
- `--print-messages` flag (used internally by SDK) may change format
- SDK imports may restructure as the package matures
- EOS mitigates by lazy-importing inside try/except

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

The Claude Agent SDK exists because Anthropic recognized that Claude Code's
real power is tool orchestration, not just chat. The SDK makes CC's subprocess
transport programmable:

**Design intent**: Give developers the same capabilities as the interactive
Claude Code CLI, but automatable. Prompt in, structured messages out, with
session persistence for multi-turn workflows.

**Key tradeoffs**:
- **Subprocess over API**: The SDK spawns a real CLI process rather than calling
  an API directly. This means you get ALL of Claude Code's capabilities (tools,
  MCP servers, project context) but pay with process overhead (~200-500MB per call).
- **Streaming over batch**: Messages arrive as they're generated. This enables
  timeout-with-partial-output but complicates error handling (exit code arrives
  after valid output).
- **Session resume over stateless**: Sessions can be resumed by ID, enabling
  multi-turn automation. But session state is managed by the CLI, not the SDK,
  so it's opaque to the caller.

**What it is NOT**: It is not a direct API client. It does not replace the
Anthropic Python SDK for simple prompt-response patterns. Use the direct API
for simple text generation; use CC SDK when you need tool orchestration.

## Problem-Solution Map and Hidden Capabilities

### Problems CC SDK solves uniquely
1. **Automated infrastructure maintenance** — Claude can read logs, check
   Docker containers, run imports, clean files. No other LLM interface provides
   this out of the box.
2. **Agent task execution with tool access** — agents can execute code, read
   files, and write results during task processing.
3. **Quality escalation** — when Haiku produces low-quality output, CC SDK
   provides Opus-level reasoning as an automatic upgrade path.

### Hidden capabilities
- **Session resume for context accumulation** — resuming a session gives Claude
  access to everything from prior turns without re-sending it. This is how EOS
  warmup works: the "Ready." prompt loads context, then real queries resume that
  session with full context.
- **--add-dir for multi-project context** — cron scripts can point Claude at any
  directory, not just the current project. This enables cross-project analysis.
- **Budget as quality control** — low budgets force Claude to be concise. High
  budgets allow deeper analysis. This is a feature, not just cost control.
- **Permission mode as security layer** — `auto` mode lets Claude use all tools
  without approval. `allowedTools` whitelist restricts to safe tools only. Cron
  scripts use whitelists; the model router uses auto.

## Operational Behavior and Edge Cases

### Exit code 1 is not a failure
This is the most important operational insight in the entire CC SDK integration.
The MCP server shutdown process produces stderr output and exit code 1 even when
the response was fully delivered. The SDK treats any non-zero exit as an
exception, but the real response has already been streamed. EOS's fix: catch
the exception inside the streaming loop, after output_parts have been collected.

### Partial output on timeout
When `asyncio.wait_for()` times out, `output_parts` may contain a partial but
useful response. EOS checks for this: if output_parts is non-empty, it returns
the partial output rather than None. This is a significant improvement over
discarding everything on timeout.

### Orphaned processes accumulate silently
A timed-out CC SDK call leaves a `claude --print-messages` process running.
Without cleanup, these accumulate and eventually OOM the VPS. EOS tracks PIDs
before each call and SIGKILLs any new ones after timeout.

### ThreadPoolExecutor in async context
When called from an async context (e.g., Discord bot's event loop),
`asyncio.run()` cannot be called directly (would create nested event loop).
EOS solves this with `ThreadPoolExecutor` — each CC SDK call runs in its own
thread with its own event loop.

### First-call latency
The first CC SDK call after process start takes 5-15 seconds (CLI init, MCP
server startup, model loading). Subsequent calls with session resume are 2-5
seconds. The warmup pattern is essential for user-facing latency.

## Ecosystem Position and Composition

### Where CC SDK sits in EOS architecture
CC SDK is the **highest-quality provider** in the model router. It sits at
the top of both routing paths:
- Heavy path: CC SDK (Opus) -> Haiku -> Gemini -> Ollama
- Fast path: Haiku -> CC SDK (escalation) -> Gemini -> Ollama

### Natural complements
- **Direct Anthropic SDK** — for simple prompt-response without tool access
- **Gemini SDK** — lower cost, higher rate limits, no tool orchestration
- **Ollama** — zero-cost local fallback, lowest quality
- **Discord bot** — primary interface that triggers CC SDK calls

### Integration pattern
CC SDK is NOT a replacement for the model router. It is one provider among
many. The model router owns the decision of when to use CC SDK vs alternatives.
The cc_sdk.py wrapper owns the HOW of CC SDK invocation.

### Composition anti-pattern
Never call CC SDK directly from service code. Always go through model_router's
`call_with_fallback()`. This ensures fallback, logging, and quality gating.

## Trajectory and Evolution

### Current state (April 2026)
- SDK is pre-1.0 (`>=0.1.55`)
- Anthropic is actively developing Claude Code as their primary developer tool
- The SDK is evolving alongside the CLI — expect breaking changes
- Session management is getting more sophisticated (project-level context)

### Where it's heading
- **MCP integration deepening** — more tools, more servers, richer tool results
- **Multi-agent orchestration** — SDK will likely support agent-to-agent calls
- **Project context** — `.claude/` directory conventions becoming standard
- **Cost model shift** — Anthropic may move from subscription to per-token for
  SDK usage (watch for this — would change EOS cost model significantly)

### Deprecation signals
- `--print-messages` is an internal flag that may change without notice
- `setting_sources` parameter may be replaced by project-level configuration
- The lazy import pattern protects EOS from SDK restructuring

### What to adopt early
- Session resume for context accumulation
- Budget caps as a governance pattern
- Permission mode whitelists for automated workflows

## Conceptual Model and Solution Recipes

### Mental model
Think of CC SDK as "Claude Code as a function call." You provide a prompt and
constraints (budget, tools, timeout), and get back a response that may include
the results of tool use (code execution, file reads, etc.).

The primitives are:
- **prompt** — what you want Claude to do
- **tools** — what Claude is allowed to use
- **budget** — how much compute to allow
- **session** — accumulated context from prior calls
- **timeout** — how long to wait

### Recipe 1: Scheduled infrastructure maintenance
```bash
# Cron: 0 2 * * *
claude -p --allowedTools "Bash Read Write Edit Glob Grep" \
  --add-dir /opt/OS --max-budget-usd 0.50 \
  "Check Docker containers. Fix anything down. Clean logs > 7 days.
   Report PASS or list issues."
```

### Recipe 2: Quality escalation in model router
```python
# Fast path: Haiku first, escalate on low quality
result = haiku_call(prompt)
if quality_score(result) < 0.40:
    result = query_cc_sync(prompt=prompt, task_type="analyze")
```

### Recipe 3: Agent warmup for latency reduction
```python
# On service startup
result = query_cc_sync(
    prompt="Ready.",
    task_type="fast_response",
    agent_id="dex",
    max_budget_usd=0.01,
)
# Subsequent calls to agent_id="dex" resume this session
```

### Recipe 4: Multi-step analysis with session resume
```python
# Step 1: gather data
r1 = query_cc_sync(prompt="Read all log files from today", agent_id="analyst")
# Step 2: analyze (resumes session, has log data in context)
r2 = query_cc_sync(prompt="Find error patterns", agent_id="analyst")
# Step 3: recommend (resumes again)
r3 = query_cc_sync(prompt="Write fix recommendations", agent_id="analyst")
```

### Recipe 5: Safe cron script with tool whitelist
```bash
claude -p --allowedTools "Bash Read Glob Grep" \
  --max-budget-usd 0.30 \
  "Verify all services are up. Do NOT modify anything.
   Report status only."
```
Note: excluding Write and Edit from allowedTools prevents accidental modifications.

## Industry Expert and Cutting-Edge Usage

### EOS as a frontier pattern
EOS represents one of the most advanced CC SDK integrations: programmatic
orchestration of Claude Code as a provider in a multi-model routing system.
Most CC SDK users run simple `claude -p` scripts. EOS uses it as:

1. **Highest-quality tier** in a 4-provider fallback chain
2. **Quality escalation target** when cheaper models produce insufficient output
3. **Autonomous infrastructure manager** via cron-scheduled maintenance
4. **Session-persistent agent runtime** with per-agent context accumulation

### Cutting-edge patterns discovered
- **Exit-code-1 trust pattern** — most users discard output on non-zero exit.
  EOS discovered that exit code 1 from MCP shutdown is benign and the output
  is valid. This single insight prevented constant Opus-to-Ollama degradation.
- **PID-tracking orphan cleanup** — snapshot process list before call, diff
  after timeout, SIGKILL orphans. Prevents memory leaks on VPS.
- **Budget-as-governance** — using `max_budget_usd` not just for cost control
  but to force concise output on fast tasks and allow deep analysis on heavy
  ones.
- **Warmup-on-startup** — pre-loading a CC session reduces first-query latency
  from 15s to 2-3s for the user-facing Discord bot.

### What most users miss
- Session resume is dramatically underused. Most people treat each CC SDK call
  as stateless. Resume enables context accumulation without re-sending prompts.
- Permission mode whitelists are a security feature, not just a convenience.
  Automated scripts should NEVER run with default permissions.
- Budget caps are quality controls, not just cost controls. A $0.05 cap on a
  classification task forces Claude to be decisive rather than verbose.

---

## EOS Usage Patterns

### Files that use CC SDK
| File | Pattern | Purpose |
|------|---------|---------|
| `eos_ai/cc_sdk.py` | Python SDK wrapper | Core entry point |
| `eos_ai/model_router.py` | Provider integration | Routing + escalation |
| `services/discord_bot.py` | Warmup on startup | Latency reduction |
| `scripts/scheduled/nightly_maintenance.sh` | CLI direct | Infrastructure maintenance |
| `scripts/scheduled/morning_prep.sh` | CLI direct | Pre-day system check |
| `scripts/scheduled/weekly_review.sh` | CLI direct | Health audit + reporting |

### Cron schedule (CC SDK related)
```
0 2 * * *   nightly_maintenance.sh    # $0.50 budget
30 5 * * *  morning_prep.sh           # $0.30 budget
0 6 * * 0   weekly_review.sh          # $1.00 budget
```

### Model router priority
```
PROVIDER_QUALITY["cc_sdk"] = 0.85  # highest
Heavy path: cc_sdk → haiku → gemini → ollama
Fast path:  haiku → (escalate if <0.40) cc_sdk → gemini → ollama
```

## Gotchas

### Exit code 1 trust (discovered 2026-04-04)
MCP server shutdown produces stderr and exit code 1. SDK raises exception.
Output is valid. Fix: catch inside _stream(), preserve output_parts.
Commit: `3b0a87a`

### Concurrent call serialization (discovered 2026-04-04)
max_workers=1 serialized all calls. Multiple agents blocked on single thread.
Fix: max_workers=3, PID tracking, orphan SIGKILL on timeout.
Commit: `d0c6ffb`

### Nested session recursion (design-time prevention)
Cron scripts run inside `claude -p`. If gateway code routes to CC SDK,
infinite subprocess recursion. Guard: `CLAUDE_CODE_SESSION` env var check.

### Session loss on restart
`_agent_sessions` is in-memory dict. Docker restart = all sessions lost.
First call after restart is cold (5-15s latency). Warmup pattern mitigates.

### Budget cap truncation
Low budget + complex task = truncated output with no error signal.
Result looks like a complete response but is actually cut short.
Always match budget to task complexity.

### Parent env for stream timeout
`CLAUDE_CODE_STREAM_CLOSE_TIMEOUT` must be set in os.environ of the parent
process. Setting it via subprocess env dict is silently ignored.
