# WP-P4 — Projection Build-Out Micro-Plan (PLANNING ONLY)

**Branch:** `docs/p4-projection-buildout-microplan`
**Base / anchor:** `c9d63e577` (main after P3 closeout #164)
**Status:** PLANNING ONLY — no code, no file moves, no new registry, no projection
feature work. Every claim below is verified against the live tree at `c9d63e577`;
where a stale doc contradicts the tree, the tree wins (noted inline).

---

## 0. What P4 is (and is not)

P3 made the ontology/projection **boundaries** unambiguous and enforceable
(Gates 11/12/13 + `check_projection_leak.py`). **P4 is projection build-out** —
maturing the projection shells into governed applications on the substrate —
**without repeating the leakage P3 just cleaned up**. The recurring failure mode
is projection-specific vocabulary/logic climbing back into L2 substrate. P4's job
is to build the projection *up* while keeping substrate *universal*.

This document is the planning artifact. It does not implement anything.

---

## 1. Current-state map (verified on `c9d63e577`)

### 1a. The three (four) projections

| Projection | `projections/` files | Contents | Runtime importers | Maturity |
|---|---|---|---|---|
| **EOS** | 43 | `entities.py` (879L factory, no own classes), `views/`×3, `workflows/`×15, `agents/`×11 (10 registered agents + base), `integration/`×8 incl. `poller.py` + `DESIGN.md` (1464L) | **6 production** (`substrate/integrations/product_connections.py`, `transports/api/{cockpit_core_eos_routes,cockpit_entity_routes,app}.py`, `services/discord_bot_commands.py`, `scripts/seed_eos_watermarks_to_now.py`) + ~25 tests | **FULL** (only wired projection; see caveats §1f) |
| **CreatorOS** | 8 | empty `__init__.py`, `integration/`×6 (manifest/tables/handlers/signals/outcomes/correlation) — **no poller, no entities/views/workflows/agents** | **1** (passive status probe only) | **SHELL → DORMANT** |
| **LyfeOS** | 8 | same shape as CreatorOS — integration-only | **1** (passive status probe only) | **SHELL → DORMANT** |
| **UMH** (self) | — | registered as a projection of itself | — | seed row `umh` (`umh-substrate`, `organism_daemon_healthy`) |

CreatorOS/LyfeOS are "SHELL trending DORMANT": their only runtime importer is
`ProductConnectionManager` (`substrate/integrations/product_connections.py`), which
returns `DISCONNECTED` unless `{CREATOROS,LYFEOS}_DATABASE_URL` is set; their
capability handlers exist but nothing invokes them (no poller/dispatch loop). Each
integration shell mirrors only ~3 of the dozens of SaaS tables in its
`data/repos/*/shared/schema.ts` — a phase-1 "prove-the-loop" stub, never advanced.

The seed `data/umh/projection_registry.json` lists **four** ids: `umh`, `eos`,
`cos` (CreatorOS), `lyfeos` — each with `app_name`, `health_url`, `public_url`,
`critical_bundle_values`, `l4_workflow`. The SaaS-side product schemas live at
`data/repos/{entrepreneuros(481L), creatoros(567L), LYFEOS(1448L)}/shared/schema.ts`.

### 1b. Where domain objects actually live (the P4 crux)

`projections/eos/entities.py` **does not define domain objects** — it imports
`Company, Department, Role, Portfolio, User, Workflow, Dashboard, …` **from
`substrate.types`** (`entities.py:9-23`) and only provides EOS **factory functions**
(`default_departments`, `default_roles`, `default_company`, `SKILL_ALLOCATION`
dict, `default_dashboards`). So:

| Object | Home | Layer | Note |
|---|---|---|---|
| `Company`, `Department`, `Role`, `Portfolio`, `User`, `Workflow`, `Dashboard` | `substrate/types.py:1273–1469` | **L2** | universal org primitives |
| `Venture`, `BusinessInstance` | `substrate/state/business/` | L3 state | relocated in #161 era |
| EOS factory functions / `SKILL_ALLOCATION` | `projections/eos/entities.py` | L3 projection | correct home |

**Verified L2 contamination (the headline P4 finding):** `substrate/types.py`
`class Company` carries **`stage_name` (`:1363`, default `"validation"`)** and
**`north_star` (`:1366`)** — EOS/BIS venture-stage vocabulary sitting in a
universal L2 primitive. This is precisely the L3-in-L2 leak `ontology-layers.md`
warns about ("`stage_name`/`north_star` is L3 EOS vocabulary"). It is not blocked
by any current gate.

### 1f. EOS concrete defects (verified on tree — crisp P4 scope)

Two latent EOS defects, both confirmed at `path:line`, that define near-term P4 work:

1. **Boot KeyError.** `transports/api/app.py:192` reads `config["org_ids"]`
   (3 uses), but `projections/eos/integration/manifest.py:153`
   `load_eos_config()` returns the key `"user_ids"` and **no `"org_ids"`**. If
   `EOS_DATABASE_URL` is set, `_register_eos_integration()` raises
   `KeyError: 'org_ids'`. EOS integration boot is gated behind an unset env var
   and would fault if enabled — a real defect, not cosmetic.
2. **Integration-layer boundary leak.** `projections/eos/integration/poller.py:15`
   imports `from adapters.notion.integration.watermarks import WatermarkStore` —
   the projection reaches directly into `adapters/`, past the public substrate API
   that `projections/eos/__init__.py` itself declares ("uses ONLY the public
   Substrate API… No internal substrate imports allowed"). The row DTOs also
   mirror raw SaaS Postgres rows, bypassing `substrate.types`. The P3/P4 line
   holds for the *domain-object ontology* (all in substrate, none duplicated in
   projections) but leaks at the *integration plumbing* layer.

3. **Schema-generation lag (informational).** EOS's committed manifest polls the
   **v1** schema (`crm_contacts/crm_deals/crm_activities`, matching
   `data/repos/entrepreneuros/shared/schema.ts`), while its own `DESIGN.md`
   describes a **v2** `ventures/clients/offers/events/approvals` contract. Built
   code lags its design by one schema generation (the doc flags this itself).

### 1c. The registration / contract surfaces (verified)

Three distinct surfaces; the "projection" word is overloaded across **three
unrelated concerns** — the plan must never conflate them:

1. **App-projection registration** — `substrate/sockets/projection_port.py`
   (**canonical, live**). `ProjectionRegistration` dataclass (`:74`) fields:
   `projection_id`, `name`, `capabilities_consumed`, `routes_mounted`,
   `substrate_imports`, `preview_url`, `health_url`, `last_build`, `last_error`,
   timestamps. `ProjectionPort` (`:169`) persists to
   `data/umh/projections/registrations.jsonl`; `_read_umh_seed_file` (`:312`) is
   the ONE reader of the seed JSON (Gate 12 enforces this). Singleton
   `get_default_projection_port()`. **This is the one surface a projection
   registers with.** Registration is a *data declaration*, not a code interface.
2. **Domain-projection / bridge** — `substrate/understanding/domains/`
   (`DomainBridge` Protocol, `DomainProjection` dataclass, `BridgeRegistry`).
   Re-types an ontology `PrimitiveObservation` into a domain view. **Orthogonal**
   to app-projection registration (different registry, different concern; shares
   only the word "projection" and the `proj-` id prefix). Bridges are named
   `business`/`creator`/`life` (domains, not product brands) — clean.
3. **Organism state broadcast** — `substrate/organism/projection_port.py`
   (`OrganismStatePort`, `ProjectionSubscriber`). A live update *sink*, not a
   registration. **Distinct by design** (its own header disambiguates it). Not a
   fork.

Plus a **false friend**: `substrate/organism/projection_engine.py` = predictive
world-model forecasting, unrelated to app-projections.

**The one genuine fork (P4 must resolve):** `substrate/types.py:1528`
`class ProjectionContract(BaseModel)` — fields `projection_id`, `name`, `version`,
`domains`, `entity_types`, `required_adapters`, `registered_at`. Its docstring
says "Every application-layer projection (EOS, CreatorOS, LyfeOS) must produce one
of these." **It has ZERO usages anywhere in the tree** (verified grep) and its
field set is disjoint from the live `ProjectionRegistration`. It is a **dead,
forked registration contract that also hard-names product brands in L2**. It is
the single clearest boundary hazard for P4.

### 1d. Runtime read/health surfaces (all substrate/transport, instance-agnostic)

- `substrate/organism/projection_certification.py` — L0–L5 cert levels;
  `ProjectionConfig`/`ProjectionRegistry` read the seed via `load_seed_config`.
- `substrate/organism/projection_integration_runtime.py` — integration
  profiles/locations/gaps/readiness (exposed by `cockpit_projection_integration_routes.py`).
- `substrate/organism/projection_source_registry.py`,
  `projection_reconciliation_engine.py`, `projection_readiness_gate.py` — source
  tracking, divergence diagnosis, readiness gating.
- `substrate/organism/reality_graph.py` — emits `RealityEntityType.PROJECTION`
  entities from the seed.
- Registration is driven by `substrate/organism/daemon.py:371,424`
  (`_register_umh_projection` → `seed_from_umh_registry`), NOT by any code under
  `projections/` (no projection self-registers).

### 1e. Cockpit / API projection routes

`cockpit_projection_routes.py` (`GET /projections`, summary, audit, register — via
`ProjectionPort()`), `cockpit_projection_integration_routes.py`,
`cockpit_spine_router.py` + `cockpit_organism_routes.py` (read seed via
`load_umh_projection_seed()`). **Tree-vs-doc correction:** `architecture-layers.md`
describes `saas/` as the EOS-projection HTTP layer; on the live tree **`saas/` is
effectively empty** (only `saas/bridge/__pycache__/*.pyc` + `node_modules`, no
`.py` source). The real EOS HTTP surface is `transports/api/cockpit_*_eos_routes.py`.
One minor inconsistency to note: `cockpit_projection_routes.py:33` calls
`ProjectionPort()` (fresh instance) rather than `get_default_projection_port()` —
same JSONL file, distinct object; not a fork, but a singleton-bypass worth a
follow-on note.

---

## 2. The canonical P4 boundary law (proposed — for owner ratification)

Who owns what. This makes the P3-cleaned boundary explicit for build-out.

| Layer / surface | OWNS | MUST NOT hold |
|---|---|---|
| **substrate/ (L2)** | universal primitives, contracts, ports, governance, proof, trace, execution spine, shared types | any projection-specific vocabulary, field, brand, or logic |
| **ProjectionPort** (`sockets/projection_port.py`) | the ONE registration registry + seed reader + import-drift audit | domain objects; projection business logic |
| **ProjectionContract / ProjectionRegistration** | the *declaration* a projection provides to register (id, name, capabilities consumed, routes, substrate imports, health/preview) | domain models, projection state, templates |
| **ProjectionRegistration instance** | one registered app's live registration metadata (persisted JSONL) | canonical types |
| **projection instances** (`projections/eos`, `creatoros`, `lyfeos`) | projection domain objects, factories, views, workflows, agents, integration | importing upward (transports/adapters); redefining substrate primitives |
| **domain bridges** (`understanding/domains/`) | mapping ontology observations → domain-typed projections | product brands; registration duties |
| **cockpit / transports routes** | read/expose projection registration + health + integration read-models | *becoming* the projection model (no domain logic in routes) |
| **NEVER in L2 substrate** | — | `stage_name`, `north_star`, `venture`, `offer`, `icp`, `monthly_revenue`, product brand names, EOS factory logic, `ProjectionContract`'s brand-named docstring |

**Enforcement already in place (P4 builds on, does not replace):**
`check_projection_leak.py` (projection naming in substrate/),
`check_instance_leak.py` (instance literals in substrate/),
`check_projection_registry_reads.py` (Gate 12 — one seed reader),
`check_ontology_layers.py` (Gate 11 — L3 out of L2 surface),
`check_ontology_homes.py` (Gate 13).

**Gap the boundary law exposes:** Gate 11's L2 surface is
`substrate/types.py` + `substrate/ontology/`, yet `Company.stage_name` /
`north_star` slipped in — so either the gate does not scan field-level EOS
vocabulary on L2 domain classes, or these were grandfathered. **This is the
concrete leak P4 planning must flag for a ruling** (§8).

---

## 3. Projection shell maturity map

| Projection | Registration | Domain objects | Views/Workflows/Agents | Integration | Verdict |
|---|---|---|---|---|---|
| **EOS** | seeded (`eos` row) + 5 runtime importers | uses L2 primitives + own factories (`entities.py`) | present (`views/`, `workflows/`, `agents/`) | present | **the only build-ready projection** |
| **CreatorOS** | seeded (`cos` row) + 1 importer | none in `projections/creatoros` | none | integration-only | **SHELL** |
| **LyfeOS** | seeded (`lyfeos` row) + 1 importer | none in `projections/lyfeos` | none | integration-only | **SHELL** |
| **UMH self** | seeded (`umh` row), registered explicitly by daemon | n/a | n/a | organism health | reference registration |

EOS is decisively the P4-first target — it is the only projection with a domain
layer wired to the substrate at runtime. The tree confirms it (5 importers vs 1);
no evidence points elsewhere.

---

## 4. Minimum-viable P4 build-out target

**Do not** start EOS feature build-out. The smallest packet that *proves the
projection model* without broad feature work is a **boundary-and-contract packet**,
not a feature packet:

> **Prove that a projection registers through the ONE canonical contract, with
> zero projection vocabulary in L2, and a governed read surface — using EOS as the
> reference projection.**

That means, before any features: (1) resolve the dead/forked `ProjectionContract`
vs `ProjectionRegistration`, (2) evict `Company.stage_name`/`north_star` from L2,
(3) make EOS's registration explicit and contract-conformant. Only after the model
is provably clean do feature packets (views, workflows, agents) follow. This keeps
P4 from re-leaking on day one.

---

## 5. Projection data / model boundary

- **Domain objects** → `projections/<name>/` (EOS factories already here) OR, for
  genuinely universal org primitives, `substrate.types` **stripped of
  projection-specific fields**. `Company`/`Department`/`Portfolio` may stay L2 as
  abstract primitives; `stage_name`/`north_star` must move to an L3 EOS home.
- **Projection state** → `substrate/state/business/` (BIS: `Venture`,
  `BusinessInstance`) — already there; runtime instance state, not L2.
- **Projection templates** → projection-owned (`projections/eos/…` or a projection
  template home), never L2.
- **`ProjectionContract` vs domain model** — the contract is a *registration
  declaration* (what capabilities/routes/adapters a projection consumes); it is
  NOT a domain model and must never carry domain objects. Today's dead
  `ProjectionContract` conflates the intent by naming `domains`/`entity_types` as
  string lists — acceptable as *references*, but it must not become a domain
  schema.
- **How projection code talks to substrate legally** — projections import
  *downward* from `substrate`/`adapters` (types, ports, governance); they never
  import from `transports`/`cockpit`. Substrate never imports `projections/`
  (enforced by `check_dependency_direction.py`). Registration is a data
  declaration handed to `ProjectionPort`, not an inheritance contract.

---

## 6. The runtime path (as it exists today)

```
data/umh/projection_registry.json  (seed: umh/eos/cos/lyfeos)
        │  _read_umh_seed_file  (the ONE reader — Gate 12)
        ▼
substrate/sockets/projection_port.py  ProjectionPort.seed_from_umh_registry
        │  ProjectionRegistration → registrations.jsonl
        ▼
substrate/organism/daemon.py  _register_umh_projection()  (registers UMH + seeds rest)
        │
        ├── projection_certification.py     → L0–L5 cert levels (read-model)
        ├── projection_integration_runtime  → integration profiles/gaps/readiness
        ├── reality_graph.py                → RealityEntityType.PROJECTION entities
        └── OrganismStatePort (broadcast)   → live state slices to subscribers
        ▼
transports/api/cockpit_projection*_routes.py  → GET /projections[/…]  (cockpit read surface)
        ▼
domain bridges (understanding/domains/)  → observation → DomainProjection  (orthogonal path)
```

Capability / pathway / workpacket relation: `ProjectionRegistration.capabilities_consumed`
is the link to the capability layer — a projection declares which substrate
capabilities it consumes. No workpacket coupling exists at registration time
(governed execution is a separate axis).

---

## 7. Risks (each tied to a verified current-state fact)

| Risk | Evidence it is live | Mitigation direction |
|---|---|---|
| **Projection logic leaking back into substrate** | `Company.stage_name`/`north_star` already in L2 (`types.py:1363,1366`); dead `ProjectionContract` docstring names brands in L2 (`:1531`) | evict fields to L3; strip/rehome the contract; consider a field-level L2-vocabulary gate |
| **Cockpit routes becoming the de facto projection model** | routes exist and expose projection data; `cockpit_projection_routes.py:33` bypasses the port singleton | keep routes as read-only surfaces over the port; no domain logic in routes |
| **Duplicate projection registries** | `ProjectionContract` (dead) forks `ProjectionRegistration` (live) | pick ONE; delete or unify the other in a guarded packet |
| **Config JSON becoming runtime state** | seed carries deploy/health config; registrations persist to JSONL | keep seed = static declaration; registrations = derived runtime record; never write domain state into the seed |
| **EOS-specific assumptions becoming universal** | EOS is the only wired projection → its shape risks being mistaken for THE shape | validate the model against a SHELL (CreatorOS/LyfeOS) before declaring it universal |
| **"projection" term overload** | three unrelated subsystems + a false friend all use the word | the boundary law must name the concern, not the word, in every packet |
| **Projection reaches past the public substrate API** | `projections/eos/integration/poller.py:15` imports `adapters.notion...` directly, violating EOS's own "public API only" contract | route integration plumbing through a substrate port/adapter contract, not a direct `adapters.*` import |
| **Latent projection boot failure masks maturity** | `app.py:192` `config["org_ids"]` vs `manifest:153 "user_ids"` KeyError | fix the key mismatch so EOS integration can actually boot before building features on it |

---

## 8. Open owner rulings (decide before the first packet)

1. **`ProjectionContract` disposition.** It is dead and forks `ProjectionRegistration`.
   Options: (a) **delete** it (registration is the live truth); (b) **promote** it
   to the canonical registration contract and migrate `ProjectionRegistration` onto
   it; (c) keep both with a clear split (contract = declaration schema,
   registration = runtime record). Recon + tree lean **(a) delete** or **(c)
   split with the brand-named docstring de-branded**. Owner rules.
2. **`Company.stage_name` / `north_star` eviction.** Confirm these are EOS L3
   vocabulary to be moved out of L2 `substrate.types` into an L3 EOS home
   (`projections/eos/` or `substrate/state/business/`), and whether a **field-level
   L2-vocabulary gate** should be added to catch the next such leak. (This is a
   substrate change — HIGH-risk-adjacent — so it may deserve its own packet ahead
   of feature work.)
3. **P4-first packet scope.** Confirm the MVP target is the **boundary/contract**
   packet (§4), not a feature packet, and that EOS is the reference projection.
4. **Singleton bypass.** Should `cockpit_projection_routes.py` be moved onto
   `get_default_projection_port()` (hygiene), or is the fresh-instance read
   acceptable? (minor)
5. **CreatorOS/LyfeOS shells.** Do they stay dormant shells during P4-EOS, or does
   P4 include a "prove the model on a shell" step to prevent EOS-shape lock-in?

---

## 9. Recommended first P4 packet (recommendation only — NOT to implement)

**WP-P4-001 — Projection registration contract convergence (boundary packet).**
Resolve the dead/forked `ProjectionContract` (per ruling 1) and evict the two
EOS-vocabulary fields from L2 `Company` (per ruling 2), leaving EOS registering
through the one canonical contract with zero L2 vocabulary. **No EOS feature work.**
This is the P4 analog of the P3 boundary packets: prove the model is clean before
building on it. Feature packets (EOS views/workflows/agents build-out) are
**WP-P4-002+**, sequenced after the contract is provably singular and L2 is clean.

**P4 sequence (proposed):**
- WP-P4-001 — registration-contract convergence + L2 vocabulary eviction (boundary)
- WP-P4-002 — EOS explicit self-registration through the canonical contract
- WP-P4-003 — EOS governed read surface hardening (routes as pure read-models)
- WP-P4-004 — validate the model against a SHELL projection (CreatorOS or LyfeOS)
- WP-P4-005+ — EOS feature build-out (views/workflows/agents), one governed slice
  at a time
Each packet: draft PR, held for approval, all gates green, no L2 leak.

---

## 10. Acceptance criteria (for this PLANNING PR)

- Exactly one new doc file; no code, no file moves, no ledger/gate change.
- Every current-state claim traceable to a `path:line` on `c9d63e577`.
- All 13 gates green; registry audit truthful; pytest collection clean.
- No P4/P5 implementation started.

## 11. Verification plan (for the eventual WP-P4-001, not now)

- `check_projection_leak.py` + `check_instance_leak.py` green after L2 eviction.
- Gate 11 (`check_ontology_layers.py`) green; if a field-level L2-vocabulary check
  is added, it must flag `stage_name`/`north_star`-class fields on new L2 classes.
- `ProjectionContract` either gone (grep proves zero definitions) or the single
  canonical contract (grep proves `ProjectionRegistration` no longer forks it).
- EOS registers through the canonical port; `list_registrations()` shows it.
- Dependency direction clean; substrate imports no `projections/`.
- Behavior: projection read surfaces return the same data pre/post.

## 12. No-go list (permanent for planning; carried into every P4 packet)

- No projection/cockpit feature work in the boundary packet.
- No new registry, no new projection system, no broad rewrite.
- No file moves / code edits in THIS planning PR.
- Do not conflate the three "projection" concerns (app / domain / broadcast).
- Substrate never imports `projections/`; projections never import `transports/`.
- Preserve P0 fail-closed, P1 runtime/approval authority, P2 registry/risk
  vocabulary, P3 ontology-home gates. `UMH_CANONICAL_RUNTIME_ROUTING` untouched.
- No P5. P4 implementation begins only on explicit owner go after the §8 rulings.

## Scope guard

This PR is planning/doc only — one new file. No code, no moves, no registry, no
gate change. The first P4 packet (WP-P4-001) begins only after the §8 owner rulings.
