# Handoff — 2026-05-21 Layer 3 Phase 3 Slice B Closure

## Status: COMPLETE

Follows: `2026-05-21_1929_layer3-phase3-slice-a-closure.md`
Spec: `2026-05-21_layer3-phase3-slice-b-spec.md` (797 lines, commit `517b9c39`)

Phase 3 Slice B: LLM capability extraction populates catalogs via
`call_with_fallback(TaskType.ANALYSIS)` over TME research artifacts.

## What Changed

**Branch commit**: `f9427588` on `layer3-phase3-slice-b-llm-extraction-wt`
**Merge commit**: `51551ada` on `main` (--no-ff)
**Push**: NOT pushed (operator deferred)
**Scope**: 4 files changed, 1151 insertions, 10 deletions
**Test baseline**: 4291 → 4300 (9 new), zero collection errors

### Files edited

| File | Change |
|------|--------|
| `adapters/adapter_engine/capability_discovery.py` | Extended 81 → 375 lines: prompt template, 7 private methods, 5 constants, `discover()` flow extended |
| `tests/test_capability_extraction_slice_b.py` | New: 8 unit + 1 integration test |
| `tests/fixtures/capability_discovery/googledrive/artifact.json` | Sanitized ResearchArtifact (timestamps → placeholder, abs paths removed) |
| `tests/fixtures/capability_discovery/googledrive/raw_excerpt.txt` | 9,653-char WebFetch-derived API reference from REST v3 endpoint page |

### Files NOT touched (zero-touch claim)

| File | Verified by |
|------|-------------|
| `composition/mastery/research/source_discovery.py` | `git diff main..HEAD -- composition/mastery/` = empty |
| `composition/mastery/research/agent.py` | same |
| `composition/mastery/research/models.py` | same |
| All TME files | sovereignty-grep: 20 DATA hits, unchanged |

## Arc Summary

**Investigation → Spec → Execute with 2 wet retries.**

1. **Spec phase** (commit `64044269`): 797-line spec locked Q19-Q25.
   Q26-Q30 self-resolved during spec drafting — see deviations below.
2. **Execute phase, attempt 1**: research.agent.run fetched Google Drive
   landing page HTML. Classifier rejected it ("unrecognised content").
   artifact.extracted_patterns all empty. LLM extraction attempted over
   empty patterns + landing HTML → ProviderState blocked all providers
   except Ollama qwen2.5:0.5b (swap at 92%, CRITICAL threshold >80%).
3. **Resource pressure fix**: stopped os-bot + os-operator + os-webhook,
   flushed swap (`swapoff -a && swapon -a`), swap dropped to 0%.
4. **Execute phase, attempt 2**: WebFetch used to retrieve actual REST API
   reference (`/drive/api/reference/rest/v3`). cc_sdk/claude-opus-4-6
   extracted 46 capabilities, 0 drops, all sanity verbs present
   (LIST/GET/CREATE). Operator approved.
5. **Fixture + commit**: sanitized artifact + WebFetch raw excerpt committed,
   integration test regex fixed, 8/8 unit tests pass, merged to main.

## First-Extraction Proof Point

| Metric | Value |
|--------|-------|
| Provider | cc_sdk / claude-opus-4-6 |
| Capabilities extracted | 46 |
| Dropped | 0 |
| Sanity verbs | LIST_FILES, GET_FILE, CREATE_FILE all present |
| Cap_id regex pass rate | 46/46 |
| Confidence range | 0.3–1.0 (evidence-driven heuristic) |
| Raw input | 9,653 chars (WebFetch API reference) + empty extracted_patterns |

## Spec Deviations

### Self-resolved during spec (Q26–Q30)

| ID | Question | Resolution |
|----|----------|------------|
| Q26 | Should extraction prompt include adapter_id or adapter_type? | Both — adapter_id for traceability, adapter_type for cap_id prefix pattern |
| Q27 | Markdown fence stripping needed? | Yes — decomposer precedent (`orchestrator.py:520`) strips fences, LLMs wrap JSON in fences unpredictably |
| Q28 | How many retry attempts? | 2 (matching decomposer pattern), not configurable this slice |
| Q29 | Should research agent failures produce empty catalog or error? | Empty catalog with error note in `source_plan_notes` — catalog always written |
| Q30 | Where to import model_router? | Lazy import inside `_extract_capabilities()` to avoid circular deps at module level |

### Reconciled during execute

| Deviation | Detail |
|-----------|--------|
| `_CAP_ID_RE` underscore broadening | Spec Q20 locked `^[a-z][a-z0-9-]+$`. Prompt examples used `google_drive-list-files` (underscore in adapter_type prefix). Code broadened to `^[a-z][a-z0-9_-]+$`. Test `cap_id_re` mirrored. |
| Raw excerpt 12K → ~9.7K | Spec §10 set 12K char cap. Actual WebFetch output was 9,653 chars — under cap, no truncation triggered. Cap remains at 12K for future adapters. |
| Branch `-wt` suffix | Worktree created branch `layer3-phase3-slice-b-llm-extraction-wt` (git appends `-wt` for worktree branches). Spec named `layer3-phase3-slice-b-llm-extraction`. Merge commit references the `-wt` branch. |
| Worktree not renamed pre-merge | Worktree rename requires CWD outside the worktree. Renamed post-merge to `worktree-layer3-phase3-slice-b-llm-extraction-wt`. |
| Raw excerpt is WebFetch-derived, not research agent output | Research agent fetched landing page HTML (classifier rejected). Raw excerpt for fixture and extraction sourced via direct WebFetch of REST API reference. Commit message documents this. |

## New Retro Candidates

| # | Candidate | Source |
|---|-----------|--------|
| 20 | First-extraction proof point: 46 capabilities with 0 drops on first approved attempt validates Option D input design (patterns + raw). Standing-on-shoulders pattern works. | Slice B execute (`f9427588`) |
| 21 | Resource pressure blindsides routing: swap at 92% pushed ProviderState to CRITICAL, routing to Ollama qwen2.5:0.5b which is too small for extraction. No warning before the call — discovered only after empty/bad output. Need pressure check before expensive LLM operations. | Slice B execute, attempt 1 |
| 22 | Research agent landing page problem: TME classifier correctly rejected the landing page HTML (no API markers), but the orchestrator silently fell through to empty patterns. The failure mode is correct (empty catalog) but invisible — no signal that the research agent found nothing useful vs found nothing at all. | Slice B execute, attempt 1 |
| 23 | WebFetch as research escape hatch: when research.agent.run produces low-quality output, manual WebFetch to a known API reference page produced far superior input. This suggests a "known good URL" registry for adapters beyond just `vendor_docs_url`. | Slice B execute, attempt 2 |
| 24 | Cap_id regex spec-vs-code inconsistency: spec Q20 said `^[a-z][a-z0-9-]+$` but prompt examples included underscores. Spec should have caught this — prompt examples ARE the spec for LLM-generated fields. | Slice B execute (`f9427588`) |
| 25 | Integration test false-positive risk: test calls `_extract_capabilities` directly, bypassing research agent. Proves LLM extraction + validation but not the full `discover()` pipeline. True E2E test deferred to operational testing phase. | Slice B execute (`f9427588`) |

## Deferred Queue (unchanged from Slice A)

- Discord command identifiers (`!buyback`, `!drip`, `!perfectweek`) — UX decision
- Snapshot-graph tarball script (low priority)
- Frozen pre-3.1 audit docs with stale `martell_patterns.py` references (small/medium scope)
- Flaky `test_completes_full_cycle` — Gemini 429 rate-limit failure

## Next Phase 3 Prong

Two candidates — operator picks:

1. **API introspection** (Slice C): live `discover()` call that runs
   research + extraction end-to-end without manual WebFetch. Requires
   fixing the research agent's landing-page-only fetch problem or adding
   a known-good-URL fallback. Proves the full pipeline, not just extraction.

2. **Operational testing** (Slice C-alt): run the full suite against
   a second adapter (e.g., Slack, GitHub) to validate generalization.
   Proves the prompt + validation isn't Google-Drive-specific.

## Verification Summary

| Check | Result |
|-------|--------|
| py_compile | Both files clean |
| ruff format | 0 reformatted |
| Unit tests | 8/8 pass |
| Integration | 1 collected (skips without LLM, runs with fixture present) |
| Collection | 4300 tests, 0 errors |
| Sovereignty | 20 DATA hits |
| TME zero-touch | 0 files changed in `composition/mastery/` |
| First extraction | 46 caps, 0 drops, operator-approved |

## Worktree

| Item | Value |
|------|-------|
| Path | `/opt/OS/.claude/worktrees/worktree-layer3-phase3-slice-b-llm-extraction-wt` |
| Branch | `layer3-phase3-slice-b-llm-extraction-wt` |
| Status | Merged, archived |
