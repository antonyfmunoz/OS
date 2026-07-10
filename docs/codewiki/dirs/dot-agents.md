---
type: codewiki-dir
dir: .agents
---

# `.agents/` — canonical home of the design/frontend skill packages

**183 files · 3,024,145 bytes · [Full file inventory](../inventory/dot-agents.md)**

## Purpose
`.agents/` holds the canonical, on-disk copies of UMH's design, frontend, and
research skill packages — the heavier "creative craft" skills that are shared
across every skill surface in the repo via symlinks. Everything lives under one
subdirectory, `.agents/skills/`. These are the anti-slop frontend skills
(`design-taste-frontend`, `impeccable`, `refero-design`), image-generation
direction skills (`imagegen-frontend-web`, `imagegen-frontend-mobile`,
`image-to-code`), brand systems (`brandkit`), UI aesthetic packs
(`industrial-brutalist-ui`, `minimalist-ui`, `high-end-visual-design`,
`gpt-taste`, `stitch-design-taste`, `redesign-existing-projects`), writing and
research tooling (`humanizer`, `last30days`, `improve`), and coding-discipline
guidance (`karpathy-guidelines`, `full-output-enforcement`). This directory is
the single source of truth so the same package is never duplicated across
`skills/` and `.claude/skills/`.

## How it fits
Like `skills/`, `.agents/` is a knowledge/config surface, not a Python code
layer — nothing in the projections → transports → adapters → substrate stack
imports it. Its role is to be the **symlink target**. Both
[`skills/`](./skills.md) and `.claude/skills/` (see [dot-claude.md](./dot-claude.md))
contain symlinks that resolve into `.agents/skills/`:

- `skills/<name>` → `../.agents/skills/<name>` (16 links)
- `.claude/skills/<name>` → `../../.agents/skills/<name>`

The two link sets differ slightly: `humanizer` and `last30days` are exposed
through `.claude/skills/` but not through `skills/`. This is a deliberate
node-role/convention layout — one physical package, surfaced wherever a skill
loader expects to find it, with zero copies. The externally-sourced packages here
(`humanizer`, `improve`, `karpathy-guidelines`, `last30days`) are pinned to their
upstream GitHub repos in the repo-root `skills-lock.json` with a `computedHash`
for re-verification.

## Structure

| Subdir | Role |
|---|---|
| `.agents/skills/` | The only subdirectory — all 183 files live here, one directory per skill package |

Notable packages inside `.agents/skills/` (by weight and role):

| Package | Files/size signal | Role |
|---|---|---|
| `impeccable/` | large — `scripts/live-browser.js` alone is 11,173 lines; `detector/detect-antipatterns-browser.js` 5,138 lines | Full frontend design/critique/live-iteration toolkit: DESIGN.md parser, anti-pattern detectors (regex + static-HTML + browser + visual engines), live variant server, and a preToolUse design gate hook |
| `design-taste-frontend/` | `SKILL.md` 1,206 lines | v2 anti-slop frontend skill; `design-taste-frontend-v1/` preserved for backward compatibility |
| `image-to-code/` | `SKILL.md` 1,228 lines | Image-first website design → code |
| `imagegen-frontend-mobile/` | `SKILL.md` 1,465 lines | Premium mobile-app screen image direction |
| `imagegen-frontend-web/` | `SKILL.md` 987 lines | Per-section website design-reference image generation |
| `brandkit/` | `SKILL.md` 798 lines | Premium brand-kit / logo-system / identity-deck image generation |
| `refero-design/` | `SKILL.md` 538 lines | Research-first UI/product design (default design skill) |
| `last30days/` | Python sub-project — `scripts/last30days.py` 1,200 lines + `lib/` + `tests/` | Research-any-topic-from-the-last-30-days harness (Reddit + X + YouTube + Web) with vendored bird-search client |
| `humanizer/` | `SKILL.md` 488 lines + README/WARP | Removes AI-writing signatures from text |
| `improve/` | `SKILL.md` 122 lines + `references/` | Read-only senior-advisor codebase audit → handoff plans |
| `industrial-brutalist-ui/`, `minimalist-ui/`, `high-end-visual-design/`, `gpt-taste/`, `stitch-design-taste/`, `redesign-existing-projects/` | `SKILL.md` each | Distinct UI aesthetic/direction packs |
| `karpathy-guidelines/`, `full-output-enforcement/` | `SKILL.md` each | LLM coding-discipline guidance |

## Key components
`impeccable/` is the centre of gravity — most of the 3 MB lives in its
`scripts/` tree. It is effectively an application: `scripts/live-server.mjs` +
`scripts/live-browser.js` run a self-contained live-variant editing server;
`scripts/detector/` is a multi-engine anti-pattern detector
(`rules/checks.mjs` is 2,671 lines) with browser, regex, static-HTML, and
visual engines plus a `registry/antipatterns.mjs`; `scripts/hook-before-edit.mjs`
and `scripts/hook-lib.mjs` (1,632 lines) implement a design-quality write gate.
`last30days/` is the other embedded sub-project — a stdlib-plus Python research
pipeline (`scripts/lib/` with brave_search, openai_reddit, youtube_yt, xai_x,
scoring, dedup, rendering) and its own `tests/`. Everything else in `.agents/`
is a `SKILL.md`-driven package whose value is the prompt/craft guidance, not
executable code.

## Data & state
- **Reads:** nothing at rest — these are skill packages loaded on demand by the
  skill loader / Claude Code.
- **Vendored/locked:** `humanizer`, `improve`, `karpathy-guidelines`, and
  `last30days` are pinned in the repo-root `skills-lock.json` (`sourceType:
  github`, per-skill `computedHash`) so their content can be verified against
  upstream. The others are UMH-authored.
- **Runtime state:** the `impeccable/` live server and `last30days/` scripts
  write their own working files under their package dirs when invoked, not into
  `.agents/` broadly.

## Gotchas
- **This is the canonical home — edit here, not through the symlinks.** A change
  made in `.agents/skills/<name>/` propagates automatically to both `skills/<name>`
  and `.claude/skills/<name>` because those are symlinks. Never "copy" a package
  out of `.agents/`; that breaks the single-source-of-truth invariant and
  violates Node Role Discipline (each artifact stored once).
- **The two symlink sets are not identical.** `humanizer` and `last30days`
  resolve from `.claude/skills/` only. If you expect a design skill under
  `skills/` and it is missing, check `.claude/skills/` and `.agents/skills/`
  before concluding it does not exist.
- **`impeccable/` and `last30days/` are code, not just prompts.** They ship
  executable Node/Python with their own dependencies and (for `last30days/`)
  tests — treat them as sub-projects, and heed their vendored-code licenses
  (`.agents/skills/last30days/scripts/lib/vendor/bird-search/LICENSE`).
- **Large generated/bundled files live here** (e.g. `modern-screenshot.umd.js`,
  the 11k-line `live-browser.js`) — they inflate `.agents/`'s byte count but are
  bundled browser payloads, not hand-maintained source.

## See also
- [skills.md](./skills.md) — the runtime skill library that symlinks into here
- [dot-claude.md](./dot-claude.md) — `.claude/skills/` (the second symlink set) and skill-authoring rules
- [agents.md](./agents.md) — agent SOUL documents (a different concept: identity, not skill packages)
- [conventions.md](../conventions.md) — the single-source-of-truth / node-role conventions this layout follows
