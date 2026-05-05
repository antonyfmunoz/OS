# Tool Mastery Engine — System Reference

The Tool Mastery Engine (TME) is a UMH substrate subsystem that
guarantees creator-level expertise with every external tool, SaaS,
API, adapter, runtime, and capability UMH touches. EOS is one
platform consumer of TME. Until 2026-04-06, TME was a manually
curated skill library. As of this upgrade, it is a **self-updating,
queryable, enforceable** system backed by five utility scripts and
a generated dependency graph.

This document describes the system layer. The authoring layer (the
in-skill decision tree) still lives in
`/opt/OS/skills/meta/tool_mastery_engine/SKILL.md`.

---

## Layout

```
/opt/OS/
├── skills/
│   ├── meta/tool_mastery_engine/       ← the engine skill itself
│   │   ├── SKILL.md                    (decision tree, research protocol)
│   │   ├── references/                 (section templates, registry)
│   │   └── scripts/scaffold_tool_skill.py
│   └── tools/                          ← 89 tool skills (as of 2026-04-06)
│       ├── notion/
│       │   ├── SKILL.md
│       │   └── references/best_practices.md
│       └── …
├── scripts/
│   ├── _tme_common.py                  ← shared loader / frontmatter parser
│   ├── sync_skills_to_neon.py          ← Neon sync
│   ├── verify_tool_skill.py            ← linter / verifier
│   ├── check_skill_staleness.py        ← freshness audit
│   ├── build_skill_graph.py            ← dependency graph
│   └── query_skills.py                 ← CLI registry
└── docs/system/
    ├── tool_mastery_engine_system.md   ← this file
    ├── skill_graph.md                  ← generated
    └── skill_graph.json                ← generated
```

---

## The five utilities

### 1. `sync_skills_to_neon.py` — Neon sync

Scans every tool skill and upserts `(org_id, name, content)` into the
`skills` Postgres table. `name` = slug, `content` = full SKILL.md,
`version` bumps on content change. No duplicate rows.

```bash
# Dry-run everything
python3 scripts/sync_skills_to_neon.py --all --dry-run

# Sync everything
python3 scripts/sync_skills_to_neon.py --all

# Sync a single skill
python3 scripts/sync_skills_to_neon.py --skill notion
```

**Notes**
- The `skills` table has no UNIQUE(org_id, name) constraint, so the
  script does a SELECT → UPDATE-or-INSERT rather than `ON CONFLICT`.
- Exit code `2` = at least one skill had a parse warning but the sync
  otherwise succeeded.

### 2. `verify_tool_skill.py` — linter / verifier

Replaces the fragile inline regex checks with a real YAML-aware
linter. For each skill it validates:

1. SKILL.md exists and ≥ 500 chars
2. Frontmatter parses as YAML (via `yaml.safe_load`, not regex)
3. Required frontmatter keys: `name`, `description`, `last_researched`, `source_url`
4. `last_researched` is a valid ISO date
5. SKILL.md contains `## Authentication` and `## Gotchas`
6. `references/best_practices.md` exists and ≥ 2000 chars
7. All 19 required best_practices sections present, tolerant of
   real-world header variance (`## 1. Authentication`,
   `### Authentication:`, etc.)
8. Directory slug is snake_case and matches frontmatter `name`
9. No Unicode replacement characters

```bash
python3 scripts/verify_tool_skill.py --all           # human output
python3 scripts/verify_tool_skill.py --all --quiet   # failures only
python3 scripts/verify_tool_skill.py --all --json    # machine output
python3 scripts/verify_tool_skill.py --skill notion
```

Exit code 0 if all pass, 1 if any fail, 2 on bad invocation.

### 3. `check_skill_staleness.py` — freshness audit

Compares each skill's `last_researched` against its `speed_category`:

| Speed category | Freshness window |
|---|---|
| `fast`   | 30 days |
| `medium` | 60 days (default) |
| `stable` | 90 days |

Rows are classified `fresh`, `near_stale` (≥ 80% of window), `stale`,
or `missing_date`.

```bash
python3 scripts/check_skill_staleness.py --all
python3 scripts/check_skill_staleness.py --all --only stale
python3 scripts/check_skill_staleness.py --all --markdown > /tmp/stale.md
python3 scripts/check_skill_staleness.py --skill notion
```

### 4. `build_skill_graph.py` — dependency graph

Cross-references every skill by scanning SKILL.md + best_practices.md
for mentions of other skill slugs, titles, and a short alias table.
Writes both machine- and human-readable output:

- `/opt/OS/docs/system/skill_graph.md`
- `/opt/OS/docs/system/skill_graph.json`

```bash
python3 scripts/build_skill_graph.py                # write files
python3 scripts/build_skill_graph.py --stdout       # preview markdown
python3 scripts/build_skill_graph.py --skill notion # single-skill deps
```

The graph reports nodes, edges, centrality, and orphans. Centrality
is simple degree (outgoing + incoming) — not PageRank. Keep it
grounded; graph theory over-engineering was explicitly out of scope.

### 5. `query_skills.py` — CLI registry

The practical entry point for asking TME questions without opening
files.

```bash
python3 scripts/query_skills.py count
python3 scripts/query_skills.py list
python3 scripts/query_skills.py search ads
python3 scripts/query_skills.py domain database
python3 scripts/query_skills.py show notion
python3 scripts/query_skills.py deps notion
python3 scripts/query_skills.py stale
python3 scripts/query_skills.py stale --only near_stale
python3 scripts/query_skills.py unverified
```

`deps` requires `build_skill_graph.py` to have been run first.
`unverified` shells out to `verify_tool_skill.py --all --json` so the
two tools stay in sync.

---

## Shared loader: `_tme_common.py`

All five scripts import from `scripts/_tme_common.py`, which provides:

- `SkillRecord` — dataclass wrapping a single skill (path, frontmatter, bodies)
- `load_skill(slug)` / `load_all_skills()` / `all_skill_slugs()`
- `_split_frontmatter(text)` — real YAML parsing, no regex
- `section_present(body, heading)` — tolerant header matcher that
  handles `## 1. Heading`, `### Heading:`, `## Heading (subtitle)`
- `REQUIRED_BP_SECTIONS`, `REQUIRED_SKILL_SECTIONS`
- `FRESHNESS_WINDOWS`, `freshness_window(speed)`, `days_since(d)`

If you find yourself adding ad-hoc regex against SKILL.md anywhere in
the repo, add it here instead.

---

## Operating workflow

A normal week of TME operation looks like this:

1. **On skill creation/update** (manual, via the TME decision tree):
   - Create or update the skill under `/opt/OS/skills/tools/<slug>/`
   - Run `verify_tool_skill.py --skill <slug>` until it passes
   - Run `sync_skills_to_neon.py --skill <slug>`

2. **Daily/weekly staleness audit**:
   ```bash
   python3 scripts/check_skill_staleness.py --all --only stale
   python3 scripts/check_skill_staleness.py --all --only near_stale
   ```
   Stale rows feed back into the TME Re-Research Flow.

3. **After any batch of updates**, rebuild the graph:
   ```bash
   python3 scripts/build_skill_graph.py
   python3 scripts/sync_skills_to_neon.py --all
   ```

4. **Quick lookups** during agent work:
   ```bash
   python3 scripts/query_skills.py search <keyword>
   python3 scripts/query_skills.py show <slug>
   python3 scripts/query_skills.py deps <slug>
   ```

---

## The self-updating loop

The five utilities close the TME loop:

```
        ┌──────────────────────────────────────────┐
        │                                          │
        ▼                                          │
  check_skill_staleness.py                         │
        │                                          │
        │ produces list of stale skills            │
        ▼                                          │
  TME Re-Research Flow (manual)                    │
        │                                          │
        │ updates SKILL.md + best_practices.md     │
        ▼                                          │
  verify_tool_skill.py --skill <slug>              │
        │                                          │
        │ must pass                                │
        ▼                                          │
  sync_skills_to_neon.py --skill <slug>            │
        │                                          │
        │ Neon is source of truth for agents       │
        ▼                                          │
  build_skill_graph.py                             │
        │                                          │
        │ refresh dependency graph                 │
        └──────────────────────────────────────────┘
```

At each point, `query_skills.py` provides a CLI into the current
state without touching files.

---

## Known limitations

- **No unique constraint** on `skills (org_id, name)` — the sync
  script tolerates it by doing a SELECT-first upsert, but a real DB
  migration to add `UNIQUE(org_id, name)` would be cleaner.
- **Centrality = raw degree.** No PageRank, no community detection.
  Good enough for "which skills are core".
- **Graph edges are text-based.** A skill that mentions `notion` in
  prose will be counted as referencing `notion` even if the mention
  is offhand. Precision > recall was not a goal here.
- **Alias list is short.** Only `postgres → neon_postgres` and a few
  obvious ones. Extend `ALIASES` in `build_skill_graph.py` as
  ambiguous cases arise.
- **Re-research is still manual.** The detector flags what's stale;
  humans (or the TME decision tree) still drive the research itself.

---

## Recommended next upgrades

1. Add `UNIQUE(org_id, name)` migration to the `skills` table so the
   sync script can use real `ON CONFLICT` upserts.
2. Wire `check_skill_staleness.py --all --only stale` into the nightly
   maintenance cron so stale skills surface automatically.
3. Add a `query_skills.py recommend "<task description>"` that uses
   embeddings (not keyword match) over all descriptions.
4. Auto-trigger `sync_skills_to_neon.py --all` from a post-commit
   git hook on any change under `skills/tools/`.
5. Extend the verifier to enforce `## Gotchas` contains at least one
   bullet (no empty Gotchas sections).
