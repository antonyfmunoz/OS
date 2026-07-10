---
type: codewiki-index
dir: (root)
---

# UMH CodeWiki — Complete Repository Map

The definitive, navigable map of the `/opt/OS` repository — **UMH (Universal Meta
Harness)**, a governed intelligence substrate on which applications
(EntrepreneurOS, CreatorOS, LyfeOS) are built as *projections*. Every
directory, folder, and file is accounted for below; per-file inventories live
under [inventory/](inventory/_census.md), narrative pages under `dirs/`.

Generated at commit `a5f09e48e` (2026-07-10). Regenerate with
`UMH_ROOT=/opt/OS python3 scripts/generate_codewiki.py` and validate with
`python3 scripts/verify_codewiki.py`.

## What UMH is (60 seconds)

A production AI substrate running live on a VPS: Discord + a cockpit app
(desktop/web/mobile) are the operator surfaces; all state changes flow through
one canonical governed runtime (`governed_mutation → MutationRouter →
GovernedExecutionSpine`); intelligence routes through a fallback chain
(Claude Opus via subscription → Gemini → Groq → Ollama) with a deterministic
spine that works when every LLM is down. Platform v1.0.0 is frozen
([PLATFORM_SPEC.md](../../PLATFORM_SPEC.md)); development extends it through
published contracts. Start with [architecture.md](architecture.md).

## Census — full accounting (nothing uncounted)

**Raw total: 716,891 regular files** under /opt/OS at generation time.
Every one lands in exactly one category (verifier-enforced):

| Category | Files | What it is |
|---|---|---|
| Inventoried per-file | **4,523** (+37 symlinks) | All source, docs, config, skills — every file has a row with lines + purpose |
| Rolled up (runtime data) | **256,113** (+2) | logs/ 212,532 · data/ 40,487 · vault/ 2,929 · .playwright-mcp 162 · runtime/graphify-out/media |
| Excluded, counted | **456,255** | .claude/worktrees 440,164 (30+ transient agent checkouts) · node_modules 9,414 · .git 3,070 · caches/__pycache__/build outputs 3,607 |
| **Accounted** | **716,891** | = raw total, delta 0 |

Full breakdown: [inventory/_census.md](inventory/_census.md) ·
machine-readable: `_manifest.json`

## Cross-cutting pages

| Page | Contents |
|---|---|
| [architecture.md](architecture.md) | 4-layer dependency law, ontology layers, canonical runtime vs cognitive spine, enforcement gates, diagrams |
| [data-flow.md](data-flow.md) | End-to-end traces (Discord message, governed mutation, cockpit) + storage topology |
| [tech-stack.md](tech-stack.md) | Languages, frameworks, LLM chain, infrastructure |
| [services-runtime.md](services-runtime.md) | What is actually running: Docker services, host processes, cron, systemd, Fly.io |
| [conventions.md](conventions.md) | The operating laws and where each is enforced |
| [health-findings.md](health-findings.md) | Audit findings: dead code, broken symlinks, doc-reality gaps, risks |
| [audit-2026-07-10.md](audit-2026-07-10.md) | Consolidated audit report for this snapshot |
| [vision-alignment.md](vision-alignment.md) | Master-doc vision ↔ codebase alignment: what UMH is (industry terms), maturity tiers, composition gap, bridge roadmap |

## Directory pages

### Platform code

| Directory | Files | Role |
|---|---|---|
| [`substrate/`](dirs/substrate.md) | 1,009 | Universal platform core — 20+ subsystems (types, control plane, execution, governance, state, understanding…) |
| [`substrate/organism/`](dirs/substrate-organism.md) | 275 | Largest subsystem — self-operating agent core + the canonical operation runtime |
| [`adapters/`](dirs/adapters.md) | 101 | External system adapters — model routing (`model_router.py`), browser, GWS, GitHub, Notion, SSH |
| [`transports/`](dirs/transports.md) | 221 | I/O surfaces — Discord (primary), HTTP API infra, node mesh, presence |
| [`services/`](dirs/services.md) | 43 | Deployment entrypoints only — `discord_bot.py`, operator API, bridges |
| [`projections/`](dirs/projections.md) | 69 | Apps on the substrate — EOS (real), CreatorOS/LyfeOS (integration shells) |
| [`nodes/`](dirs/nodes.md) | 58 | Distributed node runtime — Windows Beast daemon, execution environments |
| [`umh/`](dirs/umh.md) | 3 | Thin relay entrypoints (vision, desktop, voice preflight) |
| [`saas/`](dirs/saas.md) | 0 | Dead — source gone, only a `.pyc` and node_modules remain |

### Operator surface

| Directory | Files | Role |
|---|---|---|
| [`cockpit/`](dirs/cockpit.md) | 431 | Electron + React + Capacitor cockpit app (desktop/web/iOS/Android) |
| [`cockpit/src/renderer/`](dirs/cockpit-renderer.md) | 335 | The React app — 80 panels, 81 Zustand stores, 112 components |

### Knowledge, skills, agents

| Directory | Files | Role |
|---|---|---|
| [`skills/`](dirs/skills.md) | 466 | Runtime skill library — 97 tool-mastery skills, business domains, meta frameworks |
| [`.agents/`](dirs/dot-agents.md) | 183 | Canonical home of design/frontend skill packages (symlink target) |
| [`agents/`](dirs/agents.md) | 11 | Agent soul documents (character only, no mechanics) |
| [`knowledge/`](dirs/knowledge.md) | 344 | CANON wiki + memory palace + retrieval rules |
| [`docs/`](dirs/docs.md) | 658 | Documentation store — audits, operations, system, strategy |

### Tooling & infra

| Directory | Files | Role |
|---|---|---|
| [`scripts/`](dirs/scripts.md) | 213 | Knowledge stack, pre-commit gates, cron wrappers, ops tooling |
| [`tests/`](dirs/tests.md) | 449 | Test suite + certification suites + law-enforcing tests |
| [`infra/`](dirs/infra.md) | 19 | Device/service registries, systemd units, crontab |
| [`docker/`](dirs/docker.md) | 3 | Computer-use container (Beast) |
| [`config/`](dirs/config.md) | 1 | Non-secret env config |
| [Root files](dirs/_root-files.md) | 35 | Constitution docs, compose/Dockerfile, campaign reports |

### Workspace & hidden

| Directory | Files | Role |
|---|---|---|
| [`.claude/`](dirs/dot-claude.md) | 157 | CC config: 13 law files, 24 slash commands, 4 subagents, skills (+440K excluded worktree files) |
| [`.planning/`](dirs/dot-planning.md) | 39 | GSD planning workspace |
| [`.github/`](dirs/dot-github.md) | 1 | CI — mobile cockpit build workflow |
| [`.obsidian/`](dirs/dot-obsidian.md) | 8 | Obsidian vault config |
| [`.vscode/`](dirs/dot-vscode.md) | 1 | Editor settings |
| [`.claire/`](dirs/dot-claire.md) | 0 | Dead worktree remnant (cleanup candidate) |

### Runtime data (rollups)

| Directory | Files | Role |
|---|---|---|
| [`data/`](dirs/data.md) | 40,487 | Persistent app data — organism state, knowledge artifacts, audits, registries |
| [`logs/`](dirs/logs.md) | 212,532 | Application logs (growth concern — see health findings) |
| [`vault/`](dirs/vault.md) | 2,929 | Conversation memory vault |
| [`runtime/`](dirs/runtime.md) | 2 | Live substrate state (gitignored) |
| [`graphify-out/`](dirs/graphify-out.md) | 1 | 44 MB graph.json build artifact |
| [`media/`](dirs/media.md) | 0 | Empty media output scaffold |
| [`.playwright-mcp/`](dirs/dot-playwright-mcp.md) | 162 | Browser automation debug artifacts |

## How to use this wiki

1. New to the system → [architecture.md](architecture.md) then
   [data-flow.md](data-flow.md).
2. Working in a directory → its `dirs/` page for narrative + gotchas, its
   `inventory/` page for the complete file table.
3. Operating the system → [services-runtime.md](services-runtime.md).
4. Before writing code → [conventions.md](conventions.md) (the laws are
   enforced by pre-commit gates; knowing them first is cheaper).
5. Structural questions → `UMH_ROOT=/opt/OS python3 scripts/query_graph.py
   <deps|dependents|centrality|search> …` (see [dirs/scripts.md](dirs/scripts.md)).

## Relationship to the other knowledge systems

This CodeWiki is one of three knowledge layers, each with a different job:
`data/codebase_pages/` (35K auto-generated symbol pages — per-file/class/function
graph views), `knowledge/` (CANON business wiki + memory palace), and
`docs/codewiki/` (this — the human-navigable narrative map with full-accounting
inventory). See [dirs/knowledge.md](dirs/knowledge.md) for how they relate.
