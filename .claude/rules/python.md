---
globs: ["eos_ai/**", "services/**", "scripts/**", "orchestrator/**"]
---

# Python Rules for EOS

- Python 3.11+ syntax only
- All DB calls via psycopg2 through Neon
- sys.path.insert(0, '/opt/OS') before imports
- load_dotenv('/opt/OS/eos_ai/.env') for env vars
- Never catch Exception silently — always log
- Type hints on all public functions
- Docstrings on all classes and public methods
- After editing: python3 -m py_compile $file
- Run ruff format after every Python file edit
- Never hardcode API keys — always os.getenv()
- All new modules: add to eos_ai/__init__.py
  if they expose a public interface
