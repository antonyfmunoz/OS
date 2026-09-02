# Independent Review Verdicts — Collector Observation Correction (w16/w26/w27)

Two adversarial rounds by a fresh eos-code-reviewer instance against the live
uncommitted worktree on top of `842434dc3fa3ed16540673f5df48950ccf6a2674`.
Every finding verified by execution; the reviewer ran its own mutants rather
than trusting the reported sweep; tree verified restored byte-identical after
every mutation.

## Round 1 — REJECT (2 blockers, 4 warnings)

1. **BLOCKER — w26 structurally unpassable.** The same-thread completion
   report is a capability the candidate does not implement: no producer emits
   `execution_state='complete'`; nothing posts a report message; 3 of the 4
   old text markers could never match the UI string
   (`ChatExecutionCard.tsx` renders `EXECUTION COMPLETE — PROOF ATTACHED`
   only for a state nothing sets); the scan failed in 100% of recorded runs
   (#52, #54). The round-1 correction fixed w26's timing but kept the report
   gate → converted a fast false-negative into a slow false-negative that
   would consume another mandatory quota unit.
2. **BLOCKER — unguarded `.click()` in w27's poll loop.** AttemptsView
   repolls every 4s; a count-then-click straddling a re-render raises on a
   detached node, and the only handler re-raises — aborting the entire
   journey (losing w28–w30) on a transient.
3. Warnings: `_last_nav_error` written but never initialized/surfaced;
   D-identification exclusion untested (reviewer's mutant survived);
   `d_status` last-row-wins made a retried D order-dependent; w27's
   strengthened predicate untested.

Independently re-verified by the coordinator before acting: full-tree grep
confirmed no completion-report producer; recorded runs confirmed w26 never
passed.

## Resolution applied

- w26 GATE = bounded semantic wait on durable ledger evidence for the
  verification task(s) to terminalize succeeded+proof — the mechanism the
  owner's directive specified verbatim. Highest-attempt-number decides;
  zero-candidate graphs fail fast; timeout/failed/cancelled/proofless fail
  closed. Report scan retained as loudly-labeled NON-GATING corroboration
  (markers corrected to the real UI string and pinned against the TSX by
  test).
- w27 click guarded (retry-in-loop; `opened` set only on success).
- `_last_nav_error` initialized and surfaced as `nav_err=…` in w16/w27
  details.
- 6 new tests (exclusion pin, fast-fail, retry-ordering four-cell matrix,
  stale-DOM, click-retry, marker fidelity); mutation sweep extended to 11.

## Round 2 — APPROVE-WITH-NOTES

- Both blockers confirmed CLOSED by the reviewer's own mutants: exclusion
  mutant 2 failures; last-row-wins 1; click-guard removal reproduces the
  exact journey-aborting exception and is killed; UI-drift mutant (editing
  the TSX string) killed — a real anti-drift pin; gate-neuter (`d_ok=True`)
  3 failures.
- w27 predicate mutant verified GENUINELY EQUIVALENT by dataflow (conjuncts
  sampled only inside the on_surface→opened guards); honest documentation
  accepted as the correct disposition.
- No remaining false-negative (correct run failing) or false-positive
  (broken run passing) constructed. Worst-case runtime +560s, ~14 min
  inside the driver's 1800s poll budget.
- Regression baseline byte-identical; +22 net tests.
- **THE NOTE (governance, blocks commit):**
  `docs/wave2_field_qualification_runbook.md:119-124` lists w26 as a STRICT
  same-thread-report gate. The correction redefines what w26 asserts, and
  after it NO stage verifies same-thread reporting (the capability does not
  exist to verify). Whether the owner's directive intended to amend the
  STRICT bar is the owner's call: **do not commit until the owner confirms
  the w26 semantic change and the runbook is updated to match.** Optional:
  rename the stage so its name matches its assertion.

Status: code approved; commit withheld pending the owner's w26 ruling.

## Final fresh review pair (owner-ruled implementation)

**Reviewer A (adversarial) — APPROVE-WITH-NOTES.**
- PRIMARY: "Does the corrected w26 prove the actual Wave 2 Task-D
  verification requirement without relying on a completion-report capability
  the candidate does not implement?" → **YES** (verified empirically: every
  conjunct mapped to a real durable field against the preserved #54 records;
  the report-capability absence re-confirmed at source).
- SECONDARY: "Can final graph success, stale UI text, or a foreign/missing
  Proof falsely satisfy w26?" → **NO** (seven hostile probes all refused:
  stale-run correlation, source-mutating D, foreign proof wrong-lease,
  foreign proof wrong-plan, empty-base vacuous match, foreign candidate
  path, foreign run path; stale UI text never enters d_ok).
- Ran 12 of its own mutants: 10 killed; 1 equivalent (w27 predicate —
  dataflow-verified, disposition accepted); 1 SURVIVOR: the proof→lease
  binding conjunct was untested. **Closed post-review:**
  `test_w26_proof_binds_foreign_lease_fails` added; the mutant now fails
  1 test (verified), full suite restored green.
- Minor notes applied: `_last_nav_error` cleared per navigation attempt;
  forward-guard comment on the diff-scope enforcement check; evidence
  provenance note added to CORRECTION.md.
- Integrity: collector md5 identical before/after all reviewer mutation
  work; zero candidate/substrate/cockpit changes confirmed.

**Reviewer B (verification) — VERIFIED.**
- 58/58 collector tests; 3/3 exact-#54 reconstructions with premises
  independently confirmed against the raw JSONL (composed base
  `530b4b2745…` linkage; real correlation id; enforcement dict; verifier
  transitions on all real succeeded attempts).
- 2 self-chosen mutants (composed_base, proof_bound) both killed;
  byte-identical restore.
- Full wave2 suite: 1,857 passed; failure set confined to pre-existing
  phase14 files. Gates pass. Git state exact. Runbook matches code exactly.
- PRIMARY → **YES**; SECONDARY → **NO** (same grounds, independently derived).

Both reviewers answered the owner's questions as required. No Critical or
Wave-2-blocking High remains.
