# UMH One-Shot Convergence Audit — Coverage Proof

**Date:** 2026-07-04
**Repo under audit:** `/opt/OS/.claude/worktrees/umh-convergence-audit` (read-only; no source file modified)
**Companion deliverables:** [UMH_ONE_SHOT_CONVERGENCE_GAP_ANALYSIS.md](UMH_ONE_SHOT_CONVERGENCE_GAP_ANALYSIS.md) (§17 carries the condensed form of this proof) · [UMH_CANONICAL_PRIMITIVE_MAP.md](UMH_CANONICAL_PRIMITIVE_MAP.md) · [UMH_EXECUTION_SPINE_COMPLIANCE.md](UMH_EXECUTION_SPINE_COMPLIANCE.md) (§2.8 = out-of-scope surface classification) · [UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md](UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md) · [UMH_PROJECTION_CAPABILITY_MATRIX.md](UMH_PROJECTION_CAPABILITY_MATRIX.md) (row 47 + footnote 40) · [UMH_WORK_PACKET_BACKLOG.md](UMH_WORK_PACKET_BACKLOG.md) · `schemas/convergence/` (6 JSON Schemas)

**Purpose.** This document justifies why the gap analysis is complete enough to act on — and states, without hedging, where it is not. Coverage claims below are quoted from the 17 Phase-1 evidence ledgers' own Coverage sections and the machine-readable index (`_index.json`), cross-checked against `find`/`wc` ground truth where cheap. Where coverage was sampled, it says sampled. Where a surface was never inspected, it says blind.

---

## 1. Method

Three-stage pipeline:

**Stage 1 — 17-workstream evidence fan-out.** Seventeen parallel auditor workstreams, each with a bounded scope, a mandated Coverage section, and a read-only constraint:

| Group | Workstreams | Scope |
|---|---|---|
| A | A | Repository architecture, layer contract, entrypoints, enforcement gates |
| B | B1–B4 | 33 canonical primitives (6 + 8 + 9 + 10), competing-implementation tables |
| C | C1–C3 | Execution spine compliance: Python mutation core; API write surfaces; non-API mutation paths (services, cron, mesh, adapters, projections) |
| D | D1–D2 | Ontology/metamodel separation: substrate side; projection domain models + L4 grounding |
| E | E1–E3 | Projection capability extraction: EOS/CreatorOS/LyfeOS; Jarvis/Operator/Workstation/Meta-IDE; Broadcast/Rooms/physical-tier |
| F | F1–F2 | Cockpit convergence: 78 panels + components; 77 stores + API client + backend binding |
| G | G | Runtime node / adapter trust audit |
| H | H | Test / certification audit (377 test files) |

Each ledger records findings with path:line citations, gap candidates with severity, blockers, and an explicit Coverage section (inspected vs NOT inspected vs UNVERIFIED). Output: 270 gap candidates (23 critical / 87 high / 112 medium / 48 low) indexed in `_index.json` with per-workstream `inspected_counts`, `commands_run`, and representative file lists.

**Stage 2 — 6-artifact synthesis with mechanical gap reconciliation.** The ledgers were synthesized into the six deliverables. The work-packet backlog was assembled from three draft parts, cross-group deduplicated, renumbered, and mechanically reconciled against the 270-gap index (every gap ID maps to at least one of the 149 packets; the mapping was recomputed programmatically, not hand-tallied). Six JSON Schemas (`schemas/convergence/`) pin the target shapes for canonical primitives, operation lifecycle, ontology layers, projection capabilities, gap records, and work packets.

**Stage 3 — adversarial verification + patch.** Seven hostile reviewers ran against the finished deliverables: six per-document citation/logic auditors plus one completeness critic auditing the audit itself. Their findings were routed to patch agents and remediated (detail in §7). This document and gap-analysis §17 are themselves products of that pass — the completeness critic's top blocker was that no deliverable disclosed what was NOT inspected.

---

## 2. Directories inspected

Ground truth: **6,955 repo files** (`find`, standard excludes, 2026-07-03 ledger-A measurement; re-measured 2026-07-04: 6,967 — +12 drift). **1,789 graph-indexed Python files** / 5,222 import edges / 628,006 lines (`query_graph stats`); raw `find -name '*.py'` gives 1,973–1,982 (the graph excludes some vendored/data paths — both denominators are cited where used).

Depth classes: **full** = every in-scope file opened or traced by a claiming ledger; **census** = 100% mechanically enumerated + pattern-swept, subset opened; **sampled** = representative subset opened, remainder classified by name/grep; **targeted** = specific files only, package not claimed; **blind** = no ledger claims the directory.

| Directory | Files | Workstream(s) | Depth | Notes / holes |
|---|---|---|---|---|
| substrate/ (990) | | | | broken down below |
| — substrate/organism/ | 387 py | B2, B3, C1, G | census/sampled | C1: 22/22 assigned mutation-core files full; B2/B3 primitive-targeted; G sampled 5 of 71 runtime/workload files; ~250 modules untouched by design (non-mutation, non-primitive) |
| — substrate/execution/ | 137 py (scoped dirs) | C1, G, E2, E3 | sampled | 3 rival spines full (C1); actuation 5/5 full (G); ~70 bridge/ modules grep-only; _dormant/ classified by location |
| — substrate/ontology/, reality_model/, understanding/{ontology,world_model,domains,reality} | 35 targets | D1 | full | 32/35 opened (26 full, 6 partial), 3 empty `__init__.py` wc-verified; 8,295 target lines |
| — substrate/understanding/ (other 9 subpackages) | ~35 of 54 py | — | **blind** | deliberation, interpretation, research, patterns, world_pulse, embedding, intelligence, signals, knowledge — never checked for rival primitives or ungoverned writes |
| — substrate/state/ | 63 py | — | **blind** (3 files targeted) | only canonical_memory_store_v1, transformation_state_ledger, entity_link_store touched; 2026-07-04 grep pass: 27 files carry write-capable patterns, 0 call `governed_mutation` (spine doc §2.8) |
| — substrate/composition/ | 45 py | — | **blind** → grep-classified 2026-07-04 | TME runtime; live (imported by execution spine) with ungoverned queue write; spine doc §2.8, matrix row 47 |
| — substrate/governance/ | 19 py | (grep-cited) | targeted | 3 files reached (execution_authority_engine_v1, risk_classes, validation/completeness_engine); ~16 policy/validation files unclaimed — not swept for rival PolicyDecision/authority types |
| — substrate/contracts/, substrate/intelligence/ | 12 + 4 py | (grep-cited) | targeted | routing_contracts.py, agent_types.py, finetune_harness.py hit individually; packages not claimed |
| — substrate/sockets/ | 22 ports | A | full | 22/22 inventoried with importer counts + registration evidence |
| — substrate/types.py + canonical_types.py | 2 | B1–B4, D1 | full (sectioned) | read first by every B workstream per method |
| transports/api/ | 142 py + 18 ts | A, C2, F2 | census | 143/143 py in C2 matrix (1,306 handlers, 320 mutations, 360 governed sites); 23 full/partial-traced, 120 grep-classified (depth marked per row); 9/9 in-scope TS traced |
| transports/node_mesh/ | 12 py | G, C3 | full | server.py (1,039L) read in full |
| transports/discord/ | 6 py | C3, B3 | sampled | approval_bridge, spine_integration read; signal_factory grep-only |
| transports/presence/ | 23 py | — | **blind** → grep-classified 2026-07-04 | live command-ingress; only substrate_command_handler.py cited in Phase 1, and only as an ImportError site; per-handler classification in spine doc §2.8 |
| transports/cli/ | 7 py | — | **blind** → grep-classified 2026-07-04 | API-key ingress; read-mostly, 1 mutation endpoint (spine doc §2.8) |
| transports/channels/ | 2 py | — | **blind** | |
| adapters/ | 100 py | G, C3 | census | all 100 contract-swept (AdapterRequest/Response, cpu_gate, credentials, rollback); 8/8 named write-capable families opened; notebooklm/scrapling/ssh/tailscale/browser*/data_source_adapters bodies not opened |
| services/ | 23 py | C3, A | census | 23/23 classified, 20 opened |
| projections/ | 59 py | D2, E1, C3 | census | 59/59 enumerated, ~21 opened; EOS agents (11) and workflow bodies (16) classified by grep + pattern; creatoros/lyfeos mirrors spot-verified via grep, marked as such |
| nodes/ | 51 py | G, C3, B1/B2 | sampled | key paths opened (client, governance, work_packet, distributor); camera.py (1,344L), hermes, terminal, umh_desktop bodies not opened |
| cockpit/src/renderer/ | 309 ts/tsx | F1, F2 | census | 78/78 panels endpoint+import-grepped (52 head-sampled, 26 name/evidence-classified); 77/77 stores endpoint-extracted + consumer-mapped (bodies mostly unread); 110 components inventoried, rooms/vision/cards leaf internals unread |
| cockpit backend routes | 119 py | F2, C2 | census | ~1,250 endpoints counted; governed_mutation presence checked in all 119; per-endpoint depth = C2 matrix |
| cockpit/ios/, cockpit/android/ | — | — | not inspected | config-only surfaces per capacitor.config.ts |
| tests/ | 377 py | H | census | 377/377 AST-scanned + clustered; 32 opened; collect-only over 15,017 tests; **zero executed** |
| scripts/ | 146 py | A, C3 | targeted | 6 of 11 check gates executed `--all`; 12 cron-referenced scripts inspected; ~134 manual-ops scripts unenumerated in Phase 1 — grep-censused 2026-07-04: 58 touch external write-capable surfaces (spine doc §2.8) |
| infra/ | 14 | G, C3 | full | 5/5 registries read completely (629 lines); crontab.managed fully read |
| umh/ | 3 py | A, E2 | targeted | heads only; desktop_relay.py + vision_relay.py bodies unread (live WS surfaces — flagged, now cited in gap analysis §10/§17) |
| skills/ | 466 | E2 | census (names only) | 97 tool-skill dirs counted, saas-dev-skill opened; **~460 skill file contents unread** |
| docs/ | 616 | A, E2, E3 | targeted | see §4 |
| data/ | 2,847 | E1, D2 | **blind (bulk)** | 3 vendored schema.ts read in full (2,496 lines), 70 tables inventoried, projection_registry.json read; ~2,800 runtime artifacts/caches/repos uninspected |
| knowledge/ | 344 | — | **blind** | wiki/palace never audited for drift against code |
| agents/ | 11 md | — | **blind** | platform agent soul docs enumerated in ledger A's inventory, contents unreviewed — relevant because B2 found AgentRole fragmented and these are its doc-layer half |
| .agents/ | 64 | — | **blind** | vendored third-party skill packages (executable Python + tests). One verification grep run 2026-07-04: zero references to `.agents/` from any code layer — no runtime import path |
| docker/, config/ | 3 + 1 | — / A | blind / targeted | |

---

## 3. Files and patterns inspected (per workstream)

From `_index.json` `inspected_counts` (each ledger's self-reported, ground-truth-anchored depth):

| WS | Files opened | Pattern/graph sweeps | Denominator claims |
|---|---|---|---|
| A | ~30 | ~30 greps (exhaustive for import direction over all 5 code layers), 6 gates `--all` | 18/18 top-level dirs, 5/5 entrypoints, 22/22 socket ports vs 6,955 files / 1,789 py |
| B1 | 24 | ~30 sweeps + 4 import-verification runs | 6/6 primitives vs 986 substrate py, 377 test files |
| B2 | 29 | ~25 greps + 5 graph/find | 8/8 primitives; execution/runtime 18/18 listed |
| B3 | 24 | ~35 patterns | 9/9 primitives; 28/28 approval classes, 10/10 trace classes, 5/5 MemoryCandidate; 10 of 55 proof-named class files enumerated (sampled) |
| B4 | ~27 + 1 registry | 20+ greps, 7 graph | 10/10 primitives; all 58 Capability* and 37 Projection* hit-lines reviewed |
| C1 | 22/22 assigned full + 9 partial | ~25 grep/graph | 39 state-changing function families classified; gate scan over all 183 route/service files |
| C2 | 23 full/partial-traced + all 9 TS | per-file count greps over 143 files | 143/143 matrix rows sum to total; 1,306 handlers / 320 mutations / 360 governed sites |
| C3 | ~35 deep | ~60 grepped | 23/23 services, 20/20 cron entries, 8/8 adapter families, mesh end-to-end, 3/3 projection writebacks |
| D1 | 32 of 35 targets (+7 supporting) | 9 greps, 3 graph | 35 targets / 8,295 lines |
| D2 | ~34 | ~15 greps, 14 graph | 59/59 projection py, 70/70 vendored tables, 17 L4 mechanisms |
| E1 | ~30 (2,496 schema.ts lines full) | ~25 grep/graph | 27 capability rows × 3 projections vs 1,973 repo py |
| E2 | ~28 | ~35 grep/find, 12 graph | 56+19+18 py enumerated, 142 api py censused, 126 convergence docs listed, 366 test entries |
| E3 | 24 | ~15 structural greps | 10/10 broadcast specs, 10/10 adapters/broadcast, 7/7 actuation+media |
| F1 | 52 of 78 panels head-sampled + 10 shell/nav | 100% endpoint+import grep of 78 panels | 78/78 panels, 110/110 components, 77 stores counted |
| F2 | ~70 renderer + 15 backend | per-store extraction loops | 77/77 stores, 119/119 backend route files, 551 + 148 fetchApi sites classified |
| G | ~35 | ~300 files grep-swept | 5/5 registries, 12/12 node_mesh, 100 adapters swept, 51 nodes key paths |
| H | 32 | AST scan of all 377 + skip/mock/getsource greps | 377/377 clustered (sum verified), 15,017 tests collect-only |

Aggregate: roughly **500 files opened in full or targeted sections**, with mechanical (grep/AST/count) coverage extending to every file in the claimed censuses. The 17 ledgers list 30 representative inspected paths each (510 entries) in `_index.json`.

---

## 4. Documents inspected

Contract/spec canon (read in full): `ARCHITECTURE.md` (550L), `PLATFORM_SPEC.md` (906L; §13–15 re-read by E1), `.claude/rules/architecture-layers.md` (41L).

Strategy/phase/system docs:
- `docs/audits/convergence/` — 126 files listed; 5 deep-read (phase13_0, 13_3s, 13_4, 13_4m, 13_4r — operator-experience series). The other ~121 were used as citations only where other ledgers referenced them.
- `docs/superpowers/specs/broadcast/` — 10/10 enumerated, 7 opened (3 concept specs summarized via the build plan instead — declared); `docs/superpowers/plans/2026-06-12-broadcast-subsystem.md` read.
- `docs/strategy/` — 11 files: 2 section-read (master_intention_lock, empire_architecture), 4 grepped, 5 not inspected (outside E3 physical/broadcast scope).
- `docs/system/strategic_context_amendment_v2_physical_moat_report.md` — full (265L); `docs/system/current_system_status.md`, `docs/sessions/governance.md`, `docs/canonical/umh_synthesis.md`, `docs/phase77_workstation_state_report.md`, `docs/audits/future_trajectory_preservation.md` — read (E2).
- Deployment ground truth: `docker-compose.yml`, `cockpit/nginx.conf.template`, `infra/crontab.managed`, 5 infra registries, `pyproject.toml`, `.github/workflows/` listing, `capacitor.config.ts` + build configs.
- Vendored product schemas: `data/repos/{entrepreneuros,creatoros,LYFEOS}/shared/schema.ts` — all 2,496 lines read.

**Not inspected:** the remaining ~600 `docs/` files and all 344 `knowledge/` files. Doc-layer claims in the deliverables rest on the subset above.

---

## 5. Tests inspected

Workstream H covered the entire `tests/` tree — statically:

- **377/377** test .py files censused and clustered by an ordered-rule AST/name classifier (cluster sums verified = 377). Composition: 364 `test_*.py` + 13 non-test files.
- **32 files opened** (representative across all clusters) to judge assertion quality.
- **AST import-resolution scan of all 377** (no code executed): 4 files with unresolvable repo imports.
- **`pytest --collect-only -q`** over the whole tree: **15,017 tests collected, 3 collection errors, run INTERRUPTED** — full-suite collection is broken (GAP-H-001).
- Pattern census: 29 files pin deleted worktree paths, 155 hardcode `/opt/OS`, 201 skip/xfail markers, 79 files use mocks, 11 assert on `inspect.getsource` strings.
- Supplementary: B1–B4 grep-checked test presence per primitive (presence only — assertion quality UNVERIFIED); E1 collected `tests/test_lyfeos_creatoros_integration.py` (33 tests); `tests/adapters/broadcast/` listed (4 files), not read.

**Zero tests were executed.** All pass/fail claims in the deliverables are about collectability and static content, never runtime results. This is the single largest verification gap in the audit (see §8).

---

## 6. Queries and commands run

`_index.json` records 188 representative commands (182 unique after normalization) across the 17 ledgers; the ledgers' own Scope sections describe larger sweeps behind them (e.g. G's ~300-file grep sweep, F2's per-store loops). Deduplicated by category:

| Category | Listed commands | Notes |
|---|---|---|
| grep sweeps | 103 | class-definition sweeps per primitive across all code layers; import-direction sweeps; per-file handler/mutation count loops; registration checks against canonical_types.py; credential/cpu_gate/rollback sweeps |
| find/ls/wc ground-truth counts | 31 | every ledger anchored denominators independently (6,955 files; 986 substrate py; 377 tests; 78 panels; 77 stores; 119 route files; 59 projection py …) |
| `scripts/query_graph.py` | 27 | 5× `stats` (freshness), ~12× `dependents`, ~10× `search` |
| full-scan check gates | 8 runs | `check_dependency_direction --all` (1,299 files), `check_projection_leak --all` (917), `check_instance_leak --all` (917), `check_cpu_gate --all` (1,307, ×2), `check_type_divergence --all` (exit 1: 46 BLOCKED + 47 warnings), `check_ungoverned_mutations --all` (183, ×2) — 6 of the repo's 11 gates; gates 7–9 (credential/secret/mesh) not run (security scope) |
| import-verification runs | 4 | `python3 -c "import …"` proving 3 ImportErrors + 1 class-name introspection |
| pytest collect-only | 2 | read-only; no execution |
| other | 13 | awk sums, comm diffs, sed section reads, systemd/ps observations (host-level, marked as such) |

**query_graph.py reliability caveat (declared in ledgers, carried here):** `dependents` misses lazy function-scoped imports (E2 documented a concrete false-dormant example) and returned empty for several understanding/ modules (D1). Every dormancy classification was therefore re-verified by grep, and C3 used direct grep throughout because its questions (call sites, auth gating) are not graph-encoded. `data/node_summaries.json` does not exist in this worktree; the summaries layer of the retrieval hierarchy was unavailable and declared.

---

## 7. Verification performed

**Stage-3 adversarial pass (2026-07-04).** Seven hostile reviewers: six per-document auditors (citation existence, path:line accuracy, internal-consistency, totals recomputation) plus one completeness critic auditing coverage itself.

| Document | Verdict | path:line citations re-checked |
|---|---|---|
| UMH_CANONICAL_PRIMITIVE_MAP.md | **fail** → remediated | 221 |
| UMH_EXECUTION_SPINE_COMPLIANCE.md | pass-with-fixes | 40 |
| UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md | pass-with-fixes | 92 |
| UMH_PROJECTION_CAPABILITY_MATRIX.md | pass-with-fixes | 283 |
| UMH_WORK_PACKET_BACKLOG.md | pass-with-fixes | 560 |
| UMH_ONE_SHOT_CONVERGENCE_GAP_ANALYSIS.md | pass-with-fixes | 138 |
| Coverage (audit-of-the-audit) | **fail** → remediated | 41 |
| **Total** | | **1,375** |

Findings: **2 blockers + 20 majors** (plus minors), all routed to patch agents. The two fails: (1) the primitive map failed its citation audit and was re-issued; (2) the completeness critic found that no deliverable disclosed uninspected surfaces — remediated by gap-analysis §17, spine doc §2.8 (grep-classification of the blind mutation surfaces: composition, state, presence, cli, manual scripts), matrix row 47 + footnote 40 (TME under Self-Evolution), and this document.

**Mechanical reconciliation (Stage 2, retained):** gap→packet bijection re-check (every one of the 270 gap IDs maps into the 149-packet backlog; recomputed programmatically), severity totals recomputation (23/87/112/48 = 270), and batch existence-verification of every cited repo path against the worktree.

**Per-ledger self-verification (Stage 1):** each ledger compared its own claimed totals to independent measurement before reporting (e.g. H's cluster sums = 377; C2's matrix rows = 143; F1's registry-vs-routes `comm` diff), per the repo's Inventory & Audit Verification Protocol.

What verification did **not** include: no test execution, no service probes, no browser verification of cockpit claims, no DB queries. See §8.

---

## 8. Known blind spots

Everything below is a surface about which the deliverables make **no claims**. Convergence planning must treat these as unknown, not clean.

**In-repo code — blind or near-blind in Phase 1** (items 1–6 received a grep-level classification on 2026-07-04, recorded in spine doc §2.8; grep-level ≠ audited):

1. `substrate/composition/` — 45 .py (TME runtime). Live, ungoverned queue write found at grep level; internals, tests, and data flow unaudited.
2. `substrate/state/` — 60 of 63 .py across ~20 subpackages (session, tenancy, permissions, business, finance, lifecycle, providers, storage, stores). "Memory writes" was a mandated mutation surface; 27 files show write-capable patterns at grep level, none audited.
3. `substrate/understanding/` — 9 subpackages (~35 of 54 .py) outside D1's assigned slice: deliberation, interpretation, research, patterns, world_pulse, embedding, intelligence, signals, knowledge. Not checked for rival primitives or ungoverned write paths.
4. `transports/presence/handlers/` — 23 .py live command-ingress (voice/intent/cc-command/pipeline/substrate-command handlers). Grep-classified only.
5. `transports/cli/` — 7 .py API-key-auth ingress; F2 flagged the Clerk-vs-API-key trust asymmetry without auditing the surface. Grep-classified only.
6. `scripts/` manual-ops tier — ~134 of 146 .py never enumerated in Phase 1 (direct Neon/Notion/Discord writers among them); 2026-07-04 grep census: 58 touch external write-capable surfaces.
7. `substrate/governance/` — ~16 of 19 .py unclaimed (only 3 grep-cited) in an audit whose core subject is governance; not swept for rival PolicyDecision/authority types.
8. `substrate/contracts/` (12 .py) and `substrate/intelligence/` (4 .py) — touched only via individual grep hits; unread files not confirmed free of unregistered canonical-type rivals.
9. `transports/channels/` (2 .py), `agents/` (11 soul docs — the doc-layer half of the fragmented AgentRole primitive), `docker/` (3), `.agents/` (64 vendored skill-package files; verified 2026-07-04: zero references from any code layer).
10. `umh/desktop_relay.py` and `umh/vision_relay.py` bodies — live WS I/O surfaces, functionally transports-layer, declared nowhere; only headers read.
11. Sampled remainders inside claimed censuses: ~250 substrate/organism modules, ~70 substrate/execution/bridge modules, adapter leaf bodies (camera.py 1,344L, gws_connector 1,000+L), cockpit store bodies (77) and rooms/vision/cards leaf components (36), skills/ contents (~460 files), EOS agent bodies (11), 45 of 55 proof-named class files.

**In-repo non-code:** `data/` bulk (~2,800 of 2,847 files — runtime artifacts, prior audit outputs, graph caches, JSONL state, vendored app code beyond schema.ts), `knowledge/` (344), ~600 of 616 `docs/` files.

**Outside the repo snapshot (structurally out of reach for a read-only worktree audit):**

- **Git history** — all claims are point-in-time against the 2026-07-03 worktree; no commit archaeology.
- **Neon database contents** — table/row reality, skill/agent registration status (E2 blocker: unverifiable without DB access). Every table claim is grep-derived from code; the `umh_status`/`umh_outcomes` writeback finding (no DDL anywhere) is a repo fact, not a DB fact.
- **Runtime/process truth** — no tests executed, no endpoint probes, no service restarts. Every "deployed"/"live"/"dormant" claim derives from compose/nginx/cron/systemd config as read on this host; Hono-server dormancy verified on this host only, other hosts UNVERIFIED.
- **Deployed-container drift** — containers run images; whether deployed images match this worktree's source was not verified.
- **Beast (Windows executor) local state** — daemon, models, mirrored repos; known only via registry entries.
- **External SaaS state** — Notion, Discord, Google Workspace, 1Password vaults, Fly deployment state.
- **cockpit/ios/ + cockpit/android/** native project internals (config-only; runtime inherited from the remote web bundle).

The UNVERIFIED-items rollup (per-finding flags carried through the deliverables) lives in gap-analysis §17.5.

---

## 9. Why this is complete enough to proceed

The audit's conclusions rest on four enumerations that were driven to their measured denominators, not sampled:

1. **Mutation-surface enumeration.** Every mandated mutation surface was censused against an independently measured total: 143/143 Python API files (1,306 handlers), 9/9 in-scope TS files, 23/23 services, 20/20 cron entries, 8/8 write-capable adapter families, the mesh path end-to-end, 3/3 projection writeback structures, and the full-scan ungoverned-mutation gate over all 183 route/service files. The surfaces that escaped Phase 1 (composition, state, presence, cli, manual scripts) are now named, counted, grep-classified, and queued — they are bounded known-unknowns, not unknown-unknowns.
2. **Primitive enumeration.** All 33 assigned primitives were mapped via repo-wide class-definition greps across every code layer — a search method whose recall does not depend on which files were opened. Verdict counts (1 canonical-clean / 5 contested / 18 fragmented / 1 fragmented+broken / 8 missing) rest on all hit-lines being reviewed (e.g. all 58 `Capability*`, all 37 `Projection*` definitions).
3. **Capability-category enumeration.** 47 capability categories × 11 projection surfaces classified with evidence paths, cross-checked against the cockpit's actual 78 panels and 77 stores (both 100% enumerated), so the intended surface and the shipped surface were compared, not assumed.
4. **Adversarial pass.** 1,375 citations re-checked by hostile reviewers; the two documents that failed were re-issued; the completeness critic's coverage holes were either closed with targeted passes or converted into the explicit blind-spot register above.

Two structural arguments close the case:

- **The blind spots cannot subtract findings.** Every one of the 270 gaps is evidenced inside inspected surfaces with verified path:line citations. Uninspected surfaces can only *add* gaps. The gap ledger is therefore a floor, not a ceiling — and the remediation plan's P0 (fail-close trust boundaries) and P1 (single spine, single approval authority) phases are correct regardless of what the blind spots later reveal, because they fix defects proven in the inspected core that any newly discovered surface would route through after convergence.
- **The known-unknowns are scheduled, not ignored.** The bounded blind spots (composition, state, understanding remainder, presence, governance sweep) have queued targeted passes; the structural ones (runtime truth, DB truth, CI execution) are themselves work packets in the backlog (test-suite repair + CI, compliance acceptance tests) — closing them is part of the plan the audit produces, not a precondition for trusting it.

What this proof does **not** claim: that the audit is exhaustive. ~500 of 6,955 files were opened; the rest of the confidence comes from mechanical sweeps with measured denominators plus honest disclosure of what neither touched.

---

## 10. What would invalidate these conclusions

Concrete triggers that require re-audit of the named scope before the affected packets execute:

1. **An undocumented mutation surface is discovered** outside the censused set and the §8 register — e.g. a write path in `substrate/state/` or `transports/presence/` that bypasses even the grep signatures used in §2.8. Invalidates: spine-compliance §2 completeness; requires re-running the mutation census with widened signatures.
2. **The queued targeted passes find rival primitives** in the 9 unaudited `substrate/understanding/` subpackages, `substrate/governance/`, or `substrate/contracts/`. Invalidates: primitive-map verdict counts and the type-registry convergence packets' scope (WP-P2-*).
3. **Organism daemon architecture changes** (daemon lifecycle moved out of `services/operator_api.py`, new spine, changed `governed_mutation()` semantics). Invalidates: the entire spine-compliance classification — it is keyed to the wrapper at `transports/api/governed.py:65` and the daemon singleton topology.
4. **PLATFORM_SPEC.md revision or an accepted RFC** altering the governed-mutation contract, layer model, or projection contract. Invalidates: the canonical-target column of every deliverable; gaps stay, targets move.
5. **Divergence between this worktree and deployed containers/main** — the audit is a 2026-07-03 snapshot (+12 files drift already measured by 2026-07-04). Merges that restructure `transports/api/`, `substrate/organism/`, or cockpit stores before packet execution require re-anchoring the citations; the backlog's per-packet file lists are the checklist.
6. **Runtime evidence contradicting static classification** — first CI run of the repaired test suite, or first service probes, showing "wired" paths dead or "dormant" paths live (the known false-dormant failure mode of graph `dependents`). Invalidates: the specific wired/dormant rows, and requires re-checking every dormancy verdict that lacked a grep re-verification.
7. **DB reality contradicting grep-derived schema claims** — e.g. `umh_status`/`umh_outcomes` tables existing in Neon despite absent DDL, or Neon registrations diverging from code registries. Invalidates: the writeback-provisioning gaps (they may downgrade from "missing" to "unmanaged migration") and the registry-fragmentation packets' ordering.
8. **The 5 unread strategy docs or unread `knowledge/` corpus contain a canon supersession** (per `docs/strategy/supersession_rules.md`, itself unread). Invalidates: intent-side rows of the capability matrix for physical-tier projections.

None of these triggers is currently observed. Absent them, the gap analysis, primitive map, spine compliance, ontology separation, capability matrix, and the 149-packet backlog stand on the coverage documented above.

---

*Evidence base: 17 ledgers + `_index.json` at `/root/.claude/jobs/05379078/tmp/convergence/` (job-scoped; the durable synthesis lives in this directory). This document is the standalone form of gap-analysis §17 and supersedes nothing.*
