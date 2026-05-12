# Shim Retirement Monitoring Plan

> Monitoring window: 2026-05-12 → 2026-05-26 (14 days)
> Monitor script: scripts/shim_retirement_monitor.py
> Cron schedule: daily at 03:30 UTC

---

## Automated Checks (daily)

| Check | What It Does | PASS Condition |
|-------|-------------|----------------|
| **log_scan** | Scans service logs for new eos_ai import errors or attempts | Zero new findings above baseline (28 pre-existing) |
| **crontab** | Verifies crontab has no eos_ai references | Zero refs |
| **docker_env** | Inspects running container env vars | No eos_ai in env |
| **canonical_imports** | Tests runtime.* imports load correctly | All 7 core modules import |
| **running_processes** | Scans /proc for Python processes importing eos_ai | Zero matching processes |

## Manual Checks (weekly)

| Day | Check | Command |
|-----|-------|---------|
| Day 7 | Review monitor reports | `cat data/runtime/shim_monitor/shim_monitor_*.json \| python3 -m json.tool` |
| Day 7 | Check orchestrator ran clean | `tail -20 /opt/OS/logs/orchestrator.log` |
| Day 7 | Check weekly review ran | `tail -20 /opt/OS/logs/cron_emit.log` |
| Day 7 | Verify Discord bot uptime | `docker ps --format '{{.Names}} {{.Status}}' \| grep os-discord` |
| Day 14 | Final readiness assessment | `python3 scripts/shim_retirement_monitor.py` |

## Baseline

Captured 2026-05-12:
- 28 pre-existing eos_ai log entries (historical tracebacks from before migration)
- Stored in `data/runtime/shim_monitor/baseline.json`
- Any count above 28 indicates new eos_ai activity → investigate before retirement

## What Triggers an Alert

1. **New log entries** — any eos_ai import attempt or error not in the baseline
2. **Crontab regression** — someone adds an eos_ai ref back to crontab
3. **Container env leak** — a container restart picks up stale env_file
4. **Import failure** — canonical runtime.* import fails (regression)
5. **Running process** — a Python process has eos_ai in its cmdline

## Report Location

Daily reports: `data/runtime/shim_monitor/shim_monitor_YYYY-MM-DD.json`
Cron log: `/opt/OS/logs/shim_monitor.log`

## Rollback Command (monitoring setup)

```bash
# Remove cron entry
crontab -l | grep -v 'shim_retirement_monitor' | crontab -

# Remove monitor artifacts
rm -rf data/runtime/shim_monitor/
```

---

## Shim Retirement Readiness Checklist

All items must be checked before approving shim deletion:

### Automated (verified by monitor)

- [ ] 14 consecutive days of READY verdicts
- [ ] Zero new eos_ai log entries above baseline
- [ ] Zero eos_ai refs in crontab
- [ ] Zero eos_ai env vars in running containers
- [ ] All canonical imports pass
- [ ] Zero Python processes with eos_ai in cmdline

### Manual Verification

- [ ] All cron jobs executed successfully during window
- [ ] Discord bot had zero eos_ai-related crashes
- [ ] Nightly maintenance completed every night
- [ ] Weekly review completed (at least 1 Sunday cycle)
- [ ] Morning prep completed every day
- [ ] No user reports of import errors

### Pre-Deletion Steps

- [ ] Update 14 legacy test validator files
- [ ] Update .gitignore (remove eos_ai patterns)
- [ ] Update runtime/transport/substrate_projection_boundaries.py (1 backward-compat ref)
- [ ] Prepare graph rebuild command
- [ ] Confirm runtime/.env is the real file (not a symlink target)
- [ ] Snapshot current eos_ai/ for archive reference

### Post-Deletion Steps

- [ ] Run `scripts/update-graph` to rebuild codebase graph
- [ ] Run full test suite to confirm baseline
- [ ] Run shim monitor one final time (should show READY with 0 baseline)
- [ ] Remove monitoring cron entry
- [ ] Remove shim_retirement_monitor.py (or keep for future migrations)
