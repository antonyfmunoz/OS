# tmux — Creator-Level Best Practices
Source: man.openbsd.org/tmux, github.com/tmux/tmux, tao-of-tmux, tmux CHANGES
API Version: tmux command surface (local UNIX socket, no network API)
SDK Version: tmux 3.5a / 3.6a (stable as of 2026-04)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

N/A — tmux is local-only. There is no network API, no token, no key. Access
control is filesystem permissions on the UNIX domain socket at
`$TMPDIR/tmux-<uid>/default` (or whatever `-L name` / `-S path` specifies).
Anyone who can `read/write` that socket can drive the server. The EOS
consequence: pin the socket with `-L eos` and rely on POSIX uid ownership.
Never chmod the socket world-writable; never share a socket across untrusted
uids.

## Core Operations with Exact Signatures

All signatures assume tmux >= 3.0. Aliases in parentheses. Target syntax is
universal: `-t [session][:window][.pane]`. Windows can be referenced by index
or name; panes by index, `%id`, or position keywords (`top-left`, etc.).

### Sessions

```
tmux new-session   [-AdDEPX] [-c start-directory] [-e env=value] \
                   [-F format] [-f config-file] [-n window-name] \
                   [-s session-name] [-t group-name] [-x width] \
                   [-y height] [shell-command]
# alias: new
```

Key flags:
- `-d` detached (NEVER omit in scripts — without it tmux tries to attach and blocks on a TTY)
- `-s NAME` session name
- `-A` attach if exists, create if not (idempotent)
- `-D` if `-A` and exists, detach other clients first
- `-x COLS -y ROWS` force pseudo-terminal size for headless (otherwise defaults to 80x24)
- `-P -F '#{session_id}'` print formatted info on creation
- `-e KEY=VAL` inject env var into the new session environment
- `-c DIR` start directory

```
tmux attach-session  [-dErx] [-c working-directory] [-f flags] \
                     [-t target-session]    # alias: attach, a
tmux list-sessions   [-F format] [-f filter]                     # alias: ls
tmux kill-session    [-aC] [-t target-session]                   # -a kills all but target
tmux has-session     [-t target-session]                         # exit 0 if exists
tmux rename-session  [-t target-session] new-name
tmux switch-client   [-ElnprZ] [-c target-client] [-t target-session] [-T key-table]
tmux kill-server                                                  # nukes everything on socket
```

### Windows

```
tmux new-window     [-abdkPS] [-c start-dir] [-e env=val] \
                    [-F format] [-n window-name] [-t target-window] [shell-command]
# -a after target, -b before, -k kill existing, -d don't switch to new
tmux kill-window    [-a] [-t target-window]   # -a kill all but target
tmux rename-window  [-t target-window] new-name
tmux list-windows   [-aF format] [-f filter] [-t target-session]
tmux select-window  [-lnpT] [-t target-window]
tmux move-window    [-ardk] [-s src] [-t dst]
tmux swap-window    [-d] [-s src] [-t dst]
tmux link-window    [-abdk] [-s src] [-t dst]
tmux unlink-window  [-k] [-t target]
```

### Panes

```
tmux split-window   [-bdfhIvPZ] [-c start-dir] [-e env=val] \
                    [-l size[%]] [-t target-pane] [-F format] [shell-command]
# -h horizontal split (side-by-side), -v vertical (default, stacked)
# -f full width/height across the window (not just current pane)
# -l 30 size in lines/cols, -l 40% percentage
# -d don't make new pane active, -P print info, -F format
tmux select-pane    [-DdeLlMmRtUZ] [-T title] [-t target-pane]
# -L/-R/-U/-D move left/right/up/down, -m mark, -M clear mark
tmux kill-pane      [-a] [-t target-pane]
tmux resize-pane    [-DLMRTUZ] [-t target-pane] [-x width] [-y height] [adjustment]
tmux swap-pane      [-dDU] [-s src-pane] [-t dst-pane]
tmux break-pane     [-dPZ] [-F fmt] [-n win-name] [-s src] [-t dst]
tmux join-pane      [-bdfhv] [-l size] [-s src] [-t dst]
tmux list-panes     [-asF format] [-f filter] [-t target]
tmux respawn-pane   [-k] [-c start-dir] [-e env=val] [-t target-pane] [shell-command]
tmux respawn-window [-k] [-c start-dir] [-e env=val] [-t target-window] [shell-command]
```

### Send / Capture

```
tmux send-keys      [-FHlMRX] [-N repeat-count] [-t target-pane] key ...
# -l literal (no key-name lookup) — use for arbitrary text
# -H send hex bytes (e.g. send-keys -H 0d for CR)
# -R reset terminal state
# -X invoke a command from copy-mode key table (e.g. send-keys -X cancel)
# Keys: Enter, C-m (== Enter), C-c, Escape, BSpace, Tab, Space, Up, etc.

tmux send-prefix    [-2] [-t target-pane]

tmux capture-pane   [-aepPqCJN] [-b buffer-name] [-E end-line] \
                    [-S start-line] [-t target-pane]
# -p print to stdout (most common scripted use)
# -S -N start at line -N of scrollback (-S - means top, -S -3000 last 3000)
# -E end line (- = bottom)
# -e include escape sequences for colors
# -J join wrapped lines
# -C escape non-printables (octal)
# -a alternate screen

tmux pipe-pane      [-IOo] [-t target-pane] [shell-command]
# -O output (default, capture stdout from pane to command)
# -I input (write to pane stdin)
# -o toggle: if already piping, stop; else start
# Empty command stops piping.
```

### Display / Options / Config

```
tmux display-message  [-aIklNpvt target-client] [-c target-client] \
                      [-d delay] [-F format] [-t target-pane] [message]
# -p print to stdout (use this for format string evaluation in scripts)

tmux set-option       [-aFgopqsuUw] [-t target] option [value]
# -g global, -s server, -w window, -p pane, -a append, -u unset, -F format expand
tmux set-window-option [-aFgoqu] [-t target-window] option [value]   # alias setw
tmux show-options     [-AgHpqsvw] [-t target] [option]
tmux source-file      [-Fnqv] path ...    # -q quiet on missing, -v verbose, -n parse only
tmux set-environment  [-Fhgru] [-t target-session] name [value]
tmux show-environment [-hgs] [-t target-session] [name]
tmux set-hook         [-agRuw] [-t target-session] hook-name command
tmux wait-for         [-L|-S|-U] channel
tmux if-shell         [-bF] [-t target-pane] shell-command command [command]
tmux run-shell        [-bC] [-d delay] [-t target-pane] [shell-command]
tmux display-popup    [-BCEK] [-b border-lines] [-c start-dir] [-d start-dir] \
                      [-e env=val] [-h height] [-t target] [-T title] \
                      [-w width] [-x pos] [-y pos] [shell-command]
tmux display-menu     [-OK] [-c target-client] [-t target-pane] \
                      [-T title] [-x pos] [-y pos] name key command ...
```

### Worked examples (EOS-flavored)

```bash
# Start headless agent session sized for log scraping
tmux -L eos new-session -d -s claude -x 220 -y 50 -c /opt/OS

# Run a command in the new session
tmux -L eos send-keys -t claude 'python3 -m eos_ai.cognitive_loop' Enter

# Capture last 500 lines of scrollback for inspection
tmux -L eos capture-pane -t claude:0.0 -p -S -500 > /tmp/claude.out

# Continuous logging
tmux -L eos pipe-pane -t claude:0.0 'cat >> /var/log/claude-pane.log'
```

## Pagination Patterns

N/A — tmux has no paginated resources. All `list-*` commands return the full
set synchronously. The closest concept is scrollback: `capture-pane -S -N -E M`
lets you page through the per-pane history buffer by line offset. `history-limit`
(default 2000) bounds it. For programmatic iteration just call `list-panes -a`
or `list-sessions` once and parse `-F` output.

## Rate Limits

N/A — tmux is a local process talking to a UNIX socket. There is no quota, no
throttle, no API budget. The practical bound is socket throughput (tens of
thousands of commands/sec) and `pane-active-border-style` hook storms if you
bind expensive hooks. `status-interval` (default 15s) controls how often the
status bar re-runs any `#(shell)` fragments — effectively a poll rate, not a
rate limit.

## Error Codes and Recovery

tmux returns nonzero exit and writes a human-readable error to stderr. There
are no numeric error codes; you grep strings or test `exit $?`.

| Stderr string | Cause | Recovery |
|---|---|---|
| `no server running on /tmp/tmux-$UID/default` | socket mismatch or server dead | check `/tmp/tmux-*`, pin `-L name` |
| `can't find session: X` | typo or wrong socket | `tmux ls` with the right `-L` |
| `duplicate session: X` | `new-session -s X` when X exists | use `-A` for idempotent |
| `open terminal failed: not a terminal` | attached `new-session` from cron/systemd | add `-d` |
| `can't find pane` | pane already died | check `#{pane_dead}` via `display-message` |
| `lost server` | server crashed mid-command | re-spawn, lose in-memory state |
| `ambiguous option` / `unknown option` | tmux version mismatch with config | check `tmux -V`, gate with `if-shell` |
| `no current client` | running from script, no attached client | target explicitly with `-t` |

Recovery recipe for wedged server:

```bash
tmux -L eos list-clients -t hung_session
tmux -L eos detach-client -s hung_session
PID=$(tmux -L eos display-message -p -t hung_session:0.0 '#{pane_pid}')
kill -CONT $PID || kill -9 $PID
tmux -L eos respawn-pane -k -t hung_session:0.0
```

Nuclear option:

```bash
pkill -9 -f 'tmux: server'
rm -rf /tmp/tmux-$UID    # only if you're sure no other tmux is yours
```

## SDK Idioms

The canonical "SDK" is the `tmux` binary itself — every interactive command
is also a shell verb. For Python, **libtmux** (0.52+) wraps the command
surface with a proper ORM-style object model (`Server → Session → Window →
Pane`). Idioms:

```python
import libtmux
server = libtmux.Server(socket_name='eos')
session = server.sessions.get(session_name='claude')
pane = session.windows[0].panes[0]
pane.send_keys('python3 -m eos_ai.orchestrator', enter=True)
output = pane.capture_pane(start=-500)  # last 500 lines
```

Pure-shell idiom for EOS scripts:

```python
import subprocess
def tmux(*args):
    return subprocess.check_output(['tmux', '-L', 'eos', *args]).decode()

panes = tmux('list-panes', '-a', '-F',
             '#{session_name}\t#{pane_id}\t#{pane_pid}\t#{pane_current_command}')
for line in panes.strip().splitlines():
    sess, pid_pane, pid, cmd = line.split('\t')
```

Rules:

1. Always parse `-F` format output with a tab or null delimiter you control.
   Never grep the default human-readable `list-sessions` layout.
2. Always target by `%pane_id` / `@window_id` / `$session_id` in long-running
   scripts. These IDs are server-lifetime stable. Indexes change under
   `renumber-windows`.
3. Every shell command you send needs an explicit `Enter` (or `C-m`) as a
   separate argument. Forgetting it is the #1 scripting bug.
4. Use `has-session -t X` before `new-session`, or use `new-session -A -s X`
   for idempotent create-or-attach.

## Anti-Patterns

1. **`tmux new-session` without `-d` in scripts.** Blocks on a TTY, errors
   under cron/systemd. Always `-d`.
2. **`send-keys 'cmd'` without `Enter`.** Text sits at the prompt. The agent
   looks frozen, nothing submitted.
3. **Sending prefix sequences from scripts.** Never `send-keys C-b c` to make
   a window. Use `tmux new-window -t sess`. Prefix is for humans, commands are
   for scripts.
4. **Nesting tmux.** Every prefix becomes a chord. Use `-L inner` on a second
   socket or rebind the inner prefix.
5. **Relying on `$TMUX`.** Per-shell, stripped by `sudo`, never set in cron.
   Don't branch on it.
6. **Wrong socket confusion.** `tmux ls` as a different user or without `-L
   name` reports "no sessions" when sessions exist elsewhere. Each socket is
   an independent server.
7. **Parsing human output.** Always use `-F` with explicit fields.
8. **Omitting `-x`/`-y` on detached sessions.** Defaults to 80x24, log lines
   wrap, `capture-pane` is mangled. Set `-x 200 -y 50` for log scraping.
9. **`kill-server` to clean up one session.** Nukes every session on that
   socket. Use `kill-session -t name`.
10. **Hardcoding window/pane indexes.** `mysess:0.0` breaks the moment
    someone enables `renumber-windows` or `base-index 1`. Use `%paneid`.
11. **Long blocking commands in `run-shell` from a hook.** Blocks the server.
    Use `run-shell -b` (background).
12. **Unpinned version assumptions.** Format strings like `#{e|+:...}` won't
    parse on tmux 2.x. Gate with `if-shell '[ ... ]'`.
13. **Leaving `synchronize-panes on` and walking away.** Next keystroke goes
    to every pane. `rm -rf` disaster.

## Data Model

Hierarchy: **server → sessions → windows → panes**. One server per socket.
Multiple clients can attach to the same session (shared view) or to different
sessions on the same server.

### IDs (server-lifetime stable)

- Session: `$0`, `$1`, ...
- Window:  `@0`, `@1`, ...
- Pane:    `%0`, `%1`, ...

### Target syntax

`-t target` accepts:
- `session` — `mysess`, `$3`, `=mysess` (exact match), `~` last
- `session:window` — `mysess:1`, `mysess:editor`, `@5`
- `session:window.pane` — `mysess:1.0`, `%7`
- Special: `{last}`, `{next}`, `{previous}`, `{top}`, `{bottom}`, `{left}`,
  `{right}`, `{up-of}`, `{mouse}`, `{marked}`

Direct ID form (`%7`) is SAFEST in scripts — it cannot be ambiguous.

### Session groups

`tmux new-session -t existing` creates a new session that shares windows with
`existing`. Same windows, independent current-window. Used for multi-attach
with different views. Killing one does not kill the group.

### Linked windows

`link-window -s src -t dst` makes a window object appear in multiple sessions.
Edits propagate. `unlink-window` removes one link.

### Detached sessions

Sessions persist while the server is alive with zero attached clients. SSH
disconnect → server keeps running → `tmux attach -t name` later. This is the
entire reason tmux exists for EOS.

### Format variables (common)

```
#{session_name}      #{session_id}      #{session_attached}
#{session_windows}   #{session_created} #{session_activity}
#{window_name}       #{window_id}       #{window_index}
#{window_active}     #{window_panes}    #{window_layout}
#{pane_id}           #{pane_index}      #{pane_pid}
#{pane_current_command}                 #{pane_current_path}
#{pane_tty}          #{pane_width}      #{pane_height}
#{pane_in_mode}      #{pane_dead}       #{pane_dead_status}
#{pane_synchronized} #{client_name}     #{client_tty}
#{host}              #{host_short}
```

Format operators (3.0+):

```
#{?cond,true,false}               # ternary
#{==:a,b}                         # equality
#{m:glob,str}                     # glob match
#{s/pat/rep/:var}                 # regex substitution
#{||:a,b}  #{&&:a,b}              # boolean
#{e|+:1,2}                        # arithmetic
#{E:option}                       # expand option through format
#{T:option}                       # expand + run as strftime
```

## Webhooks and Events

N/A for network webhooks. tmux's event system is local: **hooks**. You bind
commands to named lifecycle events.

```
set-hook -g session-created     'run-shell "/usr/local/bin/notify-session"'
set-hook -g pane-died           'respawn-pane -k'
set-hook -g client-attached     'refresh-client -S'
set-hook -g alert-activity      'run-shell "logger activity in #{window_name}"'
```

Available hooks (3.5+): `client-attached`, `client-detached`, `client-resized`,
`client-session-changed`, `client-light-theme`, `client-dark-theme`,
`pane-died`, `pane-exited`, `pane-focus-in`, `pane-focus-out`,
`pane-set-clipboard`, `pane-title-changed`, `session-created`, `session-closed`,
`session-renamed`, `session-window-changed`, `window-linked`, `window-renamed`,
`window-unlinked`, `alert-activity`, `alert-bell`, `alert-silence`,
`command-error`.

Hook commands run via `run-shell` execute synchronously on the server thread
— keep them fast or background them with `run-shell -b`.

For cross-pane synchronization use `wait-for`:

```bash
# Outer script blocks until inner pane signals
tmux send-keys -t build 'make && tmux wait-for -S build-done' Enter
tmux wait-for build-done
```

## Limits

- **history-limit** default: **2000** lines per pane. Set `set -g history-limit 100000`
  for log scraping. RAM cost ~1KB/line/pane.
- **Terminal resize**: when a client attaches/detaches, the window is resized
  to the smallest attached client unless `aggressive-resize on` or
  `window-size manual|latest`. Headless: pin with `-x COLS -y ROWS` on
  `new-session`.
- **UTF-8**: tmux 2.2+ auto-detects via locale. `LANG=*.UTF-8` or pass `-u`.
- **Color depth**: `default-terminal "tmux-256color"` + `terminal-overrides ",*256col*:Tc"`
  (or `terminal-features "*:RGB"` on 3.2+) for 24-bit.
- **Pane size**: minimum 1x1 after borders/status. Splits below min fail
  silently or produce unusable panes.
- **Scrollback memory**: `clear-history -t target` flushes a pane's buffer but
  does not immediately release RSS (allocator holds pages).
- **Practical ceilings**: thousands of windows per session, hundreds of panes
  before `list-panes -a` degrades.

## Cost Model

N/A — tmux is free, open source (ISC/BSD), and runs locally. There is no
billing dimension. The only cost is server RAM (mostly scrollback) and CPU
for status bar `#(shell)` fragments running every `status-interval` seconds.
Budget aggressively: cache expensive status fragments, keep `status-interval`
at 5 or higher, and never put a git/kubectl/aws call in the status bar
uncached.

## Version Pinning

Check version: `tmux -V` → e.g. `tmux 3.5a`.

Current stable line as of 2026-04: **tmux 3.5a / 3.6a**. 3.5a (late 2024) and
3.6a (2025) are the practical baselines.

Distro shipping versions:

- Ubuntu 20.04 LTS: tmux 3.0a
- Ubuntu 22.04 LTS: tmux 3.2a
- Ubuntu 24.04 LTS: tmux 3.4
- Debian 12 (bookworm): tmux 3.3a
- Debian 13 (trixie): tmux 3.4
- RHEL 9: tmux 3.2a
- macOS Homebrew: tracks latest stable

Version-breaking features to gate:

- `display-popup` requires 3.2+
- `pane-title-changed`, `client-light-theme`, `command-error` hooks require 3.5+
- `terminal-features` option: 3.2+ (prefer over `terminal-overrides`)
- Format `#{e|+:...}` arithmetic: 3.0+
- `set -p` pane-scoped options: 3.1+
- Extended keys mode 2 (`modifyOtherKeys`): 3.5+

Gate in `.tmux.conf`:

```tmux
if-shell 'tmux -V | awk "{exit !(\$2 >= 3.2)}"' \
  'bind C-p display-popup -E -w 80% -h 80% "..."'
```

Build from source (if distro lags):

```bash
sudo apt install -y libevent-dev libncurses-dev build-essential bison pkg-config
git clone https://github.com/tmux/tmux.git
cd tmux && git checkout 3.5a
sh autogen.sh && ./configure && make
sudo make install
```

For EOS: pin expectation at `>= 3.2` (popup) and `>= 3.5` where hooks matter.
The VPS at /opt/OS is currently on the Ubuntu 24.04-shipped 3.4; upgrade to
3.5a is reasonable when a hook feature is needed.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

tmux was started by Nicholas Marriott in 2007 inside the OpenBSD ecosystem,
explicitly because GNU screen had become a barnacled, hard-to-maintain codebase
with a permissive but inconsistent license, opaque internals, and a culture
that resisted change. tmux was a clean-room rewrite under the ISC/BSD license
with three non-negotiable design goals:

1. **A real client/server split.** screen mostly pretends to be client/server;
   tmux is. There is one binary — the first invocation in a context spawns a
   server daemon, every subsequent invocation is a thin client that speaks to
   the server over a UNIX domain socket in `$TMPDIR` (default
   `/tmp/tmux-<uid>/default`). This gives you:
   - true detach/reattach with zero state loss because the server owns the PTYs
   - the ability to drive tmux from scripts (`send-keys`, `capture-pane`) with
     no terminal attached — this is the foundation EOS relies on
   - multiple simultaneous clients on the same session with independent views
     (the basis of pair programming and grouped sessions)
   - clean death semantics: kill the server, every session dies together; kill
     a client, the server keeps running

2. **A consistent, orthogonal command language.** Every interactive keybinding
   is shorthand for a command you can also run from `:` or the shell via `tmux
   <cmd>`. There is no "scriptable mode" vs "interactive mode" — they are the
   same surface. This is why `send-keys`, `display-message`, `if-shell`, and
   `run-shell` exist as first-class verbs. The whole thing is a small
   Lisp-shaped command system wearing a terminal multiplexer costume.

3. **Format strings as a first-class language.** Around 2014 tmux grew a small
   templating language (`#{...}`) that computes strings from session state
   inside any command that takes a format. It is the engine behind status
   bars, `choose-tree` views, `display-message`, and conditional styling — and
   the single most underused feature in the product.

Tradeoffs vs alternatives:

- **vs GNU screen.** tmux wins on architecture, command consistency, native
  vertical splits, UTF-8 handling, and active maintenance. screen wins on
  ubiquity in ancient enterprise images.
- **vs zellij.** zellij is Rust with a friendlier first run, supports WASM
  plugins, and floating panes out of the box. tmux wins on stability, resource
  footprint, command surface for scripting, and plugin long tail. zellij is
  better for learning; tmux is better for *building on*.
- **vs WezTerm/Kitty multiplexing.** Terminal-bound — kill the terminal, kill
  the state. tmux survives SSH disconnects and reboots (with resurrect). The
  right answer is usually "both": WezTerm/Kitty locally, tmux on the remote.
- **vs mosh.** Different layer. mosh fixes the transport (UDP, predictive
  echo, roaming). tmux fixes the session. Combo: `mosh vps -- tmux attach`.

What tmux is explicitly NOT: a window manager, a terminal emulator, a shell,
or an IDE. The core is intentionally narrow.

## Problem-Solution Map and Hidden Capabilities

Things 95% of users never discover:

- **Hooks (`set-hook`).** Named events on session/window/pane lifecycle.

  ```
  set-hook -g session-created 'run-shell "~/bin/tmux-session-init.sh"'
  set-hook -g pane-died       'respawn-pane -k'
  set-hook -g client-attached 'refresh-client -S'
  ```

  This is how you build self-healing layouts and automatic logging without
  any external supervision.

- **`display-popup` (3.2+).** Floating pane running an arbitrary command that
  disappears on exit. The right way to build "command palettes" inside tmux:

  ```
  bind C-p display-popup -E -w 80% -h 80% \
    "tmux list-sessions -F '#{session_name}' | fzf | xargs tmux switch-client -t"
  ```

  `-E` closes on exit, `-B` removes the border, `-d` sets cwd. This feature
  obsoletes 90% of "tmux launcher" plugins.

- **`display-menu`.** Right-click menus, fully customizable, format strings
  inside labels. The default `MouseDown3StatusDefault` menu is defined this
  way and you can replace it.

- **Format string language (`#{...}`).** A real expression language with
  conditionals, string substitution, comparisons, regex, and pane/window/session
  variables.

  ```
  #{?client_prefix,PREFIX,}
  #{s|^.*/||:pane_current_path}
  #{?#{==:#{session_windows},1},solo,multi}
  #{E:status-left}        # expand an option's value again
  #{T:status-left}        # expand and run as strftime
  ```

- **`if-shell` and `run-shell`.** Run arbitrary shell at config-load time,
  branch on exit code. How you write a `.tmux.conf` that adapts to version,
  OS, hostname, or SSH state.

  ```
  if-shell '[ "$(uname)" = Darwin ]' \
    'set -g default-command "reattach-to-user-namespace -l zsh"'
  ```

- **Marked panes (`select-pane -m`).** Mark a pane as "the" pane; later
  commands like `join-pane -s '{marked}'` reference it. Building block for
  "drag this pane into that window" workflows.

- **`pipe-pane`.** Tee everything a pane writes to a file or program while the
  user keeps using it. Indispensable for AI agents.

  ```
  pipe-pane -o 'cat >> ~/.tmux-logs/#S-#W-#P.log'
  ```

  Combine with a `pane-focus-in` hook to start logging automatically.

- **`respawn-pane` / `respawn-window`.** Restart a dead command in place,
  preserving geometry. With `-k` it kills a still-running one. Plus a
  `pane-died` hook = a poor man's supervisor.

- **`choose-tree -F`.** The session/window picker accepts a format. Make it
  show last activity, cwd, git branch, anything format-stringable.

- **`command-prompt -I`.** Pre-fill the prompt with text. Combined with `-p`
  for the label and `%%` for substitution, builds interactive commands without
  a popup.

- **Session groups.** `new-session -t existing` shares windows but gives each
  session its own current-window. Two attached clients can be on different
  windows of "the same" session. Underused for pair programming.

- **Linked windows.** `link-window -s src:1 -t dst:` makes window 1 of `src`
  appear in `dst` too. Edits propagate. Useful for shared dashboards across
  sessions.

- **`set-environment` / `update-environment`.** The server holds an environment
  that new panes inherit. `update-environment` controls which vars refresh
  from a re-attaching client — the fix for "my SSH agent forwarding died on
  reattach" (keep `SSH_AUTH_SOCK` in `update-environment`).

- **`wait-for`.** Barrier primitive. One pane runs `wait-for foo`, another
  runs `wait-for -S foo` to release. Cross-pane synchronization without
  polling. Also supports `-L/-U` for lock/unlock semantics.

## Operational Behavior and Edge Cases

- **`escape-time`.** Default 500 ms. tmux waits that long after `Esc` to see
  if it's an escape sequence. Inside Vim/Neovim `<Esc>` feels laggy. Always:

  ```
  set -sg escape-time 0
  ```

  `-s` = server level, one of maybe five options that lives there.

- **`send-keys` and readline state.** `send-keys` writes bytes to the PTY. It
  does not know whether the foreground process is bash, vim, or a TUI. If you
  `send-keys 'echo hi' Enter` while the user is in vim insert mode, you just
  typed "echo hi" into their buffer. Always check `pane_in_mode` first or use
  `respawn-pane` if you need a clean state.

- **`clear-history` does not free RAM immediately.** Clears scrollback but
  tmux's allocator holds the pages. For an immediate drop, detach all clients
  and re-attach, or kill the session.

- **`renumber-windows` reorders window *numbers*, not IDs.** `%N` and `@N` are
  server-lifetime stable. Session-qualified numbers (`sess:0`, `sess:1`) are
  what renumber touches. Scripts pinned to numbers silently retarget; scripts
  pinned to `%paneid` don't.

- **`synchronize-panes`.** Toggle with `setw synchronize-panes`. Every
  keystroke goes to every pane — including destructive ones. Forgetting to
  turn it off and typing `rm -rf` is the canonical tmux disaster story. Bind
  it with a visible status indicator:
  `set -g status-right '#{?pane_synchronized,#[bg=red]SYNC#[default] ,}'`.

- **`capture-pane` and carriage returns.** Reads the visible buffer. Anything
  redrawn in place with `\r` (tqdm bars, spinners, `tput cuu`) shows up as the
  final state, not the history. To capture the raw byte stream, use
  `pipe-pane` from the start. **This is the #1 surprise for people scraping
  AI agent output** — and directly relevant to EOS's memory-ingestion loop.

- **TMPDIR socket gotcha.** Socket lives at `$TMPDIR/tmux-$UID/default`. If
  TMPDIR differs between your shell and your cron job (very common — systemd
  sets a private one), `tmux attach` from cron will not find the interactive
  server and will start a second one. **Always pin the socket**: `tmux -L eos`
  or `tmux -S /tmp/tmux-eos.sock`. EOS convention: `-L eos`.

- **Nested tmux.** Two reasonable patterns: rebind the inner prefix
  (`set -g prefix C-a`) or use the outer's `send-prefix`. Some set
  `TERM=tmux-256color` for the inner; most just don't nest.

- **`default-terminal` and 256/truecolor.** Set `default-terminal
  "tmux-256color"` and `set -ga terminal-overrides ",*256col*:Tc"`. Without
  `Tc`, Neovim themes wash out. The `-ga` (greedy append) matters — `-g`
  overwrites.

- **`exit-empty` and `exit-unattached`.** Server lifecycle. By default the
  server exits when the last session dies. Set `exit-empty off` to keep it
  alive for headless workflows where you `kill-session` then re-create.

- **Mouse mode.** `set -g mouse on` enables globally but takes over text
  selection. Selection now goes through copy mode. Hold Shift while selecting
  to bypass and use native terminal selection. Teach this to anyone you
  onboard.

- **Capture quirk.** If a pane was just created and nothing has been written,
  `capture-pane` may return only the first line. Sleep briefly or send a
  newline before capturing.

- **Server logs.** Silent by default. Start with `-v` / `-vv` / `-vvvv` to
  write protocol/event logs (`tmux-server-*.log`, `tmux-client-*.log` in the
  CWD where you started the server). Use `-vvvv` only for narrow repros.

- **`tmux info`.** Dumps server version, build options, every pane, every
  window, current state. First command to grab when filing a bug or diagnosing
  a weird client.

## Ecosystem Position and Composition

Composes well with:

- **SSH.** The original killer pairing. `ssh vps -t tmux new -A -s main`
  attaches if `main` exists, creates it otherwise. `-t` forces a TTY.
- **mosh.** `mosh vps -- tmux new -A -s main`. mosh handles network flake,
  tmux handles persistence. Belt and suspenders.
- **Neovim.** `christoomey/vim-tmux-navigator` lets `<C-h/j/k/l>` jump between
  vim splits and tmux panes. Single best reason to learn tmux as a Neovim
  user.
- **fzf.** `fzf-tmux` runs fzf in a popup. Pair with `list-sessions`,
  `list-windows`, or git branches for instant pickers.
- **direnv.** Each pane is its own shell, direnv loads per-pane cleanly.
- **TPM (Tmux Plugin Manager).** `set -g @plugin '...'` + `prefix I`. Small
  but high-quality plugins: tmux-resurrect, tmux-continuum, tmux-yank,
  tmux-fzf, tmux-fingers, catppuccin themes.
- **tmuxp / tmuxinator.** Declarative YAML/Ruby session layouts. tmuxp is
  Python and plays nice with EOS.
- **Claude Code, Aider, codex, Cursor CLI.** All benefit from a named detached
  session. This IS the EOS pattern.
- **systemd.** tmux servers make excellent `Type=forking` user services.

Composes badly with:

- **Other multiplexers in the same terminal.** WezTerm, Kitty, Alacritty with
  multiplexer features fight tmux for `C-b`/`C-a` and for resize events. Pick
  one layer.
- **Terminals that intercept `Ctrl-` chords.** VS Code integrated terminal
  historically swallowed several.
- **Hardware serial tools or gdb frontends** needing specific terminal
  capabilities — tmux presents a `screen-256color` PTY by default which lies
  about a few things. Set `default-terminal` carefully.
- **Nested tmux without prefix rebind.** Covered above. Painful.

## Trajectory and Evolution

Release rhythm is roughly one significant release per year, very stable.

- **2.x era (2015–2019).** Format string language matured. `command-prompt`
  improvements. Mouse mode rewrite in 2.1 (breaking).
- **3.0 (2020).** Format string and command parser rewrite. Internal cleanup
  that made later features possible. Breaking changes around option
  inheritance. Pane zoom (`prefix z`).
- **3.1 (2020).** `{top}`/`{bottom}` target tokens, `copy-mode -e`, pane-scoped
  options (`set -p`).
- **3.2 (2021).** `display-popup` and `display-menu` shipped. This is the
  release that turned tmux into a UI platform. `terminal-features` option.
- **3.3 (2022).** Better mouse handling, `extended-keys` option, new pane
  border styling.
- **3.4 (2024).** `extended-keys` mode 1, more format vars (`pane_last`,
  `pane_marked_set`), ACL menus, large bug-fix release.
- **3.5 / 3.5a (2024).** Extended keys mode 2 (xterm modifyOtherKeys). New
  hooks: `pane-title-changed`, `client-light-theme`, `client-dark-theme`,
  `command-error`. Some key-name representation changes (`C-BTab` no longer
  same as `C-S-Tab`) — old configs may need updating.
- **3.6a (2025).** Crash/hang fixes for malformed format strings, extended-key
  polish.

Maintenance status: Nicholas Marriott still actively maintains. The project
is not dying — it is *finished* the way good Unix tools get finished. Bug
fixes flow steadily, new features land conservatively.

Competitive landscape:

- **zellij** is the only credible challenger. Better for new users, worse for
  building automation on top. Command surface smaller, changes more often.
- **WezTerm multiplexing** excellent locally, no answer for "ssh into a box
  that doesn't run WezTerm." Complementary, not a replacement.
- **Kitty tabs/windows** great locally, irrelevant remote.

5-year bet: tmux is the safest long-horizon bet for any workflow that must
survive SSH, run on stranger boxes, and be scripted by tools that aren't
humans. Invest in tmux for the server side. Pick whatever terminal you like
client side.

## Conceptual Model and Solution Recipes

**Mental model.** A tmux server is a long-lived process holding a tree:
`server → sessions → windows → panes`. Each pane owns a PTY and a child
process. Clients are ephemeral views; they attach to a session and render its
current window. Detaching a client does not touch the tree. Killing the server
takes the whole tree down. Everything you can do interactively is also a
command verb you can call from any other process by talking to the same
socket.

**Server is the truth, client is the camera.** Internalize that and every
confusing tmux behavior becomes obvious.

### Recipe A — Long-running AI agent in tmux (the EOS pattern)

```bash
SESSION=eos-agent
SOCK_NAME=eos
LOG=~/.tmux-logs/$SESSION-$(date +%F).log
mkdir -p ~/.tmux-logs

tmux -L $SOCK_NAME new-session -d -s $SESSION -n claude -x 220 -y 50 \
  "cd /opt/OS && claude-code --resume"

tmux -L $SOCK_NAME pipe-pane -t $SESSION:claude.0 -o "cat >> $LOG"
tmux -L $SOCK_NAME set-hook  -t $SESSION pane-died "respawn-pane -k"

# Reattach later from anywhere
tmux -L $SOCK_NAME attach -t $SESSION
```

The pinned socket means cron, systemd, and your shell all find the same
server. The hook respawns the pane on crash. The `pipe-pane` gives you a
permanent log while the user keeps typing.

### Recipe B — Parallel agent orchestration (4 panes, synchronized start)

```bash
SESSION=eos-swarm
tmux -L eos new-session -d -s $SESSION -n swarm -x 240 -y 60
tmux -L eos split-window -h -t $SESSION:swarm
tmux -L eos split-window -v -t $SESSION:swarm.0
tmux -L eos split-window -v -t $SESSION:swarm.2
tmux -L eos select-layout -t $SESSION:swarm tiled

for i in 0 1 2 3; do
  tmux -L eos send-keys -t $SESSION:swarm.$i \
    "python3 /opt/OS/scripts/worker.py --shard $i" Enter
done

tmux -L eos attach -t $SESSION
```

For a true synchronized start: send commands without `Enter`, toggle
`synchronize-panes`, press `Enter` once, toggle back off.

### Recipe C — Session-per-project (shell function)

```bash
mux() {
  local name=${1:-$(basename "$PWD")}
  if tmux has-session -t "$name" 2>/dev/null; then
    tmux attach -t "$name"
  else
    tmux new-session -d -s "$name" -c "$PWD"
    tmux send-keys -t "$name" 'nvim .' Enter
    tmux split-window -h -t "$name" -c "$PWD"
    tmux split-window -v -t "$name" -c "$PWD"
    tmux select-pane  -t "$name".0
    tmux attach -t "$name"
  fi
}
```

### Recipe D — Headless bot under systemd

```ini
# /etc/systemd/system/eos-bot.service
[Unit]
Description=EOS bot inside tmux
After=network.target

[Service]
Type=forking
User=eos
Environment=TMUX_TMPDIR=/run/eos
ExecStart=/usr/bin/tmux -L eos new-session -d -s bot \
  '/opt/OS/services/run-bot.sh'
ExecStop=/usr/bin/tmux -L eos kill-session -t bot
Restart=on-failure
KillMode=none

[Install]
WantedBy=multi-user.target
```

`-L eos` pins the socket so operators can `tmux -L eos attach -t bot` and
watch the bot live without disturbing it. `KillMode=none` prevents systemd
from SIGKILL'ing the children. For user services add
`loginctl enable-linger $USER`.

### Recipe E — Session switcher popup + fzf

```tmux
bind C-j display-popup -E -w 60% -h 40% "
  tmux list-sessions -F '#{session_name}' \
  | grep -v \"^$(tmux display -p '#S')\$\" \
  | fzf --reverse \
  | xargs -r tmux switch-client -t
"
```

### Recipe F — Scrape an agent's last N lines into Python

```python
import subprocess
def scrape(session, window='0', pane='0', lines=500):
    out = subprocess.check_output([
        'tmux', '-L', 'eos', 'capture-pane',
        '-t', f'{session}:{window}.{pane}',
        '-p', '-S', f'-{lines}', '-J'
    ]).decode()
    return out
```

## Industry Expert and Cutting-Edge Usage

- **AI coding agents inside tmux.** This is the dominant new pattern in
  2025–2026. Claude Code, Aider, Cursor CLI, codex — all benefit from living
  in a named detached tmux session because (a) the agent run outlasts any SSH
  session, (b) you can `pipe-pane` the whole conversation to a logfile for
  audit and replay, (c) you can `capture-pane` the visible state to feed back
  into another agent. EOS's "Claude Code runs 24/7 in tmux" is the canonical
  version. Trick people miss: rebind `prefix` to something the agent will
  never emit (`C-Space` is popular) so agent output never accidentally
  triggers tmux commands.

- **`display-popup` as a generic UI primitive.** Power users treat popup as a
  command palette substrate. fzf for sessions, lazygit in a popup, k9s in a
  popup, scratchpad notes, even nvim in a popup for "open fast, close fast."
  Bind a dozen and tmux becomes a launcher.

- **Declarative session config.** tmuxp (Python, YAML) and tmuxinator (Ruby,
  YAML) have both stabilized. Commit a `.tmuxp.yaml` per project and bootstrap
  with a single command. EOS could use this for its standard developer
  layout.

- **tmux-resurrect + tmux-continuum.** resurrect snapshots the tree to disk;
  continuum runs resurrect on a timer and restores on tmux start. Surviving a
  VPS reboot becomes one line: `set -g @continuum-restore 'on'`. Caveat:
  restores commands, not process state. An agent gets relaunched, not resumed
  mid-thought. Pair with the agent's own resume mechanism (Claude Code's
  `--resume`).

- **Status bar as dashboard.** Practitioners run real format strings: git
  branch via `#(cd #{pane_current_path} && git branch --show-current)`,
  kubectl context, current AWS profile, battery, weather, GitHub notification
  count. **Cache aggressively** — `status-interval 5` means `#(...)` runs
  every 5 seconds in every client.

- **Format string tricks worth stealing:**

  ```
  #{?client_prefix,#[reverse]PREFIX#[noreverse],}
  #{s|$HOME|~|:pane_current_path}
  #{?#{m:*nvim*,#{pane_current_command}},,#[fg=red]}
  #{T:status-left}
  #{E:@my_var}
  ```

- **The `mux-everything` pattern.** Every dev session, even local, runs inside
  tmux. Uniform muscle memory, free persistence, one keybinding set across
  local and remote, popup launcher as universal entry point. Cost: one
  abstraction layer. Benefit: workflow no longer cares whether you're local
  or on a VPS.

- **tmux + Claude Code patterns:**
  1. **Named session per agent role.** `claude-architect`, `claude-builder`,
     `claude-reviewer`. Switch with the popup picker.
  2. **Pipe-pane to JSONL** that another script tails for observability. EOS
     could emit these into Neon directly.
  3. **`capture-pane -pS -` into a second agent** that summarizes or
     critiques the first. The "two agents in two panes" pattern.
  4. **Dedicated interrupt key.** Bind a tmux key to
     `send-keys -t claude-builder Escape` to yank the agent out of a runaway
     action without switching panes.
  5. **`set-hook -g pane-died` for agent crashes** that posts to a webhook so
     a dead agent pages you instead of silently leaving an empty pane.

## EOS Usage Patterns

tmux is the substrate that makes 24/7 agent operation possible on a single
VPS (100.77.233.50, /opt/OS) without inventing a new supervisor. It is not a
convenience — it is load-bearing infrastructure.

Canonical EOS conventions:

- **Socket pin: `-L eos`.** Every script, every systemd unit, every operator
  command uses `-L eos` so cron, the founder's SSH shell, and systemd units
  all talk to the same server. Never rely on the default socket.
- **Claude Code lives in tmux 24/7.** A detached session named `claude` on
  socket `eos` runs Claude Code with `--resume`. Founder attaches from
  Termius (iPhone), code-server (iPad), or VSCode (Windows) via SSH. Detaching
  never interrupts the agent.
- **Headless sizing.** Every `new-session` in EOS scripts passes `-x 220 -y 50`
  so `capture-pane` gives clean unwrapped log lines for memory ingestion.
- **`pipe-pane` to `~/.tmux-logs/`.** Every agent pane logs continuously to a
  dated file. A separate tail loop feeds the last N lines into
  `eos_ai/memory.py` for scrollback-aware context.
- **`capture-pane -S -N` into Python.** Used by skill verification and
  debugging flows — scrape the visible scrollback, parse with Python, feed to
  the cognitive loop.
- **Multiple agent panes in one window.** Parallel workers share a window via
  the swarm recipe. `synchronize-panes` toggled only for explicit
  broadcast-then-execute operations.
- **systemd + `Type=forking` + `-L eos`.** Long-lived services
  (os-discord, os-bot, os-monitor, os-webhook) run inside tmux panes so
  operator can attach and inspect live. `KillMode=none` + `loginctl
  enable-linger`.
- **`pane-died` hook for auto-respawn.** Combined with `respawn-pane -k` for
  crash recovery without external supervision for non-critical panes. For
  critical services defer to systemd `Restart=on-failure`.
- **Prefix remapping.** Consider `C-Space` as prefix for agent sessions so
  accidental agent output never fires tmux commands.

Deploy/verification rule: after any tmux-touching script change, run

```bash
tmux -L eos ls                                   # sessions up?
tmux -L eos list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_current_command} pid=#{pane_pid}'
```

before declaring done. Never assume — inspect the tree.

## Gotchas

1. **Default socket trap.** `tmux ls` from cron/systemd vs your shell hits
   different sockets. Always `-L eos`. If you see "no server running" and
   know one exists, you're on the wrong socket.
2. **`new-session` without `-d` under cron/systemd.** `open terminal failed:
   not a terminal`. Always `-d`.
3. **`send-keys` without `Enter`.** Text sits at the prompt forever, agent
   looks frozen. Always pass `Enter` as a separate token.
4. **Default 80x24 on detached sessions.** Wraps log lines, mangles
   `capture-pane`. Always `-x 220 -y 50` for EOS scraping.
5. **`history-limit` default 2000.** Not enough for log scraping. Set
   `history-limit 100000` globally.
6. **`escape-time` default 500 ms.** Makes vim Esc laggy. `set -sg escape-time 0`.
7. **`capture-pane` only sees the final state of `\r`-redrawn lines.** Spinners
   and progress bars aren't in scrollback. Use `pipe-pane` from the start.
8. **`capture-pane` on freshly spawned pane returns one line.** Sleep briefly
   or send a newline first.
9. **`synchronize-panes` left on.** Next `rm -rf` is broadcast. Bind with a
   visible status indicator.
10. **`renumber-windows` silently retargets scripts pinned to window numbers.**
    Use `%paneid` / `@windowid` in scripts.
11. **`kill-server` kills every session on the socket.** Use `kill-session -t
    name` for surgery.
12. **Nested tmux without rebind.** Prefix collisions. Rebind inner or use a
    second socket (`-L inner`).
13. **Hooks running blocking `run-shell` commands.** Blocks the server. Use
    `run-shell -b`.
14. **`clear-history` doesn't immediately free RSS.** Detach all clients and
    reattach, or kill the session, for an immediate drop.
15. **`update-environment` forgotten.** `SSH_AUTH_SOCK` goes stale on
    reattach, agent forwarding dies. Add `SSH_AUTH_SOCK` to the list.
16. **systemd `KillMode` default.** Without `KillMode=none`, systemctl stop
    SIGKILLs all children. Always set `KillMode=none` for tmux units.
17. **`loginctl enable-linger` missing.** User services die at logout. Run it
    once per user.
18. **Format string version skew.** `#{e|+:...}` and similar require 3.0+.
    Gate with `if-shell '[ ... ]'` or pin version in the skill.
19. **Parsing human `tmux ls` output.** Use `-F` with explicit delimiters,
    never the default text format.
20. **Targeting by name when multiple sessions share a prefix.** `-t eos`
    resolves to the first alphabetical match. Use `=eos` for exact or `$id`.
