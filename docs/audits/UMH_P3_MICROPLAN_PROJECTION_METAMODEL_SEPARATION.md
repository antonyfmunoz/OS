# UMH P3 Micro-Plan — Projection / Metamodel Separation

**Status:** PLANNING ONLY. No code. Held for operator approval before any implementation.
**Base:** live main `bb39b3abd` (verified by direct `git rev-parse`; P0/P1/P2 all merged & green).
**Principle:** *substrate must define the rules of worlds, not contain the contents of one world.*

> **Recon provenance note (read first):** the four read-only recon agents resolved
> the tree as `9a17c1234`, which is **3 commits behind real main** (before #151/#152/#153).
> Every file:line and every "does X exist" claim below has been **re-anchored to real
> `bb39b3abd`** by direct measurement. Two agent "corrections" were themselves stale and
> are reversed here: (1) `check_type_divergence.py --registry-audit` **does exist** on
> real main (added by #152); (2) `substrate/types.py` domain-object line numbers are
> +~165 from the agents' numbers. Findings validated; line numbers corrected.

---

## 1. The four layers P3 separates

| Layer | Meaning | Current home(s) on real main |
|---|---|---|
| **L1** External Operational Reality Model | The real world the org operates in — external entities, real-world state | `substrate/reality_model/` (canonical.py, instance.py) + `substrate/organism/reality_graph.py` (graph view, reflects only) |
| **L2** UMH Platform Metamodel / substrate primitives | The universal type system (Signal, Operation, WorkPacket, RiskClass, PrimitiveType) | `substrate/types.py`, `substrate/ontology/{primitives,laws,relationships}.py` |
| **L3** Projection Domain Models | App-specific domain objects (EOS Company/Venture, CreatorOS content) | `projections/{eos,creatoros,lyfeos}/`; `substrate/understanding/domains/{business,creator,life}.py` (bridges) |
| **L4** Semantic Grounding / entity-resolution / bridge | Maps external reality ↔ projection domain ↔ metamodel | `substrate/understanding/domains/contract.py` (`DomainBridge`, `DomainProjection`), `registry.py` (`BridgeRegistry`), `substrate/reality_model/canonical_reality_write.py` (`CanonicalRealityWritePath`) |

**Key finding: three of four layers already have concrete homes.** P3 *extends and enforces* — it does not invent a new ontology system.

---

## 2. P3 current-state map (verified on `bb39b3abd`)

### Ports & registration — FOUR competing mechanisms (WP-P3-004 target)
1. **`ProjectionPort`** + `ProjectionRegistration` + `ProjectionPortProtocol` — `substrate/sockets/projection_port.py` (12KB, EXISTS, registered in `canonical_types.py`, wired in `substrate/organism/daemon.py`, tested by `tests/test_gate10_projection_consumption.py`). **Canonical candidate.**
2. **Legacy in-memory registry** — `register_projection()`/`get_projection()`/… in the *same file* (`projection_port.py:35-51`), labelled "backward compat". Collapse into #1.
3. **`OrganismStatePort`** / `ProjectionSubscriber` / `StateSlice` — `substrate/organism/projection_port.py` (a **different** file, name-collides). This is a state-broadcast bus, a genuinely different concern. **Keep separate; do not merge into #1.**
4. **`ProjectionRegistry`** (certification reader) — `substrate/organism/projection_certification.py`, reads `data/umh/projection_registry.json`. Read-only. Decide if its JSON becomes #1's seed format.

Plus daemon bridging (`daemon.py` `_register_umh_projection()` re-registers JSON entries into #1) and component self-registration via `Substrate.register()` (not projection registration).

### Per-type owner table (the 10 named primitives, on real main)
| Type | Exists? | Canonical owner | In `canonical_types.py`? |
|---|---|---|---|
| `Projection` | Yes | `substrate.organism.projection_engine` | Yes |
| `ProjectionContract` | Yes | `substrate.types:1528` | (verify entry — present in types) |
| `ProjectionRegistration` | Yes | `substrate.sockets.projection_port` | Yes |
| `ProjectionPort` | Yes | `substrate.sockets.projection_port` | Yes |
| `ProjectionDomainObject` | **NO** | — (invent in P3 only if proven) | No |
| `DomainBridge` | Yes | `substrate.understanding.domains.contract` | (verify) |
| `EntityResolution` | **NO** | — | No |
| `ExternalWorldEntity` | **NO** | — | No |
| `StateAuthority` | Yes | `substrate.organism.state_authority_graph` | Yes |
| `StateAuthorityGraph` | **NO (as a class)** | filename only; exports `StateAuthority` | No |

**4 of 10 do not exist.** They are P3 inventions-to-be, not owners to converge. Do not let the plan imply they exist.

### Duplicate / competing homes
- **Three domain registries:** `substrate/understanding/domains/` (real, canonical), `substrate/ontology/domains/` (re-export shims → the real one), `substrate/organism/domain_registry.py` (independent, hardcodes 15+ domains — genuine competitor to reconcile).
- **Two `RealityIntelligenceEngine`:** `reality_model/reality_intelligence.py` (clean) vs `understanding/reality/reality_engine.py` (L3 market-intel, hardcodes `lyfe_institute`).
- **Two `world_model.py`:** `understanding/world_model/` (domain L1) vs `organism/world_model.py` (organism self-model L4). Same name, different layers — disambiguate by rename, do not merge.

### Existing enforcement (models to reuse)
- `check_dependency_direction.py` **already enforces** "substrate must not import projections" (`IMPORT_RULES`), but treats all of `substrate/` as **one layer** — it has NO L2-metamodel/L3-projection sub-boundary. **This is the exact gap WP-P3-001 fills.**
- Gate skeleton is uniform across `check_{projection_leak,instance_leak,dependency_direction}.py`: `PATTERNS`/`IMPORT_RULES` + `LEGACY_*` grandfather dict keyed by rel-path + staged/`--all`/`--file` triad + categorized exit-1 report. **Clone this shape.**
- Live pre-commit hook `/opt/OS/.git/hooks/pre-commit` runs 10 gates. `scripts/pre-commit` (3 gates) and `scripts/install_hooks.sh` (2 gates) **drift** from it — flag for reconciliation.
- Test pattern for a boundary gate: `tests/test_sprint2_boundary.py` greps substrate/ for forbidden imports. Copy this for the ontology↔projection assertion.

---

## 3. P3 contamination ledger (worst first, re-anchored to `bb39b3abd`)

| # | Site | Identifier | Why it's L3-in-substrate | Disposition |
|---|---|---|---|---|
| 1 | `substrate/state/business/venture_knowledge.py:16` | `class Venture` | Fields are pure EOS GTM: `primary_icp`, `core_offer`, `price_point`, `winning_content_angles`, `monthly_revenue`. A LyfeOS/CreatorOS "venture" has none. | **MOVE → projections/eos** |
| 2 | `substrate/state/business/business_instance.py:129` | `class BusinessInstance` (+ 6-stage map) | EOS "BIS" schema: `offer_*`, `icp_*`, `monthly_revenue`, hardcoded stage ladder. | **MOVE → projections/eos** (substrate keeps the abstract `ProjectionContract`) |
| 3 | `substrate/understanding/world_pulse/world_pulse.py:46` | `PERPLEXITY_QUERIES` | Embeds one operator's ventures (`empyrean_creative`, `lyfe_institute`), ICP "men 18-28", named competitors. | **RUNTIME-REGISTER** (load from projection/BIS) |
| 4 | `substrate/understanding/intelligence/competitive_intel.py:17` | `COMPETITORS` dict | Named real-person competitors + proprietary brand archetype per venture. | **RUNTIME-REGISTER** |
| 5 | `substrate/control_plane/agents/agent_hierarchy.py` (~50 hits) | hardcoded `empyrean_*`/`lyfe_*` org chart | Entire instance org chart (venture ids, agent slugs, env-var names, soul-doc paths). Tries to be dynamic via `_venture_name()` but literals remain. | **RUNTIME-REGISTER / MOVE** |
| 6 | `substrate/governance/principles/principle_engine.py:190-212` | `empyrean_ceo`/`brand_ceo` principle blocks | One founder's business strategy embedded in the universal governance engine. | **MOVE → projections/eos** |
| 7 | `substrate/types.py:1301/1323/1350` | `Department`, `Portfolio`, `Company` | EOS org model with product-specific schema: `Company.stage∈1..6`, `stage_name="validation"`, `Portfolio="founder's portfolio of companies"`, "maps to a venture". | **MOVE (borderline)** — keep an abstract entity in L2, move the stage/venture model to EOS. **Operator decision required** (see §9). |
| 8 | `substrate/understanding/ontology/primitives.py` (33KB) | whole file | Named `ontology/primitives` (implies L2) but is L3 EOS stage-gated business advice; imports BIS `SubstrateContext`. | **RENAME/RELOCATE** out of `ontology/` (e.g. `understanding/business_rules/`) |
| 9 | `substrate/organism/domain_registry.py:74-285` | 15+ hardcoded domains | L3 domain identities (music, clothing, real_estate…) baked into an organism runtime; third competing domain registry. | **RECONCILE → understanding/domains/** |
| 10 | adapters/ leaks (`google_workspace/*`) | `Antony`, `EmailPriority.ANTONY`, "Munoz Conglomerate" | Instance literals in adapters — **not scanned by either gate** (both hard-code `startswith("substrate/")`). | **RUNTIME-REGISTER** + widen gate scope |

**Gate gaps discovered (all independently verified on real main):**
- `check_projection_leak.py:73` exempts `substrate/state/registries/os_registry.py` — **the file does not exist** (dead exemption, same class P2-001 cleaned from the type registry).
- Both leak gates only scan `substrate/` — **adapters/ and transports/ are unguarded.**
- `check_instance_leak.py` pattern is `\bEmpyrean\s+(?:Studio|Creative)\b` — **misses snake_case `empyrean_creative`/`lyfe_institute`** that saturate substrate.
- Neither gate has a rule for **domain-object class definitions** — `class Venture`, `class BusinessInstance`, `class Company(stage:1..6)` all pass because they contain no brand string.

---

## 4. Canonical-owner recommendation per primitive

| Primitive | Canonical owner (recommended) | Action |
|---|---|---|
| L1 external reality | `substrate/reality_model/` (+ `reality_graph.py` graph view) | Keep. Generalize `CanonicalRealityWritePath` as the governed L1 write contract. |
| L2 metamodel primitives | `substrate/types.py` + `substrate/ontology/` | **Evict L3 objects** (§3 #7, #8). |
| L3 projection domain | `projections/<name>/` + `understanding/domains/<name>.py` bridges | Receive the evicted objects (Venture, BusinessInstance, stage model). |
| L4 grounding/bridge | `substrate/understanding/domains/contract.py` (`DomainBridge`) + `registry.py` (`BridgeRegistry`) | Canonical. Reconcile `organism/domain_registry.py` into it. |
| `ProjectionPort`/`ProjectionRegistration` | `substrate/sockets/projection_port.py` | Canonical. Collapse legacy in-memory funcs; consolidate vs `organism/projection_port.py` name-collision. |
| `ProjectionContract` | `substrate/types.py` | Keep — this is the good registration contract. |
| `DomainBridge`/`DomainProjection` | `substrate/understanding/domains/contract.py` | Keep, canonical L4. |
| `EntityResolution`, `ExternalWorldEntity`, `ProjectionDomainObject`, `StateAuthorityGraph` | do not exist | **Do NOT invent unless a packet proves need.** Prefer converging existing types over adding new ones. |

---

## 5. Sequencing verdict

**WP-P3-001 first, then WP-P3-004. Soft dependency (coherence), not a compile-time blocker.**

Evidence: `projection_port.py` already ships its own import-drift detector and types its interface without any L2/L3 layer contract — so 004 *could* be built first. But "single projection port" means consolidating two competing ports (`sockets/projection_port.py` vs `organism/projection_port.py`) and typing what a projection may consume/subscribe to **per layer**. If 004 lands first, it encodes an ad-hoc layer model that 001 then has to retrofit. Landing 001's layer contract first lets 004's consolidated surface be typed against it. **Order: 001 → 004. No file forces it; doing it this way avoids rework** — this matches the operator's own recommendation and the 2026-05-22 convergence plan.

---

## 6. WP-P3-001 — implementation prompt (layer contract + enforcement)

> **Title:** Define & enforce the L1/L2/L3/L4 ontology/metamodel layer contract.
> **Risk:** MEDIUM (adds a gate + a rule doc + a boundary test; touches enforcement, not runtime).
> **Branch:** `fix/p3-001-ontology-layer-contract`. Draft PR. Hold for approval. Do not merge.
>
> **Preflight (read-only):** confirm main contains #152's `--registry-audit` (it does); run all 10 gates to record the baseline; record any pre-existing failures without fixing unrelated ones.
>
> **Scope (IN):**
> 1. **Write the layer law** `.claude/rules/ontology-layers.md` — clone the shape of `architecture-layers.md`/`type-coherence.md`: short imperative rules, the 4-layer table (§1), "before adding a class to `substrate/types.py` or `substrate/ontology/`, ask: would a different projection model this differently? If yes → it's L3, put it in `projections/` or a `understanding/domains/` bridge." Closing line: `Pre-commit hook enforces this: scripts/check_ontology_layers.py`.
> 2. **Write the gate** `scripts/check_ontology_layers.py` — clone the `check_projection_leak.py` skeleton (PATTERNS + `LEGACY_*` grandfather dict keyed by rel-path + staged/`--all`/`--file` triad + categorized exit-1). It must flag: (a) new domain-object class defs in `substrate/types.py`/`substrate/ontology/` whose fields are projection-specific (heuristic: field names in a configurable L3-vocabulary set — `icp`, `offer`, `venture`, `monthly_revenue`, `north_star`, `stage_name`, etc.); (b) `substrate/ontology/` modules importing BIS/`SubstrateContext` (L2 importing L3 instance state). Enumerate the §3 contamination as a **non-growth `LEGACY_ONTOLOGY_LEAKS` ledger** (may only shrink), exactly like P2-001's divergence ledger — do NOT mass-move files in this packet.
> 3. **Extend `check_dependency_direction.py`** to know the `substrate/ontology/` metamodel sub-layer: add a rule that `substrate/ontology/` must not import from `substrate/state/business/` or projection-domain modules. Add to its `IMPORT_RULES`, keep its non-growth `LEGACY_VIOLATIONS` pattern.
> 4. **Fix the two gate hygiene bugs** discovered: remove the dead `os_registry.py` exemption from `check_projection_leak.py:73`; add snake_case `empyrean_creative`/`lyfe_institute`/`personal_brand` patterns to `check_instance_leak.py` (with the existing live leaks grandfathered into `LEGACY_INSTANCE_LEAKS` so the gate goes green without a mass migration).
> 5. **Wire the new gate** into `/opt/OS/.git/hooks/pre-commit` (Gate 11) and reconcile `scripts/pre-commit` + `scripts/install_hooks.sh` drift (make all three list the same gate set).
> 6. **Boundary test** `tests/test_ontology_layer_contract.py` — clone `tests/test_sprint2_boundary.py`'s grep approach: assert `substrate/ontology/` imports nothing from `substrate/state/business/` or `projections/`; assert the `LEGACY_ONTOLOGY_LEAKS` count only shrinks (non-growth cap).
>
> **Forbidden (NO-GO):** no file moves/deletes of the contaminated domain objects in THIS packet (that's the follow-on convergence work — this packet only *defines and enforces the boundary + freezes the debt*); no new parallel type registry; no new risk taxonomy; no new projection system; no disabling/widening existing gates; substrate must not import transports/services/projections; Python 3.11 syntax.
> **Preserve:** every P0 fail-closed check, the P1 canonical runtime + approval authority, the P2 hardened registry (`--registry-audit` stays green), no new unregistered types.
> **Proof:** new gate fails on an injected L3-in-L2 class (negative control); `LEGACY_ONTOLOGY_LEAKS` enumerates every §3 site; all 10 existing gates + the new one green; `--registry-audit` green; boundary test green; P0/P1/P2 regression suites green. Discord report + draft PR.

---

## 7. WP-P3-004 — implementation prompt (single projection registration/port)

> **Title:** Converge to one canonical projection registration/port.
> **Risk:** HIGH (touches the live port used by the daemon + cockpit routes).
> **Branch:** `fix/p3-004-single-projection-port`. Based on WP-P3-001 tip. Draft PR. Hold. Do not merge.
>
> **Scope (IN):**
> 1. Declare `substrate/sockets/projection_port.py` `ProjectionPort`/`ProjectionRegistration`/`ProjectionPortProtocol` the **one canonical projection registration surface** (it already is registered + wired + tested — this formalizes it).
> 2. **Collapse the legacy in-memory functions** (`register_projection()` et al. in the same file) into the `ProjectionPort` class; route all callers through the one API. Preserve `tests/test_gate10_projection_consumption.py` green.
> 3. **Resolve the name collision** with `substrate/organism/projection_port.py` (`OrganismStatePort`/`StateSlice`): rename the organism one to its true concern (e.g. `organism/state_broadcast_port.py`) so "projection port" unambiguously means the registration port. Keep `substrate/organism/tests/test_projection_port.py` green (rename import).
> 4. **Decide the certification JSON's role**: make `data/umh/projection_registry.json` the seed *format* for `ProjectionPort.seed_from_config()` rather than a competing registry; the daemon bridges once, not twice.
> 5. **Type the port's registration surface against WP-P3-001's layer contract** — a projection declares which L1/L3 domains and which capabilities it consumes; the port validates against the layer law.
> 6. Update `.claude/rules/projection-boundary.md` — remove the stale "(planned)" on `projection_port.py`.
>
> **Forbidden (NO-GO):** do not merge `OrganismStatePort` (state broadcast) into the registration port — different concern; no new registry; no new deps; no projection feature work; preserve all P0/P1/P2 invariants; substrate must not import upward.
> **Proof:** one registration path (grep proves legacy funcs removed/delegating); both port test files green after rename; daemon boots with single registration path; cockpit projection routes still mount; 11 gates green; P0/P1/P2 regression green. Discord report + draft PR.

---

## 8. Proof requirements (both packets)

- Negative control per new gate (injected violation must fail the gate).
- Non-growth ledger for every frozen-debt list (may only shrink — P2-001 pattern).
- `--registry-audit` green (P2 registry stays truthful; any new registered type resolves).
- P0-002 mesh downgrade guard + P1 approval/spine + P2 risk/registry regression suites all green.
- All existing gates + new gate(s) exit 0 on the branch AND re-confirmed on merged main.
- Discord full report before `result:`.

---

## 9. Operator decisions required (do NOT decide unilaterally)

1. **`Company`/`Department`/`Portfolio` in `substrate/types.py` (§3 #7):** are these a *universal metamodel* org primitive (every projection has some org structure) or *EOS L3*? Their fields (`stage∈1..6`, `stage_name="validation"`, "maps to a venture", `north_star`) are EOS-specific. Recommendation: keep an *abstract* entity in L2, move the EOS stage/venture specifics to `projections/eos`. **Confirm before WP-P3-001 freezes the ledger** (it changes whether these are LEGACY-frozen or KEEP).
2. **Adapters/ instance leaks (§3 #10):** widen the leak gates to scan adapters/ now (bigger blast radius, more grandfathered debt) or defer to a separate packet? Recommendation: **defer widening** to keep WP-P3-001 focused on the L2/L3 substrate boundary; file adapters-scope as follow-on.
3. **The permission-envelope follow-on** (`required_tier_for_action` unknown→READ, tracked from P2-002): keep as separate tracked debt — **do NOT fold into P3** unless it turns out to gate projection boundary enforcement (it does not). Confirmed out of P3 scope.

---

## 10. No-go list (P3 planning + first packet)

- No projection feature work. No cockpit feature work. No P4/P5 work.
- No file moves/deletes of contaminated domain objects in WP-P3-001 (define + freeze the boundary only; convergence-by-moving is later packets with documented dispositions).
- No new parallel type registry, no new risk taxonomy, no new role/permission system, no new projection system (converge the existing `ProjectionPort`).
- No disabling or widening gates to pass tests. New debt is grandfathered into a **shrink-only** ledger, never silenced.
- No new dependencies. Python 3.11 syntax.
- substrate must not import transports/services/projections upward. Preserve P0 fail-closed, P1 canonical runtime + approval authority, P2 hardened registry. `UMH_CANONICAL_RUNTIME_ROUTING` stays OFF.
- Do not invent `EntityResolution`/`ExternalWorldEntity`/`ProjectionDomainObject`/`StateAuthorityGraph` unless a packet proves the need — prefer converging existing types.

---

## 11. Final recommendation — smallest safe first P3 packet

**Ship WP-P3-001 as the first P3 packet, scoped to "define + enforce + freeze," NOT "move."**

The smallest safe, highest-leverage first move is the **layer-contract gate + rule doc + non-growth contamination ledger + the two gate-hygiene fixes** — with **zero domain-object relocation**. This mirrors exactly what made P2-001 safe: it makes the boundary *enforceable* and the debt *frozen and visible* without the large blast radius of moving 10+ contaminated files across layers. It also hardens the gate that will police every later P3 convergence packet (same "harden the gate first" logic as P2-001 before P2-002).

Then WP-P3-004 (consolidate the projection port) as the second packet, typed against the new contract. Actual eviction of `Venture`/`BusinessInstance`/etc. into `projections/` becomes subsequent packets (WP-P3-002/003…), each with a documented dormant/move disposition, once the boundary is enforced and the operator has ruled on §9.1.
