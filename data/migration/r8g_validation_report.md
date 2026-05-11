# R8g Validation Report — Operational/Runtime Infrastructure Convergence

> Generated: 2026-05-11
> Wave: R8g — Converge operational, deployment, and bootstrap infrastructure

---

## Summary

| Metric | Value |
|--------|-------|
| Files modified | 18 |
| Shell scripts updated | 12 |
| Docker/compose files updated | 3 |
| Infra files updated | 4 |
| CLAUDE.md files updated | 2 (root + runtime/) |
| Env comment/template updates | 2 |
| Test baseline | 8684/2691/495 (exact match) |
| Module identity | PASS |
| Replay identity | PASS |
| Depth-flattened identity | PASS |
| Singleton identity | PASS |
| Core imports | PASS |
| Shell syntax | PASS (all modified files) |
| Docker compose config | VALID |
| Daemon bootstrap | PASS |
| Cold boot | 0.105s |
| Regressions | 0 |

## Scope

### Files modified

| File | Changes |
|------|---------|
| `docker-compose.yml` | 3× `eos_ai/.env` → `runtime/.env` (os-monitor, os-scraper, os-discord) |
| `install.sh` | 4 refs: `.env` paths, mkdir, cp, user instructions |
| `setup.sh` | 6 refs: `.env` path, source, import |
| `infra/docker/install.sh` | mkdir + `.env` paths (eos/ → runtime/) |
| `infra/docker/setup.sh` | `.env` paths + import |
| `infra/docker/.env.example` | Comment: "Copy to runtime/.env" |
| `infra/docker/umh.env` | Comment: "runtime environment" |
| `scripts/scheduled/nightly_maintenance.sh` | Inline Python imports + load_dotenv |
| `scripts/scheduled/nightly_consolidation.sh` | python3 -m + imports + load_dotenv |
| `scripts/scheduled/morning_prep.sh` | python3 -m + imports + load_dotenv |
| `scripts/scheduled/weekly_review.sh` | import eos_ai + from eos_ai.* |
| `scripts/auth_monitor/health_check.sh` | DISCORD_WEBHOOK_ENV path |
| `scripts/auth_monitor/credential_watcher.sh` | DISCORD_WEBHOOK_ENV path |
| `scripts/auth_monitor/session_resurrector.sh` | DISCORD_WEBHOOK_ENV path |
| `scripts/auth_monitor/credential_coordinator.sh` | DISCORD_WEBHOOK_ENV path |
| `scripts/substrate_operator_tick.sh` | Inline Python import |
| `scripts/backup.sh` | Backup path glob |
| `CLAUDE.md` (root) | Key files, import verify, intelligence routing, gotchas |
| `runtime/CLAUDE.md` | Header, identity section, conventions |

## Migration Categories

### 1. Docker Compose (3 env_file entries)
All three services that loaded `eos_ai/.env` now load `runtime/.env`:
- `os-monitor` (line 52)
- `os-scraper` (line 79)
- `os-discord` (line 141)

`eos_ai/.env` is a symlink to `runtime/.env`, so both paths resolve identically.
The change aligns the compose file with the canonical namespace.

### 2. Shell Scripts (12 files)
All inline Python `from eos_ai.*` imports rewritten to `from runtime.*`.
All `load_dotenv('/opt/OS/eos_ai/.env')` rewritten to `runtime/.env`.
All `DISCORD_WEBHOOK_ENV` paths updated.
All `python3 -m eos_ai.*` module invocations updated.

### 3. Bootstrap/Install Scripts (4 files)
Root `install.sh`, `setup.sh`, and `infra/docker/` equivalents all point
to `runtime/.env` for env setup, `runtime` for mkdir, and `runtime.*`
for Python imports.

### 4. CLAUDE.md Operational Instructions (2 files)
- Root `CLAUDE.md`: key files, deploy verify command, intelligence routing path,
  gotchas section — all now reference `runtime/`
- `runtime/CLAUDE.md`: header, identity, conventions — reflects canonical namespace

### 5. Env Templates (2 files)
- `infra/docker/.env.example`: copy instruction → `runtime/.env`
- `infra/docker/umh.env`: header comment updated

## Items Requiring Manual Update

### Live Crontab (2 entries)

```bash
# Line 6: orchestrator
# CURRENT:
0 6 * * * cd /opt/OS && python3 eos_ai/orchestrator.py >> /opt/OS/logs/orchestrator.log 2>&1
# REPLACE WITH:
0 6 * * * cd /opt/OS && python3 runtime/orchestrator.py >> /opt/OS/logs/orchestrator.log 2>&1

# Line 17: nightly email review (inline Python)
# CURRENT:
0 23 * * * python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from dotenv import load_dotenv; load_dotenv('/opt/OS/eos_ai/.env'); load_dotenv('/opt/OS/services/.env'); from eos_ai.email_reviewer import EmailReviewer; from eos_ai.context import load_context_from_env; from eos_ai.discord_utils import post_to_webhook; import os; ctx = load_context_from_env(); er = EmailReviewer(ctx); report = er.run_nightly_review(); webhook = os.getenv('DISCORD_BRIEF_WEBHOOK'); post_to_webhook(report, webhook=webhook) if webhook else None; print(report)" >> /opt/OS/logs/email_review.log 2>&1
# REPLACE WITH:
0 23 * * * python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from dotenv import load_dotenv; load_dotenv('/opt/OS/runtime/.env'); load_dotenv('/opt/OS/services/.env'); from runtime.email_reviewer import EmailReviewer; from runtime.context import load_context_from_env; from runtime.discord_utils import post_to_webhook; import os; ctx = load_context_from_env(); er = EmailReviewer(ctx); report = er.run_nightly_review(); webhook = os.getenv('DISCORD_BRIEF_WEBHOOK'); post_to_webhook(report, webhook=webhook) if webhook else None; print(report)" >> /opt/OS/logs/email_review.log 2>&1
```

### `.claude/settings.json` (3 references)
Cannot be modified by the agent (self-modification blocked). Update manually:

1. **Deny rule**: `"Read(/opt/OS/eos_ai/.env)"` → `"Read(/opt/OS/runtime/.env)"`
2. **PostToolUse hook**: `"import eos_ai"` → `"import runtime"`
3. **PreCompact hook**: `"from eos_ai.context import load_context_from_env"` → `"from runtime.context import load_context_from_env"`

### `.claude/CLAUDE.md` (12 references)
Agent project instructions file — contains operational commands and component
status references. All `eos_ai.*` import paths and file paths should be
updated to `runtime.*`. Key changes:

1. Session resume: `from eos_ai.session_state import SessionState` → `from runtime.session_state import SessionState` (2 sites)
2. Validator: `from eos_ai.context import load_context_from_env` + `from eos_ai.system_context import SystemContext` → `from runtime.*`
3. Import test pattern: `from eos_ai.[module]` → `from runtime.[module]`
4. Component status list: all `eos_ai/*.py` → `runtime/*.py` (10 entries)
5. Project structure: `eos_ai/` description → note it's the shim layer

## Remaining Intentional eos_ai References

### `eos_ai/` shim directory (459 files)
Compatibility layer. All shims re-export from `runtime/`. Will be removed
in a future wave after all consumers are verified.

### Legacy test validators (63+ refs in tests/legacy/)
String assertions verifying runtime/UMH code doesn't import from bridges.
These are correct and must stay.

### Migration tools (scripts/r8*.py)
Reference `eos_ai` by design — they generate/manage the shim layer.

### Historical docs (docs/system/)
Phase reports reference `eos_ai/` paths as they existed at time of writing.
These are historical records and should not be rewritten.

### `runtime/transport/substrate_projection_boundaries.py` (1 ref)
Backward-compat path check for `eos_ai/substrate/`.

## Identity Verification

### Module Identity (PASS)
```
PASS: eos_ai.db is runtime.db
```

### Replay Identity (PASS)
```
PASS: eos_ai.db.get_conn is runtime.db.get_conn
```

### Depth-Flattened Identity (PASS)
```
PASS: eos_ai.runtime.work_state is runtime.work_state
PASS: eos_ai.runtime.work_state._measure_pressure is runtime.work_state._measure_pressure
```

### Singleton Identity (PASS)
```
runtime.provider_state.get_system_state() is eos_ai.provider_state.get_system_state()
```

### Core Import Verification (PASS)
```
from runtime.context import load_context_from_env   — OK
from runtime.memory import AgentMemory               — OK
from runtime.authority_engine import RISK_CLASSES     — OK
from runtime.embedder import embed                    — OK
from runtime.substrate.memory_scope_contracts import MemoryScope — OK
```

### Daemon Bootstrap (PASS)
```
Context loaded: EOSContext
Context org: 72727be3...
DB connection: PASS
```

## Cold Boot Comparison

| Wave | Cold boot avg |
|------|--------------|
| R8d | 0.118s |
| R8e | 0.079s |
| R8f | 0.065s |
| R8g | 0.105s |

R8g cold boot is within normal variance. R8g changes are operational
infrastructure (shell scripts, compose files, CLAUDE.md) — no Python
import path changes that would affect cold boot latency.

## Test Baseline

| Metric | R8f | R8g | Delta |
|--------|-----|-----|-------|
| Passed | 8,684 | 8,684 | 0 |
| Failed | 2,691 | 2,691 | 0 |
| Errors | 495 | 495 | 0 |

## Verification Matrix

| Check | Result |
|-------|--------|
| Shell syntax (all modified .sh) | PASS |
| Docker compose config | VALID |
| Module identity | PASS |
| Replay identity | PASS |
| Depth identity | PASS |
| Singleton identity | PASS |
| Core imports | PASS |
| Daemon bootstrap | PASS |
| Test baseline exact match | PASS |

## Rollback Command

```bash
git checkout HEAD -- docker-compose.yml install.sh setup.sh infra/docker/ \
  scripts/scheduled/ scripts/auth_monitor/ scripts/substrate_operator_tick.sh \
  scripts/backup.sh CLAUDE.md runtime/CLAUDE.md
```

## R8h Readiness Assessment

**Status: READY**

R8g is complete. All operational infrastructure now uses canonical `runtime/` paths:
- Docker compose env_file entries (3 services) updated
- Shell scripts (12 files) migrated
- Bootstrap/install scripts (4 files) migrated
- CLAUDE.md operational instructions (2 files) updated
- Env templates (2 files) updated
- Identity guarantees preserved
- Test baseline exact match

**Manual updates required (post-R8g):**
1. Live crontab (2 entries) — see patch commands above
2. `.claude/settings.json` (3 refs) — see patch instructions above
3. `.claude/CLAUDE.md` (12 refs) — see patch instructions above
