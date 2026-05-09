# Phase 96.8AM — Execution-Time Canonical Registry Propagation Proof

## What This Proves

The node sync gate now accepts both command names AND action types
when validating execution requests. The canonical registry propagates
from surface display all the way through execution-time validation
with zero divergence.

## Root Cause

`live_local_runtime_execution_v1.py:271` passes `action_type` (e.g.
`"chrome_proof"`) as `requested_command` to the sync gate. But the
sync gate checked `requested_command not in self._command_registry`
where `_command_registry` keys are command names (`"!chrome-proof"`),
not action type values (`"chrome_proof"`).

Result: every spine-routed command that passed surface validation
was denied at execution time with `command_not_in_registry`.

## Fix

Surgical — two files, no new abstractions.

### node_sync_gate_v1.py

```python
# Construction: build known actions set from registry values
self._known_actions = set(self._command_registry.values())
self._registry_hash = registry_hash

# Validation: accept both command names AND action types
if requested_command and (
    requested_command not in self._command_registry
    and requested_command not in self._known_actions
):
    cmd_match = False
    missing_commands.append(requested_command)
    denial_reasons.append(f"command_not_in_registry: {requested_command}")
```

### discord_spine_integration_v1.py

```python
from core.registry.canonical_command_registry_v1 import get_canonical_registry

_reg = get_canonical_registry()
sync_gate = NodeSyncGate(
    command_registry=_reg.command_action_map,
    registry_hash=_reg.registry_hash(),
    ...
)
```

## What Changed

| Component | Before | After |
|-----------|--------|-------|
| Sync gate command check | Keys only (`!chrome-proof`) | Keys + values (`!chrome-proof` OR `chrome_proof`) |
| Sync gate registry hash | Not tracked | `registry_hash` parameter stored |
| Spine builder registry source | Canonical (96.8AL) | Canonical + hash propagated |
| `chrome_proof` execution | `command_not_in_registry` denial | ACCEPTED |
| `chrome_open_google_drive` execution | `command_not_in_registry` denial | ACCEPTED |

## Propagation Chain (verified)

```
CanonicalCommandRegistryV1 (single source)
  ├── Surface (!commands)     → registry_hash: 7d00140782e9
  ├── Adapter (COMMAND_ACTION_MAP) → same instance
  ├── Handler (SUBSTRATE_COMMANDS) → same instance
  ├── Router (allowed_action_types) → all 11 actions
  ├── Spine builder (NodeSyncGate) → registry_hash: 7d00140782e9
  └── Execution gate (validate) → accepts both keys AND values
```

## Test Results

```
Phase 96.8AM:  22 passed  (7 test classes)
Phase 96.8AL:  35 passed  (regression)
Phase 96.8AK:  28 passed  (regression)
Phase 96.8AJ:  60 passed  (regression)
Total:        145 passed, 0 failed
```

### Phase 96.8AM Test Classes
- TestNodeSyncAcceptsCanonicalActions (5) — action type accepted, command name accepted, unknown denied, all canonical accepted
- TestRegistryHashPropagation (4) — surface/sync same hash, adapter/canonical same source, gate gets hash, manifest matches
- TestRouterConfigParity (3) — config allows all, ALLOWED_ACTION_TYPES has all, ACTION_CAPABILITY_MAP has all
- TestSpineExecutionPropagation (3) — builder passes hash, uses canonical, passes action_type to sync
- TestNoDuplicatedRegistries (3) — no hardcoded maps, adapter derives from canonical, handler derives from canonical
- TestFullSpineSimulation (2) — chrome_proof and chrome_open_google_drive through real sync gate with full capabilities
- TestRegressionIntegrity (2) — all files compile

## Files

```
MODIFIED:
  core/runtime/node_sync_gate_v1.py
    — added _known_actions set, dual key/value check, registry_hash param
  eos_ai/interfaces/discord_spine_integration_v1.py
    — added registry_hash= to NodeSyncGate construction

CREATED:
  tests/test_registry_propagation_integrity_v1.py
  docs/system/phase968am_execution_time_registry_propagation_proof.md
```

## Final Output

```
W0 EXECUTION-TIME CANONICAL REGISTRY PROPAGATION — COMPLETE

Surface registry unified: YES (96.8AL)
Execution registry unified: YES (96.8AL)
Node sync accepts action types: YES (96.8AM)
Registry hash propagated to sync gate: YES
chrome_proof command_not_in_registry: RESOLVED
chrome_open_google_drive command_not_in_registry: RESOLVED
Canonical registry hash: 7d00140782e9
Full regression: 145 passed, 0 failed
```

## Commit

```
phase968am: prove execution-time canonical registry propagation
```
