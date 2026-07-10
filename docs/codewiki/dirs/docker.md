---
type: codewiki-dir
dir: docker
---

# `docker/` — the standalone computer-use container (VNC-accessible desktop for the Beast)

**3 files · 1,832 bytes · [Full file inventory](../inventory/docker.md)**

## Purpose
`docker/` holds exactly one thing: `docker/computer-use/`, a self-contained container image
that gives an agent a *real graphical desktop* — an Xvfb virtual display, a Fluxbox window
manager, Chromium, and X11 automation tools (`xdotool`, `scrot`, `xclip`) — reachable over
the browser via noVNC. It exists so computer-use / browser-verification workloads have an
interactive desktop session, which the headless orchestrator VPS cannot provide. The compose
file is named `docker-compose.beast.yml` because these containers are meant to run on the
Beast executor node, not the VPS.

## How it fits
This is deployment infrastructure, outside the four-layer code stack. It is deliberately
separate from the **main** application compose at the repo root (`docker-compose.yml`, which
runs the os-* services). Nothing in `substrate/`, `adapters/`, `transports/`, or
`projections/` imports from here — code reaches these desktops over VNC/noVNC (port 6080+),
consistent with the Browser Verification Law that requires an interactive desktop session on
an executor node, never the headless orchestrator.

## Structure

| File | Lines | Role |
|---|---|---|
| `docker/computer-use/Dockerfile` | 41 | Ubuntu 22.04 image: Xvfb + x11vnc + noVNC/websockify + Fluxbox + Chromium + xdotool/scrot/xclip. Display `:1`, resolution `1280x800x24`, exposes 6080 |
| `docker/computer-use/docker-compose.beast.yml` | 38 | Three parallel agent desktops — `umh-cu-agent-0/1/2`, ports 6080/6081/6082 → 6080, 2 GB mem cap each, `restart: unless-stopped` |
| `docker/computer-use/start.sh` | 13 | Entrypoint: starts Xvfb, Fluxbox, then `x11vnc` on VNC_PORT, then `websockify` serving noVNC on NOVNC_PORT |

## Key components
The full pipeline is three shell lines in `start.sh`: `Xvfb :1` creates the virtual display,
`x11vnc -display :1 -forever -nopw -rfbport 5901 -shared` exposes it over VNC with **no
password**, and `websockify --web /usr/share/novnc 6080 localhost:5901` bridges VNC to a
browser-accessible noVNC endpoint. `docker-compose.beast.yml` fans this out to three
identical desktops so multiple computer-use agents can run concurrently.

## Data & state
No persistent volumes, no env files — each container is ephemeral. State is the live X
session only. Port mapping is the entire external contract: 6080/6081/6082 on the host each
map to noVNC 6080 inside the respective `umh-cu-agent-N` container.

## Gotchas
- **`x11vnc` runs with `-nopw` (no VNC password).** Safe only because access is expected to
  be gated at the network layer (Tailscale private mesh, nothing exposed publicly). Do not
  expose these ports on a public interface.
- **Chromium here is bundled/headless-desktop Chromium, not a real branded browser.** Per
  the Real-Application Computer-Use memory, verification evidence should come from real apps
  in interactive sessions on capable nodes; this container is for lightweight desktop
  automation, and the browser choice is instance config.
- Runs on the **Beast**, not the VPS — the file is named `docker-compose.beast.yml` for a
  reason. The VPS is a headless orchestrator with no display (Browser Verification Law).
- This is NOT the application stack. The os-discord/os-operator/os-webhook/os-livekit/
  os-browser/os-scraper services live in the **repo-root** `docker-compose.yml` — see
  [`_root-files`](_root-files.md) and [services-runtime](../services-runtime.md).

## See also
- [`_root-files`](_root-files.md) — the main `docker-compose.yml` (application services)
- [`infra/`](infra.md) — device registry (Beast = executor role), systemd units
- [services-runtime](../services-runtime.md) — live process/container snapshot
- [architecture](../architecture.md)
