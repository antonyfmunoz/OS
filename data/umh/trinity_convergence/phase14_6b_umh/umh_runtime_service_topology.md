# UMH Runtime Service Topology

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Docker Services

4 containerized services on VPS, connected via Docker bridge network. Repository bind-mounted into each container.

| Service | Container | Purpose | Memory Limit |
|---------|-----------|---------|-------------|
| Discord bot | os-discord | Primary UMH interface, signal processing, agent dispatch | 1G |
| Operator API | os-operator | Cockpit backend, organism endpoints, governance API | 512M |
| Webhook handler | os-webhook | Calendly webhook receiver | 128M |
| Scraper | os-scraper | Instagram monitoring | 256M |

### Container Configuration

- **Python version**: 3.11 (no 3.12+ syntax)
- **Bind mount**: `/opt/OS` mounted into containers (Python-only changes do not require rebuild)
- **Network**: Docker bridge network (inter-container communication via container names)
- **Restart policy**: unless-stopped

## Infrastructure Topology

| Node | Role | IP (Tailscale) |
|------|------|---------------|
| VPS | Coordination brain, always-on orchestrator | 100.77.233.50 |
| Beast | GPU workhorse, heavy compute, full repo mirror | 100.74.199.102 |

### Network

- **Tailscale** mesh connects all nodes on private network
- Nothing exposed publicly except through Tailscale or explicit tunnels
- VPS is lightweight orchestrator -- no large models, no heavy compute
- Beast handles GPU workloads, media processing, large model inference

## Service Dependencies

- All services depend on Neon Postgres for persistence
- os-discord is the primary runtime surface (most signals originate here)
- os-operator serves the cockpit web UI at universalmetaharness.tech
- os-webhook and os-scraper are event-driven (idle most of the time)
