---
name: bash
description: "Use when writing, modifying, or debugging shell scripts in the EOS codebase — covers cron scheduling, flock locking, set -euo pipefail, trap patterns, exit codes, parameter expansion, log rotation, and claude -p automation wrappers."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://www.gnu.org/software/bash/manual/bash.html"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Bash 5.2"
sdk_version: "GNU coreutils, flock, date, find, tar, docker"
speed_category: stable
trigger: both
effort: medium
context: fork
---

# Tool: Bash

## What This Tool Does

Bash is the POSIX-compatible shell and scripting language that serves as the glue layer for EOS. Every scheduled automation, every cron job, every Docker lifecycle command, and every `claude -p` autonomous agent invocation runs through bash. The EOS codebase uses bash for:

- **Cron scheduling** — 25+ cron entries dispatch Python scripts and bash wrappers on intervals from every 5 minutes to weekly
- **Process locking** — `flock` prevents overlapping cron runs for long-running jobs
- **Service lifecycle** — `docker restart`, `docker ps`, `docker logs` for container management
- **Autonomous agent wrappers** — `claude -p` invocations with budget caps, tool allowlists, and prompt injection for nightly/morning/weekly cycles
- **Backup and log rotation** — `tar`, `find -mtime -delete` for housekeeping
- **Environment bootstrapping** — `install.sh`, `setup.sh` for first-run provisioning
- **Deployment sync** — file copy loops with verification steps

## EOS Integration

### Scheduled scripts (scripts/scheduled/)
All cron-invoked bash scripts live in `scripts/scheduled/`:

| Script | Schedule | Purpose |
|--------|----------|---------|
| `nightly_maintenance.sh` | 2:00am daily | Service health, import check, memory compression, log cleanup, research cycle |
| `morning_prep.sh` | 5:30am daily | Container check, API key check, Neon connection, GWS auth verification |
| `weekly_review.sh` | Sun 6:00am | Full health audit, skill count, error scan, Discord report |
| `nightly_consolidation.sh` | 3:00am daily | flock-protected memory pipeline: summarize conversations, promote to wiki |

### Cron architecture
The crontab has 25+ entries split into two categories:
1. **Bash wrappers** — `bash /opt/OS/scripts/scheduled/*.sh` for multi-step autonomous workflows
2. **Direct Python** — `python3 /opt/OS/scripts/*.py >> /opt/OS/logs/*.log 2>&1` for single-script jobs

Bash wrappers are used when:
- The job needs `claude -p` (autonomous agent with budget cap)
- The job needs `flock` (mutual exclusion)
- The job has multiple sequential steps that should fail-fast

Direct Python is used when:
- The script is self-contained
- No locking or agent orchestration needed

### Standard patterns found in EOS

**Strict mode header (all scripts):**
```bash
#!/bin/bash
set -euo pipefail
```

**Date-stamped logging:**
```bash
LOG="/opt/OS/logs/nightly_$(date +%Y%m%d).log"
echo "=== EOS Nightly Maintenance: $(date) ===" >> "$LOG"
```

**flock mutual exclusion (nightly_consolidation.sh):**
```bash
LOCK_FILE="/tmp/eos_nightly_consolidation.lock"
exec 200>"$LOCK_FILE"
if ! flock --nonblock 200; then
    echo "[$(date -Iseconds)] SKIP: another consolidation is already running" >> "$LOG_FILE"
    exit 0
fi
```

**claude -p autonomous agent wrapper:**
```bash
claude -p --allowedTools "Bash Read Write Edit Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.50 \
  "Read /opt/OS/.claude/CLAUDE.md and /opt/OS/CLAUDE.md.
  ... prompt body ..." >> "$LOG" 2>&1
```

**Log rotation (backup.sh, nightly_maintenance.sh):**
```bash
find /opt/OS/logs -name '*.log' -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
```

**Prerequisite check (install.sh):**
```bash
command -v docker >/dev/null 2>&1 || {
  echo "Docker required."
  exit 1
}
```

**Array iteration with sync (sync.sh):**
```bash
TARGETS=(
  "$HOME/.claude/skills/last30days"
  "$HOME/.agents/skills/last30days"
)
for t in "${TARGETS[@]}"; do
  mkdir -p "$t/scripts/lib"
  cp "$SRC/SKILL.md" "$t/"
done
```

### Standalone utility scripts
- `scripts/backup.sh` — daily tar.gz of critical files, 7-day retention
- `setup.sh` — first-run wizard: env check, pip install, Ollama install, Python setup
- `install.sh` — one-liner installer: prerequisite check, git clone, env file creation
- `.agents/skills/last30days/scripts/sync.sh` — multi-target file deploy with import verification

## Authentication

Bash itself has no authentication. EOS bash scripts handle secrets through these patterns:

**Loading .env files:**
```bash
source eos_ai/.env 2>/dev/null || true
```

**Checking required env vars:**
```bash
if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL not set in eos_ai/.env"
  exit 1
fi
```

**Passing secrets to Python subprocesses:**
```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
key = os.getenv('ANTHROPIC_API_KEY','')
print('Anthropic key:', 'set' if key else 'MISSING')
"
```

Secrets live in `eos_ai/.env` and `services/.env`. Never `echo` or `cat` these files. Never pass secrets as command-line arguments (visible in `ps`). Always load via `source` or `python3 -c` with `load_dotenv`.

## Quick Reference

### Start a new EOS bash script
```bash
#!/usr/bin/env bash
# Description of what this does
set -euo pipefail

cd /opt/OS
LOG="/opt/OS/logs/scriptname_$(date +%Y%m%d).log"
echo "=== Script Start: $(date) ===" >> "$LOG"

# ... body ...

echo "=== Done: $(date) ===" >> "$LOG"
```

### Add a cron job
```bash
# Edit crontab
crontab -e

# Format: minute hour day month weekday command
# Every day at 3am:
0 3 * * * bash /opt/OS/scripts/scheduled/myscript.sh >> /opt/OS/logs/myscript.log 2>&1

# Every 15 minutes:
*/15 * * * * cd /opt/OS && python3 scripts/myscript.py >> /opt/OS/logs/myscript.log 2>&1

# Sunday at 6am:
0 6 * * 0 bash /opt/OS/scripts/scheduled/weekly.sh
```

### flock-protect a cron job
```bash
LOCK="/tmp/eos_myjob.lock"
exec 200>"$LOCK"
if ! flock --nonblock 200; then
    echo "SKIP: already running" >> "$LOG"
    exit 0
fi
# Lock held until script exits (fd 200 auto-closes)
```

### Run claude -p with budget cap
```bash
claude -p --allowedTools "Bash Read Write Edit Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.50 \
  "Your prompt here" >> "$LOG" 2>&1
```

### Docker service management
```bash
# Check all containers
docker ps --format '{{.Names}}: {{.Status}}'

# Restart a specific container (use container_name, not service)
docker restart os-discord

# Tail logs
docker logs os-discord --tail 20

# Full rebuild (only when requirements.txt changes)
docker compose build --no-cache os-discord
docker compose up -d os-discord
```

### Safe file cleanup with age filter
```bash
find /opt/OS/logs -name '*.log' -mtime +7 -delete 2>/dev/null || true
find /tmp -name 'eos_*' -mtime +1 -delete 2>/dev/null || true
```

### Backup with date stamp and retention
```bash
ARCHIVE="/opt/OS/backups/eos_backup_$(date +%Y%m%d).tar.gz"
tar -czf "$ARCHIVE" /opt/OS/data/ /opt/OS/eos_ai/*.py 2>/dev/null
find /opt/OS/backups -name "*.tar.gz" -mtime +7 -delete
```

## Conceptual Model

```
Bash in EOS
  |
  +-- Cron Scheduler (crontab)
  |     |-- 25+ entries: Python scripts + bash wrappers
  |     |-- Timing: */5 (high freq) to weekly (0 6 * * 0)
  |     |-- Output: >> /opt/OS/logs/*.log 2>&1
  |     +-- All times in server TZ (check with `timedatectl`)
  |
  +-- Bash Wrappers (scripts/scheduled/*.sh)
  |     |-- set -euo pipefail (strict mode)
  |     |-- flock for mutual exclusion
  |     |-- claude -p for autonomous agent runs
  |     |-- Date-stamped log files
  |     +-- Exit code propagation
  |
  +-- Utility Scripts (setup.sh, install.sh, backup.sh)
  |     |-- Prerequisite checking (command -v)
  |     |-- Environment bootstrapping
  |     |-- File operations (tar, find, cp)
  |     +-- User-facing output
  |
  +-- Inline Bash (from Python, claude -p prompts)
        |-- docker ps/restart/logs
        |-- find + delete for cleanup
        |-- python3 -c for one-liner checks
        +-- Source .env for secret loading
```

See references/best_practices.md for error handling patterns, parameter expansion, quoting rules, and anti-patterns.

## Gotchas

### 1. Cron PATH is minimal
Cron runs with a stripped `PATH` (typically `/usr/bin:/bin`). Commands like `docker`, `claude`, `ollama`, or `npm`/`npx` may not be found. EOS scripts work around this by using absolute paths (`bash /opt/OS/scripts/...`) or by relying on Python's full path resolution. If a cron job silently fails, check `PATH` first.

### 2. flock fd must stay open for the lock to hold
The `exec 200>"$LOCK_FILE"` + `flock 200` pattern works because fd 200 stays open for the script's lifetime. If you refactor to a subshell `(flock 200; ...)`, the lock releases when the subshell exits, not when the parent exits. The EOS `nightly_consolidation.sh` pattern is correct — do not change it to a subshell form.

### 3. set -e does not catch pipe failures
`set -e` exits on the first failing command, but `cmd1 | cmd2` only checks `cmd2`'s exit code by default. Add `set -o pipefail` (which EOS already does via `set -euo pipefail`) to catch failures in any pipe stage. Without `pipefail`, a failing `grep` piped to `wc` silently succeeds.

### 4. Unquoted variables split on whitespace and glob
`$VAR` without quotes splits on IFS and expands globs. File paths with spaces break. `set -u` catches unset variables but not this. Always use `"$VAR"`. The only exception is intentional word splitting (e.g., `$ARGS` in `nightly_consolidation.sh` where args are space-separated flags).

### 5. stderr goes to cron's mail, not your log
`>> /opt/OS/logs/foo.log` only captures stdout. Without `2>&1`, stderr goes to cron's MAILTO (often `/dev/null` or bounces). Every EOS cron entry MUST end with `>> logfile 2>&1` to capture both streams.

### 6. claude -p prompt escaping is fragile
Dollar signs, backticks, and double quotes inside `claude -p` prompt strings get interpreted by bash before reaching Claude. EOS uses backslash escaping (`\$`, `\"`) inside the prompt. For complex prompts, consider heredoc syntax or a separate prompt file.

### 7. date format must match YYYY-MM-DD convention
EOS uses `$(date +%Y%m%d)` for filenames (no hyphens for cleaner paths) and `$(date +%Y-%m-%d)` for log content. Using `$(date)` without a format gives locale-dependent output that breaks parsing. Always specify the format string.

### 8. backup.sh does not use set -euo pipefail
Unlike the scheduled scripts, `scripts/backup.sh` lacks strict mode. A failing `tar` (e.g., missing source directory) silently continues. If modifying this script, add `set -euo pipefail` and handle missing paths explicitly.

### 9. source .env exposes variables to the entire shell
`source eos_ai/.env` makes all variables available as shell globals. If a variable name collides with a bash builtin or another script's variable, it silently overwrites. The Python `load_dotenv` approach is safer for production scripts. Use `source` only in setup/install contexts.
