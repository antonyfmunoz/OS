---
type: codewiki-dir
dir: skills
---

# `skills/` — the runtime skill library (agent playbooks + Tool Mastery Engine)

**466 files + 16 symlinks · 6,794,042 bytes · [Full file inventory](../inventory/skills.md)**

## Purpose
`skills/` is UMH's operational knowledge library — the reusable, versioned
playbooks that agents load on demand instead of re-deriving from scratch. Each
skill is a directory containing a `SKILL.md` whose YAML frontmatter carries a
trigger-condition `description`, an `effort` level, and a `trigger`
(scheduled/conversational/both). Skills are the mechanical embodiment of the two
Operating Principles in `CLAUDE.md`: the **Tool Mastery Engine** (creator-level
expertise on every external tool) and the **Operationalization Principle**
(after anything works, capture it as a skill so it is never rebuilt). Three
kinds of content live here: business-domain skills that agents execute (sales,
ops, marketing, research, content), meta/framework skills that govern how agents
operate, and the `tools/` reference library that powers the TME.

## How it fits
`skills/` is not a code layer in the projections → transports → adapters →
substrate stack — nothing imports it as a Python module. It is a
knowledge/config surface read at runtime by Claude Code and by the skill
registry that syncs skill definitions into Neon (per `CLAUDE.md`: "Skills synced
to Neon after file creation"). Business skills call into the deterministic layer
via `!` shell hooks — most `SKILL.md` files begin with a live-context injection
`!`python3 /opt/OS/scripts/bis_context.py --fields ...``, pulling the founder's
current stage, ICP, offer, and binding constraint from BIS so the skill's advice
is instance-aware rather than hardcoded. Sixteen entries in `skills/` are
symlinks pointing up into `.agents/skills/` (the canonical home of the
design/frontend skill packages — see [dot-agents.md](./dot-agents.md)); the same
packages are also symlinked from `.claude/skills/`. Governance for authoring
skills lives in `.claude/rules/skills.md` (every `SKILL.md` needs a trigger-style
description and a Gotchas section).

## Structure

| Subdir | Files | Role |
|---|---|---|
| `tools/` | 254 | Tool Mastery Engine reference library — 97 per-tool `SKILL.md` skills plus their `references/best_practices.md` creator-level dossiers |
| `saas-dev-skill/` | 145 | Self-contained TypeScript sub-project: a multi-agent SaaS builder (spec-parser, react-gen, backend-wirer, analytics-delivery) with its own `lib/`, `tests/`, `package.json`, `tsconfig.json` |
| `Sales/` | 20 | Sales-domain skills: qualify_lead, objection_handling, call_to_close, follow_up_sequence, proof_promise_plan_close |
| `meta/` | 14 | Framework/governance skills: `tool_mastery_engine/`, `operationalization_principle/`, `ceo_framework/`, `ea_framework/`, `portfolio_framework/`, `claude_code_best_practices/` |
| `Ops/` | 13 | Operations playbooks: inbound-lead, deal-closed, no-show recovery, war-room agenda, weekly_ceo_report |
| `Research/` | 6 | ICP-signal skills: analyze_icp_signal, detect_icp_patterns, generate_market_report, process_signal_queue |
| `Marketing/` | 4 | campaign_diagnosis, content_calendar, and Content/ subskills |
| `content/` | 3 | analyze_content_performance, discover_content_angles, generate_content_script |
| `Content/` | 2 | content_video_brief, hook_performance_analysis |
| `CustomerSuccess/` | 2 | churn_prevention, onboarding_sequence |
| `Outreach/` | 2 | dm_opener, reply_handler |
| `developer/` | 1 | adversarial_review |
| 16 symlinks | — | Design/frontend packages resolving into `.agents/skills/` (brandkit, refero-design, imagegen-*, image-to-code, industrial-brutalist-ui, minimalist-ui, high-end-visual-design, gpt-taste, design-taste-frontend[-v1], redesign-existing-projects, stitch-design-taste, improve, karpathy-guidelines, full-output-enforcement) |

## Key components

**The Tool Mastery Engine** (`skills/meta/tool_mastery_engine/SKILL.md`, 700
lines, `name: tool-mastery-engine`, `version: 4.0`) is the highest-leverage file
here. Per `CLAUDE.md` it is "a UMH substrate subsystem, not
application-specific." The TME loop, triggered whenever any external tool is
about to be used:

1. **Check** `skills/tools/{toolname}/` — if a skill exists and is current, load
   it and apply creator-level expertise immediately.
2. **Research** — if missing, exhaustively read the official docs and create a
   new tool skill (scaffolded by
   `tool_mastery_engine/scripts/scaffold_tool_skill.py`, following
   `references/research_protocol.md`, 648 lines).
3. **Update** — if the skill is stale (version change, staleness, or a failure),
   re-research and refresh it.

The engine defines "creator-level" as knowing *why* a tool was designed a
certain way and its hidden capabilities — not beginner (copies docs) nor expert
(knows rate limits). `references/tool_doc_registry.md` and
`references/update_intelligence.md` track doc sources and staleness signals.

**`skills/tools/`** is the TME's output: 97 per-tool directories, each with a
`SKILL.md` (operator's-eye overview) and a `references/best_practices.md`
(creator-level dossier, frequently 800–1,600 lines). Coverage spans the UMH
stack — `neon_postgres`, `anthropic_api`, `claude_agent_sdk`, `claude_code`,
`docker`, `discord`, `git`, `google_gemini`, `groq`, `ollama` — and the
business/creator surface — `instagram`, `meta_ads`, `google_ads`, `canva`,
`davinci_resolve`, `fl_studio`, `lightroom`, `notion`, `apify`.

**`skills/meta/`** carries the other governing frameworks:
`operationalization_principle/SKILL.md` (223 lines — the "document → skill →
never rebuild" capture loop), `ceo_framework/` (293 lines), `ea_framework/`,
`portfolio_framework/` (the agent role frameworks), and
`claude_code_best_practices/` (418 lines).

**`skills/saas-dev-skill/`** is an embedded sub-project, not a single skill — a
TypeScript multi-agent SaaS-generation pipeline. Its agents
(`lib/agents/pm-orchestrator.ts`, `architecture-agent.ts`,
`design-system-agent.ts`, `qa-agent.ts`) and stages (`lib/spec-parser/`,
`lib/react-gen/`, `lib/backend-wirer/`, `lib/analytics-delivery/`) are exercised
by a dense `tests/unit/` suite. It is the productization seed for the SaaS-dev
workflow, carried inside the skill library.

## Data & state
- **Reads:** BIS instance context at load time via
  `scripts/bis_context.py` (`!` hooks in most business `SKILL.md` files) — pulls
  name/icp/offer/stage/primary_channel/binding_constraint/north_star, or
  `--founder`. This keeps skills projection-agnostic in code while
  instance-aware at runtime.
- **Writes:** skill definitions are synced into Neon by the skill registry
  after file creation (`CLAUDE.md`: "Skills synced to Neon after file creation").
- **`skills-lock.json`** at the repo root (902 bytes, `version: 1`) pins the
  externally-sourced skills to their upstream GitHub repos + a `computedHash`:
  `humanizer` (blader/humanizer), `improve` (shadcn/improve),
  `karpathy-guidelines` (forrestchang/andrej-karpathy-skills), and `last30days`
  (a research skill living in `.agents/skills/`). The lock lets those vendored
  packages be re-verified against upstream.

## Gotchas
- **Two count surfaces disagree by design.** The manifest reports 254 files
  under `tools/` but there are 97 per-tool `SKILL.md` skills — the difference is
  each tool's `references/*.md` dossiers plus multi-file tools (e.g.
  `claude_code/` alone has 14 reference files). Count skills by `SKILL.md`, not
  by file.
- **The 16 symlinks are not the canonical files.** Editing a design skill means
  editing `.agents/skills/<name>/` — the `skills/<name>` and `.claude/skills/<name>`
  entries are symlinks (`../.agents/skills/...` and `../../.agents/skills/...`
  respectively). Editing "through" a symlink is fine; treating the symlink as an
  independent copy is a mistake. `last30days` and `humanizer` are symlinked from
  `.claude/skills/` but not from `skills/`.
- **Skill authoring is governed, not freeform.** `.claude/rules/skills.md`
  requires every `SKILL.md` to have a trigger-condition `description`
  ("Use when …", not "This skill does …"), a Gotchas section, and a verification
  step. Skills that only describe rather than trigger will not fire correctly.
- **`saas-dev-skill/` has its own `.claude/skills/` tree inside it** (a nested
  skill namespace under `skills/saas-dev-skill/.claude/skills/saas-dev/`) — do
  not confuse it with the repo-root `.claude/skills/`.

## See also
- [dot-agents.md](./dot-agents.md) — canonical home of the design/frontend skills that `skills/` symlinks to
- [dot-claude.md](./dot-claude.md) — `.claude/` skills, agents, and the rules that govern skill authoring
- [agents.md](./agents.md) — agent soul documents that load these skills as workflows
- [scripts.md](./scripts.md) — `bis_context.py` and the skill registry sync tooling
- [architecture.md](../architecture.md) — the four-layer model and the two Operating Principles
