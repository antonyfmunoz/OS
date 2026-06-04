# UMH Docker Infrastructure Truth

Phase: 14.6B-UMH | Status: DRAFT | Provenance: CODE_RESOLVED_CURRENT_TRUTH

---

## Docker Compose (docker-compose.yml, 156 lines)

### Network
- Name: eos_network (STALE -- should be umh_network)
- Driver: bridge

### Services

| Service | Container | Command | Port | Memory | CPU | Restart |
|---------|-----------|---------|------|--------|-----|---------|
| os-scraper | os-scraper | python3 services/overnight_scrape.py | none | 256M | 0.5 | no |
| os-webhook | os-webhook | python3 transports/api/webhooks/calendly_webhook.py | 8080 | 128M | 0.25 | always |
| os-discord | os-discord | python3 services/discord_bot.py | 8765 | 1G | 0.5 | on-failure |
| os-operator | os-operator | python3 -m uvicorn services.operator_api:app --host 0.0.0.0 --port 8091 | 8091 | 512M | 0.5 | unless-stopped |

### Common Configuration
All services share:
- Build: Dockerfile (python:3.11-slim base)
- Working dir: /app
- Volume: repo bind-mount (UMH_ROOT:/app)
- Env files: services/.env + infra/docker/umh.env
- Environment: PYTHONPATH=/app, UMH_ROOT=/app, TZ=America/Los_Angeles
- OLLAMA_BASE_URL=http://host.docker.internal:11434
- extra_hosts: host.docker.internal:host-gateway

### os-discord Special Config
- Additional volumes: logs, GWS configs (.config/gws, .config/@googleworkspace), .claude (ro), .claude.json (ro), tmux socket (/tmp/tmux-0)
- CC_SDK_TIMEOUT_SECONDS=180
- EOS_ROUTER_CLAUDE_CLI_ENABLED=1
- EOS_ROUTER_CLAUDE_CLI_SESSION=dex_main
- EOS_DISCORD_TEXT_TRANSPORT_ENABLED=1
- EOS_DISCORD_TEXT_REPLY_TTS_ENABLED=1
- All guild/channel/user wildcards (*)
- TMUX_TMPDIR=/tmp (binds to host socket)
- OTEL disabled

### os-operator Special Config
- Docker socket mounted read-only (/var/run/docker.sock)
- No ANTHROPIC_API_KEY passed
- PYTHONUNBUFFERED=1

## Dockerfile (18 lines)

Base: python:3.11-slim
Installs:
- System: git, curl, gcc, python3-dev, ffmpeg, espeak, tmux
- Node.js 20.x (for Claude Code CLI)
- PyTorch (CPU-only)
- Python deps from requirements.txt
- openai-whisper, yt-dlp
- Claude Code CLI (@anthropic-ai/claude-code via npm)
- Playwright chromium
- Custom patch: patch_pycord.py (fixes py-cord voice_client.py _MissingSentinel crash)

## Infrastructure Topology

### VPS (100.77.233.50 via Tailscale)
Role: Coordination brain -- lightweight, always-on
Services: Docker containers (os-discord, os-operator, os-webhook, os-scraper)
Additional: tmux sessions, Claude Code CLI, Ollama (gemma3:4b)

### Windows Beast (100.74.199.102 via Tailscale)
Role: GPU workhorse
Services: Docker Engine in WSL2 Ubuntu, Kokoro TTS at :8880
Additional: Full Trinity repos, large local models, electron-vite builds

### Tailscale Mesh
All devices on private network
Cockpit accessible via mesh
No ports exposed publicly

## Resource Budget (Total)
- Memory: 256M + 128M + 1G + 512M = 1,920M (1.88 GB)
- CPU: 0.5 + 0.25 + 0.5 + 0.5 = 1.75 cores

## Naming Debt
- Network: eos_network -> umh_network
- Multiple EOS_* env vars in os-discord config

## Gaps
1. No container health checks defined
2. No volume for persistent data (all ephemeral except bind mount)
3. os-scraper has restart: "no" -- manual restart required
4. No Docker secrets management (env files contain plaintext)
5. No container logging driver configured
6. No backup/restore for container state
7. chromium runs with --no-sandbox in computer-use Dockerfile (docker/computer-use/)
