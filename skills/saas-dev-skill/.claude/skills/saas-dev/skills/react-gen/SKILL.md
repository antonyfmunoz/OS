---
name: saas-dev:react-gen
description: Direct React component generation via Claude. Replaces the former Stitch-based UI generation. Writes production-ready .tsx files with design token enforcement, self-review, and live Vite preview.
---

# saas-dev:react-gen

Generates production-ready React/TypeScript page components directly via Claude API. No intermediate HTML, no external UI service — Claude writes the final .tsx file that Vite hot-reloads into the browser.

## Architecture

### Design Token Enforcement

All components are generated against mandatory design rules defined in `lib/react-gen/design-tokens.ts`:

- Solid primary (#6a37d4), no gradients
- Glassmorphism on floating elements
- Ambient shadow only (0 8px 32px rgba(106,55,212,0.08))
- No 1px borders — background shifts instead
- Inter font exclusively
- lucide-react icons exclusively
- shadcn/ui primitives for base components
- 12px border radius
- No pure black — #2c2f30 for text

### Shared Components First

Before any page is generated, 7 shared layout components are built sequentially:

1. `client/src/lib/design-tokens.ts` — CSS variable exports
2. `client/src/components/agent-chat-stub.tsx` — chat interface
3. `client/src/components/floating-ai-panel.tsx` — sticky AI panel
4. `client/src/components/left-rail.tsx` — nav sidebar
5. `client/src/components/right-rail.tsx` — AI assistant panel
6. `client/src/components/header.tsx` — glassmorphism navbar
7. `client/src/components/universal-layout.tsx` — full layout shell

Each is written to disk immediately so the next component can import the previous.

### Parallel Page Generation

Pages are generated in parallel (p-limit 5). Each page:

1. Claude receives: page spec + page copy + design rules + design system + brand voice + shared component paths
2. Output validated: default export, no banned imports, no gradients, no pure black, not truncated
3. If validation fails: retry once with specific failure reasons
4. Self-review by Claude Haiku: scored 0-1 against design rules, spec, copy, completeness
5. If score < 0.8 and not already retried: regenerate with review feedback
6. File written to `client/src/pages/{kebab-name}-page.tsx`
7. Vite hot-reloads — page appears in browser

### Self-Review

Every generated component gets a design review from Claude Haiku scoring:
- Design rules compliance
- Spec compliance (correct components, data, routing)
- Copy compliance (exact headings, CTAs, empty states from copy phase)
- Completeness (loading, error, empty states; mobile responsive)

Score ≥ 0.8 = pass. Below triggers one regeneration attempt with specific feedback.

### Edit Mode

After the build, `lib/react-gen/edit-mode.ts` enables surgical edits:
- Read current component
- Send current code + user instruction + design rules to Claude
- Write updated file
- Vite hot-reloads instantly

## Key Files

- `lib/react-gen/design-tokens.ts` — token constants + mandatory rules
- `lib/react-gen/component-writer.ts` — single page generation + validation + self-review
- `lib/react-gen/shared-component-builder.ts` — sequential shared component generation
- `lib/react-gen/live-preview-server.ts` — Vite dev server management
- `lib/react-gen/build-status-overlay.ts` — real-time build progress overlay
- `lib/react-gen/edit-mode.ts` — post-build surgical edits
- `lib/orchestrator/phases/react-gen-adapter.ts` — orchestrator phase implementation
