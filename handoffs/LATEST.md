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
- [DONE] scripts/fire_export.py — headless/non-headless runner with MFA detection
- [DONE] scripts/fire_exports_windows.ps1 — Windows PowerShell wrapper (non-headless)
- [GATE] Browser exports must run from Windows machine (VPS headless gets bot-blocked)
- [GATE] MFA login pass needed per service before first export
- [DONE] scripts/export_pipeline.py — Gmail poller → auto-download → route to parser → ingest. Cron-ready.
- [DONE] scripts/fire_exports_windows.ps1 — non-headless PowerShell wrapper for Windows

## FRONT 3 — Code View v1.5
- [DONE] operator-ui/ — React 18 + Vite + Tailwind + Monaco Editor
- [DONE] CodeView layout: file tree (left), Monaco editor (center), terminal (right)
- [DONE] Hono backend: /api/code/read, /api/code/write, /api/code/execute, /api/code/list
- [DONE] safePath() traversal protection — blocks ../../ escapes
- [DONE] Auth: CLAUDE_CODE_OAUTH_TOKEN header when configured, open in dev mode
- [DONE] os-operator Docker service in docker-compose.yml, port 8091, node:20-slim
- [DONE] E2E test: scripts/test_code_view_e2e.sh — 4/4 passed (health, read, execute, list)
- [GATE] AI-powered features (saas-dev-skill Claude API calls) blocked until Anthropic credits restored
- [NOTE] AUTH.md documents the auth path and gate clearly
