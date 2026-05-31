# Phase 13.3S — Definitive Ground Truth Ingestion

## Source
- **Audit:** `data/audits/2026-05-31_definitive_ground_truth_audit.md`
- **Canonical snapshot:** `data/umh/operational_truth/phase13_3s_ground_truth_snapshot.json`
- **Date:** 2026-05-31
- **Canonicality:** operational_truth_snapshot
- **Scope:** /opt/OS (entire UMH repository)

## What This Document Records

This ingestion formalizes the 2026-05-31 definitive ground-truth audit as the canonical operational snapshot for Phase 13.3S stabilization work. All Phase 13.3S tasks trace their starting conditions back to this audit.

## Key Numbers From Audit

| Metric | Value |
|--------|-------|
| Total repo files | 114,817 |
| Active Python files | 1,186 |
| Active TypeScript files | 141 |
| Disk usage | 80% (21 GB free of 96 GB) |
| RAM usage | 53% (7.8 GB total) |
| Docker containers running | 3 of 4 |
| Systemd services | 5 |
| Cron jobs | 31 |
| Organism daemon tick | 2,463 |
| Events recorded | 17,152 |
| Execution journal entries | 0 (broken) |
| Pre-commit gates wired | 2 of 4 |
| LLM providers available | 0 cloud (Ollama emergency only) |
| Knowledge graph age | 5 days stale |

## Critical Issues Identified (P0-P6)

1. **P0** — All LLM providers exhausted (Gemini 429, Groq 429, Perplexity 401)
2. **P1** — execution_journal.jsonl 0 lines (no evidence trail)
3. **P2** — Only 2/4 pre-commit gates wired
4. **P3** — EventBus loop_cycle_business_ops no handlers
5. **P4** — metrics.jsonl 238MB, disk 80%
6. **P5** — Knowledge graph 5 days stale
7. **P6** — Cockpit external access timed out

## Phase 13.3S Actions Against Each Issue

| Issue | Fix Applied | Status |
|-------|------------|--------|
| P0 LLM providers | Diagnostic + visibility — operator must restore | DIAGNOSED |
| P1 Execution journal | Daemon tick heartbeat + probe verification | FIXED |
| P2 Pre-commit gates | All 4 gates wired in .git/hooks/pre-commit | FIXED |
| P3 EventBus no-handler | Diagnostic handler registered for loop_cycle_business_ops | FIXED |
| P4 Data hygiene | Metrics rotated (238MB→2MB), worktrees cleaned (930MB), logs archived | FIXED |
| P5 Knowledge graph | Rebuild triggered via scripts/update-graph | IN PROGRESS |
| P6 Cockpit access | Root cause: Tailscale OOM on 512MB Fly machine | DIAGNOSED |

## Structured Snapshot Location

```
data/umh/operational_truth/phase13_3s_ground_truth_snapshot.json
```

This JSON contains the full structured representation of all audit findings, suitable for programmatic consumption by the JarvisReadinessGate and cockpit operational truth endpoints.
