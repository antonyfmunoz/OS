# UMH Node Mesh — Design Spec

**Date:** 2026-05-21
**Status:** Draft
**Author:** AFM + Developer Agent

---

## 1. Problem Statement

UMH runs on a single VPS (100.77.233.50). The founder's workspace spans
a Windows desktop, iPad, and iPhone — all on Tailscale but invisible to
the substrate. UMH cannot observe what's happening on those devices, and
cannot execute actions on them.

PHILOSOPHY.md §XII (Reality Mimicking Principle) defines the integration
hierarchy: (1) Direct API, (2) Browser agent, (3) Desktop computer
control, (4) Mobile control — and states: "computer and mobile control
are not optional features — they are the completion of the harness
principle."

The node mesh fulfills items 3 and 4.

---

## 2. Goals

1. **Awareness** — UMH observes system metrics, active window, and file
   changes on every connected device.
2. **Execution** — UMH can execute shell commands, manage files, automate
   the desktop, and access the clipboard on remote devices, governed by
   the same risk classes as local execution.
3. **First-class integration** — remote devices register through
   `IntegrationRegistry` using the same protocol contracts as Notion and
   EOS. The executor cannot distinguish local from remote adapters.
4. **Resilience** — devices disconnect and reconnect gracefully. No
   orphaned state, no stale adapters, no lost context.

---

## 3. Non-Goals (Phase 1)

- iOS execution capabilities (iOS sandbox prevents it)
- `PHYSICAL_WORLD` approval UI (requires a separate approval flow spec)
- Device entity in the formal data model (Phase 3)
- Non-Tailscale connectivity / TURN relay
- Store-and-forward outcome queue for disconnected nodes
- Device-level autonomy caps (inherits dispatching agent's level)
- Async executor rewrite (Phase 4)

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  VPS (100.77.233.50)                                        │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐   │
│  │ UMH FastAPI  │    │ Node Mesh Server (:8094)         │   │
│  │ (:8093)      │    │                                  │   │
│  │              │    │  ┌────────────────┐              │   │
│  │ Cockpit API ─┼────┼─►│ /mesh/nodes    │              │   │
│  │              │    │  └────────────────┘              │   │
│  │ Pipeline ◄───┼────┼── NodeSignalEmitter              │   │
│  │              │    │                                  │   │
│  │ Executor ────┼────┼──► NodeCapabilityHandler         │   │
│  │              │    │     (blocks thread, WS round-trip)│   │
│  │ OutcomeSocket┼────┼──► NodeOutcomeReceiver           │   │
│  │              │    │                                  │   │
│  │ IntRegistry ◄┼────┼── register/unregister on connect │   │
│  │              │    │                                  │   │
│  └──────────────┘    │  WebSocket /ws per node          │   │
│                      └───────────┬──────────────────────┘   │
│                                  │ Tailscale WireGuard      │
└──────────────────────────────────┼──────────────────────────┘
                                   │
          ┌────────────────────────┼─────────────────────┐
          │                        │                     │
  ┌───────▼────────┐   ┌──────────▼──────┐   ┌─────────▼──────┐
  │ Windows Desktop │   │ iPad            │   │ iPhone         │
  │                 │   │                 │   │                │
  │ umh-node-service│   │ (Phase 3)       │   │ (Phase 3)      │
  │  Session 0      │   │ Signals only    │   │ Signals only   │
  │  ├ WS client    │   │                 │   │                │
  │  ├ shell adapter│   └─────────────────┘   └────────────────┘
  │  ├ fs adapter   │
  │  └ metrics      │
  │                 │
  │ umh-desktop     │
  │  User session   │
  │  ├ desktop ctrl │
  │  ├ clipboard    │
  │  ├ active window│
  │  └ named pipe ──┼── to umh-node-service
  │                 │
  └─────────────────┘
```

---

## 5. Node Protocol & Connection Layer

### 5.1 Transport

- Dedicated WebSocket server on port **8094** (separate from cockpit WS)
- JSON-RPC 2.0 message format over WebSocket frames
- Tailscale WireGuard provides encryption; plain `ws://` over Tailscale IPs
- Future: WSS for non-Tailscale links

### 5.2 Authentication

- Pre-shared token (PSK) per node, generated during registration
- Stored in node's `.env` (`UMH_NODE_TOKEN=...`) and VPS node registry
- Sent as query parameter on WebSocket handshake: `ws://vps:8094/ws?token=<psk>`
- Server validates token before completing handshake
- Future: mTLS when mesh exceeds 5 nodes

### 5.3 Handshake

Node sends `node.hello` after WebSocket connects:

```json
{
  "jsonrpc": "2.0",
  "method": "node.hello",
  "params": {
    "node_id": "windows-desktop",
    "hostname": "DESKTOP-AFM",
    "os": "windows",
    "os_version": "11",
    "capabilities": [
      {
        "name": "shell",
        "category": "system",
        "risk_class": "REVERSIBLE_WRITE",
        "max_risk_class": "IRREVERSIBLE_WRITE"
      },
      {
        "name": "filesystem",
        "category": "system",
        "risk_class": "REVERSIBLE_WRITE",
        "max_risk_class": "IRREVERSIBLE_WRITE"
      },
      {
        "name": "desktop",
        "category": "system",
        "risk_class": "REVERSIBLE_WRITE",
        "max_risk_class": "IRREVERSIBLE_WRITE"
      },
      {
        "name": "clipboard",
        "category": "system",
        "risk_class": "READ_ONLY",
        "max_risk_class": "SAFE_WRITE"
      }
    ],
    "daemon_version": "0.1.0",
    "tailscale_ip": "100.74.199.102"
  },
  "id": 1
}
```

Server responds:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "accepted": true,
    "server_version": "0.1.0",
    "heartbeat_interval_s": 30
  },
  "id": 1
}
```

### 5.4 Heartbeat

- Node sends `node.heartbeat` every 30 seconds
- Payload includes current system metrics (CPU, memory, disk, battery)
- Server expects heartbeat within 90 seconds (3× interval)
- After 3 missed heartbeats: node marked `down`, adapter unregistered,
  `node.disconnected` signal emitted into pipeline

### 5.5 Reconnection

- Client uses exponential backoff: 1s → 2s → 4s → ... → 60s cap
- On reconnect, server calls full `unregister()` for stale registration
  before processing new `node.hello`
- Node re-sends `node.hello` — treated as fresh registration

### 5.6 Capability Updates

Node sends `node.capabilities_changed` when capabilities change
(e.g., tray companion starts or stops):

```json
{
  "jsonrpc": "2.0",
  "method": "node.capabilities_changed",
  "params": {
    "capabilities": [...]
  }
}
```

Server unregisters the old integration and re-registers with new
capabilities. This is the same unregister/register cycle as reconnect.

---

## 6. Signal Emission

Signals flow from node → VPS. Three categories with different cadences:

### 6.1 System Metrics (Telemetry)

- CPU %, memory %, disk %, battery %, network I/O
- Emitted every 30 seconds as part of `node.heartbeat`
- **Does NOT enter the full 10-stage pipeline** — goes to a lightweight
  metrics buffer (see §6.4)
- Only anomaly signals (CPU > 90%, disk > 95%, battery < 10%) get
  promoted to `submit_signal()` as `signal_class: "alert"`

### 6.2 Workspace Awareness (Event-Driven)

- Active window title + process name (from tray companion)
- Screen state (locked/unlocked, display count)
- Emitted on change, debounced at 2 seconds
- Enters pipeline as `content_type: "node.workspace.window_change"`
- Feeds the Awareness view's "workspace" tier

### 6.3 File Watch (Configurable)

- Watches configured directories for create/modify/delete
- Debounced at 2 seconds per path
- Enters pipeline as `content_type: "node.filesystem.change"`
- Default watched: `~/Documents`, `~/Desktop`, project directories

### 6.4 Metrics Buffer (Lightweight Path)

Telemetry signals bypass the pipeline entirely:

```
node.heartbeat → NodeMeshServer → MetricsBuffer (in-memory ring)
                                       │
                   /api/umh/mesh/nodes ◄┘  (cockpit reads from here)
                                       │
                   Anomaly detector ────┘  (promotes to pipeline)
```

- `MetricsBuffer`: per-node ring buffer, 1000 entries (~8 hours at 30s)
- Flushed to `data/umh/mesh/metrics.jsonl` every 5 minutes
- Anomaly thresholds configurable per node in `node_mesh_config.toml`
- This prevents 11,520+ daily metric entries from bloating the trace store

### 6.5 Signal Wire Format

```json
{
  "jsonrpc": "2.0",
  "method": "signal.emit",
  "params": {
    "content_type": "node.system.metrics",
    "payload": {
      "cpu": 45.2,
      "memory": 68.1,
      "disk": 52.0,
      "battery": 87,
      "active_window": "Visual Studio Code — project.ts"
    },
    "urgency": "LOW",
    "signal_class": "telemetry"
  }
}
```

The `signal_class` field determines routing:
- `"telemetry"` → MetricsBuffer only
- `"alert"` → full pipeline via `submit_signal()`
- `"event"` → full pipeline (workspace changes, file watches)

---

## 7. Execution Capabilities

Execution flows from VPS → node. Four capability adapters, each running
on the Windows side.

### 7.1 Shell Adapter

- Executes commands via `subprocess.run()` on Windows
- Risk class: `REVERSIBLE_WRITE`
- Node-side cap: `IRREVERSIBLE_WRITE` (node refuses anything higher)
- Operations: `shell.run`, `shell.powershell`, `shell.query`
- Timeout: from `CapabilityRequest.timeout_seconds` (default 30s)
- Runs in `umh-node-service` (Session 0, no GUI needed)

### 7.2 Filesystem Adapter

- Read, write, list, move, delete files
- Risk class: `READ_ONLY` for reads, `REVERSIBLE_WRITE` for writes
- Node-side cap: `IRREVERSIBLE_WRITE`
- Operations: `fs.read`, `fs.write`, `fs.list`, `fs.move`, `fs.delete`
- Path sandboxing: configurable allowed directories in node config
- Runs in `umh-node-service`

### 7.3 Desktop Adapter

- Mouse/keyboard automation, window management, screenshot
- Risk class: `REVERSIBLE_WRITE`
- Node-side cap: `IRREVERSIBLE_WRITE` (`PHYSICAL_WORLD` blocked until
  approval flow exists)
- Operations: `desktop.click`, `desktop.type`, `desktop.screenshot`,
  `desktop.focus_window`, `desktop.list_windows`
- Runs in `umh-desktop` (tray companion, user session — requires GUI)
- Proxied to `umh-node-service` via named pipe, then over WebSocket

### 7.4 Clipboard Adapter

- Read/write system clipboard
- Risk class: `READ_ONLY` for read, `SAFE_WRITE` for write
- Node-side cap: `SAFE_WRITE`
- Operations: `clipboard.read`, `clipboard.write`
- Runs in `umh-desktop` (requires user session)

### 7.5 Capability Wire Format

VPS sends:

```json
{
  "jsonrpc": "2.0",
  "method": "capability.execute",
  "params": {
    "request_id": "uuid",
    "capability_name": "shell.run",
    "params": {
      "command": "dir C:\\Users\\afm\\Documents"
    },
    "governance_verdict_id": "uuid",
    "trace_id": "uuid",
    "timeout_seconds": 30
  },
  "id": 42
}
```

Node responds:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "result_data": {
      "stdout": "...",
      "exit_code": 0
    },
    "latency_ms": 124.5,
    "side_effects": []
  },
  "id": 42
}
```

### 7.6 Synchronous Execution Over Async Transport

The executor's `AdapterProtocol.execute()` is synchronous. The
`NodeCapabilityHandler.handle_capability()` must block the calling
thread until the WebSocket round-trip completes:

```python
class NodeCapabilityHandler:
    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        event = threading.Event()
        response_holder: list[CapabilityResponse] = []

        self._ws.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "capability.execute",
            "params": {...},
            "id": request.request_id.hex,
        }))

        self._pending[request.request_id.hex] = (event, response_holder)
        completed = event.wait(timeout=request.timeout_seconds)

        if not completed:
            raise TimeoutError(f"node {self._node_id} did not respond "
                               f"within {request.timeout_seconds}s")

        return response_holder[0]
```

The executor catches `TimeoutError` (executor.py:142) and returns
`ExecutionOutcome.TIMEOUT`. This preserves the synchronous contract
without an executor rewrite.

### 7.7 Governance — Dual Validation

Every remote execution passes governance twice:

1. **VPS-side (pre-send):** The pipeline's governance stage evaluates
   risk class using the same `PolicyEngine` as local execution. The
   `NodeCapabilityHandler` declares its capabilities with accurate
   risk classes via `describe_capabilities()`.

2. **Node-side (pre-execute):** The daemon validates the request against
   its local capability allowlist before executing. The node can be
   **stricter** than the VPS but never looser.

Node-side config (`umh_node.toml`):

`max_risk_class` values use `RiskClass` enum names from
`services/umh/governance/risk_classes.py`. The node refuses any
capability request whose risk class exceeds this cap.

```toml
[capabilities.shell]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"
allowed_commands = []  # empty = all allowed

[capabilities.filesystem]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"
allowed_paths = ["C:\\Users\\afm"]

[capabilities.desktop]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"

[capabilities.clipboard]
enabled = true
max_risk_class = "SAFE_WRITE"
```

Risk class mapping for remote operations:

| Operation | Local (VPS) Risk | Remote Risk | Rationale |
|---|---|---|---|
| shell.run | SAFE_WRITE | REVERSIBLE_WRITE | Remote side-effects harder to undo |
| shell.powershell | SAFE_WRITE | REVERSIBLE_WRITE | Same |
| fs.read | READ_ONLY | READ_ONLY | No side-effects |
| fs.write | SAFE_WRITE | REVERSIBLE_WRITE | Remote writes need higher scrutiny |
| fs.delete | REVERSIBLE_WRITE | IRREVERSIBLE_WRITE | No trash on all systems |
| desktop.* | N/A | REVERSIBLE_WRITE | GUI actions, reversible by nature |
| clipboard.read | READ_ONLY | READ_ONLY | No side-effects |
| clipboard.write | SAFE_WRITE | SAFE_WRITE | Easily reversed |

Node-side `max_risk_class` caps all operations at `IRREVERSIBLE_WRITE`
maximum. `PHYSICAL_WORLD` risk class exists in the enum but the
approval flow has no human-in-the-loop UI yet — so any operation that
would classify as `PHYSICAL_WORLD` is blocked until that's built
(separate spec).

---

## 8. Windows Daemon Architecture

Two processes, communicating via named pipe:

### 8.1 `umh-node-service` (Windows Service)

- Runs in Session 0 (no GUI, survives logoff)
- Owns the WebSocket connection to VPS
- Implements: shell adapter, filesystem adapter, metrics collection
- Manages heartbeat cycle
- Starts on boot via Windows Service Manager
- Config: `C:\ProgramData\UMH\umh_node.toml`
- Logs: `C:\ProgramData\UMH\logs\`
- Credential: `C:\ProgramData\UMH\.env` (`UMH_NODE_TOKEN`, `UMH_VPS_HOST`)

### 8.2 `umh-desktop` (Tray Companion)

- Runs in user session (has GUI access)
- System tray icon with status indicator
- Implements: desktop adapter, clipboard adapter, workspace awareness
  (active window tracking)
- Connects to `umh-node-service` via named pipe: `\\.\pipe\umh-node`
- Starts on user login via Windows startup folder / registry Run key
- If tray companion is not running, desktop/clipboard capabilities are
  unavailable — service sends `node.capabilities_changed` to remove them

### 8.3 Named Pipe Protocol

Same JSON-RPC 2.0 as the WebSocket protocol. Messages:

- `desktop.execute` — service → tray (proxied capability request)
- `desktop.result` — tray → service (proxied capability response)
- `workspace.update` — tray → service (active window changed)
- `tray.status` — tray → service (connected/disconnected)

### 8.4 Technology

- Python 3.12 (matches VPS stack)
- `pywin32` for Windows Service support
- `pystray` for system tray
- `pyautogui` + `pygetwindow` for desktop automation
- `watchdog` for file system monitoring
- `websockets` library for WebSocket client
- Packaged via PyInstaller into standalone exe (no Python install required)

### 8.5 Installer

- MSI package built with WiX or cx_Freeze
- Installs both `umh-node-service` and `umh-desktop`
- First-run wizard: enter VPS address + token → writes `.env`
- Registers Windows Service + startup entry

---

## 9. VPS-Side Integration — Node Mesh Server

### 9.1 Module Structure

```
services/umh/
├── node_mesh/
│   ├── __init__.py
│   ├── server.py          # WebSocket server, node lifecycle
│   ├── registry.py        # NodeRegistry — tracks connected nodes
│   ├── metrics_buffer.py  # Per-node ring buffer for telemetry
│   └── config.py          # Load node_mesh_config.toml
│
├── integrations/
│   └── node_mesh/
│       ├── __init__.py
│       ├── signals.py     # NodeSignalEmitter
│       ├── handlers.py    # NodeCapabilityHandler
│       ├── outcomes.py    # NodeOutcomeReceiver
│       └── manifest.py    # Builds IntegrationManifest per node
```

### 9.2 Node Lifecycle

```
WebSocket connect
  → Authenticate (validate PSK)
  → Receive node.hello
  → If node_id already registered:
      → Call unregister_full(node_id)  [cleans sockets + executor]
  → Create NodeSignalEmitter, NodeCapabilityHandler, NodeOutcomeReceiver
  → Build IntegrationManifest(integration_id=f"node-{node_id}")
  → IntegrationRegistry.register(manifest) → adapter
  → WorkPacketExecutor.register_adapter(adapter)
  → NodeRegistry.add(node_id, ws_connection, capabilities, manifest)
  → Emit signal: "node.connected" into pipeline

WebSocket disconnect
  → unregister_full(node_id):
      → IntegrationRegistry.unregister(integration_id)
        → Extended to also call:
            signal_socket.unregister_emitter(integration_id)
            capability_socket.unregister_handler(integration_id)
            outcome_socket.unregister_receiver(integration_id)
            view_socket.unsubscribe(integration_id)  [if subscribed]
      → WorkPacketExecutor.unregister_adapter(adapter_name)
      → NodeRegistry.remove(node_id)
  → Emit signal: "node.disconnected" into pipeline
```

### 9.3 Required Codebase Changes

These changes are prerequisites for the node mesh to function:

**1. `IntegrationRegistry.unregister()` must clean up sockets.**

Current (registry.py:153-155):
```python
def unregister(self, integration_id: str) -> None:
    self._registered.pop(integration_id, None)
    self._adapters.pop(integration_id, None)
```

Required:
```python
def unregister(self, integration_id: str) -> None:
    manifest = self._registered.pop(integration_id, None)
    self._adapters.pop(integration_id, None)
    if manifest is None:
        return
    if manifest.signal_emitter is not None:
        self._signal.unregister_emitter(integration_id)
    if manifest.capability_handler is not None:
        self._capability.unregister_handler(integration_id)
    if manifest.outcome_receiver is not None:
        self._outcome.unregister_receiver(integration_id)
    if manifest.view_subscriber is not None:
        self._view.unsubscribe(integration_id)
```

Each socket needs an `unregister_*()` method added (idempotent, no-op
if not found). Currently missing from all four sockets.

**2. `WorkPacketExecutor` needs `unregister_adapter()`.**

```python
def unregister_adapter(self, name: str) -> None:
    self._adapters.pop(name, None)
```

**3. `IntegrationRegistry.register()` must allow re-registration.**

Current behavior: `raise ValueError` if integration_id exists.
Required: call `self.unregister(iid)` first if already registered,
then proceed with registration. This handles reconnects atomically.

### 9.4 NodeSignalEmitter

Implements `SignalEmitter` protocol (protocols.py:58-71):

```python
class NodeSignalEmitter:
    @property
    def integration_id(self) -> str:
        return f"node-{self._node_id}"

    def describe_signals(self) -> list[SignalDescriptor]:
        return [
            SignalDescriptor("node.system.metrics", "System telemetry",
                             default_urgency=SignalUrgency.LOW,
                             default_risk_class=RiskClass.READ_ONLY),
            SignalDescriptor("node.workspace.window_change", "Active window changed",
                             default_urgency=SignalUrgency.LOW,
                             default_risk_class=RiskClass.READ_ONLY),
            SignalDescriptor("node.filesystem.change", "File created/modified/deleted",
                             default_urgency=SignalUrgency.NORMAL,
                             default_risk_class=RiskClass.READ_ONLY),
            SignalDescriptor("node.connected", "Node came online",
                             default_urgency=SignalUrgency.NORMAL,
                             default_risk_class=RiskClass.READ_ONLY),
            SignalDescriptor("node.disconnected", "Node went offline",
                             default_urgency=SignalUrgency.HIGH,
                             default_risk_class=RiskClass.READ_ONLY),
        ]
```

When a `signal.emit` message arrives over WebSocket, the server creates
a `SignalEnvelope` and calls `SignalSocket.emit()` — routing it into
the pipeline. Telemetry signals (`signal_class: "telemetry"`) are
intercepted before `emit()` and sent to the MetricsBuffer instead.

### 9.5 NodeCapabilityHandler

Implements `CapabilityHandler` protocol (protocols.py:74-89):

```python
class NodeCapabilityHandler:
    @property
    def integration_id(self) -> str:
        return f"node-{self._node_id}"

    def describe_capabilities(self) -> list[CapabilityDescriptor]:
        # Built from node.hello capability declarations
        return self._descriptors

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        # Blocks thread, sends over WebSocket, waits for response
        # See §7.6 for implementation pattern

    def health(self) -> CapabilityHealth:
        age = time.time() - self._last_heartbeat
        if age > 90:
            return CapabilityHealth(self.integration_id, "unavailable",
                                   "no heartbeat for {age:.0f}s")
        if age > 60:
            return CapabilityHealth(self.integration_id, "degraded",
                                   "heartbeat delayed")
        return CapabilityHealth(self.integration_id, "healthy")
```

### 9.6 NodeOutcomeReceiver

Implements `OutcomeReceiver` protocol (protocols.py:92-108):

```python
class NodeOutcomeReceiver:
    @property
    def integration_id(self) -> str:
        return f"node-{self._node_id}"

    def on_outcome(self, envelope: OutcomeEnvelope) -> None:
        # Fire-and-forget: send to node if connected, log if not
        if self._ws and self._ws.open:
            self._ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "outcome.notify",
                "params": {
                    "outcome_id": str(envelope.outcome_id),
                    "outcome_type": envelope.outcome_type,
                    "summary": envelope.summary,
                }
            }))
        else:
            logger.warning("outcome for disconnected node %s: %s",
                           self._node_id, envelope.outcome_id)

    def accepts_outcomes(self) -> list[str]:
        return ["*"]  # Accepts all outcome types
```

### 9.7 Cockpit API Extension

New endpoint in `cockpit_api.py`:

```python
@router.get("/mesh/nodes")
async def mesh_nodes():
    """Returns connected mesh nodes with status and metrics."""
    return [
        {
            "id": node.node_id,
            "name": node.hostname,
            "os": node.os,
            "status": node.status,  # "connected", "degraded", "disconnected"
            "capabilities": [c.name for c in node.capabilities],
            "metrics": node.latest_metrics,
            "last_heartbeat": node.last_heartbeat_iso,
            "tailscale_ip": node.tailscale_ip,
            "connected_at": node.connected_at_iso,
        }
        for node in node_registry.all_nodes()
    ]
```

The Infrastructure view adds mesh nodes alongside Tailscale peers and
Docker containers. The Awareness view reads workspace signals for the
"embodied" and "workspace" tiers.

---

## 10. Security

### 10.1 Threat Model

| Threat | Mitigation |
|---|---|
| Stolen PSK token | Token rotation via `/api/umh/mesh/rotate-token`. Tailscale already provides network-level auth. |
| Compromised VPS sends malicious commands | Node-side governance validates all requests against local allowlist. Node can refuse any request. |
| Man-in-the-middle | Tailscale WireGuard encrypts all traffic. Non-Tailscale links require WSS. |
| Replay attack | Each `CapabilityRequest` has unique `request_id` (UUID). Node rejects duplicate IDs within a window. |
| Node impersonation | PSK is per-node. A token can only register as its assigned `node_id`. |
| Credential leak from tray companion | Tray companion never holds the WebSocket token — only the service does. Named pipe is local-only. |

### 10.2 Audit Trail

Every remote execution is traced in `data/umh/traces/traces.jsonl`:

```json
{
  "trace_id": "uuid",
  "adapter_used": "node-windows-desktop",
  "operation": "shell.run",
  "params": {"command": "dir"},
  "risk_class": "REVERSIBLE_WRITE",
  "governance_decision": "APPROVE",
  "result": "SUCCESS",
  "node_id": "windows-desktop",
  "duration_ms": 124.5
}
```

Queryable through `/api/umh/tasks` — cockpit Tasks view shows remote
executions with the node identifier.

---

## 11. Cockpit Integration

### 11.1 Infrastructure View

- New "MESH NODES" section in the summary strip and grid
- Each mesh node card shows: name, OS, status, capabilities count,
  CPU/memory/disk from latest heartbeat, latency to VPS
- Connected nodes appear green; degraded yellow; disconnected red

### 11.2 Awareness View — Embodied Tier

- System metrics from all connected nodes
- Battery level for laptops and mobile devices
- Network connectivity status
- Pulls from MetricsBuffer via `/api/umh/mesh/nodes`

### 11.3 Awareness View — Workspace Tier

- Active window title + process name from each connected desktop node
- Screen lock state
- Recent file changes from watched directories
- Pulls from pipeline observations (workspace signals enter the pipeline
  as normal signals and become observations in the memory store)

### 11.4 Tasks View

- Remote executions appear as normal tasks with `agent: "node-windows-desktop"`
- No special handling — the trace store already captures all fields

---

## 12. Configuration

### 12.1 VPS-Side (`data/umh/mesh/node_mesh_config.toml`)

```toml
[server]
port = 8094
heartbeat_timeout_s = 90
max_nodes = 10

[metrics]
buffer_size = 1000
flush_interval_s = 300
anomaly_cpu_threshold = 90
anomaly_disk_threshold = 95
anomaly_battery_threshold = 10

[nodes.windows-desktop]
token = "psk-..."
display_name = "Windows Desktop"
```

### 12.2 Windows-Side (`C:\ProgramData\UMH\umh_node.toml`)

```toml
[connection]
vps_host = "100.77.233.50"
vps_port = 8094
reconnect_max_backoff_s = 60

[identity]
node_id = "windows-desktop"
hostname = "DESKTOP-AFM"

[capabilities.shell]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"

[capabilities.filesystem]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"
allowed_paths = ["C:\\Users\\afm"]

[capabilities.desktop]
enabled = true
max_risk_class = "IRREVERSIBLE_WRITE"

[capabilities.clipboard]
enabled = true
max_risk_class = "SAFE_WRITE"

[signals.metrics]
interval_s = 30

[signals.workspace]
enabled = true
debounce_s = 2

[signals.filewatch]
enabled = true
paths = ["C:\\Users\\afm\\Documents", "C:\\Users\\afm\\Desktop"]
debounce_s = 2
```

---

## 13. Implementation Phases

### Phase 1 — VPS Foundation

**Deliverables:**
1. `services/umh/node_mesh/server.py` — WebSocket server + auth
2. `services/umh/node_mesh/registry.py` — NodeRegistry
3. `services/umh/node_mesh/metrics_buffer.py` — Ring buffer + flush
4. `services/umh/integrations/node_mesh/` — proxy integration
   (signals.py, handlers.py, outcomes.py, manifest.py)
5. Extend `IntegrationRegistry.unregister()` to clean up sockets
6. Add `unregister_adapter()` to `WorkPacketExecutor`
7. Add `unregister_*()` methods to all four sockets
8. Make `IntegrationRegistry.register()` handle re-registration
9. `/api/umh/mesh/nodes` endpoint
10. Test with a Python WebSocket client simulating a node

**Verification:**
- Simulated node connects, registers, emits signals, receives capability
  requests, disconnects, reconnects — all without errors
- MetricsBuffer stores telemetry without touching trace store
- Cockpit Infrastructure view shows mesh nodes

### Phase 2 — Windows Daemon

**Deliverables:**
1. `umh-node-service` — Windows Service with WS client, shell adapter,
   filesystem adapter, metrics collection, heartbeat
2. `umh-desktop` — tray companion with desktop adapter, clipboard
   adapter, workspace awareness, named pipe client
3. Named pipe protocol between service and tray
4. PyInstaller packaging for both executables
5. MSI installer with first-run wizard
6. End-to-end test: VPS → shell command → Windows → result → VPS

**Verification:**
- Service starts on boot, connects to VPS within 10 seconds
- Tray companion shows connected status, active window updates appear
  in Awareness view
- Shell command from VPS executes on Windows and returns output
- Disconnect/reconnect cycle completes cleanly (no stale state)

### Phase 3 — Mobile & Maturation

**Deliverables:**
1. iOS node (Shortcut-based or native app) — signals only
2. Device entity in data model
3. Outcome queue for disconnected nodes
4. Device-level autonomy caps
5. Token rotation and revocation

**Verification:**
- iPhone location and battery appear in Awareness embodied tier
- Disconnected device receives queued outcomes on reconnect

### Phase 4 — Async Executor (Future)

- Rewrite `WorkPacketExecutor` to support async adapters natively
- Remove the `threading.Event` blocking pattern from
  `NodeCapabilityHandler`
- Enable concurrent remote executions without thread-per-request

---

## 14. Known Limitations & Future Work

1. **`PHYSICAL_WORLD` has no approval UI.** Desktop automation is capped
   at `EXECUTE` risk class. Full `PHYSICAL_WORLD` support requires
   building the approval flow (separate spec).

2. **No Device entity in the entity model.** Phase 1 uses in-memory
   NodeRegistry + persisted JSONL. Formal Device entity with audit
   trails and trust scores is Phase 3.

3. **Outcomes to disconnected nodes are logged, not queued.** Phase 1
   logs and warns. Phase 3 adds a store-and-forward queue. Nodes can
   query `/api/umh/mesh/outcomes?since=<timestamp>` on reconnect.

4. **Tailscale-only connectivity.** HTTPS long-poll fallback for
   non-Tailscale links is out of scope for Phase 1.

5. **Device autonomy inherits agent level.** A device has no independent
   autonomy cap — it inherits from the dispatching agent. Phase 3 adds
   per-device caps.

6. **Synchronous executor.** Remote calls block one thread each. At
   current scale (1-2 devices) this is fine. Phase 4 rewrites the
   executor for async.

7. **No signal authentication per-message.** Signals from registered
   nodes are trusted because the WebSocket is authenticated. Per-message
   signing is future hardening work.

---

## 15. Glossary

| Term | Definition |
|---|---|
| **Node** | Any device running a UMH daemon that connects to the mesh |
| **Node Mesh** | The WebSocket-based network connecting all nodes to the VPS |
| **Node Mesh Server** | VPS-side WebSocket server managing node connections |
| **PSK** | Pre-shared key — authentication token for a node |
| **MetricsBuffer** | In-memory ring buffer for telemetry (bypasses pipeline) |
| **Tray Companion** | User-session process providing desktop/clipboard access |
| **Integration Manifest** | Declaration of what an integration provides/consumes |
| **Capability Descriptor** | Declaration of a single capability's name, risk, schema |

---

## 16. References

- `PHILOSOPHY.md` §XII — Reality Mimicking Principle
- `PHILOSOPHY.md` §XI — Complete Automation
- `ARCHITECTURE.md` §4 — Agent Hierarchy & Autonomy Levels
- `services/umh/sockets/protocols.py` — Protocol definitions
- `services/umh/sockets/registry.py` — IntegrationRegistry
- `services/umh/execution/executor.py` — WorkPacketExecutor
- `services/umh/governance/risk_classes.py` — RiskClass enum
- `services/umh/sockets/envelopes.py` — Envelope dataclasses
- `services/umh/integrations/notion/` — Reference integration pattern
- `services/umh/integrations/eos/` — Reference integration pattern
