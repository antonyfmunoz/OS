# UMH Port Map

| Port | Service | Owner | Status |
|------|---------|-------|--------|
| 8091 | Operator API | services/operator_api.py (Docker) | OCCUPIED — **PROTECTED, DO NOT TOUCH** |
| 8092 | Operator UI | operator-ui (three-fronts worktree) | OCCUPIED — tsx dev server |
| 8093 | **UMH Backend** | umh_mvp/api/app.py (uvicorn) | **JARVIS TARGET** |
| 5173 | **UMH Frontend** | frontend/ (Vite dev server) | **JARVIS TARGET** |
| 11434 | Ollama | ollama server | Used by local model routing |

## Conflict Notes

- Port 8091 is Docker-managed and must never be touched by UMH
- Port 8092 was originally considered for UMH but is occupied by operator-ui
- Port 8093 was selected as the UMH backend port (no conflict)
- Port 5173 is the standard Vite dev port (no conflict)
- Ollama on 11434 is used by local-first model routing capabilities

## Tailscale Access

All ports are accessible via Tailscale private network:

| Device | IP | Access |
|--------|-----|--------|
| VPS | 100.77.233.50 | Direct (services run here) |
| Windows Desktop | 100.74.199.102 | Frontend dev + browser access |
| iPad Pro | 100.98.71.38 | Browser access via VPS IP |
| iPhone 15 Pro Max | 100.108.75.25 | Browser access via VPS IP |

Access frontend from any device: `http://100.77.233.50:5173`
Access API from any device: `http://100.77.233.50:8093/api/umh/health`
