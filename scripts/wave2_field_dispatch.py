"""Wave 2 field-qualification dispatcher — runs on the VPS orchestrator.

Stands up an ISOLATED candidate cockpit stack (candidate operator container +
freshly-built dist-web served by its own nginx, exposed over the same Tailscale
origin the operator uses), dispatches the field collector to the Windows
executor through the GOVERNED mesh path, polls its status read-only, then
reconciles the collected browser evidence against the candidate's own runtime
state and docker logs. Finally tears the stack down and restores Tailscale serve.

Nothing here runs a browser (Browser Verification Law) and nothing dispatches
ungoverned (mesh_dispatch_port). The collector is the only browser-bearing part
and it runs on the executor.

Subcommands:
  preflight        health + nodes relay, mesh reachability, echo the start shape
  deploy-candidate build + start the candidate stack, wire Tailscale serve
  seed-fixture     generate the fixture app under the run's targets dir
  start-runner     start the run-scoped host attempt runner + control-plane poller
  smoke            one collector pass, smoke scenario
  run              N collector passes, full scenario
  pause-before-dispatch  arm the same-run ADMISSION pause (zero quota)
  inject-failure   arm a genuine worker failure variant for one pass
  activation-rehearsal  zero-quota deployed API grant activation rehearsal
  collector-teardown-rehearsal  zero-quota inert Beast collector lifecycle rehearsal
  resume           release the admission pause; scheduling resumes
  reconcile        score collected evidence against candidate state + logs
  teardown         stop containers, stop runner, shred run secret, restore serve

Every subcommand supports --dry-run: it prints the exact commands it WOULD run
and assembles no side effects. Use it to prove command assembly without touching
the live host.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))
_WORKTREE = Path(__file__).resolve().parent.parent  # the candidate source worktree

# Executor-side paths (Windows Beast). Kept in one place so the start-command
# shape is auditable.
#
# The collector runs from a DETACHED git worktree pinned to the exact
# candidate commit (exact-commit binding for the collector code itself), NOT
# from the Beast's main checkout: C:\dev\dev\OS stays on main because the
# node daemon runs from it, and main predates this branch — the collector
# doesn't even exist there (observed 2026-07-22: smoke dispatch silently
# no-opped on a missing script). Worktree lifecycle, per new candidate head:
#   git -C C:\dev\dev\OS fetch origin <branch>
#   git -C C:\dev\dev\OS worktree add --detach C:\dev\wave2_wt <sha>   (first)
#   git -C C:\dev\wave2_wt checkout --detach <sha>                     (update)
# smoke/run preflight the worktree HEAD against the candidate sha and refuse
# to dispatch on mismatch.
_BEAST_OS_ROOT = r"C:\dev\dev\OS"
_BEAST_WT = r"C:\dev\wave2_wt"
_BEAST_ENV_TPL = _BEAST_WT + r"\scripts\.env.beast.tpl"
_BEAST_COLLECTOR = _BEAST_WT + r"\scripts\wave2_field_collector.py"
_BEAST_EVIDENCE_DIR = r"C:\dev\wave2_evidence"

_MESH_NODE_ID = "windows-desktop"  # from infra/device_registry.json (executor)
_CANDIDATE_CONTAINER = "os-operator-candidate-w2"
_CANDIDATE_NGINX_CONTAINER = "os-nginx-candidate-w2"


# The compose project prefixes the network name (docker-compose → project_name
# + "_" + network). Resolve it at runtime from the LIVE os-operator container
# so the candidate shares the exact same network (container-DNS upstream works).
# NO literal fallback: the compose network name carries the instance's compose
# project name (projection/instance vocabulary — never hardcoded in platform
# harness code). If resolution fails, fail closed with the override escape
# hatch rather than guess.
def _operator_network() -> str:
    override = os.environ.get("UMH_CANDIDATE_NETWORK", "").strip()
    if override:
        return override
    try:
        out = subprocess.run(
            [
                "docker",
                "inspect",
                "os-operator",
                "--format",
                "{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        nets = out.stdout.split()
        if nets:
            return nets[0]
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] operator network resolution failed: {exc}")
    raise SystemExit(
        "cannot resolve the operator docker network from the live os-operator "
        "container — set UMH_CANDIDATE_NETWORK explicitly"
    )


def _powershell_encoded_command(script: str) -> str:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return f"powershell -NoProfile -EncodedCommand {encoded}"


def _powershell_command(script: str) -> str:
    compact = "; ".join(line.strip() for line in script.splitlines() if line.strip())
    compact = compact.replace("@{; ", "@{").replace("; }", " }")
    return "powershell -NoProfile -Command " + json.dumps(compact)


_UNCLAIMED_CANCEL_ERROR = "durable remote request cancelled before claim"


# Network + origin are module globals used by the inherited wave1 call sites as
# bare names. They are resolved LAZILY at command entry (see `_resolve_env()`
# called from `main()`), NOT at import — so importing this module for a helper
# (e.g. the self-check exercising the secret helpers) never shells out to
# `docker inspect`/`tailscale status` or `raise SystemExit` at import time
# (review W8). They start as None; any real command resolves them first.
_OPERATOR_DOCKER_NETWORK: str | None = None
_ORIGIN: str | None = None


def _resolve_env() -> None:
    """Resolve the network + candidate origin globals on first real command.

    Idempotent. Raises SystemExit (via the resolvers) only when a real command
    actually needs them and they cannot be resolved — never at import.
    """
    global _OPERATOR_DOCKER_NETWORK, _ORIGIN
    if _OPERATOR_DOCKER_NETWORK is None:
        _OPERATOR_DOCKER_NETWORK = _operator_network()
    if _ORIGIN is None:
        _ORIGIN = _candidate_origin()


_CANDIDATE_API_PORT = 8091  # inside the container
_CANDIDATE_API_HOST_PORT = 8291  # 127.0.0.1:8191 -> candidate api (recon reads)
_CANDIDATE_NGINX_HOST_PORT = 8290  # 127.0.0.1:8190 -> candidate nginx
# Tailscale-serve TLS port for the candidate. NOT 443: the host's Caddy binds
# *:443 (wildcard — it fronts the vestigial local universalmetaharness.tech
# vhost), which shadows the tailscale IP and makes tailscaled's :443 listener
# fail with EADDRINUSE — every handshake then hits Caddy, which has no cert
# for the tailnet SNI (observed 2026-07-21: TLSV1_ALERT_INTERNAL_ERROR).
# tailscale serve officially supports HTTPS on 443/8443/10000; 10443 is free on
# this host, keeps tailscale serve as the ONLY fronting mechanism for the
# candidate, and touches zero production host config.
_CANDIDATE_TLS_PORT = 10443
# CANDIDATE origin — the VPS's own tailnet HTTPS name (+ TLS port), which
# `tailscale serve --https=8443 → 127.0.0.1:8190` actually fronts. The public
# domain (universalmetaharness.tech) resolves to Fly PRODUCTION and is
# untouched by tailscale serve — using it here would have "qualified"
# production instead of the candidate (adversarial finding, 2026-07-22).
# Resolved at runtime; override with UMH_CANDIDATE_ORIGIN only for explicit
# lab setups.


def _candidate_origin() -> str:
    override = os.environ.get("UMH_CANDIDATE_ORIGIN", "").strip()
    if override:
        return override.rstrip("/")
    try:
        out = subprocess.run(
            ["tailscale", "status", "--json"], capture_output=True, text=True, timeout=15
        )
        dns_name = json.loads(out.stdout)["Self"]["DNSName"].rstrip(".")
        if dns_name:
            return f"https://{dns_name}:{_CANDIDATE_TLS_PORT}"
    except Exception as exc:  # noqa: BLE001 — preflight will fail loudly anyway
        print(f"[warn] candidate origin resolution failed: {exc}")
    raise SystemExit("cannot resolve the candidate tailnet origin — set UMH_CANDIDATE_ORIGIN")


def _origin_host() -> str:
    """Bare hostname of the candidate origin (no scheme, no port) — for `tailscale cert`."""
    _resolve_env()
    return _ORIGIN.removeprefix("https://").removeprefix("http://").split(":", 1)[0]


# ── Wave 2: fixture targets + run-scoped dispatch secret ─────────────────────
# The spool + host-runner infrastructure lives here.
import secrets as _secrets  # noqa: E402


def _smoke_workspace_scope() -> str:
    """The smoke-style COMBINED task's declared writable authority, comma-joined.

    The smoke objective is one Task covering backend + frontend + their tests, so
    its authority is the canonical combined lane — ``FIXTURE_ALLOWED_PATHS`` under
    the INTEGRATION label, which is exactly
    ``app/main.py, app/store.py, app/static, tests/test_search_api.py,
    tests/test_ui_search.py``. It deliberately EXCLUDES the fixture's seed data,
    config, and pre-existing tests: a worker that rewrites ``tests/test_api.py``
    to make its own change pass is out of scope and must fail verification.

    Read from the ONE canonical map so the harness can never drift from the
    authority the verifier enforces. This does NOT replace the A/B/C/D split —
    the full field graph still materializes distinct Tasks with the distinct
    per-lane scopes from the same map.
    """
    fts = _import_field_task_scope()
    return ",".join(fts.FIXTURE_ALLOWED_PATHS[fts.INTEGRATION])


def _import_field_task_scope():
    """Import field_task_scope from the WORKTREE via importlib.

    When run_passes() calls start_runner() in the same process, substrate may
    already be cached from the main checkout (via _mesh_read → mesh_dispatch_port).
    A plain sys.path.insert + from-import resolves against the cached package path
    (/opt/OS/substrate) which lacks execution/attempts/. importlib bypasses the
    cache and loads from the worktree's file path directly.
    """
    import importlib.util

    mod_path = _WORKTREE / "substrate" / "execution" / "attempts" / "field_task_scope.py"
    spec = importlib.util.spec_from_file_location("field_task_scope", str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _preseed_worktree_substrate() -> None:
    """Make the candidate WORKTREE own the ``substrate`` package identity.

    THE HARNESS INVARIANT: a qualification run for candidate worktree ``W`` MUST
    import qualification-facing candidate modules from ``W`` — never from
    ``/opt/OS`` merely because ``/opt/OS`` was imported earlier in the same
    process.

    The green ``run_passes`` path first drives ``_mesh_read`` (candidate
    readiness + Beast commit binding), which does ``sys.path.insert(0, _ROOT)``
    and ``import substrate.sockets.mesh_dispatch_port``. That caches the
    ``substrate`` and ``substrate.execution`` packages resolved against
    ``/opt/OS`` — the MAIN checkout, which has no ``execution/attempts/`` (that
    directory exists only on this branch's worktree). A later plain
    ``sys.path.insert(0, _WORKTREE)`` + ``from substrate.execution.attempts...``
    then resolves ``substrate.execution.attempts`` as a subpackage of the
    already-cached ``/opt/OS``-rooted ``substrate.execution`` → the path does not
    exist → ``ModuleNotFoundError: No module named 'substrate.execution.attempts'``.

    A pointwise fix (importlib leaf-load of one module) is INSUFFICIENT and was
    proven so: the leaf's own internal ``from substrate.execution.attempts...``
    imports still resolve against the stale parent. The whole
    ``substrate.execution*`` subtree — the package IDENTITY — must resolve from
    the worktree. So this helper:

      1. puts ``_WORKTREE`` first on ``sys.path`` (worktree wins path resolution);
      2. evicts every ``substrate`` / ``substrate.*`` module already cached from a
         root OTHER than the worktree, so the next import re-resolves the whole
         subtree from ``_WORKTREE``.

    It is idempotent (a second call is a clean no-op once the worktree owns the
    cache) and it NEVER silently falls back to ``/opt/OS`` — a missing worktree
    ``substrate`` package raises on the subsequent import, fail-closed, rather
    than being masked. The already-imported mesh-dispatch port re-resolves from
    the worktree on its next use; that module is byte-identical to main, so the
    mesh path is behaviour-preserved.
    """
    wt = str(_WORKTREE.resolve())
    # 1) worktree wins path resolution — remove any stale copies, then front-load.
    while wt in sys.path:
        sys.path.remove(wt)
    sys.path.insert(0, wt)
    # 2) evict substrate modules cached from outside the worktree so the whole
    #    package subtree re-resolves from _WORKTREE on the next import.
    #    Boundary: a module counts as "inside the worktree" ONLY when its
    #    resolved anchor is exactly ``wt`` or is under ``wt`` + os.sep — a bare
    #    ``startswith(wt)`` would wrongly retain a SIBLING worktree whose path is
    #    a string-prefix superset (e.g. ``<wt>-other``). A substrate module with
    #    NO anchor at all (neither __file__ nor __path__) cannot be PROVEN to
    #    come from the worktree, so it is evicted (fail-closed toward re-resolve),
    #    never silently retained.
    wt_prefix = wt + os.sep
    for name in list(sys.modules):
        if name != "substrate" and not name.startswith("substrate."):
            continue
        mod = sys.modules.get(name)
        anchor = getattr(mod, "__file__", None) or ""
        if not anchor:
            # namespace package (no __file__) — use its first __path__ entry.
            paths = list(getattr(mod, "__path__", []) or [])
            anchor = paths[0] if paths else ""
        resolved = str(Path(anchor).resolve()) if anchor else ""
        inside_worktree = resolved == wt or resolved.startswith(wt_prefix)
        if not inside_worktree:
            del sys.modules[name]


def _declared_lanes_json() -> str:
    """The A/B/C/D lane DECLARATION for the full field protocol, as JSON.

    This is the producer the multi-lane journey requires. Every lane's authority
    comes from the ONE canonical map (``FIXTURE_ALLOWED_PATHS``) so the harness
    can never drift from what the verifier enforces, and the verification lane
    is declared ZERO-WRITE (empty list = nothing may change, never "anything
    may change").

    Dependencies encode the required graph:  A ─┐
                                                ├→ C → D
                                             B ─┘
    Setting this env var also arms the runner's pre-quota graph-shape gate.

    Each lane also carries its own SELF-SUFFICIENT contract (``intent``,
    ``desired_end_state``, ``constraints``). Field run 20260803T002300Z-p1 proved
    a title alone is not enough: the lanes carried only a short title, so the
    only substantive spec a worker could find was the fixture repo's
    ``OBJECTIVE.md`` -- one document holding ALL FOUR task contracts. Both
    workers read it, implemented the whole objective, changed the same six
    files, and were correctly refused with ``diff_scope``. Binding the contract
    to the lane (and declaring the global objective subordinate) is what keeps
    each worker inside its authorized surface.
    """
    fts = _import_field_task_scope()

    def _lane(key: str, title: str, label: str, depends_on: list[str]) -> dict[str, Any]:
        allowed = list(fts.FIXTURE_ALLOWED_PATHS[label])
        forbidden = fts.forbidden_paths_for(label)
        # The path boundaries are declared ONCE, as structured fields
        # (``writable_path_scope`` / ``forbidden_path_scope``); the compiler
        # renders them into worker-visible constraint lines. Restating them here
        # as prose made each boundary reachable by two independent sources, so
        # deleting either one left the other in place and the mutation survived
        # — a boundary with a silent backup is a boundary nothing verifies.
        constraints = [
            "Implement ONLY this Task's slice — do NOT solve the complete objective.",
            fts.FIXTURE_PRECEDENCE_NOTE,
        ]
        return {
            "lane_key": key,
            "title": title,
            "intent": fts.task_intent_for(label),
            "desired_end_state": fts.task_contract_for(label),
            "constraints": constraints,
            "writable_path_scope": allowed,
            "forbidden_path_scope": forbidden,
            "depends_on": depends_on,
            "semantic_label": label,
        }

    lanes = [
        _lane("backend", "Add the note-search backend endpoint", fts.BACKEND, []),
        _lane("frontend", "Add the note-search frontend UI", fts.FRONTEND, []),
        _lane(
            "integration",
            "Integrate and reconcile the search branches",
            fts.INTEGRATION,
            ["backend", "frontend"],
        ),
        _lane(
            "verification",
            "Independently verify note search",
            fts.VERIFICATION,
            ["integration"],
        ),
    ]
    return json.dumps(lanes)


def _targets_dir(sha: str, run_id: str) -> Path:
    """Per-run fixture-target root — a fresh dir every pass, retained as evidence.

    NEVER reset in place; each run gets its own dir so cross-pass bleed is
    impossible. Lives under the candidate state root (outside the repo tree).
    """
    return Path("/var/lib/umh/candidates/wave2") / sha / "targets" / run_id


def _spool_root(sha: str, run_id: str) -> Path:
    """Signed dispatch spool root for one run (ephemeral transport)."""
    return _state_dir(sha).parent / "spool" / run_id


def _run_secret_path(sha: str) -> Path:
    """0600 file holding the run-scoped UMH_W2_DISPATCH_SECRET.

    NOT a production secret and NOT in the candidate env allowlist.

    HOST-ONLY (finding SEC-W6). The file sits at ``<candidate>/state/``, which is
    the PARENT of the ``state/umh`` directory mounted into the candidate
    container — so the container cannot read it, and must not: Amendment v1
    clause 3 gives the worker (and the container) NO signing secret. Only the
    host runner reads it. Do NOT "fix" the mount to match a sharing model that
    was never intended.

    Shredded by ``teardown`` AND by the crash handler, so an interrupted run does
    not strand it (SEC-W4). Its VALUE never appears in logs, PR, evidence,
    process args, or model context.
    """
    return _state_dir(sha).parent / ".w2_dispatch_secret"


def _mint_run_secret(runner: "Runner", sha: str) -> Path:
    """Generate the run-scoped dispatch secret to a 0600 file (idempotent).

    Returns the path. The value is written to disk ONLY — never returned to
    stdout, never logged, never passed as a CLI arg. The host runner reads it
    via --secret-env pointed at a file-sourced env; the candidate control plane
    reads the same file. First-write-wins so a re-run in the same run reuses it.
    """
    path = _run_secret_path(sha)
    if runner.dry_run:
        print(f"[dry-run] mint run-scoped dispatch secret → {path} (0600, value never printed)")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # Create with 0600 ATOMICALLY (O_CREAT|O_EXCL|mode) so the secret is
        # never world-readable for even a TOCTOU window (write-then-chmod left a
        # gap at the process umask — review W3). If creation cannot be locked
        # down, FAIL CLOSED: a run secret we cannot protect must not exist (W2).
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return path  # concurrent first-write won the race — reuse it
        except OSError as exc:
            raise RuntimeError(f"cannot mint run secret at {path}: {exc}") from exc
        try:
            os.write(fd, _secrets.token_hex(32).encode("ascii"))
        finally:
            os.close(fd)
        # Defense in depth: verify the mode actually took; fail closed if not.
        mode = os.stat(path).st_mode & 0o777
        if mode != 0o600:
            try:
                os.chmod(path, 0o600)
            except OSError as exc:
                path.unlink(missing_ok=True)
                raise RuntimeError(
                    f"run secret {path} could not be locked to 0600 (mode={oct(mode)}): {exc}"
                ) from exc
    return path


def _shred_run_secret(runner: "Runner", sha: str) -> bool:
    """Destroy the run-scoped dispatch secret at teardown.

    Overwrites then unlinks. NOTE: overwrite-in-place is best-effort on
    journaling/CoW/SSD filesystems and is NOT a cryptographic-erase guarantee
    (review W4) — the unlink is what actually removes the run-scoped, low-value
    secret from the namespace. The value never left this host or entered any log.
    """
    path = _run_secret_path(sha)
    if runner.dry_run:
        print(f"[dry-run] shred run secret {path}")
        return True
    if not path.exists():
        return True
    try:
        size = path.stat().st_size
        with open(path, "wb") as f:
            f.write(b"\x00" * max(size, 64))
            f.flush()
            os.fsync(f.fileno())
        path.unlink()
        return True
    except OSError as exc:
        print(f"[warn] run-secret shred failed: {exc}")
        return False


# Redaction for LIVE OPERATOR OUTPUT (logs, command echoes, launch-log tails).
#
# The bare `\b[0-9a-f]{64}\b` rule that briefly lived here is WITHDRAWN (finding
# SEC-C1): it matched every legitimate sha256 — artifact hashes, package_hash,
# scope_hash, `sha256:` image IDs — and would have destroyed the proof manifest's
# integrity claim. Evidence redaction is now done by the one-way finalization
# pipeline (`substrate.execution.attempts.evidence_finalization`), which redacts
# EXACT known secret values plus typed credential formats and never touches a
# bare hash.
#
# The assignment form below still catches `UMH_W2_DISPATCH_SECRET=<value>`, which
# is the shape the launch-log incident produced.
_SECRET_REDACT_RE = re.compile(
    r"(?i)(bearer\s+[A-Za-z0-9._\-]+|eyJ[A-Za-z0-9._\-]{20,}|"
    r"sk-ant-[A-Za-z0-9_\-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"(?:password|secret|token|api[_-]?key)\s*[=:]\s*\S+)"
)


# ─────────────────────────────────────────────────────────────────────────────
# Command runner with dry-run + secret redaction
# ─────────────────────────────────────────────────────────────────────────────
class Runner:
    """Runs shell commands, or in dry-run mode just prints their assembled form."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.log: list[str] = []

    def run(
        self,
        cmd: list[str],
        *,
        timeout: int = 120,
        check: bool = False,
        capture: bool = True,
    ) -> subprocess.CompletedProcess | None:
        printable = " ".join(shlex.quote(c) for c in cmd)
        printable = _SECRET_REDACT_RE.sub("<redacted>", printable)
        self.log.append(printable)
        if self.dry_run:
            print(f"[dry-run] {printable}")
            return None
        return subprocess.run(
            cmd,
            timeout=timeout,
            check=check,
            capture_output=capture,
            text=True,
        )

    def shell(self, cmd_str: str, *, timeout: int = 120) -> subprocess.CompletedProcess | None:
        printable = _SECRET_REDACT_RE.sub("<redacted>", cmd_str)
        self.log.append(printable)
        if self.dry_run:
            print(f"[dry-run] $ {printable}")
            return None
        return subprocess.run(cmd_str, shell=True, timeout=timeout, capture_output=True, text=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _run_id_default() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _proof_root() -> Path:
    return _ROOT / "data" / "audits" / "proof" / f"{_date_slug()}_wave2_field"


def _evidence_raw_root_from_path(path: Path) -> Path | None:
    """Return the run-date raw proof root for a staging/canonical evidence path."""
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    proof_base = (_ROOT / "data" / "audits" / "proof").resolve()
    parts = resolved.parts
    if ".incoming" in parts:
        idx = parts.index(".incoming")
        raw_root = Path(*parts[:idx])
    elif len(parts) >= 2 and parts[-1].startswith("pass"):
        raw_root = resolved.parent.parent
    else:
        return None
    try:
        raw_root.relative_to(proof_base)
    except ValueError:
        return None
    if raw_root.name != "raw" or not raw_root.parent.name.endswith("_wave2_field"):
        return None
    return raw_root.resolve()


def _evidence_raw_root_for_upload(upload: dict[str, Any]) -> Path | None:
    staging = _safe_absolute_evidence_path(upload.get("staging_path"))
    if staging is not None:
        raw_root = _evidence_raw_root_from_path(staging)
        if raw_root is not None:
            return raw_root
    canonical = _safe_absolute_evidence_path(upload.get("canonical_path"))
    if canonical is not None:
        return _evidence_raw_root_from_path(canonical)
    return None


def _state_dir(sha: str) -> Path:
    return Path("/var/lib/umh/candidates/wave2") / sha / "state" / "umh"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Tailscale serve snapshot / restore (idempotent, exit-safe)
# ─────────────────────────────────────────────────────────────────────────────
_serve_snapshot_path: Path | None = None
_serve_restored = False


def _serve_snapshot_stable_path(sha: str = "") -> Path:
    """Deterministic snapshot location, recoverable across CLI invocations.

    deploy-candidate, smoke, run, and teardown are SEPARATE process
    invocations. The production-serve snapshot deploy-candidate takes must be
    found again by a later teardown (or a crash handler) for the SAME candidate
    SHA so production serve is restored exactly once. A per-process global
    cannot survive a process boundary, so the canonical snapshot lives in the
    candidate's runtime state when the SHA is known.
    """
    if sha:
        return _state_dir(sha).parent / "tailscale_serve_snapshot.json"
    return _proof_root() / "tailscale_serve_snapshot.json"


def _snapshot_tailscale_serve(runner: Runner, run_dir: Path, *, sha: str = "") -> Path:
    """Snapshot current `tailscale serve status --json` to the stable path.

    Only preserves an existing snapshot while it is still active. Once teardown
    positively records restoration, the next deploy for the same SHA captures a
    fresh pre-run Serve state instead of replaying stale historical routing.
    """
    global _serve_snapshot_path
    snap = _serve_snapshot_stable_path(sha)
    _serve_snapshot_path = snap
    if runner.dry_run:
        print(f"[dry-run] would snapshot tailscale serve → {snap}")
        return snap
    if snap.exists():
        try:
            existing = json.loads(snap.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        if not isinstance(existing, dict) or not existing.get("restore_completed_at"):
            # Preserve the active pre-candidate snapshot; a redeploy would otherwise
            # capture the candidate mapping and lose the real restore target.
            return snap
    result = runner.run(["tailscale", "serve", "status", "--json"], timeout=30, capture=True)
    status = result.stdout if result and result.returncode == 0 else "{}"
    config_path = run_dir / "tailscale_serve_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_result = runner.run(
        ["tailscale", "serve", "get-config", str(config_path), "--all"],
        timeout=30,
        check=False,
        capture=True,
    )
    config = ""
    if config_result is not None and config_result.returncode == 0 and config_path.exists():
        config = config_path.read_text(encoding="utf-8")
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(
        json.dumps(
            {
                "snapshot_contract": "tailscale_serve_exact_restore_v3",
                "candidate_sha": sha,
                "deployment_id": _run_id_default(),
                "status": json.loads(status or "{}"),
                "config_captured": bool(config.strip()),
                "config": json.loads(config) if config.strip() else None,
                "captured_at": datetime.now(timezone.utc).isoformat(),
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return snap


def _load_serve_snapshot_path(sha: str = "") -> None:
    """Point the module global at the on-disk snapshot from a prior deploy.

    Called by consuming commands (smoke/run/teardown) so their crash handlers
    and teardown restore have a real production snapshot to restore, even though
    THIS process never took it.
    """
    global _serve_snapshot_path
    path = _serve_snapshot_stable_path(sha)
    if _serve_snapshot_path is None and path.exists():
        _serve_snapshot_path = path


def _mark_serve_snapshot_restored(path: Path) -> None:
    try:
        snap = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(snap, dict):
            snap["restore_completed_at"] = datetime.now(timezone.utc).isoformat()
            path.write_text(json.dumps(snap, sort_keys=True, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] could not mark tailscale serve snapshot restored: {exc}")


def _serve_restore_success(result: dict[str, Any]) -> dict[str, Any]:
    global _serve_restored
    _serve_restored = True
    if _serve_snapshot_path is not None and not result.get("dry_run"):
        _mark_serve_snapshot_restored(_serve_snapshot_path)
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _verify_tailscale_serve_restored_config(
    runner: Runner,
    *,
    snapshot: Path,
    expected_config: dict[str, Any],
) -> dict[str, Any]:
    live_path = snapshot.with_name("tailscale_serve_live_after_restore.json")
    try:
        live_path.unlink()
    except FileNotFoundError:
        pass
    readback = runner.run(
        ["tailscale", "serve", "get-config", str(live_path), "--all"],
        timeout=30,
        check=False,
        capture=True,
    )
    if readback is not None and readback.returncode != 0:
        return {
            "ok": False,
            "reason": "tailscale serve restore readback failed",
            "stderr": _SECRET_REDACT_RE.sub("<redacted>", (readback.stderr or "")[-800:]),
        }
    if not live_path.is_file():
        return {"ok": False, "reason": "tailscale serve restore readback missing"}
    try:
        live_config = json.loads(live_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "reason": f"tailscale serve restore readback unreadable: {type(exc).__name__}",
        }
    expected_digest = hashlib.sha256(_canonical_json(expected_config).encode("utf-8")).hexdigest()
    live_digest = hashlib.sha256(_canonical_json(live_config).encode("utf-8")).hexdigest()
    return {
        "ok": live_config == expected_config,
        "readback": str(live_path),
        "expected_config_sha256": expected_digest,
        "live_config_sha256": live_digest,
        "config_matches_snapshot": live_config == expected_config,
        "reason": "" if live_config == expected_config else "tailscale serve restore readback mismatch",
    }


def _serve_status_projection(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "TCP": status.get("TCP") or {},
        "Web": status.get("Web") or {},
    }


def _verify_tailscale_serve_restored_status(
    runner: Runner,
    *,
    snapshot: Path,
    expected_status: dict[str, Any],
) -> dict[str, Any]:
    readback = runner.run(
        ["tailscale", "serve", "status", "--json"],
        timeout=30,
        check=False,
        capture=True,
    )
    if readback is not None and readback.returncode != 0:
        return {
            "ok": False,
            "reason": "tailscale serve status readback failed",
            "stderr": _SECRET_REDACT_RE.sub("<redacted>", (readback.stderr or "")[-800:]),
        }
    try:
        live_status = json.loads((readback.stdout if readback is not None else "") or "{}")
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "reason": f"tailscale serve status readback unreadable: {type(exc).__name__}",
        }
    expected = _serve_status_projection(expected_status)
    live = _serve_status_projection(live_status if isinstance(live_status, dict) else {})
    expected_digest = hashlib.sha256(_canonical_json(expected).encode("utf-8")).hexdigest()
    live_digest = hashlib.sha256(_canonical_json(live).encode("utf-8")).hexdigest()
    return {
        "ok": live == expected,
        "snapshot": str(snapshot),
        "expected_status_sha256": expected_digest,
        "live_status_sha256": live_digest,
        "status_matches_snapshot": live == expected,
        "reason": "" if live == expected else "tailscale serve status readback mismatch",
    }


def _restore_tailscale_serve(runner: Runner, *, sha: str = "") -> dict[str, Any]:
    """Restore serve config from the snapshot. Idempotent; safe on every exit."""
    global _serve_restored
    if sha and _serve_snapshot_path is None:
        _load_serve_snapshot_path(sha)
    if _serve_restored or _serve_snapshot_path is None:
        return {
            "ok": _serve_restored,
            "already_restored": _serve_restored,
            "snapshot": str(_serve_snapshot_path) if _serve_snapshot_path else "",
            "reason": "" if _serve_restored else "serve snapshot unavailable",
        }
    if runner.dry_run:
        print("[dry-run] would re-apply tailscale serve snapshot if non-empty")
        return _serve_restore_success(
            {"ok": True, "dry_run": True, "snapshot": str(_serve_snapshot_path)}
        )
    try:
        snap = json.loads(_serve_snapshot_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "snapshot": str(_serve_snapshot_path),
            "reason": f"serve snapshot unreadable: {type(exc).__name__}",
        }
    if snap.get("snapshot_contract") == "tailscale_serve_exact_restore_v3":
        snapshot_sha = str(snap.get("candidate_sha", ""))
        if sha and snapshot_sha != sha:
            return {
                "ok": False,
                "snapshot": str(_serve_snapshot_path),
                "reason": "serve snapshot candidate_sha mismatch",
                "candidate_sha": sha,
                "snapshot_candidate_sha": snapshot_sha,
            }
    # Reset first, then re-apply the snapshot if it was non-empty.
    reset = runner.run(["tailscale", "serve", "reset"], timeout=30, check=False)
    if reset is not None and reset.returncode != 0:
        return {
            "ok": False,
            "snapshot": str(_serve_snapshot_path),
            "reason": "tailscale serve reset failed",
            "stderr": _SECRET_REDACT_RE.sub("<redacted>", (reset.stderr or "")[-800:]),
        }
    status = snap.get("status") if snap.get("snapshot_contract") else snap
    if snap.get("config_captured") and isinstance(snap.get("config"), dict):
        restore_cfg = _serve_snapshot_path.with_name("tailscale_serve_restore_config.json")
        restore_cfg.write_text(json.dumps(snap["config"], sort_keys=True, indent=2), encoding="utf-8")
        applied = runner.run(
            ["tailscale", "serve", "set-config", str(restore_cfg), "--all"],
            timeout=30,
            check=False,
            capture=True,
        )
        ok = bool(applied is None or applied.returncode == 0)
        out = {
            "ok": ok,
            "snapshot": str(_serve_snapshot_path),
            "method": "set-config",
            "config_captured": True,
            "stderr": "" if ok else _SECRET_REDACT_RE.sub("<redacted>", (applied.stderr or "")[-800:]),
        }
        if not ok:
            return out
        proof = _verify_tailscale_serve_restored_config(
            runner,
            snapshot=_serve_snapshot_path,
            expected_config=snap["config"],
        )
        out["readback_proof"] = proof
        out["ok"] = proof.get("ok") is True
        return _serve_restore_success(out) if out["ok"] else out
    web = status.get("Web") if isinstance(status, dict) else None
    tcp = status.get("TCP") if isinstance(status, dict) else None
    if tcp and not web:
        return {
            "ok": False,
            "snapshot": str(_serve_snapshot_path),
            "reason": "legacy serve snapshot contains TCP handlers without replayable Web config",
        }
    if not web:
        out = {"ok": True, "snapshot": str(_serve_snapshot_path), "method": "reset-empty"}
        proof = _verify_tailscale_serve_restored_status(
            runner,
            snapshot=_serve_snapshot_path,
            expected_status={"TCP": {}, "Web": {}},
        )
        out["readback_proof"] = proof
        out["ok"] = proof.get("ok") is True
        return _serve_restore_success(out) if out["ok"] else out
    restored: list[dict[str, Any]] = []
    for host_port, entry in sorted(web.items()):
        handlers = entry.get("Handlers") if isinstance(entry, dict) else None
        if not isinstance(handlers, dict):
            return {"ok": False, "snapshot": str(_serve_snapshot_path), "reason": "invalid Web handlers"}
        try:
            port = str(host_port).rsplit(":", 1)[1]
        except IndexError:
            return {"ok": False, "snapshot": str(_serve_snapshot_path), "reason": "invalid Web host:port"}
        for path, handler in sorted(handlers.items()):
            proxy = handler.get("Proxy") if isinstance(handler, dict) else None
            if not proxy:
                return {
                    "ok": False,
                    "snapshot": str(_serve_snapshot_path),
                    "reason": f"unsupported serve handler at {host_port}{path}",
                }
            cmd = ["tailscale", "serve", "--bg", f"--https={port}"]
            if path and path != "/":
                cmd.append(f"--set-path={path}")
            cmd.append(proxy)
            applied = runner.run(cmd, timeout=30, check=False, capture=True)
            if applied is not None and applied.returncode != 0:
                return {
                    "ok": False,
                    "snapshot": str(_serve_snapshot_path),
                    "reason": f"serve replay failed for {host_port}{path}",
                    "stderr": _SECRET_REDACT_RE.sub("<redacted>", (applied.stderr or "")[-800:]),
                }
            restored.append({"host_port": host_port, "path": path, "proxy": proxy})
    out = {
        "ok": True,
        "snapshot": str(_serve_snapshot_path),
        "method": "legacy-status-replay",
        "restored": restored,
    }
    proof = _verify_tailscale_serve_restored_status(
        runner,
        snapshot=_serve_snapshot_path,
        expected_status=status if isinstance(status, dict) else {},
    )
    out["readback_proof"] = proof
    out["ok"] = proof.get("ok") is True
    return _serve_restore_success(out) if out["ok"] else out


def _install_crash_handlers(runner: Runner, sha: str = "") -> None:
    """SIGINT/SIGTERM → restore production serve. NO normal-exit restore.

    deploy-candidate, smoke, and run are separate CLI invocations that must
    LEAVE the candidate serve live on normal exit for the next command — an
    atexit restore here is exactly the bug that tore the origin down the moment
    deploy-candidate finished (observed 2026-07-21: `wired: true` then
    "No serve config"). Production serve is restored on the happy path in ONE
    place only: teardown. These handlers exist solely so an interrupted/killed
    command never strands the tailnet origin pointed at a dead candidate.
    """

    def _handler(signum: int, _frame: Any) -> None:
        _restore_tailscale_serve(runner, sha=sha)
        # Destroy the run secret on an interrupted/killed run too (SEC-W4):
        # shredding used to be reachable ONLY via an explicit `teardown`, so any
        # crash or SIGKILL left it on disk indefinitely (one such orphan was
        # found during R0 containment).
        if sha:
            try:
                _shred_run_secret(runner, sha)
            except Exception as exc:  # never block the exit path
                print(f"[crash-handler] run-secret shred failed: {exc}")
        raise SystemExit(128 + signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            pass  # not in main thread / unsupported — teardown still restores


# ─────────────────────────────────────────────────────────────────────────────
# deploy-candidate
# ─────────────────────────────────────────────────────────────────────────────
def _candidate_image_id(runner: Runner) -> str:
    """Resolve the os-operator image id so the candidate runs the SAME image."""
    result = runner.run(
        ["docker", "inspect", "--format", "{{.Image}}", "os-operator"],
        timeout=30,
        capture=True,
    )
    if runner.dry_run or result is None:
        return "<os-operator-image-id>"
    return (result.stdout or "").strip() or "os-operator:latest"


def _read_clerk_publishable_key() -> str:
    """Read VITE_CLERK_PUBLISHABLE_KEY from the production fly.toml at runtime."""
    fly = _ROOT / "cockpit" / "fly.toml"
    try:
        for line in fly.read_text(encoding="utf-8").splitlines():
            if "VITE_CLERK_PUBLISHABLE_KEY" in line and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _remove_container_and_wait(runner: Runner, name: str, timeout_s: int = 90) -> None:
    """`docker rm -f` + wait until the NAME is actually free.

    `docker rm -f` returns before the daemon releases the container name; an
    immediately-following `docker run --name <same>` intermittently 125s with
    a name Conflict (observed twice on 2026-07-22 — the second time only
    because _must made it loud; the first time it silently left NO container
    and produced misleading connection-refused symptoms downstream)."""
    try:
        runner.run(["docker", "rm", "-f", name], timeout=90, check=False)
    except subprocess.TimeoutExpired:
        # Under daemon load the rm call can exceed its timeout while the
        # removal itself continues daemon-side (observed twice 2026-07-22,
        # host load ~1.6/core). The name-release wait below is the actual
        # correctness gate — don't fail the deploy on the slow rm call.
        print(f"[warn] docker rm -f {name} slow — waiting for name release")
    if runner.dry_run:
        return
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            probe = subprocess.run(
                ["docker", "inspect", name],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            # A slow daemon (post-churn backlog) is "still busy", not a
            # failure — keep waiting until the overall deadline.
            print(f"[warn] docker inspect {name} slow — daemon busy, retrying")
            continue
        if probe.returncode != 0:  # name no longer resolves — free
            return
        time.sleep(0.5)
    raise SystemExit(f"container name {name!r} still in use {timeout_s}s after rm -f")


def _must(runner: Runner, step: str, result: subprocess.CompletedProcess | None) -> None:
    """Fail the deploy LOUDLY when a critical step fails.

    Three separate field-deploy failures (missing collector script, missing
    candidate.env, phantom health route) were each invisible because runner
    results were captured and dropped. A critical step that fails now aborts
    with the step name + redacted stderr instead of letting later steps
    produce misleading downstream symptoms."""
    if runner.dry_run or result is None:
        return
    if result.returncode != 0:
        err = _SECRET_REDACT_RE.sub("<redacted>", (result.stderr or result.stdout or "")[-800:])
        raise SystemExit(f"deploy step '{step}' failed (rc={result.returncode}):\n{err}")


_FRONTEND_ARTIFACT_MANIFEST = ".umh-wave2-artifact.json"


class _FrontendAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.module_scripts: list[str] = []
        self.stylesheets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        if tag == "script" and attr.get("type") == "module" and attr.get("src"):
            self.module_scripts.append(attr["src"])
        if tag == "link" and attr.get("rel") == "stylesheet" and attr.get("href"):
            self.stylesheets.append(attr["href"])


def _frontend_asset_name_from_ref(ref: str, suffix: str) -> str:
    normalized = ref.split("?", 1)[0].split("#", 1)[0].lstrip("./")
    prefix = "assets/"
    if not normalized.startswith(prefix) or not normalized.endswith(suffix):
        return ""
    name = normalized[len(prefix) :]
    if "/" in name or not name:
        return ""
    return name


def _candidate_frontend_bytes_proof(dist_web: Path) -> dict[str, Any]:
    index = dist_web / "index.html"
    proof: dict[str, Any] = {
        "ok": False,
        "index_sha256": "",
        "assets": {},
        "errors": [],
    }
    errors: list[str] = proof["errors"]
    if not index.is_file():
        errors.append("dist-web index.html missing")
        return proof
    proof["index_sha256"] = _sha256_file(index)
    parser = _FrontendAssetParser()
    try:
        parser.feed(index.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"index.html unreadable: {type(exc).__name__}")
        return proof
    assets: dict[str, dict[str, str]] = {}
    for key, refs, suffix in (
        ("js", parser.module_scripts, ".js"),
        ("css", parser.stylesheets, ".css"),
    ):
        names = [_frontend_asset_name_from_ref(ref, suffix) for ref in refs]
        names = [name for name in names if name]
        if len(names) != 1:
            errors.append(f"expected exactly one {key} asset reference")
            continue
        asset_path = dist_web / "assets" / names[0]
        if not asset_path.is_file():
            errors.append(f"{key} asset missing: {names[0]}")
            continue
        assets[key] = {"name": names[0], "sha256": _sha256_file(asset_path)}
    proof["assets"] = assets
    proof["ok"] = not errors
    return proof


def _verify_candidate_frontend_artifact(dist_web: Path, sha: str) -> dict[str, Any]:
    manifest_path = dist_web / _FRONTEND_ARTIFACT_MANIFEST
    if not dist_web.is_dir():
        return {"ok": False, "error": "dist-web missing", "dist_web": str(dist_web)}
    if not manifest_path.is_file():
        return {"ok": False, "error": "artifact manifest missing", "dist_web": str(dist_web)}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"artifact manifest unreadable: {exc}"}
    if not isinstance(manifest, dict):
        return {"ok": False, "error": "artifact manifest is not an object"}
    if manifest.get("candidate_sha") != sha:
        return {
            "ok": False,
            "error": "artifact candidate SHA mismatch",
            "candidate_sha": manifest.get("candidate_sha"),
            "expected_sha": sha,
        }
    if manifest.get("source_head") != sha:
        return {
            "ok": False,
            "error": "artifact source HEAD mismatch",
            "source_head": manifest.get("source_head"),
            "expected_sha": sha,
        }
    if not manifest.get("source_tree"):
        return {"ok": False, "error": "artifact source tree missing"}
    index = dist_web / "index.html"
    if not index.is_file():
        return {"ok": False, "error": "dist-web index.html missing"}
    bytes_proof = _candidate_frontend_bytes_proof(dist_web)
    if not bytes_proof.get("ok"):
        return {
            "ok": False,
            "error": "artifact bytes proof failed",
            "errors": bytes_proof.get("errors", []),
        }
    if manifest.get("index_sha256") != bytes_proof.get("index_sha256"):
        return {
            "ok": False,
            "error": "artifact index hash mismatch",
            "expected": manifest.get("index_sha256"),
            "actual": bytes_proof.get("index_sha256"),
        }
    if manifest.get("assets") != bytes_proof.get("assets"):
        return {
            "ok": False,
            "error": "artifact asset hash mismatch",
            "expected": manifest.get("assets"),
            "actual": bytes_proof.get("assets"),
        }
    return {
        "ok": True,
        "candidate_sha": sha,
        "manifest": str(manifest_path),
        "dist_web": str(dist_web),
        "built_at": manifest.get("built_at"),
        "index_sha256": bytes_proof["index_sha256"],
        "assets": bytes_proof["assets"],
    }


def _prepare_candidate_frontend_artifact(
    runner: Runner, *, sha: str, clerk_key: str
) -> dict[str, Any]:
    cockpit = _WORKTREE / "cockpit"
    dist_web = cockpit / "dist-web"
    if runner.dry_run:
        print(f"[dry-run] (cwd={cockpit}) npm ci")
        print(
            f"[dry-run] (cwd={cockpit}) "
            "VITE_CLERK_PUBLISHABLE_KEY=<from fly.toml> npm run build:web"
        )
        return {
            "ok": True,
            "planned": True,
            "dist_web": str(dist_web),
            "candidate_sha": sha,
        }

    if dist_web.exists():
        shutil.rmtree(dist_web)
    head_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(_WORKTREE),
        timeout=30,
        check=False,
        capture_output=True,
        text=True,
    )
    _must(runner, "candidate_source_head", head_result)
    source_head = head_result.stdout.strip()
    if source_head != sha:
        raise SystemExit(
            f"candidate frontend artifact source HEAD {source_head!r} does not match {sha!r}"
        )
    tree_result = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=str(_WORKTREE),
        timeout=30,
        check=False,
        capture_output=True,
        text=True,
    )
    _must(runner, "candidate_source_tree", tree_result)
    source_tree = tree_result.stdout.strip()
    clean_result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", "cockpit"],
        cwd=str(_WORKTREE),
        timeout=30,
        check=False,
        capture_output=True,
        text=True,
    )
    _must(runner, "candidate_frontend_source_clean", clean_result)
    dirty_frontend = clean_result.stdout.strip()
    if dirty_frontend:
        raise SystemExit(
            "candidate frontend source tree is dirty; refusing exact-sha artifact build"
        )
    lock_hash = _sha256_file(cockpit / "package-lock.json")
    stamp = cockpit / "node_modules" / ".wave2-lock-sha"
    if stamp.exists() and stamp.read_text(encoding="utf-8").strip() == lock_hash:
        print("[deploy] npm ci skipped — lockfile unchanged since last install")
    else:
        install = subprocess.run(
            ["npm", "ci", "--legacy-peer-deps"],
            cwd=str(cockpit),
            timeout=600,
            check=False,
            capture_output=True,
            text=True,
        )
        _must(runner, "npm_ci", install)
        if (cockpit / "node_modules").is_dir():
            stamp.write_text(lock_hash, encoding="utf-8")

    build = subprocess.run(
        ["npm", "run", "build:web"],
        cwd=str(cockpit),
        timeout=600,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "VITE_CLERK_PUBLISHABLE_KEY": clerk_key},
    )
    _must(runner, "frontend_build_web", build)
    if not dist_web.is_dir():
        raise SystemExit(f"candidate frontend artifact build did not create {dist_web}")
    if not (dist_web / "index.html").is_file():
        raise SystemExit("candidate frontend artifact build did not create dist-web/index.html")
    bytes_proof = _candidate_frontend_bytes_proof(dist_web)
    if not bytes_proof.get("ok"):
        raise SystemExit(f"candidate frontend artifact bytes are invalid: {bytes_proof}")
    manifest_path = dist_web / _FRONTEND_ARTIFACT_MANIFEST
    manifest_path.write_text(
        json.dumps(
            {
                "candidate_sha": sha,
                "source_head": source_head,
                "source_tree": source_tree,
                "source_worktree": str(_WORKTREE),
                "index_sha256": bytes_proof["index_sha256"],
                "assets": bytes_proof["assets"],
                "build_command": "npm run build:web",
                "built_at": datetime.now(timezone.utc).isoformat(),
                "artifact_contract": "wave2_exact_candidate_frontend",
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    proof = _verify_candidate_frontend_artifact(dist_web, sha)
    if not proof.get("ok"):
        raise SystemExit(f"candidate frontend artifact is not exact-sha bound: {proof}")
    return proof


def deploy_candidate(runner: Runner, sha: str) -> dict[str, Any]:
    """Build + start the candidate stack and wire Tailscale serve."""
    run_dir = _proof_root()
    if not runner.dry_run:
        run_dir.mkdir(parents=True, exist_ok=True)
    state_dir = _state_dir(sha)
    image_id = _candidate_image_id(runner)
    clerk_key = _read_clerk_publishable_key()

    steps: dict[str, Any] = {"sha": sha, "state_dir": str(state_dir), "image": image_id}

    # (1) candidate state dir
    runner.run(["mkdir", "-p", str(state_dir)], timeout=30)

    # (2) generate candidate.env by allowlist. The env file (REAL secret
    # values) lives under the candidate state root OUTSIDE the repo tree —
    # never under data/audits/proof/ where a tarball/`git add -f` could leak
    # it (adversarial-review finding). The names-only audit (no values) stays
    # with the run's proof artifacts.
    env_out = state_dir.parent / "candidate.env"
    audit_out = run_dir / "candidate_env_audit.json"
    _must(
        runner,
        "make_candidate_env",
        runner.run(
            [
                sys.executable,
                str(_WORKTREE / "infra" / "candidate" / "make_candidate_env.py"),
                "--source",
                str(_ROOT / "services" / ".env"),
                "--source",
                str(_ROOT / "infra" / "docker" / "umh.env"),
                "--out",
                str(env_out),
                "--audit-out",
                str(audit_out),
                "--state-dir",
                "/state/umh",
                "--build-commit",
                sha,
            ],
            timeout=30,
        ),
    )

    # (3) retire any stale candidate containers before preparing new artifacts.
    # If the frontend build fails, no previous nginx may remain alive serving a
    # stale dist-web under this exact SHA.
    _remove_container_and_wait(runner, _CANDIDATE_CONTAINER)
    _remove_container_and_wait(runner, _CANDIDATE_NGINX_CONTAINER)

    # (4) build the candidate frontend and prove the served artifact binds to this SHA
    # before the operator imports/configures its static routes and /api/umh/build info.
    artifact = _prepare_candidate_frontend_artifact(runner, sha=sha, clerk_key=clerk_key)
    steps["dist_web"] = artifact.get("dist_web")
    steps["frontend_artifact"] = artifact
    dist_web = Path(str(artifact.get("dist_web") or (_WORKTREE / "cockpit" / "dist-web")))

    # (5) candidate operator container — SAME image, worktree mounted read-only,
    # candidate state dir mounted rw, allowlisted env only.
    _must(
        runner,
        "docker_run_operator",
        runner.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                _CANDIDATE_CONTAINER,
                "--network",
                _OPERATOR_DOCKER_NETWORK,
                "-v",
                f"{_WORKTREE}:/app:ro",
                "-v",
                f"{state_dir}:/state/umh",
                "-e",
                "UMH_STATE_DIR=/state/umh",
                "-e",
                "PYTHONDONTWRITEBYTECODE=1",
                "-e",
                "PYTHONPATH=/app",
                "-e",
                "UMH_ROOT=/app",
                "-e",
                f"UMH_BUILD_COMMIT={sha}",
                # The fixture workspace's DECLARED writable-path authority. The
                # candidate materializes every Task of the fixture objective with
                # exactly this least-privilege scope (see
                # objective_plan_routes._declared_workspace_scope). Sourced from
                # the ONE canonical map (field_task_scope.FIXTURE_ALLOWED_PATHS),
                # never a second literal. Without it, Tasks persist with
                # scope_declared=False and every legitimate worker diff is
                # unverifiable (field run 20260725T230726Z, ninth layer).
                "-e",
                f"UMH_WORKSPACE_WRITABLE_PATHS={_smoke_workspace_scope()}",
                # The A/B/C/D lane DECLARATION. Without it the candidate's
                # planning rail compiles ONE umbrella Task and the multi-lane
                # journey is unsatisfiable by construction (field run
                # 20260726T025143Z-p1). Built from the one canonical scope map.
                "-e",
                f"UMH_WORKSPACE_LANES={_declared_lanes_json()}",
                "--env-file",
                str(env_out),
                "-p",
                f"127.0.0.1:{_CANDIDATE_API_HOST_PORT}:{_CANDIDATE_API_PORT}",
                image_id,
                "python3",
                "-m",
                "uvicorn",
                "services.operator_api:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(_CANDIDATE_API_PORT),
            ],
            timeout=120,
        ),
    )

    # (6) render nginx.candidate.conf from the template and start nginx:alpine
    conf_out = run_dir / "nginx.candidate.conf"
    template = _WORKTREE / "infra" / "candidate" / "nginx.candidate.conf.template"
    # The upstream MUST be the actual wave2 operator container name (the wave1
    # template hardcoded os-operator-candidate, which does not resolve on the
    # network with the -w2 suffix and crashes nginx -> 502). Substitute the real
    # name at render time so the -w2 container is always the resolved backend.
    upstream = f"{_CANDIDATE_CONTAINER}:{_CANDIDATE_API_PORT}"
    if runner.dry_run:
        print(f"[dry-run] render {template} → {conf_out} (upstream {upstream})")
    else:
        rendered = template.read_text(encoding="utf-8").replace("${CANDIDATE_UPSTREAM}", upstream)
        if "${CANDIDATE_UPSTREAM}" in rendered:  # fail closed on unrendered token
            raise RuntimeError("nginx template still has an unrendered ${CANDIDATE_UPSTREAM}")
        conf_out.write_text(rendered, encoding="utf-8")
    _must(
        runner,
        "docker_run_nginx",
        runner.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                _CANDIDATE_NGINX_CONTAINER,
                "--network",
                _OPERATOR_DOCKER_NETWORK,
                "-v",
                f"{dist_web}:/usr/share/nginx/html:ro",
                "-v",
                f"{conf_out}:/etc/nginx/conf.d/default.conf:ro",
                "-p",
                f"127.0.0.1:{_CANDIDATE_NGINX_HOST_PORT}:8080",
                "nginx:alpine",
            ],
            timeout=90,
        ),
    )

    # (6) Tailscale serve: snapshot FIRST (stable path, first-write-wins so a
    # redeploy never clobbers the production snapshot), register CRASH-ONLY
    # restore handlers, then swing the origin to the candidate nginx with
    # `serve --bg` (persists in tailscaled beyond this process — required,
    # because smoke/run are separate invocations). Happy-path restore of
    # production serve happens exactly once, in teardown. HTTPS serve requires
    # tailnet TLS certs (owner-gated Tailscale account setting). If cert
    # issuance is unavailable the --https serve HANGS on cert provisioning;
    # probe first and record a clear owner-action verdict rather than blocking.
    # There is no automatic plaintext fallback for the Session-1 run because
    # Clerk requires HTTPS.
    _snapshot_tailscale_serve(runner, run_dir, sha=sha)
    _install_crash_handlers(runner, sha)
    # Probe cert issuance WITHOUT dropping key material into the source tree:
    # `tailscale cert` writes <host>.crt/<host>.key to CWD by default (a
    # freshly-minted private key landed in the worktree on 2026-07-21 —
    # removed, never committed). Direct both files to the candidate's state
    # root, which lives outside the repo and outside the proof package.
    tls_probe_dir = state_dir.parent / "tls"
    if runner.dry_run:
        print(f"[dry-run] would probe `tailscale cert {_origin_host()}` → {tls_probe_dir}")
        https_available = True
        cert_probe = None
    else:
        tls_probe_dir.mkdir(parents=True, exist_ok=True)
        cert_probe = subprocess.run(
            [
                "tailscale",
                "cert",
                "--cert-file",
                str(tls_probe_dir / "probe.crt"),
                "--key-file",
                str(tls_probe_dir / "probe.key"),
                _origin_host(),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        https_available = cert_probe.returncode == 0 and "does not support" not in (
            cert_probe.stdout + cert_probe.stderr
        )
    if not https_available:
        steps["serve"] = {
            "wired": False,
            "https_available": False,
            "owner_action_required": (
                "Enable HTTPS certificates for this tailnet "
                "(Tailscale admin console → DNS → HTTPS Certificates), then re-run "
                "deploy-candidate. Clerk auth requires an HTTPS origin, so the "
                "Session-1 field run cannot proceed over plaintext."
            ),
            "cert_probe": (cert_probe.stdout + cert_probe.stderr).strip()[:200],
        }
        steps["ready"] = False
        steps["deploy_ok"] = False
        steps["failure_reason"] = "candidate HTTPS serve is unavailable"
        return steps
    serve = runner.run(
        [
            "tailscale",
            "serve",
            "--bg",
            f"--https={_CANDIDATE_TLS_PORT}",
            f"http://127.0.0.1:{_CANDIDATE_NGINX_HOST_PORT}",
        ],
        timeout=45,
        check=False,
    )
    steps["serve"] = {
        "wired": bool(serve is None or serve.returncode == 0),
        "https_available": True,
    }

    # (7) readiness checks — WAIT for the operator to finish required Wave 2
    # initialization. /health is liveness only; /ready is the semantic gate.
    readiness = _wait_candidate_ready(runner, timeout_s=180.0)
    steps["readiness"] = readiness
    checks = {
        "candidate_api_health": _http_ok(
            runner, f"http://127.0.0.1:{_CANDIDATE_API_HOST_PORT}/health"
        ),
        "candidate_api_ready": _http_ok(
            runner, f"http://127.0.0.1:{_CANDIDATE_API_HOST_PORT}/ready"
        ),
        "origin_root": _http_ok(runner, _ORIGIN, expect_status={200, 401}),
        # /api/umh/health does NOT exist on the operator API (production 502s
        # on it too — verified 2026-07-22). Probe a REAL route the trial
        # drives: /api/umh/objective-plan behind Clerk auth. An unauthenticated
        # 401 is the PROOF the whole chain (tailscale serve → candidate nginx →
        # candidate API → auth middleware) is wired; 200 never happens here.
        "origin_api_reachable": _http_ok(
            runner, f"{_ORIGIN}/api/umh/objective-plan", expect_status={200, 401}
        ),
        "origin_ready": _http_ok(runner, f"{_ORIGIN}/ready", expect_status={200}),
    }
    steps["health"] = checks

    # READINESS CONTROLS THE VERDICT (finding SEC-C3). Readiness used to be
    # recorded and then ignored: deploy_candidate returned unconditionally and
    # main() returned 0, so a candidate that never came up reported success and
    # an automated driver would have proceeded to spend worker quota against a
    # dead stack. A NOT-ready deploy is now a hard failure.
    failed_checks = [
        name for name, c in checks.items() if isinstance(c, dict) and c.get("ok") is False
    ]
    if runner.dry_run:
        # A dry run asserts NOTHING about a live candidate — it only echoes the
        # command shapes. Reporting NOT READY here would make every dry-run
        # exit non-zero and mark the harness self-check FAIL, which is a false
        # negative, not a safety property.
        steps["deploy_ok"] = True
        steps["dry_run"] = True
        return steps
    ready = bool(readiness.get("ready")) if isinstance(readiness, dict) else False
    serve_wired = isinstance(steps.get("serve"), dict) and steps["serve"].get("wired") is True
    steps["deploy_ok"] = ready and serve_wired and not failed_checks
    if not steps["deploy_ok"]:
        steps["failure_reason"] = (
            f"readiness={'ok' if ready else 'NOT READY'}; "
            f"serve={'wired' if serve_wired else 'NOT WIRED'}; "
            f"failed_checks={failed_checks or 'none'}"
        )
    return steps


def _http_ok(runner: Runner, url: str, expect_status: set[int] | None = None) -> dict[str, Any]:
    """Curl-style read-only GET; returns {ok, status}. Dry-run → planned only."""
    ok_set = expect_status or {200}
    if runner.dry_run:
        print(f"[dry-run] curl -sS -o /dev/null -w '%{{http_code}}' {url}")
        return {"planned": url, "expect_status": sorted(ok_set)}
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "url": url}
    return {"ok": status in ok_set, "status": status, "url": url}


def _wait_candidate_ready(
    runner: Runner, *, timeout_s: float = 180.0, settle_s: float = 3.0
) -> dict[str, Any]:
    """Block until the candidate is semantically ready THROUGH nginx.

    ``/health`` is process liveness. ``/ready`` is the governed Wave 2 readiness
    contract: required operator wiring is up, while optional warmup may still be
    WARMING or fail-soft.
    """
    if runner.dry_run:
        print("[dry-run] wait for candidate semantic readiness via origin /ready")
        return {"planned": "candidate-ready"}
    url = f"{_candidate_origin()}/ready"
    deadline = time.time() + timeout_s
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = _http_ok(runner, url, expect_status={200})
        if last.get("ok"):
            # Small settle so in-flight worker warm-up finishes before traffic.
            time.sleep(settle_s)
            return {"ready": True, "waited_s": round(timeout_s - (deadline - time.time()), 1)}
        time.sleep(2.0)
    return {"ready": False, "last": last}


# ─────────────────────────────────────────────────────────────────────────────
# preflight
# ─────────────────────────────────────────────────────────────────────────────
def preflight(runner: Runner, sha: str) -> dict[str, Any]:
    """Relay health + nodes, mesh reachability, Beast→origin, echo start shape."""
    out: dict[str, Any] = {}

    # Relay health/nodes through op run (bearer injected) — read-only curl :8095.
    mesh_tpl = str(_ROOT / "services" / "mesh.env.tpl")
    health_cmd = (
        f"op run --env-file={shlex.quote(mesh_tpl)} -- "
        'bash -c \'curl -sS -H "Authorization: Bearer $UMH_MESH_RELAY_SECRET" '
        "http://127.0.0.1:8095/health'"
    )
    r = runner.shell(health_cmd, timeout=30)
    out["mesh_health"] = _shell_summary(runner, r)

    # Read-only mesh dispatch: schtasks + query session on the executor.
    out["schtasks_query"] = _preflight_observation_read(
        runner,
        'schtasks /query /tn "UMH Node Daemon" /v /fo LIST',
        gate="schtasks_query",
    )
    # query.exe/qwinsta are absent from the daemon shell's (WOW64) PATH —
    # probe the session id directly; the collector does the full
    # WTSGetActiveConsoleSessionId proof itself.
    out["query_session"] = _mesh_read(
        runner,
        'powershell -NoProfile -Command "[System.Diagnostics.Process]::GetCurrentProcess().SessionId"',
    )

    # Beast → origin reachability (read-only curl from the executor).
    out["beast_to_origin"] = _mesh_read(runner, f"curl -sS -o NUL -w %{{http_code}} {_ORIGIN}")

    # Echo (never execute) the powershell Start-Process command shape.
    try:
        start_shape = _build_start_command(
            run_id="RUNID", pass_num=1, scenario="full", url=_ORIGIN or "", candidate_commit="SHA"
        )
        out["start_command_shape"] = {
            "ok": True,
            "command": _SECRET_REDACT_RE.sub("<redacted>", start_shape),
        }
    except ValueError as exc:
        out["start_command_shape"] = {"ok": False, "error": str(exc)}
    print("start-command shape (echo only):")
    print(f"  {out['start_command_shape']}")

    out["authority_contract_probe"] = _authority_contract_probe(runner)
    out["activation_rehearsal"] = activation_rehearsal(runner, sha, iterations=3)
    out["codex_spark_probe"] = _beast_codex_spark_probe(runner, sha)

    # PREFLIGHT VERDICT (finding SEC-C3): mesh relay, the executor daemon in an
    # interactive session, and Beast->origin reachability are all REQUIRED. A
    # preflight that records a failure must exit non-zero rather than reporting
    # a green shape. (beast_to_origin legitimately fails before deploy — it is
    # only asserted once an origin is expected to exist.)
    required = (
        "mesh_health",
        "schtasks_query",
        "query_session",
        "authority_contract_probe",
        "activation_rehearsal",
        "codex_spark_probe",
        "start_command_shape",
    )
    failed = [k for k in required if isinstance(out.get(k), dict) and out[k].get("ok") is False]
    mesh = out.get("mesh_health") or {}
    if isinstance(mesh, dict) and mesh.get("returncode") not in (0, None):
        failed.append("mesh_health")
    out["ok"] = not failed
    if failed:
        out["failure_reason"] = f"preflight checks failed: {sorted(set(failed))}"
    return out


def _codex_probe_request_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"codex-spark-{ts}-{uuid4().hex[:8]}"


def _codex_probe_argv(*, sha: str, request_id: str) -> list[str]:
    return [
        "python",
        rf"{_BEAST_WT}\scripts\wave2_codex_spark_probe.py",
        "--sha",
        sha,
        "--worktree",
        _BEAST_WT,
        "--model",
        "gpt-5.3-codex-spark",
        "--expected-version",
        "codex-cli 0.147.0",
        "--timeout",
        "180",
        "--request-id",
        request_id,
    ]


def _codex_probe_dir(request_id: str) -> str:
    return rf"{_BEAST_EVIDENCE_DIR}\{request_id}"


def _codex_probe_launch_command(*, sha: str, request_id: str) -> str:
    """Launch the real Codex/Spark probe asynchronously on Beast.

    The synchronous mesh shell path is intentionally short-lived: it only writes
    a manifest and starts a wrapper. The wrapper owns the long Codex invocation
    and publishes status/result files atomically for read-only polling.
    """
    probe_dir = _codex_probe_dir(request_id)
    wrapper_path = rf"{probe_dir}\run_probe.ps1"
    manifest_path = rf"{probe_dir}\manifest.json"
    status_path = rf"{probe_dir}\status.json"
    result_path = rf"{probe_dir}\result.json"
    stdout_path = rf"{probe_dir}\stdout.jsonl"
    stderr_path = rf"{probe_dir}\stderr.log"
    probe_script = rf"{_BEAST_WT}\scripts\wave2_codex_spark_probe.py"
    model = "gpt-5.3-codex-spark"
    version = "codex-cli 0.147.0"
    wrapper = rf"""
$ErrorActionPreference = 'Continue'
$requestId = '{request_id}'
$sha = '{sha}'
$worktree = '{_BEAST_WT}'
$probeScript = '{probe_script}'
$statusPath = '{status_path}'
$resultPath = '{result_path}'
$stdoutPath = '{stdout_path}'
$stderrPath = '{stderr_path}'
$model = '{model}'
$expectedVersion = '{version}'
function Write-AtomicJson([string]$Path, [object]$Obj) {{
  $tmp = "$Path.tmp"
  $Obj | ConvertTo-Json -Compress -Depth 32 | Set-Content -LiteralPath $tmp -Encoding UTF8
  Move-Item -LiteralPath $tmp -Destination $Path -Force
}}
function FileSha256([string]$Path) {{
  if (Test-Path -LiteralPath $Path) {{
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
  }}
  return ""
}}
Write-AtomicJson $statusPath ([ordered]@{{
  request_id=$requestId; candidate_sha=$sha; state='starting';
  started_at=(Get-Date).ToUniversalTime().ToString('o')
}})
try {{
  $argv = @(
    $probeScript, '--sha', $sha, '--worktree', $worktree,
    '--model', $model, '--expected-version', $expectedVersion,
    '--timeout', '180', '--request-id', $requestId
  )
  $proc = Start-Process -FilePath 'python' -ArgumentList $argv -WorkingDirectory $worktree `
    -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath `
    -WindowStyle Hidden -PassThru
  Start-Sleep -Milliseconds 250
  $procMeta = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int]$proc.Id)
  Write-AtomicJson $statusPath ([ordered]@{{
    request_id=$requestId; candidate_sha=$sha; state='running';
    pid=$proc.Id; process=$procMeta; stdout_path=$stdoutPath; stderr_path=$stderrPath;
    started_at=(Get-Date).ToUniversalTime().ToString('o')
  }})
  $proc.WaitForExit()
  $rawOut = ''
  $rawErr = ''
  if (Test-Path -LiteralPath $stdoutPath) {{ $rawOut = Get-Content -Raw -LiteralPath $stdoutPath }}
  if (Test-Path -LiteralPath $stderrPath) {{ $rawErr = Get-Content -Raw -LiteralPath $stderrPath }}
  $probe = $null
  $parseError = ''
  try {{ if ($rawOut) {{ $probe = $rawOut | ConvertFrom-Json }} }} catch {{ $parseError = [string]$_ }}
  $probeOk = $false
  if ($null -ne $probe -and $probe.ok -eq $true) {{ $probeOk = $true }}
  $state = 'failed'
  if ($proc.ExitCode -eq 0 -and $probeOk) {{ $state = 'succeeded' }}
  $result = [ordered]@{{
    request_id=$requestId; candidate_sha=$sha; state=$state; exit_code=$proc.ExitCode;
    probe=$probe; parse_error=$parseError; raw_stdout=$rawOut; raw_stderr=$rawErr;
    raw_stdout_sha256=(FileSha256 $stdoutPath); raw_stderr_sha256=(FileSha256 $stderrPath);
    ended_at=(Get-Date).ToUniversalTime().ToString('o')
  }}
  Write-AtomicJson $resultPath $result
  Write-AtomicJson $statusPath ([ordered]@{{
    request_id=$requestId; candidate_sha=$sha; state=$state; pid=$proc.Id;
    exit_code=$proc.ExitCode; result_path=$resultPath; stdout_path=$stdoutPath;
    stderr_path=$stderrPath; ended_at=(Get-Date).ToUniversalTime().ToString('o')
  }})
}} catch {{
  $err = [string]$_
  Write-AtomicJson $resultPath ([ordered]@{{
    request_id=$requestId; candidate_sha=$sha; state='failed'; error=$err;
    ended_at=(Get-Date).ToUniversalTime().ToString('o')
  }})
  Write-AtomicJson $statusPath ([ordered]@{{
    request_id=$requestId; candidate_sha=$sha; state='failed'; error=$err;
    ended_at=(Get-Date).ToUniversalTime().ToString('o')
  }})
}}
"""
    wrapper_b64 = base64.b64encode(wrapper.encode("utf-8")).decode("ascii")
    launch = rf"""
$ErrorActionPreference = 'Stop'
$requestId = '{request_id}'
$probeDir = '{probe_dir}'
$wrapperPath = '{wrapper_path}'
$manifestPath = '{manifest_path}'
New-Item -ItemType Directory -Force -Path $probeDir | Out-Null
$wrapper = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{wrapper_b64}'))
Set-Content -LiteralPath $wrapperPath -Value $wrapper -Encoding UTF8
$cliPath = (Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
$cliVersion = ''
try {{ $cliVersion = (codex --version 2>&1 | Out-String).Trim() }} catch {{ $cliVersion = [string]$_ }}
$wrapperProc = Start-Process -FilePath 'powershell' `
  -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$wrapperPath) `
  -WorkingDirectory '{_BEAST_WT}' -WindowStyle Hidden -PassThru
$manifest = [ordered]@{{
  request_id=$requestId; candidate_sha='{sha}'; provider='codex';
  model='gpt-5.3-codex-spark'; expected_version='codex-cli 0.147.0';
  wrapper_pid=$wrapperProc.Id; wrapper_path=$wrapperPath; status_path='{status_path}';
  result_path='{result_path}'; stdout_path='{stdout_path}'; stderr_path='{stderr_path}';
  worktree='{_BEAST_WT}'; probe_script='{probe_script}'; cli_path=$cliPath;
  cli_version=$cliVersion; launched_at=(Get-Date).ToUniversalTime().ToString('o')
}}
$manifest | ConvertTo-Json -Compress -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$manifest | ConvertTo-Json -Compress -Depth 8
"""
    return _powershell_encoded_command(launch)


def _codex_probe_read_command(request_id: str) -> str:
    probe_dir = _codex_probe_dir(request_id)
    ps = rf"""
$ErrorActionPreference = 'Continue'
$dir = '{probe_dir}'
$manifestPath = Join-Path $dir 'manifest.json'
$statusPath = Join-Path $dir 'status.json'
$resultPath = Join-Path $dir 'result.json'
$manifest = $null
$status = $null
$result = $null
if (Test-Path -LiteralPath $manifestPath) {{ $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json }}
if (Test-Path -LiteralPath $statusPath) {{ $status = Get-Content -Raw -LiteralPath $statusPath | ConvertFrom-Json }}
if (Test-Path -LiteralPath $resultPath) {{ $result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json }}
$pids = @()
if ($null -ne $manifest -and $manifest.wrapper_pid) {{ $pids += [int]$manifest.wrapper_pid }}
if ($null -ne $status -and $status.pid) {{ $pids += [int]$status.pid }}
$processes = @()
foreach ($pid in ($pids | Select-Object -Unique)) {{
  $p = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int]$pid)
  if ($null -ne $p) {{
    $processes += ($p | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate,SessionId)
  }}
}}
$broad = @(Get-CimInstance Win32_Process | Where-Object {{
  ([string]$_.CommandLine) -like "*{request_id}*" -or
  ([string]$_.CommandLine) -like "*wave2_codex_spark_probe.py*"
}} | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate,SessionId)
[pscustomobject]@{{
  request_id='{request_id}'; manifest=$manifest; status=$status; result=$result;
  processes=$processes; broad_residue=$broad
}} | ConvertTo-Json -Compress -Depth 32
"""
    return _powershell_encoded_command(ps)


def _codex_probe_cleanup_command(request_id: str) -> str:
    probe_dir = _codex_probe_dir(request_id)
    ps = rf"""
$ErrorActionPreference = 'Continue'
$dir = '{probe_dir}'
$manifestPath = Join-Path $dir 'manifest.json'
$statusPath = Join-Path $dir 'status.json'
$ids = @()
if (Test-Path -LiteralPath $manifestPath) {{
  $m = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
  if ($m.wrapper_pid) {{ $ids += [int]$m.wrapper_pid }}
}}
if (Test-Path -LiteralPath $statusPath) {{
  $s = Get-Content -Raw -LiteralPath $statusPath | ConvertFrom-Json
  if ($s.pid) {{ $ids += [int]$s.pid }}
}}
$before = @()
$terminated = @()
$errors = @()
foreach ($pid in ($ids | Select-Object -Unique)) {{
  $p = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int]$pid)
  if ($null -ne $p) {{
    $before += ($p | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate,SessionId)
    $cmd = [string]$p.CommandLine
    if ($cmd -like "*{request_id}*" -or $cmd -like "*{probe_dir}*" -or $cmd -like "*wave2_codex_spark_probe.py*") {{
      $out = (& cmd.exe /c "taskkill /PID $pid /T" 2>&1 | Out-String)
      Start-Sleep -Seconds 3
      $alive = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int]$pid)
      $forced = $false
      if ($null -ne $alive) {{
        $cmd2 = [string]$alive.CommandLine
        if ($cmd2 -like "*{request_id}*" -or $cmd2 -like "*{probe_dir}*" -or $cmd2 -like "*wave2_codex_spark_probe.py*") {{
          $out = $out + (& cmd.exe /c "taskkill /PID $pid /T /F" 2>&1 | Out-String)
          $forced = $true
        }} else {{
          $errors += "pid identity changed before force: $pid"
        }}
      }}
      $terminated += [pscustomobject]@{{pid=$pid; forced=$forced; output=$out}}
    }} else {{
      $errors += "pid identity mismatch: $pid"
    }}
  }}
}}
Start-Sleep -Seconds 1
$residue = @(Get-CimInstance Win32_Process | Where-Object {{
  ([string]$_.CommandLine) -like "*{request_id}*" -or
  ([string]$_.CommandLine) -like "*wave2_codex_spark_probe.py*"
}} | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate,SessionId)
$removed = $false
if ($residue.Count -eq 0 -and (Test-Path -LiteralPath $dir)) {{
  Remove-Item -LiteralPath $dir -Recurse -Force
  $removed = $true
}}
[pscustomobject]@{{
  request_id='{request_id}'; before=$before; terminated=$terminated;
  residue=$residue; removed=$removed; ok=($errors.Count -eq 0 -and $residue.Count -eq 0);
  errors=$errors
}} | ConvertTo-Json -Compress -Depth 16
"""
    return _powershell_encoded_command(ps)


def _beast_codex_spark_probe(
    runner: Runner, sha: str, *, poll_timeout_seconds: int = 260, poll_interval_seconds: int = 5
) -> dict[str, Any]:
    """Run the exact Beast Codex/Spark production-path probe as a preflight gate."""
    if runner.dry_run:
        return {"dry_run": True, "ok": True}
    request_id = _codex_probe_request_id()
    argv = _codex_probe_argv(sha=sha, request_id=request_id)
    command_digest = hashlib.sha256(
        json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    out = _durable_remote_shell(
        "",
        argv=argv,
        cwd=_BEAST_WT,
        max_len=262144,
        command_timeout=220,
        dispatch_timeout=poll_timeout_seconds,
        operation_type="wave2_codex_spark_probe",
        correlation_id=f"codex-spark-{request_id}",
        candidate_sha=sha,
    )
    probe: dict[str, Any] | None = None
    parse_error = ""
    try:
        parsed = json.loads(str(out.get("stdout") or "{}"))
        if isinstance(parsed, dict):
            probe = parsed
    except ValueError as exc:
        parse_error = str(exc)
    cleanup = out.get("cleanup") if isinstance(out.get("cleanup"), dict) else {}
    cleanup_ok = cleanup.get("process_residue") == [] if isinstance(cleanup, dict) else False
    ok = (
        out.get("raw_status") == "SUCCEEDED"
        and out.get("ok") is True
        and isinstance(probe, dict)
        and probe.get("ok") is True
        and cleanup_ok
    )
    return {
        "ok": ok,
        "request_id": request_id,
        "argv": argv,
        "argv_digest": command_digest,
        "launcher_command_chars": sum(len(part) for part in argv),
        "transport": out,
        "probe": probe,
        "cleanup": cleanup,
        "parse_error": parse_error,
        "failure_reason": None if ok else "real Beast Codex/Spark production path not proven",
    }


def _authority_contract_probe(runner: Runner) -> dict[str, Any]:
    """Non-field probe for the grant producer/consumer authority contract.

    The probe uses a temporary UMH_STATE_DIR outside candidate runtime state. It
    exercises the real source defaults that the HUD path relies on:
    plan acceptance source -> execution authorization request -> execution
    authorization decision -> persisted active grant -> approved WorkPackets.
    It never writes to a field run's state and deletes its temp namespace.
    """
    if runner.dry_run:
        return {"dry_run": True, "ok": True}

    old_state = os.environ.get("UMH_STATE_DIR")
    old_root = os.environ.get("UMH_ROOT")
    previous_runtime: Any = None
    previous_governed: Any = None
    previous_organism_accessor: Any = None
    approval_routes: Any = None
    tmp = tempfile.mkdtemp(prefix="umh-wave2-auth-preflight-")
    correlation = "preflight-authority-contract"
    try:
        os.environ["UMH_STATE_DIR"] = os.path.join(tmp, "state")
        os.environ["UMH_ROOT"] = str(_WORKTREE)

        sys.path.insert(0, str(_WORKTREE))
        _preseed_worktree_substrate()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        import transports.api.cockpit_unified_approval_routes as approval_routes
        from substrate.execution.attempts.decisions import (
            ExecutionAuthorizationDecisionSource,
            execution_decision_ref,
            request_execution_authorization,
        )
        from substrate.execution.attempts.records import ExecutionAuthorizationGrantStatus
        from substrate.execution.attempts.store import ExecutionAttemptStore
        from substrate.execution.planning.decisions import (
            ObjectivePlanDecisionSource,
            plan_decision_ref,
        )
        from substrate.execution.planning.records import ObjectivePlanRecord
        from substrate.execution.planning.store import PlanningStore
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.mutation_registry import MutationRegistry
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket
        from substrate.sockets import organism_port
        from substrate.workstation.unified_approval_runtime import UnifiedApprovalRuntime

        probe_state = Path(os.environ["UMH_STATE_DIR"])
        event_spine = EventSpine(
            persist_path=str(probe_state / "events" / "organism_events.jsonl")
        )
        mutation_registry = MutationRegistry()
        journal = ExecutionJournal(
            persist_path=str(probe_state / "operator" / "mutation_journal.jsonl")
        )
        mode = ExecutionModeManager(
            initial_mode=ExecutionMode.AUTONOMOUS,
            event_spine=event_spine,
        )
        spine = GovernedExecutionSpine(
            event_spine=event_spine,
            execution_mode=mode,
            mutation_registry=mutation_registry,
            journal=journal,
        )

        previous_organism_accessor = getattr(organism_port, "_get_organism_fn", None)
        probe_daemon = SimpleNamespace(
            governed_spine=spine,
            mutation_registry=mutation_registry,
        )
        organism_port.register_organism_accessor(lambda: probe_daemon)

        planning_dir = probe_state / "operator" / "objective_planning"
        planning = PlanningStore(
            sessions_path=str(planning_dir / "planning_sessions.jsonl"),
            plans_path=str(planning_dir / "objective_plans.jsonl"),
            grounding_path=str(planning_dir / "grounding_snapshots.jsonl"),
            current_path=str(planning_dir / "current_states.jsonl"),
            desired_path=str(planning_dir / "desired_states.jsonl"),
            gaps_path=str(planning_dir / "gap_models.jsonl"),
        )
        plan = ObjectivePlanRecord(
            plan_record_id="opr-preflight-auth",
            objective_id="goal-preflight-auth",
            graph_version=1,
            status="awaiting_approval",
            conversation_id="conv-preflight-auth",
            workpacket_ids=["wp-preflight-a", "wp-preflight-b"],
            objective_text="preflight authority contract probe",
            work_scope={"tenant_id": "tenant-preflight"},
        )
        planning.append_plan(plan)

        queue = UniversalWorkQueue()
        for packet_id in plan.workpacket_ids:
            packet = WorkPacket(
                title=packet_id,
                user_intent=f"probe {packet_id}",
                approval_gates=["execution_authorization_required"],
                work_scope={"tenant_id": "tenant-preflight"},
                status=PacketLifecycleStatus.PLANNED,
            )
            packet.packet_id = packet_id
            queue.ingest_work_packet(packet)

        store = ExecutionAttemptStore(
            attempts_path=str(
                probe_state / "operator" / "execution_attempts" / "execution_attempts.jsonl"
            ),
            grants_path=str(
                probe_state
                / "operator"
                / "execution_attempts"
                / "execution_authorization_grants.jsonl"
            ),
            readiness_path=str(
                probe_state
                / "operator"
                / "execution_attempts"
                / "readiness_assessments.jsonl"
            ),
            leases_path=str(
                probe_state / "operator" / "execution_attempts" / "environment_leases.jsonl"
            ),
            assignments_path=str(
                probe_state
                / "operator"
                / "execution_attempts"
                / "execution_assignments.jsonl"
            ),
        )

        objective_source = ObjectivePlanDecisionSource(
            store=planning,
        )
        execution_source = ExecutionAuthorizationDecisionSource(
            store=store,
            latest_plan_lookup=lambda _objective_id: planning.get_plan(plan.plan_record_id),
        )
        runtime = UnifiedApprovalRuntime(
            objective_plan=objective_source,
            execution_auth=execution_source,
        )
        app = FastAPI()
        app.include_router(approval_routes._build_router())
        client = TestClient(app)
        previous_runtime = getattr(approval_routes, "_approval_runtime", None)
        previous_governed = approval_routes.governed_mutation

        def _blocked_outer(**_kw: Any) -> Any:
            raise AssertionError("source-owned approval used generic approval_decide")

        approval_routes.configure(runtime)
        approval_routes.governed_mutation = _blocked_outer

        plan_res = client.post(
            "/unified-approval/approve",
            json={
                "approval_id": plan_decision_ref(plan),
                "source_type": "objective_plan",
                "decided_by": "preflight",
            },
        )
        if plan_res.status_code != 200:
            return {
                "ok": False,
                "reason": f"plan approval route returned {plan_res.status_code}",
            }
        plan_body = plan_res.json()
        if plan_body.get("action") != "approved":
            return {"ok": False, "reason": f"plan approval route failed: {plan_body}"}
        approved_plan = planning.get_plan(plan.plan_record_id)
        if approved_plan is None or approved_plan.status != "approved":
            return {"ok": False, "reason": "plan approval was not persisted"}

        grant, approval = request_execution_authorization(
            store,
            plan=approved_plan,
            task_frontier=list(approved_plan.workpacket_ids),
            tenant_id="tenant-preflight",
            principal_id="principal-preflight",
            membership_id="membership-preflight",
            conversation_id=approved_plan.conversation_id,
            correlation_id=correlation,
            requested_by="preflight",
        )
        if grant.correlation_id != correlation:
            return {"ok": False, "reason": "correlation_id was not preserved"}
        if approval.decision_ref != execution_decision_ref(approved_plan):
            return {"ok": False, "reason": "approval decision_ref does not match plan"}

        exec_res = client.post(
            "/unified-approval/approve",
            json={
                "approval_id": grant.decision_ref,
                "source_type": "execution_authorization",
                "decided_by": "preflight",
            },
        )
        if exec_res.status_code != 200:
            return {
                "ok": False,
                "reason": f"execution approval route returned {exec_res.status_code}",
            }
        exec_body = exec_res.json()
        if exec_body.get("action") != "approved":
            return {"ok": False, "reason": f"execution approval route failed: {exec_body}"}

        active = store.get_grant(grant.decision_ref)
        if active is None or active.status != ExecutionAuthorizationGrantStatus.ACTIVE.value:
            return {"ok": False, "reason": "active grant was not persisted"}
        if active.correlation_id != correlation:
            return {"ok": False, "reason": "active grant correlation mismatch"}
        if any(g.correlation_id == "foreign-run" for g in store.active_grants()):
            return {"ok": False, "reason": "foreign correlation unexpectedly matched"}
        verified_queue = UniversalWorkQueue()
        unapproved = [
            pid
            for pid in plan.workpacket_ids
            if verified_queue.get_packet(pid).status != PacketLifecycleStatus.APPROVED
        ]
        if unapproved:
            return {"ok": False, "reason": f"task activation incomplete: {unapproved}"}
        return {
            "ok": True,
            "correlation_id": correlation,
            "decision_ref": active.decision_ref,
            "grant_status": active.status,
            "task_frontier": list(active.task_frontier),
            "governed_spine": "real",
            "plan_approval_route": plan_body.get("action"),
            "execution_approval_route": exec_body.get("action"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    finally:
        if approval_routes is not None:
            approval_routes.configure(previous_runtime)
            if previous_governed is not None:
                approval_routes.governed_mutation = previous_governed
        if old_state is None:
            os.environ.pop("UMH_STATE_DIR", None)
        else:
            os.environ["UMH_STATE_DIR"] = old_state
        if old_root is None:
            os.environ.pop("UMH_ROOT", None)
        else:
            os.environ["UMH_ROOT"] = old_root
        try:
            from substrate.sockets import organism_port as _organism_port

            _organism_port._get_organism_fn = previous_organism_accessor
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _run_state_json(state_dir: Path, code: str, *, timeout: int = 30) -> dict[str, Any]:
    env = {
        **os.environ,
        "UMH_STATE_DIR": str(state_dir),
        "UMH_ROOT": str(_WORKTREE),
        "PYTHONPATH": str(_WORKTREE),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(_WORKTREE),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"state subprocess failed rc={proc.returncode} "
            f"stderr={_SECRET_REDACT_RE.sub('<redacted>', proc.stderr[-1000:])}"
        )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("state subprocess produced no JSON")
    return json.loads(lines[-1])


def activation_rehearsal(runner: Runner, sha: str, *, iterations: int = 3) -> dict[str, Any]:
    """Production-isomorphic, zero-quota execution-authorization rehearsal.

    This is intentionally stronger than ``_authority_contract_probe``. It starts
    the same candidate API image/entrypoint in a quarantined namespace, seeds a
    canonical approved-plan + ACTIVATING grant into the mounted state store,
    then POSTs through the real deployed HTTP approval route. No field collector,
    runner, worker, model invocation, or dispatch envelope is started.
    """
    if runner.dry_run:
        return {"ok": True, "dry_run": True, "iterations": iterations}

    proof_dir = _proof_root() / "activation_rehearsal"
    proof_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    image_id = _candidate_image_id(runner)

    for idx in range(1, iterations + 1):
        rehearse_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-r{idx}"
        root = Path("/var/lib/umh/rehearsals/wave2_activation") / sha / rehearse_id
        state_dir = root / "state" / "umh"
        env_out = root / "candidate.env"
        container = f"os-operator-candidate-w2-rehearsal-{idx}-{os.getpid()}"
        port = _free_local_port()
        summary: dict[str, Any] = {
            "rehearsal_id": rehearse_id,
            "container": container,
            "port": port,
            "state_dir": str(state_dir),
        }
        try:
            runner.run(["mkdir", "-p", str(state_dir)], timeout=30)
            _must(
                runner,
                "make_rehearsal_candidate_env",
                runner.run(
                    [
                        sys.executable,
                        str(_WORKTREE / "infra" / "candidate" / "make_candidate_env.py"),
                        "--source",
                        str(_ROOT / "services" / ".env"),
                        "--source",
                        str(_ROOT / "infra" / "docker" / "umh.env"),
                        "--out",
                        str(env_out),
                        "--state-dir",
                        "/state/umh",
                        "--build-commit",
                        sha,
                    ],
                    timeout=30,
                ),
            )

            correlation = f"rehearsal-{rehearse_id}"
            seed = _run_state_json(
                state_dir,
                f"""
import json
from pathlib import Path

from substrate.execution.attempts.decisions import request_execution_authorization
from substrate.execution.attempts.store import ExecutionAttemptStore
from substrate.execution.planning.records import ObjectivePlanRecord
from substrate.execution.planning.store import PlanningStore
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket

state_dir = Path({str(state_dir)!r})
(state_dir / "events").mkdir(parents=True, exist_ok=True)
planning = PlanningStore(
    sessions_path=str(state_dir / "operator" / "objective_planning" / "planning_sessions.jsonl"),
    plans_path=str(state_dir / "operator" / "objective_planning" / "objective_plans.jsonl"),
    grounding_path=str(state_dir / "operator" / "objective_planning" / "grounding_snapshots.jsonl"),
    current_path=str(state_dir / "operator" / "objective_planning" / "current_states.jsonl"),
    desired_path=str(state_dir / "operator" / "objective_planning" / "desired_states.jsonl"),
    gaps_path=str(state_dir / "operator" / "objective_planning" / "gap_models.jsonl"),
)
plan = ObjectivePlanRecord(
    plan_record_id={f"opr-rehearsal-{idx}"!r},
    objective_id={f"goal-rehearsal-{idx}"!r},
    graph_version=1,
    status="approved",
    conversation_id={f"conv-rehearsal-{idx}"!r},
    workpacket_ids={[f"wp-rehearsal-{idx}-a", f"wp-rehearsal-{idx}-b"]!r},
    objective_text="zero-quota activation rehearsal",
    work_scope={{"tenant_id": "tenant-rehearsal"}},
)
planning.append_plan(plan)
queue = UniversalWorkQueue()
for packet_id in plan.workpacket_ids:
    packet = WorkPacket(
        title=packet_id,
        user_intent=f"rehearsal {{packet_id}}",
        approval_gates=["execution_authorization_required"],
        work_scope={{"tenant_id": "tenant-rehearsal"}},
        status=PacketLifecycleStatus.PLANNED,
    )
    packet.packet_id = packet_id
    queue.ingest_work_packet(packet)
store = ExecutionAttemptStore()
grant, _approval = request_execution_authorization(
    store,
    plan=plan,
    task_frontier=list(plan.workpacket_ids),
    tenant_id="tenant-rehearsal",
    principal_id="principal-rehearsal",
    membership_id="membership-rehearsal",
    conversation_id=plan.conversation_id,
    correlation_id={correlation!r},
    requested_by="activation_rehearsal",
)
print(json.dumps({{
    "grant_id": grant.grant_id,
    "decision_ref": grant.decision_ref,
    "correlation_id": grant.correlation_id,
    "workpacket_ids": list(plan.workpacket_ids),
    "producer_store": str(store._grants_path),
}}))
""",
            )
            summary["seed"] = seed

            _must(
                runner,
                "docker_run_activation_rehearsal",
                runner.run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        container,
                        "--network",
                        _OPERATOR_DOCKER_NETWORK,
                        "-v",
                        f"{_WORKTREE}:/app:ro",
                        "-v",
                        f"{state_dir}:/state/umh",
                        "-e",
                        "UMH_STATE_DIR=/state/umh",
                        "-e",
                        "PYTHONDONTWRITEBYTECODE=1",
                        "-e",
                        "PYTHONPATH=/app",
                        "-e",
                        "UMH_ROOT=/app",
                        "-e",
                        "UMH_DEV_BYPASS=true",
                        "-e",
                        f"UMH_BUILD_COMMIT={sha}",
                        "--env-file",
                        str(env_out),
                        "-p",
                        f"127.0.0.1:{port}:{_CANDIDATE_API_PORT}",
                        image_id,
                        "python3",
                        "-m",
                        "uvicorn",
                        "services.operator_api:app",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        str(_CANDIDATE_API_PORT),
                    ],
                    timeout=60,
                ),
            )
            ready = _wait_http_ready(f"http://127.0.0.1:{port}/ready", timeout_s=60.0)
            summary["ready"] = ready
            if not ready.get("ready"):
                raise RuntimeError(f"rehearsal container not ready: {ready}")

            body = json.dumps(
                {
                    "approval_id": seed["decision_ref"],
                    "source_type": "execution_authorization",
                    "decided_by": "activation_rehearsal",
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/umh/unified-approval/approve",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - local container
                    response_body = resp.read().decode("utf-8", errors="replace")
                    summary["http_status"] = resp.status
                    summary["http_body"] = _SECRET_REDACT_RE.sub(
                        "<redacted>", response_body[:2000]
                    )
            except urllib.error.HTTPError as exc:
                response_body = exc.read().decode("utf-8", errors="replace")
                summary["http_status"] = exc.code
                summary["http_body"] = _SECRET_REDACT_RE.sub("<redacted>", response_body[:2000])

            reread = _run_state_json(
                state_dir,
                f"""
import json
from substrate.execution.attempts.store import ExecutionAttemptStore
from substrate.organism.universal_work_queue import UniversalWorkQueue

store = ExecutionAttemptStore()
grant = store.get_grant({seed["decision_ref"]!r})
queue = UniversalWorkQueue()
packets = {seed["workpacket_ids"]!r}
print(json.dumps({{
    "grant_status": getattr(grant, "status", ""),
    "activated_task_ids": list(getattr(grant, "activated_task_ids", [])),
    "correlation_id": getattr(grant, "correlation_id", ""),
    "packet_statuses": {{
        packet_id: getattr(queue.get_packet(packet_id), "status", "")
        for packet_id in packets
    }},
    "consumer_store": str(store._grants_path),
}}))
""",
            )
            packet_statuses = dict(reread["packet_statuses"])
            summary.update(
                {
                    "grant_id": seed["grant_id"],
                    "decision_ref": seed["decision_ref"],
                    "correlation_id": correlation,
                    "grant_status": reread["grant_status"],
                    "activated_task_ids": list(reread["activated_task_ids"]),
                    "packet_statuses": packet_statuses,
                    "producer_store": seed["producer_store"],
                    "consumer_store": reread["consumer_store"],
                }
            )
            summary["ok"] = (
                summary["http_status"] == 200
                and summary["grant_status"] == "active"
                and set(summary["activated_task_ids"]) == set(seed["workpacket_ids"])
                and all(str(v) == "approved" for v in packet_statuses.values())
                and summary["producer_store"] == summary["consumer_store"]
            )
            logs = runner.run(["docker", "logs", "--tail", "1200", container], timeout=20, check=False)
            if logs is not None:
                summary["container_logs_tail"] = _SECRET_REDACT_RE.sub(
                    "<redacted>", ((logs.stdout or "") + (logs.stderr or ""))[-12000:]
                )
        except Exception as exc:  # noqa: BLE001
            summary["ok"] = False
            summary["error"] = f"{type(exc).__name__}: {exc}"
            logs = runner.run(["docker", "logs", "--tail", "1200", container], timeout=20, check=False)
            if logs is not None:
                summary["container_logs_tail"] = _SECRET_REDACT_RE.sub(
                    "<redacted>", ((logs.stdout or "") + (logs.stderr or ""))[-12000:]
                )
        finally:
            runner.run(["docker", "rm", "-f", container], timeout=30, check=False)
            shutil.rmtree(root, ignore_errors=True)
            summary["state_removed"] = not root.exists()
            evidence = proof_dir / f"{rehearse_id}.json"
            evidence.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
            results.append(summary)

    return {
        "ok": all(r.get("ok") and r.get("state_removed") for r in results),
        "iterations": iterations,
        "results": results,
        "evidence_dir": str(proof_dir),
    }


def _wait_http_ready(url: str, *, timeout_s: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:  # noqa: S310 - local candidate
                body = resp.read().decode("utf-8", errors="replace")
                if resp.status == 200:
                    return {"ready": True, "status": resp.status, "body": body[:200]}
                last = f"status={resp.status} body={body[:200]}"
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(1)
    return {"ready": False, "last": last}


def _shell_summary(runner: Runner, r: subprocess.CompletedProcess | None) -> dict[str, Any]:
    if runner.dry_run or r is None:
        return {"dry_run": True}
    return {"returncode": r.returncode, "stdout": (r.stdout or "")[:400]}


def _ensure_mesh_secrets() -> None:
    """Resolve mesh relay/verdict secrets from the LIVE mesh server process.

    The two secrets exist only in the mesh server's process environment
    (injected at its launch); they are not in services/.env. Caller-side
    shell `export $(tr ... /proc/<pid>/environ ...)` plumbing proved fragile —
    one transient empty extraction made the commit-binding gate refuse a
    dispatch (run 20260722: beast_worktree_head=""). If the env vars are
    unset, locate the :8094 listener and read its /proc environ directly
    (root-only, host-local; values are never printed, logged, or transited).
    """
    needed = ("UMH_MESH_RELAY_SECRET", "UMH_MESH_VERDICT_SECRET")
    if all(os.environ.get(k) for k in needed):
        return
    try:
        out = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, timeout=15)
        m = re.search(r":8094\b.*?pid=(\d+)", out.stdout or "")
        if not m:
            print("[warn] mesh secret resolution: no listener found on :8094")
            return
        environ = Path(f"/proc/{m.group(1)}/environ").read_bytes()
        for entry in environ.split(b"\0"):
            try:
                key, _, value = entry.decode().partition("=")
            except UnicodeDecodeError:
                continue
            if key in needed and value:
                os.environ.setdefault(key, value)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] mesh secret resolution failed: {exc}")


def _mesh_read(
    runner: Runner,
    command: str,
    *,
    max_len: int = 400,
    command_timeout: int = 60,
    dispatch_timeout: int = 90,
) -> dict[str, Any]:
    """Read-only shell command over the governed mesh.

    The NODE treats the shell capability as write-class regardless of the
    caller's claimed risk_class (fail-closed — a client claim is not
    trustworthy), so every shell dispatch carries a SIGNED verdict even for
    read-only commands.

    ``max_len`` caps the returned stdout AFTER redaction. The 400-char default is
    right for short diagnostic reads, but a ``status.json`` read needs the FULL
    document or ``json.loads`` fails on truncated JSON and the poll never sees a
    terminal state (review W9). Callers reading structured JSON pass a larger cap.
    """
    if runner.dry_run:
        print(
            f"[dry-run] durable_remote(shell, signed verdict) node={_MESH_NODE_ID} cmd={command!r}"
        )
        return {"dry_run": True, "command": command}
    return _durable_remote_shell(
        command,
        max_len=max_len,
        command_timeout=command_timeout,
        dispatch_timeout=dispatch_timeout,
        operation_type="wave2_read",
    )


def _is_cancelled_before_claim(out: dict[str, Any]) -> bool:
    return out.get("raw_status") == "CANCELLED" and _UNCLAIMED_CANCEL_ERROR in str(
        out.get("error", "")
    )


def _preflight_observation_read(
    runner: Runner,
    command: str,
    *,
    gate: str,
    max_attempts: int = 2,
    retry_delay_s: float = 3.0,
    max_len: int = 400,
    command_timeout: int = 60,
    dispatch_timeout: int = 90,
) -> dict[str, Any]:
    """Run a side-effect-free preflight observation with bounded unclaimed retry.

    A durable request cancelled before claim proves no remote command started.
    For preflight-only observations such as ``schtasks /query`` that is a safe
    retry boundary: the original request stays terminal and preserved, and the
    same logical gate gets one bounded replacement request. Any claimed,
    failed, ambiguous, or exhausted attempt still fails closed.
    """
    attempts: list[dict[str, Any]] = []
    last: dict[str, Any] = {}
    for attempt in range(1, max_attempts + 1):
        last = _mesh_read(
            runner,
            command,
            max_len=max_len,
            command_timeout=command_timeout,
            dispatch_timeout=dispatch_timeout,
        )
        attempts.append(
            {
                "attempt": attempt,
                "request_id": last.get("request_id", ""),
                "ok": last.get("ok"),
                "raw_status": last.get("raw_status", ""),
                "error": last.get("error", ""),
                "result_digest": last.get("result_digest", ""),
            }
        )
        if not _is_cancelled_before_claim(last):
            break
        if attempt < max_attempts:
            time.sleep(retry_delay_s)
    if len(attempts) > 1 or _is_cancelled_before_claim(last):
        last = dict(last)
        last["logical_gate"] = gate
        last["attempts"] = attempts
        last["preclaim_retry_attempted"] = len(attempts) > 1
        last["preclaim_retry_exhausted"] = _is_cancelled_before_claim(last)
    return last


def _durable_remote_shell(
    command: str,
    *,
    argv: list[str] | None = None,
    cwd: str | None = None,
    max_len: int = 400,
    command_timeout: int = 60,
    dispatch_timeout: int = 90,
    operation_type: str = "wave2_shell",
    correlation_id: str = "wave2-preflight",
    candidate_sha: str = "",
) -> dict[str, Any]:
    """Submit a request-bound shell command through durable remote transport."""
    _ensure_mesh_secrets()
    from substrate.execution.durable_remote_transport import DurableRemoteStore, make_request
    from substrate.execution.mesh_verdict import get_verdict_secret, sign_verdict

    if not get_verdict_secret():
        return {"ok": False, "error": "mesh verdict secret unset", "raw_status": "verdict_secret_unset"}

    store = DurableRemoteStore()
    verdict = sign_verdict(
        verdict_id=uuid4().hex,
        node_id=_MESH_NODE_ID,
        capability="shell",
        risk_class="reversible_write",
        ttl_seconds=max(command_timeout, dispatch_timeout) + 60,
    )
    queue_delivery_timeout_s = max(float(dispatch_timeout), 1.0)
    execution_timeout_s = max(float(command_timeout), 1.0)
    cancellation_delivery_timeout_s = 30.0
    process_termination_timeout_s = 15.0
    cancellation_ack_timeout_s = 30.0
    result_ingestion_timeout_s = 30.0
    reconciliation_timeout_s = 15.0
    caller_wait_timeout_s = (
        queue_delivery_timeout_s
        + execution_timeout_s
        + result_ingestion_timeout_s
        + cancellation_delivery_timeout_s
        + process_termination_timeout_s
        + cancellation_ack_timeout_s
        + reconciliation_timeout_s
    )
    budgets = {
        "queue_delivery_timeout_s": queue_delivery_timeout_s,
        "claim_timeout_s": queue_delivery_timeout_s,
        "execution_timeout_s": execution_timeout_s,
        "cancellation_delivery_timeout_s": cancellation_delivery_timeout_s,
        "process_termination_timeout_s": process_termination_timeout_s,
        "cancellation_ack_timeout_s": cancellation_ack_timeout_s,
        "result_ingestion_timeout_s": result_ingestion_timeout_s,
        "reconciliation_timeout_s": reconciliation_timeout_s,
        "caller_wait_timeout_s": caller_wait_timeout_s,
    }
    request = make_request(
        correlation_id=correlation_id,
        candidate_sha=candidate_sha or _candidate_sha(""),
        node_id=_MESH_NODE_ID,
        operation_type=operation_type,
        capability="shell",
        params={
            "command": command if argv is None else "",
            "argv": argv or [],
            "cwd": cwd,
            "timeout": command_timeout,
            "budgets": budgets,
            "governance_verdict_id": verdict,
        },
        risk_class="reversible_write",
        ttl_seconds=int(caller_wait_timeout_s + 60),
    )
    store.put_request(request)
    terminal_states = {"SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"}

    def _requires_residue_reconciliation(current: object) -> bool:
        diagnostics = getattr(current, "diagnostics", {})
        return bool(
            isinstance(diagnostics, dict)
            and (
                diagnostics.get("cancel_without_cleanup")
                or diagnostics.get("failed_without_cleanup")
                or diagnostics.get("success_without_cleanup")
                or diagnostics.get("terminal_cancel_cleanup_conflict")
            )
        )

    def _terminal_output(current: object) -> dict[str, object]:
        result = store.result_for(request.request_id) or {}
        data = result.get("result", {}) if isinstance(result, dict) else {}
        state = getattr(current, "lifecycle_state", "")
        success = bool(data.get("success")) and state == "SUCCEEDED"
        out: dict[str, object] = {
            "ok": success,
            "stdout": _SECRET_REDACT_RE.sub("<redacted>", str(data.get("stdout", ""))[:max_len]),
            "stderr": _SECRET_REDACT_RE.sub("<redacted>", str(data.get("stderr", ""))[:max_len]),
            "error": _SECRET_REDACT_RE.sub(
                "<redacted>", str(data.get("error", ""))[:max_len]
            ),
            "raw_status": state,
            "request_id": request.request_id,
            "result_digest": getattr(current, "result_digest", ""),
        }
        if isinstance(result, dict):
            out["cleanup"] = result.get("cleanup", {})
        return out

    def _reconciliation_due(current: object) -> bool:
        deadline_at = float(getattr(current, "reconciliation_deadline_at", 0.0) or 0.0)
        return bool(deadline_at and time.time() >= deadline_at)

    def _current_poll_deadline(current: object | None) -> float:
        base = request.created_at + queue_delivery_timeout_s
        if current is None:
            return base
        state = getattr(current, "lifecycle_state", "")
        if state in {"CLAIMED", "RUNNING", "CANCEL_REQUESTED", "RECONCILIATION_REQUIRED"}:
            process_tree = getattr(current, "process_tree", {})
            if isinstance(process_tree, dict):
                started_at = float(
                    process_tree.get("running_at")
                    or process_tree.get("claimed_at")
                    or getattr(current, "created_at", request.created_at)
                    or request.created_at
                )
            else:
                started_at = float(getattr(current, "created_at", request.created_at) or request.created_at)
            return max(
                base,
                started_at + execution_timeout_s + result_ingestion_timeout_s,
            )
        return base

    def _recovery_output(current: object) -> dict[str, object]:
        diagnostics = getattr(current, "diagnostics", {})
        reason = "durable remote request requires governed residue reconciliation"
        if isinstance(diagnostics, dict):
            if diagnostics.get("cancel_without_cleanup"):
                reason = "durable remote cancellation left process residue"
            elif diagnostics.get("failed_without_cleanup"):
                reason = "durable remote failure left process residue"
            elif diagnostics.get("success_without_cleanup"):
                reason = "durable remote success left process residue"
            elif diagnostics.get("terminal_cancel_cleanup_conflict"):
                reason = "durable remote terminal replay reported process residue"
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "error": reason,
            "raw_status": getattr(current, "lifecycle_state", ""),
            "request_id": request.request_id,
            "result_digest": getattr(current, "result_digest", ""),
        }

    last_state = "QUEUED"
    while True:
        current = store.get_request(request.request_id)
        if current is not None:
            last_state = current.lifecycle_state
            if current.lifecycle_state in terminal_states:
                return _terminal_output(current)
            if current.lifecycle_state == "RECONCILIATION_REQUIRED":
                if _requires_residue_reconciliation(current):
                    last_state = current.lifecycle_state
                    if time.time() >= _current_poll_deadline(current):
                        break
                    time.sleep(1)
                    continue
                if _reconciliation_due(current):
                    reconciled = store.reconcile_request(
                        request.request_id,
                        reason="client_poll_observed_reconciliation_required",
                    )
                    if reconciled.lifecycle_state in terminal_states:
                        return _terminal_output(reconciled)
        if time.time() >= _current_poll_deadline(current):
            break
        time.sleep(1)
    try:
        store.request_cancel(request.request_id)
    except Exception:
        pass
    cancel_deadline = time.time() + (
        cancellation_delivery_timeout_s
        + process_termination_timeout_s
        + cancellation_ack_timeout_s
        + reconciliation_timeout_s
    )
    while time.time() < cancel_deadline:
        current = store.get_request(request.request_id)
        if current is not None:
            last_state = current.lifecycle_state
            if current.lifecycle_state in terminal_states:
                return _terminal_output(current)
            if current.lifecycle_state == "RECONCILIATION_REQUIRED":
                if _requires_residue_reconciliation(current):
                    last_state = current.lifecycle_state
                    if time.time() >= cancel_deadline:
                        break
                    time.sleep(1)
                    continue
                if _reconciliation_due(current):
                    reconciled = store.reconcile_request(
                        request.request_id,
                        reason="client_timeout_reconciliation",
                    )
                    if reconciled.lifecycle_state in terminal_states:
                        return _terminal_output(reconciled)
        time.sleep(1)
    try:
        current = store.get_request(request.request_id)
        if (
            current is not None
            and current.lifecycle_state == "RECONCILIATION_REQUIRED"
            and not _requires_residue_reconciliation(current)
        ):
            reconciled = store.reconcile_request(
                request.request_id,
                reason="client_timeout_reconciliation_deadline",
            )
            if reconciled.lifecycle_state in terminal_states:
                return _terminal_output(reconciled)
    except Exception:
        pass
    try:
        failed = store.fail_unresolved_request(
            request.request_id,
            reason=f"client_timeout_after_cancel_state_{last_state}",
        )
        if failed.lifecycle_state == "RECONCILIATION_REQUIRED" and _requires_residue_reconciliation(failed):
            return _recovery_output(failed)
        if failed.lifecycle_state in terminal_states:
            if _requires_residue_reconciliation(failed):
                return _recovery_output(failed)
            return _terminal_output(failed)
    except Exception:
        pass
    return {
        "ok": False,
        "error": f"durable remote request timed out in state {last_state}",
        "raw_status": last_state,
        "request_id": request.request_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# collector dispatch (smoke / run)
# ─────────────────────────────────────────────────────────────────────────────
_REQUIRED_EVIDENCE_ARTIFACTS = ("result.json", "network.jsonl", "console.jsonl")
_DESTINATION_COMMIT_FILES = {
    "evidence_commit.json",
    "evidence_commit.json.tmp",
    "evidence_receipt.json",
    "evidence_receipt.json.tmp",
}


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as fh:
        os.fsync(fh.fileno())


def _safe_manifest_path(rel: Any) -> str | None:
    if not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel:
        return None
    rel_path = Path(rel)
    if any(part in ("", ".", "..") for part in rel_path.parts):
        return None
    return rel


def _safe_absolute_evidence_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    raw_parts = value.split("/")
    if raw_parts[0] != "" or any(part in ("", ".", "..") for part in raw_parts[1:]):
        return None
    if "\\" in value:
        return None
    path = Path(value)
    if not path.is_absolute():
        return None
    return path


def _existing_symlink_under(root: Path, path: Path) -> Path | None:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return path
    current = root
    if current.is_symlink():
        return current
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            return current
        if not current.exists():
            break
    return None


def _is_full_candidate_sha(sha: str) -> bool:
    return len(sha) == 40 and all(ch in "0123456789abcdef" for ch in sha)


def _load_and_verify_evidence_bundle(
    root: Path,
    sha: str,
    *,
    expected_run_id: str | None = None,
    expected_pass_num: int | None = None,
    allow_destination_commit_files: bool = False,
    allow_destination_tmp_files: bool = False,
) -> tuple[dict[str, Any] | None, str, str]:
    if root.is_symlink():
        return None, "", "symlink evidence root"
    if not allow_destination_commit_files:
        for path in root.rglob("*"):
            if path.is_symlink():
                rel = path.relative_to(root).as_posix()
                return None, "", f"symlink evidence path {rel}"
            if path.is_file() and path.name in _DESTINATION_COMMIT_FILES:
                rel = path.relative_to(root).as_posix()
                return None, "", f"destination commit artifact not allowed in uploaded bundle: {rel}"
    manifest_path = root / "evidence_manifest.json"
    if not manifest_path.is_file():
        return None, "", "missing evidence_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, "", f"manifest unreadable: {exc}"
    if not isinstance(manifest, dict):
        return None, "", "manifest is not an object"
    if expected_run_id is not None and manifest.get("run_id") != expected_run_id:
        return None, "", "binding mismatch run_id"
    if expected_pass_num is not None and manifest.get("pass_num") != expected_pass_num:
        return None, "", "binding mismatch pass_num"
    pass_num = manifest.get("pass_num")
    if manifest.get("pass_id") != f"pass{pass_num}":
        return None, "", "binding mismatch pass_id"
    candidate_sha = manifest.get("candidate_sha")
    if not isinstance(candidate_sha, str) or candidate_sha != sha:
        return None, "", "binding mismatch candidate_sha"
    required_artifacts = manifest.get("required_artifacts")
    if not isinstance(required_artifacts, list) or tuple(required_artifacts) != _REQUIRED_EVIDENCE_ARTIFACTS:
        return None, "", "required artifact contract mismatch"
    for rel in _REQUIRED_EVIDENCE_ARTIFACTS:
        if not (root / rel).is_file():
            return None, "", f"missing required artifact {rel}"
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return None, "", "manifest files is not a list"
    seen: set[str] = set()
    normalized_files: list[dict[str, Any]] = []
    for item in files:
        if not isinstance(item, dict):
            return None, "", "malformed manifest file entry"
        rel = _safe_manifest_path(item.get("path"))
        if rel is None:
            return None, "", "unsafe manifest path"
        if rel in seen:
            return None, "", "duplicate manifest path"
        seen.add(rel)
        path = root / rel
        if path.is_symlink():
            return None, "", f"symlink evidence path {rel}"
        if not path.is_file():
            return None, "", f"missing manifest file {rel}"
        data = path.read_bytes()
        try:
            size = int(item.get("size", -1))
        except (TypeError, ValueError):
            return None, "", f"bad size {rel}"
        digest = str(item.get("sha256", ""))
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            return None, "", f"digest mismatch {rel}"
        normalized_files.append({"path": rel, "size": size, "sha256": digest})
    missing_bound = [rel for rel in _REQUIRED_EVIDENCE_ARTIFACTS if rel not in seen]
    if missing_bound:
        return None, "", "required artifact missing from hash inventory: " + ",".join(missing_bound)
    inventory_digest = hashlib.sha256(
        json.dumps(normalized_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if manifest.get("inventory_sha256") != inventory_digest:
        return None, "", "inventory digest mismatch"
    allowed_files = set(seen) | {"evidence_manifest.json", "evidence_manifest.sha256", "upload_complete.json"}
    if allow_destination_commit_files:
        allowed_files.update({"evidence_commit.json", "evidence_receipt.json"})
    if allow_destination_tmp_files:
        allowed_files.update(_DESTINATION_COMMIT_FILES)
    for path in root.rglob("*"):
        if path.is_symlink():
            rel = path.relative_to(root).as_posix()
            return None, "", f"symlink evidence path {rel}"
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel not in allowed_files:
            return None, "", f"unmanifested evidence file {rel}"
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    sidecar = root / "evidence_manifest.sha256"
    if not sidecar.is_file():
        return None, "", "missing evidence_manifest.sha256"
    try:
        expected_digest = sidecar.read_text(encoding="utf-8").split()[0]
    except IndexError:
        return None, "", "manifest sidecar malformed"
    if expected_digest != manifest_digest:
        return None, "", "manifest sidecar digest mismatch"
    manifest["_computed_inventory_sha256"] = inventory_digest
    return manifest, manifest_digest, ""


def _load_and_verify_upload_marker(
    root: Path,
    *,
    transaction_id: str | None,
    manifest_digest: str,
    inventory_digest: str,
    sha: str,
    run_id: str,
    pass_num: int,
    campaign_id: str,
    staging_campaign_id: str,
    staging: Path,
    canonical: Path,
) -> tuple[dict[str, Any] | None, str]:
    marker_path = root / "upload_complete.json"
    if not marker_path.is_file():
        return None, "missing upload_complete marker"
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"upload_complete unreadable: {exc}"
    if not isinstance(marker, dict):
        return None, "upload_complete marker is not an object"
    observed_transaction_id = marker.get("transaction_id")
    if not isinstance(observed_transaction_id, str) or not observed_transaction_id:
        return None, "upload_complete transaction missing"
    if transaction_id is not None and observed_transaction_id != transaction_id:
        return None, "upload_complete transaction mismatch"
    if marker.get("run_id") != run_id or marker.get("pass_num") != pass_num:
        return None, "upload_complete binding mismatch"
    if marker.get("pass_id") != f"pass{pass_num}":
        return None, "upload_complete pass_id mismatch"
    if marker.get("campaign_id") != campaign_id:
        return None, "upload_complete campaign mismatch"
    if staging_campaign_id != campaign_id:
        return None, "staging campaign mismatch"
    marker_candidate_sha = marker.get("candidate_sha")
    if not isinstance(marker_candidate_sha, str) or marker_candidate_sha != sha:
        return None, "upload_complete candidate mismatch"
    if marker.get("manifest_sha256") != manifest_digest:
        return None, "upload_complete manifest digest mismatch"
    if marker.get("inventory_sha256") != inventory_digest:
        return None, "upload_complete inventory digest mismatch"
    staging_path = marker.get("staging_path")
    marker_staging = _safe_absolute_evidence_path(staging_path)
    if marker_staging is None or marker_staging != staging:
        return None, "upload_complete staging path mismatch"
    canonical_path = marker.get("canonical_path")
    marker_canonical = _safe_absolute_evidence_path(canonical_path)
    if marker_canonical is None or marker_canonical != canonical:
        return None, "upload_complete canonical path mismatch"
    return marker, ""


def _fsync_evidence_bundle(root: Path, manifest: dict[str, Any]) -> None:
    paths: list[Path] = []
    dirs: set[Path] = {root}
    for item in manifest.get("files", []):
        if isinstance(item, dict):
            rel = _safe_manifest_path(item.get("path"))
            if rel is not None:
                path = root / rel
                paths.append(path)
                parent = path.parent
                while root in (parent, *parent.parents):
                    dirs.add(parent)
                    if parent == root:
                        break
                    parent = parent.parent
    paths.extend(
        [
            root / "evidence_manifest.json",
            root / "evidence_manifest.sha256",
            root / "upload_complete.json",
            root / "evidence_commit.json",
            root / "evidence_receipt.json",
        ]
    )
    seen: set[Path] = set()
    for path in paths:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        _fsync_file(path)
    for directory in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if directory.is_dir():
            _fsync_dir(directory)


def _write_evidence_receipt(
    root: Path,
    *,
    manifest: dict[str, Any],
    manifest_digest: str,
    transaction_id: str,
    canonical: Path | None = None,
    recovered: bool = False,
) -> dict[str, Any]:
    canonical_path = canonical or root
    verified_at = _utc_now()
    promoted_at = _utc_now()
    commit_marker = {
        "ok": True,
        "schema_version": 1,
        "commit_id": "commit-"
        + hashlib.sha256((str(canonical_path) + manifest_digest + transaction_id).encode()).hexdigest()[:16],
        "authority": "vps_destination_commit",
        "campaign_id": manifest.get("campaign_id", ""),
        "run_id": manifest["run_id"],
        "pass_id": manifest["pass_id"],
        "pass_num": manifest["pass_num"],
        "candidate_sha": manifest["candidate_sha"],
        "transaction_id": transaction_id,
        "manifest_sha256": manifest_digest,
        "inventory_sha256": manifest.get("_computed_inventory_sha256") or manifest.get("inventory_sha256"),
        "canonical_path": str(canonical_path),
        "verified_at": verified_at,
        "promoted_at": promoted_at,
        "recovered_after_promotion": recovered,
    }
    marker_tmp = root / "evidence_commit.json.tmp"
    marker_tmp.write_text(json.dumps(commit_marker, indent=2, sort_keys=True), encoding="utf-8")
    with marker_tmp.open("rb") as fh:
        os.fsync(fh.fileno())
    os.replace(marker_tmp, root / "evidence_commit.json")
    _fsync_dir(root)
    commit_marker_digest = hashlib.sha256((root / "evidence_commit.json").read_bytes()).hexdigest()
    receipt = {
        "ok": True,
        "schema_version": 1,
        "receipt_id": "receipt-"
        + hashlib.sha256(
            (str(canonical_path) + manifest_digest + transaction_id + commit_marker_digest).encode()
        ).hexdigest()[:16],
        "receipt_authority": "vps_destination_commit",
        "campaign_id": manifest.get("campaign_id", ""),
        "run_id": manifest["run_id"],
        "pass_id": manifest["pass_id"],
        "pass_num": manifest["pass_num"],
        "candidate_sha": manifest["candidate_sha"],
        "transaction_id": transaction_id,
        "artifact_count": len(manifest.get("files", [])),
        "manifest_sha256": manifest_digest,
        "inventory_sha256": manifest.get("_computed_inventory_sha256") or manifest.get("inventory_sha256"),
        "commit_marker_sha256": commit_marker_digest,
        "canonical_path": str(canonical_path),
        "verified_at": verified_at,
        "promoted_at": promoted_at,
        "recovered_after_promotion": recovered,
        "destination_owned": True,
    }
    tmp = root / "evidence_receipt.json.tmp"
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    with tmp.open("rb") as fh:
        os.fsync(fh.fileno())
    os.replace(tmp, root / "evidence_receipt.json")
    _fsync_dir(root)
    return receipt


def _commit_uploaded_evidence_transaction(
    upload: dict[str, Any],
    sha: str,
    *,
    run_id: str,
    pass_num: int,
) -> dict[str, Any]:
    """VPS-owned verification, atomic promotion, and durable receipt commit."""
    if not isinstance(sha, str) or not _is_full_candidate_sha(sha):
        return {"ok": False, "error": "dispatcher candidate sha must be full 40-hex"}
    raw_root = _evidence_raw_root_for_upload(upload) or (_proof_root() / "raw").resolve()
    transaction_id = str(upload.get("transaction_id") or "")
    if not transaction_id:
        return {"ok": False, "error": "missing transaction_id"}
    staging = _safe_absolute_evidence_path(upload.get("staging_path"))
    if staging is None:
        return {"ok": False, "error": "bad transaction paths"}
    canonical = (raw_root / run_id / f"pass{pass_num}").resolve()
    if raw_root not in staging.parents or raw_root not in canonical.parents:
        return {"ok": False, "error": "evidence paths escape raw proof root"}
    try:
        staging_parts = staging.relative_to(raw_root).parts
    except ValueError:
        staging_parts = ()
    if (
        len(staging_parts) != 5
        or staging_parts[0] != ".incoming"
        or not staging_parts[1]
        or staging_parts[2] != run_id
        or staging_parts[3] != f"pass{pass_num}"
        or staging_parts[4] != transaction_id
    ):
        return {"ok": False, "error": "staging path does not match evidence transaction identity"}
    if _existing_symlink_under(raw_root, staging) is not None:
        return {"ok": False, "error": "staging path contains symlink"}
    if _existing_symlink_under(raw_root, canonical) is not None:
        return {"ok": False, "error": "canonical path contains symlink"}
    upload_canonical = str(upload.get("canonical_path") or "")
    if upload_canonical:
        upload_canonical_path = _safe_absolute_evidence_path(upload_canonical)
        if upload_canonical_path is None or upload_canonical_path != canonical:
            return {"ok": False, "error": "status canonical path mismatch"}
    effective_sha = sha
    receipt_path = canonical / "evidence_receipt.json"
    if receipt_path.is_file():
        prior = _verified_evidence_receipt(canonical, effective_sha)
        fresh = _fresh_process_verified_evidence_receipt(canonical, effective_sha)
        if (
            prior
            and fresh
            and prior.get("transaction_id") == transaction_id
            and fresh.get("transaction_id") == transaction_id
            and (not upload.get("manifest_sha256") or fresh.get("manifest_sha256") == upload.get("manifest_sha256"))
        ):
            try:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)
                    _fsync_dir(staging.parent)
            except OSError as exc:
                return {"ok": False, "error": f"evidence durability failure: {exc}"}
            fresh["idempotent_replay"] = True
            return {"ok": True, "receipt": fresh, "idempotent_replay": True}
        return {"ok": False, "error": "canonical destination exists with divergent receipt"}
    if canonical.exists():
        manifest, manifest_digest, error = _load_and_verify_evidence_bundle(
            canonical,
            effective_sha,
            expected_run_id=run_id,
            expected_pass_num=pass_num,
            allow_destination_commit_files=True,
            allow_destination_tmp_files=True,
        )
        if error:
            return {"ok": False, "error": "canonical destination exists without committed receipt"}
        marker, marker_error = _load_and_verify_upload_marker(
            canonical,
            transaction_id=transaction_id,
            manifest_digest=manifest_digest,
            inventory_digest=manifest.get("_computed_inventory_sha256", ""),
            sha=effective_sha,
            run_id=run_id,
            pass_num=pass_num,
            campaign_id=str((manifest or {}).get("campaign_id", "")),
            staging_campaign_id=str(staging_parts[1]),
            staging=staging,
            canonical=canonical,
        )
        if marker_error:
            return {"ok": False, "error": "canonical destination exists without committed receipt"}
        if upload.get("manifest_sha256") and upload.get("manifest_sha256") != manifest_digest:
            return {"ok": False, "error": "canonical destination exists without committed receipt"}
        try:
            receipt = _write_evidence_receipt(
                canonical,
                manifest=manifest or {},
                manifest_digest=manifest_digest,
                transaction_id=transaction_id,
                canonical=canonical,
                recovered=True,
            )
            _fsync_evidence_bundle(canonical, manifest or {})
        except OSError as exc:
            return {"ok": False, "error": f"evidence durability failure: {exc}"}
        fresh = _fresh_process_verified_evidence_receipt(canonical, effective_sha)
        if not fresh:
            return {"ok": False, "error": "fresh-process receipt verification failed"}
        return {"ok": True, "receipt": receipt, "recovered_after_promotion": True}
    manifest, manifest_digest, error = _load_and_verify_evidence_bundle(
        staging,
        effective_sha,
        expected_run_id=run_id,
        expected_pass_num=pass_num,
    )
    if error:
        return {"ok": False, "error": error, "staging_path": str(staging)}
    marker, marker_error = _load_and_verify_upload_marker(
        staging,
        transaction_id=transaction_id,
        manifest_digest=manifest_digest,
        inventory_digest=manifest.get("_computed_inventory_sha256", ""),
        sha=effective_sha,
        run_id=run_id,
        pass_num=pass_num,
        campaign_id=str((manifest or {}).get("campaign_id", "")),
        staging_campaign_id=str(staging_parts[1]),
        staging=staging,
        canonical=canonical,
    )
    if marker_error:
        return {"ok": False, "error": marker_error}
    if upload.get("manifest_sha256") and upload.get("manifest_sha256") != manifest_digest:
        return {"ok": False, "error": "status manifest digest mismatch"}
    try:
        canonical.parent.mkdir(parents=True, exist_ok=True)
        if _existing_symlink_under(raw_root, canonical) is not None:
            return {"ok": False, "error": "canonical path contains symlink"}
        _fsync_dir(canonical.parent.parent)
        _fsync_evidence_bundle(staging, manifest or {})
        os.replace(staging, canonical)
        _fsync_dir(staging.parent)
        _fsync_dir(canonical.parent)
        receipt = _write_evidence_receipt(
            canonical,
            manifest=manifest or {},
            manifest_digest=manifest_digest,
            transaction_id=transaction_id,
            canonical=canonical,
        )
        _fsync_evidence_bundle(canonical, manifest or {})
    except OSError as exc:
        return {"ok": False, "error": f"evidence durability failure: {exc}"}
    fresh = _fresh_process_verified_evidence_receipt(canonical, effective_sha)
    if not fresh:
        return {"ok": False, "error": "fresh-process receipt verification failed"}
    return {"ok": True, "receipt": receipt}


def _terminal_from_committed_evidence(receipt: dict[str, Any], sha: str) -> dict[str, Any]:
    """Derive PASS/FAIL only from destination-verified canonical evidence."""
    canonical_path = receipt.get("canonical_path")
    if not isinstance(canonical_path, str) or not canonical_path:
        return {"ok": False, "error": "receipt missing canonical path"}
    pass_dir = Path(canonical_path)
    verified = _fresh_process_verified_evidence_receipt(pass_dir, sha)
    if not verified or verified.get("receipt_id") != receipt.get("receipt_id"):
        return {"ok": False, "error": "fresh-process receipt verification failed"}
    try:
        result = json.loads((pass_dir / "result.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"canonical result unreadable: {exc}"}
    if result.get("candidate_commit") != sha:
        return {"ok": False, "error": "canonical result candidate mismatch"}
    pass_name = pass_dir.name
    try:
        pass_num = int(pass_name.removeprefix("pass"))
    except ValueError:
        return {"ok": False, "error": "canonical pass path malformed"}
    if result.get("pass_num") != pass_num:
        return {"ok": False, "error": "canonical result pass mismatch"}
    execution_passed = result.get("execution_passed") is True
    return {
        "ok": True,
        "state": "passed" if execution_passed else "failed",
        "execution_passed": execution_passed,
        "canonical_result": {
            "candidate_commit": result.get("candidate_commit"),
            "scenario": result.get("scenario"),
            "pass_num": result.get("pass_num"),
            "run_tag": result.get("run_tag"),
        },
    }


def _fresh_process_verified_evidence_receipt(pass_dir: Path, sha: str) -> dict[str, Any] | None:
    """Re-read receipt in a fresh interpreter so in-memory status cannot qualify."""
    raw_root = _evidence_raw_root_from_path(pass_dir) or (_proof_root() / "raw").resolve()
    proof_root = str(raw_root.parent)
    code = f"""
import importlib.util, json, pathlib, sys
spec = importlib.util.spec_from_file_location('wave2_field_dispatch_verify', {json.dumps(str(Path(__file__).resolve()))})
mod = importlib.util.module_from_spec(spec)
sys.modules['wave2_field_dispatch_verify'] = mod
spec.loader.exec_module(mod)
mod._proof_root = lambda: pathlib.Path({json.dumps(proof_root)})
out = mod._verified_evidence_receipt(pathlib.Path({json.dumps(str(pass_dir))}), {json.dumps(sha)})
print(json.dumps(out))
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        parsed = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_start_command(
    *, run_id: str, pass_num: int, scenario: str, url: str, candidate_commit: str
) -> str:
    """Assemble the detached powershell Start-Process → op run → collector cmd.

    The collector runs under `op run` on the executor so credentials never
    transit the mesh dispatch payload. Start-Process detaches it so the mesh
    call returns immediately; we then poll status.json read-only.
    """
    if not isinstance(url, str) or not url.strip() or url.strip().lower() == "none":
        raise ValueError("collector origin is unresolved")
    ship_to = f"{_proof_root()}/raw"
    collector = (
        f"python {_BEAST_COLLECTOR} "
        f"--url {url} "
        f"--run-id {run_id} "
        f"--pass-num {pass_num} "
        f"--evidence-dir {_BEAST_EVIDENCE_DIR} "
        f"--candidate-commit {candidate_commit} "
        f"--scenario {scenario} "
        f"--ship-to {ship_to}"
    )
    # QUOTING LAW (this exact line silently no-opped smoke twice, 2026-07-22):
    # the whole command below rides inside powershell -Command "..." — any
    # embedded double quote (e.g. --env-file="...") TERMINATES that outer
    # string and Start-Process swallows the parse error invisibly. No executor
    # path contains spaces, so nothing inside needs quoting. Keep it that way:
    # never add a quoted path here; if a path needs spaces, change the path.
    op_wrapped = f"op run --env-file={_BEAST_ENV_TPL} -- {collector}"
    # Launch log: Start-Process detaches and hides all failure output, so the
    # detached cmd redirects its own stdout+stderr to a per-run log we can
    # read over the mesh when status.json never appears (client-failure
    # observability law — instrument, don't guess).
    launch_log = rf"{_BEAST_EVIDENCE_DIR}\launch_{run_id}_p{pass_num}.log"
    pid_manifest = rf"{_BEAST_EVIDENCE_DIR}\collector_{run_id}_p{pass_num}.pid.json"
    inner = (
        f"/c md {_BEAST_EVIDENCE_DIR} 2>nul & "
        f"{op_wrapped} 1> {launch_log} 2>&1"
    )
    # Start-Process detaches; -WindowStyle Hidden keeps Session 1 clean.
    return (
        "powershell -NoProfile -Command "
        "\"$p=Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' "
        f"-ArgumentList '{inner}' -PassThru; "
        "$payload=[ordered]@{"
        f"pid=$p.Id;run_id='{run_id}';pass_num={pass_num};"
        f"candidate_commit='{candidate_commit}';command='{_BEAST_COLLECTOR}'"
        "} | ConvertTo-Json -Compress; "
        f"Set-Content -Path '{pid_manifest}' -Value $payload\""
    )


def _poll_status(
    runner: Runner,
    run_id: str,
    pass_num: int,
    timeout_min: int = 30,
    max_mesh_failures: int = 5,
    candidate_sha: str = "",
) -> dict[str, Any]:
    """Read-only 30s polls of the executor status.json until terminal.

    Reads the FULL status.json (large max_len — a truncated read never parses,
    review W9). A run of consecutive mesh-read FAILURES (dispatch down, node
    offline) fails fast after ``max_mesh_failures`` instead of silently burning
    the entire poll budget (review W9). A parse failure while the mesh is HEALTHY
    (status.json not yet written) is normal and keeps polling.
    """
    status_path = f"{_BEAST_EVIDENCE_DIR}\\{run_id}\\pass{pass_num}\\status.json"
    read_cmd = f"type {status_path}"
    deadline = time.time() + timeout_min * 60
    last: dict[str, Any] = {}
    consecutive_mesh_failures = 0
    while time.time() < deadline:
        # status.json is structured JSON — read it untruncated (64 KiB is ample).
        res = _mesh_read(runner, read_cmd, max_len=65536)
        if runner.dry_run:
            print(f"[dry-run] poll (every 30s, up to {timeout_min}m): mesh read {status_path}")
            return {"dry_run": True, "status_path": status_path}
        # A mesh dispatch FAILURE (ok=False) is distinct from "status.json not
        # yet written" (ok=True, empty/partial). Fail fast on a run of dispatch
        # failures rather than spinning the full budget.
        if not res.get("ok", False):
            consecutive_mesh_failures += 1
            if consecutive_mesh_failures >= max_mesh_failures:
                return {
                    "mesh_unreachable": True,
                    "consecutive_mesh_failures": consecutive_mesh_failures,
                    "status_path": status_path,
                }
            time.sleep(30)
            continue
        consecutive_mesh_failures = 0
        raw = res.get("stdout", "")
        try:
            last = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # mesh healthy but status.json absent/partial — keep polling.
            last = {"raw": raw[:200]}
        if last.get("state") == "evidence_preservation_failed":
            return last
        if last.get("state") == "evidence_uploaded":
            upload = last.get("evidence_upload")
            if isinstance(upload, dict):
                committed = _commit_uploaded_evidence_transaction(
                    upload,
                    candidate_sha,
                    run_id=run_id,
                    pass_num=pass_num,
                )
                if committed.get("ok"):
                    receipt = committed.get("receipt", {})
                    terminal = _terminal_from_committed_evidence(receipt, candidate_sha)
                    if not terminal.get("ok"):
                        return {
                            **last,
                            "state": "evidence_preservation_failed",
                            "preservation_error": terminal.get("error", "canonical result verification failed"),
                            "destination_commit": committed,
                        }
                    return {
                        "state": terminal["state"],
                        "run_id": run_id,
                        "pass": pass_num,
                        "execution_passed": terminal["execution_passed"],
                        "evidence_receipt": receipt,
                        "canonical_result": terminal.get("canonical_result", {}),
                        "destination_commit": committed,
                    }
                last = {
                    **last,
                    "state": "evidence_preservation_failed",
                    "preservation_error": committed.get("error", "destination evidence commit failed"),
                    "destination_commit": committed,
                }
                return last
        if last.get("state") in ("passed", "failed") and last.get("evidence_receipt"):
            return {
                **last,
                "state": "evidence_preservation_failed",
                "preservation_error": "collector terminal receipt is not destination-owned authority",
            }
        time.sleep(30)
    last["timed_out"] = True
    if last.get("state") in ("passed", "failed"):
        return {
            **last,
            "state": "evidence_preservation_failed",
            "preservation_error": "collector terminal state timed out without destination-owned receipt",
        }
    return last


_EVIDENCE_TRANSACTION_STATES = {
    "execution_complete",
    "evidence_finalizing",
    "evidence_shipping",
    "evidence_uploaded",
}


def _read_collector_status(runner: Runner, *, run_id: str, pass_num: int = 1) -> dict[str, Any]:
    status_path = f"{_BEAST_EVIDENCE_DIR}\\{run_id}\\pass{pass_num}\\status.json"
    res = _mesh_read(runner, f"type {status_path}", max_len=65536)
    if runner.dry_run:
        return {"state": "dry_run", "status_path": status_path}
    if not res.get("ok", False):
        return {
            "state": "unknown",
            "status_path": status_path,
            "read_ok": False,
            "error": res.get("error") or "mesh status read failed",
        }
    raw = res.get("stdout", "")
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {
            "state": "unknown",
            "status_path": status_path,
            "read_ok": True,
            "raw": raw[:200],
        }
    if isinstance(parsed, dict):
        parsed.setdefault("status_path", status_path)
        parsed["read_ok"] = True
        return parsed
    return {"state": "unknown", "status_path": status_path, "read_ok": True}


def _find_committed_evidence_receipt(sha: str, *, run_id: str, pass_num: int) -> dict[str, Any] | None:
    """Find an already committed VPS-owned receipt for a run/pass across run-date roots."""
    proof_base = (_ROOT / "data" / "audits" / "proof").resolve()
    pass_name = f"pass{pass_num}"
    for raw_root in sorted(proof_base.glob("*_wave2_field/raw")):
        pass_dir = (raw_root / run_id / pass_name).resolve()
        try:
            pass_dir.relative_to(raw_root.resolve())
        except ValueError:
            continue
        receipt = _fresh_process_verified_evidence_receipt(pass_dir, sha)
        if (
            receipt
            and receipt.get("run_id") == run_id
            and receipt.get("pass_num") == pass_num
            and receipt.get("candidate_sha") == sha
        ):
            return receipt
    return None


def _wait_for_evidence_transaction_clear(
    runner: Runner,
    *,
    run_id: str,
    pass_num: int = 1,
    candidate_sha: str = "",
    timeout_s: float = 600.0,
    poll_s: float = 10.0,
) -> dict[str, Any]:
    """Prevent teardown from racing collector evidence publication."""
    deadline = time.time() + timeout_s
    observations: list[dict[str, Any]] = []
    while True:
        status = _read_collector_status(runner, run_id=run_id, pass_num=pass_num)
        state = status.get("state")
        observations.append(
            {
                "state": state,
                "read_ok": status.get("read_ok"),
                "has_receipt": bool(status.get("evidence_receipt")),
                "timed_out": status.get("timed_out"),
            }
        )
        if state == "evidence_preservation_failed":
            return {"ok": True, "terminal": status, "observations": observations}
        if state in ("passed", "failed"):
            return {
                "ok": False,
                "reason": "collector terminal state is not destination-owned authority",
                "terminal": status,
                "observations": observations,
            }
        if state == "evidence_uploaded":
            upload = status.get("evidence_upload")
            if isinstance(upload, dict):
                committed = _commit_uploaded_evidence_transaction(
                    upload,
                    candidate_sha,
                    run_id=run_id,
                    pass_num=pass_num,
                )
                if committed.get("ok"):
                    receipt = committed.get("receipt", {})
                    terminal = _terminal_from_committed_evidence(receipt, candidate_sha)
                    if not terminal.get("ok"):
                        return {
                            "ok": False,
                            "reason": terminal.get("error", "canonical result verification failed"),
                            "terminal": {**status, "destination_commit": committed},
                            "observations": observations,
                        }
                    return {
                        "ok": True,
                        "terminal": {
                            **status,
                            "state": terminal["state"],
                            "execution_passed": terminal["execution_passed"],
                            "evidence_receipt": receipt,
                            "canonical_result": terminal.get("canonical_result", {}),
                            "destination_commit": committed,
                        },
                        "observations": observations,
                    }
                if time.time() >= deadline:
                    return {
                        "ok": False,
                        "reason": committed.get("error", "destination evidence commit failed"),
                        "terminal": {**status, "destination_commit": committed},
                        "observations": observations,
                    }
                time.sleep(poll_s)
                continue
        if state in ("unknown", ""):
            if time.time() >= deadline:
                receipt = _find_committed_evidence_receipt(
                    candidate_sha,
                    run_id=run_id,
                    pass_num=pass_num,
                )
                if receipt:
                    terminal = _terminal_from_committed_evidence(receipt, candidate_sha)
                    if terminal.get("ok"):
                        return {
                            "ok": True,
                            "terminal": {
                                **status,
                                "state": terminal["state"],
                                "execution_passed": terminal["execution_passed"],
                                "evidence_receipt": receipt,
                                "canonical_result": terminal.get("canonical_result", {}),
                                "destination_commit": {"ok": True, "receipt": receipt, "receipt_recovered": True},
                            },
                            "observations": observations,
                            "receipt_recovered_after_status_loss": True,
                        }
                return {
                    "ok": False,
                    "reason": "collector status unavailable during teardown guard",
                    "terminal": status,
                    "observations": observations,
                }
            time.sleep(poll_s)
            continue
        if state not in _EVIDENCE_TRANSACTION_STATES:
            return {"ok": True, "terminal": status, "observations": observations}
        if time.time() >= deadline:
            return {
                "ok": False,
                "reason": "evidence publication still active",
                "terminal": status,
                "observations": observations,
            }
        time.sleep(poll_s)


def _dispatch_collector(
    runner: Runner, *, run_id: str, pass_num: int, scenario: str, sha: str
) -> dict[str, Any]:
    """Dispatch the collector to Beast (non-blocking). Returns dispatch result."""
    if _ORIGIN is None:
        try:
            _resolve_env()
        except SystemExit as exc:
            return {"ok": False, "error": f"candidate origin unresolved: {exc}", "run_id": run_id, "pass_num": pass_num}
    try:
        command = _build_start_command(
            run_id=run_id,
            pass_num=pass_num,
            scenario=scenario,
            url=_ORIGIN or "",
            candidate_commit=sha,
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "run_id": run_id, "pass_num": pass_num}
    if runner.dry_run:
        print(f"[dry-run] durable_remote(shell, write-class) node={_MESH_NODE_ID}")
        print(f"[dry-run]   detached start: {_SECRET_REDACT_RE.sub('<redacted>', command)}")
        return {"ok": True, "dry_run": True, "run_id": run_id, "pass_num": pass_num}

    result = _durable_remote_shell(
        command,
        max_len=32768,
        command_timeout=60,
        dispatch_timeout=90,
        operation_type="wave2_collector_launch",
        correlation_id=f"w2-{run_id}-p{pass_num}",
        candidate_sha=sha,
    )
    if not result.get("ok"):
        return {
            "ok": False,
            "error": result.get("error"),
            "run_id": run_id,
            "pass_num": pass_num,
            "transport": result,
        }
    return {"ok": True, "run_id": run_id, "pass_num": pass_num}


def _stop_remote_collector_tree(runner: Runner, *, run_id: str, pass_num: int = 1) -> dict[str, Any]:
    """Stop the exact Beast collector tree recorded at dispatch.

    The collector is detached on Beast so the VPS teardown cannot rely on a
    local Popen handle. Dispatch writes a run-scoped manifest containing the
    detached cmd.exe root PID; teardown revalidates that PID's command line
    against this run before sending a signal. Escalation is exact-tree only.
    """
    pid_manifest = rf"{_BEAST_EVIDENCE_DIR}\collector_{run_id}_p{pass_num}.pid.json"
    ps = rf"""
$ErrorActionPreference = 'Continue'
$m = '{pid_manifest}'
$rid = '{run_id}'
$pat = '*wave2_field_collector.py*'
if (-not (Test-Path -LiteralPath $m)) {{
  $r = @(gwmi Win32_Process | ? {{ ([string]$_.CommandLine) -like "*$rid*" -and ([string]$_.CommandLine) -like $pat }} | select ProcessId,ParentProcessId,Name,CommandLine)
  [pscustomobject]@{{stopped=($r.Count -eq 0);note="no collector pid manifest";residue=$r}} | ConvertTo-Json -Compress -Depth 4
  exit 0
}}
$j = Get-Content -Raw -LiteralPath $m | ConvertFrom-Json
$rootPid = [int]$j.pid
$p = gwmi Win32_Process -Filter "ProcessId=$rootPid"
if ($null -eq $p) {{
  $r = @(gwmi Win32_Process | ? {{ ([string]$_.CommandLine) -like "*$rid*" -and ([string]$_.CommandLine) -like $pat }} | select ProcessId,ParentProcessId,Name,CommandLine)
  [pscustomobject]@{{stopped=($r.Count -eq 0);pid=$rootPid;note="collector root already absent";residue=$r}} | ConvertTo-Json -Compress -Depth 4
  exit 0
}}
$cmd = [string]$p.CommandLine
if ($cmd -notlike "*$rid*" -or $cmd -notlike $pat) {{
  Write-Output ('{{"stopped":false,"pid":' + $rootPid + ',"reason":"pid identity mismatch","command":' + ($cmd | ConvertTo-Json -Compress) + '}}')
  exit 2
}}
$childrenBefore = @(gwmi Win32_Process | ? {{ $_.ParentProcessId -eq $rootPid }} | select ProcessId,ParentProcessId,Name,CommandLine)
$gracefulOutput = (& cmd.exe /c "taskkill /PID $rootPid /T" 2>&1 | Out-String)
Start-Sleep -Seconds 5
$alive = gwmi Win32_Process -Filter "ProcessId=$rootPid"
$forced = $false
$forceOutput = ""
if ($null -ne $alive) {{
  $p2 = gwmi Win32_Process -Filter "ProcessId=$rootPid"
  $cmd2 = [string]$p2.CommandLine
  if ($cmd2 -notlike "*$rid*" -or $cmd2 -notlike $pat) {{
    Write-Output ('{{"stopped":false,"pid":' + $rootPid + ',"reason":"identity changed before force","command":' + ($cmd2 | ConvertTo-Json -Compress) + '}}')
    exit 3
  }}
  $forceOutput = (& cmd.exe /c "taskkill /PID $rootPid /T /F" 2>&1 | Out-String)
  Start-Sleep -Seconds 2
  $forced = $true
}}
$still = gwmi Win32_Process -Filter "ProcessId=$rootPid"
$r = @(gwmi Win32_Process | ? {{ ([string]$_.CommandLine) -like "*$rid*" -and ([string]$_.CommandLine) -like $pat }} | select ProcessId,ParentProcessId,Name,CommandLine)
[pscustomobject]@{{stopped=($null -eq $still -and $r.Count -eq 0);pid=$rootPid;forced=$forced;graceful_output=$gracefulOutput;force_output=$forceOutput;children_before=$childrenBefore;residue=$r}} | ConvertTo-Json -Compress -Depth 4
"""
    command = _powershell_encoded_command(ps)
    res = _mesh_read(runner, command, max_len=65536)
    if runner.dry_run:
        return {"stopped": True, "dry_run": True}
    if not res.get("ok"):
        return {
            "stopped": False,
            "reason": res.get("error") or "mesh dispatch failed",
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "raw_status": res.get("raw_status"),
        }
    try:
        parsed = json.loads(res.get("stdout", "") or "{}")
    except ValueError:
        return {"stopped": False, "reason": "collector teardown returned malformed JSON"}
    return parsed if isinstance(parsed, dict) else {"stopped": False, "reason": "bad result"}


def _collector_residue_query(run_id: str, pass_num: int) -> str:
    pid_manifest = rf"{_BEAST_EVIDENCE_DIR}\collector_{run_id}_p{pass_num}.pid.json"
    launch_log = rf"{_BEAST_EVIDENCE_DIR}\launch_{run_id}_p{pass_num}.log"
    ps = rf"""
$ErrorActionPreference = 'Continue'
$runId = '{run_id}'
$manifestPath = '{pid_manifest}'
$launchLog = '{launch_log}'
function ChildrenOf([int]$root) {{
  $seen = @{{}}
  $queue = New-Object System.Collections.ArrayList
  [void]$queue.Add($root)
  $out = @()
  while ($queue.Count -gt 0) {{
    $parent = [int]$queue[0]
    $queue.RemoveAt(0)
    $kids = @(Get-CimInstance Win32_Process | Where-Object {{ $_.ParentProcessId -eq $parent }})
    foreach ($kid in $kids) {{
      $key = [string]$kid.ProcessId
      if (-not $seen.ContainsKey($key)) {{
        $seen[$key] = $true
        $out += $kid
        [void]$queue.Add([int]$kid.ProcessId)
      }}
    }}
  }}
  return $out
}}
$manifest = $null
$root = $null
$tree = @()
if (Test-Path -LiteralPath $manifestPath) {{
  $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
  $root = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int]$manifest.pid)
  if ($null -ne $root) {{
    $tree = @(ChildrenOf([int]$manifest.pid) | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate)
  }}
}}
$broad = @(Get-CimInstance Win32_Process | Where-Object {{ ([string]$_.CommandLine) -like "*$runId*" -or ([string]$_.CommandLine) -like "*wave2_field_collector.py*" }} | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate)
$logTail = ""
if (Test-Path -LiteralPath $launchLog) {{
  $logTail = (Get-Content -LiteralPath $launchLog -Tail 80 | Out-String)
}}
[pscustomobject]@{{
  run_id = $runId
  manifest_path = $manifestPath
  launch_log = $launchLog
  manifest_exists = (Test-Path -LiteralPath $manifestPath)
  manifest = $manifest
  root = if ($null -eq $root) {{ $null }} else {{ $root | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate }}
  recorded_descendants = $tree
  broad_residue = $broad
  launch_log_tail = $logTail
}} | ConvertTo-Json -Compress -Depth 6
"""
    return _powershell_encoded_command(ps)


def _cleanup_collector_rehearsal_artifacts(
    runner: Runner, *, run_id: str, pass_num: int
) -> dict[str, Any]:
    ps = rf"""
$ErrorActionPreference = 'Continue'
$paths = @(
  '{_BEAST_EVIDENCE_DIR}\collector_{run_id}_p{pass_num}.pid.json',
  '{_BEAST_EVIDENCE_DIR}\launch_{run_id}_p{pass_num}.log',
  '{_BEAST_EVIDENCE_DIR}\inert_collector_{run_id}_p{pass_num}.py'
)
$removed = @()
$errors = @()
foreach ($path in $paths) {{
  try {{
    if (Test-Path -LiteralPath $path) {{
      Remove-Item -LiteralPath $path -Force
      $removed += $path
    }}
  }} catch {{
    $errors += ([string]$_)
  }}
}}
[pscustomobject]@{{ok=($errors.Count -eq 0);removed=$removed;errors=$errors}} | ConvertTo-Json -Compress -Depth 3
"""
    res = _mesh_read(runner, _powershell_encoded_command(ps), max_len=32768)
    if runner.dry_run:
        return {"ok": True, "dry_run": True}
    if not res.get("ok"):
        return {"ok": False, "reason": res.get("error"), "mesh": res}
    try:
        parsed = json.loads(res.get("stdout", "") or "{}")
    except ValueError:
        return {"ok": False, "reason": "cleanup returned malformed JSON", "mesh": res}
    return parsed if isinstance(parsed, dict) else {"ok": False, "reason": "bad cleanup result"}


def _launch_inert_collector_fixture(
    runner: Runner, *, run_id: str, pass_num: int, sha: str
) -> dict[str, Any]:
    """Launch an inert process with the production collector command topology.

    The Python command sleeps and never imports/executes the field collector.
    ``wave2_field_collector.py`` is carried only as argv text so the same PID
    manifest and identity checks bind to the rehearsal run ID.
    """
    launch_log = rf"{_BEAST_EVIDENCE_DIR}\launch_{run_id}_p{pass_num}.log"
    pid_manifest = rf"{_BEAST_EVIDENCE_DIR}\collector_{run_id}_p{pass_num}.pid.json"
    inert_py = rf"{_BEAST_EVIDENCE_DIR}\inert_collector_{run_id}_p{pass_num}.py"
    inert_code = (
        "import sys, time\n"
        "print('inert collector rehearsal', sys.argv[1:])\n"
        "sys.stdout.flush()\n"
        "time.sleep(600)\n"
    )
    inert_code_b64 = base64.b64encode(inert_code.encode("utf-8")).decode("ascii")
    inert = (
        f"op run --env-file={_BEAST_ENV_TPL} -- python {inert_py} "
        f"{_BEAST_COLLECTOR} --run-id {run_id} --pass-num {pass_num} "
        f"--candidate-commit {sha} --inert-teardown-rehearsal"
    )
    inner = f"/c md {_BEAST_EVIDENCE_DIR} 2>nul & {inert} 1> {launch_log} 2>&1"
    ps_command = (
        "powershell -NoProfile -Command "
        f"\"$code=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{inert_code_b64}')); "
        f"Set-Content -Path '{inert_py}' -Value $code; "
        "$p=Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' "
        f"-ArgumentList '{inner}' -PassThru; "
        "$payload=[ordered]@{"
        f"pid=$p.Id;run_id='{run_id}';pass_num={pass_num};"
        f"candidate_commit='{sha}';command='{_BEAST_COLLECTOR}';inert=$true"
        "} | ConvertTo-Json -Compress; "
        f"Set-Content -Path '{pid_manifest}' -Value $payload; "
        "$payload\""
    )
    res = _mesh_read(runner, ps_command, max_len=32768)
    if runner.dry_run:
        return {"ok": True, "dry_run": True, "command": ps_command}
    if not res.get("ok"):
        return {"ok": False, "reason": res.get("error"), "mesh": res}
    try:
        manifest = json.loads(res.get("stdout", "") or "{}")
    except ValueError:
        return {"ok": False, "reason": "launch returned malformed JSON", "mesh": res}
    return {"ok": True, "manifest": manifest, "mesh": res}


def collector_teardown_rehearsal(
    runner: Runner, sha: str, *, iterations: int = 3
) -> dict[str, Any]:
    """Run zero-quota inert Beast collector lifecycle/teardown rehearsals."""
    proof_dir = _proof_root() / "collector_teardown_rehearsal"
    proof_dir.mkdir(parents=True, exist_ok=True)
    if runner.dry_run:
        return {"ok": True, "dry_run": True, "iterations": iterations}

    results: list[dict[str, Any]] = []
    for idx in range(1, iterations + 1):
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-teardown-r{idx}"
        pass_num = 1
        item: dict[str, Any] = {"run_id": run_id, "pass_num": pass_num}
        before = _mesh_read(runner, _collector_residue_query(run_id, pass_num), max_len=65536)
        item["before"] = before
        before_obj: dict[str, Any] = {}
        try:
            before_obj = json.loads(before.get("stdout", "") or "{}")
        except ValueError:
            item["ok"] = False
            item["reason"] = "before residue query malformed"
            results.append(item)
            continue
        if before_obj.get("broad_residue"):
            item["ok"] = False
            item["reason"] = "matching residue exists before launch"
            results.append(item)
            continue

        launched = _launch_inert_collector_fixture(runner, run_id=run_id, pass_num=pass_num, sha=sha)
        item["launch"] = launched
        if not launched.get("ok"):
            item["ok"] = False
            item["reason"] = "launch failed"
            results.append(item)
            continue
        time.sleep(2)

        manifest = launched.get("manifest") or {}
        manifest_ok = (
            manifest.get("run_id") == run_id
            and int(manifest.get("pass_num", -1)) == pass_num
            and manifest.get("candidate_commit") == sha
            and manifest.get("command") == _BEAST_COLLECTOR
            and manifest.get("inert") is True
        )
        item["manifest_ok"] = manifest_ok
        if not manifest_ok:
            item["ok"] = False
            item["reason"] = "manifest identity mismatch"
            results.append(item)
            continue

        active = _mesh_read(runner, _collector_residue_query(run_id, pass_num), max_len=65536)
        item["active"] = active
        stopped = _stop_remote_collector_tree(runner, run_id=run_id, pass_num=pass_num)
        item["teardown"] = stopped
        after = _mesh_read(runner, _collector_residue_query(run_id, pass_num), max_len=65536)
        item["after"] = after
        second = _stop_remote_collector_tree(runner, run_id=run_id, pass_num=pass_num)
        item["idempotent_teardown"] = second
        final = _mesh_read(runner, _collector_residue_query(run_id, pass_num), max_len=65536)
        item["final"] = final
        cleanup = _cleanup_collector_rehearsal_artifacts(runner, run_id=run_id, pass_num=pass_num)
        item["cleanup"] = cleanup

        try:
            active_obj = json.loads(active.get("stdout", "") or "{}")
            after_obj = json.loads(after.get("stdout", "") or "{}")
            final_obj = json.loads(final.get("stdout", "") or "{}")
        except ValueError:
            item["ok"] = False
            item["reason"] = "residue query returned malformed JSON"
            results.append(item)
            continue
        item["forced"] = bool(stopped.get("forced"))
        item["ok"] = (
            bool(stopped.get("stopped"))
            and bool(second.get("stopped"))
            and not after_obj.get("broad_residue")
            and not final_obj.get("broad_residue")
            and bool(cleanup.get("ok"))
            and bool(active_obj.get("root"))
            and bool(active_obj.get("recorded_descendants") or active_obj.get("broad_residue"))
        )
        if not item["ok"]:
            item["reason"] = "teardown did not prove zero residue"
        results.append(item)

    out = {
        "ok": len(results) == iterations and all(bool(r.get("ok")) for r in results),
        "iterations": iterations,
        "results": results,
        "forced_count": sum(1 for r in results if r.get("forced")),
        "evidence_dir": str(proof_dir),
    }
    evidence_path = proof_dir / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    evidence_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    if out["forced_count"] < 1:
        out["ok"] = False
        out["reason"] = "remote rehearsals did not exercise exact-force escalation"
    return out


def _mesh_read_fast(runner: Runner, command: str, *, max_len: int = 65536) -> dict[str, Any]:
    """Low-latency mesh read with 15s timeout (vs 90s in _mesh_read).

    Used by the collector-authorization gate where every second counts: a slow
    mesh read can eat into w16's 240-second polling window.
    """
    if runner.dry_run:
        return {"dry_run": True, "command": command, "ok": True, "stdout": "{}"}
    return _durable_remote_shell(
        command,
        max_len=max_len,
        command_timeout=10,
        dispatch_timeout=15,
        operation_type="wave2_fast_read",
    )


def _wait_collector_authorization(
    runner: Runner,
    run_id: str,
    pass_num: int,
    *,
    timeout_min: int = 25,
    candidate_sha: str = "",
) -> bool:
    """Poll status.json until the collector reaches w15 (execution authorized).

    The runner must NOT start creating workers until the collector has navigated
    the cockpit through w15_authorize_execution — otherwise workers complete
    before the collector reaches w16_ab_running_concurrent and w16 observes
    dom_running=0. This gate was the root cause of EVERY w16 failure after the
    runner was wired into run_passes (workers complete in ~100s; the collector
    takes ~15-19 min to reach w16 from dispatch).

    CRITICAL: w16 has only a 240-second polling window. This gate must detect
    stages_done >= 15 within seconds, not minutes. Uses _mesh_read_fast (15s
    timeout) and 3-second poll interval to avoid missing the window.
    """
    status_path = f"{_BEAST_EVIDENCE_DIR}\\{run_id}\\pass{pass_num}\\status.json"
    read_cmd = f"type {status_path}"
    deadline = time.time() + timeout_min * 60
    consecutive_failures = 0
    last_stages = 0
    while time.time() < deadline:
        if runner.dry_run:
            print(f"[dry-run] wait for collector to reach w15 (poll {status_path})")
            return True
        t0 = time.time()
        res = _mesh_read_fast(runner, read_cmd)
        elapsed = time.time() - t0
        if res.get("ok", False):
            consecutive_failures = 0
            try:
                status = json.loads(res.get("stdout", ""))
                stages = status.get("stages_done", 0)
                if stages != last_stages:
                    print(f"[runner-gate] collector at stage {stages} ({elapsed:.1f}s mesh)")
                    last_stages = stages
                if stages >= 15:
                    print(f"[runner-gate] collector reached stage {stages} — starting runner")
                    return True
                state = status.get("state", "")
                if state == "evidence_uploaded":
                    upload = status.get("evidence_upload")
                    if isinstance(upload, dict) and candidate_sha:
                        committed = _commit_uploaded_evidence_transaction(
                            upload,
                            candidate_sha,
                            run_id=run_id,
                            pass_num=pass_num,
                        )
                        print(
                            "[runner-gate] collector uploaded terminal evidence before w15 "
                            f"(commit_ok={bool(committed.get('ok'))}) — aborting runner start"
                        )
                    else:
                        print(
                            "[runner-gate] collector uploaded terminal evidence before w15 "
                            "— aborting runner start"
                        )
                    return False
                if state == "evidence_preservation_failed":
                    print(
                        "[runner-gate] collector evidence preservation failed before w15 "
                        "— aborting runner start"
                    )
                    return False
                if state in ("passed", "failed"):
                    print(
                        f"[runner-gate] collector terminal ({state}) before w15 — aborting runner start"
                    )
                    return False
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            consecutive_failures += 1
            if consecutive_failures % 5 == 0:
                print(
                    f"[runner-gate] {consecutive_failures} consecutive mesh failures ({elapsed:.1f}s)"
                )
        time.sleep(3)
    print(f"[runner-gate] timed out waiting for collector to reach w15 ({timeout_min}m)")
    return False


def dispatch_pass(
    runner: Runner, *, run_id: str, pass_num: int, scenario: str, sha: str
) -> dict[str, Any]:
    """Dispatch one collector pass (governed write-class) and poll to terminal."""
    dispatched = _dispatch_collector(
        runner,
        run_id=run_id,
        pass_num=pass_num,
        scenario=scenario,
        sha=sha,
    )
    if not dispatched.get("ok"):
        return dispatched
    if runner.dry_run:
        _poll_status(runner, run_id, pass_num, candidate_sha=sha)
        return {"dry_run": True, "run_id": run_id, "pass_num": pass_num}
    terminal = _poll_status(runner, run_id, pass_num, candidate_sha=sha)
    return {"ok": terminal.get("state") == "passed", "terminal": terminal, "run_id": run_id}


def _verify_beast_collector_commit(runner: Runner, sha: str) -> dict[str, Any]:
    """Exact-commit binding for the collector CODE: the Beast worktree the
    collector runs from must be checked out at the candidate sha. Refuse to
    dispatch otherwise — a stale collector would qualify the wrong journey."""
    if runner.dry_run:
        print(f"[dry-run] would verify {_BEAST_WT} HEAD == {sha}")
        return {"ok": True, "dry_run": True}
    if not _is_full_candidate_sha(sha):
        return {"ok": False, "error": "candidate sha must be full 40-hex", "candidate_sha": sha}
    probe = _mesh_read(runner, rf"git -C {_BEAST_WT} rev-parse HEAD")
    beast_head = (probe.get("stdout") or "").strip()
    ok = probe.get("ok", False) and beast_head == sha
    return {"ok": ok, "beast_worktree_head": beast_head, "candidate_sha": sha}


def run_passes(runner: Runner, *, sha: str, scenario: str, passes: int) -> dict[str, Any]:
    """Run N collector passes with fresh run-ids; restart candidate before pass 1.

    For ``full`` scenario passes, the host-side attempt runner (control plane +
    worker loop) is started before and stopped after each pass. Without it, no
    scheduler runs after the operator authorizes execution, so zero Attempts are
    created and w16_ab_running_concurrent always fails. The runner is run-scoped:
    its spool and targets dir are keyed (sha, run_id), so each pass gets its own
    runner instance.
    """
    # READINESS GATE (finding SEC-C3): refuse to dispatch anything against a
    # candidate that is not answering. A failed gate consumes ZERO worker quota
    # because no dispatch is written, and it returns a non-zero exit via main().
    ready = _wait_candidate_ready(runner, timeout_s=120.0)
    if not runner.dry_run and not ready.get("ready"):
        return {
            "scenario": scenario,
            "passes": 0,
            "ok": False,
            "refused": "candidate is not ready — refusing to dispatch (zero quota consumed)",
            "readiness": ready,
        }

    binding = _verify_beast_collector_commit(runner, sha)
    if not binding.get("ok"):
        return {
            "scenario": scenario,
            "passes": 0,
            "ok": False,
            "refused": "beast collector worktree is not at the candidate commit",
            "binding": binding,
        }
    results = []
    for i in range(1, passes + 1):
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-p{i}"
        if i == 1:
            # RES-growth mitigation: restart the candidate before the first pass.
            runner.run(["docker", "restart", _CANDIDATE_CONTAINER], timeout=120, check=False)
            # WAIT for the upstream to answer again before dispatching. A single
            # probe is not a readiness gate: the operator needs ~15s to boot
            # (warm VoiceEngine preload), so pass 1 previously raced the restart
            # and its first requests hit nginx with no upstream -> 502s that the
            # reconciler correctly counts as orphan 5xx (run 20260723T052247Z-p1:
            # device/register + execution-summary, both at ms~10000, zero journey
            # impact but a hard reconciliation failure).
            _wait_candidate_ready(runner)

        # FULL SCENARIO RUNNER LIFECYCLE
        #
        # Root cause of ALL w16 failures: the runner must NOT create workers
        # before the collector reaches w15 (execution authorization). If the
        # runner starts immediately, it finds stale authorized plans (from the
        # smoke pass or a previous full pass) and creates workers that complete
        # in ~100s — long before the collector reaches w16 (~15-19 min after
        # dispatch). w16 then observes dom_running=0 and fails.
        #
        # Correct sequence:
        #   1. seed_fixture (prepare the fixture workspace)
        #   2. dispatch collector to Beast (non-blocking mesh dispatch)
        #   3. wait for collector to reach w15 (stages_done >= 15)
        #   4. start_runner (workers are created AFTER collector is ready)
        #   5. poll for collector completion
        runner_started: dict[str, Any] = {}
        if scenario == "full":
            fixture = seed_fixture(runner, sha, run_id, variant="clean")
            if not fixture.get("dest"):
                results.append(
                    {
                        "ok": False,
                        "error": "seed_fixture failed",
                        "fixture": fixture,
                        "run_id": run_id,
                    }
                )
                continue

            # Step 2: dispatch collector FIRST (it needs ~15-19 min to reach w15)
            dispatched = _dispatch_collector(
                runner,
                run_id=run_id,
                pass_num=i,
                scenario=scenario,
                sha=sha,
            )
            if not dispatched.get("ok"):
                results.append(dispatched)
                continue

            # Step 3: wait for collector to reach w15 before starting workers
            if not _wait_collector_authorization(runner, run_id, i, candidate_sha=sha):
                results.append(
                    {
                        "ok": False,
                        "error": "collector did not reach w15 — runner not started",
                        "run_id": run_id,
                    }
                )
                continue

            # Step 3b: MATERIALIZE THE RUN'S AUTHENTICATED EXECUTION BINDING
            # BEFORE the runner is admitted.
            #
            # w15 grants execution authorization, but the runner's attempt-
            # creation boundary reads `execution_binding.json` (via
            # read_execution_binding) to classify each Task. Without it,
            # read_execution_binding returns None → the declaration is
            # UNANSWERABLE → the store stays SEALED ("UNKNOWN MUST NEVER MEAN
            # WORKER") → zero Attempts are ever created and the whole A+B→C→D
            # graph fails. A green pass therefore runs the SAME authenticated
            # pre-run lifecycle the qualified failure/recovery driver runs —
            # grant-durability wait → write_scenario_map — differing ONLY by the
            # absence of deliberate failure injection.
            #
            # No admission pause/resume here: pause_before_dispatch exists solely
            # to open the window inject_failure binds into, and resume_after_pause
            # refuses to release an UNARMED pause. A green pass injects nothing,
            # so it must NOT arm the pause — the runner admits Attempts naturally
            # once the binding is durable (dispatch_is_paused is False when no
            # marker exists). Adding pause/resume to green would be incidental
            # injection scaffolding, not a required step (verified in source:
            # field_failure_policy.pause_state / resume_after_pause arming check).
            #
            # PRESEED THE WORKTREE SUBSTRATE FIRST. Everything above this point
            # (_wait_candidate_ready, _verify_beast_collector_commit) drove
            # `_mesh_read` → `mesh_dispatch_port`, which cached `substrate` /
            # `substrate.execution` from `/opt/OS` (no `execution/attempts/`).
            # The binding wait imports `substrate.execution.attempts.*`; without
            # this preseed, that import resolves against the stale `/opt/OS`
            # parent and the whole green pass crashes with ModuleNotFoundError
            # BEFORE any Attempt is created (run 20260808T213735Z-p1). The
            # failure/recovery driver's CLI subcommands never hit this because
            # each runs in a fresh process with no prior mesh read. Making the
            # candidate worktree own the `substrate` package identity here — the
            # one boundary green first needs it — keeps green and
            # failure/recovery resolving the SAME candidate implementation.
            if not runner.dry_run:
                _preseed_worktree_substrate()
            binding, berr = _wait_for_bindable_grant(runner, sha=sha, run_id=run_id)
            if not runner.dry_run and binding is None:
                results.append(
                    {
                        "ok": False,
                        "error": f"execution binding never became durable: {berr}",
                        "run_id": run_id,
                    }
                )
                continue
            smap = write_scenario_map(runner, sha, run_id)
            if not runner.dry_run and not smap.get("written"):
                # FAIL CLOSED: no binding on disk → the runner would refuse every
                # Task. Never start the runner against a run with no readable
                # execution binding. write_scenario_map's contract returns
                # {"written": True|False} — that single key is the authority.
                results.append(
                    {
                        "ok": False,
                        "error": "write_scenario_map refused — no execution binding for run",
                        "scenario_map": smap,
                        "run_id": run_id,
                    }
                )
                continue

            # Step 4: NOW start the runner — collector is ready AND the run's
            # authenticated execution binding is durable on disk.
            runner_started = start_runner(runner, sha, run_id, max_iterations=0)
            if not runner_started.get("started", runner_started.get("dry_run", False)):
                results.append(
                    {
                        "ok": False,
                        "error": "start_runner failed",
                        "runner": runner_started,
                        "run_id": run_id,
                    }
                )
                continue

            # Step 5: poll for collector completion
            try:
                terminal = _poll_status(runner, run_id, i, candidate_sha=sha)
                results.append(
                    {
                        "ok": terminal.get("state") == "passed",
                        "terminal": terminal,
                        "run_id": run_id,
                    }
                )
            finally:
                if runner_started.get("started", False):
                    stop_runner(runner, sha, run_id)
            continue

        try:
            results.append(
                dispatch_pass(runner, run_id=run_id, pass_num=i, scenario=scenario, sha=sha)
            )
        finally:
            pass
    return {"scenario": scenario, "passes": passes, "results": results}


# ─────────────────────────────────────────────────────────────────────────────
# reconcile
# ─────────────────────────────────────────────────────────────────────────────
# Gating UI transitions → the state-record token each must correspond to. Every
# one of these, when asserted OK by the collector, must have a matching runtime
# state record carrying the run tag, or reconciliation fails the pass.
#
# 21-step journey (plan v5.1 §23). The collector emits s## stage ids; each entry
# below maps a gating step to a substring that MUST appear in the candidate's own
# runtime-state JSONLs / logs for the pass's run tag. Server-side lifecycle the
# journey must produce (recorded here for auditability):
#   session stages: RESOLVING_OBJECTIVE → OBJECTIVE_RESOLVED → PLAN_COMPILED →
#                   TASKS_MATERIALIZED → DECISION_EVALUATED → COMMITTED
#   plan status:    draft → awaiting_approval → approved
#   decision_log:   entry with authorization_effect=plan_acceptance_only
#   JSONLs under operator/objective_planning/: objective_plans.jsonl and
#                   strategic_gaps/goals.jsonl (the canonical Goal)
#
# Only the load-bearing state-producing steps are gated for reconciliation. Pure
# negative/read-only steps (s01/s02/s03/s05/s08/s11/s12/s13/s14/s17/s18/s20/s21)
# assert absence or read-only invariants and produce no NEW state record, so they
# are not reconciled against a state token here (they still gate the collector's
# own pass verdict).
#
# CRITICAL (CodeRabbit MAJOR fix): a transition matches ONLY when a SINGLE state
# record carries the run tag AND independently satisfies that transition's token
# predicate. A blanket `run_tag in state_blob` check is a false-positive class:
# a pass that merely rendered a plan would otherwise "match" approved/rejected.
# Each predicate below receives one parsed JSONL record (dict) plus the run_tag
# and returns True only if THAT record proves the transition.
#
# `token` is the human-readable expected state token (surfaced in evidence);
# `match` is the predicate applied per-record.
_GATING_TRANSITIONS: dict[str, dict[str, Any]] = {
    # A task packet materialized: a packet record with a non-plan source whose
    # text carries the run tag and whose status is a captured (non-executable) one.
    "s04_simple_task": {
        "token": "packet",
        "match": lambda rec, tag: (
            _record_has_tag(rec, tag)
            and _is_packet_record(rec)
            and _record_status(rec) in _CAPTURED_STATUSES
        ),
    },
    # Plan compiled + awaiting approval: a plan record with the run tag whose
    # status is awaiting_approval (v1) — the compile→awaiting transition.
    "s07_complex_objective": {
        "token": "awaiting_approval|PLAN_COMPILED",
        # A plan whose compare-and-swap status has already advanced past awaiting
        # (approved/revised) still proves compile happened — accept any post-draft
        # plan status, OR a session record whose operation_stage reached compile.
        "match": lambda rec, tag: (
            _record_has_tag(rec, tag)
            and (
                (_is_plan_record(rec) and _record_status(rec) in _COMPILED_PLAN_STATUSES)
                or _session_stage_reached_compile(rec)
            )
        ),
    },
    # Plan packets materialized: the run-tagged objective_plan record itself
    # carries >=1 workpacket_id AND >=1 packet node in its graph. Materialized
    # WorkPackets are recorded ON the plan record (workpacket_ids + nodes),
    # not as separate rows in work_packets.jsonl (that store holds only the
    # simple-task/legacy packets) — so the plan record IS the authoritative
    # materialization evidence (verified 2026-07-23: every approved full-pass
    # plan carries 7 wp-ids + 7 packet nodes while work_packets.jsonl had none).
    "s09_tasks_on_kanban": {
        "token": "workpacket_ids>=1",
        "match": lambda rec, tag: (
            _record_has_tag(rec, tag)
            and bool(rec.get("plan_record_id"))
            and len(rec.get("workpacket_ids") or []) >= 1
            and any(
                n.get("kind") == "packet" for n in (rec.get("nodes") or []) if isinstance(n, dict)
            )
        ),
    },
    # Revision: a plan record with the run tag whose graph_version >= 2 (v1 was
    # preserved via supersede; this is the v2 revised record).
    "s10_conversational_revision": {
        "token": "graph_version>=2",
        "match": lambda rec, tag: (
            _record_has_tag(rec, tag)
            and _is_plan_record(rec)
            and isinstance(rec.get("graph_version"), int)
            and rec.get("graph_version", 0) >= 2
        ),
    },
    # Decision committed: a plan record with the run tag whose status is approved.
    "s15_approve_via_hud": {
        "token": "approved",
        "match": lambda rec, tag: (
            _record_has_tag(rec, tag) and _is_plan_record(rec) and _record_status(rec) == "approved"
        ),
    },
    # Decision-log proof: a plan record with the run tag whose decision_log has an
    # entry with authorization_effect == plan_acceptance_only (approval accepted
    # the plan only — no execution authority).
    "s16_approved_banner": {
        "token": "plan_acceptance_only",
        "match": lambda rec, tag: (
            _record_has_tag(rec, tag)
            and _is_plan_record(rec)
            and _decision_log_has_effect(rec, "plan_acceptance_only")
        ),
    },
}

# Packet statuses that are "captured / non-executable" (a task on the board that
# has NOT been authorized to run). Mirrors the collector's non-exec set.
_CAPTURED_STATUSES = frozenset({"drafted", "classified", "planned", "ready_for_review"})

# Plan statuses that all prove a compile already happened (draft would NOT, but
# any of these is post-compile). A compare-and-swap store advances the SAME plan
# record's status, so a fully-approved pass's plan is 'approved', not 'awaiting'.
_COMPILED_PLAN_STATUSES = frozenset(
    {"awaiting_approval", "revised", "approved", "rejected", "cancelled", "superseded"}
)

# PlanningStageMarker values (substrate/execution/planning/records.py) that mean
# compile has been reached on a session record.
_COMPILE_STAGE_VALUES = frozenset(
    {"plan_compiled", "tasks_materialized", "decision_evaluated", "committed"}
)


def _session_stage_reached_compile(rec: dict[str, Any]) -> bool:
    """Whether a session record's operation_stage has reached compile-or-later."""
    return str(rec.get("operation_stage", "")).lower() in _COMPILE_STAGE_VALUES


def _record_has_tag(rec: dict[str, Any], run_tag: str) -> bool:
    """Whether this ONE record carries the run tag anywhere in its own text.

    Serializes just this record and substring-checks — so co-occurrence is proven
    within a single record, never across the whole state blob.
    """
    if not run_tag:
        return False
    try:
        return run_tag in json.dumps(rec, default=str)
    except (TypeError, ValueError):
        return False


def _is_plan_record(rec: dict[str, Any]) -> bool:
    """A plan record has a plan_record_id and an objective_text/status pair."""
    return bool(rec.get("plan_record_id")) or (
        "graph_version" in rec and "objective_text" in rec and "workpacket_ids" in rec
    )


def _is_packet_record(rec: dict[str, Any]) -> bool:
    """A packet record carries a packet_id (and is not a plan record)."""
    return bool(rec.get("packet_id")) and not rec.get("plan_record_id")


def _record_status(rec: dict[str, Any]) -> str:
    """Lower-cased status token of a plan/packet/session record ('' if absent)."""
    return str(rec.get("status") or rec.get("operation_stage") or "").lower()


def _decision_log_has_effect(rec: dict[str, Any], effect: str) -> bool:
    """Whether the record's decision_log has an entry with the given auth effect."""
    log = rec.get("decision_log")
    if not isinstance(log, list):
        return False
    return any(
        isinstance(e, dict) and str(e.get("authorization_effect", "")) == effect for e in log
    )


def _safe_match(predicate: Any, rec: dict[str, Any], run_tag: str) -> bool:
    """Apply a transition predicate to one record, never raising on a bad record."""
    try:
        return bool(predicate(rec, run_tag))
    except Exception:  # noqa: BLE001 — a malformed record is a non-match, not a crash
        return False


def _candidate_state_jsonls(sha: str) -> list[Path]:
    """All runtime-state JSONLs the candidate may have written (glob broadly).

    We glob every JSONL under the candidate state dir and match run tags rather
    than hard-code filenames. The load-bearing planning records live under
    operator/objective_planning/ (objective_plans.jsonl and the canonical Goal in
    strategic_gaps/goals.jsonl); packet + conversation records (universal_work,
    organism/messages, operator_experience) are picked up by the same glob.
    """
    root = _state_dir(sha).parent  # .../state/umh
    if not root.exists():
        return []
    return sorted(root.rglob("*.jsonl"))


def reconcile(runner: Runner, sha: str) -> dict[str, Any]:
    """Score each pass: browser evidence vs candidate state + docker logs."""
    raw_root = _proof_root() / "raw"
    summary: dict[str, Any] = {"passes": [], "sha": sha}
    if not _is_full_candidate_sha(sha):
        summary["all_passed"] = False
        summary["error"] = "candidate sha must be full 40-hex"
        return summary
    if runner.dry_run:
        print(f"[dry-run] reconcile: scan {raw_root}/*/pass*/ vs candidate state + docker logs")
        print(f"[dry-run]   docker logs {_CANDIDATE_CONTAINER} --since <pass start>")
        print(f"[dry-run]   glob candidate state JSONLs under {_state_dir(sha).parent}")
        return {"dry_run": True, "raw_root": str(raw_root)}

    state_records = _read_state_records(sha)
    logs = _candidate_logs(runner)

    # Scope to the FULL passes of the candidate SHA under qualification. The
    # day's proof root also holds smoke passes and earlier requalified runs of
    # OTHER shas — mixing them in scored the wrong evidence and imported a
    # pre-fix run's warm-up 5xx list (observed 2026-07-23). A qualifying pass
    # is: candidate_commit == sha AND scenario == "full".
    candidate_passes = []
    for pass_dir in sorted(raw_root.glob("*/pass*")):
        rj = pass_dir / "result.json"
        if not rj.exists():
            continue
        receipt = _fresh_process_verified_evidence_receipt(pass_dir, sha)
        if receipt is None:
            continue
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if r.get("candidate_commit") == sha and r.get("scenario") == "full":
            candidate_passes.append((pass_dir, receipt))

    for pass_dir, receipt in candidate_passes:
        result_json = pass_dir / "result.json"
        network_jsonl = pass_dir / "network.jsonl"
        if not result_json.exists():
            continue
        result = json.loads(result_json.read_text(encoding="utf-8"))
        run_tag = result.get("run_tag", "")
        network = _read_jsonl(network_jsonl)

        # Requests reconciliation: every asserted API request should show up in
        # the candidate docker logs.
        total_requests = len(network)
        matched_requests = sum(1 for n in network if _path_in_logs(n.get("url", ""), logs))

        # Transition reconciliation: every gating UI transition must have a state
        # record that carries the run tag AND independently satisfies that
        # transition's own token predicate — proven within a SINGLE record. This
        # is the CodeRabbit MAJOR fix: a plan that was only rendered scores ONLY
        # the transitions whose records actually exist (e.g. never "approved").
        asserted = [
            s["stage"]
            for s in result.get("stages", [])
            if s["stage"] in _GATING_TRANSITIONS and s["ok"]
        ]
        matched_transitions = 0
        transition_detail = {}
        for stage_name in asserted:
            spec = _GATING_TRANSITIONS[stage_name]
            predicate = spec["match"]
            matching = [rec for rec in state_records if _safe_match(predicate, rec, run_tag)]
            has_record = bool(matching)
            transition_detail[stage_name] = {
                "matched": has_record,
                "expected_token": spec["token"],
                "matching_records": len(matching),
            }
            if has_record:
                matched_transitions += 1

        orphan_5xx = [n for n in network if isinstance(n.get("status"), int) and n["status"] >= 500]
        denom = total_requests + len(asserted)
        score = (matched_requests + matched_transitions) / denom if denom else 0.0
        all_gating_matched = all(
            transition_detail.get(s, {}).get("matched", False) for s in asserted
        )
        execution_passed = result.get("execution_passed") is True
        passed = execution_passed and score >= 0.90 and not orphan_5xx and all_gating_matched

        pass_result = {
            "pass_dir": str(pass_dir),
            "run_tag": run_tag,
            "execution_passed": execution_passed,
            "total_api_requests": total_requests,
            "matched_requests": matched_requests,
            "asserted_transitions": asserted,
            "matched_transitions": matched_transitions,
            "transition_detail": transition_detail,
            "orphan_5xx": [n["url"] for n in orphan_5xx],
            "score": round(score, 3),
            "passed": passed,
            "evidence_receipt": receipt,
        }
        summary["passes"].append(pass_result)
        pass_num = result.get("pass_num", "x")
        (_proof_root() / f"reconciliation_pass{pass_num}.json").write_text(
            json.dumps(pass_result, indent=2), encoding="utf-8"
        )

    summary["all_passed"] = bool(summary["passes"]) and all(p["passed"] for p in summary["passes"])
    (_proof_root() / "reconciliation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def _verified_evidence_receipt(pass_dir: Path, sha: str) -> dict[str, Any] | None:
    if not _is_full_candidate_sha(sha):
        return None
    raw_root = _evidence_raw_root_from_path(pass_dir) or (_proof_root() / "raw").resolve()
    if _existing_symlink_under(raw_root, pass_dir) is not None:
        return None
    receipt_path = pass_dir / "evidence_receipt.json"
    if not receipt_path.is_file():
        return None
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if receipt.get("ok") is not True:
        return None
    if receipt.get("destination_owned") is not True:
        return None
    if not isinstance(receipt.get("transaction_id"), str) or not receipt.get("transaction_id"):
        return None
    pass_name = pass_dir.name
    try:
        pass_num = int(pass_name.removeprefix("pass"))
    except ValueError:
        return None
    manifest, manifest_digest, error = _load_and_verify_evidence_bundle(
        pass_dir,
        sha,
        expected_run_id=pass_dir.parent.name,
        expected_pass_num=pass_num,
        allow_destination_commit_files=True,
    )
    if error or manifest is None:
        return None
    if receipt.get("run_id") != manifest.get("run_id") or receipt.get("pass_num") != pass_num:
        return None
    if receipt.get("pass_id") != manifest.get("pass_id"):
        return None
    if receipt.get("campaign_id") != manifest.get("campaign_id"):
        return None
    if receipt.get("artifact_count") != len(manifest.get("files", [])):
        return None
    receipt_candidate_sha = receipt.get("candidate_sha")
    if not isinstance(receipt_candidate_sha, str) or receipt_candidate_sha != sha:
        return None
    receipt_canonical = _safe_absolute_evidence_path(receipt.get("canonical_path"))
    if receipt_canonical is None or receipt_canonical != pass_dir:
        return None
    if receipt.get("manifest_sha256") != manifest_digest:
        return None
    if receipt.get("inventory_sha256") != manifest.get("_computed_inventory_sha256"):
        return None
    commit_marker_path = pass_dir / "evidence_commit.json"
    if not commit_marker_path.is_file():
        return None
    try:
        commit_marker = json.loads(commit_marker_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(commit_marker, dict):
        return None
    if commit_marker.get("ok") is not True or commit_marker.get("authority") != "vps_destination_commit":
        return None
    if commit_marker.get("run_id") != manifest.get("run_id") or commit_marker.get("pass_num") != pass_num:
        return None
    if commit_marker.get("pass_id") != manifest.get("pass_id"):
        return None
    if commit_marker.get("campaign_id") != manifest.get("campaign_id"):
        return None
    if commit_marker.get("candidate_sha") != sha:
        return None
    if commit_marker.get("transaction_id") != receipt.get("transaction_id"):
        return None
    if commit_marker.get("manifest_sha256") != manifest_digest:
        return None
    if commit_marker.get("inventory_sha256") != manifest.get("_computed_inventory_sha256"):
        return None
    marker_canonical = _safe_absolute_evidence_path(commit_marker.get("canonical_path"))
    if marker_canonical is None or marker_canonical != pass_dir:
        return None
    commit_marker_digest = hashlib.sha256(commit_marker_path.read_bytes()).hexdigest()
    if receipt.get("commit_marker_sha256") != commit_marker_digest:
        return None
    expected_receipt_id = (
        "receipt-"
        + hashlib.sha256(
            (str(pass_dir) + manifest_digest + str(receipt.get("transaction_id")) + commit_marker_digest).encode()
        ).hexdigest()[:16]
    )
    if receipt.get("receipt_id") != expected_receipt_id:
        return None
    if receipt.get("receipt_authority") != "vps_destination_commit":
        return None
    campaign_id = str(manifest.get("campaign_id") or "")
    transaction_id = str(receipt.get("transaction_id") or "")
    expected_staging = pass_dir.parent.parent / ".incoming" / campaign_id / pass_dir.parent.name / pass_dir.name / transaction_id
    marker, marker_error = _load_and_verify_upload_marker(
        pass_dir,
        transaction_id=transaction_id,
        manifest_digest=manifest_digest,
        inventory_digest=manifest.get("_computed_inventory_sha256", ""),
        sha=sha,
        run_id=pass_dir.parent.name,
        pass_num=pass_num,
        campaign_id=campaign_id,
        staging_campaign_id=campaign_id,
        staging=expected_staging,
        canonical=pass_dir,
    )
    if marker_error or marker is None:
        return None
    return {
        "receipt_id": receipt.get("receipt_id"),
        "transaction_id": receipt.get("transaction_id"),
        "manifest_sha256": receipt.get("manifest_sha256"),
        "inventory_sha256": receipt.get("inventory_sha256"),
        "canonical_path": receipt.get("canonical_path"),
        "verified_at": receipt.get("verified_at"),
        "destination_owned": receipt.get("destination_owned"),
    }


def _read_state_records(sha: str) -> list[dict[str, Any]]:
    """Parse EVERY candidate state JSONL line into an individual record dict.

    Per-record parsing is what lets transition reconciliation prove that the run
    tag and the expected state token co-occur in the SAME record — a concatenated
    blob cannot make that distinction. Non-dict / unparseable lines are skipped.
    """
    records: list[dict[str, Any]] = []
    for p in _candidate_state_jsonls(sha):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                records.append(obj)
    return records


def _candidate_logs(runner: Runner) -> str:
    r = runner.run(
        ["docker", "logs", _CANDIDATE_CONTAINER, "--tail", "2000"],
        timeout=30,
        capture=True,
    )
    if r is None:
        return ""
    return (r.stdout or "") + (r.stderr or "")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _path_in_logs(url: str, logs: str) -> bool:
    if not url:
        return False
    from urllib.parse import urlparse

    path = urlparse(url).path
    return bool(path) and path in logs


# ─────────────────────────────────────────────────────────────────────────────
# teardown
# ─────────────────────────────────────────────────────────────────────────────
def teardown(runner: Runner, sha: str = "", run_id: str = "") -> dict[str, Any]:
    """Stop containers + runner, sweep credential homes, shred the run secret,
    restore serve. Candidate STATE is kept as evidence; credential material is NOT.

    The run-scoped dispatch secret is DESTROYED here (Amendment v1 clause 3 /
    order step 4): it existed only for this run's spool and must not persist.

    SEC-C1: teardown now also runs the RUN-LEVEL sweep over the run's targets dir,
    destroying every worker/verifier credential home and PROVING zero residue.
    ``stop_runner`` SIGTERMs the runner, which unwinds into its OWN teardown; this
    is the authoritative second sweep that also covers a runner that already died
    (crash / SIGKILL) and never got to clean up. ``homes_swept`` feeds the
    QualificationVerdict — residue makes teardown exit non-zero (closure bar §5).
    """
    if runner.dry_run:
        print(
            f"[dry-run] teardown: stop runner, sweep homes, shred secret, restore serve ({run_id})"
        )
        return {
            "torn_down": [],
            "run_secret_shredded": True,
            "serve_restored": True,
            "dry_run": True,
        }

    stopped = {}
    collector_stopped = {"stopped": True, "note": "no run_id"}
    evidence_guard: dict[str, Any] | None = None
    if run_id:
        evidence_guard = _wait_for_evidence_transaction_clear(
            runner,
            run_id=run_id,
            pass_num=1,
            candidate_sha=sha,
        )
        if not evidence_guard.get("ok"):
            return {
                "torn_down": [],
                "collector": {
                    "stopped": False,
                    "reason": "evidence publication active; teardown refused",
                },
                "evidence_guard": evidence_guard,
                "runner": {},
                "homes_swept": {"ok": False, "reason": "teardown refused during evidence publication"},
                "run_secret_shredded": False,
                "serve_restored": False,
            }
        else:
            collector_stopped = _stop_remote_collector_tree(runner, run_id=run_id, pass_num=1)
        stopped = stop_runner(runner, sha, run_id)
        # Give the runner's signal-driven teardown a moment to unwind and sweep
        # its own homes before we run the authoritative sweep below.
        _wait_for_runner_exit(sha, run_id)
    _remove_container_and_wait(runner, _CANDIDATE_NGINX_CONTAINER)
    _remove_container_and_wait(runner, _CANDIDATE_CONTAINER)

    homes_swept = _sweep_run_homes(sha, run_id) if run_id else _no_run_ref_proof()

    secret_shredded = _shred_run_secret(runner, sha) if sha else True
    serve_restore_raw = _restore_tailscale_serve(runner, sha=sha)
    serve_restore = (
        serve_restore_raw
        if isinstance(serve_restore_raw, dict)
        else {
            "ok": False,
            "reason": "tailscale serve restore did not return structured proof",
            "unexpected_return_type": type(serve_restore_raw).__name__,
        }
    )
    return {
        "torn_down": [_CANDIDATE_CONTAINER, _CANDIDATE_NGINX_CONTAINER],
        "collector": collector_stopped,
        "evidence_guard": evidence_guard,
        "runner": stopped,
        "homes_swept": homes_swept,
        "run_secret_shredded": secret_shredded,
        "serve_restored": bool(serve_restore.get("ok")),
        "serve_restore": serve_restore,
    }


def _wait_for_runner_exit(sha: str, run_id: str, timeout_s: float = 8.0) -> None:
    """Best-effort wait for the SIGTERM'd runner to finish its own teardown.

    Polls the recorded pid file's process; returns as soon as it is gone or the
    timeout elapses. The authoritative home sweep runs regardless — this only
    lets the runner's own idempotent sweep go first so the two never race a
    half-deleted tree.
    """
    pid_file = _spool_root(sha, run_id).parent / f"runner_{run_id}.pid"
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip()) if pid_file.exists() else 0
    except (OSError, ValueError):
        pid = 0
    if pid <= 0:
        return
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, OSError):
            return  # gone
        time.sleep(0.25)


def _sweep_run_homes(sha: str, run_id: str) -> dict[str, Any]:
    """Authoritative run-level credential-home sweep for teardown (SEC-C1).

    Destroys every worker/verifier home under the run's targets dir and proves
    zero residue. Returns the RunSweepResult dict; ``ok`` gates the verdict.
    """
    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.run_teardown import sweep_run

    run_root = str(_targets_dir(sha, run_id))
    # The run's protected git refs (refs/umh/verified + refs/umh/composed) live
    # in the FIXTURE repo, not the run root. Passing the binding here is what
    # makes ref cleanup reachable in production at all — without it
    # release_composed_refs would ship as an unreachable helper.
    res = sweep_run(
        run_root,
        repo_root=str(_targets_dir(sha, run_id) / "fixture"),
        candidate=sha,
        run_id=run_id,
    )
    return res.to_dict()


def _no_run_ref_proof() -> dict[str, Any]:
    """Positive protected-ref proof for teardown calls without a run binding."""
    namespaces = ["refs/umh", "refs/candidates", "refs/wave2"]
    cmd = [
        "git",
        "for-each-ref",
        "--format=%(refname) %(objectname)",
        *namespaces,
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(_WORKTREE),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "ok": True,
            "note": "no run_id",
            "zero_ref_residue": False,
            "ref_enumeration_executed": False,
            "ref_namespaces_checked": namespaces,
            "ref_inventory": [],
            "ref_residue": ["protected-ref-enumeration:<failed>"],
            "quarantined_refs": ["protected-ref-enumeration:<failed>"],
            "unexpected_ref_count": 1,
            "errors": [proc.stderr.strip() or "protected-ref enumeration failed"],
        }
    inventory = [line for line in proc.stdout.splitlines() if line.strip()]
    return {
        "ok": True,
        "note": "no run_id",
        "zero_ref_residue": not inventory,
        "ref_enumeration_executed": True,
        "ref_namespaces_checked": namespaces,
        "ref_inventory": inventory,
        "ref_residue": inventory,
        "quarantined_refs": inventory,
        "unexpected_ref_count": len(inventory),
        "refs_deleted": [],
        "errors": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# manifest
# ─────────────────────────────────────────────────────────────────────────────
def write_manifest(runner: Runner, sha: str) -> dict[str, Any]:
    """manifest.json: sha, image id, dist index sha256 + asset list, artifacts."""
    run_dir = _proof_root()
    image_id = _candidate_image_id(runner)
    dist_web = _WORKTREE / "cockpit" / "dist-web"
    index = dist_web / "index.html"
    assets_dir = dist_web / "assets"

    manifest: dict[str, Any] = {
        "candidate_sha": sha,
        "container_image_id": image_id,
        "generated_at": _utc_now(),
        "heavyweight_artifacts_not_committed": [
            str(dist_web),
            str(_state_dir(sha).parent),
            f"{run_dir}/raw (per-pass screenshots + DOM snapshots)",
        ],
    }
    if runner.dry_run:
        print(f"[dry-run] write manifest → {run_dir}/manifest.json (index sha256 + asset list)")
        return {"dry_run": True}

    if index.exists():
        manifest["dist_index_sha256"] = _sha256_file(index)
    if assets_dir.exists():
        manifest["asset_files"] = sorted(p.name for p in assets_dir.iterdir() if p.is_file())

    # ONE-WAY EVIDENCE FINALIZATION (R1 / SEC-C1).
    #
    # The previous order hashed every artifact, THEN rewrote those same files
    # with a redaction pass, THEN wrote the manifest — so the recorded hashes
    # described bytes that no longer existed and could never re-verify. Hashing
    # now happens LAST, inside the pipeline, after redaction has finished and a
    # second scan has confirmed no secret survived. No file is rewritten after
    # its hash is taken.
    #
    # The pipeline also replaces the withdrawn bare-64-hex redaction rule, which
    # destroyed the legitimate artifact/package/scope hashes and image IDs the
    # manifest's integrity claim is built on.
    # evidence_finalization is Wave-2-only code that lives in the candidate
    # worktree, NOT in the stale /opt/OS main checkout (which is frozen at Wave
    # 0). Import it from _WORKTREE like every other attempts.* import in this
    # dispatcher (seed-fixture/start-runner/reconcile sites) — using _ROOT here
    # raised ModuleNotFoundError and aborted deploy-candidate before it could
    # write its manifest.
    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.evidence_finalization import finalize_evidence

    exact_values: list[str] = []
    secret_path = _run_secret_path(sha)
    if secret_path.exists():
        try:
            exact_values.append(secret_path.read_text(encoding="utf-8").strip())
        except OSError as exc:  # never fail finalization on an unreadable secret
            print(f"[manifest] run secret unreadable for exact-value redaction: {exc}")

    finalized = finalize_evidence(run_dir, exact_values=exact_values, extra_manifest=manifest)
    manifest["file_count"] = len(finalized.files)
    manifest["manifest_sha256"] = finalized.manifest_sha256
    manifest["redacted_files"] = finalized.redacted_files
    manifest["secret_scan_clean"] = finalized.secret_scan_clean
    return manifest


# ─────────────────────────────────────────────────────────────────────────────
# Wave 2 subcommands: seed-fixture, start-runner, inject-failure
# ─────────────────────────────────────────────────────────────────────────────
def seed_fixture(runner: Runner, sha: str, run_id: str, variant: str) -> dict[str, Any]:
    """Generate the fixture app into the run's targets dir; print base sha.

    The fixture generator is SPEC-ONLY (seeds the working app + the OBJECTIVE.md
    contract, never the solution). Each run gets a fresh targets dir so passes
    never bleed. Returns the fixture base commit sha for exact binding.
    """
    dest = _targets_dir(sha, run_id) / "fixture"
    gen = _WORKTREE / "infra" / "fixture" / "make_fixture_app.py"
    r = runner.run(
        [sys.executable, str(gen), "--dest", str(dest), "--variant", variant], timeout=60
    )
    fixture_base_sha = ""
    if r is not None and getattr(r, "stdout", ""):
        try:
            fixture_base_sha = json.loads(r.stdout).get("fixture_base_sha", "")
        except (ValueError, AttributeError):
            fixture_base_sha = ""
    return {
        "dest": str(dest),
        "variant": variant,
        "run_id": run_id,
        "fixture_base_sha": fixture_base_sha,
    }


# Operational-readiness markers the runner emits AFTER its control-plane driver
# construction resolves. "runner up:" is deliberately NOT here: the runner emits
# that BEFORE building the driver, so accepting it returned started=True for a
# run whose control plane never came up (finding B1).
RUNNER_READY_MARKERS = ("control-plane driver up: ", "runner ready worker-only: ")


def runner_readiness_announced(log_body: str, pid: int) -> bool:
    """True if *log_body* shows THIS pid reaching operational readiness.

    Module-level and named so the regression tests exercise THIS function rather
    than a copy of its logic. Independent review (R9) defeated an earlier test by
    gutting the inline loop to `if True:` while leaving every asserted source
    string in place — all 12 tests still passed. A test that replays a
    re-implementation cannot see that; a test that calls this can.

    The pid tag keeps its TRAILING SPACE deliberately: without it `pid=4242`
    prefix-matches `pid=42424`. Every occurrence of each marker is scanned, so a
    stale line from a previous launch followed by ours still succeeds, while a
    log containing only another pid's readiness does not.
    """
    pid_tag = f"pid={pid} "
    for marker in RUNNER_READY_MARKERS:
        idx = log_body.find(marker)
        while idx != -1:
            if log_body[idx + len(marker) :].startswith(pid_tag):
                return True
            idx = log_body.find(marker, idx + 1)
    return False


def start_runner(runner: Runner, sha: str, run_id: str, max_iterations: int) -> dict[str, Any]:
    """Start the run-scoped host attempt runner over this run's signed spool.

    The runner verifies ENFORCED host isolation (bwrap) is available and refuses
    to run workers unconfined (Amendment v1 clause 4). It reads the run-scoped
    dispatch secret from the 0600 file (never a CLI arg, never logged). It is a
    RUN-SCOPED component — started here, stopped at teardown — NOT a persistent
    supervisor (that is Wave 3).

    On the VPS host the runner resolves the selected provider's credential only
    through the governed model-executor boundary. This launcher verifies
    isolation + spins the loop; it never logs or passes credentials on argv.
    """
    secret_path = _mint_run_secret(runner, sha)
    spool_root = _spool_root(sha, run_id)
    runner.run(["mkdir", "-p", str(spool_root)], timeout=20)

    # Preflight isolation up-front (fail closed BEFORE any dispatch).
    pre = runner.run(
        [
            sys.executable,
            str(_WORKTREE / "scripts" / "wave2_attempt_runner.py"),
            "--spool-root",
            str(spool_root),
            "--preflight-only",
        ],
        timeout=60,
    )
    # FAIL CLOSED on every signal, not just stdout. A preflight may prove
    # confinement ONLY when it ran to completion, exited with the success code
    # its own contract defines, said nothing on stderr, and emitted an
    # affirmative BOOLEAN verdict.
    #
    # Reading stdout alone was a fail-open on the Amendment v1 clause 4 control:
    # `wave2_attempt_runner.py --preflight-only` returns `0 if (prim and ok)
    # else 2`, so a nonzero code is the preflight itself saying "do not trust
    # this" — yet a process that PRINTED an affirmative verdict and then failed
    # (nonzero exit, or a bwrap diagnostic on stderr) was accepted, and the
    # worker was launched unconfined. The real success path is verified silent:
    # rc=0, affirmative JSON on stdout, exactly zero bytes of stderr — so any
    # stderr is a contradiction, not a warning channel.
    #
    # `isolation_ok` must be the literal `True`, never merely truthy: a string
    # or number in that field is malformed evidence, not proof of confinement.
    isolation_ok = False
    isolation_detail = "preflight produced no result (CPU gate or launch failure)"
    if pre is not None:
        rc = getattr(pre, "returncode", None)
        # `or ""` alone only rescues FALSY non-strings (None/0/False); a TRUTHY
        # non-string (an int, a bytes object from a text=False caller) sails past
        # it and crashes the launcher on `.strip()`. Coerce on TYPE, not on
        # truthiness, so a duck-typed result refuses diagnosably instead of
        # raising a traceback the operator has to decode (finding R15-1).
        _raw_stdout = getattr(pre, "stdout", "")
        stdout = _raw_stdout if isinstance(_raw_stdout, str) else ""
        # stderr coercion is NOT symmetric with stdout, and the asymmetry is the
        # point. Blanking a non-str stderr DISCARDS a diagnostic and lets the
        # contradiction check pass — the exact fail-OPEN this block exists to
        # prevent (a first attempt at this coercion did precisely that: a
        # `bytes` stderr from a text=False caller was silently dropped and a
        # worker launched, finding R16 F-1). Empty-ish values mean "silent";
        # ANYTHING else carries content and is therefore a contradiction, so it
        # is rendered rather than discarded.
        _raw_stderr = getattr(pre, "stderr", "")
        if isinstance(_raw_stderr, str):
            stderr = _raw_stderr.strip()
        elif isinstance(_raw_stderr, (bytes, bytearray)):
            # Decode-then-strip, so whitespace-only bytes count as SILENCE exactly
            # as whitespace-only str does. Rendering them with repr() instead would
            # make b"  " a contradiction while "  " is not — an inconsistency the
            # string rule already settled.
            stderr = _raw_stderr.decode("utf-8", "replace").strip()
        elif _raw_stderr is None:
            stderr = ""
        else:
            # Anything else (int, list, arbitrary object) is not a recognised
            # stream, so it is a contradiction by CONSTRUCTION — never by the
            # content of its repr(). Deriving the verdict from `repr()` alone was
            # a fail-OPEN: an object whose `__repr__` returns "" produced an empty
            # `stderr`, the contradiction check saw silence, and a worker launched
            # (isolation_ok=True, popen=1). The type prefix guarantees a non-empty,
            # non-whitespace marker no matter what the object renders as.
            stderr = f"<non-stream stderr {type(_raw_stderr).__name__}> {_raw_stderr!r}"
        if rc != 0:
            isolation_detail = f"preflight exited {rc} — isolation not proven"
        elif stderr:
            isolation_detail = f"preflight wrote to stderr — isolation not proven: {stderr[:200]!r}"
        elif not stdout.strip():
            isolation_detail = "preflight emitted no evidence on stdout"
        else:
            try:
                parsed = json.loads(stdout)
            except ValueError:
                isolation_detail = "preflight evidence was not parseable JSON"
            else:
                if not isinstance(parsed, dict):
                    isolation_detail = "preflight evidence was not a JSON object"
                elif parsed.get("isolation_ok") is not True:
                    isolation_detail = (
                        f"preflight did not affirm isolation: {parsed.get('detail', parsed)!r}"
                    )
                else:
                    isolation_ok = True
                    isolation_detail = str(parsed.get("detail", "isolation verified"))
    if not isolation_ok and not runner.dry_run:
        return {
            "started": False,
            "isolation_ok": False,
            "reason": "enforced host isolation (bwrap) preflight failed — refusing "
            f"to run workers unconfined (Amendment v1 clause 4): {isolation_detail}",
        }

    if runner.dry_run:
        print(
            f"[dry-run] start host attempt runner (detached): spool={spool_root} "
            f"secret-file={secret_path} (value never printed) max_iterations={max_iterations}"
        )
        # Dry-run assembles the command only — it does NOT run the bwrap preflight,
        # so it must NEVER claim isolation was confirmed (review C3). isolation_ok
        # is None ("not verified in dry-run"), never True. A real run resolves it.
        return {
            "started": True,
            "dry_run": True,
            "spool_root": str(spool_root),
            "isolation_ok": None,
        }

    # Launch detached; the runner sources the secret from the 0600 file into its
    # own env var so the value never appears in this process's argv.
    #
    # The runner ALSO runs the host control-plane loop (turning ACTIVE grants in
    # the shared candidate ledger into signed dispatch envelopes). For that it
    # needs UMH_STATE_DIR pointed at the SAME host state dir the candidate
    # container mounts (so it reads the exact grants/packets the cockpit
    # authorization wrote), plus the fixture repo it leases worktrees from and
    # the targets dir holding the .inject_failure marker. The runner is a HOST
    # process (bwrap hides /opt/OS from the worker); UMH_STATE_DIR here scopes
    # the runner's OWN store reads to the candidate state, never /opt/OS.
    # Verify the secret file BEFORE building the launch line (SEC-W5). If
    # `$(cat ...)` fails the child would receive an empty UMH_W2_DISPATCH_SECRET;
    # the runner does fail closed on that, but the operator would see only a
    # generic "runner did not come up" instead of the real cause.
    try:
        if not secret_path.is_file() or not secret_path.read_text(encoding="utf-8").strip():
            return {
                "started": False,
                "isolation_ok": True,
                "reason": f"run secret missing or empty at {secret_path} — refusing to launch",
            }
    except OSError as exc:
        return {
            "started": False,
            "isolation_ok": True,
            "reason": f"run secret unreadable at {secret_path}: {exc}",
        }

    launch_log = spool_root.parent / f"runner_{run_id}.log"
    targets_dir = _targets_dir(sha, run_id)
    fixture_repo = targets_dir / "fixture"
    leases_dir = targets_dir / "leases"
    host_state_dir = _state_dir(sha)
    # `env VAR=value -- cmd` (NOT `exec VAR=value cmd`, which is invalid shell:
    # exec rejects assignment prefixes and bash then reports the whole assignment
    # as "not found" — echoing the SECRET VALUE into the launch log). With env the
    # value is placed in the child's environment by the shell and never appears in
    # this process's argv, nor in an error message if the interpreter is missing.
    inner_cmd = (
        f"env UMH_W2_DISPATCH_SECRET=$(cat {shlex.quote(str(secret_path))}) "
        f"UMH_STATE_DIR={shlex.quote(str(host_state_dir))} "
        # Arms the runner's PRE-QUOTA graph-shape gate. The runner refuses a
        # wrong-shaped graph before writing any dispatch envelope, so a
        # planning defect costs zero worker invocations.
        f"UMH_WORKSPACE_LANES={shlex.quote(_declared_lanes_json())} "
        f"{shlex.quote(sys.executable)} "
        f"{shlex.quote(str(_WORKTREE / 'scripts' / 'wave2_attempt_runner.py'))} "
        f"--spool-root {shlex.quote(str(spool_root))} "
        f"--fixture-repo {shlex.quote(str(fixture_repo))} "
        f"--targets-dir {shlex.quote(str(targets_dir))} "
        f"--leases-dir {shlex.quote(str(leases_dir))} "
        f"--max-iterations {int(max_iterations)} --poll-seconds 2.0"
    )
    proc = subprocess.Popen(  # noqa: S603 — run-scoped host launcher, gated by isolation preflight
        ["bash", "-c", f"exec {inner_cmd} >> {shlex.quote(str(launch_log))} 2>&1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    (spool_root.parent / f"runner_{run_id}.pid").write_text(str(proc.pid), encoding="utf-8")

    # Popen succeeding only proves bash forked — NOT that the runner is alive
    # (a bad launch line dies instantly and would still report started=True).
    # Wait for the runner to announce itself in its log, and fail closed if the
    # process is gone. Never report a dead runner as started.
    alive = False
    announced = False
    deadline = time.time() + 30.0
    while time.time() < deadline:
        time.sleep(1.0)
        alive = proc.poll() is None
        if launch_log.exists():
            try:
                head = launch_log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                head = ""
            announced = runner_readiness_announced(head, proc.pid)
            if announced:
                break
        if not alive:
            break
    if not (alive and announced):
        tail = ""
        if launch_log.exists():
            try:
                # Redact before surfacing ANY launch output (a failed launch line
                # can carry the run secret — see the env/exec note above).
                tail = _SECRET_REDACT_RE.sub(
                    "<redacted>", launch_log.read_text(encoding="utf-8", errors="replace")
                )[-400:]
            except OSError:
                tail = ""
        return {
            "started": False,
            "isolation_ok": True,
            "reason": "runner did not come up (process exited or never announced)",
            "alive": alive,
            "announced": announced,
            "launch_log_tail": tail,
            "spool_root": str(spool_root),
        }

    return {
        "started": True,
        "isolation_ok": True,
        "spool_root": str(spool_root),
        "runner_pid": proc.pid,
        "launch_log": str(launch_log),
    }


def stop_runner(runner: Runner, sha: str, run_id: str) -> dict[str, Any]:
    """Stop the run-scoped host attempt runner (by recorded pid)."""
    pid_file = _spool_root(sha, run_id).parent / f"runner_{run_id}.pid"
    if runner.dry_run:
        print(f"[dry-run] stop runner via {pid_file}")
        return {"stopped": True, "dry_run": True}
    if not pid_file.exists():
        return {"stopped": True, "note": "no runner pid recorded"}
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink()
        return {"stopped": True, "pid": pid}
    except (ValueError, ProcessLookupError, OSError) as exc:
        return {"stopped": False, "note": str(exc)}


def _wait_for_bindable_grant(
    runner: Runner,
    *,
    sha: str,
    run_id: str,
    timeout_s: float = 300.0,
    interval_s: float = 3.0,
) -> tuple[Any, str]:
    """Block until THIS run's grant is durable + bindable, or refuse (fail-closed).

    `_wait_collector_authorization` returns when the collector REACHES stage 15,
    NOT when the grant its journey causes is durable on disk (observed ~14s race:
    run 20260805T070430Z-p1). So poll the REAL binding consumer —
    `_capture_execution_binding`, the exact function `write_scenario_map` uses —
    until it binds. Reusing the consumer (never re-implementing its predicate)
    means this wait can never accept something the binding gate would reject:
    durable AND unique AND ACTIVE AND exact-correlation are all proven by the
    gate itself, not by a copy of its rules. This is the identical proven pattern
    the qualified failure/recovery driver uses; sharing the one authority
    function here keeps the green and failure/recovery paths on ONE binding
    derivation (no copy/paste divergence).

    Returns (binding, "") on success, or (None, reason) on timeout — fail-closed,
    never retrying past the bound. In dry-run there is no state to read, so it
    reports a planned wait and returns (None, "dry-run") without blocking; the
    dry-run caller does not gate on a real binding.
    """
    if runner.dry_run:
        print(f"[dry-run] wait for run {run_id} grant to become durable + bindable")
        return None, "dry-run"
    deadline = time.monotonic() + timeout_s
    last = "no attempt made"
    while time.monotonic() < deadline:
        records = _read_state_records(sha)
        binding, err = _capture_execution_binding(records, sha=sha, run_id=run_id)
        if binding is not None:
            return binding, ""
        last = err or "unknown refusal"
        time.sleep(interval_s)
    return None, f"grant not bindable within {timeout_s:.0f}s: {last}"


def write_scenario_map(runner: Runner, sha: str, run_id: str) -> dict[str, Any]:
    """Capture the run binding + resolve + persist the run's scenario map.

    This is the field consumer of the scenario-map capability (finding C-3). It
    CAPTURES the run's execution binding from the REAL grant produced by THIS
    journey (the grant whose correlation_id is this run's ``w2-<run_id>``),
    persists it as ``execution_binding.json`` (identifiers only), then resolves
    each semantic role to its exact canonical ``wp-*`` id through plan-node
    lineage and writes a binding-bound ``scenario_map.json``. WITHOUT this,
    ``inject-failure`` reads no binding and the failure-qualification pass is
    unrunnable (exit 3 forever).

    The binding is NEVER "the only ACTIVE grant" — it is the grant this run's
    journey produced, resolved by exact correlation. Must run AFTER the plan
    materializes its WorkPackets and the execution authorization is granted (i.e.
    after the collector drives approval + activation) and BEFORE inject-failure.
    """
    targets = _targets_dir(sha, run_id)
    if runner.dry_run:
        print(f"[dry-run] capture binding + resolve + write scenario map for run {run_id}")
        return {"written": True, "dry_run": True, "run_id": run_id}

    # Import the worktree substrate (not the stale /opt/OS one) — the candidate
    # source lives in this worktree, and _WORKTREE is where its modules resolve.
    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.field_scenario_map import (
        ScenarioMapError,
        build_from_records,
        write_execution_binding,
    )
    from substrate.execution.attempts.field_scenario_map import (
        write_scenario_map as _persist,
    )

    records = _read_state_records(sha)
    # Capture the EXACT binding from the grant THIS run's journey produced —
    # matched by exact correlation, then read for its full identity. Never
    # inferred from "the only active grant".
    binding, cap_err = _capture_execution_binding(records, sha=sha, run_id=run_id)
    if binding is None:
        return {
            "written": False,
            "run_id": run_id,
            "error": cap_err,
            "remediation": "drive the plan approval + execution authorization for THIS run before writing the map",
        }
    write_execution_binding(targets, binding)
    try:
        payload = build_from_records(records, binding=binding)
    except ScenarioMapError as exc:
        # FAIL CLOSED: no map is written, so inject-failure will refuse to arm.
        return {
            "written": False,
            "run_id": run_id,
            "grant_id": binding.grant_id,
            "error": str(exc),
            "remediation": "ensure the plan materialized its WorkPackets before writing the map",
        }
    path = _persist(targets, payload)
    return {
        "written": True,
        "run_id": run_id,
        "path": str(path),
        "grant_id": binding.grant_id,
        "plan_record_id": payload.get("plan_record_id", ""),
        "plan_version": payload.get("plan_version", 0),
        "backend_task_id": payload.get("backend_task_id", ""),
    }


def inject_failure(runner: Runner, sha: str, run_id: str, variant: str) -> dict[str, Any]:
    """Arm a genuine worker-failure variant for the failure-qualification pass.

    ``tools-revoked-a`` is a DISPATCH-TIME tool policy (A's attempt runs with
    Edit/Write revoked → the real worker genuinely cannot commit → validation
    genuinely fails → C stays blocked → no false Proof → retry from the HUD mints
    A2 without revocation → the graph continues). The fixture itself is
    identical; the failure is a real capability revocation, not a poisoned app.

    The variant is written to ``<targets>/.inject_failure`` and read by
    ``substrate.execution.attempts.field_failure_policy.disallowed_tools_for``
    when the field-run dispatch path builds each envelope — so the marker is
    ACTUALLY consumed (it revokes Edit/Write on A's first attempt), never a dead
    write. A unit test pins that the marker changes the computed policy.
    """
    targets = _targets_dir(sha, run_id)
    marker = targets / ".inject_failure"
    if runner.dry_run:
        print(f"[dry-run] arm failure variant {variant!r} → {marker}")
        return {"armed": True, "variant": variant, "dry_run": True}
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(variant, encoding="utf-8")

    # FAIL CLOSED (findings C2 + C-3): a revoking variant is only valid when the
    # scenario map validates against THIS run's CAPTURED execution binding — the
    # ONE canonical grant matching every binding identifier (grant_id,
    # decision_ref, plan id/version, tenant/principal/membership,
    # conversation/correlation), not stale, ref/grant_id untampered, every role
    # resolving to a real materialized packet inside that grant's frontier. An
    # armed injection that cannot target a real authorized task must never be
    # mistaken for a recovered one. The binding is read from the
    # ``execution_binding.json`` that ``write-scenario-map`` captured for THIS run.
    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.field_failure_policy import (
        arming_is_valid_for_run,
        target_task_id,
    )
    from substrate.execution.attempts.field_scenario_map import read_execution_binding

    if read_execution_binding(targets) is None:
        return {
            "armed": False,
            "variant": variant,
            "marker": str(marker),
            "invalid_reason": "no execution_binding.json for this run — binding not captured",
            "remediation": (
                "run `wave2_field_dispatch.py write-scenario-map` for THIS run AFTER "
                "the execution authorization is granted, then re-arm"
            ),
        }
    records = _read_state_records(sha)
    ok, reason = arming_is_valid_for_run(str(targets), records=records)
    if not ok:
        return {
            "armed": False,
            "variant": variant,
            "marker": str(marker),
            "invalid_reason": reason,
            "remediation": (
                "run `wave2_field_dispatch.py write-scenario-map` AFTER the plan "
                "materializes its WorkPackets and the grant is ACTIVE, then re-arm"
            ),
        }
    return {
        "armed": True,
        "variant": variant,
        "marker": str(marker),
        "target_task_id": target_task_id(str(targets)),
        "arming": reason,
    }


def pause_before_dispatch(runner: Runner, sha: str, run_id: str) -> dict[str, Any]:
    """Arm the same-run ADMISSION pause so the failure policy can be bound.

    The window this opens did not previously exist: the control plane turned a
    freshly-ACTIVE grant into signed dispatches on the same cycle, so there was
    no point at which `write-scenario-map` + `inject-failure` could run against
    THIS run's grant (cross-run binding reuse is correctly refused, so preparing
    the binding in an earlier pass is not available either).

    Armed AFTER the grant + `execution_binding.json` are durable and BEFORE any
    Task is admitted. While armed, scheduler admission is suppressed — zero
    Attempts, leases, assignments, envelopes, or quota — while result draining
    for already-dispatched work continues untouched.
    """
    targets = _targets_dir(sha, run_id)
    if runner.dry_run:
        print(f"[dry-run] arm admission pause → {targets}/.pause_before_dispatch")
        return {"paused": True, "dry_run": True}

    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.field_failure_policy import (
        arm_pause_before_dispatch,
        pause_state,
    )
    from substrate.execution.attempts.field_scenario_map import read_execution_binding

    binding = read_execution_binding(targets)
    if binding is None:
        return {
            "paused": False,
            "refused": "no execution_binding.json for this run — binding not captured",
            "remediation": (
                "run `wave2_field_dispatch.py write-scenario-map` for THIS run AFTER "
                "the execution authorization is granted, then arm the pause"
            ),
        }
    marker = arm_pause_before_dispatch(str(targets))
    paused, reason = pause_state(str(targets))
    return {
        "paused": paused,
        "marker": str(marker),
        "reason": reason,
        "run_id": binding.run_id,
        "grant_id": binding.grant_id,
        "decision_ref": binding.decision_ref,
        "candidate_sha": binding.candidate_sha,
    }


def resume_after_pause(runner: Runner, sha: str, run_id: str) -> dict[str, Any]:
    """Release THIS run's admission pause exactly once; normal scheduling resumes.

    Refuses a second release, a foreign/malformed marker, and an unreadable
    state — a duplicate `resume` must never look like it re-authorized a run
    that is already running.
    """
    targets = _targets_dir(sha, run_id)
    if runner.dry_run:
        print(f"[dry-run] release admission pause ← {targets}/.pause_before_dispatch")
        return {"released": True, "dry_run": True}

    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.field_failure_policy import (
        arming_is_valid_for_run,
        release_pause_before_dispatch,
    )

    # Releasing before the failure policy is armed would waste the whole window
    # the pause exists to create: the run would proceed unarmed and the failure
    # pass would silently run clean. Report it rather than releasing blindly.
    records = _read_state_records(sha)
    arm_ok, arm_reason = arming_is_valid_for_run(str(targets), records=records)

    released, detail = release_pause_before_dispatch(str(targets))
    return {
        "released": released,
        "detail": detail,
        "arming_valid": arm_ok,
        "arming": arm_reason,
    }


def _capture_execution_binding(
    records: list[dict[str, Any]], *, sha: str, run_id: str
) -> tuple[Any, str]:
    """Capture THIS run's execution binding from the grant its journey produced.

    The run's binding is NOT "the only ACTIVE grant" — it is the grant this run's
    journey created, identified by an EXACT match on the grant's CANONICAL
    ``correlation_id`` (the collector stamps ``w2-<run_id>`` as the correlation of
    THIS journey — see wave2_field_collector). ``correlation_id`` is part of the
    ``ExecutionAuthorizationGrant`` identity contract; ``run_tag`` is NOT, so there
    is no ``run_tag``/base-pass escape here — the production field path selects only
    the exact collector-observed correlation. The grant is then read for its FULL
    identity (grant_id, decision_ref, plan id/version, tenant/principal/membership,
    conversation/correlation). Returns ``(ExecutionBinding, "")`` on success, or
    ``(None, reason)`` fail-closed when zero or more than one grant carries this
    run's exact correlation, or the grant is not ACTIVE.

    The exact-correlation match is what makes a legitimate ACTIVE grant left by a
    prior or parallel run irrelevant: it carries a different correlation.
    """
    # field_scenario_map is Wave-2-only (candidate worktree, not stale /opt/OS
    # main). Guard the import with _WORKTREE explicitly rather than relying on a
    # prior call having inserted it — same defect class as write_manifest.
    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.field_scenario_map import ExecutionBinding

    # The collector's correlation for this journey: w2-<run_id> (run_id already
    # carries the -pN pass suffix). Match ONLY the canonical correlation_id — no
    # run_tag field, no base-tag (pre "-p") fallback.
    wanted_corr = f"w2-{run_id}" if run_id else ""
    grants = [
        g
        for g in records
        if g.get("grant_id")
        and "task_frontier" in g
        and wanted_corr
        and str(g.get("correlation_id", "")) == wanted_corr
    ]
    if len(grants) != 1:
        return None, (
            f"{len(grants)} execution-authorization grants carry exact correlation_id "
            f"{wanted_corr!r} (need exactly 1) — the run's own grant is not "
            f"uniquely identifiable"
        )
    g = grants[0]
    status = str(g.get("status", "")).lower()
    if status != "active":
        return None, (
            f"grant {g.get('grant_id')!r} for run {run_id!r} status is {status!r}, "
            f"not ACTIVE — the authorization is not live"
        )
    binding = ExecutionBinding(
        run_id=run_id,
        candidate_sha=sha,
        plan_record_id=str(g.get("plan_record_id", "")),
        plan_version=int(g.get("plan_version", 0)),
        grant_id=str(g.get("grant_id", "")),
        decision_ref=str(g.get("decision_ref", "")),
        tenant_id=str(g.get("tenant_id", "")),
        principal_id=str(g.get("principal_id", "")),
        membership_id=str(g.get("membership_id", "")),
        conversation_id=str(g.get("conversation_id", "")),
        correlation_id=str(g.get("correlation_id", "")),
    )
    return binding, ""


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def _candidate_sha(explicit: str) -> str:
    if explicit:
        return explicit
    try:
        r = subprocess.run(
            ["git", "-C", str(_WORKTREE), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return (r.stdout or "").strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wave 2 field-qualification dispatcher (VPS)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands, execute nothing")
    parser.add_argument("--sha", default="", help="Candidate commit sha (default: worktree HEAD)")
    parser.add_argument("--scenario", default="full", choices=["full", "smoke"])
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--run-id", default="", help="Run id (seed-fixture/start-runner/teardown)")
    parser.add_argument(
        "--variant",
        default="clean",
        choices=["clean", "tools-revoked-backend", "tools-revoked-a"],
        help="fixture/failure variant (seed-fixture, inject-failure)",
    )
    parser.add_argument(
        "--max-iterations", type=int, default=0, help="host runner iterations (0 = until stopped)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in (
        "preflight",
        "deploy-candidate",
        "seed-fixture",
        "start-runner",
        "smoke",
        "run",
        "write-scenario-map",
        "pause-before-dispatch",
        "inject-failure",
        "activation-rehearsal",
        "collector-teardown-rehearsal",
        "resume",
        "reconcile",
        "teardown",
    ):
        sub.add_parser(name)
    args = parser.parse_args(argv)

    runner = Runner(dry_run=args.dry_run)
    sha = _candidate_sha(args.sha)
    run_id = args.run_id or _run_id_default()

    # Resolve the network + origin globals now (a real command needs them); this
    # is where a resolution failure legitimately fails loudly — never at import.
    _resolve_env()

    if args.cmd == "preflight":
        _ensure_mesh_secrets()
        out = preflight(runner, sha)
    elif args.cmd == "deploy-candidate":
        out = deploy_candidate(runner, sha)
        write_manifest(runner, sha)
    elif args.cmd == "seed-fixture":
        out = seed_fixture(runner, sha, run_id, args.variant)
    elif args.cmd == "start-runner":
        out = start_runner(runner, sha, run_id, args.max_iterations)
    elif args.cmd == "smoke":
        _ensure_mesh_secrets()
        _load_serve_snapshot_path(sha)
        _install_crash_handlers(runner, sha)
        out = run_passes(runner, sha=sha, scenario="smoke", passes=1)
    elif args.cmd == "run":
        _ensure_mesh_secrets()
        _load_serve_snapshot_path(sha)
        _install_crash_handlers(runner, sha)
        out = run_passes(runner, sha=sha, scenario=args.scenario, passes=args.passes)
    elif args.cmd == "write-scenario-map":
        out = write_scenario_map(runner, sha, run_id)
    elif args.cmd == "pause-before-dispatch":
        out = pause_before_dispatch(runner, sha, run_id)
    elif args.cmd == "inject-failure":
        out = inject_failure(runner, sha, run_id, args.variant)
    elif args.cmd == "activation-rehearsal":
        out = activation_rehearsal(runner, sha, iterations=3)
    elif args.cmd == "collector-teardown-rehearsal":
        _ensure_mesh_secrets()
        out = collector_teardown_rehearsal(runner, sha, iterations=3)
    elif args.cmd == "resume":
        out = resume_after_pause(runner, sha, run_id)
    elif args.cmd == "reconcile":
        out = reconcile(runner, sha)
    elif args.cmd == "teardown":
        _load_serve_snapshot_path(sha)
        out = teardown(runner, sha=sha, run_id=args.run_id)
    else:  # pragma: no cover — argparse enforces
        parser.error(f"unknown command {args.cmd}")
        return 2

    # THE ONE TYPED VERDICT (C-5). Computed once, embedded in the report AND used
    # for the exit status so a report can never disagree with the exit code. This
    # replaces the ad-hoc allowlist that never inspected reconcile's all_passed
    # nor teardown's run_secret_shredded — a reconciliation scoring 0.0 (or ZERO
    # passes) and a failed secret-shred both used to exit 0.
    verdict = qualification_verdict(args.cmd, out if isinstance(out, dict) else {})
    print(
        json.dumps(
            {
                "command": args.cmd,
                "sha": sha,
                "result": out,
                "qualification_verdict": verdict.to_dict(),
            },
            indent=2,
            default=str,
        )
    )

    # EXIT CODE REFLECTS THE VERDICT (findings SEC-C3 + C-5). A report that
    # records NOT-QUALIFIED but exits 0 is prohibited: it can silently green-light
    # a run against a dead candidate or a failed reconciliation/teardown. The exit
    # is driven by the SAME verdict object that was written to the report. Nested
    # shell/dispatcher layers must preserve this nonzero code — never `|| true`.
    if not verdict.ok:
        reason = (
            "; ".join(verdict.reasons)
            or out.get("failure_reason")
            or out.get("reason")
            or "qualification verdict failed"
        )
        print(f"[{args.cmd}] NOT QUALIFIED: {reason}", file=sys.stderr)
        return 3
    return 0


@dataclass(frozen=True)
class QualificationVerdict:
    """The ONE typed verdict that governs both the written report and the exit.

    C-5: reconcile/teardown could report failure yet exit 0. The prior
    ``_result_declares_failure`` allowlist only knew a handful of generic gate
    keys — it never inspected ``reconcile``'s ``all_passed`` nor ``teardown``'s
    ``run_secret_shredded``, so a reconciliation scoring 0.0 (or ZERO passes) and
    a teardown that failed to shred the run secret both exited 0. The fix is one
    verdict object, computed by ``qualification_verdict``, that is BOTH embedded
    in the command's JSON report AND consumed for the process exit status — a
    single source of truth so the report can never disagree with the exit code.

    ``mandatory`` records every gate that was evaluated (name → passed). ``ok`` is
    True only when EVERY mandatory gate passed; a single False gate makes the
    whole verdict fail and no other key can override it (``all_passed`` cannot
    convert an independently-failed pass into success; teardown runs after a
    failed run but cannot turn failure into success).
    """

    command: str
    ok: bool
    reasons: tuple[str, ...]
    mandatory: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "ok": self.ok,
            "reasons": list(self.reasons),
            "mandatory": dict(self.mandatory),
        }


def _grade_generic(out: dict[str, Any], mandatory: dict[str, bool], reasons: list[str]) -> None:
    """Generic fail-closed gates shared by every command (the prior allowlist)."""
    for key in ("deploy_ok", "started", "armed", "ok", "ready"):
        if key in out:
            passed = out.get(key) is not False
            mandatory[f"gate:{key}"] = passed
            if not passed:
                reasons.append(f"{key} is False")
    if out.get("refused"):
        mandatory["not_refused"] = False
        reasons.append(f"refused: {out.get('refused')}")
    if out.get("invalid_reason"):
        mandatory["no_invalid_reason"] = False
        reasons.append(f"invalid_reason: {out.get('invalid_reason')}")
    results = out.get("results")
    if isinstance(results, list) and results:
        failed = [r for r in results if isinstance(r, dict) and r.get("ok") is False]
        passed = not failed
        mandatory["all_results_ok"] = passed
        if not passed:
            reasons.append(f"{len(failed)}/{len(results)} pass result(s) did not reach ok")


def qualification_verdict(command: str, out: dict[str, Any]) -> QualificationVerdict:
    """Compute the typed qualification verdict for a command's result dict.

    Command-specific mandatory predicates (C-5 closure bar):

    ``reconcile`` — a reconciliation is a PASS only when it actually scored at
    least one pass AND every scored pass passed. An empty ``passes`` list is a
    FAILURE (nothing was proven); ``all_passed`` must be exactly True; any
    per-pass ``passed is False`` fails independently so ``all_passed`` can never
    override a failed gate. A score-below-threshold pass already sets
    ``passed=False`` in ``reconcile()`` (``score >= 0.90 and not orphan_5xx and
    all_gating_matched``), so below-threshold is caught here too.

    ``teardown`` — the run-scoped dispatch secret MUST be shredded and the serve
    MUST be positively restored. ``run_secret_shredded is False`` or
    ``serve_restored is not True`` is a FAILURE. Teardown still runs on the
    failure path (main() calls it after a failed run), but a failed or unknown
    teardown cannot be reported as success.

    A dry-run result is never graded as a failure (it asserts no side effects).
    """
    mandatory: dict[str, bool] = {}
    reasons: list[str] = []

    if out.get("dry_run") is True:
        return QualificationVerdict(command=command, ok=True, reasons=(), mandatory={})

    _grade_generic(out, mandatory, reasons)

    if command == "reconcile":
        passes = out.get("passes")
        has_passes = isinstance(passes, list) and len(passes) > 0
        mandatory["reconcile:nonempty"] = has_passes
        if not has_passes:
            reasons.append("reconciliation scored ZERO passes — nothing was proven")
        else:
            each_passed = all(bool(p.get("passed")) for p in passes if isinstance(p, dict))
            mandatory["reconcile:every_pass_passed"] = each_passed
            if not each_passed:
                failed_tags = [
                    p.get("run_tag", "?")
                    for p in passes
                    if isinstance(p, dict) and not p.get("passed")
                ]
                reasons.append(
                    "reconciliation has failing pass(es) "
                    f"(score<0.90 / orphan 5xx / unmatched gating): {failed_tags}"
                )
            all_passed = out.get("all_passed")
            mandatory["reconcile:all_passed_flag"] = all_passed is True
            if all_passed is not True:
                reasons.append(f"all_passed is {all_passed!r}, not True")

    if command == "deploy-candidate":
        deploy_ok = out.get("deploy_ok")
        mandatory["deploy-candidate:deploy_ok"] = deploy_ok is True
        if deploy_ok is not True:
            reasons.append(f"deploy_ok is {deploy_ok!r}, not True")
        serve = out.get("serve")
        serve_ok = isinstance(serve, dict) and serve.get("wired") is True
        mandatory["deploy-candidate:serve_wired"] = serve_ok
        if not serve_ok:
            reasons.append(f"candidate HTTPS serve not proven wired: {serve}")
        readiness = out.get("readiness")
        readiness_ok = isinstance(readiness, dict) and readiness.get("ready") is True
        mandatory["deploy-candidate:ready"] = readiness_ok
        if not readiness_ok:
            reasons.append(f"candidate semantic readiness not proven: {readiness}")
        artifact = out.get("frontend_artifact")
        artifact_ok = isinstance(artifact, dict) and artifact.get("ok") is True
        mandatory["deploy-candidate:frontend_artifact"] = artifact_ok
        if not artifact_ok:
            reasons.append(f"candidate frontend artifact not proven exact: {artifact}")

    if command == "teardown":
        collector = out.get("collector")
        collector_ok = isinstance(collector, dict) and collector.get("stopped") is True
        mandatory["teardown:collector_stopped"] = collector_ok
        if not collector_ok:
            detail = collector.get("reason") if isinstance(collector, dict) else "no collector result"
            reasons.append(f"collector tree not proven stopped: {detail}")
        shredded = out.get("run_secret_shredded")
        mandatory["teardown:secret_shredded"] = shredded is not False
        if shredded is False:
            reasons.append("run secret was NOT shredded — a run secret must never persist")
        serve = out.get("serve_restored")
        mandatory["teardown:serve_restored"] = serve is True
        if serve is not True:
            reasons.append(f"tailscale serve restoration not positively proven: {serve!r}")
        # SEC-C1: credential-home residue is a security failure that makes the
        # whole run NOT-QUALIFIED even when execution succeeded (closure bar §5).
        # A teardown that ran the sweep MUST report homes_swept.ok — a missing key
        # (older teardown result) is treated as failure so residue can never hide.
        homes = out.get("homes_swept")
        homes_ok = isinstance(homes, dict) and homes.get("ok") is True
        mandatory["teardown:homes_swept"] = homes_ok
        if not homes_ok:
            detail = homes.get("errors") if isinstance(homes, dict) else "no homes_swept result"
            reasons.append(f"credential homes not proven clean: {detail}")
        # ZERO-RESIDUE REF GATE. Deliberately SEPARATE from `homes_swept.ok`:
        # a host that cannot delete a protected ref still completes operational
        # teardown (ok stays True) and QUARANTINES the survivor with a durable
        # record. That preserves evidence and accounts for the leftover — but it
        # is NOT clean. Field qualification requires the refs to be actually
        # GONE, so "we wrote down that we leaked it" can never read as "we did
        # not leak it".
        #
        # A missing key is treated as FAILURE (same rule as homes_swept): an
        # older teardown result must not let ref residue hide behind absence.
        ref_residue = homes.get("ref_residue") if isinstance(homes, dict) else None
        ref_inventory = homes.get("ref_inventory") if isinstance(homes, dict) else None
        ref_enumerated = (
            isinstance(homes, dict) and homes.get("ref_enumeration_executed") is True
        )
        ref_count = homes.get("unexpected_ref_count") if isinstance(homes, dict) else None
        zero_refs = (
            isinstance(homes, dict)
            and homes.get("zero_ref_residue") is True
            and ref_enumerated
            and isinstance(ref_inventory, list)
            and isinstance(ref_residue, list)
            and ref_count == 0
        )
        mandatory["teardown:zero_ref_residue"] = zero_refs
        if not zero_refs:
            quarantined = homes.get("quarantined_refs") if isinstance(homes, dict) else None
            reasons.append(
                f"trusted/composed refs still present after teardown: residue={ref_residue} "
                f"quarantined={quarantined} inventory={ref_inventory} "
                f"enumerated={ref_enumerated} unexpected_ref_count={ref_count} — "
                f"quarantine accounts for a leak, it does not make the run clean"
            )

    ok = all(mandatory.values()) if mandatory else True
    return QualificationVerdict(command=command, ok=ok, reasons=tuple(reasons), mandatory=mandatory)


def _result_declares_failure(out: dict[str, Any], command: str = "") -> bool:
    """True when a command result declares a failed verdict.

    Thin back-compat wrapper over :func:`qualification_verdict` (the one typed
    authority). Retained so any external caller keeps working; new logic in
    ``main()`` uses the verdict object directly.
    """
    return not qualification_verdict(command, out).ok


if __name__ == "__main__":
    sys.exit(main())
