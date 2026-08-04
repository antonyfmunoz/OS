# F-1 — Git Commit Capability Design (empirically derived)

Every claim below is a measured result from `gitwrite_probe{1..7}.py`, run against
real `bwrap` 0.9.0 and real `git`. Nothing here is inferred from documentation.

## The constraint chain (why the obvious designs fail)

| Design | Result | Why |
|---|---|---|
| `.git` fully read-only (current head, F-1) | **cannot commit** | `fatal: Unable to create '.git/index.lock': Read-only file system`, `ADD_RC=128` |
| Bind only the FILES git writes (`index`, `refs/heads/x`, …) | **cannot commit** | git creates `*.lock` files **beside** their targets, so it needs the *directory* writable, not the file |
| `.git` writable + individual existing ref files re-locked | **ESCAPE** | `refs/heads` dir stays writable → worker creates a **loose ref shadowing a packed ref** → `update-ref refs/heads/protected-main` succeeded (rc=0) |
| `refs/` locked + own branch FILE re-bound | **cannot commit** | needs `refs/heads/<branch>.lock` *inside* the locked dir |
| **`refs/` locked + own private ref DIRECTORY re-bound** | **WORKS** | git creates its `.lock` inside the attempt's own dir; every shared namespace stays read-only |

## The adopted seam

Per-attempt **private ref namespace**, prepared host-side at lease setup:

```
.git/refs/attempt/<attempt_id>/work     <- the ONLY writable ref location
.git/HEAD  ->  ref: refs/attempt/<attempt_id>/work
```

bwrap layering (order is load-bearing — later binds mask earlier ones):

1. `--bind <lease> <lease>` — lease writable
2. `--ro-bind` each forbidden **source** path (existing task-scope barrier)
3. `--ro-bind` each dangerous **git** subpath:
   `hooks`, `config`, `info`, `branches`, `description`, `packed-refs`, `HEAD`, **`refs`** (whole tree)
4. `--bind <priv_dir> <priv_dir>` — re-open ONLY this attempt's ref directory

`.git` itself is NOT broadly writable in the dangerous sense: `objects/`, `logs/`,
`index`, `COMMIT_EDITMSG` are writable (measured as exactly what add+commit needs);
every authorization surface is independently re-locked and proven denied.

## Measured minimal git write set (probe1)

add+commit **writes**: `objects`, `refs`(own), `logs`, `index`, `COMMIT_EDITMSG`
add+commit **never touches**: `HEAD`, `branches`, `config`, `description`, `hooks`, `info`

## Adversarial results — 18/18 (probe6)

ALLOW (3): edit+add+commit · second commit · new in-scope file+commit

DENY (15), all leaving the target **byte-identical**:
forbidden source edit · forbidden objective edit · hook install · hooks dir replace ·
config write · config rename-over · unrelated ref update · **sibling attempt ref** ·
create sibling attempt dir · loose ref in `refs/heads` · delete other branch ·
packed-refs rewrite · HEAD repoint · forbidden file staged into commit ·
rename-over forbidden · refs tree replace

## Persistence — the acceptance criterion (probe7)

One sandbox session, two commits, then sandbox closed:

```
base was      : a1ecac8cf786
host ref now  : fd389a815b47   MOVED: True
host log      : fd389a8 second | 3d9d9c0 worker change | a1ecac8 base
diff base..ref: 'app/main.py'      <- exactly what the verifier reads
FORBIDDEN.py  : 'forbidden\n'      <- byte-identical
```

The commit is durable on the host, attributable to the attempt, and scoped.

## Directive compliance

- "no broad writable `.git` bind unless every dangerous subpath is independently
  constrained and **proven safe**" → each is `--ro-bind`ed and each has a passing
  DENY vector above.
- "worker cannot alter hooks, config, refs unrelated to its Attempt" → proven,
  including the sibling-attempt namespace and the loose-ref-shadow escape.
- "commit identity bound to the exact Attempt" → the ref name *is* the attempt id.
- Not chmod-based; denials come from the mount (`Read-only file system`), so
  rename, delete, and parent-replacement are all covered.
