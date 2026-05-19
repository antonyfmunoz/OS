# Socket Layer Design Report — services/umh/sockets/

**Date:** 2026-05-19
**Author:** Developer Agent
**Status:** DESIGN ONLY — no implementation until reviewed
**Scope:** Four socket types (Signal, Capability, Outcome, View) mediating
between UMH substrate and external integrations

---

## Preamble: Why "Sockets"

The term "socket" here is architectural, not network. A UMH socket is a
**typed, governed, uni-directional port** — an explicit boundary where data
crosses between UMH and an integration. Each socket defines:

- A protocol contract (what shape the data is)
- A direction (inbound to UMH, outbound from UMH, or observation-only)
- A pipeline attachment point (which stage it touches)
- An enforcement mechanism (how Hard Invariant 8 is preserved)

Integrations never call UMH internals. UMH never imports from integrations.
Sockets are the membrane.

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────┐
                    │              INTEGRATION SIDE               │
                    │  (Notion, EntrepreneurOS, LYFEOS, etc.)     │
                    │                                             │
                    │  Implements: SignalEmitter, CapabilityHandler│
                    │  Consumes:   OutcomeReceiver, ViewSubscriber │
                    └────────┬──────────┬──────────┬──────────┬───┘
                             │          │          │          │
                        SIGNAL ↓    CAP ↑↓    OUTCOME ↓   VIEW ↓
                             │          │          │          │
                    ┌────────┴──────────┴──────────┴──────────┴───┐
                    │           services/umh/sockets/              │
                    │                                             │
                    │  signal_socket.py   — inbound intake        │
                    │  capability_socket.py — bidirectional exec  │
                    │  outcome_socket.py  — outbound results      │
                    │  view_socket.py     — outbound observation  │
                    │  registry.py        — integration registry  │
                    │  types.py           — shared socket types   │
                    └────────┬──────────┬──────────┬──────────┬───┐
                             │          │          │          │
                    ┌────────┴──────────┴──────────┴──────────┴───┘
                    │           ExecutionPipeline (10 stages)      │
                    │           EventBus (async pub/sub)           │
                    │           SubstrateRuntime                   │
                    └─────────────────────────────────────────────┘
```

---

## 1. SIGNAL SOCKET (Inbound)

### 1.1 Protocol Contract

```python
@dataclass(frozen=True)
class SignalEnvelope:
    """What an integration hands to the Signal socket."""

    integration_id: str          # registered name, e.g. "notion", "eos"
    content_type: str            # e.g. "page_created", "task_updated", "webhook"
    payload: dict[str, Any]      # integration-specific data
    raw_content: str | None      # optional human-readable summary
    source_identifier: str | None  # e.g. Notion page ID, EOS task ID
    correlation_id: UUID | None  # for request-response pairing
    urgency: SignalUrgency       # reuses existing protocol enum
    metadata: dict[str, Any]     # integration can attach anything
```

**Minimal shape:** `integration_id` + `content_type` + `payload`.
Everything else is optional metadata.

**Relationship to existing protocols:** The socket converts
`SignalEnvelope` → `protocols.signal.Signal` internally, setting
`source=SignalSource.EXTERNAL_API` and preserving the integration_id
in `metadata["integration_id"]`.

### 1.2 Pipeline Relationship

**Feeds: Stage 1 (Signal creation)**

The Signal socket is the only inbound path for external integrations.
It sits *before* the pipeline — it calls `ExecutionPipeline.submit_signal()`
or `SubstrateRuntime.ingest_signal()` depending on whether the signal
requires full governed execution or just event-sourced routing.

Flow:
```
Integration calls → SignalSocket.emit(envelope)
  → validates envelope
  → converts to protocols.Signal
  → calls pipeline.submit_signal() or runtime.ingest_signal()
  → returns SignalReceipt (signal_id, trace_id, accepted_at)
```

### 1.3 Integration-Side Contract

An integration implements:

```python
class SignalEmitter(Protocol):
    """What an integration provides to push signals into UMH."""

    @property
    def integration_id(self) -> str: ...

    def describe_signals(self) -> list[SignalDescriptor]: ...
        # Declares what signal types this integration can emit
        # e.g. [SignalDescriptor("page_created", "Notion page was created")]

    # The integration does NOT call UMH directly.
    # It registers with the socket, then calls:
    #   socket.emit(SignalEnvelope(...))
    # The socket is injected during registration.
```

`SignalDescriptor` is a simple frozen dataclass:
```python
@dataclass(frozen=True)
class SignalDescriptor:
    content_type: str      # what the integration calls this event
    description: str       # human-readable purpose
    default_urgency: SignalUrgency = SignalUrgency.NORMAL
    default_risk_class: RiskClass = RiskClass.READ_ONLY
```

### 1.4 UMH-Side Adapter

```python
class SignalSocket:
    """UMH's inbound socket for external signals."""

    def __init__(self, pipeline: ExecutionPipeline) -> None: ...

    def emit(self, envelope: SignalEnvelope) -> SignalReceipt: ...
        # Validates → converts → submits → returns receipt

    def register_emitter(self, emitter: SignalEmitter) -> None: ...
        # Records which integration_id can send what content_types
        # Rejects duplicate integration_id registration

    def registered_integrations(self) -> list[str]: ...

    def signal_catalog(self) -> dict[str, list[SignalDescriptor]]: ...
        # Returns {integration_id: [descriptors]} for introspection
```

`SignalReceipt`:
```python
@dataclass(frozen=True)
class SignalReceipt:
    signal_id: UUID
    trace_id: UUID
    accepted: bool
    accepted_at: datetime
    rejection_reason: str | None = None
```

### 1.5 Worked Example: Notion

**Notion side** (lives in e.g. `/opt/EOS/umh_integration/notion/`):
```
NotionSignalEmitter:
  integration_id = "notion"
  describe_signals() = [
    SignalDescriptor("page_created", "New Notion page", NORMAL, READ_ONLY),
    SignalDescriptor("page_updated", "Notion page edited", LOW, READ_ONLY),
    SignalDescriptor("database_entry_added", "New DB row", NORMAL, READ_ONLY),
  ]

When Notion webhook fires:
  envelope = SignalEnvelope(
    integration_id="notion",
    content_type="page_created",
    payload={"page_id": "abc-123", "title": "Q3 Revenue Plan", "database": "Projects"},
    raw_content="New page: Q3 Revenue Plan in Projects database",
    source_identifier="notion:abc-123",
  )
  receipt = signal_socket.emit(envelope)
```

**UMH side:**
```
SignalSocket receives envelope
  → validates integration_id "notion" is registered
  → validates content_type "page_created" is in the catalog
  → creates Signal(source=EXTERNAL_API, content_type="page_created",
      payload={...}, metadata={"integration_id": "notion"})
  → calls pipeline.submit_signal(
      content="New page: Q3 Revenue Plan in Projects database",
      source=SignalSource.EXTERNAL_API,
      risk_class=RiskClass.READ_ONLY,  # from descriptor default
    )
  → pipeline runs 10 stages
  → returns SignalReceipt(signal_id=..., trace_id=..., accepted=True)
```

### 1.6 Hard Invariant 8 Enforcement

- UMH never imports from the Notion integration
- `SignalSocket` lives in `services/umh/sockets/`
- `NotionSignalEmitter` lives outside UMH (e.g. `/opt/EOS/umh_integration/notion/`)
- The emitter calls `socket.emit()` — the socket never calls the emitter
- Direction: integration → socket → pipeline (one-way)

---

## 2. CAPABILITY SOCKET (Bidirectional)

### 2.1 Protocol Contract

```python
@dataclass(frozen=True)
class CapabilityRequest:
    """UMH asks an integration to do something."""

    request_id: UUID           # generated by socket
    capability_name: str       # what UMH needs done, e.g. "create_page"
    integration_id: str        # who should handle it
    params: dict[str, Any]     # operation-specific data
    governance_verdict_id: UUID  # proof that governance approved this
    trace_id: UUID             # links to pipeline trace
    timeout_seconds: float     # max wait time
    metadata: dict[str, Any]

@dataclass(frozen=True)
class CapabilityResponse:
    """Integration's answer to a capability request."""

    request_id: UUID           # correlates to CapabilityRequest
    success: bool
    result_data: dict[str, Any]  # integration-specific output
    error: str | None          # normalized, human-readable
    raw_error: str | None      # original exception type + message, unmodified
    latency_ms: float
    side_effects: list[str]    # what changed in the external system
    metadata: dict[str, Any]
```

**Minimal shape:** `request_id` + `capability_name` + `integration_id` + `params` +
`governance_verdict_id` + `trace_id`.

**Relationship to existing protocols:** `CapabilityRequest` maps to
`protocols.adapter.AdapterRequest` internally. `CapabilityResponse` maps to
`protocols.adapter.AdapterResponse`. The socket translates between the
integration-facing vocabulary and the internal adapter vocabulary.

### 2.2 Pipeline Relationship

**Fires at: Stage 5 (WorkPacketExecutor / adapter execution)**

When the pipeline reaches Stage 5 and the work packet's assigned adapter
is an integration adapter (not shell/filesystem/git), the executor
dispatches through the Capability socket instead of calling a local adapter.

Flow:
```
Pipeline Stage 5: executor.execute(packet, verdict, adapter_name="notion", ...)
  → IntegrationAdapter.execute(operation, params)
    → CapabilitySocket.request(CapabilityRequest(...))
      → looks up registered handler for "notion"
      → calls handler.handle_capability(request)
      → handler calls Notion API
      → returns CapabilityResponse
    → converts to dict for executor
  → executor wraps in ExecutionResult + Proof
  → pipeline continues to Stage 6
```

The Capability socket does NOT bypass governance. The work packet already
carries `governance_verdict_id` from Stage 3. The socket propagates it
to the integration so the integration can log it for its own audit.

### 2.3 Integration-Side Contract

```python
class CapabilityHandler(Protocol):
    """What an integration implements to receive capability requests from UMH."""

    @property
    def integration_id(self) -> str: ...

    def describe_capabilities(self) -> list[CapabilityDescriptor]: ...
        # Declares what this integration can do
        # e.g. [CapabilityDescriptor("create_page", COMMUNICATE, {...})]

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse: ...
        # Synchronous: integration executes the request and returns result
        # The integration is responsible for its own error handling
        # Must return within request.timeout_seconds

    def health(self) -> CapabilityHealth: ...
        # Current status: healthy/degraded/unavailable
```

`CapabilityDescriptor`:
```python
@dataclass(frozen=True)
class CapabilityDescriptor:
    name: str                          # "create_page", "update_row", etc.
    category: CapabilityCategory       # reuses existing protocol enum
    risk_class: RiskClass              # default risk for this capability
    input_schema: dict[str, Any]       # JSON Schema for params
    output_schema: dict[str, Any]      # JSON Schema for result_data
    description: str = ""
    cost_estimate: float = 0.0         # estimated cost per invocation
    rate_limit: int | None = None      # max invocations per minute
```

### 2.4 UMH-Side Adapter

Two components work together:

**CapabilitySocket** (in `services/umh/sockets/`):
```python
class CapabilitySocket:
    """Routes capability requests to registered integration handlers."""

    def register_handler(self, handler: CapabilityHandler) -> None: ...
    def request(self, req: CapabilityRequest) -> CapabilityResponse: ...
    def capability_catalog(self) -> dict[str, list[CapabilityDescriptor]]: ...
    def health_check(self, integration_id: str) -> CapabilityHealth: ...
```

**IntegrationAdapter** (generic, in `services/umh/sockets/registry.py`):

A thin adapter that implements `AdapterProtocol` (the existing executor
interface) and delegates to the CapabilitySocket:

```python
class IntegrationAdapter(BaseAdapter):
    """Bridges the executor's AdapterProtocol to the CapabilitySocket."""

    def __init__(self, integration_id: str, socket: CapabilitySocket) -> None: ...

    @property
    def name(self) -> str:
        return self.integration_id

    def classify_risk(self, operation: str, params: dict) -> RiskClass:
        # Looks up the CapabilityDescriptor for this operation
        # Returns its declared risk_class

    def _execute_impl(self, operation: str, params: dict) -> dict:
        # Builds CapabilityRequest
        # Calls socket.request(req)
        # Converts CapabilityResponse → dict for executor
```

This means integrations are registered as adapters in the executor,
so the existing pipeline stages 4-5 work without modification. The
`IntegrationAdapter` is the only new class that lives inside
`services/umh/` — it's a UMH-owned bridge, not integration code.

### 2.5 Worked Example: Notion

**Notion side:**
```
NotionCapabilityHandler:
  integration_id = "notion"
  describe_capabilities() = [
    CapabilityDescriptor("create_page", COMMUNICATE, EXTERNAL_COMMUNICATION,
      input_schema={"title": str, "database_id": str, "properties": dict},
      output_schema={"page_id": str, "url": str}),
    CapabilityDescriptor("update_page", COMMUNICATE, EXTERNAL_COMMUNICATION,
      input_schema={"page_id": str, "properties": dict},
      output_schema={"page_id": str, "updated": bool}),
    CapabilityDescriptor("query_database", RETRIEVE, READ_ONLY,
      input_schema={"database_id": str, "filter": dict},
      output_schema={"results": list, "count": int}),
  ]

  handle_capability(request):
    if request.capability_name == "create_page":
      page = notion_client.pages.create(
        parent={"database_id": request.params["database_id"]},
        properties=request.params["properties"],
      )
      return CapabilityResponse(
        request_id=request.request_id,
        success=True,
        result_data={"page_id": page["id"], "url": page["url"]},
        side_effects=["notion:page_created:" + page["id"]],
      )
```

**UMH side:**
```
Pipeline receives signal: "Create a project page for Q3 Revenue"
  Stage 3: governance evaluates EXTERNAL_COMMUNICATION → DENY (default policy)
  ... but if caller passes pre_approved=True (human said "do it"):
  Stage 4: WorkPacket created, assigned_adapter="notion"
  Stage 5: executor looks up "notion" adapter → finds IntegrationAdapter
    → IntegrationAdapter._execute_impl("create_page", {"title": "Q3 Revenue", ...})
    → CapabilitySocket.request(CapabilityRequest(...))
    → NotionCapabilityHandler.handle_capability(request)
    → Notion API call
    → CapabilityResponse(success=True, result_data={"page_id": "xyz"})
    → IntegrationAdapter converts → {"page_id": "xyz", "url": "..."}
  Stage 6: Proof generated (evidence includes governance_verdict_id)
  Stage 7: Outcome classified as ACTION_COMPLETED
  ... stages 8-10 complete
```

### 2.6 Hard Invariant 8 Enforcement

- `IntegrationAdapter` lives in `services/umh/sockets/registry.py`
  — this is UMH-owned code that knows how to talk to the socket
- `NotionCapabilityHandler` lives outside UMH
- UMH never imports `NotionCapabilityHandler` — it only knows the
  `CapabilityHandler` protocol from `services/umh/sockets/types.py`
- The handler is registered at startup; the socket stores a reference
- Direction: pipeline → socket → handler → external API (UMH initiates)

---

## 3. OUTCOME SOCKET (Outbound)

### 3.1 Protocol Contract

```python
@dataclass(frozen=True)
class OutcomeEnvelope:
    """What UMH sends to integrations when a pipeline completes."""

    outcome_id: UUID
    signal_id: UUID            # the originating signal
    trace_id: UUID             # full trace reference
    integration_id: str        # which integration originated this signal
    outcome_type: str          # from OutcomeClassifier: success/failure/etc.
    summary: str               # human-readable one-liner
    result_data: dict[str, Any]  # capability response data (if any)
    governance_decision: str   # approve/deny/defer/escalate
    confidence: float          # classifier confidence
    duration_ms: float         # total pipeline duration
    correlation_id: UUID | None  # for request-response pairing
    metadata: dict[str, Any]
```

**Minimal shape:** `outcome_id` + `signal_id` + `trace_id` + `outcome_type` + `summary`.

This is a one-way notification. Integrations receive it but don't respond.

### 3.2 Pipeline Relationship

**Emits after: Stage 7 (Outcome classification) or after Stage 3 (governance denial)**

Two emission points:

1. **Successful execution path** — after Stage 7 classifies the outcome,
   the Outcome socket fires if the originating signal came from a registered
   integration (checked via `metadata["integration_id"]`).

2. **Governance denial path** — after Stage 3, if governance denies the
   signal and it came from a registered integration, the Outcome socket
   fires with `outcome_type="governance_denied"`.

In both cases, emission happens *before* Stages 8-10 (trace store, memory,
promotion). The integration gets notified as soon as UMH knows the result,
not after all internal bookkeeping completes.

Flow:
```
Pipeline Stage 7 completes (or Stage 3 denies):
  → OutcomeSocket.notify(envelope)
    → looks up receiver for integration_id
    → calls receiver.on_outcome(envelope)
    → receiver processes asynchronously (socket doesn't wait)
```

### 3.3 Integration-Side Contract

```python
class OutcomeReceiver(Protocol):
    """What an integration implements to receive outcome notifications."""

    @property
    def integration_id(self) -> str: ...

    def on_outcome(self, envelope: OutcomeEnvelope) -> None: ...
        # Fire-and-forget notification
        # Integration handles its own persistence/retry
        # Must not block — UMH does not wait for this

    def accepts_outcomes(self) -> list[str]: ...
        # Which outcome_types this receiver cares about
        # Empty list = all outcomes
        # e.g. ["success", "governance_denied"] to skip timeouts
```

### 3.4 UMH-Side Adapter

```python
class OutcomeSocket:
    """Delivers outcome notifications to registered integrations."""

    def register_receiver(self, receiver: OutcomeReceiver) -> None: ...

    def notify(self, envelope: OutcomeEnvelope) -> None: ...
        # Looks up receiver by integration_id
        # Checks accepts_outcomes() filter
        # Calls on_outcome() — catches exceptions, logs, continues

    def notify_all(self, envelope: OutcomeEnvelope) -> None: ...
        # Broadcasts to all registered receivers (for system-wide events)

    def registered_receivers(self) -> list[str]: ...
```

The pipeline hooks into this via on_event(). After the pipeline calls
`_emit("outcome", {...})`, a registered listener on the pipeline builds
an `OutcomeEnvelope` and calls `OutcomeSocket.notify()`.

### 3.5 Worked Example: Notion

**Notion side:**
```
NotionOutcomeReceiver:
  integration_id = "notion"
  accepts_outcomes() = ["success", "partial", "failure", "governance_denied"]

  on_outcome(envelope):
    if envelope.outcome_type == "success":
      # Update the originating Notion page's status property
      notion_client.pages.update(
        page_id=envelope.metadata.get("source_page_id"),
        properties={"UMH Status": {"select": {"name": "Processed"}}},
      )
    elif envelope.outcome_type == "governance_denied":
      # Add a comment to the Notion page explaining why
      notion_client.comments.create(
        parent={"page_id": envelope.metadata.get("source_page_id")},
        rich_text=[{"text": {"content": f"UMH: {envelope.summary}"}}],
      )
```

**UMH side:**
```
Pipeline completes Stage 7 with outcome "success"
  → Pipeline's on_event listener fires
  → Builds OutcomeEnvelope(
      signal_id=...,
      trace_id=...,
      integration_id="notion",  # from signal metadata
      outcome_type="success",
      summary="Created project page: Q3 Revenue",
      result_data={"page_id": "xyz", "url": "..."},
      governance_decision="approve",
    )
  → OutcomeSocket.notify(envelope)
  → Looks up "notion" receiver → found
  → Calls NotionOutcomeReceiver.on_outcome(envelope)
  → Notion updates page status to "Processed"
```

### 3.6 Hard Invariant 8 Enforcement

- `OutcomeSocket` lives in `services/umh/sockets/`
- `NotionOutcomeReceiver` lives outside UMH
- UMH calls `receiver.on_outcome()` through the protocol interface
- UMH never imports from the Notion integration
- Direction: pipeline → socket → receiver (one-way push)

---

## 4. VIEW SOCKET (Outbound / Observation)

### 4.1 Protocol Contract

```python
@dataclass(frozen=True)
class ViewFrame:
    """A single frame of pipeline state for external observers."""

    frame_id: UUID
    timestamp: datetime
    event_type: str           # matches pipeline event types: signal, governance,
                              # work_packet, execution, proof, outcome,
                              # memory_candidate, memory_promotion, trace
    stage: int                # 1-10 pipeline stage number
    data: dict[str, Any]      # the event payload (same as on_event data)
    trace_id: UUID | None     # which trace this belongs to
    signal_id: UUID | None    # which signal triggered this
    integration_id: str | None  # if from an integration signal
    metadata: dict[str, Any]
```

**Minimal shape:** `frame_id` + `event_type` + `data` + `timestamp`.

The View socket is a **broadcast** — every frame goes to every subscriber.
It does NOT carry sensitive data beyond what on_event() already emits
(signal content is truncated to 120 chars in the existing pipeline).

### 4.2 Pipeline Relationship

**Emits at: Every stage (1-10) via on_event()**

The View socket registers as an `on_event()` listener on the
ExecutionPipeline. Every `_emit()` call in the pipeline produces a
ViewFrame that gets broadcast to all subscribers.

This is the **cockpit's primary data source**. The existing
`CockpitSocket` WebSocket class in the frontend already expects
`{ type: string, data: unknown }` messages — ViewFrames serialize
directly to this shape.

Flow:
```
Pipeline._emit("governance", {verdict_id, decision, approved})
  → ViewSocket listener receives (event_type="governance", data={...})
  → Wraps in ViewFrame(event_type="governance", stage=3, data={...})
  → Broadcasts to all subscribers
  → WebSocket bridge serializes and sends to connected cockpit clients
```

### 4.3 Integration-Side Contract

```python
class ViewSubscriber(Protocol):
    """What an observer implements to receive pipeline state frames."""

    @property
    def subscriber_id(self) -> str: ...

    def on_frame(self, frame: ViewFrame) -> None: ...
        # Fire-and-forget frame delivery
        # Subscriber handles buffering, rendering, etc.
        # Must not block

    def accepts_events(self) -> list[str]: ...
        # Which event_types to receive
        # Empty list = all events
        # e.g. ["governance", "outcome"] for a governance dashboard
```

For the cockpit specifically, the subscriber is a WebSocket bridge
that lives inside UMH (not an external integration). This is
intentional — the cockpit is an operator tool, not an integration.

For external integrations that want to observe pipeline activity
(e.g., EntrepreneurOS dashboard), they register as ViewSubscribers
through the same socket.

### 4.4 UMH-Side Adapter

```python
class ViewSocket:
    """Broadcasts pipeline state frames to all subscribers."""

    def subscribe(self, subscriber: ViewSubscriber) -> None: ...
    def unsubscribe(self, subscriber_id: str) -> None: ...

    def broadcast(self, frame: ViewFrame) -> None: ...
        # Iterates all subscribers
        # Checks accepts_events() filter
        # Calls on_frame() — catches exceptions, logs, continues

    def subscriber_count(self) -> int: ...
    def active_subscribers(self) -> list[str]: ...
```

**WebSocket bridge** (in `services/umh/sockets/ws_bridge.py`):

```python
class WebSocketBridge:
    """Bridges ViewSocket frames to WebSocket connections for the cockpit."""

    def __init__(self, view_socket: ViewSocket) -> None: ...
        # Registers self as a ViewSubscriber
        # subscriber_id = "cockpit_ws_bridge"

    async def websocket_handler(self, websocket: WebSocket) -> None: ...
        # FastAPI WebSocket endpoint handler
        # Accepts connection, adds to connection set
        # On ViewFrame: serializes to JSON, sends to all connections
        # Handles ping/pong heartbeat
        # Cleans up on disconnect

    def on_frame(self, frame: ViewFrame) -> None: ...
        # Queues frame for async broadcast to WebSocket connections
```

This bridge gets mounted on the FastAPI app at `/ws`:
```python
# In control_plane/app.py
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await ws_bridge.websocket_handler(websocket)
```

### 4.5 Worked Example: Notion

Notion as an integration doesn't typically subscribe to the View socket
(it uses OutcomeSocket for results). But for completeness:

**Notion dashboard side** (hypothetical):
```
NotionViewSubscriber:
  subscriber_id = "notion_dashboard"
  accepts_events() = ["outcome", "governance"]

  on_frame(frame):
    # Push to Notion's own monitoring dashboard
    # e.g., update a Notion database with pipeline metrics
```

**More relevant: Cockpit (primary consumer):**
```
Pipeline processes a Notion-originated signal:
  Stage 1: _emit("signal", {signal_id, content})
    → ViewSocket broadcasts ViewFrame(event_type="signal", stage=1, ...)
    → WebSocketBridge serializes: {"type": "signal", "data": {...}}
    → Cockpit CockpitSocket.handler receives
    → Zustand store updates traces[]

  Stage 3: _emit("governance", {verdict_id, decision, approved})
    → ViewSocket broadcasts ViewFrame(event_type="governance", stage=3, ...)
    → WebSocketBridge serializes: {"type": "governance", "data": {...}}
    → Cockpit updates approval queue if decision != "approve"

  Stage 5: _emit("execution", {result_id, outcome, success, duration_ms})
    → ViewSocket broadcasts ViewFrame(event_type="execution", stage=5, ...)
    → WebSocketBridge serializes: {"type": "execution", "data": {...}}
    → Cockpit updates active trace with execution result

  ... all 10 stages visible in real-time in the cockpit
```

### 4.6 Hard Invariant 8 Enforcement

The View socket has a nuance: the cockpit WebSocket bridge lives *inside*
`services/umh/sockets/` because the cockpit is an operator tool, not an
integration. This is correct — the cockpit is part of UMH's own
observability surface, like the FastAPI health endpoint.

For external ViewSubscribers (like an EOS dashboard), the same rules apply:
- `ViewSocket` lives in `services/umh/sockets/`
- The subscriber lives outside UMH
- UMH calls `subscriber.on_frame()` through the protocol
- UMH never imports from the subscriber's codebase

---

## 5. INTEGRATION REGISTRATION — The Startup Sequence

All four sockets connect through a single `IntegrationRegistry`:

```python
class IntegrationManifest:
    """Declares what an integration provides and consumes."""

    integration_id: str
    signal_emitter: SignalEmitter | None
    capability_handler: CapabilityHandler | None
    outcome_receiver: OutcomeReceiver | None
    view_subscriber: ViewSubscriber | None

class IntegrationRegistry:
    """Central registration point for all integrations."""

    def register(self, manifest: IntegrationManifest) -> None: ...
        # Registers each non-None component with the appropriate socket
        # Creates IntegrationAdapter if capability_handler is present
        # Registers IntegrationAdapter with WorkPacketExecutor

    def unregister(self, integration_id: str) -> None: ...
    def registered(self) -> list[str]: ...
    def health(self) -> dict[str, CapabilityHealth]: ...
```

**Startup sequence:**
```
1. SubstrateRuntime starts
2. ExecutionPipeline created
3. Socket layer created (Signal, Capability, Outcome, View sockets)
4. WebSocket bridge created, subscribed to View socket
5. View socket listener registered on pipeline via on_event()
6. Integrations register via IntegrationRegistry
   → Each integration provides a manifest
   → Registry wires everything
7. FastAPI app starts, /ws endpoint available
```

---

## 6. HARD INVARIANT 8 — Integration Boundary Exclusivity

### 6.1 Design-Level Enforcement

**Physical folder boundary:**
```
services/umh/sockets/              ← UMH-owned socket definitions + protocols
services/umh/integrations/<name>/  ← UMH-owned config per integration (manifest, transforms, routing)
<external>/                        ← Integration-owned handlers (actual API calls)
```

**Import direction (enforced):**
```
Integration code → imports from services.umh.sockets.types (protocols only)
UMH code        → never imports from integration code
```

### 6.2 Enforcement Mechanisms (ranked by recommendation)

**Tier 1: Folder structure** (structural, zero runtime cost)
- `services/umh/sockets/types.py` exports ONLY protocol types and dataclasses
- Integrations import only from `services.umh.sockets.types`
- No integration code lives inside `services/umh/`

**Tier 2: Runtime registration validation** (in `IntegrationRegistry.register()`)
- Verifies the manifest's handler objects satisfy the Protocol interfaces
- Rejects objects that import from `services.umh` internals (via `inspect.getmodule()`)
- Logs registration with full integration_id for audit

**Tier 3: Import linting** (CI / pre-commit hook)
- A simple script that scans integration code for imports from `services.umh.*`
  excluding `services.umh.sockets.types`
- Fails the build if detected
- Can be added to `ruff` or as a standalone check

**Recommendation:** Start with Tier 1 (folder structure) + Tier 2 (runtime
registration). Add Tier 3 only if the integration ecosystem grows beyond
2-3 integrations where accidental imports become a real risk.

### 6.3 What lives where

| Component | Location | Owned by |
|-----------|----------|----------|
| Socket protocols (SignalEnvelope, etc.) | `services/umh/sockets/types.py` | UMH |
| Socket implementations (SignalSocket, etc.) | `services/umh/sockets/*.py` | UMH |
| IntegrationAdapter (generic) | `services/umh/sockets/registry.py` | UMH |
| IntegrationRegistry | `services/umh/sockets/registry.py` | UMH |
| WebSocket bridge | `services/umh/sockets/ws_bridge.py` | UMH |
| Per-integration config (manifest, transforms, routing) | `services/umh/integrations/<name>/` | UMH |
| Handler implementations (actual API calls) | `<external>/umh_integration/<name>/` | Integration |
| Handler Protocol definitions | `services/umh/sockets/types.py` | UMH |

---

## 7. DESIGN DECISIONS (Resolved 2026-05-19)

### 7.1 Sync vs Async — DECIDED: Option 3

Sync pipeline on background thread. `run_coroutine_threadsafe()` pushes
ViewFrames to the async FastAPI event loop. Pipeline code stays sync.
WebSocket bridge is the only async component.

**Rationale:** Keeps ~800 lines of pipeline/executor/proof code untouched.
Thread boundary maps 1:1 to the conceptual boundary between "processing"
and "broadcasting."

### 7.2 Outcome Routing — DECIDED: Dual Mode

`notify()` sends to the originating integration only.
`notify_all()` broadcasts to all registered receivers.

Signal → 1 integration. Capability → 1 integration. Outcome → 1 or all.
View → all subscribers (broadcast by design).

### 7.3 Auth at Socket Boundary — DECIDED: Deferred

No auth on sockets in V1. All integrations run in-process. Governance
handles authorization for *what* can happen; auth at the socket boundary
answers *who* is asking — irrelevant when there's one trusted process.

#### ⚠ AUTH DEFERRED UNTIL REMOTE INTEGRATIONS

**Gap:** When integrations move to separate processes (MCP servers,
microservices, remote webhooks), the socket boundary becomes a network
boundary. At that point:

- Each integration needs an identity token validated on every socket call
- Token scope should match the integration's manifest (which sockets it
  registered for, which capabilities it declared)
- The `IntegrationRegistry.register()` method becomes the auth handshake
- WebSocket connections need auth headers or ticket-based auth

**Trigger to revisit:** First integration that runs as a separate process
(likely Notion MCP server or EOS frontend calling POST /api/umh/signal
from a different host).

**What's safe now:** Localhost-only FastAPI, in-process registration,
Tailscale network boundary.

**What breaks without auth:** Any integration reachable from outside
Tailscale, any multi-tenant scenario, any integration the founder didn't
personally deploy.

### 7.4 Outcome Correlation — DECIDED: correlation_id Propagation

Integration sets `correlation_id` on `SignalEnvelope`. UMH carries it
through the pipeline unchanged. `OutcomeEnvelope` returns it.
Integration owns its own `correlation_id → internal_state` mapping.
UMH never stores integration-side correlation state.

### 7.5 IntegrationAdapter Location — DECIDED: Generic Class + Per-Integration Directories

One generic `IntegrationAdapter` class in `services/umh/sockets/registry.py`.
All integrations use it — no Notion-specific adapter code inside UMH.

Each integration ALSO gets a per-integration directory at
`services/umh/integrations/{name}/` containing UMH-owned configuration:

```
services/umh/integrations/notion/
  __init__.py       — exports manifest for registration
  manifest.py       — declares sockets used, signal descriptors,
                      capability descriptors, default risk classes
  transforms.py     — payload translations (Notion's nested property
                      format → flat dict, and vice versa)
  routing.py        — integration-specific signal routing rules
                      (e.g., "page_created in DB X → READ_ONLY,
                       page_created in DB Y → REVERSIBLE_WRITE")
```

This is UMH's *configuration and translation layer* for the integration.
The handler implementation (code that actually calls the Notion API)
still lives outside UMH. The generic `IntegrationAdapter` reads manifests
and transforms from these directories at registration time.

### 7.6 Error Propagation — DECIDED: Socket Normalizes with Raw Preservation

Socket catches all exceptions from `CapabilityHandler`, wraps in
`CapabilityResponse(success=False)`. Pipeline continues normally through
proof/outcome/trace stages. The error is visible in the trace.

**Added requirement:** The normalized `CapabilityResponse` preserves the
raw integration-specific error in a `raw_error` field:

```python
@dataclass(frozen=True)
class CapabilityResponse:
    request_id: UUID
    success: bool
    result_data: dict[str, Any]
    error: str | None          # normalized, human-readable
    raw_error: str | None      # original exception type + message, unmodified
    latency_ms: float
    side_effects: list[str]
    metadata: dict[str, Any]
```

`error` is what the pipeline sees and traces. `raw_error` is what a
developer reads when debugging why the Notion API returned 429.

### 7.7 WebSocket Endpoint — DECIDED: /ws on Existing FastAPI

WebSocket at `/ws` on the existing FastAPI app at port 8093.
Vite proxy already configured: `/ws` → `ws://localhost:8093/ws`.
One server, one process, one port.

---

## File Inventory (Proposed)

```
services/umh/sockets/
  __init__.py
  types.py              — SignalEnvelope, CapabilityRequest, CapabilityResponse
                          (with raw_error), OutcomeEnvelope, ViewFrame,
                          SignalReceipt, SignalDescriptor, CapabilityDescriptor,
                          CapabilityHealth, Protocol definitions (SignalEmitter,
                          CapabilityHandler, OutcomeReceiver, ViewSubscriber),
                          IntegrationManifest
  signal_socket.py      — SignalSocket
  capability_socket.py  — CapabilitySocket
  outcome_socket.py     — OutcomeSocket
  view_socket.py        — ViewSocket
  registry.py           — IntegrationRegistry + generic IntegrationAdapter
  ws_bridge.py          — WebSocketBridge (ViewSubscriber → WebSocket)

services/umh/integrations/<name>/   (one per integration, UMH-owned config)
  __init__.py           — exports manifest
  manifest.py           — socket declarations, descriptors, risk classes
  transforms.py         — payload translations for this integration
  routing.py            — integration-specific signal routing rules
```

Estimated total: ~600-800 lines for sockets/, ~100-150 lines per integration config dir.

---

## Implementation Order (Suggested, Not Authorized)

1. `types.py` — all dataclasses and protocols (pure definitions, no dependencies)
2. `view_socket.py` + `ws_bridge.py` — gets the cockpit live immediately
3. `signal_socket.py` — inbound path
4. `capability_socket.py` + `registry.py` — execution path + registration
5. `outcome_socket.py` — closes the loop
6. Wire into `control_plane/app.py` and `pipeline.py`
7. Tests
