# UMH tmux Session Visibility Architecture

Phase: 14.6B-UMH
Status: DRAFT

## tmux Socket Mounting

- tmux socket mounted into `os-discord` Docker container at `/tmp/tmux-0`
- Allows Discord bot service to interact with tmux sessions on host
- Socket permissions managed by Docker volume mount configuration

## Claude CLI Session Targeting

- Environment variable: `EOS_ROUTER_CLAUDE_CLI_SESSION=dex_main`
- Routes CLI commands to the correct tmux session
- `dex_main` is the primary Claude Code development session

## tmux Tool Adapter

- Location: `adapters/tool_adapters/tmux.py` (137 lines)
- Provides programmatic tmux session interaction
- Capabilities: send keys, capture pane output, list sessions, create/kill windows
- Used by agents to execute commands in tmux sessions

## Cockpit Visibility

- No dedicated cockpit panel for tmux session visibility
- tmux session state is not surfaced in cockpit UI
- Session interaction is technically possible through the tool adapter but not exposed to the operator via cockpit
- Operator must SSH into VPS and attach to tmux directly for session visibility

## Session Architecture

- VPS runs tmux as the persistent process manager for Claude Code
- Multiple tmux windows/panes possible within `dex_main` session
- Sessions survive SSH disconnects -- always available on reconnect
- Developer accesses via Termius (iPhone), code-server (iPad), or direct SSH
