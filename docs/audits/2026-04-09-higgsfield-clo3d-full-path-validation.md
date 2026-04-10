# Tool Mastery Full-Path Validation — higgsfield + clo3d

**Date:** 2026-04-09
**Scope:** End-to-end validation of the governed Tool Mastery pipeline
(detect → classify → queue → generate candidates → approve → research →
author → verify) against the two tools that were previously blocked at
source discovery (`NO_SOURCES`, see `2026-04-08-end-to-end-tool-mastery-validation.md`).
No new architecture. Only existing governed entry points used.

---

## 1. Executive Summary

- Both tools progressed all the way through author + verify. Verifier
  PASS for both. Control Plane full audit trail present.
- The previously-reported `NO_SOURCES` wall is unblocked: deterministic
  candidate generation (`core/tool_mastery_research_agent/search_discovery.py`)
  + file-based operator approval (`candidate_approval.py`) now yields
  real fetchable URLs. higgsfield: 2/2 fetched_ok. clo3d: 4/11 fetched_ok.
- **Author output quality is the real problem.** Both runs produced
  provenance files where "sourced" sections are effectively fabricated-by-
  matching: keywords hit on JavaScript bundler flag noise, Clerk SDK JSON,
  and GitHub `copilot_*` feature-flag strings in the HTML of a landing
  page / search results page. No actual product documentation was
  captured because neither tool has fetchable text docs at the URLs that
  got approved (higgsfield.ai is an SPA marketing site; clo3d.com is a
  marketing site, docs.clo3d.com / api paths 404, real docs live at
  `support.clo3d.com` and `manual.clo3d.com` which aren't in any family).
- **Honesty boundary held by preserve-mode, not by the author agent.**
  Both SKILL.md + best_practices.md files on disk were NOT modified
  (mtimes / sizes confirm). The Author Agent detected human-authored
  skills and refused to overwrite. This is what caused verifier PASS.
  If the skills had been scaffold-state, the author agent would have
  written the garbage excerpts straight into `best_practices.md` and
  verifier would still have passed — the verifier has no semantic check
  on excerpt relevance.
- **Dominant bottleneck is now authoring precision**, specifically the
  raw→excerpt pipeline: HTML/SPA shell capture + naïve keyword scan
  produces high false-positive excerpts with zero semantic grounding.
- **Single next build recommended:** pre-author raw-capture filter
  (strip SPA shells, script/JSON blobs, feature-flag noise; require
  minimum prose ratio) + keyword hits must land inside the filtered
  prose, not inside script/JSON bodies. This is a bounded change inside
  `core/tool_mastery_author_agent/{loader,mapping,draft}.py` plus
  minor updates to `artifact.py` / fetcher stripping.

---

## 2. Per-tool summary table

| tool | baseline skill | research result | author result | verifier | final state | real quality |
| --- | --- | --- | --- | --- | --- | --- |
| higgsfield | SKILL.md 15194B (Apr 8 19:36), bp.md 40601B (Apr 8 15:51), verifier PASS | status=ok, plan=2, fetched_ok=2, raw ~2MB (higgsfield.ai SPA 1.7MB + github search 260KB) | authored_ready, preserve-mode (human-authored detected), 19 preserved, SKILL.md + bp.md UNCHANGED on disk | PASS | READY | garbage-grade provenance (excerpts are JS bundler / Clerk SDK / copilot feature flags) — but skill file preserved so on-disk quality unchanged |
| clo3d | SKILL.md 11293B (Apr 8 19:37), bp.md 39691B (Apr 6 22:31), verifier PASS | status=partial, plan=11, fetched_ok=4 (clo3d.com 2.4KB, www.clo3d.com/docs 2.4KB, github search 250KB, pypi 3KB) | authored_ready, preserve-mode, 19 preserved, SKILL.md + bp.md UNCHANGED on disk | PASS | READY | garbage-grade provenance (excerpts from github copilot feature flags + pypi metadata) — skill file preserved so on-disk quality unchanged |

---

## 3. Baseline — higgsfield

- Skill present: `/opt/OS/skills/tools/higgsfield/SKILL.md` (15194B,
  2026-04-08 19:36) + `references/best_practices.md` (40601B,
  2026-04-08 15:51).
- Verifier PASS (no failures, no warnings).
- Coverage state: READY (prior full-path audit on 2026-04-08 already
  bumped `last_researched`). Age ~0 days at time of baseline.
- Prior research runs on disk:
  `logs/tool_mastery_research/higgsfield/2026-04-09T02-04-28Z`
  (the old `no_sources` run) and `2026-04-09T02-36-56Z` (the new
  candidate-approval run executed before this audit started).
- Candidates file present:
  `logs/tool_mastery_research/higgsfield/candidates/2026-04-09T02-36-44Z.json`
  — 11 candidates across 6 families; **2 accepted** (`higgsfield.ai`,
  `github.com/search?q=higgsfield&type=repositories`), 9 pending.
- Pre-queued author action:
  `logs/deferred/81ffb9b1-8554-4339-b36f-49902100b5f1.json` —
  `tool_mastery:author:higgsfield`, risk medium, status validated.

## 4. Baseline — clo3d

- Skill present: `/opt/OS/skills/tools/clo3d/SKILL.md` (11293B,
  2026-04-08 19:37) + `references/best_practices.md` (39691B,
  2026-04-06 22:31).
- Verifier PASS (no failures, no warnings).
- Coverage state: READY.
- Research runs on disk: `2026-04-09T02-04-28Z` (old `no_sources`) +
  `2026-04-09T02-37-02Z` (new candidate-approval run).
- Candidates file:
  `logs/tool_mastery_research/clo3d/candidates/2026-04-09T02-37-02Z.json`
  — 11 candidates; **all 11 accepted**.
- Pre-queued author action:
  `logs/deferred/84ee756a-aea3-4be0-ab06-e2422474fc4e.json` —
  `tool_mastery:author:clo3d`, risk medium, status validated.

---

## 5. End-to-end trace — higgsfield

1. **Candidate generation (pre-existing)** — CP `write_file` action at
   `2026-04-09T02:36:44Z` persisted 11 candidates across 6 families.
   Audit row in `/opt/OS/logs/execution/2026-04-09-execution.jsonl`.
2. **Operator approval (pre-existing)** — 2 candidates accepted:
   `https://higgsfield.ai` (vendor_domain) and GitHub search.
3. **Research run (pre-existing)** — `2026-04-09T02-36-56Z`:
   - plan_size=2, fetched=2, fetched_ok=2, status=`ok`.
   - `raw/01_higgsfield.ai_root.txt` = 1,753,770 bytes (SPA shell with
     inlined Next.js flight data + Clerk SDK bootstrap JSON).
   - `raw/02_github.com_search.txt` = 259,910 bytes (search results
     JSON + copilot_* feature-flag strings).
   - `author_handoff.queued=true`, action id
     `81ffb9b1-8554-4339-b36f-49902100b5f1`, status `validated`.
4. **Author drain (executed in this audit):**
   ```
   $ python3 scripts/tool_mastery_research_dispatcher.py \
       --execute-author --tool higgsfield
   deferred actions scanned: 4
   author actions matched : 1
     action_id : 81ffb9b1-8554-4339-b36f-49902100b5f1
     status    : executed
     result_ok : True
   ```
   - CP lifecycle proposed → validated → approved → executed via
     `run_script` executor → `scripts/tool_mastery_author.py`.
5. **Author result:** `authored_ready`. Provenance sidecar written at
   `logs/tool_mastery_research/higgsfield/2026-04-09T02-36-56Z/authored_provenance.json`.
6. **On-disk state:** SKILL.md mtime unchanged (19:36 Apr 8, 15194B).
   best_practices.md unchanged (15:51 Apr 8, 40601B). Preserve-mode
   held — author agent detected fewer than 5 `[To be filled` markers
   and refused to overwrite.
7. **Verifier post-author:** PASS.

No bypass. No architecture modified. Governed path walked end-to-end.

## 6. End-to-end trace — clo3d

1. **Candidate generation** — CP `write_file` at `2026-04-09T02:37:02Z`,
   11 candidates. Logged.
2. **Approval** — all 11 accepted.
3. **Research run** — `2026-04-09T02-37-02Z`:
   - plan_size=11, fetched=11, fetched_ok=4, status=`partial`.
   - Fetch OK: `clo3d.com` (2403B marketing root), `www.clo3d.com/docs`
     (2403B — identical page, likely redirected to same marketing root),
     `github.com/search` (250,133B), `pypi.org/project/clo3d/` (3101B).
   - Fetch failed: `docs.clo3d.com`, `clo3d.io`, `clo3d.ai`,
     `docs.clo3d.com/api`, `docs.clo3d.com/reference`,
     `github.com/clo3d/clo3d`, `npmjs.com/package/clo3d` — all 404/NXDOMAIN.
   - `author_handoff.queued=true`, action id
     `84ee756a-aea3-4be0-ab06-e2422474fc4e`.
4. **Author drain (executed in this audit):**
   ```
   $ python3 scripts/tool_mastery_research_dispatcher.py \
       --execute-author --tool clo3d
   deferred actions scanned: 3
   author actions matched : 1
     status    : executed
     result_ok : True
   ```
5. **Author result:** `authored_ready`. Provenance sidecar written.
6. **On-disk state:** SKILL.md mtime 19:37 Apr 8, still 11293B
   (frontmatter was touched by the Research Agent's
   `apply_safe_metadata`; body unchanged). best_practices.md unchanged
   (22:31 Apr 6, 39691B). Preserve mode held.
7. **Verifier post-author:** PASS.

---

## 7. Authored output quality assessment

This is where the evaluation diverges from "verifier passed".

### 7.1 Where the excerpts actually came from

**higgsfield provenance — sampled sourced sections:**

- *Core Operations with Exact Signatures* (sourced=true, rationale
  "3 keyword hits across 2 sources"):
  Excerpt 1 quotes product marketing copy — `Glow Vintage Cannabis
  Bubbles Magazine Cold vision Modern LSD Broken mirror Lava Marble
  Ocean View all of Mixed Media Visual Effects...`. This is not API
  operations. Excerpt 2 quotes schema.org `SearchAction` JSON embedded
  in the landing page HTML. Excerpt 3 quotes GitHub `copilot_chat_*`
  feature-flag strings from the repo search page.
- *Rate Limits* (sourced=true, "2 keyword hits"):
  Excerpt 1 is the literal `static/chunks/...` JS asset URLs from
  Next.js. Excerpt 2 is `copilot_chat_reduce_quota_checks` — the word
  "quota" matched inside a GitHub feature-flag identifier.
- *Error Codes and Recovery* (sourced=true, "6 keyword hits"):
  Excerpts are `self.__next_f.push` React server component flight data
  and minified SVG `d=` paths. The numeric tokens 400/401/403/404/500
  matched inside JS bundle hashes like `4006`, `static/chunks/...`.
  None of these are actual error codes.
- *SDK Idioms* (sourced=true):
  Excerpt matches `Clerk` auth SDK metadata (`sdkMetadata` JSON) and
  the GitHub search result string `higgsfield-ai/higgsfield-client`
  with description "Python SDK for Higgsfield API". Only the last hit
  is semantically real; the first two are pure noise.

**clo3d provenance — sampled sourced sections:**

- *Pagination Patterns* (sourced=true): Excerpts are
  `copilot_spaces_pagination` feature-flag strings and "memex" feature
  flags. Zero actual pagination content.
- *Error Codes and Recovery* (sourced=true): Excerpts are GitHub repo
  list metadata (`"repo":{"repository":{"id":...}}`) and
  `mission_control_retry_on_401` feature-flag text. No real error
  codes from any clo3d documentation.
- *Webhooks and Events* (sourced=true): Excerpts are
  `actions_image_version_event` feature flag, Dismiss/refresh UI text,
  and `script.onerror = (event) => {...}` DOM handler code. No webhook
  content.

### 7.2 Verdict

**Quality:** effectively fabrication-by-matching. Every "sourced"
section in both runs is structural garbage. The keyword hits are real
(the bytes do contain `quota`, `retry`, `event`, `pagination`, `oauth`,
etc.) but they land inside JS bundle identifiers, feature-flag slugs,
SDK metadata JSON, and React flight data — none of which are operator-
actionable documentation.

- higgsfield: 0 sections are operator-useful. Sub-threshold "weak
  signal" reporting correctly demoted some sections to Uncovered
  (Authentication: `oauth` hit only inside Clerk metadata), which is
  the ONLY thing that saved a handful of sections from being promoted
  to the same garbage class as the sourced ones.
- clo3d: same story. Most sections stayed Uncovered due to the
  2-hit-minimum + small capture size (2.4KB marketing root, 3KB pypi
  page). The ones that did promote are all GitHub search noise.

**What actually saved the SKILL files from corruption:** the Author
Agent's `reconcile._looks_like_scaffold()` heuristic correctly
identified both skills as human-authored and refused to overwrite.
If either skill had been in scaffold state, the agent would have
written these garbage excerpts straight into `references/best_practices.md`
and the verifier would still have returned PASS (because the verifier
has no semantic check on excerpt content — it only checks structural
minimums).

This means: for **new** tools with no prior human skill, the current
pipeline would produce demonstrably misleading "creator-level mastery"
content. The honesty boundary is being held by an unrelated preserve-
mode check, not by any authoring-precision guard.

---

## 8. Honesty-boundary audit

| Question | Answer |
| --- | --- |
| Did the system invent sources? | No. Every URL is a generated candidate from an explicit pattern family, logged via CP, approved by operator. Provenance traceable. |
| Did the system fabricate skill content? | Not directly — every excerpt is a verbatim substring of a real raw capture on disk. BUT the *labelling* ("Status: Sourced", "Human review recommended") implies these excerpts are evidence for the section title, and they are not. This is semantic fabrication via mislabelling, not byte-level fabrication. |
| Did the system overstate readiness? | Yes, if you look at the provenance file in isolation: 6+ higgsfield sections are marked `sourced=true`. Readiness is only accurate because the SKILL file was preserved and the agent returned `authored_ready` for that reason, not for the excerpts. |
| Did the system keep uncovered areas explicit? | Partially. Sections below 2-hit threshold stayed Uncovered. Sections above threshold were promoted regardless of whether the hits were in prose or in JS. |
| Is provenance traceable? | Yes. Every draft lists `raw_paths` and `source_urls`. Every CP action in `/opt/OS/logs/execution/2026-04-09-execution.jsonl`. |
| Were human-authored files preserved? | Yes. Both SKILL.md and best_practices.md mtimes / sizes confirm zero body modification. |
| Is the audit reviewable? | Yes — `authored_provenance.json` per run is grep-able. |

**Grade:** honesty boundary held on-disk by preserve-mode, but
authoring-precision layer fails semantic honesty when the raw capture
is a SPA shell / search results page rather than real documentation.
A system-of-record reader looking only at provenance files would be
misled about which sections are actually sourced.

---

## 9. Dominant bottleneck

**Authoring precision — specifically, the raw-capture → excerpt
pipeline.**

Evidence ranked:

1. Source discovery is no longer the wall. 2/3 previously blocked
   cases now unblock with deterministic candidate generation + operator
   approval. higgsfield pulled 2MB of raw; clo3d pulled ~517KB.
2. The fetcher works.
3. The Control Plane + author loop closure works. Both drains succeeded
   via `resume_action` → `run_script` executor → author CLI. Full audit
   trail.
4. The verifier is structurally sound but semantically blind — it
   cannot distinguish "sourced from real docs" from "sourced from JS
   bundler flag noise".
5. The Author Agent's 2-hit keyword threshold is too weak a filter
   against modern SPA shells and search-result JSON. Every promoted
   section on both tools in this audit contains JS/JSON noise.
6. Preserve-mode is the only reason the on-disk skill files are not
   now polluted with those excerpts. That is load-bearing for safety,
   but it is accidental safety, not designed safety.

Not the bottleneck (yet):
- Source quality: yes, the candidate families generated lots of 404s
  for clo3d. But the real issue isn't the 404s — the 200s themselves
  were garbage-tier for authoring. Even perfect source discovery
  wouldn't rescue authoring precision.
- Operator UX: approval worked, drain signposting is still thin, but
  this is secondary.
- Verifier semantics: verifier is the *symptom* through which bad
  excerpts would leak if preserve-mode didn't catch them. Fixing
  authoring precision is cheaper and more precise than fixing the
  verifier to reason about prose quality.

---

## 10. Single recommended next build

**Pre-author raw-capture filter + hit-locality enforcement** inside
the Author Agent.

Concretely, one bounded change across three files:

1. `core/tool_mastery_author_agent/loader.py` — when loading a raw
   capture, produce BOTH the raw string and a **prose-only derivative**:
   - Strip `<script>…</script>` and `<style>…</style>` blocks.
   - Strip JSON-literal blobs (`{...}` clusters above a length
     threshold with `"key": "value"` density).
   - Strip Next.js / React flight data markers (`self.__next_f.push(...)`).
   - Strip URL-path-only lines (`static/chunks/...`, `dpl-...`).
   - Drop captures whose post-strip prose ratio is below a threshold
     (e.g. prose/raw < 5%) as **"low-signal — not usable for sourcing"**
     — these are marketing SPA shells, not docs. Record the drop
     reason in provenance notes.
2. `core/tool_mastery_author_agent/mapping.py` — `map_sections()` runs
   keyword scans against the *prose derivative only*, not the raw
   capture. Preserves the 2-hit minimum. A section can only be
   promoted to `sourced=true` if both hits land in prose, not JSON/JS.
3. `core/tool_mastery_author_agent/draft.py` — excerpts quoted in the
   rendered markdown are drawn from the prose derivative, so sourced
   sections will never contain `self.__next_f.push` garbage.

**Why this is the right move:**

- Bounded: three files, all inside the author agent. No new
  architecture, no new action types, no new dependencies, preserves
  all invariants (Control Plane, Manager, Research, Author isolation).
- Precise: fixes the exact failure mode observed in both higgsfield
  and clo3d provenance.
- Upholds the honesty contract: sections that can't be grounded in
  real prose become Uncovered, which is the honest state. The
  existing preserve-mode guard stays in place as a second safety net.
- Immediately verifiable: rerun the author drain against the existing
  `2026-04-09T02-36-56Z` (higgsfield) and `2026-04-09T02-37-02Z`
  (clo3d) research runs without re-fetching; expected outcome is
  almost every currently-sourced section on both tools demoting to
  Uncovered with the honest rationale "prose derivative had no
  in-prose keyword hits". That demotion is the success criterion.
- Cheap: no LLM, no new services, no human-in-loop changes.
- Unblocks the next real question — "do our candidate families point
  at URLs that actually contain prose documentation?" — by making
  prose absence visible in provenance instead of hiding it under
  false `sourced=true`. That becomes the next honest work item.

Secondary (not this build, but next-next):
- Once prose-locality is enforced, revisit candidate families: for
  higgsfield and clo3d specifically, the real docs live at
  `higgsfield.ai/about` / help pages and `support.clo3d.com` /
  `manual.clo3d.com`. Neither is discoverable from the current
  families. A `help_subdomain` family (`help.<base>.com`,
  `support.<base>.com`, `manual.<base>.com`) is the obvious expansion.
- Signpost two-drain model in dispatcher stdout so operators see the
  author action ID on the first run.

---

## Artifacts referenced

- `/opt/OS/logs/tool_mastery_research/higgsfield/2026-04-09T02-36-56Z/` (manifest, raw, provenance)
- `/opt/OS/logs/tool_mastery_research/higgsfield/candidates/2026-04-09T02-36-44Z.json`
- `/opt/OS/logs/tool_mastery_research/clo3d/2026-04-09T02-37-02Z/` (manifest, raw, provenance)
- `/opt/OS/logs/tool_mastery_research/clo3d/candidates/2026-04-09T02-37-02Z.json`
- `/opt/OS/logs/execution/2026-04-09-execution.jsonl` (CP audit trail; action ids `81ffb9b1-8554-4339-b36f-49902100b5f1`, `84ee756a-aea3-4be0-ab06-e2422474fc4e`)
- `/opt/OS/core/tool_mastery_research_agent/search_discovery.py`
- `/opt/OS/core/tool_mastery_research_agent/candidate_approval.py`
- `/opt/OS/core/tool_mastery_author_agent/{loader,mapping,draft,reconcile}.py`
- `/opt/OS/skills/tools/higgsfield/SKILL.md` + `references/best_practices.md`
- `/opt/OS/skills/tools/clo3d/SKILL.md` + `references/best_practices.md`

---

## Author Precision Fix Validation

**Date:** 2026-04-09
**Scope:** `core/tool_mastery_author_agent/loader.py` + `mapping.py`
**Principle:** *Better to say "I have nothing" than "I have something meaningless."*

### Motivation

Baseline authoring runs (pre-fix) on the higgsfield + clo3d research artifacts
produced suspiciously high sourcing counts given how thin the actual upstream
prose was. Inspection of `authored_provenance.json` showed the mapper was
promoting sections to "sourced" using keyword hits inside:

- Next.js flight-data payloads (`self.__next_f.push([1,"..."])`)
- Clerk SDK metadata blobs (`sdkMetadata`, `telemetry`, feature flags)
- GitHub's `featureFlags` array (hundreds of comma-separated identifiers)
- Inline `<script>` JSON for schema.org navigation
- Long base64 / hex chunk hashes

None of these represent human-authored documentation. The Author Agent was
reporting "sourced" for sections whose only evidence was noise inside a JS
SPA shell — the exact fabrication pattern the agent is supposed to prevent.

### Fix summary

Two-stage prose-only gate, applied before keyword scoring:

1. **Sanitisation (`loader.sanitize_text`)** — run at load time, before any
   downstream consumer sees the capture. Strips:
   - `<script>` / `<style>` / `<noscript>` blocks (regex, DOTALL)
   - Orphan `self.__next_f.push(...)` flight-data calls
   - Base64 runs (≥80 chars) and hex runs (≥32 chars)
   - Per-line filter: drops any line whose symbol density
     (`{}[]();=<>/\|...`) exceeds 30%, or any line >400 chars with
     symbol density >15%

2. **Prose-block enforcement (`mapping.is_prose_block` + `_split_prose_blocks`)** —
   after tag-stripping, the residue is chunked into paragraph-like blocks
   via `\n\n` or `. [A-Z]` boundaries. Each candidate must pass:
   - ≥80 chars, ≥12 words
   - Letter+space ratio ≥65%
   - Symbol-char ratio ≤8%
   - At least one sentence terminator (`.`, `!`, `?`)
   - Average word length in [3.0, 12.0] (rejects nav menus and hash slugs)

3. **Locality rule (`map_sections`)** — a section is "sourced" iff:
   - ≥2 distinct keywords matched **inside prose blocks** (not raw HTML), AND
   - ≥1 qualifying excerpt survived the prose gate, AND
   - the excerpt itself passes `is_prose_block` a second time after
     bounded window extraction (prevents mid-block code leakage)

4. **Excerpt quality filter (`_excerpt_from_block`)** — bounded excerpts are
   trimmed to word boundaries (no mid-token truncation), required to be
   ≥120 chars, and re-validated as prose.

5. **No rescue path** — if nothing qualifies, the section is demoted to
   `Uncovered`. Weak signals (≥1 keyword, below threshold) still surface in
   `matched_keywords` for honesty, but do not promote the section.

### Before / after

Both artifacts re-run through the full authoring pipeline via
`python3 -m core.tool_mastery_author_agent --tool {tool} --latest`. The
existing human-authored skills were preserved (the agent's reconcile layer
refuses to overwrite without `--force-rewrite`), so the comparison is drawn
from `authored_provenance.json` `drafts[]`, which reflects what the mapper
*would* have written.

| Tool        | Sourced (before) | Sourced (after) | Delta  | Verifier |
|-------------|-----------------:|----------------:|-------:|:--------:|
| higgsfield  | 13 / 19          | **0 / 19**      | −13    | PASS     |
| clo3d       |  7 / 19          | **0 / 19**      |  −7    | PASS     |

### Examples of filtered garbage vs accepted prose

**Rejected (higgsfield, previously "sourced" for Pagination):**

```
h color grading built in\"}],\"$Ld3\",\"$Ld4\"]}],\"$Ld5\"]}]}]}]
self.__next_f.push([1,"42:[\"$\",\"$Ld6\",null,{\"size\":5,
\"initialCursor\":2,\"totalLeft\":88}]
```
→ Scrubbed by `_NEXT_FLIGHT_RE` + symbol-density line filter in loader.

**Rejected (higgsfield, previously "sourced" for SDK Idioms):**

```
\"sdkMetadata\":{\"name\":\"@clerk/nextjs\",\"version\":\"6.39.0\",
\"environment\":\"production\"},\"nonce\":\"\",\"initialState\":null
```
→ Scrubbed as JSON inside `<script>` block.

**Rejected (higgsfield, previously "sourced" for Rate Limits via keyword `quota`):**

```
copilot_chat_reduce_quota_checks,copilot_chat_search_bar_redirect,
copilot_chat_selection_attachments,copilot_chat_vision_in_claude...
```
→ GitHub `featureFlags` array — scrubbed by symbol-density gate
(ratio >30%).

**Accepted (higgsfield, landing-page marketing copy):**

```
Create ready-to-share content in one click — from viral effects to
polished commercials, no editing needed.

Next-gen video creation powered by exclusive presets, seamless
transitions, and pro-grade VFX.
```

→ Both blocks pass `is_prose_block` (good letter ratio, sentence
terminators, reasonable word length). But neither contains ≥2
keywords for any TME section, so no section is promoted. Marketing
copy alone cannot fake technical mastery — exactly the intended
behaviour.

**Accepted (clo3d, GitHub search footer):**

```
Contributors are working behind the scenes to make open source
better for everyone—give them the help and recognition they deserve.
```
→ Passes prose gate but contains no section keywords. Correctly ignored.

### Root cause confirmation

The sanitised-then-chunked captures contain essentially **no technical
prose** for either tool:

| Capture URL                                      | Raw bytes | Prose blocks |
|--------------------------------------------------|----------:|-------------:|
| `https://higgsfield.ai`                          |   225 035 |            2 |
| `https://github.com/search?q=higgsfield`         |   229 593 |            3 |
| `https://clo3d.com`                              |       173 |            0 |
| `https://www.clo3d.com/docs`                     |       173 |            0 |
| `https://pypi.org/project/clo3d/`                |       960 |            1 |
| `https://github.com/search?q=clo3d`              |   221 941 |            2 |

All three "high-byte" captures are SPA shells whose user-visible content
is assembled client-side. The 173-byte clo3d.com / docs captures are
captive error/landing pages. The pypi capture is an "ad blocker detected"
notice. **The research layer simply did not retrieve creator-level
documentation for either tool.** The old mapper hid that failure behind
fabricated keyword hits in JS noise; the new mapper surfaces it honestly.

### No fabricated sourcing remains

Confirmed via post-fix `authored_provenance.json`:

```
higgsfield: sourced=0/19  drafts_len=19  preserved=19
clo3d:      sourced=0/19  drafts_len=19  preserved=19
```

Every draft with `sourced=true` was eliminated. The `matched_keywords`
arrays still record weak signals (e.g. higgsfield Data Model: `field`)
for diagnostic transparency, but none crossed the 2-hit + prose-locality
threshold.

### Impact on final output quality

- Existing human-authored `skills/tools/higgsfield/SKILL.md` and
  `skills/tools/clo3d/SKILL.md` are **unchanged** — the Author Agent's
  reconcile layer correctly preserved them (the whole point of the
  preserve-mode path).
- Verifier reports `PASS` for both tools (the skills satisfy the 19-section
  structural contract regardless of Author Agent output).
- Had these skills been scaffolded fresh, the new behaviour would write
  19 honest `Uncovered` placeholders rather than 13+7 fabricated
  "Sourced" blocks — forcing a human to do real research before claiming
  mastery.
- The Control Plane, Research Agent, Manager, and verifier are all
  unchanged. This is a pure authoring-precision fix.

### Files touched

- `/opt/OS/core/tool_mastery_author_agent/loader.py` — added
  `sanitize_text()` + per-line filter, wired into `_read_text_safely()`.
- `/opt/OS/core/tool_mastery_author_agent/mapping.py` — added
  `is_prose_block()`, `_split_prose_blocks()`, rewrote
  `_find_excerpt`/`_scan_capture_for_section`/`map_sections` to operate on
  prose blocks with locality enforcement and excerpt re-validation.
- No changes to `draft.py`, `reconcile.py`, `verify.py`, `agent.py`, `cli.py`.

### Principle honoured

> Better to say "I have nothing" than "I have something meaningless."

Before: 20 "sourced" sections across the two tools, every single one
traceable to JS/JSON noise. After: 0 sourced, 38 honest `Uncovered`
drafts, verifier still green, human skills untouched. The honesty gap
is closed.

---

## Source Quality Upgrade — 2026-04-09

**Principle applied:** find *better* information, not more.

### What changed

1. **New module** — `core/tool_mastery_research_agent/source_quality.py`.
   Pure functions, no LLM, no network:
   - `score_source()` — classifies a candidate as `high | medium | low`
     by URL shape: docs/developer/api subdomains, GitHub repo paths,
     package indexes (pypi/npm/crates/pkg.go.dev) → HIGH. Search
     aggregators (github.com/search, google, reddit), vendor roots
     without a docs path, `/pricing`, `/about`, social hosts → LOW.
   - `measure_signal()` — post-fetch prose density check, reusing the
     **exact same** sanitizer + prose detector the Author Agent uses
     (`sanitize_text`, `_strip_html`, `_split_prose_blocks`). A source
     must produce ≥1500 sanitized chars, ≥3 prose blocks, ≥400 prose
     chars to clear the gate.
   - `classify_quality()` — derives a run-level `high | mixed | low`
     flag from the per-source signal reports.

2. **Prioritized fetch** — `source_discovery.py` now sorts the deduped
   plan by quality score (stable within bands), so HIGH sources are
   fetched first. `plan.notes` records the pre-fetch high/medium/low
   counts.

3. **Fetch budget cap** — `fetcher.py` enforces `DEFAULT_MAX_FETCHES=12`.
   Overflow is recorded as `SKIPPED` (not silently dropped), preserving
   provenance ("we saw it, chose not to spend a fetch on it").

4. **Post-fetch signal filtering** — `artifact.build_artifact()` now
   runs the signal pass on every OK source, demotes low-signal OKs to
   `SKIPPED` in-place with a specific reason, and stamps a run-level
   `quality` flag on the artifact. Only surviving sources reach the
   Author Agent.

5. **New artifact fields** — `ResearchArtifact.quality` and
   `ResearchArtifact.signal_reports` are persisted in
   `research_artifact.json`, surfaced in `summary.md` ("Signal gate"
   section), and propagated into `manifest.json`.

### Before vs. after (validation re-runs)

Both tools re-run on 2026-04-09 after the upgrade landed.

**higgsfield** — previous run fetched 2 sources OK (vendor root +
GitHub search), 0 sanitized blocks of real technical prose between
them. New run:

| Metric               | Before | After |
|----------------------|--------|-------|
| Pre-fetch high       | n/a    | 0     |
| Pre-fetch low        | n/a    | 2     |
| OK → Author Agent    | 2      | 0     |
| Run quality          | n/a    | `low` |

Both sources now honestly dropped by the signal gate:
- `higgsfield.ai` — only 2 prose blocks (need ≥3)
- `github.com/search?q=higgsfield` — only 397 prose chars (need ≥400)

**clo3d** — previous run fetched 4 sources OK (two 2403-byte CDN
stubs, a pypi page, a github search). New run:

| Metric               | Before | After |
|----------------------|--------|-------|
| Pre-fetch high       | n/a    | 7     |
| Pre-fetch low        | n/a    | 4     |
| OK → Author Agent    | 4      | 0     |
| Run quality          | n/a    | `low` |

All four OK fetches dropped with specific reasons:
- `www.clo3d.com/docs` — sanitized body 173 chars (CDN stub)
- `clo3d.com` — sanitized body 173 chars (CDN stub)
- `pypi.org/project/clo3d/` — sanitized body 960 chars (no package)
- `github.com/search?q=clo3d` — only 2 prose blocks (aggregator)

### Signal density comparison

The honest read: neither tool has a recoverable public doc surface
today. Before the upgrade, the pipeline *also* produced nothing usable
for these tools — it just lied about it by handing "OK" HTML to the
Author Agent, which spent its own prose gate rejecting every section.
Now the rejection happens one layer earlier, with a specific reason
and a run-level `quality=low` flag that the Author Agent, TME
decision tree, and future orchestration can reason about without
re-reading every raw capture.

### Impact on authored output

No Author Agent runs were triggered for these validations because
`fetch_failed` short-circuits the handoff. This is the correct
outcome: the upgrade's whole point is that low-signal runs should
**not** produce skills, and should **not** waste an authoring pass
pretending they can.

### What this does NOT do

- It does not *find* better sources. If a tool has no docs site,
  no API reference, and no GitHub repo, the upgrade will honestly
  report `quality=low` — it will not invent a source. Operator
  intervention (registry entry, explicit `--official-url`, or
  widening the candidate generator) is still required.
- It does not second-guess human approval. Operator-approved
  candidates still enter the plan; they just get ordered and
  filtered by the same rules as everything else.
- It does not call any LLM or network service. All classification
  is deterministic and reproducible.

---

## Phase 2 — Docs Site Discovery (2026-04-08)

### Objective
Unblock documentation sites that Phase 1 could not reach: vendor
docs surfaces rendered as SPAs whose root HTML contains no prose.
Phase 1 proved GitHub repo extraction; Phase 2 targets the next
source class — any site that publishes a `sitemap.xml` or `llms.txt`.

### Implementation
New module: `core/tool_mastery_research_agent/docs_site_discovery.py`.

- Probes `/llms.txt`, `/sitemap.xml`, and `/sitemap_index.xml` against
  every unique host already on a `SourcePlan`.
- Parses sitemaps via stdlib `xml.etree.ElementTree` (no new deps).
- Parses `llms.txt` with a permissive tokeniser that accepts both
  markdown-link form `[label](url)` and bare `http(s)://` URLs.
- Detects **two llms.txt conventions** the ecosystem has forked into:
  1. *Index form* — a curated flat list of doc URLs.
  2. *Instruction form* — the file IS the documentation, written as
     prose + code blocks for LLMs to read directly (Remotion does this).
     When the body is ≥1000 bytes with <5 links, the `llms.txt` URL
     itself is emitted as a single `SourceRef` and the fetcher pulls
     it as a clean-text source.
- Filters discovered URLs through three gates:
  1. same host as the probe
  2. doc-shaped path (`/docs`, `/api`, `/reference`, `/guide`,
     `/tutorial`, `/manual`, `/examples`, or `.md`/`.mdx`/`.rst`)
  3. **topical relevance** — the tool slug (or a length≥3 token of
     it) must appear in the host or path. This check prevents a
     generic aggregator sitemap from drowning the plan with URLs
     that are shaped like docs but belong to a different project.
- Blocks sitemap discovery on aggregator hosts
  (`pypi.org`, `npmjs.com`, `github.com`, `raw.githubusercontent.com`,
  `crates.io`, `pkg.go.dev`, `rubygems.org`, `hexdocs.pm`). Those
  publish package-universe sitemaps that have nothing to do with
  any single tool's documentation. Their specific package page is
  already carried on the plan via the registry tier.
- Caps every probed host at 12 URLs, caps child sitemap descent at
  3 index children, respects the fetcher's 2 MB body limit.

Integration point (`source_discovery.discover_sources`): runs after
GitHub repo expansion, before signal scoring. Each host is probed at
most once per run. Every failure writes an explanatory note to the
`SourcePlan` — the provenance log stays complete even on sites that
publish nothing.

### Constraints preserved
- **No fabricated URLs.** Every discovered URL is verbatim from the
  site's own machine-readable file.
- **No weakened signal gate.** Discovered URLs pass through the
  existing `source_quality.score_source` pipeline exactly like any
  other source. The scorer's `_HIGH_PATH_HINTS` already rewards
  `/docs`, `/api`, `/reference` paths, so phase-2 URLs naturally
  land in the HIGH band without scorer changes.
- **Fetch budget intact.** The fetcher's `DEFAULT_MAX_FETCHES=20`
  still rules; the per-host cap of 12 keeps one site from crowding
  everything else off the plan.
- **Provenance.** Every emitted `SourceRef` carries
  `origin="docs_site_discovery:<method>:<host>"` and
  `tier=OFFICIAL_DOCS`. The method string is `llms_txt`,
  `llms_txt_instruction`, or `sitemap`.

### Validation — live runs (2026-04-08)

Three tools exercised end-to-end via `discover_sources`:

| tool        | sources (before) | sources (after) | phase 2 discovered | outcome                  |
|-------------|------------------|-----------------|--------------------|--------------------------|
| clo3d       | 11               | 11              | 0                  | no ML-readable docs      |
| higgsfield  | 2                | 2               | 0                  | llms.txt present, non-doc |
| remotion    | 1                | 8               | **7**              | **llms.txt unlocked**    |

**Remotion detail.** `www.remotion.dev/llms.txt` is instruction-form
(10,827 bytes of prose + 7 embedded `/docs/lambda/*` links). Phase 2
detected both shapes: the embedded links pass the filter and were
emitted individually. Signal band post-scoring: 7/8 HIGH.

**Higgsfield detail.** `higgsfield.ai/llms.txt` exists and parses
cleanly (24 URLs) but every URL points at product/feature landing
pages (`/image/...`, `/create/video`, `/lipsync-studio`, `/pricing`)
— none match the doc-path filter. This is an **honest negative**:
the filter correctly refused to promote marketing product pages as
documentation. Lowering the filter would corrupt the trust boundary
we built in Phase 1. Finding: the llms.txt ecosystem is not
homogeneous — some sites use it as a product index rather than a
docs index. The research agent must NOT treat these as equivalent.

**Clo3d detail.** No `llms.txt`. No `sitemap.xml` on any speculative
subdomain (`clo3d.com`, `www.clo3d.com`, `docs.clo3d.com`,
`clo3d.io`, `clo3d.ai` — last three are DNS failures). This is
a genuinely docs-dark site at the sitemap layer. The provenance log
records every probe and every failure. Further unlock for clo3d is
a Phase 3 concern (structured crawl from the known-good
`support.clo-set.com` surface the operator has already approved).

### Bugs caught during implementation

1. **`ElementTree` falsy elements.** Initial XML parser used
   `entry.find(ns+'loc') or entry.find('loc')` as a namespace
   fallback. ET elements with no children are falsy, so a valid
   `<loc>` element with text-only content was treated as missing
   and silently skipped. The parser reported "sitemap parse error:
   no element found" cleanly but returned zero URLs. Fixed by using
   explicit `is not None` checks. This is exactly the class of
   silent-failure the honesty boundary is designed to catch, and
   it was caught because offline parser tests were run before any
   live probe.

2. **Topical filter too narrow.** First version of
   `_topically_relevant` only checked the URL path. `remotion.dev`
   puts the slug in the host (`www.remotion.dev`) not the path
   (`/docs/lambda/setup`), so every remotion doc link was rejected.
   Fixed to check host + path together.

3. **pypi.org sitemap drowns discovery.** The first live run
   returned 12 URLs from `pypi.org/sitemap.xml` that all passed the
   `/project/` path hint but were unrelated packages. Fixed by
   adding the `_DISCOVERY_SKIP_HOSTS` aggregator blocklist: package
   registries and code hosts publish universe-scale sitemaps that
   are structurally wrong for per-tool discovery.

### Limitations (honestly stated)

- **SPA-only sites with no sitemap** still cannot be reached. clo3d
  is the canonical example. Phase 3 (structured crawl of already-
  approved docs URLs) is the natural next step for these.
- **Product-index llms.txt** (higgsfield pattern) yields nothing.
  This is intentional — the alternative is letting marketing
  landing pages into the research corpus, which would corrupt the
  author agent's signal.
- **No JavaScript rendering.** The fetcher is still plain `urllib`.
  Sites that require JS execution to serve docs HTML are out of
  scope for Phase 2 and Phase 3; that's a Phase 5+ concern (if
  ever — we may prefer to require sites to publish machine-readable
  surfaces instead of importing a headless browser).
- **No recursive crawl.** We consume the site's own published
  index. We do not follow `<a href>` out of discovered pages —
  that is explicitly Phase 3 (structured crawl expansion).
- **Signal is still filtered at fetch time.** Discovery only adds
  candidates; it does not bypass the signal gate. A URL that looks
  doc-shaped but fetches to a near-empty SPA shell still gets
  dropped post-fetch, exactly as in Phase 1.

### Files touched
- `core/tool_mastery_research_agent/docs_site_discovery.py` — new
- `core/tool_mastery_research_agent/source_discovery.py` — integration
  point after GitHub expansion, before signal scoring
- `docs/audits/2026-04-09-higgsfield-clo3d-full-path-validation.md` —
  this section

### Verdict
Phase 2 is **landed and honest**. It moves remotion from 1 → 8
sources (7 high-signal doc URLs via llms.txt). It cannot and does
not claim to fix clo3d or higgsfield — those sites do not publish
the surfaces Phase 2 consumes. The provenance log on every run
explains exactly which probes ran, which succeeded, and which
failed, so an operator can tell at a glance whether a tool's
coverage gap is a Phase 2 concern or a deeper issue needing Phase 3+.

---

## Phase 3 — Structured Crawl Expansion

### What landed
New module `core/tool_mastery_research_agent/structured_crawl.py`
and a single integration call in `source_discovery.py` after Phase 2
(`docs_site_discovery`) and before signal scoring.

Phase 3 takes the already-approved doc pages produced by earlier
phases and follows their in-page `<a href>` links — strictly one hop
by default — using `html.parser.HTMLParser` (stdlib, no new deps).

### Guardrails (the feature IS the guardrails)
| Guardrail | Value | Why |
|---|---|---|
| `MAX_CRAWL_DEPTH` | 1 (ceiling 2) | Parent → child only. 2 is allowed but clamped. |
| `MAX_SEEDS_PER_RUN` | 6 | Cap on number of approved parents crawled. |
| `MAX_NEW_URLS_PER_RUN` | 18 | Global new-URL budget. |
| `MAX_NEW_URLS_PER_HOST` | 10 | One nav bar cannot crowd out other tools. |
| `MAX_LINKS_PER_PAGE` | 250 | Defensive cap against pathological nav trees. |
| Same host only | enforced | Cross-origin links are never followed. |
| Doc-path allowlist | inherited from Phase 2 `_DOC_PATH_HINTS` | `/docs`, `/api`, `/reference`, `/guide`, `/tutorial`, `/examples`, ... |
| Reject list | inherited from Phase 2 `_REJECT_PATH_HINTS` | auth, pricing, blog, legal, careers, cart, search. |
| Querystring-heavy URLs | rejected | If `?…` is longer than the path → treat as app route. |
| Fragments | stripped via `urldefrag` | `/foo#bar` normalises to `/foo`. |
| Aggregator hosts | skipped | github.com / pypi.org / npmjs.com / etc. — already covered by earlier tiers. |
| Topical relevance | slug token in host/path OR sibling-of-approved | Prevents drift onto unrelated sections. |
| Signal gate | **unchanged** | Crawled candidates still pay the same prose-density tax. |
| Provenance | per-URL parent, depth, match reason | `origin=structured_crawl:<host>:depth1:<reason>:parent=<url>` |

### Validation results

All three tools were run through `discover_sources()` with Phase 3
active. Results are verbatim from the crawl reports.

#### remotion (control — expected to benefit)

With the hint `https://www.remotion.dev/docs` (matching the llms.txt
instruction-form entry that Phase 2 already surfaces in prod):

- **Seeds selected:** 6 (cap hit)
- **First seed raw anchors:** 124 (`https://www.remotion.dev/docs`)
- **Filtered-in:** ~20+ doc-shaped, same-host, topically-relevant
- **Emitted after caps:** **10** (per-host cap hit — designed behaviour)
- Dropped-by-cap examples recorded in notes:
  `animating-properties`, `reusability`, `preview`, `transforms`,
  `videos/`, `using-audio`, `parameterized-rendering`, ...
- **Total source plan grew from 8 → 18** (the 10 crawl hits are
  additive, full provenance).

Sample emitted URLs (all same-host, all doc-shaped, all with
depth-1 parent provenance):

```
https://www.remotion.dev/docs/
https://www.remotion.dev/docs/api
https://www.remotion.dev/docs/editor-starter
https://www.remotion.dev/docs/timeline
https://www.remotion.dev/docs/recorder
https://www.remotion.dev/docs/the-fundamentals
https://www.remotion.dev/learn
...
```

Phase 3 demonstrably expands usable technical prose for remotion.
The per-host cap kicked in (10/10) — exactly the guardrail we want
active on chatty nav trees.

#### clo3d (primary target — expected to stay blocked)

With the registry set as-is (3 derived doc-shaped URLs):

- **Seeds selected:** 3 (under cap)
- **Seed 1:** `https://www.clo3d.com/docs` → **0 raw anchors**
  (SPA shell — HTML served contains a bootstrap `<script>` and no
  `<a>` tags at all).
- **Seed 2:** `https://docs.clo3d.com/api` → **network error:
  Name or service not known** (the `docs.clo3d.com` subdomain
  does not resolve in DNS).
- **Seed 3:** `https://docs.clo3d.com/reference` → same DNS failure.
- **Discovered:** 0. **Filtered-in:** 0. **Emitted:** 0.

Phase 3 yielded **zero value for clo3d** and **this is the
honest, correct outcome**. The root cause is not crawler weakness:

1. `www.clo3d.com/docs` is a JS-rendered SPA with no anchor tags
   in the static HTML. A DOM-rendering browser would be required,
   which is an explicit non-goal (see Phase 2 limitations).
2. `docs.clo3d.com` is a fabricated subdomain guessed by an
   earlier discovery step — it does not exist. The crawler
   surfaces this as a concrete DNS error in provenance rather
   than silently dropping it, which is exactly what the honesty
   boundary is for.

clo3d remains honestly blocked at the Phase 2 → Phase 3 boundary.
The next move for clo3d is not a smarter crawler — it is either a
JS-rendering fetcher (Phase 5+, if ever) or an operator-provided
direct URL to real static HTML.

#### higgsfield (secondary target — expected to stay blocked)

Two runs were tried.

**Run 1 — registry only:** 2 sources surfaced (`higgsfield.ai`,
a GitHub search URL). Neither is doc-shaped.
- **Seeds selected:** 0 — crawler correctly declined to crawl
  from a homepage or a GitHub search page.
- Note emitted: `"no eligible seeds (approved refs were all
  aggregators, non-HTTP, or non-doc-shaped)"`.

**Run 2 — with the hint `https://higgsfield.ai/docs`:**
- Phase 2 surfaced 24 curated URLs from `higgsfield.ai/llms.txt`
  but **none passed the doc-path filter** (the higgsfield
  llms.txt indexes product/marketing pages, not `/docs`).
- **Seeds selected:** 1 (the hinted URL).
- `https://higgsfield.ai/docs` → **HTTP 404**.
- **Discovered:** 0. **Filtered-in:** 0. **Emitted:** 0.

Phase 3 yielded **zero value for higgsfield** and **this is the
honest, correct outcome**. higgsfield does not publish technical
docs under any `/docs`, `/api`, or `/reference` path. No amount of
crawling from a 404 produces content. The honesty boundary holds.

### Per-tool outcome table

| Tool | Seeds | Raw discovered | Filtered-in | Emitted | Net change | Verdict |
|---|---:|---:|---:|---:|---:|---|
| remotion | 6 | 124+ (first seed alone) | 20+ | **10** | 8 → 18 sources | **Phase 3 benefited materially** |
| clo3d | 3 | 0 | 0 | 0 | unchanged | honestly blocked (SPA shell + DNS failure) |
| higgsfield | 1 (with hint) / 0 (without) | 0 | 0 | 0 | unchanged | honestly blocked (no `/docs` path exists — HTTP 404) |

### Honesty boundary — what Phase 3 does NOT claim

- It does not claim to have solved clo3d.
- It does not claim to have solved higgsfield.
- It does not promote marketing, landing, pricing, login, blog,
  or changelog pages — the reject list blocks them explicitly.
- It does not cross origins. A link from `www.remotion.dev/docs`
  to `github.com/remotion-dev/remotion` is dropped (GitHub is
  already covered by Phase 1).
- It does not follow JavaScript. A site that only renders its
  nav in a React shell will return 0 anchors and the crawler
  will say so.
- It does not weaken the signal gate. Every crawled URL is still
  subject to the same post-fetch prose-density check every other
  source pays.
- It does not fabricate URLs. Every emitted ref has a real parent,
  a real depth, and a real match reason, written into its
  `origin` field as `structured_crawl:<host>:depth1:<reason>:parent=<url>`.

### What Phase 3 actually delivered

- A mechanism to surface usable doc URLs that sitemaps and
  llms.txt do not expose but that a real docs site links to
  in its own nav — the remotion case.
- Explicit, machine-readable evidence that clo3d and higgsfield
  cannot be unblocked by any honest crawl strategy with today's
  fetcher, because the first is a rendered SPA and the second
  does not publish docs at all.
- Full provenance on every new URL — parent, depth, match
  reason — so every candidate can be traced back to the approved
  entry that produced it, and every rejection can be traced back
  to the specific rule that rejected it.

### Anti-patterns consciously avoided

1. **No `<base href>` trust.** We resolve relative links against
   the fetched URL, not a page-declared base, so a site cannot
   redirect the crawler off its own origin by setting
   `<base href="https://attacker.com/">`.
2. **No depth-2 by default.** Depth 2 is wired and capped but
   only activates when the caller explicitly opts in. Every
   additional depth multiplies the blast radius.
3. **No HTML parse retries on malformed markup.** We accept
   `html.parser`'s best-effort extraction silently; a broken
   page simply contributes zero links instead of raising.
4. **No deduping across tool runs.** Each tool gets its own
   crawl budget. A URL seen by `remotion` is not memoised
   globally — the rule would cross-contaminate unrelated tools.
5. **No rewriting of URLs.** `/foo/` and `/foo` are treated as
   distinct; we do not normalise trailing slashes because some
   SPAs route them differently. `urldefrag` is used only to
   strip `#fragment`.

### Gotchas discovered during validation

1. **SPA shell returns zero anchors — clean.** `www.clo3d.com/docs`
   served a valid HTML 200 with a `<script>` bootstrap and no `<a>`
   tags. The parser recorded "0 raw anchors" without error. This
   is the desired shape of the honesty signal: we learn the site
   is empty-to-us rather than guessing.

2. **Guessed subdomains produce real DNS errors.** `docs.clo3d.com`
   was synthesised by an earlier discovery guess. It does not
   resolve. The crawler records
   `network error: Name or service not known` in provenance
   instead of swallowing it. This surfaces the guess as a bug
   in the discovery stage rather than letting Phase 3 pretend it
   is "just a missing site."

3. **Per-host cap hit on remotion is the point.** The crawler
   stopped at 10 new remotion URLs and recorded the next 7
   drop-by-cap events in the notes list. If those drops ever
   stop being logged, a future refactor has broken the visibility
   of the guardrail and the phase is no longer honest.

4. **`remotion` without an explicit hint surfaces 0 sources.**
   The registry row for remotion was not exercised in this
   validation pass; the real-world flow uses the Phase 2
   instruction-form llms.txt which is the established route.
   Phase 3 becoming useful to remotion only when hinted is not
   a crawler bug — it reflects that the upstream approved-seed
   set must already contain a real doc URL. This is the
   intended contract: **Phase 3 is expansion, not discovery.**

### Files touched
- `core/tool_mastery_research_agent/structured_crawl.py` — new (~360 lines)
- `core/tool_mastery_research_agent/source_discovery.py` — one new
  import and one new block after Phase 2, before signal scoring
- `docs/audits/2026-04-09-higgsfield-clo3d-full-path-validation.md` —
  this section

### Verdict

Phase 3 is **landed and honest**.

It expands the corpus for sites that publish ordinary HTML nav
(remotion: +10 URLs, per-host cap reached). It refuses to expand
for sites that do not (clo3d: SPA shell, higgsfield: no `/docs`).
Every new URL carries parent, depth, and match-reason provenance.
Every rejection is recorded as a note with a reason string.
The signal gate is unchanged and every crawled candidate still
pays the same prose-density tax downstream.

Conservative crawl > broad crawl. Approved page → bounded
expansion. Discovery breadth never outruns provenance.
