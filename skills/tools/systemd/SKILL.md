---
name: systemd
description: "Use when creating or editing unit files, managing the four os-* EOS services, reading journald logs, writing timers to replace cron, configuring drop-in overrides, debugging failed units, hardening services, or scripting systemctl/journalctl from Python or bash."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://www.freedesktop.org/software/systemd/man/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "systemd 249 (Ubuntu 22.04) / 255 (Ubuntu 24.04)"
sdk_version: "python3-systemd 234 (sd_notify, journal handler)"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: systemd

## What This Tool Does

systemd is the init system and service manager on modern Linux. PID 1 owns
a declarative dependency graph of units, launches every process into its own
cgroup, captures all stdout/stderr into the journal, and provides a single
coherent surface for services, timers, sockets, mounts, and resource limits.
It is not just init — it is the operating system's nervous system.

Core capabilities:

- **Service lifecycle** — start, stop, restart, reload, enable at boot, mask
- **Declarative dependencies** — `Wants=`, `Requires=`, `After=`, `BindsTo=`
  describe a graph; systemd computes the transaction
- **cgroup-backed supervision** — every descendant process is tracked; no
  double-fork escapes, no killall guessing, free CPU/memory/IO accounting
- **Timers** — cron replacement with dependency awareness, missed-run catchup
  (`Persistent=true`), journal logging, and jitter
- **journald** — structured, indexed logs queryable per-unit, per-boot,
  per-priority, per-field
- **Drop-in overrides** — layered `*.conf` snippets in `.service.d/`
- **Hardening** — `ProtectSystem=`, `DynamicUser=`, `SystemCallFilter=`,
  `LoadCredentialEncrypted=` replace containers for many sandboxing needs
- **User units** — per-UID systemd instance, linger-enabled for VPS agents

## EOS Integration

systemd is the execution substrate for every long-running EOS process on the
VPS. The four canonical services:

- **os-discord.service** — the Discord bot, primary human interface
- **os-bot.service** — the cognitive-loop worker
- **os-monitor.service** — observability and health watcher
- **os-webhook.service** — inbound webhook receiver

All four follow the same pattern: `Type=simple`, `User=eos`,
`WorkingDirectory=/opt/OS`, `EnvironmentFile=/opt/OS/eos_ai/.env`,
`Restart=on-failure`, `StandardOutput=journal`, `SyslogIdentifier=os-*`.
Logs are read via `journalctl -u os-discord -f`.

Additional EOS patterns:

- **Timers over cron** for nightly_consolidation, nightly_maintenance,
  morning_prep, weekly_review. `Persistent=true` catches missed runs after
  VPS reboot — cron cannot.
- **Drop-in overrides** for injecting per-environment secrets and resource
  caps without touching the committed unit file
- **User units with linger** (`loginctl enable-linger antony`) for any
  founder-scoped automation that must survive SSH logout
- **journald as the log substrate** — never write app logs to files. Let
  journald rotate, filter, and ship.
- **Restart policies** with `StartLimitBurst=10` / `StartLimitIntervalSec=600`
  so crash loops are contained but transient failures self-heal

## Authentication

None for read operations (`systemctl status`, `journalctl -u foo`).
Write operations (`start`, `stop`, `enable`, `daemon-reload`, editing
`/etc/systemd/system/`) require root or a polkit rule granting the action
to the calling user. The EOS VPS runs as root for deploy scripts; use
`sudo systemctl` from interactive shells. User units under
`systemctl --user` require no privilege — they operate on the per-UID
instance owned by the caller.

## Quick Reference

### Service lifecycle

```bash
# Start / stop / restart / reload
sudo systemctl start   os-discord.service
sudo systemctl stop    os-discord.service
sudo systemctl restart os-discord.service
sudo systemctl reload  os-discord.service   # requires ExecReload=

# Enable at boot, with immediate start
sudo systemctl enable --now os-discord.service
sudo systemctl disable --now os-discord.service

# Clear a failed-state after crash-loop hit StartLimitBurst
sudo systemctl reset-failed os-discord.service
sudo systemctl start os-discord.service
```

### Status and inspection

```bash
systemctl status os-discord.service               # human summary + last 10 log lines
systemctl status os-discord.service -n 50         # last 50 log lines
systemctl cat    os-discord.service               # effective unit + drop-ins
systemctl show   os-discord.service -p MainPID -p ActiveState -p NRestarts
systemctl list-units --type=service --state=failed
systemctl is-active os-discord.service            # scriptable, exit 0 if active
```

### Create or edit a unit (drop-in preferred)

```bash
# Canonical location for EOS system units
sudo tee /etc/systemd/system/os-discord.service <<'EOF'
[Unit]
Description=EOS Discord Bot
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=600
StartLimitBurst=10

[Service]
Type=simple
User=eos
WorkingDirectory=/opt/OS
EnvironmentFile=/opt/OS/eos_ai/.env
Environment=PYTHONUNBUFFERED=1 PYTHONPATH=/opt/OS
ExecStart=/usr/bin/python3 /opt/OS/services/discord_bot.py
Restart=on-failure
RestartSec=10s
TimeoutStopSec=30
KillMode=mixed
StandardOutput=journal
StandardError=journal
SyslogIdentifier=os-discord

[Install]
WantedBy=multi-user.target
EOF

sudo systemd-analyze verify /etc/systemd/system/os-discord.service
sudo systemctl daemon-reload
sudo systemctl enable --now os-discord.service
```

### Drop-in override (layered, non-destructive)

```bash
# systemctl edit creates override.conf and runs daemon-reload on save
sudo systemctl edit os-discord.service

# Or manual:
sudo mkdir -p /etc/systemd/system/os-discord.service.d
sudo tee /etc/systemd/system/os-discord.service.d/10-resources.conf <<'EOF'
[Service]
MemoryMax=1G
CPUQuota=150%
EOF
sudo systemctl daemon-reload
sudo systemctl restart os-discord.service
```

### journalctl

```bash
journalctl -u os-discord.service -f              # tail -f
journalctl -u os-discord.service -n 200          # last 200 lines
journalctl -u os-discord.service --since "1 hour ago"
journalctl -u os-discord.service -p err          # errors and worse
journalctl -u os-discord.service --grep "Exception|rate limit"
journalctl -xeu os-discord.service               # status-style, jump to end, hints
journalctl -u os-discord.service -o cat          # message-only for piping
journalctl -u os-discord.service -o json --since "1 hour ago" \
  | jq -r 'select(.PRIORITY|tonumber<=4) | .MESSAGE'
journalctl --disk-usage
sudo journalctl --vacuum-time=14d
```

### Timer pair (cron replacement)

```bash
sudo tee /etc/systemd/system/os-nightly.service <<'EOF'
[Unit]
Description=EOS Nightly Consolidation
[Service]
Type=oneshot
WorkingDirectory=/opt/OS
EnvironmentFile=/opt/OS/eos_ai/.env
ExecStart=/usr/bin/python3 /opt/OS/scripts/scheduled/nightly_consolidation.py
StandardOutput=journal
StandardError=journal
EOF

sudo tee /etc/systemd/system/os-nightly.timer <<'EOF'
[Unit]
Description=Run EOS nightly consolidation at 03:00
[Timer]
OnCalendar=*-*-* 03:00:00
RandomizedDelaySec=10min
Persistent=true
[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now os-nightly.timer
systemctl list-timers --all
systemd-analyze calendar "*-*-* 03:00:00" --iterations=3
```

### User unit with linger (survives logout)

```bash
sudo loginctl enable-linger antony
mkdir -p ~/.config/systemd/user
# write ~/.config/systemd/user/devloop.service ...
systemctl --user daemon-reload
systemctl --user enable --now devloop.service
journalctl --user -u devloop.service -f
```

### Ad-hoc transient unit (no file)

```bash
# One-shot isolated run, cgroup-accounted, journal-logged
systemd-run --unit=test-os-bot --service-type=simple \
  -p WorkingDirectory=/opt/OS \
  -p EnvironmentFile=/opt/OS/eos_ai/.env \
  /usr/bin/python3 /opt/OS/services/discord_bot.py
journalctl -u test-os-bot -f
systemctl stop test-os-bot
```

## Conceptual Model

**PID 1 owns a graph, not a sequence.** Units are atoms
(`.service`, `.timer`, `.socket`, `.path`, `.mount`, `.target`, `.slice`,
`.scope`, `.device`, `.automount`, `.swap` — eleven types). You describe a
graph with `Wants/Requires/BindsTo/PartOf` (strength) and `Before/After`
(ordering). **Strength and ordering are independent** — this is the single
most misunderstood thing in systemd. `After=foo.service` alone does nothing
to pull `foo` into the transaction; you also need `Wants=` or `Requires=`.

**Targets are not runlevels.** They are synchronization points — names for
"the state in which these units should have started." You hook into a target
with `WantedBy=multi-user.target`.

**cgroups are the supervision primitive.** Every process launched by a unit
lives transitively in that unit's cgroup. `systemctl stop` kills the whole
cgroup. `systemd-cgtop` is `top` for services. No child can escape via
double-fork. Resource limits (`MemoryMax=`, `CPUQuota=`, `TasksMax=`) are
enforced by the kernel with zero userspace glue.

**journald is mandatory.** All stdout/stderr from every unit flows into an
indexed binary store at `/var/log/journal/`. Query it by unit, boot, time,
priority, or arbitrary structured field. Never tail log files again.

## Gotchas

- **`Type=simple` on a non-trivial service** → systemd marks it "started"
  the moment the launch syscall returns, before Python has imported a
  single module. Downstream `After=` units race. Prefer `Type=notify` with
  `sd_notify("READY=1")`, or `Type=exec` at minimum.
- **`Type=forking` on Python or Node** → they don't double-fork. systemd
  waits for the parent to exit, then times out, then kills the service.
- **Relative path in `ExecStart=`** → `python3 app.py` does NOT inherit
  PATH. Must be `/usr/bin/python3 /opt/OS/services/discord_bot.py`.
- **Shell metacharacters in `ExecStart=`** → no `&&`, `||`, `|`, `>`, `&`,
  `$VAR` expansion. If you need them, write a 5-line script and call it.
- **Forgetting `daemon-reload`** after editing a unit file → new version
  is ignored. `systemctl edit` auto-reloads; manual edits do not.
- **`After=network-online.target` without `Wants=network-online.target`**
  → the target is never pulled into the transaction, so your "wait for
  network" does nothing. Always pair both.
- **`Requires=` cascades kills** → stopping the dep stops the dependent.
  Use `Wants=` by default; `Requires=` only for hard semantic coupling.
- **Crash-loop hits `StartLimitBurst=5`** → unit enters `failed` with
  `start-limit-hit`. `systemctl start` silently does nothing. Must
  `systemctl reset-failed` first. Bake into deploy scripts.
- **EnvironmentFile does NOT expand variables** → `KEY=$OTHER` sets KEY
  literally to `$OTHER`. No `$(command)` substitution either.
- **EnvironmentFile missing** with no leading `-` → `Failed to load
  environment files`. Prefix optional files with `-`: `EnvironmentFile=-/path`.
- **journald rate-limits silently** → default `RateLimitBurst=10000` per
  30s per service. Excess messages are dropped with a "Suppressed N"
  notice. For noisy services, set `LogRateLimitIntervalSec=0` on the unit.
- **`StandardOutput=file:`** without rotation → file grows unbounded. Use
  `journal` and let journald rotate.
- **User service dies on logout** unless `loginctl enable-linger $USER`.
- **`KillMode=process`** only signals the main PID → children leak out
  of the cgroup. Default `control-group` is right almost always.
- **Editing `/usr/lib/systemd/system/`** → overwritten on package upgrade.
  Always drop-in under `/etc/systemd/system/*.service.d/`.
- **Hardcoding secrets in unit files** → visible to anyone who can
  `systemctl cat`. Use `EnvironmentFile=` chmod 640 or `LoadCredentialEncrypted=`.
- **Ubuntu 22.04 ships systemd 249**, 24.04 ships 255. `RestartSteps=`,
  `RestartMaxDelaySec=`, and `Type=notify-reload` are 254+ only. Check
  with `systemctl --version` before using.

See references/best_practices.md for the full 19-section creator-level
knowledge base, recipes, and EOS-specific unit templates.
