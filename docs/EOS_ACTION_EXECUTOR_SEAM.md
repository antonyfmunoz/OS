# EOS Action Executor → UMH Governed Runtime Seam Map

**Work packet:** WP-P4-EOS-ACTION-EXECUTOR-SEAM-001
**Date:** 2026-07-06
**Source truth:** EntrepreneurOS on the Beast — `feature/company-system` @ `9c8725f`, probe 2026-07-05, VERIFIED, `source_build_safe=True` (re-confirmed live this packet)
**Machine-readable map:** `data/umh/projection_reconciliation/eos_action_executor_seam_map.json`
**Accessor:** `projections/eos/integration/action_seam.py` (`load_eos_action_seam_map()`, `mappable_seams()`)

Seam/mapping packet only. No code copied, no schema changed, no routes
implemented, no Beast writes. Files read (via the read-only inspection mirror):
`action-executor.ts`, `routes.ts` (action + chat sections), `storage.ts`
(action/metric/oauth methods), `integrations/gmail.ts`, `shared/schema.ts`.

---

## 1. What the EntrepreneurOS action executor actually does

The app implements a complete propose → approve → execute → record → retry →
learn lifecycle for agent-initiated side effects:

1. **Propose.** An agent's chat reply may embed bracket-grammar tags —
   `[ACTION:SEND_EMAIL|to:...|subject:...|body:...]` etc. The chat route
   regex-extracts them, strips them from the visible reply, and inserts an
   `agent_actions` row: `status=pending`, `requiresApproval=true`, attributed
   to agent + user + conversation, with an estimated-time-saved heuristic.
   Raw model output can never execute anything directly.
2. **Approve.** `POST /api/actions/:id/approve` checks ownership
   (`action.userId == session user`), stamps `approved/approvedBy/approvedAt`,
   then **executes inline in the same HTTP request**. Reject sets
   `status=rejected` and nothing runs.
3. **Execute.** `executeAction()` stamps `executing/executedAt`, then a switch
   on `actionType`: `send_email` (Gmail adapter over a stored OAuth token,
   with refresh), `create_task` (tasks insert), `create_document` (documents
   insert). Unknown types throw — fail closed.
4. **Record.** Success → `completed` + `completedAt` + `executionResult`
   (jsonb). Failure → `failedAt` + `errorMessage`.
5. **Retry.** On failure below `maxRetries` (3), status returns to
   **`pending`** — the action re-enters the human approval queue, so *every
   retry is human-re-approved*. At the cap it goes terminally `failed`.
6. **Learn.** Success increments per-agent per-day `agent_metrics`
   (`actionsExecuted`, `estimatedTimeSavedMinutes`).

## 2. Which parts are universal UMH runtime semantics

Thirteen seams mapped (full detail in the JSON). The headline correspondences:

| EOS mechanism | UMH primitive | Substrate owner |
|---|---|---|
| `agent_actions` pending row | **Approval** | `substrate/types.py::ApprovalRequest` (near 1:1 fields) |
| approve/reject endpoints | **Approval** (state transition) | control_plane authority gates via the governed spine |
| `executeAction()` dispatch | **Operation** | canonical runtime: `governed_mutation → MutationRouter → GovernedExecutionSpine` |
| actionType switch | **CapabilityPathway** | `capability_router.py` + `CapabilityInvocation` |
| Gmail send + token refresh | **AdapterCall** | `adapters/` GWS + `credential_gate.py` |
| `executionResult`/`errorMessage` | **Proof** | `substrate/execution/trace.py` + `Proof` types |
| bounded re-approval retry | **Operation** retry policy | spine + approval re-queue |
| `agent_metrics` increments | **Trace** → learning | `substrate/execution/feedback.py` |
| `create_task` effect | **WorkPacket** | `substrate/types.py::WorkPacket` |
| agent chief/manager/laborer tiers | **RuntimeNode** | organism roles + authority tiers |
| action queue GET endpoints | **Approval** read model | projection read-surface discipline |

**Semantics worth preserving as-is:** retry-requires-re-approval. It is
stricter than auto-retry and matches UMH fail-closed philosophy. Do not
"improve" it into silent auto-retry for side-effecting actions.

## 3. Which parts are EOS-specific (L3, stay in the projection)

- The `[ACTION:...]` bracket grammar (projection prompt protocol).
- Action-type display names, `estimatedTimeSaved` heuristics (5/3 min),
  priority/tags vocabulary, conversation linkage.
- The three concrete action types — seed entries in a capability registry,
  not substrate concepts.
- Task/document field vocabularies (status/priority enums).

## 4. Gaps the substrate closes on import

- **No risk classification.** Every EOS action carries equal approval weight.
  UMH assigns deterministic `RiskClass`/`ActionRiskClass` per action type.
- **Inline execution in the approve request.** UMH decouples decision from
  execution through the spine (approve → queued operation).
- **SECURITY: plaintext OAuth tokens** in the `oauth_tokens` table — importing
  the AdapterCall seam requires migrating to the 1Password credential-injection
  law. Never reproduce the plaintext pattern.
- **Ungoverned CRM boundary.** `crm_activities.createdByAgentId` /
  `crm_deals.assignedAgentId` allow agent-attributed CRM mutations that bypass
  the approval lifecycle entirely — the one place the app's own governance
  model leaks. When CRM mutations are imported they MUST route through
  `governed_mutation`.
- **Racy metric increments** (read-modify-write). The feedback loop is the
  canonical accumulator.

## 5. What requires owner approval before mutation

1. Any persistent approval-store schema work.
2. Credential migration (`oauth_tokens` plaintext → 1Password).
3. Routing EOS CRM mutations through `governed_mutation` (app behavior change).
4. Risk-class policy for EOS action types.
5. Any agent-tier autonomy (approval-free execution) policy.
6. Any write to the EOS Neon DB or the Beast working tree.

## 6. Recommended first implementation slice

**EOS ActionProposal read seam** — a projection-owned, read-only accessor
translating the EOS `agent_actions` row shape into a substrate
`ApprovalRequest` view, exposed through one discipline-conformant
`/eos/actions` read surface (pattern: `/eos/activation`).

- Smallest seam exercising the Approval mapping end-to-end on real EOS data.
- Gives the cockpit a real approval-queue view before any execution wiring.
- Explicitly NOT: approve/reject writes, executor port, capability routing —
  those follow once the read seam is proven.

---

## Build-safety gate (enforced in code)

`mappable_seams()` fails closed exactly like `build_mappable_modules()` (#181):
rows flow only while live `eos_readiness()['source_build_safe']` is True, the
map's recorded head matches the live VERIFIED Beast head, the map is EOS-only,
and every row maps to one of the eight sanctioned primitives with a non-empty
substrate target owner.

Regression tests: `tests/test_eos_action_executor_seam.py`.
