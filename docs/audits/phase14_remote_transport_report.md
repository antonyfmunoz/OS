# Phase 14 — Real Remote Node Transport + SSH Execution v1

**Date:** 2026-04-30
**Status:** COMPLETE
**Tests:** 50 passed (Phase 14) + 314 passed (11B-13 regression)

---

## What Changed After Phase 13

Phase 13 introduced the distributed awareness layer: heartbeats, health
state machine, remote execution protocol, and failover routing — all
operating on local state with no real network transport.

Phase 14 adds the real transport boundary:

- Transport protocol abstraction (NodeTransport)
- SSH transport implementation (system ssh binary, list args, no shell=True)
- Transport-backed remote client implementing RemoteNodeClient
- Remote heartbeat collection over SSH
- Boundary enforcement: subprocess confined to approved files only

## Why SSH First

SSH is the universal lowest-common-denominator for remote execution:
- Available on every Linux/Mac system without additional dependencies
- Handles authentication, key management, and known_hosts natively
- The system binary already supports agent forwarding and config files
- List-arg invocation via subprocess.run prevents shell injection by design
- No new Python dependencies required (no paramiko, no fabric)

Future transports (WebSocket, HTTP/gRPC) implement the same NodeTransport
protocol and plug in without changing any routing or health logic.

## Transport Abstraction

`umh/nodes/transport.py`

Three core types:

**TransportStatus** enum: OK | FAILED | TIMEOUT | UNREACHABLE | AUTH_FAILED

**RemoteCommand** (frozen dataclass):
- `command: tuple[str, ...]` — must be non-empty sequence, never a shell string
- `cwd`, `env`, `timeout_seconds`, `metadata`
- Validates non-empty command at construction time

**RemoteCommandResult** (dataclass):
- `status`, `stdout`, `stderr`, `exit_code`
- `started_at`, `finished_at`, `duration_ms`
- `error` for human-readable failure reason

**NodeTransport** protocol:
- `ping(node) -> TransportStatus`
- `run_command(node, command) -> RemoteCommandResult`
- `close(node) -> None`

No imports from cells, adapters, environments, or subprocess.
Pure data models and protocol definition.

## SSH Execution Design

`umh/nodes/ssh_transport.py`

SSHNodeTransport implements NodeTransport using the system ssh binary.

SSH command construction:
```
ssh -o BatchMode=yes
    -o StrictHostKeyChecking=accept-new
    -o ConnectTimeout=<seconds>
    -p <port>
    [-i <identity_file>]
    user@host
    -- <command args...>
```

Node metadata contract:
```json
{
  "host": "10.0.0.1",
  "user": "deploy",
  "port": 22,
  "identity_file": "/path/to/key"
}
```

Safety guarantees:
- All commands passed as list args to subprocess.run — no shell=True
- No manual string quoting or concatenation
- Missing host/user returns AUTH_FAILED immediately (no subprocess call)
- TimeoutExpired → TIMEOUT status
- SSH exit code 255 with "permission denied" → AUTH_FAILED
- SSH exit code 255 otherwise → UNREACHABLE
- Nonzero exit → FAILED with exit_code and stderr
- FileNotFoundError → FAILED with "ssh binary not found"
- All exceptions caught and converted to RemoteCommandResult

subprocess is imported only in this file and containers.py.

## Remote Client Integration

`umh/nodes/remote.py` — extended

**TransportBackedRemoteNodeClient**:
- `__init__(transport)` — validates NodeTransport protocol at construction
- `ping(node)` → delegates to transport.ping, returns bool
- `submit_execution(node, task)` → executes command synchronously over transport
- `fetch_result(node, task_id)` → returns stored result from synchronous execution
- `cancel(node, task_id)` → marks stored record as CANCELLED

Phase 14 is explicitly synchronous: submit_execution runs the command
and returns the result immediately. No async job queue, no background
workers. This is documented as a known limitation.

Task metadata contract for remote execution:
```python
{
    "task_id": "...",
    "command": ["echo", "hello"],
    "cwd": "/opt/work",          # optional
    "timeout_seconds": 30,       # optional, default 30
}
```

## Remote Heartbeat Flow

`umh/nodes/remote.collect_remote_heartbeat(node, transport)`

Runs a lightweight Python probe on the remote node:
```python
python3 -c "import json, os, platform, time; ..."
```

Collects: hostname, platform, load_1m, timestamp.

Response mapping:
- Transport OK + valid JSON → NodeHeartbeat(OK) or DEGRADED if load > 4.0
- Transport TIMEOUT → NodeHeartbeat(DEGRADED) with error metadata
- Transport UNREACHABLE/FAILED → NodeHeartbeat(UNKNOWN) with error metadata
- Invalid JSON output → NodeHeartbeat(DEGRADED) with parse error
- Transport exception → NodeHeartbeat(UNKNOWN) with exception detail

## Sync vs Async Limitation

Phase 14 remote execution is **synchronous only**:

```
Caller → TransportBackedRemoteNodeClient.submit_execution()
       → SSHNodeTransport.run_command()
       → subprocess.run() [blocks until complete or timeout]
       → RemoteExecutionRecord returned immediately
```

This means:
- The caller blocks during remote execution
- No long-running remote jobs
- No remote job queue or polling
- No parallel remote task submission

Phase 15 can build:
- Async transport wrapper (asyncio or threading)
- Remote job queue with task IDs
- Non-blocking submit + poll pattern
- Parallel multi-node execution

## Invariants Preserved

1. Cells NEVER execute — verified by boundary tests
2. Cells NEVER import environments — verified
3. Cells NEVER import nodes — verified
4. Cells NEVER import transports — verified
5. All execution flows through control plane — advisor only spawns cells
6. Environment layer is the only layer touching subprocess for local execution — verified
7. Remote transport subprocess confined to ssh_transport.py — verified by AST-based test
8. No shell=True anywhere — verified by AST analysis (not string matching)
9. Sandbox always gates before execution — unchanged
10. Remote node failure degrades safely — all exceptions caught in transport
11. Scheduler/router remain pure — unchanged
12. No global mutable state — all state in class instances

## Files Created

- `umh/nodes/transport.py` — transport abstraction (protocol + models)
- `umh/nodes/ssh_transport.py` — SSH transport implementation
- `tests/unit/test_phase14_remote_transport.py` — 50 tests
- `docs/audits/phase14_remote_transport_report.md` — this file

## Files Modified

- `umh/nodes/remote.py` — added TransportBackedRemoteNodeClient + collect_remote_heartbeat
- `umh/nodes/__init__.py` — added Phase 14 exports

## Test Summary

| Suite | Tests | Result |
|-------|-------|--------|
| Phase 14 transport | 50 | all passed |
| Phase 13 distributed | 55 | all passed |
| Phase 12 runtime | 44 | all passed |
| Phase 11F execution | 40 | all passed |
| Phase 11E environment | 37 | all passed |
| Phase 11D orchestration | 45 | all passed |
| Phase 11C cells + brain | 54 | all passed |
| Phase 11B brains | 39 | all passed |
| **Total** | **364** | **all passed** |

## Known Limitations

- Synchronous SSH execution only (no async, no job queue)
- No long-running remote job support
- No remote Docker orchestration
- No encrypted node registry or node identity verification
- No remote artifact streaming
- No mesh/P2P networking
- No durable remote job queue
- No parallel multi-node execution
- No WebSocket/HTTP transport yet
- SSH binary must be installed on the host system
- Remote heartbeat requires Python 3 on the remote node

## Is Phase 15 Safe?

Yes. Phase 14 adds two clean modules and extends one:
- `transport.py` — pure models + protocol, no I/O
- `ssh_transport.py` — confined subprocess usage, no cell/adapter deps
- `remote.py` — transport-backed client + heartbeat helper

Phase 15 can safely build:
- Async transport wrapper for non-blocking execution
- Remote job queue with task persistence
- WebSocket transport implementing NodeTransport
- Multi-node parallel execution coordinator
- Remote Docker orchestration via SSH
- Remote artifact streaming
- Encrypted node identity/authentication
