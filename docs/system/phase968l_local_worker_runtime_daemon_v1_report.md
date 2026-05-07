# Phase 96.8L -- Local Worker Runtime Daemon v1

**Date:** 2026-05-07
**Status:** COMPLETE
**Gate:** LOCAL_WORKER_RUNTIME_DAEMON_V1
**Next Gate:** DISCORD_INTERFACE_ADAPTER_V1

---

## Why Persistent Worker Runtimes Matter

Prior phases proved that the relay works (96.8H-96.8J) and that
formal contracts exist for workers, adapters, and capabilities (96.8K).
But each relay invocation was ad-hoc -- a one-shot Python command
from a terminal. There was no persistent process watching for work,
no heartbeat proving liveness, no structured proof trail.

A persistent worker runtime daemon converts proof-of-concept into
operational infrastructure. It:

1. Runs continuously and is observable (heartbeat, status file).
2. Polls for work packets rather than requiring manual invocation.
3. Routes work to the correct adapter based on the registry.
4. Persists a RuntimeProof for every action, successful or failed.
5. Handles errors without crashing (malformed packets, adapter failures).
6. Shuts down gracefully on SIGINT/SIGTERM.

This is the minimum viable daemon. It does not orchestrate, plan,
or make decisions. It routes and records.

---

## Control Plane vs Worker Runtime

| Concept | Role | Location |
|---------|------|----------|
| Control Plane | Decides what work to do, constructs packets, governs | VPS Claude Code |
| Worker Runtime | Executes work packets, routes to adapters, emits proof | Local WSL daemon |
| Adapter | Performs environment-native actions | Windows PS relay |

The control plane creates work. The worker runtime executes work.
The adapter performs the environment-specific action. Each layer
has clear authority boundaries.

---

## Adapters vs Workers

| Term | What It Is | Example |
|------|-----------|---------|
| Worker | A persistent runtime that polls for and processes work | local_wsl_worker daemon |
| Adapter | A component that performs a specific action in a specific environment | windows_interactive_desktop_relay |

A worker may use multiple adapters. An adapter may serve multiple
workers. The adapter registry maps capabilities to adapters. The
worker consults the registry to route each packet.

---

## Why filesystem_json Remains Valid for Prototype

The filesystem JSON inbox/outbox pattern is:
- Zero dependencies (no Redis, no NATS, no message broker)
- Cross-environment (WSL and Windows share /mnt/c)
- Observable (files are inspectable, debuggable)
- Sufficient for single-worker, single-adapter prototype

It has known limitations:
- No guaranteed ordering beyond filename sort
- No atomic delivery
- Polling-based, not event-driven
- Single-consumer only

These limitations are acceptable for v1. The daemon processes
packets sequentially and moves them after completion.

---

## Future Migration Paths

When the prototype outgrows filesystem_json:

| Bus | When | Why |
|-----|------|-----|
| Redis pub/sub | Multi-worker, low latency needed | Event-driven, ordered queues |
| NATS | Multi-worker, multi-adapter | Lightweight, built for this |
| Kafka | Audit trail, replay needed | Durable, ordered log |
| gRPC | Direct adapter calls, schema enforcement | Typed, low-latency |

The MessageBusType enum already supports these values. Adapter
and worker contracts are bus-agnostic.

---

## Future Layers (Not Built)

| Layer | Purpose | When |
|-------|---------|------|
| Discord interface adapter | Submit work packets from Discord | After daemon is stable |
| Scheduler | Time-based packet generation | After interface adapters |
| Multi-worker coordination | Load balancing, failover | After single-worker proven |
| Capability negotiation | Dynamic capability discovery | After static registry proven |
| Runtime governance | Authority enforcement, rate limiting | After multi-worker |

---

## Files Created

| File | Purpose |
|------|---------|
| eos_ai/substrate/local_worker_runtime_daemon.py | Daemon runtime: loop, heartbeat, routing, proof |
| config/local_worker_runtime_daemon_v1.json | Daemon config |
| tests/test_local_worker_runtime_daemon.py | 14 daemon tests |
| docs/system/phase968l_local_worker_runtime_daemon_v1_report.md | This report |

## Directories Created

| Directory | Purpose |
|-----------|---------|
| data/runtime/local_worker_runtime/ | Daemon state |
| data/runtime/local_worker_runtime/inbox/ | Work packet inbox |
| data/runtime/local_worker_runtime/processed/ | Completed packets |
| data/runtime/local_worker_runtime/failed/ | Failed packets |
| data/runtime/runtime_proofs/ | Persistent proof records |
| config/ | Daemon configuration |

---

## Tests Passed

| Test File | Tests | Status |
|-----------|-------|--------|
| test_local_worker_runtime_daemon.py | 14 | ALL PASS |

Test coverage:
- Config loading (default + custom)
- Heartbeat emission and file write
- Runtime status file write
- Ping routes to correct adapter (dry-run)
- Chrome open routes to windows relay (dry-run)
- Proof persisted to disk after routing
- Unsupported capability rejected with proof
- Rejected packet moved to failed/
- Invalid JSON does not crash daemon
- Empty JSON packet handled gracefully
- Missing action_type rejected
- Successful packet moved to processed/
- All directories created by ensure_directories

---

## Daemon Dry-Run Proof

The daemon was run in --once --dry-run mode on VPS:

```
[daemon] heartbeat emitted: 2026-05-07T19:13:37+00:00
[daemon] --once mode: 1 packet(s) found
[daemon] processing: REQ-PING-DAEMON-PROOF-001.json
[daemon]   action_type=ping request_id=REQ-PING-DAEMON-PROOF-001
[daemon]   routing to adapter: windows_interactive_desktop_relay via filesystem_json
[daemon] proof persisted: PROOF-6f3eeec4.json
[daemon]   completed: proof_status=completed adapter_status=dry_run
[daemon] --once mode complete
```

---

## What Was Not Executed

| Item | Status |
|------|--------|
| Chrome opened | NO |
| Drive/Docs accessed | NO |
| Gmail accessed | NO |
| Screenshots captured | NO |
| Tokens/cookies captured | NO |
| Memory promoted | NO |
| Discord daemon started | NO |
| LLM calls made | NO |
| Autonomous planning | NO |

---

## Next Gate: DISCORD_INTERFACE_ADAPTER_V1

Build a minimal Discord interface adapter that can submit filesystem
work packets to the local worker runtime daemon and receive
RuntimeProof responses. No orchestration or autonomy layers.
