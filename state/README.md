# state/

All persistent and session state. Memory, storage, context, business
instance state, and domain-specific state stores.

## Subdirectories

| Path | Purpose |
|------|---------|
| `business/` | Business instance state (BIS) |
| `context/` | Context assembly and resolution |
| `finance/` | Financial state (expenses, revenue) |
| `lifecycle/` | Entity lifecycle tracking |
| `logs/` | Structured logging state |
| `memory/` | Canonical memory stores (AgentMemory, ConversationMemory) |
| `metrics/` | Metrics collection |
| `permissions/` | Permission state |
| `preferences/` | User/system preferences |
| `profiles/` | User and agent profiles |
| `providers/` | Provider state and health |
| `registries/` | State registries |
| `session/` | Session state management |
| `storage/` | Low-level storage (Neon, JSON) |
| `stores/` | Domain store implementations |
| `tenancy/` | Multi-tenant state isolation |
| `work/` | Work state and pressure tracking |

## §24 Reference

Canonical module tree §24: `state/` — memory, context, world_model,
registries, session, storage.

## Boundary

State modules persist and retrieve. They do NOT make decisions, execute
actions, or call external systems. The memory canonical path (Law 5.5)
runs through `state/memory/`.
