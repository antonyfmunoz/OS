---
type: codewiki-dir
dir: adapters
---

# `adapters/` — external-system adapters and the intelligence router

**101 files · 780,940 bytes · [Full file inventory](../inventory/adapters.md)**

## Purpose
`adapters/` is the layer that lets UMH talk to the outside world: LLM providers,
Google Workspace, Notion, GitHub, the calendar, browsers, SSH, Tailscale, and the
local filesystem/shell/git/tmux. Each subsystem gets a self-contained adapter that
hides its API, CLI, or protocol behind a plain Python surface the layers above can
call. The single most important thing here is intelligence routing:
`adapters/models/model_router.py` is where every LLM call in the system is dispatched
and where the multi-provider fallback chain lives.

## How it fits
In the four-layer dependency order (`projections → transports → adapters →
substrate`, see [architecture.md](../architecture.md) and
`.claude/rules/architecture-layers.md`), `adapters/` sits above `substrate/` and below
`transports/`. Adapters may import downward from `substrate/` but must never import
from `transports/` or `services/`. The bridge in the other direction is exactly one
file: `adapters/socket_registration.py:1` — `register_all_sockets()` wires the
concrete adapters (model router, agent runtime, CLI adapters, data sources, browser,
remote exec, tool adapters) into the abstract ports under `substrate/sockets/`. Its
own docstring calls it "the ONLY file that bridges adapters → substrate/sockets/."
Service entry points (`services/discord_bot.py`, `services/operator_api.py`) call it
once at startup so substrate code can reach adapters through ports without importing
upward.

## Structure

| Subdir | Files | Role |
|---|---|---|
| `models/` | 11 | Intelligence routing — `model_router.py`, `cc_sdk.py`, `agent_runtime.py`, `llm_adapter.py`, CLI adapters (Codex, Hermes, OpenCode), `routing/`. |
| `adapter_engine/` | 17 | Adapter manifest/maturity/lifecycle + capability discovery; Google Docs/Drive adapters and the live Drive/Docs ingestion pipeline. |
| `notion/` | 13 | Notion read/write: `integration/` (manifest, handler, poller, signals, outcomes) + `notion_publisher.py` / `notion_sync.py`. |
| `broadcast/` | 10 | FFmpeg broadcast engine — subprocess lifecycle, deterministic arg/filtergraph builders, ZMQ live control. |
| `browser_exports/` | 8 | Autonomous data export from ChatGPT, Claude, Instagram, Gmail via Playwright. |
| `data_source_adapters/` | 8 | Ingestion `Source` wrappers (conversation, GitHub repo, GWS, local file) + conversation-export parsers. |
| `google_workspace/` | 7 | GWS via the `gws` CLI: `gws_connector.py`, `email_gps.py`, doc creator/filer, scanner, tasks. |
| `tool_adapters/` | 6 | Governed filesystem/shell/git/tmux access with deny-rule machinery. |
| `browser_auth/` | 3 | Clerk login + SSO-chain (GitHub/Google) auth for browser automation. |
| `calendar/` | 3 | Meeting lifecycle (`meetings.py`) and trip logistics (`travel_manager.py`). |
| `github/` | 2 | Governed GitHub writes via the `gh` CLI. |
| `notebooklm/`, `scrapling/`, `ssh/`, `tailscale/` | 2 each | NotebookLM sync, stealth HTTP fetch, centralized SSH/SCP, Tailscale admin API. |
| `browser/` | 1 | Thin re-export of the browser adapter from the substrate execution layer. |
| root | 4 | `socket_registration.py`, `protocol.py`, `README.md`, `__init__.py`. |

## Key components

- **`adapters/models/model_router.py` (1,618 lines)** — the `ModelRouter` and the
  module-level `call_with_fallback()` entry point. This is *the* intelligence routing
  seam: everything routes through it. The provider registry defines role slots
  (`STRATEGIC_BRAIN`, `FAST_RESPONDER`, `CODE_BUILDER`, `LOCAL_POWERHOUSE`,
  `EMERGENCY_FALLBACK`) mapped to concrete models. The active chain is
  cc_sdk (Opus via subscription) → Gemini 2.5 Flash → Groq → Ollama; per-role slots
  bind `CODE_BUILDER` to `cc_sdk` and quality thresholds escalate to cc_sdk when a
  cheaper provider's `quality_score` falls below its floor (`cc_sdk`: 0.85 in
  `QUALITY_THRESHOLDS`).
- **`adapters/models/cc_sdk.py` (513 lines)** — the Claude Code Agent SDK wrapper that
  runs Opus via the Max subscription over a CLI subprocess (routing "option 0", no API
  cost). It injects the ancestor Claude Code process's OAuth token via `/proc`, blanks
  `ANTHROPIC_API_KEY`, and validates streamed output against error signatures
  (`_is_error_leak()`), returning `None` on auth/quota/transport leaks so the router
  falls through. `model_router.py` is its only in-graph dependent.
- **`adapters/models/llm_adapter.py` (91 lines)** — wraps `call_with_fallback()` as a
  substrate `Adapter`, the shape substrate code consumes through the intelligence port.
- **`adapters/models/agent_runtime.py` (580 lines)** — the OS agent runtime with its own
  `_claude_available` fallback flag (per CLAUDE.md: do not break it).
- **`adapters/socket_registration.py:14`** — `register_all_sockets()`, the startup
  wiring described above.
- **Heaviest adapters**: `google_workspace/email_gps.py` (1,429), `google_workspace/gws_connector.py`
  (1,116), `adapters/calendar/meetings.py` (836), `adapters/adapter_engine/live_drive_docs_ingestion_pipeline_v1.py`
  (735). None exceed the 3,000-line ceiling.

## Data & state
- **LLM provider credentials** read from env (`GEMINI_API_KEY`, Groq/Ollama config,
  1Password-resolved secrets); cc_sdk reads the OAuth token from the ancestor process,
  never from a literal.
- **Notion** — `adapters/notion/` polls Notion databases and writes pipeline outcomes
  back to pages; auth loads from environment (`adapters/notion/integration/auth.py`).
- **Google Workspace / Calendar** — driven through the `gws` CLI; the scanner reads the
  founder's Google Docs.
- **Ingestion** — `data_source_adapters/` and `adapter_engine/` feed the canonical
  ingestion path (`substrate.execution.ingestion`).
- **Broadcast** — `broadcast/engine.py` owns an FFmpeg subprocess and a ZMQ control
  socket.

## Gotchas
- **Never construct an LLM client directly.** Per CLAUDE.md, never write
  `anthropic.Anthropic()` — always `call_with_fallback()`. The provider contract is:
  return `None`/empty on failure, non-empty content on success.
- **`call_with_fallback()` returns a `RoutingResult`** — read `.output`, not the raw
  return, per the model-router return-type memory.
- **The intelligence port is keyword-only.** `substrate.sockets.intelligence_port.call_with_fallback`
  takes `**kwargs`; pass `prompt=...`, never positionally — a positional call broke all
  chat replies (2026-07-08).
- **Deterministic-first.** Every LLM call must have a deterministic fallback that
  produces a usable result; the system must still produce output with all providers down.
- **CPU gate.** Adapters live in a gated directory: use `gated_subprocess_run()` /
  `gated_popen()` from `substrate/execution/cpu_gate.py`, never raw `subprocess.*`
  (cc_sdk has its own gate and is exempt).
- **Credential injection.** Browser-automation credentials flow through 1Password
  `op run` on the executor side; never pass secrets as CLI args (see
  `.claude/rules/credential-injection.md`).
- **Doc drift.** A comment in `model_router.py` still names "Opus 4.6" in the quality
  table; the live model is Opus 4.8. The routing behavior is unaffected — it is a stale
  comment, not a routing bug.

## See also
- [dirs/substrate.md](substrate.md) — the ports adapters register into (`substrate/sockets/`)
- [dirs/transports.md](transports.md) — the I/O layer above that consumes adapters
- [dirs/services.md](services.md) — entry points that call `register_all_sockets()`
- [architecture.md](../architecture.md) · [tech-stack.md](../tech-stack.md) · [data-flow.md](../data-flow.md)
