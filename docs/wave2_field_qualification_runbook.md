# Wave 2 — Session-1 Field Qualification Runbook

The Wave 2 slice is built and deterministically qualified, and the **field
harness itself is built and proven runnable** (no Claude quota spent). This
runbook is the exact, executable procedure for the LIVE Session-1 field
qualification. Every script it references **exists in this branch** — nothing
below is "future work."

## Built and proven (no owner resources, no quota)

Run the single self-check to reproduce all of this on the VPS:

```bash
python3 scripts/wave2_harness_selfcheck.py
```

Current result on the orchestrator: **8 PASS / 0 FAIL / 1 OWNER_GATED →
harness_runnable=True**. Each mechanic:

| Mechanic | Proof | State |
|---|---|---|
| Enforced host isolation | `bwrap 0.9.0` hides `/opt/OS` from the worker mount namespace; env scrub strips all creds | PASS |
| Fixture app | `infra/fixture/make_fixture_app.py` → green FastAPI+JS+pytest (6 tests) + A/B/C/D objective | PASS |
| Signed dispatch spool | delivery + tampered-signature quarantine (`substrate/execution/attempts/spool.py`) | PASS |
| Control-plane rehearsal | full A/B→C→D graph via REAL scheduler + spool + poller + stub worker (`tests/test_wave2_harness_rehearsal.py`, `test_wave2_control_plane_poller.py`) | PASS |
| Dispatcher command assembly | all 9 subcommands assemble under `--dry-run` | PASS |
| Run-scoped secret | mint → 0600 → 64-hex → idempotent → shred | PASS |
| Clerk origin | candidate origin resolves via tailnet DNS — **reuses the Wave-1 dev Clerk instance + JWKS, no reprovisioning** | PASS (READY) |
| Beast executor | `windows-desktop` (100.74.199.102) active on the tailnet | PASS (READY) |
| OAuth token | resolved by the host runner at worker-invocation time from its CC ancestor | verify at `start-runner` |

**HARNESS_REHEARSAL_ONLY — REAL_WORKER_QUALIFICATION_NOT_SATISFIED.** A green
self-check proves the harness runs; it is NOT a Session-1 field pass (no real
worker, no candidate deploy, no visible Chrome).

## The field harness (all built)

- `scripts/wave2_field_dispatch.py` — VPS orchestrator. Subcommands:
  `preflight | deploy-candidate | seed-fixture | start-runner | smoke | run |
  inject-failure | reconcile | teardown`. Derived from the wave1 dispatcher
  (inherits network/origin resolution, Caddy/443 avoidance, redaction, crash
  handlers, reconcile ≥0.90). Candidate: `os-operator-candidate-w2` /
  `os-nginx-candidate-w2`, ports 8291/8290, TLS 10443, state
  `/var/lib/umh/candidates/wave2/<sha>`, fixture targets
  `.../targets/<run-id>/`.
- `scripts/wave2_field_collector.py` — executor-side, VISIBLE Chrome, 30-step
  journey w01–w30 (below). Stage-0 session proof hard-fails off Session 1.
- `scripts/wave2_fixture_browser_probe.py` — executor-side independent
  visible-Chrome witness that the fixture note-search works (types "alpha",
  waits on `/api/notes/search`, asserts results render).
- `scripts/wave2_attempt_runner.py` — run-scoped host attempt runner (bwrap
  isolation preflight → claim signed dispatch → real Claude-CLI worker in the
  lease worktree → signed outbox result).
- `substrate/execution/attempts/poller.py` — control-plane poller: drains the
  outbox and advances the CANONICAL ledger dispatched→running→verifying→
  succeeded|failed, then re-runs one scheduler pass.

## Run-scoped secret model (no manual provisioning)

`UMH_W2_DISPATCH_SECRET` is **ephemeral run-scoped state**, not a production
secret and NOT in the candidate env allowlist. `start-runner` mints it to a 0600
file (`<state>/.w2_dispatch_secret`, 64 hex), sources it into the host runner's
env via `$(cat …)` (never a CLI arg / log / evidence / model context), and
`teardown` SHREDS it. The owner never creates or stores it.

## Prerequisites (the real owner gate — see the preflight table in the PR)

Everything the harness needs already works EXCEPT the one true cost gate:

1. **Real Claude Code subscription quota** for the worker invocations (the only
   owner authorization required — see "Cost gate" below).
2. OAuth token resolvable to the host runner (verified live at `start-runner`;
   resolved from the runner's CC ancestor).

Clerk origin, candidate secrets (allowlisted, no dispatch secret), Beast, and
Tailscale are READY — do not reprovision them.

## The exact run sequence

```bash
SHA=$(git -C <worktree> rev-parse --short=12 HEAD)
RUN=$(date -u +%Y%m%dT%H%M%SZ)

python3 scripts/wave2_harness_selfcheck.py                 # gate: harness_runnable
python3 scripts/wave2_field_dispatch.py preflight
python3 scripts/wave2_field_dispatch.py --sha $SHA deploy-candidate
python3 scripts/wave2_field_dispatch.py --sha $SHA --run-id $RUN --variant clean seed-fixture
python3 scripts/wave2_field_dispatch.py --sha $SHA --run-id $RUN start-runner
# smoke (abbreviated) → failure-qualification → 3 green passes:
python3 scripts/wave2_field_dispatch.py --sha $SHA smoke
python3 scripts/wave2_field_dispatch.py --sha $SHA --run-id ${RUN}-fq --variant tools-revoked-a inject-failure
python3 scripts/wave2_field_dispatch.py --sha $SHA --passes 3 run
python3 scripts/wave2_field_dispatch.py --sha $SHA reconcile
python3 scripts/wave2_field_dispatch.py --sha $SHA --run-id $RUN teardown   # shreds the run secret
```

## The 30-step Session-1 journey (per pass) → shipped w2-* testids

`scripts/wave2_field_collector.py` methods `_w01`…`_w30`:

w01 session-1 + single-daemon proof · w02 fresh candidate + fixture, ZERO
attempts · w03 Clerk auth · w04 principal/tenant · w05 type the fixture
note-search objective · w06 plan compiles (`wg-plan-root`) · w07 inspect plan
(`wg-work-detail`) · w08 Tasks A–D non-executable (plan grants zero execution
authority) · w09 approve PLAN via HUD (`wg-approve-btn`) · w10 banner
`PLAN APPROVED — EXECUTION NOT STARTED` + zero attempts · w11 type "Execute the
approved plan" · w12 chat surfaces the decision (`w2-exec-card-root`,
status-only, no authorize control), NO execution · w13 prove zero attempts +
pending (not approved) authorization · w14 HUD execution row
(`w2-execution-decision` / `wg-approval-row[data-source-type="execution_authorization"]`)
· w15 authorize (`w2-exec-approve-btn`) · **w16** A+B RUNNING concurrently (two
`w2-execution-attempt[data-status="running"]`, distinct task ids) · **w17** C
blocked (no C attempt running/succeeded while A,B run) · **w18** A,B succeeded
with `w2-proof-link` (AttemptProof) · **w19** C reconverges only AFTER both
verified · w20 preview live *(non-gating — reconcile-owned)* · w21 D distinct
verifier role · w22 D browser probe *(non-gating — Beast-probe-owned)* · w23
collector's own visible-Chrome fixture witness *(non-gating — needs
`--fixture-url`)* · **w24** Proof (`w2-proof-link`, PlanExecutionProof) · **w25**
tasks complete only after Proof · **w26** Task D terminal VERIFIED — the full
bound verification chain from durable canonical evidence (exact run-bound D
attempt · candidate+run path binding · C's exact composed base consumed ·
authenticated zero-write verifier executed · Attempt-bound Proof · terminal
success; any wrong/missing element fails closed; see the qualification-contract
correction below) · w27 Work Detail lineage (explicit `?panel=execution`
navigation → `w2-assignment`/`w2-environment-lease`/`w2-verification-status`) ·
w28 refresh + full Chrome restart persistence · w29 zero prod deploy +
`/opt/OS` unchanged + no secrets *(non-gating — reconcile-owned)* · w30 cleanup.

Load-bearing execution-semantics gates (STRICT): w16, w17, w18, w19, w24, w25,
w26 (+ w01–w15, w21, w27, w28).

### Qualification-contract correction — w26 (owner ruling 2026-08-09)

- **Old requirement:** "same-thread report in the ORIGINAL conversation" — a
  STRICT gate asserting a completion report is posted back to the driving
  conversation thread, checked by scanning the rendered page body for report
  text.
- **Why it was impossible/stale:** the candidate does not implement the
  capability. Measured evidence (inv #54 correction cycle, independently
  verified by two review passes): no producer anywhere in the tree emits
  `execution_state='complete'`; nothing posts a completion-report message to
  a conversation; the cockpit's only completion string
  (`ChatExecutionCard` `EXECUTION COMPLETE — PROOF ATTACHED`) renders solely
  for a state nothing sets; three of the stage's four historical text
  markers could never match that string; and the stage failed in 100% of
  recorded field runs (#52 `20260808T233546Z-p1`, #54 `20260809T144154Z-p1`)
  including runs whose governed execution property completed correctly.
- **New authoritative w26 semantic:** `w26_task_d_terminal_verified` — Task D
  reaches the required terminal VERIFIED outcome, proven from durable
  canonical execution evidence: (1) the exact run-bound D attempt (task
  outside the concurrent pair and the composition task; highest
  `attempt_number` decides) terminalizes SUCCEEDED with a Proof inside the
  proven latency envelope; (2) `correlation_id == w2-<run_id>`; (3) the
  lease's read-only `source_ref.repo_root` lies under
  `<candidate_sha>/targets/<run_id>/`; (4) `source_ref.base_commit` equals
  Task C's `composed_commit` from the composition Proof; (5) a
  verifying→succeeded transition by a `verifier:*` actor with a Proof-recorded
  verifier identity distinct from the worker identity; (6) the Proof's action
  binds this `attempt_id`/`task_id`/`plan_record_id`/`lease_id`; (7) the
  lease's `diff_scope_post_hoc` enforcement is `enforced` and the succeeded
  attempt reports zero `files_changed`/`commits`. Timeout, failure, missing
  or foreign Proof, wrong base, foreign run, unauthenticated zero-write, or
  source mutation all fail closed.
- **Exact durable evidence used:** by-plan attempt rows + attempt-detail
  (transitions, assignment, environment lease with `source_ref` and
  `enforcement`, `files_changed`, `commits`, `correlation_id`) +
  proof-inspector Proof action (canonical `ProofRuntime` source) + the w16
  composition anchor.
- **Same-thread reporting:** deferred capability. If still desired, it
  belongs to later cockpit / operator-experience roadmap work — Wave 2 must
  not absorb new UI/product features because an obsolete qualification gate
  named them. The collector retains the report scan as NON-GATING
  corroboration, explicitly labeled "capability not yet implemented by
  candidate"; re-gate it only when a producer ships.

## Qualification bar (the authoritative bar)

- 1 smoke pass (abbreviated) + 1 failure-qualification pass
  (`inject-failure --variant tools-revoked-a`: A1's tool policy revokes
  Edit/Write → the real worker genuinely cannot commit → verification refuses →
  C stays blocked, no false Proof → retry from `w2-execution-retry` → A2 without
  revocation → the graph continues) + **3 consecutive full green passes**.
- reconciliation ≥ 0.90; zero orphan 5xx; zero duplicate active attempts;
  exactly-2 concurrency (A/B overlap); zero attempts before authorization
  `decided_at`; C.started > max(A,B verified); exact commit binding; Proof before
  completion; zero unredacted secrets in evidence; `/opt/OS` HEAD unchanged;
  sandboxes cleaned; Tailscale serve restored; zero production deploy (no
  `FLY_`/`GH_` key in any env audit).
- Heavy evidence gitignored under `/var/lib/umh/candidates/wave2/<sha>/` +
  sha256s in a committed manifest.

## Cost gate (STOP here before the first real worker)

Before any real Claude worker runs, the harness stops and reports the exact
parameters (candidate SHA, max invocations, max turns, timeout, retries,
parallelism, cost_status) and the exact owner authorization sentence. See the PR
body's cost-gate section. Do NOT consume quota before explicit owner
authorization.

## After qualification

Regenerate `scripts/wave2_matrix_report.py` (field rows → FIELD_QUALIFIED),
update the PR with the 3 pass IDs + reconciliation scores + Proof manifest, run
the adversarial divergence review (§XVI), and only then mark the PR ready.
**Do not merge. Do not deploy production.**
