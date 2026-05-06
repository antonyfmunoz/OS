# Phase 96.8B — Local Worker Bootstrap Packet

**Date:** 2026-05-05
**Status:** READY FOR FOUNDER EXECUTION
**Gate:** BOOTSTRAP_LOCAL_WORKER_BRIDGE_ON_WINDOWS

---

## What Is Ready

| Item | Status |
|------|--------|
| VPS queue exists | YES |
| VPS outbox exists | YES |
| W0-001 packet found | YES |
| Packet ID | WP-W0-001-CU-RERUN-001 |
| Packet approval | APPROVED |
| Packet executed | NO (awaiting local worker) |
| Local worker heartbeat | NO (awaiting bootstrap) |
| All bridge tests | 64 passed |
| Bootstrap status module | Created + tested |

---

## What Is NOT Executed Yet

- Local worker has not been bootstrapped
- W0-001 CU rerun has not executed
- No Chrome has opened
- No Google Drive/Docs accessed
- No founder confirmation provided
- No results written

---

## Local Bootstrap Commands

Run these **on the Windows PC** in WSL/Ubuntu terminal.

### Step 0: Open WSL

Open Windows Terminal → Ubuntu (or `wsl` from PowerShell).

### Step 1: Confirm Local Repo

```bash
cd /opt/OS
pwd
git status --short
```

Expected: working directory is `/opt/OS`, clean or with local changes only.

### Step 2: Pull Latest Code

```bash
git pull origin main
```

### Step 3: Create Queue Directories

```bash
mkdir -p ~/eos_advisor_messages/inbox
mkdir -p ~/eos_advisor_messages/outbox
mkdir -p ~/eos_advisor_messages/archive
mkdir -p ~/eos_advisor_messages/heartbeats
mkdir -p ~/eos_advisor_messages/results
```

### Step 4: Verify Directories

```bash
ls ~/eos_advisor_messages/
```

Expected: `archive  heartbeats  inbox  outbox  results`

### Step 5: Start Tmux Session

```bash
tmux new -s eos-worker
```

If already exists:
```bash
tmux attach -t eos-worker
```

If tmux not installed:
```bash
sudo apt-get install -y tmux
tmux new -s eos-worker
```

### Step 6: Copy W0-001 Packet to Local Inbox

Option A — SCP from VPS:
```bash
scp root@100.77.233.50:/opt/OS/data/work_queue/outbox/w0_001_cu_rerun_while_present_packet.json ~/eos_advisor_messages/inbox/
```

Option B — Rsync from VPS:
```bash
rsync -avz root@100.77.233.50:/opt/OS/data/work_queue/outbox/ ~/eos_advisor_messages/inbox/
```

Option C — Manual copy (if VPS not reachable from local):
Copy the file manually from VPS `/opt/OS/data/work_queue/outbox/w0_001_cu_rerun_while_present_packet.json` to local `~/eos_advisor_messages/inbox/`.

### Step 7: Verify Packet Is Present

```bash
cat ~/eos_advisor_messages/inbox/w0_001_cu_rerun_while_present_packet.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Packet: {d[\"packet_id\"]}'); print(f'Status: {d[\"approval_status\"]}'); print(f'Risk: {d[\"risk_level\"]}')"
```

Expected:
```
Packet: WP-W0-001-CU-RERUN-001
Status: approved
Risk: high
```

### Step 8: Start Local Worker

```bash
cd /opt/OS
python3 /opt/OS/eos_ai/substrate/local_worker_auto_loop.py ~/eos_advisor_messages/inbox/w0_001_cu_rerun_while_present_packet.json
```

### Step 9: Observe Execution (Founder Must Be Present)

See W0-001 Observation Checklist below.

### Step 10: Verify Heartbeat

In a second terminal or tmux pane:
```bash
cat ~/eos_advisor_messages/heartbeats/local-windows-worker.json
```

Expected: JSON with `"status": "online"` and recent `last_seen_at`.

---

## Packet Transfer Options

| Method | Command | When to Use |
|--------|---------|-------------|
| SCP | `scp root@100.77.233.50:/opt/OS/data/work_queue/outbox/w0_001_cu_rerun_while_present_packet.json ~/eos_advisor_messages/inbox/` | Tailscale active, SSH works |
| Rsync | `rsync -avz root@100.77.233.50:/opt/OS/data/work_queue/outbox/ ~/eos_advisor_messages/inbox/` | Pull all packets at once |
| Manual | Copy file via GitHub, USB, or browser download | SSH not available |

If you don't know the exact filename:
```bash
ssh root@100.77.233.50 "ls /opt/OS/data/work_queue/outbox/"
```

---

## Heartbeat Verification

After the worker starts, check:

```bash
cat ~/eos_advisor_messages/heartbeats/local-windows-worker.json
```

Expected fields:
```json
{
  "worker_id": "local-windows-worker",
  "host": "DESKTOP-LVGUIQ9",
  "environment": "local_wsl",
  "tmux_session": "eos-worker",
  "status": "online",
  "last_seen_at": "2026-05-05T..."
}
```

If missing or stale (>60 seconds old), the worker may have crashed. Check the tmux pane for errors.

---

## Result Verification

After execution completes, check:

```bash
ls ~/eos_advisor_messages/results/
cat ~/eos_advisor_messages/results/WP-W0-001-CU-RERUN-001*.json
```

Results should include proof artifacts matching the 9 proof requirements.

To sync results back to VPS:
```bash
scp ~/eos_advisor_messages/results/*.json root@100.77.233.50:/opt/OS/data/work_queue/results/
```

---

## Expected Outbox/Result Artifacts

After W0-001 CU execution, local results directory should contain:

| Artifact | Purpose |
|----------|---------|
| correct_account_visible | Proof: correct Google account was shown |
| drive_visible | Proof: Google Drive loaded |
| drive_inventory_count_26 | Proof: 26 files visible in My Drive |
| docs_openability | Proof: Google Docs opened |
| tab_detection_attempt | Proof: tab detection was attempted |
| content_extraction_attempt | Proof: content extraction was attempted |
| governance_compliance | Proof: no blocked actions occurred |
| no_secret_no_mutation_confirmation | Proof: no secrets captured, no files mutated |
| founder_confirmation_response | Founder's explicit response |

---

## Founder Confirmation Options

After observing the execution, report ONE of:

| Option | Meaning |
|--------|---------|
| `CONFIRM_DRIVE_CU_ONLY` | Drive CU worked; Docs CU did not |
| `CONFIRM_DOCS_CU_ONLY` | Docs CU worked; Drive CU did not |
| `CONFIRM_BOTH` | Both Drive and Docs CU worked |
| `DO_NOT_CONFIRM` | Neither worked or unacceptable results |
| `RERUN_WHILE_PRESENT` | Need to run again with founder present |

---

## Next Gate

**RUN_LOCAL_WORKER_BOOTSTRAP_ON_WINDOWS**

Founder runs the bootstrap, starts the local worker, observes W0-001 CU execution, and reports the confirmation result.
