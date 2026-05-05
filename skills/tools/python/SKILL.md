---
name: python
description: "Use when writing, modifying, or debugging Python code in the EOS codebase — covers async patterns, type hints, namespace packages, psycopg2 idioms, dotenv conventions, and error handling patterns specific to EOS."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.python.org/3.12/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Python 3.12"
sdk_version: "psycopg2-binary, python-dotenv, asyncio"
speed_category: stable
trigger: both
effort: medium
context: fork
---

# Tool: Python

## What This Tool Does

Python 3.12 is the primary language for the EOS intelligence layer. Every AI agent, every database call, every LLM routing decision, and every service bot is written in Python. The codebase has 112+ modules across `eos_ai/` (core intelligence), `services/` (bots), and `scripts/` (automation).

Key roles Python fills in EOS:
- **LLM orchestration** — multi-model routing through Anthropic, Gemini, Groq, Perplexity, Ollama
- **Database layer** — psycopg2 to Neon PostgreSQL with RLS tenant isolation
- **Agent runtime** — task-type-aware model selection, skill injection, memory persistence
- **Cognitive loop** — 8-stage Perceive/Understand/Plan/Execute/Verify/Reflect/Learn/Store cycle
- **Service bots** — Discord (py-cord), Telegram (python-telegram-bot)
- **Scheduled automation** — cron-invoked scripts via `claude -p` and direct Python execution

## EOS Integration

### sys.path convention
Every EOS Python file that imports from `eos_ai` must insert the repo root into `sys.path` before any EOS imports. Two patterns exist:

**Scripts and services (outside eos_ai/):**
```python
import sys
sys.path.insert(0, '/opt/OS')
```

**Modules inside eos_ai/ (relative):**
```python
import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
```

### Namespace packages
`eos_ai` uses implicit namespace packages — there is NO `__init__.py`. This means:
- Imports work via `from eos_ai.module import Class` when `/opt/OS` is on sys.path
- If `/opt/OS` is not on sys.path, imports silently fail with `ModuleNotFoundError`
- Never create an `__init__.py` in `eos_ai/` — it would break the existing pattern

### dotenv loading
Two `.env` files exist with different scopes:
- `eos_ai/.env` — DATABASE_URL, EOS_ORG_ID, EOS_USER_ID, ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, PERPLEXITY_API_KEY
- `services/.env` — DISCORD_BOT_TOKEN, FOUNDER_DISCORD_ID, channel IDs, bot-specific tokens

Load pattern (using `pathlib.Path` for reliability):
```python
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
```

Services that need both (like discord_bot.py) load both:
```python
load_dotenv(_SCRIPT_DIR / ".env")
load_dotenv(_REPO_ROOT / "eos_ai" / ".env")
```

`load_dotenv` is idempotent — safe to call multiple times.

## Authentication

Python itself does not authenticate. EOS handles API key management through dotenv:
- All API keys stored in `.env` files (never committed, in `.gitignore`)
- Keys accessed via `os.environ["KEY"]` or `os.getenv("KEY")`
- Never hardcode API keys — always `os.getenv()`
- Database credentials embedded in `DATABASE_URL` — psycopg2 parses the connection string
- Credential stripping in error handlers: `re.sub(r'://[^@]+@', '://***:***@', str(e))`

## Quick Reference

### psycopg2 connection pattern (from db.py)
```python
from eos_ai.db import get_conn

with get_conn() as cur:
    cur.execute("SELECT id FROM interactions LIMIT 5")
    rows = cur.fetchall()
    # cur is a RealDictCursor — rows are dicts
    # RLS is already set via SET LOCAL app.current_org_id
    # Transaction auto-commits on clean exit, rolls back on exception
```

### Async function patterns (from cognitive_loop.py, discord_bot.py)
```python
# Discord bot uses asyncio event loop
import asyncio

# Custom exception handler for task-level errors
def _handle_task_exception(loop, context):
    exception = context.get("exception")
    if exception:
        msg = str(exception)
        if "_MissingSentinel" in msg:
            return  # silently ignore known voice WS errors
    loop.default_exception_handler(context)

# Async bot commands use py-cord's async decorators
@bot.command()
async def brief(ctx):
    result = await asyncio.to_thread(gateway.handle, request)
    await ctx.respond(result["output"])
```

### Type hint conventions
```python
# Use built-in generics (Python 3.12 — no need for typing.List, typing.Dict)
def resolve_venture(slug: str | None) -> str | None: ...

# Dataclasses for structured returns
@dataclass
class AgentResult:
    output: str
    model_used: str
    tokens_used: dict[str, int]
    skill_used: str | None
    interaction_id: int | None = None
    cost_usd: float = 0.0

# TYPE_CHECKING for circular import avoidance
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from eos_ai.agent_runtime import AgentResult
```

### Error handling patterns
```python
# Never catch Exception silently — always log or re-raise
try:
    conn = psycopg2.connect(_DATABASE_URL)
except Exception as e:
    safe_msg = re.sub(r'://[^@]+@', '://***:***@', str(e))
    raise psycopg2.OperationalError(f'Neon connection failed: {safe_msg}') from None

# Enhancement code uses pass-through — never block execution
try:
    past = self._memory.semantic_search(prompt)
except Exception:
    pass  # semantic retrieval is enhancement — never block execution

# Lazy imports to avoid circular dependency
def run(self, ...):
    from eos_ai.model_router import call_with_fallback as _router_call
```

### Print debugging pattern
```python
# EOS uses print() for operational logging (not logging module in most cases)
print(f"[AgentRuntime] User soul doc: {_user_soul_doc}")
print(f"[AgentRuntime] Warning: skill '{skill_name}' not found")
print(f"[RateLimiter] Minute limit hit: {org_id} — {minute_count}/min")
```

### Verification commands
```bash
# After every edit — compile check
python3 -m py_compile path/to/file.py

# After every edit — format
ruff format path/to/file.py

# Import verification
python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from eos_ai.module import Class; print('ok')"

# Full eos_ai import check
python3 -c "import sys; sys.path.insert(0, '/opt/OS'); import eos_ai; print('imports: clean')"
```

### Invocation from bash (cron/scripts)
```bash
# Inline Python for quick checks
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.session_state import SessionState
print(SessionState.get_resume_context())
"

# Heredoc for multi-line scripts in bash
python3 << 'EOF'
import sys, os
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
# ... script body
EOF
```

See references/best_practices.md for full patterns, anti-patterns, and Python 3.12 idioms.

## Gotchas

1. **sys.path must be inserted BEFORE any eos_ai imports.** The namespace package pattern means Python cannot find `eos_ai` without `/opt/OS` on sys.path. This is the #1 cause of import failures in new scripts. Always put `sys.path.insert(0, '/opt/OS')` as the first executable line after stdlib imports.

2. **No `__init__.py` in eos_ai/ — do not create one.** EOS uses implicit namespace packages. Adding `__init__.py` would change import resolution behavior and could break existing imports that rely on the namespace package pattern.

3. **Two `.env` files with different scopes.** `eos_ai/.env` has database and LLM API keys. `services/.env` has bot tokens and Discord IDs. Loading the wrong one means missing environment variables. Services that bridge both layers (discord_bot.py) must load both.

4. **asyncio event loop in Discord bot context.** py-cord runs its own event loop. Long-running synchronous EOS calls (gateway.handle, cognitive_loop.run) must be wrapped in `asyncio.to_thread()` to avoid blocking the bot. Voice WebSocket errors (`_MissingSentinel`, `poll_voice_ws`) must be caught at the event loop level via `set_exception_handler`, not in try/except.

5. **psycopg2 connection management — always use context manager.** The `get_conn()` context manager handles RLS setup (`SET LOCAL`), transaction commit/rollback, and connection cleanup. Never call `psycopg2.connect()` directly — always go through `get_conn()`. Connections are not pooled; each `with get_conn()` opens and closes a connection.

6. **ruff format required after every Python edit.** The codebase enforces consistent formatting via ruff. Run `ruff format path/to/file.py` after every edit before committing. Also run `python3 -m py_compile` to catch syntax errors.

7. **Circular imports — use lazy imports or TYPE_CHECKING.** Several modules have circular dependencies (agent_runtime <-> memory, cognitive_loop -> model_router). The pattern is: import inside the function body (`from eos_ai.model_router import call_with_fallback`) or use `TYPE_CHECKING` guard for type hints only.

8. **Credential leakage in error messages.** Database connection errors include the full `DATABASE_URL` with credentials. Always sanitize with `re.sub(r'://[^@]+@', '://***:***@', str(e))` before logging or re-raising.

9. **Docker bind-mount means no rebuild for Python changes.** Python files in eos_ai/ and services/ are bind-mounted into Docker containers. After editing, just `docker restart <container_name>` — do not rebuild the image. But if you change dependencies (requirements.txt), a full rebuild is needed.
