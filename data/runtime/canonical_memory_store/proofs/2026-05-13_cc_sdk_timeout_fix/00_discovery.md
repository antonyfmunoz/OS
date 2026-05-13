# Phase 0 — Discovery: Timeout Semantics + Upstream Contracts

> Date: 2026-05-13

## Timeout Locations

| Location | Line | Value | Semantic |
|----------|------|-------|----------|
| `query_cc()` param default | cc_sdk.py:178 | 30.0s | Total wall-clock for entire stream |
| `asyncio.wait_for()` | cc_sdk.py:270 | `timeout` param | Enforces the above |
| `query_cc_sync()` param default | cc_sdk.py:372 | 30.0s | Passed through to `query_cc()` |
| `future.result()` | cc_sdk.py:428 | `timeout + 5` | Thread pool grace (+5s over inner) |

The timeout is the total wall-clock time from the start of
`_stream()` (which includes CLI startup, auth handshake, LLM
inference, and response streaming) until the response is complete.
It is NOT an idle timeout — it fires even if data is actively
streaming.

## Upstream Callers

| Caller | File:Line | Passes timeout? | Watchdog? |
|--------|-----------|-----------------|-----------|
| model_router (fast escalation) | model_router.py:983 | No (uses default) | No |
| model_router (heavy path) | model_router.py:1046 | No (uses default) | No |
| discord_bot warmup | discord_bot.py:975 | No (uses default) | No |

No caller passes an explicit timeout. No upstream watchdog
enforces a time limit on cc_sdk calls. Bumping the default is
safe.

## Why 30s Is Too Short

The cc_sdk call chain:
1. SDK version check (~1s)
2. CLI process startup (~2-3s)
3. MCP server connection attempts (~2-5s, non-blocking errors)
4. OAuth handshake (~1-2s)
5. LLM inference (Opus 4.6: 10-60s depending on prompt)
6. Response streaming (~1-5s)

Total: 17-76s for a typical call. 30s cuts into LLM inference.
Yesterday's direct test succeeded at 45s. The default must cover
the slowest realistic case without being unreasonably long.

## Recommendation

Default: 120s. Env-configurable via CC_SDK_TIMEOUT_SECONDS.

120s covers:
- Worst-case Opus 4.6 inference (~60s) + overhead (~16s) = ~76s
- Margin for system load spikes
- Still finite — won't hang indefinitely

The env var allows tuning without code changes (e.g., lower for
fast_response tasks, higher for code generation).

## STOP Condition Check

- The 30s IS a timeout (total wall-clock) — confirmed
- No upstream caller has a hard <30s contract — confirmed
- No STOP conditions triggered
