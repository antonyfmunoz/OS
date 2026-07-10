# UMH Codebase Guide — Complete Contractor Reference

> Generated 2026-07-03 from graphify AST index (42,603 source nodes, 40,613 edges, 2,979 files)
> Platform v1.0.0 — Production Certified, Frozen 2026-07-01

This document explains **every file and directory** in the UMH codebase so that any developer — including beginners — can understand the system with zero ambiguity. Sections 1-12 explain how the system works. Section 13 is a file-by-file reference for every source file in the repository.

---

## 0. Where Do I Start? (Read This First)

**If you're adding a new feature:** Read Section 2 (Architecture) to know which layer your code goes in, then Section 6 (The 9 Laws) to know what will block your commit. Find similar existing code in Section 13 (File Reference) and follow its patterns.

**If you're fixing a bug:** Find the file in Section 13, read its description to understand what it does, then check Section 3 (Core Flows) to understand how data moves through the system.

**If you're deploying:** Read Section 5 (Docker Services) and Section 9 (Development Workflow). The most important rule: never run `flyctl deploy` directly — always `bash cockpit/deploy.sh`.

**If you're confused about a file:** Search Section 13 — every source file has a plain-English description.

**Key mental model:** Think of UMH like a factory assembly line. Raw inputs (Discord messages, HTTP requests, scheduled events) enter as "signals." They flow through an 8-stage pipeline (the "spine") where each stage adds context, checks permissions, picks the right AI model, generates a response, and records what happened. Every change to the system's state goes through a separate "governed mutation" pipeline that checks if the change is allowed before executing it.

---

## 1. What This System Is

UMH (Universal Mastery Hierarchy) is a production AI intelligence substrate. In plain English: it's a platform that takes inputs from multiple sources (a Discord message, an HTTP API call, a scheduled task, a cross-device mesh event), wraps them in a standard format, runs them through an 8-step processing pipeline with permission checks, uses AI models to generate responses (with automatic fallbacks if a model is unavailable), and records everything that happened for learning and debugging.

**What it is NOT:** This is not a chatbot framework or a simple API wrapper around an AI model. It is a complete operating system for running AI-augmented business operations — with governance (permission checks), tracing (audit logs), feedback loops (learning from outcomes), and multi-device orchestration.

**Current state:** Single-user validation phase. One organization, multiple ventures. Solo founder + contractor team. Deployed on a Hostinger VPS (lightweight orchestrator — no heavy compute) with a Windows workstation called "Beast" (GPU executor) connected via Tailscale private network.

**Tech stack (what you need to know):**
- **Backend:** Python 3.12 on the host machine, but **Python 3.11 inside Docker containers** — this means you cannot use Python 3.12+ syntax (like backslash in f-strings) in any code that runs in a container. If you're unsure, assume 3.11.
- **Frontend:** TypeScript, React 18, Vite, Tailwind CSS, shadcn/ui — the cockpit is an Electron desktop app, PWA (Progressive Web App), and native mobile app (iOS + Android via Capacitor). One React codebase renders on all surfaces.
- **CLI:** `transports/cli/` — a Rich/prompt_toolkit terminal interface. Run with `python -m transports.cli`. Connects to the UMH API for operator commands and advisor chat.
- **API layer:** Two separate API surfaces — Express + Drizzle ORM (TypeScript, handles the cockpit's HTTP routes) and FastAPI (Python, the operator API).
- **Database:** Neon Postgres (serverless PostgreSQL) with Row Level Security (RLS) for multi-tenant isolation.
- **AI Models:** Claude Opus 4.6 is the primary model (accessed via cc_sdk, which piggybacks on the founder's Claude Code subscription — no API cost). If that fails, it falls back to Gemini 2.5 Flash, then Groq, then a local Ollama model. If ALL models fail, the system still works using regex-based pattern matching.

---

## 2. Architecture — The 4 Layers

Dependency direction is **strictly one-way downward**. Pre-commit hooks enforce this. Violating it blocks your commit.

```
┌─────────────────────────────────────────────────────┐
│  projections/  (EOS, CreatorOS, LyfeOS)             │
│  saas/         (EOS-specific routes, schema, seeds) │
├─────────────────────────────────────────────────────┤
│  transports/   (Discord, HTTP API, CLI, node mesh)  │  ← I/O surfaces
├─────────────────────────────────────────────────────┤
│  adapters/     (LLM routing, browser, calendar)     │  ← external integrations
├─────────────────────────────────────────────────────┤
│  substrate/    (types, execution, governance, state) │  ← universal platform
└─────────────────────────────────────────────────────┘
         ▲ imports flow DOWN only, never up
```

**How substrate talks to upper layers without importing them:**
`substrate/sockets/` provides abstract ports. The transport layer registers a concrete implementation at startup. Substrate calls the thin wrapper — never importing from transports directly.

```python
# substrate/sockets/channel_port.py
_router_fn = None

def register_channel_router(fn):
    global _router_fn
    _router_fn = fn

def get_channel_router():
    if _router_fn:
        return _router_fn()
    return None
```

---

## 3. The Two Core Flows

### 3a. Signal Execution (read path)

Everything enters the substrate as a `SignalEnvelope`:

```python
class SignalEnvelope(BaseModel):
    id: UUID
    source: SignalSource          # user, system, scheduled, adapter, organism
    urgency: SignalUrgency        # immediate, high, normal, low, background
    modality: Modality            # text, voice, image, multimodal
    content: str
    user_id: str
    organization_id: str
    venture_id: str | None
    authority_tier: int           # 1-9, governs what actions are allowed
    attachments: list[Attachment]
    metadata: dict[str, Any]
```

The `Substrate` class is the single entry point, composing 9 subsystems:

```python
class Substrate:
    def __init__(self):
        self.self_model = self_model
        self.identity = ConcreteIdentityResolver()
        self.governance = ConcreteGovernanceEngine()
        self.memory = ConcreteMemorySystem()
        self.context = ConcreteContextAssembler(memory_system=self.memory)
        self.registry = ConcreteComponentRegistry()
        self.trace = ConcreteTraceRecorder()
        self.feedback = ConcreteFeedbackCapture()
        self.spine = ConcreteExecutionSpine(...)
        self.router = ConcreteSignalRouter(...)
```

The **ExecutionSpine** runs 8 stages:

```
interpret → recall → lookup → compose → route → execute → trace → feedback
```

Deterministic-first: intent classification uses regex patterns before any LLM call. If all providers fail, the spine returns a heuristic response:

```python
_INTENT_PATTERNS = [
    (re.compile(r"\b(schedule|book|calendar)\b", re.I), "schedule"),
    (re.compile(r"\b(send|email|message)\b", re.I), "send"),
    (re.compile(r"\b(status|progress|update)\b", re.I), "status"),
    # ... more patterns
]

_DETERMINISTIC_RESPONSES = {
    "greeting": "Hello! I'm here and ready to help.",
    "command": "I'll process that request. Working on it now.",
    # ...
}
```

### 3b. Governed Mutation (write path)

Every state change routes through `governed_mutation()`. No exceptions.

```
Propose → Governance Check → Approve/Reject → Execute → Verify → Learn → Journal → Event
```

Core types: `ActionEnvelope`, `MutationRequest`, `MutationResponse`, `MutationSpec`, `MutationRegistry`.

---

## 4. Intelligence Routing

All LLM calls go through one entry point:

```python
from adapters.models.model_router import call_with_fallback

result = call_with_fallback(prompt="...", task_type=TaskType.ANALYSIS)
```

**Routing chain:** cc_sdk (Opus 4.6 via Claude Code subscription, free) → Gemini 2.5 Flash → Groq → Ollama

- `cc_sdk` reads OAuth token from the ancestor Claude Code process via `/proc`
- CEO/strategic agents force best model: `agent_type='ceo'` or `force_opus=True`
- Every LLM call has a deterministic fallback with regex-based intent matching

Never call providers directly. Never hardcode `anthropic.Anthropic()`. Always `call_with_fallback()`.

---

## 5. Docker Services

6 containerized services on a shared `eos_network` bridge. All mount `/opt/OS` as `/app`, use Python 3.11-slim, share `services/.env` + `infra/docker/umh.env`.

| Container | Entrypoint | Port | CPU/Mem | Restart | Purpose |
|-----------|-----------|------|---------|---------|---------|
| `os-discord` | `python3 services/discord_bot.py` | 8765 | 0.35/1G | on-failure | Primary Discord bot, DEX conversational layer |
| `os-operator` | `uvicorn services.operator_api:app` | 8091 | 0.50/512M | unless-stopped | FastAPI HTTP API for cockpit |
| `os-webhook` | `python3 transports/api/webhooks/calendly_webhook.py` | 8080 | 0.25/128M | always | Calendly webhook receiver |
| `os-scraper` | `python3 services/overnight_scrape.py` | — | 0.25/256M | no | Batch scraping (on-demand) |
| `os-browser` | `python3 services/browser_relay.py` | 8086 | 0.50/1.28G | unless-stopped | Playwright browser automation |
| `os-livekit` | `livekit-server` | 7880,7881,3478/udp | 0.35/256M | unless-stopped | Voice/video (LiveKit v1.8.3) |

**Restart a service:** `docker restart os-discord` (use container name, not compose service name)

**Never** use `docker compose restart` — use `docker restart <container_name>`.

---

## 6. The 9 Laws (Non-Negotiable)

These exist because each one was violated and caused a real incident. Pre-commit hooks enforce most of them — your commit will be rejected if you violate them.

### Law 1: CPU Gate
**Rule:** Never use raw `subprocess.run/Popen/call/check_output/check_call` in substrate/, adapters/, transports/, or services/.

**Why:** Hostinger throttled the VPS CPU for an entire week after a runaway process saturated it.

**Instead:**
```python
from substrate.execution.cpu_gate import cpu_gate_check, gated_subprocess_run

# Before heavy work:
gate = cpu_gate_check("my_subsystem")
if not gate.allowed:
    return  # skip or defer

# Instead of subprocess.run():
result = gated_subprocess_run(["git", "status"], caller="my_subsystem")
if result is None:
    return  # CPU was too hot, skipped
```

**Enforced by:** `scripts/check_cpu_gate.py` pre-commit hook. Zero violations remain.

### Law 2: Cockpit Deploy Gate
**Rule:** Never run `flyctl deploy` directly for the cockpit. Always `bash cockpit/deploy.sh`.

**Why:** A worktree deploy shipped without API key injection, causing 401 Unauthorized on every cockpit API call (2026-06-06).

**Enforced by:** deploy.sh verifies nginx.conf.template, Dockerfile, and start.sh match main before deploying.

### Law 3: Python 3.11 in Docker
**Rule:** No Python 3.12+ syntax in any code that runs inside Docker containers.

**Why:** Docker images use Python 3.11-slim. Backslash in f-string expressions and other 3.12+ features cause SyntaxError at container startup.

**What to avoid:** `f"{'\\n'.join(items)}"` — use a variable instead.

### Law 4: Dependency Direction
**Rule:** substrate/ never imports from transports/ or services/. Use abstract ports in substrate/sockets/ instead.

**Enforced by:** `scripts/check_dependency_direction.py` pre-commit hook.

### Law 5: Type Coherence
**Rule:** Before defining any new Enum, BaseModel, or dataclass — check `substrate/canonical_types.py` first. If the name exists, import it. Never redefine.

**Why:** ~80 canonical types are registered. Parallel type systems cause reconvergence audits.

**Canonical locations:**
- `substrate/types.py` — SignalEnvelope, RiskClass, CapabilityStatus, etc.
- `substrate/contracts/agent_types.py` — TaskType, ModelProvider
- `substrate/execution/runtime/capability_router.py` — Capability (28 job capabilities)
- `substrate/organism/` — RuntimeClass, WorkUnitType, WorkcellRole

**Enforced by:** `scripts/check_type_divergence.py` pre-commit hook.

### Law 6: Instance Context
**Rule:** No hardcoded user/AI/company names in substrate/ code. Use runtime lookups.

**Why:** Substrate is universal. Different projections have different AI names, founder names, company names.

**Instead:** `get_ai_name()` for AI name, BIS profile for user name, env vars for infrastructure.

**Enforced by:** `scripts/check_instance_leak.py` pre-commit hook.

### Law 7: Projection Boundary
**Rule:** Substrate is universal. Projection-specific code stays in projections/.

**What's always projection-specific:** `EntrepreneurOS*` class names, `EOS_ORG_ID`, `eos-*` prefixed identifiers.

**Enforced by:** `scripts/check_projection_leak.py` pre-commit hook.

### Law 8: Credential Injection
**Rule:** All credentials for browser automation and computer use flow through 1Password `op run`. Never plaintext CLI arguments.

**Pattern:**
```bash
ssh <executor> "op run --env-file=<tpl> -- python collector.py ..."
```

**Enforced by:** `scripts/check_credential_injection.py` pre-commit hook.

### Law 9: Deterministic-First
**Rule:** Every LLM call MUST have a deterministic fallback that produces a usable result.

**Test:** "All LLM providers are down — does the system still produce output?" Must be yes.

**Pattern:** Build deterministic result → try AI enhancement → use AI if better, keep deterministic if not.

---

## 7. Complete Directory Reference

### Core Source Code (4 layers)

| Directory | Purpose | Graphify Nodes | Files | Classes | Methods |
|-----------|---------|---------------|-------|---------|---------|
| `substrate/` | Universal platform — types, execution, governance, state, organism, sockets | 17,350 | 889 | 2,298 | 10,932 |
| `adapters/` | External system integrations — LLM routing, browser, calendar, GitHub | 856 | 77 | 69 | 435 |
| `transports/` | I/O surfaces — Discord, HTTP API, CLI, node mesh, channels, presence | 2,043 | 200 | 22 | 156 |
| `projections/` | Projection-specific logic — EOS, CreatorOS, LyfeOS | 474 | 50 | 42 | 310 |

### substrate/ Subdirectories (20+)

| Subdirectory | Purpose |
|-------------|---------|
| `organism/` | Autonomous organism runtime — OrganismDaemon, OrchestratorKernel, work packets, resource allocation |
| `execution/` | Execution pipeline — spine.py (8-stage), cpu_gate.py, credential_gate.py, trace, feedback, agents, workers |
| `control_plane/` | Gateway, governance, identity, memory, registry, router, orchestrator, signals, events |
| `workstation/` | Operator workstation runtime — ContinuityEngine |
| `state/` | State management + storage — DB connections, config, context, providers |
| `composition/` | Signal composition |
| `understanding/` | Pattern recognition, 17 knowledge layers |
| `sockets/` | Abstract ports — channel_port, config_port, intelligence_port, projection_port |
| `meta_ide/` | Engineering session coordination |
| `operator/` | Operator context + intent routing |
| `governance/` | Governance rules |
| `contracts/` | Agent types, task types |
| `types.py` | THE type system — ~30+ Pydantic models |
| `canonical_types.py` | Registry of ~80 canonical types |
| `memory/` | Memory system |
| `reality_model/` | Reality queries, instance/canonical reality models |
| `intelligence/` | Intelligence subsystems |
| `ontology/` | Ontological framework |
| `observability/` | Error recording, tracing |
| `foundation/` | Foundation layer |
| `self_model.py` | System self-model |

### adapters/ Subdirectories (20+)

| Subdirectory | Purpose |
|-------------|---------|
| `models/` | **model_router.py** (THE entry point for all LLM calls), cc_sdk.py, llm_adapter.py, codex_cli.py, hermes_cli.py |
| `adapter_engine/` | Adapter lifecycle management |
| `browser/` | Browser automation |
| `browser_auth/` | SSO chain adapter |
| `browser_exports/` | Browser export utilities |
| `calendar/` | Calendar integration |
| `capabilities/` | Capability adapters |
| `data_source_adapters/` | Data source connectors |
| `github/` | GitHub integration |
| `google_workspace/` | Google Workspace (Calendar, Sheets, etc.) |
| `notion/` | Notion integration |
| `ssh/` | SSH adapter |
| `tailscale/` | Tailscale mesh networking |
| `tool_adapters/` | Generic tool adapters |
| `broadcast/` | Broadcast messaging |
| `shannon/` | Shannon information processing |

### transports/ Subdirectories

| Subdirectory | Purpose |
|-------------|---------|
| `api/` | HTTP API layer (153 files) — auth middleware, routes for organism/governance/system/dex/execution/settings, Python bridges |
| `api/http/` | Platform DB schema (users/orgs/portfolios), substrate route handlers |
| `cli/` | UMH CLI — operator terminal interface (7 files). Rich + prompt_toolkit REPL with slash commands (/status, /agents, /loops, /nodes, /approvals, /history). Run: `python -m transports.cli` |
| `discord/` | signal_factory.py — converts Discord messages to SignalEnvelope |
| `node_mesh/` | Cross-device mesh networking (server.py, client.py) |
| `channels/` | Channel base class + Discord/Telegram/Webhook/Console channels |
| `presence/` | Presence tracking (18 files) |

### Application & Deployment

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `services/` | Deployment entrypoints only. 37 files. No business logic. | discord_bot.py, operator_api.py, browser_relay.py, overnight_scrape.py, heartbeat.py, cost_tracker.py, etc. |
| `cockpit/` | Electron + React + Capacitor frontend. Own Dockerfile. | `src/renderer/` — React 18 + Tailwind + Zustand. 5 surfaces: web (PWA), desktop (Electron), mobile (Capacitor iOS + Android), Discord, CLI. `android/` (51 files), `ios/` (15 files), `assets/` (5 icon/splash PNGs), `DESIGN.md` (locked UI spec). Deploy: always `bash cockpit/deploy.sh`. CI: `.github/workflows/mobile-build.yml` |
| `nodes/` | Node management. | `windows/` (executor node daemon), `environments/` (work packets), `distribution/` |
| `umh/` | Relay servers | desktop_relay.py, vision_relay.py, voice_server.py |
| `saas/` | EOS projection only | EOS-specific routes, DB schema, seed data, bridge/ |

### Testing

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `tests/` | 250+ test files | pytest + conftest.py. Subdirs: `adapters/`, `substrate/`, `certification/`, `fixtures/` |

Run tests: `python3 -m pytest tests/`

### Tooling & Scripts

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `scripts/` | 150+ utility scripts | Graph queries (`query_graph.py`, `update-graph`), pre-commit hooks, cron jobs, deploy helpers, audit tools, session bootstrap |
| `skills/` | 25 skill directories | Business domains: Content, CustomerSuccess, Marketing, Ops, Outreach, Research, Sales. Dev: developer, meta, tools |
| `agents/` | Agent soul documents (markdown) | Character/identity only — no mechanics. 11 agent files. |

### Knowledge & Documentation

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `knowledge/` | Wiki system | concepts/, decisions/, domains/, entities/, palace/, skills/, sources/, synthesis/. Retrieval rules, wiki rules. |
| `docs/` | Project documentation | deploy.md, corporate-structure.md, brand-identity.md, SYSTEM_ARCHITECTURE.md, strategy/, operations/ |

### Infrastructure & Config

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `infra/` | Infrastructure config | `device_registry.json` (source of truth for device names), `workspace_registry.json`, service registries, `crontab.managed`, `livekit.yaml`, Docker configs |
| `config/` | Non-secret config | `nonsecret.env` |
| `docker/` | Docker build configs | `computer-use/` |

### Data & Runtime (gitignored / generated)

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `data/` | Runtime state | Traces, organism JSONL, audits, certification, codebase graph. Mostly gitignored. |
| `logs/` | Runtime logs | archive/, decisions/, execution/, signals/, tool_mastery_research/. Gitignored. |
| `runtime/` | Runtime artifacts | Empty (generated on demand). |
| `vault/` | Memory vault | memory/. |
| `media/` | Media files | higgsfield/. |
| `graphify-out/` | AST index | graph.json (42MB). Gitignored. |

### Dot-Directories (tooling/config)

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `.github/` | GitHub Actions CI | `workflows/mobile-build.yml` — builds web, iOS, and Android on push to `cockpit/` on main |
| `.claude/` | Claude Code config | CLAUDE.md, `agents/` (4 subagents), `commands/` (24 slash commands), `hooks/`, `rules/` (10 rule files), `skills/` (31 skills) |
| `.agents/` | Installed agent skill packs | 17 skills from skills.sh ecosystem |
| `.planning/` | GSD workflow state | PROJECT.md, ROADMAP.md, STATE.md, config.json, `phases/` (13 phase dirs) |
| `.obsidian/` | Obsidian vault config | app, appearance, plugins, graph, templates |
| `.claire/` | Secondary worktree manager | worktrees/ |
| `.playwright-mcp/` | Playwright MCP debug artifacts | Console logs, screenshots |
| `.vscode/` | VS Code settings | settings.json |
| `.git/` | Git repository | Custom `pre-commit` and `post-merge` hooks |
| `__pycache__/` | Python bytecode cache | Ephemeral |
| `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/` | Tool caches | Ephemeral |

### Root-Level Files

**Architecture docs:**
- `ARCHITECTURE.md` (26KB) — master specification
- `PLATFORM_SPEC.md` (29KB) — frozen v1.0 platform spec
- `PHILOSOPHY.md` (12KB) — UMH philosophy
- `EPISTEMOLOGY.md` (21KB) — how the organism learns
- `PROTOCOLS.md` (10KB) — 4-layer protocol documentation (L0-L3)
- `AGENTS.md` — agent listing
- `cloud.md` — system context

**Project docs:**
- `README.md` — project readme
- `CLAUDE.md` (20KB) — developer agent soul document (read this)
- `CLAUDE.local.md` — local preferences (gitignored)

**Campaign reports:** `C31_*.md`, `C32_*.md`, `C33_*.md` (10 files)

**Build config:**
- `Dockerfile` — root Docker build (Python 3.11-slim)
- `docker-compose.yml` — 6 services
- `Makefile` — make targets
- `pyproject.toml` — ruff, mypy, pytest config
- `requirements.txt` — Python dependencies
- `skills-lock.json` — skill lockfile

**Setup:**
- `install.sh` — initial system setup: installs Python deps, Docker, creates directories, sets permissions
- `setup.sh` — post-clone setup: creates .env from .env.example, installs pre-commit hooks, pulls Docker images
- `patch_pycord.py` — monkey-patches py-cord library to fix known Discord gateway issues

**Dotfiles:** `.gitignore`, `.dockerignore`, `.env.example`, `.env.sessions.tpl`, `.mcp.json`

---

## 8. Top 30 Most-Connected Symbols (Architectural Spine)

These are the symbols with the most edges in the graphify AST index — the structural backbone of the codebase. If you're touching code near these, you're in a high-impact area.

| Edges | Symbol | File |
|-------|--------|------|
| 155 | organism_bridge.py | transports/api/organism_bridge.py |
| 111 | cockpit.py | transports/api/cockpit.py |
| 110 | cockpit_rooms_routes.py | transports/api/cockpit_rooms_routes.py |
| 94 | types.py | substrate/types.py |
| 92 | VisionWsClient | cockpit/src/renderer/api/vision-ws.ts |
| 70 | OrganismDaemon | substrate/organism/daemon.py |
| 57 | TestIndividualArtifactExistence | tests/test_phase14_6b_umh_code_resolved_canon.py |
| 56 | cockpit_operator_loop_ext_routes.py | transports/api/cockpit_operator_loop_ext_routes.py |
| 52 | OrchestratorKernel | substrate/organism/orchestrator_kernel.py |
| 50 | test_agent_executor.py | tests/test_agent_executor.py |
| 47 | cockpit_organism_routes.py | transports/api/cockpit_organism_routes.py |
| 46 | cockpit_operator_loop_session_routes.py | transports/api/cockpit_operator_loop_session_routes.py |
| 46 | cockpit_operator_loop_routes.py | transports/api/cockpit_operator_loop_routes.py |
| 45 | ContinuityEngine | substrate/workstation/continuity_engine.py |
| 44 | orchestrator.py | substrate/control_plane/orchestrator/orchestrator.py |
| 43 | cockpit_spine_router.py | transports/api/cockpit_spine_router.py |
| 42 | ExecutivePortfolioRuntime | substrate/organism/executive_portfolio_runtime.py |
| 41 | tables.py | projections/lyfeos/integration/tables.py |
| 41 | c29_benchmark.py | tests/certification/c29_benchmark.py |
| 40 | CameraAdapter | nodes/windows/umh_node/adapters/camera.py |
| 39 | NodeMeshServer | transports/node_mesh/server.py |
| 38 | WorkPacketEngine | substrate/organism/work_packet_engine.py |
| 38 | ResourceAllocationRuntime | substrate/organism/resource_allocation_runtime.py |
| 37 | AdvisorConversation | substrate/organism/advisor_conversation.py |

---

## 9. Development Workflow

### Pre-Commit Hooks (enforced automatically)
- `scripts/check_cpu_gate.py` — blocks raw subprocess calls
- `scripts/check_dependency_direction.py` — blocks upward imports
- `scripts/check_type_divergence.py` — blocks duplicate type definitions
- `scripts/check_projection_leak.py` — blocks projection names in substrate
- `scripts/check_instance_leak.py` — blocks hardcoded instance context
- `scripts/check_credential_injection.py` — blocks plaintext credentials

### Testing
```bash
python3 -m pytest tests/                    # full suite
python3 -m pytest tests/substrate/          # substrate tests only
python3 -m pytest tests/ -k "test_spine"    # pattern match
```

### Linting & Formatting
```bash
ruff check .         # lint (config in pyproject.toml)
ruff format .        # format
mypy .               # type check (config in pyproject.toml)
```

### Import Verification
```bash
python3 -c "from substrate.types import SignalEnvelope; print('ok')"
python3 -c "from adapters.models.model_router import call_with_fallback; print('ok')"
```

### Git Workflow
- Commit directly to main (solo founder phase)
- Feature branches for experimental or risky changes
- **CI:** `.github/workflows/mobile-build.yml` runs on pushes to `cockpit/` on main — builds web, iOS archive, and Android APK via GitHub Actions
- Pre-commit hooks managed in `.git/hooks/` (not `.pre-commit-config.yaml`)

### Service Restart After Code Changes
```bash
docker restart os-discord     # restart the Discord bot
docker restart os-operator    # restart the API
docker restart os-browser     # restart browser relay
# NEVER: docker compose restart
```

### Cockpit Deploy
```bash
bash cockpit/deploy.sh        # ALWAYS this
# NEVER: flyctl deploy
```

---

## 10. Infrastructure

### Devices
- **VPS** (`srv1500858`) — Hostinger, lightweight orchestrator only. Runs all Docker services. No heavy compute.
- **Beast** (Windows workstation, see `infra/device_registry.json`) — GPU. Heavy compute, media processing, browser verification.
- Connected via Tailscale private network. SSH between devices.

Device names come from `infra/device_registry.json`. Never hardcode raw strings like "VPS" or "Beast" — use the registry.

### Infrastructure Registries (all in `infra/`)
- `device_registry.json` — source of truth for device names, roles, IPs
- `service_dependency_registry.json` — service dependency map
- `workspace_registry.json` — workspace definitions
- `project_registry.json` — project registry
- `umh_node_registry.json` — UMH node registry
- `state_authority_registry.json` — state authority definitions
- `crontab.managed` — cron schedule

### Environment Variables
- `services/.env` — service secrets (never committed)
- `infra/docker/umh.env` — Docker environment
- `.env.example` — template showing required vars
- `.env.sessions.tpl` — 1Password template for session credentials
- `config/nonsecret.env` — non-secret config (safe to commit)

---

## 11. Knowledge System

UMH has a 5-layer pre-computed knowledge system:

```
1. cloud.md                          — system context
2. knowledge/palace/index.md          — memory palace entry
3. knowledge/cloud_palace.md          — palace usage rules
4. data/codebase_pages/cloud.md      — graph rules
5. knowledge/retrieval_rules.md       — enforced hierarchy
```

**Retrieval hierarchy (enforced):**
```
Palace → Graph → Summaries → Raw Source → Logs
```

- **Palace first** — `knowledge/palace/rooms/<room>.md`
- **Graph second** — `python3 scripts/query_graph.py <cmd>`
- **Summaries third** — `data/node_summaries.json`
- **Raw source fourth** — only when graph/summary can't answer
- **Logs last** — transcripts and runtime logs

### Graphify AST Index
The graphify index at `graphify-out/graph.json` provides structural code navigation:

```bash
graphify query graphify-out/graph.json spine          # find symbols named "spine"
graphify query graphify-out/graph.json SignalEnvelope  # find SignalEnvelope
graphify update graphify-out/graph.json file1.py       # incremental update
graphify build .                                       # full rebuild
```

---

## 12. Coverage Verification

This report was generated from real data. Here's how to verify:

```bash
# Total code files in repo
find /opt/OS -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \) \
  -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/.claude/*' | wc -l
# Expected: ~3,485

# Graphify indexed files
python3 -c "import json; d=json.load(open('/opt/OS/graphify-out/graph.json')); print(len(set(n['sourceFile'] for n in d['nodes'])))"
# Expected: ~2,979

# Top-level directories
find /opt/OS -maxdepth 1 -type d | wc -l
# Expected: 37 (including . itself)

# Top-level files
find /opt/OS -maxdepth 1 -type f | wc -l
# Expected: 33
```

**What's not in the graphify index:** Directories with no code files (agents/, config/, data/, docs/, infra/, knowledge/, logs/, media/, runtime/, saas/, skills/, umh/, vault/) — these contain markdown, JSON, YAML, and log files that graphify doesn't parse. They are documented in Section 7 from filesystem audit.

**Coverage: 36 directories + 33 root files = 100% of top-level items documented.**

**File-level coverage:** Section 13 documents 2,605 individual source files — every `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, and `.sh` file in the repository, plus root config files. Each entry has a description derived from actual module docstrings, class names, and function signatures.


---

## 13. File-by-File Reference (Every Source File)

This section documents every source file in the repository — 2,605 files across 15 top-level directories. Each file gets a one-line description extracted from its docstring, class definitions, or function signatures. Grouped by directory.

**Total: 2,245 source files** (1,937 Python + 308 TypeScript)



### substrate/ — Universal Platform Layer (986 files)

### substrate/ (root)
- `__init__.py` — UMH Substrate — the unified intelligence substrate.
- `canonical_types.py` — Canonical Type Registry — single source of truth for all UMH domain types.
- `self_model.py` — Self-Model — the substrate's awareness of its own structure and state.
- `types.py` — classes: SignalSource, SignalUrgency, Modality, Attachment, SignalEnvelope; functions: required_tier_for_action

### substrate/composition/
- `__init__.py` — empty package/namespace marker
- `knowledge_gap_trigger.py` — Knowledge gap trigger — detects gaps during execution and triggers composition.

### substrate/composition/mastery/
- `__init__.py` — empty package/namespace marker

### substrate/composition/mastery/authoring/
- `__init__.py` — Tool Mastery Author Agent.
- `__main__.py` — (no module docstring)
- `agent.py` — Author Agent orchestrator.
- `cli.py` — CLI entry for the Tool Mastery Author Agent.
- `draft.py` — Draft authored section content from SectionEvidence.
- `loader.py` — Research artifact loader.
- `mapping.py` — Section → raw-capture evidence mapping.
- `models.py` — Data types for the Tool Mastery Author Agent.
- `paths.py` — Path resolution for the Tool Mastery Author Agent.
- `reconcile.py` — Reconcile drafts with existing on-disk skill files.
- `verify.py` — Run verify_tool_skill.py against an authored tool.

### substrate/composition/mastery/management/
- `__init__.py` — Tool Mastery Manager — unification layer over the Tool Mastery Engine.
- `active_tool_context.py` — Active Tool Context for the Tool Mastery Engine.
- `backlog.py` — Backlog / bootstrap flow.
- `coverage.py` — Unified coverage evaluator for the Tool Mastery Manager.
- `discovery.py` — Tool discovery for the Tool Mastery Manager.
- `ensure.py` — ensure_mastery — the primary entry point of the Tool Mastery Manager.
- `maintenance.py` — Maintenance flows for the Tool Mastery Manager.
- `mastery_assurance.py` — Mastery Assurance Gate for the Tool Mastery Engine.
- `models.py` — Data types for the Tool Mastery Manager.
- `paths.py` — Path resolution for the Tool Mastery Manager.
- `tool_mastery_resolver.py` — Natural Language Tool Mastery Resolver.

### substrate/composition/mastery/research/
- `__init__.py` — Tool Mastery Research Agent.
- `__main__.py` — (no module docstring)
- `agent.py` — Research Agent orchestrator.
- `artifact.py` — Artifact writer for the Tool Mastery Research Agent.
- `candidate_approval.py` — Candidate approval gate for search-based source discovery.
- `cli.py` — CLI entry for the Tool Mastery Research Agent.
- `docs_site_discovery.py` — Docs site discovery for the Tool Mastery Research Agent.
- `extraction.py` — Structured knowledge extraction for the Tool Mastery Research Agent.
- `fetcher.py` — Fetcher for the Tool Mastery Research Agent.
- `github_extractor.py` — GitHub repo extractor for the Tool Mastery Research Agent.
- `handoff.py` — Safe metadata handoff for the Tool Mastery Research Agent.
- `headless_fetcher.py` — Headless rendering fetch path for the Tool Mastery Research Agent.
- `models.py` — Data types for the Tool Mastery Research Agent.
- `paths.py` — Path resolution for the Tool Mastery Research Agent.
- `search_discovery.py` — Deterministic search candidate generator for the Research Agent.
- `source_discovery.py` — Source discovery for the Tool Mastery Research Agent.
- `source_quality.py` — Source quality scoring for the Tool Mastery Research Agent.
- `structured_crawl.py` — Structured crawl expansion for the Tool Mastery Research Agent.

### substrate/composition/registries/
- `__init__.py` — empty package/namespace marker
- `canonical_command_registry_v1.py` — Canonical Command Registry v1.

### substrate/contracts/
- `__init__.py` — Substrate contracts — canonical Protocol interfaces for the UMH substrate.
- `adapter_contracts.py` — Adapter registry contracts — substrate-owned interface for adapter descriptors.
- `agent_runtime_contracts.py` — Agent runtime protocol — substrate-owned interface for LLM execution.
- `agent_types.py` — Canonical agent types owned by the substrate layer.
- `control_plane_protocol.py` — Control plane protocol — canonical contracts for control plane subsystems.
- `execution_protocol.py` — Execution protocol — canonical contracts for the execution pipeline.
- `governance_protocol.py` — Governance protocol — canonical contract for governance engines.
- `infrastructure_protocol.py` — Infrastructure protocol — canonical contracts for substrate storage and projection.
- `integration_protocol.py` — Integration protocol — canonical contracts for integration-side adapters.
- `organism_protocol.py` — Organism protocol — canonical contracts for the agent society layer.
- `routing_contracts.py` — Routing contracts — substrate-owned capability classes and routing types.
- `understanding_protocol.py` — Understanding protocol — canonical contracts for domain bridges and sources.

### substrate/control_plane/
- `__init__.py` — empty package/namespace marker
- `governance.py` — GovernanceEngine — the single governance entry point for UMH.
- `memory.py` — MemorySystem — unified protocol over existing memory stores.
- `registry.py` — ComponentRegistry — unified registry for all substrate components.

### substrate/control_plane/actions/
- `__init__.py` — empty package/namespace marker
- `actions.py` — Action object — the canonical unit of control in EOS.
- `control_plane.py` — Control Plane — the public entry point for the EOS Action System.
- `deferred.py` — Durable persistence for deferred actions.
- `deferred_status.py` — Lightweight status tracking for deferred actions.
- `executor.py` — Action executors — dispatch by action.type.
- `idempotency.py` — Filesystem sentinel store for Control Plane idempotency.
- `logging.py` — Append-only JSONL loggers for execution and decision records.
- `notifier.py` — Notifier foundation for deferred actions.
- `policy.py` — Policy bridge between the Control Plane and `runtime.authority_engine`.
- `tme.py` — Tool Mastery Engine / Manager integration for the Control Plane.
- `validator.py` — Validation + approval rules for Actions.

### substrate/control_plane/agents/
- `__init__.py` — empty package/namespace marker
- `agent_hierarchy.py` — classes: AgentHierarchy; functions: _venture_name
- `agent_teams.py` — Domain team registry for the OS agent system.
- `ceo_agent.py` — CEOAgent — one per company, strategy layer.
- `ceo_intelligence.py` — CEO Intelligence — real-time business diagnostics.
- `ceo_operational_standards.py` — CEO Best Practices — operational ruleset for
- `ea_operational_standards.py` — EA Best Practices — world class EA operating standards

### substrate/control_plane/context/
- `__init__.py` — ContextAssembler — builds execution context from signal + identity.
- `context_builder.py` — ContextBuilder — single-pass context assembly for the execution spine.
- `context_compaction.py` — ContextCompactor — seamless context window management for long conversations.

### substrate/control_plane/coordination/
- `__init__.py` — empty package/namespace marker
- `coordination_engine.py` — CoordinationEngine — event-driven task coordination for AI agents and humans.

### substrate/control_plane/delegation/
- `__init__.py` — empty package/namespace marker
- `delegation_tracker.py` — Delegation Tracker — tracks tasks routed to CEO agents

### substrate/control_plane/events/
- `__init__.py` — empty package/namespace marker
- `event_bus.py` — EventBus — reactive coordination layer for UMH agents.
- `event_manager.py` — Event Manager — coordinates conferences, offsites, client dinners,

### substrate/control_plane/goals/
- `__init__.py` — empty package/namespace marker
- `goal_selector.py` — GoalSelector — goal selection + system focus layer.

### substrate/control_plane/identity/
- `__init__.py` — Identity resolution for the substrate control plane.
- `ai_identity.py` — AIIdentityEngine — foundational AI identity principles.

### substrate/control_plane/invariants/
- `__init__.py` — empty package/namespace marker
- `coherence_gate.py` — Coherence Gate — fail-closed execution guard.
- `spine_coherence_validator.py` — Canonical Spine Coherence Validator.
- `spine_lineage_contracts.py` — Canonical Spine Lineage Contracts.

### substrate/control_plane/onboarding/
- `__init__.py` — empty package/namespace marker
- `onboarding_engine.py` — OnboardingEngine — conversational onboarding for new EOS founders.
- `setup_wizard.py` — SetupWizard — onboarding flow for new EOS users.

### substrate/control_plane/orchestrator/
- `__init__.py` — empty package/namespace marker
- `orchestrator.py` — Orchestrator — strategic intelligence layer.

### substrate/control_plane/proactive/
- `__init__.py` — empty package/namespace marker
- `proactive_engine.py` — ProactiveIntelligenceEngine — surfaces what matters without being asked.

### substrate/control_plane/router/
- `__init__.py` — SignalRouter — the integration point that wires all subsystems together.
- `control_plane_router_v1.py` — Control Plane Router v1.
- `intent_router.py` — IntentRouter — classify founder messages to the correct agent domain.
- `router_contracts.py` — Control plane router contracts for the UMH substrate layer.

### substrate/control_plane/runtime/
- `__init__.py` — empty package/namespace marker
- `cognitive_loop.py` — CognitiveLoop — full Perceive → Understand → Plan → Execute
- `gateway.py` — Gateway — single control plane for all AI operations.
- `substrate_gateway.py` — SubstrateGateway — unified SignalEnvelope interface over the internal Gateway.

### substrate/control_plane/runtime/orchestrator/
- `__init__.py` — empty package/namespace marker
- `decisions.py` — Decision helpers for signal handler workflows.
- `handlers.py` — Signal handler workflows.
- `loop.py` — Autonomous loop — deterministic orchestration cycle.
- `orchestrator.py` — Orchestrator — execution coordinator for named workflows.
- `pipeline.py` — Pipeline — sequential composition of Control Plane actions.
- `signals.py` — Signals — filesystem-backed event layer for the orchestrator.
- `steps.py` — Reusable orchestrator step helpers.
- `workflows.py` — Workflow registry — wires existing Control Plane workflows into the orchestrator.

### substrate/control_plane/scheduling/
- `__init__.py` — empty package/namespace marker
- `daily_sync.py` — DailySync — structured daily briefing format.
- `ideal_week.py` — Ideal Week — stores and applies the founder's ideal
- `personal_admin.py` — Personal Admin — important dates, gift research,
- `week_architect.py` — WeekArchitect — designs the upcoming week using the Ideal Week

### substrate/control_plane/signals/
- `__init__.py` — empty package/namespace marker
- `signal_hierarchy.py` — SignalHierarchyEngine — ranks signal before the filter applies.

### substrate/control_plane/strategy/
- `__init__.py` — empty package/namespace marker
- `portfolio_advisor.py` — Portfolio Advisor — board-level intelligence across all companies in the portfolio.
- `portfolio_advisor_standards.py` — Portfolio Advisor Best Practices — operational
- `strategy_engine.py` — StrategyEngine — first-principles strategic reasoning layer.
- `task_yield_matrix.py` — Task Yield Matrix — task delegation audit framework.

### substrate/execution/
- `__init__.py` — empty package/namespace marker
- `cpu_gate.py` — Universal CPU gate — single choke point for all UMH execution paths.
- `credential_gate.py` — Credential injection gate — validates credentials flow through 1Password.
- `executor.py` — Work packet executor — the governed execution pipeline.
- `feedback.py` — FeedbackCapture — captures execution quality signals.
- `feedback_loop.py` — RLHF Feedback Loop — explicit human feedback ingestion and learning cycle.
- `mastery_gate.py` — Mastery Gate — mandatory pipeline check before execution.
- `pipeline.py` — ExecutionPipeline — the master success loop.
- `proof_generator.py` — Proof generator — creates verifiable proof artifacts from execution results.
- `queue.py` — Execution queue — ordered, priority-aware queue for work packets.
- `spine.py` — ExecutionSpine — the 8-stage execution pipeline.
- `trace.py` — TraceRecorder — records execution traces for every signal lifecycle.
- `understanding_bridge.py` — Understanding Bridge — wires the understanding layer into the execution pipeline.

### substrate/execution/actuation/
- `__init__.py` — empty package/namespace marker
- `actuator_backend_registry_v1.py` — Actuator Backend Registry v1.
- `actuator_maturity_v1.py` — Actuator Maturity Model v1.
- `observed_desktop_state_v1.py` — Observed Desktop State v1.
- `windows_foreground_actuator_v1.py` — Windows Foreground Actuator v1 (Maturity-Aware).

### substrate/execution/adapters/
- `__init__.py` — empty package/namespace marker
- `physical.py` — Physical Adapter Framework — hardware and IoT extension points.

### substrate/execution/agents/
- `__init__.py` — empty package/namespace marker
- `browser_agent.py` — BrowserAgent — Playwright-based web operator for EOS agents.
- `computer_use_agent.py` — Computer-Use Agent — governed visual automation across execution layers.

### substrate/execution/bridge/
- `__init__.py` — execution.bridge — Lazy-import package.
- `actions.py` — SafeAction schema — structured intents for future local execution.
- `app_allowlist.py` — App launch allow-list for LAUNCH_APP actions.
- `audio_loop.py` — Audio loop — bounded local interaction-window model.
- `auto_task_generation.py` — Auto-task generation — bridges the perception layer to the task system.
- `browser_agent.py` — Browser agent — real Playwright execution surface for the substrate.
- `capabilities.py` — Capability abstraction — what a node can do.
- `capability_routing.py` — Capability-aware task routing — deterministic target selection.
- `capability_tagging.py` — Capability tagging — additive pre-routing layer.
- `claude_responder.py` — Claude Responder v1 — thin adapter that turns a text prompt into a reply by
- `claude_session_bridge.py` — Claude Code Session Bridge v1 — persistent tmux-backed Claude Code sessions.
- `context_lifecycle.py` — Context lifecycle — pressure-aware session maintenance with checkpoint/restore.
- `day_workflows.py` — Day workflow coordination — open_day / close_day.
- `discord_mode_routing.py` — Discord Channel Mode Routing v1 — bounded channel→mode classification.
- `discord_output_policy.py` — Display-name policy for Discord watcher output.
- `discord_text_transport.py` — Discord text transport — Pseudo-Live Voice Loop v1.
- `discord_voice_playback.py` — Discord voice playback — bounded TTS adapter on top of the transport.
- `discord_voice_transport.py` — Discord voice transport — bounded adapter onto the existing voice substrate.
- `event_spine.py` — Event Spine — unified structured event model for EOS substrate.
- `execution_trace.py` — Execution trace for EOS request lifecycle.
- `live_sessions.py` — Live sessions — real-time continuous interaction layer for the substrate.
- `local_control.py` — Local control — safe OS-level action layer for the local machine.
- `local_listener.py` — Local listener — bounded wake/activation layer for the substrate.
- `memory_scope_contracts.py` — Memory scope contracts.
- `mode_behavior.py` — Mode behavior shaping — post-router output shaping by substrate mode.
- `node_controller.py` — NodeController — unified routing brain for task→node dispatch.
- `node_transport.py` — NodeTransport — aiohttp transport adapter for local station daemon.
- `nodes.py` — Node abstraction — execution targets beyond "the VPS".
- `operator_presence.py` — Operator presence — tiny deterministic hybrid intro/outro templates.
- `operator_session.py` — Operator session spine — single authoritative source of truth for the
- `operator_state.py` — Operator state — bounded unified state model for the workstation operator.
- `operator_transitions.py` — Operator transitions — deterministic state transition layer.
- `perception.py` — Perception layer — ambient sensing of system and environment state.
- `pipeline_execution.py` — Pipeline execution engine — step-level execution, retry, and resume.
- `playback_status.py` — Shared playback status snapshot shape for voice transports.
- `resource_guard.py` — Resource Guard v1 — pre-execution VPS resource check.
- `result_query.py` — Result query helpers — tiny operator-facing view over the ResultStore.
- `result_store.py` — ResultStore — durable index of ingested ActionResults.
- `ritual_body.py` — Ritual body — tiny executable layer for open_day / close_day.
- `ritual_inference.py` — Ritual hint inference — infer a scene hint when the operator did not
- `ritual_runner.py` — Ritual runner — shell-callable entry points for open_day / close_day.
- `rituals.py` — Ritual workflow scaffold — open_day / close_day.
- `roles.py` — Agent role abstraction — clean contract for multi-agent orchestration.
- `scene_capabilities.py` — Scene → capability requirements — tiny explicit mapping.
- `scene_policy.py` — Scene policy — deterministic mapping from (node, readiness, hint) → scene.
- `scenes.py` — Scene registry — small, code-declared workstation bootstrap recipes.
- `session_control.py` — Session control — lifecycle commands for Claude Code tmux sessions.
- `session_discord_bridge.py` — Session Discord Bridge — routes SessionWatcher events to Discord and back.
- `session_watcher.py` — Session Watcher — continuous tmux state machine for Claude Code sessions.
- `station.py` — Station Daemon contract.
- `station_bus.py` — StationBus — MVP transport between EOS and local Station Daemons.
- `station_daemon.py` — StationDaemon — minimal local node execution loop.
- `station_helpers.py` — Small helpers for proposing MVP SafeActions to a named station.
- `station_presence.py` — Station presence — unified station posture and availability state.
- `station_readiness.py` — Station readiness — derived view of whether a node is fit for ritual work.
- `storage.py` — Substrate storage — minimal persistence for NodeRegistry and RitualRegistry.
- `target_policy.py` — Hybrid Execution Target Policy v1 — deterministic target resolution.
- `task_decomposition.py` — Deterministic task decomposition — breaks tasks into ordered pipeline steps.
- `task_execution.py` — Real task execution pipeline — binds tasks to tmux-backed Claude sessions.
- `task_pipeline.py` — Task pipeline data model — ordered multi-step execution for tasks.
- `task_queue.py` — Priority queue layer for the task system.
- `task_system.py` — Task autonomy and overnight execution system (v1).
- `transcript_inject.py` — Transcript injection — the bounded entry point for text-shaped input
- `tts_sanitize.py` — TTS reply sanitization — strip Claude Code / provider footer noise.
- `voice_eos_responder.py` — Voice → EOS responder bridge.
- `voice_first.py` — Voice-first response orchestration.
- `voice_session.py` — Voice session — bounded live voice-presence layer for the substrate.
- `wake_producer.py` — Wake producer — bounded wake-word / clap activation layer for the substrate.
- `workflow_delegation.py` — Workflow Delegation Layer v1 — deterministic intent classification + policy.
- `workflow_execution.py` — Workflow Execution Layer v1.1 — bounded, deterministic workflow handlers.
- `workload_policy.py` — Workload Classification Policy v1 — deterministic execution weight.

### substrate/execution/ingestion/
- `__init__.py` — Canonical ingestion pipeline — substrate.execution.ingestion.

### substrate/execution/loop/
- `__init__.py` — Persistent execution loops — config-driven autonomous cycles for UMH.
- `execution_loop.py` — ExecutionLoop — closed-loop goal execution with outcome feedback.
- `persistent_loop.py` — PersistentLoop — config-driven runtime loops for UMH.
- `stages.py` — Built-in loop stages — composable pipeline steps for persistent loops.

### substrate/execution/media/
- `__init__.py` — empty package/namespace marker
- `media_processor.py` — MediaProcessor — unified multimodal file handler.

### substrate/execution/runtime/
- `__init__.py` — empty package/namespace marker
- `capability_router.py` — capability_router — Intent-driven tool selection for UMH.
- `execution_contracts_v1.py` — Execution Contracts v1 for the canonical runtime spine.
- `execution_spine.py` — ExecutionSpine — single execution path for all EOS operations (legacy runtime).
- `live_local_runtime_execution_v1.py` — Live Local Runtime Execution v1 for the UMH substrate layer.
- `local_runtime_supervisor_v1.py` — Local Runtime Supervisor v1 for the UMH substrate layer.
- `node_sync_gate_v1.py` — Node Sync Gate v1 for the UMH substrate layer.
- `runtime_bootstrap_state_v1.py` — Runtime Bootstrap State v1.
- `runtime_dispatch_queue_v1.py` — Runtime Dispatch Queue v1 for the UMH substrate layer.
- `runtime_execution_result_v1.py` — Runtime Execution Result v1 — proof-bearing execution result type.
- `runtime_heartbeat_v1.py` — Runtime Heartbeat v1 for the UMH substrate layer.
- `runtime_presence_state_v1.py` — Runtime Presence State v1 — workstation presence tracking.
- `runtime_recovery_v1.py` — Runtime Recovery v1 for the UMH substrate layer.
- `runtime_session_registry_v1.py` — Runtime Session Registry v1 for the UMH substrate layer.
- `substrate_continuity_engine_v1.py` — Substrate Continuity Engine v1.
- `worker_runtime_contracts.py` — Worker runtime contracts for the UMH substrate layer.
- `worker_supervisor_v1.py` — Worker Supervisor v1 for the UMH substrate layer.
- `workpacket_execution_gate_v1.py` — WorkPacket Execution Gate v1 for the UMH substrate layer.

### substrate/execution/voice/
- `__init__.py` — empty package/namespace marker
- `session.py` — Voice Session — end-to-end voice pipeline loop.
- `voice_engine.py` — VoiceEngine — intelligent voice layer for Discord.

### substrate/execution/workers/
- `__init__.py` — empty package/namespace marker

### substrate/execution/workers/workstation/
- `__init__.py` — empty package/namespace marker
- `environment_mapping_engine_v1.py` — Environment Mapping Engine v1.
- `foreground_cu_ingestion_execution_v1.py` — Foreground CU Ingestion Execution v1.
- `relay_execution_transport_v1.py` — Relay Execution Transport v1.
- `tmux_operational_adapter_v1.py` — Tmux Operational Adapter v1.
- `visible_actuation_proof_v1.py` — Visible Actuation Proof v1.
- `workstation_contracts_v1.py` — Workstation Contracts v1 for operational embodiment.
- `workstation_execution_orchestrator_v1.py` — Workstation Execution Orchestrator v1.
- `workstation_node_registry_v1.py` — Workstation Node Registry v1.
- `workstation_relay_self_heal_v1.py` — Workstation Relay Self-Heal v1.

### substrate/execution/workers/workstation/_dormant/
- `__init__.py` — empty package/namespace marker
- `adapter_autogeneration_engine_v1.py` — Adapter Autogeneration Engine v1.
- `adaptive_governance_intelligence_engine_v1.py` — Adaptive Governance Intelligence Engine v1.
- `browser_continuity_bridge_v1.py` — Browser Continuity Bridge v1.
- `browser_execution_orchestrator_v1.py` — Browser Execution Orchestrator v1.
- `browser_gui_contracts_v1.py` — Browser and GUI Embodiment Contracts v1.
- `browser_gui_embodiment_engine_v1.py` — Browser and GUI Embodiment Engine v1.
- `browser_observability_pipeline_v1.py` — Browser Observability Pipeline v1.
- `browser_operational_modes_v1.py` — Browser Operational Modes v1.
- `browser_replay_validator_v1.py` — Browser Replay Validator v1.
- `constitutional_antifragility_resilience_engine_v1.py` — Constitutional Antifragility and Evolutionary Resilience v1.
- `constitutional_epistemic_intelligence_engine_v1.py` — Constitutional Epistemic Intelligence and Reality Coherence Engine v1.
- `constitutional_identity_continuity_engine_v1.py` — Constitutional Identity Continuity and Sovereign Memory Architecture v1.
- `constitutional_resource_economics_engine_v1.py` — Constitutional Resource Economics and Coordination Engine v1.
- `constitutional_strategic_intelligence_engine_v1.py` — Constitutional Strategic Intelligence and Recursive Leverage Planning Engine v1.
- `constitutional_substrate_governance_layer_v1.py` — Constitutional Substrate Governance Layer v1.
- `constitutional_telos_alignment_engine_v1.py` — Constitutional Telos Alignment and Purpose Governance v1.
- `distributed_constitutional_substrate_federation_v1.py` — Distributed Constitutional Substrate Federation v1.
- `governed_browser_adapter_v1.py` — Governed Browser Adapter v1.
- `governed_recursive_orchestration_engine_v1.py` — Governed Recursive Orchestration Engine v1.
- `governed_shell_adapter_v1.py` — Governed Shell Adapter v1.
- `persistent_substrate_continuity_engine_v1.py` — Persistent Substrate Continuity Engine v1.
- `recursive_capability_planning_engine_v1.py` — Recursive Capability Planning Engine v1.
- `visible_gui_adapter_v1.py` — Visible GUI Adapter v1.
- `workstation_continuity_bridge_v1.py` — Workstation Continuity Bridge v1.
- `workstation_observability_pipeline_v1.py` — Workstation Observability Pipeline v1.
- `workstation_operational_embodiment_engine_v1.py` — Workstation Operational Embodiment Engine v1.
- `workstation_operational_modes_v1.py` — Workstation Operational Modes v1.
- `workstation_relay_heartbeat_v1.py` — Workstation Relay Heartbeat v1.
- `workstation_relay_node_v1.py` — Workstation Relay Node v1.
- `workstation_relay_proof_v1.py` — Workstation Relay Proof v1.
- `workstation_replay_validator_v1.py` — Workstation Replay Validator v1.
- `workstation_state_registry_v1.py` — Workstation State Registry v1.

### substrate/foundation/
- `__init__.py` — Foundation — substrate laws, identity, perspective.
- `identity.py` — Identity continuity schema — maintains coherent self across time and context switches.
- `laws.py` — Substrate laws — re-exports from substrate.ontology.laws.
- `perspective.py` — Perspective schema — the lens through which the substrate interprets signals.

### substrate/governance/
- `__init__.py` — UMH Governance — risk classification, authority, and policy enforcement.
- `authority.py` — Authority levels — what the system can do without human intervention.
- `policy_engine.py` — Policy engine — evaluates risk class + context to produce governance verdicts.
- `risk_classes.py` — Action risk categories — semantic classification of side-effect types.
- `security.py` — Security hardening — input validation, rate limiting, audit logging.

### substrate/governance/accountability/
- `__init__.py` — empty package/namespace marker
- `accountability.py` — AccountabilityEngine — holds the founder to their word.

### substrate/governance/policy/
- `__init__.py` — empty package/namespace marker
- `authority_engine.py` — classes: AuthorityEngine
- `authority_tier.py` — Authority tier constants and validation for ingestion sources.
- `confidentiality.py` — Confidentiality Protocol — handles sensitive
- `execution_authority_engine_v1.py` — Execution Authority Engine v1 for the UMH substrate layer.

### substrate/governance/principles/
- `__init__.py` — empty package/namespace marker
- `principle_engine.py` — PrincipleEngine — injects quality standards into every AI decision.

### substrate/governance/quality/
- `__init__.py` — empty package/namespace marker
- `quality_gate.py` — QualityTransformationGate — every output passes through the four values.

### substrate/governance/validation/
- `__init__.py` — empty package/namespace marker
- `completeness_engine.py` — Completeness Engine — 13-slot validation for plans, workflows, and compositions.
- `output_validator.py` — OutputValidator — EOS applies its own principles to its own outputs.

### substrate/integrations/
- `__init__.py` — Substrate integration infrastructure — capability bridge, CORS, health, product connections.
- `bridge.py` — UMH Bridge — connects UMH model routing to runtime/model_router.py.
- `cors.py` — CORS configuration for UMH API.
- `health.py` — Health aggregator — dashboard endpoint combining all service health signals.
- `product_connections.py` — SaaS product connection manager — unified API for EOS, CreatorOS, LYFEOS.

### substrate/intelligence/
- `__init__.py` — empty package/namespace marker
- `finetune_harness.py` — Fine-tuning harness — scaffolds LoRA fine-tuning for self-hosted models.
- `runtime.py` — Proprietary Intelligence Runtime — the system's learned intelligence.
- `training_extractor.py` — Training data extraction from UMH execution traces.

### substrate/memory/
- `__init__.py` — Memory candidate staging, promotion, auto-reconciliation, bridging, and watching.
- `auto_reconciler.py` — AutoReconciler — closes the gap between promoted memories and canonical store.
- `candidate_generator.py` — MemoryCandidateGenerator — stages memory candidates from completed traces.
- `canonical_write.py` — CanonicalWritePath -- single facade for organism-loop memory writes.
- `claude_bridge.py` — Claude Bridge — syncs Claude Code memory files to substrate memory candidates.
- `promoter.py` — MemoryPromoter — evaluates candidates for promotion to durable storage.
- `watcher.py` — Memory Watcher — substrate-level filesystem watcher for agent memory directories.

### substrate/meta_ide/
- `__init__.py` — Meta IDE — engineering reality awareness, planning, and proof loop.
- `browser_evidence_collector.py` — Browser Evidence Collector — runs on executor nodes to collect verification evidence.
- `browser_verification_gate.py` — Browser Verification Gate — blocking validation for UI-bearing work.
- `engineering_execution.py` — Engineering Execution Contracts — governed execution session types.
- `engineering_intent.py` — Engineering Intent Contract — types for autonomous engineering planning.
- `engineering_planner.py` — Engineering Planner — deterministic planning from high-level intent.
- `engineering_session_coordinator.py` — Engineering Session Coordinator — governed execution orchestration.
- `engineering_work_generator.py` — Engineering Work Generator — bridge from plans to governed work packets.
- `repository_model.py` — Repository reality model — read-only git awareness.
- `review_package_builder.py` — Review Package Builder — deterministic proof assembly.
- `roadmap_gap_engine.py` — Roadmap Gap Engine — detects gaps and recommends engineering work.
- `roadmap_intelligence.py` — Roadmap intelligence — phase and planning awareness.
- `shared_planner.py` — Shared EngineeringPlanner singleton for all cockpit route modules.
- `workspace_intelligence.py` — Workspace intelligence — engineering-state awareness.
- `workspace_observation.py` — Workspace Observation — live engineering runtime observation.
- `workspace_registry.py` — Workspace Registry — single source of truth for workspace topology.
- `workspace_runtime_graph.py` — Workspace Runtime Graph — canonical workspace topology models.
- `workspace_topology_engine.py` — Workspace Topology Engine — live workspace topology with health.

### substrate/observability/
- `__init__.py` — Observability — trace, proof, outcome classification, and error recording.
- `error_recorder.py` — Canonical fix-forever error recorder.
- `jsonl_rotation.py` — JSONL rotation utility.
- `outcome_classifier.py` — OutcomeClassifier — classifies execution results into outcome categories.
- `trace_store.py` — TraceStore — append-only JSONL trace persistence.

### substrate/ontology/
- `__init__.py` — empty package/namespace marker
- `laws.py` — Governing laws — enacted constraints that govern UMH like physics governs reality.
- `primitives.py` — Ontology primitives — the computational physics of UMH.
- `relationships.py` — Typed relationship edges between ontology observations.

### substrate/ontology/domains/
- `__init__.py` — Domain bridges — re-exports from substrate.understanding.domains.
- `contract.py` — Domain bridge contract — re-exports from substrate.understanding.domains.contract.
- `creator.py` — Creator domain bridge — re-exports from substrate.understanding.domains.creator.
- `life.py` — Life domain bridge — re-exports from substrate.understanding.domains.life.

### substrate/operator/
- `__init__.py` — UMH Operator — unified intent classification and routing layer.
- `continuity_engine.py` — Continuity Engine — operator presence and continuity aggregation.
- `device_continuity.py` — Device Continuity — per-device presence state tracking.
- `intent_receipt.py` — Unified intent receipt — canonical audit trail for every operator interaction.
- `intent_router.py` — Intent Router — deterministic-first classification of operator intent.
- `intent_runtime.py` — Intent Runtime — canonical intent preservation for operator continuity.
- `operator_attention_engine.py` — Operator Attention Engine — deterministic ranked priorities.
- `operator_context.py` — Operator Context Models — types for the operator home surface.
- `operator_context_engine.py` — Operator Context Engine — aggregation façade for operator home.
- `operator_presence.py` — Operator Presence Models — types for presence and continuity tracking.
- `operator_snapshot_runtime.py` — Operator Snapshot Runtime — answers the 5 operator questions.
- `presence_timeline.py` — Presence Timeline — operator presence transition tracking.
- `repository_context_resolver.py` — UMH Repository Context Resolver — maps workspace state to repo context.
- `screen_awareness.py` — UMH Screen Awareness — types for operator visual workspace context.
- `screen_context_providers.py` — UMH Screen Context Providers — three modes of screen awareness.
- `screen_observation_engine.py` — UMH Screen Observation Engine — node-role-aware screen context aggregation.
- `voice_query_engine.py` — Voice Query Engine — context-grounded query resolution.
- `workstation_session_runtime.py` — Workstation Session Runtime — operator leave/return with full context restore.
- `workstation_translator.py` — UMH Workstation Translator — Beast payload → canonical ScreenSnapshot.

### substrate/organism/
- `__init__.py` — UMH Organism — distributed orchestration substrate.
- `action_bridge.py` — Action Bridge — governed composition of catalog, observation, and execution.
- `action_catalog.py` — Action Catalog — data-driven registry of governed operator actions.
- `action_envelope.py` — ActionEnvelope — canonical executable object for ALL organism mutations.
- `action_voice_contract.py` — Voice/Intent Action Contract — interface between intent sources and ActionBridge.
- `advisor.py` — Advisor cell — the top-level orchestrator of the organism.
- `advisor_conversation.py` — Conversational advisor — multi-turn conversation with intent routing.
- `advisor_hierarchy.py` — Advisor Hierarchy — governed recursive advisory orchestration.
- `advisor_reconciliation.py` — Operator Reconciliation Integration — detects reconciliation intent in operator input.
- `agent_capability_model.py` — Agent Capability Model — track agent reliability per capability.
- `agent_execution_runner.py` — Agent Execution Runner — invokes coding agents inside governed sandboxes.
- `agent_fleet_runtime.py` — Agent Fleet Runtime — unified agent coordination layer.
- `agent_registry.py` — Agent Registry — agent types, capabilities, permissions, and routing.
- `agent_runtime.py` — Agent base runtime — the foundational behavior of every agent in the society.
- `agents.py` — Concrete agent cells — Researcher, Builder, AutoResearch.
- `allocation_loop.py` — Governed runtime allocation loop — continuous leverage allocator.
- `approval_gate.py` — Operator Approval Gate — requires explicit approval before sandbox execution.
- `approval_store.py` — Approval store — JSONL persistence for governance-blocked signals.
- `artifact_registry.py` — Artifact Registry — indexes produced outputs across UMH.
- `assisted_executor.py` — Assisted Executor — governed execution of approved maintenance actions.
- `assumption_tracking_runtime.py` — Assumption Tracking Runtime — governed assumption records for UMH.
- `async_coordinator.py` — Async coordinator execution — event-driven objective lifecycle.
- `automation_pipeline.py` — Automation Candidate Pipeline — promote repeated interventions to automation.
- `autonomous_action_gateway.py` — Autonomous Action Gateway — structural enforcement of spine-routed mutation.
- `autonomous_cadence.py` — Autonomous Cadence — scheduled autonomous improvement discovery.
- `autonomous_improvement_lane.py` — Autonomous Improvement Lane — bounded autonomous LOW-risk self-improvement.
- `autonomous_pr_factory.py` — Autonomous PR Factory — converts eligible improvements into isolated PRs.
- `autonomous_tick.py` — Autonomous tick engine — continuous organism metabolism heartbeat.
- `benchmark_harness.py` — Benchmark Harness — measures and compares Pipeline A (legacy) vs Pipeline B (governed).
- `bottleneck_engine.py` — Bottleneck Detection Engine — organism operational self-optimization.
- `candidate_supply_engine.py` — Candidate Supply Engine — discovers improvement candidates from real organism sources.
- `canonical_update.py` — Canonical Update Proposal — proposed changes to canonical truth.
- `capability_compounding_runtime.py` — Capability Compounding Runtime — Campaign 22.4
- `capability_evolution_engine.py` — Capability Evolution Engine — Campaign 12.2
- `capability_gap_engine.py` — Capability Gap Engine — detect missing or immature capabilities for goals.
- `capability_graph_engine.py` — Capability Graph Engine — explicit dependency/composition edges between capabilities.
- `capability_portfolio_runtime.py` — Capability Portfolio Runtime — portfolio-level health and compounding metrics.
- `capability_runtime.py` — Capability Runtime — emergent capability tracking and maturity lifecycle.
- `capability_validation_runtime.py` — Capability Validation Runtime — benchmark storage, reporting, and freshness tracking.
- `change_event.py` — Change Event — state change model for propagation planning.
- `changeset_manifest.py` — Changeset Manifest — evidence record for every autonomous branch/PR.
- `claude_code_runtime_adapter.py` — Claude Code PTY runtime adapter — skeleton with truthful availability.
- `coherence_propagation.py` — Coherence Propagation Engine — parallel dependent-system updates on verified change.
- `command_runtime.py` — Command Runtime — canonical intent-to-action layer for all operator surfaces.
- `composition_engine.py` — Composition Engine — deterministic intent → plan from observed capabilities.
- `compounding_engine.py` — Capability Compounding Engine — turn internal learning into leverage.
- `compute_fabric_runtime.py` — Compute Fabric Runtime — unified compute body map.
- `context_diagnostic.py` — Context Diagnostic — models for diagnostic reports on context state.
- `context_ingestion_engine.py` — Context Ingestion Engine — ingest local/system context sources.
- `context_resolution.py` — Context Resolution Engine — "the system already knows" layer.
- `continuity_runtime.py` — Continuity Runtime — operational continuity engine for UMH.
- `continuous_qualification.py` — Continuous Qualification — daemon tick stage for live ORL measurement.
- `contradiction_engine.py` — Contradiction Engine — detect mismatches between declared and observed reality.
- `coordinator.py` — OrganismCoordinator — hierarchical task decomposition and runtime assignment.
- `correspondence_scheduler.py` — Correspondence Scheduler — periodic drift detection for projections.
- `council.py` — Council — multi-perspective advisory layer for the advisor.
- `cross_source_reconciler.py` — Cross-Source Reconciler — detect relationships across fragmented sources.
- `daemon.py` — Organism daemon — manages agent lifecycle within the control plane.
- `daily_driver_log.py` — Daily Driver Log — records unhandled failures during real operation.
- `decision_impact_engine.py` — Decision Impact Engine — blast radius analysis for strategic decisions.
- `decision_lineage_engine.py` — Decision Lineage Engine — causal chain traversal for strategic decisions.
- `decision_registry.py` — Decision Registry — first-class strategic decision records for UMH.
- `decision_validity_engine.py` — Decision Validity Engine — evaluates whether decisions still make sense.
- `delegation_followup.py` — Automated delegation follow-up — checks overdue delegations and acts.
- `delegation_readiness_runtime.py` — Delegation Readiness Runtime — pre-assignment feasibility + outcome prediction.
- `delegation_runtime.py` — Delegation Runtime — intent classification, delegation proposals, mission lifecycle.
- `delegation_topology.py` — Delegation Topology Planner — chooses execution structure for a work packet.
- `dependency_graph.py` — Dependency Graph — subsystem dependency model for UMH.
- `deploy_verification_worker.py` — Deploy verification worker — no human should discover a white screen.
- `dev_session_tracker.py` — DevSessionTracker — wraps development sessions as governed spine executions.
- `development_session_bridge.py` — DevelopmentSessionBridge — makes coding agents governed organs of the organism.
- `device_awareness.py` — Device Awareness Runtime — deterministic device detection and capability routing.
- `device_capacity.py` — Device Capacity Model — per-device worker slots and backpressure.
- `device_provisioner.py` — Device Provisioner — multi-OS diagnosis + role-based provisioning.
- `device_registry_writer.py` — Device Registry Writer — atomic writes + cache invalidation.
- `device_role_registry.py` — Device role registry — tracks device roles and capabilities in the UMH organism.
- `dex_conversation.py` — Backward-compat shim — canonical module is advisor_conversation.py.
- `dex_reconciliation.py` — Backward-compat shim — canonical module is advisor_reconciliation.py.
- `diagnostic_engine.py` — Diagnostic Engine — analyze ingested context for canonical truth state.
- `distributed_runtime.py` — Distributed Runtime — facade composing all distributed runtime subsystems.
- `documentation_awareness_runtime.py` — Documentation Awareness Runtime — content-level metadata for docs.
- `domain_registry.py` — Domain Registry — first-class domain definitions for the Empire WorkPacket Engine.
- `drift_detection_engine.py` — Drift Detection Engine — unified drift synthesis.
- `embodiment_runtime.py` — Embodiment Runtime — natural language intent becomes governed work.
- `empire_router.py` — Empire Router — routes founder intent to domain-classified, governed WorkPackets.
- `environment_discovery.py` — Environment Discovery — device, filesystem, application, account inventory.
- `environment_graph.py` — Environment graph — continuously updated operational world-state.
- `environment_reconciler.py` — Environment reconciliation — continuous drift correction.
- `event_spine.py` — Unified organism event spine — canonical organism-level event transport.
- `execution_coordinator.py` — Execution Coordinator Runtime — canonical orchestration layer (Phase 13).
- `execution_economy.py` — Execution Economy — runtime cost/value tracking and leverage scoring.
- `execution_graph.py` — Execution Graph — evidence-grade lineage validation over existing execution infrastructure.
- `execution_journal.py` — ExecutionJournal — append-only execution ledger for all organism mutations.
- `execution_ledger.py` — Execution Ledger — canonical record of every execution request and outcome.
- `execution_lifecycle_runtime.py` — Execution Lifecycle Runtime — Campaign 16.2.
- `execution_modes.py` — Execution Modes — governed transition from observation to action.
- `executive_brief_runtime.py` — Executive Brief Runtime — structured operator briefing synthesis.
- `executive_portfolio_runtime.py` — C14.2 — Executive Portfolio Runtime.
- `executor_runtime.py` — Executor Runtime — canonical execution contract layer (Phase 14).
- `goal_alignment_engine.py` — Goal Alignment Engine — ensure work supports goals.
- `goal_drift_engine.py` — Goal Drift Engine — detect movement away from objectives.
- `goal_hierarchy_engine.py` — Goal Hierarchy Engine — structural operations on the goal tree.
- `governance_runtime.py` — C15.0 — Governance Runtime.
- `governed_execution_runtime.py` — Governed Execution Runtime — Campaign 16.0.
- `governed_spine.py` — GovernedExecutionSpine — THE single mutation gateway in the organism.
- `governed_work_runtime.py` — Governed Work Runtime — MANDATORY execution gateway.
- `grounded_handlers.py` — Grounded status handlers — deterministic answers backed by real data.
- `grounding_registry.py` — Grounding registry — source data requirements for deterministic status answers.
- `handoff.py` — Agent handoff protocol — structured agent-to-agent task transfer.
- `homeostasis.py` — Homeostasis — the organism's immune/self-regulation system.
- `impact_analyzer.py` — Impact Analyzer — computes change impact across the propagation graph.
- `infrastructure_runtime.py` — Infrastructure Runtime — register and track system & institutional infrastructure.
- `ingestion_job.py` — Ingestion Job — tracks context ingestion work units.
- `institutional_memory_runtime.py` — C15.2 — Institutional Memory Runtime.
- `intent_classifier.py` — Intent Classifier — converts raw user intent into structured classification.
- `knowledge_awareness_runtime.py` — Knowledge Awareness Runtime — meaning, not just documents.
- `knowledge_model_registry.py` — Knowledge Model Registry — system knowledge containers.
- `learning_extraction_runtime.py` — Learning Extraction Runtime — Campaign 12.0
- `learning_portfolio_runtime.py` — Learning Portfolio Runtime — Campaign 12.3
- `leverage_assimilation.py` — External Leverage Assimilation — ingest, classify, and operationalize
- `leverage_engine.py` — Leverage Engine — determines highest-impact actions.
- `leverage_metrics.py` — Operational Leverage Metrics — measures actual organism value.
- `maintenance_loop.py` — Autonomous Maintenance Loop — OBSERVE-mode infrastructure health cycle.
- `memory_promotion.py` — Memory Promotion Pipeline — governed promotion from instance to canonical memory.
- `mesh_reconciler.py` — Mesh node reconciliation — syncs RuntimeGraph with live mesh relay.
- `meta_ide_runtime.py` — Meta IDE Runtime — unified development surface.
- `mission.py` — Mission — bridge between user conversation and organism execution.
- `mutation_catalog.py` — MutationCatalog — maps HTTP endpoints to MutationSpec names.
- `mutation_registry.py` — MutationRegistry — canonical registry of executable mutation types.
- `mutation_router.py` — MutationRouter — canonical choke point for all organism state mutations.
- `next_action_engine.py` — Next Action Engine — evidence-based action recommender.
- `objective_physics.py` — Objective Physics — causal execution dynamics.
- `objective_queue.py` — Continuous objective queue — intake front door for OrganismCoordinator.
- `observability.py` — Organism Observability — unified dashboard snapshot.
- `operating_loop_coherence_runtime.py` — Operating Loop Coherence Runtime — aggregation, reporting, coherence synthesis.
- `operational_truth.py` — OperationalTruthSnapshot — scoreboard for UMH operational reality.
- `operationalization_runtime.py` — Operationalization Runtime — link capabilities to reusable artifacts.
- `operator_acceptance.py` — Operator acceptance run model — end-to-end acceptance test tracking.
- `operator_acceptance_mode.py` — Operator acceptance mode — standard multi-runtime vs deterministic-only vs blocked.
- `operator_acceptance_scenarios.py` — Operator acceptance scenarios — predefined end-to-end test scenarios.
- `operator_compression.py` — Operator Compression — reduce human operational burden.
- `operator_escape_tracker.py` — Operator Escape Tracker — records exits from UMH organism.
- `operator_loop_coordinator.py` — Operator loop coordinator — orchestrates the end-to-end acceptance loop.
- `operator_loop_runtime.py` — Operator Loop Runtime — the Jarvis Runtime.
- `operator_migration_runtime.py` — Operator Migration Runtime — track and close external-loop dependencies.
- `operator_readiness_gate.py` — OperatorReadinessGate — Phase 13.4 readiness assessment.
- `operator_response.py` — Operator Response — structured response contract for the orchestrator kernel.
- `operator_session.py` — Operator Session — conversational state for operator-orchestrator interaction.
- `orchestration_loop.py` — Orchestration loop — persistent autonomous execution for the organism.
- `orchestrator_awareness_runtime.py` — Orchestrator Awareness Runtime — synthesized reality model for the orchestrator.
- `orchestrator_kernel.py` — Orchestrator Kernel — central intelligence routing for operator interaction.
- `organism_coordination_engine.py` — C15.1 — Organism Coordination Engine.
- `organism_loop.py` — OrganismLoopEngine -- convergence coordinator for organism execution.
- `organism_portfolio_runtime.py` — C15.3 — Organism Portfolio Runtime.
- `organism_state_runtime.py` — Organism State Runtime — Campaign 16.1.
- `outcome_learning.py` — Outcome Learning Loop — learn from execution outcomes.
- `outcome_pattern_engine.py` — Outcome Pattern Engine — Campaign 12.1
- `outcome_tracking_runtime.py` — Outcome Tracking Runtime — measure progress toward goals.
- `outcome_verification.py` — Outcome verification engine — replaces 'Task Complete' with 'Outcome Verified'.
- `packet_router.py` — Packet Router — capability-first work routing.
- `parallel.py` — Parallel agent execution — run multiple agents concurrently.
- `permission_dialogue.py` — Socratic Permission Engine — ask before expanding context access.
- `plan_execution_adapter.py` — Plan Execution Adapter — bridges CompositionPlan to GovernedExecutionSpine.
- `prediction_portfolio_runtime.py` — Prediction Portfolio Runtime — Campaign 13.2
- `presence_runtime.py` — Presence Runtime — operator presence awareness for UMH.
- `priority_engine.py` — Priority Engine — deterministic priority synthesis.
- `product_factory_runtime.py` — C22.5 — Product Factory Runtime.
- `production_merge_verifier.py` — Production Merge Verifier — confirms sandboxed PR became production truth.
- `production_ops_runtime.py` — Production Operations Runtime — Campaign 22.0.
- `production_planning_runtime.py` — C22.1 — Production Planning Runtime.
- `production_review_runtime.py` — C22.3 — Production Review Runtime.
- `production_truth_delta.py` — Production Truth Delta — what actually changed in production after merge.
- `production_workforce_runtime.py` — Production Workforce Runtime — Campaign 22.2.
- `profile_runtime.py` — Profile Runtime — canonical authority for operator work identity and system modes.
- `project_registry.py` — Project Registry — first-class project entities for UMH.
- `projection_certification.py` — Projection certification framework — graduated L0-L5 certification.
- `projection_engine.py` — Projection Engine — predictive world-model layer for UMH.
- `projection_integration_runtime.py` — Projection Integration Runtime — audit/mapping layer over projections.
- `projection_port.py` — Projection-agnostic organism state port.
- `projection_readiness_gate.py` — Projection Readiness Gate — blocks feature build until source reconciliation is sufficient.
- `projection_reconciliation_engine.py` — Projection Reconciliation Engine — diagnoses divergence across projection sources.
- `projection_source_registry.py` — Projection Source Registry — tracks sources per projection for reconciliation.
- `promotion_threshold_policy.py` — Promotion Threshold Policy — governs cadence mode transitions.
- `proof_runtime.py` — Proof Runtime — complete proof packages per execution.
- `proof_store.py` — Proof Store — JSONL persistence for proof packages.
- `propagation_executor.py` — Propagation Executor — executes propagation plans in dry-run or governed mode.
- `propagation_graph.py` — Propagation Graph — dependency-aware change propagation model.
- `propagation_graph_builder.py` — Propagation Graph Builder — extracts nodes and edges from real system state.
- `propagation_planner.py` — Propagation Planner — creates wave-based propagation plans.
- `propagation_wiring.py` — Propagation wiring — registers all propagation targets with the engine.
- `protocols.py` — Organism protocols — typed contracts for the agent society.
- `qualification_harness.py` — Organism Qualification Harness.
- `readiness_model.py` — System Readiness Model — 6-dimension readiness assessment.
- `reality_graph.py` — Reality Graph — canonical operator-world graph for UMH.
- `recommendation_engine.py` — Recommendation Engine — unified action recommendation synthesis.
- `reconciliation_engine.py` — Reconciliation Engine — structured context reconciliation sessions.
- `reconciliation_session.py` — Reconciliation Session — structured operator-AI context alignment.
- `recursion_governance.py` — Recursion Governance — bounded recursive execution control.
- `reliability_signals.py` — Reliability Signal Model — normalizes production-backed signals for cadence ranking.
- `reliability_weighted_ranker.py` — Reliability-Weighted Ranker — deterministic candidate ranking using production signals.
- `report_dispatcher.py` — Report dispatcher — sends task completion reports to Discord + cockpit chat.
- `repository_awareness_runtime.py` — Repository Awareness Runtime — file-level depth for repositories.
- `resource_allocation_runtime.py` — C14.0 — Resource Allocation Runtime.
- `risk_engine.py` — Risk Engine — unified risk register synthesis.
- `roadmap_engine.py` — Roadmap Engine — phase linkage model for self-build queue.
- `role_contracts.py` — Role Contracts + Capability Profiles — template-based role definitions.
- `runtime_adapter.py` — Runtime adapter interface — abstract contract for execution surfaces.
- `runtime_adapters.py` — Concrete RuntimeAdapter implementations for UMH runtimes.
- `runtime_awareness_runtime.py` — Runtime Awareness Runtime — unified view of active system state.
- `runtime_fleet.py` — Runtime fleet model — tracks available runtime providers and selection decisions.
- `runtime_graph.py` — RuntimeGraph — canonical runtime registry with dynamic availability.
- `runtime_handoff.py` — Runtime handoff — bridges Work Packets to runtime sessions.
- `runtime_manager.py` — Runtime manager — orchestrates governed runtime session lifecycle.
- `runtime_session.py` — Runtime session model — governed execution surface for workcell runtimes.
- `runtime_state_registry.py` — Runtime State Registry — live environment awareness for the workstation.
- `runtime_supervisor.py` — RuntimeSupervisor — persistent runtime lifecycle management.
- `sandbox_orchestrator.py` — Sandbox Orchestrator — ties approval gate to PR factory execution.
- `scenario_intelligence_engine.py` — Scenario Intelligence Engine — Campaign 13.1
- `self_build_queue.py` — Self-Build Engineering Queue — canonical work item model and queue engine.
- `self_maintenance_bridge.py` — Self-Regulation Bridge — wires degradation detection to work packet creation.
- `self_model_predictor.py` — PredictiveSelfModel — the organism's statistical self-prediction engine.
- `service_dependency_graph.py` — Service Dependency Graph — canonical service dependency models.
- `service_dependency_registry.py` — Service Dependency Registry — canonical registry of service dependencies.
- `service_failure_engine.py` — Service Failure Engine — computes failure impact across service graph.
- `session_runtime.py` — Session Runtime — canonical session architecture for UMH.
- `shell_runtime_adapter.py` — Shell runtime adapter — safe subprocess execution surface.
- `slo_definitions.py` — Runtime SLO Definitions — concrete operational targets.
- `source_registry.py` — Source Registry — tracks all context sources available to UMH.
- `source_truth_linker.py` — Source Truth Linker — cross-domain edge builder for the Reality Graph.
- `source_truth_runtime.py` — Source Truth Runtime — full organizational lineage (Campaign 22.6 CORE).
- `spine_guard.py` — SpineGuard — enforcement layer for the single-spine mutation doctrine.
- `state_authority_graph.py` — State Authority Graph — canonical state domain authority models.
- `state_coherence_engine.py` — State Coherence Engine — detects state authority coherence across nodes.
- `state_registry.py` — State Registry — canonical registry of state domain authorities.
- `store.py` — Organism store — JSONL persistence for deliverables, messages, agent state.
- `strategic_context_runtime.py` — Strategic Context Runtime — unified executive synthesis facade.
- `strategic_gap_engine.py` — Strategic Gap Engine — compares current reality to target goals, produces gaps,
- `strategic_memory_engine.py` — Strategic Memory Engine — institutional memory with timeline and replay.
- `strategic_planning_engine.py` — Strategic Planning Engine — generate plans linking current reality to goals.
- `strategic_tick_loop.py` — Strategic Tick Loop — continuous governed awareness engine.
- `sync_policy.py` — External Sync Policy — governs how UMH relates to external tools.
- `system_identity.py` — Canonical UMH identity — single source of truth.
- `tailscale_discovery.py` — Tailscale auto-discovery tick — diffs tailscale peers vs device registry.
- `template_governance.py` — Template Governance — 9-dimension scoring engine for template cadence eligibility.
- `template_registry.py` — Template Registry — reusable executable structures from governed execution.
- `template_seeder.py` — Template Seeder — seeds evidence-backed execution templates to the runtime store.
- `tradeoff_intelligence_engine.py` — C14.1 — Tradeoff Intelligence Engine.
- `trajectory_intelligence_runtime.py` — Trajectory Intelligence Runtime — Campaign 13.0
- `trial_runner.py` — Phase 9.3 — Self-Improvement Reliability Campaign Trial Runner.
- `trust_score.py` — Trust Score Engine — composite trust scoring via weakest-link gate.
- `umh_node_registry.py` — UMH Node Registry — canonical registry of UMH organism nodes.
- `umh_node_topology.py` — UMH Node Topology — canonical node role and version models.
- `umh_version_coherence.py` — UMH Version Coherence Engine — detects version drift across nodes.
- `universal_work_queue.py` — Universal Work Queue — canonical queue for all work packets.
- `work_graph.py` — Work Graph — read-only query projection over existing work stores.
- `work_packet.py` — Work Packet — canonical intent-to-execution container.
- `work_packet_engine.py` — Work Packet Engine — creates work packets from user intent.
- `work_portfolio_runtime.py` — Work Portfolio Runtime — execution health, velocity, and drift detection.
- `work_readiness_runtime.py` — Work Readiness Runtime — multi-dimensional readiness classification.
- `work_recovery_runtime.py` — Work Recovery Runtime — maps work states to recovery actions.
- `workcell.py` — Workcell — planning/delegation workcell model for Work Packets.
- `workcell_daemon.py` — WorkcellDaemon — persistent processor for workcell inboxes.
- `workcell_protocol.py` — WorkcellV2 — durable inbox/outbox execution cells.
- `worker_cell.py` — Worker cell — bounded task execution through the existing pipeline.
- `worker_lifecycle.py` — Worker Lifecycle Emitter — structured lifecycle events.
- `worker_registry.py` — Worker Registry — active worker inventory per device.
- `workload_placement_policy.py` — Workload placement policy — selects correct runtime + device for Work Packets.
- `workload_probes.py` — Real Workload Probes — live operational pressure into the organism.
- `workload_runner.py` — Real Workload Runner — governed execution of operational jobs.
- `workspace_awareness.py` — Workspace Awareness Runtime — deterministic active-context detection.
- `workstation_runtime.py` — Workstation Runtime — canonical workstation planning layer (Phase 10).
- `worktree_sandbox.py` — Worktree Sandbox Manager — isolated execution environments for autonomous improvements.
- `world_model.py` — World Model — organism-level self-model of UMH system state.

### substrate/organism/audits/
- `__init__.py` — empty package/namespace marker
- `context_capacity.py` — Audit — Context Capacity.
- `empire_readiness.py` — Audit — Empire Readiness.
- `model_correspondence.py` — Model Correspondence Audit — predicted state vs observed reality.
- `operational_awareness.py` — Audit — Operational Awareness.
- `organism_awareness.py` — Audit — Organism Self-Awareness.
- `source_truth.py` — Audit — Source of Truth (Production Lineage).

### substrate/organism/benchmarks/
- `__init__.py` — empty package/namespace marker
- `autonomous_execution.py` — Autonomous Execution Benchmark — session depth, recovery, and independence.
- `capability_reuse.py` — Benchmark 4 — Capability Reuse (Dual-Track).
- `company_ops.py` — Company Operations Scorer — Benchmark F for C33.
- `competitive.py` — Competitive benchmarking data layer — competitor profiles, market categories, and scoring.
- `composite_scorer.py` — Composite Scorer — aggregate 20 categories into competitive matrix.
- `compounding_proof.py` — Benchmark 7 — Compounding Proof (Integration).
- `efficiency.py` — Efficiency Benchmark — capability per dollar.
- `external_adapters.py` — External benchmark adapter layer — industry-standard benchmarks through UMH.
- `governance_quality.py` — Governance Quality Scorer — Benchmark D for C33.
- `harness_scorer.py` — C29 Harness Superiority — Scoring engine.
- `harness_superiority.py` — C29 Harness Superiority — data model, task registry, result store.
- `human_amplification.py` — Human Amplification Benchmark — does the operator become more capable?
- `mutation_equivalence.py` — Mutation Equivalence Scorer — Benchmark H for C33.
- `operator_compression.py` — Benchmark 5 — Operator Compression.
- `orchestration_quality.py` — Orchestration Quality Scorer — Benchmark C for C33.
- `outcome_accuracy.py` — Outcome Accuracy Benchmark — did completed work achieve original intent?
- `production_outcome_quality.py` — Benchmark 6 — Production Outcome Quality.
- `production_quality.py` — Benchmark 2 — Production Quality.
- `production_velocity.py` — Benchmark 3 — Production Velocity.
- `projection_readiness.py` — Benchmark — Projection Readiness.
- `reality_correspondence.py` — Reality Correspondence Benchmark — 50 failure scenarios across 5 domains.
- `reality_recovery.py` — Benchmark 1 — Reality Recovery.
- `reliability.py` — Reliability Benchmark — consistency across repeated builds.
- `strategic_compression.py` — Strategic Compression Benchmark — high-level intent to executable reality.
- `surface_switching.py` — Surface Switching Cost Tracker — measures continuity across UMH surfaces.

### substrate/organism/executors/
- `__init__.py` — Executor implementations for the UMH Executor Runtime.
- `agent_executor.py` — AgentExecutor — first governed LLM/Claude Code executor (Phase 17A).
- `approval_intercept.py` — Approval Intercepts — runtime human-in-the-loop governance for executors.
- `execution_telemetry.py` — Execution Telemetry — live event pipeline for executor lifecycle.
- `workstation_executor.py` — WorkstationExecutor — first production ExecutorContract implementation.

### substrate/organism/self_use/
- `__init__.py` — Self-use certification — C27 Daily Driver Readiness.
- `certification_report.py` — Certification report — 4-gate pass/fail with coherence override.
- `gap_ledger.py` — Gap ledger — structured log of every friction point, missing capability, and failure.
- `meta_ide_audit.py` — Meta IDE functional audit — manual operator testing of every subsystem.
- `projection_delta.py` — Projection delta engine — desired vs implemented vs certified.
- `task_catalog.py` — Task catalog — load and manage C27 self-use certification tasks.
- `task_taxonomy.py` — Task taxonomy — domain classification for self-use certification.

### substrate/organism/tests/
- `__init__.py` — empty package/namespace marker
- `test_advisor.py` — Tests for advisor — interpret, decompose, delegate, synthesize.
- `test_advisor_coordinator.py` — Tests for advisor → coordinator integration (Phase 2A).
- `test_agent_runtime.py` — tests for agent base runtime — critique loop, deliverable production.
- `test_allocation_loop.py` — Tests for the governed runtime allocation loop.
- `test_approval_store.py` — tests for approval store — JSONL persistence for governance-blocked signals.
- `test_assisted_executor.py` — Tests for the AssistedExecutor — Phase 5.9.
- `test_async_coordinator.py` — Tests for async coordinator execution.
- `test_automation_pipeline.py` — Tests for the AutomationPipeline — Phase 5.9.
- `test_autonomous_tick.py` — Tests for the autonomous tick engine.
- `test_bottleneck_engine.py` — Tests for BottleneckEngine.
- `test_composition_engine.py` — Tests for composition engine.
- `test_contradiction_engine.py` — Tests for contradiction engine.
- `test_coordinator.py` — Tests for OrganismCoordinator — task decomposition, assignment, execution.
- `test_daemon_approvals.py` — tests for daemon approval creation on governance rejection.
- `test_dependency_graph.py` — Tests for organism dependency graph.
- `test_development_session_bridge.py` — Tests for DevelopmentSessionBridge — governed coding agent integration.
- `test_e2e.py` — End-to-end test — the vertical slice acceptance criterion.
- `test_environment_graph.py` — Tests for EnvironmentGraph — operational topology.
- `test_environment_reconciler.py` — Tests for EnvironmentReconciler — drift correction.
- `test_event_spine.py` — Tests for the unified organism event spine.
- `test_execution_modes.py` — Tests for ExecutionModeManager.
- `test_leverage_assimilation.py` — Tests for leverage_assimilation — external framework ingestion and scoring.
- `test_leverage_metrics.py` — Tests for LeverageMetrics engine.
- `test_leverage_rebalance.py` — Tests for continuous leverage rebalancing.
- `test_maintenance_loop.py` — Tests for the MaintenanceLoop — Phase 5.9.
- `test_memory_promotion.py` — Tests for memory promotion pipeline.
- `test_mission.py` — Tests for Mission — user conversation to organism execution bridge.
- `test_objective_physics.py` — Tests for ObjectivePhysics engine.
- `test_objective_queue.py` — Tests for the continuous objective queue.
- `test_operational_intelligence.py` — Tests for Phase 7.0 Operational Intelligence engines.
- `test_operator_compression.py` — Tests for OperatorCompression engine.
- `test_orchestration_integration.py` — Integration tests for Phase 2 organism orchestration.
- `test_orchestration_loop.py` — Tests for orchestration_loop — PersistentLoop stages wired to organism daemon.
- `test_organism_events.py` — tests for organism ViewFrame event broadcasting.
- `test_outcome_learning.py` — Tests for outcome learning loop.
- `test_phase10_template_supply.py` — Phase 10.0 — Template Library, Candidate Supply, and Cockpit Route Extraction tests.
- `test_phase11_1_universal_work.py` — Phase 11.1 — Universal Work Queue + Work Packet Engine tests.
- `test_phase11_self_build_queue.py` — Phase 11.0 — Self-Build Engineering Queue tests.
- `test_phase12_0_propagation_graph.py` — Phase 12.0 — Universal Propagation Graph / Correspondence Layer tests.
- `test_phase13_0_operator_experience.py` — Phase 13.0 — Operator Experience Kernel tests.
- `test_phase13_4m.py` — Phase 13.4M tests — multi-runtime operator acceptance correction.
- `test_phase14_1_source_inspection.py` — Tests for Phase 14.1 — Permissioned Source Inspection Execution.
- `test_phase3.py` — Phase 3 tests — Governed Recursive Execution Economy.
- `test_phase58_integration.py` — Phase 5.8 integration tests — full Operational Leverage Engine.
- `test_phase59_integration.py` — Integration tests for Phase 5.9 — end-to-end workload execution.
- `test_phase61_governed_spine.py` — Tests for Phase 6.1 — GovernedExecutionSpine, ActionEnvelope,
- `test_phase62_spine_enforcement.py` — Tests for Phase 6.2 — Execution Spine Enforcement + SpineGuard Ladder.
- `test_phase63_autonomous_gate.py` — Phase 6.3 — Autonomous Execution Spine Gate tests.
- `test_phase92_self_improvement.py` — Phase 9.2 — Governed Self-Improvement Trial tests.
- `test_phase93_reliability_campaign.py` — Phase 9.3 — Self-Improvement Reliability Campaign tests.
- `test_phase94_coherence_propagation.py` — Phase 9.4 tests — Template Registry, Agent Capability Model, Coherence Propagation.
- `test_phase95_spine_native_propagation.py` — Phase 9.5 tests — Spine-Native Propagation + Template-Guided Improvement Campaign.
- `test_phase9_integration.py` — Tests for Phase 9.0 — World Model → Execution Integration.
- `test_plan_execution_adapter.py` — Tests for plan_execution_adapter — Phase 9.1 Composition→Execution bridge.
- `test_projection_port.py` — Tests for projection-agnostic organism state port.
- `test_projection_reconciliation_engine.py` — Tests for ProjectionReconciliationEngine (Phase 14.0).
- `test_projection_source_registry.py` — Tests for ProjectionSourceRegistry (Phase 14.0).
- `test_protocols.py` — tests for organism protocols — deliverable, agent message, worker spec.
- `test_report_dispatcher.py` — Tests for substrate.organism.report_dispatcher.
- `test_runtime_events.py` — Tests for runtime event bus wiring.
- `test_runtime_graph.py` — Tests for RuntimeGraph — runtime registry, scoring, routing.
- `test_runtime_supervisor.py` — Tests for RuntimeSupervisor — lifecycle management, crash detection, recovery.
- `test_store.py` — tests for organism JSONL store.
- `test_workcell_protocol.py` — Tests for WorkcellV2 — durable inbox/outbox execution cells.
- `test_worker_cell.py` — tests for worker cell — bounded task execution.
- `test_workload_probes.py` — Tests for WorkloadProbes.
- `test_workload_runner.py` — Tests for the WorkloadRunner — Phase 5.9.
- `test_world_model.py` — Tests for organism world model — system self-model.

### substrate/reality_model/
- `__init__.py` — Reality Model — dual Canonical/Instance reality modeling.
- `canonical.py` — Canonical Reality Model — compressed, reusable intelligence.
- `canonical_reality_write.py` — Canonical reality write path — governed entry point for non-execution observations.
- `instance.py` — Instance Reality Model — live operational truth of one user/company/environment.
- `reality_intelligence.py` — Reality Intelligence Engine — read-only retrieval and explanation.
- `reality_mutation.py` — Reality mutation contracts — governed observation writes.
- `reality_query.py` — Reality Query Contract — types for reality interrogation.
- `simulation.py` — Simulation Reality — non-mutating hypothesis testing.

### substrate/sockets/
- `__init__.py` — UMH Socket Layer — typed boundary between substrate and integrations.
- `approval_port.py` — Approval port — substrate-layer abstraction for approval decisions.
- `browser_port.py` — Browser port — substrate-layer abstraction for web access adapters.
- `capability_socket.py` — Capability socket — bidirectional execution for integration capabilities.
- `channel_port.py` — Channel port — substrate-layer abstraction for the channel router.
- `config_port.py` — Config port — substrate-layer abstraction for runtime config access.
- `data_source_port.py` — Data source port — substrate-layer abstraction for external data adapters.
- `envelopes.py` — Envelope dataclasses — the data shapes that cross the socket boundary.
- `intelligence_port.py` — Intelligence port — substrate-layer abstraction for model routing and LLM access.
- `message_port.py` — Message port — substrate-layer abstraction for conversation persistence.
- `notification.py` — Notification socket — substrate-layer abstraction for outbound notifications.
- `notification_engine.py` — Multi-channel notification engine — substrate-layer abstraction.
- `organism_port.py` — Organism port — substrate-layer abstraction for daemon/organism access.
- `outcome_socket.py` — Outcome socket — outbound result notifications to integrations.
- `projection_port.py` — Projection Port — abstract consumption layer for projections.
- `protocols.py` — Protocol definitions for integration-side contracts.
- `registry.py` — Integration registry — central registration and generic adapter bridge.
- `remote_exec_port.py` — Remote execution port — substrate-layer abstraction for SSH and remote ops.
- `sensing_port.py` — Sensing adapter port — substrate-layer abstraction for perception registration.
- `signal_socket.py` — Signal socket — inbound intake for external integrations.
- `tool_adapter_port.py` — Tool adapter port — substrate-layer abstraction for shell/filesystem/git tools.
- `view_socket.py` — View socket — broadcast pipeline state frames to observers.

### substrate/sockets/view/
- `__init__.py` — View socket broadcast infrastructure — sync→async bridge and WebSocket endpoint.
- `broadcaster.py` — Broadcaster — sync→async bridge for ViewFrame delivery.
- `websocket.py` — WebSocket endpoint for broadcasting ViewFrames to cockpit clients.

### substrate/state/
- `__init__.py` — empty package/namespace marker
- `transformation_state_ledger.py` — Transformation State Ledger for the UMH substrate layer.

### substrate/state/business/
- `__init__.py` — empty package/namespace marker
- `business_instance.py` — BusinessInstance — venture-stage context layer.
- `venture_knowledge.py` — classes: Venture, VentureKnowledgeBase; functions: _load_ventures_from_json, get_venture_name

### substrate/state/config/
- `__init__.py` — UMH Config Store — layered configuration with runtime mutability.
- `config_store.py` — ConfigStore — layered JSON-file-backed configuration.
- `settings_persistence.py` — Settings Persistence — flock + atomic write for settings domains.

### substrate/state/context/
- `__init__.py` — empty package/namespace marker
- `context.py` — classes: SubstrateContext; functions: load_ventures_from_env, load_context_from_env, try_load_context_from_env

### substrate/state/finance/
- `__init__.py` — empty package/namespace marker
- `expense_tracker.py` — Expense Tracker — processes receipts from Gmail RECEIPTS-FINANCIALS folder,
- `subscription_tracker.py` — Subscription Tracker — maintains a registry of active

### substrate/state/lifecycle/
- `__init__.py` — empty package/namespace marker
- `stage_manager.py` — StageManager — auto-updates Notion, Discord, and primitives when stage advances.

### substrate/state/logs/
- `__init__.py` — empty package/namespace marker
- `decision_log.py` — DecisionLog — permanent record of important decisions made in conversation.

### substrate/state/memory/
- `__init__.py` — empty package/namespace marker
- `memory.py` — Persistent memory for OS agents — backed by Neon (PostgreSQL).

### substrate/state/memory/contracts/
- `__init__.py` — empty package/namespace marker
- `canonical_memory_query_contracts.py` — Canonical Memory Query contracts for the UMH substrate layer.
- `canonical_memory_reconciliation_engine_v1.py` — Canonical Memory Reconciliation Engine v1.
- `canonical_memory_store_v1.py` — Canonical Memory Store v1 — append-only, replay-safe, queryable memory persistence.
- `memory_conflict_governance_v1.py` — Memory Conflict Governance v1.
- `memory_identity_v1.py` — Memory Identity v1 — deterministic identity model for canonical memories.

### substrate/state/metrics/
- `__init__.py` — empty package/namespace marker
- `founder_rate.py` — Founder Rate — framework for valuing
- `okr_tracker.py` — OKR Tracker — tracks Objectives and Key Results per venture.

### substrate/state/permissions/
- `__init__.py` — empty package/namespace marker
- `os_trinity.py` — OSTrinity — OS Trinity harness layer.

### substrate/state/preferences/
- `__init__.py` — empty package/namespace marker
- `model_preferences.py` — Multi-model router with business context awareness and full human override.

### substrate/state/profiles/
- `__init__.py` — empty package/namespace marker
- `user_model.py` — UserModel — learns how the founder thinks, communicates, and makes decisions.

### substrate/state/providers/
- `__init__.py` — empty package/namespace marker
- `provider_state.py` — Global Provider State + Backpressure + Execution Budget.

### substrate/state/registries/
- `__init__.py` — empty package/namespace marker
- `claude_skill_registry.py` — ClaudeSkillRegistry — tracks all .claude/skills files, syncs them to Neon,
- `skill_registry.py` — classes: Skill, SkillRegistry; functions: get_skill_registry, reset_skill_registry
- `skill_registry_v2.py` — SkillRegistryV2 — first-class skill objects with trust scoring,

### substrate/state/session/
- `__init__.py` — empty package/namespace marker
- `session_state.py` — classes: SessionState

### substrate/state/storage/
- `__init__.py` — empty package/namespace marker
- `db.py` — Neon (PostgreSQL) connection layer for the Python AI layer.

### substrate/state/stores/
- `agent_registry_store.py` — AgentRegistryStore — canonical write API for the agents table.
- `approval_store.py` — ApprovalStore — SQL-backed multi-tenant approval API (deprecated).
- `context_compaction_store.py` — ContextCompactionStore — canonical write API for the context_compactions table.
- `email_folder_store.py` — EmailFolderStore — canonical write API for the email_folders table.
- `embedding_store.py` — EmbeddingStore — canonical write API for the embeddings table.
- `entity_link_store.py` — EntityLinkStore — canonical write API for the entity_links table.
- `entity_store.py` — EntityStore — persistence layer for the entity hierarchy.
- `goal_store.py` — GoalStore — canonical write API for the goals and goal_outcomes tables.
- `higgsfield_store.py` — HiggsFieldStore — canonical write API for the higgsfield_jobs table.
- `permission_store.py` — PermissionStore — canonical write API for cross_product_permissions and product_connections tables.
- `preference_store.py` — PreferenceStore — canonical write API for the model_preferences table.
- `profile_store.py` — ProfileStore — canonical write API for human_profiles, user_profiles, user_intelligence_profiles.
- `skill_store.py` — SkillStore — canonical API for the skills table.
- `task_store.py` — TaskStore — canonical write API for the tasks table.
- `venture_store.py` — VentureStore — canonical write API for the ventures table.

### substrate/state/tenancy/
- `__init__.py` — empty package/namespace marker
- `tenant.py` — Tenant — formal multi-tenant isolation layer for EOS.

### substrate/state/work/
- `__init__.py` — empty package/namespace marker
- `work_state.py` — Work State Detection + Idle Gate + Adaptive Throttling.

### substrate/understanding/
- `__init__.py` — empty package/namespace marker
- `breadth_expansion.py` — Breadth Expansion Engine — step 9 of the 27-step spine.

### substrate/understanding/deliberation/
- `__init__.py` — empty package/namespace marker
- `council.py` — Deliberation Council — 7-role multi-perspective advisory system.

### substrate/understanding/domains/
- `__init__.py` — Domain bridge — maps ontology observations to domain-typed projections.
- `business.py` — Business domain bridge — structural mapping from ontology to business primitives.
- `contract.py` — Domain bridge protocol and projection dataclass.
- `creator.py` — Creator domain bridge — structural mapping from ontology to creator primitives.
- `life.py` — Life domain bridge — structural mapping from ontology to life primitives.
- `registry.py` — Bridge registry — plug-in system for domain bridges.

### substrate/understanding/embedding/
- `__init__.py` — empty package/namespace marker
- `embedder.py` — Lightweight text embedder — shared singleton used by memory.py and
- `embedding_engine.py` — EmbeddingEngine — Three-tier hybrid embedding with graceful degradation.

### substrate/understanding/intelligence/
- `__init__.py` — empty package/namespace marker
- `competitive_intel.py` — Competitive Intelligence — tracks competitor signals
- `human_intelligence.py` — HumanIntelligenceEngine — behavioral profiling for every person the system
- `input_intelligence.py` — Input Intelligence Layer
- `person_recognition.py` — Person Recognition — central module for identifying known people
- `stakeholder_map.py` — Stakeholder Map — tracks key stakeholders per venture,

### substrate/understanding/interpretation/
- `__init__.py` — empty package/namespace marker
- `interpretation_engine_v1.py` — Interpretation Engine v1 for the UMH substrate layer.

### substrate/understanding/knowledge/
- `__init__.py` — empty package/namespace marker
- `knowledge_domains.py` — KnowledgeDomainRegistry — base equilibrium awareness layer.
- `knowledge_graph.py` — KnowledgeGraph — entity relationship layer for EOS.
- `knowledge_integrator.py` — KnowledgeIntegrator — permanent knowledge accumulation layer.
- `knowledge_layers.py` — Knowledge Layer Engine — behavioral distillation layers 6-17.
- `philosophy_lenses.py` — Philosophy Lens Engine — codified lenses from PHILOSOPHY.md Section VII.

### substrate/understanding/ontology/
- `__init__.py` — empty package/namespace marker
- `primitive_decomposition_v1.py` — Primitive Decomposition v1 for the UMH substrate layer.
- `primitives.py` — Primitives — stage-aware business rules and contextual reasoning engine.

### substrate/understanding/patterns/
- `__init__.py` — empty package/namespace marker
- `leverage_patterns.py` — Leverage Pattern Detection — identifies Leverage Killer
- `pattern_engine.py` — PatternEngine — cross-session behavioral pattern detection.

### substrate/understanding/perception/
- `__init__.py` — empty package/namespace marker
- `orchestrator.py` — GenericIngestionOrchestrator — source-agnostic canonical pipeline.
- `source.py` — Source abstraction for the generic ingestion pipeline.

### substrate/understanding/perception/parsers/
- `__init__.py` — Modular parser system for the EOS codebase knowledge graph.
- `base.py` — Shared contracts for all language parsers.
- `config_parser.py` — Config parser — top-level key extraction for JSON/YAML/TOML files.
- `js_parser.py` — JavaScript parser — regex-based symbol + import extraction.
- `python_parser.py` — Python parser — wraps the existing AST scanner in codebase_graph.py.
- `sql_parser.py` — SQL parser — detects tables, views, and FROM references.
- `ts_parser.py` — TypeScript parser — reuses JS regexes and adds interface/type extraction.

### substrate/understanding/reality/
- `__init__.py` — empty package/namespace marker
- `reality_context.py` — RealityContext — ambient present-state snapshot.
- `reality_engine.py` — RealityIntelligenceEngine — continuous market intelligence layer.

### substrate/understanding/research/
- `__init__.py` — empty package/namespace marker
- `research_engine.py` — ResearchEngine — autonomous knowledge gap detection and research layer.

### substrate/understanding/signals/
- `__init__.py` — empty package/namespace marker
- `founder_capture.py` — Founder Capture — detects tasks, ideas, and reminders from Discord messages

### substrate/understanding/world_model/
- `__init__.py` — empty package/namespace marker
- `world_model.py` — WorldModel — two-layer world model for the Meta Harness.

### substrate/understanding/world_pulse/
- `__init__.py` — empty package/namespace marker
- `world_pulse.py` — WorldPulse — continuous market and creator intelligence monitoring.

### substrate/workstation/
- `__init__.py` — Workstation state — profile, session, and resume snapshots.
- `activation.py` — Activation signal and presence session for workstation control.
- `agent_workforce_runtime.py` — Agent Workforce Runtime — Campaign 19.1.
- `ambient_wake_runtime.py` — Ambient Wake Runtime — Campaign 20.2.
- `app_resolver.py` — Native app resolver — Chrome-first browser policy, app vs website classification.
- `attention_aggregation_runtime.py` — Attention Aggregation Runtime — Campaign 18.2.
- `attention_vision_runtime.py` — Attention Vision Runtime — Campaign 21.3.
- `camera_commands.py` — Camera command dispatcher — routes CAMERA_CONTROL intents to operations.
- `checkpoint.py` — Continuity checkpoint — state snapshot on continuity transitions.
- `cockpit_capability_map.py` — Cockpit Capability Map — audit surface for cockpit routes, panels, stores.
- `command_center_mvp_runtime.py` — Command Center MVP Runtime — operator landing surface.
- `command_router.py` — Command router — natural language command classification and routing.
- `continuity.py` — Continuity state machine — unified lifecycle for operator presence/absence.
- `continuity_engine.py` — Continuity engine — orchestrator binding all continuity subsystems.
- `device_presence.py` — Device presence registry for active cockpit sessions.
- `environment_awareness_runtime.py` — Environment Awareness Runtime — Campaign 21.1.
- `execution_fabric_runtime.py` — Execution Fabric Runtime — Campaign 19.0.
- `file_browser.py` — Safe read-only file browser with allowlisted root paths.
- `intent_contract.py` — Intent contract — converts high-level operator intent into end-state designs.
- `jarvis_command.py` — Backward-compat shim — canonical module is command_router.py.
- `lifecycle_modes.py` — Lifecycle modes — system-level cycle that governs safety and background behavior.
- `loop_engine.py` — Loop completion engine — end-state verification and progress reporting.
- `meta_ide_context_runtime.py` — Meta IDE Context Runtime — read-only context binding for the build surface.
- `meta_ide_projection_loop_runtime.py` — Meta IDE Projection Build Loop Runtime — governed build from inside cockpit.
- `mode_commands.py` — Mode switching via natural typed commands.
- `mode_resolver.py` — Workstation mode resolver — authoritative composite of all mode systems.
- `mvp_readiness_runtime.py` — MVP Readiness Runtime — objective MVP readiness scoring across 14 dimensions.
- `operating_loop_runtime.py` — Operating Loop Runtime — visibility layer over existing execution systems.
- `orchestrator_presence_runtime.py` — Orchestrator Presence Runtime — persistent presence layer for the primary orchestrator.
- `overnight_queue.py` — Overnight safe-work queue scaffold — thin MVP for queuing permitted work.
- `profile_behavior.py` — Profile behavior configs — per-profile policies for voice, camera, notifications, apps.
- `profile_modes.py` — Profile/work modes — operator activity context governing workspace/tool/task selection.
- `resume_brief.py` — Return/resume brief generator — answers "what happened while I was gone?"
- `screen_awareness_runtime.py` — Screen Awareness Runtime — Campaign 21.0.
- `security_mode.py` — Security Harden mode — governed security posture for the cockpit.
- `session_machine_runtime.py` — Session Machine Runtime — Campaign 19.2.
- `state.py` — Workstation state — profile, session, and resume state.
- `tracker_stack.py` — Tracker stack — independent, stackable vision trackers.
- `trigger_chains.py` — Trigger chain engine — deterministic event→condition→action chains.
- `unified_approval_runtime.py` — Unified Approval Runtime — single approval queue across all UMH subsystems.
- `unified_execution_surface_runtime.py` — Unified Execution Surface Runtime — single view across all execution subsystems.
- `unified_workstation_runtime.py` — Unified Workstation Runtime — Campaign 18.0.
- `vision_presets.py` — Vision Preset Studio — full CRUD for camera presets.
- `vision_privacy.py` — Vision privacy governance — hard-coded rules for camera usage.
- `vision_query.py` — Vision query handler — grounded visual question answering.
- `vision_scene.py` — Vision scene model — grounded workspace state from camera frames.
- `visual_context_runtime.py` — Visual Context Runtime — Campaign 21.2.
- `visual_operations_runtime.py` — Visual Operations Runtime — Campaign 21.4 (composition root).
- `voice_ingress_runtime.py` — Voice Ingress Runtime — Campaign 20.0.
- `voice_operations_runtime.py` — Voice Operations Runtime — Campaign 20.4 (composition root).
- `voice_output_runtime.py` — Voice Output Runtime — Campaign 20.3.
- `voice_route_resolver.py` — Voice route resolver — separates execution target from audio output device.
- `voice_session_manager.py` — Voice Session Manager — Campaign 20.1.
- `vps_control_catalog.py` — VPS control catalog — governed command execution on the VPS node.
- `work_lane.py` — Work lane model — multi-session lane routing and foreground guard.
- `workstation_presence_runtime.py` — Workstation Presence Runtime — operator footprint across the workstation.

### adapters/ — External System Adapters (100 files)

### adapters/ (root)
- `__init__.py` — package init (empty)
- `protocol.py` — defines the `Adapter` protocol interface that every external system connector must implement (execute, health_check, capabilities)
- `socket_registration.py` — wires concrete adapter implementations into substrate's abstract ports at startup; the ONLY file that bridges adapters → substrate/sockets/

### adapters/adapter_engine/
- `__init__.py` — package init: exports manifest, maturity, lifecycle, and registry for UMH adapters
- `adapter_lifecycle_manager_v1.py` — manages the full lifecycle of adapters (registration, startup, shutdown, health monitoring) in the execution spine
- `adapter_manifest.py` — unified manifest format that describes an adapter's capabilities, requirements, and metadata
- `adapter_maturity.py` — maturity evidence model: tracks how proven/reliable each adapter is based on real usage data
- `adapter_registry_contracts.py` — type contracts (interfaces) that the adapter registry must implement
- `capability_catalog.py` — per-adapter catalog of what each adapter can do (e.g., "read email", "create doc")
- `capability_discovery.py` — discovers and indexes capabilities across all registered adapters automatically
- `cu_api_parity_v1.py` — validates that computer-use (browser automation) adapters match the same API surface as regular adapters
- `google_docs_adapter_v1.py` — Google Docs adapter: reads and writes Google Docs documents through Google API
- `google_drive_adapter_v1.py` — Google Drive adapter: lists, downloads, and uploads files in Google Drive
- `gws_scanner_bridge_v1.py` — translates Google Workspace scanner outputs into the substrate's standard ingestion format
- `live_drive_docs_ingestion_pipeline_v1.py` — real-time pipeline that watches Google Drive/Docs for changes and ingests them automatically
- `modality.py` — defines communication modality types for adapters (text, voice, visual, etc.)
- `participant.py` — classifies participants in adapter interactions (human, agent, system)
- `production_manifests.py` — pre-built manifests for all adapters currently running in production
- `substrate_candidate_gen_v1.py` — generates ingestion candidates from decomposed documents for the knowledge pipeline
- `substrate_decomposer_v1.py` — breaks normalized documents into atomic knowledge primitives using deterministic rules

### adapters/broadcast/
- `__init__.py` — package init (empty)
- `engine.py` — broadcast engine: owns the FFmpeg subprocess lifecycle, converts config to arguments, monitors health
- `ffmpeg_args.py` — pure function that converts a broadcast config object into an FFmpeg command-line argument list
- `filtergraph.py` — builds FFmpeg `-filter_complex` arguments from scene configuration for multi-source video compositing
- `process_lifecycle.py` — generic subprocess lifecycle manager (start, stop, restart, health check) used by the broadcast engine
- `scene_model.py` — data models for broadcast scenes: defines how multiple video/audio sources are composited together
- `zmq_client.py` — ZeroMQ client for sending live parameter changes to a running FFmpeg process without restarting it

### adapters/broadcast/integration/
- `__init__.py` — package init (empty)
- `handlers.py` — broadcast capability handler: implements the standard CapabilityHandler protocol for start/stop/status
- `manifest.py` — declares broadcast capabilities (start, stop, status) in the standard integration manifest format

### adapters/browser/
- `__init__.py` — re-exports browser automation tools from the substrate execution layer (convenience import)

### adapters/browser_auth/
- `__init__.py` — package init (empty)
- `clerk_auth.py` — Clerk authentication adapter: handles the single login flow for all UMH browser automation (email + password → session cookie)
- `sso_chain.py` — SSO chain adapter: follows OAuth redirect chains through GitHub/Google for services that use SSO login

### adapters/browser_exports/
- `__init__.py` — package init: exports all browser export adapters for autonomous data collection from web services
- `chatgpt_export.py` — automates clicking through ChatGPT's UI to trigger a data export download using Playwright
- `claude_export.py` — automates clicking through Claude's UI to trigger a data export download using Playwright
- `contract.py` — data classes defining the shape of export requests and results (what to export, what came back)
- `gmail_export_poller.py` — scans Gmail inbox for export-ready download links after an export is triggered
- `instagram_export.py` — scrapes Instagram saved posts collection using Playwright browser automation
- `instagram_export_parser.py` — classifies and scores Instagram saved posts to identify content worth importing
- `profile_manager.py` — manages persistent browser profiles so exports can reuse authenticated sessions across runs

### adapters/calendar/
- `__init__.py` — package init (empty)
- `meetings.py` — meeting lifecycle management: creates, updates, and tracks meetings across Neon database, Notion, and Discord simultaneously
- `travel_manager.py` — detects travel-related calendar events and builds complete travel briefing documents with logistics

### adapters/data_source_adapters/
- `__init__.py` — package init (empty)
- `conversation_source.py` — wraps parsed conversation data (from ChatGPT/Claude exports) as a standard ingestion source
- `github_source.py` — reads a single file from a cloned GitHub repository as a standard ingestion source
- `gws_source.py` — wraps Google Workspace document scanner output as a standard ingestion source
- `local_file_source.py` — reads a single local file from disk as a standard ingestion source

### adapters/data_source_adapters/parsers/
- `__init__.py` — package init: exports conversation export parsers for the ingestion pipeline
- `chatgpt_parser.py` — parses ChatGPT's JSON export format into structured conversation objects
- `claude_parser.py` — parses Claude's JSON export format into structured conversation objects

### adapters/github/
- `__init__.py` — package init (empty)
- `github_operations.py` — governed write operations for GitHub using the `gh` CLI (create PR, comment, merge) with safety checks

### adapters/google_workspace/
- `__init__.py` — package init (empty)
- `doc_creator.py` — generates briefing docs, board updates, investor updates, and proposals using LLM + Google Drive
- `document_filer.py` — intelligently files incoming email documents into the correct Google Drive folder using LLM classification
- `email_gps.py` — 7-folder email management system: automatically sorts emails into ANTONY/TO_RESPOND/REVIEW/RESPONDED/WAITING_ON/RECEIPTS/NEWSLETTERS
- `gws_connector.py` — Google Workspace integration via `gws` CLI: provides calendar, tasks, drive, and gmail access for agents
- `gws_scanner.py` — reads Google Docs the founder owns, extracts business context using AI, and ingests into knowledge layers with deduplication
- `tasks_adapter.py` — thin wrapper over GWSConnector's task methods for managing Google Tasks

### adapters/models/
- `__init__.py` — package init (empty)
- `agent_runtime.py` — agent execution runtime: routes tasks to Haiku (fast/cheap) or Sonnet (deep/creative) based on task type
- `cc_sdk.py` — Claude Code Agent SDK wrapper: runs queries through the Claude Code CLI subprocess using the host's subscription (free, no API key needed)
- `codex_cli.py` — Codex CLI adapter: wraps OpenAI's `codex exec` for non-interactive agent execution using GPT models
- `hermes_cli.py` — Hermes agent adapter: dispatches to the Hermes binary on Beast via the node mesh for model-agnostic LLM access
- `llm_adapter.py` — LLM adapter: wraps `model_router.call_with_fallback()` as a standard substrate Adapter interface
- `model_router.py` — THE central LLM router: picks the best available AI model for each task and falls back through the provider chain (cc_sdk → Gemini → Groq → Ollama)
- `opencode_cli.py` — OpenCode CLI adapter: wraps `opencode run` for non-interactive agent execution across 75+ LLM providers

### adapters/models/routing/
- `__init__.py` — package init: exports symbolic capability classes and routing config
- `capabilities.py` — defines symbolic capability classes that describe what kind of intelligence a task needs (fast, deep, creative, etc.)
- `config.py` — maps capability classes to specific model_router kwargs (which model to use for which capability)

### adapters/notebooklm/
- `__init__.py` — package init (empty)
- `notebooklm_sync.py` — bidirectional sync between Neon database and Google NotebookLM: pushes reports out, pulls insights back

### adapters/notion/
- `__init__.py` — package init (empty)
- `notion_publisher.py` — canonical Notion writer: publishes morning briefs, reports, summaries, and diagnostics to Notion pages
- `notion_sync.py` — Notion write layer: pushes EOS primitives (ventures, skills, agents) to Notion databases; failures never crash the system

### adapters/notion/integration/
- `__init__.py` — package init: exports manifest, handler, transforms, signals, outcomes for the Notion integration
- `auth.py` — loads Notion API credentials from environment variables
- `correlation.py` — thread-safe in-memory map that tracks which Notion page corresponds to which pipeline outcome
- `handlers.py` — Notion capability handler: implements the standard CapabilityHandler protocol for Notion operations
- `manifest.py` — declares Notion's sockets, signals, capabilities, and signal sources in the integration manifest format
- `outcomes.py` — writes pipeline outcomes (results of processing) back to the originating Notion pages
- `poller.py` — background thread that periodically checks Notion databases for new or changed pages
- `signals.py` — builds SignalEnvelopes from polled Notion pages so they enter the normal processing pipeline
- `transforms.py` — translates between Notion API format and UMH's internal data format
- `watermarks.py` — tracks the last-seen timestamp per database so the poller only fetches new changes

### adapters/scrapling/
- `__init__.py` — package init (empty)
- `scrapling_connector.py` — stealth web fetcher: retrieves public web pages without triggering bot detection for competitor monitoring and market research

### adapters/ssh/
- `__init__.py` — package init (empty)
- `ssh_utils.py` — centralized SSH/SCP utility: single entry point for running remote commands and transferring files between devices

### adapters/tailscale/
- `__init__.py` — package init (empty)
- `tailscale_api.py` — Tailscale Admin API adapter: queries the private mesh network for connected devices and their status

### adapters/tool_adapters/
- `__init__.py` — package init: exports governed access wrappers for filesystem, shell, git, and tmux
- `base.py` — base adapter class with shared deny-rule machinery (blocks dangerous operations like `rm -rf /`)
- `filesystem.py` — governed filesystem adapter: read, write, list, and stat files with safety rules preventing dangerous operations
- `git.py` — governed git adapter: runs git commands with read-only by default and explicit allow-list for write operations
- `shell.py` — governed shell adapter: executes commands with destructive-command blocking (prevents accidental `rm -rf`, `DROP TABLE`, etc.)
- `tmux.py` — governed tmux adapter: inspects tmux sessions but cannot kill them by default

---


### transports/ — I/O Surfaces (195 files)

### transports/ (root)
- `__init__.py` — package init (empty)

### transports/api/ (root files)
- `__init__.py` — package init (empty)
- `_mesh_dispatch.py` — sends engineering plan tasks to a connected Beast node via the mesh HTTP relay for remote execution
- `agent_bridge.py` — stdin/stdout JSON bridge between the TypeScript API and the Python AI layer (agent.run, agent.team, orchestrator.brief)
- `agent_routes.py` — agent executor API routes: submit agent tasks and list past executions
- `app.py` — UMH API server: FastAPI application that registers all route modules and middleware
- `approval_routes.py` — approval intercept endpoints: list, approve, and reject runtime execution intercepts from the cockpit
- `cockpit.py` — main cockpit API router: registers all cockpit_* route modules under /api/umh/ and serves real data to the frontend
- `computer_use.py` — execution substrate API: governed multi-layer agent execution endpoints under /api/umh/execution
- `distribution.py` — distribution API: channel status, intake, approval, and first-boot endpoints
- `event_bus.py` — internal pub/sub backbone: allows substrate components to publish and subscribe to events without direct imports
- `execcoord_routes.py` — execution coordinator routes (Phase 13): extracted from operator loop routes to stay under 3000 lines
- `executor_routes.py` — executor runtime routes (Phase 14): extracted from operator loop routes to stay under 3000 lines
- `governed.py` — governed mutation wrapper: every state-changing API endpoint calls this to enforce governance checks before writing
- `invariants.py` — invariant enforcement: validates substrate laws at every transition point to catch violations early
- `operator.py` — operator workstation API: FastAPI backend for the operator control UI
- `organism_bridge.py` — organism runtime bridge: exposes organism subsystem state and actions to the TypeScript cockpit via stdin/stdout JSON
- `runtime.py` — control plane runtime: top-level orchestrator that wires all substrate subsystems together at startup
- `runtime_state_routes.py` — runtime state routes: read-only endpoints for querying live environment state from the cockpit
- `signal_factory.py` — API signal factory: converts HTTP requests into SignalEnvelopes for the processing pipeline
- `signal_router.py` — signal router: enforces the legal processing pathway that all signals must follow
- `telemetry_routes.py` — execution telemetry routes: live and historical telemetry for executor lifecycle events with SSE streaming
- `voice.py` — voice session API: start/stop voice sessions and manage the voice pipeline over HTTP
- `workstation.py` — workstation API: workstation mode execution, state, and health endpoints

### transports/api/cockpit_* (119 route files — cockpit UI API surface)

Each file provides HTTP endpoints for a specific cockpit feature area, mounted under /api/umh/:

- `cockpit_action_bridge_routes.py` — governed action bridge: catalog, execute, approve, status, history for governed actions
- `cockpit_activity_routes.py` — activity/timeline: unified activity feed combining multiple subsystems
- `cockpit_adapter_status_routes.py` — adapter fleet observability: read-only status of all connected adapters
- `cockpit_agent_fleet_routes.py` — agent fleet coordination: manage and monitor the pool of AI agents
- `cockpit_agent_workforce_routes.py` — agent workforce runtime: manage agent work assignments (Campaign 19.1)
- `cockpit_ambient_wake_routes.py` — ambient wake runtime: background awareness triggers (Campaign 20.2)
- `cockpit_artifact_registry_routes.py` — artifact registry: read-only access to the artifact index (Campaign 6.0)
- `cockpit_attention_routes.py` — attention aggregation: prioritized attention queue for the operator (Campaign 18.2)
- `cockpit_audit.py` — audit event emitter: records all settings and mutation changes to an audit trail
- `cockpit_auth.py` — Clerk JWT validation: verifies cockpit auth tokens against Clerk's public keys
- `cockpit_autonomous_routes.py` — autonomous PR factory and cadence scheduler: auto-generates pull requests on schedule
- `cockpit_broadcast_routes.py` — broadcast control: start/stop/status for live video streaming plus WebSocket health push
- `cockpit_capability_intelligence_routes.py` — capability intelligence: gap analysis, portfolio health, compounding scores (Campaign 10.4)
- `cockpit_capability_map_routes.py` — capability map: snapshot of all capabilities, surfaces, duplications, MVP gaps
- `cockpit_capability_routes.py` — capability tracking: register, list, get, and trace capability lineage
- `cockpit_chat_routes.py` — advisor/DEX chat: conversation endpoints with multimodal file upload (images, video), message history, conversation management
- `cockpit_command_center_mvp_routes.py` — command center MVP: operator landing page with situation summary and attention items
- `cockpit_command_center_routes.py` — command center: agent registry, work packet board, and summary views
- `cockpit_compounding_routes.py` — capability compounding: detect, approve, reject, and promote compounded capabilities
- `cockpit_compute_fabric_routes.py` — compute fabric: unified view of compute resources across all devices
- `cockpit_context_assimilation_routes.py` — context assimilation: source registry, ingestion, diagnostics, and cross-source reconciliation
- `cockpit_context_resolution_routes.py` — context resolution: "system already knows" engine that resolves queries from existing knowledge (Campaign 5.5)
- `cockpit_core_bootstrap_routes.py` — bootstrap routes: initial system setup endpoints extracted from core routes
- `cockpit_core_eos_routes.py` — EOS projection routes: pipeline, KPIs, activity, accountability, intelligence endpoints
- `cockpit_core_feedback_routes.py` — feedback and notifications: feedback stats, skill recommendations, notification management
- `cockpit_core_governance_routes.py` — governance routes: governance tiers, tier checks, and approval queue
- `cockpit_core_routes.py` — core routes: original inline route handlers extracted from cockpit.py to reduce file size
- `cockpit_core_session_routes.py` — session and device routes: Claude Code session bridge, tmux commands, council review, device presence
- `cockpit_delegation_routes.py` — delegation runtime: delegation proposals, missions, queue, and nested orchestration (Campaign 4.7)
- `cockpit_device_routes.py` — device management: scan, diagnose, register, and provision new devices
- `cockpit_distributed_runtime_routes.py` — distributed runtime: organism worker routing across multiple devices
- `cockpit_documentation_awareness_routes.py` — documentation awareness: read-only access to documentation metadata (Campaign 6.2)
- `cockpit_economy_routes.py` — organism economy: recursion, advisor hierarchy, assimilation, workcells, topology, throughput
- `cockpit_embodiment_routes.py` — embodiment: natural language intent surface for the operator
- `cockpit_engineering_review_routes.py` — engineering review: execution sessions and proof review for completed work
- `cockpit_engineering_routes.py` — engineering: autonomous planning and work packetization
- `cockpit_entity_routes.py` — entity management: portfolio, departments, roles, companies CRUD, product connections
- `cockpit_execution_fabric_routes.py` — execution fabric runtime (Campaign 19.0)
- `cockpit_execution_graph_routes.py` — execution graph: record, trace, validate, audit, and replay execution lineage
- `cockpit_execution_loop_routes.py` — execution and loop: persistent execution loops and execution substrate endpoints
- `cockpit_execution_routes.py` — execution: unified API composing all execution subsystems
- `cockpit_executive_routes.py` — executive intelligence (Campaign 14.3)
- `cockpit_goal_routes.py` — goal systems: goal registry, hierarchy, outcome tracking, and strategic planning (Campaign 8.6)
- `cockpit_governance_routes.py` — organism governance (Campaign 15.4)
- `cockpit_infrastructure_routes.py` — infrastructure registry: register, list, get, and trace infrastructure components
- `cockpit_intent_routes.py` — intent preservation: capture, refine, and supersede operator intents
- `cockpit_knowledge_awareness_routes.py` — knowledge awareness: extracted decisions, constraints, conventions, lessons (Campaign 6.4)
- `cockpit_learning_routes.py` — learning intelligence: outcome patterns, capability evolution, learning extraction (Campaign 12.4)
- `cockpit_loop_coherence_routes.py` — loop coherence: coherence detection and scoring for operating loops (Campaign 4.3)
- `cockpit_memory_routes.py` — decision intelligence and strategic memory: decision registry, lineage, assumptions, validity (Campaign 9.6)
- `cockpit_meta_ide_context_routes.py` — Meta IDE context: read-only context binding for the development environment (Campaign 17.1)
- `cockpit_meta_ide_conv_routes.py` — Meta IDE convergence: unified development surface
- `cockpit_meta_ide_critical_routes.py` — Meta IDE critical path: planning, work packets, proof packages, and trust scoring
- `cockpit_meta_ide_projection_loop_routes.py` — Meta IDE projection loop: submit, advance, review, merge, reject build loop items
- `cockpit_meta_ide_routes.py` — Meta IDE: engineering reality awareness
- `cockpit_migration_routes.py` — operator migration: exit tracking and closure for completed migrations
- `cockpit_mvp_readiness_routes.py` — MVP readiness: 14-dimension readiness scoring (Campaign 4.5)
- `cockpit_operating_loop_routes.py` — operating loop: loop tracking, visibility, and lineage (Campaign 4.1)
- `cockpit_operationalization_routes.py` — operationalization: create, list, get, and trace reusable capability artifacts
- `cockpit_operator_experience_routes.py` — operator experience: session management, send, preview, and status
- `cockpit_operator_home_routes.py` — operator home: unified aggregation façade for the operator landing page
- `cockpit_operator_loop_ext_routes.py` — operator loop extensions (Phases 5-8): strategic tick loop and related endpoints
- `cockpit_operator_loop_routes.py` — operator loop: the full intent → plan → implementation → audit lifecycle (Phases 1-3)
- `cockpit_operator_loop_session_routes.py` — operator loop sessions (Phases 9-12): command runtime and related endpoints
- `cockpit_operator_presence_routes.py` — operator presence: presence and continuity tracking via ContinuityEngine
- `cockpit_operator_timeline_routes.py` — operator timeline: unified chronological view merging intents, events, decisions, and work packets
- `cockpit_orchestrator_awareness_routes.py` — orchestrator awareness: synthesized reality model for the orchestrator (Campaign 4.0)
- `cockpit_orchestrator_presence_routes.py` — orchestrator presence (Campaign 17.0)
- `cockpit_organism_map_routes.py` — organism map: unified topology view composing existing data sources
- `cockpit_organism_routes.py` — organism core: status, agents, deliverables, events, tick, metrics, bottlenecks, intelligence
- `cockpit_prediction_routes.py` — prediction intelligence (Campaign 13.3)
- `cockpit_presence_routes.py` — presence activation: Jarvis-style activation, session, command, and capabilities (Phase 14.11D)
- `cockpit_production_routes.py` — production: software production organism surface
- `cockpit_projection_integration_routes.py` — projection integration: profiles, locations, gaps, readiness for projection audit
- `cockpit_projection_routes.py` — projection consumption: read-only audit and registration for projection drift detection (Gate 10)
- `cockpit_proof_inspector_routes.py` — proof inspector: surfaces proof packages, evidence, timeline, and artifacts for operator review (G10 MVP)
- `cockpit_propagation_graph_routes.py` — propagation graph: graph, impact, plan, execute, and results for change propagation
- `cockpit_push_routes.py` — push notifications: VAPID key exchange and subscription management for browser push
- `cockpit_reality_graph_routes.py` — reality graph: operator-world relationship graph (Campaign 5.0)
- `cockpit_reality_intelligence_routes.py` — reality intelligence: read-only reality retrieval endpoints
- `cockpit_reality_model_routes.py` — reality model: canonical patterns, instance observations, and simulation
- `cockpit_recovery_dashboard_routes.py` — recovery dashboard: surfaces failed/blocked/interrupted work items with recovery actions (G11 MVP)
- `cockpit_repository_awareness_routes.py` — repository awareness: file-level repo awareness (Campaign 6.1)
- `cockpit_rooms_routes.py` — conference rooms: servers, categories, channels, messages, threads, forums, roles, members, invites, meetings, voice, DEX, artifacts, audit, search
- `cockpit_runtime_awareness_routes.py` — runtime awareness: live processes, containers, work packets (Campaign 6.3)
- `cockpit_runtime_surface_routes.py` — runtime surface: session lifecycle, events, and adapters
- `cockpit_screen_awareness_routes.py` — screen awareness: operator visual workspace context (Phase 33)
- `cockpit_self_build_routes.py` — self-build queue: summary, items, next, blocked, ready, item detail, status updates, roadmap
- `cockpit_self_improvement_routes.py` — self-improvement loop: outcome assimilation, verification, cadence integration, projection feedback
- `cockpit_service_graph_routes.py` — service graph: read-only service dependency graph and failure impact analysis
- `cockpit_session_machine_routes.py` — session machine runtime (Campaign 19.2)
- `cockpit_session_routes.py` — workstation session: session lifecycle and resume context (Campaign 4.4)
- `cockpit_settings_mutations.py` — settings mutations: single entry point for all settings changes (UI, chat, and voice all route here)
- `cockpit_spine_router.py` — spine router: GovernedExecutionSpine, journal, MutationRegistry, and SpineGuard endpoints
- `cockpit_state_authority_routes.py` — state authority: read-only state domain authority, ownership, and coherence
- `cockpit_strategic_routes.py` — strategic context: executive synthesis layer (Campaign 7.6)
- `cockpit_umh_node_routes.py` — UMH node topology: read-only node topology, service activation, and version info
- `cockpit_unified_approval_routes.py` — unified approval: single approval queue for the cockpit top HUD (Campaign 4.2)
- `cockpit_unified_execution_routes.py` — unified execution: single API across all execution subsystems (active/queued/blocked streams, approvals, completions)
- `cockpit_unified_workstation_routes.py` — unified workstation: the single canonical workstation surface (Campaign 18.0)
- `cockpit_universal_work_routes.py` — universal work queue: packets, workcells, roles, and knowledge
- `cockpit_validation_routes.py` — validation: capability compounding proof and competitive matrix
- `cockpit_visual_attention_routes.py` — attention vision runtime (Campaign 21.3)
- `cockpit_visual_awareness_routes.py` — screen awareness runtime (Campaign 21.0)
- `cockpit_visual_context_routes.py` — visual context runtime (Campaign 21.2)
- `cockpit_visual_environment_routes.py` — environment awareness runtime (Campaign 21.1)
- `cockpit_visual_ops_routes.py` — visual operations runtime (Campaign 21.4)
- `cockpit_voice_ingress_routes.py` — voice ingress runtime (Campaign 20.0)
- `cockpit_voice_ops_routes.py` — voice operations runtime (Campaign 20.4)
- `cockpit_voice_output_routes.py` — voice output runtime (Campaign 20.3)
- `cockpit_voice_routes.py` — voice query: accepts text queries, runs intent classification, returns context-grounded answers (Phase 35)
- `cockpit_voice_session_routes.py` — voice session manager (Campaign 20.1)
- `cockpit_work_center_routes.py` — work center: unified API for governed work lifecycle, all mutations through GovernedWorkRuntime
- `cockpit_work_intelligence_routes.py` — work intelligence: readiness, delegation feasibility, portfolio health (Campaign 11.3)
- `cockpit_workspace_observation_routes.py` — workspace observation: live engineering runtime observation
- `cockpit_workspace_routes.py` — workspace: file browser, diff, test results, logs, proof, and health
- `cockpit_workspace_topology_routes.py` — workspace topology: graph, health, runtimes, repositories (Phase 27)
- `cockpit_workstation_control_routes.py` — workstation control: execution pause/resume/stop with environment awareness
- `cockpit_workstation_presence_routes.py` — workstation presence (Campaign 17.2)

### transports/api/http/ (TypeScript HTTP API layer)
- `drizzle.config.ts` — Drizzle ORM configuration: points to the DB schema and connection string
- `server.ts` — Hono HTTP server: mounts all route modules, applies auth middleware, starts the Node.js server
- `types.ts` — shared Hono Env type: enables typed `c.get('orgId')` / `c.get('userId')` across all routes

### transports/api/http/db/
- `client.ts` — database client: Neon WebSocket connection pool that supports real transactions (not HTTP-only)
- `migrate.ts` — migration runner: enables pgvector + pgcrypto extensions, then applies Drizzle schema migrations
- `schema.ts` — database schema: defines all tables (organizations, users, portfolios, etc.) using Drizzle ORM

### transports/api/http/lib/
- `governed_bridge.ts` — governed mutation bridge: TypeScript equivalent of governed.py, routes all mutations through GovernedExecutionSpine
- `python_bridge.ts` — Python bridge: spawns Python subprocess to call organism runtime functions from TypeScript

### transports/api/http/middleware/
- `auth.ts` — auth middleware: validates Clerk JWT tokens, extracts orgId/userId, sets RLS context on every request
- `operator.ts` — operator middleware: additional authorization checks for operator-level actions

### transports/api/http/routes/
- `chat.ts` — chat routes: operator-to-DEX conversation endpoints (send message, get history)
- `config.ts` — config routes: read and update system configuration with operator guard
- `execution.ts` — execution routes: submit and track governed execution tasks
- `governance.ts` — governance routes: view and manage governance decisions and approvals
- `knowledge.ts` — knowledge routes: query the knowledge graph and memory system
- `organism.ts` — organism routes: organism state, events, and lifecycle management with operator guard
- `settings.ts` — settings routes: read and update system settings with governed mutations
- `system.ts` — system routes: health checks, version info, OS stats, and diagnostics

### transports/api/webhooks/
- `__init__.py` — package init (empty)
- `calendly_webhook.py` — Calendly webhook receiver: processes incoming Calendly scheduling events

### transports/channels/
- `__init__.py` — package init (empty)
- `channel.py` — channel system: base Channel class with concrete implementations for Discord, Telegram, Webhook, and Console channels

### transports/discord/
- `__init__.py` — package init (empty)
- `approval_bridge.py` — approval bridge: sends governance approval requests as Discord messages with interactive Approve/Deny buttons
- `discord_utils.py` — single source of truth for all Discord posting: every module that sends messages to Discord must use this (handles chunking, formatting, rate limits)
- `interface_adapter_v1.py` — Discord interface adapter: minimal bot that bridges Discord commands to the ControlPlaneRouter via WorkPackets
- `signal_factory.py` — Discord signal factory: converts Discord messages (text, voice, image, multimodal) into SignalEnvelopes
- `spine_integration_v1.py` — Discord spine integration: wires Discord commands through the full governed execution spine (command → WorkPacket → Authority → Gate → Dispatch → Worker → Proof → Reply)

### transports/node_mesh/
- `__init__.py` — package init (empty)
- `config.py` — mesh configuration: loads connection settings and manages authentication tokens for mesh nodes
- `metrics_buffer.py` — per-node ring buffer for telemetry metrics: stores recent measurements without going through the full pipeline
- `registry.py` — node registry: tracks all connected mesh nodes, their capabilities, and current state
- `run.py` — standalone launcher for the mesh server: `python3 -m transports.node_mesh.run`
- `server.py` — mesh WebSocket server: manages node connections on port 8094, registers each node as a first-class integration

### transports/node_mesh/integration/
- `__init__.py` — package init (empty)
- `handlers.py` — mesh capability handler: proxies execution requests to remote nodes over WebSocket
- `manifest.py` — builds an IntegrationManifest for each connected mesh node so it looks like any other integration
- `outcomes.py` — mesh outcome receiver: delivers execution results back to remote nodes
- `signals.py` — mesh signal emitter: declares what signal types a remote node can emit
- `types.py` — pure data types for the node mesh (no transport dependencies): node state, capabilities, messages

### transports/presence/
- `__init__.py` — package init (empty)

### transports/presence/handlers/
- `__init__.py` — package init: exports all Discord bot handler modules
- `cc_command_handler.py` — inline command handlers for Discord `!` commands: !followup, !travel, !nomeetings, !confirm_event, !meetingroi, !competitive, !documents, !audit, !stakeholders, etc.
- `intent_handler.py` — intent classification and gateway routing: detects what the user wants from a Discord message and routes it
- `pipeline_handler.py` — pipeline update detection: detects natural language pipeline signals (won/lost/booked) and updates Notion stage
- `report_handlers.py` — backward-compat re-export: all handler implementations now live in reports/ package
- `substrate_command_handler.py` — substrate command handler: intercepts UMH commands (!chrome-proof, !ping, !chrome, etc.) and routes through governed execution
- `voice_handler.py` — voice handler skeleton: voice logic remains in discord_bot.py due to tight coupling with bot instance

### transports/presence/handlers/reports/
- `__init__.py` — package init: re-exports all report handler functions
- `_common.py` — shared imports and helpers used by all report handler modules
- `adapter.py` — generates adapter status reports (which adapters are healthy/unhealthy)
- `capability.py` — generates capability reports (what the system can do and how well)
- `constitution.py` — generates constitution reports (system rules and governance state)
- `continuity.py` — generates continuity reports (session/execution continuity status)
- `economics.py` — generates economics reports (resource usage, cost tracking, efficiency)
- `epistemic.py` — generates epistemic reports (what the system knows and knowledge gaps)
- `federation.py` — generates federation reports (cross-device and cross-node status)
- `governance_intelligence.py` — generates governance intelligence reports (decision quality, approval patterns)
- `identity.py` — generates identity reports (who is this system, what are its roles)
- `orchestration.py` — generates orchestration reports (work coordination, pipeline throughput)
- `resilience.py` — generates resilience reports (failure recovery, redundancy status)
- `strategy.py` — generates strategy reports (strategic alignment, goal progress)
- `telos.py` — generates telos reports (purpose alignment, mission progress)

### transports/cli/ — UMH CLI Transport (7 files)
- `__init__.py` — package marker: UMH CLI — operator terminal interface
- `__main__.py` — allows `python -m transports.cli` invocation: sets sys.path and calls main()
- `client.py` — classes: UMHClient, APIError. Synchronous httpx HTTP client for UMH API. Methods: ping, converse, history, agents, loops, execution_overview, approvals, nodes, providers_health
- `commands.py` — slash command dispatch: handle_command() routes /status, /agents, /loops, /approvals, /nodes, /history, /help, /exit, /clear
- `display.py` — Rich display formatters: render_ai_response (markdown advisor output), render_status (system health table), render_agents, render_loops, render_approvals, render_nodes, render_history, render_help
- `main.py` — entry point: argparse for --url/--api-key/--verbose, prompt_toolkit REPL loop with Rich console. Slash commands go to commands.py, free text goes to client.converse()
- `theme.py` — WorldView design tokens for terminal: UMH_THEME (Rich Theme matching cockpit tokens.css), status_dot() color mapper, RUNTIME_COLORS per-runtime palette, VERSION/BANNER_LINE constants

### projections/ — Projection-Specific Logic (59 files)

### projections/ (root)

- `__init__.py` — package marker; application projections are scoped views of UMH capability.

### projections/creatoros/ — CreatorOS integration

- `__init__.py` — package marker for the CreatorOS projection.
- `integration/__init__.py` — package marker; CreatorOS integration via direct Postgres polling.
- `integration/correlation.py` — thread-safe in-memory correlation map for CreatorOS outcome writeback targeting.
- `integration/handlers.py` — CreatorOS capability handler implementing the `CapabilityHandler` protocol.
- `integration/manifest.py` — declares CreatorOS sockets, signals, capabilities, and config to the substrate.
- `integration/outcomes.py` — writes pipeline outcomes back to CreatorOS Postgres (dual writeback: source row + audit table).
- `integration/signals.py` — builds `SignalEnvelope`s from polled CreatorOS database rows.
- `integration/tables.py` — typed query helpers; the single coupling point between UMH and the CreatorOS schema (all SQL lives here).

### projections/eos/ — EntrepreneurOS projection (department agents, views, workflows)

- `__init__.py` — package marker; EOS uses ONLY the public Substrate API (no internal substrate imports).
- `agents/__init__.py` — package marker; one department agent per ARCHITECTURE.md hierarchy department.
- `agents/base.py` — base department agent with skill execution, permission tiers, and governance integration.
- `agents/ceo.py` — CEO agent (COMMIT tier): strategic decisions, can approve any cross-department action.
- `agents/customer_success.py` — Customer Success agent (EXECUTE tier): retention, satisfaction, support routing.
- `agents/engineering.py` — Engineering agent (EXECUTE tier): technical execution, architecture, deployment.
- `agents/finance.py` — Finance agent (COMMIT tier): revenue, expenses, forecasting (financial actions need approval).
- `agents/hr.py` — HR agent (EXECUTE tier): hiring pipeline, team management, onboarding.
- `agents/legal.py` — Legal agent (COMMIT tier): contract review, compliance, entity management.
- `agents/marketing.py` — Marketing agent (EXECUTE tier): content strategy and brand execution.
- `agents/operations.py` — Operations agent (EXECUTE tier): workflow optimization, process automation, system health.
- `agents/product.py` — Product agent (DRAFT tier): roadmap, feature prioritization, user feedback (no external send).
- `agents/sales.py` — Sales agent (EXECUTE tier): pipeline management and outreach execution.
- `entities.py` — EOS entity hierarchy (User → Portfolio → Company → Department → Role, plus workflows/dashboards) as Pydantic types.
- `integration/__init__.py` — package marker; EOS integration via direct Postgres polling, multi-org.
- `integration/correlation.py` — thread-safe in-memory correlation map for EOS outcome writeback targeting.
- `integration/handlers.py` — EOS capability handler implementing the `CapabilityHandler` protocol.
- `integration/manifest.py` — declares EOS sockets, signals, capabilities, and config to the substrate.
- `integration/outcomes.py` — writes pipeline outcomes back to EOS Postgres (dual writeback: source row + audit table).
- `integration/poller.py` — background thread that polls EOS Postgres tables for new rows.
- `integration/signals.py` — builds `SignalEnvelope`s from polled EOS database rows.
- `integration/tables.py` — typed query helpers; single coupling point between UMH and the EOS Drizzle schema (all SQL here).
- `views/__init__.py` — package marker; EOS views project substrate data into founder-facing dashboards.
- `views/activity.py` — projects recent system activity into a founder-facing feed.
- `views/kpis.py` — projects business metrics into founder-facing KPI cards.
- `views/pipeline.py` — projects CRM/sales data into a founder-facing pipeline.
- `workflows/__init__.py` — package marker; EOS workflows are signal-triggered automated sequences.
- `workflows/browser.py` — governed web scraping/research (wraps ScraplingConnector; dispatches browser evidence to executor nodes).
- `workflows/content.py` — content calendar workflow (ideate → draft → schedule → publish → measure).
- `workflows/daily.py` — governed daily rhythm workflow (morning brief, end-of-day) tracked by the organism.
- `workflows/design.py` — governed design asset management (deterministic now; Figma adapter swaps in later without changing steps).
- `workflows/document.py` — governed document generation (wraps doc_creator so every doc is governed and learned from).
- `workflows/execution.py` — governed task-lifecycle tracking around coding sessions (does not replace Claude Code).
- `workflows/followup.py` — automated follow-up on stale conversations (check → decide → draft → queue).
- `workflows/github.py` — governed PR/branch operations (wraps GitHubOperations adapter through `governed_mutation`).
- `workflows/outreach.py` — automated prospect outreach sequence (qualify → research → draft DM → review → send).
- `workflows/planning.py` — governed strategic planning with outcome tracking (deterministic-first, AI-enhanced options).
- `workflows/research.py` — governed research with outcome tracking (rule-based sourcing, AI-enhanced synthesis).
- `workflows/review.py` — governed code/work review (scope → analyze → findings → report; runs pre-commit gates).
- `workflows/runner.py` — `WorkflowRunner` that executes each workflow step as a governed mutation and emits learning signals.
- `workflows/slack.py` — governed messaging via an outbox JSONL (no Slack adapter yet; queues for later delivery).
- `workflows/types.py` — shared data structures used by `WorkflowRunner` and individual workflows.

### projections/lyfeos/ — LyfeOS integration

- `__init__.py` — package marker for the LyfeOS projection.
- `integration/__init__.py` — package marker; LyfeOS (life optimization platform) integration via direct Postgres polling.
- `integration/correlation.py` — thread-safe in-memory correlation map for LyfeOS outcome writeback targeting.
- `integration/handlers.py` — LyfeOS capability handler implementing the `CapabilityHandler` protocol.
- `integration/manifest.py` — declares LyfeOS sockets, signals, capabilities, and config to the substrate.
- `integration/outcomes.py` — writes pipeline outcomes back to LyfeOS Postgres (dual writeback: source row + audit table).
- `integration/signals.py` — builds `SignalEnvelope`s from polled LyfeOS database rows.
- `integration/tables.py` — typed query helpers; single coupling point between UMH and the LyfeOS schema (all SQL here).

---


### services/ — Service Entrypoints (26 files)


#### services/

- `bridge_health.py` — Bridge Health module
- `browser_adapter.py` — browser_adapter.py — Camoufox browser wrapper for anti-detect automation.
- `browser_relay.py` — Browser relay — streams headless Chromium viewports to cockpit viewers.
- `cc_webhook_receiver.py` — Cc Webhook Receiver module
- `cost_tracker.py` — Functions: load_log() + 3 more
- `discord_bot.py` — Discord Bot module
- `discord_bot_commands.py` — Discord Bot Commands module
- `discord_message_handlers.py` — Discord Message Handlers module
- `export_bridge_handler.py` — Export Bridge Handler module
- `goal_api.py` — Goal API — REST endpoints for goal selection + focus management.
- `heartbeat.py` — EOS Heartbeat Service
- `higgsfield_webhook.py` — Higgsfield Cloud API webhook receiver.
- `icp_scorer.py` — Defines RateLimiter
- `kpi_tracker.py` — Kpi Tracker module
- `local_bridge_client.py` — Local Bridge Client module
- `local_bridge_server.py` — Local Bridge Server module
- `magic_link_handler.py` — Constants/config (defines _REPO_ROOT)
- `magic_link_server.py` — magic_link_server.py — Standalone VPS server for magic-link email interception.
- `oauth_device_flow.py` — Oauth Device Flow module
- `operator_api.py` — Operator Api module
- `overnight_scrape.py` — Overnight Scrape module
- `tier_3_fallback.py` — Tier 3 fallback — stub for future UI-TARS / computer-use integration.
- `trigger_export.py` — Functions: fire_export() + 1 more

#### services/ (shell scripts)

- `local_bridge_send_to_discord.sh` — stop hook for local CC sessions (Windows WSL): reads last assistant message from CC transcript and POSTs to VPS webhook receiver via Tailscale

#### services/auth_flows/

- `__init__.py` — empty package marker
- `chatgpt.py` — scripted login for chatgpt.com: email-based auth flow with adaptive challenge detection (password, verification code, or magic-link)
- `claude.py` — scripted login for claude.ai: email magic-link flow using Gmail poller bridge to intercept magic-link URLs

### nodes/ — Node Management (51 files)

### nodes/ (root)

- `__init__.py` — package marker; distributed execution nodes across Windows/Linux/container environments.

### nodes/distribution/ — work distribution + first-boot handshake

- `__init__.py` — package marker for the task distribution layer.
- `distributor.py` — bridges channels to the execution pipeline (inbound signals, outbound outcomes, approval round-trips).
- `first_boot.py` — detects whether the system needs onboarding by checking for the onboarding result file and critical config.

### nodes/environments/ — Environment Bridge (VPS ↔ local worker packet execution)

- `__init__.py` — package marker for the Environment Bridge modules.
- `bootstrap_plan.py` — generates step-by-step one-time local-worker setup plans.
- `bootstrap_status.py` — checks whether the local worker bridge has been bootstrapped (queues, heartbeat, readiness).
- `chrome_visible_launch.py` — gate that evaluates Chrome launch attempts and records (but does not over-trust) window metadata as evidence.
- `execution_binding_contracts.py` — typed contracts modeling the 6-layer execution stack (environment, surface, etc.).
- `execution_binding_validator.py` — validates that an execution binding has all 6 layers properly bound before execution is allowed.
- `heartbeat.py` — file-based worker liveness heartbeat (worker writes, VPS reads to judge online/stale/offline).
- `local_pull_protocol.py` — pull-based packet execution: the local worker polls a queue, claims, executes, and writes results back.
- `packet_validator.py` — validates work packets before execution (approvals, expiry, blocked actions, governance, proof, bindings).
- `queue_paths.py` — canonical filesystem paths for work-packet queues on VPS and local worker (pure path construction).
- `result_ingestion.py` — validates and ingests result artifacts from local execution (proof, governance, founder confirmation).
- `tmux_surface.py` — models tmux as a persistent local execution environment; builds commands/policies and blocks dangerous ones.
- `vps_local_bridge.py` — orchestrates the VPS↔local worker connection (primary: local pull; fallback: SSH push).
- `w0_packet_builder.py` — builds the W0-001 CU rerun packet with all routing fields and an explicit 6-layer execution binding.
- `windows_desktop_adapter_contracts.py` — typed contracts for GUI actions routed through the Windows Interactive Desktop Adapter.
- `windows_desktop_adapter_validator.py` — validates desktop action requests before they hit the relay inbox.
- `windows_desktop_request_builder.py` — builds typed, validated JSON requests for the Windows desktop adapter relay.
- `work_packet.py` — the governed work-packet contract (approval status, risk, allowed/blocked actions, proof) that flows VPS↔local.
- `workspace_probe.py` — read-only, CPU-gated discovery of active workspace state (tmux sessions, Docker containers, dev previews).

### nodes/windows/ — Windows node daemon + desktop tray

- `__init__.py` — package marker; Windows node daemon service and desktop tray for the UMH mesh.
- `kokoro_server.py` — OpenAI-compatible TTS server running Kokoro 82M locally on the Beast GPU.
- `umh_desktop/__init__.py` — package marker for the desktop tray companion.
- `umh_desktop/tray.py` — system-tray companion (user session, GUI access): desktop, clipboard, and workspace-awareness adapters.
- `umh_node/__init__.py` — package marker for the Windows node daemon.
- `umh_node/adapters/__init__.py` — package marker for the node's capability adapters.
- `umh_node/adapters/broadcast.py` — runs the FFmpeg broadcast engine locally; exposes start/stop/status/scene-switch as mesh capabilities.
- `umh_node/adapters/camera.py` — webcam capture + PTZ control for the Insta360 Link 2 (OpenCV + duvc-ctl), with presets and streaming.
- `umh_node/adapters/clipboard.py` — read/write the system clipboard.
- `umh_node/adapters/container.py` — Docker container lifecycle for sandboxed computer-use agents (Xvfb + x11vnc + noVNC).
- `umh_node/adapters/desktop.py` — GUI automation, window management, and screenshots (runs in the tray, proxied via named pipe).
- `umh_node/adapters/desktop_stream.py` — captures the screen and emits JPEG frames (~30ms/frame at 1080p) on a background thread.
- `umh_node/adapters/filesystem.py` — read, write, list, move, and delete files.
- `umh_node/adapters/hermes.py` — wraps the Hermes CLI on Beast (model-agnostic agent routing to its configured provider).
- `umh_node/adapters/iou_tracker.py` — assigns stable object IDs across frames using Intersection-over-Union matching (stdlib only).
- `umh_node/adapters/object_detector.py` — runs YOLOv8n inference on camera frames and returns normalized bounding boxes.
- `umh_node/adapters/shell.py` — executes shell commands on the local machine.
- `umh_node/adapters/terminal.py` — persistent shell sessions via subprocess pipes.
- `umh_node/adapters/vision_runtime.py` — detects available CV backends and manages tracker processes that emit overlay metadata.
- `umh_node/client.py` — WebSocket client to the VPS node-mesh server (connect → hello → heartbeat → capability exec), control/media planes separated.
- `umh_node/config.py` — node daemon configuration loaded from `umh_node.toml` and `.env`.
- `umh_node/governance.py` — node-side governance validating capability requests against local policy.
- `umh_node/launcher.py` — Session 1 launcher (Task Scheduler ONLOGON) that runs the daemon with interactive desktop access.
- `umh_node/metrics.py` — system metrics collector (CPU, memory, disk, battery, network, GPU).
- `umh_node/peripheral_scanner.py` — enumerates connected peripherals via WMI/PowerShell (cached 60s), with non-Windows stubs.
- `umh_node/service.py` — Windows Service entry point (Session 0, no GUI): owns the WebSocket connection, shell/filesystem adapters, heartbeat.
- `umh_node/subprocess_utils.py` — platform-aware subprocess creation flags so Session 1 calls don't flash visible CMD windows.
- `umh_node/workspace.py` — workspace awareness: tracks the active window and full workstation state (monitors, editor context, browser tabs).

---


### scripts/ — Utility Scripts (146 files)

### scripts/ (root, .py)

- `__init__.py` — empty package marker so `scripts/` can be imported as a Python module.
- `_tme_common.py` — shared helpers for Tool Mastery Engine scripts: skill discovery, YAML frontmatter parsing, canonical paths.
- `agent_task_executor.py` — polls the tasks table for pending AI-agent tasks, runs each through the cognitive loop, reports results to Discord (cron, every 5 min).
- `auto_report_dispatch.py` — Stop hook that auto-posts a work summary to cockpit chat and Discord when a Claude Code session finishes (only if it made commits).
- `bis_context.py` — prints active venture context from `VENTURES_JSON`; used to inject live business data into skill prompts.
- `browser_gate_collector.py` — runs on Beast with a real display to collect 4-layer browser verification evidence across desktop/tablet/mobile viewports.
- `build_notion_databases.py` — one-off script to create the 9 Notion databases that failed in the first build pass.
- `build_notion_workspace.py` — builds the full EOS Notion workspace, mirroring the SaaS UI structure section-for-section.
- `build_palace.py` — generates the memory-palace markdown (palace/wings/rooms) from the codebase graph.
- `build_skill_graph.py` — builds a cross-reference dependency graph between Tool Mastery Engine tool skills.
- `c29_class_b_runner.py` — Playwright automation harness (runs on Beast) that captures real browser evidence for the C29 benchmark, legacy vs. cockpit tracks.
- `c29_run_beast.py` — Beast launcher that injects the Clerk password from 1Password and runs the C29 Class B runner.
- `c29_thesis_run_beast.py` — Beast launcher that injects credentials and runs the C29.5 thesis-validation runner.
- `c29_thesis_runner.py` — five targeted tests exercising the exact UMH differentiators the C29 benchmark is meant to score.
- `calendar_invite_handler.py` — polls for pending calendar invites every 15 min, decides accept/decline, notifies Discord, logs to Notion (cron).
- `call_prep.py` — checks the calendar every 15 min for events 25-45 min out and fires a proactive prep brief to Discord (cron).
- `check_cpu_gate.py` — pre-commit gate blocking raw subprocess usage in substrate/organism code (must use CPU-gated wrappers).
- `check_credential_injection.py` — pre-commit gate blocking plaintext credential patterns (credentials must flow through 1Password).
- `check_dependency_direction.py` — pre-commit gate enforcing the one-way layer dependency direction (projections → transports → adapters → substrate).
- `check_instance_leak.py` — pre-commit gate blocking instance-specific values (names, IDs, hosts) leaking into universal substrate code.
- `check_mesh_relay_firewall.py` — inspects the mesh relay firewall rules for correctness and safety.
- `check_projection_leak.py` — pre-commit gate blocking projection-specific names (EOS, CreatorOS) from appearing in substrate code.
- `check_secret_patterns.py` — pre-commit hook rejecting commits that contain API-key/token/password-looking patterns.
- `check_skill_staleness.py` — audits each tool skill's `last_researched` date against its freshness window and flags stale ones.
- `check_stop_condition.py` — Stop hook that decides whether Claude should keep working or is allowed to stop.
- `check_type_divergence.py` — pre-commit gate blocking new type definitions that collide with the canonical type registry.
- `check_ungoverned_mutations.py` — pre-commit gate ensuring every mutating API handler routes through `governed_mutation()`.
- `codebase_graph.py` — scans the whole codebase via Python AST and builds the persistent codebase knowledge graph (+ Obsidian vault).
- `control_plane_run.py` — reference entry point to run a shell command/script through the Control Plane so it is validated, approved, and logged.
- `create_meetings_db.py` — one-off script that creates the Notion Meetings database.
- `day_reminder.py` — fires Discord reminders for events starting in the next 10-15 min (cron, every 5 min).
- `dead_code_check.py` — checks that every `.py` under `substrate/` is imported somewhere (invariant #9, no dead code).
- `deadline_monitor.py` — checks tasks with approaching/overdue due dates each morning and alerts in Discord.
- `decisions.py` — read-only operator CLI over the Control Plane append-only decision log.
- `deferred.py` — operator CLI to list/show/approve/drop actions in the Control Plane deferred queue.
- `detemplatize_skills.py` — one-off idempotent script that strips hardcoded venture data from skills and replaces it with BIS injection.
- `device_sync.py` — post-commit hook that pushes to GitHub and pulls on Beast to keep both devices in sync.
- `discord_daily_clear.py` — clears/cleans a Discord channel daily as the EOS bot.
- `discord_setup_channels.py` — idempotent setup that ensures the builder/product Discord text channels exist.
- `emit_signal.py` — emits a named orchestrator signal from cron or the shell (prints a JSON line).
- `env_upsert.py` — idempotent `.env` key upsert utility (`KEY=VALUE` add-or-replace).
- `eod_sync.py` — 6pm end-of-day closing loop; posts meetings/expenses/updates/decisions to the morning-brief channel.
- `eos_status.py` — single operator status surface: provider health, Docker services, Ollama state, etc.
- `export_pipeline.py` — autonomous pipeline that polls Gmail for export emails, downloads archives, parses, and ingests into memory.
- `fire_export.py` — fires a single browser export via the Camoufox anti-detect browser (scripted login with MFA branching).
- `generate_codebase_report.py` — produces a single self-contained HTML report documenting the entire mapped codebase for onboarding.
- `generate_vapid_keys.py` — one-off generator of a VAPID key pair for Web Push notifications.
- `github_trinity_ingest.py` — clones and ingests the three core projection repos (EOS, CreatorOS, LYFEOS) via the canonical pipeline.
- `goals.py` — CLI entry points for goal management (wraps `runtime/goal_selector.py`).
- `gws_scanner_cron.py` — thin cron wrapper that runs an incremental Google Workspace document scan and ingests new/changed docs.
- `inbox_gps_afternoon.py` — 3pm inbox pass; posts a report to Discord if anything needs surfacing (cron).
- `inbox_zero_init.py` — run-once four-phase (audit/plan/execute/verify) inbox-zero setup for DEX.
- `incremental_graph.py` — rebuilds only the parts of the codebase graph affected by a small set of changed files (falls back to full rebuild).
- `ingest_conversations.py` — batch-ingests conversation export files into the canonical memory store.
- `ingest_github_repos.py` — batch-ingests GitHub repos into the canonical memory store (all / by category / specific).
- `loop_runner.py` — CLI to start, stop, and query the persistent autonomous loops.
- `measure_phase8_batch.py` — re-runs Phase 8 extraction across all 8 benchmark tools and counts sourced sections.
- `memory_continuous_sync.py` — cron/one-shot that sweeps promoted memories and Claude Code memory files into the canonical store.
- `memory_instant_sync.py` — PostToolUse hook that instantly syncs a written Claude Code memory file to the canonical store (<100ms).
- `memory_watcher_daemon.py` — long-running daemon that watches agent memory directories and syncs new/modified files instantly.
- `merge_graphs.py` — merges the additive `graphify_overlay.json` into the source-of-truth `codebase_graph.json`.
- `meta_ide_browser_gate.py` — 4-layer × 3-pass browser verification gate for the Meta IDE (runs on Beast, WebKit iPhone emulation).
- `midday_checkin.py` — 12:30pm check-in surfacing the afternoon agenda, urgent items, and one priority (cron).
- `migrate_instance_leaks.py` — bulk migration tool that mechanically replaces instance-specific values in substrate code with runtime lookups.
- `morning_intel.py` — 5:45am intelligence brief synthesizing overnight signals/news into a concise Discord post (cron).
- `noshow_detector.py` — flags meetings that started 30+ min ago with no captured outcome as no-shows and triggers recovery (cron, every 15 min).
- `notion_cleanup.py` — archives old scaffold Notion databases and creates per-role dashboard pages.
- `notion_outcome_sync.py` — polls the Notion Pipeline DB for stage changes and logs terminal-stage outcomes into Neon (cron).
- `notion_seed.py` — run-once seeder that populates initial rows in the EOS Notion databases.
- `notion_seed_all.py` — seeds the remaining two ventures (Empyrean Creative, Personal Brand) plus content calendars.
- `notion_setup.py` — creates the full per-venture primitive database architecture in Notion (Goals, Tasks, Meetings, etc.).
- `notion_sync_poller.py` — pushes new Neon tasks to Notion and pulls Notion status changes back to Neon (cron, every 15 min).
- `notion_tasks_sync.py` — syncs the three venture Tasks databases into the Neon events table for the morning brief (cron).
- `oauth_grant_gmail.py` — run-once (on Windows) OAuth consent flow that grants the Gmail scope and saves credentials.
- `orchestrator.py` — continuous autonomous execution layer above the workflow engine; four cooperating internal agents (scheduler, event, etc.).
- `orchestrator_loop.py` — runner for the orchestrator: one cycle, N cycles, or forever.
- `orchestrator_status.py` — operator-friendly snapshot of the Control Plane (pending signals, deferred queue, recent workflows).
- `organism_mutation_cli.py` — command-line surface for the organism's governed mutation pipeline.
- `permission_notify.py` — PermissionRequest hook that sends a channel-agnostic permission notification via the ChannelRouter.
- `phase75a_classifier.py` — auto-classifies UMH modules by PRD domain and MVP status (Phase 75A).
- `phase75a_dep_scanner.py` — AST-based dependency scanner for `umh.*` modules: import graph, cycles, high fan-in/out (Phase 75A).
- `portfolio_brief.py` — Sunday 6am portfolio brief: scans ventures, finds the binding constraint, posts to Discord + Notion (cron).
- `post_meeting_capture.py` — polls for recently ended calendar events and prompts DEX in Discord to capture outcomes (cron, every 15 min).
- `pre_tool_use_log.py` — PreToolUse hook that logs every tool call before execution (can also block).
- `query_graph.py` — retrieval CLI over the codebase knowledge graph (deps, dependents, path, search) — use before grepping.
- `query_skills.py` — CLI registry queries over the Tool Mastery Engine tool skill base.
- `refresh_fly_token.py` — refreshes the Fly.io deploy token (macaroon) from the long-lived org token in 1Password.
- `relationship_nurture.py` — surfaces contacts not heard from in 30+ days (weekly, Mondays 7am).
- `rotate_jsonl.py` — nightly rotation of oversized JSONL stores (renames to `.old`, creates a fresh empty file).
- `router_claude_runtime_debug.py` — prints the live state the model router sees for the Claude CLI backend (debug helper).
- `run_continuity_validation.py` — end-to-end validation of the substrate continuity pipeline (ingestion → snapshot → resume → briefing).
- `run_graphify.py` — Graphify enrichment adapter; produces the additive `graphify_overlay.json` (never touches the primary graph).
- `run_m1_operator_mvp_check.py` — verifies the M1 Operator MVP closure gates (Proof Inspector, Recovery Dashboard) are wired end-to-end.
- `run_qualification.py` — adaptive, convergence-driven qualification runner producing a 3-dimensional (ORL/confidence/accuracy) report.
- `run_reconciliation_ingestion.py` — runs multi-document ingestion with reconciliation and persists artifacts/receipts.
- `run_reconciliation_query_validation.py` — validates that reconciled memories are queryable, provenanced, and correctly reconciled.
- `run_reconciliation_replay_validation.py` — proves re-running the pipeline on the same documents yields identical reconciliation decisions.
- `seed_eos_watermarks_to_now.py` — seeds EOS poller watermarks to now so the next start skips historical replay.
- `send_to_builder.py` — sends a file to the EOS Discord builder channel.
- `session_bootstrap.py` — mandatory session-start context loader (cloud.md, palace index, graph rules, retrieval rules); exits non-zero if graph is stale.
- `session_start_context.py` — SessionStart hook that injects dynamic context into every Claude Code session.
- `shim_retirement_monitor.py` — scans logs/runtime for any lingering `eos_ai` shim usage during the pre-removal monitoring window.
- `subagent_start_context.py` — SubagentStart hook that injects agent-type-specific context when a native subagent starts.
- `substrate_audio_loop_cli.py` — bounded operator CLI for the local audio loop (report, inject transcripts, per-node snapshots).
- `substrate_claude_session_cli.py` — operator CLI for persistent Claude Code tmux sessions on the VPS or local node.
- `substrate_discord_voice_transport_cli.py` — bounded operator CLI to the Discord voice transport adapter (status/start).
- `substrate_execution_trace_cli.py` — operator CLI for execution trace history (latest, show, compact, summary).
- `substrate_local_listener.py` — tiny CLI to emit a bounded activation trigger (e.g. start an open-day ritual on a node).
- `substrate_operator_cli.py` — deterministic human query + controlled-command surface over the linkage snapshot.
- `substrate_voice_session_cli.py` — bounded operator CLI for voice sessions (start, say, switch role).
- `substrate_wake_producer_cli.py` — CLI to simulate wake-word/clap events and view their history.
- `summarize_nodes.py` — appends one-line summaries for every graph node (append-only, never overwrites raw docstrings).
- `sync_skills_to_neon.py` — scans local tool skills and upserts their metadata + content into the Neon `skills` table.
- `tme_quality_audit.py` — audits tool skills for content depth (frontmatter, sections, code examples, sources), not just structure.
- `tme_staleness_sweep.py` — summary-first staleness report for the Tool Mastery Engine (for hooks/cron).
- `tool_mastery_author.py` — thin dispatcher that runs the Tool Mastery Author Agent against a research artifact.
- `tool_mastery_manager.py` — CLI wrapper over the `core.tool_mastery_manager` package (source of truth is the package).
- `tool_mastery_research_dispatcher.py` — Control Plane target that runs research/refresh/repair work for a given tool.
- `user_prompt_capture.py` — UserPromptSubmit hook that captures user messages into conversation log files.
- `validate_w0_coherence_dry.py` — generates and validates the W0-001 packet through every gate without executing anything (dry run).
- `verify_completion_claim.py` — Stop hook that checks completion claims (100%, exhaustive, done) against filesystem ground truth.
- `verify_deploy.py` — standalone post-deploy verification (health path, expected values in HTML); exit code signals pass/fail.
- `verify_knowledge_system.py` — acceptance check that every cognition-stack layer is present, fresh, and queryable.
- `verify_pr47_cadence_learning.py` — verifies cadence post-production learning behavior for PR #47 (Phase 10.3F).
- `verify_pr47_production.py` — production merge verification chain for PR #47 (Phase 10.3D).
- `verify_pr47_reliability.py` — proves a successful outcome updates template confidence, agent reliability, and learning records (Phase 10.3E).
- `verify_template_store.py` — verifies the runtime template store is populated and valid.
- `verify_tool_skill.py` — YAML-aware verifier/linter for tool skills (replaces brittle regex checks).
- `waiting_on_checker.py` — surfaces WAITING_ON emails older than 48h in Discord each morning (cron).
- `watch_graph.py` — near-real-time file watcher that triggers incremental codebase-graph updates as files change.
- `week_architect.py` — Sunday 8pm review of the coming week; flags gaps/conflicts and suggests structure (cron).
- `weekly_review.py` — Sunday 7pm business review: portfolio health, open items, DEX synthesis, posts to #general (cron).
- `wiki_stop_hook.py` — Stop hook that captures assistant conversation content into the session file (pairs with `user_prompt_capture.py`).

### scripts/ (root, .sh)

- `backup.sh` — daily 6am backup of all critical local files into a dated archive.
- `cpu-watchdog.sh` — last-resort CPU defense; runs every 30s via systemd timer and takes progressive action when load per core is too high.
- `healthcheck.sh` — pings the UMH API health endpoint on a given port/host.
- `install-cpu-watchdog.sh` — installs the CPU watchdog as a systemd timer.
- `install_divergence_gate.sh` — installs the type-divergence pre-commit hook (merges with any existing pre-commit).
- `install_graph_hooks.sh` — wires the pre-commit + post-merge codebase-graph hooks into `.git/hooks` (backs up existing).
- `install_hooks.sh` — installs the UMH pre-commit hooks after a fresh clone.
- `install_sync_automation.sh` — installs the sync-ritual automation (git hook + cron), with a `--check` verify mode.
- `invariant_check.sh` — runs the 10 substrate-unification invariant checks; exits 1 on any failure.
- `migrate_module.sh` — Phase C helper to migrate a module to a target architecture layer/subpath.
- `obsidian_rsync.sh` — syncs the Obsidian vault from the Windows machine over Tailscale (with `--dry`).
- `rotate_secrets.sh` — automated 30-day secret rotation; rotates self-generated secrets, flags provider-managed ones, reports to Discord.
- `run_prod.sh` — production runner: starts the API server with worker auto-start and restart-on-crash.
- `run_ui.sh` — starts the UMH Control Plane with UI on a given port.
- `sovereignty-grep.sh` — canonical grep for external-name attribution that should have been renamed during sovereignty cleanup.
- `substrate_operator_tick.sh` — smallest safe drain+reconcile cycle for the local workstation loop (cron-safe).
- `sync_all.sh` — cross-device git sync check and fast-forward (read-only report by default).
- `test_bridge_lifecycle.sh` — chaos test for Windows bridge auto-recovery (kills the bridge, triggers an export, checks recovery).
- `test_code_view_e2e.sh` — E2E test for the operator-UI Code View backend (`/api/code` endpoints).
- `verify_relay_end_to_end.sh` — end-to-end verification of the Windows relay path (requires WSL + Tailscale up).

### scripts/ (root, other)

- `userscript_meet_captions.example.js` — reference example of a browser userscript for Google Meet captions (not active code — operator wires their own endpoint)

### scripts/c40b_phases/ — C40B runtime certification campaign

- `__init__.py` — package marker for the C40B phase modules.
- `campaign_context.py` — shared campaign state passed across all C40B phases.
- `embodiment_harness.py` — 4-dimensional runtime qualification harness (organism, runtime, projection, operator).
- `phase1_runtime_audit.py` — measures every runtime boundary in the mesh dispatch chain (latency, retries, failures).
- `phase2_runtime_fix.py` — reads Phase 1 defects, logs diagnoses, and re-verifies fixes (no-op if none found).
- `phase3_operator_qualification.py` — runs 25 operator scenarios × 10 = 250 real end-to-end executions with evidence.
- `phase4_embodied_stress.py` — sustained operator load test measuring runtime SLOs continuously.
- `phase5_runtime_certification.py` — 4-dimensional certification + production-readiness gate.
- `report_generator.py` — assembles the C40B campaign report and dispatches it to Discord.

### scripts/scheduled/ — cron-scheduled rituals (Control Plane wrappers + bash)

- `morning_prep_cp.py` — Control Plane wrapper that runs `morning_prep.sh` as a governed `run_script` action.
- `nightly_consolidation_cp.py` — Control Plane wrapper for `nightly_consolidation.sh`.
- `weekly_review_cp.py` — Control Plane wrapper for `weekly_review.sh`.
- `morning_prep.sh` — 5:30am readiness check that verifies the system is ready before the day starts.
- `nightly_consolidation.sh` — nightly memory pipeline (summarize conversations → promote to wiki), flock-guarded.
- `nightly_maintenance.sh` — 2am maintenance run via `claude -p` on the private VPS.
- `weekly_review.sh` — Sunday 6am full health audit + Discord report.

### scripts/workers/ — background queue workers

- `discord_approval_worker.py` — tails the Control Plane notifications JSONL and posts deferred-action announcements to Discord.

### scripts/auth_monitor/ — Claude Code credential/session keep-alive (bash)

- `cc_keepalive.sh` — every 6h, nudges active CC tmux sessions to refresh the OAuth token before its 8h TTL expires.
- `credential_coordinator.sh` — single source of truth for CC credentials; watches for refreshes and distributes to isolated session dirs.
- `credential_watcher.sh` — watches `~/.claude/.credentials.json` for any change and logs it.
- `health_check.sh` — every 5 min, validates CC auth state across master + all isolated session credential files.
- `session_resurrector.sh` — checks CC tmux session health and alerts the operator if a session is dead (no auto-restart).
- `setup_isolation.sh` — creates per-session `CLAUDE_CONFIG_DIR` dirs that symlink everything except an independent credentials copy.
- `start_session.sh` — starts a CC session with isolated credentials.

---


### tests/ — Test Suite (377 files)


#### tests/

- `__init__.py` — Package init
- `conftest.py` — Functions: pytest_ignore_collect
- `phase13_2_runtime_proofs.py` — Phase13 2 Proofs runtime
- `test_actuator_bridge.py` — Defines TestActuatorToAdapterMapping + 3 more
- `test_agent_executor.py` — Tests for agent_executor
- `test_agent_fleet_runtime.py` — Defines MockAgentType + 6 more
- `test_agent_workforce_runtime.py` — Tests for AgentWorkforceRuntime — Campaign 19.1.
- `test_approval_intercepts.py` — Defines TestRequestCreation + 1 more
- `test_artifact_registry.py` — Tests for Campaign 6.0 — Artifact Registry.
- `test_assumption_tracking_runtime.py` — Tests for Campaign 9.2 — Assumption Tracking Runtime.
- `test_attention_aggregation_runtime.py` — Tests for AttentionAggregationRuntime — Campaign 18.2.
- `test_authority_tier.py` — Tests for authority_tier
- `test_browser_wiring.py` — Defines TestBrowserTierMapping + 3 more
- `test_c16_integration.py` — Defines _FakeReadiness + 7 more
- `test_c18_integration.py` — Defines _Snap + 11 more
- `test_c19_integration.py` — Tests for c19_integration
- `test_c20_0_voice_ingress.py` — Tests for Campaign 20.0 — Voice Ingress Runtime.
- `test_c20_1_voice_session_manager.py` — Tests for Campaign 20.1 — Voice Session Manager.
- `test_c20_2_ambient_wake.py` — Tests for c20_2_ambient_wake
- `test_c20_3_voice_output.py` — Defines TestVoiceOutputTargetEnum + 3 more
- `test_c20_4_voice_operations.py` — Tests for c20_4_voice_operations
- `test_c20_integration.py` — TestC20Imports: All C20 runtimes, types, and routes must be importable.
- `test_c21_0_screen_awareness_runtime.py` — Tests for ScreenAwarenessRuntime — Campaign 21.0.
- `test_c21_1_environment_awareness.py` — Defines MockPresenceRuntime + 5 more
- `test_c21_2_visual_context.py` — Tests for C21.2 — Visual Context Runtime.
- `test_c21_3_attention_vision.py` — Tests for AttentionVisionRuntime — Campaign 21.3.
- `test_c21_4_visual_operations.py` — Tests for VisualOperationsRuntime — Campaign 21.4.
- `test_c21_integration.py` — Tests for c21_integration
- `test_c22_acceptance.py` — Tests for c22_acceptance
- `test_c22_capability_compounding.py` — Tests for c22_capability_compounding
- `test_c22_product_factory.py` — Tests for c22_product_factory
- `test_c22_production_ops_runtime.py` — Tests for C22.0 — Production Operations Runtime.
- `test_c22_production_planning.py` — Tests for C22.1 — Production Planning Runtime.
- `test_c22_production_review.py` — Tests for C22.3 — Production Review Runtime.
- `test_c22_production_routes.py` — Tests for C22.7 — Production Surface Routes.
- `test_c22_production_workforce.py` — Defines FakeFleetAssignment + 8 more
- `test_c22_source_truth.py` — Tests for C22.6 — Source Truth Runtime (CORE DELIVERABLE).
- `test_c23a_benchmarks.py` — Tests for c23a_benchmarks
- `test_c23a_capability_reuse.py` — Defines TestReusableCapability + 2 more
- `test_c23a_capability_validation_runtime.py` — Tests for c23a_capability_validation_runtime
- `test_c23a_compounding_proof.py` — Tests for Compounding Proof Benchmark — C23A Phase 8.
- `test_c23a_operator_compression.py` — Tests for c23a_operator_compression
- `test_c23a_production_outcome_quality.py` — Tests for c23a_production_outcome_quality
- `test_c23a_production_quality.py` — Tests for c23a_production_quality
- `test_c23a_production_velocity.py` — Tests for Benchmark 3 — Production Velocity.
- `test_c23a_projection_readiness.py` — Defines TestProjectionRequirements + 4 more
- `test_c23a_reality_recovery.py` — Defines TestQuestionGeneration + 1 more
- `test_c23b_competitive.py` — Tests for c23b_competitive
- `test_c23b_composite_scorer.py` — Tests for c23b_composite_scorer
- `test_c23b_external_adapters.py` — Tests for c23b_external_adapters
- `test_c23b_organism_audits.py` — Tests — Campaign 23B organism audits (Tier 3).
- `test_c23b_production_benchmarks.py` — Defines TestAutonomousExecution + 1 more
- `test_c23b_strategic_metrics.py` — Tests for c23b_strategic_metrics
- `test_c31_phase6.py` — Defines TestDevSessionTracker
- `test_c31_phase7.py` — Tests for c31_phase7
- `test_c31_spine_learning.py` — Tests for c31_spine_learning
- `test_c32_benchmark.py` — Defines TestBenchmarkHarness
- `test_c32_cycle1_legacy.py` — Defines TestReliabilityHistory
- `test_c32_cycles.py` — C32 Benchmark Cycle Tests — Cycles 2-5.
- `test_c32_pipeline_b.py` — TestDevSessionToSpine: DevSessionTracker → ActionEnvelope → GovernedExecutionSpine.
- `test_c33_benchmarks.py` — Tests for c33_benchmarks
- `test_c33_phase0.py` — Tests for c33_phase0
- `test_c33_phase1.py` — C33 Phase 1 exit gate tests — verify benchmark infrastructure works.
- `test_c34_mutation_router.py` — Defines TestRegistryExtensions + 1 more
- `test_c35_qualification.py` — C35 Organism Qualification Tests.
- `test_c36_qualification.py` — Defines TestConfidenceEstimate + 2 more
- `test_c37_self_model_predictor.py` — Defines TestWelfordAccumulator + 5 more
- `test_c38_predictive_optimization.py` — C38 Qualification-Driven Optimization Tests.
- `test_c39_live_simulation.py` — Defines TestMutationSubmission
- `test_c40a_runtime_convergence.py` — C40A — Surface Runtime Convergence Tests.
- `test_c40b_embodiment.py` — Tests for c40b_embodiment
- `test_canonical_memory_reconciliation_v1.py` — Tests for canonical_memory_reconciliation_v1
- `test_capability_catalog_slice_a.py` — Tests for capability_catalog_slice_a
- `test_capability_evolution_engine.py` — Tests for CapabilityEvolutionEngine — Campaign 12.2.
- `test_capability_extraction_slice_b.py` — Defines TestValidJsonParse + 3 more
- `test_capability_gap_engine.py` — Campaign 10.1 — Capability Gap Engine tests.
- `test_capability_graph_engine.py` — Tests for capability_graph_engine
- `test_capability_intelligence_integration.py` — Tests for capability_intelligence_integration
- `test_capability_portfolio_runtime.py` — Campaign 10.2 — Capability Portfolio Runtime tests.
- `test_cockpit_capability_map.py` — Tests for cockpit_capability_map
- `test_cockpit_endpoints.py` — Tests for cockpit API additions: activity stream, governance controls, DEX channel.
- `test_command_center_mvp_runtime.py` — Defines MockSnapshotRuntime + 12 more
- `test_command_runtime.py` — Tests for Phase 9 — Command Runtime.
- `test_compute_fabric_runtime.py` — Tests for compute_fabric_runtime
- `test_conference_rooms.py` — Tests for Conference Rooms — servers, categories, channels, messages, threads,
- `test_context_assembler.py` — Defines TestContextAssembler
- `test_context_resolution.py` — Tests for context_resolution
- `test_context_resolution_v2.py` — Tests for context_resolution_v2
- `test_continuity_runtime.py` — Tests for continuity_runtime
- `test_convergence_acceptance.py` — End-to-end acceptance tests for the converged UMH substrate.
- `test_correspondence_ledger.py` — Defines MockCertification + 4 more
- `test_daemon_e2e.py` — Functions: make_server() + 1 more
- `test_decision_impact_engine.py` — Defines MockDecisionRegistry + 5 more
- `test_decision_lineage_engine.py` — Tests for Campaign 9.1 — Decision Lineage Engine.
- `test_decision_registry.py` — Tests for decision_registry
- `test_decision_validity_engine.py` — Tests for decision_validity_engine
- `test_decomposer_depth.py` — Tests for decomposer_depth
- `test_delegation_readiness_runtime.py` — Tests for DelegationReadinessRuntime — Campaign 11.1.
- `test_delegation_runtime.py` — Tests for delegation_runtime
- `test_deploy_verification_worker.py` — Defines TestDeployVerificationTypes + 1 more
- `test_device_awareness.py` — Tests for Device Awareness Runtime — Campaign 5.3.
- `test_device_presence.py` — Tests for substrate/workstation/device_presence.py.
- `test_discord_hot_path_smoke.py` — Defines TestDiscordBotImports + 8 more
- `test_documentation_awareness.py` — Tests for Campaign 6.2 — Documentation Awareness Runtime.
- `test_domain_bridge.py` — Tests for domain_bridge
- `test_domain_bridge_life_creator.py` — Tests for life and creator domain bridges.
- `test_domain_stores_tier3.py` — Functions: test_entity_link_store_import() + 17 more
- `test_drift_detection_engine.py` — Tests for drift_detection_engine
- `test_embodiment_runtime.py` — Tests for W4 — Embodiment Runtime.
- `test_empire_engine.py` — TestDomainRegistry: Requirement 1: first-class domain definitions.
- `test_entity_link_store.py` — Structural tests for EntityLinkStore.
- `test_eos_projection.py` — Tests for EOS projection entry point.
- `test_execution_authority_engine_v1.py` — Tests for execution_authority_engine_v1
- `test_execution_coordinator.py` — Tests for execution_coordinator
- `test_execution_fabric_runtime.py` — Tests for execution_fabric_runtime
- `test_execution_lifecycle_runtime.py` — Defines TestLifecycleStageEnum + 7 more
- `test_execution_telemetry.py` — Tests for execution_telemetry
- `test_executive_brief_runtime.py` — Campaign 7.5 — Executive Brief Runtime tests.
- `test_executive_portfolio_runtime.py` — Defines FakeResourceAllocation + 14 more
- `test_executive_routes.py` — Tests for cockpit executive routes — Campaign 14.3.
- `test_executor_runtime.py` — Defines TestExecutorLifecycleStatus + 7 more
- `test_feedback_capture.py` — Defines TestFeedbackCapture
- `test_gap_closures.py` — Tests for the 3 final gap closures: companies endpoint, skill allocation, ingestion facade.
- `test_gate10_projection_consumption.py` — Defines TestTypes + 2 more
- `test_gate3_governed_work_runtime.py` — Tests for gate3_governed_work_runtime
- `test_gate4_intent_runtime.py` — Tests for Gate 4 — IntentRuntime (Workstation Convergence).
- `test_gate4_workstation_convergence.py` — Tests for gate4_workstation_convergence
- `test_gate5_capability_runtime.py` — Defines TestTypes + 1 more
- `test_gate6_operationalization_runtime.py` — Tests for gate6_operationalization_runtime
- `test_gate7_infrastructure_runtime.py` — Tests for Gate 7 — Infrastructure Runtime.
- `test_gate8_execution_graph.py` — Tests for gate8_execution_graph
- `test_gate9_compounding_engine.py` — Defines TestTypes + 1 more
- `test_generic_ingestion_orchestrator.py` — Defines TestLocalFileSource + 1 more
- `test_goal_alignment_engine.py` — Tests for GoalAlignmentEngine — Campaign 8.4.
- `test_goal_drift_engine.py` — FakeOutcomeTracking: Controllable OutcomeTrackingRuntime stand-in.
- `test_goal_hierarchy_engine.py` — Defines TestHierarchyNoRegistry + 3 more
- `test_governance_full.py` — Tests for governance_full
- `test_governance_routes.py` — Defines TestRouteImports + 2 more
- `test_governance_runtime.py` — Defines TestEnums + 2 more
- `test_governed_execution_runtime.py` — Tests for governed_execution_runtime
- `test_grounding_firewall.py` — Tests for Phase 14.14C — Grounding Firewall + Hermes + Vision.
- `test_gws_source.py` — Tests for GWSSource — Google Workspace ingestion source adapter.
- `test_gws_to_canonical_ingestion_v1.py` — Tests for GWS-to-canonical-substrate ingestion pipeline.
- `test_harness_scorer.py` — Tests for harness_scorer
- `test_harness_superiority.py` — Defines TestEnums + 1 more
- `test_hermes_adapter_parity.py` — Tests for Phase 14.14E — Hermes Adapter Parity.
- `test_identity_resolver.py` — Defines TestIdentityResolver
- `test_institutional_memory_runtime.py` — Tests for institutional_memory_runtime
- `test_interpretation_engine_v1.py` — Tests for Interpretation Engine v1 — Phase 96.8W.
- `test_knowledge_awareness.py` — Defines TestKnowledgeType + 3 more
- `test_knowledge_layers.py` — Defines TestLayerDefinitions + 2 more
- `test_learning_extraction_runtime.py` — Tests for LearningExtractionRuntime — Campaign 12.0.
- `test_learning_portfolio_runtime.py` — Defines FakeLessonSnapshot + 14 more
- `test_learning_routes.py` — Defines TestRouteImports + 2 more
- `test_live_runtime_identity_v1.py` — Tests for live_runtime_identity_v1
- `test_lyfeos_creatoros_integration.py` — Tests for lyfeos_creatoros_integration
- `test_memory_api_tier2.py` — Tests for Law 5.5 Tier 2 — merge_event_payload() method.
- `test_memory_system.py` — Defines TestMemorySystem
- `test_mesh_dispatch_contract.py` — C40A Phase 2 — Mesh Dispatch Contract Tests.
- `test_meta_ide_audit.py` — Tests for Meta IDE functional audit.
- `test_meta_ide_context_runtime.py` — Tests for meta_ide_context_runtime
- `test_meta_ide_projection_loop_runtime.py` — Tests for MetaIDEProjectionLoopRuntime — Campaign 3.4.
- `test_meta_ide_runtime.py` — Defines MockFleetAssignment + 6 more
- `test_mvp_readiness_runtime.py` — Tests for MVPReadinessRuntime — Campaign 4.5.
- `test_node_mesh.py` — Defines FakeEmitter + 5 more
- `test_node_mesh_ws.py` — Tests for node_mesh_ws
- `test_notification_engine.py` — Tests for notification_engine
- `test_ontology_enacted.py` — Tests for substrate.ontology — primitives, laws, and domain bridges.
- `test_operating_loop_coherence_runtime.py` — Tests for operating_loop_coherence_runtime
- `test_operating_loop_runtime.py` — Tests for OperatingLoopRuntime — Campaign 4.1.
- `test_operations_routes.py` — Defines TestExecutionFabricRoutes + 3 more
- `test_operator_loop_mvp.py` — Operator Loop MVP — end-to-end integration test.
- `test_operator_loop_phase2.py` — Tests for operator_loop_phase2
- `test_operator_migration_runtime.py` — Tests for W5 — Operator Migration Runtime.
- `test_orchestrator_awareness_runtime.py` — Tests for OrchestratorAwarenessRuntime — Campaign 4.0.
- `test_orchestrator_presence_runtime.py` — Tests for orchestrator_presence_runtime
- `test_organism_coordination_engine.py` — Tests for organism_coordination_engine
- `test_organism_portfolio_runtime.py` — Tests for organism_portfolio_runtime
- `test_organism_state_runtime.py` — Defines TestOrganismModeEnum + 6 more
- `test_outcome_pattern_engine.py` — Tests for outcome_pattern_engine
- `test_outcome_tracking_runtime.py` — Tests for outcome_tracking_runtime
- `test_outcome_verification.py` — Tests for C26A — Outcome Verification Runtime.
- `test_override_tracking.py` — TestRecordOverride: Tests for the expanded record_override method.
- `test_p0_smoke.py` — Defines TestDiscordBotImports + 4 more
- `test_p1_phase10_transports.py` — P1 Phase 10 — Transport Layer Convergence tests.
- `test_p1_phase11_adapters.py` — Defines TestAdapterInventory + 2 more
- `test_p1_phase12_projections.py` — P1 Phase 12 — Projections & Nodes Convergence tests.
- `test_p1_phase13_services.py` — Defines TestServiceEntrypoints + 3 more
- `test_p1_phase14_cockpit.py` — P1 Phase 14 — Cockpit UI Convergence tests.
- `test_p1_phase2_bridge.py` — P1 Phase 2 — Cognitive Pipeline Bridge tests.
- `test_p1_phase2b_operator.py` — P1 Phase 2B — Operator Experience Layer verification.
- `test_p1_phase3_memory.py` — Tests for p1_phase3_memory
- `test_p1_phase4_world_model.py` — P1 Phase 4 — World Model Convergence tests.
- `test_p1_phase5_reasoning.py` — Defines TestReasoningArchitecture + 3 more
- `test_p1_phase6_learning.py` — Tests for p1_phase6_learning
- `test_p1_phase7_loops.py` — P1 Phase 7 — Autonomous Operation tests.
- `test_p1_phase8_closure.py` — Defines TestSubstrateCompleteness + 4 more
- `test_p1_phase9_architecture.py` — P1 Phase 9 — Architecture Law Enforcement tests.
- `test_p2_phase1_runner.py` — P2 Phase 1 — WorkflowRunner tests.
- `test_p2_phase2_research.py` — Defines TestResearchWorkflowStructure + 1 more
- `test_p2_phase3_planning.py` — P2 Phase 3 — Planning Workflow tests.
- `test_p2_phase4_communication.py` — P2 Phase 4 — Communication Workflow tests.
- `test_p2_phase5_review.py` — P2 Phase 5 — Review Workflow tests.
- `test_p2_phase6_execution.py` — Defines TestExecutionWorkflowStructure + 1 more
- `test_p2_phase7_daily.py` — P2 Phase 7 — Daily Rhythm Workflow tests.
- `test_p2_phase8_integration.py` — P2 Phase 8 — Integration tests for all workflow domains.
- `test_p3_phase1_github.py` — P3 Phase 1 — GitHub Workflow tests.
- `test_p3_phase2_document.py` — Defines TestDocumentWorkflowStructure + 2 more
- `test_p3_phase3_browser.py` — Tests for p3_phase3_browser
- `test_p3_phase4_slack.py` — Tests for p3_phase4_slack
- `test_p3_phase5_design.py` — P3 Phase 5 — Design Workflow tests.
- `test_permission_tiers.py` — Tests for the 4-tier permission model (Read/Draft/Execute/Commit).
- `test_persist_all_observations.py` — Tests for persist-all-observations — every observation becomes a memory entry.
- `test_persistent_loops.py` — Tests for persistent_loops
- `test_phase10_2_sandbox_pr.py` — Defines TestApprovalGateCreation
- `test_phase10_3_production_truth.py` — Tests for phase10_3_production_truth
- `test_phase10_4_reliability_campaign.py` — Phase 10.4 — Low-risk production truth reliability campaign tests.
- `test_phase10_5_reliability_weighted_cadence.py` — TestReliabilitySignalAggregation: TST-22: Verify reliability signals aggregate from real artifacts.
- `test_phase13_3_context_assimilation.py` — Phase 13.3 — Context Assimilation + Continuous Reconciliation Kernel tests.
- `test_phase13_3s_operational_truth.py` — Defines TestOperationalTruthSnapshot + 2 more
- `test_phase13_4_operator_e2e_acceptance.py` — Phase 13.4 — Standard Multi-Runtime Operator E2E Acceptance Tests.
- `test_phase14_11a_execution_control.py` — Tests for phase14_11a_execution_control
- `test_phase14_11a_paused_lifecycle.py` — Defines TestPausedStateExists + 4 more
- `test_phase14_11a_workstation_endpoints.py` — Defines TestModeResolver + 5 more
- `test_phase14_11b_checkpoint_resume.py` — Defines TestContinuityCheckpoint + 2 more
- `test_phase14_11b_continuity.py` — Phase 14.11B — Continuity state machine tests.
- `test_phase14_11b_dual_modes.py` — Tests for phase14_11b_dual_modes
- `test_phase14_11b_mode_switch_overnight.py` — Defines TestModeCommandParsing + 2 more
- `test_phase14_11c_file_browser.py` — Phase 14.11C — File browser safety + functionality tests.
- `test_phase14_11c_workspace_endpoints.py` — Tests for phase14_11c_workspace_endpoints
- `test_phase14_11d_activation_signal.py` — Defines TestActivationSource + 4 more
- `test_phase14_11d_jarvis_command.py` — Phase 14.11D — Jarvis command routing + governance tests.
- `test_phase14_11d_presence_endpoints.py` — Tests for phase14_11d_presence_endpoints
- `test_phase14_11d_voice_integration.py` — Phase 14.11D — Voice/STT/TTS integration and trace tests.
- `test_phase14_11e_agent_registry.py` — Tests for phase14_11e_agent_registry
- `test_phase14_11e_jarvis_commands.py` — Tests for phase14_11e_jarvis_commands
- `test_phase14_11g_actionability.py` — Tests for phase14_11g_actionability
- `test_phase14_15_continuity.py` — Phase 14.15 — Full Continuity Daily Driver tests.
- `test_phase14_3_product_docs_convergence.py` — Tests for phase14_3_product_docs_convergence
- `test_phase14_3a_full_content_convergence.py` — Defines TestPreflight + 2 more
- `test_phase14_4_trinity_alignment.py` — Tests for phase14_4_trinity_alignment
- `test_phase14_5_convergence_planning.py` — Tests for phase14_5_convergence_planning
- `test_phase14_5a.py` — Phase 14.5A tests — 13-layer production stack + Socratic governance completion.
- `test_phase14_5r_production_truth.py` — Tests for phase14_5r_production_truth
- `test_phase14_6b_creatoros_lossless_canon.py` — Tests for phase14_6b_creatoros_lossless_canon
- `test_phase14_6b_eos_lossless_canon.py` — Comprehensive pytest test suite for EOS Phase 14.6B canon reconstruction.
- `test_phase14_6b_lyfeos_code_resolved_canon.py` — Tests for phase14_6b_lyfeos_code_resolved_canon
- `test_phase14_6b_umh_code_resolved_canon.py` — TestArtifactExistence: Test that all required artifacts exist.
- `test_phase14_6c_operator_review.py` — Comprehensive pytest test suite for Phase 14.6C operator review packet.
- `test_phase14_6d_canon_revision.py` — Constants/config (defines _REPO_ROOT)
- `test_phase14_6e_p0_ratification.py` — Comprehensive pytest test suite for Phase 14.6E P0 ratification sprint.
- `test_phase14_6f_canon_revision.py` — Tests for phase14_6f_canon_revision
- `test_phase14_6g_readiness_gate.py` — Tests for phase14_6g_readiness_gate
- `test_phase14_7a_wave1.py` — Tests for phase14_7a_wave1
- `test_phase14_7a_wave2.py` — Tests for phase14_7a_wave2
- `test_phase14_7a_wave3.py` — Tests for phase14_7a_wave3
- `test_phase14_7b_cockpit_usability.py` — Tests for phase14_7b_cockpit_usability
- `test_phase14_8a_wp12.py` — Tests for phase14_8a_wp12
- `test_phase14_8b_wave2.py` — TestIntentClassifyEndpoint: Verify POST /intent/classify exists and wires to spine classification.
- `test_phase14_8c_wave3.py` — Phase 14.8C Wave 3 tests — outcome recording, cadence enforcement,
- `test_phase17_organism_loop_e2e.py` — Tests for phase17_organism_loop_e2e
- `test_phase18_operator_convergence.py` — Phase 18 — Operator Convergence integration tests.
- `test_phase19_reality_canonicalization.py` — Phase 19 — Reality Canonicalization E2E tests.
- `test_phase20_reality_intelligence.py` — Tests for phase20_reality_intelligence
- `test_phase21_meta_ide_convergence.py` — Tests for Phase 21 — Meta IDE Convergence.
- `test_phase22_autonomous_engineering.py` — TestEngineeringIntentClassification: Test deterministic regex-based intent classification.
- `test_phase23_engineering_proof_loop.py` — Tests for phase23_engineering_proof_loop
- `test_phase24_distributed_worker_runtime.py` — Phase 24 — Distributed Worker Runtime test suite.
- `test_phase25_workspace_observation.py` — Phase 25 — Workspace Observation tests.
- `test_phase26_action_bridge.py` — Tests for phase26_action_bridge
- `test_phase27_workspace_runtime_graph.py` — Tests for phase27_workspace_runtime_graph
- `test_phase28_umh_node_role_version_topology.py` — Phase 28 — UMH Node Role & Version Topology tests.
- `test_phase29_state_authority_graph.py` — Tests for phase29_state_authority_graph
- `test_phase30_service_dependency_graph.py` — TestDependencyStrengthEnum: Test DependencyStrength enum — 3 values.
- `test_phase31_operator_home.py` — Tests for phase31_operator_home
- `test_phase32_presence_continuity.py` — Phase 32 — Presence & Continuity Runtime tests.
- `test_phase33_screen_awareness.py` — Defines MockTerminal + 8 more
- `test_phase34_workstation_observation.py` — Phase 34 — Workstation Observation Runtime tests.
- `test_phase35_voice_runtime.py` — Phase 35 — Voice Query Engine tests.
- `test_phase9_5_spine_native_propagation.py` — Tests for phase9_5_spine_native_propagation
- `test_phase9_5b_template_campaign.py` — TestCampaignExecution: Campaign runs through spine with auto-propagation.
- `test_phase9_6_autonomous_lane.py` — Tests for phase9_6_autonomous_lane
- `test_phase9_7_pr_factory.py` — Phase 9.7 — Sandboxed Autonomous PR Factory tests.
- `test_phase9_8_production_truth.py` — Phase 9.8 — Production Truth Promotion + Scheduled Autonomous Cadence tests.
- `test_philosophy_lenses.py` — Tests for substrate.understanding.knowledge.philosophy_lenses.
- `test_prediction_portfolio_runtime.py` — Tests for prediction_portfolio_runtime
- `test_prediction_routes.py` — Tests for cockpit prediction routes — Campaign 13.3.
- `test_presence_runtime.py` — Tests for Phase 8: Presence Runtime.
- `test_priority_engine.py` — Campaign 7.1 — Priority Engine tests.
- `test_product_connections.py` — Functions: test_product_enum_values() + 12 more
- `test_profile_runtime.py` — Defines TestProfileModeEnum + 7 more
- `test_project_registry.py` — Tests for project_registry
- `test_projection_certification.py` — Tests for projection_certification
- `test_projection_delta.py` — Tests for projection_delta
- `test_projection_engine.py` — Tests for projection_engine
- `test_projection_integration_runtime.py` — Tests for projection_integration_runtime
- `test_provider_state.py` — Tests for runtime.provider_state — global failure state + backpressure.
- `test_reality_ambush.py` — Tests for reality_ambush
- `test_reality_benchmark.py` — Defines TestBenchmarkScenarios + 4 more
- `test_reality_graph.py` — Tests for Reality Graph — Campaign 5.0.
- `test_reality_model.py` — Defines TestCanonicalRealityModel + 1 more
- `test_recommendation_engine.py` — Tests for recommendation_engine
- `test_registry.py` — Defines TestComponentRegistry
- `test_repository_awareness.py` — Tests for repository_awareness
- `test_resource_allocation_runtime.py` — Tests for resource_allocation_runtime
- `test_risk_engine.py` — Campaign 7.2 — Risk Engine tests.
- `test_runtime_awareness.py` — Tests for runtime_awareness
- `test_runtime_state_registry.py` — Tests for runtime_state_registry
- `test_scenario_intelligence_engine.py` — Tests for ScenarioIntelligenceEngine — Campaign 13.1.
- `test_self_model.py` — Tests for substrate.self_model — the system's self-awareness foundation.
- `test_self_use_catalog.py` — Functions: test_task_roundtrip() + 9 more
- `test_self_use_gap_ledger.py` — Functions: test_gap_entry_roundtrip() + 5 more
- `test_self_use_report.py` — Functions: test_coherence_metrics_pass() + 10 more
- `test_session_machine_runtime.py` — Tests for SessionMachineRuntime — Campaign 19.2.
- `test_session_runtime.py` — Tests for session_runtime
- `test_source_truth_linker.py` — Defines MockSource + 2 more
- `test_spine_full.py` — Tests for ConcreteExecutionSpine — 8-stage pipeline.
- `test_sprint1_smoke.py` — TestNodeRegistryDeadlock: Verify NodeRegistry deadlock is fixed — snapshot outside lock, plain Lock.
- `test_sprint2_boundary.py` — TestCanonicalTypes: Verify types are defined in substrate.contracts.agent_types.
- `test_sprint3_recovery.py` — Sprint 3 — Test Recovery verification.
- `test_sprint4_data_hygiene.py` — Sprint 4 — Data/Log Hygiene verification.
- `test_sprint5_doc_truth.py` — Sprint 5 — Documentation Truth verification.
- `test_stage1_acceptance_e2e.py` — Tests for stage1_acceptance_e2e
- `test_strategic_context_runtime.py` — Defines _MockGapEngine + 12 more
- `test_strategic_gap_engine.py` — Tests for strategic_gap_engine
- `test_strategic_memory_engine.py` — Defines MockDecision + 8 more
- `test_strategic_planning_engine.py` — Tests for StrategicPlanningEngine — Campaign 8.3.
- `test_strategic_tick_loop.py` — Tests for Phase 5: Strategic Tick Loop.
- `test_tme_active_tool_context.py` — Tests for the TME Active Tool Context.
- `test_tme_mastery_assurance_gate.py` — Defines TestNormalization + 5 more
- `test_tme_natural_language_resolver.py` — Tests for the TME Natural Language Tool Mastery Resolver.
- `test_trace_recorder.py` — Tests for ConcreteTraceRecorder.
- `test_tradeoff_intelligence_engine.py` — Tests for tradeoff_intelligence_engine
- `test_trajectory_intelligence_runtime.py` — Tests for trajectory_intelligence_runtime
- `test_transformation_state_ledger.py` — Defines TestStateLedgerRecordCreation + 1 more
- `test_trust_score.py` — Tests for trust_score
- `test_type_divergence.py` — Defines TestCanonicalTypeRegistry + 1 more
- `test_unified_approval_runtime.py` — Tests for UnifiedApprovalRuntime — Campaign 4.2.
- `test_unified_execution_surface_runtime.py` — Tests for unified_execution_surface_runtime
- `test_unified_workstation_runtime.py` — Defines _Snapshot + 10 more
- `test_vision.py` — Tests for Phase 14.14B — DEX Vision Embodiment.
- `test_vision_14_16.py` — Tests for vision_14_16
- `test_vision_14_17.py` — Tests for Phase 14.17 — Vision Reliability Hardening.
- `test_vision_14_18.py` — Tests for Phase 14.18 — Camera Default-On + Realtime PTZ Control Loop + Smooth Vision UX.
- `test_vision_14_18c.py` — Tests for vision_14_18c
- `test_vision_14e.py` — Tests for vision_14e
- `test_voice_idempotency.py` — Phase 14.13V: Voice turn idempotency tests.
- `test_voice_identity.py` — Phase 14.13U: Voice identity and source sync tests.
- `test_voice_route_resolver.py` — Tests for substrate/workstation/voice_route_resolver.py.
- `test_voice_turn_assembly.py` — Tests for voice_turn_assembly
- `test_work_intelligence_routes.py` — Tests for work_intelligence_routes
- `test_work_lanes.py` — Tests for Beast multi-session work lanes, app resolver, and loop engine.
- `test_work_portfolio_runtime.py` — Defines _MockReadinessAssessment + 15 more
- `test_work_readiness_runtime.py` — Defines _MockNode + 11 more
- `test_work_state.py` — Tests for runtime.work_state — idle detection + adaptive throttling.
- `test_workspace_awareness.py` — Tests for workspace_awareness
- `test_workstation_executor.py` — Defines TestPathValidation + 2 more
- `test_workstation_mvp_loop.py` — Integration tests for Campaign 17 — Workstation MVP Loop.
- `test_workstation_presence_runtime.py` — Tests for Campaign 17.2 — WorkstationPresenceRuntime.
- `test_workstation_runtime.py` — Tests for workstation_runtime
- `test_workstation_session_runtime.py` — Defines TestLifecycle + 1 more

#### tests/adapters/

- `__init__.py` — Package init

#### tests/adapters/broadcast/

- `__init__.py` — Package init
- `test_filtergraph.py` — Tests for filtergraph
- `test_node_dispatch.py` — TestBroadcastAdapter: Tests for the node-side broadcast adapter.
- `test_process_lifecycle.py` — Functions: sleep_cmd() + 4 more

#### tests/certification/

- `__init__.py` — Package init
- `c28_certification.py` — C28 Certification module
- `c28_panel_audit.py` — C28 Panel Audit — runs ON Beast with real Playwright display.
- `c28_task_acceptance.py` — Defines TaskResult
- `c29_benchmark.py` — Constants/config (defines _COCKPIT_URL)
- `c29_evidence.py` — Constants/config (defines _COCKPIT_URL)
- `c29_report.py` — C29 Harness Superiority — Certification Report Generator.

#### tests/substrate/

- `__init__.py` — Package init
- `test_entity_store.py` — Tests for substrate.state.stores.entity_store — entity persistence layer.
- `test_feedback_loop.py` — Tests for feedback_loop
- `test_types.py` — Tests for types

### umh/ — Desktop/Voice/Vision Relays (3 files)

- `desktop_relay.py` — desktop relay server (ws://0.0.0.0:8100/desktop) that bridges Beast desktop frames to cockpit viewers.
- `vision_relay.py` — vision relay server (ws://0.0.0.0:8097/vision) that bridges Beast camera frames to cockpit viewers.
- `voice_server.py` — cockpit voice server (ws://0.0.0.0:8096/voice) providing pure STT + TTS bridging for DEX conversations.



### cockpit/ — Electron + React + Capacitor Frontend (385+ files)

### cockpit/ (root config + scripts)
- `deploy.sh` — cockpit deploy gate: verifies nginx.conf.template, Dockerfile, and start.sh match main before running flyctl deploy. NEVER run flyctl deploy directly.
- `start.sh` — container startup script: copies nginx template to config, starts nginx to serve the built cockpit PWA
- `electron.vite.config.ts` — Electron-Vite build configuration: resolves main/preload/renderer entry points, applies React + Tailwind plugins
- `vite.web.config.ts` — Vite config for the standalone PWA web build (non-Electron), wires React + Tailwind, sets /src/renderer as root
- `vitest.config.ts` — Vitest test runner configuration with React plugin and path aliases
- `capacitor.config.ts` — Capacitor mobile config: app ID `tech.universalmetaharness.cockpit`, webDir `dist-web`, dark splash/status bar, push notification presentation options, iOS scheme and Android background color
- `DESIGN.md` — LOCKED UI design specification (2026-07-03): complete token system (colors, spacing, typography), component dimensions (TitleBar 46px, HudBar 28px, drawers 160/240px), layout rules for desktop/mobile/web, chat styling, and canvas behavior. Authoritative — changes require explicit approval.

### cockpit/assets/ — icon and splash source images (5 files)
- `icon-background.png` — adaptive icon background layer
- `icon-foreground.png` — adaptive icon foreground layer
- `icon-only.png` — standalone app icon (no background)
- `splash.png` — light splash screen image
- `splash-dark.png` — dark splash screen image

### cockpit/android/ — Capacitor Android native project (51 files)
Generated by `npx cap add android`. Gradle build system, Android SDK.
- `build.gradle` — root Gradle build config
- `settings.gradle` — Gradle module settings
- `variables.gradle` — Capacitor version variables
- `gradle.properties` — Gradle JVM and AndroidX settings
- `gradlew` / `gradlew.bat` — Gradle wrapper scripts
- `gradle/wrapper/gradle-wrapper.properties` — Gradle distribution URL
- `gradle/wrapper/gradle-wrapper.jar` — Gradle wrapper binary
- `app/build.gradle` — app module Gradle config (minSdk, targetSdk, dependencies)
- `app/proguard-rules.pro` — ProGuard rules (empty by default)
- `app/src/main/AndroidManifest.xml` — Android manifest: permissions, activity declaration
- `app/src/main/java/tech/universalmetaharness/cockpit/MainActivity.java` — Capacitor BridgeActivity entry point
- `app/src/main/res/` — Android resources: launcher icons (hdpi through xxxhdpi), splash screens (portrait/landscape per density), layout XML, strings, styles, adaptive icon XML
- `app/src/test/` — unit test stub (ExampleUnitTest.java)
- `app/src/androidTest/` — instrumented test stub (ExampleInstrumentedTest.java)

### cockpit/ios/ — Capacitor iOS native project (15 files)
Generated by `npx cap add ios`. Xcode workspace, CocoaPods.
- `App/Podfile` — CocoaPods dependency file (Capacitor pods)
- `App/App.xcodeproj/project.pbxproj` — Xcode project config
- `App/App.xcworkspace/xcshareddata/IDEWorkspaceChecks.plist` — workspace metadata
- `App/App/AppDelegate.swift` — iOS app delegate (Capacitor CAPBridgeViewController)
- `App/App/Info.plist` — iOS app info (bundle ID, version, permissions)
- `App/App/Base.lproj/Main.storyboard` — main storyboard
- `App/App/Base.lproj/LaunchScreen.storyboard` — launch screen storyboard
- `App/App/Assets.xcassets/Contents.json` — asset catalog root
- `App/App/Assets.xcassets/AppIcon.appiconset/Contents.json` — app icon config
- `App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png` — 1024x1024 app icon
- `App/App/Assets.xcassets/Splash.imageset/Contents.json` — splash image config
- `App/App/Assets.xcassets/Splash.imageset/splash-2732x2732.png` / `-1.png` / `-2.png` — splash images at 1x/2x/3x

### cockpit/tests/
- `__init__.py` — empty package marker for cockpit test suite

### cockpit/src/main/
- `index.ts` — Electron main process: creates BrowserWindow, manages tray icon, spawns voice/vision/browser relay child processes, handles IPC for window modes (maximized → large-fab → medium-fab → small-fab → invisible), global shortcuts, notifications

### cockpit/src/preload/
- `index.ts` — Electron preload script: exposes a secure `window.cockpit` bridge via contextBridge for window controls (minimize/maximize/close/setMode), voice start/stop, vision start/stop, browser relay, notifications, file operations

### cockpit/src/renderer/ (root)
- `App.tsx` — Root React component: wraps app in Clerk auth (SignedIn/SignedOut), initializes keyboard hooks, organism realtime WebSocket, vision connection, guest join routing for conference rooms
- `main.tsx` — React entry point: mounts App inside ClerkProvider and StrictMode, registers service worker for PWA push notifications, initializes Capacitor on native platforms
- `capacitor-init.ts` — Capacitor native platform init: sets dark status bar, hides keyboard accessory bar, requests push notification permissions, registers device token with API, handles notification tap → URL navigation. Only runs on native (iOS/Android), no-op on web.
- `constants.ts` — Exports `getAiName()` which reads the AI assistant's display name from configStore (falls back to VITE_AI_NAME env var)
- `global.d.ts` — TypeScript declarations for the `window.cockpit` Electron bridge (window, voice, vision, browser, notifications, files) and Vite env vars
- `sw.ts` — Service worker: caches app shell (index.html, JS/CSS bundles) for offline support, serves offline.html fallback when network unavailable, handles push notification events with title/body/category, opens cockpit URL on notification click

### cockpit/src/renderer/__tests__/
- `apiClient.test.ts` — Unit tests for the `fetchApi` HTTP client: verifies auth header injection, JSON parsing, error handling, 401 retry logic
- `cockpitStore.test.ts` — Unit tests for `cockpitStore`: verifies panel switching, chat toggle, split panel, window mode cycling state transitions
- `setup.ts` — Vitest setup file: imports jest-dom matchers for React component testing

### cockpit/src/renderer/public/ — PWA static assets (6 files)
- `manifest.json` — PWA manifest: app name "UMH Cockpit", start URL, theme color #07080a, display standalone, icon references (192/512 standard + maskable)
- `offline.html` — PWA offline fallback page: dark-themed "You're offline" message with retry button, shown when network unavailable and no cached page exists
- `favicon.ico` — browser tab icon
- `icon-192.png` — PWA icon 192x192 (standard)
- `icon-512.png` — PWA icon 512x512 (standard)
- `icon-maskable-192.png` — PWA maskable icon 192x192 (safe area for adaptive icon shapes)
- `icon-maskable-512.png` — PWA maskable icon 512x512 (safe area for adaptive icon shapes)

### cockpit/src/renderer/api/
- `broadcast-ws.ts` — WebSocket client for the real-time broadcast system: connects to the broadcast relay, sends/receives live state updates across connected devices
- `browser-ws.ts` — WebSocket client for remote browser streaming: connects to the browser relay, receives page screenshots/DOM state, sends navigation commands and click/type events
- `client.ts` — Central HTTP API client: `fetchApi()` wrapper that adds Clerk auth token to every request, handles 401 token refresh, exports `setTokenGetter()` and `getApiKey()` for other modules
- `device-presence.ts` — Device presence API: registers the current device (mobile/desktop/electron/terminal) with the operator API, sends heartbeats, handles disconnect and session recovery
- `tts-playback-controller.ts` — TTS audio playback controller with iOS Safari unlock: maintains a reusable Audio element unlocked on first user gesture, queues and plays TTS audio chunks sequentially
- `vision-ws.ts` — WebSocket client for the vision relay: streams camera frames, sends PTZ commands (pan/tilt/zoom), receives object detection and tracking data from the vision pipeline
- `voice-controller.ts` — Voice session controller: coordinates mic capture → STT → advisor → TTS pipeline, manages voice turn lifecycle (start/stop/barge-in), handles clap detection for hands-free activation
- `voice-turn-assembler.ts` — Collects STT transcript segments into coherent turns before dispatch: prevents duplicate messages from STT pauses using silence grace timeout (1600ms desktop / 2200ms mobile) and tap-to-stop
- `voice-ws.ts` — WebSocket client for the voice relay: streams mic audio as PCM chunks, receives STT transcripts and TTS audio responses, handles WebSocket reconnection
- `websocket.ts` — Generic WebSocket client base class: auto-reconnect with exponential backoff, JSON message routing by type, binary data handlers, heartbeat keepalive

### cockpit/src/renderer/components/
- `ActionRequired.tsx` — Renders a list of action-required items (approvals, blocked tasks, failures, stale items) with severity-colored badges and click handlers
- `AgentCard.tsx` — Card component displaying an agent's name, status, role, skills list, and runtime badge (which AI model/runtime is executing it)
- `CallOverlay.tsx` — Full-screen voice call overlay: shows mic/speaker mute toggles, call duration, hangup button, participant info during active voice sessions
- `CameraController.tsx` — PTZ camera control panel: directional pad (up/down/left/right), zoom in/out, home position, presets, camera on/off toggle, PiP mode, scene inventory
- `CameraPreview.tsx` — Compact camera preview widget: shows live vision feed thumbnail with camera toggle, snapshot button, PiP popout, collapsible to save space
- `CanvasMenuBar.tsx` — Menu bar for the canvas workspace: mode selector (general/agents/workflows/loops/harness/organism), canvas-specific actions, window management
- `ChannelList.tsx` — Renders a scrollable list of conversation channels with last message preview, sender, timestamp, and unread count badge
- `ChannelView.tsx` — Renders a single conversation thread: message bubbles with sender, timestamp, intent labels, and a compose input at the bottom
- `CommandPalette.tsx` — Global command palette (Cmd+K): fuzzy-searches panels, canvas modes, and API commands; navigates to the selected item on enter
- `ConnectionBanner.tsx` — Alert banner shown when the WebSocket connection to the organism is disconnected: shows reconnect count, events/minute, last pulse timestamp
- `ControlPanel.tsx` — Bottom control bar: collapsible panel with dark/light theme toggle, governance mode selector, active approvals count, quick-action buttons, operator chat input
- `CronTable.tsx` — Table component displaying scheduled cron jobs: columns for agent, name, schedule expression, last fired time, next run, and status badge
- `DetailDrawer.tsx` — Slide-in drawer from the right edge: renders a title, subtitle, optional badge, and arbitrary children content for detail views
- `DeviceDiagnosisInline.tsx` — Inline device diagnosis component: runs connectivity checks against a Tailscale peer, shows SSH guidance per OS, triggers device registration
- `DeviceOnboardingCard.tsx` — Card for onboarding a new device: shows device details, role/type dropdowns, approve/reject buttons for adding the device to the UMH mesh
- `ErrorBoundary.tsx` — React error boundary: catches render errors in child components, shows fallback UI, logs error info
- `EventConsole.tsx` — Real-time scrolling event log: shows organism events color-coded by domain (runtime=cyan, governance=purple, advisor=amber), filterable by domain
- `ExecutionTimeline.tsx` — Renders the lifecycle stages of an execution (proposed → governance_check → approved → executing → completed) with timing and duration
- `ExecutorBadge.tsx` — Small badge showing the executor type and target machine for a task (e.g., "claude-code on VPS")
- `FabLarge.tsx` — Large floating action button (FAB) mode: shows agent status, chat input, voice waveform, and mode indicator (EXECUTE/PLAN) in an expanded floating widget
- `FabMedium.tsx` — Medium FAB mode: compact floating widget with voice waveform, mode color indicator, and click-to-expand behavior
- `FabSmall.tsx` — Small FAB mode: minimal floating circle with voice waveform, auto-cycles window modes on click
- `GraphView.tsx` — Canvas-based graph renderer: draws nodes and edges with force-directed layout, supports pan/zoom, click selection, and hover tooltips
- `HudBar.tsx` — Top status HUD bar: shows system status indicators (voice active, vision connected, realtime events/min), workstation mode, connection quality
- `IDEMenuBar.tsx` — Meta-IDE menu bar: File/Edit/View/Run/Terminal menus for the integrated code editor, triggers API calls for file operations and terminal commands
- `LeftDrawer.tsx` — Left-side slide-out drawer (mobile): renders children content in an overlay panel that slides in from the left edge on mobile viewports
- `LeftRail.tsx` — Left navigation rail (240px): renders grouped route icons with labels, active panel highlight, collapse/expand toggle, and a compass icon header
- `LivePreview.tsx` — Embedded live preview iframe: shows a projection's web UI with navigation controls (back/forward/refresh), viewport selector (desktop/tablet/mobile), and URL bar
- `NavRail.tsx` — Compact icon-only navigation rail: renders panel icons with keyboard shortcut labels (1-9), highlights active panel
- `OverlayToggle.tsx` — Toggle button group for enabling/disabling overlay options: renders a row of labeled toggle buttons with optional color indicators
- `ResumeCard.tsx` — Session resume card: shows the last active session's state (branch, files, time elapsed), with a "Resume" button to restore the workstation context
- `RightDrawer.tsx` — Right-side slide-out drawer (mobile): renders the chat RightRail in an overlay panel on mobile viewports
- `RightRail.tsx` — Right chat panel: renders the operator↔DEX conversation with markdown support, message input with attachments (image/file), voice mic toggle, edit/download actions
- `RingGauge.tsx` — SVG ring gauge component: renders a circular progress indicator with value, max, label, unit text, and configurable color/size
- `RuntimeBadge.tsx` — Badge showing which runtime is executing a task: normalizes runtime strings to icons (claude-code, codex, hermes, browser, shell, local-model)
- `Shell.tsx` — Top-level layout shell: composes TitleBar + LeftRail/LeftDrawer + main panel area + RightRail/RightDrawer + ControlPanel + HudBar + CommandPalette + FAB overlays
- `SplitPane.tsx` — Horizontal split pane with draggable divider: renders left and right children with configurable initial ratio and min/max constraints
- `SplitPreview.tsx` — Multi-projection live preview: renders 1-4 LivePreview iframes side by side, with add/remove/cycle controls for comparing UMH/EOS/CreatorOS/LyfeOS projections
- `StatusBadge.tsx` — Colored status badge: maps status strings (active, running, idle, failed, etc.) to color-coded pill badges with consistent styling
- `StorePolling.tsx` — Background polling coordinator: calls fetch methods on multiple Zustand stores (execution summary, workstation, approvals, engineering) at regular intervals
- `TaskBlock.tsx` — Task list item: renders task title, status (pending/in_progress/completed/blocked), assigned agent, timestamp, and click handler
- `TimelineView.tsx` — Vertical timeline component: renders events as connected nodes with labels, timestamps, status indicators, and dependency lines
- `TitleBar.tsx` — Custom window title bar for Electron: renders minimize/maximize/close buttons, drag region, and window mode indicator
- `TopologyMap.tsx` — Organism topology visualization: renders workcell nodes (advisor, executor, researcher, reviewer) with status dots and connection lines showing the organism structure
- `TrackingPanel.tsx` — Vision object tracking controls: manage tracked objects with enable/disable, alert/notify toggles, search filter, delete, and focus-camera actions
- `ViewportSelector.tsx` — Dropdown selector for viewport presets (responsive, desktop 1440px, tablet 768px, mobile 375px) used by LivePreview
- `VisionPopout.tsx` — Popout window for the vision feed: opens the camera stream in a separate browser window (480×360) for picture-in-picture viewing
- `VoiceCommandBar.tsx` — Voice command bar UI: shows mic level indicator, wake-word detection (clap or name), transcript display, and voice state transitions
- `VoiceRouteHud.tsx` — Compact HUD showing the active voice route: displays which device's mic and TTS are currently active, only visible during voice sessions
- `VoiceWaveform.tsx` — Animated voice waveform visualization: renders audio level bars that respond to real-time mic input levels

### cockpit/src/renderer/components/canvas/
- `AgentCanvasNode.tsx` — Draggable agent node on the canvas: shows agent name, status, minimize/maximize/close controls, renders AgentWindowContent inside
- `AgentCanvasWorkspace.tsx` — Agent-focused canvas workspace: manages layout of multiple agent nodes with add-agent button, auto-layout, and eye-toggle for visibility
- `BaseCanvas.tsx` — Base canvas component: handles pan (mouse drag), zoom (scroll wheel), provides coordinate system transformation for all canvas workspaces
- `CanvasContextMenu.tsx` — Right-click context menu for canvas: offers "Add Window" options (browser, desktop, camera, terminal, panel, preview) at cursor position
- `CanvasPalette.tsx` — Floating palette for adding new windows to the canvas: icon grid for browser, desktop, camera, terminal, panel, preview window types
- `CanvasToolbar.tsx` — Canvas toolbar: zoom in/out/reset controls, toggle left panel, grid/snap options, fit-to-screen button
- `CanvasWindow.tsx` — Draggable, resizable window container on the canvas: handles drag, resize from edges/corners, title bar with minimize/maximize/close buttons, renders WindowContent inside
- `CanvasWorkspace.tsx` — General-purpose canvas workspace: manages multiple CanvasWindow instances with add/remove, context menu, and toolbar
- `HarnessCanvasWorkspace.tsx` — Harness topology canvas: visualizes runtime nodes (CPU, server, database, monitor, terminal) with health indicators, connection lines, and auto-layout
- `LoopCanvasWorkspace.tsx` — Loop builder canvas: visual editor for creating/editing execution loops with play/stop/step controls, test runner, and iteration history
- `OrganismCanvasWorkspace.tsx` — Organism topology canvas: renders workcell nodes (Brain, Server, CPU), connection edges, health indicators, and auto-layout for the organism structure
- `UnifiedCanvasWorkspace.tsx` — Canvas mode router: switches between general/agents/workflows/loops/harness/organism canvas workspaces based on the active canvas mode
- `WindowContent.tsx` — Lazy-loading router for canvas window content: maps window types (browser, desktop, vision, terminal, panel, preview) to their content components
- `WorkflowCanvasWorkspace.tsx` — Workflow builder canvas: visual editor for creating workflow DAGs with nodes, connections, add-node button, and workflow toolbar
- `WorkflowConnection.tsx` — SVG arrow connecting two workflow nodes: renders a curved bezier path between source and target node positions
- `WorkflowNode.tsx` — Draggable workflow node: renders node type icon (trigger, action, condition, gate, timer, merge, alert, end), label, and status indicator

### cockpit/src/renderer/components/canvas/windows/
- `AgentConfigView.tsx` — Agent configuration editor inside a canvas window: edit agent name, model, skills, soul document, with save/reset buttons
- `AgentWindowContent.tsx` — Agent detail view inside a canvas window: shows agent status, recent tasks, execution history, and live output stream
- `BrowserWindowContent.tsx` — Embedded browser pane inside a canvas window: wraps BrowserPane component for remote browser streaming
- `DesktopWindowContent.tsx` — Remote desktop view inside a canvas window: shows a live monitor screenshot from a mesh-connected device, with refresh controls
- `PanelWindowContent.tsx` — Lazy-loads any cockpit panel (dashboard, agents, work, etc.) inside a canvas window: maps panel names to lazy-imported components
- `PreviewWindowContent.tsx` — URL preview iframe inside a canvas window: renders any URL in an embedded iframe with loading state
- `TerminalWindowContent.tsx` — Terminal emulator inside a canvas window: connects to a tmux session via API, renders command output, accepts keyboard input
- `VisionWindowContent.tsx` — Vision camera feed inside a canvas window: renders the live camera stream with overlay controls

### cockpit/src/renderer/components/cards/
- `ApprovalCard.tsx` — Chat card for approval requests: renders risk level badge (LOW/MEDIUM/HIGH/CRITICAL), action description, approve/reject buttons, and metadata
- `CommandResultCard.tsx` — Chat card for command execution results: renders markdown-formatted output with syntax highlighting and suggested follow-up actions
- `ConversationBubble.tsx` — Chat message bubble: renders markdown content with sender avatar, timestamp, role-based styling (operator, dex, system, agent, external)
- `ErrorCard.tsx` — Chat card for error messages: renders error description with severity styling and suggested recovery actions
- `RRIPRenderer.tsx` — RRIP message renderer: dispatches to the correct card type (ConversationBubble, ReportCard, CommandResultCard, ApprovalCard, ErrorCard) based on message kind
- `ReportCard.tsx` — Chat card for work/audit reports: renders markdown report content with download button and metadata header

### cockpit/src/renderer/components/rooms/
- `ChannelCreateModal.tsx` — Modal dialog for creating a new channel in a conference server: channel type selector (text/voice/video/forum/stage/broadcast/announcement), name input, optional category
- `ChannelSidebar.tsx` — Sidebar listing channels grouped by category: collapsible category sections, channel type icons (hash for text, speaker for voice), unread indicators
- `ForumChannelView.tsx` — Forum-style channel view: renders threaded posts with tags, pinned/locked indicators, reply counts, and a new-post form
- `GuestJoinPage.tsx` — Guest join page for conference rooms: invite link validation, camera/mic preview, display name input, connection quality indicator, join button
- `InvitePanel.tsx` — Panel for managing room invites: create invite links with expiry/max-uses, copy link, view active invites, set guest permissions
- `MeetingRoomPanel.tsx` — Video meeting room: camera/mic/screen-share controls, participant grid, chat sidebar, connection quality indicator, leave button
- `MemberListPanel.tsx` — Panel listing room members: grouped by presence status (online/idle/offline/dnd), shows role badges and status colors
- `RoomAuditLog.tsx` — Audit log for a conference server: displays timestamped moderation events (joins, leaves, kicks, role changes, channel updates)
- `RoomChatPanel.tsx` — Chat panel inside a conference room: message list with replies, compose input, real-time updates from the rooms store
- `RoomDexPanel.tsx` — DEX AI assistant panel inside a conference room: mode selector (silent/assist/active/moderate), DEX conversation thread
- `RoomMainView.tsx` — Main content area for a room: routes to TextChannelView, ForumChannelView, or MeetingRoomPanel based on the active channel type
- `RoomRightRail.tsx` — Right sidebar in conference rooms: tabs for member list, DEX assistant, chat, audit log, and invite management
- `ServerCreateModal.tsx` — Modal for creating a new conference server: name input, privacy selector (public/private/secret), template selector (team/project/community/gaming)
- `ServerRail.tsx` — Left rail showing conference server icons: server avatar circles, active server highlight, "+" button for creating new servers
- `TextChannelView.tsx` — Text channel view: scrolling message list with edit/delete/pin/reply/react actions, compose bar with formatting
- `ThreadPanel.tsx` — Thread sidebar: shows thread list for the current channel with message counts, archive/lock actions, and new-thread creation
- `VoiceRoomPanel.tsx` — Voice-only room panel: participant list with speaking indicators, mute/deafen/disconnect controls, connection status

### cockpit/src/renderer/components/vision/
- `index.ts` — Barrel export for all vision components: re-exports VisionOverlay, TrackedObjectBox, FaceTrackingOverlay, HandLandmarkOverlay, PoseSkeletonOverlay, and OverlayMetadata type
- `CameraModeSelector.tsx` — Camera mode picker: switches between tracking, face-recognition, alert, autonomous, and security modes with authority level selector
- `DiagnosticsPanel.tsx` — Vision diagnostics panel: shows stream metrics (FPS, latency, resolution), relay pipeline stats, quality mode selector, collapsible sections
- `FaceTrackingOverlay.tsx` — SVG overlay rendering detected face landmarks as connected dots on the camera feed
- `HandLandmarkOverlay.tsx` — SVG overlay rendering detected hand landmarks as connected dots on the camera feed
- `NotificationCenter.tsx` — Vision notification center: lists security/tracking/alert notifications with severity levels, dismiss/clear actions, collapsible by severity
- `PoseSkeletonOverlay.tsx` — SVG overlay rendering detected body pose skeleton (limb connections) on the camera feed
- `SceneInventory.tsx` — Scene inventory panel: lists all detected objects in the current camera view with inline label editing and delete actions
- `StatusHud.tsx` — Vision status HUD: compact display of camera state (connected/streaming/quality), frame freshness, control authority level
- `ToastContainer.tsx` — Toast notification container for vision events: renders auto-dismissing alerts with ok/warn/danger variants
- `TrackedObjectBox.tsx` — Bounding box overlay for a tracked object: renders a labeled rectangle at specified coordinates on the camera feed
- `VisionConnectionStatus.tsx` — Vision chain status indicator: shows relay connection state (relay_offline → connecting → camera_offline → streaming → error) with color-coded badge
- `VisionOverlay.tsx` — Composites all vision overlays: renders TrackedObjectBox, PoseSkeletonOverlay, HandLandmarkOverlay, and FaceTrackingOverlay together on the camera feed
- `VisionSettings.tsx` — Vision settings panel: camera selection, quality profile (low/medium/high), resolution, frame rate, stream metrics, relay configuration

### cockpit/src/renderer/constants/
- `devices.ts` — Device naming constants: canonical display names for all UMH devices (VPS, Beast) in `tailscale-hostname (device-type)` format, loaded from device_registry.json; `getDeviceDisplayName()` helper

### cockpit/src/renderer/hooks/
- `useBroadcastConnection.ts` — React hook managing the broadcast WebSocket lifecycle: connects on mount, syncs received state to broadcastStore, exposes client reference
- `useBrowserStream.ts` — React hook for remote browser streaming: manages BrowserWsClient connection, tracks current URL/title/loading state, provides navigation methods
- `useCanvasDrag.ts` — React hook for canvas drag interactions: tracks mouse down/move/up with zoom-corrected deltas, calls onDragStart/onDrag/onDragEnd callbacks
- `useCanvasResize.ts` — React hook for canvas window resizing: handles edge/corner drag with minimum size constraints, zoom-corrected coordinates
- `useConferenceRoom.ts` — React hook for LiveKit conference rooms: manages audio/video tracks, participant list, screen sharing, connection quality diagnostics
- `useIsMobile.ts` — React hook detecting mobile viewport: returns true when screen width ≤ 640px, uses matchMedia for efficient re-renders
- `useKeyboard.ts` — React hook for global keyboard shortcuts: maps number keys (1-9) and letter keys (q, etc.) to panel navigation, Cmd+K for command palette
- `useOrganismRealtime.ts` — React hook for organism WebSocket: connects to /ws/organism, distributes events to organismStore/systemStore/activityStore/chatStore/roomsStore
- `usePolling.ts` — React hook for interval-based polling: calls a callback at the specified interval with optional initial delay, cleans up on unmount
- `useVisionConnection.ts` — React hook managing the vision WebSocket lifecycle: connects to vision relay, handles camera control, object tracking, quality presets, auto-start logic
- `useVoiceDetection.ts` — React hook for wake-word and clap detection: listens for configurable wake words or loud clap sounds to activate voice recording
- `useVoiceRoom.ts` — React hook wrapping useConferenceRoom with voice-specific exports: re-exports conference room types and state for voice-only room panels

### cockpit/src/renderer/lib/
- `pushNotifications.ts` — Push notification helpers: checks browser support, subscribes to push via service worker, sends subscription to the API for server-side push delivery
- `rrip-normalize.ts` — RRIP message normalizer: converts raw ChatMessage objects into typed RRIPMessage format with role, kind, and metadata extraction
- `time.ts` — Time formatting utilities: `relativeTime()` returns human-readable durations ("5m ago"), `formatDuration()` converts milliseconds to readable strings

### cockpit/src/renderer/operator/
- `speechInputAdapter.ts` — Browser Speech Recognition adapter: wraps the Web Speech API for continuous speech-to-text, manages listening state, emits transcript segments
- `voiceTypes.ts` — TypeScript types for voice command state machine: VoiceCommandState ('idle'|'listening'|'processing'|...) and VoiceTranscript interface

### cockpit/src/renderer/panels/
- `ActionsPanel.tsx` — Panel listing available system actions: fetches action definitions from API, shows parameters, execute button, and result history
- `ActivityPanel.tsx` — Real-time activity feed: scrolling list of organism events color-coded by severity (info=cyan, warn=amber, error=red), auto-scrolls to latest
- `AnalyticsPanel.tsx` — Analytics dashboard: model usage ring gauges, signal volume mini-charts, cost breakdown, time-series data from analyticsStore
- `ApprovalsPanel.tsx` — Approval queue: lists pending governed mutations requiring human approval, with approve/reject/escalate actions and risk level badges
- `BroadcastPanel.tsx` — Device broadcast panel: shows connected mesh nodes, broadcast state (idle/starting/live), node health indicators, start/stop controls
- `BrowserPanel.tsx` — Remote browser panel: URL bar with back/forward/refresh, embedded browser stream via WebSocket, click/type interaction forwarding, full-screen toggle
- `BuildLoopPanel.tsx` — Build loop panel: shows active build loop status, iteration history, send-command interface, success/failure indicators
- `CapabilitiesPanel.tsx` — Capability registry panel: lists all 28 registered capabilities with status, category, dependency graph, and alert indicators
- `CapabilityMapPanel.tsx` — Visual capability map: shows capabilities organized by category with status indicators, copy-to-clipboard, and drill-down detail
- `CommandCenterPanel.tsx` — Primary command center: combines camera preview, operator chat, vision controls, and system status into the main operational view
- `CommandsPanel.tsx` — Command registry: lists all available commands (fetched from API), shows command ID, source, parameters, and execution interface
- `CommsPanel.tsx` — Communications panel: shows agent-to-agent conversation channels with message history and compose interface
- `CompanyPanel.tsx` — Company overview: displays venture data (name, stage, north star, KPIs) fetched from the API
- `ConferenceRoomsPanel.tsx` — Conference rooms panel: Discord-like UI with server rail, channel sidebar, main content area (text/forum/meeting), and right rail (members/chat/dex)
- `ContinuityPanel.tsx` — Operator continuity panel: tabbed view of objectives, active loops, pending approvals, and timeline for maintaining operational continuity
- `DashboardPanel.tsx` — Main dashboard: system health overview, pending approvals count, recent executions, organism status, quick-action buttons
- `DelegationPanel.tsx` — Delegation management: tabbed view of delegation proposals, active missions, and work queue with approve/reject controls
- `DistributedRuntimePanel.tsx` — Distributed runtime panel: tabbed topology/devices/workers/capacity/assignments view of the multi-device compute cluster
- `EngineeringPanel.tsx` — Engineering metrics: shows engineering plans, code quality indicators, risk assessment with color-coded severity levels
- `ExecCoordPanel.tsx` — Execution coordination: manages execution plans with start/stop controls, shows plan status and coordination state
- `ExecutionPanel.tsx` — Execution history: lists recent spine executions with status, duration, input/output, governance decisions, and timeline view
- `ExecutivePanel.tsx` — Executive overview: tabbed view of allocations, budgets, tradeoffs, and strategic drift analysis
- `ExecutorPanel.tsx` — Executor management: lists executor requests with status, shows executor capabilities and assignment history
- `GoalPanel.tsx` — Goal tracker: displays active goals with progress indicators, alert markers, refresh controls
- `GovernancePanel.tsx` — Governance panel: tabbed view of governance overview, conflicts, coordination state, knowledge, and health metrics
- `InfrastructurePanel.tsx` — Infrastructure status: shows system health (CPU, memory, disk), node status, Docker container states, and service dependencies
- `IntelligencePanel.tsx` — Intelligence overview: bottleneck evidence, coherence analysis, model routing status, and intelligence metrics
- `IntentPanel.tsx` — Intent registry: shows canonical intents organized by scope (empire/product/architecture/engineering/session) with real-time connection status
- `KnowledgePanel.tsx` — Knowledge management: observations, knowledge graph entries, skill registry, with search and add interfaces
- `LearningPanel.tsx` — Learning system: tabbed view of lessons learned, patterns detected, evolution tracking, and drift analysis
- `MVPReadinessPanel.tsx` — MVP readiness tracker: overview of blockers, escape points, and next steps with progress indicators
- `MemoryPanel.tsx` — Memory system panel: shows memory entries by type (episodic, semantic, procedural), with search, create, and detail views
- `MetaIDEPanel.tsx` — Meta-IDE panel: integrated code editor with file tree, terminal, git status, database browser, and deployment controls
- `OperatingLoopPanel.tsx` — Operating loop panel: shows active and completed operating loops with timing, status, and snapshot history
- `OperationsPanel.tsx` — Operations dashboard: real-time operational metrics from operationsStore with color-coded status indicators
- `OperatorContinuityPanel.tsx` — Operator continuity: shows device presence states with color-coded indicators for maintaining operator session continuity
- `OperatorHomePanel.tsx` — Operator home: status cards with severity-colored indicators, quick actions, and system overview for daily operator use
- `OperatorPanel.tsx` — Operator workstation: intent contracts, work packets, validation results, audit entries, and execution controls with collapsible sections
- `OperatorTimelinePanel.tsx` — Operator timeline: chronological view of operator actions and system events with type-colored markers
- `OrchestratorPanel.tsx` — Orchestrator awareness: tabbed context/health/score view of the orchestrator's self-awareness and decision-making state
- `OrganismLoopPanel.tsx` — Organism loop: shows the organism's autonomous loop cycles with status indicators and event history
- `OrganismMapPanel.tsx` — Organism topology map: visual map of workcells, connections, and health indicators using the organism canvas store
- `OrganismPanel.tsx` — Organism overview: spine execution stats, workcell status, daemon state, recent executions, governance decisions, with real-time updates
- `PortfolioPanel.tsx` — Portfolio panel: shows department-level data (name, stage, KPIs) across the venture portfolio
- `PredictionPanel.tsx` — Prediction engine: tabbed view of forecasts, scenarios, risk analysis, and confidence levels
- `PresencePanel.tsx` — Presence panel: shows whether the operator is present, device presence status, and session activity indicators
- `ProfilePanel.tsx` — Profile panel: operator profile with KPI cards showing key performance indicators
- `ProjectionIntegrationPanel.tsx` — Projection integration: shows integration status of projections (EOS, CreatorOS, LyfeOS) with health checks and refresh controls
- `ProjectionPanel.tsx` — Projection metrics: trending up/down indicators, alerts, and performance data for active projections
- `ProofInspectorPanel.tsx` — Proof inspector: tabbed view of proof packages with overview, detail, timeline, evidence, and raw data views
- `PropagationGraphPanel.tsx` — Propagation graph: visualizes how changes propagate through the organism with connection lines and node status
- `RealityGraphPanel.tsx` — Reality graph: tabbed view of entities, artifact resolution, files, docs, runtime state, and knowledge in the reality model
- `RealityIntelligencePanel.tsx` — Reality intelligence: displays reality evidence entries with source-type-colored badges
- `RealityTimelinePanel.tsx` — Reality timeline: chronological view of reality observations with source-colored markers and polling updates
- `RecoveryDashboardPanel.tsx` — Recovery dashboard: tabbed view of recovery queue, action details, action execution, and recovery history
- `RuntimePanel.tsx` — Runtime overview: shows total sessions, active runtimes, resource usage, and runtime health metrics
- `ScreenAwarenessPanel.tsx` — Screen awareness: displays focused application information and screen context from the screenAwarenessStore
- `SelfBuildPanel.tsx` — Self-build panel: shows the organism's self-improvement loop with active builds, operator loop integration, and build history
- `ServiceGraphPanel.tsx` — Service dependency graph: visualizes service nodes with criticality-colored indicators and dependency connections
- `SessionPanel.tsx` — Session management: KPI cards for session metrics, session history, and session configuration
- `SessionResumePanel.tsx` — Session resume: tabbed active/history view of workstation sessions with save/resume/pause controls
- `SettingsPanel.tsx` — Settings panel: model routing configuration, device management (Tailscale peers), AI name configuration, and system preferences
- `SkillsPanel.tsx` — Skills registry panel: lists registered skills from knowledgeStore with polling for updates
- `StateAuthorityPanel.tsx` — State authority panel: shows state authority registrations with status indicators and criticality coloring
- `StrategicPanel.tsx` — Strategic overview: compass-oriented strategic analysis with alerts, refresh controls, and priority indicators
- `StrategyPanel.tsx` — Strategy panel: trending metrics, alerts, and strategic goal tracking with drill-down capabilities
- `TasksPanel.tsx` — Task list panel: renders TaskBlock components from taskStore with polling for live updates
- `TickLoopPanel.tsx` — Tick loop panel: shows the organism's tick-based execution loop with play/pause controls and iteration metrics
- `TmuxPanel.tsx` — Tmux panel: remote terminal sessions via API with connection status banner and polling for session output
- `UMHNodePanel.tsx` — UMH node panel: shows registered UMH nodes with service status indicators and collapsible details
- `UnifiedExecutionPanel.tsx` — Unified execution panel: merged view of all execution pipelines with play/pause controls and execution history
- `UniversalWorkPanel.tsx` — Universal work panel: combined view of work items from all sources with operator loop integration and connection status
- `VisionPanel.tsx` — Vision panel: camera controller, vision feed, and vision overlay controls integrated into a dedicated panel view
- `WorkIntelligencePanel.tsx` — Work intelligence: success/failure indicators, work pattern analysis, and task completion insights
- `WorkPanel.tsx` — Work management: cron job table, work item details in a slide-out drawer, with view context filtering
- `WorkspaceTopologyPanel.tsx` — Workspace topology: read-only visualization of workspace→repos→runtimes→devices relationships with health indicators
- `WorkstationPanel.tsx` — Workstation preparation: tabbed view of preparation checklists, templates, snapshots, restoration, and recommendations
- `WorldModelPanel.tsx` — World model: shows canonical patterns, beliefs, and world-state assertions with confidence-colored indicators

### cockpit/src/renderer/stores/
- `actionsStore.ts` — Zustand store for system actions: fetches action definitions from API, tracks action parameters and execution results
- `activityStore.ts` — Zustand store for activity feed: fetches and stores organism activity events with severity levels
- `agentCanvasStore.ts` — Zustand store for agent canvas: persists agent node positions, sizes, and states with pan/zoom for the agent canvas workspace
- `agentStore.ts` — Zustand store for agents: fetches agent list from API, tracks agent status, roles, skills, and runtime assignments
- `analyticsStore.ts` — Zustand store for analytics: fetches model usage, signal volume, and cost data from API for the analytics panel
- `bootstrapStore.ts` — Zustand store for app bootstrap: persists initial setup state, fetches bootstrap config from API, manages hydration
- `broadcastStore.ts` — Zustand store for broadcast: tracks broadcast state (idle/starting/live/stopping/error), connected nodes, health tier
- `buildLoopStore.ts` — Zustand store for build loops: fetches build loop state from API, tracks iterations and results
- `canvasStore.ts` — Zustand store for general canvas: persists window positions/sizes, pan/zoom state, z-order for the canvas workspace
- `capabilityIntelligenceStore.ts` — Zustand store for capability intelligence: fetches and stores capability health, bottleneck, and optimization data
- `capabilityMapStore.ts` — Zustand store for capability map: fetches capability registry with categories and status for visual mapping
- `chatStore.ts` — Zustand store for operator↔DEX chat: manages message history with provenance, multimodal file attachments (image/video upload, paste, preview, inline display), send/receive, and conversation state
- `cockpitStore.ts` — Zustand store for cockpit UI state: persists active panel, chat open/closed, split panel, window mode, rail collapsed, drawer states, canvas mode, and mobile viewport detection
- `coherenceStore.ts` — Zustand store for coherence analysis: fetches template summaries and coherence drift data from API
- `collapseStore.ts` — Zustand store for collapsible UI sections: persists which panels/sections are collapsed across sessions
- `configStore.ts` — Zustand store for UMH configuration: fetches AI name, system config, and runtime settings from API
- `delegationStore.ts` — Zustand store for delegation: fetches delegation proposals, missions, and queue from API
- `deviceSessionStore.ts` — Zustand store for device presence session: registers device, sends heartbeats, tracks voice route info and session ID
- `deviceStore.ts` — Zustand store for devices: fetches registered devices and Tailscale peers, manages device diagnosis and onboarding state
- `editorStore.ts` — Zustand store for Meta-IDE editor: fetches file tree from API, manages open files, active file, and file content
- `engineeringStore.ts` — Zustand store for engineering metrics: fetches engineering plans and code quality data with risk-colored indicators
- `executionSummaryStore.ts` — Zustand store for execution summary: fetches "what is happening" overview data for the execution panel
- `executiveStore.ts` — Zustand store for executive data: fetches allocation recommendations and strategic analysis from API
- `goalStore.ts` — Zustand store for goals: fetches and tracks active goals with progress and alert states
- `governanceStore.ts` — Zustand store for governance: fetches subsystem conflicts, coordination state, and governance health from API
- `harnessCanvasStore.ts` — Zustand store for harness canvas: persists runtime node positions and connections, fetches topology from API
- `intelligenceStore.ts` — Zustand store for intelligence: fetches bottleneck evidence and intelligence metrics from API
- `intentStore.ts` — Zustand store for canonical intents: fetches intent registry organized by scope from API
- `knowledgeStore.ts` — Zustand store for knowledge: fetches observations, knowledge graph, and skill registry from API
- `learningStore.ts` — Zustand store for learning system: fetches lessons, patterns, and evolution data from API
- `loopCanvasStore.ts` — Zustand store for loop canvas: persists loop node positions and execution state with pan/zoom
- `memoryStore.ts` — Zustand store for memory system: fetches memory entries by type from API
- `metaIDEStore.ts` — Zustand store for Meta-IDE: fetches repository health data from API
- `mvpReadinessStore.ts` — Zustand store for MVP readiness: fetches readiness assessment data from API
- `operatingLoopStore.ts` — Zustand store for operating loops: fetches active and completed loop data from API
- `operationsStore.ts` — Zustand store for operations: fetches operational metrics and status from API
- `operatorExperienceStore.ts` — Zustand store for operator experience: manages speech input adapter integration and operator interaction state
- `operatorHomeStore.ts` — Zustand store for operator home: fetches status cards and quick-action data from API
- `operatorLoopStore.ts` — Zustand store for operator loop: fetches loop status, intent contracts, work packets, validation results, and audit entries from API
- `operatorTimelineStore.ts` — Zustand store for operator timeline: fetches chronological timeline entries from API
- `orchestratorAwarenessStore.ts` — Zustand store for orchestrator awareness: fetches orchestrator self-model context, health, and score from API
- `organismCanvasStore.ts` — Zustand store for organism canvas: persists topology node/edge positions, fetches organism topology from API
- `organismLoopStore.ts` — Zustand store for organism loop: fetches cycle event data and loop state from API
- `organismStore.ts` — Zustand store for organism state: fetches spine stats, workcell status, daemon state, governance decisions, recent executions from API
- `predictionStore.ts` — Zustand store for predictions: fetches forecast data and scenario analysis from API
- `presenceStore.ts` — Zustand store for presence: fetches operator and device presence status from API
- `projectionIntegrationStore.ts` — Zustand store for projection integration: fetches projection health and integration status from API
- `proofInspectorStore.ts` — Zustand store for proof inspector: fetches proof packages with detail, timeline, and evidence from API
- `providerRegistryStore.ts` — Zustand store for provider registry: fetches registered AI/service providers from API
- `realityGraphStore.ts` — Zustand store for reality graph: fetches reality entities and their relationships from API
- `realityIntelligenceStore.ts` — Zustand store for reality intelligence: fetches reality evidence observations from API
- `realityTimelineStore.ts` — Zustand store for reality timeline: fetches chronological reality observations from API
- `realtimeStore.ts` — Zustand store for real-time WebSocket: manages connection status, event stream, events per minute, GPU metrics, reconnect state
- `recoveryDashboardStore.ts` — Zustand store for recovery: fetches recovery actions, queue, and history from API
- `roomsStore.ts` — Zustand store for conference rooms: manages servers, channels, messages, threads, members, invites, and DEX mode with full CRUD operations
- `screenAwarenessStore.ts` — Zustand store for screen awareness: fetches focused application and screen context from API
- `serviceGraphStore.ts` — Zustand store for service graph: fetches service nodes with criticality levels from API
- `settingsStore.ts` — Zustand store for settings: fetches and updates model routes, system preferences, and AI configuration from API
- `stateAuthorityStore.ts` — Zustand store for state authority: fetches state authority registrations and status from API
- `strategicStore.ts` — Zustand store for strategic data: fetches strategic analysis and priority data from API
- `systemStore.ts` — Zustand store for system health: fetches node GPU metrics, CPU/memory/disk stats, Docker container status, and service health from API
- `taskStore.ts` — Zustand store for tasks: fetches task list with status (pending/in_progress/completed/blocked), agent assignments, and timestamps from API
- `umhNodeStore.ts` — Zustand store for UMH nodes: fetches registered UMH node services and status from API
- `unifiedApprovalStore.ts` — Zustand store for approvals: fetches unified approval queue (governed mutations requiring human action) from API
- `unifiedCanvasStore.ts` — Zustand store for canvas mode: persists which canvas mode is active (general/agents/workflows/loops/harnesses/organism)
- `unifiedExecutionStore.ts` — Zustand store for unified execution: fetches merged execution data from all pipelines from API
- `unifiedWorkstationStore.ts` — Zustand store for workstation: fetches overnight status, workstation health, and operational readiness from API
- `viewContextStore.ts` — Zustand store for view context: tracks which panel is active and provides context for view-specific filtering
- `visionStore.ts` — Zustand store for vision: manages camera state, overlay metadata, tracked objects, quality profiles, stream metrics, security notifications, presets
- `voiceSessionStore.ts` — Zustand store for voice sessions: manages LiveKit room connection, participant tracks, mute/deafen state, call duration
- `voiceStore.ts` — Zustand store for voice: manages mic state (idle/listening/processing/speaking), audio level, transcript, wake-word detection state
- `workIntelligenceStore.ts` — Zustand store for work intelligence: fetches work pattern analysis and completion insights from API
- `workflowCanvasStore.ts` — Zustand store for workflow canvas: persists workflow nodes and connections with pan/zoom for the visual workflow editor
- `workspaceContextStore.ts` — Zustand store for workspace context: persists active workspace selection, fetches workspace list from API
- `workspaceTopologyStore.ts` — Zustand store for workspace topology: fetches workspace→repo→runtime→device topology from API
- `workstationSessionStore.ts` — Zustand store for workstation sessions: fetches active and historical workstation session data from API
- `worldModelStore.ts` — Zustand store for world model: fetches canonical patterns, beliefs, and world-state assertions from API

### cockpit/src/renderer/types/
- `rooms.ts` — TypeScript types for the conference rooms system: ChannelType, ServerCategory, RoomMessage, ForumPost, PresenceStatus, GuestPermissions, DexRoomMode, and more
- `routes.ts` — Route definitions mapping panel names to icons and labels: imports Lucide icons, defines ROUTES array and ROUTE_GROUPS for LeftRail navigation
- `rrip.ts` — TypeScript types for the RRIP message protocol: RRIPRole (operator/dex/system/agent/external), RRIPKind (conversation/command_result/work_report/...), RRIPMessage, RRIPSuggestedAction

### cockpit/src/renderer/utils/
- `canvasCoords.ts` — Canvas coordinate math utilities: `screenToCanvas()` converts screen coordinates to canvas space, `zoomAtPoint()` adjusts zoom around a focal point, `clampZoom()` enforces min/max zoom limits

### skills/ — Skill Definitions and SaaS Dev Pipeline (131 files)

### skills/meta/tool_mastery_engine/scripts/
- `scaffold_tool_skill.py` — Scaffolds a new tool skill directory from the canonical template (creates SKILL.md and references/best_practices.md)

### skills/saas-dev-skill/.claude/skills/saas-dev/scripts/
- `setup.ts` — First-run setup script for saas-dev skill — validates prerequisites, creates .planning/ structure, checks DB connection
- `verify.ts` — Health check script for saas-dev skill — reports on environment, DB, and pipeline readiness

### skills/saas-dev-skill/lib/agents/
- `agent-runner.ts` — Spawns, coordinates, and manages agent lifecycle with retries, exponential backoff, and progress reporting
- `architecture-agent.ts` — Designs complete system architecture from a ProjectBrief and ProductInsights — outputs SystemArchitecture artifact
- `artifact-store.ts` — Central typed artifact store for inter-agent communication — persists as JSON under .planning/artifacts/
- `backend-agent.ts` — Generates Express route handlers, storage methods, and Drizzle schemas from SystemArchitecture
- `component-library-agent.ts` — Builds all shared components with design system context, extracts TypeScript interfaces for downstream page agents
- `copy-agent.ts` — Orchestrates brand voice loading, copy generation, and copy review via copy-planner and brand-voice-inferrer
- `design-system-agent.ts` — Generates product-specific design tokens, CSS custom properties, Tailwind config, and component design guide
- `page-agent.ts` — Wraps component-writer with full ArtifactStore context — delegates generation, validation, review, and tsc checks
- `pm-orchestrator.ts` — Coordinates intake, all build agents, live preview, and progress — runs agents in dependency-ordered waves
- `product-intel-agent.ts` — Wraps competitive researcher and adds product analysis layer — produces ProductInsights for downstream agents
- `qa-agent.ts` — Validates entire project after all agents complete — runs tsc, import validation, null-safety, and state-pattern checks
- `types.ts` — Shared TypeScript interfaces for the v3 multi-agent architecture — all agents communicate through these types

### skills/saas-dev-skill/lib/analytics-delivery/
- `analytics-injector.ts` — Injects PostHog analytics event calls into generated React components based on taxonomy
- `deploy-runner.ts` — Runs deployment commands for Fly.io, Vercel, and Railway with preflight checks and rollback
- `docker-config-generator.ts` — Generates multi-stage Dockerfiles for all hosting targets (Vite client + esbuild server)
- `env-scanner.ts` — Scans codebase for environment variable usage and produces an inventory for deployment config
- `github-actions-generator.ts` — Generates CI/CD GitHub Actions workflows with shared setup steps for build and deploy
- `posthog-setup.ts` — Checks and configures PostHog analytics setup — verifies API key, project, and event taxonomy
- `taxonomy-auditor.ts` — Audits analytics event taxonomy against spec — ensures all user-facing actions have tracking
- `types.ts` — Zod schemas and TypeScript types for analytics delivery (TaxonomyReport, DeployConfig, HostingTarget)

### skills/saas-dev-skill/lib/backend-wirer/
- `brownfield-backend-audit.ts` — Audits existing backend code to build an inventory of routes, schemas, and storage methods
- `codex-adversarial.ts` — Adversarial code review via Claude — validates generated routes and schemas against spec
- `hook-injector.ts` — Injects React Query hooks into frontend pages to connect them to generated backend endpoints
- `migration-runner.ts` — Writes and executes Drizzle ORM SQL migration files from generated schema changes
- `route-generator.ts` — Generates Express route handler code from BackendEndpointSpec definitions
- `schema-generator.ts` — Generates Drizzle ORM pgTable schema code from data model definitions
- `tdd-skill.ts` — Generates test files via Claude for backend routes before implementation (test-driven development)
- `types.ts` — Zod schemas and types for backend wiring (BackendSpec, RouteCodeBlock, SchemaCodeBlock, WiringPlan)
- `wiring-applier.ts` — Applies generated routes, schemas, and hooks to the existing codebase without breaking imports

### skills/saas-dev-skill/lib/copy-planner/
- `copy-reviewer.ts` — Reviews all project copy at once for cross-page voice consistency and brand compliance via Claude
- `copy-writer.ts` — Generates all UI copy for a project in one Claude call for cross-page voice coherence
- `types.ts` — Zod schemas for copy planning (PageCopy, CopyReview, BrandVoice)

### skills/saas-dev-skill/lib/intake/
- `codebase-scanner.ts` — Scans an existing codebase to extract what already exists (routes, components, schemas, packages)
- `competitive-researcher.ts` — Researches competitor websites to extract copy patterns, UX flows, and competitive intelligence
- `doc-scanner.ts` — Scans .planning/ directory for existing documentation and reads all files for context
- `intake-orchestrator.ts` — Unified intake phase — collects everything needed before generation and produces a ProjectBrief
- `mode-detector.ts` — Detects which intake mode to use (greenfield vs brownfield) based on filesystem state
- `types.ts` — Zod schemas for unified intake phase (ProjectBrief, CompetitorAnalysis, CodebaseSnapshot)

### skills/saas-dev-skill/lib/orchestrator/
- `approval-gate.ts` — Approval gate handling — formats approval messages for Claude to relay to the human operator
- `context-detector.ts` — Determines current pipeline position so the orchestrator can skip completed phases
- `db.ts` — Postgres-backed state for pipeline runs — wraps pipeline_runs and pipeline_pages tables (never JSON files)
- `index.ts` — Pipeline spine — loads config, detects state, runs phases in order with per-page Postgres checkpointing
- `phase-runner.ts` — Generic per-page phase runner — accepts a PhaseImplementation and handles retry/checkpoint bookkeeping

### skills/saas-dev-skill/lib/react-gen/
- `build-status-overlay.ts` — Injects a build progress overlay into running Vite app — communicates via public/build-status.json
- `component-writer.ts` — Generates a single production-ready React/TypeScript page component using Claude with design validation
- `design-linter.ts` — Programmatic checker that scans component code for design system violations before writing to disk
- `design-tokens.ts` — Design token constants and mandatory rules enforced in every generated component (colors, spacing, typography)
- `edit-mode.ts` — Post-build surgical file-level component updates with instant Vite preview and full validation pipeline
- `live-preview-server.ts` — Ensures a Vite dev server is running for live preview during generation — pages hot-reload automatically
- `screenshot-reviewer.ts` — Playwright-based screenshot capture + Claude vision quality gate — scores against design rules
- `shared-component-builder.ts` — Builds shared layout components before pages (sequential — each can import the previous)
- `skill-loader.ts` — Loads design-relevant skill content from ~/.claude/skills/ and .claude/skills/ for injection into prompts

### skills/saas-dev-skill/lib/spec-parser/
- `brand-voice-inferrer.ts` — Infers brand voice from a PRD/spec document via Claude — writes to .planning/BRAND-VOICE.md
- `chunk-spec.ts` — Splits a large spec into per-page chunks for parallel processing by downstream agents
- `collaborative-flow.ts` — Interactive spec refinement flow — Claude asks clarifying questions, user answers, spec improves
- `deduplicate-components.ts` — Identifies and merges duplicate shared components across pages via Claude analysis
- `derive-backend-spec.ts` — Derives backend API specification from frontend page specs via Claude
- `gap-analyzer.ts` — Analyzes draft SpecOutput for missing pages, flows, states, and assumptions (static + LLM checks)
- `parse-spec.ts` — Entry point for spec parsing — orchestrates restructuring, chunking, and validation
- `restructure-spec.ts` — Restructures raw PRD text into structured SpecOutput format via Claude with Zod validation
- `spec-approval.ts` — Formats GapAnalysis as a human-readable report for the approval gate
- `spec-editor.ts` — Applies targeted edits to an existing SpecOutput (add/remove/modify pages and components)
- `types.ts` — Re-exports from shared/spec-schema.ts for use within spec-parser modules

### skills/saas-dev-skill/lib/ (root)
- `claude-subprocess.ts` — Drop-in replacement for @anthropic-ai/sdk — routes all LLM calls through `claude -p` subprocess
- `detect-framework.ts` — Detects project framework (currently React+Vite+Tailwind+shadcn) from package.json and file structure
- `env.ts` — Single source of truth for all environment variables used in lib/ — never read process.env directly
- `project-config.ts` — Loads and validates project config from .planning/project.config.json — throws if missing

### skills/saas-dev-skill/scripts/
- `saas-dev-build.ts` — Single entry point for SaaS dev pipeline (v3 multi-agent architecture) — supports --resume
- `saas-dev-fix.ts` — Targeted fix script — re-runs only failed or low-quality phases, skips completed artifacts

### skills/saas-dev-skill/shared/
- `design-schema.ts` — Drizzle ORM table definitions for design memory (pipeline_runs, pipeline_pages, design sessions)
- `spec-schema.ts` — Zod schemas for spec parsing — PageSpec, SharedComponentSpec, BackendSpec, SpecOutput with provenance tracking

### skills/saas-dev-skill/tests/unit/agents/
- `agent-runner.test.ts` — Tests for agent lifecycle management (spawn, retry, backoff, progress)
- `architecture-agent.test.ts` — Tests for architecture agent artifact generation
- `artifact-store.test.ts` — Tests for artifact store read/write/persist operations
- `design-system-agent.test.ts` — Tests for design system generation output
- `page-agent.test.ts` — Tests for page component generation and validation
- `pm-orchestrator.test.ts` — Tests for PM orchestrator wave execution and state management
- `qa-agent.test.ts` — Tests for QA validation pipeline (tsc, imports, null-safety)

### skills/saas-dev-skill/tests/unit/analytics-delivery/
- `analytics-injector.test.ts` — Tests for PostHog event injection into React components
- `deploy-runner.test.ts` — Tests for deployment command execution and preflight checks
- `docker-config-generator.test.ts` — Tests for Dockerfile generation across hosting targets
- `env-scanner.test.ts` — Tests for environment variable scanning and inventory
- `github-actions-generator.test.ts` — Tests for CI/CD workflow generation
- `posthog-setup.test.ts` — Tests for PostHog configuration validation
- `taxonomy-auditor.test.ts` — Tests for analytics event taxonomy auditing

### skills/saas-dev-skill/tests/unit/backend-wirer/
- `brownfield-backend-audit.test.ts` — Tests for existing backend inventory scanning
- `codex-adversarial.test.ts` — Tests for adversarial code review validation
- `hook-injector.test.ts` — Tests for React Query hook injection into pages
- `migration-runner.test.ts` — Tests for SQL migration file generation and execution
- `route-generator.test.ts` — Tests for Express route handler generation
- `schema-generator.test.ts` — Tests for Drizzle schema code generation
- `types.test.ts` — Tests for backend wiring Zod schema validation
- `wiring-applier.test.ts` — Tests for applying generated code without breaking imports

### skills/saas-dev-skill/tests/unit/code-integrator/
- `brownfield-audit.test.ts` — Tests for brownfield codebase audit accuracy
- `brownfield-planner.test.ts` — Tests for brownfield integration planning
- `codex-review.test.ts` — Tests for code review pass validation
- `git-workflow.test.ts` — Tests for git branch and commit workflow
- `html-to-shadcn.test.ts` — Tests for HTML to shadcn/ui component conversion
- `nav-injector.test.ts` — Tests for navigation menu injection into layouts
- `page-writer.test.ts` — Tests for page file writing and import management
- `route-injector.test.ts` — Tests for router configuration injection

### skills/saas-dev-skill/tests/unit/copy-planner/
- `copy-reviewer.test.ts` — Tests for cross-page copy consistency review
- `copy-writer.test.ts` — Tests for UI copy generation coherence

### skills/saas-dev-skill/tests/unit/ (root)
- `design-schema.test.ts` — Tests for design memory Drizzle schema validation
- `detect-framework.test.ts` — Tests for framework detection accuracy

### skills/saas-dev-skill/tests/unit/intake/
- `competitive-researcher.test.ts` — Tests for competitor website analysis
- `intake-orchestrator.test.ts` — Tests for unified intake phase orchestration
- `mode-detector.test.ts` — Tests for greenfield vs brownfield detection

### skills/saas-dev-skill/tests/unit/orchestrator/
- `copy-adapter.test.ts` — Tests for copy agent adapter integration
- `deploy-adapter-inject-import.test.ts` — Tests for deploy adapter import injection
- `integration-adapter-name-matching.test.ts` — Tests for integration adapter name matching logic
- `phase-runner-hook.test.ts` — Tests for phase runner hook execution
- `react-gen-adapter.test.ts` — Tests for React generation adapter integration

### skills/saas-dev-skill/tests/unit/react-gen/
- `component-writer.test.ts` — Tests for React component generation and validation
- `design-linter.test.ts` — Tests for design system violation detection
- `design-tokens.test.ts` — Tests for design token constant validation
- `screenshot-reviewer.test.ts` — Tests for Playwright screenshot quality gate
- `shared-component-builder.test.ts` — Tests for shared component sequential build
- `skill-loader.test.ts` — Tests for skill content loading and caching

### skills/saas-dev-skill/tests/unit/spec-parser/
- `brand-voice-inferrer.test.ts` — Tests for brand voice inference from PRD
- `chunk-spec.test.ts` — Tests for spec chunking into per-page segments
- `collaborative-flow.test.ts` — Tests for interactive spec refinement flow
- `deduplicate-components.test.ts` — Tests for shared component deduplication
- `derive-backend-spec.test.ts` — Tests for backend spec derivation from frontend specs
- `gap-analyzer.test.ts` — Tests for spec gap analysis (missing pages, flows, states)
- `parse-spec.test.ts` — Tests for end-to-end spec parsing pipeline
- `restructure-spec.test.ts` — Tests for raw PRD to structured SpecOutput conversion
- `spec-editor.test.ts` — Tests for targeted spec editing operations

---

### data/ — Trinity App Repo Snapshots + Misc Data Scripts (154 files)

These are snapshot copies of the three Trinity SaaS applications (EntrepreneurOS, CreatorOS, LyfeOS). They serve as reference implementations and schema sources — not actively developed here.

### data/ (root)
- `notion_datasource_ids.sh` — Notion data source IDs resolved from database IDs via ntn CLI (generated 2026-05-17, used for ntn datasources queries)

### data/repos/LYFEOS/
- `build.sh` — simple build script: runs npm install + npm run build
- `drizzle.config.ts` — Drizzle ORM configuration pointing to LyfeOS database
- `postcss.config.js` — PostCSS configuration with Tailwind CSS plugin
- `tailwind.config.ts` — Tailwind CSS theme configuration for LyfeOS
- `vite.config.ts` — Vite build configuration for LyfeOS
- `vitest.config.ts` — Vitest test runner configuration for LyfeOS

### data/repos/LYFEOS/scripts/
- `kill-port.sh` — kills any process on port 5000 (dev server cleanup)
- `capture-screenshots.ts` — Playwright script to capture screenshots of all LyfeOS pages for visual regression
- `seed-demo-user.ts` — Seeds a demo user with sample data for LyfeOS development/testing

### data/repos/LYFEOS/shared/
- `schema.ts` — Drizzle ORM database schema for LyfeOS (users, XP, achievements, habits, journal)

### data/repos/LYFEOS/shared/models/
- `chat.ts` — Chat message types for LyfeOS AI conversation feature

### data/repos/LYFEOS/tests/
- `api-auth.test.ts` — API authentication endpoint tests for LyfeOS
- `xp-calculations.test.ts` — XP (experience points) calculation logic tests for LyfeOS gamification

### data/repos/creatoros/
- `drizzle.config.ts` — Drizzle ORM configuration pointing to CreatorOS database
- `postcss.config.js` — PostCSS configuration with Tailwind CSS plugin
- `tailwind.config.ts` — Tailwind CSS theme configuration for CreatorOS
- `vite.config.ts` — Vite build configuration for CreatorOS

### data/repos/creatoros/scripts/
- `seed-db.ts` — Seeds the CreatorOS database with initial data for development

### data/repos/creatoros/shared/
- `schema.ts` — Drizzle ORM database schema for CreatorOS (creators, content, analytics, subscriptions)

### data/repos/entrepreneuros/
- `drizzle.config.ts` — Drizzle ORM configuration pointing to EntrepreneurOS database
- `llmApi.ts` — LLM API client for EntrepreneurOS — wraps multiple AI providers (OpenAI, Anthropic, Gemini)
- `postcss.config.js` — PostCSS configuration with Tailwind CSS plugin
- `tailwind.config.ts` — Tailwind CSS theme configuration for EntrepreneurOS
- `vite.config.ts` — Vite build configuration for EntrepreneurOS

### data/repos/entrepreneuros/client/src/
- `App.tsx` — Root React component with route definitions (Dashboard, TaskBoard, AgentChat, CRM, Settings, etc.)
- `main.tsx` — React DOM entry point — mounts App component to #root element

### data/repos/entrepreneuros/client/src/components/
- `action-approval-panel.tsx` — UI panel for approving/rejecting AI-proposed actions before execution
- `agent-card.tsx` — Card component displaying an AI agent's name, status, capabilities, and metrics
- `agent-metrics.tsx` — Dashboard metrics for agent performance (tasks completed, success rate, response time)
- `ai-fab.tsx` — Floating action button for triggering AI assistant from any page
- `ai-model-selector.tsx` — Dropdown selector for choosing AI model (GPT-4, Claude, Gemini, etc.)
- `api-key-dialog.tsx` — Dialog for entering and validating API keys for AI providers
- `create-agent-form.tsx` — Form for configuring a new AI agent (name, role, model, instructions)
- `create-agent-modal.tsx` — Modal wrapper around create-agent-form with save/cancel actions
- `direct-gpt4o-chat.tsx` — Direct chat interface with GPT-4o model (bypasses agent layer)
- `gmail-connect-button.tsx` — OAuth button for connecting Gmail integration to EntrepreneurOS
- `header.tsx` — Top navigation header with user menu, notifications, and search
- `integrations.tsx` — Integration management panel listing connected services (Gmail, Slack, etc.)
- `layout.tsx` — Main application layout with sidebar, header, and content area
- `notification-dropdown.tsx` — Dropdown showing recent notifications with read/unread state
- `performance-analytics.tsx` — Charts and metrics for overall business performance analytics
- `sidebar.tsx` — Left navigation sidebar with page links and agent shortcuts
- `sop-template-button.tsx` — Button that generates Standard Operating Procedure templates via AI
- `stats-overview.tsx` — Dashboard overview cards showing key business statistics
- `task-board.tsx` — Kanban-style task board with drag-and-drop columns (To Do, In Progress, Done)
- `task-card.tsx` — Individual task card showing title, assignee, priority, and due date

### data/repos/entrepreneuros/client/src/components/ui/
- `accordion.tsx` — shadcn/ui accordion component (collapsible content sections)
- `alert-dialog.tsx` — shadcn/ui alert dialog (confirmation modal with destructive action support)
- `alert.tsx` — shadcn/ui alert component (info, warning, error banners)
- `aspect-ratio.tsx` — shadcn/ui aspect ratio container (maintains width:height ratio)
- `avatar.tsx` — shadcn/ui avatar component (user profile image with fallback initials)
- `badge.tsx` — shadcn/ui badge component (small status/category labels)
- `breadcrumb.tsx` — shadcn/ui breadcrumb navigation component
- `button.tsx` — shadcn/ui button component (primary, secondary, destructive, outline, ghost variants)
- `calendar.tsx` — shadcn/ui calendar date picker component
- `card.tsx` — shadcn/ui card component (container with header, content, footer)
- `carousel.tsx` — shadcn/ui carousel component (horizontal scrolling content)
- `chart.tsx` — shadcn/ui chart wrapper component (Recharts integration with theme support)
- `checkbox.tsx` — shadcn/ui checkbox input component
- `collapsible.tsx` — shadcn/ui collapsible component (expandable/collapsible section)
- `command.tsx` — shadcn/ui command palette component (searchable command menu)
- `context-menu.tsx` — shadcn/ui context menu (right-click menu)
- `dialog.tsx` — shadcn/ui dialog component (modal overlay)
- `drawer.tsx` — shadcn/ui drawer component (slide-in panel from screen edge)
- `dropdown-menu.tsx` — shadcn/ui dropdown menu component
- `form.tsx` — shadcn/ui form component (react-hook-form integration with validation)
- `hover-card.tsx` — shadcn/ui hover card (tooltip-like popover on hover)
- `input-otp.tsx` — shadcn/ui OTP input component (one-time password entry)
- `input.tsx` — shadcn/ui text input component
- `label.tsx` — shadcn/ui label component (form field labels)
- `menubar.tsx` — shadcn/ui menubar component (horizontal menu with dropdowns)
- `navigation-menu.tsx` — shadcn/ui navigation menu component (complex nav with submenus)
- `pagination.tsx` — shadcn/ui pagination component (page navigation controls)
- `popover.tsx` — shadcn/ui popover component (floating content panel)
- `progress.tsx` — shadcn/ui progress bar component
- `radio-group.tsx` — shadcn/ui radio group component (single-select options)
- `resizable.tsx` — shadcn/ui resizable panels component (draggable dividers)
- `scroll-area.tsx` — shadcn/ui scroll area component (custom scrollbar)
- `select.tsx` — shadcn/ui select component (dropdown selection)
- `separator.tsx` — shadcn/ui separator component (horizontal/vertical divider)
- `sheet.tsx` — shadcn/ui sheet component (side panel overlay)
- `sidebar.tsx` — shadcn/ui sidebar component (responsive navigation sidebar)
- `skeleton.tsx` — shadcn/ui skeleton component (loading placeholder animation)
- `slider.tsx` — shadcn/ui slider component (range input)
- `switch.tsx` — shadcn/ui switch component (toggle on/off)
- `table.tsx` — shadcn/ui table component (data table with header, body, footer)
- `tabs.tsx` — shadcn/ui tabs component (tabbed content sections)
- `textarea.tsx` — shadcn/ui textarea component (multi-line text input)
- `toast.tsx` — shadcn/ui toast component (temporary notification popup)
- `toaster.tsx` — shadcn/ui toaster provider (manages toast notification stack)
- `toggle-group.tsx` — shadcn/ui toggle group component (multi-select toggle buttons)
- `toggle.tsx` — shadcn/ui toggle component (pressed/unpressed state button)
- `tooltip.tsx` — shadcn/ui tooltip component (hover text hint)

### data/repos/entrepreneuros/client/src/hooks/
- `use-ai-api-keys.ts` — React hook for managing AI provider API keys (CRUD operations via React Query)
- `use-ai-models.ts` — React hook for fetching and selecting available AI models
- `use-auth.tsx` — React hook and context provider for authentication state (login, logout, current user)
- `use-mobile.tsx` — React hook for detecting mobile viewport (responsive layout switching)
- `use-notifications.tsx` — React hook for fetching, marking read, and managing notification state
- `use-toast.ts` — React hook for triggering toast notifications programmatically

### data/repos/entrepreneuros/client/src/lib/
- `firebase.ts` — Firebase SDK initialization for EntrepreneurOS (auth, Firestore)
- `llmApi.ts` — Client-side LLM API wrapper for sending prompts to the server
- `openai.ts` — Direct OpenAI SDK client initialization for client-side features
- `protected-route.tsx` — Route guard component that redirects unauthenticated users to login
- `queryClient.ts` — React Query client configuration (retry, stale time, cache settings)
- `utils.ts` — Utility functions (cn() classname merger via clsx + tailwind-merge)

### data/repos/entrepreneuros/client/src/pages/
- `agent-chat.tsx` — Chat interface page for conversing with AI agents
- `agent-os-dashboard.tsx` — Agent OS dashboard showing all agents, their status, and quick actions
- `agent-programming.tsx` — Page for programming agent behavior (instructions, tools, knowledge)
- `analytics-page.tsx` — Business analytics page with charts for revenue, engagement, and growth
- `auth-page.tsx` — Login/register page with email/password authentication
- `crm-page.tsx` — Customer Relationship Management page (contacts, deals, pipeline)
- `dashboard.tsx` — Main dashboard with overview stats, recent activity, and quick actions
- `documents-page.tsx` — Document management page (create, edit, organize business documents)
- `gpt4o-chat-page.tsx` — Direct GPT-4o chat page (standalone AI conversation without agent layer)
- `integrations-page.tsx` — Integration management page (connect/disconnect third-party services)
- `not-found.tsx` — 404 Not Found page
- `notifications-page.tsx` — Full notifications page with filtering and bulk actions
- `settings-page.tsx` — User settings page (profile, preferences, API keys, billing)
- `support-page.tsx` — Support page with FAQ, contact form, and documentation links
- `task-board-page.tsx` — Task management page with kanban board and list views
- `tutorials-page.tsx` — Tutorials and onboarding page for new users

### data/repos/entrepreneuros/scripts/
- `add-metadata-column.ts` — Migration script adding metadata JSONB column to agents table
- `create-demo-user.ts` — Seeds a demo user with sample agents, tasks, and messages
- `create-notifications-table.ts` — Migration script creating the notifications table
- `fix-messages-table.ts` — Migration script fixing messages table schema (column types/constraints)
- `setup-crm-tables.ts` — Migration script creating CRM tables (contacts, deals, pipeline_stages)
- `setup-documents-table.ts` — Migration script creating the documents table
- `setup-folders-table.ts` — Migration script creating the folders table for document organization
- `setup-tables.ts` — Initial migration script creating all core tables (users, agents, tasks, messages)
- `update-agents-table.ts` — Migration script adding new columns to agents table
- `update-messages-table.ts` — Migration script updating messages table schema
- `update-notifications-table.ts` — Migration script updating notifications table schema
- `update-tasks-table.ts` — Migration script adding priority and due date to tasks table

### data/repos/entrepreneuros/server/
- `auth.ts` — Passport.js local strategy authentication with scrypt password hashing and session management
- `db.ts` — Drizzle ORM database client initialization (PostgreSQL via postgres.js)
- `firebase.ts` — Server-side Firebase Admin SDK initialization
- `index.ts` — Express server entry point — registers routes, sets up Vite dev server or static serving
- `openai.ts` — OpenAI SDK initialization and helper functions for agent response generation
- `routes.ts` — Express route definitions — REST API for agents, tasks, messages, CRM, documents, AI chat
- `storage.ts` — Database storage layer — CRUD operations for all entities via Drizzle ORM queries
- `vite.ts` — Vite dev server integration for Express (HMR in development, static in production)

### data/repos/entrepreneuros/server/ai/
- `anthropic-service.ts` — Anthropic Claude API service for generating agent responses
- `gemini-service.ts` — Google Gemini API service for generating agent responses
- `index.ts` — AI service aggregator — exports all provider services and routing logic
- `openai-service.ts` — OpenAI GPT API service for generating agent responses
- `perplexity-service.ts` — Perplexity API service for research-oriented agent responses
- `xai-service.ts` — xAI (Grok) API service for generating agent responses

### data/repos/entrepreneuros/server/integrations/
- `gmail.ts` — Gmail OAuth2 integration — connects user's Gmail for email automation

### data/repos/entrepreneuros/server/replit_integrations/batch/
- `index.ts` — Batch processing entry point for Replit agent integrations
- `utils.ts` — Utility functions for batch processing (rate limiting, error handling)

### data/repos/entrepreneuros/server/replit_integrations/chat/
- `index.ts` — Chat integration entry point for Replit agent communication
- `routes.ts` — Express routes for Replit chat integration API
- `storage.ts` — Chat message storage for Replit integration sessions

### data/repos/entrepreneuros/server/services/
- `action-executor.ts` — Executes AI-approved actions (send email, create task, update CRM) after human approval

### data/repos/entrepreneuros/shared/
- `schema.ts` — Drizzle ORM database schema for EntrepreneurOS (users, agents, tasks, messages, CRM, documents, notifications)

### data/repos/entrepreneuros/shared/models/
- `chat.ts` — Chat message type definitions for EntrepreneurOS AI conversation feature

---

### .github/ — GitHub Actions CI (1 file)

### .github/workflows/
- `mobile-build.yml` — GitHub Actions CI for mobile: triggers on pushes to `cockpit/` on main. 3 jobs: (1) build-web — Vite build with web config, uploads dist-web artifact; (2) build-ios — downloads web artifact, runs `cap sync ios`, builds unsigned Xcode archive on macos-latest; (3) build-android — downloads web artifact, runs `cap sync android`, builds debug APK with Gradle on ubuntu-latest

---

### .claude/ — Claude Code Configuration (6 code files)

### .claude/hooks/
- `validate_change.py` — Pre-tool-use hook — fires before Write, Edit, and Bash to detect risk level and surface warnings for high-risk operations

### .claude/skills/impeccable/scripts/
- `modern-screenshot.umd.js` — UMD bundle of modern-screenshot library — captures DOM elements as images for visual comparison
- `live-browser.js` — Browser-side script for Impeccable live variant mode — injects design feedback overlay into running app
- `live-browser-dom.js` — Browser-side DOM helpers for Impeccable live mode — element selection and measurement utilities
- `live-browser-session.js` — Browser-side durable session helpers for Impeccable live mode — persists state across page reloads

### .claude/skills/impeccable/scripts/detector/
- `detect-antipatterns-browser.js` — Anti-pattern browser detector for Impeccable — scans rendered DOM for common UI/UX anti-patterns

---

### knowledge/ — Knowledge Wiki Code Files (2 files)

### knowledge/skills/marketing/content/remotion/
- `remotion.config.ts` — Remotion video framework configuration (render settings, codec, frame rate)

### knowledge/skills/marketing/content/remotion/src/
- `index.ts` — Remotion entry point — registers the RemotionRoot component for video composition
- `Composition.tsx` — React component stub for Remotion video composition (returns null placeholder)
- `Root.tsx` — Remotion root: registers MyComposition with default dimensions and frame rate

### docker/ — Computer Use Container (1 file)

- `computer-use/start.sh` — container startup: launches Xvfb virtual display, starts VNC server and noVNC web UI for headless browser automation

### infra/scripts/ — Infrastructure Shell Scripts (4 files)

- `dc-up.sh` — starts Docker services with secrets from 1Password: generates ephemeral .env files from op:// references, starts containers, then shreds plaintext files
- `install-crontab.sh` — installs the managed crontab from infra/crontab.managed with 1Password service account token injection
- `op-setup.sh` — one-time 1Password vault population: reads secrets from existing .env files and creates 1Password items (run once after account creation)
- `run.sh` — universal secret-injected command runner: wraps any command with UMH secrets from 1Password (usage: `bash infra/scripts/run.sh <command>`)

---

### Root-Level Files

**Architecture docs:**
- `ARCHITECTURE.md` (26KB) — master specification
- `PLATFORM_SPEC.md` (29KB) — frozen v1.0 platform spec
- `PHILOSOPHY.md` (12KB) — UMH philosophy
- `EPISTEMOLOGY.md` (21KB) — how the organism learns
- `PROTOCOLS.md` (10KB) — 4-layer protocol documentation (L0-L3)
- `AGENTS.md` — agent listing
- `cloud.md` — system context

**Project docs:**
- `README.md` — project readme
- `CLAUDE.md` (20KB) — developer agent soul document (read this)
- `CLAUDE.local.md` — local preferences (gitignored)

**Campaign reports:** `C31_*.md`, `C32_*.md`, `C33_*.md` (10 files)

**Build config:**
- `Dockerfile` — root Docker build (Python 3.11-slim)
- `docker-compose.yml` — 6 services
- `Makefile` — make targets
- `pyproject.toml` — ruff, mypy, pytest config
- `requirements.txt` — Python dependencies
- `skills-lock.json` — skill lockfile

**Setup:**
- `install.sh` — initial system setup: installs Python deps, Docker, creates directories, sets permissions
- `setup.sh` — post-clone setup: creates .env from .env.example, installs pre-commit hooks, pulls Docker images
- `patch_pycord.py` — monkey-patches py-cord library to fix known Discord gateway issues

**Dotfiles:** `.gitignore`, `.dockerignore`, `.env.example`, `.env.sessions.tpl`, `.mcp.json`

---

