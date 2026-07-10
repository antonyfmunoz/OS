---
type: codewiki-page
dir: (cross-cutting)
---

# Tech Stack

**The languages, runtimes, dependencies, model providers, and infrastructure that UMH is built from.** Every number below comes from `docs/codewiki/_manifest.json`, the fresh structural graph (`scripts/query_graph.py stats`), or a manifest file read directly.

## Languages

The indexed codebase is **664,724 lines** across **2,428 code files** (structural graph):

| Language | Files | Notes |
|---|---|---|
| Python | 1,929 | The substrate, adapters, transports, projections, services, scripts, tests |
| TypeScript | 485 | The cockpit (Electron + React renderer, web/mobile builds) |
| JavaScript | 14 | Build config, small glue |

Python dominates the backend (7,044 classes, 34,789 functions, 113,938 graph edges). TypeScript is concentrated almost entirely in `cockpit/`. The graph indexes 278 entry points across the tree.

## Python runtime — 3.11 only (hard constraint)

`pyproject.toml` pins `requires-python = ">=3.11"` and ruff `target-version = "py311"`. **Docker containers run Python 3.11 — 3.12+ syntax is forbidden** (e.g. backslashes in f-string expressions). This is a NON-NEGOTIABLE completion standard in `CLAUDE.md`: code that compiles on a 3.12 host can still break in the container. See `conventions.md` for the enforcement context. Stray `cpython-312` `.pyc` artifacts in the tree (`umh/__pycache__/`, `saas/bridge/`, `.claire/worktrees/`) are the residue of 3.12 hosts and are flagged in `health-findings.md`.

`eos_ai` uses implicit namespace packages (no `__init__.py`); substrate imports rely on `sys.path.insert(0, "/opt/OS")` before use. Public functions carry type hints; caught exceptions are always logged, never silently swallowed.

## Backend dependencies

From `requirements.txt` and `pyproject.toml` (`[project]` core + optional extras `voice`/`perception`/`telegram`/`scraping`/`agents`):

- **LLM SDKs** — `anthropic`, `google-genai` (NOT the deprecated `google.generativeai`), `groq==1.1.1`, `claude-agent-sdk>=0.1.55` (the Agent-SDK path behind `cc_sdk`), `openai>=1.0.0`.
- **Discord + voice** — `py-cord[voice]==2.6.1` (pinned; the voice extra), plus the audio stack: `openai-whisper`, `faster-whisper`, `webrtcvad`, `silero-vad`, `librosa`, `numpy`, `sounddevice`.
- **Web frameworks** — `fastapi>=0.115,<1.0` and `flask>=3.1,<4.0` (both present — FastAPI for the HTTP API surface, Flask for legacy/bridge routes).
- **Database** — `psycopg2-binary` talking to **Neon Postgres**. All DB calls go through psycopg2 through Neon (`.claude/rules/python.md`).
- **Embeddings / retrieval** — `fastembed` (local embedding, no API cost).
- **Auth / notifications** — `PyJWT[crypto]`, `pywebpush` (PWA push).
- **Scraping / media** — `playwright`, `yt-dlp`.
- **Ops** — `psutil` (feeds the CPU gate), `python-dotenv`, `requests`, `notion-client==3.0.0`, `python-telegram-bot`.

The build backend is `hatchling`; the wheel packages `substrate` only.

## Frontend stack — the cockpit

From `cockpit/package.json` (name `umh-cockpit`, version `0.1.0`):

- **Shell** — **Electron 42** via `electron-vite 5`. `main` entry is `./out/main/index.js`. One codebase ships three ways: desktop (`electron-vite`), web (`vite --config vite.web.config.ts`), and **mobile via Capacitor 7** (`build:mobile` runs a web build then `npx cap sync`), with iOS/Android targets (`@capacitor/ios`, `@capacitor/android` 8.x).
- **UI** — **React 19** (`react`/`react-dom` ^19.2), **Zustand 5** for state, **Tailwind CSS 4** (`@tailwindcss/vite`), `lucide-react` icons, `react-markdown` + `remark-gfm` for message rendering, `clsx` for class composition.
- **Auth** — **Clerk** (`@clerk/clerk-react` ^5.24) — the cockpit is locked to the founder's Clerk ID.
- **Realtime voice/video** — **LiveKit** (`livekit-client` ^2.19) for the live voice-session path.
- **Native mobile capabilities** — Capacitor plugins for haptics, keyboard, push notifications, splash screen, status bar.
- **Tooling** — TypeScript 6, Vitest 3 + Testing Library for tests, `tsc --noEmit` typecheck.

See `dirs/cockpit.md` and `dirs/cockpit-renderer.md` for the surface breakdown.

## LLM provider chain

Every agent call routes through `adapters/models/model_router.py::call_with_fallback()` — the single module-level entry point. The chain is deterministic-first with graceful fallthrough (each provider returns `None`/empty on failure, non-empty content on success):

```
cc_sdk (Opus 4.8 via Max subscription, no API cost)
  → Gemini 2.5 Flash (google-genai; use gemini-2.5-flash, not 2.0)
  → Groq (Llama 3.3 70B)
  → Ollama fallback
```

Provider roles are defined in `model_router.py` (`ProviderRole` → provider maps): `cc_sdk` is the CODE_BUILDER, Groq/Gemini fill STRATEGIC_BRAIN and FAST_RESPONDER, and there are two Ollama tiers — **`beast-ollama`** (the Windows Beast GPU node running `qwen2.5-coder:14b` at `100.74.199.102:11434`) as LOCAL_POWERHOUSE, and a tiny VPS-local **`ollama-qwen`** (`qwen2.5:0.5b`) as EMERGENCY_FALLBACK only. Quality thresholds (`model_router.py:386`) gate escalation: below a per-provider score the router retries with `cc_sdk`.

`cc_sdk` (`adapters/models/cc_sdk.py`) drives Opus 4.8 through the Claude Code CLI as a subprocess: `_get_subprocess_env()` injects the OAuth token from the ancestor CC process (via `/proc`) and blanks `ANTHROPIC_API_KEY`, so it costs nothing against the Max subscription. It validates streamed output against error signatures (`_is_error_leak()`) and returns `None` on auth/quota/transport leaks so the router falls through cleanly. Default timeout 120s (`CC_SDK_TIMEOUT_SECONDS`). CEO/strategic tasks force best-available with `agent_type='ceo'` or `force_opus=True`.

Every LLM call must have a deterministic fallback — the [Deterministic-First Principle](conventions.md) makes the AI a cognitive enhancement, never a dependency.

## Infrastructure

UMH runs as a distributed organism across nodes joined by a private mesh:

- **VPS (Hostinger)** — `100.77.233.50`, dir `/opt/OS`. The always-on **coordination brain**: runtime code, services (`os-discord`, `os-operator`, `os-webhook`, `os-scraper`), orchestration. Lightweight by role — no large models, no heavy compute. Hostinger throttles CPU on abuse, which is why the [CPU Gate Law](conventions.md) exists.
- **Windows Beast** — the GPU workhorse (`100.74.199.102`), full repo mirror, large local models (`qwen2.5-coder:14b` on Ollama, Kokoro TTS at `:8880`), heavy compute and media processing, and the interactive-desktop executor for browser verification. Node roles are defined in `infra/device_registry.json` — never hardcode device names (`.claude/rules/device-naming.md`).
- **Tailscale** — the private mesh; all nodes on one network, nothing exposed publicly. The UMH node daemon runs on `:8094`; the mesh HTTP relay dispatches to executor nodes on `:8095`.
- **Fly.io** — hosts the deployed cockpit (single domain `universalmetaharness.tech`). Deploys go through `bash cockpit/deploy.sh`, never raw `flyctl deploy` (the [Cockpit Deploy Gate](conventions.md)).
- **Neon Postgres** — the platform database. Agents and skills are registered in Neon, not just in code.
- **1Password** — the single source of secrets. All computer-use credentials flow through `op run --env-file=<tpl>` resolving `op://` URIs; secrets never transit CLI args, SSH, or plaintext env (the [Credential Injection Law](conventions.md)).

Docker packaging: containers run Python 3.11; Python-only changes never require a rebuild.

## See also

- [conventions.md](conventions.md) — the laws that govern how this stack is used
- [services-runtime.md](services-runtime.md) — the running services and processes
- [architecture.md](architecture.md) — the four-layer dependency model
- [dirs/adapters.md](dirs/adapters.md) — model routing internals
- [dirs/cockpit.md](dirs/cockpit.md) · [dirs/cockpit-renderer.md](dirs/cockpit-renderer.md) — the frontend
- [health-findings.md](health-findings.md) — where the stack has drifted or accreted cruft
