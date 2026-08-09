# w16 Root-Cause Analysis — Proof-Inspector / ProofRuntime Path Divergence

**Run:** `20260809T021413Z-p1` | **SHA:** `83c56cb6d` | **Invocation #53**
**Analysis:** zero-quota, non-destructive, zero edits

---

## Root Cause: HARNESS DEFECT (cockpit API wiring)

The proof-inspector API endpoint reads from the WRONG proof store.

### The two proof systems

| System | Class | Path resolution | Used by |
|---|---|---|---|
| **ProofStore** | `substrate.organism.proof_store.ProofStore` | `Path(UMH_ROOT) / "data" / "runtime" / "proof_packages.jsonl"` | Proof-inspector cockpit routes |
| **ProofRuntime** | `substrate.organism.proof_runtime.ProofRuntime` | `runtime_state_path("organism", "proof_packages.jsonl")` → `UMH_STATE_DIR / "organism" / "proof_packages.jsonl"` | Execution system (poller, verifier, field_control_plane) |

### Inside the candidate container

| Env var | Value | Mount |
|---|---|---|
| `UMH_ROOT` | `/app` | Worktree (READ-ONLY): `-v {worktree}:/app:ro` |
| `UMH_STATE_DIR` | `/state/umh` | State dir (READ-WRITE): `-v {state_dir}:/state/umh` |

- **ProofStore** reads from `/app/data/runtime/proof_packages.jsonl` — this file does NOT EXIST (it's in the read-only worktree mount, and `data/runtime/` is gitignored, so it was never tracked).
- **ProofRuntime** writes to `/state/umh/organism/proof_packages.jsonl` — this is where all execution proofs land.

### The failing collector chain

```
w16 entry
  → _identify_composition(page, attempts)
    → for each attempt with proof_id:
      → _composition_proof(page, proof_id)
        → _authed_get(page, "/api/umh/proof-inspector/packages/{proof_id}")
          → cockpit_proof_inspector_routes._package_detail()
            → _get_proof_store()
              → ProofStore()  ← reads from /app/data/runtime/proof_packages.jsonl
              → ProofStore._load() → file doesn't exist → 0 packages loaded
            → store.get(proof_id)
              → None  (empty store)
            → raise HTTPException(404, "Proof proof-d82a8aa751a1 not found")
          → HTTP 404
        → resp.__status == 404 ≠ 200
        → return {}
      → action == {}, predecessor_commits == None
      → isinstance(None, dict) is False → skip
    → return {}  (no composition found)
  → comp == {}, pred_tasks == set()
  → [240s polling loop: every 3s repeats the same failing lookup]
  → deadline expires
  → pred_tasks = []
  → ok = len([]) == 2 → False
  → FAIL: "concurrent_tasks=[] dispatched_overlap_s=0.0 both_dispatched=False execution_surface=False"
```

### Why execution_surface is also False

The `execution_surface` check (`page.locator('[data-testid="w2-execution-root"]').count() > 0`) is a secondary corroboration check. The `w2-execution-root` div is rendered by `ExecutionPanel.tsx` which mounts when the cockpit navigates to the execution route. If the Beast collector's Playwright page was still on the chat/plan approval view (from w15) and never navigated to execution, this would be False. However, this is a SECONDARY failure — even if `execution_surface` were True, the pass would still fail because `pred_tasks=[]`.

### Timeline proving data availability

| Time (UTC) | Event |
|---|---|
| 02:15:12 | Collector reaches w15 (driver detects) |
| 02:15:20 | Runner starts |
| 02:15:21 | A + B dispatched concurrently |
| 02:16:46 | B succeeded (`proof_id=proof-197cf0dcda78`), A failed |
| 02:16:47 | A retry dispatched |
| 02:18:04 | A retry succeeded (`proof_id=proof-2d4a8c860e3a`) |
| 02:18:04 | C (composition) created→ready→leased |
| 02:18:06 | C succeeded (`proof_id=proof-d82a8aa751a1`) |
| ~02:19:12 | w16 deadline (w15 + 240s) |

The composition proof existed from **02:18:06**, giving the collector **~66s** of remaining window. The data was available in `/state/umh/organism/proof_packages.jsonl`. The proof-inspector never looked there.

---

## Classification

**HARNESS DEFECT.** Specifically: cockpit API wiring defect.

- **Candidate:** INNOCENT. The execution lifecycle was correct (complete A+B→C→D failure/recovery property with temporal overlap, composition proof with predecessor_commits, and downstream dispatch).
- **Harness (collector):** INNOCENT in isolation. Its observation model is correct — it reads attempts (which work), then reads the proof via the proof-inspector API (which should work but doesn't due to the cockpit route wiring).
- **Harness (cockpit API):** DEFECTIVE. The proof-inspector routes use `ProofStore` (reads from `UMH_ROOT/data/runtime/`) instead of `ProofRuntime` (reads from `UMH_STATE_DIR/organism/`). This is not a Clerk auth issue, not a timing issue, not an external transient — it's a structural mismatch between two proof persistence systems that has existed since the proof-inspector routes were written.

**This is NOT reserve-eligible** — it's a code defect in the cockpit API layer.

---

## Reproduction

Deterministic. Any field pass using the current proof-inspector routes in a candidate container will fail to observe execution proofs, because the proof-inspector always reads from the wrong file.

To reproduce without a field invocation:
1. Start a candidate container with `UMH_ROOT=/app` and `UMH_STATE_DIR=/state/umh`
2. Write a proof via `ProofRuntime.create_direct()` → writes to `/state/umh/organism/proof_packages.jsonl`
3. GET `/api/umh/proof-inspector/packages/{proof_id}` → 404 (reads from `/app/data/runtime/proof_packages.jsonl` which doesn't exist)

---

## Whether collector semantics or cockpit API is wrong

**The cockpit API is wrong.** The collector's observation model is correct:
- `_read_attempts` reads from `ExecutionAttemptStore` which correctly uses `runtime_state_path` → `UMH_STATE_DIR` ✓
- `_composition_proof` reads from the proof-inspector API which INCORRECTLY uses `ProofStore` → `UMH_ROOT/data/runtime/` ✗

The proof-inspector was written for the organism-level `ProofStore` (a separate proof system), not for the execution-level `ProofRuntime`. When the w16/w17/w18 durable-history rewrite (commit `95a88fc99`) introduced the `_composition_proof` → proof-inspector dependency, it assumed the proof-inspector would serve execution proofs. That assumption was wrong.

---

## Smallest correction

**Option A (cockpit route fix):** Change `_get_proof_store()` in `cockpit_proof_inspector_routes.py` to read from `ProofRuntime` instead of (or in addition to) `ProofStore`:

```python
def _get_proof_store() -> Any:
    try:
        from substrate.organism.proof_runtime import ProofRuntime
        return ProofRuntime()  # Uses runtime_state_path → UMH_STATE_DIR
    except Exception:
        return None
```

This is the smallest change (1 import, 1 line). Both `ProofStore` and `ProofRuntime` expose `.get(proof_id)`, `.query()`, and `.to_dict()` — the route handler doesn't care which it gets. However, `ProofRuntime` returns `ProofPackage` from `proof_runtime` (different class from `proof_store.ProofPackage`), and `to_dict()` returns different fields. The route only calls `pkg.to_dict()`, `pkg.proof_id`, and `store.get(proof_id)` which both classes support.

**Option B (collector fix):** Change `_composition_proof` to read from the attempt-detail endpoint instead of the proof-inspector. The attempt-detail endpoint returns `proof_id` but NOT the proof's `action` (no `predecessor_commits`). This would require either:
- Adding `predecessor_commits` to the attempt-detail response (enlarges the API surface), or
- Adding `execution_kind` to `_attempt_row` and using that to identify the composition task (then extracting predecessor info from the attempt's own data rather than the proof)

Option B is more invasive. Option A is a 2-line fix.

**Option C (dual-store fallback):** Try `ProofRuntime` first, fall back to `ProofStore`:

```python
def _get_proof_store() -> Any:
    try:
        from substrate.organism.proof_runtime import ProofRuntime
        return ProofRuntime()
    except Exception:
        pass
    try:
        from substrate.organism.proof_store import get_proof_store
        return get_proof_store()
    except Exception:
        return None
```

This preserves backward compatibility for any non-execution proofs in `ProofStore`.

---

## Tests/mutations needed

1. **Unit test:** `test_proof_inspector_reads_from_runtime_state_dir` — set `UMH_STATE_DIR`, write a proof via `ProofRuntime.create_direct()`, then verify `GET /api/umh/proof-inspector/packages/{proof_id}` returns 200 with the proof data including `action.predecessor_commits`.

2. **Integration test:** `test_composition_proof_visible_in_candidate_container` — simulate the candidate container's env (`UMH_ROOT=/app`, `UMH_STATE_DIR=/state/umh`), write a composition proof with `predecessor_commits`, verify the proof-inspector endpoint returns it.

3. **Mutation:** Remove the `ProofRuntime` import from `_get_proof_store` → test 1 must fail.

---

## Whether another field invocation is justified

**YES** — once the proof-inspector fix is applied and committed (creating a new SHA). The defect is:
- Deterministic (not a transient)
- Structural (affects every field pass, not just this one)
- In the cockpit API wiring, not in the collector or candidate
- A 2-line fix with a clear, testable correction

The new SHA voids the current campaign per the Tracked Edit Stop Law, so a new authorization is required. However, the fix is small, well-understood, and the candidate's execution properties are proven correct by the persisted ledger — only the observation path was broken.
