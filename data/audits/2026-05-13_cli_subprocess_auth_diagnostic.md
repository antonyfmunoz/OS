# CLI Subprocess Auth Diagnostic — 2026-05-13

## Root Cause

The Claude Code CLI subprocess launched by cc_sdk.py (via
claude-agent-sdk) lacked `CLAUDE_CODE_OAUTH_TOKEN` in its
environment. The token exists in the running Claude Code
process (PID 4143861) but is NOT propagated to Python
tool-execution subprocesses via shell snapshots.

Meanwhile, `dotenv.load_dotenv('/opt/OS/runtime/.env')` loads
`ANTHROPIC_API_KEY` into `os.environ`. The CLI subprocess
inherits this key, attempts API-key auth, and gets 401 because
the Anthropic credit balance is depleted.

## Environment Delta

| Variable | Interactive bash | Python os.environ | Effect |
|----------|-----------------|-------------------|--------|
| CLAUDE_CODE_OAUTH_TOKEN | PRESENT (108 chars) | **MISSING** | CLI can't use subscription auth |
| ANTHROPIC_API_KEY | absent | PRESENT (via dotenv) | CLI uses depleted API key |
| CLAUDECODE | 1 | 1 | SDK strips this (line 356) |
| CLAUDE_CODE_SESSION | absent | absent | _is_nested_cc_session() returns False |

## Credential Store State

```
/root/.claude/.credentials.json:
  subscriptionType: max
  rateLimitTier: default_claude_max_20x
  accessToken: 108 chars (EXPIRED)
  expiresAt: 2026-04-18 (25 days ago)
  refreshToken: NONE
```

The credential store has an expired access token and no refresh
token. The running Claude Code session has a fresh token (set via
its own Node.js runtime), but this isn't persisted back to the
credential store or to `.env.sessions`.

## .env.sessions State

```
/opt/OS/.env.sessions:
  CLAUDE_CODE_OAUTH_TOKEN: 92 chars (STALE — different from live)
```

The `.env.sessions` file was manually created but never updated
when Claude Code refreshed the token internally. The 92-char
token is different from the live 108-char token.

## Fix Applied

Added `_find_ancestor_oauth()` and `_get_subprocess_env()` to
`runtime/cc_sdk.py`. The fix:

1. Walks /proc/<pid>/environ up the process ancestry to find
   `CLAUDE_CODE_OAUTH_TOKEN` from the Claude Code parent process
2. Injects it into `ClaudeAgentOptions(env=...)` so the SDK
   merges it into the child subprocess environment
3. Blanks `ANTHROPIC_API_KEY` in the subprocess env to prevent
   the CLI from falling back to depleted API-key auth

The token is cached after first discovery (module-level
`_cached_oauth`) to avoid repeated /proc reads.

## Verification

### Direct cc_sdk test
```
query_cc_sync('Say exactly: CC_SDK_AUTH_TEST', timeout=45.0)
→ provider: cc_sdk
→ model: claude-opus-4-6
→ output: CC_SDK_AUTH_TEST
```

### Canary ingestion (through orchestrator)
```
verdict: COMPLETE_CYCLE
decomposition: 6 observations (LLM extraction)
method: llm (via Groq fallthrough — cc_sdk timed out at 30s default)
```

cc_sdk timed out at the default 30s during the canary (session
contention), but no auth error leaked. The router fell through to
Groq cleanly. When tested directly with 45s timeout, cc_sdk
succeeded via Opus 4.6.

### Test suite
```
25/25 pass:
  tests/test_cc_sdk_subprocess_env.py: 9 tests
  tests/test_cc_sdk_error_validation.py: 16 tests
```

## Provider Chain After Fix

| Provider | Priority | Status |
|----------|----------|--------|
| CLAUDE_CLI | 0 | Nested (skipped — running inside CC session) |
| CC_SDK | 1 | **WORKING** (OAuth injected, Opus 4.6) |
| GEMINI | 2 | Quota exhausted (free tier) |
| GROQ | 3 | Available (Llama 3.3 70B) |
| ANTHROPIC | 4 | 401 (credit balance) |
| PERPLEXITY | 5 | Available |
| OLLAMA | 6 | Available |
