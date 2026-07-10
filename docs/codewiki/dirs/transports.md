---
type: codewiki-dir
dir: transports
---

# `transports/` — I/O surfaces (Discord, HTTP API, CLI, node mesh)

**221 files · 2,047,311 bytes · [Full file inventory](../inventory/transports.md)**

## Purpose
`transports/` is where UMH meets the outside caller. It holds every I/O surface that
turns an inbound event — a Discord message, an HTTP request, a CLI keystroke, a
WebSocket frame from a remote node — into a `SignalEnvelope` the substrate can process,
and turns substrate results back into responses. It is the layer that owns *how* the
system is reached, not *what* it decides. The bulk of it is the cockpit HTTP API
(`transports/api/`, 169 files), plus the Discord transport, the operator CLI, the node
mesh WebSocket server, and the Discord presence/handler stack.

## How it fits
In the dependency order (`projections → transports → adapters → substrate`), transports
sits above `adapters/` and below `projections/`. It may import downward from adapters
and substrate but never from `projections/` or `services/`. Signal factories are the
canonical entry pattern: `transports/discord/signal_factory.py`,
`transports/api/signal_factory.py`, and the signal router
(`transports/api/signal_router.py`) enforce "the legal processing pathway for all
signals." State mutations from a transport route go through the governed path —
`transports/api/governed.py` (`governed_mutation()`), which the centrality query flags
as the single most-depended-on node in the graph (78 in-edges) — so no route writes
state directly.

The **`transports/api/http/` vs `saas/` ownership split** matters here (see
`.claude/rules/architecture-layers.md`): `transports/api/http/` is *UMH HTTP
infrastructure* — auth middleware (`middleware/auth.ts`, `operator.ts`), the platform
DB schema (`db/schema.ts`: users/orgs/portfolios), the Python bridge
(`lib/python_bridge.ts`), and substrate route handlers (`routes/organism.ts`,
`system.ts`, `execution.ts`, `governance.ts`). EOS-specific routes and schema belong in
`saas/`, which imports this infrastructure — not the reverse. (In this repo mirror
`saas/` carries only `bridge/` and `node_modules/`; the manifest reports 0 code files
for it. The EOS source truth lives on the Beast.)

## Structure

| Subdir | Files | Role |
|---|---|---|
| `api/` | 169 | The cockpit HTTP API. Python FastAPI routes (`cockpit_*.py`, ~120 route modules), the governed-mutation wrapper, signal factory/router, the organism bridge, plus the TypeScript `http/` infrastructure and `webhooks/`. |
| `presence/` | 23 | The Discord bot's handler stack — intent classification, inline command handlers, pipeline detection, and the 15 substrate "report" handlers (`reports/`). Imported by `services/discord_bot.py`. |
| `node_mesh/` | 12 | WebSocket mesh server (`server.py`, 1,172 lines) connecting remote nodes (Beast), plus registry, config/token loading, and the capability-handler integration. |
| `cli/` | 8 | The operator terminal — `main.py`, HTTP `client.py`, slash-command dispatch, Rich display, push-to-talk voice, WorldView theme tokens. |
| `discord/` | 6 | The Discord transport proper — `interface_adapter_v1.py`, `signal_factory.py`, `approval_bridge.py`, `discord_utils.py`, `spine_integration_v1.py`. |
| `channels/` | 2 | The EOS channel-routing system (`channel.py`). |
| root | 1 | `__init__.py` (empty package marker). |

## Key components

- **`transports/discord/signal_factory.py` (75 lines)** — converts a Discord message
  into a `SignalEnvelope`. This is the primary transport's ingress: it is where an
  external message becomes something the substrate governs. Confirmed runtime per
  CLAUDE.md.
- **`transports/discord/interface_adapter_v1.py` (503 lines)** — the Discord Interface
  Adapter; a graph entry point.
- **`transports/discord/approval_bridge.py` (235 lines)** — renders governance approvals
  as interactive Discord buttons; wired into the bot via `set_bot()`/`set_channel()`.
- **`transports/api/governed.py` (111 lines)** — `governed_mutation()`, the FastAPI
  wrapper that forces every route write through the governed path. Highest in-degree
  node in the whole graph (78 dependents).
- **`transports/api/organism_bridge.py` (2,538 lines)** — the largest file here; exposes
  organism subsystem state and actions to the API. A graph entry point.
- **`transports/api/cockpit_core_routes.py` (2,127)** and **`cockpit_rooms_routes.py`
  (2,371)** — the biggest route modules; both under the 3,000-line ceiling.
- **`transports/api/signal_router.py` (208 lines)** — enforces the legal processing
  pathway for all signals; the HTTP analogue of the Discord signal factory.
- **`transports/api/http/routes/organism.ts` (729 lines)** — the largest TypeScript
  route; the substrate organism surface over Hono.
- **`transports/node_mesh/server.py` (1,172 lines)** — the mesh WebSocket server that
  manages remote-node connections and dispatches work to Beast. Note this runs as a
  host process on `:8094`, not inside a Docker container (memory: mesh server is a host
  process — a Docker restart does not touch it).
- **`transports/presence/handlers/substrate_command_handler.py` (939 lines)** and
  **`intent_handler.py` (437)** — the live Discord command surface and gateway routing,
  imported directly by `services/discord_bot.py:162`.

## Data & state
- **Discord** — reads Gateway events, posts via webhook (`discord_utils.py` is the
  single source of truth for posting). Channel IDs come from config, never hardcoded
  literals.
- **HTTP API** — `transports/api/http/db/schema.ts` defines the platform DB (Neon):
  users, orgs, portfolios; auth via Clerk JWT (`cockpit_auth.py`).
- **Node mesh** — `node_mesh/config.py` loads mesh tokens; `server.py` tracks connected
  nodes in `registry.py`; metrics flow through a per-node ring buffer.
- **Webhooks** — `api/webhooks/calendly_webhook.py` (the `os-webhook` container entry
  point) and `services/higgsfield_webhook.py` receive external callbacks.

## Gotchas
- **Never write state directly from a route.** All mutations go through
  `governed_mutation()` (`transports/api/governed.py`). This is a permanent platform
  constraint (PLATFORM_SPEC / CLAUDE.md).
- **The `http/` vs `saas/` boundary is enforced.** `scripts/check_dependency_direction.py`
  blocks a transport importing upward; auth middleware, DB client, and Python bridges
  belong in `transports/api/http/`, not `saas/`. Do not move UMH infra into `saas/`.
- **Projection read surfaces have exactly one legal shape.** `/eos/*` read routes must
  be thin wrappers over a projection-owned accessor; only `/eos/activation` currently
  conforms, five others are sanctioned legacy on a shrink-only allowlist (see
  `.claude/rules/projection-read-surfaces.md`).
- **Mesh server restart ≠ Docker restart.** The `:8094` mesh WebSocket is a host process;
  restart it directly, not via `docker restart`.
- **Client-failure observability.** Voice/vision/desktop surfaces here can fail entirely
  in the browser and never hit the server — instrument the client beacon before shipping
  a second speculative fix (`.claude/rules/client-failure-observability.md`); the
  reference beacon is `transports/api/voice.py`'s `POST /api/umh/voice/diag`.
- **Read-path isolation.** Hot cockpit poll routes run through
  `transports/api/read_path_isolation.py` (P4S-31C) to keep reads off the write path.
- **`cockpit_core_eos_routes.py` is grandfathered** in the dependency gate's
  `LEGACY_VIOLATIONS` because it lazily imports `projections/` inside handlers — the
  sanctioned projection read-surface pattern, not a license for new upward imports.

## See also
- [dirs/adapters.md](adapters.md) — the adapter layer transports consume
- [dirs/services.md](services.md) — the deployment entry points that run these transports
- [dirs/substrate.md](substrate.md) — the governed core behind `governed_mutation()`
- [dirs/cockpit.md](cockpit.md) · [dirs/cockpit-renderer.md](cockpit-renderer.md) — the frontend the HTTP API serves
- [dirs/saas.md](saas.md) — the EOS projection that imports `transports/api/http/`
- [architecture.md](../architecture.md) · [data-flow.md](../data-flow.md) · [services-runtime.md](../services-runtime.md)
