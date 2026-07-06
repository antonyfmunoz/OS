# P4S-31 — UMH MVP Intent → Proof Operating Loop Skeleton (Proof)

**Packet:** P4S-31 (Lane B, HIGH risk, Opus executor)
**Date:** 2026-07-06
**Objective:** The thinnest UMH operating loop that turns operator intent into a
governed packet/proof record — intent → IntentSpec → WorkPacket draft → held
approval gate → governed decision → proof record → Cockpit-readable surface.
**Machine artifact:** `data/audits/proof/2026-07-06_p4s31_mvp_loop_proof.json`
(every id below comes from that real in-process run — no fabricated data).

## The end-to-end chain (one real intent)

Raw operator intent (generic, no tenant literals):

> "Draft follow-up plan for demo lead pipeline"

Loop id: `loop_167ae36f5c68`. Canonical runtime:
`governed_mutation -> MutationRouter -> GovernedExecutionSpine`.

### Step 1 — Deterministic IntentSpec (no LLM, no network)

| field | value |
|---|---|
| intent_id | `intent_478c8de9dbfa` |
| intent_type | `directive` |
| route_type | `hybrid` (from the existing `IntentRouter`) |
| risk_level | `medium` (from `extract_intent_risk`) |
| deterministic | `true` |

Parse is a pure function of the text: same input → identical spec shape
(regression `test_intent_spec_parse_is_deterministic`). The classifier reused is
the existing `substrate.operator.intent_router.IntentRouter`; the risk table is
the existing `substrate.workstation.intent_contract.extract_intent_risk`. No new
classifier, no new risk vocabulary, no LLM call anywhere.

### Step 2 — Typed WorkPacket draft

| field | value |
|---|---|
| draft_id | `draft_6391e49cb6a1` |
| status | `pending` (`WorkPacketStatus.PENDING`) |
| priority | `normal` (`WorkPacketPriority.NORMAL`) |
| actionable | `true` (directive intents only) |

The draft is the **pre-governance** `WorkPacketDraft`, deliberately distinct from
the heavy runtime `substrate.types.WorkPacket` (which needs a
governance_verdict_id / capability_id / trace_id it does not have yet). It reuses
the canonical `WorkPacketStatus` / `WorkPacketPriority` vocabulary — not a
parallel enum.

### Step 3 — Approval gate HOLDS

After `submit()` the loop is at `awaiting_approval`, and there is **no proof
record** (`proof_present_before_decision: false`). The loop never self-advances
past the gate. A fresh loop can never reach `proof_recorded` without an explicit
governed decision (regression `test_gate_cannot_reach_proof_without_decision`).

### Step 4 — Governed approval through the canonical runtime

The approve decision is submitted through `transports.api.governed
.governed_mutation` under the **registered** MutationSpec
`intent_loop_approval_decision`. The state transition (stage → PROOF_RECORDED)
happens **inside** the mutation's `execute_fn`, so the governed spine is the only
thing that flips the gate — no bypass.

| field | value |
|---|---|
| mutation_name | `intent_loop_approval_decision` |
| governance_status | `completed_degraded` |
| governed_success | `true` |
| degraded_audited | `true` (ledger audit id emitted, e.g. `led-512f0d55e2e7`) |

Because this proof runs in a worktree with **no organism daemon**, the loop's
default governed path is the **substrate-native** canonical choke point
`substrate.organism.mutation_router.route_mutation_degraded` — the same
fail-closed gate the transport shim itself delegates to when the daemon is down.
The substrate module never imports `transports/` (dependency-direction law); the
transport route injects the daemon-backed `governed_mutation` for the live spine
path. The spec is `risk=low`, `blast_radius=LOCAL_FILE`,
`degraded_mode_allowed=True`, so it is permitted to execute in degraded mode —
**with a mandatory audit record** (ledger id `led-…`) — writing only
substrate-owned JSON. This is governed, never ungoverned. With the daemon up, the
identical call routes through the full `GovernedExecutionSpine` and yields an
`envelope_id`.

### Step 5 — Proof record (substrate server truth)

`proof_88799d8c8670` — decision `approve`, decided_by `umh_operator`,
mutation `intent_loop_approval_decision`, governed_success `true`,
resulting_stage `proof_recorded`. Persisted in
`data/umh/operator/intent_loop/intent_loops.jsonl` (same store mechanism as
`IntentReceiptStore`).

### Step 6 — Final stage

`proof_recorded`.

### Step 7 — Cockpit-readable surface

`GET /api/umh/intent-loop` → `read_intent_loop_surface()` returns:

```
surface=intent_loop  connection_status=connected  total=1
awaiting_approval=0  proof_recorded=1  stage_counts={proof_recorded: 1}
```

The Cockpit `IntentLoopPanel` (read-only mirror, P4S-31) polls this surface.

## Constraints upheld (all `true` in the JSON artifact)

- no provider action
- no projection-DB write (substrate-owned JSON only)
- deterministic, no LLM
- governed, no bypass (mutation = `intent_loop_approval_decision`)
- gate held before approval

## Composition — reused vs new

**Reused (imported, not re-built):**
`IntentRouter` / `RouteType` (deterministic classification),
`extract_intent_risk` (risk table), `WorkPacketStatus` / `WorkPacketPriority`
(lifecycle vocabulary), `governed_mutation` + `MutationRegistry` (canonical
runtime + spec registration), the `IntentReceiptStore` JSONL+atomic persistence
pattern, the projection-read-surface route discipline, the `ProjectionMirrorsPanel`
panel/store structure.

**New (genuinely absent before this packet):** `IntentSpec` /
`WorkPacketDraft` / `IntentLoopStage` / `IntentType` (typed loop records —
`IntentSpec` was unregistered and unused anywhere), `IntentLoop` / `IntentLoopStore`
/ `ProofRecord` (the loop state machine + substrate-owned store), the
`intent_loop_approval_decision` MutationSpec, the `/intent-loop` read route, and
the `IntentLoopPanel` Cockpit mirror.

## Tests

`tests/test_p4s31_intent_loop.py` — 16 tests: deterministic parse, gate holds,
mutation registered (#197 style), degraded-safe spec, governed submission (no
bypass) at runtime, real end-to-end governed decision, proof shape, read-surface
shape, no projection/provider imports, instance-context clean. All green.
