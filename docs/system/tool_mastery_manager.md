# Tool Mastery Manager — System Reference

The **Tool Mastery Manager** (TMM) is the unification layer that sits
on top of the Tool Mastery Engine (TME). Where the TME exposes
read-only and advisory primitives — "load this skill", "verify this
skill", "is this skill stale?" — the Manager adds the missing *active*
layer:

> Given an environment, make sure every tool that matters has
> creator-level mastery coverage, scaffold what is missing, queue
> research/refresh/repair work through the Control Plane, and keep
> itself updated over time.

It is deliberately small. The Manager does not duplicate TME logic; it
composes it. It does not fabricate mastery content; it scaffolds
skeletons and queues research as a separate step.

---

## 1. Where it lives

```
/opt/OS/
├── core/
│   ├── action_system/
│   │   └── tme.py                    ← Control Plane bridge
│   │                                    (query_relevant_skills + ensure_tool_mastery)
│   └── tool_mastery_manager/          ← this subsystem
│       ├── __init__.py
│       ├── models.py                  ← CoverageStatus, ToolRef, EnsureResult
│       ├── paths.py                   ← EOS_ROOT + all filesystem paths
│       ├── discovery.py               ← 4 discovery sources
│       ├── coverage.py                ← unified evaluator
│       ├── ensure.py                  ← ensure_mastery flow
│       ├── backlog.py                 ← backlog + bootstrap
│       └── maintenance.py             ← refresh-stale / repair-invalid / audit-all
├── scripts/
│   ├── tool_mastery_manager.py                  ← CLI
│   └── tool_mastery_research_dispatcher.py      ← queued-action target
├── config/
│   └── tool_mastery_seeds.yaml                  ← portable seed list
└── logs/
    └── tool_mastery_manager/                    ← backlog + bootstrap artifacts
```

Everything else (verification, staleness, Neon sync, graph) remains in
`scripts/_tme_common.py` and the existing TME utilities. The Manager
**imports** those utilities; it does not re-implement them.

---

## 2. Relationship to the Tool Mastery Engine

| Concern | Lives in | Owned by |
|---|---|---|
| Skill layout + frontmatter schema | `scripts/_tme_common.py` | TME |
| Skill verification (9 checks) | `scripts/verify_tool_skill.py` | TME |
| Staleness windows + assessment | `scripts/check_skill_staleness.py` | TME |
| Neon sync | `scripts/sync_skills_to_neon.py` | TME |
| Dependency graph | `scripts/build_skill_graph.py` | TME |
| Authoring decision tree | `skills/meta/tool_mastery_engine/SKILL.md` | TME |
| Template scaffold | `skills/meta/tool_mastery_engine/scripts/scaffold_tool_skill.py` | TME |
| **Tool discovery (env scan)** | `core/tool_mastery_manager/discovery.py` | TMM |
| **Unified coverage classification** | `core/tool_mastery_manager/coverage.py` | TMM |
| **Ensure-mastery flow** | `core/tool_mastery_manager/ensure.py` | TMM |
| **Backlog / bootstrap** | `core/tool_mastery_manager/backlog.py` | TMM |
| **Maintenance loops** | `core/tool_mastery_manager/maintenance.py` | TMM |
| **Control Plane bridge** | `core/action_system/tme.py` | TMM + CP |

Rule of thumb: if you are reading or validating *a* skill, you are in
TME. If you are deciding *which* skills need to exist or what to *do*
about them, you are in TMM.

---

## 3. Relationship to the Control Plane and Orchestrator

The Manager never invents new action types. Every queued work item is
a standard Control Plane `run_script` action targeting the research
dispatcher. Concretely:

- **Type**: `run_script` (one of the four `ALLOWED_ACTION_TYPES`)
- **Risk**: `medium` — medium-risk without explicit approval gets
  auto-deferred by `core/action_system/validator.py` and persisted to
  `/opt/OS/logs/deferred/`. *That deferred queue is the Manager's
  backlog.* Nothing else needed to exist.
- **Idempotency key**: `tool_mastery:{work_type}:{slug}` with a 7-day
  TTL. Re-running `ensure` on the same tool while an action is
  in-flight or already deferred returns `skipped_duplicate`.
- **Semantic payload**: the `inputs` dict carries `work_type` and
  `tool` alongside the standard `path` + `args`, so future dispatchers
  (or `resume_action`) can introspect without parsing CLI args.
- **Execution surface**: when an operator runs
  `resume_action(action_id)`, the Control Plane invokes
  `python3 scripts/tool_mastery_research_dispatcher.py --work-type …
  --tool …`, which prints a structured next-steps plan. It does not
  auto-author research.

The orchestrator integration is implicit: the deferred queue is the
same queue the orchestrator already drains, so no orchestrator wiring
was added in this phase. Surfacing TMM work in morning briefs or
nightly maintenance is a follow-up concern.

---

## 4. Discovery model

Four deterministic sources, merged by slug:

| # | Source | Notes |
|---|---|---|
| (i) | `skills/tools/` existing slugs | every directory with a SKILL.md |
| (ii) | explicit caller / CLI arg | `ensure <tool>` |
| (iii) | `config/tool_mastery_seeds.yaml` | portable, human-declared intent |
| (iv) | `~/.claude.json` `mcpServers` (top-level + per-project) | real env scan |

Every discovered tool is normalised to snake_case via
`discovery.normalise_slug`. Duplicates across sources are merged into a
single `ToolRef` with the `sources` list unioned — so a tool that
appears in both `skills_dir` and `seed_list` is reported with both
provenance tags and never double-counted.

**Deliberately not implemented in v1:**
- Python import scanning across `eos_ai/` — noisy, EOS-coupled.
- Prose-based inference from arbitrary files — unexplainable.

Adding a new discovery source means: add a function to `discovery.py`,
append its return value to `discover_all()`, and add a `DiscoverySource`
enum entry. That is the entire extension surface.

---

## 5. Coverage model

`coverage.evaluate_coverage(slug)` collapses the output of three
existing TME internals into one of five statuses:

| Status | Meaning |
|---|---|
| `READY` | Skill exists, verifier passes, staleness = fresh |
| `MISSING` | No `SKILL.md` under `skills/tools/<slug>/` |
| `INVALID` | Exists but verifier has hard failures |
| `STALE` | Exists, verifier passes, staleness = stale or missing_date |
| `PARTIAL` | Exists, verifier passes but has warnings or staleness = near_stale |

Severity (most severe first): `MISSING > INVALID > STALE > PARTIAL > READY`.

The evaluator imports `_check` from `verify_tool_skill` and `_assess`
from `check_skill_staleness` directly — the same internal entrypoints
`scripts/query_skills.py` uses. No verification rule is redefined in
the Manager.

---

## 6. Ensure-mastery flow

`ensure.ensure_mastery(slug, *, auto_scaffold=True, dry_run=False)` is
the primary entry point. For a given tool:

1. Evaluate coverage.
2. If `READY` → return immediately, no side effects.
3. If `MISSING` and `auto_scaffold=True` → shell out to
   `scaffold_tool_skill.py` to create the skeleton files. Re-evaluate;
   the scaffolded skill will land in `INVALID` (the template
   intentionally fails the verifier until filled). Queue a `research`
   action regardless, because the *semantic* work is still "research a
   brand-new tool", not "repair a broken skill".
4. If `STALE` → queue a `refresh` action.
5. If `INVALID` or `PARTIAL` → queue a `repair` action.
6. Return an `EnsureResult` containing initial status, final status,
   whether scaffolding ran, the Control Plane action id, and the plan.

All queueing goes through `core.action_system.control_plane.run_action`
with `risk_level="medium"` and an idempotency key. Nothing bypasses
governance.

---

## 7. Backlog and bootstrap

- `backlog.build_backlog()` — run discovery + coverage, return all
  non-`READY` tools sorted by severity.
- `backlog.backlog_report()` — same plus a persisted markdown + JSON
  artifact under `/opt/OS/logs/tool_mastery_manager/backlog-<ts>.{md,json}`.
- `backlog.bootstrap()` — run backlog then call `ensure_mastery` on
  every non-`READY` entry. Writes a bootstrap artifact capturing every
  ensure result. Intended for the fresh-install path.

Both commands accept `dry_run=True` (where applicable) so an installer
can preview what would be scaffolded and queued before committing.

---

## 8. Maintenance

`maintenance.py` provides three thin compositions:

- `refresh_stale()` — iterate `STALE` tools, call `ensure_mastery` on each.
- `repair_invalid()` — iterate `INVALID` + `PARTIAL` tools, call
  `ensure_mastery` on each.
- `audit_all()` — return the full coverage snapshot including `READY`
  entries (for `scripts/tool_mastery_manager.py scan`).

These are the surfaces to wire into cron or the orchestrator when the
TMM graduates from manual use to scheduled use.

---

## 9. Portability assumptions

- The Manager reads `EOS_ROOT` from the environment (default: `/opt/OS`)
  via `core/tool_mastery_manager/paths.py`. All filesystem paths inside
  the Manager derive from this.
- `CLAUDE_JSON` env var can override the default `~/.claude.json`
  discovery path for test or multi-profile setups.
- The scaffold script and research dispatcher still hardcode
  `/opt/OS` — they predate this build and touching them is a separate
  cleanup. A portable Manager install that points `EOS_ROOT` at another
  checkout will work for discovery, coverage, backlog, and dry-run
  ensure; full scaffold + queue requires adjusting those two scripts.
- `config/tool_mastery_seeds.yaml` is the primary portability lever:
  different deployments declare different seed tools without touching
  code.
- Degrading sources: if `~/.claude.json` is missing, discovery silently
  skips source (iv); if the seed list is missing, it silently skips
  source (iii). A fresh install with neither falls back to whatever is
  already in `skills/tools/` plus explicit CLI input.

---

## 10. Current limitations

- **Research is still manual.** The Manager scaffolds and queues, but
  best_practices content is authored by a human (or a research-capable
  subagent) following the TME decision tree. Claiming otherwise would
  be dishonest.
- **Dispatcher is advisory.** `tool_mastery_research_dispatcher.py`
  prints a plan; it does not execute research. When a resume path
  that invokes a research subagent becomes available, the dispatcher
  is the single place to wire it in.
- **MCP discovery is Claude Code-specific.** Hosts without
  `~/.claude.json` get no source (iv). Other agent hosts would need
  their own discovery adapter.
- **Orchestrator wiring not yet in place.** The Manager writes to the
  same deferred queue the orchestrator drains, but nothing
  automatically surfaces TMM items in the morning brief or nightly
  maintenance. Wiring is a follow-up.
- **PARTIAL and INVALID share the same work_type (`repair`).** In
  practice PARTIAL = warnings + near-stale while INVALID = hard
  verifier failures. A future split could route PARTIAL through a
  lighter-touch refresh path.

---

## CLI cheatsheet

```bash
# One tool
python3 scripts/tool_mastery_manager.py status notion
python3 scripts/tool_mastery_manager.py ensure slack

# Everything
python3 scripts/tool_mastery_manager.py scan
python3 scripts/tool_mastery_manager.py backlog
python3 scripts/tool_mastery_manager.py bootstrap --dry-run

# Maintenance
python3 scripts/tool_mastery_manager.py refresh-stale --dry-run

# JSON output on any command
python3 scripts/tool_mastery_manager.py scan --json | jq .counts
```

And from Python, inside EOS:

```python
from core.action_system.tme import ensure_tool_mastery
ensure_tool_mastery("slack")          # real ensure via Control Plane
ensure_tool_mastery("slack", dry_run=True)
```
