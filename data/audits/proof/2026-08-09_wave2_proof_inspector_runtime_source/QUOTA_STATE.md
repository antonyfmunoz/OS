# Wave 2 Quota State — after proof-inspector runtime-source correction

This correction consumed ZERO field quota (no collector dispatch, no field
execution, no reserve use — a bounded non-field source change only, per owner
authorization 2026-08-08: "ACCEPT ROOT CAUSE. AUTHORIZE NARROW NON-FIELD
CORRECTION ONLY.").

| Field | Value |
|---|---|
| Consumed | 53 |
| Ceiling | 57 |
| Available | 4 |
| Of which mandatory | 3 |
| Of which reserve | 1 |

**Unchanged.** The last consumed unit was invocation #53 (run
`20260809T021413Z-p1`, Pass 1 failure/recovery) at SHA `83c56cb6d…`, which
failed at collector w16 on the now-fixed proof-inspector wiring defect.
Invocation #53 is preserved as consumed/not-qualified evidence
(`PASS1_EVIDENCE/`, this dir) and is NOT reinterpreted as a candidate failure
— the candidate's A+B→C→D property is proven correct by the durable ledger.

## SHA transition
- Prior SHA (defective proof-inspector surface): `83c56cb6d9782b60dc81aa019bcb9bb8a73bb2e0`
- Correction commit (fix + tests): `f43a03b18a81a0b18249593290a47ea9b68d9234`.
- **New exact SHA = the branch HEAD containing this record** (the evidence
  commit; reported verbatim in the owner return and reconciled five ways:
  VPS worktree HEAD == origin == PR #313 headRefOid == Beast main mirror ==
  Beast collector worktree).
- PR #313: OPEN / DRAFT / UNMERGED.

## Consequence for the new SHA
Tracked source change → the `83c56cb6d` campaign is VOID per the Tracked Edit
Stop Law. Pass 1 (#53) does NOT carry over. A NEW exact-SHA field
authorization is required; all 4 mandatory passes run fresh:
1 failure/recovery + 3 green.

## Ceiling arithmetic (owner-decides — NOT self-authorized)
- Remaining budget under the standing ceiling: 57 − 53 = 4 = exactly the 4
  mandatory passes, with ZERO reserve margin left if all four are needed
  (the previously designated reserve unit becomes the 4th mandatory pass).
- The reserve is NOT usable for this correction retroactively — the defect
  was a code defect, not an external transient.
- No dispatch occurs without explicit new owner authorization.
