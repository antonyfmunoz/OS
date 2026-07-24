# Wave 2 — Exact Critical Ledger

One row per CRITICAL. **No finding may disappear or be downgraded without a
written adjudication recorded here.**

## Accounting reconciliation

An earlier status report said "nine new CRITICALs, three fixed, five open" —
which sums to eight. The omission was **SEC-C1** (teardown never destroys
`worker-homes/`): it was described in prose but left out of the open count. The
correct accounting is below and is now the authority.

| Round | Count | IDs |
|---|---|---|
| Round 1 (pre-repair) | 7 | C1, C2, C3, C4, SEC-C1(evidence), SEC-C2(shared home), SEC-C3(readiness exit) |
| Round 2 (post-repair review) | 9 | C-1…C-5, SEC-C1…SEC-C4 |
| **Round 2 status** | **9 = 6 fixed + 3 open** | fixed: SEC-C2, SEC-C3, SEC-C4, C-1, C-2, C-3 |

Round-1 and Round-2 IDs are namespaced by round; they are different findings that
happen to share numbering. Round 1 is closed (all 7 repaired in R1–R3). This
ledger tracks Round 2.

---

## Round 2 — the nine

### SEC-C3 — ambient env bypass disabled the entire Proof gate — **FIXED**

- **Root cause:** `lifecycle._assert_durable_proof` began with
  `if os.environ.get("UMH_W2_ALLOW_NONDURABLE_PROOF") == "1": return`.
- **Authority violated:** governed completion (Amendment v1 clause 6) — no Task
  completes without independent durable Proof.
- **Exploit path:** the runner is launched via
  `bash -c "exec env ... python ..."`, which **inherits the operator's full
  environment**. Any stale export in a shell profile, tmux pane, or prior test
  session silently converts the completion guarantee into a no-op, unlogged, on a
  live billed run. Verified: with the var set, a **nonexistent** `proof_id`
  completed an attempt.
- **Status:** FIXED — hatch deleted, no replacement bypass. The three lifecycle
  test files that used it now mint REAL durable Proofs.
- **Commit:** R4b. **Test:** `test_no_proof_bypass_exists_in_the_tree`.
- **Independent-review disposition:** raised by security review; verified
  independently before fixing.
- **Residual risk:** none. A source-level test asserts the string appears nowhere
  in `substrate/` or `scripts/`.

### SEC-C2 — Proof lineage failed OPEN on absent binding — **FIXED**

- **Root cause:** both binding checks were guarded by truthiness
  (`if recorded_attempt and recorded_attempt != ...`), so a Proof whose `action`
  carried no `attempt_id` satisfied the gate for **every** attempt.
- **Authority violated:** Proof-to-attempt binding; a Proof may only complete the
  attempt it proves.
- **Exploit path:** the plan-execution path mints proofs without `attempt_id`.
  Verified: a durable Proof with an empty `attempt_id` completed an unrelated
  attempt on the same task — so a stray proof could complete a *failed* retry.
- **Status:** FIXED — both checks are equality, absent lineage is a rejection.
- **Commit:** R4b. **Test:** `test_proof_with_absent_lineage_is_rejected`,
  `test_proof_for_another_attempt_is_rejected`.
- **Residual risk:** none for attempt proofs. Plan-execution proofs are bound by
  `work_id` + classification and are never used to complete an attempt.

### SEC-C4 — non-bwrap primitives exempted from the isolation gate — **FIXED**

- **Root cause:** `preflight_isolation` returned `(True, "not probe-verified")`
  for `systemd-run`/`nsjail`, and both call sites used
  `if not ok and prim == "bwrap"` / `ok or prim != "bwrap"` — so a non-bwrap
  primitive **could never fail** the gate.
- **Authority violated:** Amendment v1 clause 4 (enforced host isolation).
- **Exploit path:** `systemd-run` creates no mount namespace (`/opt/OS`, all
  credentials, every other run's state readable); `nsjail --chroot /` is the
  whole filesystem. Neither propagates `CLAUDE_CONFIG_DIR`/`TMPDIR`/`XDG_*`, so
  the per-attempt credential boundary collapses to the real `~/.claude` —
  reinstating the shared-home defect while reporting `isolation_ok: true`.
- **Status:** FIXED — unprovable primitives return `False`; both gates use
  `if not ok`. Wave 2 hard-requires bwrap.
- **Commit:** R4b. **Test:** `test_non_bwrap_primitive_cannot_qualify`,
  `test_isolation_gates_fail_closed_for_every_primitive`.
- **Residual risk:** the run cannot proceed on a host without bwrap. Intended.

### C-1 — `diff_scope` is a structural no-op — **FIXED**

Closed in three stages; the first two were incomplete and are recorded here
because "the repair needed repairing twice" is the finding.

- **Root cause:** `LeaseManager.acquire` always sets
  `writable_paths=[worktree_path]`; verification normalized that single absolute
  entry to `"."` → `whole_worktree=True` → `scope_ok=True` unconditionally, and
  the computed `outside` list was discarded.
- **Authority violated:** diff-scope containment; the packet's declared paths.
- **Failure path:** a worker that rewrites the fixture's own tests earns a valid
  AttemptProof.
- **Stage 1 (`dab9045f5`):** scope sourced from canonical WorkPacket, computed
  from git (tracked + untracked) against the lease base, unsafe policies
  rejected, verdict fails before Proof creation.
- **Stage 2 (`7ece70194`) — owner correction, BINDING:** stage 1 resolved scope
  through plan-node lineage, which reads `source_evidence`. That made
  *descriptive provenance* control *execution permission* — editing an evidence
  entry could widen what a worker may write. `EvidenceRef` states the rule
  verbatim: "Evidence is provenance — it can never be a mutation authority."
  Authority moved to first-class typed `WorkRequirements.writable_path_scope` +
  `scope_declared`. Evidence still resolves IDENTITY (which packet is "the
  backend Task"), never permission.
- **Stage 3 (this commit) — snapshot-bound diff:** `base = snapshot_ref or
  "HEAD"` was a *deterministic* false green, not an edge case. Real workers
  COMMIT, so after the commit HEAD **is** the worker's commit and
  `git diff HEAD` returns exactly nothing. Measured:
  `vs REAL base: 'tests/test_api.py'` / `vs HEAD: ''`. No fallback remains; a
  lease with no snapshot_ref fails closed.
- **Same defect found on the WORKER side while closing stage 3:**
  `worker_claude_cli` captured artifacts as `<base>..HEAD` with the same `or
  "HEAD"` fallback, and `wave2_attempt_runner` built its lease with
  `snapshot_ref = ""`. The real field range was therefore `HEAD..HEAD` — empty
  by definition — so **every** attempt would have reported zero files and zero
  commits and failed the `artifacts` check on genuinely successful work. The
  dispatch envelope carried no base at all. `DispatchEnvelope.base_commit` added
  (covered by the HMAC via `asdict`), threaded through the runner, and the
  worker now refuses an unanchored lease.
- **Commits:** dab9045f5, 7ece70194, this one.
- **Tests:** `tests/test_wave2_diff_scope_authority.py` (37) — every rejection
  paired with a control so a reject-everything check cannot masquerade as
  correct. Mutation-verified at each stage: re-injecting the whole-worktree pass
  fails 5; re-injecting evidence-derived scope fails 2; restoring the HEAD
  fallback fails 3 (verifier) + 2 (worker chain).
- **Residual risk:** the fixture defaults are a seeding input at materialization
  only. A Task that reaches verification with no declared scope BLOCKS.

### C-2 — the lease is never released; retry deadlocks — **FIXED**

- **Root cause:** `LeaseManager.release()` had **zero production callers**;
  cleanup was scattered (acquire-rollback, revoke, and the worker's own
  `finally`) with nothing tying lease release to home destruction to retry
  admission.
- **Authority violated:** one-active-lease-per-task; retry-as-new-attempt.
- **Failure path:** A1 fails → its lease stays ACTIVE → scheduler mints A2 →
  `acquire()` raises `LeaseError` → A2 BLOCKED → re-READY → BLOCKED forever,
  producing the exact "A failed, C blocked, no false Proof" shape the
  qualification expects for entirely the wrong reason.
- **Fix:** ONE idempotent authority `substrate/execution/attempts/
  terminalization.py::terminalize`. Strict order: verify terminal → release/
  revoke lease → destroy attempt-private home + credential material → reconcile
  spool → retry admissible only after the prior lease is inactive. Covers all
  eleven terminal reasons. Cleanup failure RAISES (blocking security condition),
  never a warning. Refuses to terminalize a still-live attempt. `retry_admissible`
  is the structural gate.
- **Wired:** the control-plane poller terminalizes on EVERY terminal transition
  (SUCCEEDED + verification_rejected) through the SAME `LeaseManager` the
  scheduler acquires with (shared instance in `FieldControlPlaneDriver`).
- **Commit:** this one. **Tests:** `tests/test_wave2_terminalization.py` (21) +
  the field-pipeline recovery assertion in
  `test_failure_qualification_rehearsal`. MUTATION-VERIFIED: skipping lease
  release fails the deadlock tests; dropping the residue scan fails the security
  test; removing the poller's terminalize call fails the pipeline recovery test.
- **Microfix (owner, binding):** the first cut of `TerminalizationResult.ok`
  failed OPEN — it returned True unless a SECURITY-prefixed error or credential
  residue was present, so a lease-release failure reported ok=True and the run
  would pass while the lease stayed ACTIVE. Corrected: `ok` is False for ANY
  error (release/revoke failure, missing LeaseManager with a lease_id, missing
  run_root, residue, spool-reconcile failure, unknown reason). A supplied spool
  with no `drop_inflight_for_attempt` hook is now an explicit failure, not a
  "ledger is truth" no-op. `DispatchSpool.drop_inflight_for_attempt` implemented:
  exact-attempt-id match on the VERIFIED envelope (never a filename), atomic move
  to quarantine, fail-closed on unreadable/tampered envelopes, idempotent, never
  touches a sibling attempt. +12 mutation-verified tests.
- **Wiring truth (order §6):** the authority SUPPORTS eleven reasons; the live
  pipeline WIRES exactly TWO — the poller's `succeeded` and
  `verification_rejected` transitions, the only terminal transitions the
  run-scoped pipeline performs on an attempt. Cancellation / revocation / expiry
  / abandonment / crash / teardown / security-failure are supported but their
  production call sites (a grant-level REVOKED cascade, a teardown sweep) are
  Wave 2 follow-ons — NOT claimed as wired. Pinned by
  `test_poller_wires_exactly_succeeded_and_verification_rejected` and the
  scheduler-docstring truthfulness test (the scheduler docstring previously
  overclaimed a revoke cascade it has no code for; corrected).
- **Residual risk:** teardown-level "zero worker homes across the whole run" is
  SEC-C1's scope (order §8); the cancel/revoke/expiry cascade wiring is a stated
  Wave 2 follow-on, tracked here not hidden.

### C-3 — `scenario_map.json` has no field writer — **FIXED**

- **Root cause:** `write_scenario_map` had ONE non-test occurrence — inside a
  remediation *string*. The real pipeline never wrote the map, so
  `inject-failure` read `{}` → `armed:False` → exit 3, and the failure pass was
  unrunnable. An operator hitting exit 3 would hand-write the map with guessed
  ids or delete the check — restoring the original defect.
- **Authority violated:** failure-injection targeting.
- **Fix:** new field consumer `substrate/execution/attempts/field_scenario_map.py`
  + `write-scenario-map` field subcommand. It reads the ACTUAL materialized
  plan + WorkPacket records from candidate state, resolves each semantic role to
  its exact `wp-<hex12>` through plan-node lineage (`resolve_scenario_map`, no
  title/regex/id-shape guess), and writes a map BOUND to run_id +
  plan_record_id + plan_version + a digest over the resolved ids.
- **Consumed:** `inject-failure` now calls `arming_is_valid_for_run`, which
  validates the persisted map against the LIVE plan+packets and the authorized
  frontier before arming. The chain: real records → exact ids → bound map →
  reread at arming → target by exact equality → injection fires on the backend
  packet's FIRST attempt only → retry (attempt 2) unrevoked → recover.
- **Fails qualification on all C-3 modes** (each pinned by a test): absent map,
  stale map (plan superseded / digest recompute mismatch), wrong-run binding,
  nonexistent task, target outside the authorized frontier, ambiguous role
  (two nodes same title), unknown variant, and `injection_fired`==False
  (configured-but-never-observed). A sibling task is never revoked.
- **Architectural guard (C-1 applied to C-3):** the map carries task IDENTITIES
  + binding ONLY — never allowed tools, writable scope, or execution
  constraints. Those stay on the canonical WorkPacket requirements. Pinned by
  `test_scenario_map_is_identity_only_never_writable_scope` and an AST-level
  no-shape-guessing test.
- **Commit:** this one. **Tests:** `tests/test_wave2_scenario_map_field.py` (16).
  MUTATION-VERIFIED: skipping the staleness recompute fails the stale-map test.
- **Microfix (owner, binding):** the first cut left three fail-open shortcuts.
  (1) A plan node's `workpacket_id` was treated as PROOF a packet exists —
  `build_from_records` synthesized packet records from plan nodes. Removed: for
  every role the lineage must close on a REAL persisted WorkPacket record whose
  `source_evidence` names the node AND whose `packet_id == node.workpacket_id`
  (fails on ghost packet, mismatched lineage, id disagreement). (2) Run selection
  fell back to "latest plan" via a run-tag substring — a run could adopt
  another's plan. Removed: `select_plan` requires an EXACT `(plan_record_id,
  plan_version)`; zero or multiple matches fail. (3) The "authorized frontier"
  was "all packets I can find". Replaced by `resolve_authorized_frontier`, which
  reads the ONE ACTIVE execution-authorization grant's `task_frontier` for the
  exact plan version — no grant / multiple grants / non-ACTIVE / expired / empty
  frontier / wrong-version all fail closed, and an unrelated packet never enters
  the frontier. The map persists `execution_authorization_ref` but authority is
  REREAD from the canonical stores at arming — never delegated to the map. Field
  callers derive the exact plan+authorization from the single ACTIVE grant in
  candidate state; the all-packets `_authorized_frontier` helper is deleted.
- **FINAL run-binding microfix (owner, binding):** the prior cut still resolved
  the target through "the ONE ACTIVE grant in all candidate state" — NOT a run
  binding. A legitimate ACTIVE grant left by a prior/parallel run breaks it (0 or
  2 matches), and it discarded identifiers already on `ExecutionAuthorizationGrant`
  (grant_id, decision_ref, conversation_id, correlation_id, tenant/principal/
  membership). Fixed in five parts:
  (1) **Capture the exact field-journey binding.** `write-scenario-map` now writes
  `<targets>/<run-id>/execution_binding.json` (identifiers + observed versions
  ONLY: run_id, candidate_sha, plan_record_id, plan_version, grant_id,
  decision_ref, tenant/principal/membership/conversation/correlation), populated
  from the grant THIS run's journey produced — matched by EXACT `correlation_id`
  (`w2-<run_id>`, stamped by the collector), never a blob substring
  (`run-1` ⊂ `opr-run-1`) and never "the only active grant".
  (2) **Deleted global-singleton inference.** `_active_grant_binding` is removed;
  `_capture_execution_binding` replaces it. Both `write-scenario-map` and
  `inject-failure` load `execution_binding.json`; other ACTIVE grants are
  irrelevant and never block the exact match.
  (3) **Centralized canonical grant resolution.** ONE resolver
  `resolve_canonical_grant(records, binding)` used by BOTH map writing and arming:
  requires exact match on all nine binding fields; status ACTIVE; not_before
  satisfied; not expired; non-empty task_frontier; the exact Plan version exists
  and is a live accepted version (not draft/rejected/cancelled/superseded); every
  frontier id a persisted canonical WorkPacket of that Plan and tenant. No second
  weaker preselection helper.
  (4) **The map's authorization binding is REAL, not asserted.** The digest now
  covers the full binding (`binding_digest`). At arming, `validate_against_run`
  rereads `execution_binding.json` + the canonical grant, requires persisted
  `execution_authorization_ref == grant.decision_ref` and persisted
  `grant_id == grant.grant_id`, recomputes the binding digest, and rejects any
  mismatch — authority is never delegated to the map.
  (5) **Tests A–N** (`tests/test_wave2_scenario_map_field.py`, 48): two unrelated
  ACTIVE grants → exact selection; prior-pass grant doesn't shadow; other tenant /
  wrong conversation / correlation / grant_id / tampered ref / missing binding /
  duplicate exact binding / non-ACTIVE / expired / not-yet-valid / draft-or-
  superseded plan / frontier packet outside plan or tenant — all fail closed.
  MUTATION-VERIFIED: restoring "the only active grant" selection kills B/C/D/E/F;
  dropping the decision_ref comparison kills the tampered-ref test; a static
  build-time `binding_digest` kills the persisted-content-digest test.
- **CLOSURE CORRECTION (owner, binding):** three discrepancies still blocked
  truthful closure. All prior exact-run-binding work is preserved.
  (1) **`resolve_canonical_grant` is now the ACTUAL single authority for map
  creation.** `build_from_records` previously captured a binding and built the
  payload WITHOUT calling the resolver — contradicting the "same resolver governs
  writing and arming" invariant. It now calls
  `resolve_canonical_grant(records, binding, now=now)` BEFORE producing any
  payload, so map creation fails closed on zero/multiple exact grants, non-ACTIVE
  status, unmet not_before, elapsed expires_at, empty frontier, absent/non-live
  Plan version, and any invalid first-class frontier ownership. No second reduced
  validator: an expired or not-yet-valid grant cannot even produce
  `scenario_map.json` (proven by `test_corr_B`/`test_corr_C`, not merely later
  arming rejection).
  (2) **Packet ownership validated through FIRST-CLASS contracts.** WorkPacket has
  no canonical top-level `tenant_id`; the permissive `packet.get("tenant_id")` +
  empty-value handling is replaced by `_validate_frontier_packet_ownership`, which
  reads the authoritative fields: `work_scope.tenant_id` (non-empty AND ==
  grant.tenant_id), `lineage.plan_record_id` == grant.plan_record_id,
  `lineage.objective_id` == Plan.objective_id, `packet_id` ∈ Plan.workpacket_ids,
  exactly one corresponding Plan node whose `workpacket_id` == packet_id, and
  `source_evidence` resolving to that same node. Missing scope, missing lineage,
  empty tenant, a fake top-level tenant_id, absent node correspondence, or any
  mismatch fails closed (`test_corr_D`–`test_corr_L`).
  (3) **Removed the non-canonical `run_tag` match escape.**
  `_capture_execution_binding` now selects ONLY on the exact canonical
  `correlation_id` (`w2-<run_id>`); the `run_tag`/base-tag (pre-`-p`) fallback is
  gone — `run_tag` is not part of the grant identity contract. Test fixtures
  populate `correlation_id`, not `run_tag`. Proven by
  `test_M_capture_rejects_run_tag_and_base_tag_selection`.
  Suite now 61 tests. MUTATION-VERIFIED: removing the resolver call from map
  creation kills corr_A/B/C; honoring a fake top-level tenant kills corr_E;
  restoring run_tag/base-tag selection kills the capture-rejection test.
- **FINAL fail-closed microfix (owner, binding):** three residual fail-open
  conditions in `resolve_canonical_grant`, all preserving the C-3 architecture.
  (1) **Exact APPROVED plan status — allowlist, not denylist.** The denylist
  (`_PLAN_NONLIVE = {draft,rejected,cancelled,superseded}`) let AWAITING_APPROVAL
  and unknown/malformed statuses pass as "live accepted". Replaced with
  `plan_status != ObjectivePlanStatus.APPROVED.value` (imported from the canonical
  planning-records home — no duplicated literal). `awaiting_approval`, empty, and
  unknown statuses now all fail closed.
  (2) **Nonempty exact Plan materialization set.** The old
  `if plan_packet_ids and tid not in ...` failed open when `workpacket_ids` was
  absent/empty. New `_validate_plan_materialization_set` requires
  `workpacket_ids` to be a list, nonempty, with unique nonempty ids, each
  resolving to exactly one persisted canonical WorkPacket of the same Plan+tenant;
  the frontier-membership check is now UNCONDITIONAL. The set is NEVER inferred
  from nodes (correspondence records) — `ObjectivePlanRecord.workpacket_ids` is
  the first-class materialization record.
  (3) **Nonempty canonical objective identity.** Before comparing, `plan.objective_id`,
  `grant.plan_record_id`, `lineage.objective_id`, and `lineage.plan_record_id`
  must ALL be nonempty — equality of two empty strings is never valid
  correspondence.
  Suite now 80 tests. MUTATION-VERIFIED: restoring the denylist kills the
  non-APPROVED status cases; restoring `if plan_packet_ids and ...` (fail-open)
  kills the empty-set + unconditional-check tests; allowing empty-string objective
  correspondence kills the objective-identity tests.
- **IDENTITY-CARDINALITY microfix (owner, binding):** `_validate_plan_materialization_set`
  claimed "exactly one persisted WorkPacket per id" but `resolve_canonical_grant`
  first built a LOSSY `packets_by_id = {pid: packet for p in ...}` that collapsed
  duplicate packet_id records by record order (last-write-wins). The WorkPacket
  JSONL can carry multiple current-truth records with the same packet_id, so
  cardinality must be PROVEN before selecting.
  New `_index_packet_records` builds a cardinality-preserving
  `packet_id → [all records]` index; `_exactly_one_packet` enforces the exact-one
  rule (0 → fail, 1 → return, >1 → fail as canonical identity ambiguity). BOTH
  byte-identical and conflicting duplicates fail — a duplicate current-truth
  identity is corruption even when payloads match. Order-invariant (reversing
  duplicate rows yields the same rejection, never selects another record). The one
  resolved record is threaded forward (materialization → frontier ownership) so no
  downstream code rebuilds a lossy dict. Bounded to the ids this run trusts (Plan
  materialization set ∪ frontier); unrelated duplicates elsewhere do not block.
  `resolve_scenario_map`'s `by_node` tightened to reject ANY second record for a
  node_id (including byte-identical). Suite now 88 tests. MUTATION-VERIFIED:
  restoring the lossy comprehension makes the duplicate tests (C/D/E/F) stop
  failing and trips the AST guard (H).
- **Residual risk:** the end-to-end injection→A1-fail→C-blocked→A2-recover graph
  mechanics are proven in `test_failure_qualification_rehearsal` (no quota); the
  live field pass requires a candidate deploy (C7, owner-gated).

### C-4 — the verifier executes worker-authored code unconfined — **OPEN**

- **Root cause:** `_independent_checks_for` runs `pytest` with
  `cwd=<lease worktree>` via `gated_subprocess_run` — no `build_isolated_command`,
  no bwrap, no `scrub_worker_env`, full host environment.
- **Authority violated:** Amendment v1 clause 4; the entire R1 credential
  boundary.
- **Exploit path:** the worker's job is to write files in that worktree,
  including test modules. A `conftest.py` there is arbitrary Python that pytest
  imports and executes as the runner user with the runner's environment
  (including `CLAUDE_CODE_OAUTH_TOKEN`). The runner refuses to start without
  bwrap and then runs adversary-influenced code unconfined a few frames later.
- **Status:** OPEN — repair in progress (order §6).

### C-5 — `reconcile`/`teardown` exit 0 on failure — **OPEN**

- **Root cause:** `_result_declares_failure` checks
  `("deploy_ok","started","armed","ok","ready")`; `reconcile` returns
  `all_passed`, `teardown` returns no verdict key at all.
- **Authority violated:** readiness/verdict exit semantics (the SEC-C3 class from
  round 1), in the scoring command.
- **Failure path:** a reconciliation scoring 0.0 — or scoring **zero passes** —
  exits 0. A driver chaining `deploy → run → reconcile` by exit code treats a
  failed or empty reconciliation as success. `teardown` failing to shred the run
  secret also exits 0.
- **Status:** OPEN — repair in progress (order §7).

### SEC-C1 — teardown never destroys `worker-homes/`; residue assert is dead — **OPEN**

- **Root cause:** `assert_no_credential_residue` is defined, exported and tested
  but **called from nowhere in production**; `teardown()` contains zero
  references to `worker-homes`.
- **Authority violated:** credential lifetime (the incident this campaign opened
  with).
- **Exploit path:** `stop_runner` sends SIGTERM; the runner installs **no signal
  handler**, so the `finally:` that destroys the attempt home never runs and the
  operator's real OAuth credential survives on disk indefinitely. The cleanup
  guarantee holds only on the graceful path.
- **Status:** OPEN — repair in progress (order §8).

---

## Warnings from round 2 (non-critical, tracked)

W-1 double proof record; W-2 `reread_durable` substring fast-path; W-3 CPU-gate
fallback to worker self-report; W-4 concurrency test never exercises `run_loop`;
W-5 three independent `2` caps + CPU gate denies the second worker; W-6 Bash
revocation semantics; W-7 no VERIFYING recovery; W-8 nonce replay on recovery;
SEC-W1 finalization not idempotent; SEC-W2 dispatch secret unmatched by typed
patterns; SEC-W3 residue raise inside `finally` strands the claim; SEC-W4
`_safe_component` not injective; SEC-W5 launch log outside the evidence tree;
SEC-W6 over-redaction of URLs/base64; SEC-W7 memory read cost; SEC-W8 detached
manifest hash is not out-of-band.

Disposition recorded per item in `docs/wave2_repair_ledger.md` as each is closed.
