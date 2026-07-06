# UMH Work Packet Backlog — Convergence Remediation Plan

Generated 2026-07-03 from the 17 Phase-1 evidence ledgers (A, B1-B4, C1-C3, D1-D2, E1-E3, F1-F2, G, H) via three draft backlog parts, cross-group deduped, renumbered, and mechanically reconciled against the 270-gap index.
Repo under audit: `/opt/OS/.claude/worktrees/umh-convergence-audit` (all paths repo-relative). UMH here is the human-governed agentic operating control plane for desired-state reconciliation — the substrate beneath the cockpit/EOS/CreatorOS/LyfeOS surfaces, not any of those surfaces.
Layer legend used throughout: L1 External Operational Reality Model · L2 UMH Platform Metamodel · L3 Projection Domain Models · L4 Semantic Grounding / Mapping Layer.

## Front matter

- **Total work packets: 149** (162 draft packets, 13 cross-group merges).
- **Packets per phase:** P0: 15, P1: 21, P2: 30, P3: 20, P4: 20, P5: 19, P6: 24.
- **Gap coverage:** all 270 gap IDs from the Phase-1 index map to exactly one packet (reconciliation table at the end; verified mechanically).
- **Packet classification (by primary artifact):** code-touching 134, test-only 10 (WP-P6-002, WP-P6-005, WP-P6-006, WP-P6-007, WP-P6-008, WP-P6-009, WP-P6-010, WP-P6-011, WP-P6-013, WP-P6-015), documentation-only 4 (WP-P3-003, WP-P4-006, WP-P4-020, WP-P6-023), schema-only 1 (WP-P2-020). Schema-bearing code packets (CRITICAL migration discipline): WP-P0-010, WP-P1-019, WP-P3-009, WP-P3-011, WP-P4-009, WP-P5-017.
- **Packets requiring human approval (71):** WP-P0-001, WP-P0-002, WP-P0-003, WP-P0-004, WP-P0-005, WP-P0-006, WP-P0-009, WP-P0-010, WP-P0-013, WP-P0-014, WP-P0-015, WP-P1-001, WP-P1-003, WP-P1-005, WP-P1-006, WP-P1-007, WP-P1-008, WP-P1-009, WP-P1-010, WP-P1-011, WP-P1-012, WP-P1-013, WP-P1-014, WP-P1-017, WP-P1-019, WP-P1-020, WP-P1-021, WP-P2-002, WP-P2-005, WP-P2-010, WP-P2-011, WP-P2-014, WP-P2-018, WP-P2-022, WP-P2-024, WP-P2-025, WP-P2-027, WP-P2-030, WP-P3-001, WP-P3-002, WP-P3-003, WP-P3-004, WP-P3-005, WP-P3-007, WP-P3-009, WP-P3-011, WP-P3-012, WP-P3-015, WP-P3-016, WP-P3-020, WP-P4-001, WP-P4-002, WP-P4-003, WP-P4-004, WP-P4-005, WP-P4-007, WP-P4-009, WP-P4-013, WP-P4-014, WP-P4-016, WP-P4-019, WP-P4-020, WP-P5-001, WP-P5-003, WP-P5-004, WP-P5-005, WP-P5-015, WP-P5-017, WP-P5-019, WP-P6-017, WP-P6-018.

### Cross-group dedupe record (13 merges)

| Final packet | Merged drafts | Defect |
|---|---|---|
| WP-P0-001 | WP-DRAFT-PART1-001 + WP-DRAFT-PART2-002 | fail-open governed_mutation() (spine + primitives groups) |
| WP-P0-002 | WP-DRAFT-PART1-002 + WP-DRAFT-PART1-037 | mesh auth fail-open + ungoverned dispatch (spine + trust groups) |
| WP-P0-008 | WP-DRAFT-PART2-001 + WP-DRAFT-PART1-042 | WorkPacket rename breakage + registry/doc drift (primitives + spine groups) |
| WP-P1-001 | WP-DRAFT-PART1-016 + WP-DRAFT-PART2-006 | rival execution spines / event backbones |
| WP-P1-007 | WP-DRAFT-PART1-013 + WP-DRAFT-PART2-012 | approval fragmentation — server-side authority + canonical type |
| WP-P2-002 | WP-DRAFT-PART1-018 + WP-DRAFT-PART2-016 | risk-taxonomy + same-name collision remediation |
| WP-P2-010 | WP-DRAFT-PART1-023 + WP-DRAFT-PART2-022 | runtime-node identity fragmentation |
| WP-P2-011 | WP-DRAFT-PART1-022 + WP-DRAFT-PART2-023 | adapter-contract fragmentation |
| WP-P3-004 | WP-DRAFT-PART2-033 + WP-DRAFT-PART3-010 | projection homonym / port / id fragmentation |
| WP-P3-009 | WP-DRAFT-PART2-045 + WP-DRAFT-PART3-020 | undeclared umh_status/umh_outcomes writeback schema |
| WP-P3-011 | WP-DRAFT-PART2-036 + WP-DRAFT-PART3-021 | entity/identity resolution registry |
| WP-P3-012 | WP-DRAFT-PART1-026 + WP-DRAFT-PART2-048 | vendored projection repo trim + schema ownership |
| WP-P3-013 | WP-DRAFT-PART2-044 + WP-DRAFT-PART3-011 | substrate→projections import inversion in product_connections |

Approval-fragmentation note: the server-side authority is WP-P1-007; the cockpit-client single queue (WP-P5-004) and the EOS product-approval mapping (WP-P4-009) remain separate packets because they deliver different layers of the same convergence and depend on WP-P1-007.

### Parallelization plan (waves per phase)

Waves are computed from intra-phase Dependencies. Packets in the same wave may run concurrently subject to (a) their own `Parallelizable` field and (b) not touching the same files; packets marked `Parallelizable: no` serialize against same-file packets even within a wave.

- **P0** — Wave 1: WP-P0-001, WP-P0-004, WP-P0-005, WP-P0-006, WP-P0-007, WP-P0-008, WP-P0-009, WP-P0-010, WP-P0-011, WP-P0-012, WP-P0-013, WP-P0-014, WP-P0-015 · Wave 2: WP-P0-002 · Wave 3: WP-P0-003
- **P1** — Wave 1: WP-P1-001, WP-P1-002, WP-P1-005, WP-P1-014, WP-P1-015, WP-P1-018, WP-P1-020 · Wave 2: WP-P1-003, WP-P1-006, WP-P1-007, WP-P1-008, WP-P1-009, WP-P1-011, WP-P1-012, WP-P1-013 · Wave 3: WP-P1-004, WP-P1-010, WP-P1-016, WP-P1-017, WP-P1-019, WP-P1-021
- **P2** — Wave 1: WP-P2-001, WP-P2-005, WP-P2-021, WP-P2-024, WP-P2-025, WP-P2-026, WP-P2-027, WP-P2-028, WP-P2-029 · Wave 2: WP-P2-002, WP-P2-004, WP-P2-006, WP-P2-007, WP-P2-009, WP-P2-012, WP-P2-014, WP-P2-017, WP-P2-018, WP-P2-020, WP-P2-022 · Wave 3: WP-P2-003, WP-P2-008, WP-P2-010, WP-P2-011, WP-P2-016, WP-P2-019, WP-P2-030 · Wave 4: WP-P2-013, WP-P2-015, WP-P2-023
- **P3** — Wave 1: WP-P3-001, WP-P3-002, WP-P3-003, WP-P3-004, WP-P3-006, WP-P3-007, WP-P3-008, WP-P3-009, WP-P3-018, WP-P3-019, WP-P3-020 · Wave 2: WP-P3-005, WP-P3-010, WP-P3-011, WP-P3-013, WP-P3-015 · Wave 3: WP-P3-012, WP-P3-014, WP-P3-016, WP-P3-017
- **P4** — Wave 1: WP-P4-001, WP-P4-002, WP-P4-003, WP-P4-004, WP-P4-005, WP-P4-006, WP-P4-007, WP-P4-008, WP-P4-013, WP-P4-014, WP-P4-016, WP-P4-017, WP-P4-018, WP-P4-019, WP-P4-020 · Wave 2: WP-P4-009, WP-P4-010, WP-P4-011, WP-P4-012, WP-P4-015
- **P5** — Wave 1: WP-P5-001, WP-P5-002, WP-P5-016, WP-P5-017, WP-P5-019 · Wave 2: WP-P5-003 · Wave 3: WP-P5-004, WP-P5-013 · Wave 4: WP-P5-005 · Wave 5: WP-P5-006, WP-P5-007, WP-P5-008, WP-P5-009, WP-P5-010, WP-P5-011, WP-P5-012, WP-P5-014, WP-P5-015 · Wave 6: WP-P5-018
- **P6** — Wave 1: WP-P6-001, WP-P6-002, WP-P6-003, WP-P6-005, WP-P6-006, WP-P6-007, WP-P6-011, WP-P6-013, WP-P6-014, WP-P6-015, WP-P6-016, WP-P6-017, WP-P6-018, WP-P6-019, WP-P6-020, WP-P6-021, WP-P6-022, WP-P6-023, WP-P6-024 · Wave 2: WP-P6-004, WP-P6-008, WP-P6-009, WP-P6-010 · Wave 3: WP-P6-012

### Cross-phase prerequisites

- Phases execute in order P0 → P6, with two sanctioned overlaps: P6 test-infrastructure packets (WP-P6-001…004) may start once WP-P0-011 lands; P5 client work may begin its wave 1 once WP-P1-007 is merged.
- Keystone packets on the critical path: WP-P0-001 → WP-P1-001 → WP-P1-007 → {WP-P2-001, WP-P2-002} → WP-P3-004 → WP-P4-004 → WP-P5-005.
- **Forward coordination dependencies** (a packet lands its own scope in its phase; integration with the referenced later packet completes when that packet lands): WP-P0-002 → WP-P1-001; WP-P0-002 → WP-P2-010; WP-P0-003 → WP-P2-002; WP-P0-005 → WP-P1-001; WP-P0-008 → WP-P2-002; WP-P0-010 → WP-P3-009; WP-P0-014 → WP-P5-016; WP-P1-005 → WP-P2-022; WP-P1-018 → WP-P2-010; WP-P1-020 → WP-P2-030; WP-P2-007 → WP-P3-007; WP-P2-025 → WP-P6-022; WP-P2-028 → WP-P4-010; WP-P2-030 → WP-P4-002; WP-P3-009 → WP-P4-004; WP-P3-013 → WP-P4-004; WP-P4-012 → WP-P5-017.

### Packet field key

Every packet carries: Closes (gap IDs) · Current state (evidence with path:line) · Desired state · Files to inspect / likely modified · Forbidden files/actions (repo laws) · Dependencies (final IDs) · Risk class (LOW additive / MEDIUM existing-method / HIGH core infra / CRITICAL schema-RLS-data) · Approval · Acceptance criteria · Proof required · Tests · Rollback plan · Expected output · Parallelizable · Phase.

---

## P0 — Safety-critical — stop the bleeding (15 packets)

**Objective.** Close the fail-open trust boundaries and the defects that corrupt or bypass governance today: the ungoverned mutation fallback, the open mesh/webhook/WS surfaces, the silently broken governed paths, the cross-tenant read, and the broken test collection.

**Entry criteria.** None — start immediately. All wave-1 packets are independently executable.

**Exit criteria.** Every control-plane entry point fails closed; the two silently broken governed paths work; pytest collection is green; no unauthenticated mutation surface (HTTP, WS, IPC, mesh, webhook) remains reachable.

### WP-P0-001: Fail-close governed_mutation() and move the mutation choke point below the transport layer
- Closes: GAP-C1-003, GAP-C2-001, GAP-B1-008, GAP-B3-001, GAP-B3-014
- Current state: The documented single mutation entry point `governed_mutation()` lives in the transport layer (`transports/api/governed.py:65`) and fails open: when the organism daemon is unavailable (`_get_router()` returns None), `transports/api/governed.py:91-111` executes `execute_fn()` directly with status `completed_ungoverned` (docstring at lines 74-80 states the fallback explicitly), bypassing spine, ledger, and proof. All 360 Python `governed_mutation()` call sites — filesystem writes, remote SSH writes, signal intake, pipeline submit — degrade to direct ungoverned execution with only a `logger.warning`. Project docs (CLAUDE.md "All state changes through governed_mutation()") and internal briefs claim substrate ownership (`substrate/organism/governed_spine.py` has no such def; the spine is consumed via `substrate/organism/mutation_router.py:29,80`) — the canonical control-plane choke point is transport-owned, inverting layer authority.
- Desired state: fail-closed default — non-LOW-risk mutations are rejected (503) or queued when the control plane is down, and no state change occurs. An explicit per-MutationSpec `degraded_mode_allowed` flag (default false) gates a narrow allowlist of read-adjacent / LOCAL_RUNTIME / low-risk operations; any permitted degraded execution emits a mandatory typed audit record (trace event marked `degraded`) with alerting. The choke-point contract moves to substrate (extend `substrate/organism/mutation_router.py`); `transports/api/governed.py` becomes a thin delegation shim; docs corrected to the real location.
- Files to inspect: transports/api/governed.py (all 111 lines); substrate/organism/mutation_router.py:93-126; substrate/organism/mutation_registry.py (MutationSpec definition); substrate/organism/governed_spine.py; substrate/organism/execution_ledger.py; callers of governed_mutation (grep transports/ and services/).
- Files likely modified: substrate/organism/mutation_router.py (fail-closed entry point); transports/api/governed.py (delegation shim); substrate/organism/mutation_registry.py (add `degraded_mode_allowed` field); CLAUDE.md / architecture docs referencing the location.
- Forbidden files/actions: substrate/ must not import transports/ (the move is downward only); no silent except-pass around the fallback; keep the MutationSpec type change registered in `substrate/canonical_types.py`; deterministic-first — the fail-closed decision is a rules table keyed on risk class, no LLM involvement; Python 3.11 syntax only; never restart all services simultaneously when deploying.
- Dependencies: none
- Risk class: HIGH (core control-plane trust boundary)
- Approval required: yes — fail-open→fail-closed semantics change live behavior: mutations that previously executed ungoverned will queue or reject when the daemon is down; operator must accept the availability trade-off.
- Acceptance criteria: with the daemon stopped, a mutation without `degraded_mode_allowed` returns 503/queued and performs no write (verified by asserting target state unchanged); a flagged low-risk mutation succeeds and emits a `degraded` trace event; with the daemon running, behavior unchanged; grep shows no remaining `completed_ungoverned` execution path for non-LOW risk; `scripts/check_dependency_direction.py` passes.
- Proof required: before/after transcript of a mutation attempt with the daemon stopped (ungoverned execution before, fail-closed after); trace-event records for one blocked and one allowed degraded mutation; execution-ledger entry for the audit record; before/after state snapshot of a filesystem-write target proving no write on 503.
- Tests to add/run: new tests/test_governed_mutation_fail_closed.py (daemon-down blocked per risk class, daemon-down allowlisted, daemon-up passthrough, audit-record emission); re-run scripts/check_ungoverned_mutations.py --all; run tests/test_p1_phase2_bridge.py.
- Rollback plan: git revert of mutation_router + governed.py + MutationSpec field; the transport shim preserves the old call signature so callers are unaffected by rollback; the allowlist flag defaults false so revert restores prior behavior.
- Expected output: code change + documentation correction.
- Parallelizable: no (blocks WP-P0-002, WP-P0-003 and the P1 spine packets, which assume fail-closed semantics)
- Requires human approval: yes
- Phase: P0
- Merged from: WP-DRAFT-PART1-001 + WP-DRAFT-PART2-002 (same defect reported by the spine and primitives workstreams).

### WP-P0-002: Close the mesh trust boundary — governed remote dispatch, fail-closed relay and WS auth, token→node binding
- Closes: GAP-C2-004, GAP-C3-001, GAP-C3-009, GAP-G-001, GAP-G-002, GAP-G-004, GAP-G-016
- Current state: (a) `POST /terminal/remote/{create,send,send-key,destroy}` (`transports/api/cockpit_workstation_control_routes.py:54-60,278-371`) dispatch arbitrary shell text/keystrokes to remote mesh nodes via `POST :8095/dispatch` with no `governed_mutation`, no risk class, no approval, no trace; (b) `transports/node_mesh/server.py:894-898` relay `/dispatch` auth is `hmac … or not relay_secret` — fail-open when `UMH_MESH_RELAY_SECRET` is unset; (c) `_http_dispatch` (`server.py:973-1039`) sends `capability.execute` with no policy check, no governance verdict, no risk_class; (d) the socket path (`transports/node_mesh/integration/handlers.py:64-77`) carries a `governance_verdict_id` string the node never validates; (e) WS `_authenticate()` returns True for any configured node's token and returns True unconditionally when zero tokens are configured (`transports/node_mesh/server.py:470-473`); `_node_id_for_token()` exists but is never called (`:475-479`) — node_id is taken from the self-declared `node.hello` payload (`:487`), so any valid token can register as any node identity (mesh identity spoofing); the token travels in the WS URL query string (`nodes/windows/umh_node/config.py:52`) where it can leak into logs; `GET /nodes` and `GET /health` on :8095 are unauthenticated and leak node IDs, capabilities, tailscale IPs, peripherals (`server.py:876,911,962-971`); (f) `substrate/organism/governed_spine.py` has zero adapter/mesh/node references; the raw relay and the governed path reach identical actuation with different guarantees (`substrate/meta_ide/browser_evidence_collector.py` uses the raw relay). The registry already defines `remote_node_exec` (`substrate/organism/mutation_registry.py:289`) and `tmux_send` (`:229`).
- Desired state: one dispatch path, fail-closed at every layer. Every remote actuation is wrapped as a `remote_node_exec`/`tmux_send` governed mutation carrying a verifiable governance verdict (signed token or DB-checked id); the relay refuses `/dispatch` when the secret is unset and requires a verdict reference on every payload; the raw `_http_dispatch` is removed or forced through the capability socket; every dispatch emits a trace event. WS auth: refuse connections when no tokens are configured; token→node_id binding enforced at hello (call the existing `_node_id_for_token`); token carried in a header, not the URL; per-node keys; the same bearer auth applied to `/nodes` and `/health` (read-only scope acceptable).
- Files to inspect: transports/api/cockpit_workstation_control_routes.py:278-371,508; transports/node_mesh/server.py:461-514,851-1039; transports/node_mesh/integration/handlers.py:56-108; substrate/organism/mutation_registry.py:229,289; substrate/meta_ide/browser_evidence_collector.py:433; nodes/windows/umh_node/config.py:52.
- Files likely modified: transports/api/cockpit_workstation_control_routes.py; transports/node_mesh/server.py; transports/node_mesh/integration/handlers.py; substrate/meta_ide/browser_evidence_collector.py; nodes/windows/umh_node/config.py.
- Forbidden files/actions: no raw `subprocess` in gated dirs; no fail-open auth; no token in URL; do not weaken to accept any node_id; do not add a second dispatch path — remove the raw one; keep dependency direction (mesh integration is transports layer); Python 3.11.
- Dependencies: WP-P0-001. Forward coordination: the verdict-issuance contract completes under WP-P1-001 (the fail-closed relay/WS mechanics land here now); durable token→node binding joins the canonical node record under WP-P2-010 (non-blocking — bind against existing per-node token config meanwhile).
- Risk class: HIGH (mesh server + remote actuation trust boundary)
- Approval required: yes — remote command execution surface; wrong verdict/binding wiring can strand or expose the executor node.
- Acceptance criteria: `/dispatch` with unset secret refuses at startup (process exits or endpoint returns 503); a WS connection with no tokens configured is refused; a token bound to node A cannot register as node B; the token is read from a header; `/nodes` and `/health` require auth; a remote terminal create/send produces a `remote_node_exec` trace event with an attached verdict id that the node validates before executing; a dispatch with a missing/invalid verdict for a write-class capability is rejected node-side; the raw relay path is gone from all callers (grep clean).
- Proof required: startup-refusal log with secret unset; refusal log with zero tokens configured; spoof-attempt rejection log; unauthenticated `/nodes` rejection; trace event + node-side verdict-validation log for one governed remote exec; rejection log for a verdict-less write dispatch.
- Tests to add/run: tests/test_mesh_dispatch_governed.py (fail-closed secret, verdict required, verdict validated node-side); tests/test_mesh_auth_binding.py (no-token refusal, token→node binding, header transport, /nodes auth); re-run scripts/check_mesh_relay_firewall.py.
- Rollback plan: revert the five files; prior fail-open relay/WS behavior restored (documented regression, acceptable only for emergency rollback).
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P0
- Merged from: WP-DRAFT-PART1-002 + WP-DRAFT-PART1-037 (mesh auth reported by the spine and runtime-node-trust workstreams).

### WP-P0-003: Node-side risk derivation, deny-by-default config, and hardened permission envelope
- Closes: GAP-C3-002, GAP-C3-013, GAP-G-003, GAP-G-010
- Current state: `nodes/windows/umh_node/client.py:458` reads `risk_class` from the request payload (default `REVERSIBLE_WRITE`) — caller-declared, never derived; `governance_verdict_id` is transmitted but never read/validated node-side. `nodes/windows/umh_node/governance.py:31-64` shell allowlist checks only `command.split()[0]` (an allowed interpreter passes arbitrary payloads) and filesystem check is unnormalized `path.startswith(allowed)` (`..` traversal / prefix-sibling escape). Defaults are open: `max_risk_class="IRREVERSIBLE_WRITE"`, empty allowlists = allow-all (`config.py:22-26`); unconfigured adapters get a fresh permissive `CapabilityConfig()` (`client.py:462-463`). The executor ShellAdapter (`nodes/windows/umh_node/adapters/shell.py`) has no deny patterns, unlike the VPS-side ShellAdapter (`adapters/tool_adapters/shell.py:13-51`). The mesh accepts any declared capability set / self-graded ceiling at hello (`server.py:506-514`) without checking device role.
- Desired state: the node derives risk class deterministically from capability + params locally (porting the VPS ShellAdapter deny-pattern set); `CapabilityConfig` defaults deny-by-default; argument-aware shell command policy; canonicalized path-containment check; declared capabilities at hello are rejected when they exceed the device's registry-declared role envelope.
- Files to inspect: `nodes/windows/umh_node/client.py:452-500`; `nodes/windows/umh_node/governance.py:12-64`; `nodes/windows/umh_node/config.py:17-79`; `nodes/windows/umh_node/adapters/shell.py:13-59`; `adapters/tool_adapters/shell.py:13-51,99-153`; `infra/device_registry.json`.
- Files likely modified: `nodes/windows/umh_node/governance.py`; `nodes/windows/umh_node/config.py`; `nodes/windows/umh_node/client.py`; `nodes/windows/umh_node/adapters/shell.py`.
- Forbidden files/actions: `nodes/` runs on the Windows executor (Python 3.11 target); do not weaken to allow-all defaults; risk class must be computed, not trusted; do not hardcode device roles — read from `infra/device_registry.json`.
- Dependencies: WP-P0-002 (verdict transmission), WP-P2-002 (canonical role envelope)
- Risk class: HIGH (executor-node trust boundary)
- Approval required: yes — deny-by-default can block legitimate executor operations until allowlists are populated.
- Acceptance criteria: a `rm -rf`/destructive payload dispatched at default caps is rejected node-side; a `..`-traversal path write is rejected; an unconfigured capability is denied (not permissively allowed); a hello declaring a capability outside the device role is rejected; a benign allowlisted op still succeeds.
- Proof required: node governance rejection logs for the destructive shell, traversal path, and over-role hello cases; success log for a benign op.
- Tests to add/run: `nodes/windows/umh_node/tests/test_node_governance.py` (risk derivation, path containment, argv policy, deny-by-default, role-envelope rejection).
- Rollback plan: revert the four node files; prior permissive config restored.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P0

### WP-P0-004: Authenticate and loopback-bind the CC webhook receiver
- Closes: GAP-C3-005
- Current state: `services/cc_webhook_receiver.py:305` binds `0.0.0.0` (docstring claims 127.0.0.1, L8); `/cc-reply`, `/cc-prompt`, `/mfa-challenge` (`:112,159,229`) are unauthenticated; `/cc-prompt` button callbacks inject responses into tmux Claude Code sessions via `session_discord_bridge`/`watcher.send_response` (`:159-165`); MFA challenge codes transit this open endpoint.
- Desired state: bind loopback (127.0.0.1) or require a bearer token on every endpoint; MFA relay authenticated end-to-end; docstring and bind address reconciled.
- Files to inspect: `services/cc_webhook_receiver.py:8,100-229,305-308`.
- Files likely modified: `services/cc_webhook_receiver.py`.
- Forbidden files/actions: no plaintext bearer secret in source — read from env/1Password; keep `services/` a thin entrypoint (no new business logic).
- Dependencies: none
- Risk class: MEDIUM (single service module)
- Approval required: yes — changes an auth-carrying endpoint that other automation depends on.
- Acceptance criteria: unauthenticated request to any of the three endpoints is rejected (401/refused); loopback bind confirmed via `ss`/`netstat`; a valid-token request still routes to the tmux bridge.
- Proof required: rejection log for an unauthenticated request; bind-address listing showing 127.0.0.1 or token-gated 0.0.0.0.
- Tests to add/run: `tests/test_cc_webhook_auth.py` (unauth reject, auth pass).
- Rollback plan: revert single file.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P0

### WP-P0-005: Decompose the nightly autonomous-agent cron into governed steps
- Closes: GAP-C3-004
- Current state: `scripts/scheduled/nightly_maintenance.sh` invokes `claude -p --allowedTools "Bash Read Write Edit Glob Grep" --add-dir /opt/OS` nightly (`infra/crontab.managed`, `0 2 * * *`) — an autonomous LLM agent with write+shell on the production repo, whose only constraint is `--max-budget-usd 0.50`; no governed mutation, proof artifact, approval, or rollback. Its failure-alert path imports `interface.discord.discord_utils` — `interface/` does not exist (confirmed absent), so alerting is dead code.
- Desired state: nightly maintenance decomposed into deterministic steps routed through the governed spine; any residual agentic step runs behind a work-packet approval contract with a proof artifact; the alert import is fixed to a real module.
- Files to inspect: `scripts/scheduled/nightly_maintenance.sh:1-50`; `infra/crontab.managed` (nightly stanza); `transports/discord/discord_utils.py` (correct alert module).
- Files likely modified: `scripts/scheduled/nightly_maintenance.sh`; `infra/crontab.managed`.
- Forbidden files/actions: do not grant write+shell to an ungoverned agent; use `gated_subprocess_run` semantics via `scripts/cron-run`; no `interface.*` imports.
- Dependencies: WP-P1-001 (governed-spine submission entry for cron)
- Risk class: HIGH (production-repo write surface)
- Approval required: yes — removes an autonomous write path that may have silent dependencies.
- Acceptance criteria: nightly run produces a proof artifact per step; no unbounded `--allowedTools` shell agent runs; the alert path resolves to an existing module and fires on a simulated failure.
- Proof required: proof artifacts from one scheduled run; alert delivered on a forced failure.
- Tests to add/run: dry-run the rewritten script under `scripts/cron-run`; assert no raw `claude -p` write-agent invocation remains (grep).
- Rollback plan: restore prior crontab stanza and script from git.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P0

### WP-P0-006: Add auth to dormant mutation services or archive them
- Closes: GAP-C3-014
- Current state: `services/goal_api.py` (Flask :8090, POST activate/defer/complete/drop, no auth), `services/higgsfield_webhook.py` (no signature verification; request_id-existence check only), and `services/local_bridge_server.py` (POST /message → tmux injection, health-check-only trust) are not in `docker-compose.yml` but are one `python3 services/…` away from being live ungoverned side doors.
- Desired state: each service either gains authentication (bearer token / signature verification) before it can be started, or is archived per the dormant-classification protocol (PROMOTE/MERGE/ISOLATE/ARCHIVE/DELETE).
- Files to inspect: `services/goal_api.py:1-18`; `services/higgsfield_webhook.py:11-14`; `services/local_bridge_server.py:1-17`; `docker-compose.yml:11-214`.
- Files likely modified: the three service files (add auth) or their removal + a dormant-classification note.
- Forbidden files/actions: no plaintext secrets; 1Password `op run` for any injected token; if archived, follow dormant-classification (do not silently delete working code).
- Dependencies: none
- Risk class: MEDIUM
- Approval required: yes — archival is a working-feature decision; must confirm none are started out-of-band.
- Acceptance criteria: for each retained service, an unauthenticated request is rejected; for each archived service, it is removed from the tree with a classification record and no remaining import references (grep).
- Proof required: rejection logs (retained) or grep-clean import check + classification note (archived).
- Tests to add/run: auth-reject test per retained service.
- Rollback plan: revert per-file.
- Expected output: code change (and/or documentation classification note).
- Parallelizable: yes
- Requires human approval: yes
- Phase: P0

### WP-P0-007: Fix the two silently-broken governed paths (create_from_intent, update_status)
- Closes: GAP-C1-001, GAP-C1-002, GAP-C1-014
- Current state: (a) `GovernedWorkRuntime.submit_work` (`substrate/organism/governed_work_runtime.py:232`) calls `packet_engine.create_from_intent` — no such method exists (WorkPacketEngine has `create_packet_from_intent`, `work_packet_engine.py:67`; grep confirms zero `def create_from_intent` repo-wide); AttributeError is swallowed (`:236-237`) so the "mandatory DO layer" never creates a real packet and classifier-derived risk is never applied. (b) `CommandRouter._process_approval` (`command_runtime.py:887-899`) calls `UniversalWorkQueue.update_status` — the queue exposes `update_packet_status` (`universal_work_queue.py:237`); grep confirms no `update_status` — AttributeError swallowed, so every packet approve/reject via operator command returns an error dict. (c) `tests/test_gate3_governed_work_runtime.py` never exercises `submit_work`, so GAP-C1-001 went uncaught.
- Desired state: both call sites use the correct method names and surface failures instead of swallowing them; a round-trip test (intent → packet → plan → approve → dispatch) exercises `submit_work` against a real WorkPacketEngine.
- Files to inspect: `substrate/organism/governed_work_runtime.py:211-237`; `substrate/organism/work_packet_engine.py:67`; `substrate/organism/command_runtime.py:887-899`; `substrate/organism/universal_work_queue.py:237`; `tests/test_gate3_governed_work_runtime.py`.
- Files likely modified: `substrate/organism/governed_work_runtime.py`; `substrate/organism/command_runtime.py`.
- Forbidden files/actions: no silent `except/logger.debug` swallow of the corrected call — must raise or return a typed error; Python 3.11 syntax.
- Dependencies: none
- Risk class: MEDIUM (correcting existing methods)
- Approval required: no — pure defect fix restoring intended behavior.
- Acceptance criteria: `submit_work` creates a real packet (id is a packet id, not a raw uuid) and classifier risk is applied; a packet approve/reject via CommandRuntime returns success, not an error dict; the new round-trip test passes.
- Proof required: test run showing packet creation with applied risk and a successful command-driven approval.
- Tests to add/run: extend `tests/test_gate3_governed_work_runtime.py` with a `submit_work` round-trip; add a CommandRuntime approve/reject test.
- Rollback plan: revert both files.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P0

### WP-P0-008: Fix WorkPacket-rename import breakage; reconcile the type registry, rule docs, and stale config
- Closes: GAP-B1-001, GAP-B2-002, GAP-C3-017
- Current state: A mechanical rename left two modules broken at import time (verified ImportError): `substrate/control_plane/router/control_plane_router_v1.py:28-38` imports `WorkPacket` from `.router_contracts`, which only defines `RouterWorkPacket` (`substrate/control_plane/router/router_contracts.py:91`); `nodes/environments/packet_validator.py:20-25` imports `WorkPacket, WorkPacketRiskLevel, WorkPacketStatus` from `.work_packet`, which only defines doubled-prefix `EnvironmentEnvironmentPacket*` names (`nodes/environments/work_packet.py:19,32,49`). Downstream dead importers: `transports/discord/interface_adapter_v1.py:36`, `transports/presence/handlers/substrate_command_handler.py:49`, `nodes/environments/w0_packet_builder.py:36`. Simultaneously, `substrate/canonical_types.py:103-106,1296` registers non-existent `EnvironmentPacket*` names and `.claude/rules/type-coherence.md` cites a third naming (`WorkPacketRiskLevel`/`WorkPacketStatus`) — three sources of truth, zero agreement; the divergence gate never caught it. Adjacent ground-truth drift: `services/CLAUDE.md` cites `transports/discord/bot.py` (confirmed absent), and `infra/crontab.managed` retains an expired one-time `shred` entry (dated 2026-06-08) marked "remove after it fires."
- Desired state: all importers resolve against the real symbol names (or explicit compatibility aliases in the defining modules); `canonical_types.py` registry entries resolve to real symbols; `.claude/rules/type-coherence.md` names match code; an import-smoke test covers `substrate/control_plane/router/` and `nodes/environments/`; the dead `services/CLAUDE.md` reference corrected; the expired cron entry removed. The `EnvironmentEnvironmentPacket*` class names themselves are corrected in WP-P2-002 — this packet restores importability and doc/registry ground truth now.
- Files to inspect: substrate/control_plane/router/control_plane_router_v1.py; substrate/control_plane/router/router_contracts.py; nodes/environments/packet_validator.py; nodes/environments/work_packet.py; nodes/environments/w0_packet_builder.py; transports/discord/interface_adapter_v1.py; transports/presence/handlers/substrate_command_handler.py; substrate/canonical_types.py (lines 103-106, 1296); .claude/rules/type-coherence.md; services/CLAUDE.md; infra/crontab.managed (final stanza).
- Files likely modified: control_plane_router_v1.py; packet_validator.py; w0_packet_builder.py; interface_adapter_v1.py; substrate_command_handler.py; nodes/environments/work_packet.py (aliases); substrate/canonical_types.py; .claude/rules/type-coherence.md; services/CLAUDE.md; infra/crontab.managed; new tests/test_import_smoke_router_environments.py.
- Forbidden files/actions: do not rename the canonical `substrate/organism/work_packet.py` WorkPacket (that convergence is WP-P2-005); no new type definitions without canonical_types.py registration; do not remove a cron entry that has not yet fired without confirming; Python 3.11 syntax only.
- Dependencies: none (WP-P2-002 later finalizes the class renames)
- Risk class: MEDIUM (modifying existing import statements in dormant-but-referenced modules; no schema or core-infra change)
- Approval required: no — restoring importability and ground truth is corrective, not architectural.
- Acceptance criteria: `python3 -c "import substrate.control_plane.router.control_plane_router_v1"` and `python3 -c "import nodes.environments.packet_validator"` succeed; a registry-resolution check confirms every canonical_types.py entry for nodes.environments.work_packet resolves via importlib+getattr; the new smoke test passes; `services/CLAUDE.md` has no dead `transports/discord/bot.py` reference; the expired shred cron entry is gone.
- Proof required: command transcripts of the two imports before (ImportError) and after (clean); pytest output of the new smoke test; doc and crontab diffs.
- Tests to add/run: add tests/test_import_smoke_router_environments.py (import every module in substrate/control_plane/router/ and nodes/environments/); run pytest tests/test_type_divergence.py; grep for the dead references (must be zero).
- Rollback plan: git revert of the single commit; no data or schema involved.
- Expected output: code fix + one new test file + rule-doc/config corrections.
- Parallelizable: yes
- Requires human approval: no
- Phase: P0
- Merged from: WP-DRAFT-PART2-001 + WP-DRAFT-PART1-042 (same rename artifact reported by the primitives and non-API-mutation workstreams).

### WP-P0-009: Remove fail-open and silent-loss defaults in quality governance and trace/feedback persistence

- Closes: GAP-B3-006, GAP-B3-010
- Current state: `ConcreteGovernanceEngine.evaluate_quality` (`substrate/control_plane/governance.py:267-268`) returns `{"score": 0.5, "passed": True}` on ANY exception — a policy engine that fails open via bare `except Exception`, violating the no-silent-except rule. Separately, `substrate/execution/trace.py:124-126` and `substrate/execution/feedback.py:84-85` swallow all exceptions during Neon persistence, so trace-event and evaluation-result data loss is invisible.
- Desired state: evaluate_quality fails closed (passed=False) or degrades with a logged, typed error — never defaults passed=True; trace/feedback persistence failures log at warning level and enqueue to a dead-letter/retry path; a persistence-success SLO metric is emittable.
- Files to inspect: substrate/control_plane/governance.py (evaluate_quality and its callers), substrate/execution/trace.py, substrate/execution/feedback.py, substrate/observability/trace_store.py (JSONL fallback candidate for dead-letter)
- Files likely modified: substrate/control_plane/governance.py, substrate/execution/trace.py, substrate/execution/feedback.py, new tests
- Forbidden files/actions: no silent except-pass (every handler at minimum logger.debug, here logger.warning); deterministic-first (the degraded verdict is deterministic, not an LLM retry); do not change the Neon `traces` schema (schema changes are CRITICAL-class and out of scope here); Python 3.11 syntax.
- Dependencies: none
- Risk class: HIGH (modifies confirmed-runtime governance and trace modules — `substrate/execution/trace.py` and `substrate/execution/feedback.py` are CONFIRMED_RUNTIME per .claude/CLAUDE.md)
- Approval required: yes — fail-closed quality evaluation can newly block work that previously passed by default; behavioral change to a live gate.
- Acceptance criteria: unit test injecting an exception into evaluate_quality observes passed=False plus a structured error record; injected Neon failure in trace/feedback persistence produces a warning log line and a dead-letter entry, and the operation continues; grep confirms zero bare `except Exception: pass/return-default` in the three touched functions.
- Proof required: pytest output; log excerpt showing the warning path; docker restart logs of affected containers (os-discord, os-operator) showing clean startup.
- Tests to add/run: new tests/test_governance_fail_closed.py, tests/test_trace_persistence_deadletter.py; run existing tests/test_trace_recorder.py.
- Rollback plan: git revert; dead-letter file/queue is additive and ignorable by old code.
- Expected output: three hardened modules + tests; no schema change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P0

### WP-P0-010: Close the EOS cross-tenant read in task polling

- Closes: GAP-D2-001
- Current state: `fetch_tasks_since` in `projections/eos/integration/tables.py:228-247` accepts `user_id` but never binds it — the WHERE clause is tautological, so the data plane reads tasks across tenant scope. The vendored `agents` table (`data/repos/entrepreneuros/shared/schema.ts:36-53`) has no owner column, so per-user scoping is currently unimplementable through that join path.
- Desired state: tenant scope enforced in the read path: either an owner column on agents (schema change in the source EOS repo + vendored schema refresh) or a task→user join path; `user_id` bound in the query; a tenancy regression test proves cross-tenant rows are not returned.
- Files to inspect: projections/eos/integration/tables.py (fetch_tasks_since and every other fetch helper for the same defect class), data/repos/entrepreneuros/shared/schema.ts, projections/eos/integration/poller.py (call sites)
- Files likely modified: projections/eos/integration/tables.py, data/repos/entrepreneuros/shared/schema.ts (vendored refresh only — source of truth is the EOS app repo), new tests
- Forbidden files/actions: no direct DDL against the live Neon EOS database from this repo without the Breaking Change Process (schema migrations are CRITICAL class — confirm row counts first); do not widen any other query's scope while editing; credential handling via existing env/.env only.
- Dependencies: WP-P3-009 if the owner-column route is chosen (writeback/migration discipline); none for the join-path route.
- Risk class: CRITICAL if the owner-column/schema route is taken; MEDIUM if solved as a query-only join binding. Treat as CRITICAL for planning.
- Approval required: yes — tenant-isolation semantics and a possible schema migration in a production-adjacent database.
- Acceptance criteria: query text binds user_id (no tautological predicate); regression test with two seeded tenants shows each poll returns only its own rows; row counts checked before/after any migration.
- Proof required: SQL/query diff; test output with two-tenant fixture; if migrated, migration file + row-count check transcript.
- Tests to add/run: new tests/test_eos_tenant_isolation.py; run tests/test_eos_projection.py.
- Rollback plan: query change: git revert. Schema change: down-migration written before up-migration is applied.
- Expected output: tenant-scoped read path + regression test; possibly one migration artifact.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P0

### WP-P0-011: Restore full-suite pytest collection

- Closes: GAP-H-001
- Current state: `pytest tests` cannot run: 3 module-level ImportErrors interrupt collection of 15,017 tests — `tests/test_execution_coordinator.py:15` (stale `ExecutionMode`), `tests/test_c23b_production_benchmarks.py` (stale `OutcomeRecord`), `tests/test_c31_phase6.py` (stale `SessionStatus`). Collection ends INTERRUPTED.
- Desired state: zero collection errors; the three stale-symbol tests fixed against current symbols (`substrate/organism/execution_coordinator.py`, `substrate/organism/benchmarks/outcome_accuracy.py`, `substrate/organism/dev_session_tracker.py`) or deleted under the dormant-classification protocol; a `pytest --collect-only` smoke gate wired into pre-commit.
- Files to inspect: tests/test_execution_coordinator.py, tests/test_c23b_production_benchmarks.py, tests/test_c31_phase6.py, substrate/organism/execution_coordinator.py, substrate/organism/benchmarks/outcome_accuracy.py, substrate/organism/dev_session_tracker.py, pyproject.toml
- Files likely modified: the three test files (fix or delete), .git pre-commit hook config / scripts (new collect-only gate)
- Forbidden files/actions: do not fix by adding back-compat aliases into substrate modules just to keep stale tests green (that hides the drift the tests should catch); classify before deleting (PROMOTE/MERGE/ISOLATE/ARCHIVE/DELETE).
- Dependencies: none
- Risk class: LOW (test files + one new gate script)
- Approval required: no
- Acceptance criteria: `pytest tests --collect-only -q` exits 0 with 0 errors; collected count reported and stable; pre-commit gate blocks a synthetic broken-import test file.
- Proof required: collect-only transcript before (3 errors, INTERRUPTED) and after (exit 0).
- Tests to add/run: `pytest tests --collect-only`; run the three repaired files individually if retained.
- Rollback plan: git revert; deleted tests recoverable from git history.
- Expected output: green collection + pre-commit collection gate.
- Parallelizable: yes
- Requires human approval: no
- Phase: P0

### WP-P0-012: Enforce the authenticated API client for all cockpit HTTP calls (kill raw fetch auth bypasses)
- Closes: GAP-F1-012, GAP-F2-003
- Current state: `cockpit/src/renderer/stores/chatStore.ts:123-127` uploads chat media via raw `fetch(\`${API_BASE}/chat/upload\`)` with FormData and NO Authorization header; the `/api/umh` router requires Clerk auth on every route (`transports/api/cockpit.py:168` `APIRouter(prefix="/api/umh", dependencies=[Depends(require_clerk_auth)])`), so media upload 401s on every surface. `cockpit/src/renderer/panels/SessionPanel.tsx:3,68-92` and `cockpit/src/renderer/panels/ProfilePanel.tsx:3,58-106` hardcode `const API_BASE = '/api/umh'` and use bare `fetch()`, bypassing the Clerk bearer injection wired in `cockpit/src/renderer/api/client.ts` (token getter set in App.tsx) and duplicating the base-URL logic consolidated in commit e1b87bd82.
- Desired state: one authenticated multipart-capable helper in `api/client.ts` (fetchApi + `uploadApi`); chatStore, SessionPanel, ProfilePanel route all I/O through it; zero bare `fetch(` calls to `/api/umh` outside `api/client.ts` (lint/grep gate).
- Files to inspect: cockpit/src/renderer/api/client.ts; cockpit/src/renderer/stores/chatStore.ts:110-140; cockpit/src/renderer/panels/SessionPanel.tsx; cockpit/src/renderer/panels/ProfilePanel.tsx; transports/api/cockpit.py:160-175.
- Files likely modified: cockpit/src/renderer/api/client.ts (add multipart helper); cockpit/src/renderer/stores/chatStore.ts; cockpit/src/renderer/panels/SessionPanel.tsx; cockpit/src/renderer/panels/ProfilePanel.tsx.
- Forbidden files/actions: no visual/layout changes (layout lock); deploy only via `bash cockpit/deploy.sh`; do not weaken the router-level Clerk guard to make the broken calls pass.
- Dependencies: none
- Risk class: MEDIUM (modifying existing client methods)
- Approval required: no — bug fix restoring intended auth behavior.
- Acceptance criteria: chat media upload succeeds against the Clerk-guarded router with a valid session and returns 401 without one; SessionPanel and ProfilePanel data loads carry the bearer header (verified in browser devtools network tab); `grep -rn "fetch(" cockpit/src/renderer --include='*.ts*' | grep -v api/client` shows no raw `/api/umh` fetches.
- Proof required: browser network capture (executor-node browser verification per browser-verification law) showing authorized upload + panel requests; grep output.
- Tests to add/run: cockpit unit test for the multipart helper (mock 401/200); `npm run build` in cockpit/; 3-pass browser validation on the deployed UI.
- Rollback plan: revert the four files; prior (broken-upload) behavior restored.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P0

### WP-P0-013: Authenticate the voice WebSocket and remove the shipped static vision token
- Closes: GAP-F2-006
- Current state: `cockpit/src/renderer/api/voice-ws.ts:21` connects `/api/umh/voice/ws` (→ :8096 per `cockpit/nginx.conf.template`) with NO client credential; `cockpit/src/renderer/api/vision-ws.ts:161-162` authenticates `/api/umh/vision/ws` with a build-time `VITE_VISION_TOKEN` compiled into the public JS bundle served from the production domain — a shipped, extractable credential. The organism and broadcast WS channels already use the correct pattern: per-session Clerk bearer subprotocol (`cockpit/src/renderer/hooks/useOrganismRealtime.ts:28-33`, `cockpit/src/renderer/api/broadcast-ws.ts:24-26`).
- Desired state: voice and vision WS both authenticate with per-session Clerk-derived tokens using the broadcast-ws subprotocol pattern; server side (`umh/voice_server.py`, `umh/vision_relay.py`) validates the token; `VITE_VISION_TOKEN` removed from the build and rotated/invalidated server-side.
- Files to inspect: cockpit/src/renderer/api/voice-ws.ts; cockpit/src/renderer/api/vision-ws.ts; cockpit/src/renderer/api/broadcast-ws.ts:20-30 (reference pattern); umh/voice_server.py; umh/vision_relay.py; cockpit/nginx.conf.template.
- Files likely modified: cockpit/src/renderer/api/voice-ws.ts; cockpit/src/renderer/api/vision-ws.ts; umh/voice_server.py; umh/vision_relay.py.
- Forbidden files/actions: no plaintext credentials in code or env-baked bundles (credential-injection law); relay processes are host processes — do not assume Docker restart reaches them; deploy cockpit only via `bash cockpit/deploy.sh`.
- Dependencies: none
- Risk class: HIGH (trust boundary on live WS channels; wrong validation bricks voice/vision)
- Approval required: yes — can sever live voice/vision until both ends are rolled together.
- Acceptance criteria: unauthenticated WS connect to voice and vision endpoints is refused; authenticated connect streams normally; `grep -rn VITE_VISION_TOKEN cockpit/` returns only dead config removal history (zero live references); the old static token no longer grants access.
- Proof required: connection-refusal log for tokenless connect + successful authenticated session transcript on both channels; grep output.
- Tests to add/run: server-side unit test for token validation in voice_server/vision_relay; manual E2E from executor-node browser.
- Rollback plan: revert client+server files; static-token behavior restored (documented regression, emergency only).
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P0

### WP-P0-014: Route Electron IPC filesystem writes through the governed mutation contract
- Closes: GAP-F2-007
- Current state: `cockpit/src/main/index.ts:153-177` registers ipcMain handlers `fs:readDir`/`fs:readFile`/`fs:writeFile` that give the renderer raw, ungoverned filesystem writes on the desktop device — no `governed_mutation`, no audit trail, no permission envelope — while the equivalent HTTP path IS governed (`transports/api/cockpit_workspace_routes.py:108` wraps write-file in `governed_mutation`). The Electron surface is therefore a control-plane bypass for exactly the operation class the platform governs elsewhere.
- Desired state: desktop file writes routed through the same governed contract as HTTP — either the IPC handler forwards to the local API `/workspace/write-file` (preferred: one choke point, proof artifact + trace event emitted) or the handler is removed and the renderer uses the HTTP path directly. Read-only IPC (readDir/readFile) may remain with an audit log line.
- Files to inspect: cockpit/src/main/index.ts:140-180; transports/api/cockpit_workspace_routes.py:61,108; cockpit/src/renderer (grep `fs:writeFile` invokers).
- Files likely modified: cockpit/src/main/index.ts; renderer callers of `window.api.fs.writeFile` (grep-resolved).
- Forbidden files/actions: no second write path left behind — remove, don't deprecate; deploy gate for cockpit; no visual changes.
- Dependencies: none; forward coordination: WP-P5-016 (Electron API binding, required only for the forwarding variant — see Cross-phase prerequisites)
- Risk class: MEDIUM (modifying existing IPC handlers; Electron surface currently non-functional against API anyway per GAP-F2-005)
- Approval required: yes — removes a working (if ungoverned) desktop capability.
- Acceptance criteria: a file write initiated from the Electron renderer produces a governed-mutation trace event and proof artifact identical in shape to the HTTP path; `grep -n "fs:writeFile" cockpit/src/main/index.ts` shows no raw `writeFileSync` on renderer input.
- Proof required: trace event for one desktop-initiated write; grep output.
- Tests to add/run: electron main unit test (mock ipc → assert forwarded call); cockpit build.
- Rollback plan: revert index.ts; raw IPC writes restored.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P0

### WP-P0-015: Fence or govern the saas-dev-skill parallel agentic execution system
- Closes: GAP-E2-003
- Current state: `skills/saas-dev-skill/` is a standalone TypeScript multi-agent build pipeline with its OWN orchestrator, approval gate, and DB access (`skills/saas-dev-skill/lib/orchestrator/approval-gate.ts`, `lib/orchestrator/{index,phase-runner,context-detector,db}.ts`) and routes all LLM calls through a `claude -p` subprocess (`skills/saas-dev-skill/lib/claude-subprocess.ts:1-10` — "Drop-in replacement for @anthropic-ai/sdk"). It imports nothing from governed_mutation, the spine, or the policy engine (grep-verified) and is not registered in the repo's `.claude/skills/`. It is a second, ungoverned agentic execution system inside the control-plane repo.
- Desired state: an explicit decision executed one of two ways: (a) GOVERN — its approval gate delegates to the UMH approval authority and its phase execution emits work packets/trace events through the governed spine; or (b) FENCE — a written trust-boundary declaration (README + registry entry) stating it runs out-of-control-plane, plus removal of any credentials/DB access shared with the platform, plus registration or archival per the dormant-classification protocol. Default recommendation: (b) now, (a) if productized.
- Files to inspect: skills/saas-dev-skill/lib/orchestrator/ (all); skills/saas-dev-skill/lib/claude-subprocess.ts; skills/saas-dev-skill/README.md; transports/api/governed.py (contract to target for option a).
- Files likely modified: skills/saas-dev-skill/lib/orchestrator/approval-gate.ts; skills/saas-dev-skill/lib/orchestrator/db.ts; new trust-boundary declaration doc inside skills/saas-dev-skill/.
- Forbidden files/actions: its `claude -p` subprocess spawning must respect the CPU gate law if it ever runs on the VPS (cc_sdk has its own gate — do not bypass); no plaintext credentials.
- Dependencies: none
- Risk class: LOW (fencing = new docs + config removal) / HIGH if option (a) chosen
- Approval required: yes — architectural decision (govern vs fence) belongs to the operator.
- Acceptance criteria: either every saas-dev build phase produces a UMH approval + trace event, or the fence declaration exists, the skill has no shared platform credentials/DB, and its status is recorded (PROMOTE/ISOLATE/ARCHIVE).
- Proof required: for (b): the declaration file + grep showing no platform DB/credential imports; for (a): one end-to-end build with UMH approval records.
- Tests to add/run: existing `skills/saas-dev-skill/tests/unit/` suites still pass after fencing.
- Rollback plan: revert; system returns to undeclared state.
- Expected output: decision + code/doc change (documentation-only if option b with no shared credentials found).
- Parallelizable: yes
- Requires human approval: yes
- Phase: P0

---

## P1 — Spine convergence (21 packets)

**Objective.** Converge on one canonical governed operation runtime and one mutation-submission entry; unify the approval authority; make the spine durable; land the commit/verdict/trace/proof primitives the runtime emits.

**Entry criteria.** P0 complete — in particular WP-P0-001 (fail-closed choke point) and WP-P0-004 (authenticated webhook channel).

**Exit criteria.** A single documented submission entry exists and is enforced by an architecture test; every mutation path routes through it or carries a recorded exemption; approvals land in one auditable store; pending work survives process restarts.

### WP-P1-001: Establish one canonical governed operation runtime; retire rival spines, pipelines, and event backbones
- Closes: GAP-A-004, GAP-A-009, GAP-C1-018, GAP-B1-010, GAP-B2-006, GAP-H-012
- Current state: The operation data plane is split across concurrent spines and pipelines: `substrate/organism/governed_spine.py` (GovernedExecutionSpine, ActionEnvelope, approval/rollback/journal machinery), the ungoverned 8-stage `substrate/execution/spine.py` (SignalEnvelope; CONFIRMED_RUNTIME per .claude/CLAUDE.md; mandatory `ConversationMemory.store`/`AgentMemory.log` on every signal, `:388-433`), the legacy sync `substrate/execution/runtime/execution_spine.py`, `substrate/execution/pipeline.py` (ExecutionPipeline), and `transports/api/signal_router.py`. Mutations on the execution-spine path never pass governed approval/rollback; the governed path and the WorkPacket pipeline are disjoint: `substrate/organism/governed_spine.py` has zero WorkPacket linkage while `substrate/organism/organism_loop.py:5,25-27` runs PolicyEngine→WorkPacketExecutor independently — two governance choke points for the same class of state change. Two event backbones: `services/discord_bot.py:108` imports `substrate/execution/bridge/event_spine` instead of the canonical `substrate/organism/event_spine.py` (PLATFORM_SPEC.md §3). Four+ HTTP API implementations coexist; the live HTTP state authority is `services/operator_api.py` (:8091, nginx target, `docker-compose.yml:174-177`), but `ARCHITECTURE.md:434` claims "One API — transports/api/http/ serves all clients," which is false. `tests/test_spine_full.py:10` pins the ungoverned `ConcreteExecutionSpine` as current, keeping the deprecated path alive and green.
- Desired state: one declared canonical mutation-submission entry (the governed spine via `governed_mutation`/MutationRouter) that cron, services, workcells, and the organism loop submit into; the other spines become stages of it or are retired via documented migration; `ConcreteExecutionSpine` memory writes route through the canonical memory write path (`substrate/memory/canonical_write.py:177`) with a promotion policy; the deployed service imports the canonical `organism/event_spine.py`; `ARCHITECTURE.md` §9 corrected to deployment reality; tests/test_spine_full.py migrated to GovernedExecutionSpine or marked legacy; the rival read/signal pipeline documented as read-only or converged.
- Files to inspect: substrate/organism/governed_spine.py; substrate/execution/spine.py:388-433; substrate/execution/runtime/execution_spine.py; substrate/execution/pipeline.py:142; substrate/organism/organism_loop.py; transports/api/signal_router.py; substrate/organism/event_spine.py; substrate/execution/bridge/event_spine.py; services/discord_bot.py:108; substrate/memory/canonical_write.py:177; substrate/organism/mutation_router.py; ARCHITECTURE.md:432-436; PLATFORM_SPEC.md §3; tests/test_spine_full.py.
- Files likely modified: substrate/organism/organism_loop.py (route WorkPacketExecutor through the governed path); substrate/execution/spine.py (stage-ification or deprecation shim + canonical memory writes); services/discord_bot.py; one event_spine module (retire); tests/test_spine_full.py; ARCHITECTURE.md; .claude/CLAUDE.md (status-taxonomy correction); migration doc.
- Forbidden files/actions: `substrate/execution/spine.py` is CONFIRMED_RUNTIME — never remove behavior without the migration doc, a dependents check, and staged cutover; substrate/ must not import transports/services; CPU gate law for any spawned work; never restart all services simultaneously; deterministic-first for routing decisions.
- Dependencies: WP-P0-001 (fail-closed substrate choke point must exist before all traffic routes through it)
- Risk class: HIGH (core execution/event backbone; affects every executing service)
- Approval required: yes — architecture decision retiring/subordinating a confirmed-runtime spine.
- Acceptance criteria: an architecture test (AST-based) proves no mutation-executing path reaches an executor without a governed verdict; only one spine entry point is exported and the documented single submission entry is referenced by cron/services; duplicate event_spine resolved (grep shows a single event-spine import in the deployed path); `ConcreteExecutionSpine` memory writes go through canonical_write.py; ARCHITECTURE.md §9 matches deployment reality; test_spine_full.py no longer pins the ungoverned variant; Discord/operator services restart clean.
- Proof required: architecture-test output; trace/ledger records showing a WorkPacket execution passing governed stages end-to-end; event-spine import grep; a memory write via the canonical path; corrected doc diff; container restart logs.
- Tests to add/run: new tests/test_single_spine_architecture.py; new tests/test_single_event_spine.py; migrate tests/test_spine_full.py; run tests/test_gate3_governed_work_runtime.py, tests/test_c34_mutation_router.py; memory-promotion suite.
- Rollback plan: staged cutover behind a routing flag; rollback = flip flag + git revert per stage; journal entries from the governed path are additive; doc changes non-executable.
- Expected output: code change + documentation change + migration doc.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1
- Merged from: WP-DRAFT-PART1-016 + WP-DRAFT-PART2-006 (rival-spine convergence reported by the architecture and primitives workstreams).

### WP-P1-002: Register the five unregistered mutation names and add a CI literal↔registry check
- Closes: GAP-C2-003
- Current state: `filesystem_write`, `config_update`, `proof_review`, `workstation_execute`, `recovery_action` are used at 8 handler call sites but absent from `substrate/organism/mutation_registry.py` (47 specs). `MutationRouter.execute` rejects unregistered names (`mutation_router.py:94-103`) when the daemon runs; the WP-P0-001 fallback executed them when it did not. Highest blast radius: `/workspace/write-file` and `/workspace/remote-write-file` (base64-over-SSH PowerShell write, `cockpit_workspace_routes.py:590-609`).
- Desired state: every `mutation_name=` literal resolves to a registered MutationSpec (either add specs, or repoint handlers to existing `file_write`/`config_set`); a CI/pre-commit check greps handler literals against the registry and fails on any unregistered name.
- Files to inspect: `transports/api/cockpit_workspace_routes.py:109,605`; `transports/api/workstation.py:77,108`; `transports/api/cockpit_core_bootstrap_routes.py:482`; `transports/api/cockpit_proof_inspector_routes.py:212,238`; `transports/api/cockpit_recovery_dashboard_routes.py:231`; `substrate/organism/mutation_registry.py:304,414`.
- Files likely modified: `substrate/organism/mutation_registry.py`; the five route files (repoint literals); new `scripts/check_mutation_name_registration.py`.
- Forbidden files/actions: no unregistered literals; new spec risk levels must be accurate (not blanket low); type-coherence for any new spec type.
- Dependencies: WP-P0-001
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: with the daemon running, all 8 endpoints succeed (names resolve); the new check passes on the tree and fails on an injected bad literal.
- Proof required: gate output green; injected-bad-literal failure demonstration.
- Tests to add/run: run the new checker `--all`; endpoint smoke for the 8 handlers.
- Rollback plan: revert registry + route edits; remove checker.
- Expected output: code change (+ new enforcement script).
- Parallelizable: yes
- Requires human approval: no
- Phase: P1

### WP-P1-003: Eliminate the state_mutate catch-all; enforce capability-derived mutation names
- Closes: GAP-C2-006, GAP-C3-015
- Current state: `mutation_name="state_mutate"` accounts for 159 of ~430 Python literals (and 29/33 TS), spec'd low-risk / fully-reversible / local-runtime (`mutation_registry.py:538-545`), yet is used for execution stop/kill (`execution.ts:114-120`), universal signal intake (`app.py:549`), pipeline submit (`app.py:712`), and operator_api chat/ingest/TTS/vision (`operator_api.py:441-636`). The policy engine's risk input is self-declared by the handler author; the registry's per-mutation risk model is bypassed by name reuse.
- Desired state: per-operation mutation specs replace `state_mutate` at high-effect call sites; a lint rule caps `state_mutate` usage; the spine rejects `state_mutate` for envelopes whose intent strings match high-risk verbs.
- Files to inspect: `substrate/organism/mutation_registry.py:538-545`; `transports/api/app.py:549,712`; `transports/api/http/routes/execution.ts:106-137`; `services/operator_api.py:441-636`; grep distribution of `mutation_name=`.
- Files likely modified: `substrate/organism/mutation_registry.py` (new specs); high-effect route/service files; `substrate/organism/governed_spine.py` (heuristic reject) or `mutation_router.py`; new lint in `scripts/`.
- Forbidden files/actions: substrate must not import transports; keep new specs in `canonical_types.py` if new enums arise; deterministic-first for the intent-verb heuristic (regex/table, LLM optional).
- Dependencies: WP-P1-002
- Risk class: HIGH (touches spine/mutation-router risk evaluation)
- Approval required: yes — changes risk classification behavior for many live routes.
- Acceptance criteria: high-effect handlers use accurate names; a `state_mutate` envelope with a high-risk intent verb is rejected; lint fails when `state_mutate` count exceeds the cap.
- Proof required: rejection trace for a high-risk `state_mutate`; lint output.
- Tests to add/run: `tests/test_state_mutate_guard.py`; run the new lint `--all`.
- Rollback plan: revert; heuristic behind a flag.
- Expected output: code change (+ lint script).
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-004: Wrap remaining autonomous-lane and file-write side-door endpoints in governed mutations
- Closes: GAP-C2-007, GAP-C2-011, GAP-C3-016
- Current state: `/organism/autonomous-cadence/set-mode` writes `cadence.mode` directly (`cockpit_autonomous_routes.py:374-392`, mode-allowlisted), `run-dry-run` runs a cadence cycle directly (`:359-367`), PR-factory cleanup and candidate-supply run are direct calls (`:85,91,101`); `/chat/upload` writes to `data/chat_media/` directly (`cockpit_chat_routes.py:473-509`, type/size validated); cron/scraper paths (`scripts/agent_task_executor.py:265`, `services/icp_scorer.py:20`) write `AgentMemory` directly, bypassing the memory-promotion candidate→record lifecycle.
- Desired state: cadence-mode change becomes a governed governance-mode mutation; dry-run/cleanup/candidate-run wrapped or explicitly registered as low-risk exempt; chat upload wrapped as `file_write` or registered as an exempted low-risk data-plane op; cron-originated memories enter as memory candidates through the promotion pipeline.
- Files to inspect: `transports/api/cockpit_autonomous_routes.py:84-101,359-392`; `transports/api/cockpit_chat_routes.py:466-520`; `scripts/agent_task_executor.py:263-266`; `services/icp_scorer.py:18-20`; `substrate/organism/memory_promotion.py`.
- Files likely modified: `transports/api/cockpit_autonomous_routes.py`; `transports/api/cockpit_chat_routes.py`; `scripts/agent_task_executor.py`; `services/icp_scorer.py`.
- Forbidden files/actions: no direct memory writes bypassing promotion; keep mutation names capability-accurate (no `state_mutate` catch-all — see WP-P1-003).
- Dependencies: WP-P1-002 (specs), WP-P1-003 (naming discipline)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: each listed endpoint routes through `governed_mutation` with an accurate registered name (or a documented exemption); cron memory writes appear as candidates, not direct records.
- Proof required: trace events for cadence-mode change and chat upload; a promotion-candidate record from a cron run.
- Tests to add/run: endpoint tests asserting governed path; memory-candidate assertion for the cron writer.
- Rollback plan: revert per-file.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P1

### WP-P1-005: Make organism_bridge governed-execute actually apply state (kill governance theater)
- Closes: GAP-C2-002
- Current state: `transports/api/organism_bridge.py:2351-2352` defines `execute_fn = lambda: (json.dumps(mutation_payload), True)` — the envelope's execute function echoes the payload and does nothing. All 33 Hono TS mutations (memory-promotion approve/reject, approval-packet decisions, kill/resume) record a successful governed mutation with a proof artifact and trace event, but no state change occurs. Proof artifacts assert effects that never happened. (Mitigated only because the Hono server is currently undeployed — see WP-P2-022.)
- Desired state: `organism.governed_execute` dispatches `mutation_payload` to a registered server-side executor keyed by `mutation_name` (a payload-executor registry), so the envelope's execute_fn performs the real mutation; or, if the TS surface is retired (WP-P2-022), this handler is removed.
- Files to inspect: `transports/api/organism_bridge.py:2336-2363`; `transports/api/http/lib/governed_bridge.ts:29-55`; `transports/api/http/routes/organism.ts:177-196`.
- Files likely modified: `transports/api/organism_bridge.py`; new payload-executor registry module under `transports/api/`.
- Forbidden files/actions: no no-op execute_fn passed to `governed_mutation`; keep dependency direction (transports may import substrate).
- Dependencies: WP-P2-022 (decide TS surface fate first)
- Risk class: MEDIUM
- Approval required: yes — proof-artifact integrity change; if the TS surface is retired instead, this becomes a deletion.
- Acceptance criteria: a memory-promotion approve via the TS bridge produces an actual promotion (state verified independently), not just a proof artifact; or the handler is removed and grep shows no remaining no-op execute_fn.
- Proof required: before/after state of a promoted memory record; or grep-clean removal.
- Tests to add/run: `tests/test_organism_bridge_execute.py` asserting real state change per mutation_name.
- Rollback plan: revert bridge file / restore handler.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-006: Migrate the live Discord path off the legacy sync ExecutionSpine onto the governed path
- Closes: GAP-C1-006, GAP-A-008
- Current state: `substrate/execution/runtime/execution_spine.py:16-18` self-labels legacy ("new code should use canonical") yet is the live production Discord path (`services/discord_bot.py`, `services/discord_message_handlers.py` per query_graph dependents); it runs its own AuthorityEngine approval queue (`:113-127`) and direct `ConversationMemory`/`AgentMemory` writes + `storage.put` (`:156-210`) — all bypassing governed mutation. Separately, `CognitiveLoop` executes "through governed spine when bridge is active, else direct" (`substrate/control_plane/runtime/cognitive_loop.py:365,720`), with spine injection dependent on daemon availability (`gateway.py:1016-1025`) — a conditional bypass. PLATFORM_SPEC.md §1 requires all state changes to route through governed mutation.
- Desired state: the Discord hot path routes through the canonical governed spine/governed_mutation; the CognitiveLoop fails closed (read-only) when the governed spine is unavailable instead of executing directly; the legacy shim is deleted once no dependents remain.
- Files to inspect: `substrate/execution/runtime/execution_spine.py:86-222`; `services/discord_bot.py`; `services/discord_message_handlers.py`; `substrate/control_plane/runtime/cognitive_loop.py:314-449,720`; `substrate/control_plane/runtime/gateway.py:1012-1025`.
- Files likely modified: `substrate/control_plane/runtime/cognitive_loop.py`; `services/discord_message_handlers.py`; `services/discord_bot.py`; delete `substrate/execution/runtime/execution_spine.py` (final step).
- Forbidden files/actions: do not remove the shim before dependents migrate; restart `os-discord` and verify clean startup after changes; substrate must not import services.
- Dependencies: WP-P0-001, WP-P1-001
- Risk class: HIGH (deployed Discord service core path)
- Approval required: yes — hot path on a production container.
- Acceptance criteria: a Discord-originated mutation produces a governed-spine trace event; with the governed spine unavailable, the loop performs no direct mutation (reads only); `os-discord` starts clean; the legacy shim has zero dependents (grep) before deletion.
- Proof required: governed-spine trace for a Discord mutation; clean `docker logs os-discord`; dependents grep = 0.
- Tests to add/run: `tests/test_discord_governed_path.py`; import-smoke `tests/test_p0_smoke.py`.
- Rollback plan: restore prior imports; shim retained until migration proven.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-007: One approval authority — canonical ApprovalRequest, typed approval port, single pending-work store
- Closes: GAP-C1-004, GAP-C2-005, GAP-C3-008, GAP-B3-002, GAP-B3-012
- Current state: at least four independent approval/lifecycle state machines exist with no single pending-work authority — (1) GovernedExecutionSpine envelopes (`substrate/organism/governed_spine.py:256`), (2) ExecutionCoordinator plans (`substrate/organism/execution_coordinator.py:913-960`), (3) CommandRuntime lifecycle over JSONL (`substrate/organism/command_runtime.py:1186`), (4) legacy AuthorityEngine queue (`substrate/execution/runtime/execution_spine.py:113-127`); `GovernedExecutionRuntime` reads yet another view. Operator-loop HTTP handlers delegate to `execcoord_routes.py`/`executor_routes.py`/`agent_routes.py`/`approval_routes.py`, which write directly to these substrate services with bespoke `_audit_log()` and no spine envelope (`substrate/organism/executor_runtime.py:1242-1245` auto-approves fail-open when the intercept service is missing). Across surfaces there are three parallel approval channels: OperatorApprovalGate (`transports/discord/approval_bridge.py`), CC-session buttons (`cc_webhook_receiver` → tmux), and `nodes/distribution/distributor.py` request/receive_approval. The approval primitive itself is fragmented across 4 typed schemas + 2 untyped dict stores with no canonical type: `substrate/organism/approval_gate.py:38` (ApprovalPacket), `substrate/organism/executors/approval_intercept.py:57` (ApprovalInterceptRequest), `substrate/workstation/unified_approval_runtime.py:43` (UnifiedApproval/UnifiedApprovalItem), `substrate/organism/approval_store.py:19` (dict store); `tests/test_phase31_operator_home.py:122` mocks a nonexistent `ApprovalRequest`. The trust-boundary port `substrate/sockets/approval_port.py:13-41` is an untyped callable registry (dict in/dict out, silent no-op when unregistered).
- Desired state: one canonical `ApprovalRequest` in substrate/types.py (registered in canonical_types.py) with per-source adapters mapping the variants and a single approval-ID namespace; `approval_port` typed with Pydantic request/response and loud, fail-closed behavior when no handler is registered; one approval authority / one pending-work state authority — the other stacks become projections of it (per-channel adapters landing every approval in one auditable store); the executor-runtime fail-open fallback becomes fail-closed; delegated handler libraries submit envelopes internally or wrap calls in `governed_mutation`.
- Files to inspect: substrate/organism/governed_spine.py:256; substrate/organism/execution_coordinator.py:900-1010; substrate/organism/command_runtime.py:1186-1310; substrate/execution/runtime/execution_spine.py:113-127; transports/api/execcoord_routes.py:114-220; transports/api/executor_routes.py:147-174; transports/api/agent_routes.py:52-98; transports/api/approval_routes.py:94-156; substrate/organism/executor_runtime.py:733-760,1242-1245; transports/discord/approval_bridge.py:68-121; nodes/distribution/distributor.py:218-262; substrate/organism/approval_gate.py:38; substrate/organism/executors/approval_intercept.py:57; substrate/workstation/unified_approval_runtime.py:43; substrate/organism/approval_store.py:19; substrate/sockets/approval_port.py:13-41; tests/test_phase31_operator_home.py:122.
- Files likely modified: a new/consolidated approval-authority module in substrate/organism/; substrate/types.py; substrate/canonical_types.py; approval_gate.py; approval_intercept.py; unified_approval_runtime.py; approval_store.py; substrate/sockets/approval_port.py; the four handler-library route files; substrate/organism/executor_runtime.py; the three approval-channel adapters.
- Forbidden files/actions: no new parallel approval store; approval is a human-governance trust boundary — no fallback that auto-approves on port failure (fail closed, including the missing-intercept case); substrate must not import transports (the Discord bridge registers via the port); type-coherence registration.
- Dependencies: WP-P0-001, WP-P0-004, WP-P1-001
- Risk class: HIGH (core state-authority consolidation across every approval surface)
- Approval required: yes — large blast radius; changes the operator approval contract.
- Acceptance criteria: one registered ApprovalRequest; all variants constructible from/convertible to it with round-trip tests; an unregistered approval_port handler raises (or queues) instead of silently no-oping; every approval (spine, coordinator, command, node, Discord, CC) lands in one auditable store; a query for "what is pending approval" returns a single unified view; executor-runtime with no intercept service rejects rather than auto-approves; the Discord approval round-trip works.
- Proof required: unified pending-approval query result spanning ≥3 origin channels; fail-closed log for the missing intercept service; round-trip test output; a live (or TestClient) approval-flow trace.
- Tests to add/run: tests/test_unified_approval_authority.py (multi-channel approvals into one store; fail-closed); tests/test_approval_request_canonical.py; run tests/test_phase31_operator_home.py (fix its mock to the real type).
- Rollback plan: staged — introduce the unified store as a shadow reader first; adapters preserve old shapes at boundaries; revert adapters if drift detected.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1
- Merged from: WP-DRAFT-PART1-013 + WP-DRAFT-PART2-012 (approval fragmentation reported by the spine and primitives workstreams; the cockpit-client consumer is WP-P5-004 and the EOS product-approval mapping is WP-P4-009).

### WP-P1-008: Govern the Workcell protocol/daemon and the ungoverned WorkloadRunner default path
- Closes: GAP-C1-005, GAP-C1-008
- Current state: `Workcell.process_next` (`workcell_protocol.py:266-311`) executes arbitrary prompts via a bound `RuntimeAdapter.execute()` (default "shell") with no envelope, risk class, or approval; `WorkcellDaemon` (`workcell_daemon.py:251-332`) schedules periodic injections with no governance gate. Separately, `WorkloadRunner.run_workload` (`workload_runner.py:242`) executes handlers directly under `ExecutionModeManager` only; `set_governed_spine` (`:170`) stores a reference that is never read (dead wiring; `daemon.py:327` sets it).
- Desired state: Workcell execution wraps adapter calls in an ActionEnvelope routed through the spine (or gateway) with risk classification; `WorkloadRunner.run_workload` routes mutation-capable workloads through the spine by default, or the dead `_governed_spine` attribute is removed.
- Files to inspect: `substrate/organism/workcell_protocol.py:284-311`; `substrate/organism/workcell_daemon.py:286-332`; `substrate/organism/workload_runner.py:167,170-171,242-372`; `substrate/organism/daemon.py:327`.
- Files likely modified: `substrate/organism/workcell_protocol.py`; `substrate/organism/workcell_daemon.py`; `substrate/organism/workload_runner.py`.
- Forbidden files/actions: no arbitrary prompt execution without an envelope; deterministic risk classification before adapter dispatch.
- Dependencies: WP-P1-001
- Risk class: HIGH (execution runtime)
- Approval required: yes — arbitrary-adapter execution surface.
- Acceptance criteria: `process_next` produces an ActionEnvelope + risk class before adapter dispatch; a periodic daemon injection is gated; `run_workload` routes a mutation-capable workload through the spine, or the dead attribute is gone (grep).
- Proof required: envelope/trace for a workcell execution; grep showing `_governed_spine` either read or removed.
- Tests to add/run: `substrate/organism/tests/test_workcell_governed.py`; extend `test_workload_runner.py` for the default-path routing.
- Rollback plan: revert the three files.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-009: Route CommandRuntime mutation commands through envelopes; fix non-atomic JSONL + idempotency
- Closes: GAP-C1-011, GAP-C1-016, GAP-C1-015
- Current state: CommandRuntime executes profile/system-mode switches (`command_runtime.py:738-775`), objective creation (`:782-805`), scheduling via private `loop._candidate_queue.add` (`:729`), and inline execution of non-approval commands (`:1172-1179`) directly on subsystems with `approval_state="not_required"` and no envelope. `CommandHistory.update_status` rewrites the JSONL with `open(path,"w")` (`:1069-1072`) — non-atomic; a crash mid-write corrupts the command state authority (contrast `workcell.py:247-252` which uses tempfile+os.replace). Spine idempotency map is unbounded (`governed_spine.py:133,477-479`) and registry validation is skipped when `metadata.mutation_name` is unset (`:341-346`).
- Desired state: mutation-classed CommandActionTypes produce ActionEnvelopes routed through MutationRouter; `CommandHistory.update_status` uses tempfile+os.replace; spine idempotency keys have a TTL/LRU bound and `submit()` requires a `mutation_name` or an explicit exemption class.
- Files to inspect: `substrate/organism/command_runtime.py:713-805,1067-1073,1172-1179`; `substrate/organism/governed_spine.py:133,339-374,477-479`; `substrate/organism/workcell.py:247-252`.
- Files likely modified: `substrate/organism/command_runtime.py`; `substrate/organism/governed_spine.py`.
- Forbidden files/actions: no non-atomic full-file rewrites of state authority; no reaching into private queues — use public APIs; Python 3.11.
- Dependencies: WP-P1-001
- Risk class: HIGH (spine + command state authority)
- Approval required: yes — modifies the governed spine.
- Acceptance criteria: a profile/system-mode switch emits an envelope/trace; a simulated crash mid `update_status` leaves history intact; idempotency map is bounded under a soak; a `submit()` without mutation_name and without exemption is rejected.
- Proof required: envelope/trace for a command mutation; integrity of history after a killed write; bounded map size under soak.
- Tests to add/run: `tests/test_command_runtime_governed.py`; `tests/test_history_atomic_write.py`; `tests/test_spine_idempotency_bound.py`.
- Rollback plan: revert both files.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-010: Route the cron mutation plane through the governed spine via signal submission
- Closes: GAP-C3-006, GAP-C3-003, GAP-C3-007
- Current state: cron scripts mutate Neon `events` and Notion directly every 5-15 minutes with no governed mutation, trace, or proof — `agent_task_executor.py:101-265` (CognitiveLoop → complete_task → Notion → AgentMemory), `call_prep.py:324`, `noshow_detector.py:129`, `notion_tasks_sync.py:138-231`, `notion_sync_poller.py`; `cron-run` provides only CPU/lock/secret hygiene. External side effects execute outside governance while only bookkeeping is governed: `gws.send_email()` runs directly (`services/discord_bot_commands.py:546,654`) and only the subsequent `UPDATE events` is wrapped in `governed_mutation`. `calendar_invite_handler.py` auto-accepts/declines external calendar invites on high LLM/rule confidence (`:273-306`) via GWSConnector — an externally-visible L1 mutation with an LLM in the loop, from cron, ungoverned.
- Desired state: cron scripts submit signals (the `emit_signal.py` pattern) consumed by the orchestrator/governed spine; direct DB/Notion writes migrate behind governed mutation contracts; the external mutation itself (email send, invite response) is the governed execute_fn (or an ActionEnvelope with `require_approval`) with rollback/verification hooks and a proof artifact; invite responses classified EXTERNAL_COMMUNICATION with an approval or deterministic-rule gate.
- Files to inspect: `infra/crontab.managed`; `scripts/agent_task_executor.py:101-265`; `scripts/notion_tasks_sync.py:138-157`; `scripts/calendar_invite_handler.py:112-306`; `scripts/cron-run:1-60`; `services/discord_bot_commands.py:505-580,654`; `adapters/google_workspace/gws_connector.py:1074`; `scripts/emit_signal.py`.
- Files likely modified: the cron scripts above; `services/discord_bot_commands.py`.
- Forbidden files/actions: no direct DB/Notion writes from cron for governed domains; use `governed_mutation` with accurate names; deterministic-first for the invite decision (rules before LLM); `op run` for credentials.
- Dependencies: WP-P1-001, WP-P1-003
- Risk class: HIGH (external-visible mutations + broad cron surface)
- Approval required: yes — external communication effects (email/calendar) visible to third parties.
- Acceptance criteria: a cron-originated event mutation produces a governed trace + proof; an email send is the governed execute_fn (send gated, not just logged); an auto invite response emits a proof artifact and is deterministic-rule or approval gated.
- Proof required: trace/proof for one cron event mutation and one governed email send; proof artifact for an auto invite response.
- Tests to add/run: `tests/test_cron_governed_submission.py`; invite-handler decision test (deterministic path).
- Rollback plan: revert per-script; cron entries restored from git.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-011: Converge dual signal intake types and rival signal routers

- Closes: GAP-B1-003
- Current state: `substrate/types.py` defines BOTH `SignalEnvelope` (line 48, "The universal input type") and `Signal` (line 990, "all external input enters as a Signal"); each has its own pipeline — `substrate/control_plane/router/__init__.py:28-62` (ConcreteSignalRouter over SignalEnvelope) vs `transports/api/signal_router.py:31-50` (SignalRouter over Signal + types.py WorkPacket), consumed by `transports/api/runtime.py:12`. `Signal` is unregistered in canonical_types.py.
- Desired state: one intake type and one router contract; the loser deprecated with a migration shim and registered deprecation marker; canonical_types.py names the survivor.
- Files to inspect: substrate/types.py:48,990; substrate/control_plane/router/__init__.py; transports/api/signal_router.py; transports/api/runtime.py; transports/discord/signal_factory.py (CONFIRMED_RUNTIME producer of SignalEnvelope); all grep hits for `Signal(` construction
- Files likely modified: transports/api/signal_router.py (retarget to survivor type), substrate/types.py (deprecation alias), substrate/canonical_types.py, transports/api/runtime.py
- Forbidden files/actions: do not break transports/discord/signal_factory.py (CONFIRMED_RUNTIME); no new parallel type — converge to one of the two existing; type-coherence registration mandatory.
- Dependencies: WP-P1-001 (spine decision determines which router survives)
- Risk class: HIGH (intake path of the control plane)
- Approval required: yes — selecting the canonical intake type is an architecture decision.
- Acceptance criteria: exactly one intake class registered as canonical; the deprecated one importable only as an alias emitting DeprecationWarning; both former pipelines' consumers pass their tests; check_type_divergence.py passes.
- Proof required: grep inventory showing all constructors on the survivor; pytest of intake tests; a live Discord signal traced end-to-end through the surviving router.
- Tests to add/run: new tests/test_signal_intake_convergence.py; run existing signal/router tests.
- Rollback plan: alias keeps old imports working; git revert restores dual routers.
- Expected output: one intake type + one router contract + deprecation shim.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-012: Durable operation queues in the governed spine

- Closes: GAP-B1-012
- Current state: GovernedExecutionSpine uses in-process deques (`_MAX_QUEUE = 500`, `_MAX_COMPLETED = 1000`, `substrate/organism/governed_spine.py:62-63`) — pending approvals and envelope lifecycle are lost on process restart; ExecutionJournal records phases but there is no replay/resume contract at the spine boundary (lines 197-295).
- Desired state: durable operation queue with journal-backed recovery on boot: pending approvals and executing envelopes survive restarts; a documented replay contract (idempotency keys on envelope execution).
- Files to inspect: substrate/organism/governed_spine.py:60-66,197-295; the ExecutionJournal implementation it writes to; substrate/organism/execution_ledger.py
- Files likely modified: substrate/organism/governed_spine.py (boot-time recovery), journal module (recovery read API), new tests
- Forbidden files/actions: no schema migration in this packet (persist via existing journal/ledger stores); no silent except-pass in recovery; CPU gate before heavy replay loops.
- Dependencies: WP-P1-001
- Risk class: HIGH (core governed-spine lifecycle)
- Approval required: yes — replay semantics can re-trigger operations; idempotency policy needs sign-off.
- Acceptance criteria: kill/restart test — enqueue N envelopes incl. one pending approval, restart process, all N recovered with statuses intact and no duplicate execution; SLO measurable: zero lost pending approvals across restart.
- Proof required: restart-test transcript with envelope IDs matched before/after.
- Tests to add/run: new tests/test_governed_spine_durability.py (in-process restart simulation).
- Rollback plan: recovery path behind a flag; disable flag reverts to in-memory behavior.
- Expected output: durable queue recovery + replay contract doc section.
- Parallelizable: yes (after 006 lands)
- Requires human approval: yes
- Phase: P1

### WP-P1-013: Introduce a canonical StateCommit primitive and unify the commit ledgers

- Closes: GAP-B3-005
- Current state: no StateCommit primitive exists; four disjoint ledgers record state changes — `substrate/organism/execution_ledger.py:29`, `substrate/state/transformation_state_ledger.py:205`, MutationRecord via `substrate/organism/mutation_router.py:53`, and memory receipts; `MutationResponse` lacks before/after hashes and any rollback reference; there is no unified commit log enabling replay or rollback.
- Desired state: canonical `StateCommit` (registered in canonical_types.py) emitted by the spine outcome stage — operation id, before/after state hashes, authority, rollback reference; existing ledgers become indices over the commit log.
- Files to inspect: substrate/organism/execution_ledger.py, substrate/state/transformation_state_ledger.py, substrate/organism/mutation_router.py, substrate/organism/governed_spine.py (outcome stage), substrate/types.py
- Files likely modified: substrate/types.py (new StateCommit), substrate/canonical_types.py (registration), substrate/organism/governed_spine.py, substrate/organism/mutation_router.py (MutationResponse gains commit reference)
- Forbidden files/actions: type-coherence law — check canonical_types.py first, register after defining; no Neon schema change in this packet (commit log persists through existing ledger stores; DB table is a follow-up CRITICAL packet if needed); Python 3.11.
- Dependencies: WP-P0-001, WP-P1-001
- Risk class: HIGH (touches mutation_router and governed_spine)
- Approval required: yes — defines the platform's commit/rollback contract.
- Acceptance criteria: every governed mutation produces exactly one StateCommit retrievable by operation id; MutationResponse carries commit id; rollback reference resolves; existing ledger writes unchanged (additive).
- Proof required: end-to-end trace of one mutation showing StateCommit emission and ledger indexing; pytest output.
- Tests to add/run: new tests/test_state_commit.py; run tests/test_c34_mutation_router.py.
- Rollback plan: StateCommit emission is additive; disable emission flag + git revert.
- Expected output: new registered primitive + spine emission + ledger indexing.
- Parallelizable: yes (after 006)
- Requires human approval: yes
- Phase: P1

### WP-P1-014: Unify the PolicyDecision verdict envelope and CONDITIONAL executability semantics

- Closes: GAP-B3-011
- Current state: the policy verdict is split: `GovernanceVerdict` (`substrate/types.py:280-282`) excludes CONDITIONAL from executable; `PipelineGovernanceVerdict` (`substrate/types.py:301-306`) permits CONDITIONAL when conditions are verified; condition enforcement is unimplemented on the signal path — two executability laws for one decision type.
- Desired state: a single verdict type with a scope discriminator and one executability law; condition verification implemented (deterministically) before a CONDITIONAL verdict becomes executable.
- Files to inspect: substrate/types.py:269-306, substrate/control_plane/governance.py (verdict producers), all grep hits consuming either verdict class
- Files likely modified: substrate/types.py, substrate/control_plane/governance.py, verdict consumers, substrate/canonical_types.py
- Forbidden files/actions: deterministic-first — condition checks are rules, not LLM judgments; type-coherence registration; do not weaken the stricter law by default (converge on GovernanceVerdict semantics unless approval says otherwise).
- Dependencies: WP-P0-009
- Risk class: HIGH (control-plane policy semantics)
- Approval required: yes — chooses the executability law for CONDITIONAL verdicts platform-wide.
- Acceptance criteria: one verdict class registered; CONDITIONAL is executable only through an implemented, tested condition-verification path; grep shows zero consumers of the retired class name (alias allowed with DeprecationWarning).
- Proof required: pytest matrix over verdict × condition states; grep inventory.
- Tests to add/run: new tests/test_policy_verdict_unification.py.
- Rollback plan: alias-based; git revert.
- Expected output: unified verdict envelope + condition enforcement.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P1

### WP-P1-015: Resolve Trace name collision and declare trace-store authority

- Closes: GAP-B3-009
- Current state: `substrate/types.py:462` aliases `Trace = TraceRecord` while `substrate/observability/trace_store.py:36` defines an unrelated class `Trace`; persistence is dual — Neon `traces` table (`substrate/execution/trace.py:81-126`) vs JSONL TraceStore — with no reconciliation; SpineLineage is a third lifecycle record.
- Desired state: one `Trace` name resolving to one type; one authoritative store (or a declared authority + sync contract between Neon and JSONL); spine lineage events unified into a TraceEventType taxonomy.
- Files to inspect: substrate/types.py:460-462, substrate/observability/trace_store.py:26-69, substrate/execution/trace.py, substrate/control_plane/invariants/spine_lineage_contracts.py
- Files likely modified: substrate/observability/trace_store.py (rename class), substrate/types.py, substrate/canonical_types.py, authority declaration in module docstrings + architecture doc
- Forbidden files/actions: `substrate/execution/trace.py` is CONFIRMED_RUNTIME — additive changes only; no Neon schema change; no silent except-pass (coordinates with WP-P0-009).
- Dependencies: WP-P0-009 (dead-letter path defines the sync failure mode)
- Risk class: MEDIUM (rename + authority declaration; runtime write paths preserved)
- Approval required: no — single-owner naming per Type Coherence Law; authority declaration is documentation of existing primary (Neon).
- Acceptance criteria: `from substrate.types import Trace` and observability imports resolve to distinct, correctly named types with no shadowing; check_type_divergence.py passes; authority contract documented and referenced from both modules.
- Proof required: import transcript; divergence-gate output.
- Tests to add/run: extend tests/test_trace_recorder.py with name-resolution assertions.
- Rollback plan: git revert (rename is mechanical).
- Expected output: collision-free trace types + declared state authority for trace events.
- Parallelizable: yes
- Requires human approval: no
- Phase: P1

### WP-P1-016: Typed ProofContract and single proof-artifact envelope

- Closes: GAP-B3-003, GAP-B3-007
- Current state: two same-name `ProofPackage` classes with incompatible schemas — `substrate/organism/proof_runtime.py:51` (before/action/after; registered at canonical_types.py:752) vs `substrate/organism/proof_store.py:33` (files_changed/verification_results; unregistered). ProofContract exists only as a stage marker + string lists: `substrate/control_plane/invariants/spine_lineage_contracts.py:51` (SpineStage.PROOF_CONTRACT) and `nodes/environments/work_packet.py:64,75` (`proof_requirements: list[str]`); the coherence validator (`substrate/control_plane/invariants/spine_coherence_validator.py:229`) checks existence, not content.
- Desired state: one registered proof envelope with one proof_id namespace (rename or merge the two ProofPackage classes); a typed ProofContract binding required proof-artifact types + acceptance criteria to the operation before execution; validator checks contract content.
- Files to inspect: proof_runtime.py, proof_store.py, substrate/execution/proof_generator.py, spine_lineage_contracts.py, spine_coherence_validator.py, nodes/environments/work_packet.py
- Files likely modified: proof_store.py (rename class), substrate/types.py or proof_runtime.py (ProofContract type), substrate/canonical_types.py, spine_coherence_validator.py
- Forbidden files/actions: type-coherence law; do not delete stored proof artifacts (data plane is append-only here); no schema migration.
- Dependencies: WP-P1-013 (StateCommit links proofs to commits)
- Risk class: MEDIUM (modifying proof modules; no core-spine behavior change)
- Approval required: no — naming convergence + typed contract are mechanical under existing laws.
- Acceptance criteria: single registered proof envelope; typed ProofContract present on operations that declare proof requirements; coherence validator asserts contract fields; divergence gate passes.
- Proof required: pytest output; a sample operation record showing typed contract → produced artifacts linkage.
- Tests to add/run: new tests/test_proof_contract_typed.py.
- Rollback plan: git revert; rename shim preserves old import path for one release.
- Expected output: typed proof primitives, registered.
- Parallelizable: yes
- Requires human approval: no
- Phase: P1

### WP-P1-017: Declare one canonical operator-intent kernel; demote the rivals to adapters
- Closes: GAP-E2-001
- Current state: four executable operator-intent entry points coexist with no declared state authority: (a) `substrate/organism/dex_conversation.py` — the live chat path via `transports/api/cockpit_chat_routes.py:178` `POST /dex/converse` and the Discord handler; (b) `substrate/organism/orchestrator_kernel.py` — phase13_0 kernel wired via `transports/api/organism_bridge.py:1782`; (c) `substrate/organism/operator_loop_coordinator.py:79` `OperatorLoopCoordinator` (renamed from jarvis_loop_coordinator) wired via organism_bridge:2098,2168; (d) `substrate/organism/operator_loop_runtime.py:3` ("This IS the product … the thing the operator talks to") with its own route family mounted at `transports/api/cockpit.py:463-468`. Each accepts operator intent through separate routes with separate session/turn models.
- Desired state: a state-authority record (doc + code comment headers) names ONE canonical kernel; the other three become documented facades/adapters that delegate to it (or are archived per dormant-classification), so an operator utterance has exactly one intake, one session model, one approval interlock regardless of surface (chat, Discord, voice, operator-loop routes).
- Files to inspect: substrate/organism/dex_conversation.py; substrate/organism/orchestrator_kernel.py; substrate/organism/operator_loop_coordinator.py; substrate/organism/operator_loop_runtime.py; transports/api/cockpit_chat_routes.py:170-200; transports/api/organism_bridge.py:1780-1790,2090-2175; transports/api/cockpit.py:460-470; docs/canonical/umh_synthesis.md §7.
- Files likely modified: the three demoted kernels (delegation shims); one new state-authority record under docs/ or data/umh/; route files re-pointed.
- Forbidden files/actions: never remove a confirmed-working live path (dex_conversation serves production Discord/chat) before its facade is proven; substrate/ must not import transports/; no LLM call without deterministic fallback in the unified intake.
- Dependencies: WP-P1-007 (approval state-machine unification), WP-P1-001 (canonical mutation-submission entry)
- Risk class: HIGH (core operator loop — cognitive_loop-class infrastructure)
- Approval required: yes — changes the product's primary interaction path.
- Acceptance criteria: one kernel handles intent from chat, Discord, and operator-loop routes (trace events show a single kernel id); demoted modules contain no independent execution logic (grep for direct spine/LLM calls returns delegation only); the state-authority record exists and names the owner.
- Proof required: trace events from all three surfaces resolving to the same kernel; the authority record.
- Tests to add/run: tests/test_operator_kernel_authority.py (new: three-surface intake convergence); existing dex/operator-loop tests still green.
- Rollback plan: facades revert to their prior standalone implementations (kept in git history); route pointers reverted.
- Expected output: code change + state-authority record.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-018: Source mesh-dispatch node allowlist and cwd roots from the device registry
- Closes: GAP-E2-004
- Current state: `transports/api/_mesh_dispatch.py:22` hardcodes `_ALLOWED_NODE_IDS = frozenset({"windows-desktop"})` and lines 23-27 hardcode Windows cwd roots (`C:\dev\dev\`, `C:\dev\`, `D:\dev\`) in the platform transport layer. The mesh cannot scale past one executor node without a code edit, and the hardcoding violates the repo's instance-context and device-naming laws (`infra/device_registry.json` is the declared single source of truth).
- Desired state: allowlisted node ids and per-node permitted cwd roots loaded from `infra/device_registry.json` (executor-roled nodes), with per-node permission envelopes; adding a device requires a registry entry only.
- Files to inspect: transports/api/_mesh_dispatch.py; infra/device_registry.json; transports/node_mesh/server.py (node hello/roles); nodes/windows/umh_node/client.py (capability declaration).
- Files likely modified: transports/api/_mesh_dispatch.py; infra/device_registry.json (add `dispatch.allowed_cwd_roots` fields).
- Forbidden files/actions: never hardcode device display names (device-naming rule); do not widen the allowlist to allow-all as a shortcut — registry absent must fail closed; no raw subprocess (CPU gate) if any local execution added.
- Dependencies: WP-P2-010 (canonical RuntimeNode entity), WP-P0-003 (node-side permission envelope)
- Risk class: MEDIUM (modifying an existing dispatch guard; behavior-preserving for the current single node)
- Approval required: no — behavior-preserving refactor with fail-closed default.
- Acceptance criteria: dispatch to the current executor node still succeeds; dispatch to a node absent from the registry (or with no executor role) is rejected; a second registry entry enables a second node with zero code change (integration test with mocked registry).
- Proof required: passing dispatch contract test with two mocked registry nodes; rejection log for unregistered node.
- Tests to add/run: extend tests/test_mesh_dispatch_contract.py (registry-driven allowlist, cwd containment per node).
- Rollback plan: revert _mesh_dispatch.py to the frozen set.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P1

### WP-P1-019: Move conference-rooms state authority off unlocked flat JSON onto a durable store
- Closes: GAP-E3-005
- Current state: every room entity — servers, channels, messages, roles, meetings, invites, artifacts, audit log — persists via `_load`/`_save` to flat JSON files under `/var/lib/umh/rooms` (`transports/api/cockpit_rooms_routes.py:50-70`): no file locking, no transactionality, `JSONDecodeError` silently returns `[]` (data-loss masking — violates the no-silent-except rule), no tenant scoping, no rollback. This is the state authority for a multi-user surface that mints guest-invite JWTs.
- Desired state: rooms state in the platform Postgres (Neon) behind a repository module, with migrations, per-entity tables (or a documented jsonb-document design), corruption detection, and an audit-preserving one-time data move from the JSON files; interim hardening (flock + atomic rename + logged decode errors) acceptable as a first commit if the migration is split.
- Files to inspect: transports/api/cockpit_rooms_routes.py:40-120 (storage), 145-171 (permissions), 1901-1990 (meetings); transports/api/http/db/schema.ts (platform DB conventions); /var/lib/umh/rooms (runtime data inventory, count rows before move).
- Files likely modified: transports/api/cockpit_rooms_routes.py (storage layer extraction); new transports/api/rooms_store.py; new migration under the platform DB migrations path.
- Forbidden files/actions: never run the data move without row counts before/after (CRITICAL-change rule); keep all mutations inside `governed_mutation()` as they are today (cockpit_rooms_routes.py:29 imports it); no silent except-pass in the new store.
- Dependencies: none (interim hardening); migration sequenced after WP-P1-007 if approval records are co-located
- Risk class: CRITICAL (data move + schema addition)
- Approval required: yes — schema migration and live-data move.
- Acceptance criteria: pre/post row-count parity per collection; concurrent-write test produces no lost updates; corrupted-store simulation raises + logs instead of returning `[]`; all room endpoints behave identically through the new store (existing route tests green).
- Proof required: row-count parity table; concurrency test output; error-path log capture.
- Tests to add/run: new tests/test_rooms_store.py (CRUD, concurrency, corruption); existing rooms route tests.
- Rollback plan: store module is swappable behind the `_load/_save` interface — revert to JSON backend flag; JSON files retained untouched until parity verified for 7 days.
- Expected output: code change + schema migration.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

### WP-P1-020: Govern or quarantine the PhysicalAdapterRegistry execute path
- Closes: GAP-E3-007
- Current state: `substrate/execution/adapters/physical.py` ships a full sensor/actuator contract, registry, and a functional HomeAssistant adapter, but has ZERO dependents (query_graph-confirmed). Its docstring (:9) claims adapters are "governance-gated through the standard execution pipeline," yet `PhysicalAdapterRegistry.execute()` (:316-327, verified) calls `adapter.execute_action()` directly — no `governed_mutation()`, no risk classification, no permission envelope. If ever wired, physical actions (locks, switches) bypass the policy engine entirely.
- Desired state: `execute()` routes through the governed mutation contract with a physical-domain risk class (deny-by-default pending the safety envelope of WP-P2-030), OR the module is formally classified DORMANT/ISOLATE per the dormant-classification protocol with the misleading docstring corrected. Either way the governance claim and the code must agree.
- Files to inspect: substrate/execution/adapters/physical.py (full, 340 lines); substrate/organism/governed_spine.py (contract); substrate/organism/mutation_registry.py (register a `physical_action` mutation name).
- Files likely modified: substrate/execution/adapters/physical.py; substrate/organism/mutation_registry.py.
- Forbidden files/actions: substrate/ must not import transports/ (use the substrate-side governed spine, not transports/api/governed.py); no new Enum without checking canonical_types.py; physical execution stays deny-by-default until WP-P2-030 lands.
- Dependencies: WP-P2-030 (safety envelope) for any allow decision; none for the quarantine variant
- Risk class: MEDIUM (modifying a dormant module's execute method)
- Approval required: yes — establishes the trust posture for all future physical actuation.
- Acceptance criteria: `PhysicalAdapterRegistry.execute()` cannot reach `adapter.execute_action()` without a governance verdict (unit test asserts denial without verdict); docstring matches behavior; dormant disposition recorded if quarantined.
- Proof required: unit-test output for the deny path; the disposition record or the registered mutation spec.
- Tests to add/run: new tests/test_physical_adapter_governance.py.
- Rollback plan: revert physical.py (module is dormant — zero runtime blast radius).
- Expected output: code change (or disposition record if quarantine chosen).
- Parallelizable: yes
- Requires human approval: yes
- Phase: P1

### WP-P1-021: Define a durable-execution contract with declared recovery semantics (RPO/RTO)
- Closes: GAP-E2-009
- Current state: durability for operator-facing operations is single-host filesystem constructs: `substrate/organism/workcell_protocol.py:1-18` (inbox/ → inflight/ → processed/ atomic renames, "exactly-once delivery semantics without a database", checkpoint/resume, heartbeat) and JSONL session persistence in `substrate/organism/operator_session.py`. There is no DB-backed durable execution, no cross-node recovery, and no stated recovery SLO (RPO/RTO) anywhere inspected. Host loss = silent loss of in-flight operator work.
- Desired state: a written durable-execution contract (which operation classes require what durability), with the workcell protocol either journaled to Neon (write-ahead record per envelope transition) or explicitly declared single-host-best-effort; recovery SLO stated and tested (kill-process → restart → in-flight envelopes resume or surface as recoverable in the recovery dashboard).
- Files to inspect: substrate/organism/workcell_protocol.py; substrate/organism/workcell_daemon.py; substrate/organism/operator_session.py; substrate/canonical_types.py (WorkcellV2 types); transports/api/cockpit_recovery_dashboard_routes.py (surface for recoverables) [verify exact filename before edit].
- Files likely modified: substrate/organism/workcell_protocol.py (journal hooks); new docs/ contract file; possibly a new substrate/organism/execution_journal.py.
- Forbidden files/actions: do not break the existing rename-protocol atomicity; Python 3.11 syntax; no schema change without row-count discipline; substrate/ dependency direction.
- Dependencies: WP-P1-008 (governing the workcell protocol) — coordinate to avoid double-touching the same file
- Risk class: HIGH (core operation runtime durability semantics)
- Approval required: yes — changes recovery guarantees the operator relies on.
- Acceptance criteria: contract doc exists naming RPO/RTO per operation class; chaos test (SIGKILL mid-envelope) results in resume-or-recoverable within the declared RTO; no envelope silently lost (journal parity check).
- Proof required: chaos-test transcript; journal/inbox parity counts before and after kill.
- Tests to add/run: new tests/test_durable_execution_recovery.py (kill/restart/resume); existing workcell tests.
- Rollback plan: journal hooks behind a feature flag (default off until proven); revert flag.
- Expected output: code change + contract doc.
- Parallelizable: no
- Requires human approval: yes
- Phase: P1

---

## P2 — Primitive / type convergence (30 packets)

**Objective.** One canonical definition per platform primitive: risk, WorkPacket, Signal, Intent, ApprovalRequest (landed in P1), RuntimeNode, AgentRole/Instance, MemoryCandidate, EvaluationResult, Capability, ExecutionStep, ToolCall; the registry gate hardened to hold the line; operator-facing runtime authorities (presence, workstation, voice) declared.

**Entry criteria.** P1 canonical runtime declared (WP-P1-001); full-suite collection green (WP-P0-011).

**Exit criteria.** check_type_divergence.py --all exits 0; the canonical registry covers all public platform types; each contested primitive has exactly one registered owner; dormant runtime stacks have recorded dispositions.

### WP-P2-001: Harden the canonical type registry gate and add LEGACY_DUPLICATES burn-down tracking

- Closes: GAP-B1-011, GAP-B4-015
- Current state: `substrate/canonical_types.py` omits substrate/types.py's own contested types — Signal (types.py:990), Intent (753), the WorkPacket class (929; only its enums registered) — and all substrate/reality_model/ types; the registry the Type Coherence Law depends on is incomplete exactly where fragmentation is worst (canonical_types.py:29-76,244-259). The `LEGACY_DUPLICATES` allowlist (canonical_types.py:1286-1322, 17 modules, grandfathered since 2026-05-27, includes a third Capability enum) has no convergence tracking — no owner, no work item, no shrink requirement.
- Desired state: registry covers 100% of exported public types in substrate/types.py and substrate/reality_model/; `scripts/check_type_divergence.py` validates that every registry entry resolves to a real symbol (importlib) and compares definitions, not just names; each LEGACY_DUPLICATES entry carries an owner + work-packet reference, and a gate asserts the list only shrinks.
- Files to inspect: substrate/canonical_types.py (full), scripts/check_type_divergence.py, substrate/types.py export surface, substrate/reality_model/__init__.py
- Files likely modified: substrate/canonical_types.py, scripts/check_type_divergence.py, tests/test_type_divergence.py
- Forbidden files/actions: pre-commit gates run staged-only today — the full-scan mode must be additive (CI/manual), not a change that blocks unrelated commits on legacy debt; no type definitions moved in this packet (registration only).
- Dependencies: WP-P0-011 (collection must work for the gate test to run)
- Risk class: MEDIUM (modifies an enforcement script; wrong logic blocks commits)
- Approval required: no
- Acceptance criteria: `python3 scripts/check_type_divergence.py --all` resolves every registry entry via importlib (stale entries fail); registry-coverage test asserts 0 unregistered public types in the two target modules; LEGACY_DUPLICATES entries each name an owner/work-packet; monotonic-shrink check in place.
- Proof required: gate run transcript before/after; coverage count comparison (independent grep count vs registry count).
- Tests to add/run: extend tests/test_type_divergence.py.
- Rollback plan: git revert; gate changes are tooling-only.
- Expected output: hardened divergence gate + complete registry + burn-down metadata. Partially schema-only (registry entries) and tooling.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-002: Unify the risk taxonomy into one canonical enum and remediate same-name class/enum collisions
- Closes: GAP-G-011, GAP-C1-010, GAP-B1-004, GAP-B2-014, GAP-B3-013, GAP-D1-005
- Current state: four incompatible risk vocabularies traverse a single dispatch — `substrate/types.py:252-258` `RiskClass` (critical/high/medium/low/negligible/forbidden), `substrate/governance/risk_classes.py:17-66` `ActionRiskCategory` rebound to `RiskClass` with `# type: ignore[assignment]`, `nodes/windows/umh_node/governance.py:12-21` a raw string-list copy, `nodes/environments/work_packet.py:32-39` `EnvironmentEnvironmentPacketRiskLevel` (LOW/MEDIUM/HIGH/CRITICAL, also a botched-rename class name). Same-name collisions (unregistered duplicates violating the Type Coherence Law) degrade grounding repo-wide: two `Workcell` classes (`substrate/organism/workcell.py:128` vs `substrate/organism/workcell_protocol.py:130`), two `WorkloadType` enums (`substrate/organism/workload_runner.py:71` vs `substrate/organism/workload_placement_policy.py:28`), two event-spine modules, three `ExecutionSpine` classes; SignalEnvelope (`substrate/types.py:48` vs `substrate/sockets/envelopes.py:14`), SignalType (`substrate/organism/outcome_learning.py:41` vs `substrate/organism/cross_source_reconciler.py:43`), SignalSource (`substrate/types.py:14` vs `substrate/execution/runtime/execution_contracts_v1.py:48`), WorldModel (`substrate/organism/world_model.py:171` vs `substrate/understanding/world_model/world_model.py:134`), GapSeverity (strategic_gap_engine.py:64 vs world_model.py:66), GapType (`substrate/organism/self_use/gap_ledger.py:23` vs qualification_harness.py:148), GapEntry (self_use/gap_ledger.py:57 vs benchmarks/competitive.py:110), IntentClassification (intent_classifier.py:129 vs embodiment_runtime.py:45), IntentType (×3: embodiment_runtime.py:31, `substrate/organism/operator_session.py:91`, execution_contracts_v1.py:57), IntentRouter (`substrate/operator/intent_router.py:114` vs `substrate/control_plane/router/intent_router.py:30`), ExecutionQueue ×2 (`substrate/execution/queue.py:28` vs `substrate/organism/execution_coordinator.py:422`, only the latter registered at canonical_types.py:451), MemoryEntry/CanonicalMemoryEntry double collision (`substrate/types.py:97`, `substrate/state/memory/contracts/canonical_memory_store_v1.py:61` + alias, `substrate/organism/memory_promotion.py:132`), and RealityIntelligenceEngine ×2 with unrelated responsibilities (`substrate/reality_model/reality_intelligence.py:52`, registered at canonical_types.py:529, vs `substrate/understanding/reality/reality_engine.py:95` — an LLM market-signal scanner), where `tests/test_p1_phase4_world_model.py:132` verifies presence by source-text grep that can match either file.
- Desired state: one canonical risk taxonomy registered in `substrate/canonical_types.py`; the wire format uses its values; the node daemon imports or vendors a generated copy of the same enum; every colliding name resolves to exactly one canonical module — duplicates renamed (e.g. understanding RealityIntelligenceEngine → MarketSignalEngine; organism CanonicalMemoryEntry deleted, alias dropped; the botched `EnvironmentEnvironmentPacket*` names corrected) or converged and imported; all registered in canonical_types.py; test_p1_phase4_world_model.py asserts an import, not a text grep.
- Files to inspect: substrate/types.py:252-258; substrate/governance/risk_classes.py:17-66; nodes/windows/umh_node/governance.py:12-21; nodes/environments/work_packet.py:19-49; substrate/canonical_types.py; every collision site listed under Current state.
- Files likely modified: substrate/canonical_types.py; substrate/types.py; substrate/governance/risk_classes.py; nodes/environments/work_packet.py (rename); node governance vendored enum; the ~16 defining modules for the colliding names and their importers; tests/test_p1_phase4_world_model.py.
- Forbidden files/actions: check canonical_types.py first (type-coherence law); no new parallel type system; renames only where a consumer inventory (grep + graph) is attached as proof; no semantic merges unless schemas are identical (semantic convergence belongs to the per-primitive packets); pre-commit check_type_divergence.py must pass after.
- Dependencies: WP-P2-001 (the hardened gate must be able to hold the line after remediation)
- Risk class: MEDIUM (type unification + mechanical renames touching many call sites)
- Approval required: yes — cross-layer type change; wire-format compatibility must be preserved during rollout.
- Acceptance criteria: one risk enum is the single canonical definition; a dispatch VPS→mesh→node carries one taxonomy end-to-end; `check_type_divergence.py --all` reports zero same-name collisions for the listed names and no longer flags the risk types; per-name importlib resolution test passes; full grep inventory shows no stale references; the botched `EnvironmentEnvironmentPacket*` names are corrected; duplicate class names are unique.
- Proof required: before/after divergence-gate output; grep inventory per renamed symbol; grep showing a single canonical risk-enum import path.
- Tests to add/run: tests/test_risk_taxonomy_canonical.py; extend tests/test_type_divergence.py; run the import-smoke suite from WP-P0-008; run check_type_divergence.py --all.
- Rollback plan: git revert; retain compatibility shims until node daemons redeploy; renames are mechanical with no data impact.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P2
- Merged from: WP-DRAFT-PART1-018 + WP-DRAFT-PART2-016 (risk-vocabulary and name-collision fragmentation reported by the spine/trust and primitives/grounding workstreams).

### WP-P2-003: Drive the full-scan type-coherence gate to green
- Closes: GAP-A-005
- Current state: `scripts/check_type_divergence.py --all` exits 1 with 46 BLOCKED + 47 WARNING divergences, including `substrate/contracts/agent_types.py:87` `RoutingResult` diverging from `substrate/organism/empire_router`, `substrate/meta_ide/repository_model.py:65` `RepositorySnapshot`, and certification-test types (`TaskResult`, `CertificationReport`). Pre-commit runs staged-only, so these persist between commits.
- Desired state: full-scan gate green; divergent types imported from their canonical locations per PLATFORM_SPEC.md §9.
- Files to inspect: `scripts/check_type_divergence.py`; `substrate/contracts/agent_types.py:87`; `substrate/meta_ide/repository_model.py:65`; `substrate/canonical_types.py`; `PLATFORM_SPEC.md:543-571`; the 46 BLOCKED sites from the gate output.
- Files likely modified: the 46 divergent type definitions (import from canonical instead of redefining); `substrate/canonical_types.py` (register genuinely new types).
- Forbidden files/actions: no new parallel definitions; do not weaken the checker to pass; Python 3.11.
- Dependencies: WP-P2-002 (risk-type subset)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: `scripts/check_type_divergence.py --all` exits 0; every previously-BLOCKED type imports from its canonical location.
- Proof required: gate `--all` output showing 0 BLOCKED.
- Tests to add/run: run `check_type_divergence.py --all`; import-smoke of the touched modules.
- Rollback plan: revert per-file.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-004: Deduplicate the primitive-ontology type system (types.py vs primitive_decomposition_v1)

- Closes: GAP-D1-001
- Current state: `PrimitiveType`, `RelationshipType`, `PrimitiveObservation` are defined twice — Pydantic canonical set (substrate/types.py:528-591) and a dataclass copy (substrate/understanding/ontology/primitive_decomposition_v1.py:17-72). The entire L4 bridge layer consumes the legacy copy (substrate/understanding/domains/contract.py:14, business.py:13, creator.py:11, life.py:11), so domain projections are typed against the non-canonical variant. canonical_types.py:1307-1311 whitelists the divergence in LEGACY_DUPLICATES instead of scheduling convergence.
- Desired state: single definition in substrate/types.py; primitive_decomposition_v1 imports it; the LEGACY_DUPLICATES entries removed; L4 bridges typed against the canonical set.
- Files to inspect: substrate/types.py:528-591, substrate/understanding/ontology/primitive_decomposition_v1.py, substrate/understanding/domains/contract.py + business.py/creator.py/life.py, substrate/canonical_types.py:1307-1311
- Files likely modified: primitive_decomposition_v1.py (re-import), the four domain modules' imports, substrate/canonical_types.py
- Forbidden files/actions: dataclass→Pydantic behavioral differences (defaults, validation) must be diffed field-by-field before switch; no content changes to bridge keyword maps (that is WP-P3-015).
- Dependencies: WP-P2-001
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: one definition per name; bridges import from substrate.types; LEGACY_DUPLICATES entries 1307-1311 gone; tests/test_ontology_enacted.py passes.
- Proof required: field-level diff document; pytest output.
- Tests to add/run: run tests/test_ontology_enacted.py, tests/test_grounding_firewall.py.
- Rollback plan: git revert.
- Expected output: single primitive-ontology type system.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-005: Converge the four WorkPacket variants onto one canonical Operation record

- Closes: GAP-B1-009, GAP-B2-001, GAP-B2-013
- Current state: four shapes for the unit of execution with no mapping contract: `substrate/organism/work_packet.py:117` (organism dataclass, ~90 fields), `substrate/types.py:929` (Pydantic pipeline unit), `substrate/control_plane/router/router_contracts.py:91` (RouterWorkPacket), `nodes/environments/work_packet.py:49` (EnvironmentWorkPacket — dormant, 2 referencing files). `substrate/organism/organism_loop.py:34-45,332` bridges two of them with a per-execution alias-and-convert shim. Two consuming pipelines are themselves rivals (transports/api/signal_router.py vs organism queue).
- Desired state: one canonical L2 WorkPacket with formally mapped boundary DTOs (router view, environment view) and explicit converters; no per-call conversion shim in the primary loop; EnvironmentWorkPacket classified per the dormant protocol (PROMOTE into the mapping or ARCHIVE).
- Files to inspect: the four definitions above, organism_loop.py, substrate/canonical_types.py:74-76,106, all grep hits constructing any variant
- Files likely modified: substrate/organism/work_packet.py (canonical), substrate/types.py (deprecation alias), router_contracts.py (DTO derives from canonical), nodes/environments/work_packet.py (promote or archive), organism_loop.py, substrate/canonical_types.py
- Forbidden files/actions: type-coherence law; classify EnvironmentWorkPacket before removal (dormant protocol); do not break WorkPacketExecutionGate scalar interface without updating WP-P6-013 tests; Python 3.11.
- Dependencies: WP-P0-008 (imports must work first), WP-P1-001 (single pipeline decides which consumers remain)
- Risk class: HIGH (unit-of-execution model used by the primary loop)
- Approval required: yes — canonical-field decision for the platform's operation record.
- Acceptance criteria: exactly one WorkPacket registered as canonical; converters have round-trip tests; organism_loop shim removed; grep shows all constructors on canonical or a declared DTO; divergence gate passes.
- Proof required: round-trip pytest; one packet executed end-to-end through the converged loop with trace evidence.
- Tests to add/run: new tests/test_workpacket_canonical.py; run tests/test_work_state.py.
- Rollback plan: aliases keep old names importable; staged: converters first, shim removal last; git revert per stage.
- Expected output: canonical WorkPacket + mapped DTOs + converters.
- Parallelizable: no
- Requires human approval: yes
- Phase: P2

### WP-P2-006: Typed DesiredState primitive and Gap closure linkage

- Closes: GAP-B1-002, GAP-B1-007
- Current state: DesiredState exists nowhere as a type — represented as free text (`substrate/organism/work_packet.py:134` `desired_state: str` AND :121 `desired_end_state: str`, two redundant fields on one dataclass), untyped dict (`substrate/organism/strategic_planning_engine.py:64`), free-text `Gap.required_state`, and ungoverned JSON canons tested only for file existence (tests/test_phase14_4_trinity_alignment.py:106-150). The canonical Gap (`substrate/organism/strategic_gap_engine.py:183-240`) stores current_state/required_state as strings with no closure linkage — resolution traceability is one hop removed via `Recommendation.converted_packet_id` (lines 250-280), with no field recording which Operation closed the gap or re-detection identity across runs.
- Desired state: typed, versioned DesiredState record in substrate/reality_model/ with state-authority binding, acceptance criteria, and L3 inheritance hooks; Gap references CurrentState/DesiredState ids and carries resolution linkage (closing packet id, closed_at, verification result, stable re-detection identity); WorkPacket's two redundant string fields collapse to a DesiredState reference.
- Files to inspect: the four sites above + substrate/reality_model/canonical.py, substrate/reality_model/instance.py
- Files likely modified: new substrate/reality_model/desired_state.py, substrate/canonical_types.py, strategic_gap_engine.py, work_packet.py, strategic_planning_engine.py
- Forbidden files/actions: type-coherence registration; keep string fields as deprecated pass-throughs one release (reconciliation consumers read them); no LLM in gap-identity computation (deterministic hash of typed fields).
- Dependencies: WP-P2-005 (WorkPacket field ownership)
- Risk class: MEDIUM (new type LOW + modifying gap/planning engines MEDIUM)
- Approval required: no
- Acceptance criteria: DesiredState registered; a Gap created from a typed delta round-trips to closure with the closing operation id recorded; re-running detection yields the same gap identity; old string fields still populated during deprecation window.
- Proof required: pytest of gap lifecycle; sample gap record JSON before/after.
- Tests to add/run: new tests/test_desired_state_gap_linkage.py.
- Rollback plan: additive types; git revert removes references, string fields still authoritative until cutover.
- Expected output: DesiredState primitive + closure-linked Gap.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-007: Unifying EntityState record for CurrentState reconcilers

- Closes: GAP-B1-006
- Current state: "what is true now" is modeled six ways (InstanceObservation, CanonicalPattern, WorldEntity, RealitySnapshot, OperationalTruthSnapshot, EnvironmentSnapshot) and five reconcilers emit private report shapes: substrate/organism/environment_reconciler.py:26,79 (ReconciliationReport), substrate/organism/mesh_reconciler.py:92 (MeshReconcileReport), substrate/organism/projection_reconciliation_engine.py:103, substrate/organism/advisor_reconciliation.py:30 (ReconciliationIntent), substrate/organism/cross_source_reconciler.py:113 — no shared state-authority/source-of-truth precedence contract; reality_model types absent from canonical_types.py (substrate/reality_model/instance.py:30, canonical.py:37; also substrate/organism/world_model.py:145, empire_router.py:78).
- Desired state: one EntityState record (entity ref + authority + evidence + confidence + freshness) that reconcilers consume/emit; reality_model types registered; reconciler reports become views over EntityState deltas.
- Files to inspect: the five reconcilers + reality_model instance/canonical + world_model.py + empire_router.py
- Files likely modified: new substrate/reality_model/entity_state.py, substrate/canonical_types.py, the five reconcilers (emit adapters)
- Forbidden files/actions: type-coherence; do not change reconciler decision logic in this packet (shape convergence only); authority precedence comes from WP-P3-007 — reference, don't invent a second taxonomy.
- Dependencies: WP-P2-001; coordinates with WP-P3-007
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: EntityState registered; each reconciler's report convertible to a list[EntityState] with a tested adapter; registry coverage test includes reality_model.
- Proof required: adapter round-trip pytest; registry coverage diff.
- Tests to add/run: new tests/test_entity_state_record.py.
- Rollback plan: additive; git revert.
- Expected output: shared CurrentState record + adapters.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-008: Converge the four Intent lifecycles on CanonicalIntent

- Closes: GAP-B1-005
- Current state: four parallel intent lifecycles with no cross-references: CanonicalIntent (substrate/operator/intent_runtime.py:77-110), IntentContract (substrate/workstation/intent_contract.py:42), types.py Intent (753 — unregistered, untested), EngineeringIntent (meta_ide), plus an IntentReceipt store (canonical_types.py:220-222,545-546,767-772 registrations).
- Desired state: CanonicalIntent as the sole L2 intent record; the others become scoped views carrying `intent_id` references or are deprecated; types.py Intent removed or aliased.
- Files to inspect: intent_runtime.py, intent_contract.py, substrate/types.py:753, meta_ide EngineeringIntent site, canonical_types.py intent registrations
- Files likely modified: intent_contract.py (intent_id reference), types.py (deprecate Intent), canonical_types.py, meta_ide module
- Forbidden files/actions: type-coherence; consumer inventory before deprecating types.py Intent (it is untested — verify zero runtime constructors first).
- Dependencies: WP-P2-002 (IntentType/IntentRouter collisions resolved first)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: one registered intent record; all other intent types carry intent_id or are gone; grep shows no orphan constructors of deprecated types.
- Proof required: consumer inventory + pytest.
- Tests to add/run: new tests/test_intent_convergence.py.
- Rollback plan: git revert; references are additive.
- Expected output: single intent lifecycle with scoped views.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-009: Resolve the RuntimeSession homonym

- Closes: GAP-B2-003
- Current state: two identically named `RuntimeSession` classes with disjoint schemas, neither registered: substrate/organism/runtime_session.py:115 vs substrate/execution/runtime/runtime_session_registry_v1.py:35 (worker-binding variant).
- Desired state: the organism variant is canonical `RuntimeSession`; the worker-binding variant renamed (e.g. WorkerSessionBinding); both registered in canonical_types.py.
- Files to inspect: both modules + their importers (graph dependents)
- Files likely modified: runtime_session_registry_v1.py (rename), importers, substrate/canonical_types.py
- Forbidden files/actions: type-coherence; rename only with consumer inventory attached.
- Dependencies: WP-P2-001
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: both names registered and unique; imports resolve; divergence gate passes.
- Proof required: grep inventory + gate output.
- Tests to add/run: covered by WP-P6-013 registry tests; run import smoke.
- Rollback plan: git revert.
- Expected output: collision-free session types.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-010: One canonical RuntimeNode entity and node-identity state authority
- Closes: GAP-G-005, GAP-G-013, GAP-B2-004
- Current state: no single canonical RuntimeNode — node/device models coexist across code and registries with incompatible ID schemes and three role vocabularies: `infra/device_registry.json` ("vps"), `infra/umh_node_registry.json` ("umh-vps") read by `substrate/organism/umh_node_registry.py:38-92` (UMHNodeRecord; `last_seen` never updated — `:87` reads only), mesh `ConnectedNode` (`transports/node_mesh/integration/types.py:81-129`), organism `RuntimeNode` (`substrate/organism/runtime_graph.py:131-172`), `DeviceNodeProfile` (`substrate/organism/device_role_registry.py:54-64`), topology `UMHNodeRecord` (`substrate/organism/umh_node_topology.py:139`), and `ComputeNode` (`substrate/organism/compute_fabric_runtime.py:53`). ID joins are fragile (optional `mesh_node_id`/`device_id`; `substrate/organism/mesh_reconciler.py:75-79` falls back to raw node_id); `infra/state_authority_registry.json` keys (umh-vps/umh-windows) never meet live mesh/runtime IDs, and the state-authority-bearing registry has 1 consumer while `device_registry.json` has ≥10. Live state persists to two divergent snapshot files (`data/runtime/mesh_nodes.json`, `data/umh/organism/mesh_metrics.json` — runtime artifacts written by the live deployment, absent from a fresh checkout); `state_authority_registry.json` says runtime authority is "in_memory" — no durable execution record for mesh dispatches.
- Desired state: one canonical RuntimeNode entity in L2 (UMHNodeRecord as the base, registered in `substrate/canonical_types.py`) with `node_id` as the join key and a single role enum; the registries and the other code models projected/derived from it or retired to views; a resolution function maps `device_registry.json` ids ↔ node ids (shared key or mapping table); a registry-lint cross-validates all sources; a declared state authority for node lifecycle (who writes what, freshness SLO); one snapshot schema; heartbeat-driven `last_seen` in the canonical record; runtime endpoints modeled separately from identity.
- Files to inspect: infra/device_registry.json; infra/umh_node_registry.json; infra/state_authority_registry.json; substrate/organism/umh_node_registry.py; substrate/organism/umh_node_topology.py; transports/node_mesh/integration/types.py; substrate/organism/runtime_graph.py; substrate/organism/device_role_registry.py; substrate/organism/compute_fabric_runtime.py; substrate/organism/mesh_reconciler.py:75-212; consumers of device_registry.json (incl. cockpit/src/renderer/constants/devices.ts per the device-naming protocol).
- Files likely modified: canonical RuntimeNode in substrate/organism/ + substrate/canonical_types.py; umh_node_topology.py; runtime_graph.py; compute_fabric_runtime.py; device_role_registry.py; mesh_reconciler.py; snapshot writers; infra/umh_node_registry.json (mapping fields); new scripts/check_node_registry_coherence.py.
- Forbidden files/actions: no additional node model — check canonical_types.py first; Device Naming Protocol — never hardcode device display names; infra/device_registry.json remains the display-name source for UI (do not break cockpit consumers); no hardcoded /opt/OS paths (use UMH_ROOT); mesh WS :8094 is a host process — no restart assumptions; no device names as literals in substrate.
- Dependencies: WP-P2-001; WP-P2-002 (role/risk enums)
- Risk class: HIGH (node registries feed mesh dispatch and the cockpit)
- Approval required: yes — declares the state authority for node identity across devices; foundational entity change under multiple consumers.
- Acceptance criteria: one RuntimeNode definition registered; all registries derive from or validate against it; the lint cross-validates and fails on an injected mismatch; a resolution function maps device_registry ids ↔ node ids with tests; `last_seen` updates from heartbeats; one snapshot schema in use; ≥1 previously divergent consumer migrated; /workspace/mesh-nodes output unchanged for existing clients (display fields).
- Proof required: lint output; a heartbeat updating canonical `last_seen`; id-mapping test output; mesh-nodes API response diff (empty for display fields).
- Tests to add/run: tests/test_runtime_node_canonical.py; tests/test_node_identity_authority.py; run the registry-coherence lint.
- Rollback plan: mapping/derivations are additive; keep legacy registries as read-only shims during rollout; git revert.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P2
- Merged from: WP-DRAFT-PART1-023 + WP-DRAFT-PART2-022 (node-identity fragmentation reported by the runtime-node-trust and primitives workstreams).

### WP-P2-011: One adapter contract with governance/trace fields; every adapter in one capability registry
- Closes: GAP-G-006, GAP-B2-005
- Current state: competing adapter contracts run simultaneously: the declared `adapters/protocol.py:10-19` async AdapterRequest/AdapterResponse Protocol is implemented by exactly one file (`adapters/models/llm_adapter.py:16-91`); `adapters/tool_adapters/base.py:12-50` ABC (4 impls); `substrate/execution/executor.py:23-31` sync dict `AdapterProtocol` (carries live traffic); `adapters/adapter_engine/adapter_manifest.py:39-60` descriptive manifests (16 production manifests, `adapters/adapter_engine/production_manifests.py:22-353`); plus duck-typed node-daemon adapters and node-proxy `IntegrationManifest`. AdapterRequest carries only id/adapter_id/payload/timeout — no trace_id, capability_id, governance-verdict id, permission envelope, or idempotency key; AdapterResponse is registered (canonical_types.py:45) but AdapterRequest is not (substrate/types.py:624 context). `adapters/socket_registration.py:5` claims to be "the ONLY file that bridges adapters → substrate/sockets," but broadcast, github, tailscale, browser_auth, browser_exports, adapter_engine, and data_source_adapters bypass it.
- Desired state: converge on one adapter contract (typed request/response + `classify_risk` + `health_check` + `capabilities()`) in which AdapterRequest carries trace_id, capability_id, governance-verdict id, permission envelope, and idempotency key; a durable AdapterCall trace event exists per invocation; the executor dict path becomes a compatibility wrapper; every adapter registers through `socket_registration.py` into one capability registry; `adapters/protocol.py` enforced via pre-commit or deprecated in favor of the chosen canonical contract.
- Files to inspect: adapters/protocol.py:10-19; adapters/models/llm_adapter.py:16-91; adapters/tool_adapters/base.py:12-50; substrate/execution/executor.py:23-31; adapters/adapter_engine/adapter_manifest.py:21-60; adapters/adapter_engine/production_manifests.py:22-353; adapters/socket_registration.py:5-192; substrate/types.py:624; live adapter implementations under adapters/.
- Files likely modified: adapters/protocol.py; substrate/execution/executor.py; substrate/canonical_types.py; substrate/execution/trace.py (AdapterCall event type); the adapter families that bypass registration; adapters/socket_registration.py; new scripts/check_adapter_contract.py.
- Forbidden files/actions: dependency direction — substrate/ defines the contract, adapters/ implement it (substrate must not import concrete adapters; adapters may import substrate); no new competing contract; CPU gate for any subprocess-backed adapter; credential-injection law for any adapter carrying auth; register capability types in canonical_types.py.
- Dependencies: WP-P1-015 (trace taxonomy); WP-P2-005 (canonical WorkPacket); coordinates with WP-P2-018 (capability registry record design overlaps)
- Risk class: HIGH (the executor carries live traffic; the adapter contract is a published platform contract — breaking-change process if fields become required)
- Approval required: yes — cross-adapter contract convergence with broad reach.
- Acceptance criteria: one contract is canonical and documented; a live adapter call emits an AdapterCall trace event containing trace_id + capability_id; the dict-path wrapper round-trips; every adapter registers through socket_registration.py; the new checker fails on an unregistered adapter; existing adapters pass their tests unmodified or with mechanical updates.
- Proof required: trace-event sample from a real adapter invocation; checker output; grep showing all adapters registered.
- Tests to add/run: tests/test_adapter_contract.py; run the new adapter-contract checker --all.
- Rollback plan: the wrapper preserves the dict path; flag-gated trace emission; git revert per adapter family.
- Expected output: code change (+ enforcement script).
- Parallelizable: no
- Requires human approval: yes
- Phase: P2
- Merged from: WP-DRAFT-PART1-022 + WP-DRAFT-PART2-023 (adapter-contract fragmentation reported by the trust and primitives workstreams).

### WP-P2-012: Canonical ExecutionStep primitive

- Closes: GAP-B2-007
- Current state: no ExecutionStep primitive; ≥9 unshared step types (ExecutableStep, CompositionStep, PipelineStep, ActionStep/FuncStep, WorkflowStep, TemplateStep, VerificationPlanStep, PreparationStep, ProvisionStep) across substrate/organism/plan_execution_adapter.py:122, substrate/execution/bridge/task_pipeline.py:66,97, substrate/organism/composition_engine.py:36,117, substrate/control_plane/runtime/orchestrator/pipeline.py:42-100; spine stages are strings/comments (substrate/execution/spine.py:172-435); duplicate StepStatus enums (composition_engine.py:36 vs task_pipeline.py:66).
- Desired state: canonical ExecutionStep with trace linkage; spine stages typed; the step types converge to it or formally derive; one StepStatus enum.
- Files to inspect: the step-defining modules above
- Files likely modified: substrate/types.py (ExecutionStep), substrate/canonical_types.py, step-defining modules (derivation), spine stage typing
- Forbidden files/actions: type-coherence; do not alter spine control flow (typing only); coordinate with WP-P1-001 on which spine's stages get typed first.
- Dependencies: WP-P1-001, WP-P2-005
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: ExecutionStep registered; one StepStatus; ≥3 of the 9 step types derive from or convert to it with tests; spine stages enumerable programmatically.
- Proof required: pytest + registry diff.
- Tests to add/run: new tests/test_execution_step.py.
- Rollback plan: additive; git revert.
- Expected output: canonical step primitive; derivation plan for remaining step types.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-013: Canonical ToolCall primitive and model-adapter tool-use support

- Closes: GAP-B2-008
- Current state: no ToolCall type anywhere; the model adapter layer has no tool-use support at all — grep-negative for tools=/tool_choice/function_call across adapters/models/*.py (only adapters/models/hermes_cli.py:131 touches the concept); tool references elsewhere are list[str] (substrate/organism/work_packet.py required_tools; substrate/types.py:1127).
- Desired state: typed ToolCall record (name, args, result, verdict, trace linkage) emitted by model adapters and agent runtimes; adapters/models gains a tool-use pass-through consistent with the router contract (return None/empty on failure).
- Files to inspect: adapters/models/model_router.py, adapters/models/llm_adapter.py, adapters/models/hermes_cli.py, adapters/models/cc_sdk.py, substrate/types.py
- Files likely modified: substrate/types.py (ToolCall), substrate/canonical_types.py, adapters/models/* (tool plumbing), substrate/execution/trace.py (event type)
- Forbidden files/actions: never hardcode `anthropic.Anthropic()` — all calls via model_router.call_with_fallback; provider contract preserved (None/empty on failure); deterministic-first (tool-call parsing failures degrade to no-tools response, not a crash); cc_sdk timeout/env rules untouched.
- Dependencies: WP-P2-011 (AdapterCall trace event), WP-P1-015
- Risk class: MEDIUM (model_router is CONFIRMED_RUNTIME — additive parameters only)
- Approval required: no
- Acceptance criteria: ToolCall registered; a routed call with a tool definition emits typed ToolCall records in the trace; all providers without tool support degrade cleanly (tested).
- Proof required: trace sample from a live routed call; pytest with provider fakes.
- Tests to add/run: new tests/test_tool_call_primitive.py.
- Rollback plan: additive; feature-flag tool plumbing; git revert.
- Expected output: ToolCall primitive + adapter tool-use plumbing.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-014: Converge AgentRole and the permission vocabulary; purge founder-shaped defaults

- Closes: GAP-B2-009, GAP-B2-015, GAP-B2-016
- Current state: agent-role fragmented across 4+ models with 4 permission vocabularies: AgentRole with scopes (substrate/execution/bridge/roles.py:48), Role with permission_tier/autonomy_level (substrate/types.py:1108), RoleContract (substrate/organism/role_contracts.py:66), AgentType with permissions/max_risk_class (substrate/organism/agent_registry.py:19), plus PipelineAgentRole enum (substrate/execution/bridge/task_pipeline.py:78-81); none named AgentRole is registered. task_pipeline.py:81 cites non-existent `substrate.roles` (actual: substrate.execution.bridge.roles). RoleRegistry.default() seeds founder-interface literals (ea_orchestrator/ceo/portfolio_advisor) inside substrate/ (roles.py:70-110) — an instance-context leak.
- Desired state: one role metamodel (types.py Role) with a single permission-envelope vocabulary; other role types derived; stale comment corrected; default roles loaded from runtime registration/BIS, not literals in substrate/.
- Files to inspect: the five role modules above
- Files likely modified: roles.py (defaults externalized + derivation), role_contracts.py, agent_registry.py, task_pipeline.py (comment), substrate/canonical_types.py, a BIS/config seed location for default roles
- Forbidden files/actions: instance-context law — no founder/venture literals remain in substrate/ (check_instance_leak.py must pass without new exemptions); permission changes are governance-relevant — no widening of any role's envelope during convergence.
- Dependencies: WP-P2-001
- Risk class: MEDIUM (HIGH if authority_engine consumes these — verify before merge)
- Approval required: yes — permission-envelope vocabulary unification affects what agents may do.
- Acceptance criteria: one registered role metamodel; a permission-envelope comparison test proves no role gained authority; defaults come from registration/BIS; check_instance_leak.py passes.
- Proof required: before/after permission matrix; instance-leak gate output.
- Tests to add/run: new tests/test_agent_role_convergence.py.
- Rollback plan: git revert; old defaults kept as data-file fallback during transition.
- Expected output: single role metamodel + externalized defaults.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P2

### WP-P2-015: Durable AgentInstance record

- Closes: GAP-B2-010
- Current state: no AgentInstance primitive — running-agent identity is split across an in-memory runtime object (substrate/organism/agent_runtime.py:31 AgentRuntime), a worker record (substrate/organism/worker_registry.py:33 WorkerInstance), and dispatch records (substrate/organism/agent_fleet_runtime.py:76 FleetAssignment) with no join key; substrate/organism/role_contracts.py:3-4 prose promises instances that have no type.
- Desired state: durable AgentInstance record: role binding, node, session, status, spawn lineage; the three existing records carry agent_instance_id.
- Files to inspect: agent_runtime.py, worker_registry.py, agent_fleet_runtime.py, role_contracts.py
- Files likely modified: new type in substrate/types.py, substrate/canonical_types.py, the three record modules (join key)
- Forbidden files/actions: agents must be registered in Neon per UMH conventions — but no Neon schema change in this packet (id fields ride existing stores); type-coherence.
- Dependencies: WP-P2-009 (session type), WP-P2-014 (role binding), WP-P2-010 (node identity)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: AgentInstance registered; spawn→work→complete lifecycle test shows one id joining runtime, worker, and fleet records.
- Proof required: lifecycle pytest with joined records printed.
- Tests to add/run: new tests/test_agent_instance.py.
- Rollback plan: additive; git revert.
- Expected output: joinable running-agent identity.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-016: Canonical MemoryCandidate with unified promotion-status enum

- Closes: GAP-B3-004
- Current state: MemoryCandidate defined 4× with divergent schemas and status enums, zero canonical registration: substrate/types.py:786, substrate/organism/memory_promotion.py:74, substrate/memory/candidate_generator.py:33, adapters/adapter_engine/live_drive_docs_ingestion_pipeline_v1.py:183 (grep count in canonical_types.py = 0).
- Desired state: one registered MemoryCandidate; unified promotion-status enum; the adapter-side variant maps at the grounding boundary (L4 adapter, not a fourth schema).
- Files to inspect: the four defining modules + promotion consumers
- Files likely modified: substrate/types.py (canonical), memory_promotion.py, candidate_generator.py, live_drive pipeline (boundary mapper), substrate/canonical_types.py
- Forbidden files/actions: memory promotion is a governance mechanic — do not auto-promote anything during migration; type-coherence; adapters/ may import substrate types, never the reverse.
- Dependencies: WP-P2-002 (MemoryEntry collision resolved first)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: one registered MemoryCandidate + one status enum; adapter variant converts via a tested mapper; promotion pipeline round-trips.
- Proof required: pytest; registry diff.
- Tests to add/run: new tests/test_memory_candidate_canonical.py; run tests/test_memory_system.py.
- Rollback plan: git revert; mappers preserve old shapes at boundary.
- Expected output: single memory-promotion input type.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-017: Canonical EvaluationResult and single DimensionScore

- Closes: GAP-B3-008
- Current state: no canonical EvaluationResult; 12+ scattered score/verdict types (FeedbackRecord substrate/types.py:474 vs FeedbackEntry substrate/execution/feedback_loop.py:72 vs QualityVerdict, EvalResult, TrustScore, …); `DimensionScore` defined three times: substrate/organism/readiness_model.py:47, substrate/organism/template_governance.py:86, substrate/organism/trust_score.py:57.
- Desired state: canonical EvaluationResult carrying criteria reference and evaluator method; single DimensionScore imported by the three consumers; feedback types converge or derive.
- Files to inspect: the modules above + substrate/execution/feedback.py
- Files likely modified: substrate/types.py, substrate/canonical_types.py, readiness_model.py, template_governance.py, trust_score.py, feedback_loop.py
- Forbidden files/actions: type-coherence; scoring semantics unchanged (shape convergence only); feedback.py is CONFIRMED_RUNTIME — additive.
- Dependencies: WP-P2-001
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: EvaluationResult + one DimensionScore registered; the three former definitions import the canonical one; score values bit-identical across a fixture corpus before/after.
- Proof required: fixture-corpus score diff (empty); pytest.
- Tests to add/run: new tests/test_evaluation_result.py; run tests/test_trust_score.py.
- Rollback plan: git revert.
- Expected output: single evaluation vocabulary.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-018: Capability registry convergence — one joining record, one naming authority, router decision

- Closes: GAP-B4-001, GAP-B4-002, GAP-B4-006
- Current state: the Capability primitive is fragmented across 58 class definitions with no joining record — two sanctioned homonyms + 1 grandfathered enum + EmergentCapability, RuntimeCapability, CapabilityEntry, CapabilityDescriptor, CatalogEntry, CapabilityBinding etc., unlinked (substrate/canonical_types.py:91-110,1302; substrate/types.py:658; substrate/execution/runtime/capability_router.py:36; substrate/execution/bridge/capabilities.py:29; substrate/organism/capability_runtime.py:95). capability_router (28-capability enum + provider chains) is dormant — zero runtime dependents, test imports only (tests/test_stage1_acceptance_e2e.py:345, tests/test_phase14_8b_wave2.py:274) yet cited as a canonical type location in .claude/rules/type-coherence.md. An unregistered `CapabilityName` enum (substrate/organism/template_registry.py:66, 13 names) duplicates capability naming semantics.
- Desired state: one capability registry record (identity, schema, provider chain, maturity, evidence, revision pointer) with role-specific views; one capability naming authority referenced by templates; capability_router either wired into the canonical spine's capability dispatch or archived and de-referenced from the rules doc.
- Files to inspect: the six modules above + .claude/rules/type-coherence.md + tests/test_capability_catalog_slice_a.py
- Files likely modified: a canonical capability module (likely substrate/organism/capability_runtime.py or new substrate/capabilities.py), substrate/canonical_types.py, template_registry.py, capability_router.py (wire or archive), .claude/rules/type-coherence.md
- Forbidden files/actions: dormant-classification protocol before archiving capability_router (PROMOTE/MERGE/ISOLATE/ARCHIVE/DELETE); type-coherence; capabilities must remain Neon-registered per UMH conventions — registry record changes must not orphan Neon rows.
- Dependencies: WP-P2-001
- Risk class: HIGH (capability registry is the platform's capability source of truth)
- Approval required: yes — capability record schema and the router wire-or-archive decision are architecture decisions.
- Acceptance criteria: one registered joining record; every one of the 58 definitions classified (converge/view/archive) in an attached inventory; one naming authority; rules doc matches reality; divergence gate passes.
- Proof required: 58-row classification inventory (independent grep count must equal 58); pytest.
- Tests to add/run: new tests/test_capability_registry_record.py; run tests/test_capability_catalog_slice_a.py.
- Rollback plan: staged: joining record additive first; archival last; git revert per stage.
- Expected output: capability registry convergence + classification inventory.
- Parallelizable: no
- Requires human approval: yes
- Phase: P2

### WP-P2-019: CapabilityPathway and CapabilityRevision primitives

- Closes: GAP-B4-003, GAP-B4-004
- Current state: CapabilityPathway missing — "pathway" exists only in prose (substrate/ontology/laws.py:152; transports/api/signal_router.py:1; substrate/organism/source_truth_runtime.py:48-61); provider chains are literals inside capability_router; no governed intent→execution route object. CapabilityRevision missing — capability definitions have no versioning; EvolutionEvent (substrate/organism/capability_evolution_engine.py:59-77,21) records observed before/after state only; no rollback pointer; grep "class .*Revision" = 0.
- Desired state: first-class pathway object (stages, policy gates, fallback, SLO, rollback) and immutable revision records per capability-definition change linked to approvals.
- Files to inspect: capability_evolution_engine.py, capability_router.py, the canonical capability record from WP-P2-018
- Files likely modified: new substrate modules for pathway + revision, substrate/canonical_types.py, capability_evolution_engine.py (emit revisions)
- Forbidden files/actions: type-coherence; revisions are append-only (never rewrite history); approval linkage uses WP-P1-007's canonical ApprovalRequest.
- Dependencies: WP-P2-018, WP-P1-007
- Risk class: LOW (new files/types) escalating to MEDIUM where evolution engine is modified
- Approval required: no
- Acceptance criteria: both types registered; a capability-definition change produces an immutable revision with rollback pointer; a pathway object drives one dispatch in tests.
- Proof required: pytest; sample revision chain JSON.
- Tests to add/run: new tests/test_capability_pathway_revision.py.
- Rollback plan: additive; git revert.
- Expected output: capability lifecycle objects.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-020: Register template types in the canonical registry

- Closes: GAP-B4-005
- Current state: substrate/organism/template_registry.py:29-728 defines 12 template types of which only WorkspaceTemplate/WorkspaceTemplateRegistry are registered (canonical_types.py:373-385) — the divergence gate cannot protect TemplateCandidate/TemplateRegistry/etc.; CapabilityTemplate (substrate/organism/compounding_engine.py:65) is unmerged/unregistered.
- Desired state: all template types registered; CapabilityTemplate merged with the template family or registered as distinct with a documented boundary.
- Files to inspect: template_registry.py, compounding_engine.py, canonical_types.py:373-385
- Files likely modified: substrate/canonical_types.py (registrations only), possibly compounding_engine.py import
- Forbidden files/actions: registration only — no type moves or renames in this packet.
- Dependencies: WP-P2-001
- Risk class: LOW
- Approval required: no
- Acceptance criteria: registry entries resolve via importlib for all 12+1 types; divergence gate passes.
- Proof required: gate output; count check (grep class count vs registry count).
- Tests to add/run: extend tests/test_type_divergence.py.
- Rollback plan: git revert.
- Expected output: schema-only packet — registry entries, no behavior change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-021: Move cross-entrypoint daemon/singleton access behind organism_port and add the transports→services rule
- Closes: GAP-A-002, GAP-A-016
- Current state: `transports/api/cockpit_core_routes.py:115,143` import `_organism_daemon` and `_mesh_server_instance` from `services/operator_api.py`; `transports/api/webhooks/calendly_webhook.py:47` imports `services.higgsfield_webhook`. `scripts/check_dependency_direction.py` has no transports→services rule (IMPORT_RULES `:39-72`), so the daemon's state authority living in an entrypoint module's globals is silently reachable from transports. Separately, `services/operator_api.py:16` needs `import adapters  # lock correct resolution before execution_spine shadows it` — a top-level package shadowed by a substrate module's import behavior.
- Desired state: OrganismDaemon/mesh-server accessors exposed only through `substrate/sockets/organism_port.py` (already registered at `transports/api/cockpit_spine_router.py:50-51`); a `transports → services` rule added to the dependency checker; the `execution_spine` shadowing root cause fixed (rename/import hygiene) and the guard comment removed.
- Files to inspect: `transports/api/cockpit_core_routes.py:115,143`; `transports/api/webhooks/calendly_webhook.py:47`; `substrate/sockets/organism_port.py`; `transports/api/cockpit_spine_router.py:50-51`; `scripts/check_dependency_direction.py:39-72`; `services/operator_api.py:16`; `substrate/execution/runtime/execution_spine.py`.
- Files likely modified: `transports/api/cockpit_core_routes.py`; `transports/api/webhooks/calendly_webhook.py`; `scripts/check_dependency_direction.py`; `substrate/execution/runtime/execution_spine.py` (namespace fix); `services/operator_api.py` (remove guard).
- Forbidden files/actions: substrate must not import transports/services; add — do not remove — enforcement rules; Python 3.11.
- Dependencies: WP-P1-006 (execution_spine migration reduces shadowing surface)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: no transports file imports `services.*` singletons (accessed via organism_port); `check_dependency_direction.py` fails on an injected transports→services import; the `import adapters` guard comment is gone and imports resolve cleanly.
- Proof required: grep-clean transports→services; checker failure on injected violation; clean import of `services/operator_api.py` without the guard.
- Tests to add/run: run `check_dependency_direction.py --all`; import-smoke.
- Rollback plan: revert per-file.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: no
- Phase: P2

### WP-P2-022: Resolve the dormant duplicate API surfaces (TS Hono stack + dead operator.py)
- Closes: GAP-A-013, GAP-C2-008, GAP-C2-012, GAP-C2-013, GAP-A-014
- Current state: `transports/api/operator.py` is a 601-line near-duplicate of the deployed `services/operator_api.py` and is broken at import (`os` used at `:7` before `import os` at `:12` → NameError); it duplicates four mutation endpoints and violates the no-duplicate-definitions standard. `transports/api/http/` maintains a full parallel 137-handler Hono API not referenced by docker-compose/systemd (no running process found) with a broken mutation bridge (WP-P1-005) and TS mutation endpoints lacking `operatorGuard` (`organism.ts:416,441,449`, all of `execution.ts:106-137`, `chat.ts:8,23`, `settings.ts:49`, `governance.ts:47`). Separately, `services/discord_message_handlers.py:1200` imports the `_organism` singleton from the undeployed `transports/api/app.py`, whose module import constructs `SubstrateRuntime`/executor/`ExecutionPipeline`/pollers at module scope — a second, divergent organism accessor.
- Desired state: `transports/api/operator.py` deleted (deployment remains `services/operator_api.py`); the Hono tree either wired into deployment with a working governed bridge (WP-P1-005) and uniform `operatorGuard`, or marked DEPRECATED with frozen mutation handlers; the cross-entrypoint `_organism` import replaced by the `substrate/sockets/organism_port.py` accessor (WP-P2-021).
- Files to inspect: `transports/api/operator.py:4-12`; `transports/api/http/server.ts:15-60`; `transports/api/http/package.json:11`; `transports/api/http/routes/*.ts`; `services/discord_message_handlers.py:1200`; `transports/api/app.py:43-58`; `docker-compose.yml:174-177`.
- Files likely modified: delete `transports/api/operator.py`; add a DEPRECATED marker under `transports/api/http/` or wire it in; `services/discord_message_handlers.py` (accessor swap).
- Forbidden files/actions: do not delete without a dependents check; if wiring Hono in, use `bash cockpit/deploy.sh` for any cockpit-adjacent deploy; no module-scope organism construction on import.
- Dependencies: WP-P1-005, WP-P2-021
- Risk class: MEDIUM
- Approval required: yes — deprecation/deletion of a surface (working-feature decision).
- Acceptance criteria: `operator.py` is gone with no import references (grep); the Hono tree is either deployed-with-guards or clearly DEPRECATED; `discord_message_handlers` no longer imports `app._organism`.
- Proof required: grep-clean deletion; deprecation marker or deploy reference; accessor-swap grep.
- Tests to add/run: import-smoke of `services/discord_message_handlers.py`; TS `operatorGuard` presence check if wired in.
- Rollback plan: restore files from git.
- Expected output: code change (+ documentation deprecation marker).
- Parallelizable: no
- Requires human approval: yes
- Phase: P2

### WP-P2-023: Graduate shared domain types into the canonical type registry (WorkflowStep, broadcast scene models)
- Closes: GAP-E1-013, GAP-E3-012
- Current state: (a) `projections/eos/workflows/types.py:13` defines a `WorkflowStep` dataclass parallel to the Pydantic `WorkflowStep` in `substrate/types.py:1227` — a Type Coherence Law violation at the projection layer (entities.py imports the substrate one, workflows uses its own). (b) Broadcast domain models Scene/SourceEntry/SourceLayout/CompositeConfig live in `adapters/broadcast/scene_model.py` and are consumed from three surfaces (engine, capability handler `adapters/broadcast/integration/handlers.py`, routes `transports/api/cockpit_broadcast_routes.py`, Windows node adapter `nodes/windows/umh_node/adapters/broadcast.py`) — the documented graduation rule ("register in canonical_types.py when shared across subsystems", docs/superpowers/specs/broadcast/SLICE0_INVESTIGATION.md:92-101) is triggered but unexecuted.
- Desired state: EOS workflows either import the canonical WorkflowStep or rename theirs to a distinct `StepSpec` registered appropriately; broadcast scene models registered in `substrate/canonical_types.py` (re-export from the adapter module is acceptable — one definition, one registration).
- Files to inspect: projections/eos/workflows/types.py; substrate/types.py:1220-1240; projections/eos/workflows/runner.py (consumer); adapters/broadcast/scene_model.py; substrate/canonical_types.py; scripts/check_type_divergence.py.
- Files likely modified: projections/eos/workflows/types.py; substrate/canonical_types.py; possibly adapters/broadcast/scene_model.py (registration hook only).
- Forbidden files/actions: never redefine a canonical type — import or rename (type-coherence law); substrate must not import adapters upward for the registration (register by name/reference pattern used elsewhere in canonical_types.py — inspect precedent first).
- Dependencies: WP-P2-003 (type-coherence gate to green) — coordinate, don't duplicate
- Risk class: MEDIUM (renaming a type used by the EOS workflow runner)
- Approval required: no
- Acceptance criteria: `scripts/check_type_divergence.py --all` reports no WorkflowStep divergence and recognizes the broadcast models; EOS workflow runner tests pass; broadcast tests pass.
- Proof required: gate output before/after.
- Tests to add/run: tests for EOS workflows + tests/adapters/broadcast/; full type-divergence scan.
- Rollback plan: revert; divergence returns to tracked-known state.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-024: Declare one presence state authority; make the other presence modules views
- Closes: GAP-E2-005
- Current state: five overlapping presence modules answer the same "where is the operator / what device / what mode" questions with no canonical authority: `substrate/organism/presence_runtime.py` (Phase 8, self-described foundational layer), `substrate/operator/operator_presence.py` (+ presence_timeline), `substrate/workstation/device_presence.py` (in-memory cockpit session registry), `substrate/workstation/workstation_presence_runtime.py` (C17.2), `substrate/workstation/orchestrator_presence_runtime.py` (C17.0); four route surfaces in transports/api (cockpit_presence_routes.py mounted at cockpit.py:558, plus operator/orchestrator/workstation presence route files).
- Desired state: one presence state authority (recommend `substrate/organism/presence_runtime.py` as the base layer per its own contract) owning the presence record; the other four modules refactored to write into / read from it (views/projections); a state-authority record names the owner; the four route families keep their paths but serve from the single store.
- Files to inspect: the five modules above (full); transports/api/cockpit_presence_routes.py; transports/api/cockpit_operator_presence_routes.py; transports/api/cockpit_orchestrator_presence_routes.py; transports/api/cockpit_workstation_presence_routes.py [verify filenames via ls before edit]; substrate/organism/state_authority_graph.py (register the domain).
- Files likely modified: the four non-canonical presence modules; state_authority_graph domain registration; possibly route files (import targets only).
- Forbidden files/actions: do not break device_presence's cockpit session registration used by the live shell; substrate dependency direction; no route path changes (client compatibility).
- Dependencies: WP-P1-017 (kernel needs one presence read)
- Risk class: HIGH (presence feeds the operator loop and continuity behavior)
- Approval required: yes — touches live cockpit session behavior.
- Acceptance criteria: presence writes from any module land in one store (test: register device via device_presence, read via presence_runtime); the state-authority graph lists a single PRESENCE domain owner; all existing presence tests (tests/test_presence_runtime.py, test_device_presence.py, test_orchestrator_presence_runtime.py, test_workstation_presence_runtime.py) pass.
- Proof required: cross-module read-your-write test output; state-authority snapshot.
- Tests to add/run: the four existing presence suites + a new cross-module coherence test.
- Rollback plan: modules revert to independent stores (git revert; no data migration involved — presence is ephemeral).
- Expected output: code change + state-authority record.
- Parallelizable: no
- Requires human approval: yes
- Phase: P2

### WP-P2-025: Declare the workstation runtime source of truth and disposition the 33 dormant engines
- Closes: GAP-E2-006, GAP-E2-007
- Current state: three code generations claim the workstation concern: `substrate/organism/workstation_runtime.py` (1400L state model, WorkstationMode enum at :46), `substrate/workstation/unified_workstation_runtime.py` (C18.0, docstring claims "Single source of truth for workstation state", composes 7 runtimes, read-only), and `substrate/execution/workers/workstation/` (9 active relay/execution engines). Additionally 33 modules sit in `substrate/execution/workers/workstation/_dormant/` (browser embodiment stack, constitutional_* engines, relay/observability stack) with no PROMOTE/MERGE/ISOLATE/ARCHIVE/DELETE disposition record — violating the repo's own dormant-classification protocol. `docs/phase77_workstation_state_report.md` documents an `umh/workstation/` package that no longer exists.
- Desired state: a state-authority record declares `unified_workstation_runtime` (or a named successor) the authority; the organism-layer state model and workers engines documented as its inputs; every `_dormant/` module gets a written disposition (one line each: decision + rationale); ARCHIVE/DELETE decisions executed; phase77 doc superseded (see WP-P6-023 for the doc side).
- Files to inspect: substrate/organism/workstation_runtime.py:1-80; substrate/workstation/unified_workstation_runtime.py:1-40; substrate/execution/workers/workstation/ (ls all, incl. _dormant/); docs/phase77_workstation_state_report.md.
- Files likely modified: new disposition record (data/audits/ or docs/); _dormant/ modules moved/deleted per decision; docstring corrections in the two runtime files.
- Forbidden files/actions: dormant modules must be classified before removal (dormant-classification rule); worktrees/branches cleaned after merge (node-role discipline); no deletion of anything with live dependents (verify with query_graph + grep for lazy imports — the graph misses function-scoped imports, GAP-E2-015).
- Dependencies: WP-P6-022 (lazy-import indexing) improves confidence but is not blocking (grep compensates)
- Risk class: MEDIUM (mostly classification; deletions verified dependency-free)
- Approval required: yes — DELETE decisions on 33 modules.
- Acceptance criteria: disposition record covers all 33 files (count matches `find substrate/execution/workers/workstation/_dormant -name '*.py' | wc -l`); authority record exists; post-deletion import sweep clean (`python3 -c "import substrate"` + full test suite).
- Proof required: disposition table with per-file grep evidence of zero dependents for deletions; test-suite run.
- Tests to add/run: full pytest run; import check.
- Rollback plan: git revert restores archived/deleted modules.
- Expected output: disposition record + code removal/moves.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P2

### WP-P2-026: Finish the jarvis→operator rename residue in platform code
- Closes: GAP-E2-012, GAP-E2-016
- Current state: the bulk of the rename has landed since the E2 ledger snapshot — `substrate/organism/` now contains only `operator_acceptance{,_mode,_scenarios}.py` and `operator_loop_coordinator.py` (verified 2026-07-03; the ledger's `jarvis_acceptance*.py` / `jarvis_loop_coordinator.py` no longer exist). Residue: `substrate/workstation/jarvis_command.py` (compat shim) and jarvis references in `substrate/organism/tests/test_phase14_1_source_inspection.py` and `substrate/organism/tests/test_projection_reconciliation_engine.py` (grep-verified). The persona codename in platform module names is an instance-context smell per the repo's own rules.
- Desired state: shim retired after confirming zero importers (or documented with a removal date); test files updated to current module names; `grep -rln jarvis substrate/ --include='*.py'` returns zero; "Jarvis" survives only in docs/ as historical phase naming.
- Files to inspect: substrate/workstation/jarvis_command.py; substrate/organism/tests/test_phase14_1_source_inspection.py; substrate/organism/tests/test_projection_reconciliation_engine.py; grep -rn jarvis across transports/, services/, scripts/.
- Files likely modified: the three files above (delete shim / edit tests).
- Forbidden files/actions: do not remove the shim if any live import remains (grep + graph first); after refactor, check tests asserting on source-code strings still match (codebase-quality rule — these two tests do exactly that).
- Dependencies: none
- Risk class: LOW (shim removal + test string updates)
- Approval required: no
- Acceptance criteria: grep clean as above; the two source-inspection tests pass against renamed modules; import sweep clean.
- Proof required: grep output; pytest output for the two files.
- Tests to add/run: the two touched test files + full substrate/organism/tests run.
- Rollback plan: git revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-027: Converge the three voice stacks under one ingress contract and close real-microphone acceptance
- Closes: GAP-E2-002
- Current state: ≥3 parallel voice stacks: (a) `umh/voice_server.py` (WS :8096, Groq Whisper + faster-whisper fallback, Kokoro/espeak TTS); (b) C20 substrate runtimes (`substrate/workstation/voice_ingress_runtime.py`, `voice_session_manager.py`, ambient wake / operations / output / route-resolver siblings) wired via lazy imports in `transports/api/cockpit_voice_ingress_routes.py:16`; (c) `substrate/execution/voice/voice_engine.py` (631L Discord voice, consumed by services/discord_bot.py). The phase13_4 residual blocker "real microphone capture never proven" (docs/audits/convergence/phase13_4_standard_multi_runtime_true_jarvis_e2e_acceptance.md:266-272) was never resolved in any later doc.
- Desired state: one voice ingress contract with one session/state authority (C20 `voice_session_manager` is the natural owner); the cockpit WS server and Discord engine become transports feeding that contract; a real-device acceptance proof (microphone on an executor-roled node with an interactive session → transcription → intent intake) recorded as a proof artifact.
- Files to inspect: umh/voice_server.py; substrate/workstation/voice_ingress_runtime.py; substrate/workstation/voice_session_manager.py; substrate/execution/voice/voice_engine.py; transports/api/cockpit_voice_ingress_routes.py; cockpit/src/renderer/api/voice-ws.ts (client contract).
- Files likely modified: umh/voice_server.py (delegate session state); substrate/execution/voice/voice_engine.py (session delegation); substrate/workstation/voice_session_manager.py.
- Forbidden files/actions: deterministic-first — STT provider chain must keep the local faster-whisper fallback; browser/microphone verification runs on executor nodes only (browser-verification law), never the headless orchestrator; voice relay is a host process — Docker restarts don't reach it; CPU gate for any local whisper subprocess.
- Dependencies: WP-P0-013 (voice WS auth — land first so the acceptance proof runs against the final auth), WP-P1-017 (kernel intake)
- Risk class: HIGH (live voice path for Discord and cockpit)
- Approval required: yes.
- Acceptance criteria: one session store observed from both cockpit-WS and Discord ingress (trace shows shared session ids); real-microphone E2E proof artifact exists (audio in → transcript → kernel intent) captured on an executor node; C20 suites pass.
- Proof required: the real-device proof artifact (Class A evidence — real hardware, not synthetic); shared-session trace.
- Tests to add/run: tests/test_c20_*.py (after WP-P6-002 fixes their paths); new session-authority test.
- Rollback plan: stacks revert to independent session stores (git revert; sessions are ephemeral).
- Expected output: code change + proof artifact.
- Parallelizable: no
- Requires human approval: yes
- Phase: P2

### WP-P2-028: Build the recurring-schedule reconciliation primitive
- Closes: GAP-E1-010
- Current state: LyfeOS quests carry a full recurrence model (repeatFrequency/Interval/Days/EndDate, parentRitualId — data/repos/LYFEOS/shared/schema.ts:335-339) plus smartReminders (:1383-1404); UMH-side scheduling is host cron plus an explicitly unwired ritual scaffold (`substrate/execution/bridge/rituals.py:8-11` — "NOT wired into every interface yet"). No substrate recurring-job engine exists to reconcile desired schedules against actual executions.
- Desired state: a substrate recurring-schedule primitive (schedule object: rule, next-fire, owner, last-outcome) with desired-state reconciliation (missed-fire detection, catch-up policy) and an L4 sync mapping so LyfeOS quest recurrence rules materialize as platform schedule objects; rituals.py scaffold wired to it.
- Files to inspect: substrate/execution/bridge/rituals.py; substrate/execution/bridge/ritual_runner.py; data/repos/LYFEOS/shared/schema.ts:311-356,1383-1404 (source model); substrate/canonical_types.py (register ScheduleSpec); substrate/organism/autonomous_tick.py (tick integration point).
- Files likely modified: new substrate/execution/schedule/ module; substrate/execution/bridge/rituals.py; substrate/canonical_types.py.
- Forbidden files/actions: deterministic-first (scheduler is pure rules — no LLM in the firing path); CPU gate before any spawned work; cron wrapper conventions (cron-run + flock) for the host trigger; type coherence for new types.
- Dependencies: WP-P4-010 (LyfeOS sync needs the live poller) for the L4 mapping half; the primitive itself has none
- Risk class: LOW (new module) / MEDIUM where rituals.py is modified
- Approval required: no
- Acceptance criteria: schedule objects fire deterministically in unit tests (frozen clock); missed-fire reconciliation produces catch-up or explicit skip records; a LyfeOS quest recurrence rule round-trips to a ScheduleSpec and back losslessly (mapping test with fixture rows).
- Proof required: unit-test output; round-trip fixture diff (empty).
- Tests to add/run: new tests/test_schedule_primitive.py; tests/test_lyfeos_creatoros_integration.py still green.
- Rollback plan: new module removed; rituals.py revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-029: Build the media asset management primitive (object storage + metadata)
- Closes: GAP-E1-017
- Current state: no substrate asset abstraction exists. LyfeOS stores base64 file bodies in Postgres text columns (`data/repos/LYFEOS/shared/schema.ts:906` documents.fileData, `:1188` mediaItems.fileData); CreatorOS media are raw URL strings (`data/repos/creatoros/shared/schema.ts:34-36`). Every projection reinvents (or degrades) asset storage.
- Desired state: a platform media/asset service: content-addressed object storage (filesystem-backed initially, S3-compatible interface) + metadata records (owner, mime, size, checksum, source projection), exposed as a capability adapters and projections consume; migration of product base64 columns is a separate, later product-side decision (documented, not executed here).
- Files to inspect: substrate/execution/media/media_processor.py (existing offline media primitive — integrate, don't duplicate); substrate/canonical_types.py; transports/api/cockpit_workspace_routes.py (existing file handling precedent).
- Files likely modified: new substrate/execution/media/asset_store.py; substrate/canonical_types.py (AssetRecord); new route file or extension for upload/fetch.
- Forbidden files/actions: no base64 bodies in the platform DB (that is the defect being fixed); node-role discipline — large assets do not live on the VPS beyond cache (Beast is the heavy-storage node); credential injection for any cloud storage keys; centralized utility — one canonical asset module, no per-projection copies.
- Dependencies: none
- Risk class: LOW (new files)
- Approval required: no
- Acceptance criteria: store/fetch/delete round-trip with checksum verification; metadata queryable by owner+projection; chat upload path (WP-P0-012) optionally re-pointed at it as first consumer.
- Proof required: round-trip test output with checksum assertions.
- Tests to add/run: new tests/test_asset_store.py.
- Rollback plan: remove new module + route (no consumers forced onto it in this packet).
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P2

### WP-P2-030: Physical governance primitives — safety envelope, emergency stop, pre-actuation impact analysis
- Closes: GAP-E3-008, GAP-E3-013
- Current state: (a) the only kill switch is agent-recursion scoped (`substrate/organism/recursion_governance.py:166-212`); there is no substrate primitive for physical blast radius, actuator interlocks, safe-state fallback, e-stop, or rollback semantics for non-reversible physical actions — strategy docs mandate human approval for manufacturing actions (`docs/strategy/source_ingestion_map.md:208-210`) but that is doc policy, not an enforced gate. (b) There is no pre-actuation simulation/impact-analysis stage for physical or go-live operations (predicted effect, reversibility, cost, exposure) — GUI actuation has a post-hoc maturity model (`substrate/execution/actuation/actuator_maturity_v1.py`), physical actions have nothing pre-execution.
- Desired state: two L2 contracts, shipped together because they compose: (1) PhysicalSafetyEnvelope — per-device permitted operation set, non-reversibility flag feeding risk classification, e-stop channel that halts all physical adapters; (2) PreActuationImpactAnalysis — a required evaluation step (predicted effect, reversibility, cost, exposure) whose result feeds the governance risk class, reusable by broadcast go-live, manufacturing job release, robotics motion, and security mitigation. Both are prerequisites hard-wired into `PhysicalAdapterRegistry.execute()` (WP-P1-020).
- Files to inspect: substrate/execution/adapters/physical.py:29-145 (contract to extend); substrate/organism/recursion_governance.py:160-220 (kill-switch precedent); substrate/execution/actuation/actuator_maturity_v1.py (evidence-discipline precedent); substrate/canonical_types.py; docs/system/strategic_context_amendment_v2_physical_moat_report.md:181-191.
- Files likely modified: new substrate/execution/adapters/physical_safety.py; new substrate/execution/adapters/impact_analysis.py; substrate/execution/adapters/physical.py (enforce both in execute()); substrate/canonical_types.py.
- Forbidden files/actions: deterministic-first — the envelope check and impact classification are rule-based, never LLM-gated; type coherence; no physical execution allowed to skip the envelope even in degraded mode (fail closed); align risk enum with WP-P2-002's canonical taxonomy.
- Dependencies: WP-P1-020 (execute() governance hook), WP-P4-002 (generalized e-stop for actuation — share the stop-channel mechanism, don't duplicate), WP-P2-002 (risk taxonomy)
- Risk class: LOW (new modules; enforcement lands on a dormant path)
- Approval required: yes — defines the permanent trust posture for physical actuation.
- Acceptance criteria: an action outside a device's permitted set is denied; a non-reversible action without an impact-analysis record is denied; e-stop flips all registered adapters to refuse within one call cycle (unit-tested with a fake adapter); reversible+analyzed action passes.
- Proof required: unit-test matrix output (deny/deny/stop/allow).
- Tests to add/run: new tests/test_physical_safety_envelope.py.
- Rollback plan: remove enforcement hook + new modules (dormant path — no runtime impact).
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P2

---

## P3 — Ontology / metamodel separation (20 packets)

**Objective.** Enforce the four-layer separation: L1 external-reality entities modeled, L2 metamodel free of projection/instance content, L3 domain models owned by projections, L4 grounding/resolution contracts declared and versioned (entity resolution, writeback schema, domain vocabulary, state authority).

**Entry criteria.** P2 canonical types (WP-P2-001/002); the layer-contract extension (WP-P3-001) should land first within this phase.

**Exit criteria.** No upward imports (gates green with exemption lists burned down); no projection or instance literals in substrate; declared state authorities for reality/world models, outcomes, and sources of truth; versioned schema artifacts for every write path.

### WP-P3-001: Extend the layer contract to nodes/, umh/, cockpit/ and add missing dependency rules
- Closes: GAP-A-003, GAP-C3-011
- Current state: `nodes/` (56 runtime-node client files) is absent from the 4-layer contract yet is imported upward from substrate (`substrate/execution/agents/computer_use_agent.py:256,268,304,313`) and sideways from transports; no checker rule covers `nodes`. `umh/` (3 live WS servers proxied by nginx) and `cockpit/` (frontend) are undeclared. Separately, `check_cpu_gate.py` GATED_DIRS = substrate/adapters/transports/services (`scripts/check_cpu_gate.py:28-33`), exempting `nodes/` despite raw `subprocess.run/Popen` throughout (`nodes/windows/umh_node/adapters/hermes.py:138-333`, `adapters/container.py:53-120`, `adapters/camera.py:750`, `client.py:571`, `nodes/distribution/first_boot.py:101`) — contradicting the CPU Gate Law's "any future node" scope.
- Desired state: the layer contract (`.claude/rules/architecture-layers.md`, ARCHITECTURE.md) extended to place `nodes/` (data-plane runtime-node clients), `umh/` (transports), `cockpit/` (presentation); `check_dependency_direction.py` gains rules for these; substrate→nodes access moves behind `substrate/sockets/remote_exec_port.py`; `nodes/` is either added to CPU-gate enforcement (Windows-appropriate gate) or the law amends to document the executor-node exemption.
- Files to inspect: `.claude/rules/architecture-layers.md`; `ARCHITECTURE.md`; `substrate/execution/agents/computer_use_agent.py:256-313`; `scripts/check_dependency_direction.py:39-72`; `scripts/check_cpu_gate.py:28-40`; `substrate/sockets/remote_exec_port.py`.
- Files likely modified: `.claude/rules/architecture-layers.md`; `ARCHITECTURE.md`; `scripts/check_dependency_direction.py`; `scripts/check_cpu_gate.py`; `substrate/execution/agents/computer_use_agent.py` (route via port).
- Forbidden files/actions: substrate must not import nodes directly (use remote_exec_port); do not weaken CPU Gate Law without an explicit documented exemption.
- Dependencies: none
- Risk class: MEDIUM
- Approval required: yes — amends architecture contract + enforcement scope.
- Acceptance criteria: contract names nodes/umh/cockpit with dependency rules; substrate→nodes goes through the port (grep); CPU-gate scope decision recorded and enforced.
- Proof required: checker rule additions demonstrated on injected violations; grep showing no direct substrate→nodes import.
- Tests to add/run: run `check_dependency_direction.py --all` and `check_cpu_gate.py --all`.
- Rollback plan: revert; doc changes non-executable.
- Expected output: code change + documentation change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P3

### WP-P3-002: Remove the ghost saas/ layer from contract and enforcement; relocate EOS routes
- Closes: GAP-A-001, GAP-A-011, GAP-C1-012
- Current state: `.claude/rules/architecture-layers.md:6,29,35-38`, `scripts/check_dependency_direction.py:94,158-170` (LEGACY entry `saas/api/routes/analytics.ts`, saas/ globs, INFRA_IN_PROJECTION_DIRS), and `scripts/check_ungoverned_mutations.py:30-33` all regulate a `saas/` directory that does not exist (confirmed absent). Its declared responsibilities are scattered: EOS routes in `transports/api/cockpit_core_eos_routes.py` + `cockpit_entity_routes.py` (inside the layer the rule says they must not be in); EOS schema in `data/repos/entrepreneuros/shared/schema.ts`; EOS logic in `projections/eos/`. Separately the projection-leak gate flags `substrate/organism/candidate_supply_engine.py:546` and misses the live `EntrepreneurOSGateway = Gateway` alias (`gateway.py:1946`, imported by `services/discord_bot.py:91`). `check_ungoverned_mutations.py` also grandfathers two live services (`goal_api.py`, `higgsfield_webhook.py`).
- Desired state: the contract names the real owner of projection-specific routes/schema (`projections/eos/` or a restored `saas/`); stale `saas/` gate entries removed; EOS routes relocated out of `transports/`; the `EntrepreneurOSGateway` alias deleted with consumers migrated to `Gateway`; the projection-leak gate extended to catch alias assignments; `check_ungoverned_mutations.py` ROUTE_DIRS updated to reality and grandfathered list burned down.
- Files to inspect: `.claude/rules/architecture-layers.md:29`; `scripts/check_dependency_direction.py:94,158-170`; `scripts/check_ungoverned_mutations.py:29-33,72-75`; `transports/api/cockpit_core_eos_routes.py:33`; `transports/api/cockpit_entity_routes.py`; `substrate/control_plane/runtime/gateway.py:1946`; `services/discord_bot.py:91`; `substrate/organism/candidate_supply_engine.py:546`; `scripts/check_projection_leak.py`.
- Files likely modified: the two check scripts; `.claude/rules/architecture-layers.md`; `substrate/control_plane/runtime/gateway.py` (drop alias); `services/discord_bot.py` (use Gateway); `substrate/organism/candidate_supply_engine.py`; relocated EOS route files.
- Forbidden files/actions: no projection names in substrate (projection-boundary law); do not remove enforcement for real dirs; keep dependency direction when relocating routes.
- Dependencies: none
- Risk class: MEDIUM
- Approval required: yes — relocating EOS routes changes the deployed API surface layout.
- Acceptance criteria: `saas/` no longer referenced by any rule or checker; `check_projection_leak.py --all` passes (alias gone, candidate_supply fixed) and flags an injected alias assignment; EOS routes owned outside `transports/`; `check_ungoverned_mutations.py` ROUTE_DIRS matches reality.
- Proof required: projection-leak gate green + injected-alias failure; grep showing no `saas/` in rules/checkers; relocated-route import check.
- Tests to add/run: `check_projection_leak.py --all`, `check_dependency_direction.py --all`, `check_ungoverned_mutations.py --all`.
- Rollback plan: revert per-file.
- Expected output: code change + documentation change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P3

### WP-P3-003: Reality/world-model responsibility boundary document

- Closes: GAP-D1-006
- Current state: five overlapping world/reality-model homes with no declared per-layer responsibility boundary: substrate/reality_model/ (L1 observations+patterns), substrate/understanding/world_model/ (L1/L3 knowledge entries with its own canonical/instance duality), substrate/organism/world_model.py (L2 self-model), substrate/organism/reality_graph.py (L2/L4 operator-world composition), substrate/understanding/reality/ (L1 market signals). Only reality_graph.py (1-14) and organism/world_model.py (1-10) document their boundary; substrate/reality_model/canonical_reality_write.py:5-12 admits parallel write paths; vocabulary ("canonical", "instance", "reality", "world model") is reused with different semantics in each.
- Desired state: a written metamodel boundary doc naming one canonical home per layer (L1 observation store, L2 self-model, L4 composition), the deprecation/re-scope decision for understanding/world_model, and per-module docstring cross-references to the boundary doc.
- Files to inspect: the five module families' headers; D1 ledger F3 proposal
- Files likely modified: new docs/architecture/reality-model-boundaries.md (or ARCHITECTURE.md section), docstring cross-references in the five module homes
- Forbidden files/actions: documentation and docstrings only — zero behavior change; PLATFORM_SPEC.md is frozen (this is an architecture-notes doc, not a spec change).
- Dependencies: none (informs 019/035/036/042)
- Risk class: LOW
- Approval required: yes — the boundary assignment is an architecture decision the follow-on packets execute against.
- Acceptance criteria: doc names a single owner per layer and the disposition of understanding/world_model; each of the five module homes' docstrings cite the doc; review sign-off recorded.
- Proof required: the doc + docstring diff.
- Tests to add/run: none (documentation-only).
- Rollback plan: git revert.
- Expected output: documentation-only packet.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P3

### WP-P3-004: One projection concept — canonical projection ids, a single projection port, converged registration
- Closes: GAP-B4-007, GAP-B4-008, GAP-B4-009, GAP-D2-009, GAP-E1-004, GAP-E1-015
- Current state: "Projection" means four different things in L2: (a) forecast object — `Projection` registered at canonical_types.py:295, produced by `substrate/organism/projection_engine.py:346`; (b) product application (EOS/CreatorOS/LyfeOS) — ProjectionContract (`substrate/types.py:1363`, unregistered), sockets ProjectionPort + legacy in-memory dict (`substrate/sockets/projection_port.py:33-51,60,155`), projection_certification.ProjectionRegistry (`substrate/organism/projection_certification.py:104-129`), projection_integration_runtime (`substrate/organism/projection_integration_runtime.py:244`) — ≥4 independent registration mechanisms; (c) DomainProjection (`substrate/understanding/domains/contract.py:72-74`); (d) doc-source scope. Two of these share one data dir (`data/umh/projections/`, projection_engine.py:46-47) and one `proj-` id prefix. Two same-named port abstractions with unrelated contracts: `substrate/sockets/projection_port.py` (ProjectionRegistration/ProjectionPort, file-backed registry) vs `substrate/organism/projection_port.py` (OrganismStatePort — state-slice broadcast), both used by `substrate/organism/daemon.py:424-454`. Projection identity has ≥3 schemes: `data/umh/projection_registry.json` keys `umh|lyfeos|eos|cos`; the alias normalizer `_PROJECTION_ALIASES` (`substrate/organism/projection_integration_runtime.py:193-204`) canonicalizes `eos → entrepreneuros` and knows `creatoros` but NOT `cos`, so `_normalize_projection_id("cos")` falls through to a fourth identifier; integration manifests use `INTEGRATION_ID = "eos"|"creatoros"|"lyfeos"` (`projections/*/integration/manifest.py:18`). `ProjectionName` enum (`substrate/organism/projection_source_registry.py:42-46`) cannot represent EOS/CreatorOS/LyfeOS (values: UMH/Shared/Unknown), so the reconciliation engine (`substrate/organism/projection_reconciliation_engine.py:20-28`) cannot attribute sources to product projections.
- Desired state: the forecast layer renamed (e.g. ForecastEngine/Forecast, with alias); one projection record + one projection port owning both registration and state subscription (the organism state-broadcast module renamed, e.g. organism_state_port.py, with a compat shim); registration mechanisms converged; separate persistence namespaces and id prefixes; one canonical projection_id per product enforced at registration (alias map covers `cos` and every legacy key; registry file rewritten to canonical keys; registration rejects non-canonical ids); product projections representable via dynamic registration replacing the closed enum and attributable by the reconciliation engine.
- Files to inspect: substrate/organism/projection_engine.py; substrate/sockets/projection_port.py; substrate/organism/projection_port.py; substrate/organism/projection_certification.py:104-129; substrate/organism/projection_integration_runtime.py:190-260; substrate/organism/projection_source_registry.py:42-46; substrate/organism/projection_reconciliation_engine.py:20-28; substrate/organism/daemon.py:420-460; data/umh/projection_registry.json; projections/eos/integration/manifest.py:18 (+ creatoros/lyfeos manifests); substrate/types.py:1363; consumers of both ports (graph dependents).
- Files likely modified: projection_engine.py (rename); both projection_port modules (merge + shim); projection_certification.py; projection_integration_runtime.py; projection_source_registry.py; substrate/organism/daemon.py; substrate/types.py; substrate/canonical_types.py; data/umh/projection_registry.json; data-dir namespace split.
- Forbidden files/actions: projection-boundary law — the record stays projection-agnostic (names arrive via runtime registration, never as substrate literals; do not extend the grandfathered alias map beyond canonicalization — WP-P3-013 removes the hardcoded name tables); do not delete existing data/umh/projections/ artifacts (namespace split is additive with a migration script); type coherence; keep a compat shim for the renamed module one release.
- Dependencies: WP-P2-001
- Risk class: HIGH (projection registration is the L3 attachment mechanism)
- Approval required: yes — architecture decision on the single projection-port contract.
- Acceptance criteria: "Projection" resolves to exactly one product-projection concept in L2; forecast renamed with alias; one port; `_normalize_projection_id("cos") == "creatoros"`; the registry JSON contains only canonical keys; daemon boot registers all projections under canonical ids (log evidence); EOS registers through the unified port and is attributable by the reconciliation engine; the id-prefix collision is gone.
- Proof required: registration round-trip test for a fake projection; unit-test output for the alias matrix incl. `cos`; daemon startup log; grep inventory of the four former meanings.
- Tests to add/run: tests/test_projection_port_unified.py; alias-matrix extension of the projection-runtime tests; run tests/test_projection_certification.py, tests/test_gate10_projection_consumption.py; import check `python3 -c "import substrate.organism.daemon"`.
- Rollback plan: aliases + staged port merge; revert the registry file; shims keep old imports working; git revert per stage.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P3
- Merged from: WP-DRAFT-PART2-033 + WP-DRAFT-PART3-010 (projection homonym/port/identity fragmentation reported by the metamodel and projection workstreams).

### WP-P3-005: Move L3 domain entities out of substrate/types.py

- Closes: GAP-B4-010, GAP-D2-006
- Current state: EOS domain entities (Company substrate/types.py:1136, Department :1158, Portfolio :1185, plus Role/User/Workflow/Dashboard across types.py:1108-1254) live in the L2 platform type module; `projections/eos/entities.py:9-24` imports them from substrate.types — the projection boundary is inverted (platform carries product domain).
- Desired state: domain entities owned by projections/eos/; substrate keeps only projection-agnostic metamodel objects (tenant, operator, capability, work packet, trace); ProjectionContract.entity_types made structural so projections declare their own entity sets.
- Files to inspect: substrate/types.py:1108-1254, projections/eos/entities.py, all substrate-internal consumers of the moved types (graph dependents — any hit means a substrate module depends on L3 shapes and needs an abstraction first)
- Files likely modified: projections/eos/entities.py (real definitions), substrate/types.py (remove or deprecation re-export), substrate/canonical_types.py, any substrate consumers (retarget to metamodel abstractions)
- Forbidden files/actions: dependency direction — substrate/ must not import projections/ (the move must not create a reverse import; use re-export shims pointing downward only during deprecation, then delete); projection-boundary and instance-context gates must pass with no new exemptions.
- Dependencies: WP-P3-004 (structural entity_types), WP-P2-014 (Role disambiguation)
- Risk class: HIGH (type moves across the layer boundary with unknown substrate consumers until inventoried)
- Approval required: yes — changes the published substrate type surface.
- Acceptance criteria: zero L3 entity classes defined in substrate/types.py; projections/eos/entities.py self-owned; check_dependency_direction.py + check_projection_leak.py pass; consumer inventory shows every former import site retargeted.
- Proof required: gate outputs; consumer inventory; import smoke.
- Tests to add/run: run tests/test_eos_projection.py, tests/test_p1_phase9_architecture.py.
- Rollback plan: deprecation re-export window; git revert.
- Expected output: clean L2/L3 type ownership.
- Parallelizable: no
- Requires human approval: yes
- Phase: P3

### WP-P3-006: L1 external-world entity model (people/orgs/customers)

- Closes: GAP-B4-011
- Current state: no L1 model for people/orgs/customers exists: RealityEntityType covers only dev/infra artifacts (16 types, none human/org/commercial — substrate/organism/reality_graph.py:35-51); `world_model.py` is a misnamed self-model — its EntityCategory enumerates UMH-internal subsystems (substrate/organism/world_model.py:39-51,145).
- Desired state: L1 external-entity model with projection-extensible kinds (person, organization, account, asset), observation grounding (source_ref/evidence), and external-ID mapping; reality_graph extended (or a sibling module added) to carry them.
- Files to inspect: reality_graph.py, world_model.py, substrate/reality_model/instance.py, substrate/reality_model/canonical.py
- Files likely modified: new substrate/reality_model/external_entities.py (or reality_graph extension), substrate/canonical_types.py
- Forbidden files/actions: no projection or instance literals (kinds are extensible via registration, not hardcoded CRM semantics); type-coherence; no PII persistence decisions in this packet beyond the type shape (data handling policy is a separate concern).
- Dependencies: WP-P2-007 (EntityState), WP-P2-001
- Risk class: LOW (new model files) 
- Approval required: no
- Acceptance criteria: PERSON/ORGANIZATION entity kinds representable with evidence links and external IDs; registered; a fixture person observed from two sources produces one entity with two external IDs.
- Proof required: pytest fixture output.
- Tests to add/run: new tests/test_external_world_entities.py.
- Rollback plan: additive; git revert.
- Expected output: L1 entity vocabulary for the external operational reality model.
- Parallelizable: yes
- Requires human approval: no
- Phase: P3

### WP-P3-007: Unify StateAuthority with source-canonicality taxonomies

- Closes: GAP-B4-014
- Current state: StateAuthority is domain-coarse, static, and disconnected: a 10-domain registry with string-typed fields ignoring its own enums, no conflict resolution or delegation (substrate/organism/state_authority_graph.py:21-72; infra/state_authority_registry.json); SourceCanonicality (substrate/organism/projection_source_registry.py:48) and authority_tier (substrate/understanding/domains/contract.py:57) are parallel unlinked truth taxonomies.
- Desired state: per-entity state authority with typed levels, a conflict-resolution policy, delegation, unified with source canonicality — one authority taxonomy consumed by reconcilers (WP-P2-007) and entity resolution (WP-P3-011).
- Files to inspect: state_authority_graph.py, infra/state_authority_registry.json (verify the loader actually reads it — flagged UNVERIFIED in ledger B4), projection_source_registry.py, contract.py:57
- Files likely modified: state_authority_graph.py, projection_source_registry.py, substrate/canonical_types.py, infra/state_authority_registry.json (schema of entries)
- Forbidden files/actions: authority decisions are deterministic tables — no LLM; registry JSON edits must keep existing consumers parsing (additive fields).
- Dependencies: WP-P2-001
- Risk class: MEDIUM
- Approval required: yes — declares who wins conflicts between sources of truth.
- Acceptance criteria: one authority taxonomy registered; a conflict fixture (two sources asserting different values) resolves per policy with a journaled decision; SourceCanonicality/authority_tier map into it.
- Proof required: conflict-fixture pytest; taxonomy mapping table in the diff.
- Tests to add/run: new tests/test_state_authority_unified.py.
- Rollback plan: additive; git revert.
- Expected output: single state-authority model.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P3

### WP-P3-008: Route canonical-reality write side-doors through the validated write path and invoke policy at the choke point
- Closes: GAP-C1-007, GAP-C1-009
- Current state: direct `InstanceRealityModel.record` calls bypass `CanonicalRealityWritePath` validation + trust gate — `substrate/organism/work_packet_engine.py:674` (also hardcodes `user_id="system"`/`org_id="system"`), `substrate/organism/deploy_verification_worker.py:527`, `substrate/organism/projection_certification.py:295`; `transports/api/cockpit_reality_model_routes.py:377` is governed at HTTP but skips the reality-write validation. `CanonicalRealityWritePath.apply_mutation` explicitly "Does NOT call governance (caller's responsibility)" (`canonical_reality_write.py:44-45`), and its trust gate only fires when `metadata.work_id` is present (`:107-109`) — the policy engine is optional at the single reality-write choke point.
- Desired state: all non-execution observation writes route through `CanonicalRealityWritePath.apply_mutation`; that choke point invokes governance (or asserts a governance context is attached to the mutation); the hardcoded "system" identity is replaced with runtime-loaded instance context.
- Files to inspect: `substrate/reality_model/canonical_reality_write.py:44-45,60,102-124`; `substrate/organism/work_packet_engine.py:640-680`; `substrate/organism/deploy_verification_worker.py:527`; `substrate/organism/projection_certification.py:295`; `transports/api/cockpit_reality_model_routes.py:377`.
- Files likely modified: the three direct-record call sites; `substrate/reality_model/canonical_reality_write.py` (invoke policy); `transports/api/cockpit_reality_model_routes.py`.
- Forbidden files/actions: no hardcoded identity in substrate (instance-context law — load from BIS/env); deterministic validation before any LLM enhancement.
- Dependencies: WP-P1-001
- Risk class: MEDIUM (L4 grounding / source-of-truth writes)
- Approval required: no
- Acceptance criteria: no direct `InstanceRealityModel.record` outside the write path (grep); the choke point rejects a write lacking a governance context; the "system" identity comes from runtime context.
- Proof required: grep-clean direct-record check; rejection log for a context-less reality write.
- Tests to add/run: `tests/test_reality_write_governed.py`.
- Rollback plan: revert per-file.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P3

### WP-P3-009: Declare and version the umh_status/umh_outcomes writeback schema; one outcome-ledger authority
- Closes: GAP-D2-002, GAP-E1-002, GAP-E1-016
- Current state: all three projection `tables.py` modules write `umh_status` columns onto product source rows and insert into a product-side `umh_outcomes` table (`projections/eos/integration/tables.py:487-583`; `projections/creatoros/integration/tables.py:346-439`; `projections/lyfeos/integration/tables.py:408-504`), but NONE of the three product Drizzle schemas declare those columns/tables (`grep umh_status data/repos/*/shared/schema.ts` → zero hits) and zero DDL/migration files exist repo-wide — migrations applied out-of-band, live-DB existence UNVERIFIED; the write path's schema has no source of truth, and the reconciliation engine itself already flags the drift (`substrate/organism/projection_reconciliation_engine.py:224-244`). Separately, the platform DB defines its OWN `umh_outcomes` (`transports/api/http/db/schema.ts:182`) — two definitions with different owners and no declared relationship; the source of truth for outcome records is undefined.
- Desired state: one declared design with versioned artifacts: the platform `umh_outcomes` is the outcome ledger of record (source-system row references, projection id, capability, correlation id); product-side writeback is either (a) retired in favor of ledger reads, or (b) kept as a declared replication with versioned migration artifacts per projection DB and the columns/table added to each vendored schema.ts so schema files match live DDL; a startup provisioning check verifies (never creates) expected columns/tables and fails loudly; a state-authority record names the ledger owner.
- Files to inspect: projections/eos/integration/tables.py:480-590; projections/creatoros/integration/tables.py; projections/lyfeos/integration/tables.py; data/repos/entrepreneuros/shared/schema.ts; data/repos/creatoros/shared/schema.ts; data/repos/LYFEOS/shared/schema.ts; transports/api/http/db/schema.ts:175-195; substrate/organism/projection_reconciliation_engine.py:220-250; live-DB introspection (read-only) to establish ground truth first.
- Files likely modified: new migration files per projection DB (location per each app repo's convention, vendored here); the three product schema.ts files (declare writeback) or the three tables.py (re-point writes at the platform ledger); tables.py (startup verification); transports/api/http/db/schema.ts if ledger columns are extended; state-authority record.
- Forbidden files/actions: CRITICAL schema class — introspect and record row counts before authoring anything; never auto-create tables from the poller path; never run migrations without counting first; product repos on the VPS carry shared/schema.ts ONLY (node-role discipline) — actual product-DB DDL executes from the product repos on Beast, this packet aligns declarations and platform code; credentials via env only.
- Dependencies: none (coordination: WP-P4-004 makes the writeback path exercisable end-to-end)
- Risk class: CRITICAL (schema declarations + potential data-path move for production-adjacent databases)
- Approval required: yes — schema-level and source-of-truth decision.
- Acceptance criteria: every column/table written by outcome receivers appears in a versioned migration + vendored schema (or the writes are removed under design a); exactly one umh_outcomes authority named; the startup check passes against the live DB and fails against a scratch DB missing the schema; the reconciliation engine no longer reports this drift class; an outcome write round-trip test passes against the chosen store.
- Proof required: live-DB introspection transcript (before); migration files; startup-check output both ways; reconciliation-engine report before/after; row-count parity for any moved data.
- Tests to add/run: tests/test_writeback_schema_declared.py (static: every written column exists in schema source); outcome insert+read tests per projection handler; tests/test_lyfeos_creatoros_integration.py; tests/test_eos_projection.py.
- Rollback plan: migrations are declarative records where the DB already has the schema — rollback is file deletion; for genuinely new DDL, down-migrations authored first; re-pointed writes flag-guarded.
- Expected output: schema migration artifacts + code change (startup verification; schema-only under design b).
- Parallelizable: yes
- Requires human approval: yes
- Phase: P3
- Merged from: WP-DRAFT-PART2-045 + WP-DRAFT-PART3-020 (undeclared writeback schema reported by the grounding and projection workstreams).

### WP-P3-010: Automated correspondence check between integration bindings and vendored schemas

- Closes: GAP-D2-003, GAP-D2-016
- Current state: two hand-maintained sources of L3 domain truth with no drift check: projections/*/integration/tables.py dataclasses+SQL vs data/repos/*/shared/schema.ts (Drizzle); coherence is manual and already broken — the EOS tables.py docstring claims 7 tables incl. agents/agent_metrics (lines 6-13) while code wires 5 (VALID_SOURCE_TABLES, lines 497-499), with no fetch helpers for the other 2.
- Desired state: a generated binding or an automated correspondence check (CI-runnable script parsing pgTable definitions and comparing to tables.py column references); docstring matches VALID_SOURCE_TABLES; drift fails a gate.
- Files to inspect: the three tables.py, the three schema.ts, scripts/ conventions
- Files likely modified: new scripts/check_schema_correspondence.py, projections/eos/integration/tables.py (docstring), test
- Forbidden files/actions: check is read-only over both sources; no runtime DB access required; do not "fix" drift by widening tables.py in this packet (report only).
- Dependencies: WP-P3-009
- Risk class: LOW (new tooling + docstring fix)
- Approval required: no
- Acceptance criteria: script exits non-zero on a seeded drift fixture; current real drift inventory produced; docstring corrected.
- Proof required: script output on real tree + fixture.
- Tests to add/run: new tests/test_schema_correspondence_tool.py.
- Rollback plan: git revert.
- Expected output: tooling packet + one docstring fix.
- Parallelizable: yes
- Requires human approval: no
- Phase: P3

### WP-P3-011: L4 entity-resolution contract and registry (operator identity + external persons/orgs)
- Closes: GAP-B4-012, GAP-D1-013, GAP-D2-005, GAP-D2-014, GAP-E1-003, GAP-E1-019
- Current state: entity resolution is three unlinked mechanisms with no shared contract: ContextResolutionEngine (NL→project, `substrate/organism/context_resolution.py:29-40`; `resolve_entity_reference` at :194 is name-lookup only), IdentityResolver (signal→operator, `substrate/control_plane/identity/__init__.py:15-36`), EntityLinkStore (raw insert-only table writes, `substrate/state/stores/entity_link_store.py:1-39`, single consumer, no read/query API, and no `entity_links` DDL anywhere in the repo). RealityGraph builds entity ids by source-prefixed convention (`dev-`, `ws-`, `repo-`, `proj-`, `cap-`; `substrate/organism/reality_graph.py:296-741`) with last-observed-wins merging only on identical ids (:249-257); nothing resolves the same external object across id schemes or links RealityEntity ↔ InstanceObservation ↔ WorldModelEntry (`substrate/understanding/domains/contract.py:38-56` back-references decompositions only). Operator identity is four parallel user stores with no bridge — platform `users` (uuid/email, `transports/api/http/db/schema.ts:75`), EOS `users` (text id/Firebase, `data/repos/entrepreneuros/shared/schema.ts:6-33`), CreatorOS `users` (serial int, `data/repos/creatoros/shared/schema.ts:7-18`), LyfeOS `users` (own 2FA/Stripe fields, `data/repos/LYFEOS/shared/schema.ts:7-41`), plus Clerk referenced in `data/umh/projection_registry.json`. The same defect for external persons: three unlinked contact tables model the same people — EOS crm_contacts (:237-251), CreatorOS contacts (`data/repos/creatoros/shared/schema.ts:235-249`), LyfeOS contacts with trustLevel (`data/repos/LYFEOS/shared/schema.ts:402-434`) — no resolver maps projection rows to canonical entities.
- Desired state: a declared L4 entity-resolution contract (merge/split, confidence scoring, external-ID resolution) composing the three mechanisms; an identity/entity-resolution registry in the platform DB — entity table (kind: operator|person|org) + per-source mapping rows (source system, source id, confidence, resolution method) — with `entity_links` DDL under version control and a read/traversal API (or consolidation into RealityGraph edges); deterministic matchers first (exact email/phone), optional AI-assisted matching second; `resolve_entity_reference` extended to consult it; platform users + Clerk id declared the operator state authority with product user rows as mapped sources; projection contact rows resolvable to L1 person/org entities with per-attribute state-authority rules; merge/split operations journaled.
- Files to inspect: substrate/organism/context_resolution.py:29-240; substrate/control_plane/identity/__init__.py:15-36; substrate/state/stores/entity_link_store.py; substrate/organism/reality_graph.py:249-741; transports/api/http/db/schema.ts:75-141; the three product schema.ts user/contact sections; data/umh/projection_registry.json.
- Files likely modified: new substrate L4 resolution contract module (substrate/organism/entity_resolution.py or an extension of context_resolution.py); entity_link_store.py (read API); migration file(s) for entity_links / entity-map tables in the platform DB (transports/api/http/db/schema.ts); resolver adapters per projection under projections/*/integration/; substrate/canonical_types.py (EntityRecord/EntityMapping).
- Forbidden files/actions: DDL/migration = CRITICAL class — check row counts before any change to an existing live table; substrate/ must not import projections/ (projection resolvers register via port); deterministic-first — no LLM-only matching (rules/thresholds are tables; LLM assist optional with deterministic fallback); no founder-specific identity literals in substrate (instance-context law); credential-injection law for any DB access; type coherence.
- Dependencies: WP-P3-006 (L1 external entities), WP-P3-007 (authority rules), WP-P3-009 (migration discipline)
- Risk class: CRITICAL (new platform schema; identity is the tenancy root)
- Approval required: yes — schema migration + identity-merge semantics.
- Acceptance criteria: entity_links/entity-map tables have versioned DDL and a query API; an operator resolves to one entity id from Clerk id, platform uuid, and each product user row (fixture test); a person present in two projections' contact tables resolves to one canonical entity with a confidence score and both source refs; unresolved rows remain unlinked (no false merges in the deterministic tier — precision test); merge/split operations are journaled.
- Proof required: migration artifact applied with row counts; resolution fixture matrix output; journal records for one merge and one split.
- Tests to add/run: tests/test_entity_resolution_contract.py; tests/test_entity_resolution_registry.py.
- Rollback plan: mapping tables are additive and side-effect-free — down-migration authored first; resolver behind a flag; no source rows modified; git revert.
- Expected output: code change + schema migration.
- Parallelizable: no
- Requires human approval: yes
- Phase: P3
- Merged from: WP-DRAFT-PART2-036 + WP-DRAFT-PART3-021 (entity/identity resolution reported by the grounding and projection workstreams).

### WP-P3-012: Own projection domain schemas in the code layer; trim vendored repos to schema-only
- Closes: GAP-A-015, GAP-D2-015
- Current state: EOS/CreatorOS/LYFEOS domain schemas live at `data/repos/*/shared/schema.ts` in the data plane with no code-layer owner; vendored-repo hygiene diverges from the node-role policy (VPS: "Trinity app repos: shared/schema.ts ONLY") — `data/repos/entrepreneuros/` carries a full application payload (client/, server/, package-lock.json); `data/repos/creatoros/shared/` lacks the models/ dir present in the other two (LYFEOS and entrepreneuros have shared/models/chat.ts).
- Desired state: projection domain schemas registered under `projections/<name>/` or a schema registry (L3/L4 ownership) with a declared code-layer owner per schema; excess repo payload removed per node-role discipline; the shared/models/chat.ts status documented (kept intentionally or removed everywhere).
- Files to inspect: data/repos/entrepreneuros/ listing; data/repos/*/shared/schema.ts; projections/eos/entities.py; any repo code importing from the vendored client/server dirs (must be zero before deletion); the node-role rule in CLAUDE.md.
- Files likely modified: new schema registry / projections/<name>/ schema references; deletions under data/repos/entrepreneuros/{client,server}; a hygiene note in the data/ README or docs.
- Forbidden files/actions: this is a data-plane move — verify zero importers before deletion (grep + graph); do not delete schema.ts without registering its L3 owner; deletions only in the vendored copies — never in the source app repos (Beast holds full mirrors per node-role discipline).
- Dependencies: WP-P3-002 (contract names the projection-route/schema owner); WP-P3-010 (correspondence tool confirms schema.ts is all that is consumed)
- Risk class: MEDIUM (data-plane move; confirm no live consumers)
- Approval required: yes — removing repo payloads is a data move.
- Acceptance criteria: each projection schema has a declared code-layer owner; `ls data/repos/entrepreneuros` shows no client/ or server/; importer grep = 0 before and after; the correspondence tool still passes; no runtime import references removed files.
- Proof required: pre-deletion importer grep transcript; post-deletion tree listing; ownership record per projection schema.
- Tests to add/run: import/consumer grep for removed paths; projection integration import-smoke; run the correspondence tool.
- Rollback plan: restore payload from git history.
- Expected output: code change (+ documentation ownership record). Schema-relocation packet — no schema-column changes, data-plane file move only.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P3
- Merged from: WP-DRAFT-PART1-026 + WP-DRAFT-PART2-048 (the same vendored-payload trim reported by the architecture and grounding workstreams).

### WP-P3-013: Invert substrate→projections imports in product_connections via runtime manifest registration
- Closes: GAP-D2-004, GAP-E1-012
- Current state: `substrate/integrations/product_connections.py:26-29,65,96,127` imports the three projection manifests (`projections.eos|creatoros|lyfeos.integration.manifest`) and hardcodes a `Product` enum with EOS/CREATOROS/LYFEOS in substrate — an upward import and L3-names-in-L2 layer inversion violating architecture-layers.md, projection-boundary.md, and PLATFORM_SPEC.md §14 (substrate never references projections by name); `substrate/organism/projection_integration_runtime.py:193-240` additionally hardcodes projection name/path tables (`_PROJECTION_ALIASES`, `_KNOWN_PROJECTIONS`).
- Desired state: manifest discovery inverted — projections (or the transports-layer app boot) register their manifests into the substrate projection registry (`substrate/sockets/projection_port.py`) at startup; substrate consumes registrations only; `product_connections.py` reads from the registry (enum → dynamic registry); the hardcoded name/path tables are deleted.
- Files to inspect: substrate/integrations/product_connections.py; substrate/organism/projection_integration_runtime.py:190-260; substrate/sockets/projection_port.py; projections/*/integration manifests; transports/api/app.py:140-210 (registration-site precedent); scripts/check_projection_leak.py (enforcement hook).
- Files likely modified: substrate/integrations/product_connections.py; substrate/organism/projection_integration_runtime.py; transports/api/app.py (registration calls); substrate/sockets/projection_port.py (registration payload carries manifest metadata); projection manifests (register).
- Forbidden files/actions: dependency direction — the fix must not move the upward import elsewhere in substrate; projection names may appear only in projections/ and transports-layer registration calls; check_dependency_direction.py and check_projection_leak.py must pass with no new exemptions; status-probe behavior preserved for existing consumers; no new types without a canonical_types check.
- Dependencies: WP-P3-004 (canonical ids + single port); sequence before WP-P4-004 (shares the registration site)
- Risk class: MEDIUM (modifying substrate module import structure)
- Approval required: no
- Acceptance criteria: `grep -rn "from projections" substrate/` returns zero hits; scripts/check_projection_leak.py passes repo-wide; product connection status still reports all three products (registry-driven); connection-status output before/after parity.
- Proof required: grep output; gate output; status-probe response diff.
- Tests to add/run: existing product_connections tests; a new registry-driven discovery test; run tests/test_p1_phase9_architecture.py; pre-commit gate run.
- Rollback plan: revert the touched files.
- Expected output: code change.
- Parallelizable: no (shares files with WP-P3-004 and WP-P4-004)
- Requires human approval: no
- Phase: P3
- Merged from: WP-DRAFT-PART2-044 + WP-DRAFT-PART3-011 (the same layer inversion reported by the grounding and projection workstreams).

### WP-P3-014: Domain vocabulary cross-reference and DomainBridge registration

- Closes: GAP-D1-010, GAP-B4-013
- Current state: "Domain" is four unrelated concepts with no shared registry or grounding: (a) free-text `domain: str` on CanonicalPattern/InstanceObservation (substrate/reality_model/canonical.py:41, instance.py:33) — unvalidated, drives reality_intelligence summaries; (b) governance domains (substrate/organism/domain_registry.py:33); (c) bridge domains (substrate/understanding/domains/registry.py); (d) StateDomain enum (substrate/organism/state_authority_graph.py:21). An observation tagged `domain="sales"` has no defined relation to the `sales` governance domain or `business` bridge domain. The DomainBridge protocol (substrate/understanding/domains/contract.py:18) and its registry are unregistered in canonical_types.py; rival substrate/organism/domain_registry.py is dormant (dependents: tests/test_empire_engine.py:46 only).
- Desired state: a single domain vocabulary or explicit per-context namespaces with an L4 cross-reference registry; observation `domain` validated against it; DomainBridge registered as canonical; DomainRegistry classified (promote into work-packet routing or archive per dormant protocol).
- Files to inspect: the four domain sites + contract.py + understanding/domains/registry.py
- Files likely modified: new L4 domain cross-reference module, canonical.py/instance.py (validation hook), substrate/canonical_types.py, domain_registry.py disposition
- Forbidden files/actions: dormant-classification before archiving DomainRegistry; validation must not reject existing stored observations (warn-then-enforce rollout); no projection content added to substrate (vocabulary mechanism only).
- Dependencies: WP-P2-004 (bridge types canonical), WP-P3-015 (bridge content relocation defines what registers)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: cross-reference resolves a domain tag to its governance/bridge/state counterparts (or declares no-mapping); observation writes validate; DomainBridge in registry; DomainRegistry disposition documented.
- Proof required: pytest; sample cross-reference lookups.
- Tests to add/run: new tests/test_domain_crossref.py; run tests/test_empire_engine.py.
- Rollback plan: validation flag off; git revert.
- Expected output: grounded domain vocabulary.
- Parallelizable: yes
- Requires human approval: no
- Phase: P3

### WP-P3-015: Relocate projection domain-bridge content and the EOS primitive library out of substrate

- Closes: GAP-D1-002, GAP-D1-003, GAP-D2-012
- Current state: substrate/understanding/ontology/primitives.py (923L) contains an EOS business advice library — PRIMITIVE_LIBRARY (hire_salesperson, paid_advertising, pricing_psychology, referral_flywheel, …; lines 82-676) and STAGE_PRIMITIVES (bootstrapped 6-stage doctrine, "$10K/month", "founder closes first"; lines 681-778) — masquerading as ontology primitives, colliding by name with substrate/ontology/primitives.py (the actual L1 vocabulary) and reading BIS venture stage at lines 792-806. substrate/understanding/domains/{business.py, creator.py (515L), life.py (568L)} hardcode projection-specific keyword maps (docstrings self-declare "CreatorOS creator domain primitives", creator.py:4; "LyfeOS life domain primitives", life.py:4-5); the projection-leak checker exempts them (scripts/check_projection_leak.py:81-82) instead of the content being relocated; substrate/execution/understanding_bridge.py:159-161 imports all three unconditionally, so every ingestion pass runs all projections' bridges regardless of tenant.
- Desired state: bridge contract + registry stay in substrate (contract.py, registry.py are correct L4); the three bridge content modules and the business primitive/stage library move to projections/ (or data-driven config) and register at runtime via the BridgeRegistry plug-in path (understanding/domains/registry.py:8-27 already supports registration); checker exemptions deleted; understanding_bridge loads bridges from the registry, per-tenant.
- Files to inspect: the five content modules, understanding_bridge.py, scripts/check_projection_leak.py, substrate/understanding/domains/registry.py
- Files likely modified: new projections/eos|creatoros|lyfeos bridge/content modules, deletion/shimming of the three substrate content modules + primitives library, understanding_bridge.py, scripts/check_projection_leak.py (remove exemptions)
- Forbidden files/actions: projection-boundary law is the point of this packet — zero product identifiers remain in substrate content modules; dependency direction — substrate never imports projections (registration flows upward via port/registry at runtime); keep the KnowledgePrimitive container type in substrate.
- Dependencies: WP-P2-004 (canonical bridge types), WP-P3-004 (registration port)
- Risk class: HIGH (relocation of live ingestion-path content across the layer boundary)
- Approval required: yes — changes what knowledge every ingestion pass applies per tenant.
- Acceptance criteria: check_projection_leak.py passes with exemption lines 81-82 removed; substrate/understanding/domains contains contract/registry only; ingestion with only EOS registered applies only the business bridge (tested); primitive library content byte-identical post-move.
- Proof required: gate output; content checksum comparison; ingestion test trace.
- Tests to add/run: new tests/test_bridge_runtime_registration.py; run tests/test_ontology_enacted.py, tests/test_grounding_firewall.py.
- Rollback plan: shims re-exporting from new location during transition; git revert.
- Expected output: substrate carries L4 mechanism only; L3 content lives in projections/.
- Parallelizable: no
- Requires human approval: yes
- Phase: P3

### WP-P3-016: Purge instance/projection doctrine from canonical seeds, prompts, and governance domains

- Closes: GAP-D1-004, GAP-D1-007, GAP-D1-009
- Current state: three instance-context leaks in substrate: (1) `CanonicalWorldModel` ("shared truths across all orgs", substrate/understanding/world_model/world_model.py:4) `_ensure_seeded` writes EOS stage-progression/founder-bottleneck/outreach-vs-content doctrine at confidence 0.90-0.95 with source="seeded" (lines 143-196), bypassing the promotion mechanic; `__main__` hardcodes org_id="lyfe_institute" (line 248); this layer is injected into every prompt via get_context_for_prompt (218-244) and consumed by substrate/control_plane/context/context_builder.py:511-515. (2) substrate/organism/domain_registry.py claims "Instance-agnostic" (line 7) but registers music/clothing/real_estate/personal-LifeOS — one founder's venture portfolio — as substrate constants (lines 201-249). (3) substrate/understanding/reality/reality_engine.py hardcodes "LYFEOS, gamification, AI, execution framework" venture advantages into a competitor-analysis prompt (line 457) and lyfe_institute ids in usage docs (21-23); reality_context.py derives a founder-specific night_owl pattern (33-41).
- Desired state: canonical world-model layer seeded only with projection-agnostic entries (or empty) — doctrine enters via instance layer + governed memory promotion or from projections/ seed data; DomainDefinition/DomainRegistry mechanism stays, domain rows load from BIS/projection registration; venture advantages, tenant ids, and operator patterns come from BIS/venture knowledge at runtime with parameterized prompts.
- Files to inspect: world_model.py (understanding), context_builder.py:511-515, domain_registry.py, reality_engine.py, reality_context.py
- Files likely modified: those five + BIS/config seed locations + projections/ seed data files
- Forbidden files/actions: instance-context law (check_instance_leak.py must pass without new exemptions); memory-promotion governance is mandatory — no re-seeding path that skips it; deterministic-first for prompt parameter assembly.
- Dependencies: WP-P3-015 (same relocation pattern; shared seed-data layout)
- Risk class: MEDIUM (content relocation; prompt behavior changes for one tenant)
- Approval required: yes — removes doctrine from every-prompt context; operator should confirm the instance-layer replacement before cutover.
- Acceptance criteria: grep for lyfe_institute/LYFEOS/music/clothing/real_estate in substrate/ returns zero content hits; canonical layer seed list is projection-agnostic; prompts parameterized (fixture with a different BIS profile yields different advantages text); check_instance_leak.py passes.
- Proof required: gate output; grep inventory; prompt-diff fixture output.
- Tests to add/run: new tests/test_instance_context_purge.py.
- Rollback plan: seed data preserved in projections/ files; git revert restores literals.
- Expected output: instance-clean substrate seeds/prompts/domains.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P3

### WP-P3-017: Retire the laws/primitives/domains re-export shim chain

- Closes: GAP-D1-008
- Current state: two-deep re-export shims with no deprecation path: substrate/foundation/laws.py:8-18 re-exports substrate/ontology/laws.py including private `_ALL_LAWS` (line 18); substrate/ontology/primitives.py:9-16 and relationships.py re-export substrate/types.py; substrate/ontology/domains/__init__.py:7-17 re-exports understanding/domains but omits the business bridge (exports DomainBridge/Life/Creator only). Consumers split across all aliases (understanding_bridge.py:25 uses ontology.laws; tests use both).
- Desired state: one import path per symbol; shims carry deprecation markers and a removal milestone; the business-bridge asymmetry resolved (or the shim package removed entirely once consumers are migrated).
- Files to inspect: foundation/laws.py, ontology/{laws,primitives,relationships}.py, ontology/domains/__init__.py, all alias consumers (grep)
- Files likely modified: shim modules (deprecation warnings), consumer imports, eventual deletion commit
- Forbidden files/actions: no private-symbol re-export survives; coordinate with WP-P3-015 (domains content moves first).
- Dependencies: WP-P3-015, WP-P2-004
- Risk class: MEDIUM (import-path migration)
- Approval required: no
- Acceptance criteria: every shim emits DeprecationWarning; consumer grep shows one canonical path per symbol; import smoke green.
- Proof required: grep inventory; warning capture in tests.
- Tests to add/run: extend import-smoke suite.
- Rollback plan: git revert.
- Expected output: single import topology for ontology symbols.
- Parallelizable: yes
- Requires human approval: no
- Phase: P3

### WP-P3-018: Reality/world-model module hygiene (paths, stale extractors, facade, sys.path)

- Closes: GAP-D1-011, GAP-D1-012, GAP-D1-014, GAP-D1-015
- Current state: four hygiene defects: (1) hardcoded `/opt/OS` store paths ignoring UMH_ROOT — substrate/reality_model/canonical.py:25, instance.py:25 (siblings do it correctly: reality_graph.py:29, organism/world_model.py:27). (2) organism/world_model.py self-model extractors probe nonexistent saas/ paths (lines 395, 419-421, 556-559) — no saas/ dir exists, so `transport_cockpit_api` is permanently mis-reported MISSING. (3) substrate/reality_model/__init__.py:1-37 omits its own stores (CanonicalRealityModel, InstanceRealityModel, InstanceObservation, CanonicalPattern, SimulationReality) — 20+ consumers import submodules directly. (4) understanding modules insert a mis-computed "repo root" (actually substrate/understanding/) into sys.path — world_model.py:16-18, reality_engine.py:33-35 — risking top-level module shadowing (`domains`, `ontology`).
- Desired state: UMH_ROOT-derived store paths; extractor targets match actual topology (cockpit/, transports/api/http/); package facade exports the full contract (or documents submodule-import as convention); zero sys.path mutation inside substrate modules.
- Files to inspect: the six files above
- Files likely modified: canonical.py, instance.py, organism/world_model.py, reality_model/__init__.py, understanding/world_model/world_model.py, understanding/reality/reality_engine.py
- Forbidden files/actions: no hardcoded /opt/OS (the rule this enforces); store-path change must preserve reads of existing data files (same default when UMH_ROOT unset).
- Dependencies: none
- Risk class: MEDIUM (small edits to live modules)
- Approval required: no
- Acceptance criteria: grep for `"/opt/OS` in reality_model returns only env-default fallbacks; self-model run reports cockpit transport correctly; facade imports work; `sys.path` grep in substrate/understanding returns zero mutations.
- Proof required: self-model extractor output before/after; grep transcripts.
- Tests to add/run: new tests/test_reality_model_hygiene.py.
- Rollback plan: git revert.
- Expected output: hygiene fixes, no semantic change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P3

### WP-P3-019: Move WatermarkStore to a neutral canonical location

- Closes: GAP-D2-013
- Current state: the EOS poller imports the Notion adapter's WatermarkStore (`projections/eos/integration/poller.py:15` ← `adapters/notion/integration/watermarks.py`) — a de-facto generic watermark store living inside a specific adapter.
- Desired state: WatermarkStore at a neutral canonical location (adapters/ shared module or substrate/state/), imported by both Notion and projection pollers; old path re-exports during deprecation.
- Files to inspect: adapters/notion/integration/watermarks.py, poller.py, other WatermarkStore importers (grep)
- Files likely modified: new neutral module, watermarks.py (re-export shim), poller.py import
- Forbidden files/actions: centralized-utilities rule (this packet enforces it); no behavior change to watermark semantics; dependency direction respected (substrate/state/ placement must not import adapters/).
- Dependencies: none
- Risk class: LOW
- Approval required: no
- Acceptance criteria: one canonical definition; all importers on the new path or the shim; polling still advances watermarks (test).
- Proof required: grep inventory; poller unit test.
- Tests to add/run: watermark round-trip test.
- Rollback plan: git revert.
- Expected output: canonical watermark utility.
- Parallelizable: yes
- Requires human approval: no
- Phase: P3

### WP-P3-020: Consolidate third-party OAuth tokens into the platform credential path
- Closes: GAP-E1-007
- Current state: the same class of secrets lives in three trust boundaries: EOS `oauth_tokens` table (data/repos/entrepreneuros/shared/schema.ts:425-449) and LyfeOS `integrations` table (data/repos/LYFEOS/shared/schema.ts:1006-1037) hold access/refresh tokens in product DBs, parallel to the governed UMH path (`services/oauth_device_flow.py` + `substrate/execution/credential_gate.py` + 1Password per .claude/rules/credential-injection.md).
- Desired state: all third-party tokens held in the platform credential path (1Password-backed, credential-gate-validated); product tables hold opaque references only. Because product-DB writes happen in the product repos, this packet delivers: (1) the platform-side token vault interface + reference format, (2) the credential-gate check that refuses platform-side use of raw product-DB tokens, (3) a written migration directive for the two product repos.
- Files to inspect: services/oauth_device_flow.py; substrate/execution/credential_gate.py; data/repos/entrepreneuros/shared/schema.ts:425-449; data/repos/LYFEOS/shared/schema.ts:1006-1037; .claude/rules/credential-injection.md.
- Files likely modified: substrate/execution/credential_gate.py (reference resolution); services/oauth_device_flow.py; new migration directive doc.
- Forbidden files/actions: credential-injection law — no plaintext tokens in code, CLI args, or committed files; never log token values; product schema edits are declaration-only on the VPS (node-role discipline).
- Dependencies: none
- Risk class: HIGH (credential path is core trust infrastructure)
- Approval required: yes — secret-handling architecture.
- Acceptance criteria: `validate_credential_source()` accepts vault references and rejects raw-token payloads (unit test); oauth_device_flow stores into the vault path; the migration directive enumerates every token column with its target reference format.
- Proof required: credential-gate unit-test output; directive doc.
- Tests to add/run: new tests for credential_gate reference resolution; existing oauth flow tests.
- Rollback plan: gate change flag-guarded; revert flag.
- Expected output: code change + migration directive doc.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P3

---

## P4 — Projection capability build-out (20 packets)

**Objective.** Activate the projection surfaces on top of the converged contracts: manifest-driven registration and pollers, EOS/CreatorOS/LyfeOS capability expansion, governed external actuation (payments, publishing, calendar/notifications, broadcast, physical), and the governed continuity loop.

**Entry criteria.** P3 registration/port (WP-P3-004/013) and writeback (WP-P3-009) contracts landed.

**Exit criteria.** Every projection is either wired end-to-end (poll → signal → handler → outcome) or explicitly classified dormant; every externally visible actuation runs behind governed mutation with approval and proof.

### WP-P4-001: Repair or retire the broken nightly scrape → ICP → KPI chain
- Closes: GAP-C3-012
- Current state: cron fires `docker-compose run --rm os-scraper` at 4am (`infra/crontab.managed`); `services/overnight_scrape.py:144` calls `services/apify_scraper.py` (confirmed absent) and reads/writes `01_Inbox/raw_signals/` + `03_CRM/` (confirmed absent). The chain (apify → `icp_scorer` → `kpi_tracker`) is broken; `icp_scorer.py` and `kpi_tracker.py` are stranded downstream. Dead compute + log noise nightly.
- Desired state: the cron entry is removed or repaired; `icp_scorer.py`/`kpi_tracker.py` are classified per the dormant-classification protocol (PROMOTE/MERGE/ISOLATE/ARCHIVE/DELETE).
- Files to inspect: `infra/crontab.managed` (`0 4 * * *`); `services/overnight_scrape.py:139-152`; `services/icp_scorer.py`; `services/kpi_tracker.py`.
- Files likely modified: `infra/crontab.managed`; `services/overnight_scrape.py`; classification records for the stranded modules.
- Forbidden files/actions: follow dormant-classification before deleting; do not leave a firing cron entry that references nonexistent code.
- Dependencies: none
- Risk class: LOW (ops hygiene / dormant code)
- Approval required: yes — dormant-classification decisions on working-intent code.
- Acceptance criteria: no cron entry references nonexistent scripts/dirs; each stranded module has a classification record; a dry run of the cron entry produces no missing-file error.
- Proof required: crontab diff; classification records; clean dry-run log.
- Tests to add/run: cron entry dry-run under `scripts/cron-run`.
- Rollback plan: restore crontab from git.
- Expected output: code change (+ documentation classification).
- Parallelizable: yes
- Requires human approval: yes
- Phase: P4

### WP-P4-002: Generalize the actuation maturity model and add a blocking human-confirmation gate + emergency stop + rollback
- Closes: GAP-G-008, GAP-G-009, GAP-G-014, GAP-G-017
- Current state: the actuation maturity ladder L0-L7 (`substrate/execution/actuation/actuator_maturity_v1.py:16-77`) hardwires Chrome-specific evidence keys (`chrome_pid`, `:40-76`); `founder_confirmation_required=True` (`windows_foreground_actuator_v1.py:84`) is a recorded field, not a blocking gate; backend selection ignores `security_risk` (`actuator_backend_registry_v1.py:244-268`). There is no emergency stop — once `capability.execute` is dispatched, only the timeout bounds it (600s HTTP relay `server.py:980`, 300s node `client.py:499-501`); no mesh method cancels an in-flight execution. No rollback primitive exists in the actuation/mesh path (`grep def rollback` → no live hits); the `side_effects` field on CapabilityResponse (`handlers.py:122`) is never populated or consumed. `PHYSICAL_WORLD` risk exists as a category (`risk_classes.py:30`) but has no gate/adapter/safety-envelope semantics.
- Desired state: an application-agnostic evidence schema (process/window/focus/nav/screenshot as generic dimensions); L6 requires a blocking approval workflow; backend selection weighs `security_risk`; a `capability.cancel` RPC + node-side cooperative cancellation + operator-facing emergency stop (drain + deny new dispatches); every REVERSIBLE_WRITE capability declares its compensating action and persists a `side_effects` ledger per trace_id; PHYSICAL_WORLD operations are structurally impossible without a safety-envelope contract (rate limit, e-stop, human-in-loop) defined before the first physical adapter ships.
- Files to inspect: `substrate/execution/actuation/actuator_maturity_v1.py:16-106`; `substrate/execution/actuation/windows_foreground_actuator_v1.py:84-314`; `substrate/execution/actuation/actuator_backend_registry_v1.py:78-268`; `transports/node_mesh/server.py:980`; `nodes/windows/umh_node/client.py:453,499-501`; `transports/node_mesh/integration/handlers.py:122`; `substrate/governance/risk_classes.py:30`.
- Files likely modified: the actuation modules; `transports/node_mesh/server.py` + node client (cancel RPC); `transports/node_mesh/integration/handlers.py` (side_effects ledger); a new safety-envelope contract module.
- Forbidden files/actions: no irreversible actuation without prior approval + proof; PHYSICAL_WORLD must fail-closed until the safety contract exists; keep dependency direction.
- Dependencies: WP-P0-002, WP-P0-004 (approval consolidation)
- Risk class: HIGH (actuation safety)
- Approval required: yes — safety-critical actuation semantics.
- Acceptance criteria: maturity evidence schema is application-agnostic; an L6 claim blocks on human confirmation; `capability.cancel` aborts an in-flight execution; a REVERSIBLE_WRITE populates a `side_effects` ledger; a PHYSICAL_WORLD op is rejected without a safety-envelope contract.
- Proof required: cancel-mid-execution log; side_effects ledger entry per trace_id; blocked L6 claim awaiting confirmation; PHYSICAL_WORLD rejection.
- Tests to add/run: `tests/test_actuation_cancel.py`; `tests/test_actuation_safety_envelope.py`.
- Rollback plan: revert; cancel RPC additive.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P4

### WP-P4-003: Reduce services/ to thin entrypoints; move business logic and mutable state out
- Closes: GAP-A-012, GAP-C3-019
- Current state: `.claude/rules/architecture-layers.md:31` says services/ is "deployment entrypoints only. No business logic," but services/ holds scoring/KPI/cost-tracking/auth-flow/relay logic and 7+ mutable JSON state files (`calls_log.json`, `cost_log.json`, `kpi_history.json`, `revenue_log.json`, etc.); `operator_api.py` (865L) owns the OrganismDaemon lifecycle + module globals that other layers import; `services/discord_bot_commands.py` is 3,113 lines (exceeds the 3,000-line standard) mixing 93 command handlers with inline SQL and inline GWS calls.
- Desired state: business logic relocated to substrate/adapters/transports; entrypoints reduced to launchers; runtime JSON state moved to the data plane or DB; `discord_bot_commands.py` split per domain with mutation logic extracted behind governed contracts.
- Files to inspect: services/ listing (icp_scorer.py, kpi_tracker.py, cost_tracker.py, magic_link_*.py, oauth_device_flow.py, browser_relay.py, etc.); `services/operator_api.py:143-164`; `services/discord_bot_commands.py` (wc -l = 3113).
- Files likely modified: the logic-bearing service files (relocate logic); `services/discord_bot_commands.py` (split); state-file locations.
- Forbidden files/actions: keep dependency direction on relocation; no god files (>3000 lines); restart affected containers (`os-discord`, `os-operator`) and verify clean startup after moves.
- Dependencies: WP-P1-007, WP-P1-010 (mutation logic must land behind governed contracts)
- Risk class: MEDIUM (large refactor across deployed services)
- Approval required: yes — touches deployed entrypoints.
- Acceptance criteria: services/ files contain launcher/wiring only (no scoring/KPI business logic); no service file exceeds 3,000 lines; runtime state no longer stored as service-dir JSON; `os-discord`/`os-operator` start clean.
- Proof required: `wc -l` on split files; clean container logs; grep showing relocated logic imported from its new home.
- Tests to add/run: import-smoke of split modules; container startup verification.
- Rollback plan: revert per-file; state-file move reversible from git/backup.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P4

### WP-P4-004: Manifest-driven integration registration + generic poller (activate CreatorOS, LyfeOS, Broadcast)
- Closes: GAP-E1-001, GAP-E3-001
- Current state: only EOS and Notion are wired at boot: `transports/api/app.py:142-203,363` registers `_register_eos_integration()` (EOSPoller/handler/emitter/receiver); CreatorOS and LyfeOS have complete manifests/handlers/signals/outcomes/tables passing 33 unit tests (tests/test_lyfeos_creatoros_integration.py) but NO poller module and NO registration call — dormant. The same defect for broadcast: `BroadcastCapabilityHandler` (adapters/broadcast/integration/handlers.py:19) + manifest exist with zero registration anywhere (`transports/api/app.py:86-116` registers only Notion); the SLICE0 proof report's "registration PASS" was a validation-run instantiation, not runtime wiring (docs/superpowers/specs/broadcast/SLICE0_PROOF_REPORT.md:178-186). One underlying defect: registration is hand-rolled per integration instead of manifest-driven.
- Desired state: a generic registration runtime in the transports layer: iterate registered manifests (from the projection/capability registry per WP-P3-013), instantiate handler + a generic poller parameterized by the manifest's polled tables (EOSPoller generalized), gate each by env config; CreatorOS, LyfeOS, and Broadcast register at boot with zero bespoke functions.
- Files to inspect: transports/api/app.py:80-210,360-370; projections/eos/integration/poller.py (template to generalize); projections/creatoros/integration/{manifest,handlers,tables}.py; projections/lyfeos/integration/{manifest,handlers,tables}.py; adapters/broadcast/integration/{manifest,handlers}.py; docs/superpowers/specs/broadcast/AGENT_GOLIVE_INVESTIGATION.md:230-242 (documented registration pattern).
- Files likely modified: transports/api/app.py; new transports/api/integration_registration.py; new generic poller module (projections-shared or transports layer); projections/eos/integration/poller.py (subsume).
- Forbidden files/actions: substrate must not gain projection imports (registration lives in transports — dependency direction); CPU gate before poll cycles; deterministic polling (no LLM in the poll loop); env-gated activation defaults OFF for products without configured DB connections.
- Dependencies: WP-P3-004 (canonical projection ids), WP-P3-013 (registry-driven manifests)
- Risk class: MEDIUM (modifying the live app boot path)
- Approval required: yes — activates polling against two product databases.
- Acceptance criteria: with env config present, app boot logs registration for eos+creatoros+lyfeos+broadcast; generic poller emits the manifest-declared signals from fixture rows for each product; with env absent, boot is unchanged (EOS-only parity); broadcast capabilities dispatchable through the capability registry by an agent cell.
- Proof required: boot log; per-projection signal-emission test output; one broadcast capability dispatch trace.
- Tests to add/run: tests/test_lyfeos_creatoros_integration.py; new registration-runtime test; tests/adapters/broadcast/.
- Rollback plan: env flags OFF restores current behavior instantly; code revert removes the runtime.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P4

### WP-P4-005: Wire CreatorOS/LyfeOS integrations or classify them DORMANT

- Closes: GAP-D2-007
- Current state: CreatorOS and LyfeOS projections are integration-only shells with no runtime path: no entities/agents/views/workflows, no poller, and their emitters/handlers/outcome receivers are registered nowhere — `transports/api/app.py:140-201` wires EOS only; consumers are tests (tests/test_lyfeos_creatoros_integration.py) and a product_connections status probe.
- Desired state: either wire pollers + registry registration to parity with the EOS path, or explicitly classify both DORMANT in the component-status taxonomy (CONFIRMED_RUNTIME…DORMANT) with the decision recorded.
- Files to inspect: projections/creatoros/, projections/lyfeos/, transports/api/app.py:140-201, projections/eos/integration/poller.py (parity template)
- Files likely modified: if wired: new pollers + app.py registration; if DORMANT: .claude/CLAUDE.md component-status section / status doc
- Forbidden files/actions: dormant-classification protocol (PROMOTE/MERGE/ISOLATE/ARCHIVE/DELETE) before any removal; if wiring: WP-P0-010's tenant-scope pattern must be applied from day one; credential-injection law for any new DB connections; never restart all services simultaneously.
- Dependencies: WP-P0-010, WP-P3-009, WP-P3-004
- Risk class: MEDIUM (new wiring) — LOW if the DORMANT route is chosen
- Approval required: yes — business decision: activate two product integrations or park them.
- Acceptance criteria: wired: a CreatorOS and a LyfeOS signal each traverse poll→signal→handler→outcome in a test environment; DORMANT: status doc updated and probe reports the classification.
- Proof required: end-to-end integration test trace, or the classification record.
- Tests to add/run: extend tests/test_lyfeos_creatoros_integration.py to runtime-path assertions (or mark environment-gated).
- Rollback plan: registration is additive — unregister + git revert.
- Expected output: two projections with honest runtime status.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P4

### WP-P4-006: Declared integration coverage matrix per projection

- Closes: GAP-D2-008
- Current state: integration coverage is a thin, undeclared slice: EOS 5/15 tables, CreatorOS 4/20, LyfeOS 4/35 observable/actuatable (tables.py constants vs `grep -c pgTable` on vendored schemas = 15/20/35); communities, rituals, missions, calendar, documents etc. are invisible to the control plane with no record that this is intentional.
- Desired state: a declared coverage matrix per projection with explicit in-scope/out-of-scope marks per table; expansion happens through the capability registry, not ad-hoc; the correspondence tool (WP-P3-010) validates the matrix against both sources.
- Files to inspect: projections/*/integration/tables.py, data/repos/*/shared/schema.ts
- Files likely modified: new coverage manifest per projection (data or module constant), correspondence tool extension
- Forbidden files/actions: no new table wiring in this packet (declaration only); expansion packets route through capability registry (WP-P2-018).
- Dependencies: WP-P3-010
- Risk class: LOW
- Approval required: no
- Acceptance criteria: matrix rows sum to 15/20/35 exactly (independent pgTable count); every wired table marked in-scope; tool fails on an unmarked table.
- Proof required: count reconciliation transcript.
- Tests to add/run: extend tests/test_schema_correspondence_tool.py.
- Rollback plan: git revert.
- Expected output: documentation/manifest-only packet.
- Parallelizable: yes
- Requires human approval: no
- Phase: P4

### WP-P4-007: Promote or archive the dormant L4 grounding runtimes

- Closes: GAP-D2-010
- Current state: the bulk of the L4 grounding layer has test-only dependents per the dependency graph: SourceTruthLinker, SourceTruthRuntime, ProjectionEngine, ProjectionReconciliationEngine, ProjectionIntegrationRuntime, CorrespondenceScheduler (substrate/organism/source_truth_linker.py, source_truth_runtime.py, projection_engine.py, projection_reconciliation_engine.py, projection_integration_runtime.py, correspondence_scheduler.py) — no runtime consumers.
- Desired state: each of the six classified per the dormant taxonomy: promoted (wired into the daemon tick / governed spine) or archived; no module left in limbo.
- Files to inspect: the six modules + the organism daemon tick loop + tests/test_source_truth_linker.py
- Files likely modified: daemon wiring for promoted modules; archive moves for the rest; component-status doc
- Forbidden files/actions: dormant-classification before archive; CPU gate check before adding any work to the daemon tick; promoted reconciliation must route mutations through governed_mutation (WP-P0-001).
- Dependencies: WP-P3-004 (projection engine rename), WP-P1-001
- Risk class: MEDIUM
- Approval required: yes — wiring reconciliation into the live daemon changes runtime behavior.
- Acceptance criteria: graph dependents for each module show a runtime consumer or the module is archived; daemon tick stays within CPU-gate thresholds under the new load.
- Proof required: classification table (6/6); daemon logs post-wire; CPU-load sample.
- Tests to add/run: run tests/test_source_truth_linker.py; new daemon-wiring test for promoted modules.
- Rollback plan: unwire from tick + git revert; archives reversible from git.
- Expected output: zero limbo modules in the L4 layer.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P4

### WP-P4-008: Grounding evaluation and confidence calibration for domain bridges

- Closes: GAP-D2-011
- Current state: semantic grounding is keyword-lookup V1 only: business/creator/life bridges are static keyword maps; substrate/understanding/domains/business.py:1-10 self-declares a V2 TODO for disambiguation; bridge confidence values are not evidence-linked to proof artifacts and there is no evaluation/calibration loop.
- Desired state: evaluation results + confidence calibration for bridge mappings (a labeled fixture corpus scoring precision per bridge); a disambiguation path with a deterministic fallback; confidence values traceable to evaluation evidence.
- Files to inspect: the bridge modules (post-relocation per WP-P3-015), substrate/understanding/domains/contract.py, WP-P2-017's EvaluationResult
- Files likely modified: bridge registry (evaluation hooks), new calibration fixture corpus + scorer, bridge content confidence fields
- Forbidden files/actions: deterministic-first — keyword lookup remains the spine; LLM disambiguation is optional enhancement with the keyword result as fallback; no ungrounded confidence constants added.
- Dependencies: WP-P3-015, WP-P2-017
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: calibration run emits EvaluationResult records per bridge; confidence values updated from measurements; all-providers-down test still produces grounding output.
- Proof required: calibration report; degradation test output.
- Tests to add/run: new tests/test_bridge_calibration.py.
- Rollback plan: calibration is additive metadata; git revert.
- Expected output: measured, calibrated grounding layer.
- Parallelizable: yes
- Requires human approval: no
- Phase: P4

### WP-P4-009: Extend the EOS bridge to tasks/agent-actions and map product approvals into the UMH approval authority
- Closes: GAP-E1-005, GAP-E1-014
- Current state: (a) the EOS bridge covers only the CRM slice — 3 of 15 tables (projections/eos/integration/manifest.py:113 polls crm_contacts/crm_deals/crm_activities); `tables.py` already has TaskRow/AgentActionRow readers (projections/eos/integration/tables.py:104-116,228-261) that no signal descriptor or capability exposes; agent_metrics and notifications are never read. (b) The EOS product runs its OWN approval loop — `agent_actions` with requiresApproval/approvedBy/status (data/repos/entrepreneuros/shared/schema.ts:376-423) — unlinked to the UMH `approvals` table (transports/api/http/db/schema.ts:161) and `substrate/sockets/approval_port.py`. Two approval authorities for the same actions.
- Desired state: SIGNAL_DESCRIPTORS/CAPABILITY_DESCRIPTORS extended to task and agent-action lifecycles; product agent_actions requiring approval surface as UMH approvals (L4 mapping row linking product action id ↔ approval id), decided through the UMH approval authority and written back; single approval source of truth declared.
- Files to inspect: projections/eos/integration/manifest.py; projections/eos/integration/tables.py:89-270; substrate/sockets/approval_port.py; transports/api/http/db/schema.ts:155-175; data/repos/entrepreneuros/shared/schema.ts:376-423.
- Files likely modified: projections/eos/integration/manifest.py; projections/eos/integration/tables.py; projections/eos/integration/handlers.py; possibly a small L4 mapping table (platform DB).
- Forbidden files/actions: writeback columns must follow WP-P3-009's declared schema design; approval decisions only through the UMH authority once mapped (no double-decide); CRITICAL discipline if the mapping table is added.
- Dependencies: WP-P4-004 (poller runtime), WP-P3-009 (writeback design), WP-P1-007 (server-side approval unification)
- Risk class: MEDIUM (extending manifest/handlers) + CRITICAL element if mapping table added
- Approval required: yes — merges two approval systems.
- Acceptance criteria: a fixture agent_action with requiresApproval produces a UMH approval; deciding it in UMH writes the decision back to the product row (status + approvedBy); task lifecycle signals emitted from fixture rows; no approval decidable in two places (the product-side decide path is documented as deprecated or mirrored read-only).
- Proof required: end-to-end fixture trace (product row → approval → decision → writeback row diff).
- Tests to add/run: extend tests/test_eos_projection.py with the approval round-trip.
- Rollback plan: manifest additions removed; mapping table dropped; product loop resumes standalone.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P4

### WP-P4-010: LyfeOS capability expansion driven from its schema surface
- Closes: GAP-E1-008
- Current state: LyfeOS has the largest domain surface (~35 tables in data/repos/LYFEOS/shared/schema.ts: userStats, userProfile ~130 fields, quests with recurrence + external calendar sync fields :311-356, calendarEvents :368-383, kanban/canvas/spreadsheets, mediaAlbums/Items, smartReminders, progressTrackers, userActivityEvents, pushSubscriptions) against the thinnest bridge — 3 polled tables + 3 capabilities (projections/lyfeos/integration/manifest.py:99) — and the bridge itself is dormant until WP-P4-004.
- Desired state: prioritized expansion executed from the schema surface: wave 1 = quests + user_daily_logs + vision_goals live (existing manifest, now polling); wave 2 = calendarEvents bridged to the calendar adapters (`Capability.CALENDAR_MANAGE` — substrate/execution/runtime/capability_router.py:62; adapters/calendar/, adapters/google_workspace/); wave 3 = quest recurrence mapped onto the schedule primitive (WP-P2-028) and rituals scaffold (substrate/execution/bridge/rituals.py); remaining tables get an explicit deferred/bridged decision row in the manifest doc.
- Files to inspect: data/repos/LYFEOS/shared/schema.ts (full); projections/lyfeos/integration/{manifest,tables,handlers}.py; substrate/execution/bridge/rituals.py; substrate/execution/runtime/capability_router.py:36-73.
- Files likely modified: projections/lyfeos/integration/manifest.py; projections/lyfeos/integration/tables.py; projections/lyfeos/integration/handlers.py.
- Forbidden files/actions: projection code stays in projections/ (boundary law); writeback per WP-P3-009; no substrate types redefined (type coherence).
- Dependencies: WP-P4-004, WP-P2-028, WP-P3-009
- Risk class: MEDIUM (extending live integration modules)
- Approval required: no (env-gated; additive capability descriptors)
- Acceptance criteria: signal descriptors + capabilities exist for waves 1-2 with fixture-row tests; calendar round-trip (LyfeOS calendarEvent → platform calendar adapter object) passes; every unbridged table has a decision row (count matches table count in schema.ts).
- Proof required: fixture test output; decision-coverage count vs `grep -c 'pgTable' data/repos/LYFEOS/shared/schema.ts`.
- Tests to add/run: extend tests/test_lyfeos_creatoros_integration.py.
- Rollback plan: manifest revert; poller ignores removed descriptors.
- Expected output: code change.
- Parallelizable: yes (after deps)
- Requires human approval: no
- Phase: P4

### WP-P4-011: CreatorOS community/social-graph domain surface
- Closes: GAP-E1-009
- Current state: 8 community/messaging tables (communities, channels, channelMessages, followers — data/repos/creatoros/shared/schema.ts:155-216; conversations, conversationParticipants, directMessages :310-362) have zero UMH surface; substrate has no community domain model and `substrate/sockets/message_port.py:1-25` is a persistence sink only, not a messaging domain model.
- Desired state: an L3 community domain model in the projection layer (Community/Channel/Membership/FollowEdge types) + signal descriptors for community events (member joined, message posted, follower added) added to the CreatorOS manifest; substrate stays generic (signals only) — no community model migrates into substrate.
- Files to inspect: data/repos/creatoros/shared/schema.ts:155-216,310-362; projections/creatoros/integration/{manifest,tables,handlers}.py; substrate/sockets/message_port.py.
- Files likely modified: projections/creatoros/integration/manifest.py; projections/creatoros/integration/tables.py; new projections/creatoros/domain/community.py.
- Forbidden files/actions: projection boundary — community types stay in projections/; type coherence check before any new shared type; writeback per WP-P3-009.
- Dependencies: WP-P4-004
- Risk class: LOW (new projection files + additive manifest rows)
- Approval required: no
- Acceptance criteria: fixture rows in the 8 tables produce the new signals through the generic poller; domain types round-trip from Drizzle-shaped fixtures.
- Proof required: signal-emission test output.
- Tests to add/run: extend tests/test_lyfeos_creatoros_integration.py with community fixtures.
- Rollback plan: revert manifest/domain additions.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P4

### WP-P4-012: Bridge product notification stores into the substrate notification engine
- Closes: GAP-E1-011
- Current state: product notification stacks are disjoint from the platform: EOS `notifications` (data/repos/entrepreneuros/shared/schema.ts:189-214) and CreatorOS notifications (data/repos/creatoros/shared/schema.ts:287-307) are unbridged tables; LyfeOS uses quest `notifications` jsonb + FCM `pushSubscriptions` (data/repos/LYFEOS/shared/schema.ts:769-779); the substrate engine (`substrate/sockets/notification_engine.py:22-34`, 5 channels, tested) and the cockpit VAPID push stack (`transports/api/cockpit_push_routes.py`) never see any of them.
- Desired state: product notification events emitted as signals via the manifests (poll or trigger) and fanned out by the substrate notification engine as the single fan-out authority; product tables remain product-facing render stores; FCM tokens noted as a channel target owned by the platform push registry (WP-P5-017).
- Files to inspect: substrate/sockets/notification_engine.py; the three product schema notification sections; projections/*/integration/manifest.py; transports/api/cockpit_push_routes.py.
- Files likely modified: projections/eos|creatoros|lyfeos integration manifests/tables (notification signal descriptors); possibly a notification-engine channel adapter.
- Forbidden files/actions: engine stays projection-agnostic (no product names in substrate); dedup guard so bridged notifications don't double-send to the same operator via product + platform channels.
- Dependencies: WP-P4-004, WP-P5-017
- Risk class: MEDIUM (touches the live notification engine's input set)
- Approval required: no
- Acceptance criteria: a fixture product notification row emits one engine event and exactly one delivery per subscribed channel (dedup test); engine tests still green.
- Proof required: fan-out test output with dedup assertion.
- Tests to add/run: tests/test_notification_engine.py + new bridge tests.
- Rollback plan: remove descriptors; engine input set reverts.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P4

### WP-P4-013: Governed payments adapter (Stripe first) with entitlement model
- Closes: GAP-E1-006
- Current state: `Capability.PAYMENT_PROCESS` is an enum value + intent regex only (substrate/execution/runtime/capability_router.py:61,454-460); the authority engine deliberately denies payment execution (tests/test_execution_authority_engine_v1.py financial-denial tests); yet two projections need governed payments: CreatorOS products/revenue (data/repos/creatoros/shared/schema.ts:89-109,219-232 — `record_revenue` is a DB insert, not a payment) and LyfeOS Stripe subscription fields (data/repos/LYFEOS/shared/schema.ts:37-38), with tests/test_phase14_6b_lyfeos_code_resolved_canon.py::test_no_stripe_resources_created confirming deliberate non-implementation to date.
- Desired state: an adapters-layer payments adapter (Stripe API) exposing risk-classed capabilities (create_checkout, refund, subscription read/update) that execute ONLY through governed mutation with mandatory approval for money-moving operations; an entitlement read model for LyfeOS subscriptions; the authority-engine denial replaced by an explicit approval-required policy (deny remains the default absent approval).
- Files to inspect: substrate/execution/runtime/capability_router.py:36-75,430-480; adapters/ (structure precedent, e.g. adapters/google_workspace/); tests/test_execution_authority_engine_v1.py (denial contract); .claude/rules/credential-injection.md.
- Files likely modified: new adapters/payments/stripe_adapter.py; substrate/execution/runtime/capability_router.py (routing rows); substrate/organism/mutation_registry.py (payment mutation specs, approval-required).
- Forbidden files/actions: Stripe keys via 1Password op run only (credential-injection law); money-moving ops NEVER auto-approved regardless of risk-score (hard stop); test against Stripe test mode only until operator sign-off; deterministic-first (no LLM in the payment path).
- Dependencies: WP-P2-011 (adapter contract), WP-P3-020 (token/credential path)
- Risk class: HIGH (financial actuation surface)
- Approval required: yes — financial capability activation.
- Acceptance criteria: a payment capability without an approval record is denied by the policy engine (test); with approval, a Stripe test-mode charge round-trips with a proof artifact; the phase14_6b no-Stripe-resources test is superseded by an explicit test-mode assertion; entitlement reads reflect a test subscription.
- Proof required: policy-denial test output; test-mode charge trace + proof artifact.
- Tests to add/run: new tests/adapters/test_stripe_adapter.py (mocked + test-mode); authority-engine tests updated deliberately.
- Rollback plan: routing rows removed → capability reverts to enum stub; adapter file inert without keys.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P4

### WP-P4-014: Governed external social publishing adapters
- Closes: GAP-E1-021
- Current state: CreatorOS `create_post` inserts a row in the product DB only (projections/creatoros/integration/manifest.py:55-66); `Capability.SOCIAL_POST` is regex-routed only (substrate/execution/runtime/capability_router.py:58,436-442); `adapters/broadcast/` is a streaming engine, not social publishing. No external platform publishing adapter exists despite the capability enum and the product's create_post.
- Desired state: per-platform publishing adapters (start with one platform end-to-end) behind governed mutation with approval for public posts; the product post row is the source record, the platform publish is the actuation with a proof artifact (post URL + response payload).
- Files to inspect: substrate/execution/runtime/capability_router.py:430-445; projections/creatoros/integration/manifest.py:41-96; adapters/ (contract precedent).
- Files likely modified: new adapters/social/<platform>_publisher.py; capability_router routing rows; mutation_registry spec (approval-required for public publish).
- Forbidden files/actions: platform API credentials via 1Password only; public posting never auto-approved (blast radius = public internet); rate limits enforced deterministically; no browser automation on the orchestrator node (browser-verification law) if a platform requires browser flows.
- Dependencies: WP-P3-020 (credentials), WP-P2-011 (adapter contract)
- Risk class: MEDIUM (new adapter + routing rows)
- Approval required: yes — public-facing actuation.
- Acceptance criteria: publish without approval → denied; with approval → post created on the external platform (sandbox/test account) and proof artifact stored with the post URL; product row linked to the proof.
- Proof required: proof artifact with external post reference.
- Tests to add/run: adapter unit tests (mocked API) + one live sandbox acceptance run.
- Rollback plan: remove routing rows; adapter inert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P4

### WP-P4-015: Verify and wire EOS organization-model persistence through governed reconciliation
- Closes: GAP-E1-020
- Current state: `projections/eos/entities.py:27-300` builds 10 Departments/Roles/Company/Portfolio as pure constructors from substrate/types.py; whether these are ever persisted via governed_mutation and reconciled against product state is UNVERIFIED — no write path found in entities.py or projections/eos/views/ (read-only). The org model may be a phantom: types without state.
- Desired state: ground-truth audit first (is there any persisted org state anywhere — platform DB, product DB, files?); then either (a) wire a persistence + reconciliation path (entities as desired state, `governed_mutation` writes, reconciliation report against actual), or (b) record the org model as compute-on-read with no persistence by design. Decision recorded either way.
- Files to inspect: projections/eos/entities.py; projections/eos/views/kpis.py; projections/eos/workflows/runner.py:29,140 (governed_mutation consumption precedent); transports/api/http/db/schema.ts (org tables :100-141).
- Files likely modified: projections/eos/entities.py (persistence hooks) or a decision record; possibly projections/eos/views/.
- Forbidden files/actions: writes only through `governed_mutation` (transports/api/governed.py path as runner.py does); no substrate schema change without CRITICAL discipline.
- Dependencies: WP-P4-004 (if reconciled against product rows)
- Risk class: LOW (audit + additive persistence) 
- Approval required: no
- Acceptance criteria: the audit answer is written down with evidence; if wired: departments/roles persist idempotently (re-run produces zero diffs) and a reconciliation report lists drift; if not wired: the decision record exists and entities.py docstring says so.
- Proof required: audit note + (if wired) idempotency run output.
- Tests to add/run: new test for idempotent org persistence (variant a).
- Rollback plan: revert hooks; constructors unaffected.
- Expected output: code change or decision record (documentation-only in variant b).
- Parallelizable: yes
- Requires human approval: no
- Phase: P4

### WP-P4-016: Implement the governed continuity loop (work continues while operator away)
- Closes: GAP-E2-017
- Current state: the doctrine marks the continuity behavior non-optional (docs/canonical/umh_synthesis.md §7.1: leave → governed continue → return → summarize → resume), but `substrate/workstation/overnight_queue.py:1-8` is explicitly a non-executing scaffold ("thin MVP … does not implement full autonomous execution" — queue/dry-run/approval-only); no governed autonomous continuation exists. The read side (`substrate/workstation/resume_brief.py`) exists.
- Desired state: governed continuation under a cadence policy: on operator-away presence transition, pre-approved queued work executes through the canonical spine with blast-radius limits (risk-class ceiling, per-domain allowlist, budget); on return, resume_brief summarizes what ran with proof links. Approval granted at queue time, not execution time; anything above the ceiling waits.
- Files to inspect: substrate/workstation/overnight_queue.py; substrate/workstation/resume_brief.py; presence authority (WP-P2-024's owner); substrate/organism/mutation_registry.py; docs/canonical/umh_synthesis.md §7.1.
- Files likely modified: substrate/workstation/overnight_queue.py (execution stage); new continuity policy module; transports route additions for queue approval.
- Forbidden files/actions: continuation NEVER exceeds the queued approval's risk envelope; CPU gate + cadence limits (this runs unattended on the VPS — Hostinger throttle history); deterministic scheduling; every executed item emits trace + proof.
- Dependencies: WP-P2-024 (presence authority triggers), WP-P1-017 (kernel), WP-P1-001 (canonical submission entry)
- Risk class: HIGH (unattended autonomous execution)
- Approval required: yes — autonomy expansion.
- Acceptance criteria: away-transition executes only pre-approved items within the ceiling (test with one allowed + one over-ceiling item: first runs, second holds); return produces a resume brief listing executions with proof links; kill switch (WP-P4-002 stop channel) halts the loop.
- Proof required: end-to-end away/return transcript with trace events and the resume brief artifact.
- Tests to add/run: new tests/test_continuity_loop.py (ceiling, hold, resume-brief).
- Rollback plan: execution stage behind a feature flag (default off); flip off restores scaffold behavior.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P4

### WP-P4-017: Broadcast audio pipeline (per-source inputs, amix, live volume/mute, VU readback)
- Closes: GAP-E3-002
- Current state: every shipped broadcast carries `anullsrc` silence — audio is marked ABSENT/CRITICAL in docs/superpowers/specs/broadcast/BROADCAST_BUILD_PLAN.md:104,150-177. The spike proved the mechanics (live volume/mute via ZMQ, astats VU readback path — docs/superpowers/specs/broadcast/AUDIO_SPIKE_FINDINGS.md:8-60) but nothing is built.
- Desired state: per-source audio inputs, amix with unity weights + per-source volume control (the spike-proven architecture), live mute/volume through the existing ZMQ client, VU readback surfaced to the cockpit BroadcastPanel and the capability API.
- Files to inspect: adapters/broadcast/ffmpeg_args.py; adapters/broadcast/filtergraph.py; adapters/broadcast/zmq_client.py:64-108; adapters/broadcast/scene_model.py; adapters/broadcast/engine.py; docs/superpowers/specs/broadcast/AUDIO_SPIKE_FINDINGS.md; transports/api/cockpit_broadcast_routes.py.
- Files likely modified: adapters/broadcast/ffmpeg_args.py; adapters/broadcast/filtergraph.py; adapters/broadcast/scene_model.py (audio fields); transports/api/cockpit_broadcast_routes.py (VU endpoint); cockpit BroadcastPanel store wiring.
- Forbidden files/actions: ffmpeg subprocesses only through the existing CPU-gated process lifecycle (adapters/broadcast/process_lifecycle.py); SSRF output validation preserved (ffmpeg_args.py `_validate_output_url`); license firewall — no GPL-flipping components (build plan Zone rules); state changes stay inside governed_mutation as routes already do.
- Dependencies: WP-P2-023 (scene-model type registration) — soft
- Risk class: MEDIUM (extending the live broadcast arg builder)
- Approval required: no
- Acceptance criteria: a two-source scene streams mixed audio (not silence) to the test RTMP target; live mute/volume change applies without process restart (pid stable); VU values stream to the panel endpoint; all 25+ filtergraph tests plus new audio tests pass.
- Proof required: proof stream recording with audible mix; pid-stability assertion output; VU sample log.
- Tests to add/run: extend tests/adapters/broadcast/ (audio graph construction, ZMQ volume command).
- Rollback plan: audio fields optional — scenes without them behave exactly as today; revert restores anullsrc.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P4

### WP-P4-018: Node-aware real capture and hardware encode for broadcast
- Closes: GAP-E3-003
- Current state: display/window/webcam/mic/system-audio capture and NVENC are ABSENT (BROADCAST_BUILD_PLAN.md:105-106); `nodes/windows/umh_node/adapters/broadcast.py` contains zero dshow/ddagrab/nvenc constructs — it wraps the same VPS libx264 `build_args` (lavfi/file/pull sources only). The node-aware capability→FFmpeg-construct resolution table exists only as spec (BROADCAST_BUILD_PLAN.md:34-48).
- Desired state: the arg builder resolves input/encoder constructs per runtime node capability (ddagrab/gdigrab/dshow/WASAPI on Windows; NVENC when detected); an encoder-detection probe runs on node startup and reports capability flags into the node's declared capability set; the Windows adapter builds Windows-native capture pipelines.
- Files to inspect: adapters/broadcast/ffmpeg_args.py; nodes/windows/umh_node/adapters/broadcast.py:32-181; nodes/windows/umh_node/client.py:120-130 (adapter registration); docs/superpowers/specs/broadcast/BROADCAST_BUILD_PLAN.md:34-48,179-197.
- Files likely modified: adapters/broadcast/ffmpeg_args.py (node-capability parameter); nodes/windows/umh_node/adapters/broadcast.py; nodes/windows/umh_node/client.py (probe + flags).
- Forbidden files/actions: encoder probe subprocesses use no-window creationflags on Windows (window-flicker rule) and respect the node's own load limits; NVENC chosen over x264 for hardware paths per the license strategy (BROADCAST_BUILD_PLAN.md:53-58); capability flags reported through the node registry, not hardcoded.
- Dependencies: WP-P2-010 (RuntimeNode capability registry) — soft; probe results can live in the node hello payload meanwhile
- Risk class: MEDIUM (arg-builder branching; existing sources must be byte-identical)
- Approval required: no
- Acceptance criteria: existing lavfi/file/pull arg outputs unchanged (golden tests); on a Windows node with NVENC, a display-capture + NVENC pipeline produces a live stream (executor-node acceptance); nodes without the hardware degrade to libx264 with a logged reason.
- Proof required: golden-diff output (empty) for existing sources; executor-node capture proof recording.
- Tests to add/run: golden arg tests; tests/adapters/broadcast/test_node_dispatch.py extension.
- Rollback plan: node-capability parameter defaults to VPS profile — revert restores current behavior.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P4

### WP-P4-019: Rooms transcription/recording — wire real capability or retract the permission surface
- Closes: GAP-E3-006
- Current state: meeting transcription/recording are permission-gated stubs: `transcript_placeholder: True` hardcoded on meeting creation (transports/api/cockpit_rooms_routes.py:1923); `recording_consent` flag (:440,1921) and `record_meeting`/`view_transcripts` permissions (:567,575) exist with no implementation. A local transcription primitive exists unconnected (`substrate/execution/media/media_processor.py:1-11`, faster-whisper + Gemini routing).
- Desired state: either (a) LiveKit egress/recording wired + media_processor transcription attached to meetings (consent-gated, artifacts stored via the asset primitive), or (b) the placeholder field, consent flag, and the two permissions removed so the permission envelope matches real capability. Truthfulness is the requirement; (a) is the build, (b) is the honest floor.
- Files to inspect: transports/api/cockpit_rooms_routes.py:434-457,560-580,1901-1990; substrate/execution/media/media_processor.py; LiveKit env config (LIVEKIT_* usage at cockpit_rooms_routes.py:2122-2156).
- Files likely modified: transports/api/cockpit_rooms_routes.py; (variant a) new recording/transcription worker module.
- Forbidden files/actions: recording without consent flag true must be impossible (hard gate); transcription runs deterministic-first (faster-whisper local before any cloud call); CPU gate for whisper subprocesses; assets via WP-P2-029, not base64-in-DB.
- Dependencies: WP-P1-019 (rooms store), WP-P2-029 (asset store) for variant a
- Risk class: MEDIUM
- Approval required: yes — recording humans requires an explicit product decision.
- Acceptance criteria: variant a: a test meeting produces a recording artifact + transcript linked to the meeting record, only when consent=true; variant b: grep shows no transcript_placeholder/record_meeting/view_transcripts/recording_consent remnants and the UI shows no dead toggles.
- Proof required: variant a: artifact + transcript for a consent-true meeting and refusal log for consent-false; variant b: grep output.
- Tests to add/run: rooms route tests for the consent gate (a) or removal (b).
- Rollback plan: variant a behind env flag; variant b revert restores stubs.
- Expected output: code change (variant b partially documentation/permission-schema cleanup).
- Parallelizable: yes
- Requires human approval: yes
- Phase: P4

### WP-P4-020: Scope-decision records for absent domain models (courses, ManufacturingOS, RoboticsOS, SecurityOS)
- Closes: GAP-E1-018, GAP-E3-009, GAP-E3-010, GAP-E3-011
- Current state: four domain surfaces exist as intent with zero (or near-zero) code, and none has a recorded scope decision: (1) course/learning modeling absent everywhere despite CreatorOS scope and LyfeOS learning-profile fields (data/repos/LYFEOS/shared/schema.ts:128-137); (2) ManufacturingOS — strategy-intent only, 15 explicit non-implementations (docs/system/strategic_context_amendment_v2_physical_moat_report.md:214-232; docs/strategy/product_map.md:133-136); (3) RoboticsOS — strategy-intent only, 10+ year horizon (product_map.md:128,135), with a naming-collision risk because "actuator" already means GUI actuation in substrate (substrate/execution/actuation/actuator_backend_registry_v1.py:17-28); (4) SecurityOS — zero repo evidence (repo-wide grep), only hooks `PhysicalDomain.SECURITY_PHYSICAL` and the HomeAssistant lock mapping (substrate/execution/adapters/physical.py:35,188).
- Desired state: one decision record (docs/strategy/ or data/audits/) with a row per domain: status (DEFERRED with trigger condition / OUT-OF-SCOPE), activation prerequisites (SecurityOS and RoboticsOS list WP-P1-020 and -019 as hard prerequisites), the reserved namespace for physical actuation (resolving the "actuator" collision on paper now), and the template-extensibility constraint (physical_moat_report §11) restated as a check for type-contract changes.
- Files to inspect: the four evidence sets above; docs/strategy/supersession_rules.md (record conventions).
- Files likely modified: one new decision-record doc.
- Forbidden files/actions: no code changes; no new types (this is a decision record, not scaffolding).
- Dependencies: none
- Risk class: LOW (new doc)
- Approval required: yes — scope decisions are the operator's.
- Acceptance criteria: record exists with all four rows, each carrying trigger condition + prerequisites; referenced from the strategy doctrine index.
- Proof required: the doc.
- Tests to add/run: none.
- Rollback plan: delete the doc.
- Expected output: documentation-only.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P4

---

## P5 — Cockpit convergence (19 packets)

**Objective.** Make the client a faithful projection of the control plane: five-surface information architecture, one approval queue, domain stores replacing per-panel stores, a single staleness policy, and removal of instance literals and broken distribution bindings.

**Entry criteria.** Server-side approval authority (WP-P1-007) and node identity (WP-P2-010) landed; P5 packets consume, not produce, server contracts. Layout lock (2026-07-03) applies: information-architecture and state-layer changes only.

**Exit criteria.** One client owner per control-plane object family; a decision made on any surface is visible on all; zero raw fetch bypasses; every registered panel reachable or dispositioned; all cockpit deploys via bash cockpit/deploy.sh.

### WP-P5-001: Add the operator-role guard to the open organism-signal endpoint
- Closes: GAP-C2-010
- Current state: `POST /organism/signal` is registered without the operator-role dependency (`transports/api/cockpit_organism_routes.py:84`) while all sibling mutations require it (`:89-96`); any clerk-authenticated principal can inject organism signals (the handler itself is governed, `:526-538`).
- Desired state: the endpoint takes the operator-role dependency, or the open posture is explicitly documented as intentional.
- Files to inspect: `transports/api/cockpit_organism_routes.py:84-96,526-538`; `transports/api/cockpit.py:135,168`.
- Files likely modified: `transports/api/cockpit_organism_routes.py`.
- Forbidden files/actions: single-line dependency change; do not alter the governed handler body.
- Dependencies: none
- Risk class: MEDIUM (auth on a live endpoint)
- Approval required: yes — changes who can inject signals.
- Acceptance criteria: a non-operator clerk principal is rejected from `/organism/signal`; an operator principal succeeds; sibling behavior unchanged.
- Proof required: rejection log (non-operator) + success log (operator).
- Tests to add/run: `tests/test_organism_signal_auth.py`.
- Rollback plan: revert single line.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P5

### WP-P5-002: Converge the settings-mutation pipeline into the governed spine
- Closes: GAP-C2-014
- Current state: `transports/api/cockpit_settings_mutations.py:1-16` implements its own validate→constrain→warn→approval-gate→persist→audit pipeline ("single entry point for all settings mutations") independent of MutationRouter/spine, while `settings_update` is separately registered (`mutation_registry.py:403-404`) and used by 16 `governed_mutation` call sites — two overlapping settings-mutation paths.
- Desired state: the settings pipeline runs as the execute_fn of a governed `settings_update` envelope (one spine, one journal), or is documented as a sanctioned pre-spine validator.
- Files to inspect: `transports/api/cockpit_settings_mutations.py:1-60`; `substrate/organism/mutation_registry.py:403-414`.
- Files likely modified: `transports/api/cockpit_settings_mutations.py`; the settings route call sites.
- Forbidden files/actions: no third parallel governance path; keep the approval gate but route it through the spine.
- Dependencies: WP-P1-007
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: a settings mutation produces a single governed-spine journal entry (not a separate parallel audit); the pipeline is the envelope's execute_fn or documented as a validator.
- Proof required: single journal entry for a settings change.
- Tests to add/run: `tests/test_settings_mutation_governed.py`.
- Rollback plan: revert per-file.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-003: Express the five-surface model in routes.ts — nesting metadata, structural absorption, orphan + shortcut resolution, Proof promotion
- Closes: GAP-F1-001, GAP-F1-004, GAP-F1-013, GAP-F1-015, GAP-F2-009
- Current state: (a) `cockpit/src/renderer/types/routes.ts:55-171` has only `group: 'primary'|'system'` and flat visibility — ~60 panels form one undifferentiated [DEV] list in CommandPalette (components/CommandPalette.tsx:55-63); the five-surface model (Command/Operations/Reality/Proof/Capability) exists only implicitly. (b) 7 registered panels are unreachable — `executive`, `governance`, `learning`, `prediction`, `skills`, `tasks`, `workintelligence` exist in PANEL_COMPONENTS (components/canvas/windows/PanelWindowContent.tsx) with no routes.ts entry; governance observability is invisible in a governance-first control plane. (c) routes.ts comments declare absorptions ("Absorbed into Command Center" :102, "Absorbed into Meta IDE" :110,:122, "Absorbed into Organism Map" :112, "Absorbed into Activity" :120) that were never structurally executed — absorbed panels persist as independent route+component+store. (d) Shortcut collisions: key '6' → browser (:80) and analytics (:168); key 'g' → propagation (:132) and realitygraph (:139). (e) The Proof surface (ProofInspectorPanel :164, ApprovalsPanel :74, GovernancePanel, MemoryPanel) is dev-visibility only — approval/proof inspection is not first-class navigation.
- Desired state: RouteEntry gains `surface: 'command'|'operations'|'reality'|'proof'|'capability'` and `absorbedInto?: routeId` metadata; CommandPalette + CanvasPalette group by surface; absorbed routes open inside their anchor (tab/section) instead of as free windows; the 7 orphans each get a surfaced route or `deprecated` visibility; shortcut keys unique; Proof anchor (ProofInspector + unified approvals) promoted to primary visibility. IA-only — the locked layout, chat styling, and input design are untouched.
- Files to inspect: cockpit/src/renderer/types/routes.ts (full); cockpit/src/renderer/components/CommandPalette.tsx; cockpit/src/renderer/components/canvas/CanvasPalette.tsx; cockpit/src/renderer/components/canvas/windows/PanelWindowContent.tsx; cockpit/src/renderer/stores/cockpitStore.ts (nav state).
- Files likely modified: types/routes.ts; CommandPalette.tsx; CanvasPalette.tsx; PanelWindowContent.tsx (nested-open support); cockpitStore.ts.
- Forbidden files/actions: layout lock — no visual redesign, no chat/input changes; deploy via `bash cockpit/deploy.sh` only; no panel deletion in this packet (nest/hide/defer only, per F1 ledger).
- Dependencies: none (anchor-tab rendering for specific clusters lands in WP-P5-007…WP-P5-015)
- Risk class: MEDIUM (navigation metadata + palette logic)
- Approval required: yes — changes primary navigation content (Proof promotion).
- Acceptance criteria: every PANEL_COMPONENTS key has a routes.ts entry (comm diff empty); `grep -oP "key: '\K[^']+" types/routes.ts | sort | uniq -d` empty; palettes render five surface groups; opening an absorbed route opens its anchor with the absorbed content focused; Proof reachable from primary nav.
- Proof required: comm/uniq outputs; browser screenshots of grouped palettes + nested open (executor-node verification).
- Tests to add/run: routes.ts invariant unit test (registry↔routes parity, unique keys, valid absorbedInto targets — becomes a CI gate); cockpit build; 3-pass browser validation.
- Rollback plan: revert routes/palette files — metadata is additive.
- Expected output: code change.
- Parallelizable: no (all P5 nesting packets build on this metadata)
- Requires human approval: yes
- Phase: P5

### WP-P5-004: One approval domain across the cockpit — single queue, single decide path
- Closes: GAP-F1-002, GAP-F2-001
- Current state: the approval concern is rendered by 11 surfaces (components/ControlPanel.tsx:274 APPROVALS section, ApprovalsPanel, CommandCenterPanel, CommandsPanel, ActionsPanel, DashboardPanel, UnifiedExecutionPanel approvals tab, ContinuityPanel approvals tab, WorkPanel overnight approve, EngineeringPanel, DelegationPanel) and OWNED by ≥9 stores each hitting a different backend approval family: unifiedApprovalStore (/unified-approval/*), organismStore (/organism/spine/approve|reject/{id}), operatorLoopStore (/operator-loop/approve*), proofInspectorStore, delegationStore, unifiedExecutionStore, engineeringStore, actionsStore, coherenceStore, plus a 10th cached copy in bootstrapStore (bootstrapStore.ts:37,170). An operator cannot know which surface is the state authority for pending decisions; a decision made in one surface is not guaranteed visible in others. This is permission-envelope integrity, not cosmetics.
- Desired state: `unifiedApprovalStore` is the only client owner of the pending-approval queue and the only module issuing decide mutations; every other surface renders read-only projections of it; backend families funnel through the unified-approval endpoints (server-side merge delivered by WP-P1-007 — this packet consumes it); bootstrapStore stops caching approvals as decidable state (ties into WP-P5-006).
- Files to inspect: cockpit/src/renderer/stores/unifiedApprovalStore.ts; stores/{organismStore,operatorLoopStore,proofInspectorStore,delegationStore,unifiedExecutionStore,engineeringStore,actionsStore,coherenceStore,bootstrapStore}.ts (approval slices); components/ControlPanel.tsx:260-340; the 11 panel files; transports/api/cockpit_unified_approval_routes.py.
- Files likely modified: the 9 stores (remove decide mutations, subscribe to unified store); the 11 surfaces (render from unified store); unifiedApprovalStore.ts (domain-complete model).
- Forbidden files/actions: layout lock; do not remove a decide path client-side before its backend family is merged server-side (sequencing with WP-P1-007); deploy gate.
- Dependencies: WP-P1-007 (server-side approval state authority), WP-P5-003 (surface metadata). Coordination (non-blocking): this packet is the pattern-setter for the domain-store layer — WP-P5-005 generalizes the pattern established here and depends on this packet, not the reverse.
- Risk class: HIGH (the approve/reject path is the operator's core governance control)
- Approval required: yes.
- Acceptance criteria: a decision made in any surface is immediately reflected in all others (single store — test by approving in ControlPanel and observing ApprovalsPanel); `grep -rn "approve" cockpit/src/renderer/stores | grep -v unifiedApprovalStore` shows no residual decide mutations; pending count consistent across HudBar/ControlPanel/panels.
- Proof required: cross-surface consistency browser capture; grep output.
- Tests to add/run: store unit tests (single-queue invariant); browser 3-pass on approve/reject flows.
- Rollback plan: stores revert to independent queues (git revert); backend unaffected.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P5

### WP-P5-005: Introduce the domain-store layer — retire per-panel stores, the god store, canvas-store septuplet, and panel-level fetch
- Closes: GAP-F1-005, GAP-F2-004, GAP-F2-012, GAP-F2-015
- Current state: one underlying defect — client state is organized per-panel, not per-domain: (a) 77 stores nearly 1:1 with 78 panels (`ls cockpit/src/renderer/stores | wc -l` = 77), same control-plane objects (work packets, approvals, nodes) fetched redundantly by multiple stores, cross-panel coherence impossible by construction; (b) operatorLoopStore is a 1553-line god store owning 7 backend route families for 7 panels; (c) 7 sibling canvas stores persist independent layout schemas (canvasStore, unifiedCanvasStore, agentCanvasStore, harnessCanvasStore, loopCanvasStore, organismCanvasStore, workflowCanvasStore); (d) 148 direct fetchApi call sites in 37 panels/components bypass the store layer entirely, including mutation POSTs (/agents/run, /command/submit, /mesh/dispatch, /comms/send, /broadcast/scene/switch, /presence/command) with no shared refresh/optimistic/error policy.
- Desired state: domain stores per control-plane object family (workPackets, approvals, runtimeNodes, traces, capabilities, realityModel, sessions) consumed by all panels of a surface; operatorLoopStore split along its 7 backend families with the approvals slice merged into the approval domain; one canvas-layout store parameterized by canvas mode; panels become pure views — all server I/O through stores (CI grep gate: no fetchApi outside stores/ and api/).
- Files to inspect: cockpit/src/renderer/stores/ (all 77 — start from the F2.2 inventory table); stores/operatorLoopStore.ts; the 7 canvas stores; grep output of fetchApi in components/+panels/ (37 files); cockpit/src/renderer/api/client.ts.
- Files likely modified: new stores/domain/*.ts; most existing stores (delegate or delete); the 37 direct-fetch panels/components; UnifiedCanvasWorkspace + canvas menu components (single layout store).
- Forbidden files/actions: layout lock (persisted canvas layouts must migrate losslessly — layout data is user state); no endpoint changes in this packet (client-side only); deploy gate; incremental migration must never leave a domain double-owned (old store deleted the same PR its consumers move).
- Dependencies: WP-P5-003 (surface mapping), WP-P5-004 (approval domain first, as the pattern-setter)
- Risk class: HIGH (touches nearly every panel's data path)
- Approval required: yes.
- Acceptance criteria: store count drops to domain+UI stores with zero same-entity double-owners (documented mapping table old→new); `grep -rn fetchApi cockpit/src/renderer/components cockpit/src/renderer/panels | wc -l` → 0; persisted canvas layouts survive migration (fixture localStorage → identical rendered layout); all panels function in a full browser pass.
- Proof required: grep counts before/after; old→new store mapping table; browser regression pass.
- Tests to add/run: domain-store unit tests; layout-migration test; full cockpit build + 3-pass browser validation.
- Rollback plan: staged by domain — each domain migration is an independent revertible commit.
- Expected output: code change.
- Parallelizable: no (after deps; internally staged by domain)
- Requires human approval: yes
- Phase: P5

### WP-P5-006: Client cache-invalidation, polling, and persistence policy
- Closes: GAP-F2-002, GAP-F2-010, GAP-F2-013
- Current state: one staleness posture defect in three expressions: (a) WS invalidation covers exactly 4 domains (settings/loops/approvals/execution — cockpit/src/renderer/hooks/useOrganismRealtime.ts:182-198, room/spine events :214-221); the other ~60 fetch-based stores have NO invalidation — data fetched on mount goes stale until manual refresh; (b) components/StorePolling.tsx polls 5 endpoints every 5s unconditionally regardless of visible panel, and WS-loss fallback doubles organismStore fetches (useOrganismRealtime.ts:49-73); (c) bootstrapStore persists server state (approvals, pulse, mesh nodes, file trees) to localStorage with no TTL and re-seeds stores on rehydrate before any network validation (bootstrapStore.ts:125-259) — a reopened client briefly treats its disk cache as state authority, rendering stale approvals as current.
- Desired state: one documented staleness policy: domain-keyed server-push invalidation extended across entity domains (mutation_event carries domain tags; client maps domain→store refetch), visibility-gated polling (poll only when a consumer surface is visible; one coordinator arbitrates poll vs push), and bootstrap rehydration marked stale-until-validated with a TTL — approval state never seeded from disk.
- Files to inspect: cockpit/src/renderer/hooks/useOrganismRealtime.ts; cockpit/src/renderer/components/StorePolling.tsx; cockpit/src/renderer/stores/bootstrapStore.ts; transports/api side of mutation_event emission (organism WS) for domain tagging.
- Files likely modified: useOrganismRealtime.ts; StorePolling.tsx; bootstrapStore.ts; the WS event emitter (domain tags); domain stores from WP-P5-005 (invalidation hooks).
- Forbidden files/actions: layout lock; do not increase unconditional background load (the defect being fixed); deploy gate; approvals must fail to a fetch, never to cache.
- Dependencies: WP-P5-005 (domain stores are the invalidation targets)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: a backend mutation in any tagged domain refreshes its store without manual reload (test per domain); network tab shows zero polling for hidden surfaces; reopened client shows a stale badge (or refetch spinner) instead of stale approvals; steady-state request rate measurably below current 5-endpoint×5s baseline.
- Proof required: before/after request-rate capture; stale-rehydrate browser capture.
- Tests to add/run: invalidation-map unit test; bootstrap rehydrate test (stale flag).
- Rollback plan: revert three files; prior polling restored.
- Expected output: code change.
- Parallelizable: yes (after 038)
- Requires human approval: no
- Phase: P5

### WP-P5-007: Consolidate the work-packet/execution concern into one Operations anchor
- Closes: GAP-F1-003
- Current state: 12 panels render running-work state over ≥3 endpoint families with no single source of truth for "what is running": WorkPanel (/command-center/work-packets), UniversalWorkPanel (/organism/universal-work/packets — a second work-packet browser on a different family), TasksPanel (orphan), OperationsPanel, ExecutionPanel, UnifiedExecutionPanel, ExecCoordPanel, ExecutorPanel (1016L), WorkIntelligencePanel (orphan), DelegationPanel, RecoveryDashboardPanel, ActionsPanel (all under cockpit/src/renderer/panels/).
- Desired state: WorkPanel is the Operations anchor with tabs queue/executors/plans/delegation/recovery backed by the workPackets domain store; UniversalWork/Tasks/WorkIntelligence become tabs; ExecCoord+Executor merge into one execution-plan view; the two work-packet endpoint families reconciled server-side is tracked in PART1 (spine unification) — client renders one merged model meanwhile with source annotations.
- Files to inspect: the 12 panel files; stores/{operatorLoopStore,unifiedExecutionStore,operationsStore,workIntelligenceStore,taskStore,delegationStore,recoveryDashboardStore}.ts; types/routes.ts (absorbedInto rows).
- Files likely modified: WorkPanel.tsx (tab host); the 11 absorbed panels (content extraction into tabs); routes.ts metadata.
- Forbidden files/actions: layout lock; no deletion of RecoveryDashboardPanel content (MVP-critical M1 G11); deploy gate.
- Dependencies: WP-P5-003, WP-P5-005
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: one route ("work") reaches every work/execution view as tabs; the 11 non-anchor routes carry absorbedInto metadata and open inside the anchor; work-packet lists in any two tabs agree (single store assertion).
- Proof required: browser walkthrough capture of all tabs; store-consistency assertion.
- Tests to add/run: cockpit build; browser 3-pass on Operations flows.
- Rollback plan: routes metadata revert re-exposes standalone panels (components retained).
- Expected output: code change.
- Parallelizable: yes (after deps)
- Requires human approval: no
- Phase: P5

### WP-P5-008: Consolidate the strategy concern (Goal/Strategy/Strategic/Executive) into one Command view
- Closes: GAP-F1-006
- Current state: four panels + IntentPanel overlap on the strategy concern with overlapping tabs (drift/recommendations/priorities): GoalPanel (451L), StrategyPanel (593L — routes.ts:102 claims "Absorbed into Command Center" yet it persists), StrategicPanel (417L), ExecutivePanel (233L, orphan — no route); each with its own store (goalStore, strategicStore, executiveStore).
- Desired state: one strategy view nested in the Command surface with tabs goals/priorities/allocations/drift/recommendations; ExecutivePanel content merged as tabs; the four stores collapse into one strategy domain store (or slices of it).
- Files to inspect: panels/{GoalPanel,StrategyPanel,StrategicPanel,ExecutivePanel,IntentPanel}.tsx; stores/{goalStore,strategicStore,executiveStore,intentStore}.ts; types/routes.ts:100-105.
- Files likely modified: one consolidated strategy panel (anchor); routes.ts; the four stores.
- Forbidden files/actions: layout lock; deploy gate; keep IntentPanel distinct (intent capture is Command-anchor territory, not strategy tabs).
- Dependencies: WP-P5-003, WP-P5-005
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: one strategy route; ExecutivePanel reachable as a tab (orphan resolved jointly with WP-P5-003); no duplicate drift/recommendation renderings from separate stores.
- Proof required: browser capture of the merged view.
- Tests to add/run: cockpit build; browser pass.
- Rollback plan: metadata revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-009: Consolidate session/continuity/resume into one Operations continuity view
- Closes: GAP-F1-007
- Current state: 8 surfaces render checkpoint/resume/session state via ≥4 stores + raw fetch: ContinuityPanel (376L, operatorLoopStore), OperatorContinuityPanel (248L, presenceStore), SessionPanel (417L, raw fetch — fixed for auth by WP-P0-012), SessionResumePanel (workstationSessionStore), WorkstationPanel (routes.ts:110 "Absorbed into Meta IDE" yet persists), DashboardPanel (checkpoint/resume), CommandCenterPanel (checkpoint chip), RecoveryDashboardPanel.
- Desired state: one continuity view in Operations (tabs: sessions, checkpoints, resume, presence-continuity) backed by a sessions domain store; CommandCenterPanel keeps only a checkpoint summary chip; WorkstationPanel's prepare/snapshot content absorbed into Meta IDE as its comment claims.
- Files to inspect: the 8 panel files; stores/{operatorLoopStore,presenceStore,workstationSessionStore}.ts; types/routes.ts:108-112.
- Files likely modified: consolidated continuity view; routes.ts; the session-related stores (fold into sessions domain store).
- Forbidden files/actions: layout lock; deploy gate; RecoveryDashboard content preserved (MVP-critical).
- Dependencies: WP-P5-003, WP-P5-005, WP-P0-012
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: one continuity route; checkpoint state identical between the Command chip and the continuity view (single store); WorkstationPanel route carries absorbedInto → editor (Meta IDE).
- Proof required: browser capture; store-consistency assertion.
- Tests to add/run: cockpit build; browser pass on checkpoint/pause/resume flows.
- Rollback plan: metadata revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-010: One runtime-node topology view; one client node-entity model
- Closes: GAP-F1-008, GAP-F2-008
- Current state: (a) 8 panels render runtime-node/mesh state independently: InfrastructurePanel (routes.ts:112 "Absorbed into Organism Map" yet persists), UMHNodePanel, DistributedRuntimePanel (most complete: topology/devices/workers/capacity/assignments), RuntimePanel, ServiceGraphPanel, WorkspaceTopologyPanel, OrganismMapPanel, DashboardPanel. (b) The node entity is split across 5 stores and two route families: deviceStore (/devices/* — cockpit_device_routes.py), deviceSessionStore (/device/* singular — cockpit_core_session_routes.py), umhNodeStore (/umh-nodes), systemStore.meshNodes (/mesh/nodes), metaIDEStore.fileMeshNodes (seeded from bootstrap — bootstrapStore.ts:88-98).
- Desired state: DistributedRuntimePanel becomes the topology anchor (others as tabs/overlays); one runtimeNodes domain store models the node entity with session presence as a sub-resource; the /device vs /devices route-family split is annotated for the server-side merge under WP-P2-010 (client consumes one model now).
- Files to inspect: the 8 panel files; stores/{deviceStore,umhNodeStore,systemStore,bootstrapStore,metaIDEStore}.ts; cockpit/src/renderer/api/device-presence.ts; cockpit/src/renderer/constants/devices.ts.
- Files likely modified: DistributedRuntimePanel.tsx (anchor); new runtimeNodes domain store; the 5 stores (delegate); routes.ts metadata.
- Forbidden files/actions: device display names only via constants/devices.ts / registry API (device-naming rule); layout lock; deploy gate.
- Dependencies: WP-P5-003, WP-P5-005; WP-P2-010 for the server-side entity merge (client packet does not block on it)
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: node lists identical across all topology tabs (single store); device-session presence renders as a node sub-resource; one topology route reaches all 8 views.
- Proof required: browser capture; store-consistency assertion.
- Tests to add/run: cockpit build; browser pass incl. device onboarding card flow.
- Rollback plan: metadata revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-011: One trace-event stream in Proof with source filters
- Closes: GAP-F1-009
- Current state: the timeline/trace-event concern is rendered by 6 surfaces with no canonical stream: ActivityPanel (activityStore), OperatorTimelinePanel (operatorTimelineStore), RealityTimelinePanel (routes.ts:120 says "Absorbed into Activity" but both persist as separate routes/stores), plus timeline tabs inside ContinuityPanel, PresencePanel, CommandsPanel.
- Desired state: one trace-event stream view under Proof (ActivityPanel as anchor) with source filters (execution/governance/observation/memory_write/presence/command); the other surfaces become filter presets or embed the shared stream component; one traces domain store.
- Files to inspect: panels/{ActivityPanel,OperatorTimelinePanel,RealityTimelinePanel}.tsx; timeline tabs in ContinuityPanel/PresencePanel/CommandsPanel; stores/{activityStore,operatorTimelineStore,realityTimelineStore}.ts.
- Files likely modified: ActivityPanel.tsx (filterable anchor); shared timeline component; the three stores → traces domain store; routes.ts metadata.
- Forbidden files/actions: layout lock; deploy gate.
- Dependencies: WP-P5-003, WP-P5-005
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: the same event visible in any two timeline surfaces is the same object (id match, single store); filter presets reproduce each retired panel's former view.
- Proof required: browser capture with matching event ids across presets.
- Tests to add/run: traces store unit test; cockpit build; browser pass.
- Rollback plan: metadata revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-012: One capability-registry view
- Closes: GAP-F1-010
- Current state: the capability-registry concern is split across 4 surfaces including 2 orphans: CapabilityMapPanel (routed — snapshot/surfaces/gaps/duplications), CapabilitiesPanel (orphan — portfolio/gaps/graph/compounding), SkillsPanel (orphan, 47 lines), KnowledgePanel (skills via knowledgeStore).
- Desired state: CapabilityMapPanel is the Capability-surface anchor; portfolio/graph/compounding and skills become tabs; capabilityIntelligenceStore + the knowledgeStore skills slice merge into a capabilities domain store.
- Files to inspect: panels/{CapabilityMapPanel,CapabilitiesPanel,SkillsPanel,KnowledgePanel}.tsx; stores/{capabilityMapStore,capabilityIntelligenceStore,knowledgeStore}.ts.
- Files likely modified: CapabilityMapPanel.tsx; the three stores; routes.ts metadata.
- Forbidden files/actions: layout lock; deploy gate.
- Dependencies: WP-P5-003, WP-P5-005
- Risk class: MEDIUM
- Approval required: no
- Acceptance criteria: one capability route reaches all four views as tabs; orphans resolved (jointly with 036); skill list identical between the skills tab and KnowledgePanel (single source).
- Proof required: browser capture.
- Tests to add/run: cockpit build; browser pass.
- Rollback plan: metadata revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-013: Merge forecast panels and reserve the "Projection" name for L3 projections
- Closes: GAP-F1-011
- Current state: `cockpit/src/renderer/panels/ProjectionPanel.tsx` renders forecasts (horizons 24h/7d/30d/90d, trends/risks/accuracy), duplicating the orphaned PredictionPanel, while the actual projection registry lives in ProjectionIntegrationPanel.tsx. The route label "Projections" (routes.ts:105) collides with the platform term for L3 projections and misleads operators about projection state.
- Desired state: PredictionPanel + ProjectionPanel merged into one "Forecasts" view (Reality surface); the "Projections" label/route reserved for ProjectionIntegrationPanel (Capability surface, projection inheritance registry).
- Files to inspect: panels/{ProjectionPanel,PredictionPanel,ProjectionIntegrationPanel}.tsx; stores/{predictionStore,projectionIntegrationStore}.ts; operatorLoopStore /projection/* slice; types/routes.ts:105.
- Files likely modified: merged Forecasts panel; routes.ts (rename + re-point); the two forecast stores → one.
- Forbidden files/actions: layout lock; deploy gate; the /projection/* backend paths are not renamed here (server naming tracked separately) — client labels only.
- Dependencies: WP-P5-003
- Risk class: LOW (rename + merge of dev-visibility panels)
- Approval required: no
- Acceptance criteria: no route labeled "Projections" renders forecasts; searching the palette for "projection" surfaces the registry view; forecast content fully reachable under "Forecasts".
- Proof required: palette screenshot.
- Tests to add/run: cockpit build; routes invariant test.
- Rollback plan: revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-014: LoopCanvasWorkspace as the single loop surface
- Closes: GAP-F1-014
- Current state: the loop concern is reachable via two mechanisms: TickLoopPanel, OperatingLoopPanel, OrganismLoopPanel, BuildLoopPanel exist as separate routes AND are re-imported wholesale by components/canvas/LoopCanvasWorkspace.tsx:16-19 — the same UI mounted through two paths.
- Desired state: LoopCanvasWorkspace is the single loop surface (Operations); the four individual loop routes retire to nested tabs (absorbedInto metadata); loop stores fold into the domain layer per WP-P5-005.
- Files to inspect: components/canvas/LoopCanvasWorkspace.tsx; panels/{TickLoopPanel,OperatingLoopPanel,OrganismLoopPanel,BuildLoopPanel}.tsx; stores/{operatorLoopStore (tick slice),operatingLoopStore,organismLoopStore,buildLoopStore}.ts; types/routes.ts loop entries.
- Files likely modified: routes.ts; LoopCanvasWorkspace.tsx (tab hosting).
- Forbidden files/actions: layout lock; deploy gate.
- Dependencies: WP-P5-003, WP-P5-005
- Risk class: LOW
- Approval required: no
- Acceptance criteria: one loop entry point; the four loop views render inside it; no duplicate mounting path remains (grep for the four panel imports outside the workspace → routes-only shims).
- Proof required: browser capture; grep output.
- Tests to add/run: cockpit build; browser pass on loop start/stop/dry-run.
- Rollback plan: metadata revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-015: Generated cockpit route/store registry + disposition of the dormant dev surface
- Closes: GAP-E2-013, GAP-F2-014
- Current state: (a) the backend has 121 route-satellite files with 324 include/mount lines in transports/api/cockpit.py (1571L) and no machine-readable inventory mapping route file → substrate authority → auth requirement; (b) the client mirrors this sprawl: ~40 stores + their route modules serve only dev-visibility panels (~60 dev routes reachable via CommandPalette only; ~1250 backend endpoint registrations vs 551 store call sites) — a dormant surface with no PROMOTE/MERGE/ARCHIVE disposition.
- Desired state: a generated registry artifact (script + JSON output, CI-refreshed) enumerating every cockpit route module, its prefix(es), mounted-or-not, governed_mutation usage, auth dependency, and consuming store/panel; using it, every dev-visibility store/panel/route triple gets a recorded disposition (PROMOTE into one of the five surfaces / MERGE into an anchor / ARCHIVE), and ARCHIVE decisions are executed (routes unmounted, stores removed) shrinking the 119-file cockpit_*.py surface.
- Files to inspect: transports/api/cockpit.py; `ls transports/api/cockpit_*` (119 files); cockpit/src/renderer/types/routes.ts; the F2.2 store inventory (77 rows) as the seed mapping.
- Files likely modified: new scripts/generate_cockpit_route_registry.py; new data/umh/cockpit_route_registry.json (generated); cockpit.py (unmounts per disposition); archived route files + stores per decisions.
- Forbidden files/actions: never remove a working feature without CRITICAL-class review (removals are the operator's call — the disposition record IS the approval artifact); dormant-classification protocol for every archive; deploy gate; keep the generator deterministic (no LLM).
- Dependencies: WP-P5-003 (surface taxonomy), WP-P5-005 (store consolidation supplies MERGE targets)
- Risk class: MEDIUM (registry LOW; unmounting routes MEDIUM; feature removal escalates to CRITICAL per item)
- Approval required: yes — dispositions remove reachable functionality.
- Acceptance criteria: registry row count equals `find transports/api -name 'cockpit_*.py' | wc -l`; every dev route id has a disposition row; executed ARCHIVEs leave the build green and the browser pass clean; registry regeneration is idempotent in CI.
- Proof required: registry file + count parity; disposition table; post-archive test/browser run.
- Tests to add/run: registry-generator unit test; full cockpit build; API smoke tests on remaining routes.
- Rollback plan: unmounts are single-line reverts; archived files restored from git.
- Expected output: code change + generated registry artifact + disposition record.
- Parallelizable: no
- Requires human approval: yes
- Phase: P5

### WP-P5-016: Fix the Electron production API/WS binding
- Closes: GAP-F2-005
- Current state: Electron production loads `loadFile(join(__dirname, '../renderer/index.html'))` (cockpit/src/main/index.ts:51) → `file://` origin; `API_BASE` defaults to relative `/api/umh` (cockpit/src/renderer/api/client.ts:1) which resolves to `file:///api/umh` (broken); all WS URLs derive from `window.location.host` (useOrganismRealtime.ts:25, voice-ws.ts:21, vision-ws.ts:16, broadcast-ws.ts:17) → empty host; `cockpit/electron.vite.config.ts` sets no VITE_API_URL default and no in-repo injection point exists. The Electron production surface is non-functional against the API (UNVERIFIED whether an out-of-repo build script compensates; in-repo evidence says broken).
- Desired state: Electron either injects an absolute API/WS base at build time (single canonical domain, sourced from config — not hardcoded, per instance-context law) or loads the hosted web app like Capacitor does (capacitor.config.ts precedent: server.url → hosted bundle). One documented decision, implemented and verified on a packaged build.
- Files to inspect: cockpit/src/main/index.ts:40-60; cockpit/electron.vite.config.ts; cockpit/src/renderer/api/client.ts:1-30; cockpit/capacitor.config.ts (remote-shell precedent); ARCHITECTURE.md §9 distribution surfaces.
- Files likely modified: cockpit/electron.vite.config.ts or cockpit/src/main/index.ts (loadURL variant); possibly api/client.ts (env override honored at runtime).
- Forbidden files/actions: no hardcoded production domain in source (instance-context law — config/env only); deploy gate for any web-side change; single-domain rule (universalmetaharness.tech is instance config, not code).
- Dependencies: none (WP-P0-014 forwarding variant depends on this)
- Risk class: MEDIUM (distribution build config)
- Approval required: no
- Acceptance criteria: a packaged Electron build performs an authenticated API call and opens the organism WS successfully (network log); no `file:///api` requests observed.
- Proof required: packaged-build network capture from an executor node.
- Tests to add/run: electron build in CI; manual E2E on the executor node.
- Rollback plan: revert config; Electron returns to (already broken) prior state — zero regression risk.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-017: Harden push notifications — durable subscription store, unified registration, startup health, delivery proof
- Closes: GAP-E2-010, GAP-F2-017
- Current state: (a) `transports/api/cockpit_push_routes.py:29-35` treats pywebpush as an optional import that downgrades to `logger.debug` and silently disables ALL push; no delivery acceptance test exists; VAPID key presence unverified at startup. (b) Two parallel registration paths — native (cockpit/src/renderer/capacitor-init.ts:16-32 → POST /push/register) and web (cockpit/src/renderer/lib/pushNotifications.ts:25-28 → /push/subscribe) — persist to `data/push_subscriptions.json` (runtime artifact, path per cockpit_push_routes.py:24; not committed): file-based, no durable store, no tenancy.
- Desired state: one push-registration model keyed by operator+device in the platform DB (native and web paths converge on it); startup health check surfaces push availability (pywebpush present, VAPID keys valid) into the operational-truth snapshot instead of a debug log; a delivery acceptance test proves an end-to-end notification on at least one real device.
- Files to inspect: transports/api/cockpit_push_routes.py (228L, full); cockpit/src/renderer/lib/pushNotifications.ts; cockpit/src/renderer/capacitor-init.ts; cockpit/src/renderer/sw.ts:15-45; transports/api/http/db/schema.ts (table conventions).
- Files likely modified: cockpit_push_routes.py; new platform DB table (push_subscriptions); pushNotifications.ts + capacitor-init.ts (unified payload); scripts/generate_vapid_keys.py check integration.
- Forbidden files/actions: VAPID private key via 1Password/env only (credential-injection law); JSON-file migration with count parity (CRITICAL data-move discipline, small but real); silent-disable pattern removed — absence of pywebpush must surface loudly.
- Dependencies: WP-P4-012 (engine fan-out consumes this registry) — soft
- Risk class: MEDIUM (+ CRITICAL element: subscription data move)
- Approval required: yes — schema addition.
- Acceptance criteria: registrations from web and native land in one table with operator+device keys; JSON→DB migration count parity; startup health endpoint reports push status; one real-device delivery captured.
- Proof required: migration counts; health snapshot; device screenshot/log of a delivered test notification.
- Tests to add/run: new tests/test_push_registry.py; delivery acceptance run.
- Rollback plan: routes flag-guarded to fall back to the JSON file (retained until parity verified).
- Expected output: code change + schema migration.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P5

### WP-P5-018: Remove instance-context literals from shipped cockpit artifacts (sw.ts domain, devices.ts fleet)
- Closes: GAP-F2-016
- Current state: `cockpit/src/renderer/sw.ts:38` hardcodes `c.url.includes('universalmetaharness.tech')` in the notificationclick handler — a single-domain assumption baked into a platform artifact; `cockpit/src/renderer/constants/devices.ts:20-57` embeds the operator's personal 5-device fleet in the shipped bundle. Both violate the Instance Context Law for a multi-tenant platform artifact (the device-naming rule's intent is a registry-driven constants file, not a hardcoded fleet).
- Desired state: service worker derives the app origin from its registration scope (`self.registration.scope`), no domain literal; devices.ts becomes a thin typed accessor over the `/workspace/mesh-nodes` API (or a build-time injection from infra/device_registry.json), with no per-device literals in the platform bundle.
- Files to inspect: cockpit/src/renderer/sw.ts; cockpit/src/renderer/constants/devices.ts; infra/device_registry.json; consumers of devices.ts (grep VPS./BEAST. imports).
- Files likely modified: sw.ts; constants/devices.ts; its consumers.
- Forbidden files/actions: device-naming protocol still applies — display names come from the registry, never re-hardcoded at call sites; deploy gate; layout lock.
- Dependencies: WP-P5-010 (runtimeNodes domain store is the natural data source)
- Risk class: LOW/MEDIUM (SW click-through behavior + device labels)
- Approval required: no
- Acceptance criteria: `grep -rn "universalmetaharness" cockpit/src/` → only config/env references, zero in shipped source; `grep -n "srv1500858\|Beast" cockpit/src/renderer/constants/devices.ts` → zero literals (registry-driven); notification click still focuses/opens the app on the deployed domain.
- Proof required: grep outputs; notification-click browser capture.
- Tests to add/run: cockpit build; SW behavior manual check.
- Rollback plan: revert two files.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P5

### WP-P5-019: Align CLI operator identity with the platform identity model
- Closes: GAP-F2-018
- Current state: the CLI surface authenticates with an API key (env / `~/.umh/config.json` — ARCHITECTURE.md:405-411) while every visual surface uses Clerk (ARCHITECTURE.md:436) — an asymmetric trust boundary: two credential classes grant the same operator powers with different lifecycle, revocation, and audit properties.
- Desired state: one operator identity model across surfaces: the CLI performs a device-token exchange for a Clerk-verified session (device-flow precedent exists in services/oauth_device_flow.py), or API keys are formally scoped/audited as machine identities distinct from operator identity — decided and documented; trace events from CLI actions carry the same operator identity as cockpit actions.
- Files to inspect: transports/cli/ (auth module); services/oauth_device_flow.py; ARCHITECTURE.md:400-440; transports/api auth middleware (require_clerk_auth path in transports/api/cockpit.py:168).
- Files likely modified: transports/cli auth module; possibly a token-exchange endpoint.
- Forbidden files/actions: no plaintext keys in code (credential-injection law); do not break the existing CLI during migration (dual-accept window, then retire).
- Dependencies: WP-P3-011 (operator identity authority) — soft
- Risk class: MEDIUM (auth path change on a working surface)
- Approval required: yes — auth model change.
- Acceptance criteria: a CLI action and a cockpit action by the same operator produce trace events with the same operator identity; revoked session blocks both; legacy API-key path retired or documented as machine identity.
- Proof required: trace-event pair; revocation test log.
- Tests to add/run: CLI auth integration test.
- Rollback plan: dual-accept flag revert.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P5

---

## P6 — Test / certification hardening (24 packets)

**Objective.** Make the guarantees mechanical: CI, marker taxonomy, contract tests for the trust boundaries, honest certification suites, full-scan enforcement sweeps, and the residual hygiene/tooling packets (credential gate, SSH pinning, instance leaks, doc-truth reconciliation).

**Entry criteria.** Test-infrastructure packets (WP-P6-001…004) can start as soon as WP-P0-011 lands and run in parallel with P2-P5; enforcement sweeps (WP-P6-014) require the P2/P3 gates to be green first.

**Exit criteria.** CI executes the suite on every push; all check_*.py gates pass with --all; certification is repeatable and environment-gated; no stale doc contradicts observed deployment reality.

### WP-P6-001: Centralize test sys.path setup; eliminate hardcoded and dead path pins

- Closes: GAP-H-003
- Current state: 29 tests pin deleted worktree sys.paths — `remaining-phases` (13), `c4-6-cockpit-finalization` (10), `c20-voice-operations` (6), none exist; 155 files insert `/opt/OS` at index 0, so tests executed in a worktree silently import main-repo modules (shadowing hazard documented in tests/test_convergence_acceptance.py:8-16; examples tests/test_trust_score.py:12, tests/test_goal_alignment_engine.py:10, tests/test_c20_0_voice_ingress.py:9, tests/test_p0_smoke.py:17).
- Desired state: single conftest-level path setup relative to `Path(__file__).parents[1]` / UMH_ROOT; zero per-file hardcoded inserts; a gate preventing new ones.
- Files to inspect: tests/conftest.py, the 184 offending files (scripted inventory)
- Files likely modified: tests/conftest.py, ~184 test files (mechanical removal), a lint gate script
- Forbidden files/actions: mechanical edit only — no assertion changes ride along; verify collected-test count identical before/after (ground truth from `pytest --collect-only -q | tail`).
- Dependencies: WP-P0-011
- Risk class: MEDIUM (broad mechanical edit across the suite)
- Approval required: no
- Acceptance criteria: `grep -rln "sys.path.insert" tests/ | wc -l` = 0 outside conftest; collected count unchanged; a worktree run imports worktree modules (asserted via `__file__` prefix check test).
- Proof required: grep counts before/after; collect-only counts; worktree-import assertion output.
- Tests to add/run: new tests/test_path_hygiene.py; full collect-only.
- Rollback plan: git revert (single mechanical commit).
- Expected output: environment-correct test suite.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-002: Fix the C20 voice-test hardcoded worktree paths
- Closes: GAP-E2-008
- Current state: all 6 C20 test files insert a deleted worktree into sys.path — `sys.path.insert(0, "/opt/OS/.claude/worktrees/c20-voice-operations")` (verified: tests/test_c20_0_voice_ingress.py:9, test_c20_1_voice_session_manager.py:9, test_c20_2_ambient_wake.py:7, test_c20_3_voice_output.py:6, test_c20_4_voice_operations.py:7, test_c20_integration.py:7; the worktree is absent). Tests resolve imports only by accident of cwd-relative resolution; also an absolute-path instance leak in tests.
- Desired state: relative/repo-root path insertion (the C21 tests' pattern) in all 6 files; suites collected and passing from a clean checkout; CI-run proof on main.
- Files to inspect: the 6 tests/test_c20_*.py files; tests/test_c21_0_screen_awareness_runtime.py (correct pattern).
- Files likely modified: the 6 test files.
- Forbidden files/actions: no hardcoded /opt/OS paths (use repo-root derivation); do not weaken assertions to make them pass.
- Dependencies: none (feeds WP-P2-027 acceptance)
- Risk class: LOW (test-infra fix)
- Approval required: no
- Acceptance criteria: `grep -rn "c20-voice-operations" tests/` → zero; `pytest tests/test_c20_*.py` collects and runs from an arbitrary cwd.
- Proof required: grep + pytest outputs.
- Tests to add/run: the 6 suites.
- Rollback plan: git revert.
- Expected output: code change (tests only).
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-003: Test-suite marker taxonomy and retired-campaign triage

- Closes: GAP-H-008
- Current state: ~120 retired-campaign test files (46 campaign-suite C16-C40, 28 P-runner, 46 phase-cluster) pin retired scaffolding with no marker separating living platform-contract tests from legacy regression pins (pyproject.toml markers = integration + smoke only); 3 break collection (handled by WP-P0-011), 4 import deleted scripts (e.g. tests/test_c39_live_simulation.py:221, tests/test_c40a_runtime_convergence.py:30).
- Desired state: marker taxonomy (`contract`, `legacy_campaign`, `integration`, `smoke`) applied across the suite; retired suites promoted to contract tests or archived per dormant protocol; the 4 deleted-script importers fixed or removed; CI selects by marker.
- Files to inspect: pyproject.toml, the ~120 campaign/phase test files (scripted inventory; ledger H clusters sum to 377 ground truth)
- Files likely modified: pyproject.toml (markers), ~120 test files (marker lines), archive moves
- Forbidden files/actions: classification before deletion; marker edits must not change assertions; totals must reconcile — every one of the 377 test files lands in exactly one marker class, verified by count.
- Dependencies: WP-P0-011
- Risk class: LOW (metadata + archival)
- Approval required: no
- Acceptance criteria: `pytest -m contract --collect-only` and `-m legacy_campaign` partition cleanly; unmarked-file gate = 0; classification table sums to ground-truth file count.
- Proof required: partition counts vs `find tests -name "test_*.py" | wc -l`.
- Tests to add/run: collect-only per marker.
- Rollback plan: git revert.
- Expected output: navigable, selectable suite taxonomy.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-004: CI pipeline executing the test suite

- Closes: GAP-H-004
- Current state: no CI executes tests — `.github/workflows/` contains only mobile-build.yml; the 15k-test suite is manual-only, which is how the broken collection (GAP-H-001) shipped unnoticed.
- Desired state: CI job running at minimum `pytest -m smoke` + `pytest --collect-only` on every push; nightly full run with `--continue-on-collection-errors` reporting; results visible per commit.
- Files to inspect: .github/workflows/mobile-build.yml (conventions), pyproject.toml [tool.pytest.ini_options], tests/conftest.py (env needs — Neon/env-gated tests must skip cleanly in CI)
- Files likely modified: new .github/workflows/tests.yml
- Forbidden files/actions: no secrets in workflow files (env-gated integration tests skip in CI; credential-injection law); CI must not run environment-coupled certification scripts (c28/c29 — see WP-P6-012); no cockpit deploys from CI.
- Dependencies: WP-P0-011, WP-P6-001, WP-P6-003 (marker taxonomy defines the smoke/contract set)
- Risk class: LOW (new workflow file)
- Approval required: no
- Acceptance criteria: a push triggers the workflow; smoke + collect-only green; a seeded failing smoke test turns the check red; nightly schedule present.
- Proof required: two workflow-run links/logs (green, and red on seeded failure).
- Tests to add/run: the pipeline itself.
- Rollback plan: delete the workflow file.
- Expected output: continuous certification gate.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-005: Governed-mutation compliance acceptance test

- Closes: GAP-H-002
- Current state: the constraint "All state changes through governed_mutation()" (CLAUDE.md) has no enforcing test: governed_mutation() (transports/api/governed.py:65) is covered only by a signature check (tests/test_p1_phase2_bridge.py:266-273); no AST scan asserts that route handlers/services call it.
- Desired state: an architecture-law test in the style of tests/test_p1_phase9_architecture.py that statically verifies every mutation call site routes through governed_mutation()/GovernedExecutionSpine, with an explicit, reviewed allowlist for exceptions.
- Files to inspect: tests/test_p1_phase9_architecture.py (pattern), transports/api/governed.py, transports/api routes, services/
- Files likely modified: new tests/test_governed_mutation_compliance.py
- Forbidden files/actions: the allowlist starts from measured reality (violations become gap records, not silent exemptions); test must run under worktree paths (WP-P6-001 conventions).
- Dependencies: WP-P0-001 (choke point in final location), WP-P0-011
- Risk class: LOW (new test file)
- Approval required: no
- Acceptance criteria: test fails when a synthetic ungoverned mutation call site is introduced; passes on the converged tree; allowlist entries each cite a gap/packet ID.
- Proof required: red/green demonstration transcript.
- Tests to add/run: the new test; run in CI set.
- Rollback plan: git revert.
- Expected output: enforced mutation-law gate.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-006: Projection inheritance acceptance tests

- Closes: GAP-H-005
- Current state: zero test files mention inheritance; projection coverage is limited to registration/consumption (tests/test_gate10_projection_consumption.py) and EOS agent registration (tests/test_eos_projection.py) — nothing proves projection domain models inherit/override platform metamodel contracts without divergence.
- Desired state: acceptance tests proving L3 domain models correctly extend L2 metamodel contracts: EOS/CreatorOS/LyfeOS parity fixtures registering through the unified port, inheriting entity_types, and failing on contract divergence.
- Files to inspect: tests/test_gate10_projection_consumption.py, tests/test_eos_projection.py, the unified projection port (WP-P3-004), projections/eos/entities.py
- Files likely modified: new tests/test_projection_inheritance.py + fixtures
- Forbidden files/actions: fixtures use synthetic projections plus EOS — no live-DB dependency; no product literals leak into substrate while writing fixtures.
- Dependencies: WP-P3-004, WP-P3-005
- Risk class: LOW
- Approval required: no
- Acceptance criteria: test fails when a fixture projection redefines a metamodel field incompatibly; passes for compliant EOS registration; runs in CI.
- Proof required: red/green transcript.
- Tests to add/run: the new suite.
- Rollback plan: git revert.
- Expected output: projection-inheritance gate.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-007: Node-trust and permission-envelope tests for mesh dispatch

- Closes: GAP-H-006
- Current state: no PermissionEnvelope tests exist anywhere (grep = 0); tests/test_trust_score.py covers work-claim scoring only; tests/test_mesh_dispatch_contract.py:21-45 verifies an in-test `_simulate_chain` rather than the real transport; tests/test_node_mesh.py does not cover trust registration.
- Desired state: acceptance tests for node registration trust, capability permission envelopes at the mesh trust boundary, and dispatch-path serialization exercised against the real relay code path (in-process, not simulated re-implementation).
- Files to inspect: tests/test_mesh_dispatch_contract.py, tests/test_node_mesh.py, tests/test_trust_score.py, the mesh dispatch relay implementation (transports/node mesh modules), WP-P2-014 permission envelope
- Files likely modified: new tests/test_node_trust_boundary.py; test_mesh_dispatch_contract.py (replace simulation with real code path)
- Forbidden files/actions: mesh WS :8094 is a host process — tests must not require or restart it (in-process invocation of the real dispatch functions); no live Beast SSH in unit tier; browser-verification law untouched (no orchestrator-side GUI checks).
- Dependencies: WP-P2-014 (envelope vocabulary), WP-P2-010 (node identity)
- Risk class: LOW (test files; one test rewrite)
- Approval required: no
- Acceptance criteria: an unauthorized-capability dispatch is rejected in test; serialization round-trips through the real relay functions; simulation helper deleted.
- Proof required: pytest transcript; diff showing _simulate_chain removed.
- Tests to add/run: the new suite + rewritten contract test.
- Rollback plan: git revert.
- Expected output: tested mesh trust boundary.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-008: HTTP-level contract tests for cockpit/API surface routes

- Closes: GAP-H-007
- Current state: cockpit surface tests assert route names and counts only — e.g. tests/test_governance_routes.py:27-40 checks path strings and `len(router.routes) == 7`; tests/test_cockpit_endpoints.py similar; no response schemas, status codes, or auth-middleware assertions; the real certification (tests/certification/c28_certification.py) requires live prod + Beast SSH.
- Desired state: TestClient-based contract tests validating response schema, status codes, and auth behavior (401 without key) per route; a CI-runnable subset of the c28 checks.
- Files to inspect: tests/test_governance_routes.py, tests/test_cockpit_endpoints.py, the route modules under transports/api/http/routes/ and services/operator_api.py
- Files likely modified: rewrite/extend the two test files; new contract-test module
- Forbidden files/actions: no cockpit deploy in this packet (cockpit deploy gate `bash cockpit/deploy.sh` only, and not needed for TestClient tests); no live prod URL dependencies in the CI tier; no plaintext credentials in fixtures.
- Dependencies: WP-P0-011, WP-P6-001
- Risk class: LOW
- Approval required: no
- Acceptance criteria: every asserted route has schema + status + auth assertions; a route response-shape change breaks the test; suite runs without network access.
- Proof required: red/green transcript on a seeded shape change.
- Tests to add/run: the rewritten suites.
- Rollback plan: git revert.
- Expected output: real API contract coverage.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-009: Make canon certification suites fail loudly instead of mass-skipping

- Closes: GAP-H-009
- Current state: the phase14_6b canon "certification" suites pass by mass skip when artifacts are absent: tests/test_phase14_6b_creatoros_lossless_canon.py:210+ skips per-artifact (`pytest.skip(f"{name} not on disk")` ×94) and tests/test_phase14_6b_eos_lossless_canon.py:24 hardcodes an absolute CANON_DIR under /opt/OS with 61 skip sites — certification that certifies nothing when the artifacts are missing.
- Desired state: a required-artifact manifest per suite; artifact presence is an assertion (fail loudly) OR the suites are explicitly marked environment-gated `integration` with a manifest report of what was and was not certified; CANON_DIR derives from UMH_ROOT.
- Files to inspect: both canon test files; the canon artifact directories under data/umh/
- Files likely modified: both test files; new manifest files
- Forbidden files/actions: do not fabricate canon artifacts to go green; no hardcoded /opt/OS.
- Dependencies: WP-P6-003 (marker), WP-P6-001
- Risk class: LOW
- Approval required: no
- Acceptance criteria: with artifacts absent, the suite fails (or reports 0-certified under the integration marker) — never silently green; skip count for present-artifact runs is 0.
- Proof required: run transcripts in both artifact states.
- Tests to add/run: the two suites.
- Rollback plan: git revert.
- Expected output: honest certification suites.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-010: Replace misleading assertion patterns

- Closes: GAP-H-010
- Current state: three misleading-test patterns: enum-value self-assertions that can only fail if Python breaks (tests/test_governed_execution_runtime.py:23-58; tests/test_c20_0_voice_ingress.py:22-40); 11 files asserting on `inspect.getsource` string content (e.g. tests/test_phase9_5_spine_native_propagation.py:557-560) — brittle against refactors and satisfiable by comments; simulated transport (test_mesh_dispatch_contract.py, handled by WP-P6-007).
- Desired state: behavioral assertions replace enum self-checks; source-string checks replaced by AST-based checks or removed; an inventory documents each replacement.
- Files to inspect: the 11 getsource files (scripted inventory), the two enum-literal files
- Files likely modified: ~13 test files
- Forbidden files/actions: do not delete coverage without replacement or explicit classification; after refactoring, remember tests asserting on source strings elsewhere may break — run the full contract set.
- Dependencies: WP-P0-011, WP-P6-003
- Risk class: LOW
- Approval required: no
- Acceptance criteria: `grep -rln "inspect.getsource" tests/` reduced to 0 (or each survivor justified in-file); enum self-assertion patterns gone; replaced tests fail on a seeded behavioral regression.
- Proof required: grep counts; one red/green example per pattern class.
- Tests to add/run: the modified files + contract set.
- Rollback plan: git revert.
- Expected output: assertions that measure behavior.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-011: Ontology layer-separation acceptance test (L1→L4→L2/L3 grounding chain)

- Closes: GAP-H-011
- Current state: tests/test_p1_phase9_architecture.py enforces code-layer import direction only; tests/test_ontology_enacted.py covers primitive/law/domain-bridge units; nothing asserts that L1 external-reality observations stay grounded (source_ref/evidence) through L4 mapping into L2/L3 objects end-to-end (related: tests/test_grounding_firewall.py, tests/test_source_truth_linker.py).
- Desired state: an acceptance test tracing an observation → grounding/bridge mapping → metamodel object → projection consumption, asserting evidence links survive every hop and that no L3 content is reachable from L1/L2 fixtures.
- Files to inspect: tests/test_ontology_enacted.py, tests/test_grounding_firewall.py, tests/test_source_truth_linker.py, the bridge registry and reality_model stores
- Files likely modified: new tests/test_ontology_grounding_chain.py + fixtures
- Forbidden files/actions: fixture-driven, no live LLM calls (deterministic bridge path); no live-DB dependency.
- Dependencies: WP-P2-004, WP-P3-015, WP-P3-014
- Risk class: LOW
- Approval required: no
- Acceptance criteria: test fails when a fixture drops the evidence link mid-chain or when substrate fixture content contains projection identifiers; green on the converged tree; in CI contract set.
- Proof required: red/green transcript.
- Tests to add/run: the new suite.
- Rollback plan: git revert.
- Expected output: enforced four-layer separation at the semantic level.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-012: Split c28/c29 certification into CI-runnable contract layer + environment-gated live layer

- Closes: GAP-H-013
- Current state: tests/certification/c28_certification.py hardcodes the live prod URL (https://universalmetaharness.tech), Beast SSH env, and a Windows collector path (C:\dev\dev\OS\scripts\browser_gate_collector.py) via _COCKPIT_URL/_BEAST_SSH/_COLLECTOR_SCRIPT constants; tests/certification/c29_benchmark.py similar — runnable only from the production VPS with the executor node online; results are point-in-time, not regression-repeatable.
- Desired state: (a) a CI-runnable contract layer against a local cockpit build/TestClient; (b) an environment-gated live certification marked `integration` with evidence manifests; endpoints/hosts from device_registry/env, not literals.
- Files to inspect: both certification scripts; WP-P6-008's contract tests (shared fixtures); infra/device_registry.json
- Files likely modified: split modules under tests/certification/; marker config
- Forbidden files/actions: Browser Verification Law — live browser evidence collection stays on executor-roled nodes via the mesh daemon relay, never orchestrator-local Playwright; credential-injection law (1Password op run) for any executor-side auth; single-domain rule (universalmetaharness.tech) stays config, not code; no cockpit deploy.
- Dependencies: WP-P6-008, WP-P6-003
- Risk class: LOW
- Approval required: no
- Acceptance criteria: contract layer runs green in CI with no network beyond localhost; live layer refuses to run without required env and produces an evidence manifest when it does; zero hardcoded host/path constants remain (env/registry-derived).
- Proof required: CI run of the contract layer; grep for the three removed constants.
- Tests to add/run: both layers.
- Rollback plan: git revert.
- Expected output: repeatable certification architecture.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-013: Contract tests for untested runtime v1 gates and registries

- Closes: GAP-B2-011, GAP-B2-012
- Current state: WorkPacketExecutionGate v1 (substrate/execution/runtime/workpacket_execution_gate_v1.py:310) validates packets before the runtime crossing yet has zero test coverage (grep of tests/ negative) and validates scalars, not a typed WorkPacket; RuntimeSessionRegistry v1 (substrate/execution/runtime/runtime_session_registry_v1.py:82) is equally untested (no test file references it).
- Desired state: contract tests for every gate dimension; registry lifecycle tests (create/heartbeat/health transitions); the gate typed against the canonical WorkPacket once WP-P2-005 lands.
- Files to inspect: the two modules; WP-P2-005's canonical WorkPacket; WP-P2-009's renamed session type
- Files likely modified: new tests/test_workpacket_execution_gate.py, tests/test_runtime_session_registry.py; gate typing update after 014
- Forbidden files/actions: tests must not require live nodes or the mesh host process; typing change to the gate is a separate commit from the tests (tests first, against current behavior).
- Dependencies: WP-P0-011; typing step depends on WP-P2-005, WP-P2-009
- Risk class: LOW (new tests; MEDIUM for the later typing commit)
- Approval required: no
- Acceptance criteria: every public gate check has a passing + failing case; registry lifecycle transitions covered; coverage grep no longer negative for either module.
- Proof required: pytest transcript; coverage grep.
- Tests to add/run: the two new suites.
- Rollback plan: git revert.
- Expected output: tested runtime-crossing contracts.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-014: Add a scheduled full-scan enforcement sweep for all check_*.py gates
- Closes: GAP-A-006, GAP-A-007
- Current state: `/opt/OS/.git/hooks/pre-commit` runs 9 gates on staged files only; no CI/cron runs `--all`. Full-scan failures exist today (46 BLOCKED type divergences, 3 projection-leak violations) while every commit passes. Separately, `check_dependency_direction.py` LEGACY_VIOLATIONS exempts 70 files but only ~10 still violate (e.g., substrate→adapters importers = 1: `grounding_registry.py:370`) — the grandfather list is stale by ~55 entries, so every exempted-but-clean file can silently regress.
- Desired state: a scheduled (cron/CI) full-scan of all `check_*.py` gates with `--all`, surfacing failures; the dependency-checker grandfather list re-derived from ground truth so migrated files are removed and regressions are caught.
- Files to inspect: `/opt/OS/.git/hooks/pre-commit`; `scripts/check_*.py`; `scripts/check_dependency_direction.py:74-155`; `infra/crontab.managed`.
- Files likely modified: new `scripts/full_scan_gates.sh`; `infra/crontab.managed`; `scripts/check_dependency_direction.py` (LEGACY_VIOLATIONS re-derivation).
- Forbidden files/actions: use `scripts/cron-run` wrapper (CPU/lock/secret hygiene); do not silence real failures to make the sweep green.
- Dependencies: WP-P2-003, WP-P3-002 (gates must be green before the sweep enforces)
- Risk class: LOW (new tooling + config)
- Approval required: no
- Acceptance criteria: a scheduled sweep runs all gates `--all` and reports failures; the grandfather list contains only files that actually still violate (injected regression on a de-listed file is caught).
- Proof required: sweep run output; a de-listed file's injected violation caught by the checker.
- Tests to add/run: run the sweep manually; `check_dependency_direction.py --all`.
- Rollback plan: remove the cron entry and script.
- Expected output: code change (+ new enforcement script/config).
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-015: Backfill test coverage for uncovered mutation-core functions
- Closes: GAP-C1-013
- Current state: multiple mutation-core functions are UNVERIFIED for test coverage — ExecutionCoordinator lifecycle methods, `ExecutionPipeline.submit_signal`, `UniversalWorkQueue` writers, `WorkcellDaemon`, `WorkerRegistry`, bridge event model, direct `InstanceRealityModel.record` callers, `GovernedExecutionRuntime`; the `governed_mutation` ungoverned fallback (row 4) has no exercising test; `OperatorLoopRuntime` dormancy is unconfirmed. Additionally, docs/briefs assert `governed_mutation` lives in `substrate/organism/governed_spine.py`, but the only definition is `transports/api/governed.py:65` — a ground-truth/doc drift.
- Desired state: direct tests for the UNVERIFIED mutation-core functions; the fallback path exercised; `OperatorLoopRuntime` dormancy confirmed or wired; docs corrected to point `governed_mutation` at `transports/api/governed.py:65` (or a substrate-level re-export added if the transports location is intentional).
- Files to inspect: C1 findings-table rows 4,10,11,23,26,27,28,30,35,38,39; `transports/api/governed.py:65`; the modules named.
- Files likely modified: new test files under `tests/` and `substrate/organism/tests/`; docs referencing `governed_mutation` location.
- Forbidden files/actions: tests must assert real behavior (not import-only); Python 3.11.
- Dependencies: WP-P0-001 (fallback semantics finalized before testing them)
- Risk class: LOW (tests + docs)
- Approval required: no
- Acceptance criteria: each named function has a behavior test; the fallback path has an exercising test; `OperatorLoopRuntime` is confirmed dormant (documented) or covered; the `governed_mutation` location is documented correctly.
- Proof required: test-run output covering the named functions; doc diff.
- Tests to add/run: the new test files.
- Rollback plan: remove added tests; revert doc.
- Expected output: code change (tests) + documentation change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-016: Remove dead socket ports or wire them
- Closes: GAP-A-010
- Current state: 3 of 22 `substrate/sockets/` ports have zero importers and zero symbol references — `approval_port.py`, `message_port.py`, `sensing_port.py`; approvals actually flow through `substrate/organism/approval_store.py` (the approval_port abstraction was superseded, not removed).
- Desired state: dead ports removed or wired; the sockets inventory documented.
- Files to inspect: `substrate/sockets/approval_port.py:16-39`; `substrate/sockets/message_port.py`; `substrate/sockets/sensing_port.py`; `substrate/organism/approval_store.py`.
- Files likely modified: delete the three port files (or wire them); a sockets-inventory doc.
- Forbidden files/actions: confirm zero importers by grep before deletion; do not remove a port that WP-P1-007 will use for approval consolidation (re-check after WP-P1-007).
- Dependencies: WP-P1-007 (may adopt approval_port during approval unification)
- Risk class: LOW
- Approval required: no
- Acceptance criteria: each of the three ports is either removed (grep confirms zero references) or wired to a live consumer; sockets inventory documented.
- Proof required: grep-clean removal or wiring evidence.
- Tests to add/run: import-smoke of `substrate/sockets/`.
- Rollback plan: restore from git.
- Expected output: code change (+ documentation inventory).
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-017: Enforce the credential gate at every authenticated actuation entry
- Closes: GAP-C3-010, GAP-G-007
- Current state: `substrate/execution/credential_gate.validate_credential_source()` has exactly one caller repo-wide — `substrate/meta_ide/browser_evidence_collector.py:289`. None of the 8 adapter families, node adapters, or auth flows call it, despite `.claude/rules/credential-injection.md` declaring it mandatory. Credential state authority is fragmented: `magic_link_handler.py` stores Gmail creds at `/root/.config/gws/*.json` (`:8,80-83`), `health_check.sh` copies CC credentials to backup dirs, Notion (`adapters/notion/integration/auth.py:29`), Tailscale (`tailscale_api.py:24`), and GWS (dotenv, `gws_connector.py:21`) use raw env credentials; only `adapters/browser_auth/clerk_auth.py` is on the documented `op run` path.
- Desired state: the credential gate is invoked by the adapter base / execution spine for any SECURITY_SENSITIVE or EXTERNAL_COMMUNICATION operation; each adapter declares its credential source in its manifest; disk credential caches are inventoried and either vaulted (1Password) or registered as explicit exceptions.
- Files to inspect: `substrate/execution/credential_gate.py:35`; `substrate/meta_ide/browser_evidence_collector.py:289`; `adapters/notion/integration/auth.py:29`; `adapters/tailscale/tailscale_api.py:24`; `adapters/google_workspace/gws_connector.py:21`; `nodes/windows/umh_node/config.py:55-79`; `services/magic_link_handler.py:8,80-98`; `scripts/auth_monitor/health_check.sh:7-14`.
- Files likely modified: `adapters/tool_adapters/base.py` or the execution spine (gate invocation); the credential-consuming adapters/auth flows; adapter manifests (credential-source declaration).
- Forbidden files/actions: 1Password `op run` for all computer-use credentials (credential-injection law); no plaintext credentials in subprocess/SSH; keep dependency direction.
- Dependencies: WP-P2-011 (adapter contract carries the credential-source declaration)
- Risk class: MEDIUM (touches every credentialed adapter)
- Approval required: yes — could block credentialed operations if a source is misdeclared.
- Acceptance criteria: an authenticated actuation without a validated credential source is rejected; each adapter declares its credential source; disk credential caches are vaulted or explicitly excepted; `check_credential_injection.py --all` passes.
- Proof required: rejection log for a gate-less credentialed op; manifest credential-source declarations; `check_credential_injection.py --all` output.
- Tests to add/run: `tests/test_credential_gate_enforced.py`; run `check_credential_injection.py --all`.
- Rollback plan: revert; gate invocation behind a flag during rollout.
- Expected output: code change.
- Parallelizable: no
- Requires human approval: yes
- Phase: P6

### WP-P6-018: Pin SSH host keys per device-registry entry
- Closes: GAP-G-012
- Current state: `adapters/ssh/ssh_utils.py:19,89,120` and `substrate/execution/workers/workstation/relay_execution_transport_v1.py:28,48-58` use key-based SSH with `StrictHostKeyChecking=accept-new` (TOFU) and a hardcoded key path `/root/.ssh/id_ed25519` — the first connection to a spoofed host is accepted silently; no host-key pinning.
- Desired state: `known_hosts` pinned per `infra/device_registry.json` entry (host key fingerprint as a registry field); `StrictHostKeyChecking=yes`; key path from config not hardcoded.
- Files to inspect: `adapters/ssh/ssh_utils.py:4,19-25,89-121`; `substrate/execution/workers/workstation/relay_execution_transport_v1.py:28,48-58`; `infra/device_registry.json`.
- Files likely modified: `adapters/ssh/ssh_utils.py`; `relay_execution_transport_v1.py`; `infra/device_registry.json` (add host-key fingerprint field).
- Forbidden files/actions: no TOFU on production SSH; no hardcoded key path in substrate/adapters — use config/env; instance-context law for host identities.
- Dependencies: WP-P2-010 (device registry gains the fingerprint field)
- Risk class: MEDIUM
- Approval required: yes — could block SSH to nodes if fingerprints are wrong.
- Acceptance criteria: SSH to a device with a mismatched host key is refused; a pinned known-good host connects; no `accept-new` remains (grep).
- Proof required: refusal log for a mismatched fingerprint; success for a pinned host; grep showing no `accept-new`.
- Tests to add/run: `tests/test_ssh_hostkey_pinning.py` (mismatch rejected).
- Rollback plan: revert; re-add accept-new only for emergency rollback.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: yes
- Phase: P6

### WP-P6-019: Fix hardcoded /opt/OS mesh snapshot path
- Closes: GAP-G-015
- Current state: `transports/node_mesh/registry.py:14` hardcodes `_SNAPSHOT_PATH = Path("/opt/OS/data/runtime/mesh_nodes.json")`, violating the repo's UMH_ROOT convention used 700 lines later in the same package (`server.py:777-778`).
- Desired state: UMH_ROOT-derived path (`os.environ.get("UMH_ROOT", "/opt/OS")`).
- Files to inspect: `transports/node_mesh/registry.py:14`; `transports/node_mesh/server.py:777-778`.
- Files likely modified: `transports/node_mesh/registry.py`.
- Forbidden files/actions: no hardcoded `/opt/OS` paths.
- Dependencies: none
- Risk class: LOW
- Approval required: no
- Acceptance criteria: no hardcoded `/opt/OS` in `registry.py` (grep); snapshot writes to the UMH_ROOT-derived path.
- Proof required: grep-clean check; snapshot written under the derived path.
- Tests to add/run: import-smoke; path-derivation unit assertion.
- Rollback plan: revert single line.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-020: Remove instance-context leaks from substrate and adapters
- Closes: GAP-C1-017, GAP-C3-018
- Current state: `substrate/organism/workload_placement_policy.py:105-125` hardcodes device ids `"vps"`/`"windows_beast"`/`"fly_cockpit"` (violating the Instance Context Law / device-registry protocol); `adapters/github/github_operations.py:35` hardcodes repo default `"antonyfmunoz/OS"`; `adapters/google_workspace/email_gps.py:385-394` hardcodes founder-name heuristics.
- Desired state: device roles loaded from `infra/device_registry.json`/BIS at runtime; repo default and founder heuristics injected from instance config.
- Files to inspect: `substrate/organism/workload_placement_policy.py:105-125`; `adapters/github/github_operations.py:35`; `adapters/google_workspace/email_gps.py:385-394`; `infra/device_registry.json`.
- Files likely modified: the three files above.
- Forbidden files/actions: no instance literals in substrate (instance-context law); no device display-name strings (device-naming protocol); `check_instance_leak.py` must pass.
- Dependencies: WP-P2-010 (canonical node/device source)
- Risk class: LOW
- Approval required: no
- Acceptance criteria: no device ids / repo / founder literals in the cited files; values come from registry/config; `check_instance_leak.py --all` passes.
- Proof required: grep-clean check; `check_instance_leak.py --all` output.
- Tests to add/run: run `check_instance_leak.py --all`; import-smoke.
- Rollback plan: revert per-file.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-021: Correct the mislabelled merge-verification mutation name
- Closes: GAP-C2-009
- Current state: `transports/api/cockpit_autonomous_routes.py:266-267` — `_autonomous_pr_factory_verify_merge` submits with `mutation_name="sandbox_create"`; the verification-of-merge action inherits the sandbox-creation risk spec and the audit trail misattributes the action class.
- Desired state: a dedicated `merge_verify` MutationSpec (or an accurate existing registered name) is used.
- Files to inspect: `transports/api/cockpit_autonomous_routes.py:241-267`; `substrate/organism/mutation_registry.py`.
- Files likely modified: `transports/api/cockpit_autonomous_routes.py`; `substrate/organism/mutation_registry.py` (add `merge_verify` spec).
- Forbidden files/actions: mutation name must match action semantics; register any new spec accurately.
- Dependencies: WP-P1-002 (registration + literal check)
- Risk class: LOW
- Approval required: no
- Acceptance criteria: merge verification submits under an accurate registered name; trace events attribute the correct action class; the literal↔registry check passes.
- Proof required: trace event showing the corrected mutation name.
- Tests to add/run: assertion in the autonomous-routes test; run `check_mutation_name_registration.py`.
- Rollback plan: revert per-file.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-022: Index function-scoped (lazy) imports in the structural graph
- Closes: GAP-E2-015
- Current state: `scripts/query_graph.py dependents` misses lazy function-scoped imports, so route-wired modules report tests-only dependents — e.g. `substrate/workstation/voice_ingress_runtime.py` shows no wiring although `transports/api/cockpit_voice_ingress_routes.py:16` imports it inside `configure()`. Every "dormant" classification (WP-P2-025, -048) currently requires manual grep compensation; the graph under-reports wiring across the 121 route satellites, which use the lazy pattern pervasively.
- Desired state: the graph builder indexes function-scoped imports (flagged `lazy: true` on the edge), or a supplementary wiring-census generator produces a machine-readable lazy-import map merged into dependents queries; bootstrap freshness checks unchanged.
- Files to inspect: scripts/query_graph.py; the graph builder invoked by scripts/update-graph; a sample lazy import (transports/api/cockpit_voice_ingress_routes.py:16) as fixture.
- Files likely modified: graph builder script(s); query_graph.py (edge-type surfacing).
- Forbidden files/actions: deterministic AST-based extraction only (no LLM); keep graph rebuild within CPU-gate budgets (it runs on the VPS); do not change the graph schema in a way that breaks existing consumers (retrieval-rules hierarchy depends on it).
- Dependencies: none
- Risk class: MEDIUM (tooling used by every session's retrieval hierarchy)
- Approval required: no
- Acceptance criteria: `query_graph.py dependents substrate/workstation/voice_ingress_runtime.py` lists cockpit_voice_ingress_routes.py with a lazy flag; graph rebuild completes within current time budget; verify_knowledge_system passes.
- Proof required: before/after dependents output for the fixture module; rebuild timing.
- Tests to add/run: graph-builder unit test with a lazy-import fixture; `python3 scripts/verify_knowledge_system.py`.
- Rollback plan: revert builder; regenerate graph.
- Expected output: code change.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-023: Doc-truth reconciliation — regenerate stale operator/broadcast/API status docs from live inventory
- Closes: GAP-E2-011, GAP-E2-014, GAP-E3-014, GAP-F2-011
- Current state: the knowledge layer contradicts the code in at least six places: (a) docs/system/current_system_status.md is frozen at 2026-05-27 / Phase 96.8-era, predating the entire 13.x/14.x and C17-C21 record; (b) docs/audits/future_trajectory_preservation.md:105-151 recommends "Preserve all" for ~16,500 lines whose files (runtime_engine/, substrate/stt_producer.py, substrate/station_daemon.py) no longer exist — never reconciled migrated-vs-lost; (c) docs/phase77_workstation_state_report.md cites a deleted umh/workstation/ package (umh/ now holds 3 relay scripts); (d) docs/audits/convergence/phase13_4m_multi_runtime_jarvis_acceptance_correction.md:65 says the browser adapter has "No adapter export yet" while adapters/browser/__init__.py re-exports BrowserAgent — one is stale; (e) the canonical broadcast plan (docs/superpowers/plans/2026-06-12-broadcast-subsystem.md:234-254,253) keeps a superseded wave graph and a "scene activation restarts FFmpeg" claim contradicted by its own ZMQ evidence (docs/superpowers/specs/broadcast/WAVE2_INVESTIGATION.md:150-176,275 explicitly requests the update); (f) ARCHITECTURE.md:433 claims "One API — transports/api/http/ serves all clients" while all cockpit traffic serves from FastAPI services/operator_api.py:862 via transports/api/cockpit.py — the parallel Hono stack (transports/api/http/server.ts) is undeployed (its retirement decision is WP-P2-022; this packet corrects the documentation to observed reality and records the decision's outcome).
- Desired state: each stale doc corrected or superseded with a supersession notice per docs/strategy/supersession_rules.md; current_system_status.md regenerated from live inventory (and ideally made generator-backed); the preservation doc gets a per-file migrated/lost disposition table; fleet-audit claims regenerated from the adapter registry rather than manual tables; ARCHITECTURE.md names the actually-serving API.
- Files to inspect: the six documents above; adapters/browser/__init__.py; ls umh/; services/operator_api.py:840-870; transports/api/http/server.ts:1-60.
- Files likely modified: the six documents (+ supersession notices); optionally a small generator script for the status doc.
- Forbidden files/actions: documentation only — zero code-behavior changes; do not delete historical phase docs (supersede, don't erase); ARCHITECTURE.md is a master spec — changes reviewed like code.
- Dependencies: WP-P2-022 (API-stack decision feeds the ARCHITECTURE.md correction; interim wording may state observed reality + pending decision)
- Risk class: LOW (docs)
- Approval required: no
- Acceptance criteria: none of the six docs cites a nonexistent path (link-check script over cited paths passes); each superseded section carries a notice; ARCHITECTURE.md API section matches nginx/operator_api observed binding.
- Proof required: path-existence check output over all doc-cited paths; diff of the six docs.
- Tests to add/run: a docs path-reference checker run (add to scripts/ if absent).
- Rollback plan: git revert.
- Expected output: documentation-only.
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

### WP-P6-024: Prove cross-host broadcast stream egress (VPS → Beast over WireGuard)
- Closes: GAP-E3-004
- Current state: every broadcast proof to date used same-host MediaMTX (the VPS's own Tailscale IP, kernel-local); cross-host VPS→Beast RTMP over WireGuard is explicitly DEFERRED/NOT PROVEN (docs/superpowers/specs/broadcast/AGENT_GOLIVE_INVESTIGATION.md:186-217; SLICE0_PROOF_REPORT.md:211). An unresolved risk rides along: Python 3.11-in-Docker vs 3.12 `ipaddress.is_private` classification of 100.64.0.0/10 may change the SSRF validator's verdict for tailnet addresses (AGENT_GOLIVE_INVESTIGATION.md:126). The acceptance criterion is already written (BROADCAST_BUILD_PLAN.md:340-341).
- Desired state: a recorded cross-node egress proof (VPS engine → Beast-hosted RTMP sink over the tailnet) with the SSRF validator's behavior verified under the container's Python 3.11 (`_validate_output_url` unit-tested against 100.64.0.0/10 addresses in both interpreter contexts); results appended to the broadcast proof record.
- Files to inspect: adapters/broadcast/ffmpeg_args.py (`_validate_output_url`); docs/superpowers/specs/broadcast/AGENT_GOLIVE_INVESTIGATION.md:118-132,186-217; docs/superpowers/specs/broadcast/BROADCAST_BUILD_PLAN.md:335-345; tests/adapters/broadcast/.
- Files likely modified: tests/adapters/broadcast/ (new SSRF interpreter-matrix test); proof record doc; possibly ffmpeg_args.py if the 3.11 verdict is wrong (then MEDIUM change).
- Forbidden files/actions: Python 3.11 semantics are the deployment truth (Docker law) — never validate only on host 3.12; stream egress subprocesses through the CPU-gated lifecycle; Beast-side sink setup respects node-role discipline (heavy media on Beast is correct placement); no public egress targets in the proof (tailnet only).
- Dependencies: WP-P4-018 (optional — proof is valid with synthetic sources; real capture strengthens it)
- Risk class: LOW (proof + tests; escalates to MEDIUM only if validator fix required)
- Approval required: no
- Acceptance criteria: live stream produced on the VPS is consumable from the Beast sink for ≥60s without drop (per the build plan's written criterion); SSRF test matrix documents allow/deny for tailnet, loopback, and public targets under Python 3.11; proof appended to the broadcast spec record.
- Proof required: sink-side recording snippet + stream stats; test-matrix output from the 3.11 container.
- Tests to add/run: new SSRF matrix test run inside the Docker Python 3.11 image; tests/adapters/broadcast/ suite.
- Rollback plan: none needed (proof + additive tests); validator fix (if any) is an isolated revertible commit.
- Expected output: proof artifact + tests (code change only if the validator is wrong).
- Parallelizable: yes
- Requires human approval: no
- Phase: P6

---

## Gap → Packet reconciliation (all 270 gap IDs)

Mechanically verified: the set of gap IDs in this table equals the set in `_index.json` (270/270), and each gap maps to exactly one packet.

### Workstream A (16 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-A-001 | high | WP-P3-002 |
| GAP-A-002 | high | WP-P2-021 |
| GAP-A-003 | high | WP-P3-001 |
| GAP-A-004 | critical | WP-P1-001 |
| GAP-A-005 | high | WP-P2-003 |
| GAP-A-006 | high | WP-P6-014 |
| GAP-A-007 | medium | WP-P6-014 |
| GAP-A-008 | high | WP-P1-006 |
| GAP-A-009 | medium | WP-P1-001 |
| GAP-A-010 | low | WP-P6-016 |
| GAP-A-011 | medium | WP-P3-002 |
| GAP-A-012 | medium | WP-P4-003 |
| GAP-A-013 | medium | WP-P2-022 |
| GAP-A-014 | medium | WP-P2-022 |
| GAP-A-015 | low | WP-P3-012 |
| GAP-A-016 | low | WP-P2-021 |

### Workstream B1 (12 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-B1-001 | critical | WP-P0-008 |
| GAP-B1-002 | high | WP-P2-006 |
| GAP-B1-003 | high | WP-P1-011 |
| GAP-B1-004 | high | WP-P2-002 |
| GAP-B1-005 | medium | WP-P2-008 |
| GAP-B1-006 | medium | WP-P2-007 |
| GAP-B1-007 | medium | WP-P2-006 |
| GAP-B1-008 | high | WP-P0-001 |
| GAP-B1-009 | medium | WP-P2-005 |
| GAP-B1-010 | high | WP-P1-001 |
| GAP-B1-011 | medium | WP-P2-001 |
| GAP-B1-012 | low | WP-P1-012 |

### Workstream B2 (16 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-B2-001 | critical | WP-P2-005 |
| GAP-B2-002 | high | WP-P0-008 |
| GAP-B2-003 | high | WP-P2-009 |
| GAP-B2-004 | high | WP-P2-010 |
| GAP-B2-005 | high | WP-P2-011 |
| GAP-B2-006 | high | WP-P1-001 |
| GAP-B2-007 | medium | WP-P2-012 |
| GAP-B2-008 | medium | WP-P2-013 |
| GAP-B2-009 | medium | WP-P2-014 |
| GAP-B2-010 | medium | WP-P2-015 |
| GAP-B2-011 | medium | WP-P6-013 |
| GAP-B2-012 | medium | WP-P6-013 |
| GAP-B2-013 | low | WP-P2-005 |
| GAP-B2-014 | low | WP-P2-002 |
| GAP-B2-015 | low | WP-P2-014 |
| GAP-B2-016 | low | WP-P2-014 |

### Workstream B3 (14 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-B3-001 | critical | WP-P0-001 |
| GAP-B3-002 | high | WP-P1-007 |
| GAP-B3-003 | high | WP-P1-016 |
| GAP-B3-004 | high | WP-P2-016 |
| GAP-B3-005 | high | WP-P1-013 |
| GAP-B3-006 | high | WP-P0-009 |
| GAP-B3-007 | medium | WP-P1-016 |
| GAP-B3-008 | medium | WP-P2-017 |
| GAP-B3-009 | medium | WP-P1-015 |
| GAP-B3-010 | medium | WP-P0-009 |
| GAP-B3-011 | medium | WP-P1-014 |
| GAP-B3-012 | low | WP-P1-007 |
| GAP-B3-013 | low | WP-P2-002 |
| GAP-B3-014 | low | WP-P0-001 |

### Workstream B4 (15 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-B4-001 | critical | WP-P2-018 |
| GAP-B4-002 | high | WP-P2-018 |
| GAP-B4-003 | medium | WP-P2-019 |
| GAP-B4-004 | medium | WP-P2-019 |
| GAP-B4-005 | medium | WP-P2-020 |
| GAP-B4-006 | medium | WP-P2-018 |
| GAP-B4-007 | critical | WP-P3-004 |
| GAP-B4-008 | high | WP-P3-004 |
| GAP-B4-009 | medium | WP-P3-004 |
| GAP-B4-010 | high | WP-P3-005 |
| GAP-B4-011 | high | WP-P3-006 |
| GAP-B4-012 | high | WP-P3-011 |
| GAP-B4-013 | medium | WP-P3-014 |
| GAP-B4-014 | medium | WP-P3-007 |
| GAP-B4-015 | low | WP-P2-001 |

### Workstream C1 (18 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-C1-001 | critical | WP-P0-007 |
| GAP-C1-002 | critical | WP-P0-007 |
| GAP-C1-003 | high | WP-P0-001 |
| GAP-C1-004 | high | WP-P1-007 |
| GAP-C1-005 | high | WP-P1-008 |
| GAP-C1-006 | high | WP-P1-006 |
| GAP-C1-007 | medium | WP-P3-008 |
| GAP-C1-008 | medium | WP-P1-008 |
| GAP-C1-009 | medium | WP-P3-008 |
| GAP-C1-010 | medium | WP-P2-002 |
| GAP-C1-011 | medium | WP-P1-009 |
| GAP-C1-012 | low | WP-P3-002 |
| GAP-C1-013 | low | WP-P6-015 |
| GAP-C1-014 | medium | WP-P0-007 |
| GAP-C1-015 | medium | WP-P1-009 |
| GAP-C1-016 | medium | WP-P1-009 |
| GAP-C1-017 | low | WP-P6-020 |
| GAP-C1-018 | medium | WP-P1-001 |

### Workstream C2 (14 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-C2-001 | critical | WP-P0-001 |
| GAP-C2-002 | critical | WP-P1-005 |
| GAP-C2-004 | critical | WP-P0-002 |
| GAP-C2-003 | high | WP-P1-002 |
| GAP-C2-005 | high | WP-P1-007 |
| GAP-C2-006 | high | WP-P1-003 |
| GAP-C2-007 | medium | WP-P1-004 |
| GAP-C2-008 | medium | WP-P2-022 |
| GAP-C2-010 | medium | WP-P5-001 |
| GAP-C2-012 | medium | WP-P2-022 |
| GAP-C2-014 | medium | WP-P5-002 |
| GAP-C2-009 | low | WP-P6-021 |
| GAP-C2-011 | low | WP-P1-004 |
| GAP-C2-013 | low | WP-P2-022 |

### Workstream C3 (19 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-C3-001 | critical | WP-P0-002 |
| GAP-C3-002 | high | WP-P0-003 |
| GAP-C3-003 | high | WP-P1-010 |
| GAP-C3-004 | high | WP-P0-005 |
| GAP-C3-005 | high | WP-P0-004 |
| GAP-C3-006 | high | WP-P1-010 |
| GAP-C3-007 | high | WP-P1-010 |
| GAP-C3-008 | medium | WP-P1-007 |
| GAP-C3-009 | medium | WP-P0-002 |
| GAP-C3-010 | medium | WP-P6-017 |
| GAP-C3-011 | medium | WP-P3-001 |
| GAP-C3-012 | medium | WP-P4-001 |
| GAP-C3-013 | medium | WP-P0-003 |
| GAP-C3-014 | medium | WP-P0-006 |
| GAP-C3-015 | low | WP-P1-003 |
| GAP-C3-016 | low | WP-P1-004 |
| GAP-C3-017 | low | WP-P0-008 |
| GAP-C3-018 | low | WP-P6-020 |
| GAP-C3-019 | low | WP-P4-003 |

### Workstream D1 (15 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-D1-001 | high | WP-P2-004 |
| GAP-D1-002 | high | WP-P3-015 |
| GAP-D1-003 | high | WP-P3-015 |
| GAP-D1-004 | medium | WP-P3-016 |
| GAP-D1-005 | high | WP-P2-002 |
| GAP-D1-006 | high | WP-P3-003 |
| GAP-D1-007 | medium | WP-P3-016 |
| GAP-D1-008 | medium | WP-P3-017 |
| GAP-D1-009 | medium | WP-P3-016 |
| GAP-D1-010 | medium | WP-P3-014 |
| GAP-D1-011 | low | WP-P3-018 |
| GAP-D1-012 | low | WP-P3-018 |
| GAP-D1-013 | medium | WP-P3-011 |
| GAP-D1-014 | low | WP-P3-018 |
| GAP-D1-015 | low | WP-P3-018 |

### Workstream D2 (16 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-D2-001 | critical | WP-P0-010 |
| GAP-D2-002 | high | WP-P3-009 |
| GAP-D2-003 | high | WP-P3-010 |
| GAP-D2-004 | high | WP-P3-013 |
| GAP-D2-005 | high | WP-P3-011 |
| GAP-D2-006 | high | WP-P3-005 |
| GAP-D2-007 | high | WP-P4-005 |
| GAP-D2-008 | medium | WP-P4-006 |
| GAP-D2-009 | medium | WP-P3-004 |
| GAP-D2-010 | medium | WP-P4-007 |
| GAP-D2-011 | medium | WP-P4-008 |
| GAP-D2-012 | medium | WP-P3-015 |
| GAP-D2-013 | medium | WP-P3-019 |
| GAP-D2-014 | medium | WP-P3-011 |
| GAP-D2-015 | low | WP-P3-012 |
| GAP-D2-016 | low | WP-P3-010 |

### Workstream E1 (21 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-E1-001 | high | WP-P4-004 |
| GAP-E1-002 | high | WP-P3-009 |
| GAP-E1-003 | critical | WP-P3-011 |
| GAP-E1-004 | medium | WP-P3-004 |
| GAP-E1-005 | high | WP-P4-009 |
| GAP-E1-006 | high | WP-P4-013 |
| GAP-E1-007 | high | WP-P3-020 |
| GAP-E1-008 | high | WP-P4-010 |
| GAP-E1-009 | medium | WP-P4-011 |
| GAP-E1-010 | medium | WP-P2-028 |
| GAP-E1-011 | medium | WP-P4-012 |
| GAP-E1-012 | high | WP-P3-013 |
| GAP-E1-013 | medium | WP-P2-023 |
| GAP-E1-014 | medium | WP-P4-009 |
| GAP-E1-015 | medium | WP-P3-004 |
| GAP-E1-016 | medium | WP-P3-009 |
| GAP-E1-017 | medium | WP-P2-029 |
| GAP-E1-018 | low | WP-P4-020 |
| GAP-E1-019 | medium | WP-P3-011 |
| GAP-E1-020 | medium | WP-P4-015 |
| GAP-E1-021 | medium | WP-P4-014 |

### Workstream E2 (17 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-E2-001 | critical | WP-P1-017 |
| GAP-E2-002 | high | WP-P2-027 |
| GAP-E2-003 | high | WP-P0-015 |
| GAP-E2-004 | high | WP-P1-018 |
| GAP-E2-005 | medium | WP-P2-024 |
| GAP-E2-006 | medium | WP-P2-025 |
| GAP-E2-007 | medium | WP-P2-025 |
| GAP-E2-008 | medium | WP-P6-002 |
| GAP-E2-009 | medium | WP-P1-021 |
| GAP-E2-010 | medium | WP-P5-017 |
| GAP-E2-011 | medium | WP-P6-023 |
| GAP-E2-012 | medium | WP-P2-026 |
| GAP-E2-013 | medium | WP-P5-015 |
| GAP-E2-017 | medium | WP-P4-016 |
| GAP-E2-014 | low | WP-P6-023 |
| GAP-E2-015 | low | WP-P6-022 |
| GAP-E2-016 | low | WP-P2-026 |

### Workstream E3 (14 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-E3-001 | high | WP-P4-004 |
| GAP-E3-002 | high | WP-P4-017 |
| GAP-E3-003 | high | WP-P4-018 |
| GAP-E3-004 | medium | WP-P6-024 |
| GAP-E3-005 | high | WP-P1-019 |
| GAP-E3-006 | medium | WP-P4-019 |
| GAP-E3-007 | high | WP-P1-020 |
| GAP-E3-008 | high | WP-P2-030 |
| GAP-E3-009 | low | WP-P4-020 |
| GAP-E3-010 | low | WP-P4-020 |
| GAP-E3-011 | low | WP-P4-020 |
| GAP-E3-012 | medium | WP-P2-023 |
| GAP-E3-013 | medium | WP-P2-030 |
| GAP-E3-014 | low | WP-P6-023 |

### Workstream F1 (15 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-F1-002 | critical | WP-P5-004 |
| GAP-F1-001 | high | WP-P5-003 |
| GAP-F1-003 | high | WP-P5-007 |
| GAP-F1-004 | high | WP-P5-003 |
| GAP-F1-005 | high | WP-P5-005 |
| GAP-F1-012 | high | WP-P0-012 |
| GAP-F1-015 | medium | WP-P5-003 |
| GAP-F1-006 | medium | WP-P5-008 |
| GAP-F1-007 | medium | WP-P5-009 |
| GAP-F1-008 | medium | WP-P5-010 |
| GAP-F1-009 | medium | WP-P5-011 |
| GAP-F1-010 | medium | WP-P5-012 |
| GAP-F1-011 | medium | WP-P5-013 |
| GAP-F1-013 | low | WP-P5-003 |
| GAP-F1-014 | low | WP-P5-014 |

### Workstream F2 (18 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-F2-001 | critical | WP-P5-004 |
| GAP-F2-002 | high | WP-P5-006 |
| GAP-F2-003 | high | WP-P0-012 |
| GAP-F2-004 | high | WP-P5-005 |
| GAP-F2-005 | high | WP-P5-016 |
| GAP-F2-006 | high | WP-P0-013 |
| GAP-F2-007 | high | WP-P0-014 |
| GAP-F2-008 | medium | WP-P5-010 |
| GAP-F2-009 | medium | WP-P5-003 |
| GAP-F2-010 | medium | WP-P5-006 |
| GAP-F2-011 | medium | WP-P6-023 |
| GAP-F2-012 | medium | WP-P5-005 |
| GAP-F2-013 | medium | WP-P5-006 |
| GAP-F2-014 | medium | WP-P5-015 |
| GAP-F2-015 | low | WP-P5-005 |
| GAP-F2-016 | low | WP-P5-018 |
| GAP-F2-017 | low | WP-P5-017 |
| GAP-F2-018 | low | WP-P5-019 |

### Workstream G (17 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-G-001 | critical | WP-P0-002 |
| GAP-G-002 | critical | WP-P0-002 |
| GAP-G-003 | critical | WP-P0-003 |
| GAP-G-004 | critical | WP-P0-002 |
| GAP-G-005 | high | WP-P2-010 |
| GAP-G-006 | high | WP-P2-011 |
| GAP-G-007 | high | WP-P6-017 |
| GAP-G-008 | high | WP-P4-002 |
| GAP-G-009 | high | WP-P4-002 |
| GAP-G-010 | high | WP-P0-003 |
| GAP-G-011 | medium | WP-P2-002 |
| GAP-G-012 | medium | WP-P6-018 |
| GAP-G-013 | medium | WP-P2-010 |
| GAP-G-014 | medium | WP-P4-002 |
| GAP-G-015 | low | WP-P6-019 |
| GAP-G-016 | low | WP-P0-002 |
| GAP-G-017 | low | WP-P4-002 |

### Workstream H (13 gaps)

| Gap ID | Severity | Packet |
|---|---|---|
| GAP-H-001 | critical | WP-P0-011 |
| GAP-H-002 | critical | WP-P6-005 |
| GAP-H-003 | high | WP-P6-001 |
| GAP-H-004 | high | WP-P6-004 |
| GAP-H-005 | high | WP-P6-006 |
| GAP-H-006 | high | WP-P6-007 |
| GAP-H-007 | medium | WP-P6-008 |
| GAP-H-008 | medium | WP-P6-003 |
| GAP-H-009 | medium | WP-P6-009 |
| GAP-H-010 | medium | WP-P6-010 |
| GAP-H-011 | medium | WP-P6-011 |
| GAP-H-012 | low | WP-P1-001 |
| GAP-H-013 | low | WP-P6-012 |

