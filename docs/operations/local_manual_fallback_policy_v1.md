# Local Manual Fallback Policy v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Policy

Local terminal is a fallback interface, not the primary control path.
Manual local execution is the last resort when all automated paths are
blocked or unavailable.

## When Manual Fallback Activates

1. **No automated worker available** — no node has the required
   capabilities and the task cannot be deferred
2. **All automated paths blocked** — governance blocks the action
   and only human hands can complete it
3. **Worker explicitly set to MANUAL_FALLBACK mode** — founder
   chose step-by-step control for this worker
4. **Transport failure** — message bus cannot reach the target node
   and the founder is physically present at the machine

## Manual Fallback vs AUTO

| Aspect | AUTO | MANUAL_FALLBACK |
|--------|------|-----------------|
| Action execution | Automatic | Waits for human at each step |
| Governance gates | Only pauses at REQUIRE_ADVISOR_APPROVAL | Pauses at every step |
| Approval routing | Via message bus + advisor session | Via local terminal |
| Speed | Fast | Slow, human-paced |
| When to use | Default for all work | Only when AUTO is impossible |

## Governance Still Applies

Manual fallback does not bypass governance. Every action still passes
through `evaluate_action_gate()`. BLOCKED actions remain blocked even
in manual mode. The only difference is that ALLOWED actions also pause
for human confirmation instead of proceeding automatically.

## Worker Profile Configuration

```python
WorkerProfile(
    worker_id="manual_operator_1",
    node_id="local_machine",
    roles=[WorkerRole.MANUAL_OPERATOR],
    capabilities=["local_files", "gui_computer_use"],
    mode=WorkerMode.MANUAL_FALLBACK,
)
```

## File

`eos_ai/substrate/worker_node_contracts.py` — `WorkerMode.MANUAL_FALLBACK`
