---
type: codewiki-inventory
dir: infra
source_sha: a5f09e48e253dafdfcecee94a8e54f16224bae43
---

# `infra/` — File Inventory

**Files:** 19 regular + 0 symlinks · **Bytes:** 60,510

[Narrative page](../dirs/infra.md)


## infra/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `infra/crontab.managed` | 53 | — |
| `infra/device_registry.json` | 142 | — |
| `infra/device_registry.json.lock` | 0 | build/lock artifact |
| `infra/livekit.yaml` | 15 | — |
| `infra/livekit.yaml.tpl` | 15 | — |
| `infra/project_registry.json` | 50 | — |
| `infra/service_dependency_registry.json` | 187 | — |
| `infra/state_authority_registry.json` | 72 | — |
| `infra/umh-vision-relay.service` | 16 | — |
| `infra/umh_node_registry.json` | 66 | — |
| `infra/workspace_registry.json` | 162 | — |

## infra/docker/ (3 files)

| Path | Lines | Purpose |
|---|---|---|
| `infra/docker/.env.example` | 69 | Environment variable template (no secrets) |
| `infra/docker/umh.env` | 104 | UMH Docker runtime secrets — resolved from 1Password at runtime via dc-up.sh |
| `infra/docker/umh.env.tpl` | 103 | UMH Docker runtime secrets — resolved from 1Password at runtime via dc-up.sh |

## infra/scripts/ (4 files)

| Path | Lines | Purpose |
|---|---|---|
| `infra/scripts/dc-up.sh` | 101 | dc-up.sh — Start Docker services with secrets from 1Password |
| `infra/scripts/install-crontab.sh` | 37 | — |
| `infra/scripts/op-setup.sh` | 136 | op-setup.sh — Populate 1Password vault from current .env files |
| `infra/scripts/run.sh` | 15 | run.sh — Run any command with UMH secrets from 1Password |

## infra/systemd/ (1 files)

| Path | Lines | Purpose |
|---|---|---|
| `infra/systemd/umh-mesh.service` | 30 | — |
