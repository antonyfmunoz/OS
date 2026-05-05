# Local Worker Bootstrap Instructions v1

**Phase:** 96.8A
**Status:** Active
**One-time setup.** After bootstrap, worker runs autonomously.

## Prerequisites

- Windows desktop with WSL2 installed
- tmux installed in WSL (`sudo apt-get install -y tmux`)
- Tailscale connected (VPS at 100.77.233.50)
- Python 3.11+ in WSL

## Required Steps (must complete all 4)

### Step 1: Create Queue Directories

```bash
mkdir -p ~/eos_advisor_messages/{inbox,outbox,archive,heartbeats,results}
```

### Step 2: Start Persistent Tmux Session

```bash
tmux new-session -d -s eos-worker -n main
```

### Step 3: Start Local Worker in Tmux

```bash
tmux send-keys -t eos-worker:main \
  'python3 /opt/OS/eos_ai/substrate/local_worker_auto_loop.py \
   ~/eos_advisor_messages/inbox/w0_001_cu_rerun_while_present.json' Enter
```

### Step 4: Verify Heartbeat

```bash
cat ~/eos_advisor_messages/heartbeats/local-windows-worker.json
```

Expected: JSON with `status: "online"` and recent `last_seen_at`.

## Optional Steps (convenience automation)

### Step 5: Windows Task Scheduler Auto-Start (optional)

```powershell
schtasks /create /tn "EOS Local Worker" `
  /tr "wsl bash -c 'tmux new-session -d -s eos-worker'" `
  /sc onlogon /rl highest
```

### Step 6: WSL .bashrc Auto-Start (optional)

```bash
echo '# EOS worker auto-start
if ! tmux has-session -t eos-worker 2>/dev/null; then
  tmux new-session -d -s eos-worker -n main
fi' >> ~/.bashrc
```

### Step 7: Configure Rsync Pull from VPS (optional)

```bash
rsync -avz root@100.77.233.50:/opt/OS/data/work_queue/outbox/ \
  ~/eos_advisor_messages/inbox/
```

## Verification

After completing steps 1-4:

1. Heartbeat file exists at `~/eos_advisor_messages/heartbeats/local-windows-worker.json`
2. Tmux session `eos-worker` is running: `tmux has-session -t eos-worker`
3. Queue directories exist: `ls ~/eos_advisor_messages/`

## After Bootstrap

The worker runs autonomously:
- Polls `~/eos_advisor_messages/inbox/` for approved packets
- Executes locally (GUI, browser, tmux as needed)
- Writes results to `~/eos_advisor_messages/results/`
- Writes heartbeat to `~/eos_advisor_messages/heartbeats/`
- VPS reads heartbeat and results for status
