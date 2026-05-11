# /eos_ai — Status

## Classification: ACTIVE_RUNTIME_LEGACY_NAME

This directory contains the active UMH runtime intelligence layer.
It currently powers the Discord bot, GWS scanner, LLM routing,
memory persistence, and all substrate subsystems.

The name `eos_ai` is a legacy artifact from when EOS (EntrepreneurOS)
was treated as the system owner. In the canonical UMH architecture,
EOS is an application projection — UMH is the substrate. This directory
is the substrate runtime, not an EOS-specific module.

### What this means
- `services/discord_bot.py` imports 15+ modules from `eos_ai/`
- Contains the confirmed-working LLM routing chain (model_router.py)
- Contains the confirmed-working Neon memory layer (memory.py, db.py)
- Contains the confirmed-working GWS scanner (gws_scanner.py)
- Contains canonical transport subsystem (`transport/`)
- Contains substrate shim layer (`substrate/` → re-exports from `transport/`)

### Why "legacy name"
The name `eos_ai` conflates an application (EOS) with the substrate (UMH).
In the canonical architecture, this code belongs in:
- `umh_runtime/` or `substrate/` — intelligence, memory, governance, execution
- `interfaces/` — Discord/Telegram/CLI surface code
- `platforms/eos/` — EOS product-specific logic

### Future rename recommendation
Target: `umh_runtime/` (preferred) or `substrate/`
Strategy: compatibility shim (`eos_ai/__init__.py` re-exports) + gradual import migration
Blockers: 200+ import sites across services/, scripts/, core/, tests/
Timeline: post-R7, when physical rename /opt/OS → /opt/UMH is complete

### Rules
- Do NOT rename this directory abruptly — it would break all runtime imports
- New canonical work should target `core/` or `eos_ai/transport/`
- Migration to `umh_runtime/` will use compatibility shims (re-exports)
- Existing imports from `eos_ai.*` will continue to work during migration

### Subdirectory status
| Subdirectory | Status | Notes |
|-------------|--------|-------|
| `transport/` | CANONICAL_TRANSPORT | Session, perception, execution — canonical UMH transport |
| `substrate/` | SHIM_LAYER | Re-exports from transport/ — 88 test files import through here |
| `runtime/` | CONFIRMED_RUNTIME | work_state.py used by Discord bot |
| `interfaces/` | DORMANT | Interface contracts not connected |
| `platforms/eos/` | DORMANT | EOS platform prototype not connected |
| `.substrate_sandbox/` | DORMANT | Sandbox artifacts |
| `.substrate_station/` | DORMANT | Station artifacts |

> Classified: Phase 96.8CO — 2026-05-10
> Previous: Phase 96.8BJ — 2026-05-09
