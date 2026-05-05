# Docker — Creator-Level Best Practices
Source: https://docs.docker.com/
API Version: Docker Engine 28.2.2 / API v1.47
SDK Version: Docker Compose v5.1.0 (Compose spec 3.8)
Last Researched: 2026-04-04

---

# Tier 1 — Technical Mastery

## Authentication

### Docker Hub
Docker Hub auth is optional for public images. EOS builds all images locally — no registry auth needed.

```bash
# Login (if ever needed for private images)
docker login -u USERNAME
# Credentials stored: ~/.docker/config.json
# CI: use DOCKER_USERNAME + DOCKER_PASSWORD env vars
```

**Rate limits (unauthenticated):** 100 pulls / 6 hours per IP.
**Rate limits (authenticated):** 200 pulls / 6 hours per user.
**Rate limits (paid):** 5,000 pulls / day.

### Docker socket
The Docker daemon socket (`/var/run/docker.sock`) is the primary auth boundary.
Anyone with access to the socket has root-equivalent access to the host.
Never mount the socket into untrusted containers. If needed, use read-only: `:ro`.

### Registry auth config
```json
// ~/.docker/config.json
{
  "auths": {
    "https://index.docker.io/v1/": {
      "auth": "base64(username:password)"
    }
  },
  "credHelpers": {
    "gcr.io": "gcloud"
  }
}
```

## Core Operations with Exact Signatures

### Container lifecycle
```bash
# Create (does not start)
docker create [OPTIONS] IMAGE [COMMAND] [ARG...]
  --name NAME          # assign name
  --restart POLICY     # no|always|on-failure[:max]|unless-stopped
  -e KEY=VALUE         # env var
  -v HOST:CONTAINER    # bind mount
  -p HOST:CONTAINER    # port map
  --network NET        # attach to network
  --shm-size SIZE      # /dev/shm size (default 64MB)

# Start
docker start [OPTIONS] CONTAINER [CONTAINER...]
  -a, --attach         # attach STDOUT/STDERR
  -i, --interactive    # attach STDIN

# Stop (sends SIGTERM, then SIGKILL after grace period)
docker stop [OPTIONS] CONTAINER [CONTAINER...]
  -t, --time INT       # seconds before SIGKILL (default 10)

# Restart (stop + start)
docker restart [OPTIONS] CONTAINER [CONTAINER...]
  -t, --time INT       # seconds before SIGKILL (default 10)

# Kill (sends signal immediately, no grace period)
docker kill [OPTIONS] CONTAINER [CONTAINER...]
  -s, --signal SIGNAL  # signal to send (default SIGKILL)

# Remove
docker rm [OPTIONS] CONTAINER [CONTAINER...]
  -f, --force          # force remove running container (SIGKILL)
  -v, --volumes        # remove anonymous volumes

# Wait (block until stop, print exit code)
docker wait CONTAINER [CONTAINER...]
```

### Exit codes
| Code | Meaning |
|------|---------|
| 0 | Clean exit |
| 1 | Application error |
| 125 | Docker daemon error (e.g., bad flag) |
| 126 | Command cannot be invoked (permission) |
| 127 | Command not found |
| 137 | SIGKILL (128 + 9) — OOM or `docker kill` |
| 143 | SIGTERM (128 + 15) — `docker stop` |
| 255 | Exit status out of range |

### Image operations
```bash
# Build
docker build [OPTIONS] PATH
  --no-cache           # ignore layer cache
  --pull               # always pull newer base image
  --build-arg K=V      # build-time variable
  --target STAGE       # multi-stage target
  --platform P         # e.g., linux/amd64
  -t NAME:TAG          # tag the image
  -f DOCKERFILE        # specify Dockerfile path

# List
docker images [OPTIONS]
  --filter dangling=true  # untagged images only
  --format "table {{.Repository}}\t{{.Size}}"

# Remove
docker rmi IMAGE [IMAGE...]
  -f, --force

# Prune
docker image prune -f              # dangling only
docker image prune -a -f           # all unused
docker system prune -f             # containers + networks + dangling images
docker system prune -a -f          # + all unused images
docker builder prune -f            # build cache
```

### Compose operations
```bash
# Start services (detached)
docker compose up -d [SERVICE...]
  --build              # rebuild before starting
  --force-recreate     # recreate even if config unchanged
  --no-deps            # don't start dependencies

# Stop and remove
docker compose down [OPTIONS]
  -v, --volumes        # remove named volumes
  --rmi all            # remove all images
  --rmi local          # remove only locally built images

# Restart (stop + start, keeps containers)
docker compose restart [SERVICE...]
  -t, --timeout INT    # SIGTERM grace period (default 10)

# Rebuild
docker compose build [SERVICE...]
  --no-cache           # full rebuild
  --pull               # pull newer base images

# Logs
docker compose logs [SERVICE...]
  --tail N             # last N lines
  --since TIME         # e.g., 5m, 2h, 2026-04-04T00:00:00
  -f, --follow         # stream

# Status
docker compose ps [OPTIONS]
  -a, --all            # include stopped
  --format json        # JSON output
```

### Exec into container
```bash
docker exec [OPTIONS] CONTAINER COMMAND [ARG...]
  -it                  # interactive TTY
  -e KEY=VALUE         # env var for this exec
  -w WORKDIR           # working directory
  --user USER          # run as user
```

### Inspect
```bash
docker inspect CONTAINER --format '{{.State.Status}}'
docker inspect CONTAINER --format '{{.State.ExitCode}}'
docker inspect CONTAINER --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{end}}'
docker inspect CONTAINER --format '{{.HostConfig.RestartPolicy.Name}}'
```

### Stats
```bash
docker stats --no-stream              # one-shot CPU/memory
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
docker system df                      # disk usage by images, containers, volumes, cache
```

## Pagination Patterns

N/A — Docker CLI and API return complete result sets. No cursor or offset-based pagination.

The `docker events` stream is continuous (not paginated). Filter with `--since` and `--until`:
```bash
docker events --since 1h --until 0m --filter container=os-discord
```

For the Docker Engine API (REST), `/containers/json` returns all containers. `/events` is a long-poll stream.

## Rate Limits

### Docker Hub (image pulls)
| Tier | Limit | Window |
|------|-------|--------|
| Anonymous | 100 pulls | 6 hours per IP |
| Free (authenticated) | 200 pulls | 6 hours per user |
| Pro / Team / Business | 5,000 pulls | 24 hours per user |

Rate limit headers on pull responses:
```
RateLimit-Limit: 100;w=21600
RateLimit-Remaining: 97;w=21600
```

### Local Docker daemon
No rate limits. The daemon processes requests as fast as resources allow.
Compose `up` with many services can saturate disk I/O during parallel builds.

### Container restart throttling
Docker applies exponential backoff to restart loops:
100ms → 200ms → 400ms → ... up to 60s cap.
Reset to 100ms after container runs for 10+ seconds.

## Error Codes and Recovery

### Docker daemon errors
| Scenario | Behavior | Recovery |
|----------|----------|----------|
| Daemon not running | `Cannot connect to the Docker daemon` | `systemctl start docker` |
| Permission denied | `Got permission denied while trying to connect` | Add user to `docker` group or use `sudo` |
| Port conflict | `bind: address already in use` | `lsof -i :PORT` → kill or change port |
| Name conflict | `container name "/os-discord" is already in use` | `docker rm os-discord` first |
| OOM kill | Container exits with code 137, `OOMKilled: true` in inspect | Increase `mem_limit` or reduce workload |
| Disk full | `no space left on device` | `docker system prune -a -f` |
| Image not found | `manifest unknown` or `pull access denied` | Check image name/tag, check auth |
| Build cache issue | Stale layers cause unexpected behavior | `docker build --no-cache` |

### Compose-specific errors
| Scenario | Behavior | Recovery |
|----------|----------|----------|
| Invalid YAML | `yaml: line N: ...` | Fix syntax at line N |
| Orphan containers | `Found orphan containers` warning | `docker compose down --remove-orphans` |
| env_file missing | `Couldn't find env file` | Create file or use `required: false` (Compose 2.24+) |
| Network conflict | `network X already exists` | `docker network rm X` |

### Signal handling
```
docker stop → SIGTERM → 10s default → SIGKILL
docker kill → SIGKILL (immediate)
```
**PID 1 trap:** If Dockerfile uses shell form (`CMD python3 app.py`), `/bin/sh` is PID 1 and does NOT forward SIGTERM. Use exec form (`CMD ["python3", "app.py"]`) or `exec` prefix.

EOS Dockerfile uses `command:` in compose which runs via exec form by default.

## SDK Idioms

### Docker SDK for Python
```python
import docker
client = docker.from_env()  # reads DOCKER_HOST env

# List containers
containers = client.containers.list()  # running only
containers = client.containers.list(all=True)  # all

# Run command in container
container = client.containers.get("os-discord")
exit_code, output = container.exec_run("python3 -c 'import eos_ai'")
print(output.decode())

# Get logs
logs = container.logs(tail=10, timestamps=True)

# Restart
container.restart(timeout=10)

# Build image
image, logs = client.images.build(path="/opt/OS", nocache=True)
```

EOS does not use the Python SDK — all Docker operations are via CLI in deployment scripts and Claude Code sessions. The SDK is documented here for completeness.

### Docker Compose Python library
```python
# python-on-whales (modern alternative to docker-compose Python)
from python_on_whales import DockerClient
docker = DockerClient(compose_files=["./docker-compose.yml"])
docker.compose.up(detach=True, services=["os-discord"])
docker.compose.restart(services=["os-discord"])
```

### CLI composition patterns (what EOS actually uses)
```bash
# Chain: verify → restart → wait → check
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); import eos_ai; print('ok')" && \
  docker restart os-discord && \
  sleep 15 && \
  docker logs os-discord --tail 10

# Parallel restart with staggered timing
for svc in os-discord os-bot os-webhook; do
  docker restart $svc
  sleep 15
  docker logs $svc --tail 5
done
```

## Anti-Patterns

1. **Shell form CMD without exec** — `CMD python3 app.py` wraps in `/bin/sh -c`, PID 1 doesn't forward signals. Use `CMD ["python3", "app.py"]` or `command: python3 app.py` in compose (which uses exec form).

2. **`apt-get update` in separate RUN** — Creates a stale package index layer. Always combine:
   ```dockerfile
   RUN apt-get update && apt-get install -y pkg && rm -rf /var/lib/apt/lists/*
   ```

3. **COPY before pip install** — Invalidates pip cache on any code change. Copy requirements first, install, then copy code:
   ```dockerfile
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   ```

4. **`docker compose restart` for config changes** — Restart reuses the existing container. Config changes (env vars, ports, volumes) require `down` + `up`, or `up -d` (which recreates changed services).

5. **Mounting secrets as env vars in compose.yml** — Visible in `docker inspect`. Use `env_file` pointing to a gitignored file, or Docker secrets for Swarm.

6. **`restart: always` for batch jobs** — The container restarts endlessly after completing. Use `restart: "no"` for one-shot tasks (EOS: os-scraper uses this correctly).

7. **Running as root without necessity** — Container processes run as root by default. For production, add `USER` instruction. EOS runs as root because the VPS itself runs as root and bind mounts require matching permissions.

8. **Ignoring build context size** — Without `.dockerignore`, the entire directory is sent to the daemon. EOS sends all of `/opt/OS` (~1GB+). Add `.dockerignore` for `.git`, `logs/`, `node_modules/`.

9. **`docker system prune -a` in production** — Removes ALL unused images, including base images you'll need on next build. Use `docker image prune` (dangling only) or `docker builder prune` (cache only) for safer cleanup.

10. **Restarting all services at once** — Causes thundering herd on shared resources (Neon DB connections, Ollama). Restart one at a time with 15s gap.

## Data Model

### Object hierarchy
```
Docker daemon
├── Images (immutable, layered filesystem)
│   ├── Layers (content-addressable, shared across images)
│   └── Tags (mutable pointers to image digests)
├── Containers (running or stopped instances of images)
│   ├── Writable layer (ephemeral, lost on removal)
│   ├── Mounts (bind or volume)
│   └── Network interfaces
├── Volumes (persistent, Docker-managed storage)
├── Networks (bridge, host, none, overlay)
└── Build cache (layer cache for builds)
```

### Key relationships
- **Image → Container**: one-to-many. Multiple containers from one image.
- **Container → Volume**: many-to-many. Volumes outlive containers.
- **Container → Network**: many-to-many. A container can be on multiple networks.
- **Compose service → Container**: one-to-one (scale=1) or one-to-many (scale>1).
- **Compose project → Services**: one-to-many. Project name prefixes container names.

### Immutable vs mutable
| Object | Immutable | Persists removal |
|--------|-----------|-----------------|
| Image layer | Yes | Yes (shared) |
| Image tag | No (re-taggable) | No |
| Container writable layer | No | No |
| Named volume | No | Yes |
| Bind mount | No | Yes (host filesystem) |
| Network | N/A | No (removed with `down`) |

## Webhooks and Events

### Docker events stream
```bash
# All events
docker events

# Filtered events
docker events --filter container=os-discord --filter event=start
docker events --filter event=die --since 1h

# JSON output
docker events --format '{{json .}}'
```

Event types: `attach`, `commit`, `copy`, `create`, `destroy`, `detach`, `die`, `exec_create`, `exec_detach`, `exec_die`, `exec_start`, `export`, `health_status`, `kill`, `oom`, `pause`, `rename`, `resize`, `restart`, `start`, `stop`, `top`, `unpause`, `update`.

### Docker Engine API (REST)
```bash
# Stream events via API
curl --unix-socket /var/run/docker.sock \
  'http://localhost/v1.47/events?filters={"container":["os-discord"]}'
```

### Healthcheck as event source
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import eos_ai"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```
Generates `health_status` events: `health_status: healthy` or `health_status: unhealthy`.
EOS does not currently use healthchecks — services validate via log output.

## Limits

| Resource | Limit |
|----------|-------|
| Container name length | 1-128 chars (`[a-zA-Z0-9_.-]`) |
| Image tag length | 1-128 chars |
| Env var count | No hard limit (practical: thousands) |
| Port range | 1-65535 |
| Volume name length | No hard limit (must not be `.` or `..`) |
| Network name length | 1-64 chars |
| Compose services | No hard limit |
| Build layers | 127 max (default, configurable) |
| Build context | Sent to daemon in full — no size limit but affects speed |
| shm_size | Default 64MB, configurable per container |
| PID limit | Default unlimited, configurable via `--pids-limit` |
| File descriptors | Default 1048576 (ulimit in daemon.json) |
| Log file size | Default unlimited — use `max-size` + `max-file` log opts |

### EOS-specific resource usage
```
os-discord:  ~200MB RAM, minimal CPU
os-bot:      ~150MB RAM, minimal CPU
os-monitor:  ~700MB RAM (Chromium), burst CPU during page loads
os-webhook:  ~100MB RAM, minimal CPU
os-scraper:  ~300MB RAM (batch, not always running)
Total:       ~1.5GB steady state, 2-4GB with spikes
```

## Cost Model

Docker Engine is **free and open source** (Apache 2.0 license).

**Docker Desktop** (commercial):
- Free for personal use, education, small businesses (<250 employees, <$10M revenue)
- Pro: $5/month, Team: $9/user/month, Business: $24/user/month
- EOS: Not applicable — runs on Linux VPS, no Desktop needed.

**Docker Hub:**
- Free: 1 private repo, 100 pulls/6h anonymous
- Pro: unlimited private repos, 5000 pulls/day
- EOS: Not used — all images built locally.

**Real costs for EOS:**
- VPS RAM consumed by containers (~2-4GB)
- Disk for images, layers, build cache (~3-5GB)
- CPU time during builds and Chromium rendering

## Version Pinning

### Current versions (EOS VPS)
- Docker Engine: **28.2.2**
- Docker Compose: **v5.1.0**
- BuildKit: **v0.25.2** (bundled with Engine 28)
- Compose file format: **3.8**

### Base image pinning
```dockerfile
# EOS current (tag-pinned):
FROM python:3.11-slim

# Better (digest-pinned for supply chain security):
FROM python:3.11-slim@sha256:abc123...
```

Tag-pinned is acceptable for EOS (single-developer, not a supply-chain target).
Digest-pinned is recommended for production SaaS deployments.

### Compose version
Compose V2 (the `docker compose` plugin) replaced standalone `docker-compose` (V1).
V1 was removed in Docker Engine 24+. EOS uses V2 exclusively.

The `version: '3.8'` key in compose.yml is informational only in Compose V2 — it does not restrict features. Compose V2 supports all spec features regardless of the version key.

### Deprecation warnings
- `docker-compose` (V1 binary): removed, use `docker compose`
- `version` key in compose.yml: deprecated in Compose V2, ignored
- `links`: deprecated, use networks instead
- `--link` flag: deprecated

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Docker's fundamental design bet: **process isolation without virtualization overhead.** Containers share the host kernel (unlike VMs) but get their own filesystem, network, and PID namespace. This means:

1. **Startup in milliseconds, not minutes.** No OS boot — just process start. This is why `docker restart` is viable for deploys (EOS restarts in ~2-5s).

2. **Layers as content-addressable cache.** Each Dockerfile instruction creates a layer identified by its content hash. Unchanged layers are reused across builds AND across images. This is why layer ordering matters — changing an early layer invalidates all subsequent layers.

3. **Ephemeral by design.** Containers are meant to be disposable. State goes in volumes or external stores (Neon for EOS). This enables the "cattle not pets" pattern — kill and recreate rather than debug in-place.

4. **Compose as declarative infrastructure.** The compose file describes desired state, not steps. `docker compose up -d` converges toward that state — creating, recreating, or leaving containers as needed. This is infrastructure-as-code without Terraform.

5. **Bind mounts as development escape hatch.** The immutability of images is intentional for production. Bind mounts exist specifically so developers can iterate without rebuilding. EOS exploits this — the entire `/opt/OS` is bind-mounted, making Python file changes instant.

## Problem-Solution Map and Hidden Capabilities

### "Container keeps restarting in a loop"
Check exit code: `docker inspect os-discord --format '{{.State.ExitCode}}'`
- 137 = OOM kill → increase memory or reduce workload
- 1 = application error → `docker logs os-discord --tail 50`
- Check restart backoff: Docker backs off 100ms → 200ms → ... → 60s cap

### "Changes to .env not picked up"
`docker restart` does NOT re-read env files. Must `docker compose up -d` (recreates container with new env). Or `docker compose down && docker compose up -d`.

### "Build is slow despite no code changes"
Build context is too large. Create `.dockerignore`:
```
.git
logs/
*.pyc
__pycache__
node_modules/
```

### "Container can't reach Ollama on host"
Verify `extra_hosts` mapping in compose.yml. Inside container:
```bash
docker exec os-discord curl -s http://host.docker.internal:11434/api/tags
```
If DNS fails, use host gateway IP directly: `172.17.0.1:11434`.

### Hidden capabilities
- **`docker compose cp`** — copy files to/from running containers without exec
- **`docker compose watch`** (Compose 2.22+) — auto-rebuild/restart on file changes
- **`docker compose alpha viz`** — visualize service dependencies as a graph
- **`docker diff CONTAINER`** — show filesystem changes in writable layer
- **`docker commit CONTAINER IMAGE`** — snapshot running container as new image (debugging only)
- **`docker compose config`** — validate and dump resolved compose file (shows env substitution results)

## Operational Behavior and Edge Cases

### Signal propagation
Python in Docker: `CMD ["python3", "app.py"]` — Python receives SIGTERM directly as PID 1. Python's default SIGTERM handler raises `SystemExit`. For asyncio apps, register a signal handler:
```python
import signal, asyncio
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(shutdown()))
```

### OOM behavior
Docker default: no memory limit. The kernel OOM killer picks a victim based on `oom_score_adj`. Containers without limits can kill host processes (including other containers). Set `mem_limit` in production.

EOS observed OOM: os-monitor (Chromium) + qwen2.5:3b → 137 exit codes. Fixed by switching to qwen2.5:0.5b.

### Volume mount timing
Bind mounts are established at container creation, not start. If the host directory doesn't exist at `docker create` / `docker compose up`, Docker creates it as root-owned empty directory. This can cause confusing permission issues.

### Network DNS resolution
Containers on the same bridge network resolve each other by **service name** (not container name). `os-discord` can reach `os-webhook` as `http://os-webhook:8080` — but only because the compose service name matches the container name in EOS.

### Compose recreate behavior
`docker compose up -d` compares running state to compose file. If config changed (env, volumes, ports), it stops and recreates the container. If unchanged, it does nothing. This is idempotent — safe to run repeatedly.

### Log rotation
Default logging driver (`json-file`) has NO rotation. Logs grow unbounded until disk is full. Configure in daemon.json:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```
Or per-service in compose.yml under `logging:`.

## Ecosystem Position and Composition

### Docker in the EOS stack
```
Developer (Claude Code) → docker restart → Container picks up bind-mounted code changes
                       → docker compose build → Rebuild when Dockerfile/requirements change
                       → docker logs → Debug runtime issues
                       → docker exec → Run one-off commands in container context
```

Docker is the **deployment layer** — it wraps Python services in isolated processes with managed networking and restart policies. It does NOT handle:
- Orchestration across hosts (use Kubernetes/Swarm for that)
- Secrets management (EOS uses .env files, not Docker secrets)
- Service discovery (EOS services know each other by convention, not discovery)

### Natural complements
- **Ollama** — runs on host, containers reach via `host.docker.internal`
- **Neon** — external DB, containers connect via `DATABASE_URL` env var
- **Tailscale** — VPN runs on host, containers access private network via host networking
- **GitHub** — code pushed to repo, pulled to VPS, containers pick up via bind mount

### Anti-complement
- **Docker Swarm** — overkill for single-host EOS. Adds complexity without benefit.
- **Kubernetes** — massively overkill. EOS is 5 services on one VPS.
- **Docker-in-Docker (DinD)** — never needed for EOS. Adds security risk.

## Trajectory and Evolution

### Recent (Engine 28, 2025-2026)
- BuildKit v0.25 default — faster builds, better caching
- `docker compose watch` — file-sync and auto-rebuild
- `docker init` — generates Dockerfile + compose for common frameworks
- `docker scout` — vulnerability scanning built into CLI
- Compose V2 fully replaced V1 (V1 removed)

### Direction
- **BuildKit as platform** — more build steps, better caching, remote builders
- **Containerd integration deeper** — image store backed by containerd (not legacy)
- **Security-first** — scout, SBOM generation, provenance attestations
- **Developer experience** — compose watch, init, debug commands

### Deprecation risks for EOS
- `version` key in compose.yml already deprecated (harmless, just remove it)
- Compose V1 syntax quirks may not work in V2 (EOS compose file is V2-compatible)
- No imminent risk to current EOS setup

## Conceptual Model and Solution Recipes

### Mental model
Think of Docker as **three layers**:
1. **Build time** — Dockerfile → image. Immutable. Cached. Shareable.
2. **Run time** — image + config → container. Ephemeral. Configurable.
3. **Compose time** — compose.yml → multi-container app. Declarative. Idempotent.

### Recipe: Deploy Python code change (EOS standard)
```bash
# 1. Verify imports locally
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); import eos_ai; print('ok')"

# 2. Restart container (bind mount = instant code pickup)
docker restart os-discord

# 3. Wait for startup
sleep 15

# 4. Verify
docker logs os-discord --tail 10
# Look for: "online", "connected", "ready"
# Watch for: Traceback, ImportError, Error
```

### Recipe: Add new Python dependency
```bash
# 1. Add to requirements.txt
echo "new-package==1.2.3" >> services/requirements.txt

# 2. Rebuild image (requirements layer invalidated)
docker compose build --no-cache os-discord

# 3. Recreate container with new image
docker compose up -d os-discord

# 4. Wait longer (pip install takes time)
sleep 30

# 5. Verify
docker logs os-discord --tail 10
```

### Recipe: Debug a crashing container
```bash
# 1. Check exit code
docker inspect os-discord --format '{{.State.ExitCode}} {{.State.OOMKilled}}'

# 2. Check logs (look backwards from crash)
docker logs os-discord --tail 100

# 3. If crash-looping, run interactively
docker compose run --rm os-discord bash
# Inside container:
python3 -c "import eos_ai"
python3 services/discord_bot.py

# 4. Check resource usage
docker stats --no-stream
```

### Recipe: Full rebuild (nuclear option)
```bash
docker compose down
docker system prune -f          # remove stopped containers + cache
docker compose build --no-cache # full rebuild
docker compose up -d            # fresh start
sleep 30
docker compose ps               # verify all running
```

### Recipe: Check what's eating disk
```bash
docker system df                # overview
docker system df -v             # detailed breakdown
docker builder prune -f         # clear build cache
docker image prune -f           # dangling images
```

## Industry Expert and Cutting-Edge Usage

### Pattern: Bind-mount development, image-based production
EOS uses bind mounts for all services — this is the development pattern. For production SaaS deployment (Phase 2), switch to:
1. Multi-stage build: build stage installs deps, production stage copies only needed files
2. No bind mounts — code baked into image
3. Image pushed to registry, pulled on deploy servers
4. `docker compose pull && docker compose up -d` for deploys

### Pattern: Sidecar containers
Run supporting processes as separate containers alongside the main app:
- Log shipper sidecar (fluentd/logstash) that reads from shared volume
- Metrics exporter (prometheus node-exporter) for monitoring
- EOS already does this implicitly — os-webhook is a sidecar to the main os-discord service

### Pattern: Init containers
Run setup tasks before main service starts:
```yaml
services:
  db-migrate:
    build: .
    command: python3 migrate.py
    restart: "no"
  app:
    depends_on:
      db-migrate:
        condition: service_completed_successfully
```

### Pattern: Health-gated deploys
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import eos_ai; print('ok')"]
  interval: 10s
  retries: 3
  start_period: 30s
depends_on:
  db:
    condition: service_healthy
```
Container won't accept traffic until health check passes. Dependent services wait for healthy state.

### Pattern: Docker Compose profiles for environment switching
```yaml
services:
  os-discord:
    profiles: ["prod", "dev"]
  os-debug:
    profiles: ["dev"]
    command: python3 -m pdb services/discord_bot.py
```
`docker compose --profile prod up -d` — only production services.
`docker compose --profile dev up -d` — includes debug tools.

---

## EOS Usage Patterns

### Service map
| Service | Container | Entry | Restart | Network |
|---------|-----------|-------|---------|---------|
| os-bot | os-bot | `python3 services/telegram_control.py` | always | eos_network |
| os-monitor | os-monitor | `python3 -u services/dm_monitor.py` | always | eos_network |
| os-scraper | os-scraper | `python3 services/overnight_scrape.py` | no | eos_network |
| os-webhook | os-webhook | `python3 services/calendly_webhook.py` | always | eos_network |
| os-discord | os-discord | `python3 services/discord_bot.py` | on-failure | eos_network |

### Bind mount architecture
All services mount `/opt/OS:/app`. This means:
- Python file edits on host are instantly available in all containers
- No rebuild needed for code changes
- All services share the same codebase view
- `PYTHONPATH=/app` makes `import eos_ai` work

### Environment variable flow
```
services/.env    → bot tokens, API keys, chat IDs
eos_ai/.env      → Anthropic key, Neon URL, org config
compose environment: block → PYTHONPATH, TZ, OLLAMA_BASE_URL overrides
```
Precedence: `environment:` > `env_file` > Dockerfile `ENV`.

### Special configurations
- **os-monitor**: `shm_size: '2gb'` for Chromium, `PYTHONUNBUFFERED=1` for log streaming
- **os-discord**: `restart: on-failure` (clean shutdown stays stopped), mounts `.claude` and GWS config
- **os-scraper**: `restart: "no"` (one-shot batch job)
- **All services**: `extra_hosts: host.docker.internal:host-gateway` for Ollama access

## Gotchas

### Stale container after compose.yml change
Changed `environment:` in compose.yml but ran `docker restart` instead of `docker compose up -d`. Container kept old env vars. `restart` reuses the existing container definition. `up -d` detects changes and recreates.

### os-monitor Chromium OOM
Chromium needs ~700MB RAM. Combined with other services, the VPS was hitting swap. Added 90-second startup delay (`MONITOR_STARTUP_DELAY=90`) to stagger container initialization and prevent overlapping memory spikes.

### docker compose vs docker restart naming
`docker compose restart os-discord` uses the **service name** from compose.yml.
`docker restart os-discord` uses the **container name** set via `container_name:`.
In EOS they match — but this is by convention, not guarantee. Prefer `docker restart` for directness.

### Build cache invalidation cascade
Adding a system package to the `apt-get install` line in Dockerfile invalidates that layer AND the entire pip install layer below it. A 30-second code deploy becomes a 5-minute full rebuild. Keep system packages stable.

### Log overflow on os-discord
Without log rotation, os-discord generates ~50MB/day of logs. After a month, 1.5GB. Not configured yet — should add `logging: max-size: 10m, max-file: 3` to compose.yml.
