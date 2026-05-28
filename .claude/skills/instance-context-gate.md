---
name: instance-context-gate
description: "Use when modifying substrate/ code or reviewing changes for instance-specific value leaks. Enforces the Instance Context Law."
trigger: conversational
effort: low
---

# Instance Context Gate

## When to use
- Before any commit touching substrate/ Python files
- When reviewing code for instance-specific hardcoded values
- When adding new files to substrate/
- When migrating legacy files from the grandfathered list

## The Law
UMH substrate is universal. It works for ANY user, ANY org, ANY deployment.
Instance-specific values in substrate/ code are defects.

## Instance categories (never hardcode these)
1. **AI name** → `get_handler_prefix()` from `substrate.self_model` or `os.environ.get("AI_NAME", "")`
2. **Founder/user name** → `os.environ.get("UMH_FOUNDER_NAME", "")` or `self_model.instance.founder_name`
3. **Company/venture names** → `substrate.state.business.venture_knowledge.get_venture_name(key)`
4. **Product names** → same as company names, via venture_knowledge
5. **Infrastructure IPs** → env vars (`EOS_LOCAL_BRIDGE_IP`, `TAILSCALE_VPS_IP`, etc.)
6. **Account IDs** → `os.environ.get("GITHUB_USER", "")`
7. **Session prefixes** → `make_session_name()` from `substrate.execution.bridge.claude_session_bridge`

## Runtime helpers
```python
# Handler prefix for event types and handled_by fields
from substrate.self_model import get_handler_prefix as _ghp
handled_by=f'{_ghp()}task_name'

# AI name and founder name for prompts
_ai = os.environ.get("AI_NAME", "AI")
_founder = os.environ.get("UMH_FOUNDER_NAME", "the founder")

# Session names
from substrate.execution.bridge.claude_session_bridge import make_session_name as _msn
session = _msn("builder", "main")

# Venture/company names
from substrate.state.business.venture_knowledge import get_venture_name
name = get_venture_name("lyfe_institute")
```

## Verification commands
```bash
# Scan entire substrate for leaks
python3 scripts/check_instance_leak.py --all

# Scan a specific file
python3 scripts/check_instance_leak.py --file substrate/path/to/file.py

# Run the migration scanner
python3 scripts/migrate_instance_leaks.py --scan

# Install pre-commit hooks (once per clone)
bash scripts/install_hooks.sh
```

## SQL queries
Never use `event_type = 'dex_task'` — always parameterize:
```python
cur.execute("... WHERE event_type = %s ...", (f"{_ghp()}task",))
```

## Gotchas
- `import os` must go AFTER `from __future__ import annotations` if both exist
- `get_handler_prefix()` is safe at import time (pure env var lookup, no DB)
- `self_model.instance` attributes may be empty if env vars aren't set — always provide fallbacks
- `venture_knowledge.get_venture_name()` loads from `data/umh/ventures.json` — file must exist
- Legacy files are tracked in `LEGACY_INSTANCE_LEAKS` dict in `scripts/check_instance_leak.py`
- The pre-commit hook runs both type coherence AND instance context gates
