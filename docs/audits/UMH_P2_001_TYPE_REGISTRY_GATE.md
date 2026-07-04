# WP-P2-001 — Harden the Canonical Type Registry + Divergence Gate

**Branch:** `fix/p2-001-canonical-type-registry` off `origin/main @ 566771265` (contains all P0 + P1-001 + P1-007).
**Risk:** MEDIUM (gate/registry infrastructure; no runtime behavior, no projection behavior).
**Mandate:** make the registry and its gate *truthful, exhaustive, and fail-closed*. Do not grandfather fresh divergence; exemptions shrink or get stricter, never expand casually. No disabling/widening gates to make tests pass.

Verified against the live tree by recon + independent measurement. All counts are ground-truth at `566771265`.

---

## 1. Before-state (measured, not asserted)

| Metric | Value |
|---|---|
| Registry literal entries written | 1051 |
| Distinct keys surviving (dict collapses dups) | **1041** |
| **Duplicate keys silently dropped** | **10** (first canonical location lost) |
| Entries resolving to a real symbol | 1038 |
| **Stale entries (symbol missing)** | **3** — `EnvironmentPacket{Status,RiskLevel,ExecutionTarget}` |
| `LEGACY_DUPLICATES` exemptions | 21 (16 modules) |
| **Dead exemptions (symbol/module missing)** | **3** — `foundation.primitives` (module gone), `next_action_engine.ActionResult`, `extraction.ActionCategory` |
| Registered-name shadow divergences (`--all` on main) | **46 BLOCKED** across 41 names |
| Same-name public collisions under `substrate/` | 128 names / 100 unaccounted |
| Dedicated test `tests/test_type_divergence.py` | **4 failed, 12 passed** (pre-existing red) |

### Root causes
- **3 stale entries + 3 test failures**: a botched rename doubled the prefix in `nodes/environments/work_packet.py` → real classes are `EnvironmentEnvironmentPacket{Status,RiskLevel,ExecutionTarget}` (`:19,32,39`); the registry names them `EnvironmentPacket*` and the test/doc still say `WorkPacket*`. Registry, source, doc, test all disagree.
- **3 dead exemptions**: grandfathered symbols that no longer exist — mask nothing.
- **10 duplicate keys**: real homonyms recorded as single-location twice; the dict collapses them, losing the first canonical location.

### The gate's real gaps (confirmed firsthand)
1. **No symbol-resolution check** — never verifies a registry entry resolves to a real symbol. The 3 stale entries are invisible.
2. **No duplicate-key detection** — the runtime dict has already collapsed the 10 dup keys; only an AST read of the source literal can see them.
3. **Exemptions unvalidated + metadata-less** — `LEGACY_DUPLICATES: dict[str, set[str]]` carries no owner/sunset/rationale, never checked to resolve. Fresh divergence can be grandfathered by adding a name.
4. **Scope bugs neutralize full-scan**: `_get_all_python_files` hard-codes `root = Path("/opt/OS")` (never the worktree) and `_EXCLUDES` contains `".claude/worktrees"` — divergence inside a worktree passes silently.
5. **`main()` returns 0 on empty file list** — a `--all` that resolves to zero files false-passes.

---

## 2. Scope decision (honest, respects constraints)

The 46 registered-name shadows + ~100 unregistered homonyms are **accumulated historical debt**, not something WP-P2-001 converges (that means editing 100+ files across every layer — follow-on convergence work; explodes blast radius; violates "no file moves/deletes unless the packet requires it"). This packet makes the gate **capable and truthful** so *new* drift is caught, and fixes the *clean* truthfulness defects.

**IN scope:**
- New fail-closed `--registry-audit` mode: symbol-resolution verification, duplicate-key detection, exemption-metadata validation.
- Fix the worktree-exclusion + hard-coded-path scope bugs so `--all` scans the actual working tree.
- Fix `main()` empty-list false-pass.
- Fix the 3 stale registry entries (registry follows the real source symbol names — no source rename here).
- Remove the 3 dead exemptions.
- Resolve the 10 duplicate keys to explicit homonym form `[modA, modB]`.
- Migrate `LEGACY_DUPLICATES` to metadata-carrying form (owner/sunset/rationale) + back-compat accessor.
- Update `.claude/rules/type-coherence.md` (the "~80 types" lie; stale `WorkPacket*` names).
- Fix the 4 red assertions in `tests/test_type_divergence.py`; add negative-control tests for every new check.

**OUT of scope (documented, not silenced):**
- Converging the 46 registered shadows + ~100 unregistered homonyms. Enumerated in a tracked debt ledger (`data/audits/2026-07-04_type_divergence_ledger.md`) so they are visible and non-expanding. The `--all` name-shadow scan stays available (exits 1 on the 46) but is NOT wired into the blocking pre-commit path in this packet (that requires the convergence work). The pre-commit path keeps its current staged scope (no regression); the new `--registry-audit` truthfulness checks are what this packet makes fail-closed and green.

Nothing is disabled or widened; the exemption list SHRINKS (21→18) and gains required metadata.

---

## 3. Implementation

### 3.1 `substrate/canonical_types.py`
- Fix 3 stale entries → register the actual symbol names (`EnvironmentEnvironmentPacket*`), drop the phantom `EnvironmentPacket*` keys.
- Resolve 10 duplicate keys → single homonym entry each with `[moduleA, moduleB]`.
- Migrate `LEGACY_DUPLICATES` → `dict[str, dict[str, dict]]` `{module: {name: {owner, sunset, rationale}}}`; add `legacy_names_for(module) -> set[str]` back-compat accessor. Remove 3 dead exemptions.

### 3.2 `scripts/check_type_divergence.py`
- `verify_registry_truthful() -> list[str]`: (a) every registry entry resolves to a real symbol; (b) no duplicate keys in the source literal (AST); (c) every exemption module+name resolves and carries owner/sunset/rationale with non-past sunset.
- `--registry-audit` mode calling it; non-zero on any failure; no early-return on empty file list.
- Fix `_get_all_python_files`: root from `git rev-parse --show-toplevel`; stop excluding the current worktree.

### 3.3 tests
- `tests/test_type_divergence.py`: fix the 4 stale assertions.
- `tests/test_registry_truthfulness.py`: negative controls — audit FAILS on (missing-symbol entry / missing-symbol exemption / metadata-less exemption / duplicate key) and PASSES on the corrected tree.

---

## 4. Proof
- Before/after registry counts (stale 3→0; exemptions 21→18 all resolving+metadata; dup keys 10→0).
- `--registry-audit` exits 0 on corrected tree; negative controls exit non-zero on injected divergence.
- All 9 global gates exit 0. `tests/test_type_divergence.py` green (4→0). No runtime/projection change.
