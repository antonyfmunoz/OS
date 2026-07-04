# UMH Convergence — Implementation Execution Plan

> **Status:** Wartime execution board. Read-only against all code — this is a PLAN, not a change set.
> **Scope:** 149 work packets across P0→P6, execution order fixed by the critical path.
> **Companion docs (this directory):**
> - `UMH_WORK_PACKET_BACKLOG.md` — the 149-packet backlog (source of every packet body quoted here)
> - `UMH_ONE_SHOT_CONVERGENCE_GAP_ANALYSIS.md` — gap analysis and risk register
> - `UMH_CANONICAL_PRIMITIVE_MAP.md` — 33-primitive status rollup
> - `UMH_EXECUTION_SPINE_COMPLIANCE.md` — governed-mutation adoption evidence
> - `UMH_ONTOLOGY_METAMODEL_DOMAIN_SEPARATION.md` — L1–L4 layer separation basis for P3
> - `UMH_PROJECTION_CAPABILITY_MATRIX.md` — projection surface inventory for P4
> - `bypass_inventory.md`, `duplicate_reconciliation_map.md` — supporting evidence
> - Schemas: `../../schemas/convergence/{canonical_primitives,gap_record,ontology_layer,operation_lifecycle,projection_capability,work_packet}.schema.json`

---

## 1. Executive Summary

This plan is the ordered, self-contained execution board for converging UMH from a working-but-fragmented single-operator control plane into a singular, mechanical, fail-closed platform. It sequences the 149 bounded work packets in `UMH_WORK_PACKET_BACKLOG.md` into an executable order with per-packet verification, rollback, acceptance criteria, and PR strategy.

**Verdict from the audit (three findings that drive the whole plan):**

1. **The understanding gap is closed.** The one-shot convergence audit produced a complete map: 33 canonical primitives with status, 4 rival execution spines, 4 WorkPacket variants, 4 approval state machines on 11 UI surfaces, 5 runtime-node models. There is no remaining "we don't know what's there" risk. This is a declare-one-owner-per-concern exercise, **not a rewrite** — the governed spine, the integration contract, and the Meta IDE verification primitives are sound and reused.

2. **Convergence-before-features is non-negotiable.** No projection-facing feature work begins until P0–P3 land. P4 (projection capability build-out) is the earliest projection-facing phase, and it is gated on the converged spine (P1), canonical types (P2), and four-layer separation (P3). Building projections on top of fail-open trust boundaries would multiply the blast radius of every P0 defect.

3. **P0 is stop-the-bleeding.** P0 is the only phase where the system is *actively unsafe* rather than merely fragmented. `governed_mutation()` fails **open** when the control-plane daemon is down (every one of 360 mutation sites degrades to `completed_ungoverned` with no state-commit record); the mesh relay dispatches arbitrary remote shell with no auth when one env var is unset; two governed paths are silently broken by typo'd method calls; and the 15,017-test suite cannot even collect. Until P0 is green, no downstream packet has a trustworthy verification harness.

**Single recommended first action:** Implement **WP-P0-001** (fail-close `governed_mutation()` and move the mutation choke point below the transport layer) as a single small PR off `umh-convergence-audit`. It is the keystone — it blocks WP-P0-002, WP-P0-003, and every P1 spine packet, all of which assume fail-closed semantics. Nothing else in the plan is trustworthy until it lands.

---

## 2. P0 Stop-the-Bleeding Implementation Order

P0 has 15 packets in **3 waves**. Wave 1 is a 13-packet independent parallel set; Wave 2 and Wave 3 serialize the two mesh-boundary packets behind the keystone.

### Wave 1 — 13 independent packets (start immediately, parallel)

| Packet | What it closes | Boundary touched |
|---|---|---|
| **WP-P0-001** | Fail-open `governed_mutation()` → fail-closed; choke point moved below transport layer (keystone) | mutation (control plane) |
| WP-P0-004 | Unauthenticated 0.0.0.0 CC webhook receiver carrying MFA codes + tmux CC-session control | auth (also terminal) |
| WP-P0-005 | Nightly autonomous write+shell Claude agent on the production repo, ungoverned | mutation / terminal |
| WP-P0-007 | Two silently-broken governed paths (`create_from_intent`, `update_status`) — governance theater | mutation (governed work runtime) |
| WP-P0-008 | WorkPacket-rename import breakage + type-registry/doc ground-truth repair | none (import/registry/doc) |
| WP-P0-009 | Fail-open `evaluate_quality` + silent trace/feedback persistence loss | mutation (quality gate + trace) |
| WP-P0-010 | EOS cross-tenant task read (`user_id` accepted, never bound) | tenant (data-plane; schema-bearing) |
| WP-P0-011 | Broken full-suite pytest collection (3 ImportErrors, INTERRUPTED) | test-infra |
| WP-P0-012 | Raw-fetch cockpit HTTP calls with no Authorization header (401 on every media upload) | auth (cockpit client) |
| WP-P0-013 | Unauthenticated voice WS + shipped static vision token in public JS bundle | auth (live WS) |
| WP-P0-014 | Ungoverned Electron IPC `fs:writeFile` — control-plane bypass on the desktop | mutation (Electron IPC) |
| WP-P0-015 | Ungoverned parallel agentic execution system (`saas-dev-skill`) inside the repo | mutation / trust boundary |
| WP-P0-006 | Dormant unauthenticated mutation services (goal_api, higgsfield_webhook, local_bridge_server) | auth (also terminal) |

### Wave 2 — after WP-P0-001 merges

| Packet | What it closes | Boundary touched |
|---|---|---|
| **WP-P0-002** | Mesh trust boundary: governed remote dispatch, fail-closed relay + WS auth, token→node binding. **Depends on WP-P0-001** (carries the fail-closed verdict semantics). | mesh (also mutation, auth) |

### Wave 3 — after WP-P0-002 merges

| Packet | What it closes | Boundary touched |
|---|---|---|
| **WP-P0-003** | Node-side risk derivation, deny-by-default config, hardened permission envelope. **Depends on WP-P0-002** (verdict transmission) and forward-coordinates WP-P2-002 (canonical role envelope). | mesh / terminal (also auth) |

**P0 exit gate:** every control-plane entry point fails closed; the two broken governed paths work; `pytest --collect-only` is green; no unauthenticated mutation surface (HTTP, WS, IPC, mesh, webhook) remains reachable.

---

## 3. Full Phase Order P0→P6 (Macro Board)

Execution order is strictly P0→P6 with **two sanctioned overlaps** (see §4). Per-phase approval load intersects the 71-packet approval list; sums verified to total 71.

| Phase | Objective (verbatim from backlog) | Entry | Exit | Packets | Waves | Approvals | Keystone |
|---|---|---|---|---|---|---|---|
| **P0** Safety-critical (stop the bleeding) | Close the fail-open trust boundaries and the defects that corrupt or bypass governance today. | None — start immediately. | Every control-plane entry point fails closed; broken governed paths work; collection green; no unauthenticated mutation surface reachable. | 15 | 3 | 11 | **WP-P0-001** |
| **P1** Spine convergence | Converge on one canonical governed operation runtime + one mutation-submission entry; unify approval authority; make spine durable; land commit/verdict/trace/proof primitives. | P0 complete — esp. WP-P0-001 (fail-closed) + WP-P0-004 (authed webhook). | Single documented submission entry enforced by an architecture test; every mutation path routes through it or carries a recorded exemption; approvals in one auditable store; pending work survives restarts. | 21 | 3 | 16 | **WP-P1-001** (runtime), **WP-P1-007** (approval authority) |
| **P2** Primitive / type convergence | One canonical definition per platform primitive; registry gate hardened to hold the line; operator-facing runtime authorities declared. | P1 canonical runtime declared (WP-P1-001); collection green (WP-P0-011). | `check_type_divergence.py --all` exits 0; registry covers all public types; each contested primitive has exactly one owner; dormant stacks dispositioned. | 30 | 4 | 11 | **WP-P2-001** + **WP-P2-002** (parallel pair) |
| **P3** Ontology / metamodel separation | Enforce four-layer separation: L1 reality entities, L2 metamodel free of projection/instance content, L3 projection-owned domain models, L4 grounding/resolution contracts. | P2 canonical types (WP-P2-001/002); WP-P3-001 layer-contract extension lands first within phase. | No upward imports; no projection/instance literals in substrate; declared state authorities; versioned schema artifacts for every write path. | 20 | 3 | 12 | **WP-P3-004** (projection registration/port) |
| **P4** Projection capability build-out | Activate projection surfaces on converged contracts: manifest-driven registration + pollers, EOS/CreatorOS/LyfeOS expansion, governed external actuation, governed continuity loop. | P3 registration/port (WP-P3-004/013) + writeback (WP-P3-009) landed. | Every projection wired end-to-end (poll→signal→handler→outcome) or explicitly dormant; every externally visible actuation behind governed mutation with approval + proof. | 20 | 2 | 12 | **WP-P4-004** |
| **P5** Cockpit convergence | Make the client a faithful projection of the control plane: five-surface IA, one approval queue, domain stores, single staleness policy, remove instance literals + broken bindings. | Server-side approval authority (WP-P1-007) + node identity (WP-P2-010) landed. Layout lock (2026-07-03) applies — IA + state-layer only. | One client owner per control-plane object family; a decision on any surface visible on all; zero raw-fetch bypasses; every panel reachable or dispositioned; all deploys via `bash cockpit/deploy.sh`. | 19 | 6 | 7 | **WP-P5-005** (terminal critical-path hop) |
| **P6** Test / certification hardening | Make the guarantees mechanical: CI, marker taxonomy, contract tests for trust boundaries, honest certification suites, full-scan enforcement sweeps, residual hygiene. | WP-P6-001…004 start once WP-P0-011 lands (parallel with P2–P5); enforcement sweeps (WP-P6-014) require P2/P3 gates green. | CI executes suite on every push; all `check_*.py` gates pass `--all`; certification repeatable + environment-gated; no stale doc contradicts deployment reality. | 24 | 3 | 2 | **WP-P6-014** (enforcement sweep) |

**Cross-phase critical path (7 hops):**
`WP-P0-001 → WP-P1-001 → WP-P1-007 → {WP-P2-001, WP-P2-002} → WP-P3-004 → WP-P4-004 → WP-P5-005`
The two P2 keystones are a parallel pair; both must land before WP-P3-004.

---

## 4. Parallelizable Work Packets (per phase, the waves)

**Same-file-serialization caveat (applies to every wave):** packets in the same wave run concurrently *only when they do not modify the same file*. When two wave-siblings touch a shared file (e.g. `substrate/canonical_types.py` in P0-008 and other P0 registry work, or `substrate/organism/command_runtime.py` in P0-007 and elsewhere), serialize them or coordinate a single merge — never let two open PRs edit the same file in parallel. This is a merge-hygiene rule, not a dependency edge.

- **P0** (3 waves): Wave 1 = {001, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 015} (13 parallel); Wave 2 = {002}; Wave 3 = {003}.
- **P1** (3 waves): Wave 1 = {001, 002, 005, 014, 015, 018, 020}; Wave 2 = {003, 006, 007, 008, 009, 011, 012, 013}; Wave 3 = {004, 010, 016, 017, 019, 021}.
- **P2** (4 waves): Wave 1 = {001, 005, 021, 024, 025, 026, 027, 028, 029}; Wave 2 = {002, 004, 006, 007, 009, 012, 014, 017, 018, 020, 022}; Wave 3 = {003, 008, 010, 011, 016, 019, 030}; Wave 4 = {013, 015, 023}.
- **P3** (3 waves): Wave 1 = {001, 002, 003, 004, 006, 007, 008, 009, 018, 019, 020}; Wave 2 = {005, 010, 011, 013, 015}; Wave 3 = {012, 014, 016, 017}.
- **P4** (2 waves): Wave 1 = {001, 002, 003, 004, 005, 006, 007, 008, 013, 014, 016, 017, 018, 019, 020}; Wave 2 = {009, 010, 011, 012, 015}.
- **P5** (6 waves): Wave 1 = {001, 002, 016, 017, 019}; Wave 2 = {003}; Wave 3 = {004, 013}; Wave 4 = {005}; Wave 5 = {006, 007, 008, 009, 010, 011, 012, 014, 015}; Wave 6 = {018}.
- **P6** (3 waves): Wave 1 = {001, 002, 003, 005, 006, 007, 011, 013, 014, 015, 016, 017, 018, 019, 020, 021, 022, 023, 024}; Wave 2 = {004, 008, 009, 010}; Wave 3 = {012}.

**Two sanctioned cross-phase overlaps:**
1. P6 test-infra {WP-P6-001…004} may start once **WP-P0-011** lands (run parallel with P2–P5).
2. P5 client work **wave 1** may begin once **WP-P1-007** merges (does not wait for full P4).

---

## 5. Sequential Work Packets (critical path + forced ordering)

### Critical-path chain (must be serial — each hop depends on the prior)
`WP-P0-001 → WP-P1-001 → WP-P1-007 → {WP-P2-001 ∥ WP-P2-002} → WP-P3-004 → WP-P4-004 → WP-P5-005`

### Intra-P0 hard dependency edges (force wave ordering)
- WP-P0-002 **depends on** WP-P0-001 (fail-closed verdict semantics)
- WP-P0-003 **depends on** WP-P0-002 (verdict transmission) and forward-coordinates WP-P2-002 (canonical role envelope)

### Forward-coordination dependencies (17 edges — packet lands its own scope in its phase; integration with the referenced later packet completes when that later packet lands)
- WP-P0-002 → WP-P1-001 (verdict-issuance contract)
- WP-P0-002 → WP-P2-010 (durable token→node binding joins canonical node record)
- WP-P0-003 → WP-P2-002 (canonical role envelope)
- WP-P0-005 → WP-P1-001 (governed-spine submission entry for cron)
- WP-P0-008 → WP-P2-002 (class renames finalized later)
- WP-P0-010 → WP-P3-009 (owner-column route → writeback/migration discipline)
- WP-P0-014 → WP-P5-016 (Electron API binding — forwarding variant only)
- WP-P1-005 → WP-P2-022; WP-P1-018 → WP-P2-010; WP-P1-020 → WP-P2-030
- WP-P2-007 → WP-P3-007; WP-P2-025 → WP-P6-022; WP-P2-028 → WP-P4-010; WP-P2-030 → WP-P4-002
- WP-P3-009 → WP-P4-004; WP-P3-013 → WP-P4-004
- WP-P4-012 → WP-P5-017

### Phase-entry serialization (macro)
P1 requires P0 complete (esp. WP-P0-001, WP-P0-004). P2 requires WP-P1-001 + WP-P0-011. P3 requires WP-P2-001/002 (and WP-P3-001 first within phase). P4 requires WP-P3-004/013 + WP-P3-009. P5 requires WP-P1-007 + WP-P2-010. P6 enforcement sweeps (WP-P6-014) require P2/P3 gates green.

---

## 6. Packets Requiring Human Approval (71 total)

Grouped by phase. Per-phase counts: P0=11, P1=16, P2=11, P3=12, P4=12, P5=7, P6=2 (sum = 71).

- **P0 (11):** WP-P0-001, 002, 003, 004, 005, 006, 009, 010, 013, 014, 015.
- **P1 (16):** WP-P1-001, 003, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 017, 019, 020, 021.
- **P2 (11):** WP-P2-002, 005, 010, 011, 014, 018, 022, 024, 025, 027, 030.
- **P3 (12):** WP-P3-001, 002, 003, 004, 005, 007, 009, 011, 012, 015, 016, 020.
- **P4 (12):** WP-P4-001, 002, 003, 004, 005, 007, 009, 013, 014, 016, 019, 020.
- **P5 (7):** WP-P5-001, 003, 004, 005, 015, 017, 019.
- **P6 (2):** WP-P6-017, WP-P6-018.

**P0 approval-not-required (4):** WP-P0-007 (pure defect fix), WP-P0-008 (importability/ground-truth repair), WP-P0-011 (test-infra), WP-P0-012 (bug fix restoring intended auth).

---

## 7. Documentation-Only Packets (4)

These touch documentation only — no runtime code, no schema:

- **WP-P3-003** — (P3 documentation-only)
- **WP-P4-006** — (P4 documentation-only)
- **WP-P4-020** — (P4 documentation-only)
- **WP-P6-023** — (P6 documentation-only)

Note: WP-P0-008 modifies docs (`type-coherence.md`, `services/CLAUDE.md`) but is classified code-touching because it also repairs import statements and the type registry — it is not documentation-only.

---

## 8. Schema Packets

### Schema-only (1)
- **WP-P2-020** — the single schema-only packet (schema artifact, no runtime code path).

### Schema-bearing CRITICAL-migration code packets (6 — carry migration discipline)
- **WP-P0-010** (EOS tenant scope — owner-column route)
- **WP-P1-019**
- **WP-P3-009** (writeback schema)
- **WP-P3-011**
- **WP-P4-009**
- **WP-P5-017**

**Migration-discipline note (applies to all 6):** Row counts checked before any migration; versioned migration files; **down-migration written before the up-migration is applied**; no destructive DDL without backup; no direct DDL against the live Neon EOS database from this repo without the Breaking Change Process in `PLATFORM_SPEC.md`. See the `work_packet.schema.json` and `operation_lifecycle.schema.json` contracts in `../../schemas/convergence/`.

---

## 9. Boundary-Touching Packets

Boundaries: **runtime** (control-plane execution), **mutation** (governed write choke point), **auth** (credential/trust), **mesh** (remote node dispatch), **terminal** (tmux/shell injection), **tenant** (multi-tenant data isolation).

### P0 — mapped precisely from the extract

| Packet | mutation | auth | mesh | terminal | tenant | runtime |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| WP-P0-001 | ● (choke point) | | | | | ● |
| WP-P0-002 | ● | ● | ● | | | |
| WP-P0-003 | | ● | ● | ● | | |
| WP-P0-004 | | ● | | ● (tmux CC inject) | | |
| WP-P0-005 | ● | | | ● (agentic write) | | |
| WP-P0-006 | | ● | | ● (tmux inject) | | |
| WP-P0-007 | ● (governed work runtime) | | | | | ● |
| WP-P0-008 | — (import/registry/doc repair; no boundary) | | | | | |
| WP-P0-009 | ● (quality gate + trace) | | | | | ● |
| WP-P0-010 | | | | | ● (cross-tenant read) | |
| WP-P0-011 | — (test-infra; no boundary) | | | | | |
| WP-P0-012 | | ● (cockpit HTTP client) | | | | |
| WP-P0-013 | | ● (live WS) | | | | |
| WP-P0-014 | ● (Electron IPC write) | | | | | |
| WP-P0-015 | ● (parallel agentic exec) | trust boundary | | | | ● |

### P1–P6 — packet-title granularity (from phase objectives)

| Phase | Primary boundaries touched (from objective) |
|---|---|
| P1 | runtime (canonical governed spine), mutation (single submission entry), auth (unified approval authority), terminal (cron plane governed) |
| P2 | runtime (runtime-node/session/agent authorities), mutation (canonical WorkPacket/Operation record), tenant (agent role/instance) |
| P3 | mutation (writeback schema), tenant (projection/instance-context separation), auth (credential-source declarations, WP-P3-020) |
| P4 | mutation (governed external actuation — payments/publishing/broadcast/physical), auth (adapter credentials), terminal (governed continuity loop) |
| P5 | auth (kill raw-fetch bypasses, WS auth), runtime (domain stores as control-plane projections), tenant (instance-literal removal) |
| P6 | auth (credential gate, SSH pinning, WP-P6-017/018), mutation (trust-boundary contract tests), tenant (instance-leak sweep) |

---

## 10. Packets Requiring New Tests (from the P0 extract)

Ground-truth verified against the actual tree (see `UMH_WORK_PACKET_BACKLOG.md` P0 bodies + the P0 ground-truth report).

### New test files to CREATE (do not exist today)
- `tests/test_governed_mutation_fail_closed.py` — **WP-P0-001** (daemon-down blocked per risk class, daemon-down allowlisted, daemon-up passthrough, audit-record emission)
- `tests/test_mesh_dispatch_governed.py` — **WP-P0-002** (fail-closed secret, verdict required, verdict validated node-side)
- `tests/test_mesh_auth_binding.py` — **WP-P0-002** (no-token refusal, token→node binding, header transport, /nodes auth)
- `tests/test_node_governance.py` (under `nodes/windows/umh_node/tests/`) — **WP-P0-003** (risk derivation, path containment, argv policy, deny-by-default, role-envelope rejection)
- `tests/test_cc_webhook_auth.py` — **WP-P0-004** (unauth reject, auth pass)
- `tests/test_import_smoke_router_environments.py` — **WP-P0-008** (import every module in `substrate/control_plane/router/` and `nodes/environments/`)
- `tests/test_governance_fail_closed.py` + `tests/test_trace_persistence_deadletter.py` — **WP-P0-009**
- `tests/test_eos_tenant_isolation.py` — **WP-P0-010** (two-tenant fixture, cross-tenant rows not returned)

### EXISTING suites to EXTEND (no new file)
- `tests/test_gate3_governed_work_runtime.py` (present, 945 lines) — **WP-P0-007** adds a `submit_work` round-trip + a CommandRuntime approve/reject test.

### EXISTING suites to RE-RUN only
- `tests/test_p1_phase2_bridge.py` — WP-P0-001
- `tests/test_eos_projection.py` — WP-P0-010
- `tests/test_trace_recorder.py` — WP-P0-009

### Gate scripts (all exist, re-run)
- `scripts/check_ungoverned_mutations.py`, `scripts/check_dependency_direction.py` — WP-P0-001
- `scripts/check_mesh_relay_firewall.py` — WP-P0-002

**P6 is the test-hardening phase.** The exhaustive contract-test build-out, marker taxonomy, CI, and honest certification suites all land in P6. WP-P0-011 only restores *collection* so the rest of the plan has a harness; it wires a `pytest --collect-only` pre-commit gate but the full CI suite is a P6 deliverable.

---

## 11. Risky Packets and Why

### Risk-register top entries (from `UMH_ONE_SHOT_CONVERGENCE_GAP_ANALYSIS.md`)

| # | Risk | Likelihood / Impact | Mitigation |
|---|---|---|---|
| 1 | Daemon outage silently degrades all 360 governed mutation sites to `completed_ungoverned` | High (any restart) / Critical | **WP-P0-001** |
| 2 | Mesh `/dispatch` reachable with no auth when `UMH_MESH_RELAY_SECRET` unset → arbitrary remote shell | Medium / Critical | **WP-P0-002** |
| 3 | Caller-declared risk class + deny-pattern-free executor shell adapter → destructive commands pass at default caps | High (structural) / Critical | **WP-P0-003** |
| 4 | Two broken governed paths — DO layer creates no packets, operator approve/reject fails (governance theater) | Certain / High | **WP-P0-007** |
| 5 | Nightly autonomous write-enabled Claude agent on the production repo outside all governance | Certain / High | **WP-P0-005** |
| 6 | Unauthenticated 0.0.0.0 webhook carrying MFA codes + CC-session control | Medium / High | **WP-P0-004** |
| 7 | EOS cross-tenant task read (`user_id` accepted, never bound) | Certain under multi-tenant / Critical | **WP-P0-010** |
| 8 | Approval fragmentation (4 machines / 3 channels / 11 surfaces) | Certain (structural) / High | WP-P1-007, WP-P5-004 |
| 11 | Type divergence accumulates invisibly (gate staged-only, full scan fails today) | Certain / High | WP-P2-001, WP-P2-003, WP-P6-014 |
| 12 | Rival spines carry live traffic (legacy sync ExecutionSpine in deployed Discord path) | Certain / High | WP-P1-001, WP-P1-006 |
| 13 | No StateCommit / unified commit log; fail-open path leaves no record | Certain (structural) / High | WP-P1-013 |
| 16 | Test suite cannot collect, no CI, misleading suites create false confidence | Certain / High | WP-P0-011, WP-P6-004/009/010 |
| 20 | Convergence-execution risk: 149 packets touch core infra without acceptance scaffolding | Medium / High | Sequencing (P0 test packets first) + §19 No-Go list |

### Every HIGH/CRITICAL P0 packet — the specific danger

- **WP-P0-001 (HIGH, control-plane trust boundary).** Fail-open→fail-closed is a **live behavior change**: previously-ungoverned mutations now queue/reject when the daemon is down. Blast radius = all 360 mutation routes (filesystem, SSH remote writes, signal intake). The danger is an availability regression if the degraded-mode allowlist is mis-scoped. Mitigated by `degraded_mode_allowed` defaulting **false**.
- **WP-P0-002 (HIGH, mesh + remote-actuation trust boundary).** Wrong verdict/binding wiring can **strand or expose the executor node**. Blast radius = arbitrary remote shell/keystroke on any connected mesh node.
- **WP-P0-003 (HIGH, executor-node trust boundary).** Deny-by-default can **block legitimate executor operations** until allowlists are populated. Blast radius = executor availability; the upside is destructive commands (`rm -rf`, `..`-traversal) rejected node-side.
- **WP-P0-005 (HIGH, production-repo write surface).** Removes an autonomous write path that **may have silent dependencies**; the alert path is currently dead code (`interface.discord` absent), so failures are invisible today.
- **WP-P0-009 (HIGH, modifies CONFIRMED_RUNTIME governance + trace modules).** Fail-closed quality evaluation can **newly block work that previously passed by default** — a behavioral change to a live gate. `trace.py`/`feedback.py` are CONFIRMED_RUNTIME — additive changes only.
- **WP-P0-010 (CRITICAL for planning — schema-bearing).** Tenant-isolation semantics + a possible schema migration in a production-adjacent database. The vendored `agents` table has no owner column, so per-user scoping is unimplementable through the current join path — forcing either a source-repo schema change (CRITICAL) or a task→user join route (MEDIUM). Treat as CRITICAL.
- **WP-P0-013 (HIGH, live WS trust boundary).** Wrong validation **bricks voice/vision**; relay processes are host processes (Docker restart does not reach them), so rollback must roll both ends together.

MEDIUM P0 packets (004, 006, 007, 008, 011, 012, 014) are lower-blast-radius single-surface fixes; WP-P0-011 is LOW; WP-P0-015 is LOW if fenced, HIGH if governed.

---

## 12. Convergence-Before-Features Gate

**Explicit statement:** No projection feature work begins until P0, P1, P2, and P3 convergence lands. **P4 (projection capability build-out) is the earliest projection-facing surface** in the entire plan. Everything before P4 is substrate/spine/type/ontology convergence — none of it ships a new projection capability.

**Why:** projections cannot be built on fail-open trust boundaries or broken governed paths (P0); they activate against the converged spine + single approval authority (P1); their domain models inherit canonical platform types (P2); and the four-layer separation must be enforced before L3 projection entities can be moved out of substrate and wired to the L4 resolution/writeback contracts (P3).

**Gating packets (P4 entry gate, verbatim from P4 entry criteria):** **WP-P3-004** (projection registration/port), **WP-P3-013**, and **WP-P3-009** (writeback schema) must all be landed. The EOS approval-loop bridge (WP-P4-009) additionally targets the UMH approval authority delivered by **WP-P1-007**.

The only sanctioned pre-P4 client work is **P5 wave 1** (cockpit IA + state layer), which may begin once **WP-P1-007** merges — but that is cockpit information architecture, not projection feature build, and it is bound by the 2026-07-03 layout lock.

---

## 13. Smallest Safe First Implementation Batch — Batch 1: P0 Runtime Safety

**Batch 1 = WP-P0-001, WP-P0-002, WP-P0-007, WP-P0-010, WP-P0-011.**

**Within-batch ordering:** WP-P0-002 depends on WP-P0-001, so the order is **001 → 002**; the other three (007, 010, 011) are independent and run in parallel with each other and with the 001→002 chain.

**Why exactly these five (and not the other ten P0 packets):**

1. **WP-P0-001** — the keystone. It is the single largest live danger (Risk #1: any daemon restart silently ungoverns all 360 mutation sites) and it blocks WP-P0-002, WP-P0-003, and every P1 spine packet. Nothing downstream is trustworthy until it lands. Must be first.
2. **WP-P0-002** — Risk #2, the second Critical live danger (unauthenticated arbitrary remote shell). It is the immediate dependent of 001 and the only Wave-2 packet, so pulling it into Batch 1 completes the mesh trust boundary in the same safety sweep.
3. **WP-P0-007** — Risk #4, *certain* and *broken today*: the governed DO layer creates no real packets and every operator approve/reject returns an error dict (governance theater). It requires **NO approval** (pure defect fix) and is a two-file change — the cheapest possible restoration of a core guarantee. Fixing it early makes every later packet's approval-path verification meaningful.
4. **WP-P0-010** — Risk #7, *certain under multi-tenant* / Critical: cross-tenant data read. It is the one schema-bearing CRITICAL migration in P0; landing it in Batch 1 forces the migration-discipline muscle (row counts, down-migration-first) before it recurs in P1–P5.
5. **WP-P0-011** — the harness. `pytest` cannot collect (3 ImportErrors, INTERRUPTED across 15,017 tests) and no CI runs pytest. Without it, none of the other four packets can be verified by the suite, and the sanctioned P6 test-infra overlap cannot start. It is LOW risk, NO approval, and unblocks everything. It is the *entry gate proof* for the whole batch.

These five are the intersection of **highest present-tense danger**, **the critical-path root**, **the verification harness**, and **the cheapest-to-revert defect fixes**. They deliberately exclude the auth/webhook/WS/IPC/service packets (004, 006, 012, 013, 014, 015) — real but lower-blast-radius single-surface fixes that belong to Batch 2 — and WP-P0-003/005/008/009, which either depend on Batch 1 (003 → 002) or are independent single-surface hardening best sequenced after the harness and keystone are proven.

---

## 14. Exact Commands / Tests After Each P0 Batch-1 Packet

Run `python3 -c "import sys; sys.path.insert(0,'/opt/OS'); import runtime"` before any deploy; never restart all services simultaneously. Docker is Python 3.11 only.

### WP-P0-001 — fail-close governed_mutation
```bash
# import + dependency-direction laws
python3 -m py_compile substrate/organism/mutation_router.py transports/api/governed.py substrate/organism/mutation_registry.py
python3 scripts/check_dependency_direction.py          # must pass (substrate must not import transports)
# CREATE THEN RUN the new fail-closed suite
#   tests/test_governed_mutation_fail_closed.py  (does not exist yet — create per acceptance)
pytest tests/test_governed_mutation_fail_closed.py -q
# re-run the ungoverned-mutation full scan
python3 scripts/check_ungoverned_mutations.py --all    # no remaining completed_ungoverned for non-LOW risk
# existing bridge suite
pytest tests/test_p1_phase2_bridge.py -q
# manual daemon-down proof: stop daemon, attempt a non-LOW mutation, assert 503/queued + target state unchanged
```

### WP-P0-002 — mesh trust boundary (bases on WP-P0-001)
```bash
python3 -m py_compile transports/api/cockpit_workstation_control_routes.py transports/node_mesh/server.py transports/node_mesh/integration/handlers.py substrate/meta_ide/browser_evidence_collector.py nodes/windows/umh_node/config.py
# CREATE THEN RUN both new mesh suites
#   tests/test_mesh_dispatch_governed.py  and  tests/test_mesh_auth_binding.py  (create per acceptance)
pytest tests/test_mesh_dispatch_governed.py tests/test_mesh_auth_binding.py -q
# mesh relay firewall gate
python3 scripts/check_mesh_relay_firewall.py
# mesh auth checks (manual proofs required by acceptance):
#   - start relay with UMH_MESH_RELAY_SECRET unset → process exits / endpoint returns 503
#   - WS connect with zero tokens configured → refused
#   - token bound to node A registers as node B → rejected
#   - /nodes and /health without bearer → 401
#   - grep -rn "_http_dispatch\|POST :8095/dispatch" transports/ substrate/ nodes/  → no raw relay path in callers
```

### WP-P0-007 — broken governed paths
```bash
python3 -m py_compile substrate/organism/governed_work_runtime.py substrate/organism/command_runtime.py
# EXTEND existing suite (no new file): add submit_work round-trip + CommandRuntime approve/reject
pytest tests/test_gate3_governed_work_runtime.py -q
# confirm the two corrected call sites resolve and do NOT swallow:
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from substrate.organism.work_packet_engine import WorkPacketEngine; assert hasattr(WorkPacketEngine,'create_packet_from_intent')"
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from substrate.organism.universal_work_queue import UniversalWorkQueue; assert hasattr(UniversalWorkQueue,'update_packet_status')"
```

### WP-P0-010 — EOS tenant scope
```bash
python3 -m py_compile projections/eos/integration/tables.py
# CREATE THEN RUN the tenant-isolation test (two seeded tenants; each poll returns only its own rows)
#   tests/test_eos_tenant_isolation.py  (create per acceptance)
pytest tests/test_eos_tenant_isolation.py -q
# existing projection suite
pytest tests/test_eos_projection.py -q
# query-diff proof: show WHERE clause binds user_id (no tautological predicate)
# IF owner-column/schema route chosen: check row counts before/after; down-migration written first
```

### WP-P0-011 — pytest collection
```bash
# BEFORE (must show 3 errors, INTERRUPTED):
python3 -m pytest tests --collect-only -q
# AFTER repair (fix against real symbols; NO back-compat aliases):
#   tests/test_c23b_production_benchmarks.py : OutcomeRecord  -> BenchmarkOutcomeRecord
#   tests/test_c31_phase6.py                 : SessionStatus  -> DevSessionStatus
#   tests/test_execution_coordinator.py      : ExecutionMode  -> NO direct rename; choose intended enum
#                                              (ExecutionPlanStatus/...) OR delete under dormant-classification
python3 -m pytest tests --collect-only -q               # MUST exit 0, 0 errors, stable collected count
# pre-commit collect-only gate blocks a synthetic broken-import test file
```

---

## 15. Rollback Plan for Each P0 Batch-1 Packet (verbatim)

- **WP-P0-001:** *git revert of mutation_router + governed.py + MutationSpec field; the transport shim preserves the old call signature so callers are unaffected by rollback; the allowlist flag defaults false so revert restores prior behavior.*
- **WP-P0-002:** *revert the five files; prior fail-open relay/WS behavior restored (documented regression, acceptable only for emergency rollback).*
- **WP-P0-007:** *revert both files.*
- **WP-P0-010:** *query change: git revert. Schema change: down-migration written before up-migration is applied.*
- **WP-P0-011:** *git revert; deleted tests recoverable from git history.*

---

## 16. Acceptance Criteria for Each P0 Batch-1 Packet (verbatim)

- **WP-P0-001:** *with the daemon stopped, a mutation without `degraded_mode_allowed` returns 503/queued and performs no write (verified by asserting target state unchanged); a flagged low-risk mutation succeeds and emits a degraded trace event; with the daemon running, behavior unchanged; grep shows no remaining `completed_ungoverned` execution path for non-LOW risk; `scripts/check_dependency_direction.py` passes.*
- **WP-P0-002:** */dispatch with unset secret refuses at startup (process exits or endpoint returns 503); a WS connection with no tokens configured is refused; a token bound to node A cannot register as node B; the token is read from a header; /nodes and /health require auth; a remote terminal create/send produces a `remote_node_exec` trace event with an attached verdict id that the node validates before executing; a dispatch with a missing/invalid verdict for a write-class capability is rejected node-side; the raw relay path is gone from all callers (grep clean).*
- **WP-P0-007:** *`submit_work` creates a real packet (id is a packet id, not a raw uuid) and classifier risk is applied; a packet approve/reject via CommandRuntime returns success, not an error dict; the new round-trip test passes.*
- **WP-P0-010:** *query text binds `user_id` (no tautological predicate); regression test with two seeded tenants shows each poll returns only its own rows; row counts checked before/after any migration.*
- **WP-P0-011:** *`pytest tests --collect-only -q` exits 0 with 0 errors; collected count reported and stable; pre-commit gate blocks a synthetic broken-import test file.*

---

## 17. PR Strategy

**Recommendation: NOT one mega-PR.** One PR per P0 packet for the five Batch-1 packets — each small, revertible, and independently reviewable. This matches the per-packet rollback plans (a mega-PR cannot honor "revert both files" or "revert the five files" cleanly) and lets the human-approval gate operate per packet.

**Stacking:** WP-P0-002's PR **bases on WP-P0-001's branch** (it depends on the fail-closed verdict semantics). The other three (007, 010, 011) branch independently off `umh-convergence-audit`.

**Base branch:** All five branch off **`umh-convergence-audit`**, not `main`. Reason: this is a scoped convergence effort with its own worktree and audit artifacts; keeping the P0 stack on the convergence branch lets the whole batch be reviewed and gated as a unit before it merges to `main`, and it keeps the 149-packet effort from interleaving with unrelated `main` traffic. WP-P0-002 additionally stacks on WP-P0-001 within that branch.

**Recommended branch names:**
- `fix/p0-001-fail-close-governed-mutation`
- `fix/p0-002-mesh-trust-boundary` (stacked on `fix/p0-001-fail-close-governed-mutation`)
- `fix/p0-007-broken-governed-paths`
- `fix/p0-010-eos-tenant-scope`
- `fix/p0-011-pytest-collection`

Cockpit-touching P0 packets in later batches (012, 013, 014) must deploy only via `bash cockpit/deploy.sh` — never raw `flyctl deploy`.

---

## 18. Human Review Checklist (per Batch-1 packet, before merge)

**Universal (every packet):** all 9 repo laws respected — (1) no raw subprocess in gated dirs [CPU gate]; (2) cockpit deploy only via `cockpit/deploy.sh`; (3) Python 3.11 syntax only; (4) dependency direction projections→transports→adapters→substrate (substrate imports nothing upward); (5) type coherence via `canonical_types.py` (any new type registered, resolves to a real symbol); (6) no instance context in substrate; (7) projection boundary respected; (8) credentials via 1Password `op run` (no plaintext); (9) deterministic-first (rules/lookup before any LLM). Approval obtained where required (001, 002, 010 require approval; 007, 011 do not). No silent except-pass.

- **WP-P0-001:** Fail-closed **proven with the daemon down** — a non-LOW mutation returns 503/queued and the target state is provably unchanged (before/after snapshot). A flagged low-risk mutation emits a degraded trace event. `grep` shows zero remaining `completed_ungoverned` path for non-LOW risk. `check_dependency_direction.py` passes (substrate does not import transports; the transport shim is delegation-only). MutationSpec field registered in `canonical_types.py`. Allowlist flag defaults false.
- **WP-P0-002:** **No unauthenticated mutation surface remains** — relay refuses with secret unset; WS refuses with zero tokens; token→node binding enforced (A-as-B rejected); token in header not URL; `/nodes` + `/health` require bearer. A governed remote exec carries a verdict id validated **node-side**; a verdict-less write dispatch is rejected node-side. Raw relay path grep-clean. Rebases cleanly on WP-P0-001.
- **WP-P0-007:** `submit_work` creates a real packet (packet id, not raw uuid) with classifier risk applied; CommandRuntime approve/reject returns success, not an error dict. The corrected calls **raise or return a typed error** — no silent swallow reintroduced. Fix anchors to the `UniversalWorkQueue` call at `command_runtime.py:896` specifically (grep over-matches — 18 other classes define `update_status`).
- **WP-P0-010:** **Tenant scope enforced** — query binds `user_id` (no tautological predicate); two-tenant fixture proves no cross-tenant rows. If the owner-column/schema route was taken: row counts checked before/after, down-migration written before up-migration, Breaking Change Process followed (no ad-hoc DDL against live Neon EOS). No other query's scope widened.
- **WP-P0-011:** **Collection green** — `pytest --collect-only` exits 0 with 0 errors and a stable count. Stale symbols repaired against **real** current symbols (no back-compat aliases added to substrate). `ExecutionMode` specifically: confirm the reviewer accepts the chosen intended enum OR the dormant-classification deletion (it has no 1:1 rename). Pre-commit collect-only gate blocks a synthetic broken-import file.

---

## 19. No-Go List

From the master No-Go list (`UMH_ONE_SHOT_CONVERGENCE_GAP_ANALYSIS.md` §5) plus plan-specific constraints:

1. **No mega-rewrite.** Declare owners and migrate callers. The spine, integration contract, and Meta IDE primitives are sound and reused.
2. **No file moves/deletes** without a recorded dormant disposition (PROMOTE/MERGE/ISOLATE/ARCHIVE/DELETE). This is a PLAN-ONLY task — no moves/deletes here at all.
3. **No projection features** before P4. P0–P3 convergence gates every projection-facing surface (§12).
4. **No cockpit deploys outside `bash cockpit/deploy.sh`.** Never raw `flyctl deploy`.
5. **No ungoverned migration scripts.** Migration steps route through governed mutation or land as reviewed commits with rollback plans; the 6 schema-bearing packets carry CRITICAL migration discipline (§8).
6. **No touching frozen `PLATFORM_SPEC` contracts without an RFC** (Breaking Change Process). Description corrections are documentation, not RFCs.
7. **No raw `subprocess` in gated dirs** (substrate/, adapters/, transports/, services/) — `gated_subprocess_run()`/`gated_popen()` only. `nodes/` being outside GATED_DIRS is not a license.
8. **No starting P1 spine convergence until P0 is green.** P1 assumes fail-closed boundaries (WP-P0-001) and an authenticated webhook channel (WP-P0-004); starting P1 early builds on unsafe ground.
9. **No new parallel implementations during convergence** — no new approval store, work-packet type, node model, event bus, or API entrypoint, including "temporary" shims that outlive their packet. Every bridge names its removal milestone.
10. **No disabling/grandfathering enforcement gates to make packets pass** — exemption lists only shrink.
11. **No production restarts of all services simultaneously; no Docker rebuilds for Python-only changes** — per-service restart with clean-startup log verification.
12. **No instance context added to platform files; no plan-file rewrites; no worktree/branch debris.** Plans are immutable (archive then re-plan); worktrees removed after merge.
13. **No physical-actuation capability work** until the safety-envelope/e-stop/rollback contract exists (WP-P2-030 before any PHYSICAL_WORLD adapter).
14. **No deploying dormant surfaces "because they exist"** — Hono stack, goal_api/higgsfield_webhook/local_bridge_server stay down until their packets wire or retire them.

---

## 20. Final Recommendation

Implement **Batch 1 next: WP-P0-001, WP-P0-002, WP-P0-007, WP-P0-010, WP-P0-011** — five small, independently-revertible PRs off `umh-convergence-audit`, with WP-P0-002 stacked on WP-P0-001 (order 001→002; 007/010/011 parallel).

**Entry gate for the batch (both must hold before any Batch-1 PR merges):**
1. **Green collection** — `pytest tests --collect-only -q` exits 0 (delivered by WP-P0-011; without it nothing else can be verified by the suite).
2. **Daemon-down proof** — WP-P0-001's fail-closed behavior is demonstrated with the daemon stopped (non-LOW mutation returns 503/queued, target state provably unchanged).

**Why this batch is the line between vision-era and operational UMH:** it converts the platform's central guarantee from "governed when the daemon happens to be up" into "governed always, fail-closed, with a working test harness to prove it" — the exact moment the control plane stops being a demo of governance and becomes a control plane that actually holds.

---

## Batch 1 at a Glance

| Packet | Boundary | Approval | New tests | PR branch |
|---|---|---|---|---|
| **WP-P0-001** | mutation (control plane / choke point) | YES | CREATE `tests/test_governed_mutation_fail_closed.py`; re-run `check_ungoverned_mutations.py --all`, `test_p1_phase2_bridge.py` | `fix/p0-001-fail-close-governed-mutation` |
| **WP-P0-002** | mesh (also mutation, auth) | YES | CREATE `tests/test_mesh_dispatch_governed.py`, `tests/test_mesh_auth_binding.py`; re-run `check_mesh_relay_firewall.py` | `fix/p0-002-mesh-trust-boundary` (stacked on p0-001) |
| **WP-P0-007** | mutation (governed work runtime / approval) | NO | EXTEND `tests/test_gate3_governed_work_runtime.py` (submit_work round-trip + approve/reject) | `fix/p0-007-broken-governed-paths` |
| **WP-P0-010** | tenant (data-plane cross-tenant read; schema-bearing CRITICAL) | YES | CREATE `tests/test_eos_tenant_isolation.py`; re-run `test_eos_projection.py` | `fix/p0-010-eos-tenant-scope` |
| **WP-P0-011** | test-infra | NO | Repair 3 existing files + wire `pytest --collect-only` pre-commit gate | `fix/p0-011-pytest-collection` |
