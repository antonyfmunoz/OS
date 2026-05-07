---
type: codebase-class
file: core/security/execution.py
line: 89
generated: 2026-05-07
---

# ExecutionContext

**File:** [[core-security-execution-py]] | **Line:** 89

Declarative set of restrictions for a run of code.

Fields
------
name               — human label ("agent:executor@sandbox-1")
...

## Methods

- [[core-security-execution-py-ExecutionContext-check_path]]`(path) → Path` — Raise ExecutionDenied if `path` is not allowed for `mode`.
- [[core-security-execution-py-ExecutionContext-may_path]]`(path) → bool` — Non-raising version of check_path.
- [[core-security-execution-py-ExecutionContext-_matches]]`(path_str, prefix) → bool` — 
- [[core-security-execution-py-ExecutionContext-check_command]]`(command) → None` — Refuse shell metacharacters unless shell=True AND allow_shell=True.
- [[core-security-execution-py-ExecutionContext-scrubbed_env]]`(extra) → dict` — Return a minimized env dict to hand to subprocess.
- [[core-security-execution-py-ExecutionContext-to_dict]]`() → dict` — 

## Decorators

- `@dataclass`
