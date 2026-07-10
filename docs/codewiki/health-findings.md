---
type: codewiki-page
dir: (cross-cutting)
---

# Health Findings

**Repository health audit — every finding below was verified with a command on the live `/opt/OS` tree (2026-07-10); the evidence is shown inline.** Findings are ranked by severity. This page feeds the consolidated `audit-2026-07-10.md`.

Ground-truth scale (from `docs/codewiki/_manifest.json`): the raw tree is **716,891 files**; the structural graph indexes **2,428 code files / 664,724 lines**. The gap is dominated by runtime data and logs, which is the source of most findings here.

---

## Critical

### C1 — `data/` is 36GB on a lightweight VPS (Node Role Discipline violation)

```
$ du -sh data → 36G
  32G  data/archive
  3.5G data/umh
  447M data/audits
  145M data/codebase_pages
```

The VPS is defined as the **lightweight, always-on coordination brain** — its role explicitly excludes "archive dirs, old proofs, or ingestion intermediaries" (`CLAUDE.md`, Node Role Discipline). `data/archive` alone is 32GB. Archive belongs on the Beast (full mirror, heavy storage), not the orchestrator. **Recommendation:** move `data/archive` off the VPS to the Beast, keep only what the coordination role requires. This is the single largest disk-pressure item and a direct role violation.

### C2 — Live structural graph on `main` is 311 commits stale

```
$ ls -la data/codebase_graph.json → 63MB, mtime Jul 1 22:13
  generated_at: 2026-07-02T05:13:03Z
$ git log -1 --format=%ci → 2026-07-10
$ git log --oneline --since=2026-07-02 | wc -l → 311
```

The graph that the Cognition Stack and retrieval hierarchy depend on was built 2026-07-02 and is **311 commits behind** the current HEAD. Every "Palace → Graph → Summaries" retrieval on `main` is querying a week-old picture of the code, and structural decisions made against it may be wrong. **Recommendation:** run `scripts/update-graph` on `main` to rebuild graph + palace + summaries end-to-end. (This CodeWiki uses a *fresh* worktree-scoped graph built today, so its numbers are current; the problem is the graph living in the live checkout.)

---

## High

### H1 — Broken symlink `logs/logs` → missing `_holding/logs`

```
$ ls -la logs/logs → logs/logs -> /opt/OS/_holding/logs
$ ls -la _holding/logs → No such file or directory
```

A dangling symlink. Any code or `find` traversal that follows it errors or silently skips. **Recommendation:** remove the symlink (`rm logs/logs`) — its target directory no longer exists.

### H2 — `logs/` is 1.2GB / 212,556 files (unbounded growth)

```
$ du -sh logs → 1.2G
$ find logs -type f | wc -l → 212,556
```

`logs/` holds 212K files — the overwhelming majority of the raw tree's file count. Nothing here is truncated or rotated. On a lightweight VPS this is real disk and inode pressure, and it makes every full-tree `find` slow. **Recommendation:** add log rotation/pruning (age or size cap) and confirm `logs/` is gitignored.

### H3 — 36MB of stale verification artifacts committed at repo root

```
$ du -sh .playwright-mcp → 30M (162 files: cockpit-*.png, console-*.log dated 2026-05)
$ ls -la scripts/agent_executor.log → 8.3MB, mtime Jul 10 13:21 (a live log inside scripts/)
```

`.playwright-mcp/` is 30MB of browser screenshots and console logs from May, sitting in the repo root. `scripts/agent_executor.log` is an 8.3MB actively-growing log living inside the source directory `scripts/`. Neither belongs in tracked/working source. **Recommendation:** move both under `logs/` (or delete `.playwright-mcp/` outright) and gitignore.

### H4 — `services/instagram_session.json` (184KB) — possible session credential in source dir

```
$ ls -la services/instagram_session.json → 184843 bytes, mtime Apr 29
```

A 184KB Instagram *session* file living in the `services/` source directory. Session files typically carry auth cookies/tokens. Per the Instance Context and Credential Injection laws, secrets never live in source — they belong in 1Password / env. **Recommendation:** confirm contents, remove from the tree, verify it is not (and never was) committed, rotate the session if it was exposed. (Contents not inspected here to avoid handling credentials.)

---

## Medium

### M1 — Runtime JSON state written into the `services/` source directory

```
$ ls services/*.json →
  calls_log.json  cost_log.json  kpi_history.json  opener_stats.json
  revenue_log.json  scraped_posts.json  hashtag_config.json
```

Services write their runtime state (call logs, cost logs, KPI history, scraped posts) as JSON *next to their own source*. `services/` is meant for deployment entrypoints only (`.claude/rules/architecture-layers.md`) — mutable runtime state belongs under `data/` or `logs/`, not mixed into code. This also churns git if any are tracked. **Recommendation:** relocate runtime JSON to `data/umh/` and point the services at the new paths.

### M2 — `saas/` source is gone; only a Python-3.12 `.pyc` remains

```
$ find saas -type f -not -path '*/node_modules/*'
  → saas/bridge/__pycache__/organism_bridge.cpython-312.pyc   (only file)
```

The `saas/` directory (the EOS projection surface per the Architecture Layer Law) has **no source left** outside `node_modules/` — just a single compiled `organism_bridge.cpython-312.pyc`. The `.pyc` is `cpython-312`, but Docker runs Python 3.11, so it could never be imported in the container even if the source returned. `node_modules/` (4,386 files) is also present on the VPS, which Node Role Discipline forbids for inactive frontends. **Recommendation:** delete the orphan `.pyc` and the `node_modules/`; if `saas/` is meant to be live, restore its source from the Beast mirror.

### M3 — `.claire/` dead worktree remnant with 3.12 `.pyc` files

```
$ find .claire -type f
  .claire/worktrees/full-convergence/.../test_ontology_enacted.cpython-312.pyc
  .claire/worktrees/full-convergence/.../test_registry.cpython-312.pyc
  .claire/worktrees/full-convergence/.../primitives.cpython-312.pyc
```

`.claire/` is a leftover worktree root (`full-convergence` branch) holding nothing but three orphaned `cpython-312` `.pyc` files — no source, no live worktree. It is dead and 3.12-tainted. **Recommendation:** `rm -rf .claire/` (Node Role Discipline: remove worktrees immediately after merge).

### M4 — Mixed-interpreter `.pyc` in `umh/__pycache__`

```
$ find umh -name '*.pyc'
  umh/__pycache__/voice_preflight.cpython-311.pyc   ← correct
  umh/__pycache__/voice_preflight.cpython-312.pyc   ← wrong interpreter
  umh/__pycache__/voice_server.cpython-312.pyc
  umh/__pycache__/vision_relay.cpython-312.pyc
```

`umh/` has both 3.11 and 3.12 compiled artifacts — evidence a 3.12 host ran this code, which the Docker 3.11 constraint forbids. `voice_server.cpython-312.pyc` has no `.py` beside it (source moved/renamed). **Recommendation:** clear all `__pycache__` (`find . -name __pycache__ -type d -prune -exec rm -rf {} +`) and ensure only 3.11 ever executes this tree.

### M5 — Two files exceed the 3,000-line god-file limit

```
$ wc -l → 3113 services/discord_bot_commands.py
         3010 umh/vision_relay.py
```

The Codebase Quality Standard is "No Python file over 3,000 lines — split before moving on" (`CLAUDE.md`). Both files are just over. **Recommendation:** split each along a natural seam (command groups for the Discord file; relay concerns for `vision_relay.py`).

### M6 — 20 tracked runtime-data files modified-but-uncommitted on `main`

```
$ git status --short | grep -cE '^ ?[MD]' → 20
  e.g.  M data/umh/organism/events.jsonl
        M data/umh/organism/execution_journal.jsonl
        D data/umh/operator_experience/dex_conversations.jsonl
        M data/umh/organism/workcells/*/heartbeat.json
```

The live organism writes its state (`events.jsonl`, heartbeats, work packets, journals) into **git-tracked** files, so the working tree on `main` is permanently dirty and one file was even deleted (`dex_conversations.jsonl`). Runtime state should not be version-controlled. **Recommendation:** move these paths out of tracking (gitignore `data/umh/**/*.jsonl` and the heartbeat/queue JSON), keeping only seed/config committed.

---

## Low

### L1 — `knowledge/index.md` frontmatter date drifts from file reality

```
$ head knowledge/index.md → updated: 2026-04-05
$ ls -la knowledge/*.md → all mtime May 22 (index.md, log.md, retrieval_rules.md, ...)
```

The wiki index declares `updated: 2026-04-05` in frontmatter but the file (and its siblings) were last written May 22 — a self-reported staleness marker that undersells the drift. The knowledge wiki has not been maintained in ~7 weeks. **Recommendation:** refresh the index or correct the `updated` field so the retrieval hierarchy's top tier isn't trusted as fresher than it is.

### L2 — `media/` empty scaffold

```
$ find media -type f | wc -l → 0   (only media/higgsfield/, empty)
```

`media/` contains one empty subdirectory and no files — a scaffold that was never populated. Harmless but dead. **Recommendation:** remove or populate.

### L3 — `data/codebase_pages/` — 35,582 files, untracked

```
$ find data/codebase_pages -type f | wc -l → 35,582
$ git ls-files data/codebase_pages | wc -l → 0
```

35K generated codebase-page files, none tracked by git (correctly gitignored), but 145MB on disk on the lightweight node. Intermediate ingestion output that Node Role Discipline says shouldn't accumulate on the VPS. **Recommendation:** prune stale pages or keep them only on the Beast.

### L4 — Large single-file JSON state blobs

```
$ du -h runtime/.substrate_station/.inbox.json → 46M   (one JSON file)
$ du -h graphify-out/graph.json → 42M
```

`runtime/.substrate_station/.inbox.json` is a 46MB single JSON document — read/parse cost grows with every append, and an interrupted write can corrupt the whole file. `graphify-out/graph.json` is another 42MB artifact. **Recommendation:** move `.inbox.json` to an append-only JSONL or a table; treat `graphify-out/` as a build artifact (gitignore, prune).

---

## Fixed in this PR

### F1 — `codebase_graph.py` worktree self-exclusion bug — FIXED

```
$ git diff main -- scripts/codebase_graph.py
- if any(part in SKIP_DIRS for part in path.parts):
+ if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):   (×2, lines 381 & 592)
```

The graph builder excluded `SKIP_DIRS` by checking **absolute** path parts. When `ROOT` is itself a worktree under `.claude/worktrees/` (as it is for this CodeWiki build), `worktrees` appears in the absolute path and the check nuked the *entire* tree — zero files indexed. This PR switches both scan sites to check parts **relative to ROOT**, matching the known "gate-worktree-exclude" lesson (tree-scanning gates must exclude by relative path). This is exactly why the CodeWiki's graph could be built worktree-scoped and returns the correct 1,929 Python / 485 TypeScript counts.

---

## Summary table

| ID | Severity | Finding | Fix |
|---|---|---|---|
| C1 | Critical | `data/archive` = 32GB on lightweight VPS | Move to Beast |
| C2 | Critical | Live graph 311 commits stale on `main` | Run `scripts/update-graph` |
| H1 | High | Broken `logs/logs` symlink | `rm logs/logs` |
| H2 | High | `logs/` = 1.2GB / 212K files, no rotation | Add rotation + gitignore |
| H3 | High | 30MB `.playwright-mcp/` + 8MB log in `scripts/` | Move to `logs/`, gitignore |
| H4 | High | `services/instagram_session.json` possible creds | Remove, rotate, verify never committed |
| M1 | Medium | Runtime JSON written into `services/` | Relocate to `data/` |
| M2 | Medium | `saas/` source gone, only 3.12 `.pyc` + node_modules | Delete orphans / restore source |
| M3 | Medium | `.claire/` dead worktree, 3.12 `.pyc` only | `rm -rf .claire/` |
| M4 | Medium | Mixed 3.11/3.12 `.pyc` in `umh/` | Clear `__pycache__` |
| M5 | Medium | 2 files > 3,000-line limit | Split |
| M6 | Medium | 20 tracked runtime files dirty on `main` | Gitignore runtime state |
| L1 | Low | `knowledge/index.md` date drift | Refresh index |
| L2 | Low | `media/` empty scaffold | Remove |
| L3 | Low | 35K untracked codebase pages, 145MB | Prune / Beast-only |
| L4 | Low | 46MB + 42MB single-file JSON blobs | JSONL / build artifact |
| F1 | Fixed | Graph worktree self-exclusion bug | Fixed in this PR |

## See also

- [conventions.md](conventions.md) — the laws these findings measure against (Node Role Discipline, Instance Context, Architecture Layers, Docker 3.11)
- [tech-stack.md](tech-stack.md) — the runtime + Python-3.11 constraint behind the `.pyc` findings
- [audit-2026-07-10.md](audit-2026-07-10.md) — consolidated audit this page feeds
- [dirs/data.md](dirs/data.md) · [dirs/logs.md](dirs/logs.md) · [dirs/services.md](dirs/services.md) — the directories most affected
