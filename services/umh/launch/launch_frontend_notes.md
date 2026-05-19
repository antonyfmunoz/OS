# UMH Frontend — Launch Notes

The frontend is a React 19 + Vite 8 + Tailwind 4 application.
It runs on the **Windows desktop** (or any machine with Node.js).

## Quick Start (from repo root)

```bash
cd frontend
npm install
npm run dev
```

The dev server starts on **port 5173** with proxy to backend at **localhost:8093**.

## Cross-Device Access via Tailscale

The Vite config binds to `0.0.0.0`, so it's accessible from any
Tailscale device:

| Device | URL |
|--------|-----|
| VPS (localhost) | http://localhost:5173 |
| Windows desktop | http://100.74.199.102:5173 |
| iPad | Access via http://100.77.233.50:5173 (VPS) |
| iPhone | Access via http://100.77.233.50:5173 (VPS) |

## API Proxy

Vite proxies `/api/*` and `/ws` to `http://localhost:8093`.
If the backend runs on a different host (e.g., VPS via Tailscale),
update `vite.config.ts`:

```ts
proxy: {
  '/api': 'http://100.77.233.50:8093',
  '/ws': { target: 'ws://100.77.233.50:8093', ws: true }
}
```

## Production Build

```bash
npm run build
# Output: frontend/dist/
# Serve with: npx serve dist -l 5173
```

## Current Views

- **Dashboard** — system overview with governance stats
- **Signal** — submit signals to the pipeline
- **Traces** — execution trace browser
- **Work Packets** — work packet list and status
- **Governance** — pending approvals and decisions
- **Awareness** — global awareness aggregation
