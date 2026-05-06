# Execution Binding Contract v1

**Phase:** 96.8F
**Status:** Active
**Layer:** UMH Substrate — Adapter Boundary Layer
**Module:** `core/environment_bridge/execution_binding_contracts.py`

## Doctrine

UMH must explicitly bind all 6 execution layers before any external action.
Collapsing layers into a single "backend" is architecturally invalid.

## The 6 Layers

| # | Layer | What It Answers | Example |
|---|-------|----------------|---------|
| 1 | Environment | Where does execution happen? | Windows desktop |
| 2 | Execution Surface | What runs the commands? | PowerShell, WSL, tmux |
| 3 | Application | What program is used? | Google Chrome |
| 4 | Target Service | What service is accessed? | Google Drive, Google Docs |
| 5 | Capability | What action is performed? | Open URL, read inventory |
| 6 | Proof | What evidence is required? | Founder visual confirmation |

## Non-Collapsibility Rules

- **Environment is not execution surface.** Windows desktop != PowerShell.
- **Execution surface is not application.** PowerShell != Chrome.
- **Application is not target service.** Chrome != Google Drive.
- **Target service is not capability.** Google Drive != read_file_inventory.
- **Capability is not proof.** read_file_inventory != founder_visual_confirmation.

Each layer has its own identity, type, constraints, and validation rules.

## Founder Correction Context

Phase 96.8D/E treated "preferred_backend: GUI_COMPUTER_USE" as a single
opaque concept covering environment, surface, application, service,
capability, and proof simultaneously.

This allowed ambiguity: the system could route through `explorer.exe`
or default-browser handling instead of Chrome directly, because no layer
explicitly declared which application was required.

Phase 96.8F makes each layer explicit so the system must declare:
- I am executing on `local_windows_desktop` (environment)
- Via `wsl_tmux_worker` as orchestrator and `windows_powershell_relay`
  as GUI actuator (execution surface)
- Using `google_chrome_windows` via `direct_executable` (application)
- Targeting `google_drive` in `google_workspace` family (target service)
- To perform `google_drive.read_file_inventory` (capability)
- With `founder_visual_confirmation` proof (proof)

## Validation Rules

1. All 6 layers must be present and non-empty
2. Chrome actions reject explorer/default-browser/generic shell routing
3. Google Drive/Docs actions require google_workspace service family
4. WSL/tmux cannot be final GUI authority (gui_actuator role)
5. Founder visual confirmation is required for visible Chrome launch
6. process_exists_only and window_metadata_only are blocked evidence

## Alignment with UMH External Boundary Law

The External Boundary Law requires that all interactions with external
systems go through governed adapter boundaries. The Execution Binding
Contract extends this by requiring that the adapter boundary's work
packets carry explicit bindings for every layer of the execution stack.

A work packet with `execution_binding: {}` or missing `execution_binding`
is invalid and cannot execute. This prevents any external action from
proceeding with vague, collapsed, or assumed layer bindings.
