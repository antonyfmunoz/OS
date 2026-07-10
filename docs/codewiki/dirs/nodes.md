---
type: codewiki-dir
dir: nodes
---

# `nodes/` — distributed node runtime (work distribution + Windows daemon + execution bridges)

**58 files · 393,902 bytes · [Full file inventory](../inventory/nodes.md)**

## Purpose
`nodes/` is the runtime for UMH's distributed execution — the code that lets the coordination brain (the VPS orchestrator) hand real work to capable executor nodes (the Beast, containers, other machines) and get results back. It has three concerns: distributing work off the orchestrator, defining and validating the *binding contracts* that pin a work packet to a concrete execution environment, and the Windows daemon that runs on the Beast to actually perform GUI/vision/shell/terminal work in an interactive desktop session.

## How it fits
`nodes/` is executor-side runtime. Its Windows daemon (`nodes/windows/umh_node/`) connects *up* to the transport mesh — `client.py` opens a WebSocket to the VPS node-mesh server ("connected to VPS mesh server") and enforces write-class authorization against `substrate/execution/mesh_verdict.py` (mesh-signed tokens). The `nodes/environments/` bridge contracts pair with the substrate/organism reconcilers (`substrate/organism/mesh_reconciler.py`, `device_provisioner.py`) that keep the orchestrator's model of each node in sync. So the flow is: orchestrator distributes → mesh transport carries → node daemon executes → results ingested back. This is the concrete machinery behind the **Browser Verification Law**: real, visible, interactive browser evidence runs on executor-roled nodes here, never on the headless orchestrator.

## Structure

| Subdir | Files | Role |
|---|---|---|
| `distribution/` | 3 | Bridges channels to the execution pipeline (`distributor.py`) + first-boot onboarding detection (`first_boot.py`) |
| `environments/` | 19 | Execution binding contracts/validators, packet builders, queue paths, VPS↔local bridge, Windows-desktop adapter contracts |
| `windows/` | 35 | The Windows node daemon (`umh_node/`), desktop tray (`umh_desktop/`), Kokoro TTS server, setup scripts |
| `__init__.py` | 1 | Package marker |

## Key components

**`environments/` — the binding layer.** `execution_binding_contracts.py` (342) and `execution_binding_validator.py` (281) define and enforce how a work packet is *bound* to a real environment before it runs. `work_packet.py` (206) is the packet contract; `w0_packet_builder.py` and `windows_desktop_request_builder.py` (433) construct packets/requests. `vps_local_bridge.py` (144) and `local_pull_protocol.py` (256) are the VPS↔local worker handoff. `chrome_visible_launch.py` (246) is the gate that ensures Chrome opens *visibly* on an executor — the mechanical enforcement of "no headless verification evidence." `workspace_probe.py` (232) discovers active workspace state via subprocess.

**`windows/umh_node/` — the daemon.** This is the process that runs on the Beast as a **Windows Task Scheduler ONLOGON job in Session 1** (the interactive desktop session) so that GUI automation and real Chrome are visible, not stuck in headless Session 0. Core: `client.py` (693, the mesh WebSocket client), `service.py` (141, Windows Service entry), `launcher.py` (10, the Session-1 launcher), `config.py` (146, reads `umh_node.toml`/`.env`), `governance.py` (64, node-side capability policy), `workspace.py` (349, active-window/screen tracking). Its `adapters/` are the capability surface: `desktop.py` (GUI automation/screenshots), `desktop_stream.py` (JPEG frame emission — feeds `umh/desktop_relay.py`), `camera.py` (1,344 — Insta360 webcam + PTZ, feeds `umh/vision_relay.py`), `object_detector.py` (YOLOv8n), `vision_runtime.py`, `iou_tracker.py`, `terminal.py` (persistent shells), `shell.py`, `filesystem.py`, `clipboard.py`, `container.py` (Docker), `broadcast.py` (FFmpeg), `hermes.py` (Hermes CLI). `umh_desktop/tray.py` (197) is the system-tray companion. `kokoro_server.py` (123) hosts the Kokoro TTS model on the Beast GPU.

**`distribution/`** — `distributor.py` (356) bridges channels to the execution pipeline; `first_boot.py` (176) detects whether a node still needs onboarding.

## Data & state
The daemon reads config from `umh_node.toml` and `.env` (`config.py`) and emits system metrics (`metrics.py` — CPU/mem/disk/battery/GPU). Mesh auth is token-signed: write-class capability requests must carry a token signed with the shared mesh-verdict secret (`substrate/execution/mesh_verdict.py`), validated in `client.py`. Queue/result state flows through `environments/queue_paths.py`, `result_ingestion.py`, and `local_pull_protocol.py`. A stray `nodes/windows/.ruff_cache/` (2 files) is a committed lint-cache artifact, not runtime state.

## Gotchas
- **The daemon must run in Session 1, not Session 0.** SSH-launched processes land in the non-interactive Session 0 where Chrome is invisible and GUI automation fails. The Task Scheduler ONLOGON path (`launcher.py`) is the only one that produces real, visible, interactive sessions — this is why `chrome_visible_launch.py` exists as a gate (per `.claude/rules/browser-verification.md`).
- **The mesh WS server is a host process, not a container.** The Beast daemon dials the VPS mesh server on the mesh port; restarting Docker services does not restart that server. Debug mesh connectivity at the process level.
- **All node subprocess calls on Windows use `CREATE_NO_WINDOW`** (`subprocess_utils.py` / `no_window_kwargs()`) to stop CMD/PowerShell console windows flashing during automation in the interactive session.
- **Node Role Discipline applies here:** the Windows node is the GPU workhorse (full repos, large models, heavy compute); the VPS is coordination-only. Don't push heavy artifacts to the VPS side of this bridge.
- The `.ruff_cache/` under `nodes/windows/` is checked-in lint scratch — safe to ignore/clean; it is not part of the daemon.

## See also
- [umh.md](umh.md) — the vision/desktop relays these node adapters feed
- [transports.md](transports.md) — `node_mesh/server.py`, the mesh server the daemon connects to
- [substrate.md](substrate.md) — `execution/mesh_verdict.py`, `organism/mesh_reconciler.py`, `organism/device_provisioner.py`
- [dot-claude.md](dot-claude.md) — `rules/browser-verification.md` (executor-roled node law)
- [infra.md](infra.md) — `device_registry.json` defines which nodes are executor-roled
