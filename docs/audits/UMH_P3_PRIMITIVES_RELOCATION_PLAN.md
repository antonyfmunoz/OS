# WP-P3 — `understanding/ontology/primitives.py` Relocation Micro-Plan (PLAN ONLY)

**Branch:** `docs/p3-primitives-relocation-plan`
**Base:** `3e1dbe736` (main after #159)
**Status:** BOUNDED RELOCATION SPEC — no code moved in this PR. Doc-only. The owner
ruling below is now baked in (destination `substrate/state/business/primitives.py`,
no shim, keep whole); this doc is the spec for a separate execution packet. No `git
mv`, no import edits, no ledger/gate change in this PR.

## Why this file is the next high-leverage target

`substrate/understanding/ontology/primitives.py` (923 lines) is the second frozen
ontology-home competitor from #158, and the clearer P3 violation: it is **L3
business-rule logic living in an ontology/ directory**. Unlike the world-model
name-collision (#159, resolved by disambiguation), this is a genuine
**layer-location** problem — the file must eventually move, not just be documented.

Evidence it is L3, not ontology:
- Module docstring: "stage-aware business rules and contextual reasoning engine"
  (hiring, sales, ICP, paid ads, outsourcing) — `primitives.py:1-14`.
- Imports L3 instance state directly:
  - `from substrate.state.context.context import SubstrateContext` (`:36`, module-level)
  - `from substrate.state.business.business_instance import BusinessInstanceManager` (`:795`, `:855`)
- Public surface: `KnowledgePrimitive` (`:42`), `PRIMITIVE_LIBRARY` dict (`:82`),
  `PrimitiveRegistry` (`:783`), `ContextualReasoningEngine` (`:838`).

## 1. Exact live importers (5 sites, 5 files — all lazy, all symbol-only)

| Consumer | Line | Symbol imported | Usage |
|---|---|---|---|
| `substrate/control_plane/proactive/proactive_engine.py` | 150 | `PRIMITIVE_LIBRARY` | lazy, inside fn |
| `substrate/control_plane/orchestrator/orchestrator.py` | 1059 | `PRIMITIVE_LIBRARY` | lazy, inside fn |
| `substrate/control_plane/context/context_builder.py` | 318 | `PrimitiveRegistry` | `PrimitiveRegistry(ctx).compose_business_context(...)`, try/except |
| `substrate/control_plane/runtime/cognitive_loop.py` | 832 | `ContextualReasoningEngine` | lazy, inside fn |
| `substrate/state/lifecycle/stage_manager.py` | 114, 189 | `PRIMITIVE_LIBRARY` | lazy, inside fn |

All 5 are **lazy imports inside functions** (deferred), each wrapped in graceful
degradation. **All depend on SYMBOLS, not the module path** — none reflect on
`__module__`, none `getattr` the module, none string-match the path.

## 2. Path-coupling — no runtime *code* coupling, but two load-bearing path refs

No consumer reflects on `__module__`, `getattr`s the module, or string-matches the
path — the 5 consumers are pure symbol imports. But an exhaustive whole-tree grep
(all file types) found path-literal references in three tiers a move must handle:

**Load-bearing (MUST update for the move to work / pass CI):**
- `scripts/check_ontology_homes.py:95` — `FROZEN_ONTOLOGY_HOMES` entry (path literal).
- `scripts/check_ontology_homes.py:124` — `FROZEN_ONTOLOGY_COMPETITORS` entry (path literal).
- `.claude/skills/new-primitive.md:41` — a **live skill** with a copy-paste import
  `from substrate.understanding.ontology.primitives import PRIMITIVE_LIBRARY`. If the
  path moves with no shim, this skill instruction breaks — the execution packet MUST
  update this line.

**Stale-tolerant (update for hygiene, not blocking):**
- `data/audits/2026-06-23_*` snapshots, `data/graphify_overlay.json`,
  `data/*_source_index.json` (generated/frozen — not runtime).
- `docs/superpowers/specs/*`, `docs/superpowers/plans/*`, `knowledge/*`,
  `.claude/rules/ontology-layers.md:42`, this audit doc — documentation drift.

**No runtime *code* path-couples** — consumers are symbol-coupled, so the move is
import-line-only for code; the skill + gate-ledger path literals are the extra
targets to update.

## 3. Destination analysis

The 5 consumers are ALL in `substrate/` (`control_plane/`, `state/`). This is the
decisive constraint.

| Candidate | Verdict | Rationale |
|---|---|---|
| `projections/eos/` | **ELIMINATED** | `projections/` is the TOP layer. `substrate/` must NEVER import from it (`check_dependency_direction.py:13`). Moving here makes all 5 substrate consumers import UPWARD — the dependency gate would BLOCK it. Not viable while substrate consumers exist. |
| `substrate/understanding/domains/business/` | Weak | Would nest under the L4 bridge home; `understanding/domains/business.py` already exists as an L4 bridge FILE, so a `business/` subdir invites confusion between "business bridge" (L4) and "business rules" (L3 logic). Also still an `understanding/domains` semantic (bridges), which this is not. |
| `substrate/state/business/` | **RULED (owner-chosen)** | It already imports `substrate.state.business.business_instance`; co-locating with BIS state is coherent (this IS BIS-stage business logic). Consumers stay downward-legal (substrate→substrate). Con: mixes "state" (data) with "rules" (logic) in one dir — accepted, because an existing business-state home already owns the closest dependency. |
| `substrate/understanding/business_rules/` (new dir) | Considered, not chosen | Semantically purest (stage-aware business RULES, not ontology/bridges/state) and gate-safe, but creates a NEW one-file home when the existing `state/business/` home already owns the closest dependency. Not chosen. |

Additional detail on `understanding/domains/business/`: the L4 bridge already
exists as the FILE `understanding/domains/business.py` (classified `"L4"` in the
home ledger). A `business/` *package* there would create a Python import ambiguity
with that file and would sit inside a *guarded* home dir — requiring a new
`FROZEN_ONTOLOGY_HOMES` entry. High friction; not recommended.

**OWNER RULING — destination: `substrate/state/business/primitives.py`.** Singular,
decided. `understanding/business_rules/` was the semantic runner-up but is not chosen.

Rationale: (1) keeps every consumer import legal (substrate→substrate) — the property
`projections/eos` fails; (2) co-locates the file with the exact dependency it already
reaches for, `BusinessInstanceManager` (`primitives.py:795`, `:855`); (3) it is NOT a
guarded ontology-home dir, so the move needs NO new `FROZEN_ONTOLOGY_HOMES` entry and
cleanly exits both ledgers; (4) no Gate 11 / projection-leak delta; (5) an existing
business-state home already owns the closest dependency, so a new one-file
`business_rules/` dir is not warranted for the first relocation. The `state`-vs-`rules`
naming blur is accepted as the smaller cost.

## 4. Compatibility shim

Two clean options:
- **(a) Update 5 lazy imports** — mechanical, 6 import lines across 5 files; no shim
  left behind. Preferred: smallest permanent footprint, no lingering alias.
- **(b) Shim at the old path** — `understanding/ontology/primitives.py` re-exports
  from the new location (`# noqa: F401`). Avoids touching consumers, but leaves an
  `ontology/`-labelled file behind, which re-introduces the very ambiguity we are
  removing — and Gate 13 would still see a file under the guarded ontology dir.

**OWNER RULING — no shim.** Option (a): update the 6 lazy import lines (5 files;
stage_manager has two) **plus the skill line `.claude/skills/new-primitive.md:41`**.
The whole point is to remove the file from the ontology dir; a shim would keep a file
under the guarded `understanding/ontology/` dir (still requiring a
`FROZEN_ONTOLOGY_HOMES` `"...-shim"` entry, mirroring `substrate/ontology/domains/*`),
which defeats the eviction — clean import rewiring is the correct convergence move.
Total edits: 6 import lines + 1 skill line = 7.

## 5. Gate / ledger impact after relocation

- **Gate 13 (`check_ontology_homes.py`):** the file leaves the guarded
  `substrate/understanding/ontology/` dir → remove it from BOTH
  `FROZEN_ONTOLOGY_HOMES` (27 → 26) and `FROZEN_ONTOLOGY_COMPETITORS` (2 → 1).
  Both are shrink-only — this is a legal shrink.
- **Gate 11 (`check_ontology_layers.py`):** its L2 surface is `substrate/types.py`
  + `substrate/ontology/` only. `understanding/ontology/` is NOT on that surface, so
  primitives.py contributes no Gate-11 leak today and the move creates no Gate-11 delta.
- **Gate 4 (`check_dependency_direction.py`):** the WP-P3-001 sub-layer rule forbids
  `substrate/ontology/` (not `understanding/ontology/`) from importing state.business.
  Ruled destination `state/business/` keeps all imports legal (within-substrate).
  `projections/eos/` would newly VIOLATE it — reconfirming its elimination.
- **`check_projection_leak.py`:** if the destination were `projections/`, this gate
  scans projections/ — but that destination is already eliminated.

## 6. Behavior safety

`primitives.py` has **no import-time side effects** beyond constructing the
`PRIMITIVE_LIBRARY` module-level dict — no registration-on-import, no singleton
instantiation, no global mutation (`grep` for module-level `.register(`/`.append(`/
`= ...()` at column 0 → none). A move therefore cannot change behavior; only import
paths change. No domain-object behavior changes.

## Execution packet (separate PR — the owner ruling is the spec)

1. `git mv substrate/understanding/ontology/primitives.py
   substrate/state/business/primitives.py` — preserve history. Keep the file WHOLE
   (no split in the first relocation packet).
2. Update the 6 lazy import sites (5 files) **and `.claude/skills/new-primitive.md:41`**
   to `from substrate.state.business.primitives import ...`. No shim.
3. Remove the two path-literal entries from `FROZEN_ONTOLOGY_HOMES` (`:95`, 27→26)
   and `FROZEN_ONTOLOGY_COMPETITORS` (`:124`, 2→1); tighten the non-growth caps.
   **(These ledger edits happen in the EXECUTION packet, NOT in this plan-only PR.)**
4. Refresh the audit doc ledger + `.claude/rules/ontology-layers.md:42` note; update
   the stale-tolerant `data/`/`docs/`/`knowledge/` references for hygiene.
5. Verify: all 13 gates green; dep-direction green (no `substrate_imports_projections`);
   the 5 consumers import + run; `PrimitiveRegistry`/`ContextualReasoningEngine`/
   `PRIMITIVE_LIBRARY` behave identically; regression pack green.

## Owner rulings — DECIDED

1. **Destination**: `substrate/state/business/primitives.py`. (Singular. Not
   `understanding/business_rules/`, not `domains/business/`, not `projections/eos/`.)
2. **Shim**: no shim — update the 6 code imports + `.claude/skills/new-primitive.md`.
3. **Split**: keep the 923-line file WHOLE for the first relocation packet. Relocate
   intact, prove behavior identical, shrink the ledger; consider splitting later only
   if the file's internal structure justifies it — a second dimension of change that
   does not belong in the relocation packet.

## Scope guard

This PR is **plan/doc only** — no `git mv`, no import edits, no ledger change, no
gate change. Nothing moves in this plan-only PR. The separate execution packet
follows the owner rulings above.
