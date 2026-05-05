# End-to-End Tool Mastery Validation — 2026-04-08

Real-world run of the governed Tool Mastery pipeline
(detect -> classify -> queue -> research -> queue -> author -> verify)
against 3 intentionally-different tools. No new architecture built.
Everything was routed through the existing dispatcher + Control Plane.

## 1. Executive Summary

- All 91 tools currently classify READY; backlog size = 0. To exercise
  the pipeline I forced `--work-type refresh` runs.
- **notion** — full happy path. Discovery found 2 registry URLs,
  fetcher pulled 758KB of real HTML, Research Agent queued author
  action through the CP, drainer executed it via `resume_action`,
  Author Agent returned `authored_ready` in preserve-mode (existing
  human skill was respected, 19 sections preserved), verifier PASS.
- **higgsfield** — `status=no_sources`. Not in `tool_doc_registry.md`
  and not present as an MCP server in `~/.claude.json`. Author action
  correctly NOT queued (handoff.queued=false). Honest no-op.
- **clo3d** — identical failure mode to higgsfield. No registry row,
  no MCP entry. Honest `no_sources`.
- **Single highest-leverage bottleneck: source discovery.** Discovery
  is registry-only + MCP-only. Any tool not in
  `skills/meta/tool_mastery_engine/references/tool_doc_registry.md` or
  `~/.claude.json` produces `NO_SOURCES` regardless of whether rich
  public docs exist. This is the wall 2 of 3 cases hit.

## 2. Case selection

Backlog was empty (everything READY, verifier clean, fresh). To get a
real trace I picked 3 refreshable tools representing the three
difficulty bands the mission asked for.

| tool | difficulty band | why picked |
| --- | --- | --- |
| notion | strong-source | Real official developer docs at developers.notion.com; already in `tool_doc_registry.md` row 13; deep API surface; tests the happy path end-to-end including the new loop closure. |
| higgsfield | partial-source | AI video tool, sparse and marketing-heavy docs, no dev portal. Expected to stress source discovery. Existing skill is 15KB so preservation behaviour is also testable. |
| clo3d | hard / uncertain | 3D fashion software, human-in-the-loop speed_category, mostly vendor marketing + PDFs, no structured docs. Expected to hit discovery wall hardest. |

Stitch (yesterday's test) was deliberately skipped: within the 24h
`tool_mastery:author:<slug>` idempotency TTL it would return
`skipped_duplicate` instead of exercising the path.

## 3. Baseline state

| tool | skill path | skill mtime | manager status | existing research | backlog |
| --- | --- | --- | --- | --- | --- |
| notion | `/opt/OS/skills/tools/notion/SKILL.md` (8175B) | 2026-04-08 16:25 | READY, age_days=0 | 2 runs earlier today (23-25Z, 23-28Z, both status=ok, pre-loop-closure) | empty |
| higgsfield | `/opt/OS/skills/tools/higgsfield/SKILL.md` (15195B) | 2026-04-06 22:45 | READY, age_days=2 | none | empty |
| clo3d | `/opt/OS/skills/tools/clo3d/SKILL.md` (11298B) | 2026-04-06 22:23 | READY, age_days=2 | none | empty |

Verifier PASS for all 3 pre-run.

## 4. End-to-end run trace

All runs invoked with:

```
python3 /opt/OS/scripts/tool_mastery_research_dispatcher.py \
    --work-type refresh --tool <slug> --execute --json
```

### 4a. notion

- `run_dir` = `/opt/OS/logs/tool_mastery_research/notion/2026-04-09T02-04-27Z`
- `artifact_path` = `.../research_artifact.json`
- Plan size 2, fetched 2, fetched_ok 2, status `ok`.
- Real HTTP fetches:
  - `https://developers.notion.com/` → 200, 311,848 bytes, raw saved
  - `https://developers.notion.com/reference` → 200, 446,060 bytes, raw saved
- `manifest.author_handoff`:
  `{queued: true, action_id: c38745e1-3571-4b59-8185-6e7d4c0bcb7c, action_status: validated}`
- Drain:

  ```
  python3 /opt/OS/scripts/tool_mastery_research_dispatcher.py \
      --execute-author --tool notion
  ```

  Output: deferred scanned=3, author matches=1, status=executed,
  result_ok=True.

- CP execution log (`/opt/OS/logs/execution/2026-04-09-execution.jsonl`)
  shows the full proposed → validated → approved → executed transition
  with `result.ok=true, returncode=0`.
- Author result JSON:

  ```json
  {"status": "authored_ready",
   "sections_sourced": 0,
   "sections_placeholder": 0,
   "sections_preserved": 19,
   "verifier_passed": true,
   "notes": ["existing skill appears human-authored; refusing to overwrite without force_rewrite=True"]}
  ```

- Post-run verifier: PASS. Post-run manager status: READY, last_researched 2026-04-09.
- Existing `SKILL.md` + `references/best_practices.md` left UNTOUCHED
  (mtimes unchanged). Preserve mode honoured.

### 4b. higgsfield

- `run_dir` = `/opt/OS/logs/tool_mastery_research/higgsfield/2026-04-09T02-04-28Z`
- Plan size 0, fetched 0, fetched_ok 0, status `no_sources`.
- `manifest.author_handoff = {queued: false}` — correct; loop gate is
  `status != NO_SOURCES`.
- Nothing queued. Nothing drained. Skill untouched. Verifier still PASS.
- `next_steps`: "Add a tool_doc_registry.md entry or re-run with --official-url".

### 4c. clo3d

- `run_dir` = `/opt/OS/logs/tool_mastery_research/clo3d/2026-04-09T02-04-28Z`
- Identical shape: plan 0, fetched 0, status `no_sources`, no handoff queued.
- Existing skill untouched. Verifier PASS.

## 5. Final outcome

| tool | baseline | research | author | verifier | final |
| --- | --- | --- | --- | --- | --- |
| notion | READY | ok, 2 fetched, 758KB real HTML | authored_ready, preserve-mode, 19 preserved | PASS | READY (fresh 2026-04-09) |
| higgsfield | READY | no_sources | not queued (correct) | PASS | READY (unchanged) |
| clo3d | READY | no_sources | not queued (correct) | PASS | READY (unchanged) |

## 6. Failure-mode analysis

### higgsfield + clo3d — NO_SOURCES
Root cause: `core/tool_mastery_research_agent/source_discovery.py`
`discover_sources()` looks at exactly three inputs:

1. explicit `--official-url` / hints (none provided)
2. `skills/meta/tool_mastery_engine/references/tool_doc_registry.md` row match
3. `~/.claude.json` mcpServers block

That is the entire discovery surface. There is no web search, no
search engine fallback, no guessing from slug, no probe of
`https://<slug>.com/docs`, no heuristic. Comment in the module is
explicit: *"Derived guesses are NOT fabricated."*

- **clo3d**: no registry row, no MCP entry. **Correct behaviour given
  the current contract, but it is a practical bottleneck** — clo3d
  does in fact have public docs (support.clo3d.com, manual.clo3d.com)
  the registry just doesn't know about them. Classification:
  **discovery weakness, not a bug in the agent, but a bug in the
  system's reach**.
- **higgsfield**: same story. Real public marketing/help docs exist;
  the registry has no row; discovery returns empty. Same classification.

### notion — authored_ready (preserve mode)
Not a failure, but worth flagging: `sections_sourced=0,
sections_placeholder=0, sections_preserved=19`. The Author Agent did
NOT use any of the 758KB of freshly-fetched notion docs because the
existing skill is human-authored. The whole research fetch was
effectively thrown away at author time. This is **correct preserve-mode
behaviour** (never clobber a human file without `force_rewrite`), but
it means the refresh path on already-populated tools is currently a
verify-only loop, not a content-update loop. Classification: **correct
behaviour, but the operator value of the refresh is near zero on
human-authored skills**.

## 7. Honesty boundary audit

- **Fabrication:** none. Every fetched URL is from `tool_doc_registry.md`
  row 13. Raw HTML captures exist on disk and match the HTTP responses.
- **Overclaim readiness:** none. NO_SOURCES cases did not queue author,
  did not modify skills, did not bump last_researched. notion only
  reached `authored_ready` because verifier genuinely passed.
- **Uncertainty preservation:** yes. NO_SOURCES runs wrote explicit
  `next_steps` pointing at the registry gap.
- **Human-authored preservation:** confirmed. notion SKILL.md mtime and
  byte count unchanged after authoring. Author explicitly logged
  "refusing to overwrite without force_rewrite=True".
- **Partial/blocked marking:** handled — NO_SOURCES is a first-class
  terminal state, not silently coerced to `ok`.

Grade: honest.

## 8. Operator experience

From the CLI alone:

- **Understandable?** Mostly. JSON envelopes are clean, statuses are
  named sensibly (`ok`, `no_sources`, `authored_ready`).
- **Queueing behaviour clear?** Partially. The research dispatcher run
  doesn't echo back the fact that an author action was queued — you
  only learn the action_id by reading the manifest.json. An operator
  reading only stdout would not know an action was queued.
- **Logs traceable?** Yes. Every run has a dated `run_dir`,
  `manifest.json`, `raw/`, `research_artifact.json`, `summary.md`,
  `sources.md`. CP runs also land in
  `/opt/OS/logs/execution/<date>-execution.jsonl`. Grep by `action_id`
  works.
- **Final state obvious?** Yes for notion (drainer prints
  `status=executed, result_ok=True`). For higgsfield/clo3d there is
  no follow-up step — the operator is told "Add a tool_doc_registry.md
  entry or re-run with --official-url" and has to act manually.
- **Would they know what to do next?** For NO_SOURCES: yes, the hint
  is clear. For a *successful* research run, they might not realise
  they need to run `--execute-author` as a separate drain step. The
  two-drain model is intentional but not signposted in the first run's
  stdout.

## 9. Single highest-leverage next bottleneck

**Source discovery coverage.**

Evidence:
- 2 of 3 cases (66%) hit `NO_SOURCES`, not for any agent/fetch/author
  reason but purely because the tool slug isn't in a hand-maintained
  markdown table.
- The fetcher works (notion proved it: 758KB real HTTP 200s).
- The Author Agent works (notion proved it: authored_ready, verifier
  PASS, preserve mode correct).
- The loop closure works (notion proved it: research ->
  auto-queued author action -> drained via Control Plane ->
  `resume_action` -> `run_script` executor -> author CLI -> PASS).
- The one piece that did not work was `discover_sources()` for any tool
  not pre-registered. Discovery is the hard wall.

This is also the cheapest fix: either (a) expand
`tool_doc_registry.md` systematically, or (b) add a Tier-3 fallback
that searches for `site:<slug>.com docs` / queries an approved search
API and requires human approval before adopting results. Option (b)
preserves the "no fabrication" contract because discovered URLs would
still need to be fetchable + tier-classified before use.

## 10. Recommended next move

1. Add a third discovery source — **search-engine-backed
   candidate generation** — gated behind a CP `call_api` action so the
   operator approves the candidate URL list before the fetcher is told
   to pull them. Keep the honesty contract: candidates are proposals,
   not sources, until explicitly approved.
2. As a near-term unblock, manually add `higgsfield` and `clo3d` rows
   to `tool_doc_registry.md` so those specific tools are unblocked
   immediately.
3. Signpost the two-drain model: after a successful `--execute` run
   that queues an author action, the dispatcher should print the
   action_id and the exact `--execute-author` command to run next.
4. Decide policy on refresh-over-human-authored: currently it is a
   no-op. Either document that explicitly or add a `--propose-diff`
   mode that writes a candidate SKILL.md alongside the existing one
   for human review.

---

Artifacts referenced:
- `/opt/OS/logs/tool_mastery_research/notion/2026-04-09T02-04-27Z/`
- `/opt/OS/logs/tool_mastery_research/higgsfield/2026-04-09T02-04-28Z/`
- `/opt/OS/logs/tool_mastery_research/clo3d/2026-04-09T02-04-28Z/`
- `/opt/OS/logs/execution/2026-04-09-execution.jsonl`
  (action `c38745e1-3571-4b59-8185-6e7d4c0bcb7c`)
- `/opt/OS/core/tool_mastery_research_agent/source_discovery.py`
- `/opt/OS/skills/meta/tool_mastery_engine/references/tool_doc_registry.md`
