# saas-dev

End-to-end SaaS development skill system. Takes a product from spec → deployed app via 7 coordinated skills: spec-parser, detect-framework, ui-generator, integrator, backend-wirer, analytics-delivery, orchestrator.

## Install

1. Drop this `saas-dev/` directory into `.claude/skills/` of a target project.
2. Copy `templates/.env.example` → project root `.env` and fill in keys:
   - `ANTHROPIC_API_KEY` (required)
   - `STITCH_API_KEY` (required for ui-generator)
   - `DATABASE_URL` (Neon Postgres — required for design consistency memory)
3. Copy `templates/design-system.template.md` → `.planning/design-system.md` and customize tokens (colors, type scale, spacing, radii, motion).
4. Run the health check: `tsx scripts/verify.ts` (see below).
5. Invoke the orchestrator skill in Claude Code to start a run.

## MCPs required

- `magicui` — component registry queries
- `magic21` (21st.dev) — component inspiration
- `playwright` — preview server interaction
- `neon` — design consistency DB

If any are missing, `spec-parser` and `ui-generator` will warn and degrade gracefully (no hard failure).

## Framework support (v1)

React + Vite + Tailwind + shadcn/ui in a monorepo layout (`client/`, `server/`, `shared/`). `detect-framework` will bail out on anything else in v1.

## Health check

```
tsx scripts/verify.ts
```

Reports: required env vars, MCP availability, template presence, framework detection.

## Layout

- `skills/*/SKILL.md` — the 7 skill entry points
- `lib/` (in project root) — implementation libraries consumed by skills
- `templates/` — starter files (design system, .env, spec)
- `scripts/setup.ts` — first-run installer
- `scripts/verify.ts` — health check
