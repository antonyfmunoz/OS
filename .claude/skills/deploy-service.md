# How to Deploy EOS Service Changes

## Decision tree

Python file changed (no Dockerfile change):
  docker compose restart [service]
  sleep 15
  docker logs [service] --tail 10

requirements.txt changed:
  docker compose build --no-cache [service]
  docker compose up -d [service]
  sleep 20
  docker logs [service] --tail 10

## Always run first
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import eos_ai
print('imports: clean')
" 2>&1

## Services → files
os-discord  → 13_Scripts/discord_bot.py
os-bot      → 13_Scripts/telegram_control.py
os-monitor  → 13_Scripts/dm_monitor.py

## After deploy — verify
docker logs [service] --tail 10
Look for: "online" or "started"
Watch for: Error, Traceback, ImportError

## Never do
- Never restart all services at once
- Never rebuild unless Dockerfile changed
- Never deploy without import check
