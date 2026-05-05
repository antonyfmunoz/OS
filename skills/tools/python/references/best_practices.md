# Python — Creator-Level Best Practices
Source: https://docs.python.org/3.12/
API Version: Python 3.12
SDK Version: psycopg2-binary 2.9.x, python-dotenv 1.0.x, asyncio (stdlib)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Python itself has no authentication mechanism. In EOS, authentication means managing API keys and database credentials securely through environment variables.

**Pattern: dotenv-based secret management**
```python
from pathlib import Path
from dotenv import load_dotenv
import os

# Always use absolute path to the correct .env
load_dotenv(Path(__file__).parent / ".env")

# Access keys — never provide defaults for secrets
api_key = os.environ["ANTHROPIC_API_KEY"]       # raises KeyError if missing (good)
optional_key = os.getenv("OPTIONAL_SERVICE")     # returns None if missing

# Never do this:
# api_key = "sk-ant-..."  # hardcoded secret
# api_key = os.getenv("KEY", "sk-fallback-...")  # default secret
```

**Two .env scopes in EOS:**
| File | Contains | Used by |
|------|----------|---------|
| `eos_ai/.env` | DATABASE_URL, EOS_ORG_ID, EOS_USER_ID, LLM API keys | All eos_ai modules, agent_runtime, model_router |
| `services/.env` | DISCORD_BOT_TOKEN, FOUNDER_DISCORD_ID, channel IDs | discord_bot.py, telegram_control.py |

**Credential sanitization in errors:**
```python
import re
safe_msg = re.sub(r'://[^@]+@', '://***:***@', str(error))
```

## Core Operations with Exact Signatures

**Context managers for resource cleanup (the EOS way):**
```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def get_conn(org_id: str = ORG_ID) -> Generator:
    conn = psycopg2.connect(_DATABASE_URL)
    try:
        with conn:  # transaction context
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SET LOCAL app.current_org_id = %s", (org_id,))
                yield cur
    finally:
        conn.close()
```

**Dataclass for structured returns:**
```python
from dataclasses import dataclass, field

@dataclass
class CognitiveResult:
    status: str                              # 'completed' | 'pending_approval'
    output: str | None
    model_used: str = ""
    tokens_used: dict = field(default_factory=dict)
    iterations: int = 1
    was_enhanced: bool = False
```

**Enum for type-safe constants:**
```python
from enum import Enum

class TaskType(Enum):
    SCORE = "score"
    CLASSIFY = "classify"
    ANALYZE = "analyze"
    GENERATE = "generate"
```

**Path manipulation:**
```python
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent
_SOUL_PATH = Path(__file__).parent.parent / "agents" / f"{agent}.md"
```

## Pagination Patterns

N/A — Python is a programming language, not an API. Pagination logic in EOS is handled at the psycopg2 query level using `LIMIT` and `OFFSET` clauses, or via API-specific SDK pagination (Anthropic, Notion, etc.).

## Rate Limits

N/A for the language itself. EOS implements its own rate limiting in Python:

```python
class RateLimiter:
    LIMITS = {"per_minute": 30, "per_hour": 500}

    @classmethod
    def check(cls, org_id: str) -> bool:
        # In-memory per-org rate limiter
        # Returns True if allowed, False if rate limited
        ...
```

Rate limits for external APIs (Anthropic, Gemini, Groq) are handled in `model_router.py` via retry with exponential backoff:
```python
_MAX_RETRIES = 4
_BACKOFF_BASE = 2  # delays: 2 -> 4 -> 8 -> 16 seconds
```

## Error Codes and Recovery

Python exception hierarchy relevant to EOS:

| Exception | Cause in EOS | Recovery |
|-----------|-------------|----------|
| `ModuleNotFoundError` | sys.path not set before eos_ai import | Add `sys.path.insert(0, '/opt/OS')` before import |
| `psycopg2.OperationalError` | Neon connection failed (network, credentials) | Check DATABASE_URL, retry with backoff |
| `psycopg2.IntegrityError` | Duplicate key or constraint violation | Check data before insert, use ON CONFLICT |
| `KeyError` | Missing env var (`os.environ["KEY"]`) | Check .env file loaded, key exists |
| `anthropic.AuthenticationError` | Invalid/expired API key (401) | Check ANTHROPIC_API_KEY in eos_ai/.env |
| `ConnectionError` | Network issues to external APIs | Retry with backoff, fall through to next provider |
| `json.JSONDecodeError` | Malformed JSON from LLM response | Wrap in try/except, return raw text |
| `asyncio.CancelledError` | Task cancelled during shutdown | Let propagate, do not catch |
| `ImportError` | Circular import or missing dependency | Use lazy import pattern or TYPE_CHECKING |

**EOS error handling tiers:**
1. **Critical path** — raise with sanitized message: `raise OperationalError(safe_msg) from None`
2. **Enhancement path** — catch and continue: `except Exception: pass  # never block execution`
3. **User-facing** — return structured error: `AgentResult(output="Rate limit reached.", ...)`

## SDK Idioms

Python idioms used throughout EOS:

**Union types (Python 3.10+):**
```python
def resolve(slug: str | None) -> str | None:  # not Optional[str]
```

**Built-in generic types (Python 3.9+):**
```python
tokens: dict[str, int]       # not Dict[str, int]
parts: list[str]             # not List[str]
cache: dict[str, str] = {}   # not Dict[str, str]
```

**Walrus operator (Python 3.8+):**
```python
if (key := os.getenv("API_KEY")) is not None:
    client = create_client(key)
```

**F-strings for all string formatting:**
```python
print(f"[AgentRuntime] Warning: skill '{skill_name}' not found")
slug = f"{team}.{sub_agent}"
```

**Context managers for all resource management:**
```python
with get_conn() as cur:    # database
with open(path) as f:      # files
with tempfile.NamedTemporaryFile() as tmp:  # temp files
```

**Lazy imports to break circular dependencies:**
```python
def run(self, ...):
    from eos_ai.model_router import call_with_fallback  # imported at call time
```

**TYPE_CHECKING guard for annotation-only imports:**
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from eos_ai.agent_runtime import AgentResult
```

**Global state with module-level caching:**
```python
_spend_cache: dict = {}
_spend_cache_ts: float = 0.0
_SPEND_CACHE_TTL = 60

_caches_loaded: bool = False  # load-once pattern
```

## Anti-Patterns

**Never do these in EOS Python code:**

1. **Bare except without logging:**
   ```python
   # BAD
   try: result = call_api()
   except: pass

   # GOOD
   try: result = call_api()
   except Exception as e:
       print(f"[Module] API call failed: {e}")
   ```

2. **Hardcoded paths instead of Path objects:**
   ```python
   # BAD
   open("/opt/OS/eos_ai/memory.db")

   # GOOD
   DB_PATH = Path(__file__).parent / "memory.db"
   ```

3. **Missing type hints on public functions:**
   ```python
   # BAD
   def resolve_venture(slug):
       return _cache.get(slug)

   # GOOD
   def resolve_venture(slug: str | None) -> str | None:
       return _cache.get(slug)
   ```

4. **Direct psycopg2.connect instead of get_conn:**
   ```python
   # BAD
   conn = psycopg2.connect(os.environ["DATABASE_URL"])

   # GOOD
   with get_conn() as cur:
       cur.execute(...)
   ```

5. **Hardcoded API keys or defaults:**
   ```python
   # BAD
   client = Anthropic(api_key="sk-ant-...")
   key = os.getenv("KEY", "sk-fallback")

   # GOOD
   key = os.environ["ANTHROPIC_API_KEY"]
   ```

6. **Creating __init__.py in eos_ai/:**
   EOS uses implicit namespace packages. Adding __init__.py changes resolution semantics.

7. **Blocking async event loop with sync calls:**
   ```python
   # BAD (in Discord bot context)
   result = gateway.handle(request)

   # GOOD
   result = await asyncio.to_thread(gateway.handle, request)
   ```

8. **Catching Exception silently in critical path:**
   ```python
   # BAD — hides real errors
   try: conn = psycopg2.connect(url)
   except Exception: conn = None

   # GOOD — sanitize and re-raise
   except Exception as e:
       safe = re.sub(r'://[^@]+@', '://***:***@', str(e))
       raise psycopg2.OperationalError(f'Failed: {safe}') from None
   ```

## Data Model

EOS Python uses these typing constructs:

**Dataclasses** — primary structured data pattern:
```python
@dataclass
class AgentResult:
    output: str
    model_used: str
    tokens_used: dict[str, int]
    skill_used: str | None
    interaction_id: int | None = None
    cost_usd: float = 0.0
    duration_ms: int = 0
```

**Enums** — type-safe constants:
```python
class TaskType(Enum):
    SCORE = "score"
    CLASSIFY = "classify"
```

**TypedDict** — not currently used in EOS but available for structured dict typing.

**Module-level dicts for caching:**
```python
_venture_cache: dict[str, str] = {}   # slug -> UUID
_skill_cache: dict[str, str] = {}     # name -> UUID
COST_PER_MILLION_TOKENS: dict[str, dict[str, float]] = { ... }
```

**frozenset for immutable constant sets:**
```python
_APPROVAL_REQUIRED_ACTIONS = frozenset({"send", "delete", "payment"})
```

## Webhooks and Events

N/A for Python itself. EOS webhook handling is done in Flask (services) and Discord event handlers (py-cord). The pattern is:
- Discord events: `@bot.event` decorators for `on_message`, `on_ready`
- Flask webhooks: route handlers in services (calendly_webhook.py)
- Cron automation: bash scripts invoke Python directly

## Limits

**Python runtime limits relevant to EOS:**
- **Recursion limit:** 1000 (default). Not typically hit in EOS — no recursive algorithms in core path.
- **GIL (Global Interpreter Lock):** Single-threaded Python execution. CPU-bound work blocks the event loop. EOS mitigates via `asyncio.to_thread()` for long sync operations.
- **Memory:** VPS has limited RAM. Ollama gemma3:4b needs ~3.3 GiB. Stop os-bot before loading Ollama if memory is tight.
- **Connection limits:** Neon has connection limits per plan. EOS opens/closes connections per request (no pooling) — works at current scale but may need pooling at higher throughput.
- **File descriptors:** Default 1024. Docker containers inherit this. Not currently a bottleneck.

## Cost Model

N/A — Python is free and open source. The costs in EOS come from:
- LLM API calls (tracked per-call in `AgentResult.cost_usd`)
- Neon PostgreSQL (usage-based plan)
- VPS hosting (fixed monthly)

## Version Pinning

**Python version:** 3.12.3 (installed on VPS, used in Docker images).

**Dependency management:** `services/requirements.txt` — pinned with minimum versions where needed:
```
psycopg2-binary          # Neon PostgreSQL driver
python-dotenv            # .env file loading
anthropic                # Anthropic SDK
google-genai             # Gemini SDK (new — not google.generativeai)
openai>=1.0.0            # OpenAI-compatible APIs (Groq, Perplexity)
py-cord[voice]==2.6.1    # Discord bot (pinned — voice depends on exact version)
claude-agent-sdk>=0.1.55 # CC SDK for agent dispatch
fastembed                # Local embedding for semantic search
```

**Version gotchas:**
- `google.generativeai` (old SDK) is deprecated — always use `google.genai` (new SDK)
- `gemini-2.0-flash` deprecated for new users — use `gemini-2.5-flash`
- py-cord pinned to 2.6.1 — voice features depend on this exact version

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Python was chosen for EOS's intelligence layer because:

1. **Ecosystem dominance in AI/ML.** Every major LLM SDK (Anthropic, OpenAI, Google) has Python as the primary supported language. Wrappers in other languages lag behind.
2. **Readability as architecture documentation.** Python code reads like pseudocode. In a system where a solo founder must understand every module, readability is a structural advantage.
3. **Rapid iteration speed.** No compile step. Edit a bind-mounted file, `docker restart`, and the change is live. This matters when iterating on agent behavior daily.
4. **Explicit over implicit.** Python's philosophy aligns with EOS's: `sys.path.insert` is explicit about where imports come from. `load_dotenv(path)` is explicit about which secrets load. No magic.

**Tradeoff: TypeScript for the SaaS layer.** The customer-facing SaaS (React, Vite, Express, Drizzle) is TypeScript. Python handles intelligence; TypeScript handles UI. They share the same Neon PostgreSQL instance through RLS — unified data layer, split execution layers.

**Tradeoff: No connection pooling.** EOS opens/closes psycopg2 connections per request instead of using a pool (like pgBouncer or psycopg2.pool). At current scale (single user, low request volume), this is correct — pooling adds complexity for no benefit. When throughput increases, switch to `psycopg2.pool.ThreadedConnectionPool` or an async driver like `asyncpg`.

## Problem-Solution Map and Hidden Capabilities

| Problem | EOS Solution |
|---------|-------------|
| Circular imports between modules | Lazy imports inside function bodies + TYPE_CHECKING guard |
| Multiple .env files for different layers | Explicit `load_dotenv(Path(...))` with absolute paths |
| Tenant isolation in shared DB | `SET LOCAL app.current_org_id` via get_conn() context manager |
| LLM provider failures | Fallback chain: CC SDK -> Anthropic -> Gemini -> Ollama |
| Credential leakage in logs | `re.sub(r'://[^@]+@', '://***:***@', str(e))` |
| Blocking async event loop | `asyncio.to_thread()` for sync EOS calls in Discord bot |
| Voice WebSocket crashes killing bot | Custom `set_exception_handler` on event loop |
| Module-level state initialization | Load-once pattern with `_caches_loaded` flag |
| Rate limiting without external service | In-memory `RateLimiter` class with per-minute/per-hour windows |
| Cost tracking across providers | `calculate_cost()` with per-model rate table |

**Hidden capability: python3 -c for inline verification.** EOS uses `python3 -c "..."` extensively for quick checks from bash. This is a first-class pattern — every deployment includes an import check, every cron job uses it for state saves.

## Operational Behavior and Edge Cases

**Module loading order matters.** `agent_runtime.py` calls `load_dotenv()` at module level before importing `db.py`. This ensures DATABASE_URL is available when db.py reads `os.environ["DATABASE_URL"]` at import time. If you import db.py before dotenv is loaded, you get a `KeyError`.

**Global state is per-process.** `_venture_cache`, `_skill_cache`, `_spend_cache` are all module-level dicts populated on first use. In Docker, each container is a separate process with its own cache. Restarting a container clears all caches.

**psycopg2 connections are not thread-safe.** The `get_conn()` context manager creates a new connection per call. This is safe for concurrent use from multiple threads (like Discord bot handlers) because each thread gets its own connection. But a single connection object must not be shared across threads.

**asyncio.to_thread uses a thread pool.** When Discord bot wraps sync calls via `asyncio.to_thread()`, those calls run in a thread pool (default size = min(32, os.cpu_count() + 4)). Heavy concurrent requests could exhaust the pool.

**dotenv does not override existing environment variables by default.** If `DATABASE_URL` is already set in the shell environment, `load_dotenv()` will not overwrite it. Pass `override=True` to force, but this is rarely needed in EOS.

## Ecosystem Position and Composition

**Python in the EOS stack:**
```
Layer           | Language    | Runtime
─────────────── | ─────────── | ────────────────
Intelligence    | Python 3.12 | Docker (os-discord, os-bot)
SaaS frontend   | TypeScript  | Vite dev / Vercel
SaaS backend    | TypeScript  | Express + Drizzle ORM
Database        | SQL         | Neon PostgreSQL
Automation      | Bash + Py   | cron -> claude -p / python3
Infrastructure  | YAML        | Docker Compose
```

Python modules compose through explicit imports. There is no dependency injection framework, no plugin system, no metaclass magic. Composition is manual and visible:
- `cognitive_loop.py` imports `agent_runtime.py` imports `model_router.py`
- `gateway.py` imports `cognitive_loop.py` — the single entry point
- Services import `gateway.py` and call `gateway.handle(request)`

**Key dependency chain:**
```
discord_bot.py -> EOSGateway -> CognitiveLoop -> AgentRuntime -> ModelRouter
                                                              -> AgentMemory -> db.py
```

## Trajectory and Evolution

**Python 3.13+ features to watch:**
- **Free-threaded mode (PEP 703):** Experimental GIL removal. Would enable true parallel execution in EOS without `asyncio.to_thread()`. Not production-ready yet — monitor for 3.14/3.15.
- **JIT compiler (PEP 744):** Copy-and-patch JIT in 3.13. Minor speedups now, but trajectory toward significant performance gains.
- **Improved error messages:** 3.12 already has excellent error messages. 3.13+ continues improving `NameError` suggestions and traceback context.
- **typing improvements:** `type` statement (3.12), `TypeVar` defaults (3.13), continued evolution toward simpler annotation syntax.

**EOS-specific trajectory:**
- Current: psycopg2 (sync) — adequate for single-user
- Future: Consider `asyncpg` when moving to fully async architecture
- Current: No connection pooling — adequate at low scale
- Future: `psycopg2.pool.ThreadedConnectionPool` or pgBouncer when concurrent requests increase
- Current: print() for logging — adequate for Docker logs
- Future: structured logging (`logging` module with JSON formatter) when observability matters

## Conceptual Model and Solution Recipes

**Mental model: Python as the nervous system.**
- `gateway.py` is the spinal cord — every signal enters here
- `cognitive_loop.py` is the brain — processes signals through 8 stages
- `agent_runtime.py` is the motor cortex — selects and executes the right model
- `model_router.py` is the neurotransmitter system — routes to the right provider
- `db.py` is long-term memory — persists everything to Neon
- `memory.py` is working memory — retrieves relevant past interactions

**Recipe: Adding a new EOS module**
1. Create `eos_ai/new_module.py`
2. No `__init__.py` needed (namespace package)
3. Add `load_dotenv` if it needs env vars
4. Import from other eos_ai modules as needed
5. Verify: `python3 -c "import sys; sys.path.insert(0, '/opt/OS'); from eos_ai.new_module import NewClass; print('ok')"`
6. Run `ruff format eos_ai/new_module.py`

**Recipe: Adding a new service script**
1. Create `scripts/new_script.py`
2. First lines: `import sys; sys.path.insert(0, '/opt/OS')`
3. Load dotenv: `from dotenv import load_dotenv; load_dotenv('/opt/OS/eos_ai/.env')`
4. Import EOS modules: `from eos_ai.gateway import EOSGateway`
5. Verify: `python3 scripts/new_script.py`

**Recipe: Database query**
```python
from eos_ai.db import get_conn

with get_conn() as cur:
    cur.execute("""
        SELECT id, input_summary, created_at
        FROM interactions
        WHERE agent = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, ("sales_agent",))
    for row in cur.fetchall():
        print(row["input_summary"])
```

## Industry Expert and Cutting-Edge Usage

**Structural pattern matching (Python 3.10+):**
Not currently used in EOS but valuable for gateway routing:
```python
match request["type"]:
    case "agent_task":
        return self._handle_agent_task(request)
    case "event":
        return self._handle_event(request)
    case "status":
        return self._get_status()
    case _:
        return {"status": "error", "output": f"Unknown type: {request['type']}"}
```

**ExceptionGroup (Python 3.11+):**
Useful for reporting multiple failures from fallback chains:
```python
except* ConnectionError as eg:
    # Handle all connection errors from parallel provider attempts
    for e in eg.exceptions:
        print(f"Provider failed: {e}")
```

**TaskGroup for structured concurrency (Python 3.11+):**
```python
async with asyncio.TaskGroup() as tg:
    task1 = tg.create_task(fetch_signals())
    task2 = tg.create_task(fetch_profiles())
# Both complete or both cancel — no orphaned tasks
```

**slots=True on dataclasses for memory efficiency:**
```python
@dataclass(slots=True)
class RoutingResult:
    output: str
    provider: str
    model: str
    # ~40% less memory per instance
```

**tomllib (Python 3.11+):**
Built-in TOML parsing — no third-party dependency needed for config files.

**Modern typing patterns:**
```python
# TypeAlias (3.10+)
type TokenDict = dict[str, int]

# Self type (3.11+)
from typing import Self
class Builder:
    def set_name(self, name: str) -> Self: ...

# TypeVar defaults (3.13)
from typing import TypeVar
T = TypeVar("T", default=str)
```

---

## EOS Usage Patterns

**Standard module header (eos_ai/):**
```python
"""
ModuleName — one-line description.

Detailed description of what this module does and how it fits
in the EOS architecture.

Usage:
    from eos_ai.module_name import ClassName
    obj = ClassName()
    result = obj.method(args)
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from eos_ai.db import get_conn
from eos_ai.context import EOSContext, load_context_from_env
```

**Standard script header (scripts/, services/):**
```python
import sys
sys.path.insert(0, '/opt/OS')

from pathlib import Path
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

from eos_ai.gateway import EOSGateway
```

## Gotchas

1. **`google.generativeai` vs `google.genai`:** The old SDK is deprecated. EOS uses `google-genai` (new SDK). Import as `from google import genai`, not `import google.generativeai`.
2. **py-cord voice requires exact version pin (2.6.1).** Voice features break on other versions. The `[voice]` extra installs PyNaCl, opus, etc.
3. **`os.environ["KEY"]` raises `KeyError`; `os.getenv("KEY")` returns None.** Use `environ` for required keys (fail fast), `getenv` for optional ones.
4. **Docker bind-mount caching:** Python's `.pyc` cache (`__pycache__/`) can serve stale bytecode after edits. If behavior doesn't match code, delete `__pycache__/` and restart.
5. **Neon cold starts:** First connection after idle period may take 1-3 seconds. The `get_conn()` pattern handles this transparently, but it affects latency for the first request.
