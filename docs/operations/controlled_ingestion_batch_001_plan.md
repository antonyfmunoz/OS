# Controlled Ingestion Batch 001 — Plan

**Date**: 2026-05-03
**Phase**: 89 — Controlled Ingestion Batch + Context Rehydration v1
**Operator**: Antony F. Munoz
**Status**: ACTIVE

---

## Objective

Read-only inventory and structured extraction from all known local sources and external source candidates. No scraping, no API calls, no external system access. Everything derived from files already on disk or explicitly documented source locations.

---

## Source Inventory — Local (On-Disk)

### Strategy Documents (11 files)

| # | File | Purpose | Priority |
|---|------|---------|----------|
| 1 | `docs/strategy/master_intention_lock.md` | Single canonical strategic reference — identity, empire architecture, priorities | CRITICAL |
| 2 | `docs/strategy/company_map.md` | 5-entity corporate structure with roles, stages, workflows | CRITICAL |
| 3 | `docs/strategy/product_map.md` | 6+ products with purpose, stage, user, data produced | CRITICAL |
| 4 | `docs/strategy/first_operating_workflow.md` | 16-stage Personal Brand → Initiate Arena revenue loop | CRITICAL |
| 5 | `docs/strategy/current_doctrine_index.md` | 40+ active doctrines governing system behavior | HIGH |
| 6 | `docs/strategy/source_ingestion_map.md` | Source types, governing doctrines, safety rules | HIGH |
| 7 | `docs/strategy/war_sprint_context_manifest.md` | Phase status, read order, end-state checklist | HIGH |
| 8 | `docs/strategy/north_star_workflow_definitions.md` | North Star dual-track workflow specs | HIGH |
| 9 | `docs/strategy/phased_context_ingestion_plan.md` | Ingestion phase roadmap | MEDIUM |
| 10 | `docs/strategy/google_drive_source_inventory.md` | External source candidates (if exists) | MEDIUM |
| 11 | `docs/strategy/self_build_workflow.md` | Self-build track workflow definition | MEDIUM |

### System Documents (35+ files)

| Category | Count | Path Pattern | Key Files |
|----------|-------|-------------|-----------|
| Phase reports | 18 | `docs/system/phase*_report.md` | All phases 75a–88 |
| Architecture | 3 | `docs/system/{codebase_map,dependency_graph,module_inventory}.json` | Structural truth |
| Control plane | 2 | `docs/system/{control_plane,orchestrator}.md` | Execution infrastructure |
| Deprecation | 1 | `docs/system/deprecation_plan.md` | What to remove |
| MVP scope | 1 | `docs/system/mvp_scope.md` | Delivery boundary |
| Layering | 1 | `docs/system/layering_violations.md` | Architecture health |

### Operations Documents (8 files)

| # | File | Purpose |
|---|------|---------|
| 1 | `business_test_001_packet.md` | BOT-001 daily operating packet |
| 2 | `business_test_001_results.md` | BOT-001 results template |
| 3 | `first_workflow_test_run_template.md` | Generic test run template |
| 4 | `business_workflow_test_run_template.md` | Business track template |
| 5 | `self_build_test_001_packet.md` | Self-build test packet |
| 6 | `self_build_test_001_results.md` | Self-build test results |
| 7 | `self_build_workflow_test_run_template.md` | Self-build track template |
| 8 | `north_star_test_run_template.md` | North Star dual-track template |

### Wiki (30+ entities)

| Category | Location | Count |
|----------|----------|-------|
| Concepts | `10_Wiki/entities/concepts/` | ~15 |
| Decisions | `10_Wiki/entities/decisions/` | ~10 |
| Palace rooms | `10_Wiki/palace/rooms/` | ~8 |
| Index | `10_Wiki/index.md` | 1 |
| Cloud palace | `10_Wiki/cloud_palace.md` | 1 |
| Retrieval rules | `10_Wiki/retrieval_rules.md` | 1 |

### Vault (5 directories, 540+ files)

| Directory | Count | Content |
|-----------|-------|---------|
| `vault/memory/conversations/` | 395 | Session conversation logs |
| `vault/memory/summaries/` | 144 | Session summaries |
| `vault/memory/Conversion_Signals/` | 1 | Lead conversion signals |
| `vault/daily/` | 2 | Daily logs (March 2026) |
| `vault/dashboard/` | 5 | Clients, Home, Product, Sales, Content dashboards |
| `vault/clients/` | 1 | Client template |
| `vault/insights/` | 1 | Insights log |

### Agent Definitions (23 total)

| Location | Count | Type |
|----------|-------|------|
| `agents/*.md` | 19 | Soul documents (character, judgment, role) |
| `.claude/agents/*.md` | 4 | CC native subagents (eos-code-reviewer, eos-researcher, eos-simplifier, eos-verifier) |

### Skills (158 total)

| Category | Count | Location |
|----------|-------|----------|
| Tool skills | 96 | `skills/tools/*/SKILL.md` |
| Meta skills | 9 | `skills/meta/*/SKILL.md` |
| Domain skills | 53 | `skills/{Content,CustomerSuccess,Marketing,Ops,Outreach,Research,Sales,content,developer}/` |

### Memory Files (13)

| Location | Purpose |
|----------|---------|
| `~/.claude/projects/-opt-OS/memory/` | Cross-session memory (project state, intelligence routing, substrate, recent builds, etc.) |

### Code Modules

| Metric | Value |
|--------|-------|
| UMH directories | 144 |
| UMH top-level packages | 67 |
| Total tests collected | 16,795 |
| Completed phases | 18+ (75a–88) |

---

## Source Inventory — External Candidates (Not Accessed)

These are known to exist based on user documentation. They are listed here as future ingestion candidates, NOT accessed in this batch.

### Google Drive (25+ folders/files)

| # | Folder/File | Expected Content | Ingestion Priority |
|---|-------------|-----------------|-------------------|
| 1 | UMH | Architecture docs, design notes | HIGH |
| 2 | EntrepreneurOS | Product specs, roadmaps | HIGH |
| 3 | LyfeOS | Product specs | MEDIUM |
| 4 | CreatorOS | Product specs | MEDIUM |
| 5 | AI Tools | Tool evaluations, setup notes | MEDIUM |
| 6 | AI Agents | Agent designs, conversation exports | HIGH |
| 7 | Automations | Workflow designs, integration specs | MEDIUM |
| 8 | Systems Inventory | Current tools/services in use | HIGH |
| 9 | Coaching Frameworks | Initiate Arena curriculum, coaching methodology | HIGH |
| 10 | Content Calendar/Strategy | Content plans, positioning docs | HIGH |
| 11 | Email Sequences | Sales/nurture email copy | MEDIUM |
| 12 | Offer Documents | Pricing, packaging, sales pages | HIGH |
| 13 | Brand Guidelines | Visual identity, voice guidelines | MEDIUM |
| 14 | Business Plans | Entity-level plans, projections | MEDIUM |
| 15 | Financial Models | Revenue models, expense tracking | MEDIUM |
| 16 | Legal/Contracts | Entity formation docs, agreements | LOW |
| 17 | Client Files | Past client work (Empyrean Studio) | LOW |
| 18 | Course Materials | Initiate Arena content drafts | HIGH |
| 19 | Social Media Assets | Graphics, templates, captions | MEDIUM |
| 20 | Competitor Research | Market analysis, competitor profiles | MEDIUM |
| 21 | Partnership Docs | Collaboration frameworks | LOW |
| 22 | Personal Development | Reading notes, frameworks learned | LOW |
| 23 | Music/Creative | FL Studio projects, creative assets | LOW |
| 24 | Photography/Video | Media assets, shoot plans | LOW |
| 25 | Meeting Notes | External meeting notes, call recordings | MEDIUM |

### Other External Sources (Not Accessed)

| Source | Type | Status |
|--------|------|--------|
| ChatGPT conversation exports | AI chat history | CANDIDATE — requires manual export |
| Claude conversation exports | AI chat history | CANDIDATE — requires manual export |
| Notion databases | Knowledge base | CANDIDATE — API access available |
| Gmail | Communications | CANDIDATE — GWS scanner exists |
| Instagram | Content + engagement data | CANDIDATE — requires Computer Use (Phase 90) |
| Discord | Community conversations | CANDIDATE — bot integration exists |
| Neon Postgres | Structured data | CANDIDATE — direct access available |

---

## Ingestion Rules for This Batch

1. **Read-only** — no writes to external systems
2. **Local files only** — no API calls, no scraping, no network requests
3. **No scraping social media** — no Instagram, no X, no TikTok
4. **No sending messages** — no DMs, no emails, no notifications
5. **No financial transactions** — no payments, no subscriptions
6. **Structured output** — all extractions go into typed documents
7. **Source attribution** — every extracted fact cites its source file
8. **Conflict resolution** — `master_intention_lock.md` wins all conflicts
9. **Staleness marking** — if a source appears outdated, mark it, don't correct it
10. **Missing context flagging** — unknown information listed explicitly, not inferred

---

## Extraction Priority Order

1. User profile (identity, role, goals, constraints)
2. Company map (entities, stages, relationships)
3. Product/offer map (products, offers, pricing, stages)
4. Workflow context (16-stage loop, KPIs, targets)
5. Personal brand context (voice, aesthetic, content strategy)
6. Agent artifact inventory (all defined agents)
7. Content/positioning inventory (content angles, hooks, CTAs)
8. Template candidate inventory (repeating patterns)
9. Missing context list (gaps that need future ingestion)
10. Review queue (conflicts, staleness, ambiguity)

---

## Success Criteria

- [ ] All 10 structured outputs produced
- [ ] Every extraction cites source file
- [ ] No external API calls made
- [ ] No inferred data — only extracted or explicitly flagged as missing
- [ ] Missing context list is comprehensive
- [ ] Agent artifact inventory covers all 23 defined agents
- [ ] Review queue identifies all conflicts and staleness
