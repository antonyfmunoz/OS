# Pass 1 Stop Classification — NOT QUALIFIED

**Run ID:** 20260809T021413Z-p1
**SHA:** 83c56cb6d9782b60dc81aa019bcb9bb8a73bb2e0
**Invocation:** #53 (CONSUMED)
**Terminal state:** `failed` at `w16_ab_running_concurrent`
**Classification:** COLLECTOR OBSERVATION FAILURE — NOT HARNESS OR CANDIDATE DEFECT

## What happened

The **candidate lifecycle executed correctly**:

| Attempt | Task | Status | Kind | Notes |
|---|---|---|---|---|
| ea-d6a278cd58e2 | wp-3700f1b6ddc5 (A) | FAILED | worker | tools-revoked injection worked |
| ea-6ef488a15ddb | wp-c731ec2633ca (B) | SUCCEEDED | worker | Concurrent with A |
| ea-612d00259ee4 | wp-3700f1b6ddc5 (A retry) | SUCCEEDED | worker | Recovery after failure |
| ea-68f8be51abfe | wp-f0e194753775 (C) | SUCCEEDED | control_plane_composition | Proof has predecessor_commits |
| ea-5dc8164807fa | wp-0c47809ef072 (D) | DISPATCHED | worker | Started but incomplete |

This is the **complete A+B→C→D failure/recovery property** — A fails, B succeeds
concurrently, A retries and succeeds, C composes from A+B predecessors, D dispatches.

The **collector on Beast** failed to observe this because:

1. `w16_ab_running_concurrent` → `concurrent_tasks=[]` — the composition was never
   identified via the API. Root cause undiagnosed (API auth on Beast? Clerk session
   expiry during the 240s poll window? Proof-inspector endpoint inaccessible from
   Beast's Playwright context?).

2. `execution_surface=False` — the cockpit UI's execution surface (`[data-testid="w2-execution-root"]`)
   was not mounted, suggesting the cockpit's React component never rendered the execution view.

3. w17 and w18 also failed as a consequence (they depend on w16's composition identification).

## What the durable evidence proves

The persisted attempt ledger has full transition histories with timestamps. Task A (first
attempt) dispatched at 1786241721.602 and ran until 1786241804.791. Task B dispatched at
1786241721.653 and ran until 1786241806.208. **Temporal overlap: ~83 seconds**. This is the
exact property w16 was supposed to observe.

The composition Proof (`proof-d82a8aa751a1`) has `predecessor_commits` binding to both
predecessor task commits. This is the exact property w18 was supposed to observe.

## Why this is NOT a reserve-eligible transient

The failure is in the **collector observation model**, not in an external transient (network
blip, resource exhaustion). The collector's inability to identify the composition via the
API is an undiagnosed collector/cockpit interaction issue. Per the directive: "Reserve is
ONLY for a proven external transient after candidate AND harness innocence is established."
Candidate is proven innocent (correct lifecycle). Harness innocence is NOT established
(collector couldn't observe).

## Directive compliance

> "If consumed and NOT QUALIFIED: STOP and return to owner. Do not automatically retry."

STOPPING. Returning to owner.

## Quota state

- Consumed: 53/57 (Pass 1 consumed invocation #53)
- Available: 4 (3 mandatory + 1 reserve)
- No further dispatches without owner authorization
