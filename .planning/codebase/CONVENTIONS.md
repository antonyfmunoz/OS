# Code Conventions
*Generated: 2026-03-26*
*Focus: quality*

## Summary
The EOS codebase follows consistent Python conventions established organically across 67 modules. No linter config is present, but patterns are uniform: snake_case files, PascalCase classes, section dividers inside classes, and print-based logging. Error handling uses four distinct patterns depending on context.

## Naming Patterns

| Artifact | Convention | Example |
|----------|-----------|---------|
| Files/modules | `snake_case` | `agent_runtime.py` |
| Classes | `PascalCase` | `AgentRuntime`, `CognitiveLoop` |
| Constants | `ALL_CAPS` | `PRIMITIVE_LIBRARY`, `HIERARCHY` |
| Methods | `snake_case` | `run_task()`, `load_context()` |
| Private methods | `_snake_case` | `_build_prompt()` |
| Dataclass fields | `snake_case` | `org_id`, `venture_id` |

## Module Structure

Standard module layout (top to bottom):
```python
"""Module docstring."""
# stdlib imports
# third-party imports
# internal imports

# Constants / config
CONSTANT = ...

# Dataclasses / TypedDicts
@dataclass
class SomeModel:
    ...

# Main class
class ClassName:
    # ─── Section Name ───────────────────────────────
    def method(self):
        ...
```

Section dividers (`# ─── Section ───`) are used inside larger classes to group related methods.

## Import Organization

1. Standard library (`sys`, `os`, `json`, `pathlib`, `datetime`)
2. Third-party (`anthropic`, `psycopg2`, `playwright`, `requests`)
3. Internal EOS modules (`from eos_ai.db import get_conn`)

**Repo root injection pattern** — used consistently across all scripts:
```python
import sys
sys.path.insert(0, '/opt/OS')
from eos_ai.module import Class
```

`TYPE_CHECKING` guard used to avoid circular imports in tightly coupled modules.

## Error Handling Patterns

Four patterns in use:

| Pattern | When Used | Example |
|---------|-----------|---------|
| Silent `pass` | Non-critical optional features | Embedding lookup fallback |
| Explicit re-raise | Critical paths where caller must know | DB connection failures |
| `ErrorHandler` class | Centralized error routing | `eos_ai/error_handler.py` |
| `with_retry` decorator | External API calls (Anthropic, Neon) | LLM dispatch |

## Logging

No structured logging framework. All logging uses `print()` with class prefix:
```python
print(f"[AgentRuntime] Running task for agent: {agent_id}")
print(f"[CognitiveLoop] Stage 3 complete")
```

This makes logs human-readable in `docker logs` but not machine-parseable.

## Type Hints

Modern union syntax used (`str | None` not `Optional[str]`). Type hints are present on most public method signatures. Dataclasses used heavily for structured data (context objects, result types, primitives).

## Docstrings

Sparse. Module-level docstrings exist on most files. Method-level docstrings are inconsistent — present on public APIs, absent on internal helpers.

## Key Files

- `eos_ai/cognitive_loop.py` — best example of full module structure and section dividers
- `eos_ai/primitives.py` — best example of ALL_CAPS constants and dataclass usage
- `eos_ai/error_handler.py` — centralized error handling implementation
- `eos_ai/agent_runtime.py` — `with_retry` decorator pattern
