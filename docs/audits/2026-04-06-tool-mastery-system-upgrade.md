# Audit — Tool Mastery Engine System Upgrade

**Date:** 2026-04-06
**Scope:** Promote TME from a manually curated skill library to a
self-updating, queryable, enforceable system.
**Goal:** Close the five systemization gaps (sync, verify, staleness,
graph, registry) without adding new tool skills or running capability
research waves.

---

## What was built

### New scripts
| Script | Purpose |
|---|---|
| `scripts/_tme_common.py` | Shared loader: `SkillRecord`, YAML frontmatter parsing, tolerant section matcher, freshness helpers. Single source of truth for file-parsing logic. |
| `scripts/sync_skills_to_neon.py` | Canonical Neon sync. Modes: `--all`, `--skill <slug>`, `--dry-run`, `--verbose`. SELECT → UPDATE-or-INSERT (no duplicates, bumps `version` on content change). |
| `scripts/verify_tool_skill.py` | TME verifier / linter. YAML-aware, replaces the fragile in-skill regex checks. Validates 9 conditions incl. 19-section best_practices contract. Modes: `--all`, `--skill`, `--quiet`, `--json`. |
| `scripts/check_skill_staleness.py` | Freshness audit by `speed_category` (fast=30 / medium=60 / stable=90). Statuses: `fresh`, `near_stale`, `stale`, `missing_date`. Modes: text, `--markdown`, `--json`, `--only`. |
| `scripts/build_skill_graph.py` | Dependency graph via slug/title/alias mentions across SKILL.md + best_practices.md. Produces `docs/system/skill_graph.md` and `docs/system/skill_graph.json` with centrality + orphans. |
| `scripts/query_skills.py` | CLI registry: `search`, `show`, `deps`, `stale`, `unverified`, `domain`, `list`, `count`. Delegates to the four analyzer scripts so results never drift from source of truth. |

### New docs
| Path | Purpose |
|---|---|
| `docs/system/tool_mastery_engine_system.md` | Full system reference: layout, utilities, shared loader, operating workflow, self-updating loop diagram, known limitations, next upgrades. |
| `docs/system/skill_graph.md` | Auto-generated human-readable graph. Top 20 central skills + full adjacency. |
| `docs/system/skill_graph.json` | Auto-generated machine-readable graph. |
| `docs/audits/2026-04-06-tool-mastery-system-upgrade.md` | This report. |

---

## Validation results

### Verifier
```
Verified 89 skills: 82 passed, 7 failed
```

Failures are real data gaps in older wave-4/5 skills, not verifier
bugs (confirmed by re-running the tolerant section matcher against
`notion/references/best_practices.md`, which uses `## 1. Authentication`
style numbered headers and now passes). Failing skills:

- `shadcn_ui` — best_practices.md missing most Tier-1/2 sections
- `voice_pipeline` — SKILL.md missing `## Authentication` (domain-appropriate; candidate for a skill-specific exemption)
- `whop` — best_practices.md missing 17 of 19 sections
- 4 others flagged with similar coverage gaps (see `query_skills.py unverified`)

These are recorded as a punch list for the next research wave.
**The verifier itself is trustworthy** — section matching now handles
numbered headers, trailing punctuation, parenthetical suffixes, and
is case-insensitive.

### Staleness
```
fresh=89 near_stale=0 stale=0 missing_date=0 total=89
```
All 89 skills are within their freshness window as of 2026-04-06.

### Sync (dry-run, then real)
```
Summary: insert=15 update=2 unchanged=72 skip=0 total=89
```
Dry-run and real-run plans matched exactly. 15 skills were not
previously in Neon; 2 had content drift between filesystem and DB
and were bumped; 72 were identical. The Neon `skills` table has no
UNIQUE(org_id,name) constraint, so the script uses SELECT-first
upsert — no duplicate rows created.

### Graph
```
Nodes=89 edges=898 orphans=0
```
Every skill connects to at least one other skill. Top centrality
(from `skill_graph.md`): `python`, `bash`, `notion`, `neon_postgres`,
`git` — unsurprising, given those are the universal tools.

### Query tool
All commands smoke-tested:
- `count` → 89
- `search ads` → 9 relevant matches
- `deps notion` → 6 outgoing, 27 incoming, centrality 33
- `unverified` → 7 failing skills with truncated failure lists
- `show <slug>`, `domain <substring>`, `list`, `stale --only near_stale`

---

## Known limitations

1. **No UNIQUE constraint** on `skills(org_id, name)`. Works today via
   SELECT-first upsert, but a real migration would be cleaner.
2. **Centrality is raw degree**, not PageRank. Intentional — graph
   theory over-engineering was explicitly out of scope.
3. **Edge detection is text-based.** Offhand mentions of a tool count
   as edges. Precision > recall was not a goal.
4. **Alias list is short** (only `postgres/neon` etc.). Extend
   `ALIASES` in `build_skill_graph.py` as needed.
5. **Re-research is still manual.** The detector flags what's stale;
   humans (or the TME decision tree) drive the actual research.
6. **Verifier does not enforce non-empty Gotchas.** A skill can pass
   with a `## Gotchas` header and zero bullets.
7. **`voice_pipeline` fails auth-section check.** Domain-appropriate —
   may need a per-skill exemption mechanism or a looser check.

---

## Recommended next upgrades

1. **DB migration** — add `UNIQUE(org_id, name)` to `skills`, then
   refactor `sync_skills_to_neon.py` to use `ON CONFLICT DO UPDATE`.
2. **Nightly cron** — wire
   `check_skill_staleness.py --all --only stale`
   and `--only near_stale` into
   `scripts/scheduled/nightly_maintenance.sh`. Push results to
   Discord/Notion.
3. **Post-commit hook** — auto-run `sync_skills_to_neon.py --all` on
   any change under `skills/tools/`.
4. **Embedding-based recommend** — `query_skills.py recommend "<task>"`
   using descriptions embedded via the existing embedding_engine.
5. **Verifier exemptions** — add an optional `tme_exempt_sections:`
   frontmatter key for legitimate domain cases (e.g., `voice_pipeline`
   having no auth).
6. **Gotchas bullet enforcement** — require at least one `-` bullet
   under `## Gotchas`.
7. **Fix the 7 failing skills** (shadcn_ui, voice_pipeline, whop +
   others) in a focused re-research pass.

---

## Files touched

```
A  scripts/_tme_common.py
A  scripts/sync_skills_to_neon.py
A  scripts/verify_tool_skill.py
A  scripts/check_skill_staleness.py
A  scripts/build_skill_graph.py
A  scripts/query_skills.py
A  scripts/__init__.py
A  docs/system/tool_mastery_engine_system.md
A  docs/system/skill_graph.md
A  docs/system/skill_graph.json
A  docs/audits/2026-04-06-tool-mastery-system-upgrade.md
```

No modifications to existing TME SKILL.md or any tool skill files —
this was purely additive system infrastructure.
