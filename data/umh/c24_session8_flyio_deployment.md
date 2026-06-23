# C24 Session 8: Flyio Deployment

Generated via UMH governed development loop
Latency: 113771ms | Elapsed: 117s

Both files are created. Here's a summary:

---

### `fly.toml` highlights
- **Region:** `sea` (Seattle â€” closest to Portland)
- **Internal port:** 8080
- **Health check:** `GET /api/health` every 30s
- **Auto-scaling:** suspend idle machines, min 1 running, soft/hard connection limits at 200/250
- **VM:** `shared-cpu-1x` / 512MB (cheapest tier, upgrade as needed)

### `Dockerfile` highlights
- **Multi-stage build** â€” builder stage compiles everything, production stage only has runtime deps
- **Native deps handled** â€” `python3 make g++` installed for `bcrypt`, purged after `npm ci`
- **VITE_ build args** â€” Firebase keys (and future Clerk/PostHog) passed at build time so Vite bakes them into the frontend bundle
- **Drizzle schema sync** â€” copies `drizzle.config.ts`, `shared/`, and `tsconfig.json` since `server/index.ts:ensureDatabaseSchema()` runs `npx drizzle-kit push` at startup

### Required action before deploying

**Fix the host binding** in `server/index.ts:256` â€” change `127.0.0.1` to `0.0.0.0`:

```ts
server.listen({ port, host: "0.0.0.0" });
```

Fly.io routes traffic to the container's internal port, so the server must listen on all interfaces. Want me to make that change now?

### Deployment commands
```bash
# Set secrets (one-time)
fly secrets set DATABASE_URL="..." SESSION_SECRET="..." FIREBASE_SERVICE_ACCOUNT_KEY="..."

# Deploy with VITE_ build args
fly deploy \
  --build-arg VITE_FIREBASE_API_KEY=... \
  --build-arg VITE_FIREBASE_APP_ID=... \
  --build-arg VITE_FIREBASE_AUTH_DOMAIN=lyfeos.net \
  --build-arg VITE_FIREBASE_PROJECT_ID=lyfeos-a55f4 \
  --build-arg VITE_FIREBASE_ACTUAL_PROJECT_ID=lyfeos-a55f4 \
  --build-arg VITE_FIREBASE_MESSAGING_SENDER_ID=76858514072
```