# UMH One-Shot Convergence Gap Analysis

**Date:** 2026-07-03
**Repo under audit:** `/opt/OS/.claude/worktrees/umh-convergence-audit` (all paths repo-relative; read-only audit)
**Sources:** 17 Phase-1 evidence ledgers (A, B1-B4, C1-C3, D1-D2, E1-E3, F1-F2, G, H); four synthesis artifacts — [UMH_CANONICAL_PRIMITIVE_MAP.md](UMH_CANONICAL_PRIMITIVE_MAP.md), [UMH_EXECUTION_SPINE_COMPLIANCE.md](UMH_EXECUTION_SPINE_COMPLIANCE.md), [UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md](UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md), [UMH_PROJECTION_CAPABILITY_MATRIX.md](UMH_PROJECTION_CAPABILITY_MATRIX.md); the remediation plan [UMH_WORK_PACKET_BACKLOG.md](UMH_WORK_PACKET_BACKLOG.md) (149 packets); the consolidated gap index (270 gap candidates: 23 critical / 87 high / 112 medium / 48 low).
**Audience:** this is the document a staff engineering team reads first. Every claim below carries a path:line citation from the evidence ledgers; every cited repo path was batch-verified to exist in the audited worktree. Items the ledgers could not verify are marked UNVERIFIED, not asserted.

**Layer legend used throughout:** L1 = External Operational Reality Model · L2 = UMH Platform Metamodel · L3 = Projection Domain Models · L4 = Semantic Grounding / Mapping Layer.

---

## 1. Executive Summary

**What UMH is.** UMH is a human-governed agentic operating control plane for desired-state reconciliation across software, data, humans, organizations, workflows, filesystems, cloud services, local devices, runtime nodes, agents, adapters, sensors, and physical/digital actuators. It is the substrate beneath the cockpit/EOS/CreatorOS/LyfeOS surfaces — not any of those surfaces. Its load-bearing guarantees are: every state change flows through a governed mutation contract with policy evaluation, approval, trace, proof, and rollback; the model of external reality (L1), the platform metamodel (L2), each projection's domain model (L3), and the grounding between them (L4) stay separate; and runtime nodes execute only inside attested permission envelopes.

**Verdict in three sentences.** The governed spine is real, well-built, and densely adopted at the deployed HTTP boundary (360 `governed_mutation()` call sites, 68/143 API files fully compliant) — but the guarantee is not upheld below the transport layer: the single wrapper fronting every governed route fails open when the control-plane daemon is down (`transports/api/governed.py:91-111`), the node-mesh relay dispatches arbitrary remote execution with no auth when one env var is unset (`transports/node_mesh/server.py:894-898`), and two governed paths are silently broken by typo'd method calls. Of the 33 canonical primitives a reconciliation control plane requires, exactly 1 is canonical-clean (StateAuthority); the rest are fragmented across 4 rival execution spines, 4 WorkPacket variants, 4 approval state machines rendered on 11 UI surfaces, 5 runtime-node models with 3 role vocabularies, and 4 API entrypoints of which only one is deployed. The system is a working single-operator control plane whose contracts exist but are not yet singular, mechanical, or fail-closed — convergence is an exercise in declaring one owner per concern and making the existing guarantees hold everywhere, not a rewrite.

**The five highest-leverage moves** (packet IDs from [UMH_WORK_PACKET_BACKLOG.md](UMH_WORK_PACKET_BACKLOG.md)):

1. **Fail-close every trust boundary** — `governed_mutation()` fail-closed with a degraded-mode allowlist; mesh relay/WS auth mandatory with token→node binding; node-side risk derivation; authenticated webhook/voice/IPC surfaces (WP-P0-001 … WP-P0-015). This is the only phase where the system is actively unsafe rather than merely fragmented.
2. **One governed operation runtime and one approval authority** — retire the 4 rival spines/pipelines and the rival event backbone; converge the 4 approval state machines and 3 approval channels into one canonical ApprovalRequest and pending-work store (WP-P1-001, WP-P1-007). Nearly every downstream duplication collapses against these two authorities.
3. **Fix the type registry so it can hold the line** — the divergence gate passes commits while 46 full-scan violations exist and the registry omits the exact primitives that are most fragmented; harden the gate, register everything public, then converge WorkPacket/risk/node/approval types (WP-P2-001, WP-P2-002, WP-P2-005, WP-P2-010).
4. **Enforce the four-layer separation** — move EOS doctrine and entity types out of substrate, converge projection registration on one contract and one port, land the L4 entity-resolution and writeback-schema contracts (WP-P3-002, WP-P3-004, WP-P3-005, WP-P3-009, WP-P3-011).
5. **Make the guarantees mechanical** — CI that actually runs the 15,017-test suite (collection is broken today and no workflow executes pytest), a governed-mutation compliance acceptance test, projection-inheritance and node-trust acceptance tests, and full-scan enforcement sweeps of all check gates (WP-P0-011, WP-P6-004, WP-P6-005, WP-P6-006, WP-P6-007, WP-P6-014).

---

## 2. Current-State Verdict

One verdict paragraph per subsystem, with the decisive evidence.

**Architecture / layering — contract real, decaying at the edges, and wrong about what is deployed.** The four-layer dependency direction largely holds (only ~10 true violations remain of 70 grandfathered exemptions — the checker's grandfather list is ~55 entries stale), but the contract legislates a ghost `saas/` layer that does not exist (`.claude/rules/architecture-layers.md:29`, `scripts/check_dependency_direction.py:94`) and omits `nodes/`, `umh/`, `cockpit/`, and `services/` from the dependency diagram entirely — while substrate imports `nodes/` (`substrate/execution/agents/computer_use_agent.py:256`) and transports imports daemon singletons upward from `services/operator_api.py` with no checker rule for that pair. Deployment reality contradicts ARCHITECTURE.md:434 ("One API — transports/api/http/ serves all clients"): nginx proxies all cockpit traffic to `services/operator_api.py` on :8091 (`cockpit/nginx.conf.template:1-2`), while `transports/api/http/server.ts` (Hono) and `transports/api/app.py` are parallel undeployed stacks and `transports/api/operator.py` is a dead 601-line near-duplicate that NameErrors at import (uses `os` at line 7 before `import os`). (Ledger A; GAP-A-001…A-016.)

**Execution spine — strongest-converged at the deployed HTTP boundary; bypassable below, beside, and inside it.** 360 `governed_mutation()` call sites; 68 of 143 FastAPI files fully canonical-governed; pre-commit reports the route/service layer clean. But the wrapper itself fails open to direct ungoverned execution with status `completed_ungoverned` when the daemon is down (`transports/api/governed.py:91-111`); four rival spines coexist (`substrate/execution/spine.py`, `substrate/execution/runtime/execution_spine.py` — live in the deployed Discord path, `substrate/execution/pipeline.py`, plus the name-colliding `substrate/execution/bridge/event_spine.py` vs the canonical `substrate/organism/event_spine.py`); the cron plane mutates Neon/Notion/calendar directly every 5–15 minutes with zero policy gating; and two governed paths are silently broken by AttributeError (`substrate/organism/governed_work_runtime.py:232` calls nonexistent `create_from_intent`; `substrate/organism/command_runtime.py:896` calls nonexistent `update_status`). Full detail: [UMH_EXECUTION_SPINE_COMPLIANCE.md](UMH_EXECUTION_SPINE_COMPLIANCE.md).

**Primitives / types — 1 of 33 canonical-clean.** `substrate/types.py` defines ~90 models; `substrate/canonical_types.py` is a name→module registry, not a type module — and it is incomplete exactly where fragmentation is worst (WorkPacket, Signal, Intent, ApprovalPacket, MemoryCandidate, ProofArtifact, all 12 template types, the entire `substrate/reality_model/` package are unregistered). The registry sanctions homonyms (two canonical `Capability` types, canonical name `Projection` owned by a forecast), carries a 17-module LEGACY_DUPLICATES allowlist with no burn-down, and the gate fails a full scan today (46 BLOCKED + 47 warnings, staged-only enforcement). Rollup: 1 canonical-clean, 5 canonical-but-contested, 18 fragmented, 1 fragmented+broken, 8 missing outright — the missing eight are the core reconciliation guarantees (DesiredState, StateCommit, ProofContract, ToolCall, ExecutionStep, AgentInstance, CapabilityPathway, CapabilityRevision). Full detail: [UMH_CANONICAL_PRIMITIVE_MAP.md](UMH_CANONICAL_PRIMITIVE_MAP.md).

**Ontology layers — the boundary exists in rules but not in the code.** Three overlapping substrate ontology homes (`substrate/ontology/`, `substrate/reality_model/`, `substrate/understanding/`); L3 EOS business doctrine lives inside substrate as "universal" ontology (`substrate/understanding/ontology/primitives.py` — hire_salesperson, pricing_psychology, 6-stage doctrine; world-model seeds at 0.90–0.95 confidence with `org_id="lyfe_institute"` hardcoded at `substrate/understanding/world_model/world_model.py:248`); EOS entity types (Company, Department, Role, Portfolio) are defined in `substrate/types.py:1108-1254` and imported by the projection — the boundary leak inverted; substrate imports projections by name (`substrate/integrations/product_connections.py:65-134`). There is no PERSON/ORGANIZATION/CUSTOMER entity anywhere at L1/L2, and of ~20 L4 grounding mechanisms, 8 are wired, 7 dormant, 2 partial, 4 missing (cross-source entity resolution, non-EOS projection sync, schema-drift detection, writeback provisioning). Full detail: [UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md](UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md).

**Projections — one wired, two dormant shells, physical tier strategy-only.** EOS is the only projection registered at runtime (`transports/api/app.py:142-203`) and its workflows correctly route through governed mutation (`projections/eos/workflows/runner.py:29`), but the bridge covers 3 of 15 product tables and the task read path is cross-tenant (`projections/eos/integration/tables.py:228-247` accepts `user_id` and never binds it — GAP-D2-001, critical). CreatorOS (3/20 tables) and LyfeOS (3/~35) compile and pass unit tests but have no poller and no registration. All three write a `umh_status`/`umh_outcomes` writeback surface that appears in no schema and no migration anywhere in the repo. Jarvis/Operator is the broadest shipped surface with the worst fragmentation (4 operator-intent kernels, 3 voice stacks, presence in 5 modules). SecurityOS has zero repo evidence; ManufacturingOS/RoboticsOS are strategy documents. Full detail: [UMH_PROJECTION_CAPABILITY_MATRIX.md](UMH_PROJECTION_CAPABILITY_MATRIX.md).

**Cockpit — fragmented panel museum with a genuine mission-control spine emerging.** 78 panels, 77 near-1:1 zustand stores, 74 routes of which only 6 primary + settings are reachable outside the command palette; 7 registered panels have no route at all. Each core control-plane concern is rendered by 4–12 independent panels against inconsistent endpoint families — approvals by 11 surfaces over ≥9 backend approval families. Convergence so far operated at the navigation layer (demote to [DEV]) rather than the information-architecture layer: routes.ts comments declare absorptions that were never structurally executed. The five-surface anchors already exist (CommandCenter/Work/RealityGraph/ProofInspector/CapabilityMap) but the model is expressed nowhere in routes, palettes, or stores. Electron production builds have a broken API binding (`file://` origin + relative `/api/umh` base) and side-door ungoverned filesystem writes via IPC (`cockpit/src/main/index.ts:153-177`). (Ledgers F1/F2.)

**Runtime nodes / trust — the trust boundary is decorative.** Mesh WS auth returns True unconditionally when no tokens are configured and never binds token to node identity — any valid token can register as any node (`transports/node_mesh/server.py:470-487`); the HTTP relay's `/dispatch` auth passes through when `UMH_MESH_RELAY_SECRET` is unset (`server.py:894-898`); risk class of remote execution is caller-declared with a permissive default (`nodes/windows/umh_node/client.py:458`) and the executor-side shell adapter has zero deny patterns; the governed spine has no references to mesh or nodes at all. Five parallel node models with three incompatible role vocabularies describe the same two machines; the declared adapter contract (`adapters/protocol.py`) is implemented by 1 of ~100 adapter files; the credential gate has exactly one caller repo-wide; there is no emergency stop, no cancellation, and no rollback primitive anywhere in the actuation path. (Ledger G.)

**Tests / certification — 15,017 tests that cannot run and no CI to notice.** `pytest tests --collect-only` collects 15,017 tests then INTERRUPTS on 3 module-level ImportErrors; `.github/workflows/` contains only `mobile-build.yml` — no CI executes pytest at all. 29 test files pin `sys.path` to deleted worktrees; 155 hardcode `/opt/OS`, so worktree runs silently test main-repo code. Misleading patterns are systemic: enum-literal self-assertions, 11 files asserting on `inspect.getsource` strings, a mesh-dispatch "contract test" that re-implements the chain inside the test, canon certification suites that go green by mass skip (94+61 skips when the artifacts they certify are absent). There is no acceptance test for governed-mutation compliance, projection inheritance (zero files mention inheritance), node trust / permission envelopes, or L1→L4→L2/L3 grounding. (Ledger H.)

---

## 3. Intended Target Architecture

The converged design that the backlog's P0–P6 phases walk toward. Nothing here is speculative — every element is the "desired state" side of a gap whose current state is evidenced above.

**One governed operation runtime.** A single spine — `GovernedExecutionSpine` (`substrate/organism/governed_spine.py:197`) reached through `MutationRouter` (`substrate/organism/mutation_router.py:93`) — is the only path by which state changes. The submission entry point lives in substrate (not the transport layer), fails closed, and every mutation name resolves to a registered `MutationSpec`; the `state_mutate` catch-all is retired. The rival spines (`substrate/execution/spine.py`, `substrate/execution/runtime/execution_spine.py`, `substrate/execution/pipeline.py`) are migrated or deleted; one event backbone (`substrate/organism/event_spine.py`) carries pub/sub. The runtime emits the currently missing primitives: a **StateCommit** per applied change (before/after hashes, authority ref, rollback ref, idempotency key) into a single commit log; a typed **ProofContract** before execution; **TraceEvents** into one declared trace-store authority; an **EvaluationResult** against acceptance criteria after. Operation queues are durable — pending work survives process restarts with declared RPO/RTO (WP-P1-012, WP-P1-021).

**One canonical primitive set.** `substrate/types.py` (or its successor) is the single L2 definition module; `substrate/canonical_types.py` registers 100% of exported public types; the divergence gate validates that registry entries resolve to real symbols and rejects same-name/different-module definitions, and runs full-scan in CI, not staged-only. One WorkPacket, one risk taxonomy, one ApprovalRequest, one RuntimeNode (`UMHNodeRecord` as the identity spine), one Intent, one MemoryCandidate, one adapter contract — each with boundary DTOs formally mapped rather than parallel definitions. See §5 and [UMH_CANONICAL_PRIMITIVE_MAP.md](UMH_CANONICAL_PRIMITIVE_MAP.md) for the per-primitive owner decisions.

**Four-layer ontology separation.** Substrate owns mechanisms (stores, contracts, decay, promotion, bridges, laws, authority graphs, registration ports); projections own content (domains, primitives, keyword maps, seeds, entity kinds), supplied at runtime through the registration seams that already exist (`BridgeRegistry`, `ProjectionPort`). L1 gains external-entity kinds (person, organization, customer, lead, account) with per-entity state authority; L2 sheds EOS doctrine and EOS entity types; L3 domain schemas are owned in the code layer with an automated correspondence check against the vendored `schema.ts` sources; L4 gains a unified entity-resolution contract (composing `ContextResolutionEngine` + `IdentityResolver` + `EntityLinkStore`) and a versioned, migrated writeback schema. Boundary detail: [UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md](UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md) §4.

**Projection inheritance through published contracts.** One projection record (`ProjectionContract`, extended) behind one port (`substrate/sockets/projection_port.py`); the forecast type that currently owns the canonical name `Projection` is renamed. Registration is manifest-driven so the second-through-nth projection is as cheap as the first: manifest + handlers + tables + poller activate through a generic registration runtime rather than hand-wired `_register_eos_integration()`-style code. Every projection is either wired end-to-end (poll → signal → handler → outcome writeback) or explicitly classified dormant; projection-inheritance acceptance tests prove domain models inherit platform contracts without divergence.

**Trust-bounded runtime nodes.** One canonical RuntimeNode entity joins the five current models; device registries project from it. Mesh auth is fail-closed with token→node-identity binding; capability declarations are attested against the registry-declared role envelope; risk class is derived server/node-side from operation content, never caller-declared; every dispatch carries a verifiable governance verdict and emits a trace event; SSH host keys are pinned per registry entry; credentials flow through the credential gate at every authenticated actuation. The actuation path gains an emergency-stop/cancel RPC, a compensating-action (rollback) declaration per reversible capability, and a safety-envelope contract that must exist before any PHYSICAL_WORLD adapter ships.

**Five cockpit surfaces.** The client becomes a faithful projection of the control plane, organized into five surfaces: **Command** (issue intent, approve, converse — CommandCenterPanel + one approval queue + shell chat), **Operations** (running work: packets, agents, queues, nodes, continuity — WorkPanel/MetaIDE anchors), **Reality** (external world state, entity resolution, state authority — RealityGraph/StateAuthority anchors), **Proof** (traces, proof artifacts, evaluations, audits — ProofInspector/Activity anchors), **Capability** (registry, skills, templates, adapters, settings — CapabilityMap/Settings anchors). One domain store per control-plane object family replaces the 77 per-panel stores; a decision made on any surface is visible on all; declared absorptions become structural (anchor renders the absorbed content; absorbed routes retire). Layout lock (2026-07-03) is respected — this is information architecture and state-layer work, not visual redesign.

---

## 4. Four-Layer Model Summary

Condensed from [UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md](UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md), which carries the full file map, blended-concepts table, and entity-category mapping.

| Layer | Definition | Canonical home (proposed) | Current state |
|---|---|---|---|
| **L1 — External Operational Reality Model** | What is true outside UMH, with what evidence, since when: entities, observations, patterns reconciliation targets | `substrate/reality_model/` (observation store, pattern store, governed write path, simulation) | Cleanest of the three ontology homes, but no PERSON/ORG/CUSTOMER/LEAD entity exists anywhere at L1/L2 — `RealityEntityType` (`substrate/organism/reality_graph.py:35-51`) covers 16 dev/infra kinds only; market-signal acquisition contaminated with instance content |
| **L2 — UMH Platform Metamodel** | The platform's model of itself: types, invariants, execution objects, state authority, lineage | `substrate/types.py` + `substrate/canonical_types.py`; `substrate/ontology/laws.py`; state-authority and lineage modules in `substrate/organism/` | Carries L3 content it must shed: EOS entity types at `substrate/types.py:1108-1254`, EOS doctrine in `substrate/understanding/`, venture-portfolio rows in `substrate/organism/domain_registry.py:201-249`; projection registration fragmented ≥4 ways |
| **L3 — Projection Domain Models** | Each product's entities, workflows, vocabulary (EOS, CreatorOS, LyfeOS, BroadcastOS, …) | `projections/<name>/` + `data/repos/<name>/shared/schema.ts` as source-of-record | EOS typed against L2; CreatorOS/LyfeOS integration-only dormant shells; integration coverage a thin slice (EOS 5/15, COS 4/20, LyfeOS 4/35 tables); dual hand-maintained schema truth with no drift check |
| **L4 — Semantic Grounding / Mapping** | Entity resolution, observation→domain mapping, projection↔platform sync, source-of-truth/state-authority assignment, evidence linking | `substrate/understanding/domains/{contract,registry}.py` (bridge seam), `substrate/reality_model/` evidence retrieval, `substrate/organism/state_authority_graph.py` + `infra/state_authority_registry.json` | Of ~20 mechanisms: 8 wired, 7 implemented-but-dormant (test-only dependents), 2 partial, 4 missing — the missing four are exactly what multi-projection reconciliation cannot operate without (cross-source entity resolution, non-EOS sync, schema-drift detection, writeback provisioning verification) |

The blended-concepts inventory (ontology doc §3) is the working list of what must be teased apart: "primitive" (L1 vocabulary vs L3 business rules under one name, with L4 bridges typed against a divergent legacy copy), "world model" (L2 self-model vs L3-seeded knowledge store sharing a name), "reality" (three subsystems plus an enum member, no boundary document), "domain" (four distinct meanings, free-text tag grounded against none), "projection" (four unrelated concepts, with the product concept — the one L3 governance needs — owning no canonical name), and three-plus unlinked source-of-truth taxonomies.

---

## 5. Canonical Primitive Map

Status rollup from [UMH_CANONICAL_PRIMITIVE_MAP.md](UMH_CANONICAL_PRIMITIVE_MAP.md), which carries the full 33-row mapping table (definition, current canonical file, competing files, tests, required convergence action per primitive).

| Status | Count | Primitives |
|---|---|---|
| canonical-clean | 1 | StateAuthority |
| canonical-but-contested | 5 | Gap, PolicyDecision, TraceEvent, Template, DomainBridge |
| fragmented | 18 | Signal, Intent, CurrentState, WorkPacket, AdapterCall, RuntimeNode, RuntimeSession, AgentRole, ApprovalRequest, ProofArtifact, EvaluationResult, MemoryCandidate, MemoryRecord, Capability, Projection, ProjectionDomainObject, ExternalWorldEntity, EntityResolution |
| fragmented + broken (verified import-time failures) | 1 | Operation |
| missing | 8 | DesiredState, ExecutionStep, ToolCall, AgentInstance, ProofContract, StateCommit, CapabilityPathway, CapabilityRevision |
| **Total** | **33** | |

Reading for planning purposes: the 8 missing primitives are concentrated where a reconciliation control plane carries its core guarantees — the desired-state spec (DesiredState), the commit log (StateCommit), the pre-execution evidence contract (ProofContract), and the agent-action unit (ToolCall). The fragmentation cluster concentrates at same-name/different-schema collisions the existing divergence gate structurally cannot catch (registry incomplete; gate does not verify registered names resolve to real symbols). Sequencing: fix the gate and registry first (WP-P2-001), repair the two verified import breakages (WP-P0-008), close the ungoverned-mutation fail-open (WP-P0-001), then per-primitive convergence critical → high (WP-P2-002 … WP-P2-020).

---

## 6. Overlap / Duplication Ledger

Every N-way duplicate found across the ledgers, with the recommended canonical owner and the closing packet. This table is the collapse map: converging rows 1–4 (spine, approvals, types, nodes) removes the mechanism that keeps regenerating the rest.

| # | Concern | N | Instances (evidence) | Canonical owner recommendation | Packet |
|---|---|---|---|---|---|
| 1 | Execution spines / pipelines | 5 | `substrate/organism/governed_spine.py` (canonical); `substrate/execution/spine.py:389-427` (ungoverned memory writes); `substrate/execution/runtime/execution_spine.py:86` (legacy sync, LIVE in Discord); `substrate/execution/pipeline.py:142` (parallel full pipeline, own proof+memory); `substrate/execution/bridge/event_spine.py` (name-collides with canonical bus) | `GovernedExecutionSpine` via `MutationRouter`; others migrated/deleted | WP-P1-001, WP-P1-006 |
| 2 | Event backbones | 2 | `substrate/organism/event_spine.py` (canonical pub/sub per PLATFORM_SPEC §3) vs `substrate/execution/bridge/event_spine.py` (imported by deployed bot, `services/discord_bot.py:108`) | `substrate/organism/event_spine.py` | WP-P1-001 |
| 3 | Approval state machines / channels / UI surfaces | 4 / 3 / 11 | Machines: GovernedWorkRuntime plan FSM, `substrate/organism/execution_coordinator.py`, `substrate/organism/command_runtime.py` JSONL lifecycle, spine approve/reject. Channels: OperatorApprovalGate + Discord `transports/discord/approval_bridge.py:68`, `services/cc_webhook_receiver.py` tmux injection, `nodes/distribution/distributor.py:218`. UI: 11 cockpit surfaces over ≥9 stores/endpoint families (F1 duplicate cluster 1; GAP-F2-001) | One canonical ApprovalRequest type + one pending-work store + typed approval port; all surfaces render projections of it | WP-P1-007 (server), WP-P5-004 (client), WP-P4-009 (EOS product loop) |
| 4 | WorkPacket variants | 4 | `substrate/organism/work_packet.py:117` (recommended, unregistered); `substrate/types.py:929`; `substrate/control_plane/router/router_contracts.py:91` `RouterWorkPacket`; `nodes/environments/work_packet.py:49` (dormant, doubled-prefix rename damage) | `substrate/organism/work_packet.py` WorkPacket as the Operation record; boundary DTOs formally mapped | WP-P2-005 (breakage first: WP-P0-008) |
| 5 | Type system modules | 2 | `substrate/types.py` (~90 definitions) vs `substrate/canonical_types.py` (registry defining no classes, incomplete, homonym-sanctioning, 17-module LEGACY_DUPLICATES) | types.py defines; registry covers 100% of public types; gate validates symbol resolution | WP-P2-001 |
| 6 | Risk taxonomies | 4 | `substrate/types.py:252` RiskClass; `substrate/governance/risk_classes.py:17-66` ActionRiskCategory (rebinds RiskClass with type-ignore); `nodes/windows/umh_node/governance.py:12-21` string-list copy; `nodes/environments/work_packet.py:32-39` packet risk enum | Single canonical risk enum in the type registry; wire format uses its values; node imports/vendors the same enum | WP-P2-002 |
| 7 | Runtime-node models / role vocabularies | 5 / 3 | `infra/device_registry.json`; `infra/umh_node_registry.json` + `substrate/organism/umh_node_topology.py` UMHNodeRecord; mesh ConnectedNode (`transports/node_mesh/integration/types.py:81-129`); `substrate/organism/runtime_graph.py:131` RuntimeNode; `substrate/organism/device_role_registry.py:54` DeviceNodeProfile. Role vocabularies: orchestrator/executor/controller vs workstation/builder/observer vs heavy_workstation/cockpit_ui | UMHNodeRecord as single node identity + one role enum; registries become projections; registry lint cross-validates | WP-P2-010, WP-P1-018 |
| 8 | Adapter contracts | 6 | `adapters/protocol.py:10-19` (1/100 implementations); `adapters/tool_adapters/base.py:12-50` BaseAdapter; `substrate/execution/executor.py:27-31` AdapterProtocol; `adapters/adapter_engine/adapter_manifest.py:39-60` manifests (descriptive only); duck-typed `nodes/windows/umh_node/adapters/*`; mesh NodeCapabilityHandler proxies | One typed contract (request/response + classify_risk + health + capabilities) + every adapter in one capability registry | WP-P2-011 |
| 9 | Operator-intent kernels | 4 | dex_conversation (live `/dex/converse` + Discord); OrchestratorKernel (`transports/api/organism_bridge.py`); operator loop coordinator (`substrate/organism/operator_loop_coordinator.py`); OperatorLoopRuntime ("This IS the product", `substrate/organism/operator_loop_runtime.py:3`) | One declared kernel; rivals demoted to adapters over it | WP-P1-017 |
| 10 | Operator identity stores | 4 (+2 auth models) | Platform `users` (`transports/api/http/db/schema.ts:75`); EOS/CreatorOS/LyfeOS product `users` tables (Firebase / serial-int / Stripe+2FA variants); plus Clerk identities and API-key CLI auth — no identity bridge | Platform identity model + L4 identity-resolution bridge to product user rows; CLI aligned to platform identity | WP-P3-011, WP-P5-019 |
| 11 | API entrypoints | 4 | `services/operator_api.py` (DEPLOYED :8091); `transports/api/app.py` (undeployed, singleton imported cross-container); `transports/api/operator.py` (dead, NameError at import); `transports/api/http/server.ts` (undeployed Hono, spawns a fresh daemon per request via `transports/api/http/lib/python_bridge.ts:17`) | One declared canonical entrypoint; dead duplicate deleted; ARCHITECTURE.md §9 corrected; TS stack retired or wired to real executors | WP-P1-001, WP-P2-022 |
| 12 | Ontology homes | 3 | `substrate/ontology/` (laws + shims); `substrate/reality_model/` (L1 stores + L2 write path + L4 evidence); `substrate/understanding/` (blended: L3 doctrine, divergent L1 vocabulary copy, L4 bridges, contaminated L1 acquisition) | Per §4 boundaries: reality_model = L1; ontology/laws = L2; domains contract/registry = L4 seam; L3 content exits substrate | WP-P3-003, WP-P3-015, WP-P3-016, WP-P3-017 |
| 13 | Domain registries | 2 | `substrate/organism/domain_registry.py:325` DomainRegistry (L2 governance, dormant, carries venture rows) vs `substrate/understanding/domains/registry.py:8` BridgeRegistry (L4, wired, unregistered in type registry) | BridgeRegistry as the L4 seam (registered); domain_registry mechanism kept, instance rows move to projection-supplied registration | WP-P3-014 |
| 14 | Projection registration mechanisms | ≥4 (+2 ports) | `substrate/types.py:1363` ProjectionContract (unregistered); `substrate/sockets/projection_port.py:60,155` (+legacy in-memory dict :33-51); `substrate/organism/projection_certification.py` ProjectionRegistry; `substrate/organism/projection_integration_runtime.py`; second unrelated `substrate/organism/projection_port.py:41` | Extended ProjectionContract behind the single sockets port; forecast `Projection` renamed to free the canonical name | WP-P3-004 |
| 15 | Entity-resolution mechanisms | 3 | `substrate/organism/context_resolution.py` (NL→project/repo/device); `substrate/control_plane/identity/__init__.py:15,21` IdentityResolver (signal→operator); `substrate/state/stores/entity_link_store.py:7` (insert-only, no resolve API) | Unified L4 resolution contract composing all three + cross-source external-entity resolution | WP-P3-011 |
| 16 | Trace stores / Trace name | 2 | Neon `traces` via `substrate/execution/trace.py:39` vs JSONL `substrate/observability/trace_store.py:36` (class `Trace` collides with alias `Trace = TraceRecord`, `substrate/types.py:462`) | types.py TraceEvent/TraceRecord + one declared store authority; alias retired | WP-P1-015 |
| 17 | Proof types | 5 | `substrate/types.py:881` Proof; `substrate/execution/runtime/runtime_execution_result_v1.py:42` ProofArtifact; ProofPackage ×2 same-name (`substrate/organism/proof_runtime.py:51` vs `substrate/organism/proof_store.py:33`, incompatible schemas); `substrate/meta_ide/engineering_execution.py:210` — 55 proof-named classes, ≥3 proof-ID namespaces | `Proof` as canonical envelope; others become typed payload variants in one proof_id namespace | WP-P1-016 |
| 18 | MemoryCandidate schemas | 4 | `substrate/types.py:786`; `substrate/organism/memory_promotion.py:74`; `substrate/memory/candidate_generator.py:33`; `adapters/adapter_engine/live_drive_docs_ingestion_pipeline_v1.py:183` — zero registered; status enums 7/4/3-state + string | One registered MemoryCandidate + unified promotion-status enum; adapter variant maps at L4 boundary | WP-P2-016 |
| 19 | Canonical/instance store dualities | 3 | `substrate/reality_model/{canonical,instance}.py`; `substrate/understanding/world_model/world_model.py:35-131` own duality with own promotion; memory canonical_write path (self-described "PARALLEL" at `substrate/reality_model/canonical_reality_write.py:5-12`) | reality_model stores canonical; world-model entry store deprecated into them | WP-P3-003, WP-P3-018 |
| 20 | WorldModel classes | 2 | `substrate/organism/world_model.py:145` (L2 self-model) vs `substrate/understanding/world_model/world_model.py:134` (L3-seeded knowledge store) — docstring must disclaim the collision | Organism self-model keeps the concept, cedes the "world" name; understanding store deprecated | WP-P3-018 |
| 21 | Signal intake types / routers | 2 / 2 | `substrate/types.py:48` SignalEnvelope vs `substrate/types.py:990` Signal (unregistered); sockets envelope same-name different-shape; rival router `transports/api/signal_router.py:31` vs control-plane router | One intake type + one router contract | WP-P1-011 |
| 22 | Intent lifecycles | 4 | CanonicalIntent (`substrate/operator/intent_runtime.py`, registered); `substrate/types.py:753` Intent; `substrate/workstation/intent_contract.py:42`; `substrate/meta_ide/engineering_intent.py`; plus 3 IntentType enums, 2 IntentRouter name collisions | CanonicalIntent as sole L2 intent record | WP-P2-008 |
| 23 | RuntimeSession homonym | 2 | `substrate/organism/runtime_session.py:115` vs `substrate/execution/runtime/runtime_session_registry_v1.py:35` — same name, disjoint schemas; 7+ adjacent session models | Keep organism variant; rename the v1 registry class; register both | WP-P2-009 |
| 24 | Voice stacks | 3 | `umh/voice_server.py` (WS :8096, unauthenticated); C20 `substrate/workstation/` voice runtimes; `substrate/execution/voice` Discord engine | One ingress contract; real-microphone acceptance closed | WP-P2-027 |
| 25 | Presence modules / routes | 5 / 4 | organism, operator, 3× workstation presence modules; 4 cockpit route files; plus cockpit presenceStore vs OperatorContinuityPanel overlaps | One presence state authority; other modules become views | WP-P2-024 |
| 26 | Workstation runtime generations | 3 (+33 dormant) | `substrate/organism/workstation_runtime.py` (1,400L); `substrate/workstation/unified_workstation_runtime.py` (claims "single source of truth"); `substrate/execution/workers/workstation/` engines; 33 undispositioned `_dormant/` modules | Declared source of truth; dormant engines dispositioned PROMOTE/MERGE/ARCHIVE/DELETE | WP-P2-025 |
| 27 | Cockpit approval/work/timeline/node/continuity panel clusters | 11 / 12 / 6 / 8 / 8 | F1 duplicate clusters 1–6: approvals 11 surfaces; work packets 12 panels over ≥3 endpoint families; timelines 6; node topology 8; session/continuity 8; strategy 5 | One anchor view per concern; absorbed panels become tabs; five-surface route taxonomy | WP-P5-003 … WP-P5-011 |
| 28 | Cockpit canvas layout stores | 7 | canvasStore, unifiedCanvasStore, agentCanvasStore, harnessCanvasStore, loopCanvasStore, organismCanvasStore, workflowCanvasStore — independent persisted layout schemas | One canvas layout store parameterized by mode | WP-P5-005 |
| 29 | Push-notification registration paths | 2 | native `cockpit/src/renderer/capacitor-init.ts` → `/push/register` vs web `cockpit/src/renderer/lib/pushNotifications.ts` → `/push/subscribe`; file-based subscription store declared at `transports/api/cockpit_push_routes.py:24` | Unified registration model in platform DB keyed by operator+device | WP-P5-017 |
| 30 | Mesh live-state snapshots | 2 | two divergent snapshot targets declared in code: `transports/node_mesh/registry.py:14` (hardcoded `/opt/OS/data/runtime/mesh_nodes.json`) vs `transports/node_mesh/server.py:777-823` (writes `mesh_metrics.json` under data/umh/organism/) — different schemas; both are runtime artifacts, code-declared | Single snapshot schema under the canonical node record's state authority | WP-P2-010, WP-P6-019 |
| 31 | DimensionScore definitions | 3 | `substrate/organism/readiness_model.py:47`; `substrate/organism/template_governance.py:86`; `substrate/organism/trust_score.py:57` | Single DimensionScore under canonical EvaluationResult | WP-P2-017 |
| 32 | Source-of-truth taxonomies | 3+ | StateAuthorityLevel (`substrate/organism/state_authority_graph.py`); SourceCanonicality (`substrate/organism/projection_source_registry.py:48`); `DomainProjection.authority_tier` (bare int) | Unified under StateAuthority with per-entity granularity | WP-P3-007 |
| 33 | Forecast panels ("Projection" misnomer) | 2 | `cockpit/src/renderer/panels/ProjectionPanel.tsx` (forecasts) duplicating orphaned PredictionPanel; name collides with the platform projection concept | Merge as Forecasts; reserve "Projection" for L3 projection registry | WP-P5-013 |

---

## 7. Execution Spine Audit

Full report: [UMH_EXECUTION_SPINE_COMPLIANCE.md](UMH_EXECUTION_SPINE_COMPLIANCE.md) (path-by-path compliance matrix over the Python mutation core, 143 FastAPI files, the Hono TS surface, services/cron, node mesh, adapters, Discord, and projections).

**Compliance totals.**

| Measure | Value | Reading |
|---|---|---|
| Python API files / HTTP handlers / mutation handlers | 143 / 1,306 / 320 | `governed_mutation()` call sites: 360 |
| FastAPI files fully canonical-governed | 68 / 143 | 47 read-only, 14 non-route support; **18/143 carry governance risk** (SD/SD-latent/GF/DEP/UNC) |
| Hono TS mutations that actually execute | **0 / 33** | All 33 route through `governedMutation()`, but the bridge's `execute_fn` echoes the payload and does nothing (`transports/api/organism_bridge.py:2351-2352`) — proof artifacts assert effects that never happened (dormant surface) |
| services/ entrypoints fully governed | 1 / 23 | The services tier is predominantly fragmented/side-door/dormant |
| cron entries with any policy gating | ~1 / 20 | Only secret rotation; the rest is a parallel ungoverned mutation plane on 5–15 min cadences |
| Node dispatch paths carrying a governance verdict | 1 of 2 | Governed capability-socket path vs raw fail-open HTTP relay to the same adapters |
| Single state authority for "what is pending approval" | No | 4 parallel approval state machines + 3 parallel approval channels |

**Side-door ledger, ranked by blast radius** (SD-01…SD-09 are the individually enumerated doors; full text in the compliance report §3):

| Rank | Side door | Blast radius | Evidence | Packet |
|---|---|---|---|---|
| SD-01 | `governed_mutation()` fails open to direct ungoverned execution (`completed_ungoverned`) when the daemon is down | EVERY mutation route (360 sites) | `transports/api/governed.py:91-111` | WP-P0-001 |
| SD-02 | Mesh HTTP `/dispatch` unauthenticated when `UMH_MESH_RELAY_SECRET` unset; no risk class, no verdict in payload | Arbitrary remote code on any connected node | `transports/node_mesh/server.py:894-898, 973-1039` | WP-P0-002 |
| SD-03 | TS governed bridge records mutations without executing them (proof-artifact integrity broken; latent — undeployed) | All 33 TS mutations | `transports/api/organism_bridge.py:2351-2352`; `transports/api/http/lib/governed_bridge.ts:29-55` | WP-P1-005 (Hono disposition: WP-P2-022) |
| SD-04 | Remote-terminal endpoints (`/terminal/remote/*`) dispatch arbitrary shell to mesh nodes with no spine, while the local sibling in the same file IS governed | Arbitrary remote shell per HTTP call | `transports/api/cockpit_workstation_control_routes.py:54-60, 278-371` | WP-P0-002 |
| SD-05 | Nightly cron runs an autonomous write-enabled Claude agent (`--allowedTools "Bash Read Write Edit …"`) on the production repo outside all governance | Production repo write+shell nightly | `scripts/scheduled/nightly_maintenance.sh`; `infra/crontab.managed` | WP-P0-005 |
| SD-06 | `cc_webhook_receiver` binds 0.0.0.0:8765 with zero auth; carries MFA codes; second approval channel via tmux injection | MFA relay + CC session control | `services/cc_webhook_receiver.py:8, 100-229, 305-308` | WP-P0-004 |
| SD-07 | External mutations (email send, calendar create, LLM-decided invite auto-accept) execute outside governance; only the bookkeeping UPDATE is wrapped | Externally visible third-party actions | `services/discord_bot_commands.py:505-580`; `scripts/calendar_invite_handler.py:170-306` | WP-P1-010 (with WP-P0-005) |
| SD-08 | Cron layer mutates Neon `events` + Notion directly every 5–15 min (agent_task_executor, call_prep, noshow_detector, notion syncs) | Neon + Notion continuously | `scripts/agent_task_executor.py:101-265`; `infra/crontab.managed` | WP-P1-010 |
| SD-09 | Node trusts caller-declared risk class (default REVERSIBLE_WRITE); governance_verdict_id transmitted but never validated; weak allowlist (`command.split()[0]`, unnormalized `startswith` path check) | All node write-class actions | `nodes/windows/umh_node/client.py:452-500`; `governance.py:31-64` | WP-P0-003 |
| SD-10..14 | Ungoverned autonomous-lane endpoints; 5 unregistered mutation names that invert governance (fail when daemon up, succeed ungoverned when down); dormant unauthenticated services (goal_api, higgsfield_webhook, local_bridge_server); ungoverned chat-media upload; canonical-reality write side-doors; ungoverned command-runtime direct routes; side-door AgentMemory writes | Medium / bounded / dormant | compliance report §3 | WP-P1-002/003/004, WP-P0-006, WP-P3-008 |

**Broken-call-path ledger** (governed paths that silently produce nothing — both AttributeErrors swallowed at debug level, both verified against source):

1. `substrate/organism/governed_work_runtime.py:232` calls nonexistent `packet_engine.create_from_intent` (actual: `create_packet_from_intent`, `substrate/organism/work_packet_engine.py:67`) — the "mandatory DO layer" never creates real packets; no test exercises submit_work. → WP-P0-007
2. `substrate/organism/command_runtime.py:896` calls nonexistent `UniversalWorkQueue.update_status` (actual: `update_packet_status`, `substrate/organism/universal_work_queue.py:237`) — every packet approve/reject through an operator command returns an error dict. → WP-P0-007

**The convergence gap in one line:** governance is real and enforced at the deployed HTTP boundary, and absent or bypassable everywhere that boundary is crossed by another route — the fail-open wrapper below it, the mesh relay beside it, the cron/services/node planes underneath it. Converging the spine means making the transport-layer guarantee hold below the transport layer, not adding more governed routes.

---

## 8. Projection-Derived Substrate Capability Matrix

Full matrix: [UMH_PROJECTION_CAPABILITY_MATRIX.md](UMH_PROJECTION_CAPABILITY_MATRIX.md) — 47 substrate capability categories × 11 projections, with per-capability owners, evidence, and gap pointers. (Row 47, Tool mastery / knowledge-gap composition, was added 2026-07-04 after hostile review found `substrate/composition/` outside all Phase-1 ledger scopes — see §17.)

**Per-projection readiness rollup:**

| Projection | Verdict |
|---|---|
| EOS | Most integrated projection; runtime-untested beyond unit level. Only projection registered at runtime; workflows governed; but bridge covers a CRM slice only, two unlinked approval systems, identity/OAuth/writeback authority unclear, cross-tenant task read (GAP-D2-001, critical) |
| CreatorOS | Dormant shell — manifest/handlers/tables pass unit tests, never registered; no poller; community/social graph (8 tables) has zero UMH surface |
| LyfeOS | Dormant shell with the largest domain gap (~35-table surface vs 3 polled tables on an unwired bridge); recurrence/rituals have no substrate scheduling primitive |
| Jarvis/Operator | Broadest shipped surface; worst fragmentation — 4 intent kernels, ≥9 approval stores, 3 voice stacks, presence ×5, continuity loop unimplemented |
| Workstation | Three coexisting code generations; 33 dormant engines without disposition; single-host filesystem durability, no recovery SLO; mesh capped at one hardcoded executor node |
| Meta IDE | Most coherent shipped projection — correct dependency direction, strongest verification primitives; residual: governed HTTP path undermined by ungoverned Electron IPC sibling |
| BroadcastOS | Deepest vertical slice with genuine proof discipline; agent path unwired at boot; audio/real capture/hardware encode/cross-host egress spec-only |
| Conference Rooms | Functionally shipped; structurally fragile — state authority is unlocked flat JSON with silent data-loss masking; transcription/recording are permission-gated stubs |
| SecurityOS | Zero repo evidence — all cells inferred; gated behind physical governance prerequisites |
| ManufacturingOS | Strategy-intent only, correctly sequenced post-revenue |
| RoboticsOS | Strategy-intent only, 10+ year horizon; "actuator" namespace already means GUI actuation (collision risk) |

**Per-capability universality (three tiers):**

- **Tier 1 — canonical somewhere, extensible (the substrate's real assets):** the governed-mutation policy/authority path (enforced in EOS workflows, Broadcast, Rooms, workspace I/O, and all mutation-bearing cockpit route files at coarse scan); the adapter/integration contract (manifest+handler+signals+outcomes — proven end-to-end once, copied correctly three more times); local evidence discipline (actuator maturity levels, broadcast proof reports) not yet a shared L2 contract.
- **Tier 2 — present everywhere, fragmented everywhere (highest-leverage convergence targets):** approval routing (worst case in the audit); identity/tenancy (4 stores + Clerk + API-key CLI, no bridge); operator intent ingestion (4 kernels); notifications, voice, presence, screen awareness, state authority, timelines/traces, work packets, node registry — each with 3–8 rival implementations and no declared owner.
- **Tier 3 — missing everywhere (build-new, mostly L2/L4):** physical safety envelope / e-stop / rollback; cross-projection entity resolution / identity bridge; commerce/payments; media asset management; recurring-schedule reconciliation; pre-actuation impact analysis; social publishing adapters.

**Structural pattern:** the governed-mutation spine and the integration contract are sound and reused; what is missing is (a) a registration/wiring runtime that makes the second-through-nth consumer of any contract as cheap as the first, and (b) declared state authority per concern. Nearly every fragmented or unclear-authority cell reduces to one of those two deficits.

---

## 9. Cockpit Convergence Audit

Sources: ledgers F1 (78 panels + components) and F2 (77 stores, API client layer, data flow, distribution surfaces).

**Verdict: fragmented panel museum with a genuine mission-control spine emerging.** The 6-primary-route reduction, the single-shell canvas-window architecture (`cockpit/src/renderer/components/canvas/windows/PanelWindowContent.tsx`, 78 lazy entries), and the C28 orphan-rescue show active convergence discipline — but convergence has operated at the navigation layer (demote to [DEV]) rather than the information-architecture layer. 72 of 78 panels remain live code paths with private stores; each core control-plane concern is rendered by 4–12 independent panels against inconsistent endpoint families; `cockpit/src/renderer/types/routes.ts` comments declare absorptions ("Absorbed into Command Center" :102, "Absorbed into Activity" :120) that were never structurally executed — the convergence ledger and the code disagree.

**Five-surface mapping summary** (all 78 panels classified; F1 carries the full per-panel table):

| Surface | Panels | Anchors (MVP-critical) | Notable duplicates |
|---|---|---|---|
| Command | 14 | CommandCenterPanel (primary), ApprovalsPanel, ControlPanel (shell chat/approvals) | CommandsPanel (parallel command+approval pipeline), ActionsPanel, Strategy/Strategic/Executive/Goal quadruplication, Dashboard/OperatorHome |
| Operations | 35 | WorkPanel (primary), RecoveryDashboardPanel, MetaIDEPanel (primary, 1,285 lines) | UniversalWorkPanel (second work-packet browser on a different endpoint family), Tasks/WorkIntelligence orphans, ExecCoord+Executor pair, 4 loop panels + LoopCanvasWorkspace, 8 session/continuity surfaces, 8 node-topology surfaces |
| Reality | 13 | StateAuthorityPanel, KnowledgePanel (reality-model snapshot), RealityGraphPanel (strongest L4 surface) | WorldModel/RealityIntelligence overlap; Prediction+Projection forecast duplication (misnamed vs the platform "projection" concept) |
| Proof | 10 | ProofInspectorPanel, ActivityPanel | OperatorTimeline/RealityTimeline duplicating Activity; GovernancePanel is an ORPHAN — governance observability is invisible in a governance-first control plane |
| Capability | 6 | CapabilityMapPanel, SettingsPanel | CapabilitiesPanel + SkillsPanel orphans; ProfilePanel raw-fetch bypass |

**Duplicate surfaces (headline numbers):** approvals — 11 surfaces, ≥4 endpoint families, ≥9 owning stores plus a localStorage-cached 10th copy in bootstrapStore (GAP-F2-001, critical); work packets/execution — 12 surfaces, ≥3 endpoint families; session/continuity — 8; node/infra topology — 8; timelines — 6; strategy — 5; loops — 4 panels + a dedicated canvas workspace re-importing them; capability registry — 4; canvas layout — 7 sibling persisted stores.

**Data-layer facts that make cross-panel coherence impossible by construction:** 77 stores near-1:1 with panels and no shared domain model; 551 `fetchApi` call sites in stores plus 148 direct call sites in 37 panels/components bypassing the store layer (including mutation POSTs); WS invalidation covers exactly 4 domains — every other fetch-based store serves stale state until manual refresh; unconditional 5s polling of 5 endpoints regardless of visible panel; `bootstrapStore` persists server state (approvals, pulse, mesh nodes) to localStorage with no TTL and re-seeds stores on rehydrate.

**Trust-boundary defects on the client:** chat media upload uses raw `fetch()` with no Authorization against a Clerk-guarded router (`cockpit/src/renderer/stores/chatStore.ts:123-127` — fails 401 on all surfaces); SessionPanel/ProfilePanel raw-fetch bypasses; voice WS carries no credential and vision WS ships a static build-time token in the public bundle (`cockpit/src/renderer/api/vision-ws.ts:161-162`); Electron production build is non-functional against the API (`file://` origin + relative base, `cockpit/src/main/index.ts:51`) and its IPC `fs:writeFile` is ungoverned while the equivalent HTTP path is governed; `cockpit/src/renderer/sw.ts:38` hardcodes the production domain and `cockpit/src/renderer/constants/devices.ts:20-57` embeds the operator's personal device fleet in the shipped platform artifact.

**MVP-critical list (the visible spine):** Command — CommandCenterPanel, ApprovalsPanel, ControlPanel. Operations — WorkPanel, RecoveryDashboardPanel, MetaIDEPanel. Reality — StateAuthorityPanel, KnowledgePanel, RealityGraphPanel. Proof — ProofInspectorPanel, ActivityPanel. Capability — SettingsPanel, CapabilityMapPanel.

**Nest / hide / defer (no deletion; IA-only, layout lock respected):** nest under Command — Commands, Actions, Intent, the Goal/Strategy/Strategic/Executive cluster as one strategy view, Dashboard+OperatorHome as one home, Operator, Comms. Under Operations — UniversalWork/Tasks/WorkIntelligence as WorkPanel tabs, ExecCoord+Executor as one execution-plan view, the 4 loop panels as one loop view (LoopCanvasWorkspace), the session/continuity cluster as one continuity view, the node cluster as one topology view (DistributedRuntimePanel is the most complete), Tmux inside MetaIDE, Broadcast on the projection domain shelf. Under Reality — WorldModel/RealityIntelligence into RealityGraph tabs, Prediction+Projection into one Forecasts view, Company+Portfolio as an L3 EOS shelf, ScreenAwareness+Presence into an observation view. Under Proof — OperatorTimeline+RealityTimeline into Activity, Governance/Learning/Memory/Intelligence as Proof tabs, MVPReadiness as an evaluation tab. Under Capability — Capabilities+Skills into CapabilityMap, Profile into Settings. Closing packets: WP-P5-003 (route taxonomy + structural absorption), WP-P5-004 (one approval domain), WP-P5-005 (domain-store layer), WP-P5-007…WP-P5-014 (per-concern consolidations).

---

## 10. Runtime Node / Adapter Trust Audit

Source: ledger G. Lead finding: **the mesh trust boundary fails open.**

**Node-model inconsistencies.** Five parallel node/device models with overlapping but non-identical fields and three mutually incompatible role vocabularies (§6 row 7). Cross-registry identity joins are fragile: device_registry `beast` ↔ mesh `windows-desktop` linked only by an optional `mesh_node_id` field; `infra/state_authority_registry.json` assigns state authority exclusively to `umh-*` IDs that the live mesh and RuntimeGraph never reference — live runtime state is never joined to state authority by ID. Reconciliation is one-directional and lossy: `substrate/organism/mesh_reconciler.py:146-212` maps capabilities via a 5-entry static map and drops the node's per-capability risk ceilings at the boundary. Live mesh state persists to two snapshot files with different schemas, one on a hardcoded `/opt/OS` path (`transports/node_mesh/registry.py:14`).

**Adapter-contract conformance.** The declared contract (`adapters/protocol.py:10-19`) is implemented by exactly one of ~100 adapter files (`adapters/models/llm_adapter.py`). Six contracts operate simultaneously (§6 row 8). `adapters/socket_registration.py:5` claims to be "the ONLY file that bridges adapters → substrate/sockets," but broadcast, github, tailscale, browser_auth, browser_exports, adapter_engine, and data_source_adapters bypass it. VPS-side tool adapters carry deny-regex + risk classification; the executor-side node adapters carry neither (`nodes/windows/umh_node/adapters/shell.py:13-59` — no deny patterns at all).

**Trust-boundary gaps (lead: fail-open mesh auth).**
- WS auth (:8094): `_authenticate()` returns True unconditionally when zero tokens are configured (`transports/node_mesh/server.py:470-473`); `_node_id_for_token()` exists but is dead code — node identity is self-declared at `node.hello` (:487), so any valid token can register as any node. Token travels in the WS URL query string. Plain `ws://`; network trust is Tailscale-implicit, unverified in code.
- HTTP relay (:8095): `/dispatch` auth passes through when the relay secret is unset (`server.py:894-898`); `/nodes` and `/health` are unauthenticated topology leaks; the relay binds 0.0.0.0.
- Permission envelope: executor defaults are open — `max_risk_class="IRREVERSIBLE_WRITE"`, empty allowlists mean allow-all (`nodes/windows/umh_node/config.py:22-26`); unconfigured adapters get a fresh permissive config (`client.py:462-463`). Risk class is caller-declared and defaulted (`client.py:458`); neither dispatch path supplies it, so every remote execution is evaluated at REVERSIBLE_WRITE regardless of content — a dispatched `rm -rf` passes node governance.
- Governance: `substrate/organism/governed_spine.py` contains zero references to adapters, mesh, or nodes; the socket dispatch path carries an opaque `governance_verdict_id` the node never validates; the 13-dimension `substrate/execution/runtime/workpacket_execution_gate_v1.py` is not imported by any mesh dispatch path (wiring UNVERIFIED).
- No node identity keys, no attestation of code version at connect, no capability-set validation against the registry-declared role; `DeviceNodeProfile.trust_level` is a free string never evaluated by any gate. SSH is TOFU (`StrictHostKeyChecking=accept-new`, `adapters/ssh/ssh_utils.py:19`) with a hardcoded key path — no host-key pinning.

**Credential handling.** `validate_credential_source()` (`substrate/execution/credential_gate.py:35`) has exactly one caller repo-wide (`substrate/meta_ide/browser_evidence_collector.py:289`). Notion, Tailscale, and GWS adapters use raw env credentials; the Windows node daemon reads a plaintext `.env` in ProgramData; only `adapters/browser_auth/clerk_auth.py` is on the documented 1Password `op run` path. Product-side OAuth token tables (EOS `oauth_tokens`, LyfeOS `integrations`) hold raw access/refresh tokens parallel to the platform credential path.

**Physical actuation maturity.** Actuation today is desktop GUI only (Chrome on the Windows executor). Genuine assets exist: an L0–L7 evidence-capped maturity ladder (`substrate/execution/actuation/actuator_maturity_v1.py:16-106`), a 7-backend registry with security_risk metadata (`actuator_backend_registry_v1.py:78-229` — metadata recorded but ignored in selection), and persisted proof artifacts (`windows_foreground_actuator_v1.py:213-314`). Defects: the evidence schema is Chrome-hardwired; "founder confirmation" is a recorded field, not a blocking gate; there is **no emergency stop or cancellation** for in-flight remote execution (timeout is the only bound: 600s relay / 300s node); **no rollback/compensation model** anywhere in the adapter or actuation path (`side_effects` exists on CapabilityResponse but nothing populates or consumes it); no per-node rate limits or blast-radius declarations. `PHYSICAL_WORLD` exists as a risk category with no gate, adapter, or safety-envelope semantics — it must become structurally impossible to actuate physically without a safety-envelope contract before any physical adapter ships. Closing packets: WP-P0-002, WP-P0-003, WP-P1-018, WP-P1-020, WP-P2-010, WP-P2-011, WP-P2-030, WP-P4-002, WP-P6-017, WP-P6-018.

---

## 11. Proof / Trace / Memory Audit

From ledger B3 material as synthesized in [UMH_CANONICAL_PRIMITIVE_MAP.md](UMH_CANONICAL_PRIMITIVE_MAP.md) §4.3. This is the evidence tier of the control plane — the layer that lets an operator trust that what the system says happened, happened.

| Primitive | Status | Decisive evidence | Convergence action (packet) |
|---|---|---|---|
| ProofContract | **missing** | Exists only as a stage-enum member and untyped string lists (`nodes/environments/work_packet.py:64,75`); coherence rule checks existence, not content | Typed ProofContract produced at the PROOF_CONTRACT stage, binding required artifact types + acceptance criteria to the operation (WP-P1-016) |
| ProofArtifact | **fragmented** | 5 overlapping proof types incl. a same-name `ProofPackage` collision with incompatible schemas (`substrate/organism/proof_runtime.py:51` vs `substrate/organism/proof_store.py:33`); 55 proof-named classes; ≥3 proof-ID namespaces; string-typed cross-references. Systemic integrity break: the dormant TS bridge records proof artifacts for mutations it never executes (SD-03) | `substrate/types.py::Proof` as canonical envelope; packages become typed payload variants in one ID namespace; content hash/signature added (WP-P1-016) |
| TraceEvent | **canonical-but-contested** | Registered and consumed, but: alias `Trace = TraceRecord` (`substrate/types.py:462`) collides with class `Trace` (`substrate/observability/trace_store.py:36`); dual persistence (Neon vs JSONL) with no reconciliation; **silent trace loss** via except-pass on persist (`substrate/execution/trace.py:124-126`); parallel SpineLineage lifecycle records not unified | Retire the alias; declare one trace-store authority; unify spine lineage into TraceEventType; dead-letter/retry with a persistence SLO (WP-P1-015) |
| EvaluationResult | **fragmented** | No canonical type; 12+ scattered score/verdict types; `DimensionScore` defined 3×; the quality gate returns an untyped dict and **fails open** (`{"score":0.5,"passed":True}` on any exception, `substrate/control_plane/governance.py:267-268`) | Canonical EvaluationResult generalizing FeedbackRecord/FeedbackEntry with criteria reference + evaluator method; fail-closed quality gate (WP-P2-017, WP-P0-009) |
| StateCommit | **missing** | The write path exists without the record: envelope → spine → four disjoint ledgers with no unified commit log; the fail-open wrapper produces state changes with no envelope, ledger entry, or proof | StateCommit emitted by the spine outcome stage into a single commit log (before/after hashes, authority ref, rollback ref, idempotency key); ledgers become indices (WP-P1-013) |
| MemoryCandidate | **fragmented** | Four same-name classes, zero registered, four status vocabularies (7/4/3-state + free string); cron/scraper paths write AgentMemory directly, bypassing the promotion pipeline entirely (spine report SD-10..14) | One registered MemoryCandidate + unified promotion-status enum; side-door memory writes routed through promotion (WP-P2-016) |
| MemoryRecord | **fragmented** | Canonical `MemoryEntry` shadowed by a provenance-rich second `MemoryEntry` (divergence-exempted); `CanonicalMemoryEntry` resolves to two different types; multiple write paths; canon "certification" suites for memory artifacts go green by mass skip (H) | Merge provenance fields into the canonical entry; `CanonicalMemoryStore` declared the single state authority (WP-P2-016) |
| PolicyDecision | **canonical-but-contested** | `GovernanceVerdict` vs `PipelineGovernanceVerdict` diverge on the executability law itself (CONDITIONAL executable or not); 11+ domain decision types carry no verdict lineage | Single verdict with a scope discriminator and one executability law; sibling decisions carry verdict_id (WP-P1-014) |

The pattern across this tier: every evidence mechanism exists in at least one strong local form, and none is a single, registered, fail-closed contract. Until StateCommit and ProofContract exist and the trace store has one authority, "the system proved it" is a per-subsystem claim, not a platform guarantee.

---

## 12. Test / Certification Audit

Source: ledger H. Ground truth: 377 test files (`find tests -name "*.py" | wc -l`), 15,017 tests collected, **3 collection errors interrupt the run** — `pytest tests` cannot execute today — and **no CI runs pytest at all** (`.github/workflows/` contains only `mobile-build.yml`).

**Cluster coverage table** (all 377 files classified, sums verified):

| Cluster | Files | Coverage classification |
|---|---|---|
| agents-runtime | 59 | PARTIAL (broad, shallow; heavy mocking — 79/377 files use MagicMock/monkeypatch) |
| campaign-suites (C16–C40) | 46 | LEGACY — retired scaffolding pinned; 3 break collection, 4 import deleted scripts |
| phase-clusters (phase9–35) | 46 | LEGACY |
| intelligence-ontology | 36 | PARTIAL |
| p-runners (P0–P3) | 28 | LEGACY/smoke |
| proof-trace-memory | 25 | PARTIAL — trace recorder real; memory tests exercise the DB-unavailable fallback only |
| certification-gates | 21 | MIXED — `tests/test_p1_phase9_architecture.py` is a genuine acceptance test; c28/c29 are environment-coupled scripts requiring live prod URL + executor SSH |
| capability-registry | 15 | PARTIAL |
| governed-spine-mutation | 14 | PARTIAL — real spine test exists (`tests/test_c34_mutation_router.py`); `governed_mutation()` covered only by a signature check; **no compliance test that mutation call sites route through it** |
| adapters | 13 | PARTIAL — only 5 files under tests/adapters/ vs a full adapter layer |
| vision | 13 | PARTIAL |
| voice | 12 | MISLEADING-LEANING — enum self-assertions; all 6 c20 files pin a deleted worktree path |
| projections | 11 | PARTIAL — registration/consumption only; **zero files reference inheritance** |
| cockpit-api | 10 | MISLEADING-LEANING — path-string membership and route counts, no schema/status/auth assertions |
| node-mesh | 10 | PARTIAL + MISLEADING — dispatch "contract test" re-implements the chain in the test body |
| primitives-types | 6 | STRONG (type registry + divergence blocking) |
| sprint-hardening | 5 | STRONG-ish |
| work-packets | 5 | PARTIAL |
| infra | 2 | — |

**Broken collection:** `tests/test_execution_coordinator.py:15` (`ExecutionMode` gone), `tests/test_c23b_production_benchmarks.py` (`OutcomeRecord` gone), `tests/test_c31_phase6.py` (`SessionStatus` gone). Runtime-broken beyond collection: 4 files import deleted `scripts/run_c39/c40a/c40b_*` modules and a nonexistent `jarvis_readiness_gate`. Environment rot: 29 files pin `sys.path` to deleted worktrees; 155 hardcode `/opt/OS` at index 0 — tests executed in any worktree silently import main-repo code (shadowing hazard documented in `tests/test_convergence_acceptance.py:8-12`).

**Misleading-test patterns:** enum-literal self-assertions (`tests/test_governed_execution_runtime.py:23-58`); 11 files asserting on `inspect.getsource` strings (break on refactor, pass on behavior change); in-test re-implementation of the system under test (`tests/test_mesh_dispatch_contract.py:21-45`); route contracts as path strings + counts (`tests/test_governance_routes.py:27-40` asserts `len(router.routes) == 7`); canon certification that goes green by mass skip (94 skips in `tests/test_phase14_6b_creatoros_lossless_canon.py` when the artifacts it certifies are absent); the legacy ungoverned spine pinned as current by `tests/test_spine_full.py`.

**Missing acceptance tests, by convergence-critical concern:** governed-mutation compliance — NO (WP-P6-005); projection inheritance — NO, zero grep hits (WP-P6-006); ontology layer separation beyond import direction — PARTIAL-NO (WP-P6-011); node trust / permission envelope — NO, `PermissionEnvelope` appears in zero test or substrate files (WP-P6-007); HTTP-level cockpit contract tests — WEAK (WP-P6-008); rollback/reversibility — WEAK; suite health itself — NO CI (WP-P6-004). Immediate remediation: restore collection (WP-P0-011), centralize path setup (WP-P6-001/002), marker taxonomy separating living contract tests from retired campaign pins (WP-P6-003).

---

## 13. Risk Register

Top 20 risks, ranked. Likelihood = probability the failure mode occurs (or is already occurring) under current operations; impact = damage when it does; blast radius = scope of affected state. Mitigation = closing packet in [UMH_WORK_PACKET_BACKLOG.md](UMH_WORK_PACKET_BACKLOG.md).

| # | Risk | Likelihood | Impact | Blast radius | Mitigation |
|---|---|---|---|---|---|
| 1 | Daemon outage silently degrades all 360 governed mutation sites to ungoverned direct execution (`completed_ungoverned`) | High (any daemon restart) | Critical | Every mutation route: filesystem, SSH remote writes, signal intake | WP-P0-001 |
| 2 | Mesh relay `/dispatch` reachable with no auth when `UMH_MESH_RELAY_SECRET` unset → arbitrary remote shell/desktop actuation on connected nodes | Medium (one env-var regression) | Critical | Any connected runtime node | WP-P0-002 |
| 3 | Caller-declared risk class + deny-pattern-free executor shell adapter → destructive commands pass node governance at default caps | High (structural, exercised on every dispatch) | Critical | Executor node filesystem/OS | WP-P0-003 |
| 4 | Two silently broken governed paths (create_from_intent, update_status) mean the DO layer creates no packets and operator approve/reject fails — governance theater | Certain (broken today) | High | Work-packet lifecycle integrity | WP-P0-007 |
| 5 | Nightly autonomous write-enabled Claude agent on the production repo outside all governance | Certain (cron fires nightly) | High | Production repo + shell | WP-P0-005 |
| 6 | Unauthenticated 0.0.0.0 webhook receiver carrying MFA codes and CC-session control (second approval channel) | Medium | High | Operator session + MFA relay | WP-P0-004 |
| 7 | EOS cross-tenant task read (`user_id` accepted, never bound) — any tenant's tasks readable | Certain under multi-tenant use | Critical | L3 tenant isolation | WP-P0-010 |
| 8 | Approval fragmentation (4 machines / 3 channels / 11 surfaces): a decision recorded in one store is invisible in others; operator cannot know the pending-decision authority | Certain (structural) | High | Permission-envelope integrity across the platform | WP-P1-007, WP-P5-004 |
| 9 | Effect-free TS governed bridge records proof artifacts for mutations that never execute — proof integrity broken if the Hono stack is ever deployed | Low (dormant) / Certain if deployed | High | All 33 TS mutations; trust in proof artifacts generally | WP-P1-005, WP-P2-022 |
| 10 | Cron plane mutates Neon/Notion/calendar directly every 5–15 min with zero policy gating, incl. LLM-decided external calendar responses | Certain (running today) | Medium-High | External third-party-visible state + Neon | WP-P1-010, WP-P0-005 |
| 11 | Type divergence accumulates invisibly: gate is staged-only, full scan fails today (46 BLOCKED), registry omits the most-fragmented primitives | Certain | High | Metamodel integrity; every downstream consumer | WP-P2-001, WP-P2-003, WP-P6-014 |
| 12 | Rival spines carry live traffic (legacy sync ExecutionSpine in the deployed Discord path; conditional governance "when bridge is active, else direct") | Certain | High | Discord-originated mutations, memory writes | WP-P1-001, WP-P1-006 |
| 13 | No StateCommit / unified commit log: applied changes are unattributable and irreversible at platform level; fail-open path leaves no record at all | Certain (structural) | High | Rollback + audit capability platform-wide | WP-P1-013 |
| 14 | Silent trace/feedback loss (except-pass on persist) + dual unreconciled trace stores → evidence gaps precisely during incidents | Medium-High | Medium-High | Trace/evaluation evidence tier | WP-P0-009, WP-P1-015 |
| 15 | No emergency stop, cancellation, or rollback for in-flight remote actuation; timeout is the only bound | Medium | High | Executor nodes during runaway actuation | WP-P1-020, WP-P2-030, WP-P4-002 |
| 16 | Test suite cannot collect, no CI, and misleading suites (mass-skip certification, getsource assertions) create false confidence during the convergence itself | Certain | High | Every convergence packet's verification step | WP-P0-011, WP-P6-004, WP-P6-009, WP-P6-010 |
| 17 | Credential sprawl: credential gate enforced at 1 call site; raw env/plaintext .env credentials in adapters and node daemon; product tables hold raw OAuth tokens; static vision token shipped in the public JS bundle | High | High | External accounts (Google, Notion, Tailscale, Stripe-adjacent), camera/vision channel | WP-P0-013, WP-P3-020, WP-P6-017 |
| 18 | Ungoverned client-side write paths: Electron IPC fs:writeFile, raw-fetch panel mutations, unauthenticated voice WS | Medium | Medium-High | Desktop filesystem; cockpit mutation surface | WP-P0-012, WP-P0-013, WP-P0-014 |
| 19 | Conference-rooms state authority on unlocked flat JSON with silent data-loss masking; command-runtime JSONL rewritten non-atomically (crash corrupts command state) | Medium | Medium | Rooms domain + command history state | WP-P1-019, WP-P1-009 |
| 20 | Convergence-execution risk: 149 packets touching core infra without the acceptance-test scaffolding in place → regressions ship undetected mid-migration | Medium | High | The convergence program itself | Sequencing (P0 test packets first; WP-P6-005…008 before spine/type migrations complete), §14 No-Go list |

---

## 14. No-Go List

Actions that must NOT be taken during convergence. Each is either a repo law, a lesson already paid for, or a direct consequence of the evidence above.

1. **No delete/move sprees.** Every dormant module gets a recorded disposition (PROMOTE / MERGE / ISOLATE / ARCHIVE / DELETE) before removal — 33 dormant workstation engines, 7 dormant L4 grounding runtimes, ~40 dev-visibility cockpit store/panel/route triples, the dormant Hono stack. Dormant ≠ dead: several dormant modules (source_truth_runtime, correspondence_scheduler) are the intended future owners of their concern.
2. **No big-bang rewrites.** The governed spine, the integration contract, and the Meta IDE verification primitives are sound and reused — convergence declares owners and migrates callers; it does not rebuild. The backlog is deliberately 149 bounded packets with per-packet rollback plans, not a rewrite plan.
3. **No ungoverned migration scripts.** Convergence work itself mutates state (registries, JSONL stores, DB schemas); migration steps route through governed mutation or land as reviewed commits with rollback plans — never as ad-hoc scripts run against production data. Schema-bearing packets (WP-P0-010, WP-P1-019, WP-P3-009, WP-P3-011, WP-P4-009, WP-P5-017) carry CRITICAL migration discipline: row counts checked before, versioned migrations, no destructive DDL without backup.
4. **No touching frozen PLATFORM_SPEC contracts without RFC.** PLATFORM_SPEC.md is frozen (v1.0.0); architectural contract changes require the Breaking Change Process (RFC + migration + regression qualification). Several packets adjust what the spec *describes* (e.g., correcting the governed_mutation location claim) — description corrections are documentation; contract changes are RFCs.
5. **No cockpit deploys outside `bash cockpit/deploy.sh`.** Never raw `flyctl deploy` — the gate exists because a worktree deploy shipped without API-key injection and broke every cockpit API call.
6. **No raw `subprocess` in gated directories.** CPU Gate Law: `gated_subprocess_run()`/`gated_popen()` only, in substrate/, adapters/, transports/, services/. Note `nodes/` is currently outside GATED_DIRS — extending coverage is a packet (WP-P6-014 scope); do not use its absence as license.
7. **No disabling or grandfathering-around enforcement gates to make packets pass.** The stale-exemption pattern is itself a finding (~55 stale grandfather entries, 17-module LEGACY_DUPLICATES with no burn-down). Exemption lists only shrink; new violations fail.
8. **No new parallel implementations during convergence.** No new approval store, work-packet type, node model, canvas store, event bus, or API entrypoint for any reason — including "temporary" migration shims that outlive their packet. Every packet that introduces a bridge names its removal milestone.
9. **No deleting or rewriting plan files, and no worktree/branch debris.** Plans are immutable (archive, then re-plan); worktrees are removed after merge; test files must not pin worktree paths (that is how 29 tests died).
10. **No production restarts of all services simultaneously; no Docker rebuilds for Python-only changes.** Per-service restart with clean-startup log verification after each packet that touches services/.
11. **No instance context added to platform files while removing it elsewhere.** Convergence removes founder/device/venture literals from substrate and shipped artifacts (WP-P3-016, WP-P5-018, WP-P6-020); packets must not introduce new ones — names come from BIS/env/registries at runtime.
12. **No trusting subagent or point-in-time proof claims during verification.** Phase-doc proof claims (85/85 tests etc.) are doc claims, not runtime truth; every packet's acceptance criteria are re-verified against the actual tree, and "done" claims require an independent measurement (the audit's own inventory protocol).
13. **No physical-actuation capability work of any kind** until the safety-envelope/e-stop/rollback contract exists (WP-P2-030 before any PHYSICAL_WORLD adapter; RoboticsOS/SecurityOS remain unscheduled).
14. **No deploying the dormant surfaces "because they exist."** The Hono TS stack (effect-free mutations), the dormant unauthenticated services (goal_api, higgsfield_webhook, local_bridge_server), and the CreatorOS/LyfeOS shells stay down until their packets wire or retire them — a `python3` invocation away from live is the risk, not the feature.

---

## 15. Recommended Convergence Phases

Aligned exactly with [UMH_WORK_PACKET_BACKLOG.md](UMH_WORK_PACKET_BACKLOG.md) (149 packets; per-phase waves and the full dependency graph live there). Keystone critical path: WP-P0-001 → WP-P1-001 → WP-P1-007 → {WP-P2-001, WP-P2-002} → WP-P3-004 → WP-P4-004 → WP-P5-005.

**P0 — Safety-critical: stop the bleeding (15 packets).** Close the fail-open trust boundaries and the defects that corrupt or bypass governance today: fail-close `governed_mutation()` and move the choke point below the transport layer; close the mesh trust boundary (relay + WS auth, token→node binding); node-side risk derivation and deny-by-default config; authenticate the webhook receiver, voice WS, and Electron IPC writes; fix the two silently broken governed paths; close the cross-tenant read; restore pytest collection; decompose the nightly autonomous cron. *Entry:* none — start immediately; wave 1 is 13 independent packets. *Exit:* every control-plane entry point fails closed; broken governed paths work; collection green; no unauthenticated mutation surface (HTTP, WS, IPC, mesh, webhook) reachable. *Unblocks:* everything — P1 assumes fail-closed boundaries; P6 test-infra packets may start once WP-P0-011 lands.

**P1 — Spine convergence (21 packets).** One canonical governed operation runtime and one mutation-submission entry; retire rival spines/pipelines/event backbones; migrate the live Discord path; one approval authority (canonical ApprovalRequest, typed port, single pending-work store); govern the cron plane via signal submission and the workcell/CommandRuntime paths via envelopes; durable operation queues; land StateCommit, unified PolicyDecision, trace-store authority, typed ProofContract/proof envelope; declare one operator-intent kernel. *Entry:* P0 complete (specifically WP-P0-001, WP-P0-004). *Exit:* a single documented submission entry enforced by an architecture test; every mutation path routes through it or carries a recorded exemption; approvals in one auditable store; pending work survives restarts. *Unblocks:* P2 primitive convergence (canonical runtime declared) and P5 wave 1 (client approval work may begin once WP-P1-007 merges).

**P2 — Primitive / type convergence (30 packets).** One canonical definition per platform primitive: risk taxonomy, WorkPacket, Signal, Intent, RuntimeNode, RuntimeSession, AgentRole/AgentInstance, MemoryCandidate, EvaluationResult, Capability, ExecutionStep, ToolCall; the registry gate hardened (symbol-resolution validation, LEGACY_DUPLICATES burn-down) and driven to full-scan green; one adapter contract and one capability registry; dormant runtime stacks (workstation generations, presence, voice, dual API surfaces) dispositioned. *Entry:* WP-P1-001 declared; WP-P0-011 green. *Exit:* `check_type_divergence.py --all` exits 0; registry covers all public platform types; each contested primitive has exactly one registered owner; dormant stacks have recorded dispositions. *Unblocks:* P3 (layer separation presupposes canonical types to relocate).

**P3 — Ontology / metamodel separation (20 packets).** Enforce the four-layer separation: extend the layer contract to nodes/, umh/, cockpit/ and remove the ghost saas/ layer; move L3 entities and doctrine out of substrate; one projection concept (canonical IDs, single port, converged registration); L1 external-entity model (people/orgs/customers); unified StateAuthority; versioned writeback schema (`umh_status`/`umh_outcomes`) with migrations; L4 entity-resolution contract and registry; invert the substrate→projections import; consolidate OAuth tokens into the platform credential path. *Entry:* WP-P2-001/002 landed; WP-P3-001 first within the phase. *Exit:* no upward imports (gates green, exemptions burned down); no projection/instance literals in substrate; declared state authorities for reality/world models, outcomes, sources of truth; versioned schema artifacts for every write path. *Unblocks:* P4 (registration/port + writeback contracts are what projections activate against).

**P4 — Projection capability build-out (20 packets).** Activate projection surfaces on the converged contracts: manifest-driven registration + generic poller (activate CreatorOS, LyfeOS, Broadcast, or classify DORMANT); repair or retire the broken nightly scrape→ICP→KPI chain; reduce services/ to thin entrypoints; generalized actuation maturity with a blocking human-confirmation gate, e-stop, and rollback; governed payments and social-publishing adapters; the EOS approval-loop bridge into the UMH approval authority; the governed continuity loop; broadcast audio/capture/egress; scope-decision records for absent domain models. *Entry:* WP-P3-004/013 and WP-P3-009 landed. *Exit:* every projection wired end-to-end (poll → signal → handler → outcome) or explicitly dormant; every externally visible actuation behind governed mutation with approval and proof. *Unblocks:* P5's projection-facing views have real data contracts to render.

**P5 — Cockpit convergence (19 packets).** Make the client a faithful projection of the control plane: five-surface information architecture in routes.ts with structural absorption and orphan resolution; one approval queue and decide path client-wide; the domain-store layer replacing per-panel stores, the god store, and the canvas-store septuplet; a single cache-invalidation/polling policy; one Operations work anchor, one Command strategy view, one continuity view, one node-topology view, one trace stream, one capability view; fix the Electron production binding; harden push; remove instance-context literals from shipped artifacts; align CLI identity with the platform identity model. *Entry:* WP-P1-007 and WP-P2-010 landed — P5 consumes server contracts, never produces them. Layout lock applies: IA and state-layer changes only. *Exit:* one client owner per control-plane object family; a decision made on any surface visible on all; zero raw-fetch bypasses; every registered panel reachable or dispositioned; all deploys via `bash cockpit/deploy.sh`.

**P6 — Test / certification hardening (24 packets).** Make the guarantees mechanical: centralized test path setup; CI executing the suite on every push; marker taxonomy and retired-campaign triage; acceptance tests for governed-mutation compliance, projection inheritance, node trust/permission envelopes, ontology layer separation, and HTTP-level cockpit contracts; honest certification (fail loudly instead of mass-skip; CI-runnable contract layer split from environment-gated live layer); scheduled full-scan sweeps of all check gates; residual hygiene (credential gate at every authenticated actuation, SSH host-key pinning, instance-leak removal, doc-truth reconciliation, cross-host broadcast egress proof). *Entry:* WP-P6-001…004 start as soon as WP-P0-011 lands and run in parallel with P2–P5; enforcement sweeps require P2/P3 gates green. *Exit:* CI on every push; all `check_*.py --all` green; certification repeatable and environment-gated; no stale doc contradicting observed deployment reality.

---

## 16. Final Gap Ledger

All 270 gap candidates from the Phase-1 index, grouped by severity, one line each with the closing work packet. Mapping is mechanically verified against [UMH_WORK_PACKET_BACKLOG.md](UMH_WORK_PACKET_BACKLOG.md) (each gap closes in exactly one packet; titles truncated to one line). Severity totals: 23 critical / 87 high / 112 medium / 48 low.

### Critical (23)

| Gap | Summary | Packet |
|---|---|---|
| GAP-A-004 | Four parallel API entrypoints; deployed surface (services/operator_api.py :8091) contradicts ARCHITECTURE.md 'one… | WP-P1-001 |
| GAP-B1-001 | WorkPacket rename campaign left control-plane router v1 and node packet validator broken at import time (verified… | WP-P0-008 |
| GAP-B2-001 | WorkPacket fragmented across 4 definitions with runtime alias-and-convert shim in primary loop | WP-P2-005 |
| GAP-B3-001 | governed_mutation() fail-open: ungoverned direct execution when organism not running | WP-P0-001 |
| GAP-B4-001 | Capability primitive fragmented across 58 class definitions with no joining record | WP-P2-018 |
| GAP-B4-007 | Projection homonym: forecast owns canonical name; product projection split across 4+ registration mechanisms | WP-P3-004 |
| GAP-C1-001 | GovernedWorkRuntime.submit_work calls nonexistent WorkPacketEngine.create_from_intent — packet creation always fai… | WP-P0-007 |
| GAP-C1-002 | CommandRuntime packet approval broken — UniversalWorkQueue.update_status does not exist | WP-P0-007 |
| GAP-C2-001 | governed_mutation() fails open to ungoverned direct execution when organism daemon is down | WP-P0-001 |
| GAP-C2-002 | TS governed bridge records mutations without executing them (proof artifacts assert effects that never happened) | WP-P1-005 |
| GAP-C2-004 | Remote terminal HTTP endpoints bypass the spine entirely (arbitrary remote shell input) | WP-P0-002 |
| GAP-C3-001 | Node mesh HTTP /dispatch fail-open when UMH_MESH_RELAY_SECRET unset — unauthenticated remote node actuation | WP-P0-002 |
| GAP-D2-001 | EOS task polling ignores tenant scope — cross-tenant read in data plane | WP-P0-010 |
| GAP-E1-003 | Four parallel identity stores with no identity bridge or entity resolution | WP-P3-011 |
| GAP-E2-001 | Four rival operator-intent kernels with no declared state authority | WP-P1-017 |
| GAP-F1-002 | Approval concern fragmented across 11 surfaces and >=4 endpoint families - no state authority for decisions | WP-P5-004 |
| GAP-F2-001 | Approval state fragmented across >=9 stores and >=9 backend approval endpoint families | WP-P5-004 |
| GAP-G-001 | Mesh authentication fails open and never binds token to node identity | WP-P0-002 |
| GAP-G-002 | HTTP relay /dispatch auth optional; arbitrary remote execution when UMH_MESH_RELAY_SECRET unset | WP-P0-002 |
| GAP-G-003 | Risk class of remote execution caller-declared/defaulted; executor shell has no deny patterns | WP-P0-003 |
| GAP-G-004 | Mesh dispatch bypasses governed spine; workpacket execution gate unwired to dispatch paths | WP-P0-002 |
| GAP-H-001 | Full-suite pytest collection broken: 3 stale-symbol ImportErrors interrupt collection of 15,017 tests | WP-P0-011 |
| GAP-H-002 | No governed-mutation compliance acceptance test enforcing 'all state changes through governed_mutation()' | WP-P6-005 |

### High (87)

| Gap | Summary | Packet |
|---|---|---|
| GAP-A-001 | Ghost saas/ layer legislated by architecture-layers.md and enforcement gates; its responsibilities scattered acros… | WP-P3-002 |
| GAP-A-002 | transports/ -> services/ upward imports (daemon singletons) with no checker rule | WP-P2-021 |
| GAP-A-003 | nodes/, umh/, cockpit/ absent from layer contract; substrate imports nodes/ uncovered by any rule | WP-P3-001 |
| GAP-A-005 | Type coherence gate fails full scan: 46 BLOCKED divergences incl. substrate/contracts/agent_types.py:87 | WP-P2-003 |
| GAP-A-006 | All enforcement gates staged-only; no full-scan CI, drift accumulates invisibly | WP-P6-014 |
| GAP-A-008 | Conditional governance: CognitiveLoop executes direct when governed spine bridge inactive, vs PLATFORM_SPEC 'no ex… | WP-P1-006 |
| GAP-B1-002 | DesiredState primitive does not exist as a type — free text, dicts, and ungoverned JSON canons only | WP-P2-006 |
| GAP-B1-003 | Two universal intake types (SignalEnvelope vs Signal) with two rival signal routers | WP-P1-011 |
| GAP-B1-004 | Ten same-name class/enum collisions across the six primitives, unregistered in canonical_types.py | WP-P2-002 |
| GAP-B1-008 | governed_mutation() lives in transports/ and silently degrades to ungoverned direct execution when daemon is down | WP-P0-001 |
| GAP-B1-010 | Rival execution spines split the Operation data plane — governed and ungoverned run concurrently | WP-P1-001 |
| GAP-B2-002 | canonical_types.py registers non-existent EnvironmentPacket* names; rule doc cites a third naming | WP-P0-008 |
| GAP-B2-003 | Two identically-named RuntimeSession classes with disjoint schemas; neither registered | WP-P2-009 |
| GAP-B2-004 | Node identity fragmented: 4 node models + 2 JSON registries with different ID schemes | WP-P2-010 |
| GAP-B2-005 | Two incompatible adapter contracts; AdapterRequest lacks governance/trace fields and is unregistered | WP-P2-011 |
| GAP-B2-006 | Governed mutation path and WorkPacket pipeline are disjoint execution routes | WP-P1-001 |
| GAP-B3-002 | ApprovalRequest fragmented: 4 typed schemas + 2 untyped dict stores, no canonical type | WP-P1-007 |
| GAP-B3-003 | Two same-name ProofPackage classes with incompatible schemas | WP-P1-016 |
| GAP-B3-004 | MemoryCandidate defined 4x with divergent schemas and status enums, zero canonical registration | WP-P2-016 |
| GAP-B3-005 | No StateCommit primitive; four disjoint ledgers; no unified commit log | WP-P1-013 |
| GAP-B3-006 | Quality governance fails open on exception (passed=True) | WP-P0-009 |
| GAP-B4-002 | capability_router (28-capability enum + provider chains) dormant — test imports only | WP-P2-018 |
| GAP-B4-008 | Two parallel projection ports (sockets vs organism) with same name, unrelated contracts | WP-P3-004 |
| GAP-B4-010 | L3 domain entities (Company/Department/Portfolio) defined inside L2 substrate/types.py | WP-P3-005 |
| GAP-B4-011 | No L1 model for people/orgs/customers; world_model.py is a misnamed self-model | WP-P3-006 |
| GAP-B4-012 | EntityResolution fragmented: three unlinked mechanisms, no cross-source resolution | WP-P3-011 |
| GAP-C1-003 | governed_mutation ungoverned fallback executes mutations without policy when organism daemon is down | WP-P0-001 |
| GAP-C1-004 | Four parallel approval/execution state machines with no single state authority | WP-P1-007 |
| GAP-C1-005 | Workcell protocol + daemon execute arbitrary prompts via RuntimeAdapter with zero governance | WP-P1-008 |
| GAP-C1-006 | Legacy sync ExecutionSpine still live in production Discord services despite deprecation note | WP-P1-006 |
| GAP-C2-003 | Five unregistered mutation names -> endpoints rejected when governed, executed when ungoverned | WP-P1-002 |
| GAP-C2-005 | Operator-loop delegated handler libraries form a parallel governance system (execcoord/executor/agent/approval) | WP-P1-007 |
| GAP-C2-006 | Risk-classification collapse: state_mutate catch-all on 159 call sites incl. kill/signal/pipeline | WP-P1-003 |
| GAP-C3-002 | Node trusts caller-declared risk_class; governance_verdict_id transmitted but never validated on node | WP-P0-003 |
| GAP-C3-003 | External mutations (email send, calendar create) execute outside governed_mutation; only bookkeeping is governed | WP-P1-010 |
| GAP-C3-004 | Nightly cron runs autonomous write-enabled claude -p agent outside all governance; alert import broken | WP-P0-005 |
| GAP-C3-005 | cc_webhook_receiver on 0.0.0.0:8765 with zero auth carries MFA codes and CC permission approvals into tmux | WP-P0-004 |
| GAP-C3-006 | Cron layer mutates Neon + Notion directly every 5-15 min with no governed_mutation, trace, or proof artifact | WP-P1-010 |
| GAP-C3-007 | LLM-assisted auto-accept/decline of external calendar invites from cron with no approval envelope or proof artifact | WP-P1-010 |
| GAP-D1-001 | Duplicate primitive ontology type system (types.py vs primitive_decomposition_v1.py) registered as permanent legac… | WP-P2-004 |
| GAP-D1-002 | EOS business advice library (PRIMITIVE_LIBRARY, STAGE_PRIMITIVES) masquerading as 'ontology primitives' in substra… | WP-P3-015 |
| GAP-D1-003 | CreatorOS/LyfeOS/EOS domain bridge content hardcoded in substrate/understanding/domains with pre-commit checker ex… | WP-P3-015 |
| GAP-D1-005 | Exact class-name collision: two unrelated RealityIntelligenceEngine implementations; only one registered in canoni… | WP-P2-002 |
| GAP-D1-006 | Five overlapping world/reality-model homes with no declared per-layer responsibility boundary | WP-P3-003 |
| GAP-D2-002 | Writeback schema (umh_status, umh_outcomes) has no source of truth in repo | WP-P3-009 |
| GAP-D2-003 | Two hand-maintained sources of L3 domain truth with no drift check | WP-P3-010 |
| GAP-D2-004 | substrate imports from projections; Product enum hardcodes L3 names in L2 | WP-P3-013 |
| GAP-D2-005 | No cross-projection entity resolution for persons/orgs | WP-P3-011 |
| GAP-D2-006 | EOS L3 domain types defined in substrate/types.py (L2 metamodel) | WP-P3-005 |
| GAP-D2-007 | CreatorOS and LyfeOS integrations are shells with no runtime path (no poller, no registration) | WP-P4-005 |
| GAP-E1-001 | CreatorOS and LyfeOS integrations dormant: no poller, no runtime registration | WP-P4-004 |
| GAP-E1-002 | umh_status/umh_outcomes writeback undeclared in product Drizzle schemas (drift) | WP-P3-009 |
| GAP-E1-005 | Two unlinked approval systems (EOS agent_actions vs UMH approvals/approval_port) | WP-P4-009 |
| GAP-E1-006 | Commerce/payments capability is enum stub; CreatorOS revenue and LyfeOS Stripe need governed adapter | WP-P4-013 |
| GAP-E1-007 | OAuth token storage triplicated outside the credential gate | WP-P3-020 |
| GAP-E1-008 | LyfeOS ~35-table domain surface vs 3 polled tables + 3 capabilities (largest projection gap) | WP-P4-010 |
| GAP-E1-012 | substrate imports projections by name (dependency-direction violation) | WP-P3-013 |
| GAP-E2-002 | Voice fragmented across 3 stacks; real-microphone E2E never closed | WP-P2-027 |
| GAP-E2-003 | saas-dev-skill is a parallel ungoverned agentic execution system | WP-P0-015 |
| GAP-E2-004 | Mesh dispatch hardcodes single executor node + Windows paths in platform layer | WP-P1-018 |
| GAP-E3-001 | Broadcast agent capability surface never registered with IntegrationRegistry at boot (only Notion is) | WP-P4-004 |
| GAP-E3-002 | Broadcast audio pipeline absent — all streams carry anullsrc silence; spike-proven mechanics unbuilt | WP-P4-017 |
| GAP-E3-003 | No real capture or hardware encode; Windows node adapter reuses VPS libx264 arg builder | WP-P4-018 |
| GAP-E3-005 | Conference rooms state authority is unlocked flat JSON files with silent corruption masking | WP-P1-019 |
| GAP-E3-007 | PhysicalAdapterRegistry dormant (zero dependents) and execute() bypasses governed_mutation despite docstring gover… | WP-P1-020 |
| GAP-E3-008 | No physical safety envelope, emergency-stop, or rollback primitive — kill switch is agent-recursion scoped only | WP-P2-030 |
| GAP-F1-001 | 7 registered panels unreachable: executive, governance, learning, prediction, skills, tasks, workintelligence | WP-P5-003 |
| GAP-F1-003 | Work-packet/execution concern rendered by 12 panels over >=3 endpoint families | WP-P5-007 |
| GAP-F1-004 | Five-surface model not expressed in routes.ts taxonomy; 60 panels form one flat [DEV] list | WP-P5-003 |
| GAP-F1-005 | One-store-per-panel architecture: 77 stores, no shared domain model layer | WP-P5-005 |
| GAP-F1-012 | SessionPanel and ProfilePanel raw-fetch /api/umh bypassing authenticated api/client | WP-P0-012 |
| GAP-F2-002 | No cache-invalidation strategy for ~60 fetch-based stores; WS invalidation covers 4 domains only | WP-P5-006 |
| GAP-F2-003 | chatStore /chat/upload raw fetch without Authorization fails against Clerk-guarded router | WP-P0-012 |
| GAP-F2-004 | 148 direct fetchApi calls in 37 panels/components bypass the store layer incl. mutation POSTs | WP-P5-005 |
| GAP-F2-005 | Electron production surface has broken API/WS binding (file:// origin, relative API_BASE, host-derived WS URLs) | WP-P5-016 |
| GAP-F2-006 | Voice WS unauthenticated; Vision WS ships static VITE_VISION_TOKEN in public bundle | WP-P0-013 |
| GAP-F2-007 | Electron IPC fs:writeFile grants ungoverned filesystem writes (HTTP equivalent is governed) | WP-P0-014 |
| GAP-G-005 | No canonical RuntimeNode: five node models, three role vocabularies, fragile ID joins | WP-P2-010 |
| GAP-G-006 | Adapter contract fictional: 1/100 files implement adapters/protocol.py; >=6 parallel contracts | WP-P2-011 |
| GAP-G-007 | Credential gate enforced at exactly one call site; adapters use raw env credentials | WP-P6-017 |
| GAP-G-008 | No emergency stop or cancellation for in-flight remote execution | WP-P4-002 |
| GAP-G-009 | No rollback/compensation model in adapter or actuation path; side_effects never consumed | WP-P4-002 |
| GAP-G-010 | Node capability declarations unattested and unbounded by registered role | WP-P0-003 |
| GAP-H-003 | 29 tests pin deleted worktree sys.paths; 155 hardcode /opt/OS so worktree runs test wrong code | WP-P6-001 |
| GAP-H-004 | No CI executes the test suite (only mobile-build.yml workflow exists) | WP-P6-004 |
| GAP-H-005 | No projection inheritance acceptance tests (zero test files mention inheritance) | WP-P6-006 |
| GAP-H-006 | No node-trust / permission-envelope tests; mesh dispatch contract tested against an in-test simulation | WP-P6-007 |

### Medium (112)

| Gap | Summary | Packet |
|---|---|---|
| GAP-A-007 | Dependency checker grandfather list ~55 entries stale (56 claimed substrate->adapters violators, 1 real) — regress… | WP-P6-014 |
| GAP-A-009 | Deployed Discord service uses rival event spine (execution/bridge/event_spine.py) instead of canonical organism/ev… | WP-P1-001 |
| GAP-A-011 | Projection name leak live in substrate: EntrepreneurOSGateway alias (gateway.py:1946) imported by deployed bot; ga… | WP-P3-002 |
| GAP-A-012 | services/ contains business logic + mutable JSON state, violating 'deployment entrypoints only' contract | WP-P4-003 |
| GAP-A-013 | Dead duplicate entrypoint transports/api/operator.py (601L, NameError at import: os used before import) | WP-P2-022 |
| GAP-A-014 | Cross-entrypoint singleton coupling: discord handlers import _organism from undeployed transports/api/app.py with… | WP-P2-022 |
| GAP-B1-005 | Intent object model fragmented across four parallel lifecycles (CanonicalIntent, IntentContract, types.Intent, Eng… | WP-P2-008 |
| GAP-B1-006 | CurrentState has no unifying entity-state record; five reconcilers emit private report shapes | WP-P2-007 |
| GAP-B1-007 | Canonical Gap carries free-text state deltas and no closure linkage to the resolving Operation | WP-P2-006 |
| GAP-B1-009 | Four WorkPacket variants with no mapping contract between them | WP-P2-005 |
| GAP-B1-011 | canonical_types.py registry omits substrate/types.py's own contested types and all reality_model types | WP-P2-001 |
| GAP-B2-007 | ExecutionStep primitive missing; >=9 unshared step types; spine stages are strings/comments | WP-P2-012 |
| GAP-B2-008 | ToolCall primitive missing; model adapter layer has no tool-use support | WP-P2-013 |
| GAP-B2-009 | AgentRole fragmented across 4+ role models with 4 permission vocabularies | WP-P2-014 |
| GAP-B2-010 | AgentInstance missing — running-agent identity split across 3 record types with no join key | WP-P2-015 |
| GAP-B2-011 | WorkPacketExecutionGate v1 has zero test coverage | WP-P6-013 |
| GAP-B2-012 | RuntimeSessionRegistry v1 untested | WP-P6-013 |
| GAP-B3-007 | ProofContract has no typed artifact — stage enum + string lists only | WP-P1-016 |
| GAP-B3-008 | No canonical EvaluationResult; 12+ scattered score types; DimensionScore triplicated | WP-P2-017 |
| GAP-B3-009 | Trace name collision + dual trace persistence (Neon vs JSONL) with no reconciliation | WP-P1-015 |
| GAP-B3-010 | Silent except-pass in trace and feedback Neon persistence — observability loss invisible | WP-P0-009 |
| GAP-B3-011 | PolicyDecision envelope split with divergent executability semantics for CONDITIONAL | WP-P1-014 |
| GAP-B4-003 | CapabilityPathway primitive missing — no governed intent-to-execution route object | WP-P2-019 |
| GAP-B4-004 | CapabilityRevision missing — no versioning of capability definitions | WP-P2-019 |
| GAP-B4-005 | template_registry.py's 12 types absent from canonical_types.py divergence registry | WP-P2-020 |
| GAP-B4-006 | Unregistered CapabilityName enum duplicates capability naming semantics | WP-P2-018 |
| GAP-B4-009 | ProjectionName enum cannot represent EOS/CreatorOS/LyfeOS | WP-P3-004 |
| GAP-B4-013 | DomainBridge unregistered in canonical_types; rival organism/domain_registry.py dormant | WP-P3-014 |
| GAP-B4-014 | StateAuthority domain-coarse, static, disconnected from SourceCanonicality/authority_tier taxonomies | WP-P3-007 |
| GAP-C1-007 | Canonical-reality write side doors bypass CanonicalRealityWritePath validation and trust gate | WP-P3-008 |
| GAP-C1-008 | WorkloadRunner governed-spine wiring is dead code — default run_workload bypasses spine | WP-P1-008 |
| GAP-C1-009 | CanonicalRealityWritePath does not invoke the policy engine (caller's responsibility) | WP-P3-008 |
| GAP-C1-010 | Name collisions across mutation core: two Workcell classes, two WorkloadType enums, three ExecutionSpine classes,… | WP-P2-002 |
| GAP-C1-011 | CommandRuntime mutation routes execute directly on subsystems without envelopes, incl. private-attribute reach-in | WP-P1-009 |
| GAP-C1-014 | Test gap: gate-3 suite never exercises submit_work, leaving GAP-C1-001 uncaught | WP-P0-007 |
| GAP-C1-015 | Spine idempotency map unbounded; mutation-registry validation optional for direct spine.submit without mutation_na… | WP-P1-009 |
| GAP-C1-016 | CommandHistory.update_status rewrites JSONL non-atomically — crash corrupts command state authority | WP-P1-009 |
| GAP-C1-018 | ConcreteExecutionSpine performs mandatory ungoverned memory writes on every signal | WP-P1-001 |
| GAP-C2-007 | Ungoverned autonomous-lane control endpoints (cadence set-mode direct attribute write, cleanup, run) | WP-P1-004 |
| GAP-C2-008 | Dead rival operator API module broken at import (duplicate of deployed operator_api.py) | WP-P2-022 |
| GAP-C2-010 | POST /organism/signal lacks operator-role check present on all sibling mutations | WP-P5-001 |
| GAP-C2-012 | Dormant Hono API duplicates the FastAPI write surface without deprecation marker | WP-P2-022 |
| GAP-C2-014 | Settings mutation runtime is a third governance pipeline overlapping registered settings_update | WP-P5-002 |
| GAP-C3-008 | Three parallel approval systems with no shared store or unified audit | WP-P1-007 |
| GAP-C3-009 | Dual dispatch paths to identical node actuation: governed CapabilityRequest vs raw HTTP relay | WP-P0-002 |
| GAP-C3-010 | Credential Injection Law unenforced: validate_credential_source has one caller; creds cached as disk JSON | WP-P6-017 |
| GAP-C3-011 | nodes/ excluded from CPU gate enforcement despite law's all-nodes scope; raw subprocess throughout node adapters | WP-P3-001 |
| GAP-C3-012 | Broken nightly scrape chain still scheduled: apify_scraper.py and 03_CRM/01_Inbox do not exist | WP-P4-001 |
| GAP-C3-013 | Node shell allowlist checks only argv[0] and filesystem check is unnormalized startswith — bypassable envelope | WP-P0-003 |
| GAP-C3-014 | Unauthenticated dormant mutation services in tree (goal_api, higgsfield_webhook, local_bridge_server tmux injectio… | WP-P0-006 |
| GAP-D1-004 | Understanding world model seeds 'universal canonical' layer with EOS doctrine at 0.9+ confidence, bypassing promot… | WP-P3-016 |
| GAP-D1-007 | Instance-specific governance domains (music, clothing, real_estate, personal/LifeOS) hardcoded in organism/domain_… | WP-P3-016 |
| GAP-D1-008 | Two-deep re-export shim chain for laws/primitives/domains with private-symbol re-export and business-bridge asymme… | WP-P3-017 |
| GAP-D1-009 | Instance/projection content in understanding/reality market intelligence (LYFEOS advantages in prompt, lyfe_instit… | WP-P3-016 |
| GAP-D1-010 | 'Domain' is four unrelated concepts (observation tag, governance domain, bridge domain, StateDomain) with no share… | WP-P3-014 |
| GAP-D1-013 | No entity-resolution component in L4: RealityGraph entities, reality_model observations, and world-model entries a… | WP-P3-011 |
| GAP-D2-008 | Integration coverage thin: 5/15, 4/20, 4/35 tables observable per projection | WP-P4-006 |
| GAP-D2-009 | Four-way 'projection' terminology collision; shared data dir and id prefix | WP-P3-004 |
| GAP-D2-010 | Bulk of L4 grounding layer dormant — test-only dependents | WP-P4-007 |
| GAP-D2-011 | Semantic grounding is keyword-lookup V1 only, no evaluation/calibration | WP-P4-008 |
| GAP-D2-012 | LyfeOS/CreatorOS domain vocabularies hardcoded in substrate keyword maps | WP-P3-015 |
| GAP-D2-013 | EOS poller depends on Notion adapter's WatermarkStore | WP-P3-019 |
| GAP-D2-014 | entity_links table lacks DDL in repo; store has no read/query API | WP-P3-011 |
| GAP-E1-004 | Projection ID canon conflict: eos/entrepreneuros, cos/creatoros across registry, alias map, manifests | WP-P3-004 |
| GAP-E1-009 | CreatorOS community/social graph (communities, channels, DMs, followers) has zero UMH surface | WP-P4-011 |
| GAP-E1-010 | No canonical recurring-schedule engine to reconcile LyfeOS recurrence rules | WP-P2-028 |
| GAP-E1-011 | Product notification stores and FCM never reach substrate notification engine | WP-P4-012 |
| GAP-E1-013 | Duplicate WorkflowStep type in EOS projection vs substrate/types.py | WP-P2-023 |
| GAP-E1-014 | EOS bridge covers CRM slice only; tasks/agent_actions/metrics readers exist but unexposed | WP-P4-009 |
| GAP-E1-015 | Two same-named projection-port abstractions with different contracts | WP-P3-004 |
| GAP-E1-016 | Two umh_outcomes definitions (platform DB vs product DBs), no declared relationship | WP-P3-009 |
| GAP-E1-017 | No media asset management primitive; LyfeOS stores base64 file bodies in Postgres | WP-P2-029 |
| GAP-E1-019 | Cross-projection contact/person entity resolution missing (three unlinked contact tables) | WP-P3-011 |
| GAP-E1-020 | EOS organization model has no verified persistence/reconciliation path (UNVERIFIED) | WP-P4-015 |
| GAP-E1-021 | No external social publishing adapter despite SOCIAL_POST capability and CreatorOS create_post | WP-P4-014 |
| GAP-E2-005 | 5 overlapping presence modules + 4 route surfaces, no canonical authority | WP-P2-024 |
| GAP-E2-006 | Workstation runtime source of truth split across 3 code generations | WP-P2-025 |
| GAP-E2-007 | 33 dormant engines in workers/workstation/_dormant with no disposition record | WP-P2-025 |
| GAP-E2-008 | C20 voice tests hardcode deleted worktree absolute path | WP-P6-002 |
| GAP-E2-009 | Durable operations single-host filesystem-bound, no recovery SLO | WP-P1-021 |
| GAP-E2-010 | Push delivery silently disableable (optional pywebpush) and unproven | WP-P5-017 |
| GAP-E2-011 | Operator-experience doc layer stale — 3 docs cite deleted code | WP-P6-023 |
| GAP-E2-012 | Duplicate acceptance module families jarvis_* and operator_acceptance* coexist | WP-P2-026 |
| GAP-E2-013 | Cockpit route-satellite sprawl without a route registry contract | WP-P5-015 |
| GAP-E2-017 | Non-optional continuity loop (work continues while operator away) unimplemented | WP-P4-016 |
| GAP-E3-004 | Cross-host stream egress (VPS to Beast over WireGuard) never proven; SSRF validator untested on container Python | WP-P6-024 |
| GAP-E3-006 | Meeting transcription and recording are permission-gated stubs; local whisper primitive unconnected | WP-P4-019 |
| GAP-E3-012 | Broadcast domain models shared across three surfaces without canonical_types registration (documented graduation r… | WP-P2-023 |
| GAP-E3-013 | No pre-actuation simulation/impact-analysis primitive for physical or go-live operations | WP-P2-030 |
| GAP-F1-006 | Strategy concern quadruplicated: Goal/Strategy/Strategic/Executive panels with overlapping tabs | WP-P5-008 |
| GAP-F1-007 | Session/continuity/resume concern spread over 8 panels with >=4 stores + raw fetch | WP-P5-009 |
| GAP-F1-008 | Runtime-node/infrastructure topology rendered by 8 independent panels | WP-P5-010 |
| GAP-F1-009 | Trace-event/timeline concern in 6 surfaces with no canonical Proof stream | WP-P5-011 |
| GAP-F1-010 | Capability registry split across 4 surfaces including 2 orphans | WP-P5-012 |
| GAP-F1-011 | ProjectionPanel renders forecasts, colliding with platform projection concept (ProjectionIntegrationPanel) | WP-P5-013 |
| GAP-F1-015 | Declared absorptions in routes.ts comments never structurally executed - absorbed panels persist | WP-P5-003 |
| GAP-F2-008 | Device/node entity split across 5 stores and two route families (/device vs /devices) | WP-P5-010 |
| GAP-F2-009 | Proof surface demoted to dev-visibility; approvals/proof/governance not in primary nav | WP-P5-003 |
| GAP-F2-010 | bootstrapStore persists server state (approvals, pulse, nodes) to localStorage with no TTL, re-seeds on rehydrate | WP-P5-006 |
| GAP-F2-011 | Dual API stacks (FastAPI /api/umh live vs parallel Hono transports/api/http); ARCHITECTURE.md documents the wrong… | WP-P6-023 |
| GAP-F2-012 | operatorLoopStore god store: 1553 lines, 7 route families, 7 panels | WP-P5-005 |
| GAP-F2-013 | Unconditional 5s global polling of 5 endpoints regardless of visible panel | WP-P5-006 |
| GAP-F2-014 | ~40 stores + route modules serve only dev-visibility panels (dormant surface: ~1250 endpoints vs 551 store call si… | WP-P5-015 |
| GAP-G-011 | Four incompatible risk taxonomies across execution path incl. EnvironmentEnvironmentPacketRiskLevel rename artifact | WP-P2-002 |
| GAP-G-012 | SSH trust is TOFU with hardcoded key path; no host-key pinning | WP-P6-018 |
| GAP-G-013 | Node registries static JSON with no lifecycle write-back or freshness contract; two divergent live snapshots | WP-P2-010 |
| GAP-G-014 | Actuation maturity model Chrome-hardwired; founder confirmation non-blocking; backend selection ignores security_r… | WP-P4-002 |
| GAP-H-007 | Cockpit surface contract tests assert route names and counts only, no response schemas or auth | WP-P6-008 |
| GAP-H-008 | ~120 retired-campaign test files (C16-C40, P1-P3, phase9-35) pinned without marker taxonomy; 7 broken | WP-P6-003 |
| GAP-H-009 | Canon certification suites pass by mass skip when artifacts absent (94 + 61 skip sites) | WP-P6-009 |
| GAP-H-010 | Misleading assertion patterns: enum-literal self-checks, 11 getsource string-assertion files, simulated transport | WP-P6-010 |
| GAP-H-011 | No ontology layer-separation acceptance tests beyond code import-direction law | WP-P6-011 |

### Low (48)

| Gap | Summary | Packet |
|---|---|---|
| GAP-A-010 | Dead socket ports: approval_port, message_port, sensing_port (0 importers each) | WP-P6-016 |
| GAP-A-015 | Projection domain schemas ownerless in data plane; data/repos/entrepreneuros carries full app repo vs schema-only… | WP-P3-012 |
| GAP-A-016 | Package shadowing hazard: entrypoint needs 'import adapters' guard before execution_spine shadows it | WP-P2-021 |
| GAP-B1-012 | Governed spine operation queues are in-memory deques — pending approvals lost on restart, no durable-execution rep… | WP-P1-012 |
| GAP-B2-013 | EnvironmentWorkPacket dormant — no consumers outside own module + registry | WP-P2-005 |
| GAP-B2-014 | Duplicate ExecutionQueue classes; only one registered | WP-P2-002 |
| GAP-B2-015 | Stale module reference: task_pipeline cites non-existent substrate.roles | WP-P2-014 |
| GAP-B2-016 | Instance-context leak: hardcoded founder-shaped default roles in substrate/ | WP-P2-014 |
| GAP-B3-012 | approval_port is an untyped callable registry at a trust boundary | WP-P1-007 |
| GAP-B3-013 | MemoryEntry / CanonicalMemoryEntry double name collision across three modules | WP-P2-002 |
| GAP-B3-014 | Doc drift: governed_mutation location and layer inversion (transport-owned mutation entry point) | WP-P0-001 |
| GAP-B4-015 | LEGACY_DUPLICATES allowlist (17 modules) has no convergence burn-down tracking | WP-P2-001 |
| GAP-C1-012 | check_ungoverned_mutations gate scans nonexistent saas/ and grandfathers two live services | WP-P3-002 |
| GAP-C1-013 | Docs/ground-truth drift: governed_mutation lives in transports/api/governed.py, not governed_spine.py | WP-P6-015 |
| GAP-C1-017 | Instance-context leak: device ids (vps, windows_beast, fly_cockpit) hardcoded in substrate placement policy | WP-P6-020 |
| GAP-C2-009 | Merge verification submits as mutation_name=sandbox_create (audit misattribution) | WP-P6-021 |
| GAP-C2-011 | Chat media upload is an ungoverned direct file write (bounded/validated) | WP-P1-004 |
| GAP-C2-013 | TS mutation endpoints missing operatorGuard (refresh/handoff/parallel, execution, chat, settings, governance) | WP-P2-022 |
| GAP-C3-015 | Mutation-name granularity collapse: 'state_mutate' for chat/ingest/tts/vision; reused 'event_status_update' | WP-P1-003 |
| GAP-C3-016 | Side-door AgentMemory writes from cron/scraper bypass memory promotion pipeline | WP-P1-004 |
| GAP-C3-017 | Doc/registry drift: nonexistent transports/discord/bot.py cited; type-coherence rule names missing types; expired… | WP-P0-008 |
| GAP-C3-018 | Instance-context leaks in adapters: hardcoded 'antonyfmunoz/OS' repo default and founder-name heuristics | WP-P6-020 |
| GAP-C3-019 | discord_bot_commands.py is a 3,113-line god file mixing 93 handlers with inline SQL and external mutations | WP-P4-003 |
| GAP-D1-011 | Hardcoded /opt/OS default store paths in reality_model ignore UMH_ROOT | WP-P3-018 |
| GAP-D1-012 | organism/world_model.py self-model extractors probe nonexistent saas/ paths, permanently mis-reporting cockpit tra… | WP-P3-018 |
| GAP-D1-014 | reality_model package facade omits its own stores (CanonicalRealityModel, InstanceRealityModel, SimulationReality) | WP-P3-018 |
| GAP-D1-015 | understanding modules insert substrate/understanding into sys.path (mis-computed repo root), risking top-level mod… | WP-P3-018 |
| GAP-D2-015 | Vendored repo hygiene divergence (entrepreneuros vendors client/+server/; creatoros lacks shared/models/) | WP-P3-012 |
| GAP-D2-016 | EOS tables.py docstring claims 7 tables, code wires 5 | WP-P3-010 |
| GAP-E1-018 | Course/learning modeling absent across product schemas and substrate | WP-P4-020 |
| GAP-E2-014 | Browser adapter status contradictory between fleet audit and code | WP-P6-023 |
| GAP-E2-015 | Structural graph under-reports wiring (lazy imports invisible to dependents) | WP-P6-022 |
| GAP-E2-016 | Jarvis codename embedded in substrate module names (rename half-done) | WP-P2-026 |
| GAP-E3-009 | ManufacturingOS domain model absent (jobs/machines/materials/QC) — strategy-intent only, correctly sequenced post-… | WP-P4-020 |
| GAP-E3-010 | RoboticsOS control-loop and physical-actuator command model absent; 'actuator' namespace already taken by GUI actu… | WP-P4-020 |
| GAP-E3-011 | SecurityOS zero repo evidence; all required capabilities (sensors/zones/alerts/incidents/mitigations/policies) inf… | WP-P4-020 |
| GAP-E3-014 | Broadcast plan lineage stale — canonical plan contradicts its own ZMQ proof and superseded dependency graph never… | WP-P6-023 |
| GAP-F1-013 | Keyboard shortcut collisions: key '6' and key 'g' each assigned twice in routes.ts | WP-P5-003 |
| GAP-F1-014 | Loop concern duplicated: 4 loop panels as routes AND re-imported by LoopCanvasWorkspace | WP-P5-014 |
| GAP-F2-015 | 7 sibling canvas stores with separate persisted layout schemas | WP-P5-005 |
| GAP-F2-016 | sw.ts hardcodes production domain; constants/devices.ts embeds instance device fleet in platform artifact | WP-P5-018 |
| GAP-F2-017 | Two parallel push-registration paths persisting to a JSON file (no durable store, no tenancy) | WP-P5-017 |
| GAP-F2-018 | CLI uses API-key auth while visual surfaces use Clerk — asymmetric operator identity | WP-P5-019 |
| GAP-G-015 | Mesh registry hardcodes /opt/OS snapshot path violating UMH_ROOT convention | WP-P6-019 |
| GAP-G-016 | Unauthenticated mesh /nodes and /health endpoints leak topology (IDs, capabilities, tailscale IPs, peripherals) | WP-P0-002 |
| GAP-G-017 | PHYSICAL_WORLD risk category exists with no gate, adapter, or safety-envelope semantics | WP-P4-002 |
| GAP-H-012 | test_spine_full.py pins the ungoverned rival spine variant (substrate/execution/spine.py) as current | WP-P1-001 |
| GAP-H-013 | c28/c29 certification suites are environment-coupled scripts (live prod URL + Beast SSH), not repeatable tests | WP-P6-012 |

---

## 17. Coverage Proof

*Added 2026-07-04 in a hostile-review remediation pass. The 17 Phase-1 ledgers each carried a Coverage section; none of that disclosure had reached the deliverable docs. This section synthesizes it: what was inspected, at what depth, against what ground truth — and, explicitly, what was NOT inspected. An audit that does not state its blind spots invites exactly the false-100% failure this repo's own verification protocol legislates against. The full standalone proof — including method, command census, verification statistics, and invalidation triggers — is [UMH_ONE_SHOT_COVERAGE_PROOF.md](UMH_ONE_SHOT_COVERAGE_PROOF.md).*

### 17.1 Ground truth

- **6,955 repo files** (`find`, standard excludes, 2026-07-03 — ledger A) / **1,789 graph-indexed Python files**, 5,222 import edges, 628,006 lines (`query_graph stats`). Re-measured 2026-07-04: 6,967 files (+12 drift since ledger capture; per-directory numbers below are the 2026-07-03 ledger-A F1 figures).
- The 18 top-level directories in the ledger-A F1 table sum to **6,751** files; the remainder (~204) is root-level files (README, ARCHITECTURE.md, PLATFORM_SPEC.md, docker-compose.yml, dotfiles, etc.), which workstream A covered directly.

### 17.2 Per-directory coverage vs ground truth

Coverage classes: **deep** = files opened/traced by a workstream whose ledger claims the surface; **census** = 100% mechanically enumerated/grepped, subset opened; **targeted** = specific files only, package not claimed; **blind** = no ledger claims the directory.

| Directory | Files (A F1) | Coverage | Claimed by | Known holes |
|---|---|---|---|---|
| substrate/ | 990 | census/deep (partial) | B1–B4 (primitives), D1 (ontology slice), C1 (mutation core), G (execution/organism sampled) | `composition/` 45 .py **blind** (now grep-classified — spine doc §2.8, matrix row 47); `state/` 60 of 63 .py **blind** (3 files touched: canonical_memory_store_v1, transformation_state_ledger, entity_link_store); `understanding/` 9 subpackages ~35 of 54 .py **blind** (D1 covered only ontology/, world_model/, domains/, reality/) — deliberation, interpretation, research, patterns, world_pulse, embedding, intelligence, signals, knowledge were never checked for rival primitives or ungoverned write paths |
| transports/ | 215 | census (api), deep (discord, node_mesh) | A, C1, C2 (143/143 api .py + 9/9 TS), C3, G (12/12 node_mesh) | `presence/` 23 .py **blind** (only substrate_command_handler.py cited, and only as an ImportError site — now grep-classified, spine doc §2.8); `cli/` 7 .py **blind** (F2 flagged its auth asymmetry without auditing it — now grep-classified, spine doc §2.8); `channels/` 2 .py blind |
| adapters/ | 102 | census | G (100 .py contract sweep), C3 (8/8 adapter families) | leaf bodies sampled, not all opened |
| cockpit/ | 409 | census/deep | F1 (78/78 panels, 110 components inventoried), F2 (77/77 stores, ~1,250 endpoints counted) | 77 store bodies mostly unread (names + imports used); rooms/vision/cards leaf internals unread (36 files) |
| tests/ | 378 | census | H (377/377 AST-scanned; 32 opened; collect-only run over all 15,017) | **no test executed** — collection only |
| scripts/ | 196 | targeted | A (6 of 11 check gates run), C3 (12 cron-referenced scripts) | ~134 manually runnable .py never enumerated in Phase 1 — grep-censused 2026-07-04 (58 touch an external write-capable surface; spine doc §2.8) |
| projections/ | 60 | census | D2 (59/59 .py enumerated, 21 opened) | — |
| nodes/ | 56 | deep (key paths) | G (51 .py), B1/B2 (environments/) | — |
| services/ | 40 | census | C3 (23/23 services) | — |
| infra/ | 14 | deep | G (5/5 registries), C3 (20/20 cron entries) | — |
| umh/ | 3 | targeted | A (heads of desktop_relay, voice_server), E2/F2 (citations) | vision_relay.py (105KB) body unread |
| skills/ | 466 | census (names only) | E2 (97 tool skills counted; saas-dev-skill opened) | **contents of ~460 skill files unread** — classification is by name/structure |
| data/ | 2,847 | **blind (bulk)** | E1 (3 vendored schema.ts read in full — 2,496 lines), D2 (70 vendored tables inventoried), targeted JSON registries | ~2,800 runtime artifacts, audit outputs, graph caches, repos/ app code **uninspected** |
| docs/ | 616 | targeted | E2 (126 convergence docs listed, 5 deep-read), E3 (10/10 broadcast specs, 7/11 strategy docs), A (root canon docs) | several hundred plan/audit docs unread |
| knowledge/ | 344 | **blind** | — | wiki/palace never audited for drift against code |
| agents/ | 11 | **blind** | — | soul documents not reviewed |
| docker/ | 3 | blind | — | — |
| config/ | 1 | targeted | (env conventions checked by A/C ledgers) | — |

### 17.3 Per-workstream inspection depth

| WS | Scope | Depth claim (from ledger Coverage section) |
|---|---|---|
| A | Architecture / layering / entrypoints | ~30 files opened, ~30 grep sweeps over all 5 code layers (exhaustive for import direction); 6 of 11 check gates run `--all`; 18/18 top-level dirs, 5/5 entrypoints, 22/22 socket ports |
| B1 | Primitives: Signal/Intent/Gap/DesiredState/CurrentState/Operation | 24 files opened, ~30 sweeps, 4 import-verification runs; 6/6 assigned primitives |
| B2 | Primitives: WorkPacket/Step/Adapter/Tool/Node/Session/Role/Instance | 29 files opened, ~25 greps; 8/8 primitives; execution/runtime 18/18 .py listed |
| B3 | Primitives: Policy/Approval/Proof/Eval/Memory/StateCommit | 24 files opened, ~35 patterns; 9/9 primitives; 28 approval classes accounted; 10 of 55 proof-named class files enumerated |
| B4 | Primitives: Capability/Projection/Domain/Entity/StateAuthority | ~27 files + 1 registry; 10/10 primitives; all 58 Capability* and 37 Projection* class hit-lines reviewed |
| C1 | Python mutation core | 22/22 assigned files in full + 9 partial; gate scan over all 183 route/service files; 39 state-changing function families classified |
| C2 | API write surfaces | 143/143 Python API files (1,306 handlers, 320 mutations, 360 governed sites) + 9/9 TS files |
| C3 | Non-API mutation paths | 23/23 services, 20/20 cron entries, 8/8 adapter families, mesh end-to-end; ~35 files deep + ~60 grepped |
| D1 | Ontology slice (ontology/, world_model/, domains/, reality/) | 32 of 35 ground-truth targets opened (8,295 target lines); **did not cover the other 9 understanding/ subpackages** |
| D2 | Projections / vendored schemas | 59/59 projection .py enumerated, 70/70 vendored tables, 17 L4 grounding mechanisms |
| E1 | Capability inheritance | all 2,496 schema.ts lines read; 27 capability rows × 3 projections |
| E2 | Operator/workstation/meta-IDE | 56+19+18 .py enumerated; 142 transports/api .py censused; 126 convergence docs listed; **skills/ covered at doc layer only** |
| E3 | Broadcast/rooms/physical | 10/10 broadcast specs, 10/10 adapters/broadcast, 7/7 actuation+media files |
| F1 | Cockpit panels/routes | 78/78 panels endpoint- and import-grepped (100%), 52 head-sampled; 110/110 components inventoried |
| F2 | Cockpit stores/backend binding | 77/77 stores, 10/10 api files, 12/12 hooks, 119/119 backend cockpit route files (~1,250 endpoints); 551 store fetchApi sites classified |
| G | Nodes/mesh/trust | 5/5 registries, 12/12 node_mesh .py, 100 adapters .py contract-swept, 51 nodes .py key paths |
| H | Tests/certification | 377/377 test files AST-scanned; collect-only over 15,017 tests; **zero tests executed** |

### 17.4 Blind spots (explicit)

Surfaces this audit did **not** inspect. Findings in this document make no claims about them; convergence planning must treat them as unknown, not clean.

**In-repo code (bounded, now grep-classified where marked):**
1. `substrate/composition/` — 45 .py, the TME runtime. Live (imported by the execution spine) with an ungoverned queue write. Grep-classified 2026-07-04: spine doc §2.8, matrix row 47. Full pass queued.
2. `substrate/state/` — 60 of 63 .py, ~20 subpackages including 15 store modules; 27 files carry write-capable patterns, 0 call `governed_mutation` directly. "Memory writes" was a mandated mutation surface; this package was neither inspected nor previously declared. Spine doc §2.8.
3. `substrate/understanding/` — 9 subpackages (~35 of 54 .py) outside D1's slice. Not checked for rival primitives or ungoverned writes. Targeted pass queued.
4. `transports/presence/handlers/` — 23 .py live command-ingress transport; per-handler governed-vs-direct classification outstanding. Spine doc §2.8.
5. `transports/cli/` — 7 .py API-key ingress; grep-classified as a read-mostly pass-through (1 mutation endpoint). Spine doc §2.8.
6. `scripts/` manual ops tier — ~134 of 146 .py never enumerated in Phase 1; 58 touch external write-capable surfaces at grep level. Spine doc §2.8.
7. `transports/channels/` (2 .py), `agents/` (11 soul docs), `docker/` (3), `skills/` file contents (~460), most `docs/` (~600) and all `knowledge/` (344).

**In-repo data:** the bulk of `data/` (2,847 files) — runtime artifacts, prior audit outputs, graph caches, JSONL state, and the vendored app repos beyond their `shared/schema.ts` files.

**Outside the repo snapshot (structurally out of scope for a read-only worktree audit):**
- **Git history** — no ledger inspected commit history; all claims are point-in-time against the 2026-07-03 worktree.
- **Neon database contents** — schema/row reality, skill/agent registration status (E2 blocker: unverifiable without DB access). Code-side claims about tables are grep-derived.
- **Runtime/process truth** — no tests executed, no service probes, no endpoint calls (E2/H blockers); systemd listings cited as observed-on-host only. Every "deployed"/"live" claim derives from compose/nginx/cron config, not from probing.
- **Beast (Windows executor) local state** — daemon, models, mirrored repos; described only via registry entries and memory notes.
- **External SaaS state** — Notion workspaces, Discord servers, Google Workspace, 1Password vaults, Fly deployment state.

### 17.5 UNVERIFIED rollup

Carried as UNVERIFIED across the deliverables — asserted nowhere as fact:

| Item | Source |
|---|---|
| Live runtime health of the registered EOS poller | E1/E2; matrix appendix |
| EOS entity persistence path (pure constructors observed) | GAP-E1-020 |
| Whether the two work-packet endpoint families share a backing table | F1 |
| Whether backend `/presence/command` can emit the 7 orphaned panel ids | F1 |
| Per-endpoint depth of governed_mutation wrapping in the 51 no-mutation-verb API files | F2/C2 |
| Neon skill/agent registration status | E2 blocker |
| Fleet-audit doc vs `adapters/browser/__init__.py` — which is stale | GAP-E2-014 |
| EventConsole vs ActivityPanel vs TimelineView duplication (bodies unread) | F1 |
| All §2.8 spine-doc classifications (grep-level, no data-flow audit) | this pass, 2026-07-04 |
| Test-suite pass/fail state (collection breaks; nothing executed) | H |

**Effect on the gap ledger:** none of the blind spots above reduces any §16 finding — every gap is evidenced within inspected surfaces. The exposure runs the other way: uninspected surfaces can only add gaps. The 270-gap index is a floor, not a ceiling.

---

*End of document. Companion artifacts: [UMH_CANONICAL_PRIMITIVE_MAP.md](UMH_CANONICAL_PRIMITIVE_MAP.md) · [UMH_EXECUTION_SPINE_COMPLIANCE.md](UMH_EXECUTION_SPINE_COMPLIANCE.md) · [UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md](UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md) · [UMH_PROJECTION_CAPABILITY_MATRIX.md](UMH_PROJECTION_CAPABILITY_MATRIX.md) · [UMH_WORK_PACKET_BACKLOG.md](UMH_WORK_PACKET_BACKLOG.md).*
