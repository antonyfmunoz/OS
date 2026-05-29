# Phase 9.2 — Trial Candidate Selection

## Selected Candidate

**Fix false-positive high-severity contradiction: governance_router reported MISSING**

The world model's `_extract_governance()` function checks for `substrate/control_plane/router.py`,
but the router is a Python package at `substrate/control_plane/router/` with an `__init__.py`.
This causes a false "capability_gap" contradiction at HIGH severity, inflating the contradiction
count and suppressing the governance readiness score.

## Evidence

1. **World model entity definition** (`substrate/organism/world_model.py:504`):
   ```python
   ("governance_router", "substrate/control_plane/router.py", "Signal lifecycle orchestration")
   ```
2. **Actual filesystem state**:
   - `substrate/control_plane/router.py` — does NOT exist
   - `substrate/control_plane/router/__init__.py` — EXISTS (operational package)
   - `substrate/control_plane/router/control_plane_router_v1.py` — EXISTS
   - `substrate/control_plane/router/intent_router.py` — EXISTS
   - `substrate/control_plane/router/router_contracts.py` — EXISTS
3. **Contradiction engine output** (contradiction #13):
   ```json
   {
     "type": "capability_gap",
     "severity": "high",
     "evidence": "Governance system missing",
     "recommended_fix": "Create or locate substrate.control_plane.router"
   }
   ```

## Why Selected

- **Highest-leverage safe target**: Eliminates the only HIGH-severity contradiction in the system.
- **Evidence-backed**: The world model extraction code, filesystem check, and contradiction engine
  output all confirm this is a stale path reference, not a missing capability.
- **LOW risk**: Single-line change in a data extraction function.
- **Fully reversible**: Revert the path string.
- **Immediately measurable**: Re-running the contradiction engine should show 12 contradictions
  (down from 13), with zero HIGH-severity contradictions remaining.
- **No security impact**: This changes self-observation accuracy, not execution behavior.
- **No deployment change**: No containers, no network, no auth affected.
- **Improves readiness score**: Governance readiness dimension improves when the HIGH
  contradiction disappears.

## Why Safe

- The change modifies a string literal in the world model extraction function.
- It does not alter any execution path, governance policy, or runtime behavior.
- The affected code (`_extract_governance`) only reads the filesystem — it never writes.
- The fix is a pure observation-accuracy improvement.

## Expected Outcome

| Metric                         | Before | After |
|-------------------------------|--------|-------|
| Total contradictions          | 13     | 12    |
| HIGH-severity contradictions  | 1      | 0     |
| governance_router entity status| MISSING| PARTIAL (or OPERATIONAL) |
| Governance readiness factor   | Degraded | Improved |

## Validation Method

1. Run `detect_contradictions()` after the change.
2. Assert total contradictions <= 12.
3. Assert zero contradictions with severity == "high".
4. Assert `governance_router` entity status != "missing".
5. Run full organism test suite — all 891 tests must still pass.

## Rollback Method

Revert `substrate/organism/world_model.py:504` from:
```python
("governance_router", "substrate/control_plane/router/__init__.py", ...)
```
back to:
```python
("governance_router", "substrate/control_plane/router.py", ...)
```

## Selection Process

1. Built world model → 81 entities, 1 gap, 0 uncertainties.
2. Built dependency graph → 28 edges.
3. Ran contradiction engine → 13 contradictions (1 HIGH, 2 MEDIUM, 2 LOW, 8 INFO).
4. Evaluated all contradictions for safety, reversibility, and measurability.
5. Selected the HIGH-severity false positive as highest-leverage, lowest-risk target.
