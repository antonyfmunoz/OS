# UMH Ontology / Metamodel / Domain Separation

**Audit synthesis — 2026-07-03**
Sources: Phase-1 evidence ledgers D1 (substrate-side ontology), D2 (projection domain models + grounding layer), B4 (primitive canonicalization: Projection, ProjectionDomainObject, ExternalWorldEntity, EntityResolution, DomainBridge, StateAuthority).
Repo under audit: `/opt/OS/.claude/worktrees/umh-convergence-audit` (all paths repo-relative). Read-only audit; this document proposes boundaries only — **no file moves are performed or mandated by this document**.
All cited paths were existence-checked against the worktree at synthesis time. Items that could not be verified from the repo are marked UNVERIFIED inline.

Framing: UMH is a human-governed agentic operating control plane for desired-state reconciliation across software, data, humans, organizations, workflows, filesystems, cloud services, local devices, runtime nodes, agents, adapters, sensors, and physical/digital actuators. It is the substrate beneath the cockpit/EOS/CreatorOS/LyfeOS surfaces, not any of those surfaces. That mission makes layer separation load-bearing: reconciliation is only well-defined when the model of external reality (L1), the platform's own metamodel (L2), each product's domain model (L3), and the mapping between them (L4) are distinct and individually owned.

---

## 1. The Four-Layer Model

### L1 — External Operational Reality Model

The control plane's model of the world **outside UMH**: entities, observations, and patterns about external operational reality that reconciliation targets. L1 answers "what is true out there, with what evidence, since when."

Object inventory belonging to L1:

| Object | Definition site | Role |
|---|---|---|
| `PrimitiveType`, `OntologicalCategory`, `RelationshipType`, `TemporalMode`, `CausalRole`, `PrimitiveObservation` | `substrate/types.py:528-591` (canonical); façade `substrate/ontology/primitives.py:9-16` | Universal decomposition vocabulary for external observations |
| `InstanceObservation` / `InstanceRealityModel` | `substrate/reality_model/instance.py:30-66` | Ephemeral tenant-scoped observation store (14-day decay, JSONL) |
| `CanonicalPattern` / `CanonicalRealityModel` | `substrate/reality_model/canonical.py:37-56` | Promoted knowledge patterns (governance-gated, 180-day confidence decay) |
| Market-signal acquisition | `substrate/understanding/reality/reality_engine.py`, `reality_context.py` | External market observation intake (currently contaminated — see §3, §4) |
| External person/org/customer/lead entities | **NONE at platform level** | GAP-D2-005, GAP-B4-011: exist only as disjoint L3 rows (`crm_contacts`, `contacts`, `contacts`) |

Known L1 hole: `RealityEntityType` (`substrate/organism/reality_graph.py:35-51`) enumerates 16 entity types — PROJECT, REPOSITORY, WORKSPACE, DEVICE, DOCUMENT, SERVICE, PROJECTION, BRANCH, WORK_PACKET, APPROVAL, DELEGATION_MISSION, CAPABILITY, INFRASTRUCTURE, FILE, ARTIFACT, DECISION — all of which describe UMH's own operational estate. There is **no** PERSON, ORGANIZATION, CUSTOMER, LEAD, ACCOUNT, MARKET, or financial entity anywhere at L1/L2. External operational reality beyond dev artifacts is unmodeled above L3.

### L2 — UMH Platform Metamodel

The platform's model of **itself and its universal mechanisms**: types, invariants, execution objects, state authority, lineage, self-inventory. L2 is projection-agnostic by definition; anything that would differ for a different projection or a different tenant does not belong here.

Object inventory belonging to L2:

| Object | Definition site | Role |
|---|---|---|
| Type registry | `substrate/canonical_types.py` (name→module registry); definitions in `substrate/types.py` | Canonical type ownership |
| Governance invariants (14 executable laws) | `substrate/ontology/laws.py:64-164` (`_ALL_LAWS`); shim `substrate/foundation/laws.py:8-18` | Control-plane exclusivity, single execution spine, trace completeness |
| Governed mutation contract for L1 data | `substrate/reality_model/reality_mutation.py:41-63`, `canonical_reality_write.py:60-122` | `RealityMutation` + trust-gated write path emitting trace events |
| Pre-execution simulation / blast-radius estimation | `substrate/reality_model/simulation.py:97-167` | Non-mutating hypothesis testing against cloned models |
| Platform self-model | `substrate/organism/world_model.py` (`WorldEntity`, `EntityCategory` at :39, :145) | Deterministic self-inventory of subsystems/adapters/routes/data stores with evidence and gaps |
| State authority declarations | `substrate/organism/state_authority_graph.py:21-74` (`StateDomain`, `StateAuthorityLevel`, `StateAuthority`, `StateCoherenceStatus`); data plane `infra/state_authority_registry.json` | Which runtime node is authoritative per state domain |
| Source-of-truth lineage | `substrate/organism/source_truth_runtime.py:33-61,163-188` | Intent→Decision→WorkPacket→Execution→…→Capability lineage graph |
| Projection registration metamodel | `substrate/types.py:1363` `ProjectionContract`; `substrate/sockets/projection_port.py:60,155` | Declaration + port through which projections register (fragmented — see §4) |
| Work-packet governance domain mechanism | `substrate/organism/domain_registry.py` (`DomainDefinition`/`DomainRegistry`) | Allowed actions, proof requirements, approval gates, risk classes per domain (mechanism L2; current rows are L3/instance — see §3) |

### L3 — Projection Domain Models

Each product surface's domain model: the entities, workflows, and vocabulary of EOS, CreatorOS, LyfeOS. Owned by `projections/<name>/` plus the vendored source-of-record schemas under `data/repos/`.

Object inventory belonging to L3 (current state, per D2 F1):

| Projection | Control-plane-side model | Data-plane rows | Vendored source-of-record schema |
|---|---|---|---|
| EOS | `projections/eos/entities.py` (879L): Company, 10 Departments, 10 Roles, Portfolio, User, 10 Workflows, Dashboards, skill allocation — **but the types are imported from `substrate/types.py:1108-1254`** (see §4) | `projections/eos/integration/tables.py` (582L): CrmContactRow, CrmDealRow, CrmActivityRow, TaskRow, AgentActionRow; outcome writeback at :507-583 | `data/repos/entrepreneuros/shared/schema.ts` (481L, 15 pgTable) |
| CreatorOS | **NONE** — `projections/creatoros/` is integration-only (no entities.py, agents/, views/, workflows/, poller) | `projections/creatoros/integration/tables.py` (439L): PostRow, ProductRow, RevenueRow, StoryRow | `data/repos/creatoros/shared/schema.ts` (567L, 20 pgTable) |
| LyfeOS | **NONE** — integration-only, same shape | `projections/lyfeos/integration/tables.py` (503L): QuestRow, UserStatsRow, DailyLogRow, VisionGoalRow | `data/repos/LYFEOS/shared/schema.ts` (1448L, 35 pgTable) |

Integration coverage of the domain models is a thin slice: EOS 5/15 tables, CreatorOS 4/20, LyfeOS 4/35 (GAP-D2-008). CreatorOS's community/commerce/social graph and LyfeOS's rituals/missions/calendar/kanban are invisible to the control plane.

### L4 — Semantic Grounding / Mapping Layer

The machinery that binds the other three layers: entity resolution, observation→domain mapping, projection↔platform sync, source-of-truth and state-authority assignment, evidence linking.

Object inventory belonging to L4:

| Object | Definition site | Role |
|---|---|---|
| `DomainBridge` protocol + `DomainProjection` + `BridgeRegistry` | `substrate/understanding/domains/contract.py:18,39`, `registry.py:8-31` | PrimitiveObservation → domain-typed projection mapping; plug-in registration |
| Evidence retrieval / observation grounding | `substrate/reality_model/reality_intelligence.py:52-70`, `reality_query.py` | Read-only `why` / `what_changed` / `contradictions` / `lineage` across instance/canonical/memory/event-spine sources |
| Cross-domain composition graph | `substrate/organism/reality_graph.py`, `source_truth_linker.py` | Entity composition + cross-domain edges (projects↔repos↔docs↔projections↔devices) |
| State authority mapping | `substrate/organism/state_authority_graph.py` + `infra/state_authority_registry.json` | Source-of-truth designation for reconciliation (L2 declaration consumed as L4 grounding) |
| Entity link persistence | `substrate/state/stores/entity_link_store.py:7` | Insert-only API over `entity_links` (no read/resolve API; no DDL in repo) |
| Resolution engines (fragmented) | `substrate/organism/context_resolution.py` (`ContextResolutionEngine`), `substrate/control_plane/identity/__init__.py:15,21` (`IdentityResolver`) | NL→project/repo/device resolution; SignalEnvelope→operator identity. **No cross-source external-entity resolution exists** (GAP-D1-013, GAP-D2-005) |
| Cross-source reconciliation | `substrate/organism/cross_source_reconciler.py`, `projection_reconciliation_engine.py`, `projection_source_registry.py` | Relationship inference and divergence diagnosis (partially dormant — see §6) |

---

## 2. Current-State File Map

Each module home mapped to the layer(s) its content **actually occupies today**, per D1 F1 and D2 F1/F7. "Claims" = what the module's naming/docstring implies; "Actual" = evidence-based classification.

### 2.1 The three overlapping substrate ontology homes

| Home | Contents | Claims | Actual layer(s) | Evidence |
|---|---|---|---|---|
| `substrate/ontology/` | `laws.py` (14 governance invariants); `primitives.py` + `relationships.py` (pure re-export shims of `substrate/types.py`); `domains/` (re-export shims of `understanding/domains/`, **omitting the business bridge**) | L2 ontology | `laws.py` = clean **L2**. Shims = façade over L1 vocabulary (correct) and L4/L3 bridges. The shim chain itself is a topology defect (GAP-D1-008) | `laws.py:64-164`; `primitives.py:9-16`; `domains/__init__.py:7-17`; consumed by `substrate/execution/understanding_bridge.py:25`; re-exported (including private `_ALL_LAWS`) by `substrate/foundation/laws.py:8-18` |
| `substrate/reality_model/` | `canonical.py`, `instance.py` (L1 pattern/observation stores); `reality_mutation.py` + `canonical_reality_write.py` (governed write path); `reality_query.py` + `reality_intelligence.py` (evidence retrieval); `simulation.py` (hypothesis testing) | L1 reality model | **L1 stores + L2 mechanisms + L4 evidence linking — the cleanest of the three homes.** Defects: hardcoded `/opt/OS` store paths (`canonical.py:25`, `instance.py:25`, GAP-D1-011); package façade omits its own stores (`__init__.py:1-37`, GAP-D1-014); admits a parallel write path vs memory canonical_write (`canonical_reality_write.py:5-12`) | D1 F1 rows; `canonical.py:37-56,171-186`; `instance.py:30-66`; `reality_intelligence.py:52-70,541-589`; `simulation.py:97-167` |
| `substrate/understanding/` | `ontology/primitives.py` (923L `PRIMITIVE_LIBRARY` + `STAGE_PRIMITIVES`); `ontology/primitive_decomposition_v1.py` (duplicate dataclass copies of the L1 vocabulary); `world_model/world_model.py` (canonical/instance knowledge-entry store); `domains/` (bridge contract + registry + three projection bridges); `reality/` (market-signal scanner) | "Understanding" (implied L1/L2) | **Heavily blended.** `ontology/primitives.py` is **L3 EOS business doctrine** misfiled as substrate ontology (hire_salesperson, paid_advertising, pricing_psychology, 6-stage doctrine, BIS venture-stage reads at :792-806 — GAP-D1-002). `primitive_decomposition_v1.py:17-72` is a **divergent L1 vocabulary copy** whitelisted at `canonical_types.py:1307-1311` (GAP-D1-001) — and the entire L4 bridge layer types against this legacy copy (`domains/contract.py:14`). `world_model.py` seeds its "universal" canonical layer with EOS stage/founder doctrine at 0.90-0.95 confidence and hardcodes `org_id="lyfe_institute"` at :248 (**L3 content in an L2 container**, GAP-D1-004). `domains/contract.py` + `registry.py` = **correct L4**; `domains/{business,creator,life}.py` = **L3 keyword content inside substrate**, exempted by `scripts/check_projection_leak.py:81-82` (GAP-D1-003). `reality/reality_engine.py` = **L1 acquisition fused with instance content** ("LYFEOS, gamification" in prompt at :457; `lyfe_institute` at :21-23; founder `night_owl` pattern in `reality_context.py:33-41` — GAP-D1-009) | D1 F1 rows as cited |

### 2.2 Organism reality / world / source-truth / state-authority modules

| Module | Actual layer(s) | Assessment | Evidence |
|---|---|---|---|
| `substrate/organism/reality_graph.py` (760L) | L2 entity inventory + L4 composition | Clean layering; read-only, mutations route through `CanonicalRealityWritePath`; declares authority boundaries in docstring. L1 coverage gap: dev-artifact entity types only | `:1-14, 35-79, 249-268, 474-486` |
| `substrate/organism/world_model.py` (647L) | L2 platform self-model | Clean, but name collides with `understanding/world_model` (docstring at :3-5 has to disclaim it) and extractors reference nonexistent `saas/` paths, permanently reporting `transport_cockpit_api` MISSING (`:395, 419-421, 556-559`, GAP-D1-012). `WorldEntity` is introspective despite the name (B4 §7) | `:1-10, 39-51, 145, 283-357` |
| `substrate/organism/source_truth_runtime.py` (877L) | L2 lineage / state authority over platform objects | Clean design; **dormant** — sole dependent `tests/test_c22_source_truth.py` (D2 F7) | `:1-15, 33-61, 163-188` |
| `substrate/organism/source_truth_linker.py` (295L) | L4 cross-domain edge builder | Implemented, **dormant** — sole dependent `tests/test_source_truth_linker.py` | D2 F7 |
| `substrate/organism/state_authority_graph.py` (131L) | L2 declaration / L4 grounding | Canonical and registered (`canonical_types.py:666-668`), tested — but domain-coarse (10 domains), static JSON registry, string-typed fields ignoring its own enums (`:51-55`), no conflict-resolution or delegation semantics (GAP-B4-014). Whether `infra/state_authority_registry.json` is loaded at runtime: UNVERIFIED (B4) | `:21-74`; `infra/state_authority_registry.json` |
| `substrate/organism/domain_registry.py` (359L) | L2 mechanism carrying L3/instance content | Claims "Instance-agnostic" (:7) yet registers `music`/"Artist", `clothing`, `real_estate`, `personal`/"LifeOS" — one founder's venture portfolio — as substrate constants (:201-249); docstring "Empire WorkPacket Engine" (:1). **Dormant**: zero runtime dependents, imports only in `tests/test_empire_engine.py` (B4 §9). GAP-D1-007, GAP-B4-013 | `:1, 7, 201-249, 304-322` |
| `substrate/organism/state_coherence_engine.py` | L2 | Header inspected only (D1); coherence checking over state authority | header |

### 2.3 Projection entity/table files and data/repos schemas

| File set | Actual layer(s) | Defects | Evidence |
|---|---|---|---|
| `projections/eos/entities.py` | L3 — but **typed against L2**: Company, Department, Role, Portfolio, User, Workflow, Dashboard are defined in `substrate/types.py:1108-1254` and imported at `entities.py:9-24` (GAP-D2-006, GAP-B4-010) | Platform metamodel carries a product's domain model — the projection-boundary leak inverted. North-star literal `"$10K/month net profit"` at `entities.py:279` is instance data in L3 (acceptable per instance-context law, flagged) | D2 F1.1, F5.B1/B5 |
| `projections/*/integration/tables.py` | L3 data-plane binding | Hand-written SQL + frozen dataclasses; second hand-maintained description of the same schema as the vendored schema.ts, no drift check (GAP-D2-003). EOS `fetch_tasks_since` (`tables.py:228-247`) accepts `user_id` but never binds it — tautological WHERE, cross-tenant read; root cause: vendored `agents` table (`data/repos/entrepreneuros/shared/schema.ts:36-53`) has no owner column (**GAP-D2-001, critical**). Docstring claims 7 tables, `VALID_SOURCE_TABLES` (:497) has 5 (GAP-D2-016). EOS poller imports `WatermarkStore` from `adapters/notion/integration/watermarks.py` (`poller.py:15`, GAP-D2-013) | D2 F2, F3 |
| Writeback schema (`umh_status` column, `umh_outcomes` table) | L4 / data plane | Written by all three projections' outcome paths (`projections/eos/integration/tables.py:507-583`; creatoros `:346-439`; lyfeos `:408-504`) but present in **none** of the vendored schema.ts files and **no DDL/migration anywhere in the repo** (repo-wide grep: zero hits). Live-DB existence: UNVERIFIED. GAP-D2-002 | D2 F2 |
| `data/repos/{entrepreneuros,creatoros,LYFEOS}/shared/schema.ts` | L3 source-of-record (Drizzle pgTable; 15/20/35 tables) | TypeScript, entirely outside the Python type system — no bridge, no schema-version linkage (B4 §6). Vendored-repo freshness vs deployed apps: UNVERIFIED (no git metadata in worktree). `entrepreneuros/` vendors `client/` + `server/` against Node Role Discipline; `creatoros/` lacks `shared/models/` (GAP-D2-015) | D2 F1, Coverage |

### 2.4 Runtime wiring asymmetry (context for everything above)

Per D2 F4: EOS is fully wired (`transports/api/app.py:140-201` registers integration + executor + pipeline; poller exists). CreatorOS and LyfeOS integration code compiles and is tested (`tests/test_lyfeos_creatoros_integration.py`) but has **no poller and no registry registration** — DORMANT shells (GAP-D2-007). Their only substrate consumer is `substrate/integrations/product_connections.py:96,127` — which is itself a **layer inversion**: substrate importing `projections.*.integration.manifest`, with a `Product` enum hardcoding EOS/CREATOROS/LYFEOS at `product_connections.py:26-29` (GAP-D2-004).

---

## 3. Blended-Concepts Table

Consolidated from D1 F2, D2 F5/F6, B4 §5-§10. Each row is a term or object whose current implementations span layers that must stay separate.

| Concept | Files | Layers mixed | Evidence | Why it matters |
|---|---|---|---|---|
| **"Primitive"** | `substrate/types.py:528` (`PrimitiveType`, L1 vocabulary); `substrate/ontology/primitives.py` (shim); `substrate/understanding/ontology/primitive_decomposition_v1.py:17-72` (divergent dataclass copy); `substrate/understanding/ontology/primitives.py:82-778` (`KnowledgePrimitive` — L3 business advice); `canonical_types.py:1306` also lists `substrate.foundation.primitives` as a legacy `Modality` home, but **that module does not exist in this worktree** (stale registry entry) | L1 vocabulary vs L3 business rules under one name; two divergent L1 definitions; L4 bridges typed against the legacy copy (`domains/contract.py:14`) | `canonical_types.py:1307-1311` registers the divergence as permanent `LEGACY_DUPLICATES` | Domain projections are typed against the non-canonical vocabulary; type coherence is structurally broken at the ontology root. GAP-D1-001, GAP-D1-002 |
| **"Canonical / Instance" duality** | `substrate/reality_model/{canonical,instance}.py`; `substrate/understanding/world_model/world_model.py:35-131` (own `CanonicalWorldModel`/`InstanceWorldModel`); memory canonical_write path referenced as "PARALLEL" in `canonical_reality_write.py:5-12` | Three parallel canonical/instance stores, different schemas/decay/persistence; memory-promotion semantics duplicated (`world_model.py` has its own `promote_from_instance` at :60-73) | `canonical_reality_write.py:5-12` | Memory promotion — a governance-relevant mechanism — has three uncoordinated implementations; promoted "truth" depends on which store a writer picked. GAP-D1-006 |
| **"World model"** | `substrate/understanding/world_model/world_model.py` (knowledge store, L3-seeded); `substrate/organism/world_model.py` (L2 self-model) | L2 self-model vs L3-contaminated knowledge store share a name; the self-model's docstring must disclaim the collision (:3-5) | `substrate/control_plane/context/context_builder.py:511-515` consumes the understanding one — EOS doctrine injected into every prompt as "universal" | Prompt-context provenance is wrong at the source. GAP-D1-004, GAP-D1-006 |
| **"Reality"** | `substrate/reality_model/` (L1 stores); `substrate/understanding/reality/` (L1 acquisition + instance content); `substrate/organism/reality_graph.py` (L2/L4 graph); `StateDomain.REALITY` (`state_authority_graph.py:30`) | Three subsystems + one enum member, no boundary document | D1 F1 rows | Any engineer told to "write to the reality model" has three plausible targets. GAP-D1-006 |
| **`RealityIntelligenceEngine`** (exact class-name collision) | `substrate/reality_model/reality_intelligence.py:52` (deterministic read-only evidence retrieval; registered `canonical_types.py:529`); `substrate/understanding/reality/reality_engine.py:95` (LLM market scanner) | L4 evidence linking vs L1/L3 market intelligence under one class name | `tests/test_p1_phase4_world_model.py:132` verifies presence by grepping source text — matches either file | A canonical-registry name with two unrelated implementations; the test cannot distinguish them. GAP-D1-005 |
| **"Domain"** | Free-text `domain: str` on observations (`canonical.py:41`, `instance.py:33`); governance domains (`organism/domain_registry.py:33`); bridge domains (`understanding/domains/registry.py`); `StateDomain` platform-state enum (`state_authority_graph.py:21`) | Four distinct meanings; the free-text observation field validates against none of them | D1 F2 | An observation tagged `domain="sales"` has no defined relation to the `sales` governance domain or the `business` bridge domain — L4 grounding is undefined for the system's most-used tag. GAP-D1-010 |
| **"Domain registry"** | `organism/domain_registry.py:325` `DomainRegistry` (L2 governance lookup, dormant); `understanding/domains/registry.py:8` `BridgeRegistry` (L4 plug-in registry, wired) | L2 governance vs L4 bridge registration | B4 §9: `DomainBridge`/`DomainProjection`/`BridgeRegistry` absent from `canonical_types.py` | The wired registry is unregistered in the type system; the registered-adjacent one is dormant. GAP-B4-013 |
| **"Projection"** (four unrelated concepts) | (1) Product application — `projections/` dir + `substrate/sockets/projection_port.py`; (2) forecast object — `substrate/organism/projection_engine.py:346` `Projection` ("A forecast of future state"), which **owns the canonical name** (`canonical_types.py:295`); (3) `DomainProjection` mapping record — `understanding/domains/contract.py:39`; (4) doc/code source scope — `ProjectionName` = {UMH, Shared, Unknown} (`projection_source_registry.py:42-46`) | All L2, but the product-projection concept — the one that matters for L3 governance — has **no canonical name**, while a forecast holds it | Persistence collision: `data/umh/projections/` shared by projection_port (`:31-32`) and projection_engine (`:46-47`); id-prefix collision: `proj-` used by both `ProjectionRegistration` (`projection_port.py:61`) and `make_projection_id` (`contract.py:72-74`) | Projection registration is fragmented across ≥4 mechanisms (`ProjectionContract` at `types.py:1363` — unregistered; sockets port + legacy in-memory dict at `projection_port.py:33-51`; `projection_certification.py:104-129` `ProjectionRegistry`; `projection_integration_runtime.py:244`) plus a **second unrelated** `substrate/organism/projection_port.py:41` (`ProjectionSubscriber`). GAP-B4-007 (critical), GAP-B4-008, GAP-B4-009, GAP-D2-009 |
| **EOS domain entities in the platform type module** | `substrate/types.py:1108-1254` (Role, Department, Portfolio, Company, User, Workflow, Dashboard); imported by `projections/eos/entities.py:9-24` | L3 in L2 | D2 F5.B1; B4 §6 | The platform metamodel carries one product's org chart; any second projection either reuses EOS semantics or forks the type module. GAP-D2-006, GAP-B4-010 |
| **substrate → projections import (layer inversion)** | `substrate/integrations/product_connections.py:26-29,65,96,127` | L3 names + upward dependency in L2 | Violates `.claude/rules/architecture-layers.md` and `.claude/rules/projection-boundary.md`; the correct seam (`substrate/sockets/projection_port.py`) exists and is unused for this | GAP-D2-004 |
| **"Laws"** | `substrate/ontology/laws.py` (canonical); `substrate/foundation/laws.py:8-18` (shim re-exporting private `_ALL_LAWS` as `SUBSTRATE_LAWS`) | Single layer, double home | consumers split across aliases (`understanding_bridge.py:25` uses ontology.laws) | GAP-D1-008 |
| **Business-stage doctrine (triplicated)** | `understanding/ontology/primitives.py:681-778` (`STAGE_PRIMITIVES`); `understanding/world_model/world_model.py:148-194` (seeds); `understanding/reality/reality_engine.py:440-460` (venture prompts) | Same L3 EOS content in three substrate modules; none in `projections/` | D1 F2 | Changing the stage model requires three uncoordinated substrate edits; none is governed as projection content. GAP-D1-002/-004/-009 |
| **Source-of-truth taxonomies (parallel, unlinked)** | `state_authority_graph.py` (`StateAuthorityLevel`); `projection_source_registry.py:48` (`SourceCanonicality`: PRODUCTION_TRUTH…DIVERGENT); `DomainProjection.authority_tier` (`contract.py:56`, bare int); `source_truth_runtime.py` lineage | Three-plus authority vocabularies with no cross-reference | B4 §10 | Reconciliation cannot arbitrate a conflict when "authoritative" is defined three ways. GAP-B4-014 |

---

## 4. Proposed Canonical Responsibility Boundaries (proposal only — no file moves in this document)

Boundary principle (D1 F3, consistent with `.claude/rules/projection-boundary.md` and `.claude/rules/instance-context.md`): **substrate owns mechanisms** (stores, contracts, decay, promotion, bridges, laws, authority graphs, registration ports); **projections own content** (which domains, which primitives, which keyword maps, which seeds, which entity kinds), supplied at runtime through registration seams that already exist (`BridgeRegistry`, `ProjectionPort`, `DomainRegistry`-shaped plug-ins). The pre-commit exemption table at `scripts/check_projection_leak.py:73-82` currently waives exactly the violations this boundary would eliminate.

### L1 — canonical home: `substrate/reality_model/`

- Owns: observation store (`instance.py`), pattern store (`canonical.py`), governed mutation contract (`reality_mutation.py`, `canonical_reality_write.py`), simulation (`simulation.py`).
- The L1 decomposition vocabulary (`PrimitiveType` etc.) stays defined in `substrate/types.py` with `substrate/ontology/primitives.py` as the single named façade; the `primitive_decomposition_v1.py` duplicate converges onto it and the `LEGACY_DUPLICATES` waiver is removed.
- `understanding/world_model`'s entry store is redundant with reality_model + memory canonical_write and should be deprecated into them (its promotion mechanic already exists there).
- `understanding/reality/` market-signal scanning is L1 acquisition and belongs beside reality_model intake, with all venture/tenant/operator content parameterized from BIS at runtime.
- New requirement: L1 external-entity kinds (person, organization, customer, lead, account) — either `RealityEntityType` extended with projection-registered kinds or a dedicated L1 entity module; today this is absent (GAP-B4-011, GAP-D2-005).

### L2 — canonical homes

- `substrate/types.py` + `substrate/canonical_types.py` — type definitions + registry. Registry gaps to close: `ProjectionContract`, `DomainBridge`/`DomainProjection`/`BridgeRegistry` are currently unregistered (B4).
- `substrate/ontology/laws.py` — invariants (single home; `foundation/laws.py` shim deprecated with a removal milestone).
- `substrate/organism/world_model.py` — platform self-model (conceptually a self-model; the "world" name should be ceded — B4 §7 — and extractor targets fixed to actual repo topology, GAP-D1-012).
- `substrate/organism/{state_authority_graph.py, state_registry, state_coherence_engine.py}` — state authority; `source_truth_runtime.py` — lineage.
- `substrate/organism/domain_registry.py` — mechanism stays; the venture-portfolio domain rows (`:201-249`) move to BIS/projection-supplied registration.
- Projection registration converges on **one record + one port**: `ProjectionContract` (extended with entity_types-as-structure, bridge declarations, certification, integration profile, capability inheritance, sync status) behind `substrate/sockets/projection_port.py`; the forecast `Projection` is renamed (e.g., StateForecast) to free the canonical name; the second `organism/projection_port.py` merges or renames (GAP-B4-007/-008; per-item dispositions are for the roadmap doc, not here).
- EOS domain types (Company, Department, Role, Portfolio, Workflow, Dashboard at `types.py:1108-1254`) are designated EOS-owned and exit the platform type module in favor of structural registration via `ProjectionContract.entity_types` (GAP-D2-006).

### L3 — canonical home: `projections/<name>/` + `data/repos/<name>/shared/schema.ts`

- Each projection owns: entities, agents, views, workflows, integration rows, and its writeback contract.
- Content currently resident in substrate that this boundary assigns to L3: `understanding/ontology/primitives.py` PRIMITIVE_LIBRARY + STAGE_PRIMITIVES; `understanding/domains/{business,creator,life}.py` keyword vocabularies (registered through `BridgeRegistry` from projection code/data); `understanding/world_model` seeds; `domain_registry.py` venture rows; `understanding/reality` venture prompts.
- The vendored schema.ts remains the L3 source-of-record for each SaaS data plane; a generated binding or automated correspondence check replaces the second hand-maintained description in `tables.py` (GAP-D2-003), and the `umh_status`/`umh_outcomes` writeback surface gets versioned migrations under repo control (GAP-D2-002).

### L4 — canonical homes

- `substrate/understanding/domains/contract.py` + `registry.py` — the bridge contract and registration mechanism stay in substrate (they are the correct L4 seam); bridge **content** registers from projections.
- `substrate/reality_model/{reality_intelligence.py, reality_query.py}` — evidence linking.
- `substrate/organism/reality_graph.py` (+ `source_truth_linker.py`) — cross-domain composition and projection sync.
- `substrate/organism/state_authority_graph.py` + `infra/state_authority_registry.json` — state authority, extended to per-entity granularity and unified with `SourceCanonicality` and `authority_tier` (GAP-B4-014).
- **New component required**: an entity-resolution contract composing `ContextResolutionEngine` + `IdentityResolver` + `EntityLinkStore` behind one interface, resolving external references across sources (Discord handle ↔ email ↔ CRM row ↔ projection contact rows) to canonical L1 entities, with state-authority annotations per entity (GAP-D1-013, GAP-D2-005, GAP-B4-012).
- **New component required**: a domain-vocabulary cross-reference so the observation `domain` tag, governance domains, and bridge domains share one registry or explicit namespaces (GAP-D1-010).

---

## 5. Grounding-Layer (L4) Maturity Assessment

Per D2 F7 (dependents-graph verdicts) and B4 §7-§10. "Dormant" = compiles and is tested but has no runtime consumer in the dependency graph.

| Mechanism | Path | Status | Notes |
|---|---|---|---|
| **Entity resolution — internal (NL→project/repo/device)** | `substrate/organism/context_resolution.py` | Implemented / wired | Deterministic strategies (EXACT_MATCH/PATTERN_MATCH/GRAPH_WALK/RECENCY_BIAS/ACTIVE_CONTEXT) over the Reality Graph |
| **Entity resolution — operator identity** | `substrate/control_plane/identity/__init__.py:15,21` | Implemented / wired | SignalEnvelope→Identity only |
| **Entity resolution — cross-source external entities** | — | **MISSING** | No module resolves the same person/org across EOS `crm_contacts` / CreatorOS `contacts` / LyfeOS `contacts`; `query_graph.py search entity_resolution` returns nothing relevant; `RealityEntityType` has no PERSON/ORG type. GAP-D2-005, GAP-B4-012 |
| **Entity link persistence** | `substrate/state/stores/entity_link_store.py` | Partial | Insert-only; no read/query/resolve API; untyped string relationships; `entity_links` DDL absent from repo; one consumer (`substrate/understanding/knowledge/knowledge_graph.py:70`). GAP-D2-014 |
| **Semantic mapping (observation→domain)** | `substrate/understanding/domains/{contract,registry}.py` + business/creator/life bridges | Partial / wired | Keyword-lookup V1 only; business.py self-declares "V2 TODO: LLM-based semantic disambiguation"; confidence not evidence-linked; loaded unconditionally for all projections via `substrate/execution/understanding_bridge.py:159-161` regardless of tenant. GAP-D2-011, GAP-D1-003 |
| **Projection registration** | `substrate/sockets/projection_port.py` | Implemented / wired | Dependents: `substrate/organism/daemon.py`, `substrate/contracts/infrastructure_protocol.py`. But fragmented across ≥4 rival mechanisms (B4 §5) and carries a legacy in-memory registry in the same file (`:33-51`) |
| **Projection sync — EOS** | `projections/eos/integration/` + `transports/api/app.py:140-201` | Implemented / wired | Poller + registry + executor + pipeline; **critical tenant-isolation defect** in the read path (GAP-D2-001) |
| **Projection sync — CreatorOS / LyfeOS** | `projections/{creatoros,lyfeos}/integration/` | **MISSING (runtime)** | Code exists and is tested; no poller, no registration — dormant shells. GAP-D2-007 |
| **Projection schema drift detection** | `substrate/organism/projection_reconciliation_engine.py:256` (`_check_schema_drift`) | Partial / dormant | Test-only dependents; `ProjectionName` enum = {UMH, Shared, Unknown} — structurally cannot represent EOS/CreatorOS/LyfeOS. GAP-B4-009, GAP-D2-003 |
| **Source truth — canonicality metadata** | `substrate/organism/projection_source_registry.py` | Implemented | Consumed only by the dormant reconciliation engine + tests |
| **Source truth — lineage** | `substrate/organism/source_truth_runtime.py` | Implemented / dormant | Test-only dependent. GAP-D2-010 |
| **Source truth — cross-domain edges** | `substrate/organism/source_truth_linker.py` | Implemented / dormant | Test-only dependent. GAP-D2-010 |
| **Cross-source reconciliation (operator-confirmed)** | `substrate/organism/cross_source_reconciler.py` | Implemented / wired | Consumer: `transports/api/cockpit_context_assimilation_routes.py` |
| **State authority** | `substrate/organism/state_authority_graph.py` + `infra/state_authority_registry.json` | Implemented, shallow | Canonical, registered, tested — but domain-coarse (10 domains), static registry (runtime load UNVERIFIED), string-typed fields, no conflict-resolution/delegation, unlinked to `SourceCanonicality`/`authority_tier`. GAP-B4-014 |
| **Reality correspondence checks** | `substrate/organism/correspondence_scheduler.py` | Implemented / dormant | Periodic checks + regression alerts; test-only dependent |
| **External sync policy** | `substrate/organism/sync_policy.py` | Partial by design | Dry-run only; "no actual external writes" (`:4-6`) |
| **Grounded status answers** | `substrate/organism/grounding_registry.py` + `grounded_handlers.py` | Implemented / wired | Deterministic answers from declared data sources ("LLM never fills gaps"); via `advisor_conversation` |
| **Data-source adapter registration** | `substrate/sockets/data_source_port.py`; `adapters/data_source_adapters/*` | Implemented / wired | Ingestion Source implementations on the `substrate/understanding/perception/source.py` contract |
| **Product connection status** | `substrate/integrations/product_connections.py` | Implemented / wired — **layer-inverted** | Substrate imports projection manifests; `Product` enum hardcodes projections. GAP-D2-004 |
| **Projection integration audit** | `substrate/organism/projection_integration_runtime.py` | Implemented / dormant | Test-only dependent |
| **L3↔schema.ts drift checker** | — | **MISSING** | No automated correspondence between `tables.py` dataclasses and vendored Drizzle schemas. GAP-D2-003 |
| **Writeback schema provisioning check** | — | **MISSING** | `umh_status`/`umh_outcomes` written with no repo DDL and no startup verification. GAP-D2-002 |

Summary: of ~20 grounding mechanisms, 8 are wired, 7 are implemented-but-dormant (test-only dependents — GAP-D2-010), 2 are partial, and 4 are missing outright. The missing four are precisely the mechanisms a desired-state reconciliation control plane cannot operate without at multi-projection scale: cross-source entity resolution, non-EOS projection sync, schema-drift detection, and writeback provisioning verification.

---

## 6. Entity-Category Mapping Table

Real-world entity category → L2 platform object → L3 projection object(s) → L4 grounding mechanism → status. Compiled from D1 F1, D2 F1/F7/F8, B4 §5-§10.

| Real-world entity category | L2 platform object | L3 projection object(s) | L4 grounding mechanism | Status |
|---|---|---|---|---|
| Person (customer, lead, contact) | **NONE** — `RealityEntityType` has no PERSON (`reality_graph.py:35-51`) | EOS `crm_contacts` (`schema.ts`), `CrmContactRow` (`tables.py:45+`); CreatorOS `contacts` (`schema.ts:235`); LyfeOS `contacts` (`schema.ts:402`) | **NONE** — no cross-projection resolver; `EntityLinkStore` insert-only | **MISSING at L1/L2 and L4** (GAP-D2-005, GAP-B4-011) |
| Organization / company | **misplaced**: `Company` defined at `substrate/types.py:1185` (EOS domain type in L2) | `projections/eos/entities.py:269` `default_company()` | none | **BLENDED** — L3 type in L2; no L1 org entity (GAP-D2-006, GAP-B4-010) |
| Operator / platform user | `User` (`substrate/types.py:1168` — EOS-flavored); operator identity via `IdentityResolver` (`control_plane/identity/__init__.py:15`) | `default_user()` (`entities.py:291`); per-app `users` tables in all three schema.ts | IdentityResolver (SignalEnvelope→Identity) — wired | **PARTIAL** — operator identity resolved; no linkage of platform operator to projection user rows |
| Deal / transaction / revenue | none | EOS `crm_deals`/`CrmDealRow`; CreatorOS `revenue`/`RevenueRow` | outcome writeback (`umh_status`/`umh_outcomes`) — schema unprovisioned in repo | **PARTIAL** (GAP-D2-002) |
| Task / work item | `WorkPacket` family (L2, canonical per work-packet contracts); `RealityEntityType.WORK_PACKET` | EOS `tasks`/`TaskRow`; LyfeOS `quests`/`QuestRow`; kanban_tasks (unintegrated) | EOS poller→signal pipeline (wired, tenant-defective per GAP-D2-001); LyfeOS dormant | **PARTIAL** |
| Content / media / posts | `RealityEntityType.DOCUMENT`, `FILE`, `ARTIFACT` (dev-artifact scope) | CreatorOS `posts`/`PostRow`, `stories`/`StoryRow`; LyfeOS media_albums/media_items (unintegrated) | CreatorOS integration dormant (no poller) | **DORMANT** (GAP-D2-007) |
| Product / offer | none | CreatorOS `products`/`ProductRow` | dormant | **DORMANT** |
| Habit / ritual / goal | none | LyfeOS `user_daily_logs`/`DailyLogRow`, `vision_goals`/`VisionGoalRow`, `user_stats`/`UserStatsRow`; ritual_groups/mission_pages (unintegrated) | dormant | **DORMANT** (GAP-D2-007, GAP-D2-008) |
| Device / runtime node | `RealityEntityType.DEVICE`, `INFRASTRUCTURE`; `infra/device_registry.json`; node records in state authority registry | n/a (platform-level) | RealityGraph ingest + `ContextResolutionEngine`; StateAuthority per state domain | **IMPLEMENTED** — the best-grounded category |
| Repository / project / workspace | `RealityEntityType.{REPOSITORY, PROJECT, WORKSPACE, BRANCH}` | n/a | RealityGraph ingest, `source_truth_linker` edges (dormant), `ContextResolutionEngine` (wired) | **IMPLEMENTED / partially dormant** |
| Document (external, e.g. GWS/Notion) | `RealityEntityType.DOCUMENT` | per-app `documents` tables (all three schema.ts — unintegrated) | `data_source_port` + adapters (wired); `cross_source_reconciler` duplicate-doc inference (wired) | **PARTIAL** — platform docs grounded; projection document tables invisible |
| Market / competitor | **NONE** as entity | none | `understanding/reality/reality_engine.py` market-signal scanner — L1 acquisition contaminated with instance content (`:457`) | **BLENDED / PARTIAL** (GAP-D1-009) |
| Business knowledge / doctrine (stages, playbooks) | **misplaced**: `understanding/ontology/primitives.py` PRIMITIVE_LIBRARY + STAGE_PRIMITIVES in substrate; `understanding/world_model` seeds | should be EOS-owned projection content | `BridgeRegistry` exists as the correct registration seam; unused for this | **BLENDED** — L3 content resident in L2 homes (GAP-D1-002, GAP-D1-004) |
| Observation / event (about any of the above) | `InstanceObservation` / `CanonicalPattern` (`reality_model/`); `PrimitiveObservation` vocabulary (`types.py:528-591`) | projection signal emitters (`projections/*/integration/signals.py`) | `RealityIntelligenceEngine` evidence retrieval (wired); DomainBridge mapping (wired, keyword V1); free-text `domain` tag ungrounded | **PARTIAL** (GAP-D1-010, GAP-D2-011) |
| State-authority designation (who owns which truth) | `StateAuthority` + `StateDomain` (10 coarse domains) | none per-entity/per-row | `state_authority_graph.py` + static JSON registry; parallel unlinked taxonomies (`SourceCanonicality`, `authority_tier`) | **IMPLEMENTED, shallow** (GAP-B4-014) |

---

## 7. Gap Cross-Reference

Gaps synthesized in this document, by owning ledger (severities as assigned in Phase 1):

- **Critical**: GAP-D2-001 (cross-tenant EOS task read), GAP-B4-007 (Projection homonym owns canonical name; product-projection registration fragmented ≥4 ways).
- **High**: GAP-D1-001 (duplicate primitive ontology, L4 typed against legacy copy), GAP-D1-002 (EOS doctrine as substrate "ontology"), GAP-D1-003 (projection bridges hardcoded in substrate), GAP-D1-005 (`RealityIntelligenceEngine` class collision), GAP-D1-006 (four overlapping world/reality homes, no boundary doc), GAP-D2-002 (unprovisioned writeback schema), GAP-D2-003 (dual hand-maintained L3 truth, no drift check), GAP-D2-004 (substrate→projections import inversion), GAP-D2-005 (no cross-projection entity resolution), GAP-D2-006 / GAP-B4-010 (EOS types in `substrate/types.py`), GAP-D2-007 (CreatorOS/LyfeOS runtime-orphaned), GAP-B4-008 (two projection ports), GAP-B4-011 (no L1 person/org model; "world_model" is a self-model), GAP-B4-012 (EntityResolution fragmented: three unlinked mechanisms, no cross-source resolution).
- **Medium**: GAP-D1-004, GAP-D1-007, GAP-D1-008, GAP-D1-009, GAP-D1-010, GAP-D1-013, GAP-D2-008 through GAP-D2-014, GAP-B4-009, GAP-B4-013, GAP-B4-014.
- **Low**: GAP-D1-011, GAP-D1-012, GAP-D1-014, GAP-D1-015, GAP-D2-015, GAP-D2-016.

UNVERIFIED items carried forward from the ledgers: live-DB existence of `umh_status`/`umh_outcomes`; vendored schema.ts currency vs deployed SaaS apps; runtime loading of `infra/state_authority_registry.json`. Additionally verified during synthesis: `substrate/foundation/primitives.py` (listed in `canonical_types.py:1306` LEGACY_DUPLICATES) does not exist in this worktree — the registry entry is stale.
