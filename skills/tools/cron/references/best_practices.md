# Cron — Creator-Level Best Practices
Source: man crontab(5), man cron(8), POSIX.1-2017, Vixie cron source
API Version: Vixie cron (cron 3.0pl1-137, Ubuntu/Debian default)
SDK Version: N/A (system utility, no SDK — managed via `crontab` CLI)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Cron does not use API keys or OAuth. Access control is file-based:

**User crontabs:** Each user has a crontab stored in `/var/spool/cron/crontabs/{username}`.
The file is owned by the user and readable only by root. Edited via `crontab -e` (never
edit the spool file directly — crontab validates syntax before saving).

**Allow/deny lists:**
- `/etc/cron.allow` — if exists, only listed users can use crontab
- `/etc/cron.deny` — if exists, listed users are denied (everyone else allowed)
- If neither exists: Debian/Ubuntu allows all users; Red Hat denies all non-root users

**System crontabs:** Files in `/etc/cron.d/` are owned by root and follow a 6-field format
(extra "user" field between time expression and command). Root can also place scripts in
`/etc/cron.{hourly,daily,weekly,monthly}/` directories run by anacron.

**EOS context:** All 26+ jobs run under the root crontab. No `/etc/cron.allow` or
`/etc/cron.deny` exists. Jobs that need API credentials load them via `dotenv` from
`/opt/OS/eos_ai/.env` and `/opt/OS/services/.env` at runtime. Shell scripts using
`claude -p` inherit the shell environment which includes PATH but NOT custom env vars
unless explicitly sourced.

**Permissions for EOS scripts:**
- Shell scripts in `scripts/scheduled/` must be `chmod +x` (executable)
- Python scripts don't need execute bit (invoked as `python3 script.py`)
- Log directories (`/opt/OS/logs/`) must be writable by root

## Core Operations with Exact Signatures

### crontab CLI

```bash
crontab -l                    # List current user's crontab (stdout)
crontab -e                    # Edit crontab in $VISUAL/$EDITOR (validates on save)
crontab -r                    # Remove entire crontab (DANGEROUS — no confirmation)
crontab -u username -l        # List another user's crontab (root only)
crontab filename              # Replace crontab with contents of file
```

### Time expression fields

```
Field         Range           Special Values
─────         ─────           ──────────────
Minute        0-59            * , - /
Hour          0-23            * , - /
Day of Month  1-31            * , - / L W (some implementations)
Month         1-12 or jan-dec * , - /
Day of Week   0-7 or sun-sat  * , - / (0 and 7 both = Sunday)
```

**Operators:**
- `*` — every value in range
- `,` — value list: `1,3,5`
- `-` — range: `1-5`
- `/` — step: `*/15` (every 15), `1-30/2` (odd numbers 1-29)

**Special strings (non-POSIX, supported by Vixie cron):**
```
@reboot    — run once at daemon startup
@yearly    — 0 0 1 1 * (Jan 1 midnight)
@monthly   — 0 0 1 * *
@weekly    — 0 0 * * 0 (Sunday midnight)
@daily     — 0 0 * * *
@hourly    — 0 * * * *
```

### Environment variables in crontab

```cron
SHELL=/bin/bash            # Default is /bin/sh
PATH=/usr/local/bin:/usr/bin:/bin
MAILTO=""                  # Empty = suppress mail; address = send output there
HOME=/root                 # Working directory for jobs
```

Variables set BEFORE job lines apply to all subsequent jobs. They do NOT inherit
the interactive shell's environment (.bashrc, .profile are NOT sourced).

### flock CLI (mutual exclusion for cron jobs)

```bash
flock [options] lockfile command [args]
flock [options] fd                        # lock an already-open file descriptor

# Options:
flock -n, --nonblock     # fail immediately if lock unavailable (exit 1)
flock -w N, --timeout=N  # wait N seconds for lock, then fail
flock -s, --shared       # shared (read) lock instead of exclusive
flock -u, --unlock       # release lock (rarely needed — auto on fd close)
flock -E N               # exit code on lock failure (default 1)
```

**Two invocation patterns:**

Pattern 1 — Command form (simple):
```bash
flock -n /tmp/myjob.lock python3 script.py
```

Pattern 2 — File descriptor form (EOS standard, more flexible):
```bash
exec 200>/tmp/myjob.lock
if ! flock --nonblock 200; then
    echo "SKIP: already running"
    exit 0
fi
# Job body here — lock held until script exits
```

The fd-based pattern is preferred because it allows custom skip-logging and
doesn't spawn a subshell.

## Pagination Patterns

N/A — Cron is a local system daemon with no API pagination. When listing jobs
(`crontab -l`), all entries are returned at once. For systems with many jobs,
pipe through `grep` to filter:

```bash
crontab -l | grep "scripts/"       # all EOS script jobs
crontab -l | grep "^\*/5"          # all 5-minute jobs
crontab -l | grep -v "^#"          # non-comment lines only
crontab -l | grep -c "^\*\|^[0-9]" # count active jobs
```

## Rate Limits

Cron itself has no rate limits — it will happily fire 100 jobs per minute. The
real rate limits in EOS are resource contention:

**CPU/Memory contention:** The VPS has finite resources. High-frequency jobs
(every 5 minutes) must be lightweight. Heavy jobs (claude -p, docker-compose run)
should run during low-activity windows (2am-5am).

**Anthropic API budget:** `claude -p` jobs have per-invocation budget caps
(`--max-budget-usd`). Current caps:
- nightly_maintenance.sh: $0.50
- morning_prep.sh: $0.30
- weekly_review.sh: $1.00

If two claude -p jobs overlap, they share the same API key's rate limit. Anthropic's
rate limits are per-key, not per-process.

**Disk I/O:** Multiple jobs appending to log files simultaneously is safe (atomic
at small write sizes on Linux) but can cause I/O contention on slow disks.

**Database connections:** Multiple Python jobs hitting Neon Postgres simultaneously
can exhaust connection limits. Neon free tier: 100 simultaneous connections.
EOS jobs are short-lived and close connections, but a burst of 8 concurrent
15-minute jobs could theoretically approach this.

**EOS contention windows:**
- `*/5` jobs: 2 jobs (day_reminder + agent_task_executor) every 5 minutes
- `*/15` jobs: 6 jobs every 15 minutes (call_prep, notion_tasks_sync, post_meeting, calendar_invites, noshow_detector, notion_sync_poller)
- Highest contention: minutes 0, 15, 30, 45 of every hour (all */5 AND */15 fire)

## Error Codes and Recovery

### crontab exit codes
```
0  — Success (job ran, regardless of job's own exit code)
1  — crontab: syntax error (on crontab -e save)
```

### Job exit codes (logged by cron)
Cron does not interpret job exit codes. It only:
1. Runs the command in a shell
2. If the command produces stdout/stderr AND MAILTO is set, mails output
3. Logs to syslog: `CRON[PID]: (user) CMD (command)` on start

**EOS recovery patterns:**

Script-level: `set -euo pipefail` in shell scripts causes immediate exit on
any error. The cron entry's `>> log 2>&1` captures the error. Recovery is
manual (check logs next morning).

flock skip: If a flock-protected job finds the lock held, it exits 0 (not an
error — intentional skip). The skip is logged.

claude -p failure: If claude -p exits non-zero (API error, budget exhausted),
the shell script continues to the next step only if `set -e` is NOT active, or
stops if it is. EOS nightly_maintenance.sh uses `set -euo pipefail` so a claude -p
failure stops the entire maintenance run.

**Diagnosing "job didn't run":**
1. Check syslog: `grep CRON /var/log/syslog | tail -20`
2. Check job log: `tail -20 /opt/OS/logs/jobname.log`
3. Check crontab syntax: `crontab -l | grep jobname`
4. Check script permissions: `ls -la scripts/scheduled/jobname.sh`
5. Test manually: run the exact cron command from a shell

## SDK Idioms

Cron has no SDK. Interaction is through the `crontab` CLI and configuration files.

**EOS idiom for programmatic crontab management:**
```bash
# Read current crontab
CURRENT=$(crontab -l 2>/dev/null || echo "")

# Append a new job
echo "$CURRENT
0 9 * * * cd /opt/OS && python3 scripts/new_job.py >> /opt/OS/logs/new_job.log 2>&1" | crontab -

# Remove a specific job
crontab -l | grep -v "new_job.py" | crontab -

# Replace entire crontab from file
crontab /opt/OS/config/crontab.txt
```

**EOS idiom for shell wrapper scripts:**
```bash
#!/bin/bash
set -euo pipefail
LOG="/opt/OS/logs/jobname_$(date +%Y%m%d).log"
echo "=== Job Start: $(date) ===" >> "$LOG"
cd /opt/OS
# ... job body ...
echo "=== Done: $(date) ===" >> "$LOG"
```

**EOS idiom for Python cron jobs:**
```python
import sys, os
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/services/.env')
# ... job body using EOS imports ...
```

## Anti-Patterns

### 1. Using `>` instead of `>>`
```bash
# WRONG — overwrites log every run, loses history
0 6 * * * python3 script.py > /opt/OS/logs/script.log 2>&1

# RIGHT — appends, preserves history
0 6 * * * python3 script.py >> /opt/OS/logs/script.log 2>&1
```

### 2. Forgetting `2>&1`
```bash
# WRONG — stderr goes to cron mail, not log file
0 6 * * * python3 script.py >> /opt/OS/logs/script.log

# RIGHT — captures both stdout and stderr
0 6 * * * python3 script.py >> /opt/OS/logs/script.log 2>&1
```

### 3. Using relative paths
```bash
# WRONG — runs from HOME, not project root
0 6 * * * python3 scripts/morning_intel.py

# RIGHT — explicit cd or absolute path
0 6 * * * cd /opt/OS && python3 scripts/morning_intel.py >> /opt/OS/logs/morning_intel.log 2>&1
```

### 4. No mutual exclusion on long-running jobs
```bash
# WRONG — if job takes >15 min, two instances run concurrently
*/15 * * * * python3 long_running_script.py

# RIGHT — flock prevents overlap
*/15 * * * * flock -n /tmp/long_running.lock python3 long_running_script.py
```

### 5. Unescaped percent signs in crontab
```bash
# WRONG — cron interprets % as newline, truncates command
0 6 * * * echo "Today is $(date +%Y-%m-%d)"

# RIGHT — escape percent signs
0 6 * * * echo "Today is $(date +\%Y-\%m-\%d)"
```

### 6. Complex inline commands instead of script files
```bash
# WRONG — unmaintainable, quoting nightmares
0 23 * * * python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from dotenv import load_dotenv; ..."

# RIGHT — extract to a script file
0 23 * * * cd /opt/OS && python3 scripts/nightly_email_review.py >> /opt/OS/logs/email_review.log 2>&1
```

### 7. Not logging job start/end timestamps
```bash
# WRONG — no way to measure duration or detect hangs
cd /opt/OS && python3 scripts/job.py >> log

# RIGHT — wrapper with timestamps
echo "=== Start: $(date) ===" >> log && python3 scripts/job.py >> log 2>&1 && echo "=== End: $(date) ===" >> log
```

## Data Model

The crontab IS the data model. There is no database, no API, no schema. Each line
is a self-contained job definition:

```
┌─ Time Expression ─┐  ┌─ Command ─────────────────────────┐
0 6 * * *              cd /opt/OS && python3 scripts/foo.py
│ │ │ │ │              └── shell command (run via SHELL)
│ │ │ │ └── day of week (0=Sun, 1=Mon, ..., 7=Sun)
│ │ │ └──── month (1-12)
│ │ └────── day of month (1-31)
│ └──────── hour (0-23)
└────────── minute (0-59)
```

**EOS crontab structure (26+ entries):**
- Comment lines: `# description`
- Environment lines: `VAR=value`
- Job lines: `time-expr command`

**Job categories by frequency:**

| Frequency | Count | Examples |
|-----------|-------|---------|
| Every 5 min | 2 | day_reminder, agent_task_executor |
| Every 15 min | 6 | call_prep, notion_tasks_sync, post_meeting, calendar_invites, noshow_detector, notion_sync_poller |
| Daily fixed time | 12 | orchestrator, morning_prep, nightly_maintenance, midday_checkin, eod_sync, etc. |
| Weekly | 5 | weekly_review (x2), portfolio_brief, relationship_nurture, week_architect |
| On boot | 0 | (none currently) |

**Associated file paths per job:**
- Script: `/opt/OS/scripts/*.py` or `/opt/OS/scripts/scheduled/*.sh`
- Log: `/opt/OS/logs/*.log`
- Lock: `/tmp/eos_*.lock` (flock-protected jobs only)

## Webhooks and Events

N/A — Cron has no webhook or event system. It is a fire-and-forget scheduler.

**EOS alternatives for job-completion notifications:**
Jobs that need to report status use Discord webhooks at the end of their execution:
```python
from eos_ai.discord_utils import post_to_webhook
post_to_webhook(report, title="Job Complete", webhook=os.getenv("DISCORD_BRIEF_WEBHOOK"))
```

This is an application-level pattern, not a cron feature. Jobs that fail silently
produce no notification unless the script itself implements error-reporting logic.

**Missing capability:** EOS has no centralized "job failed" alerting. If a cron job
fails at 2am, no one knows until manually checking logs. Recommendation: add a
lightweight wrapper that posts to Discord on non-zero exit codes.

## Limits

**Crontab limits (Vixie cron):**
- Maximum crontab size: no hard limit (file-based), but excessively large crontabs
  slow the daemon's per-minute scan
- Minimum interval: 1 minute (cron checks once per minute)
- Maximum simultaneous jobs: no limit (all matching jobs fire independently)
- Command line length: limited by `ARG_MAX` (typically 2MB on Linux)
- Environment variable lines: max ~1000 chars per line

**EOS operational limits:**
- VPS RAM: shared across all concurrent jobs — high-frequency jobs must be lightweight
- Neon free tier: 100 simultaneous connections
- Anthropic key: per-minute token limits (varies by plan)
- Log disk space: unbounded growth without rotation — 7-day cleanup in nightly_maintenance.sh
- flock files: limited by /tmp filesystem space (negligible — lock files are 0 bytes)

**Timing precision:**
Cron checks once per minute. A job scheduled for `0 6 * * *` may fire at 06:00:00
through 06:00:59 depending on daemon load. For sub-minute precision, use `sleep` within
a per-minute cron job or switch to systemd timers.

## Cost Model

Cron itself is free — it's a system daemon. Costs in EOS come from what cron triggers:

**claude -p API spend (daily):**
| Job | Budget Cap | Frequency | Max Daily |
|-----|-----------|-----------|-----------|
| nightly_maintenance.sh | $0.50 | daily | $0.50 |
| morning_prep.sh | $0.30 | daily | $0.30 |
| weekly_review.sh | $1.00 | weekly | $0.14/day avg |

**Max daily AI spend from cron: ~$0.94/day** (assuming all caps hit).
Monthly ceiling: ~$28.20 from cron jobs alone.

**Neon Postgres:** Jobs making DB queries consume compute units. Short queries
from 15-minute polling jobs are negligible.

**Docker:** `os-scraper` ephemeral container consumes CPU/memory during run.

**Monitoring cost:** Log files consume disk. EOS rotates logs older than 7 days
in nightly_maintenance.sh (`find /opt/OS/logs -name '*.log' -mtime +7 -delete`).

## Version Pinning

**Cron version:** `cron 3.0pl1-137` (Vixie cron, Ubuntu/Debian package). This version
has been stable for years with no breaking changes. The crontab syntax has been unchanged
since POSIX.1-2001.

**No API versioning:** Cron has no API version. The crontab(5) format is the interface
and it is fully stable.

**Deprecation risk:** Zero. Cron has been part of Unix since 1975. While systemd timers
offer a modern alternative, cron is not deprecated and remains the default on
Debian/Ubuntu.

**EOS version pinning:**
- `claude` CLI version: pinned by npm install, check with `claude --version`
- Python 3.12: pinned by system install
- Script dependencies: pinned in `/opt/OS/requirements.txt`

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Cron was designed in 1975 by Ken Thompson for Version 7 Unix. The modern implementation
(Vixie cron, by Paul Vixie, 1987) added per-user crontabs and environment variable
support. The design philosophy is radical simplicity:

**Core tradeoff: Simplicity over sophistication.** Cron deliberately has:
- No dependency graph (unlike Airflow, Prefect, systemd)
- No retry logic (unlike job queues)
- No output management (unlike modern schedulers)
- No distributed coordination (single-host only)

This is intentional. Cron answers one question: "Run this command at this time."
Everything else is the command's responsibility.

**What cron is NOT:**
- Not a workflow engine — use Airflow/Prefect for DAGs
- Not a job queue — use Celery/Redis for queued work
- Not a process supervisor — use systemd/supervisord for long-running services
- Not a distributed scheduler — use Kubernetes CronJobs for multi-node

**Why EOS uses cron instead of alternatives:** EOS runs on a single VPS. The jobs
are independent (no DAG dependencies). The schedule is human-readable. There is no
cluster to coordinate. Cron is the correct tool for this scale. When EOS outgrows
a single VPS, migrate to Kubernetes CronJobs or a managed scheduler.

## Problem-Solution Map and Hidden Capabilities

**Problem: Long-running job overlaps with next invocation.**
Solution: flock with `--nonblock`. The second invocation detects the lock, logs a
skip message, and exits cleanly. No data corruption, no resource doubling.

**Problem: Job needs to run only on business days.**
Solution: Day-of-week field + inline check:
```cron
0 9 * * 1-5 cd /opt/OS && python3 scripts/weekday_only.py >> log 2>&1
```
Or for holidays: add a bash guard `[ -f /opt/OS/config/holiday ] && exit 0` at
the top of the script.

**Problem: Job should only run if a previous job succeeded.**
Solution: Chain with `&&` or use a sentinel file:
```bash
# In job A: touch /tmp/eos_jobA_done on success
# In job B crontab: 0 7 * * * [ -f /tmp/eos_jobA_done ] && python3 jobB.py && rm /tmp/eos_jobA_done
```

**Problem: Need sub-minute scheduling.**
Solution: Use a per-minute cron job with sleep:
```cron
* * * * * cd /opt/OS && python3 scripts/check.py
* * * * * sleep 30 && cd /opt/OS && python3 scripts/check.py
```

**Hidden capability — @reboot:** Run a job once when cron starts (system boot or
cron daemon restart). Useful for starting EOS services:
```cron
@reboot cd /opt/OS && docker compose up -d >> /opt/OS/logs/boot.log 2>&1
```

**Hidden capability — MAILTO for error alerting:**
```cron
MAILTO="alerts@domain.com"
# All subsequent jobs mail their output (stdout+stderr) to this address
```
Not useful for EOS (no mail server configured), but the concept maps to
Discord webhook alerting.

**Hidden capability — CRON_TZ (per-job timezone):**
Some cron implementations support `CRON_TZ=America/Los_Angeles` as an
environment variable in the crontab, making that job's schedule evaluate in
Pacific time. Not universally supported — test before relying on it.

## Operational Behavior and Edge Cases

**Daylight Saving Time (DST):**
This is the most dangerous cron edge case. When clocks spring forward:
- A job scheduled at 2:30am DOES NOT RUN (2:30am doesn't exist)
- A job at 3:00am runs normally

When clocks fall back:
- A job scheduled at 1:30am may run TWICE (1:30am occurs twice)

EOS mitigation: The maintenance window (2:00-3:00am) is in the DST danger zone.
In March, nightly_maintenance.sh at 2:00am will NOT fire on spring-forward night.
Move critical nightly jobs to 3:00am or later to avoid this, or use UTC.

**System clock jumps:**
If the system clock jumps forward (NTP correction, manual change), cron may
fire all missed jobs at once or skip them entirely depending on implementation.
Vixie cron re-checks the time every minute and fires anything whose time matches
the current minute — it does not "catch up" on missed minutes.

**Cron daemon restart:**
If crond is stopped and restarted, jobs that should have fired during downtime
are NOT retroactively executed. They are simply lost. Use anacron for jobs that
must run "at least once per day" even if the system was down.

**Zombie processes:**
If a cron job's child process becomes a zombie (parent died without wait()),
it persists until crond reaps it. This is rare with bash scripts but can happen
with backgrounded subprocesses.

**Log file contention:**
Multiple jobs appending to the same log file simultaneously is safe on Linux
(writes under PIPE_BUF = 4096 bytes are atomic). But interleaved output from
concurrent jobs makes logs hard to parse. EOS uses separate log files per job.

**Empty crontab on accidental `crontab -r`:**
`crontab -r` removes the ENTIRE crontab with NO confirmation. Muscle memory
from typing `crontab -e` can cause catastrophic deletion. Mitigation: back up
crontab periodically:
```bash
crontab -l > /opt/OS/config/crontab_backup_$(date +%Y%m%d).txt
```

## Ecosystem Position and Composition

**Cron's position:** Cron is the scheduling layer. It triggers other tools but
does not process data itself. In EOS:

```
Cron (scheduler)
  ├── triggers → Python scripts (business logic)
  ├── triggers → Shell wrappers → claude -p (AI processing)
  ├── triggers → Docker containers (isolated tasks)
  ├── triggers → orchestrator.py → EOS gateway (full pipeline)
  └── all jobs → log files → manual review (no automated monitoring)
```

**Natural complements:**
- **flock** — mutual exclusion (already used)
- **logrotate** — log management (not yet configured for EOS — jobs grow unbounded)
- **systemd timers** — modern alternative with dependency support and logging
- **anacron** — catch-up scheduling for jobs that must not be skipped
- **at** — one-time future scheduling (useful for ad-hoc tasks)

**Integration anti-patterns:**
- Cron + long-running processes: use systemd services instead
- Cron + interactive commands: cron has no TTY, interactive prompts hang forever
- Cron + GUI applications: cron has no display server ($DISPLAY is unset)

## Trajectory and Evolution

**Cron's trajectory:** Stable and unchanging. The crontab format has not changed
meaningfully since 1987. Vixie cron continues to receive security patches but no
feature development.

**The systemd timer alternative:** systemd timers offer:
- Built-in logging (journalctl)
- Dependency ordering (After=, Requires=)
- Randomized delay (RandomizedDelaySec) to prevent thundering herd
- Persistent timers (run missed jobs after downtime)
- Resource control (CPUQuota, MemoryMax)

EOS should NOT migrate to systemd timers now. The crontab is simpler to edit,
simpler to audit (`crontab -l`), and the 26-job scale doesn't warrant systemd
complexity. Revisit if: job count exceeds 50, dependency chains become critical,
or log management becomes a bottleneck.

**Kubernetes CronJobs:** When EOS moves to multi-node, Kubernetes CronJobs provide:
- Container isolation per job
- Resource limits per job
- Automatic retry with backoff
- Concurrency policy (Allow, Forbid, Replace)
This is the likely migration path when EOS scales beyond a single VPS.

## Conceptual Model and Solution Recipes

**Mental model:** Think of cron as an alarm clock with 26+ alarms. Each alarm fires
independently. There is no snooze (retry), no "only if the previous alarm was
acknowledged" (dependency), and no "tell me if this alarm was missed" (monitoring).
Every feature beyond "fire at this time" must be built into the job itself.

**The EOS cron primitives:**
1. **Time expression** — when to fire
2. **Working directory** — `cd /opt/OS &&`
3. **Command** — what to run
4. **Output capture** — `>> log 2>&1`
5. **Mutual exclusion** — flock (optional)
6. **Budget cap** — `--max-budget-usd` for claude -p (optional)

**Recipe 1: Add a new daily Python job**
```bash
# 1. Create the script
cat > /opt/OS/scripts/new_job.py << 'EOF'
import sys, os
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
# ... job logic ...
print("Done")
EOF

# 2. Test manually
cd /opt/OS && python3 scripts/new_job.py

# 3. Add to crontab
(crontab -l; echo "0 9 * * * cd /opt/OS && python3 scripts/new_job.py >> /opt/OS/logs/new_job.log 2>&1") | crontab -

# 4. Verify
crontab -l | grep new_job
```

**Recipe 2: Add a flock-protected shell wrapper with claude -p**
```bash
# 1. Create the wrapper
cat > /opt/OS/scripts/scheduled/new_job.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail
LOCK="/tmp/eos_new_job.lock"
LOG="/opt/OS/logs/new_job_$(date +%Y%m%d).log"
exec 200>"$LOCK"
if ! flock --nonblock 200; then
    echo "[$(date -Iseconds)] SKIP: already running" >> "$LOG"
    exit 0
fi
echo "=== Start: $(date) ===" >> "$LOG"
cd /opt/OS
claude -p --allowedTools "Bash Read Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.25 \
  "Your prompt here" >> "$LOG" 2>&1
echo "=== Done: $(date) ===" >> "$LOG"
SCRIPT
chmod +x /opt/OS/scripts/scheduled/new_job.sh

# 2. Test manually
bash /opt/OS/scripts/scheduled/new_job.sh

# 3. Add to crontab
(crontab -l; echo "0 14 * * * bash /opt/OS/scripts/scheduled/new_job.sh") | crontab -
```

**Recipe 3: Audit all cron jobs for issues**
```bash
# List all jobs with line numbers
crontab -l | grep -n "^[^#]" | grep -v "^$"

# Check for missing 2>&1
crontab -l | grep -v "2>&1" | grep -v "^#" | grep -v "^$" | grep -v "^[A-Z]"

# Check for missing cd /opt/OS
crontab -l | grep "python3" | grep -v "cd /opt/OS" | grep -v "^#"

# Check for unescaped percent signs
crontab -l | grep "%" | grep -v "\\\\%" | grep -v "^#"

# Count jobs by frequency
echo "Every 5 min: $(crontab -l | grep '^\*/5' | wc -l)"
echo "Every 15 min: $(crontab -l | grep '^\*/15' | wc -l)"
echo "Daily: $(crontab -l | grep '^[0-9]' | grep -v '\*/\|* *0\|* *1' | wc -l)"
echo "Weekly: $(crontab -l | grep '* *[0-7]$' | wc -l)"
```

**Recipe 4: Add failure alerting to any job**
```bash
#!/bin/bash
set -euo pipefail
cd /opt/OS

python3 scripts/some_job.py >> /opt/OS/logs/some_job.log 2>&1
EXIT=$?

if [ $EXIT -ne 0 ]; then
    python3 -c "
import sys, os
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/services/.env')
from eos_ai.discord_utils import post_to_webhook
post_to_webhook(
    'CRON FAILURE: some_job.py exited $EXIT',
    title='Cron Alert',
    webhook=os.getenv('DISCORD_BRIEF_WEBHOOK'))
"
fi
```

**Recipe 5: Backup and restore crontab**
```bash
# Backup
crontab -l > /opt/OS/config/crontab_backup_$(date +%Y%m%d).txt

# Restore
crontab /opt/OS/config/crontab_backup_20260406.txt

# Diff current vs backup
diff <(crontab -l) /opt/OS/config/crontab_backup_20260401.txt
```

## Industry Expert and Cutting-Edge Usage

**Pattern: Cron + healthcheck endpoint.**
Modern SaaS teams run a per-minute cron job that pings a healthcheck service
(Healthchecks.io, Cronitor, Better Uptime). If the ping stops arriving, the
service alerts. This inverts the monitoring problem: instead of monitoring job
success, monitor job absence.

EOS implementation:
```cron
*/5 * * * * curl -fsS --retry 3 https://hc-ping.com/your-uuid-here > /dev/null
```
Or build it internally: a cron job that touches a timestamp file + a monitor that
alerts if the timestamp is stale.

**Pattern: Cron + git for audit trail.**
Commit the crontab to git whenever it changes:
```bash
crontab -l > /opt/OS/config/crontab.txt
cd /opt/OS && git diff --quiet config/crontab.txt || git add config/crontab.txt && git commit -m "update crontab"
```
This gives you version history, blame, and rollback for your schedule.

**Pattern: Structured JSON logging.**
Replace plain-text logging with JSON for machine parsing:
```python
import json, sys
from datetime import datetime

def log(event, **data):
    entry = {"ts": datetime.utcnow().isoformat(), "event": event, **data}
    print(json.dumps(entry), file=sys.stderr)
```
Enables: log aggregation, alerting on specific events, duration tracking.

**Pattern: Cost-aware scheduling.**
For claude -p jobs, track actual spend vs budget cap:
```bash
# After claude -p call, parse the output for token/cost info
# Log it: {"job": "nightly_maintenance", "budget": 0.50, "actual": 0.23}
# Alert if actual consistently approaches cap (job complexity growing)
```

**Pattern: Graceful degradation chain.**
When a job's primary tool is unavailable (API down, key expired), fall through
to a degraded mode instead of failing:
```bash
python3 scripts/morning_intel.py 2>/dev/null \
  || python3 scripts/morning_intel_fallback.py 2>/dev/null \
  || echo "Morning intel: all sources unavailable" >> log
```
This mirrors EOS's model_router fallback chain (Anthropic -> Gemini -> Ollama)
applied to cron jobs.

**AI-native cron pattern: Self-healing schedules.**
Use claude -p in a weekly meta-job to audit the crontab itself:
```bash
claude -p "Review this crontab for issues: $(crontab -l). Check for: overlapping
heavy jobs, missing log redirects, stale entries pointing to deleted scripts,
DST vulnerability, missing flock on long-running jobs. Output a fix list."
```
EOS should implement this as part of weekly_review.sh.

---

## EOS Usage Patterns

**Total active cron jobs:** 26
**Job breakdown:** 2 every-5-min, 6 every-15-min, 12 daily, 5 weekly, 1 Docker
**Shell wrappers using claude -p:** 3 (nightly_maintenance, morning_prep, weekly_review)
**flock-protected jobs:** 1 (nightly_consolidation) — more should be added
**Log directory:** /opt/OS/logs/ (7-day rotation in nightly maintenance)
**Lock directory:** /tmp/ (prefix: eos_)

**Jobs that should be flock-protected but aren't:**
- agent_task_executor.py (runs every 5 min, could overlap if slow)
- notion_tasks_sync.py (runs every 15 min, Notion API can be slow)
- notion_sync_poller.py (runs every 15 min, same risk)

**Jobs that should stagger but don't:**
- 3:00am: discord_daily_clear + nightly_consolidation
- Sunday 6:00am: weekly_review.sh + portfolio_brief.py

## Gotchas

### DST spring-forward kills 2am jobs
On spring-forward night (March), 2:00am-2:59am does not exist. The
nightly_maintenance.sh job at `0 2 * * *` will not fire. One night per year,
maintenance is silently skipped. Move to 3:00am or use UTC cron.

### `crontab -r` is one keystroke from `crontab -e`
On a keyboard, `r` is right next to `e`. One typo deletes the entire crontab
with no confirmation, no backup, no undo. Always maintain a crontab backup file
in the repo. Consider aliasing `crontab -r` to a safer alternative.

### call_prep.py log goes to wrong directory
The crontab has a mismatch comment "DEX Email GPS — 6pm EOD closing loop" above
the `call_prep.py` entry, but call_prep runs every 15 minutes and is not the
6pm EOD job. The comment is stale/incorrect. Comments in crontabs drift from
reality — always verify the actual command, not the comment.

### No centralized failure alerting
If any of the 26 jobs fails at 2am, there is no notification. The failure sits
in a log file until someone checks. This is the single biggest operational gap
in EOS cron infrastructure. Priority fix: add a Discord webhook wrapper for
critical jobs (nightly_maintenance, morning_prep, orchestrator).

### agent_task_executor.py logs to scripts/ not logs/
The entry `>> /opt/OS/scripts/agent_executor.log` logs into the scripts directory
instead of the standard `/opt/OS/logs/` directory. This breaks the log rotation
pattern in nightly_maintenance.sh which only cleans `/opt/OS/logs/`.
