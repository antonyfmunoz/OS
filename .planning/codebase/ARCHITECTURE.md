# Architecture
*Generated: 2026-03-26*
*Focus: arch*

## Summary
EOS is a role-centric AI business operating system built around a four-layer protocol model. The Python `eos_ai/` intelligence layer handles all AI execution and memory; a TypeScript/Hono API in `eos_saas/` serves as the future SaaS surface; Docker services wire everything to external interfaces (Telegram, Discord, webhooks). All state is persisted to a single Neon PostgreSQL instance shared by both layers using row-level security.

---

## Protocol Layers

The four-layer stack governs everything the AI outputs. Each layer wraps the one below. Swapping the LLM does not break the system — intelligence lives in the layers, not the model.

```
Layer 0 — AI Identity        eos_ai/ai_identity.py
  12 universal principles, injected before everything else
  Non-negotiable, platform-agnostic

Layer 1 — Platform (EOS)     eos_ai/cognitive_loop.py
  8-stage Perceive→Store loop
  Authority gating, prompt enhancement, quality verification

Layer 2 — OS Module          per-venture config + eos_ai modules
  EntrepreneurOS / CreatorOS / LyfeOS subscription surfaces
  Stage-aware gating via BIS (Business Instance Spec)

Layer 3 — Instance Context   ventures table + BIS JSON in Neon
  Org ID, venture ID, stage, ICP, offer, financial targets
  Loaded at runtime — never hardcoded in platform files
```

---

## Cognitive Loop (Layer 1 detail)

`eos_ai/cognitive_loop.py` — every AI task enters here. Direct calls to `AgentRuntime` bypass authority gating and should not be made from outside `eos_ai/`.

**8 stages:**
1. PERCEIVE — inject knowledge (4-layer injection order below)
2. UNDERSTAND — classify intent, resolve agent
3. PLAN — authority engine check (Read / Draft / Execute / Commit)
4. EXECUTE — dispatch to `AgentRuntime` → Haiku or Sonnet
5. VERIFY — quality gate on output
6. REFLECT — RLHF signal evaluation
7. LEARN — skill improvement trigger
8. STORE — write interaction + embedding to Neon

**Knowledge injection order at PERCEIVE:**
```
1a. principle_engine       — root rules for every decision
1b. domain knowledge       — KnowledgeDomainRegistry, top-3 trigger-matched
1b2. layered inject        — get_layered_injection() → 17-layer behavioral distillation
1c. behavioral context     — KnowledgeLayerEngine.get_relevant_layer()
1d. BIS venture context    — BusinessInstanceManager.get_context_for_agents()
1e. ambient reality        — reality_context.py
1f. primitive context      — primitives.py PRIMITIVE_LIBRARY
1g. template + evolution   — template_library.py + evolution_engine.py
1h. hierarchy context      — agent_hierarchy.py per-agent org position
```

All injections are enhancement-only — never block execution on failure.

---

## Agent Hierarchy

```
Level 0   Human / Founder           Always in control. Can override anything.
Level 1   Portfolio Advisor         eos_ai/portfolio_advisor.py — cross-venture intelligence
Level 2   CEO Agent (per venture)   eos_ai/cognitive_loop.py → agent='ceo_agent'
Level 3   Department Agents         eos_ai/agent_teams.py — 6 teams, 25 sub-agents
Level 4   Execution Layer           eos_ai/browser_agent.py — built, not wired
```

**Department teams and sub-agents** (`eos_ai/agent_teams.py`):
- **sales** — icp_qualifier, outreach_writer, objection_handler, follow_up_sequencer, follow_up, call_closer, nurture_sequencer, call_summarizer
- **research** — signal_processor, icp_analyzer, pattern_detector, market_reporter
- **content** — hook_generator, post_writer, arena_post_writer
- **marketing** — campaign_diagnostician, calendar_planner
- **operations** — bottleneck_analyst, war_room_facilitator
- **customer_success** — onboarding_guide, check_in_manager

Soul documents live in `/opt/OS/12_Agents/*.md`. Agents are also registered in Neon `agents` table.

---

## Request Flow

**Telegram → CognitiveLoop → Neon:**
```
1. User sends message or voice to Telegram
2. 13_Scripts/telegram_control.py receives update
3. Routes to EOSGateway.handle() → eos_ai/gateway.py
4. Gateway classifies request type: agent_task | event | status | brief
5. Approval check — some actions require human gate (send, delete, payment, publish)
6. CognitiveLoop.run() → 8-stage loop
7. AgentRuntime dispatches to Haiku (score/classify/summarize) or Sonnet (analyze/generate)
8. Response stored to Neon (interactions + embeddings tables)
9. Result returned via Telegram
```

**Outbound approval flow:**
```
Actions requiring approval → written to 15_Orchestrator/approvals/pending/
Founder approves via Telegram /approve command
Approved → moved to 15_Orchestrator/approvals/approved/
```

**Proactive / scheduled flow:**
```
6am cron → eos_ai/orchestrator.py → morning brief via Telegram
Event bus (eos_ai/event_bus.py) → reactive triggers on signals and outcomes
reality_engine.py → market intel scan every 6h
```

---

## Authority Engine

`eos_ai/authority_engine.py` — 4-tier permission system enforced at PLAN stage.

| Tier    | Scope                                              |
|---------|----------------------------------------------------|
| Read    | View data — never modify                           |
| Draft   | Create drafts — human approves before sending      |
| Execute | Run workflows, send messages, create records       |
| Commit  | Financial actions, contracts — always human-gated  |

Autonomy levels 0–5 configurable per agent. Level 5 never permitted for Finance or Legal.

---

## Model Routing

`eos_ai/agent_runtime.py` — routes by `TaskType`:

| TaskType  | Model  | Use case                             |
|-----------|--------|--------------------------------------|
| SCORE     | Haiku  | ICP scoring, lead qualification      |
| CLASSIFY  | Haiku  | archetype detection, intent          |
| SUMMARIZE | Haiku  | quick summaries, call digests        |
| ANALYZE   | Sonnet | deep signal analysis, conversation   |
| GENERATE  | Sonnet | outreach copy, content, reports      |

`eos_ai/model_preferences.py` provides business-context overrides (venture + task → model config).

---

## Data Architecture

**Single Neon PostgreSQL instance** shared by Python (`eos_ai/db.py` via psycopg2) and TypeScript (`eos_saas/db/` via Drizzle ORM). Row-level security enforced with `SET LOCAL app.current_org_id` on every transaction.

| Table                    | Contents                                        |
|--------------------------|-------------------------------------------------|
| `interactions`           | Every AI call — input, output, model, tokens, cost |
| `embeddings`             | 768-dim semantic vectors (BAAI/bge-small-en-v1.5) |
| `outcomes`               | RLHF signals — thumbs up/down, outcome type     |
| `human_profiles`         | Behavioral profiles of leads and contacts       |
| `agents`                 | Registered agents — soul path, skills, autonomy |
| `skills`                 | 23 skills at 8-component spec                   |
| `tasks`                  | Task lifecycle — queued → completed → outcome   |
| `entity_links`           | Knowledge graph edges                           |
| `events`                 | Event bus log with payload                      |
| `ventures`               | Venture config including BIS JSON               |
| `organizations`          | Org-level RLS isolation boundary                |
| `approvals`              | Pending human approvals queue                   |
| `user_intelligence_profiles` | OS Trinity — cross-product behavioral profile |
| `cross_product_permissions`  | User-granted data sharing between OS products |

**Business Instance Spec (BIS)** — stored as JSON in `ventures.config_json`. Contains: stage (1-6), proof_to_advance, offer_name, offer_price, ICP description, primary_channels, financial_targets, constraints, TAM_estimate, runway_months.

**In-memory at runtime (not persisted):**
- 17-layer knowledge distillation (`eos_ai/knowledge_layers.py`) — 148 behavioral principles
- Domain knowledge registry — 21 domains, 6-layer structure (`eos_ai/knowledge_domains.py`)
- Context window — `CognitiveLoop` session context, compacted at 80% capacity via `eos_ai/context_compaction.py`

---

## Deployment Topology

**VPS: 100.77.233.50** — single server, Docker Compose, always-on.

```
os-bot       telegram_control.py   — Telegram NLP interface
os-monitor   dm_monitor.py         — Instagram DM inbox (Playwright, network_mode: host)
os-scraper   overnight_scrape.py   — batch scrape job (restart: no)
os-webhook   calendly_webhook.py   — Calendly webhook receiver, port 8080
os-discord   discord_bot.py        — Discord community interface (network_mode: host)
```

All containers share `/opt/OS` as a volume. Environment loaded from `13_Scripts/.env` and `eos_ai/.env`. Shared base image: `python:3.11-slim` with Playwright Chromium, Whisper, ffmpeg, espeak.

**Cron** (outside Docker): `0 6 * * *` → `eos_ai/orchestrator.py` → morning brief.

---

## SaaS API Layer

`eos_saas/api/` — Hono (TypeScript) REST API. Not yet deployed as primary interface; exists as future web dashboard backend.

Routes (all behind `authMiddleware`):
- `/ventures` — venture CRUD and BIS management
- `/skills` — skill registry read
- `/interactions` — interaction history
- `/outcomes` — RLHF signal writing
- `/approvals` — approval queue management
- `/agent` — direct agent task dispatch
- `/events` — event bus writes

`eos_saas/bridge/agent_bridge.py` — Python bridge allowing TypeScript API to call Python `CognitiveLoop` directly.

---

## Self-Improvement Loop

```
Interaction completes → stored to Neon (interactions + embeddings)
Founder gives thumbs up/down → outcomes table (RLHF signal)
eos_ai/skill_improvement.py — rewrites skill files from outcome data
eos_ai/evolution_engine.py  — weekly workflow evolution, stage-aware proposals
eos_ai/research_engine.py   — detects knowledge gaps, fills them autonomously
```

---

## Key Files

- `eos_ai/cognitive_loop.py` — core 8-stage loop, entry point for all AI tasks
- `eos_ai/gateway.py` — single control plane, request classification and approval routing
- `eos_ai/agent_runtime.py` — multi-model router (Haiku/Sonnet), TaskType dispatch
- `eos_ai/agent_teams.py` — 6 domain teams, 25 sub-agent configs
- `eos_ai/agent_hierarchy.py` — 5-level org chart, soul doc paths, escalation rules
- `eos_ai/authority_engine.py` — 4-tier permission system
- `eos_ai/db.py` — Neon connection with RLS, venture/skill slug caches
- `eos_ai/memory.py` — all Neon writes (interactions, events, outcomes, profiles)
- `eos_ai/context.py` — EOSContext dataclass, `load_context_from_env()`
- `eos_ai/orchestrator.py` — 6am cron, morning brief, proactive triggers
- `eos_ai/business_instance.py` — BIS stage tracker, 6-stage lifecycle
- `eos_ai/knowledge_layers.py` — 17-layer behavioral distillation, 148 principles
- `eos_ai/knowledge_domains.py` — 21-domain registry, trigger matching
- `eos_ai/ai_identity.py` — Layer 0 identity principles, injected first
- `13_Scripts/telegram_control.py` — primary founder interface, 40+ NLP commands
- `13_Scripts/discord_bot.py` — Discord community interface
- `13_Scripts/dm_monitor.py` — Instagram DM inbox monitor (Playwright)
- `eos_saas/api/index.ts` — Hono REST API, 7 route groups
- `eos_saas/db/schema.ts` — Drizzle schema (TypeScript side of shared DB)
- `docker-compose.yml` — 5-service deployment topology
- `Dockerfile` — shared base image for all services
