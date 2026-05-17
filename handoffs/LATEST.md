# Handoffs — Three Fronts Sprint

## FRONT 2 — Gateway CognitiveLoop Fallback Removal
- [SHELVED] Analysis complete. 8 gaps prevent safe removal. See docs/changes/gateway_cogloop_removal.md
- ExecutionSpine covers core LLM path but missing: post-response side effects, quality gate, prompt enhancement, quality retry, stage filter, response footer, multimodal, portfolio injection
- Revisit post-MVP as dedicated session

## FRONT 1 — Autonomous Ingestion
- [DONE] scripts/obsidian_rsync.sh — cron-ready, needs TAILSCALE_IP/USER/PATH filled in
- [DONE] scripts/github_trinity_ingest.py — clone + ingest via GenericIngestionOrchestrator
- [DONE] scripts/gws_scanner_cron.py — thin wrapper for existing GWSDocumentScanner
- [DONE] adapters/browser_exports/ — export agents for claude/chatgpt/instagram
- [DONE] scripts/fire_export.py — headless/non-headless runner with MFA detection + bridge callback
- [DONE] scripts/fire_exports_windows.ps1 — Windows PowerShell wrapper (persistent profiles)
- [DONE] scripts/export_pipeline.py — Gmail poller → auto-download → route to parser → ingest. Cron-ready.
- [DONE] services/trigger_export.py — VPS-side trigger (CLI + importable)
- [DONE] services/export_bridge_handler.py — Windows-side handler (/fire-export, /mfa-response)
- [DONE] operator-ui/src/server/routes/export.ts — HTTP trigger endpoint POST /api/export/fire
- [DONE] cc_webhook_receiver.py extended — /mfa-challenge handler surfaces to Discord
- [DONE] local_bridge_client.py extended — send_mfa_response() for MFA code delivery
- [DONE] local_bridge_server.py extended — register_routes() loads export_bridge_handler
- [DONE] discord_bot.py extended — !mfa <service> <code> + !fire_export <service> commands
- [DONE] services/bridge_health.py — VPS watchdog (ensure_bridge_live + SSH autostart)
- [DONE] docs/setup/windows_bridge_autostart.md — schtasks install + lifecycle pattern
- [DONE] scripts/test_bridge_lifecycle.sh — chaos test (kill bridge → verify auto-recovery)
- [DONE] trigger_export.py integrates watchdog — transparent recovery before dispatch
- [GATE] MFA login pass needed per service before first export (one-time, phone tap)
- [GATE] Tailscale SSH: run `tailscale set --ssh` on Windows once (watchdog surfaces gate)

## FRONT 3 — Code View v1.5
- [DONE] operator-ui/ — React 18 + Vite + Tailwind + Monaco Editor
- [DONE] CodeView layout: file tree (left), Monaco editor (center), terminal (right)
- [DONE] Hono backend: /api/code/read, /api/code/write, /api/code/execute, /api/code/list
- [DONE] safePath() traversal protection — blocks ../../ escapes
- [DONE] Auth: CLAUDE_CODE_OAUTH_TOKEN header when configured, open in dev mode
- [DONE] os-operator Docker service in docker-compose.yml, port 8091, node:20-slim
- [DONE] E2E test: scripts/test_code_view_e2e.sh — 4/4 passed (health, read, execute, list)
- [DONE] saas-dev-skill wired to claude -p subprocess (Max subscription, zero API cost)
- [DONE] lib/claude-subprocess.ts — drop-in Anthropic SDK replacement, OAuth token auth
- [DONE] All 21 constructor calls across 20 files replaced, 0 TypeScript errors from changes
- [DONE] E2E verified: messages.create (Haiku) + messages.stream (Sonnet) both pass
- [NOTE] AUTH.md documents the auth path and gate clearly
