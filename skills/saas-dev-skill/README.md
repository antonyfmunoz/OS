# saas-dev-skill

AI product engineering team — takes a SaaS product from spec to deployed app via coordinated Claude agents.

## What it does

A multi-agent pipeline that builds complete SaaS products:

1. **Product Intel Agent** — analyzes your product brief, researches competitors, identifies market positioning
2. **Architecture Agent** — designs data model, API contracts, page structure, component hierarchy (extends existing codebase, doesn't replace it)
3. **Design System Agent** — researches animation/component libraries for your product, generates tokens, Tailwind config, CSS variables, component design guide
4. **Copy Agent** — writes all UI copy (headings, CTAs, empty states, error messages) matched to brand voice
5. **Component Library Agent** — builds shared components with design system tokens baked in
6. **Page Agents** — generates every page in parallel (p-limit 5) with full design system, copy, and component context
7. **Backend Agent** — generates Express routes, Drizzle schemas, storage methods, and migrations
8. **QA Agent** — runs tsc, import validation, null-safety scans, state pattern checks, design consistency analysis, and auto-fixes issues

### Key features

- **User Supremacy** — explicit user constraints (colors, fonts, rules) are LAW. Agents have creative freedom only in areas the user didn't specify.
- **Pre-flight checks** — validates env vars, database URL, and TypeScript compilation before running any agent.
- **Codebase audit** — scans existing routes, tables, pages, and storage methods before designing architecture. Extends, doesn't replace.
- **QA as hard gate** — build reports FAILED if QA doesn't pass. No silent success.
- **Coherence review** — after each wave, reviews creative decisions against user constraints for consistency.
- **Targeted fix mode** — re-run only failed phases instead of full rebuild.

## Installation

```bash
# Clone into your project's parent directory
git clone <repo-url> saas-dev-skill
cd saas-dev-skill
npm install

# Copy .env.example to .env and fill in your keys
cp .env.example .env
```

## Usage

### Full build (from your SaaS project directory)

```bash
npx tsx path/to/saas-dev-skill/scripts/saas-dev-build.ts
```

### Targeted fix (re-run only failed phases)

```bash
npx tsx path/to/saas-dev-skill/scripts/saas-dev-fix.ts
```

### As a Claude Code skill

The `.claude/skills/saas-dev/` directory contains skill definitions that Claude Code discovers automatically. Copy or symlink the skills directory into your project's `.claude/skills/`.

## What it produces

In your project directory:

- `client/src/pages/*.tsx` — React page components
- `client/src/components/shared/*.tsx` — shared components
- `client/src/styles/design-system.css` — CSS custom properties
- `client/src/lib/design-tokens.ts` — TypeScript design contract
- `server/generated/routes/*.ts` — Express route handlers
- `server/generated/storage/*.ts` — storage methods
- `server/generated/schema.ts` — Drizzle table schemas
- `tailwind.config.ts` — updated with design tokens
- `.planning/artifacts/` — build state, QA reports, agent results
- `.planning/output/migrations/*.sql` — database migration SQL

## Requirements

- Node.js 20+
- Anthropic API key (Claude Sonnet 4.5 for generation, Haiku 4.5 for review/research)
- PostgreSQL database URL (for backend generation)
- An existing or new React + Vite + Tailwind + shadcn/ui project

## Tech stack

- TypeScript, Node.js
- Anthropic Claude API (multi-model: Sonnet for generation, Haiku for fast tasks)
- Drizzle ORM for schema generation
- Zod for validation
- p-limit for parallel agent execution
- Playwright (optional) for screenshot-based visual QA
