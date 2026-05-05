# Advisor Relay Bridge Wiring v1

**Phase**: 94D.5 — Relay Wiring + GUI Healthcheck + W0-001 Relaunch
**Status**: WIRED
**Date**: 2026-05-04

---

## Purpose

Wire the Phase 94D.4 advisor relay contracts into the existing bridge
transport so that approval requests from the local worker reach the VPS
advisor session, and approval responses flow back.

## Wiring Architecture

```
LOCAL PC WORKER                    VPS ORCHESTRATOR
─────────────────                  ──────────────────
Worker needs approval              Advisor session
  → writes AdvisorMessageFile      ← reads via SSH poll
    to ~/eos_outbox/                 or bridge reverse path
                                   
                                   Founder responds
                                     → writes AdvisorMessageFile
Worker receives response             to advisor_response.json
  ← reads from ~/eos_inbox/       ← forwards via bridge POST /message
    or ~/eos_advisor_messages/       or SSH → wsl → file write
```

## Module: `advisor_bridge_transport.py`

Transport-aware helpers that bind abstract relay contracts to current topology.

### Path Builders
- `build_local_inbox_path(session_name)` → `~/eos_inbox/{session_name}.txt`
- `build_local_outbox_path(work_order_id)` → `~/eos_outbox/advisor_request_{wo_id}.json`

### Message Serialization
- `AdvisorMessageFile` — serializable message with `to_json()`/`from_json()`
- `AdvisorMessageFile.from_envelope()` — convert from Phase 94D.4 MessageEnvelope
- `create_worker_approval_request_file()` — build APPROVAL_NEEDED file
- `create_advisor_response_file()` — build APPROVAL_RESPONSE file

### Transport Commands
- `build_forward_to_local_payload()` — payload for bridge `forward_to_local()`
- `build_poll_local_outbox_command()` — SSH command to list outbox files
- `build_read_local_outbox_file_command()` — SSH command to read specific file
- `build_write_local_inbox_command()` — SSH command to write to inbox
- `build_ssh_health_command()` — SSH echo test
- `build_bridge_health_command()` — curl bridge health
- `build_mkdir_local_dirs_command()` — create inbox/outbox/advisor dirs

## No Existing Internals Modified

The bridge server, bridge client, webhook receiver, and station bus are
untouched. This module wraps them additively.

## File

`eos_ai/substrate/advisor_bridge_transport.py`
