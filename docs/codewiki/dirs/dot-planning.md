---
type: codewiki-dir
dir: .planning
---

# `.planning/` — GSD planning workspace (phases, plans, summaries)

**39 files · 348,539 bytes · [Full file inventory](../inventory/dot-planning.md)**

## Purpose
`.planning/` is the on-disk workspace for the GSD (Get Sh*t Done) workflow — the phased planning discipline this repo builds through. Every non-trivial change is meant to enter via a GSD command (`/gsd:quick`, `/gsd:debug`, `/gsd:execute-phase`), and the artifacts those commands produce — project definition, requirements, roadmap, per-phase plans, and post-execution summaries — are persisted here so planning intent and execution state stay in sync across sessions and context resets.

## How it fits
Like `.claude/`, this directory is meta-tooling, not part of the projections→transports→adapters→substrate stack. It is the record of *how* the code got built, not the code itself. The root `CLAUDE.md` enforces GSD as the entry point for file-changing work; `.planning/` is where that enforcement leaves its trail. The current milestone captured here is **Phase 10.0 — Production Template Library + Cadence Candidate Supply + Cockpit Quality Gate**.

## Structure

| Subdir / file | Role |
|---|---|
| `PROJECT.md` | Milestone-level project definition (Phase 10.0) |
| `REQUIREMENTS.md` | Requirements spec for the active milestone (182 lines) |
| `ROADMAP.md` | Phase-by-phase roadmap (190 lines) |
| `STATE.md` | Live project state — where execution currently stands |
| `config.json` | GSD workspace configuration |
| `phases/` | 11 numbered phase dirs (23 files): PLAN.md + SUMMARY.md pairs per phase |
| `quick/` | 10 files — ad-hoc `/gsd:quick` tasks (timestamped slugs) |
| `debug/` | 1 file — a persisted `/gsd:debug` investigation session |

## Key components
**The GSD spine — `PROJECT.md` → `REQUIREMENTS.md` → `ROADMAP.md` → `STATE.md`** — is the read-first set: it tells you what milestone is active, what it must deliver, how it decomposes into phases, and how far execution has gotten.

**`phases/`** holds the executed work as PLAN/SUMMARY pairs across **11 numbered directories** (`01-preflight` through `10-browser-verification`, plus `12-audit`; phase `11` is skipped in the sequence). The plans are large and one-shot-executable by design — e.g. `04-template-seeding/04-01-PLAN.md` is 1,092 lines and `03-template-audit/03-01-PLAN.md` is 638 — matching the "exhaustive plans" discipline (every diff, config, and import specified so execution is pure application). Each phase's `-SUMMARY.md` records what actually shipped. `12-audit/12-01-AUDIT-REPORT.md` (248 lines) is the milestone's post-hoc audit.

**`quick/`** captures out-of-band tasks that jumped the phase queue — notably the Phase 13.x / 14.x operator-experience and voice work (e.g. `260608-rtf-…-device-presence-voice-session-routing`, `260609-rtf-…-voice-ux-seal`). **`debug/phase-14-18c-field-failure.md`** is a persisted debug session for a field failure.

## Data & state
All files are Markdown/JSON planning artifacts — no runtime state, no secrets, no code execution. `STATE.md` and `config.json` are the mutable coordination surface; the `phases/` and `quick/` trees are append-mostly historical records.

## Gotchas
- **Plan files are effectively immutable once written** (per the Plan File Immutability law in `CLAUDE.md`): the only sanctioned edit to an existing plan is marking a section COMPLETED. New plans get new filenames — never overwrite, because lost designs are irrecoverable.
- The phase numbering has a **gap at 11** — `phases/` jumps from `10-browser-verification` to `12-audit`. This is expected, not missing data.
- `.planning/` reflects one active milestone at a time. Historical milestones are archived out via `/gsd:cleanup` and `/gsd:complete-milestone`, so this snapshot is Phase 10.0 plus the quick/debug overflow, not the full project history.
- Do not treat `quick/` slugs' embedded phase numbers (13.x, 14.x) as contradicting the `phases/` numbering — `quick/` is a parallel ad-hoc lane, not part of the numbered roadmap.

## See also
- [dot-claude.md](dot-claude.md) — the GSD slash commands live in `.claude/commands/`
- [conventions.md](../conventions.md) · [architecture.md](../architecture.md)
