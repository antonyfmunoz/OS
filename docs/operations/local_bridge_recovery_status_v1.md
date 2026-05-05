# Local Bridge Recovery Status v1

**Date**: 2026-05-04
**Phase**: 94D.1 — Remote Local Bridge Recovery / Start Attempt v1
**Work Order**: WO-LOCAL-PILOT-GDRIVE-GDOCS-001

---

## Current State

| Field | Value |
|-------|-------|
| Local PC online (Tailscale) | YES — `desktop-lvguiq9` at `100.74.199.102`, Windows, active, direct |
| Tailscale ping | YES — 75ms round-trip |
| Bridge server (port 8766) | **RUNNING** — started remotely via SSH |
| Bridge health check | **PASS** — `{"status":"ok","machine":"local"}` |
| SSH (port 22) | AVAILABLE — Windows OpenSSH, ED25519 key auth |
| Tailscale SSH | FAILED — `502 Bad Gateway` (not needed, direct SSH works) |

---

## Recovery Verdict

**REMOTE RECOVERY SUCCEEDED.**

The VPS started the local bridge server remotely via:

```
VPS → SSH (port 22, ED25519 key auth) → Windows OpenSSH → wsl -e bash → tmux new-session → python3 ~/local_bridge_server.py
```

### Recovery sequence

1. SSH keypair generated on VPS (`~/.ssh/id_ed25519`, comment `vps-to-local-pc`)
2. Public key added to `C:\ProgramData\ssh\administrators_authorized_keys` on local PC
3. ACL fixed: `SYSTEM:(F)` + `Administrators:(F)`, inheritance removed
4. Passwordless SSH confirmed: `ssh ... 'echo SSH_OK'` → `SSH_OK`
5. Bridge started: `ssh ... 'wsl -e bash -c "tmux new-session -d -s bridge ..."'` → `BRIDGE_STARTED`
6. Health verified from VPS: `curl http://100.74.199.102:8766/health` → `{"status":"ok","machine":"local"}`

---

## Remote Bridge Start Command (reusable)

If the bridge goes down in the future, the VPS can restart it with:

```bash
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 \
  'DESKTOP-LVGUIQ9\antonys beast pc'@100.74.199.102 \
  'wsl -e bash -c "tmux new-session -d -s bridge \"python3 ~/local_bridge_server.py\""'
```

Then verify:

```bash
curl -s --connect-timeout 5 http://100.74.199.102:8766/health
```

---

## VPS SSH Config

| Field | Value |
|-------|-------|
| Key file | `/root/.ssh/id_ed25519` |
| Key type | ED25519 |
| Fingerprint | `SHA256:uHmtd2VEVaRSaKYBZln9BqUJMSXsLjiJc/sAehLFFmQ` |
| Comment | `vps-to-local-pc` |
| Target | `DESKTOP-LVGUIQ9\antonys beast pc`@`100.74.199.102` |
| Port | 22 (Windows OpenSSH) |
| Auth | Public key (no password) |

---

## Architecture Gap (RESOLVED)

The bootstrap problem identified earlier (no remote path to start local processes) is now solved:

| Gap | Status | Resolution |
|-----|--------|------------|
| No remote bootstrap | **RESOLVED** | SSH key auth established, VPS can start processes via `ssh → wsl → tmux` |
| No SSH on local | **RESOLVED** | Windows OpenSSH was running on port 22 (initial test timed out due to Tailscale SSH wrapper interference) |
| No auto-start | OPEN | Bridge server does not auto-start on login or WSL boot |

### Remaining improvement (NOT implemented)

- **Auto-start bridge on WSL boot** — add to `.bashrc` or Windows Task Scheduler to eliminate manual/remote start entirely
