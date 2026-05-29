# Architecture Layer Law

UMH has four code layers with strict dependency direction:

```
projections/ (EOS, CreatorOS)  →  saas/ is an EOS projection
    ↓ can import from
transports/ (discord, api/http)  →  transports/api/http/ is UMH HTTP infrastructure
    ↓ can import from
adapters/ (models, GWS, browser)
    ↓ can import from
substrate/ (types, control_plane, execution, governance, state, organism)
```

**Dependency direction is one-way downward. Never upward. Never sideways between peers at the same level.**

## Before creating or moving ANY file, answer:

1. "Which layer does this belong to?" — If uncertain, it's probably substrate.
2. "Does it import from a layer above it?" — If yes, you're violating dependency direction. Use an abstract port in `substrate/sockets/` instead.
3. "Would a different projection need this?" — If yes, it's NOT projection-specific. It goes in `transports/` or `substrate/`, never in `saas/` or `projections/`.

## What lives where:

- `substrate/` — universal platform. Types, execution, governance, state, organism, sockets.
- `adapters/` — external system adapters. Model routing, calendar, browser, capabilities.
- `transports/` — I/O surfaces. Discord bot, API HTTP layer (auth, middleware, routes for organism/governance/system/dex/execution/settings), Python bridges, node mesh.
- `transports/api/http/` — UMH HTTP API infrastructure. Auth middleware, platform DB schema (users/orgs/portfolios), substrate route handlers, Python bridge spawner.
- `saas/` — EOS projection ONLY. EOS-specific routes (ventures, skills, agents, analytics), EOS DB schema (ventures, clients, transactions, offers), EOS seed data. Imports UMH infrastructure from `transports/api/http/`.
- `projections/` — projection-specific logic (EOS agent configs, workflows).
- `services/` — deployment entrypoints only. No business logic.

## Common mistakes this prevents:

- Putting auth middleware in `saas/` (it's UMH infra → `transports/api/http/middleware/`)
- Putting Python bridges in `saas/` (they're transport layer → `transports/api/`)
- Putting DB client/migrations in `saas/` (they're platform infra → `transports/api/http/db/`)
- Putting organism routes in `saas/` (they're substrate surface → `transports/api/http/routes/`)
- Having `substrate/` import from `transports/` (use `substrate/sockets/` abstract port)

Pre-commit hook enforces this: `scripts/check_dependency_direction.py`
