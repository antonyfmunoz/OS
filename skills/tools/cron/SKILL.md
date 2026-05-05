<<<<<<< Updated upstream
---
name: cron
description: "Use when adding, modifying, debugging, or auditing scheduled jobs in EOS — including crontab entries, flock locking, log rotation, claude -p budget caps, or diagnosing why a scheduled task did not fire."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://man7.org/linux/man-pages/man5/crontab.5.html"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "vixie-cron (Debian/Ubuntu default)"
sdk_version: "cron 3.0pl1-137 (Ubuntu)"
speed_category: stable
trigger: both
effort: medium
context: fork
---

# Tool: Cron (Scheduled Task Management)

## What This Tool Does

Cron is the POSIX job scheduler daemon that executes commands on a time-based schedule
defined in crontab files. Each line in a crontab maps a five-field time expression
(minute, hour, day-of-month, month, day-of-week) to a shell command. The daemon wakes
every minute, checks all crontabs, and runs any jobs whose time expression matches the
current wall-clock time.

EOS uses cron as the heartbeat of the entire operating system. 26+ jobs orchestrate the
daily cycle: nightly maintenance, morning prep, intelligence briefs, pipeline monitoring,
meeting detection, memory consolidation, and weekly reviews. Jobs fall into five categories:

- **Shell wrappers** (`scripts/scheduled/*.sh`) — multi-step workflows using `claude -p`
  with budget caps and flock mutual exclusion
- **Direct Python** — single-purpose scripts invoked as `python3 /opt/OS/scripts/foo.py`
- **Inline Python** — one-liner `python3 -c "..."` for simple operations
- **Docker commands** — `docker-compose run` for containerized tasks
- **Orchestrator** — the 6am orchestrator that triggers the full morning cycle

## EOS Integration

### Complete Crontab — Annotated by Category

**NIGHTLY (2am-3am) — Maintenance Window**
```cron
0 2 * * *   bash /opt/OS/scripts/scheduled/nightly_maintenance.sh
0 3 * * *   cd /opt/OS && python3 scripts/discord_daily_clear.py >> /opt/OS/logs/discord_clear.log 2>&1
0 3 * * *   bash /opt/OS/scripts/scheduled/nightly_consolidation.sh >> /opt/OS/logs/nightly_consolidation.log 2>&1
```
- `nightly_maintenance.sh` — claude -p ($0.50 cap): service health, import check, memory compression, temp cleanup, Notion sync, GWS auth check, ICP signal research
- `discord_daily_clear.py` — clears daily Discord channels for fresh start
- `nightly_consolidation.sh` — flock-protected memory pipeline: summarize conversations, promote to wiki

**EARLY MORNING (4am-5:45am) — Data Collection**
```cron
0 4 * * *   docker-compose run --rm os-scraper >> /opt/OS/logs/scraper.log 2>&1
45 5 * * *  cd /opt/OS && python3 scripts/morning_intel.py >> /opt/OS/logs/morning_intel.log 2>&1
```
- `os-scraper` — Docker container for data scraping
- `morning_intel.py` — gathers intelligence for the morning brief

**MORNING PREP (5:30am-6:10am) — System Readiness + Briefing**
```cron
30 5 * * *  bash /opt/OS/scripts/scheduled/morning_prep.sh
0 6 * * *   cd /opt/OS && python3 eos_ai/orchestrator.py >> /opt/OS/logs/orchestrator.log 2>&1
5 6 * * *   python3 scripts/waiting_on_checker.py >> /opt/OS/logs/waiting_on.log 2>&1
10 6 * * *  python3 scripts/deadline_monitor.py >> /opt/OS/logs/deadlines.log 2>&1
```
- `morning_prep.sh` — claude -p ($0.30 cap): container check, API key verify, Neon connection test, GWS auth check
- `orchestrator.py` — master morning cycle, triggers the full briefing pipeline
- `waiting_on_checker.py` — flags items where others owe action
- `deadline_monitor.py` — alerts on approaching deadlines

**HIGH-FREQUENCY (every 5-15 min) — Continuous Monitoring**
```cron
*/5 * * * *   cd /opt/OS && python3 scripts/day_reminder.py >> /opt/OS/logs/day_reminder.log 2>&1
*/5 * * * *   cd /opt/OS && python3 scripts/agent_task_executor.py >> /opt/OS/scripts/agent_executor.log 2>&1
*/15 * * * *  cd /opt/OS && python3 scripts/call_prep.py >> /opt/OS/logs/call_prep.log 2>&1
*/15 * * * *  cd /opt/OS && python3 scripts/notion_tasks_sync.py >> /opt/OS/logs/notion_tasks_sync.log 2>&1
*/15 * * * *  python3 scripts/post_meeting_capture.py >> /opt/OS/logs/post_meeting.log 2>&1
*/15 * * * *  cd /opt/OS && python3 scripts/calendar_invite_handler.py >> /opt/OS/logs/calendar_invites.log 2>&1
*/15 * * * *  python3 scripts/noshow_detector.py >> /opt/OS/logs/noshow.log 2>&1
*/15 * * * *  python3 scripts/notion_sync_poller.py >> /opt/OS/logs/notion_sync.log 2>&1
```
- `day_reminder.py` (5min) — upcoming event alerts
- `agent_task_executor.py` (5min) — processes queued agent tasks
- `call_prep.py` (15min) — preps context for upcoming calls
- `notion_tasks_sync.py` (15min) — bidirectional Notion task sync
- `post_meeting_capture.py` (15min) — captures post-meeting notes
- `calendar_invite_handler.py` (15min) — processes new calendar invites
- `noshow_detector.py` (15min) — flags missed meetings
- `notion_sync_poller.py` (15min) — polls Notion for changes

**AFTERNOON + EVENING — Daily Checkpoints**
```cron
30 12 * * *  cd /opt/OS && python3 scripts/midday_checkin.py >> /opt/OS/logs/midday.log 2>&1
0 15 * * *   python3 /opt/OS/scripts/inbox_gps_afternoon.py >> /opt/OS/logs/email_gps.log 2>&1
0 18 * * *   cd /opt/OS && python3 scripts/eod_sync.py >> /opt/OS/logs/eod_sync.log 2>&1
0 23 * * *   python3 -c "..." >> /opt/OS/logs/email_review.log 2>&1
```
- `midday_checkin.py` (12:30pm) — midday progress check posted to Discord
- `inbox_gps_afternoon.py` (3pm) — afternoon email pass
- `eod_sync.py` (6pm) — end-of-day sync and status update
- Inline email reviewer (11pm) — nightly email review via EmailReviewer class

**WEEKLY — Strategic Reviews**
```cron
0 6 * * 0   bash /opt/OS/scripts/scheduled/weekly_review.sh
0 6 * * 0   cd /opt/OS && python3 scripts/portfolio_brief.py >> /opt/OS/logs/portfolio_brief.log 2>&1
0 7 * * 1   cd /opt/OS && python3 scripts/relationship_nurture.py >> /opt/OS/logs/nurture.log 2>&1
0 19 * * 0  cd /opt/OS && python3 scripts/weekly_review.py >> /opt/OS/logs/weekly_review.log 2>&1
0 20 * * 0  python3 scripts/week_architect.py >> /opt/OS/logs/week_architect.log 2>&1
```
- `weekly_review.sh` (Sun 6am) — claude -p ($1.00 cap): full health audit, imports, services, skills, errors, Discord report
- `portfolio_brief.py` (Sun 6am) — venture portfolio overview
- `relationship_nurture.py` (Mon 7am) — relationship maintenance prompts
- `weekly_review.py` (Sun 7pm) — weekly business review
- `week_architect.py` (Sun 8pm) — plans the upcoming week

### Daily Timeline (All Times Server-Local)

```
 2:00  nightly_maintenance.sh — health, cleanup, research
 3:00  discord_daily_clear.py — channel reset
 3:00  nightly_consolidation.sh — memory pipeline (flock)
 4:00  os-scraper (Docker) — data collection
 5:30  morning_prep.sh — system readiness
 5:45  morning_intel.py — intelligence gathering
 6:00  orchestrator.py — morning brief cycle
 6:05  waiting_on_checker.py — pending items
 6:10  deadline_monitor.py — deadline alerts
 ----  every 5 min: day_reminder, agent_task_executor
 ----  every 15 min: call_prep, notion_tasks_sync, post_meeting,
       calendar_invites, noshow_detector, notion_sync_poller
12:30  midday_checkin.py — progress checkpoint
15:00  inbox_gps_afternoon.py — email pass
18:00  eod_sync.py — end-of-day
23:00  email nightly review — inbox cleanup

WEEKLY:
Sun 6:00am  weekly_review.sh + portfolio_brief.py
Sun 7:00pm  weekly_review.py (business)
Sun 8:00pm  week_architect.py (next week plan)
Mon 7:00am  relationship_nurture.py
```

## Authentication

N/A for the cron daemon itself. Cron runs as the user whose crontab it reads (root
in EOS). Jobs that call external APIs load credentials from:
- `/opt/OS/eos_ai/.env` — Anthropic, Gemini, Neon, Groq, Perplexity keys
- `/opt/OS/services/.env` — Discord, Instagram tokens

Shell scripts using `claude -p` inherit the `ANTHROPIC_API_KEY` from the environment.
Budget caps (`--max-budget-usd`) are the authorization boundary for AI spend.

## Quick Reference

### Cron time expression syntax
```
 ┌───────────── minute (0-59)
 │ ┌─────────── hour (0-23)
 │ │ ┌───────── day of month (1-31)
 │ │ │ ┌─────── month (1-12 or jan-dec)
 │ │ │ │ ┌───── day of week (0-7, 0 and 7 = Sunday, or sun-sat)
 │ │ │ │ │
 * * * * *  command
```

### Common schedule expressions used in EOS
```
*/5 * * * *    every 5 minutes
*/15 * * * *   every 15 minutes
0 6 * * *      daily at 6:00am
30 5 * * *     daily at 5:30am
0 2 * * *      daily at 2:00am (maintenance window)
0 6 * * 0      Sunday at 6:00am
0 7 * * 1      Monday at 7:00am
0 19 * * 0     Sunday at 7:00pm
```

### flock pattern for mutual exclusion
```bash
LOCK_FILE="/tmp/eos_jobname.lock"
exec 200>"$LOCK_FILE"
if ! flock --nonblock 200; then
    echo "SKIP: already running" >> "$LOG_FILE"
    exit 0
fi
# ... job body runs with lock held ...
# Lock auto-releases when script exits (fd 200 closes)
```

### Standard logging pattern
```cron
0 6 * * * cd /opt/OS && python3 scripts/foo.py >> /opt/OS/logs/foo.log 2>&1
```
Always: `>> append` (not `>` overwrite), `2>&1` captures stderr, `cd /opt/OS` sets working dir.

### claude -p budget-capped pattern
```bash
claude -p --allowedTools "Bash Read Write Edit Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.50 \
  "Prompt here" >> "$LOG" 2>&1
```

### Edit crontab
```bash
crontab -e          # edit current user's crontab
crontab -l          # list current crontab
crontab -l | wc -l  # count entries
```

### Add a new job (append pattern)
```bash
(crontab -l 2>/dev/null; echo "0 9 * * * cd /opt/OS && python3 scripts/new_job.py >> /opt/OS/logs/new_job.log 2>&1") | crontab -
```

## Conceptual Model

```
cron daemon (crond)
  |
  +-- Reads crontab every minute
  |     |-- /var/spool/cron/crontabs/root (user crontab)
  |     +-- /etc/cron.d/* (system drop-in files)
  |
  +-- For each matching entry:
  |     |-- Fork shell (/bin/sh by default)
  |     |-- Set env: HOME, LOGNAME, SHELL, PATH (minimal!)
  |     |-- Execute command
  |     |-- Capture stdout/stderr → mail to user (unless redirected)
  |     +-- No dependency graph — all matching jobs fire independently
  |
  +-- EOS job types:
        |-- Shell wrappers (scripts/scheduled/*.sh)
        |     |-- set -euo pipefail
        |     |-- flock for mutual exclusion
        |     |-- claude -p with budget cap
        |     +-- Structured logging with timestamps
        |
        |-- Direct Python (python3 scripts/*.py)
        |     |-- >> log 2>&1 for output capture
        |     |-- cd /opt/OS for correct working directory
        |     +-- sys.path.insert + dotenv for EOS imports
        |
        +-- Docker (docker-compose run --rm)
              +-- Ephemeral container, removed after run
```

See references/best_practices.md for flock patterns, timezone handling, error recovery, and anti-patterns.

## Gotchas

### PATH is minimal in cron
Cron sets PATH to `/usr/bin:/bin` by default. Commands like `docker-compose`, `claude`,
`npx`, `node` may not be found. EOS shell scripts work because `claude` is in `/usr/local/bin`
which is in the default PATH on this VPS, but this is not guaranteed after system updates.
Fix: add `PATH=/usr/local/bin:/usr/bin:/bin` at top of crontab or use absolute paths.

### Working directory is HOME, not /opt/OS
Cron jobs start in the user's HOME directory. Scripts that use relative imports or
relative file paths will fail silently. EOS pattern: always `cd /opt/OS &&` before
the command, or use absolute paths in the script itself.

### Two jobs at 3:00am compete for resources
Both `discord_daily_clear.py` and `nightly_consolidation.sh` fire at `0 3 * * *`.
The consolidation script uses flock to prevent overlap with itself, but both jobs
running simultaneously can compete for CPU/memory. If consolidation uses claude -p
in the future, this becomes a budget conflict. Consider staggering by 5 minutes.

### Two jobs at Sunday 6:00am
Both `weekly_review.sh` (claude -p $1.00 cap) and `portfolio_brief.py` fire at
`0 6 * * 0`. The weekly review uses claude -p which holds an API session.
Portfolio brief may also call LLMs. Stagger these.

### flock lock files persist in /tmp
Lock files in `/tmp` survive reboots on some systems (tmpfs) and persist on others
(disk-backed /tmp). A stale lock file does NOT block flock (flock operates on the
file descriptor, not file existence). But `/tmp` cleanup by systemd-tmpfiles can
remove the lock file mid-run if the file is old, causing flock to lose the lock.
EOS mitigation: lock files are re-created each run via `exec 200>"$LOCK_FILE"`.

### Cron has no job dependency graph
Unlike systemd timers or Airflow, cron has zero awareness of job dependencies.
The morning pipeline relies on ordering by time (5:30 prep, 5:45 intel, 6:00
orchestrator) but if prep overruns, orchestrator fires anyway. No mechanism
exists to wait or retry. Current EOS mitigation: generous time gaps between
dependent jobs.

### stderr swallowed without 2>&1
If a crontab line omits `2>&1`, stderr goes to cron's mail system (usually
/var/mail/root) instead of the log file. Most EOS jobs include `2>&1` but
check any new additions.

### claude -p budget conflicts
Multiple claude -p jobs running simultaneously (e.g., nightly_maintenance.sh
overlapping with morning_prep.sh) each have independent budget caps but share
the same Anthropic API key. If the key has a global spend limit, parallel jobs
can exhaust it, causing one to fail with a 429 or auth error.

### Inline python3 -c quoting hell
The 11pm email reviewer uses a long inline `python3 -c "..."` in the crontab.
Cron uses `%` as newline in the command field (percent signs must be escaped as
`\%`). Complex inline Python should be extracted to a standalone script file.
=======
---
name: cron
description: "Use when adding, modifying, debugging, or auditing scheduled jobs in EOS — including crontab entries, flock locking, log rotation, claude -p budget caps, or diagnosing why a scheduled task did not fire."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://man7.org/linux/man-pages/man5/crontab.5.html"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "vixie-cron (Debian/Ubuntu default)"
sdk_version: "cron 3.0pl1-137 (Ubuntu)"
speed_category: fast
trigger: both
effort: medium
context: fork
---

# Tool: Cron (Scheduled Task Management)

## What This Tool Does

Cron is the POSIX job scheduler daemon that executes commands on a time-based schedule
defined in crontab files. Each line in a crontab maps a five-field time expression
(minute, hour, day-of-month, month, day-of-week) to a shell command. The daemon wakes
every minute, checks all crontabs, and runs any jobs whose time expression matches the
current wall-clock time.

EOS uses cron as the heartbeat of the entire operating system. 26+ jobs orchestrate the
daily cycle: nightly maintenance, morning prep, intelligence briefs, pipeline monitoring,
meeting detection, memory consolidation, and weekly reviews. Jobs fall into five categories:

- **Shell wrappers** (`scripts/scheduled/*.sh`) — multi-step workflows using `claude -p`
  with budget caps and flock mutual exclusion
- **Direct Python** — single-purpose scripts invoked as `python3 /opt/OS/scripts/foo.py`
- **Inline Python** — one-liner `python3 -c "..."` for simple operations
- **Docker commands** — `docker-compose run` for containerized tasks
- **Orchestrator** — the 6am orchestrator that triggers the full morning cycle

## EOS Integration

### Complete Crontab — Annotated by Category

**NIGHTLY (2am-3am) — Maintenance Window**
```cron
0 2 * * *   bash /opt/OS/scripts/scheduled/nightly_maintenance.sh
0 3 * * *   cd /opt/OS && python3 scripts/discord_daily_clear.py >> /opt/OS/logs/discord_clear.log 2>&1
0 3 * * *   bash /opt/OS/scripts/scheduled/nightly_consolidation.sh >> /opt/OS/logs/nightly_consolidation.log 2>&1
```
- `nightly_maintenance.sh` — claude -p ($0.50 cap): service health, import check, memory compression, temp cleanup, Notion sync, GWS auth check, ICP signal research
- `discord_daily_clear.py` — clears daily Discord channels for fresh start
- `nightly_consolidation.sh` — flock-protected memory pipeline: summarize conversations, promote to wiki

**EARLY MORNING (4am-5:45am) — Data Collection**
```cron
0 4 * * *   docker-compose run --rm os-scraper >> /opt/OS/logs/scraper.log 2>&1
45 5 * * *  cd /opt/OS && python3 scripts/morning_intel.py >> /opt/OS/logs/morning_intel.log 2>&1
```
- `os-scraper` — Docker container for data scraping
- `morning_intel.py` — gathers intelligence for the morning brief

**MORNING PREP (5:30am-6:10am) — System Readiness + Briefing**
```cron
30 5 * * *  bash /opt/OS/scripts/scheduled/morning_prep.sh
0 6 * * *   cd /opt/OS && python3 eos_ai/orchestrator.py >> /opt/OS/logs/orchestrator.log 2>&1
5 6 * * *   python3 scripts/waiting_on_checker.py >> /opt/OS/logs/waiting_on.log 2>&1
10 6 * * *  python3 scripts/deadline_monitor.py >> /opt/OS/logs/deadlines.log 2>&1
```
- `morning_prep.sh` — claude -p ($0.30 cap): container check, API key verify, Neon connection test, GWS auth check
- `orchestrator.py` — master morning cycle, triggers the full briefing pipeline
- `waiting_on_checker.py` — flags items where others owe action
- `deadline_monitor.py` — alerts on approaching deadlines

**HIGH-FREQUENCY (every 5-15 min) — Continuous Monitoring**
```cron
*/5 * * * *   cd /opt/OS && python3 scripts/day_reminder.py >> /opt/OS/logs/day_reminder.log 2>&1
*/5 * * * *   cd /opt/OS && python3 scripts/agent_task_executor.py >> /opt/OS/scripts/agent_executor.log 2>&1
*/15 * * * *  cd /opt/OS && python3 scripts/call_prep.py >> /opt/OS/logs/call_prep.log 2>&1
*/15 * * * *  cd /opt/OS && python3 scripts/notion_tasks_sync.py >> /opt/OS/logs/notion_tasks_sync.log 2>&1
*/15 * * * *  python3 scripts/post_meeting_capture.py >> /opt/OS/logs/post_meeting.log 2>&1
*/15 * * * *  cd /opt/OS && python3 scripts/calendar_invite_handler.py >> /opt/OS/logs/calendar_invites.log 2>&1
*/15 * * * *  python3 scripts/noshow_detector.py >> /opt/OS/logs/noshow.log 2>&1
*/15 * * * *  python3 scripts/notion_sync_poller.py >> /opt/OS/logs/notion_sync.log 2>&1
```
- `day_reminder.py` (5min) — upcoming event alerts
- `agent_task_executor.py` (5min) — processes queued agent tasks
- `call_prep.py` (15min) — preps context for upcoming calls
- `notion_tasks_sync.py` (15min) — bidirectional Notion task sync
- `post_meeting_capture.py` (15min) — captures post-meeting notes
- `calendar_invite_handler.py` (15min) — processes new calendar invites
- `noshow_detector.py` (15min) — flags missed meetings
- `notion_sync_poller.py` (15min) — polls Notion for changes

**AFTERNOON + EVENING — Daily Checkpoints**
```cron
30 12 * * *  cd /opt/OS && python3 scripts/midday_checkin.py >> /opt/OS/logs/midday.log 2>&1
0 15 * * *   python3 /opt/OS/scripts/inbox_gps_afternoon.py >> /opt/OS/logs/email_gps.log 2>&1
0 18 * * *   cd /opt/OS && python3 scripts/eod_sync.py >> /opt/OS/logs/eod_sync.log 2>&1
0 23 * * *   python3 -c "..." >> /opt/OS/logs/email_review.log 2>&1
```
- `midday_checkin.py` (12:30pm) — midday progress check posted to Discord
- `inbox_gps_afternoon.py` (3pm) — afternoon email pass
- `eod_sync.py` (6pm) — end-of-day sync and status update
- Inline email reviewer (11pm) — nightly email review via EmailReviewer class

**WEEKLY — Strategic Reviews**
```cron
0 6 * * 0   bash /opt/OS/scripts/scheduled/weekly_review.sh
0 6 * * 0   cd /opt/OS && python3 scripts/portfolio_brief.py >> /opt/OS/logs/portfolio_brief.log 2>&1
0 7 * * 1   cd /opt/OS && python3 scripts/relationship_nurture.py >> /opt/OS/logs/nurture.log 2>&1
0 19 * * 0  cd /opt/OS && python3 scripts/weekly_review.py >> /opt/OS/logs/weekly_review.log 2>&1
0 20 * * 0  python3 scripts/week_architect.py >> /opt/OS/logs/week_architect.log 2>&1
```
- `weekly_review.sh` (Sun 6am) — claude -p ($1.00 cap): full health audit, imports, services, skills, errors, Discord report
- `portfolio_brief.py` (Sun 6am) — venture portfolio overview
- `relationship_nurture.py` (Mon 7am) — relationship maintenance prompts
- `weekly_review.py` (Sun 7pm) — weekly business review
- `week_architect.py` (Sun 8pm) — plans the upcoming week

### Daily Timeline (All Times Server-Local)

```
 2:00  nightly_maintenance.sh — health, cleanup, research
 3:00  discord_daily_clear.py — channel reset
 3:00  nightly_consolidation.sh — memory pipeline (flock)
 4:00  os-scraper (Docker) — data collection
 5:30  morning_prep.sh — system readiness
 5:45  morning_intel.py — intelligence gathering
 6:00  orchestrator.py — morning brief cycle
 6:05  waiting_on_checker.py — pending items
 6:10  deadline_monitor.py — deadline alerts
 ----  every 5 min: day_reminder, agent_task_executor
 ----  every 15 min: call_prep, notion_tasks_sync, post_meeting,
       calendar_invites, noshow_detector, notion_sync_poller
12:30  midday_checkin.py — progress checkpoint
15:00  inbox_gps_afternoon.py — email pass
18:00  eod_sync.py — end-of-day
23:00  email nightly review — inbox cleanup

WEEKLY:
Sun 6:00am  weekly_review.sh + portfolio_brief.py
Sun 7:00pm  weekly_review.py (business)
Sun 8:00pm  week_architect.py (next week plan)
Mon 7:00am  relationship_nurture.py
```

## Authentication

N/A for the cron daemon itself. Cron runs as the user whose crontab it reads (root
in EOS). Jobs that call external APIs load credentials from:
- `/opt/OS/eos_ai/.env` — Anthropic, Gemini, Neon, Groq, Perplexity keys
- `/opt/OS/services/.env` — Discord, Instagram tokens

Shell scripts using `claude -p` inherit the `ANTHROPIC_API_KEY` from the environment.
Budget caps (`--max-budget-usd`) are the authorization boundary for AI spend.

## Quick Reference

### Cron time expression syntax
```
 ┌───────────── minute (0-59)
 │ ┌─────────── hour (0-23)
 │ │ ┌───────── day of month (1-31)
 │ │ │ ┌─────── month (1-12 or jan-dec)
 │ │ │ │ ┌───── day of week (0-7, 0 and 7 = Sunday, or sun-sat)
 │ │ │ │ │
 * * * * *  command
```

### Common schedule expressions used in EOS
```
*/5 * * * *    every 5 minutes
*/15 * * * *   every 15 minutes
0 6 * * *      daily at 6:00am
30 5 * * *     daily at 5:30am
0 2 * * *      daily at 2:00am (maintenance window)
0 6 * * 0      Sunday at 6:00am
0 7 * * 1      Monday at 7:00am
0 19 * * 0     Sunday at 7:00pm
```

### flock pattern for mutual exclusion
```bash
LOCK_FILE="/tmp/eos_jobname.lock"
exec 200>"$LOCK_FILE"
if ! flock --nonblock 200; then
    echo "SKIP: already running" >> "$LOG_FILE"
    exit 0
fi
# ... job body runs with lock held ...
# Lock auto-releases when script exits (fd 200 closes)
```

### Standard logging pattern
```cron
0 6 * * * cd /opt/OS && python3 scripts/foo.py >> /opt/OS/logs/foo.log 2>&1
```
Always: `>> append` (not `>` overwrite), `2>&1` captures stderr, `cd /opt/OS` sets working dir.

### claude -p budget-capped pattern
```bash
claude -p --allowedTools "Bash Read Write Edit Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.50 \
  "Prompt here" >> "$LOG" 2>&1
```

### Edit crontab
```bash
crontab -e          # edit current user's crontab
crontab -l          # list current crontab
crontab -l | wc -l  # count entries
```

### Add a new job (append pattern)
```bash
(crontab -l 2>/dev/null; echo "0 9 * * * cd /opt/OS && python3 scripts/new_job.py >> /opt/OS/logs/new_job.log 2>&1") | crontab -
```

## Conceptual Model

```
cron daemon (crond)
  |
  +-- Reads crontab every minute
  |     |-- /var/spool/cron/crontabs/root (user crontab)
  |     +-- /etc/cron.d/* (system drop-in files)
  |
  +-- For each matching entry:
  |     |-- Fork shell (/bin/sh by default)
  |     |-- Set env: HOME, LOGNAME, SHELL, PATH (minimal!)
  |     |-- Execute command
  |     |-- Capture stdout/stderr → mail to user (unless redirected)
  |     +-- No dependency graph — all matching jobs fire independently
  |
  +-- EOS job types:
        |-- Shell wrappers (scripts/scheduled/*.sh)
        |     |-- set -euo pipefail
        |     |-- flock for mutual exclusion
        |     |-- claude -p with budget cap
        |     +-- Structured logging with timestamps
        |
        |-- Direct Python (python3 scripts/*.py)
        |     |-- >> log 2>&1 for output capture
        |     |-- cd /opt/OS for correct working directory
        |     +-- sys.path.insert + dotenv for EOS imports
        |
        +-- Docker (docker-compose run --rm)
              +-- Ephemeral container, removed after run
```

See references/best_practices.md for flock patterns, timezone handling, error recovery, and anti-patterns.

## Gotchas

### PATH is minimal in cron
Cron sets PATH to `/usr/bin:/bin` by default. Commands like `docker-compose`, `claude`,
`npx`, `node` may not be found. EOS shell scripts work because `claude` is in `/usr/local/bin`
which is in the default PATH on this VPS, but this is not guaranteed after system updates.
Fix: add `PATH=/usr/local/bin:/usr/bin:/bin` at top of crontab or use absolute paths.

### Working directory is HOME, not /opt/OS
Cron jobs start in the user's HOME directory. Scripts that use relative imports or
relative file paths will fail silently. EOS pattern: always `cd /opt/OS &&` before
the command, or use absolute paths in the script itself.

### Two jobs at 3:00am compete for resources
Both `discord_daily_clear.py` and `nightly_consolidation.sh` fire at `0 3 * * *`.
The consolidation script uses flock to prevent overlap with itself, but both jobs
running simultaneously can compete for CPU/memory. If consolidation uses claude -p
in the future, this becomes a budget conflict. Consider staggering by 5 minutes.

### Two jobs at Sunday 6:00am
Both `weekly_review.sh` (claude -p $1.00 cap) and `portfolio_brief.py` fire at
`0 6 * * 0`. The weekly review uses claude -p which holds an API session.
Portfolio brief may also call LLMs. Stagger these.

### flock lock files persist in /tmp
Lock files in `/tmp` survive reboots on some systems (tmpfs) and persist on others
(disk-backed /tmp). A stale lock file does NOT block flock (flock operates on the
file descriptor, not file existence). But `/tmp` cleanup by systemd-tmpfiles can
remove the lock file mid-run if the file is old, causing flock to lose the lock.
EOS mitigation: lock files are re-created each run via `exec 200>"$LOCK_FILE"`.

### Cron has no job dependency graph
Unlike systemd timers or Airflow, cron has zero awareness of job dependencies.
The morning pipeline relies on ordering by time (5:30 prep, 5:45 intel, 6:00
orchestrator) but if prep overruns, orchestrator fires anyway. No mechanism
exists to wait or retry. Current EOS mitigation: generous time gaps between
dependent jobs.

### stderr swallowed without 2>&1
If a crontab line omits `2>&1`, stderr goes to cron's mail system (usually
/var/mail/root) instead of the log file. Most EOS jobs include `2>&1` but
check any new additions.

### claude -p budget conflicts
Multiple claude -p jobs running simultaneously (e.g., nightly_maintenance.sh
overlapping with morning_prep.sh) each have independent budget caps but share
the same Anthropic API key. If the key has a global spend limit, parallel jobs
can exhaust it, causing one to fail with a 429 or auth error.

### Inline python3 -c quoting hell
The 11pm email reviewer uses a long inline `python3 -c "..."` in the crontab.
Cron uses `%` as newline in the command field (percent signs must be escaped as
`\%`). Complex inline Python should be extracted to a standalone script file.
>>>>>>> Stashed changes
