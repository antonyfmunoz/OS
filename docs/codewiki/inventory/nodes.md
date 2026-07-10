---
type: codewiki-inventory
dir: nodes
source_sha: 70deadbac8667755a38ac49595afd09afc209c2f
---

# `nodes/` — File Inventory

**Files:** 58 regular + 0 symlinks · **Bytes:** 393,902

[Narrative page](../dirs/nodes.md)


## nodes/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `nodes/__init__.py` | 1 | Distributed execution nodes — Windows, Linux, container environments. |

## nodes/distribution/ (3 files)

| Path | Lines | Purpose |
|---|---|---|
| `nodes/distribution/__init__.py` | 1 | Task distribution layer — work distribution and first-boot handshake. |
| `nodes/distribution/distributor.py` | 356 | Distribution Layer — bridges channels to the execution pipeline. |
| `nodes/distribution/first_boot.py` | 176 | First Boot — detects whether the system needs onboarding. |

## nodes/environments/ (19 files)

| Path | Lines | Purpose |
|---|---|---|
| `nodes/environments/__init__.py` | 0 | package marker (empty) |
| `nodes/environments/bootstrap_plan.py` | 231 | Bootstrap plan for the Environment Bridge. |
| `nodes/environments/bootstrap_status.py` | 144 | Bootstrap status checker for the Environment Bridge. |
| `nodes/environments/chrome_visible_launch.py` | 246 | Chrome visible launch gate for the Environment Bridge. |
| `nodes/environments/execution_binding_contracts.py` | 342 | Execution Binding Contracts for the Environment Bridge. |
| `nodes/environments/execution_binding_validator.py` | 281 | Execution Binding Validator for the Environment Bridge. |
| `nodes/environments/heartbeat.py` | 137 | Worker heartbeat for the Environment Bridge. |
| `nodes/environments/local_pull_protocol.py` | 256 | Local pull protocol for the Environment Bridge. |
| `nodes/environments/packet_validator.py` | 274 | Packet validator for the Environment Bridge. |
| `nodes/environments/queue_paths.py` | 104 | Queue paths for the Environment Bridge. |
| `nodes/environments/result_ingestion.py` | 164 | Result ingestion for the Environment Bridge. |
| `nodes/environments/tmux_surface.py` | 139 | Tmux execution surface for the Environment Bridge. |
| `nodes/environments/vps_local_bridge.py` | 144 | VPS ↔ Local Worker bridge for the Environment Bridge. |
| `nodes/environments/w0_packet_builder.py` | 268 | W0-001 packet builder for the Environment Bridge. |
| `nodes/environments/windows_desktop_adapter_contracts.py` | 196 | Windows Interactive Desktop Adapter Contracts. |
| `nodes/environments/windows_desktop_adapter_validator.py` | 161 | Windows Interactive Desktop Adapter Validator. |
| `nodes/environments/windows_desktop_request_builder.py` | 433 | Windows Interactive Desktop Request Builder. |
| `nodes/environments/work_packet.py` | 206 | Work Packet contract for the Environment Bridge. |
| `nodes/environments/workspace_probe.py` | 232 | Workspace Probe — subprocess-based discovery of active workspace state. |

## nodes/windows/ (35 files)

| Path | Lines | Purpose |
|---|---|---|
| `nodes/windows/.ruff_cache/.gitignore` | 2 | Git ignore patterns |
| `nodes/windows/.ruff_cache/CACHEDIR.TAG` | 1 | — |
| `nodes/windows/__init__.py` | 1 | Windows node — daemon service and desktop tray for UMH mesh. |
| `nodes/windows/kokoro_server.py` | 123 | Kokoro TTS Server — OpenAI-compatible API on Beast GPU. |
| `nodes/windows/pyproject.toml` | 32 | Python package/build configuration |
| `nodes/windows/requirements-windows.txt` | 9 | websockets>=12.0 |
| `nodes/windows/requirements.txt` | 11 | Python pip dependencies |
| `nodes/windows/setup_windows.ps1` | 79 | UMH Node Daemon — Windows Setup Script |
| `nodes/windows/start_kokoro.ps1` | 27 | Start Kokoro TTS Server on Beast |
| `nodes/windows/umh_desktop/__init__.py` | 0 | package marker (empty) |
| `nodes/windows/umh_desktop/tray.py` | 197 | umh-desktop — System tray companion for UMH node mesh. |
| `nodes/windows/umh_node/__init__.py` | 0 | package marker (empty) |
| `nodes/windows/umh_node/adapters/__init__.py` | 0 | package marker (empty) |
| `nodes/windows/umh_node/adapters/broadcast.py` | 181 | Broadcast adapter — runs FFmpeg engine on the local node. |
| `nodes/windows/umh_node/adapters/camera.py` | 1,344 | Camera adapter — webcam capture and PTZ control for Insta360 Link 2. |
| `nodes/windows/umh_node/adapters/clipboard.py` | 31 | Clipboard adapter — read/write system clipboard. |
| `nodes/windows/umh_node/adapters/container.py` | 178 | Container adapter — Docker container lifecycle and execution. |
| `nodes/windows/umh_node/adapters/desktop.py` | 273 | Desktop adapter — GUI automation, window management, screenshots. |
| `nodes/windows/umh_node/adapters/desktop_stream.py` | 95 | Desktop streaming adapter — captures screen and emits JPEG frames. |
| `nodes/windows/umh_node/adapters/filesystem.py` | 95 | Filesystem adapter — read, write, list, move, delete files. |
| `nodes/windows/umh_node/adapters/hermes.py` | 430 | Hermes adapter — wraps Hermes CLI on the Beast machine. |
| `nodes/windows/umh_node/adapters/iou_tracker.py` | 262 | IoU tracker — persistent object IDs across frames. |
| `nodes/windows/umh_node/adapters/object_detector.py` | 376 | Object detector — YOLOv8n inference on camera frames. |
| `nodes/windows/umh_node/adapters/shell.py` | 62 | Shell adapter — executes commands on the local machine. |
| `nodes/windows/umh_node/adapters/terminal.py` | 434 | Terminal adapter — persistent shell sessions via subprocess pipes. |
| `nodes/windows/umh_node/adapters/vision_runtime.py` | 265 | Vision runtime — CV capability detection and tracker management on Beast. |
| `nodes/windows/umh_node/client.py` | 693 | WebSocket client — connects to the VPS node mesh server. |
| `nodes/windows/umh_node/config.py` | 146 | Node daemon configuration — reads umh_node.toml and .env. |
| `nodes/windows/umh_node/governance.py` | 64 | Node-side governance — validates capability requests against local policy. |
| `nodes/windows/umh_node/launcher.py` | 10 | Session 1 launcher — starts UMH node daemon in the interactive desktop session. |
| `nodes/windows/umh_node/metrics.py` | 95 | System metrics collector — CPU, memory, disk, battery, network, GPU. |
| `nodes/windows/umh_node/peripheral_scanner.py` | 416 | Peripheral scanner — enumerates all connected peripherals. |
| `nodes/windows/umh_node/service.py` | 141 | umh-node-service — Windows Service entry point. |
| `nodes/windows/umh_node/subprocess_utils.py` | 17 | Subprocess helpers for the Windows daemon. |
| `nodes/windows/umh_node/workspace.py` | 349 | Workspace awareness — tracks active window and full screen state. |
