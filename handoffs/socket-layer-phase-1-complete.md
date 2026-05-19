# Handoff: Socket Layer Phase 1 Complete

**Date:** 2026-05-19
**Branch:** worktree-socket-layer-design
**Commit:** 512c8b76
**Status:** Phase 1 complete. Phase 2 NOT started.

---

## What was done

Built the socket layer framework at `services/umh/sockets/` — protocol
contracts, envelope dataclasses, four socket implementations, integration
registry, and generic adapter bridge. No pipeline or executor modifications.

### Files created (13)

| File | Lines | Purpose |
|------|-------|---------|
| `services/umh/sockets/__init__.py` | 43 | Public API exports |
| `services/umh/sockets/protocols.py` | 126 | Four Protocol classes (SignalEmitter, CapabilityHandler, OutcomeReceiver, ViewSubscriber), descriptor and health dataclasses |
| `services/umh/sockets/envelopes.py` | 95 | Frozen dataclasses: SignalEnvelope, CapabilityRequest, CapabilityResponse (with raw_error), OutcomeEnvelope, ViewFrame, SignalReceipt |
| `services/umh/sockets/signal_socket.py` | 95 | SignalSocket: emit(), register_emitter(), catalog validation |
| `services/umh/sockets/capability_socket.py` | 102 | CapabilitySocket: request(), register_handler(), error normalization at boundary |
| `services/umh/sockets/outcome_socket.py` | 76 | OutcomeSocket: notify() (targeted), notify_all() (broadcast), accepts_outcomes() filtering |
| `services/umh/sockets/view_socket.py` | 64 | ViewSocket: broadcast(), subscribe(), accepts_events() filtering |
| `services/umh/sockets/registry.py` | 167 | IntegrationManifest, IntegrationRegistry, generic IntegrationAdapter |
| `services/umh/integrations/__init__.py` | 6 | Package docstring |
| `services/umh/integrations/notion/__init__.py` | 10 | Package docstring with directory purpose |
| `services/umh/integrations/notion/manifest.py` | 61 | Template: signal and capability descriptors for future Notion integration |
| `services/umh/tests/test_socket_protocols.py` | 27 tests | Protocol existence, structural satisfaction via isinstance, envelope construction, descriptor defaults |
| `services/umh/tests/test_socket_registration.py` | 34 tests | All four sockets, registry wiring, adapter protocol conformance, error normalization |

### Test results

**109 passed, 0 failed** (48 existing + 61 new, 0.45s)

### What was NOT touched

- `services/umh/control_plane/pipeline.py` — closed for modification
- `services/umh/execution/executor.py` — closed for modification
- No existing files modified

---

## Architectural insights (preserved for future sessions)

### 1. @runtime_checkable enables isinstance tests but only checks attribute presence

All four Protocol classes use `@runtime_checkable`. This enables test
assertions like `assert isinstance(Dummy(), SignalEmitter)` — but the
runtime check only verifies that the required attributes/methods exist
on the object, not that their signatures match. Real type-safety (argument
types, return types) comes from static analysis via mypy/pyright. The
runtime check is a structural presence test, not a contract enforcement.

### 2. IntegrationAdapter intentionally does NOT inherit BaseAdapter

BaseAdapter adds deny-rule machinery (`_DENIED_OPERATIONS`,
`_DENIED_PATTERNS`, `_check_denied()`) designed for local adapters
(shell, filesystem, git) where UMH must block dangerous operations
before they reach the OS. Socket-mediated integration calls don't need
this — the governance layer already classified risk at Stage 3, and the
CapabilitySocket already normalizes errors at the boundary. Adding deny
rules would create a second, contradictory enforcement layer.

IntegrationAdapter satisfies `AdapterProtocol` directly (`name`,
`execute()`, `classify_risk()`) without inheriting the deny-rule base.
The executor only requires the Protocol; it doesn't check inheritance.

---

## Phase 2 plan: View Socket End-to-End

### Build

- `services/umh/sockets/view/broadcaster.py` — the sync→async bridge
  using `run_coroutine_threadsafe` to push ViewFrames to the FastAPI
  event loop
- `services/umh/sockets/view/websocket.py` — FastAPI /ws endpoint,
  connection manager, broadcast logic
- Wire `view_socket.broadcast()` as a listener on `pipeline.on_event()`
  during app startup (in the existing FastAPI app's lifespan hook)
- `apps/cockpit/src/lib/ws-client.ts` — WebSocket client that subscribes
  to /ws, parses ViewFrame messages, dispatches to Zustand store
- `apps/cockpit/src/stores/substrate.ts` (or wherever the existing store
  lives) — add live-state slice that ws-client writes into
- One existing cockpit view subscribes to that store and renders live
  state (pick simplest implemented view)

### Tests

- `test_view_socket_e2e.py` — start FastAPI test client, connect WS
  subscriber, submit a signal via the pipeline, assert ViewFrames stream
  through the WebSocket
- Manual: `cd apps/cockpit && npm run dev`, then `curl` a signal to
  `/api/umh/signal`, watch the cockpit render live

### Deliverables

- broadcaster.py file contents (sync→async bridge is load-bearing)
- WebSocket test pass result
- Description of what the cockpit renders during a live signal

---

## Phase 3 plan: Verify + Merge

- Full pytest pass: `pytest services/umh/tests/ -v`
- Full cockpit build: `cd apps/cockpit && npm run build`
- Commit with detailed message
- Merge `worktree-socket-layer-design` to main as 12th `--no-ff`
  consolidation

---

## Open questions to verify when starting Phase 2

### 1. OutcomeReceiver blocking risk

`OutcomeReceiver.on_outcome()` runs on the pipeline thread. If an
integration's network call takes seconds, it blocks the pipeline. The
View socket solves this with `run_coroutine_threadsafe` — should
OutcomeSocket get similar background-task isolation? Check whether the
"long-running receiver should defer to background task" docstring
contract is sufficient, or whether UMH should enforce non-blocking
delivery.

### 2. Which FastAPI app file?

The existing `/api/umh` endpoints live in
`services/umh/control_plane/app.py`. The new `/ws` endpoint adds to
this app's lifespan/startup hook. Verify this is still the correct
location and that CORS allows WebSocket upgrade from the cockpit's
origin (currently allows `localhost:5173` and `100.77.233.50:5173` —
cockpit runs on port 5174).

### 3. Which cockpit view for live-state demo?

Pick the simplest implemented view that can render live pipeline state.
Candidates: CommandCenter (has pulse, traces, approvals sections),
Activity (described as "real-time trace stream with WebSocket" in its
stub). Check which views have real rendering beyond `<ViewStub>`.
