# UMH Developer Codebase Audit - 2026-06-23

This is a fresh audit of `/opt/OS` for developer handoff. It separates editable source from runtime state, generated reports, caches, dependencies, build outputs, and duplicated worktrees.

## Audit Artifacts
- `data/audits/2026-06-23_detailed_inventory.json`
- `data/audits/2026-06-23_detailed_inventory.tsv`
- `data/audits/2026-06-23_full_filesystem_inventory.json`
- `data/audits/2026-06-23_full_filesystem_inventory.tsv`
- `data/audits/2026-06-23_python_source_index.json`
- `data/audits/2026-06-23_typescript_source_index.json`

## Scope Notes
- `.git`, `node_modules`, Python caches, `.claude/worktrees`, Cockpit build output, and similar heavyweight duplicate/generated trees are summarized as skipped-heavy directories in the inventory rather than expanded into the prose report.
- Earlier repo audit docs exist, but their counts are stale relative to this filesystem. This audit derives counts directly from the current tree.
- Git status already had dirty runtime state under `data/umh/organism` and many untracked report/screenshot files before this audit.

## Current Shape
- Detailed files inventoried: 163,900. Detailed directories inventoried: 1,323. Heavy directories summarized: 173.
- Primary source files indexed: 2,158. Python modules indexed: 1,796. TS/JS files indexed: 274.
- Separate raw `find` counts before pruning showed about 670k visible files when `.claude` worktrees and generated surfaces are included; this is not the editable source size.

## Top-Level Map
| Path | Detailed files | Role |
|---|---:|---|
| `logs` | 142,410 | Runtime logs, signal queues, archives, decisions, execution traces, idempotency records. |
| `data` | 14,773 | Runtime/generated state: reports, proofs, registries, source records, organism journals, snapshots, convergence artifacts. |
| `vault` | 2,775 | Local memory vault with conversations/summaries. |
| `substrate` | 961 | Core UMH brain: types, control plane, governance, execution, memory, organism, reality model, state, understanding, workstation. |
| `docs` | 616 | Human docs: audits, setup, operations, strategy, sessions, architecture, changes, research. |
| `skills` | 466 | Agent/tool skill library; includes domain skills and tool-specific instructions. |
| `tests` | 324 | Pytest suite for substrate, organism, APIs, governance, execution, voice, workstation, integrations, phase gates. |
| `knowledge` | 290 | Markdown knowledge base: concepts, entities, decisions, synthesis, palace, retrieval rules. |
| `cockpit` | 278 | Electron/Vite operator cockpit frontend plus build artifacts and package metadata. |
| `transports` | 192 | Ingress/egress: cockpit/operator APIs, Discord, presence handlers, node mesh, webhooks, channels, HTTP TS API. |
| `scripts` | 175 | Operational, verification, graph, cron, hook, scheduled, and worker scripts. |
| `.playwright-mcp` | 162 | tooling/cache/hidden |
| `adapters` | 101 | External integrations and wrappers: LLM routing, Google Workspace, Notion, browser exports, calendar, broadcast, tools. |
| `.agents` | 64 | tooling/cache/hidden |
| `.claude` | 55 | tooling/cache/hidden |
| `nodes` | 52 | Distributed node and Windows environment bootstrap/runtime code. |
| `projections` | 48 | Domain/product projections consuming substrate: EOS, CreatorOS, LYFEOS. |
| `services` | 41 | Deployable process entrypoints and service-local JSON/config for Discord, operator API, webhooks, scraping, bridge/auth utilities. |
| `.planning` | 39 | tooling/cache/hidden |
| `infra` | 17 | Deployment support config, Docker env, scripts, LiveKit config. |
| `agents` | 11 | Agent role/soul/persona docs. |
| `.obsidian` | 8 | tooling/cache/hidden |
| `docker` | 3 | Docker assets, especially computer-use container. |
| `runtime` | 2 | Local runtime station/state area. |
| `umh` | 2 | Small package for voice and vision relay servers. |
| `.dockerignore` | 1 | tooling/cache/hidden |
| `.env.example` | 1 | tooling/cache/hidden |
| `.env.sessions.tpl` | 1 | tooling/cache/hidden |
| `.gitignore` | 1 | tooling/cache/hidden |
| `.mcp.json` | 1 | tooling/cache/hidden |
| `AGENTS.md` | 1 | other |
| `ARCHITECTURE.md` | 1 | other |
| `AUDIT_INDEX.md` | 1 | other |
| `CLAUDE.local.md` | 1 | other |
| `CLAUDE.md` | 1 | other |
| `CODEBASE_AUDIT.md` | 1 | other |
| `Dockerfile` | 1 | deployment/config |
| `EXHAUSTIVE_INVENTORY.md` | 1 | other |
| `Makefile` | 1 | deployment/config |
| `PHILOSOPHY.md` | 1 | other |
| `PROTOCOLS.md` | 1 | other |
| `README.md` | 1 | other |
| `TECHNICAL_REFERENCE.md` | 1 | other |
| `cloud.md` | 1 | other |
| `cockpit-after-login.png` | 1 | other |
| `cockpit-after-wait.png` | 1 | other |
| `cockpit-grey-screen.png` | 1 | other |
| `cockpit-loaded.png` | 1 | other |
| `cockpit-login-check.png` | 1 | other |
| `cockpit-metaide-converged.png` | 1 | other |
| `cockpit-metaide.png` | 1 | other |
| `docker-compose.yml` | 1 | deployment/config |
| `install.sh` | 1 | other |
| `patch_pycord.py` | 1 | other |
| `pyproject.toml` | 1 | deployment/config |
| `requirements.txt` | 1 | deployment/config |
| `setup.sh` | 1 | other |
| `skills-lock.json` | 1 | other |
| `.vscode` | 1 | tooling/cache/hidden |
| `config` | 1 | deployment/config |

## Category Counts
| Category | Files |
|---|---:|
| runtime/generated state | 159,960 |
| editable source (python/runtime) | 1,896 |
| knowledge/docs/skills | 1,383 |
| tooling/cache/hidden | 334 |
| editable source (typescript/frontend-api) | 262 |
| deployment/config | 26 |
| other | 23 |
| frontend package/build/deps | 16 |

## Dominant Extensions
| Extension | Files |
|---|---:|
| `.json` | 144,984 |
| `.md` | 15,377 |
| `.py` | 1,834 |
| `[none]` | 332 |
| `.ts` | 311 |
| `.tsx` | 251 |
| `.jsonl` | 228 |
| `.txt` | 172 |
| `.log` | 156 |
| `.yml` | 107 |
| `.sh` | 45 |
| `.png` | 22 |
| `.js` | 15 |
| `.ps1` | 7 |
| `.bak` | 6 |
| `.wav` | 6 |
| `.tpl` | 5 |
| `.css` | 5 |
| `.toml` | 4 |
| `.sqlite` | 4 |
| `.yaml` | 3 |
| `.html` | 3 |
| `.example` | 2 |
| `.mjs` | 2 |
| `.env` | 2 |
| `.nix` | 2 |
| `.gz` | 2 |
| `.tmp` | 2 |
| `.bat` | 2 |
| `.template` | 1 |
| `.tsv` | 1 |
| `.baj` | 1 |
| `.baf` | 1 |
| `.old` | 1 |
| `.managed` | 1 |

## Heavy / Generated Trees Summarized
| Path | Why summarized | Approx files | Approx dirs |
|---|---|---:|---:|
| `.git` | heavy duplicate/cache/build/dependency tree | 7774 | 443 |
| `.mypy_cache` | heavy duplicate/cache/build/dependency tree | 18 | 1 |
| `.pytest_cache` | heavy duplicate/cache/build/dependency tree | 5 | 2 |
| `.ruff_cache` | heavy duplicate/cache/build/dependency tree | 74 | 1 |
| `__pycache__` | heavy duplicate/cache/build/dependency tree | 1 | 0 |
| `.agents/skills/last30days/scripts/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `.agents/skills/last30days/scripts/lib/__pycache__` | heavy duplicate/cache/build/dependency tree | 22 | 0 |
| `.agents/skills/last30days/tests/__pycache__` | heavy duplicate/cache/build/dependency tree | 9 | 0 |
| `.claire/worktrees/full-convergence/substrate/ontology/__pycache__` | heavy duplicate/cache/build/dependency tree | 1 | 0 |
| `.claire/worktrees/full-convergence/tests/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `.claude/worktrees` | heavy duplicate/cache/build/dependency tree | 178655 | 21479 |
| `adapters/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `adapters/adapter_engine/__pycache__` | heavy duplicate/cache/build/dependency tree | 20 | 0 |
| `adapters/broadcast/__pycache__` | heavy duplicate/cache/build/dependency tree | 14 | 0 |
| `adapters/broadcast/integration/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `adapters/browser/__pycache__` | heavy duplicate/cache/build/dependency tree | 1 | 0 |
| `adapters/browser_exports/__pycache__` | heavy duplicate/cache/build/dependency tree | 8 | 0 |
| `adapters/calendar/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `adapters/capabilities/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `adapters/data_source_adapters/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `adapters/data_source_adapters/parsers/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `adapters/google_workspace/__pycache__` | heavy duplicate/cache/build/dependency tree | 9 | 0 |
| `adapters/higgsfield/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `adapters/models/__pycache__` | heavy duplicate/cache/build/dependency tree | 15 | 0 |
| `adapters/models/routing/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `adapters/notebooklm/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `adapters/notion/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `adapters/notion/integration/__pycache__` | heavy duplicate/cache/build/dependency tree | 12 | 0 |
| `adapters/scrapling/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `adapters/shannon/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `adapters/tool_adapters/__pycache__` | heavy duplicate/cache/build/dependency tree | 12 | 0 |
| `cockpit/dist` | heavy duplicate/cache/build/dependency tree | 12 | 2 |
| `cockpit/dist-web` | heavy duplicate/cache/build/dependency tree | 5 | 1 |
| `cockpit/out` | heavy duplicate/cache/build/dependency tree | 6 | 4 |
| `nodes/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `nodes/distribution/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `nodes/environments/__pycache__` | heavy duplicate/cache/build/dependency tree | 21 | 0 |
| `nodes/windows/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `nodes/windows/umh_desktop/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `nodes/windows/umh_node/__pycache__` | heavy duplicate/cache/build/dependency tree | 7 | 0 |
| `nodes/windows/umh_node/adapters/__pycache__` | heavy duplicate/cache/build/dependency tree | 10 | 0 |
| `projections/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `projections/creatoros/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `projections/creatoros/integration/__pycache__` | heavy duplicate/cache/build/dependency tree | 9 | 0 |
| `projections/eos/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `projections/eos/agents/__pycache__` | heavy duplicate/cache/build/dependency tree | 24 | 0 |
| `projections/eos/integration/__pycache__` | heavy duplicate/cache/build/dependency tree | 10 | 0 |
| `projections/eos/views/__pycache__` | heavy duplicate/cache/build/dependency tree | 8 | 0 |
| `projections/eos/workflows/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `projections/lyfeos/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `projections/lyfeos/integration/__pycache__` | heavy duplicate/cache/build/dependency tree | 9 | 0 |
| `saas/node_modules` | heavy duplicate/cache/build/dependency tree | 4396 | 441 |
| `saas/bridge/__pycache__` | heavy duplicate/cache/build/dependency tree | 1 | 0 |
| `scripts/__pycache__` | heavy duplicate/cache/build/dependency tree | 114 | 0 |
| `scripts/scheduled/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `scripts/workers/__pycache__` | heavy duplicate/cache/build/dependency tree | 1 | 0 |
| `services/__pycache__` | heavy duplicate/cache/build/dependency tree | 27 | 0 |
| `services/auth_flows/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `skills/meta/tool_mastery_engine/scripts/__pycache__` | heavy duplicate/cache/build/dependency tree | 1 | 0 |
| `skills/saas-dev-skill/node_modules` | heavy duplicate/cache/build/dependency tree | 5038 | 417 |
| `substrate/__pycache__` | heavy duplicate/cache/build/dependency tree | 7 | 0 |
| `substrate/composition/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `substrate/composition/mastery/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/composition/mastery/authoring/__pycache__` | heavy duplicate/cache/build/dependency tree | 11 | 0 |
| `substrate/composition/mastery/management/__pycache__` | heavy duplicate/cache/build/dependency tree | 16 | 0 |
| `substrate/composition/mastery/research/__pycache__` | heavy duplicate/cache/build/dependency tree | 18 | 0 |
| `substrate/composition/registries/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/contracts/__pycache__` | heavy duplicate/cache/build/dependency tree | 10 | 0 |
| `substrate/control_plane/__pycache__` | heavy duplicate/cache/build/dependency tree | 8 | 0 |
| `substrate/control_plane/actions/__pycache__` | heavy duplicate/cache/build/dependency tree | 23 | 0 |
| `substrate/control_plane/agents/__pycache__` | heavy duplicate/cache/build/dependency tree | 10 | 0 |
| `substrate/control_plane/context/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/control_plane/coordination/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/control_plane/delegation/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/control_plane/events/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `substrate/control_plane/goals/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/control_plane/identity/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/control_plane/invariants/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/control_plane/onboarding/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `substrate/control_plane/orchestrator/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/control_plane/proactive/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/control_plane/router/__pycache__` | heavy duplicate/cache/build/dependency tree | 7 | 0 |
| `substrate/control_plane/runtime/__pycache__` | heavy duplicate/cache/build/dependency tree | 7 | 0 |
| `substrate/control_plane/runtime/orchestrator/__pycache__` | heavy duplicate/cache/build/dependency tree | 14 | 0 |
| `substrate/control_plane/scheduling/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `substrate/control_plane/signals/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/control_plane/strategy/__pycache__` | heavy duplicate/cache/build/dependency tree | 7 | 0 |
| `substrate/execution/__pycache__` | heavy duplicate/cache/build/dependency tree | 23 | 0 |
| `substrate/execution/actuation/__pycache__` | heavy duplicate/cache/build/dependency tree | 7 | 0 |
| `substrate/execution/adapters/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/execution/agents/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `substrate/execution/bridge/__pycache__` | heavy duplicate/cache/build/dependency tree | 103 | 0 |
| `substrate/execution/ingestion/__pycache__` | heavy duplicate/cache/build/dependency tree | 1 | 0 |
| `substrate/execution/loop/__pycache__` | heavy duplicate/cache/build/dependency tree | 8 | 0 |
| `substrate/execution/media/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/execution/runtime/__pycache__` | heavy duplicate/cache/build/dependency tree | 32 | 0 |
| `substrate/execution/voice/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `substrate/execution/workers/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/execution/workers/workstation/__pycache__` | heavy duplicate/cache/build/dependency tree | 45 | 0 |
| `substrate/foundation/__pycache__` | heavy duplicate/cache/build/dependency tree | 9 | 0 |
| `substrate/governance/__pycache__` | heavy duplicate/cache/build/dependency tree | 10 | 0 |
| `substrate/governance/accountability/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/governance/policy/__pycache__` | heavy duplicate/cache/build/dependency tree | 9 | 0 |
| `substrate/governance/principles/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/governance/quality/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/governance/validation/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `substrate/integrations/__pycache__` | heavy duplicate/cache/build/dependency tree | 8 | 0 |
| `substrate/intelligence/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/memory/__pycache__` | heavy duplicate/cache/build/dependency tree | 13 | 0 |
| `substrate/meta_ide/__pycache__` | heavy duplicate/cache/build/dependency tree | 35 | 0 |
| `substrate/observability/__pycache__` | heavy duplicate/cache/build/dependency tree | 12 | 0 |
| `substrate/ontology/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/ontology/domains/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `substrate/operator/__pycache__` | heavy duplicate/cache/build/dependency tree | 19 | 0 |
| `substrate/organism/__pycache__` | heavy duplicate/cache/build/dependency tree | 423 | 0 |
| `substrate/organism/benchmarks/__pycache__` | heavy duplicate/cache/build/dependency tree | 9 | 0 |
| `substrate/organism/executors/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `substrate/organism/tests/__pycache__` | heavy duplicate/cache/build/dependency tree | 128 | 0 |
| `substrate/reality_model/__pycache__` | heavy duplicate/cache/build/dependency tree | 16 | 0 |
| `substrate/sockets/__pycache__` | heavy duplicate/cache/build/dependency tree | 29 | 0 |
| `substrate/sockets/view/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/state/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/business/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/state/config/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/context/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/finance/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `substrate/state/lifecycle/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/state/logs/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/memory/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/memory/contracts/__pycache__` | heavy duplicate/cache/build/dependency tree | 11 | 0 |
| `substrate/state/metrics/__pycache__` | heavy duplicate/cache/build/dependency tree | 5 | 0 |
| `substrate/state/permissions/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/preferences/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/profiles/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/providers/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/registries/__pycache__` | heavy duplicate/cache/build/dependency tree | 8 | 0 |
| `substrate/state/session/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/storage/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/stores/__pycache__` | heavy duplicate/cache/build/dependency tree | 20 | 0 |
| `substrate/state/tenancy/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/state/work/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/understanding/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/understanding/deliberation/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/understanding/domains/__pycache__` | heavy duplicate/cache/build/dependency tree | 12 | 0 |
| `substrate/understanding/embedding/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/understanding/intelligence/__pycache__` | heavy duplicate/cache/build/dependency tree | 9 | 0 |
| `substrate/understanding/interpretation/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/understanding/knowledge/__pycache__` | heavy duplicate/cache/build/dependency tree | 11 | 0 |
| `substrate/understanding/ontology/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/understanding/patterns/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/understanding/perception/__pycache__` | heavy duplicate/cache/build/dependency tree | 3 | 0 |
| `substrate/understanding/perception/parsers/__pycache__` | heavy duplicate/cache/build/dependency tree | 7 | 0 |
| `substrate/understanding/reality/__pycache__` | heavy duplicate/cache/build/dependency tree | 6 | 0 |
| `substrate/understanding/research/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/understanding/signals/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/understanding/world_model/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `substrate/understanding/world_pulse/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `substrate/workstation/__pycache__` | heavy duplicate/cache/build/dependency tree | 85 | 0 |
| `tests/__pycache__` | heavy duplicate/cache/build/dependency tree | 364 | 0 |
| `tests/adapters/__pycache__` | heavy duplicate/cache/build/dependency tree | 1 | 0 |
| `tests/adapters/broadcast/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `tests/substrate/__pycache__` | heavy duplicate/cache/build/dependency tree | 7 | 0 |
| `transports/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `transports/api/__pycache__` | heavy duplicate/cache/build/dependency tree | 241 | 0 |
| `transports/api/webhooks/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `transports/channels/__pycache__` | heavy duplicate/cache/build/dependency tree | 4 | 0 |
| `transports/discord/__pycache__` | heavy duplicate/cache/build/dependency tree | 11 | 0 |
| `transports/node_mesh/__pycache__` | heavy duplicate/cache/build/dependency tree | 12 | 0 |
| `transports/node_mesh/integration/__pycache__` | heavy duplicate/cache/build/dependency tree | 8 | 0 |
| `transports/presence/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |
| `transports/presence/handlers/__pycache__` | heavy duplicate/cache/build/dependency tree | 13 | 0 |
| `transports/presence/handlers/reports/__pycache__` | heavy duplicate/cache/build/dependency tree | 30 | 0 |
| `umh/__pycache__` | heavy duplicate/cache/build/dependency tree | 2 | 0 |

## Architecture Summary
UMH is a governed intelligence substrate. `substrate/` owns canonical models and runtime logic; `adapters/` bridges external systems; `transports/` exposes Discord/API/presence/node-mesh surfaces; `services/` contains deployable entrypoints; `projections/` provides EOS/CreatorOS/LYFEOS product-specific layers; `cockpit/` is the operator UI; `data/` and `logs/` are state/evidence. The execution model described by project docs is signal -> context/understanding -> governance -> execution -> proof/memory/learning.

## Service and Deployment Surface
`docker-compose.yml` defines `os-discord` (primary interface), `os-operator` (operator API/cockpit backend), `os-webhook`, `os-scraper`, and `os-livekit`. Root dependency declarations are `pyproject.toml` and `requirements.txt`; service-specific requirements and env templates sit under `services/`. Project rules say not to rebuild Docker unless Dockerfile changed.

## Source Directory Density
| Directory | Source files |
|---|---:|
| `tests` | 314 |
| `substrate/organism` | 257 |
| `scripts` | 155 |
| `transports/api` | 127 |
| `cockpit/src/renderer/panels` | 80 |
| `substrate/execution/bridge` | 71 |
| `substrate/organism/tests` | 69 |
| `cockpit/src/renderer/stores` | 68 |
| `substrate/workstation` | 56 |
| `substrate/execution/workers/workstation` | 42 |
| `cockpit/src/renderer/components` | 39 |
| `services` | 38 |
| `nodes/environments` | 19 |
| `substrate/operator` | 19 |
| `substrate/organism/benchmarks` | 19 |
| `substrate/composition/mastery/research` | 18 |
| `substrate/execution/runtime` | 18 |
| `substrate/meta_ide` | 18 |
| `cockpit/src/renderer/components/rooms` | 17 |
| `adapters/adapter_engine` | 16 |
| `substrate/sockets` | 16 |
| `substrate/state/stores` | 15 |
| `transports/presence/handlers/reports` | 15 |
| `cockpit/src/renderer/components/vision` | 14 |
| `nodes/windows/umh_node/adapters` | 12 |
| `projections/eos/agents` | 12 |
| `substrate/control_plane/actions` | 12 |
| `substrate/execution` | 12 |
| `adapters/notion/integration` | 11 |
| `substrate/composition/mastery/authoring` | 11 |
| `substrate/composition/mastery/management` | 11 |
| `cockpit/src/renderer/api` | 9 |
| `projections/eos/integration` | 9 |
| `substrate/control_plane/runtime/orchestrator` | 9 |
| `substrate/foundation` | 9 |
| `adapters/browser_exports` | 8 |
| `adapters/models` | 8 |
| `cockpit/src/renderer/hooks` | 8 |
| `nodes/windows/umh_node` | 8 |
| `substrate/reality_model` | 8 |
| `transports/api/http/routes` | 8 |
| `adapters/broadcast` | 7 |
| `adapters/google_workspace` | 7 |
| `nodes/windows` | 7 |
| `projections/creatoros/integration` | 7 |
| `projections/lyfeos/integration` | 7 |
| `scripts/auth_monitor` | 7 |
| `scripts/scheduled` | 7 |
| `substrate/control_plane/agents` | 7 |
| `substrate/memory` | 7 |
| `substrate/organism/audits` | 7 |
| `substrate/organism/self_use` | 7 |
| `substrate/understanding/perception/parsers` | 7 |
| `transports/presence/handlers` | 7 |
| `adapters/capabilities` | 6 |
| `adapters/tool_adapters` | 6 |
| `cockpit/src/renderer/components/cards` | 6 |
| `substrate/governance` | 6 |
| `substrate/observability` | 6 |
| `substrate/state/memory/contracts` | 6 |
| `substrate/state/registries` | 6 |
| `substrate/understanding/domains` | 6 |
| `substrate/understanding/intelligence` | 6 |
| `substrate/understanding/knowledge` | 6 |
| `transports/discord` | 6 |
| `transports/node_mesh` | 6 |
| `transports/node_mesh/integration` | 6 |
| `adapters/data_source_adapters` | 5 |
| `cockpit/src/renderer` | 5 |
| `substrate/contracts` | 5 |
| `substrate/control_plane/scheduling` | 5 |
| `substrate/control_plane/strategy` | 5 |
| `substrate/execution/actuation` | 5 |
| `substrate/governance/policy` | 5 |
| `substrate/integrations` | 5 |
| `substrate/ontology/domains` | 5 |
| `substrate/organism/executors` | 5 |
| `transports/api/http` | 5 |
| `projections/eos/views` | 4 |
| `projections/eos/workflows` | 4 |
| `substrate` | 4 |
| `substrate/control_plane` | 4 |
| `substrate/control_plane/invariants` | 4 |
| `substrate/control_plane/router` | 4 |
| `substrate/control_plane/runtime` | 4 |
| `substrate/execution/loop` | 4 |
| `substrate/intelligence` | 4 |
| `substrate/ontology` | 4 |
| `tests/adapters/broadcast` | 4 |
| `tests/substrate` | 4 |
| `adapters` | 3 |
| `adapters/broadcast/integration` | 3 |
| `adapters/calendar` | 3 |
| `adapters/data_source_adapters/parsers` | 3 |
| `adapters/models/routing` | 3 |
| `adapters/notion` | 3 |
| `cockpit/src/renderer/types` | 3 |
| `nodes/distribution` | 3 |
| `services/auth_flows` | 3 |
| `substrate/composition` | 3 |
| `substrate/control_plane/context` | 3 |
| `substrate/control_plane/events` | 3 |
| `substrate/control_plane/onboarding` | 3 |
| `substrate/execution/agents` | 3 |
| `substrate/execution/voice` | 3 |
| `substrate/governance/validation` | 3 |
| `substrate/sockets/view` | 3 |
| `substrate/state` | 3 |
| `substrate/state/business` | 3 |
| `substrate/state/finance` | 3 |
| `substrate/state/metrics` | 3 |
| `substrate/understanding` | 3 |
| `substrate/understanding/embedding` | 3 |
| `substrate/understanding/ontology` | 3 |
| `substrate/understanding/patterns` | 3 |
| `substrate/understanding/perception` | 3 |
| `substrate/understanding/reality` | 3 |
| `transports/api/http/db` | 3 |
| `adapters/higgsfield` | 2 |
| `adapters/notebooklm` | 2 |
| `adapters/scrapling` | 2 |
| `adapters/shannon` | 2 |
| `cockpit/src/renderer/dist/web/assets` | 2 |
| `cockpit/src/renderer/lib` | 2 |
| `cockpit/src/renderer/operator` | 2 |
| `cockpit/src/renderer/styles` | 2 |
| `nodes/windows/umh_desktop` | 2 |
| `projections/eos` | 2 |
| `scripts/graph_hooks` | 2 |
| `scripts/hooks` | 2 |
| `substrate/composition/registries` | 2 |
| `substrate/control_plane/coordination` | 2 |
| `substrate/control_plane/delegation` | 2 |
| `substrate/control_plane/goals` | 2 |
| `substrate/control_plane/identity` | 2 |
| `substrate/control_plane/orchestrator` | 2 |
| `substrate/control_plane/proactive` | 2 |
| `substrate/control_plane/signals` | 2 |
| `substrate/execution/adapters` | 2 |
| `substrate/execution/media` | 2 |

## Important Source Areas
### `substrate`
- Role: Core UMH brain: types, control plane, governance, execution, memory, organism, reality model, state, understanding, workstation.
- Indexed Python modules: 956. Indexed TS/JS files: 0.
- Python concentration: `organism` 364, `execution` 164, `control_plane` 77, `state` 64, `workstation` 56, `understanding` 54, `composition` 45, `governance` 19, `operator` 19, `sockets` 19, `meta_ide` 18, `foundation` 9.
### `adapters`
- Role: External integrations and wrappers: LLM routing, Google Workspace, Notion, browser exports, calendar, broadcast, tools.
- Indexed Python modules: 99. Indexed TS/JS files: 0.
- Python concentration: `adapter_engine` 16, `notion` 13, `models` 11, `broadcast` 10, `browser_exports` 8, `data_source_adapters` 8, `google_workspace` 7, `capabilities` 6, `tool_adapters` 6, `calendar` 3, `higgsfield` 2, `notebooklm` 2.
### `transports`
- Role: Ingress/egress: cockpit/operator APIs, Discord, presence handlers, node mesh, webhooks, channels, HTTP TS API.
- Indexed Python modules: 173. Indexed TS/JS files: 17.
- Python concentration: `api` 129, `presence` 23, `node_mesh` 12, `discord` 6, `channels` 2, `__init__.py` 1.
### `services`
- Role: Deployable process entrypoints and service-local JSON/config for Discord, operator API, webhooks, scraping, bridge/auth utilities.
- Indexed Python modules: 25. Indexed TS/JS files: 0.
- Python concentration: `auth_flows` 3, `bridge_health.py` 1, `browser_adapter.py` 1, `cc_webhook_receiver.py` 1, `cost_tracker.py` 1, `discord_bot.py` 1, `discord_bot_commands.py` 1, `discord_message_handlers.py` 1, `export_bridge_handler.py` 1, `goal_api.py` 1, `heartbeat.py` 1, `higgsfield_webhook.py` 1.
### `projections`
- Role: Domain/product projections consuming substrate: EOS, CreatorOS, LYFEOS.
- Indexed Python modules: 47. Indexed TS/JS files: 0.
- Python concentration: `eos` 30, `creatoros` 8, `lyfeos` 8, `__init__.py` 1.
### `cockpit`
- Role: Electron/Vite operator cockpit frontend plus build artifacts and package metadata.
- Indexed Python modules: 1. Indexed TS/JS files: 256.
- Python concentration: `tests` 1.
### `scripts`
- Role: Operational, verification, graph, cron, hook, scheduled, and worker scripts.
- Indexed Python modules: 123. Indexed TS/JS files: 1.
- Python concentration: `scheduled` 3, `__init__.py` 1, `_tme_common.py` 1, `agent_task_executor.py` 1, `auto_report_dispatch.py` 1, `bis_context.py` 1, `browser_gate_collector.py` 1, `build_notion_databases.py` 1, `build_notion_workspace.py` 1, `build_palace.py` 1, `build_skill_graph.py` 1, `calendar_invite_handler.py` 1.
### `tests`
- Role: Pytest suite for substrate, organism, APIs, governance, execution, voice, workstation, integrations, phase gates.
- Indexed Python modules: 323. Indexed TS/JS files: 0.
- Python concentration: `adapters` 5, `substrate` 4, `__init__.py` 1, `conftest.py` 1, `phase13_2_runtime_proofs.py` 1, `test_actuator_bridge.py` 1, `test_agent_executor.py` 1, `test_agent_fleet_runtime.py` 1, `test_agent_workforce_runtime.py` 1, `test_approval_intercepts.py` 1, `test_artifact_registry.py` 1, `test_assumption_tracking_runtime.py` 1.
### `nodes`
- Role: Distributed node and Windows environment bootstrap/runtime code.
- Indexed Python modules: 47. Indexed TS/JS files: 0.
- Python concentration: `windows` 24, `environments` 19, `distribution` 3, `__init__.py` 1.
### `umh`
- Role: Small package for voice and vision relay servers.
- Indexed Python modules: 2. Indexed TS/JS files: 0.
- Python concentration: `vision_relay.py` 1, `voice_server.py` 1.

## Python Module Index (Condensed)
### `adapters/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/adapter_engine/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/adapter_engine/adapter_lifecycle_manager_v1.py`
- Lines: 247. Doc: Adapter Lifecycle Manager v1 for the canonical runtime spine.
- Classes: AdapterState, AdapterHealthRecord, AdapterLifecycleManager
- Functions: _build_evidence
- Imports: __future__, adapters.adapter_engine.adapter_manifest, adapters.adapter_engine.adapter_maturity, dataclasses, datetime, enum, substrate.execution.runtime.execution_contracts_v1, typing
### `adapters/adapter_engine/adapter_manifest.py`
- Lines: 97. Doc: Unified adapter manifest for the UMH substrate layer.
- Classes: AdapterMaturityLevel, AdapterManifest
- Functions: -
- Imports: __future__, adapters.adapter_engine.adapter_registry_contracts, adapters.adapter_engine.modality, adapters.adapter_engine.participant, dataclasses, enum
### `adapters/adapter_engine/adapter_maturity.py`
- Lines: 202. Doc: Generalized adapter maturity evidence model.
- Classes: MaturityEvidence
- Functions: _check_predicate, compute_adapter_maturity, validate_maturity_claim, actuator_to_adapter_maturity, adapter_to_actuator_target
- Imports: __future__, adapters.adapter_engine.adapter_manifest, dataclasses, substrate.execution.actuation.actuator_maturity_v1, typing
### `adapters/adapter_engine/adapter_registry_contracts.py`
- Lines: 157. Doc: Adapter registry contracts for the UMH substrate layer.
- Classes: CapabilityDescriptor, AdapterDescriptor, AdapterRegistry
- Functions: -
- Imports: __future__, adapters.adapter_engine.modality, adapters.adapter_engine.participant, dataclasses, json, pathlib, substrate.execution.runtime.worker_runtime_contracts, typing
### `adapters/adapter_engine/capability_catalog.py`
- Lines: 66. Doc: Per-adapter capability catalog for the UMH substrate layer.
- Classes: CatalogEntry, CapabilityCatalog
- Functions: -
- Imports: __future__, dataclasses, typing
### `adapters/adapter_engine/capability_discovery.py`
- Lines: 376. Doc: Capability discovery orchestrator for the UMH substrate layer.
- Classes: CapabilityDiscoveryOrchestrator
- Functions: _now_iso
- Imports: __future__, adapters.adapter_engine.adapter_manifest, adapters.adapter_engine.capability_catalog, adapters.adapter_engine.modality, dataclasses, datetime, json, logging
### `adapters/adapter_engine/cu_api_parity_v1.py`
- Lines: 260. Doc: CU / API Parity Validator v1 for the UMH substrate layer.
- Classes: ParityConfidence, ParityStatus, ParityCheck, ExtractionComparison, ParityResult
- Functions: compare_extractions, assess_parity
- Imports: .google_docs_adapter_v1, __future__, dataclasses, datetime, enum, hashlib, json, typing
### `adapters/adapter_engine/google_docs_adapter_v1.py`
- Lines: 397. Doc: Google Docs Adapter v1 for the UMH substrate layer.
- Classes: DocsCapabilityType, DocsAdapterStatus, ExtractionPath, DocsOpenProof, ExtractionResult, NormalizedExtraction, GoogleDocsAdapterV1
- Functions: normalize_text
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, typing, uuid
### `adapters/adapter_engine/google_drive_adapter_v1.py`
- Lines: 288. Doc: Google Drive Adapter v1 for the UMH substrate layer.
- Classes: DriveCapabilityType, DriveAdapterStatus, DriveOpenProof, DriveMetadataResult, GoogleDriveAdapterV1
- Functions: -
- Imports: __future__, adapters.adapter_engine.adapter_manifest, adapters.adapter_engine.adapter_registry_contracts, adapters.adapter_engine.modality, adapters.adapter_engine.participant, dataclasses, datetime, enum
### `adapters/adapter_engine/gws_scanner_bridge_v1.py`
- Lines: 176. Doc: GWS Scanner Bridge v1 — translates existing scanner outputs into substrate ingestion contracts.
- Classes: NormalizedTab, NormalizedDocument
- Functions: _extract_text_from_google_doc_body, _compute_content_hash, normalize_from_scanner_outputs
- Imports: __future__, dataclasses, datetime, hashlib, json, pathlib, typing, uuid
### `adapters/adapter_engine/live_drive_docs_ingestion_pipeline_v1.py`
- Lines: 736. Doc: Live Drive/Docs Ingestion Pipeline v1 for the UMH substrate layer.
- Classes: PipelineStage, PipelineProofType, PipelineSnapshot, IngestionCandidate, MemoryCandidate, GovernanceReceipt, ReplayQueryResult, LiveDriveDocsIngestionPipeline
- Functions: -
- Imports: .cu_api_parity_v1, .google_docs_adapter_v1, .google_drive_adapter_v1, __future__, dataclasses, datetime, enum, hashlib
### `adapters/adapter_engine/modality.py`
- Lines: 22. Doc: Communication modality types for UMH adapters.
- Classes: ModalityType
- Functions: -
- Imports: __future__, enum
### `adapters/adapter_engine/participant.py`
- Lines: 21. Doc: Participant type classification for UMH adapters.
- Classes: ParticipantType
- Functions: -
- Imports: __future__, enum
### `adapters/adapter_engine/substrate_candidate_gen_v1.py`
- Lines: 218. Doc: Substrate Candidate Generation v1 — generates ingestion candidates from decomposition.
- Classes: MemoryType, GovernanceState, IngestionCandidate, CandidateSet
- Functions: _deterministic_id, _classify_memory_type, generate_candidates
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, substrate.understanding.ontology.primitive_decomposition_v1, typing
### `adapters/adapter_engine/substrate_decomposer_v1.py`
- Lines: 285. Doc: Substrate Decomposer v1 — deterministic primitive decomposition from normalized documents.
- Classes: -
- Functions: _deterministic_id, _extract_sentences, _classify_sentence, decompose_document, _infer_relationship
- Imports: __future__, dataclasses, datetime, hashlib, json, re, substrate.understanding.ontology.primitive_decomposition_v1, typing
### `adapters/broadcast/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/broadcast/engine.py`
- Lines: 325. Doc: Broadcast engine — owns FFmpeg subprocess lifecycle, config->args, health.
- Classes: BroadcastHealth, BroadcastEngine
- Functions: -
- Imports: __future__, adapters.broadcast.ffmpeg_args, adapters.broadcast.filtergraph, adapters.broadcast.process_lifecycle, adapters.broadcast.scene_model, adapters.broadcast.zmq_client, asyncio, logging
### `adapters/broadcast/ffmpeg_args.py`
- Lines: 253. Doc: Pure deterministic config -> FFmpeg CLI argument list.
- Classes: -
- Functions: _get_allowed_media_dir, build_args, _input_args, _validate_output_url, _validate_file_output, _validate_input_url, _rebuild_url, _reject_control_chars, _resolve_and_pin, _reject_addr
- Imports: __future__, os, typing, urllib.parse
### `adapters/broadcast/filtergraph.py`
- Lines: 217. Doc: Filtergraph builder — scene config -> FFmpeg -filter_complex args.
- Classes: -
- Functions: overlay_filter_name, build_composite_args, _source_input_args, _build_filtergraph, build_scene_switch_commands
- Imports: __future__, adapters.broadcast.scene_model, os, typing
### `adapters/broadcast/integration/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/broadcast/integration/handlers.py`
- Lines: 227. Doc: Broadcast capability handler — implements CapabilityHandler Protocol.
- Classes: BroadcastCapabilityHandler
- Functions: -
- Imports: .manifest, __future__, adapters.broadcast.engine, asyncio, logging, substrate.sockets.envelopes, substrate.sockets.protocols, time
### `adapters/broadcast/integration/manifest.py`
- Lines: 63. Doc: Broadcast integration manifest — declares capabilities for start, stop, status.
- Classes: -
- Functions: -
- Imports: __future__, substrate.governance.risk_classes, substrate.sockets.protocols, substrate.types
### `adapters/broadcast/process_lifecycle.py`
- Lines: 208. Doc: Subsystem-agnostic subprocess lifecycle manager.
- Classes: ProcessLifecycle
- Functions: -
- Imports: __future__, asyncio, logging, os, signal, subprocess, sys, typing
### `adapters/broadcast/scene_model.py`
- Lines: 126. Doc: Scene + SourceEntry models for multi-source compositing.
- Classes: SourceEntry, SourceLayout, Scene, CompositeConfig
- Functions: -
- Imports: __future__, pydantic, re, typing
### `adapters/broadcast/zmq_client.py`
- Lines: 138. Doc: ZMQ command client for live FFmpeg filter parameter control.
- Classes: ZmqCommandResult, ZmqBatchResult, ZmqFilterClient
- Functions: -
- Imports: __future__, logging, time, typing
### `adapters/browser/__init__.py`
- Lines: 11. Doc: Browser adapter — re-exports from substrate execution layer.
- Classes: -
- Functions: -
- Imports: substrate.execution.agents.browser_agent
### `adapters/browser_exports/__init__.py`
- Lines: 28. Doc: Browser export adapters — autonomous data export from web services.
- Classes: -
- Functions: -
- Imports: adapters.browser_exports.chatgpt_export, adapters.browser_exports.claude_export, adapters.browser_exports.contract, adapters.browser_exports.instagram_export, adapters.browser_exports.profile_manager
### `adapters/browser_exports/chatgpt_export.py`
- Lines: 195. Doc: ChatGPT data export trigger — deterministic Playwright script.
- Classes: -
- Functions: trigger_chatgpt_export, _screenshot
- Imports: adapters.browser_exports.contract, adapters.browser_exports.profile_manager, datetime, dotenv, logging, pathlib, sys
### `adapters/browser_exports/claude_export.py`
- Lines: 192. Doc: Claude data export trigger — deterministic Playwright script.
- Classes: -
- Functions: trigger_claude_export, _screenshot
- Imports: adapters.browser_exports.contract, adapters.browser_exports.profile_manager, datetime, dotenv, logging, pathlib, sys
### `adapters/browser_exports/contract.py`
- Lines: 30. Doc: Browser export contract — data classes for export requests and results.
- Classes: ExportRequest, ExportResult
- Functions: -
- Imports: __future__, dataclasses, pathlib, typing
### `adapters/browser_exports/gmail_export_poller.py`
- Lines: 122. Doc: Gmail export email poller — finds export download links in inbox.
- Classes: -
- Functions: poll_for_export_emails
- Imports: datetime, dotenv, logging, pathlib, re, sys
### `adapters/browser_exports/instagram_export.py`
- Lines: 209. Doc: Instagram saved posts export — scrapes saved collection via Playwright.
- Classes: -
- Functions: trigger_instagram_export, _scroll_and_collect_posts, _screenshot
- Imports: adapters.browser_exports.contract, adapters.browser_exports.profile_manager, datetime, dotenv, json, logging, os, pathlib
### `adapters/browser_exports/instagram_export_parser.py`
- Lines: 538. Doc: Instagram curation analyst — classifies saved posts and scores harness candidates.
- Classes: HarnessCandidate, ClassifiedSave, InstagramCurationReport, InstagramSaveSource
- Functions: _classify_url, _categorize_capability, _score_license, _score_activity, _score_maturity, _fetch_github_metadata, _fetch_readme_summary, _parse_github_url, _evaluate_github_repo, parse_instagram_saves, saves_to_sources
- Imports: __future__, dataclasses, datetime, hashlib, json, logging, os, pathlib
### `adapters/browser_exports/profile_manager.py`
- Lines: 183. Doc: ProfileManager — persistent browser context for authenticated exports.
- Classes: ProfileManager
- Functions: -
- Imports: asyncio, dotenv, logging, os, pathlib, substrate.execution.agents.browser_agent, sys
### `adapters/calendar/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/calendar/meetings.py`
- Lines: 837. Doc: Meetings — central module for all meeting lifecycle management.
- Classes: -
- Functions: create_meeting_record, update_meeting_outcome, update_meeting_prep_notes, find_notion_meeting_by_person, get_open_loop_meetings, queue_follow_up_tasks, build_prep_brief, draft_meeting_agenda, draft_meeting_minutes, calculate_meeting_roi
- Imports: datetime, json, logging, os, zoneinfo
### `adapters/calendar/travel_manager.py`
- Lines: 349. Doc: Travel Manager — full trip logistics management.
- Classes: -
- Functions: detect_travel_event, build_travel_brief, log_trip, research_flights, research_hotels, research_restaurants, generate_trip_itinerary, log_loyalty_program, reconcile_trip_expenses
- Imports: datetime, dotenv, json, logging, os, zoneinfo
### `adapters/capabilities/__init__.py`
- Lines: 28. Doc: UMH Capability Contracts — expose all contracts and harnesses.
- Classes: -
- Functions: -
- Imports: .contracts
### `adapters/capabilities/contracts.py`
- Lines: 166. Doc: UMH Capability Contracts — stable interfaces to wrapped external tools.
- Classes: CapabilityResult, CapabilityContract, SoftwareCreationRequest, SoftwareCreationCapability, DesktopControlRequest, DesktopControlCapability, VoiceInteractionRequest, VoiceInteractionCapability
- Functions: -
- Imports: __future__, abc, dataclasses, logging, pathlib, typing
### `adapters/capabilities/creative_gen_harness.py`
- Lines: 230. Doc: Creative generation harness — Tier 1 wrapper for creative_generation capability.
- Classes: CreativeGenHarness
- Functions: -
- Imports: .contracts, __future__, asyncio, logging, os, pathlib, shutil, subprocess
### `adapters/capabilities/goose_harness.py`
- Lines: 135. Doc: Goose harness — Tier 1 subprocess wrapper for software_creation capability.
- Classes: GooseHarness
- Functions: -
- Imports: .contracts, __future__, asyncio, logging, os, shutil, subprocess, time
### `adapters/capabilities/ui_tars_harness.py`
- Lines: 143. Doc: UI-TARS harness — Tier 1 wrapper for desktop_control capability.
- Classes: UITarsHarness
- Functions: -
- Imports: .contracts, __future__, asyncio, logging, os, time, typing
### `adapters/capabilities/voice_pro_harness.py`
- Lines: 266. Doc: Voice-Pro harness — Tier 1 wrapper for voice_interaction capability.
- Classes: VoiceProHarness
- Functions: -
- Imports: .contracts, __future__, asyncio, logging, os, pathlib, shutil, subprocess
### `adapters/data_source_adapters/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/data_source_adapters/conversation_source.py`
- Lines: 108. Doc: ConversationSource — wraps parsed conversation data as an ingestion Source.
- Classes: ConversationTurn, Conversation, ConversationSource
- Functions: -
- Imports: __future__, dataclasses, hashlib, json, os, substrate.governance.policy.authority_tier, substrate.understanding.perception.source, sys
### `adapters/data_source_adapters/github_source.py`
- Lines: 304. Doc: GitHubRepoSource — reads a single file from a cloned GitHub repo as an ingestion source.
- Classes: GitHubRepoSource, GitHubRepoWalker
- Functions: -
- Imports: __future__, collections.abc, hashlib, logging, mimetypes, os, pathlib, subprocess
### `adapters/data_source_adapters/gws_source.py`
- Lines: 89. Doc: GWSSource — wraps GWSDocumentScanner as an ingestion Source.
- Classes: GWSSource
- Functions: -
- Imports: __future__, hashlib, substrate.governance.policy.authority_tier, substrate.understanding.perception.source, typing
### `adapters/data_source_adapters/local_file_source.py`
- Lines: 59. Doc: LocalFileSource — reads a single local file as an ingestion source.
- Classes: LocalFileSource
- Functions: -
- Imports: __future__, hashlib, mimetypes, pathlib, substrate.governance.policy.authority_tier, substrate.understanding.perception.source, typing
### `adapters/data_source_adapters/parsers/__init__.py`
- Lines: 7. Doc: Conversation export parsers for UMH ingestion pipeline.
- Classes: -
- Functions: -
- Imports: adapters.data_source_adapters.parsers.chatgpt_parser, adapters.data_source_adapters.parsers.claude_parser
### `adapters/data_source_adapters/parsers/chatgpt_parser.py`
- Lines: 257. Doc: ChatGPT conversation export parser.
- Classes: -
- Functions: _unix_to_iso, _extract_message_text, _get_message_role, _walk_conversation_tree, _parse_single_conversation, parse_chatgpt_export, _parse_zip, _parse_json_file, _parse_raw_conversations
- Imports: __future__, adapters.data_source_adapters.conversation_source, json, logging, os, pathlib, sys, typing
### `adapters/data_source_adapters/parsers/claude_parser.py`
- Lines: 176. Doc: Claude conversation export parser.
- Classes: -
- Functions: _extract_text_content, _normalize_role, _parse_single_conversation, parse_claude_export, _parse_file
- Imports: __future__, adapters.data_source_adapters.conversation_source, json, logging, os, pathlib, sys, typing
### `adapters/google_workspace/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/google_workspace/doc_creator.py`
- Lines: 367. Doc: Document Creator — generates briefing docs, board updates,
- Classes: -
- Functions: create_briefing_doc, create_presentation_outline, fact_check, draft_announcement, draft_crisis_communication
- Imports: datetime, dotenv, json, logging, os, zoneinfo
### `adapters/google_workspace/document_filer.py`
- Lines: 138. Doc: Document Filing System — intelligently files documents
- Classes: -
- Functions: classify_document, log_document, process_email_attachments
- Imports: datetime, dotenv, json, logging, os, zoneinfo
### `adapters/google_workspace/email_gps.py`
- Lines: 1430. Doc: EmailGPS — 7-folder email management system for DEX.
- Classes: EmailFolder, ProcessedEmail, EmailGPS
- Functions: -
- Imports: asyncio, dataclasses, enum, os, re, subprocess, typing
### `adapters/google_workspace/gws_connector.py`
- Lines: 1117. Doc: GWSConnector — Google Workspace integration via gws CLI.
- Classes: GWSConnector
- Functions: _in_cooldown, _trip_cooldown
- Imports: datetime, dotenv, json, os, pathlib, subprocess, substrate.execution.cpu_gate, time
### `adapters/google_workspace/gws_scanner.py`
- Lines: 704. Doc: GWSDocumentScanner — reads Google Docs the founder owns,
- Classes: GWSDocument, GWSDocumentScanner
- Functions: -
- Imports: dataclasses, datetime, json, os, pathlib, re, subprocess, substrate.execution.cpu_gate
### `adapters/google_workspace/tasks_adapter.py`
- Lines: 89. Doc: Google Tasks adapter — thin wrapper over GWSConnector task methods.
- Classes: TaskItem, GoogleTasksAdapter
- Functions: -
- Imports: __future__, dataclasses, datetime, logging, typing
### `adapters/higgsfield/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/higgsfield/higgsfield_client.py`
- Lines: 113. Doc: Higgsfield Cloud API wrapper for EOS.
- Classes: -
- Functions: generate, get_status, cancel
- Imports: __future__, dotenv, higgsfield_client, json, os, substrate.state.storage.db, sys
### `adapters/models/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/models/agent_runtime.py`
- Lines: 581. Doc: Agent runtime for OS agents.
- Classes: RateLimiter, AgentRuntime
- Functions: -
- Imports: datetime, dotenv, json, os, pathlib, re, substrate.contracts.agent_types, substrate.governance.policy.authority_engine
### `adapters/models/cc_sdk.py`
- Lines: 514. Doc: cc_sdk — Claude Code Agent SDK wrapper for UMH.
- Classes: CCResult
- Functions: _resolve_timeout, _is_error_leak, _track_cc_sdk_result, _cpu_too_hot, _resolve_cli_path, _find_ancestor_oauth, _get_subprocess_env, _is_nested_cc_session, query_cc, _kill_orphaned_claude_procs, _get_claude_pids, query_cc_sync
- Imports: asyncio, dataclasses, logging, os, signal, subprocess, time
### `adapters/models/codex_cli.py`
- Lines: 264. Doc: codex_cli — Codex CLI adapter for EOS.
- Classes: CodexResult
- Functions: _resolve_timeout, _is_error_leak, _track_result, is_available, query_codex_sync, review_codex_sync
- Imports: dataclasses, json, logging, os, shutil, subprocess, substrate.execution.cpu_gate, time
### `adapters/models/hermes_cli.py`
- Lines: 992. Doc: hermes_cli — Hermes Agent runtime adapter for UMH.
- Classes: HermesSession, HermesResult
- Functions: _is_error_leak, _resolve_timeout, _track_result, _mesh_dispatch, _hermes_shell, _hermes_operation, _encode_prompt, _beast_connected, is_available, is_verified, is_configured, health
- Imports: base64, dataclasses, json, logging, os, time, typing, uuid
### `adapters/models/llm_adapter.py`
- Lines: 92. Doc: LLMAdapter — wraps model_router.call_with_fallback() as a substrate Adapter.
- Classes: LLMAdapter
- Functions: -
- Imports: __future__, adapters.protocol, substrate.types, time, uuid
### `adapters/models/model_router.py`
- Lines: 1598. Doc: ModelRouter — standalone multi-model router for EOS.
- Classes: ModelConfig, ModelRouter
- Functions: _deterministic_router_response, _circuit_check, _circuit_record_failure, _circuit_record_success, _track_provider_result, _hermes_allowed_for_purpose, _estimate_quality_score, _should_escalate, _ollama_available, _remote_ollama_available, get_router, _resolve_purpose
- Imports: adapters.models.cc_sdk, adapters.models.codex_cli, adapters.models.hermes_cli, adapters.models.opencode_cli, dataclasses, datetime, enum, json
### `adapters/models/opencode_cli.py`
- Lines: 184. Doc: opencode_cli — OpenCode CLI adapter for EOS.
- Classes: OpenCodeResult
- Functions: _resolve_timeout, _is_error_leak, _track_result, is_available, query_opencode_sync
- Imports: dataclasses, json, logging, os, shutil, subprocess, substrate.execution.cpu_gate, time
### `adapters/models/routing/__init__.py`
- Lines: 17. Doc: Model routing — symbolic capability classes and routing config.
- Classes: -
- Functions: -
- Imports: adapters.models.routing.capabilities, adapters.models.routing.config
### `adapters/models/routing/capabilities.py`
- Lines: 124. Doc: Symbolic capability classes for model routing.
- Classes: -
- Functions: -
- Imports: substrate.contracts.routing_contracts
### `adapters/models/routing/config.py`
- Lines: 129. Doc: Routing config — maps capability classes to runtime/model_router kwargs.
- Classes: RoutingConfig
- Functions: load_routing_config
- Imports: .capabilities, __future__, os, typing
### `adapters/notebooklm/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/notebooklm/notebooklm_sync.py`
- Lines: 309. Doc: NotebookLMSync — bidirectional sync between Neon and NotebookLM.
- Classes: NotebookConfig, NotebookLMSync
- Functions: -
- Imports: dataclasses, datetime, json, os, pathlib, subprocess, substrate.execution.cpu_gate, substrate.state.context.context
### `adapters/notion/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/notion/integration/__init__.py`
- Lines: 2. Doc: Notion integration — manifest, handler, transforms, signals, outcomes.
- Classes: -
- Functions: -
- Imports: -
### `adapters/notion/integration/auth.py`
- Lines: 65. Doc: Notion auth — credential loading from environment.
- Classes: -
- Functions: _ensure_env_loaded, get_notion_client, discover_database_ids
- Imports: __future__, dotenv, notion_client, os, pathlib
### `adapters/notion/integration/correlation.py`
- Lines: 41. Doc: Thread-safe in-memory correlation map for outcome writeback targeting.
- Classes: WritebackTarget, CorrelationMap
- Functions: -
- Imports: __future__, dataclasses, threading, typing, uuid
### `adapters/notion/integration/handlers.py`
- Lines: 215. Doc: Notion capability handler — implements CapabilityHandler Protocol.
- Classes: NotionCapabilityHandler
- Functions: -
- Imports: .auth, .manifest, .transforms, __future__, logging, notion_client, substrate.sockets.envelopes, substrate.sockets.protocols
### `adapters/notion/integration/manifest.py`
- Lines: 125. Doc: Notion integration manifest — declares sockets, signals, capabilities, signal sources.
- Classes: -
- Functions: load_signal_sources
- Imports: .auth, __future__, os, substrate.governance.risk_classes, substrate.sockets.protocols, substrate.types
### `adapters/notion/integration/outcomes.py`
- Lines: 140. Doc: Notion outcome receiver — writes pipeline outcomes back to Notion pages.
- Classes: NotionOutcomeReceiver
- Functions: -
- Imports: .correlation, .manifest, __future__, logging, notion_client, substrate.sockets.envelopes, time, typing
### `adapters/notion/integration/poller.py`
- Lines: 214. Doc: Notion poller — background thread that polls databases for changes.
- Classes: NotionPoller
- Functions: -
- Imports: __future__, adapters.notion.integration.correlation, adapters.notion.integration.signals, adapters.notion.integration.watermarks, logging, notion_client, substrate.governance.risk_classes, substrate.sockets.envelopes
### `adapters/notion/integration/signals.py`
- Lines: 104. Doc: Notion signal emitter — builds SignalEnvelopes from polled Notion pages.
- Classes: NotionSignalEmitter
- Functions: _extract_title, _extract_properties
- Imports: .manifest, __future__, logging, substrate.sockets.envelopes, substrate.sockets.protocols, substrate.types, typing, uuid
### `adapters/notion/integration/transforms.py`
- Lines: 107. Doc: Notion API ↔ UMH payload translations.
- Classes: -
- Functions: build_create_page_payload, extract_create_page_result, build_update_page_payload, extract_update_page_result, build_append_block_payload, extract_append_block_result, build_query_database_payload, extract_query_database_result
- Imports: __future__, typing
### `adapters/notion/integration/watermarks.py`
- Lines: 72. Doc: Watermark persistence — JSONL append-log for per-database poll high-water marks.
- Classes: WatermarkStore
- Functions: _default_watermark
- Imports: __future__, datetime, json, logging, pathlib, threading, typing
### `adapters/notion/notion_publisher.py`
- Lines: 486. Doc: EOS Notion Publisher — canonical pattern for writing EOS content to Notion.
- Classes: NotionPublisher
- Functions: _get_db_id, _api_call, _page_url, _heading, _paragraph, _divider, _bulleted, _create_page, _find_page_by_title, _brief_blocks, get_publisher
- Imports: datetime, dotenv, json, logging, os, typing, zoneinfo
### `adapters/notion/notion_sync.py`
- Lines: 470. Doc: Notion Sync — EOS runtime write layer.
- Classes: -
- Functions: get_db_id, _title, _text, _select, _date, _number, _checkbox, _create_page, _update_page, write_task, update_task_status, write_pipeline_entry
- Imports: datetime, dotenv, json, logging, os, requests
### `adapters/protocol.py`
- Lines: 20. Doc: -
- Classes: Adapter
- Functions: -
- Imports: __future__, substrate.types, typing, uuid
### `adapters/scrapling/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/scrapling/scrapling_connector.py`
- Lines: 142. Doc: ScraplingConnector — stealth HTTP fetching for EOS agents.
- Classes: ScraplingConnector
- Functions: -
- Imports: urllib.parse
### `adapters/shannon/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `adapters/shannon/shannon_connector.py`
- Lines: 266. Doc: ShannonConnector — AI penetration testing via KeygraphHQ/Shannon.
- Classes: ShannonConnector
- Functions: _validate_url, _validate_path, _validate_name, _in_cooldown, _trip_cooldown
- Imports: __future__, logging, os, pathlib, re, shlex, subprocess, substrate.execution.cpu_gate
### `adapters/tool_adapters/__init__.py`
- Lines: 16. Doc: Tool adapters — governed access to external systems (filesystem, shell, git, tmux).
- Classes: -
- Functions: -
- Imports: adapters.tool_adapters.base, adapters.tool_adapters.filesystem, adapters.tool_adapters.git, adapters.tool_adapters.shell, adapters.tool_adapters.tmux
### `adapters/tool_adapters/base.py`
- Lines: 51. Doc: Base adapter — shared interface and deny-rule machinery.
- Classes: BaseAdapter
- Functions: -
- Imports: __future__, abc, re, substrate.governance.risk_classes, typing
### `adapters/tool_adapters/filesystem.py`
- Lines: 162. Doc: Filesystem adapter — governed read/write/list/stat operations.
- Classes: FilesystemAdapter
- Functions: -
- Imports: __future__, adapters.tool_adapters.base, os, pathlib, re, substrate.governance.risk_classes, typing
### `adapters/tool_adapters/git.py`
- Lines: 127. Doc: Git adapter — governed git operations. Read-only by default.
- Classes: GitAdapter
- Functions: -
- Imports: __future__, adapters.tool_adapters.base, re, subprocess, substrate.execution.cpu_gate, substrate.governance.risk_classes, typing
### `adapters/tool_adapters/shell.py`
- Lines: 154. Doc: Shell adapter — governed command execution with destructive-command blocking.
- Classes: ShellAdapter
- Functions: -
- Imports: __future__, adapters.tool_adapters.base, re, subprocess, substrate.execution.cpu_gate, substrate.governance.risk_classes, typing
### `adapters/tool_adapters/tmux.py`
- Lines: 139. Doc: Tmux adapter — governed session inspection. No killing by default.
- Classes: TmuxAdapter
- Functions: -
- Imports: __future__, adapters.tool_adapters.base, re, subprocess, substrate.execution.cpu_gate, substrate.governance.risk_classes, typing
### `cockpit/tests/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `nodes/__init__.py`
- Lines: 2. Doc: Distributed execution nodes — Windows, Linux, container environments.
- Classes: -
- Functions: -
- Imports: -
### `nodes/distribution/__init__.py`
- Lines: 2. Doc: Task distribution layer — work distribution and first-boot handshake.
- Classes: -
- Functions: -
- Imports: -
### `nodes/distribution/distributor.py`
- Lines: 357. Doc: Distribution Layer — bridges channels to the execution pipeline.
- Classes: ChannelRouterProtocol, _NullRouter, MultiChannelRouter, DistributionEvent, DistributionStats, DistributionLayer
- Functions: -
- Imports: __future__, dataclasses, datetime, logging, typing, uuid
### `nodes/distribution/first_boot.py`
- Lines: 158. Doc: First Boot — detects whether the system needs onboarding.
- Classes: EnvironmentProfile, FirstBootStatus
- Functions: detect_environment, check_first_boot, mark_first_boot_complete, load_onboarding_result
- Imports: __future__, dataclasses, datetime, json, logging, os, pathlib, typing
### `nodes/environments/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `nodes/environments/bootstrap_plan.py`
- Lines: 232. Doc: Bootstrap plan for the Environment Bridge.
- Classes: BootstrapStepStatus, BootstrapStep, BootstrapPlan
- Functions: build_local_worker_bootstrap_plan, build_windows_task_scheduler_bootstrap_plan, build_tmux_local_worker_bootstrap_plan, bootstrap_plan_requires_manual_once, summarize_bootstrap_plan
- Imports: __future__, dataclasses, enum, os, typing
### `nodes/environments/bootstrap_status.py`
- Lines: 145. Doc: Bootstrap status checker for the Environment Bridge.
- Classes: BootstrapCheckStatus, BootstrapStatusReport
- Functions: check_vps_bootstrap_readiness, bootstrap_status_blocks_dispatch, summarize_bootstrap_status
- Imports: .queue_paths, __future__, dataclasses, enum, pathlib, typing
### `nodes/environments/chrome_visible_launch.py`
- Lines: 247. Doc: Chrome visible launch gate for the Environment Bridge.
- Classes: ChromeLaunchMethod, MetadataEvidence, ChromeVisibleLaunchStatus, ChromeProcessSnapshot, ChromeVisibleLaunchProof
- Functions: required_chrome_executable_paths, is_allowed_chrome_launch_method, build_chrome_launch_command, parse_chrome_process_snapshot, classify_metadata_evidence, evaluate_visible_chrome_launch, apply_founder_visual_confirmation, parse_founder_visual_confirmation, visible_launch_proof_allows_next_gate
- Imports: __future__, dataclasses, enum, typing
### `nodes/environments/execution_binding_contracts.py`
- Lines: 343. Doc: Execution Binding Contracts for the Environment Bridge.
- Classes: EnvironmentType, ExecutionSurfaceType, ExecutionSurfaceRole, ApplicationLaunchMethod, TargetServiceFamily, CapabilityMutability, ProofLevel, EvidenceType
- Functions: build_w0_chrome_gws_binding
- Imports: __future__, dataclasses, enum, typing
### `nodes/environments/execution_binding_validator.py`
- Lines: 282. Doc: Execution Binding Validator for the Environment Bridge.
- Classes: BindingValidationResult
- Functions: validate_execution_binding, validate_execution_binding_dict, _validate_environment, _validate_execution_surfaces, _validate_application, _validate_target_services, _validate_capabilities, _validate_proof, _validate_cross_layer_rules
- Imports: .execution_binding_contracts, __future__, dataclasses, typing
### `nodes/environments/heartbeat.py`
- Lines: 138. Doc: Worker heartbeat for the Environment Bridge.
- Classes: WorkerHeartbeatStatus, WorkerHeartbeat
- Functions: build_worker_heartbeat, heartbeat_is_stale, write_heartbeat, read_heartbeat, summarize_heartbeat
- Imports: __future__, dataclasses, datetime, enum, json, pathlib, typing
### `nodes/environments/local_pull_protocol.py`
- Lines: 257. Doc: Local pull protocol for the Environment Bridge.
- Classes: LocalPullStatus, TransportStrategy, LocalPullCycleResult
- Functions: _now_iso, discover_remote_packets, copy_remote_packet_to_local, claim_local_packet, mark_packet_running, mark_packet_completed, mark_packet_failed, write_local_result, sync_local_results_to_remote, run_local_pull_cycle, _update_packet_status
- Imports: .work_packet, __future__, dataclasses, datetime, enum, json, pathlib, typing
### `nodes/environments/packet_validator.py`
- Lines: 275. Doc: Packet validator for the Environment Bridge.
- Classes: PacketValidationStatus, PacketValidationResult
- Functions: validate_work_packet, validate_w0_packet_dict, packet_has_required_governance, packet_has_required_proof, packet_contains_blocked_action_violation, packet_validator_blocks_execution, packet_requires_environment_adapter, packet_requires_human_approval_adapter, _check_cu_governance, packet_requires_mastery, packet_requires_worker_runtime, _check_routing_fields
- Imports: .execution_binding_validator, .work_packet, __future__, dataclasses, enum, substrate.control_plane.invariants.spine_coherence_validator, typing
### `nodes/environments/queue_paths.py`
- Lines: 105. Doc: Queue paths for the Environment Bridge.
- Classes: QueuePaths
- Functions: build_vps_queue_paths, build_local_queue_paths, ensure_queue_paths, queue_paths_are_valid, summarize_queue_paths
- Imports: __future__, dataclasses, os, pathlib, typing
### `nodes/environments/result_ingestion.py`
- Lines: 165. Doc: Result ingestion for the Environment Bridge.
- Classes: BridgeResultStatus, BridgeResult
- Functions: build_bridge_result, validate_bridge_result, result_satisfies_proof_requirements, result_has_governance_compliance, ingest_bridge_result, summarize_bridge_result
- Imports: .work_packet, __future__, dataclasses, enum, typing
### `nodes/environments/tmux_surface.py`
- Lines: 140. Doc: Tmux execution surface for the Environment Bridge.
- Classes: TmuxSurfaceStatus, TmuxSurface
- Functions: build_tmux_surface, tmux_command_is_allowed, build_tmux_send_command, tmux_surface_blocks_command, summarize_tmux_surface
- Imports: __future__, dataclasses, enum, os, typing
### `nodes/environments/vps_local_bridge.py`
- Lines: 145. Doc: VPS ↔ Local Worker bridge for the Environment Bridge.
- Classes: BridgeMode, VPSLocalBridgeStatus, VPSLocalBridge
- Functions: build_vps_local_bridge, evaluate_vps_local_bridge_status, bridge_can_dispatch_by_push, bridge_can_dispatch_by_pull, bridge_requires_manual_bootstrap, summarize_vps_local_bridge
- Imports: .heartbeat, .queue_paths, __future__, dataclasses, enum, typing
### `nodes/environments/w0_packet_builder.py`
- Lines: 269. Doc: W0-001 packet builder for the Environment Bridge.
- Classes: -
- Functions: _build_w0_001_coherence_envelope, build_w0_001_packet, w0_001_packet_has_required_routing, w0_001_packet_blocks_playwright
- Imports: .execution_binding_contracts, .work_packet, __future__, datetime, substrate.control_plane.invariants.spine_lineage_contracts, typing, uuid
### `nodes/environments/windows_desktop_adapter_contracts.py`
- Lines: 197. Doc: Windows Interactive Desktop Adapter Contracts.
- Classes: WindowsDesktopActionType, WindowsDesktopAdapterStatus, WindowsDesktopProofStatus, WindowsDesktopActionRequest, WindowsDesktopActionResult, WindowsDesktopProofArtifact, WindowsDesktopRelayPaths
- Functions: -
- Imports: __future__, dataclasses, enum, pathlib, typing
### `nodes/environments/windows_desktop_adapter_validator.py`
- Lines: 162. Doc: Windows Interactive Desktop Adapter Validator.
- Classes: AdapterValidationResult
- Functions: validate_desktop_action_request, validate_desktop_action_request_dict, _validate_open_url_request
- Imports: .windows_desktop_adapter_contracts, __future__, dataclasses, typing
### `nodes/environments/windows_desktop_request_builder.py`
- Lines: 434. Doc: Windows Interactive Desktop Request Builder.
- Classes: -
- Functions: build_w0_chrome_open_request, build_ping_request, build_w0_drive_safe_test_doc_request, build_w0_doc_extract_safe_test_doc_request, build_w0_full_live_ingestion_request, build_w0_doc_ingestion_candidate_request, build_w0_promote_safe_memory_candidate_request, build_w0_query_safe_memory_reference_request, build_w0_chrome_proof_request, build_w0_real_foreground_cu_ingestion_request, request_to_json
- Imports: .windows_desktop_adapter_contracts, __future__, datetime, typing, uuid
### `nodes/environments/work_packet.py`
- Lines: 207. Doc: Work Packet contract for the Environment Bridge.
- Classes: WorkPacketStatus, WorkPacketRiskLevel, WorkPacketExecutionEnvironment, WorkPacket
- Functions: build_work_packet, work_packet_requires_approval, work_packet_is_executable, work_packet_targets_local_gui, work_packet_blocks_if_unapproved, summarize_work_packet
- Imports: __future__, dataclasses, datetime, enum, typing
### `nodes/environments/workspace_probe.py`
- Lines: 233. Doc: Workspace Probe — subprocess-based discovery of active workspace state.
- Classes: WorkspaceProbe
- Functions: -
- Imports: __future__, json, logging, os, re, substrate.execution.cpu_gate, time, typing
### `nodes/windows/__init__.py`
- Lines: 2. Doc: Windows node — daemon service and desktop tray for UMH mesh.
- Classes: -
- Functions: -
- Imports: -
### `nodes/windows/kokoro_server.py`
- Lines: 124. Doc: Kokoro TTS Server — OpenAI-compatible API on Beast GPU.
- Classes: SpeechRequest
- Functions: lifespan, health, create_speech, list_voices
- Imports: __future__, contextlib, fastapi, fastapi.responses, io, logging, numpy, pydantic
### `nodes/windows/umh_desktop/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `nodes/windows/umh_desktop/tray.py`
- Lines: 198. Doc: umh-desktop — System tray companion for UMH node mesh.
- Classes: PipeClient
- Functions: _setup_logging, _on_workspace_change, run_tray, _run_tray_icon, _run_headless, main
- Imports: __future__, asyncio, json, logging, nodes.windows.umh_node.adapters.clipboard, nodes.windows.umh_node.adapters.desktop, nodes.windows.umh_node.config, nodes.windows.umh_node.workspace
### `nodes/windows/umh_node/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `nodes/windows/umh_node/adapters/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `nodes/windows/umh_node/adapters/broadcast.py`
- Lines: 182. Doc: Broadcast adapter — runs FFmpeg engine on the local node.
- Classes: BroadcastAdapter
- Functions: -
- Imports: __future__, adapters.broadcast.engine, adapters.broadcast.scene_model, asyncio, logging, os, sys, typing
### `nodes/windows/umh_node/adapters/camera.py`
- Lines: 1343. Doc: Camera adapter — webcam capture and PTZ control for Insta360 Link 2.
- Classes: CameraAdapter
- Functions: _default_presets
- Imports: __future__, base64, copy, json, logging, pathlib, queue, sys
### `nodes/windows/umh_node/adapters/clipboard.py`
- Lines: 32. Doc: Clipboard adapter — read/write system clipboard.
- Classes: ClipboardAdapter
- Functions: -
- Imports: __future__, logging, typing
### `nodes/windows/umh_node/adapters/container.py`
- Lines: 171. Doc: Container adapter — Docker container lifecycle and execution.
- Classes: ContainerAdapter
- Functions: -
- Imports: __future__, base64, json, logging, subprocess, typing
### `nodes/windows/umh_node/adapters/desktop.py`
- Lines: 125. Doc: Desktop adapter — GUI automation, window management, screenshots.
- Classes: DesktopAdapter
- Functions: -
- Imports: __future__, base64, io, logging, sys, typing
### `nodes/windows/umh_node/adapters/filesystem.py`
- Lines: 96. Doc: Filesystem adapter — read, write, list, move, delete files.
- Classes: FilesystemAdapter
- Functions: -
- Imports: __future__, logging, os, pathlib, shutil, typing
### `nodes/windows/umh_node/adapters/hermes.py`
- Lines: 423. Doc: Hermes adapter — wraps Hermes CLI on the Beast machine.
- Classes: HermesAdapter
- Functions: _is_error_leak, _redact_secrets
- Imports: __future__, logging, os, shutil, subprocess, sys, threading, time
### `nodes/windows/umh_node/adapters/iou_tracker.py`
- Lines: 263. Doc: IoU tracker — persistent object IDs across frames.
- Classes: Track, IoUTracker
- Functions: _iou, _center, _describe_position
- Imports: __future__, dataclasses, time, typing
### `nodes/windows/umh_node/adapters/object_detector.py`
- Lines: 377. Doc: Object detector — YOLOv8n inference on camera frames.
- Classes: ObjectDetector
- Functions: -
- Imports: __future__, json, logging, pathlib, sys, threading, time, typing
### `nodes/windows/umh_node/adapters/shell.py`
- Lines: 61. Doc: Shell adapter — executes commands on the local machine.
- Classes: ShellAdapter
- Functions: -
- Imports: __future__, logging, subprocess, sys, typing
### `nodes/windows/umh_node/adapters/vision_runtime.py`
- Lines: 266. Doc: Vision runtime — CV capability detection and tracker management on Beast.
- Classes: CVCapability, TrackerProcess, VisionRuntime
- Functions: detect_capabilities, map_capabilities_to_trackers
- Imports: __future__, dataclasses, logging, threading, time, typing
### `nodes/windows/umh_node/client.py`
- Lines: 522. Doc: WebSocket client — connects to the VPS node mesh server.
- Classes: NodeClient
- Functions: -
- Imports: __future__, asyncio, collections, concurrent.futures, json, logging, nodes.windows.umh_node.adapters.broadcast, nodes.windows.umh_node.adapters.camera
### `nodes/windows/umh_node/config.py`
- Lines: 137. Doc: Node daemon configuration — reads umh_node.toml and .env.
- Classes: CapabilityConfig, SignalsConfig, NodeConfig
- Functions: _load_env, load_node_config
- Imports: __future__, dataclasses, os, pathlib, sys, typing
### `nodes/windows/umh_node/governance.py`
- Lines: 65. Doc: Node-side governance — validates capability requests against local policy.
- Classes: -
- Functions: _risk_level, validate_request
- Imports: __future__, logging, nodes.windows.umh_node.config, typing
### `nodes/windows/umh_node/launcher.py`
- Lines: 11. Doc: Session 1 launcher — starts UMH node daemon in the interactive desktop session.
- Classes: -
- Functions: -
- Imports: nodes.windows.umh_node.service, sys
### `nodes/windows/umh_node/metrics.py`
- Lines: 94. Doc: System metrics collector — CPU, memory, disk, battery, network, GPU.
- Classes: -
- Functions: _collect_gpu, collect_metrics
- Imports: __future__, logging, platform, psutil, subprocess, typing
### `nodes/windows/umh_node/service.py`
- Lines: 142. Doc: umh-node-service — Windows Service entry point.
- Classes: -
- Functions: _setup_logging, run_foreground, main
- Imports: __future__, asyncio, logging, nodes.windows.umh_node.client, nodes.windows.umh_node.config, pathlib, signal, sys
### `nodes/windows/umh_node/workspace.py`
- Lines: 350. Doc: Workspace awareness — tracks active window and full screen state.
- Classes: WorkspaceMonitor
- Functions: get_active_window, _classify_app, _get_window_pid, _get_process_name, _collect_monitors, _collect_windows, _detect_editor_context, _detect_browser_tabs, _detect_terminal_sessions, _get_focused_window_id, collect_workstation_state, _state_hash
- Imports: __future__, hashlib, json, logging, sys, threading, time, typing
### `projections/__init__.py`
- Lines: 2. Doc: Application projections — scoped views of UMH capability.
- Classes: -
- Functions: -
- Imports: -
### `projections/creatoros/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `projections/creatoros/integration/__init__.py`
- Lines: 2. Doc: CreatorOS integration — creator platform, direct Postgres polling.
- Classes: -
- Functions: -
- Imports: -
### `projections/creatoros/integration/correlation.py`
- Lines: 45. Doc: Thread-safe in-memory correlation map for CreatorOS outcome writeback targeting.
- Classes: CreatorOSWritebackTarget, CreatorOSCorrelationMap
- Functions: -
- Imports: __future__, dataclasses, threading, uuid
### `projections/creatoros/integration/handlers.py`
- Lines: 151. Doc: CreatorOS capability handler — implements CapabilityHandler Protocol.
- Classes: CreatorOSCapabilityHandler
- Functions: -
- Imports: .manifest, .tables, __future__, logging, psycopg2, substrate.types, time, typing
### `projections/creatoros/integration/manifest.py`
- Lines: 140. Doc: CreatorOS integration manifest — declares sockets, signals, capabilities, config.
- Classes: -
- Functions: load_creatoros_config
- Imports: __future__, logging, os, substrate.types
### `projections/creatoros/integration/outcomes.py`
- Lines: 181. Doc: CreatorOS outcome receiver — writes pipeline outcomes back to CreatorOS Postgres.
- Classes: CreatorOSOutcomeReceiver
- Functions: _build_audit_payload
- Imports: .correlation, .manifest, .tables, __future__, logging, psycopg2, substrate.types, typing
### `projections/creatoros/integration/signals.py`
- Lines: 147. Doc: CreatorOS signal emitter — builds SignalEnvelopes from polled CreatorOS database rows.
- Classes: CreatorOSSignalEmitter
- Functions: -
- Imports: .correlation, .manifest, .tables, __future__, logging, substrate.types, uuid
### `projections/creatoros/integration/tables.py`
- Lines: 440. Doc: Typed query helpers for CreatorOS database tables.
- Classes: PostRow, ProductRow, RevenueRow, StoryRow
- Functions: fetch_user_ids, fetch_posts_since, fetch_products_since, fetch_revenue_since, fetch_stories_since, _require_str, _require_int, insert_post, insert_product, insert_revenue, outcome_severity, update_umh_status
- Imports: __future__, dataclasses, datetime, logging, psycopg2, psycopg2.extras, typing
### `projections/eos/__init__.py`
- Lines: 93. Doc: EOS projection — EntrepreneurOS department agents registered on the substrate.
- Classes: -
- Functions: register_eos_agents
- Imports: __future__, substrate.types, typing
### `projections/eos/agents/__init__.py`
- Lines: 44. Doc: EOS department agents — one per department in the ARCHITECTURE.md hierarchy.
- Classes: -
- Functions: -
- Imports: projections.eos.agents.ceo, projections.eos.agents.customer_success, projections.eos.agents.engineering, projections.eos.agents.finance, projections.eos.agents.hr, projections.eos.agents.legal, projections.eos.agents.marketing, projections.eos.agents.operations
### `projections/eos/agents/base.py`
- Lines: 199. Doc: Base department agent with skill execution, permission tiers, and governance integration.
- Classes: SkillResult, AgentSkill, DepartmentAgent
- Functions: -
- Imports: __future__, asyncio, dataclasses, logging, substrate.types, typing
### `projections/eos/agents/ceo.py`
- Lines: 213. Doc: EOS CEO Agent — strategic decision making for entrepreneur operations.
- Classes: CEOAgent
- Functions: register_ceo_agent
- Imports: __future__, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/agents/customer_success.py`
- Lines: 284. Doc: EOS Customer Success Agent — retention, satisfaction, support routing.
- Classes: CustomerSuccessAgent
- Functions: register_customer_success_agent
- Imports: __future__, datetime, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/agents/engineering.py`
- Lines: 220. Doc: EOS Engineering Agent — technical execution, architecture, deployment.
- Classes: EngineeringAgent
- Functions: register_engineering_agent
- Imports: __future__, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/agents/finance.py`
- Lines: 237. Doc: EOS Finance Agent — revenue tracking, expense management, financial forecasting.
- Classes: FinanceAgent
- Functions: register_finance_agent
- Imports: __future__, datetime, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/agents/hr.py`
- Lines: 208. Doc: EOS HR Agent — hiring pipeline, team management, onboarding.
- Classes: HRAgent
- Functions: register_hr_agent
- Imports: __future__, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/agents/legal.py`
- Lines: 270. Doc: EOS Legal Agent — contract review, compliance tracking, entity management.
- Classes: LegalAgent
- Functions: register_legal_agent
- Imports: __future__, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/agents/marketing.py`
- Lines: 214. Doc: EOS Marketing Agent — content strategy and brand execution.
- Classes: MarketingAgent
- Functions: register_marketing_agent
- Imports: __future__, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/agents/operations.py`
- Lines: 244. Doc: EOS Operations Agent — workflow optimization, process automation, system health.
- Classes: OperationsAgent
- Functions: register_operations_agent
- Imports: __future__, projections.eos.agents.base, subprocess, substrate, substrate.types, typing
### `projections/eos/agents/product.py`
- Lines: 247. Doc: EOS Product Agent — roadmap management, feature prioritization, user feedback.
- Classes: ProductAgent
- Functions: register_product_agent
- Imports: __future__, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/agents/sales.py`
- Lines: 170. Doc: EOS Sales Agent — pipeline management and outreach execution.
- Classes: SalesAgent
- Functions: register_sales_agent
- Imports: __future__, projections.eos.agents.base, substrate, substrate.types, typing
### `projections/eos/entities.py`
- Lines: 880. Doc: EOS entity definitions — full entity hierarchy.
- Classes: -
- Functions: default_departments, default_roles, default_company, default_portfolio, default_user, default_workflows, get_skills_for_department, get_department_for_skill, default_dashboards
- Imports: __future__, substrate.types
### `projections/eos/integration/__init__.py`
- Lines: 2. Doc: EOS (EntrepreneurOS) integration — direct Postgres polling, multi-org.
- Classes: -
- Functions: -
- Imports: -
### `projections/eos/integration/correlation.py`
- Lines: 42. Doc: Thread-safe in-memory correlation map for EOS outcome writeback targeting.
- Classes: EOSWritebackTarget, EOSCorrelationMap
- Functions: -
- Imports: __future__, dataclasses, threading, uuid
### `projections/eos/integration/handlers.py`
- Lines: 158. Doc: EOS capability handler — implements CapabilityHandler Protocol.
- Classes: EOSCapabilityHandler
- Functions: -
- Imports: .manifest, .tables, __future__, logging, psycopg2, substrate.types, time, typing
### `projections/eos/integration/manifest.py`
- Lines: 157. Doc: EOS integration manifest — declares sockets, signals, capabilities, config.
- Classes: -
- Functions: load_eos_config
- Imports: __future__, logging, os, substrate.types
### `projections/eos/integration/outcomes.py`
- Lines: 183. Doc: EOS outcome receiver — writes pipeline outcomes back to EOS Postgres.
- Classes: EOSOutcomeReceiver
- Functions: _build_audit_payload
- Imports: .correlation, .manifest, .tables, __future__, logging, psycopg2, substrate.types, typing
### `projections/eos/integration/poller.py`
- Lines: 257. Doc: EOS poller — background thread that polls EOS Postgres tables for new rows.
- Classes: EOSPoller
- Functions: -
- Imports: .correlation, .signals, .tables, __future__, adapters.notion.integration.watermarks, logging, psycopg2, substrate.types
### `projections/eos/integration/signals.py`
- Lines: 158. Doc: EOS signal emitter — builds SignalEnvelopes from polled EOS database rows.
- Classes: EOSSignalEmitter
- Functions: -
- Imports: .correlation, .manifest, .tables, __future__, logging, substrate.types, typing, uuid
### `projections/eos/integration/tables.py`
- Lines: 583. Doc: Typed query helpers for EOS database tables.
- Classes: CrmContactRow, CrmDealRow, CrmActivityRow, TaskRow, AgentActionRow
- Functions: fetch_user_ids, fetch_contacts_since, fetch_deals_since, fetch_activities_since, fetch_tasks_since, _require_str, insert_contact, insert_deal, update_deal_stage, insert_activity, outcome_severity, update_umh_status
- Imports: __future__, dataclasses, datetime, decimal, logging, psycopg2, psycopg2.extras, typing
### `projections/eos/views/__init__.py`
- Lines: 8. Doc: EOS views — project substrate data into entrepreneur-facing dashboards.
- Classes: -
- Functions: -
- Imports: projections.eos.views.activity, projections.eos.views.kpis, projections.eos.views.pipeline
### `projections/eos/views/activity.py`
- Lines: 92. Doc: Activity view — projects recent system activity into a founder-facing feed.
- Classes: ActivityEntry, ActivityFeed, ActivityView
- Functions: -
- Imports: __future__, dataclasses, typing
### `projections/eos/views/kpis.py`
- Lines: 146. Doc: KPI view — projects business metrics into founder-facing KPI cards.
- Classes: KPICard, KPIDashboard, KPIView
- Functions: -
- Imports: __future__, dataclasses, typing
### `projections/eos/views/pipeline.py`
- Lines: 102. Doc: Pipeline view — projects CRM/sales data into a founder-facing pipeline.
- Classes: PipelineStage, PipelineSnapshot, PipelineView
- Functions: get_pipeline_data
- Imports: __future__, dataclasses, typing
### `projections/eos/workflows/__init__.py`
- Lines: 8. Doc: EOS workflows — automated sequences triggered by signals.
- Classes: -
- Functions: -
- Imports: projections.eos.workflows.content, projections.eos.workflows.followup, projections.eos.workflows.outreach
### `projections/eos/workflows/content.py`
- Lines: 101. Doc: Content calendar workflow — schedule and track content across channels.
- Classes: ContentPiece, ContentCalendar, ContentCalendarWorkflow
- Functions: -
- Imports: __future__, dataclasses, datetime, typing
### `projections/eos/workflows/followup.py`
- Lines: 94. Doc: Follow-up workflow — automated follow-up on stale conversations.
- Classes: FollowUpAction, FollowUpWorkflow
- Functions: -
- Imports: __future__, dataclasses, datetime, typing
### `projections/eos/workflows/outreach.py`
- Lines: 115. Doc: Outreach workflow — automated prospect outreach sequence.
- Classes: OutreachStep, OutreachResult, OutreachWorkflow
- Functions: -
- Imports: __future__, dataclasses, typing
### `projections/lyfeos/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `projections/lyfeos/integration/__init__.py`
- Lines: 2. Doc: LyfeOS integration — life optimization platform, direct Postgres polling.
- Classes: -
- Functions: -
- Imports: -
### `projections/lyfeos/integration/correlation.py`
- Lines: 42. Doc: Thread-safe in-memory correlation map for LyfeOS outcome writeback targeting.
- Classes: LyfeOSWritebackTarget, LyfeOSCorrelationMap
- Functions: -
- Imports: __future__, dataclasses, threading, uuid
### `projections/lyfeos/integration/handlers.py`
- Lines: 152. Doc: LyfeOS capability handler — implements CapabilityHandler Protocol.
- Classes: LyfeOSCapabilityHandler
- Functions: -
- Imports: .manifest, .tables, __future__, logging, psycopg2, substrate.types, time, typing
### `projections/lyfeos/integration/manifest.py`
- Lines: 143. Doc: LyfeOS integration manifest — declares sockets, signals, capabilities, config.
- Classes: -
- Functions: load_lyfeos_config
- Imports: __future__, logging, os, substrate.types
### `projections/lyfeos/integration/outcomes.py`
- Lines: 181. Doc: LyfeOS outcome receiver — writes pipeline outcomes back to LyfeOS Postgres.
- Classes: LyfeOSOutcomeReceiver
- Functions: _build_audit_payload
- Imports: .correlation, .manifest, .tables, __future__, logging, psycopg2, substrate.types, typing
### `projections/lyfeos/integration/signals.py`
- Lines: 167. Doc: LyfeOS signal emitter — builds SignalEnvelopes from polled LyfeOS database rows.
- Classes: LyfeOSSignalEmitter
- Functions: -
- Imports: .correlation, .manifest, .tables, __future__, logging, substrate.types, typing, uuid
### `projections/lyfeos/integration/tables.py`
- Lines: 504. Doc: Typed query helpers for LyfeOS database tables.
- Classes: QuestRow, UserStatsRow, DailyLogRow, VisionGoalRow
- Functions: fetch_user_ids, fetch_quests_since, fetch_stats_for_user, fetch_daily_logs_since, fetch_vision_goals_since, _require_str, _require_int, insert_quest, update_quest, insert_daily_log, outcome_severity, update_umh_status
- Imports: __future__, dataclasses, datetime, logging, psycopg2, psycopg2.extras, typing
### `scripts/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `scripts/_tme_common.py`
- Lines: 237. Doc: Shared helpers for Tool Mastery Engine system scripts.
- Classes: SkillRecord
- Functions: _split_frontmatter, load_skill, all_skill_slugs, load_all_skills, section_present, days_since, freshness_window, eprint
- Imports: __future__, dataclasses, datetime, os, pathlib, sys, typing, yaml
### `scripts/agent_task_executor.py`
- Lines: 340. Doc: Agent Task Executor — polls the tasks table for
- Classes: -
- Functions: load_soul_doc, execute_agent_task, requires_approval, run_executor
- Imports: asyncio, datetime, discord, dotenv, os, sys, zoneinfo
### `scripts/auto_report_dispatch.py`
- Lines: 166. Doc: Stop hook: auto-dispatch a report to cockpit chat and Discord
- Classes: -
- Functions: _detect_git_dir, _git, _recent_session_commits, _extract_metadata, _find_audit_file, dispatch, main
- Imports: __future__, json, os, subprocess, sys, time
### `scripts/bis_context.py`
- Lines: 88. Doc: BIS context injector — prints active venture context from VENTURES_JSON.
- Classes: -
- Functions: get_ventures, get_active_venture, main
- Imports: argparse, dotenv, json, os, sys
### `scripts/browser_gate_collector.py`
- Lines: 637. Doc: Browser Gate Collector — runs ON Beast with real display.
- Classes: -
- Functions: _get_auth_state_path, _ensure_auth, collect_log_layer, collect_viewport_evidence, merge_viewport_evidence, run_collection, main
- Imports: argparse, json, os, subprocess, sys, time, urllib.request
### `scripts/build_notion_databases.py`
- Lines: 117. Doc: Create the 9 databases that failed in the first build pass.
- Classes: -
- Functions: create_database
- Imports: dotenv, notion_client, os, sys
### `scripts/build_notion_workspace.py`
- Lines: 714. Doc: Build EOS Notion Workspace
- Classes: -
- Functions: create_page, create_database, text_block, heading_block, divider_block, callout_block
- Imports: dotenv, notion_client, os, sys
### `scripts/build_palace.py`
- Lines: 485. Doc: build_palace.py — Generates the EOS memory palace from the graph.
- Classes: -
- Functions: _wikilink_for_file, score_file, select_loci, render_room, render_wing, render_index, _graph_freshness, _render_candidate_room, _load_overlay_clusters, build, main
- Imports: __future__, argparse, datetime, json, os, pathlib, scripts.query_graph, sys
### `scripts/build_skill_graph.py`
- Lines: 221. Doc: build_skill_graph.py — Tool Mastery Engine skill dependency graph.
- Classes: -
- Functions: _tokens_for, _find_refs, build_graph, render_markdown, main
- Imports: __future__, argparse, collections, json, os, pathlib, re, scripts._tme_common
### `scripts/calendar_invite_handler.py`
- Lines: 349. Doc: Calendar Invite Handler — polls for pending invites every 15 mins.
- Classes: -
- Functions: load_state, save_state, get_pending_invites, _deterministic_assess, assess_invite, respond_to_invite, process_invites
- Imports: asyncio, datetime, discord, dotenv, json, os, re, sys
### `scripts/call_prep.py`
- Lines: 443. Doc: Call Prep — runs every 15 minutes via cron.
- Classes: -
- Functions: get_upcoming_calls, build_prep_brief, post_to_discord, already_prepped, mark_prepped, main
- Imports: datetime, dotenv, os, sys
### `scripts/check_cpu_gate.py`
- Lines: 151. Doc: Pre-commit gate: block raw subprocess usage in substrate/ and organism/.
- Classes: -
- Functions: get_staged_files, get_all_files, is_exempt, check_file, main
- Imports: __future__, pathlib, re, subprocess, sys
### `scripts/check_dependency_direction.py`
- Lines: 256. Doc: Pre-commit gate: blocks commits that violate UMH architecture dependency direction.
- Classes: -
- Functions: _get_staged_files, _get_all_files, _check_file, main
- Imports: __future__, pathlib, re, subprocess, sys
### `scripts/check_instance_leak.py`
- Lines: 222. Doc: Pre-commit gate: blocks commits that leak instance-specific values into substrate code.
- Classes: -
- Functions: _should_skip, _scan_file, _get_staged_files, _get_all_substrate_files, main
- Imports: __future__, pathlib, re, subprocess, sys
### `scripts/check_mesh_relay_firewall.py`
- Lines: 145. Doc: Check mesh relay firewall state for correctness and safety.
- Classes: -
- Functions: _run, main
- Imports: __future__, json, os, subprocess, sys
### `scripts/check_projection_leak.py`
- Lines: 228. Doc: Pre-commit gate: blocks projection-specific naming from substrate code.
- Classes: -
- Functions: _should_skip, _scan_file, _get_staged_files, _get_all_substrate_files, main
- Imports: __future__, pathlib, re, subprocess, sys
### `scripts/check_secret_patterns.py`
- Lines: 93. Doc: Pre-commit hook: reject commits containing secret patterns.
- Classes: -
- Functions: get_staged_files, check_file, main
- Imports: __future__, re, subprocess, sys
### `scripts/check_skill_staleness.py`
- Lines: 171. Doc: check_skill_staleness.py — Tool Mastery Engine staleness audit.
- Classes: StalenessRow
- Functions: _assess, _render_text, _render_markdown, main
- Imports: __future__, argparse, dataclasses, datetime, json, os, scripts._tme_common, sys
### `scripts/check_stop_condition.py`
- Lines: 96. Doc: Stop hook handler.
- Classes: -
- Functions: should_continue, main
- Imports: json, os, sys
### `scripts/check_type_divergence.py`
- Lines: 240. Doc: Pre-commit gate: blocks commits that create types diverging from canonical registry.
- Classes: -
- Functions: _file_to_module, _is_excluded, _extract_type_definitions, _get_staged_files, _get_all_python_files, _similar_names, check_files, main
- Imports: __future__, ast, pathlib, subprocess, substrate.canonical_types, sys
### `scripts/codebase_graph.py`
- Lines: 1216. Doc: codebase_graph.py — Persistent codebase knowledge graph for EOS.
- Classes: FunctionNode, ClassNode, FileNode, Edge, CodebaseGraph
- Functions: _rel, _module_name, _decorator_name, _extract_calls, _annotation_str, _is_entry_point, scan_file, scan_codebase, scan_non_python, export_json, _slug, _wikilink
- Imports: __future__, argparse, ast, collections, dataclasses, datetime, json, os
### `scripts/control_plane_run.py`
- Lines: 106. Doc: control_plane_run.py — run a shell command or script through the Control Plane.
- Classes: -
- Functions: main
- Imports: __future__, argparse, json, os, substrate.control_plane.actions.control_plane, sys
### `scripts/create_meetings_db.py`
- Lines: 68. Doc: -
- Classes: -
- Functions: -
- Imports: dotenv, os, requests
### `scripts/day_reminder.py`
- Lines: 117. Doc: Day Reminder — fires reminders throughout the day.
- Classes: -
- Functions: check_and_remind
- Imports: asyncio, datetime, discord, dotenv, json, os, sys, zoneinfo
### `scripts/dead_code_check.py`
- Lines: 59. Doc: Check for dead code in the substrate package.
- Classes: -
- Functions: main
- Imports: os, re, sys
### `scripts/deadline_monitor.py`
- Lines: 183. Doc: Deadline Monitor — checks tasks with due dates
- Classes: -
- Functions: check_deadlines, check_stale_tasks
- Imports: asyncio, datetime, discord, dotenv, json, os, sys, zoneinfo
### `scripts/decisions.py`
- Lines: 204. Doc: decisions.py — operator CLI for the Control Plane decision log.
- Classes: -
- Functions: _iter_log_files, _iter_records, _short, _truncate, cmd_list, cmd_show, cmd_for_action, main
- Imports: __future__, argparse, datetime, json, os, sys, typing
### `scripts/deferred.py`
- Lines: 350. Doc: deferred.py — operator CLI for the Control Plane deferred queue.
- Classes: -
- Functions: cmd_list, cmd_show, cmd_approve, cmd_drop, cmd_status, cmd_stale_check, cmd_prune, cmd_wake, _render_sentinel, cmd_idem_list, cmd_idem_show, cmd_idem_clear
- Imports: __future__, argparse, json, os, substrate.control_plane.actions, substrate.control_plane.actions.control_plane, substrate.control_plane.actions.deferred, substrate.control_plane.actions.deferred_status
### `scripts/detemplatize_skills.py`
- Lines: 206. Doc: Removes hardcoded venture data from all skills.
- Classes: -
- Functions: has_hardcoded, has_bis_injection, has_old_bis, replace_old_bis_block, replace_hardcoded_in_body, update_description, ensure_bis_block, process_skill, main
- Imports: os, re
### `scripts/discord_daily_clear.py`
- Lines: 35. Doc: -
- Classes: -
- Functions: clear_channels
- Imports: asyncio, discord, dotenv, os
### `scripts/discord_setup_channels.py`
- Lines: 197. Doc: Discord Builder/Product Channels Setup v1.
- Classes: -
- Functions: _log, _load_token, _run, main
- Imports: __future__, asyncio, json, os, pathlib, sys
### `scripts/emit_signal.py`
- Lines: 69. Doc: Emit an orchestrator signal from cron or the shell.
- Classes: -
- Functions: main
- Imports: __future__, argparse, json, os, substrate.control_plane.runtime.orchestrator.signals, sys
### `scripts/env_upsert.py`
- Lines: 105. Doc: Idempotent .env key upsert.
- Classes: -
- Functions: _parse_args, main
- Imports: __future__, os, pathlib, re, sys
### `scripts/eod_sync.py`
- Lines: 243. Doc: EOD Sync — 6pm PDT daily closing loop.
- Classes: -
- Functions: _get_todays_meetings, _get_todays_purchases, _get_todays_project_updates, _get_todays_decisions, build_eod_message, build_and_post_eod
- Imports: asyncio, datetime, discord, dotenv, json, os, sys, zoneinfo
### `scripts/eos_status.py`
- Lines: 162. Doc: EOS Operator Status — single inspectable surface.
- Classes: -
- Functions: section, docker_status, cron_recent_runs, active_locks, recent_provider_errors, main
- Imports: datetime, dotenv, observability.health.provider_health, os, pathlib, subprocess, sys
### `scripts/export_pipeline.py`
- Lines: 316. Doc: export_pipeline.py — Autonomous export-to-ingestion pipeline.
- Classes: -
- Functions: _load_processed, _save_processed, poll_and_process, _download_export, _route_and_ingest, _ingest_claude_export, _ingest_chatgpt_export, _ingest_instagram_export, main
- Imports: argparse, asyncio, datetime, dotenv, hashlib, json, logging, os
### `scripts/fire_export.py`
- Lines: 366. Doc: Fire a single browser export via Camoufox anti-detect browser.
- Classes: -
- Functions: run_export, _navigate_chatgpt_settings, _load_auth_flow, _get_export_url, _get_success_markers, _click_export_button, _try_tier_3
- Imports: asyncio, datetime, os, pathlib, sys, traceback
### `scripts/github_trinity_ingest.py`
- Lines: 230. Doc: github_trinity_ingest.py — Clone and ingest the three core repos via canonical pipeline.
- Classes: -
- Functions: clone_or_pull, collect_files, ingest_repo, main
- Imports: adapters.data_source_adapters.local_file_source, argparse, logging, os, pathlib, subprocess, substrate.governance.policy.authority_tier, substrate.understanding.perception.orchestrator
### `scripts/goals.py`
- Lines: 110. Doc: CLI entry points for goal management. Wraps runtime/goal_selector.py.
- Classes: -
- Functions: _sel, cmd_goals, cmd_goal_add, cmd_goal_activate, cmd_goal_defer, cmd_goal_cycle, cmd_goal_explain
- Imports: json, os, substrate.control_plane.goals.goal_selector, sys
### `scripts/gws_scanner_cron.py`
- Lines: 105. Doc: gws_scanner_cron.py — Thin cron wrapper for GWSDocumentScanner.
- Classes: -
- Functions: main
- Imports: argparse, datetime, dotenv, logging, os, sys
### `scripts/inbox_gps_afternoon.py`
- Lines: 30. Doc: Email GPS — 3pm afternoon inbox pass.
- Classes: -
- Functions: -
- Imports: adapters.google_workspace.email_gps, dotenv, os, substrate.state.context.context, sys, transports.discord.discord_utils
### `scripts/inbox_zero_init.py`
- Lines: 404. Doc: Inbox Zero Initialization — run ONCE on first DEX setup.
- Classes: -
- Functions: run_post_init_verification, verify_existing_labels
- Imports: adapters.google_workspace.email_gps, adapters.google_workspace.gws_connector, collections, dotenv, os, pathlib, substrate.state.context.context, sys
### `scripts/incremental_graph.py`
- Lines: 773. Doc: incremental_graph.py — Dirty-set incremental updates for the codebase graph.
- Classes: -
- Functions: _load_graph, _save_graph, _rel, _is_tracked, _classify, _file_imported_by, _compute_dirty_set, _node_ids_for_files, _strip_dirty, _strip_non_python, _scan_python_files, _scan_non_python_file
- Imports: __future__, argparse, collections, dataclasses, datetime, json, os, pathlib
### `scripts/ingest_conversations.py`
- Lines: 213. Doc: Batch ingest conversation exports into UMH canonical memory store.
- Classes: -
- Functions: _get_orchestrator, _scan_export_dir, ingest_service, main
- Imports: __future__, adapters.data_source_adapters.conversation_source, adapters.data_source_adapters.parsers.chatgpt_parser, adapters.data_source_adapters.parsers.claude_parser, argparse, datetime, json, logging
### `scripts/ingest_github_repos.py`
- Lines: 219. Doc: Batch ingest GitHub repos into UMH canonical memory store.
- Classes: -
- Functions: load_config, load_sync_state, save_sync_state, get_repos, ingest_repo, _append_log, main
- Imports: __future__, adapters.data_source_adapters.github_source, argparse, datetime, json, logging, os, pathlib
### `scripts/loop_runner.py`
- Lines: 203. Doc: Loop runner CLI — start, stop, and query persistent loops.
- Classes: -
- Functions: _init_registry, cmd_status, cmd_start, cmd_stop, cmd_run_once, cmd_run_forever, cmd_add, cmd_remove, cmd_stages, main
- Imports: __future__, argparse, json, os, signal, substrate.execution.loop, substrate.execution.loop.persistent_loop, sys
### `scripts/measure_phase8_batch.py`
- Lines: 340. Doc: Phase 8 batch measurement — full re-extraction.
- Classes: ToolResult
- Functions: find_latest_artifact, _load_raw_captures_from_disk, re_extract_patterns, measure_tool, main
- Imports: dataclasses, json, os, pathlib, substrate.composition.mastery.authoring.draft, substrate.composition.mastery.authoring.loader, substrate.composition.mastery.authoring.mapping, substrate.composition.mastery.research.artifact
### `scripts/memory_continuous_sync.py`
- Lines: 133. Doc: Continuous memory synchronization.
- Classes: -
- Functions: sweep_promoted_to_canonical, print_stats, main
- Imports: json, os, pathlib, substrate.memory.auto_reconciler, substrate.memory.candidate_generator, substrate.memory.claude_bridge, substrate.memory.promoter, substrate.state.memory.contracts.canonical_memory_store_v1
### `scripts/memory_instant_sync.py`
- Lines: 115. Doc: Instant memory sync hook — fires on PostToolUse for Write/Edit.
- Classes: -
- Functions: parse_frontmatter
- Imports: hashlib, json, os, pathlib, re, sys
### `scripts/memory_watcher_daemon.py`
- Lines: 66. Doc: Memory Watcher Daemon — runs the substrate memory watcher.
- Classes: -
- Functions: main
- Imports: logging, os, signal, substrate.memory.watcher, sys, time
### `scripts/merge_graphs.py`
- Lines: 342. Doc: merge_graphs.py — Merge graphify_overlay.json into codebase_graph.json.
- Classes: -
- Functions: _load_json, _edge_key, _overlay_edge_to_primary, merge, _assemble_merged, _write_merged, _print_stats, main
- Imports: __future__, argparse, datetime, json, os, pathlib, sys, typing
### `scripts/meta_ide_browser_gate.py`
- Lines: 331. Doc: Meta IDE Browser Verification Gate — 4-layer × 3-pass.
- Classes: -
- Functions: collect_pass, evaluate_pass, main
- Imports: json, subprocess, sys, time
### `scripts/midday_checkin.py`
- Lines: 111. Doc: Mid-day check-in — runs at 12:30pm PDT.
- Classes: -
- Functions: midday_checkin
- Imports: asyncio, datetime, discord, dotenv, os, sys, zoneinfo
### `scripts/migrate_instance_leaks.py`
- Lines: 311. Doc: Bulk migration tool: mechanically replaces instance-specific values in substrate/ code.
- Classes: Replacement
- Functions: _load_instance_config, _scan_file, scan_all, report, main
- Imports: __future__, json, os, pathlib, re, sys
### `scripts/morning_intel.py`
- Lines: 200. Doc: Morning Intelligence Brief — runs at 5:45am PDT daily,
- Classes: -
- Functions: build_intel_brief
- Imports: asyncio, datetime, discord, dotenv, os, sys, zoneinfo
### `scripts/noshow_detector.py`
- Lines: 165. Doc: No-show detector — checks meetings that started 30+ min ago with no
- Classes: -
- Functions: detect_noshows
- Imports: asyncio, datetime, discord, dotenv, json, os, sys, zoneinfo
### `scripts/notion_cleanup.py`
- Lines: 569. Doc: Notion Cleanup — archives old scaffold databases
- Classes: -
- Functions: _get_page_title, get_all_dbs, get_child_page_titles, archive_db, ensure_dashboards_page, create_role_page, create_stub_page, run_cleanup
- Imports: dotenv, os, requests, sys
### `scripts/notion_outcome_sync.py`
- Lines: 198. Doc: Notion → Neon Outcome Sync
- Classes: -
- Functions: load_state, save_state, query_pipeline, extract_page_data, fire_outcome, run_sync
- Imports: datetime, dotenv, json, os, pathlib, requests, sys
### `scripts/notion_seed.py`
- Lines: 509. Doc: Notion Seed — populates initial rows in EOS Notion databases.
- Classes: -
- Functions: seed_portfolio, seed_roles, seed_tools, seed_goals, main
- Imports: adapters.notion.notion_sync, datetime, dotenv, os, requests, sys
### `scripts/notion_seed_all.py`
- Lines: 934. Doc: Notion Seed All — seeds Empyrean Creative, Personal Brand ventures
- Classes: -
- Functions: seed_empyrean, seed_personal_brand, seed_content_calendars, main
- Imports: adapters.notion.notion_sync, datetime, dotenv, os, sys
### `scripts/notion_setup.py`
- Lines: 1083. Doc: Notion Setup — creates the full per-venture primitive database
- Classes: -
- Functions: _to_env_key, _create_db, _get_all_dbs, _ensure_db, _get_existing_page_titles, _ensure_dashboards_page, _create_role_dashboard_page, main
- Imports: dotenv, json, os, requests, sys
### `scripts/notion_sync_poller.py`
- Lines: 44. Doc: Notion Sync Poller — runs every 15 minutes via cron.
- Classes: -
- Functions: run
- Imports: datetime, dotenv, os, sys, zoneinfo
### `scripts/notion_tasks_sync.py`
- Lines: 283. Doc: Notion Tasks → Neon Sync
- Classes: -
- Functions: load_state, save_state, query_database, extract_task, write_to_neon, push_status_to_notion, sync_neon_to_notion, run_sync
- Imports: datetime, dotenv, json, os, pathlib, requests, sys
### `scripts/oauth_grant_gmail.py`
- Lines: 152. Doc: One-shot OAuth grant for Gmail scope — run on Windows (needs browser).
- Classes: -
- Functions: _load_client_config, main
- Imports: __future__, asyncio, json, os, pathlib, sys, time, urllib.parse
### `scripts/orchestrator.py`
- Lines: 1125. Doc: orchestrator.py — Continuous, autonomous execution layer for EOS.
- Classes: TriggerType, JobStatus, Job, Verifier, ActivityLog, ExecutionQueue, SchedulerAgent, EventAgent
- Functions: _parse_hhmm, _graph_freshness_ok, build_default_jobs, _install_signal_handlers, _cmd_list, _cmd_status, _cmd_trigger, _cmd_start, main
- Imports: __future__, argparse, concurrent.futures, dataclasses, datetime, enum, json, os
### `scripts/orchestrator_loop.py`
- Lines: 75. Doc: Orchestrator loop runner.
- Classes: -
- Functions: main
- Imports: __future__, argparse, json, os, substrate.control_plane.runtime.orchestrator.loop, substrate.control_plane.runtime.orchestrator.orchestrator, substrate.control_plane.runtime.orchestrator.workflows, sys
### `scripts/orchestrator_status.py`
- Lines: 389. Doc: orchestrator_status.py — operator-friendly snapshot of the Control Plane.
- Classes: -
- Functions: _now, _age_seconds, _fmt_age, _today_execution_log, pending_signals_summary, deferred_summary, recent_workflows, recent_failures, loop_heartbeat, loop_activity, _hdr, render_text
- Imports: __future__, argparse, datetime, json, os, substrate.control_plane.actions.deferred, substrate.control_plane.actions.logging, substrate.control_plane.runtime.orchestrator.loop
### `scripts/permission_notify.py`
- Lines: 105. Doc: PermissionRequest hook.
- Classes: -
- Functions: is_safe, log_permission, main
- Imports: json, os, sys, time
### `scripts/phase75a_classifier.py`
- Lines: 281. Doc: Phase 75A — Auto-classify UMH modules by PRD domain and MVP status.
- Classes: -
- Functions: module_from_path, get_purpose, classify, get_domain, extract_imports, main
- Imports: ast, json, os, pathlib
### `scripts/phase75a_dep_scanner.py`
- Lines: 233. Doc: Phase 75A — AST-based dependency scanner for UMH.
- Classes: -
- Functions: find_python_files, module_from_path, extract_imports, normalize_to_package, find_cycles, detect_sensitive_imports, main
- Imports: ast, collections, json, os, pathlib
### `scripts/portfolio_brief.py`
- Lines: 128. Doc: Sunday Portfolio Brief — runs at 6am every Sunday.
- Classes: -
- Functions: post_to_notion, run_portfolio_brief
- Imports: asyncio, datetime, discord, dotenv, json, os, requests, sys
### `scripts/post_meeting_capture.py`
- Lines: 135. Doc: Post-meeting capture — polls for recently ended calendar events
- Classes: -
- Functions: load_state, save_state, check_and_prompt
- Imports: asyncio, datetime, discord, dotenv, json, os, sys, zoneinfo
### `scripts/pre_tool_use_log.py`
- Lines: 57. Doc: PreToolUse hook.
- Classes: -
- Functions: main
- Imports: json, os, sys, time
### `scripts/query_graph.py`
- Lines: 329. Doc: query_graph.py — Retrieval layer over the EOS codebase knowledge graph.
- Classes: GraphQuery
- Functions: _print_list, main
- Imports: __future__, argparse, collections, dataclasses, datetime, json, os, pathlib
### `scripts/query_skills.py`
- Lines: 215. Doc: query_skills.py — Tool Mastery Engine CLI registry.
- Classes: -
- Functions: _matches, cmd_search, cmd_show, _load_graph, cmd_deps, cmd_stale, cmd_unverified, cmd_domain, cmd_list, cmd_count, main
- Imports: __future__, argparse, datetime, json, os, pathlib, scripts._tme_common, scripts.check_skill_staleness
### `scripts/relationship_nurture.py`
- Lines: 128. Doc: Relationship nurturing — checks for contacts not heard from in 30+ days
- Classes: -
- Functions: check_relationships
- Imports: asyncio, datetime, discord, dotenv, os, sys, zoneinfo
### `scripts/router_claude_runtime_debug.py`
- Lines: 71. Doc: Router runtime debug helper — prints the actual, live state the router
- Classes: -
- Functions: main
- Imports: __future__, json, os, sys
### `scripts/run_continuity_validation.py`
- Lines: 387. Doc: Continuity engine end-to-end validation.
- Classes: -
- Functions: run
- Imports: __future__, json, os, pathlib, substrate.execution.runtime.substrate_continuity_engine_v1, sys
### `scripts/run_graphify.py`
- Lines: 527. Doc: run_graphify.py — Pluggable enrichment layer (Graphify adapter).
- Classes: -
- Functions: _probe_external, _run_external_binary, _run_external_module, _load_graph, _file_import_graph, _label_propagation, _clusters_from_labels, _tokenize_doc, _co_occurrence_edges, _cross_language_edges, _build_internal, _build_external
- Imports: __future__, argparse, collections, datetime, importlib.util, json, os, pathlib
### `scripts/run_reconciliation_ingestion.py`
- Lines: 212. Doc: Multi-document ingestion with reconciliation.
- Classes: -
- Functions: run
- Imports: __future__, adapters.adapter_engine.gws_scanner_bridge_v1, adapters.adapter_engine.substrate_candidate_gen_v1, adapters.adapter_engine.substrate_decomposer_v1, json, os, pathlib, substrate.state.memory.contracts.canonical_memory_reconciliation_engine_v1
### `scripts/run_reconciliation_query_validation.py`
- Lines: 171. Doc: Reconciliation query validation.
- Classes: -
- Functions: run
- Imports: __future__, json, os, pathlib, substrate.state.memory.contracts.canonical_memory_reconciliation_engine_v1, substrate.state.memory.contracts.canonical_memory_store_v1, sys
### `scripts/run_reconciliation_replay_validation.py`
- Lines: 129. Doc: Reconciliation replay validation.
- Classes: -
- Functions: run
- Imports: __future__, adapters.adapter_engine.gws_scanner_bridge_v1, adapters.adapter_engine.substrate_candidate_gen_v1, adapters.adapter_engine.substrate_decomposer_v1, json, os, pathlib, substrate.state.memory.contracts.canonical_memory_reconciliation_engine_v1
### `scripts/scheduled/morning_prep_cp.py`
- Lines: 85. Doc: morning_prep_cp.py — Control Plane wrapper for morning_prep.sh.
- Classes: -
- Functions: main
- Imports: __future__, argparse, datetime, os, substrate.control_plane.runtime.orchestrator.steps, sys
### `scripts/scheduled/nightly_consolidation_cp.py`
- Lines: 113. Doc: nightly_consolidation_cp.py — Control Plane wrapper for nightly_consolidation.sh.
- Classes: -
- Functions: main
- Imports: __future__, argparse, datetime, os, substrate.control_plane.runtime.orchestrator.steps, sys
### `scripts/scheduled/weekly_review_cp.py`
- Lines: 109. Doc: weekly_review_cp.py — Control Plane wrapper for weekly_review.sh.
- Classes: -
- Functions: _idempotency_key, main
- Imports: __future__, argparse, datetime, os, substrate.control_plane.runtime.orchestrator.steps, sys
### `scripts/seed_eos_watermarks_to_now.py`
- Lines: 66. Doc: Seed EOS watermarks to NOW — skip historical replay on next poller start.
- Classes: -
- Functions: main
- Imports: __future__, adapters.notion.integration.watermarks, datetime, dotenv, os, pathlib, projections.eos.integration.manifest, projections.eos.integration.tables
### `scripts/send_to_builder.py`
- Lines: 35. Doc: Send a file to the EOS Discord builder channel.
- Classes: -
- Functions: -
- Imports: dotenv, os, requests, sys
### `scripts/session_bootstrap.py`
- Lines: 188. Doc: session_bootstrap.py — Mandatory context load at session start.
- Classes: -
- Functions: _read, print_full, print_compact, check_freshness, register_organism_session, main
- Imports: __future__, argparse, json, os, pathlib, scripts.query_graph, sys
### `scripts/session_start_context.py`
- Lines: 232. Doc: SessionStart hook.
- Classes: -
- Functions: _timeout_handler, _acquire_lock, get_cc_version, check_version_change, get_pending_tasks, get_venture_stage, get_system_health_summary, main
- Imports: datetime, fcntl, os, signal, subprocess, sys, zoneinfo
### `scripts/shim_retirement_monitor.py`
- Lines: 273. Doc: Shim retirement readiness monitor.
- Classes: -
- Functions: scan_logs_for_eos_ai, _is_pre_migration_entry, check_docker_containers, check_crontab, check_shim_imports, check_process_imports, _load_baseline, _save_baseline, generate_report, main
- Imports: __future__, argparse, datetime, glob, json, os, subprocess, sys
### `scripts/subagent_start_context.py`
- Lines: 73. Doc: SubagentStart hook.
- Classes: -
- Functions: main
- Imports: json, os, sys
### `scripts/substrate_audio_loop_cli.py`
- Lines: 137. Doc: Bounded operator CLI for the local audio loop.
- Classes: -
- Functions: _dumps, cmd_report, cmd_report_node, cmd_inject_transcript, cmd_prime, build_parser, main
- Imports: __future__, argparse, json, os, sys
### `scripts/substrate_claude_session_cli.py`
- Lines: 172. Doc: Claude Code Session Bridge CLI.
- Classes: -
- Functions: _print_json, cmd_detect, cmd_list, cmd_status, cmd_ensure, cmd_send, cmd_capture, cmd_ask, _add_target, _add_session, main
- Imports: __future__, argparse, json, os, substrate.execution.bridge, sys
### `scripts/substrate_discord_voice_transport_cli.py`
- Lines: 239. Doc: Discord voice transport CLI — bounded operator interface to the
- Classes: _FakeVoiceClient
- Functions: _print_json, _transport, cmd_status, cmd_start, cmd_inject, cmd_end, cmd_report, cmd_attach_fake, cmd_detach, cmd_play, cmd_playback_status, _common_target
- Imports: __future__, argparse, json, os, sys
### `scripts/substrate_execution_trace_cli.py`
- Lines: 179. Doc: Operator CLI for EOS execution trace history.
- Classes: -
- Functions: _print_json, _history, cmd_latest, cmd_show, cmd_by_mode, cmd_by_session, cmd_compact, cmd_clear_history, cmd_by_provider, cmd_by_path, cmd_summary, build_parser
- Imports: __future__, argparse, collections, json, os, sys
### `scripts/substrate_local_listener.py`
- Lines: 105. Doc: Local listener CLI — emit a bounded activation trigger.
- Classes: -
- Functions: main
- Imports: __future__, argparse, json, os, substrate.execution.bridge.local_listener, sys
### `scripts/substrate_operator_cli.py`
- Lines: 230. Doc: Operator CLI for EOS substrate — Operator Interface Layer v1.
- Classes: -
- Functions: _print_json, _add_common, _build_parser, main
- Imports: __future__, argparse, json, os, substrate.execution.bridge, sys
### `scripts/substrate_voice_session_cli.py`
- Lines: 150. Doc: Bounded operator CLI for the voice session substrate.
- Classes: -
- Functions: _maybe_install_eos_responder, _print_session, cmd_start, cmd_say, cmd_switch, cmd_end, cmd_report, build_parser, main
- Imports: __future__, argparse, json, os, substrate.execution.bridge.voice_session, sys
### `scripts/substrate_wake_producer_cli.py`
- Lines: 111. Doc: Wake producer CLI — simulate wake-word / clap events and view history.
- Classes: -
- Functions: _emit, cmd_simulate_wake_word, cmd_simulate_clap, cmd_report, cmd_status, build_parser, main
- Imports: __future__, argparse, json, os, substrate.execution.bridge.wake_producer, sys
### `scripts/summarize_nodes.py`
- Lines: 151. Doc: summarize_nodes.py — Append-only one-line summaries for every graph node.
- Classes: -
- Functions: _one_line, build_summaries, _upsert, show, stats, main
- Imports: __future__, argparse, datetime, json, os, pathlib, re, sys
### `scripts/sync_skills_to_neon.py`
- Lines: 133. Doc: sync_skills_to_neon.py — Canonical Tool Mastery Engine → Neon sync.
- Classes: -
- Functions: _raw_text, _sync_one, main
- Imports: __future__, argparse, os, scripts._tme_common, substrate.state.context.context, substrate.state.stores.skill_store, sys
### `scripts/tme_quality_audit.py`
- Lines: 246. Doc: TME Quality Audit — checks content depth, not just structure.
- Classes: -
- Functions: audit_skill, main
- Imports: argparse, json, os, re, scripts._tme_common, sys
### `scripts/tme_staleness_sweep.py`
- Lines: 87. Doc: TME staleness sweep — summary-first report for hooks and cron.
- Classes: -
- Functions: main
- Imports: __future__, argparse, datetime, json, os, scripts._tme_common, sys
### `scripts/tool_mastery_author.py`
- Lines: 126. Doc: Tool Mastery author dispatcher.
- Classes: -
- Functions: _run, _consume_action, main
- Imports: __future__, argparse, json, os, pathlib, substrate.composition.mastery.authoring.agent, substrate.composition.mastery.authoring.models, sys
### `scripts/tool_mastery_manager.py`
- Lines: 217. Doc: Tool Mastery Manager — CLI.
- Classes: -
- Functions: _emit, cmd_ensure, cmd_status, cmd_scan, cmd_backlog, cmd_bootstrap, cmd_refresh_stale, main
- Imports: __future__, argparse, json, os, substrate.composition.mastery.management.backlog, substrate.composition.mastery.management.coverage, substrate.composition.mastery.management.ensure, substrate.composition.mastery.management.maintenance
### `scripts/tool_mastery_research_dispatcher.py`
- Lines: 313. Doc: Tool Mastery research dispatcher.
- Classes: -
- Functions: _plan_research, _plan_refresh, _plan_repair, _drain_author_queue, main
- Imports: __future__, argparse, json, os, pathlib, substrate.composition.mastery.management.coverage, substrate.composition.mastery.management.paths, sys
### `scripts/user_prompt_capture.py`
- Lines: 114. Doc: UserPromptSubmit hook: capture user messages into conversation files.
- Classes: -
- Functions: _read_payload, _build_header, main
- Imports: datetime, json, os, sys, typing
### `scripts/validate_w0_coherence_dry.py`
- Lines: 240. Doc: W0 Dry Validation with Coherence Envelope.
- Classes: -
- Functions: run_dry_validation, _write_report
- Imports: datetime, json, nodes.environments.execution_binding_validator, nodes.environments.packet_validator, nodes.environments.w0_packet_builder, os, pathlib, substrate.control_plane.invariants.coherence_gate
### `scripts/verify_completion_claim.py`
- Lines: 89. Doc: Completion Claim Verifier — runs at Stop hook.
- Classes: -
- Functions: get_file_count, main
- Imports: json, os, subprocess, sys
### `scripts/verify_deploy.py`
- Lines: 92. Doc: Standalone post-deploy verification script.
- Classes: -
- Functions: main
- Imports: __future__, argparse, json, substrate.organism.deploy_verification_worker, sys
### `scripts/verify_knowledge_system.py`
- Lines: 354. Doc: verify_knowledge_system.py — Acceptance check for the EOS cognition stack.
- Classes: CheckResult
- Functions: check_session_docs, check_data_artifacts, check_palace_structure, check_codebase_vault, check_graph_loads, check_freshness, check_parser_registry, check_query_cli, check_summaries_alignment, check_palace_alignment, check_claude_md_directives, run_all
- Imports: __future__, argparse, dataclasses, json, os, pathlib, subprocess, sys
### `scripts/verify_pr47_cadence_learning.py`
- Lines: 108. Doc: Phase 10.3F — Cadence post-production learning check.
- Classes: -
- Functions: main
- Imports: __future__, json, os, substrate.organism.autonomous_cadence, substrate.organism.candidate_supply_engine, sys, time
### `scripts/verify_pr47_production.py`
- Lines: 182. Doc: Phase 10.3D — Production merge verification for PR #47.
- Classes: -
- Functions: _capture_state_snapshot, main
- Imports: __future__, json, os, substrate.organism.production_merge_verifier, substrate.organism.production_truth_delta, substrate.organism.worktree_sandbox, sys, time
### `scripts/verify_pr47_reliability.py`
- Lines: 138. Doc: Phase 10.3E — Template + Agent Reliability Update verification.
- Classes: -
- Functions: main
- Imports: __future__, json, os, substrate.organism.template_registry, sys, time
### `scripts/verify_template_store.py`
- Lines: 50. Doc: Verify the runtime template store is populated and valid.
- Classes: -
- Functions: verify
- Imports: __future__, json, os, sys
### `scripts/verify_tool_skill.py`
- Lines: 193. Doc: verify_tool_skill.py — Tool Mastery Engine verifier / linter.
- Classes: VerifyResult
- Functions: _check, _render, _render_json, main
- Imports: __future__, argparse, dataclasses, json, os, pathlib, re, scripts._tme_common
### `scripts/waiting_on_checker.py`
- Lines: 94. Doc: WAITING_ON checker — scans emails in WAITING_ON folder
- Classes: -
- Functions: check_waiting_on
- Imports: asyncio, datetime, discord, dotenv, os, sys, zoneinfo
### `scripts/watch_graph.py`
- Lines: 527. Doc: watch_graph.py — Near real-time file watcher for the codebase graph.
- Classes: CodebaseEventHandler
- Functions: _now, _is_tracked_path, _append_perf, _run_overlay_chain, _process_batch, _debounce_loop, watch, once, main
- Imports: __future__, argparse, collections, datetime, json, os, pathlib, scripts.incremental_graph
### `scripts/week_architect.py`
- Lines: 134. Doc: Week Architect — Sunday 8pm PDT.
- Classes: -
- Functions: architect_week
- Imports: asyncio, datetime, discord, dotenv, os, sys, zoneinfo
### `scripts/weekly_review.py`
- Lines: 244. Doc: Weekly business review — Sunday 7pm PDT.
- Classes: -
- Functions: run_weekly_review
- Imports: asyncio, datetime, discord, dotenv, os, sys, zoneinfo
### `scripts/wiki_stop_hook.py`
- Lines: 170. Doc: Stop hook: capture real conversation content to session file.
- Classes: -
- Functions: _read_payload, _extract_assistant_text, _build_header, _build_entry, main
- Imports: datetime, json, os, sys, typing
### `scripts/workers/discord_approval_worker.py`
- Lines: 236. Doc: discord_approval_worker.py — tail notifications.jsonl, post to Discord.
- Classes: -
- Functions: _read_offset, _write_offset, _is_still_deferred, _format_discord_payload, _post_to_discord, _log, drain_once, main
- Imports: __future__, argparse, datetime, json, os, sys, time, urllib.request
### `services/auth_flows/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `services/auth_flows/chatgpt.py`
- Lines: 457. Doc: Scripted login for chatgpt.com — email-based auth flow.
- Classes: -
- Functions: login, _already_authenticated, _click_login_button, _fill_email, _submit_email, _detect_challenge_type, _handle_password_challenge, _handle_code_challenge, _wait_for_verification_code, _wait_for_magic_link, _confirm_authenticated, _screenshot
- Imports: __future__, dotenv, logging, os, pathlib, sys
### `services/auth_flows/claude.py`
- Lines: 211. Doc: Scripted login for claude.ai — email magic-link flow.
- Classes: -
- Functions: login, _already_authenticated, _click_continue_with_email, _fill_email, _detect_check_email_page, _wait_for_magic_link, _confirm_authenticated, _get_body_text
- Imports: __future__, dotenv, logging, os, pathlib, sys
### `services/bridge_health.py`
- Lines: 317. Doc: bridge_health.py — VPS-side watchdog for the Windows bridge.
- Classes: -
- Functions: _ssh_cmd, _check_health, _check_ssh, _start_bridge_via_ssh, _kill_bridge_via_ssh, _surface_error, _surface_setup_gate, ensure_bridge_live, main
- Imports: __future__, dotenv, logging, os, pathlib, requests, subprocess, substrate.execution.cpu_gate
### `services/browser_adapter.py`
- Lines: 99. Doc: browser_adapter.py — Camoufox browser wrapper for anti-detect automation.
- Classes: -
- Functions: launch_browser
- Imports: __future__, logging, os, pathlib
### `services/cc_webhook_receiver.py`
- Lines: 310. Doc: CC Reply Webhook Receiver — receives POSTs from the CC Stop hook and
- Classes: -
- Functions: _build_session_channel_map, _chunk_message, start_webhook_server
- Imports: __future__, aiohttp, dotenv, json, logging, os, pathlib, sys
### `services/cost_tracker.py`
- Lines: 415. Doc: -
- Classes: -
- Functions: _deep_copy_empty_day, load_log, save_log, _today_key, _month_key, sync_apify_balance, sync_and_update_apify_log, log_apify_runs, log_scraper_costs, log_copilot_costs, get_today_costs, get_monthly_costs
- Imports: datetime, dotenv, json, os
### `services/discord_bot.py`
- Lines: 1872. Doc: EntrepreneurOS Discord Bot — DEX conversational layer.
- Classes: SilenceDetectingSink, DiscordServerManager
- Functions: _handle_task_exception, transcribe_with_groq, _detect_day_command, _run_day_command, _format_day_result, _send_day_response, on_error, _build_request, _detect_pipeline_update, _run_gateway, handle_meeting_voice, start_meeting_mode
- Imports: asyncio, datetime, discord, discord.ext, discord.sinks, dotenv, importlib.util, json
### `services/discord_bot_commands.py`
- Lines: 2742. Doc: Discord bot commands — extracted from discord_bot.py.
- Classes: -
- Functions: register_commands
- Imports: __future__, asyncio, discord, discord.ext, os, pathlib, subprocess, substrate.execution.bridge.session_discord_bridge
### `services/discord_message_handlers.py`
- Lines: 1319. Doc: Discord message handlers — extracted from discord_bot.py.
- Classes: -
- Functions: _persist_and_push, init, get_pending_events, _bot, _ai_name, _detect_part, _assemble_parts, _memory_gateway, _handle_audio_attachment, _handle_image_attachment, _handle_buffer_done, _handle_buffer_start
- Imports: __future__, asyncio, datetime, discord, json, logging, os, pathlib
### `services/export_bridge_handler.py`
- Lines: 266. Doc: export_bridge_handler.py — Windows-side handler for fire_export bridge messages.
- Classes: -
- Functions: _get_powershell_path, _notify_vps_mfa, _run_export, handle_fire_export, handle_mfa_response, register_routes
- Imports: __future__, aiohttp, asyncio, json, logging, os, pathlib, subprocess
### `services/goal_api.py`
- Lines: 195. Doc: Goal API — REST endpoints for goal selection + focus management.
- Classes: -
- Functions: _selector, _goal_to_dict, list_goals, create_goal, get_goal, activate_goal, defer_goal, complete_goal, drop_goal, run_cycle, health, register
- Imports: flask, os, substrate.control_plane.goals.goal_selector, sys
### `services/heartbeat.py`
- Lines: 114. Doc: EOS Heartbeat Service
- Classes: -
- Functions: system_health_heartbeat, run_once, run_loop
- Imports: datetime, dotenv, json, logging, os, sys, time, zoneinfo
### `services/higgsfield_webhook.py`
- Lines: 132. Doc: Higgsfield Cloud API webhook receiver.
- Classes: -
- Functions: _download, _extract_output_url, handle_webhook, register
- Imports: __future__, datetime, flask, os, pathlib, requests, substrate.state.storage.db, sys
### `services/icp_scorer.py`
- Lines: 604. Doc: -
- Classes: RateLimiter
- Functions: parse_frontmatter, extract_comment_text, get_processed_filenames, lead_exists, already_contacted, in_pipeline, load_outreach_messages, _extract_openers, pick_opener, score_comment, update_opener_stats_sent, push_lead_to_notion
- Imports: adapters.models.agent_runtime, datetime, dotenv, glob, json, os, shutil, substrate.state.memory.memory
### `services/kpi_tracker.py`
- Lines: 412. Doc: -
- Classes: -
- Functions: get_pipeline_counts, get_scraper_stats, get_daily_log, get_conversation_stats, _parse_lead_frontmatter, get_opener_stats, get_hashtag_stats, append_kpi_history, get_reply_rate_trend, get_hashtag_report, build_eod_report, send_telegram
- Imports: cost_tracker, datetime, dotenv, glob, json, os, requests, sys
### `services/local_bridge_client.py`
- Lines: 173. Doc: Local Bridge Client — forwards Discord messages to Antony's local machine.
- Classes: -
- Functions: is_bridge_enabled, check_health, forward_to_local, send_mfa_response, bridge_status
- Imports: __future__, dotenv, logging, os, pathlib, requests, sys, typing
### `services/local_bridge_server.py`
- Lines: 259. Doc: Local Bridge Server — runs on Antony's Windows machine (WSL2).
- Classes: -
- Functions: _tmux_has_session, _tmux_send, _inject_message, handle_health, handle_message, handle_status, create_app
- Imports: __future__, aiohttp, asyncio, json, logging, os, pathlib, subprocess
### `services/magic_link_handler.py`
- Lines: 359. Doc: magic_link_handler.py — Bridge endpoint for intercepting auth emails.
- Classes: -
- Functions: _creds_path_for_inbox, _get_gmail_service, _gmail_list_messages, _gmail_get_message, _get_full_message_body, _extract_body_from_payload, _extract_verification_code, _extract_magic_link, _is_recent_email, handle_wait_for_magic_link, register_routes
- Imports: __future__, aiohttp, asyncio, base64, json, logging, os, pathlib
### `services/magic_link_server.py`
- Lines: 60. Doc: magic_link_server.py — Standalone VPS server for magic-link email interception.
- Classes: -
- Functions: create_app
- Imports: __future__, aiohttp, logging, os, pathlib, services.magic_link_handler, sys
### `services/oauth_device_flow.py`
- Lines: 305. Doc: oauth_device_flow.py — Headless OAuth re-auth via Tailscale-routed callback.
- Classes: -
- Functions: _resolve_scopes, _load_client_config, _get_redirect_uri, _build_auth_url, _exchange_code, _notify_discord, _save_credentials, run_oauth_flow, main
- Imports: __future__, aiohttp, argparse, asyncio, json, logging, os, pathlib
### `services/operator_api.py`
- Lines: 791. Doc: UMH Operator Workstation API — FastAPI backend for the operator UI.
- Classes: _RequestTimeoutMiddleware
- Functions: _wire_spine_to_cockpit_ws, _tick_loop, lifespan, verify_api_key, health, _load_memories, knowledge_entries, knowledge_stats, knowledge_search, system_costs, system_containers, system_ingestion_status
- Imports: adapters, asyncio, concurrent.futures, contextlib, datetime, dotenv, fastapi, fastapi.middleware.cors
### `services/overnight_scrape.py`
- Lines: 253. Doc: -
- Classes: -
- Functions: send_telegram, count_new_leads_today, get_today_cost, force_group_a, get_scrape_stats, get_hashtag_learning, check_cost_approval, run_scraper, run_scorer, main
- Imports: datetime, dotenv, glob, json, os, requests, subprocess, substrate.execution.cpu_gate
### `services/tier_3_fallback.py`
- Lines: 29. Doc: Tier 3 fallback — stub for future UI-TARS / computer-use integration.
- Classes: -
- Functions: tier_3_fallback
- Imports: __future__, logging, typing
### `services/trigger_export.py`
- Lines: 129. Doc: trigger_export.py — VPS-side trigger for browser exports on Windows.
- Classes: -
- Functions: _check_bridge_health, fire_export, main
- Imports: __future__, argparse, dotenv, json, logging, os, pathlib, requests
### `substrate/__init__.py`
- Lines: 499. Doc: UMH Substrate — the unified intelligence substrate.
- Classes: Substrate
- Functions: get_conn, run_browser_task
- Imports: __future__, asyncio, logging, substrate.control_plane.context, substrate.control_plane.governance, substrate.control_plane.identity, substrate.control_plane.memory, substrate.control_plane.registry
### `substrate/canonical_types.py`
- Lines: 1329. Doc: Canonical Type Registry — single source of truth for all UMH domain types.
- Classes: -
- Functions: lookup, check_name
- Imports: __future__
### `substrate/composition/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/composition/knowledge_gap_trigger.py`
- Lines: 171. Doc: Knowledge gap trigger — detects gaps during execution and triggers composition.
- Classes: KnowledgeGap, KnowledgeGapTrigger
- Functions: -
- Imports: __future__, dataclasses, json, logging, pathlib, time, typing
### `substrate/composition/mastery/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/composition/mastery/authoring/__init__.py`
- Lines: 22. Doc: Tool Mastery Author Agent.
- Classes: -
- Functions: -
- Imports: .agent, .models
### `substrate/composition/mastery/authoring/__main__.py`
- Lines: 5. Doc: -
- Classes: -
- Functions: -
- Imports: .cli
### `substrate/composition/mastery/authoring/agent.py`
- Lines: 189. Doc: Author Agent orchestrator.
- Classes: -
- Functions: _iso_now, _display_name, author, _write_provenance
- Imports: .draft, .loader, .mapping, .models, .reconcile, .verify, __future__, datetime
### `substrate/composition/mastery/authoring/cli.py`
- Lines: 133. Doc: CLI entry for the Tool Mastery Author Agent.
- Classes: -
- Functions: _latest_artifact_for, build_parser, main
- Imports: .agent, .models, .paths, __future__, argparse, json, pathlib, sys
### `substrate/composition/mastery/authoring/draft.py`
- Lines: 452. Doc: Draft authored section content from SectionEvidence.
- Classes: -
- Functions: _label_for, _render_ordered_list, _render_pattern, _render_prose_excerpt, _looks_marketing, _render_sourced_content, _render_uncovered_content, _has_usable_evidence, build_drafts, render_best_practices, _status_badge, render_skill_body
- Imports: .mapping, .models, __future__
### `substrate/composition/mastery/authoring/loader.py`
- Lines: 219. Doc: Research artifact loader.
- Classes: RawCapture, LoadedArtifact
- Functions: sanitize_text, _symbol_density, _read_text_safely, load_artifact
- Imports: __future__, dataclasses, json, pathlib, re, typing
### `substrate/composition/mastery/authoring/mapping.py`
- Lines: 610. Doc: Section → raw-capture evidence mapping.
- Classes: SectionEvidence
- Functions: _strip_html, is_prose_block, _split_prose_blocks, _excerpt_from_block, _scan_capture_for_section, _apply_pattern_evidence, map_sections
- Imports: .loader, __future__, dataclasses, html, re
### `substrate/composition/mastery/authoring/models.py`
- Lines: 141. Doc: Data types for the Tool Mastery Author Agent.
- Classes: AuthorStatus, AuthorRequest, SectionDraft, AuthoredProvenance, AuthorResult
- Functions: -
- Imports: __future__, dataclasses, enum, typing
### `substrate/composition/mastery/authoring/paths.py`
- Lines: 17. Doc: Path resolution for the Tool Mastery Author Agent.
- Classes: -
- Functions: -
- Imports: __future__, os, pathlib
### `substrate/composition/mastery/authoring/reconcile.py`
- Lines: 173. Doc: Reconcile drafts with existing on-disk skill files.
- Classes: ReconcilePlan
- Functions: _looks_like_scaffold, plan_reconciliation, run_scaffold, replace_body_preserving_frontmatter
- Imports: .paths, __future__, dataclasses, pathlib, subprocess, substrate.execution.cpu_gate
### `substrate/composition/mastery/authoring/verify.py`
- Lines: 78. Doc: Run verify_tool_skill.py against an authored tool.
- Classes: VerifyReport
- Functions: verify_skill
- Imports: .paths, __future__, dataclasses, json, subprocess, substrate.execution.cpu_gate
### `substrate/composition/mastery/management/__init__.py`
- Lines: 75. Doc: Tool Mastery Manager — unification layer over the Tool Mastery Engine.
- Classes: -
- Functions: -
- Imports: .active_tool_context, .mastery_assurance, .models, .tool_mastery_resolver, __future__
### `substrate/composition/mastery/management/active_tool_context.py`
- Lines: 151. Doc: Active Tool Context for the Tool Mastery Engine.
- Classes: ActiveToolContext
- Functions: _now_iso, create_active_tool_context, update_active_tool_context, should_continue_context, should_switch_context, summarize_active_tool_context
- Imports: .tool_mastery_resolver, __future__, dataclasses, datetime, typing
### `substrate/composition/mastery/management/backlog.py`
- Lines: 189. Doc: Backlog / bootstrap flow.
- Classes: BacklogEntry
- Functions: _iter_discovered, build_backlog, _write_report, backlog_report, bootstrap
- Imports: .coverage, .discovery, .ensure, .models, .paths, __future__, dataclasses, datetime
### `substrate/composition/mastery/management/coverage.py`
- Lines: 121. Doc: Unified coverage evaluator for the Tool Mastery Manager.
- Classes: -
- Functions: evaluate_coverage, evaluate_many
- Imports: .models, .paths, __future__, datetime, os, scripts._tme_common, scripts.check_skill_staleness, scripts.verify_tool_skill
### `substrate/composition/mastery/management/discovery.py`
- Lines: 333. Doc: Tool discovery for the Tool Mastery Manager.
- Classes: -
- Functions: normalise_slug, _title_case, discover_skills_dir, discover_explicit, discover_seed_list, discover_claude_json, _merge, load_exclude_slugs, _apply_exclusions, discover_all
- Imports: .models, .paths, __future__, json, pathlib, re, typing
### `substrate/composition/mastery/management/ensure.py`
- Lines: 175. Doc: ensure_mastery — the primary entry point of the Tool Mastery Manager.
- Classes: -
- Functions: _scaffold, _plan_for, _queue, ensure_mastery
- Imports: .coverage, .models, .paths, __future__, os, pathlib, subprocess, substrate.control_plane.actions.control_plane
### `substrate/composition/mastery/management/maintenance.py`
- Lines: 61. Doc: Maintenance flows for the Tool Mastery Manager.
- Classes: -
- Functions: refresh_stale, repair_invalid, audit_all
- Imports: .backlog, .coverage, .discovery, .ensure, .models, __future__
### `substrate/composition/mastery/management/mastery_assurance.py`
- Lines: 266. Doc: Mastery Assurance Gate for the Tool Mastery Engine.
- Classes: MasteryAssuranceStatus, RecommendedFlow, MasteryAssuranceDecision
- Functions: normalize_tool_name, determine_staleness_threshold, evaluate_pack_freshness, evaluate_pack_quality, evaluate_pack_completeness, determine_required_tme_flow, ensure_mastery_before_execution, mastery_assurance_blocks_execution
- Imports: __future__, dataclasses, datetime, enum, re, typing
### `substrate/composition/mastery/management/models.py`
- Lines: 122. Doc: Data types for the Tool Mastery Manager.
- Classes: CoverageStatus, DiscoverySource, ToolRef, CoverageReport, ManagerPlan, EnsureResult
- Functions: -
- Imports: __future__, dataclasses, enum, typing
### `substrate/composition/mastery/management/paths.py`
- Lines: 21. Doc: Path resolution for the Tool Mastery Manager.
- Classes: -
- Functions: -
- Imports: __future__, os, pathlib
### `substrate/composition/mastery/management/tool_mastery_resolver.py`
- Lines: 326. Doc: Natural Language Tool Mastery Resolver.
- Classes: ResolvedToolMention, ResolvedCapabilityMention, ResolvedMasteryPack, ToolMasteryResolution
- Functions: detect_tool_mentions, detect_capability_mentions, _detect_runtimes, infer_required_mastery_packs, resolve_mastery_for_task, should_reuse_active_tool_context, explain_mastery_resolution
- Imports: __future__, dataclasses, os, re, typing
### `substrate/composition/mastery/research/__init__.py`
- Lines: 44. Doc: Tool Mastery Research Agent.
- Classes: -
- Functions: -
- Imports: .models, __future__
### `substrate/composition/mastery/research/__main__.py`
- Lines: 5. Doc: -
- Classes: -
- Functions: -
- Imports: .cli
### `substrate/composition/mastery/research/agent.py`
- Lines: 202. Doc: Research Agent orchestrator.
- Classes: -
- Functions: _run_stamp, _derive_status, _queue_author_action, run
- Imports: .artifact, .fetcher, .handoff, .models, .paths, .source_discovery, __future__, datetime
### `substrate/composition/mastery/research/artifact.py`
- Lines: 609. Doc: Artifact writer for the Tool Mastery Research Agent.
- Classes: -
- Functions: _iso_now, _ok_sources, _run_signal_pass, _run_phase5_extraction, build_artifact, _render_summary, _render_sources, write_artifact
- Imports: .extraction, .headless_fetcher, .models, .source_quality, __future__, datetime, json, pathlib
### `substrate/composition/mastery/research/candidate_approval.py`
- Lines: 272. Doc: Candidate approval gate for search-based source discovery.
- Classes: CandidateRecord, ApprovalFile
- Functions: _now_iso, _candidates_dir, build_approval_file, persist_approval_file, load_approval_file, save_approval_file, latest_approval_file, apply_decision, approved_source_refs, format_candidates_for_display
- Imports: .models, .paths, .search_discovery, __future__, dataclasses, datetime, json, pathlib
### `substrate/composition/mastery/research/cli.py`
- Lines: 250. Doc: CLI entry for the Tool Mastery Research Agent.
- Classes: -
- Functions: _load_action_file, build_parser, _parse_index_set, _handle_generate_candidates, _handle_show_candidates, _handle_apply_decision, main
- Imports: .agent, .candidate_approval, .models, .search_discovery, __future__, argparse, json, pathlib
### `substrate/composition/mastery/research/docs_site_discovery.py`
- Lines: 612. Doc: Docs site discovery for the Tool Mastery Research Agent.
- Classes: SiteCoordinates
- Functions: parse_site_coordinates, _http_get, _looks_like_doc_path, _parse_sitemap_xml, _parse_llms_txt, _same_host, _discover_via_sitemap, _discover_via_llms_txt, _topically_relevant, _filter_and_rank, discover_docs_site_urls
- Imports: .models, __future__, dataclasses, os, re, socket, urllib.error, urllib.parse
### `substrate/composition/mastery/research/extraction.py`
- Lines: 1266. Doc: Structured knowledge extraction for the Tool Mastery Research Agent.
- Classes: SourceType, SourceTypeReport, ExtractedPattern, SourceExtraction
- Functions: preprocess_for_extraction, _count_vocab_hits, classify_source_type, _heading_with_body, _bounded, _confidence, _emit_if_worthy, _extract_install_commands, _extract_setup_flows, _extract_config_blocks, _extract_function_signatures, _extract_param_defs
- Imports: __future__, dataclasses, enum, html, re, typing, urllib.parse
### `substrate/composition/mastery/research/fetcher.py`
- Lines: 166. Doc: Fetcher for the Tool Mastery Research Agent.
- Classes: -
- Functions: _iso_now, _safe_filename, fetch_source, fetch_plan
- Imports: .models, __future__, datetime, os, pathlib, socket, urllib.error, urllib.parse
### `substrate/composition/mastery/research/github_extractor.py`
- Lines: 351. Doc: GitHub repo extractor for the Tool Mastery Research Agent.
- Classes: RepoCoordinates
- Functions: parse_github_url, _api_get_json, _get_default_branch_sha, _list_tree, _path_in_any_dir, _prioritise_files, _raw_url, _classify_label, expand_github_repo
- Imports: .models, __future__, dataclasses, json, os, socket, urllib.error, urllib.parse
### `substrate/composition/mastery/research/handoff.py`
- Lines: 124. Doc: Safe metadata handoff for the Tool Mastery Research Agent.
- Classes: -
- Functions: _top_source_url, _update_frontmatter_field, apply_safe_metadata
- Imports: .models, .paths, __future__, datetime, pathlib
### `substrate/composition/mastery/research/headless_fetcher.py`
- Lines: 367. Doc: Headless rendering fetch path for the Tool Mastery Research Agent.
- Classes: RenderAttempt, RenderPassReport
- Functions: _iso_now, is_likely_spa, _load_playwright, _render_one, render_low_signal_sources
- Imports: .models, __future__, dataclasses, datetime, pathlib, re, typing
### `substrate/composition/mastery/research/models.py`
- Lines: 210. Doc: Data types for the Tool Mastery Research Agent.
- Classes: ResearchMode, ResearchStatus, SourceTier, FetchStatus, ResearchRequest, SourceRef, SourcePlan, FetchedSource
- Functions: -
- Imports: __future__, dataclasses, enum, typing
### `substrate/composition/mastery/research/paths.py`
- Lines: 18. Doc: Path resolution for the Tool Mastery Research Agent.
- Classes: -
- Functions: -
- Imports: __future__, os, pathlib
### `substrate/composition/mastery/research/search_discovery.py`
- Lines: 354. Doc: Deterministic search candidate generator for the Research Agent.
- Classes: Candidate, CandidatePlan
- Functions: _tokenize, _join, _variants, _family_pypi, _family_npm, _family_github_search, _family_github_repo_guess, _family_vendor_domain, _family_api_reference, _dedupe, generate_candidates
- Imports: .models, __future__, dataclasses, re, typing
### `substrate/composition/mastery/research/source_discovery.py`
- Lines: 363. Doc: Source discovery for the Tool Mastery Research Agent.
- Classes: -
- Functions: _slugify, _from_registry, _from_claude_json, discover_sources
- Imports: .candidate_approval, .docs_site_discovery, .github_extractor, .models, .paths, .source_quality, .structured_crawl, __future__
### `substrate/composition/mastery/research/source_quality.py`
- Lines: 371. Doc: Source quality scoring for the Tool Mastery Research Agent.
- Classes: SignalReport
- Functions: _split_host, score_source, sort_sources_by_quality, _is_raw_text_source, measure_signal, classify_quality
- Imports: .models, __future__, dataclasses, re, typing, urllib.parse
### `substrate/composition/mastery/research/structured_crawl.py`
- Lines: 439. Doc: Structured crawl expansion for the Tool Mastery Research Agent.
- Classes: CrawlProvenance, CrawlReport, _AnchorExtractor
- Functions: _extract_anchors, _http_get, _same_host, _looks_like_doc_path, _normalise, crawl_approved_docs
- Imports: .docs_site_discovery, .models, __future__, dataclasses, html.parser, os, re, socket
### `substrate/composition/registries/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/composition/registries/canonical_command_registry_v1.py`
- Lines: 426. Doc: Canonical Command Registry v1.
- Classes: RoutingMode, ExecutionMode, CommandEntry, CanonicalCommandRegistryV1
- Functions: get_canonical_registry
- Imports: __future__, dataclasses, enum, hashlib, json, typing
### `substrate/contracts/__init__.py`
- Lines: 2. Doc: Substrate contracts — types and protocols that adapters implement.
- Classes: -
- Functions: -
- Imports: -
### `substrate/contracts/adapter_contracts.py`
- Lines: 65. Doc: Adapter registry contracts — substrate-owned interface for adapter descriptors.
- Classes: CapabilityDescriptor, AdapterDescriptor, AdapterRegistry
- Functions: -
- Imports: __future__, dataclasses, substrate.execution.runtime.worker_runtime_contracts, typing
### `substrate/contracts/agent_runtime_contracts.py`
- Lines: 42. Doc: Agent runtime protocol — substrate-owned interface for LLM execution.
- Classes: AgentRuntimeProtocol
- Functions: get_agent_runtime
- Imports: __future__, substrate.contracts.agent_types, substrate.state.context.context, typing
### `substrate/contracts/agent_types.py`
- Lines: 115. Doc: Canonical agent types owned by the substrate layer.
- Classes: TaskType, ModelProvider, ProviderRole, AgentResult, RoutingResult
- Functions: calculate_cost
- Imports: __future__, dataclasses, enum
### `substrate/contracts/routing_contracts.py`
- Lines: 51. Doc: Routing contracts — substrate-owned capability classes and routing types.
- Classes: CapabilityClass, PrivacyLevel, CapabilityEntry
- Functions: -
- Imports: __future__, enum, pydantic
### `substrate/control_plane/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/actions/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/actions/actions.py`
- Lines: 85. Doc: Action object — the canonical unit of control in EOS.
- Classes: Action
- Functions: propose_action
- Imports: __future__, dataclasses, datetime, typing, uuid
### `substrate/control_plane/actions/control_plane.py`
- Lines: 273. Doc: Control Plane — the public entry point for the EOS Action System.
- Classes: -
- Functions: _execute_approved, _skipped_duplicate, _deferred_file_exists, run_action, resume_action
- Imports: ., .actions, .deferred, .executor, .logging, .notifier, .policy, .tme
### `substrate/control_plane/actions/deferred.py`
- Lines: 99. Doc: Durable persistence for deferred actions.
- Classes: -
- Functions: _path_for, save_deferred, load_deferred, delete_deferred, list_deferred
- Imports: .actions, __future__, dataclasses, datetime, json, os, typing
### `substrate/control_plane/actions/deferred_status.py`
- Lines: 242. Doc: Lightweight status tracking for deferred actions.
- Classes: DeferredStatus
- Functions: _status_path, read_status, write_status, clear_status, is_stale, wake_due_snoozed, list_overdue_snoozed, mark_stale_over_threshold
- Imports: .deferred, __future__, dataclasses, datetime, json, os, typing
### `substrate/control_plane/actions/executor.py`
- Lines: 134. Doc: Action executors — dispatch by action.type.
- Classes: -
- Functions: _run_shell, _execute_shell_command, _execute_run_script, _execute_write_file, _execute_call_api, _execute_compose_action, execute_action
- Imports: .actions, __future__, os, subprocess, substrate.execution.cpu_gate, typing
### `substrate/control_plane/actions/idempotency.py`
- Lines: 298. Doc: Filesystem sentinel store for Control Plane idempotency.
- Classes: Sentinel
- Functions: _hash_key, _path_for, _now_iso, read, _write, claim, force_claim, complete, clear, list_all, find, prune_expired
- Imports: __future__, dataclasses, datetime, hashlib, json, os, typing
### `substrate/control_plane/actions/logging.py`
- Lines: 75. Doc: Append-only JSONL loggers for execution and decision records.
- Classes: -
- Functions: _today_path, _append_jsonl, log_execution, log_decision
- Imports: .actions, __future__, datetime, json, os, typing, uuid
### `substrate/control_plane/actions/notifier.py`
- Lines: 122. Doc: Notifier foundation for deferred actions.
- Classes: Notifier, FileNotifier, DiscordNotifier, MultiNotifier
- Functions: default_notifier
- Imports: .actions, __future__, datetime, json, os, typing
### `substrate/control_plane/actions/policy.py`
- Lines: 165. Doc: Policy bridge between the Control Plane and `runtime.authority_engine`.
- Classes: -
- Functions: normalize_risk, map_to_authority_class, required_autonomy_level, requires_explicit_approval, blocks_auto_execute, authority_classify, resolve_effective_risk
- Imports: __future__, typing
### `substrate/control_plane/actions/tme.py`
- Lines: 141. Doc: Tool Mastery Engine / Manager integration for the Control Plane.
- Classes: -
- Functions: query_relevant_skills, ensure_tool_mastery, ensure_mastery_before_tool_execution, resolve_mastery_for_user_intent
- Imports: __future__, os, subprocess, substrate.execution.cpu_gate, typing
### `substrate/control_plane/actions/validator.py`
- Lines: 188. Doc: Validation + approval rules for Actions.
- Classes: -
- Functions: _check_path_safety, _check_shell_safety, validate_action, approve_action
- Imports: .actions, .policy, __future__, typing
### `substrate/control_plane/agents/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/agents/agent_hierarchy.py`
- Lines: 467. Doc: -
- Classes: AgentHierarchy
- Functions: _venture_name
- Imports: os
### `substrate/control_plane/agents/agent_teams.py`
- Lines: 527. Doc: Domain team registry for the OS agent system.
- Classes: SubAgentConfig, SalesTeam, ResearchTeam, ContentTeam, MarketingTeam, CustomerSuccessTeam, OperationsTeam
- Functions: route, run_team_task, run_browser_action, send_outreach_dm, research_prospect, list_teams
- Imports: dataclasses, substrate.contracts.agent_types
### `substrate/control_plane/agents/ceo_agent.py`
- Lines: 377. Doc: CEOAgent — one per company, strategy layer.
- Classes: CEOAgent
- Functions: -
- Imports: json, os, substrate.state.context.context, typing
### `substrate/control_plane/agents/ceo_intelligence.py`
- Lines: 727. Doc: CEO Intelligence — real-time business diagnostics.
- Classes: -
- Functions: _get_benchmarks, get_funnel_metrics, diagnose_constraint, get_offer_stage, get_agent_performance, generate_ceo_brief
- Imports: datetime, dotenv, json, logging, os, zoneinfo
### `substrate/control_plane/agents/ceo_operational_standards.py`
- Lines: 604. Doc: CEO Best Practices — operational ruleset for
- Classes: -
- Functions: get_constraint_rules, get_offer_rules, get_delegation_rules, get_hiring_rules, get_metric_rules, get_decision_rules, get_stage_rules, get_growth_rules, get_all_standards
- Imports: -
### `substrate/control_plane/agents/ea_operational_standards.py`
- Lines: 143. Doc: EA Best Practices — world class EA operating standards
- Classes: -
- Functions: get_calendar_rules, get_email_rules, get_meeting_rules, get_all_standards
- Imports: -
### `substrate/control_plane/context/__init__.py`
- Lines: 93. Doc: ContextAssembler — builds execution context from signal + identity.
- Classes: ContextAssembler, ConcreteContextAssembler
- Functions: -
- Imports: __future__, os, substrate.types, typing
### `substrate/control_plane/context/context_builder.py`
- Lines: 551. Doc: ContextBuilder — single-pass context assembly for the execution spine.
- Classes: UnifiedContext, ContextBuilder
- Functions: -
- Imports: dataclasses, json, os, pathlib, substrate.self_model, substrate.state.context.context, sys, typing
### `substrate/control_plane/context/context_compaction.py`
- Lines: 214. Doc: ContextCompactor — seamless context window management for long conversations.
- Classes: ContextCompactor
- Functions: _utcnow
- Imports: datetime, json, substrate.state.context.context, substrate.state.storage.db, uuid
### `substrate/control_plane/coordination/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/coordination/coordination_engine.py`
- Lines: 387. Doc: CoordinationEngine — event-driven task coordination for AI agents and humans.
- Classes: CoordinationEngine
- Functions: _utcnow, _notify
- Imports: datetime, dotenv, json, pathlib, substrate.control_plane.events.event_bus, substrate.governance.policy.authority_engine, substrate.state.context.context, substrate.state.storage.db
### `substrate/control_plane/delegation/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/delegation/delegation_tracker.py`
- Lines: 95. Doc: Delegation Tracker — tracks tasks routed to CEO agents
- Classes: -
- Functions: log_delegation, get_overdue_delegations, mark_delegation_complete
- Imports: datetime, json, logging, substrate.self_model, zoneinfo
### `substrate/control_plane/events/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/events/event_bus.py`
- Lines: 668. Doc: EventBus — reactive coordination layer for UMH agents.
- Classes: EventBus, EventRegistry
- Functions: _utcnow, _handle_new_lead, _handle_lead_replied, _handle_lead_booked, _handle_lead_closed, _handle_lead_lost, _handle_signal_captured, _handle_content_needed, _handle_morning_cycle, _handle_loop_cycle, _handle_skill_threshold, _handle_goal_activated
- Imports: datetime, json, os, substrate.state.memory.memory, substrate.state.storage.db, sys, threading, typing
### `substrate/control_plane/events/event_manager.py`
- Lines: 255. Doc: Event Manager — coordinates conferences, offsites, client dinners,
- Classes: -
- Functions: create_event, get_events, log_speaking_engagement, draft_talking_points, log_pr_media_inquiry
- Imports: datetime, dotenv, json, logging, pathlib, substrate.self_model, zoneinfo
### `substrate/control_plane/goals/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/goals/goal_selector.py`
- Lines: 1486. Doc: GoalSelector — goal selection + system focus layer.
- Classes: GoalState, PerformanceProfile, MultiHorizonProfile, Goal, OpportunityCostLayer, StrategicHorizonLayer, GoalSelector, OutcomeTracker
- Functions: -
- Imports: dataclasses, datetime, enum, json, math, os, substrate.state.storage.db, sys
### `substrate/control_plane/governance.py`
- Lines: 279. Doc: GovernanceEngine — the single governance entry point for UMH.
- Classes: GovernanceEngine, ConcreteGovernanceEngine
- Functions: -
- Imports: __future__, re, substrate.types, typing
### `substrate/control_plane/identity/__init__.py`
- Lines: 70. Doc: Identity resolution for the substrate control plane.
- Classes: IdentityResolver, ConcreteIdentityResolver
- Functions: -
- Imports: __future__, substrate.types, typing
### `substrate/control_plane/identity/ai_identity.py`
- Lines: 268. Doc: AIIdentityEngine — foundational AI identity principles.
- Classes: IdentityPrinciple, AIIdentityEngine
- Functions: -
- Imports: dataclasses
### `substrate/control_plane/invariants/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/invariants/coherence_gate.py`
- Lines: 75. Doc: Coherence Gate — fail-closed execution guard.
- Classes: CoherenceGateBlocked
- Functions: evaluate_coherence_before_execution, assert_coherent_or_block, coherence_gate_allows_execution
- Imports: .spine_coherence_validator, .spine_lineage_contracts, __future__, typing
### `substrate/control_plane/invariants/spine_coherence_validator.py`
- Lines: 234. Doc: Canonical Spine Coherence Validator.
- Classes: -
- Functions: validate_coherence_envelope, validate_coherence_envelope_dict, _check_required_stages, _check_no_duplicates, _check_stage_order, _check_stage_artifacts, _check_mvp_stubs, _check_ordering_constraints
- Imports: .spine_lineage_contracts, __future__
### `substrate/control_plane/invariants/spine_lineage_contracts.py`
- Lines: 190. Doc: Canonical Spine Lineage Contracts.
- Classes: SpineStage, SpineStageStatus, CoherenceStatus, CoherenceFailureReason, SpineStageArtifact, SpineLineage, CoherenceEnvelope, CoherenceValidationResult
- Functions: -
- Imports: __future__, dataclasses, enum, typing
### `substrate/control_plane/memory.py`
- Lines: 100. Doc: MemorySystem — unified protocol over existing memory stores.
- Classes: MemorySystem, ConcreteMemorySystem
- Functions: -
- Imports: __future__, substrate.types, typing, uuid
### `substrate/control_plane/onboarding/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/onboarding/onboarding_engine.py`
- Lines: 357. Doc: OnboardingEngine — conversational onboarding for new EOS founders.
- Classes: OnboardingStep, OnboardingSession, OnboardingEngine
- Functions: -
- Imports: __future__, asyncio, dataclasses, datetime, enum, json, os, pathlib
### `substrate/control_plane/onboarding/setup_wizard.py`
- Lines: 167. Doc: SetupWizard — onboarding flow for new EOS users.
- Classes: -
- Functions: generate_ea_soul_doc, run_setup
- Imports: __future__, os, pathlib, sys
### `substrate/control_plane/orchestrator/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/orchestrator/orchestrator.py`
- Lines: 1911. Doc: Orchestrator — strategic intelligence layer.
- Classes: CEOAgent, Orchestrator
- Functions: _notify, _send_discord_webhook, _fmt_company_reports, _fmt_signals, _fmt_pending, _fmt_patterns, run_full_morning_cycle, run_ceo_morning_delegation, check_proactive_triggers, check_outcome_milestone, generate_morning_brief, write_to_notion_dashboard
- Imports: datetime, dotenv, json, os, pathlib, requests, substrate.contracts.agent_runtime_contracts, substrate.contracts.agent_types
### `substrate/control_plane/proactive/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/proactive/proactive_engine.py`
- Lines: 302. Doc: ProactiveIntelligenceEngine — surfaces what matters without being asked.
- Classes: ProactiveSignalType, ProactiveSignal, ProactiveIntelligenceEngine
- Functions: -
- Imports: dataclasses, datetime, enum
### `substrate/control_plane/registry.py`
- Lines: 106. Doc: ComponentRegistry — unified registry for all substrate components.
- Classes: ComponentRegistry, ConcreteComponentRegistry
- Functions: -
- Imports: __future__, substrate.types, typing, uuid
### `substrate/control_plane/router/__init__.py`
- Lines: 112. Doc: SignalRouter — the integration point that wires all subsystems together.
- Classes: SignalRouter, ConcreteSignalRouter
- Functions: -
- Imports: __future__, substrate.types, typing
### `substrate/control_plane/router/control_plane_router_v1.py`
- Lines: 521. Doc: Control Plane Router v1.
- Classes: ControlPlaneRouterV1
- Functions: _log, _log_error, load_config
- Imports: .router_contracts, __future__, datetime, json, os, pathlib, substrate.contracts.adapter_contracts, substrate.execution.runtime.worker_runtime_contracts
### `substrate/control_plane/router/intent_router.py`
- Lines: 171. Doc: IntentRouter — classify founder messages to the correct agent domain.
- Classes: IntentDomain, IntentRouter
- Functions: -
- Imports: enum, os, substrate.state.context.context
### `substrate/control_plane/router/router_contracts.py`
- Lines: 168. Doc: Control plane router contracts for the UMH substrate layer.
- Classes: RouterStatus, CapabilityType, WorkPacket, CapabilityRequirement, RouterDecision, RuntimeProofReference, RouterResult
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, typing
### `substrate/control_plane/runtime/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/runtime/cognitive_loop.py`
- Lines: 1540. Doc: CognitiveLoop — full Perceive → Understand → Plan → Execute
- Classes: MultimodalInput, CognitiveResult, CognitiveLoop
- Functions: _deterministic_cognitive_response, _get_neon_spend, format_response_footer, _format_intent_context, detect_intent_and_inject
- Imports: dataclasses, datetime, json, logging, os, pathlib, re, substrate.contracts.agent_runtime_contracts
### `substrate/control_plane/runtime/gateway.py`
- Lines: 1928. Doc: Gateway — single control plane for all AI operations.
- Classes: Gateway
- Functions: _utcnow, _timestamp_id, get_gateway, ingest_external_context
- Imports: datetime, json, logging, os, pathlib, re, substrate.observability.error_recorder, substrate.state.storage.db
### `substrate/control_plane/runtime/orchestrator/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/runtime/orchestrator/decisions.py`
- Lines: 159. Doc: Decision helpers for signal handler workflows.
- Classes: -
- Functions: _today_decision_log_path, retry_count_today, _action_type, _risk, _has_idempotency, should_retry, should_escalate, should_ignore
- Imports: __future__, datetime, json, os, substrate.control_plane.actions.logging, typing
### `substrate/control_plane/runtime/orchestrator/handlers.py`
- Lines: 322. Doc: Signal handler workflows.
- Classes: -
- Functions: _append_operator_notice, _action_from_context, handle_deferred_stale, handle_action_failed, handle_action_retry_requested
- Imports: .decisions, __future__, datetime, json, os, substrate.control_plane.actions.control_plane, substrate.control_plane.actions.notifier, typing
### `substrate/control_plane/runtime/orchestrator/loop.py`
- Lines: 455. Doc: Autonomous loop — deterministic orchestration cycle.
- Classes: LoopConfig, CycleReport
- Functions: _drain_signals, _scan_stale_deferred, _today_execution_log_path, _read_recent_failures, _already_followed_up, _scan_failures, _write_heartbeat, run_cycle, run_forever
- Imports: .orchestrator, .signals, __future__, dataclasses, datetime, json, os, substrate.control_plane.actions.deferred
### `substrate/control_plane/runtime/orchestrator/orchestrator.py`
- Lines: 202. Doc: Orchestrator — execution coordinator for named workflows.
- Classes: WorkflowRecord, Orchestrator
- Functions: default_orchestrator
- Imports: .pipeline, __future__, dataclasses, datetime, json, os, substrate.control_plane.actions.logging, threading
### `substrate/control_plane/runtime/orchestrator/pipeline.py`
- Lines: 277. Doc: Pipeline — sequential composition of Control Plane actions.
- Classes: ActionStep, FuncStep, Pipeline, StepOutcome, PipelineResult
- Functions: _run_action_step, _run_func_step, run_pipeline
- Imports: __future__, dataclasses, substrate.control_plane.actions.control_plane, substrate.control_plane.actions.logging, time, typing
### `substrate/control_plane/runtime/orchestrator/signals.py`
- Lines: 211. Doc: Signals — filesystem-backed event layer for the orchestrator.
- Classes: SignalEmission
- Functions: _signal_dir, _pending_dir, _processed_dir, _load_bindings, _save_bindings, define_signal, emit_signal, register_handler, unregister_handler, get_handlers, list_signals, list_pending
- Imports: __future__, dataclasses, datetime, json, os, time, typing, uuid
### `substrate/control_plane/runtime/orchestrator/steps.py`
- Lines: 211. Doc: Reusable orchestrator step helpers.
- Classes: ScriptWorkflowSpec
- Functions: run_script_workflow, script_step, api_step
- Imports: .pipeline, __future__, dataclasses, json, substrate.control_plane.actions.control_plane, typing
### `substrate/control_plane/runtime/orchestrator/workflows.py`
- Lines: 125. Doc: Workflow registry — wires existing Control Plane workflows into the orchestrator.
- Classes: -
- Functions: _wrap_main, register_default_workflows
- Imports: .handlers, .orchestrator, .signals, __future__, importlib, sys, typing
### `substrate/control_plane/runtime/substrate_gateway.py`
- Lines: 179. Doc: SubstrateGateway — unified SignalEnvelope interface over the internal Gateway.
- Classes: SubstrateGateway
- Functions: create_signal_from_discord
- Imports: __future__, logging, os, substrate.types, time, typing, uuid
### `substrate/control_plane/scheduling/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/scheduling/daily_sync.py`
- Lines: 630. Doc: DailySync — structured daily briefing format.
- Classes: SyncAgenda, DailySync
- Functions: _normalize_task
- Imports: dataclasses, datetime, os, substrate.self_model
### `substrate/control_plane/scheduling/ideal_week.py`
- Lines: 259. Doc: Ideal Week — stores and applies the founder's ideal
- Classes: -
- Functions: get_ideal_week, save_ideal_week, create_process_capture, save_annual_architecture, get_annual_architecture, get_current_quarter_rocks
- Imports: datetime, dotenv, json, logging, os, pathlib, re, substrate.self_model
### `substrate/control_plane/scheduling/personal_admin.py`
- Lines: 140. Doc: Personal Admin — important dates, gift research,
- Classes: -
- Functions: add_important_date, get_upcoming_dates, research_gift
- Imports: datetime, dotenv, json, logging, os, substrate.self_model, zoneinfo
### `substrate/control_plane/scheduling/week_architect.py`
- Lines: 95. Doc: WeekArchitect — designs the upcoming week using the Ideal Week
- Classes: -
- Functions: architect_week, _fallback_week
- Imports: datetime, dotenv, logging, os, pathlib, zoneinfo
### `substrate/control_plane/signals/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/signals/signal_hierarchy.py`
- Lines: 250. Doc: SignalHierarchyEngine — ranks signal before the filter applies.
- Classes: SignalTier, Signal, SignalHierarchyEngine
- Functions: -
- Imports: dataclasses, enum
### `substrate/control_plane/strategy/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/control_plane/strategy/portfolio_advisor.py`
- Lines: 799. Doc: Portfolio Advisor — board-level intelligence across all companies in the portfolio.
- Classes: VentureHealth, PortfolioAdvisor
- Functions: _load_org_names
- Imports: adapters.models.agent_runtime, collections, dataclasses, datetime, json, os, pathlib, substrate.contracts.agent_types
### `substrate/control_plane/strategy/portfolio_advisor_standards.py`
- Lines: 487. Doc: Portfolio Advisor Best Practices — operational
- Classes: -
- Functions: get_capital_allocation_rules, get_portfolio_assessment_rules, get_strategic_decision_rules, get_communication_rules, get_north_star_rules, get_engagement_rules, get_all_standards
- Imports: -
### `substrate/control_plane/strategy/strategy_engine.py`
- Lines: 526. Doc: StrategyEngine — first-principles strategic reasoning layer.
- Classes: StrategyEngine, DecisionEngine
- Functions: _query_30d_stats, _parse_labeled_sections
- Imports: datetime, json, os, pathlib, substrate.contracts.agent_types, substrate.control_plane.runtime.cognitive_loop, substrate.state.business.venture_knowledge, substrate.state.context.context
### `substrate/control_plane/strategy/task_yield_matrix.py`
- Lines: 175. Doc: Task Yield Matrix — task delegation audit framework.
- Classes: -
- Functions: classify_task_yield, run_yield_audit, format_yield_report
- Imports: datetime, dotenv, json, logging, os, substrate.self_model, zoneinfo
### `substrate/execution/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/actuation/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/actuation/actuator_backend_registry_v1.py`
- Lines: 287. Doc: Actuator Backend Registry v1.
- Classes: BackendCapability, BackendEnvironment, ActuatorBackendEntry, ActuatorBackendRegistry
- Functions: get_backend_registry
- Imports: __future__, dataclasses, enum, typing
### `substrate/execution/actuation/actuator_maturity_v1.py`
- Lines: 135. Doc: Actuator Maturity Model v1.
- Classes: ActuatorMaturityLevel
- Functions: compute_maturity_level, maturity_ceiling, validate_maturity_claim, _is_truthy
- Imports: __future__, enum, typing
### `substrate/execution/actuation/observed_desktop_state_v1.py`
- Lines: 134. Doc: Observed Desktop State v1.
- Classes: ObservedDesktopStateV1
- Functions: from_relay_result
- Imports: .actuator_maturity_v1, __future__, dataclasses, datetime, json, typing
### `substrate/execution/actuation/windows_foreground_actuator_v1.py`
- Lines: 315. Doc: Windows Foreground Actuator v1 (Maturity-Aware).
- Classes: ActuatorProofRequest, ActuatorProofResult
- Functions: classify_relay_result, build_backend_selection_proof, persist_proof_artifacts
- Imports: .actuator_backend_registry_v1, .actuator_maturity_v1, .observed_desktop_state_v1, __future__, dataclasses, datetime, hashlib, json
### `substrate/execution/adapters/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/adapters/physical.py`
- Lines: 348. Doc: Physical Adapter Framework — hardware and IoT extension points.
- Classes: PhysicalDomain, PhysicalCapability, ConnectionType, PhysicalDeviceInfo, PhysicalActionResult, SensorReading, PhysicalAdapter, HomeAssistantAdapter
- Functions: build_default_registry
- Imports: __future__, abc, dataclasses, datetime, enum, logging, typing
### `substrate/execution/agents/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/agents/browser_agent.py`
- Lines: 561. Doc: BrowserAgent — Playwright-based web operator for EOS agents.
- Classes: BrowserAgent, ManusAgent, InstagramAgent
- Functions: _synthesize_findings, run_browser_task
- Imports: dotenv, json, pathlib, re
### `substrate/execution/agents/computer_use_agent.py`
- Lines: 331. Doc: Computer-Use Agent — governed visual automation across execution layers.
- Classes: AgentStatus, ActionEntry, ExecutionSlotState, ComputerUseAgent, ContainerComputerAgent, NativeComputerAgent
- Functions: -
- Imports: __future__, abc, asyncio, base64, dataclasses, enum, logging, time
### `substrate/execution/bridge/__init__.py`
- Lines: 66. Doc: execution.bridge — Lazy-import package.
- Classes: -
- Functions: _m, __getattr__
- Imports: __future__, importlib, logging, typing
### `substrate/execution/bridge/actions.py`
- Lines: 119. Doc: SafeAction schema — structured intents for future local execution.
- Classes: ActionKind, ActionStatus, SafeAction, ActionResult
- Functions: _new_id, _utcnow
- Imports: __future__, dataclasses, datetime, enum, typing, uuid
### `substrate/execution/bridge/app_allowlist.py`
- Lines: 71. Doc: App launch allow-list for LAUNCH_APP actions.
- Classes: AllowedApp
- Functions: resolve_app, is_allowed
- Imports: __future__, dataclasses
### `substrate/execution/bridge/audio_loop.py`
- Lines: 613. Doc: Audio loop — bounded local interaction-window model.
- Classes: AudioLoopStatus, TranscriptEntry, AudioLoopState, AudioLoopStore
- Functions: _log, _utcnow, _parse_iso, _new_id, get_audio_loop_store, reset_audio_loop_store_for_tests, _set_status, mark_primed, mark_listening, mark_responding, mark_cooling_down, mark_inactive
- Imports: __future__, dataclasses, datetime, enum, sys, threading, typing, uuid
### `substrate/execution/bridge/auto_task_generation.py`
- Lines: 291. Doc: Auto-task generation — bridges the perception layer to the task system.
- Classes: -
- Functions: _log, _utcnow, _candidate_title, generate_tasks_from_perceptions, run_perception_cycle, get_perception_summary
- Imports: __future__, datetime, substrate.execution.bridge.perception, sys, typing
### `substrate/execution/bridge/browser_agent.py`
- Lines: 495. Doc: Browser agent — real Playwright execution surface for the substrate.
- Classes: BrowserActionType, BrowserActionResult, BrowserAgent
- Functions: _log, _utcnow, _stream_browser_event, _stream_browser_result, get_browser_agent, execute_browser_action
- Imports: __future__, dataclasses, datetime, enum, sys, threading, time, typing
### `substrate/execution/bridge/capabilities.py`
- Lines: 81. Doc: Capability abstraction — what a node can do.
- Classes: Capability, CapabilityRegistry
- Functions: -
- Imports: __future__, enum, typing
### `substrate/execution/bridge/capability_routing.py`
- Lines: 231. Doc: Capability-aware task routing — deterministic target selection.
- Classes: TaskCapability, ExecutionTarget
- Functions: _log, infer_task_capabilities, choose_execution_target, route_task, _build_reason
- Imports: __future__, enum, re, sys, typing
### `substrate/execution/bridge/capability_tagging.py`
- Lines: 134. Doc: Capability tagging — additive pre-routing layer.
- Classes: -
- Functions: _text, _comm_type, _channel, _is_voice, _is_browser, _is_workstation, _is_long_running, tag_request
- Imports: __future__, substrate.execution.bridge.capabilities, typing
### `substrate/execution/bridge/claude_responder.py`
- Lines: 179. Doc: Claude Responder v1 — thin adapter that turns a text prompt into a reply by
- Classes: -
- Functions: session_name_for_discord_channel, _empty, respond_via_claude_session
- Imports: __future__, os, substrate.execution.bridge, typing
### `substrate/execution/bridge/claude_session_bridge.py`
- Lines: 1186. Doc: Claude Code Session Bridge v1 — persistent tmux-backed Claude Code sessions.
- Classes: ClaudeSessionTarget, ClaudeSessionInfo
- Functions: _get_session_lock, detect_tmux_available, detect_claude_cli_available, default_session_target, _current_node_id, _sanitize_session_name, _get_session_prefix, make_session_name, _validate_target, _validate_session_name, _err, _resolve_soul_doc
- Imports: __future__, dataclasses, os, re, shutil, socket, subprocess, substrate.execution.cpu_gate
### `substrate/execution/bridge/context_lifecycle.py`
- Lines: 314. Doc: Context lifecycle — pressure-aware session maintenance with checkpoint/restore.
- Classes: -
- Functions: _pressure_threshold, _guard_enabled, _log, _has_degradation_markers, detect_context_pressure, build_context_checkpoint, restore_from_checkpoint, maybe_clear_and_restore
- Imports: __future__, datetime, os, re, sys, typing
### `substrate/execution/bridge/day_workflows.py`
- Lines: 571. Doc: Day workflow coordination — open_day / close_day.
- Classes: -
- Functions: _log, _utcnow, _today_str, _start_ritual_best_effort, _advance_ritual_best_effort, open_day, close_day
- Imports: __future__, datetime, substrate.execution.bridge.operator_session, substrate.execution.bridge.rituals, sys, typing
### `substrate/execution/bridge/discord_mode_routing.py`
- Lines: 337. Doc: Discord Channel Mode Routing v1 — bounded channel→mode classification.
- Classes: -
- Functions: _parse_id_set, _flag_truthy, _norm_target, resolve_discord_mode, resolve_mode_session, current_mode_context, mode_context, clear_mode_context_for_tests
- Imports: __future__, contextlib, os, substrate.execution.bridge.claude_session_bridge, threading, typing
### `substrate/execution/bridge/discord_text_transport.py`
- Lines: 1654. Doc: Discord text transport — Pseudo-Live Voice Loop v1.
- Classes: DiscordTextEvent, _TextHistory
- Functions: _log, _utcnow_iso, _flag_truthy, _ingress_enabled, _tts_enabled, _parse_allowlist, _allowlist_permits, _reply_max_chars, truncate_reply, _record_backend, _backend_snapshot, reset_backend_state_for_tests
- Imports: __future__, dataclasses, datetime, os, substrate.execution.bridge.claude_session_bridge, substrate.execution.bridge.context_lifecycle, substrate.execution.bridge.resource_guard, substrate.execution.bridge.workload_policy
### `substrate/execution/bridge/discord_voice_playback.py`
- Lines: 652. Doc: Discord voice playback — bounded TTS adapter on top of the transport.
- Classes: PlaybackResult, _PlaybackHistory, DiscordVoicePlayback
- Functions: _log, _utcnow_iso, probe_playback_capability, get_playback_history, reset_playback_history_for_tests, _render_tts_to_wav, playback_env_enabled, normalize_playback_result
- Imports: __future__, dataclasses, datetime, os, shutil, subprocess, substrate.execution.cpu_gate, sys
### `substrate/execution/bridge/discord_voice_transport.py`
- Lines: 805. Doc: Discord voice transport — bounded adapter onto the existing voice substrate.
- Classes: DiscordTransportEvent, _TransportHistory, DiscordVoiceTransport
- Functions: _log, _utcnow_iso, _probe_discord_capability, get_transport_history, reset_transport_history_for_tests, _build_node_id, get_default_discord_voice_transport, reset_default_discord_voice_transports_for_tests, _env_hook_enabled, _playback_env_enabled, maybe_attach_discord_voice_client, maybe_mirror_discord_utterance
- Imports: __future__, dataclasses, datetime, os, sys, threading, typing
### `substrate/execution/bridge/event_spine.py`
- Lines: 207. Doc: Event Spine — unified structured event model for EOS substrate.
- Classes: EventType, EventStatus, Event
- Functions: _now_iso, _new_event_id, _content_hash, create_event
- Imports: __future__, dataclasses, enum, hashlib, time, typing, uuid
### `substrate/execution/bridge/execution_trace.py`
- Lines: 301. Doc: Execution trace for EOS request lifecycle.
- Classes: _TraceHistory
- Functions: _log, new_trace, update_trace, finalize_trace, format_trace_compact, get_trace_history, set_current_trace, get_current_trace, clear_current_trace, trace_context
- Imports: __future__, collections, contextlib, datetime, sys, threading, typing, uuid
### `substrate/execution/bridge/live_sessions.py`
- Lines: 635. Doc: Live sessions — real-time continuous interaction layer for the substrate.
- Classes: LiveSessionState, LiveSessionType, LiveSession, LiveSessionStore
- Functions: _log, _utcnow, _new_id, _get_current_day_session_id, _get_and_validate, create_live_session, start_live_session, pause_live_session, resume_live_session, end_live_session, fail_live_session, attach_task_to_live_session
- Imports: __future__, dataclasses, datetime, enum, sys, threading, typing, uuid
### `substrate/execution/bridge/local_control.py`
- Lines: 947. Doc: Local control — safe OS-level action layer for the local machine.
- Classes: LocalControlAction, LocalControlMode, RequestStatus, LocalControlRequest, LocalControlStore
- Functions: _log, _utcnow, _make_id, is_action_allowed, submit_control_request, execute_control_request, _dispatch_browser_open_url, _dispatch_browser_click, _dispatch_browser_type, _dispatch_browser_press_keys, _dispatch_browser_screenshot, _dispatch_subprocess_open_app
- Imports: __future__, dataclasses, datetime, enum, shutil, subprocess, substrate.execution.cpu_gate, sys
### `substrate/execution/bridge/local_listener.py`
- Lines: 397. Doc: Local listener — bounded wake/activation layer for the substrate.
- Classes: TriggerKind, TriggerStatus, LocalTrigger, TriggerHistory, LocalListener
- Functions: _log, _utcnow, _new_id, get_trigger_history, listener_report
- Imports: __future__, dataclasses, datetime, enum, substrate.execution.bridge.nodes, substrate.execution.bridge.ritual_body, substrate.execution.bridge.ritual_runner, substrate.execution.bridge.rituals
### `substrate/execution/bridge/meeting_types.py`
- Lines: 587. Doc: Meeting types — bounded configuration for 11 voice-meeting archetypes.
- Classes: MeetingType, MeetingConfig
- Functions: get_meeting_config, get_pre_brief, get_post_actions
- Imports: __future__, dataclasses, enum, typing
### `substrate/execution/bridge/memory_scope_contracts.py`
- Lines: 97. Doc: Memory scope contracts.
- Classes: MemoryScope, PromotionPath, MemoryScopeAssignment
- Functions: raw_account_data_default_scope, canonical_source_record_is_not_global_canon, can_promote_to_global_canon, requires_abstraction_for_global
- Imports: __future__, dataclasses, enum, typing
### `substrate/execution/bridge/mode_behavior.py`
- Lines: 260. Doc: Mode behavior shaping — post-router output shaping by substrate mode.
- Classes: -
- Functions: _log, _contains_internal_language, _strip_internal_lines, _mask_internal_refs, _enforce_builder_structure, _shape_product, shape_reply, detect_internal_leakage
- Imports: __future__, os, re, sys, typing
### `substrate/execution/bridge/node_controller.py`
- Lines: 358. Doc: NodeController — unified routing brain for task→node dispatch.
- Classes: TransportPreference, RoutingReason, RoutingDecision
- Functions: _log, _is_local_node_online, _is_http_transport_available, _is_local_available_via_presence, get_node_health_summary, route, _local_decision, _vps_decision
- Imports: __future__, dataclasses, enum, os, sys, typing
### `substrate/execution/bridge/node_transport.py`
- Lines: 291. Doc: NodeTransport — aiohttp transport adapter for local station daemon.
- Classes: NodeTransportServer
- Functions: _log, send_task_via_http, check_http_health
- Imports: __future__, sys, typing
### `substrate/execution/bridge/nodes.py`
- Lines: 246. Doc: Node abstraction — execution targets beyond "the VPS".
- Classes: NodeType, NodeRole, NodeStatus, Node, NodeRegistry
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, typing
### `substrate/execution/bridge/operator_presence.py`
- Lines: 120. Doc: Operator presence — tiny deterministic hybrid intro/outro templates.
- Classes: -
- Functions: line_for_transition, intro_for_transition
- Imports: __future__, substrate.execution.bridge.operator_state, typing
### `substrate/execution/bridge/operator_session.py`
- Lines: 300. Doc: Operator session spine — single authoritative source of truth for the
- Classes: OperatorDayMode, OperatorSession, OperatorSessionStore
- Functions: _log, _utcnow, _new_id
- Imports: __future__, dataclasses, datetime, enum, sys, threading, typing, uuid
### `substrate/execution/bridge/operator_state.py`
- Lines: 394. Doc: Operator state — bounded unified state model for the workstation operator.
- Classes: OperatorMode, OperatorTransition, OperatorState, OperatorStateStore
- Functions: _log, _utcnow, _new_id, get_operator_state_store, reset_operator_state_store_for_tests
- Imports: __future__, dataclasses, datetime, enum, sys, threading, typing, uuid
### `substrate/execution/bridge/operator_transitions.py`
- Lines: 482. Doc: Operator transitions — deterministic state transition layer.
- Classes: TransitionTrigger, TransitionDecision
- Functions: _log, _utcnow, _new_transition_id, decide_transition, _record_transition, _emit_presence_if_needed, apply_wake_event, apply_voice_session, apply_ritual
- Imports: __future__, dataclasses, datetime, substrate.execution.bridge.operator_state, sys, typing
### `substrate/execution/bridge/perception.py`
- Lines: 998. Doc: Perception layer — ambient sensing of system and environment state.
- Classes: PerceptionSource, PerceptionSeverity, PerceptionRecord, PerceptionStore
- Functions: _log, _utcnow, _now, _new_id, _make_fingerprint, collect_task_perception, collect_pipeline_perception, collect_operator_session_perception, collect_node_status_perception, collect_git_perception, collect_runtime_log_perception, collect_station_presence_perception
- Imports: __future__, dataclasses, datetime, enum, hashlib, os, subprocess, substrate.execution.cpu_gate
### `substrate/execution/bridge/pipeline_execution.py`
- Lines: 741. Doc: Pipeline execution engine — step-level execution, retry, and resume.
- Classes: -
- Functions: _log, _utcnow, _stream_step_event, _map_keyword_to_action, _detect_local_control_action, _execute_local_control_step, _execute_step, execute_pipeline, retry_step, resume_pipeline, get_pipeline_summary, format_blocked_summary
- Imports: __future__, datetime, substrate.execution.bridge.task_pipeline, sys, typing
### `substrate/execution/bridge/playback_status.py`
- Lines: 93. Doc: Shared playback status snapshot shape for voice transports.
- Classes: PlaybackStatusSnapshot
- Functions: make_playback_status_snapshot, aggregate_by_status
- Imports: __future__, dataclasses, typing
### `substrate/execution/bridge/resource_guard.py`
- Lines: 273. Doc: Resource Guard v1 — pre-execution VPS resource check.
- Classes: -
- Functions: _flag_truthy, _env_float, _parse_meminfo, _count_processes, current_resource_snapshot, evaluate_resource_guard, _guard_result
- Imports: __future__, datetime, os, typing
### `substrate/execution/bridge/result_query.py`
- Lines: 455. Doc: Result query helpers — tiny operator-facing view over the ResultStore.
- Classes: -
- Functions: _row, latest, latest_by_node, by_action_id, latest_failed, stats, latest_by_kind, node_health_summary, unresolved_rituals, station_readiness_report, recent_open_close_summaries, recent_voice_sessions
- Imports: __future__, substrate.execution.bridge.result_store, typing
### `substrate/execution/bridge/result_store.py`
- Lines: 246. Doc: ResultStore — durable index of ingested ActionResults.
- Classes: IngestedResult, ResultStore
- Functions: _log, _utcnow, get_result_store, reset_result_store_for_tests
- Imports: __future__, dataclasses, datetime, sys, threading, typing
### `substrate/execution/bridge/ritual_body.py`
- Lines: 342. Doc: Ritual body — tiny executable layer for open_day / close_day.
- Classes: RitualPolicy
- Functions: _log, _resolve_station, _record, run_open_day_body, run_close_day_body
- Imports: __future__, dataclasses, substrate.execution.bridge.actions, substrate.execution.bridge.nodes, substrate.execution.bridge.result_query, substrate.execution.bridge.ritual_inference, substrate.execution.bridge.rituals, substrate.execution.bridge.scene_policy
### `substrate/execution/bridge/ritual_inference.py`
- Lines: 199. Doc: Ritual hint inference — infer a scene hint when the operator did not
- Classes: InferredHint
- Functions: _last_successful_scene_for_node, _role_preferred_scene, infer_open_scene_hint
- Imports: __future__, dataclasses, substrate.execution.bridge.nodes, typing
### `substrate/execution/bridge/ritual_runner.py`
- Lines: 218. Doc: Ritual runner — shell-callable entry points for open_day / close_day.
- Classes: -
- Functions: _apply_ritual_state, _today_inputs, start_open_day, finish_open_day, start_close_day, finish_close_day, fail_ritual, _main
- Imports: __future__, datetime, substrate.execution.bridge.ritual_body, substrate.execution.bridge.rituals, sys
### `substrate/execution/bridge/rituals.py`
- Lines: 214. Doc: Ritual workflow scaffold — open_day / close_day.
- Classes: RitualKind, RitualState, Ritual, RitualRegistry
- Functions: _new_id, _utcnow
- Imports: __future__, dataclasses, datetime, enum, typing, uuid
### `substrate/execution/bridge/roles.py`
- Lines: 156. Doc: Agent role abstraction — clean contract for multi-agent orchestration.
- Classes: RoleScope, AgentRole, RoleRegistry
- Functions: -
- Imports: __future__, dataclasses, enum, typing
### `substrate/execution/bridge/scene_capabilities.py`
- Lines: 173. Doc: Scene → capability requirements — tiny explicit mapping.
- Classes: -
- Functions: _walk_scene, requirements_for, node_supports, scene_requirements_inventory
- Imports: __future__, substrate.execution.bridge.actions, substrate.execution.bridge.capabilities, substrate.execution.bridge.scenes, typing
### `substrate/execution/bridge/scene_policy.py`
- Lines: 244. Doc: Scene policy — deterministic mapping from (node, readiness, hint) → scene.
- Classes: SceneDecision
- Functions: _lookup_node, _capability_guarded, _resolve_classification, _normalize_hint, select_scene
- Imports: __future__, dataclasses, substrate.execution.bridge.scene_capabilities, substrate.execution.bridge.scenes, substrate.execution.bridge.station_readiness, typing
### `substrate/execution/bridge/scenes.py`
- Lines: 181. Doc: Scene registry — small, code-declared workstation bootstrap recipes.
- Classes: SceneStep, Scene
- Functions: _scene, get_scene, list_scenes
- Imports: __future__, dataclasses, os, substrate.execution.bridge.actions, typing
### `substrate/execution/bridge/session_control.py`
- Lines: 262. Doc: Session control — lifecycle commands for Claude Code tmux sessions.
- Classes: -
- Functions: _log, _auto_clear_threshold, _increment_count, _reset_count, get_message_count, reset_counters_for_tests, clear_session, reset_session, maybe_auto_clear
- Imports: __future__, os, sys, threading, typing
### `substrate/execution/bridge/session_discord_bridge.py`
- Lines: 460. Doc: Session Discord Bridge — routes SessionWatcher events to Discord and back.
- Classes: PlanApprovalView, PermissionView, QuestionOptionView, SessionDiscordBridge
- Functions: _extract_options, format_event, _resolve_channel_id, get_bridge, send_reply
- Imports: __future__, asyncio, discord, os, re, substrate.execution.bridge.claude_session_bridge, substrate.execution.bridge.session_watcher, sys
### `substrate/execution/bridge/session_watcher.py`
- Lines: 747. Doc: Session Watcher — continuous tmux state machine for Claude Code sessions.
- Classes: SessionState, WatcherEvent, SessionWatcher
- Functions: get_watcher, start_watcher, stop_watcher, stop_all_watchers, ask_session_watched
- Imports: __future__, dataclasses, enum, re, substrate.execution.bridge.claude_session_bridge, threading, time, typing
### `substrate/execution/bridge/station.py`
- Lines: 228. Doc: Station Daemon contract.
- Classes: ControlMode, StationHeartbeat, StationEvent, StationContract
- Functions: _utcnow
- Imports: __future__, dataclasses, datetime, enum, substrate.execution.bridge.actions, typing
### `substrate/execution/bridge/station_bus.py`
- Lines: 190. Doc: StationBus — MVP transport between EOS and local Station Daemons.
- Classes: StationBus
- Functions: _log, _atomic_write_json, _read_json, get_station_bus, reset_station_bus_for_tests
- Imports: __future__, json, os, pathlib, substrate.execution.bridge.actions, substrate.execution.bridge.station, sys, threading
### `substrate/execution/bridge/station_daemon.py`
- Lines: 870. Doc: StationDaemon — minimal local node execution loop.
- Classes: _HandlerOutcome, StationDaemon
- Functions: _log, _utcnow, _build_arg_parser, main, start_station_daemon
- Imports: __future__, argparse, asyncio, dataclasses, datetime, os, shutil, signal
### `substrate/execution/bridge/station_helpers.py`
- Lines: 128. Doc: Small helpers for proposing MVP SafeActions to a named station.
- Classes: -
- Functions: _contract_in_drive, propose_speak_text, propose_open_url, propose_launch_app, propose_focus_app, propose_open_scene, propose_play_sound
- Imports: __future__, substrate.execution.bridge.actions, substrate.execution.bridge.station, typing
### `substrate/execution/bridge/station_presence.py`
- Lines: 335. Doc: Station presence — unified station posture and availability state.
- Classes: StationPresenceMode, StationPresence, StationPresenceStore
- Functions: _log, _utcnow, _new_id, get_station_presence, update_station_presence, set_presence_mode, mark_local_available, mark_local_unavailable, get_station_summary
- Imports: __future__, dataclasses, datetime, enum, sys, threading, typing, uuid
### `substrate/execution/bridge/station_readiness.py`
- Lines: 306. Doc: Station readiness — derived view of whether a node is fit for ritual work.
- Classes: StationReadiness
- Functions: _utcnow, _parse_iso, _age_seconds, _count_unresolved_for_node, station_readiness, is_ready
- Imports: __future__, dataclasses, datetime, substrate.execution.bridge.nodes, substrate.execution.bridge.result_query, substrate.execution.bridge.result_store, typing
### `substrate/execution/bridge/storage.py`
- Lines: 214. Doc: Substrate storage — minimal persistence for NodeRegistry and RitualRegistry.
- Classes: SubstrateStorage, JSONFileStorage, NeonStorage
- Functions: _log, get_storage, reset_storage_for_tests
- Imports: __future__, json, os, pathlib, sys, threading, typing
### `substrate/execution/bridge/target_policy.py`
- Lines: 214. Doc: Hybrid Execution Target Policy v1 — deterministic target resolution.
- Classes: -
- Functions: _flag_truthy, _clamp_target, _mode_default, resolve_execution_target, resolve_execution_policy, should_delegate_product_to_local, _check_delegation
- Imports: __future__, os, typing
### `substrate/execution/bridge/task_decomposition.py`
- Lines: 225. Doc: Deterministic task decomposition — breaks tasks into ordered pipeline steps.
- Classes: -
- Functions: _log, infer_agent_role, _builder_steps, _product_steps, _ceo_portfolio_steps, decompose_task
- Imports: __future__, re, substrate.execution.bridge.task_pipeline, sys, typing
### `substrate/execution/bridge/task_execution.py`
- Lines: 505. Doc: Real task execution pipeline — binds tasks to tmux-backed Claude sessions.
- Classes: -
- Functions: _log, _utcnow, _resolve_tmux_target, detect_human_block, execute_task, _execute_via_pipeline, _sync_pipeline_to_task, _execute_legacy, _build_dispatch_text, run_overnight_execution
- Imports: __future__, datetime, re, substrate.execution.bridge.claude_session_bridge, substrate.execution.bridge.task_system, sys, typing
### `substrate/execution/bridge/task_pipeline.py`
- Lines: 481. Doc: Task pipeline data model — ordered multi-step execution for tasks.
- Classes: PipelineStatus, StepStatus, PipelineAgentRole, PipelineStep, TaskPipeline, PipelineStore
- Functions: _log, _utcnow, _new_pipeline_id, _new_step_id
- Imports: __future__, dataclasses, datetime, enum, sys, threading, typing, uuid
### `substrate/execution/bridge/task_queue.py`
- Lines: 245. Doc: Priority queue layer for the task system.
- Classes: TaskPriority
- Functions: _log, infer_task_priority, assign_queue, prioritize_and_queue, _priority_sort, get_ready_tasks, get_overnight_tasks, get_waiting_on_operator_tasks, get_tasks_sorted_for_execution, get_enhanced_task_summary, prepare_overnight_queue
- Imports: __future__, enum, re, substrate.execution.bridge.task_system, sys, typing
### `substrate/execution/bridge/task_system.py`
- Lines: 602. Doc: Task autonomy and overnight execution system (v1).
- Classes: TaskExecutionPolicy, TaskStatus, Task, TaskStore
- Functions: _log, _utcnow, _new_id, classify_task, create_task, process_task, run_overnight_tasks, get_task_summary
- Imports: __future__, dataclasses, datetime, enum, re, sys, threading, typing
### `substrate/execution/bridge/transcript_inject.py`
- Lines: 205. Doc: Transcript injection — the bounded entry point for text-shaped input
- Classes: -
- Functions: _log, _resolve_active_session_id, inject_transcript
- Imports: __future__, substrate.execution.bridge.voice_session, sys, typing
### `substrate/execution/bridge/tts_sanitize.py`
- Lines: 187. Doc: TTS reply sanitization — strip Claude Code / provider footer noise.
- Classes: -
- Functions: _clip, sanitize_tts_reply
- Imports: __future__, os, re
### `substrate/execution/bridge/voice_eos_responder.py`
- Lines: 339. Doc: Voice → EOS responder bridge.
- Classes: -
- Functions: _log, _system_prompt_for, _build_prompt, _record_responder_meta, _safe_fallback_text, _route_role, _eos_voice_responder, build_eos_voice_responder, install_default_eos_voice_responder, is_eos_voice_responder_installed, uninstall_eos_voice_responder
- Imports: __future__, substrate.execution.bridge.voice_session, sys, threading, typing
### `substrate/execution/bridge/voice_first.py`
- Lines: 435. Doc: Voice-first response orchestration.
- Classes: VoiceFirstResult
- Functions: _log, _utcnow, _ensure_ack_dir, _generate_ack_wav, ensure_ack_wavs, pick_ack_wav, needs_ack, voice_system_prompt, truncate_for_voice, strip_markdown, normalize_for_speech, prepare_voice_response
- Imports: __future__, asyncio, dataclasses, datetime, os, pathlib, random, subprocess
### `substrate/execution/bridge/voice_session.py`
- Lines: 790. Doc: Voice session — bounded live voice-presence layer for the substrate.
- Classes: VoiceSessionStatus, VoiceTurnSource, VoiceTurn, VoiceSession, VoiceSessionStore, VoiceSessionRuntime
- Functions: _log, _utcnow, _new_id, get_voice_session_store, reset_voice_session_store_for_tests, _default_responder, set_voice_responder, _apply_operator_state, _call_responder, voice_session_report
- Imports: __future__, dataclasses, datetime, enum, substrate.execution.bridge.nodes, substrate.execution.bridge.roles, substrate.execution.bridge.station_helpers, sys
### `substrate/execution/bridge/wake_producer.py`
- Lines: 491. Doc: Wake producer — bounded wake-word / clap activation layer for the substrate.
- Classes: WakeProducerKind, WakeProducerEvent, WakeProducerHistory, WakeProducerRuntime
- Functions: _log, _utcnow, _new_id, resolve_role_hint, get_wake_producer_history, get_wake_producer_runtime, reset_wake_producer_runtime_for_tests
- Imports: __future__, dataclasses, datetime, enum, substrate.execution.bridge.local_listener, substrate.execution.bridge.storage, substrate.execution.bridge.voice_session, sys
### `substrate/execution/bridge/workflow_delegation.py`
- Lines: 474. Doc: Workflow Delegation Layer v1 — deterministic intent classification + policy.
- Classes: -
- Functions: classify_workflow_intent, _result, _check_extra_keywords, resolve_workflow_policy, _policy_result, enrich_metadata
- Imports: __future__, os, re, typing
### `substrate/execution/bridge/workflow_execution.py`
- Lines: 362. Doc: Workflow Execution Layer v1.1 — bounded, deterministic workflow handlers.
- Classes: -
- Functions: _handle_builder_dev, _handle_product_runtime, _content_ops_prefix, _handle_content_ops, _analysis_prefix, _handle_analysis, _handle_system_ops, _resolve_handler, execute_workflow_if_allowed
- Imports: __future__, substrate.execution.bridge.workflow_delegation, typing
### `substrate/execution/bridge/workload_policy.py`
- Lines: 193. Doc: Workload Classification Policy v1 — deterministic execution weight.
- Classes: -
- Functions: classify_workload, workload_weight_order, _result
- Imports: __future__, typing
### `substrate/execution/cpu_gate.py`
- Lines: 207. Doc: Universal CPU gate — single choke point for all UMH execution paths.
- Classes: CpuGateResult
- Functions: cpu_gate_check, cpu_gate_status, gated_subprocess_run, gated_popen
- Imports: __future__, dataclasses, logging, os, subprocess, time, typing
### `substrate/execution/executor.py`
- Lines: 185. Doc: Work packet executor — the governed execution pipeline.
- Classes: AdapterProtocol, ExecutionBundle, WorkPacketExecutor
- Functions: build_default_executor
- Imports: __future__, datetime, substrate.execution.proof_generator, substrate.governance.risk_classes, substrate.types, time, typing, uuid
### `substrate/execution/feedback.py`
- Lines: 86. Doc: FeedbackCapture — captures execution quality signals.
- Classes: FeedbackCapture, ConcreteFeedbackCapture
- Functions: -
- Imports: __future__, substrate.types, typing
### `substrate/execution/feedback_loop.py`
- Lines: 492. Doc: RLHF Feedback Loop — explicit human feedback ingestion and learning cycle.
- Classes: Rating, OutcomeCategory, FeedbackEntry, FeedbackLoop
- Functions: get_feedback_loop
- Imports: __future__, dataclasses, datetime, enum, logging, substrate.state.storage.db, typing
### `substrate/execution/ingestion/__init__.py`
- Lines: 47. Doc: Canonical ingestion pipeline — substrate.execution.ingestion.
- Classes: -
- Functions: -
- Imports: substrate.understanding.domains.contract, substrate.understanding.ontology.primitive_decomposition_v1, substrate.understanding.perception.orchestrator, substrate.understanding.perception.source
### `substrate/execution/loop/__init__.py`
- Lines: 18. Doc: Persistent execution loops — config-driven autonomous cycles for UMH.
- Classes: -
- Functions: -
- Imports: substrate.execution.loop.persistent_loop, substrate.execution.loop.stages
### `substrate/execution/loop/execution_loop.py`
- Lines: 329. Doc: ExecutionLoop — closed-loop goal execution with outcome feedback.
- Classes: ExecutionResult, Executor, Planner, PassthroughPlanner, NoOpExecutor, CycleResult, ExecutionLoop
- Functions: _safe_serialize
- Imports: __future__, argparse, dataclasses, datetime, json, os, substrate.control_plane.goals.goal_selector, substrate.types
### `substrate/execution/loop/persistent_loop.py`
- Lines: 408. Doc: PersistentLoop — config-driven runtime loops for UMH.
- Classes: LoopState, CycleReport, LoopDefinition, PersistentLoop, LoopRegistry
- Functions: _root, _heartbeat_dir, _definitions_path, register_stage, stage, get_registry
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, pathlib
### `substrate/execution/loop/stages.py`
- Lines: 275. Doc: Built-in loop stages — composable pipeline steps for persistent loops.
- Classes: -
- Functions: signal_drain, actionable_scan, goal_execution, feedback_collection, health_check, research_topic_select, research_execute, world_model_store, staleness_scan
- Imports: __future__, datetime, json, logging, os, pathlib, substrate.execution.loop.persistent_loop, typing
### `substrate/execution/mastery_gate.py`
- Lines: 152. Doc: Mastery Gate — mandatory pipeline check before execution.
- Classes: MasteryGateResult, MasteryGate
- Functions: _load_pack
- Imports: __future__, dataclasses, logging, pathlib, substrate.composition.mastery.management.mastery_assurance, substrate.composition.mastery.management.tool_mastery_resolver, typing
### `substrate/execution/media/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/media/media_processor.py`
- Lines: 348. Doc: MediaProcessor — unified multimodal file handler.
- Classes: MediaProcessor
- Functions: -
- Imports: base64, dotenv, os, pathlib, subprocess, substrate.execution.cpu_gate, tempfile
### `substrate/execution/pipeline.py`
- Lines: 555. Doc: ExecutionPipeline — the master success loop.
- Classes: PipelineResult, ExecutionPipeline
- Functions: -
- Imports: __future__, pydantic, substrate.execution.executor, substrate.execution.mastery_gate, substrate.execution.understanding_bridge, substrate.governance.policy_engine, substrate.governance.risk_classes, substrate.governance.validation.completeness_engine
### `substrate/execution/proof_generator.py`
- Lines: 102. Doc: Proof generator — creates verifiable proof artifacts from execution results.
- Classes: ProofGenerator
- Functions: _summarize_output
- Imports: __future__, datetime, substrate.types, typing, uuid
### `substrate/execution/queue.py`
- Lines: 81. Doc: Execution queue — ordered, priority-aware queue for work packets.
- Classes: _QueueEntry, ExecutionQueue
- Functions: -
- Imports: __future__, dataclasses, heapq, substrate.types, typing, uuid
### `substrate/execution/runtime/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/runtime/capability_router.py`
- Lines: 611. Doc: capability_router — Intent-driven tool selection for UMH.
- Classes: Capability, ProviderEntry, CapabilityResult
- Functions: _track, _codex_review_provider, _codex_exec_provider, _cc_sdk_provider, _hermes_provider, _opencode_provider, _perplexity_provider, _gemini_provider, _build_chains, _get_chains, detect_capability, _normalize_result
- Imports: dataclasses, enum, logging, re, time, typing
### `substrate/execution/runtime/execution_contracts_v1.py`
- Lines: 569. Doc: Execution Contracts v1 for the canonical runtime spine.
- Classes: SignalSource, IntentType, CapabilityDomain, GovernanceVerdict, SpineOutcome, ExecutionMode, ExecutionSignal, InterpretedIntent
- Functions: _now_iso, _new_id, _deterministic_id, _content_hash
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, substrate.types, typing
### `substrate/execution/runtime/execution_spine.py`
- Lines: 229. Doc: ExecutionSpine — single execution path for all EOS operations (legacy runtime).
- Classes: ExecutionSpine
- Functions: _deterministic_response
- Imports: datetime, os, re, substrate.execution.spine, sys, uuid
### `substrate/execution/runtime/live_local_runtime_execution_v1.py`
- Lines: 465. Doc: Live Local Runtime Execution v1 for the UMH substrate layer.
- Classes: ExecutionSpineOutcome, ExecutionSpineResult, LiveLocalRuntimeExecution
- Functions: -
- Imports: .local_runtime_supervisor_v1, .node_sync_gate_v1, .runtime_dispatch_queue_v1, .runtime_execution_result_v1, .runtime_recovery_v1, .runtime_session_registry_v1, __future__, dataclasses
### `substrate/execution/runtime/local_runtime_supervisor_v1.py`
- Lines: 616. Doc: Local Runtime Supervisor v1 for the UMH substrate layer.
- Classes: SupervisorState, SupervisorStatus, LocalRuntimeSupervisor
- Functions: -
- Imports: .runtime_dispatch_queue_v1, .runtime_execution_result_v1, .runtime_heartbeat_v1, .runtime_presence_state_v1, .runtime_recovery_v1, .runtime_session_registry_v1, __future__, dataclasses
### `substrate/execution/runtime/node_sync_gate_v1.py`
- Lines: 671. Doc: Node Sync Gate v1 for the UMH substrate layer.
- Classes: SyncStatus, SyncDecision, SyncPolicy, RuntimeCodeHash, NodeSyncState, NodeVersionReport, SyncProof, NodeSyncGateResult
- Functions: compute_file_hash, get_git_head_commit, check_git_dirty, count_commits_behind_ahead
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, os, pathlib
### `substrate/execution/runtime/runtime_bootstrap_state_v1.py`
- Lines: 261. Doc: Runtime Bootstrap State v1.
- Classes: BootstrapStage, BootstrapValidation, RuntimeBootstrapStateV1
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, os, pathlib
### `substrate/execution/runtime/runtime_dispatch_queue_v1.py`
- Lines: 196. Doc: Runtime Dispatch Queue v1 for the UMH substrate layer.
- Classes: DispatchStatus, DispatchRecord, RuntimeDispatchQueue
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, pathlib, typing
### `substrate/execution/runtime/runtime_execution_result_v1.py`
- Lines: 139. Doc: Runtime Execution Result v1 — proof-bearing execution result type.
- Classes: ExecutionOutcome, ProofArtifactType, ProofArtifact, RuntimeExecutionResult
- Functions: persist_execution_result
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, pathlib, typing
### `substrate/execution/runtime/runtime_heartbeat_v1.py`
- Lines: 124. Doc: Runtime Heartbeat v1 for the UMH substrate layer.
- Classes: HeartbeatHealth, RuntimeHeartbeat
- Functions: evaluate_heartbeat_health, write_runtime_heartbeat, read_runtime_heartbeat
- Imports: __future__, dataclasses, datetime, enum, json, pathlib, typing
### `substrate/execution/runtime/runtime_presence_state_v1.py`
- Lines: 74. Doc: Runtime Presence State v1 — workstation presence tracking.
- Classes: WorkstationPresenceState, WorkstationPresence
- Functions: is_execution_capable
- Imports: __future__, datetime, enum, logging
### `substrate/execution/runtime/runtime_recovery_v1.py`
- Lines: 223. Doc: Runtime Recovery v1 for the UMH substrate layer.
- Classes: FailureType, RecoveryStrategy, FailureRecord, RecoveryDecision, RuntimeRecoveryEngine
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, typing, uuid
### `substrate/execution/runtime/runtime_session_registry_v1.py`
- Lines: 164. Doc: Runtime Session Registry v1 for the UMH substrate layer.
- Classes: RuntimeMode, RuntimeHealth, RuntimeSession, RuntimeSessionRegistry
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, typing, uuid
### `substrate/execution/runtime/substrate_continuity_engine_v1.py`
- Lines: 296. Doc: Substrate Continuity Engine v1.
- Classes: SubstrateContinuityEngine
- Functions: -
- Imports: .continuity_classification_engine_v1, .continuity_summary_engine_v1, .open_loop_registry_v1, .runtime_cognition_contracts_v1, .runtime_continuity_store_v1, .runtime_memory_governance_bridge_v1, .runtime_resume_packet_v1, __future__
### `substrate/execution/runtime/worker_runtime_contracts.py`
- Lines: 141. Doc: Worker runtime contracts for the UMH substrate layer.
- Classes: EnvironmentType, AuthorityDomain, MessageBusType, ProofStatus, EnvironmentAuthorityDescriptor, WorkerRuntimeDescriptor, WorkerHeartbeat, RuntimeProofRecord
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, typing
### `substrate/execution/runtime/worker_supervisor_v1.py`
- Lines: 399. Doc: Worker Supervisor v1 for the UMH substrate layer.
- Classes: WorkerType, WorkerHealthStatus, AutostartDecision, RecoveryAction, WorkerHealthCheck, WorkerStartupPlan, WorkerProcessRef, WorkerAutostartPolicy
- Functions: -
- Imports: .worker_runtime_contracts, __future__, dataclasses, datetime, enum, typing, uuid
### `substrate/execution/runtime/workpacket_execution_gate_v1.py`
- Lines: 660. Doc: WorkPacket Execution Gate v1 for the UMH substrate layer.
- Classes: GateVerdict, GateDenialCategory, EnvironmentReadiness, RuntimeReadiness, AdapterReadiness, ProofReadiness, ExecutionReadiness, RuntimeExecutionRequest
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, pathlib, substrate.governance.policy.execution_authority_engine_v1
### `substrate/execution/spine.py`
- Lines: 523. Doc: ExecutionSpine — the 8-stage execution pipeline.
- Classes: ExecutionSpine, ConcreteExecutionSpine
- Functions: -
- Imports: __future__, asyncio, datetime, json, pathlib, re, substrate.observability.error_recorder, substrate.types
### `substrate/execution/trace.py`
- Lines: 127. Doc: TraceRecorder — records execution traces for every signal lifecycle.
- Classes: TraceRecorder, ConcreteTraceRecorder
- Functions: -
- Imports: __future__, json, os, substrate.types, sys, typing, uuid
### `substrate/execution/understanding_bridge.py`
- Lines: 312. Doc: Understanding Bridge — wires the understanding layer into the execution pipeline.
- Classes: UnderstandingContext, UnderstandingBridge
- Functions: -
- Imports: __future__, dataclasses, hashlib, json, logging, substrate.ontology.laws, substrate.reality_model.canonical, substrate.reality_model.instance
### `substrate/execution/voice/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/voice/session.py`
- Lines: 235. Doc: Voice Session — end-to-end voice pipeline loop.
- Classes: SessionStatus, VoiceExchange, SessionState, VoiceSession
- Functions: -
- Imports: __future__, dataclasses, enum, logging, pathlib, substrate.execution.voice.voice_engine, tempfile, time
### `substrate/execution/voice/voice_engine.py`
- Lines: 632. Doc: VoiceEngine — intelligent voice layer for Discord.
- Classes: SpeechClassification, IntelligentVoiceProcessor, VADProcessor, VoiceEngine
- Functions: -
- Imports: collections, datetime, os, pathlib, subprocess, substrate.execution.cpu_gate, tempfile, wave
### `substrate/execution/workers/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/workers/workstation/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/execution/workers/workstation/adapter_autogeneration_engine_v1.py`
- Lines: 993. Doc: Adapter Autogeneration Engine v1.
- Classes: ReplayContract, GovernanceClassification, AdapterBlueprint, MaturityEvaluation, AdapterAutogenEvidence, AdapterAutogenProof
- Functions: _now_iso, _resolve_adapter_platform, _build_replay_path, _build_evidence_requirements, _build_rollback_conditions, _determine_risk_level, _determine_relationship_strategy, generate_blueprint_for_platform, generate_blueprints_from_topology, classify_blueprint_scope, classify_extraction_scope, compute_adapter_maturity
- Imports: .environment_mapping_engine_v1, __future__, dataclasses, datetime, hashlib, json, os, pathlib
### `substrate/execution/workers/workstation/adaptive_governance_intelligence_engine_v1.py`
- Lines: 1351. Doc: Adaptive Governance Intelligence Engine v1.
- Classes: GovernanceIntegrityIntelligence, OrchestrationIntelligence, ContinuityIntelligence, EpistemicIntelligence, GovernanceProposal, AdaptiveRiskScores, PolicySimulationOutcome, GovernanceLearningMemory
- Functions: _now_iso, build_governance_integrity, build_orchestration_intelligence, build_continuity_intelligence, build_epistemic_intelligence, compute_adaptive_risk, generate_governance_proposals, simulate_policy_changes, build_governance_learning_memory, compute_governance_intelligence_maturity, _check_gi_evidence, governance_intelligence_maturity_ceiling
- Imports: .governed_recursive_orchestration_engine_v1, .persistent_substrate_continuity_engine_v1, .recursive_capability_planning_engine_v1, __future__, dataclasses, datetime, hashlib, json
### `substrate/execution/workers/workstation/browser_continuity_bridge_v1.py`
- Lines: 276. Doc: Browser Continuity Bridge v1.
- Classes: BrowserContinuityBridge
- Functions: -
- Imports: .browser_gui_contracts_v1, __future__, json, pathlib, typing
### `substrate/execution/workers/workstation/browser_execution_orchestrator_v1.py`
- Lines: 226. Doc: Browser Execution Orchestrator v1.
- Classes: BrowserExecutionOrchestrator
- Functions: -
- Imports: .browser_continuity_bridge_v1, .browser_gui_contracts_v1, .browser_observability_pipeline_v1, .browser_operational_modes_v1, .governed_browser_adapter_v1, .visible_gui_adapter_v1, __future__, typing
### `substrate/execution/workers/workstation/browser_gui_contracts_v1.py`
- Lines: 511. Doc: Browser and GUI Embodiment Contracts v1.
- Classes: BrowserActionType, BrowserActionVerdict, BrowserExecutionOutcome, BrowserOperationalMode, NavigationScope, GUIWindowState, BrowserState, BrowserSession
- Functions: _now_iso, _new_id, _deterministic_id, _content_hash
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, typing, uuid
### `substrate/execution/workers/workstation/browser_gui_embodiment_engine_v1.py`
- Lines: 246. Doc: Browser and GUI Embodiment Engine v1.
- Classes: BrowserGUIEmbodimentEngine
- Functions: -
- Imports: .browser_continuity_bridge_v1, .browser_execution_orchestrator_v1, .browser_gui_contracts_v1, .browser_observability_pipeline_v1, .browser_operational_modes_v1, .browser_replay_validator_v1, .governed_browser_adapter_v1, .visible_gui_adapter_v1
### `substrate/execution/workers/workstation/browser_observability_pipeline_v1.py`
- Lines: 154. Doc: Browser Observability Pipeline v1.
- Classes: BrowserObservabilityPipeline
- Functions: -
- Imports: .browser_gui_contracts_v1, __future__, json, pathlib, typing
### `substrate/execution/workers/workstation/browser_operational_modes_v1.py`
- Lines: 238. Doc: Browser Operational Modes v1.
- Classes: BrowserModeDefinition
- Functions: _is_local_url, _is_internal_url, _is_approved_domain, get_browser_mode_definition, get_all_browser_modes
- Imports: .browser_gui_contracts_v1, __future__, dataclasses, typing
### `substrate/execution/workers/workstation/browser_replay_validator_v1.py`
- Lines: 260. Doc: Browser Replay Validator v1.
- Classes: BrowserReplayCheck, BrowserReplayResult, BrowserReplaySessionResult, BrowserReplayValidator
- Functions: -
- Imports: .browser_gui_contracts_v1, .browser_operational_modes_v1, .governed_browser_adapter_v1, __future__, dataclasses, json, pathlib, typing
### `substrate/execution/workers/workstation/constitutional_antifragility_resilience_engine_v1.py`
- Lines: 1242. Doc: Constitutional Antifragility and Evolutionary Resilience v1.
- Classes: ResiliencePrimitive, ResiliencePrimitiveSet, CatastrophicScenario, CatastropheSimulationAnalysis, AntifragilityDimension, AntifragilityAnalysis, EvolutionaryResilienceForecast, EvolutionaryResilienceAnalysis
- Functions: _upstream_tolerance, build_resilience_primitives, build_catastrophe_simulation, build_antifragility_analysis, build_evolutionary_resilience, build_existential_risk_analysis, build_resilience_topology, build_resilience_adaptations, enforce_resilience_hard_ceilings, compute_resilience_maturity, resilience_maturity_ceiling, classify_resilience_maturity
- Imports: .adaptive_governance_intelligence_engine_v1, .constitutional_epistemic_intelligence_engine_v1, .constitutional_identity_continuity_engine_v1, .constitutional_resource_economics_engine_v1, .constitutional_strategic_intelligence_engine_v1, .constitutional_substrate_governance_layer_v1, .constitutional_telos_alignment_engine_v1, .distributed_constitutional_substrate_federation_v1
### `substrate/execution/workers/workstation/constitutional_epistemic_intelligence_engine_v1.py`
- Lines: 1513. Doc: Constitutional Epistemic Intelligence and Reality Coherence Engine v1.
- Classes: EpistemicPrimitive, EpistemicPrimitiveSet, EvidenceIntegrityResult, EvidenceIntegrityAnalysis, RealityCoherenceDetection, RealityCoherenceAnalysis, ProbabilisticAssessment, ProbabilisticReasoningSet
- Functions: build_epistemic_primitives, build_evidence_integrity, build_reality_coherence, build_probabilistic_reasoning, build_contradiction_analysis, build_epistemic_topology, build_epistemic_adaptations, enforce_epistemic_hard_ceilings, compute_epistemic_maturity, epistemic_maturity_ceiling, classify_epistemic_maturity, build_full_epistemic_proof
- Imports: .adaptive_governance_intelligence_engine_v1, .constitutional_resource_economics_engine_v1, .constitutional_strategic_intelligence_engine_v1, .constitutional_substrate_governance_layer_v1, .distributed_constitutional_substrate_federation_v1, .governed_recursive_orchestration_engine_v1, .persistent_substrate_continuity_engine_v1, .recursive_capability_planning_engine_v1
### `substrate/execution/workers/workstation/constitutional_identity_continuity_engine_v1.py`
- Lines: 1495. Doc: Constitutional Identity Continuity and Sovereign Memory Architecture v1.
- Classes: IdentityPrimitive, IdentityPrimitiveSet, SovereignMemoryLayer, SovereignMemoryAnalysis, NarrativeContinuityDimension, NarrativeContinuityAnalysis, IdentityDriftDetection, IdentityDriftAnalysis
- Functions: build_identity_primitives, build_sovereign_memory, build_narrative_continuity, build_identity_drift, build_historical_reconciliation, build_temporal_topology, build_identity_adaptations, enforce_identity_hard_ceilings, compute_identity_maturity, identity_maturity_ceiling, classify_identity_maturity, build_full_identity_proof
- Imports: .adaptive_governance_intelligence_engine_v1, .constitutional_epistemic_intelligence_engine_v1, .constitutional_resource_economics_engine_v1, .constitutional_strategic_intelligence_engine_v1, .constitutional_substrate_governance_layer_v1, .distributed_constitutional_substrate_federation_v1, .governed_recursive_orchestration_engine_v1, .persistent_substrate_continuity_engine_v1
### `substrate/execution/workers/workstation/constitutional_resource_economics_engine_v1.py`
- Lines: 1263. Doc: Constitutional Resource Economics and Coordination Engine v1.
- Classes: NodeResourceProfile, FederationResourceGraph, ExecutionEconomicsScores, DelegationPath, DelegationTopology, DegradedModeStatus, ScarcitySimulationOutcome, EconomicsEvidence
- Functions: _now_iso, build_resource_graph, compute_execution_economics, build_delegation_topology, build_degraded_mode_status, enforce_economics_hard_ceilings, run_scarcity_simulations, compute_economics_maturity, economics_maturity_ceiling, classify_economics_maturity, build_full_economics_proof, persist_economics_proof
- Imports: .adaptive_governance_intelligence_engine_v1, .constitutional_substrate_governance_layer_v1, .distributed_constitutional_substrate_federation_v1, .governed_recursive_orchestration_engine_v1, .persistent_substrate_continuity_engine_v1, .recursive_capability_planning_engine_v1, __future__, dataclasses
### `substrate/execution/workers/workstation/constitutional_strategic_intelligence_engine_v1.py`
- Lines: 1853. Doc: Constitutional Strategic Intelligence and Recursive Leverage Planning Engine v1.
- Classes: StrategicForecast, StrategicForecastSet, LeverageChain, RecursiveLeverageModel, BottleneckPrediction, BottleneckForecastSet, HorizonSimulationOutcome, StrategicSequenceItem
- Functions: _now_iso, build_strategic_forecasts, build_recursive_leverage_model, build_bottleneck_predictions, run_long_horizon_simulations, build_strategic_sequence, build_strategic_topology, build_strategic_adaptations, enforce_strategic_hard_ceilings, compute_strategy_maturity, strategy_maturity_ceiling, classify_strategy_maturity
- Imports: .adaptive_governance_intelligence_engine_v1, .constitutional_resource_economics_engine_v1, .constitutional_substrate_governance_layer_v1, .distributed_constitutional_substrate_federation_v1, .governed_recursive_orchestration_engine_v1, .persistent_substrate_continuity_engine_v1, .recursive_capability_planning_engine_v1, __future__
### `substrate/execution/workers/workstation/constitutional_substrate_governance_layer_v1.py`
- Lines: 1560. Doc: Constitutional Substrate Governance Layer v1.
- Classes: ConstitutionalSafetyInvariantStatus, ConstitutionalAuthorityBoundaryStatus, ConstitutionalContinuityContractStatus, ConstitutionalEmergencyGovernanceStatus, ConstitutionalIntegrityResult, ConstitutionalMutationClassification, ConstitutionalRiskScores, ConstitutionalGovernanceContract
- Functions: _now_iso, build_safety_invariants, build_authority_boundaries, build_continuity_contracts, build_emergency_governance, validate_constitutional_integrity, classify_mutation, compute_constitutional_risk, build_governance_contracts, enforce_hard_ceilings, run_constitutional_simulations, build_migration_contract
- Imports: .adaptive_governance_intelligence_engine_v1, .governed_recursive_orchestration_engine_v1, .persistent_substrate_continuity_engine_v1, .recursive_capability_planning_engine_v1, __future__, dataclasses, datetime, hashlib
### `substrate/execution/workers/workstation/constitutional_telos_alignment_engine_v1.py`
- Lines: 1382. Doc: Constitutional Telos Alignment and Purpose Governance v1.
- Classes: TelosPrimitive, TelosPrimitiveSet, MissionContinuityDimension, MissionContinuityAnalysis, OptimizationDirectionDetection, OptimizationDirectionAnalysis, ValueHierarchyEntry, ValueHierarchyAnalysis
- Functions: build_telos_primitives, build_mission_continuity, build_optimization_direction, build_value_hierarchy, build_purpose_conflicts, build_alignment_topology, build_telos_adaptations, enforce_telos_hard_ceilings, compute_telos_maturity, telos_maturity_ceiling, classify_telos_maturity, build_full_telos_proof
- Imports: .adaptive_governance_intelligence_engine_v1, .constitutional_epistemic_intelligence_engine_v1, .constitutional_identity_continuity_engine_v1, .constitutional_resource_economics_engine_v1, .constitutional_strategic_intelligence_engine_v1, .constitutional_substrate_governance_layer_v1, .distributed_constitutional_substrate_federation_v1, .governed_recursive_orchestration_engine_v1
### `substrate/execution/workers/workstation/distributed_constitutional_substrate_federation_v1.py`
- Lines: 1445. Doc: Distributed Constitutional Substrate Federation v1.
- Classes: FederatedNode, FederatedNodeRegistry, FederatedReplayCoordination, FederatedContinuityCoordination, FederatedConstitutionalGovernance, FederationTrustScores, FederationDriftSignal, FederatedEmergencyGovernance
- Functions: _now_iso, build_node_registry, build_replay_coordination, build_continuity_coordination, build_constitutional_governance, compute_federation_trust, detect_federation_drift, build_emergency_governance, enforce_federation_hard_ceilings, run_federation_simulations, compute_federation_maturity, federation_maturity_ceiling
- Imports: .adaptive_governance_intelligence_engine_v1, .constitutional_substrate_governance_layer_v1, .governed_recursive_orchestration_engine_v1, .persistent_substrate_continuity_engine_v1, .recursive_capability_planning_engine_v1, __future__, dataclasses, datetime
### `substrate/execution/workers/workstation/environment_mapping_engine_v1.py`
- Lines: 1125. Doc: Environment Mapping Engine v1.
- Classes: DiscoveredPlatform, DiscoveredAccount, DiscoveredWorkspace, RelationshipEdge, IngestionLane, EnvironmentTopology, EnvironmentMappingEvidence, EnvironmentMappingProof
- Functions: _now_iso, classify_platform_type, extract_platforms_from_process_list, extract_platforms_from_installed_apps, extract_accounts_from_chrome_profiles, extract_accounts_from_browser_sessions, synthesize_relationships, plan_ingestion_lanes, compute_environment_maturity, environment_maturity_ceiling, classify_environment_mapping, extract_mapping_evidence
- Imports: __future__, dataclasses, datetime, hashlib, json, os, pathlib, substrate.execution.actuation.actuator_maturity_v1
### `substrate/execution/workers/workstation/foreground_cu_ingestion_execution_v1.py`
- Lines: 576. Doc: Foreground CU Ingestion Execution v1.
- Classes: CUIngestionEvidence, IngestionCandidate, CUIngestionProof
- Functions: _now_iso, extract_ingestion_evidence, compute_ingestion_maturity, ingestion_maturity_ceiling, classify_candidate_type, generate_candidates_from_extraction, classify_cu_ingestion, build_full_ingestion_proof, persist_cu_ingestion_proof, send_ingest_safe_doc_request
- Imports: __future__, dataclasses, datetime, hashlib, json, os, pathlib, substrate.execution.actuation.actuator_maturity_v1
### `substrate/execution/workers/workstation/governed_browser_adapter_v1.py`
- Lines: 451. Doc: Governed Browser Adapter v1.
- Classes: BrowserGovernanceDecision, GovernedBrowserAdapter
- Functions: -
- Imports: .browser_gui_contracts_v1, .browser_operational_modes_v1, __future__, dataclasses, time, typing
### `substrate/execution/workers/workstation/governed_recursive_orchestration_engine_v1.py`
- Lines: 1465. Doc: Governed Recursive Orchestration Engine v1.
- Classes: DAGNode, OrchestrationDAG, BlastRadius, RollbackPlan, SimulationOutcome, OrchestrationEvidence, OrchestrationProof
- Functions: _now_iso, _detect_cycles, _topological_sort, _assign_waves, build_execution_dag, build_dependency_dag, build_governance_dag, build_rollback_dag, build_replay_dag, build_maturity_dag, build_infrastructure_mutation_dag, build_all_dags
- Imports: .environment_mapping_engine_v1, .recursive_capability_planning_engine_v1, __future__, dataclasses, datetime, hashlib, json, os
### `substrate/execution/workers/workstation/governed_shell_adapter_v1.py`
- Lines: 382. Doc: Governed Shell Adapter v1.
- Classes: ShellGovernanceDecision, GovernedShellAdapter
- Functions: -
- Imports: .workstation_contracts_v1, .workstation_operational_modes_v1, __future__, dataclasses, shlex, subprocess, substrate.execution.cpu_gate, time
### `substrate/execution/workers/workstation/persistent_substrate_continuity_engine_v1.py`
- Lines: 1470. Doc: Persistent Substrate Continuity Engine v1.
- Classes: ExecutionLineageEntry, ExecutionContinuityMemory, MaturityTransition, CapabilityContinuityMemory, TopologyContinuityMemory, EpistemicContinuityMemory, SubstrateSnapshot, DriftSignal
- Functions: _now_iso, build_execution_continuity, build_capability_continuity, build_topology_continuity, build_epistemic_continuity, build_substrate_snapshot, detect_drift, build_continuity_lineage, replay_orchestration_history, replay_maturity_evolution, replay_drift_emergence, validate_replay_continuity
- Imports: .governed_recursive_orchestration_engine_v1, .recursive_capability_planning_engine_v1, __future__, dataclasses, datetime, hashlib, json, os
### `substrate/execution/workers/workstation/recursive_capability_planning_engine_v1.py`
- Lines: 1314. Doc: Recursive Capability Planning Engine v1.
- Classes: CapabilityNode, LeverageScore, Bottleneck, UpgradeProposal, CapabilityGraph, CapabilityPlanningEvidence, CapabilityPlanningProof
- Functions: _now_iso, _compute_dependents, build_capability_graph, analyze_bottlenecks, score_upgrade, generate_upgrade_proposals, analyze_registries, analyze_proof_artifacts, analyze_governance_surface, find_infrastructure_reuse, compute_capability_maturity, _check_evidence
- Imports: .adapter_autogeneration_engine_v1, .environment_mapping_engine_v1, __future__, dataclasses, datetime, hashlib, json, os
### `substrate/execution/workers/workstation/relay_execution_transport_v1.py`
- Lines: 286. Doc: Relay Execution Transport v1.
- Classes: RelayTransportResult
- Functions: _now_iso, _log, _ssh_cmd, _run_ssh, check_ssh_reachable, check_relay_inbox_exists, write_request_to_relay, write_request_via_scp, poll_relay_result, send_and_wait, send_chrome_proof_request, send_ping_request
- Imports: __future__, dataclasses, datetime, json, os, pathlib, subprocess, substrate.execution.cpu_gate
### `substrate/execution/workers/workstation/tmux_operational_adapter_v1.py`
- Lines: 267. Doc: Tmux Operational Adapter v1.
- Classes: TmuxGovernanceDecision, TmuxOperationalAdapter
- Functions: _run_tmux
- Imports: .governed_shell_adapter_v1, .workstation_contracts_v1, .workstation_operational_modes_v1, __future__, dataclasses, subprocess, substrate.execution.cpu_gate, time
### `substrate/execution/workers/workstation/visible_actuation_proof_v1.py`
- Lines: 286. Doc: Visible Actuation Proof v1.
- Classes: VisibleActuationEvidence, VisibleActuationProof, FounderConfirmationArtifact
- Functions: classify_visible_actuation, extract_evidence_from_relay_result, persist_visible_actuation_proof, persist_founder_confirmation
- Imports: __future__, dataclasses, datetime, hashlib, json, os, pathlib, substrate.execution.actuation.actuator_maturity_v1
### `substrate/execution/workers/workstation/visible_gui_adapter_v1.py`
- Lines: 283. Doc: Visible GUI Adapter v1.
- Classes: GUIGovernanceDecision, VisibleGUIAdapter
- Functions: -
- Imports: .browser_gui_contracts_v1, .browser_operational_modes_v1, __future__, dataclasses, subprocess, substrate.execution.cpu_gate, time, typing
### `substrate/execution/workers/workstation/workstation_continuity_bridge_v1.py`
- Lines: 307. Doc: Workstation Continuity Bridge v1.
- Classes: WorkstationContinuityBridge
- Functions: -
- Imports: .workstation_contracts_v1, __future__, json, pathlib, typing
### `substrate/execution/workers/workstation/workstation_contracts_v1.py`
- Lines: 486. Doc: Workstation Contracts v1 for operational embodiment.
- Classes: WorkstationRole, ConnectivityStatus, OperationalMode, ShellCommandVerdict, WorkstationExecutionOutcome, WorkstationState, WorkstationSession, WorkstationEnvironment
- Functions: _now_iso, _new_id, _deterministic_id, _content_hash
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, typing, uuid
### `substrate/execution/workers/workstation/workstation_execution_orchestrator_v1.py`
- Lines: 190. Doc: Workstation Execution Orchestrator v1.
- Classes: WorkstationExecutionOrchestrator
- Functions: -
- Imports: .governed_shell_adapter_v1, .tmux_operational_adapter_v1, .workstation_continuity_bridge_v1, .workstation_contracts_v1, .workstation_observability_pipeline_v1, .workstation_operational_modes_v1, __future__, typing
### `substrate/execution/workers/workstation/workstation_node_registry_v1.py`
- Lines: 109. Doc: Workstation Node Registry v1.
- Classes: WorkstationNodeRegistry
- Functions: -
- Imports: .workstation_relay_heartbeat_v1, .workstation_relay_node_v1, __future__, datetime, json, os, pathlib, substrate.execution.runtime.runtime_heartbeat_v1
### `substrate/execution/workers/workstation/workstation_observability_pipeline_v1.py`
- Lines: 135. Doc: Workstation Observability Pipeline v1.
- Classes: WorkstationObservabilityPipeline
- Functions: -
- Imports: .workstation_contracts_v1, __future__, json, pathlib, typing
### `substrate/execution/workers/workstation/workstation_operational_embodiment_engine_v1.py`
- Lines: 317. Doc: Workstation Operational Embodiment Engine v1.
- Classes: WorkstationOperationalEmbodimentEngine
- Functions: -
- Imports: .governed_shell_adapter_v1, .tmux_operational_adapter_v1, .workstation_continuity_bridge_v1, .workstation_contracts_v1, .workstation_execution_orchestrator_v1, .workstation_observability_pipeline_v1, .workstation_operational_modes_v1, .workstation_replay_validator_v1
### `substrate/execution/workers/workstation/workstation_operational_modes_v1.py`
- Lines: 211. Doc: Workstation Operational Modes v1.
- Classes: ModeDefinition
- Functions: get_mode_definition, get_all_modes
- Imports: .workstation_contracts_v1, __future__, dataclasses, typing
### `substrate/execution/workers/workstation/workstation_relay_heartbeat_v1.py`
- Lines: 159. Doc: Workstation Relay Heartbeat v1.
- Classes: RelayHeartbeat
- Functions: write_relay_heartbeat, read_relay_heartbeat, evaluate_relay_health, is_relay_online
- Imports: __future__, dataclasses, datetime, json, os, pathlib, substrate.execution.runtime.runtime_heartbeat_v1, typing
### `substrate/execution/workers/workstation/workstation_relay_node_v1.py`
- Lines: 131. Doc: Workstation Relay Node v1.
- Classes: WorkstationRelayNode
- Functions: load_relay_node_from_heartbeat
- Imports: __future__, dataclasses, datetime, hashlib, json, pathlib, typing
### `substrate/execution/workers/workstation/workstation_relay_proof_v1.py`
- Lines: 98. Doc: Workstation Relay Proof v1.
- Classes: -
- Functions: classify_relay_proof, persist_relay_proof, compute_proof_hash
- Imports: __future__, datetime, hashlib, json, os, pathlib, substrate.execution.actuation.actuator_maturity_v1, substrate.execution.actuation.observed_desktop_state_v1
### `substrate/execution/workers/workstation/workstation_relay_self_heal_v1.py`
- Lines: 161. Doc: Workstation Relay Self-Heal v1.
- Classes: RelayHealthReport
- Functions: read_autostart_marker, compute_heartbeat_age, assess_relay_health, should_allow_chrome_proof
- Imports: .workstation_relay_heartbeat_v1, __future__, dataclasses, datetime, json, os, pathlib, substrate.execution.runtime.runtime_heartbeat_v1
### `substrate/execution/workers/workstation/workstation_replay_validator_v1.py`
- Lines: 287. Doc: Workstation Replay Validator v1.
- Classes: ReplayCheck, ReplayResult, ReplaySessionResult, WorkstationReplayValidator
- Functions: -
- Imports: .governed_shell_adapter_v1, .workstation_contracts_v1, .workstation_operational_modes_v1, __future__, dataclasses, json, pathlib, typing
### `substrate/execution/workers/workstation/workstation_state_registry_v1.py`
- Lines: 213. Doc: Workstation State Registry v1.
- Classes: WorkstationStateRegistry
- Functions: -
- Imports: .workstation_contracts_v1, __future__, json, os, pathlib, platform, subprocess, substrate.execution.cpu_gate
### `substrate/foundation/__init__.py`
- Lines: 2. Doc: Foundation — substrate laws, identity, perspective, primitives, epistemology.
- Classes: -
- Functions: -
- Imports: -
### `substrate/foundation/derived_constructs.py`
- Lines: 94. Doc: Derived operational constructs — higher-order types built from primitives.
- Classes: GoalStatus, Goal, Plan, PlanStep, Context, Commitment
- Functions: -
- Imports: .epistemology, .primitives, __future__, datetime, enum, pydantic, typing, uuid
### `substrate/foundation/epistemology.py`
- Lines: 88. Doc: Epistemology schemas — how the substrate knows, believes, and tracks certainty.
- Classes: EpistemicStatus, EvidenceType, ConfidenceLevel, Belief, EpistemicRevision, KnowledgeGap
- Functions: -
- Imports: __future__, datetime, enum, pydantic, typing, uuid
### `substrate/foundation/identity.py`
- Lines: 59. Doc: Identity continuity schema — maintains coherent self across time and context switches.
- Classes: IdentityAspect, ContinuityAnchor, IdentityState
- Functions: -
- Imports: __future__, datetime, enum, pydantic, typing, uuid
### `substrate/foundation/laws.py`
- Lines: 34. Doc: Substrate laws — re-exports from substrate.ontology.laws.
- Classes: -
- Functions: -
- Imports: substrate.ontology.laws
### `substrate/foundation/persona.py`
- Lines: 50. Doc: Runtime persona configuration — the user-facing AI identity.
- Classes: PresentationStyle, VoiceProfile, Persona
- Functions: -
- Imports: __future__, dataclasses, enum, os
### `substrate/foundation/perspective.py`
- Lines: 65. Doc: Perspective schema — the lens through which the substrate interprets signals.
- Classes: PerspectiveType, PriorityFrame, Perspective, PerspectiveStack
- Functions: -
- Imports: __future__, datetime, enum, pydantic, typing, uuid
### `substrate/foundation/possibility.py`
- Lines: 84. Doc: Possibility space schema — models what COULD happen, not just what IS.
- Classes: PossibilityStatus, ActionType, Possibility, PossibilitySpace
- Functions: -
- Imports: __future__, datetime, enum, pydantic, typing, uuid
### `substrate/foundation/primitives.py`
- Lines: 79. Doc: Layer 0 ontological primitives — the irreducible types of existence in the substrate.
- Classes: Modality, OntologicalPrimitive, Relation, CompositionEdge
- Functions: -
- Imports: __future__, datetime, enum, pydantic, substrate.types, typing, uuid
### `substrate/governance/__init__.py`
- Lines: 10. Doc: UMH Governance — risk classification, authority, and policy enforcement.
- Classes: -
- Functions: -
- Imports: -
### `substrate/governance/accountability/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/governance/accountability/accountability.py`
- Lines: 321. Doc: AccountabilityEngine — holds the founder to their word.
- Classes: Commitment, AccountabilityEngine
- Functions: -
- Imports: dataclasses, datetime, json, uuid
### `substrate/governance/authority.py`
- Lines: 28. Doc: Authority levels — what the system can do without human intervention.
- Classes: AuthorityLevel
- Functions: -
- Imports: __future__, enum
### `substrate/governance/policy/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/governance/policy/authority_engine.py`
- Lines: 268. Doc: -
- Classes: AuthorityEngine
- Functions: -
- Imports: datetime, json, substrate.state.context.context, substrate.state.storage.db, substrate.types, uuid
### `substrate/governance/policy/authority_tier.py`
- Lines: 50. Doc: Authority tier constants and validation for ingestion sources.
- Classes: -
- Functions: validate_tier, tier_name, get_authority_tier
- Imports: __future__
### `substrate/governance/policy/confidentiality.py`
- Lines: 115. Doc: Confidentiality Protocol — handles sensitive
- Classes: -
- Functions: detect_confidential_context, create_confidential_session
- Imports: datetime, dotenv, json, logging, os, zoneinfo
### `substrate/governance/policy/execution_authority_engine_v1.py`
- Lines: 725. Doc: Execution Authority Engine v1 for the UMH substrate layer.
- Classes: AuthorityClass, ApprovalRequirement, EnvironmentAuthority, CapabilityAuthority, ExecutionAuthorityRequest, AuthorityDecision, AuthorityProof, ExecutionAuthorityEngine
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, pathlib, substrate.types
### `substrate/governance/policy_engine.py`
- Lines: 184. Doc: Policy engine — evaluates risk class + context to produce governance verdicts.
- Classes: PolicyVerdict, PolicyEngine
- Functions: -
- Imports: __future__, datetime, pydantic, substrate.governance.authority, substrate.governance.risk_classes, substrate.types, typing, uuid
### `substrate/governance/principles/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/governance/principles/principle_engine.py`
- Lines: 520. Doc: PrincipleEngine — injects quality standards into every AI decision.
- Classes: PrincipleEngine
- Functions: -
- Imports: __future__, os, substrate.state.context.context
### `substrate/governance/quality/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/governance/quality/quality_gate.py`
- Lines: 516. Doc: QualityTransformationGate — every output passes through the four values.
- Classes: TransformationResult, QualityTransformationGate
- Functions: quality_check, gate_outgoing_email
- Imports: dataclasses, logging
### `substrate/governance/risk_classes.py`
- Lines: 67. Doc: Action risk categories — semantic classification of side-effect types.
- Classes: ActionRiskCategory
- Functions: -
- Imports: __future__, enum, substrate.types
### `substrate/governance/security.py`
- Lines: 220. Doc: Security hardening — input validation, rate limiting, audit logging.
- Classes: ValidationResult, RateLimiter, AuditLog
- Functions: validate_signal_content, validate_path, validate_command, get_rate_limiter, get_audit_log
- Imports: __future__, collections, dataclasses, datetime, hashlib, logging, pathlib, re
### `substrate/governance/validation/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/governance/validation/completeness_engine.py`
- Lines: 288. Doc: Completeness Engine — 13-slot validation for plans, workflows, and compositions.
- Classes: SlotStatus, CompletenessSlot, SlotEvaluation, CompletenessResult, CompletenessEngine
- Functions: -
- Imports: __future__, dataclasses, enum, typing
### `substrate/governance/validation/output_validator.py`
- Lines: 315. Doc: OutputValidator — EOS applies its own principles to its own outputs.
- Classes: ViolationType, ValidationViolation, ValidationResult, OutputValidator
- Functions: get_validator, validate_before_discord
- Imports: dataclasses, enum, os
### `substrate/integrations/__init__.py`
- Lines: 10. Doc: Substrate integration infrastructure — capability bridge, CORS, health, product connections.
- Classes: -
- Functions: -
- Imports: -
### `substrate/integrations/bridge.py`
- Lines: 92. Doc: UMH Bridge — connects UMH model routing to runtime/model_router.py.
- Classes: CapabilityBridge
- Functions: _load_routing
- Imports: __future__, os, substrate.contracts.routing_contracts, sys, typing
### `substrate/integrations/cors.py`
- Lines: 45. Doc: CORS configuration for UMH API.
- Classes: -
- Functions: cors_origins
- Imports: __future__, os
### `substrate/integrations/health.py`
- Lines: 82. Doc: Health aggregator — dashboard endpoint combining all service health signals.
- Classes: HealthAggregator
- Functions: _probe
- Imports: __future__, json, os, time, typing, urllib.request
### `substrate/integrations/product_connections.py`
- Lines: 206. Doc: SaaS product connection manager — unified API for EOS, CreatorOS, LYFEOS.
- Classes: Product, ConnectionStatus, ProductConnection, ProductConnectionManager
- Functions: get_product_manager
- Imports: __future__, dataclasses, enum, logging, os, typing
### `substrate/intelligence/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/intelligence/finetune_harness.py`
- Lines: 449. Doc: Fine-tuning harness — scaffolds LoRA fine-tuning for self-hosted models.
- Classes: LoRAConfig, DataSplit, EvalResult, FinetuneHarness
- Functions: -
- Imports: __future__, dataclasses, json, logging, math, pathlib, random, substrate.execution.cpu_gate
### `substrate/intelligence/runtime.py`
- Lines: 440. Doc: Proprietary Intelligence Runtime — the system's learned intelligence.
- Classes: LearnedPattern, DecisionRecord, Prediction, PatternIntelligence, DecisionIntelligence, PredictiveIntelligence, IntelligenceRuntime
- Functions: -
- Imports: __future__, collections, dataclasses, datetime, json, logging, pathlib, time
### `substrate/intelligence/training_extractor.py`
- Lines: 243. Doc: Training data extraction from UMH execution traces.
- Classes: TrainingExample, ExtractionReport, TrainingExtractor
- Functions: -
- Imports: __future__, dataclasses, json, logging, pathlib, time, typing
### `substrate/memory/__init__.py`
- Lines: 23. Doc: Memory candidate staging, promotion, auto-reconciliation, bridging, and watching.
- Classes: -
- Functions: __getattr__
- Imports: substrate.memory.auto_reconciler, substrate.memory.candidate_generator, substrate.memory.claude_bridge, substrate.memory.promoter
### `substrate/memory/auto_reconciler.py`
- Lines: 172. Doc: AutoReconciler — closes the gap between promoted memories and canonical store.
- Classes: AutoReconciler
- Functions: _content_hash, _infer_primitive_type
- Imports: __future__, hashlib, logging, substrate.memory.candidate_generator, substrate.state.memory.contracts.canonical_memory_reconciliation_engine_v1, substrate.state.memory.contracts.canonical_memory_store_v1, substrate.state.memory.contracts.memory_conflict_governance_v1, typing
### `substrate/memory/candidate_generator.py`
- Lines: 177. Doc: MemoryCandidateGenerator — stages memory candidates from completed traces.
- Classes: PromotionStatus, MemoryCandidate, MemoryCandidateGenerator
- Functions: _deterministic_id
- Imports: __future__, dataclasses, datetime, hashlib, json, pathlib, substrate.observability.jsonl_rotation, typing
### `substrate/memory/canonical_write.py`
- Lines: 221. Doc: CanonicalWritePath -- single facade for organism-loop memory writes.
- Classes: MemoryWriteReceipt, CanonicalWritePath
- Functions: _safe_uuid
- Imports: __future__, dataclasses, datetime, logging, substrate.execution.executor, substrate.memory.candidate_generator, substrate.memory.promoter, substrate.reality_model.instance
### `substrate/memory/claude_bridge.py`
- Lines: 210. Doc: Claude Bridge — syncs Claude Code memory files to substrate memory candidates.
- Classes: ClaudeMemoryBridge
- Functions: _parse_frontmatter, _file_hash, sync_claude_memories
- Imports: __future__, hashlib, logging, pathlib, re, substrate.memory.auto_reconciler, substrate.memory.candidate_generator, substrate.memory.promoter
### `substrate/memory/promoter.py`
- Lines: 255. Doc: MemoryPromoter — evaluates candidates for promotion to durable storage.
- Classes: MemoryPromoter
- Functions: _tokenize, _tfidf_cosine, _detect_contradiction, _temporal_weight
- Imports: __future__, collections, hashlib, json, logging, math, pathlib, re
### `substrate/memory/watcher.py`
- Lines: 338. Doc: Memory Watcher — substrate-level filesystem watcher for agent memory directories.
- Classes: _SyncedHashes, _MemoryFileHandler, MemoryWatcher
- Functions: _parse_frontmatter, _file_hash, start_memory_watcher
- Imports: __future__, hashlib, json, logging, pathlib, re, substrate.memory.auto_reconciler, substrate.memory.candidate_generator
### `substrate/meta_ide/__init__.py`
- Lines: 132. Doc: Meta IDE — engineering reality awareness, planning, and proof loop.
- Classes: -
- Functions: -
- Imports: substrate.meta_ide.engineering_execution, substrate.meta_ide.engineering_intent, substrate.meta_ide.engineering_planner, substrate.meta_ide.engineering_session_coordinator, substrate.meta_ide.engineering_work_generator, substrate.meta_ide.repository_model, substrate.meta_ide.review_package_builder, substrate.meta_ide.roadmap_gap_engine
### `substrate/meta_ide/browser_evidence_collector.py`
- Lines: 282. Doc: Browser Evidence Collector — runs on Beast to collect verification evidence.
- Classes: ViewportEvidence, PassEvidence
- Functions: trigger_collection, collect_local_logs
- Imports: __future__, dataclasses, json, logging, os, shlex, subprocess, substrate.execution.cpu_gate
### `substrate/meta_ide/browser_verification_gate.py`
- Lines: 408. Doc: Browser Verification Gate — blocking validation for UI-bearing work.
- Classes: BrowserLayerResult, NetworkLayerResult, ConsoleLayerResult, LogLayerResult, VerificationPass, BrowserVerificationResult, BrowserVerificationGate
- Functions: get_pass_count, _recompute_pass_verdicts
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/meta_ide/engineering_execution.py`
- Lines: 205. Doc: Engineering Execution Contracts — governed execution session types.
- Classes: EngineeringExecutionStatus, OperatorRecommendation, EngineeringArtifactType, EngineeringArtifact, EngineeringExecutionSession, EngineeringProofPackage
- Functions: _classify_artifact_type
- Imports: __future__, dataclasses, enum, hashlib, time, typing, uuid
### `substrate/meta_ide/engineering_intent.py`
- Lines: 199. Doc: Engineering Intent Contract — types for autonomous engineering planning.
- Classes: EngineeringIntentType, EngineeringIntent, EngineeringTask, EngineeringPlan, EngineeringPlanReceipt
- Functions: classify_engineering_intent, extract_goal
- Imports: __future__, dataclasses, enum, re, time, typing, uuid
### `substrate/meta_ide/engineering_planner.py`
- Lines: 322. Doc: Engineering Planner — deterministic planning from high-level intent.
- Classes: EngineeringPlanner
- Functions: -
- Imports: __future__, logging, os, re, substrate.meta_ide.engineering_intent, typing
### `substrate/meta_ide/engineering_session_coordinator.py`
- Lines: 670. Doc: Engineering Session Coordinator — governed execution orchestration.
- Classes: EngineeringSessionCoordinator
- Functions: _build_execution_waves
- Imports: __future__, logging, os, substrate.meta_ide.browser_evidence_collector, substrate.meta_ide.browser_verification_gate, substrate.meta_ide.engineering_execution, substrate.meta_ide.engineering_intent, time
### `substrate/meta_ide/engineering_work_generator.py`
- Lines: 119. Doc: Engineering Work Generator — bridge from plans to governed work packets.
- Classes: EngineeringWorkGenerator
- Functions: -
- Imports: __future__, logging, substrate.meta_ide.engineering_intent, typing
### `substrate/meta_ide/repository_model.py`
- Lines: 279. Doc: Repository reality model — read-only git awareness.
- Classes: RepositoryHealthStatus, BranchSnapshot, WorktreeSnapshot, RepositoryHealth, RepositorySnapshot, RepositoryReader
- Functions: -
- Imports: __future__, dataclasses, enum, logging, os, re, substrate.execution.cpu_gate, time
### `substrate/meta_ide/review_package_builder.py`
- Lines: 235. Doc: Review Package Builder — deterministic proof assembly.
- Classes: ReviewPackageBuilder
- Functions: -
- Imports: __future__, logging, substrate.meta_ide.engineering_execution, typing
### `substrate/meta_ide/roadmap_gap_engine.py`
- Lines: 248. Doc: Roadmap Gap Engine — detects gaps and recommends engineering work.
- Classes: RoadmapGap, GapAnalysis, GapRecommendation, RoadmapGapEngine
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/meta_ide/roadmap_intelligence.py`
- Lines: 219. Doc: Roadmap intelligence — phase and planning awareness.
- Classes: PhaseState, PhaseStatus, RoadmapStatus, RoadmapIntelligence
- Functions: -
- Imports: __future__, dataclasses, enum, logging, os, re, time, typing
### `substrate/meta_ide/shared_planner.py`
- Lines: 31. Doc: Shared EngineeringPlanner singleton for all cockpit route modules.
- Classes: -
- Functions: get_shared_planner
- Imports: __future__, logging, typing
### `substrate/meta_ide/workspace_intelligence.py`
- Lines: 252. Doc: Workspace intelligence — engineering-state awareness.
- Classes: RiskLevel, EngineeringRisk, WorkspaceSummary, MetaIDEWorkspaceEngine
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.meta_ide.repository_model, time, typing
### `substrate/meta_ide/workspace_observation.py`
- Lines: 321. Doc: Workspace Observation — live engineering runtime observation.
- Classes: ObservationDomain, ProcessHealth, TerminalObservation, ContainerObservation, PreviewObservation, EngineeringSessionObservation, WorkspaceObservationSnapshot, WorkspaceObservationEngine
- Functions: _safe_parse
- Imports: __future__, collections, dataclasses, enum, json, logging, os, time
### `substrate/meta_ide/workspace_registry.py`
- Lines: 158. Doc: Workspace Registry — single source of truth for workspace topology.
- Classes: WorkspaceRegistry
- Functions: _find_registry_path, _load_seed_workspaces
- Imports: __future__, json, logging, os, substrate.meta_ide.workspace_runtime_graph, typing
### `substrate/meta_ide/workspace_runtime_graph.py`
- Lines: 205. Doc: Workspace Runtime Graph — canonical workspace topology models.
- Classes: WorkspaceType, RuntimeTargetType, BuildTargetType, WorkspaceHealth, WorkspaceRepository, WorkspaceRuntime, WorkspaceBuildTarget, WorkspaceDefinition
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/meta_ide/workspace_topology_engine.py`
- Lines: 272. Doc: Workspace Topology Engine — live workspace topology with health.
- Classes: WorkspaceTopologyEngine
- Functions: -
- Imports: __future__, logging, substrate.meta_ide.workspace_registry, substrate.meta_ide.workspace_runtime_graph, typing
### `substrate/observability/__init__.py`
- Lines: 9. Doc: Observability — trace, proof, outcome classification, and error recording.
- Classes: -
- Functions: -
- Imports: substrate.observability.error_recorder, substrate.observability.outcome_classifier, substrate.observability.proof_store, substrate.observability.trace_store
### `substrate/observability/error_recorder.py`
- Lines: 58. Doc: Canonical fix-forever error recorder.
- Classes: -
- Functions: record_error
- Imports: __future__, datetime, json, logging, os, pathlib, substrate.observability.jsonl_rotation
### `substrate/observability/jsonl_rotation.py`
- Lines: 64. Doc: JSONL rotation utility.
- Classes: -
- Functions: _count_lines, rotate_if_needed
- Imports: __future__, datetime, logging, pathlib
### `substrate/observability/outcome_classifier.py`
- Lines: 123. Doc: OutcomeClassifier — classifies execution results into outcome categories.
- Classes: OutcomeCategory, ClassificationResult, OutcomeClassifier
- Functions: -
- Imports: __future__, dataclasses, typing
### `substrate/observability/proof_store.py`
- Lines: 118. Doc: ProofStore — JSON-based proof artifact persistence.
- Classes: ProofArtifact, ProofStore
- Functions: _deterministic_id
- Imports: __future__, dataclasses, datetime, hashlib, json, pathlib, typing
### `substrate/observability/trace_store.py`
- Lines: 236. Doc: TraceStore — append-only JSONL trace persistence.
- Classes: TraceStatus, Trace, TraceStore
- Functions: _deterministic_id
- Imports: __future__, dataclasses, datetime, hashlib, json, pathlib, substrate.observability.jsonl_rotation, typing
### `substrate/ontology/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/ontology/domains/__init__.py`
- Lines: 21. Doc: Domain bridges — re-exports from substrate.understanding.domains.
- Classes: -
- Functions: -
- Imports: substrate.understanding.domains.contract, substrate.understanding.domains.creator, substrate.understanding.domains.life, substrate.understanding.domains.registry
### `substrate/ontology/domains/contract.py`
- Lines: 13. Doc: Domain bridge contract — re-exports from substrate.understanding.domains.contract.
- Classes: -
- Functions: -
- Imports: substrate.understanding.domains.contract
### `substrate/ontology/domains/creator.py`
- Lines: 9. Doc: Creator domain bridge — re-exports from substrate.understanding.domains.creator.
- Classes: -
- Functions: -
- Imports: substrate.understanding.domains.creator
### `substrate/ontology/domains/life.py`
- Lines: 9. Doc: Life domain bridge — re-exports from substrate.understanding.domains.life.
- Classes: -
- Functions: -
- Imports: substrate.understanding.domains.life
### `substrate/ontology/domains/registry.py`
- Lines: 12. Doc: Bridge registry — re-exports from substrate.understanding.domains.registry.
- Classes: -
- Functions: -
- Imports: substrate.understanding.domains.registry
### `substrate/ontology/laws.py`
- Lines: 200. Doc: Governing laws — enacted constraints that govern UMH like physics governs reality.
- Classes: LawCategory, Severity, Law, LawRegistry
- Functions: -
- Imports: __future__, enum, pydantic, typing, uuid
### `substrate/ontology/primitives.py`
- Lines: 26. Doc: Ontology primitives — the computational physics of UMH.
- Classes: -
- Functions: -
- Imports: substrate.types
### `substrate/ontology/relationships.py`
- Lines: 8. Doc: Typed relationship edges between ontology observations.
- Classes: -
- Functions: -
- Imports: __future__, substrate.types
### `substrate/operator/__init__.py`
- Lines: 75. Doc: UMH Operator — unified intent classification and routing layer.
- Classes: -
- Functions: -
- Imports: substrate.operator.intent_receipt, substrate.operator.intent_router
### `substrate/operator/continuity_engine.py`
- Lines: 501. Doc: Continuity Engine — operator presence and continuity aggregation.
- Classes: ContinuityEngine
- Functions: -
- Imports: __future__, json, logging, os, substrate.operator.operator_presence, time, typing
### `substrate/operator/device_continuity.py`
- Lines: 129. Doc: Device Continuity — per-device presence state tracking.
- Classes: DevicePresenceState, DeviceContinuityTracker
- Functions: -
- Imports: __future__, dataclasses, substrate.operator.operator_presence, time, typing
### `substrate/operator/intent_receipt.py`
- Lines: 147. Doc: Unified intent receipt — canonical audit trail for every operator interaction.
- Classes: ReceiptStatus, IntentReceipt, IntentReceiptStore
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, tempfile, threading
### `substrate/operator/intent_router.py`
- Lines: 250. Doc: Intent Router — deterministic-first classification of operator intent.
- Classes: RouteType, RouteClassification, IntentRouter
- Functions: -
- Imports: __future__, dataclasses, enum, logging, re, typing
### `substrate/operator/intent_runtime.py`
- Lines: 590. Doc: Intent Runtime — canonical intent preservation for operator continuity.
- Classes: IntentScope, CanonicalIntentStatus, ConflictType, CanonicalIntent, IntentConflict, _JSONLStore, IntentRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, threading, time
### `substrate/operator/operator_attention_engine.py`
- Lines: 321. Doc: Operator Attention Engine — deterministic ranked priorities.
- Classes: AttentionItem, OperatorAttentionEngine
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/operator/operator_context.py`
- Lines: 205. Doc: Operator Context Models — types for the operator home surface.
- Classes: OperatorSeverity, OperatorAttentionType, OperatorAttentionItem, OperatorStatusCard, OperatorHealthSummary, OperatorTimelineEvent, OperatorSnapshot
- Functions: -
- Imports: __future__, dataclasses, enum, time, typing, uuid
### `substrate/operator/operator_context_engine.py`
- Lines: 521. Doc: Operator Context Engine — aggregation façade for operator home.
- Classes: OperatorContextEngine
- Functions: -
- Imports: __future__, logging, substrate.operator.operator_context, time, typing
### `substrate/operator/operator_presence.py`
- Lines: 208. Doc: Operator Presence Models — types for presence and continuity tracking.
- Classes: PresenceState, PresenceDeviceType, ContinuityStatus, OperatorPresence, ActiveContext, ContinuityCheckpoint, PresenceSnapshot
- Functions: -
- Imports: __future__, dataclasses, enum, time, typing, uuid
### `substrate/operator/operator_snapshot_runtime.py`
- Lines: 489. Doc: Operator Snapshot Runtime — answers the 5 operator questions.
- Classes: SituationSnapshot, ChangeEntry, DecisionItem, OperatorNextAction, OperatorQuestionSnapshot, OperatorSnapshotRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.operator.operator_attention_engine, time, typing
### `substrate/operator/presence_timeline.py`
- Lines: 185. Doc: Presence Timeline — operator presence transition tracking.
- Classes: PresenceTransitionType, PresenceTransition, PresenceTimeline
- Functions: -
- Imports: __future__, dataclasses, substrate.operator.operator_presence, time, typing, uuid
### `substrate/operator/repository_context_resolver.py`
- Lines: 108. Doc: UMH Repository Context Resolver — maps workspace state to repo context.
- Classes: RepositoryContextResolver
- Functions: -
- Imports: __future__, logging, substrate.operator.screen_awareness, typing
### `substrate/operator/screen_awareness.py`
- Lines: 292. Doc: UMH Screen Awareness — types for operator visual workspace context.
- Classes: ScreenSourceType, ScreenContextStatus, ApplicationCategory, FocusedApplication, ActiveWindow, RepositoryContext, FileContext, BrowserContext
- Functions: -
- Imports: __future__, dataclasses, enum, substrate.operator.operator_presence, time, typing, uuid
### `substrate/operator/screen_context_providers.py`
- Lines: 297. Doc: UMH Screen Context Providers — three modes of screen awareness.
- Classes: ScreenContextProvider, InferredScreenContextProvider, ObservedScreenContextProvider, ReportedScreenContextProvider
- Functions: _classify_freshness
- Imports: __future__, logging, os, socket, substrate.operator.operator_presence, substrate.operator.screen_awareness, time, typing
### `substrate/operator/screen_observation_engine.py`
- Lines: 273. Doc: UMH Screen Observation Engine — node-role-aware screen context aggregation.
- Classes: ScreenObservationEngine
- Functions: -
- Imports: __future__, collections, logging, socket, substrate.operator.screen_awareness, substrate.operator.screen_context_providers, time, typing
### `substrate/operator/voice_query_engine.py`
- Lines: 953. Doc: Voice Query Engine — context-grounded query resolution.
- Classes: QueryDomain, QueryResolution, VoiceQueryEngine, ActionResolution
- Functions: _detect_action_intent, _build_confirmation
- Imports: __future__, dataclasses, enum, logging, re, time, typing
### `substrate/operator/workstation_session_runtime.py`
- Lines: 413. Doc: Workstation Session Runtime — operator leave/return with full context restore.
- Classes: WorkstationSessionStatus, WorkstationSessionCheckpoint, WorkstationSessionResume, WorkstationSession, WorkstationSessionRuntime
- Functions: _safe_call, _safe_dict, _safe_list, _safe_float
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/operator/workstation_translator.py`
- Lines: 211. Doc: UMH Workstation Translator — Beast payload → canonical ScreenSnapshot.
- Classes: WorkstationTranslator
- Functions: classify_application
- Imports: __future__, logging, os, substrate.operator.screen_awareness, time, typing
### `substrate/organism/__init__.py`
- Lines: 72. Doc: UMH Organism — distributed orchestration substrate.
- Classes: -
- Functions: -
- Imports: -
### `substrate/organism/action_bridge.py`
- Lines: 464. Doc: Action Bridge — governed composition of catalog, observation, and execution.
- Classes: ActionRequest, ActionResult, ActionBridge
- Functions: _under_allowed_root
- Imports: __future__, collections, dataclasses, logging, os, re, substrate.organism.action_catalog, time
### `substrate/organism/action_catalog.py`
- Lines: 309. Doc: Action Catalog — data-driven registry of governed operator actions.
- Classes: ActionRiskLevel, ActionCategory, ActionStatus, ActionParameter, ActionPrecondition, ActionDefinition, ActionCatalog
- Functions: -
- Imports: __future__, dataclasses, enum, logging, re, typing
### `substrate/organism/action_envelope.py`
- Lines: 173. Doc: ActionEnvelope — canonical executable object for ALL organism mutations.
- Classes: ActionType, ReversibilityClass, BlastRadius, EnvelopeStatus, VerificationStrategy, RollbackStrategy, ExecutionConstraints, ActionEnvelope
- Functions: -
- Imports: __future__, dataclasses, enum, time, typing, uuid
### `substrate/organism/action_voice_contract.py`
- Lines: 81. Doc: Voice/Intent Action Contract — interface between intent sources and ActionBridge.
- Classes: IntentActionRequest, IntentActionContract
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/organism/advisor.py`
- Lines: 816. Doc: Advisor cell — the top-level orchestrator of the organism.
- Classes: Advisor
- Functions: _infer_capability, _infer_risk_class
- Imports: __future__, datetime, logging, substrate.organism.agent_runtime, substrate.organism.agents, substrate.organism.coordinator, substrate.organism.delegation_followup, substrate.organism.handoff
### `substrate/organism/advisor_conversation.py`
- Lines: 2013. Doc: Conversational advisor — multi-turn conversation with intent routing.
- Classes: AdvisorResponse, AdvisorConversation
- Functions: -
- Imports: __future__, dataclasses, datetime, json, logging, os, typing, uuid
### `substrate/organism/advisor_hierarchy.py`
- Lines: 410. Doc: Advisor Hierarchy — governed recursive advisory orchestration.
- Classes: AdvisorScope, AdvisorAuthority, AdvisorStatus, EscalationPolicy, AdvisorNode, AdvisorHierarchy
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/advisor_reconciliation.py`
- Lines: 228. Doc: Operator Reconciliation Integration — detects reconciliation intent in operator input.
- Classes: ReconciliationIntent, AdvisorReconciliation
- Functions: classify_reconciliation_intent, extract_topic
- Imports: __future__, logging, re, substrate.organism.canonical_update, substrate.organism.context_diagnostic, substrate.organism.ingestion_job, substrate.organism.reconciliation_engine, substrate.organism.reconciliation_session
### `substrate/organism/agent_capability_model.py`
- Lines: 282. Doc: Agent Capability Model — track agent reliability per capability.
- Classes: AgentReliabilityRecord, AgentCapability, AgentCapabilityProfile, AgentCapabilityModel
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, time, typing, uuid
### `substrate/organism/agent_execution_runner.py`
- Lines: 637. Doc: Agent Execution Runner — invokes coding agents inside governed sandboxes.
- Classes: AgentExecutionPlan, ExecutionRecord, FailureReport, AgentExecutionRunner
- Functions: _repo_root
- Imports: __future__, dataclasses, json, logging, os, time, typing, uuid
### `substrate/organism/agent_fleet_runtime.py`
- Lines: 590. Doc: Agent Fleet Runtime — unified agent coordination layer.
- Classes: FleetDispatchStatus, AssignmentRationale, FleetAssignment, FleetDispatch, FleetDispatchResult, FleetSnapshot, FleetHealth, WaveResult
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/agent_registry.py`
- Lines: 224. Doc: Agent Registry — agent types, capabilities, permissions, and routing.
- Classes: AgentType, AgentRegistry
- Functions: _register
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/agent_runtime.py`
- Lines: 187. Doc: Agent base runtime — the foundational behavior of every agent in the society.
- Classes: AgentRuntime
- Functions: -
- Imports: __future__, logging, substrate.organism.protocols, substrate.organism.store, substrate.organism.worker_cell, typing
### `substrate/organism/agents.py`
- Lines: 60. Doc: Concrete agent cells — Researcher, Builder, AutoResearch.
- Classes: -
- Functions: create_researcher, create_builder, create_auto_research
- Imports: __future__, substrate.organism.agent_runtime, substrate.organism.protocols, substrate.organism.store, substrate.organism.worker_cell
### `substrate/organism/allocation_loop.py`
- Lines: 152. Doc: Governed runtime allocation loop — continuous leverage allocator.
- Classes: AllocationStrategy, AllocationDecision, AllocationLoop
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.event_spine, substrate.organism.execution_economy, substrate.organism.recursion_governance, substrate.organism.runtime_graph
### `substrate/organism/approval_gate.py`
- Lines: 277. Doc: Operator Approval Gate — requires explicit approval before sandbox execution.
- Classes: ApprovalStatus, ApprovalPacket, OperatorApprovalGate
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/approval_store.py`
- Lines: 108. Doc: Approval store — JSONL persistence for governance-blocked signals.
- Classes: ApprovalStore
- Functions: -
- Imports: __future__, datetime, json, logging, pathlib, substrate.sockets.notification, typing, uuid
### `substrate/organism/artifact_registry.py`
- Lines: 210. Doc: Artifact Registry — indexes produced outputs across UMH.
- Classes: ArtifactType, ArtifactStatus, ArtifactEntry, ArtifactRegistry
- Functions: -
- Imports: __future__, dataclasses, enum, hashlib, json, logging, os, time
### `substrate/organism/assisted_executor.py`
- Lines: 501. Doc: Assisted Executor — governed execution of approved maintenance actions.
- Classes: ActionResult, AssistedAction, AssistedExecutor
- Functions: _rotate_logs, _restart_container, _refresh_runtime, _run_tests, _rebuild_graph, _cleanup_branches, _cleanup_disk
- Imports: __future__, dataclasses, enum, logging, os, pathlib, re, subprocess
### `substrate/organism/assumption_tracking_runtime.py`
- Lines: 189. Doc: Assumption Tracking Runtime — governed assumption records for UMH.
- Classes: AssumptionStatus, AssumptionRecord, AssumptionTrackingRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/async_coordinator.py`
- Lines: 262. Doc: Async coordinator execution — event-driven objective lifecycle.
- Classes: AsyncObjectiveStatus, AsyncObjective, AsyncCoordinator
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.coordinator, substrate.organism.event_spine, time, typing
### `substrate/organism/audits/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/organism/audits/context_capacity.py`
- Lines: 182. Doc: Audit — Context Capacity.
- Classes: ContextCapacityReport, ContextCapacityAudit
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, typing
### `substrate/organism/audits/empire_readiness.py`
- Lines: 197. Doc: Audit — Empire Readiness.
- Classes: ProjectionScore, EmpireReadinessReport, EmpireReadinessAudit
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.organism.benchmarks.projection_readiness, typing
### `substrate/organism/audits/model_correspondence.py`
- Lines: 165. Doc: Model Correspondence Audit — predicted state vs observed reality.
- Classes: PredictionRecord, CorrespondenceDimension, ModelCorrespondenceReport, ModelCorrespondenceAudit
- Functions: score_match
- Imports: __future__, dataclasses, typing
### `substrate/organism/audits/operational_awareness.py`
- Lines: 88. Doc: Audit — Operational Awareness.
- Classes: ServiceState, OperationalAwarenessReport, OperationalAwarenessAudit
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/audits/organism_awareness.py`
- Lines: 130. Doc: Audit — Organism Self-Awareness.
- Classes: AwarenessDimension, OrganismAwarenessReport, OrganismAwarenessAudit
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/audits/source_truth.py`
- Lines: 139. Doc: Audit — Source of Truth (Production Lineage).
- Classes: LineageChain, SourceTruthReport, SourceTruthAudit
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/automation_pipeline.py`
- Lines: 248. Doc: Automation Candidate Pipeline — promote repeated interventions to automation.
- Classes: CandidateStatus, AutomationRisk, AutomationProposal, AutomationPipeline
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.event_spine, substrate.organism.execution_modes, substrate.organism.operator_compression, time
### `substrate/organism/autonomous_action_gateway.py`
- Lines: 423. Doc: Autonomous Action Gateway — structural enforcement of spine-routed mutation.
- Classes: AutonomousPolicy, GatewayDecision, AutonomousActionGateway
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.action_envelope, substrate.organism.event_spine, substrate.organism.execution_journal, substrate.organism.execution_modes
### `substrate/organism/autonomous_cadence.py`
- Lines: 326. Doc: Autonomous Cadence — scheduled autonomous improvement discovery.
- Classes: CadenceMode, CadencePolicy, CadenceRunResult, AutonomousCadence
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/autonomous_improvement_lane.py`
- Lines: 909. Doc: Autonomous Improvement Lane — bounded autonomous LOW-risk self-improvement.
- Classes: LaneDecision, LaneRunStatus, AutonomousLanePolicy, AutonomousImprovementCandidate, CandidateEvaluation, AutonomousLaneRun, AutonomousCandidateSelector, AutonomousPolicyEvaluator
- Functions: _has_sensitive_content
- Imports: __future__, dataclasses, enum, json, logging, os, substrate.organism.agent_capability_model, substrate.organism.composition_engine
### `substrate/organism/autonomous_pr_factory.py`
- Lines: 867. Doc: Autonomous PR Factory — converts eligible improvements into isolated PRs.
- Classes: PRCreationStatus, OutcomeBoundary, SandboxOutcomeCommitted, ProductionOutcomeCommitted, PRValidationGate, PRReviewPacket, AutonomousPRRequest, AutonomousPRResult
- Functions: _run_cmd, _gh_available, _git_diff_stat
- Imports: __future__, dataclasses, enum, json, logging, os, shutil, subprocess
### `substrate/organism/autonomous_tick.py`
- Lines: 286. Doc: Autonomous tick engine — continuous organism metabolism heartbeat.
- Classes: TickConfig, TickMetrics, TickStage, CycleReport, AutonomousTick
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.organism.event_spine, threading, time, typing
### `substrate/organism/benchmarks/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/organism/benchmarks/autonomous_execution.py`
- Lines: 86. Doc: Autonomous Execution Benchmark — session depth, recovery, and independence.
- Classes: SessionRecord, AutonomousExecutionResult, AutonomousExecutionBenchmark
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/capability_reuse.py`
- Lines: 234. Doc: Benchmark 4 — Capability Reuse (Dual-Track).
- Classes: ReusableCapability, TrackRecord, CapabilityROI, CapabilityReuseResult, CapabilityReuseBenchmark
- Functions: _avg, _pct_improvement
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/competitive.py`
- Lines: 274. Doc: Competitive benchmarking data layer — competitor profiles, market categories, and scoring.
- Classes: MarketCategory, MeasurementType, ComparisonType, CompetitorProfile, CategoryScore, GapEntry, CompetitiveMatrix, CompetitorRegistry
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, pathlib, time, typing
### `substrate/organism/benchmarks/composite_scorer.py`
- Lines: 246. Doc: Composite Scorer — aggregate 20 categories into competitive matrix.
- Classes: CompositeScorer
- Functions: -
- Imports: __future__, logging, substrate.organism.benchmarks.competitive, time, typing
### `substrate/organism/benchmarks/compounding_proof.py`
- Lines: 218. Doc: Benchmark 7 — Compounding Proof (Integration).
- Classes: BuildMetrics, CompoundingVerdict, CompoundingCurve, CompoundingProofResult, CompoundingProofBenchmark
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/efficiency.py`
- Lines: 118. Doc: Efficiency Benchmark — capability per dollar.
- Classes: ProductionCost, EfficiencyResult, EfficiencyBenchmark
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/external_adapters.py`
- Lines: 364. Doc: External benchmark adapter layer — industry-standard benchmarks through UMH.
- Classes: BenchmarkTask, TaskResult, ExternalBenchmarkResult, ExternalBenchmarkAdapter, SWEBenchAdapter, TerminalBenchAdapter, WebArenaAdapter, GAIAAdapter
- Functions: get_adapter
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/human_amplification.py`
- Lines: 132. Doc: Human Amplification Benchmark — does the operator become more capable?
- Classes: SkillLevel, TaskComplexity, AmplificationRecord, AmplificationResult, HumanAmplificationBenchmark
- Functions: -
- Imports: __future__, dataclasses, typing
### `substrate/organism/benchmarks/operator_compression.py`
- Lines: 265. Doc: Benchmark 5 — Operator Compression.
- Classes: OperatorInteraction, ProductionInteractions, CompressionMetrics, OperatorCompressionResult, OperatorCompressionBenchmark
- Functions: classify_operator_message, _compute_trend
- Imports: __future__, dataclasses, re, typing
### `substrate/organism/benchmarks/outcome_accuracy.py`
- Lines: 88. Doc: Outcome Accuracy Benchmark — did completed work achieve original intent?
- Classes: OutcomeRecord, OutcomeAccuracyResult, OutcomeAccuracyBenchmark
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/production_outcome_quality.py`
- Lines: 249. Doc: Benchmark 6 — Production Outcome Quality.
- Classes: AcceptanceCriterion, ProductionOutcome, TrackMetrics, QualityComparison, ProductionOutcomeResult, ProductionOutcomeQualityBenchmark
- Functions: -
- Imports: __future__, dataclasses, typing
### `substrate/organism/benchmarks/production_quality.py`
- Lines: 247. Doc: Benchmark 2 — Production Quality.
- Classes: SeededDefect, DefectSeeder, DefectDetector, ProductionQualityResult, ProductionQualityBenchmark
- Functions: _load_defect_catalog
- Imports: __future__, dataclasses, json, logging, os, pathlib, re, tempfile
### `substrate/organism/benchmarks/production_velocity.py`
- Lines: 147. Doc: Benchmark 3 — Production Velocity.
- Classes: ProductionRecord, VelocityResult, ProductionVelocityBenchmark
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/projection_readiness.py`
- Lines: 197. Doc: Benchmark — Projection Readiness.
- Classes: ProjectionCoverage, ProjectionReadinessResult, ProjectionReadinessBenchmark
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/reality_correspondence.py`
- Lines: 1240. Doc: Reality Correspondence Benchmark — 50 failure scenarios across 5 domains.
- Classes: BenchmarkDomain, BenchmarkScenario, BenchmarkResult, RealityCorrespondenceBenchmark
- Functions: _build_scenarios
- Imports: __future__, dataclasses, enum, json, logging, tempfile, time, typing
### `substrate/organism/benchmarks/reality_recovery.py`
- Lines: 586. Doc: Benchmark 1 — Reality Recovery.
- Classes: Question, ScoredAnswer, RealityRecoveryResult, RealityRecoveryBenchmark
- Functions: _run_cmd, _read_json_file, _count_lines, _count_files
- Imports: __future__, dataclasses, json, logging, os, pathlib, subprocess, substrate.execution.cpu_gate
### `substrate/organism/benchmarks/reliability.py`
- Lines: 95. Doc: Reliability Benchmark — consistency across repeated builds.
- Classes: ReliabilityTrial, ReliabilityResult, ReliabilityBenchmark
- Functions: _population_variance
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/benchmarks/strategic_compression.py`
- Lines: 92. Doc: Strategic Compression Benchmark — high-level intent to executable reality.
- Classes: IntentRecord, StrategicCompressionResult, StrategicCompressionBenchmark
- Functions: -
- Imports: __future__, dataclasses, typing
### `substrate/organism/bottleneck_engine.py`
- Lines: 485. Doc: Bottleneck Detection Engine — organism operational self-optimization.
- Classes: BottleneckSeverity, BottleneckCategory, BottleneckEvidence, Bottleneck, BottleneckThresholds, BottleneckEngine
- Functions: -
- Imports: __future__, collections, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/candidate_supply_engine.py`
- Lines: 615. Doc: Candidate Supply Engine — discovers improvement candidates from real organism sources.
- Classes: SupplyCandidate, SupplyResult, CandidateSupplyEngine
- Functions: -
- Imports: __future__, dataclasses, glob, logging, os, re, substrate.organism.template_governance, substrate.organism.template_registry
### `substrate/organism/canonical_update.py`
- Lines: 192. Doc: Canonical Update Proposal — proposed changes to canonical truth.
- Classes: ProposalType, ProposalStatus, CanonicalUpdateProposal, ProposalStore
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/capability_compounding_runtime.py`
- Lines: 585. Doc: Capability Compounding Runtime — Campaign 22.4
- Classes: CompoundingStage, CompoundingHealth, CompoundingSnapshot, PipelineTrace, ReusableAsset, CapabilityCompoundingRuntime
- Functions: _stage_index, _next_stage
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/capability_evolution_engine.py`
- Lines: 524. Doc: Capability Evolution Engine — Campaign 12.2
- Classes: EvolutionEventType, EvolutionEvent, CapabilityTrajectory, EvolutionSnapshot, CapabilityEvolutionEngine
- Functions: -
- Imports: __future__, dataclasses, enum, hashlib, json, logging, os, time
### `substrate/organism/capability_gap_engine.py`
- Lines: 286. Doc: Capability Gap Engine — detect missing or immature capabilities for goals.
- Classes: CapabilityGapSeverity, CapabilityGap, CapabilityGapEngine
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/capability_graph_engine.py`
- Lines: 361. Doc: Capability Graph Engine — explicit dependency/composition edges between capabilities.
- Classes: CapabilityRelationType, CapabilityEdge, CapabilityGraphEngine
- Functions: -
- Imports: __future__, collections, dataclasses, enum, json, logging, os, time
### `substrate/organism/capability_portfolio_runtime.py`
- Lines: 255. Doc: Capability Portfolio Runtime — portfolio-level health and compounding metrics.
- Classes: PortfolioHealth, CapabilityPortfolioSnapshot, CapabilityPortfolioRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/capability_runtime.py`
- Lines: 473. Doc: Capability Runtime — emergent capability tracking and maturity lifecycle.
- Classes: CapabilityMaturity, CapabilityEvidenceType, CapabilityEvidence, EmergentCapability, CapabilityRuntime
- Functions: compute_maturity_score, maturity_from_score, detect_capability_patterns
- Imports: __future__, collections, dataclasses, enum, json, logging, os, threading
### `substrate/organism/capability_validation_runtime.py`
- Lines: 506. Doc: Capability Validation Runtime — benchmark storage, reporting, and freshness tracking.
- Classes: BenchmarkRun, CapabilityFreshness, CompoundingVerdict, QualityVerdict, ValidationReport, CapabilityValidationRuntime
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, pathlib, time, typing
### `substrate/organism/change_event.py`
- Lines: 371. Doc: Change Event — state change model for propagation planning.
- Classes: ChangeType, PropagationActionStatus, ChangeEvent, PropagationAction, PropagationWave, PropagationPlan, PropagationResult
- Functions: persist_change_events, load_change_events, persist_propagation_plans, persist_propagation_results
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/changeset_manifest.py`
- Lines: 296. Doc: Changeset Manifest — evidence record for every autonomous branch/PR.
- Classes: ChangedFile, ValidationProof, RiskProof, RollbackProof, PropagationProof, ChangeSetManifest
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, time, typing, uuid
### `substrate/organism/claude_code_runtime_adapter.py`
- Lines: 180. Doc: Claude Code PTY runtime adapter — skeleton with truthful availability.
- Classes: ClaudeCodeRuntimeAdapter
- Functions: _detect_claude_binary, _detect_runtime_policy
- Imports: __future__, logging, os, shutil, substrate.organism.runtime_adapter, substrate.organism.runtime_session, typing
### `substrate/organism/coherence_propagation.py`
- Lines: 535. Doc: Coherence Propagation Engine — parallel dependent-system updates on verified change.
- Classes: OutcomeEventType, PrimitiveRelationship, OutcomeCommitted, OutcomeFailed, PropagationStatus, PropagationTarget, PropagationResult, PropagationWave
- Functions: -
- Imports: __future__, concurrent.futures, dataclasses, enum, json, logging, os, time
### `substrate/organism/command_runtime.py`
- Lines: 1354. Doc: Command Runtime — canonical intent-to-action layer for all operator surfaces.
- Classes: CommandActionType, CommandStatus, CommandSource, CommandEventType, CommandContext, Command, CommandEvent, CommandRoutingDecision
- Functions: _repo_root, get_command_runtime, reset_command_runtime
- Imports: __future__, dataclasses, enum, json, logging, os, re, time
### `substrate/organism/composition_engine.py`
- Lines: 466. Doc: Composition Engine — deterministic intent → plan from observed capabilities.
- Classes: GovernanceMode, StepStatus, CompositionIntent, CompositionContext, CompositionConstraint, CapabilityMatch, CompositionRisk, CompositionStep
- Functions: _classify_intent, compose_plan, persist_plan
- Imports: __future__, dataclasses, enum, json, logging, os, substrate.types, time
### `substrate/organism/compounding_engine.py`
- Lines: 457. Doc: Capability Compounding Engine — turn internal learning into leverage.
- Classes: PromotionType, PromotionStatus, PromotionCandidate, CompoundingEngine
- Functions: score_outcome_to_insight, score_insight_to_capability, score_capability_to_operationalization, score_operationalization_to_infrastructure
- Imports: __future__, collections, dataclasses, enum, json, logging, os, threading
### `substrate/organism/compute_fabric_runtime.py`
- Lines: 455. Doc: Compute Fabric Runtime — unified compute body map.
- Classes: ComputeNodeType, ComputeNodeHealth, ComputeNode, RoutingDecision, ComputeFabricRuntime
- Functions: _infer_node_type, _compute_health
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/context_diagnostic.py`
- Lines: 228. Doc: Context Diagnostic — models for diagnostic reports on context state.
- Classes: ContradictionType, DiagnosticStatus, CanonicalClaim, ContextContradiction, ContextDiagnosticReport, DiagnosticReportStore
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/context_ingestion_engine.py`
- Lines: 451. Doc: Context Ingestion Engine — ingest local/system context sources.
- Classes: ContextIngestionEngine
- Functions: _load_entity_patterns, _is_safe_path, _is_allowed_extension, _is_within_size_limit, _redact_secrets, _extract_claims, _extract_entities, _extract_decisions, _classify_freshness
- Imports: __future__, glob, json, logging, os, re, substrate.organism.ingestion_job, substrate.organism.source_registry
### `substrate/organism/context_resolution.py`
- Lines: 557. Doc: Context Resolution Engine — "the system already knows" layer.
- Classes: ResolutionStrategy, ResolvedContext, ContextResolutionEngine
- Functions: _extract_candidate_names
- Imports: __future__, dataclasses, enum, logging, re, time, typing
### `substrate/organism/continuity_runtime.py`
- Lines: 1354. Doc: Continuity Runtime — operational continuity engine for UMH.
- Classes: AttentionState, TimelineEventType, ChangeCategory, BriefSection, ContinuitySnapshot, TimelineEvent, ResumeReport, OperatorBrief
- Functions: _repo_root, _continuity_data_dir, _ensure_dirs, get_continuity_runtime, reset_continuity_runtime
- Imports: __future__, dataclasses, enum, hashlib, json, logging, os, time
### `substrate/organism/contradiction_engine.py`
- Lines: 397. Doc: Contradiction Engine — detect mismatches between declared and observed reality.
- Classes: ContradictionSeverity, ContradictionType, Claim, Observation, Contradiction, ContradictionReport, ContradictionEngine
- Functions: _check_missing_subsystem_files, _check_empty_data_stores, _check_orphaned_subsystems, _check_deployment_files, _check_route_panel_mismatch, _check_dependency_cycles, _check_governance_missing, detect_contradictions, persist_contradictions
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/coordinator.py`
- Lines: 619. Doc: OrganismCoordinator — hierarchical task decomposition and runtime assignment.
- Classes: WorkUnitStatus, ObjectiveStatus, WorkUnitType, WorkUnit, Objective, OrganismCoordinator
- Functions: _get_workload_type, _infer_unit_type
- Imports: __future__, dataclasses, enum, json, logging, pathlib, substrate.organism.runtime_graph, time
### `substrate/organism/correspondence_scheduler.py`
- Lines: 230. Doc: Correspondence Scheduler — periodic drift detection for projections.
- Classes: RegressionAlert, CorrespondenceScheduler
- Functions: -
- Imports: __future__, collections, dataclasses, datetime, logging, substrate.organism.production_truth_delta, time, typing
### `substrate/organism/council.py`
- Lines: 286. Doc: Council — multi-perspective advisory layer for the advisor.
- Classes: CouncilRole, CouncilReview, Council
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, time, typing
### `substrate/organism/cross_source_reconciler.py`
- Lines: 346. Doc: Cross-Source Reconciler — detect relationships across fragmented sources.
- Classes: SignalType, SignalStatus, CrossSourceSignal, CrossSourceReconciler
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, substrate.organism.canonical_update, substrate.organism.permission_dialogue
### `substrate/organism/daemon.py`
- Lines: 1027. Doc: Organism daemon — manages agent lifecycle within the control plane.
- Classes: OrganismDaemon
- Functions: _map_risk_level
- Imports: __future__, json, logging, os, pathlib, substrate.execution.pipeline, substrate.organism.advisor, substrate.organism.agent_capability_model
### `substrate/organism/decision_impact_engine.py`
- Lines: 266. Doc: Decision Impact Engine — blast radius analysis for strategic decisions.
- Classes: DecisionImpact, DecisionImpactEngine
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/decision_lineage_engine.py`
- Lines: 364. Doc: Decision Lineage Engine — causal chain traversal for strategic decisions.
- Classes: LineageNode, DecisionLineage, DecisionLineageEngine
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/decision_registry.py`
- Lines: 310. Doc: Decision Registry — first-class strategic decision records for UMH.
- Classes: DecisionStatus, StrategicDecision, DecisionRegistry
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/decision_validity_engine.py`
- Lines: 315. Doc: Decision Validity Engine — evaluates whether decisions still make sense.
- Classes: ValidityStatus, DecisionValidity, DecisionValidityEngine
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/delegation_followup.py`
- Lines: 229. Doc: Automated delegation follow-up — checks overdue delegations and acts.
- Classes: FollowupAction, FollowupReport, DelegationFollowup
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/delegation_readiness_runtime.py`
- Lines: 516. Doc: Delegation Readiness Runtime — pre-assignment feasibility + outcome prediction.
- Classes: DelegationReadiness, DelegationReadinessSnapshot, DelegationReadinessRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/delegation_runtime.py`
- Lines: 884. Doc: Delegation Runtime — intent classification, delegation proposals, mission lifecycle.
- Classes: OperatorIntentType, DelegationMissionStatus, DelegationMission, DelegationProposal, NestedOrchestratorState, DelegationRuntime
- Functions: classify_intent
- Imports: __future__, dataclasses, enum, json, logging, pathlib, re, time
### `substrate/organism/delegation_topology.py`
- Lines: 203. Doc: Delegation Topology Planner — chooses execution structure for a work packet.
- Classes: TopologyType, DelegationTopology, DelegationTopologyPlanner
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/organism/dependency_graph.py`
- Lines: 402. Doc: Dependency Graph — subsystem dependency model for UMH.
- Classes: DependencyType, DependencyStrength, DependencyNode, DependencyEdge, CriticalPath, DependencyGraph
- Functions: build_dependency_graph, persist_dependency_graph
- Imports: __future__, collections, dataclasses, enum, json, logging, os, time
### `substrate/organism/deploy_verification_worker.py`
- Lines: 530. Doc: Deploy verification worker — no human should discover a white screen.
- Classes: DeployCheckStatus, DeployCheckResult, DeployVerificationResult, DeployVerificationWorker
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, logging, re, time, typing
### `substrate/organism/development_session_bridge.py`
- Lines: 354. Doc: DevelopmentSessionBridge — makes coding agents governed organs of the organism.
- Classes: DevelopmentEvent, CoherenceObservation, DevelopmentSessionBridge
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, pathlib, time, typing
### `substrate/organism/device_awareness.py`
- Lines: 212. Doc: Device Awareness Runtime — deterministic device detection and capability routing.
- Classes: DeviceRecord, DeviceAwarenessRuntime
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, socket, typing
### `substrate/organism/device_capacity.py`
- Lines: 112. Doc: Device Capacity Model — per-device worker slots and backpressure.
- Classes: DeviceCapacity, DeviceCapacityModel
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.organism.device_role_registry, substrate.organism.worker_registry, typing
### `substrate/organism/device_role_registry.py`
- Lines: 278. Doc: Device role registry — tracks device roles and capabilities in the UMH organism.
- Classes: DeviceRole, DeviceCapability, DeviceNodeProfile
- Functions: node_from_dict, _default_registry_path, seed_known_nodes, persist_registry, load_registry, get_node, get_nodes_by_role
- Imports: __future__, dataclasses, enum, json, os, pathlib, typing, uuid
### `substrate/organism/dex_conversation.py`
- Lines: 9. Doc: Backward-compat shim — canonical module is advisor_conversation.py.
- Classes: -
- Functions: -
- Imports: substrate.organism.advisor_conversation
### `substrate/organism/dex_reconciliation.py`
- Lines: 5. Doc: Backward-compat shim — canonical module is advisor_reconciliation.py.
- Classes: -
- Functions: -
- Imports: substrate.organism.advisor_reconciliation
### `substrate/organism/diagnostic_engine.py`
- Lines: 333. Doc: Diagnostic Engine — analyze ingested context for canonical truth state.
- Classes: DiagnosticEngine
- Functions: _load_entity_knowledge, _get_known_entities, _get_expected_products, _get_expected_companies
- Imports: __future__, json, logging, os, substrate.organism.canonical_update, substrate.organism.context_diagnostic, substrate.organism.ingestion_job, substrate.organism.source_registry
### `substrate/organism/distributed_runtime.py`
- Lines: 237. Doc: Distributed Runtime — facade composing all distributed runtime subsystems.
- Classes: DistributedRuntime
- Functions: -
- Imports: __future__, collections, json, logging, pathlib, substrate.organism.device_capacity, substrate.organism.device_role_registry, substrate.organism.packet_router
### `substrate/organism/documentation_awareness_runtime.py`
- Lines: 328. Doc: Documentation Awareness Runtime — content-level metadata for docs.
- Classes: DocumentStatus, DocumentEntry, DocumentationSnapshot, DocumentationAwarenessRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, os, re, time, typing
### `substrate/organism/domain_registry.py`
- Lines: 360. Doc: Domain Registry — first-class domain definitions for the Empire WorkPacket Engine.
- Classes: ProofRequirement, DomainDefinition, DomainRegistry
- Functions: _register
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/drift_detection_engine.py`
- Lines: 255. Doc: Drift Detection Engine — unified drift synthesis.
- Classes: DriftType, UnifiedDriftWarning, DriftDetectionEngine
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/embodiment_runtime.py`
- Lines: 510. Doc: Embodiment Runtime — natural language intent becomes governed work.
- Classes: IntentType, IntentClassification, EmbodimentContext, EmbodimentResponse, ProcessedIntent, RoutingAccuracyReport, EmbodimentRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/empire_router.py`
- Lines: 422. Doc: Empire Router — routes founder intent to domain-classified, governed WorkPackets.
- Classes: RoutingResult, RealitySnapshot, EmpireRouter
- Functions: _repo_root
- Imports: __future__, dataclasses, json, logging, os, time, typing
### `substrate/organism/environment_discovery.py`
- Lines: 347. Doc: Environment Discovery — device, filesystem, application, account inventory.
- Classes: DeviceType, DiscoveryStatus, PermissionState, AppType, UsageStatus, ScopeStatus, FilesystemScope, ApplicationInventoryItem
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/environment_graph.py`
- Lines: 239. Doc: Environment graph — continuously updated operational world-state.
- Classes: TopologyNode, TopologySnapshot, TopologyDiff, EnvironmentGraph
- Functions: -
- Imports: __future__, collections, dataclasses, logging, os, time, typing
### `substrate/organism/environment_reconciler.py`
- Lines: 186. Doc: Environment reconciliation — continuous drift correction.
- Classes: ReconciliationReport, EnvironmentReconciler
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.organism.event_spine, substrate.organism.runtime_graph, time, typing
### `substrate/organism/event_spine.py`
- Lines: 293. Doc: Unified organism event spine — canonical organism-level event transport.
- Classes: EventDomain, EventPriority, OrganismEvent, _Subscriber, EventSpine
- Functions: -
- Imports: __future__, collections, dataclasses, enum, json, logging, os, pathlib
### `substrate/organism/execution_coordinator.py`
- Lines: 1180. Doc: Execution Coordinator Runtime — canonical orchestration layer (Phase 13).
- Classes: ExecutionPlanStatus, ExecutionTargetType, ExecutionMode, ExecutionPriority, CoordinatorApprovalState, LifecycleEventType, CoordinatorExecutionPlan, ExecutorDefinition
- Functions: _repo_root, _coord_data_dir, _ensure_dirs, get_execution_coordinator, reset_execution_coordinator
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/execution_economy.py`
- Lines: 393. Doc: Execution Economy — runtime cost/value tracking and leverage scoring.
- Classes: ExecutionClass, VerificationResult, ExecutionCost, ExecutionValue, RuntimeBenchmark, RuntimePerformanceProfile, TaskExecutionProfile, ExecutionDecisionRecord
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/execution_graph.py`
- Lines: 432. Doc: Execution Graph — evidence-grade lineage validation over existing execution infrastructure.
- Classes: ExecutionNodeType, LineageGap, ExecutionGraphNode, ExecutionGraph
- Functions: validate_lineage, validate_chain, replay_node
- Imports: __future__, dataclasses, enum, json, logging, os, threading, time
### `substrate/organism/execution_journal.py`
- Lines: 241. Doc: ExecutionJournal — append-only execution ledger for all organism mutations.
- Classes: JournalPhase, JournalEntry, ExecutionJournal
- Functions: -
- Imports: __future__, collections, dataclasses, enum, json, logging, pathlib, threading
### `substrate/organism/execution_lifecycle_runtime.py`
- Lines: 423. Doc: Execution Lifecycle Runtime — Campaign 16.2.
- Classes: LifecycleStage, LifecycleArc, ExecutionLifecycleSnapshot, ExecutionLifecycleRuntime
- Functions: _lesson_matches_goal
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/execution_modes.py`
- Lines: 283. Doc: Execution Modes — governed transition from observation to action.
- Classes: ExecutionMode, TransitionReason, ModeTransition, ExecutionDecision, ExecutionModeManager
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/executive_brief_runtime.py`
- Lines: 556. Doc: Executive Brief Runtime — structured operator briefing synthesis.
- Classes: ExecutiveBrief, ExecutiveBriefRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/executive_portfolio_runtime.py`
- Lines: 665. Doc: C14.2 — Executive Portfolio Runtime.
- Classes: ExecutiveHealth, ExecutiveDriftType, ExecutiveDriftWarning, ExecutivePortfolioSnapshot, ExecutivePortfolioRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/executor_runtime.py`
- Lines: 1458. Doc: Executor Runtime — canonical execution contract layer (Phase 14).
- Classes: ExecutorLifecycleStatus, ExecutorType, ExecutorRequestStatus, ExecutorEventType, ExecutorApprovalState, ExecutorRuntimeContext, ExecutorRequest, ExecutorArtifact
- Functions: _repo_root, _executor_data_dir, _ensure_dirs, get_executor_runtime, reset_executor_runtime
- Imports: __future__, abc, dataclasses, enum, json, logging, os, time
### `substrate/organism/executors/__init__.py`
- Lines: 10. Doc: Executor implementations for the UMH Executor Runtime.
- Classes: -
- Functions: -
- Imports: -
### `substrate/organism/executors/agent_executor.py`
- Lines: 829. Doc: AgentExecutor — first governed LLM/Claude Code executor (Phase 17A).
- Classes: AgentTaskResult, AgentExecutionProof, AgentExecutor
- Functions: _validate_working_dir, classify_agent_task_risk, build_agent_runtime_context, _build_agent_prompt, parse_agent_output, _redact_output
- Imports: __future__, dataclasses, json, logging, os, pathlib, re, signal
### `substrate/organism/executors/approval_intercept.py`
- Lines: 675. Doc: Approval Intercepts — runtime human-in-the-loop governance for executors.
- Classes: ApprovalInterceptStatus, ApprovalInterceptRequest, ApprovalInterceptStore, ApprovalInterceptService, ApprovalScope, ApprovalPolicy, ApprovalDecision, ApprovalPolicyRegistry
- Functions: classify_operation_risk, requires_approval, get_approval_intercept_service, reset_approval_intercept_service
- Imports: __future__, dataclasses, enum, logging, threading, time, typing, uuid
### `substrate/organism/executors/execution_telemetry.py`
- Lines: 404. Doc: Execution Telemetry — live event pipeline for executor lifecycle.
- Classes: TelemetryEventType, ExecutionTelemetryEvent, InMemoryExecutionTelemetryStore, ExecutionTelemetryEmitter
- Functions: _value_looks_secret, _redact_value, redact_telemetry_payload, get_telemetry_emitter, reset_telemetry_emitter
- Imports: __future__, collections, dataclasses, enum, json, logging, re, threading
### `substrate/organism/executors/workstation_executor.py`
- Lines: 786. Doc: WorkstationExecutor — first production ExecutorContract implementation.
- Classes: ExecutionProof, WorkstationExecutor
- Functions: _is_safe_without_approval, _resolve_and_validate, _check_blocked, _op_create_worktree, _op_run_command, _op_read_file, _op_write_file, _op_list_directory, _sanitize
- Imports: __future__, dataclasses, json, logging, os, pathlib, substrate.execution.cpu_gate, substrate.organism.executor_runtime
### `substrate/organism/goal_alignment_engine.py`
- Lines: 215. Doc: Goal Alignment Engine — ensure work supports goals.
- Classes: AlignmentReport, GoalAlignmentEngine
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/goal_drift_engine.py`
- Lines: 265. Doc: Goal Drift Engine — detect movement away from objectives.
- Classes: GoalDriftType, GoalDriftWarning, GoalDriftSnapshot, GoalDriftEngine
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/goal_hierarchy_engine.py`
- Lines: 227. Doc: Goal Hierarchy Engine — structural operations on the goal tree.
- Classes: HierarchyValidation, GoalHierarchyEngine
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/organism/governance_runtime.py`
- Lines: 687. Doc: C15.0 — Governance Runtime.
- Classes: GovernanceAuthority, ConflictStatus, ConflictSeverityLevel, GovernanceHealth, GovernanceDriftType, SubsystemConflict, GovernancePolicy, GovernanceDriftWarning
- Functions: _conflict_id
- Imports: __future__, dataclasses, enum, hashlib, logging, time, typing
### `substrate/organism/governed_execution_runtime.py`
- Lines: 489. Doc: Governed Execution Runtime — Campaign 16.0.
- Classes: ExecutionState, ExecutionBlocker, GovernedExecutionHealth, ExecutionStateAssessment, GovernedExecutionSnapshot, GovernedExecutionRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/governed_spine.py`
- Lines: 612. Doc: GovernedExecutionSpine — THE single mutation gateway in the organism.
- Classes: SpineViolation, GovernedExecutionSpine
- Functions: -
- Imports: __future__, collections, logging, substrate.organism.action_envelope, substrate.organism.coherence_propagation, substrate.organism.event_spine, substrate.organism.execution_journal, substrate.organism.execution_modes
### `substrate/organism/governed_work_runtime.py`
- Lines: 498. Doc: Governed Work Runtime — MANDATORY execution gateway.
- Classes: WorkSubmission, ExecutionReceipt, WorkStatus, GovernedWorkRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/organism/grounded_handlers.py`
- Lines: 544. Doc: Grounded status handlers — deterministic answers backed by real data.
- Classes: -
- Functions: _make_response, _format_missing, _format_response_with_missing, handle_grounded_status, handle_grounded_docker, handle_grounded_providers, handle_grounded_blocked, handle_grounded_agents, handle_grounded_resume, handle_grounded_vision, handle_grounded_beast, _fetch_latest_frame
- Imports: __future__, json, logging, typing
### `substrate/organism/grounding_registry.py`
- Lines: 625. Doc: Grounding registry — source data requirements for deterministic status answers.
- Classes: GroundingSource, GroundedResult
- Functions: _collect_docker, _collect_providers, _collect_voice, _collect_vision, _collect_work_packets, _collect_blocked_packets, _collect_workcell_heartbeats, _collect_beast_health, _collect_recent_reports, _collect_approvals, _collect_recent_deployments, _collect_hermes_status
- Imports: __future__, dataclasses, datetime, http.client, json, logging, os, pathlib
### `substrate/organism/handoff.py`
- Lines: 227. Doc: Agent handoff protocol — structured agent-to-agent task transfer.
- Classes: HandoffType, HandoffStatus, HandoffRequest, HandoffResult, HandoffRouter
- Functions: -
- Imports: __future__, enum, logging, pydantic, substrate.organism.protocols, time, typing, uuid
### `substrate/organism/homeostasis.py`
- Lines: 477. Doc: Homeostasis — the organism's immune/self-regulation system.
- Classes: SystemMode, HealthDimension, DimensionStatus, HomeostasisReport, Override, HomeostasisEngine
- Functions: -
- Imports: __future__, collections, dataclasses, datetime, enum, logging, time, typing
### `substrate/organism/impact_analyzer.py`
- Lines: 324. Doc: Impact Analyzer — computes change impact across the propagation graph.
- Classes: ImpactedNode, ImpactAnalysis, ImpactAnalyzer
- Functions: -
- Imports: __future__, collections, dataclasses, enum, logging, substrate.organism.change_event, substrate.organism.propagation_graph, time
### `substrate/organism/infrastructure_runtime.py`
- Lines: 393. Doc: Infrastructure Runtime — register and track system & institutional infrastructure.
- Classes: InfrastructureType, InfrastructureHealth, InfrastructureEntity, InfrastructureRuntime
- Functions: -
- Imports: __future__, collections, dataclasses, enum, json, logging, os, threading
### `substrate/organism/ingestion_job.py`
- Lines: 260. Doc: Ingestion Job — tracks context ingestion work units.
- Classes: JobType, JobStatus, IngestedItem, IngestionJob, IngestionJobStore
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/institutional_memory_runtime.py`
- Lines: 558. Doc: C15.2 — Institutional Memory Runtime.
- Classes: KnowledgeState, InstitutionalMemoryHealth, MemoryDriftType, InstitutionalKnowledge, InstitutionalMemoryDriftWarning, InstitutionalMemorySnapshot, InstitutionalMemoryRuntime
- Functions: _knowledge_id
- Imports: __future__, dataclasses, enum, hashlib, logging, time, typing
### `substrate/organism/intent_classifier.py`
- Lines: 325. Doc: Intent Classifier — converts raw user intent into structured classification.
- Classes: IntentClassification, IntentClassifier
- Functions: _load_entity_patterns, _load_entity_metadata
- Imports: __future__, dataclasses, logging, re, typing
### `substrate/organism/knowledge_awareness_runtime.py`
- Lines: 271. Doc: Knowledge Awareness Runtime — meaning, not just documents.
- Classes: KnowledgeType, KnowledgeEntry, KnowledgeSnapshot, KnowledgeAwarenessRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, hashlib, logging, re, time, typing
### `substrate/organism/knowledge_model_registry.py`
- Lines: 168. Doc: Knowledge Model Registry — system knowledge containers.
- Classes: KnowledgeModel, KnowledgeModelRegistry
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, tempfile, time, typing
### `substrate/organism/learning_extraction_runtime.py`
- Lines: 691. Doc: Learning Extraction Runtime — Campaign 12.0
- Classes: LessonCategory, ExtractedLesson, LessonExtractionSnapshot, LearningExtractionRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, hashlib, json, logging, os, time
### `substrate/organism/learning_portfolio_runtime.py`
- Lines: 563. Doc: Learning Portfolio Runtime — Campaign 12.3
- Classes: LearningHealth, LearningDriftType, LearningDriftWarning, LearningPortfolioSnapshot, LearningPortfolioRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/leverage_assimilation.py`
- Lines: 619. Doc: External Leverage Assimilation — ingest, classify, and operationalize
- Classes: ArtifactType, LeveragePrimitiveType, AssimilationStatus, LeverageScore, ExtractedPrimitive, AssimilationArtifact, LeverageAssimilator
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, pathlib, time, typing
### `substrate/organism/leverage_engine.py`
- Lines: 299. Doc: Leverage Engine — determines highest-impact actions.
- Classes: LeverageEvidence, LeverageOpportunity, LeverageEngine
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/organism/leverage_metrics.py`
- Lines: 263. Doc: Operational Leverage Metrics — measures actual organism value.
- Classes: TaskRecord, LeverageDimensions, LeverageMetrics
- Functions: -
- Imports: __future__, collections, dataclasses, logging, time, typing
### `substrate/organism/maintenance_loop.py`
- Lines: 314. Doc: Autonomous Maintenance Loop — OBSERVE-mode infrastructure health cycle.
- Classes: ActionSeverity, ActionCategory, MaintenanceRecommendation, MaintenanceCycleReport, MaintenanceLoop
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.event_spine, substrate.organism.execution_modes, substrate.organism.workload_runner, time
### `substrate/organism/memory_promotion.py`
- Lines: 515. Doc: Memory Promotion Pipeline — governed promotion from instance to canonical memory.
- Classes: MemoryPromotionStatus, MemoryScope, MemoryCategory, MemoryEvidence, MemoryCandidate, MemoryPromotionDecision, CanonicalMemoryEntry, MemoryPromotionPipeline
- Functions: _check_promotion_eligibility, _needs_operator_approval
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/mesh_reconciler.py`
- Lines: 218. Doc: Mesh node reconciliation — syncs RuntimeGraph with live mesh relay.
- Classes: MeshReconcileReport, MeshReconciler
- Functions: _detect_relay_host, _load_device_registry, _resolve_device_id
- Imports: __future__, dataclasses, json, logging, os, substrate.organism.runtime_graph, time, typing
### `substrate/organism/meta_ide_runtime.py`
- Lines: 539. Doc: Meta IDE Runtime — unified development surface.
- Classes: ReviewStatus, DevelopmentPhase, WorkspaceSnapshot, IDEPlan, DevelopmentStream, ReviewDetail, MergeResult, IDEStatusSnapshot
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/mission.py`
- Lines: 257. Doc: Mission — bridge between user conversation and organism execution.
- Classes: MissionStatus, MissionResult, Mission
- Functions: mission_from_user_intent, execute_mission, synthesize_mission_result
- Imports: __future__, dataclasses, enum, logging, substrate.organism.coordinator, time, typing, uuid
### `substrate/organism/mutation_registry.py`
- Lines: 462. Doc: MutationRegistry — canonical registry of executable mutation types.
- Classes: MutationSpec, MutationRegistry
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.organism.action_envelope, substrate.organism.execution_modes, typing
### `substrate/organism/next_action_engine.py`
- Lines: 276. Doc: Next Action Engine — evidence-based action recommender.
- Classes: ActionPriority, ActionCategory, ActionEvidence, NextAction, NextActionEngine
- Functions: _score_to_priority
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/objective_physics.py`
- Lines: 321. Doc: Objective Physics — causal execution dynamics.
- Classes: ObjectiveState, ObjectiveNode, CriticalPath, LeveragePropagation, ObjectivePhysics
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/objective_queue.py`
- Lines: 232. Doc: Continuous objective queue — intake front door for OrganismCoordinator.
- Classes: ObjectiveQueueStatus, ObjectiveRequest, ObjectiveQueue
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.event_spine, time, typing, uuid
### `substrate/organism/observability.py`
- Lines: 330. Doc: Organism Observability — unified dashboard snapshot.
- Classes: BottleneckReport, OrganismSnapshot, OrganismObserver
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.organism.coordinator, substrate.organism.homeostasis, substrate.organism.runtime_graph, substrate.organism.runtime_supervisor, substrate.organism.workcell_daemon
### `substrate/organism/operating_loop_coherence_runtime.py`
- Lines: 476. Doc: Operating Loop Coherence Runtime — aggregation, reporting, coherence synthesis.
- Classes: LoopCoherenceStatus, LoopCoherenceIssueType, LoopCoherenceIssue, LoopCoherenceReport, OperatingLoopCoherenceRuntime
- Functions: _safe_call, _safe_dict, _safe_list
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/operational_truth.py`
- Lines: 364. Doc: OperationalTruthSnapshot — scoreboard for UMH operational reality.
- Classes: OperationalReadinessStatus, IssuePriority, IssueStatus, FixEffort, OperationalIssue, ContainerState, ServiceState, LLMProviderState
- Functions: collect_snapshot, persist_snapshot, persist_issues
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, pathlib
### `substrate/organism/operationalization_runtime.py`
- Lines: 400. Doc: Operationalization Runtime — link capabilities to reusable artifacts.
- Classes: OperationalizationForm, OperationalizationStatus, Operationalization, OperationalizationRuntime
- Functions: extract_invariants_from_steps, compute_reuse_score
- Imports: __future__, collections, dataclasses, enum, json, logging, os, threading
### `substrate/organism/operator_acceptance.py`
- Lines: 299. Doc: Operator acceptance run model — end-to-end acceptance test tracking.
- Classes: AcceptanceRunStatus, OperatorAcceptanceRun, OperatorAcceptanceArtifact
- Functions: create_run, create_artifact, run_from_dict, artifact_from_dict, _default_persist_dir, persist_run, persist_artifact, load_runs, load_artifacts, get_run
- Imports: __future__, dataclasses, enum, json, logging, os, pathlib, time
### `substrate/organism/operator_acceptance_mode.py`
- Lines: 379. Doc: Operator acceptance mode — standard multi-runtime vs deterministic-only vs blocked.
- Classes: OperatorAcceptanceMode, OperatorAcceptanceModeDecision
- Functions: to_dict, from_dict, create_standard_mode_decision, create_deterministic_mode_decision, select_acceptance_mode, persist_mode_decision, load_mode_decisions
- Imports: __future__, dataclasses, enum, json, logging, os, pathlib, time
### `substrate/organism/operator_acceptance_scenarios.py`
- Lines: 249. Doc: Operator acceptance scenarios — predefined end-to-end test scenarios.
- Classes: AcceptanceScenario
- Functions: get_all_scenarios, get_scenario, export_scenarios_json
- Imports: __future__, dataclasses, datetime, json, typing
### `substrate/organism/operator_compression.py`
- Lines: 196. Doc: Operator Compression — reduce human operational burden.
- Classes: InterventionType, OperatorAction, AutomationCandidate, OperatorCompression
- Functions: -
- Imports: __future__, collections, dataclasses, enum, logging, time, typing
### `substrate/organism/operator_loop_coordinator.py`
- Lines: 786. Doc: Operator loop coordinator — orchestrates the end-to-end acceptance loop.
- Classes: OperatorLoopCoordinator
- Functions: _build_implementation_report
- Imports: __future__, json, logging, os, substrate.organism.operator_acceptance, substrate.organism.operator_acceptance_mode, substrate.organism.operator_readiness_gate, time
### `substrate/organism/operator_loop_runtime.py`
- Lines: 392. Doc: Operator Loop Runtime — the Jarvis Runtime.
- Classes: OperatorLoopPhase, OperatorLoopState, OperatorLoopRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/operator_migration_runtime.py`
- Lines: 465. Doc: Operator Migration Runtime — track and close external-loop dependencies.
- Classes: ExitReason, MigrationStatus, ExitEvent, ExitClassification, MigrationPriority, CoverageReport, OperationalizationSuggestion, Migration
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/operator_readiness_gate.py`
- Lines: 307. Doc: OperatorReadinessGate — Phase 13.4 readiness assessment.
- Classes: OperatorReadinessReport
- Functions: _detect_cli_runtime, _detect_runtime_fleet, assess_readiness, persist_readiness_report
- Imports: __future__, dataclasses, json, logging, os, pathlib, shutil, subprocess
### `substrate/organism/operator_response.py`
- Lines: 218. Doc: Operator Response — structured response contract for the orchestrator kernel.
- Classes: OutputMode, Option, OperatorResponse
- Functions: _default_responses_path, persist_responses, load_responses
- Imports: __future__, dataclasses, enum, json, logging, os, tempfile, time
### `substrate/organism/operator_session.py`
- Lines: 350. Doc: Operator Session — conversational state for operator-orchestrator interaction.
- Classes: SessionStatus, IntentType, OperatorIntent, OperatorTurn, OperatorSession
- Functions: _default_sessions_path, persist_sessions, load_sessions, persist_turns, persist_intents
- Imports: __future__, dataclasses, enum, json, logging, os, tempfile, time
### `substrate/organism/orchestration_loop.py`
- Lines: 448. Doc: Orchestration loop — persistent autonomous execution for the organism.
- Classes: -
- Functions: _get_daemon, _emit_stage_event, _stage_organism_tick, _stage_health_check, _stage_homeostasis, _stage_recovery, _stage_delegation_check, _stage_objective_advance, _stage_state_persist, _stage_work_queue_drain, register_organism_stages, create_orchestration_loop
- Imports: __future__, asyncio, logging, substrate.execution.loop.persistent_loop, time, typing
### `substrate/organism/orchestrator_awareness_runtime.py`
- Lines: 586. Doc: Orchestrator Awareness Runtime — synthesized reality model for the orchestrator.
- Classes: AwarenessDomain, OrchestratorContext, DomainAwareness, OrchestratorAwarenessSnapshot, OrchestratorAwarenessRuntime
- Functions: _safe_call, _safe_dict, _safe_list
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/orchestrator_kernel.py`
- Lines: 941. Doc: Orchestrator Kernel — central intelligence routing for operator interaction.
- Classes: OrchestratorKernel
- Functions: -
- Imports: __future__, logging, os, re, substrate.organism.operator_response, substrate.organism.operator_session, time, typing
### `substrate/organism/organism_coordination_engine.py`
- Lines: 498. Doc: C15.1 — Organism Coordination Engine.
- Classes: CoordinationIssueType, CoordinationHealth, CoordinationIssue, CoordinationSnapshot, OrganismCoordinationEngine
- Functions: _health_to_score, _issue_id
- Imports: __future__, dataclasses, enum, hashlib, logging, time, typing
### `substrate/organism/organism_loop.py`
- Lines: 498. Doc: OrganismLoopEngine -- convergence coordinator for organism execution.
- Classes: OrganismLoopResult, OrganismLoopEngine
- Functions: -
- Imports: __future__, asyncio, dataclasses, logging, substrate.execution.executor, substrate.governance.policy_engine, substrate.governance.risk_classes, substrate.memory.canonical_write
### `substrate/organism/organism_portfolio_runtime.py`
- Lines: 423. Doc: C15.3 — Organism Portfolio Runtime.
- Classes: OrganismHealth, OrganismDriftType, OrganismDriftWarning, SubsystemHealthEntry, OrganismPortfolioSnapshot, OrganismPortfolioRuntime
- Functions: _health_to_score
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/organism_state_runtime.py`
- Lines: 283. Doc: Organism State Runtime — Campaign 16.1.
- Classes: OrganismMode, OrganismStateSnapshot, OrganismStateRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/outcome_learning.py`
- Lines: 380. Doc: Outcome Learning Loop — learn from execution outcomes.
- Classes: OutcomeStatus, SignalType, OutcomeRecord, LearningSignal, OutcomeEvaluation, RecommendationAdjustment, ReliabilityUpdate, OutcomeLearningLoop
- Functions: -
- Imports: __future__, collections, dataclasses, enum, json, logging, os, time
### `substrate/organism/outcome_pattern_engine.py`
- Lines: 749. Doc: Outcome Pattern Engine — Campaign 12.1
- Classes: PatternType, DetectedPattern, AttributionLink, PatternSnapshot, OutcomePatternEngine
- Functions: -
- Imports: __future__, dataclasses, enum, hashlib, json, logging, os, time
### `substrate/organism/outcome_tracking_runtime.py`
- Lines: 253. Doc: Outcome Tracking Runtime — measure progress toward goals.
- Classes: OutcomeProgress, OutcomeSnapshot, OutcomeTrackingRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/outcome_verification.py`
- Lines: 450. Doc: Outcome verification engine — replaces 'Task Complete' with 'Outcome Verified'.
- Classes: VerificationLevel, OutcomeVerificationStatus, VerificationMethod, VerificationStepResult, VerificationPlanStep, VerificationPlan, OutcomeVerification, VerificationPlanRegistry
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, typing
### `substrate/organism/packet_router.py`
- Lines: 287. Doc: Packet Router — capability-first work routing.
- Classes: PacketPlacement, PacketRouter
- Functions: -
- Imports: __future__, dataclasses, logging, re, substrate.organism.device_capacity, substrate.organism.device_role_registry, substrate.organism.worker_registry, time
### `substrate/organism/parallel.py`
- Lines: 213. Doc: Parallel agent execution — run multiple agents concurrently.
- Classes: ParallelTask, ParallelResult, ParallelCoordinator
- Functions: -
- Imports: __future__, concurrent.futures, dataclasses, logging, substrate.organism.protocols, time, typing, uuid
### `substrate/organism/permission_dialogue.py`
- Lines: 395. Doc: Socratic Permission Engine — ask before expanding context access.
- Classes: ApprovalOption, RequestStatus, Sensitivity, PermissionRequest, PermissionPreference, SocraticPermissionEngine
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/plan_execution_adapter.py`
- Lines: 716. Doc: Plan Execution Adapter — bridges CompositionPlan to GovernedExecutionSpine.
- Classes: ExecutionGraphStatus, StepExecutionStatus, ExecutionDependency, ExecutableStep, ExecutablePlan, ExecutionGraph, PlanExecutionAdapter
- Functions: _infer_action_type
- Imports: __future__, dataclasses, enum, logging, substrate.organism.action_envelope, substrate.organism.composition_engine, substrate.organism.memory_promotion, substrate.organism.outcome_learning
### `substrate/organism/prediction_portfolio_runtime.py`
- Lines: 524. Doc: Prediction Portfolio Runtime — Campaign 13.2
- Classes: PredictionHealth, PredictionDriftType, PredictionDriftWarning, PredictionPortfolioSnapshot, PredictionPortfolioRuntime
- Functions: _get_attr, _to_dict
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/presence_runtime.py`
- Lines: 974. Doc: Presence Runtime — operator presence awareness for UMH.
- Classes: PresenceAttentionState, InterruptionLevel, PresenceEventType, InteractionSurface, DeviceInfo, SessionInfo, PresenceSnapshot, PresenceEvent
- Functions: _repo_root, _presence_data_dir, _ensure_dirs, get_presence_runtime, reset_presence_runtime
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/priority_engine.py`
- Lines: 239. Doc: Priority Engine — deterministic priority synthesis.
- Classes: PrioritizedItem, PriorityEngine
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/organism/product_factory_runtime.py`
- Lines: 788. Doc: C22.5 — Product Factory Runtime.
- Classes: ProductGoalType, ProductReadiness, ProductGoal, ProductPlan, ProductEntry, ProductFactorySnapshot, ProductFactoryRuntime
- Functions: _estimate_complexity, _classify_goal_type, _classify_goal_risk, _build_dependency_order, _estimate_roles
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/production_merge_verifier.py`
- Lines: 612. Doc: Production Merge Verifier — confirms sandboxed PR became production truth.
- Classes: MergeVerificationStatus, ProductionMergeVerification, ProductionPromotionDecision, ProductionMergeVerifier
- Functions: _run_cmd, _gh_available
- Imports: __future__, dataclasses, enum, json, logging, os, subprocess, substrate.execution.cpu_gate
### `substrate/organism/production_ops_runtime.py`
- Lines: 576. Doc: Production Operations Runtime — Campaign 22.0.
- Classes: ProductionPhase, ProductionTarget, ProductionHealth, ProductionEntry, ProductionSnapshot, ProductionOpsRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/production_planning_runtime.py`
- Lines: 646. Doc: C22.1 — Production Planning Runtime.
- Classes: ProductionDiscipline, ProductionType, ProductionPlan, DisciplinePacket, ProductionPlanningRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/production_review_runtime.py`
- Lines: 848. Doc: C22.3 — Production Review Runtime.
- Classes: ReviewVerdict, QualityDimension, QualityCheck, ProductionReviewResult, ReviewHistory, ShipReadinessReport, ProductionReviewSnapshot, ProductionReviewRuntime
- Functions: _run_gate_script, _check_tests, _check_architecture, _check_security_deterministic, _check_observability, _check_deployment_readiness, run_all_quality_checks, determine_verdict
- Imports: __future__, dataclasses, enum, logging, os, time, typing
### `substrate/organism/production_truth_delta.py`
- Lines: 445. Doc: Production Truth Delta — what actually changed in production after merge.
- Classes: DeltaStatus, StateSnapshot, FileDivergence, PostMergeValidationResult, ProductionTruthDelta, CorrespondenceStatus, CorrespondenceResult, CorrespondenceChecker
- Functions: -
- Imports: __future__, collections, dataclasses, datetime, enum, logging, substrate.execution.cpu_gate, time
### `substrate/organism/production_workforce_runtime.py`
- Lines: 703. Doc: Production Workforce Runtime — Campaign 22.2.
- Classes: ProductionRole, ProductionAuthority, ProductionAssignment, ProductionProgress, OrgChartNode, ProductionWorkforceRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/profile_runtime.py`
- Lines: 1491. Doc: Profile Runtime — canonical authority for operator work identity and system modes.
- Classes: ProfileModeEnum, SystemModeEnum, ActivationSource, ProfileEventType, ConflictSeverity, Profile, SystemMode, ProfileModeState
- Functions: _repo_root, _profile_data_dir, _ensure_dirs, _default_profiles, _default_system_modes, get_profile_runtime, reset_profile_runtime
- Imports: __future__, dataclasses, enum, json, logging, os, re, time
### `substrate/organism/project_registry.py`
- Lines: 162. Doc: Project Registry — first-class project entities for UMH.
- Classes: ProjectDefinition, ProjectRegistry
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, typing
### `substrate/organism/projection_certification.py`
- Lines: 455. Doc: Projection certification framework — graduated L0-L5 certification.
- Classes: CertificationLevel, LevelCheckResult, ProjectionCertification, ProjectionConfig, ProjectionRegistry, ProjectionCertificationEngine
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, typing
### `substrate/organism/projection_engine.py`
- Lines: 1450. Doc: Projection Engine — predictive world-model layer for UMH.
- Classes: TimeHorizon, TrendDirection, RiskSeverity, ProjectionConfidence, TrendRecord, TrendDetector, Projection, StrategicRisk
- Functions: _repo_root, _projection_data_dir, _ensure_dirs, get_projection_engine, reset_projection_engine
- Imports: __future__, dataclasses, enum, hashlib, json, logging, math, os
### `substrate/organism/projection_integration_runtime.py`
- Lines: 581. Doc: Projection Integration Runtime — audit/mapping layer over projections.
- Classes: ProjectionMachineType, ProjectionAvailability, ProjectionMaturityLevel, IntegrationGapType, ProjectionCodeLocation, ProjectionIntegrationGap, ProjectionIntegrationProfile, ProjectionBuildReadiness
- Functions: _normalize_projection_id
- Imports: __future__, dataclasses, enum, logging, os, time, typing, uuid
### `substrate/organism/projection_port.py`
- Lines: 158. Doc: Projection-agnostic organism state port.
- Classes: StateSlice, ProjectionSubscriber, OrganismStatePort
- Functions: -
- Imports: __future__, abc, enum, json, logging, pathlib, typing
### `substrate/organism/projection_readiness_gate.py`
- Lines: 135. Doc: Projection Readiness Gate — blocks feature build until source reconciliation is sufficient.
- Classes: -
- Functions: _file_exists, _load_json, assess_projection_readiness
- Imports: __future__, json, logging, os, typing
### `substrate/organism/projection_reconciliation_engine.py`
- Lines: 324. Doc: Projection Reconciliation Engine — diagnoses divergence across projection sources.
- Classes: DivergenceType, DivergenceSeverity, ProjectionDivergence, ProjectionReconciliationEngine
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, substrate.organism.projection_source_registry, time
### `substrate/organism/projection_source_registry.py`
- Lines: 253. Doc: Projection Source Registry — tracks sources per projection for reconciliation.
- Classes: ProjectionSourceType, ProjectionName, SourceCanonicality, ReadStatus, ProjectionSource, ProjectionSourceRegistry
- Functions: create_initial_registry
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/promotion_threshold_policy.py`
- Lines: 272. Doc: Promotion Threshold Policy — governs cadence mode transitions.
- Classes: CadenceLevel, ThresholdSpec, ThresholdEvaluation, PromotionThresholdPolicy
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.reliability_signals, typing
### `substrate/organism/proof_runtime.py`
- Lines: 254. Doc: Proof Runtime — complete proof packages per execution.
- Classes: ProofEvidence, ProofPackage, _PendingSnapshot, ProofRuntime
- Functions: -
- Imports: __future__, collections, dataclasses, logging, time, typing, uuid
### `substrate/organism/propagation_executor.py`
- Lines: 240. Doc: Propagation Executor — executes propagation plans in dry-run or governed mode.
- Classes: ExecutionMode, PropagationExecutor
- Functions: -
- Imports: __future__, json, logging, os, substrate.organism.change_event, substrate.organism.propagation_graph, time, typing
### `substrate/organism/propagation_graph.py`
- Lines: 434. Doc: Propagation Graph — dependency-aware change propagation model.
- Classes: PropagationNodeType, PropagationEdgeType, PropagationMode, EdgeStrength, PropagationNode, PropagationEdge, PropagationGraph
- Functions: -
- Imports: __future__, collections, dataclasses, enum, json, logging, os, time
### `substrate/organism/propagation_graph_builder.py`
- Lines: 533. Doc: Propagation Graph Builder — extracts nodes and edges from real system state.
- Classes: PropagationGraphBuilder
- Functions: -
- Imports: __future__, json, logging, os, substrate.organism.propagation_graph, time, typing, uuid
### `substrate/organism/propagation_planner.py`
- Lines: 197. Doc: Propagation Planner — creates wave-based propagation plans.
- Classes: PropagationPlanner
- Functions: -
- Imports: __future__, logging, substrate.organism.change_event, substrate.organism.impact_analyzer, substrate.organism.propagation_graph, time, typing, uuid
### `substrate/organism/propagation_wiring.py`
- Lines: 297. Doc: Propagation wiring — registers all propagation targets with the engine.
- Classes: -
- Functions: _build_outcome_learning_handler, _build_template_generation_handler, _build_memory_generation_handler, _build_agent_capability_handler, _build_world_model_evidence_handler, _build_contradiction_recheck_handler, _build_readiness_recalculate_handler, _build_bottleneck_recalculate_handler, _build_composition_refresh_handler, _build_dependency_recompute_handler, build_propagation_engine
- Imports: __future__, logging, substrate.organism.agent_capability_model, substrate.organism.coherence_propagation, substrate.organism.outcome_learning, substrate.organism.template_registry, typing
### `substrate/organism/protocols.py`
- Lines: 76. Doc: Organism protocols — typed contracts for the agent society.
- Classes: AgentStatus, CritiqueResult, Deliverable, AgentMessage, WorkerSpec, LearningSignal
- Functions: -
- Imports: __future__, datetime, enum, pydantic, typing, uuid
### `substrate/organism/readiness_model.py`
- Lines: 420. Doc: System Readiness Model — 6-dimension readiness assessment.
- Classes: DimensionScore, ReadinessReport, ReadinessModel
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/reality_graph.py`
- Lines: 761. Doc: Reality Graph — canonical operator-world graph for UMH.
- Classes: RealityEntityType, RealityRelationType, RealityEntityStatus, RealityEntity, RealityRelation, RealityGraph
- Functions: -
- Imports: __future__, collections, dataclasses, enum, json, logging, os, time
### `substrate/organism/recommendation_engine.py`
- Lines: 241. Doc: Recommendation Engine — unified action recommendation synthesis.
- Classes: UnifiedRecommendation, RecommendationEngine
- Functions: _token_overlap
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/organism/reconciliation_engine.py`
- Lines: 266. Doc: Reconciliation Engine — structured context reconciliation sessions.
- Classes: ReconciliationEngine
- Functions: -
- Imports: __future__, logging, substrate.organism.canonical_update, substrate.organism.context_diagnostic, substrate.organism.context_ingestion_engine, substrate.organism.diagnostic_engine, substrate.organism.ingestion_job, substrate.organism.reconciliation_session
### `substrate/organism/reconciliation_session.py`
- Lines: 235. Doc: Reconciliation Session — structured operator-AI context alignment.
- Classes: SessionStatus, ReconciliationMode, ReconciliationDecision, ReconciliationSession, ReconciliationSessionStore
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/recursion_governance.py`
- Lines: 405. Doc: Recursion Governance — bounded recursive execution control.
- Classes: EscalationLevel, RecursionApproval, RecursionLimits, RecursionState, EscalationEvent, GovernanceCheckResult, RecursionGovernor
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.execution_economy, time, typing
### `substrate/organism/reliability_signals.py`
- Lines: 465. Doc: Reliability Signal Model — normalizes production-backed signals for cadence ranking.
- Classes: TemplateReliabilitySignal, AgentReliabilitySignal, CandidateSourceReliabilitySignal, ValidationReliabilitySignal, RollbackReliabilitySignal, ProductionTruthReliabilitySignal, ReliabilitySignalBundle, ReliabilitySignalAggregator
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, typing
### `substrate/organism/reliability_weighted_ranker.py`
- Lines: 301. Doc: Reliability-Weighted Ranker — deterministic candidate ranking using production signals.
- Classes: PromotionClass, RankedCandidate, ReliabilityWeightedRanker
- Functions: -
- Imports: __future__, dataclasses, enum, logging, substrate.organism.reliability_signals, typing
### `substrate/organism/report_dispatcher.py`
- Lines: 246. Doc: Report dispatcher — sends task completion reports to Discord + cockpit chat.
- Classes: Report, DispatchResult, ReportDispatcher
- Functions: -
- Imports: __future__, dataclasses, datetime, io, json, logging, os, pathlib
### `substrate/organism/repository_awareness_runtime.py`
- Lines: 307. Doc: Repository Awareness Runtime — file-level depth for repositories.
- Classes: FileCategory, FileEntry, RepositorySnapshot, RepositoryAwarenessRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, os, time, typing
### `substrate/organism/resource_allocation_runtime.py`
- Lines: 689. Doc: C14.0 — Resource Allocation Runtime.
- Classes: ResourceType, AllocationPriority, AllocationHealth, AllocationRecommendation, ResourceBudget, AllocationSnapshot, ResourceAllocationRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/risk_engine.py`
- Lines: 243. Doc: Risk Engine — unified risk register synthesis.
- Classes: RiskCategory, UnifiedRisk, RiskEngine
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/roadmap_engine.py`
- Lines: 165. Doc: Roadmap Engine — phase linkage model for self-build queue.
- Classes: RoadmapPhase, RoadmapEngine
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, tempfile, time, typing
### `substrate/organism/role_contracts.py`
- Lines: 244. Doc: Role Contracts + Capability Profiles — template-based role definitions.
- Classes: CapabilityProfile, RoleContract
- Functions: persist_role_contracts, load_role_contracts
- Imports: __future__, dataclasses, json, logging, os, tempfile, time, typing
### `substrate/organism/runtime_adapter.py`
- Lines: 121. Doc: Runtime adapter interface — abstract contract for execution surfaces.
- Classes: RuntimeStartRequest, RuntimeStartResult, RuntimeInjectRequest, RuntimeAdapter
- Functions: -
- Imports: __future__, abc, dataclasses, typing
### `substrate/organism/runtime_adapters.py`
- Lines: 890. Doc: Concrete RuntimeAdapter implementations for UMH runtimes.
- Classes: CCSDKAdapter, CodexAdapter, HermesAdapter, OpenCodeAdapter, GeminiAdapter, OllamaAdapter, DockerAdapter, TmuxAdapter
- Functions: _discover_docker_containers, _discover_tmux_sessions, build_default_graph
- Imports: __future__, logging, os, shutil, substrate.execution.cpu_gate, substrate.organism.runtime_graph, typing
### `substrate/organism/runtime_awareness_runtime.py`
- Lines: 214. Doc: Runtime Awareness Runtime — unified view of active system state.
- Classes: RuntimeAwarenessSnapshot, RuntimeAwarenessRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/organism/runtime_fleet.py`
- Lines: 360. Doc: Runtime fleet model — tracks available runtime providers and selection decisions.
- Classes: RuntimeProvider, RuntimeCostModel, RuntimeReadiness, RuntimeFleetMember, RuntimeSelection
- Functions: create_fleet_member, create_selection, member_from_dict, selection_from_dict, _fleet_path, _selections_path, persist_fleet, persist_selection, load_fleet, load_selections, get_capable_runtimes, has_capable_runtime
- Imports: __future__, dataclasses, enum, json, logging, os, pathlib, time
### `substrate/organism/runtime_graph.py`
- Lines: 410. Doc: RuntimeGraph — canonical runtime registry with dynamic availability.
- Classes: AvailabilityStatus, RuntimeClass, RuntimeCapability, CostProfile, ReliabilityScore, RuntimeAdapter, RuntimeResult, RuntimeNode
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/runtime_handoff.py`
- Lines: 209. Doc: Runtime handoff — bridges Work Packets to runtime sessions.
- Classes: RuntimeHandoffPreview
- Functions: classify_runtime_need, create_handoff_preview, execute_approved_handoff
- Imports: __future__, dataclasses, logging, substrate.organism.runtime_manager, substrate.organism.runtime_session, time, typing, uuid
### `substrate/organism/runtime_manager.py`
- Lines: 387. Doc: Runtime manager — orchestrates governed runtime session lifecycle.
- Classes: RuntimePolicyViolation, RuntimeManager
- Functions: -
- Imports: __future__, logging, os, subprocess, substrate.execution.cpu_gate, substrate.organism.claude_code_runtime_adapter, substrate.organism.runtime_adapter, substrate.organism.runtime_session
### `substrate/organism/runtime_session.py`
- Lines: 263. Doc: Runtime session model — governed execution surface for workcell runtimes.
- Classes: RuntimeStatus, RuntimeType, RuntimeEventType, RuntimeEvent, RuntimeSession
- Functions: _ensure_dir, persist_session, persist_event, load_sessions, load_events, get_session
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/runtime_state_registry.py`
- Lines: 588. Doc: Runtime State Registry — live environment awareness for the workstation.
- Classes: WorktreeInfo, GitRepoInfo, ProcessInfo, ContainerInfo, ExecutionInfo, RuntimeSnapshot, RuntimeStateStore, RuntimeStateRefresher
- Functions: _safe_run, collect_worktrees, _parse_worktree, collect_git_info, collect_processes, _is_interesting_process, collect_containers, collect_executions, get_runtime_state_registry, reset_runtime_state_registry
- Imports: __future__, dataclasses, logging, os, subprocess, threading, time, typing
### `substrate/organism/runtime_supervisor.py`
- Lines: 430. Doc: RuntimeSupervisor — persistent runtime lifecycle management.
- Classes: SupervisedHealth, CrashRecord, SupervisedRuntime, RuntimeSupervisor
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, pathlib, substrate.organism.runtime_graph, time
### `substrate/organism/sandbox_orchestrator.py`
- Lines: 217. Doc: Sandbox Orchestrator — ties approval gate to PR factory execution.
- Classes: SandboxExecutionResult, SandboxOrchestrator
- Functions: _supply_to_improvement
- Imports: __future__, dataclasses, json, logging, os, substrate.organism.approval_gate, substrate.organism.autonomous_improvement_lane, substrate.organism.autonomous_pr_factory
### `substrate/organism/scenario_intelligence_engine.py`
- Lines: 660. Doc: Scenario Intelligence Engine — Campaign 13.1
- Classes: ScenarioType, FutureScenario, ScenarioIntelligenceEngine
- Functions: _get_attr
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/self_build_queue.py`
- Lines: 708. Doc: Self-Build Engineering Queue — canonical work item model and queue engine.
- Classes: WorkItemStatus, WorkItemSourceType, SelfBuildWorkItem, SelfBuildQueueEngine
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, tempfile, time
### `substrate/organism/self_use/__init__.py`
- Lines: 72. Doc: Self-use certification — C27 Daily Driver Readiness.
- Classes: -
- Functions: -
- Imports: __future__, substrate.organism.self_use.certification_report, substrate.organism.self_use.gap_ledger, substrate.organism.self_use.meta_ide_audit, substrate.organism.self_use.projection_delta, substrate.organism.self_use.task_catalog, substrate.organism.self_use.task_taxonomy, substrate.organism.strategic_gap_engine
### `substrate/organism/self_use/certification_report.py`
- Lines: 278. Doc: Certification report — 4-gate pass/fail with coherence override.
- Classes: CertificationGate, CoherenceMetrics, GateResult, CertificationReport, ReportBuilder
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, typing
### `substrate/organism/self_use/gap_ledger.py`
- Lines: 187. Doc: Gap ledger — structured log of every friction point, missing capability, and failure.
- Classes: GapType, GapEntry, GapLedger
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, substrate.organism.strategic_gap_engine
### `substrate/organism/self_use/meta_ide_audit.py`
- Lines: 223. Doc: Meta IDE functional audit — manual operator testing of every subsystem.
- Classes: FunctionalStatus, SubsystemOperation, SubsystemAudit, AuditMatrix
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, typing
### `substrate/organism/self_use/projection_delta.py`
- Lines: 231. Doc: Projection delta engine — desired vs implemented vs certified.
- Classes: CapabilityState, ProjectionCapability, ProjectionDelta, DeltaReport, ProjectionDeltaEngine
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, typing
### `substrate/organism/self_use/task_catalog.py`
- Lines: 203. Doc: Task catalog — load and manage C27 self-use certification tasks.
- Classes: TaskStatus, SelfUseTask, TaskResult, TaskCatalog
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, substrate.organism.self_use.task_taxonomy
### `substrate/organism/self_use/task_taxonomy.py`
- Lines: 53. Doc: Task taxonomy — domain classification for self-use certification.
- Classes: StreamType, TaskDomain, CoherenceDomain
- Functions: -
- Imports: __future__, enum
### `substrate/organism/service_dependency_graph.py`
- Lines: 167. Doc: Service Dependency Graph — canonical service dependency models.
- Classes: DependencyStrength, ServiceCriticality, ServiceHealthImpact, ServiceDependency, ServiceNode, FailureImpact, ServiceDependencyTopology
- Functions: -
- Imports: __future__, dataclasses, enum, time, typing, uuid
### `substrate/organism/service_dependency_registry.py`
- Lines: 140. Doc: Service Dependency Registry — canonical registry of service dependencies.
- Classes: ServiceDependencyRegistry
- Functions: _find_registry_path, _load_seed_data
- Imports: __future__, json, logging, os, substrate.organism.service_dependency_graph, typing
### `substrate/organism/service_failure_engine.py`
- Lines: 169. Doc: Service Failure Engine — computes failure impact across service graph.
- Classes: ServiceFailureEngine
- Functions: -
- Imports: __future__, collections, logging, substrate.organism.service_dependency_graph, typing
### `substrate/organism/session_runtime.py`
- Lines: 1115. Doc: Session Runtime — canonical session architecture for UMH.
- Classes: SessionType, SessionStatus, SessionAuthority, SessionEventType, HandoffStatus, Session, SessionEvent, SessionHandoff
- Functions: _repo_root, _session_data_dir, _ensure_dirs, get_session_runtime, reset_session_runtime
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/shell_runtime_adapter.py`
- Lines: 446. Doc: Shell runtime adapter — safe subprocess execution surface.
- Classes: ShellRuntimeAdapter
- Functions: is_command_blocked, _redact_secrets, _sandbox_env, _is_inside_worktree_base, is_path_allowed
- Imports: __future__, logging, os, re, signal, subprocess, substrate.execution.cpu_gate, substrate.organism.runtime_adapter
### `substrate/organism/source_registry.py`
- Lines: 232. Doc: Source Registry — tracks all context sources available to UMH.
- Classes: SourceType, SyncPolicy, Canonicality, SourceStatus, ContextSource, SourceRegistry
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/source_truth_linker.py`
- Lines: 296. Doc: Source Truth Linker — cross-domain edge builder for the Reality Graph.
- Classes: SourceTruthLinker
- Functions: -
- Imports: __future__, collections, logging, substrate.organism.reality_graph, time, typing
### `substrate/organism/source_truth_runtime.py`
- Lines: 878. Doc: Source Truth Runtime — full organizational lineage (Campaign 22.6 CORE).
- Classes: LineageNodeType, LineageTerminalState, LineageNode, LineageChain, LineageSummary, SourceTruthRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/spine_guard.py`
- Lines: 241. Doc: SpineGuard — enforcement layer for the single-spine mutation doctrine.
- Classes: GuardMode, Violation, SpineGuard
- Functions: -
- Imports: __future__, dataclasses, enum, logging, threading, time, typing
### `substrate/organism/state_authority_graph.py`
- Lines: 132. Doc: State Authority Graph — canonical state domain authority models.
- Classes: StateDomain, StateAuthorityLevel, StateCoherenceStatus, StateAuthority, StateDomainStatus, OrganismStateGraph
- Functions: -
- Imports: __future__, dataclasses, enum, time, typing, uuid
### `substrate/organism/state_coherence_engine.py`
- Lines: 175. Doc: State Coherence Engine — detects state authority coherence across nodes.
- Classes: StateCoherenceEngine
- Functions: -
- Imports: __future__, logging, substrate.organism.state_authority_graph, substrate.organism.state_registry, time, typing
### `substrate/organism/state_registry.py`
- Lines: 109. Doc: State Registry — canonical registry of state domain authorities.
- Classes: StateRegistry
- Functions: _find_registry_path, _load_seed_authorities
- Imports: __future__, json, logging, os, substrate.organism.state_authority_graph, typing
### `substrate/organism/store.py`
- Lines: 124. Doc: Organism store — JSONL persistence for deliverables, messages, agent state.
- Classes: OrganismStore
- Functions: -
- Imports: __future__, datetime, json, pathlib, substrate.organism.protocols, typing
### `substrate/organism/strategic_context_runtime.py`
- Lines: 514. Doc: Strategic Context Runtime — unified executive synthesis facade.
- Classes: StrategicHealth, StrategicContext, StrategicContextRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/strategic_gap_engine.py`
- Lines: 978. Doc: Strategic Gap Engine — compares current reality to target goals, produces gaps,
- Classes: GoalStatus, GoalType, GapSeverity, RecommendationStatus, SuccessCriterion, Goal, Gap, Recommendation
- Functions: _repo_root, _data_dir, _ensure_dirs, score_gap
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/strategic_memory_engine.py`
- Lines: 432. Doc: Strategic Memory Engine — institutional memory with timeline and replay.
- Classes: MemorySnapshot, StrategicMemory, StrategicMemoryEngine
- Functions: -
- Imports: __future__, dataclasses, json, logging, os, time, typing, uuid
### `substrate/organism/strategic_planning_engine.py`
- Lines: 347. Doc: Strategic Planning Engine — generate plans linking current reality to goals.
- Classes: PlanningStatus, StrategicMilestone, StrategicPlan, StrategicPlanningEngine
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/strategic_tick_loop.py`
- Lines: 871. Doc: Strategic Tick Loop — continuous governed awareness engine.
- Classes: TickFrequency, RecommendationLifecycle, DriftSeverity, RealityDelta, ChangeDetector, CandidateWorkItem, CandidateWorkQueue, DriftWarning
- Functions: _repo_root, _tick_data_dir, _ensure_tick_dirs, _snapshot_hash, apply_profile_weighting, get_tick_loop, reset_tick_loop
- Imports: __future__, dataclasses, enum, hashlib, json, logging, os, time
### `substrate/organism/sync_policy.py`
- Lines: 174. Doc: External Sync Policy — governs how UMH relates to external tools.
- Classes: CanonicalDirection, ReadPolicy, WritePolicy, ConflictPolicy, ExternalSyncStatus, ExternalSyncPolicy, SyncPolicyStore
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/system_identity.py`
- Lines: 139. Doc: Canonical UMH identity — single source of truth.
- Classes: -
- Functions: _get_ai_name, _ai_identity_pattern, get_system_identity_context, is_identity_question, get_identity_answer, get_prompt_grounding
- Imports: __future__, os, re
### `substrate/organism/template_governance.py`
- Lines: 338. Doc: Template Governance — 9-dimension scoring engine for template cadence eligibility.
- Classes: GovernanceDecision, DimensionScore, TemplateGovernanceScore, TemplateGovernance
- Functions: -
- Imports: __future__, dataclasses, enum, logging, re, substrate.organism.template_registry, typing
### `substrate/organism/template_registry.py`
- Lines: 663. Doc: Template Registry — reusable executable structures from governed execution.
- Classes: TemplateStatus, TemplateType, AgentType, CapabilityName, TemplateEvidence, TemplateStep, TemplateValidation, TemplateRollback
- Functions: _infer_template_type, _infer_trigger_conditions
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/template_seeder.py`
- Lines: 1172. Doc: Template Seeder — seeds evidence-backed execution templates to the runtime store.
- Classes: SeedResult, TemplateSeeder
- Functions: main
- Imports: __future__, dataclasses, json, logging, os, substrate.organism.template_registry, time, typing
### `substrate/organism/tests/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/organism/tests/test_advisor.py`
- Lines: 47. Doc: Tests for advisor — interpret, decompose, delegate, synthesize.
- Classes: -
- Functions: store, advisor, test_advisor_has_agents, test_advisor_delegates_to_researcher, test_advisor_delegates_to_builder, test_advisor_returns_status
- Imports: pytest, substrate.organism.advisor, substrate.organism.store
### `substrate/organism/tests/test_advisor_coordinator.py`
- Lines: 159. Doc: Tests for advisor → coordinator integration (Phase 2A).
- Classes: FakeAdapter, TestAdvisorCoordinatorIntegration
- Functions: _make_graph
- Imports: substrate.organism.advisor, substrate.organism.coordinator, substrate.organism.runtime_graph, sys, tempfile, typing
### `substrate/organism/tests/test_agent_runtime.py`
- Lines: 79. Doc: tests for agent base runtime — critique loop, deliverable production.
- Classes: -
- Functions: store, runtime, test_runtime_starts_idle, test_runtime_processes_task, test_deliverable_persisted_to_store, test_status_transitions
- Imports: pytest, substrate.organism.agent_runtime, substrate.organism.protocols, substrate.organism.store
### `substrate/organism/tests/test_allocation_loop.py`
- Lines: 116. Doc: Tests for the governed runtime allocation loop.
- Classes: -
- Functions: _make_graph, _make_loop, test_allocation_cycle, test_detect_degraded_runtime, test_throttle_under_governor_kill, test_emits_allocation_events, test_cost_spike_detection, test_to_dict
- Imports: __future__, substrate.organism.allocation_loop, substrate.organism.event_spine, substrate.organism.execution_economy, substrate.organism.recursion_governance, substrate.organism.runtime_graph, substrate.organism.runtime_supervisor, sys
### `substrate/organism/tests/test_approval_store.py`
- Lines: 69. Doc: tests for approval store — JSONL persistence for governance-blocked signals.
- Classes: -
- Functions: store, test_create_approval, test_list_approvals, test_list_approvals_filter_status, test_approve_item, test_deny_item, test_decide_nonexistent, test_pending_count
- Imports: pytest, substrate.organism.approval_store
### `substrate/organism/tests/test_assisted_executor.py`
- Lines: 129. Doc: Tests for the AssistedExecutor — Phase 5.9.
- Classes: -
- Functions: _make_executor, _make_assisted_executor, test_blocked_in_observe_mode, test_can_execute_in_assisted_mode, test_audit_trail, test_critical_container_protection, test_to_dict, test_event_emission
- Imports: __future__, substrate.organism.assisted_executor, substrate.organism.event_spine, substrate.organism.execution_modes, substrate.organism.leverage_metrics, substrate.organism.maintenance_loop, sys
### `substrate/organism/tests/test_async_coordinator.py`
- Lines: 122. Doc: Tests for async coordinator execution.
- Classes: -
- Functions: _make_coordinator, test_submit_objective, test_advance_processes_submitted, test_cancel_objective, test_progress_tracking, test_emits_lifecycle_events, test_list_active, test_completed_not_in_active, test_dag_state
- Imports: __future__, substrate.organism.async_coordinator, substrate.organism.coordinator, substrate.organism.event_spine, substrate.organism.runtime_graph, sys
### `substrate/organism/tests/test_automation_pipeline.py`
- Lines: 133. Doc: Tests for the AutomationPipeline — Phase 5.9.
- Classes: -
- Functions: _make_pipeline_with_data, test_scan_finds_candidates, test_no_duplicates_on_rescan, test_approve_proposal, test_deny_proposal, test_cannot_approve_nonexistent, test_risk_classification, test_leverage_scoring, test_pipeline_tick, test_list_proposals_by_status, test_event_emission
- Imports: __future__, substrate.organism.automation_pipeline, substrate.organism.event_spine, substrate.organism.operator_compression, sys
### `substrate/organism/tests/test_autonomous_tick.py`
- Lines: 183. Doc: Tests for the autonomous tick engine.
- Classes: -
- Functions: _make_tick, test_tick_config_defaults, test_tick_register_stage, test_tick_single_cycle, test_tick_stage_failure_isolation, test_tick_emits_events, test_tick_governance_kill, test_tick_governance_pause_resume, test_tick_metrics, test_tick_adaptive_cadence_speeds_up, test_tick_adaptive_cadence_slows_down, test_tick_run_loop_stops_on_kill
- Imports: __future__, substrate.organism.autonomous_tick, substrate.organism.event_spine, sys, threading, time
### `substrate/organism/tests/test_bottleneck_engine.py`
- Lines: 132. Doc: Tests for BottleneckEngine.
- Classes: -
- Functions: test_no_bottlenecks_on_clean_state, test_high_failure_rate, test_retry_storm, test_repetitive_intervention, test_high_latency, test_slow_runtime, test_queue_buildup, test_stalled_objective, test_recurrence_escalation, test_multiple_detections, test_history, test_to_dict
- Imports: __future__, os, substrate.organism.bottleneck_engine, sys
### `substrate/organism/tests/test_composition_engine.py`
- Lines: 199. Doc: Tests for composition engine.
- Classes: TestCompositionIntent, TestCompositionStep, TestCompositionPlan, TestIntentClassification, TestCapabilityMatching, TestMissingDependencyDetection, TestRiskClassification, TestGovernanceRequirement
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.composition_engine, sys, tempfile
### `substrate/organism/tests/test_contradiction_engine.py`
- Lines: 191. Doc: Tests for contradiction engine.
- Classes: TestClaim, TestObservation, TestContradiction, TestContradictionReport, TestConfidenceScoring, TestContradictionEngine, TestPersistence
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.contradiction_engine, sys, tempfile
### `substrate/organism/tests/test_coordinator.py`
- Lines: 242. Doc: Tests for OrganismCoordinator — task decomposition, assignment, execution.
- Classes: FakeAdapter, TestWorkUnit, TestDecomposition, TestRuntimeAssignment, TestExecution, TestStatus
- Functions: _make_coordinator
- Imports: pytest, substrate.organism.coordinator, substrate.organism.runtime_graph, sys, tempfile, typing
### `substrate/organism/tests/test_daemon_approvals.py`
- Lines: 68. Doc: tests for daemon approval creation on governance rejection.
- Classes: -
- Functions: test_map_risk_level_deny, test_map_risk_level_escalate, test_map_risk_level_defer, test_map_risk_level_unknown, test_daemon_creates_approval_on_governance_deny, test_daemon_ignores_approved_governance_events, test_daemon_ignores_non_governance_events
- Imports: pytest, substrate.organism.daemon
### `substrate/organism/tests/test_dependency_graph.py`
- Lines: 190. Doc: Tests for organism dependency graph.
- Classes: TestDependencyNode, TestDependencyEdge, TestDependencyGraph, TestBuildDependencyGraph, TestPersistence
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.dependency_graph, sys, tempfile
### `substrate/organism/tests/test_development_session_bridge.py`
- Lines: 242. Doc: Tests for DevelopmentSessionBridge — governed coding agent integration.
- Classes: TestSessionLifecycle, TestMutationRecording, TestDecisionRecording, TestCoherenceObservations, TestGateResults, TestEventSpineIntegration, TestHarnessAgnostic, TestToDict
- Functions: tmp_umh
- Imports: __future__, json, os, pytest, substrate.organism.development_session_bridge, substrate.organism.event_spine, sys, tempfile
### `substrate/organism/tests/test_e2e.py`
- Lines: 64. Doc: End-to-end test — the vertical slice acceptance criterion.
- Classes: -
- Functions: store, advisor, test_full_vertical_slice, test_multiple_signals_accumulate, test_organism_status_reflects_work
- Imports: pytest, substrate.organism.advisor, substrate.organism.store
### `substrate/organism/tests/test_environment_graph.py`
- Lines: 157. Doc: Tests for EnvironmentGraph — operational topology.
- Classes: -
- Functions: _make_graph, test_capture_creates_snapshot, test_capture_includes_workcells, test_diff_detects_added_nodes, test_diff_detects_removed_nodes, test_diff_detects_status_changes, test_no_diff_when_unchanged, test_to_dict_structure, test_latest_returns_none_when_empty, test_recent_snapshots
- Imports: __future__, os, substrate.organism.environment_graph, substrate.organism.runtime_graph, sys
### `substrate/organism/tests/test_environment_reconciler.py`
- Lines: 164. Doc: Tests for EnvironmentReconciler — drift correction.
- Classes: -
- Functions: _simple_graph, test_reconcile_returns_report, test_reconcile_tick_returns_bool, test_status_change_detection, test_stale_dynamic_runtime_removed, test_to_dict, test_emits_events_on_changes
- Imports: __future__, os, substrate.organism.environment_reconciler, substrate.organism.event_spine, substrate.organism.runtime_graph, sys
### `substrate/organism/tests/test_event_spine.py`
- Lines: 236. Doc: Tests for the unified organism event spine.
- Classes: -
- Functions: test_event_creation, test_event_priority_default, test_event_priority_critical, test_spine_emit_and_recent, test_spine_subscribe_and_receive, test_spine_subscribe_with_domain_filter, test_spine_unsubscribe, test_spine_replay, test_spine_replay_since, test_spine_snapshot, test_spine_max_events_bounded, test_spine_subscriber_error_isolation
- Imports: __future__, substrate.organism.event_spine, sys, time
### `substrate/organism/tests/test_execution_modes.py`
- Lines: 115. Doc: Tests for ExecutionModeManager.
- Classes: -
- Functions: test_initial_mode, test_custom_initial_mode, test_can_execute, test_promote, test_promote_no_downgrade, test_demote, test_propose_action_observe, test_propose_action_autonomous, test_auto_demotion_on_failures, test_auto_promotion_on_success, test_reliability, test_transition_history
- Imports: __future__, os, substrate.organism.execution_modes, sys
### `substrate/organism/tests/test_leverage_assimilation.py`
- Lines: 280. Doc: Tests for leverage_assimilation — external framework ingestion and scoring.
- Classes: TestLeverageScore, TestExtractedPrimitive, TestAssimilationArtifact, TestAssimilatorIngest, TestAssimilatorClassify, TestAssimilatorExtract, TestAssimilatorRedundancy, TestAssimilatorScoring
- Functions: -
- Imports: json, pathlib, pytest, substrate.organism.leverage_assimilation, tempfile
### `substrate/organism/tests/test_leverage_metrics.py`
- Lines: 134. Doc: Tests for LeverageMetrics engine.
- Classes: -
- Functions: test_empty_metrics, test_record_task_updates_totals, test_intervention_counted, test_time_compression, test_failure_recovery_speed, test_bottleneck_inputs, test_leverage_tick_returns_summary, test_cost_tracking, test_operator_seconds_saved
- Imports: __future__, os, substrate.organism.leverage_metrics, sys, time
### `substrate/organism/tests/test_leverage_rebalance.py`
- Lines: 53. Doc: Tests for continuous leverage rebalancing.
- Classes: -
- Functions: test_rebalance_cycle, test_rebalance_emits_events, test_detect_degraded_primitives, test_works_without_spine
- Imports: __future__, substrate.organism.event_spine, substrate.organism.leverage_assimilation, sys
### `substrate/organism/tests/test_maintenance_loop.py`
- Lines: 91. Doc: Tests for the MaintenanceLoop — Phase 5.9.
- Classes: -
- Functions: _make_loop, test_maintenance_tick, test_cycle_count_increments, test_recent_reports, test_to_dict, test_event_emission
- Imports: __future__, substrate.organism.event_spine, substrate.organism.execution_modes, substrate.organism.leverage_metrics, substrate.organism.maintenance_loop, substrate.organism.operator_compression, substrate.organism.workload_runner, sys
### `substrate/organism/tests/test_memory_promotion.py`
- Lines: 303. Doc: Tests for memory promotion pipeline.
- Classes: TestMemoryEvidence, TestMemoryCandidate, TestCanonicalMemoryEntry, TestMemoryPromotionDecision, TestPipelineSubmission, TestContradictionBlocking, TestEvidenceValidation, TestPromotionApproval
- Functions: pipeline, _good_evidence
- Imports: __future__, json, os, pytest, substrate.organism.memory_promotion, sys, tempfile
### `substrate/organism/tests/test_mission.py`
- Lines: 243. Doc: Tests for Mission — user conversation to organism execution bridge.
- Classes: FakeAdapter, TestMissionFromUserIntent, TestMission, TestMissionResult, TestExecuteMission, TestSynthesizeMissionResult
- Functions: _make_coordinator
- Imports: substrate.organism.coordinator, substrate.organism.mission, substrate.organism.runtime_graph, sys, tempfile, typing
### `substrate/organism/tests/test_objective_physics.py`
- Lines: 139. Doc: Tests for ObjectivePhysics engine.
- Classes: -
- Functions: test_register_objective, test_dependency_linking, test_blocking_nodes, test_update_state, test_execution_gravity, test_critical_paths, test_leverage_propagation, test_what_matters_most, test_what_blocks_everything, test_physics_tick, test_to_dict, test_cycle_prevention
- Imports: __future__, os, substrate.organism.objective_physics, sys
### `substrate/organism/tests/test_objective_queue.py`
- Lines: 169. Doc: Tests for the continuous objective queue.
- Classes: -
- Functions: _make_queue, test_enqueue_and_peek, test_priority_ordering, test_dequeue, test_complete, test_fail_and_retry, test_fail_exhausts_retries, test_dependency_ordering, test_blocked_item_not_dequeued, test_emits_events, test_cancel, test_queue_depth
- Imports: __future__, substrate.organism.event_spine, substrate.organism.objective_queue, sys
### `substrate/organism/tests/test_operational_intelligence.py`
- Lines: 331. Doc: Tests for Phase 7.0 Operational Intelligence engines.
- Classes: TestBottleneckEngine, TestLeverageEngine, TestNextActionEngine, TestReadinessModel, TestIntegration
- Functions: -
- Imports: __future__, substrate.organism.bottleneck_engine, substrate.organism.leverage_engine, substrate.organism.next_action_engine, substrate.organism.readiness_model, sys, time
### `substrate/organism/tests/test_operator_compression.py`
- Lines: 107. Doc: Tests for OperatorCompression engine.
- Classes: -
- Functions: test_empty_compression, test_autonomous_records, test_intervention_reduces_ratio, test_automation_candidate_detection, test_different_patterns_tracked, test_compression_tick, test_to_dict
- Imports: __future__, os, substrate.organism.operator_compression, sys
### `substrate/organism/tests/test_orchestration_integration.py`
- Lines: 481. Doc: Integration tests for Phase 2 organism orchestration.
- Classes: FakeAdapter, TestCapabilityInference, TestAdvisorGraphIntegration, TestAdvisorSupervisorIntegration, TestAdvisorHomeostasisIntegration, TestAutonomousTick, TestSignalQueue, TestResourceTopology
- Functions: _make_graph, _make_full_daemon
- Imports: __future__, pytest, substrate.organism.advisor, substrate.organism.coordinator, substrate.organism.daemon, substrate.organism.homeostasis, substrate.organism.observability, substrate.organism.runtime_graph
### `substrate/organism/tests/test_orchestration_loop.py`
- Lines: 202. Doc: Tests for orchestration_loop — PersistentLoop stages wired to organism daemon.
- Classes: FakeAdapter, TestStageRegistration, TestOrganismTickStage, TestHealthCheckStage, TestHomeostasisStage, TestStatePersistStage, TestLoopCreation
- Functions: _make_graph, _make_report
- Imports: pytest, substrate.execution.loop.persistent_loop, substrate.organism.daemon, substrate.organism.homeostasis, substrate.organism.orchestration_loop, substrate.organism.runtime_graph, substrate.organism.runtime_supervisor, tempfile
### `substrate/organism/tests/test_organism_events.py`
- Lines: 60. Doc: tests for organism ViewFrame event broadcasting.
- Classes: FakeViewSocket
- Functions: store, view_socket, advisor, test_signal_emits_events, test_signal_received_has_routing, test_deliverable_event_has_critique, test_no_events_without_view_socket
- Imports: pytest, substrate.organism.advisor, substrate.organism.store, substrate.sockets.envelopes
### `substrate/organism/tests/test_outcome_learning.py`
- Lines: 212. Doc: Tests for outcome learning loop.
- Classes: TestOutcomeRecord, TestLearningSignal, TestOutcomeEvaluation, TestRecommendationAdjustment, TestOutcomeLearningLoop
- Functions: temp_store
- Imports: __future__, json, os, pytest, substrate.organism.outcome_learning, sys, tempfile
### `substrate/organism/tests/test_phase10_template_supply.py`
- Lines: 830. Doc: Phase 10.0 — Template Library, Candidate Supply, and Cockpit Route Extraction tests.
- Classes: TestTemplateSeeder, TestTemplateGovernance, TestCandidateSupplyEngine, TestCadenceIntegration, TestRouteExtraction
- Functions: tmp_store, seeder, governance, _make_strong_template
- Imports: __future__, json, os, pytest, substrate.organism.autonomous_cadence, substrate.organism.candidate_supply_engine, substrate.organism.template_governance, substrate.organism.template_registry
### `substrate/organism/tests/test_phase11_1_universal_work.py`
- Lines: 855. Doc: Phase 11.1 — Universal Work Queue + Work Packet Engine tests.
- Classes: TestWorkPacket, TestPacketLifecycleStatus, TestWorkPacketPersistence, TestWorkcell, TestAdvisorBranch, TestReconvergenceResult, TestWorkcellPersistence, TestRoleContract
- Functions: tmp_dir, packets_path, workcells_path, roles_path, knowledge_path, engine, queue
- Imports: __future__, json, os, pytest, substrate.organism.delegation_topology, substrate.organism.intent_classifier, substrate.organism.knowledge_model_registry, substrate.organism.role_contracts
### `substrate/organism/tests/test_phase11_self_build_queue.py`
- Lines: 662. Doc: Phase 11.0 — Self-Build Engineering Queue tests.
- Classes: TestSelfBuildWorkItem, TestWorkItemStatus, TestWorkItemSourceType, TestQueueEngineCreation, TestCandidateIngestion, TestAuditFindingIngestion, TestRoadmapRequirementIngestion, TestDuplicateSuppression
- Functions: tmp_store, tmp_roadmap, engine, roadmap, _make_candidate
- Imports: __future__, json, os, pytest, substrate.organism.roadmap_engine, substrate.organism.self_build_queue, sys, tempfile
### `substrate/organism/tests/test_phase12_0_propagation_graph.py`
- Lines: 990. Doc: Phase 12.0 — Universal Propagation Graph / Correspondence Layer tests.
- Classes: TestPropagationNodeSerialization, TestPropagationEdgeSerialization, TestPropagationGraphBuild, TestCycleDetection, TestGraphPersistence, TestChangeEventSerialization, TestPropagationPlanSerialization, TestPropagationAction
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.change_event, substrate.organism.impact_analyzer, substrate.organism.propagation_executor, substrate.organism.propagation_graph
### `substrate/organism/tests/test_phase13_0_operator_experience.py`
- Lines: 842. Doc: Phase 13.0 — Operator Experience Kernel tests.
- Classes: TestOperatorIntentSerialization, TestOperatorTurnSerialization, TestOperatorSessionSerialization, TestOperatorResponseSerialization, TestOptionSerialization, TestSessionPersistence, TestResponsePersistence, TestTurnIntentPersistence
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.operator_response, substrate.organism.operator_session, substrate.organism.orchestrator_kernel, tempfile
### `substrate/organism/tests/test_phase13_4m.py`
- Lines: 615. Doc: Phase 13.4M tests — multi-runtime operator acceptance correction.
- Classes: TestDeviceRoleRegistry, TestRuntimeFleetModel, TestWorkloadPlacementPolicy, TestOperatorReadinessGate, TestOperatorAcceptanceMode, TestSafetyInvariants, TestAPIBridgeHandlers, TestReadinessGateUsesFleet
- Functions: -
- Imports: __future__, json, os, pytest, sys, tempfile, time
### `substrate/organism/tests/test_phase14_1_source_inspection.py`
- Lines: 699. Doc: Tests for Phase 14.1 — Permissioned Source Inspection Execution.
- Classes: TestPermissionStateClassification, TestLocalOptOSInspection, TestSaasInspection, TestProjectionsDirectoryInspection, TestGoogleDocsBlockerInspection, TestGitHubInspection, TestWindowsDevInspection, TestCrossSourceIndex
- Functions: _find_repo_root
- Imports: __future__, json, os, pytest, substrate.organism.projection_readiness_gate, substrate.organism.projection_reconciliation_engine, substrate.organism.projection_source_registry, tempfile
### `substrate/organism/tests/test_phase3.py`
- Lines: 750. Doc: Phase 3 tests — Governed Recursive Execution Economy.
- Classes: TestExecutionEconomy, TestRecursionGovernance, TestAdvisorHierarchy, TestCockpitObservability, TestExternalLeverageMapSchema, TestStructuralIntegrity
- Functions: -
- Imports: __future__, os, pytest, sys, time
### `substrate/organism/tests/test_phase58_integration.py`
- Lines: 210. Doc: Phase 5.8 integration tests — full Operational Leverage Engine.
- Classes: -
- Functions: _make_daemon, test_daemon_has_new_engines, test_daemon_tick_includes_new_stages, test_daemon_tick_runs_all_stages, test_daemon_status_includes_new_engines, test_leverage_metrics_through_daemon, test_bottleneck_detection_through_daemon, test_objective_physics_through_daemon, test_operator_compression_through_daemon, test_execution_mode_through_daemon, test_workload_probes_through_daemon, test_event_spine_receives_leverage_events
- Imports: __future__, os, substrate.organism.daemon, substrate.organism.event_spine, substrate.organism.leverage_metrics, substrate.organism.objective_physics, substrate.organism.operator_compression, sys
### `substrate/organism/tests/test_phase59_integration.py`
- Lines: 117. Doc: Integration tests for Phase 5.9 — end-to-end workload execution.
- Classes: -
- Functions: test_daemon_has_phase59_subsystems, test_tick_includes_maintenance_and_automation, test_daemon_status_includes_phase59, test_full_tick_cycle, test_workload_runner_through_daemon, test_run_all_observe_through_daemon, test_assisted_blocked_in_observe, test_assisted_works_after_promotion, test_leverage_records_from_workloads, test_events_emitted_during_workloads
- Imports: __future__, substrate.organism.daemon, substrate.organism.execution_modes, substrate.organism.workload_runner, sys
### `substrate/organism/tests/test_phase61_governed_spine.py`
- Lines: 687. Doc: Tests for Phase 6.1 — GovernedExecutionSpine, ActionEnvelope,
- Classes: TestActionEnvelope, TestMutationRegistry, TestExecutionJournal, TestGovernedSpine, TestSpineGuard, TestIntegration
- Functions: _make_spine, _success_envelope, _failing_envelope, _exception_envelope
- Imports: __future__, substrate.organism.action_envelope, substrate.organism.event_spine, substrate.organism.execution_journal, substrate.organism.execution_modes, substrate.organism.governed_spine, substrate.organism.leverage_metrics, substrate.organism.mutation_registry
### `substrate/organism/tests/test_phase62_spine_enforcement.py`
- Lines: 831. Doc: Tests for Phase 6.2 — Execution Spine Enforcement + SpineGuard Ladder.
- Classes: TestSpineGuardEnforcementLadder, TestProductionEnforcement, TestMutationRegistryContracts, TestReliabilityContracts, TestDaemonIntegration, TestCockpitSpineRouter, TestRiskClassification
- Functions: _make_spine, _low_risk_envelope, _medium_risk_envelope, _high_risk_envelope, _critical_risk_envelope
- Imports: __future__, substrate.organism.action_envelope, substrate.organism.event_spine, substrate.organism.execution_journal, substrate.organism.execution_modes, substrate.organism.governed_spine, substrate.organism.leverage_metrics, substrate.organism.mutation_registry
### `substrate/organism/tests/test_phase63_autonomous_gate.py`
- Lines: 595. Doc: Phase 6.3 — Autonomous Execution Spine Gate tests.
- Classes: TestGatewayPolicyObserve, TestGatewayPolicyRecommend, TestGatewayPolicyAssisted, TestGatewayPolicyAutonomous, TestDirectMutationBlocked, TestWorkloadRunnerGateway, TestAssistedExecutorGateway, TestMaintenanceLoopGateway
- Functions: _make_spine_stack, _make_gateway, _simple_envelope
- Imports: __future__, pytest, substrate.organism.action_envelope, substrate.organism.autonomous_action_gateway, substrate.organism.daemon, substrate.organism.event_spine, substrate.organism.execution_journal, substrate.organism.execution_modes
### `substrate/organism/tests/test_phase92_self_improvement.py`
- Lines: 790. Doc: Phase 9.2 — Governed Self-Improvement Trial tests.
- Classes: TestTrialCandidateSelection, TestCustomStepComposition, TestExecutionGraph, TestGovernanceDryRun, TestGovernedExecution, TestOutcomeCapture, TestMemoryCandidateGeneration, TestAdapterSpineGuardIntegration
- Functions: world_model, dep_graph, contradiction_report, composition_engine, tmpdir, governed_stack
- Imports: __future__, json, os, pytest, substrate.organism.action_envelope, substrate.organism.autonomous_action_gateway, substrate.organism.composition_engine, substrate.organism.contradiction_engine
### `substrate/organism/tests/test_phase93_reliability_campaign.py`
- Lines: 779. Doc: Phase 9.3 — Self-Improvement Reliability Campaign tests.
- Classes: TestCandidateRanking, TestSafetyGate, TestBlockedTrialHandling, TestMultiTrialExecution, TestMetricsAggregation, TestReadinessDelta, TestContradictionDelta, TestMemoryCandidateGeneration
- Functions: tmpdir, governed_stack, sample_candidates
- Imports: __future__, json, os, pytest, substrate.organism.autonomous_action_gateway, substrate.organism.composition_engine, substrate.organism.contradiction_engine, substrate.organism.dependency_graph
### `substrate/organism/tests/test_phase94_coherence_propagation.py`
- Lines: 796. Doc: Phase 9.4 tests — Template Registry, Agent Capability Model, Coherence Propagation.
- Classes: TestTemplateRegistry, TestAgentCapabilityModel, TestCoherencePropagation, TestIntegration, TestPrimitiveRelationships
- Functions: -
- Imports: __future__, json, os, pytest, sys, tempfile, time
### `substrate/organism/tests/test_phase95_spine_native_propagation.py`
- Lines: 1474. Doc: Phase 9.5 tests — Spine-Native Propagation + Template-Guided Improvement Campaign.
- Classes: TestSpineNativeOutcomeCommitted, TestSpineNativeOutcomeFailed, TestPropagationEngineAutoInvocation, TestIdempotencyProtection, TestFailureIsolation, TestSpinePropagationIntegration, TestOutcomeContracts, TestPropagationEngineInternals
- Functions: _make_event_spine, _make_journal, _make_mode_manager, _make_mutation_registry, _make_propagation_engine, _make_spine, _make_envelope, _sample_outcome
- Imports: __future__, json, os, pytest, substrate.organism.event_spine, sys, tempfile, time
### `substrate/organism/tests/test_phase9_integration.py`
- Lines: 478. Doc: Tests for Phase 9.0 — World Model → Execution Integration.
- Classes: TestWorldModelExtraction, TestDependencyGraphConstruction, TestContradictionDetection, TestCompositionEngine, TestOutcomeCapture, TestMemoryPromotion, TestFullLoop
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.composition_engine, substrate.organism.contradiction_engine, substrate.organism.dependency_graph, substrate.organism.memory_promotion
### `substrate/organism/tests/test_plan_execution_adapter.py`
- Lines: 770. Doc: Tests for plan_execution_adapter — Phase 9.1 Composition→Execution bridge.
- Classes: FakeSpine, TestPlanConversion, TestDependencyPreservation, TestGovernancePreservation, TestApprovalRouting, TestExecutionGraphTraversal, TestRollbackGeneration, TestOutcomeGeneration
- Functions: _make_plan
- Imports: __future__, os, pytest, substrate.organism.action_envelope, substrate.organism.composition_engine, substrate.organism.memory_promotion, substrate.organism.outcome_learning, substrate.organism.plan_execution_adapter
### `substrate/organism/tests/test_projection_port.py`
- Lines: 118. Doc: Tests for projection-agnostic organism state port.
- Classes: MockProjection
- Functions: test_register_projection, test_unregister_projection, test_broadcast_to_all, test_filtered_broadcast, test_subscriber_error_isolation, test_spine_bridge, test_state_slices_cover_domains
- Imports: __future__, substrate.organism.event_spine, substrate.organism.projection_port, sys
### `substrate/organism/tests/test_projection_reconciliation_engine.py`
- Lines: 450. Doc: Tests for ProjectionReconciliationEngine (Phase 14.0).
- Classes: TestDivergenceType, TestDivergenceSeverity, TestProjectionDivergence, TestProjectionReconciliationEngine, TestNoHardcodedJarvisTerminology, TestNoExternalWrites, TestReadinessGate, TestWorkPacketGeneration
- Functions: _make_test_sources
- Imports: __future__, json, os, pytest, substrate.organism.projection_reconciliation_engine, substrate.organism.projection_source_registry, tempfile
### `substrate/organism/tests/test_projection_source_registry.py`
- Lines: 393. Doc: Tests for ProjectionSourceRegistry (Phase 14.0).
- Classes: TestProjectionSourceType, TestProjectionName, TestSourceCanonicality, TestReadStatus, TestProjectionSource, TestProjectionSourceRegistry, TestCreateInitialRegistry
- Functions: _make_test_sources
- Imports: __future__, json, os, pytest, substrate.organism.projection_source_registry, tempfile
### `substrate/organism/tests/test_protocols.py`
- Lines: 68. Doc: tests for organism protocols — deliverable, agent message, worker spec.
- Classes: -
- Functions: test_deliverable_creation, test_critique_result_threshold, test_agent_message_creation, test_worker_spec_creation, test_learning_signal_creation
- Imports: pytest, substrate.organism.protocols
### `substrate/organism/tests/test_report_dispatcher.py`
- Lines: 158. Doc: Tests for substrate.organism.report_dispatcher.
- Classes: TestReport, TestDispatchResult, TestReportDispatcherLocal, TestBridgeIntegration
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.report_dispatcher, sys, tempfile
### `substrate/organism/tests/test_runtime_events.py`
- Lines: 97. Doc: Tests for runtime event bus wiring.
- Classes: -
- Functions: test_graph_emits_register_event, test_graph_emits_status_change_event, test_graph_emits_failure_event, test_supervisor_emits_crash_event, test_supervisor_emits_recovery_event, test_supervisor_emits_recovery_failure_event
- Imports: __future__, substrate.organism.event_spine, substrate.organism.runtime_graph, substrate.organism.runtime_supervisor, sys
### `substrate/organism/tests/test_runtime_graph.py`
- Lines: 294. Doc: Tests for RuntimeGraph — runtime registry, scoring, routing.
- Classes: FakeAdapter, TestRuntimeNode, TestReliabilityScore, TestRuntimeGraph
- Functions: -
- Imports: pytest, substrate.organism.runtime_graph, sys, typing
### `substrate/organism/tests/test_runtime_supervisor.py`
- Lines: 251. Doc: Tests for RuntimeSupervisor — lifecycle management, crash detection, recovery.
- Classes: FakeAdapter, TestSupervise, TestHeartbeat, TestCrashDetection, TestRecovery, TestCheckAll, TestPersistence
- Functions: _make_supervisor
- Imports: pytest, substrate.organism.runtime_graph, substrate.organism.runtime_supervisor, sys, tempfile, time, typing
### `substrate/organism/tests/test_store.py`
- Lines: 73. Doc: tests for organism JSONL store.
- Classes: -
- Functions: store, test_save_and_list_deliverables, test_save_and_list_messages, test_save_agent_state, test_load_missing_agent_state, test_save_learning_signal
- Imports: pytest, substrate.organism.protocols, substrate.organism.store
### `substrate/organism/tests/test_workcell_protocol.py`
- Lines: 294. Doc: Tests for WorkcellV2 — durable inbox/outbox execution cells.
- Classes: FakeAdapter, FailingAdapter, TestWorkcellMessage, TestWorkcellInboxOutbox, TestWorkcellExecution, TestWorkcellCheckpoint, TestWorkcellHeartbeat, TestWorkcellStatus
- Functions: -
- Imports: json, pytest, substrate.organism.runtime_graph, substrate.organism.workcell_protocol, sys, tempfile, time, typing
### `substrate/organism/tests/test_worker_cell.py`
- Lines: 38. Doc: tests for worker cell — bounded task execution.
- Classes: -
- Functions: test_worker_executes_without_spine, test_worker_result_has_trace_id
- Imports: pytest, substrate.execution.pipeline, substrate.organism.protocols, substrate.organism.worker_cell
### `substrate/organism/tests/test_workload_probes.py`
- Lines: 101. Doc: Tests for WorkloadProbes.
- Classes: -
- Functions: test_docker_probe_returns_structure, test_disk_probe, test_memory_probe, test_repo_probe, test_process_probe, test_full_probe, test_cache, test_disk_probe_serialization, test_disk_pressure_levels, test_to_dict
- Imports: __future__, os, substrate.organism.workload_probes, sys
### `substrate/organism/tests/test_workload_runner.py`
- Lines: 125. Doc: Tests for the WorkloadRunner — Phase 5.9.
- Classes: -
- Functions: _make_runner, test_run_repo_health, test_run_disk_pressure, test_run_memory_pressure, test_run_docker_health, test_run_stale_branches, test_run_knowledge_staleness, test_run_all_observe, test_medium_risk_blocked_in_observe, test_to_dict, test_leverage_recording, test_event_emission
- Imports: __future__, substrate.organism.event_spine, substrate.organism.execution_modes, substrate.organism.leverage_metrics, substrate.organism.operator_compression, substrate.organism.workload_runner, sys
### `substrate/organism/tests/test_world_model.py`
- Lines: 276. Doc: Tests for organism world model — system self-model.
- Classes: TestWorldEvidence, TestWorldEntity, TestWorldGap, TestWorldUncertainty, TestWorldModel, TestExtraction, TestPersistence, TestDaemonIntegration
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.world_model, sys, tempfile
### `substrate/organism/tradeoff_intelligence_engine.py`
- Lines: 564. Doc: C14.1 — Tradeoff Intelligence Engine.
- Classes: TradeoffSeverity, TradeoffOption, TradeoffAnalysis, TradeoffSnapshot, TradeoffIntelligenceEngine
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/organism/trajectory_intelligence_runtime.py`
- Lines: 874. Doc: Trajectory Intelligence Runtime — Campaign 13.0
- Classes: TrajectoryStatus, TrajectoryForecast, TrajectoryIntelligenceRuntime
- Functions: _get_attr, _estimate_delta
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/trial_runner.py`
- Lines: 683. Doc: Phase 9.3 — Self-Improvement Reliability Campaign Trial Runner.
- Classes: TrialStatus, CandidateSource, TrialCandidate, TrialMetrics, TrialResult, CampaignBaseline, CampaignResult, ReliabilityCampaignRunner
- Functions: rank_candidates, build_candidate_queue, _deployment_fix_steps, _wiring_fix_steps, _route_verification_steps, safety_check, persist_campaign, persist_candidate_queue
- Imports: __future__, dataclasses, enum, json, logging, os, substrate.organism.composition_engine, substrate.organism.contradiction_engine
### `substrate/organism/trust_score.py`
- Lines: 208. Doc: Trust Score Engine — composite trust scoring via weakest-link gate.
- Classes: TrustDimension, TrustLevel, DimensionScore, TrustScore, TrustScoreEngine
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, logging, time, typing, uuid
### `substrate/organism/umh_node_registry.py`
- Lines: 150. Doc: UMH Node Registry — canonical registry of UMH organism nodes.
- Classes: UMHNodeRegistry
- Functions: _find_registry_path, _load_seed_nodes
- Imports: __future__, json, logging, os, substrate.organism.umh_node_topology, typing
### `substrate/organism/umh_node_topology.py`
- Lines: 236. Doc: UMH Node Topology — canonical node role and version models.
- Classes: UMHNodeRole, UMHNodeStatus, UMHServiceRole, UMHVersionStatus, UMHVersionInfo, UMHServiceActivation, UMHNodeRecord, UMHNodeTopology
- Functions: -
- Imports: __future__, dataclasses, enum, time, typing, uuid
### `substrate/organism/umh_version_coherence.py`
- Lines: 133. Doc: UMH Version Coherence Engine — detects version drift across nodes.
- Classes: UMHVersionCoherenceEngine
- Functions: -
- Imports: __future__, logging, substrate.organism.umh_node_registry, substrate.organism.umh_node_topology, typing
### `substrate/organism/universal_work_queue.py`
- Lines: 343. Doc: Universal Work Queue — canonical queue for all work packets.
- Classes: UniversalWorkQueue
- Functions: -
- Imports: __future__, json, logging, os, substrate.organism.work_packet, substrate.organism.work_packet_engine, time, typing
### `substrate/organism/work_graph.py`
- Lines: 461. Doc: Work Graph — read-only query projection over existing work stores.
- Classes: WorkNodeType, BlockerType, WorkBlocker, WorkResult, WorkGraphNode, WorkGraphSnapshot, WorkGraph
- Functions: _is_active, _is_blocked, _is_completed, _is_failed, _is_executable
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/work_packet.py`
- Lines: 452. Doc: Work Packet — canonical intent-to-execution container.
- Classes: PacketLifecycleStatus, WorkPacket
- Functions: persist_packets, load_packets
- Imports: __future__, dataclasses, enum, json, logging, os, tempfile, time
### `substrate/organism/work_packet_engine.py`
- Lines: 868. Doc: Work Packet Engine — creates work packets from user intent.
- Classes: WorkPacketEngine
- Functions: -
- Imports: __future__, json, logging, os, substrate.execution.cpu_gate, substrate.organism.delegation_topology, substrate.organism.intent_classifier, substrate.organism.knowledge_model_registry
### `substrate/organism/work_portfolio_runtime.py`
- Lines: 630. Doc: Work Portfolio Runtime — execution health, velocity, and drift detection.
- Classes: WorkPortfolioHealth, WorkDriftType, WorkDriftWarning, WorkPortfolioSnapshot, _VelocityTracker, WorkPortfolioRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, time, typing
### `substrate/organism/work_readiness_runtime.py`
- Lines: 634. Doc: Work Readiness Runtime — multi-dimensional readiness classification.
- Classes: ReadinessStatus, ReadinessAssessment, WorkReadinessSnapshot, WorkReadinessRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/work_recovery_runtime.py`
- Lines: 306. Doc: Work Recovery Runtime — maps work states to recovery actions.
- Classes: RecoveryState, RecoveryActionType, RecoveryAction, RecoveryAssessment, WorkRecoveryRuntime
- Functions: _classify_recovery_state
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/organism/workcell.py`
- Lines: 279. Doc: Workcell — planning/delegation workcell model for Work Packets.
- Classes: PlanningWorkcellStatus, AdvisorBranchStatus, AdvisorBranch, ReconvergenceResult, Workcell
- Functions: persist_workcells, load_workcells
- Imports: __future__, dataclasses, enum, json, logging, os, tempfile, time
### `substrate/organism/workcell_daemon.py`
- Lines: 346. Doc: WorkcellDaemon — persistent processor for workcell inboxes.
- Classes: DaemonStatus, DaemonStats, WorkcellDaemon
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, pathlib, substrate.organism.workcell_protocol, threading
### `substrate/organism/workcell_protocol.py`
- Lines: 397. Doc: WorkcellV2 — durable inbox/outbox execution cells.
- Classes: WorkcellStatus, WorkcellRole, WorkcellMessage, WorkcellCheckpoint, Workcell
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, os, pathlib, substrate.organism.runtime_graph
### `substrate/organism/worker_cell.py`
- Lines: 47. Doc: Worker cell — bounded task execution through the existing pipeline.
- Classes: WorkerCell
- Functions: -
- Imports: __future__, substrate.execution.executor, substrate.execution.pipeline, substrate.governance.risk_classes, substrate.organism.protocols, substrate.types, typing, uuid
### `substrate/organism/worker_lifecycle.py`
- Lines: 113. Doc: Worker Lifecycle Emitter — structured lifecycle events.
- Classes: WorkerEventType, WorkerLifecycleEmitter
- Functions: -
- Imports: __future__, enum, logging, typing
### `substrate/organism/worker_registry.py`
- Lines: 193. Doc: Worker Registry — active worker inventory per device.
- Classes: WorkerStatus, WorkerInstance, WorkerRegistry
- Functions: -
- Imports: __future__, dataclasses, enum, logging, threading, time, typing, uuid
### `substrate/organism/workload_placement_policy.py`
- Lines: 394. Doc: Workload placement policy — selects correct runtime + device for Work Packets.
- Classes: WorkloadType, WorkloadPlacementDecision
- Functions: _generate_decision_id, _resolve_workload_type, _pick_best, select_placement, _resolve_persist_path, persist_decision, decision_from_dict, load_decisions
- Imports: __future__, dataclasses, datetime, enum, json, logging, os, pathlib
### `substrate/organism/workload_probes.py`
- Lines: 326. Doc: Real Workload Probes — live operational pressure into the organism.
- Classes: DockerProbe, DiskProbe, MemoryProbe, RepoProbe, ProcessProbe, WorkloadProbes
- Functions: _run
- Imports: __future__, dataclasses, logging, os, pathlib, shutil, subprocess, substrate.execution.cpu_gate
### `substrate/organism/workload_runner.py`
- Lines: 850. Doc: Real Workload Runner — governed execution of operational jobs.
- Classes: WorkloadType, WorkloadRisk, WorkloadOutcome, WorkloadRunner
- Functions: _run, _scan_repo_health, _scan_stale_branches, _scan_docker_health, _scan_disk_pressure, _scan_memory_pressure, _scan_log_rotation, _scan_knowledge_staleness, _scan_test_run, _scan_runtime_reconciliation
- Imports: __future__, dataclasses, enum, logging, os, pathlib, subprocess, substrate.organism.action_envelope
### `substrate/organism/workspace_awareness.py`
- Lines: 252. Doc: Workspace Awareness Runtime — deterministic active-context detection.
- Classes: WorkspaceSnapshot, WorkspaceAwarenessRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, os, platform, time, typing
### `substrate/organism/workstation_runtime.py`
- Lines: 1401. Doc: Workstation Runtime — canonical workstation planning layer (Phase 10).
- Classes: WorkstationMode, WorkspaceStatus, PreparationStepType, SnapshotTrigger, RecommendationType, WorkspaceTemplate, PreparationStep, WorkspacePreparationPlan
- Functions: _repo_root, _workstation_data_dir, _ensure_dirs, _default_templates, get_workstation_runtime, reset_workstation_runtime
- Imports: __future__, dataclasses, enum, json, logging, os, re, time
### `substrate/organism/worktree_sandbox.py`
- Lines: 456. Doc: Worktree Sandbox Manager — isolated execution environments for autonomous improvements.
- Classes: SandboxStatus, SandboxCleanupPolicy, SandboxLock, SandboxValidationResult, WorktreeSandbox, SandboxManager
- Functions: make_branch_name, _run_git
- Imports: __future__, dataclasses, enum, json, logging, os, shutil, subprocess
### `substrate/organism/world_model.py`
- Lines: 648. Doc: World Model — organism-level self-model of UMH system state.
- Classes: EntityStatus, EntityCategory, EvidenceType, GapSeverity, WorldEvidence, WorldGap, WorldUncertainty, WorldCapability
- Functions: _check_file, _check_dir, _check_import, _file_nonempty, _extract_subsystems, _extract_adapters, _extract_transports, _extract_cockpit_surfaces, _extract_data_stores, _extract_governance, _extract_deployment, _extract_api_routes
- Imports: __future__, dataclasses, enum, importlib, json, logging, os, pathlib
### `substrate/reality_model/__init__.py`
- Lines: 37. Doc: Reality Model — dual Canonical/Instance reality modeling.
- Classes: -
- Functions: -
- Imports: substrate.reality_model.canonical_reality_write, substrate.reality_model.reality_intelligence, substrate.reality_model.reality_mutation, substrate.reality_model.reality_query
### `substrate/reality_model/canonical.py`
- Lines: 221. Doc: Canonical Reality Model — compressed, reusable intelligence.
- Classes: CanonicalRelationship, CanonicalPattern, CanonicalRealityModel
- Functions: -
- Imports: __future__, datetime, json, logging, math, pathlib, pydantic, typing
### `substrate/reality_model/canonical_reality_write.py`
- Lines: 180. Doc: Canonical reality write path — governed entry point for non-execution observations.
- Classes: CanonicalRealityWritePath
- Functions: _safe_uuid
- Imports: __future__, logging, substrate.reality_model.reality_mutation, time, typing, uuid
### `substrate/reality_model/instance.py`
- Lines: 188. Doc: Instance Reality Model — live operational truth of one user/company/environment.
- Classes: InstanceObservation, InstanceRealityModel
- Functions: -
- Imports: __future__, datetime, json, logging, math, pathlib, pydantic, typing
### `substrate/reality_model/reality_intelligence.py`
- Lines: 679. Doc: Reality Intelligence Engine — read-only retrieval and explanation.
- Classes: RealityIntelligenceEngine
- Functions: -
- Imports: __future__, datetime, logging, re, substrate.reality_model.reality_query, time, typing, uuid
### `substrate/reality_model/reality_mutation.py`
- Lines: 64. Doc: Reality mutation contracts — governed observation writes.
- Classes: MutationSource, MutationType, RealityMutation, RealityMutationReceipt
- Functions: -
- Imports: __future__, dataclasses, enum, time, typing
### `substrate/reality_model/reality_query.py`
- Lines: 59. Doc: Reality Query Contract — types for reality interrogation.
- Classes: RealityQueryType, RealityQuery, RealityEvidence, RealityQueryResult
- Functions: -
- Imports: __future__, dataclasses, enum, time, typing
### `substrate/reality_model/simulation.py`
- Lines: 326. Doc: Simulation Reality — non-mutating hypothesis testing.
- Classes: SimulationStep, SimulationDiff, SimulationResult, SimulationReality
- Functions: -
- Imports: __future__, dataclasses, json, logging, substrate.reality_model.canonical, substrate.reality_model.instance, time, typing
### `substrate/self_model.py`
- Lines: 479. Doc: Self-Model — the substrate's awareness of its own structure and state.
- Classes: Layer, ContextKind, CanonicalSelf, InstanceSelf, SelfModel
- Functions: get_handler_prefix, register_instance_loader
- Imports: __future__, dataclasses, enum, json, logging, os, pathlib, time
### `substrate/sockets/__init__.py`
- Lines: 44. Doc: UMH Socket Layer — typed boundary between substrate and integrations.
- Classes: -
- Functions: -
- Imports: substrate.sockets.envelopes, substrate.sockets.protocols, substrate.sockets.registry
### `substrate/sockets/approval_port.py`
- Lines: 42. Doc: Approval port — substrate-layer abstraction for approval decisions.
- Classes: -
- Functions: register_approval_handler, submit_approval, get_approval_handler
- Imports: __future__, typing
### `substrate/sockets/capability_socket.py`
- Lines: 110. Doc: Capability socket — bidirectional execution for integration capabilities.
- Classes: CapabilitySocket
- Functions: -
- Imports: __future__, logging, substrate.sockets.envelopes, substrate.sockets.protocols, time, typing, uuid
### `substrate/sockets/channel_port.py`
- Lines: 24. Doc: Channel port — substrate-layer abstraction for the channel router.
- Classes: -
- Functions: register_channel_router, get_channel_router
- Imports: typing
### `substrate/sockets/config_port.py`
- Lines: 70. Doc: Config port — substrate-layer abstraction for runtime config access.
- Classes: -
- Functions: register_config_store, get_config, set_config, get_all_config, on_config_change
- Imports: __future__, typing
### `substrate/sockets/envelopes.py`
- Lines: 104. Doc: Envelope dataclasses — the data shapes that cross the socket boundary.
- Classes: SignalEnvelope, SignalReceipt, CapabilityRequest, CapabilityResponse, OutcomeEnvelope, ViewFrame
- Functions: -
- Imports: __future__, datetime, pydantic, substrate.types, typing, uuid
### `substrate/sockets/message_port.py`
- Lines: 30. Doc: Message port — substrate-layer abstraction for conversation persistence.
- Classes: -
- Functions: register_message_sink, save_message, get_message_sink
- Imports: __future__, typing
### `substrate/sockets/notification.py`
- Lines: 92. Doc: Notification socket — substrate-layer abstraction for outbound notifications.
- Classes: -
- Functions: register_notifier, register_chunker, register_chat_push, register_approval_alert, notify_webhook, push_chat, alert_approval, chunk_content
- Imports: __future__, typing
### `substrate/sockets/notification_engine.py`
- Lines: 246. Doc: Multi-channel notification engine — substrate-layer abstraction.
- Classes: NotificationChannel, NotificationPriority, Notification, NotificationResult, NotificationEngine
- Functions: get_notification_engine
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/sockets/outcome_socket.py`
- Lines: 81. Doc: Outcome socket — outbound result notifications to integrations.
- Classes: OutcomeSocket
- Functions: -
- Imports: __future__, logging, substrate.sockets.envelopes, substrate.sockets.protocols
### `substrate/sockets/projection_port.py`
- Lines: 269. Doc: Projection Port — abstract consumption layer for projections.
- Classes: ProjectionRegistration, ProjectionPortProtocol, ProjectionPort
- Functions: register_projection, get_projection, list_projections, unregister_projection, detect_import_drift, scan_projection_imports
- Imports: __future__, dataclasses, json, logging, os, threading, time, typing
### `substrate/sockets/protocols.py`
- Lines: 129. Doc: Protocol definitions for integration-side contracts.
- Classes: SignalDescriptor, CapabilityDescriptor, CapabilityHealth, SignalEmitter, CapabilityHandler, OutcomeReceiver, ViewSubscriber
- Functions: -
- Imports: __future__, pydantic, substrate.governance.risk_classes, substrate.sockets.envelopes, substrate.types, typing
### `substrate/sockets/registry.py`
- Lines: 180. Doc: Integration registry — central registration and generic adapter bridge.
- Classes: IntegrationManifest, IntegrationAdapter, IntegrationRegistry
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.governance.risk_classes, substrate.sockets.capability_socket, substrate.sockets.envelopes, substrate.sockets.outcome_socket, substrate.sockets.protocols
### `substrate/sockets/sensing_port.py`
- Lines: 68. Doc: Sensing adapter port — substrate-layer abstraction for perception registration.
- Classes: -
- Functions: register_sensing_registry, register_signal_handler, get_registry, emit_sensing_signal, sensing_health, sensing_summary
- Imports: __future__, typing
### `substrate/sockets/signal_socket.py`
- Lines: 109. Doc: Signal socket — inbound intake for external integrations.
- Classes: SignalSocket
- Functions: -
- Imports: __future__, datetime, logging, substrate.sockets.envelopes, substrate.sockets.protocols, typing, uuid
### `substrate/sockets/view/__init__.py`
- Lines: 2. Doc: View socket broadcast infrastructure — sync→async bridge and WebSocket endpoint.
- Classes: -
- Functions: -
- Imports: -
### `substrate/sockets/view/broadcaster.py`
- Lines: 147. Doc: Broadcaster — sync→async bridge for ViewFrame delivery.
- Classes: ViewFrameBroadcaster
- Functions: _serialize_frame, make_pipeline_listener, _extract_uuid
- Imports: __future__, asyncio, dataclasses, datetime, logging, substrate.sockets.envelopes, typing, uuid
### `substrate/sockets/view/websocket.py`
- Lines: 96. Doc: WebSocket endpoint for broadcasting ViewFrames to cockpit clients.
- Classes: ConnectionManager
- Functions: broadcast_frame, ws_endpoint
- Imports: __future__, fastapi, json, logging, typing
### `substrate/sockets/view_socket.py`
- Lines: 63. Doc: View socket — broadcast pipeline state frames to observers.
- Classes: ViewSocket
- Functions: -
- Imports: __future__, logging, substrate.sockets.envelopes, substrate.sockets.protocols
### `substrate/state/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/business/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/business/business_instance.py`
- Lines: 490. Doc: BusinessInstance — venture-stage context layer.
- Classes: BusinessInstance, BusinessInstanceManager
- Functions: get_ai_name
- Imports: dataclasses, datetime, json, typing
### `substrate/state/business/venture_knowledge.py`
- Lines: 201. Doc: -
- Classes: Venture, VentureKnowledgeBase
- Functions: _load_ventures_from_json, get_venture_name
- Imports: dataclasses, json, logging, os, substrate.state.storage.db, typing
### `substrate/state/config/__init__.py`
- Lines: 28. Doc: UMH Config Store — layered configuration with runtime mutability.
- Classes: -
- Functions: -
- Imports: substrate.state.config.config_store
### `substrate/state/config/config_store.py`
- Lines: 184. Doc: ConfigStore — layered JSON-file-backed configuration.
- Classes: ConfigStore
- Functions: -
- Imports: __future__, json, logging, os, pathlib, threading, typing
### `substrate/state/context/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/context/context.py`
- Lines: 60. Doc: -
- Classes: SubstrateContext
- Functions: load_ventures_from_env, load_context_from_env, try_load_context_from_env
- Imports: dataclasses, dotenv, json, os, pathlib
### `substrate/state/finance/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/finance/expense_tracker.py`
- Lines: 444. Doc: Expense Tracker — processes receipts from Gmail RECEIPTS-FINANCIALS folder,
- Classes: -
- Functions: extract_expense_from_email, store_expense, get_monthly_summary, process_receipt_emails, create_invoice, get_invoices, get_overdue_invoices, generate_invoice_text, generate_expense_report, generate_budget_vs_actual
- Imports: datetime, dotenv, json, logging, os, substrate.self_model, zoneinfo
### `substrate/state/finance/subscription_tracker.py`
- Lines: 122. Doc: Subscription Tracker — maintains a registry of active
- Classes: -
- Functions: get_subscriptions, add_subscription, get_upcoming_renewals, get_monthly_subscription_total
- Imports: datetime, json, logging, substrate.self_model, zoneinfo
### `substrate/state/lifecycle/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/lifecycle/stage_manager.py`
- Lines: 287. Doc: StageManager — auto-updates Notion, Discord, and primitives when stage advances.
- Classes: StageTransitionResult, StageManager
- Functions: detect_stage_transition
- Imports: dataclasses, datetime, dotenv, os, pathlib, substrate.state.context.context, sys
### `substrate/state/logs/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/logs/decision_log.py`
- Lines: 211. Doc: DecisionLog — permanent record of important decisions made in conversation.
- Classes: Decision, DecisionLog
- Functions: -
- Imports: dataclasses, json, re, substrate.state.context.context, uuid
### `substrate/state/memory/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/memory/contracts/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/memory/contracts/canonical_memory_query_contracts.py`
- Lines: 208. Doc: Canonical Memory Query contracts for the UMH substrate layer.
- Classes: QueryScope, CanonicalMemoryQuery, MemoryLineageReference, QueryResultReference, QueryProofArtifact
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, typing
### `substrate/state/memory/contracts/canonical_memory_reconciliation_engine_v1.py`
- Lines: 530. Doc: Canonical Memory Reconciliation Engine v1.
- Classes: ReconciliationAction, ReconciliationDecision, ReconciliationReceipt, ReconciliationEngine
- Functions: _normalize_label, _label_overlap_score, _content_overlap_score, _detect_conflict, _primitive_to_entity_type
- Imports: .memory_identity_v1, __future__, dataclasses, datetime, enum, hashlib, json, pathlib
### `substrate/state/memory/contracts/canonical_memory_store_v1.py`
- Lines: 290. Doc: Canonical Memory Store v1 — append-only, replay-safe, queryable memory persistence.
- Classes: PromotionDecision, PromotionReceipt, MemoryEntry, CanonicalMemoryStore
- Functions: _deterministic_id
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, pathlib, substrate.types
### `substrate/state/memory/contracts/memory_conflict_governance_v1.py`
- Lines: 168. Doc: Memory Conflict Governance v1.
- Classes: ConflictResolution, ConflictRecord, ConflictGovernance
- Functions: -
- Imports: .memory_identity_v1, __future__, dataclasses, datetime, enum, json, pathlib, typing
### `substrate/state/memory/contracts/memory_identity_v1.py`
- Lines: 101. Doc: Memory Identity v1 — deterministic identity model for canonical memories.
- Classes: MemoryIdentity, EntityReference
- Functions: deterministic_id, content_fingerprint
- Imports: __future__, dataclasses, datetime, hashlib, typing
### `substrate/state/memory/memory.py`
- Lines: 1040. Doc: Persistent memory for OS agents — backed by Neon (PostgreSQL).
- Classes: AgentMemory, Message, ConversationMemory
- Functions: _utcnow, _tokens_to_neon
- Imports: dataclasses, datetime, json, pathlib, substrate.state.storage.db, typing, uuid
### `substrate/state/metrics/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/metrics/founder_rate.py`
- Lines: 285. Doc: Founder Rate — framework for valuing
- Classes: -
- Functions: calculate_founder_rate, store_founder_rate, get_current_founder_rate, log_time_block, get_time_audit_summary, add_to_no_list, get_no_list, check_against_no_list, detect_delegation_threshold
- Imports: datetime, dotenv, json, logging, pathlib, substrate.self_model, zoneinfo
### `substrate/state/metrics/okr_tracker.py`
- Lines: 115. Doc: OKR Tracker — tracks Objectives and Key Results per venture.
- Classes: -
- Functions: set_okr, get_okrs, generate_okr_report
- Imports: datetime, dotenv, json, logging, pathlib, substrate.self_model, zoneinfo
### `substrate/state/permissions/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/permissions/os_trinity.py`
- Lines: 382. Doc: OSTrinity — OS Trinity harness layer.
- Classes: OSTrinity
- Functions: -
- Imports: datetime, json, substrate.state.context.context, uuid
### `substrate/state/preferences/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/preferences/model_preferences.py`
- Lines: 448. Doc: Multi-model router with business context awareness and full human override.
- Classes: ModelPreferences
- Functions: -
- Imports: os, substrate.state.context.context, substrate.state.storage.db
### `substrate/state/profiles/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/profiles/user_model.py`
- Lines: 455. Doc: UserModel — learns how the founder thinks, communicates, and makes decisions.
- Classes: UserModel
- Functions: -
- Imports: adapters.models.agent_runtime, datetime, dotenv, json, os, pathlib, substrate.contracts.agent_types, substrate.control_plane.runtime.cognitive_loop
### `substrate/state/providers/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/providers/provider_state.py`
- Lines: 288. Doc: Global Provider State + Backpressure + Execution Budget.
- Classes: ProviderStatus, SystemStatus, ProviderState, ExecutionBudget, SystemProviderState
- Functions: get_system_state
- Imports: __future__, dataclasses, enum, logging, os, threading, time
### `substrate/state/registries/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/registries/claude_skill_registry.py`
- Lines: 242. Doc: ClaudeSkillRegistry — tracks all .claude/skills files, syncs them to Neon,
- Classes: ClaudeSkill, ClaudeSkillRegistryManager
- Functions: -
- Imports: dataclasses, datetime, os, pathlib
### `substrate/state/registries/os_registry.py`
- Lines: 308. Doc: OSRegistry — formal registry for all three OS modules.
- Classes: OSModule, OSModuleConfig, OSRegistryManager
- Functions: -
- Imports: dataclasses, enum
### `substrate/state/registries/skill_registry.py`
- Lines: 255. Doc: -
- Classes: Skill, SkillRegistry
- Functions: get_skill_registry, reset_skill_registry
- Imports: dataclasses, numpy, os, pathlib, re, typing
### `substrate/state/registries/skill_registry_v2.py`
- Lines: 479. Doc: SkillRegistryV2 — first-class skill objects with trust scoring,
- Classes: SkillDomain, TrustLevel, SkillV2, SkillRegistryV2
- Functions: -
- Imports: dataclasses, datetime, enum
### `substrate/state/registries/template_registry.py`
- Lines: 589. Doc: TemplateRegistry — formal template schema for the Meta Harness.
- Classes: TemplateSlot, Template, TemplateInstance, TemplateRegistry
- Functions: _common_business_slots
- Imports: __future__, dataclasses, datetime, typing, uuid
### `substrate/state/session/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/session/session_state.py`
- Lines: 90. Doc: -
- Classes: SessionState
- Functions: -
- Imports: datetime, json, pathlib
### `substrate/state/storage/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/storage/db.py`
- Lines: 130. Doc: Neon (PostgreSQL) connection layer for the Python AI layer.
- Classes: -
- Functions: _load_caches, get_conn, resolve_venture, resolve_skill
- Imports: contextlib, dotenv, os, pathlib, psycopg2, psycopg2.extras, re, typing
### `substrate/state/stores/agent_registry_store.py`
- Lines: 28. Doc: AgentRegistryStore — canonical write API for the agents table.
- Classes: AgentRegistryStore
- Functions: -
- Imports: substrate.state.storage.db, uuid
### `substrate/state/stores/approval_store.py`
- Lines: 78. Doc: ApprovalStore — canonical write API for the approvals table.
- Classes: ApprovalStore
- Functions: -
- Imports: datetime, json, substrate.state.storage.db, uuid
### `substrate/state/stores/context_compaction_store.py`
- Lines: 38. Doc: ContextCompactionStore — canonical write API for the context_compactions table.
- Classes: ContextCompactionStore
- Functions: -
- Imports: json, substrate.state.storage.db
### `substrate/state/stores/email_folder_store.py`
- Lines: 47. Doc: EmailFolderStore — canonical write API for the email_folders table.
- Classes: EmailFolderStore
- Functions: -
- Imports: substrate.state.storage.db
### `substrate/state/stores/embedding_store.py`
- Lines: 37. Doc: EmbeddingStore — canonical write API for the embeddings table.
- Classes: EmbeddingStore
- Functions: -
- Imports: substrate.state.storage.db
### `substrate/state/stores/entity_link_store.py`
- Lines: 40. Doc: EntityLinkStore — canonical write API for the entity_links table.
- Classes: EntityLinkStore
- Functions: -
- Imports: json, substrate.state.storage.db
### `substrate/state/stores/entity_store.py`
- Lines: 336. Doc: EntityStore — persistence layer for the entity hierarchy.
- Classes: EntityStore
- Functions: _ensure_tables
- Imports: __future__, datetime, json, logging, substrate.state.storage.db, typing, uuid
### `substrate/state/stores/goal_store.py`
- Lines: 189. Doc: GoalStore — canonical write API for the goals and goal_outcomes tables.
- Classes: GoalStore
- Functions: -
- Imports: json, substrate.state.storage.db
### `substrate/state/stores/higgsfield_store.py`
- Lines: 50. Doc: HiggsFieldStore — canonical write API for the higgsfield_jobs table.
- Classes: HiggsFieldStore
- Functions: -
- Imports: json, substrate.state.storage.db
### `substrate/state/stores/permission_store.py`
- Lines: 115. Doc: PermissionStore — canonical write API for cross_product_permissions and product_connections tables.
- Classes: PermissionStore
- Functions: -
- Imports: datetime, json, substrate.state.storage.db, uuid
### `substrate/state/stores/preference_store.py`
- Lines: 47. Doc: PreferenceStore — canonical write API for the model_preferences table.
- Classes: PreferenceStore
- Functions: -
- Imports: json, substrate.state.storage.db
### `substrate/state/stores/profile_store.py`
- Lines: 149. Doc: ProfileStore — canonical write API for human_profiles, user_profiles, user_intelligence_profiles.
- Classes: ProfileStore
- Functions: _j
- Imports: datetime, json, substrate.state.storage.db, uuid
### `substrate/state/stores/skill_store.py`
- Lines: 81. Doc: SkillStore — canonical API for the skills table.
- Classes: SkillStore
- Functions: -
- Imports: substrate.state.storage.db, uuid
### `substrate/state/stores/task_store.py`
- Lines: 84. Doc: TaskStore — canonical write API for the tasks table.
- Classes: TaskStore
- Functions: -
- Imports: substrate.state.storage.db
### `substrate/state/stores/venture_store.py`
- Lines: 37. Doc: VentureStore — canonical write API for the ventures table.
- Classes: VentureStore
- Functions: -
- Imports: json, substrate.state.storage.db, uuid
### `substrate/state/tenancy/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/tenancy/tenant.py`
- Lines: 146. Doc: Tenant — formal multi-tenant isolation layer for EOS.
- Classes: TenantLayer, TenantContext, TenantManager
- Functions: -
- Imports: dataclasses, enum
### `substrate/state/transformation_state_ledger.py`
- Lines: 384. Doc: Transformation State Ledger for the UMH substrate layer.
- Classes: TransformationStage, StateArtifactReference, TransformationEdge, StateLedgerRecord, TransformationStateLedger
- Functions: compute_hash, make_state_id, make_trace_id
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, pathlib, typing
### `substrate/state/work/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/state/work/work_state.py`
- Lines: 226. Doc: Work State Detection + Idle Gate + Adaptive Throttling.
- Classes: Pressure, WorkState
- Functions: record_signal, has_recent_signal, _measure_pressure, _get_swap_pct, _compute_idle_delay, reset_idle_counter, register_goal_detector, register_task_detector, detect_work_state, get_idle_delay
- Imports: __future__, dataclasses, enum, logging, os, threading, time, typing
### `substrate/types.py`
- Lines: 1401. Doc: -
- Classes: SignalSource, SignalUrgency, Modality, Attachment, SignalEnvelope, Identity, MemoryType, MemoryEntry
- Functions: required_tier_for_action
- Imports: __future__, datetime, enum, pydantic, substrate.governance.risk_classes, substrate.sockets.envelopes, substrate.sockets.protocols, typing
### `substrate/understanding/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/breadth_expansion.py`
- Lines: 187. Doc: Breadth Expansion Engine — step 9 of the 27-step spine.
- Classes: DomainExpansion, BreadthResult, BreadthExpansionEngine
- Functions: -
- Imports: __future__, dataclasses, logging, typing
### `substrate/understanding/deliberation/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/deliberation/council.py`
- Lines: 529. Doc: Deliberation Council — 7-role multi-perspective advisory system.
- Classes: CouncilRole, Verdict, RoleOpinion, CouncilDeliberation, DeliberationCouncil
- Functions: -
- Imports: __future__, dataclasses, enum, json, logging, substrate.reality_model.simulation, time, typing
### `substrate/understanding/domains/__init__.py`
- Lines: 15. Doc: Domain bridge — maps ontology observations to domain-typed projections.
- Classes: -
- Functions: -
- Imports: ., .contract, .registry
### `substrate/understanding/domains/business.py`
- Lines: 246. Doc: Business domain bridge — structural mapping from ontology to business primitives.
- Classes: BusinessBridge
- Functions: -
- Imports: .contract, .registry, __future__, substrate.understanding.ontology.primitive_decomposition_v1
### `substrate/understanding/domains/contract.py`
- Lines: 75. Doc: Domain bridge protocol and projection dataclass.
- Classes: DomainBridge, DomainProjection
- Functions: make_projection_id
- Imports: __future__, dataclasses, substrate.understanding.ontology.primitive_decomposition_v1, typing, uuid
### `substrate/understanding/domains/creator.py`
- Lines: 516. Doc: Creator domain bridge — structural mapping from ontology to creator primitives.
- Classes: CreatorBridge
- Functions: -
- Imports: .contract, .registry, __future__, substrate.understanding.ontology.primitive_decomposition_v1
### `substrate/understanding/domains/life.py`
- Lines: 569. Doc: Life domain bridge — structural mapping from ontology to life primitives.
- Classes: LifeBridge
- Functions: -
- Imports: .contract, .registry, __future__, substrate.understanding.ontology.primitive_decomposition_v1
### `substrate/understanding/domains/registry.py`
- Lines: 32. Doc: Bridge registry — plug-in system for domain bridges.
- Classes: BridgeRegistry
- Functions: -
- Imports: .contract, __future__
### `substrate/understanding/embedding/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/embedding/embedder.py`
- Lines: 70. Doc: Lightweight text embedder — shared singleton used by memory.py and
- Classes: -
- Functions: _get_model, embed, cosine_similarity, serialize, deserialize
- Imports: numpy
### `substrate/understanding/embedding/embedding_engine.py`
- Lines: 401. Doc: EmbeddingEngine — Three-tier hybrid embedding with graceful degradation.
- Classes: EmbeddingEngine
- Functions: -
- Imports: dotenv, os, pathlib, typing
### `substrate/understanding/intelligence/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/intelligence/competitive_intel.py`
- Lines: 145. Doc: Competitive Intelligence — tracks competitor signals
- Classes: -
- Functions: log_competitor_signal, get_recent_signals, synthesize_competitive_landscape
- Imports: datetime, dotenv, json, logging, os, zoneinfo
### `substrate/understanding/intelligence/human_intelligence.py`
- Lines: 709. Doc: HumanIntelligenceEngine — behavioral profiling for every person the system
- Classes: HumanIntelligenceEngine
- Functions: _utcnow, format_profile
- Imports: adapters.models.agent_runtime, datetime, glob, json, os, pathlib, re, substrate.contracts.agent_types
### `substrate/understanding/intelligence/input_intelligence.py`
- Lines: 348. Doc: Input Intelligence Layer
- Classes: InputAssessment, EnhancedInput, InputIntelligence
- Functions: -
- Imports: dataclasses, logging, os, re
### `substrate/understanding/intelligence/person_recognition.py`
- Lines: 600. Doc: Person Recognition — central module for identifying known people
- Classes: HumanIntelligenceProfile
- Functions: create_lead_file, recognize_person, format_person_context, build_intelligence_profile, format_intelligence_profile, score_relationship_health
- Imports: dataclasses, datetime, json, logging, os, typing, zoneinfo
### `substrate/understanding/intelligence/stakeholder_map.py`
- Lines: 249. Doc: Stakeholder Map — tracks key stakeholders per venture,
- Classes: -
- Functions: add_stakeholder, get_stakeholders, generate_stakeholder_brief, add_board_member, get_board_members, generate_board_update_brief
- Imports: datetime, dotenv, json, logging, os, substrate.self_model, zoneinfo
### `substrate/understanding/interpretation/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/interpretation/interpretation_engine_v1.py`
- Lines: 552. Doc: Interpretation Engine v1 for the UMH substrate layer.
- Classes: InterpretationStage, ConfidenceEnvelope, InterpretationBoundary, InterpretationInput, InterpretationHypothesis, InterpretationResult, _DeterministicIdGenerator, InterpretationEngineV1
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, hashlib, json, substrate.understanding.ontology.primitive_decomposition_v1, typing
### `substrate/understanding/knowledge/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/knowledge/knowledge_domains.py`
- Lines: 1127. Doc: KnowledgeDomainRegistry — base equilibrium awareness layer.
- Classes: KnowledgeDomainRegistry
- Functions: -
- Imports: datetime, json, os, pathlib, sys
### `substrate/understanding/knowledge/knowledge_graph.py`
- Lines: 522. Doc: KnowledgeGraph — entity relationship layer for EOS.
- Classes: KnowledgeGraph
- Functions: _utcnow
- Imports: datetime, json, substrate.state.context.context, substrate.state.storage.db
### `substrate/understanding/knowledge/knowledge_integrator.py`
- Lines: 238. Doc: KnowledgeIntegrator — permanent knowledge accumulation layer.
- Classes: KnowledgeIntegrator
- Functions: -
- Imports: substrate.state.context.context, substrate.state.memory.memory, substrate.understanding.embedding.embedding_engine, typing, uuid
### `substrate/understanding/knowledge/knowledge_layers.py`
- Lines: 478. Doc: Knowledge Layer Engine — behavioral distillation layers 6-17.
- Classes: KnowledgeLayer, KnowledgeLayerEngine
- Functions: -
- Imports: __future__, dataclasses, re, typing
### `substrate/understanding/knowledge/philosophy_lenses.py`
- Lines: 383. Doc: Philosophy Lens Engine — codified lenses from PHILOSOPHY.md Section VII.
- Classes: PhilosophyLens, LensEngine
- Functions: -
- Imports: __future__, dataclasses, re
### `substrate/understanding/ontology/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/ontology/primitive_decomposition_v1.py`
- Lines: 128. Doc: Primitive Decomposition v1 for the UMH substrate layer.
- Classes: PrimitiveType, RelationshipType, PrimitiveObservation, PrimitiveRelationship, DecompositionResult
- Functions: -
- Imports: __future__, dataclasses, enum, typing
### `substrate/understanding/ontology/primitives.py`
- Lines: 924. Doc: Primitives — stage-aware business rules and contextual reasoning engine.
- Classes: KnowledgePrimitive, PrimitiveRegistry, ContextualReasoningEngine
- Functions: -
- Imports: dataclasses, substrate.state.context.context
### `substrate/understanding/patterns/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/patterns/leverage_patterns.py`
- Lines: 120. Doc: Leverage Pattern Detection — identifies Leverage Killer
- Classes: -
- Functions: detect_leverage_killer, check_solution_standard
- Imports: logging
### `substrate/understanding/patterns/pattern_engine.py`
- Lines: 206. Doc: PatternEngine — cross-session behavioral pattern detection.
- Classes: Pattern, PatternEngine
- Functions: -
- Imports: dataclasses, datetime, substrate.state.context.context
### `substrate/understanding/perception/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/perception/orchestrator.py`
- Lines: 1158. Doc: GenericIngestionOrchestrator — source-agnostic canonical pipeline.
- Classes: Signal, InterpretationResult, WorldUpdate, MemoryWrite, PromotionReceipt, QueryProof, IngestionResult, GenericIngestionOrchestrator
- Functions: -
- Imports: __future__, dataclasses, datetime, json, logging, pathlib, substrate.execution.bridge.memory_scope_contracts, substrate.governance.policy.authority_tier
### `substrate/understanding/perception/parsers/__init__.py`
- Lines: 39. Doc: Modular parser system for the EOS codebase knowledge graph.
- Classes: -
- Functions: parse
- Imports: .base, .config_parser, .js_parser, .python_parser, .sql_parser, .ts_parser, __future__, pathlib
### `substrate/understanding/perception/parsers/base.py`
- Lines: 58. Doc: Shared contracts for all language parsers.
- Classes: ParsedSymbol, ParsedImport, ParsedFile, Parser
- Functions: -
- Imports: __future__, abc, dataclasses, pathlib
### `substrate/understanding/perception/parsers/config_parser.py`
- Lines: 52. Doc: Config parser — top-level key extraction for JSON/YAML/TOML files.
- Classes: ConfigParser
- Functions: -
- Imports: .base, __future__, json, os, pathlib
### `substrate/understanding/perception/parsers/js_parser.py`
- Lines: 96. Doc: JavaScript parser — regex-based symbol + import extraction.
- Classes: JSParser
- Functions: -
- Imports: .base, __future__, os, pathlib, re
### `substrate/understanding/perception/parsers/python_parser.py`
- Lines: 126. Doc: Python parser — wraps the existing AST scanner in codebase_graph.py.
- Classes: PythonParser
- Functions: _load_legacy_scanner
- Imports: .base, __future__, ast, importlib.util, os, pathlib, re, sys
### `substrate/understanding/perception/parsers/sql_parser.py`
- Lines: 54. Doc: SQL parser — detects tables, views, and FROM references.
- Classes: SQLParser
- Functions: -
- Imports: .base, __future__, os, pathlib, re
### `substrate/understanding/perception/parsers/ts_parser.py`
- Lines: 34. Doc: TypeScript parser — reuses JS regexes and adds interface/type extraction.
- Classes: TSParser
- Functions: -
- Imports: .base, .js_parser, __future__, pathlib, re
### `substrate/understanding/perception/source.py`
- Lines: 34. Doc: Source abstraction for the generic ingestion pipeline.
- Classes: RawContent, Source
- Functions: -
- Imports: __future__, dataclasses, substrate.governance.policy.authority_tier, typing
### `substrate/understanding/reality/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/reality/reality_context.py`
- Lines: 154. Doc: RealityContext — ambient present-state snapshot.
- Classes: RealityContext
- Functions: -
- Imports: substrate.state.context.context
### `substrate/understanding/reality/reality_engine.py`
- Lines: 589. Doc: RealityIntelligenceEngine — continuous market intelligence layer.
- Classes: RealityIntelligenceEngine
- Functions: _notify
- Imports: datetime, dotenv, os, pathlib, substrate.contracts.agent_types, substrate.control_plane.events.event_bus, substrate.control_plane.runtime.cognitive_loop, substrate.control_plane.strategy.strategy_engine
### `substrate/understanding/research/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/research/research_engine.py`
- Lines: 678. Doc: ResearchEngine — autonomous knowledge gap detection and research layer.
- Classes: ResearchEngine
- Functions: -
- Imports: datetime, dotenv, os, pathlib, re, substrate.contracts.agent_types, substrate.control_plane.runtime.cognitive_loop, substrate.control_plane.strategy.strategy_engine
### `substrate/understanding/signals/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/signals/founder_capture.py`
- Lines: 228. Doc: Founder Capture — detects tasks, ideas, and reminders from Discord messages
- Classes: -
- Functions: should_capture, _classify_venture, capture_to_neon, capture_to_notion, capture
- Imports: datetime, json, logging, os, substrate.self_model
### `substrate/understanding/world_model/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/world_model/world_model.py`
- Lines: 261. Doc: WorldModel — two-layer world model for the Meta Harness.
- Classes: WorldModelEntry, CanonicalWorldModel, InstanceWorldModel, WorldModel
- Functions: -
- Imports: dataclasses, datetime, os, sys, uuid
### `substrate/understanding/world_pulse/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `substrate/understanding/world_pulse/world_pulse.py`
- Lines: 601. Doc: WorldPulse — continuous market and creator intelligence monitoring.
- Classes: WorldPulse
- Functions: -
- Imports: substrate.state.context.context, substrate.understanding.knowledge.knowledge_integrator
### `substrate/workstation/__init__.py`
- Lines: 18. Doc: Workstation state — profile, session, and resume snapshots.
- Classes: -
- Functions: -
- Imports: substrate.workstation.state
### `substrate/workstation/activation.py`
- Lines: 215. Doc: Activation signal and presence session for workstation control.
- Classes: ActivationSource, ActivationCapabilityStatus, ActivationSignal, PresenceCapability, PresenceSession
- Functions: get_activation_capabilities, _detect_stt_status, _detect_stt_blocker
- Imports: __future__, dataclasses, datetime, enum, os, typing, uuid
### `substrate/workstation/agent_workforce_runtime.py`
- Lines: 345. Doc: Agent Workforce Runtime — Campaign 19.1.
- Classes: WorkforceHealth, AgentWorkforceSnapshot, AgentWorkforceRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/ambient_wake_runtime.py`
- Lines: 408. Doc: Ambient Wake Runtime — Campaign 20.2.
- Classes: AmbientState, WakeTransition, AmbientWakeSnapshot, AmbientWakeRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/app_resolver.py`
- Lines: 230. Doc: Native app resolver — Chrome-first browser policy, app vs website classification.
- Classes: AppTarget
- Functions: _get_platform_process_map, _strip_verb_prefix, classify_app_vs_website, resolve_app_target, resolve_search_url
- Imports: __future__, dataclasses, logging, re, typing, urllib.parse
### `substrate/workstation/attention_aggregation_runtime.py`
- Lines: 256. Doc: Attention Aggregation Runtime — Campaign 18.2.
- Classes: AttentionQueueSnapshot, AttentionAggregationRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/workstation/attention_vision_runtime.py`
- Lines: 365. Doc: Attention Vision Runtime — Campaign 21.3.
- Classes: VisualSignalType, VisualSignalSeverity, VisualAttentionSignal, AttentionVisionSnapshot, AttentionVisionRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, re, time, typing
### `substrate/workstation/camera_commands.py`
- Lines: 648. Doc: Camera command dispatcher — routes CAMERA_CONTROL intents to operations.
- Classes: CameraCommand
- Functions: classify_camera_command, dispatch_camera_command, analyze_snapshot
- Imports: __future__, dataclasses, logging, re, typing
### `substrate/workstation/checkpoint.py`
- Lines: 152. Doc: Continuity checkpoint — state snapshot on continuity transitions.
- Classes: ContinuityCheckpoint, CheckpointManager
- Functions: -
- Imports: __future__, dataclasses, datetime, json, logging, os, pathlib, typing
### `substrate/workstation/cockpit_capability_map.py`
- Lines: 421. Doc: Cockpit Capability Map — audit surface for cockpit routes, panels, stores.
- Classes: SurfaceCategory, MVPStatus, CoverageStatus, CockpitSurface, DuplicationFinding, CockpitCapabilitySnapshot, CockpitCapabilityMap
- Functions: _classify_coverage
- Imports: __future__, dataclasses, enum, time, typing
### `substrate/workstation/command_center_mvp_runtime.py`
- Lines: 390. Doc: Command Center MVP Runtime — operator landing surface.
- Classes: CommandCenterSection, ExecutionPulse, CapabilityPulse, MigrationPulse, CommandCenterRecommendation, CommandCenterSnapshot, CommandCenterMVPRuntime
- Functions: _safe_call
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/command_router.py`
- Lines: 1168. Doc: Command router — natural language command classification and routing.
- Classes: CommandIntent, GovernanceRequirement, CommandResult
- Functions: _strip_node_qualifier, _get_known_app_keys, _is_workstation_app_target, classify_intent, resolve_navigation_target, resolve_mode_target, _lookup_app, _enrich_with_lane_info, resolve_workstation_target, resolve_continuity_target, resolve_packet_control_action, governance_requirement
- Imports: __future__, dataclasses, datetime, enum, logging, typing, uuid
### `substrate/workstation/continuity.py`
- Lines: 215. Doc: Continuity state machine — unified lifecycle for operator presence/absence.
- Classes: ContinuityState, ContinuityTransition, ContinuityStateMachine
- Functions: -
- Imports: __future__, dataclasses, datetime, enum, logging, typing, uuid
### `substrate/workstation/continuity_engine.py`
- Lines: 583. Doc: Continuity engine — orchestrator binding all continuity subsystems.
- Classes: CompositeState, StartupResult, ShutdownResult, ContinuityEngine
- Functions: -
- Imports: __future__, dataclasses, datetime, json, logging, os, pathlib, typing
### `substrate/workstation/device_presence.py`
- Lines: 163. Doc: Device presence registry for active cockpit sessions.
- Classes: DeviceSession, DevicePresenceRegistry
- Functions: get_registry
- Imports: __future__, dataclasses, datetime, logging, threading, typing
### `substrate/workstation/environment_awareness_runtime.py`
- Lines: 363. Doc: Environment Awareness Runtime — Campaign 21.1.
- Classes: SurfaceType, SurfaceHealth, ObservedSurface, EnvironmentAwarenessSnapshot, EnvironmentAwarenessRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/execution_fabric_runtime.py`
- Lines: 339. Doc: Execution Fabric Runtime — Campaign 19.0.
- Classes: ExecutionFabricState, ExecutionFabricSnapshot, ExecutionFabricRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/file_browser.py`
- Lines: 221. Doc: Safe read-only file browser with allowlisted root paths.
- Classes: FileEntry, BrowseResult, FileReadResult
- Functions: _detect_source_env, _is_path_allowed, _detect_language, browse_directory, read_file
- Imports: __future__, dataclasses, os, pathlib, platform, typing
### `substrate/workstation/intent_contract.py`
- Lines: 259. Doc: Intent contract — converts high-level operator intent into end-state designs.
- Classes: IntentStatus, IntentContract, IntentContractManager
- Functions: extract_intent_risk, create_contract_from_intent
- Imports: __future__, dataclasses, datetime, json, logging, os, pathlib, typing
### `substrate/workstation/jarvis_command.py`
- Lines: 6. Doc: Backward-compat shim — canonical module is command_router.py.
- Classes: -
- Functions: -
- Imports: substrate.workstation.command_router
### `substrate/workstation/lifecycle_modes.py`
- Lines: 51. Doc: Lifecycle modes — system-level cycle that governs safety and background behavior.
- Classes: LifecycleMode
- Functions: -
- Imports: __future__, enum
### `substrate/workstation/loop_engine.py`
- Lines: 284. Doc: Loop completion engine — end-state verification and progress reporting.
- Classes: LoopStatus, LoopContract, VerifyResult, LoopProgressReport, EndStateVerifier
- Functions: advance_loop, create_loop_report
- Imports: __future__, dataclasses, datetime, enum, logging, typing, uuid
### `substrate/workstation/meta_ide_context_runtime.py`
- Lines: 273. Doc: Meta IDE Context Runtime — read-only context binding for the build surface.
- Classes: MetaIdeContextSnapshot, MetaIdeContextRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/workstation/meta_ide_projection_loop_runtime.py`
- Lines: 343. Doc: Meta IDE Projection Build Loop Runtime — governed build from inside cockpit.
- Classes: BuildLoopPhase, BuildRequest, BuildLoopStatus, MetaIDEProjectionLoopRuntime
- Functions: _detect_projection
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/workstation/mode_commands.py`
- Lines: 115. Doc: Mode switching via natural typed commands.
- Classes: ModeCommandResult
- Functions: parse_mode_command
- Imports: __future__, dataclasses, re, substrate.workstation.continuity, substrate.workstation.lifecycle_modes, substrate.workstation.profile_modes, typing
### `substrate/workstation/mode_resolver.py`
- Lines: 204. Doc: Workstation mode resolver — authoritative composite of all mode systems.
- Classes: -
- Functions: resolve_composite_mode, _read_operator_day_mode, _read_operational_mode, _read_station_presence_mode, _read_operator_mode, _read_continuity_state, _read_profile_modes, _derive_lifecycle_mode, _derive_risk_ceiling, _derive_posture
- Imports: __future__, json, logging, os, typing
### `substrate/workstation/mvp_readiness_runtime.py`
- Lines: 444. Doc: MVP Readiness Runtime — objective MVP readiness scoring across 14 dimensions.
- Classes: MVPDimensionStatus, MVPDimension, MVPEscapePoint, MVPReadinessReport, MVPReadinessRuntime
- Functions: _status_from_score, _safe_call, _safe_dict, _safe_float
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/operating_loop_runtime.py`
- Lines: 301. Doc: Operating Loop Runtime — visibility layer over existing execution systems.
- Classes: OperatingLoopStage, OperatingLoopTransition, OperatingLoop, OperatingLoopSnapshot, OperatingLoopRuntime
- Functions: _safe_call
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/workstation/orchestrator_presence_runtime.py`
- Lines: 396. Doc: Orchestrator Presence Runtime — persistent presence layer for the primary orchestrator.
- Classes: PresenceMode, OrchestratorPresenceSnapshot, OrchestratorPresenceRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/overnight_queue.py`
- Lines: 197. Doc: Overnight safe-work queue scaffold — thin MVP for queuing permitted work.
- Classes: OvernightWorkItem, OvernightQueue
- Functions: -
- Imports: __future__, dataclasses, datetime, json, logging, os, pathlib, typing
### `substrate/workstation/profile_behavior.py`
- Lines: 225. Doc: Profile behavior configs — per-profile policies for voice, camera, notifications, apps.
- Classes: VoiceBehavior, NotificationPolicy, CameraPolicy, ExecutionMode, ReportingCadence, ProfileBehavior
- Functions: get_behavior, get_notification_policy_for_lifecycle, resolve_effective_notification_policy
- Imports: __future__, dataclasses, enum, typing
### `substrate/workstation/profile_modes.py`
- Lines: 36. Doc: Profile/work modes — operator activity context governing workspace/tool/task selection.
- Classes: ProfileMode
- Functions: -
- Imports: __future__, enum
### `substrate/workstation/resume_brief.py`
- Lines: 289. Doc: Return/resume brief generator — answers "what happened while I was gone?"
- Classes: ReturnBrief, ReturnBriefGenerator
- Functions: -
- Imports: __future__, dataclasses, datetime, json, logging, os, pathlib, typing
### `substrate/workstation/screen_awareness_runtime.py`
- Lines: 283. Doc: Screen Awareness Runtime — Campaign 21.0.
- Classes: ScreenAwarenessHealth, DeviceScreenBinding, ScreenAwarenessSnapshot, ScreenAwarenessRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/security_mode.py`
- Lines: 219. Doc: Security Harden mode — governed security posture for the cockpit.
- Classes: SecurityEvent, SecurityModeState, SecurityModeManager
- Functions: get_security_manager
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/workstation/session_machine_runtime.py`
- Lines: 331. Doc: Session Machine Runtime — Campaign 19.2.
- Classes: MachineSessionBinding, SessionMachineSnapshot, SessionMachineRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/workstation/state.py`
- Lines: 222. Doc: Workstation state — profile, session, and resume state.
- Classes: WorkstationProfile, WorkstationSessionState, ResumeState, WorkstationSnapshot, WorkstationStateManager
- Functions: -
- Imports: __future__, dataclasses, datetime, json, os, pathlib, typing
### `substrate/workstation/tracker_stack.py`
- Lines: 244. Doc: Tracker stack — independent, stackable vision trackers.
- Classes: TrackerConfig, TrackerStack, TrackerStackManager
- Functions: get_tracker_manager
- Imports: __future__, dataclasses, logging, time, typing
### `substrate/workstation/trigger_chains.py`
- Lines: 395. Doc: Trigger chain engine — deterministic event→condition→action chains.
- Classes: ChainCondition, ChainAction, ChainGovernance, ChainFireRecord, TriggerChain, TriggerChainManager
- Functions: get_chain_manager
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/workstation/unified_approval_runtime.py`
- Lines: 493. Doc: Unified Approval Runtime — single approval queue across all UMH subsystems.
- Classes: ApprovalSourceType, UnifiedApproval, ApprovalAction, UnifiedApprovalSnapshot, UnifiedApprovalRuntime
- Functions: _compute_urgency, _safe_call, _extract_id, _extract_title, _extract_risk, _extract_waiting_since, _item_to_unified
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/workstation/unified_execution_surface_runtime.py`
- Lines: 454. Doc: Unified Execution Surface Runtime — single view across all execution subsystems.
- Classes: ExecutionStreamType, ExecutionStreamStatus, UnifiedExecutionStream, UnifiedApprovalItem, ExecutionSurfaceSnapshot, UnifiedExecutionSurfaceRuntime
- Functions: _safe_call, _extract_id, _extract_str, _extract_float
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/workstation/unified_workstation_runtime.py`
- Lines: 337. Doc: Unified Workstation Runtime — Campaign 18.0.
- Classes: UnifiedWorkstationState, UnifiedWorkstationSnapshot, UnifiedWorkstationRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/vision_presets.py`
- Lines: 328. Doc: Vision Preset Studio — full CRUD for camera presets.
- Classes: PresetZone, VisionPreset, VisionPresetManager
- Functions: get_preset_manager
- Imports: __future__, dataclasses, json, logging, os, time, typing, uuid
### `substrate/workstation/vision_privacy.py`
- Lines: 238. Doc: Vision privacy governance — hard-coded rules for camera usage.
- Classes: CameraMode
- Functions: validate_default_on_activation, validate_camera_activation, validate_frame_storage, validate_analysis_request, validate_tracking_activation, validate_watch_activation, validate_follow_activation, validate_visual_claim, validate_operator_enrollment, validate_gesture_control, validate_trigger_chain_action, get_active_mode
- Imports: __future__, enum, logging
### `substrate/workstation/vision_query.py`
- Lines: 270. Doc: Vision query handler — grounded visual question answering.
- Classes: -
- Functions: handle_visual_query, _analyze_with_vlm, _extract_objects_from_vlm, _infer_watch_condition
- Imports: __future__, base64, logging, time, typing
### `substrate/workstation/vision_scene.py`
- Lines: 530. Doc: Vision scene model — grounded workspace state from camera frames.
- Classes: DetectedObject, WatchItem, FollowState, VisionScene, VisionSceneManager
- Functions: get_scene_manager
- Imports: __future__, dataclasses, logging, time, typing, uuid
### `substrate/workstation/visual_context_runtime.py`
- Lines: 393. Doc: Visual Context Runtime — Campaign 21.2.
- Classes: ContextBindingDepth, ContextBinding, VisualContextSnapshot, VisualContextRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/visual_operations_runtime.py`
- Lines: 365. Doc: Visual Operations Runtime — Campaign 21.4 (composition root).
- Classes: VisualOperationsHealth, VisualCapabilityStatus, VisualOperationsSnapshot, VisualOperationsRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/voice_ingress_runtime.py`
- Lines: 353. Doc: Voice Ingress Runtime — Campaign 20.0.
- Classes: VoiceSourceType, ActivationMode, VoiceChannelContext, VoicePermissionScope, VoiceIngressEvent, VoiceIngressSnapshot, VoiceIngressRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, re, time, typing
### `substrate/workstation/voice_operations_runtime.py`
- Lines: 463. Doc: Voice Operations Runtime — Campaign 20.4 (composition root).
- Classes: VoiceOperationsHealth, VoiceCapabilityStatus, VoiceOperationsSnapshot, VoiceOperationsRuntime
- Functions: _is_action_intent
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/voice_output_runtime.py`
- Lines: 266. Doc: Voice Output Runtime — Campaign 20.3.
- Classes: VoiceOutputTarget, OutputRoutingDecision, VoiceOutputSnapshot, VoiceOutputRuntime
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing
### `substrate/workstation/voice_route_resolver.py`
- Lines: 280. Doc: Voice route resolver — separates execution target from audio output device.
- Classes: VoiceRoute
- Functions: parse_target_node, parse_audio_override, resolve_voice_route
- Imports: __future__, dataclasses, logging, re
### `substrate/workstation/voice_session_manager.py`
- Lines: 368. Doc: Voice Session Manager — Campaign 20.1.
- Classes: VoiceSessionType, VoiceSessionPriority, ManagedVoiceSession, SessionConflictResolution, VoiceSessionManagerSnapshot, VoiceSessionManager
- Functions: -
- Imports: __future__, dataclasses, enum, logging, time, typing, uuid
### `substrate/workstation/vps_control_catalog.py`
- Lines: 649. Doc: VPS control catalog — governed command execution on the VPS node.
- Classes: VpsRisk, CatalogEntry, VpsCommandResult
- Functions: is_vps_command, resolve_vps_action, _is_blocked_pattern, check_blocked, execute_catalog_action, _execute_shell_command, _execute_docker_command, _docker_socket_connect, _strip_docker_log_prefix, _execute_provider_health, _execute_voice_health
- Imports: __future__, dataclasses, datetime, enum, logging, os, typing
### `substrate/workstation/work_lane.py`
- Lines: 515. Doc: Work lane model — multi-session lane routing and foreground guard.
- Classes: LaneType, IsolationLevel, TransportType, WorkLane, ForegroundCheckResult, ForegroundGuard, TransportCheckResult
- Functions: route_to_lane, lane_hud_metadata, check_transport_allowed, get_lane_inventory, build_worker_chrome_launch_cmd
- Imports: __future__, dataclasses, datetime, enum, logging, typing, uuid
### `substrate/workstation/workstation_presence_runtime.py`
- Lines: 290. Doc: Workstation Presence Runtime — operator footprint across the workstation.
- Classes: WorkstationPresenceSnapshot, WorkstationPresenceRuntime
- Functions: -
- Imports: __future__, dataclasses, logging, time, typing
### `tests/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `tests/adapters/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `tests/adapters/broadcast/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `tests/adapters/broadcast/test_filtergraph.py`
- Lines: 253. Doc: Unit tests for multi-source filtergraph builder + scene switch commands.
- Classes: TestOverlayFilterName, TestBuildFiltergraph, TestBuildSceneSwitchCommands, TestIdValidation, TestCompositeConfig
- Functions: _make_config
- Imports: __future__, adapters.broadcast.filtergraph, adapters.broadcast.scene_model, os, pytest, sys
### `tests/adapters/broadcast/test_node_dispatch.py`
- Lines: 201. Doc: Unit tests for Phase 0 — organism engine placement.
- Classes: TestBroadcastAdapter, TestRoutingLayer, TestDaemonAsyncDispatch, TestNodeListShape
- Functions: _load_routes
- Imports: __future__, asyncio, os, pytest, sys, unittest.mock
### `tests/adapters/broadcast/test_process_lifecycle.py`
- Lines: 143. Doc: Tests for ProcessLifecycle fixes: stale exit, SIGKILL timeout, lock, cancel race.
- Classes: -
- Functions: sleep_cmd, short_cmd, test_stale_exit_callback_unbound_on_stop, test_stale_exit_no_corruption_on_restart, test_sigkill_wait_has_timeout, test_concurrent_start_stop_serialized, test_monitor_cancel_race_safe, test_lock_exists, test_rapid_start_stop_start
- Imports: __future__, adapters.broadcast.process_lifecycle, asyncio, os, pytest, sys
### `tests/conftest.py`
- Lines: 13. Doc: -
- Classes: -
- Functions: pytest_ignore_collect
- Imports: substrate.execution.bridge
### `tests/phase13_2_runtime_proofs.py`
- Lines: 632. Doc: Phase 13.2 runtime surface proofs — lifecycle, stop/cancel, policy blocks.
- Classes: -
- Functions: proof, setup_temp_persistence, proof_create_session, proof_start_session, proof_events_persisted, proof_validation_results, proof_overview, proof_stdout_events, proof_sandbox_allocation, proof_stop_session, proof_stop_terminated, proof_cleanup
- Imports: __future__, json, os, sys, tempfile, time
### `tests/substrate/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `tests/substrate/test_entity_store.py`
- Lines: 320. Doc: Tests for substrate.state.stores.entity_store — entity persistence layer.
- Classes: TestEnsureTables, TestEntityStoreInit, TestSaveUser, TestGetUser, TestListUsers, TestSaveCompany, TestListCompanies, TestSaveDepartment
- Functions: reset_tables_flag, mock_conn
- Imports: os, pytest, substrate.state.stores.entity_store, sys, unittest.mock
### `tests/substrate/test_feedback_loop.py`
- Lines: 387. Doc: Tests for substrate.execution.feedback_loop — RLHF feedback ingestion + learning cycle.
- Classes: TestRating, TestOutcomeCategory, TestFeedbackEntry, TestRecordFeedback, TestGetFeedbackStats, TestSkillEffectiveness, TestRecommendRoutingAdjustment, TestSingleton
- Functions: -
- Imports: datetime, substrate.execution.feedback_loop, sys, types, unittest.mock
### `tests/substrate/test_types.py`
- Lines: 209. Doc: -
- Classes: TestSignalEnvelope, TestGovernanceVerdict, TestExecutionResult, TestTraceRecord, TestEnumCounts, TestMemoryQuery, TestFeedbackRecord
- Functions: -
- Imports: pydantic, pytest, substrate.types, sys, uuid
### `tests/test_actuator_bridge.py`
- Lines: 120. Doc: Tests for Layer 3 Phase 2 Slice D: ActuatorMaturityLevel ↔ AdapterMaturityLevel bridge.
- Classes: TestActuatorToAdapterMapping, TestAdapterToActuatorTarget, TestMappingDictCompleteness, TestSemanticCorrespondence
- Functions: -
- Imports: adapters.adapter_engine.adapter_manifest, adapters.adapter_engine.adapter_maturity, os, substrate.execution.actuation.actuator_maturity_v1, sys, unittest
### `tests/test_agent_executor.py`
- Lines: 727. Doc: Tests for AgentExecutor — Phase 17A.
- Classes: -
- Functions: _make_request, _make_executor, test_classify_always_high, test_classify_mutating_is_high, test_classify_high_risk, test_validate_repo_root_rejected, test_validate_subdir_of_approved, test_validate_unapproved_path, test_validate_nonexistent_path, test_validate_secrets_path_rejected, test_parse_agent_output_structured, test_parse_agent_output_no_result_block
- Imports: __future__, dataclasses, pytest, substrate.organism.executor_runtime, substrate.organism.executors.agent_executor, sys, time, typing
### `tests/test_agent_fleet_runtime.py`
- Lines: 520. Doc: Tests for W3 — Agent Fleet Runtime.
- Classes: MockAgentType, MockAgentRegistry, MockCapabilityProfile, MockCapabilityModel, MockRoutingDecision, MockComputeFabric, TestAssignmentScoring, TestRiskGate
- Functions: _make_fleet
- Imports: __future__, dataclasses, pytest, substrate.organism.agent_fleet_runtime, sys, time, typing
### `tests/test_agent_workforce_runtime.py`
- Lines: 278. Doc: Tests for AgentWorkforceRuntime — Campaign 19.1.
- Classes: MockAgentType, MockDispatch, MockDelegationSnap, TestHealthDerivation, TestSnapshot, TestPublicAPI, TestGracefulDegradation, TestTypeRegistration
- Functions: _empty_registry, _empty_fleet, _empty_delegation, _empty_coord, _make_runtime, _make_empty_runtime
- Imports: __future__, dataclasses, pytest, substrate.workstation.agent_workforce_runtime, sys, time, typing, unittest.mock
### `tests/test_approval_intercepts.py`
- Lines: 806. Doc: Phase 15C: Approval Intercepts — comprehensive test suite.
- Classes: TestRequestCreation, TestStoreOperations, TestServiceLayer, TestRiskClassification, TestStateTransitions, TestTimeoutHandling, TestPauseResume, TestProofIntegration
- Functions: store, service, pending_intercept
- Imports: __future__, os, pytest, substrate.organism.executors.approval_intercept, sys, threading, time
### `tests/test_artifact_registry.py`
- Lines: 364. Doc: Tests for Campaign 6.0 — Artifact Registry.
- Classes: TestArtifactTypes, TestArtifactEntry, TestRegistryCRUD, TestRegistryFilters, TestRegistrySummary, TestPersistence, TestRealityGraphIngestion, TestIdGeneration
- Functions: tmp_store, registry, _make_entry
- Imports: __future__, json, os, pytest, substrate.organism.artifact_registry, substrate.organism.reality_graph, sys, tempfile
### `tests/test_assumption_tracking_runtime.py`
- Lines: 266. Doc: Tests for Campaign 9.2 — Assumption Tracking Runtime.
- Classes: TestAssumptionStatus, TestAssumptionRecord, TestAssumptionTrackingRuntime
- Functions: -
- Imports: __future__, os, pytest, substrate.organism.assumption_tracking_runtime, sys, time
### `tests/test_attention_aggregation_runtime.py`
- Lines: 238. Doc: Tests for AttentionAggregationRuntime — Campaign 18.2.
- Classes: _Snapshot, _FakeItem, _FakeAttentionEngine, _FakeOrganismState, _FakeGovernedExecution, _FakeOrganismPortfolio, TestAttentionQueueSnapshot, TestCollection
- Functions: _runtime
- Imports: __future__, substrate.workstation.attention_aggregation_runtime, sys, time
### `tests/test_authority_tier.py`
- Lines: 292. Doc: Tests for authority tier propagation through the ingestion pipeline.
- Classes: TestSourceDeclaresTier, TestTierValidation, TestTierFlowsToObservation, TestTierFlowsToProjection, TestTierPersistsInMemoryEntry, TestLegacyEntriesDefaultToT5
- Functions: _mock_call_with_fallback, fixture_file, memory_store
- Imports: adapters.data_source_adapters.gws_source, adapters.data_source_adapters.local_file_source, json, os, pathlib, pytest, substrate.governance.policy.authority_tier, substrate.understanding.domains.business
### `tests/test_browser_wiring.py`
- Lines: 98. Doc: Tests for browser control wiring to department agents.
- Classes: TestBrowserTierMapping, TestBrowserSkillRegistration, TestBrowserSkillExecution, TestDraftAgentBrowserGate
- Functions: -
- Imports: os, projections.eos.agents.base, substrate.types, sys
### `tests/test_c16_integration.py`
- Lines: 366. Doc: Integration tests for Campaign 16 — Governed Execution Loop.
- Classes: _FakeReadiness, _FakeApprovals, _FakeDelegation, _FakeAllocation, _FakeTradeoff, _FakePortfolio, _FakeBrief, TestPipelineComposition
- Functions: _ger
- Imports: __future__, substrate.organism.execution_lifecycle_runtime, substrate.organism.governed_execution_runtime, substrate.organism.organism_state_runtime, sys, typing, unittest.mock
### `tests/test_c18_integration.py`
- Lines: 209. Doc: Integration tests for Campaign 18 — Jarvis Experience Validation (C18.5).
- Classes: _Snap, _FakeItem, _FakeOrchestrator, _FakeWorkstation, _FakeOrgState, _FakeExec, _FakePortfolio, _FakeApprovals
- Functions: -
- Imports: __future__, substrate.workstation.attention_aggregation_runtime, substrate.workstation.unified_workstation_runtime, sys, time
### `tests/test_c19_integration.py`
- Lines: 366. Doc: Integration tests for Campaign 19 — Execution Fabric & Agent Operations.
- Classes: MockComputeNode, MockPlan, MockAgentType, MockDispatch, MockDevice, MockSession, MockGovSnapshot, TestSnapshotRoundTrip
- Functions: _shared_coord
- Imports: __future__, dataclasses, pytest, substrate.workstation.agent_workforce_runtime, substrate.workstation.execution_fabric_runtime, substrate.workstation.session_machine_runtime, sys, typing
### `tests/test_c20_0_voice_ingress.py`
- Lines: 352. Doc: Tests for Campaign 20.0 — Voice Ingress Runtime.
- Classes: TestVoiceSourceType, TestActivationMode, TestVoiceChannelContext, TestVoicePermissionScope, TestVoiceIngressEvent, TestVoiceIngressSnapshot, TestVoiceIngressRuntime
- Functions: -
- Imports: __future__, substrate.workstation.voice_ingress_runtime, sys, time, unittest
### `tests/test_c20_1_voice_session_manager.py`
- Lines: 376. Doc: Tests for Campaign 20.1 — Voice Session Manager.
- Classes: TestVoiceSessionType, TestVoiceSessionPriority, TestManagedVoiceSession, TestSessionConflictResolution, TestVoiceSessionManagerSnapshot, TestVoiceSessionManagerStartSession, TestVoiceSessionManagerEndSession, TestVoiceSessionManagerActiveSessions
- Functions: -
- Imports: __future__, substrate.workstation.voice_ingress_runtime, substrate.workstation.voice_session_manager, sys, time, unittest
### `tests/test_c20_2_ambient_wake.py`
- Lines: 237. Doc: Tests for Campaign 20.2 — Ambient Wake Runtime.
- Classes: TestAmbientStateEnum, TestWakeTransition, TestAmbientWakeSnapshot, TestAmbientWakeRuntime
- Functions: -
- Imports: substrate.workstation.ambient_wake_runtime, sys, time, unittest
### `tests/test_c20_3_voice_output.py`
- Lines: 184. Doc: Tests for Campaign 20.3 — Voice Output Runtime.
- Classes: TestVoiceOutputTargetEnum, TestOutputRoutingDecision, TestVoiceOutputSnapshot, TestVoiceOutputRuntime
- Functions: -
- Imports: substrate.workstation.voice_output_runtime, sys, unittest
### `tests/test_c20_4_voice_operations.py`
- Lines: 462. Doc: Tests for Campaign 20.4 — Voice Operations Runtime.
- Classes: MockIngressEvent, MockIngressRuntime, MockManagedSession, MockSessionManager, MockAmbientWake, MockOutputDecision, MockOutputRuntime, MockQueryResolution
- Functions: -
- Imports: substrate.workstation.voice_operations_runtime, sys, time, unittest
### `tests/test_c20_integration.py`
- Lines: 435. Doc: Integration tests for Campaign 20 — Voice Operations & Ambient Jarvis.
- Classes: TestC20Imports, TestFullPipeline, TestConcurrentSessions, TestWakeWordStateMachine, TestConflictResolution, TestOutputRoutingAccuracy, TestGracefulDegradation, TestCrossRuntimeComposition
- Functions: -
- Imports: sys, time, unittest
### `tests/test_c21_0_screen_awareness_runtime.py`
- Lines: 254. Doc: Tests for ScreenAwarenessRuntime — Campaign 21.0.
- Classes: MockScreenSnapshot, MockEngine, MockWorkspaceSnapshot, MockWorkspaceAwareness, MockPresenceSnapshot, MockPresence, TestTypes, TestNoDeps
- Functions: -
- Imports: __future__, dataclasses, os, substrate.workstation.screen_awareness_runtime, sys, time, typing, unittest
### `tests/test_c21_1_environment_awareness.py`
- Lines: 237. Doc: Tests for EnvironmentAwarenessRuntime — Campaign 21.1.
- Classes: MockPresenceRuntime, MockSessionMachineRuntime, MockScreenAwarenessRuntime, TestTypes, TestNoDeps, TestWithMocks, TestSurfaceMapping, TestPrimarySurface
- Functions: -
- Imports: __future__, os, substrate.workstation.environment_awareness_runtime, sys, unittest
### `tests/test_c21_2_visual_context.py`
- Lines: 301. Doc: Tests for C21.2 — Visual Context Runtime.
- Classes: _MockIdeContext, _MockScreenAwareness, _MockWorkspace, TestTypes, TestNoDeps, TestWaterfallResolution, TestContinueWork, TestSnapshot
- Functions: -
- Imports: __future__, os, substrate.workstation.visual_context_runtime, sys, unittest
### `tests/test_c21_3_attention_vision.py`
- Lines: 361. Doc: Tests for AttentionVisionRuntime — Campaign 21.3.
- Classes: MockScreenAwareness, MockQueueSnapshot, MockAttentionAggregation, MockEnvironmentAwareness, TestTypes, TestNoDeps, TestErrorDetection, TestCriticalFiltering
- Functions: -
- Imports: __future__, dataclasses, os, substrate.workstation.attention_vision_runtime, sys, typing, unittest
### `tests/test_c21_4_visual_operations.py`
- Lines: 451. Doc: Tests for VisualOperationsRuntime — Campaign 21.4.
- Classes: _NoRuntime, _NoRuntimeHealth, _MockScreenSnapshot, _MockScreenHealth, MockScreenAwareness, _MockEnvSnapshot, _MockObservedSurface, MockEnvironment
- Functions: -
- Imports: __future__, dataclasses, os, sys, time, typing, unittest
### `tests/test_c21_integration.py`
- Lines: 323. Doc: Integration tests for Campaign 21 — Visual Awareness.
- Classes: _Health, _ScreenSnap, MockScreen, _Surface, _EnvSnap, MockEnv, _Binding, MockContext
- Functions: -
- Imports: __future__, dataclasses, os, sys, time, typing, unittest
### `tests/test_c22_acceptance.py`
- Lines: 493. Doc: Acceptance tests for Campaign 22 — Software Production Organism.
- Classes: TestAT1FullProductionLoop, TestAT2TargetAgnostic, TestAT3CapabilityReuse, _FakePacket, _FakeWPEngine, TestAT4OrganizationalLineage, TestAT5MultiProjectConcurrent, TestAT6VoiceToProductionQueue
- Functions: -
- Imports: __future__, dataclasses, sys, time, typing, unittest
### `tests/test_c22_capability_compounding.py`
- Lines: 631. Doc: Tests for CapabilityCompoundingRuntime — Campaign 22.4
- Classes: FakePatternSnapshot, FakeLessonSnapshot, FakeDetectedPattern, FakeLesson, FakeTrajectory, FakePromotionCandidate, FakeOutcomePatternEngine, FakeLearningExtractionRuntime
- Functions: _make_runtime
- Imports: __future__, dataclasses, substrate.organism.capability_compounding_runtime, sys, time, typing, unittest, unittest.mock
### `tests/test_c22_product_factory.py`
- Lines: 713. Doc: Tests for C22.5 — Product Factory Runtime.
- Classes: FakeIntegrationGap, FakeBuildReadiness, FakeProjectionIntegrationRuntime, FakeProductionPlan, FakeProductionPlanningRuntime, FakeGovernanceHealth, FakeGovernanceRuntime, FakeTradeoffAnalysis
- Functions: -
- Imports: __future__, dataclasses, os, substrate.organism.product_factory_runtime, sys, time, typing, unittest
### `tests/test_c22_production_ops_runtime.py`
- Lines: 684. Doc: Tests for C22.0 — Production Operations Runtime.
- Classes: FakeIDEStatus, FakeMetaIDE, FakeExecutionState, FakeExecutionHealth, FakeAssessment, FakeGovernedExecution, FakeWorkforceHealth, FakeAgentWorkforce
- Functions: -
- Imports: __future__, dataclasses, substrate.organism.production_ops_runtime, sys, time, typing, unittest, unittest.mock
### `tests/test_c22_production_planning.py`
- Lines: 574. Doc: Tests for C22.1 — Production Planning Runtime.
- Classes: FakeWorkPacketEngine, FakeGovernanceRuntime, _Unavailable, FakeTradeoffSnapshot, FakeTradeoffEngine, FakeTrajectoryForecast, FakeTrajectoryRuntime, TestProductionTypes
- Functions: _make_runtime
- Imports: __future__, dataclasses, substrate.organism.production_planning_runtime, sys, time, typing, unittest, unittest.mock
### `tests/test_c22_production_review.py`
- Lines: 691. Doc: Tests for C22.3 — Production Review Runtime.
- Classes: FakeUnifiedApprovalRuntime, FakeGovernanceRuntime, FakeReviewPackageBuilder, FakeTrajectoryRuntime, FakeLearningRuntime, TestReviewVerdict, TestQualityDimension, TestQualityCheck
- Functions: -
- Imports: __future__, dataclasses, os, substrate.organism.production_review_runtime, sys, time, typing, unittest
### `tests/test_c22_production_routes.py`
- Lines: 293. Doc: Tests for C22.7 — Production Surface Routes.
- Classes: FakeProductionOpsRuntime, FakeProductionWorkforceRuntime, FakeProductionReviewRuntime, FakeCapabilityCompoundingRuntime, FakeProductFactoryRuntime, FakeSourceTruthRuntime, FakeQueryParams, FakeRequest
- Functions: _run
- Imports: __future__, asyncio, dataclasses, sys, typing, unittest, unittest.mock
### `tests/test_c22_production_workforce.py`
- Lines: 603. Doc: Tests for Campaign 22.2 — Production Workforce Runtime.
- Classes: FakeFleetAssignment, FakeAgentFleetRuntime, FakeAgentWorkforceRuntime, FakePlan, FakeExecutionCoordinator, FakeDelegationResult, FakeDelegationReadinessRuntime, TestProductionRoleEnum
- Functions: _make_packets, _make_runtime
- Imports: __future__, dataclasses, substrate.organism.production_workforce_runtime, sys, time, typing, unittest
### `tests/test_c22_source_truth.py`
- Lines: 714. Doc: Tests for C22.6 — Source Truth Runtime (CORE DELIVERABLE).
- Classes: FakeDecision, FakeDecisionRegistry, FakeWorkPacket, FakeWorkPacketEngine, FakeExecutionPlan, FakeExecutionCoordinator, FakeLesson, FakeLearningExtraction
- Functions: _build_runtime, _full_chain_data
- Imports: __future__, dataclasses, substrate.organism.source_truth_runtime, sys, time, typing, unittest
### `tests/test_c23a_benchmarks.py`
- Lines: 588. Doc: Tests for C23A benchmarks 2-7 + projection readiness.
- Classes: TestProductionQuality, TestProductionVelocity, TestCapabilityReuse, TestOperatorCompression, TestProductionOutcomeQuality, TestCompoundingProof, TestProjectionReadiness, TestValidationRoutes
- Functions: -
- Imports: __future__, os, pathlib, sys, tempfile, unittest
### `tests/test_c23a_capability_reuse.py`
- Lines: 171. Doc: Tests for Benchmark 4 — Capability Reuse (Dual-Track).
- Classes: TestReusableCapability, TestTrackRecord, TestCapabilityReuseBenchmark
- Functions: -
- Imports: substrate.organism.benchmarks.capability_reuse, sys
### `tests/test_c23a_capability_validation_runtime.py`
- Lines: 413. Doc: Tests for CapabilityValidationRuntime — C23A Phase 1.
- Classes: TestBenchmarkRun, TestCapabilityFreshness, TestStorage, TestFreshnessStorage, TestCompoundingCurve, TestControlComparison, TestVerdicts, TestReportGeneration
- Functions: tmp_store
- Imports: __future__, json, os, pytest, substrate.organism.capability_validation_runtime, sys, tempfile, time
### `tests/test_c23a_compounding_proof.py`
- Lines: 237. Doc: Tests for Compounding Proof Benchmark — C23A Phase 8.
- Classes: TestBuildMetrics, TestCompoundingCurve, TestCompoundingProofBenchmark
- Functions: benchmark
- Imports: __future__, os, pytest, substrate.organism.benchmarks.compounding_proof, sys
### `tests/test_c23a_operator_compression.py`
- Lines: 198. Doc: Tests for Benchmark 5 — Operator Compression.
- Classes: TestClassifyOperatorMessage, TestOperatorInteraction, TestProductionInteractions, TestComputeMetrics, TestFromInteractions, TestComputeTrend, TestOperatorCompressionBenchmark
- Functions: -
- Imports: substrate.organism.benchmarks.operator_compression, sys
### `tests/test_c23a_production_outcome_quality.py`
- Lines: 218. Doc: Tests for Benchmark 6 — Production Outcome Quality.
- Classes: TestAcceptanceCriterion, TestProductionOutcome, TestTrackMetrics, TestProductionOutcomeQualityBenchmark
- Functions: -
- Imports: substrate.organism.benchmarks.production_outcome_quality, sys
### `tests/test_c23a_production_quality.py`
- Lines: 195. Doc: Tests for Benchmark 2 — Production Quality.
- Classes: TestSeededDefect, TestDefectSeeder, TestDefectDetector, TestProductionQualityBenchmark
- Functions: -
- Imports: pathlib, substrate.organism.benchmarks.production_quality, sys, tempfile
### `tests/test_c23a_production_velocity.py`
- Lines: 173. Doc: Tests for Benchmark 3 — Production Velocity.
- Classes: TestProductionRecord, TestVelocityResult, TestProductionVelocityBenchmark
- Functions: -
- Imports: substrate.organism.benchmarks.production_velocity, sys
### `tests/test_c23a_projection_readiness.py`
- Lines: 183. Doc: Tests for Projection Readiness Benchmark — C23A Phase 9.
- Classes: TestProjectionRequirements, TestProjectionCoverage, TestProjectionReadinessResult, TestFuzzyMatching, TestEvaluate, TestNetNew
- Functions: benchmark
- Imports: __future__, os, pytest, substrate.organism.benchmarks.projection_readiness, sys
### `tests/test_c23a_reality_recovery.py`
- Lines: 195. Doc: Tests for Reality Recovery Benchmark — C23A Phase 2.
- Classes: TestQuestionGeneration, TestScoring, TestResultFormat, TestSubstringMatch, TestIntegration
- Functions: benchmark
- Imports: __future__, os, pytest, substrate.organism.benchmarks.reality_recovery, sys
### `tests/test_c23b_competitive.py`
- Lines: 292. Doc: Tests for Campaign 23B competitive data layer and composite scorer.
- Classes: TestMarketCategory, TestMeasurementType, TestCategoryRegistry, TestTierWeights, TestCompositeDomains, TestCompetitorProfile, TestCategoryScore, TestGapEntry
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.benchmarks.competitive, sys, tempfile
### `tests/test_c23b_composite_scorer.py`
- Lines: 292. Doc: Tests for Campaign 23B composite scorer and routes.
- Classes: TestCompositeScorer, TestCompetitorComposite, TestGapAnalysis, TestUniqueCategories, TestMarketCategoryComparison, TestGenerateMatrix, TestSummary
- Functions: registry
- Imports: __future__, json, pytest, substrate.organism.benchmarks.competitive, substrate.organism.benchmarks.composite_scorer, sys
### `tests/test_c23b_external_adapters.py`
- Lines: 225. Doc: Tests for Campaign 23B external benchmark adapters.
- Classes: TestBenchmarkTask, TestTaskResult, TestExternalBenchmarkResult, TestSWEBenchAdapter, TestTerminalBenchAdapter, TestWebArenaAdapter, TestGAIAAdapter, TestBrowseCompAdapter
- Functions: -
- Imports: __future__, pytest, substrate.organism.benchmarks.external_adapters, sys
### `tests/test_c23b_organism_audits.py`
- Lines: 676. Doc: Tests — Campaign 23B organism audits (Tier 3).
- Classes: TestContextCapacity, TestOperationalAwareness, TestSourceTruth, TestOrganismAwareness, TestEmpireReadiness, TestStructure
- Functions: _full_production
- Imports: __future__, substrate.organism.audits.context_capacity, substrate.organism.audits.empire_readiness, substrate.organism.audits.operational_awareness, substrate.organism.audits.organism_awareness, substrate.organism.audits.source_truth, sys
### `tests/test_c23b_production_benchmarks.py`
- Lines: 368. Doc: Tests for Campaign 23B production benchmarks (B, N, Q, R).
- Classes: TestAutonomousExecution, TestOutcomeAccuracy, TestEfficiency, TestReliability, TestPopulationVariance, TestAllJsonSerializable
- Functions: -
- Imports: __future__, json, pytest, substrate.organism.benchmarks.autonomous_execution, substrate.organism.benchmarks.efficiency, substrate.organism.benchmarks.outcome_accuracy, substrate.organism.benchmarks.reliability, sys
### `tests/test_c23b_strategic_metrics.py`
- Lines: 621. Doc: Campaign 23B — Strategic Metrics test suite.
- Classes: -
- Functions: test_correspondence_domains_constant, test_score_match_exact_case_insensitive, test_score_match_substring, test_score_match_no_match, test_score_match_empty, test_prediction_resolved_score_uses_preset, test_prediction_resolved_score_computes_when_unset, test_prediction_to_dict, _five_predictions_three_domains, test_correspondence_per_domain_accuracy, test_correspondence_overall_accuracy_weighted, test_correspondence_best_worst_domain
- Imports: __future__, pytest, substrate.organism.audits.model_correspondence, substrate.organism.benchmarks.human_amplification, substrate.organism.benchmarks.strategic_compression, sys
### `tests/test_canonical_memory_reconciliation_v1.py`
- Lines: 373. Doc: Tests for canonical memory reconciliation engine.
- Classes: TestMemoryIdentity, TestOverlapScoring, TestConflictDetection, TestReconciliationEngine, TestConflictGovernance, TestReconciliationReplay, TestRuntimeArtifacts
- Functions: real_sources, tmp_store, tmp_engine, doc1_candidates, doc2_candidates
- Imports: __future__, adapters.adapter_engine.gws_scanner_bridge_v1, adapters.adapter_engine.substrate_candidate_gen_v1, adapters.adapter_engine.substrate_decomposer_v1, json, os, pathlib, pytest
### `tests/test_capability_catalog_slice_a.py`
- Lines: 229. Doc: Tests for Layer 3 Phase 3 Slice A — Capability Catalog + TME Orchestrator.
- Classes: TestCatalogEntryConstructs, TestCapabilityCatalogConstructs, TestCatalogEmptyIsValid, TestCatalogToDictRoundtrip, TestManifestVendorDocsUrlField, TestGoogleDriveManifestHasVendorDocsUrl, TestOrchestratorSkipsWhenNoUrl, TestOrchestratorWritesCatalog
- Functions: -
- Imports: __future__, adapters.adapter_engine.adapter_manifest, adapters.adapter_engine.adapter_registry_contracts, adapters.adapter_engine.capability_catalog, adapters.adapter_engine.capability_discovery, adapters.adapter_engine.google_drive_adapter_v1, adapters.adapter_engine.modality, adapters.adapter_engine.participant
### `tests/test_capability_evolution_engine.py`
- Lines: 228. Doc: Tests for CapabilityEvolutionEngine — Campaign 12.2.
- Classes: FakeCapabilityRuntime, FakeCapabilityPortfolio, FakePatternEngine, FakeLearningExtraction, FakeCompounding, TestEvolutionEventType, TestEvolutionEvent, TestCapabilityTrajectory
- Functions: -
- Imports: __future__, pytest, substrate.organism.capability_evolution_engine, sys, time
### `tests/test_capability_extraction_slice_b.py`
- Lines: 342. Doc: Tests for Layer 3 Phase 3 Slice B — LLM capability extraction.
- Classes: TestValidJsonParse, TestInvalidCapabilityIdRejected, TestEvidenceTruncation, TestEmptyArtifactHandling, TestLlmFailureReturnsEmpty, TestFullOrchestratorMocked, TestResearchAgentFailure, TestConfidenceFormula
- Functions: _make_manifest, _load_fixture
- Imports: __future__, adapters.adapter_engine.adapter_manifest, adapters.adapter_engine.capability_catalog, adapters.adapter_engine.capability_discovery, adapters.adapter_engine.modality, adapters.adapter_engine.participant, json, pathlib
### `tests/test_capability_gap_engine.py`
- Lines: 368. Doc: Campaign 10.1 — Capability Gap Engine tests.
- Classes: _MockMaturity, _MockCap, _MockCapabilityRuntime, _MockGoal, _MockGoalRegistry, TestCapabilityGap, TestCapabilityGapSeverity, TestAcceptanceQuestions
- Functions: _make_engine
- Imports: __future__, pytest, substrate.organism.capability_gap_engine, sys
### `tests/test_capability_graph_engine.py`
- Lines: 247. Doc: Campaign 10.0 — Capability Graph Engine tests.
- Classes: _MockCap, _MockCapabilityRuntime, TestCapabilityEdge, TestCapabilityRelationType, TestAddEdge, TestRemoveEdge, TestDependencies, TestCompositionTree
- Functions: _make_engine
- Imports: __future__, json, os, pytest, substrate.organism.capability_graph_engine, sys, tempfile
### `tests/test_capability_intelligence_integration.py`
- Lines: 214. Doc: Campaign 10 — Capability Intelligence integration tests.
- Classes: _Maturity, _Cap, _MockCapRuntime, _Goal, _GoalRegistry, TestFullCapabilityStack, TestExecutiveBriefIntegration, TestStrategicContextIntegration
- Functions: -
- Imports: __future__, pytest, substrate.organism.capability_gap_engine, substrate.organism.capability_graph_engine, substrate.organism.capability_portfolio_runtime, substrate.organism.executive_brief_runtime, substrate.organism.strategic_context_runtime, sys
### `tests/test_capability_portfolio_runtime.py`
- Lines: 274. Doc: Campaign 10.2 — Capability Portfolio Runtime tests.
- Classes: _MockMaturity, _MockCap, _MockCapabilityRuntime, _MockGraphEngine, _MockGap, _MockGapEngine, _MockAgentModel, TestCapabilityPortfolioSnapshot
- Functions: _make_runtime
- Imports: __future__, pytest, substrate.organism.capability_portfolio_runtime, sys
### `tests/test_cockpit_capability_map.py`
- Lines: 256. Doc: Tests for CockpitCapabilityMap — Campaign 3.1.
- Classes: TestRegistryIntegrity, TestCoverageClassification, TestDuplicationDetection, TestMVPGaps, TestSurfaceFiltering, TestSummaryAggregation, TestTypeSerialization
- Functions: -
- Imports: __future__, pytest, substrate.workstation.cockpit_capability_map, sys, time
### `tests/test_cockpit_endpoints.py`
- Lines: 154. Doc: Tests for cockpit API additions: activity stream, governance controls, DEX channel.
- Classes: TestActivityStream, TestGovernanceControls, TestDexChannel
- Functions: -
- Imports: json, pathlib, pytest
### `tests/test_command_center_mvp_runtime.py`
- Lines: 542. Doc: Tests for CommandCenterMVPRuntime — Campaign 3.2.
- Classes: MockSnapshotRuntime, MockAttentionEngine, MockAgentFleet, MockComputeFabric, MockGovernedWork, MockCompoundingEngine, MockMigrationRuntime, MockCapabilityRuntime
- Functions: -
- Imports: __future__, pytest, substrate.workstation.command_center_mvp_runtime, sys
### `tests/test_command_runtime.py`
- Lines: 857. Doc: Tests for Phase 9 — Command Runtime.
- Classes: TestCommandActionType, TestCommandStatus, TestCommandSource, TestCommandEventType, TestCommand, TestCommandEvent, TestCommandContext, TestCommandRoutingDecision
- Functions: -
- Imports: __future__, json, os, sys, tempfile, time, unittest
### `tests/test_compute_fabric_runtime.py`
- Lines: 520. Doc: Tests for W1 — Unified Compute Fabric Runtime.
- Classes: MockDistributedRuntime, TestNodeTypeInference, TestHealthComputation, TestNodeAggregation, TestWorkerTracking, TestHealthSummary, TestCapacity, TestActiveExecutions
- Functions: _make_vps_profile, _make_beast_profile, _make_offline_profile, _make_fabric
- Imports: __future__, pytest, substrate.organism.compute_fabric_runtime, substrate.organism.device_capacity, substrate.organism.device_role_registry, substrate.organism.worker_registry, sys, time
### `tests/test_conference_rooms.py`
- Lines: 1060. Doc: Tests for Conference Rooms — servers, categories, channels, messages, threads,
- Classes: TestServerCRUD, TestCategories, TestChannels, TestMessages, TestThreads, TestForumPosts, TestRoles, TestInvites
- Functions: clean_data
- Imports: __future__, fastapi, json, os, pathlib, pytest, shutil, sys
### `tests/test_context_assembler.py`
- Lines: 113. Doc: Tests for ConcreteContextAssembler.
- Classes: TestContextAssembler
- Functions: _make_signal, _make_identity
- Imports: __future__, pytest, substrate.control_plane.context, substrate.types
### `tests/test_context_resolution.py`
- Lines: 354. Doc: Tests for Context Resolution Engine — Campaign 5.5.
- Classes: TestCandidateExtraction, TestResolveCreatorOS, TestResolveUMH, TestResolveByRepoName, TestNoResolution, TestResolvedContext, TestResolveEntityReference, TestPopulateOrchestratorContext
- Functions: device_registry, workspace_registry, project_registry_path, graph, project_reg, engine
- Imports: __future__, json, os, pytest, substrate.organism.context_resolution, substrate.organism.project_registry, substrate.organism.reality_graph, sys
### `tests/test_context_resolution_v2.py`
- Lines: 671. Doc: Tests for Campaign 6.5 — Context Resolution V2 (Operational Reality).
- Classes: MockFileEntry, MockRepositoryRuntime, MockDocEntry, MockDocumentationRuntime, MockWorkPacket, MockRuntimeAwareness, MockKnowledgeEntry, MockKnowledgeRuntime
- Functions: device_registry, workspace_registry, project_registry_path, seeded_graph, project_reg, rich_runtimes
- Imports: __future__, dataclasses, json, os, pytest, substrate.organism.context_resolution, substrate.organism.project_registry, substrate.organism.reality_graph
### `tests/test_continuity_runtime.py`
- Lines: 818. Doc: Tests for Phase 7: Continuity Runtime.
- Classes: TestAttentionState, TestTimelineEventType, TestChangeCategory, TestBriefSection, TestContinuitySnapshot, TestTimelineEvent, TestResumeReport, TestOperatorBrief
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.continuity_runtime, sys, tempfile, time
### `tests/test_convergence_acceptance.py`
- Lines: 153. Doc: End-to-end acceptance tests for the converged UMH substrate.
- Classes: TestConvergenceAcceptance
- Functions: -
- Imports: os, pathlib, projections, projections.eos, projections.eos.agents, pytest, substrate, substrate.types
### `tests/test_correspondence_ledger.py`
- Lines: 346. Doc: C26D — Correspondence Ledger tests.
- Classes: MockCertification, MockCertificationEngine, MockRegistry, TestCorrespondenceResult, TestCorrespondenceChecker, TestCorrespondenceScheduler, TestJournalEntryTypes, TestRegressionAlert
- Functions: -
- Imports: __future__, dataclasses, datetime, substrate.organism.correspondence_scheduler, substrate.organism.execution_journal, substrate.organism.production_truth_delta, sys
### `tests/test_daemon_e2e.py`
- Lines: 415. Doc: End-to-end integration test — real NodeMeshServer + real NodeClient.
- Classes: -
- Functions: _alloc_port, make_server, make_client, _stop_all, test_connect_hello_heartbeat, test_capability_execution, test_capability_governance_deny, test_signal_emission, test_disconnect_cleanup, test_reconnect, test_metrics_buffered, run_all
- Imports: __future__, asyncio, json, nodes.windows.umh_node.client, nodes.windows.umh_node.config, substrate.execution.executor, substrate.sockets.capability_socket, substrate.sockets.outcome_socket
### `tests/test_decision_impact_engine.py`
- Lines: 392. Doc: Tests for Campaign 9.5 — Decision Impact Engine.
- Classes: MockDecisionRegistry, MockGoalHierarchy, MockGoalChild, MockAssumptionTracking, TestDecisionImpact, TestDecisionImpactEngine
- Functions: -
- Imports: __future__, pytest, substrate.organism.assumption_tracking_runtime, substrate.organism.decision_impact_engine, substrate.organism.decision_registry, sys, time
### `tests/test_decision_lineage_engine.py`
- Lines: 363. Doc: Tests for Campaign 9.1 — Decision Lineage Engine.
- Classes: MockGoal, MockGoalRegistry, MockGoalHierarchy, MockDecisionRegistry, TestLineageNode, TestDecisionLineage, TestDecisionLineageEngine
- Functions: -
- Imports: __future__, pytest, substrate.organism.decision_lineage_engine, substrate.organism.decision_registry, sys, time
### `tests/test_decision_registry.py`
- Lines: 362. Doc: Tests for Campaign 9.0 — Decision Registry.
- Classes: TestDecisionStatus, TestStrategicDecision, TestDecisionRegistry, TestRealityGraphExtension
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.decision_registry, sys, tempfile, time
### `tests/test_decision_validity_engine.py`
- Lines: 531. Doc: Tests for Campaign 9.3 — Decision Validity Engine.
- Classes: MockDecisionRegistry, MockAssumptionTracking, MockAlignmentReport, MockGoalAlignment, MockOutcomeTracking, TestValidityStatus, TestDecisionValidity, TestDecisionValidityEngine
- Functions: -
- Imports: __future__, dataclasses, pytest, substrate.organism.assumption_tracking_runtime, substrate.organism.decision_registry, substrate.organism.decision_validity_engine, sys, time
### `tests/test_decomposer_depth.py`
- Lines: 366. Doc: Tests for decomposer depth upgrade — semantic extraction quality.
- Classes: TestExtractionSchemaShape, TestIdentityStability, TestRelationshipsAreTyped, TestHeuristicFallback, TestValidationRejectsGarbage
- Functions: _make_signal, _make_interp, _make_raw, _mock_call_with_fallback
- Imports: json, os, pathlib, pytest, substrate.understanding.ontology.primitive_decomposition_v1, substrate.understanding.perception.orchestrator, substrate.understanding.perception.source, sys
### `tests/test_delegation_readiness_runtime.py`
- Lines: 417. Doc: Tests for DelegationReadinessRuntime — Campaign 11.1.
- Classes: _MockFleetAssignment, _MockRationale, _MockFleetRuntime, _MockCapProfile, _MockCapModel, _MockCapGap, _MockGapItem, _MockDecisionValidity
- Functions: -
- Imports: os, pytest, substrate.organism.delegation_readiness_runtime, sys
### `tests/test_delegation_runtime.py`
- Lines: 383. Doc: Tests for Campaign 4.7 — Delegation Runtime.
- Classes: TestIntentClassification, TestDelegationProposal, TestProposalLifecycle, TestMissionLifecycle, TestQueueManagement, TestExecutionResolution, TestPersistence, TestExplainUnderstanding
- Functions: runtime, _make_mission
- Imports: __future__, os, pytest, substrate.organism.delegation_runtime, sys, tempfile
### `tests/test_deploy_verification_worker.py`
- Lines: 317. Doc: Tests for C26B — Deploy Verification Worker.
- Classes: TestDeployVerificationTypes, TestDeployVerificationWorker, TestDeployCanonicalTypes
- Functions: make_mock_http
- Imports: __future__, pytest, substrate.organism.deploy_verification_worker, sys
### `tests/test_device_awareness.py`
- Lines: 320. Doc: Tests for Device Awareness Runtime — Campaign 5.3.
- Classes: TestDeviceRecord, TestDetectActiveDevice, TestDeviceCapabilities, TestBestDeviceFor, TestAvailableDevices, TestPopulateContext, TestSnapshot, TestEdgeCases
- Functions: registry_path, runtime
- Imports: __future__, json, os, pytest, substrate.organism.device_awareness, sys
### `tests/test_device_presence.py`
- Lines: 171. Doc: Tests for substrate/workstation/device_presence.py.
- Classes: TestRegisterSession, TestHeartbeat, TestStaleSessionCleanup, TestMultipleSessions, TestDefaultAudioOutput, TestDisconnect
- Functions: make_session
- Imports: __future__, pytest, substrate.workstation.device_presence, sys, time
### `tests/test_discord_hot_path_smoke.py`
- Lines: 119. Doc: Smoke test: Discord → Gateway → CognitiveLoop → ModelRouter → Governance.
- Classes: TestDiscordBotImports, TestGateway, TestCognitiveLoop, TestModelRouter, TestGovernance, TestMemory, TestSubstrate, TestAgentTeams
- Functions: -
- Imports: dotenv, os, pytest, sys
### `tests/test_documentation_awareness.py`
- Lines: 352. Doc: Tests for Campaign 6.2 — Documentation Awareness Runtime.
- Classes: TestDocumentStatus, TestDocumentEntry, TestDocumentationSnapshot, TestIndexing, TestStatusDetection, TestEntityRefs, TestQueries, TestScan
- Functions: runtime, doc_content
- Imports: __future__, os, pytest, substrate.organism.documentation_awareness_runtime, sys, time
### `tests/test_domain_bridge.py`
- Lines: 286. Doc: Tests for ontology-domain bridge — business as first domain projection.
- Classes: TestBridgeProtocol, TestBridgeNoMatch, TestStructuralMapping, TestProjectionBackReference, TestPipelinePersistsBothLayers
- Functions: _mock_call_with_fallback, _make_obs, fixture_file, memory_store
- Imports: adapters.data_source_adapters.local_file_source, json, os, pathlib, pytest, substrate.understanding.domains.business, substrate.understanding.domains.contract, substrate.understanding.ontology.primitive_decomposition_v1
### `tests/test_domain_bridge_life_creator.py`
- Lines: 723. Doc: Tests for life and creator domain bridges.
- Classes: TestLifeBridgeProtocol, TestLifeBridgeMapping, TestLifeBridgeMissions, TestLifeBridgeThreads, TestLifeBridgeRituals, TestLifeBridgeReflections, TestLifeBridgeGamification, TestLifeBridgePlayerProfile
- Functions: _make_obs
- Imports: os, pytest, substrate.understanding.domains.contract, substrate.understanding.domains.creator, substrate.understanding.domains.life, substrate.understanding.domains.registry, substrate.understanding.ontology.primitive_decomposition_v1, sys
### `tests/test_domain_stores_tier3.py`
- Lines: 178. Doc: Structural tests for all 14 Tier 3 domain store classes.
- Classes: -
- Functions: test_entity_link_store_import, test_entity_link_store_signature, test_context_compaction_store_import, test_context_compaction_store_signature, test_agent_registry_store_import, test_agent_registry_store_signature, test_embedding_store_import, test_embedding_store_return_type, test_higgsfield_store_import, test_higgsfield_store_insert_signature, test_email_folder_store_import, test_venture_store_import
- Imports: dotenv, inspect, os, sys
### `tests/test_drift_detection_engine.py`
- Lines: 328. Doc: Campaign 7.4 — Drift Detection Engine tests.
- Classes: _MockTickLoop, _MockDocEntry, _MockDocAwareness, _MockRuntimeAwareness, _MockPrioritizedItem, _MockPriorityEngine, TestUnifiedDriftWarning, TestDriftType
- Functions: _make_engine
- Imports: __future__, pytest, substrate.organism.drift_detection_engine, sys, time
### `tests/test_embodiment_runtime.py`
- Lines: 355. Doc: Tests for W4 — Embodiment Runtime.
- Classes: MockAssignment, MockDispatch, MockAgentFleet, MockIDEPlan, MockMetaIDE, MockCommandRuntime, MockPersona, TestClassification
- Functions: _make_emb
- Imports: __future__, dataclasses, pytest, substrate.organism.embodiment_runtime, sys, typing
### `tests/test_empire_engine.py`
- Lines: 457. Doc: Empire WorkPacket Engine — Phase 3 tests.
- Classes: TestDomainRegistry, TestAgentRegistry, TestEmpireRouter, TestProfileAwareness, TestDecomposition, TestProofStandard, TestRealityModel, TestUrgencyDetection
- Functions: _isolate_data
- Imports: __future__, json, os, pytest, sys
### `tests/test_entity_link_store.py`
- Lines: 32. Doc: Structural tests for EntityLinkStore.
- Classes: -
- Functions: test_entity_link_store_exists, test_insert_link_signature, test_insert_link_return_annotation
- Imports: dotenv, inspect, os, sys
### `tests/test_eos_projection.py`
- Lines: 64. Doc: Tests for EOS projection entry point.
- Classes: TestEOSProjection, TestEOSAgentRegistration
- Functions: -
- Imports: pathlib, pytest, substrate, substrate.types, sys
### `tests/test_execution_authority_engine_v1.py`
- Lines: 659. Doc: Tests for Execution Authority Engine v1.
- Classes: TestReadOnlyAuthority, TestSafeIngestionAuthority, TestGUIExecutionAuthority, TestFinancialDenial, TestCredentialDenial, TestRecursiveAutonomyDenial, TestMissingAuthority, TestProofRequirements
- Functions: _make_engine, _make_request
- Imports: json, os, pathlib, pytest, substrate.governance.policy.execution_authority_engine_v1, sys, tempfile
### `tests/test_execution_coordinator.py`
- Lines: 1024. Doc: Tests for Phase 13: Execution Coordinator Runtime.
- Classes: TestExecutionPlanStatus, TestExecutionTargetType, TestExecutionMode, TestExecutionPriority, TestCoordinatorApprovalState, TestLifecycleEventType, TestCoordinatorExecutionPlan, TestExecutorDefinition
- Functions: -
- Imports: __future__, json, os, shutil, substrate.organism.execution_coordinator, sys, tempfile, time
### `tests/test_execution_fabric_runtime.py`
- Lines: 326. Doc: Tests for ExecutionFabricRuntime — Campaign 19.0.
- Classes: MockComputeNode, MockGovSnapshot, MockPlan, TestStateDrivation, TestSnapshot, TestPublicAPI, TestGracefulDegradation, TestTypeRegistration
- Functions: _empty_compute, _empty_coord, _empty_gov, _empty_portfolio, _empty_sessions, _empty_presence, _make_runtime, _make_empty_runtime
- Imports: __future__, dataclasses, pytest, substrate.workstation.execution_fabric_runtime, sys, time, typing, unittest.mock
### `tests/test_execution_lifecycle_runtime.py`
- Lines: 394. Doc: Tests for Execution Lifecycle Runtime — Campaign 16.2.
- Classes: TestLifecycleStageEnum, TestLifecycleArc, TestExecutionLifecycleSnapshot, _FakeOutcomeTracking, _FakeLearningExtraction, _FakeOutcomePatterns, _FakeCapabilityEvolution, TestExecutionLifecycleNoDeps
- Functions: -
- Imports: __future__, substrate.organism.execution_lifecycle_runtime, sys, unittest.mock
### `tests/test_execution_telemetry.py`
- Lines: 719. Doc: Tests for Execution Telemetry — Phase 15B.
- Classes: TestEventCreation, TestSequenceOrdering, TestSubscribeGet, TestLifecycleEmission, TestCommandEvents, TestFailureAndCancel, TestResilience, TestRedaction
- Functions: reset_singleton, store, emitter
- Imports: __future__, json, os, pytest, substrate.organism.executors.execution_telemetry, sys, threading, time
### `tests/test_executive_brief_runtime.py`
- Lines: 491. Doc: Campaign 7.5 — Executive Brief Runtime tests.
- Classes: _MockStrategicContext, _FakeCtx, _MockPrioritizedItem, _MockPriorityEngine, _MockRisk, _MockRiskEngine, _MockRecommendation, _MockRecommendationEngine
- Functions: _make_runtime
- Imports: __future__, pytest, substrate.organism.executive_brief_runtime, sys, time
### `tests/test_executive_portfolio_runtime.py`
- Lines: 357. Doc: Tests for ExecutivePortfolioRuntime — Campaign 14.2.
- Classes: FakeResourceAllocation, FakeResourceAllocationWithUnallocated, FakeTradeoffEngine, FakeWorkPortfolio, FakePredictionPortfolio, FakePredictionPortfolioWithDrift, FakeLearningPortfolio, FakeDecisionImpact
- Functions: -
- Imports: __future__, pytest, substrate.organism.executive_portfolio_runtime, sys
### `tests/test_executive_routes.py`
- Lines: 106. Doc: Tests for cockpit executive routes — Campaign 14.3.
- Classes: TestRouteImports, TestLazySingletons, TestRuntimeIntegration
- Functions: -
- Imports: __future__, pytest, sys
### `tests/test_executor_runtime.py`
- Lines: 1106. Doc: Tests for Phase 14 — Executor Runtime.
- Classes: TestExecutorLifecycleStatus, TestExecutorType, TestExecutorRequestStatus, TestExecutorEventType, TestExecutorApprovalState, TestExecutorRuntimeContext, TestExecutorRequest, TestExecutorArtifact
- Functions: -
- Imports: __future__, json, os, pytest, shutil, substrate.organism.executor_runtime, sys, tempfile
### `tests/test_feedback_capture.py`
- Lines: 139. Doc: Tests for ConcreteFeedbackCapture.
- Classes: TestFeedbackCapture
- Functions: _make_result, _make_trace
- Imports: __future__, pytest, substrate.execution.feedback, substrate.execution.trace, substrate.types, uuid
### `tests/test_gap_closures.py`
- Lines: 181. Doc: Tests for the 3 final gap closures: companies endpoint, skill allocation, ingestion facade.
- Classes: TestSkillAllocation, TestIngestionFacade, TestCompaniesEndpoint
- Functions: -
- Imports: os, pytest, sys
### `tests/test_gate10_projection_consumption.py`
- Lines: 312. Doc: Tests for Gate 10 — Projection Consumption Layer.
- Classes: TestTypes, TestDriftDetection, TestProjectionPort, TestPersistence, TestLegacyCompat, TestTypeCoherence, TestRoutes
- Functions: -
- Imports: __future__, json, os, sys, tempfile, unittest
### `tests/test_gate3_governed_work_runtime.py`
- Lines: 946. Doc: Gate 3 — Governed Work Runtime — test suite.
- Classes: TestWorkGraph, TestApprovalRuntime, TestProofRuntime, TestWorkRecoveryRuntime, TestGovernedWorkRuntime, TestVoiceActionResolution, TestCockpitWorkCenterRoutes, TestOperatorLoopRuntime
- Functions: -
- Imports: __future__, pytest, sys, time
### `tests/test_gate4_intent_runtime.py`
- Lines: 804. Doc: Tests for Gate 4 — IntentRuntime (Workstation Convergence).
- Classes: TestIntentScope, TestIntentStatus, TestCanonicalIntent, TestIntentConflict, TestJSONLStore, TestCapture, TestRefine, TestSupersede
- Functions: tmp_dir, runtime
- Imports: __future__, json, os, pytest, substrate.operator.intent_runtime, sys, tempfile
### `tests/test_gate4_workstation_convergence.py`
- Lines: 678. Doc: Gate 4 — Workstation Convergence Runtime — Validation Tests.
- Classes: TestIntentRuntimeCapture, TestIntentRuntimeRefine, TestIntentRuntimeSupersede, TestIntentRuntimeRetrieve, TestIntentRuntimeLineage, TestIntentRuntimeConflicts, TestIntentRuntimeAlignment, TestIntentRuntimeLifecycle
- Functions: tmp_dir, intent_runtime
- Imports: __future__, json, os, pytest, shutil, sys, tempfile
### `tests/test_gate5_capability_runtime.py`
- Lines: 582. Doc: Gate 5 — Capability Runtime tests.
- Classes: TestTypes, TestMaturityScoring, TestPatternDetection, TestCapabilityRuntime, TestPersistence, TestTypeCoherence, TestRoutes
- Functions: runtime
- Imports: __future__, json, os, pytest, sys, tempfile
### `tests/test_gate6_operationalization_runtime.py`
- Lines: 479. Doc: Gate 6 — Operationalization Runtime tests.
- Classes: TestTypes, TestInvariantExtraction, TestReuseScoring, TestOperationalizationRuntime, TestPersistence, TestTypeCoherence, TestRoutes
- Functions: runtime
- Imports: __future__, json, os, pytest, sys
### `tests/test_gate7_infrastructure_runtime.py`
- Lines: 343. Doc: Tests for Gate 7 — Infrastructure Runtime.
- Classes: TestTypes, TestClassification, TestInfrastructureRuntime, TestPersistence, TestTypeCoherence, TestRoutes
- Functions: -
- Imports: __future__, json, os, sys, tempfile, unittest
### `tests/test_gate8_execution_graph.py`
- Lines: 528. Doc: Tests for Gate 8 — Execution Graph (lineage validation).
- Classes: TestTypes, TestLineageValidation, TestChainValidation, TestReplay, TestExecutionGraph, TestPersistence, TestTypeCoherence, TestRoutes
- Functions: -
- Imports: __future__, json, os, sys, tempfile, unittest
### `tests/test_gate9_compounding_engine.py`
- Lines: 384. Doc: Tests for Gate 9 — Capability Compounding Engine.
- Classes: TestTypes, TestScoring, TestDetection, TestGovernance, TestReporting, TestPersistence, TestTypeCoherence, TestRoutes
- Functions: -
- Imports: __future__, json, os, sys, tempfile, unittest
### `tests/test_generic_ingestion_orchestrator.py`
- Lines: 176. Doc: Tests for the generic ingestion orchestrator.
- Classes: TestLocalFileSource, TestGenericIngestionOrchestrator
- Functions: temp_memory_store
- Imports: adapters.data_source_adapters.local_file_source, json, os, pathlib, pytest, shutil, substrate.understanding.perception.orchestrator, sys
### `tests/test_goal_alignment_engine.py`
- Lines: 479. Doc: Tests for GoalAlignmentEngine — Campaign 8.4.
- Classes: FakeRealityEntity, FakeRealityGraph, FakeRuntimeSnapshot, FakeRuntimeAwareness, TestAlignmentReportDefaults, TestConstructorDegradation, TestAlignmentScore, TestUnlinkedWork
- Functions: tmp_goals, hierarchy
- Imports: pytest, substrate.organism.goal_alignment_engine, substrate.organism.goal_hierarchy_engine, substrate.organism.strategic_gap_engine, sys, time
### `tests/test_goal_drift_engine.py`
- Lines: 592. Doc: Tests for GoalDriftEngine — Campaign 8.5.
- Classes: FakeOutcomeTracking, FakeAlignmentEngine, FakePlanningEngine, TestGoalDriftTypeEnum, TestGoalDriftWarningDefaults, TestGoalDriftSnapshotDefaults, TestConstructorDegradation, TestEmptyRegistry
- Functions: tmp_goals, hierarchy
- Imports: pytest, substrate.organism.goal_alignment_engine, substrate.organism.goal_drift_engine, substrate.organism.goal_hierarchy_engine, substrate.organism.outcome_tracking_runtime, substrate.organism.strategic_gap_engine, substrate.organism.strategic_planning_engine, sys
### `tests/test_goal_hierarchy_engine.py`
- Lines: 345. Doc: Goal Hierarchy Engine — Campaign 8.1 tests.
- Classes: TestHierarchyNoRegistry, TestRoots, TestLeaves, TestPath, TestAncestors, TestDescendants, TestDepth, TestTree
- Functions: tmp_dir, registry, hierarchy, _add_chain
- Imports: __future__, os, pytest, substrate.organism.goal_hierarchy_engine, substrate.organism.strategic_gap_engine, sys, tempfile
### `tests/test_governance_full.py`
- Lines: 155. Doc: Tests for GovernanceEngine — risk classification and execution authority.
- Classes: TestGovernanceEngine
- Functions: _make_signal, _make_identity, _make_context
- Imports: __future__, pytest, substrate.control_plane.governance, substrate.types, uuid
### `tests/test_governance_routes.py`
- Lines: 91. Doc: Tests for cockpit governance routes — Campaign 15.4.
- Classes: TestRouteImports, TestLazySingletons, TestRuntimeIntegration
- Functions: -
- Imports: __future__, pytest, sys
### `tests/test_governance_runtime.py`
- Lines: 259. Doc: Tests for Governance Runtime — Campaign 15.0.
- Classes: TestEnums, TestAuthorityHierarchy, TestDataclasses, TestGovernanceRuntime, TestCanonicalTypes
- Functions: -
- Imports: __future__, pytest, substrate.organism.governance_runtime, sys
### `tests/test_governed_execution_runtime.py`
- Lines: 348. Doc: Tests for Governed Execution Runtime — Campaign 16.0.
- Classes: TestExecutionStateEnum, TestExecutionBlockerEnum, TestGovernedExecutionHealthEnum, TestExecutionStateAssessment, TestGovernedExecutionSnapshot, TestGovernedExecutionNoDeps, _FakeReadiness, _FakeDelegation
- Functions: -
- Imports: __future__, substrate.organism.governed_execution_runtime, sys, unittest.mock
### `tests/test_grounding_firewall.py`
- Lines: 692. Doc: Tests for Phase 14.14C — Grounding Firewall + Hermes + Vision.
- Classes: TestNoDataNoFabrication, TestFirewallPreventsLLM, TestRealDataGrounded, TestHermesIntegration, TestVisionGrounding, TestResponseFormat, TestProviderMetadata, TestApprovalGrounding
- Functions: -
- Imports: __future__, json, os, pathlib, pytest, sys, unittest.mock
### `tests/test_gws_source.py`
- Lines: 169. Doc: Tests for GWSSource — Google Workspace ingestion source adapter.
- Classes: TestGWSSourceImplementsProtocol, TestGWSSourceWithMockedScanner, TestGWSSourceMetadataShape
- Functions: _make_scanner
- Imports: adapters.data_source_adapters.gws_source, hashlib, os, pytest, substrate.understanding.perception.source, sys, typing, unittest.mock
### `tests/test_gws_to_canonical_ingestion_v1.py`
- Lines: 227. Doc: Tests for GWS-to-canonical-substrate ingestion pipeline.
- Classes: TestBridge, TestDecomposition, TestCandidateGeneration, TestMemoryStore, TestReplay, TestNoFabricatedProof
- Functions: real_source_files, normalized_doc, decomposition, candidates, memory_store
- Imports: __future__, adapters.adapter_engine.gws_scanner_bridge_v1, adapters.adapter_engine.substrate_candidate_gen_v1, adapters.adapter_engine.substrate_decomposer_v1, hashlib, json, os, pathlib
### `tests/test_hermes_adapter_parity.py`
- Lines: 586. Doc: Tests for Phase 14.14E — Hermes Adapter Parity.
- Classes: TestHermesHealth, TestHermesInventory, TestHermesGenerate, TestHermesSessions, TestHermesCapabilities, TestHermesRoleMatrix, TestHermesRouterIntegration, TestHermesDiagnostics
- Functions: _mock_mesh_dispatch_success, _mock_mesh_dispatch_timeout, _mock_beast_connected, _mock_hermes_available, _mock_hermes_shell_version
- Imports: __future__, json, os, pytest, sys, time, unittest.mock
### `tests/test_identity_resolver.py`
- Lines: 92. Doc: Tests for ConcreteIdentityResolver.
- Classes: TestIdentityResolver
- Functions: _make_signal
- Imports: __future__, pytest, substrate.control_plane.identity, substrate.types
### `tests/test_institutional_memory_runtime.py`
- Lines: 262. Doc: Tests for InstitutionalMemoryRuntime — Campaign 15.2.
- Classes: TestKnowledgeStateEnum, TestInstitutionalMemoryHealthEnum, TestMemoryDriftTypeEnum, TestInstitutionalKnowledge, TestInstitutionalMemoryDriftWarning, TestInstitutionalMemorySnapshot, TestNoDeps, TestKnowledgeLifecycle
- Functions: -
- Imports: __future__, pytest, substrate.organism.institutional_memory_runtime, sys
### `tests/test_interpretation_engine_v1.py`
- Lines: 587. Doc: Tests for Interpretation Engine v1 — Phase 96.8W.
- Classes: TestPipelineCompleteness, TestDeterministicReplay, TestDeterministicIdGenerator, TestObservations, TestRelationships, TestPrimitiveDecomposition, TestHypotheses, TestConfidenceEnvelope
- Functions: _make_input, _run_engine
- Imports: json, os, pathlib, substrate.state.transformation_state_ledger, substrate.understanding.interpretation.interpretation_engine_v1, substrate.understanding.ontology.primitive_decomposition_v1, sys, unittest
### `tests/test_knowledge_awareness.py`
- Lines: 311. Doc: Tests for Campaign 6.4 — Knowledge Awareness Runtime.
- Classes: TestKnowledgeType, TestKnowledgeEntry, TestKnowledgeSnapshot, TestExtraction, TestQueries, TestScan, TestIdGeneration
- Functions: runtime, rich_content
- Imports: __future__, os, pytest, substrate.organism.knowledge_awareness_runtime, sys
### `tests/test_knowledge_layers.py`
- Lines: 152. Doc: -
- Classes: TestLayerDefinitions, TestKnowledgeLayerEngine, TestUnifiedContextIntegration
- Functions: -
- Imports: os, substrate.understanding.knowledge.knowledge_layers, sys
### `tests/test_learning_extraction_runtime.py`
- Lines: 224. Doc: Tests for LearningExtractionRuntime — Campaign 12.0.
- Classes: FakeOutcomeLearning, FakeDecisionRegistry, FakeAssumptionTracking, FakeOutcomeTracking, FakeStrategicMemory, TestLessonCategory, TestExtractedLesson, TestLessonExtractionSnapshot
- Functions: -
- Imports: __future__, pytest, substrate.organism.learning_extraction_runtime, sys, time
### `tests/test_learning_portfolio_runtime.py`
- Lines: 256. Doc: Tests for LearningPortfolioRuntime — Campaign 12.3.
- Classes: FakeLessonSnapshot, FakeLearningExtraction, FakePatternSnapshot, FakePatternEngine, FakeEvolutionSnapshot, FakeEvolutionEngine, FakeOutcomeLearning, FakeCompounding
- Functions: -
- Imports: __future__, pytest, substrate.organism.learning_portfolio_runtime, sys, time
### `tests/test_learning_routes.py`
- Lines: 92. Doc: Tests for cockpit learning routes — Campaign 12.4.
- Classes: TestRouteImports, TestLazySingletons, TestRuntimeIntegration
- Functions: -
- Imports: __future__, pytest, sys
### `tests/test_live_runtime_identity_v1.py`
- Lines: 303. Doc: Tests for Phase 96.8AK — Live Runtime Identity and Git Parity.
- Classes: TestStaleRuntimeDetection, TestMetaCommands, TestSubstrateInterceptOrder, TestCommandRegistryParity, TestLogStartup, TestBotWiringIntegrity, TestContainerIdentity
- Functions: -
- Imports: asyncio, hashlib, json, os, pathlib, pytest, sys, unittest.mock
### `tests/test_lyfeos_creatoros_integration.py`
- Lines: 491. Doc: Tests for EOS, LyfeOS, and CreatorOS integration adapters — protocol conformance and signal building.
- Classes: TestEOSProtocols, TestEOSSignals, TestEOSCorrelation, TestEOSConfig, TestLyfeOSProtocols, TestLyfeOSSignals, TestLyfeOSCorrelation, TestLyfeOSConfig
- Functions: -
- Imports: datetime, os, projections.creatoros.integration.correlation, projections.creatoros.integration.handlers, projections.creatoros.integration.manifest, projections.creatoros.integration.signals, projections.creatoros.integration.tables, projections.eos.integration.correlation
### `tests/test_meeting_types.py`
- Lines: 225. Doc: Tests for substrate.execution.bridge.meeting_types.
- Classes: TestMeetingTypeEnum, TestMeetingConfigs, TestGetMeetingConfig, TestGetPreBrief, TestGetPostActions, TestMeetingConfigFrozen
- Functions: -
- Imports: pytest, substrate.execution.bridge.meeting_types
### `tests/test_memory_api_tier2.py`
- Lines: 40. Doc: Tests for Law 5.5 Tier 2 — merge_event_payload() method.
- Classes: -
- Functions: test_merge_event_payload_exists, test_merge_event_payload_signature, test_merge_event_payload_annotations
- Imports: dotenv, inspect, json, os, sys
### `tests/test_memory_system.py`
- Lines: 111. Doc: Tests for ConcreteMemorySystem.
- Classes: TestMemorySystem
- Functions: _make_entry, _make_query
- Imports: __future__, pytest, substrate.control_plane.memory, substrate.types, uuid
### `tests/test_meta_ide_audit.py`
- Lines: 227. Doc: Tests for Meta IDE functional audit.
- Classes: -
- Functions: test_operation_defaults, test_subsystem_compute_status_all_functional, test_subsystem_compute_status_any_broken, test_subsystem_compute_status_partial, test_subsystem_compute_status_mixed_not_tested, test_audit_matrix_record_operation, test_audit_matrix_critical_path_broken, test_audit_matrix_critical_path_ok, test_audit_matrix_summary, test_audit_matrix_markdown, test_audit_matrix_json_roundtrip, test_broken_subsystems
- Imports: __future__, json, os, substrate.organism.self_use.meta_ide_audit, sys, tempfile
### `tests/test_meta_ide_context_runtime.py`
- Lines: 190. Doc: Tests for Campaign 17.1 — MetaIdeContextRuntime.
- Classes: _FakeContextResolution, _FakeWorkspaceAwareness, _FakeDeviceAwareness, _FakeMetaIdeLoop, _FakeOrchestratorAwareness, TestMetaIdeContext, TestActiveFiles, TestResolveIntent
- Functions: _mic
- Imports: __future__, substrate.workstation.meta_ide_context_runtime, sys, typing, unittest.mock
### `tests/test_meta_ide_projection_loop_runtime.py`
- Lines: 326. Doc: Tests for MetaIDEProjectionLoopRuntime — Campaign 3.4.
- Classes: TestProjectionDetection, TestSubmitPipeline, TestPhaseStateMachine, TestStatusAggregation, TestHistoryActive, TestTypeSerialization, TestFullLifecycleValidation
- Functions: -
- Imports: __future__, dataclasses, pytest, substrate.workstation.meta_ide_projection_loop_runtime, sys, typing, unittest.mock
### `tests/test_meta_ide_runtime.py`
- Lines: 367. Doc: Tests for W2 — Meta IDE Runtime.
- Classes: MockFleetAssignment, MockFleetDispatch, MockAgentFleet, MockExecutionGraph, TestWorkspaceSnapshot, TestPlanFromIntent, TestAssignPlan, TestDispatchPlan
- Functions: _make_ide
- Imports: __future__, dataclasses, pytest, substrate.organism.meta_ide_runtime, sys, time, typing
### `tests/test_mvp_readiness_runtime.py`
- Lines: 335. Doc: Tests for MVPReadinessRuntime — Campaign 4.5.
- Classes: TestFullAssessment, TestOrchestratorAwareness, TestScoring, TestStatusThresholds, TestBlockers, TestEscapePoints, TestRecommendations, TestMissingDeps
- Functions: _mock_awareness, _mock_loop, _mock_approval, _mock_coherence, _mock_session, _mock_cap_map, _mock_proj, _build_full_runtime
- Imports: __future__, pytest, substrate.workstation.mvp_readiness_runtime, sys, typing, unittest.mock
### `tests/test_node_mesh.py`
- Lines: 388. Doc: Node mesh integration tests — verifies the full VPS-side stack.
- Classes: -
- Functions: test_signal_socket_unregister, test_capability_socket_unregister, test_outcome_socket_unregister, test_registry_reregistration, test_executor_unregister, test_metrics_buffer, test_node_registry, test_node_registry_stale_detection, test_node_signal_emitter, test_node_capability_handler_descriptors, test_node_outcome_receiver, test_build_node_manifest
- Imports: __future__, datetime, time, uuid
### `tests/test_node_mesh_ws.py`
- Lines: 172. Doc: WebSocket integration test — simulates a node connecting to the mesh server.
- Classes: -
- Functions: run_test
- Imports: __future__, asyncio, json, substrate.execution.executor, substrate.sockets.capability_socket, substrate.sockets.outcome_socket, substrate.sockets.signal_socket, substrate.sockets.view_socket
### `tests/test_notification_engine.py`
- Lines: 218. Doc: Tests for substrate.sockets.notification_engine.
- Classes: -
- Functions: test_engine_starts_with_no_channels, test_register_sync_channel, test_register_async_channel, test_send_success, test_send_fallback_on_failure, test_send_all_fail, test_send_no_handler, test_send_exception_in_handler, test_default_channels_critical, test_default_channels_low, test_history_tracking, test_stats
- Imports: asyncio, os, substrate.sockets.notification_engine, sys
### `tests/test_ontology_enacted.py`
- Lines: 199. Doc: Tests for substrate.ontology — primitives, laws, and domain bridges.
- Classes: TestPrimitiveObservation, TestLaws, TestDomainProjection
- Functions: _make_observation, _make_projection, _make_law
- Imports: __future__, pytest, substrate.ontology.domains.contract, substrate.ontology.laws, substrate.ontology.primitives, substrate.types, uuid
### `tests/test_operating_loop_coherence_runtime.py`
- Lines: 548. Doc: Tests for OperatingLoopCoherenceRuntime — Campaign 4.3.
- Classes: TestCoherentLoop, TestOrphanDetection, TestBrokenChain, TestMissingLineage, TestMissingLearning, TestStaleApprovals, TestContradictions, TestCoherenceScoring
- Functions: _mock_intent_runtime, _mock_governed_work, _mock_loop_runtime, _mock_approval_runtime, _mock_contradiction_engine, _mock_state_coherence, _mock_execution_graph, _mock_learning_loop, _mock_awareness, _make_loop, _full_runtime
- Imports: __future__, pytest, substrate.organism.operating_loop_coherence_runtime, substrate.workstation.operating_loop_runtime, sys, time, typing, unittest.mock
### `tests/test_operating_loop_runtime.py`
- Lines: 354. Doc: Tests for OperatingLoopRuntime — Campaign 4.1.
- Classes: TestTrack, TestTransitions, TestActiveCompleted, TestCorrelate, TestLineage, TestSnapshot, TestErrorHandling, TestNoDeps
- Functions: _mock_graph, _build_runtime
- Imports: __future__, pytest, substrate.workstation.operating_loop_runtime, sys, time, typing, unittest.mock
### `tests/test_operations_routes.py`
- Lines: 106. Doc: Tests for Operations API routes — Campaign 19.3.
- Classes: TestExecutionFabricRoutes, TestAgentWorkforceRoutes, TestSessionMachineRoutes, TestRouterMounting
- Functions: -
- Imports: __future__, pytest, sys, typing, unittest.mock
### `tests/test_operator_loop_mvp.py`
- Lines: 357. Doc: Operator Loop MVP — end-to-end integration test.
- Classes: TestIntentContract, TestApprovalGate, TestSandboxManager, TestExecutionArtifacts, TestValidationCommands, TestAuditTrail, TestOutcomeRecording, TestFullLifecycle
- Functions: _isolate_data
- Imports: __future__, json, os, pytest, sys, tempfile, time
### `tests/test_operator_loop_phase2.py`
- Lines: 310. Doc: Operator Loop Phase 2 — Autonomous Implementation tests.
- Classes: TestPlanGeneration, TestExecutionModes, TestFailureRecovery, TestReviewGate, TestDataclasses, TestValidationCommands, TestRecordRetrieval
- Functions: _isolate_data, _make_packet
- Imports: __future__, json, os, pytest, sys, time
### `tests/test_operator_migration_runtime.py`
- Lines: 319. Doc: Tests for W5 — Operator Migration Runtime.
- Classes: MockCompoundingEngine, MockCapabilityRuntime, TestExitRecording, TestClassification, TestMigrationPriorities, TestFeasibility, TestCoverage, TestOperationalizationBridge
- Functions: _make_mig
- Imports: __future__, dataclasses, pytest, substrate.organism.operator_migration_runtime, sys, time, typing
### `tests/test_orchestrator_awareness_runtime.py`
- Lines: 681. Doc: Tests for OrchestratorAwarenessRuntime — Campaign 4.0.
- Classes: TestContextAssembly, TestDualCapabilityLayer, TestDomainIsolation, TestAwarenessScoring, TestDomainHealth, TestGracefulDegradation, TestSnapshot, TestContextSerialization
- Functions: _mock_intent, _mock_snapshot, _mock_attention, _mock_cap_map, _mock_cmd_center, _mock_exec_surface, _mock_capability_runtime, _mock_capability_router, _mock_ops_runtime, _mock_infra_runtime, _mock_compounding, _mock_continuity
- Imports: __future__, dataclasses, pytest, substrate.organism.orchestrator_awareness_runtime, sys, time, typing, unittest.mock
### `tests/test_orchestrator_presence_runtime.py`
- Lines: 242. Doc: Tests for Campaign 17.0 — OrchestratorPresenceRuntime.
- Classes: _FakeOrchestratorAwareness, _FakeOrganismState, _FakeGovernedExecution, _FakeContextResolution, _FakeWorkspaceAwareness, _FakeDeviceAwareness, _FakeApprovals, _FakeDelegation
- Functions: _opr
- Imports: __future__, substrate.workstation.orchestrator_presence_runtime, sys, time, typing, unittest.mock
### `tests/test_organism_coordination_engine.py`
- Lines: 279. Doc: Tests for Organism Coordination Engine — Campaign 15.1.
- Classes: TestEnums, TestDataclasses, TestHealthScoreMapping, TestOrganismCoordinationEngine
- Functions: -
- Imports: __future__, pytest, substrate.organism.organism_coordination_engine, sys, unittest.mock
### `tests/test_organism_portfolio_runtime.py`
- Lines: 288. Doc: Tests for OrganismPortfolioRuntime — Campaign 15.3.
- Classes: FakeHealthy, FakeDrifting, FakeCritical, TestOrganismHealthEnum, TestOrganismDriftTypeEnum, TestOrganismDriftWarning, TestSubsystemHealthEntry, TestOrganismPortfolioSnapshot
- Functions: -
- Imports: __future__, pytest, substrate.organism.organism_portfolio_runtime, sys
### `tests/test_organism_state_runtime.py`
- Lines: 247. Doc: Tests for Organism State Runtime — Campaign 16.1.
- Classes: TestOrganismModeEnum, TestOrganismStateSnapshot, _FakePortfolio, _FakeExecution, _FakeBrief, TestOrganismStateMinimalDeps, TestOrganismModeClassification, TestOrganismStateSnapshot
- Functions: -
- Imports: __future__, substrate.organism.organism_state_runtime, sys, unittest.mock
### `tests/test_outcome_pattern_engine.py`
- Lines: 247. Doc: Tests for OutcomePatternEngine — Campaign 12.1.
- Classes: FakeLearningExtraction, FakeDecisionLineage, FakeDecisionValidity, FakeDecisionImpact, FakeOutcomeLearning, FakeCompounding, FakeGoalHierarchy, TestPatternType
- Functions: -
- Imports: __future__, pytest, substrate.organism.outcome_pattern_engine, sys, time
### `tests/test_outcome_tracking_runtime.py`
- Lines: 313. Doc: Tests for OutcomeTrackingRuntime — Campaign 8.2.
- Classes: TestOutcomeProgress, TestOutcomeSnapshot, TestConstructor, TestCompletion, TestHealthClassification, TestProgress, TestGoalsAtRisk, TestSnapshot
- Functions: tmp_store, registry, hierarchy, runtime, _goal
- Imports: os, pytest, substrate.organism.goal_hierarchy_engine, substrate.organism.outcome_tracking_runtime, substrate.organism.strategic_gap_engine, sys, time
### `tests/test_outcome_verification.py`
- Lines: 526. Doc: Tests for C26A — Outcome Verification Runtime.
- Classes: TestVerificationTypes, TestVerificationPlanRegistry, TestOutcomeVerificationEngine, TestVerificationIntegrity, TestCanonicalTypeRegistration
- Functions: _pass_result, _fail_result, _make_check_fn, _all_passing_fns
- Imports: __future__, json, os, pytest, substrate.organism.outcome_verification, sys, tempfile
### `tests/test_override_tracking.py`
- Lines: 256. Doc: Tests for override outcome tracking in HomeostasisEngine.
- Classes: TestRecordOverride, TestRecordOverrideOutcome, TestOverrideHistory, TestOverrideStats, TestOverrideCapEnforcement, TestOverrideToDict
- Functions: engine
- Imports: datetime, pytest, substrate.organism.homeostasis
### `tests/test_p0_smoke.py`
- Lines: 178. Doc: P0 smoke tests — fast import/health checks for all production services.
- Classes: TestDiscordBotImports, TestOperatorAPI, TestWebhookService, TestNodeMesh, TestSubstrateCore, TestNoGhostEnvRefs
- Functions: -
- Imports: importlib, os, pathlib, pytest, sys, threading, time, unittest.mock
### `tests/test_permission_tiers.py`
- Lines: 157. Doc: Tests for the 4-tier permission model (Read/Draft/Execute/Commit).
- Classes: TestPermissionTierEnum, TestActionMapping, TestRequiredTier, TestExecutionAuthorityEngineIntegration, TestGovernanceEngineIntegration
- Functions: -
- Imports: __future__, os, pytest, substrate.types, sys
### `tests/test_persist_all_observations.py`
- Lines: 224. Doc: Tests for persist-all-observations — every observation becomes a memory entry.
- Classes: TestPersistAllObservations
- Functions: _mock_call_with_fallback, fixture_file, memory_store
- Imports: adapters.data_source_adapters.local_file_source, json, os, pathlib, pytest, substrate.understanding.perception.orchestrator, sys, unittest.mock
### `tests/test_persistent_loops.py`
- Lines: 346. Doc: Tests for the persistent loop infrastructure.
- Classes: -
- Functions: _counting_stage, _failing_stage, _make_loop, test_loop_initial_state, test_run_once, test_run_once_multiple, test_failing_stage_captures_error, test_unknown_stage_reports_error, test_mixed_stages, test_error_state_after_5_consecutive, test_status_dict, test_cycle_report_to_dict
- Imports: json, os, pytest, substrate.execution.loop.persistent_loop, substrate.execution.loop.stages, sys, time
### `tests/test_phase10_2_sandbox_pr.py`
- Lines: 477. Doc: Phase 10.2 — Operator-Approved Template-Supplied Sandbox PR Creation tests.
- Classes: TestApprovalGateCreation, TestApprovalGateDecisions, TestSandboxOrchestratorGates, TestValidationGate, TestBridgeEndpoints, TestRouteAuth, TestSafetyInvariants
- Functions: tmp_store, approval_gate, sample_packet_kwargs, supply_candidate
- Imports: __future__, json, os, pytest, substrate.organism.approval_gate, substrate.organism.autonomous_cadence, substrate.organism.autonomous_pr_factory, substrate.organism.candidate_supply_engine
### `tests/test_phase10_3_production_truth.py`
- Lines: 273. Doc: Phase 10.3 — Production truth promotion tests.
- Classes: TestProductionTruthDelta, TestProductionMergeVerification, TestProductionOutcomeIdempotency, TestCandidateSupplyResolution, TestTemplateReliabilityUpdate, TestFileDivergence, TestMergeVerifierDiffIsolation
- Functions: -
- Imports: __future__, json, os, pytest, subprocess, substrate.organism.candidate_supply_engine, substrate.organism.production_merge_verifier, substrate.organism.production_truth_delta
### `tests/test_phase10_4_reliability_campaign.py`
- Lines: 528. Doc: Phase 10.4 — Low-risk production truth reliability campaign tests.
- Classes: TestCampaignQueueRanking, TestExtendedSources, TestBatchSelection, TestApprovalPacketCreation, TestDocumentationAlignmentTemplate, TestMultiCandidateProductionVerification, TestReliabilityCalibration, TestPostCampaignCadenceSuppression
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.autonomous_cadence, substrate.organism.candidate_supply_engine, substrate.organism.production_merge_verifier, substrate.organism.production_truth_delta
### `tests/test_phase10_5_reliability_weighted_cadence.py`
- Lines: 713. Doc: Phase 10.5 — Reliability-Weighted Cadence Ranking + Promotion Thresholds.
- Classes: TestReliabilitySignalAggregation, TestTemplateReliabilityExtraction, TestAgentReliabilityExtraction, TestCandidateSourceReliability, TestValidationReliability, TestRollbackReliability, TestProductionTruthReliability, TestWeightedRankingFormula
- Functions: -
- Imports: __future__, json, os, sys, unittest
### `tests/test_phase13_3_context_assimilation.py`
- Lines: 1143. Doc: Phase 13.3 — Context Assimilation + Continuous Reconciliation Kernel tests.
- Classes: TestSourceRegistry, TestIngestionJob, TestContextIngestionEngine, TestContextDiagnostic, TestDiagnosticEngine, TestCanonicalUpdate, TestReconciliationSession, TestReconciliationEngine
- Functions: _temp_path
- Imports: __future__, json, os, pytest, tempfile, time
### `tests/test_phase13_3s_operational_truth.py`
- Lines: 702. Doc: Phase 13.3S — Operational Truth Stabilization tests.
- Classes: TestOperationalTruthSnapshot, TestOperationalIssue, TestStateTypes, TestPersistence, TestExecutionJournal, TestPrecommitGateDetection, TestEventBusHandlerDetection, TestDataHygienePolicy
- Functions: -
- Imports: __future__, json, os, pathlib, pytest, sys, tempfile, time
### `tests/test_phase13_4_operator_e2e_acceptance.py`
- Lines: 656. Doc: Phase 13.4 — Standard Multi-Runtime Operator E2E Acceptance Tests.
- Classes: TestOperatorAcceptanceRunModel, TestOperatorAcceptanceArtifactModel, TestOperatorAcceptanceModeDecision, TestOperatorLoopCoordinator, TestScenarios, TestRuntimeExecution, TestSafetyPolicy, TestAPIRoutes
- Functions: -
- Imports: __future__, json, os, pytest, sys, tempfile, time
### `tests/test_phase14_11a_execution_control.py`
- Lines: 192. Doc: Phase 14.11A — execution control adapter tests.
- Classes: _ConcreteAdapter, TestRuntimeAdapterDefaults, TestClaudeCodeAdapterInheritsDefaults, TestShellAdapterPauseResume, TestEnvironmentAwareness
- Functions: -
- Imports: __future__, substrate.organism.claude_code_runtime_adapter, substrate.organism.runtime_adapter, substrate.organism.shell_runtime_adapter, sys
### `tests/test_phase14_11a_paused_lifecycle.py`
- Lines: 90. Doc: Phase 14.11A — PAUSED lifecycle state transition tests.
- Classes: TestPausedStateExists, TestPausedAllowedTransitions, TestPausedDisallowedTransitions, TestPausedIsNotTerminal, TestAllStatesHaveTransitions
- Functions: -
- Imports: __future__, substrate.organism.work_packet, sys
### `tests/test_phase14_11a_workstation_endpoints.py`
- Lines: 108. Doc: Phase 14.11A — workstation endpoint and mode resolver tests.
- Classes: TestModeResolver, TestPostureDerivation, TestMeshSnapshotReader, TestVpsNodeReader, TestTmuxAdapter, TestRouteFileImport
- Functions: -
- Imports: __future__, sys
### `tests/test_phase14_11b_checkpoint_resume.py`
- Lines: 246. Doc: Phase 14.11B — Checkpoint + resume brief tests.
- Classes: TestContinuityCheckpoint, TestCheckpointManager, TestReturnBrief, TestReturnBriefGenerator, TestRouteEndpoints
- Functions: -
- Imports: __future__, json, os, pytest, substrate.workstation.checkpoint, substrate.workstation.resume_brief, sys, tempfile
### `tests/test_phase14_11b_continuity.py`
- Lines: 210. Doc: Phase 14.11B — Continuity state machine tests.
- Classes: TestContinuityStateEnum, TestTransitionMap, TestContinuityStateMachine, TestContinuityTransition, TestSerialization
- Functions: -
- Imports: __future__, pytest, substrate.workstation.continuity, sys
### `tests/test_phase14_11b_dual_modes.py`
- Lines: 194. Doc: Phase 14.11B — Dual mode taxonomy + resolver tests.
- Classes: TestLifecycleModeEnum, TestProfileModeEnum, TestDualComposition, TestResolverUpgrade, TestDeriveLifecycleMode, TestRiskCeiling
- Functions: -
- Imports: __future__, pytest, substrate.workstation.lifecycle_modes, substrate.workstation.mode_resolver, substrate.workstation.profile_modes, sys
### `tests/test_phase14_11b_mode_switch_overnight.py`
- Lines: 238. Doc: Phase 14.11B — Mode switching + overnight scaffold tests.
- Classes: TestModeCommandParsing, TestOvernightWorkItem, TestOvernightQueue
- Functions: -
- Imports: __future__, pytest, substrate.workstation.mode_commands, substrate.workstation.overnight_queue, sys, tempfile
### `tests/test_phase14_11c_file_browser.py`
- Lines: 219. Doc: Phase 14.11C — File browser safety + functionality tests.
- Classes: TestAllowlist, TestTraversalDenial, TestDeniedPatterns, TestBrowseDirectory, TestReadFile, TestSourceEnvironment, TestLanguageDetection, TestWindowsUnavailable
- Functions: -
- Imports: __future__, os, pytest, substrate.workstation.file_browser, sys, tempfile
### `tests/test_phase14_11c_workspace_endpoints.py`
- Lines: 259. Doc: Phase 14.11C — Workspace endpoint tests.
- Classes: TestGitStatus, TestGitDiff, TestTestResults, TestExecutionLogs, TestProofArtifacts, TestHealthCheck, TestTraceLinkage, TestProofClassification
- Functions: -
- Imports: __future__, json, os, pytest, sys, tempfile
### `tests/test_phase14_11d_activation_signal.py`
- Lines: 211. Doc: Phase 14.11D — ActivationSignal model tests.
- Classes: TestActivationSource, TestActivationCapabilityStatus, TestActivationSignal, TestPresenceCapability, TestGetActivationCapabilities, TestPresenceSession
- Functions: -
- Imports: __future__, pytest, sys
### `tests/test_phase14_11d_jarvis_command.py`
- Lines: 308. Doc: Phase 14.11D — Jarvis command routing + governance tests.
- Classes: TestClassifyIntent, TestResolveNavigationTarget, TestResolveModeTarget, TestGovernanceRequirement, TestJarvisCommandResult
- Functions: -
- Imports: __future__, pytest, sys
### `tests/test_phase14_11d_presence_endpoints.py`
- Lines: 207. Doc: Phase 14.11D — Presence endpoint tests.
- Classes: FakeReq, TestActivateEndpoint, TestCurrentEndpoint, TestCapabilitiesEndpoint, TestCommandEndpoint, TestDetectEnv
- Functions: _run
- Imports: __future__, asyncio, pytest, sys
### `tests/test_phase14_11d_voice_integration.py`
- Lines: 259. Doc: Phase 14.11D — Voice/STT/TTS integration and trace tests.
- Classes: FakeReq, TestVoiceCommandRouting, TestSTTCapability, TestTTSCapability, TestDiscordCommandAlignment, TestTraceResumeIntegration, TestHotkeyActivation, TestManualActivation
- Functions: _run
- Imports: __future__, asyncio, json, os, pytest, sys, tempfile
### `tests/test_phase14_11e_agent_registry.py`
- Lines: 245. Doc: Phase 14.11E — Agent registry and command center route tests.
- Classes: FakeReq, TestAgentRegistry, TestWorkPacketBoard, TestBlockedWork, TestApprovalsView, TestTraces, TestCommandCenterSummary, TestCrossDeviceLabeling
- Functions: _run
- Imports: __future__, asyncio, json, os, pytest, sys, tempfile
### `tests/test_phase14_11e_jarvis_commands.py`
- Lines: 200. Doc: Phase 14.11E — Jarvis command integration tests for agent/task/work-packet commands.
- Classes: FakeReq, TestNewIntentClassification, TestPacketControlActions, TestGovernanceNewIntents, TestPresenceRouteIntegration
- Functions: _run
- Imports: __future__, asyncio, pytest, sys
### `tests/test_phase14_11g_actionability.py`
- Lines: 279. Doc: Phase 14.11G — Integrated workstation actionability tests.
- Classes: FakeReq, TestWorkspacePanelTarget, TestCheckpointSummaryWiring, TestLiveRefresh, TestApproveAction, TestWorkPacketCreate, TestJarvisToWorkPacketE2E, TestGovernanceIntegrity
- Functions: _run
- Imports: __future__, asyncio, json, os, pytest, sys, tempfile
### `tests/test_phase14_15_continuity.py`
- Lines: 614. Doc: Phase 14.15 — Full Continuity Daily Driver tests.
- Classes: TestContinuityStatePersistence, TestStartupSequence, TestShutdownSequence, TestProfileModes, TestLifecycleModes, TestPresence, TestIntentContract, TestLoopEngine
- Functions: -
- Imports: __future__, json, os, pytest, sys, tempfile, uuid
### `tests/test_phase14_3_product_docs_convergence.py`
- Lines: 557. Doc: Phase 14.3 — Google Docs Product Documentation Convergence tests.
- Classes: TestPreflight, TestGoogleDocsAccess, TestDocumentInventory, TestExtractedClaims, TestDocClassification, TestEndStateDesignMap, TestDocsVsSourceReality, TestRequirementsGapReport
- Functions: _load
- Imports: __future__, json, os, pathlib, pytest, sys
### `tests/test_phase14_3a_full_content_convergence.py`
- Lines: 598. Doc: Phase 14.3A — Full Google Docs Product Documentation Convergence tests.
- Classes: TestPreflight, TestGWSAuth, TestInventory, TestDocClassification, TestCanonicalCandidateMap, TestDocsVsSourceReality, TestMVPMaturity, TestConvergenceSequence
- Functions: _load
- Imports: __future__, json, os, pytest, sys
### `tests/test_phase14_4_trinity_alignment.py`
- Lines: 661. Doc: Phase 14.4 — Trinity GitHub/Windows Alignment + Product Design Diff
- Classes: TestPhase143ARPreflight, TestDesiredStateCanons, TestNoCollapsedDocs, TestDeviceRuntimePlacement, TestSourceAccessState, TestCurrentSourceInventories, TestGithubWindowsAlignment, TestFeaturePreservationMatrices
- Functions: load_json, artifact_path, convergence_path
- Imports: __future__, glob, json, os, pytest, subprocess, sys
### `tests/test_phase14_5_convergence_planning.py`
- Lines: 714. Doc: Phase 14.5 — Trinity Convergence Planning / Decision Session
- Classes: TestPhase144RPreflight, TestSourceTruthPacket, TestDecisionLedger, TestEOSSourceStrategyDecision, TestCreatorOSMVPScopeDecision, TestLyfeOSPRDVersionDecision, TestClerkMigrationOrderDecision, TestOSPlatformStandardV2
- Functions: load_json, convergence_path, trinity_path
- Imports: __future__, glob, json, os, pytest, subprocess, sys
### `tests/test_phase14_5a.py`
- Lines: 898. Doc: Phase 14.5A tests — 13-layer production stack + Socratic governance completion.
- Classes: TestPhase145Preflight, TestEOS13Layer, TestCreatorOS13Layer, TestLyfeOS13Layer, TestUMH13Layer, TestOSPlatformStandardV2, TestUMHIntegrationBoundary, TestIntentExtrapolation
- Functions: load
- Imports: __future__, json, os, sys, unittest
### `tests/test_phase14_5r_production_truth.py`
- Lines: 498. Doc: Phase 14.5R — Trinity Convergence + 13-Layer + Socratic Governance Production Truth Promotion tests.
- Classes: TestPreflight, TestReview, TestStackVerification, TestIntegrationBoundary, TestSocraticGovernance, TestReadinessGates, TestWorkPacketTree, TestPolicySafety
- Functions: convergence_path, load
- Imports: glob, json, os, pytest
### `tests/test_phase14_6b_creatoros_lossless_canon.py`
- Lines: 1295. Doc: Comprehensive pytest test suite for CreatorOS Phase 14.6B canon reconstruction.
- Classes: TestArtifactExistence, TestArtifactMetadata, TestArtifactProvenance, TestJSONValidity, TestMarkdownValidity, TestContentQuality, TestNoMutation, TestCrossReferences
- Functions: _json_path, _md_path, _artifact_path, _load_json, _read_md, _all_json_on_disk, _all_md_on_disk
- Imports: __future__, json, os, pathlib, pytest, re
### `tests/test_phase14_6b_eos_lossless_canon.py`
- Lines: 1399. Doc: Comprehensive pytest test suite for EOS Phase 14.6B canon reconstruction.
- Classes: TestArtifactExistence, TestArtifactMetadata, TestArtifactProvenance, TestJSONValidity, TestMarkdownValidity, TestContentQuality, TestNoMutation, TestCrossReferences
- Functions: _json_path, _md_path, _load_json, _load_md, _parse_md_frontmatter, _all_json_slugs_that_exist, _all_md_slugs_that_exist, _all_artifact_filenames, _collect_provenance_from_json, _collect_all_provenance_labels, _all_provenance_in_corpus_content
- Imports: __future__, json, os, pathlib, pytest, subprocess, typing
### `tests/test_phase14_6b_lyfeos_code_resolved_canon.py`
- Lines: 1653. Doc: Phase 14.6B-LyfeOS: Code-Resolved Lossless LyfeOS Product Canon Reconstruction
- Classes: TestArtifactExistence, TestJSONValidity, TestPhaseMetadata, TestProvenanceLabels, TestNavigationCanon, TestNovaNamingCorrection, TestOnboardingCanon, TestTransformationThread
- Functions: _read_artifact, _load_json_artifact, _artifact_exists, _content_contains, _content_contains_any, _json_deep_search
- Imports: json, os, pathlib, re, subprocess, sys, typing
### `tests/test_phase14_6b_umh_code_resolved_canon.py`
- Lines: 1817. Doc: Phase 14.6B-UMH: Code-Resolved Universal Meta Harness Canon Reconstruction
- Classes: TestArtifactExistence, TestPhaseMetadata, TestNamingCanonicalization, TestEcosystemDoctrine, TestBoundaryMatrix, TestCodebaseAnalysis, TestProjectionArtifacts, TestCockpitJarvis
- Functions: -
- Imports: json, os, pathlib, re, sys
### `tests/test_phase14_6c_operator_review.py`
- Lines: 1241. Doc: Comprehensive pytest test suite for Phase 14.6C operator review packet.
- Classes: TestArtifactExistence, TestArtifactMetadata, TestPhaseCompliance, TestMarkdownValidity, TestReviewIndex, TestEcosystemDoctrine, TestBoundaryMatrix, TestRealityModelCorrection
- Functions: _md_path, _load_md, _load_md_lines, _parse_md_frontmatter, _get_frontmatter, _md_has_section, _md_has_text, _count_occurrences, _all_slugs_that_exist, _load_all_contents
- Imports: __future__, os, pathlib, pytest, re, subprocess, typing
### `tests/test_phase14_6d_canon_revision.py`
- Lines: 812. Doc: Comprehensive pytest test suite for Phase 14.6D canon revision.
- Classes: TestArtifactExistence, TestMinimumSize, TestPhaseMarkerUpdated, TestDecisionReferences, TestRealityModelFraming, TestStaleLanguageRemoved, TestProductNamePreserved, TestImplementationGatesPreserved
- Functions: _md_path, _json_path, _load_md, _load_json, _load_md_lines, _parse_md_frontmatter, _md_has_text, _md_has_section, _count_occurrences
- Imports: __future__, json, os, pathlib, pytest, re, typing
### `tests/test_phase14_6e_p0_ratification.py`
- Lines: 547. Doc: Comprehensive pytest test suite for Phase 14.6E P0 ratification sprint.
- Classes: TestArtifactExistence, TestImplementationGatesPreserved, TestAllP0DecisionsApproved, TestDecisionQueueConsistency, TestDecisionResolutions, TestDeltaReportStructure, TestSpecificDecisionContent, TestProductGroupCounts
- Functions: _load, _parse_md_frontmatter, _has_text, _has_section, _count_occurrences, _get_decision_section
- Imports: __future__, os, pathlib, pytest, re, typing
### `tests/test_phase14_6f_canon_revision.py`
- Lines: 860. Doc: Comprehensive pytest test suite for Phase 14.6F cross-product canon revision sprint.
- Classes: TestArtifactExistence, TestPhaseMarkers, TestImplementationGates, TestStaleNaming, TestRealityModelFraming, TestStage1Organism, TestMaterializationPrinciple, TestUMHOpenQuestionsResolved
- Functions: _read, _read_json, _content_lower, _has_stale_unqualified
- Imports: __future__, json, os, pathlib, pytest, re
### `tests/test_phase14_6g_readiness_gate.py`
- Lines: 581. Doc: Phase 14.6G: UMH Stage 1 Functional Organism Readiness Gate Tests
- Classes: TestArtifactExistence, TestFrontmatter, TestP0DecisionCoverage, TestAcceptanceCriteria, TestWorkPacketIndex, TestDependencyGraph, TestGovernanceGate, TestProjectionDependencyGate
- Functions: _read
- Imports: os, pathlib, pytest, re, subprocess
### `tests/test_phase14_7a_wave1.py`
- Lines: 739. Doc: Phase 14.7A Wave 1 — Foundation Wiring tests.
- Classes: TestRealityModelRoutesExist, TestRealityModelCanonical, TestRealityModelInstance, TestRealityModelSimulation, TestMemoryRouteUpgrade, TestExecutionControlWiring, TestUsableRealityModel, TestWorkPacketLifecycle
- Functions: -
- Imports: __future__, importlib, json, os, pathlib, pytest, sys, tempfile
### `tests/test_phase14_7a_wave2.py`
- Lines: 454. Doc: Phase 14.7A Wave 2 — Organism Loop tests.
- Classes: TestOperatorLoopRouteModule, TestWorkPacketGeneration, TestAgentToolRouting, TestGovernedApprovalGates, TestOperatorLoopEndToEnd, TestAuditTrail, TestRealityModelOutcomeRecording, TestSelfImprovementSafety
- Functions: -
- Imports: __future__, importlib, json, os, pathlib, pytest, sys, tempfile
### `tests/test_phase14_7a_wave3.py`
- Lines: 380. Doc: Phase 14.7A Wave 3 — Self-Improvement Loop tests.
- Classes: TestSelfImprovementRouteModule, TestOutcomeAssimilation, TestCadenceIntegration, TestVerificationPipeline, TestFeedbackLoop, TestWave3SafetyGates
- Functions: -
- Imports: __future__, importlib, json, os, pathlib, pytest, sys, tempfile
### `tests/test_phase14_7b_cockpit_usability.py`
- Lines: 576. Doc: Phase 14.7B — Cockpit Command Surface Wiring + Internal Operator Usability.
- Classes: TestAgentCommandCenter, TestWorkPacketKanban, TestOperatorLoopStore, TestOperatorControlLoop, TestA2AComms, TestProviderRegistry, TestMetaIDE, TestMemorySkillsSourceTruth
- Functions: -
- Imports: __future__, importlib, json, os, pathlib, pytest, sys, tempfile
### `tests/test_phase14_8a_wp12.py`
- Lines: 295. Doc: Phase 14.8A WP-1.2 — WorldModelPanel wiring to reality model routes.
- Classes: TestNoOrganismEndpoints, TestStoreCallsRealityModelRoutes, TestBackendRouteContracts, TestFrontendTypeAlignment, TestPanelStructure, TestDistWebBuild, TestBackendResponseShapes
- Functions: -
- Imports: __future__, json, os, pathlib, pytest, re, sys
### `tests/test_phase14_8b_wave2.py`
- Lines: 374. Doc: Phase 14.8B Wave 2 — Organism Loop wiring tests.
- Classes: TestIntentClassifyEndpoint, TestIntentPatterns, TestGenerateEndpoint, TestExistingCreateEndpoint, TestWorkPacketEngineIntegration, TestUniversalWorkPanelRoutes, TestExecutionStartRouting, TestCapabilityRouterIntegration
- Functions: _find_handler_block, _find_handler_by_def
- Imports: __future__, os, pathlib, pytest, re, sys
### `tests/test_phase14_8c_wave3.py`
- Lines: 606. Doc: Phase 14.8C Wave 3 tests — outcome recording, cadence enforcement,
- Classes: TestOutcomeRecordingHook, TestOutcomeEndpoints, TestOutcomeVisibilityRoutes, TestCadenceDryRunEnforcement, TestCadenceDataFlow, TestVerificationPipeline, TestVerificationFields, TestProjectionDetection
- Functions: -
- Imports: __future__, json, os, pathlib, pytest, sys, tempfile, time
### `tests/test_phase17_organism_loop_e2e.py`
- Lines: 317. Doc: Phase 17 — Organism Loop E2E integration tests.
- Classes: TestOrganismLoopCycle1, TestOrganismLoopCycle2, TestOrganismSubsystemWiring, TestOrganismLoopLifecycleStates, TestOrganismLoopSecurityHardening
- Functions: -
- Imports: __future__, os, pathlib, projections, projections.eos, projections.eos.agents, pytest, substrate
### `tests/test_phase18_operator_convergence.py`
- Lines: 413. Doc: Phase 18 — Operator Convergence integration tests.
- Classes: TestIntentRouterClassification, TestIntentReceiptPersistence, TestRealityAwareConversation, TestOperatorTimeline, TestPersistenceContinuity, TestJarvisE2E, TestNoNewExecutionAuthority
- Functions: -
- Imports: __future__, json, os, pathlib, projections, projections.eos, projections.eos.agents, pytest
### `tests/test_phase19_reality_canonicalization.py`
- Lines: 503. Doc: Phase 19 — Reality Canonicalization E2E tests.
- Classes: TestConversationToReality, TestGovernanceToReality, TestValidationGates, TestRestartContinuity, TestNoNewAuthority, TestWritePathNoAuthority, TestMutationContract, TestEventEmission
- Functions: _make_instance_model, _make_mutation
- Imports: __future__, json, os, pathlib, pytest, substrate.reality_model.canonical_reality_write, substrate.reality_model.instance, substrate.reality_model.reality_mutation
### `tests/test_phase20_reality_intelligence.py`
- Lines: 656. Doc: Phase 20 — Reality Intelligence tests.
- Classes: _MockObservation, _MockPattern, _MockInstanceModel, _MockCanonicalModel, _MockEvent, _MockEventDomain, _MockEventSpine, _MockMemoryStore
- Functions: -
- Imports: __future__, dataclasses, datetime, pytest, substrate.reality_model.reality_intelligence, substrate.reality_model.reality_query, sys, time
### `tests/test_phase21_meta_ide_convergence.py`
- Lines: 508. Doc: Tests for Phase 21 — Meta IDE Convergence.
- Classes: TestRepositoryModelContracts, TestRepositoryReader, TestWorkspaceIntelligence, TestRiskDetection, TestRoadmapIntelligence, TestRealityIntegration, TestReadOnlyGuarantee, TestTypeRegistry
- Functions: -
- Imports: __future__, os, pytest, sys, tempfile, time, unittest.mock
### `tests/test_phase22_autonomous_engineering.py`
- Lines: 773. Doc: Phase 22 — Autonomous Engineering Loop tests.
- Classes: TestEngineeringIntentClassification, TestEngineeringIntentTypes, TestGoalExtraction, TestEngineeringPlanner, TestWorkGeneratorComposition, TestGovernanceEnforcement, TestNoNewAuthority, TestRoadmapGapEngine
- Functions: -
- Imports: __future__, dataclasses, pytest, substrate.meta_ide.engineering_intent, substrate.meta_ide.engineering_planner, substrate.meta_ide.engineering_work_generator, substrate.meta_ide.roadmap_gap_engine, sys
### `tests/test_phase23_engineering_proof_loop.py`
- Lines: 841. Doc: Phase 23 — Engineering Proof Loop test suite.
- Classes: TestExecutionContracts, TestSessionCoordinator, TestReviewPackageBuilder, TestExecutorComposition, TestMultiAgentDispatch, TestGovernanceEnforcement, TestNoNewAuthority, TestDeterministicFirst
- Functions: _make_plan
- Imports: __future__, substrate.meta_ide.engineering_execution, substrate.meta_ide.engineering_intent, substrate.meta_ide.engineering_session_coordinator, substrate.meta_ide.review_package_builder, sys, unittest, unittest.mock
### `tests/test_phase24_distributed_worker_runtime.py`
- Lines: 812. Doc: Phase 24 — Distributed Worker Runtime test suite.
- Classes: _FakePacket, TestWorkerRegistry, TestDeviceCapacityModel, TestPacketRouter, TestCoordinatorConstraints, TestWorkerLifecycle, TestDistributedRuntime, TestCockpitRoutes
- Functions: _make_profiles, _make_spine
- Imports: __future__, substrate.organism.device_capacity, substrate.organism.device_role_registry, substrate.organism.distributed_runtime, substrate.organism.event_spine, substrate.organism.packet_router, substrate.organism.worker_lifecycle, substrate.organism.worker_registry
### `tests/test_phase25_workspace_observation.py`
- Lines: 894. Doc: Phase 25 — Workspace Observation tests.
- Classes: TestObservationTypes, TestTerminalObservation, TestContainerObservation, TestPreviewObservation, TestEngineeringSessionObservation, TestWorkspaceObservationSnapshot, TestWorkspaceObservationEngine, TestWorkspaceProbe
- Functions: -
- Imports: __future__, json, os, pytest, sys, time, unittest.mock
### `tests/test_phase26_action_bridge.py`
- Lines: 786. Doc: Phase 26 — Governed Action Bridge tests.
- Classes: TestActionTypes, TestActionDefinition, TestActionCatalog, TestActionBridge, TestIntentContract, TestCockpitRoutes, TestTypeRegistration, TestIntegration
- Functions: -
- Imports: __future__, os, pytest, sys, time, unittest.mock
### `tests/test_phase27_workspace_runtime_graph.py`
- Lines: 705. Doc: Tests for Phase 27 — Workspace Runtime Graph.
- Classes: TestWorkspaceTypes, TestWorkspaceModels, TestWorkspaceRegistry, TestTopologyEngine, TestRuntimeGraphIntegration, TestWorkspaceHealth, TestCockpitRoutes, TestTypeRegistration
- Functions: -
- Imports: __future__, os, sys, unittest
### `tests/test_phase28_umh_node_role_version_topology.py`
- Lines: 759. Doc: Phase 28 — UMH Node Role & Version Topology tests.
- Classes: TestUMHNodeTypes, TestUMHVersionInfo, TestUMHServiceActivation, TestUMHNodeModels, TestUMHNodeRegistry, TestSeedNodes, TestVersionCoherence, TestWorkspaceNodeLinks
- Functions: -
- Imports: __future__, json, os, substrate.organism.umh_node_topology, sys, time, unittest, unittest.mock
### `tests/test_phase29_state_authority_graph.py`
- Lines: 802. Doc: Phase 29 — Organism State Authority & Coherence tests.
- Classes: TestStateDomainEnum, TestStateAuthorityLevel, TestStateCoherenceStatus, TestStateAuthorityModel, TestStateDomainStatusModel, TestOrganismStateGraph, TestStateRegistry, TestSeedAuthorities
- Functions: -
- Imports: __future__, json, os, sys, time, unittest, unittest.mock
### `tests/test_phase30_service_dependency_graph.py`
- Lines: 981. Doc: Phase 30 — Service Dependency & Failure Graph tests.
- Classes: TestDependencyStrengthEnum, TestServiceCriticalityEnum, TestServiceHealthImpactEnum, TestServiceDependency, TestServiceNode, TestFailureImpact, TestServiceDependencyTopology, TestServiceDependencyRegistry
- Functions: -
- Imports: json, os, sys, unittest
### `tests/test_phase31_operator_home.py`
- Lines: 937. Doc: Phase 31 — Operator Home & Context Engine tests.
- Classes: MockOrganismEvent, MockEventSpine, MockNodeRecord, MockNodeRegistry, MockApprovalRequest, MockApprovalStore, MockServiceFailureEngine, MockStateCoherenceEngine
- Functions: _make_card, _make_attention, _make_timeline_event, _make_health, _make_engine
- Imports: __future__, dataclasses, os, substrate.operator.operator_context, substrate.operator.operator_context_engine, sys, time, typing
### `tests/test_phase32_presence_continuity.py`
- Lines: 1282. Doc: Phase 32 — Presence & Continuity Runtime tests.
- Classes: TestPresenceStateEnum, TestPresenceDeviceTypeEnum, TestContinuityStatusEnum, TestOperatorPresence, TestActiveContext, TestContinuityCheckpoint, TestPresenceSnapshot, MockWorkspaceObservationEngine
- Functions: _make_engine
- Imports: __future__, os, sys, time, unittest, unittest.mock
### `tests/test_phase33_screen_awareness.py`
- Lines: 1397. Doc: Phase 33 — Screen Awareness Runtime tests.
- Classes: MockTerminal, MockSession, MockWorkspaceSnapshot, MockWorkspaceEngine, MockTopologyEngine, MockNode, MockNodeRegistry, MockContextEngine
- Functions: _make_engine, _make_continuity_engine
- Imports: __future__, os, sys, time, unittest, unittest.mock
### `tests/test_phase34_workstation_observation.py`
- Lines: 1172. Doc: Phase 34 — Workstation Observation Runtime tests.
- Classes: TestWorkstationTranslatorBasic, TestWorkstationTranslatorFocusedWindow, TestWorkstationTranslatorApplications, TestWorkstationTranslatorEditor, TestWorkstationTranslatorBrowser, TestWorkstationTranslatorDetail, TestAppClassification, TestScreenSnapshotExtension
- Functions: _make_beast_payload, _make_window, _make_monitor
- Imports: __future__, hashlib, json, os, sys, time, typing, unittest
### `tests/test_phase35_voice_runtime.py`
- Lines: 1050. Doc: Phase 35 — Voice Query Engine tests.
- Classes: MockClassification, MockSnapshot, MockHealthSummary, MockScreenSnapshot, MockSourceType, MockApp, MockFileContext, MockRepoContext
- Functions: _patch_reality_import
- Imports: __future__, dataclasses, pytest, substrate.operator.voice_query_engine, sys, time, unittest.mock
### `tests/test_phase9_5_spine_native_propagation.py`
- Lines: 854. Doc: Phase 9.5 — Spine-Native Propagation + Template-Guided Campaign Tests.
- Classes: TestSpineNativePropagation, TestBackwardCompatibility, TestIdempotency, TestFailureIsolation, TestTemplateGuidedCampaign, TestOutcomeEvents, TestDaemonWiring, TestPropagationWiring
- Functions: tmpdir, event_spine, mode_manager, mutation_registry, journal, learning_loop, template_registry, memory_pipeline, agent_model, propagation_engine, spine, spine_no_propagation
- Imports: __future__, json, os, pytest, substrate.organism.action_envelope, substrate.organism.agent_capability_model, substrate.organism.coherence_propagation, substrate.organism.event_spine
### `tests/test_phase9_5b_template_campaign.py`
- Lines: 438. Doc: Phase 9.5B — Real Template-Guided Improvement Campaign Tests.
- Classes: TestCampaignExecution, TestTemplateGeneration, TestTemplateLifecycle, TestAgentCapability, TestOutcomeLearning, TestMemoryPromotion, TestCandidateQueue, TestSafetyGates
- Functions: tmpdir, campaign_env, _step_executor_factory
- Imports: __future__, json, os, pytest, substrate.organism.action_envelope, substrate.organism.agent_capability_model, substrate.organism.coherence_propagation, substrate.organism.composition_engine
### `tests/test_phase9_6_autonomous_lane.py`
- Lines: 1002. Doc: Phase 9.6 — Autonomous Improvement Lane Tests.
- Classes: TestCandidateSelector, TestPolicyEvaluator, TestDryRun, TestRunOnce, TestSafetyGates, TestNoManualPropagation, TestLaneStatus, TestTemplateConfidence
- Functions: tmpdir, lane_env, _step_executor_factory, _make_promoted_template, _seed_agent_reliability
- Imports: __future__, json, os, pytest, substrate.organism.agent_capability_model, substrate.organism.autonomous_improvement_lane, substrate.organism.composition_engine, substrate.organism.event_spine
### `tests/test_phase9_7_pr_factory.py`
- Lines: 1104. Doc: Phase 9.7 — Sandboxed Autonomous PR Factory tests.
- Classes: TestMakeBranchName, TestWorktreeSandbox, TestSandboxValidationResult, TestSandboxManager, TestChangedFile, TestValidationProof, TestRiskProof, TestChangeSetManifest
- Functions: tmp_dir, sandbox_manager, sample_candidate, sample_candidate_b
- Imports: __future__, json, os, pytest, shutil, substrate.organism.autonomous_improvement_lane, substrate.organism.autonomous_pr_factory, substrate.organism.changeset_manifest
### `tests/test_phase9_8_production_truth.py`
- Lines: 1860. Doc: Phase 9.8 — Production Truth Promotion + Scheduled Autonomous Cadence tests.
- Classes: TestProductionTruthDelta, TestProductionMergeVerifier, TestProductionOutcomeCommittedContract, TestTruthBoundary, TestAutonomousCadence, TestDaemonCadenceIntegration, TestCleanupLifecycle, TestMergeVerificationStatus
- Functions: -
- Imports: __future__, json, os, pytest, shutil, tempfile, time
### `tests/test_philosophy_lenses.py`
- Lines: 154. Doc: Tests for substrate.understanding.knowledge.philosophy_lenses.
- Classes: -
- Functions: test_lenses_count_is_16, test_all_lenses_have_unique_ids, test_all_lenses_have_unique_names, test_all_lenses_have_trigger_keywords, test_all_lenses_have_application_question, test_all_lenses_have_description, test_lens_ids_are_sequential, test_match_returns_relevant_lenses, test_match_respects_top_n, test_match_returns_empty_for_no_keywords, test_apply_returns_formatted_question, test_inject_returns_formatted_context
- Imports: __future__, substrate.understanding.knowledge.philosophy_lenses
### `tests/test_prediction_portfolio_runtime.py`
- Lines: 314. Doc: Tests for PredictionPortfolioRuntime — Campaign 13.2.
- Classes: FakeTrajectoryRuntime, FakeScenarioEngine, FakeLearningPortfolio, FakeCapabilityPortfolio, FakeWorkPortfolio, FakeStrategicMemory, TestPredictionHealth, TestPredictionDriftType
- Functions: -
- Imports: __future__, pytest, substrate.organism.prediction_portfolio_runtime, sys
### `tests/test_prediction_routes.py`
- Lines: 97. Doc: Tests for cockpit prediction routes — Campaign 13.3.
- Classes: TestRouteImports, TestLazySingletons, TestRuntimeIntegration
- Functions: -
- Imports: __future__, pytest, sys
### `tests/test_presence_runtime.py`
- Lines: 798. Doc: Tests for Phase 8: Presence Runtime.
- Classes: TestPresenceAttentionState, TestInterruptionLevel, TestPresenceEventType, TestInteractionSurface, TestDeviceInfo, TestSessionInfo, TestPresenceSnapshot, TestPresenceEvent
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.presence_runtime, sys, tempfile, time
### `tests/test_priority_engine.py`
- Lines: 306. Doc: Campaign 7.1 — Priority Engine tests.
- Classes: _MockGapEngine, _MockRuntimeAwareness, _MockTickLoop, _MockKnowledgeEntry, _MockKnowledgeAwareness, TestPrioritizedItem, TestScoringFormula, TestSourceMerging
- Functions: _make_engine, _old_gap
- Imports: __future__, pytest, substrate.organism.priority_engine, sys, time
### `tests/test_product_connections.py`
- Lines: 130. Doc: Tests for substrate.integrations.product_connections.
- Classes: -
- Functions: test_product_enum_values, test_connection_status_values, test_product_connection_defaults, test_manager_creates_all_products, test_manager_get_connection, test_manager_get_missing_product, test_all_connections_format, test_cross_product_summary_structure, test_connected_products_returns_configured, test_connected_products_excludes_disconnected, test_compounding_requires_two, test_refresh_reloads
- Imports: os, substrate.integrations.product_connections, sys
### `tests/test_profile_runtime.py`
- Lines: 970. Doc: Tests for Phase 11 — Profile Runtime.
- Classes: TestProfileModeEnum, TestSystemModeEnum, TestActivationSource, TestProfileEventType, TestConflictSeverity, TestProfile, TestSystemModeModel, TestProfileModeState
- Functions: -
- Imports: __future__, json, os, shutil, substrate.organism.profile_runtime, sys, tempfile, time
### `tests/test_project_registry.py`
- Lines: 304. Doc: Tests for Project Registry — Campaign 5.2.
- Classes: TestProjectDefinition, TestProjectRegistryLoad, TestProjectRegistryGet, TestProjectRegistryList, TestContextForProject, TestEdgeCases
- Functions: seed_data, registry_path, registry
- Imports: __future__, json, os, pytest, substrate.organism.project_registry, sys
### `tests/test_projection_certification.py`
- Lines: 448. Doc: Tests for C26C — Projection Certification Framework.
- Classes: TestCertificationTypes, TestProjectionConfig, TestProjectionRegistry, TestProjectionCertificationEngine, TestCertificationInvariants, TestCertificationCanonicalTypes
- Functions: make_mock_http
- Imports: __future__, json, os, pytest, substrate.organism.projection_certification, sys, tempfile
### `tests/test_projection_delta.py`
- Lines: 207. Doc: Tests for projection delta engine.
- Classes: -
- Functions: test_capability_state, test_projection_delta_counts, test_delta_report_markdown, test_engine_compare, test_engine_json_roundtrip, test_engine_missing_report, test_capability_to_dict, test_delta_report_to_dict
- Imports: __future__, json, os, substrate.organism.self_use.projection_delta, sys, tempfile
### `tests/test_projection_engine.py`
- Lines: 772. Doc: Tests for Phase 6: Projection Engine.
- Classes: TestTimeHorizon, TestTrendDirection, TestRiskSeverity, TestProjectionConfidence, TestTrendRecord, TestProjection, TestStrategicRisk, TestStrategicOpportunity
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.projection_engine, sys, tempfile, time
### `tests/test_projection_integration_runtime.py`
- Lines: 347. Doc: Tests for ProjectionIntegrationRuntime — Campaign 3.5.
- Classes: TestAliasNormalization, TestLocationRegistration, TestAvailabilityProbing, TestAudit, TestGapDetection, TestDuplicationDetection, TestBuildReadiness, TestSnapshotAggregation
- Functions: -
- Imports: __future__, os, pytest, substrate.organism.projection_integration_runtime, sys, unittest.mock
### `tests/test_provider_state.py`
- Lines: 209. Doc: Tests for runtime.provider_state — global failure state + backpressure.
- Classes: -
- Functions: test_provider_state_lifecycle, test_system_global_status, test_all_providers_failed_backoff, test_no_retry_storm, test_execution_budget, test_agent_spawn_guard, test_system_allow_agent_spawn, test_recovery_path, test_singleton, test_summary
- Imports: os, substrate.state.providers.provider_state, sys, time
### `tests/test_reality_ambush.py`
- Lines: 533. Doc: Reality Ambush Test — Phase 1 Final Gate.
- Classes: TestAmbush1_MissingClerkKey, TestAmbush2_HealthFailure, TestAmbush3_MissingRoute, TestAmbush4_BrokenDatabase, TestAmbush5_WrongDNS, TestAmbush6_WrongPort, TestAmbush7_MissingClerkSecret, TestAmbush8_WrongClerkKey
- Functions: make_mock_http, make_engine
- Imports: __future__, json, os, pytest, substrate.meta_ide.engineering_execution, substrate.meta_ide.review_package_builder, substrate.organism.deploy_verification_worker, substrate.organism.outcome_verification
### `tests/test_reality_benchmark.py`
- Lines: 136. Doc: Tests for C26F Reality Correspondence Benchmark.
- Classes: TestBenchmarkScenarios, TestBenchmarkResults, TestScoringEngine, TestBenchmarkTypes, TestCanonicalTypes
- Functions: benchmark
- Imports: __future__, pytest, substrate.organism.benchmarks.reality_correspondence, sys
### `tests/test_reality_graph.py`
- Lines: 546. Doc: Tests for Reality Graph — Campaign 5.0.
- Classes: TestRealityEntityType, TestRealityRelationType, TestRealityEntityStatus, TestRealityEntity, TestRealityRelation, TestSeedFromRegistries, TestFindByName, TestFindByProperty
- Functions: device_registry, workspace_registry, project_registry, seeded_graph
- Imports: __future__, json, os, pytest, substrate.organism.reality_graph, sys, tempfile, time
### `tests/test_reality_model.py`
- Lines: 95. Doc: -
- Classes: TestCanonicalRealityModel, TestInstanceRealityModel
- Functions: -
- Imports: pathlib, pytest, substrate.reality_model.canonical, substrate.reality_model.instance, sys, uuid
### `tests/test_recommendation_engine.py`
- Lines: 310. Doc: Campaign 7.3 — Recommendation Engine tests.
- Classes: _MockRec, _MockGapEngine, _MockAction, _MockNextActionEngine, _MockTickLoop, _MockPrioritizedItem, _MockPriorityEngine, TestUnifiedRecommendation
- Functions: _make_engine
- Imports: __future__, pytest, substrate.organism.recommendation_engine, sys, time
### `tests/test_registry.py`
- Lines: 105. Doc: Tests for ConcreteComponentRegistry.
- Classes: TestComponentRegistry
- Functions: _make_component
- Imports: __future__, pytest, substrate.control_plane.registry, substrate.types, uuid
### `tests/test_repository_awareness.py`
- Lines: 355. Doc: Tests for Campaign 6.1 — Repository Awareness Runtime.
- Classes: TestFileCategory, TestFileEntry, TestRepositorySnapshot, TestCategorization, TestImportantFiles, TestRepositoryScan, TestSnapshot, TestEntityFileMapping
- Functions: runtime, mock_repo
- Imports: __future__, os, pytest, substrate.organism.repository_awareness_runtime, sys, time
### `tests/test_resource_allocation_runtime.py`
- Lines: 350. Doc: Tests for ResourceAllocationRuntime — Campaign 14.0.
- Classes: FakeStrategicPlanning, FakeGoalAlignment, FakeCapabilityGap, FakeWorkPortfolio, FakePredictionPortfolio, FakeLearningPortfolio, FakeDecisionImpact, TestResourceType
- Functions: -
- Imports: __future__, pytest, substrate.organism.resource_allocation_runtime, sys
### `tests/test_risk_engine.py`
- Lines: 254. Doc: Campaign 7.2 — Risk Engine tests.
- Classes: _MockProjectionEngine, _MockRuntimeAwareness, _MockDocEntry, _MockDocAwareness, _MockKnowledgeEntry, _MockKnowledgeAwareness, TestUnifiedRisk, TestRiskCategory
- Functions: _make_engine
- Imports: __future__, pytest, substrate.organism.risk_engine, sys, time
### `tests/test_runtime_awareness.py`
- Lines: 316. Doc: Tests for Campaign 6.3 — Runtime Awareness Runtime.
- Classes: MockWorktree, MockProcess, MockContainer, MockExecution, MockSnapshot, MockStateRegistry, MockWorkPacket, MockExecutionCoordinator
- Functions: populated_state, populated_execution, populated_work_graph
- Imports: __future__, dataclasses, os, pytest, substrate.organism.runtime_awareness_runtime, sys, typing
### `tests/test_runtime_state_registry.py`
- Lines: 434. Doc: Tests for Runtime State Registry — Phase 16.
- Classes: -
- Functions: test_worktree_info_frozen, test_worktree_info_to_dict, test_git_repo_info_to_dict, test_process_info_to_dict, test_container_info_to_dict, test_execution_info_to_dict, test_snapshot_immutable, test_snapshot_to_dict_summary, _make_snap, test_store_empty, test_store_append_and_latest, test_store_bounded_eviction
- Imports: __future__, pytest, substrate.organism.runtime_state_registry, sys, threading, time
### `tests/test_scenario_intelligence_engine.py`
- Lines: 298. Doc: Tests for ScenarioIntelligenceEngine — Campaign 13.1.
- Classes: FakeTrajectoryRuntime, FakeDecisionValidity, FakeWorkPortfolio, FakeCapabilityPortfolio, FakeLearningPortfolio, FakeStrategicPlanning, FakeRiskEngine, TestScenarioType
- Functions: -
- Imports: __future__, pytest, substrate.organism.scenario_intelligence_engine, sys, time
### `tests/test_self_model.py`
- Lines: 350. Doc: Tests for substrate.self_model — the system's self-awareness foundation.
- Classes: TestCanonicalSelf, TestInstanceSelf, TestClassification, TestLayerDetection, TestInstanceValueDetection, _MockRegistry, _MockTraceRecorder, _MockRuntimeGraph
- Functions: -
- Imports: os, pytest, substrate.self_model, sys
### `tests/test_self_use_catalog.py`
- Lines: 148. Doc: Tests for C27 self-use task catalog.
- Classes: -
- Functions: test_task_roundtrip, test_task_coherence_domain, test_catalog_from_json, test_catalog_by_stream, test_catalog_by_projection, test_catalog_record_result, test_catalog_surface_coverage, test_catalog_summary, test_catalog_missing_file, test_task_result_roundtrip
- Imports: __future__, json, os, substrate.organism.self_use.task_catalog, substrate.organism.self_use.task_taxonomy, sys, tempfile
### `tests/test_self_use_gap_ledger.py`
- Lines: 136. Doc: Tests for C27 gap ledger.
- Classes: -
- Functions: test_gap_entry_roundtrip, test_ledger_add_and_query, test_ledger_resolve, test_ledger_summary, test_ledger_json_roundtrip, test_all_gap_types_valid
- Imports: __future__, json, os, substrate.organism.self_use.gap_ledger, substrate.organism.strategic_gap_engine, sys, tempfile
### `tests/test_self_use_report.py`
- Lines: 183. Doc: Tests for C27 certification report.
- Classes: -
- Functions: test_coherence_metrics_pass, test_coherence_metrics_fail_threshold, test_coherence_metrics_fail_zero_tolerance, test_coherence_metrics_fail_lost_commitments, test_coherence_override, test_all_gates_pass, test_production_gate_fail, test_meta_ide_critical_path_broken, test_report_to_markdown, test_report_to_dict, test_gate_result_roundtrip
- Imports: __future__, substrate.organism.self_use.certification_report, sys
### `tests/test_session_machine_runtime.py`
- Lines: 344. Doc: Tests for SessionMachineRuntime — Campaign 19.2.
- Classes: MockDevice, MockSession, MockWorkspace, MockHandoff, TestSnapshot, TestBindings, TestPrimarySession, TestWorkspaces
- Functions: _empty_sessions, _empty_presence, _empty_workspace, _empty_continuity, _make_runtime, _make_empty_runtime
- Imports: __future__, dataclasses, pytest, substrate.workstation.session_machine_runtime, sys, time, typing, unittest.mock
### `tests/test_session_runtime.py`
- Lines: 1013. Doc: Tests for Phase 12: Session Runtime.
- Classes: TestSessionType, TestSessionStatus, TestSessionAuthority, TestSessionEventType, TestHandoffStatusEnum, TestSession, TestSessionEvent, TestSessionHandoff
- Functions: _patch_data_dir, _cleanup_data_dir, isolate_test
- Imports: __future__, json, os, pytest, shutil, sys, tempfile, time
### `tests/test_source_truth_linker.py`
- Lines: 413. Doc: Tests for Source Truth Linker — Campaign 5.4.
- Classes: MockSource, MockSourceRegistry, TestLinkProjectsToRepos, TestLinkReposToWorkspaces, TestLinkProjectsToProjections, TestLinkProjectsToDocs, TestLinkServicesToDevices, TestTraceFromEntity
- Functions: device_registry, workspace_registry, project_registry_path, seeded_graph, project_registry, linker, linked_graph
- Imports: __future__, json, os, pytest, substrate.organism.project_registry, substrate.organism.reality_graph, substrate.organism.source_truth_linker, sys
### `tests/test_spine_full.py`
- Lines: 163. Doc: Tests for ConcreteExecutionSpine — 8-stage pipeline.
- Classes: TestExecutionSpine
- Functions: _make_signal, _make_identity, _make_context, _make_verdict
- Imports: __future__, pytest, substrate.execution.spine, substrate.types, uuid
### `tests/test_sprint1_smoke.py`
- Lines: 265. Doc: Sprint 1 smoke tests — production stabilization.
- Classes: TestNodeRegistryDeadlock, TestRuntimeExecutionResultV1, TestRuntimePresenceStateV1, TestSupervisorImportChain, TestContextEnvLoading, TestServiceImportSmoke
- Functions: -
- Imports: os, pytest, threading
### `tests/test_sprint2_boundary.py`
- Lines: 122. Doc: Sprint 2 boundary repair tests — verify substrate→adapters type extraction.
- Classes: TestCanonicalTypes, TestBackwardCompatibility, TestNoTypeImportsFromAdapters
- Functions: -
- Imports: os, subprocess
### `tests/test_sprint3_recovery.py`
- Lines: 74. Doc: Sprint 3 — Test Recovery verification.
- Classes: TestMockPathsFixed, TestIntegrationMarkRegistered, TestReconciliationReceiptTestRobust
- Functions: -
- Imports: __future__, ast, os, pathlib, pytest, sys
### `tests/test_sprint4_data_hygiene.py`
- Lines: 117. Doc: Sprint 4 — Data/Log Hygiene verification.
- Classes: TestGitignoreCoversRuntimeData, TestJsonlRotation, TestRotationWiredIn
- Functions: -
- Imports: __future__, json, os, pathlib, pytest, subprocess, sys, tempfile
### `tests/test_sprint5_doc_truth.py`
- Lines: 81. Doc: Sprint 5 — Documentation Truth verification.
- Classes: TestReadmeAccuracy, TestClaudeMdAccuracy, TestSystemArchitecture, TestCurrentSystemStatus, TestCorporateStructure
- Functions: -
- Imports: __future__, os, pathlib, pytest, sys
### `tests/test_stage1_acceptance_e2e.py`
- Lines: 722. Doc: Phase 14.9A — Stage 1 E2E Acceptance Validation.
- Classes: TestAC1CockpitInterface, TestAC2IntentMemory, TestAC3RealityModel, TestAC4WorkPackets, TestAC5WorkRouting, TestAC6GovernedApproval, TestAC7Verification, TestAC8RealityUpdate
- Functions: _load_operator_token, _get, _post
- Imports: __future__, json, os, pytest, sys, time, urllib.error, urllib.request
### `tests/test_strategic_context_runtime.py`
- Lines: 398. Doc: Campaign 7.0 — Strategic Context Runtime tests.
- Classes: _MockGapEngine, _MockTickLoop, _MockProjectionEngine, _MockOperatorContext, _MockNextActionEngine, _MockAction, _MockRuntimeAwareness, _MockKnowledgeAwareness
- Functions: _make_runtime
- Imports: __future__, pytest, substrate.organism.strategic_context_runtime, sys, time
### `tests/test_strategic_gap_engine.py`
- Lines: 668. Doc: Strategic Gap Engine — Phase 4 acceptance tests.
- Classes: TestGoalRegistry, TestGoalSerialization, TestGapDetector, TestPriorityScoring, TestRecommendationEngine, TestStrategicGapEngine, TestAcceptanceTest, TestC80GoalTypeExtension
- Functions: tmp_dir, goal_registry, engine
- Imports: __future__, json, os, pytest, substrate.organism.strategic_gap_engine, tempfile, time
### `tests/test_strategic_memory_engine.py`
- Lines: 551. Doc: Tests for Campaign 9.4 — Strategic Memory Engine.
- Classes: MockDecision, MockDecisionRegistry, MockGoal, MockGoalRegistry, MockAssumption, MockAssumptionTracking, MockValidity, MockValidityEngine
- Functions: -
- Imports: __future__, dataclasses, os, pytest, substrate.organism.strategic_memory_engine, sys, time, typing
### `tests/test_strategic_planning_engine.py`
- Lines: 393. Doc: Tests for StrategicPlanningEngine — Campaign 8.3.
- Classes: TestPlanningStatus, TestStrategicMilestone, TestStrategicPlan, TestConstructor, TestClassifyStatus, TestGeneratePlan, TestMilestones, TestStatus
- Functions: tmp_store, registry, hierarchy, outcomes, engine, _goal
- Imports: os, pytest, substrate.organism.goal_hierarchy_engine, substrate.organism.outcome_tracking_runtime, substrate.organism.strategic_gap_engine, substrate.organism.strategic_planning_engine, sys, time
### `tests/test_strategic_tick_loop.py`
- Lines: 665. Doc: Tests for Phase 5: Strategic Tick Loop.
- Classes: TestTickFrequency, TestChangeDetector, TestSnapshotHash, TestCandidateWorkQueue, TestCandidateWorkItemSerialization, MockGoal, TestDriftDetector, TestDriftWarningSerialization
- Functions: -
- Imports: __future__, json, os, pytest, substrate.organism.strategic_tick_loop, sys, tempfile, time
### `tests/test_tme_active_tool_context.py`
- Lines: 189. Doc: Tests for the TME Active Tool Context.
- Classes: TestCreateActiveToolContext, TestUpdateActiveToolContext, TestShouldContinueContext, TestShouldSwitchContext, TestSummarize, TestSerialization
- Functions: _make_resolution
- Imports: os, substrate.composition.mastery.management.active_tool_context, substrate.composition.mastery.management.tool_mastery_resolver, sys, unittest
### `tests/test_tme_mastery_assurance_gate.py`
- Lines: 257. Doc: Tests for the TME Mastery Assurance Gate.
- Classes: TestNormalization, TestFreshness, TestQuality, TestCompleteness, TestRecommendedFlow, TestEnsureMasteryBeforeExecution, TestBlocksExecution, TestSerialization
- Functions: -
- Imports: datetime, os, substrate.composition.mastery.management.mastery_assurance, sys, unittest
### `tests/test_tme_natural_language_resolver.py`
- Lines: 205. Doc: Tests for the TME Natural Language Tool Mastery Resolver.
- Classes: TestDetectToolMentions, TestDetectCapabilityMentions, TestInferRequiredMasteryPacks, TestResolveMasteryForTask, TestShouldReuseActiveToolContext, TestExplainMasteryResolution
- Functions: -
- Imports: os, substrate.composition.mastery.management.tool_mastery_resolver, sys, unittest
### `tests/test_trace_recorder.py`
- Lines: 90. Doc: Tests for ConcreteTraceRecorder.
- Classes: TestTraceRecorder
- Functions: -
- Imports: __future__, pytest, substrate.execution.trace, substrate.types, uuid
### `tests/test_tradeoff_intelligence_engine.py`
- Lines: 290. Doc: Tests for TradeoffIntelligenceEngine — Campaign 14.1.
- Classes: FakeAllocationRecommendation, FakeResourceAllocation, FakeStrategicPlanning, FakeGoalAlignment, FakeWorkPortfolio, FakeCapabilityGap, FakePredictionPortfolio, TestTradeoffSeverity
- Functions: -
- Imports: __future__, pytest, substrate.organism.tradeoff_intelligence_engine, sys
### `tests/test_trajectory_intelligence_runtime.py`
- Lines: 349. Doc: Tests for TrajectoryIntelligenceRuntime — Campaign 13.0.
- Classes: FakeProjectionEngine, FakeOutcomeTracking, FakeGoalDrift, FakeDecisionValidity, FakeCapabilityEvolution, FakeLearningPortfolio, FakeWorkPortfolio, TestTrajectoryStatus
- Functions: -
- Imports: __future__, pytest, substrate.organism.trajectory_intelligence_runtime, sys, time
### `tests/test_transformation_state_ledger.py`
- Lines: 431. Doc: Tests for Transformation State Ledger -- Phase 96.8V.
- Classes: TestStateLedgerRecordCreation, TestStateLedgerValidation, TestStateLedgerTransitionValidation, TestLineageReconstruction, TestRollbackChain, TestLedgerPersistence, TestLedgerExampleArtifacts, TestTransformationStages
- Functions: _make_record
- Imports: json, os, pathlib, substrate.state.transformation_state_ledger, sys, tempfile, unittest
### `tests/test_trust_score.py`
- Lines: 265. Doc: Tests for TrustScoreEngine — C26E Phase 2.
- Classes: TestTrustScoreEngine, TestClassify, TestCanPromote, TestCache, TestSummary, TestSerialization, TestTrustGateIntegration, TestCanonicalTypes
- Functions: -
- Imports: __future__, pytest, substrate.organism.trust_score, sys
### `tests/test_type_divergence.py`
- Lines: 129. Doc: Tests for the type divergence detection system.
- Classes: TestCanonicalTypeRegistry, TestDivergenceChecker
- Functions: -
- Imports: pathlib, pytest, substrate.canonical_types, sys, tempfile
### `tests/test_unified_approval_runtime.py`
- Lines: 543. Doc: Tests for UnifiedApprovalRuntime — Campaign 4.2.
- Classes: TestPending, TestUrgencyScoring, TestByUrgency, TestApprove, TestReject, TestSnapshot, TestDecisions, TestGracefulDegradation
- Functions: _mock_governed, _mock_intercept, _mock_gate, _mock_strategic, _mock_compounding, _mock_templates, _mock_memory, _mock_overnight, _mock_automation, _mock_reconciliation, _build_runtime, _full_runtime
- Imports: __future__, pytest, substrate.workstation.unified_approval_runtime, sys, time, typing, unittest.mock
### `tests/test_unified_execution_surface_runtime.py`
- Lines: 603. Doc: Tests for UnifiedExecutionSurfaceRuntime — Campaign 3.3.
- Classes: MockGovernedWork, MockAgentFleet, MockComputeFabric, MockProofRuntime, MockCompoundingEngine, MockExecutionGraph, TestExecutionStreamSerialization, TestApprovalItemSerialization
- Functions: -
- Imports: __future__, pytest, substrate.workstation.unified_execution_surface_runtime, sys, time
### `tests/test_unified_workstation_runtime.py`
- Lines: 323. Doc: Tests for UnifiedWorkstationRuntime — Campaign 18.0.
- Classes: _Snapshot, _FakeOrchestratorPresence, _FakeWorkstationPresence, _FakeOrganismState, _FakeGovernedExecution, _FakeOrganismPortfolio, _FakeUnifiedApprovals, _FakeCommandCenter
- Functions: _runtime
- Imports: __future__, substrate.workstation.unified_workstation_runtime, sys, time
### `tests/test_vision.py`
- Lines: 240. Doc: Tests for Phase 14.14B — DEX Vision Embodiment.
- Classes: TestCameraCommandClassification, TestCameraVoiceRouting, TestDevicePresenceVideo, TestVisionPrivacy
- Functions: -
- Imports: __future__, os, pytest, substrate.workstation.camera_commands, substrate.workstation.device_presence, substrate.workstation.vision_privacy, substrate.workstation.voice_route_resolver, sys
### `tests/test_vision_14_16.py`
- Lines: 666. Doc: Tests for Phase 14.16 — Realtime Vision Overlay + Tracker Stack + Vision Preset Studio + Trigger Chain Engine.
- Classes: TestTrackerStack, TestVisionPresets, TestTriggerChains, TestSecurityMode, TestOverlayPrivacy, TestOverlayVoiceCommands, TestOverlayCommandRouter, TestOverlayVoiceRouting
- Functions: -
- Imports: __future__, os, pytest, substrate.workstation.camera_commands, substrate.workstation.command_router, substrate.workstation.security_mode, substrate.workstation.tracker_stack, substrate.workstation.trigger_chains
### `tests/test_vision_14_17.py`
- Lines: 355. Doc: Tests for Phase 14.17 — Vision Reliability Hardening.
- Classes: TestVisionHealthEndpoint, TestFrameValidation, TestOverlayTracking, TestCameraRecovery, TestTrackerCrashIsolation, TestGroundedVisionStatus, TestRelayPingPong
- Functions: -
- Imports: __future__, json, os, sys, threading, time, unittest, unittest.mock
### `tests/test_vision_14_18.py`
- Lines: 643. Doc: Tests for Phase 14.18 — Camera Default-On + Realtime PTZ Control Loop + Smooth Vision UX.
- Classes: TestDefaultOnPolicy, TestPrivacyRulesDefaultOn, TestContinuousMotionCommands, TestStopMotionCommands, TestDefaultOnCommands, TestDiagnosticCommands, TestExistingCommandsRegression, TestMotionStateMachine
- Functions: -
- Imports: __future__, os, pytest, re, sys
### `tests/test_vision_14_18c.py`
- Lines: 341. Doc: Tests for Phase 14.18C/19B — True PTZ Joystick + Overlay Visibility + Diagnostics.
- Classes: TestOverlayFilter, TestRelayMotionState, TestDiagnosticOverlays, TestHealthReport, TestJoystickVector, TestSourceCodeAudit
- Functions: -
- Imports: __future__, json, os, pytest, re, sys
### `tests/test_vision_14e.py`
- Lines: 674. Doc: Tests for Phase 14.14E — Voice Camera Control, Tracking, Scene Understanding.
- Classes: TestVoiceCameraPTZ, TestVoiceCameraRouting, TestVoicePresetControl, TestVoiceQualityMode, TestSceneState, TestObjectDetection, TestObjectTracking, TestOperatorLabeling
- Functions: -
- Imports: __future__, os, pytest, substrate.workstation.camera_commands, substrate.workstation.command_router, substrate.workstation.vision_privacy, substrate.workstation.vision_scene, substrate.workstation.voice_route_resolver
### `tests/test_voice_idempotency.py`
- Lines: 177. Doc: Phase 14.13V: Voice turn idempotency tests.
- Classes: TestVoiceTurnIdempotency
- Functions: _mock_call_with_fallback
- Imports: __future__, pytest, sys, time, unittest.mock
### `tests/test_voice_identity.py`
- Lines: 290. Doc: Phase 14.13U: Voice identity and source sync tests.
- Classes: TestSelfModelCanonical, TestVoiceFirstBridge, TestAdvisorResponseContract, TestVoiceSourceSync, TestOrganismResponseEnvelope, TestTtsPlaybackController
- Functions: -
- Imports: __future__, pytest, sys
### `tests/test_voice_route_resolver.py`
- Lines: 257. Doc: Tests for substrate/workstation/voice_route_resolver.py.
- Classes: TestTargetNodeParsing, TestAudioOverrideParsing, TestResolveVoiceRoute, TestSpokenTextContract
- Functions: _make_registry_with_session
- Imports: __future__, pytest, substrate.workstation.device_presence, substrate.workstation.voice_route_resolver, sys
### `tests/test_voice_turn_assembly.py`
- Lines: 263. Doc: Phase 14.13V: Voice turn assembly tests.
- Classes: TestVoiceTurnAssemblerExists, TestVoiceTurnControllerIntegration, TestSilenceTimerValues, TestDeduplicationLogic, TestDraftBubbleSupport
- Functions: -
- Imports: __future__, os, pytest, sys
### `tests/test_work_intelligence_routes.py`
- Lines: 311. Doc: Tests for cockpit work intelligence routes — Campaign 11.3.
- Classes: _MockReadinessAssessment, _MockReadinessSnapshot, _MockReadinessRuntime, _MockDelegationReadiness, _MockDelegationSnapshot, _MockDelegationRuntime, _MockDriftWarning, _MockPortfolioHealth
- Functions: reset_singletons, client
- Imports: dataclasses, os, pytest, sys, transports.api.cockpit_work_intelligence_routes, typing
### `tests/test_work_lanes.py`
- Lines: 549. Doc: Tests for Beast multi-session work lanes, app resolver, and loop engine.
- Classes: TestNativeAppResolution, TestChromeFirstPolicy, TestAppVsWebsiteClassification, TestLaneRouting, TestForegroundGuard, TestLoopEngine, TestSearchUrl, TestCommandRouterIntegration
- Functions: -
- Imports: __future__, pytest, sys, uuid
### `tests/test_work_portfolio_runtime.py`
- Lines: 513. Doc: Tests for WorkPortfolioRuntime — Campaign 11.2.
- Classes: _MockReadinessAssessment, _MockReadinessSnapshot, _MockReadinessRuntime, _MockDelegationSnapshot, _MockDelegationRuntime, _MockWGSnapshot, _MockWorkGraph, _MockOutcome
- Functions: -
- Imports: json, os, pytest, substrate.organism.work_portfolio_runtime, sys, tempfile
### `tests/test_work_readiness_runtime.py`
- Lines: 344. Doc: Tests for WorkReadinessRuntime — Campaign 11.0.
- Classes: _MockNode, _MockBlocker, _MockWorkGraph, _MockGoalAlignment, _MockCapabilityGap, _MockGap, _MockApprovalRuntime, _MockApprovalSnap
- Functions: -
- Imports: os, pytest, substrate.organism.work_readiness_runtime, sys, time
### `tests/test_work_state.py`
- Lines: 172. Doc: Tests for runtime.work_state — idle detection + adaptive throttling.
- Classes: -
- Functions: _reset_module_state, test_idle_when_no_work, test_not_idle_with_signal, test_not_idle_with_goals, test_not_idle_with_tasks, test_exponential_backoff, test_signal_resets_backoff, test_signal_ttl_expiry, test_pressure_measurement, test_max_idle_cap, test_provider_state_pressure_delegation
- Imports: os, substrate.state.work.work_state, sys, time
### `tests/test_workspace_awareness.py`
- Lines: 420. Doc: Tests for Workspace Awareness Runtime — Campaign 5.1.
- Classes: MockGitRepoInfo, MockWorktreeInfo, MockRuntimeSnapshot, MockRuntimeStateRegistry, TestWorkspaceSnapshot, TestDeviceDetection, TestDetectActiveWorkspace, TestGraphResolution
- Functions: seeded_graph, mock_runtime_state
- Imports: __future__, dataclasses, json, os, pytest, substrate.organism.reality_graph, substrate.organism.workspace_awareness, sys
### `tests/test_workstation_executor.py`
- Lines: 1102. Doc: Tests for WorkstationExecutor — Phase 15A.
- Classes: TestPathValidation, TestExecutionProof, TestValidation, TestPreparation, TestRunCommand, TestReadFile, TestWriteFile, TestListDirectory
- Functions: executor, tmp_workspace, sample_request, runtime_dir
- Imports: __future__, json, os, pytest, shutil, substrate.organism.executor_runtime, substrate.organism.executors.workstation_executor, sys
### `tests/test_workstation_mvp_loop.py`
- Lines: 367. Doc: Integration tests for Campaign 17 — Workstation MVP Loop.
- Classes: _FakeOrchestratorAwareness, _FakeOrganismState, _FakeGovernedExecution, _FakeContextResolution, _FakeWorkspaceAwareness, _FakeDeviceAwareness, _FakeApprovals, _FakeDelegation
- Functions: -
- Imports: __future__, substrate.workstation.meta_ide_context_runtime, substrate.workstation.orchestrator_presence_runtime, substrate.workstation.workstation_presence_runtime, sys, typing, unittest.mock
### `tests/test_workstation_presence_runtime.py`
- Lines: 213. Doc: Tests for Campaign 17.2 — WorkstationPresenceRuntime.
- Classes: _FakeDeviceAwareness, _FakeWorkspaceAwareness, _FakeContinuityEngine, _FakeApprovals, _FakeDevicePresence, TestWorkstationPresenceSnapshot, TestPanelTracking, TestDeviceOverride
- Functions: _wpr
- Imports: __future__, substrate.workstation.workstation_presence_runtime, sys, typing, unittest.mock
### `tests/test_workstation_runtime.py`
- Lines: 897. Doc: Tests for Phase 10 — Workstation Runtime.
- Classes: TestWorkstationMode, TestWorkspaceStatus, TestPreparationStepType, TestSnapshotTrigger, TestRecommendationType, TestWorkspaceTemplate, TestPreparationStep, TestWorkspacePreparationPlan
- Functions: -
- Imports: __future__, json, os, substrate.organism.workstation_runtime, sys, tempfile, time, unittest
### `tests/test_workstation_session_runtime.py`
- Lines: 462. Doc: Tests for WorkstationSessionRuntime — Campaign 4.4.
- Classes: TestLifecycle, TestResumeContext, TestChanges, TestCheckpoint, TestMultipleCheckpoints, TestSessionHistory, TestMissingDeps, TestNextActions
- Functions: _mock_awareness, _mock_continuity_runtime, _mock_continuity_engine, _mock_snapshot, _mock_attention, _mock_loop_rt, _mock_approval_rt, _mock_coherence_rt, _build_full_runtime
- Imports: __future__, pytest, substrate.operator.workstation_session_runtime, sys, time, typing, unittest.mock
### `transports/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `transports/api/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `transports/api/_mesh_dispatch.py`
- Lines: 257. Doc: Mesh dispatch — sends engineering plan tasks to a connected node via mesh HTTP relay.
- Classes: -
- Functions: get_proof_packages, _validate_node_id, _validate_cwd, dispatch_plan_to_node, _assemble_proof, _build_claude_prompt
- Imports: __future__, json, logging, os, time, typing
### `transports/api/agent_bridge.py`
- Lines: 139. Doc: Stdin/stdout JSON bridge between the TypeScript API and the Python AI layer.
- Classes: -
- Functions: _emit, _run_agent, _run_team, _run_brief, main
- Imports: dotenv, json, os, sys
### `transports/api/agent_routes.py`
- Lines: 161. Doc: Agent Executor API routes — governed cognitive worker endpoints.
- Classes: -
- Functions: _ensure_agent_executor_registered, _get_runtime, _authenticated_operator, agent_run, agent_executions, agent_execution_detail, agent_cancel
- Imports: __future__, fastapi, logging, time
### `transports/api/app.py`
- Lines: 705. Doc: UMH API server — FastAPI surface matching existing UMH service conventions.
- Classes: SignalRequest, SignalResponse, WritebackTo, SubmitRequest
- Functions: _start_persistent_loops, _stop_persistent_loops, _register_notion_integration, _register_eos_integration, _register_organism, _build_runtime_graph_hook, _resolve_device_id, _register_node_mesh, _wire_workstation_bridge, lifespan, health, signal_intake
- Imports: __future__, adapters.notion.integration.correlation, asyncio, contextlib, datetime, fastapi, fastapi.middleware.cors, logging
### `transports/api/approval_routes.py`
- Lines: 110. Doc: Phase 15C: Approval Intercept route handlers.
- Classes: -
- Functions: _get_service, _authenticated_operator, approvals_pending, approval_detail, approval_approve, approval_reject
- Imports: __future__, fastapi, logging
### `transports/api/cockpit.py`
- Lines: 1477. Doc: Cockpit API endpoints — serves real data from UMH stores to the frontend.
- Classes: -
- Functions: _is_private_ip, _real_client_ip, _dev_bypass_allowed, _check_rate_limit, _require_api_key, _require_operator_role, _mount_spine_router, _mount_chat_router, _mount_execution_loop_router, _mount_organism_router, _mount_entity_router, _mount_meta_ide_critical_router
- Imports: __future__, asyncio, datetime, fastapi, fastapi.responses, fastapi.security, hmac, ipaddress
### `transports/api/cockpit_action_bridge_routes.py`
- Lines: 128. Doc: Cockpit routes for the Governed Action Bridge (Phase 26).
- Classes: ExecuteActionBody
- Functions: _get_operator_id, configure, _get_bridge, _build_router
- Imports: __future__, fastapi, logging, pydantic, typing
### `transports/api/cockpit_activity_routes.py`
- Lines: 230. Doc: Cockpit Activity Routes — canonical activity/timeline capability surface.
- Classes: -
- Functions: configure, _get_event_spine, _get_receipt_store, _get_continuity_engine, _get_reality_engine, _safe_dict, _safe_list, _build_router
- Imports: __future__, fastapi, logging, time, typing
### `transports/api/cockpit_agent_fleet_routes.py`
- Lines: 161. Doc: Cockpit agent fleet routes — unified agent coordination surface.
- Classes: -
- Functions: configure, _get_fleet, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_agent_workforce_routes.py`
- Lines: 71. Doc: Cockpit routes for AgentWorkforceRuntime — Campaign 19.1.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_ambient_wake_routes.py`
- Lines: 54. Doc: Cockpit routes for AmbientWakeRuntime — Campaign 20.2.
- Classes: WakeRequest
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, pydantic, typing
### `transports/api/cockpit_artifact_registry_routes.py`
- Lines: 64. Doc: Cockpit routes for Artifact Registry — Campaign 6.0.
- Classes: -
- Functions: _get_registry, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_attention_routes.py`
- Lines: 43. Doc: Cockpit routes for AttentionAggregationRuntime — Campaign 18.2.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_auth.py`
- Lines: 210. Doc: Clerk JWT server-side validation for cockpit API.
- Classes: ClerkUser
- Functions: _get_jwks_client, _is_private_ip, _real_client_ip, _dev_bypass_allowed, _validate_jwt, require_clerk_auth, validate_ws_clerk_token
- Imports: __future__, dataclasses, fastapi, jwt, logging, os
### `transports/api/cockpit_autonomous_routes.py`
- Lines: 595. Doc: Cockpit autonomous PR factory and cadence scheduler routes.
- Classes: -
- Functions: configure, _get_pr_factory, _build_router, _autonomous_pr_factory_status, _autonomous_pr_factory_sandboxes, _autonomous_pr_factory_sandbox_detail, _autonomous_pr_factory_manifests, _autonomous_pr_factory_manifest_detail, _autonomous_pr_factory_create_pr, _autonomous_pr_factory_cleanup, _autonomous_pr_factory_parallel_dry_run, _autonomous_pr_factory_production_truth
- Imports: __future__, asyncio, fastapi, glob, json, logging, os, pathlib
### `transports/api/cockpit_broadcast_routes.py`
- Lines: 528. Doc: Broadcast API — start/stop/status + WebSocket health push.
- Classes: SourceType, BroadcastStartRequest, BroadcastStatusResponse, SourceEntryRequest, SourceLayoutRequest, SceneRequest, CompositeStartRequest, SceneSwitchRequest
- Functions: _get_engine, _on_engine_health, _dispatch_remote, _is_remote, start_broadcast, stop_broadcast, get_broadcast_status, start_composite_broadcast, switch_scene, list_scenes, list_broadcast_nodes, _extract_ws_subprotocol
- Imports: __future__, adapters.broadcast.scene_model, asyncio, enum, fastapi, json, logging, os
### `transports/api/cockpit_capability_intelligence_routes.py`
- Lines: 182. Doc: Cockpit routes for Capability Intelligence — Campaign 10.4.
- Classes: -
- Functions: _get_capability_runtime, _get_graph_engine, _get_gap_engine, _get_portfolio_runtime, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_capability_map_routes.py`
- Lines: 71. Doc: Cockpit Capability Map Routes — API surface for cockpit audit.
- Classes: -
- Functions: configure, _get_map, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_capability_routes.py`
- Lines: 138. Doc: Cockpit Capability Routes — API surface for emergent capability tracking.
- Classes: -
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_chat_routes.py`
- Lines: 420. Doc: Cockpit chat routes — advisor/dex conversation + operator chat.
- Classes: -
- Functions: configure, _build_router
- Imports: __future__, datetime, fastapi, fastapi.responses, json, logging, os, pathlib
### `transports/api/cockpit_command_center_mvp_routes.py`
- Lines: 123. Doc: Command Center MVP Routes — operator landing surface API.
- Classes: -
- Functions: configure, _get_runtime, _get_governed_execution, _get_organism_state, _get_execution_lifecycle, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_command_center_routes.py`
- Lines: 788. Doc: Cockpit command center routes — agent registry, work packet board, summary.
- Classes: -
- Functions: configure, _detect_env, _load_workcell_heartbeats, _load_work_packets, _load_blocked_packets, _load_approvals, _load_journal_recent, _load_traces_recent, _label_environment, _get_snapshot_runtime, _situation, _attention
- Imports: __future__, datetime, fastapi, json, logging, os, typing
### `transports/api/cockpit_compounding_routes.py`
- Lines: 124. Doc: Cockpit Compounding Routes — API surface for capability compounding.
- Classes: -
- Functions: configure, _get_engine, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_compute_fabric_routes.py`
- Lines: 89. Doc: Cockpit compute fabric routes — unified compute body map surface.
- Classes: -
- Functions: configure, _get_fabric, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_context_assimilation_routes.py`
- Lines: 552. Doc: Cockpit context assimilation routes — source registry, ingestion,
- Classes: -
- Functions: configure, _get_engine, _get_diagnostic_engine, _get_reconciliation_engine, _get_dex_reconciliation, _get_permission_engine, _get_env_store, _get_cross_source, _get_sync_store, _get_proposal_store, _get_report_store, _get_session_store
- Imports: __future__, fastapi, logging, time, typing
### `transports/api/cockpit_context_resolution_routes.py`
- Lines: 64. Doc: Cockpit routes for Context Resolution — Campaign 5.5.
- Classes: -
- Functions: _get_engine, configure, _build_router, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_core_routes.py`
- Lines: 2656. Doc: Cockpit core routes — extracted inline route handlers.
- Classes: -
- Functions: configure, get_organism, get_org_id, get_mesh_server, _build_routers
- Imports: __future__, asyncio, datetime, fastapi, fastapi.responses, hmac, json, logging
### `transports/api/cockpit_delegation_routes.py`
- Lines: 126. Doc: Cockpit routes for Delegation Runtime — Campaign 4.7.
- Classes: -
- Functions: _get_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_distributed_runtime_routes.py`
- Lines: 202. Doc: Cockpit distributed runtime routes — organism worker routing surface.
- Classes: -
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, re, typing
### `transports/api/cockpit_documentation_awareness_routes.py`
- Lines: 67. Doc: Cockpit routes for Documentation Awareness — Campaign 6.2.
- Classes: -
- Functions: _get_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_economy_routes.py`
- Lines: 448. Doc: Cockpit organism economy, recursion, advisor hierarchy, assimilation, snapshot,
- Classes: -
- Functions: configure, _build_router, _organism_economy, _organism_economy_records, _organism_task_profile, _organism_recursion, _organism_recursion_escalations, _organism_kill_switch, _organism_resume_switch, _organism_advisor_hierarchy, _organism_advisor_tree, _organism_overdue_advisors
- Imports: __future__, asyncio, fastapi, logging, typing
### `transports/api/cockpit_embodiment_routes.py`
- Lines: 107. Doc: Cockpit Embodiment routes — natural language intent surface.
- Classes: -
- Functions: configure, _get_embodiment, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_engineering_review_routes.py`
- Lines: 277. Doc: Cockpit engineering review routes — execution sessions and proof review.
- Classes: -
- Functions: configure, _get_executor, _get_coordinator, _get_builder, _validate_workspace_targets, _get_shared_planner, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_engineering_routes.py`
- Lines: 272. Doc: Cockpit engineering routes — autonomous planning and packetization.
- Classes: -
- Functions: configure, _get_planner, _get_generator, _get_gap_engine, _get_or_create_planner, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_entity_routes.py`
- Lines: 334. Doc: Cockpit entity and product routes — portfolio, departments, roles, companies
- Classes: -
- Functions: configure, _build_router, _entity_portfolio, _entity_departments, _entity_department_detail, _entity_roles, _entity_companies, _entity_company_detail, _upsert_company, _product_connections, _refresh_product_connections
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_execution_fabric_routes.py`
- Lines: 71. Doc: Cockpit routes for ExecutionFabricRuntime — Campaign 19.0.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_execution_graph_routes.py`
- Lines: 118. Doc: Cockpit Execution Graph Routes — API surface for lineage validation.
- Classes: -
- Functions: configure, _get_graph, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_execution_loop_routes.py`
- Lines: 485. Doc: Cockpit execution and loop routes — persistent loops + execution substrate.
- Classes: -
- Functions: configure, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_execution_routes.py`
- Lines: 281. Doc: Cockpit Execution Routes — canonical execution capability surface.
- Classes: -
- Functions: configure, _get_work_runtime, _get_telemetry_store, _get_approval_service, _get_event_spine, _safe_dict, _safe_list, _build_router
- Imports: __future__, fastapi, logging, time, typing
### `transports/api/cockpit_executive_routes.py`
- Lines: 144. Doc: Cockpit routes for Executive Intelligence — Campaign 14.3.
- Classes: -
- Functions: _get_resource_allocation, _get_tradeoff, _get_portfolio, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_goal_routes.py`
- Lines: 192. Doc: Cockpit routes for Goal Systems & Strategic Planning — Campaign 8.6.
- Classes: -
- Functions: _get_registry, _get_hierarchy, _get_outcome_tracking, _get_planning_engine, _get_alignment_engine, _get_drift_engine, configure, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_governance_routes.py`
- Lines: 146. Doc: Cockpit routes for Organism Governance — Campaign 15.4.
- Classes: -
- Functions: _get_governance, _get_coordination, _get_institutional_memory, _get_organism_portfolio, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_infrastructure_routes.py`
- Lines: 144. Doc: Cockpit Infrastructure Routes — API surface for infrastructure registry.
- Classes: -
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_intent_routes.py`
- Lines: 181. Doc: Cockpit Intent Routes — API surface for intent preservation runtime.
- Classes: -
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_knowledge_awareness_routes.py`
- Lines: 61. Doc: Cockpit routes for Knowledge Awareness — Campaign 6.4.
- Classes: -
- Functions: _get_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_learning_routes.py`
- Lines: 208. Doc: Cockpit routes for Learning Intelligence — Campaign 12.4.
- Classes: -
- Functions: _get_extraction, _get_patterns, _get_evolution, _get_portfolio, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_loop_coherence_routes.py`
- Lines: 79. Doc: Cockpit routes for Operating Loop Coherence Runtime — Campaign 4.3.
- Classes: -
- Functions: _get_coherence_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_memory_routes.py`
- Lines: 309. Doc: Cockpit routes for Decision Intelligence & Strategic Memory — Campaign 9.6.
- Classes: -
- Functions: _get_decision_registry, _get_assumption_tracking, _get_lineage_engine, _get_validity_engine, _get_memory_engine, _get_impact_engine, configure, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_meta_ide_context_routes.py`
- Lines: 71. Doc: Cockpit routes for Meta IDE Context — Campaign 17.1.
- Classes: ResolveIntentRequest
- Functions: _get_runtime, get_router
- Imports: __future__, logging, pydantic, typing
### `transports/api/cockpit_meta_ide_conv_routes.py`
- Lines: 177. Doc: Cockpit Meta IDE convergence routes — unified development surface.
- Classes: -
- Functions: configure, _get_ide, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_meta_ide_critical_routes.py`
- Lines: 354. Doc: Meta IDE critical path routes — planning, work packets, proof packages, trust.
- Classes: -
- Functions: configure, _build_router, _get_planner, _get_trust_engine, _compose, _list_plans, _get_plan, _approve_plan, _reject_plan, _execute_plan, _pending_steps, _list_deliverables
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_meta_ide_projection_loop_routes.py`
- Lines: 91. Doc: Cockpit Meta IDE Projection Loop Routes — API surface for build loop.
- Classes: -
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_meta_ide_routes.py`
- Lines: 261. Doc: Cockpit Meta IDE routes — engineering reality awareness.
- Classes: -
- Functions: configure, _get_engine, _get_roadmap, _repo_snap_to_dict, _phase_to_dict, _build_router, _safe_dict
- Imports: __future__, fastapi, logging, os, typing
### `transports/api/cockpit_migration_routes.py`
- Lines: 137. Doc: Cockpit Operator Migration routes — exit tracking and closure.
- Classes: -
- Functions: configure, _get_migration, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_mvp_readiness_routes.py`
- Lines: 65. Doc: Cockpit routes for MVP Readiness Runtime — Campaign 4.5.
- Classes: -
- Functions: _get_mvp_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_operating_loop_routes.py`
- Lines: 95. Doc: Cockpit routes for Operating Loop Runtime — Campaign 4.1.
- Classes: -
- Functions: _get_loop_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_operationalization_routes.py`
- Lines: 134. Doc: Cockpit Operationalization Routes — API surface for reusable capability artifacts.
- Classes: -
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_operator_experience_routes.py`
- Lines: 146. Doc: Cockpit operator experience routes — session, send, preview, status.
- Classes: -
- Functions: configure, _get_orchestrator, _build_router, _overview, _sessions, _session_detail, _status, _approvals, _send, _packet_preview, _propagation_preview, _topology_preview
- Imports: __future__, fastapi, json, logging, os, typing
### `transports/api/cockpit_operator_home_routes.py`
- Lines: 107. Doc: Cockpit Operator Home Routes — unified operator context API.
- Classes: -
- Functions: configure, _get_engine, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_operator_loop_routes.py`
- Lines: 2978. Doc: Cockpit operator loop routes — intent to plan to implementation to audit.
- Classes: -
- Functions: _safe_artifact_path, configure, _build_router, _get_queue, _get_runner, _get_sandbox_manager, _audit_log, _record_outcome_internal, _submit_intent, _generate_plan, _get_plan, _approve_plan
- Imports: __future__, fastapi, json, logging, os, re, time, typing
### `transports/api/cockpit_operator_presence_routes.py`
- Lines: 103. Doc: Cockpit Operator Presence Routes — presence and continuity API.
- Classes: -
- Functions: configure, _get_engine, _get_timeline, _get_device_tracker, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_operator_timeline_routes.py`
- Lines: 160. Doc: Cockpit operator timeline routes — unified chronological activity view.
- Classes: -
- Functions: configure, _build_router, _build_timeline_entry, _timeline, _receipt_detail
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_orchestrator_awareness_routes.py`
- Lines: 70. Doc: Cockpit routes for Orchestrator Awareness Runtime — Campaign 4.0.
- Classes: -
- Functions: _get_awareness, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_orchestrator_presence_routes.py`
- Lines: 68. Doc: Cockpit routes for Orchestrator Presence — Campaign 17.0.
- Classes: InterpretRequest
- Functions: _get_runtime, get_router
- Imports: __future__, logging, pydantic, typing
### `transports/api/cockpit_organism_map_routes.py`
- Lines: 231. Doc: Cockpit Organism Map Routes — unified topology for the organism map instrument.
- Classes: -
- Functions: configure, _get_node_registry, _get_service_graph, _get_state_engine, _get_failure_engine, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_organism_routes.py`
- Lines: 706. Doc: Cockpit organism core routes — status, agents, deliverables, events, tick,
- Classes: -
- Functions: configure, _build_router, _organism_status, _organism_agents, _organism_deliverables, _organism_events, _organism_tick_status, _organism_leverage, _organism_metrics, _organism_bottlenecks, _organism_intelligence, _organism_intelligence_leverage
- Imports: __future__, asyncio, dataclasses, fastapi, logging, time, typing
### `transports/api/cockpit_prediction_routes.py`
- Lines: 200. Doc: Cockpit routes for Prediction Intelligence — Campaign 13.3.
- Classes: -
- Functions: _get_trajectory, _get_scenarios, _get_portfolio, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_presence_routes.py`
- Lines: 570. Doc: Cockpit presence routes — activation, session, command, capabilities.
- Classes: -
- Functions: configure, _get_dep, _detect_env, _load_continuity_state, _load_resume_summary, _load_pending_approvals, _log_presence_event, _activate, _current, _command, _capabilities, _voice_health
- Imports: __future__, datetime, fastapi, json, logging, os, typing, uuid
### `transports/api/cockpit_production_routes.py`
- Lines: 329. Doc: Cockpit production routes — software production organism surface.
- Classes: -
- Functions: configure, _get_ops, _get_workforce, _get_review, _get_compounding, _get_factory, _get_source_truth, _unavailable, _snapshot, _phase, _active, _workforce_summary
- Imports: __future__, fastapi, logging, time, typing
### `transports/api/cockpit_projection_integration_routes.py`
- Lines: 88. Doc: Cockpit Projection Integration Routes — API surface for projection audit.
- Classes: -
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_projection_routes.py`
- Lines: 93. Doc: Cockpit routes for Gate 10 — Projection Consumption Layer.
- Classes: -
- Functions: configure, _get_dep, _port, _validate_projection_name, list_projections, projection_summary, audit_all_projections, audit_projection, get_projection, register_projection
- Imports: __future__, fastapi, os, sys, typing
### `transports/api/cockpit_propagation_graph_routes.py`
- Lines: 217. Doc: Cockpit propagation graph routes — graph, impact, plan, execute, results.
- Classes: -
- Functions: configure, _get_graph, _get_builder, _get_analyzer, _get_planner, _get_executor, _build_router, _overview, _summary, _nodes, _edges, _change_events
- Imports: __future__, fastapi, json, logging, os, typing
### `transports/api/cockpit_reality_graph_routes.py`
- Lines: 104. Doc: Cockpit routes for Reality Graph — Campaign 5.0.
- Classes: -
- Functions: _get_graph, configure, _build_router, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_reality_intelligence_routes.py`
- Lines: 221. Doc: Cockpit reality intelligence routes — read-only reality retrieval.
- Classes: -
- Functions: configure, _get_engine, _result_to_dict, _build_router
- Imports: __future__, fastapi, logging, os, typing
### `transports/api/cockpit_reality_model_routes.py`
- Lines: 376. Doc: Cockpit reality model routes — canonical patterns, instance observations, simulation.
- Classes: -
- Functions: configure, _get_canonical, _get_instance, _get_simulation, _build_router, _status, _canonical_patterns, _canonical_pattern_detail, _canonical_search, _canonical_domains, _canonical_stats, _canonical_relationships
- Imports: __future__, fastapi, logging, os, typing
### `transports/api/cockpit_repository_awareness_routes.py`
- Lines: 70. Doc: Cockpit routes for Repository Awareness — Campaign 6.1.
- Classes: -
- Functions: _get_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_rooms_routes.py`
- Lines: 1897. Doc: Conference Rooms API — servers, categories, channels, messages, threads, forums,
- Classes: CreateServerReq, UpdateServerReq, CreateCategoryReq, UpdateCategoryReq, CreateChannelReq, UpdateChannelReq, SendMessageReq, EditMessageReq
- Functions: _push_room_event, _store_path, _load, _save, _now, _uid, _audit, _verify_guest_token, _user_id, _display_name, _get_member, _effective_permissions
- Imports: __future__, datetime, fastapi, json, jwt, logging, os, pathlib
### `transports/api/cockpit_runtime_awareness_routes.py`
- Lines: 60. Doc: Cockpit routes for Runtime Awareness — Campaign 6.3.
- Classes: -
- Functions: _get_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_runtime_surface_routes.py`
- Lines: 164. Doc: Cockpit runtime surface routes — session lifecycle, events, adapters.
- Classes: -
- Functions: configure, _get_manager, _build_router, _overview, _sessions, _session_detail, _session_events, _adapters, _create_session, _start_session, _inject_message, _stop_session
- Imports: __future__, fastapi, json, logging, typing
### `transports/api/cockpit_screen_awareness_routes.py`
- Lines: 146. Doc: Cockpit Screen Awareness Routes — operator visual workspace context.
- Classes: -
- Functions: configure, _get_engine, _get_resolver, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_self_build_routes.py`
- Lines: 192. Doc: Cockpit self-build queue routes — summary, items, next, blocked, ready,
- Classes: -
- Functions: configure, _get_queue, _get_roadmap, _build_router, _self_build_overview, _self_build_summary, _self_build_items, _self_build_next, _self_build_blocked, _self_build_ready, _self_build_item_detail, _roadmap_overview
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_self_improvement_routes.py`
- Lines: 450. Doc: Cockpit self-improvement loop routes — outcome assimilation, verification,
- Classes: -
- Functions: configure, _build_router, _get_queue, _get_instance_model, _get_canonical_model, _get_cadence, _get_self_build_queue, _improvement_log_path, _log_improvement_event, _improvement_status, _cadence_status, _recent_outcomes
- Imports: __future__, fastapi, json, logging, os, time, typing, uuid
### `transports/api/cockpit_service_graph_routes.py`
- Lines: 109. Doc: Cockpit Service Graph Routes — read-only service dependency API.
- Classes: -
- Functions: configure, _get_registry, _get_engine, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_session_machine_routes.py`
- Lines: 64. Doc: Cockpit routes for SessionMachineRuntime — Campaign 19.2.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_session_routes.py`
- Lines: 81. Doc: Cockpit routes for Workstation Session Runtime — Campaign 4.4.
- Classes: -
- Functions: _get_session_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_spine_router.py`
- Lines: 519. Doc: Cockpit spine router — GovernedExecutionSpine, Journal, MutationRegistry,
- Classes: -
- Functions: configure, _build_router, _spine_status, _spine_pending, _spine_active, _spine_completed, _spine_lifecycle, _spine_approve, _spine_reject, _spine_retry, _journal_status, _journal_recent
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_state_authority_routes.py`
- Lines: 100. Doc: Cockpit State Authority Routes — read-only state domain authority API.
- Classes: -
- Functions: configure, _get_registry, _get_coherence, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_strategic_routes.py`
- Lines: 188. Doc: Cockpit routes for Strategic Context — Campaign 7.6.
- Classes: -
- Functions: _get_strategic_context, _get_priority_engine, _get_risk_engine, _get_recommendation_engine, _get_drift_engine, _get_brief_runtime, configure, _build_router, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_umh_node_routes.py`
- Lines: 101. Doc: Cockpit UMH Node Topology Routes — read-only node topology API.
- Classes: -
- Functions: configure, _get_registry, _get_coherence, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_unified_approval_routes.py`
- Lines: 88. Doc: Cockpit routes for Unified Approval Runtime — Campaign 4.2.
- Classes: -
- Functions: _get_approval_runtime, configure, _build_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_unified_execution_routes.py`
- Lines: 94. Doc: Unified Execution Surface Routes — single API surface across all execution subsystems.
- Classes: ApproveRequest, RejectRequest
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, pydantic, typing
### `transports/api/cockpit_unified_workstation_routes.py`
- Lines: 64. Doc: Cockpit routes for UnifiedWorkstationRuntime — Campaign 18.0.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_universal_work_routes.py`
- Lines: 272. Doc: Cockpit universal work queue routes — packets, workcells, roles, knowledge.
- Classes: -
- Functions: configure, _get_queue, _get_workcells, _get_role_contracts, _get_knowledge_registry, _build_router, _overview, _summary, _packets, _packet_detail, _next_best, _by_domain
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_validation_routes.py`
- Lines: 310. Doc: Cockpit validation routes — capability compounding proof + competitive matrix surface.
- Classes: -
- Functions: configure, register_validation_routes, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_visual_attention_routes.py`
- Lines: 51. Doc: Cockpit routes for AttentionVisionRuntime — Campaign 21.3.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_visual_awareness_routes.py`
- Lines: 65. Doc: Cockpit routes for ScreenAwarenessRuntime — Campaign 21.0.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_visual_context_routes.py`
- Lines: 58. Doc: Cockpit routes for VisualContextRuntime — Campaign 21.2.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_visual_environment_routes.py`
- Lines: 51. Doc: Cockpit routes for EnvironmentAwarenessRuntime — Campaign 21.1.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_visual_ops_routes.py`
- Lines: 79. Doc: Cockpit routes for VisualOperationsRuntime — Campaign 21.4.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_voice_ingress_routes.py`
- Lines: 43. Doc: Cockpit routes for VoiceIngressRuntime — Campaign 20.0.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_voice_ops_routes.py`
- Lines: 59. Doc: Cockpit routes for VoiceOperationsRuntime — Campaign 20.4.
- Classes: ProcessRequest
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, pydantic, typing
### `transports/api/cockpit_voice_output_routes.py`
- Lines: 36. Doc: Cockpit routes for VoiceOutputRuntime — Campaign 20.3.
- Classes: -
- Functions: _get_runtime, get_router
- Imports: __future__, fastapi, typing
### `transports/api/cockpit_voice_routes.py`
- Lines: 90. Doc: Cockpit Voice Query Routes — context-grounded query resolution.
- Classes: -
- Functions: configure, _get_engine, _build_router
- Imports: __future__, collections, fastapi, logging, time, typing
### `transports/api/cockpit_voice_session_routes.py`
- Lines: 73. Doc: Cockpit routes for VoiceSessionManager — Campaign 20.1.
- Classes: SessionStartRequest
- Functions: _get_manager, get_router
- Imports: __future__, fastapi, pydantic, typing
### `transports/api/cockpit_work_center_routes.py`
- Lines: 163. Doc: Cockpit Work Center Routes — unified API for governed work lifecycle.
- Classes: -
- Functions: configure, _get_runtime, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_work_intelligence_routes.py`
- Lines: 200. Doc: Cockpit routes for Work Intelligence — Campaign 11.3.
- Classes: -
- Functions: _get_readiness, _get_delegation, _get_portfolio, configure, get_router
- Imports: __future__, logging, typing
### `transports/api/cockpit_workspace_observation_routes.py`
- Lines: 123. Doc: Cockpit workspace observation routes — live engineering runtime observation.
- Classes: -
- Functions: configure, _get_engine, _get_probe, _run_observation, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_workspace_routes.py`
- Lines: 637. Doc: Cockpit workspace routes — file browser, diff, test results, logs, proof, health.
- Classes: -
- Functions: configure, _build_router, _browse_dir, _read_file, _write_file, _run_git, _git_status, _git_diff, _git_diff_file, _test_results, _execution_logs, _proof_artifacts
- Imports: __future__, datetime, fastapi, json, logging, os, pathlib, platform
### `transports/api/cockpit_workspace_topology_routes.py`
- Lines: 108. Doc: Cockpit routes for Workspace Topology (Phase 27).
- Classes: -
- Functions: configure, _get_engine, _build_router
- Imports: __future__, fastapi, logging, typing
### `transports/api/cockpit_workstation_control_routes.py`
- Lines: 648. Doc: Cockpit workstation control routes — execution pause/resume/stop with environment awareness.
- Classes: -
- Functions: configure, _get_manager, _build_router, _resolve_adapter, _execution_pause, _execution_resume, _execution_stop, _execution_status, _read_mesh_snapshot, _read_vps_node, _workstation_nodes, _workstation_resume
- Imports: __future__, datetime, fastapi, logging, os, platform, typing
### `transports/api/cockpit_workstation_presence_routes.py`
- Lines: 86. Doc: Cockpit routes for Workstation Presence — Campaign 17.2.
- Classes: PanelUpdate, DeviceUpdate, ContextUpdate
- Functions: _get_runtime, get_router
- Imports: __future__, logging, pydantic, typing
### `transports/api/computer_use.py`
- Lines: 188. Doc: Execution substrate API — governed multi-layer agent execution.
- Classes: StartRequest, SlotRequest
- Functions: start_execution, stop_execution, pause_execution, resume_execution, get_status, get_log, preview_authority, start_container, stop_container, list_containers
- Imports: __future__, asyncio, fastapi, logging, pydantic, typing
### `transports/api/distribution.py`
- Lines: 96. Doc: Distribution API — channel status, intake, approval, and first-boot endpoints.
- Classes: ChannelIngestRequest, ApprovalResponse
- Functions: wire_pipeline, channel_ingest, receive_approval, channel_status, distribution_stats, recent_events, first_boot_status, complete_first_boot
- Imports: __future__, fastapi, nodes.distribution.distributor, nodes.distribution.first_boot, pydantic, typing
### `transports/api/event_bus.py`
- Lines: 73. Doc: Event bus — pub/sub backbone for the substrate's internal communication.
- Classes: Event, EventBus
- Functions: -
- Imports: __future__, asyncio, collections, datetime, logging, pydantic, typing, uuid
### `transports/api/execcoord_routes.py`
- Lines: 225. Doc: Phase 13: Execution Coordinator route handlers.
- Classes: -
- Functions: _get_execution_coordinator, _audit_log, execcoord_state, execcoord_queue, execcoord_active, execcoord_awaiting, execcoord_history, execcoord_lifecycle, execcoord_executors, execcoord_create, execcoord_approve, execcoord_deny
- Imports: __future__, fastapi, logging
### `transports/api/executor_routes.py`
- Lines: 253. Doc: Phase 14: Executor Runtime route handlers.
- Classes: -
- Functions: _get_executor_runtime, _audit_log, executor_state, executor_requests_all, executor_active, executor_results_all, executor_failures, executor_history, executor_lifecycle, executor_types, executor_create, executor_run
- Imports: __future__, fastapi, logging
### `transports/api/invariants.py`
- Lines: 150. Doc: Invariant enforcement — validates substrate laws at every transition point.
- Classes: InvariantViolation, InvariantChecker
- Functions: -
- Imports: __future__, dataclasses, logging, substrate.foundation.laws, substrate.types, typing
### `transports/api/operator.py`
- Lines: 569. Doc: UMH Operator Workstation API — FastAPI backend for the operator UI.
- Classes: -
- Functions: verify_api_key, health, _load_memories, knowledge_entries, knowledge_stats, knowledge_search, system_costs, system_containers, system_ingestion_status, chat, ingest_trigger, _generate_tts
- Imports: asyncio, datetime, dotenv, fastapi, fastapi.middleware.cors, fastapi.responses, fastapi.staticfiles, json
### `transports/api/organism_bridge.py`
- Lines: 2319. Doc: Organism runtime bridge — exposes organism subsystem state and actions
- Classes: -
- Functions: _emit, _get_daemon, _get_economy, _get_governor, _get_advisors, _get_approval_store, _get_homeostasis, _get_observer, _get_store, _get_leverage, _get_handoff_router, _snapshot
- Imports: dotenv, json, logging, os, substrate.execution.cpu_gate, sys
### `transports/api/runtime.py`
- Lines: 91. Doc: Control plane runtime — the top-level orchestrator that wires everything together.
- Classes: SubstrateRuntime
- Functions: -
- Imports: __future__, datetime, logging, substrate.foundation.identity, substrate.foundation.laws, substrate.foundation.perspective, substrate.types, transports.api.event_bus
### `transports/api/runtime_state_routes.py`
- Lines: 122. Doc: Runtime State API routes — read-only workstation awareness.
- Classes: -
- Functions: _get_registry, runtime_state, runtime_snapshot_latest, runtime_executions, runtime_processes, runtime_worktrees, runtime_containers, runtime_history
- Imports: __future__, fastapi, logging
### `transports/api/signal_factory.py`
- Lines: 33. Doc: API signal factory — converts HTTP requests to SignalEnvelopes.
- Classes: -
- Functions: http_request_to_signal
- Imports: __future__, substrate.types, typing
### `transports/api/signal_router.py`
- Lines: 209. Doc: Signal router — enforces the legal processing pathway for all signals.
- Classes: SignalRouter
- Functions: -
- Imports: __future__, datetime, logging, substrate.types, transports.api.event_bus, transports.api.invariants, uuid
### `transports/api/telemetry_routes.py`
- Lines: 134. Doc: Phase 15B: Execution Telemetry route handlers.
- Classes: -
- Functions: _get_emitter, telemetry_latest, telemetry_for_execution, telemetry_stream
- Imports: __future__, asyncio, fastapi, json, logging, starlette.responses, time
### `transports/api/voice.py`
- Lines: 96. Doc: Voice session API — exposes the voice pipeline loop over HTTP.
- Classes: StartRequest, ProcessRequest
- Functions: wire_pipeline, start_session, stop_session, process_text, session_status
- Imports: __future__, fastapi, logging, pydantic, substrate.execution.voice.session, typing
### `transports/api/webhooks/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `transports/api/webhooks/calendly_webhook.py`
- Lines: 435. Doc: -
- Classes: -
- Functions: _log_calendly_outcome, _detect_venture_from_event, verify_signature, send_telegram, find_lead_by_name_or_email, move_pipeline_card, update_lead_file, update_notion_lead_stage, calendly_webhook, health
- Imports: datetime, dotenv, flask, glob, hashlib, hmac, json, os
### `transports/api/workstation.py`
- Lines: 135. Doc: Workstation API — workstation mode execution, state, and health.
- Classes: WorkstationExecRequest, WorkstationModeRequest
- Functions: workstation_execute, get_mode, set_mode, get_state, workstation_health, workstation_stats
- Imports: __future__, asyncio, fastapi, logging, pydantic, substrate.execution.workers.workstation.workstation_contracts_v1, substrate.execution.workers.workstation.workstation_execution_orchestrator_v1, substrate.governance.security
### `transports/channels/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `transports/channels/channel.py`
- Lines: 453. Doc: EOS Channel System
- Classes: ChannelType, Message, ChannelConfig, Channel, DiscordChannel, TelegramChannel, WebhookChannel, ConsoleChannel
- Functions: get_channel_router
- Imports: abc, dataclasses, enum, json, logging, os, typing, urllib.parse
### `transports/discord/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `transports/discord/approval_bridge.py`
- Lines: 202. Doc: Approval bridge — Discord interactive buttons for governance approvals.
- Classes: GovernanceApprovalView
- Functions: set_bot, set_channel, _format_approval_message, handle_approval_alert
- Imports: __future__, asyncio, discord, logging, os, typing
### `transports/discord/discord_utils.py`
- Lines: 173. Doc: discord_utils — single source of truth for all Discord posting from EOS.
- Classes: -
- Functions: chunk_message, post_to_webhook, post_to_channel
- Imports: dotenv, os, time
### `transports/discord/interface_adapter_v1.py`
- Lines: 504. Doc: Discord Interface Adapter v1.
- Classes: DiscordInterfaceAdapter
- Functions: _log, _log_error, load_config, build_work_packet_for_router, build_work_packet, write_work_packet, poll_for_proof, format_router_result, format_proof_summary, main
- Imports: __future__, adapters.adapter_engine.adapter_registry_contracts, asyncio, datetime, discord, json, nodes.environments.windows_desktop_request_builder, os
### `transports/discord/signal_factory.py`
- Lines: 76. Doc: Discord signal factory -- converts Discord messages to SignalEnvelopes.
- Classes: -
- Functions: message_to_signal
- Imports: __future__, substrate.types, typing
### `transports/discord/spine_integration_v1.py`
- Lines: 277. Doc: Discord Spine Integration v1.
- Classes: SpineExecutionConfig, SpineRoutedResult
- Functions: _log, build_spine_infrastructure, execute_spine_command, format_spine_result
- Imports: __future__, dataclasses, datetime, json, os, pathlib, substrate.execution.runtime.live_local_runtime_execution_v1, substrate.execution.runtime.local_runtime_supervisor_v1
### `transports/node_mesh/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `transports/node_mesh/config.py`
- Lines: 86. Doc: Node mesh configuration loader.
- Classes: NodeTokenEntry, MeshConfig
- Functions: load_mesh_config
- Imports: __future__, dataclasses, logging, pathlib, typing
### `transports/node_mesh/integration/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `transports/node_mesh/integration/handlers.py`
- Lines: 149. Doc: Node mesh capability handler — proxies execution requests to remote nodes over WebSocket.
- Classes: NodeCapabilityHandler
- Functions: _parse_risk_class, _parse_category
- Imports: __future__, json, logging, substrate.governance.risk_classes, substrate.sockets.envelopes, substrate.sockets.protocols, substrate.types, threading
### `transports/node_mesh/integration/manifest.py`
- Lines: 20. Doc: Build an IntegrationManifest for a connected mesh node.
- Classes: -
- Functions: build_node_manifest
- Imports: __future__, substrate.sockets.registry, transports.node_mesh.integration.handlers, transports.node_mesh.integration.outcomes, transports.node_mesh.integration.signals, transports.node_mesh.integration.types
### `transports/node_mesh/integration/outcomes.py`
- Lines: 54. Doc: Node mesh outcome receiver — delivers outcomes to remote nodes.
- Classes: NodeOutcomeReceiver
- Functions: -
- Imports: __future__, asyncio, json, logging, substrate.sockets.envelopes, typing
### `transports/node_mesh/integration/signals.py`
- Lines: 58. Doc: Node mesh signal emitter — declares signal types a remote node can emit.
- Classes: NodeSignalEmitter
- Functions: -
- Imports: __future__, substrate.governance.risk_classes, substrate.sockets.protocols, substrate.types
### `transports/node_mesh/integration/types.py`
- Lines: 67. Doc: Pure data types for the node mesh — no transport dependencies.
- Classes: NodeCapability, ConnectedNode
- Functions: -
- Imports: __future__, dataclasses, datetime, time, typing
### `transports/node_mesh/metrics_buffer.py`
- Lines: 126. Doc: Per-node ring buffer for telemetry metrics — bypasses the full pipeline.
- Classes: MetricsSnapshot, MetricsBuffer
- Functions: -
- Imports: __future__, collections, dataclasses, datetime, json, logging, pathlib, threading
### `transports/node_mesh/registry.py`
- Lines: 80. Doc: Node registry — tracks connected mesh nodes and their state.
- Classes: NodeRegistry
- Functions: -
- Imports: __future__, json, logging, pathlib, threading, time, transports.node_mesh.integration.types, typing
### `transports/node_mesh/run.py`
- Lines: 158. Doc: Standalone launcher for the UMH Node Mesh server.
- Classes: -
- Functions: _validate_relay_port, _ensure_docker_relay_access, main
- Imports: __future__, json, logging, os, signal, substrate.execution.executor, substrate.sockets.capability_socket, substrate.sockets.outcome_socket
### `transports/node_mesh/server.py`
- Lines: 907. Doc: Node Mesh WebSocket server — manages node connections and lifecycle.
- Classes: NodeMeshServer
- Functions: -
- Imports: __future__, asyncio, json, logging, os, substrate.execution.executor, substrate.sockets.capability_socket, substrate.sockets.envelopes
### `transports/presence/__init__.py`
- Lines: 1. Doc: -
- Classes: -
- Functions: -
- Imports: -
### `transports/presence/handlers/__init__.py`
- Lines: 6. Doc: Discord bot handler modules.
- Classes: -
- Functions: -
- Imports: -
### `transports/presence/handlers/cc_command_handler.py`
- Lines: 564. Doc: Inline command handlers for Discord on_message.
- Classes: -
- Functions: handle_followup, handle_travel, handle_nomeetings, handle_confirm_event, handle_meetingroi, handle_competitive, handle_documents, handle_audit, handle_stakeholders, handle_add_stakeholder, handle_calendar_write, try_inline_commands
- Imports: datetime, json, os, sys, zoneinfo
### `transports/presence/handlers/intent_handler.py`
- Lines: 438. Doc: Intent classification and gateway routing.
- Classes: -
- Functions: build_request, run_gateway
- Imports: datetime, json, os, pathlib, re, substrate.observability.error_recorder, sys, uuid
### `transports/presence/handlers/pipeline_handler.py`
- Lines: 139. Doc: Pipeline update detection and Notion stage updates.
- Classes: -
- Functions: detect_pipeline_update, handle_pipeline_update
- Imports: os, re, sys
### `transports/presence/handlers/report_handlers.py`
- Lines: 22. Doc: Report handler functions — backward-compat re-export.
- Classes: -
- Functions: -
- Imports: transports.presence.handlers.reports
### `transports/presence/handlers/reports/__init__.py`
- Lines: 32. Doc: Report handler package — re-exports all handler functions.
- Classes: -
- Functions: -
- Imports: .adapter, .capability, .constitution, .continuity, .economics, .epistemic, .federation, .governance_intelligence
### `transports/presence/handlers/reports/_common.py`
- Lines: 54. Doc: Shared imports and helpers for report handler modules.
- Classes: -
- Functions: _log, _wait_for_founder_confirmation
- Imports: __future__, asyncio, datetime, json, logging, os, pathlib, sys
### `transports/presence/handlers/reports/adapter.py`
- Lines: 221. Doc: Adapter report handler.
- Classes: -
- Functions: _handle_adapter_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/capability.py`
- Lines: 228. Doc: Capability report handler.
- Classes: -
- Functions: _handle_capability_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/constitution.py`
- Lines: 322. Doc: Constitution report handler.
- Classes: -
- Functions: _handle_constitution_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/continuity.py`
- Lines: 286. Doc: Continuity report handler.
- Classes: -
- Functions: _handle_continuity_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/economics.py`
- Lines: 348. Doc: Economics report handler.
- Classes: -
- Functions: _handle_economics_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/epistemic.py`
- Lines: 273. Doc: Epistemic report handler.
- Classes: -
- Functions: _handle_epistemic_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/federation.py`
- Lines: 324. Doc: Federation report handler.
- Classes: -
- Functions: _handle_federation_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/governance_intelligence.py`
- Lines: 299. Doc: Governance intelligence report handler.
- Classes: -
- Functions: _handle_governance_intelligence_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/identity.py`
- Lines: 289. Doc: Identity report handler.
- Classes: -
- Functions: _handle_identity_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/orchestration.py`
- Lines: 255. Doc: Orchestration report handler.
- Classes: -
- Functions: _handle_orchestration_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/resilience.py`
- Lines: 170. Doc: Resilience report handler.
- Classes: -
- Functions: _handle_resilience_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/strategy.py`
- Lines: 372. Doc: Strategy report handler.
- Classes: -
- Functions: _handle_strategy_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/reports/telos.py`
- Lines: 306. Doc: Telos report handler.
- Classes: -
- Functions: _handle_telos_report
- Imports: ._common, __future__, typing
### `transports/presence/handlers/substrate_command_handler.py`
- Lines: 940. Doc: Substrate command handler for the live Discord bot.
- Classes: -
- Functions: _log, _get_vps_commit_hash, _get_origin_commit_hash, _get_command_surface_hash, _get_router_contract_hash, _file_hash, _container_id, _is_stale_runtime, _ensure_infrastructure, is_substrate_command, handle_substrate_command, _handle_version
- Imports: __future__, adapters.adapter_engine.adapter_registry_contracts, asyncio, datetime, hashlib, json, os, pathlib
### `transports/presence/handlers/voice_handler.py`
- Lines: 23. Doc: Voice handler — skeleton module.
- Classes: -
- Functions: -
- Imports: -
### `umh/vision_relay.py`
- Lines: 2624. Doc: Vision relay server — bridges Beast camera frames to cockpit viewers.
- Classes: -
- Functions: _check_origin, _emit_vision_event, _authority_has_decayed, _claim_authority, _release_authority, _check_authority_for_command, _record_pipeline_metrics, _get_pipeline_metrics, _register_camera, _update_camera_frame, _get_broadcast_lock, _is_fault_active
- Imports: __future__, asyncio, base64, json, logging, os, sys, time
### `umh/voice_server.py`
- Lines: 397. Doc: Cockpit Voice Server — pure STT + TTS bridge for DEX conversations.
- Classes: -
- Functions: _transcribe_groq, _transcribe_local, transcribe, _tts_kokoro, _tts_espeak, generate_tts, prepare_for_speech, compute_audio_level, save_wav, handle_voice, main
- Imports: __future__, asyncio, dotenv, json, logging, math, os, pathlib

## TypeScript / Frontend Index (Condensed)
### `cockpit/src/main/index.ts`
- Lines: 268. Definitions/exports: const WINDOW_MODES = ['maximized', 'large-fab', 'medium-fab', 'small-fab', 'invisible'] as const; const FAB_SIZES: Record<string, { width: number; height: number }> = {; function createWindow(): void {; function spawnVoiceServer(): void {; const voicePath = join(process.env['UMH_ROOT'] || '/opt/OS', 'umh', 'voice_server.py'); function spawnVisionRelay(): void {; const visionPath = join(process.env['UMH_ROOT'] || '/opt/OS', 'umh', 'vision_relay.py'); const entries = await readdir(dirPath, { withFileTypes: true })
### `cockpit/src/preload/index.ts`
- Lines: 34. Definitions/exports: -
### `cockpit/src/renderer/App.tsx`
- Lines: 125. Definitions/exports: const hasClerk = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY; function TokenGate({ children }: { children: ReactNode }) {; const { getToken } = useAuth(); const ref = useRef(getToken); function AuthenticatedApp() {; const boot = useBootstrapStore((s) => s.boot); const loadHistory = useChatStore((s) => s.loadHistory); const startPolling = useChatStore((s) => s.startPolling)
### `cockpit/src/renderer/api/broadcast-ws.ts`
- Lines: 101. Definitions/exports: function getBroadcastUrl(): string {; const isLocalhost =; const isElectron = Boolean((window as Record<string, unknown>).cockpit); const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'; const BROADCAST_URL = getBroadcastUrl(); const clerkToken = await getClerkToken(); const wsToken = getWsToken(); export interface BroadcastHealthMetrics {
### `cockpit/src/renderer/api/client.ts`
- Lines: 99. Definitions/exports: const API_BASE = import.meta.env.VITE_API_URL as string || '/api/umh'; export class ApiError extends Error {; export function setTokenGetter(fn: () => Promise<string | null>) {; export function getApiKey(): string {; export function getWsToken(): string {; export async function getClerkToken(): Promise<string | null> {; const t = await _getToken(); const t = await window.Clerk.session.getToken({ skipCache: true })
### `cockpit/src/renderer/api/device-presence.ts`
- Lines: 60. Definitions/exports: export interface DeviceRegistration {; export interface DeviceSession {; export async function registerDevice(session: DeviceRegistration): Promise<void> {; export async function heartbeatDevice(; export async function disconnectDevice(sessionId: string): Promise<void> {; export async function getActiveSessions(): Promise<DeviceSession[]> {; const res = await fetchApi<{ sessions: DeviceSession[] }>('/device/sessions')
### `cockpit/src/renderer/api/tts-playback-controller.ts`
- Lines: 282. Definitions/exports: const log = (stage: string, ...args: unknown[]) =>; export type PlaybackStatus = 'idle' | 'unlocking' | 'playing' | 'error'; export interface TtsPlaybackState {; type StateListener = (state: TtsPlaybackState) => void; const _listeners: StateListener[] = []; function _notify(): void {; export function onPlaybackStateChange(fn: StateListener): () => void {; const idx = _listeners.indexOf(fn)
### `cockpit/src/renderer/api/vision-ws.ts`
- Lines: 812. Definitions/exports: function getVisionUrl(): string {; const isLocalhost =; const isElectron = Boolean((window as Record<string, unknown>).cockpit); const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'; const VISION_URL = getVisionUrl(); const log = (stage: string, ...args: unknown[]) =>; export interface CameraPreset {; export type PtzDirection =
### `cockpit/src/renderer/api/voice-controller.ts`
- Lines: 556. Definitions/exports: const PENDING_RESPONSE_TIMEOUT_MS = 30_000; const NO_TRANSCRIPT_TIMEOUT_MS = 10_000; const MAX_RECORDING_MS = 30_000; const TTS_GENERATE_TIMEOUT_MS = 15_000; const log = (stage: string, ...args: unknown[]) =>; function clearAllTimers(): void {; function _dispatchCommittedTurn(turn: VoiceTurnState): void {; const text = turn.assembledText
### `cockpit/src/renderer/api/voice-turn-assembler.ts`
- Lines: 289. Definitions/exports: const log = (stage: string, ...args: unknown[]) =>; export interface VoiceTranscriptSegment {; export type VoiceTurnStatus = 'active' | 'assembling' | 'committed' | 'cancelled'; export interface VoiceTurnState {; function _isMobile(): boolean {; const ua = navigator.userAgent || ''; export function getSilenceTimeoutMs(): number {; export function createTurn(): VoiceTurnState {
### `cockpit/src/renderer/api/voice-ws.ts`
- Lines: 219. Definitions/exports: function getVoiceUrl(): string {; const isLocalhost =; const isElectron = Boolean((window as Record<string, unknown>).cockpit); const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'; const VOICE_URL = getVoiceUrl(); const TARGET_SAMPLE_RATE = 16000; const CHUNK_SIZE = 4096; const log = (stage: string, ...args: unknown[]) =>
### `cockpit/src/renderer/api/websocket.ts`
- Lines: 171. Definitions/exports: type WsHandler = (data: Record<string, unknown>) => void; export class WsClient {; const data = JSON.parse(event.data as string) as Record<string, unknown>; const type = (data.type as string) || 'message'; const existing = this.handlers.get(type) || []; const existing = this.handlers.get(type) || []; const staleMs = Date.now() - this._lastMessageAt
### `cockpit/src/renderer/components/ActionRequired.tsx`
- Lines: 118. Definitions/exports: export interface ActionItem {; const SEVERITY_COLOR: Record<string, string> = {; const TYPE_ICON: Record<string, string> = {; interface ActionRequiredProps {; export function ActionRequired({ items, loading }: ActionRequiredProps) {; export function buildActionItems(; const items: ActionItem[] = []; const approvalCount = summary.what_needs_approval?.count ?? summary.what_needs_approval?.items?.length ?? 0
### `cockpit/src/renderer/components/AgentCard.tsx`
- Lines: 111. Definitions/exports: interface AgentCardProps {; const STATUS_COLORS: Record<string, string> = {; export function AgentCard({; const statusColor = STATUS_COLORS[status] || 'var(--color-text-tertiary)'
### `cockpit/src/renderer/components/CallOverlay.tsx`
- Lines: 70. Definitions/exports: export function CallOverlay() {; const state = useVoiceSessionStore((s) => s.state); const isMuted = useVoiceSessionStore((s) => s.isMuted); const isDeafened = useVoiceSessionStore((s) => s.isDeafened); const activeChannelId = useVoiceSessionStore((s) => s.activeChannelId); const toggleMute = useVoiceSessionStore((s) => s.toggleMute); const toggleDeafen = useVoiceSessionStore((s) => s.toggleDeafen); const disconnect = useVoiceSessionStore((s) => s.disconnect)
### `cockpit/src/renderer/components/CameraController.tsx`
- Lines: 1400. Definitions/exports: type QualityMode,; type MotionState,; type CameraPreset,; type FrameFreshness,; const QUALITY_LABELS: Record<QualityMode, string> = {; const QUALITY_DESCRIPTIONS: Record<QualityMode, string> = {; function nextMotionId(): string {; const MOTION_UPDATE_INTERVAL_MS = 33
### `cockpit/src/renderer/components/CameraPreview.tsx`
- Lines: 202. Definitions/exports: export function CameraPreview() {; const {; const overlays = useVisionStore((s) => s.overlays); const overlayVisible = useVisionStore((s) => s.overlayVisible); const width = useVisionStore((s) => s.width); const height = useVisionStore((s) => s.height); const poppedOut = useVisionStore((s) => s.poppedOut); const { openPopout } = useVisionPopout()
### `cockpit/src/renderer/components/ChannelList.tsx`
- Lines: 91. Definitions/exports: export interface Conversation {; interface ConversationListProps {; function timeAgo(ts: string): string {; const diff = Date.now() - new Date(ts).getTime(); const mins = Math.floor(diff / 60000); const hrs = Math.floor(mins / 60); const INTENT_ICON: Record<string, string> = {; export function ConversationList({ conversations, selected, onSelect }: ConversationListProps) {
### `cockpit/src/renderer/components/ChannelView.tsx`
- Lines: 114. Definitions/exports: export interface A2AMessage {; interface ConversationViewProps {; function formatTime(ts: string): string {; const INTENT_LABEL: Record<string, { label: string; color: string }> = {; export function ConversationView({ conversationId, messages, participants }: ConversationViewProps) {; const bottomRef = useRef<HTMLDivElement>(null); const isSelf = m.direction === 'outbound'; const intentInfo = INTENT_LABEL[m.intent]
### `cockpit/src/renderer/components/CommandPalette.tsx`
- Lines: 179. Definitions/exports: interface Command {; export function CommandPalette() {; const aiName = useConfigStore((s) => s.aiName); const [open, setOpen] = useState(false); const [query, setQuery] = useState(''); const [jarvisResponse, setJarvisResponse] = useState(''); const inputRef = useRef<HTMLInputElement>(null); const setPanel = useCockpitStore((s) => s.setPanel)
### `cockpit/src/renderer/components/ConnectionBanner.tsx`
- Lines: 51. Definitions/exports: export function ConnectionBanner() {; const status = useRealtimeStore((s) => s.status); const reconnectCount = useRealtimeStore((s) => s.reconnectCount); const eventsPerMinute = useRealtimeStore((s) => s.eventsPerMinute); const lastPulseTimestamp = useRealtimeStore((s) => s.lastPulseTimestamp); const stalePulse = lastPulseTimestamp && Date.now() - lastPulseTimestamp > 10000; const bgClass = status === 'fallback' ? 'bg-amber/10 border-amber/20' :; const textClass = status === 'fallback' ? 'text-amber' :
### `cockpit/src/renderer/components/ControlPanel.tsx`
- Lines: 389. Definitions/exports: const CONTINUITY_COLORS: Record<string, string> = {; const RISK_COLORS: Record<string, string> = {; const MODE_COLORS: Record<string, string> = {; const STATUS_DOT: Record<string, string> = {; export function ControlPanel() {; const expanded = useCollapseStore((s) => s.isOpen('control-panel')); const toggleExpanded = useCollapseStore((s) => s.toggle); const [continuityState, setContinuityState] = useState('ACTIVE')
### `cockpit/src/renderer/components/CronTable.tsx`
- Lines: 103. Definitions/exports: export interface CronJob {; interface CronTableProps {; function formatTime(ts: string | null): string {; const d = new Date(ts); const now = Date.now(); const diff = now - d.getTime(); export function CronTable({ jobs, loading }: CronTableProps) {
### `cockpit/src/renderer/components/DetailDrawer.tsx`
- Lines: 141. Definitions/exports: interface DetailDrawerProps {; export function DetailDrawer({; const closeRef = useRef<HTMLButtonElement>(null); const handler = (e: KeyboardEvent) => {
### `cockpit/src/renderer/components/ErrorBoundary.tsx`
- Lines: 52. Definitions/exports: interface Props {; interface State {; export class ErrorBoundary extends Component<Props, State> {
### `cockpit/src/renderer/components/EventConsole.tsx`
- Lines: 175. Definitions/exports: const DOMAIN_COLORS: Record<string, string> = {; const PRIORITY_COLORS: Record<string, string> = {; const FILTER_GROUPS: { label: string; value: EventDomainFilter }[] = [; function matchesFilter(event: OrganismEvent, filter: EventDomainFilter): boolean {; interface EventConsoleProps {; export function EventConsole({ maxHeight = '400px', compact = false }: EventConsoleProps) {; const events = useRealtimeStore((s) => s.events); const status = useRealtimeStore((s) => s.status)
### `cockpit/src/renderer/components/ExecutionTimeline.tsx`
- Lines: 208. Definitions/exports: const LIFECYCLE_STAGES = [; const STAGE_COLORS: Record<string, string> = {; const STAGE_TEXT_COLORS: Record<string, string> = {; const RISK_COLORS: Record<string, string> = {; interface EnvelopeEntry {; function stageIndex(status: string): number {; const idx = LIFECYCLE_STAGES.indexOf(status as typeof LIFECYCLE_STAGES[number]); function EnvelopeTimeline({ env }: { env: EnvelopeEntry }) {
### `cockpit/src/renderer/components/FabLarge.tsx`
- Lines: 140. Definitions/exports: const MODE_COLORS: Record<string, string> = {; export function FabLarge() {; const aiName = useConfigStore((s) => s.aiName); const mode = useCockpitStore((s) => s.mode); const cycleWindowMode = useCockpitStore((s) => s.cycleWindowMode); const setWindowMode = useCockpitStore((s) => s.setWindowMode); const setPanel = useCockpitStore((s) => s.setPanel); const agents = useAgentStore((s) => s.agents)
### `cockpit/src/renderer/components/FabMedium.tsx`
- Lines: 63. Definitions/exports: const MODE_COLORS: Record<string, string> = {; export function FabMedium() {; const mode = useCockpitStore((s) => s.mode); const cycleWindowMode = useCockpitStore((s) => s.cycleWindowMode); const micState = useVoiceStore((s) => s.micState)
### `cockpit/src/renderer/components/FabSmall.tsx`
- Lines: 32. Definitions/exports: export function FabSmall() {; const cycleWindowMode = useCockpitStore((s) => s.cycleWindowMode); const micState = useVoiceStore((s) => s.micState)
### `cockpit/src/renderer/components/GraphView.tsx`
- Lines: 184. Definitions/exports: interface GraphNode {; interface GraphEdge {; interface GraphViewProps {; export function GraphView({ nodes, edges, onNodeClick, colorMap = {} }: GraphViewProps) {; const svgRef = useRef<SVGSVGElement>(null); const simRef = useRef<GraphNode[]>([]); const svg = svgRef.current; const rect = svg.getBoundingClientRect()
### `cockpit/src/renderer/components/HudBar.tsx`
- Lines: 265. Definitions/exports: function StatusDot({ status }: { status: 'connected' | 'connecting' | 'disconnected' }) {; function AudioMeter({ level }: { level: number }) {; const bars = 5; const active = Math.round(level * bars); function OrganismMetrics() {; const nodeMetrics = useRealtimeStore((s) => s.nodeMetrics); const online = Object.values(nodeMetrics).filter((m) => m.status === 'online'); const total = Object.keys(nodeMetrics).length
### `cockpit/src/renderer/components/LeftRail.tsx`
- Lines: 87. Definitions/exports: export function LeftRail() {; const activePanel = useCockpitStore((s) => s.activePanel); const railCollapsed = useCockpitStore((s) => s.railCollapsed); const setPanel = useCockpitStore((s) => s.setPanel); const toggleRail = useCockpitStore((s) => s.toggleRail); const allRoutes = ROUTE_GROUPS.flatMap((group) =>; const Icon = r.icon; const groupRoutes = ROUTES.filter(
### `cockpit/src/renderer/components/LivePreview.tsx`
- Lines: 89. Definitions/exports: interface LivePreviewProps {; export function LivePreview({ url, defaultUrl = 'http://localhost:5173' }: LivePreviewProps) {; const [currentUrl, setCurrentUrl] = useState(url || defaultUrl); const [inputUrl, setInputUrl] = useState(url || defaultUrl); const [loading, setLoading] = useState(true); const iframeRef = useRef<HTMLIFrameElement>(null); function handleNavigate(e: React.FormEvent) {; function handleRefresh() {
### `cockpit/src/renderer/components/NavRail.tsx`
- Lines: 73. Definitions/exports: const NAV_ITEMS: Array<{ panel: Panel; icon: string; label: string; key: string }> = [; export function NavRail() {; const aiName = useConfigStore((s) => s.aiName); const activePanel = useCockpitStore((s) => s.activePanel); const setPanel = useCockpitStore((s) => s.setPanel); const toggleChat = useCockpitStore((s) => s.toggleChat); const chatOpen = useCockpitStore((s) => s.chatOpen)
### `cockpit/src/renderer/components/OverlayToggle.tsx`
- Lines: 36. Definitions/exports: interface OverlayOption {; interface OverlayToggleProps {; export function OverlayToggle({ options, active, onToggle }: OverlayToggleProps) {; const isActive = active.includes(opt.id)
### `cockpit/src/renderer/components/RightRail.tsx`
- Lines: 670. Definitions/exports: const API_URL = import.meta.env.VITE_API_URL || '/api/umh'; function safeUrl(url: string): string {; const markdownComponents = {; type RightTab = 'conversation' | 'context' | 'execution'; export function RightRail() {; const collapsed = useCollapseStore((s) => !s.isOpen('right-rail')); const toggleCollapsed = useCallback(() => useCollapseStore.getState().toggle('right-rail'), []); const [activeTab, setActiveTab] = useState<RightTab>('conversation')
### `cockpit/src/renderer/components/RingGauge.tsx`
- Lines: 53. Definitions/exports: interface RingGaugeProps {; export function RingGauge({ value, max, label, unit = '', color = 'var(--color-cyan)', size = 80 }: RingGaugeProps) {; const pct = Math.min(value / Math.max(max, 1), 1); const radius = (size - 8) / 2; const circumference = 2 * Math.PI * radius; const strokeDashoffset = circumference * (1 - pct)
### `cockpit/src/renderer/components/RuntimeBadge.tsx`
- Lines: 66. Definitions/exports: function normalizeRuntime(runtime: string): string {; const value = runtime.toLowerCase().replace(/_/g, '-'); export const RUNTIME_COLORS: Record<string, { color: string; bg: string; label: string }> = {; interface RuntimeBadgeProps {; export function RuntimeBadge({ runtime }: RuntimeBadgeProps) {; const normalized = normalizeRuntime(runtime); const config = RUNTIME_COLORS[normalized] || {
### `cockpit/src/renderer/components/Shell.tsx`
- Lines: 300. Definitions/exports: function ActivePanel() {; const activePanel = useCockpitStore((s) => s.activePanel); export function Shell() {; const windowMode = useCockpitStore((s) => s.windowMode); const initializeDeviceSession = useDeviceSessionStore((s) => s.initialize); const teardownDeviceSession = useDeviceSessionStore((s) => s.teardown)
### `cockpit/src/renderer/components/SplitPane.tsx`
- Lines: 80. Definitions/exports: interface SplitPaneProps {; export function SplitPane({; const [ratio, setRatio] = useState(initialRatio); const containerRef = useRef<HTMLDivElement>(null); const dragging = useRef(false); const handleMouseDown = useCallback((e: React.MouseEvent) => {; const onMouseMove = (ev: MouseEvent) => {; const rect = containerRef.current.getBoundingClientRect()
### `cockpit/src/renderer/components/StatusBadge.tsx`
- Lines: 40. Definitions/exports: const STATUS_STYLES: Record<string, { color: string; bg: string }> = {; interface StatusBadgeProps {; export function StatusBadge({ status, dot }: StatusBadgeProps) {; const style = STATUS_STYLES[status.toLowerCase()] || STATUS_STYLES.pending
### `cockpit/src/renderer/components/TaskBlock.tsx`
- Lines: 59. Definitions/exports: interface TaskBlockProps {; const STATUS_COLORS = {; const STATUS_LABELS = {; export function TaskBlock({ title, status, agent, timestamp, onClick }: TaskBlockProps) {; const color = STATUS_COLORS[status]
### `cockpit/src/renderer/components/TimelineView.tsx`
- Lines: 107. Definitions/exports: interface TimelineEvent {; interface TimelineViewProps {; const STATUS_COLORS: Record<string, string> = {; export function TimelineView({ events, onEventClick }: TimelineViewProps) {; const sorted = [...events].sort(; const earliest = new Date(sorted[0].timestamp).getTime(); const latest = new Date(sorted[sorted.length - 1].timestamp).getTime(); const range = latest - earliest || 1
### `cockpit/src/renderer/components/TitleBar.tsx`
- Lines: 75. Definitions/exports: interface Window {; export function TitleBar() {; const toggleFullscreen = () => {
### `cockpit/src/renderer/components/TopologyMap.tsx`
- Lines: 205. Definitions/exports: const STATUS_DOT: Record<string, string> = {; interface TopologyNode {; export function TopologyMap() {; const organismStatus = useOrganismStore((s) => s.organismStatus); const runtimeGraph = useOrganismStore((s) => s.runtimeGraph); const spine = useOrganismStore((s) => s.spine); const guard = useOrganismStore((s) => s.guard); const gateway = useOrganismStore((s) => s.gateway)
### `cockpit/src/renderer/components/TrackingPanel.tsx`
- Lines: 330. Definitions/exports: const STATUS_COLORS: Record<string, string> = {; export function TrackingPanel() {; const {; const [trackInput, setTrackInput] = useState(''); const [labelInput, setLabelInput] = useState(''); const [watchInput, setWatchInput] = useState(''); const [queryInput, setQueryInput] = useState(''); const handleTrackStart = useCallback(() => {
### `cockpit/src/renderer/components/VisionPopout.tsx`
- Lines: 285. Definitions/exports: const POPOUT_WIDTH = 480; const POPOUT_HEIGHT = 360; function getVisionWsUrl(): string {; const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'; const isElectron = Boolean((window as Record<string, unknown>).cockpit); const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'; function buildPopoutDom(doc: Document): void {; const wsUrl = getVisionWsUrl()
### `cockpit/src/renderer/components/VoiceCommandBar.tsx`
- Lines: 420. Definitions/exports: const CLAP_THRESHOLD = 0.6; const CLAP_COOLDOWN_MS = 1500; function makeWakeWords(name: string): string[] {; const lower = name.toLowerCase(); function VoiceOrb() {; const aiName = useConfigStore((s) => s.aiName); const micState = useVoiceStore((s) => s.micState); const ttsState = useVoiceStore((s) => s.ttsState)
### `cockpit/src/renderer/components/VoiceRouteHud.tsx`
- Lines: 84. Definitions/exports: export function VoiceRouteHud() {; const micState = useVoiceStore((s) => s.micState); const ttsState = useVoiceStore((s) => s.ttsState); const voiceRoute = useDeviceSessionStore((s) => s.voiceRoute); const isActive =; const route = voiceRoute; const labelStyle: React.CSSProperties = {; const valueStyle: React.CSSProperties = {
### `cockpit/src/renderer/components/VoiceWaveform.tsx`
- Lines: 32. Definitions/exports: export function VoiceWaveform() {; const audioLevel = useVoiceStore((s) => s.audioLevel); const micState = useVoiceStore((s) => s.micState); const bars = 5; const levels = Array.from({ length: bars }, (_, i) => {; const offset = (i - Math.floor(bars / 2)) * 0.15; const base = Math.max(0, Math.min(1, audioLevel + offset))
### `cockpit/src/renderer/components/cards/ApprovalCard.tsx`
- Lines: 81. Definitions/exports: const RISK_COLORS: Record<string, { text: string; bg: string }> = {; interface ApprovalCardProps {; export function ApprovalCard({ message, onApprove, onDeny }: ApprovalCardProps) {; const data = message.approval_data; const riskStyle = RISK_COLORS[data.risk_level] || RISK_COLORS.MEDIUM
### `cockpit/src/renderer/components/cards/CommandResultCard.tsx`
- Lines: 75. Definitions/exports: function safeUrl(url: string): string {; const markdownComponents = {; interface CommandResultCardProps {; function bubbleWidth(text: string): string {; const len = text.length; export function CommandResultCard({ message, aiName, onAction }: CommandResultCardProps) {; const w = bubbleWidth(message.content)
### `cockpit/src/renderer/components/cards/ConversationBubble.tsx`
- Lines: 72. Definitions/exports: function safeUrl(url: string): string {; const markdownComponents = {; interface ConversationBubbleProps {; function bubbleWidth(text: string): string {; const len = text.length; export function ConversationBubble({ message, aiName }: ConversationBubbleProps) {; const w = bubbleWidth(message.content); const w = bubbleWidth(message.content)
### `cockpit/src/renderer/components/cards/ErrorCard.tsx`
- Lines: 48. Definitions/exports: interface ErrorCardProps {; export function ErrorCard({ message, onAction }: ErrorCardProps) {
### `cockpit/src/renderer/components/cards/RRIPRenderer.tsx`
- Lines: 36. Definitions/exports: interface RRIPRendererProps {; export function RRIPRenderer({ message, aiName, onAction, onApprove, onDeny }: RRIPRendererProps) {
### `cockpit/src/renderer/components/cards/ReportCard.tsx`
- Lines: 116. Definitions/exports: const API_URL = import.meta.env.VITE_API_URL || '/api/umh'; function safeUrl(url: string): string {; const markdownComponents = {; export function ReportCard({ message }: { message: RRIPMessage }) {; const handleDownload = useCallback(async (e: React.MouseEvent) => {; const url = `${API_URL}/chat/attachment?path=${encodeURIComponent(message.attachment.path)}`; const headers: Record<string, string> = {}; const key = getApiKey()
### `cockpit/src/renderer/components/rooms/ChannelCreateModal.tsx`
- Lines: 171. Definitions/exports: const CHANNEL_TYPES: { value: ChannelType; label: string }[] = [; interface Props {; export function ChannelCreateModal({ serverId, categories, onClose }: Props) {; const createChannel = useRoomsStore((s) => s.createChannel); const createCategory = useRoomsStore((s) => s.createCategory); const setActiveChannel = useRoomsStore((s) => s.setActiveChannel); const [mode, setMode] = useState<'channel' | 'category'>('channel'); const [name, setName] = useState('')
### `cockpit/src/renderer/components/rooms/ChannelSidebar.tsx`
- Lines: 243. Definitions/exports: const CHANNEL_ICONS: Record<ChannelType, typeof Hash> = {; interface CategoryGroupProps {; function CategoryGroup({ category, channels }: CategoryGroupProps) {; const key = `rooms:category:${category.id}`; const collapsed = useCollapseStore((s) => !s.isOpen(key, !category.collapsed)); const toggle = useCollapseStore((s) => s.toggle); const activeChannelId = useRoomsStore((s) => s.activeChannelId); const setActiveChannel = useRoomsStore((s) => s.setActiveChannel)
### `cockpit/src/renderer/components/rooms/ForumChannelView.tsx`
- Lines: 220. Definitions/exports: function PostCard({ post, onClick }: { post: ForumPost; onClick: () => void }) {; function CreatePostForm({ channelId, onClose }: { channelId: string; onClose: () => void }) {; const createForumPost = useRoomsStore((s) => s.createForumPost); const forumTags = useRoomsStore((s) => s.forumTags); const [title, setTitle] = useState(''); const [body, setBody] = useState(''); const [tags, setTags] = useState<string[]>([]); const [creating, setCreating] = useState(false)
### `cockpit/src/renderer/components/rooms/GuestJoinPage.tsx`
- Lines: 1366. Definitions/exports: type RemoteParticipant,; type Participant,; interface InviteInfo {; interface GuestToken {; type GuestJoinStage =; const STAGE_LABELS: Record<GuestJoinStage, string> = {; export function GuestJoinPage({ inviteCode }: { inviteCode: string }) {; const [info, setInfo] = useState<InviteInfo | null>(null)
### `cockpit/src/renderer/components/rooms/InvitePanel.tsx`
- Lines: 363. Definitions/exports: export function InvitePanel() {; const activeServerId = useRoomsStore((s) => s.activeServerId); const activeChannelId = useRoomsStore((s) => s.activeChannelId); const channels = useRoomsStore((s) => s.channels); const invites = useRoomsStore((s) => s.invites); const fetchInvites = useRoomsStore((s) => s.fetchInvites); const createInvite = useRoomsStore((s) => s.createInvite); const revokeInvite = useRoomsStore((s) => s.revokeInvite)
### `cockpit/src/renderer/components/rooms/MeetingRoomPanel.tsx`
- Lines: 1593. Definitions/exports: const MEETING_MODES: { value: MeetingMode; label: string }[] = [; const SOURCE_TYPE_ICONS: Record<string, typeof Monitor> = {; const SOURCE_TYPE_LABELS: Record<string, string> = {; function isIOS(): boolean {; type MeetingSidePanel = 'chat' | 'agenda' | 'notes' | 'actions' | null; export function MeetingRoomPanel({ channelId, onOpenChat }: { channelId: string; onOpenChat?: () => void }) {; const channels = useRoomsStore((s) => s.channels); const channel = channels.find((c) => c.id === channelId)
### `cockpit/src/renderer/components/rooms/MemberListPanel.tsx`
- Lines: 117. Definitions/exports: const STATUS_COLORS: Record<PresenceStatus, string> = {; export function MemberListPanel() {; const members = useRoomsStore((s) => s.members); const roles = useRoomsStore((s) => s.roles); const grouped = useMemo(() => {; const online = members.filter((m) => m.presence !== 'offline'); const offline = members.filter((m) => m.presence === 'offline'); const roleMap = useMemo(() => {
### `cockpit/src/renderer/components/rooms/RoomAuditLog.tsx`
- Lines: 51. Definitions/exports: export function RoomAuditLog() {; const activeServerId = useRoomsStore((s) => s.activeServerId); const auditLog = useRoomsStore((s) => s.auditLog); const fetchAuditLog = useRoomsStore((s) => s.fetchAuditLog)
### `cockpit/src/renderer/components/rooms/RoomChatPanel.tsx`
- Lines: 181. Definitions/exports: export function RoomChatPanel() {; const activeChannelId = useRoomsStore((s) => s.activeChannelId); const messages = useRoomsStore((s) => s.messages); const fetchMessages = useRoomsStore((s) => s.fetchMessages); const sendMessage = useRoomsStore((s) => s.sendMessage); const typingUsers = useRoomsStore((s) => s.typingUsers); const [input, setInput] = useState(''); const [sending, setSending] = useState(false)
### `cockpit/src/renderer/components/rooms/RoomDexPanel.tsx`
- Lines: 179. Definitions/exports: const DEX_MODES: { value: DexRoomMode; label: string }[] = [; export function RoomDexPanel() {; const activeChannelId = useRoomsStore((s) => s.activeChannelId); const dexSettings = useRoomsStore((s) => s.dexSettings); const updateDexSettings = useRoomsStore((s) => s.updateDexSettings); const dexSummarize = useRoomsStore((s) => s.dexSummarize); const [summary, setSummary] = useState<string | null>(null); const [summarizing, setSummarizing] = useState(false)
### `cockpit/src/renderer/components/rooms/RoomMainView.tsx`
- Lines: 97. Definitions/exports: const VoiceRoomPanel = lazy(() =>; const MeetingRoomPanel = lazy(() =>; export function RoomMainView({ onOpenChat }: { onOpenChat?: () => void }) {; const activeChannelId = useRoomsStore((s) => s.activeChannelId); const channels = useRoomsStore((s) => s.channels); const channel = channels.find((c) => c.id === activeChannelId); const isVoiceType = channel.type === 'voice' || channel.type === 'stage' || channel.type === 'broadcast'; function LoadingFallback({ label }: { label: string }) {
### `cockpit/src/renderer/components/rooms/RoomRightRail.tsx`
- Lines: 104. Definitions/exports: type Tab = 'members' | 'dex' | 'chat' | 'invites' | 'audit'; const TABS: { id: Tab; label: string; icon: typeof Users }[] = [; interface Props {; export function RoomRightRail({ collapsed, onToggleCollapse, chatRequested, onChatOpened }: Props) {; const [activeTab, setActiveTab] = useState<Tab>('members'); const isChatActive = activeTab === 'chat'; const railWidth = isChatActive ? 'w-80' : 'w-56'; const Icon = tab.icon
### `cockpit/src/renderer/components/rooms/ServerCreateModal.tsx`
- Lines: 161. Definitions/exports: const TEMPLATES: { value: ServerTemplate; label: string; emoji: string }[] = [; const PRIVACY_OPTIONS: { value: ServerPrivacy; label: string }[] = [; interface Props {; export function ServerCreateModal({ onClose }: Props) {; const createServer = useRoomsStore((s) => s.createServer); const setActiveServer = useRoomsStore((s) => s.setActiveServer); const [name, setName] = useState(''); const [description, setDescription] = useState('')
### `cockpit/src/renderer/components/rooms/ServerRail.tsx`
- Lines: 63. Definitions/exports: export function ServerRail() {; const servers = useRoomsStore((s) => s.servers); const activeServerId = useRoomsStore((s) => s.activeServerId); const setActiveServer = useRoomsStore((s) => s.setActiveServer); const [showCreate, setShowCreate] = useState(false); const visibleServers = servers
### `cockpit/src/renderer/components/rooms/TextChannelView.tsx`
- Lines: 383. Definitions/exports: function formatTime(iso: string): string {; const d = new Date(iso); function formatDate(iso: string): string {; const d = new Date(iso); const today = new Date(); const yesterday = new Date(today); interface MessageGroupProps {; function MessageGroup({ messages, onReply }: MessageGroupProps) {
### `cockpit/src/renderer/components/rooms/ThreadPanel.tsx`
- Lines: 111. Definitions/exports: export function ThreadPanel() {; const threads = useRoomsStore((s) => s.threads); const activeChannelId = useRoomsStore((s) => s.activeChannelId); const createThread = useRoomsStore((s) => s.createThread); const updateThread = useRoomsStore((s) => s.updateThread); const [showCreate, setShowCreate] = useState(false); const [name, setName] = useState(''); const [creating, setCreating] = useState(false)
### `cockpit/src/renderer/components/rooms/VoiceRoomPanel.tsx`
- Lines: 1253. Definitions/exports: const SOURCE_TYPE_ICONS: Record<string, typeof Monitor> = {; const SOURCE_TYPE_LABELS: Record<string, string> = {; function detectScreenShareCapability(): 'native' | 'browser' | 'none' {; const isNativeApp = !!(window as Record<string, unknown>).Capacitor; function isIOS(): boolean {; export function VoiceRoomPanel({ channelId, onOpenChat }: { channelId: string; onOpenChat?: () => void }) {; const channels = useRoomsStore((s) => s.channels); const channel = channels.find((c) => c.id === channelId)
### `cockpit/src/renderer/components/vision/CameraModeSelector.tsx`
- Lines: 158. Definitions/exports: interface ModeSpec {; const MODES: ModeSpec[] = [; const AUTHORITY_PRIORITY: ControlAuthority[] = ['operator', 'voice', 'ai', 'autonomous']; export function CameraModeSelector() {; const connected = useVisionStore((s) => s.connected); const cameraMode = useVisionStore((s) => s.cameraMode); const setCameraMode = useVisionStore((s) => s.setCameraMode); const followMode = useVisionStore((s) => s.followMode)
### `cockpit/src/renderer/components/vision/DiagnosticsPanel.tsx`
- Lines: 296. Definitions/exports: const QUALITY_DESCRIPTIONS: Record<QualityMode, string> = {; export function DiagnosticsPanel({; const chainHealth = useVisionStore((s) => s.chainHealth); const trackerStack = useVisionStore((s) => s.trackerStack); const latencyHistory = useVisionStore((s) => s.latencyHistory); const labelCorrections = useVisionStore((s) => s.labelCorrections); const authorityLog = useVisionStore((s) => s.authority.log); const pipelineLatency = useVisionStore((s) => s.pipelineLatency)
### `cockpit/src/renderer/components/vision/FaceTrackingOverlay.tsx`
- Lines: 51. Definitions/exports: interface Landmark {; interface FaceTrackingOverlayProps {; export function FaceTrackingOverlay({ x, y, w, h, label, confidence, landmarks }: FaceTrackingOverlayProps) {; const color = '#3b82f6'
### `cockpit/src/renderer/components/vision/HandLandmarkOverlay.tsx`
- Lines: 40. Definitions/exports: interface Landmark {; interface HandLandmarkOverlayProps {; export function HandLandmarkOverlay({ landmarks, connections, color = '#22d3ee' }: HandLandmarkOverlayProps) {; const la = landmarks[a]; const lb = landmarks[b]
### `cockpit/src/renderer/components/vision/NotificationCenter.tsx`
- Lines: 130. Definitions/exports: const SEVERITY_STYLES: Record<NotificationSeverity, { bg: string; border: string; text: string; dot: string }> = {; function formatAge(ts: number): string {; const sec = Math.round((Date.now() - ts) / 1000); function NotificationRow({ n, onAck, onClear }: {; const s = SEVERITY_STYLES[n.severity]; export function NotificationCenter() {; const notifications = useVisionStore((s) => s.notifications); const unreadCount = useVisionStore((s) => s.notificationUnreadCount)
### `cockpit/src/renderer/components/vision/PoseSkeletonOverlay.tsx`
- Lines: 40. Definitions/exports: interface Landmark {; interface PoseSkeletonOverlayProps {; export function PoseSkeletonOverlay({ landmarks, connections, color = '#a78bfa' }: PoseSkeletonOverlayProps) {; const la = landmarks[a]; const lb = landmarks[b]
### `cockpit/src/renderer/components/vision/SceneInventory.tsx`
- Lines: 233. Definitions/exports: const MAX_CHIPS = 12; export function SceneInventory() {; const overlays = useVisionStore((s) => s.overlays); const trackedObjects = useVisionStore((s) => s.trackedObjects); const connected = useVisionStore((s) => s.connected); const labelCorrections = useVisionStore((s) => s.labelCorrections); const setLabelCorrection = useVisionStore((s) => s.setLabelCorrection); const removeLabelCorrection = useVisionStore((s) => s.removeLabelCorrection)
### `cockpit/src/renderer/components/vision/StatusHud.tsx`
- Lines: 299. Definitions/exports: type StatusColor = 'ok' | 'warn' | 'danger' | 'off'; function Dot({ color }: { color: StatusColor }) {; const bg = color === 'ok' ? 'bg-ok' : color === 'warn' ? 'bg-warning' : color === 'danger' ? 'bg-danger' : 'bg-text-quaternary'; function DomainChip({ label, state, color }: { label: string; state: string; color: StatusColor }) {; const textCls = color === 'ok' ? 'text-ok' : color === 'warn' ? 'text-warning' : color === 'danger' ? 'text-danger' : 'text-text-quaternary'; const AUTHORITY_LABELS: Record<ControlAuthority, string> = {; export function StatusHud() {; const connected = useVisionStore((s) => s.connected)
### `cockpit/src/renderer/components/vision/ToastContainer.tsx`
- Lines: 47. Definitions/exports: const VARIANT_STYLES: Record<string, string> = {; export function ToastContainer() {; const toasts = useVisionStore((s) => s.toasts); const removeToast = useVisionStore((s) => s.removeToast); const timer = setInterval(() => {; const now = Date.now()
### `cockpit/src/renderer/components/vision/TrackedObjectBox.tsx`
- Lines: 45. Definitions/exports: interface TrackedObjectBoxProps {; export function TrackedObjectBox({ x, y, w, h, label, confidence, color = '#22c55e', trackId }: TrackedObjectBoxProps) {; const labelAbove = y >= 18; const labelY = labelAbove ? y - 16 : y + h; const labelTextY = labelAbove ? y - 4 : y + h + 12; const idSuffix = trackId && !trackId.startsWith('det_')
### `cockpit/src/renderer/components/vision/VisionConnectionStatus.tsx`
- Lines: 130. Definitions/exports: const STATUS_CONFIG: Record<VisionChainStatus, { color: string; label: string }> = {; function formatAge(ms: number): string {; export function VisionConnectionStatus(): JSX.Element {; const connected = useVisionStore((s) => s.connected); const health = useVisionStore((s) => s.chainHealth); const analysisStatus = useVisionStore((s) => s.analysisStatus); const cfg = connected; const handleReconnect = () => {
### `cockpit/src/renderer/components/vision/VisionOverlay.tsx`
- Lines: 114. Definitions/exports: interface VisionOverlayProps {; export function VisionOverlay({ overlays = [], width, height, visible = true }: VisionOverlayProps) {; const trackerStack = useVisionStore((s) => s.trackerStack); const securityMode = useVisionStore((s) => s.securityMode); const labelCorrections = useVisionStore((s) => s.labelCorrections); const effectiveOverlays = overlays; const correction = labelCorrections[o.track_id]; const enabledCategories = new Set(
### `cockpit/src/renderer/components/vision/VisionSettings.tsx`
- Lines: 474. Definitions/exports: type QualityMode,; type CameraDevice,; type DeviceStatus,; type VisionReadiness,; const QUALITY_LABELS: Record<QualityMode, string> = {; const QUALITY_DESCRIPTIONS: Record<QualityMode, string> = {; const STATUS_LABELS: Record<DeviceStatus, string> = {; const READINESS_COLORS: Record<VisionReadiness, string> = {
### `cockpit/src/renderer/components/vision/index.ts`
- Lines: 12. Definitions/exports: export type { OverlayMetadata } from '../../stores/visionStore'
### `cockpit/src/renderer/constants/devices.ts`
- Lines: 62. Definitions/exports: export interface DeviceInfo {; export const DEVICES: Record<string, DeviceInfo> = {; export const VPS = DEVICES.vps; export const BEAST = DEVICES.beast; export function getDeviceDisplayName(nodeId: string): string {; export function isWindows(nodeParam?: string): boolean {
### `cockpit/src/renderer/constants.ts`
- Lines: 8. Definitions/exports: export const FALLBACK_AI_NAME = import.meta.env.VITE_AI_NAME || 'Assistant'; export function getAiName(): string {
### `cockpit/src/renderer/dist/web/assets/index-BJmTyqJa.js`
- Lines: 16. Definitions/exports: -
### `cockpit/src/renderer/global.d.ts`
- Lines: 37. Definitions/exports: interface CockpitBridge {; interface Window {
### `cockpit/src/renderer/hooks/useBroadcastConnection.ts`
- Lines: 62. Definitions/exports: export function getBroadcastClient(): BroadcastWsClient | null {; export function useBroadcastConnection(): void {; const setConnected = useBroadcastStore((s) => s.setConnected); const setBroadcastState = useBroadcastStore((s) => s.setBroadcastState); const setHealth = useBroadcastStore((s) => s.setHealth); const setPid = useBroadcastStore((s) => s.setPid); const setConfig = useBroadcastStore((s) => s.setConfig); const setComposite = useBroadcastStore((s) => s.setComposite)
### `cockpit/src/renderer/hooks/useConferenceRoom.ts`
- Lines: 305. Definitions/exports: export type StreamSourceType = 'camera' | 'screen' | 'window' | 'tab' | 'application'; export interface MediaStreamSource {; export interface ConferenceParticipant {; export type ConferenceRoomState =; export type MicState =; export type CameraState =; export type JoinStage =; export interface MediaIntent {
### `cockpit/src/renderer/hooks/useKeyboard.ts`
- Lines: 55. Definitions/exports: const PANEL_KEYS: Record<string, Panel> = {; export function useKeyboard(): void {; const setPanel = useCockpitStore((s) => s.setPanel); const toggleChat = useCockpitStore((s) => s.toggleChat); const toggleRail = useCockpitStore((s) => s.toggleRail); const cycleWindowMode = useCockpitStore((s) => s.cycleWindowMode); function handleKeyDown(e: KeyboardEvent): void {; const panel = PANEL_KEYS[e.key]
### `cockpit/src/renderer/hooks/useOrganismRealtime.ts`
- Lines: 257. Definitions/exports: const RECONNECT_BASE_MS = 1000; const RECONNECT_MAX_MS = 30000; const HEARTBEAT_INTERVAL_MS = 25000; const FALLBACK_POLL_BASE_MS = 5000; const FALLBACK_POLL_MAX_MS = 30000; function buildWsUrl(): string {; const envUrl = import.meta.env.VITE_ORGANISM_WS_URL as string | undefined; const clerkToken = await getClerkToken()
### `cockpit/src/renderer/hooks/usePolling.ts`
- Lines: 31. Definitions/exports: export function usePolling(; const savedCallback = useRef(callback); const timers: ReturnType<typeof setTimeout>[] = []; const start = () => {; const id = setInterval(() => savedCallback.current(), intervalMs)
### `cockpit/src/renderer/hooks/useVisionConnection.ts`
- Lines: 874. Definitions/exports: type CameraPreset,; type TrackedObjectState,; type WatchItemState,; type FollowModeState,; type TrackerConfigState,; type VisionPresetInfo,; type TriggerChainInfo,; type ChainFireInfo,
### `cockpit/src/renderer/hooks/useVoiceDetection.ts`
- Lines: 117. Definitions/exports: const CLAP_THRESHOLD = 0.6; const CLAP_COOLDOWN_MS = 1500; function makeWakeWords(name: string): string[] {; const lower = name.toLowerCase(); export function useVoiceDetection(): void {; const aiName = useConfigStore((s) => s.aiName); const wakeWords = useMemo(() => makeWakeWords(aiName), [aiName]); const clapEnabled = useVoiceStore((s) => s.clapEnabled)
### `cockpit/src/renderer/hooks/useVoiceRoom.ts`
- Lines: 75. Definitions/exports: export type { StreamSourceType, MediaStreamSource }; export type VoiceParticipant = ConferenceParticipant; export type VoiceRoomState = ConferenceRoomState; export type VoiceDiagnostics = ConferenceDiagnostics; export interface UseVoiceRoomReturn {; export function useVoiceRoom(channelId: string): UseVoiceRoomReturn {; const conf = useConferenceRoom(channelId)
### `cockpit/src/renderer/lib/rrip-normalize.ts`
- Lines: 54. Definitions/exports: const COMMAND_INTENTS = new Set([; function inferRole(msg: ChatMessage): RRIPRole {; function inferKind(msg: ChatMessage): RRIPKind {; export function normalizeLegacyMessage(msg: ChatMessage): RRIPMessage {
### `cockpit/src/renderer/lib/time.ts`
- Lines: 25. Definitions/exports: export function relativeTime(iso: string): string {; const diff = Date.now() - new Date(iso).getTime(); const seconds = Math.floor(diff / 1000); const minutes = Math.floor(seconds / 60); const hours = Math.floor(minutes / 60); export function formatUptime(seconds: number): string {; const d = Math.floor(seconds / 86400); const h = Math.floor((seconds % 86400) / 3600)
### `cockpit/src/renderer/main.tsx`
- Lines: 20. Definitions/exports: const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string
### `cockpit/src/renderer/operator/speechInputAdapter.ts`
- Lines: 198. Definitions/exports: type SpeechRecognitionLike = {; type SpeechRecognitionEventLike = {; type SpeechRecognitionErrorLike = {; export type SpeechStateListener = (state: VoiceCommandState) => void; export type TranscriptListener = (transcript: VoiceTranscript) => void; export type ErrorListener = (error: string) => void; function nextTranscriptId(): string {; function getSpeechRecognitionConstructor(): (new () => SpeechRecognitionLike) | null {
### `cockpit/src/renderer/operator/voiceTypes.ts`
- Lines: 138. Definitions/exports: export type VoiceCommandState =; export type VoiceInputMode = 'voice' | 'text' | 'fallback_text'; export interface VoiceTranscript {; export interface VoiceCommandRequest {; export interface VoiceCommandResult {; export interface DexResponse {; export interface PacketPreview {; export interface TopologyPreview {
### `cockpit/src/renderer/panels/ActionsPanel.tsx`
- Lines: 187. Definitions/exports: const RISK_COLORS: Record<string, string> = {; const STATUS_COLORS: Record<string, string> = {; const CATEGORY_ORDER = ['observation', 'test', 'container', 'service', 'build', 'workspace']; export function ActionsPanel() {; const actions = useActionsStore((s) => s.actions); const history = useActionsStore((s) => s.history); const loading = useActionsStore((s) => s.loading); const executing = useActionsStore((s) => s.executing)
### `cockpit/src/renderer/panels/ActivityPanel.tsx`
- Lines: 106. Definitions/exports: const SEVERITY_COLORS: Record<string, string> = {; const SEVERITY_BG: Record<string, string> = {; export function ActivityPanel() {; const events = useActivityStore((s) => s.events); const filter = useActivityStore((s) => s.filter); const autoScroll = useActivityStore((s) => s.autoScroll); const fetchEvents = useActivityStore((s) => s.fetchEvents); const setAutoScroll = useActivityStore((s) => s.setAutoScroll)
### `cockpit/src/renderer/panels/AgentsPanel.tsx`
- Lines: 221. Definitions/exports: const STATUS_CONFIG: Record<string, { color: string; label: string }> = {; function StatusDot({ status }: { status: string }) {; const cfg = STATUS_CONFIG[status] || { color: 'bg-text-tertiary', label: status }; export function AgentsPanel() {; const agents = useAgentStore((s) => s.agents); const selectedId = useAgentStore((s) => s.selectedId); const detail = useAgentStore((s) => s.detail); const fetchAgents = useAgentStore((s) => s.fetchAgents)
### `cockpit/src/renderer/panels/AnalyticsPanel.tsx`
- Lines: 122. Definitions/exports: function MiniChart({ data }: { data: { date: string; count: number }[] }) {; const max = Math.max(...data.map((d) => d.count), 1); const w = 600; const h = 120; const points = data.map((d, i) => {; const x = (i / Math.max(data.length - 1, 1)) * w; const y = h - (d.count / max) * (h - 10); const x = (i / Math.max(data.length - 1, 1)) * w
### `cockpit/src/renderer/panels/ApprovalsPanel.tsx`
- Lines: 254. Definitions/exports: const RISK_BADGE: Record<string, string> = {; export function ApprovalsPanel() {; const approvals = useApprovalStore((s) => s.approvals); const fetchApprovals = useApprovalStore((s) => s.fetchApprovals); const approve = useApprovalStore((s) => s.approve); const deny = useApprovalStore((s) => s.deny); const spineEnvelopes = useOrganismStore((s) => s.pendingEnvelopes); const completedEnvelopes = useOrganismStore((s) => s.completedEnvelopes)
### `cockpit/src/renderer/panels/BroadcastPanel.tsx`
- Lines: 282. Definitions/exports: export function BroadcastPanel() {; const setViewContext = useViewContextStore((s) => s.setContext); const {; const [outputUrl, setOutputUrl] = useState('rtmp://localhost/live/test'); const [starting, setStarting] = useState(false); const [stopping, setStopping] = useState(false); const [switching, setSwitching] = useState<string | null>(null); const [selectedNode, setSelectedNode] = useState('local')
### `cockpit/src/renderer/panels/BuildLoopPanel.tsx`
- Lines: 185. Definitions/exports: type Tab = 'submit' | 'active' | 'history'; const PHASE_COLORS: Record<string, string> = {; export function BuildLoopPanel() {; const [tab, setTab] = useState<Tab>('submit'); const [text, setText] = useState(''); const [target, setTarget] = useState(''); const { status, activeRequests, history, loading, fetchStatus, fetchActive, fetchHistory, submit } =; const handleSubmit = useCallback(async () => {
### `cockpit/src/renderer/panels/CapabilitiesPanel.tsx`
- Lines: 371. Definitions/exports: type Tab = 'portfolio' | 'gaps' | 'graph' | 'compounding'; const TABS: { id: Tab; label: string; icon: typeof Layers }[] = [; function Badge({ label, variant = 'default' }: { label: string; variant?: string }) {; const colors: Record<string, string> = {; const cls = colors[variant] || colors[label] || colors.default; function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {; function PortfolioTab() {; const { portfolio, loading, fetchPortfolio } = useCapabilityIntelligenceStore()
### `cockpit/src/renderer/panels/CapabilityMapPanel.tsx`
- Lines: 164. Definitions/exports: type Tab = 'overview' | 'surfaces' | 'gaps' | 'duplications'; export function CapabilityMapPanel() {; const [tab, setTab] = useState<Tab>('overview'); const { snapshot, mvpGaps, duplications, loading, fetchSnapshot, fetchMvpGaps, fetchDuplications } =
### `cockpit/src/renderer/panels/CommandCenterPanel.tsx`
- Lines: 508. Definitions/exports: interface SummaryData {; const CONTINUITY_COLORS: Record<string, string> = {; const RISK_CEILING_COLORS: Record<string, string> = {; interface ReturnBrief {; export function CommandCenterPanel() {; const defaultSummary: SummaryData = {; const [summary, setSummary] = useState<SummaryData>(defaultSummary); const cachedSummary = useBootstrapStore((s) => s.cache.command_center_summary) as SummaryData | undefined
### `cockpit/src/renderer/panels/CommandsPanel.tsx`
- Lines: 396. Definitions/exports: interface CommandData {; interface CommandStatus {; interface TimelineEvent {; type Tab = 'submit' | 'active' | 'pending' | 'timeline' | 'history'; function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {; function getStatusColor(status: string): string {; function getActionBadge(action: string): string {; function formatTimestamp(ts: number): string {
### `cockpit/src/renderer/panels/CommsPanel.tsx`
- Lines: 235. Definitions/exports: export function CommsPanel() {; const [messages, setMessages] = useState<A2AMessage[]>([]); const [loading, setLoading] = useState(true); const [selectedConversation, setSelectedConversation] = useState<string | null>(null); const [sendText, setSendText] = useState(''); const [sendRecipient, setSendRecipient] = useState('dex'); const [sending, setSending] = useState(false); const fetchMessages = useCallback(async () => {
### `cockpit/src/renderer/panels/CompanyPanel.tsx`
- Lines: 292. Definitions/exports: interface CompanyData {; interface DepartmentData {; interface RoleData {; interface WorkflowData {; type View = 'overview' | 'departments' | 'workflows'; export function CompanyPanel() {; const [companies, setCompanies] = useState<CompanyData[]>([]); const [departments, setDepartments] = useState<DepartmentData[]>([])
### `cockpit/src/renderer/panels/ConferenceRoomsPanel.tsx`
- Lines: 73. Definitions/exports: export function ConferenceRoomsPanel() {; const fetchServers = useRoomsStore((s) => s.fetchServers); const activeServerId = useRoomsStore((s) => s.activeServerId); const loading = useRoomsStore((s) => s.loading); const channelSidebarCollapsed = useCollapseStore((s) => !s.isOpen('rooms:channel-sidebar')); const rightRailCollapsed = useCollapseStore((s) => !s.isOpen('rooms:right-rail')); const [chatRequested, setChatRequested] = useState(false); const toggleChannelSidebar = useCallback(() => useCollapseStore.getState().toggle('rooms:channel-sidebar'), [])
### `cockpit/src/renderer/panels/ContinuityPanel.tsx`
- Lines: 377. Definitions/exports: type ContinuityTab = 'overview' | 'objectives' | 'loops' | 'approvals' | 'timeline'; export function ContinuityPanel() {; const [tab, setTab] = useState<ContinuityTab>('overview'); const {; const tabs: { id: ContinuityTab; label: string }[] = [; function OverviewTab() {; const { continuityStatus, continuitySnapshot, continuityBrief, continuityResume } = useOperatorLoopStore(); function ObjectivesTab() {
### `cockpit/src/renderer/panels/DashboardPanel.tsx`
- Lines: 501. Definitions/exports: export function DashboardPanel() {; const pulse = useSystemStore((s) => s.pulse); const meshNodes = useSystemStore((s) => s.meshNodes); const models = useSystemStore((s) => s.models); const infraNodes = useSystemStore((s) => s.infraNodes); const fetchPulse = useSystemStore((s) => s.fetchPulse); const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes); const fetchModels = useSystemStore((s) => s.fetchModels)
### `cockpit/src/renderer/panels/DelegationPanel.tsx`
- Lines: 243. Definitions/exports: type Tab = 'proposals' | 'missions' | 'queue'; function str(obj: Record<string, unknown>, key: string, fallback = ''): string {; const v = obj[key]; function num(obj: Record<string, unknown> | null, key: string): number {; const v = obj[key]; function missionStatusColor(status: string): string {; export function DelegationPanel() {; const [tab, setTab] = useState<Tab>('proposals')
### `cockpit/src/renderer/panels/DistributedRuntimePanel.tsx`
- Lines: 294. Definitions/exports: type Tab = 'topology' | 'devices' | 'workers' | 'capacity' | 'assignments'; interface DeviceSummary {; interface Worker {; interface Placement {; interface CapMatrix {; interface RuntimeData {; const STATUS_COLORS: Record<string, string> = {; function StatusDot({ status }: { status: string }) {
### `cockpit/src/renderer/panels/EngineeringPanel.tsx`
- Lines: 556. Definitions/exports: const RISK_COLORS: Record<string, string> = {; const STATUS_COLORS: Record<string, string> = {; const GAP_COLORS: Record<string, string> = {; const RECOMMENDATION_COLORS: Record<string, string> = {; function TabBar({ active, onSelect }: { active: string; onSelect: (t: string) => void }) {; const tabs = ['intent', 'plan', 'queue', 'sessions', 'review', 'gaps'] as const; function IntentTab() {; const [intent, setIntent] = useState('')
### `cockpit/src/renderer/panels/ExecCoordPanel.tsx`
- Lines: 346. Definitions/exports: interface ExecutionPlan {; interface LifecycleEvent {; interface ExecutorDef {; interface CoordState {; type Tab = 'queue' | 'active' | 'approval' | 'history' | 'executors'; function KpiCard({ label, value }: { label: string; value: string | number }) {; function getStatusColor(status: string): string {; function getPriorityColor(priority: string): string {
### `cockpit/src/renderer/panels/ExecutionPanel.tsx`
- Lines: 187. Definitions/exports: const RISK_BADGE: Record<string, string> = {; export function ExecutionPanel() {; const spine = useOrganismStore((s) => s.spine); const executionMode = useOrganismStore((s) => s.executionMode); const guard = useOrganismStore((s) => s.guard); const gateway = useOrganismStore((s) => s.gateway); const leverage = useOrganismStore((s) => s.leverage); const journal = useOrganismStore((s) => s.journal)
### `cockpit/src/renderer/panels/ExecutivePanel.tsx`
- Lines: 234. Definitions/exports: const TABS = ['overview', 'allocations', 'budgets', 'tradeoffs', 'drift'] as const; const healthColor: Record<string, string> = {; const priorityColor: Record<string, string> = {; function OverviewTab() {; const { overview } = useExecutiveStore(); function AllocationsTab() {; const { allocations } = useExecutiveStore(); function BudgetsTab() {
### `cockpit/src/renderer/panels/ExecutorPanel.tsx`
- Lines: 1017. Definitions/exports: interface ExecutorRequest {; interface ExecutorResultData {; interface LifecycleEvent {; interface ExecutorState {; interface TelemetryEvent {; interface ApprovalIntercept {; interface WorktreeData {; interface ProcessData {
### `cockpit/src/renderer/panels/ExperimentsPanel.tsx`
- Lines: 17. Definitions/exports: export function ExperimentsPanel() {
### `cockpit/src/renderer/panels/GoalPanel.tsx`
- Lines: 452. Definitions/exports: type Tab = 'goals' | 'outcomes' | 'plans' | 'alignment' | 'drift'; const STATUS_COLORS: Record<string, string> = {; const DRIFT_COLORS: Record<string, string> = {; function Badge({ text, color }: { text: string; color?: string }) {; const cls = color ?? STATUS_COLORS[text.toLowerCase()] ?? 'text-text-tertiary bg-surface-raised'; function SectionCard({ children }: { children: React.ReactNode }) {; function ProgressBar({ value }: { value: number }) {; const pct = Math.round(value * 100)
### `cockpit/src/renderer/panels/GovernancePanel.tsx`
- Lines: 268. Definitions/exports: const TABS = ['overview', 'conflicts', 'coordination', 'knowledge', 'health'] as const; type Tab = typeof TABS[number]; const healthColor: Record<string, string> = {; const severityColor: Record<string, string> = {; function OverviewTab() {; const { overview } = useGovernanceStore(); function ConflictsTab() {; const { conflicts } = useGovernanceStore()
### `cockpit/src/renderer/panels/InfrastructurePanel.tsx`
- Lines: 197. Definitions/exports: export function InfrastructurePanel() {; const infraNodes = useSystemStore((s) => s.infraNodes); const meshNodes = useSystemStore((s) => s.meshNodes); const fetchInfra = useSystemStore((s) => s.fetchInfra); const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes); const buildInfo = useSystemStore((s) => s.buildInfo); const fetchBuildInfo = useSystemStore((s) => s.fetchBuildInfo); const workloads = useOrganismStore((s) => s.workloads)
### `cockpit/src/renderer/panels/IntelligencePanel.tsx`
- Lines: 658. Definitions/exports: const SEVERITY_COLORS: Record<string, string> = {; const PRIORITY_COLORS: Record<string, string> = {; const STATUS_COLORS: Record<string, string> = {; function ReadinessBar({ label, score, weight }: { label: string; score: number; weight: number }) {; const color = score >= 80 ? 'bg-ok' : score >= 60 ? 'bg-warn' : score >= 40 ? 'bg-cyan' : 'bg-danger'; function ConfidenceDot({ value }: { value: number }) {; const color = value >= 0.8 ? 'bg-ok' : value >= 0.5 ? 'bg-warn' : 'bg-text-tertiary'; function TemplateStatusBadge({ status }: { status: string }) {
### `cockpit/src/renderer/panels/IntentPanel.tsx`
- Lines: 127. Definitions/exports: const SCOPE_ORDER = ['empire', 'product', 'architecture', 'engineering', 'session']; const SCOPE_COLORS: Record<string, string> = {; export function IntentPanel() {; const activeIntents = useIntentStore((s) => s.activeIntents); const conflicts = useIntentStore((s) => s.conflicts); const summary = useIntentStore((s) => s.summary); const loading = useIntentStore((s) => s.loading); const fetchActive = useIntentStore((s) => s.fetchActive)
### `cockpit/src/renderer/panels/KnowledgePanel.tsx`
- Lines: 339. Definitions/exports: const PRIMITIVE_COLORS: Record<string, string> = {; const TABS = [; export function KnowledgePanel() {; const observations = useKnowledgeStore((s) => s.observations); const memory = useKnowledgeStore((s) => s.memory); const skills = useKnowledgeStore((s) => s.skills); const tracking = useKnowledgeStore((s) => s.tracking); const viewMode = useKnowledgeStore((s) => s.viewMode)
### `cockpit/src/renderer/panels/LearningPanel.tsx`
- Lines: 290. Definitions/exports: const TABS = ['overview', 'lessons', 'patterns', 'evolution', 'drift'] as const; function OverviewTab() {; const { overview } = useLearningStore(); const healthColor: Record<string, string> = {; function LessonsTab() {; const { lessons, actionableLessons } = useLearningStore(); const categoryColor: Record<string, string> = {; const displayLessons = lessons.length > 0 ? lessons : actionableLessons
### `cockpit/src/renderer/panels/MVPReadinessPanel.tsx`
- Lines: 161. Definitions/exports: type Tab = 'overview' | 'blockers' | 'escapepoints' | 'next'; export function MVPReadinessPanel() {; const [tab, setTab] = useState<Tab>('overview'); const {; const refresh = () => {; const scoreColor = score !== null; const scoreBg = score !== null; const name = (ep as Record<string, unknown>).name as string ?? `Escape Point ${i}`
### `cockpit/src/renderer/panels/MemoryPanel.tsx`
- Lines: 431. Definitions/exports: type Tab = 'decisions' | 'assumptions' | 'timeline' | 'validity' | 'impact'; const TABS: { id: Tab; label: string; icon: typeof Brain }[] = [; function Badge({ label, variant = 'default' }: { label: string; variant?: string }) {; const colors: Record<string, string> = {; const cls = colors[variant] || colors[label] || colors.default; function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {; function DecisionDetail({; const { selectedDecision, lineage, validity, impact, fetchDecisionDetail, fetchLineage, fetchValidity, fetchImpact } = useMemoryStore()
### `cockpit/src/renderer/panels/MetaIDEPanel.tsx`
- Lines: 1287. Definitions/exports: const SIDEBAR_ITEMS: Array<{ id: SidebarTab; icon: LucideIcon; label: string }> = [; const PANEL_TABS: Array<{ id: PanelTab; icon: LucideIcon; label: string }> = [; const RISK_COLORS: Record<string, string> = {; const HEALTH_COLORS: Record<string, string> = {; const STATE_COLORS: Record<string, string> = {; function useDragResize(; const dragging = useRef(false); const startPos = useRef(0)
### `cockpit/src/renderer/panels/OperatingLoopPanel.tsx`
- Lines: 153. Definitions/exports: type Tab = 'active' | 'completed' | 'snapshot'; export function OperatingLoopPanel() {; const [tab, setTab] = useState<Tab>('active'); const { activeLoops, completedLoops, snapshot, loading, fetchActiveLoops, fetchCompletedLoops, fetchSnapshot } =; const refresh = () => {; const stageColor = (stage: string): string => {; const stage = (loop as Record<string, unknown>).stage as string ?? 'UNKNOWN'; const intent = (loop as Record<string, unknown>).intent_text as string ?? `Loop ${i}`
### `cockpit/src/renderer/panels/OperationsPanel.tsx`
- Lines: 299. Definitions/exports: const stateColor: Record<string, string> = {; const stateBg: Record<string, string> = {; function StateBadge({ label, state }: { label: string; state: string }) {; function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {; function FabricSection() {; const fabric = useOperationsStore((s) => s.fabric); const nodes = (fabric.compute_nodes as Record<string, unknown>[]) || []; const cap = fabric as Record<string, unknown>
### `cockpit/src/renderer/panels/OperatorContinuityPanel.tsx`
- Lines: 249. Definitions/exports: const stateColor = (state: string): string => {; const statusColor = (status: string): string => {; function SectionHeader({ title }: { title: string }) {; function CurrentSection() {; const snapshot = usePresenceStore((s) => s.snapshot);; const ctx = snapshot.active_context;; function InfoCard({; function ResumeSection() {
### `cockpit/src/renderer/panels/OperatorHomePanel.tsx`
- Lines: 249. Definitions/exports: const severityColor = (severity: string): string => {; const statusColor = (status: string): string => {; const StatusCard: React.FC<{; const AttentionRow: React.FC<{; const TimelineRow: React.FC<{; const SectionHeader: React.FC<{ title: string; count?: number }> = ({ title, count }) => (; export const OperatorHomePanel: React.FC = () => {; const { snapshot, attention, timeline, loading, error, fetchHome } = useOperatorHomeStore();
### `cockpit/src/renderer/panels/OperatorPanel.tsx`
- Lines: 952. Definitions/exports: const RISK_COLOR: Record<string, string> = {; type Tab = 'command' | 'loop'; export function OperatorPanel() {; const [tab, setTab] = useState<Tab>('loop'); function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {; function WorkLoopTab() {; const {; function HealthBar({ health }: { health: { healthy: boolean; sandbox_summary: { total: number; active: number }; reality_model: string } | null }) {
### `cockpit/src/renderer/panels/OperatorTimelinePanel.tsx`
- Lines: 136. Definitions/exports: const TYPE_COLORS: Record<string, string> = {; const TYPE_LABELS: Record<string, string> = {; function formatTs(ts: number): string {; export function OperatorTimelinePanel() {; const { entries, loading, error, selectedIntentId, fetchTimeline, selectIntent } =; const [filterType, setFilterType] = useState<string>(''); const [expandedId, setExpandedId] = useState<string | null>(null); const filtered = filterType
### `cockpit/src/renderer/panels/OrchestratorPanel.tsx`
- Lines: 135. Definitions/exports: type Tab = 'context' | 'health' | 'score'; export function OrchestratorPanel() {; const [tab, setTab] = useState<Tab>('context'); const { context, snapshot, healthItems, score, loading, fetchContext, fetchSnapshot, fetchHealth, fetchScore } =; const refresh = () => {; const status = (item as Record<string, unknown>).status as string ?? 'unknown'; const domain = (item as Record<string, unknown>).domain as string ?? `Domain ${i}`
### `cockpit/src/renderer/panels/OrganismLoopPanel.tsx`
- Lines: 342. Definitions/exports: const STATUS_COLORS: Record<string, string> = {; const LOOP_STEPS = [; const STEP_KEYS: Record<string, number> = {; function stepReachedIndex(stepsCompleted: string[]): number {; const idx = STEP_KEYS[step]; interface CycleEvent {; function CurrentReality({ cycles }: { cycles: CycleEvent[] }) {; const latest = cycles.length > 0 ? cycles[cycles.length - 1] : null
### `cockpit/src/renderer/panels/OrganismMapPanel.tsx`
- Lines: 103. Definitions/exports: export function OrganismMapPanel() {; const topology = useOrganismMapStore((s) => s.topology); const health = useOrganismMapStore((s) => s.health); const selectedNode = useOrganismMapStore((s) => s.selectedNode); const loading = useOrganismMapStore((s) => s.loading); const fetchTopology = useOrganismMapStore((s) => s.fetchTopology); const fetchHealth = useOrganismMapStore((s) => s.fetchHealth); const fetchNodeDetail = useOrganismMapStore((s) => s.fetchNodeDetail)
### `cockpit/src/renderer/panels/OrganismPanel.tsx`
- Lines: 350. Definitions/exports: const SEVERITY_COLORS: Record<string, string> = {; const RISK_BADGE: Record<string, string> = {; export function OrganismPanel() {; const spine = useOrganismStore((s) => s.spine); const gateway = useOrganismStore((s) => s.gateway); const guard = useOrganismStore((s) => s.guard); const bottleneckStatus = useOrganismStore((s) => s.bottleneckStatus); const leverage = useOrganismStore((s) => s.leverage)
### `cockpit/src/renderer/panels/PortfolioPanel.tsx`
- Lines: 232. Definitions/exports: interface DepartmentData {; interface RoleData {; interface ProductConnection {; interface ProductSummary {; type View = 'portfolio' | 'department' | 'role'; export function PortfolioPanel() {; const [departments, setDepartments] = useState<DepartmentData[]>([]); const [roles, setRoles] = useState<RoleData[]>([])
### `cockpit/src/renderer/panels/PredictionPanel.tsx`
- Lines: 278. Definitions/exports: const TABS = ['overview', 'forecasts', 'scenarios', 'risk', 'confidence'] as const; function OverviewTab() {; const { overview } = usePredictionStore(); const healthColor: Record<string, string> = {; function ForecastsTab() {; const { forecasts } = usePredictionStore(); const statusColor: Record<string, string> = {; function ScenariosTab() {
### `cockpit/src/renderer/panels/PresencePanel.tsx`
- Lines: 372. Definitions/exports: interface PresenceStatus {; interface DeviceData {; interface SessionData {; interface PresenceTimelineEvent {; type Tab = 'overview' | 'devices' | 'sessions' | 'attention' | 'history'; function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {; function getAttentionColor(state: string): string {; function getInterruptionBadge(level: string): string {
### `cockpit/src/renderer/panels/ProfilePanel.tsx`
- Lines: 465. Definitions/exports: const API_BASE = '/api/umh'; function KpiCard({ label, value }: { label: string; value: string }) {; function formatTimestamp(ts: number): string {; function getProfileBadgeColor(profile: string): string {; const colors: Record<string, string> = {; function getModeBadgeColor(mode: string): string {; const colors: Record<string, string> = {; type Tab = 'active' | 'profiles' | 'modes' | 'transitions' | 'conflicts' | 'preferences'
### `cockpit/src/renderer/panels/ProjectionIntegrationPanel.tsx`
- Lines: 240. Definitions/exports: type Tab = 'overview' | 'locations' | 'gaps' | 'readiness'; const MATURITY_COLORS: Record<string, string> = {; export function ProjectionIntegrationPanel() {; const [tab, setTab] = useState<Tab>('overview'); const [selectedProjection, setSelectedProjection] = useState(''); const {; const projections = ((snapshot as Record<string, unknown> | null)?.projections as Record<string, unknown>[]) ?? []; const handleSelectProjection = useCallback((id: string) => {
### `cockpit/src/renderer/panels/ProjectionPanel.tsx`
- Lines: 420. Definitions/exports: type Tab = 'overview' | 'trends' | 'risks' | 'opportunities' | 'accuracy'; const HORIZON_LABELS: Record<string, string> = {; const SEVERITY_COLORS: Record<string, string> = {; const CONFIDENCE_COLORS: Record<string, string> = {; const DIRECTION_ICONS: Record<string, typeof TrendingUp> = {; const DIRECTION_COLORS: Record<string, string> = {; function KpiCard({ label, value, icon: Icon, color = 'text-text-primary' }: {; function OverviewTab({
### `cockpit/src/renderer/panels/PropagationGraphPanel.tsx`
- Lines: 234. Definitions/exports: interface GraphStats {; interface GraphNode {; interface ImpactResult {; interface CorrespondenceProof {; const NODE_TYPE_COLOR: Record<string, string> = {; export default function PropagationGraphPanel() {; const [stats, setStats] = useState<GraphStats | null>(null); const [nodes, setNodes] = useState<GraphNode[]>([])
### `cockpit/src/renderer/panels/RealityGraphPanel.tsx`
- Lines: 610. Definitions/exports: type Tab = 'overview' | 'entities' | 'resolve' | 'artifacts' | 'files' | 'docs' | 'runtime' | 'knowledge'; const TYPE_COLORS: Record<string, string> = {; function TypeBadge({ type }: { type: string }) {; const color = TYPE_COLORS[type] || 'text-text-secondary'; function StatusDot({ status }: { status: string }) {; const color = status === 'active' ? 'bg-green-400' : status === 'degraded' ? 'bg-yellow-400' : 'bg-text-tertiary'; export function RealityGraphPanel() {; const [tab, setTab] = useState<Tab>('overview')
### `cockpit/src/renderer/panels/RealityIntelligencePanel.tsx`
- Lines: 226. Definitions/exports: const SOURCE_TYPE_COLORS: Record<string, string> = {; const SOURCE_TYPE_LABELS: Record<string, string> = {; type QueryType = 'why' | 'what_changed' | 'evidence' | 'contradictions' | 'lineage' | 'domain_summary' | 'priorities'; const TABS: { key: QueryType; label: string }[] = [; function ConfidenceBar({ value }: { value: number }) {; const pct = Math.round(value * 100); const color = value >= 0.8 ? 'bg-ok' : value >= 0.5 ? 'bg-warn' : 'bg-danger'; export function RealityIntelligencePanel() {
### `cockpit/src/renderer/panels/RealityTimelinePanel.tsx`
- Lines: 160. Definitions/exports: const SOURCE_COLORS: Record<string, string> = {; const SOURCE_LABELS: Record<string, string> = {; function ConfidenceBar({ value }: { value: number }) {; const pct = Math.round(value * 100); const color = value >= 0.8 ? 'bg-ok' : value >= 0.5 ? 'bg-warn' : 'bg-danger'; export function RealityTimelinePanel() {; const {; const [expandedId, setExpandedId] = useState<string | null>(null)
### `cockpit/src/renderer/panels/RuntimePanel.tsx`
- Lines: 384. Definitions/exports: interface RuntimeOverview {; interface AdapterInfo {; interface RuntimeSessionData {; interface RuntimeEventData {; interface HandoffPreview {; function usePolling(fn: () => void, intervalMs: number) {; const id = setInterval(fn, intervalMs); function StatusBadge({ status }: { status: string }) {
### `cockpit/src/renderer/panels/ScreenAwarenessPanel.tsx`
- Lines: 423. Definitions/exports: const sourceColor = (source: string): string => {; const statusColor = (status: string): string => {; const confidenceLabel = (c: number): string => {; function SectionHeader({ title }: { title: string }) {; function InfoCard({; function SourceSection() {; const snapshot = useScreenAwarenessStore((s) => s.snapshot);; function ApplicationSection() {
### `cockpit/src/renderer/panels/SelfBuildPanel.tsx`
- Lines: 304. Definitions/exports: interface QueueSummary {; interface WorkItemSafe {; interface RoadmapSummary {; const STATUS_COLOR: Record<string, string> = {; const RISK_COLOR: Record<string, string> = {; const PHASE_STATUS_COLOR: Record<string, string> = {; export function SelfBuildPanel() {; const [summary, setSummary] = useState<QueueSummary | null>(null)
### `cockpit/src/renderer/panels/ServiceGraphPanel.tsx`
- Lines: 232. Definitions/exports: const criticalityColor = (criticality: string): string => {; const severityColor = (severity: string): string => {; type TabId = 'services' | 'critical-path' | 'impact';; const ServiceCard: React.FC<{ service: any; onSelect: (role: string) => void }> = ({ service, onSelect }) => {; const key = `service:${service.service_role}`; const expanded = useCollapseStore((s) => s.isOpen(key)); const toggle = useCollapseStore((s) => s.toggle); export const ServiceGraphPanel: React.FC = () => {
### `cockpit/src/renderer/panels/SessionPanel.tsx`
- Lines: 418. Definitions/exports: const API_BASE = '/api/umh'; function KpiCard({ label, value }: { label: string; value: string }) {; function formatTimestamp(ts: number): string {; function getStatusColor(status: string): string {; const colors: Record<string, string> = {; function getAuthorityColor(authority: string): string {; const colors: Record<string, string> = {; function getTypeIcon(type: string): string {
### `cockpit/src/renderer/panels/SessionResumePanel.tsx`
- Lines: 165. Definitions/exports: type Tab = 'active' | 'history'; export function SessionResumePanel() {; const [tab, setTab] = useState<Tab>('active'); const {; const refresh = () => {; const sessionId = activeSession; const id = (session as Record<string, unknown>).id as string ?? `session-${i}`; const status = (session as Record<string, unknown>).status as string ?? 'unknown'
### `cockpit/src/renderer/panels/SettingsPanel.tsx`
- Lines: 138. Definitions/exports: const AUTHORITY_COLORS: Record<string, string> = {; export function SettingsPanel() {; const settings = useSettingsStore((s) => s.settings); const governance = useSettingsStore((s) => s.governance); const fetchSettings = useSettingsStore((s) => s.fetchSettings); const fetchGovernance = useSettingsStore((s) => s.fetchGovernance)
### `cockpit/src/renderer/panels/SkillsPanel.tsx`
- Lines: 48. Definitions/exports: export function SkillsPanel() {; const { skills, fetchSkills } = useKnowledgeStore()
### `cockpit/src/renderer/panels/StateAuthorityPanel.tsx`
- Lines: 105. Definitions/exports: const statusColor = (status: string): string => {; const healthColor = (health: string): string => {; const DomainCard: React.FC<{ domain: any }> = ({ domain }) => {; const key = `domain:${domain.domain}`; const expanded = useCollapseStore((s) => s.isOpen(key)); const toggle = useCollapseStore((s) => s.toggle); export const StateAuthorityPanel: React.FC = () => {; const { coherence, loading, error, fetchCoherence } = useStateAuthorityStore();
### `cockpit/src/renderer/panels/StrategicPanel.tsx`
- Lines: 418. Definitions/exports: type Tab = 'overview' | 'priorities' | 'risks' | 'drift' | 'recommendations' | 'brief'; const SEVERITY_COLORS: Record<string, string> = {; function Badge({ text, color }: { text: string; color?: string }) {; const cls = color ?? SEVERITY_COLORS[text.toLowerCase()] ?? 'text-text-tertiary bg-surface-raised'; function SectionCard({ children }: { children: React.ReactNode }) {; function OverviewTab() {; const { context, brief } = useStrategicStore(); const health = (context as Record<string, unknown>)?.health as string ?? 'unknown'
### `cockpit/src/renderer/panels/StrategyPanel.tsx`
- Lines: 594. Definitions/exports: type Tab = 'overview' | 'goals' | 'gaps' | 'recommendations' | 'decisions'; const SEVERITY_COLORS: Record<string, string> = {; const STATUS_COLORS: Record<string, string> = {; export function StrategyPanel() {; const [tab, setTab] = useState<Tab>('overview'); const [showAddGoal, setShowAddGoal] = useState(false); const {; const handleAnalyze = useCallback(async () => {
### `cockpit/src/renderer/panels/TasksPanel.tsx`
- Lines: 97. Definitions/exports: export function TasksPanel() {; const tasks = useTaskStore((s) => s.tasks); const workflows = useTaskStore((s) => s.workflows); const viewMode = useTaskStore((s) => s.viewMode); const fetchTasks = useTaskStore((s) => s.fetchTasks); const fetchWorkflows = useTaskStore((s) => s.fetchWorkflows); const setViewMode = useTaskStore((s) => s.setViewMode); const triggerWorkflow = useTaskStore((s) => s.triggerWorkflow)
### `cockpit/src/renderer/panels/TickLoopPanel.tsx`
- Lines: 490. Definitions/exports: type Tab = 'command' | 'candidates' | 'drift' | 'history'; const FREQ_OPTIONS = [; const PROFILE_OPTIONS = [; const DRIFT_COLORS: Record<string, string> = {; const LIFECYCLE_COLORS: Record<string, string> = {; function KpiCard({ label, value, icon: Icon, color = 'text-text-primary' }: {; export function TickLoopPanel() {; const [activeTab, setActiveTab] = useState<Tab>('command')
### `cockpit/src/renderer/panels/TmuxPanel.tsx`
- Lines: 112. Definitions/exports: interface TmuxSession {; export function TmuxPanel() {; const [sessions, setSessions] = useState<TmuxSession[]>([]); const [selectedSession, setSelectedSession] = useState<string>(''); const [paneOutput, setPaneOutput] = useState<string>(''); const [loading, setLoading] = useState(false); const [error, setError] = useState<string>(''); const fetchSessions = useCallback(async () => {
### `cockpit/src/renderer/panels/TrackingPanel.tsx`
- Lines: 17. Definitions/exports: export function TrackingPanel() {
### `cockpit/src/renderer/panels/UMHNodePanel.tsx`
- Lines: 136. Definitions/exports: const STATUS_COLORS: Record<string, string> = {; function NodeCard({ node }: { node: any }) {; const key = `node:${node.node_id}`; const expanded = useCollapseStore((s) => s.isOpen(key)); const toggle = useCollapseStore((s) => s.toggle); export default function UMHNodePanel() {; const { topology, versionStatus, loading, fetchTopology, fetchVersionStatus } =
### `cockpit/src/renderer/panels/UnifiedExecutionPanel.tsx`
- Lines: 198. Definitions/exports: type Tab = 'active' | 'approvals' | 'history'; const STATUS_COLORS: Record<string, string> = {; export function UnifiedExecutionPanel() {; const [tab, setTab] = useState<Tab>('active'); const {; const handleRefresh = useCallback(() => {; const status = (s as Record<string, unknown>).status as string ?? 'unknown'
### `cockpit/src/renderer/panels/UniversalWorkPanel.tsx`
- Lines: 880. Definitions/exports: interface QueueSummary {; interface PacketSafe {; const STATUS_COLOR: Record<string, string> = {; const RISK_COLOR: Record<string, string> = {; const KANBAN_COLUMNS = [; type ViewMode = 'kanban' | 'table' | 'detail'; export function UniversalWorkPanel() {; const [summary, setSummary] = useState<QueueSummary | null>(null)
### `cockpit/src/renderer/panels/VisionPanel.tsx`
- Lines: 143. Definitions/exports: export function VisionPanel() {; const setViewContext = useViewContextStore((s) => s.setContext); const {; const trackingCount = trackedObjects.length + labeledItems.length; const watchCount = activeWatches.length
### `cockpit/src/renderer/panels/WorkIntelligencePanel.tsx`
- Lines: 351. Definitions/exports: type Tab = 'overview' | 'ready' | 'blocked' | 'delegation' | 'drift'; const STATUS_COLORS: Record<string, string> = {; const HEALTH_COLORS: Record<string, string> = {; function Badge({ label, colorClass }: { label: string; colorClass?: string }) {; const cls = colorClass || STATUS_COLORS[label] || 'text-muted bg-muted/10'; function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {; function Metric({ label, value, sub }: { label: string; value: string | number; sub?: string }) {; export function WorkIntelligencePanel() {
### `cockpit/src/renderer/panels/WorkPanel.tsx`
- Lines: 570. Definitions/exports: interface WorkPacket {; interface OvernightItem {; type WorkTab = 'packets' | 'tasks' | 'workflows' | 'overnight'; const RISK_COLOR: Record<string, string> = {; const STATUS_COLOR: Record<string, string> = {; const OVERNIGHT_SAFETY_COLOR: Record<string, string> = {; export function WorkPanel() {; const [activeTab, setActiveTab] = useState<WorkTab>('packets')
### `cockpit/src/renderer/panels/WorkflowsPanel.tsx`
- Lines: 51. Definitions/exports: export function WorkflowsPanel() {; const workflows = useTaskStore((s) => s.workflows); const fetchWorkflows = useTaskStore((s) => s.fetchWorkflows); const triggerWorkflow = useTaskStore((s) => s.triggerWorkflow)
### `cockpit/src/renderer/panels/WorkspacePanel.tsx`
- Lines: 531. Definitions/exports: type Tab = 'files' | 'diff' | 'tests' | 'logs' | 'proof' | 'health'; interface FileEntry {; interface GitChanged {; export function WorkspacePanel() {; const [activeTab, setActiveTab] = useState<Tab>('files'); const tabs: { id: Tab; label: string }[] = [; function FileBrowserPane() {; const [entries, setEntries] = useState<FileEntry[]>([])
### `cockpit/src/renderer/panels/WorkspaceTopologyPanel.tsx`
- Lines: 162. Definitions/exports: const healthColor = (h: string): string => {; const healthLabel = (h: string): string => {; const WorkspaceCard: React.FC<{ ws: WorkspaceEntry }> = ({ ws }) => {; const key = `workspace:${ws.name}`; const expanded = useCollapseStore((s) => s.isOpen(key)); const toggle = useCollapseStore((s) => s.toggle); const WorkspaceTopologyPanel: React.FC = () => {; const { topology, loading, error, fetchTopology } = useWorkspaceTopologyStore();
### `cockpit/src/renderer/panels/WorkstationPanel.tsx`
- Lines: 459. Definitions/exports: type Tab = 'preparation' | 'templates' | 'snapshots' | 'restoration' | 'recommendations'; interface PreparationStep {; interface PreparationPlan {; interface Template {; interface Snapshot {; interface Recommendation {; interface WorkstationState {; function getStepTypeBadge(type: string): string {
### `cockpit/src/renderer/panels/WorldModelPanel.tsx`
- Lines: 650. Definitions/exports: const CONFIDENCE_COLORS = (v: number) =>; const RISK_BADGE: Record<string, string> = {; const TABS = [; function TabBar() {; const tab = useWorldModelStore((s) => s.tab); const setTab = useWorldModelStore((s) => s.setTab); const status = useWorldModelStore((s) => s.status); function WorldTab() {
### `cockpit/src/renderer/stores/actionsStore.ts`
- Lines: 124. Definitions/exports: interface ActionParameter {; interface ActionPrecondition {; interface PreconditionResult {; export interface ActionDefinition {; export interface ActionResult {; interface ActionsState {; export const useActionsStore = create<ActionsState>((set, get) => ({; const url = category
### `cockpit/src/renderer/stores/activityStore.ts`
- Lines: 53. Definitions/exports: interface ActivityEvent {; interface ActivityState {; export const useActivityStore = create<ActivityState>((set) => ({; const data = await fetchApi<ActivityEvent[]>('/activity/stream?limit=200')
### `cockpit/src/renderer/stores/agentStore.ts`
- Lines: 126. Definitions/exports: interface Agent {; interface AgentDetail {; interface AgentState {; export const useAgentStore = create<AgentState>((set, get) => ({; const [basic, organism] = await Promise.all([; const merged = basic.length > 0 ? basic : organism; const deliverables = await fetchApi<AgentDetail['deliverables']>(; const agent = get().agents.find((a) => a.id === id)
### `cockpit/src/renderer/stores/analyticsStore.ts`
- Lines: 124. Definitions/exports: interface ModelUsage {; interface DailyTrace {; interface AnalyticsData {; interface KPICard {; interface PipelineStage {; interface PipelineData {; interface AccountabilityData {; interface IntelligenceData {
### `cockpit/src/renderer/stores/approvalStore.ts`
- Lines: 50. Definitions/exports: interface Approval {; interface ApprovalState {; export const useApprovalStore = create<ApprovalState>((set, get) => ({; const data = await fetchApi<Approval[]>('/approvals')
### `cockpit/src/renderer/stores/bootstrapStore.ts`
- Lines: 261. Definitions/exports: function safeStorage() {; interface BootstrapResponse {; interface SlowBootstrapResponse {; interface BootstrapState {; function seedDownstreamStores(cache: Partial<BootstrapResponse>) {; const aiName = (cache.config.ai_name as string) || import.meta.env.VITE_AI_NAME || 'Assistant'; export function waitForHydration(): Promise<void> {; const unsub = useBootstrapStore.subscribe((s) => {
### `cockpit/src/renderer/stores/broadcastStore.ts`
- Lines: 121. Definitions/exports: export type BroadcastState = 'idle' | 'starting' | 'live' | 'stopping' | 'error'; export type StatusTier = 'HEALTHY' | 'WARNING' | 'CRITICAL'; export interface BroadcastHealthMetrics {; const INITIAL_HEALTH: BroadcastHealthMetrics = {; export interface SceneInfo {; export interface SourceInfo {; export interface NodeInfo {; export interface BroadcastStoreState {
### `cockpit/src/renderer/stores/buildLoopStore.ts`
- Lines: 61. Definitions/exports: interface BuildLoopState {; export const useBuildLoopStore = create<BuildLoopState>((set, get) => ({; const data = await fetchApi<Record<string, unknown>>('/build-loop/status'); const data = await fetchApi<Record<string, unknown>[]>('/build-loop/active'); const data = await fetchApi<Record<string, unknown>[]>('/build-loop/history')
### `cockpit/src/renderer/stores/capabilityIntelligenceStore.ts`
- Lines: 84. Definitions/exports: interface CapabilityIntelligenceState {; export const useCapabilityIntelligenceStore = create<CapabilityIntelligenceState>((set) => ({; const data = await fetchApi<{ portfolio: Record<string, unknown> }>('/capability-intelligence/portfolio'); const data = await fetchApi<{ gaps: Record<string, unknown>[] }>('/capability-intelligence/gaps'); const data = await fetchApi<{ gaps: Record<string, unknown>[] }>('/capability-intelligence/gaps/critical'); const data = await fetchApi<{ edges: Record<string, unknown>[]; summary: Record<string, unknown> }>('/capability-intelligence/graph'); const data = await fetchApi<Record<string, unknown>>('/capability-intelligence/compounding'); const data = await fetchApi<{ bottlenecks: Record<string, unknown>[] }>('/capability-intelligence/bottlenecks')
### `cockpit/src/renderer/stores/capabilityMapStore.ts`
- Lines: 48. Definitions/exports: interface CapabilityMapState {; export const useCapabilityMapStore = create<CapabilityMapState>((set) => ({; const data = await fetchApi<Record<string, unknown>>('/capability-map/snapshot'); const data = await fetchApi<Record<string, unknown>[]>('/capability-map/mvp-gaps'); const data = await fetchApi<Record<string, unknown>[]>('/capability-map/duplications')
### `cockpit/src/renderer/stores/chatStore.ts`
- Lines: 266. Definitions/exports: export interface Provenance {; export interface Attachment {; export interface SuggestedAction {; export interface ChatMessage {; interface ChatResponse {; interface ChatState {; export const useChatStore = create<ChatState>((set, get) => ({; const { targetChannel, conversationId } = get()
### `cockpit/src/renderer/stores/cockpitStore.ts`
- Lines: 180. Definitions/exports: export type Panel =; export type WindowMode = 'maximized' | 'large-fab' | 'medium-fab' | 'small-fab' | 'invisible'; export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected'; const WINDOW_MODE_ORDER: WindowMode[] = ['maximized', 'large-fab', 'medium-fab', 'small-fab', 'invisible']; interface CockpitState {; export const useCockpitStore = create<CockpitState>()(; const redirects: Partial<Record<Panel, Panel>> = {; const idx = WINDOW_MODE_ORDER.indexOf(s.windowMode)
### `cockpit/src/renderer/stores/coherenceStore.ts`
- Lines: 249. Definitions/exports: interface TemplateSummary {; interface TemplateData {; interface CapabilityDetail {; interface AgentProfile {; interface AgentCapabilityData {; interface PropagationEventSummary {; interface PropagationData {; interface SandboxSummary {
### `cockpit/src/renderer/stores/collapseStore.ts`
- Lines: 34. Definitions/exports: interface CollapseState {; export const useCollapseStore = create<CollapseState>()(; const v = get().sections[key]
### `cockpit/src/renderer/stores/configStore.ts`
- Lines: 79. Definitions/exports: interface UmhConfig {; interface ConfigState {; const FALLBACK_AI_NAME = import.meta.env.VITE_AI_NAME || 'Assistant'; const DEFAULT_CONFIG: UmhConfig = {; export const useConfigStore = create<ConfigState>((set, get) => ({; const data = await fetchApi<UmhConfig>('/config'); const aiName = (data.ai_name as string) || FALLBACK_AI_NAME; const prev = get().config
### `cockpit/src/renderer/stores/delegationStore.ts`
- Lines: 134. Definitions/exports: interface DelegationState {; export const useDelegationStore = create<DelegationState>((set, get) => ({; const data = await fetchApi<Record<string, unknown>>('/delegation/summary'); const path = status ? `/delegation/proposals?status=${status}` : '/delegation/proposals'; const data = await fetchApi<Record<string, unknown>[]>(path); const path = status ? `/delegation/missions?status=${status}` : '/delegation/missions'; const data = await fetchApi<Record<string, unknown>[]>(path); const data = await fetchApi<Record<string, unknown>[]>('/delegation/missions/active')
### `cockpit/src/renderer/stores/deviceSessionStore.ts`
- Lines: 164. Definitions/exports: export interface VoiceRouteInfo {; type ClientType = 'mobile_browser' | 'desktop_browser' | 'electron' | 'terminal'; interface DeviceSessionState {; function detectClientType(): ClientType {; const ua = navigator.userAgent || ''; const mobile = /Mobi|Android|iPhone|iPad/i.test(ua) || window.innerWidth < 768; function deriveControlSurface(clientType: ClientType): string {; const host = typeof window !== 'undefined' ? window.location.hostname : ''
### `cockpit/src/renderer/stores/editorStore.ts`
- Lines: 219. Definitions/exports: interface FileNode {; interface OpenFile {; interface SessionInfo {; interface EditorState {; function detectLanguage(name: string): string {; const ext = name.split('.').pop()?.toLowerCase() || ''; const map: Record<string, string> = {; export const useEditorStore = create<EditorState>((set, get) => ({
### `cockpit/src/renderer/stores/engineeringStore.ts`
- Lines: 368. Definitions/exports: interface EngineeringPlan {; interface PlanReceipt {; interface GapAnalysis {; interface GapRecommendation {; interface EngineeringSession {; interface EngineeringProofPackage {; interface EngineeringState {; export const useEngineeringStore = create<EngineeringState>((set) => ({
### `cockpit/src/renderer/stores/executionStore.ts`
- Lines: 161. Definitions/exports: export type ExecutionLayer = 'native' | 'container' | 'wsl' | 'vm'; interface ActionLogEntry {; interface ExecutionSlot {; interface AuthorityPreview {; interface ExecutionState {; export const useExecutionStore = create<ExecutionState>((set, get) => ({; const data = await fetchApi<{ slots: Array<{; const data = await fetchApi<{ slot: number; log: ActionLogEntry[] }>(
### `cockpit/src/renderer/stores/executiveStore.ts`
- Lines: 174. Definitions/exports: interface AllocationRecommendation {; interface ResourceBudget {; interface DriftWarning {; interface TradeoffAnalysis {; interface ExecutiveOverview {; interface ExecutiveStore {; const API_BASE = '/api'; export const useExecutiveStore = create<ExecutiveStore>((set) => ({
### `cockpit/src/renderer/stores/goalStore.ts`
- Lines: 96. Definitions/exports: interface GoalState {; export const useGoalStore = create<GoalState>((set) => ({; const data = await fetchApi<{ goals: Record<string, unknown>[] }>('/goals/active'); const data = await fetchApi<Record<string, unknown>>('/goals/tree'); const data = await fetchApi<Record<string, unknown>>('/goals/plans/roadmap'); const data = await fetchApi<Record<string, unknown>>('/goals/alignment/report'); const data = await fetchApi<Record<string, unknown>>('/goals/outcomes/snapshot'); const data = await fetchApi<Record<string, unknown>>('/goals/drift/summary')
### `cockpit/src/renderer/stores/governanceStore.ts`
- Lines: 202. Definitions/exports: interface SubsystemConflict {; interface GovernancePolicy {; interface SubsystemHealthEntry {; interface OrganismDriftWarning {; interface OrganismOverview {; interface CoordinationSnapshot {; interface InstitutionalMemorySnapshot {; interface GovernanceStore {
### `cockpit/src/renderer/stores/intelligenceStore.ts`
- Lines: 127. Definitions/exports: interface BottleneckEvidence {; interface Bottleneck {; interface LeverageEvidence {; interface LeverageOpportunity {; interface ActionEvidence {; interface NextAction {; interface DimensionScore {; interface ReadinessData {
### `cockpit/src/renderer/stores/intentStore.ts`
- Lines: 89. Definitions/exports: export interface CanonicalIntent {; export interface IntentConflict {; interface IntentState {; export const useIntentStore = create<IntentState>((set) => ({; const data = await fetchApi('/api/umh/intent/active'); const data = await fetchApi('/api/umh/intent/summary'); const data = await fetchApi('/api/umh/intent/conflicts'); const data = await fetchApi('/api/umh/intent/capture', {
### `cockpit/src/renderer/stores/knowledgeStore.ts`
- Lines: 108. Definitions/exports: interface Observation {; interface Skill {; interface MemoryEntry {; interface TrackingEntry {; type ViewMode = 'observations' | 'memory' | 'skills' | 'tracking' | 'reality'; interface KnowledgeState {; export const useKnowledgeStore = create<KnowledgeState>((set) => ({; const data = await fetchApi<Observation[]>('/observations')
### `cockpit/src/renderer/stores/learningStore.ts`
- Lines: 191. Definitions/exports: interface LessonData {; interface PatternData {; interface TrajectoryData {; interface DriftWarning {; interface PortfolioOverview {; interface LearningState {; const API_BASE = '/api'; export const useLearningStore = create<LearningState>((set) => ({
### `cockpit/src/renderer/stores/memoryStore.ts`
- Lines: 136. Definitions/exports: interface MemoryState {; export const useMemoryStore = create<MemoryState>((set) => ({; const url = status ? `/memory/decisions?status=${status}` : '/memory/decisions'; const data = await fetchApi<{ decisions: Record<string, unknown>[] }>(url); const url = status ? `/memory/assumptions?status=${status}` : '/memory/assumptions'; const data = await fetchApi<{ assumptions: Record<string, unknown>[] }>(url); const data = await fetchApi<{ assumptions: Record<string, unknown>[] }>('/memory/assumptions/invalidated'); const data = await fetchApi<{ snapshot: Record<string, unknown> | null }>('/memory/snapshot')
### `cockpit/src/renderer/stores/metaIDEStore.ts`
- Lines: 311. Definitions/exports: interface RepositoryHealth {; interface Branch {; interface Worktree {; interface Repository {; interface RiskItem {; interface Phase {; interface RoadmapData {; interface WorkspaceData {
### `cockpit/src/renderer/stores/mvpReadinessStore.ts`
- Lines: 78. Definitions/exports: interface MvpReadinessState {; export const useMvpReadinessStore = create<MvpReadinessState>((set) => ({; const data = await fetchApi<Record<string, unknown>>('/mvp-readiness/assess'); const data = await fetchApi<{ score: number }>('/mvp-readiness/score'); const data = await fetchApi<string[]>('/mvp-readiness/blockers'); const data = await fetchApi<Record<string, unknown>[]>('/mvp-readiness/escape-points'); const data = await fetchApi<string[]>(`/mvp-readiness/next?limit=${limit}`)
### `cockpit/src/renderer/stores/operatingLoopStore.ts`
- Lines: 96. Definitions/exports: interface OperatingLoopState {; export const useOperatingLoopStore = create<OperatingLoopState>((set, get) => ({; const data = await fetchApi<Record<string, unknown>[]>('/operating-loop/active'); const data = await fetchApi<Record<string, unknown>[]>(`/operating-loop/completed?limit=${limit}`); const data = await fetchApi<Record<string, unknown>>('/operating-loop/snapshot'); const data = await fetchApi<Record<string, unknown>>(`/operating-loop/${id}`); const data = await fetchApi<Record<string, unknown>[]>(`/operating-loop/${id}/trace`)
### `cockpit/src/renderer/stores/operationsStore.ts`
- Lines: 60. Definitions/exports: interface OperationsState {; export const useOperationsStore = create<OperationsState>((set) => ({; const data = await fetchApi<Record<string, unknown>>('/execution-fabric/snapshot'); const data = await fetchApi<Record<string, unknown>>('/agent-workforce/snapshot'); const data = await fetchApi<Record<string, unknown>>('/session-machine/snapshot'); const store = useOperationsStore.getState()
### `cockpit/src/renderer/stores/operatorExperienceStore.ts`
- Lines: 377. Definitions/exports: interface OperatorOverview {; interface StatusResponse {; interface ApprovalResponse {; interface ApprovalItem {; interface OperatorExperienceState {; function generateSessionId(): string {; function parseDexResponse(data: Record<string, unknown>): DexResponse {; export const useOperatorExperienceStore = create<OperatorExperienceState>((set, get) => {
### `cockpit/src/renderer/stores/operatorHomeStore.ts`
- Lines: 106. Definitions/exports: interface StatusCard {; interface HealthSummary {; interface AttentionItem {; interface TimelineEvent {; interface OperatorSnapshot {; interface OperatorHomeState {; export const useOperatorHomeStore = create<OperatorHomeState>((set) => ({; const resp = await fetch('/api/umh/operator/home');
### `cockpit/src/renderer/stores/operatorLoopStore.ts`
- Lines: 1554. Definitions/exports: interface LoopStatus {; export interface PacketSummary {; export interface PacketDetail extends PacketSummary {; export interface ValidationResult {; export interface SandboxDetail {; export interface AuditEntry {; export type ExecutionMode = 'validate_only' | 'implement' | 'implement_and_validate'; export interface IntentContract {
### `cockpit/src/renderer/stores/operatorTimelineStore.ts`
- Lines: 44. Definitions/exports: interface TimelineEntry {; interface OperatorTimelineState {; export const useOperatorTimelineStore = create<OperatorTimelineState>((set) => ({; const data = await fetchApi<{ timeline: TimelineEntry[]; total: number }>(
### `cockpit/src/renderer/stores/orchestratorAwarenessStore.ts`
- Lines: 67. Definitions/exports: interface OrchestratorAwarenessState {; export const useOrchestratorAwarenessStore = create<OrchestratorAwarenessState>((set) => ({; const data = await fetchApi<Record<string, unknown>>('/orchestrator/context'); const data = await fetchApi<Record<string, unknown>>('/orchestrator/snapshot'); const data = await fetchApi<Record<string, unknown>[]>('/orchestrator/health'); const data = await fetchApi<{ awareness_score: number }>('/orchestrator/score'); const data = await fetchApi<Record<string, unknown>>(`/orchestrator/awareness/${domain}`)
### `cockpit/src/renderer/stores/organismLoopStore.ts`
- Lines: 86. Definitions/exports: interface CycleEventData {; interface CycleEvent {; interface LoopResult {; interface OrganismLoopState {; export const useOrganismLoopStore = create<OrganismLoopState>((set) => ({; const data = await fetchApi<{ cycles: CycleEvent[]; count: number }>(; const body: Record<string, string> = { intent }; const result = await fetchApi<LoopResult>('/organism/loop/execute', {
### `cockpit/src/renderer/stores/organismMapStore.ts`
- Lines: 70. Definitions/exports: interface TopologyNode {; interface TopologyEdge {; interface OrganismMapState {; export const useOrganismMapStore = create<OrganismMapState>((set) => ({; const data = await fetchApi('/api/umh/organism-map/topology'); const data = await fetchApi('/api/umh/organism-map/health'); const data = await fetchApi(`/api/umh/organism-map/node/${encodeURIComponent(nodeId)}`)
### `cockpit/src/renderer/stores/organismStore.ts`
- Lines: 474. Definitions/exports: interface SpineStats {; interface EnvelopeRecord {; interface JournalEntry {; interface JournalStats {; interface GatewayDecision {; interface GatewayStatus {; interface GuardStatus {; interface Bottleneck {
### `cockpit/src/renderer/stores/predictionStore.ts`
- Lines: 139. Definitions/exports: interface ForecastData {; interface ScenarioData {; interface DriftWarning {; interface PredictionOverview {; interface PredictionState {; const API_BASE = '/api'; export const usePredictionStore = create<PredictionState>((set) => ({; const res = await fetch(`${API_BASE}/prediction/overview`)
### `cockpit/src/renderer/stores/presenceStore.ts`
- Lines: 120. Definitions/exports: interface PresenceState {; interface ActiveContext {; interface ContinuityCheckpoint {; interface PresenceSnapshot {; interface PresenceTransition {; interface ResumeSuggestion {; interface PresenceStoreState {; const API_BASE = "/api/umh/presence";
### `cockpit/src/renderer/stores/projectionIntegrationStore.ts`
- Lines: 79. Definitions/exports: interface ProjectionIntegrationState {; export const useProjectionIntegrationStore = create<ProjectionIntegrationState>((set) => ({; const data = await fetchApi<Record<string, unknown>>('/projections/integration/snapshot'); const data = await fetchApi<Record<string, unknown>>(`/projections/integration/profile/${id}`); const data = await fetchApi<Record<string, unknown>[]>(`/projections/integration/locations/${id}`); const data = await fetchApi<Record<string, unknown>[]>(`/projections/integration/gaps/${id}`); const data = await fetchApi<Record<string, unknown>>(`/projections/integration/readiness/${id}`)
### `cockpit/src/renderer/stores/providerRegistryStore.ts`
- Lines: 86. Definitions/exports: interface Provider {; interface ProviderRegistryState {; const KNOWN_PROVIDERS: Provider[] = [; export const useProviderRegistryStore = create<ProviderRegistryState>((set) => ({; const models = await fetchApi<Record<string, unknown>>('/models').catch(() => null); const infra = await fetchApi<Record<string, unknown>>('/infra').catch(() => null); const hasGemini = JSON.stringify(models).toLowerCase().includes('gemini'); const hasOllama = JSON.stringify(infra).toLowerCase().includes('ollama')
### `cockpit/src/renderer/stores/realityGraphStore.ts`
- Lines: 243. Definitions/exports: interface RealityEntity {; interface GraphSummary {; interface ResolvedContext {; interface ArtifactEntry {; interface RepositorySnapshot {; interface DocumentationSnapshot {; interface RuntimeAwarenessSnapshot {; interface KnowledgeSnapshot {
### `cockpit/src/renderer/stores/realityIntelligenceStore.ts`
- Lines: 135. Definitions/exports: interface RealityEvidence {; interface RealityQueryResult {; type QueryType = 'why' | 'what_changed' | 'evidence' | 'contradictions' | 'lineage' | 'domain_summary' | 'priorities'; interface RealityIntelligenceState {; export const useRealityIntelligenceStore = create<RealityIntelligenceState>((set) => ({; const data = await fetchApi<RealityQueryResult>(; const data = await fetchApi<RealityQueryResult>(; const data = await fetchApi<RealityQueryResult>(
### `cockpit/src/renderer/stores/realityTimelineStore.ts`
- Lines: 67. Definitions/exports: interface RealityObservation {; interface RealityTimelineState {; export const useRealityTimelineStore = create<RealityTimelineState>((set, get) => ({; const { filterDomain, filterSource } = get(); const params = new URLSearchParams(); const data = await fetchApi<{
### `cockpit/src/renderer/stores/realtimeStore.ts`
- Lines: 155. Definitions/exports: export interface NodeGpuMetrics {; export interface NodeMetrics {; export interface OrganismEvent {; export type RealtimeStatus = 'connected' | 'connecting' | 'disconnected' | 'fallback'; export type EventDomainFilter =; const MAX_EVENTS = 500; const MAX_EVENT_IDS = 1000; interface RealtimeState {
### `cockpit/src/renderer/stores/roomsStore.ts`
- Lines: 1043. Definitions/exports: const API = '/rooms'; export interface CreateInviteOptions {; interface RoomsState {; const STORAGE_KEY = 'rooms:lastActive'; function loadLastActive(): { serverId: string | null; channelId: string | null } {; const raw = localStorage.getItem(STORAGE_KEY); function saveLastActive(serverId: string | null, channelId: string | null) {; const lastActive = loadLastActive()
### `cockpit/src/renderer/stores/screenAwarenessStore.ts`
- Lines: 176. Definitions/exports: interface FocusedApplication {; interface ActiveWindow {; interface RepositoryContext {; interface FileContext {; interface BrowserContext {; interface ScreenSnapshot {; interface ProviderStatus {; interface VisualContext {
### `cockpit/src/renderer/stores/serviceGraphStore.ts`
- Lines: 82. Definitions/exports: interface ServiceNode {; interface FailureImpact {; interface CriticalPathEntry {; interface ServiceGraphState {; export const useServiceGraphStore = create<ServiceGraphState>((set) => ({; const resp = await fetch('/api/umh/service-graph/services');; const data = await resp.json();; const resp = await fetch(`/api/umh/service-graph/impact/${serviceRole}`);
### `cockpit/src/renderer/stores/settingsStore.ts`
- Lines: 76. Definitions/exports: interface ModelRoute {; interface GovernancePolicy {; interface GovernanceData {; interface SettingsData {; interface SettingsState {; export const useSettingsStore = create<SettingsState>((set) => ({; const data = await fetchApi<SettingsData>('/settings'); const data = await fetchApi<GovernanceData>('/governance')
### `cockpit/src/renderer/stores/stateAuthorityStore.ts`
- Lines: 65. Definitions/exports: interface StateAuthority {; interface DomainCoherenceReport {; interface CoherenceReport {; interface StateAuthorityState {; export const useStateAuthorityStore = create<StateAuthorityState>((set) => ({; const resp = await fetch('/api/umh/state-authority/domains');; const data = await resp.json();; const resp = await fetch('/api/umh/state-authority/coherence');
### `cockpit/src/renderer/stores/strategicStore.ts`
- Lines: 85. Definitions/exports: interface StrategicState {; export const useStrategicStore = create<StrategicState>((set) => ({; const data = await fetchApi<Record<string, unknown>>('/strategic/context'); const data = await fetchApi<{ priorities: Record<string, unknown>[] }>('/strategic/priorities/top?limit=10'); const data = await fetchApi<{ risks: Record<string, unknown>[] }>('/strategic/risks'); const data = await fetchApi<{ recommendations: Record<string, unknown>[] }>('/strategic/recommendations'); const data = await fetchApi<{ drift_warnings: Record<string, unknown>[] }>('/strategic/drift'); const data = await fetchApi<Record<string, unknown>>('/strategic/brief')
### `cockpit/src/renderer/stores/systemStore.ts`
- Lines: 225. Definitions/exports: interface NodeGpuMetrics {; interface NodeMetricsEntry {; interface PulseData {; interface MeshNode {; export interface ModelBadge {; export interface TraceEvent {; export interface InfraNode {; interface RawTask {
### `cockpit/src/renderer/stores/taskStore.ts`
- Lines: 72. Definitions/exports: interface Task {; interface Workflow {; type ViewMode = 'tasks' | 'workflows' | 'timeline'; interface TaskState {; export const useTaskStore = create<TaskState>((set, get) => ({; const data = await fetchApi<Task[]>('/tasks'); const data = await fetchApi<Workflow[]>('/workflows')
### `cockpit/src/renderer/stores/umhNodeStore.ts`
- Lines: 85. Definitions/exports: interface UMHNodeService {; interface UMHNodeVersion {; interface UMHNode {; interface UMHNodeTopology {; interface UMHNodeState {; export const useUMHNodeStore = create<UMHNodeState>((set) => ({; const resp = await fetch('/api/umh/umh-nodes');; const data = await resp.json();
### `cockpit/src/renderer/stores/unifiedApprovalStore.ts`
- Lines: 82. Definitions/exports: interface UnifiedApprovalState {; export const useUnifiedApprovalStore = create<UnifiedApprovalState>((set, get) => ({; const q = sourceType ? `?source_type=${sourceType}` : ''; const data = await fetchApi<Record<string, unknown>[]>(`/unified-approval/pending${q}`); const data = await fetchApi<Record<string, unknown>[]>(`/unified-approval/by-urgency?limit=${limit}`); const data = await fetchApi<Record<string, unknown>>('/unified-approval/snapshot'); const data = await fetchApi<Record<string, unknown>[]>(`/unified-approval/decisions?limit=${limit}`)
### `cockpit/src/renderer/stores/unifiedExecutionStore.ts`
- Lines: 72. Definitions/exports: interface UnifiedExecutionState {; export const useUnifiedExecutionStore = create<UnifiedExecutionState>((set, get) => ({; const data = await fetchApi<Record<string, unknown>>('/unified-execution/snapshot'); const data = await fetchApi<Record<string, unknown>[]>('/unified-execution/streams/active'); const data = await fetchApi<Record<string, unknown>[]>('/unified-execution/approvals/pending')
### `cockpit/src/renderer/stores/unifiedWorkstationStore.ts`
- Lines: 36. Definitions/exports: interface UnifiedWorkstationState {; export const useUnifiedWorkstationStore = create<UnifiedWorkstationState>((set) => ({; const data = await fetchApi<Record<string, unknown>>('/unified-workstation/snapshot'); const data = await fetchApi<{ total: number; critical: number }>('/attention/count')
### `cockpit/src/renderer/stores/viewContextStore.ts`
- Lines: 87. Definitions/exports: export interface ViewContext {; interface ViewContextState {; export const useViewContextStore = create<ViewContextState>((set) => ({
### `cockpit/src/renderer/stores/visionStore.ts`
- Lines: 1289. Definitions/exports: export interface OverlayMetadata {; export type CameraStatus = 'off' | 'connecting' | 'live' | 'analyzing' | 'error'; export type CameraMode = 'manual' | 'follow' | 'watch' | 'ai_assist'; export type ControlAuthority = 'operator' | 'voice' | 'ai' | 'autonomous'; export interface AuthorityLogEntry {; export interface AuthorityState {; export interface RelayPipelineMetrics {; export interface BeastStreamMetrics {
### `cockpit/src/renderer/stores/voiceSessionStore.ts`
- Lines: 1221. Definitions/exports: type TrackPublication,; const MAX_STREAMS_PER_USER = 4; const MAX_RECONNECT_ATTEMPTS = 5; const INITIAL_BACKOFF_MS = 1000; const TOKEN_CACHE_TTL_MS = 25000; const RECONNECT_WATCHDOG_MS = 3000; const DATA_CHAT_TOPIC = 'umh-chat'; function nextActionId(): number { return ++actionIdCounter }
### `cockpit/src/renderer/stores/voiceStore.ts`
- Lines: 135. Definitions/exports: export type MicState =; export type TtsState = 'idle' | 'generating_tts' | 'ready_to_speak' | 'speaking' | 'tts_failed'; export type ActivationMode = 'manual' | 'wake_word' | 'clap' | 'always_on'; export type PresentationStatus =; export interface OrganismResponseEnvelope {; export type VoiceOutcome =; interface VoiceState {; export const useVoiceStore = create<VoiceState>((set) => ({
### `cockpit/src/renderer/stores/workIntelligenceStore.ts`
- Lines: 124. Definitions/exports: interface WorkIntelligenceState {; export const useWorkIntelligenceStore = create<WorkIntelligenceState>((set) => ({; const data = await fetchApi<Record<string, unknown>>('/work-intelligence/overview'); const data = await fetchApi<{ ready: Record<string, unknown>[] }>('/work-intelligence/ready'); const data = await fetchApi<{ blocked: Record<string, unknown>[] }>('/work-intelligence/blocked'); const data = await fetchApi<Record<string, unknown>>('/work-intelligence/delegation'); const data = await fetchApi<{ drift: Record<string, unknown>[] }>('/work-intelligence/drift'); const data = await fetchApi<Record<string, unknown>>('/work-intelligence/velocity')
### `cockpit/src/renderer/stores/workspaceTopologyStore.ts`
- Lines: 91. Definitions/exports: interface WorkspaceTopology {; interface WorkspaceEntry {; interface Repository {; interface Runtime {; interface BuildTarget {; interface WorkspaceTopologyState {; const API_BASE = '/api/umh/workspace-topology';; export const useWorkspaceTopologyStore = create<WorkspaceTopologyState>((set) => ({
### `cockpit/src/renderer/stores/workstationSessionStore.ts`
- Lines: 79. Definitions/exports: interface WorkstationSessionState {; export const useWorkstationSessionStore = create<WorkstationSessionState>((set, get) => ({; const data = await fetchApi<Record<string, unknown>>('/wk-session/active'); const data = await fetchApi<Record<string, unknown>[]>(`/wk-session/history?limit=${limit}`); const data = await fetchApi<Record<string, unknown>>(`/wk-session/${sessionId}/checkpoint`)
### `cockpit/src/renderer/stores/worldModelStore.ts`
- Lines: 249. Definitions/exports: interface CanonicalPattern {; interface PatternDetail extends CanonicalPattern {; interface PatternRelationship {; interface CanonicalStats {; interface InstanceStats {; interface RealityModelStatus {; interface InstanceObservation {; interface DomainCount {
### `cockpit/src/renderer/types/rooms.ts`
- Lines: 382. Definitions/exports: export type ChannelType =; export type ServerPrivacy = 'private' | 'internal' | 'client_facing' | 'community'; export type ServerTemplate =; export type PresenceStatus = 'online' | 'away' | 'busy' | 'offline'; export type MemberRole = 'owner' | 'admin' | 'moderator' | 'member' | 'guest' | 'client'; export type DexRoomMode =; export type MeetingMode =; export type RoomPermission =
### `cockpit/src/renderer/types/routes.ts`
- Lines: 154. Definitions/exports: export interface RouteEntry {; export const ROUTES: RouteEntry[] = [; export const ROUTE_GROUPS = [
### `cockpit/src/renderer/types/rrip.ts`
- Lines: 67. Definitions/exports: export type RRIPRole = 'operator' | 'dex' | 'system' | 'agent' | 'external'; export type RRIPKind =; export interface RRIPRouting {; export interface RRIPProvenance {; export interface RRIPAttachment {; export interface RRIPSuggestedAction {; export interface RRIPApprovalData {; export interface RRIPMessage {
### `scripts/userscript_meet_captions.example.js`
- Lines: 83. Definitions/exports: const ENDPOINT = "http://localhost:8799/caption";; const MEETING_CODE = location.pathname.replace(/^\//, "") || "unknown";; const SOURCE = "google_meet";; const seen = new Map();; const DEDUP_MS = 4000;; function nowIsoUtc() {; function post(record) {; function handleCaption(speaker, text) {
### `transports/api/http/db/client.ts`
- Lines: 92. Definitions/exports: const adminUrl = process.env.DATABASE_URL; const appUrl   = process.env.DATABASE_APP_URL ?? process.env.DATABASE_URL; const adminPool = new Pool({ connectionString: adminUrl }); export const db = drizzle(adminPool, { schema }); const appPool = new Pool({ connectionString: appUrl }); export const appDb = drizzle(appPool, { schema }); export async function withOrg<T>(; export async function closeDb() {
### `transports/api/http/db/migrate.ts`
- Lines: 168. Definitions/exports: const pool = new Pool({ connectionString: process.env.DATABASE_URL }); const db = drizzle(pool); const TENANT_TABLES = [; const ORG_ISOLATION_EXPR = (table: string) =>
### `transports/api/http/db/schema.ts`
- Lines: 222. Definitions/exports: type AnyPgColumn,; export const orgPlanEnum = pgEnum('org_plan', [; export const memberRoleEnum = pgEnum('member_role', [; export const approvalStatusEnum = pgEnum('approval_status', [; export const vectorType = customType<{; export const tokensJsonSchema = z.object({; export type TokensJson = z.infer<typeof tokensJsonSchema>; export const users = pgTable('users', {
### `transports/api/http/drizzle.config.ts`
- Lines: 14. Definitions/exports: -
### `transports/api/http/lib/python_bridge.ts`
- Lines: 55. Definitions/exports: const __dirname = dirname(fileURLToPath(import.meta.url)); const AGENT_BRIDGE    = resolve(__dirname, '../../agent_bridge.py'); const ORGANISM_BRIDGE = resolve(__dirname, '../../organism_bridge.py'); export interface BridgeResult {; function _callPython(bridgePath: string, payload: Record<string, unknown>): Promise<BridgeResult> {; const proc = spawn('python3', [bridgePath], {; const parsed = JSON.parse(out); export async function callBridge(payload: Record<string, unknown>): Promise<BridgeResult> {
### `transports/api/http/middleware/auth.ts`
- Lines: 35. Definitions/exports: const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i; export async function authMiddleware(c: Context<Env>, next: Next) {; const orgId = c.req.header('x-org-id'); const rows = await db
### `transports/api/http/middleware/operator.ts`
- Lines: 38. Definitions/exports: export async function operatorGuard(c: Context<Env>, next: Next) {; const orgId = c.get('orgId'); const userId = c.get('userId'); const rows = await db
### `transports/api/http/routes/chat.ts`
- Lines: 49. Definitions/exports: const router = new Hono<Env>(); const body = await c.req.json() as { content: string }; const content = body.content?.trim(); const result = await callOrganism('organism.converse', { content }); const data = result.data as Record<string, unknown> | undefined; const body = await c.req.json().catch(() => ({})) as Record<string, unknown>; const result = await callOrganism('organism.send_channel_message', body); const result = await callOrganism('organism.chat_history', { limit: 50 })
### `transports/api/http/routes/config.ts`
- Lines: 42. Definitions/exports: const router = new Hono<Env>(); const result = await callOrganism('config.get'); const key = c.req.param('key'); const result = await callOrganism('config.get', { key }); const body = await c.req.json().catch(() => ({})) as Record<string, unknown>; const key = body.key as string | undefined; const value = body.value; const layer = (body.layer as string) || 'system'
### `transports/api/http/routes/execution.ts`
- Lines: 126. Definitions/exports: const router = new Hono<Env>(); const [workcells, governor, snapshot] = await Promise.all([; const govData = governor.data as Record<string, unknown> | undefined; const snapData = snapshot.data as Record<string, unknown> | undefined; const workUnits = (snapData?.work_units ?? {}) as Record<string, number>; const slots = [; const slot = Number(c.req.query('slot') ?? 0); const result = await callOrganism('organism.economy.records', { limit: 20 })
### `transports/api/http/routes/governance.ts`
- Lines: 51. Definitions/exports: const router = new Hono<Env>(); const result = await callOrganism('organism.governor'); const gov = result.data as Record<string, unknown>; const approvalMap = (gov.approval_map ?? {}) as Record<string, string>; const policies = Object.entries(approvalMap).map(([scope, level]) => ({
### `transports/api/http/routes/knowledge.ts`
- Lines: 105. Definitions/exports: const router = new Hono<Env>(); const result = await callOrganism('organism.snapshot'); const snap = result.data as Record<string, unknown>; const objectives = (snap.objectives ?? {}) as Record<string, number>; const workUnits = (snap.work_units ?? {}) as Record<string, number>; const bottlenecks = (snap.bottlenecks ?? []) as Array<Record<string, unknown>>; const observations: Array<Record<string, unknown>> = []; const result = await callOrganism('organism.learning', { limit: 50 })
### `transports/api/http/routes/organism.ts`
- Lines: 661. Definitions/exports: const router = new Hono<Env>(); const result = await callOrganism('organism.snapshot'); const result = await callOrganism('organism.status'); const result = await callOrganism('organism.health'); const result = await callOrganism('organism.agents'); const agentId = c.req.query('agent_id'); const limit = Number(c.req.query('limit') ?? 50); const result = await callOrganism('organism.deliverables', { agent_id: agentId, limit })
### `transports/api/http/routes/settings.ts`
- Lines: 53. Definitions/exports: const router = new Hono<Env>(); const [runtimes, governor] = await Promise.all([; const govData = governor.data as Record<string, unknown> | undefined; const rtData = runtimes.data as Record<string, unknown> | undefined; const nodes = ((rtData?.nodes ?? []) as Array<Record<string, unknown>>); const modelRouting = nodes.length > 0
### `transports/api/http/routes/system.ts`
- Lines: 261. Definitions/exports: interface RegistryEntry {; function loadDeviceRegistry(): RegistryEntry[] {; const root = process.env.UMH_ROOT ?? '/opt/OS'; const router = new Hono<Env>(); function safeExecFile(cmd: string, args: string[], fallback = ''): string {; const cpus = os.cpus(); const cpuIdle = cpus.reduce((sum, cpu) => sum + cpu.times.idle, 0); const cpuTotal = cpus.reduce(
### `transports/api/http/server.ts`
- Lines: 63. Definitions/exports: const app = new Hono<Env>(); const PORT = Number(process.env.UMH_API_PORT ?? process.env.PORT ?? 3000)
### `transports/api/http/types.ts`
- Lines: 11. Definitions/exports: export type Env = {

## Developer Warnings
- Verify imports for any touched module before done.
- Prefer substrate runtime changes over duplicating behavior in route or UI layers.
- Do not treat `data/`, `logs/`, `.playwright-mcp/`, screenshots, or generated reports as canonical source unless the task is about state/evidence.
- CPU gate law in `CLAUDE.md` requires gated subprocess wrappers in runtime code.
- LLM routing order from AGENTS.md is `cc_sdk` -> Gemini 2.5 Flash -> Groq -> Ollama.
