# Wave 2 Quota State — after collector observation correction

This correction consumed ZERO field quota (no dispatch, no field execution —
a bounded collector-side source change only, per owner authorization
2026-08-09: "Authorize a narrow non-field correction cycle only.").

| Field | Value |
|---|---|
| Consumed | 54 |
| Ceiling | 57 |
| Remaining | 3 |
| Reserve | 0 (none exists) |

## Invocation ledger (campaign-relevant tail)

| Invocation | SHA | Run | Outcome |
|---|---|---|---|
| #53 | `83c56cb6d…` | 20260809T021413Z-p1 | CONSUMED / NOT QUALIFIED — proof-inspector 404 (fixed: `f43a03b18`) |
| #54 | `842434dc3…` | 20260809T144154Z-p1 | CONSUMED / NOT QUALIFIED — collector w16/w26/w27 observation defects (fixed: this correction). Candidate INNOCENT; property field-proven; historical evidence only — does NOT carry forward |

## SHA transition
- Prior SHA (defective collector observation): `842434dc3fa3ed16540673f5df48950ccf6a2674`
- Correction commit (collector + runbook + tests): `07f580b65a27d5c9530e69bb8613e54b87df600a`.
- **New exact SHA = the branch HEAD containing this record** (reported
  verbatim in the owner return; reconciled five ways: VPS worktree HEAD ==
  origin == PR #313 headRefOid == Beast main mirror == Beast collector
  worktree).
- PR #313: OPEN / DRAFT / UNMERGED. Wave 3: not started.

## Ceiling arithmetic (owner-decides — NOT self-authorized)
A fresh campaign at the new SHA requires 4 mandatory passes
(1 failure/recovery + 3 green). Remaining budget is 3.

- **3 < 4 — the standing ceiling of 57 cannot complete the campaign.**
- Absolute minimum ceiling to complete: 54 consumed + 4 mandatory = **58**.
- If one evidence-justified reserve is granted: 54 + 4 + 1 = **59**.
- Quota remains **54/57** until the owner rules. No dispatch occurs without
  a new exact-SHA field-quota authorization.
