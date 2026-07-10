---
type: codewiki-dir
dir: infra
---

# `infra/` — declarative infrastructure: device/service registries, cron, systemd, LiveKit, 1Password secret injection

**19 files · 60,510 bytes · [Full file inventory](../inventory/infra.md)**

## Purpose
`infra/` is the declarative source of truth for *how UMH is deployed and wired across
devices* — not runtime code, but the JSON registries, systemd units, cron schedule, and
secret-injection scripts that describe the organism's physical topology. It answers
"which device owns which role," "which service owns which state domain," "what runs on a
schedule," and "how do secrets reach a process without ever touching disk." Five JSON
registries encode the mesh (`device_registry.json`, `umh_node_registry.json`,
`service_dependency_registry.json`, `state_authority_registry.json`,
`workspace_registry.json`, `project_registry.json`); the rest is deployment plumbing.

## How it fits
`infra/` is consumed by, not part of, the four-layer code stack (projections → transports
→ adapters → substrate). Backend code reads `infra/device_registry.json` for canonical
device names (per the Device Naming Protocol); the cockpit frontend mirrors the same data
through `cockpit/src/renderer/constants/devices.ts`. `infra/livekit.yaml` is bind-mounted
into the `os-livekit` container by the root `docker-compose.yml`; `infra/docker/umh.env`
is one of the compose `env_file` sources. The systemd units here are *staged copies* — the
live units live in `/etc/systemd/system/`.

## Structure

| Subdir | Files | Role |
|---|---|---|
| `infra/` (root) | 11 | The five mesh registries + `livekit.yaml`(+`.tpl`) for the LiveKit voice server + two lock/template artifacts |
| `infra/docker/` | 3 | Docker runtime env: `.env.example` (no secrets), `umh.env` + `umh.env.tpl` (1Password `op://` references, resolved at runtime by `dc-up.sh`) |
| `infra/scripts/` | 4 | 1Password + Docker orchestration: `dc-up.sh`, `run.sh`, `op-setup.sh`, `install-crontab.sh` |
| `infra/systemd/` | 1 | `umh-mesh.service` — the node-mesh server unit (staged copy) |

## Key components

**`device_registry.json`** (142 lines) — the single source of truth for device naming and
role assignment. Five devices: `vps` (`srv1500858`, role `orchestrator`, always-online at
`100.77.233.50`), `beast` (`desktop-lvguiq9`, role `executor`, Windows GPU box at
`100.74.199.102` running Ollama `qwen2.5-coder:14b` on :11434 and Kokoro TTS on :8880), and
three `controller`-role devices (`ipad`, `iphone`, `macbook`). Each entry carries
`allowed_roles`, `candidate_roles`, `role_confidence`, and diagnosis status. Per the Device
Naming Protocol, NEVER hardcode display names — read from here.

**`umh_node_registry.json`** (66 lines) — maps devices to logical UMH nodes: `umh-vps`
(primary, roles orchestrator/control_plane/observer, owns memory/governance/runtime/
execution/proof/reality/configuration state domains) and `umh-windows` (roles workstation/
builder/observer, owns workspace/session/observation).

**`state_authority_registry.json`** (72 lines) — declares which node is `primary` authority
for each of ten state domains and where that state physically lives (`neon_postgres`,
`in_memory`, or `json_file`). The VPS owns everything except workspace/session/observation,
which the Beast owns.

**`service_dependency_registry.json`** (187 lines) — 14 service roles with criticality
(`critical`/`core`/`supporting`/`optional`) and 16 typed dependencies (`required`/
`degraded`/`optional`). This is the graph behind "if governance is down, what breaks" —
e.g. `distributed_runtime → governance` is `required` (no packet executes without approval).

**`scripts/dc-up.sh`** (101 lines) — starts Docker services with secrets resolved from
1Password at runtime, never from plaintext files. **`scripts/install-crontab.sh`** (37 lines)
reads the op service-account token from `/root/.op-service-account-token` (mode 600, owner
check enforced), validates its `ops_*` format, injects it via stdin (never argv), and pipes
the rendered `crontab.managed` into `crontab -`.

**`systemd/umh-mesh.service`** — runs `transports/node_mesh/run.py` wrapped in
`scripts/op_run.sh` with the least-privilege `services/mesh.env.tpl` manifest so mesh relay
secrets (`UMH_MESH_RELAY_SECRET`, `UMH_MESH_VERDICT_SECRET`) are injected without a plaintext
copy. **`umh-vision-relay.service`** (in `infra/` root, not `systemd/`) runs `umh/vision_relay.py`
and self-installs iptables ACCEPT rules for port 8097 from the Docker and localhost subnets.

## Data & state
Reads: `/root/.op-service-account-token` (secret, mode-600), `services/mesh.env.tpl`,
`services/.env`. Writes: `crontab -` (via install-crontab), iptables rules (via the vision
relay unit's `ExecStartPost`). `device_registry.json.lock` is a lock artifact for concurrent
registry writes. Env vars flow exclusively through 1Password `op run`/`op inject` — the
umh.env template files hold only `op://` URIs, never resolved secrets.

## Gotchas
- **`livekit.yaml` contains a live LiveKit API key committed in cleartext** (the `keys:`
  block). It is a self-hosted-server shared secret bind-mounted read-only into `os-livekit`,
  but it is a plaintext credential in git — treat as a real finding; the `.tpl` variant
  exists to move it to 1Password.
- The systemd units in `infra/systemd/` and `infra/umh-vision-relay.service` are **staged
  copies**, not the running units. The live files are under `/etc/systemd/system/`; changing
  the repo copy does nothing until `sudo cp … && systemctl daemon-reload && restart`.
- The mesh server (`umh-mesh.service`, port :8094) and vision relay (:8097) are **host
  processes outside Docker** — `docker restart` never touches them (see
  [services-runtime](../services-runtime.md)).
- Never inline the op service-account token in `crontab.managed` — it would appear in
  `crontab -l` output. `install-crontab.sh` enforces stdin injection.
- Device display names must come from `device_registry.json` (backend) or
  `constants/devices.ts` (frontend) — hardcoding "VPS"/"Beast" violates the Device Naming
  Protocol pre-commit rule.

## See also
- [`docker/`](docker.md) — the Beast computer-use container (main compose is at repo root)
- [`config/`](config.md) — non-secret env config (`config/nonsecret.env`)
- [services-runtime](../services-runtime.md) — what is actually running right now
- [`_root-files`](_root-files.md) — `docker-compose.yml`, `Dockerfile`, deploy scripts
- [`scripts/`](scripts.md) — `cron-run`, `op_run.sh`, and the cron target scripts
- [architecture](../architecture.md) · [conventions](../conventions.md)
