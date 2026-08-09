# Wave 2 — Collector Observation-Model Correction (w16 / w26 / w27)

**Authorized by:** OWNER DECISION — "ACCEPT INVOCATION #54 HARNESS-OBSERVATION
DEFECT … Authorize a narrow non-field correction cycle only." (2026-08-09).
NO field execution, NO quota consumption, NO reserve (none exists).

**Prior SHA (defective collector observation):** `842434dc3fa3ed16540673f5df48950ccf6a2674`
**Field defect that triggered this:** invocation #54, run `20260809T144154Z-p1`
(Pass 1 failure/recovery) — 33/36 stages green; failed w16/w26/w27 on a FULLY
CORRECT candidate run. Evidence: `PASS_P54_EVIDENCE/` (this dir).

## 1. What #54 proved (preserved as field evidence, per owner)

The complete governed A+B→C→D property at `842434dc3…`: A failed by injection
(verification refused, files=0), B succeeded concurrently (96.9s real
dispatched overlap), exactly one correctly-lineaged A retry succeeded, A+B
fanned into a real `control_plane_composition` attempt whose Proof binds BOTH
predecessor commits, predecessor commits were promoted/retained (teardown
released 2 trusted + 1 composed + 2 promoted refs), and D dispatched on C's
composed base. The proof-inspector correction (`f43a03b18`) is field-validated:
the collector identified the composition through the previously-404ing API.
**#54 does NOT count as a qualifying mandatory pass on any future SHA.**

## 2. Root cause — one defect class in three stages

Point-in-time live-UI checks evaluated when the checked surface could not be
present:

- **w16** counted `w2-execution-root` on whatever view the page was on; the
  collector never navigated to the execution panel (page sits on approvals
  after w15) → structurally False on every correct run since the `95a88fc99`
  w16 rewrite.
- **w26** scanned the body for Task D's completion report 4s after w25, while
  D was ~25s into a ~100-110s execution → the report could not exist yet.
- **w27** clicked a chat-card affordance from a non-hosting view and sampled
  the lineage drawer 1s later; the drawer (AttemptsView) lives on the
  execution panel and renders only after selecting an attempt row.

## 3. The correction (collector-side ONLY)

One source file: `scripts/wave2_field_collector.py`. Zero candidate,
substrate, or cockpit changes.

- **`_goto_panel()`** — explicit `?panel=<id>` deep-link navigation (the
  cockpit's single navigation authority: App.tsx → cockpitStore.setPanel) +
  bounded `wait_for_selector`; fails CLOSED on navigation error or mount
  timeout.
- **Latency-envelope constants** (observed in #54: 236s w15→composition;
  D ~100-110s): `PROVEN_WORKER_LATENCY_ENVELOPE_S=240`,
  `W16_COMPOSITION_WAIT_S=420` (was 240 — 4s of margin in #54),
  `W26_D_TERMINALIZE_WAIT_S=300`, `W27_DRAWER_WAIT_S=60`, and the
  non-gating `W26_REPORT_CORROBORATION_WAIT_S=20` (exempt from the
  envelope). Every gating timeout fails closed.
- **w16**: composition wait uses the envelope bound; `execution_surface` is
  now explicitly navigated (`_goto_panel(page, "execution",
  W2_EXECUTION_ROOT)`) — never sampled from a coincidental view.
- **w26 — RENAMED `w26_task_d_terminal_verified` (OWNER RULING 2026-08-09,
  Option 1):** the old STRICT "same-thread report" requirement was ruled
  stale/unimplementable — the candidate has NO completion-report producer
  (no `execution_state='complete'` emitter; nothing posts a report message;
  three of four old text markers could never match the UI string; the scan
  failed in 100% of recorded field runs #52/#54, including runs whose
  governed property completed correctly). The semantically false stage name
  was corrected per the ruling. The GATE is now the FULL BOUND verification
  chain from durable canonical evidence — final graph success alone is
  insufficient. Conjuncts (ALL required, each independently fail-closed):
  1. *terminalized* — every verification task (outside the concurrent pair
     and the composition task; deciding attempt = HIGHEST `attempt_number`)
     settles within the latency envelope; no-verification-task graphs fail
     immediately (no stall);
  2. *succeeded* — final attempt succeeded WITH a Proof id;
  3. *run_bound* — `correlation_id == w2-<run_id>` (foreign/stale-run
     evidence fails);
  4. *candidate_bound* — lease `source_ref.repo_root` under
     `<candidate_sha>/targets/<run_id>/`;
  5. *composed_base* — lease `source_ref.base_commit` equals Task C's
     `composed_commit` from the w16 composition anchor (verified against
     REAL #54 data: both are `530b4b2745…`);
  6. *verifier_ran* — verifying→succeeded transition by a `verifier:*`
     actor AND Proof-recorded verifier identity distinct from worker;
  7. *proof_bound* — Proof action binds this
     `attempt_id`/`task_id`/`plan_record_id`/`lease_id` (missing or foreign
     Proof fails);
  8. *zero_write* — lease `enforcement.diff_scope_post_hoc == 'enforced'`
     AND zero `files_changed`/`commits` (source mutation where forbidden
     fails; matches D's inspect-and-report-only contract,
     `FIXTURE_ALLOWED_PATHS[VERIFICATION] == []`).
  The report scan survives ONLY as non-gating corroboration, loudly labeled
  "capability not yet implemented by candidate", markers corrected to the
  real UI string and pinned against `ChatExecutionCard.tsx` by test.
  Same-thread reporting is a DEFERRED capability for later cockpit /
  operator-experience roadmap work — Wave 2 does not absorb it. The runbook
  carries the full qualification-contract correction record
  (`docs/wave2_field_qualification_runbook.md`).
- **w27**: navigate to the execution panel, wait for attempt rows, click a
  row (the drawer's real open affordance — guarded: AttemptsView repolls
  every 4s, so a detached-node click raise retries in-loop instead of
  aborting the whole journey), bounded-wait for the drawer's assignment +
  environment-lease + verification sections. `ok` now also requires
  `on_surface` and `opened` — STRICTLY STRONGER than before.
- **Diagnosability**: `_last_nav_error` initialized and surfaced as
  `nav_err=…` in w16/w27 detail strings whenever the surface is False — the
  next field failure distinguishes nav error from mount timeout from the
  detail alone.

Driver interaction verified: worst-case corrected collector runtime ≈ 990s,
under the driver's `_poll_status` 30-minute ceiling.

## 4. Qualification evidence

- **Regression tests** — `tests/test_wave2_collector_p54_observation.py`
  (NEW, 34 tests, fake clock — zero real sleeping; fake SPA page with real
  views + attempt-detail/lease/proof fabric mirroring the REAL persisted
  schemas): the owner-required scenarios — surface check from an unrelated
  page (THE #54 shape), Task D beyond the old observation window, lineage
  from a non-hosting panel, fast graph, slow-but-valid graph (composition at
  300s — beyond the old 240s bound), genuinely missing execution surface,
  genuine D non-terminalization, genuinely missing lineage — plus every
  bound-chain conjunct negative (wrong run, wrong candidate, wrong composed
  base, missing composition anchor, foreign Proof, missing Proof record,
  verifier-not-run, verifier==worker, source mutation, unauthenticated
  zero-write, success-without-proof), envelope contract, UI-marker fidelity
  (read from the real ChatExecutionCard.tsx), report-absence non-gating
  marker, D-identification exclusion, no-verification-task fast-fail,
  D-retry ordering (both row orders, pass and fail shapes), no-attempt-rows,
  unmountable-surface with nav_err, stale-DOM lineage, transient-click
  retry, **and three EXACT #54 RECONSTRUCTIONS driving the real corrected
  stages against the real preserved durable records** (w16 passes on real
  evidence with the real composed commit `530b4b2745…`; w26 fails closed on
  the frozen ledger where D is still dispatched; w26 passes when D's
  completion — what the bounded wait would have observed — is simulated on
  the REAL lease and proof schemas).
- **Harness contract update** — `tests/test_wave2_collector_history_observation.py`
  fake page now models the navigation contract (goto / wait_for_selector;
  `surface=0` = mount timeout). All 24 existing tests pass unchanged in
  intent.
- **Mutation sweep (final, on the bound-chain gate) — 11 mutants, ALL
  KILLED, zero non-equivalent survivors** (collector restored byte-identical
  after each; final 58/58 green): composed_base dropped (2 fail) · run
  binding dropped (1) · candidate binding dropped (1) · proof binding
  dropped (2) · verifier check dropped (2) · zero-write authentication
  dropped (1) · source-mutation check dropped (1) · gate neutered
  `d_ok=True` (14) · pair/composition exclusion dropped (7) · last-row-wins
  restored (1) · w16 skips-navigation regression (8) · w16 wait below
  envelope (2). Earlier-round sweeps (navigation/point-in-time/timeout-as-
  success/click-guard classes) also all killed. ONE equivalent mutant from
  round 2 (w27 `ok` predicate revert) — equivalence demonstrated
  behaviorally by dataflow (conjuncts sampled only inside the
  on_surface→opened guards, cannot alter any observable result), confirmed
  by the independent reviewer, disposition recorded here and in the test
  docstring per the owner's mutation-disposition rule.
- **Targeted collector suite:** 92 passed (all five collector test files).
- **Complete Wave 2 suite:** 1,857 passed / 3 skipped; the 16 FAILED + 26
  ERROR are byte-identical to the campaign baseline (pre-existing
  `test_phase14_*` environmental debt — hardcoded removed-worktree paths).
- **Gates:** all 8 authoritative gates + `--registry-audit` (1,165 entries)
  pass.
- **Independent review (four passes total):** round 1 adversarial — REJECT
  (two blockers: w26 structurally unpassable on the missing report
  capability; unguarded click race — both independently verified and
  resolved). Round 2 adversarial — APPROVE-WITH-NOTES ("merge"), governance
  note escalated to owner → OWNER RULING accepted Option 1 and specified the
  bound-chain semantic + rename + runbook correction implemented here.
  Final fresh review pair (Reviewer A adversarial / Reviewer B verification)
  on the ruled implementation: see `REVIEW_VERDICTS.md` (this dir).

## 5. Consequence

Tracked source change → NEW exact SHA. All 4 mandatory passes must run fresh
at the new SHA. Quota consumed stands at 54/57 with 3 units remaining — fewer
than the 4 mandatory passes require. **The ceiling decision is the owner's**;
no dispatch occurs without a new field-quota authorization.

## Evidence-file provenance note

`PASS_P54_EVIDENCE/environment_leases.jsonl` and
`execution_assignments.jsonl` were added to this record ~2h after the other
#54 evidence files, copied from the same candidate state dir
(`/var/lib/umh/candidates/wave2/842434dc3…/state/umh/operator/execution_attempts/`)
to back the exact-#54 reconstruction tests and the composed-base linkage
proof. Same run, same durable source — later copy time only.
