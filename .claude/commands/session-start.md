Load full EOS context at start of session.

1. python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from substrate.state.session.session_state import SessionState
print(SessionState.get_resume_context())
"
2. docker ps --format "{{.Names}}: {{.Status}}"
3. curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print('Ollama:', [m['name'] for m in d.get('models',[])])"

Report full system state.
