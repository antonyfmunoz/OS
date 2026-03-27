Check full EOS system status.

Run these in sequence:
1. docker ps --format "table {{.Names}}\t{{.Status}}"
2. python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from eos_ai.session_state import SessionState
print(SessionState.get_resume_context())
"
3. curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; data=json.load(sys.stdin); print('Ollama models:', [m['name'] for m in data.get('models',[])])"

Report: which services are running, current
stage, active models, any errors.
