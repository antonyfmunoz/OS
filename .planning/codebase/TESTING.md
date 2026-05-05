# Testing
*Generated: 2026-03-26*
*Focus: quality*

## Summary
The `eos_ai/` core layer has no automated test suite — verification relies on manual import checks and a single integration test script. A unittest-based test suite exists for the `.agents/skills/` utility library. Coverage gaps are significant across all core modules.

## What Exists

### Integration Test (manual)
- **File:** `eos_ai/integration_test.py`
- **Type:** Manual end-to-end script, not a test framework
- **Usage:** Run directly (`python3 eos_ai/integration_test.py`)
- **Covers:** Full pipeline walkthrough — context load → cognitive loop → agent runtime → memory write
- **Not:** Automated, not part of any CI pipeline

### Unit Tests (skills utility library)
- **Location:** `.agents/skills/last30days/tests/`
- **Framework:** Python `unittest`
- **Count:** 8 test files
- **Covers:** Skill utility library functions only — not EOS core modules
- **Not run by:** Any CI/CD or pre-commit hook

### Import Verification (primary pattern)
The standard verification method used throughout CLAUDE.md and dev workflows:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import eos_ai
print('imports: clean')
"
```
Or per-module:
```python
python3 -c "from eos_ai.[module] import [Class]; print('import ok')"
```
This is the de facto test gate before any deploy.

## Coverage Gaps

| Module Group | Coverage | Notes |
|-------------|----------|-------|
| `cognitive_loop.py` | None | Most critical, zero tests |
| `agent_runtime.py` | None | Multi-model routing untested |
| `authority_engine.py` | None | Risk classification untested |
| `memory.py` | None | Memory writes untested |
| `db.py` | None | RLS behavior untested |
| `evolution_engine.py` | None | Stage progression untested |
| `primitives.py` | None | Primitive validity untested |
| `orchestrator.py` | None | 1,461 lines, zero tests |
| Skills utility lib | Partial | 8 unittest files in `.agents/` |

## No Test Infrastructure

- No `pytest` or `unittest` runner configured
- No `Makefile` test target
- No CI/CD pipeline (no `.github/workflows/`)
- No pre-commit hooks for testing
- No coverage measurement tooling

## Recommended Test Entry Points

If tests are added, the natural starting points based on risk:
1. `eos_ai/authority_engine.py` — deterministic logic, easy to unit test
2. `eos_ai/primitives.py` — static data validation
3. `eos_ai/agent_runtime.py` — model routing logic (can mock LLM calls)
4. `eos_ai/integration_test.py` — already exists, extend it

## Key Files

- `eos_ai/integration_test.py` — only end-to-end test, run manually
- `.agents/skills/last30days/tests/` — only automated tests, skill library only
