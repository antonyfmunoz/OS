# Codebase Structure
*Generated: 2026-03-26*
*Focus: arch*

## Summary
The OS repo is a monorepo combining an AI intelligence layer (Python), a SaaS API bridge (TypeScript/Hono), and an operational knowledge base (Markdown). The directory numbering system (00_–15_) is an Obsidian vault convention adapted for the AI system. Core AI logic lives in `eos_ai/` (67 Python modules).

## Top-Level Layout

```
/opt/OS/
├── eos_ai/              # AI intelligence layer — 67 Python modules
├── eos_saas/            # SaaS API bridge — TypeScript/Hono + Drizzle
├── 13_Scripts/          # Automation scripts — Telegram bot, DM monitor, scrapers
├── 15_Orchestrator/     # Scheduled tasks, approvals, daily ops
├── 12_Agents/           # Agent soul documents (.md)
├── 06_Skills/           # Agent skill files (.md) organized by department
├── 03_CRM/              # CRM data — pipeline, leads, conversations
├── 07_Knowledge/        # ICP profiles, market reports
├── 05_Workflows/        # Process workflows by function
├── 04_Offers/           # Offer documentation
├── 09_Content/          # Content ideas and drafts
├── 01_Inbox/            # Signal processing inbox (raw + processed)
├── 14_Templates/        # Reusable templates
├── .claude/             # Claude Code config — skills, hooks, commands
├── .agents/             # Agent skills directory
├── .planning/           # GSD planning artifacts
├── data/                # Runtime data files
├── knowledge/           # Knowledge base files
├── vault/               # Vault files
├── archive/             # Archived scripts
└── products/            # Product definitions
```

## eos_ai/ Module Groups

### Core Loop (entry points)
- `cognitive_loop.py` — 8-stage processing loop, main AI entry point
- `gateway.py` — external-facing entry point (NOTE: known param bug)
- `agent_runtime.py` — multi-model LLM dispatch (Claude → Qwen fallback)
- `orchestrator.py` — 6am cron + morning cycle (1,461 lines)

### Identity & Hierarchy
- `ai_identity.py` — Layer 0: 12 non-negotiable AI principles
- `agent_hierarchy.py` — org chart, reporting structure
- `agent_teams.py` — domain sub-agents and team router
- `primitives.py` — 13 business knowledge primitives

### Context & State
- `context.py` — runtime context loading from env
- `business_instance.py` — BIS (Business Instance State)
- `session_state.py` — cross-session state persistence
- `reality_context.py` — reality grounding layer
- `system_context.py` — system-level context

### Intelligence Engines
- `authority_engine.py` — 4-tier risk/authority classification
- `evolution_engine.py` — business stage progression
- `execution_engine.py` — task execution logic
- `research_engine.py` — market research automation
- `strategy_engine.py` — strategic reasoning
- `principle_engine.py` — principle application
- `quality_gate.py` — output quality validation
- `proactive_engine.py` — proactive insight generation

### Knowledge & Memory
- `memory.py` — all memory writes go to Neon
- `knowledge_graph.py` — knowledge graph operations
- `knowledge_layers.py` — layered knowledge architecture
- `knowledge_domains.py` — domain-specific knowledge
- `knowledge_integrator.py` — knowledge synthesis
- `venture_knowledge.py` — venture-specific knowledge (currently static dict)
- `world_pulse.py` — external signal processing

### Skills & Registry
- `skill_registry.py` — skill loading and lookup
- `claude_skill_registry.py` — Claude Code skill integration
- `harness_registry.py` — agent harness management
- `skill_improvement.py` — skill optimization

### Integrations
- `db.py` — Neon PostgreSQL with RLS
- `gws_connector.py` — Google Workspace connector
- `gws_scanner.py` — GWS document scanner
- `media_processor.py` — voice synthesis, audio processing
- `embedder.py` — text embeddings (currently dimension-mismatched)
- `embedding_engine.py` — embedding storage/retrieval
- `browser_agent.py` — Playwright browser automation

### OS & Tenant
- `tenant.py` — multi-tenant primitives
- `os_registry.py` — OS module registry
- `os_trinity.py` — OS trinity framework
- `trinity.py` — trinity pattern implementation
- `identity_engine.py` — identity management

## eos_saas/ Structure

```
eos_saas/
├── api/
│   ├── routes/          # Hono route handlers
│   ├── middleware/      # Auth, logging middleware
│   └── lib/             # Shared utilities
├── bridge/              # Python↔TypeScript bridge
└── db/
    └── migrations/      # Drizzle migration files
```

## 13_Scripts/ Structure

```
13_Scripts/
├── discord_bot.py       # Primary Discord interface (os-discord service)
├── telegram_control.py  # Telegram mobile control (os-bot service)
├── dm_monitor.py        # Instagram DM monitor (os-monitor service)
├── apify_scraper.py     # Instagram comment scraper
├── icp_scorer.py        # ICP scoring logic
├── overnight_scrape.py  # Scheduled scraping
├── calendly_webhook.py  # Calendly integration receiver
└── instagram_session/   # Session cookies (on disk — security concern)
```

## 06_Skills/ Department Structure

```
06_Skills/
├── Sales/               # Sales skills (qualify, outreach, summarize, etc.)
├── Marketing/           # Content and campaign skills
├── Research/            # ICP analysis, market reports, signal processing
├── Ops/                 # Operations and war room skills
└── CustomerSuccess/     # Customer success skills
```

## 12_Agents/ Soul Documents

Agent soul docs follow a 5-section structure:
Identity → Role → Tone → What you never do → Example responses

Current agents: sales_agent, customer_success_agent, executive_assistant, empyrean_ceo, lyfe_institute_ceo, marketing_agent, operations_agent, finance_agent, portfolio_advisor

## Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Python modules | snake_case | `agent_runtime.py` |
| Python classes | PascalCase | `AgentRuntime` |
| Python methods | snake_case | `run_task()` |
| Directories | numbered prefix + name | `06_Skills/` |
| Agent soul docs | snake_case | `sales_agent.md` |
| Skill files | snake_case | `qualify_lead.md` |
| CRM leads | `lead_{username}_{date}.md` | `lead_jacobwilliamsss__2026-03-19.md` |
| Data files | `YYYY-MM-DD` suffix | `kpi_history.json` |

## Key Files

- `eos_ai/cognitive_loop.py` — core loop, do not break
- `eos_ai/agent_runtime.py` — LLM routing, confirmed working
- `eos_ai/db.py` — Neon connection with RLS, confirmed working
- `13_Scripts/discord_bot.py` — primary human interface
- `docker-compose.yml` — 4-service deployment topology
- `ARCHITECTURE.md` — master specification, read before major changes
