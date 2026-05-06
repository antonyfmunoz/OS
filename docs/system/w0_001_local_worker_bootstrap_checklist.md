# W0-001 Local Worker Bootstrap Checklist

**Date:** 2026-05-05
**Status:** PENDING FOUNDER EXECUTION

---

## Pre-Flight (Before Running Worker)

- [ ] Windows PC is powered on
- [ ] WSL/Ubuntu terminal is open
- [ ] Tailscale is connected (VPS at 100.77.233.50 reachable)
- [ ] `/opt/OS` exists locally and is current: `cd /opt/OS && git pull origin main`
- [ ] Queue directories created: `mkdir -p ~/eos_advisor_messages/{inbox,outbox,archive,heartbeats,results}`
- [ ] tmux installed: `tmux -V` (install if missing: `sudo apt-get install -y tmux`)
- [ ] tmux session started: `tmux new -s eos-worker` or `tmux attach -t eos-worker`
- [ ] W0-001 packet copied to inbox: `ls ~/eos_advisor_messages/inbox/w0_001*.json`
- [ ] Packet is approved: check `approval_status` field = `"approved"`

---

## Execution (Inside Tmux)

- [ ] Worker started: `python3 /opt/OS/eos_ai/substrate/local_worker_auto_loop.py ~/eos_advisor_messages/inbox/w0_001_cu_rerun_while_present_packet.json`
- [ ] Worker did not crash on startup
- [ ] Heartbeat file written: `cat ~/eos_advisor_messages/heartbeats/local-windows-worker.json`
- [ ] Worker claimed the packet (logged "CLAIMED" or similar)
- [ ] Worker validated the packet (logged "VALIDATED" or similar)
- [ ] Worker began execution

---

## Post-Execution Verification

- [ ] Worker wrote result artifacts to `~/eos_advisor_messages/results/`
- [ ] Result JSON contains proof artifacts
- [ ] No crash or unhandled exception in tmux output
- [ ] Worker heartbeat shows recent `last_seen_at`

---

## Result Transfer to VPS

- [ ] Results synced: `scp ~/eos_advisor_messages/results/*.json root@100.77.233.50:/opt/OS/data/work_queue/results/`
- [ ] VPS has results: `ls /opt/OS/data/work_queue/results/` (run on VPS)

---

## Status Codes

| If This Happens | Status |
|-----------------|--------|
| Worker starts, claims, executes, writes results | SUCCESS |
| Worker starts but packet not in inbox | PACKET_MISSING — copy packet first |
| Worker crashes on startup | WORKER_ERROR — check Python traceback |
| Worker validates but blocks execution | GOVERNANCE_BLOCK — check blocked actions |
| Worker runs but Chrome doesn't open | ENVIRONMENT_ERROR — check Windows GUI access |
| Worker completes but no results written | RESULT_ERROR — check output path |
