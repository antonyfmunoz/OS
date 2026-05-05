# Wave 4 — Frontend Ecosystem Tool Mastery Audit

**Date:** 2026-04-06
**Engine:** `/opt/OS/skills/meta/tool_mastery_engine` (Create Flow, v3.0)
**Scope:** Close the remaining Tier 1 frontend ecosystem gaps directly referenced by the existing skill graph after Waves 1–3.
**Outcome:** 4/4 skills created, verified, Neon-synced, and pushed to `main`.

---

## Skills created

| # | Skill | SKILL.md | best_practices.md | Verification | Neon | Commit |
|---|---|---:|---:|---|---|---|
| 1 | `tanstack_table` | 18,063 | 33,100 | PASS | OK | `29d68d0` |
| 2 | `radix_ui`       | 14,511 | 39,466 | PASS | OK | `37a585a` |
| 3 | `sonner`         | 11,148 | 25,703 | PASS | OK | `7441951` |
| 4 | `vitest`         |  9,483 | 18,073 | PASS | OK | `5930e85` |

All four exceed every Tool Mastery Engine bar (SKILL.md > 500 chars, best_practices.md > 2,000 chars, all 19 protocol sections present, Authentication + Gotchas in SKILL.md, frontmatter complete with `last_researched`, `source_url`, `api_version`, `sdk_version`, `speed_category`, `context: fork`).

Each skill ships the full 5-artifact set:
- `SKILL.md`
- `references/best_practices.md` (19 sections)
- `references/examples.md` (real EOS-aligned recipes)
- `references/anti_patterns.md`
- `references/integrations.md`

---

## Execution method

For each skill, the main thread dispatched **one specialist build subagent**, which in turn:

1. Created the `.creating` lock file and ran `scaffold_tool_skill.py`.
2. Attempted Context7 Phase 0 SDK pull (skipped where unavailable).
3. Launched **two parallel research subagents** in a single tool-use block:
   - **Subagent A — Operational Knowledge** (official docs, changelog, GitHub issues, version pinning).
   - **Subagent B — Creator Intelligence** (founder philosophy, ecosystem position, frontier patterns, trajectory).
4. Synthesized into all 5 artifacts.
5. Ran the engine's verification block until PASS.
6. Synced to Neon `skills` table via the `INSERT … ON CONFLICT (org_id, name) DO UPDATE` pattern.
7. Cleaned `/tmp` + `.creating` lock, committed only the new skill directory, pushed to `origin/main`.

This pattern (1 build agent → 2 research agents) is the right granularity for Tier 1 skill creation: it isolates each skill's research from main-thread context bloat while keeping git operations sequential and conflict-free.

---

## Skill-specific highlights

### 1. tanstack_table
- 9 EOS-shaped recipes including server-driven pagination with TanStack Query (`placeholderData: keepPreviousData`), faceted filters, RHF inline cell editing, nuqs URL-state sync, and a 50k-row virtualized log viewer.
- 11 enumerated gotchas covering memoization of `columns`/`data`, controlled-state churn, row identity stability, and the manual-pagination contract.
- Marks Auth/Rate Limits/Webhooks/Cost Model as N/A with rationale (client lib).

### 2. radix_ui
- 39,466 chars of best practices — the deepest of the wave because Radix is the substrate for nearly every shadcn component.
- Captures the editing rule: **touch shadcn wrappers for styling, never for behavior** — behavior belongs to the underlying Radix primitive.
- Documents `asChild` / `Slot` mechanics, FocusScope, Portal layering, scroll-lock conflicts, and the React 18 / Next App Router `"use client"` requirement.
- Cross-references sonner as the canonical replacement for `@radix-ui/react-toast` (now in maintenance).

### 3. sonner
- Centers the canonical pattern: **TanStack Query `MutationCache.onError` for global error toasts + per-mutation `toast.promise` for happy-path feedback**.
- Documents the id-based dedupe pattern that eliminates toast spam in long-running flows.
- Notes shadcn dropped `use-toast` — `toast()` is the only surface in current shadcn. (Action item: refresh `shadcn_ui` skill if still mentioning `use-toast`.)
- Frontier patterns sourced from Vercel / Cursor / X usage and Emil Kowalski's "Building a toast component" essay.

### 4. vitest
- Vitest = Vite (same toolchain via `mergeConfig` from `vitest/config`) — the design insight that explains everything else.
- Captures the **jsdom + Radix incompatibility matrix**: without `hasPointerCapture`, `scrollIntoView`, `ResizeObserver`, and `IntersectionObserver` stubs in the setup file, ~80% of shadcn components are untestable.
- TanStack Query test wrapper rule: **fresh `QueryClient` per test with `retry: false`, `gcTime: Infinity`** — eliminates the #1 React Query test footgun.
- userEvent v14 + fake timers compatibility (`shouldAdvanceTime: true`).
- Explicit boundary drawn vs Playwright: Vitest = unit/integration, Playwright = e2e, Vitest browser mode = jsdom-incompatible middle ground.

---

## Integration relationships discovered

The four skills knit the EOS frontend stack into a single coherent graph:

```
react ──┬── typescript ──┬── shadcn_ui ── radix_ui
        │                │       │
        ├── vite ── vitest       ├── tanstack_table ── tanstack_react_query
        │                        │
        └── tailwind             ├── react_hook_form ── zod
                                 │
                                 └── sonner
```

Specific relationships now documented in EOS skills:

- **shadcn_ui ↔ radix_ui** — every `components/ui/*.tsx` is a thin Radix wrapper. Editing rule encoded.
- **tanstack_table ↔ tanstack_react_query** — manual pagination + `placeholderData: keepPreviousData` is the canonical server-table contract.
- **tanstack_table ↔ shadcn_ui** — DataTable copy-paste pattern.
- **sonner ↔ tanstack_react_query** — `MutationCache.onError` global handler + `toast.promise` per-mutation is the highest-leverage feedback pattern.
- **sonner ↔ radix_ui** — sonner is the official replacement for `@radix-ui/react-toast`.
- **vitest ↔ MSW v2** — mock at the network boundary with `http.get`, never patch `fetch`.
- **vitest ↔ radix_ui/shadcn_ui** — jsdom polyfill matrix is mandatory.
- **vitest ↔ react_hook_form + zod** — RHF form test recipe (fill, submit, assert error states) is in `examples.md`.
- **vitest ↔ tanstack_react_query** — fresh `QueryClient` + `retry: false` + `gcTime: Infinity` per test.

---

## Issues encountered

1. **Verifier regex brittleness.** The Tool Mastery Engine verification uses `'## Rate Limits' in b` (substring). Skill #1 (`tanstack_table`) initially used `## Section 4: Rate Limits` headers and failed the check; the build agent fixed by stripping the `Section N:` prefix. Subsequent skills used plain headers from the start.
   - **Recommendation:** Update `scripts/scaffold_tool_skill.py` (or the verifier) to either enforce the plain `## Section Name` style or use a smarter regex (`re.search(r'^##\s+(Section\s+\d+:\s+)?Rate Limits\s*$', b, re.M)`).

2. **N/A sections.** All four targets are client-side libraries — Authentication, Rate Limits, Webhooks, and Cost Model do not apply. The convention adopted (and now repeated across all four) is: **include the exact protocol header, then a one-paragraph N/A rationale**. This satisfies the verifier and preserves the 19-section discipline. The engine should formalize this in `research_protocol.md`.

3. **Context7 coverage gaps.** Context7 had partial-to-no coverage for sonner and limited coverage for tanstack_table v8. The parallel research subagents picked up the slack via WebSearch/WebFetch, which is exactly the engine's fallback design — no blocking issues.

4. **No Neon failures.** All four syncs upserted cleanly via the org-scoped `INSERT … ON CONFLICT` pattern. The failure-tolerant capture path was never exercised.

---

## Structural gaps revealed

Beyond the four Wave 4 targets, the skill graph still has visible holes that the new skills repeatedly reference but cannot resolve:

| Gap | Why it matters | Source |
|---|---|---|
| `tanstack_react_virtual` | Required for any list >1k rows; tanstack_table integrations doc references it as the virtualization partner. | tanstack_table |
| `msw` (Mock Service Worker v2) | The right network-mock layer for vitest; v1→v2 migration is non-trivial. | vitest |
| `cmdk` | The command-palette engine that composes with Radix Dialog/Popover; shadcn `Command` depends on it; every modern SaaS has ⌘K. | radix_ui |
| `nuqs` | URL state library; referenced by both tanstack_table (URL-synced filters) and radix_ui (URL-synced Tabs). | tanstack_table, radix_ui |
| `playwright` | Defines the e2e boundary that vitest deliberately stops at. | vitest |
| `testing_library_react` | userEvent v14 + query priority hierarchy + `renderHook` deserve a dedicated skill rather than living inside vitest. | vitest |
| `class_variance_authority` (cva) | Used by every shadcn component for variants; foundational to the Slot/polymorphism pattern. | radix_ui |
| `tailwindcss_animate` | Required plugin for shadcn enter/exit animations; referenced by both radix_ui and sonner. | radix_ui, sonner |
| `next_themes` | Referenced by shadcn's sonner wrapper for theme binding. | sonner |
| `floating_ui` | Under the hood of all Radix positioning; needed if EOS ever builds custom positioned primitives. | radix_ui |
| `tanstack_router` / `react_router` | Tanstack Router is referenced for end-to-end type-safe URL→table state but no skill exists. | tanstack_table |
| `storybook` | Storybook 8 + Vitest browser mode is the 2026 trajectory for component dev/test. | vitest |
| `drizzle_orm` (refresh) | The integrations doc shows the canonical server-side pagination/sort/filter contract — confirm `drizzle_orm` skill aligns. | tanstack_table |

---

## Recommended Wave 5 targets

**Wave 5 Tier 1 (highest leverage, build first):**

1. **`msw`** — vitest is essentially incomplete without a paired network-mock skill. Build immediately.
2. **`testing_library_react`** — pull the userEvent v14 + query priority knowledge out of vitest's examples into its own skill so it can be referenced from any frontend test context.
3. **`cmdk`** — universal SaaS UX pattern (⌘K), already referenced by radix_ui.
4. **`tanstack_react_virtual`** — unlocks safe rendering of any large list/table in EOS SaaS.
5. **`playwright`** — closes the vitest e2e boundary.

**Wave 5 Tier 2 (composition primitives):**

6. **`class_variance_authority`** — variant DSL behind every shadcn component.
7. **`nuqs`** — URL state, referenced from two of the four Wave 4 skills.
8. **`tailwindcss_animate`** — referenced from two of the four Wave 4 skills.
9. **`next_themes`** — referenced from sonner integration.

**Wave 5 Tier 3 (longer horizon):**

10. **`floating_ui`** — only needed if EOS builds custom positioned primitives.
11. **`storybook`** — adopt only when EOS SaaS needs an isolated component dev environment.
12. **`tanstack_router`** — adopt only if EOS migrates off whatever router shadcn-stack is using today.

**Engine improvements (do alongside Wave 5):**

- Tighten the verifier regex (or scaffold script) so `## Section N: Rate Limits`-style headers either work or are explicitly rejected at scaffold time.
- Formalize the **N/A-with-rationale** convention for client-side libraries in `references/research_protocol.md` so future tool skills don't have to re-derive it.
- Refresh `shadcn_ui` skill to remove any lingering `use-toast` references — the `toast()` direct call is the only current surface.

---

## Verification trail

```
$ git log --oneline -5
5930e85 Add tool skill: vitest
7441951 Add tool skill: sonner
37a585a Add tool skill: radix_ui
29d68d0 Add tool skill: tanstack_table
0164dd1 docs: Wave 3 Tier 1 frontend skills audit report
```

All four commits pushed to `origin/main`. Neon `skills` table contains the canonical content for each new tool skill, scoped to the active org.

Wave 4 closes the Tier 1 frontend ecosystem gap. EOS now has creator-level coverage of the React 18 + TS + Vite + shadcn/ui + Tailwind + Zod + RHF + TanStack Query + TanStack Table + Radix + Sonner + Vitest stack — the full surface needed to build, test, and ship the Initiate Arena and Empyrean Studio frontends without falling back to plugin-level skills.
