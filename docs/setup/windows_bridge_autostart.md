# Windows Bridge Autostart

The local bridge server runs on the Windows workstation and handles
browser exports, MFA routing, and future Windows-side capabilities
(UI-TARS, Voice-Pro, etc.).

## Autostart via Scheduled Task

The bridge auto-starts on Windows user login and auto-restarts on failure.
VPS installs this task once via Tailscale SSH.

### Install command (run from VPS)

```bash
ssh antony@100.74.199.102 'schtasks /create \
  /tn "EOS-Bridge" \
  /tr "wsl -d Ubuntu -e bash -lc \"cd ~/OS/services && python3 local_bridge_server.py >> ~/eos_bridge.log 2>&1\"" \
  /sc onlogon \
  /rl highest \
  /f'
```

### What this does

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `/tn` | EOS-Bridge | Task name |
| `/tr` | wsl → python3 local_bridge_server.py | Runs bridge in WSL |
| `/sc` | onlogon | Fires on user login |
| `/rl` | highest | Run with elevated privileges |
| `/f` | — | Force overwrite if exists |

### Verify task installed

```bash
ssh antony@100.74.199.102 'schtasks /query /tn "EOS-Bridge" /fo list'
```

### Manual start/stop from VPS

```bash
# Start
ssh antony@100.74.199.102 'schtasks /run /tn "EOS-Bridge"'

# Stop
ssh antony@100.74.199.102 'wsl -d Ubuntu -e bash -c "pkill -f local_bridge_server"'

# Check status
ssh antony@100.74.199.102 'wsl -d Ubuntu -e bash -c "pgrep -f local_bridge_server && echo running || echo stopped"'
```

### Automatic recovery

The VPS watchdog (`services/bridge_health.py`) handles recovery transparently:

1. Any bridge-dependent operation calls `ensure_bridge_live()` first
2. If bridge unreachable → SSH to Windows → start process
3. Polls until port responds (up to 30s)
4. If SSH fails → surfaces one-time setup gate to Discord

You never need to SSH to Windows manually. The VPS handles it.

## Prerequisites (one-time)

### 1. Tailscale SSH on Windows

```powershell
# On Windows (admin PowerShell):
tailscale set --ssh
```

### 2. WSL with Ubuntu

The bridge runs in WSL. Verify:
```bash
ssh antony@100.74.199.102 'wsl -l -v'
```

### 3. Python + deps in WSL

```bash
ssh antony@100.74.199.102 'wsl -d Ubuntu -e bash -lc "python3 --version && pip3 show aiohttp"'
```

### 4. Repo synced to Windows

The bridge expects the repo at `~/OS/` in WSL. Sync via git:
```bash
ssh antony@100.74.199.102 'wsl -d Ubuntu -e bash -lc "cd ~/OS && git pull"'
```

## Environment variables

| Variable | Default | Where |
|----------|---------|-------|
| EOS_WINDOWS_TAILSCALE_HOST | 100.74.199.102 | services/.env on VPS |
| EOS_WINDOWS_TAILSCALE_USER | antony | services/.env on VPS |
| EOS_LOCAL_BRIDGE_PORT | 8766 | both VPS + Windows |
| EOS_WINDOWS_BRIDGE_SCRIPT | ~/OS/services/local_bridge_server.py | VPS (override if needed) |
| EOS_WINDOWS_BRIDGE_LOG | ~/eos_bridge.log | VPS (log path on Windows) |

## Lifecycle pattern

This same pattern applies to any future Windows-side service:

1. **Autostart**: schtasks /create with /sc onlogon
2. **Watchdog**: VPS-side health check + SSH autostart
3. **Integration**: caller invokes `ensure_X_live()` transparently
4. **Setup gate**: one-time Discord notification with remediation steps

Template for new services: copy `bridge_health.py`, change the health
endpoint and start command.
