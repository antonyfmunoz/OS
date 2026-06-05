# Phase 14.7D — Sync Report

## Date: 2026-06-05

## Sync Operation
- Source: `cockpit/out/renderer/` (electron-vite build output)
- Destination: `cockpit/dist-web/` (StaticFiles served directory)
- Method: `cp -r` with old backup preserved at `cockpit/dist-web.bak.20260529/`

## Verification

### File Inventory
| File | Size | Hash Fragment |
|------|------|---------------|
| index.html | 327B | references CKsSa-e8 |
| assets/index-CKsSa-e8.js | 1.74 MB | content-hash in filename |
| assets/index-BoML2ien.css | 54.5 KB | content-hash in filename |

### Container Mount Verification
- Docker bind mount: `/opt/OS` → `/app`
- Container path: `/app/cockpit/dist-web/index.html`
- Verified via `docker exec os-operator cat /app/cockpit/dist-web/index.html`
- Container sees `index-CKsSa-e8.js` reference (matches new build)

### Server Restart
- `docker restart os-operator`
- Verified via `curl http://localhost:8091/` — returns HTML referencing `index-CKsSa-e8.js`

## Sync Status: COMPLETE
Old build (May 29, `index-_DW6Wo1o.js`) replaced with new build (June 5, `index-CKsSa-e8.js`).
