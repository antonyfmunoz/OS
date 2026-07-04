# UMH Projection Capability Matrix

Date: 2026-07-03. Repo: `/opt/OS/.claude/worktrees/umh-convergence-audit` (all paths repo-relative).
Synthesized from Phase 1 evidence ledgers E1 (EOS/CreatorOS/LyfeOS), E2 (Jarvis/Operator, Workstation, Meta IDE), E3 (BroadcastOS, Conference Rooms, ManufacturingOS, RoboticsOS, SecurityOS), cross-checked against F1 (cockpit panels) and F2 (cockpit stores/API layer). Gap IDs reference the consolidated gap index (270 candidates).

UMH framing used throughout: UMH is a human-governed agentic operating control plane for desired-state reconciliation across software, data, humans, organizations, workflows, filesystems, cloud services, local devices, runtime nodes, agents, adapters, sensors, and physical/digital actuators. The projections in the columns below are surfaces built on that substrate; this matrix scores what each surface requires from the substrate and what the substrate actually provides today.

Layer references: **L1** = External Operational Reality Model, **L2** = UMH Platform Metamodel, **L3** = Projection Domain Models, **L4** = Semantic Grounding/Mapping Layer.

---

## 1. Method Note

Capability status was inferred from four evidence classes, in descending evidentiary strength:

1. **Shipped code** — modules in `substrate/`, `adapters/`, `transports/`, `projections/`, `cockpit/`, plus wiring evidence (who registers/imports/mounts what). Runtime wiring was verified by grep, not graph alone (the structural graph misses lazy function-scoped imports).
2. **Vendored product schemas** — the three Drizzle schemas define the intended L3 domain surface per product projection: `data/repos/entrepreneuros/shared/schema.ts` (481 L), `data/repos/creatoros/shared/schema.ts` (567 L), `data/repos/LYFEOS/shared/schema.ts` (1,448 L). All 2,496 lines were read by the E1 auditor.
3. **Spec docs** — executed-program specifications with proof reports: `docs/superpowers/specs/broadcast/` (10 files), `docs/audits/convergence/phase13_*` operator-experience series, `docs/canonical/umh_synthesis.md` §7.
4. **Strategy docs** — intent-only sources: `docs/strategy/product_map.md`, `docs/strategy/source_ingestion_map.md`, `docs/system/strategic_context_amendment_v2_physical_moat_report.md`.

Rules applied:

- A capability is **not** credited as available to a projection unless the code path is registered/wired at runtime. Example: CreatorOS and LyfeOS integration handlers exist and pass unit tests, but only `_register_eos_integration()` exists (`transports/api/app.py:142-203,363`) and the only poller class in the codebase is `EOSPoller` (`projections/eos/integration/poller.py:34`) — so CreatorOS/LyfeOS integration cells are **dormant**, not present.
- Point-in-time proof claims in phase docs (85/85 tests, etc.) are treated as doc claims, not current runtime truth; no CI manifest ties those suites to main (E2 F4).
- **SecurityOS rows are inferred-only.** `grep -ril "securityos|security os" docs/ substrate/ adapters/` returned zero hits (E3). The only code hooks are `PhysicalDomain.SECURITY_PHYSICAL` and a HomeAssistant lock mapping (`substrate/execution/adapters/physical.py:35,188`). Every SecurityOS cell derives required capabilities from the audit brief's domain model, not from repo evidence.
- **ManufacturingOS and RoboticsOS are strategy-intent only** — no runtime module, no domain model, no schema (E3 F4/F5; explicit non-implementation list at `docs/system/strategic_context_amendment_v2_physical_moat_report.md:214-232`).
- Rename caveat: the E2 ledger observed `jarvis_loop_coordinator.py` / `jarvis_acceptance*.py` in `substrate/organism/`; at synthesis time only the renamed `operator_loop_coordinator.py` / `operator_acceptance*.py` exist (verified by `ls`). Citations below use the verified operator-prefixed names; GAP-E2-012/GAP-E2-016 (duplicate module families / codename leak) appear at least partially resolved since ledger capture and should be re-verified before scheduling.
- Every repo path cited in this document was existence-checked against the worktree on 2026-07-03; the two stale jarvis paths above were the only failures and were replaced with their verified successors.

---

## 2. Columns and Status Vocabulary

### Columns (11 projections)

| Column | What it is | Evidence base |
|---|---|---|
| **EOS** | EntrepreneurOS business projection (CRM, agents, workflows) | Shipped code + vendored schema (E1) |
| **CreatorOS (COS)** | Creator/community product projection | Shipped integration shell + vendored schema (E1) |
| **LyfeOS** | Personal-state product projection (quests, rituals, vision) | Shipped integration shell + vendored schema (E1) |
| **Jarvis/Operator (J/O)** | Operator-experience surface: conversational kernel, approvals, presence, voice, continuity | Shipped code + phase13_x spec docs (E2), cockpit bindings (F1/F2) |
| **Workstation (WS)** | Workstation runtime: execution engines, actuation, relays, node mesh, durability | Shipped code (E2) |
| **Meta IDE (MI)** | Engineering workbench: planning, review, workspace, verification | Shipped code (E2), cockpit bindings (F1/F2) |
| **BroadcastOS (BC)** | Live capture/compositing/streaming projection | Shipped code + spec docs with proof reports (E3) |
| **Conference Rooms (CR)** | Rooms/channels/meetings/voice-video surface | Shipped code (E3), cockpit bindings (F2) |
| **SecurityOS (SEC)** | Physical security projection — **zero repo evidence; all cells inferred** | Inference only (E3 F6) |
| **ManufacturingOS (MFG)** | Physical production projection | Strategy docs only (E3 F4) |
| **RoboticsOS (ROB)** | Robotics control projection, 10+ year horizon | Strategy docs only (E3 F5) |

### Cell status vocabulary

| Token | Meaning |
|---|---|
| **CT** | canonical-tested — one canonical substrate implementation, wired at runtime, with tests |
| **PF** | present-fragmented — capability exists but split across rival implementations/stores/endpoints with no declared authority |
| **PO** | projection-only — exists in the projection's own code/DB with no substrate counterpart |
| **DM** | dormant — code exists and compiles (may pass unit tests) but is not wired into the operation runtime |
| **MS** | missing — required by the projection's domain surface, absent everywhere |
| **UT** | untested — implementation exists but no runtime/acceptance proof in repo |
| **UA** | unclear-authority — two or more systems claim the same state with no declared source of truth |
| **NA** | n-a — not part of this projection's required capability surface |
| **INF** | inferred — status derived without repo evidence (SecurityOS-only, plus explicitly marked cells) |

Compound tokens (e.g. `PF/UT`) mean both conditions hold. In the SEC column, `MS/INF` pairs a repo-verified absence (the capability exists nowhere in the repo) with a requirement that is itself inferred from the audit brief's domain model, not from repo evidence — per the SecurityOS inferred-only rule in Section 1.

---

## 3. Capability × Projection Matrix

47 substrate capability categories, grouped into 9 thematic sub-tables. Column order: EOS, COS, LyfeOS, J/O, WS, MI, BC, CR, SEC, MFG, ROB. Section 4 carries the per-capability owner files, evidence, and gap pointers. (Row 47, Tool Mastery / knowledge-gap composition, was added 2026-07-04 in a hostile-review remediation pass — `substrate/composition/` was outside every Phase-1 ledger's scope; see footnote ⁴⁰.)

### 3.A Identity, Governance, Policy

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Identity / tenancy | UA | UA | UA | PF | PF | PF | PF | PF | INF | MS | MS |
| 2 | Roles / permissions | PF | MS | MS | PF | NA | NA | MS | PO | INF | MS | MS |
| 3 | Policy / authority (governed mutation) | CT | DM | DM | PF | PF | PF | CT¹ | CT | INF | MS | MS |
| 4 | Approval routing | UA | MS | MS | PF² | PF | PF | UT | PF | INF | MS | MS |

¹ BC human path (start/stop/composite/switch) is governed; the agent path is dormant (row 19).
² Critical fragmentation: ≥9 client approval stores over ≥9 backend approval families (GAP-F2-001), 11 UI surfaces (GAP-F1-002).

### 3.B Domain Modeling (L3)

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | Organization modeling (companies/departments) | PO/UT | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| 6 | Business modeling (CRM/pipeline/deals) | PO | NA³ | NA³ | NA | NA | NA | NA | NA | NA | NA | NA |
| 7 | Personal-state modeling (stats/rituals/quests/vision) | NA | NA³ | PO/DM | NA | NA | NA | NA | NA | NA | NA | NA |
| 8 | Creator/media content modeling (posts/stories) | NA | PO/DM | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| 9 | Community modeling (communities/channels/followers) | NA | MS | NA | NA | NA | NA | NA | PO | NA | NA | NA |
| 10 | Course / learning modeling | MS | MS | MS | NA | NA | NA | NA | NA | NA | NA | NA |
| 11 | Commerce / payments / entitlements | MS | PO⁴ | MS | NA | NA | NA | NA | NA | NA | NA | NA |

³ Sibling tables exist in the product schema (COS contacts/xp fields, LyfeOS contacts) but are unbridged; scored NA because the capability belongs to another projection's core surface.
⁴ COS `record_revenue` is a DB insert, not payment execution; `Capability.PAYMENT_PROCESS` is an enum + intent regex only, and the authority engine denies payment execution (GAP-E1-006).

### 3.C Coordination & Delivery

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 12 | Scheduling / queues / recurring jobs | PF | MS | PO | PF/UT⁵ | PF/UT | NA | NA | NA | INF | MS | MS |
| 13 | Notifications / push | PF | PF | PF | PF/UT⁶ | PF | NA | NA | NA | INF | NA | NA |
| 14 | Realtime messaging / rooms / voice / video | PF | MS | PF | PF | NA | NA | NA | PF⁷ | NA | NA | NA |
| 15 | Media asset management | MS | MS | PO⁸ | NA | NA | NA | MS | MS | NA | NA | NA |
| 16 | Capture / streaming / transcoding | NA | NA | NA | PF | PF | NA | PF⁹ | UT | INF | NA | NA |
| 17 | Publishing / distribution | PO | DM | NA | NA | NA | NA | PF¹⁰ | NA | NA | NA | NA |

⁵ `substrate/workstation/overnight_queue.py` is an explicitly non-executing scaffold (queue/dry-run/approval-only); the mandated continuity loop (leave→continue→resume) is not implemented (GAP-E2-017).
⁶ Delivery silently disableable — pywebpush optional import downgrades to `logger.debug` and disables all push; no delivery acceptance test (GAP-E2-010).
⁷ Rooms CRUD + LiveKit voice/video shipped and governed, but state authority is unlocked flat JSON (row 32, GAP-E3-005) and transcription/recording are permission-gated stubs (GAP-E3-006).
⁸ LyfeOS stores base64 file bodies in Postgres text columns (`data/repos/LYFEOS/shared/schema.ts:906,1188`); no substrate asset store exists (GAP-E1-017).
⁹ Slice-0 pipeline (synthetic/file/pull → compose → RTMP) is runtime-proven with governed routes; real capture, hardware encode, and the audio pipeline are DOC-SPEC ONLY (GAP-E3-002, GAP-E3-003).
¹⁰ Same-host RTMP egress proven; cross-host egress explicitly deferred/unproven (GAP-E3-004). CreatorOS `create_post` writes a product DB row only — no social publishing adapter exists (GAP-E1-021).

### 3.D Credentials, Adapters, Runtime Nodes & Execution

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 18 | OAuth / credential management | UA | MS | UA | PF¹¹ | PF | PF | MS | PF | INF | NA | NA |
| 19 | Adapters / connectors (capability handlers) | CT/UT | DM | DM | PF | PF | PF | DM¹² | NA | DM/INF¹³ | MS | MS |
| 20 | Runtime-node registry | NA | NA | NA | PF | PF | PF | PF | NA | INF | MS | MS |
| 21 | Workload placement | NA | NA | NA | PF/UT | PF/UT¹⁴ | NA | PF | NA | NA | MS | MS |
| 22 | Agent delegation | PO | MS | MS | PF/UT | PF | PF | DM | NA | NA | MS | MS |
| 23 | Work packets | NA | NA | NA | PF¹⁵ | PF | PF | NA | NA | INF | MS | MS |
| 24 | Durable operations | NA | NA | NA | PF¹⁶ | PF | PF | MS | UA | MS/INF | MS | MS |

¹¹ 1Password credential gate is the governed path, but the vision WS ships a static build-time token in the public JS bundle and the voice WS carries no credential (GAP-F2-006); three parallel OAuth token stores exist across product DBs (GAP-E1-007).
¹² `BroadcastCapabilityHandler` exists but no boot-time registration call exists anywhere; `transports/api/app.py:86-116` registers only the Notion integration. The proof report's "registered — PASS" was a validation-run instantiation, not runtime wiring (GAP-E3-001).
¹³ `substrate/execution/adapters/physical.py` ships a full sensor/actuator contract + functional HomeAssistant adapter with zero dependents, and its `registry.execute()` bypasses `governed_mutation()` despite a docstring claiming governance (GAP-E3-007).
¹⁴ Mesh dispatch hardcodes a single executor node and Windows cwd allowlist in the platform transport layer — `_ALLOWED_NODE_IDS = frozenset({"windows-desktop"})` (`transports/api/_mesh_dispatch.py:22`) — capping placement at exactly one node (GAP-E2-004).
¹⁵ Two work-packet endpoint families (`/command-center/work-packets` vs `/organism/universal-work/packets`) rendered by 12 independent panels; UNVERIFIED whether they share a backing table (GAP-F1-003).
¹⁶ Durability = single-host POSIX renames (workcell inbox/inflight/processed) + JSONL session persistence; no DB-backed durable execution, no cross-node recovery, no recovery SLO (GAP-E2-009).

### 3.E Evidence & Evaluation

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25 | Proof artifacts | UT¹⁷ | NA | NA | PF | PF | PF | PF | PO | MS/INF | MS | MS |
| 26 | Trace events | PF | DM | DM | PF¹⁸ | PF | PF | UT | PO | INF | NA | NA |
| 27 | Evaluation results | UT | UT | UT | PF | PF¹⁹ | PF | PF | UT | MS/INF | MS | MS |
| 28 | Memory promotion | NA | NA | NA | PF/DM²⁰ | NA | NA | NA | NA | NA | NA | NA |

¹⁷ EOS entity persistence/reconciliation has no verified proof-artifact path (GAP-E1-020).
¹⁸ Six independent timeline/trace-event surfaces, none canonical (GAP-F1-009).
¹⁹ Actuator maturity model L0–L7 caps proof claims by evidence class — the strongest evaluation discipline in the repo (`substrate/execution/actuation/actuator_maturity_v1.py:16-77`).
²⁰ LearningPanel (lessons/patterns/evolution/drift) is registered but has no route — the memory-promotion loop view is unreachable (GAP-F1-001).

### 3.F Registries & State

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 29 | Capability registry | PF | DM | DM | PF²¹ | PF | PF | DM | NA | INF | MS | MS |
| 30 | Template registry | NA | NA | NA | PF/UT | NA | NA | NA | NA | NA | MS²² | NA |
| 31 | Projection registry / inheritance | PF²³ | PF²³ | PF²³ | PF | NA | NA | MS | MS | MS/INF | MS | MS |
| 32 | State authority | UT | UT | UT | PF | UA²⁴ | UT | UT | UA²⁵ | MS/INF | MS | MS |
| 33 | Entity resolution (cross-projection) | MS | MS | MS | PF²⁶ | NA | NA | NA | NA | INF | NA | NA |
| 34 | Source truth / outcome writeback | UA²⁷ | UA/DM | UA/DM | PF²⁸ | NA | NA | NA | UA | NA | NA | NA |

²¹ Capability-registry UI split across 4 surfaces incl. 2 orphans (GAP-F1-010); the substrate router is 28 enum capabilities with regex intent routing only.
²² Template-system extensibility is a doc policy constraint (physical-domain templates must not be precluded), not an implementation.
²³ Registry fragmentation + ID canon conflict: at least three ID schemes per projection (`eos`/`entrepreneuros`, `cos`/`creatoros`); registry key `cos` is absent from the alias normalizer (GAP-E1-004); two distinct "projection port" abstractions share the same name (GAP-E1-015).
²⁴ Three coexisting code generations claim workstation state (GAP-E2-006).
²⁵ All room state persists as unlocked flat JSON under `/var/lib/umh/rooms` with silent `return []` on decode error (GAP-E3-005).
²⁶ `resolve_entity_reference` is name-lookup only; three contact tables model the same external persons with no linkage (GAP-E1-019); four parallel operator identity stores with no bridge (GAP-E1-003).
²⁷ `umh_status` columns and `umh_outcomes` tables written into product DBs are undeclared in all three product Drizzle schemas (GAP-E1-002); two `umh_outcomes` definitions with different owners (GAP-E1-016).
²⁸ Client-side: bootstrapStore persists approvals/pulse/mesh-nodes to localStorage and reseeds stores on rehydrate with no TTL — the client briefly treats its cache as state authority (GAP-F2-010).

### 3.G Operator Surfaces & Interaction Primitives

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 35 | Analytics / dashboards | PF | MS | MS | PF | NA | NA | NA | NA | NA | NA | NA |
| 36 | Search / discovery / marketplace | MS | PO | MS | PF | NA | NA | NA | NA | NA | NA | NA |
| 37 | File / document / calendar / board / canvas primitives | PO | PO | PO²⁹ | PF³⁰ | PF | PF | NA | NA | NA | NA | NA |
| 38 | Browser / computer use | NA | NA | NA | PF | PF/DM³¹ | PF | NA | NA | NA | NA | NA |
| 39 | Voice (STT/TTS/wake/session) | NA | NA | NA | PF/UT³² | PF | NA | NA | PF | NA | NA | NA |
| 40 | Vision / screen awareness | NA | NA | NA | PF/UT | PF/UT³³ | NA | NA | NA | INF | NA | NA |

²⁹ Three incompatible document models across product schemas; LyfeOS additionally carries kanban/canvas/spreadsheet/graph/missionView primitives with zero substrate counterpart.
³⁰ Cockpit side: 7 sibling persisted canvas-layout stores (GAP-F2-015); operator loop / conversational kernel itself has four executable entry points with no declared authority — `substrate/organism/dex_conversation.py`, `orchestrator_kernel.py`, `operator_loop_runtime.py`, `operator_loop_coordinator.py` (GAP-E2-001).
³¹ 9 dormant browser engines in `substrate/execution/workers/workstation/_dormant/` with no disposition record (GAP-E2-007); fleet-audit doc contradicts `adapters/browser/__init__.py` on adapter export status (GAP-E2-014); Electron IPC `fs:writeFile` gives the renderer ungoverned filesystem writes while the HTTP equivalent is governed (GAP-F2-007).
³² Three parallel voice stacks (cockpit WS server, C20 substrate runtimes, Discord voice engine); real-microphone E2E was a documented phase13_4 blocker never closed; voice WS carries no client credential (GAP-E2-002, GAP-F2-006); C20 tests hardcode a deleted worktree path (GAP-E2-008).
³³ Two rival screen-awareness modules in two packages, both route-wired; C21 tests validate against in-file mocks — no live-capture acceptance in repo.

### 3.H Physical & Safety

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 41 | Physical actuation (sensors/actuators/IoT) | NA | NA | NA | NA | NA³⁴ | NA | NA | NA | DM/INF | MS | MS |
| 42 | Safety / emergency-stop / rollback | NA | NA | NA | PF³⁵ | MS | NA | MS³⁶ | NA | MS/INF | MS | MS |
| 43 | Simulation / impact analysis | NA | NA | NA | PF/UT³⁷ | MS | NA | MS | NA | MS/INF | MS | MS |

³⁴ "Actuator" in shipped code (`substrate/execution/actuation/`) means GUI/desktop actuation exclusively — a naming-collision risk when physical actuation arrives (GAP-E3-010).
³⁵ The only kill switch is agent-recursion-scoped (`substrate/organism/recursion_governance.py:166-212`). No physical safety envelope, actuator interlock, non-reversibility flag, or e-stop channel exists anywhere (GAP-E3-008) — a hard prerequisite for SEC/MFG/ROB.
³⁶ BC's only blast-radius control is the output-URL SSRF guard (`adapters/broadcast/ffmpeg_args.py:137`); no pre-go-live impact analysis exists (GAP-E3-013).
³⁷ `/reality-model/simulate` exists as a client-reachable endpoint (worldModelStore → `transports/api/cockpit_reality_model_routes.py`); no pre-actuation impact-analysis contract feeds the governance risk class (GAP-E3-013).

### 3.I Self-Evolution & Verification

| # | Capability | EOS | COS | LyfeOS | J/O | WS | MI | BC | CR | SEC | MFG | ROB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 44 | Self-improvement / self-build | NA | NA | NA | PF³⁸ | PF | PF | NA | NA | NA | NA | NA |
| 45 | CI/CD deploy verification | NA | NA | NA | UT³⁹ | UT | PF | UT | UT | NA | NA | NA |
| 46 | Testing / certification | UT | DM | DM | UT | UT | PF | PF | UT | INF | MS | MS |
| 47 | Tool mastery / knowledge-gap composition (TME) | NA | NA | NA | NA | UT⁴⁰ | UT⁴⁰ | NA | NA | NA | NA | NA |

³⁸ A second, ungoverned agentic execution system exists inside the repo: `skills/saas-dev-skill/` carries its own orchestrator, approval gate, and direct `claude -p` subprocess LLM calls with zero imports of governed_mutation/spine/policy engine (GAP-E2-003).
³⁹ Phase docs claim large passing counts as point-in-time worktree runs; no CI manifest ties those suites to main (E2 F4).
⁴⁰ Added 2026-07-04: `substrate/composition/` (45 .py — knowledge_gap_trigger.py, mastery/{research,authoring,management}/, registries/) was inspected by no Phase-1 ledger; E2 covered only the `skills/` doc layer. Status here derives from a targeted grep pass only: the package is live (imported by `substrate/execution/spine.py`, `substrate/execution/mastery_gate.py`, `substrate/control_plane/actions/tme.py`) but has zero `governed_mutation` calls and writes its gap queue directly (`substrate/composition/knowledge_gap_trigger.py:135-140` → `data/umh/composition/gap_queue.jsonl`). No test/acceptance evidence was audited — internals UNVERIFIED pending a full pass (spine-compliance doc §2.8).

---

## 4. Per-Capability Detail: Owners, Evidence, Gap Pointers

Columns: substrate owner = canonical L2 location (or "none"); evidence = load-bearing files/docs; gaps = gap-index IDs to schedule against.

### 4.A Identity, Governance, Policy

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 1 | Identity / tenancy | `transports/api/http/db/schema.ts:75-141` (platform users/portfolios/organizations/orgMembers) | Four parallel user stores: platform users vs `data/repos/entrepreneuros/shared/schema.ts:6-33` (Firebase), `data/repos/creatoros/shared/schema.ts:7-18` (serial int), `data/repos/LYFEOS/shared/schema.ts:7-41` (2FA/Stripe), plus Clerk (`data/umh/projection_registry.json`). CLI uses API-key auth vs Clerk everywhere else (`ARCHITECTURE.md:400-411,436`) | GAP-E1-003 (critical), GAP-F2-018 |
| 2 | Roles / permissions | `orgMembers.role/accessLevel` (`transports/api/http/db/schema.ts:126-141`); `substrate/types.py:1108` (Role) | 4 permission vocabularies in EOS alone (`projections/eos/entities.py:36-141`, product `agents.roleLevel`); Rooms has its own server/role/permission model (`transports/api/cockpit_rooms_routes.py:145-171,307-459`) | (feeds GAP-E1-005) |
| 3 | Policy / authority | `substrate/organism/governed_spine.py`; consumed via `transports/api/governed.py:65` (`governed_mutation`); `substrate/control_plane/governance.py` (risk classification) | EOS workflows route every step through governed_mutation (`projections/eos/workflows/runner.py:29,140`); BC routes governed (`transports/api/cockpit_broadcast_routes.py:37,172,215,320,397`); Rooms governed (`cockpit_rooms_routes.py:29,668,695,717,755`); COS/LyfeOS handlers declare RiskClass but are never registered. CT test basis: `tests/test_execution_authority_engine_v1.py` (authority engine), `tests/test_conference_rooms.py` (CR governed path), `tests/adapters/broadcast/test_process_lifecycle.py` (BC CT¹) | GAP-E1-001, GAP-E3-007, GAP-F2-007 |
| 4 | Approval routing | `substrate/sockets/approval_port.py`; `approvals` table (`transports/api/http/db/schema.ts:161`); `scripts/workers/discord_approval_worker.py` | EOS product `agent_actions` runs its own approval loop unlinked to UMH approvals (`data/repos/entrepreneuros/shared/schema.ts:376-423`); cockpit: ≥9 stores/≥9 backend approval families (`cockpit/src/renderer/stores/unifiedApprovalStore.ts`, `organismStore` spine approve, `operatorLoopStore`, `proofInspectorStore`, `delegationStore`, `unifiedExecutionStore`, `engineeringStore`, `actionsStore`, `coherenceStore`, plus `bootstrapStore.ts:37`); 11 UI surfaces | GAP-F2-001 (critical), GAP-F1-002 (critical), GAP-E1-005 |

### 4.B Domain Modeling

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 5 | Organization modeling | `substrate/types.py:1108-1304` (Role, Department, Portfolio, Company, Workflow*, Dashboard*) | `projections/eos/entities.py:27-300` builds 10 departments/roles from substrate types; persistence/reconciliation path UNVERIFIED (pure constructors, read-only views); `projections/eos/workflows/types.py:13` redefines WorkflowStep parallel to `substrate/types.py:1227` — Type Coherence Law violation | GAP-E1-020, GAP-E1-013 |
| 6 | Business modeling | none — substrate carries only generic `events` (`projections/eos/views/kpis.py:44-61`) | CRM lives in the EOS product DB; bridge covers contacts/deals/activities only (`projections/eos/integration/manifest.py:113`); `projections/eos/views/pipeline.py` projects it | GAP-E1-014 |
| 7 | Personal-state modeling | `substrate/execution/bridge/rituals.py` + `ritual_runner.py` (scaffold, explicitly unwired per docstring lines 8-11) | LyfeOS ~35-table surface (`data/repos/LYFEOS/shared/schema.ts:44-255,311-356,1294-1317`) vs 3 polled tables, and the bridge itself is dormant | GAP-E1-008, GAP-E1-001 |
| 8 | Creator/media content modeling | none | COS posts/stories/comments/savedPosts/taggedUsers (`data/repos/creatoros/shared/schema.ts:30-79,267-284,387-408`); only `posts` polled, dormant | GAP-E1-001 |
| 9 | Community modeling | none (`substrate/sockets/message_port.py:1-25` is a persistence sink, not a domain model) | COS communities/channels/channelMessages/followers have zero UMH surface (`data/repos/creatoros/shared/schema.ts:155-216`); Rooms server/channel model is the nearest shipped analog (`transports/api/cockpit_rooms_routes.py:307-459`) — the two are unrelated implementations | GAP-E1-009 |
| 10 | Course / learning | none anywhere in repo | No course/lesson/enrollment tables in any product schema; LyfeOS learning profile is a jsonb field (`data/repos/LYFEOS/shared/schema.ts:128-137`) | GAP-E1-018 |
| 11 | Commerce / payments / entitlements | `Capability.PAYMENT_PROCESS` enum + intent regex only (`substrate/execution/runtime/capability_router.py:61,454-460`); authority engine denies execution | LyfeOS Stripe fields with deliberate non-implementation (`tests/test_phase14_6b_lyfeos_code_resolved_canon.py::test_no_stripe_resources_created`); COS products/revenue tables (`data/repos/creatoros/shared/schema.ts:89-109,219-232`) | GAP-E1-006 |

### 4.C Coordination & Delivery

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 12 | Scheduling / queues | none canonical — host cron + `substrate/organism/autonomous_tick.py`; `substrate/organism/correspondence_scheduler.py` is regression-check-only | LyfeOS quests carry a full recurrence model (`data/repos/LYFEOS/shared/schema.ts:335-339`) with no substrate recurring-schedule primitive to reconcile against; `substrate/workstation/overnight_queue.py` is a non-executing scaffold | GAP-E1-010, GAP-E2-017 |
| 13 | Notifications / push | `substrate/sockets/notification_engine.py:22-34` (5 channels, tested: `tests/test_notification_engine.py`) | Product notification stores disjoint (EOS/COS tables, LyfeOS FCM `pushSubscriptions`); UMH web push separate VAPID stack (`transports/api/cockpit_push_routes.py`, pywebpush optional at line 35); two client registration paths persisting to `data/push_subscriptions.json` (`cockpit/src/renderer/capacitor-init.ts:16-32`, `cockpit/src/renderer/lib/pushNotifications.ts:25-28`) | GAP-E1-011, GAP-E2-010, GAP-F2-017 |
| 14 | Realtime messaging / rooms / voice / video | `substrate/sockets/message_port.py` (sink only); no messaging domain model | Rooms + LiveKit shipped (`transports/api/cockpit_rooms_routes.py:101-123,1694-1699,2122-2156`; `cockpit/src/renderer/stores/roomsStore.ts` 42 mutation endpoints; `voiceSessionStore.ts`); COS conversations/DMs unbridged (`data/repos/creatoros/shared/schema.ts:310-362`) | GAP-E3-005, GAP-E1-009 |
| 15 | Media asset management | none (graph search `media` returns no substrate asset owner) | LyfeOS base64 `fileData` columns (`data/repos/LYFEOS/shared/schema.ts:906,1188`); COS raw URL strings (`data/repos/creatoros/shared/schema.ts:34-36`) | GAP-E1-017 |
| 16 | Capture / streaming / transcoding | `adapters/broadcast/` (engine, filtergraph, zmq_client, process_lifecycle); `substrate/execution/media/media_processor.py` (offline faster-whisper + Gemini) | BC slice-0 runtime-proven (`adapters/broadcast/engine.py:103-199`; proof: `docs/superpowers/specs/broadcast/SLICE0_PROOF_REPORT.md:110-117`); real capture/NVENC/audio DOC-SPEC ONLY (`docs/superpowers/specs/broadcast/BROADCAST_BUILD_PLAN.md:104-106`); Windows node adapter reuses the VPS libx264 arg builder (`nodes/windows/umh_node/adapters/broadcast.py`); broadcast Scene/SourceEntry/CompositeConfig (`adapters/broadcast/scene_model.py`) are now consumed by three surfaces (routes, capability handler, Windows node adapter) — the documented "graduate to canonical_types.py when shared" rule is triggered but not executed | GAP-E3-002, GAP-E3-003, GAP-E3-012 |
| 17 | Publishing / distribution | `Capability.SOCIAL_POST` enum only (`substrate/execution/runtime/capability_router.py:58`); `adapters/broadcast/` is streaming, not social publishing | EOS content workflows (`projections/eos/workflows/content.py`); COS `create_post` inserts a product DB row (`projections/creatoros/integration/manifest.py:55-66`); BC cross-host egress deferred (`docs/superpowers/specs/broadcast/AGENT_GOLIVE_INVESTIGATION.md:186-217`) | GAP-E1-021, GAP-E3-004 |

### 4.D Credentials, Adapters, Runtime Nodes & Execution

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 18 | OAuth / credential mgmt | `substrate/execution/credential_gate.py` + `services/oauth_device_flow.py` + 1Password injection (`.claude/rules/credential-injection.md`) | EOS `oauth_tokens` + LyfeOS `integrations` store raw tokens in product DBs (`data/repos/entrepreneuros/shared/schema.ts:425-449`; `data/repos/LYFEOS/shared/schema.ts:1006-1037`); vision WS static token in public bundle (`cockpit/src/renderer/api/vision-ws.ts:161-162`); voice WS credential-free (`cockpit/src/renderer/api/voice-ws.ts:17-21`); BC stream-key registry DOC-SPEC (`AGENT_GOLIVE_INVESTIGATION.md:46-66`) | GAP-E1-007, GAP-F2-006 |
| 19 | Adapters / connectors | registration site: `transports/api/app.py:142-203` (EOS) and `:86-116` (Notion — only two); `adapters/` family (google_workspace, notion, github, browser, broadcast, calendar, ssh, tailscale) | Only `EOSPoller` exists (`projections/eos/integration/poller.py:34`); COS/LyfeOS handlers complete but unregistered (`projections/creatoros/integration/handlers.py:24-147`); `BroadcastCapabilityHandler` unregistered (`adapters/broadcast/integration/handlers.py:19`); `substrate/integrations/product_connections.py:65-134` imports projections from substrate — dependency-direction violation. EOS CT test basis: `tests/test_eos_projection.py` (unit-level; live poller runtime health UNVERIFIED per Appendix, hence CT/UT) | GAP-E1-001, GAP-E3-001, GAP-E1-012 |
| 20 | Runtime-node registry | `infra/device_registry.json`; `transports/node_mesh/server.py` (WS :8094) + `registry.py`; `substrate/organism/runtime_fleet.py` | 5 client stores own device/node state over two route families (`cockpit/src/renderer/stores/deviceStore.ts`, `umhNodeStore.ts`, `systemStore.ts`, `bootstrapStore.ts:88-98`, `api/device-presence.ts:32-53`); 8 topology panels (F1 cluster 6) | GAP-F2-008, GAP-F1-008 |
| 21 | Workload placement | `substrate/organism/workload_placement_policy.py` (phase 13.4M) | Mesh dispatch single-node hardcode (`transports/api/_mesh_dispatch.py:22-28,37`); BC remote dispatch via `:8095/dispatch` (`transports/api/cockpit_broadcast_routes.py:115-158`) | GAP-E2-004 |
| 22 | Agent delegation | `substrate/organism/delegation_runtime.py` (+ `delegation_topology.py`, `substrate/workstation/agent_workforce_runtime.py`); tests `tests/test_delegation_runtime.py` | Flow intent→proposal→mission→WorkPacket→GovernedWorkRuntime unit-tested, no runtime proof; EOS ships 10 department agents (projection-local); saas-dev-skill runs delegation outside governance | GAP-E2-003 |
| 23 | Work packets | `nodes/environments/work_packet.py` (WorkPacketRiskLevel/Status, per canonical type registry) | Two endpoint families rendered by 12 panels (`cockpit/src/renderer/panels/WorkPanel.tsx` vs `UniversalWorkPanel` et al.); god store `operatorLoopStore.ts` (1,553 lines, 7 route families) | GAP-F1-003, GAP-F2-012 |
| 24 | Durable operations | `substrate/organism/workcell_protocol.py:1-18` (filesystem exactly-once); `substrate/organism/operator_session.py` (JSONL); `substrate/workstation/checkpoint.py`, `continuity.py` | Single-host POSIX rename durability, no recovery SLO; Rooms state = unlocked flat JSON (`transports/api/cockpit_rooms_routes.py:50-70`) | GAP-E2-009, GAP-E3-005 |

### 4.E Evidence & Evaluation

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 25 | Proof artifacts | `substrate/execution/workers/workstation/visible_actuation_proof_v1.py`; `substrate/meta_ide/browser_evidence_collector.py`; proof surface: `transports/api/cockpit_proof_inspector_routes.py` + `cockpit/src/renderer/panels/ProofInspectorPanel.tsx` | Proof surface is dev-visibility only — not first-class navigation (`cockpit/src/renderer/types/routes.ts:164`); BC proof reports exist but one claim (handler registration) misstates runtime wiring (`SLICE0_PROOF_REPORT.md:178-186`); Rooms `_audit` log (`cockpit_rooms_routes.py:81`) | GAP-F2-009, GAP-E3-001 |
| 26 | Trace events | `substrate/execution/trace.py` (CONFIRMED_RUNTIME per component status registry); cockpit `/activity/stream` | 6 timeline surfaces, none canonical (ActivityPanel, OperatorTimelinePanel, RealityTimelinePanel + 3 embedded tabs); "Absorbed into Activity" declared in routes.ts but both persist | GAP-F1-009, GAP-F1-015 |
| 27 | Evaluation results | `substrate/execution/feedback.py` (quality scoring); `substrate/execution/actuation/actuator_maturity_v1.py:16-77` (evidence-capped L0–L7); `substrate/organism/operator_acceptance.py` (+ `_mode`, `_scenarios`) | Acceptance scenarios exist (phase13_4 18-step E2E documented); MVP readiness scoring (`cockpit/src/renderer/stores/mvpReadinessStore.ts` → `transports/api/cockpit_mvp_readiness_routes.py`); projection unit tests never exercise runtime paths | GAP-E2-012 (re-verify post-rename) |
| 28 | Memory promotion | `transports/api/cockpit_learning_routes.py` + `cockpit_memory_routes.py`; panels `LearningPanel.tsx` (ORPHAN), `MemoryPanel.tsx` | Lessons/patterns/evolution/drift view unreachable (no route); decision-memory view dev-visibility | GAP-F1-001 |

### 4.F Registries & State

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 29 | Capability registry | `substrate/execution/runtime/capability_router.py:36-73` (28 capabilities, regex intent routing at 440-480) | UI split across `CapabilityMapPanel.tsx` (routed), `CapabilitiesPanel`/`SkillsPanel` (orphans), KnowledgePanel; BC/COS/LyfeOS capabilities defined but unregistered; 33 dormant workstation engines lack disposition (`substrate/execution/workers/workstation/_dormant/`) | GAP-F1-010, GAP-E2-007, GAP-E3-001 |
| 30 | Template registry | `/organism/templates` + template-candidates approve/reject (`cockpit/src/renderer/stores/coherenceStore.ts` → `transports/api/cockpit_autonomous_routes.py`) | Client-reachable, no acceptance evidence; MFG template-extensibility constraint is doc policy (`docs/system/strategic_context_amendment_v2_physical_moat_report.md:249-262`) | — |
| 31 | Projection registry | `substrate/sockets/projection_port.py:60-197` + `data/umh/projection_registry.json` seeded by `substrate/organism/daemon.py:424-454` | ID canon conflict (`cos` absent from `_PROJECTION_ALIASES`, `substrate/organism/projection_integration_runtime.py:192-204`); rival `substrate/organism/projection_port.py` (state-slice broadcast) shares the name; cockpit view: `projectionIntegrationStore.ts` → `transports/api/cockpit_projection_integration_routes.py` | GAP-E1-004, GAP-E1-015 |
| 32 | State authority | `substrate/organism/state_authority_graph.py` (+ `transports/api/cockpit_state_authority_routes.py`; tests `tests/test_phase29_state_authority_graph.py`) | Models domains but declares no owner for projection data (CRM rows vs umh_status); StateAuthorityPanel is dev-visibility; workstation authority split across 3 code generations (`substrate/organism/workstation_runtime.py` 1,400 L vs `substrate/workstation/unified_workstation_runtime.py` "single source of truth" claim vs workers/workstation engines) | GAP-E2-006, GAP-E2-001 |
| 33 | Entity resolution | `substrate/organism/context_resolution.py:194` (`resolve_entity_reference`, name-lookup only); client surface `realityGraphStore.ts` → `/context-resolution/resolve` | Three unlinked contact tables; four unlinked user stores; no L4 identity-resolution registry | GAP-E1-019, GAP-E1-003 (critical) |
| 34 | Source truth / outcome writeback | intended: platform `umh_outcomes` (`transports/api/http/db/schema.ts:182`) | All three `tables.py` write `umh_status` + product-side `umh_outcomes` undeclared in product schemas (`projections/eos/integration/tables.py:487-583`; grep of `data/repos/*/shared/schema.ts` = 0 hits); divergence already recorded by `substrate/organism/projection_reconciliation_engine.py:224-244` | GAP-E1-002, GAP-E1-016, GAP-F2-010 |

### 4.G Operator Surfaces & Interaction Primitives

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 35 | Analytics / dashboards | `substrate/types.py:1277-1304` (Dashboard types); EOS KPIs read substrate `events` (`projections/eos/views/kpis.py:44-61`) | Product `agent_metrics` is a second unbridged metrics store; cockpit analytics route is `planned` visibility (`cockpit/src/renderer/stores/analyticsStore.ts` → `transports/api/cockpit_core_eos_routes.py`) | GAP-E1-014 |
| 36 | Search / discovery / marketplace | `embeddings` table (`transports/api/http/db/schema.ts:207`); `substrate/understanding/embedding/embedding_engine.py` | Platform-content only; COS products table is marketplace-lite with no discovery substrate (`data/repos/creatoros/shared/schema.ts:89-100`) | — |
| 37 | File / document / calendar / board / canvas | `Capability.DOCUMENT_MANAGE` / `CALENDAR_MANAGE` enums (`capability_router.py:62`); `adapters/google_workspace/doc_creator.py`; `adapters/calendar/`; governed workspace I/O (`transports/api/cockpit_workspace_routes.py:61,108`) | Three incompatible document models across product schemas; LyfeOS calendar/kanban/canvas/spreadsheet primitives have no bridge; cockpit has 7 sibling canvas-layout stores | GAP-E1-017, GAP-F2-015 |
| 38 | Browser / computer use | `adapters/browser/__init__.py` (re-exports BrowserAgent); `services/browser_relay.py` (os-browser container); `substrate/execution/actuation/actuator_backend_registry_v1.py:78-229` (7 GUI backends); `substrate/meta_ide/browser_verification_gate.py` | 9 dormant browser engines; fleet-audit doc contradicts adapter export (`docs/audits/convergence/phase13_4m_multi_runtime_jarvis_acceptance_correction.md:65`); Electron IPC fs bypass (`cockpit/src/main/index.ts:153-177`) | GAP-E2-007, GAP-E2-014, GAP-F2-007 |
| 39 | Voice | no single owner — 3 stacks: `umh/voice_server.py` (WS :8096), `substrate/workstation/voice_ingress_runtime.py` + C20 siblings, `substrate/execution/voice/voice_engine.py` (Discord) | Real-mic E2E never proven (`docs/audits/convergence/phase13_4_standard_multi_runtime_true_jarvis_e2e_acceptance.md:266-272`); C20 tests hardcode deleted worktree path (`tests/test_c20_0_voice_ingress.py:9`); Rooms voice via LiveKit is a fourth, separate stack | GAP-E2-002, GAP-E2-008, GAP-F2-006 |
| 40 | Vision / screen awareness | rivals: `substrate/operator/screen_awareness.py` + `screen_observation_engine.py` (Phase 32/33) vs `substrate/workstation/screen_awareness_runtime.py` (C21, wired via `transports/api/cockpit_screen_awareness_routes.py`); relays `umh/vision_relay.py`, `umh/desktop_relay.py` | Both rivals route-wired; C21 tests mock-only; vision WS ships static token | GAP-E2-005 (adjacent presence sprawl), GAP-F2-006 |

### 4.H Physical & Safety

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 41 | Physical actuation | `substrate/execution/adapters/physical.py` (PhysicalAdapter ABC :122-145, registry :286-340, HomeAssistant adapter :148-283) — zero dependents | Docstring claims governance (:9) but `registry.execute()` (:316-327) calls `adapter.execute_action()` directly — no `governed_mutation()`, no risk class, no permission envelope; `SensorReading.to_observation()` (:108-119) feeds nothing (no reconciliation loop over sensor input) | GAP-E3-007 |
| 42 | Safety / emergency-stop / rollback | none — only agent-recursion kill switch (`substrate/organism/recursion_governance.py:166-212`) | No per-device permitted-operation set, e-stop channel, interlock, or non-reversibility flag; MFG human-approval mandate is doc policy only (`docs/strategy/source_ingestion_map.md:208-210`) | GAP-E3-008 (prerequisite for SEC/MFG/ROB) |
| 43 | Simulation / impact analysis | `/reality-model/simulate` (`cockpit/src/renderer/stores/worldModelStore.ts` → `transports/api/cockpit_reality_model_routes.py`) | No pre-actuation impact-analysis contract (predicted effect, reversibility, cost, exposure) feeding governance risk class — needed by BC go-live, MFG job release, ROB motion, SEC mitigation | GAP-E3-013 |

### 4.I Self-Evolution & Verification

| # | Capability | Substrate owner | Key evidence | Gaps |
|---|---|---|---|---|
| 44 | Self-improvement / self-build | `/organism/self-build/*` + `/organism/roadmap` (`cockpit/src/renderer/panels/SelfBuildPanel.tsx`); `transports/api/cockpit_self_improvement_routes.py`; `substrate/meta_ide/roadmap_gap_engine.py`, `engineering_work_generator.py` | Parallel ungoverned build system: `skills/saas-dev-skill/lib/orchestrator/approval-gate.ts`, `lib/claude-subprocess.ts` — zero governed_mutation/spine/policy imports, not registered in `.claude/skills/` | GAP-E2-003 |
| 45 | CI/CD deploy verification | `substrate/meta_ide/browser_verification_gate.py` + `browser_evidence_collector.py`; `cockpit/deploy.sh` (cockpit deploy gate) | Phase-doc test claims are point-in-time worktree runs; no CI manifest ties suites to main; browser verification must run on executor nodes (orchestrator is headless) per `.claude/rules/browser-verification.md` | GAP-E2-011 (stale doc layer) |
| 46 | Testing / certification | `substrate/organism/operator_acceptance.py` family; `substrate/execution/actuation/actuator_maturity_v1.py` | Projection tests unit-only against unwired code (`tests/test_lyfeos_creatoros_integration.py` — 33 tests, no runtime path); C20 tests import from deleted worktree; C21 tests mock-only; BC has real proof discipline (`tests/adapters/broadcast/test_process_lifecycle.py`, filtergraph tests, `SLICE0_PROOF_REPORT.md`) | GAP-E2-008, GAP-E1-020 |
| 47 | Tool mastery / knowledge-gap composition (TME) | `substrate/composition/` — `knowledge_gap_trigger.py`, `mastery/{research,authoring,management}/`, `registries/canonical_command_registry_v1.py` (45 .py) | Live substrate subsystem: consumed by `substrate/execution/spine.py`, `substrate/execution/mastery_gate.py`, `substrate/control_plane/actions/tme.py` (repo grep, 2026-07-04). Write surface ungoverned: gap queue appended directly at `knowledge_gap_trigger.py:135-140` (`data/umh/composition/gap_queue.jsonl`); backlog artifacts via `mastery/management/backlog.py:110-113,179`; zero `governed_mutation` calls in package. **Coverage caveat:** no Phase-1 ledger inspected this package — row derives from a targeted post-synthesis grep pass; spine-compliance doc §2.8 carries the write-surface classification | none assigned (Phase-1 coverage gap — gap-analysis §17) |

---

## 5. Rollups

### 5.1 Per-projection readiness

| Projection | Verdict | Basis |
|---|---|---|
| **EOS** | **Most integrated projection; runtime-untested beyond unit level.** | Only projection registered at runtime (`transports/api/app.py:142-203`); workflows route through governed_mutation. But: bridge covers 3 of 15 product tables (CRM slice only), two unlinked approval systems (GAP-E1-005), identity/OAuth/outcome-writeback authority all unclear (GAP-E1-003/-007/-002), entity persistence unverified (GAP-E1-020). |
| **CreatorOS** | **Dormant shell.** | Manifest/handlers/tables exist, pass unit tests, are never registered; no poller. 3 of 20 tables covered; community/social graph (8 tables) has zero UMH surface (GAP-E1-009); publishing is a DB insert (GAP-E1-021). |
| **LyfeOS** | **Dormant shell with the largest domain gap in the portfolio.** | ~35-table product surface vs 3 polled tables on a bridge that is itself unwired (GAP-E1-008); recurrence/rituals have no substrate scheduling primitive to reconcile against (GAP-E1-010); commerce deliberately unimplemented. |
| **Jarvis/Operator** | **Broadest shipped surface; worst fragmentation.** | Four executable operator-intent kernels with no declared authority (GAP-E2-001); approvals split across ≥9 stores/families (GAP-F2-001, critical); 3 voice stacks with real-mic E2E never closed (GAP-E2-002); presence in 5 modules/4 route surfaces (GAP-E2-005); continuity loop unimplemented (GAP-E2-017). The five-surface convergence model exists only as routes.ts comments (GAP-F1-004/-015). |
| **Workstation** | **Three coexisting code generations; heavy dormant inventory.** | organism runtime vs workstation package vs workers/workstation engines, no declared authority (GAP-E2-006); 33 dormant engines without disposition (GAP-E2-007); durability is single-host filesystem with no recovery SLO (GAP-E2-009); mesh capped at one hardcoded executor node (GAP-E2-004). |
| **Meta IDE** | **Most coherent shipped projection.** | 18 substrate modules + 5 route files + tests, correct dependency direction, functional wiring census; the strongest verification primitives in the repo (browser evidence collector, verification gate, review packages). Residual: split across two packages (layering smell), governed HTTP path undermined by ungoverned Electron IPC sibling (GAP-F2-007). |
| **BroadcastOS** | **Deepest vertical slice with genuine proof discipline; agent path unwired.** | Slice-0 pipeline runtime-proven, governed, SSRF-guarded, CPU-gated; scene switching proven blip-free. But the "dual-consumer" thesis fails at boot (handler never registered, GAP-E3-001); audio, real capture, hardware encode, and cross-host egress are spec-only (GAP-E3-002/-003/-004); shared domain types await canonical registration (GAP-E3-012); plan-document lineage is stale — three overlapping roadmaps coexist with no supersession notices (GAP-E3-014). |
| **Conference Rooms** | **Functionally shipped; structurally fragile.** | Full server/channel/role/meeting model, LiveKit voice/video, governed mutations, audit log. State authority is unlocked flat JSON with silent data-loss masking (GAP-E3-005, high); transcription/recording are permission-gated stubs (GAP-E3-006); no spec doc exists for the surface. |
| **SecurityOS** | **Zero repo evidence — unscheduled.** | All rows inferred (E3 F6). Nearest primitives (physical adapter contract, HomeAssistant lock mapping) are dormant and ungoverned. Prerequisites before any scoping: GAP-E3-007 (govern physical execution) and GAP-E3-008 (safety envelope). |
| **ManufacturingOS** | **Strategy-intent only — correctly sequenced post-revenue.** | 15 explicit non-implementations enumerated in the physical-moat report; only near-term obligation is the template-extensibility constraint (GAP-E3-009). |
| **RoboticsOS** | **Strategy-intent only — 10+ year horizon by declared strategy.** | No motion/trajectory/feedback primitive; "actuator" namespace already means GUI actuation (collision risk, GAP-E3-010); gated behind GAP-E3-008. |

### 5.2 Per-capability universality

**Tier 1 — Canonical somewhere, extensible (the substrate's real assets):**

- **Policy/authority (`governed_mutation`)** is the single most universal capability: enforced in EOS workflows, Broadcast routes, Rooms routes, workspace I/O, and (coarse scan) all mutation-bearing cockpit route files (68/119 import it; zero mutation-verb endpoints found in the other 51 — F2, per-endpoint depth unaudited). The two known bypasses are Electron IPC writes (GAP-F2-007) and the physical adapter registry (GAP-E3-007).
- **Adapter/integration contract** (manifest + handler + signals + outcomes) is registered and wired end-to-end exactly once (EOS; live runtime health unverified — see Appendix) and copied correctly three more times (COS, LyfeOS, Broadcast) — the pattern generalizes; only the registration/poller runtime is missing (GAP-E1-001, GAP-E3-001).
- **Evidence discipline** exists in two strong local forms — actuator maturity levels and broadcast proof reports — but is not a shared L2 contract.

**Tier 2 — Present everywhere, fragmented everywhere (highest-leverage convergence targets):**

- **Approval routing** — the worst case in the audit: ≥9 backend families, ≥9 client stores, 11 UI surfaces, plus a parallel product-DB approval loop in EOS (GAP-F2-001, GAP-F1-002, GAP-E1-005 — two criticals).
- **Identity/tenancy** — four operator identity stores plus Clerk plus API-key CLI; no bridge (GAP-E1-003, critical).
- **Operator intent ingestion** — four kernels (GAP-E2-001, critical).
- **Notifications, voice, presence, screen awareness, state authority, timelines/traces, work packets, node registry** — each has 3–8 rival implementations with no declared owner.
- **Cockpit route layer** — 121 route files / 324 include-mount lines with no machine-readable route registry mapping route file → substrate authority → auth requirement (GAP-E2-013).

**Tier 3 — Missing everywhere (build-new decisions, mostly L2/L4):**

- **Physical safety envelope / e-stop / rollback** (GAP-E3-008) — hard prerequisite for the entire physical-projection roadmap.
- **Cross-projection entity resolution / identity bridge** (GAP-E1-003/-019) — prerequisite for any multi-projection reconciliation claim.
- **Commerce/payments** (GAP-E1-006), **media asset management** (GAP-E1-017), **recurring-schedule reconciliation** (GAP-E1-010), **course/learning** (GAP-E1-018), **pre-actuation simulation/impact analysis** (GAP-E3-013), **social publishing adapters** (GAP-E1-021).

**Structural pattern across all three tiers:** the substrate's governed-mutation spine and its integration contract are sound and reused; what is missing is (a) a registration/wiring runtime that makes the second-through-nth consumer of any contract as cheap as the first, and (b) declared state authority per concern. Nearly every PF and UA cell in Section 3 reduces to one of those two deficits.

---

## Appendix — Verification Record

- All repo paths cited above were existence-checked with a shell loop over the worktree on 2026-07-03 (two batches, ~200 paths). Failures: `substrate/organism/jarvis_loop_coordinator.py` and `substrate/organism/jarvis_acceptance.py` (cited by ledger E2) no longer exist; the renamed `operator_loop_coordinator.py`, `operator_acceptance{,_mode,_scenarios}.py`, and `operator_readiness_gate.py` were verified present and substituted. `substrate/workstation/jarvis_command.py` (compat shim) still exists.
- Line-number citations are carried from the Phase 1 ledgers as recorded and were not independently re-read at synthesis time.
- Known UNVERIFIED items inherited from ledgers and preserved as such: EOS entity persistence path (GAP-E1-020); live runtime health of the registered EOS poller; whether the two work-packet endpoint families share a backing table (F1); per-endpoint depth of governed_mutation wrapping (F2, workstream C2 scope); which of the fleet-audit doc vs `adapters/browser/__init__.py` is stale (GAP-E2-014).
- 2026-07-04 remediation addition: row 47 (Tool mastery / TME, `substrate/composition/`) was added after hostile review found the package absent from all 17 ledger coverage claims. Its evidence is a targeted grep pass, not a Phase-1 workstream audit; its internals (mastery pipeline behavior, test coverage, queue consumers) remain UNVERIFIED. The original 46 rows and all other cells are unchanged.
- Gap ID totals: consolidated index reports 270 gap candidates (23 critical / 87 high / 112 medium / 48 low); E1 contributed 21, E2 17, E3 14. Criticals cited in this matrix: GAP-E1-003, GAP-E2-001, GAP-F1-002, GAP-F2-001.
