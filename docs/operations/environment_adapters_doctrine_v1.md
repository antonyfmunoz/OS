# Environment Adapters Doctrine v1

**Phase:** 96.8A.1
**Status:** Active
**Layer:** UMH Substrate

## Core Principle

VPS, WSL, tmux, Windows GUI, Chrome, and the local worker are
**environment adapters** — not standalone infrastructure.

The VPS ↔ Local Worker Bridge is an Environment Adapter implementation.
It exists because the External Boundary Law requires that all
environment transitions pass through governed adapter boundaries.

## Environment Adapter Inventory

| Environment | System Type | Adapter Category |
|-------------|-------------|-----------------|
| VPS (Linux) | `vps` | ENVIRONMENT |
| Local WSL | `local_wsl` | ENVIRONMENT |
| Local Windows GUI | `local_windows_gui` | ENVIRONMENT |
| Tmux session | `tmux` | ENVIRONMENT |
| Chrome browser | `chrome_browser` | BROWSER |
| Founder visual confirmation | `founder_confirmation` | HUMAN_APPROVAL |

## Bridge as Adapter Path

The VPS ↔ Local Worker Bridge connects:
- VPS orchestrator (environment adapter: VPS)
- Local WSL worker (environment adapter: WSL)
- Local tmux session (environment adapter: tmux)
- Windows GUI (environment adapter: local_windows_gui)
- Chrome session (browser adapter: chrome_browser)
- Founder visual confirmation (human approval adapter)

Each of these is a separate external system that requires its own
adapter boundary under the External Boundary Law.

## Computer Use Dependency

Computer Use (CU) depends on environment adapters:
- CU needs a visible Chrome instance → browser adapter
- CU needs a Windows GUI → environment adapter
- CU needs tmux for persistent execution → environment adapter
- CU results need founder confirmation → human approval adapter

Without environment adapters, CU has no execution surface.

## Packet Validator Integration

The packet validator (`packet_validator.py`) enforces:
- Local GUI packets require `required_environment_adapters`
- Founder confirmation packets require `required_human_approval_adapters`
- These fields were added in Phase 96.8A.1

## Work Packet Integration

Work packets (`work_packet.py`) carry:
- `adapter_boundary_required` — defaults to True
- `required_environment_adapters` — list of environment adapter IDs
- `required_human_approval_adapters` — list of approval adapter IDs
- `external_interaction_id` — link to ExternalInteraction record

## Modules

- `core/environment_bridge/` — environment adapter implementations
- `core/adapter_engine/adapter_taxonomy.py` — adapter classification
- `core/adapter_engine/adapter_boundary_validator.py` — boundary enforcement
