# Wave 2 — Proof-Inspector Canonical Runtime Source Correction

**Authorized by:** OWNER DECISION — "ACCEPT ROOT CAUSE. AUTHORIZE NARROW NON-FIELD
CORRECTION ONLY." (2026-08-08). NO field execution, NO quota consumption, NO reserve
use, NO redispatch. Invocation #53 preserved as consumed/not-qualified evidence and
is NOT reinterpreted as a candidate failure.

**Prior SHA (defective proof surface):** `83c56cb6d9782b60dc81aa019bcb9bb8a73bb2e0`
**Field defect that triggered this:** invocation #53, run `20260809T021413Z-p1`
(Pass 1, failure/recovery) — collector failed `w16_ab_running_concurrent` with
`concurrent_tasks=[]` despite a fully correct candidate A+B→C→D lifecycle
(composition proof `proof-d82a8aa751a1` durable at 02:18:06Z with
`predecessor_commits`, ~66s inside the w16 window).

---

## 1. Root cause (measured, zero-quota investigation)

Two proof persistence systems with divergent paths:

| System | Path resolution | In candidate container | Used by |
|---|---|---|---|
| `ProofStore` (`substrate/organism/proof_store.py`) | `UMH_ROOT/data/runtime/proof_packages.jsonl` | `/app/data/runtime/…` — **does not exist** (gitignored file on a read-only worktree mount) | proof-inspector cockpit routes (defective) |
| `ProofRuntime` (`substrate/organism/proof_runtime.py`) | `runtime_state_path("organism", "proof_packages.jsonl")` → `UMH_STATE_DIR/organism/proof_packages.jsonl` | `/state/umh/organism/…` — **all execution proofs land here** | poller, verifier, field control plane (canonical) |

Failing chain: collector `_identify_composition` → `_composition_proof` →
`GET /api/umh/proof-inspector/packages/{proof_id}` → `_get_proof_store()` →
`ProofStore()` loads 0 packages from the nonexistent legacy file → `get()` → None →
HTTP 404 → collector receives `{}` → no composition identified → 240s poll loop
repeats the same deterministic 404 → w16 FAIL (w17/w18 consequential).

Classification: **HARNESS DEFECT (cockpit API wiring)**. Candidate INNOCENT
(persisted attempt ledger proves the full A+B→C→D failure/recovery property with
~83s temporal overlap). Collector observation model INNOCENT in isolation. NOT an
external transient — NOT reserve-eligible. Introduced when commit `95a88fc99`
(w16/w17/w18 durable-history rewrite) added the `_composition_proof` →
proof-inspector dependency, assuming the proof-inspector served execution proofs.

Full analysis: `ROOT_CAUSE_ANALYSIS.md` (this dir). Pass 1 evidence:
`../2026-08-08_wave2_c6462dc25_pass1_failrec/` and preserved attempt ledger /
proof packages in `PASS1_EVIDENCE/` (this dir).

## 2. The correction (exact scope, post-review revision)

One source file: `transports/api/cockpit_proof_inspector_routes.py`.

- `_get_proof_store()` now returns `_CanonicalProofSource`. By-id reads
  (`get(proof_id)` — package detail/timeline/evidence/raw, the exact w16 read)
  consult a fresh `ProofRuntime` per call FIRST (re-reads the durable JSONL, so
  proofs written by other processes are visible without restart), falling back
  to the legacy `ProofStore` singleton. Both unavailable → None (unchanged 503
  semantics).
- **No writes on the read path:** the runtime store path is resolved with
  `runtime_state_path(..., create_parent=False)` and injected via
  `ProofRuntime(store_path=...)` — the default constructor mkdirs the state
  dir, and a failed mkdir would have silently degraded the source to
  legacy-only (the exact #53 failure shape). Degradation now logs at
  `warning`, never `debug`.
- **Exposure is deliberately asymmetric:** `query()`/`summary()` (listing,
  summary, artifacts) are pure legacy passthroughs — the two package classes
  have disjoint wire shapes (`status`/`created_at` vs `outcome`/`timestamp`)
  and merging them corrupts the cockpit panel (Invalid Date, unfilterable
  rows, irreconcilable totals). Runtime proofs resolve by id only.
- Review mutations (`approve`/`reject`) delegate to the legacy store ONLY —
  execution proofs are verifier-attested, immutable evidence, not
  operator-reviewed here (unchanged observable behavior: they 404'd before).
- `getattr` guards where by-id routes touched legacy-only package attributes
  (`evidence_dir`, `execution_id`, `browser_evidence`, `verification_results`)
  so runtime packages serialize without 500s.

NOT touched: candidate execution semantics, scheduler, poller, verifier,
lifecycle, composition, promotion, retention, field control plane, schemas,
collector, dispatch harness, any other cockpit route. `/packages`,
`/artifacts`, and `/summary` wire shapes are byte-identical to pre-fix
behavior.

### Pre-existing ProofRuntime debt recorded (out of this bounded scope)
- Torn-JSONL crash truncation: a crash-truncated line without trailing newline
  concatenates with the next record in `_load_from_disk`/`reread_durable`
  (concurrent writers are safe under `LOCK_EX`; bounded to crash-mid-write).
- Unbounded `_packages` growth: `_MAX_HISTORY=200` caps the history deque,
  not the dict (measured 3.58 ms/construct at 300 proofs — no field impact;
  needs a retention story before high-volume accumulation).

## 3. Qualification evidence

- **Behavioral tests:** `tests/test_wave2_proof_inspector_runtime_source.py` —
  11 tests, all green: runtime proof served by package detail (the exact w16
  read); candidate-container shape (read-only `UMH_ROOT`, no legacy file,
  `UMH_STATE_DIR` state dir) observes a real execution proof; cross-process
  visibility without restart; legacy-store fallback + approve path preserved;
  listing/summary remain legacy-only (panel wire-shape contract); runtime
  wins on proof_id collision (lookup-order pin, closes reviewer WARNING 5);
  read path serves the proof even with `Path.mkdir` forced to raise
  (root-proof, no chmod); read path creates zero directories;
  timeline/evidence/raw never 500 on runtime packages; missing proof still
  404; direct canonical-source assertion.
- **Mutation coverage (all killed, then restored byte-identical + re-verified green):**
  1. Route reverted to legacy ProofStore only → 7 test failures.
  2. Runtime source dropped (legacy-first equivalent) → 7 test failures.
  3. `evidence_dir` guard removed → 6 test failures.
  4. Default `ProofRuntime()` (mkdir on read path) reintroduced → 2 failures.
  5. Runtime proofs re-merged into `query()` (panel corruption) → 1 failure.
  6. `get()` lookup order inverted (legacy first) → 1 failure
     (round-2 reviewer's surviving M-C mutant, now killed).
- **Complete Wave 2 suite:** 1,822 passed / 3 skipped. The 16 FAILED + 26 ERROR
  are byte-identical to the baseline `83c56cb6d` failure set (verified by
  stash-diff): legacy `test_phase14_7a_wave2.py` / `test_phase14_8b_wave2.py`
  hardcode a removed worktree path (`.claude/worktrees/phase-14-7b-cockpit-usability`)
  — pre-existing environmental debt, zero regressions from this change.
- **Authoritative gates (all pass):** type divergence (+ `--registry-audit`:
  1,165 entries truthful), dependency direction, cpu gate, ontology homes,
  projection leak, instance leak, ontology layers, credential injection.
- **Independent review (two adversarial rounds + two verification rounds):**
  Round 1 eos-code-reviewer — REJECT (3 criticals: mkdir-on-read silent
  legacy revert; panel wire-shape corruption; summary vocabulary merge). All
  three fixed; the revision adopted the reviewer's own minimal option.
  Round 2 eos-code-reviewer — APPROVE-WITH-NOTES, "merge" recommendation;
  could not reproduce a post-fix w16 404 under any legitimate configuration;
  its one surviving mutant (lookup-order inversion) is now killed by a new
  test. eos-verifier — VERIFIED on both the original and revised correction
  (6/6 checks each round, including end-to-end simulation of the exact field
  failure shape and the mkdir-forbidden read). Full verdicts:
  `REVIEW_VERDICTS.md` (this dir).

## 4. Consequence for the campaign

This is a tracked source change → NEW exact SHA → the `83c56cb6d` campaign is
VOID per the Tracked Edit Stop Law. Invocation #53 remains consumed/not-qualified.
A new field authorization is required; all 4 mandatory passes (1 failure/recovery
+ 3 green) must run fresh at the new SHA. Another field invocation IS justified:
the defect was deterministic and structural (every field pass at `83c56cb6d`
would fail w16 identically), the candidate's execution properties are already
proven correct by the durable ledger, and only the observation path was broken.
