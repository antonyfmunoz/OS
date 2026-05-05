# Bash -- Creator-Level Best Practices
Source: https://www.gnu.org/software/bash/manual/bash.html
API Version: Bash 5.2 (GNU, Linux)
SDK Version: GNU coreutils, util-linux (flock), findutils
Last Researched: 2026-04-06

---

# Tier 1 -- Technical Mastery

## Authentication

Bash has no API authentication. In EOS, bash scripts handle secrets through environment variable loading.

**Secret storage:**
- `eos_ai/.env` -- DATABASE_URL, ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, PERPLEXITY_API_KEY, EOS_ORG_ID, EOS_USER_ID
- `services/.env` -- DISCORD_BOT_TOKEN, FOUNDER_DISCORD_ID, DISCORD_BRIEF_WEBHOOK, channel IDs

**Loading patterns:**
```bash
# Source directly (exposes to shell -- use only in setup scripts)
source eos_ai/.env 2>/dev/null || true

# Check required vars after sourcing
if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL not set" >&2
  exit 1
fi

# Prefer Python load_dotenv for production scripts
python3 -c "
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
import os
print(os.getenv('ANTHROPIC_API_KEY', 'MISSING'))
"
```

**Security rules:**
- Never `echo "$SECRET"` -- visible in logs
- Never pass secrets as CLI args -- visible in `ps aux`
- Never commit .env files -- both are in `.gitignore`
- Use `${VAR:-}` with `set -u` to safely test if a var is set without erroring

## Core Operations with Exact Signatures

### Strict mode
```bash
set -e          # Exit on first error (non-zero exit code)
set -u          # Error on undefined variables
set -o pipefail # Pipe returns rightmost non-zero exit code
# Combined:
set -euo pipefail
```

### Variable operations
```bash
# Assignment (no spaces around =)
VAR="value"

# Parameter expansion
${VAR}              # Value of VAR
${VAR:-default}     # Default if unset or empty
${VAR:=default}     # Assign default if unset or empty
${VAR:+alternate}   # Alternate if set and non-empty
${VAR:?error msg}   # Error and exit if unset or empty

# String manipulation
${VAR#pattern}      # Remove shortest prefix match
${VAR##pattern}     # Remove longest prefix match
${VAR%pattern}      # Remove shortest suffix match
${VAR%%pattern}     # Remove longest suffix match
${VAR/old/new}      # Replace first match
${VAR//old/new}     # Replace all matches
${#VAR}             # String length
${VAR:offset:length} # Substring
```

### Conditionals
```bash
# Test command (prefer [[ ]] over [ ])
[[ -f "$FILE" ]]     # File exists and is regular file
[[ -d "$DIR" ]]      # Directory exists
[[ -z "$VAR" ]]      # String is empty
[[ -n "$VAR" ]]      # String is non-empty
[[ "$A" == "$B" ]]   # String equality
[[ "$A" =~ regex ]]  # Regex match (no quotes on regex)
[[ "$A" -eq "$B" ]]  # Integer equality
[[ "$A" -lt "$B" ]]  # Integer less than

# Arithmetic
(( count++ ))
(( x = a + b ))
(( x > 0 )) && echo "positive"
```

### Process control
```bash
# Background + wait
long_task &
PID=$!
wait $PID
EXIT_CODE=$?

# Subshell (isolated env)
(cd /tmp && do_something)
# Parent's cwd unchanged

# Command substitution
RESULT=$(command_here)
RESULT=$(command_here 2>&1)  # Capture stderr too

# Process substitution
diff <(sort file1) <(sort file2)

# Heredoc
cat << 'EOF'
Literal content, no expansion
EOF

cat << EOF
Expanded content: $VAR
EOF
```

### File descriptors and redirection
```bash
command > file       # stdout to file (overwrite)
command >> file      # stdout to file (append)
command 2>&1         # stderr to stdout
command &> file      # both to file (bash-specific)
command > /dev/null 2>&1  # silence all output
exec 3>file          # open fd 3 for writing
echo "data" >&3     # write to fd 3
exec 3>&-            # close fd 3
```

## Pagination Patterns

Bash does not have pagination in the API sense. The equivalent is processing large datasets in chunks through pipelines.

**Line-by-line processing (streaming):**
```bash
while IFS= read -r line; do
  process "$line"
done < input_file

# Or from a command
command | while IFS= read -r line; do
  process "$line"
done
```

**Batch processing with xargs:**
```bash
# Process 10 items at a time
find /opt/OS/logs -name '*.log' -print0 | xargs -0 -n 10 process_batch

# Parallel execution (4 jobs)
find . -name '*.py' -print0 | xargs -0 -P 4 -n 1 python3 -m py_compile
```

**Chunked file reading:**
```bash
# Read N lines at a time
split -l 1000 bigfile.txt chunk_
for chunk in chunk_*; do
  process "$chunk"
  rm "$chunk"
done
```

## Rate Limits

Bash has no rate limits. The relevant concept is resource management and process limits.

**ulimit values (per-process):**
```bash
ulimit -n    # Max open file descriptors (typically 1024)
ulimit -u    # Max user processes (typically 63000+)
ulimit -v    # Max virtual memory (KB)
ulimit -f    # Max file size created by shell (KB)
```

**Cron concurrency control with flock:**
```bash
# Prevent overlapping runs (EOS pattern from nightly_consolidation.sh)
LOCK="/tmp/eos_myjob.lock"
exec 200>"$LOCK"
if ! flock --nonblock 200; then
    echo "SKIP: already running"
    exit 0
fi
# Lock held until process exits

# With timeout (wait up to 10 seconds)
if ! flock --timeout 10 200; then
    echo "TIMEOUT: could not acquire lock"
    exit 1
fi
```

**Throttling outbound calls:**
```bash
# Simple rate limit: 1 request per second
for url in "${URLS[@]}"; do
  curl -s "$url" >> results.txt
  sleep 1
done

# Parallel with rate limit
echo "${URLS[@]}" | xargs -P 4 -I{} sh -c 'curl -s "{}" && sleep 0.25'
```

## Error Codes and Recovery

### Standard exit codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Misuse of shell command (bad syntax, missing keyword) |
| 126 | Command found but not executable (permissions) |
| 127 | Command not found |
| 128 | Invalid exit argument |
| 128+N | Killed by signal N (e.g., 130 = SIGINT/Ctrl-C, 137 = SIGKILL, 143 = SIGTERM) |

### Error trapping
```bash
# Trap on any error
trap 'echo "ERROR on line $LINENO: exit $?" >&2' ERR

# Cleanup trap (always runs)
cleanup() {
  rm -f "$TMPFILE"
  echo "Cleaned up"
}
trap cleanup EXIT

# Multiple signals
trap 'echo "Interrupted"; exit 130' INT TERM

# Trap with context
trap 'echo "Failed at: $BASH_COMMAND" >&2' ERR
```

### Recovery patterns
```bash
# Retry with exponential backoff
retry() {
  local max_attempts=3 delay=1
  for ((i=1; i<=max_attempts; i++)); do
    "$@" && return 0
    echo "Attempt $i failed, waiting ${delay}s..." >&2
    sleep $delay
    delay=$((delay * 2))
  done
  return 1
}
retry curl -s https://api.example.com/health

# Fallback chain
docker restart os-discord || docker compose up -d os-discord || echo "CRITICAL: cannot restart"

# Safe cleanup even on failure
TMPFILE=$(mktemp)
trap "rm -f '$TMPFILE'" EXIT
```

## SDK Idioms

Bash is the "SDK" itself. These are the idiomatic patterns.

**Shebang:**
```bash
#!/usr/bin/env bash    # Portable (finds bash in PATH)
#!/bin/bash            # Direct (faster, no PATH search)
```
EOS uses both. `#!/usr/bin/env bash` for scripts that might run outside the VPS. `#!/bin/bash` for cron scripts that always run on the VPS.

**Function definition:**
```bash
# Modern style (no 'function' keyword needed)
my_func() {
  local var="$1"    # Always use local in functions
  local -r const="immutable"  # Read-only local
  echo "$var"
  return 0
}

# Capture function output
result=$(my_func "arg")
```

**Array idioms:**
```bash
# Declare
arr=("one" "two" "three")

# Iterate (always quote)
for item in "${arr[@]}"; do
  echo "$item"
done

# Length
echo "${#arr[@]}"

# Append
arr+=("four")

# Associative array (bash 4+)
declare -A map
map[key]="value"
echo "${map[key]}"
```

**String testing (prefer [[ ]] always):**
```bash
# [[ ]] is bash-specific, safer, supports regex and glob
[[ "$str" == *.log ]]    # Glob match
[[ "$str" =~ ^[0-9]+$ ]] # Regex match
[[ -z "${VAR:-}" ]]      # Safe empty check with set -u
```

## Anti-Patterns

### 1. Unquoted variables
```bash
# WRONG: breaks on spaces, expands globs
for f in $FILES; do ...

# RIGHT: always quote
for f in "${FILES[@]}"; do ...
for f in "$DIR"/*.log; do ...
```

### 2. Parsing ls output
```bash
# WRONG: ls output is not machine-readable
for f in $(ls *.log); do ...

# RIGHT: use globbing
for f in /opt/OS/logs/*.log; do
  [[ -f "$f" ]] || continue
  ...
done
```

### 3. Using cat unnecessarily (UUOC)
```bash
# WRONG
cat file.txt | grep pattern

# RIGHT
grep pattern file.txt
```

### 4. Testing with [ ] instead of [[ ]]
```bash
# WRONG: [ ] requires careful quoting, no regex
[ $x = "yes" ]

# RIGHT: [[ ]] handles unquoted vars, supports =~ and ==
[[ "$x" == "yes" ]]
```

### 5. Not using set -euo pipefail
```bash
# WRONG: backup.sh pattern -- errors silently continue
#!/bin/bash
tar -czf ...
find ... -delete   # Runs even if tar failed

# RIGHT: fail fast
#!/bin/bash
set -euo pipefail
tar -czf ... || { echo "tar failed" >&2; exit 1; }
```

### 6. Variable assignment with spaces
```bash
# WRONG: runs "value" as a command
VAR = "value"

# RIGHT: no spaces around =
VAR="value"
```

### 7. cd without error check
```bash
# WRONG: if cd fails, all subsequent commands run in wrong directory
cd /opt/OS
rm -rf data/tmp/

# RIGHT: fail if cd fails (set -e handles this, but be explicit for safety)
cd /opt/OS || exit 1
```

### 8. Using backticks instead of $()
```bash
# WRONG: backticks can't nest, hard to read
DATE=`date +%Y%m%d`

# RIGHT: $() nests cleanly
DATE=$(date +%Y%m%d)
NESTED=$(echo $(date +%Y%m%d))
```

## Data Model

Bash's "data model" is the filesystem and process hierarchy.

**Filesystem primitives:**
- Files (regular, symbolic links, pipes, sockets, devices)
- Directories (namespace hierarchy)
- File descriptors (integers 0-N mapping to open files/pipes/sockets)
- Permissions (rwx for owner/group/other, sticky, setuid, setgid)

**Process primitives:**
- PID (process ID) -- `$$` for current, `$!` for last background
- PPID (parent process ID) -- `$PPID`
- Exit code -- `$?` (0-255)
- Signal -- sent via `kill -SIGNAL PID`
- Environment -- inherited key=value pairs
- File descriptors -- inherited from parent (stdin=0, stdout=1, stderr=2)
- Process group -- related processes for signal delivery
- Session -- terminal-attached process group tree

**EOS data flow:**
```
crontab entry
  -> bash wrapper (scripts/scheduled/*.sh)
    -> flock (exclusive lock on fd)
    -> claude -p OR python3 (actual work)
    -> >> log file 2>&1 (output capture)
    -> exit code (0=success, nonzero=failure)
```

**Key EOS filesystem paths:**
- `/opt/OS/` -- repo root, all scripts reference absolute paths from here
- `/opt/OS/logs/` -- all log output, rotated at 7 days
- `/opt/OS/backups/` -- daily tar.gz archives
- `/tmp/eos_*` -- temporary files, cleaned nightly
- `/tmp/eos_*.lock` -- flock lock files

## Webhooks and Events

Bash does not receive webhooks. The equivalent is **signal handling**.

**Signals relevant to EOS scripts:**
| Signal | Number | Default | Use in EOS |
|--------|--------|---------|------------|
| SIGHUP | 1 | Terminate | Sent to process when terminal closes. Cron jobs are immune. |
| SIGINT | 2 | Terminate | Ctrl-C. Trap for graceful cleanup. |
| SIGTERM | 15 | Terminate | `docker stop` sends this first. Trap for shutdown logic. |
| SIGKILL | 9 | Terminate (uncatchable) | `kill -9`. Cannot be trapped. Last resort. |
| SIGCHLD | 17 | Ignore | Child process exited. Used by `wait`. |
| SIGUSR1 | 10 | Terminate | Custom signal. Could be used for log rotation. |

**Trap patterns:**
```bash
# Cleanup on any exit (normal, error, signal)
trap 'rm -f /tmp/eos_myjob_*' EXIT

# Graceful shutdown on SIGTERM (Docker stop)
trap 'echo "Shutting down..."; cleanup; exit 0' TERM

# Ignore SIGHUP (keep running after terminal close)
trap '' HUP

# Log the signal received
trap 'echo "Caught SIGINT"; exit 130' INT
```

## Limits

**Bash-specific limits:**
- Maximum argument length: `getconf ARG_MAX` (typically 2097152 bytes / 2MB)
- Maximum filename length: 255 bytes (ext4)
- Maximum path length: 4096 bytes (PATH_MAX)
- Maximum open file descriptors: `ulimit -n` (default 1024, can raise)
- Maximum environment size: ~128KB (varies by kernel)
- Maximum function recursion: controlled by `FUNCNEST` (default unlimited, can cause stack overflow)
- Array maximum index: 2^63-1 (effectively unlimited)
- Variable value maximum: limited only by available memory

**Cron-specific limits:**
- Minimum interval: 1 minute (use `sleep` subdivision for sub-minute)
- No native second-level scheduling
- Environment is minimal: PATH, SHELL, HOME, LOGNAME only
- MAILTO defaults to crontab owner -- set `MAILTO=""` to suppress

**EOS-specific limits:**
- `claude -p --max-budget-usd 0.50` -- hard spending cap per autonomous run
- Log files rotated at 7 days (`find -mtime +7 -delete`)
- Backup archives retained 7 days
- flock prevents concurrent runs (no queue -- skip or fail)

## Cost Model

Bash itself is free. The cost surfaces in EOS are:

- **claude -p invocations** -- each autonomous agent wrapper has a budget cap:
  - `nightly_maintenance.sh`: $0.50/run = ~$15/month
  - `morning_prep.sh`: $0.30/run = ~$9/month
  - `weekly_review.sh`: $1.00/run = ~$4/month
  - Total autonomous agent cost: ~$28/month at full utilization
- **Compute time** -- VPS is flat-rate, so CPU/memory from cron jobs is included
- **Disk** -- logs and backups consume storage. 7-day rotation keeps this bounded.

**Monitoring:**
```bash
# Check log disk usage
du -sh /opt/OS/logs/
du -sh /opt/OS/backups/

# Check claude -p spending in logs
grep "budget" /opt/OS/logs/nightly_*.log
```

## Version Pinning

**Bash version:**
- Current: Bash 5.2 on Ubuntu/Debian (VPS)
- Shebang `#!/usr/bin/env bash` or `#!/bin/bash` -- no version pinning mechanism
- Feature compatibility: all EOS scripts use Bash 4.0+ features (associative arrays, `[[ ]]`, `set -o pipefail`). Nothing requires Bash 5-specific features.

**Coreutils versions:**
- `flock` from util-linux (any version -- API is stable)
- `find` from findutils (any version -- `-mtime`, `-delete` are POSIX-adjacent and stable)
- `date` -- GNU date for `+%Y%m%d` format (not BSD date)
- `tar` -- GNU tar for `-czf` (gzip compression)

**Deprecation risk: near zero.** Bash maintains backward compatibility aggressively. Scripts written for Bash 3.x still run on Bash 5.x. The only risk is relying on GNU-specific extensions on non-GNU systems (macOS uses BSD tools), but EOS runs exclusively on Linux.

**Version checking:**
```bash
# Bash version
echo "${BASH_VERSION}"   # e.g., 5.2.15(1)-release
echo "${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}"  # e.g., 5.2

# Guard for minimum version
if (( BASH_VERSINFO[0] < 4 )); then
  echo "Bash 4+ required" >&2
  exit 1
fi
```

---

# Tier 2 -- Creator Intelligence

## Design Intent and Tradeoffs

Bash was created by Brian Fox in 1989 as the free replacement for the Bourne shell (sh), commissioned by the Free Software Foundation. The name is "Bourne Again SHell" -- a pun and a mission statement. The design philosophy:

**Core design decisions:**
1. **Backward compatibility with sh is sacred.** Every POSIX sh script must work in bash. This is why bash has both `[ ]` and `[[ ]]`, both `$(())` and `expr`, both backticks and `$()`. Old syntax is never removed.
2. **Interactive and scripting are the same language.** Unlike Python (REPL vs files), bash optimizes for both. This creates tension: features great for interactive use (history expansion with `!`, tilde expansion) create gotchas in scripts.
3. **Text is the universal interface.** Everything is a string. Numbers are strings parsed as integers in arithmetic contexts. Arrays are ordered string lists. This makes bash infinitely composable via pipes but terrible for structured data.
4. **Process spawning is cheap.** Each `$(command)`, pipe stage, and subshell forks a new process. Bash assumes the OS handles this efficiently (Linux does). This is why bash scripts that seem simple can spawn hundreds of processes.

**What bash is NOT:**
- Not a programming language for complex logic (use Python)
- Not a data processing tool (use jq, awk, Python)
- Not a configuration management tool (use Ansible, Terraform)
- Not safe for untrusted input without extreme care (injection risks everywhere)

**The conscious tradeoff EOS makes:** Bash is the thinnest possible wrapper around system operations. Python does the thinking. Bash does the plumbing. This is why EOS bash scripts are short (under 50 lines typically) and delegate to `python3` or `claude -p` for any logic.

## Problem-Solution Map and Hidden Capabilities

**Problems bash solves in EOS:**
1. **Scheduling** -- cron + bash is the simplest scheduler that actually works. No daemon to manage, no database to corrupt, no UI to break.
2. **Process isolation** -- flock prevents cron job overlap without any infrastructure.
3. **Failure containment** -- `set -euo pipefail` + `trap` + exit codes give reliable failure signaling.
4. **Environment bootstrapping** -- `install.sh` and `setup.sh` provision a machine from zero.
5. **Glue** -- connecting Docker, Python, claude CLI, and filesystem operations in sequence.

**Hidden capabilities most people miss:**

1. **Process substitution for diffing command outputs:**
```bash
diff <(docker ps --format '{{.Names}}' | sort) <(cat expected_services.txt | sort)
```

2. **Coprocess for bidirectional IPC:**
```bash
coproc WORKER { python3 worker.py; }
echo "task1" >&${WORKER[1]}
read result <&${WORKER[0]}
```

3. **BASH_REMATCH for regex capture groups:**
```bash
if [[ "$log_line" =~ \[([0-9]{4}-[0-9]{2}-[0-9]{2})\]\ (.+) ]]; then
  date="${BASH_REMATCH[1]}"
  message="${BASH_REMATCH[2]}"
fi
```

4. **mapfile/readarray for bulk file reading:**
```bash
mapfile -t lines < /opt/OS/logs/errors.log
echo "Total error lines: ${#lines[@]}"
```

5. **Brace expansion for multi-directory creation:**
```bash
mkdir -p /opt/OS/{logs,backups,data,tmp}
```

6. **Parameter expansion for path manipulation (no basename/dirname needed):**
```bash
filepath="/opt/OS/logs/nightly_20260406.log"
filename="${filepath##*/}"    # nightly_20260406.log
dirname="${filepath%/*}"      # /opt/OS/logs
extension="${filepath##*.}"   # log
stem="${filename%.*}"         # nightly_20260406
```

## Operational Behavior and Edge Cases

**Edge cases that bite in production:**

1. **Empty glob expands to literal.** If `/opt/OS/logs/*.log` matches nothing, the loop iterates once with the literal string `*.log`. Fix: `shopt -s nullglob` or guard with `[[ -f "$f" ]] || continue`.

2. **Subshells don't propagate variables.** Piping into a while loop creates a subshell:
```bash
# WRONG: count is always 0 after the loop
count=0
cat file | while read line; do ((count++)); done
echo "$count"  # 0

# RIGHT: use process substitution or redirect
count=0
while read line; do ((count++)); done < file
echo "$count"  # correct
```

3. **Arithmetic overflow is silent.** Bash integers are 64-bit signed. Overflow wraps without error: `echo $((9223372036854775807 + 1))` prints `-9223372036854775808`.

4. **Word splitting on command substitution.** `for f in $(find ...)` breaks on filenames with spaces. Use `find -print0 | while read -d '' f` or `find -exec`.

5. **set -e inside functions behaves differently.** A function called in an `if` condition does not trigger `set -e` on internal failures:
```bash
set -e
fail() { false; echo "still runs"; }
if fail; then echo "yes"; fi   # "still runs" prints -- set -e is suppressed
```

6. **Cron timezone depends on system timezone.** All EOS cron times are in the server's timezone (check with `timedatectl`). If the VPS timezone changes, all cron schedules shift. Docker containers may have a different timezone.

7. **Here-strings add a trailing newline.** `wc -c <<< "hello"` returns 6, not 5.

8. **trap EXIT fires on every exit path.** Including `exit 0` in a signal handler. If your EXIT trap and INT trap both run cleanup, it runs twice. Guard with a flag variable.

## Ecosystem Position and Composition

**Where bash sits in EOS architecture:**
```
Cron (system scheduler)
  -> Bash (orchestration layer)
    -> Python (intelligence layer)
      -> LLM APIs (reasoning)
      -> Neon PostgreSQL (persistence)
      -> Discord API (communication)
```

Bash is Layer 0 -- the thinnest orchestration between the OS scheduler and the application logic. It never contains business logic. It never processes data. It only:
- Sets up the environment
- Acquires locks
- Delegates to Python or claude -p
- Captures output
- Handles exit codes

**Natural complements:**
- `jq` -- JSON processing in pipelines (not currently used in EOS, but should be for Docker inspect output)
- `envsubst` -- template variable substitution
- `parallel` (GNU) -- parallel job execution with throttling
- `systemd timers` -- modern alternative to cron with better logging, dependency management, and calendar events

**Integration anti-patterns:**
- Don't parse JSON with grep/sed/awk -- use jq or Python
- Don't do HTTP requests with bash string manipulation -- use curl + jq or Python requests
- Don't build complex conditional logic in bash -- delegate to Python
- Don't use bash for anything that needs data structures beyond arrays

## Trajectory and Evolution

**Bash 5.x (current) brought:**
- `EPOCHSECONDS` and `EPOCHREALTIME` variables (avoid `$(date +%s)` overhead)
- `wait -n` (wait for any background job, not a specific one)
- Nameref variables (`declare -n ref=var`)
- `${var@Q}` for safe quoting in output

**Where the ecosystem is heading:**
1. **systemd timers are replacing cron** on modern Linux. They offer journal logging, dependency ordering, randomized delay, and calendar-event syntax. EOS could migrate for better observability.
2. **POSIX shell (dash/sh) for performance-critical scripts.** Bash startup overhead (~5ms) matters for scripts called thousands of times. Not relevant for EOS (cron jobs are infrequent).
3. **Oil/YSH shell** -- a modern shell language with proper data types, JSON interop, and sane error handling. Experimental but worth watching.
4. **GitHub Actions / CI runners** increasingly replace cron for scheduled tasks. Not applicable to EOS VPS model.

**What is stable and safe to build on:**
- `set -euo pipefail` -- universally recommended, never going away
- `flock` -- util-linux staple, no deprecation risk
- `trap` -- POSIX standard, stable forever
- Cron -- will exist as long as Unix exists
- `[[ ]]` -- bash-specific but bash dominance is permanent on Linux

## Conceptual Model and Solution Recipes

**Mental model: Bash as a process orchestrator**

Think of bash not as a programming language but as a conductor. Each line is an instruction to the operating system: "run this process, connect its output to that process, check if it succeeded, then run the next thing." The primitives are:

- **Commands** -- programs to execute
- **Pipes** -- connect stdout of one to stdin of next
- **Redirections** -- route output to files or file descriptors
- **Exit codes** -- success/failure signals
- **Variables** -- string storage
- **Control flow** -- if/for/while based on exit codes
- **Signals** -- inter-process communication
- **File descriptors** -- open channels to files/pipes/sockets

**Recipe 1: Cron-safe scheduled job with locking and logging**
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0" .sh)"
LOG="/opt/OS/logs/${SCRIPT_NAME}_$(date +%Y%m%d).log"
LOCK="/tmp/eos_${SCRIPT_NAME}.lock"

# Acquire lock
exec 200>"$LOCK"
if ! flock --nonblock 200; then
  echo "[$(date -Iseconds)] SKIP: already running" >> "$LOG"
  exit 0
fi

# Cleanup trap
trap 'echo "[$(date -Iseconds)] EXIT: code $?" >> "$LOG"' EXIT

echo "[$(date -Iseconds)] START" >> "$LOG"
cd /opt/OS

# ... actual work here ...

echo "[$(date -Iseconds)] DONE" >> "$LOG"
```

**Recipe 2: Service health check with restart**
```bash
#!/usr/bin/env bash
set -euo pipefail

SERVICES=("os-discord" "os-monitor" "os-webhook")

for svc in "${SERVICES[@]}"; do
  if ! docker inspect -f '{{.State.Running}}' "$svc" 2>/dev/null | grep -q true; then
    echo "RESTART: $svc"
    docker restart "$svc" || echo "FAILED: $svc"
    sleep 5
  fi
done

docker ps --format '{{.Names}}: {{.Status}}'
```

**Recipe 3: Autonomous agent wrapper with budget cap**
```bash
#!/usr/bin/env bash
set -euo pipefail

LOG="/opt/OS/logs/agent_$(date +%Y%m%d).log"
echo "=== Agent Run: $(date) ===" >> "$LOG"

claude -p --allowedTools "Bash Read Write Edit Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.50 \
  "Your structured prompt here.
  Step 1: ...
  Step 2: ...
  Report: PASS or list issues." >> "$LOG" 2>&1

echo "=== Done: $(date) ===" >> "$LOG"
```

**Recipe 4: Prerequisite checker for installation**
```bash
#!/usr/bin/env bash
set -euo pipefail

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "MISSING: $1 -- $2" >&2
    exit 1
  }
}

require_cmd docker "Install: https://docs.docker.com/get-docker/"
require_cmd python3 "Install Python 3.11+"
require_cmd git "Install: apt install git"

PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if (( PY_MINOR < 11 )); then
  echo "Python 3.11+ required, found 3.$PY_MINOR" >&2
  exit 1
fi

echo "All prerequisites met"
```

**Recipe 5: Backup with retention and size reporting**
```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/opt/OS/backups"
DATE=$(date +%Y%m%d)
ARCHIVE="$BACKUP_DIR/eos_backup_$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$ARCHIVE" \
  /opt/OS/eos_ai/*.py \
  /opt/OS/services/*.py \
  /opt/OS/.claude/ \
  2>/dev/null || true

echo "Created: $ARCHIVE ($(du -sh "$ARCHIVE" | cut -f1))"

# Retain 7 days
DELETED=$(find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete -print | wc -l)
echo "Cleaned: $DELETED old archives"
```

## Industry Expert and Cutting-Edge Usage

**How top practitioners use bash in 2026:**

1. **Bash as the outermost orchestration layer for AI agents.** EOS already does this with `claude -p` wrappers. The pattern is: bash handles scheduling, locking, logging, and budget caps. The AI handles reasoning. This separation means the unreliable part (AI) is contained within the reliable part (bash process management).

2. **flock as poor man's distributed lock.** On a single VPS (EOS's model), flock is simpler and more reliable than Redis locks, database advisory locks, or file-based semaphores. The fd-based pattern (exec + flock) is preferred over the subshell pattern (flock -n lockfile command) because it holds the lock for the entire script, not just one command.

3. **Structured logging with ISO 8601 timestamps.** `date -Iseconds` outputs `2026-04-06T03:00:00-07:00` -- machine-parseable, timezone-aware, sortable. EOS's `nightly_consolidation.sh` already uses this. The other scripts use `$(date)` which produces locale-dependent output. Standardizing on `-Iseconds` would improve log parsing.

4. **Exit code contracts.** Expert bash scripts define exit code meanings: 0=success, 1=error, 2=skip (already running), 3=partial success. EOS's `nightly_consolidation.sh` uses 0 for both success and skip-already-running. Differentiating would improve monitoring.

5. **Shellcheck as mandatory linter.** `shellcheck script.sh` catches quoting errors, POSIX incompatibilities, and common gotchas statically. Should be added to EOS CI or pre-commit hooks. Equivalent to `ruff` for Python.

6. **Heredoc prompts for claude -p.** Instead of escaping dollar signs and quotes in the prompt string, use a heredoc to a temp file:
```bash
PROMPT=$(cat << 'PROMPT_EOF'
Your prompt here with $variables and "quotes" treated literally.
No escaping needed.
PROMPT_EOF
)
claude -p --allowedTools "Bash Read" "$PROMPT" >> "$LOG" 2>&1
```
This eliminates the fragile escaping currently used in `nightly_maintenance.sh`.

7. **Process supervision patterns.** For long-running bash-launched processes, the expert pattern is:
```bash
while true; do
  python3 worker.py
  EXIT=$?
  echo "Worker exited with $EXIT, restarting in 5s..."
  sleep 5
done
```
Docker handles this for EOS services, but it is useful for ad-hoc processes.

---

## EOS Usage Patterns

EOS uses bash in five distinct roles:

1. **Cron wrappers** (`scripts/scheduled/*.sh`) -- strict mode, flock, claude -p delegation, log capture
2. **Infrastructure scripts** (`install.sh`, `setup.sh`) -- prerequisite checking, pip install, environment bootstrapping
3. **Operational scripts** (`scripts/backup.sh`) -- tar, find, file management
4. **Sync scripts** (`.agents/skills/last30days/scripts/sync.sh`) -- array iteration, file copy, import verification
5. **Inline bash** (inside cron entries as direct `python3 -c` invocations or `cd /opt/OS && python3 scripts/...` chains)

**Standard EOS bash header:**
```bash
#!/usr/bin/env bash
set -euo pipefail
cd /opt/OS
LOG="/opt/OS/logs/$(basename "$0" .sh)_$(date +%Y%m%d).log"
```

**Cron entry standard:**
```
MINUTE HOUR DOM MON DOW bash /opt/OS/scripts/scheduled/name.sh >> /opt/OS/logs/name.log 2>&1
```

## Gotchas

1. **backup.sh missing strict mode.** This is the only EOS script without `set -euo pipefail`. A failing `tar` (missing source path) silently continues. Discovered during skill research 2026-04-06.

2. **nightly_maintenance.sh prompt escaping.** The claude -p prompt uses `\$` and `\"` throughout to prevent bash expansion. This is fragile -- a single missed escape breaks the prompt silently. Heredoc approach would be safer.

3. **Cron PATH variation.** Commands like `claude`, `ollama`, `npx` may not be in cron's default PATH. EOS works around this by using `bash /opt/OS/scripts/...` (absolute paths) but inline cron entries with bare command names could fail.

4. **flock lock files persist after reboot.** `/tmp/eos_*.lock` files survive if `/tmp` is not on tmpfs. They are harmless (flock checks the fd, not the file), but they accumulate. The nightly cleanup handles this with `find /tmp -name 'eos_*' -mtime +1 -delete`.
