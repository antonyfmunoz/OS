# systemd — Best Practices and Creator-Level Intelligence

Source URL: https://www.freedesktop.org/software/systemd/man/
Version: systemd 249 (Ubuntu 22.04 LTS) / 255 (Ubuntu 24.04 LTS)
Last Researched: 2026-04-06

This is the authoritative knowledge base behind the EOS systemd tool skill.
Tier 1 covers the surface every operator needs; Tier 2 captures design
intent, hidden capabilities, and industry-expert patterns.

---

# Tier 1 — Technical Mastery

## Authentication

systemd has no user-space authentication layer of its own. Authority comes
from the kernel (UID 0) and from polkit.

- Read operations (`systemctl status`, `systemctl list-units`,
  `journalctl -u foo`) are available to any local user. Journal access for
  non-root users is granted by membership in the `systemd-journal` group.
- Write operations (`start`, `stop`, `restart`, `enable`, `daemon-reload`)
  require root OR a polkit rule granting the action
  (`org.freedesktop.systemd1.manage-units`) to the calling user.
- Editing files under `/etc/systemd/system/` requires root.
- `systemctl --user` operates on the per-UID user-instance of systemd and
  needs no privilege — the user owns their own instance.
- Remote operations via `systemctl -H user@host` use SSH for transport;
  polkit still mediates on the remote side.
- Containers: `systemctl -M container_name` enters a machinectl-registered
  container's systemd instance. Requires `CAP_SYS_ADMIN` usually.

EOS on the VPS: the deploy scripts run as root. Interactive edits from
`antony` use `sudo systemctl`. No polkit rules are configured.

## Core Operations with Exact Signatures

### systemctl lifecycle

```
systemctl start   UNIT[...]          # start now, no persistence
systemctl stop    UNIT[...]
systemctl restart UNIT[...]          # stop + start (single transaction, deps not restarted)
systemctl reload  UNIT[...]          # only works if ExecReload= is defined
systemctl reload-or-restart UNIT
systemctl kill -s SIGTERM UNIT
systemctl kill -s SIGKILL --kill-who=main UNIT
```

### Persistence

```
systemctl enable  UNIT               # creates [Install] symlinks
systemctl disable UNIT
systemctl enable  --now UNIT         # enable + start in one shot
systemctl disable --now UNIT
systemctl mask    UNIT               # symlink to /dev/null, cannot start
systemctl unmask  UNIT
systemctl reenable UNIT              # disable + enable (rewrites symlinks)
systemctl preset  UNIT               # apply vendor preset policy
```

### State queries (all return exit codes, use in scripts)

```
systemctl is-active   UNIT           # exit 0 if active
systemctl is-enabled  UNIT           # exit 0 if enabled/static
systemctl is-failed   UNIT
systemctl is-system-running          # running|degraded|starting|...
```

### Inspection

```
systemctl status UNIT                # human summary, last 10 log lines
systemctl status UNIT -n 50          # last 50 log lines
systemctl cat    UNIT                # effective unit file + all drop-ins
systemctl show   UNIT                # every property as key=value
systemctl show   UNIT -p MainPID -p ActiveState -p SubState -p NRestarts
systemctl list-units --type=service
systemctl list-units --type=service --all
systemctl list-units --type=service --state=failed
systemctl list-unit-files --type=service
systemctl list-dependencies UNIT
systemctl list-dependencies UNIT --reverse
systemctl list-dependencies UNIT --all
systemctl list-jobs
systemctl list-timers --all
```

### Editing

```
systemctl edit UNIT                  # creates drop-in override.conf in $EDITOR
systemctl edit --full UNIT           # edit full copy in /etc/systemd/system
systemctl edit --runtime UNIT        # /run, ephemeral until reboot
systemctl revert UNIT                # drop overrides, restore vendor
systemctl daemon-reload              # MANDATORY after manual edits
systemctl daemon-reexec              # re-exec systemd itself
```

### Recovery

```
systemctl reset-failed               # clear failed state on ALL units
systemctl reset-failed UNIT
```

### Global flags

- `--user` — operate on the per-user instance
- `--system` — explicit system instance (default)
- `--now` — combine with enable/disable/mask
- `--no-pager` — pipe-friendly
- `--no-block` — don't wait for the job to finish
- `-q / --quiet` — suppress info messages
- `-H user@host` — operate on a remote host via SSH
- `-M container` — operate inside a machinectl container

Target resolution: bare names get `.service` appended. Use `.timer`,
`.socket`, `.target`, `.mount`, `.path`, `.slice`, `.scope` explicitly
when the unit is not a service.

### Unit file locations (precedence, highest wins)

1. `/etc/systemd/system/` — admin overrides, edit here
2. `/run/systemd/system/` — runtime, ephemeral
3. `/usr/lib/systemd/system/` — vendor units, never edit

Drop-ins: `/etc/systemd/system/<unit>.service.d/*.conf` merged on top.
Drop-in files are sorted lexically — name them `10-`, `20-`, `90-` for
predictable ordering.

### journalctl

```
journalctl -u UNIT                          # all logs for unit
journalctl -u UNIT -f                       # tail -f
journalctl -u UNIT -n 100                   # last 100 lines
journalctl -u UNIT1 -u UNIT2                # multiple units
journalctl --since "2026-04-06 00:00:00"
journalctl --since "1 hour ago"
journalctl --since yesterday --until "1 hour ago"
journalctl -b                               # current boot
journalctl -b -1                            # previous boot
journalctl --list-boots
journalctl -u UNIT -p err                   # err (3) and worse
journalctl -u UNIT -p warning..err
journalctl -u UNIT -o cat                   # message only
journalctl -u UNIT -o json                  # machine-readable
journalctl -u UNIT -o json-pretty
journalctl -u UNIT --grep "ERROR|Exception"
journalctl _SYSTEMD_UNIT=os-bot.service _PID=12345
journalctl -k                               # kernel (dmesg)
journalctl -xeu UNIT                        # explanatory + jump to end
journalctl --disk-usage
journalctl --vacuum-time=14d
journalctl --vacuum-size=500M
journalctl --rotate
```

## Pagination Patterns

Mostly N/A — systemd is a local tool with no HTTP API. The closest
analogue is journalctl's time-and-cursor based windowing:

- `-n N` — last N entries
- `--since / --until` — time-range pagination
- `--cursor=...` — resume from a saved cursor (printed by
  `journalctl --show-cursor`). This is the right way to incrementally
  ship logs to an external store: save the cursor, exit, resume next run.
- `-r` — reverse order (newest first), useful for `| head`

## Rate Limits

systemd imposes no API rate limit (it is a local tool). **journald does
rate-limit log ingestion per service**, and this trips people up.

Defaults (in `/etc/systemd/journald.conf`):

- `RateLimitIntervalSec=30s`
- `RateLimitBurst=10000`

If a single unit logs more than `RateLimitBurst` messages in
`RateLimitIntervalSec`, excess messages are **dropped silently** and
journald emits a one-line "Suppressed N messages from service X" notice.

Mitigation:

1. Raise globally in a journald drop-in:

```
sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/rate-limit.conf <<'EOF'
[Journal]
RateLimitIntervalSec=10s
RateLimitBurst=50000
EOF
sudo systemctl restart systemd-journald
```

2. Opt out per-unit:

```
[Service]
LogRateLimitIntervalSec=0
LogRateLimitBurst=0
```

The per-unit directives take precedence over the global journald
settings for that unit.

## Error Codes and Recovery

### systemctl exit codes

- `0` — command succeeded / state query true
- `1` — generic failure / state query false
- `3` — unit is inactive/dead (for `is-active`)
- `4` — no such unit

### Symptomatic `systemctl status` lines and what they mean

| Status line | Meaning | Fix |
|---|---|---|
| `(code=exited, status=203/EXEC)` | ExecStart binary not found or not executable | Absolute path, `chmod +x` |
| `(code=exited, status=200/CHDIR)` | WorkingDirectory does not exist or unreadable | Create dir, fix perms, or remove directive |
| `(code=exited, status=217/USER)` | `User=` does not exist | Create user or fix typo |
| `(code=exited, status=226/NAMESPACE)` | Namespace setup failed (PrivateTmp etc.) | Loosen hardening, check kernel support |
| `(code=exited, status=1/FAILURE)` | Generic non-zero from your program | Read journal for actual error |
| `(code=killed, signal=TERM)` | Killed by stop or another unit | Expected on stop; else check OnFailure=/Conflicts= |
| `(code=killed, signal=KILL)` | OOM killer or TimeoutStopSec → SIGKILL | `MemoryMax=`, `dmesg \| grep -i oom`, raise TimeoutStopSec |
| `Result: watchdog` | Type=notify failed to send WATCHDOG=1 in time | Implement sd_notify keepalive or drop WatchdogSec |
| `Result: start-limit-hit` | Too many restarts in window | `systemctl reset-failed`; loosen limits; fix root cause |
| `Result: timeout` | TimeoutStartSec exceeded | Increase timeout, or fire READY=1 earlier |
| `Failed to load environment files` | EnvironmentFile path missing, no `-` prefix | Prefix `-` or create file |
| `Unit is masked` | Symlinked to /dev/null | `systemctl unmask` |
| `condition failed` | `Condition*=` returned false | Intentional skip, not failure |
| `Unit not found` | File not in search path, or no daemon-reload | Place in /etc/systemd/system/, reload |
| Stuck in `activating` forever | Wrong `Type=` | Switch type (simple vs forking vs notify) |

### Canonical debug order

1. `systemctl status UNIT` — top-line state
2. `journalctl -xeu UNIT` — recent logs with hints
3. `systemd-analyze verify /etc/systemd/system/UNIT` — syntax check
4. `systemctl list-dependencies UNIT` — dep graph
5. `systemctl show UNIT -p ExecStart -p Environment -p WorkingDirectory`
6. `systemd-run --unit=test-UNIT ... /path/to/bin` — ad-hoc transient run
7. `systemctl reset-failed UNIT && systemctl start UNIT` if stuck failed

## SDK Idioms

systemd has no official SDK. The idiomatic surfaces:

### Bash

- Check before acting: `systemctl is-active UNIT && ...`
- Deploy script pattern: `reset-failed || true; daemon-reload; restart`
- Parse properties with `systemctl show UNIT -p KEY --value`
- Parse JSON logs: `journalctl -u UNIT -o json | jq ...`
- Never grep `systemctl status` output — use `-p` and `is-*` instead

### Python

The `python3-systemd` package (Debian/Ubuntu: `apt install python3-systemd`)
provides:

```python
from systemd import daemon, journal

# Notify readiness (Type=notify)
daemon.notify("READY=1")
daemon.notify("STATUS=Connected to 5 peers")
daemon.notify("WATCHDOG=1")  # keepalive for WatchdogSec=
daemon.notify("STOPPING=1")

# Journal logging as a handler
import logging
log = logging.getLogger("os-discord")
log.addHandler(journal.JournalHandler(SYSLOG_IDENTIFIER="os-discord"))
```

Alternative without the C extension — write to `$NOTIFY_SOCKET` directly:

```python
import os, socket
sock_path = os.environ.get("NOTIFY_SOCKET")
if sock_path:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    s.connect(sock_path.replace("@", "\0", 1) if sock_path.startswith("@") else sock_path)
    s.sendall(b"READY=1\n")
```

### sd_notify protocol keys

- `READY=1` — initialization complete
- `RELOADING=1` + `MONOTONIC_USEC=...` — reload started
- `STOPPING=1` — shutdown beginning
- `STATUS=<free-form>` — shown in `systemctl status`
- `WATCHDOG=1` — keepalive ping
- `MAINPID=12345` — declare main pid (needs `NotifyAccess=all`)
- `ERRNO=13` — set failure errno
- `FDSTORE=1` — push an FD into systemd's store for restart survival

## Anti-Patterns

- **`Type=simple` on anything non-trivial.** systemd considers it started
  the moment the launch syscall returns, before your interpreter has
  imported a module. `After=` units race. Use `Type=notify` + sd_notify,
  or `Type=exec` at minimum.
- **`Type=forking` on Python or Node.** They don't double-fork. systemd
  waits for the parent to die and times out.
- **Relative paths in `ExecStart=`.** PATH is not inherited. Always
  absolute: `/usr/bin/python3 /opt/OS/services/discord_bot.py`.
- **Shell metacharacters in `ExecStart=`.** No `&&`, `||`, `|`, `>`, `<`,
  `&`, `$VAR` expansion, `$(cmd)` substitution. Write a script.
- **Background `&` in `ExecStart=`.** Process exits, unit fails.
- **Interactive prompts** (`read`, `getpass`) — no TTY, service hangs.
- **`After=` without `Wants=` / `Requires=`.** `After=` only orders; does
  not pull the dep into the transaction. Network-online needs BOTH
  `After=network-online.target` and `Wants=network-online.target`.
- **`Requires=` for soft deps.** Cascades kills. Use `Wants=` by default;
  `Requires=` only when the dep failing should stop you; `BindsTo=` only
  when the dep stopping should stop you (stricter than Requires=).
- **Skipping `Restart=`** — default is `no`. Most services want `on-failure`.
- **Editing `/usr/lib/systemd/system/`** — overwritten on package upgrade.
  Drop-in under `/etc/systemd/system/UNIT.service.d/`.
- **`ExecStartPre=/bin/bash -c "..."` for non-trivial prep.** Spawns a
  shell parser, loses argv quoting, breaks credential injection, blocks
  startup. Write a script and call it directly.
- **`daemon-reload` in a loop.** Re-parses every unit on the system,
  hundreds of ms. Do it once at the end.
- **Hardcoded secrets in the unit file.** Visible to anyone who can
  `systemctl cat`. Use `EnvironmentFile=` (chmod 640) or
  `LoadCredentialEncrypted=`.
- **`StandardOutput=file:/path/to/log`** without rotation. File grows
  unbounded. Use `journal` and let journald rotate.
- **`KillMode=process`** for multi-process apps. Only the main PID gets
  the signal, children leak. Default `control-group` is right.
- **Hand-parsing `systemctl status` with grep.** Use `show -p KEY --value`
  and `is-active/is-enabled/is-failed` exit codes.
- **`systemctl start` on a crash-looped service.** Silently does nothing
  until `reset-failed` is called. Bake `reset-failed || true` into deploys.

## Data Model

### Unit types (11)

| Type | Purpose |
|---|---|
| `.service` | A process (or group). Most common. |
| `.socket` | A listening socket that can activate a `.service` |
| `.target` | A synchronization point (grouping unit) |
| `.timer` | Fires to activate another unit on schedule or interval |
| `.mount` | A filesystem mount (from fstab generator or hand-written) |
| `.automount` | Lazy mount point, triggers `.mount` on access |
| `.swap` | Swap device or file |
| `.path` | Activates a unit when a file/dir appears, changes, exists |
| `.slice` | A cgroup grouping, for resource accounting across units |
| `.scope` | A group of foreign processes (created via dbus, not a unit file) |
| `.device` | A udev-backed device, used for `SYSTEMD_WANTS=` pulls |

### Unit sections

- `[Unit]` — metadata, dependencies, conditions
- `[Service]` | `[Socket]` | `[Timer]` | `[Mount]` | ... — type-specific
- `[Install]` — how `enable` wires the unit into targets

### cgroup tree

Every unit corresponds to a cgroup under `/sys/fs/cgroup/`. Services live
under `system.slice/` by default. Slices nest (`system.slice/ai.slice/...`),
and limits on a parent cap the aggregate of its children. `systemd-cgls`
shows the tree; `systemd-cgtop` shows live usage.

### Dependency verbs

Strength (what happens when the dep is missing/failing):

- `Wants=` — soft pull; missing dep is ignored
- `Requires=` — hard pull; stopping or failure cascades to us
- `Requisite=` — fails immediately if dep not already active (no pull)
- `BindsTo=` — strictest; if dep stops for ANY reason, we stop
- `PartOf=` — we restart/stop when parent does, but not vice versa
- `Upholds=` — continuously try to keep dep active (255+)

Ordering (orthogonal to strength):

- `Before=` — we must start before dep
- `After=` — we must start after dep

Negative:

- `Conflicts=` — mutual exclusion; starting us stops dep

## Webhooks and Events

N/A for a push-style webhook API — systemd is local. The analogous
surfaces that give you event-driven behavior:

- **Socket activation** (`.socket` + `.service`) — systemd opens the
  listening socket at boot and hands the FD to the service on first
  connection via `LISTEN_FDS=`. Service stays cold until a client hits
  the port.
- **Path units** (`.path` with `PathExists=`, `PathChanged=`,
  `PathModified=`, `DirectoryNotEmpty=`) — activate a service when a
  file or directory transitions. Replaces inotify scripts and cron
  directory pollers.
- **Device units** via udev `SYSTEMD_WANTS=` — activate a service when a
  device appears (USB, block device, etc.).
- **`OnFailure=`** — fire a unit when this one fails. The canonical alert
  pattern: `OnFailure=os-alert@%n.service` where `os-alert@` is a
  templated unit that takes the failed unit name as instance.

## Limits

Per-unit limits come in two families:

### rlimits (POSIX, per-process)

```
LimitNOFILE=65536
LimitNPROC=4096
LimitCORE=0
LimitMEMLOCK=infinity
LimitSTACK=
LimitAS=
```

### cgroup limits (systemd.resource-control)

```
MemoryAccounting=yes
MemoryMax=2G            # hard kill above this
MemoryHigh=1500M        # throttling threshold (soft pressure)
MemoryLow=256M          # protected from reclaim
MemoryMin=128M          # never reclaimed
MemorySwapMax=0         # disable swap for this unit

CPUAccounting=yes
CPUQuota=200%           # 2 full cores
CPUWeight=100           # default 100, range 1-10000
StartupCPUWeight=200    # higher during boot
AllowedCPUs=0-3         # cpuset
AllowedMemoryNodes=0

IOAccounting=yes
IOWeight=100
IOReadBandwidthMax=/var/lib/eos 50M
IOWriteBandwidthMax=/var/lib/eos 50M

TasksAccounting=yes
TasksMax=512            # cap on threads + processes
```

`TasksMax=` is the most underused — Python thread pools and subprocess
explosions are contained cheaply. Default is host-wide in
`/etc/systemd/system.conf` (`DefaultTasksMax=`), typically 15% of
kernel.pid_max.

## Cost Model

N/A — systemd is local. Resource cost is dominated by:

- **cgroup accounting** — `MemoryAccounting=yes`, `CPUAccounting=yes`,
  `IOAccounting=yes` each cost roughly 1-2% of overall perf and some
  kernel memory per unit. Still negligible on a VPS; turn them on.
- **journald storage** — persistent mode (`/var/log/journal/` exists)
  consumes up to 10% of the filesystem by default, capped at 4G. Tune
  via `SystemMaxUse=` in journald.conf.
- **`daemon-reload`** — re-parses every unit, hundreds of ms on a full
  system. Don't loop it.
- **`systemd-networkd-wait-online`** — can add 30-120s to boot if an
  interface never comes up. Override its timeout for slow-boot fixes.

## Version Pinning

systemd versions shipped on Ubuntu LTS (as of 2026-04):

| Ubuntu | systemd | Notable features |
|---|---|---|
| 20.04 (Focal) | 245 | Baseline; no LoadCredentialEncrypted |
| 22.04 (Jammy) | 249 | LoadCredentialEncrypted=, ProtectProc=, ProcSubset= |
| 24.04 (Noble) | 255 | RestartSteps=, RestartMaxDelaySec=, Type=notify-reload, pidfd everywhere |
| 24.10 (Oracular) | 256 | systemd-vmspawn, run0, capsule services |

Feature deltas that bite EOS:

- **`RestartSteps=` / `RestartMaxDelaySec=`** (254+) — stepped backoff.
  On 22.04 you have to roll your own with just `RestartSec=`.
- **`Type=notify-reload`** (253+) — handles SIGHUP + notify cycle. On
  22.04 use `Type=notify` + manual SIGHUP handler.
- **`systemd-creds`** full TPM2 support — 250+ (present on both).
- **`ExitType=cgroup`** (252+) — restart based on cgroup empty, not main
  PID. Useful for services that intentionally exit the launcher.

Check before using new directives:

```
systemctl --version
systemd-analyze verify /etc/systemd/system/your.service
```

`systemd-analyze verify` is your friend — it catches unknown directives
and typos before reload.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

### Why Lennart built it

SysVinit was a serial shell-script orchestrator from the 1980s. Boot was
a chain of `/etc/rc?.d/S##name start` invocations — slow, brittle,
impossible to reason about as a graph. Upstart (Ubuntu) tried event-driven
init but remained imperative and per-distro.

In **April 2010, Lennart Poettering published "Rethinking PID 1"** (read
it — it is the thesis). The core insight: **most boot serialization is
artificial.** Two services that "depend on the network" usually depend on
a *socket*, not on a daemon. If PID 1 owns the socket and hands it to the
daemon when the daemon launches, every service can launch in parallel
from the start — clients block on socket read and the kernel buffers
writes. This is **socket activation**, copied from Apple's launchd.

Three more pillars followed:

1. **Declarative dependencies** — `Wants=`, `Requires=`, `After=`
   describe a graph; systemd computes the transaction. Stop telling the
   computer *how* to boot.
2. **cgroups as the unit of truth** — every service lives in its own
   cgroup; systemd *knows* every descendant process. No more `killall`
   guessing, no more daemons escaping via double-fork.
3. **One service manager for the whole distro** — `nginx.service` works
   identically on Fedora, Debian, Arch, SUSE.

### The controversy

systemd absorbed udev, logind, resolved, networkd, timesyncd, journald,
homed, boot. Critics screamed "Unix philosophy violation: do one thing
well." Lennart's counter: the *project* ships many small binaries, each
doing one thing, sharing a repo and a coherent IPC story (sd-bus). That
is closer to how Plan 9 or BSD bases ship than to "monolith."

The real tradeoff is **coupling at the distro layer**: you cannot fully
swap journald for plain text — it is wired into PID 1. Devuan and Artix
forked. They lost. As of 2026, every mainstream non-Alpine distro is
systemd-based.

### Dependency graph as transaction

Most operators never internalize this. When you `systemctl start foo`,
systemd computes a **transaction** — the set of state changes required to
reach the requested state, including dep activations, ordering
constraints, and conflict resolutions. The transaction is checked for
consistency (cycles, unsatisfiable conflicts) before any action runs. If
the transaction is invalid, nothing happens — you get a single error.

This is why `systemctl restart foo` does NOT restart foo's `After=` deps:
restart is a single transaction that stops and starts foo, nothing else.

## Problem-Solution Map and Hidden Capabilities

Most admins use 5% of systemd. Here is the other 95%.

### Activation patterns

- **Socket activation** (`foo.socket` + `foo.service`) — systemd opens
  the listening socket at boot, hands the FD to the service via
  `LISTEN_FDS=` when the first connection arrives. Service can be cold
  for hours; first request is sub-second. How `cups`, on-demand `sshd`,
  and `docker.socket` work.
- **Path activation** (`foo.path`) — start a service when a file
  appears, changes, or a directory becomes non-empty. Replaces inotify
  scripts and directory-polling cron jobs.
- **Timer units** (`foo.timer`) — cron with dep awareness,
  `Persistent=true` missed-run catchup, `RandomizedDelaySec=` jitter,
  full journal logging.
- **Device activation** via udev `SYSTEMD_WANTS=` — start a service when
  a USB device appears.
- **Mount activation** (`foo.automount`) — lazy-mount NFS/sshfs only
  when something `cd`s into the path.

### Transient and ad-hoc units — `systemd-run`

The most underused command in Linux:

```
systemd-run --unit=myjob --scope htop
systemd-run --on-active=30s --unit=cleanup /path/to/script.sh
systemd-run -p MemoryMax=2G -p CPUQuota=50% python train.py
systemd-run --user --scope -- bash
```

That last one gives your shell session its own cgroup so the OOM killer
kills *only* what you ran, not your entire login session.

### Containerization and isolation

- **`systemd-nspawn`** — chroot on steroids. Full namespace isolation,
  networking, cgroups, zero overhead, uses host kernel. Not Docker, but
  closer to LXC done right.
- **`portablectl`** — portable services. Ship a service as a squashfs
  image with its own `/usr` overlay; systemd attaches it as a regular
  service unit. "Container without container."
- **`systemd-sysext`** — extension images. Atomic `/usr` overlays. The
  foundation of Fedora Silverblue and ParticleOS.

### Identity and secrets

- **`systemd-homed`** — `$HOME` as an encrypted LUKS image with account
  metadata embedded. Portable Linux identity.
- **`systemd-creds`** — encrypted credentials sealed to the TPM2.
  `LoadCredentialEncrypted=db_password:/etc/creds/db.cred` injects a
  decrypted secret into `$CREDENTIALS_DIRECTORY/db_password` at start,
  never on disk in plaintext, never in environment variables. Replaces
  Vault for single-node deployments.
- **`systemd-sysusers`** — declarative `/etc/passwd`.
- **`systemd-tmpfiles`** — declarative `/tmp`, `/run`, `/var/lib/foo`
  directory creation, ownership, age-based cleanup.

### Reliability primitives

- **Watchdog** — `WatchdogSec=30s` + `sd_notify("WATCHDOG=1")` from your
  code. systemd kills + restarts if the heartbeat stops. Combined with
  `RuntimeWatchdogSec=` in `system.conf`, the kernel will reboot the box
  if PID 1 itself wedges. Real HA.
- **`Type=notify`** + `sd_notify("READY=1")` — your service tells
  systemd "I am actually serving traffic now," not "the launcher
  returned." **Always use notify for any non-trivial service.**
- **`DynamicUser=yes`** — systemd allocates a UID at start, runs as that
  UID, releases at stop. Combined with `StateDirectory=`,
  `RuntimeDirectory=`, `LogsDirectory=`, the service gets writable
  scoped paths and zero persistent state.

### Resource accounting without containers

Every unit gets free CPU/memory/IO accounting via cgroups v2.
`systemd-cgtop` is `top` for services. `MemoryMax=`, `MemoryHigh=` (soft
pressure), `CPUWeight=`, `IOWeight=`, `TasksMax=` per unit. **You do not
need Docker to get resource limits.**

## Operational Behavior and Edge Cases

### `restart` vs stop+start

`systemctl restart foo` is a single transaction: foo stops and starts.
**`After=` deps are NOT re-stopped.** If you want fresh dependencies,
`stop` then `start`.

### `Restart=on-failure` semantics

"Failure" is *not* "non-zero exit code." It is determined by
`SuccessExitStatus=`, signal disposition, watchdog timeout, and abnormal
termination. A service that exits 0 with `Restart=on-failure` will
**not** restart. To restart on any exit, use `Restart=always`. To
consider exit code 2 success: `SuccessExitStatus=0 2`.

### `Type=simple` is a footgun

With `Type=simple`, systemd considers the service "started" the moment
the launch syscall returns, before Python has imported a single module.
`After=foo.service` units race. **Prefer `Type=notify`**, or
`Type=exec` (v240+) which waits for the launch syscall to succeed.

### The start-limit-hit trap

A crash-looping service hits `StartLimitBurst=5` within
`StartLimitIntervalSec=10s` and enters failed state with
`start-limit-hit`. `systemctl start` silently does nothing. Bake into
deploy scripts:

```
systemctl reset-failed myservice || true
systemctl restart myservice
```

### journald rate limiting silently drops logs

See Tier 1 "Rate Limits." The default `RateLimitBurst=10000` per 30s
will drop messages on any noisy service with no signal to the
application. For high-volume services, raise the burst globally or set
`LogRateLimitIntervalSec=0` on the unit.

### `ExecStartPre=/bin/bash -c "..."` is an anti-pattern

- Spawns a shell parser between systemd and your binary
- Loses argv quoting precision
- Breaks `Type=notify` and credential injection
- Write a 5-line script and call it directly.

### cgroup v1 vs v2

Modern Ubuntu (22.04+) is **unified cgroup v2 only**. `MemoryAccounting=`
is free in v2, and Pressure Stall Information (PSI) is v2-only, exposed
via `systemd-cgtop --order=memory`.

### Cascade failures from `Requires=`

`Requires=foo.service` means "if foo stops or fails, I stop too." On
`A Requires B Requires C`, killing C kills A. **Use `Wants=` by default;
reserve `Requires=` for hard semantic dependencies.** `BindsTo=` is
even stricter.

### `StopWhenUnneeded=yes`

A unit with this set stops itself the instant nothing else `Wants=` it.
Combined with socket activation, gives you "runs only while a client is
connected." Surprises people.

### `daemon-reload` is not free

Re-parses every unit and rebuilds the dep graph. Don't loop it.

## Ecosystem Position and Composition

### vs supervisord / runit / launchd / PM2 / forever

- **supervisord** — Python process supervisor; predates cgroups.
  Process-level tracking only, no cgroup containment, no log indexing.
  Obsolete when systemd is available.
- **runit / s6** — minimalist supervision. Fast, elegant, no deps. Still
  popular in Alpine and some embedded distros. Loses on: no dep graph,
  no timers, no journal, no hardening directives.
- **launchd** — Apple's inspiration for socket activation. macOS-only.
- **PM2** — Node.js process manager with cluster mode. Wins on:
  multi-process load balancing, metrics dashboard, zero-downtime reload.
  **Rule of thumb:** if you need cluster mode, use PM2 *under* systemd
  (`pm2 startup` creates a systemd unit). Otherwise plain systemd + `node
  app.js` is simpler and more robust.

### systemd + Docker

- **dockerd as a systemd service** — native and clean. `docker.socket`
  provides socket activation for the daemon.
- **systemd inside a container** — possible but hard (`--privileged`,
  `--tmpfs /run`, cgroup delegation). Used by CI images to test units.
  **Don't do this in production** — one process per container.
- Containers inherit cgroup limits from `docker.service`'s slice. Set
  `MemoryMax=` on docker.service to cap *all* containers' memory at once.

### systemd + Podman / Quadlet

**`podman generate systemd --new --name mycontainer > ~/.config/systemd/user/mycontainer.service`**
plus `loginctl enable-linger $USER` gives you **rootless containers
managed by per-user systemd**, surviving logout, with full journal
integration. Newer Podman uses **Quadlet** (`.container` files in
`~/.config/containers/systemd/`) which systemd auto-converts to services.

### systemd + cron

Timers replace cron when you need: dep awareness, missed-run catchup
(`Persistent=true`), journal logs, per-unit hardening, or
`RandomizedDelaySec` jitter. Cron wins on: single-line definitions,
no .timer+.service pair, familiar to every sysadmin, `MAILTO=`
failure emails.

**EOS decision**: all scheduled EOS jobs should be timers — the
`Persistent=true` behavior alone is worth it for a VPS that may reboot.

### systemd + tmux

- **tmux as a user service with linger** — `loginctl enable-linger
  antony` + `~/.config/systemd/user/tmux.service` running `tmux new -d`.
  Survives logout, journal-logged.
- **tmux inside a system service is wrong** — PID 1 of the service
  becomes tmux, which forks children that escape into a new pty
  namespace, defeating cgroup tracking. **For long-running agents, run
  the binary directly and use journalctl, not tmux.**

### systemd + Python venvs

Always: `ExecStart=/opt/OS/.venv/bin/python -m module_name` — invoke the
venv interpreter directly, never `source activate` in a shell wrapper.
The venv is just a python with a baked-in `sys.prefix`. Set
`Environment=PYTHONUNBUFFERED=1` or journald sees logs in 4KB chunks.

### journald vs rsyslog vs Loki/Vector

- **journald** is mandatory. Stores binary indexed logs in
  `/var/log/journal/`.
- **rsyslog** can coexist by reading the journal and writing plain text
  or forwarding to remote syslog. Many shops keep it for compliance.
- **Loki / Vector / Promtail** — the modern shipping path. Vector has a
  native `journald` source. Loki indexes by labels (unit, host) — perfect
  because journald already structures fields. `MESSAGE` + `_SYSTEMD_UNIT`
  + `PRIORITY` is your label set.

## Trajectory and Evolution

### Recent versions

- **v250** (2022) — `systemd-creds` production, `systemd-sysext` stable,
  TPM2-sealed encrypted credentials.
- **v252** (2022, RHEL 9) — `ExitType=cgroup`, more sandboxing.
- **v253** (2023) — `systemd-sysupdate`, image dissection improvements.
- **v254** (2023) — Varlink IPC stable, `BPFDelegateCommands=`, confext.
- **v255** (2023) — pidfd everywhere (no more PID races),
  `Type=notify-reload`, image-based provisioning.
- **v256** (2024) — `systemd-vmspawn`, `run0` (sudo replacement using
  polkit + clean unit), capsule services.
- **v257** (2025) — UKI improvements, refined ParticleOS plumbing.

### Lennart at Microsoft

Lennart joined Microsoft in 2022 to work full-time on systemd,
specifically the **secure boot story**: `systemd-boot`, **Unified Kernel
Images (UKI)** bundling kernel + initrd + cmdline + signature into a
single signed PE binary, `sd-measure` for TPM PCR pre-computation, and
`systemd-pcrlock` for unattended LUKS unlock. The end state: **measured
boot from firmware to userspace, sealed credentials, encrypted home,
atomic OS image updates.** This is **ParticleOS**, the reference distro.

### Immutable Linux is here

- **Fedora Silverblue / CoreOS** — `/usr` read-only, atomic image swaps.
- **SteamOS 3** — Arch-based immutable, A/B partitioned.
- **Ubuntu Core** — snap-based but heavy systemd primitives.

The mental shift: stop thinking "package manager installs files into
/usr." Start thinking "base image + sysext overlays + per-user homed +
per-service credentials."

## Conceptual Model and Solution Recipes

### How to actually think about systemd

1. **Units are atoms.** Eleven types. Everything is one.
2. **Dependencies are declarative.** You describe a graph, systemd
   computes a transaction. `Wants/Requires/Requisite/BindsTo/PartOf`
   (strength) and `Before/After` (ordering) are orthogonal. **This is
   the single most misunderstood thing in systemd.**
3. **cgroups are systemd's superpower.** Every process started by a unit
   lives in that unit's cgroup, transitively. Killing the unit kills the
   cgroup. Accounting free. Limits free. Forkbombs contained.
4. **Targets are not runlevels.** They are *synchronization points* —
   names for "the state where these services should be up." You hook in
   via `WantedBy=multi-user.target`.

### Recipe A — Python long-running agent (the EOS pattern)

`/etc/systemd/system/os-discord.service`:

```ini
[Unit]
Description=EOS Discord Bot
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=600
StartLimitBurst=10

[Service]
Type=notify
NotifyAccess=all
User=eos
WorkingDirectory=/opt/OS
EnvironmentFile=/opt/OS/eos_ai/.env
Environment=PYTHONUNBUFFERED=1 PYTHONPATH=/opt/OS
ExecStart=/opt/OS/.venv/bin/python -m services.discord_bot
Restart=on-failure
RestartSec=10s
TimeoutStartSec=60
TimeoutStopSec=30
WatchdogSec=120
KillMode=mixed

StandardOutput=journal
StandardError=journal
SyslogIdentifier=os-discord

MemoryMax=1G
MemoryHigh=768M
CPUQuota=100%
TasksMax=256
LimitNOFILE=65536

NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictNamespaces=yes
RestrictRealtime=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
SystemCallArchitectures=native
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources
ReadWritePaths=/opt/OS /var/log/eos

[Install]
WantedBy=multi-user.target
```

Pair with `sd_notify("READY=1")` and `sd_notify("WATCHDOG=1")` from
Python. Verify:

```
sudo systemd-analyze verify /etc/systemd/system/os-discord.service
sudo systemctl daemon-reload
sudo systemctl enable --now os-discord.service
systemctl status os-discord.service
journalctl -u os-discord.service -f
systemd-analyze security os-discord.service    # aim for < 3.0
```

### Recipe B — Nightly maintenance timer (cron replacement)

```ini
# /etc/systemd/system/os-nightly.service
[Unit]
Description=EOS Nightly Consolidation

[Service]
Type=oneshot
User=eos
WorkingDirectory=/opt/OS
EnvironmentFile=/opt/OS/eos_ai/.env
ExecStart=/opt/OS/.venv/bin/python /opt/OS/scripts/scheduled/nightly_consolidation.py
StandardOutput=journal
StandardError=journal
SyslogIdentifier=os-nightly
```

```ini
# /etc/systemd/system/os-nightly.timer
[Unit]
Description=Run EOS nightly consolidation at 03:00

[Timer]
OnCalendar=*-*-* 03:00:00
RandomizedDelaySec=10min
Persistent=true
Unit=os-nightly.service

[Install]
WantedBy=timers.target
```

`Persistent=true` is the killer flag: if the VPS was off at 03:00, it
runs on next boot. cron cannot do this.

```
sudo systemctl daemon-reload
sudo systemctl enable --now os-nightly.timer
systemctl list-timers os-nightly.timer
```

### Recipe C — Ollama warm-model service

```ini
[Unit]
Description=Ollama Local LLM
After=network-online.target

[Service]
Type=exec
ExecStart=/usr/local/bin/ollama serve
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_KEEP_ALIVE=24h
Environment=OLLAMA_NUM_PARALLEL=2
ExecStartPost=/usr/local/bin/warmup-ollama.sh
Restart=always
RestartSec=5

MemoryHigh=3500M
MemoryMax=4500M
CPUWeight=80
Slice=ai.slice

[Install]
WantedBy=multi-user.target
```

The warmup script curls `/api/generate` with `keep_alive: 24h` after a
3-second sleep. Create `/etc/systemd/system/ai.slice` to group AI
workloads under a single accountable parent.

### Recipe D — User service surviving logout

```bash
sudo loginctl enable-linger antony
mkdir -p ~/.config/systemd/user
```

`~/.config/systemd/user/devloop.service`:

```ini
[Unit]
Description=Personal dev loop

[Service]
ExecStart=%h/bin/devloop
Restart=always

[Install]
WantedBy=default.target
```

```
systemctl --user daemon-reload
systemctl --user enable --now devloop.service
loginctl show-user antony | grep Linger
```

### Recipe E — Hardened webhook receiver

```ini
[Unit]
Description=EOS Webhook Receiver
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
DynamicUser=yes
ExecStart=/opt/OS/.venv/bin/python -m services.webhook_receiver --listen 127.0.0.1:9000

ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectKernelLogs=true
ProtectControlGroups=true
ProtectClock=true
ProtectHostname=true
ProtectProc=invisible
ProcSubset=pid
StateDirectory=os-webhook
RuntimeDirectory=os-webhook
LogsDirectory=os-webhook

RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources
SystemCallArchitectures=native
NoNewPrivileges=true
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictRealtime=true
RestrictSUIDSGID=true
RestrictNamespaces=true
CapabilityBoundingSet=
AmbientCapabilities=

LoadCredentialEncrypted=hmac_secret:/etc/credstore.encrypted/webhook_hmac

[Install]
WantedBy=multi-user.target
```

Inside the service the secret is at `$CREDENTIALS_DIRECTORY/hmac_secret`.
Score with `systemd-analyze security os-webhook.service` — aim for
under 2.0 ("OK").

### Recipe F — Socket-activated service

```ini
# /etc/systemd/system/echo.socket
[Unit]
Description=Echo socket
[Socket]
ListenStream=8080
Accept=no
[Install]
WantedBy=sockets.target
```

```ini
# /etc/systemd/system/echo.service
[Unit]
Requires=echo.socket
[Service]
ExecStart=/usr/local/bin/echod
StandardInput=socket
```

`systemctl enable --now echo.socket` and the service is cold until first
`nc localhost 8080`. The service receives the listening FD via
`LISTEN_FDS=1`.

## Industry Expert and Cutting-Edge Usage

### `systemd-creds` for secret management without Vault

Single-node deployments do not need Vault. Encrypt a secret to the
host's TPM2:

```
sudo systemd-creds encrypt --tpm2-pcrs=7 \
  plaintext.txt /etc/eos/credentials/anthropic.cred
```

The cred file can sit in git (encrypted to a TPM you don't own). On the
host, `LoadCredentialEncrypted=anthropic_key:/etc/eos/credentials/anthropic.cred`
injects it. **90% replacement for Vault for solo founders.**

### Portable services for dev/prod parity

Build with `mkosi`, attach with `portablectl attach myapp.raw`, and run
identically on dev laptop and prod VPS. Full systemd integration, no
Docker daemon, no Kubernetes. **Nix-like reproducibility without Nix.**

### Hardening score

Run `systemd-analyze security UNIT` on every service you write. Score
is 0.0 (perfect) to 10.0 (UNSAFE). Treat it as a code-review metric:

- **< 2.0** — OK (hardened)
- **2.0–5.0** — MEDIUM (adequate for internal services)
- **5.0–9.0** — EXPOSED (needs hardening)
- **9.0+** — UNSAFE (reject)

The command lists every directive you haven't set and what it would
improve. Use it as a checklist.

### AI workload patterns — transient units

```
systemd-run \
  --unit=train-run-2026-04-06 \
  -p Slice=ai.slice \
  -p MemoryMax=64G \
  -p CPUQuota=800% \
  -p Environment=CUDA_VISIBLE_DEVICES=0,1 \
  -p WorkingDirectory=/opt/training \
  -p StandardOutput=journal \
  /opt/training/.venv/bin/python train.py --config big.yaml
```

cgroup isolation, journal-logged output, resource limits, clean stop
via `systemctl stop train-run-2026-04-06` killing every descendant
including the python→torch→CUDA worker tree. **The no-Kubernetes way
to run training jobs on a single box.**

### The DHH / Kamal / 37signals narrative

37signals' "leaving the cloud" series (2023–2025): a small team can run
a Rails app on bare metal cheaper, faster, more reliably than
AWS+ECS+Fargate. **Kamal** ships Docker containers to bare-metal hosts
via SSH; the hosts run plain Docker on plain systemd. No Kubernetes. No
service mesh. Traefik handles ingress. **The whole production stack
fits in a 200-line config.** This is the credible counter-movement to
Kubernetes-by-default, and **systemd is the substrate that makes it
work.**

### The EOS-relevant stack

For EOS-scale (one VPS, one founder): **systemd + Docker + Tailscale +
Caddy + journald + Vector → Loki**. You get encrypted mesh networking,
automatic TLS, structured logs, zero-downtime reload, health/restart,
and full observability. No Istio, no Linkerd, no Envoy. **Boring,
durable, debuggable.**

## EOS Usage Patterns

### The four canonical os-* services

All four (os-discord, os-bot, os-monitor, os-webhook) follow the same
template as Recipe A, with these per-service overrides:

- `os-discord` — `SyslogIdentifier=os-discord`, `MemoryMax=1G`
- `os-bot` — `SyslogIdentifier=os-bot`, `MemoryMax=2G` (LLM inference),
  higher `TimeoutStartSec=120` for cold-start model loading
- `os-monitor` — `SyslogIdentifier=os-monitor`, `MemoryMax=512M`,
  `Nice=10` (low-priority background)
- `os-webhook` — `SyslogIdentifier=os-webhook`, `MemoryMax=512M`,
  additional `RestrictAddressFamilies=AF_INET AF_INET6` for listening

### Per-env secret injection via drop-ins

Keep the committed unit file generic; inject environment via drop-in:

```bash
sudo systemctl edit os-discord.service
# Opens override.conf in $EDITOR
```

```ini
[Service]
Environment=DISCORD_TOKEN=...
Environment=ANTHROPIC_API_KEY=...
```

Saved to `/etc/systemd/system/os-discord.service.d/override.conf` —
not in git, chmod 640.

### Canonical log-scraping pattern

Python reading the last hour of a unit's logs into memory:

```python
import subprocess, json
result = subprocess.run(
    ["journalctl", "-u", "os-discord.service",
     "--since", "1 hour ago", "-o", "json", "--no-pager"],
    capture_output=True, text=True, check=True
)
entries = [json.loads(line) for line in result.stdout.splitlines() if line]
errors = [e["MESSAGE"] for e in entries if int(e.get("PRIORITY", 6)) <= 3]
```

This is the pattern EOS observability hooks should use — structured,
filterable, no file tailing.

### Deploy script pattern

```bash
#!/usr/bin/env bash
set -euo pipefail
UNIT="os-discord.service"
sudo cp "/opt/OS/deploy/${UNIT}" "/etc/systemd/system/${UNIT}"
sudo systemd-analyze verify "/etc/systemd/system/${UNIT}"
sudo systemctl daemon-reload
sudo systemctl reset-failed "${UNIT}" || true
sudo systemctl enable --now "${UNIT}"
sudo systemctl restart "${UNIT}"
sleep 2
systemctl is-active "${UNIT}" || {
    journalctl -xeu "${UNIT}" -n 50
    exit 1
}
```

The `reset-failed || true` line is the non-obvious one: without it,
after a crash-loop the deploy looks like it succeeded but `start` was a
silent no-op.

### Restart policy tuning for EOS

- `StartLimitIntervalSec=600` — 10-minute window
- `StartLimitBurst=10` — tolerate transient upstream outages
- `Restart=on-failure` — don't loop on clean exits
- `RestartSec=10s` — enough backoff to not hammer upstreams
- `TimeoutStopSec=30` — graceful Python asyncio shutdown
- `WatchdogSec=120` — if using `Type=notify` with sd_notify heartbeat

## Gotchas (from real production)

- **Type=simple on a Python service with downstream `After=` units** →
  downstream races against your startup. Fix: `Type=notify` +
  `daemon.notify("READY=1")` after actually connecting.
- **`After=network-online.target` without the matching `Wants=`** → the
  target is never pulled into the boot transaction and your service
  starts before the network. Always both.
- **`Requires=` cascades** — a flaky dep kills your whole service tree.
  Use `Wants=`.
- **EnvironmentFile missing on deploy** → `Failed to load environment
  files` and the unit refuses to start. Prefix optional files with `-`:
  `EnvironmentFile=-/opt/OS/services/.env.local`.
- **`$VAR` in EnvironmentFile does NOT expand** → `KEY=$OTHER` sets KEY
  to the literal string `$OTHER`. Same for `$(cmd)`. No substitution of
  any kind.
- **EnvironmentFile with world-readable perms** → security audit fail.
  `chown root:eos /opt/OS/eos_ai/.env && chmod 640 /opt/OS/eos_ai/.env`.
- **Forgetting `daemon-reload` after editing** → new version ignored.
  `systemctl edit` auto-reloads; manual edits do not.
- **`systemctl edit` without `--full`** for a vendor unit without a
  local override — creates an empty drop-in, confuses next maintainer.
  Use `--full` to materialize the whole unit in `/etc/systemd/system/`
  once you know you want a fork.
- **`systemctl --user` failing with "Failed to connect to bus"** → no
  user-bus because no linger and no active login. `loginctl enable-linger
  antony`.
- **`journalctl --user -u foo` empty** → you're looking at system logs.
  User-unit logs are in the user journal. Use `--user`.
- **Crash-loop hit, silent `start`** → `reset-failed` first.
- **`KillMode=process`** leaks children → use default `control-group`.
- **Python `print()` appearing 10 seconds late in journal** → stdio
  buffering. `Environment=PYTHONUNBUFFERED=1`.
- **Ollama warm model cold after daemon-reload** → the
  `ExecStartPost` warmup only runs on start, not on reload. Use
  `systemctl restart ollama` to re-warm.
- **`systemctl restart` does not restart `After=` deps** — if you want
  a fresh database connection, `systemctl restart postgresql
  os-discord` as two separate restarts, ordered manually.
- **Docker container units and `docker.service` ordering** — if you
  deploy with `systemd-docker` unit wrappers, always `After=docker.service
  Requires=docker.service`. Otherwise on boot the unit races Docker
  startup and fails with "cannot connect to daemon."
- **`systemd-analyze security` score looks bad because of default
  unit** — compare against a minimal service. Scores >8 on base services
  are common; focus on the *delta* after your hardening directives.
- **Timer fires but the paired service does nothing visible** — a
  oneshot with no logs is normal. Use `StandardOutput=journal` and log
  from the Python script directly.
- **User timer doesn't fire at 03:00 if the user is logged out** — no
  linger. `loginctl enable-linger`.
- **Ubuntu 22.04 rejecting `RestartSteps=`** — that directive is 254+.
  On 22.04 (systemd 249) roll your own with just `RestartSec=`.
- **`docker restart` vs `systemctl restart docker`** — both work, but
  `docker restart` restarts a container (by name), `systemctl restart
  docker` restarts the daemon and kills all containers. The EOS
  convention is `docker restart os-monitor` for individual containers;
  never `systemctl restart docker` unless you mean the whole world.
