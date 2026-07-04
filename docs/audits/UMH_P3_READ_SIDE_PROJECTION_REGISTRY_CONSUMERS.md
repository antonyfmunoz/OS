# WP-P3 — Read-Side Projection Registry Consumer Convergence

**Branch:** `fix/p3-read-side-projection-registry-consumers`
**Base:** `f3568f279` (main after WP-P3-001 + WP-P3-004)
**Risk class:** MEDIUM (touches read paths of one substrate socket + one substrate/organism module + two transport routes; no writes, no schema, no feature change)

## Purpose

WP-P3-004 made `substrate/sockets/projection_port.py` the **one canonical
projection registration surface** and turned `data/umh/projection_registry.json`
into a **seed/config input** loaded through `ProjectionPort.seed_from_umh_registry()`.

Four read-side consumers still opened that JSON file **independently**, each
re-implementing its own `json.load(open(...))` walk — i.e. treating the file as a
competing runtime registry. This packet converges those read paths so the file is
opened by **exactly one** code path (the canonical port), while every existing
response/output shape is preserved byte-for-byte.

This is convergence, **not** a UI/API feature change.

## Consumer map — BEFORE

Ground truth: the registry is a keyed object `{proj_id: {app_name, health_url,
public_url, l4_workflow, critical_bundle_values}}` for 4 projections
(`cos`, `eos`, `lyfeos`, `umh`).

| # | Consumer | Site | How it reads the JSON | Fields consumed | Disposition |
|---|----------|------|-----------------------|-----------------|-------------|
| — | `substrate/organism/daemon.py` | `_register_umh_projection` | via `port.seed_from_umh_registry()` | (registration) | **Canonical registration owner** — already converged in WP-P3-004. Untouched. |
| — | `substrate/sockets/projection_port.py` | `seed_from_umh_registry` | `open()` + `json.load` | app_name/health_url/public_url | **Seed input loader** (the one legit reader). Refactored to a single private `_read_umh_seed_file()`. |
| 1 | `substrate/organism/projection_certification.py` | `ProjectionRegistry._load` | own `open()`+`json.load`, own `ProjectionConfig` dataclass | all 5 | **Certification read model** → route through canonical port seed view; keep `ProjectionConfig` shape. |
| 2 | `substrate/organism/reality_graph.py` | `_seed_projections` | own `open()`+`json.load` | app_name/public_url/health_url | **Reality-graph read model** → route through canonical port seed view; keep entity properties shape. |
| 3 | `transports/api/cockpit_spine_router.py` | `_projection_health` | own `open()`+`json.load` | app_name/health_url/public_url/l4_workflow | **Cockpit read model** → route through canonical port seed view; keep response shape (incl. `has_l4_workflow`). |
| 4 | `transports/api/cockpit_organism_routes.py` | `_load_projection_registry` | own `open()`+`json.load` | app_name/public_url/health_url | **Cockpit read model** → route through canonical port seed view; keep response shape. |

## Design

`ProjectionRegistration` (the typed registration) intentionally does **not** carry
seed-config vocabulary like `l4_workflow` / `critical_bundle_values` — those are
seed/config fields, not registration semantics. Mapping the registry through
`ProjectionRegistration` and back would lose `l4_workflow` (which cockpit needs)
and rename `app_name`/`public_url`. So the canonical view is **not** the typed
registration list; it is the **raw seed config**, exposed by the port as the one
reader of the file.

Added to `ProjectionPort`:

- `load_seed_config(registry_path="") -> dict[str, dict[str, Any]]` — the single
  canonical reader of `data/umh/projection_registry.json`. Returns the raw keyed
  per-projection config (all fields preserved), or `{}` if missing/malformed.
- `_read_umh_seed_file(path) -> dict` — private helper doing the one `open()`;
  `seed_from_umh_registry` now calls it too, so there is exactly **one** `open()`
  of that file in the port.

Module-level convenience (so consumers needn't build a port each call):

- `load_umh_projection_seed(registry_path="") -> dict[str, dict[str, Any]]` —
  delegates to `get_default_projection_port().load_seed_config(...)`.

Each consumer replaces its inline `open()+json.load` with
`load_umh_projection_seed(...)` (or `ProjectionPort().load_seed_config(...)` where
a path is injected for tests), preserving its existing downstream shape exactly.

`data/umh/projection_registry.json` remains seed/config input only — it is now
opened by the port and nothing else.

## Consumer map — AFTER

| Consumer | Reads JSON directly? | Reads via canonical port view? | Output shape preserved? |
|----------|----------------------|-------------------------------|-------------------------|
| `daemon.py` | no | yes (`seed_from_umh_registry`) | n/a (registration) |
| `projection_port.py` | yes — **the one reader** | is the port | seed dict |
| `projection_certification.py` | no | yes (`load_seed_config`) | `ProjectionConfig` unchanged |
| `reality_graph.py` | no | yes (`load_umh_projection_seed`) | entity properties unchanged |
| `cockpit_spine_router.py` | no | yes (`load_umh_projection_seed`) | response incl. `has_l4_workflow` unchanged |
| `cockpit_organism_routes.py` | no | yes (`load_umh_projection_seed`) | response unchanged |

## Enforcement

`scripts/check_projection_registry_reads.py` (new gate, wired into pre-commit as an
extension of the projection-leak family) fails if any module **other than**
`substrate/sockets/projection_port.py` contains a direct
`open(...projection_registry.json...)` / `json.load` of that file — i.e. a new
competing registry reader. Existing converged consumers pass because they no
longer open the file.

## Non-goals (Scope OUT)

No projection features, no cockpit features, no domain-object relocation, no
ontology-home consolidation, no schema changes, no new registry, no new type
registry, no new dependencies, no file moves/deletes, `UMH_CANONICAL_RUNTIME_ROUTING`
untouched, P4/P5 not started. `substrate/organism/projection_port.py`
(`OrganismStatePort`, state-broadcast) is a different concern and is not touched.

## Rollback

`git revert` of the squash commit — additive port helper + gate + doc, plus
in-place read-path substitutions in 4 consumers. No schema/data/runtime-flag
change; revert fully restores prior state.
