# Wave 5 — Infrastructure & Runtime Tool Mastery
Date: 2026-04-06
Author: Developer Agent (synthesis pass)
Scope: Tool Mastery Engine skills for the EOS execution substrate.

## Objective

Convert pre-existing Wave 5 research (already on disk in `/tmp/`) into production
Tool Mastery Engine skills for the five infrastructure layers EOS depends on at
runtime: terminal multiplexing, service supervision, private networking, the
JavaScript runtime, and the persistence layer's raw-SQL surface.

This wave is **synthesis-only** — no new research was run.

## Skills delivered

| Skill           | Action   | SKILL.md | best_practices.md | Extra reference                  |
|-----------------|----------|---------:|------------------:|----------------------------------|
| tmux            | fill     |      199 |              1032 | —                                |
| systemd         | create   |      301 |              1308 | —                                |
| tailscale       | create   |      300 |              1122 | —                                |
| nodejs          | create   |      293 |              1315 | —                                |
| neon_postgres   | refresh  |      383 |               868 | references/raw_sql_mastery.md (1323) |

Total new/expanded content this wave: **~7,144 lines** of creator-level operational
knowledge across five tools.

## Scope discipline

Per the wave brief, only the required artifacts were generated:

- ✅ SKILL.md (19-section structure where applicable, tmux-style tone and EOS framing)
- ✅ references/best_practices.md (full 19-section depth: Tier 1 technical + Tier 2 creator intel)
- ✅ For neon_postgres: a NEW references/raw_sql_mastery.md absorbing the 39 KB Raw SQL addendum

NOT generated (intentionally — already covered by best_practices.md depth):

- ❌ examples.md
- ❌ anti_patterns.md
- ❌ integrations.md

## Sources

All research files were pre-written and consumed read-only:

- `/tmp/tmux_operational.md` + `/tmp/tmux_creator_intel.md`
- `/tmp/systemd_operational.md` + `/tmp/systemd_creator_intel.md`
- `/tmp/tailscale_operational.md` + `/tmp/tailscale_creator_intel.md`
- `/tmp/nodejs_operational.md` + `/tmp/nodejs_creator_intel.md`
- `/tmp/neon_postgres_raw_sql.md`

No web research, no subagent research dispatches — synthesis only.

## Verification status

| Check | Result |
|---|---|
| All 5 SKILL.md files have valid YAML frontmatter | ✅ |
| All 5 `last_researched` set to 2026-04-06 | ✅ |
| All 5 `version` = 1.0 | ✅ |
| No examples.md / anti_patterns.md / integrations.md created | ✅ |
| Each best_practices.md > 800 lines | ✅ |
| neon_postgres existing content preserved (no rewrites) | ✅ |
| raw_sql_mastery.md created and cross-linked from SKILL.md + best_practices.md | ✅ |

Note: There is no automated `sync_skills_to_neon` script in `/opt/OS/scripts/` and
no executable Tool Mastery Engine verification script (only `scaffold_tool_skill.py`).
Skill registry sync to Neon is currently a manual gap — flagged for follow-up wave.

## Commits

Each skill committed individually per the wave brief naming convention:

- `Add tool skill: tmux` (best_practices.md fill)
- `Add tool skill: systemd`
- `Add tool skill: tailscale`
- `Add tool skill: nodejs`
- `Refresh tool skill: neon_postgres`

Plus this report.

## Key infrastructure capabilities unlocked

**tmux** — EOS now has a creator-level reference for the substrate that holds the
24/7 Claude Code session. Socket pinning convention (`-L eos`), headless sizing
(`-x 220 -y 50`), `pipe-pane` continuous logging, `capture-pane -p -S -N` for
log scraping into Python memory, `display-message -p '#{pane_pid}'` for
hung-pane recovery, and the systemd integration recipe (`Type=forking`,
`KillMode=none`, `loginctl enable-linger`) are all documented.

**systemd** — Production knowledge for the four os-* services (os-discord,
os-bot, os-monitor, os-webhook). Hardened unit-file recipes, drop-in patterns
for env injection, journalctl scraping, `Type=notify` + `sd_notify` for honest
readiness, cgroup limits (`MemoryMax`, `TasksMax`, `CPUQuota`), and Ubuntu
22.04 vs 24.04 feature deltas.

**tailscale** — The complete tailnet model for Antony's multi-device setup
(VPS as hub, iPhone Termius, iPad code-server, Windows VS Code). MagicDNS,
ACL grants, tagged servers with `autoApprovers`, key types (ephemeral /
preauthorized / tagged), DERP fallback, Funnel/Serve for selective exposure,
and the "nothing on the public internet" enforcement pattern.

**nodejs** — Runtime knowledge for the `saas/` TypeScript stack
(React + Vite + Hono/Express + Drizzle + vitest + pnpm). LTS schedule pinning,
ESM/CJS resolution rules, native fetch + AbortController patterns,
worker_threads for CPU work, graceful shutdown on SIGTERM, V8 heap tuning,
and the Node-vs-Python decision criteria for new EOS services.

**neon_postgres (raw SQL mastery)** — Postgres-internals expertise that an
ORM user does not have: query planner intuition, index selection (B-tree vs
GIN vs GiST vs BRIN), JSONB operator class choices, **pgvector HNSW vs
IVFFlat trade-offs for the embedding(1536) memories table**, MVCC mechanics,
advisory locks (and their PgBouncer transaction-mode incompatibility),
EXPLAIN ANALYZE reading, and slow-query debugging — all framed against EOS's
multi-tenant `agents` / `skills` / `memories` / `feedback_events` schema with
RLS via `app.current_org_id`.

## Issues / follow-ups

1. **No skill→Neon sync script.** `sync_skills_to_neon` does not exist in
   `/opt/OS/scripts/`. The skill registry rows for these five skills must be
   inserted/updated manually or via a future automation pass.
2. **No Tool Mastery Engine verification script.** Only `scaffold_tool_skill.py`
   exists. A linter that checks 19-section presence + frontmatter validity
   should be added in a meta wave.
3. **MEMORY.md recent_builds index** should be updated to reference Wave 5
   skills (5 new/expanded tool mastery skills) — separate task.
