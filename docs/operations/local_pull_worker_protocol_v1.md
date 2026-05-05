# Local Pull Worker Protocol v1

**Phase:** 96.8A
**Status:** Active
**Layer:** UMH Substrate — `core/environment_bridge/local_pull_protocol.py`

## Purpose

Defines the pull-based execution protocol where the local worker
polls the VPS outbox for approved work packets, copies them locally,
claims them, validates them, executes, and writes results.

## Pull Cycle Steps

```
1. DISCOVER  — scan remote outbox for *.json packets
2. COPY      — copy packet from remote outbox to local inbox
3. CLAIM     — set status=claimed, write claimed_at timestamp
4. VALIDATE  — run validator_fn if provided, block invalid packets
5. EXECUTE   — execute locally (not done by this module — delegated)
6. RESULT    — write result JSON to local results directory
7. SYNC      — copy local results back to remote results directory
```

## Transport Strategies

| Strategy | Description |
|----------|-------------|
| `LOCAL_ONLY` | Remote and local on same filesystem (dev/test) |
| `SCP_PULL` | SCP from VPS outbox to local inbox |
| `RSYNC_PULL` | Rsync from VPS outbox to local inbox |
| `SHARED_FOLDER` | Shared folder (Tailscale, NFS, etc.) |
| `MANUAL_COPY` | Founder copies files manually |

## Cycle Status Values

| Status | Meaning |
|--------|---------|
| `READY` | Cycle initialized, ready to discover |
| `NO_REMOTE_QUEUE` | Remote outbox directory missing or unavailable |
| `NO_LOCAL_QUEUE` | Local inbox directory missing |
| `NO_PACKETS` | No packets found in remote outbox |
| `PACKET_CLAIMED` | At least one packet claimed but not yet executed |
| `PACKET_INVALID` | Packet failed validation |
| `EXECUTION_BLOCKED` | All packets blocked by validator |
| `RESULT_WRITTEN` | At least one result written successfully |
| `SYNC_FAILED` | Result sync to remote failed |
| `BLOCKED` | Cycle cannot proceed |

## Safety Properties

- Packets are **claimed** before execution — prevents duplicate execution
- Invalid packets are **blocked**, never silently skipped
- Status transitions are written to the packet JSON on disk — auditable
- `force_` parameters allow deterministic testing without filesystem I/O

## Queue Paths

- VPS outbox: `/opt/OS/data/work_queue/outbox/`
- VPS results: `/opt/OS/data/work_queue/results/`
- Local inbox: `~/eos_advisor_messages/inbox/`
- Local results: `~/eos_advisor_messages/results/`
