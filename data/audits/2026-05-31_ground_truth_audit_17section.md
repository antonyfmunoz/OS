I now have sufficient data to produce the final report.

# GROUND-TRUTH AUDIT REPORT -- UMH/OS Repository
## Date: 2026-05-31

---

### 1. EXECUTIVE REALITY SUMMARY

UMH (Universal Mastery Hierarchy) is a pre-revenue AI substrate platform at /opt/OS, built by a solo founder as infrastructure for running business operations through AI agents. The repository contains 34,886 files (excluding worktrees/caches), of which 1,186 are Python and 92 are TypeScript/TSX in the active cockpit. The system runs on a single Hostinger VPS (96GB disk at 80% usage, 7.8GB RAM at 53% usage) with 3 active Docker containers, 5 systemd services, 31 cron jobs, and an active organism daemon at tick 2,463.

The system is currently in a degraded operational state. All LLM providers in the Discord bot's fallback chain are exhausted (Gemini 429 free-tier, Groq 429 TPD limit, Perplexity 401 quota exceeded). The bot is alive but functionally brain-dead -- it processes signals but cannot generate intelligent responses, defaulting to deterministic fallback. The operator API is healthy on port 8091. The cockpit is deployed to Fly.io (machine running in LAX region) but was unreachable via universalmetaharness.tech during this audit (DNS/routing issue -- Fly machine is "started" per flyctl).

The codebase is architecturally sophisticated but over-built for a pre-revenue solo project. The substrate/ package alone has 685 Python files with 10 empty placeholder directories. The organism subsystem (185 files) generates 17K+ events and ticks every 5 seconds but produces zero execution journal entries -- the recording pathway is broken. A 238MB metrics JSONL file and 153MB of logs consume significant disk. The knowledge system (codebase graph, node summaries, memory palace) is 5 days stale with 412 Python files modified since the last rebuild.

The project has strong architectural governance (pre-commit hooks enforcing type coherence, instance context boundaries, and dependency direction) and a test suite of 1,783 collected tests. However, the gap between documented ambition and operational reality is wide: the system aspires to be a multi-projection universal platform but currently serves a single user with a single Discord bot in degraded state.

---

### 2. CONFIRMED ARCHITECTURE

**Four-layer dependency model (VERIFIED -- pre-commit enforced):**
```
projections/ (47 .py files) --> transports/ (72 .py files) --> adapters/ (95 .py files) --> substrate/ (685 .py files)
```

**Substrate internal structure (VERIFIED):**
- `substrate/__init__.py` -- public API: Substrate class, SignalEnvelope, types, sockets
- `substrate/types.py` -- 87 Pydantic/Enum classes (single type system)
- `substrate/canonical_types.py` -- registry of 134 canonical types (132 in substrate/, 2 in nodes/)
- `substrate/control_plane/runtime/gateway.py` -- Gateway class (1,927 lines), EntrepreneurOSGateway alias at line 1927
- `substrate/control_plane/runtime/cognitive_loop.py` -- 1,539 lines
- `substrate/control_plane/orchestrator/orchestrator.py` -- 1,910 lines, CEOAgent class at line 73
- `substrate/execution/spine.py` -- ConcreteExecutionSpine (419 lines, single public method: execute())
- `substrate/sockets/` -- 16 abstract port files (channel, notification, capability, outcome, etc.)
- `substrate/organism/` -- 185 files (120 production + 65 test)
- `substrate/execution/` -- 163 files
- `substrate/execution/workers/workstation/` -- 42 files of "constitutional engines"

**Transport layer (VERIFIED):**
- `transports/api/` -- 28 Python files, FastAPI-based cockpit/operator API
- `transports/api/cockpit.py` -- 2,304 lines (under 3K limit)
- `transports/api/http/` -- 17 TypeScript files (Hono-based API)
- `transports/presence/` -- Discord command routing and report handlers

**Adapter layer (VERIFIED):**
- `adapters/models/model_router.py` -- 1,442 lines, `call_with_fallback()` (457 lines) is the single intelligence entry point
- 10-provider fallback chain: cc_sdk -> Gemini -> Groq -> Anthropic -> Perplexity -> Ollama -> Codex -> Hermes -> OpenCode

**Services layer (VERIFIED):**
- `services/` -- 22 Python files, deployment entrypoints only
- `services/discord_bot.py` -- 1,974 lines (primary production service)

**Pre-commit hooks (VERIFIED -- `.git/hooks/pre-commit` exists):**
- Gate 1: `scripts/check_type_divergence.py` -- passes clean
- Gate 2: `scripts/check_instance_leak.py` -- passes clean
- Missing from hook: `check_dependency_direction.py` and `check_projection_leak.py` (exist as scripts but NOT wired into pre-commit)

**Dependency direction violations (VERIFIED):**
- 0 actual `import` statements from transports/services in substrate/ production code (the 4 grep hits are in comments/docstrings)
- 3 imports from adapters/ in substrate/ (all `from adapters.models.agent_runtime import AgentRuntime`)
- 10 imports from projections/ in transports/ (lazy imports in cockpit entity routes and app.py)
- `scripts/check_dependency_direction.py` passes clean (implies these are exempted or below threshold)

---

### 3. ACTIVE RUNTIME PATHS

**Docker containers (VERIFIED):**
| Container | Status | Port | Function |
|-----------|--------|------|----------|
| os-discord | Up 2hr | 8765 (ws) | Discord bot + cognitive loop |
| os-operator | Up 8hr | 8091 | FastAPI operator API + organism daemon |
| os-webhook | Up 42hr | 8080 | Webhook receiver |
| os-scraper | NOT running | -- | On-demand via nightly cron |

**Systemd services (VERIFIED):**
- caddy.service -- reverse proxy/TLS
- ollama.service -- local LLM (only qwen2.5:0.5b loaded, 397MB)
- tailscaled.service -- Tailscale mesh agent
- ttyd.service -- terminal web access
- umh-mesh.service -- node mesh server (port 8094, NOT responding to curl)

**Cron jobs: 31 active (VERIFIED)**

**Organism daemon (VERIFIED):**
- tick_count: 2,463 (actively incrementing)
- Runs inside os-operator container
- Reconciles environments every ~1-2 seconds
- Publishes events nobody handles: `[EventBus] loop_cycle_business_ops published -- no handlers registered`

**Operator API (VERIFIED -- http://localhost:8091/health returns `{"status":"ok"}`):**
- Serves cockpit HTML at root
- 101+ route definitions across cockpit*.py and operator.py files

**Tailscale mesh (VERIFIED):**
- 2 peers: DESKTOP-LVGUIQ9 (online), localhost x2 (1 online, 1 offline)
- Windows Beast is reachable

---

### 4. DEAD / STALE / SHADOW SYSTEMS

**DEAD:**
- `runtime/` top-level package -- 0 Python files, directory exists but empty. Zero imports from `runtime` in production code. **DEAD**
- 4 SQLite databases at `data/runtime/` -- approvals (0 rows), identities (1 row), memory (0 rows), tasks (0 rows). **DEAD** (approval_counters has 3 rows but nothing reads them)
- `substrate/deployment/` -- empty directory. **DEAD**
- `substrate/distribution/` -- empty directory. **DEAD**
- `substrate/execution/environments/` -- empty directory. **DEAD**
- `substrate/integrations/node_mesh/`, `substrate/integrations/creatoros/`, `substrate/integrations/eos/`, `substrate/integrations/lyfeos/`, `substrate/integrations/notion/` -- all empty. **DEAD**
- `substrate/control_plane/orchestrator/approvals/approved/` and `pending/` -- empty. **DEAD**
- umh-mesh.service (port 8094) -- running but not responding to HTTP. **DEAD or MISCONFIGURED**
- `data/umh/organism/execution_journal.jsonl` -- 0 lines. Recording pathway exists but never writes. **DEAD**

**STALE:**
- `data/codebase_graph.json` (4.5MB) -- last rebuilt 2026-05-26, 412 files modified since. **STALE**
- `data/node_summaries.json` (3.5MB) -- same age as graph. **STALE**
- CLAUDE.md claims "72 legacy files in LEGACY_INSTANCE_LEAKS" -- actual count is 0 (all cleaned). **STALE DOCUMENTATION**
- `data/umh/mesh/metrics.jsonl` -- 1.3M lines, 238MB, single file growing indefinitely with no rotation. **STALE/UNBOUNDED**
- `logs/` -- 20,636 files, 153MB, no evidence of rotation policy. **STALE**

**SHADOW/DUPLICATE:**
- 3 `CEOAgent` classes: `substrate/control_plane/orchestrator/orchestrator.py:73`, `substrate/control_plane/agents/ceo_agent.py:39`, `projections/eos/agents/ceo.py:16`. **SHADOW**
- `EntrepreneurOSGateway = Gateway` alias in gateway.py:1927 -- backward-compat debt. **SHADOW**
- 42 "constitutional engine" files in `substrate/execution/workers/workstation/` -- imported only by report handlers in transports/presence, never executed in production runtime. **SHADOW/PARTIAL**
- `data/repos/entrepreneuros/` -- complete 89-TSX reference snapshot of earlier SaaS frontend. **STALE ARCHIVE**

---

### 5. EXECUTION SPINES

**Canonical execution path (VERIFIED):**
```
Signal arrives --> ConcreteSignalRouter.route() [57 lines]
  --> GovernanceEngine.classify() [risk classification]
  --> GovernanceVerdict gates execution
  --> ConcreteExecutionSpine.execute() [419 lines, single public method]
  --> 8-stage pipeline
```
Located at: `substrate/execution/spine.py`

**Secondary execution path -- Discord cognitive loop (VERIFIED):**
```
Discord message --> signal_factory.py --> Gateway.process()
  --> cognitive_loop.py --> model_router.call_with_fallback()
  --> Response back to Discord
```
Located at: `substrate/control_plane/runtime/cognitive_loop.py`

**Organism autonomous cadence (PARTIAL):**
```
Organism daemon tick (every 5s) --> environment_reconciler
  --> publishes events to EventBus --> NO HANDLERS REGISTERED
```
Events recorded to `data/umh/organism/events.jsonl` (17K+ lines) but execution_journal.jsonl is empty.

**Intelligence routing (VERIFIED):**
```
call_with_fallback() --> cc_sdk (Claude CLI) --> Gemini --> Groq --> Perplexity --> Ollama
  --> deterministic fallback on ALL_DOWN
```
Currently: ALL providers exhausted. Deterministic fallback active.

---

### 6. GOVERNANCE STATUS

**Genuinely enforced (VERIFIED):**
- `ConcreteSignalRouter.route()` calls `GovernanceEngine.classify()` -- confirmed via source inspection
- Execution blocked on governance verdict -- structural enforcement, not optional
- Pre-commit hooks block type divergence and instance leaks -- both pass clean, hook file verified at `.git/hooks/pre-commit`
- `STRUCTURALLY_DENIED_ACTIONS` prevents financial/credential operations unconditionally

**Partially enforced (PARTIAL):**
- `check_dependency_direction.py` exists and passes but is NOT in the pre-commit hook
- `check_projection_leak.py` exists but is NOT in the pre-commit hook
- 10 transports/ -> projections/ imports exist (lazy/deferred) -- technically violations but passing checks

**Not enforced (DEAD):**
- Execution journal recording -- pathway exists but produces 0 output
- Organism work processing -- daemon ticks but `loop_cycle_business_ops` has no handlers
- `approval_counters` table has 3 rows but nothing consumes them

---

### 7. MEMORY STATUS

**Neon PostgreSQL (PARTIAL -- no runtime verification of connectivity):**
- Connection string in `infra/docker/umh.env` (NOT git-tracked, properly gitignored)
- Code references: interactions, outcomes, embeddings (pgvector 384-dim), skills, ventures with RLS
- No verification of actual table state possible without DB access

**Local JSONL persistence (VERIFIED):**
- 174 JSONL files total
- `data/umh/mesh/metrics.jsonl`: 1,307,164 lines (238MB) -- unbounded growth
- `data/umh/organism/events.jsonl`: 17,152 lines (active, growing)
- `logs/pipeline_trace.jsonl`: 43,959 lines
- `data/umh/organism/execution_journal.jsonl`: 0 lines (broken)

**Local SQLite (DEAD):**
- 4 databases, effectively empty (0-1 rows), nothing reads or writes them

**Knowledge system (VERIFIED but STALE):**
- `data/codebase_graph.json`: 4.5MB (last rebuilt 2026-05-26)
- `data/node_summaries.json`: 3.5MB
- `knowledge/palace/`: 19 markdown files
- `knowledge/`: 273 markdown wiki pages total
- `data/codebase_pages/`: 6,292 documentation pages
- `scripts/query_graph.py`: functional

**Embeddings (PARTIAL):**
- `[EmbeddingEngine] Active: fastembed (local)` -- confirmed in Discord bot logs
- Uses fastembed for local embeddings, pgvector for storage

---

### 8. DISTRIBUTED SYSTEM STATUS

**Tailscale mesh (VERIFIED):**
- VPS (this machine): online
- DESKTOP-LVGUIQ9 (Windows Beast): online
- 2 nodes connected out of 3 registered

**umh-mesh.service (DEGRADED):**
- systemd says: running
- HTTP health check on port 8094: no response
- Likely WebSocket-only protocol or misconfigured port binding

**Node daemon for Windows (PARTIAL):**
- Code exists at `nodes/` directory
- Windows Beast is reachable via Tailscale
- No verification of daemon actually running on Beast

**Cross-node execution (STUBBED):**
- `substrate/execution/workers/workstation/` has 42 engine files
- Report handlers in transports/ import them
- No evidence of actual cross-node execution occurring

---

### 9. UI + COCKPIT STATUS

**Cockpit application (PARTIAL):**
- Built with: React 19, electron-vite, dual-target (Electron + web SPA)
- Location: `cockpit/` -- 92 TypeScript/TSX files
- Package: `umh-cockpit v0.1.0`
- Backed by: FastAPI operator API on port 8091 (VERIFIED healthy, serves HTML at root)

**Fly.io deployment (DEGRADED):**
- App: `umh-cockpit`, machine `d8976eec9e1258` in LAX region, state: "started"
- Last updated: 2026-05-30T08:03:37Z
- universalmetaharness.tech: returned HTML from localhost but timed out externally during this audit
- Verdict: Fly machine is running but external DNS/routing may be broken

**Operator API (VERIFIED):**
- 101+ route definitions
- Health endpoint returns 200 with JSON status
- Serves full cockpit SPA at root URL

**saas/ API (PARTIAL):**
- Hono TypeScript API with 12 route files (agents, ventures, workflows, tasks, etc.)
- `saas/package.json` exists
- No evidence it is currently running or deployed

---

### 10. PLATFORM SEPARATION STATUS

**substrate/ independence (VERIFIED):**
- Zero actual imports from transports/ or services/ in production code
- 3 imports from adapters/ (AgentRuntime) -- minor violation
- 134 canonical types registered, all in substrate/ or nodes/
- Pre-commit hooks enforce type coherence and instance context

**Projection separation (PARTIAL):**
- EOS (`projections/eos/`): 5,699 lines across agents, views, workflows, integration
- CreatorOS (`projections/creatoros/`): 1,099 lines, integration package only
- LyfeOS (`projections/lyfeos/`): 1,184 lines, integration package only
- `substrate/integrations/{eos,creatoros,lyfeos,notion}` -- ALL EMPTY directories (dead)

**Boundary violations (VERIFIED):**
- `transports/api/cockpit_entity_routes.py` imports from `projections.eos` (8 imports)
- `transports/api/app.py` imports `projections.eos.integration` (2 imports)
- `EntrepreneurOSGateway` alias persists in gateway.py
- `check_projection_leak.py` is NOT in the pre-commit hook

**Env var migration (VERIFIED):**
- Code uses `UMH_ORG_ID` with `EOS_ORG_ID` fallback pattern
- Instance context gate passes clean (0 violations)

---

### 11. IMPORT + DEPENDENCY GRAPH ISSUES

**Clean (VERIFIED):**
- All 5 core packages import without error: substrate, adapters, transports, services, projections
- Zero circular import issues
- Zero syntax errors in production code
- Type divergence check passes (0 violations)
- Instance leak check passes (0 violations)
- Dependency direction check passes (0 violations -- exemptions exist)

**Known issues (VERIFIED):**
- 3 CEOAgent class definitions (type system violation not caught by checks)
- 26 orphaned modules (nothing imports them)
- 9 shadow enums: SessionStatus, SignalType, GovernanceDecision duplicated across modules (blocked by type divergence check for new code, grandfathered existing)
- 42 workstation engine files imported only by report handlers, never by execution runtime

**Graph staleness (VERIFIED):**
- `data/codebase_graph.json` is 5 days old
- 412 Python files modified since last rebuild
- Graph queries work but return stale results

---

### 12. PACKAGING + DEPLOYMENT STATUS

**Docker Compose (VERIFIED):**
- 4 services defined: os-scraper, os-webhook, os-discord, os-operator
- All use same build context with bind-mounted Python code
- Python 3.11 in containers
- Restart policies: scraper=no, webhook=always, discord=on-failure, operator=unless-stopped

**Fly.io (VERIFIED):**
- Single app: umh-cockpit
- Region: LAX
- Machine state: started (version 36)
- External reachability: DEGRADED

**No CI/CD pipeline (UNKNOWN):**
- No evidence of GitHub Actions, CircleCI, or any CI system
- Deployment appears manual (docker restart, flyctl deploy)

**Python packaging (VERIFIED):**
- `pyproject.toml` with hatchling build system
- 143 `__init__.py` files (Python packages)
- 144 Python scripts + 30 shell scripts

**TypeScript packaging (PARTIAL):**
- cockpit: electron-vite, buildable for Electron + web
- saas: Hono API, drizzle ORM, package.json present
- transports/api/http: Hono API, package.json present

---

### 13. CRITICAL CONTRADICTIONS

| # | Documentation says | Reality | Severity |
|---|---|---|---|
| 1 | "72 legacy files in LEGACY_INSTANCE_LEAKS" (CLAUDE.md) | 0 legacy leaks exist; all cleaned | LOW (stale docs) |
| 2 | "4 pre-commit gates" (CLAUDE.md) | Only 2 gates in actual .git/hooks/pre-commit (type_divergence + instance_leak). dependency_direction and projection_leak are NOT wired. | HIGH |
| 3 | "execution_journal records traces" (implied by architecture) | execution_journal.jsonl has 0 lines | HIGH (broken recording) |
| 4 | "Organism autonomous cadence" (Phase 10.0) | EventBus publishes `loop_cycle_business_ops` with NO HANDLERS REGISTERED | HIGH (no-op cadence) |
| 5 | "umh-mesh.service" (running per systemd) | Port 8094 does not respond to HTTP | MEDIUM |
| 6 | "cockpit reachable at universalmetaharness.tech" | Timed out externally during audit (Fly machine says "started") | MEDIUM |
| 7 | "No Python file over 3,000 lines" (quality standard) | No violations found -- standard is met | OK |
| 8 | "Graph-first retrieval hierarchy" (CLAUDE.md) | Graph is 5 days stale (412 files modified since rebuild) | MEDIUM |
| 9 | "10-provider fallback chain" (model_router) | ALL providers exhausted -- system is brain-dead for LLM tasks | CRITICAL (operational) |
| 10 | "substrate/ never imports from transports/" | True for actual import statements; 3 adapter imports exist (minor) | LOW |

---

### 14. WHAT IS PRODUCTION-REAL

These components are confirmed running, processing data, and producing observable output:

1. **Discord bot** (`services/discord_bot.py` in os-discord container) -- VERIFIED running, processes signals, but LLM-degraded
2. **Operator API** (FastAPI on port 8091 in os-operator container) -- VERIFIED healthy, serves cockpit HTML + JSON endpoints
3. **Organism daemon** (tick 2,463, 5s interval) -- VERIFIED ticking, writing events.jsonl, reconciling environments
4. **Cron system** (31 jobs) -- VERIFIED scheduled
5. **Pre-commit governance** (type coherence + instance leak) -- VERIFIED enforced
6. **Signal routing + governance gating** (ConcreteSignalRouter + GovernanceEngine) -- VERIFIED in code path
7. **Fastembed local embeddings** -- VERIFIED active in Discord bot logs
8. **Tailscale mesh** (VPS + Beast connected) -- VERIFIED
9. **Webhook receiver** (os-webhook on 8080) -- VERIFIED running 42 hours
10. **Cockpit Fly.io machine** -- VERIFIED started (reachability intermittent)

---

### 15. WHAT IS PARTIAL

1. **Organism cadence** -- daemon ticks, events recorded, but no handlers process business_ops. execution_journal empty. **PARTIAL**
2. **Workstation engines** (42 files) -- code exists, report handlers import them, no runtime execution proof. **PARTIAL**
3. **Node mesh** -- systemd service running, port unresponsive, Beast reachable via Tailscale but no proof of daemon on Beast. **PARTIAL**
4. **CreatorOS/LyfeOS projections** -- integration packages exist (1K+ lines each), no runtime activation. **PARTIAL**
5. **saas/ TypeScript API** -- route files exist, schema defined, not confirmed running. **PARTIAL**
6. **Cockpit external access** -- Fly machine started, HTML served locally, external timeout. **PARTIAL**
7. **Neon PostgreSQL** -- connection configured, code references tables, no runtime verification. **PARTIAL**
8. **Execution spine 8-stage pipeline** -- class exists (419 lines), governance calls it, but execution_journal records nothing. **PARTIAL**
9. **Knowledge retrieval system** -- scripts functional but graph 5 days stale. **PARTIAL**
10. **Intelligence routing** -- code is sophisticated (10 providers, circuit breaker, quality escalation) but ALL providers currently exhausted. **PARTIAL**

---

### 16. WHAT IS THE TRUE CANONICAL CORE

The smallest set of files that constitute the real, running, production UMH:

**Brain (intelligence + routing):**
- `adapters/models/model_router.py` (1,442 lines) -- single intelligence entry point
- `substrate/control_plane/runtime/gateway.py` (1,927 lines) -- Gateway class
- `substrate/control_plane/runtime/cognitive_loop.py` (1,539 lines) -- thinking loop
- `substrate/types.py` -- 87 canonical types

**Governance:**
- `substrate/control_plane/governance.py` -- risk classification
- `substrate/control_plane/router/__init__.py` -- signal lifecycle with governance gating
- `substrate/execution/spine.py` (419 lines) -- execution pipeline

**Production entrypoints:**
- `services/discord_bot.py` (1,974 lines) -- Discord bot
- `services/discord_bot_commands.py` (2,740 lines) -- command handlers
- `services/discord_message_handlers.py` -- message processing
- `transports/api/cockpit.py` (2,304 lines) -- operator API routes
- `services/operator_api.py` -- API entrypoint

**Organism (alive but incomplete):**
- `substrate/organism/daemon.py` (or equivalent tick driver)
- `substrate/organism/environment_reconciler.py` -- actually executing
- `data/umh/organism/events.jsonl` -- growing log

**Infrastructure:**
- `docker-compose.yml` -- service definitions
- `infra/docker/umh.env` -- secrets (gitignored)
- `.git/hooks/pre-commit` -- governance gates

**Total canonical core: approximately 25-30 files out of 1,186 Python files (2.5%).**

The remaining 97.5% is either support infrastructure (scripts, knowledge, tests), aspirational architecture (workstation engines, projections, mesh), or generated data.

---

### 17. RECOMMENDED NEXT PHASE

Based solely on verified findings:

**P0 -- Restore LLM Intelligence (CRITICAL, same-day):**
- Gemini: upgrade from free tier or add billing (20 req/day limit is unusable)
- Groq: wait for TPD reset or upgrade tier
- The system is functionally lobotomized without LLM providers

**P1 -- Fix Broken Recording (HIGH, 1 day):**
- `execution_journal.jsonl` is 0 lines -- the spine executes but never records
- Without this, no evidence of what the system actually does
- Wire execution trace recording to actually persist

**P2 -- Wire Missing Pre-commit Gates (HIGH, 1 hour):**
- Add `check_dependency_direction.py` and `check_projection_leak.py` to `.git/hooks/pre-commit`
- CLAUDE.md claims 4 gates; only 2 are real

**P3 -- Organism Cadence Completion (MEDIUM, 2-3 days):**
- `loop_cycle_business_ops` publishes to EventBus with no handlers
- Register handlers or remove the dead publish
- This is the Phase 10.0 goal -- "template library + candidate supply" -- but the bus has no subscribers

**P4 -- Data Hygiene (MEDIUM, 1 day):**
- `data/umh/mesh/metrics.jsonl`: 238MB single file with no rotation -- will fill disk
- `logs/`: 20K+ files, 153MB, no rotation
- Disk is at 80% (21GB free) -- this will become critical

**P5 -- Knowledge System Rebuild (LOW, 30 min):**
- Graph is 5 days stale (412 files changed)
- Run `scripts/update-graph`
- The entire retrieval hierarchy is compromised when the graph is stale

**P6 -- Resolve Cockpit External Access (LOW, investigation):**
- Fly machine is "started" but external requests timeout
- Could be DNS, Fly networking, or certificate issue
- Local access works (port 8091 serves cockpit HTML)