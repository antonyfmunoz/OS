# Exhaustive Codebase Audit — /opt/OS
**Date:** 2026-05-25
**Scope:** 100% of /opt/OS — every file, every directory, every language
**Method:** 19 parallel audit agents (8 structural + 6 Python behavioral + 5 non-Python)
**Metrics:** 12,930 files | 232K lines Python | 41K lines TypeScript | 65K lines Markdown | 545 MB on disk

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [What Is Actually Running](#2-what-is-actually-running)
3. [The Three Execution Paths](#3-the-three-execution-paths)
4. [Intelligence Routing](#4-intelligence-routing)
5. [Governance Architecture](#5-governance-architecture)
6. [Memory Architecture](#6-memory-architecture)
7. [SaaS Layer (TypeScript)](#7-saas-layer-typescript)
8. [Agent Definitions](#8-agent-definitions)
9. [Skills / Tool Mastery Engine](#9-skills--tool-mastery-engine)
10. [Knowledge / Documentation](#10-knowledge--documentation)
11. [Data / Runtime State](#11-data--runtime-state)
12. [Infrastructure / Deployment](#12-infrastructure--deployment)
13. [Dependency Direction Violations](#13-dependency-direction-violations)
14. [Dead Code Inventory](#14-dead-code-inventory)
15. [Critical Bugs](#15-critical-bugs)
16. [Documentation-Reality Gaps](#16-documentation-reality-gaps)
17. [Security Findings](#17-security-findings)
18. [Disk Pressure](#18-disk-pressure)
19. [Prioritized Remediation](#19-prioritized-remediation)

---

## 1. Executive Summary

UMH (Universal Mastery Hierarchy) is a 232K-line Python + 41K-line TypeScript AI intelligence substrate. Its only production consumer is a Discord bot named DEX that routes messages through an 11-provider LLM fallback chain. The codebase completed a 9-phase "Coherence Convergence" refactor on 2026-05-25 that reorganized everything into 4 canonical packages (substrate/, adapters/, transports/, projections/). The convergence moved code into its canonical homes but did not delete the ~61K lines of dormant code that predates it, nor update the ~750 documentation files that still reference pre-convergence paths.

**What works:** Discord bot (DEX) processes messages → Gateway → CognitiveLoop → AgentRuntime → LLM → response. Morning briefs. Cockpit API (58 endpoints, no auth). Canonical memory store (103 memories). SaaS schema deployed to Neon (21 tables with RLS).

**What doesn't:** SaaS API server (not running). Cockpit frontend (no source on VPS). 3 of 4 CC subagents (need Anthropic credits). Autonomous loops (defined but not running). Node mesh daemon (stopped since May 7). 6 of 7 palace rooms (empty). Knowledge graph (2.5 days stale, scans wrong directories). 43 of 96 tool skills (past staleness threshold).

**The single biggest risk:** The system has three parallel execution paths that are not synchronized. A signal entering Path 1 (Gateway→CognitiveLoop) vs Path 2 (Substrate.execute()→ExecutionSpine) vs Path 3 (ExecutionPipeline→WorkPackets) will get different governance checks, different memory writes, and different trace recording.

---

## 2. What Is Actually Running

### Production Services (Docker)

| Container | Image | Status | Port | Function |
|-----------|-------|--------|------|----------|
| os-discord | Dockerfile | Up 4 hours | — | DEX Discord bot (services/discord_bot.py) |
| os-operator | Dockerfile | Up 2 hours | 8091 | Cockpit API (transports/api/cockpit.py) |
| os-webhook | Dockerfile | Up 4 days | 8092 | Calendly/Higgsfield webhooks |

### What Each Service Does

**os-discord (DEX):** The production system. Receives Discord messages → `EntrepreneurOSGateway.handle()` → classifies intent → routes to `CognitiveLoop.run()` → `AgentRuntime.run()` → LLM call via `model_router.call_with_fallback()` → response. Handles: agent tasks, events, status queries, morning briefs. Smart model routing (CEO tasks get Opus, fast responses get Haiku). Person recognition for known contacts.

**os-operator (Cockpit API):** 58 REST endpoints at `/api/umh/*` + WebSocket at `/api/umh/ws` (2-second pulse). Exposes: system status, agent registry, memory queries, signal submission, governance verdicts, execution traces, loop management, world model, approvals. **No authentication** — anyone with the URL has full access.

**os-webhook:** Calendly event handler (meeting → memory) + Higgsfield video generation webhook.

### Cron Jobs

| Schedule | Script | Function |
|----------|--------|----------|
| Every 5 min | scripts/cron_morning_brief.py | Morning brief (runs only 6-7 AM PT) |
| Hourly | scripts/cron_research.py | Research loop (currently no-ops) |
| Daily 3 AM | scripts/cron_health.py | Health check |

---

## 3. The Three Execution Paths

This is the most important architectural finding. The codebase has three complete execution pipelines, each with their own governance, tracing, and memory handling. Only Path 1 is used in production.

### Path 1: Gateway → CognitiveLoop → AgentRuntime (PRODUCTION)

```
Discord message
  → EntrepreneurOSGateway.handle()
    → validates, checks approval queue (filesystem-based)
    → routes by task_type:
        agent_task → CognitiveLoop.run()
        event → EventBus
        status → Neon query
        brief → morning_cycle()
    → CognitiveLoop.run() (8 steps):
        1. Multimodal resolution
        2. Context assembly (25 layers, each try/excepted)
        3. Authority check
        4. Execute via AgentRuntime + deterministic fallback
        5. Quality verify (max 3 iterations)
        6. Reflect + learn
    → AgentRuntime.run()
        → model_router.call_with_fallback()
        → returns response
```

**Governance:** GovernanceEngine (regex-based risk classification: LOW/MEDIUM/HIGH/CRITICAL)
**Memory:** ConversationMemory (in-memory dict) + AgentMemory (Neon)
**Tracing:** ExecutionTracer (Neon writes)

### Path 2: Substrate.execute() → ConcreteSignalRouter → ExecutionSpine (V2)

```
SignalEnvelope
  → Substrate.execute()
    → ConcreteSignalRouter.route()
      → ConcreteExecutionSpine.execute() (8 stages):
          0. Governance gate (risk classification)
          0a. Simulation dry-run (HIGH/CRITICAL)
          0b. Deliberation council (HIGH/CRITICAL)
          1. Interpret signal
          2. Recall from world model
          3. Lookup (authority/capability)
          4. Compose response
          5. Route + execute (deterministic-first, then AI)
          6. Trace recording
          7. Knowledge gap detection
          8. Memory writes (Neon mandatory)
          9. Feedback scoring
```

**Governance:** Same GovernanceEngine + AuthorityEngine (DB-backed) + ExecutionAuthorityEngine (13-dimension)
**Memory:** Canonical Memory Store + World Model
**Tracing:** TraceRecord (Neon + JSONL)

### Path 3: ExecutionPipeline → WorkPacketExecutor (GOVERNED WORK)

```
WorkPacket
  → ExecutionPipeline.execute()
    → WorkPacketExecutor
      → adapter execution
      → proof generation
      → outcome classification
      → memory promotion
      → completeness check
```

**Governance:** PolicyEngine (risk→verdict) + QualityTransformationGate (4-value lens)
**Memory:** Promotion receipts + reconciliation
**Tracing:** Proof files (JSONL)

### The Problem

These three paths have:
- **Different governance engines** with unsynchronized regex patterns
- **Different memory write targets** (ConversationMemory vs CanonicalMemoryStore vs PromotionReceipts)
- **Different tracing formats** (ExecutionTracer vs TraceRecord vs proof files)
- **No unified entry point** — Gateway._route_agent_task creates a SignalEnvelope and calls Substrate.execute() (Path 2), but the actual execution still goes through CognitiveLoop (Path 1)

The convergence added a bridge in Gateway (Stage 0c for DeliberationCouncil, Stage 8b for mandatory memory writes), but the paths are not truly unified.

---

## 4. Intelligence Routing

**File:** `adapters/models/model_router.py` (1,496 lines)

The intelligence routing backbone. `call_with_fallback()` is the single entry point for all LLM calls.

### Provider Chain (in fallback order)

| Priority | Provider | Model | Cost | Status |
|----------|----------|-------|------|--------|
| 0 | CC SDK (Claude CLI) | Opus 4.6 | $0 (Max subscription) | ACTIVE — primary |
| 1 | Gemini | gemini-2.5-flash | Pay-per-use | ACTIVE — fallback |
| 2 | Groq | llama-3.3-70b-versatile | Free tier | ACTIVE — fallback |
| 3 | Anthropic Haiku | claude-haiku-4-5 | Pay-per-use | BLOCKED (invalid key) |
| 4 | Anthropic Sonnet | claude-sonnet-4-5 | Pay-per-use | BLOCKED (invalid key) |
| 5 | Anthropic Opus | claude-opus-4 | Pay-per-use | BLOCKED (invalid key) |
| 6 | Perplexity | sonar-pro | Pay-per-use | AVAILABLE |
| 7 | Ollama | gemma3:4b | Free (local) | AVAILABLE (needs 3.3 GiB RAM) |
| 8 | Codex | — | — | NOT in chain (reconnect issues) |
| 9 | Hermes | — | — | NOT in chain |
| 10 | OpenCode | — | — | NOT in chain |

### Routing Logic

- **CEO/strategic tasks** (`agent_type='ceo'` or `force_opus=True`): Skip economy mode, use best available
- **Fast tasks** (TaskType.FAST_RESPONSE): Route to fast chain (Groq → Gemini → Haiku)
- **Heavy tasks**: Route to heavy chain (CC SDK → Gemini → Anthropic → Perplexity → Ollama)
- **Vision tasks**: Filter to vision-capable providers only
- **Economy mode** (`pre_revenue` stage): Forces Haiku unless overridden

### CC SDK Details

`adapters/models/cc_sdk.py` (465 lines):
- Detects nested Claude Code sessions to prevent recursion
- Injects OAuth token from ancestor process via `/proc` walk
- Error leak detection: catches auth/quota errors that stream as text
- Orphan process cleanup for subprocess management
- 120s timeout (configurable via CC_SDK_TIMEOUT_SECONDS)

### Circuit Breaker

Each provider has a circuit breaker:
- Opens after N consecutive failures
- Half-open test after cooldown period
- Quality-based escalation: if quality score < 0.40, escalates to next provider

---

## 5. Governance Architecture

Five layers of governance exist, not all active in production:

| Layer | File | Used In Production? | What It Does |
|-------|------|-------------------|--------------|
| GovernanceEngine | substrate/control_plane/governance.py | YES | Regex-based risk classification (LOW/MEDIUM/HIGH/CRITICAL) |
| AuthorityEngine | substrate/governance/authority.py | NO (Path 2 only) | DB-backed authority validation |
| ExecutionAuthorityEngine | substrate/governance/execution_authority.py | NO (Path 2 only) | 13-dimension authority scoring |
| PolicyEngine | substrate/governance/policy.py | NO (Path 3 only) | Risk→verdict mapping |
| QualityTransformationGate | substrate/governance/quality.py | NO (Path 3 only) | 4-value lens (Reality/Intelligence/Personalization/Execution) |

**Production governance is regex-only.** The GovernanceEngine classifies risk by pattern matching on keywords. The deeper governance layers (authority validation, policy evaluation, quality gates) exist in code but are only wired into the non-production execution paths.

---

## 6. Memory Architecture

Five memory systems exist:

| System | Storage | Used In Production? | Capacity |
|--------|---------|-------------------|----------|
| ConversationMemory | In-memory dict | YES | Volatile (lost on restart) |
| AgentMemory | Neon Postgres | YES | Persistent per-agent |
| Canonical Memory Store | JSONL + Neon | PARTIALLY | 103 memories indexed |
| World Model | JSONL (canonical + instance) | NO (Path 2 only) | Observations, never queried live |
| Knowledge Graph | data/codebase_graph.json | STALE | 332 files, 2.5 days old, wrong scan dirs |

**The memory problem:** Production (Path 1) uses ConversationMemory, which is a Python dict that dies on container restart. Canonical Memory Store has 103 memories but is not queried during production message handling. The World Model accumulates observations but has zero live consumers. The Knowledge Graph scans `["runtime", "services", "scripts", "core"]` — missing all 4 canonical packages.

---

## 7. SaaS Layer (TypeScript)

**Directory:** `saas/` (31 files)
**Stack:** Hono + Drizzle ORM + Neon serverless + Zod
**Status:** Schema deployed to Neon, API server NOT running

### Schema (21 tables with RLS)

Core tables: users, portfolios, organizations, org_members, ventures, agents, skills, skill_versions, events, workflows, interactions, outcomes, umh_outcomes, human_profiles, approvals, embeddings, user_agent_sessions

CRM tables (text org_id, not UUID): clients, transactions, fulfillment_events, offers

### Issues Found

1. **Schema drift:** 7 tables exist via SQL migrations but are NOT in schema.ts (goals, goal_outcomes, model_preferences, higgsfield_jobs, cross_product_permissions, user_intelligence_profiles, product_connections). Invisible to ORM.

2. **Embedding dimension mismatch:** Migration 0000 creates vector(1536), schema.ts specifies 384 with BAAI/bge-small-en-v1.5.

3. **Migration gap:** Migration 0004 is missing from the sequence.

4. **Type system split:** CRM tables use text org_id/venture_id (Python .env string IDs), all others use UUID. Two tenant isolation patterns in one schema.

5. **Python bridge:** `saas/bridge/agent_bridge.py` imports Gateway and Orchestrator from substrate, supports 3 actions (agent.run, agent.team, orchestrator.brief). Functional but API server not started.

6. **Auth:** Header-based (`x-org-id`). Validates org exists but no token/session auth.

---

## 8. Agent Definitions

### Soul Documents (agents/) — 11 files

All 10 main agents follow identical 5-section structure (Identity, Judgment, Role Boundary, Communication Standard, Hard Stops). All under 300 lines. Authority tiers are coherent:

| Tier | Agents |
|------|--------|
| COMMIT | CEO, Finance, Legal |
| EXECUTE | Customer Success, Engineering, HR, Marketing, Operations, Sales |
| DRAFT | Product |
| Supervised | Computer-Use (40 lines, deviates from standard structure) |

### CC Native Subagents (.claude/agents/) — 4 files

| Agent | Model | Status |
|-------|-------|--------|
| eos-code-reviewer | opus | FUNCTIONAL (Max subscription) |
| eos-researcher | sonnet | BLOCKED (needs Anthropic credits) |
| eos-simplifier | sonnet | BLOCKED (needs Anthropic credits) |
| eos-verifier | haiku | BLOCKED (needs Anthropic credits) |

### CC Commands — 21, CC Skills — 11, CC Rules — 3, CC Hooks — 1

### Third-Party Skills (.agents/skills/) — 2

- `humanizer` (blader/humanizer) — AI writing pattern removal, 24 categories
- `last30days` (charlesdove977/goviralbitch) — multi-platform research engine

---

## 9. Skills / Tool Mastery Engine

**Directory:** `skills/` (5,492 files, 467 excluding node_modules)
**Tool mastery packs:** 96 tools with SKILL.md + references/

### Coverage by Category

| Category | Count | Examples |
|----------|-------|---------|
| AI/LLM | 11 | anthropic_api, claude_code, gemini, groq, ollama, openai |
| Development | 18+ | docker, git, react, typescript, vite, drizzle_orm |
| Social/Marketing | 14 | discord, instagram, x_twitter, youtube, tiktok |
| Business/SaaS | 13+ | stripe, shopify, notion, quickbooks, calendly |
| Content/Creative | 7 | davinci_resolve, fl_studio, photoshop, obs |
| Data/Infra | 5 | aws, neon_postgres, posthog, playwright |
| Knowledge | 4+ | obsidian, notebooklm, json_canvas |

### Quality Metrics

| Metric | Result |
|--------|--------|
| Gotchas section present | 96/96 (100%) |
| Verification steps present | 46/96 (48%) |
| Past staleness threshold | 43/96 (45%) |
| "EOS" naming (should be "UMH") | 96/96 (100%) |

### Critical Issues

1. **45% of tools are stale.** All 11 "fast" category tools (google_gemini, claude_code, react, etc.) and the "ultra" tool (groq) are past their refresh thresholds. The automated staleness sweep defined in the TME engine skill is not running.

2. **Content/content case collision.** Both `Content/` and `content/` directories exist with different skills. Will fail on case-insensitive filesystems.

3. **4 orphaned `.creating` lock files** in nodejs, systemd, tailscale, tmux — interrupted skill creation.

4. **saas-dev-skill has 106 MB node_modules on VPS** — violates Node Role Discipline.

5. **claude_code is the deepest skill** (14 reference files, "Critical" tier) but 27 days past its 14-day freshness threshold.

### Domain Skills (non-tool)

| Category | Files |
|----------|-------|
| Sales | 20 |
| Meta | 15 |
| Ops | 13 |
| Research | 6 |
| Marketing | 4 |
| Content | 5 (split across 2 dirs) |
| CustomerSuccess | 2 |
| Outreach | 2 |
| Developer | 1 |

---

## 10. Knowledge / Documentation

### knowledge/ (236 .md files)

| Subdirectory | Files | Status |
|-------------|-------|--------|
| concepts/ | 111 | ~60% generic LLM planning filler |
| synthesis/ | 33 | ~70% generic |
| entities/ | 23 | Mixed quality |
| decisions/ | 2 | Valid |
| skills/marketing/ | 52 | Remotion project |
| palace/ | 7 rooms | 6 of 7 rooms EMPTY |
| domains/, sources/, agents/, workflows/ | 0-1 | Empty/placeholder |

**Critical Issues:**

1. **37 broken wikilinks in index.md.** Pages were promoted to `10_Wiki/` instead of `knowledge/`. Every link in the index points to a file that doesn't exist in its expected location.

2. **6 of 7 palace rooms are empty shells.** Only `transports.md` has actual loci. The palace was regenerated on 2026-05-23 but didn't populate.

3. **Zero wiki pages reference `substrate/` paths.** Every file reference points to deleted paths (`eos_ai/`, pre-convergence `runtime/`, `services/umh/`).

4. **EOS naming throughout.** Palace is titled "EOS Memory Palace." Post-convergence, it should be UMH.

5. **Last wiki mutation was 2026-05-21.** No updates since convergence completed.

### 10_Wiki/ (37 files) — ORPHANED

All 37 files are output from a batch wiki promotion on 2026-05-13 that wrote to the wrong directory. These are the missing targets of the 37 broken wikilinks in knowledge/index.md. No duplicates with knowledge/ — clean merge possible.

### docs/ (475 files)

| Subdirectory | Files | Notes |
|-------------|-------|-------|
| audits/ | 153 | Historical build phase reports (phase 0-77) |
| operations/ | 182 | Operational doctrine, heavily versioned, mostly stale |
| system/ | 92 | Architecture plans, contracts, specs |
| strategy/ | 11 | Empire architecture, doctrine |
| sessions/ | 6 | Design docs |
| superpowers/ | 11 | GSD plans and specs |
| other | 20 | migrations, mvp, canonical, setup, changes, design-system |

**107 files reference `eos_ai/`** (deleted directory). Only 1 file modified since convergence (May 23).

### Key Current Documents

- `docs/corporate-structure.md` — current entity map
- `docs/brand-identity.md` — current brand reference
- `docs/canonical/umh_synthesis.md` — 15K-word authoritative UMH synthesis
- `docs/system/domain_bridge_contract_v1.md` — current architectural contract
- `docs/system/decomposition_extraction_contract_v1.md` — current extraction contract

---

## 11. Data / Runtime State

**Directory:** `data/` (~8,100 files, 400 MB)

### Size Breakdown

| Directory | Size | % of Total |
|-----------|------|------------|
| data/umh/ | 273 MB | 68% |
| data/logs/ | 58 MB | 14% |
| data/runtime/ | 50 MB | 12% |
| data/semantic_space/ | 41 MB | 10% |
| Other | 11 MB | 3% |

### Space Bombs

| File | Size | Lines | Issue |
|------|------|-------|-------|
| umh/mesh/metrics.jsonl | 205 MB | 1,127,222 | No rotation — 51% of all data/ |
| umh/traces/traces.jsonl | 47 MB | 55,906 | Unbounded accumulation |
| umh/memory_candidates/candidates.jsonl | 22 MB | 27,964 | Promotion pipeline not running |
| logs/pipeline_trace.jsonl | 11 MB | — | No rotation |
| runtime/substrate_continuity/resume_packets.jsonl | 10 MB | — | 212 duplicate failure entries from May 10-11 |

### Codebase Graph

- **332 files indexed, 341 classes, 2,559 functions, 7,938 edges**
- Generated 2026-05-23 01:31 UTC — **2.5 days stale**
- `SCAN_DIRS = ["runtime", "services", "scripts", "core"]` — **missing all 4 canonical packages** (substrate/, adapters/, transports/, projections/)
- The entire knowledge system (palace, graph queries, node summaries) is built on this incomplete graph

### Canonical Memory Store

- 103 memories indexed (5 canonical, 34 instance + behavioral feedback)
- Sources: Google Drive docs, local file ingestion, Claude memory sync
- Last updated: 2026-05-24 22:47 UTC

### Config

- `github_repos.json`: 4 Trinity repos monitored
- `loop_definitions.jsonl`: 3 loops defined (business_ops/300s, self_build/1800s, research/3600s) — none running

---

## 12. Infrastructure / Deployment

### Docker

- **Dockerfile:** Python 3.11-slim, bind-mounts /opt/OS, patches py-cord voice reconnection
- **docker-compose.yml:** 4 services defined (discord, operator, webhook, monitor) — `env_file: runtime/.env` which DOES NOT EXIST
- **Running containers:** 3 (os-discord, os-operator, os-webhook) — started individually via `docker restart`, NOT via compose (because compose is broken)

### Computer-Use Infrastructure

- `docker/computer-use/` — headless GUI containers (Xvfb + noVNC + Chromium)
- `docker-compose.beast.yml` — 3 agent containers at 2GB each, designed for Beast machine
- Status: DORMANT (not built, not running)

### Environment Files

- `infra/docker/services.env` — ALL production secrets (Discord, Telegram, Apify, Anthropic, Gemini, Groq, Perplexity, OpenAI, Instagram, Calendly, Stitch, Notion)
- `infra/docker/umh.env` — extended config + secrets + Notion DB IDs
- `infra/docker/.env.sessions` — CC SDK OAuth token
- All properly gitignored

### Node Roles

| Node | Role | Status |
|------|------|--------|
| VPS (100.77.233.50) | Coordination brain | ACTIVE — runs 3 Docker services |
| Windows Beast (100.74.199.102) | GPU workhorse | DORMANT — daemon stopped May 7 |

---

## 13. Dependency Direction Violations

**Architecture contract:** `projections → transports → adapters → substrate` (substrate is innermost, never reaches outward)

### Violations Found (108 total)

The Phase 2 behavioral audit identified 108 instances where `substrate/` imports from outer layers:

- substrate/ → transports/ (direct imports of Discord handlers)
- substrate/ → services/ (imports of Discord bot functions)
- substrate/ → projections/ (imports of EOS-specific agents)

These are concentrated in:
- `substrate/control_plane/orchestrator/orchestrator.py` (imports morning brief handlers from transports)
- `substrate/execution/bridge/` (imports Discord-specific session management)
- `substrate/interface/` (channel surfaces that should be in transports/)

### socket/ Pattern

The correct pattern exists: `substrate/sockets/` defines abstract ports (notification, channel, signal, sensing, capability, outcome, view). Concrete implementations should register at startup. Some ports have implementations (NotificationPort), others are abstract-only.

---

## 14. Dead Code Inventory

### Confirmed Dead (61K+ lines)

| Location | Lines | Description |
|----------|-------|-------------|
| substrate/execution/workers/workstation/ | 22,400 | Constitutional proof engines, 42 files, zero imports |
| runtime/ (legacy compatibility) | ~15,000 | Pre-convergence runtime, partially imported |
| substrate/execution/pipeline.py + related | ~3,000 | Path 3 execution, never called in production |
| substrate/governance/authority.py + related | ~2,500 | Deep governance layers, not wired to production |
| substrate/understanding/ (portions) | ~5,000 | Perception/interpretation modules, not called |
| substrate/composition/ | ~3,000 | Mastery registries, not used |
| projections/eos/ (portions) | ~2,000 | EOS agents defined but never instantiated |
| Various | ~8,000+ | Scattered across packages |

### Largest Individual Dormant Files

| File | Lines | Status |
|------|-------|--------|
| substrate/control_plane/orchestrator/orchestrator.py | 1,905 | Partially active (morning cycle), mostly dormant |
| services/discord_bot.py | 1,930 | PRODUCTION but contains ~800 lines of unused handlers |
| substrate/execution/workers/workstation/types.py | 1,200+ | Entirely dormant |
| runtime/cognitive_loop.py | ~800 | Legacy, compatibility import only |

---

## 15. Critical Bugs

### P0 — System Broken

1. **`docker-compose.yml` references `runtime/.env` which does not exist.** All `docker compose` operations fail. Services run only because they were started individually via `docker restart`.

2. **`scripts/codebase_graph.py` SCAN_DIRS scans wrong directories.** Set to `["runtime", "services", "scripts", "core"]` — misses substrate/, adapters/, transports/, projections/. The entire knowledge graph, memory palace, and node summaries are built on an incomplete scan.

3. **CLAUDE.md session resume protocol references dead modules.** `runtime.session_state.SessionState` and `runtime.context.load_context_from_env` do not exist. Every new CC session following bootstrap protocol hits ModuleNotFoundError.

### P1 — Functionality Broken

4. **43 test failures from stale imports.** 23 tests mock `substrate.execution.runtime.model_router` → should be `adapters.models.model_router`. 20 tests import `runtime_execution_result_v1` which doesn't exist.

5. **Resume packet has 212 duplicate failure entries.** All from test runs on 2026-05-10/11. No deduplication or pruning. The resume packet is 290 KB of mostly duplicate data.

6. **Canonical memory store index mismatch.** index.json says 39 memories but JSONL has 103 entries.

### P2 — Degraded

7. **3 of 4 CC subagents non-functional.** eos-researcher (sonnet), eos-simplifier (sonnet), eos-verifier (haiku) need Anthropic API credits.

8. **`alwaysThinkingEnabled` discrepancy.** CLAUDE.md says "always on" but settings.json says `false`.

9. **37 broken wikilinks in knowledge/index.md.** Pages in 10_Wiki/, not knowledge/.

10. **PROTOCOLS.md, AGENTS.md, ARCHITECTURE.md all reference `eos_ai/`** — a directory deleted during convergence.

---

## 16. Documentation-Reality Gaps

| Document | Claims | Reality |
|----------|--------|---------|
| CLAUDE.md "Key files" | Lists 16 canonical files | 14 exist, 2 at wrong paths |
| CLAUDE.md "Session resume" | `runtime.session_state.SessionState` | Module does not exist |
| CLAUDE.md "Extended thinking" | "always on" | settings.json: false |
| PROTOCOLS.md | References eos_ai/* paths | eos_ai/ deleted in convergence |
| AGENTS.md | "LLM: qwen2.5:3b" | Actual: cc_sdk → Gemini → Groq → Ollama |
| ARCHITECTURE.md | 1 execution path | 3 parallel paths exist |
| ARCHITECTURE.md | Section 11 → 13 → 12 | Numbering broken |
| cloud.md | Knowledge hierarchy | Palace rooms empty, graph stale |
| docker-compose.yml | env_file: runtime/.env | File does not exist |
| Tool skills | "EOS" naming | System is "UMH", EOS is a projection |
| Knowledge palace | "EOS Memory Palace" | Should be "UMH Memory Palace" |
| Palace wing | References eos_ai/ directory | Directory deleted |

---

## 17. Security Findings

### Critical

1. **Cockpit API has NO authentication.** 58 endpoints including signal submission, approval management, and system configuration are exposed on port 8091 with zero auth. The operator API has a default key "dev-key-change-me".

2. **infra/docker/services.env and umh.env contain ALL production secrets in plaintext.** Both files exist (not consolidated). Properly gitignored but no encryption at rest.

### Medium

3. **RLS bypass possible.** The Neon connection uses `neondb_owner` role which has BYPASSRLS. The SaaS API correctly uses `eos_app` role, but the Python substrate connects as owner.

4. **Discord bot token in services.env** — single point of compromise for the production system.

5. **Instagram credentials stored in plaintext** in services.env.

### Low

6. **Chromium `--no-sandbox` flag** in computer-use Dockerfile. Standard for containers but worth noting.

7. **SaaS API auth is header-only** (`x-org-id`). No session tokens, no JWT.

---

## 18. Disk Pressure

**VPS disk at 79% capacity** (from prior audit). Key consumers in /opt/OS:

| Item | Size | Action |
|------|------|--------|
| data/umh/mesh/metrics.jsonl | 205 MB | ROTATE immediately |
| saas-dev-skill/node_modules/ | 106 MB | Remove from VPS |
| data/umh/traces/traces.jsonl | 47 MB | ROTATE |
| data/semantic_space/ | 41 MB | Evaluate necessity |
| data/umh/memory_candidates/ | 22 MB | Process or archive |
| data/logs/ (all) | 58 MB | ROTATE |
| data/runtime/test artifacts | ~50 MB (944 files) | DELETE |
| .git/ | est. 200+ MB | git gc --prune=now |

**Estimated recoverable:** 400+ MB from rotation, cleanup, and gc.

---

## 19. Prioritized Remediation

### P0 — Do Now (System Broken)

| # | Issue | Fix | Impact |
|---|-------|-----|--------|
| 1 | docker-compose.yml references missing runtime/.env | Create symlink or update env_file path to infra/docker/services.env | Unblocks all compose operations |
| 2 | codebase_graph.py SCAN_DIRS wrong | Change to ["substrate", "adapters", "transports", "projections", "services", "scripts"] | Fixes entire knowledge system |
| 3 | CLAUDE.md session resume references dead modules | Update to valid import paths or remove | Every new session breaks |
| 4 | Cockpit API no auth | Add API key middleware at minimum | Production security |

### P1 — Do This Week (Functionality Broken)

| # | Issue | Fix | Impact |
|---|-------|-----|--------|
| 5 | 43 test failures | Fix mock paths to adapters.models.model_router | Test suite usable |
| 6 | 37 broken wikilinks | Move 10_Wiki/ contents into knowledge/ | Knowledge system functional |
| 7 | Palace rooms empty | Re-run palace generation with corrected graph | Retrieval hierarchy works |
| 8 | Resume packet bloat (212 dupes) | Deduplicate and prune stale entries | Clean resume state |
| 9 | mesh/metrics.jsonl 205 MB | Implement JSONL rotation (keep last 7 days) | Recover 180+ MB |

### P2 — Do This Sprint (Degraded)

| # | Issue | Fix | Impact |
|---|-------|-----|--------|
| 10 | PROTOCOLS.md stale paths | Update all eos_ai/ → substrate/ references | Accurate documentation |
| 11 | AGENTS.md stale | Update LLM reference, file paths | Accurate cross-agent config |
| 12 | ARCHITECTURE.md section numbering | Fix 11→13→12 sequence | Readable spec |
| 13 | Tool skills "EOS" → "UMH" | Batch rename in 96 SKILL.md files | Correct naming |
| 14 | 43 stale tool skills | Run TME staleness sweep | Current mastery |
| 15 | alwaysThinkingEnabled discrepancy | Decide and align CLAUDE.md ↔ settings.json | Consistent config |
| 16 | Content/content case collision | Merge into one directory | Cross-platform safety |

### P3 — Do This Month (Technical Debt)

| # | Issue | Fix | Impact |
|---|-------|-----|--------|
| 17 | 3 execution paths | Unify into single path with feature flags | Architecture coherence |
| 18 | 108 dependency direction violations | Move imports to socket pattern | Clean architecture |
| 19 | 61K lines dead code | Delete workstation/ and unused governance layers | Maintainability |
| 20 | Schema drift (7 migration-only tables) | Add to schema.ts or document as Python-only | ORM accuracy |
| 21 | Embedding dimension mismatch | Verify actual column, align migration + schema | Data integrity |
| 22 | SaaS API not running | Add to docker-compose as service | SaaS functional |
| 23 | Test artifacts in data/runtime/ | Delete 944 files | Recover 50 MB |
| 24 | docs/ 107 stale eos_ai/ references | Batch update or archive | Clean documentation |

### P4 — Architectural (Next Quarter)

| # | Issue | Fix | Impact |
|---|-------|-----|--------|
| 25 | ConversationMemory is volatile | Wire to Neon or Canonical Memory Store | Persistent memory |
| 26 | Production governance is regex-only | Wire AuthorityEngine into production path | Real governance |
| 27 | World model never queried live | Wire into CognitiveLoop context assembly | Intelligence upgrade |
| 28 | Autonomous loops not running | Start loop_runner.py via systemd or cron | Persistent autonomy |
| 29 | Node mesh daemon stopped | Restart and wire into cockpit | Distributed execution |
| 30 | SaaS auth header-only | Implement proper JWT/session auth | Production security |

---

## Appendix A: File Count by Top-Level Directory

| Directory | Files (excl node_modules) | Primary Language | Status |
|-----------|--------------------------|-----------------|--------|
| substrate/ | ~350 | Python | CANONICAL — production + dormant |
| adapters/ | ~80 | Python | CANONICAL — production |
| transports/ | ~60 | Python | CANONICAL — production |
| projections/ | ~40 | Python | CANONICAL — mostly dormant |
| services/ | ~15 | Python | LEGACY — production entrypoints |
| runtime/ | ~50 | Python | LEGACY — compatibility layer |
| scripts/ | ~40 | Python | OPERATIONAL — cron + tools |
| tests/ | ~100 | Python | 43 failing |
| nodes/ | ~55 | Python | DORMANT — Windows daemon |
| skills/ | 467 | Markdown + Python/TS | ACTIVE — 45% stale |
| knowledge/ | 236 | Markdown | STALE — 37 broken links |
| docs/ | 475 | Markdown | STALE — 107 dead refs |
| data/ | ~8,100 | JSON/JSONL/MD | ACTIVE — needs rotation |
| saas/ | 31 | TypeScript | PARTIAL — schema deployed, server stopped |
| agents/ | 11 | Markdown | CURRENT — well-structured |
| .claude/ | ~40 | Markdown/JSON | CURRENT — 3/4 subagents blocked |
| .agents/ | ~100 | Markdown/Python | THIRD-PARTY — 2 skill packages |
| apps/ | ~0 source | Built JS | DORMANT — no source on VPS |
| frontend/ | 6 | Built JS | DORMANT — no source on VPS |
| docker/ | 3 | Dockerfile/Bash | DORMANT — Beast machine infra |
| infra/ | 4 | Env files | ACTIVE — secrets backbone |
| 10_Wiki/ | 37 | Markdown | ORPHANED — should merge into knowledge/ |
| archive/ | varies | Mixed | ARCHIVED |

## Appendix B: Python Package Map

```
substrate/                          # The UMH brain
├── __init__.py                     # Public API: execute, query, register, status
├── types.py                        # 30+ Pydantic v2 models (SignalEnvelope, Identity, etc.)
├── control_plane/
│   ├── runtime/
│   │   ├── gateway.py              # PRODUCTION entry point (1,922 lines)
│   │   └── cognitive_loop.py       # 8-step thinking engine (1,514 lines)
│   ├── governance.py               # Regex risk classification
│   ├── router.py                   # Signal lifecycle orchestration
│   ├── registry.py                 # Agent/capability registry
│   ├── memory/                     # Memory adapters
│   ├── identity/                   # AI identity management
│   ├── context/
│   │   └── context_builder.py      # 25-layer context assembly (544 lines)
│   └── orchestrator/
│       └── orchestrator.py         # Morning cycle, CEO delegation (1,905 lines)
├── execution/
│   ├── spine.py                    # 8-stage execution pipeline (521 lines)
│   ├── pipeline.py                 # WorkPacket execution (554 lines)
│   ├── trace.py                    # Trace recording + Neon
│   ├── feedback.py                 # Quality scoring + learning
│   ├── ingestion/                  # Canonical ingestion path
│   ├── bridge/                     # Session management
│   ├── loop/                       # Persistent loops + registry
│   ├── actuation/                  # Real-world action execution
│   └── workers/workstation/        # DORMANT (22,400 lines, 42 files)
├── governance/
│   ├── authority.py                # DB-backed authority (not in production)
│   ├── execution_authority.py      # 13-dimension scoring (not in production)
│   ├── policy.py                   # Risk→verdict (not in production)
│   └── quality.py                  # 4-value lens (not in production)
├── understanding/
│   ├── perception/                 # Signal perception
│   ├── interpretation/             # Meaning extraction
│   ├── domains/                    # Domain-specific understanding
│   ├── ontology/                   # Laws, primitives, relationships
│   ├── world_model/                # Canonical + instance world state
│   └── signals/                    # Signal processing
├── state/                          # Persistence (business, memory, profiles, session)
├── sockets/                        # Abstract ports (notification, channel, signal, etc.)
├── interface/                      # Channel surfaces (should be in transports/)
├── composition/                    # Mastery registries (dormant)
├── observability/
│   └── error_recorder.py           # Centralized error recording
└── ontology/                       # Laws, primitives, relationships

adapters/                           # External system adapters
├── models/
│   ├── model_router.py             # Intelligence routing (1,496 lines)
│   ├── cc_sdk.py                   # Claude Code Agent SDK (465 lines)
│   ├── llm_adapter.py              # LLM adapter wrapping model_router
│   └── agent_runtime.py            # Agent execution with fallback
├── calendar/                       # Google Calendar
├── google_workspace/               # GWS adapter
├── browser/                        # Browser automation
├── capabilities/                   # Capability adapters
└── data_source_adapters/           # File/GWS ingestion sources

transports/                         # I/O surfaces
├── discord/
│   ├── bot.py                      # Substrate-wired Discord bot
│   └── signal_factory.py           # Message → SignalEnvelope
├── api/
│   └── cockpit.py                  # 58 REST endpoints + WebSocket (1,809 lines)
├── presence/handlers/              # Command dispatch, report handlers
└── node_mesh/                      # Distributed node communication

projections/                        # Application-specific views
└── eos/                            # EntrepreneurOS agents + workflows

services/                           # Deployment entrypoints
├── discord_bot.py                  # Production Discord bot (1,930 lines)
├── discord_message_handlers.py     # Extracted message handlers
├── discord_bot_commands.py         # Extracted bot commands
├── operator_api.py                 # Legacy operator API
└── higgsfield_webhook.py           # Video generation webhook
```

---

*This audit was produced by 19 parallel investigation agents reading every file in /opt/OS. It represents the ground truth of the codebase as of 2026-05-25.*
