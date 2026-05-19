# Socket Layer — Executive Summary

**Date:** 2026-05-19
**Full reference:** `handoffs/socket-layer-design-report.md` (1000+ lines)
**Status:** Design complete, all decisions resolved. Awaiting implementation scope.

---

## What This Is

The socket layer (`services/umh/sockets/`) is the membrane between UMH and
external integrations (Notion, EntrepreneurOS, LYFEOS, Stripe, etc.). Four
typed sockets mediate all data flow. Integrations never call UMH internals.
UMH never imports from integrations. Sockets enforce Hard Invariant 8.

---

## The Four Sockets

### Signal Socket (Inbound → Stage 1)

Carries `SignalEnvelope`: integration_id, content_type, payload, optional
raw_content, source_identifier, correlation_id, urgency, metadata.
Integrations push events into UMH through this socket. The socket validates
the envelope, converts it to the internal `protocols.Signal` type, and calls
`ExecutionPipeline.submit_signal()`. Returns a `SignalReceipt` with signal_id
and trace_id. One-way: integration → UMH.

### Capability Socket (Bidirectional → Stage 5)

Carries `CapabilityRequest` (outbound): request_id, capability_name,
integration_id, params, governance_verdict_id, trace_id, timeout_seconds.
Returns `CapabilityResponse`: success, result_data, error, raw_error,
latency_ms, side_effects. UMH asks an integration to do something
(create a Notion page, charge a Stripe card). Fires during Stage 5
(WorkPacketExecutor). A generic `IntegrationAdapter` implements the existing
`AdapterProtocol` and delegates to the socket, so the pipeline's stages 4-5
work without modification.

### Outcome Socket (Outbound → after Stage 7 or Stage 3)

Carries `OutcomeEnvelope`: outcome_id, signal_id, trace_id, integration_id,
outcome_type, summary, result_data, governance_decision, confidence,
duration_ms, correlation_id, metadata. Fires after outcome classification
(Stage 7) or after governance denial (Stage 3). One-way push — integrations
receive notification of what happened to their signal. Dual-mode:
`notify()` sends to originating integration; `notify_all()` broadcasts.

### View Socket (Broadcast → Every Stage)

Carries `ViewFrame`: frame_id, timestamp, event_type, stage (1-10), data,
trace_id, signal_id, integration_id, metadata. Registered as an
`on_event()` listener on the pipeline. Every `_emit()` in the pipeline
produces a frame broadcast to all subscribers. The cockpit's primary data
source — a `WebSocketBridge` subscriber serializes frames to the existing
`CockpitSocket` `{ type, data }` JSON format over `/ws`.

---

## Registration Flow

An integration plugs in through `IntegrationRegistry`:

```
1. Integration builds an IntegrationManifest declaring:
   - integration_id (e.g. "notion")
   - SignalEmitter (optional — what signals it can push)
   - CapabilityHandler (optional — what capabilities it provides)
   - OutcomeReceiver (optional — whether it wants outcome notifications)
   - ViewSubscriber (optional — whether it wants pipeline observation)

2. Integration calls registry.register(manifest)

3. Registry wires each non-None component:
   - SignalEmitter → registered with SignalSocket
   - CapabilityHandler → registered with CapabilitySocket,
     generic IntegrationAdapter created and registered with
     WorkPacketExecutor as adapter_name=integration_id
   - OutcomeReceiver → registered with OutcomeSocket
   - ViewSubscriber → registered with ViewSocket

4. Integration is live. Signals flow in, capabilities fire,
   outcomes notify, view frames broadcast.
```

Per-integration config lives at `services/umh/integrations/{name}/`
(UMH-owned: manifest, transforms, routing rules). Handler implementations
(actual API calls) live outside UMH.

---

## Hard Invariant 8 Enforcement

**Mechanism:** Python `Protocol` (structural subtyping).

UMH defines `CapabilityHandler(Protocol)` in `services/umh/sockets/types.py`.
An integration implements a class with matching method signatures. The
integration never imports the Protocol — structural typing means the class
satisfies the Protocol by shape alone. UMH holds a reference typed as
`CapabilityHandler`; the actual object is integration code. The import graph
never crosses the boundary.

**Concrete example:**

```python
# UMH side — services/umh/sockets/types.py
class CapabilityHandler(Protocol):
    @property
    def integration_id(self) -> str: ...
    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse: ...

# Integration side — /opt/EOS/umh_integration/notion/handler.py
# Does NOT import CapabilityHandler. Satisfies it structurally.
class NotionHandler:
    @property
    def integration_id(self) -> str:
        return "notion"
    def handle_capability(self, request):  # CapabilityRequest from types.py
        ...
```

**Three enforcement tiers:**
1. Folder structure (structural, zero runtime cost) — primary
2. Runtime registration validation (`inspect.getmodule()` checks) — secondary
3. Import linting (CI hook, scans for forbidden imports) — deferred until 3+ integrations

---

## Notion Worked Example (Compressed)

```
Notion webhook fires "page_created"
  → NotionSignalEmitter builds SignalEnvelope(integration_id="notion", ...)
  → SignalSocket.emit(envelope) → validates, converts to Signal → pipeline.submit_signal()
  → Stage 3: governance evaluates READ_ONLY → APPROVE
  → Stage 5: if pipeline needs Notion action (e.g. update_page),
    IntegrationAdapter dispatches via CapabilitySocket → NotionHandler.handle_capability()
    → Notion API call → CapabilityResponse(success=True, page_id="xyz")
  → Stage 7: OutcomeSocket.notify() → NotionOutcomeReceiver.on_outcome()
    → Notion updates page status to "Processed"
  → Stages 1-10: ViewSocket broadcasts ViewFrames → WebSocketBridge
    → cockpit sees every stage in real-time
```

---

## Design Decisions (All Resolved)

### 1. Sync/Async — Option 3: Sync Pipeline on Background Thread

Pipeline stays sync (~800 lines untouched). `run_coroutine_threadsafe()`
pushes ViewFrames to the async FastAPI event loop. Thread boundary = clean
seam between processing and broadcasting.

### 2. Outcome Routing — Dual Mode

`notify()` targets the originating integration. `notify_all()` broadcasts
to all registered receivers. Covers both "tell Notion what happened to its
signal" and "tell everyone about a system-wide event."

### 3. Auth — Deferred Until Remote Integrations

No socket auth in V1. All integrations run in-process behind Tailscale.
Governance handles *what* can happen. Auth answers *who* is asking — irrelevant
with one trusted process.

**⚠ Gap trigger:** First integration running as a separate process (Notion MCP
server, EOS frontend calling from a different host). At that point: token-per-
integration, validated on every socket call, scope matching manifest declarations.

### 4. IntegrationAdapter — Generic Class + Per-Integration Directories

One `IntegrationAdapter` class in `sockets/registry.py` handles all integrations.
Each integration gets a config directory at `services/umh/integrations/{name}/`
with UMH-owned manifest, transforms, and routing rules. Handler code (actual API
calls) stays outside UMH.

### 5. Error Propagation — Socket Normalizes, Raw Preserved

Socket catches handler exceptions, wraps in `CapabilityResponse(success=False)`.
Pipeline continues normally. Two error fields:
- `error` — normalized, human-readable (what the pipeline traces)
- `raw_error` — original exception type + message (what a developer debugs)

### 6. WebSocket Endpoint — /ws on Existing FastAPI at 8093

Single server, single port. Vite proxy already configured.

---

## File Layout

```
services/umh/sockets/                     # Socket layer (new)
  __init__.py
  types.py            — all dataclasses, protocols, enums
  signal_socket.py    — SignalSocket (inbound)
  capability_socket.py — CapabilitySocket (bidirectional)
  outcome_socket.py   — OutcomeSocket (outbound)
  view_socket.py      — ViewSocket (broadcast)
  registry.py         — IntegrationRegistry + generic IntegrationAdapter
  ws_bridge.py        — WebSocketBridge (View → WebSocket)

services/umh/integrations/{name}/         # Per-integration config (new)
  __init__.py
  manifest.py         — socket declarations, descriptors, risk classes
  transforms.py       — payload translations
  routing.py          — signal routing rules
```

~600-800 lines for sockets/. ~100-150 lines per integration config dir.

---

## Suggested Implementation Order (Not Yet Authorized)

1. `types.py` — pure definitions, no dependencies
2. `view_socket.py` + `ws_bridge.py` — cockpit gets live data immediately
3. `signal_socket.py` — inbound path
4. `capability_socket.py` + `registry.py` — execution + registration
5. `outcome_socket.py` — closes the loop
6. Wire into `control_plane/app.py` and `pipeline.py`
7. Tests
