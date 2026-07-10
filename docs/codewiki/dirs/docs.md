---
type: codewiki-dir
dir: docs
---

# `docs/` — the human-readable documentation store (audits, doctrine, contracts, session logs)

**658 files · 6,488,078 bytes · [Full file inventory](../inventory/docs.md)**

## Purpose
`docs/` is the prose record of the system: how it was built, what was decided,
what each layer contracts to do, and what state the codebase was in at each
milestone. It is markdown-only — no code runs from here. Two things live side by
side: **timeless doctrine and contracts** (still authoritative) and a very large
**historical build record** (phase reports, convergence audits, campaign
proofs that captured the system at a moment and were never meant to be updated).
Reading `docs/` well means knowing which cluster you are in. This new CodeWiki
lives one level down at `docs/codewiki/` and is itself a `docs/` sub-tree — the
narrative map you are reading now.

## How it fits
`docs/` is a CORPUS layer under the wiki model: `knowledge/WIKI_RULES.md`
classifies `docs/` as immutable reference documentation — "Claude may read but
MUST NEVER modify them." It sits outside the four code layers
(projections → transports → adapters → substrate); nothing imports it and it
imports nothing. Its authoritative counterparts in code are `ARCHITECTURE.md`,
`PLATFORM_SPEC.md`, `CLAUDE.md`, and the enforced laws in `.claude/rules/`. Where
a doc and the code disagree, the code and the `.claude/rules/` gates win — many
files here predate laws that were later mechanized.

## Structure
| Subdir | Files | Era / role |
|---|---|---|
| `docs/` (root) | 25 | Live contracts + guides: `SYSTEM_ARCHITECTURE.md`, the `VOICE_*`/`PROJECTION_*` contracts, `deploy.md`, `CONTRACTOR_CODEBASE_GUIDE.md` (3,906 lines) |
| `docs/audits/` | 308 | The build record. Three eras: tool-mastery waves (2026-04), the `phaseNN_*` report era (Phases 2–74, the numbered-layer march), and the `UMH_P*` work-packet + `convergence/` era (2026-05→07, current) |
| `docs/operations/` | 182 | Doctrine and policy: `*_doctrine_v1.md`, `*_law_v1.md`, adapter/backend/bridge policies, message-type contracts, healthcheck checklists |
| `docs/system/` | 91 | System-state and W0 reports: roadmaps, canonical type contracts, ingestion-lifecycle status, MVP scope |
| `docs/superpowers/` | 23 | Design specs (`specs/`) and plans (`plans/`) — dated design docs for mesh, convergence, substrate unification |
| `docs/strategy/` | 11 | Business/entity doctrine: `company_map.md`, `empire_architecture.md`, `master_intention_lock.md`, supersession rules |
| `docs/sessions/` | 6 | Session working notes (cockpit-shell, governance, layer0, global-awareness) |
| `docs/plans/` | 3 | Execution-wiring and unification plans |
| `docs/research/` | 2 | cortextOS runtime-surface comparison notes |
| `docs/design-system/` | 2 | WorldView reference + three-state discipline |
| `docs/mvp/` | 2 | `golden_paths.md`, the 1,206-line `umh_mvp_operator_guide.md` |
| `docs/canonical/` | 1 | `umh_synthesis.md` (1,998 lines) — the canonical system synthesis |
| `docs/changes/` | 1 | Change record (gateway CognitiveLoop removal) |
| `docs/setup/` | 1 | Windows bridge autostart |

## Key components
Read these first, in this order, and treat them as current:

- `docs/SYSTEM_ARCHITECTURE.md` (333 lines) — multi-surface operating model.
- `docs/canonical/umh_synthesis.md` (1,998 lines) — the single canonical
  synthesis of what UMH is; the densest true-today overview in the tree.
- `docs/mvp/umh_mvp_operator_guide.md` (1,206 lines) + `docs/mvp/golden_paths.md`
  — what the operator product actually does end to end.
- `docs/operations/` doctrine files — the `*_law_v1.md` and `*_doctrine_v1.md`
  set is where boundary rules were written before several were promoted into
  `.claude/rules/` gates. Cross-check against the rules directory for what is now
  mechanically enforced.
- `docs/audits/UMH_P1_*` → `UMH_P3_*` — the current work-packet era
  (spine migration, approval authority, type-registry gate, risk/role/permission
  unification, ontology-home consolidation). These describe the platform as
  frozen at v1.0.0 and extended through packets, matching `PLATFORM_SPEC.md`.
- `docs/CONTRACTOR_CODEBASE_GUIDE.md` (3,906 lines) — the largest single doc; an
  onboarding-grade tour written for an external contractor.

What is historical, not authoritative: the `phaseNN_*` report family in
`docs/audits/` (Phases 2 through 74 — adaptive-prediction, regime-classification,
half-life, and similar "layer vN" reports) captured an earlier
autonomous-cognition build direction. Much of that surface is classified DORMANT
or PROOF_ONLY elsewhere in the audit record. `docs/audits/convergence/` is the
bridge era where that sprawl was collapsed toward the current governed platform;
`phase14_1r_saas_decommission_decision.md` and the `phase14_*` Trinity-convergence
docs are the freshest of that cluster.

## Data & state
Read-only markdown. No Neon tables, JSONL stores, or env vars are read or written
from `docs/`. `docs/audits/rollback/` holds two captured crontab snapshots
(`crontab-pre-phase7`/`pre-phase8`) as `.txt` rollback artifacts — the only
non-`.md` payload of note.

## Gotchas
- **Never edit files here.** `WIKI_RULES.md` marks `docs/` as immutable CORPUS.
  Durable knowledge is summarized into `knowledge/` (CANON), not edited in place.
- **Doc-reality drift is expected.** The `phaseNN_*` reports describe systems that
  were later frozen, deprecated, or reclassified. Verify any claim against current
  code (`scripts/query_graph.py`) and the `.claude/rules/` gates before acting on
  it. The `Completion Standards` in `CLAUDE.md` exist because past audits here
  claimed "100%" or "done" and were wrong.
- **`_v1` suffixes are permanent, not stale.** In `docs/operations/` the `_v1`
  marks a doctrine version, not a draft; there is no `_v2` cleanup pending.
- **Generated-file dates matter.** Per `CLAUDE.md`, dated filenames (`YYYY-MM-DD`)
  are the convention; a doc's date is its as-of, not its last-true date.
- **Two "audit" homes exist.** `docs/audits/` is the prose report tree; deep
  machine audits also live at `data/audits/` (e.g. `FRESH_EYES_SYSTEM_AUDIT.md`,
  `2026-05-25_exhaustive_codebase_audit.md`) referenced by `CLAUDE.md`. Don't
  conflate them.

## See also
- [`knowledge/`](knowledge.md) — the CANON knowledge layer that summarizes CORPUS like `docs/`
- [`.obsidian/`](dot-obsidian.md) — the vault config that makes `docs/` + `knowledge/` browsable
- [`dot-claude/`](dot-claude.md) — the enforced laws (`.claude/rules/`) that supersede older doctrine here
- [Architecture overview](../architecture.md) · [Conventions](../conventions.md) · [Health findings](../health-findings.md)
