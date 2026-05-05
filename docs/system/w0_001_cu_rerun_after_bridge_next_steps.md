# W0-001 CU Rerun — Next Steps After Bridge

**Phase:** 96.8A
**Status:** Infrastructure complete. Execution pending.

## What Exists

- Environment Bridge infrastructure: 9 Python modules in `core/environment_bridge/`
- Work packet: `data/work_queue/outbox/w0_001_cu_rerun_while_present_packet.json`
- Packet ID: `WP-W0-001-CU-RERUN-001`
- Risk: HIGH, Approval: APPROVED
- 86 tests passing, 176 regression passing

## What Must Happen Next

### 1. Bootstrap Local Worker (one-time, founder at desktop)

See `docs/system/local_worker_bootstrap_instructions_v1.md` for full steps.

```bash
mkdir -p ~/eos_advisor_messages/{inbox,outbox,archive,heartbeats,results}
tmux new-session -d -s eos-worker -n main
```

### 2. Copy Packet to Local Inbox

Either via rsync pull:
```bash
rsync -avz root@100.77.233.50:/opt/OS/data/work_queue/outbox/ \
  ~/eos_advisor_messages/inbox/
```

Or manual copy of `w0_001_cu_rerun_while_present_packet.json` to
`~/eos_advisor_messages/inbox/`.

### 3. Execute CU Rerun (founder present)

The local worker claims the packet, validates it, and executes the
CU rerun on Google Drive and Google Docs. Founder must be present
to visually confirm:

- Correct Google account visible
- Drive loads with 26 documents
- Docs open and tabs are detected
- Content extraction runs
- No credential/token/mutation occurs

### 4. Write Result and Sync Back

Worker writes result to `~/eos_advisor_messages/results/`.
Result syncs back to VPS at `/opt/OS/data/work_queue/results/`.

### 5. Founder Confirmation

Founder provides explicit confirmation after visual verification.
System never auto-confirms.

## Blockers

- None from infrastructure side
- Only blocker: founder must be physically at Windows desktop

## Dependency Chain

```
Phase 96.8A (this) → Bootstrap → W0-001 CU Rerun → Result Ingestion → W0-001 Complete
```
