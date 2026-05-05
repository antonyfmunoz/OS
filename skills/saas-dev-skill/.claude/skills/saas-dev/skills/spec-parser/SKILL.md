---
name: saas-dev:spec-parser
description: Parses or collaboratively creates a SaaS product spec, producing a validated PageSpec[] with four composable layers (core, UI, data, analytics) plus shared components and backend spec. Supports paste-and-parse or domain-first guided creation. All items carry provenance (explicit vs inferred).
---

# saas-dev:spec-parser

Ingests a product spec (pasted or created collaboratively) and produces a validated `SpecOutput` — a structured `PageSpec[]` with composable layers for downstream phases. Every item carries `source: "explicit" | "inferred"` provenance for confirmation display.

## Input Paths

### 1. Paste path (SPEC-01)

User provides raw spec text (any format: markdown, plain text, Notion export, bullet list). System parses and restructures into PageSpec[].

**Pre-chunking (addresses oversized input):** Call `chunkRawText(rawInput)` from `lib/spec-parser/chunk-spec.ts` FIRST before any AI call. If it returns multiple chunks, call `restructureSpec` on each chunk separately, then merge the SpecOutput results (combine pages[], merge sharedComponents via `deduplicateComponents`, unify suggestedOrder).

For single-chunk input (most cases): call `parseSpec(rawInput)` from `lib/spec-parser/parse-spec.ts` directly.

```
import { chunkRawText } from "lib/spec-parser/chunk-spec.ts";
import { parseSpec } from "lib/spec-parser/parse-spec.ts";
import { restructureSpec } from "lib/spec-parser/restructure-spec.ts";

const chunks = chunkRawText(rawInput);
const output = chunks.length === 1
  ? await parseSpec(rawInput)
  : mergeSpecOutputs(await Promise.all(chunks.map(restructureSpec)));
```

### 2. Collaborate path (SPEC-02)

User has no spec. System guides through domain-first structured questioning.

```
import {
  createInitialState,
  buildSystemPromptForStage,
  isFlowComplete,
  extractSpecFromConversation,
  QUESTION_SEQUENCE,
} from "lib/spec-parser/collaborative-flow.ts";

const state = createInitialState();

for (const stage of QUESTION_SEQUENCE) {
  const systemPrompt = buildSystemPromptForStage(stage, priorContextSummary);
  // Ask the user stage-appropriate questions using systemPrompt
  // Record user + assistant messages in state.messages
  // Accept references (URLs, screenshots, "make it like X") at any point (D-08)
  state.stageIndex++;
}

const output = await extractSpecFromConversation(state.messages);
```

The multi-turn conversation loop is driven here in the skill. These modules provide the building blocks; the skill orchestrates the interaction.

## Post-Processing Pipeline

After either input path produces an initial SpecOutput:

### 1. Page count check (D-24/D-25)

If `output.pages.length > 25`, call `chunkSpecByDomain(pages)` from `lib/spec-parser/chunk-spec.ts`, re-restructure each chunk if needed, then merge.

```
import { chunkSpecByDomain } from "lib/spec-parser/chunk-spec.ts";

if (output.pages.length > 25) {
  const chunks = chunkSpecByDomain(output.pages);
  // Merge back after per-chunk processing
}
```

### 2. Provenance marking

Call `markProvenance(output, originalInputPageNames)` from `lib/spec-parser/spec-editor.ts` to ensure all items have accurate `source` fields based on comparison with the original user input.

```
import { markProvenance } from "lib/spec-parser/spec-editor.ts";

const markedOutput = markProvenance(output, originalInputPageNames);
```

### 3. Deduplication (D-20/D-21/D-22)

Call `deduplicateComponents(output.sharedComponents, output.pages)` from `lib/spec-parser/deduplicate-components.ts`. Show user the merges: "I merged these descriptions into one shared component: `ComponentName`." User confirms or splits.

```
import { deduplicateComponents } from "lib/spec-parser/deduplicate-components.ts";

const { deduplicated, merges } = await deduplicateComponents(
  output.sharedComponents,
  output.pages
);
// Show merges to user, allow split/confirm
```

### 4. Backend spec derivation (D-09/D-10)

Call `deriveBackendSpec(output.pages)` from `lib/spec-parser/derive-backend-spec.ts`. Auto-generation always runs when UI spec exists. If user also pastes a backend spec, show derived vs pasted and let user reconcile.

```
import { deriveBackendSpec } from "lib/spec-parser/derive-backend-spec.ts";

const backendSpec = await deriveBackendSpec(output.pages);
```

### 5. Backend-only concerns (D-12)

After auto-derivation, ask user: "Are there backend-only concerns not visible from the UI? (webhooks, cron jobs, third-party integrations, background tasks)" Append overrides to backendSpec.

## Confirmation Gate (D-03, D-04)

Before persisting ANYTHING to Neon, display the full restructured spec to the user.

**Provenance display (addresses HIGH review concern):** For each page and component, display items with their `source` field clearly marked:

- Items with `source: "explicit"` — show normally, these came from the user's input
- Items with `source: "inferred"` — prefix with `[INFERRED]` marker or use blockquote formatting to visually distinguish AI-added content from user-explicit content

Example display format:

```
Pages in your spec:
1. Dashboard (/dashboard) — authenticated — explicit from your input
2. [INFERRED] Login (/login) — public — added to support authenticated flows
3. [INFERRED] 404 (/404) — public — standard error page

Shared Components:
- Sidebar — used by: /dashboard, /settings — [INFERRED]
```

Show:
- The suggested generation order (`suggestedOrder` array) (D-15)
- Shared components with their deduplication merges (D-22)
- The derived backend spec with provenance markers

User options:
- **"approve"** — proceed to persistence
- **"edit [page name or route]"** — surgical edit via spec-editor module
- **"redo"** — re-interpret from scratch

On **"edit"**: use `applySpecEdit` from `lib/spec-parser/spec-editor.ts` for surgical edit (D-16), which bumps `specVersion` automatically. Then call `flagDependentPages` to identify affected pages and re-show only the changed page + dependent pages for confirmation.

```
import { applySpecEdit, flagDependentPages } from "lib/spec-parser/spec-editor.ts";

const updatedSpec = applySpecEdit(spec, targetRoute, updatedPage);
const dependentRoutes = flagDependentPages(spec, targetRoute);
// Show confirmation for: targetRoute + dependentRoutes only
```

On **"approve"**: persist to Neon pipeline_pages table.

## Persistence

After user confirms:

1. Create `pipeline_run` row with `phase="spec"`, `status="complete"`
2. For each page in `SpecOutput.pages`: insert `pipeline_pages` row with `output=JSON.stringify(page)`, `status="complete"`
3. Store SpecOutput as the phase output for the orchestrator to hand off to Phase 3

**Future consideration:** Collaborative flow state is currently held in conversation context. For cross-session resume, CollaborativeState could be serialized to `pipeline_runs.output` as JSON. Not implemented in v1.

## Spec Editing (D-16/D-17/D-18/D-19)

When user requests a spec edit after initial confirmation:

1. Accept page name or route to edit
2. Call `applySpecEdit(spec, targetRoute, updatedPage)` from `lib/spec-parser/spec-editor.ts` — handles version bumping (D-16)
3. Call `flagDependentPages(spec, editedRoute)` — returns routes of pages that depend on the edited page (D-17)
4. Show confirmation gate for affected pages only (edited page + flagged dependents)
5. Update `pipeline_pages` status to `"spec-changed"` for the edited page (D-19)
6. Pages with no relationship to the change are untouched (D-18)

## Gap Analysis (Spec Intelligence)

After the spec is restructured and before it is locked, a gap analyzer challenges the spec:

```typescript
import { analyzeGaps, hasBlockingGaps } from "lib/spec-parser/gap-analyzer.ts";
import { formatGapReport } from "lib/spec-parser/spec-approval.ts";

const gaps = await analyzeGaps(spec);
const report = formatGapReport(spec, gaps);

if (hasBlockingGaps(gaps)) {
  // Pipeline stops — user must resolve blocking gaps
  throw new SpecBlockedByGapsError(report);
}
// Non-blocking gaps are logged but don't halt the pipeline
```

### Severity Levels

| Severity | Meaning | Pipeline behavior |
|----------|---------|-------------------|
| **blocking** | Must fix before proceeding | Pipeline throws `SpecBlockedByGapsError` |
| **recommended** | Should fix, but won't halt | Logged in GAP-ANALYSIS.md, pipeline continues |
| **optional** | Nice to have | Logged only |

### What Gets Checked

- **Missing onboarding**: signup exists but no onboarding/welcome page → blocking
- **Auth gaps**: authenticated pages + signup but no password reset → blocking
- **Orphaned routes**: page depends on a route not in the spec → blocking
- **Missing 404**: no not-found page → recommended
- **Missing profile/settings**: authenticated app with no account page → recommended
- **Missing empty states**: pages with data but no emptyState → recommended per page
- **Missing error states**: pages with APIs but no errorState → recommended per page
- **Missing mobile considerations**: complex layouts with no mobile notes → optional
- **LLM contextual analysis**: Claude reviews the spec and suggests missing flows for this product type → optional

### Override

Set `SKIP_GAP_ANALYSIS=true` in `.env` to bypass gap analysis entirely. Not recommended — the checks exist to catch real gaps before they become expensive rework downstream.

### Output

Gap analysis report is saved to `.planning/output/spec/GAP-ANALYSIS.md` regardless of severity.

## Contracts

- **Input:** raw text (any format) OR collaborative conversation
- **Output:** `SpecOutput` from `shared/spec-schema.ts` — validated by `SpecOutputSchema.parse()`
- **Layers:** `PageSpecCore` (all phases), `PageSpecUI` (Phase 3-4), `PageSpecData` (Phase 5), `PageSpecAnalytics` (Phase 6)
- **Composition:** Downstream phases use `PageSpecCore.merge(PageSpecUI)` etc. to get only their fields
- **Provenance:** Every page, component, endpoint, and event carries `source: "explicit" | "inferred"` via `SpecItemSource`

## Dependencies

- `lib/spec-parser/parse-spec.ts` — paste path entry point (with MAX_RAW_INPUT_SIZE size guard)
- `lib/spec-parser/restructure-spec.ts` — AI restructuring engine (with provenance in system prompt)
- `lib/spec-parser/collaborative-flow.ts` — guided creation state machine (QUESTION_SEQUENCE, createInitialState, buildSystemPromptForStage, isFlowComplete, extractSpecFromConversation)
- `lib/spec-parser/spec-editor.ts` — surgical editing with version bumping and dependency flagging (applySpecEdit, flagDependentPages, markProvenance)
- `lib/spec-parser/derive-backend-spec.ts` — backend spec auto-derivation (with provenance propagation)
- `lib/spec-parser/deduplicate-components.ts` — shared component dedup (with provenance preservation)
- `lib/spec-parser/chunk-spec.ts` — large spec chunking: chunkRawText (pre-chunking raw text before AI calls) and chunkSpecByDomain (post-parse page chunking for large specs)
- `lib/spec-parser/gap-analyzer.ts` — static + LLM gap detection (analyzeGaps, hasBlockingGaps)
- `lib/spec-parser/spec-approval.ts` — gap report formatting (formatGapReport, hasBlockingGaps re-export)
- `shared/spec-schema.ts` — all Zod contracts including SpecItemSource, SpecOutputSchema, PageSpecFull

## Relationship to Intake Phase

As of the unified intake system, spec is now produced BY `lib/intake/intake-orchestrator.ts` for docs-only and existing-codebase modes. The intake orchestrator calls `restructureSpec()`, `deriveBackendSpec()`, and `analyzeGaps()` internally. Spec-parser modules remain the building blocks — intake is the new entry point that wraps them with product metadata, brand voice, tech stack, and deployment context into a complete `ProjectBrief`.

For greenfield projects (no docs, no code), the collaborative flow in `collaborative-flow.ts` is still the primary interaction path, called from within the intake conversation.

## Sub-Skill Of

`saas-dev:orchestrator` (phase: spec, intake)
