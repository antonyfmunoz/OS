# Agent Artifact Inventory v1

**Date**: 2026-05-03
**Phase**: 89 — Controlled Ingestion Batch + Context Rehydration v1
**Source**: Local files only — `agents/*.md`, `.claude/agents/*.md`, `eos_ai/agent_runtime.py`
**Total agents inventoried**: 23 (19 soul docs + 4 CC subagents)

---

## Soul Document Agents (agents/*.md)

These define character, judgment, role boundaries, communication standards, and hard stops. Loaded at position 0a in `agent_runtime.py run()`.

### Active Agents

| # | Name | File | Domain | Description (Trigger) | Model | Status |
|---|------|------|--------|----------------------|-------|--------|
| 1 | `ceo-agent` | `ceo_agent.md` | Strategic direction | CEO coordination layer — strategic direction, agent delegation, org decisions across all ventures | sonnet | ACTIVE |
| 2 | `content-agent` | `content_agent.md` | Content production | Creates content packages for filming — hooks, captions, video briefs | sonnet | ACTIVE |
| 3 | `customer-success-agent` | `customer_success_agent.md` | Client management | Manages enrolled client transformation — check-ins and testimonial capture | sonnet | ACTIVE |
| 4 | `developer-agent` | `developer_agent.md` | Technical development | Builds, tests, and maintains EOS infrastructure — all code changes and system improvements | sonnet | ACTIVE |
| 5 | `empyrean-ceo` | `empyrean_ceo.md` | Empyrean Studio strategy | CEO of Empyrean Creative — all Empyrean strategy and build decisions | sonnet | ACTIVE (dormant — entity pre-revenue) |
| 6 | `executive-assistant` | `executive_assistant.md` | Founder interface | Primary interface for founder requests — inbox, calendar, task coordination, approvals, daily briefings | sonnet | ACTIVE |
| 7 | `finance-agent` | `finance_agent.md` | Unit economics | Tracks and models unit economics — expense review and financial modeling | sonnet | ACTIVE |
| 8 | `intelligence-agent` | `intelligence_agent.md` | Signal interpretation | Interprets research into actionable direction — translates signals into outreach angles | sonnet | ACTIVE |
| 9 | `lyfe-institute-ceo` | `lyfe_institute_ceo.md` | Lyfe Institute strategy | CEO of Lyfe Institute — strategy, constraint diagnosis, daily objectives | sonnet | ACTIVE |
| 10 | `marketing-agent` | `marketing_agent.md` | Distribution strategy | Owns distribution strategy — channel strategy when content is live | sonnet | ACTIVE |
| 11 | `operations-agent` | `operations_agent.md` | Process improvement | Improves and documents processes — bottleneck diagnosis and SOP creation | sonnet | ACTIVE |
| 12 | `outreach-agent` | `outreach_agent.md` | First-touch outreach | Sends and tests first-touch outreach — DM generation and opener testing | sonnet | ACTIVE |
| 13 | `personal-brand-ceo` | `personal_brand_ceo.md` | Personal brand strategy | CEO of personal brand — content strategy and audience building decisions | sonnet | ACTIVE |
| 14 | `portfolio-advisor` | `portfolio_advisor.md` | Board-level counsel | Board-level strategic counsel — capital decisions, venture sequencing, existential strategic questions | sonnet | ACTIVE |
| 15 | `research-agent` | `research_agent.md` | ICP intelligence | Sources and surfaces ICP intelligence — signal discovery and pattern detection | sonnet | ACTIVE |
| 16 | `sales-agent` | `sales_agent.md` | Sales conversion | Closes sales conversations — lead replied, needs conversion to booked call or sale | sonnet | ACTIVE |

### Deprecated/Template Agents

| # | Name | File | Status | Notes |
|---|------|------|--------|-------|
| 17 | `portfolio-agent` | `portfolio_agent.md` | DEPRECATED | Absorbed into `portfolio-advisor` — do not use |
| 18 | `ea-template` | `ea_template.md` | TEMPLATE | Template for instantiating new EA soul docs — not a live agent |

### Agent Hierarchy Map

| Level | Agent | Reports To | Delegates To |
|-------|-------|-----------|-------------|
| L0 — Board | `portfolio-advisor` | Founder (Antony) | CEOs |
| L1 — CEO | `ceo-agent` | Founder / portfolio-advisor | All L2 agents |
| L1 — CEO | `lyfe-institute-ceo` | Founder / ceo-agent | Relevant L2 agents |
| L1 — CEO | `empyrean-ceo` | Founder / ceo-agent | Relevant L2 agents |
| L1 — CEO | `personal-brand-ceo` | Founder / ceo-agent | content, marketing, outreach |
| L2 — Executive | `executive-assistant` | CEOs | None (coordinator) |
| L2 — Functional | `developer-agent` | Founder (technical) | None |
| L2 — Functional | `content-agent` | personal-brand-ceo | None |
| L2 — Functional | `marketing-agent` | personal-brand-ceo | None |
| L2 — Functional | `outreach-agent` | lyfe-institute-ceo | None |
| L2 — Functional | `sales-agent` | lyfe-institute-ceo | None |
| L2 — Functional | `customer-success-agent` | lyfe-institute-ceo | None |
| L2 — Functional | `research-agent` | ceo-agent | None |
| L2 — Functional | `intelligence-agent` | ceo-agent | None |
| L2 — Functional | `finance-agent` | ceo-agent | None |
| L2 — Functional | `operations-agent` | ceo-agent | None |

---

## Claude Code Native Subagents (.claude/agents/*.md)

These are CC-specific agents with frontmatter defining model, tools, context, and memory settings. Operate within Claude Code sessions.

| # | Name | File | Purpose | Model | Tools | Status |
|---|------|------|---------|-------|-------|--------|
| 19 | `eos-code-reviewer` | `eos-code-reviewer.md` | Adversarial code review after any EOS code change | — | Read, Grep, Glob, Bash, Write, Edit | ACTIVE |
| 20 | `eos-researcher` | `eos-researcher.md` | Research agent for ICP intelligence, market signals, competitor analysis | — | WebSearch, WebFetch, Read, Grep, Glob, Write, Edit | ACTIVE |
| 21 | `eos-simplifier` | `eos-simplifier.md` | Code simplification after implementation — reuse, quality, efficiency | — | Read, Grep, Glob, Edit, Write | ACTIVE |
| 22 | `eos-verifier` | `eos-verifier.md` | Verification after implementation — imports, errors, expected behavior | — | Bash, Read, Grep, Write, Edit | ACTIVE |

### CC Subagent Workflow

```
Implementation complete
    → eos-code-reviewer (adversarial review)
    → eos-simplifier (quality/reuse)
    → eos-verifier (correctness verification)

Research needed
    → eos-researcher (web search + analysis)
```

---

## Agent Infrastructure (Code Layer)

| Component | Location | Purpose |
|-----------|----------|---------|
| `eos_ai/agent_runtime.py` | Runtime | Multi-model agent execution with fallback chain |
| `eos_ai/agent_hierarchy.py` | Registry | Org chart and delegation rules |
| `eos_ai/ai_identity.py` | Identity | Step 0 principles loaded before every agent run |
| `eos_ai/model_router.py` | Routing | Intelligence routing — `call_with_fallback()` entry point |
| `eos_ai/model_preferences.py` | Config | Business context routing preferences |

### Current Routing Chain

```
CC SDK (priority 0) → Gemini 2.5 Flash → Ollama qwen2.5:0.5b
CEO/strategic: force_opus=True or agent_type='ceo'
```

---

## External Agent Artifacts (Not Accessed — Candidates)

These are known or suspected to exist in external systems. Listed for future ingestion.

| # | Source | Expected Content | Ingestion Method |
|---|--------|-----------------|-----------------|
| 1 | Google Drive — AI Agents folder | Prior agent designs, conversation exports | Computer Use or manual export |
| 2 | Google Drive — AI Tools folder | Tool evaluations, setup notes | Computer Use or manual export |
| 3 | ChatGPT conversation exports | Prior agent conversations, strategic planning sessions | Manual export from OpenAI |
| 4 | Claude conversation exports | Prior strategic sessions | Manual export from Anthropic |
| 5 | Google Drive — Automations folder | Workflow automation designs | Computer Use or manual export |

### Capture Fields for External Agents (when ingested)

When external agent artifacts are ingested in future batches, capture these 16 fields per agent:

| # | Field | Description |
|---|-------|-------------|
| 1 | `agent_name` | Name used in the original system |
| 2 | `original_platform` | ChatGPT, Claude, custom, etc. |
| 3 | `creation_date` | When created (if known) |
| 4 | `last_active_date` | Last used (if known) |
| 5 | `purpose` | What it was built to do |
| 6 | `domain` | Business domain (sales, content, ops, etc.) |
| 7 | `company_context` | Which entity it served |
| 8 | `capabilities` | What it could do |
| 9 | `limitations` | Known limitations |
| 10 | `prompt_text` | System prompt or instructions (if recoverable) |
| 11 | `tools_used` | Any tools/plugins configured |
| 12 | `model` | Model it ran on |
| 13 | `status` | Active, deprecated, superseded, abandoned |
| 14 | `superseded_by` | Current EOS agent that replaced it (if any) |
| 15 | `unique_knowledge` | Strategic context not captured elsewhere |
| 16 | `migration_notes` | What to preserve when migrating to EOS |

---

## Gaps and Observations

| # | Observation | Impact | Action |
|---|------------|--------|--------|
| 1 | All soul doc agents use `model: sonnet` — no agent-specific model overrides | May under-resource strategic agents | Verify CEO agents get Opus via `agent_type='ceo'` in runtime |
| 2 | `portfolio-agent` deprecated but file still exists | Confusion risk | Consider removing file or adding prominent deprecation notice |
| 3 | No soul docs for per-venture functional agents | Each CEO delegates but recipients are shared | May need venture-scoped agent variants as operations scale |
| 4 | CC subagents blocked without Anthropic credits | Cannot run eos-code-reviewer, eos-verifier, etc. | Restore credits or route subagents through Gemini |
| 5 | External agent artifacts completely un-inventoried | Strategic context may be lost | Priority ingestion target for Phase 90+ |
| 6 | No agent performance metrics captured | Cannot measure agent effectiveness | Future: add execution traces per agent |
