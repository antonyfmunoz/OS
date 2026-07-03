# UMH Codebase Guide — Contractor Reference

> Generated 2026-07-03 from graphify AST index (42,603 source nodes, 40,613 edges, 2,979 files)
> Platform v1.0.0 — Production Certified, Frozen 2026-07-01

---

## 1. What This System Is

UMH (Universal Mastery Hierarchy) is a production AI intelligence substrate — a modular platform that receives signals from any source (Discord, HTTP, scheduled events, mesh nodes), routes them through an 8-stage execution pipeline with governance checks, and produces responses using a multi-provider LLM chain with deterministic fallbacks.

It is NOT a chatbot framework. It is an operating system for running AI-augmented business operations.

**Current state:** Single-user validation phase. One organization, multiple ventures. Solo founder + contractor team. Deployed on a Hostinger VPS (orchestrator) with a Windows workstation (executor) connected via Tailscale.

**Tech stack:**
- Backend: Python 3.12 (host), Python 3.11 (Docker containers — no 3.12+ syntax in containerized code)
- Frontend: TypeScript, React 18, Vite, Tailwind CSS, shadcn/ui (Electron + PWA cockpit)
- API: Express + Drizzle ORM (TypeScript HTTP layer), FastAPI (Python operator API)
- Database: Neon Postgres with RLS
- LLM: Claude Opus 4.6 (primary via cc_sdk), Gemini 2.5 Flash, Groq, Ollama (fallback chain)

---

## 2. Architecture — The 4 Layers

Dependency direction is **strictly one-way downward**. Pre-commit hooks enforce this. Violating it blocks your commit.

```
┌─────────────────────────────────────────────────────┐
│  projections/  (EOS, CreatorOS, LyfeOS)             │
│  saas/         (EOS-specific routes, schema, seeds) │
├─────────────────────────────────────────────────────┤
│  transports/   (Discord, HTTP API, node mesh)       │  ← I/O surfaces
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
| `transports/` | I/O surfaces — Discord, HTTP API, node mesh, channels, presence | 2,043 | 193 | 22 | 156 |
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
| `discord/` | signal_factory.py — converts Discord messages to SignalEnvelope |
| `node_mesh/` | Cross-device mesh networking (server.py, client.py) |
| `channels/` | Channel base class + Discord/Telegram/Webhook/Console channels |
| `presence/` | Presence tracking (18 files) |

### Application & Deployment

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `services/` | Deployment entrypoints only. 37 files. No business logic. | discord_bot.py, operator_api.py, browser_relay.py, overnight_scrape.py, heartbeat.py, cost_tracker.py, etc. |
| `cockpit/` | Electron + React frontend. Own Dockerfile. | `src/renderer/` — React 18 + Tailwind + Zustand. 307 source files. Deploy: always `bash cockpit/deploy.sh` |
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

**Setup:** `install.sh`, `setup.sh`, `patch_pycord.py`

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
- No CI/CD — hooks run locally only
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
- **Beast** (`antonys beast pc`) — Windows workstation, GPU. Heavy compute, media processing, browser verification.
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
