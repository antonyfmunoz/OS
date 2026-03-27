Rebuild Docker containers that need it, verify all imports are clean, restart services, confirm Docker ps shows all healthy.

Protocol:

1. CHECK current Docker status:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```

2. CHECK for import errors before rebuilding — don't rebuild a broken image:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '/opt/OS')
   modules = [
     ('eos_ai.agent_runtime', 'AgentRuntime'),
     ('eos_ai.cognitive_loop', 'CognitiveLoop'),
     ('eos_ai.authority_engine', 'AuthorityEngine'),
     ('eos_ai.memory', 'AgentMemory'),
   ]
   for mod, cls in modules:
     try:
       m = __import__(mod, fromlist=[cls])
       getattr(m, cls)
       print(f'  PASS {mod}')
     except Exception as e:
       print(f'  FAIL {mod}: {e}')
   "
   ```

3. If imports fail: run /eos-fix first before deploying

4. REBUILD and restart:
   ```bash
   cd /opt/OS && docker compose down && docker compose up -d --build
   ```

5. WAIT for containers to start (30 seconds), then verify:
   ```bash
   sleep 30 && docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

6. CHECK logs for startup errors:
   ```bash
   docker compose logs --tail=50
   ```

7. RESTART Telegram bot if needed (runs outside Docker):
   ```bash
   pkill -f telegram_control; sleep 2
   nohup python3 /opt/OS/13_Scripts/telegram_control.py >> /opt/OS/logs/telegram.log 2>&1 &
   sleep 3 && pgrep -f telegram_control && echo "Telegram: running" || echo "Telegram: FAILED"
   ```

8. CONFIRM all services healthy — report any container in unhealthy or exited state
