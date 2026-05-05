---
name: saas-dev:orchestrator
description: Orchestrates the SaaS development pipeline from spec to deployment. Runs direct React generation with live Vite preview. Single entry point builds the full app.
---

# saas-dev:orchestrator

Orchestrates the complete SaaS development pipeline. One command takes a product from spec to deployed app with live preview.

## Pipeline Phases

1. **spec** — Parse or collaboratively create a page spec from PRD/requirements. Produces validated SpecOutput consumed by all downstream phases.
2. **copy** — Generate all UI copy in one pass for cross-page voice coherence. Brand voice applied, reviewed, persisted.
3. **react-gen** — Generate React/TypeScript page components directly via Claude. Writes .tsx files to disk — Vite hot-reloads them into the browser as each completes. Shared layout components built first (sequential), then pages in parallel (p-limit 5).
4. **integration** — Route injection, nav wiring, shadcn component installation. Handles brownfield merges.
5. **backend** — Generate API routes, schemas, and run database migrations.
6. **deploy** — Instrument analytics and deploy the application.

## Single Entry Point

```bash
npx tsx scripts/saas-dev-build.ts
```

Full flow:
1. Run intake (auto-detects mode: greenfield/docs/existing)
2. Run spec phase — parse and validate
3. Run copy phase — generate brand-voice-aligned copy
4. Start Vite dev server — live preview URL printed
5. Build shared components (sequential): design-tokens, agent-chat-stub, floating-ai-panel, left-rail, right-rail, header, universal-layout
6. Build pages (parallel, p-limit 5) — each appears in browser as it completes
7. Run integration phase — routes, nav, shadcn
8. Run backend phase — API endpoints
9. Print completion summary

## Live Preview

The react-gen phase starts a Vite dev server before generating any components. As each page file is written to `client/src/pages/`, Vite hot-reloads it into the browser. A build status overlay shows real-time progress (bottom-right corner, auto-removed on completion).

## Edit Mode

After the build completes, describe changes in the Claude Code chat. The edit-mode system reads the current component, applies surgical changes via Claude, and writes the updated file — Vite hot-reloads instantly.

## State Management

- Pipeline state persisted in Neon PostgreSQL (pipeline_runs + pipeline_pages tables)
- Each page tracks its own checkpoint within each phase
- Resuming a paused run continues from last completed page
- Failed pages include an error field for retry context

## Project Config

Required fields validated by ProjectConfigSchema in shared/design-schema.ts:

- `projectId` — unique identifier for the project
- `repoPath` — absolute path to the project repository
- `framework` — detected framework enum (currently only "react-vite-tailwind-shadcn")
