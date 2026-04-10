---
name: tmux
description: "Use when running, attaching to, or scripting long-lived terminal sessions, managing detached agent processes, capturing pane output, splitting panes, automating tmux from Python/bash, debugging hung sessions, or configuring .tmux.conf."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://man.openbsd.org/tmux"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "tmux 3.5a"
sdk_version: "libtmux 0.53 (Python bindings)"
speed_category: stable
---

# Tool: tmux

## What This Tool Does

tmux is a terminal multiplexer with a client/server architecture. A long-lived
server holds sessions, windows, and panes in memory; lightweight clients attach
and detach without affecting the tree. Every interactive keybinding is also a
command verb you can call from scripts — this makes tmux the canonical substrate
for long-running agents, detachable SSH work, and programmatic terminal control.

Core capabilities:

- **Persistent sessions** that survive SSH disconnects, reboots (with resurrect), and client crashes
- **Scriptable control** via `send-keys`, `capture-pane`, `pipe-pane`, `display-message -p`, `list-* -F`
- **Panes, windows, sessions** as a three-level hierarchy with stable IDs (`%N`, `@N`, `$N`)
- **Hooks and format strings** — a small programming language inside the multiplexer
- **Popups (`display-popup`)** — floating panes for command palettes and launchers
- **Multi-client sessions** — multiple attachers see the same state simultaneously

## EOS Integration

tmux is the execution substrate for EOS long-running processes. Primary uses:

- **Claude Code 24/7 loop** — a named detached session on a pinned socket so
  the main agent can be reattached from iPhone/iPad/laptop without interrupting it
- **Parallel agent orchestration** — multiple panes running independent workers
  (cognitive loops, debug sessions, research agents)
- **Log scraping** — `capture-pane -p -S -N` to pull the last N lines of any
  pane's scrollback into Python for analysis or memory writes
- **Continuous logging** — `pipe-pane 'cat >> logfile'` for always-on append
- **Headless execution** — `tmux new-session -d` from cron and systemd to run
  processes that need a PTY without a human attached

Canonical EOS pattern:
- Socket pinned: `tmux -L eos ...` (or `-S /tmp/tmux-eos.sock`)
- Detached: `-d`
- Sized: `-x 220 -y 50` (so log lines don't wrap)
- Logged: `pipe-pane -o 'cat >> ~/.tmux-logs/SESSION.log'`
- Respawned: `set-hook pane-died 'respawn-pane -k'`

## Authentication

None. tmux is local-only. Security is enforced by Unix socket permissions
(`/tmp/tmux-$UID/default`, mode 0700 by default). Different users have different
sockets and cannot see each other's sessions unless the socket is explicitly
shared.

## Quick Reference

### Create, attach, detach

```bash
# Detached session, idempotent (attach if exists, create if not)
tmux new-session -d -A -s eos-main -x 220 -y 50 -c /opt/OS

# Attach, forcing other clients to detach
tmux attach -d -t eos-main

# List
tmux list-sessions -F '#{session_name} #{session_attached}'

# Detach programmatically
tmux detach-client -s eos-main
```

### Send commands to a pane

```bash
# RIGHT — Enter submits the line
tmux send-keys -t eos-main:0.0 'python3 -m eos_ai.cognitive_loop' Enter

# WRONG — text sits at the prompt forever
tmux send-keys -t eos-main:0.0 'python3 -m eos_ai.cognitive_loop'

# Control characters
tmux send-keys -t eos-main:0.0 C-c       # cancel running process
tmux send-keys -t eos-main:0.0 C-d       # EOF

# Literal text containing key-name-looking strings
tmux send-keys -t eos-main:0.0 -l 'echo "press Enter"'
tmux send-keys -t eos-main:0.0 Enter
```

### Capture output

```bash
# Last 1000 lines of scrollback
tmux capture-pane -t eos-main:0.0 -p -S -1000

# Whole scrollback, joining wrapped lines
tmux capture-pane -t eos-main:0.0 -p -S - -E - -J > /tmp/claude.out

# With color escapes preserved
tmux capture-pane -t eos-main:0.0 -p -e -S -500
```

### Continuous pipe-pane logging

```bash
tmux pipe-pane -t eos-main:0.0 -O 'cat >> ~/.tmux-logs/eos-main.log'
# Stop
tmux pipe-pane -t eos-main:0.0
```

### Read pane state via format strings

```bash
# PID of a specific pane (for kill -9 if hung)
PID=$(tmux display-message -p -t eos-main:0.0 '#{pane_pid}')

# List every pane server-wide, tab-delimited for parsing
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index}\t#{pane_id}\t#{pane_pid}\t#{pane_current_command}'
```

### Splits, windows, layouts

```bash
tmux new-window -t eos-main -n worker
tmux split-window -h -t eos-main:0 -c /opt/OS       # side-by-side
tmux split-window -v -t eos-main:0 -c /opt/OS       # stacked
tmux select-layout -t eos-main:0 tiled
tmux kill-pane -t eos-main:0.1
tmux kill-window -t eos-main:worker
```

### Socket pinning

```bash
# All commands MUST use the same -L or -S to talk to the same server
tmux -L eos new-session -d -s main
tmux -L eos attach -t main
tmux -L eos kill-session -t main
```

## Conceptual Model

**Server is the truth. Clients are cameras.** A tmux server is a long-lived
process holding a tree: `server → sessions → windows → panes`. Each pane owns
a PTY and a child process. Attaching a client just opens a view; detaching
closes the view without touching the tree. Kill the server, the whole tree dies.

Every interactive binding (`prefix c` for new-window) is shorthand for a
command verb (`tmux new-window`). This is why tmux is scriptable — there is no
"scripting mode" vs "interactive mode," they are the same command surface.

If you internalize server-as-truth, every confusing tmux behavior becomes obvious:
- "I closed my terminal and came back — everything's still there" → the server never noticed
- "My cron job can't find the session" → cron is talking to a different socket
- "send-keys isn't registering" → you forgot `Enter`, or the pane is in copy-mode

## Gotchas

- **Forgetting `-d` on scripted `new-session`** → `open terminal failed: not a
  terminal` under cron/systemd. ALWAYS `-d` in scripts.
- **Forgetting `Enter` on `send-keys`** → command sits at prompt unsubmitted.
  The #1 scripting bug. Use `Enter` or `C-m` (equivalent).
- **Wrong socket** → different `$UID`, different `-L`, different `XDG_RUNTIME_DIR`
  produces "no server running" on a server that is actually up. Pin with
  `-L name` or `-S /path` on EVERY call.
- **Default `history-limit=2000`** is too small for log scraping. Set
  `set -g history-limit 100000` in .tmux.conf.
- **`escape-time` default 500ms** makes `<Esc>` laggy in Neovim. Set
  `set -sg escape-time 0`.
- **`capture-pane` shows the final redrawn state** for lines rewritten with
  `\r` (tqdm, spinners). To capture the raw stream, use `pipe-pane` from the start.
- **Default session size 80x24** if no client attaches — log lines wrap. Pass
  `-x 220 -y 50` on detached `new-session`.
- **`synchronize-panes` foot-gun** — forgetting to turn it off and typing
  `rm -rf` hits every pane. Add `#{?pane_synchronized,SYNC,}` to status-right.
- **`send-keys` doesn't know if the pane is in vim insert mode** — it just
  writes bytes. Check `#{pane_in_mode}` or `respawn-pane -k` first if you need
  a known-clean state.
- **Ubuntu 22.04 ships tmux 3.2a**, 24.04 ships 3.4. Features like
  `pane-title-changed` hooks (3.5+) won't exist. `tmux -V` at provisioning time.
- **systemd user service needs `loginctl enable-linger $USER`** or the service
  dies on logout. Plus `Type=forking` and `KillMode=none` so children survive
  `systemctl stop`.
- **Cron has empty PATH and no TMUX env** — use absolute `/usr/bin/tmux` and
  set `HOME=/root` at top of crontab.
- **Parsing `tmux ls` human output with grep is fragile** — always use
  `-F '#{field}\t#{field2}'` and split on `\t` in your script.

See references/best_practices.md for the full 19-section creator-level knowledge base.
See references/examples.md for EOS-specific recipes.
See references/anti_patterns.md for the full failure catalog.
See references/integrations.md for composition with SSH, systemd, cron, Neovim, fzf, Claude Code.
