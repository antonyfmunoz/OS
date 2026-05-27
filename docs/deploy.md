# UMH Deployment Guide

## Requirements

- Python 3.11+ (Docker containers run 3.11)
- Docker + Docker Compose
- Neon PostgreSQL (external, connection via DATABASE_URL)
- Tailscale (private network mesh)
- Linux VPS (tested on Ubuntu 22.04+)

## Architecture

UMH runs as Docker containers on a VPS orchestrated by docker-compose.
Database is Neon PostgreSQL (managed, external). Local services run
via systemd. The Windows Beast node connects over Tailscale.

## Services

| Container | Purpose | Port |
|-----------|---------|------|
| os-discord | Discord bot (DEX) | 8765 (WebSocket) |
| os-operator | Operator API + cockpit backend | 8091 |
| os-webhook | Calendly + Higgsfield webhooks | 8080 |
| os-scraper | Overnight data scraping (runs on schedule) | — |

### Non-Docker Services
| Service | Purpose | Port |
|---------|---------|------|
| umh-mesh | Node mesh WebSocket server (systemd) | 8094 |
| Ollama | Local LLM inference | 11434 |
| Caddy | HTTP reverse proxy | 80 |

## Environment Files

Two env files (both gitignored):

- `services/.env` — Discord tokens, API keys, org/user IDs
- `infra/docker/umh.env` — Database URLs, Notion keys, model API keys

**Required keys** (by name, never commit values):
- DATABASE_URL — Neon PostgreSQL connection string
- EOS_ORG_ID — organization UUID
- EOS_USER_ID — user UUID
- DISCORD_BOT_TOKEN — Discord bot token

## Deploy / Restart

```bash
# Restart a single service
docker restart os-discord

# Restart all services
docker compose up -d

# Rebuild after Dockerfile changes
docker compose build && docker compose up -d

# Restart mesh server
sudo systemctl restart umh-mesh
```

## Verification

```bash
# Check all containers
docker ps

# Check mesh
systemctl status umh-mesh

# Import smoke test
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); import substrate; print('ok')"

# Check Discord bot logs
docker logs os-discord --tail 20
```

## Crontab

30 cron jobs handle scheduled operations. See `crontab -l` for current state.
Staggered to prevent CPU pile-up on 2-core VPS.

## Monitoring

```bash
docker logs os-discord --tail 50 -f   # Discord bot
docker logs os-webhook --tail 50 -f   # Webhook handler
docker logs os-operator --tail 50 -f  # Operator API
journalctl -u umh-mesh -f             # Mesh server
```

## Troubleshooting

### Container crash-looping
```bash
docker logs <container> --tail 30    # Check error
docker compose config                # Validate compose
```

### Missing env vars
Containers need both `services/.env` and `infra/docker/umh.env`.
Check docker-compose.yml `env_file:` section for each service.

### Mesh backlog
Port 8094 may show high Recv-Q from internet port scanners.
If Windows node can't connect, check Tailscale status and mesh token config.
