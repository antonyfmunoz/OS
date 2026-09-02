# Wave 2 Quota State — after green-pass preseed correction

This correction consumed ZERO field quota (no collector dispatch, no field
execution — a bounded harness source change only, per owner authorization).

| Field | Value |
|---|---|
| Consumed | 51 |
| Ceiling | 53 |
| Available | 2 |
| Reserve | 0 |

**Unchanged.** The last consumed unit was invocation #51 (run `20260808T213735Z-p1`,
Green Pass 1) on the prior SHA `4778030c7…`, which failed on the now-fixed sys.path
substrate race.

## SHA transition
- Prior SHA (defective green path): `4778030c7f62e46c831826e9cef04d99f1365a3c`
- **New exact SHA (this correction): `6e2d23ecfb472abb8b34698110cef9d61c72dfed`**
- HEAD == origin == PR #313 headRefOid == `6e2d23ecf…`
- PR #313: OPEN / DRAFT / UNMERGED (mergedAt=null)

## Consequence for the new SHA
Because this is a tracked-harness source change producing a new SHA, the prior
QUALIFIED failure/recovery pass (#50, `20260808T212611Z-p1` at `4778030c7…`) does
NOT satisfy the mandatory failure/recovery requirement for `6e2d23ecf…`. A NEW exact
SHA requires all 4 mandatory passes fresh: 1 failure/recovery + 3 green.

## Ceiling recommendation (owner-decides — NOT self-authorized)
- Absolute minimum future ceiling: 51 consumed + 4 mandatory = **55**.
- If one reserve is judged evidence-justified given campaign history:
  51 + 4 + 1 = **56**.
- Quota remains **51/53** until the owner rules. This correction does not change it.
