# End-to-End Routed Execution Runbook v1

**Date:** 2026-05-07
**Phase:** 96.8Q
**Status:** Proven working

---

## Overview

This runbook documents the exact operator steps to start the
full canonical routed execution path and validate it with
Discord commands.

---

## Startup Order

Components must start in this exact order. Each step depends
on the previous step being ready.

### A) VPS — Claude Code / Control Session

This is your command center. SSH into VPS via Termius or
terminal. Claude Code runs here in tmux.

```bash
ssh root@100.77.233.50
cd /opt/OS
git pull origin main
```

No services need to start on VPS for the routed execution
path. The VPS is used for code changes, pushes, and monitoring.

### B) Local Windows — PowerShell Relay

Open a PowerShell window on the Windows desktop. The relay
must be visible (not minimized, not in a background service).

```powershell
cd C:\Users\<username>\path\to\OS
git pull origin main
.\scripts\windows_interactive_desktop_relay.ps1
```

The relay will print:
```
[HH:MM:SS] [relay] Windows Interactive Desktop Relay v1
[HH:MM:SS] [relay] inbox: C:\Users\<username>\eos_advisor_messages\windows_desktop_relay\inbox
[HH:MM:SS] [relay] outbox: C:\Users\<username>\eos_advisor_messages\windows_desktop_relay\outbox
[HH:MM:SS] [relay] polling...
```

Leave this window running.

### C) Local WSL — Worker Runtime Daemon

Open a WSL terminal (or a new tmux pane in WSL).

```bash
cd /opt/OS
git pull origin main
source venv/bin/activate
python3 eos_ai/substrate/local_worker_runtime_daemon.py \
  --config config/local_worker_runtime_daemon_v1.json
```

The daemon will print:
```
[HH:MM:SS] [daemon] ==================================================
[HH:MM:SS] [daemon] Local Worker Runtime Daemon v1
[HH:MM:SS] [daemon] worker_id: local_wsl_worker
[HH:MM:SS] [daemon] capabilities: ['ping', 'open_application_url']
[HH:MM:SS] [daemon] ==================================================
```

Leave this running.

### D) Local WSL — Discord Interface Adapter

Open another WSL terminal (or tmux pane).

```bash
cd /opt/OS
source venv/bin/activate
python3 eos_ai/interfaces/discord_interface_adapter_v1.py
```

The adapter will print:
```
[HH:MM:SS] [discord-adapter] ==================================================
[HH:MM:SS] [discord-adapter] Discord Interface Adapter v1 (routed)
[HH:MM:SS] [discord-adapter] router: control_plane_v1
[HH:MM:SS] [discord-adapter] ==================================================
[HH:MM:SS] [discord-adapter] connected as BotName#1234
```

Leave this running.

### E) Discord — Test Commands

Go to the Discord channel configured for the bot.

#### Test 1: Ping

```
!ping
```

Expected response:
```
**!ping** -- routing (REQ-PING-*), waiting for proof...
**!ping** -- completed
action: ping
adapter: windows_interactive_desktop_relay
runtime: local_worker_runtime_daemon
adapter_status: pong
request_id: REQ-PING-*
```

#### Test 2: Chrome

```
!chrome
```

Expected response:
```
**!chrome** -- routing (REQ-W0-*), waiting for proof...
**!chrome** -- completed
action: open_application_url
adapter: windows_interactive_desktop_relay
runtime: local_worker_runtime_daemon
adapter_status: completed
request_id: REQ-W0-*
```

Expected visible result: Chrome opens on the Windows desktop
showing Google Drive (My Drive).

#### Test 3: Status

```
!status
```

Expected response:
```
**status** -- adapter=running router=control_plane_v1
```

---

## Shutdown Order

Reverse of startup:

1. Ctrl+C the Discord adapter (WSL terminal D)
2. Ctrl+C the daemon (WSL terminal C)
3. Ctrl+C the PowerShell relay (Windows terminal B)

---

## Troubleshooting

### Stale repo in one terminal

**Symptom:** ImportError or AttributeError after a VPS push.

**Fix:**
```bash
cd /opt/OS && git pull origin main
```

Do this in every terminal (WSL, PowerShell) before restarting.

### venv not activated

**Symptom:** `ModuleNotFoundError: No module named 'discord'`

**Fix:**
```bash
source venv/bin/activate
```

The venv must be active in every WSL terminal that runs
Python components.

### discord.py not installed

**Symptom:** `ModuleNotFoundError: No module named 'discord'`
even with venv active.

**Fix:**
```bash
pip install discord.py
```

### Missing DISCORD token

**Symptom:** `[discord-adapter] ERROR: no Discord token found`

**Fix:** Ensure `DISCORD_BOT_TOKEN` is set in the environment
or in the `.env` file that the adapter loads. The env var name
is configured in `config/discord_interface_adapter_v1.json`
under `discord_token_env_var`.

```bash
export DISCORD_BOT_TOKEN="your-token-here"
```

### PowerShell relay not running

**Symptom:** Discord !ping or !chrome times out.
Daemon log shows: `routing to adapter: windows_interactive_desktop_relay`
but no result arrives.

**Fix:** Start the relay on the Windows desktop:
```powershell
.\scripts\windows_interactive_desktop_relay.ps1
```

The relay must be running in a visible PowerShell window.

### Daemon not running

**Symptom:** Discord adapter says "routing" but never gets
a proof response. No daemon log output.

**Fix:** Start the daemon:
```bash
python3 eos_ai/substrate/local_worker_runtime_daemon.py \
  --config config/local_worker_runtime_daemon_v1.json
```

### Wrong repo path

**Symptom:** `FileNotFoundError` for config or registry files.

**Fix:** Ensure you are in `/opt/OS` (WSL/VPS) or the correct
clone directory (Windows). All paths are relative to the repo root.

### WSL vs Windows path confusion

**Symptom:** Relay inbox/outbox paths don't match between
daemon and relay.

**Key paths:**
- WSL sees: `/mnt/c/Users/<username>/eos_advisor_messages/windows_desktop_relay/`
- Windows sees: `C:\Users\<username>\eos_advisor_messages\windows_desktop_relay\`

These are the same physical directory via WSL's `/mnt/c` mount.

The daemon auto-detects the Windows home via `cmd.exe /C echo %USERPROFILE%`.
If detection fails, pass `--relay-root` explicitly:

```bash
python3 eos_ai/substrate/local_worker_runtime_daemon.py \
  --config config/local_worker_runtime_daemon_v1.json \
  --relay-root /mnt/c/Users/YourUsername/eos_advisor_messages/windows_desktop_relay
```

### Stale long-running process after git reset

**Symptom:** Old version of daemon or adapter still running
after a `git pull` with breaking changes.

**Fix:** Kill all Python processes from the repo, then restart:
```bash
pkill -f "local_worker_runtime_daemon"
pkill -f "discord_interface_adapter_v1"
```

Then restart in order (C → D above).

### Chrome does not open

**Symptom:** Daemon says completed but Chrome doesn't appear.

**Check:**
1. Is the PowerShell relay running?
2. Is Chrome installed at `C:\Program Files\Google\Chrome\Application\chrome.exe`?
3. Is the Windows user logged in to a desktop session?
4. Check relay outbox for result files with error messages.

### Proof timeout (60s default)

**Symptom:** Discord reply says timeout.

**Possible causes:**
- Relay not running (most common)
- Daemon not running
- Filesystem relay path mismatch
- Chrome hanging on startup

**Debug:** Check daemon and relay logs. The daemon logs every
packet it processes. The relay logs every request it reads.

---

## Architecture Reference

```
VPS (tmux)                    Local WSL                   Windows Desktop
┌─────────────┐    SSH/git    ┌─────────────────┐   /mnt/c  ┌──────────────┐
│ Claude Code  │───────────→ │ Worker Daemon    │────────→ │ PS Relay      │
│ (control)    │             │ Discord Adapter  │←────────│ Chrome        │
└─────────────┘              └─────────────────┘          └──────────────┘
                                     ↕
                              filesystem JSON
                              inbox / outbox
```

Each environment owns what it is natively authorized to do.
The VPS orchestrates. WSL bridges. Windows executes GUI.
