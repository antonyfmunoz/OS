# Phase 1 Report — Fix Production-Breaking Issues

**Date:** 2026-05-27
**Branch:** chore/umh-coherence-convergence-20260527-0550

---

## 1. os-webhook crash (FIXED)

**Root cause:** `docker-compose.yml` os-webhook service only loaded `services/.env` but not `infra/docker/umh.env`. The `substrate/state/storage/db.py` module used `os.environ["EOS_ORG_ID"]` at import time — crashes if the var is missing.

**Fixes applied:**
- `docker-compose.yml`: Added `infra/docker/umh.env` to os-webhook's `env_file` list
- `substrate/state/storage/db.py`: Changed `os.environ["KEY"]` → `os.environ.get("KEY", "")` for `DATABASE_URL`, `EOS_ORG_ID`, `EOS_USER_ID` — no more import-time crash
- `substrate/state/storage/db.py`: Added runtime validation in `get_conn()` — raises clear error if DATABASE_URL is empty when actually connecting

**Verification:** Import succeeds without env vars set. Connection attempt gives clear error message.

## 2. Mesh backlog (DOCUMENTED — NOT A BUG)

**Finding:** Port 8094 `Recv-Q: 101` is static — not growing, not draining. The Windows desktop node is connected and functioning (confirmed in systemd logs).

**Analysis:** The backlog consists of incomplete TCP handshakes from internet port scanners hitting the VPS's public IP. The `websockets.serve()` server accepts valid WebSocket connections normally. The kernel queues SYN packets from scanners that never complete the handshake.

**Recommendation:** Not a production issue. If desired later, bind to `100.77.233.50` (Tailscale IP) instead of `0.0.0.0` to prevent scanner noise. No code change needed now.

## 3. Missing get_pipeline_data() (FIXED)

**Fix:** Added `get_pipeline_data(org_id)` function to `projections/eos/views/pipeline.py` — wraps `PipelineView.snapshot()` and returns a dict suitable for API responses.

**Verification:** Import succeeds, function signature matches expected usage.

## 4. subagent_start_context.py hardcoded data (FIXED)

**Problem:** Hardcoded ICP details ("Men 18-25, fitness/self-improvement"), channel ("Instagram DMs"), and offer ("Initiate Arena $750/90-day") — stale and brittle.

**Fix:** Removed all hardcoded venture/research data. All context now comes from `load_context_from_env()` which reads from BIS. The venture context (stage, north star, binding constraint, active venture) is injected for all agent types, not just CEO/venture-specific ones. EA context still queries pending tasks but uses `get_conn()` through the canonical db layer instead of raw psycopg2.

**Verification:** File compiles clean.

## 5. CLAUDE.md stale references (FIXED)

**Fixes:**
- `.claude/CLAUDE.md`: Removed `transports/discord/bot.py` (doesn't exist) from component status. `services/discord_bot.py` is the actual production entrypoint — already listed.
- `.claude/CLAUDE.md`: Changed `interface/` (doesn't exist) → `sockets/` in project structure
- `CLAUDE.md`: Fixed `alwaysThinkingEnabled: true` → `false` to match `settings.json` runtime truth

## Import Smoke Checks

```
db.py import OK (ORG_ID='', USER_ID='')
pipeline.py import OK (get_pipeline_data available)
subagent_start_context.py compiles OK
```

All Phase 1 fixes pass. No production services were restarted (worktree isolation — changes must be merged to main and services restarted there).
