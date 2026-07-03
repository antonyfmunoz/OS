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


---

## 13. File-by-File Reference (Every Source File)

This section documents every source file in the repository. Each file gets a one-line description
extracted from its docstring, class definitions, or function signatures. Grouped by directory.

**Total: 2,245 source files** (1,937 Python + 308 TypeScript)



### substrate/ — Universal Platform Layer (986 files)


#### substrate/

- `__init__.py` — Package init
- `canonical_types.py` — Canonical Types module
- `self_model.py` — Self Model module
- `types.py` — Types module

#### substrate/composition/

- `__init__.py` — Package init
- `knowledge_gap_trigger.py` — Knowledge gap trigger — detects gaps during execution and triggers composition.

#### substrate/composition/mastery/

- `__init__.py` — Package init

#### substrate/composition/mastery/authoring/

- `__init__.py` — Package init
- `__main__.py` — Main  module
- `agent.py` — Functions: author()
- `cli.py` — Functions: build_parser() + 1 more
- `draft.py` — Constants/config (defines UNCOVERED_PLACEHOLDER)
- `loader.py` — Loader module
- `mapping.py` — Mapping module
- `models.py` — Data types for the Tool Mastery Author Agent.
- `paths.py` — Path resolution for the Tool Mastery Author Agent.
- `reconcile.py` — Reconcile module
- `verify.py` — Run verify_tool_skill.py against an authored tool.

#### substrate/composition/mastery/management/

- `__init__.py` — Package init
- `active_tool_context.py` — Active Tool Context module
- `backlog.py` — Backlog module
- `coverage.py` — Unified coverage evaluator for the Tool Mastery Manager.
- `discovery.py` — Discovery module
- `ensure.py` — Ensure module
- `maintenance.py` — Maintenance flows for the Tool Mastery Manager.
- `mastery_assurance.py` — Defines MasteryAssuranceStatus + 2 more
- `models.py` — Data types for the Tool Mastery Manager.
- `paths.py` — Path resolution for the Tool Mastery Manager.
- `tool_mastery_resolver.py` — Tool Mastery Resolver module

#### substrate/composition/mastery/research/

- `__init__.py` — Package init
- `__main__.py` — Main  module
- `agent.py` — Agent module
- `artifact.py` — Artifact module
- `candidate_approval.py` — Candidate Approval module
- `cli.py` — Functions: build_parser()
- `docs_site_discovery.py` — Docs site discovery for the Tool Mastery Research Agent.
- `extraction.py` — Structured knowledge extraction for the Tool Mastery Research Agent.
- `fetcher.py` — Fetcher module
- `github_extractor.py` — GitHub repo extractor for the Tool Mastery Research Agent.
- `handoff.py` — Safe metadata handoff for the Tool Mastery Research Agent.
- `headless_fetcher.py` — Headless rendering fetch path for the Tool Mastery Research Agent.
- `models.py` — ResearchMode: What the research agent is being asked to do.
- `paths.py` — Path resolution for the Tool Mastery Research Agent.
- `search_discovery.py` — Deterministic search candidate generator for the Research Agent.
- `source_discovery.py` — Source discovery for the Tool Mastery Research Agent.
- `source_quality.py` — Source Quality module
- `structured_crawl.py` — Structured crawl expansion for the Tool Mastery Research Agent.

#### substrate/composition/registries/

- `__init__.py` — Package init
- `canonical_command_registry_v1.py` — Canonical Command Registry implementation

#### substrate/contracts/

- `__init__.py` — Package init
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

#### substrate/control_plane/

- `__init__.py` — Package init
- `governance.py` — Governance module
- `memory.py` — Defines MemorySystem + 1 more
- `registry.py` — Defines ComponentRegistry + 1 more

#### substrate/control_plane/actions/

- `__init__.py` — Package init
- `actions.py` — Action object — the canonical unit of control in EOS.
- `control_plane.py` — Control Plane module
- `deferred.py` — Functions: save_deferred() + 3 more
- `deferred_status.py` — Defines DeferredStatus
- `executor.py` — Functions: execute_action()
- `idempotency.py` — Filesystem sentinel store for Control Plane idempotency.
- `logging.py` — Append-only JSONL loggers for execution and decision records.
- `notifier.py` — Defines Notifier + 3 more
- `policy.py` — Policy module
- `tme.py` — Tme module
- `validator.py` — Validation + approval rules for Actions.

#### substrate/control_plane/agents/

- `__init__.py` — Package init
- `agent_hierarchy.py` — Agent Hierarchy module
- `agent_teams.py` — Defines SubAgentConfig + 2 more
- `ceo_agent.py` — Ceo Agent module
- `ceo_intelligence.py` — Ceo Intelligence module
- `ceo_operational_standards.py` — Ceo Operational Standards module
- `ea_operational_standards.py` — EA Best Practices — world class EA operating standards

#### substrate/control_plane/context/

- `__init__.py` — Package init
- `context_builder.py` — Context Builder module
- `context_compaction.py` — ContextCompactor — seamless context window management for long conversations.

#### substrate/control_plane/coordination/

- `__init__.py` — Package init
- `coordination_engine.py` — Coordination engine

#### substrate/control_plane/delegation/

- `__init__.py` — Package init
- `delegation_tracker.py` — Delegation Tracker — tracks tasks routed to CEO agents

#### substrate/control_plane/events/

- `__init__.py` — Package init
- `event_bus.py` — EventBus — reactive coordination layer for UMH agents.
- `event_manager.py` — Event Manager module

#### substrate/control_plane/goals/

- `__init__.py` — Package init
- `goal_selector.py` — GoalSelector — goal selection + system focus layer.

#### substrate/control_plane/identity/

- `__init__.py` — Package init
- `ai_identity.py` — Ai Identity module

#### substrate/control_plane/invariants/

- `__init__.py` — Package init
- `coherence_gate.py` — Coherence Gate — fail-closed execution guard.
- `spine_coherence_validator.py` — Functions: validate_coherence_envelope() + 1 more
- `spine_lineage_contracts.py` — Canonical Spine Lineage Contracts.

#### substrate/control_plane/onboarding/

- `__init__.py` — Package init
- `onboarding_engine.py` — Onboarding engine
- `setup_wizard.py` — Setup Wizard module

#### substrate/control_plane/orchestrator/

- `__init__.py` — Package init
- `orchestrator.py` — Orchestrator module

#### substrate/control_plane/proactive/

- `__init__.py` — Package init
- `proactive_engine.py` — Proactive engine

#### substrate/control_plane/router/

- `__init__.py` — Package init
- `control_plane_router_v1.py` — Control Plane Router implementation
- `intent_router.py` — Defines IntentDomain + 1 more
- `router_contracts.py` — Control plane router contracts for the UMH substrate layer.

#### substrate/control_plane/runtime/

- `__init__.py` — Package init
- `cognitive_loop.py` — Defines MultimodalInput
- `gateway.py` — Gateway module
- `substrate_gateway.py` — Substrate Gateway module

#### substrate/control_plane/runtime/orchestrator/

- `__init__.py` — Package init
- `decisions.py` — Decision helpers for signal handler workflows.
- `handlers.py` — Handlers module
- `loop.py` — Loop module
- `orchestrator.py` — Orchestrator — execution coordinator for named workflows.
- `pipeline.py` — Pipeline — sequential composition of Control Plane actions.
- `signals.py` — Signals module
- `steps.py` — Steps module
- `workflows.py` — Functions: register_default_workflows()

#### substrate/control_plane/scheduling/

- `__init__.py` — Package init
- `daily_sync.py` — Daily Sync module
- `ideal_week.py` — Ideal Week module
- `personal_admin.py` — Functions: add_important_date() + 2 more
- `week_architect.py` — Functions: architect_week()

#### substrate/control_plane/signals/

- `__init__.py` — Package init
- `signal_hierarchy.py` — Defines SignalTier + 2 more

#### substrate/control_plane/strategy/

- `__init__.py` — Package init
- `portfolio_advisor.py` — Portfolio Advisor module
- `portfolio_advisor_standards.py` — Portfolio Advisor Best Practices — operational
- `strategy_engine.py` — Strategy engine
- `task_yield_matrix.py` — Task Yield Matrix module

#### substrate/execution/

- `__init__.py` — Package init
- `cpu_gate.py` — Universal CPU gate — single choke point for all UMH execution paths.
- `credential_gate.py` — Credential injection gate — validates credentials flow through 1Password.
- `executor.py` — Executor module
- `feedback.py` — FeedbackCapture — captures execution quality signals.
- `feedback_loop.py` — RLHF Feedback Loop — explicit human feedback ingestion and learning cycle.
- `mastery_gate.py` — MasteryGateResult: Result of the mastery gate check.
- `pipeline.py` — Pipeline module
- `proof_generator.py` — ProofGenerator: Generates Proof objects from execution outcomes.
- `queue.py` — Execution queue — ordered, priority-aware queue for work packets.
- `spine.py` — Spine module
- `trace.py` — TraceRecorder: Protocol for recording execution traces.
- `understanding_bridge.py` — Understanding Bridge — wires the understanding layer into the execution pipeline.

#### substrate/execution/actuation/

- `__init__.py` — Package init
- `actuator_backend_registry_v1.py` — Actuator Backend Registry implementation
- `actuator_maturity_v1.py` — Defines ActuatorMaturityLevel
- `observed_desktop_state_v1.py` — ObservedDesktopStateV1: Observed state of the Windows desktop with maturity classification.
- `windows_foreground_actuator_v1.py` — Windows Foreground Actuator implementation

#### substrate/execution/adapters/

- `__init__.py` — Package init
- `physical.py` — Physical module

#### substrate/execution/agents/

- `__init__.py` — Package init
- `browser_agent.py` — BrowserAgent — Playwright-based web operator for EOS agents.
- `computer_use_agent.py` — Computer Use Agent module

#### substrate/execution/bridge/

- `__init__.py` — Package init
- `actions.py` — ActionKind: Canonical intents. Anything a local node might do for EOS must map to
- `app_allowlist.py` — App launch allow-list for LAUNCH_APP actions.
- `audio_loop.py` — AudioLoopStatus: Bounded local audio loop statuses.
- `auto_task_generation.py` — Auto Task Generation module
- `browser_agent.py` — Browser agent — real Playwright execution surface for the substrate.
- `capabilities.py` — Capability abstraction — what a node can do.
- `capability_routing.py` — Capability-aware task routing — deterministic target selection.
- `capability_tagging.py` — Functions: tag_request()
- `claude_responder.py` — Claude Responder module
- `claude_session_bridge.py` — Claude Code Session Bridge v1 — persistent tmux-backed Claude Code sessions.
- `context_lifecycle.py` — Context Lifecycle module
- `day_workflows.py` — Day Workflows module
- `discord_mode_routing.py` — Discord Mode Routing module
- `discord_output_policy.py` — Display-name policy for Discord watcher output.
- `discord_text_transport.py` — Functions: truncate_reply()
- `discord_voice_playback.py` — Discord Voice Playback module
- `discord_voice_transport.py` — DiscordTransportEvent: One bounded transcript event flowing through the transport.
- `event_spine.py` — Event Spine module
- `execution_trace.py` — Functions: new_trace() + 2 more
- `live_sessions.py` — Live Sessions module
- `local_control.py` — Local control — safe OS-level action layer for the local machine.
- `local_listener.py` — TriggerKind: Bounded set of activation causes the listener will accept.
- `memory_scope_contracts.py` — Defines MemoryScope + 2 more
- `mode_behavior.py` — Mode Behavior module
- `node_controller.py` — NodeController — unified routing brain for task→node dispatch.
- `node_transport.py` — NodeTransportServer: aiohttp-based HTTP transport for the station daemon.
- `nodes.py` — Node abstraction — execution targets beyond "the VPS".
- `operator_presence.py` — Functions: line_for_transition() + 1 more
- `operator_session.py` — Operator session spine — single authoritative source of truth for the
- `operator_state.py` — Operator state — bounded unified state model for the workstation operator.
- `operator_transitions.py` — Operator Transitions module
- `perception.py` — Perception layer — ambient sensing of system and environment state.
- `pipeline_execution.py` — Pipeline Execution module
- `playback_status.py` — Shared playback status snapshot shape for voice transports.
- `resource_guard.py` — Functions: current_resource_snapshot() + 1 more
- `result_query.py` — Result query helpers — tiny operator-facing view over the ResultStore.
- `result_store.py` — Result Store module
- `ritual_body.py` — Ritual Body module
- `ritual_inference.py` — Ritual Inference module
- `ritual_runner.py` — Ritual runner — shell-callable entry points for open_day / close_day.
- `rituals.py` — Ritual workflow scaffold — open_day / close_day.
- `roles.py` — Roles module
- `scene_capabilities.py` — Scene → capability requirements — tiny explicit mapping.
- `scene_policy.py` — SceneDecision: The result of select_scene(). scene=None means 'do not open a scene'.
- `scenes.py` — Scenes module
- `session_control.py` — Session Control module
- `session_discord_bridge.py` — Session Discord Bridge module
- `session_watcher.py` — Session Watcher module
- `station.py` — Station Daemon contract.
- `station_bus.py` — StationBus: Process-wide station transport hub.
- `station_daemon.py` — StationDaemon — minimal local node execution loop.
- `station_helpers.py` — Functions: propose_speak_text() + 5 more
- `station_presence.py` — Station presence — unified station posture and availability state.
- `station_readiness.py` — Station readiness — derived view of whether a node is fit for ritual work.
- `storage.py` — Storage module
- `target_policy.py` — Target Policy module
- `task_decomposition.py` — Task Decomposition module
- `task_execution.py` — Task Execution module
- `task_pipeline.py` — Task pipeline data model — ordered multi-step execution for tasks.
- `task_queue.py` — Task Queue module
- `task_system.py` — Task autonomy and overnight execution system (v1).
- `transcript_inject.py` — Functions: inject_transcript()
- `tts_sanitize.py` — Tts Sanitize module
- `voice_eos_responder.py` — Voice → EOS responder bridge.
- `voice_first.py` — Functions: ensure_ack_wavs() + 4 more
- `voice_session.py` — VoiceSessionStatus: Bounded lifecycle of a single voice session.
- `wake_producer.py` — WakeProducerKind: Bounded set of wake producer signals.
- `workflow_delegation.py` — Workflow Delegation module
- `workflow_execution.py` — Workflow Execution module
- `workload_policy.py` — Workload Policy module

#### substrate/execution/ingestion/

- `__init__.py` — Package init

#### substrate/execution/loop/

- `__init__.py` — Package init
- `execution_loop.py` — ExecutionLoop — closed-loop goal execution with outcome feedback.
- `persistent_loop.py` — Persistent Loop module
- `stages.py` — Stages module

#### substrate/execution/media/

- `__init__.py` — Package init
- `media_processor.py` — MediaProcessor — unified multimodal file handler.

#### substrate/execution/runtime/

- `__init__.py` — Package init
- `capability_router.py` — Capability Router module
- `execution_contracts_v1.py` — Defines SignalSource + 7 more
- `execution_spine.py` — ExecutionSpine — single execution path for all EOS operations (legacy runtime).
- `live_local_runtime_execution_v1.py` — Live Local Runtime Execution v1 for the UMH substrate layer.
- `local_runtime_supervisor_v1.py` — Local Runtime Supervisor implementation
- `node_sync_gate_v1.py` — Node Sync Gate implementation
- `runtime_bootstrap_state_v1.py` — Runtime Bootstrap State implementation
- `runtime_dispatch_queue_v1.py` — Defines DispatchStatus + 2 more
- `runtime_execution_result_v1.py` — Defines ExecutionOutcome + 3 more
- `runtime_heartbeat_v1.py` — Runtime Heartbeat v1 for the UMH substrate layer.
- `runtime_presence_state_v1.py` — Runtime Presence State v1 — workstation presence tracking.
- `runtime_recovery_v1.py` — Runtime Recovery implementation
- `runtime_session_registry_v1.py` — Defines RuntimeMode + 3 more
- `substrate_continuity_engine_v1.py` — Substrate Continuity Engine implementation
- `worker_runtime_contracts.py` — Defines EnvironmentType + 7 more
- `worker_supervisor_v1.py` — Worker Supervisor implementation
- `workpacket_execution_gate_v1.py` — Workpacket Execution Gate implementation

#### substrate/execution/voice/

- `__init__.py` — Package init
- `session.py` — Voice Session — end-to-end voice pipeline loop.
- `voice_engine.py` — Voice engine

#### substrate/execution/workers/

- `__init__.py` — Package init

#### substrate/execution/workers/workstation/

- `__init__.py` — Package init
- `environment_mapping_engine_v1.py` — Environment Mapping Engine v1.
- `foreground_cu_ingestion_execution_v1.py` — Foreground Cu Ingestion Execution implementation
- `relay_execution_transport_v1.py` — Relay Execution Transport implementation
- `tmux_operational_adapter_v1.py` — Tmux Operational Adapter implementation
- `visible_actuation_proof_v1.py` — Visible Actuation Proof implementation
- `workstation_contracts_v1.py` — Workstation Contracts implementation
- `workstation_execution_orchestrator_v1.py` — Workstation Execution Orchestrator implementation
- `workstation_node_registry_v1.py` — WorkstationNodeRegistry: Registry of known workstation relay nodes.
- `workstation_relay_self_heal_v1.py` — Workstation Relay Self Heal implementation

#### substrate/execution/workers/workstation/_dormant/

- `__init__.py` — Package init
- `adapter_autogeneration_engine_v1.py` — Adapter Autogeneration Engine implementation
- `adaptive_governance_intelligence_engine_v1.py` — Constants/config (defines _ROOT)
- `browser_continuity_bridge_v1.py` — Browser Continuity Bridge v1.
- `browser_execution_orchestrator_v1.py` — Browser Execution Orchestrator v1.
- `browser_gui_contracts_v1.py` — Browser and GUI Embodiment Contracts v1.
- `browser_gui_embodiment_engine_v1.py` — Browser and GUI Embodiment Engine v1.
- `browser_observability_pipeline_v1.py` — Browser Observability Pipeline implementation
- `browser_operational_modes_v1.py` — Browser Operational Modes implementation
- `browser_replay_validator_v1.py` — Browser Replay Validator implementation
- `constitutional_antifragility_resilience_engine_v1.py` — Constitutional Antifragility Resilience Engine implementation
- `constitutional_epistemic_intelligence_engine_v1.py` — Constitutional Epistemic Intelligence Engine implementation
- `constitutional_identity_continuity_engine_v1.py` — IdentityPrimitive: Single identity continuity measurement.
- `constitutional_resource_economics_engine_v1.py` — Constitutional Resource Economics Engine implementation
- `constitutional_strategic_intelligence_engine_v1.py` — Constants/config (defines _ROOT)
- `constitutional_substrate_governance_layer_v1.py` — Constants/config (defines _ROOT)
- `constitutional_telos_alignment_engine_v1.py` — TelosPrimitive: Single telos alignment primitive measurement.
- `distributed_constitutional_substrate_federation_v1.py` — Distributed Constitutional Substrate Federation implementation
- `governed_browser_adapter_v1.py` — Governed Browser Adapter implementation
- `governed_recursive_orchestration_engine_v1.py` — Governed Recursive Orchestration Engine implementation
- `governed_shell_adapter_v1.py` — Governed Shell Adapter v1.
- `persistent_substrate_continuity_engine_v1.py` — Persistent Substrate Continuity Engine implementation
- `recursive_capability_planning_engine_v1.py` — Recursive Capability Planning Engine implementation
- `visible_gui_adapter_v1.py` — Visible Gui Adapter implementation
- `workstation_continuity_bridge_v1.py` — Workstation Continuity Bridge implementation
- `workstation_observability_pipeline_v1.py` — WorkstationObservabilityPipeline: Append-only telemetry pipeline for workstation executions.
- `workstation_operational_embodiment_engine_v1.py` — Workstation Operational Embodiment Engine v1.
- `workstation_operational_modes_v1.py` — Workstation Operational Modes implementation
- `workstation_relay_heartbeat_v1.py` — Workstation Relay Heartbeat implementation
- `workstation_relay_node_v1.py` — WorkstationRelayNode: Identity and state of a Windows workstation relay node.
- `workstation_relay_proof_v1.py` — Functions: classify_relay_proof() + 2 more
- `workstation_replay_validator_v1.py` — Workstation Replay Validator implementation
- `workstation_state_registry_v1.py` — Workstation State Registry implementation

#### substrate/foundation/

- `__init__.py` — Package init
- `identity.py` — Identity continuity schema — maintains coherent self across time and context switches.
- `laws.py` — Substrate laws — re-exports from substrate.ontology.laws.
- `perspective.py` — Perspective schema — the lens through which the substrate interprets signals.

#### substrate/governance/

- `__init__.py` — Package init
- `authority.py` — Authority levels — what the system can do without human intervention.
- `policy_engine.py` — Policy engine
- `risk_classes.py` — Action risk categories — semantic classification of side-effect types.
- `security.py` — Security hardening — input validation, rate limiting, audit logging.

#### substrate/governance/accountability/

- `__init__.py` — Package init
- `accountability.py` — Accountability module

#### substrate/governance/policy/

- `__init__.py` — Package init
- `authority_engine.py` — Authority engine
- `authority_tier.py` — Authority tier constants and validation for ingestion sources.
- `confidentiality.py` — Functions: detect_confidential_context() + 1 more
- `execution_authority_engine_v1.py` — Execution Authority Engine implementation

#### substrate/governance/principles/

- `__init__.py` — Package init
- `principle_engine.py` — Principle engine

#### substrate/governance/quality/

- `__init__.py` — Package init
- `quality_gate.py` — Defines TransformationResult + 1 more

#### substrate/governance/validation/

- `__init__.py` — Package init
- `completeness_engine.py` — Completeness engine
- `output_validator.py` — Output Validator module

#### substrate/integrations/

- `__init__.py` — Package init
- `bridge.py` — UMH Bridge — connects UMH model routing to runtime/model_router.py.
- `cors.py` — CORS configuration for UMH API.
- `health.py` — Health aggregator — dashboard endpoint combining all service health signals.
- `product_connections.py` — Product Connections module

#### substrate/intelligence/

- `__init__.py` — Package init
- `finetune_harness.py` — Finetune Harness module
- `runtime.py` — Runtime runtime
- `training_extractor.py` — TrainingExample: A single training example in Alpaca format.

#### substrate/memory/

- `__init__.py` — Package init
- `auto_reconciler.py` — AutoReconciler — closes the gap between promoted memories and canonical store.
- `candidate_generator.py` — Defines PromotionStatus + 2 more
- `canonical_write.py` — MemoryWriteReceipt: Receipt returned after a canonical memory write attempt.
- `claude_bridge.py` — Claude Bridge module
- `promoter.py` — MemoryPromoter: Promotes memory candidates with semantic dedup, contradiction detection, and temporal decay.
- `watcher.py` — Watcher module

#### substrate/meta_ide/

- `__init__.py` — Package init
- `browser_evidence_collector.py` — Browser Evidence Collector module
- `browser_verification_gate.py` — Browser Verification Gate — blocking validation for UI-bearing work.
- `engineering_execution.py` — Engineering Execution engine
- `engineering_intent.py` — Engineering Intent Contract — types for autonomous engineering planning.
- `engineering_planner.py` — Engineering Planner engine
- `engineering_session_coordinator.py` — Engineering Session Coordinator engine
- `engineering_work_generator.py` — EngineeringWorkGenerator: Converts engineering plans into governed work packets.
- `repository_model.py` — Repository reality model — read-only git awareness.
- `review_package_builder.py` — Review Package Builder — deterministic proof assembly.
- `roadmap_gap_engine.py` — Roadmap Gap engine
- `roadmap_intelligence.py` — Roadmap Intelligence module
- `shared_planner.py` — Shared EngineeringPlanner singleton for all cockpit route modules.
- `workspace_intelligence.py` — Workspace intelligence — engineering-state awareness.
- `workspace_observation.py` — Workspace Observation — live engineering runtime observation.
- `workspace_registry.py` — Workspace Registry module
- `workspace_runtime_graph.py` — Workspace Runtime Graph — canonical workspace topology models.
- `workspace_topology_engine.py` — Workspace Topology Engine — live workspace topology with health.

#### substrate/observability/

- `__init__.py` — Package init
- `error_recorder.py` — Canonical fix-forever error recorder.
- `jsonl_rotation.py` — JSONL rotation utility.
- `outcome_classifier.py` — OutcomeClassifier — classifies execution results into outcome categories.
- `trace_store.py` — Defines TraceStatus + 2 more

#### substrate/ontology/

- `__init__.py` — Package init
- `laws.py` — Laws module
- `primitives.py` — Ontology primitives — the computational physics of UMH.
- `relationships.py` — Typed relationship edges between ontology observations.

#### substrate/ontology/domains/

- `__init__.py` — Package init
- `contract.py` — Domain bridge contract — re-exports from substrate.understanding.domains.contract.
- `creator.py` — Creator domain bridge — re-exports from substrate.understanding.domains.creator.
- `life.py` — Life domain bridge — re-exports from substrate.understanding.domains.life.

#### substrate/operator/

- `__init__.py` — Package init
- `continuity_engine.py` — Continuity engine
- `device_continuity.py` — Device Continuity — per-device presence state tracking.
- `intent_receipt.py` — Unified intent receipt — canonical audit trail for every operator interaction.
- `intent_router.py` — Intent Router module
- `intent_runtime.py` — Intent Runtime — canonical intent preservation for operator continuity.
- `operator_attention_engine.py` — Operator Attention engine
- `operator_context.py` — Operator Context module
- `operator_context_engine.py` — Operator Context engine
- `operator_presence.py` — Operator Presence module
- `operator_snapshot_runtime.py` — Operator Snapshot runtime
- `presence_timeline.py` — Presence Timeline — operator presence transition tracking.
- `repository_context_resolver.py` — RepositoryContextResolver: Maps workspace/topology data into structured repository context.
- `screen_awareness.py` — Screen Awareness module
- `screen_context_providers.py` — UMH Screen Context Providers — three modes of screen awareness.
- `screen_observation_engine.py` — Screen Observation engine
- `voice_query_engine.py` — Voice Query engine
- `workstation_session_runtime.py` — Workstation Session runtime
- `workstation_translator.py` — WorkstationTranslator: Translates Beast workstation payload → canonical ScreenSnapshot.

#### substrate/organism/

- `__init__.py` — Package init
- `action_bridge.py` — Action Bridge module
- `action_catalog.py` — Action Catalog module
- `action_envelope.py` — Action Envelope module
- `action_voice_contract.py` — Voice/Intent Action Contract — interface between intent sources and ActionBridge.
- `advisor.py` — Constants/config (defines _COMPLEXITY_KEYWORDS)
- `advisor_conversation.py` — Defines AdvisorResponse + 1 more
- `advisor_hierarchy.py` — Advisor Hierarchy module
- `advisor_reconciliation.py` — Advisor Reconciliation module
- `agent_capability_model.py` — Agent Capability Model module
- `agent_execution_runner.py` — Agent Execution Runner — invokes coding agents inside governed sandboxes.
- `agent_fleet_runtime.py` — Agent Fleet runtime
- `agent_registry.py` — Agent Registry module
- `agent_runtime.py` — Agent base runtime — the foundational behavior of every agent in the society.
- `agents.py` — Concrete agent cells — Researcher, Builder, AutoResearch.
- `allocation_loop.py` — Allocation Loop module
- `approval_gate.py` — Approval Gate module
- `approval_store.py` — Defines ApprovalStore
- `artifact_registry.py` — Artifact Registry module
- `assisted_executor.py` — Assisted Executor — governed execution of approved maintenance actions.
- `assumption_tracking_runtime.py` — Assumption Tracking Runtime — governed assumption records for UMH.
- `async_coordinator.py` — Async Coordinator module
- `automation_pipeline.py` — Automation Candidate Pipeline — promote repeated interventions to automation.
- `autonomous_action_gateway.py` — Autonomous Action Gateway — structural enforcement of spine-routed mutation.
- `autonomous_cadence.py` — Defines CadenceMode + 3 more
- `autonomous_improvement_lane.py` — Autonomous Improvement Lane — bounded autonomous LOW-risk self-improvement.
- `autonomous_pr_factory.py` — Autonomous Pr Factory module
- `autonomous_tick.py` — Autonomous Tick module
- `benchmark_harness.py` — Benchmark Harness — measures and compares Pipeline A (legacy) vs Pipeline B (governed).
- `bottleneck_engine.py` — Bottleneck engine
- `candidate_supply_engine.py` — Candidate Supply engine
- `canonical_update.py` — Canonical Update module
- `capability_compounding_runtime.py` — Capability Compounding runtime
- `capability_evolution_engine.py` — Capability Evolution Engine — Campaign 12.2
- `capability_gap_engine.py` — Capability Gap Engine — detect missing or immature capabilities for goals.
- `capability_graph_engine.py` — Capability Graph engine
- `capability_portfolio_runtime.py` — Capability Portfolio Runtime — portfolio-level health and compounding metrics.
- `capability_runtime.py` — Capability runtime
- `capability_validation_runtime.py` — Capability Validation Runtime — benchmark storage, reporting, and freshness tracking.
- `change_event.py` — Change Event module
- `changeset_manifest.py` — Defines ChangedFile + 5 more
- `claude_code_runtime_adapter.py` — Defines ClaudeCodeRuntimeAdapter
- `coherence_propagation.py` — Defines OutcomeEventType + 3 more
- `command_runtime.py` — Command runtime
- `composition_engine.py` — Composition Engine — deterministic intent → plan from observed capabilities.
- `compounding_engine.py` — Compounding engine
- `compute_fabric_runtime.py` — Compute Fabric Runtime — unified compute body map.
- `context_diagnostic.py` — Context Diagnostic module
- `context_ingestion_engine.py` — Context Ingestion engine
- `context_resolution.py` — Context Resolution module
- `continuity_runtime.py` — Continuity runtime
- `continuous_qualification.py` — Continuous Qualification module
- `contradiction_engine.py` — Defines ContradictionSeverity + 5 more
- `coordinator.py` — OrganismCoordinator — hierarchical task decomposition and runtime assignment.
- `correspondence_scheduler.py` — RegressionAlert: A detected certification regression.
- `council.py` — Council module
- `cross_source_reconciler.py` — Cross Source Reconciler module
- `daemon.py` — Daemon module
- `daily_driver_log.py` — Defines DriverFailure + 1 more
- `decision_impact_engine.py` — Defines DecisionImpact + 1 more
- `decision_lineage_engine.py` — Decision Lineage engine
- `decision_registry.py` — Decision Registry module
- `decision_validity_engine.py` — Decision Validity engine
- `delegation_followup.py` — Delegation Followup module
- `delegation_readiness_runtime.py` — Delegation Readiness runtime
- `delegation_runtime.py` — Delegation runtime
- `delegation_topology.py` — Defines TopologyType + 2 more
- `dependency_graph.py` — Dependency Graph module
- `deploy_verification_worker.py` — Defines DeployCheckStatus + 3 more
- `dev_session_tracker.py` — Dev Session Tracker module
- `development_session_bridge.py` — Development Session Bridge module
- `device_awareness.py` — Device Awareness module
- `device_capacity.py` — Defines DeviceCapacity + 1 more
- `device_provisioner.py` — Device Provisioner module
- `device_registry_writer.py` — Device Registry Writer module
- `device_role_registry.py` — Device Role Registry module
- `dex_conversation.py` — Backward-compat shim — canonical module is advisor_conversation.py.
- `dex_reconciliation.py` — Backward-compat shim — canonical module is advisor_reconciliation.py.
- `diagnostic_engine.py` — Diagnostic Engine — analyze ingested context for canonical truth state.
- `distributed_runtime.py` — Distributed runtime
- `documentation_awareness_runtime.py` — Documentation Awareness Runtime — content-level metadata for docs.
- `domain_registry.py` — Domain Registry module
- `drift_detection_engine.py` — Drift Detection Engine — unified drift synthesis.
- `embodiment_runtime.py` — Embodiment runtime
- `empire_router.py` — Empire Router — routes founder intent to domain-classified, governed WorkPackets.
- `environment_discovery.py` — Environment Discovery module
- `environment_graph.py` — Environment Graph module
- `environment_reconciler.py` — Environment Reconciler module
- `event_spine.py` — Defines EventDomain + 4 more
- `execution_coordinator.py` — Execution Coordinator Runtime — canonical orchestration layer (Phase 13).
- `execution_economy.py` — Execution Economy — runtime cost/value tracking and leverage scoring.
- `execution_graph.py` — Defines ExecutionNodeType + 2 more
- `execution_journal.py` — Defines JournalPhase + 2 more
- `execution_ledger.py` — Defines LedgerEntry + 1 more
- `execution_lifecycle_runtime.py` — Execution Lifecycle runtime
- `execution_modes.py` — Execution Modes module
- `executive_brief_runtime.py` — Executive Brief runtime
- `executive_portfolio_runtime.py` — Executive Portfolio runtime
- `executor_runtime.py` — Executor Runtime — canonical execution contract layer (Phase 14).
- `goal_alignment_engine.py` — Defines AlignmentReport + 1 more
- `goal_drift_engine.py` — Goal Drift Engine — detect movement away from objectives.
- `goal_hierarchy_engine.py` — Goal Hierarchy Engine — structural operations on the goal tree.
- `governance_runtime.py` — C15.0 — Governance Runtime.
- `governed_execution_runtime.py` — Governed Execution runtime
- `governed_spine.py` — Governed Spine module
- `governed_work_runtime.py` — Governed Work Runtime — MANDATORY execution gateway.
- `grounded_handlers.py` — Grounded Handlers module
- `grounding_registry.py` — Grounding Registry module
- `handoff.py` — Agent handoff protocol — structured agent-to-agent task transfer.
- `homeostasis.py` — Defines SystemMode + 5 more
- `impact_analyzer.py` — Impact Analyzer — computes change impact across the propagation graph.
- `infrastructure_runtime.py` — Infrastructure Runtime — register and track system & institutional infrastructure.
- `ingestion_job.py` — Ingestion Job module
- `institutional_memory_runtime.py` — Institutional Memory runtime
- `intent_classifier.py` — Intent Classifier module
- `knowledge_awareness_runtime.py` — Knowledge Awareness runtime
- `knowledge_model_registry.py` — Knowledge Model Registry module
- `learning_extraction_runtime.py` — Learning Extraction runtime
- `learning_portfolio_runtime.py` — Learning Portfolio Runtime — Campaign 12.3
- `leverage_assimilation.py` — Leverage Assimilation module
- `leverage_engine.py` — Leverage engine
- `leverage_metrics.py` — Operational Leverage Metrics — measures actual organism value.
- `maintenance_loop.py` — Maintenance Loop module
- `memory_promotion.py` — Memory Promotion module
- `mesh_reconciler.py` — Mesh node reconciliation — syncs RuntimeGraph with live mesh relay.
- `meta_ide_runtime.py` — Meta IDE Runtime — unified development surface.
- `mission.py` — Defines MissionStatus + 2 more
- `mutation_catalog.py` — Defines EndpointEntry + 1 more
- `mutation_registry.py` — Mutation Registry module
- `mutation_router.py` — Mutation Router module
- `next_action_engine.py` — Next Action Engine — evidence-based action recommender.
- `objective_physics.py` — Objective Physics module
- `objective_queue.py` — Objective Queue module
- `observability.py` — Observability module
- `operating_loop_coherence_runtime.py` — Defines LoopCoherenceStatus + 4 more
- `operational_truth.py` — OperationalTruthSnapshot — scoreboard for UMH operational reality.
- `operationalization_runtime.py` — Defines OperationalizationForm + 2 more
- `operator_acceptance.py` — Operator Acceptance module
- `operator_acceptance_mode.py` — Operator acceptance mode — standard multi-runtime vs deterministic-only vs blocked.
- `operator_acceptance_scenarios.py` — Operator Acceptance Scenarios module
- `operator_compression.py` — Operator Compression module
- `operator_escape_tracker.py` — Operator Escape Tracker module
- `operator_loop_coordinator.py` — Operator loop coordinator — orchestrates the end-to-end acceptance loop.
- `operator_loop_runtime.py` — Operator Loop runtime
- `operator_migration_runtime.py` — Operator Migration Runtime — track and close external-loop dependencies.
- `operator_readiness_gate.py` — Defines OperatorReadinessReport
- `operator_response.py` — Operator Response module
- `operator_session.py` — Operator Session module
- `orchestration_loop.py` — Orchestration loop — persistent autonomous execution for the organism.
- `orchestrator_awareness_runtime.py` — Orchestrator Awareness Runtime — synthesized reality model for the orchestrator.
- `orchestrator_kernel.py` — Orchestrator Kernel module
- `organism_coordination_engine.py` — Defines CoordinationIssueType + 4 more
- `organism_loop.py` — OrganismLoopResult: Complete result of an organism loop cycle.
- `organism_portfolio_runtime.py` — Organism Portfolio runtime
- `organism_state_runtime.py` — Organism State runtime
- `outcome_learning.py` — Outcome Learning module
- `outcome_pattern_engine.py` — Outcome Pattern Engine — Campaign 12.1
- `outcome_tracking_runtime.py` — Outcome Tracking Runtime — measure progress toward goals.
- `outcome_verification.py` — VerificationLevel: Graduated verification depth — maps to projection certification L0-L5.
- `packet_router.py` — Packet Router module
- `parallel.py` — ParallelTask: A single task within a parallel execution batch.
- `permission_dialogue.py` — Permission Dialogue module
- `plan_execution_adapter.py` — Defines ExecutionGraphStatus + 4 more
- `prediction_portfolio_runtime.py` — Prediction Portfolio runtime
- `presence_runtime.py` — PresenceAttentionState: Fine-grained attention states for presence-aware logic.
- `priority_engine.py` — Priority Engine — deterministic priority synthesis.
- `product_factory_runtime.py` — Product Factory runtime
- `production_merge_verifier.py` — Production Merge Verifier module
- `production_ops_runtime.py` — Defines ProductionPhase + 5 more
- `production_planning_runtime.py` — Production Planning runtime
- `production_review_runtime.py` — Production Review runtime
- `production_truth_delta.py` — Production Truth Delta module
- `production_workforce_runtime.py` — ProductionRole: Organizational hierarchy for software production.
- `profile_runtime.py` — Profile Runtime — canonical authority for operator work identity and system modes.
- `project_registry.py` — Project Registry module
- `projection_certification.py` — Projection Certification module
- `projection_engine.py` — Projection engine
- `projection_integration_runtime.py` — Projection Integration runtime
- `projection_port.py` — Defines StateSlice + 2 more
- `projection_readiness_gate.py` — Projection Readiness Gate — blocks feature build until source reconciliation is sufficient.
- `projection_reconciliation_engine.py` — Projection Reconciliation engine
- `projection_source_registry.py` — Defines ProjectionSourceType + 5 more
- `promotion_threshold_policy.py` — Defines CadenceLevel + 3 more
- `proof_runtime.py` — Proof Runtime — complete proof packages per execution.
- `proof_store.py` — Proof Store module
- `propagation_executor.py` — Propagation Executor module
- `propagation_graph.py` — Propagation Graph — dependency-aware change propagation model.
- `propagation_graph_builder.py` — PropagationGraphBuilder: Builds propagation graph from current system state.
- `propagation_planner.py` — Propagation Planner — creates wave-based propagation plans.
- `propagation_wiring.py` — Propagation Wiring module
- `protocols.py` — Organism protocols — typed contracts for the agent society.
- `qualification_harness.py` — ConfidenceEstimate: Statistical confidence interval for a metric.
- `readiness_model.py` — Readiness Model module
- `reality_graph.py` — Reality Graph module
- `recommendation_engine.py` — Recommendation engine
- `reconciliation_engine.py` — Reconciliation Engine — structured context reconciliation sessions.
- `reconciliation_session.py` — Reconciliation Session — structured operator-AI context alignment.
- `recursion_governance.py` — Defines EscalationLevel + 6 more
- `reliability_signals.py` — Reliability Signal Model — normalizes production-backed signals for cadence ranking.
- `reliability_weighted_ranker.py` — Reliability Weighted Ranker module
- `report_dispatcher.py` — Report dispatcher — sends task completion reports to Discord + cockpit chat.
- `repository_awareness_runtime.py` — Defines FileCategory + 3 more
- `resource_allocation_runtime.py` — Defines ResourceType + 6 more
- `risk_engine.py` — Risk Engine — unified risk register synthesis.
- `roadmap_engine.py` — Roadmap Engine — phase linkage model for self-build queue.
- `role_contracts.py` — Role Contracts + Capability Profiles — template-based role definitions.
- `runtime_adapter.py` — Defines RuntimeStartRequest + 3 more
- `runtime_adapters.py` — Concrete RuntimeAdapter implementations for UMH runtimes.
- `runtime_awareness_runtime.py` — Runtime Awareness Runtime — unified view of active system state.
- `runtime_fleet.py` — Runtime Fleet runtime
- `runtime_graph.py` — Runtime Graph runtime
- `runtime_handoff.py` — Runtime Handoff runtime
- `runtime_manager.py` — Runtime Manager runtime
- `runtime_session.py` — Runtime Session runtime
- `runtime_state_registry.py` — Runtime State Registry — live environment awareness for the workstation.
- `runtime_supervisor.py` — Defines SupervisedHealth + 3 more
- `sandbox_orchestrator.py` — Sandbox Orchestrator — ties approval gate to PR factory execution.
- `scenario_intelligence_engine.py` — Scenario Intelligence engine
- `self_build_queue.py` — Defines WorkItemStatus + 2 more
- `self_maintenance_bridge.py` — Functions: create_degradation_callback() + 1 more
- `self_model_predictor.py` — Self Model Predictor module
- `service_dependency_graph.py` — Service Dependency Graph — canonical service dependency models.
- `service_dependency_registry.py` — ServiceDependencyRegistry: Single source of truth for service dependency topology.
- `service_failure_engine.py` — ServiceFailureEngine: Computes failure impact and critical path across the service graph.
- `session_runtime.py` — Session Runtime — canonical session architecture for UMH.
- `shell_runtime_adapter.py` — Shell runtime adapter — safe subprocess execution surface.
- `slo_definitions.py` — SLODefinition: A single Service Level Objective.
- `source_registry.py` — Source Registry — tracks all context sources available to UMH.
- `source_truth_linker.py` — Source Truth Linker module
- `source_truth_runtime.py` — LineageNodeType: Every node type in the full organizational lineage chain.
- `spine_guard.py` — SpineGuard — enforcement layer for the single-spine mutation doctrine.
- `state_authority_graph.py` — Defines StateDomain + 5 more
- `state_coherence_engine.py` — State Coherence engine
- `state_registry.py` — State Registry — canonical registry of state domain authorities.
- `store.py` — Defines OrganismStore
- `strategic_context_runtime.py` — Defines StrategicHealth + 2 more
- `strategic_gap_engine.py` — Strategic Gap Engine — compares current reality to target goals, produces gaps,
- `strategic_memory_engine.py` — Strategic Memory engine
- `strategic_planning_engine.py` — Strategic Planning Engine — generate plans linking current reality to goals.
- `strategic_tick_loop.py` — Strategic Tick Loop module
- `sync_policy.py` — Sync Policy module
- `system_identity.py` — Canonical UMH identity — single source of truth.
- `tailscale_discovery.py` — Tailscale auto-discovery tick — diffs tailscale peers vs device registry.
- `template_governance.py` — Template Governance module
- `template_registry.py` — Template Registry — reusable executable structures from governed execution.
- `template_seeder.py` — Template Seeder module
- `tradeoff_intelligence_engine.py` — Tradeoff Intelligence engine
- `trajectory_intelligence_runtime.py` — Trajectory Intelligence runtime
- `trial_runner.py` — Trial Runner module
- `trust_score.py` — Trust Score module
- `umh_node_registry.py` — Umh Node Registry module
- `umh_node_topology.py` — UMH Node Topology — canonical node role and version models.
- `umh_version_coherence.py` — UMH Version Coherence Engine — detects version drift across nodes.
- `universal_work_queue.py` — Universal Work Queue module
- `work_graph.py` — Defines WorkNodeType + 5 more
- `work_packet.py` — Work Packet module
- `work_packet_engine.py` — Work Packet Engine — creates work packets from user intent.
- `work_portfolio_runtime.py` — Work Portfolio Runtime — execution health, velocity, and drift detection.
- `work_readiness_runtime.py` — Work Readiness runtime
- `work_recovery_runtime.py` — Work Recovery Runtime — maps work states to recovery actions.
- `workcell.py` — Workcell — planning/delegation workcell model for Work Packets.
- `workcell_daemon.py` — WorkcellDaemon — persistent processor for workcell inboxes.
- `workcell_protocol.py` — Workcell Protocol module
- `worker_cell.py` — Worker cell — bounded task execution through the existing pipeline.
- `worker_lifecycle.py` — Defines WorkerEventType + 1 more
- `worker_registry.py` — Worker Registry — active worker inventory per device.
- `workload_placement_policy.py` — Workload Placement Policy module
- `workload_probes.py` — Real Workload Probes — live operational pressure into the organism.
- `workload_runner.py` — Defines WorkloadType + 3 more
- `workspace_awareness.py` — Workspace Awareness module
- `workstation_runtime.py` — Workstation Runtime — canonical workstation planning layer (Phase 10).
- `worktree_sandbox.py` — Worktree Sandbox Manager — isolated execution environments for autonomous improvements.
- `world_model.py` — World Model — organism-level self-model of UMH system state.

#### substrate/organism/audits/

- `__init__.py` — Package init
- `context_capacity.py` — Audit — Context Capacity.
- `empire_readiness.py` — Empire Readiness module
- `model_correspondence.py` — Model Correspondence module
- `operational_awareness.py` — Audit — Operational Awareness.
- `organism_awareness.py` — AwarenessDimension: Reported vs actual value for a single awareness dimension.
- `source_truth.py` — LineageChain: Lineage completeness for a single production.

#### substrate/organism/benchmarks/

- `__init__.py` — Package init
- `autonomous_execution.py` — Defines SessionRecord + 2 more
- `capability_reuse.py` — Benchmark 4 — Capability Reuse (Dual-Track).
- `company_ops.py` — Company Ops module
- `competitive.py` — Competitive module
- `composite_scorer.py` — Composite Scorer module
- `compounding_proof.py` — Compounding Proof module
- `efficiency.py` — Efficiency Benchmark — capability per dollar.
- `external_adapters.py` — External Adapters module
- `governance_quality.py` — Governance Quality module
- `harness_scorer.py` — Harness Scorer module
- `harness_superiority.py` — Harness Superiority module
- `human_amplification.py` — Defines SkillLevel + 4 more
- `mutation_equivalence.py` — Mutation Equivalence Scorer — Benchmark H for C33.
- `operator_compression.py` — Operator Compression module
- `orchestration_quality.py` — Defines OrchestrationDecision + 2 more
- `outcome_accuracy.py` — Outcome Accuracy Benchmark — did completed work achieve original intent?
- `production_outcome_quality.py` — Production Outcome Quality module
- `production_quality.py` — Benchmark 2 — Production Quality.
- `production_velocity.py` — Benchmark 3 — Production Velocity.
- `projection_readiness.py` — ProjectionCoverage: Coverage analysis for a single projection.
- `reality_correspondence.py` — Reality Correspondence module
- `reality_recovery.py` — Benchmark 1 — Reality Recovery.
- `reliability.py` — Reliability Benchmark — consistency across repeated builds.
- `strategic_compression.py` — IntentRecord: A single operator intent and its execution outcome.
- `surface_switching.py` — Surface Switching module

#### substrate/organism/executors/

- `__init__.py` — Package init
- `agent_executor.py` — Functions: classify_agent_task_risk() + 1 more
- `approval_intercept.py` — Defines ApprovalInterceptStatus + 2 more
- `execution_telemetry.py` — Execution Telemetry — live event pipeline for executor lifecycle.
- `workstation_executor.py` — Workstation Executor module

#### substrate/organism/self_use/

- `__init__.py` — Package init
- `certification_report.py` — Certification Report module
- `gap_ledger.py` — Gap Ledger module
- `meta_ide_audit.py` — Meta Ide Audit module
- `projection_delta.py` — Projection Delta module
- `task_catalog.py` — Defines TaskStatus + 3 more
- `task_taxonomy.py` — Task taxonomy — domain classification for self-use certification.

#### substrate/organism/tests/

- `__init__.py` — Package init
- `test_advisor.py` — Tests for advisor — interpret, decompose, delegate, synthesize.
- `test_advisor_coordinator.py` — Tests for advisor → coordinator integration (Phase 2A).
- `test_agent_runtime.py` — tests for agent base runtime — critique loop, deliverable production.
- `test_allocation_loop.py` — Functions: test_allocation_cycle() + 5 more
- `test_approval_store.py` — tests for approval store — JSONL persistence for governance-blocked signals.
- `test_assisted_executor.py` — Functions: test_blocked_in_observe_mode() + 5 more
- `test_async_coordinator.py` — Functions: test_submit_objective() + 7 more
- `test_automation_pipeline.py` — Tests for the AutomationPipeline — Phase 5.9.
- `test_autonomous_tick.py` — Tests for the autonomous tick engine.
- `test_bottleneck_engine.py` — Tests for BottleneckEngine.
- `test_composition_engine.py` — Defines TestCompositionIntent + 6 more
- `test_contradiction_engine.py` — Tests for contradiction_engine
- `test_coordinator.py` — Tests for coordinator
- `test_daemon_approvals.py` — tests for daemon approval creation on governance rejection.
- `test_dependency_graph.py` — Tests for dependency_graph
- `test_development_session_bridge.py` — Defines TestSessionLifecycle + 2 more
- `test_e2e.py` — End-to-end test — the vertical slice acceptance criterion.
- `test_environment_graph.py` — Tests for EnvironmentGraph — operational topology.
- `test_environment_reconciler.py` — Defines _MockAdapter + 2 more
- `test_event_spine.py` — Functions: test_event_creation() + 14 more
- `test_execution_modes.py` — Tests for ExecutionModeManager.
- `test_leverage_assimilation.py` — Tests for leverage_assimilation — external framework ingestion and scoring.
- `test_leverage_metrics.py` — Functions: test_empty_metrics() + 8 more
- `test_leverage_rebalance.py` — Tests for continuous leverage rebalancing.
- `test_maintenance_loop.py` — Tests for the MaintenanceLoop — Phase 5.9.
- `test_memory_promotion.py` — Tests for memory_promotion
- `test_mission.py` — Defines FakeAdapter + 4 more
- `test_objective_physics.py` — Functions: test_register_objective() + 11 more
- `test_objective_queue.py` — Functions: test_enqueue_and_peek() + 11 more
- `test_operational_intelligence.py` — Tests for Phase 7.0 Operational Intelligence engines.
- `test_operator_compression.py` — Tests for OperatorCompression engine.
- `test_orchestration_integration.py` — Tests for orchestration_integration
- `test_orchestration_loop.py` — Tests for orchestration_loop — PersistentLoop stages wired to organism daemon.
- `test_organism_events.py` — tests for organism ViewFrame event broadcasting.
- `test_outcome_learning.py` — Tests for outcome learning loop.
- `test_phase10_template_supply.py` — Tests for phase10_template_supply
- `test_phase11_1_universal_work.py` — Phase 11.1 — Universal Work Queue + Work Packet Engine tests.
- `test_phase11_self_build_queue.py` — Tests for phase11_self_build_queue
- `test_phase12_0_propagation_graph.py` — Phase 12.0 — Universal Propagation Graph / Correspondence Layer tests.
- `test_phase13_0_operator_experience.py` — Phase 13.0 — Operator Experience Kernel tests.
- `test_phase13_4m.py` — Tests for phase13_4m
- `test_phase14_1_source_inspection.py` — Tests for phase14_1_source_inspection
- `test_phase3.py` — Phase 3 tests — Governed Recursive Execution Economy.
- `test_phase58_integration.py` — Tests for phase58_integration
- `test_phase59_integration.py` — Integration tests for Phase 5.9 — end-to-end workload execution.
- `test_phase61_governed_spine.py` — Tests for Phase 6.1 — GovernedExecutionSpine, ActionEnvelope,
- `test_phase62_spine_enforcement.py` — Tests for phase62_spine_enforcement
- `test_phase63_autonomous_gate.py` — Tests for phase63_autonomous_gate
- `test_phase92_self_improvement.py` — Tests for phase92_self_improvement
- `test_phase93_reliability_campaign.py` — Tests for phase93_reliability_campaign
- `test_phase94_coherence_propagation.py` — Defines TestTemplateRegistry
- `test_phase95_spine_native_propagation.py` — TestSpineNativeOutcomeCommitted: Verify spine automatically emits OutcomeCommitted after verified success.
- `test_phase9_integration.py` — Tests for Phase 9.0 — World Model → Execution Integration.
- `test_plan_execution_adapter.py` — Tests for plan_execution_adapter — Phase 9.1 Composition→Execution bridge.
- `test_projection_port.py` — Tests for projection-agnostic organism state port.
- `test_projection_reconciliation_engine.py` — Defines TestDivergenceType + 3 more
- `test_projection_source_registry.py` — Tests for ProjectionSourceRegistry (Phase 14.0).
- `test_protocols.py` — tests for organism protocols — deliverable, agent message, worker spec.
- `test_report_dispatcher.py` — Tests for substrate.organism.report_dispatcher.
- `test_runtime_events.py` — Tests for runtime event bus wiring.
- `test_runtime_graph.py` — Tests for runtime_graph
- `test_runtime_supervisor.py` — Tests for RuntimeSupervisor — lifecycle management, crash detection, recovery.
- `test_store.py` — tests for organism JSONL store.
- `test_workcell_protocol.py` — Tests for WorkcellV2 — durable inbox/outbox execution cells.
- `test_worker_cell.py` — tests for worker cell — bounded task execution.
- `test_workload_probes.py` — Tests for WorkloadProbes.
- `test_workload_runner.py` — Functions: test_run_repo_health() + 10 more
- `test_world_model.py` — Tests for organism world model — system self-model.

#### substrate/reality_model/

- `__init__.py` — Package init
- `canonical.py` — Defines CanonicalRelationship + 2 more
- `canonical_reality_write.py` — Canonical Reality Write module
- `instance.py` — Instance module
- `reality_intelligence.py` — Reality Intelligence module
- `reality_mutation.py` — Reality mutation contracts — governed observation writes.
- `reality_query.py` — Reality Query Contract — types for reality interrogation.
- `simulation.py` — Simulation module

#### substrate/sockets/

- `__init__.py` — Package init
- `approval_port.py` — Approval port — substrate-layer abstraction for approval decisions.
- `browser_port.py` — Browser port — substrate-layer abstraction for web access adapters.
- `capability_socket.py` — CapabilitySocket: Routes capability requests to registered integration handlers.
- `channel_port.py` — Channel port — substrate-layer abstraction for the channel router.
- `config_port.py` — Config port — substrate-layer abstraction for runtime config access.
- `data_source_port.py` — Data source port — substrate-layer abstraction for external data adapters.
- `envelopes.py` — Envelope dataclasses — the data shapes that cross the socket boundary.
- `intelligence_port.py` — Intelligence port — substrate-layer abstraction for model routing and LLM access.
- `message_port.py` — Message port — substrate-layer abstraction for conversation persistence.
- `notification.py` — Notification socket — substrate-layer abstraction for outbound notifications.
- `notification_engine.py` — Multi-channel notification engine — substrate-layer abstraction.
- `organism_port.py` — Organism port — substrate-layer abstraction for daemon/organism access.
- `outcome_socket.py` — OutcomeSocket: Delivers outcome notifications to registered integrations.
- `projection_port.py` — Projection Port module
- `protocols.py` — SignalDescriptor: Declares a signal type an integration can emit.
- `registry.py` — Registry module
- `remote_exec_port.py` — Remote execution port — substrate-layer abstraction for SSH and remote ops.
- `sensing_port.py` — Sensing adapter port — substrate-layer abstraction for perception registration.
- `signal_socket.py` — SignalSocket: UMH's inbound socket for external signals.
- `tool_adapter_port.py` — Tool adapter port — substrate-layer abstraction for shell/filesystem/git tools.
- `view_socket.py` — View socket — broadcast pipeline state frames to observers.

#### substrate/sockets/view/

- `__init__.py` — Package init
- `broadcaster.py` — ViewFrameBroadcaster: ViewSubscriber that bridges sync on_frame() calls to an async callback.
- `websocket.py` — WebSocket endpoint for broadcasting ViewFrames to cockpit clients.

#### substrate/state/

- `__init__.py` — Package init
- `transformation_state_ledger.py` — Transformation State Ledger for the UMH substrate layer.

#### substrate/state/business/

- `__init__.py` — Package init
- `business_instance.py` — Business Instance module
- `venture_knowledge.py` — Defines Venture + 1 more

#### substrate/state/config/

- `__init__.py` — Package init
- `config_store.py` — Config Store module
- `settings_persistence.py` — Functions: load_settings() + 2 more

#### substrate/state/context/

- `__init__.py` — Package init
- `context.py` — Defines SubstrateContext

#### substrate/state/finance/

- `__init__.py` — Package init
- `expense_tracker.py` — Expense Tracker module
- `subscription_tracker.py` — Functions: get_subscriptions() + 3 more

#### substrate/state/lifecycle/

- `__init__.py` — Package init
- `stage_manager.py` — Stage Manager module

#### substrate/state/logs/

- `__init__.py` — Package init
- `decision_log.py` — Decision Log module

#### substrate/state/memory/

- `__init__.py` — Package init
- `memory.py` — Memory module

#### substrate/state/memory/contracts/

- `__init__.py` — Package init
- `canonical_memory_query_contracts.py` — Canonical Memory Query contracts for the UMH substrate layer.
- `canonical_memory_reconciliation_engine_v1.py` — Canonical Memory Reconciliation Engine implementation
- `canonical_memory_store_v1.py` — Canonical Memory Store implementation
- `memory_conflict_governance_v1.py` — Memory Conflict Governance implementation
- `memory_identity_v1.py` — MemoryIdentity: Identity envelope for a canonical or instance memory.

#### substrate/state/metrics/

- `__init__.py` — Package init
- `founder_rate.py` — Founder Rate module
- `okr_tracker.py` — Functions: set_okr() + 2 more

#### substrate/state/permissions/

- `__init__.py` — Package init
- `os_trinity.py` — Os Trinity module

#### substrate/state/preferences/

- `__init__.py` — Package init
- `model_preferences.py` — Model Preferences module

#### substrate/state/profiles/

- `__init__.py` — Package init
- `user_model.py` — UserModel: Behavioral model of the founder's communication style, decision patterns,

#### substrate/state/providers/

- `__init__.py` — Package init
- `provider_state.py` — Global Provider State + Backpressure + Execution Budget.

#### substrate/state/registries/

- `__init__.py` — Package init
- `claude_skill_registry.py` — Claude Skill Registry module
- `skill_registry.py` — Skill Registry module
- `skill_registry_v2.py` — Skill Registry V2 module

#### substrate/state/session/

- `__init__.py` — Package init
- `session_state.py` — Defines SessionState

#### substrate/state/storage/

- `__init__.py` — Package init
- `db.py` — Functions: get_conn() + 2 more

#### substrate/state/stores/

- `agent_registry_store.py` — AgentRegistryStore — canonical write API for the agents table.
- `approval_store.py` — ApprovalStore — SQL-backed multi-tenant approval API (deprecated).
- `context_compaction_store.py` — ContextCompactionStore — canonical write API for the context_compactions table.
- `email_folder_store.py` — EmailFolderStore — canonical write API for the email_folders table.
- `embedding_store.py` — EmbeddingStore — canonical write API for the embeddings table.
- `entity_link_store.py` — EntityLinkStore — canonical write API for the entity_links table.
- `entity_store.py` — State store for entity_store
- `goal_store.py` — State store for goal_store
- `higgsfield_store.py` — HiggsFieldStore — canonical write API for the higgsfield_jobs table.
- `permission_store.py` — Defines PermissionStore
- `preference_store.py` — PreferenceStore — canonical write API for the model_preferences table.
- `profile_store.py` — State store for profile_store
- `skill_store.py` — SkillStore — canonical API for the skills table.
- `task_store.py` — TaskStore — canonical write API for the tasks table.
- `venture_store.py` — VentureStore — canonical write API for the ventures table.

#### substrate/state/tenancy/

- `__init__.py` — Package init
- `tenant.py` — Tenant — formal multi-tenant isolation layer for EOS.

#### substrate/state/work/

- `__init__.py` — Package init
- `work_state.py` — Defines Pressure + 1 more

#### substrate/understanding/

- `__init__.py` — Package init
- `breadth_expansion.py` — Breadth Expansion module

#### substrate/understanding/deliberation/

- `__init__.py` — Package init
- `council.py` — Defines CouncilRole + 4 more

#### substrate/understanding/domains/

- `__init__.py` — Package init
- `business.py` — Business module
- `contract.py` — Domain bridge protocol and projection dataclass.
- `creator.py` — Creator module
- `life.py` — Life module
- `registry.py` — Bridge registry — plug-in system for domain bridges.

#### substrate/understanding/embedding/

- `__init__.py` — Package init
- `embedder.py` — Lightweight text embedder — shared singleton used by memory.py and
- `embedding_engine.py` — EmbeddingEngine — Three-tier hybrid embedding with graceful degradation.

#### substrate/understanding/intelligence/

- `__init__.py` — Package init
- `competitive_intel.py` — Functions: log_competitor_signal() + 2 more
- `human_intelligence.py` — Defines HumanIntelligenceEngine
- `input_intelligence.py` — Input Intelligence module
- `person_recognition.py` — Person Recognition module
- `stakeholder_map.py` — Stakeholder Map module

#### substrate/understanding/interpretation/

- `__init__.py` — Package init
- `interpretation_engine_v1.py` — Interpretation Engine v1 for the UMH substrate layer.

#### substrate/understanding/knowledge/

- `__init__.py` — Package init
- `knowledge_domains.py` — Knowledge Domains module
- `knowledge_graph.py` — Knowledge Graph module
- `knowledge_integrator.py` — Knowledge Integrator module
- `knowledge_layers.py` — Knowledge Layers module
- `philosophy_lenses.py` — Philosophy Lenses module

#### substrate/understanding/ontology/

- `__init__.py` — Package init
- `primitive_decomposition_v1.py` — Defines PrimitiveType + 4 more
- `primitives.py` — Primitives module

#### substrate/understanding/patterns/

- `__init__.py` — Package init
- `leverage_patterns.py` — Functions: detect_leverage_killer() + 1 more
- `pattern_engine.py` — Pattern engine

#### substrate/understanding/perception/

- `__init__.py` — Package init
- `orchestrator.py` — Orchestrator module
- `source.py` — Source abstraction for the generic ingestion pipeline.

#### substrate/understanding/perception/parsers/

- `__init__.py` — Package init
- `base.py` — Shared contracts for all language parsers.
- `config_parser.py` — Config parser — top-level key extraction for JSON/YAML/TOML files.
- `js_parser.py` — Defines JSParser
- `python_parser.py` — Defines PythonParser
- `sql_parser.py` — SQL parser — detects tables, views, and FROM references.
- `ts_parser.py` — TypeScript parser — reuses JS regexes and adds interface/type extraction.

#### substrate/understanding/reality/

- `__init__.py` — Package init
- `reality_context.py` — Reality Context module
- `reality_engine.py` — Reality engine

#### substrate/understanding/research/

- `__init__.py` — Package init
- `research_engine.py` — Research engine

#### substrate/understanding/signals/

- `__init__.py` — Package init
- `founder_capture.py` — Founder Capture module

#### substrate/understanding/world_model/

- `__init__.py` — Package init
- `world_model.py` — WorldModel — two-layer world model for the Meta Harness.

#### substrate/understanding/world_pulse/

- `__init__.py` — Package init
- `world_pulse.py` — World Pulse module

#### substrate/workstation/

- `__init__.py` — Package init
- `activation.py` — Activation module
- `agent_workforce_runtime.py` — WorkforceHealth: Agent workforce health — derived deterministically.
- `ambient_wake_runtime.py` — Ambient Wake runtime
- `app_resolver.py` — Native app resolver — Chrome-first browser policy, app vs website classification.
- `attention_aggregation_runtime.py` — Attention Aggregation runtime
- `attention_vision_runtime.py` — Defines VisualSignalType + 4 more
- `camera_commands.py` — Camera Commands module
- `checkpoint.py` — Checkpoint module
- `cockpit_capability_map.py` — Cockpit Capability Map — audit surface for cockpit routes, panels, stores.
- `command_center_mvp_runtime.py` — Command Center Mvp runtime
- `command_router.py` — Command Router module
- `continuity.py` — Continuity state machine — unified lifecycle for operator presence/absence.
- `continuity_engine.py` — Continuity engine
- `device_presence.py` — DeviceSession: A single active operator surface registered with the presence registry.
- `environment_awareness_runtime.py` — Environment Awareness runtime
- `execution_fabric_runtime.py` — Execution Fabric Runtime — Campaign 19.0.
- `file_browser.py` — File Browser module
- `intent_contract.py` — Intent contract — converts high-level operator intent into end-state designs.
- `jarvis_command.py` — Backward-compat shim — canonical module is command_router.py.
- `lifecycle_modes.py` — Lifecycle modes — system-level cycle that governs safety and background behavior.
- `loop_engine.py` — Loop completion engine — end-state verification and progress reporting.
- `meta_ide_context_runtime.py` — Meta IDE Context Runtime — read-only context binding for the build surface.
- `meta_ide_projection_loop_runtime.py` — Meta Ide Projection Loop runtime
- `mode_commands.py` — ModeCommandResult: Result of parsing a natural mode command.
- `mode_resolver.py` — Mode Resolver module
- `mvp_readiness_runtime.py` — Defines MVPDimensionStatus + 4 more
- `operating_loop_runtime.py` — Operating Loop runtime
- `orchestrator_presence_runtime.py` — Defines PresenceMode + 2 more
- `overnight_queue.py` — OvernightWorkItem: A work item queued for overnight processing.
- `profile_behavior.py` — Profile Behavior module
- `profile_modes.py` — Profile/work modes — operator activity context governing workspace/tool/task selection.
- `resume_brief.py` — Return/resume brief generator — answers "what happened while I was gone?"
- `screen_awareness_runtime.py` — Defines ScreenAwarenessHealth + 3 more
- `security_mode.py` — Security Mode module
- `session_machine_runtime.py` — Session Machine Runtime — Campaign 19.2.
- `state.py` — WorkstationProfile: Static-ish workstation identity and environment.
- `tracker_stack.py` — Tracker Stack module
- `trigger_chains.py` — Trigger Chains module
- `unified_approval_runtime.py` — Defines ApprovalSourceType + 3 more
- `unified_execution_surface_runtime.py` — Unified Execution Surface Runtime — single view across all execution subsystems.
- `unified_workstation_runtime.py` — UnifiedWorkstationState: What the organism is doing — derived deterministically.
- `vision_presets.py` — PresetZone: A named region within a preset's view.
- `vision_privacy.py` — Vision Privacy module
- `vision_query.py` — Vision Query module
- `vision_scene.py` — Vision Scene module
- `visual_context_runtime.py` — Visual Context runtime
- `visual_operations_runtime.py` — Visual Operations runtime
- `voice_ingress_runtime.py` — Voice Ingress runtime
- `voice_operations_runtime.py` — Voice Operations runtime
- `voice_output_runtime.py` — Voice Output runtime
- `voice_route_resolver.py` — Functions: parse_target_node()
- `voice_session_manager.py` — Voice Session Manager — Campaign 20.1.
- `vps_control_catalog.py` — Vps Control Catalog module
- `work_lane.py` — Work Lane module
- `workstation_presence_runtime.py` — Workstation Presence Runtime — operator footprint across the workstation.

### adapters/ — External System Adapters (100 files)


#### adapters/

- `__init__.py` — Package init
- `protocol.py` — Adapter: Every external system connection implements this.
- `socket_registration.py` — Socket Registration module

#### adapters/adapter_engine/

- `__init__.py` — Package init
- `adapter_lifecycle_manager_v1.py` — Adapter Lifecycle Manager implementation
- `adapter_manifest.py` — AdapterMaturityLevel: How well UMH understands an adapter's capabilities.
- `adapter_maturity.py` — Adapter Maturity module
- `adapter_registry_contracts.py` — Adapter Registry Contracts module
- `capability_catalog.py` — Per-adapter capability catalog for the UMH substrate layer.
- `capability_discovery.py` — Capability Discovery module
- `cu_api_parity_v1.py` — CU / API Parity Validator v1 for the UMH substrate layer.
- `google_docs_adapter_v1.py` — Google Docs Adapter implementation
- `google_drive_adapter_v1.py` — Defines DriveCapabilityType + 4 more
- `gws_scanner_bridge_v1.py` — Gws Scanner Bridge implementation
- `live_drive_docs_ingestion_pipeline_v1.py` — Live Drive Docs Ingestion Pipeline implementation
- `modality.py` — Communication modality types for UMH adapters.
- `participant.py` — Participant type classification for UMH adapters.
- `production_manifests.py` — Production Manifests module
- `substrate_candidate_gen_v1.py` — Substrate Candidate Gen implementation
- `substrate_decomposer_v1.py` — Functions: decompose_document()

#### adapters/broadcast/

- `__init__.py` — Package init
- `engine.py` — Engine engine
- `ffmpeg_args.py` — Pure deterministic config -> FFmpeg CLI argument list.
- `filtergraph.py` — Filtergraph module
- `process_lifecycle.py` — Process Lifecycle module
- `scene_model.py` — SourceEntry: One source in a scene — position, scale, and enable state.
- `zmq_client.py` — ZmqCommandResult: Result of a single zmq command.

#### adapters/broadcast/integration/

- `__init__.py` — Package init
- `handlers.py` — Handlers module
- `manifest.py` — Broadcast integration manifest — declares capabilities for start, stop, status.

#### adapters/browser/

- `__init__.py` — Package init

#### adapters/browser_auth/

- `__init__.py` — Package init
- `clerk_auth.py` — Clerk Auth module
- `sso_chain.py` — Functions: detect_sso_provider()

#### adapters/browser_exports/

- `__init__.py` — Package init
- `chatgpt_export.py` — Chatgpt Export module
- `claude_export.py` — Claude Export module
- `contract.py` — Browser export contract — data classes for export requests and results.
- `gmail_export_poller.py` — Constants/config (defines _REPO_ROOT)
- `instagram_export.py` — Instagram Export module
- `instagram_export_parser.py` — Instagram curation analyst — classifies saved posts and scores harness candidates.
- `profile_manager.py` — Profile Manager module

#### adapters/calendar/

- `__init__.py` — Package init
- `meetings.py` — Meetings module
- `travel_manager.py` — Travel Manager module

#### adapters/data_source_adapters/

- `__init__.py` — Package init
- `conversation_source.py` — ConversationTurn: A single turn in a conversation.
- `github_source.py` — Github Source module
- `gws_source.py` — GWSSource: Reads a single Google Workspace document via GWSDocumentScanner.
- `local_file_source.py` — LocalFileSource — reads a single local file as an ingestion source.

#### adapters/data_source_adapters/parsers/

- `__init__.py` — Package init
- `chatgpt_parser.py` — ChatGPT conversation export parser.
- `claude_parser.py` — Functions: parse_claude_export()

#### adapters/github/

- `__init__.py` — Package init
- `github_operations.py` — GitHubOperations: Governed GitHub write operations via gh CLI.

#### adapters/google_workspace/

- `__init__.py` — Package init
- `doc_creator.py` — Doc Creator module
- `document_filer.py` — Functions: classify_document() + 2 more
- `email_gps.py` — Email Gps module
- `gws_connector.py` — Gws Connector module
- `gws_scanner.py` — Gws Scanner module
- `tasks_adapter.py` — Google Tasks adapter — thin wrapper over GWSConnector task methods.

#### adapters/models/

- `__init__.py` — Package init
- `agent_runtime.py` — RateLimiter: In-memory per-org rate limiter.
- `cc_sdk.py` — CCResult: Return type for cc_sdk queries.
- `codex_cli.py` — Defines CodexResult
- `hermes_cli.py` — hermes_cli — Hermes Agent runtime adapter for UMH.
- `llm_adapter.py` — LLMAdapter: Wraps model_router as a substrate-compliant adapter.
- `model_router.py` — Model Router module
- `opencode_cli.py` — Defines OpenCodeResult

#### adapters/models/routing/

- `__init__.py` — Package init
- `capabilities.py` — Capabilities module
- `config.py` — RoutingConfig: Resolves capability classes to model_router kwargs and metadata.

#### adapters/notebooklm/

- `__init__.py` — Package init
- `notebooklm_sync.py` — Notebooklm Sync module

#### adapters/notion/

- `__init__.py` — Package init
- `notion_publisher.py` — Notion Publisher module
- `notion_sync.py` — Notion Sync module

#### adapters/notion/integration/

- `__init__.py` — Package init
- `auth.py` — Notion auth — credential loading from environment.
- `correlation.py` — Thread-safe in-memory correlation map for outcome writeback targeting.
- `handlers.py` — Handlers module
- `manifest.py` — Functions: load_signal_sources()
- `outcomes.py` — Notion outcome receiver — writes pipeline outcomes back to Notion pages.
- `poller.py` — Poller module
- `signals.py` — Notion signal emitter — builds SignalEnvelopes from polled Notion pages.
- `transforms.py` — Notion API ↔ UMH payload translations.
- `watermarks.py` — Watermark persistence — JSONL append-log for per-database poll high-water marks.

#### adapters/scrapling/

- `__init__.py` — Package init
- `scrapling_connector.py` — ScraplingConnector: Stealth web fetcher using Scrapling under the hood.

#### adapters/ssh/

- `__init__.py` — Package init
- `ssh_utils.py` — Functions: ssh_run() + 3 more

#### adapters/tailscale/

- `__init__.py` — Package init
- `tailscale_api.py` — Tailscale Admin API adapter.

#### adapters/tool_adapters/

- `__init__.py` — Package init
- `base.py` — Base adapter — shared interface and deny-rule machinery.
- `filesystem.py` — FilesystemAdapter: Filesystem access with safe-root enforcement.
- `git.py` — Git adapter — governed git operations. Read-only by default.
- `shell.py` — Shell adapter — governed command execution with destructive-command blocking.
- `tmux.py` — Tmux module

### transports/ — I/O Surfaces (188 files)


#### transports/

- `__init__.py` — Package init

#### transports/api/

- `__init__.py` — Package init
- `_mesh_dispatch.py` — Mesh Dispatch module
- `agent_bridge.py` — Functions: main()
- `agent_routes.py` — Agent Routes module
- `app.py` — App module
- `approval_routes.py` — Approval Routes module
- `cockpit.py` — Cockpit API endpoints — serves real data from UMH stores to the frontend.
- `cockpit_action_bridge_routes.py` — Defines ExecuteActionBody
- `cockpit_activity_routes.py` — Cockpit Activity Routes module
- `cockpit_adapter_status_routes.py` — Cockpit adapter status routes — read-only observability for the adapter fleet.
- `cockpit_agent_fleet_routes.py` — Functions: configure() + 6 more
- `cockpit_agent_workforce_routes.py` — Cockpit routes for AgentWorkforceRuntime — Campaign 19.1.
- `cockpit_ambient_wake_routes.py` — Cockpit routes for AmbientWakeRuntime — Campaign 20.2.
- `cockpit_artifact_registry_routes.py` — Cockpit routes for Artifact Registry — Campaign 6.0.
- `cockpit_attention_routes.py` — Cockpit routes for AttentionAggregationRuntime — Campaign 18.2.
- `cockpit_audit.py` — Functions: emit_settings_audit() + 1 more
- `cockpit_auth.py` — Cockpit Auth module
- `cockpit_autonomous_routes.py` — Cockpit Autonomous Routes module
- `cockpit_broadcast_routes.py` — Defines SourceType + 2 more
- `cockpit_capability_intelligence_routes.py` — Cockpit Capability Intelligence Routes module
- `cockpit_capability_map_routes.py` — Cockpit Capability Map Routes — API surface for cockpit audit.
- `cockpit_capability_routes.py` — Cockpit Capability Routes — API surface for emergent capability tracking.
- `cockpit_chat_routes.py` — Functions: configure() + 1 more
- `cockpit_command_center_mvp_routes.py` — Functions: configure() + 12 more
- `cockpit_command_center_routes.py` — Functions: configure()
- `cockpit_compounding_routes.py` — Cockpit Compounding Routes module
- `cockpit_compute_fabric_routes.py` — Functions: configure() + 4 more
- `cockpit_context_assimilation_routes.py` — Cockpit Context Assimilation Routes module
- `cockpit_context_resolution_routes.py` — Cockpit routes for Context Resolution — Campaign 5.5.
- `cockpit_core_bootstrap_routes.py` — Cockpit Core Bootstrap Routes module
- `cockpit_core_eos_routes.py` — Functions: register_eos_routes() + 5 more
- `cockpit_core_feedback_routes.py` — Cockpit feedback & notification routes — extracted from cockpit_core_routes.py.
- `cockpit_core_governance_routes.py` — Cockpit Core Governance Routes module
- `cockpit_core_routes.py` — Cockpit Core Routes module
- `cockpit_core_session_routes.py` — Cockpit session & device routes — extracted from cockpit_core_routes.py.
- `cockpit_delegation_routes.py` — Cockpit routes for Delegation Runtime — Campaign 4.7.
- `cockpit_device_routes.py` — Functions: configure()
- `cockpit_distributed_runtime_routes.py` — Cockpit Distributed Routes runtime
- `cockpit_documentation_awareness_routes.py` — Cockpit routes for Documentation Awareness — Campaign 6.2.
- `cockpit_economy_routes.py` — Cockpit Economy Routes module
- `cockpit_embodiment_routes.py` — Functions: configure() + 7 more
- `cockpit_engineering_review_routes.py` — Cockpitering Review Routes engine
- `cockpit_engineering_routes.py` — Cockpit engineering routes — autonomous planning and packetization.
- `cockpit_entity_routes.py` — Cockpit Entity Routes module
- `cockpit_execution_fabric_routes.py` — Cockpit routes for ExecutionFabricRuntime — Campaign 19.0.
- `cockpit_execution_graph_routes.py` — Cockpit Execution Graph Routes module
- `cockpit_execution_loop_routes.py` — Cockpit Execution Loop Routes module
- `cockpit_execution_routes.py` — Cockpit Execution Routes — canonical execution capability surface.
- `cockpit_executive_routes.py` — Cockpit routes for Executive Intelligence — Campaign 14.3.
- `cockpit_goal_routes.py` — Cockpit routes for Goal Systems & Strategic Planning — Campaign 8.6.
- `cockpit_governance_routes.py` — Functions: get_router() + 7 more
- `cockpit_infrastructure_routes.py` — Cockpit Infrastructure Routes module
- `cockpit_intent_routes.py` — Cockpit Intent Routes module
- `cockpit_knowledge_awareness_routes.py` — Cockpit routes for Knowledge Awareness — Campaign 6.4.
- `cockpit_learning_routes.py` — Cockpit Learning Routes module
- `cockpit_loop_coherence_routes.py` — Cockpit routes for Operating Loop Coherence Runtime — Campaign 4.3.
- `cockpit_memory_routes.py` — Functions: configure() + 1 more
- `cockpit_meta_ide_context_routes.py` — Cockpit routes for Meta IDE Context — Campaign 17.1.
- `cockpit_meta_ide_conv_routes.py` — Cockpit Meta IDE convergence routes — unified development surface.
- `cockpit_meta_ide_critical_routes.py` — Cockpit Meta Ide Critical Routes module
- `cockpit_meta_ide_projection_loop_routes.py` — Cockpit Meta IDE Projection Loop Routes — API surface for build loop.
- `cockpit_meta_ide_routes.py` — Cockpit Meta IDE routes — engineering reality awareness.
- `cockpit_migration_routes.py` — Functions: configure() + 8 more
- `cockpit_mvp_readiness_routes.py` — Cockpit routes for MVP Readiness Runtime — Campaign 4.5.
- `cockpit_operating_loop_routes.py` — Defines TrackRequest + 1 more
- `cockpit_operationalization_routes.py` — Functions: configure() + 4 more
- `cockpit_operator_experience_routes.py` — Cockpit operator experience routes — session, send, preview, status.
- `cockpit_operator_home_routes.py` — Cockpit Operator Home Routes — unified operator context API.
- `cockpit_operator_loop_ext_routes.py` — Cockpit operator loop extension routes — Phases 5-8.
- `cockpit_operator_loop_routes.py` — Cockpit operator loop routes — intent to plan to implementation to audit.
- `cockpit_operator_loop_session_routes.py` — Functions: configure()
- `cockpit_operator_presence_routes.py` — Cockpit Operator Presence Routes — presence and continuity API.
- `cockpit_operator_timeline_routes.py` — Cockpit Operator Timeline Routes module
- `cockpit_orchestrator_awareness_routes.py` — Cockpit routes for Orchestrator Awareness Runtime — Campaign 4.0.
- `cockpit_orchestrator_presence_routes.py` — Cockpit routes for Orchestrator Presence — Campaign 17.0.
- `cockpit_organism_map_routes.py` — Cockpit Organism Map Routes — unified topology for the organism map instrument.
- `cockpit_organism_routes.py` — Functions: configure()
- `cockpit_prediction_routes.py` — Cockpit Prediction Routes module
- `cockpit_presence_routes.py` — Cockpit Presence Routes module
- `cockpit_production_routes.py` — Cockpit production routes — software production organism surface.
- `cockpit_projection_integration_routes.py` — Functions: configure() + 7 more
- `cockpit_projection_routes.py` — Cockpit routes for Gate 10 — Projection Consumption Layer.
- `cockpit_proof_inspector_routes.py` — Cockpit Proof Inspector routes — G10 MVP gate.
- `cockpit_propagation_graph_routes.py` — Cockpit Propagation Graph Routes module
- `cockpit_push_routes.py` — Cockpit Push Routes module
- `cockpit_reality_graph_routes.py` — Functions: configure() + 8 more
- `cockpit_reality_intelligence_routes.py` — Cockpit Reality Intelligence Routes module
- `cockpit_reality_model_routes.py` — Functions: configure()
- `cockpit_recovery_dashboard_routes.py` — Cockpit Recovery Dashboard Routes module
- `cockpit_repository_awareness_routes.py` — Cockpit routes for Repository Awareness — Campaign 6.1.
- `cockpit_rooms_routes.py` — Conference Rooms API — servers, categories, channels, messages, threads, forums,
- `cockpit_runtime_awareness_routes.py` — Cockpit routes for Runtime Awareness — Campaign 6.3.
- `cockpit_runtime_surface_routes.py` — Cockpit Surface Routes runtime
- `cockpit_screen_awareness_routes.py` — Functions: configure() + 9 more
- `cockpit_self_build_routes.py` — Cockpit Self Build Routes module
- `cockpit_self_improvement_routes.py` — Cockpit self-improvement loop routes — outcome assimilation, verification,
- `cockpit_service_graph_routes.py` — Functions: configure() + 7 more
- `cockpit_session_machine_routes.py` — Cockpit routes for SessionMachineRuntime — Campaign 19.2.
- `cockpit_session_routes.py` — Functions: configure() + 8 more
- `cockpit_settings_mutations.py` — Cockpit Settings Mutations module
- `cockpit_spine_router.py` — Cockpit Spine Router module
- `cockpit_state_authority_routes.py` — Cockpit State Authority Routes — read-only state domain authority API.
- `cockpit_strategic_routes.py` — Functions: configure() + 9 more
- `cockpit_umh_node_routes.py` — Functions: configure() + 7 more
- `cockpit_unified_approval_routes.py` — Cockpit Unified Approval Routes module
- `cockpit_unified_execution_routes.py` — Cockpit Unified Execution Routes module
- `cockpit_unified_workstation_routes.py` — Functions: get_router() + 1 more
- `cockpit_universal_work_routes.py` — Functions: configure()
- `cockpit_validation_routes.py` — Functions: configure() + 9 more
- `cockpit_visual_attention_routes.py` — Cockpit routes for AttentionVisionRuntime — Campaign 21.3.
- `cockpit_visual_awareness_routes.py` — Cockpit routes for ScreenAwarenessRuntime — Campaign 21.0.
- `cockpit_visual_context_routes.py` — Cockpit routes for VisualContextRuntime — Campaign 21.2.
- `cockpit_visual_environment_routes.py` — Cockpit routes for EnvironmentAwarenessRuntime — Campaign 21.1.
- `cockpit_visual_ops_routes.py` — Cockpit routes for VisualOperationsRuntime — Campaign 21.4.
- `cockpit_voice_ingress_routes.py` — Cockpit routes for VoiceIngressRuntime — Campaign 20.0.
- `cockpit_voice_ops_routes.py` — Cockpit routes for VoiceOperationsRuntime — Campaign 20.4.
- `cockpit_voice_output_routes.py` — Cockpit routes for VoiceOutputRuntime — Campaign 20.3.
- `cockpit_voice_routes.py` — Functions: configure() + 2 more
- `cockpit_voice_session_routes.py` — Cockpit routes for VoiceSessionManager — Campaign 20.1.
- `cockpit_work_center_routes.py` — Functions: configure() + 10 more
- `cockpit_work_intelligence_routes.py` — Cockpit Work Intelligence Routes module
- `cockpit_workspace_observation_routes.py` — Functions: configure() + 5 more
- `cockpit_workspace_routes.py` — Cockpit Workspace Routes module
- `cockpit_workspace_topology_routes.py` — Functions: configure() + 6 more
- `cockpit_workstation_control_routes.py` — Cockpit Workstation Control Routes module
- `cockpit_workstation_presence_routes.py` — Defines PanelUpdate + 2 more
- `computer_use.py` — Execution substrate API — governed multi-layer agent execution.
- `distribution.py` — Distribution API — channel status, intake, approval, and first-boot endpoints.
- `event_bus.py` — Event bus — pub/sub backbone for the substrate's internal communication.
- `execcoord_routes.py` — Execcoord Routes module
- `executor_routes.py` — Executor Routes module
- `governed.py` — Functions: reset_router_cache() + 1 more
- `invariants.py` — Invariant enforcement — validates substrate laws at every transition point.
- `operator.py` — Operator module
- `organism_bridge.py` — Organism Bridge module
- `runtime.py` — SubstrateRuntime: The top-level runtime for the UMH substrate.
- `runtime_state_routes.py` — Runtime State Routes runtime
- `signal_factory.py` — API signal factory — converts HTTP requests to SignalEnvelopes.
- `signal_router.py` — Signal Router module
- `telemetry_routes.py` — Phase 15B: Execution Telemetry route handlers.
- `voice.py` — Defines StartRequest + 1 more
- `workstation.py` — Defines WorkstationExecRequest + 1 more

#### transports/api/webhooks/

- `__init__.py` — Package init
- `calendly_webhook.py` — Functions: verify_signature() + 4 more

#### transports/channels/

- `__init__.py` — Package init
- `channel.py` — Channel module

#### transports/discord/

- `__init__.py` — Package init
- `approval_bridge.py` — Approval Bridge module
- `discord_utils.py` — Discord Utils module
- `interface_adapter_v1.py` — Discord Interface Adapter v1.
- `signal_factory.py` — Discord signal factory -- converts Discord messages to SignalEnvelopes.
- `spine_integration_v1.py` — Spine Integration implementation

#### transports/node_mesh/

- `__init__.py` — Package init
- `config.py` — Config module
- `metrics_buffer.py` — Defines MetricsSnapshot + 1 more
- `registry.py` — Node registry — tracks connected mesh nodes and their state.
- `run.py` — Run module
- `server.py` — Node Mesh WebSocket server — manages node connections and lifecycle.

#### transports/node_mesh/integration/

- `__init__.py` — Package init
- `handlers.py` — Handlers module
- `manifest.py` — Build an IntegrationManifest for a connected mesh node.
- `outcomes.py` — Node mesh outcome receiver — delivers outcomes to remote nodes.
- `signals.py` — Node mesh signal emitter — declares signal types a remote node can emit.
- `types.py` — Defines NodeCapability + 3 more

#### transports/presence/

- `__init__.py` — Package init

#### transports/presence/handlers/

- `__init__.py` — Package init
- `cc_command_handler.py` — Cc Command Handler module
- `intent_handler.py` — Intent Handler module
- `pipeline_handler.py` — Functions: detect_pipeline_update()
- `report_handlers.py` — Report handler functions — backward-compat re-export.
- `substrate_command_handler.py` — Constants/config (defines _REPO_ROOT)
- `voice_handler.py` — Voice handler — skeleton module.

#### transports/presence/handlers/reports/

- `__init__.py` — Package init
- `_common.py` — Shared imports and helpers for report handler modules.
- `adapter.py` — Adapter module
- `capability.py` — Capability module
- `constitution.py` — Constitution module
- `continuity.py` — Continuity module
- `economics.py` — Economics module
- `epistemic.py` — Epistemic module
- `federation.py` — Federation module
- `governance_intelligence.py` — Governance Intelligence module
- `identity.py` — Identity module
- `orchestration.py` — Orchestration module
- `resilience.py` — Resilience module
- `strategy.py` — Strategy module
- `telos.py` — Telos module

### projections/ — Projection-Specific Logic (59 files)


#### projections/

- `__init__.py` — Package init

#### projections/creatoros/

- `__init__.py` — Package init

#### projections/creatoros/integration/

- `__init__.py` — Package init
- `correlation.py` — Thread-safe in-memory correlation map for CreatorOS outcome writeback targeting.
- `handlers.py` — Handlers module
- `manifest.py` — Functions: load_creatoros_config()
- `outcomes.py` — Outcomes module
- `signals.py` — CreatorOSSignalEmitter: Declares signal types and builds envelopes from polled CreatorOS rows.
- `tables.py` — Tables module

#### projections/eos/

- `__init__.py` — Package init
- `entities.py` — Entities module

#### projections/eos/agents/

- `__init__.py` — Package init
- `base.py` — Base module
- `ceo.py` — Ceo module
- `customer_success.py` — Customer Success module
- `engineering.py` — Defines EngineeringAgent
- `finance.py` — EOS Finance Agent — revenue tracking, expense management, financial forecasting.
- `hr.py` — Hr module
- `legal.py` — Legal module
- `marketing.py` — Marketing module
- `operations.py` — Operations module
- `product.py` — Product module
- `sales.py` — Sales module

#### projections/eos/integration/

- `__init__.py` — Package init
- `correlation.py` — Thread-safe in-memory correlation map for EOS outcome writeback targeting.
- `handlers.py` — Handlers module
- `manifest.py` — Manifest module
- `outcomes.py` — Outcomes module
- `poller.py` — EOS poller — background thread that polls EOS Postgres tables for new rows.
- `signals.py` — Signals module
- `tables.py` — Typed query helpers for EOS database tables.

#### projections/eos/views/

- `__init__.py` — Package init
- `activity.py` — Defines ActivityEntry + 2 more
- `kpis.py` — Kpis module
- `pipeline.py` — Defines PipelineStage + 2 more

#### projections/eos/workflows/

- `__init__.py` — Package init
- `browser.py` — Browser module
- `content.py` — Content calendar workflow — schedule and track content across channels.
- `daily.py` — Daily module
- `design.py` — Design module
- `document.py` — Document module
- `execution.py` — Execution module
- `followup.py` — Followup module
- `github.py` — Github module
- `outreach.py` — Outreach workflow — automated prospect outreach sequence.
- `planning.py` — Defines StateAssessment + 2 more
- `research.py` — Research workflow — governed research with outcome tracking.
- `review.py` — Defines ReviewFinding + 2 more
- `runner.py` — WorkflowRunner: Executes multi-step workflows through governed mutation.
- `slack.py` — SlackWorkflow: Slack messaging workflow through governed mutation.
- `types.py` — Workflow types — shared data structures for all EOS workflows.

#### projections/lyfeos/

- `__init__.py` — Package init

#### projections/lyfeos/integration/

- `__init__.py` — Package init
- `correlation.py` — Thread-safe in-memory correlation map for LyfeOS outcome writeback targeting.
- `handlers.py` — Handlers module
- `manifest.py` — Functions: load_lyfeos_config()
- `outcomes.py` — Outcomes module
- `signals.py` — Signals module
- `tables.py` — QuestRow: Typed representation of a LyfeOS quests table row.

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

#### services/auth_flows/

- `__init__.py` — Package init
- `chatgpt.py` — Chatgpt module
- `claude.py` — Claude module

### nodes/ — Node Management (51 files)


#### nodes/

- `__init__.py` — Package init

#### nodes/distribution/

- `__init__.py` — Package init
- `distributor.py` — Distribution Layer — bridges channels to the execution pipeline.
- `first_boot.py` — First Boot — detects whether the system needs onboarding.

#### nodes/environments/

- `__init__.py` — Package init
- `bootstrap_plan.py` — Bootstrap Plan module
- `bootstrap_status.py` — Defines BootstrapCheckStatus + 1 more
- `chrome_visible_launch.py` — Chrome Visible Launch module
- `execution_binding_contracts.py` — Defines EnvironmentType + 11 more
- `execution_binding_validator.py` — Execution Binding Validator module
- `heartbeat.py` — Worker heartbeat for the Environment Bridge.
- `local_pull_protocol.py` — Local Pull Protocol module
- `packet_validator.py` — Packet validator for the Environment Bridge.
- `queue_paths.py` — Queue paths for the Environment Bridge.
- `result_ingestion.py` — Result Ingestion module
- `tmux_surface.py` — Defines TmuxSurfaceStatus + 1 more
- `vps_local_bridge.py` — Vps Local Bridge module
- `w0_packet_builder.py` — W0 Packet Builder module
- `windows_desktop_adapter_contracts.py` — Windows Interactive Desktop Adapter Contracts.
- `windows_desktop_adapter_validator.py` — Windows Desktop Adapter Validator module
- `windows_desktop_request_builder.py` — Windows Interactive Desktop Request Builder.
- `work_packet.py` — Work Packet module
- `workspace_probe.py` — Workspace Probe module

#### nodes/windows/

- `__init__.py` — Package init
- `kokoro_server.py` — Defines SpeechRequest

#### nodes/windows/umh_desktop/

- `__init__.py` — Package init
- `tray.py` — Tray module

#### nodes/windows/umh_node/

- `__init__.py` — Package init
- `client.py` — Client module
- `config.py` — Defines CapabilityConfig + 2 more
- `governance.py` — Node-side governance — validates capability requests against local policy.
- `launcher.py` — Session 1 launcher — starts UMH node daemon in the interactive desktop session.
- `metrics.py` — System metrics collector — CPU, memory, disk, battery, network, GPU.
- `peripheral_scanner.py` — Peripheral Scanner module
- `service.py` — Defines UMHNodeService
- `subprocess_utils.py` — Subprocess helpers for the Windows daemon.
- `workspace.py` — Workspace module

#### nodes/windows/umh_node/adapters/

- `__init__.py` — Package init
- `broadcast.py` — Broadcast module
- `camera.py` — Camera adapter — webcam capture and PTZ control for Insta360 Link 2.
- `clipboard.py` — Clipboard adapter — read/write system clipboard.
- `container.py` — Container module
- `desktop.py` — Desktop module
- `desktop_stream.py` — Defines DesktopStreamAdapter
- `filesystem.py` — FilesystemAdapter: File operations on the local machine.
- `hermes.py` — Hermes module
- `iou_tracker.py` — Defines Track + 1 more
- `object_detector.py` — Object Detector module
- `shell.py` — Shell adapter — executes commands on the local machine.
- `terminal.py` — Terminal module
- `vision_runtime.py` — CVCapability: A single computer vision capability.

### scripts/ — Utility Scripts (146 files)


#### scripts/

- `__init__.py` — Package init
- `_tme_common.py` — Tme Common module
- `agent_task_executor.py` — Agent Task Executor module
- `auto_report_dispatch.py` — Functions: dispatch() + 1 more
- `bis_context.py` — BIS context injector — prints active venture context from VENTURES_JSON.
- `browser_gate_collector.py` — Browser Gate Collector module
- `build_notion_databases.py` — Functions: create_database()
- `build_notion_workspace.py` — Build Notion Workspace module
- `build_palace.py` — Build Palace module
- `build_skill_graph.py` — Build Skill Graph module
- `c29_class_b_runner.py` — C29 Class B Runner module
- `c29_run_beast.py` — Beast launcher for C29 Class B Runner.
- `c29_thesis_run_beast.py` — Beast launcher for C29.5 Thesis Validation Runner.
- `c29_thesis_runner.py` — C29 Thesis Runner module
- `calendar_invite_handler.py` — Calendar Invite Handler module
- `call_prep.py` — Call Prep module
- `check_cpu_gate.py` — Pre-commit gate: block raw subprocess usage in substrate/ and organism/.
- `check_credential_injection.py` — Functions: get_staged_files() + 4 more
- `check_dependency_direction.py` — Check Dependency Direction module
- `check_instance_leak.py` — Check Instance Leak module
- `check_mesh_relay_firewall.py` — Functions: main()
- `check_projection_leak.py` — Check Projection Leak module
- `check_secret_patterns.py` — Functions: get_staged_files() + 2 more
- `check_skill_staleness.py` — Check Skill Staleness module
- `check_stop_condition.py` — Stop hook handler.
- `check_type_divergence.py` — Check Type Divergence module
- `check_ungoverned_mutations.py` — Check Ungoverned Mutations module
- `codebase_graph.py` — Codebase Graph module
- `control_plane_run.py` — Functions: main()
- `create_meetings_db.py` — Create Meetings Db module
- `day_reminder.py` — Constants/config (defines PDT)
- `dead_code_check.py` — Check for dead code in the substrate package.
- `deadline_monitor.py` — Deadline Monitor module
- `decisions.py` — Decisions module
- `deferred.py` — Deferred module
- `detemplatize_skills.py` — Removes hardcoded venture data from all skills.
- `device_sync.py` — Functions: log() + 5 more
- `discord_daily_clear.py` — Constants/config (defines DISCORD_TOKEN)
- `discord_setup_channels.py` — Discord Setup Channels module
- `emit_signal.py` — Emit an orchestrator signal from cron or the shell.
- `env_upsert.py` — Functions: main()
- `eod_sync.py` — Eod Sync module
- `eos_status.py` — Eos Status module
- `export_pipeline.py` — export_pipeline.py — Autonomous export-to-ingestion pipeline.
- `fire_export.py` — Fire Export module
- `generate_codebase_report.py` — Generate Codebase Report module
- `generate_vapid_keys.py` — Generate VAPID key pair for Web Push notifications.
- `github_trinity_ingest.py` — Github Trinity Ingest module
- `goals.py` — CLI entry points for goal management. Wraps runtime/goal_selector.py.
- `gws_scanner_cron.py` — Functions: main()
- `inbox_gps_afternoon.py` — Email GPS — 3pm afternoon inbox pass.
- `inbox_zero_init.py` — Inbox Zero Initialization — run ONCE on first DEX setup.
- `incremental_graph.py` — Incremental Graph module
- `ingest_conversations.py` — Functions: ingest_service() + 1 more
- `ingest_github_repos.py` — Ingest Github Repos module
- `loop_runner.py` — Loop runner CLI — start, stop, and query persistent loops.
- `measure_phase8_batch.py` — Measure Phase8 Batch module
- `memory_continuous_sync.py` — Functions: sweep_promoted_to_canonical() + 2 more
- `memory_instant_sync.py` — Functions: parse_frontmatter()
- `memory_watcher_daemon.py` — Memory Watcher Daemon — runs the substrate memory watcher.
- `merge_graphs.py` — Functions: merge()
- `meta_ide_browser_gate.py` — Meta Ide Browser Gate module
- `midday_checkin.py` — Constants/config (defines PDT)
- `migrate_instance_leaks.py` — Bulk migration tool: mechanically replaces instance-specific values in substrate/ code.
- `morning_intel.py` — Morning Intel module
- `noshow_detector.py` — Noshow Detector module
- `notion_cleanup.py` — Notion Cleanup module
- `notion_outcome_sync.py` — Notion → Neon Outcome Sync
- `notion_seed.py` — Notion Seed module
- `notion_seed_all.py` — Notion Seed All module
- `notion_setup.py` — Notion Setup module
- `notion_sync_poller.py` — Notion Sync Poller — runs every 15 minutes via cron.
- `notion_tasks_sync.py` — Notion Tasks Sync module
- `oauth_grant_gmail.py` — Constants/config (defines _REPO_ROOT)
- `orchestrator.py` — Defines TriggerType + 2 more
- `orchestrator_loop.py` — Orchestrator loop runner.
- `orchestrator_status.py` — Orchestrator Status module
- `organism_mutation_cli.py` — organism_mutation_cli.py — CLI for governed mutations.
- `permission_notify.py` — PermissionRequest hook.
- `phase75a_classifier.py` — Phase75A Classifier module
- `phase75a_dep_scanner.py` — Functions: find_python_files() + 7 more
- `portfolio_brief.py` — Sunday Portfolio Brief — runs at 6am every Sunday.
- `post_meeting_capture.py` — Functions: load_state() + 1 more
- `pre_tool_use_log.py` — PreToolUse hook.
- `query_graph.py` — query_graph.py — Retrieval layer over the EOS codebase knowledge graph.
- `query_skills.py` — query_skills.py — Tool Mastery Engine CLI registry.
- `refresh_fly_token.py` — Refresh Fly.io deploy token using the org token from 1Password.
- `relationship_nurture.py` — Constants/config (defines PDT)
- `rotate_jsonl.py` — Rotate JSONL stores that exceed a size threshold.
- `router_claude_runtime_debug.py` — Router runtime debug helper — prints the actual, live state the router
- `run_continuity_validation.py` — Run Continuity Validation module
- `run_graphify.py` — Constants/config (defines ROOT)
- `run_m1_operator_mvp_check.py` — Run M1 Operator Mvp Check module
- `run_qualification.py` — Adaptive Qualification Runner — convergence-driven, not count-driven.
- `run_reconciliation_ingestion.py` — Multi-document ingestion with reconciliation.
- `run_reconciliation_query_validation.py` — Reconciliation query validation.
- `run_reconciliation_replay_validation.py` — Run Reconciliation Replay Validation module
- `seed_eos_watermarks_to_now.py` — Seed EOS watermarks to NOW — skip historical replay on next poller start.
- `send_to_builder.py` — Send a file to the EOS Discord builder channel.
- `session_bootstrap.py` — Session Bootstrap module
- `session_start_context.py` — Session Start Context module
- `shim_retirement_monitor.py` — Shim Retirement Monitor module
- `subagent_start_context.py` — SubagentStart hook.
- `substrate_audio_loop_cli.py` — Functions: cmd_report() + 5 more
- `substrate_claude_session_cli.py` — Functions: cmd_detect() + 7 more
- `substrate_discord_voice_transport_cli.py` — Substrate Discord Voice Transport Cli module
- `substrate_execution_trace_cli.py` — Substrate Execution Trace Cli module
- `substrate_local_listener.py` — Functions: main()
- `substrate_operator_cli.py` — Substrate Operator Cli module
- `substrate_voice_session_cli.py` — Functions: cmd_start() + 6 more
- `substrate_wake_producer_cli.py` — Functions: cmd_simulate_wake_word() + 5 more
- `summarize_nodes.py` — Functions: build_summaries() + 3 more
- `sync_skills_to_neon.py` — Functions: main()
- `tme_quality_audit.py` — TME Quality Audit — checks content depth, not just structure.
- `tme_staleness_sweep.py` — Functions: main()
- `tool_mastery_author.py` — Functions: main()
- `tool_mastery_manager.py` — Tool Mastery Manager module
- `tool_mastery_research_dispatcher.py` — Tool Mastery Research Dispatcher module
- `user_prompt_capture.py` — UserPromptSubmit hook: capture user messages into conversation files.
- `validate_w0_coherence_dry.py` — W0 Dry Validation with Coherence Envelope.
- `verify_completion_claim.py` — Completion Claim Verifier — runs at Stop hook.
- `verify_deploy.py` — Standalone post-deploy verification script.
- `verify_knowledge_system.py` — verify_knowledge_system.py — Acceptance check for the EOS cognition stack.
- `verify_pr47_cadence_learning.py` — Functions: main()
- `verify_pr47_production.py` — Phase 10.3D — Production merge verification for PR #47.
- `verify_pr47_reliability.py` — Verify Pr47 Reliability module
- `verify_template_store.py` — Verify the runtime template store is populated and valid.
- `verify_tool_skill.py` — Verify Tool Skill module
- `waiting_on_checker.py` — WAITING_ON checker — scans emails in WAITING_ON folder
- `watch_graph.py` — Watch Graph module
- `week_architect.py` — Constants/config (defines PDT)
- `weekly_review.py` — Weekly Review module
- `wiki_stop_hook.py` — Functions: main()

#### scripts/c40b_phases/

- `__init__.py` — Package init
- `campaign_context.py` — C40B Campaign Context — shared state across all phases.
- `embodiment_harness.py` — Embodiment Harness module
- `phase1_runtime_audit.py` — Phase1 Audit runtime
- `phase2_runtime_fix.py` — Defines DefectEntry
- `phase3_operator_qualification.py` — Phase3 Operator Qualification module
- `phase4_embodied_stress.py` — Phase4 Embodied Stress module
- `phase5_runtime_certification.py` — Phase5 Certification runtime
- `report_generator.py` — C40B Report Generator — campaign report + Discord dispatch.

#### scripts/scheduled/

- `morning_prep_cp.py` — Functions: main()
- `nightly_consolidation_cp.py` — Functions: main()
- `weekly_review_cp.py` — Functions: main()

#### scripts/workers/

- `discord_approval_worker.py` — Functions: drain_once()

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


#### umh/

- `desktop_relay.py` — Desktop Relay module
- `vision_relay.py` — Vision Relay module
- `voice_server.py` — Voice Server module

### saas/ — EOS Projection (SaaS Layer) (1 files)


#### saas/node_modules/shell-quote/

- `print.py` — Print module

### cockpit/src/ — Electron + React Frontend (308 files)


#### cockpit/src/main/

- `index.ts` — Electron main process — creates BrowserWindow, spawns voice/vision/browser relay child processes

#### cockpit/src/preload/

- `index.ts` — Electron preload bridge — contextBridge.exposeInMainWorld for secure IPC

#### cockpit/src/renderer/

- `App.tsx` — Root React app — wraps Clerk auth, keyboard hooks, organism realtime, routing
- `constants.ts` — App-wide constants (API base URLs, polling intervals, feature flags)
- `global.d.ts` — TypeScript global type declarations (window.electron, env vars)
- `main.tsx` — React root mount — createRoot with ClerkProvider
- `sw.ts` — Service worker for PWA push notifications and offline caching

#### cockpit/src/renderer/__tests__/

- `apiClient.test.ts` — Unit tests for API client (fetchApi, error handling)
- `cockpitStore.test.ts` — Unit tests for cockpit Zustand store
- `setup.ts` — Vitest test setup — imports jest-dom matchers

#### cockpit/src/renderer/api/

- `broadcast-ws.ts` — API client: broadcast-ws
- `browser-ws.ts` — API client: browser-ws
- `client.ts` — API client: client
- `device-presence.ts` — API client: device-presence
- `tts-playback-controller.ts` — TTS Playback Controller — manages audio playback with iOS unlock support.
- `vision-ws.ts` — API client: vision-ws
- `voice-controller.ts` — API client: voice-controller
- `voice-turn-assembler.ts` — Voice Turn Assembler — collects STT transcript segments into a single
- `voice-ws.ts` — API client: voice-ws
- `websocket.ts` — API client: websocket

#### cockpit/src/renderer/components/

- `ActionRequired.tsx` — UI component: ActionRequired
- `AgentCard.tsx` — UI component: AgentCard
- `CallOverlay.tsx` — UI component: CallOverlay
- `CameraController.tsx` — UI component: CameraController
- `CameraPreview.tsx` — UI component: CameraPreview
- `CanvasMenuBar.tsx` — ─── Types ──────────────────────────────────────────────────────
- `ChannelList.tsx` — UI component: ChannelList
- `ChannelView.tsx` — UI component: ChannelView
- `CommandPalette.tsx` — UI component: CommandPalette
- `ConnectionBanner.tsx` — UI component: ConnectionBanner
- `ControlPanel.tsx` — ── colour maps ──
- `CronTable.tsx` — UI component: CronTable
- `DetailDrawer.tsx` — UI component: DetailDrawer
- `DeviceDiagnosisInline.tsx` — UI component: DeviceDiagnosisInline
- `DeviceOnboardingCard.tsx` — UI component: DeviceOnboardingCard
- `ErrorBoundary.tsx` — UI component: ErrorBoundary
- `EventConsole.tsx` — UI component: EventConsole
- `ExecutionTimeline.tsx` — UI component: ExecutionTimeline
- `ExecutorBadge.tsx` — UI component: ExecutorBadge
- `FabLarge.tsx` — UI component: FabLarge
- `FabMedium.tsx` — UI component: FabMedium
- `FabSmall.tsx` — UI component: FabSmall
- `GraphView.tsx` — UI component: GraphView
- `HudBar.tsx` — UI component: HudBar
- `IDEMenuBar.tsx` — ─── Types ──────────────────────────────────────────────────────
- `LeftDrawer.tsx` — UI component: LeftDrawer
- `LeftRail.tsx` — UI component: LeftRail
- `LivePreview.tsx` — UI component: LivePreview
- `NavRail.tsx` — UI component: NavRail
- `OverlayToggle.tsx` — UI component: OverlayToggle
- `ResumeCard.tsx` — UI component: ResumeCard
- `RightDrawer.tsx` — UI component: RightDrawer
- `RightRail.tsx` — UI component: RightRail
- `RingGauge.tsx` — UI component: RingGauge
- `RuntimeBadge.tsx` — UI component: RuntimeBadge
- `Shell.tsx` — UI component: Shell
- `SplitPane.tsx` — UI component: SplitPane
- `SplitPreview.tsx` — UI component: SplitPreview
- `StatusBadge.tsx` — UI component: StatusBadge
- `StorePolling.tsx` — UI component: StorePolling
- `TaskBlock.tsx` — UI component: TaskBlock
- `TimelineView.tsx` — UI component: TimelineView
- `TitleBar.tsx` — UI component: TitleBar
- `TopologyMap.tsx` — UI component: TopologyMap
- `TrackingPanel.tsx` — UI component: TrackingPanel
- `ViewportSelector.tsx` — UI component: ViewportSelector
- `VisionPopout.tsx` — UI component: VisionPopout
- `VoiceCommandBar.tsx` — UI component: VoiceCommandBar
- `VoiceRouteHud.tsx` — VoiceRouteHud — compact display of the active voice route.
- `VoiceWaveform.tsx` — UI component: VoiceWaveform

#### cockpit/src/renderer/components/canvas/

- `AgentCanvasNode.tsx` — Canvas component: AgentCanvasNode
- `AgentCanvasWorkspace.tsx` — Canvas component: AgentCanvasWorkspace
- `BaseCanvas.tsx` — Canvas component: BaseCanvas
- `CanvasContextMenu.tsx` — Canvas component: CanvasContextMenu
- `CanvasPalette.tsx` — Canvas component: CanvasPalette
- `CanvasToolbar.tsx` — Canvas component: CanvasToolbar
- `CanvasWindow.tsx` — Canvas component: CanvasWindow
- `CanvasWorkspace.tsx` — Canvas component: CanvasWorkspace
- `HarnessCanvasWorkspace.tsx` — Canvas component: HarnessCanvasWorkspace
- `LoopCanvasWorkspace.tsx` — Canvas component: LoopCanvasWorkspace
- `OrganismCanvasWorkspace.tsx` — Canvas component: OrganismCanvasWorkspace
- `UnifiedCanvasWorkspace.tsx` — Canvas component: UnifiedCanvasWorkspace
- `WindowContent.tsx` — Canvas component: WindowContent
- `WorkflowCanvasWorkspace.tsx` — Canvas component: WorkflowCanvasWorkspace
- `WorkflowConnection.tsx` — Canvas component: WorkflowConnection
- `WorkflowNode.tsx` — ── Color + icon mapping ───────────────────────────────────────

#### cockpit/src/renderer/components/canvas/windows/

- `AgentConfigView.tsx` — Canvas window type: AgentConfigView
- `AgentWindowContent.tsx` — Canvas window type: AgentWindowContent
- `BrowserWindowContent.tsx` — Canvas window type: BrowserWindowContent
- `DesktopWindowContent.tsx` — Canvas window type: DesktopWindowContent
- `PanelWindowContent.tsx` — Canvas window type: PanelWindowContent
- `PreviewWindowContent.tsx` — Canvas window type: PreviewWindowContent
- `TerminalWindowContent.tsx` — Canvas window type: TerminalWindowContent
- `VisionWindowContent.tsx` — Canvas window type: VisionWindowContent

#### cockpit/src/renderer/components/cards/

- `ApprovalCard.tsx` — Card component: ApprovalCard
- `CommandResultCard.tsx` — Card component: CommandResultCard
- `ConversationBubble.tsx` — Card component: ConversationBubble
- `ErrorCard.tsx` — Card component: ErrorCard
- `RRIPRenderer.tsx` — Card component: RRIPRenderer
- `ReportCard.tsx` — Card component: ReportCard

#### cockpit/src/renderer/components/rooms/

- `ChannelCreateModal.tsx` — Room component: ChannelCreateModal
- `ChannelSidebar.tsx` — Room component: ChannelSidebar
- `ForumChannelView.tsx` — Room component: ForumChannelView
- `GuestJoinPage.tsx` — Room component: GuestJoinPage
- `InvitePanel.tsx` — Room component: InvitePanel
- `MeetingRoomPanel.tsx` — Room component: MeetingRoomPanel
- `MemberListPanel.tsx` — Room component: MemberListPanel
- `RoomAuditLog.tsx` — Room component: RoomAuditLog
- `RoomChatPanel.tsx` — Room component: RoomChatPanel
- `RoomDexPanel.tsx` — Room component: RoomDexPanel
- `RoomMainView.tsx` — Room component: RoomMainView
- `RoomRightRail.tsx` — Room component: RoomRightRail
- `ServerCreateModal.tsx` — Room component: ServerCreateModal
- `ServerRail.tsx` — Room component: ServerRail
- `TextChannelView.tsx` — Room component: TextChannelView
- `ThreadPanel.tsx` — Room component: ThreadPanel
- `VoiceRoomPanel.tsx` — Room component: VoiceRoomPanel

#### cockpit/src/renderer/components/vision/

- `CameraModeSelector.tsx` — Vision component: CameraModeSelector
- `DiagnosticsPanel.tsx` — Vision component: DiagnosticsPanel
- `FaceTrackingOverlay.tsx` — Vision component: FaceTrackingOverlay
- `HandLandmarkOverlay.tsx` — Vision component: HandLandmarkOverlay
- `NotificationCenter.tsx` — Vision component: NotificationCenter
- `PoseSkeletonOverlay.tsx` — Vision component: PoseSkeletonOverlay
- `SceneInventory.tsx` — Vision component: SceneInventory
- `StatusHud.tsx` — Vision component: StatusHud
- `ToastContainer.tsx` — Vision component: ToastContainer
- `TrackedObjectBox.tsx` — Vision component: TrackedObjectBox
- `VisionConnectionStatus.tsx` — Vision component: VisionConnectionStatus
- `VisionOverlay.tsx` — Vision component: VisionOverlay
- `VisionSettings.tsx` — Vision component: VisionSettings
- `index.ts` — Vision component: index

#### cockpit/src/renderer/constants/

- `devices.ts` — Device Naming Protocol — single source of truth for all device labels.

#### cockpit/src/renderer/hooks/

- `useBroadcastConnection.ts` — React hook: useBroadcastConnection
- `useBrowserStream.ts` — React hook: useBrowserStream
- `useCanvasDrag.ts` — React hook: useCanvasDrag
- `useCanvasResize.ts` — React hook: useCanvasResize
- `useConferenceRoom.ts` — React hook: useConferenceRoom
- `useIsMobile.ts` — React hook: useIsMobile
- `useKeyboard.ts` — React hook: useKeyboard
- `useOrganismRealtime.ts` — React hook: useOrganismRealtime
- `usePolling.ts` — React hook: usePolling
- `useVisionConnection.ts` — React hook: useVisionConnection
- `useVoiceDetection.ts` — React hook: useVoiceDetection
- `useVoiceRoom.ts` — React hook: useVoiceRoom

#### cockpit/src/renderer/lib/

- `pushNotifications.ts` — PWA push notification registration and handling
- `rrip-normalize.ts` — RRIP (Rich Response Interchange Protocol) data normalization
- `time.ts` — Time formatting utilities (relative timestamps, duration display)

#### cockpit/src/renderer/operator/

- `speechInputAdapter.ts` — Speech-to-text input adapter for voice commands
- `voiceTypes.ts` — TypeScript types for voice session state and events

#### cockpit/src/renderer/panels/

- `ActionsPanel.tsx` — UI panel component for Actions view
- `ActivityPanel.tsx` — UI panel component for Activity view
- `AnalyticsPanel.tsx` — UI panel component for Analytics view
- `ApprovalsPanel.tsx` — UI panel component for Approvals view
- `BroadcastPanel.tsx` — UI panel component for Broadcast view
- `BrowserPanel.tsx` — UI panel component for Browser view
- `BuildLoopPanel.tsx` — UI panel component for BuildLoop view
- `CapabilitiesPanel.tsx` — UI panel component for Capabilities view
- `CapabilityMapPanel.tsx` — UI panel component for CapabilityMap view
- `CommandCenterPanel.tsx` — UI panel component for CommandCenter view
- `CommandsPanel.tsx` — UI panel component for Commands view
- `CommsPanel.tsx` — UI panel component for Comms view
- `CompanyPanel.tsx` — UI panel component for Company view
- `ConferenceRoomsPanel.tsx` — UI panel component for ConferenceRooms view
- `ContinuityPanel.tsx` — UI panel component for Continuity view
- `DashboardPanel.tsx` — UI panel component for Dashboard view
- `DelegationPanel.tsx` — UI panel component for Delegation view
- `DistributedRuntimePanel.tsx` — UI panel component for DistributedRuntime view
- `EngineeringPanel.tsx` — UI panel component for Engineering view
- `ExecCoordPanel.tsx` — UI panel component for ExecCoord view
- `ExecutionPanel.tsx` — UI panel component for Execution view
- `ExecutivePanel.tsx` — UI panel component for Executive view
- `ExecutorPanel.tsx` — UI panel component for Executor view
- `GoalPanel.tsx` — UI panel component for Goal view
- `GovernancePanel.tsx` — UI panel component for Governance view
- `InfrastructurePanel.tsx` — UI panel component for Infrastructure view
- `IntelligencePanel.tsx` — UI panel component for Intelligence view
- `IntentPanel.tsx` — UI panel component for Intent view
- `KnowledgePanel.tsx` — UI panel component for Knowledge view
- `LearningPanel.tsx` — UI panel component for Learning view
- `MVPReadinessPanel.tsx` — UI panel component for MVPReadiness view
- `MemoryPanel.tsx` — UI panel component for Memory view
- `MetaIDEPanel.tsx` — UI panel component for MetaIDE view
- `OperatingLoopPanel.tsx` — UI panel component for OperatingLoop view
- `OperationsPanel.tsx` — UI panel component for Operations view
- `OperatorContinuityPanel.tsx` — UI panel component for OperatorContinuity view
- `OperatorHomePanel.tsx` — UI panel component for OperatorHome view
- `OperatorPanel.tsx` — UI panel component for Operator view
- `OperatorTimelinePanel.tsx` — UI panel component for OperatorTimeline view
- `OrchestratorPanel.tsx` — UI panel component for Orchestrator view
- `OrganismLoopPanel.tsx` — UI panel component for OrganismLoop view
- `OrganismMapPanel.tsx` — UI panel component for OrganismMap view
- `OrganismPanel.tsx` — UI panel component for Organism view
- `PortfolioPanel.tsx` — UI panel component for Portfolio view
- `PredictionPanel.tsx` — UI panel component for Prediction view
- `PresencePanel.tsx` — UI panel component for Presence view
- `ProfilePanel.tsx` — UI panel component for Profile view
- `ProjectionIntegrationPanel.tsx` — UI panel component for ProjectionIntegration view
- `ProjectionPanel.tsx` — UI panel component for Projection view
- `ProofInspectorPanel.tsx` — UI panel component for ProofInspector view
- `PropagationGraphPanel.tsx` — UI panel component for PropagationGraph view
- `RealityGraphPanel.tsx` — UI panel component for RealityGraph view
- `RealityIntelligencePanel.tsx` — UI panel component for RealityIntelligence view
- `RealityTimelinePanel.tsx` — UI panel component for RealityTimeline view
- `RecoveryDashboardPanel.tsx` — UI panel component for RecoveryDashboard view
- `RuntimePanel.tsx` — UI panel component for Runtime view
- `ScreenAwarenessPanel.tsx` — UI panel component for ScreenAwareness view
- `SelfBuildPanel.tsx` — UI panel component for SelfBuild view
- `ServiceGraphPanel.tsx` — UI panel component for ServiceGraph view
- `SessionPanel.tsx` — UI panel component for Session view
- `SessionResumePanel.tsx` — UI panel component for SessionResume view
- `SettingsPanel.tsx` — UI panel component for Settings view
- `SkillsPanel.tsx` — UI panel component for Skills view
- `StateAuthorityPanel.tsx` — UI panel component for StateAuthority view
- `StrategicPanel.tsx` — UI panel component for Strategic view
- `StrategyPanel.tsx` — UI panel component for Strategy view
- `TasksPanel.tsx` — UI panel component for Tasks view
- `TickLoopPanel.tsx` — UI panel component for TickLoop view
- `TmuxPanel.tsx` — UI panel component for Tmux view
- `UMHNodePanel.tsx` — UI panel component for UMHNode view
- `UnifiedExecutionPanel.tsx` — UI panel component for UnifiedExecution view
- `UniversalWorkPanel.tsx` — UI panel component for UniversalWork view
- `VisionPanel.tsx` — UI panel component for Vision view
- `WorkIntelligencePanel.tsx` — UI panel component for WorkIntelligence view
- `WorkPanel.tsx` — UI panel component for Work view
- `WorkspaceTopologyPanel.tsx` — WorkspaceTopologyPanel — workspace→repos→runtimes→devices topology view.
- `WorkstationPanel.tsx` — UI panel component for Workstation view
- `WorldModelPanel.tsx` — UI panel component for WorldModel view

#### cockpit/src/renderer/stores/

- `actionsStore.ts` — Zustand state store for actions data
- `activityStore.ts` — Zustand state store for activity data
- `agentCanvasStore.ts` — ── Types ──────────────────────────────────────────────────────
- `agentStore.ts` — Zustand state store for agent data
- `analyticsStore.ts` — Zustand state store for analytics data
- `bootstrapStore.ts` — Zustand state store for bootstrap data
- `broadcastStore.ts` — Zustand state store for broadcast data
- `buildLoopStore.ts` — Zustand state store for buildLoop data
- `canvasStore.ts` — ── Types ──────────────────────────────────────────────────────
- `capabilityIntelligenceStore.ts` — Zustand state store for capabilityIntelligence data
- `capabilityMapStore.ts` — Zustand state store for capabilityMap data
- `chatStore.ts` — Zustand state store for chat data
- `cockpitStore.ts` — Zustand state store for cockpit data
- `coherenceStore.ts` — Zustand state store for coherence data
- `collapseStore.ts` — Zustand state store for collapse data
- `configStore.ts` — Zustand state store for config data
- `delegationStore.ts` — Zustand state store for delegation data
- `deviceSessionStore.ts` — Zustand state store for deviceSession data
- `deviceStore.ts` — Zustand state store for device data
- `editorStore.ts` — Zustand state store for editor data
- `engineeringStore.ts` — Zustand state store for engineering data
- `executionSummaryStore.ts` — Zustand state store for executionSummary data
- `executiveStore.ts` — Zustand state store for executive data
- `goalStore.ts` — Zustand state store for goal data
- `governanceStore.ts` — -- Interfaces ---------------------------------------------------------
- `harnessCanvasStore.ts` — Zustand state store for harnessCanvas data
- `intelligenceStore.ts` — Zustand state store for intelligence data
- `intentStore.ts` — Zustand state store for intent data
- `knowledgeStore.ts` — Zustand state store for knowledge data
- `learningStore.ts` — Zustand state store for learning data
- `loopCanvasStore.ts` — Zustand state store for loopCanvas data
- `memoryStore.ts` — Zustand state store for memory data
- `metaIDEStore.ts` — Zustand state store for metaIDE data
- `mvpReadinessStore.ts` — Zustand state store for mvpReadiness data
- `operatingLoopStore.ts` — Zustand state store for operatingLoop data
- `operationsStore.ts` — Zustand state store for operations data
- `operatorExperienceStore.ts` — Zustand state store for operatorExperience data
- `operatorHomeStore.ts` — Zustand state store for operatorHome data
- `operatorLoopStore.ts` — Zustand state store for operatorLoop data
- `operatorTimelineStore.ts` — Zustand state store for operatorTimeline data
- `orchestratorAwarenessStore.ts` — Zustand state store for orchestratorAwareness data
- `organismCanvasStore.ts` — Zustand state store for organismCanvas data
- `organismLoopStore.ts` — Zustand state store for organismLoop data
- `organismStore.ts` — Zustand state store for organism data
- `predictionStore.ts` — Zustand state store for prediction data
- `presenceStore.ts` — Zustand state store for presence data
- `projectionIntegrationStore.ts` — Zustand state store for projectionIntegration data
- `proofInspectorStore.ts` — Zustand state store for proofInspector data
- `providerRegistryStore.ts` — Zustand state store for providerRegistry data
- `realityGraphStore.ts` — Zustand state store for realityGraph data
- `realityIntelligenceStore.ts` — Zustand state store for realityIntelligence data
- `realityTimelineStore.ts` — Zustand state store for realityTimeline data
- `realtimeStore.ts` — Zustand state store for realtime data
- `recoveryDashboardStore.ts` — Zustand state store for recoveryDashboard data
- `roomsStore.ts` — Zustand state store for rooms data
- `screenAwarenessStore.ts` — Zustand state store for screenAwareness data
- `serviceGraphStore.ts` — Zustand state store for serviceGraph data
- `settingsStore.ts` — Zustand state store for settings data
- `stateAuthorityStore.ts` — Zustand state store for stateAuthority data
- `strategicStore.ts` — Zustand state store for strategic data
- `systemStore.ts` — Zustand state store for system data
- `taskStore.ts` — Zustand state store for task data
- `umhNodeStore.ts` — Zustand state store for umhNode data
- `unifiedApprovalStore.ts` — Zustand state store for unifiedApproval data
- `unifiedCanvasStore.ts` — Zustand state store for unifiedCanvas data
- `unifiedExecutionStore.ts` — Zustand state store for unifiedExecution data
- `unifiedWorkstationStore.ts` — Zustand state store for unifiedWorkstation data
- `viewContextStore.ts` — Zustand state store for viewContext data
- `visionStore.ts` — Zustand state store for vision data
- `voiceSessionStore.ts` — Zustand state store for voiceSession data
- `voiceStore.ts` — Zustand state store for voice data
- `workIntelligenceStore.ts` — Zustand state store for workIntelligence data
- `workflowCanvasStore.ts` — ── Types ──────────────────────────────────────────────────────
- `workspaceContextStore.ts` — Zustand state store for workspaceContext data
- `workspaceTopologyStore.ts` — Workspace Topology Store — Phase 27
- `workstationSessionStore.ts` — Zustand state store for workstationSession data
- `worldModelStore.ts` — Zustand state store for worldModel data

#### cockpit/src/renderer/types/

- `rooms.ts` — TypeScript types for Discord-style rooms (channels, permissions, roles)
- `routes.ts` — Route definitions and panel-to-route mapping constants
- `rrip.ts` — TypeScript types for RRIP (Rich Response Interchange Protocol) messages

#### cockpit/src/renderer/utils/

- `canvasCoords.ts` — Canvas coordinate math utilities (pan, zoom clamping, viewport transforms)

### Root-Level Files

**Architecture & Philosophy:**
- `ARCHITECTURE.md` — Master architecture specification (26KB)
- `PLATFORM_SPEC.md` — Frozen v1.0.0 platform specification (29KB)
- `PHILOSOPHY.md` — UMH philosophy: Reality, Intelligence, Personalization, Execution (12KB)
- `EPISTEMOLOGY.md` — How the organism learns — templates, invariants, capability stack (21KB)
- `PROTOCOLS.md` — 4-layer protocol documentation L0-L3 (10KB)
- `AGENTS.md` — Cross-agent configuration reference
- `cloud.md` — System context for knowledge system
- `README.md` — Project readme

**Build & Deploy:**
- `Dockerfile` — Docker image build (Python 3.11-slim base)
- `docker-compose.yml` — 6 services: os-discord, os-operator, os-webhook, os-scraper, os-browser, os-livekit
- `Makefile` — Build automation targets
- `pyproject.toml` — Ruff, mypy, pytest configuration
- `requirements.txt` — Python dependency list
- `install.sh` — Initial setup script
- `setup.sh` — Environment setup
- `patch_pycord.py` — Pycord library patch
- `skills-lock.json` — Skill version lockfile

**Config:**
- `.gitignore` — Git ignore rules (secrets, caches, generated files, runtime state)
- `.dockerignore` — Docker build context exclusions
- `.env.example` — Template showing required environment variables
- `.env.sessions.tpl` — 1Password template for session secrets (op:// URIs)
- `.mcp.json` — MCP server configuration

**Developer Docs:**
- `CLAUDE.md` — Developer agent soul document (20KB — read this first)
- `CLAUDE.local.md` — Local preferences (gitignored)

**Campaign Reports:** C31 through C33 reports (10 files documenting substrate convergence, operational hardening, and meta-harness validation campaigns)


### Non-Code Directories (Markdown, JSON, YAML, Shell)

These directories contain configuration, documentation, skills, and knowledge — not source code.
Documented at the subdirectory level since individual files are mostly markdown/JSON.

#### .claude/ — Claude Code Configuration

| Subdirectory | Count | Purpose |
|-------------|-------|---------|
| `agents/` | 4 | CC native subagent definitions (code-reviewer, researcher, simplifier, verifier) |
| `commands/` | 24 | Slash command definitions (GSD workflow, debug, deploy, etc.) |
| `hooks/` | 3 | Pre/post hooks (stop hook, pre-tool-use) |
| `rules/` | 10 | Enforcement rules (architecture-layers, type-coherence, projection-boundary, etc.) |
| `skills/` | 31 | CC skill definitions (deploy-service, new-agent, debug-agent, etc.) |
| `settings.json` | — | Claude Code settings (model, permissions, MCP servers) |
| `CLAUDE.md` | — | Developer agent soul document (dotdir version) |

#### agents/ — Agent Soul Documents (11 files)

- `ceo_agent.md` — ---
- `computer_use_agent.md` — ---
- `customer_success_agent.md` — ---
- `engineering_agent.md` — ---
- `finance_agent.md` — ---
- `hr_agent.md` — ---
- `legal_agent.md` — ---
- `marketing_agent.md` — ---
- `operations_agent.md` — ---
- `product_agent.md` — ---
- `sales_agent.md` — ---


#### skills/ — Skill Directories (25 domains)

| Directory | Purpose |
|-----------|---------|

| `Content/` | Content (2 files) |
| `CustomerSuccess/` | Customersuccess (2 files) |
| `Marketing/` | Marketing (4 files) |
| `Ops/` | Ops (13 files) |
| `Outreach/` | Outreach (2 files) |
| `Research/` | Research (6 files) |
| `Sales/` | Sales (20 files) |
| `brandkit/` | Premium brand-kit image generation skill for creating high-end brand-guidelin... (1 files) |
| `content/` | Content (3 files) |
| `design-taste-frontend/` | Anti-slop frontend skill for landing pages, portfolios, and redesigns. The ag... (1 files) |
| `design-taste-frontend-v1/` | The original v1 taste-skill, preserved for projects depending on its exact be... (1 files) |
| `developer/` | Developer (1 files) |
| `full-output-enforcement/` | Overrides default LLM truncation behavior. Enforces complete code generation,... (1 files) |
| `gpt-taste/` | Elite UX/UI & Advanced GSAP Motion Engineer. Enforces Python-driven true rand... (1 files) |
| `high-end-visual-design/` | Teaches the AI to design like a high-end agency. Defines the exact fonts, spa... (1 files) |
| `image-to-code/` | Elite website image-to-code skill for Codex. For visually important web tasks... (1 files) |
| `imagegen-frontend-mobile/` | Elite mobile app image-generation skill for creating premium, app-native scre... (1 files) |
| `imagegen-frontend-web/` | Elite frontend image-direction skill for generating premium, conversion-aware... (1 files) |
| `industrial-brutalist-ui/` | Raw mechanical interfaces fusing Swiss typographic print with military termin... (1 files) |
| `meta/` | Meta (15 files) |
| `minimalist-ui/` | Clean editorial-style interfaces. Warm monochrome palette, typographic contra... (1 files) |
| `redesign-existing-projects/` | Upgrades existing websites and apps to premium quality. Audits current design... (1 files) |
| `refero-design/` | Primary/default skill for UI design, product design, web design, landing page... (1 files) |
| `saas-dev-skill/` | Saas Dev Skill (5183 files) |
| `stitch-design-taste/` | Semantic Design System Skill for Google Stitch. Generates agent-friendly DESI... (2 files) |
| `tools/` | Tools (254 files) |


#### knowledge/ — Wiki System

| Subdirectory | Purpose |
|-------------|---------|
| `concepts/` | Concept definitions |
| `decisions/` | Decision records |
| `domains/` | Domain knowledge (business, technical) |
| `entities/` | Entity definitions |
| `palace/` | Memory palace rooms — entry points for knowledge retrieval |
| `skills/` | Skill knowledge files |
| `sources/` | Source references |
| `synthesis/` | Knowledge synthesis outputs |
| `index.md` | Wiki index |
| `WIKI_RULES.md` | Rules for wiki contributions |
| `retrieval_rules.md` | Enforced retrieval hierarchy |

#### docs/ — Project Documentation

| Subdirectory | Purpose |
|-------------|---------|
| `strategy/` | Business strategy documents |
| `operations/` | Operational procedures |
| Root files | deploy.md, corporate-structure.md, brand-identity.md, SYSTEM_ARCHITECTURE.md |

#### infra/ — Infrastructure Configuration

| File | Purpose |
|------|---------|
| `device_registry.json` | Source of truth for device names, roles, IPs |
| `service_dependency_registry.json` | Service dependency map |
| `workspace_registry.json` | Workspace definitions |
| `project_registry.json` | Project registry |
| `umh_node_registry.json` | UMH node registry |
| `state_authority_registry.json` | State authority definitions |
| `crontab.managed` | Managed cron schedule |
| `livekit.yaml.tpl` | LiveKit server config template (1Password URIs) |
| `docker/` | Docker-specific configs |
| `scripts/` | Infrastructure scripts |

#### config/

| File | Purpose |
|------|---------|
| `nonsecret.env` | Non-secret environment variables (safe to commit) |

#### docker/

| Subdirectory | Purpose |
|-------------|---------|
| `computer-use/` | Computer-use Docker configuration |
