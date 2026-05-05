# Local Tmux Execution Surface v1

**Phase:** 96.8A
**Status:** Active
**Layer:** UMH Substrate — `core/environment_bridge/tmux_surface.py`

## Purpose

Models tmux as a persistent local execution environment. Provides
command construction, allowlisting, and dangerous command blocking
at the model layer — before any command reaches a shell.

## Default Configuration

| Field | Default |
|-------|---------|
| Host | `DESKTOP-LVGUIQ9` |
| Session | `eos-worker` |
| Window | `main` |
| Working directory | `/opt/OS` |

## Allowed Commands (default)

`python3`, `pip`, `git`, `ls`, `cat`, `echo`, `mkdir`, `cp`

## Dangerous Commands (blocked)

Full commands: `rm -rf /`, `rm -rf ~`, `rm -rf /*`, `mkfs`,
`dd if=/dev/zero`, `chmod -R 777 /`, `shutdown`, `reboot`,
`halt`, `poweroff`, `init 0`, `init 6`, fork bomb.

Prefix patterns: `rm -rf /`, `mkfs `, `dd if=/dev/zero`,
`chmod -R 777 /`, `curl | bash`, `wget | bash`,
`curl | sh`, `wget | sh`.

## Command Construction

`build_tmux_send_command()` generates the tmux send-keys invocation:

```
tmux send-keys -t eos-worker:main 'safe_cmd' Enter
```

Single quotes in the command are escaped: `'` → `'\''`

## Safety Model

1. Check `tmux_command_is_allowed()` before building
2. Blocked commands checked against exact match AND prefix match
3. Case-insensitive comparison
4. `tmux_surface_blocks_command()` is the inverse gate for use
   in validators

## Key Constraint

This module builds commands but does NOT execute them. Execution
happens in the local worker runtime. The module is pure safety
and construction — no shell calls, no I/O.
