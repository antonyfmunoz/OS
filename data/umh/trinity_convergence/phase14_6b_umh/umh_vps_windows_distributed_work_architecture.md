# UMH VPS-Windows Distributed Work Architecture

Phase: 14.6B-UMH
Status: DRAFT

## VPS Node (100.77.233.50)

- **Role**: Coordination brain -- lightweight, always-on
- Runtime code, services, orchestration
- Docker containers: `os-discord`, `os-operator`, `os-webhook`, `os-scraper`
- tmux sessions for Claude Code (`dex_main`)
- No large models (tiny fallback only, e.g. `qwen2.5:0.5b` via Ollama)
- No heavy compute -- delegates to Beast for GPU work

## Beast Node (100.74.199.102)

- **Role**: GPU workhorse
- Docker Engine in WSL2 Ubuntu (bypasses Docker Desktop)
- SSH-controllable from VPS
- Kokoro TTS 82M at `:8880` (Python 3.12 venv, `E:\kokoro-tts`)
- Electron builds for cockpit desktop app (`electron-vite build`)
- Full OS repo mirror at `C:\dev\dev\`
- Large local models for heavy inference
- Media processing and heavy compute tasks

## Network Layer

- **Tailscale mesh** connects all devices on private network
- Nothing exposed publicly -- all inter-node communication over Tailscale
- Devices: VPS, Beast (Windows), iPhone (Termius), iPad (code-server)
- SSH access to Beast: `ssh "antonys beast pc@100.74.199.102"`

## Node Mesh Protocol

- Location: `transports/node_mesh/`
- Defines inter-node communication protocol
- Nodes discover each other and exchange capabilities
- VPS coordinates work distribution across mesh

## Windows Daemon

- Location: `nodes/`
- UMH node daemon runs as Windows Service (`AUTO_START`)
- Connects to VPS mesh on `:8094`
- Receives work packets from VPS coordinator
- Executes in appropriate environment (native Windows, WSL2, containers, Hyper-V)

## Development Session Bridge

- Location: `substrate/organism/development_session_bridge.py`
- Makes any coding harness (Claude Code, VS Code, etc.) a governed organ
- Bridges development activity into organism awareness
- Cockpit endpoint: `organism.dev_sessions`
- Development sessions are tracked, governed, and visible to the organism

## Node Role Discipline

- Each node stores only what its role requires
- VPS: no large models, no node_modules for inactive frontends, no archives
- Beast: full repos with git history, large models, heavy assets
- Worktrees removed immediately after merge on VPS
- Local branches deleted after merge; `git gc --prune=now` after cleanup
