# WP-P4 — First Live Organic Loop: Execution Proof

Date: 2026-07-06
Operator order: EXECUTION MODE — merge #198 and complete the live proof chain.
Verdict: **ACCEPTED. `action_1783367421127_b0ztpntev` completed PENDING → APPROVED → EXECUTED (completed) through UMH governance, with the resulting task row verified in the EntrepreneurOS app DB. No manual DB writes, no seeding, no provider actions, no secrets leaked, gates green.**

## The loop that closed

```
EntrepreneurOS agent chat (organic user signal)
  → model emits [ACTION:CREATE_TASK|...]           19:50:21Z  status=pending
  → UMH read seam surfaces PENDING proposal
  → governed approve (operator token auth)          21:48:04Z  pending→approved   envelope 0b29e3f9754a47ed
  → server truth: APPROVED, execute_enabled=true
  → governed execute (non_provider_allowlist)       21:48:33Z  approved→completed envelope 4d692aeb6b044543
  → REAL task row created in EntrepreneurOS DB      21:48:31Z  tasks/e455ff56-fc73-48fc-aa27-a91116e1c254
```

Every transition is server truth read back from the live system (route envelopes
+ read-seam states + read-only SQL against the app DB). Full machine-readable
record: `data/audits/proof/2026-07-06_first_loop/execution_proof.json`.

## Ordered steps → outcomes

| Step | Outcome |
|---|---|
| 1. Merge #198 | merged `fc5776193` |
| 2. Sync main | `git pull` clean |
| 3. Full gates | 133 tests pass; registry audit truthful (1051 entries); 13/13 pre-commit gates |
| 4. Restart os-operator | healthy; secrets present; #198 fix verified live in-process |
| 5. Proposal exists | exactly 1 row, `action_1783367421127_b0ztpntev`, PENDING |
| 6. Governed approve | 200, `decision_applied=true`, `pending→approved` |
| 7. Status APPROVED | read seam: APPROVED, `execute_enabled=true` |
| 8. Execute (server said executable) | 200, `execution_applied=true`, `approved→completed` |
| 9. Final status | `completed`; `execute_enabled=false` (no re-execution possible) |
| 10. Task row in app DB | `e455ff56-fc73-48fc-aa27-a91116e1c254` "Follow up with Demo Lead", agent_executive — read-only verified |
| 11. Proof artifacts | this doc + JSON envelope; secret scan 0 hits |
| 12. Contradictions | none |

## What the live loop earned (beyond the proof)

Two real defects that 160 green tests could not see, found only by running the
loop against reality, each fixed with a regression test pinning the real layer:

1. **#197** — `eos_action_proposal_decision`/`_execute` were never registered in
   `MutationRegistry`; all suites faked the registry.
2. **#198** — approve wrote the UMH operator identity into
   `agent_actions.approved_by`, which is FK-constrained to the app's `users.id`;
   fix stamps the row's own `user_id` (the app principal — identical to the
   app's own approve semantics), UMH decider stays in the governed envelope.

Both times the governed spine failed closed and preserved the row — the
proposal survived two defect discoveries untouched and completed on the third
pass. That is the doctrine working as written.

## Evidence integrity

- `approved_by = user_1776306380825` (FK-safe app principal), `approved_at`,
  `executed_at`, `completed_at` all stamped — read-only SQL.
- Operator identity recorded in governance envelopes, never in the app row.
- Executor scope was `non_provider_allowlist` (`create_task`,`create_document`);
  no provider action was reachable.
- Secret scan over all artifacts: 0 hits; only op:// references exist in git.

## Deferred debt (named, not hidden)

- `agent_actions.task_id` is not backfilled by the UMH executor (`result_ref` +
  `execution_result` carry the linkage) — candidate micro-packet.
- Cockpit UI pixel-verification of the queue remains Clerk-gated (API layer is
  Class A; UI layer Class B) — open #187 item.
- os-operator threadpool starvation under sustained polling — separate packet.
- W1/W2 app-side hardening awaiting app-repo review: EntrepreneurOS#3, #4.
