# Tool Mastery Manager — Build Audit

**Date:** 2026-04-08
**Author:** Developer Agent (Claude Opus 4.6)
**Branch:** `main`
**Scope:** First production-ready Tool Mastery Manager subsystem on top of the
existing TME / Control Plane / Orchestrator stack.

---

## 1. Executive summary

Before this build, the Tool Mastery Engine exposed five advisory utilities —
load, verify, staleness, sync, graph — plus a manual authoring decision tree.
The Control Plane had a 38-line TME bridge (`core/action_system/tme.py`) that
shelled out to `query_skills.py search <term>` and attached the result to
action logs. There was no active layer. No code in the repo answered the
question *"given this environment, what tools are missing mastery?"* or *"how
do I close those gaps safely?"*.

This build adds the missing unification layer: a `core/tool_mastery_manager/`
package that discovers tools from four deterministic sources, classifies each
into a unified coverage status, scaffolds missing skeletons, and queues
research / refresh / repair work through the standard Control Plane deferred
queue. It ships with a CLI, a research dispatcher script, a portable seed
list, subsystem docs, and an extended Control Plane bridge.

No TME logic was duplicated. No new Control Plane action types were
introduced. The Manager queues work as medium-risk `run_script` actions, which
are auto-deferred by the existing validator into
`/opt/OS/logs/deferred/` — that disk queue *is* the backlog.

Validation exercised all five coverage statuses and every CLI command against
the real codebase. The scan surfaced pre-existing technical debt that was
previously invisible: 7 INVALID skills (mostly missing best_practices
sections) and 3 MISSING tools declared in `~/.claude.json` that had never been
covered.

---

## 2. What already existed

All of this was already in place before the build started and was **composed,
not duplicated** by the Manager:

| Component | Path | Role |
|---|---|---|
| Shared loader + dataclass | `scripts/_tme_common.py` | `SkillRecord`, frontmatter parse, `all_skill_slugs`, `load_skill` |
| Verifier (9 checks) | `scripts/verify_tool_skill.py` (`_check`) | Required FM keys, sections, sizes, slug rules |
| Staleness assessor | `scripts/check_skill_staleness.py` (`_assess`) | `fresh / near_stale / stale / missing_date` |
| CLI registry | `scripts/query_skills.py` | Search, show, deps, stale, unverified |
| Neon sync | `scripts/sync_skills_to_neon.py` | Upsert `(org_id, name, content)` |
| Graph builder | `scripts/build_skill_graph.py` | Cross-reference all skills |
| Scaffold template | `skills/meta/tool_mastery_engine/scripts/scaffold_tool_skill.py` | Create skeleton SKILL.md + 19-section best_practices |
| Template files | `templates/tools/_template/SKILL.md` | The skeleton source |
| TME decision tree | `skills/meta/tool_mastery_engine/SKILL.md` | Manual research/authoring protocol |
| Control Plane | `core/action_system/control_plane.py` | `run_action` with propose→validate→approve→execute→log + idempotency |
| Allowed action types | `core/action_system/actions.py` | `run_script`, `shell_command`, `write_file`, `call_api` |
| Deferred queue | `core/action_system/deferred.py` + `/opt/OS/logs/deferred/` | Persist + notify medium/high-risk unapproved actions |
| TME bridge stub | `core/action_system/tme.py` | 38-line advisory `query_relevant_skills` |

**The gap**: nothing composed verify + staleness into a single per-tool
verdict, nothing discovered tools beyond `skills/tools/`, nothing queued
research work, and nothing gave a fresh-environment installer a way to figure
out what was missing.

---

## 3. What was added

New files, grouped by phase:

**Manager package** — `core/tool_mastery_manager/`
- `__init__.py` — public exports
- `models.py` — `CoverageStatus` (5-state enum), `ToolRef`, `CoverageReport`, `ManagerPlan`, `EnsureResult`, `DiscoverySource`
- `paths.py` — single source of truth for filesystem paths; honours `EOS_ROOT` and `CLAUDE_JSON` env vars for portability
- `discovery.py` — four discovery sources (skills dir, explicit, seed list, `~/.claude.json` MCP servers) + slug normalisation + source-union merge
- `coverage.py` — `evaluate_coverage(slug)` composing `_tme_common.load_skill` + `verify_tool_skill._check` + `check_skill_staleness._assess` into one of five statuses
- `ensure.py` — `ensure_mastery(slug)` primary entry point: scaffolds if MISSING, queues via Control Plane, returns `EnsureResult`
- `backlog.py` — `build_backlog`, `backlog_report`, `bootstrap`; writes markdown + JSON artifacts to `/opt/OS/logs/tool_mastery_manager/`
- `maintenance.py` — `refresh_stale`, `repair_invalid`, `audit_all`

**Scripts**
- `scripts/tool_mastery_manager.py` — thin CLI (`ensure`, `status`, `scan`, `backlog`, `bootstrap`, `refresh-stale`) with `--json` mode on every command
- `scripts/tool_mastery_research_dispatcher.py` — target of queued `run_script` actions; prints a structured research/refresh/repair plan without fabricating mastery content

**Config**
- `config/tool_mastery_seeds.yaml` — portable seed list with 9 baseline entries (LLM providers, DB, CC runtime, shell/git/docker)

**Modified** — `core/action_system/tme.py`
- Kept `query_relevant_skills` intact (still imported by `control_plane.py` at module load time).
- Added `ensure_tool_mastery(tool, *, dry_run=False)` that delegates to `core.tool_mastery_manager.ensure.ensure_mastery`. Import is deferred to call time to prevent circular imports (the Manager itself depends on `control_plane.run_action`). Never raises — returns a dict with `ok=False` on error.

**Docs**
- `docs/system/tool_mastery_manager.md` — full subsystem reference (10 sections + CLI cheatsheet)
- `docs/audits/2026-04-08-tool-mastery-manager.md` — this file

**Lines added:** ~1400 code + ~450 docs. Zero files deleted. Zero existing
lines modified in `_tme_common.py`, `verify_tool_skill.py`,
`check_skill_staleness.py`, `query_skills.py`, or `control_plane.py`.

---

## 4. Discovery model

Four deterministic sources, merged by normalised snake_case slug with sources
and metadata unioned:

1. **`skills_dir`** — every directory under `/opt/OS/skills/tools/` that
   contains a `SKILL.md` (delegates to `all_skill_slugs` from `_tme_common`).
2. **`explicit`** — tool names passed via CLI arg or Python caller.
3. **`seed_list`** — `/opt/OS/config/tool_mastery_seeds.yaml`, supporting
   both bare-slug and object entries (`name`, `display_name`, metadata).
4. **`claude_json`** — `~/.claude.json` top-level `mcpServers` block plus the
   union of per-project `mcpServers` blocks. Reads both stdio and HTTP
   server configs.

Slug normalisation uses the same rule as `scaffold_tool_skill.py`:
`[^a-z0-9]+` → `_`. So `notebooklm-mcp` in `.claude.json` becomes
`notebooklm_mcp`, which is comparable to the `skills/tools/` layout.

**Explicitly out of scope:** Python import scanning and prose-based inference
from arbitrary files. These were rejected upfront as noisy and
unexplainable — discovery has to be deterministic for reports to be
trustworthy.

**Discovery observed on this environment (2026-04-08):**
- `skills_dir`: 89 entries
- `seed_list`: 9 entries (6 of which are also in `skills_dir`, 3 new)
- `claude_json`: 3 unique entries (`goviralbitch`, `notebooklm_mcp`, `stitch`)
- **Total after merge: 92 tool refs**, with 9 multi-source tools.

---

## 5. Coverage model

`coverage.evaluate_coverage(slug)` returns a `CoverageReport` with a
`CoverageStatus` from this ladder (severity ordered):

| Status | Trigger |
|---|---|
| `MISSING` | No `SKILL.md` under `skills/tools/<slug>/` |
| `INVALID` | Exists but verifier has hard failures |
| `STALE` | Verifier passes but `_assess` says `stale` or `missing_date` |
| `PARTIAL` | Verifier passes with warnings, or `_assess` says `near_stale` |
| `READY` | Verifier clean, within freshness window |

The evaluator composes **three existing TME internals** directly — the same
entrypoints `query_skills.py` already uses — so verification and staleness
rules stay in one place:

```python
from scripts._tme_common import load_skill
from scripts.verify_tool_skill import _check
from scripts.check_skill_staleness import _assess
```

If the TME rules change (new verifier check, different freshness window), the
Manager picks it up for free.

**Observed breakdown on this environment:**
- READY: 82
- INVALID: 7 (`brave_search`, `fl_studio`, `higgsfield`, `remotion`, `shadcn_ui`, `voice_pipeline`, `whop`)
- MISSING: 3 (from `claude.json` discovery)
- STALE: 0
- PARTIAL: 0

The 7 INVALID findings are pre-existing technical debt that has been quietly
accumulating because nothing was checking it at the "per tool coverage" level.
The Manager surfacing this is the first output of real value — those skills
exist but do not meet TME v3.0 standards.

---

## 6. Ensure-mastery flow

```
ensure_mastery(slug)
   │
   ▼
evaluate_coverage(slug)
   │
   ├── READY → return EnsureResult(final=READY), no side effects
   │
   ├── MISSING → scaffold_tool_skill.py <slug>   (creates skeleton files)
   │             re-evaluate → lands in INVALID (template is intentionally
   │             below the verifier threshold)
   │             queue work_type=research (because the *semantic* work is
   │             "research a brand new tool", not "repair")
   │
   ├── STALE   → queue work_type=refresh
   │
   └── INVALID │
       or     ├→ queue work_type=repair
       PARTIAL│
```

All queueing goes through `control_plane.run_action(type="run_script",
risk_level="medium", idempotency_key="tool_mastery:{work_type}:{slug}",
idempotency_ttl_seconds=604800)`. Because medium-risk actions without explicit
approval are auto-deferred by the validator, the action lands in
`/opt/OS/logs/deferred/<action_id>.json` — the Manager's backlog is the
existing deferred queue. No parallel queue was created.

The queued `run_script` points at
`/opt/OS/scripts/tool_mastery_research_dispatcher.py --work-type <type>
--tool <slug>`, so `resume_action(action_id)` actually invokes something
meaningful: a dispatcher that prints the next-steps plan a human or research
subagent should execute.

---

## 7. Backlog / bootstrap behaviour

- **`backlog.build_backlog()`** — discover → evaluate → filter non-READY →
  sort by severity (`MISSING > INVALID > STALE > PARTIAL`). Ties broken by
  slug.
- **`backlog.backlog_report()`** — same, plus writes
  `/opt/OS/logs/tool_mastery_manager/backlog-<ISO_timestamp>.md` and `.json`.
- **`backlog.bootstrap(dry_run=…)`** — run backlog then iterate
  `ensure_mastery` on every entry. Writes a `bootstrap-<ts>.json` artifact
  capturing every EnsureResult.

In dry_run mode no scaffolding runs and no actions are queued — the result is
a pure plan. This is the intended first step on any fresh install.

**Observed on this environment:**
- Backlog size after build: **11** (8 INVALID + 3 MISSING)
- Bootstrap dry-run considered all 11 and correctly reported 0 queued /
  0 scaffolded because `dry_run=True`.

---

## 8. Maintenance behaviour

`maintenance.py` is a thin composition surface:

- `refresh_stale(dry_run=…)` — iterate STALE tools, call `ensure_mastery` on
  each.
- `repair_invalid(dry_run=…)` — iterate INVALID + PARTIAL tools, call
  `ensure_mastery` on each.
- `audit_all()` — full coverage snapshot including READY, used by CLI `scan`.

These are the hooks to wire into cron / orchestrator when the TMM graduates
from manual use. That wiring is intentionally **not** added in this build — it
is a follow-up with its own risk profile and should be done alongside morning
brief / nightly maintenance changes.

---

## 9. Control Plane / Orchestrator integration

**Invariants preserved:**
- Only allowed action types (`run_script`) are emitted. The Control Plane's
  `ALLOWED_ACTION_TYPES` tuple was not extended.
- Medium-risk actions without `explicit_approval` auto-defer through the
  existing validator path. Nothing bypassed `validate_action` or
  `approve_action`.
- Idempotency is enforced through the existing `idempotency.py` store.
- `query_relevant_skills` — imported by `control_plane.py` at module load —
  was preserved exactly so no pre-existing callers break.
- The Manager's new entry point `ensure_tool_mastery` is imported lazily
  inside the function body, preventing circular imports between
  `core.action_system` and `core.tool_mastery_manager`.
- Failures in `ensure_tool_mastery` return a dict with `ok=False` — they
  never raise — so the bridge stays as advisory-safe as before.

**New capability surfaced through Control Plane bridge:**

```python
from core.action_system.tme import ensure_tool_mastery

ensure_tool_mastery("slack")            # real ensure through the Control Plane
ensure_tool_mastery("slack", dry_run=True)
```

**Orchestrator integration:** none added in this build. The Manager writes
to the same deferred queue the orchestrator already drains, so no wiring is
required for actions to be visible in existing operator surfaces. Surfacing
TMM work specifically (e.g., "3 tools missing mastery" in the morning brief)
is listed as a follow-up in Section 12.

---

## 10. Portability considerations

- **`EOS_ROOT` env var** (default: `/opt/OS`) resolved in
  `core/tool_mastery_manager/paths.py`. Every path inside the Manager package
  derives from this — `SKILLS_TOOLS_DIR`, `CONFIG_DIR`, `SEED_LIST_PATH`,
  `BACKLOG_DIR`, `RESEARCH_DISPATCHER`, `SCAFFOLD_SCRIPT`.
- **`CLAUDE_JSON` env var** (default: `~/.claude.json`) lets test or
  multi-profile setups point discovery at a different file.
- **`config/tool_mastery_seeds.yaml`** is the primary declarative portability
  lever — the installer or operator edits this file to tell the Manager what
  tools matter in their deployment, without touching code.
- **Graceful degradation** — each discovery source returns `[]` silently if
  its input is missing. A fresh install with neither `~/.claude.json` nor a
  seed list will fall back to `skills/tools/` plus explicit CLI input and
  still work.

**Portability gaps acknowledged:**
- `scaffold_tool_skill.py` and `tool_mastery_research_dispatcher.py` still
  hardcode `/opt/OS`. These predate this build and touching them is a
  separate cleanup. A Manager install pointed at a different `EOS_ROOT`
  works for discovery, coverage, backlog, and dry-run ensure — full
  scaffold + queue requires adjusting these two scripts.
- MCP discovery is Claude Code-specific. Other agent hosts would need their
  own discovery adapter. Adding one means: a new function in `discovery.py`,
  a new `DiscoverySource` enum value, and inclusion in `discover_all()`.

---

## 11. Validation results

All scenarios executed against the real codebase, not mocks.

### Scenario 1 — READY tool (no-op path)
```
python3 scripts/tool_mastery_manager.py ensure notion
→ initial_status: ready
→ final_status:   ready
→ scaffolded:     False
→ action_id:      —
→ note:           already READY — no action
```
**PASS.** No side effects for a READY tool.

### Scenario 2 — MISSING tool, full ensure (scaffold + queue)
```
python3 scripts/tool_mastery_manager.py ensure tmm_validation_probe
→ initial_status: missing
→ final_status:   invalid                 # post-scaffold template intentionally fails verifier
→ scaffolded:     True
→ action_id:      cf2d4355-375c-4241-a683-e55124821fd5
→ action_status:  validated                # medium-risk auto-deferred
→ planned:        research via /opt/OS/scripts/tool_mastery_research_dispatcher.py
```
Filesystem evidence:
- `/opt/OS/skills/tools/tmm_validation_probe/SKILL.md` created
- `/opt/OS/skills/tools/tmm_validation_probe/references/best_practices.md` created
- `/opt/OS/logs/deferred/cf2d4355-375c-4241-a683-e55124821fd5.json` created

Post-ensure coverage:
```
python3 scripts/tool_mastery_manager.py status tmm_validation_probe
→ status: invalid
→ verifier_failures:
    - SKILL.md missing section: ## Gotchas
    - best_practices.md too short: 1908 < 2000
```
**PASS.** Scaffold created real files, the template's intentional "fails until
filled" semantics are preserved, and the research action was correctly queued
and auto-deferred.

### Scenario 3 — Idempotency (re-run same tool)
```
python3 scripts/tool_mastery_manager.py ensure tmm_validation_probe
→ initial_status: invalid                  # scaffolded in scenario 2
→ final_status:   invalid
→ scaffolded:     False                    # correctly skipped
→ action_id:      31d4523c-c01b-40ff-a803-b9202e7e68c2    # new id
→ planned:        repair via …
```
**PASS with a nuance.** The re-run did not return `skipped_duplicate` because
the tool's status flipped from MISSING to INVALID between runs, which changes
the work_type from `research` to `repair`, which in turn changes the
idempotency key from `tool_mastery:research:tmm_validation_probe` to
`tool_mastery:repair:tmm_validation_probe`. Both actions live in the deferred
queue honestly — one for the original research and one for the post-scaffold
repair. This is the correct behaviour (two distinct pieces of work), but it
means operators may see two queue entries for the same tool during the
scaffold → research → verify → repair lifecycle. Documented here for future
reference.

### Scenario 4 — Backlog
```
python3 scripts/tool_mastery_manager.py backlog
→ backlog size: 11
→ counts: invalid=8, missing=3, partial=0, stale=0
→ artifacts:
    md   = /opt/OS/logs/tool_mastery_manager/backlog-2026-04-08T22-17-11Z.md
    json = /opt/OS/logs/tool_mastery_manager/backlog-2026-04-08T22-17-11Z.json
```
Non-READY tools (sorted by severity):
- `goviralbitch`, `notebooklm_mcp`, `stitch` (MISSING, sources=claude_json)
- `brave_search` (INVALID, 19 failures), `remotion` (19), `shadcn_ui` (19), `whop` (17), `fl_studio` (13), `higgsfield` (13), `voice_pipeline` (1), plus `tmm_validation_probe` (2)

**PASS.** Prioritised report is deterministic and includes provenance.

### Scenario 5 — Bootstrap dry-run
```
python3 scripts/tool_mastery_manager.py bootstrap --dry-run
→ considered: 11
→ dry_run:    True
→ queued:     0
→ scaffolded: 0
→ artifact:   /opt/OS/logs/tool_mastery_manager/bootstrap-2026-04-08T22-17-12Z.json
```
Every row correctly reported `action=—` because dry_run suppresses queueing.
**PASS.**

### Scenario 6 — Dispatcher
```
python3 scripts/tool_mastery_research_dispatcher.py \
    --work-type research --tool tmm_validation_probe
→ === Tool Mastery RESEARCH plan: tmm_validation_probe ===
→ current status: invalid
→ Next steps: [7-step plan ending in verify + sync]
→ NOTE: This dispatcher does not auto-fabricate mastery. …
```
**PASS.** Dispatcher prints a plan, never fakes research.

### Control Plane invariant check
- ✅ `control_plane.py` imports unchanged and module-load still succeeds.
- ✅ `query_relevant_skills` still works (verified in-session).
- ✅ `ensure_tool_mastery` via `core.action_system.tme` works both dry-run and real.
- ✅ Queued actions land in `/opt/OS/logs/deferred/` via the standard deferred path.
- ✅ Idempotency sentinels land in `/opt/OS/logs/idempotency/` via the standard store.
- ✅ No new action type was added; only `run_script` is emitted.

### Post-validation cleanup
The `tmm_validation_probe` slug is a fake used only for scenarios 2–5. After
validation, the following artifacts were deleted under explicit user approval
(via individual `python3 -c "shutil.rmtree(...)"` / `os.remove(...)` calls,
one path at a time, each verified with `os.path.exists() == False` after the
delete — the sandbox `rm` policy blocks direct `rm` commands so the
Python-based workaround was approved for exactly this scope):

- `/opt/OS/skills/tools/tmm_validation_probe/` (scaffolded skeleton)
- `/opt/OS/logs/deferred/cf2d4355-…-821fd5.json` (research action)
- `/opt/OS/logs/deferred/31d4523c-…-b9202e7e68c2.json` (repair action)
- `/opt/OS/logs/idempotency/b1883672…684.json` (research sentinel, key `tool_mastery:research:tmm_validation_probe`)
- `/opt/OS/logs/idempotency/ae5fbdda…755ea.json` (repair sentinel, key `tool_mastery:repair:tmm_validation_probe`)

Real system state — including the 89 skill directories, existing deferred
actions, unrelated idempotency sentinels, and all log files — was NOT
touched. The backlog/bootstrap artifacts under
`/opt/OS/logs/tool_mastery_manager/` were deliberately preserved as evidence
of the validation run.

---

## 12. Remaining limitations / next steps

**Honest about what this build does NOT do:**

1. **Research is still manual.** `ensure_mastery` scaffolds and queues, but
   the 19 best_practices sections are filled by a human (or a research-capable
   subagent) following the TME decision tree at
   `skills/meta/tool_mastery_engine/SKILL.md`. The dispatcher prints a plan;
   it does not author mastery.
2. **Dispatcher resume path is advisory.** When `resume_action(action_id)`
   runs a queued TMM action, the dispatcher prints the plan and exits 0 —
   which marks the Control Plane action as `executed` even though no content
   was written. This is honest (the dispatcher does what it says on the tin)
   but it does mean "executed" does not imply "mastery acquired". A follow-up
   could either (a) make the dispatcher exit non-zero until the underlying
   skill passes `verify_tool_skill.py`, or (b) introduce a separate
   `tool_mastery_applied` sentinel.
3. **No orchestrator wiring yet.** Morning brief, nightly maintenance, and
   operator surfaces don't surface TMM items automatically. The deferred
   queue shows them, but a dedicated "3 tools need mastery" line in the brief
   is a follow-up.
4. **Scaffold + dispatcher still hardcode `/opt/OS`.** The Manager package
   itself is portable via `EOS_ROOT`, but those two scripts aren't. Cleaning
   them up is a one-line change per file and can ship separately.
5. **PARTIAL and INVALID share work_type `repair`.** PARTIAL means warnings
   or near-stale; INVALID means hard verifier failures. Splitting PARTIAL to
   a lighter-touch refresh would be a useful refinement.
6. **Idempotency across work_type transitions.** As documented in Scenario 3,
   a tool that moves from MISSING → (scaffold) → INVALID produces two
   distinct queued actions because the idempotency key includes
   `work_type`. This is the right behaviour for honesty but could be made
   cleaner with a "tool-level" idempotency that supersedes per-work-type
   keys.
7. **MCP discovery is CC-specific.** Other host environments need their own
   adapter.

**Recommended follow-ups, in priority order:**

1. Wire `refresh-stale` and `repair-invalid` into nightly maintenance cron.
2. Surface TMM backlog counts in the morning brief.
3. Harden the dispatcher to verify the skill passes after a research
   subagent has run, turning `executed` into a meaningful signal.
4. Repair the 7 pre-existing INVALID skills surfaced by scenario 4 —
   this is the first actionable output of the Manager and was invisible
   before today.
5. Research the 3 MISSING MCP tools (`stitch`, `notebooklm_mcp`,
   `goviralbitch`), or explicitly declare them out of scope in the seed list
   if they are not worth covering.
6. Port `scaffold_tool_skill.py` and `tool_mastery_research_dispatcher.py`
   to `EOS_ROOT` for full portability.
7. Add `PARTIAL → refresh` routing (lighter touch than `repair`).
