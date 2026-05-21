# UMH Reference Archive Manifest

Archived during convergence Wave 2 — 2026-05-10.

## Why Archived

`umh/` (Universal Meta Harness) is the prior-generation intelligence
architecture. It was superseded by the substrate v1 system in `core/`.
Zero live-runtime imports exist — no service, no eos_ai module, and
no core module imports from umh/.

## Contents

- 897 tracked Python files from umh/
- 1 dormant script: scripts/demo_mvp_loop.py (zero callers)
- Reference architecture preserved for pattern mining

## Associated Legacy Tests

Moved to tests/legacy/:
- tests/legacy/unit/ — 165 files (all umh importers)
- tests/legacy/test_*.py — 156 root test files (umh importers)
- tests/legacy/substrate/ — 24 pre-substrate tests (umh importers)
- tests/legacy/adapters/ — 6 files (umh importers + __init__.py)
- tests/legacy/runtime/ — 8 files (umh importers + __init__.py)

Total: 359 legacy test files relocated

## Import Shim

`umh/__init__.py` installed at original location — raises ImportError
with guidance message pointing to this archive.

## Rollback

```bash
git revert <wave-2-commit>
```
