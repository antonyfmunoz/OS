# UMH Deployment Guide

## Requirements
- Python 3.11+
- Linux (tested on Ubuntu 22.04+)
- ~100MB disk for runtime data
- No external services required (SQLite-backed)

## Quick Start

### 1. Install dependencies
```
pip install fastapi uvicorn pydantic
```

### 2. Set environment variables
```
export UMH_API_KEY="your-secret-api-key"
export UMH_API_PORT=8000
```

### 3. Start in production mode
```
./scripts/run_prod.sh
```

### 4. Access
- UI: http://localhost:8000/ui/
- API: http://localhost:8000/
- Health: http://localhost:8000/health

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| UMH_API_PORT | 8000 | API server port |
| UMH_API_HOST | 127.0.0.1 | API bind address |
| UMH_API_KEY | (required) | API authentication key |
| UMH_DB_PATH | data/runtime/tasks.sqlite | Task database path |
| UMH_WORKER_AUTO_START | true | Auto-start background worker |
| UMH_WORKER_INTERVAL | 2.0 | Worker poll interval (seconds) |
| UMH_LEASE_TIMEOUT | 300.0 | Stuck task detection timeout |
| UMH_LOG_DIR | data/logs | Log directory |
| UMH_LOG_LEVEL | INFO | Logging level |
| UMH_TASK_BACKEND | sqlite | Task backend (sqlite/memory) |

## Running with tmux (recommended)

```
tmux new -d -s umh ./scripts/run_prod.sh
tmux attach -t umh  # to view
Ctrl+B D             # to detach
```

## Running with systemd

Create `/etc/systemd/system/umh.service`:

```ini
[Unit]
Description=UMH Control Plane
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/OS
Environment=UMH_API_KEY=your-secret-api-key
Environment=UMH_WORKER_AUTO_START=true
ExecStart=/opt/OS/scripts/run_prod.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```
systemctl daemon-reload
systemctl enable umh
systemctl start umh
```

## Monitoring

```
./scripts/healthcheck.sh
```

## Logs

```
tail -f data/logs/umh_api.log     # all API activity
tail -f data/logs/umh_worker.log  # worker activity
tail -f data/logs/umh_errors.log  # errors only
tail -f data/logs/umh_server.log  # uvicorn output
```

## Data

SQLite databases in `data/runtime/`:
- `tasks.sqlite` -- task state (survives restart)
- `approvals.sqlite` -- approval state

## Backup

```
cp data/runtime/*.sqlite /path/to/backup/
```

## Troubleshooting

### API won't start
- Check port not in use: `lsof -i :8000`
- Check Python version: `python3 --version` (need 3.11+)
- Check dependencies: `pip list | grep fastapi`

### Worker not running
- Check: `curl http://localhost:8000/worker/health`
- Check logs: `tail data/logs/umh_worker.log`

### Tasks stuck
- Worker detects stuck tasks (>5min) automatically
- Manual: check `GET /tasks` for RUNNING tasks with old timestamps
