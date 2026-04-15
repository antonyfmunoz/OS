# Execution Constraints — Design Specification

**Date:** 2026-04-15
**Status:** Approved
**Scope:** Minimal execution-constraint layer for the EOS substrate permission stack

---

## Problem

The existing permission stack decides ALLOW / ESCALATE / DENY based on
role, intent type, and risk level. But after tool policy says ALLOW,
nothing checks what the allowed action actually targets. A builder with
ALLOW on FILE_WRITE can write to `/etc/passwd` just as easily as
`/opt/OS/eos_ai/foo.py`.

The execution constraint layer fills that gap: deterministic path and
command boundaries that cannot be bypassed.

## Design Principles

1. `resolve_permission()` is the single authoritative decision boundary.
2. Constraints can tighten decisions but never loosen them.
3. DENY is terminal — no layer can override it.
4. All decision values are enums — no raw strings in the pipeline.
5. The constraint module is pure: no roles, no UI, no side effects.
6. The bridge is a pure executor: no decision logic.

---

## Architecture

### Decision Flow

```
extract_intent()
    → classify_risk()
        → resolve_permission()
            ├── resolve_tool_policy()        → ToolPolicyDecision
            ├── evaluate_execution_constraints() → ConstraintResult
            ├── _combine_decisions()         → FinalResolution
            ├── _derive_resolution()         → PermissionResolution (transport)
            └── return PermissionDecision    (complete trace)
```

### Module Boundaries

```
execution_constraints.py    — pure constraint evaluation (no roles, no UI)
discord_output_policy.py    — decision composition + authoritative resolve_permission()
session_discord_bridge.py   — pure executor consuming PermissionDecision
```

---

## New File: `eos_ai/substrate/execution_constraints.py`

### Enums

```python
class ConstraintDecision(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    ESCALATE = "escalate"

class PathScope(str, Enum):
    APPROVED_ROOT = "approved_root"
    TEMP_ROOT = "temp_root"
    OUTSIDE_ROOT = "outside_root"
    SYSTEM_PATH = "system_path"

class CommandClass(str, Enum):
    SAFE = "safe"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"

class ConstraintType(str, Enum):
    PATH_BOUNDARY = "path_boundary"
    COMMAND_SAFETY = "command_safety"
    NETWORK_SCOPE = "network_scope"
    NO_TARGET = "no_target"
    NONE = "none"              # constraint evaluated, no issue found
    NOT_EVALUATED = "not_evaluated"  # constraint evaluated but intent type has no
                                     # meaningful constraint logic (PROCESS_EXEC, UNKNOWN)
```

### Result Model

```python
@dataclass(frozen=True)
class ConstraintResult:
    result: ConstraintDecision
    constraint_type: ConstraintType
    reason: str
```

### Approved Roots

```python
_APPROVED_ROOTS: tuple[str, ...] = ("/opt/OS",)
_APPROVED_TEMP_PREFIXES: tuple[str, ...] = ("/tmp/eos_",)
_SYSTEM_PATHS: frozenset[str] = frozenset({
    "/", "/etc", "/root", "/usr", "/var", "/boot",
    "/sbin", "/bin", "/lib", "/proc", "/sys", "/dev",
})

def get_approved_roots(session: Any = None) -> list[str]:
    """Always includes _APPROVED_ROOTS. Optionally appends session.active_workspace.
    Never removes or overrides base roots."""
```

**Rules:**
- Always includes `_APPROVED_ROOTS`
- If `session` is provided and has `active_workspace` attribute that is a
  non-empty string, appends it
- Never removes or overrides base roots
- Returns a new list every call (no shared mutable state)

### Path Classification

```python
def classify_path_scope(target_path: str, session: Any = None) -> PathScope:
```

**Rules:**
1. Normalize via `os.path.realpath(os.path.abspath(target_path))`
2. Check against `_SYSTEM_PATHS`: if normalized path equals or starts
   with any system path + `os.sep`, return `SYSTEM_PATH`
3. Check against `get_approved_roots(session)`: if normalized path equals
   or starts with any root + `os.sep`, return `APPROVED_ROOT`
4. Check against `_APPROVED_TEMP_PREFIXES`: if normalized path starts with
   any temp prefix, return `TEMP_ROOT`
5. Otherwise return `OUTSIDE_ROOT`

**Order matters:** System paths are checked first. `/etc/eos` would match
`/etc` as a system path before any approved root check.

**Traversal prevention:** `os.path.realpath()` resolves symlinks and `../`
sequences. A target of `/opt/OS/../../etc/passwd` resolves to `/etc/passwd`
→ `SYSTEM_PATH`.

### Command Classification

```python
def classify_command(command: str) -> CommandClass:
```

Reuses `_SAFE_COMMAND_PATTERNS` and `_DESTRUCTIVE_COMMAND_PATTERNS` imported
from `discord_output_policy`. No new pattern sets.

- Match destructive first → `DESTRUCTIVE`
- Match safe → `SAFE`
- No match → `UNKNOWN`

### Command Path Extraction

```python
def _extract_command_target_path(command: str) -> str:
```

**Strict extraction rules:**
- Split command, look for arguments that start with `/` (absolute paths)
- If exactly one absolute path found, return it
- If zero or multiple found, return `""` (fail safe to unknown)
- Never guess, never partially parse
- Piped commands: split on `|`, examine only the first segment for paths

### Core Evaluator

```python
def evaluate_execution_constraints(
    intent: PermissionIntent,
    risk_level: RiskLevel,
    target_path: str = "",
) -> ConstraintResult:
```

**Intent-type routing:**

| Intent Type | Behavior |
|---|---|
| `FILE_READ` | Classify path scope from `intent.target`, apply read rules |
| `FILE_WRITE` | Classify path scope from `intent.target`, apply write rules |
| `COMMAND` | Classify command + extract path + apply matrix |
| `NETWORK_CALL` | Return `ESCALATE` with `constraint_type=NETWORK_SCOPE` |
| `PROCESS_EXEC` | Return `ESCALATE` with `constraint_type=NOT_EVALUATED` |
| `UNKNOWN` | Return `ESCALATE` with `constraint_type=NOT_EVALUATED` |

**File read/write rules:**
- No target path → `ESCALATE` with `constraint_type=NO_TARGET`
- `APPROVED_ROOT` or `TEMP_ROOT` → `ALLOWED`
- `OUTSIDE_ROOT` → `BLOCKED` for writes, `ESCALATE` for reads
- `SYSTEM_PATH` → `BLOCKED`

**Command decision matrix:**

| Command Class | Path Scope | Result |
|---|---|---|
| SAFE | APPROVED_ROOT | ALLOWED |
| SAFE | TEMP_ROOT | ALLOWED |
| SAFE | OUTSIDE_ROOT | ESCALATE |
| SAFE | SYSTEM_PATH | BLOCKED |
| DESTRUCTIVE | APPROVED_ROOT | ESCALATE |
| DESTRUCTIVE | TEMP_ROOT | ESCALATE |
| DESTRUCTIVE | OUTSIDE_ROOT | BLOCKED |
| DESTRUCTIVE | SYSTEM_PATH | BLOCKED |
| UNKNOWN | APPROVED_ROOT | ESCALATE |
| UNKNOWN | TEMP_ROOT | ESCALATE |
| UNKNOWN | OUTSIDE_ROOT | BLOCKED |
| UNKNOWN | SYSTEM_PATH | BLOCKED |

**No-path commands:** If `_extract_command_target_path()` returns `""`,
treat as `UNKNOWN` command class + escalate with `constraint_type=NO_TARGET`.

---

## Modified: `eos_ai/substrate/discord_output_policy.py`

### New Enums

```python
class FinalResolution(str, Enum):
    ALLOW = "allow"
    ESCALATE = "escalate"
    DENY = "deny"

class ExecutionMode(str, Enum):
    AUTO = "auto"              # autonomous session
    INTERACTIVE = "interactive"  # user-facing session
```

`FinalResolution` has a priority ordering: `DENY(2) > ESCALATE(1) > ALLOW(0)`.

### New Dataclass

```python
@dataclass(frozen=True)
class PermissionDecision:
    final_resolution: FinalResolution
    execution_mode: ExecutionMode
    origin: PermissionOrigin
    tool_policy_decision: ToolPolicyDecision | None
    constraint_evaluated: bool
    constraint_result: ConstraintDecision | None
    constraint_type: ConstraintType | None
    constraint_reason: str | None
    resolution: PermissionResolution = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolution", _derive_resolution(
            self.final_resolution, self.execution_mode,
        ))
```

`resolution` is always derived — never set by callers. The `__post_init__`
invariant guarantees this.

### Derivation Function

```python
def _derive_resolution(
    final: FinalResolution,
    mode: ExecutionMode,
) -> PermissionResolution:
    if mode == ExecutionMode.INTERACTIVE:
        return PermissionResolution.SURFACE_AND_WAIT
    # AUTO mode
    if final == FinalResolution.ALLOW:
        return PermissionResolution.AUTO_APPROVE_AND_SUPPRESS
    if final == FinalResolution.DENY:
        return PermissionResolution.AUTO_DENY_AND_SUPPRESS
    # ESCALATE in auto mode → surface
    return PermissionResolution.SURFACE_AND_WAIT
```

### Composition Function

```python
_FINAL_PRIORITY: dict[str, int] = {
    FinalResolution.ALLOW: 0,
    FinalResolution.ESCALATE: 1,
    FinalResolution.DENY: 2,
}

_CONSTRAINT_TO_FINAL: dict[ConstraintDecision, FinalResolution] = {
    ConstraintDecision.ALLOWED: FinalResolution.ALLOW,
    ConstraintDecision.ESCALATE: FinalResolution.ESCALATE,
    ConstraintDecision.BLOCKED: FinalResolution.DENY,
}

_TOOL_POLICY_TO_FINAL: dict[ToolPolicyDecision, FinalResolution] = {
    ToolPolicyDecision.ALLOW: FinalResolution.ALLOW,
    ToolPolicyDecision.ESCALATE: FinalResolution.ESCALATE,
    ToolPolicyDecision.DENY: FinalResolution.DENY,
}

def _combine_decisions(
    tool_policy: ToolPolicyDecision,
    constraint: ConstraintResult,
) -> FinalResolution:
    tp_final = _TOOL_POLICY_TO_FINAL[tool_policy]
    ct_final = _CONSTRAINT_TO_FINAL[constraint.result]
    # max() over priority — DENY > ESCALATE > ALLOW
    if _FINAL_PRIORITY[tp_final] >= _FINAL_PRIORITY[ct_final]:
        return tp_final
    return ct_final
```

### Updated `resolve_permission()`

```python
def resolve_permission(
    session_name: str,
    intent: PermissionIntent | None = None,
    risk_level: RiskLevel | None = None,
) -> PermissionDecision:
```

**Logic:**

1. Classify origin → `PermissionOrigin`
2. Derive `execution_mode` from origin:
   - `INTERNAL_AUTO` → `ExecutionMode.AUTO`
   - `USER_FACING` → `ExecutionMode.INTERACTIVE`
3. If intent and risk_level are None (legacy path):
   - Return `PermissionDecision` with `constraint_evaluated=False`,
     all constraint fields `None`, `final_resolution=ALLOW`,
     `tool_policy_decision=None`
4. Resolve tool policy: `resolve_tool_policy(role, intent, risk_level)`
5. If tool policy is DENY:
   - Return with `constraint_evaluated=False`, all constraint fields `None`
     (skipped — DENY is terminal, constraints cannot change the outcome)
6. Evaluate constraints: `evaluate_execution_constraints(intent, risk_level, intent.target)`
7. Combine: `_combine_decisions(tool_policy, constraint_result)`
8. Return `PermissionDecision` with full trace

### Updated `should_surface_permission()`

```python
def should_surface_permission(...) -> bool:
    decision = resolve_permission(session_name, intent, risk_level)
    return decision.resolution == PermissionResolution.SURFACE_AND_WAIT
```

---

## Modified: `eos_ai/substrate/session_discord_bridge.py`

### Changes

1. Remove direct `resolve_tool_policy()` call — moved inside `resolve_permission()`
2. Branch on `decision.final_resolution`, not `PermissionResolution`
3. Use `decision.execution_mode` to determine auto vs surfaced behavior
4. Enrich event payloads with constraint trace fields

### Bridge Branching

```python
intent = extract_intent(event.text)
risk = classify_risk(intent)
decision = resolve_permission(event.session_name, intent, risk)

# Build payload once
_perm_payload_base = _build_permission_payload(decision, event_id, intent, risk, text_hash)

if decision.final_resolution == FinalResolution.ALLOW:
    # Auto-approve and suppress (only reachable in AUTO mode)
    ...
elif decision.final_resolution == FinalResolution.DENY:
    if decision.execution_mode == ExecutionMode.AUTO:
        # Auto-deny and suppress
        ...
    else:
        # Interactive deny — surface the denial
        ...
elif decision.final_resolution == FinalResolution.ESCALATE:
    # Always surface — falls through to Discord delivery
    ...
```

### Payload Builder

```python
def _enum_val(e: Enum | None) -> str | None:
    return e.value if e is not None else None

def _build_permission_payload(
    decision: PermissionDecision,
    event_id: str,
    intent: PermissionIntent,
    risk: RiskLevel,
    content_hash: str,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "resolution": decision.resolution.value,
        "origin": decision.origin.value,
        "execution_mode": decision.execution_mode.value,
        "intent_type": intent.type.value,
        "intent_command": intent.command,
        "intent_target": intent.target,
        "risk_level": risk.value,
        "tool_policy_decision": _enum_val(decision.tool_policy_decision),
        "constraint_evaluated": decision.constraint_evaluated,
        "constraint_result": _enum_val(decision.constraint_result),
        "constraint_type": _enum_val(decision.constraint_type),
        "constraint_reason": decision.constraint_reason,
        "final_resolution": decision.final_resolution.value,
        "decision_mode": "legacy" if decision.tool_policy_decision is None else "full",
        "content_hash": content_hash,
    }
```

---

## Test Suite: `tests/substrate/test_execution_constraints.py`

Pure function calls. No mocking. No Discord. No tmux.

### Constraint Module Tests

**Path classification:**
- `/opt/OS/eos_ai/foo.py` → `APPROVED_ROOT`
- `/tmp/eos_workspace_123/file.txt` → `TEMP_ROOT`
- `/home/user/something.py` → `OUTSIDE_ROOT`
- `/etc/nginx/conf.d/default.conf` → `SYSTEM_PATH`
- `/opt/OS/../../etc/passwd` → `SYSTEM_PATH` (traversal resolved)

**Command classification:**
- `git status` → `SAFE`
- `rm -rf /` → `DESTRUCTIVE`
- `docker build .` → `UNKNOWN`

**Command path extraction:**
- `rm -rf /opt/OS/tmp/` → `/opt/OS/tmp/`
- `git status` → `""` (no absolute path)
- `cat /etc/passwd | grep root` → `/etc/passwd` (first segment only)
- `cp /a /b` → `""` (multiple paths, fail safe)

**Decision matrix (all 12 cells):**
- SAFE + APPROVED_ROOT → ALLOWED
- SAFE + TEMP_ROOT → ALLOWED
- SAFE + OUTSIDE_ROOT → ESCALATE
- SAFE + SYSTEM_PATH → BLOCKED
- DESTRUCTIVE + APPROVED_ROOT → ESCALATE
- DESTRUCTIVE + TEMP_ROOT → ESCALATE
- DESTRUCTIVE + OUTSIDE_ROOT → BLOCKED
- DESTRUCTIVE + SYSTEM_PATH → BLOCKED
- UNKNOWN + APPROVED_ROOT → ESCALATE
- UNKNOWN + TEMP_ROOT → ESCALATE
- UNKNOWN + OUTSIDE_ROOT → BLOCKED
- UNKNOWN + SYSTEM_PATH → BLOCKED

**Edge cases:**
- FILE_WRITE with no target → ESCALATE, `NO_TARGET`
- NETWORK_CALL → ESCALATE, `NETWORK_SCOPE`
- FILE_READ at OUTSIDE_ROOT → ESCALATE (not blocked)
- FILE_READ at SYSTEM_PATH → BLOCKED

### Composition Tests (all 9 combinations)

| Tool Policy | Constraint | Final |
|---|---|---|
| ALLOW | ALLOWED | ALLOW |
| ALLOW | ESCALATE | ESCALATE |
| ALLOW | BLOCKED | DENY |
| ESCALATE | ALLOWED | ESCALATE |
| ESCALATE | ESCALATE | ESCALATE |
| ESCALATE | BLOCKED | DENY |
| DENY | * | DENY (skipped) |

### Integration Tests (end-to-end through `resolve_permission`)

1. Builder safe read `/opt/OS/eos_ai/foo.py`
   → `ALLOW` + `AUTO` → `AUTO_APPROVE_AND_SUPPRESS`
2. Builder write `/opt/OS/eos_ai/bar.py`
   → `ALLOW` + `AUTO` → `AUTO_APPROVE_AND_SUPPRESS`
3. Builder write `/home/user/something.py`
   → `DENY` + constraint_type=`PATH_BOUNDARY`
4. Builder `rm -rf /etc/nginx`
   → `DENY` + constraint_type=`COMMAND_SAFETY`
5. DEX read `/opt/OS/data/report.json`
   → `ALLOW` + `AUTO` → `AUTO_APPROVE_AND_SUPPRESS`
6. Legacy call (no intent/risk)
   → `constraint_evaluated=False`, `decision_mode="legacy"`

### Invariant Tests

- `PermissionDecision.resolution` always equals
  `_derive_resolution(final_resolution, execution_mode)`
- `constraint_evaluated=False` ↔ all constraint fields are `None`
- `constraint_evaluated=True` ↔ all constraint fields are populated

---

## Files Changed

| File | Change |
|---|---|
| `eos_ai/substrate/execution_constraints.py` | **NEW** — pure constraint evaluation |
| `eos_ai/substrate/discord_output_policy.py` | Add `FinalResolution`, `ExecutionMode`, `PermissionDecision`; update `resolve_permission()` to compose tool policy + constraints; update `should_surface_permission()` |
| `eos_ai/substrate/session_discord_bridge.py` | Remove direct `resolve_tool_policy()` call; branch on `final_resolution`; enrich event payloads |
| `tests/substrate/test_execution_constraints.py` | **NEW** — full validation suite |

## Remaining Limitations

1. Command path extraction is strict — commands with no clear absolute path
   argument escalate rather than being precisely evaluated. This is
   intentional (fail safe) but means some safe commands will escalate
   unnecessarily until extraction improves.
2. `_APPROVED_TEMP_PREFIXES` uses prefix matching (`/tmp/eos_`) — a file
   at `/tmp/eos_evil_namespace/` would match. Acceptable for now; tighten
   if temp workspaces get formal registration.
3. Network constraints are observability-only (ESCALATE with `NETWORK_SCOPE`).
   Domain-level blocking is a future extension.
4. `get_approved_roots()` session extension is additive-only. If session
   workspace paths need validation themselves, that's a future concern.
5. `PROCESS_EXEC` and `UNKNOWN` intents escalate unconditionally. No path
   or command analysis is attempted for these — they rely entirely on
   tool policy and operator judgment.
