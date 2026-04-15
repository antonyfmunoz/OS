# Local Bridge Setup — Windows WSL

Routes Discord messages to a Claude Code session on your local PC
when you're at your desk. Falls back to VPS when you're away.

## Architecture

```
Discord msg → VPS discord_bot.py
  → local_bridge_client.forward_to_local()
    → GET http://100.74.199.102:8766/health (2s timeout)
    → If healthy: POST /message → local tmux session
    → If unhealthy: inject into VPS tmux session (normal path)

Local CC reply → Stop hook
  → POST http://100.77.233.50:8765/cc-reply
  → VPS webhook receiver → Discord channel
```

## VPS Side (already configured)

Files:
- `services/local_bridge_client.py` — HTTP client (forward_to_local)
- `services/cc_webhook_receiver.py` — reply receiver (updated for dex_local mapping)
- `docker-compose.yml` — port 8765 opened to 0.0.0.0 for Tailscale

Env vars (in both eos_ai/.env and services/.env):
```
EOS_LOCAL_BRIDGE_IP=100.74.199.102
EOS_LOCAL_BRIDGE_PORT=8766
EOS_LOCAL_BRIDGE_ENABLED=1
```

After updating docker-compose.yml, restart the Discord bot:
```bash
docker compose up -d os-discord
```

## Windows WSL Setup

### 1. Copy bridge server to WSL

From the Windows machine (Git Bash or PowerShell):
```bash
# Clone or pull the OS repo, then copy the server file
scp root@100.77.233.50:/opt/OS/services/local_bridge_server.py ~/local_bridge_server.py
scp root@100.77.233.50:/opt/OS/services/local_bridge_send_to_discord.sh ~/send-to-discord.sh
```

Or from WSL:
```bash
cp /mnt/c/Users/YourUser/path/to/OS/services/local_bridge_server.py ~/local_bridge_server.py
cp /mnt/c/Users/YourUser/path/to/OS/services/local_bridge_send_to_discord.sh ~/send-to-discord.sh
```

### 2. Install dependencies in WSL

```bash
pip install aiohttp
```

### 3. Start the bridge server

```bash
# Option A: Run directly
python3 ~/local_bridge_server.py

# Option B: Run in tmux (recommended)
tmux new-session -d -s bridge "python3 ~/local_bridge_server.py"
```

Verify it's running:
```bash
curl http://localhost:8766/health
# Should return: {"status": "ok", "machine": "local"}
```

### 4. Start a local CC session

```bash
tmux new-session -d -s dex_builder_main
tmux send-keys -t dex_builder_main "claude" Enter
```

Use `dex_builder_main` or `dex_product_main` to match the VPS session names —
this ensures replies route to the correct Discord channel.

### 5. Install the Stop hook

Create the hooks directory and copy the script:
```bash
mkdir -p ~/.claude/hooks
cp ~/send-to-discord.sh ~/.claude/hooks/send-to-discord.sh
chmod +x ~/.claude/hooks/send-to-discord.sh
```

Add to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/send-to-discord.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### 6. Verify end-to-end

From VPS:
```bash
# Test health check
curl http://100.74.199.102:8766/health

# Test message forwarding
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from services.local_bridge_client import forward_to_local
print(forward_to_local('hello from VPS', 'dex_builder_main'))
"
```

From a Discord channel, send a message. It should:
1. Hit VPS discord_bot.py
2. Forward to your local bridge
3. Inject into your local CC session
4. CC reply goes back to Discord via Stop hook

## Disabling the Bridge

Set `EOS_LOCAL_BRIDGE_ENABLED=0` in both .env files and restart os-discord:
```bash
docker restart os-discord
```

All messages will route to VPS tmux sessions as normal.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Messages not forwarding to local | `curl http://100.74.199.102:8766/health` from VPS |
| Replies not reaching Discord | `curl http://100.77.233.50:8765/health` from WSL |
| Wrong Discord channel | Ensure local tmux session name matches (dex_builder_main / dex_product_main) |
| Bridge server crashes | Check `python3 ~/local_bridge_server.py` for errors |
| Tailscale unreachable | `tailscale ping 100.77.233.50` from Windows |

## Security

- Port 8766 (local bridge) only exposed via Tailscale private network
- Port 8765 (VPS webhook) bound to 0.0.0.0 — Tailscale ACLs provide access control
- No secrets transmitted — only message text and session names
- VPS UFW is inactive; relies on Tailscale + cloud provider security groups
