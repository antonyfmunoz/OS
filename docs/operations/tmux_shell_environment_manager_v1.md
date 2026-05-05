# Tmux Shell Environment Manager v1

**Phase**: 94D.8
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Purpose

Discovers, classifies, and manages tmux panes as execution environments.
Selects appropriate panes for command dispatch. Avoids sending commands
into busy or sensitive sessions.

## Module

`eos_ai/substrate/tmux_environment_manager.py`

## Pane Classification

| Command | Classification | Safe to dispatch? |
|---------|---------------|-------------------|
| bash, zsh, sh, fish, pwsh | shell | YES |
| claude | busy | NO (never) |
| python, python3 | busy | NO |
| node, npm | busy | NO |
| vim, nvim, nano | busy | NO |
| ssh, tmux | busy | NO |
| less, man, top, htop | busy | NO |
| (other) | unknown | NO (require caution) |

## Selection Priority

1. Panes with "gui" or "shell" in session name
2. Any available shell pane
3. Create new session `umh_gui_shell` if none available

## Key Functions

| Function | Purpose |
|----------|---------|
| `parse_tmux_list_panes_output()` | Parse tmux output into pane objects |
| `classify_tmux_pane()` | Return "shell", "busy", or "unknown" |
| `is_shell_pane()` | True if pane is a shell |
| `is_busy_pane()` | True if pane should not be touched |
| `choose_best_shell_pane()` | Select optimal dispatch target |
| `build_tmux_send_keys_command()` | Build SSH command for dispatch |
| `build_tmux_new_shell_session_command()` | Create new shell session |
| `build_tmux_capture_pane_command()` | Capture pane output |

## Current Local Panes (Phase 94D.8 Inspection)

```
bridge:0.1     | python3 | BUSY (do not touch)
test_interop:1.1 | bash  | SHELL (available but no interop)
umh_core:0.1   | bash    | SHELL (available but no interop)
```

## Critical Limitation

All three panes were created via SSH and lack the Windows interop socket.
`powershell.exe` commands fail with `UtilAcceptVsock:271: accept4 failed 110`.

Tmux panes are useful for:
- File operations within WSL
- Python scripts that don't call Windows executables
- Monitoring and logging
- Advisor relay file I/O

Tmux panes created via SSH are NOT useful for:
- Launching Chrome or any Windows GUI
- Calling `powershell.exe`, `cmd.exe`, or `.exe` files
- Any command requiring the Windows interop socket

## Correct Path for GUI Launch

The Chrome launch must come from a WSL instance that was started
from the Windows side (Windows Terminal, wsl.exe from cmd, etc.).
See: `docs/operations/interactive_gui_bound_environment_policy_v1.md`
