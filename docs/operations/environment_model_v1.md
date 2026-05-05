# Environment Model v1

**Phase**: 94D.8
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Core Doctrine

- **Nodes** contain environments.
- **Environments** host workers.
- **Workers** execute capabilities.
- **Capabilities** are selected based on task constraints.
- **Interfaces** are separate from environments.

The system manages shells, tmux sessions, containers, and browser profiles
as first-class environments within the organism.

## Environment Types

| Type | Description |
|------|-------------|
| SSH_SESSION | Remote command execution session |
| WSL_SHELL | Windows Subsystem for Linux shell |
| TMUX_SESSION | Terminal multiplexer session |
| TMUX_PANE | Individual pane within tmux |
| WINDOWS_DESKTOP_SESSION | Interactive Windows desktop |
| PYTHON_VENV | Python virtual environment |
| DOCKER_CONTAINER | Containerized environment |
| BROWSER_PROFILE | Browser with specific profile/account |
| LOCAL_DAEMON | Background service on local machine |

## Environment Capabilities

| Capability | Description |
|-----------|-------------|
| SHELL_EXECUTION | Can run shell commands |
| FILE_ACCESS | Can read/write files |
| GUI_LAUNCH | Can launch GUI windows |
| GUI_OBSERVATION | Can observe GUI state |
| BROWSER_VISIBLE_LAUNCH | Can open visible browser |
| BROWSER_CONTROL | Can control browser DOM |
| COMPUTER_USE | Full mouse/keyboard/screen |
| LONG_RUNNING_WORKER | Can host persistent processes |
| ADVISOR_RELAY | Can communicate with VPS advisor |

## Environment Bindings

| Binding | GUI Reliable? | Description |
|---------|-------------|-------------|
| HEADLESS | NO | No display attached |
| SSH_SERVICE | NO | Windows Session 0 (service context) |
| INTERACTIVE_USER_SESSION | AFTER CONFIRMATION | Windows Session 1+ |
| UNKNOWN | NO | Not classified yet |

## GUI Safety Rule

An environment is GUI-safe ONLY when:
1. It is bound to INTERACTIVE_USER_SESSION
2. The WSL instance was started from Windows (not SSH)
3. Founder has confirmed visible launch works from that environment

## Key Discovery (Phase 94D.8)

Tmux sessions created via SSH inherit the SSH connection's broken
Windows interop socket. Even though they are "interactive" bash shells,
they cannot execute `powershell.exe` or any Windows executable because
the VSocket bridge is absent.

The interop socket is established when Windows launches WSL via:
- Windows Terminal → WSL tab
- `wsl.exe` from Windows command prompt
- Task Scheduler running as the logged-in user

It is NOT established when:
- SSH → `wsl -e bash` (service context)
- Any tmux session created from an SSH-originated WSL instance

## Module

`eos_ai/substrate/environment_contracts.py`
