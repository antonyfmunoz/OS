# interface/

User-facing surfaces and protocol bridges. Everything that connects UMH
to humans lives here.

## Subdirectories

| Path | Purpose |
|------|---------|
| `api/` | HTTP webhook receivers (Calendly, etc.) |
| `channels/` | Channel abstraction layer |
| `discord/` | Discord-specific interface code |
| `presence/` | Primary presence layer (handlers, command routing) |

## §24 Reference

Canonical module tree §24: `interface/` — presence, API, channels.

## Boundary

Interface modules translate user intent into control plane requests.
They do NOT execute actions, access storage directly, or make governance
decisions.
