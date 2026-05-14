---
name: docker
description: "Use when building, deploying, restarting, debugging, or configuring any containerized EOS service."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.docker.com/"
last_researched: "2026-04-03"
instantiated_from: templates/tools/_template/
api_version: "Docker Engine 27.x / API v1.47"
sdk_version: "Docker Compose v2.32+"
speed_category: "stable"
trigger: both
effort: low
context: fork
---

# Tool: Docker + Docker Compose

## What This Tool Does

Docker packages applications into isolated containers that share the host kernel but have their own filesystem, networking, and process space. Docker Compose orchestrates multi-container applications from a single YAML file, managing builds, networking, volumes, environment variables, and service dependencies declaratively.

Core capabilities:
- **Image building** — Dockerfile defines reproducible build steps. Layers are cached. Each instruction creates a layer.
- **Container lifecycle** — create, start, stop, restart, remove. Containers are ephemeral by default.
- **Volume mounts** — bind mounts (host path into container) and named volumes (Docker-managed). Bind mounts are live — file changes on host appear instantly in container.
- **Networking** — bridge networks isolate services. Containers on the same bridge resolve each other by service name.
- **Compose orchestration** — `docker-compose.yml` declares all services, their images, volumes, networks, env, ports, and restart policies as code.
- **Resource management** — memory limits, CPU shares, shm_size, OOM behavior.

## EOS Integration

EOS runs 5 services from `/opt/OS/docker-compose.yml`:

| Service | Container Name | Entrypoint | Restart Policy |
|---------|---------------|------------|----------------|
| os-bot | os-bot | `python3 services/telegram_control.py` | always |
| os-monitor | os-monitor | `python3 -u services/dm_monitor.py` | always |
| os-scraper | os-scraper | `python3 services/overnight_scrape.py` | no |
| os-webhook | os-webhook | `python3 services/calendly_webhook.py` | always |
| os-discord | os-discord | `python3 services/discord_bot.py` | on-failure |

**Architecture pattern:** All services share a single Dockerfile (`python:3.11-slim` base). The entire `/opt/OS` directory is bind-mounted to `/app` inside each container. This means Python file changes are live immediately — no rebuild needed. Only Dockerfile or `requirements.txt` changes require a rebuild.

**Networking:** All services are on `eos_network` (bridge). Ollama runs on the host and is accessed via `host.docker.internal:11434` (mapped through `extra_hosts`). The webhook service exposes port 8080.

**Environment:** Each service loads env vars from `services/.env` (some also from `eos_ai/.env`). `PYTHONPATH=/app` and `TZ=America/Los_Angeles` are set on all services. `ANTHROPIC_API_KEY` and `OLLAMA_BASE_URL` are injected via environment block.

**Agents that use Docker:** Developer Agent (deploy, restart, debug), EA Agent (service health checks), System Health Monitor (container status).

## Authentication

Docker Hub authentication is not required for EOS — all images are built locally from the project Dockerfile. No private registry is used.

If Docker Hub auth is ever needed:
```bash
docker login -u USERNAME
# Credentials stored in ~/.docker/config.json
# For CI: use DOCKER_USERNAME and DOCKER_PASSWORD env vars
```

Docker Hub rate limits for unauthenticated pulls: 100 pulls/6 hours per IP. Authenticated: 200 pulls/6 hours. EOS builds locally so this rarely applies.

## Quick Reference

### Deploy decision tree (memorize this)

**Python file changed (no Dockerfile/requirements change):**
```bash
docker restart os-discord  # or os-bot, os-monitor, os-webhook
sleep 15
docker logs os-discord --tail 10
```

**requirements.txt changed:**
```bash
docker compose build --no-cache os-discord
docker compose up -d os-discord
sleep 20
docker logs os-discord --tail 10
```

**Dockerfile changed:**
```bash
docker compose build --no-cache
docker compose up -d
sleep 30
docker logs os-discord --tail 10
```

### Essential commands
```bash
# Status
docker ps                              # running containers
docker ps -a                           # all containers (including stopped)
docker stats --no-stream               # CPU/memory snapshot
docker system df                       # disk usage

# Logs
docker logs os-discord --tail 50       # last 50 lines
docker logs os-discord --since 5m      # last 5 minutes
docker logs os-discord -f              # follow (stream)

# Lifecycle
docker restart os-bot                  # restart single service
docker stop os-monitor                 # stop single service
docker start os-monitor                # start stopped service

# Debugging
docker exec -it os-discord bash        # shell into running container
docker exec os-discord python3 -c "import eos_ai; print('ok')"
docker inspect os-discord --format '{{.State.Status}}'

# Cleanup
docker system prune -f                 # remove stopped containers, unused networks, dangling images
docker image prune -f                  # remove dangling images only
docker builder prune -f                # clear build cache

# Compose
docker compose up -d                   # start all services detached
docker compose down                    # stop and remove all
docker compose ps                      # compose-managed services
docker compose logs os-bot --tail 20   # logs via compose
```

### Pre-deploy verification (always run first)
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import eos_ai
print('imports: clean')
" 2>&1
```

### Post-deploy verification
```bash
docker logs [container_name] --tail 10
# Look for: "online", "started", "ready", "connected"
# Watch for: Error, Traceback, ImportError, ModuleNotFoundError
```

## Conceptual Model

```
Dockerfile ──build──> Image ──run──> Container
                        │                │
                  (immutable layers)  (ephemeral process)
                        │                │
                  cached per layer    bind-mount = live files
                                     volume = persisted data

docker-compose.yml
  ├── services (os-bot, os-discord, ...)
  │     ├── build context + dockerfile
  │     ├── volumes (bind mounts)
  │     ├── networks (eos_network)
  │     ├── environment (env vars)
  │     ├── ports (host:container)
  │     └── restart policy
  └── networks (eos_network: bridge)
```

**Image** = frozen filesystem snapshot built from Dockerfile. Immutable. Cached by layer.
**Container** = running (or stopped) instance of an image. Ephemeral. State lost on removal unless persisted via volumes.
**Bind mount** = host directory mapped into container. Changes are bidirectional and immediate. EOS uses this for `/opt/OS:/app`.
**Named volume** = Docker-managed persistent storage. Survives container removal.
**Bridge network** = isolated L2 network. Containers resolve each other by service name. `eos_network` connects all EOS services.
**extra_hosts** = injects entries into container `/etc/hosts`. EOS uses `host.docker.internal:host-gateway` to reach Ollama on the host.

## Gotchas

**Never restart all services simultaneously.** Services have interdependencies and staggered startup. Restart one at a time with 15s wait between.

**`docker restart` vs `docker compose restart`.** Both work but `docker restart os-discord` uses the container name directly and is more reliable. `docker compose restart os-discord` uses the service name from compose.yml. Prefer `docker restart`.

**Ollama OOM with qwen2.5:3b.** The 3b model needs 1.9 GiB and Docker services consume 4+ GiB. Switched to qwen2.5:0.5b. If upgrading Ollama models, check `docker stats --no-stream` first.

**shm_size matters for Playwright.** os-monitor sets `shm_size: '2gb'` because Chromium uses shared memory for rendering. Default is 64MB and Chromium will crash with `SIGBUS` on complex pages.

**PYTHONUNBUFFERED=1 for streaming logs.** os-monitor and os-discord set this. Without it, Python buffers stdout and `docker logs` shows nothing until the buffer flushes (which can be minutes).

**Build cache invalidation is top-down.** If any layer changes, all subsequent layers rebuild. The EOS Dockerfile installs system packages first, then pip packages, then copies code. If you add a system package, the entire pip install re-runs. Order matters.

**`restart: always` vs `on-failure`.** `always` restarts even on clean exit (code 0). `on-failure` only restarts on non-zero exit. os-discord uses `on-failure` because a clean shutdown should stay stopped. os-scraper uses `"no"` because it is a one-shot batch job.

**Bind mount permissions.** Files created inside the container are owned by root (container runs as root). This is fine for EOS since the VPS runs as root, but be aware if switching to non-root containers.

**After Ollama model change, restart services.** The model name is loaded at service startup. Changing the Ollama model on the host does not affect running containers until they restart.

**env_file vs environment block.** `env_file` loads from a file. `environment` sets inline. If both define the same var, `environment` wins. EOS uses both — secrets in `env_file`, overrides in `environment`.

See references/best_practices.md for full technical reference and anti-patterns.
