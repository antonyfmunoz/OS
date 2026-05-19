# UMH Cockpit Shell — Discovery Report

**Session:** A (Cockpit / WorldView UI)
**Date:** 2026-05-18
**Worktree:** cockpit-shell

## Environment Discovery

### Frontend Stack
- React 19.2.6
- Vite 8.0.12
- TypeScript 6.0.2
- Tailwind CSS 4.3.0 (CSS-first via @tailwindcss/vite plugin)
- Zustand 5.0.13 (state management)
- Lucide React 1.16.0 (icons)
- clsx 2.1.1 (classname composition)

### Existing Frontend
- `/opt/OS/frontend/` — 3-view prototype (Chat, Knowledge, System) on port 5173
- React 19 + Vite 8 + Tailwind 4 — same stack
- NOT modified or overwritten

### Existing Services
- Port 8091: operator_api.py (untouched)
- Port 8092: three-fronts operator-ui (untouched)
- Port 8093: Jarvis API (from umh-mvp session, untouched)
- Port 5174: NEW cockpit shell (this session)

### Protected Files
- No protected files modified
- No existing services overwritten
- No backend dependencies

### Architecture Decisions
1. **New app at `jarvis/jarvis_web/`** — clean separation from existing frontend prototype
2. **Port 5174** — avoids collision with existing 5173 dev server
3. **No path aliases** — TS 6 deprecates `baseUrl`/`paths`; relative imports are forward-compatible
4. **Tailwind 4 CSS-first config** — no tailwind.config.js; all theme tokens via `@theme` blocks
5. **Mock data first** — all views render with mock data, no backend required
6. **Zustand over Redux** — single-store pattern matches cockpit's global state model
7. **No routing library** — simple state-driven view switching; appropriate for a single-page cockpit shell
