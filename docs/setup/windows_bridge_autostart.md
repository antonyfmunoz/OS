# Windows Bridge Autostart

The local bridge server runs on the Windows workstation (in WSL) and handles
browser exports, MFA routing, and future Windows-side capabilities
(UI-TARS, Voice-Pro, etc.).

## Autostart via Scheduled Task

The bridge auto-starts on Windows user login and auto-restarts on failure.
VPS installs this task once via OpenSSH.

### Install command (run from VPS)

```bash
ssh -l "antonys beast pc" 100.74.199.102 powershell -c \
  'schtasks /create /tn "EOS-Bridge" /tr "wsl -d Ubuntu -e bash -lc \"cd ~/OS/services && python3 local_bridge_server.py >> ~/eos_bridge.log 2>&1\"" /sc onlogon /rl highest /f'
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
ssh -l "antonys beast pc" 100.74.199.102 powershell -c 'schtasks /query /tn "EOS-Bridge" /fo list'
```

### Manual start/stop from VPS

```bash
# Start (via scheduled task)
ssh -l "antonys beast pc" 100.74.199.102 powershell -c 'schtasks /run /tn "EOS-Bridge"'

# Start (direct)
ssh -l "antonys beast pc" 100.74.199.102 powershell -c 'Start-Process -NoNewWindow -FilePath "wsl" -ArgumentList "-d","Ubuntu","-e","bash","-lc","cd ~/OS/services && python3 local_bridge_server.py >> ~/eos_bridge.log 2>&1"'

# Stop
ssh -l "antonys beast pc" 100.74.199.102 powershell -c 'wsl -d Ubuntu -e bash -c "pkill -f local_bridge_server"'

# Check status
ssh -l "antonys beast pc" 100.74.199.102 powershell -c 'wsl -d Ubuntu -e bash -c "pgrep -f local_bridge_server && echo running || echo stopped"'
```

### Automatic recovery

The VPS watchdog (`services/bridge_health.py`) handles recovery transparently:

1. Any bridge-dependent operation calls `ensure_bridge_live()` first
2. If bridge unreachable → SSH to Windows → start process
3. Polls until port responds (up to 30s)
4. If SSH fails → surfaces one-time setup gate to Discord

You never need to SSH to Windows manually. The VPS handles it.

## Prerequisites (one-time, already done)

### 1. OpenSSH Server on Windows

```powershell
# Install (admin PowerShell)
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Start and auto-enable
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

### 2. Bind sshd to Tailscale interface

Edit `C:\ProgramData\ssh\sshd_config`:
```
ListenAddress 100.74.199.102
```

### 3. VPS pubkey in administrators_authorized_keys

```powershell
# Paste VPS pubkey into:
#   C:\ProgramData\ssh\administrators_authorized_keys
#
# Then fix permissions (CRITICAL — sshd ignores file otherwise):
icacls "C:\ProgramData\ssh\administrators_authorized_keys" /inheritance:r /grant "SYSTEM:F" /grant "Administrators:F"
```

### 4. WSL with Ubuntu

```bash
ssh -l "antonys beast pc" 100.74.199.102 powershell -c 'wsl -l -v'
```

### 5. Python + deps in WSL

```bash
ssh -l "antonys beast pc" 100.74.199.102 powershell -c 'wsl -d Ubuntu -e bash -lc "python3 --version && pip3 show aiohttp"'
```

### 6. Repo synced to Windows WSL

The bridge expects the repo at `~/OS/` in WSL:
```bash
ssh -l "antonys beast pc" 100.74.199.102 powershell -c 'wsl -d Ubuntu -e bash -lc "cd ~/OS && git pull"'
```

## Environment variables

| Variable | Default | Where |
|----------|---------|-------|
| EOS_WINDOWS_TAILSCALE_HOST | 100.74.199.102 | services/.env on VPS |
| EOS_WINDOWS_TAILSCALE_USER | antonys beast pc | services/.env on VPS |
| EOS_LOCAL_BRIDGE_PORT | 8766 | both VPS + Windows |
| EOS_WINDOWS_BRIDGE_SCRIPT | ~/OS/services/local_bridge_server.py | VPS (WSL path) |
| EOS_WINDOWS_BRIDGE_LOG | ~/eos_bridge.log | VPS (WSL log path) |

## SSH notes

- Username has spaces (`antonys beast pc`). Always use `-l` flag with
  list-form args in subprocess. Never use `user@host` concatenation.
- Tailscale SSH server is NOT available on Windows — only OpenSSH Server
  bound to the Tailscale interface (100.74.199.102) works.
- VPS pubkey must be in `administrators_authorized_keys` (not regular
  `authorized_keys`) because the Windows user is an administrator.

## Lifecycle pattern

This same pattern applies to any future Windows-side service:

1. **Autostart**: schtasks /create with /sc onlogon
2. **Watchdog**: VPS-side health check + SSH autostart
3. **Integration**: caller invokes `ensure_X_live()` transparently
4. **Setup gate**: one-time Discord notification with remediation steps

Template for new services: copy `bridge_health.py`, change the health
endpoint and start command.
