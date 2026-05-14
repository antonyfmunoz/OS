# Phase 96.8AL — Runtime Bootstrap + Canonical Registry Unification Proof

## What This Proves

All runtime command systems now derive from ONE canonical source:

1. **Surface display** (`!commands`) — from CanonicalCommandRegistryV1
2. **Router lookup** (ControlPlaneRouterV1) — from CanonicalCommandRegistryV1
3. **Execution lookup** (spine gate) — from CanonicalCommandRegistryV1
4. **Node sync validation** (NodeSyncGate) — from CanonicalCommandRegistryV1
5. **WorkPacket dispatch** — from CanonicalCommandRegistryV1

And all runtime state initialization goes through ONE bootstrap path:
RuntimeBootstrapStateV1

## Root Cause

Commands were defined in 4 separate places that had to stay in sync manually:
- `COMMAND_ACTION_MAP` (discord_interface_adapter_v1.py)
- `ACTION_CAPABILITY_MAP` (control_plane_router_v1.py)
- `allowed_action_types` (control_plane_router_v1.json)
- `capabilities` (local_worker_adapter_registry_v1.json)

When `!chrome-open-google-drive` was added to the surface but not to the
router config `allowed_action_types`, it appeared in `!commands` but failed
at execution with `command_not_in_registry`.

Additionally, the node sync gate required a `config_marker.json` in
`spine_gate_proofs/` that was never created, causing `config_missing` denials.

## Canonical Command Registry

```
core/registry/canonical_command_registry_v1.py

CommandEntry {
  command_name, canonical_action, routing_mode,
  governance_policy, execution_mode, foreground_required,
  readonly, require_screenshot_proof, required_runtime_state,
  required_proof_state, required_environment, required_worker,
  adapter_id, capability_type
}

CanonicalCommandRegistryV1:
  .commands            → frozenset of command names
  .actions             → frozenset of action names
  .command_action_map  → dict used by router/spine
  .spine_routed_commands → frozenset
  .router_routed_commands → frozenset
  .command_contracts   → spine governance contracts
  .allowed_action_types → sorted list for router config
  .registry_hash()     → deterministic content hash
  .surface_hash()      → deterministic surface hash
```

## Runtime Bootstrap

```
core/runtime/runtime_bootstrap_state_v1.py

Lifecycle:
  BOOTSTRAP_START
  → BOOTSTRAP_PATHS_INITIALIZED (auto-heal safe dirs)
  → BOOTSTRAP_REGISTRY_INITIALIZED (load canonical registry)
  → BOOTSTRAP_PROOFS_INITIALIZED (config markers)
  → BOOTSTRAP_RUNTIME_READY

Auto-heals:
  ✓ runtime directories
  ✓ cache folders
  ✓ proof markers
  ✓ config markers

Never auto-heals:
  ✗ authority state / governance configs
  ✗ secrets (.env files)
  ✗ user data / adapter registries
```

## Unification Changes

| System | Before | After |
|--------|--------|-------|
| `SUPPORTED_COMMANDS` | Hardcoded set literal | `_REGISTRY.commands \| {"!status"}` |
| `COMMAND_ACTION_MAP` | Hardcoded dict literal | `_REGISTRY.command_action_map` |
| `SPINE_ROUTED_COMMANDS` | Hardcoded frozenset | `_REGISTRY.spine_routed_commands` |
| `COMMAND_CONTRACT` | Hardcoded dict literal | `_REGISTRY.command_contracts` |
| `SUBSTRATE_COMMANDS` | `SUPPORTED - {"!status"}` | `_CANONICAL.commands` |
| Node sync gate registry | `dict(COMMAND_ACTION_MAP)` | `_reg.command_action_map` |
| Spine action lookup | `COMMAND_ACTION_MAP.get()` | `get_canonical_registry().command_action_map.get()` |
| Router config allowed | 7 actions (missing spine) | 11 actions (all canonical) |

## Config Gap Fixed

`config/control_plane_router_v1.json::allowed_action_types` was missing:
- `chrome_open_google_drive`
- `chrome_proof`
- `ingest_safe_doc`
- `ingest_safe_doc_cu`

Now includes all 11 canonical actions.

## Live Startup Banner

```
[substrate-handler] Substrate Command Handler — ACTIVE
[substrate-handler] VPS HEAD: 41adf365
[substrate-handler] origin/main: 41adf365
[substrate-handler] parity: SYNCED
[substrate-handler] substrate commands: 11
[substrate-handler] meta commands: 3
[substrate-handler] surface hash: fbce7519491c
[substrate-handler] registry hash: 7d00140782e9
[substrate-handler] registry source: canonical_command_registry_v1
[substrate-handler] commands: !chrome, !chrome-open-google-drive, !chrome-proof, ...
```

## Test Results

```
Phase 96.8AL:  35 passed  (9 test classes)
Phase 96.8AK:  28 passed  (regression)
Phase 96.8AJ:  60 passed  (regression)
Total:        123 passed, 0 failed
```

### Phase 96.8AL Test Classes
- TestCanonicalRegistrySingleSource (9) — all derivations match
- TestRegistryHashDeterminism (5) — hashes stable, singleton
- TestBootstrapLifecycle (7) — auto-heal, fail, marker, ledger
- TestBootstrapDeniedExecution (2) — denial state
- TestRouterConfigParity (2) — all actions in config, no orphans
- TestCommandSurfaceFromCanonical (3) — manifest from canonical
- TestRegistryContracts (5) — spine contracts, frozen entries
- TestLiveBootstrapOnVPS (2) — real bootstrap succeeds

## Files

```
CREATED:
  core/registry/canonical_command_registry_v1.py
  core/runtime/runtime_bootstrap_state_v1.py
  tests/test_canonical_registry_bootstrap_v1.py
  docs/system/phase968al_runtime_bootstrap_canonical_registry_proof.md

MODIFIED:
  eos_ai/interfaces/discord_interface_adapter_v1.py
    — replaced 4 hardcoded command maps with canonical registry derivations
  eos_ai/interfaces/discord_spine_integration_v1.py
    — sync gate + spine execution use canonical registry
  services/handlers/substrate_command_handler.py
    — SUBSTRATE_COMMANDS from canonical, bootstrap on init, enhanced !runtime
  config/control_plane_router_v1.json
    — added 4 missing spine-routed actions to allowed_action_types
```

## Final Output

```
W0 RUNTIME BOOTSTRAP + CANONICAL REGISTRY UNIFICATION — COMPLETE

Surface registry unified: YES
Execution registry unified: YES
Node sync registry unified: YES
Bootstrap auto-healing working: YES
Runtime proof initialized: YES
Canonical registry hash: 7d00140782e9
Runtime bootstrap hash: RUNTIME-<generated>
```

## Commit

```
phase968al: prove runtime bootstrap and canonical registry unification
```
