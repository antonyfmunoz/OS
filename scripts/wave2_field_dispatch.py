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
  inject-failure   arm a genuine worker failure variant for one pass
  reconcile        score collected evidence against candidate state + logs
  teardown         stop containers, stop runner, shred run secret, restore serve

Every subcommand supports --dry-run: it prints the exact commands it WOULD run
and assembles no side effects. Use it to prove command assembly without touching
the live host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def _serve_snapshot_stable_path() -> Path:
    """Deterministic snapshot location, recoverable across CLI invocations.

    deploy-candidate, smoke, run, and teardown are SEPARATE process
    invocations. The production-serve snapshot deploy-candidate takes must be
    found again by a later teardown (or a crash handler) so production serve is
    restored exactly once, at the end. A per-process global cannot survive a
    process boundary, so the canonical snapshot lives at a fixed path.
    """
    return _proof_root() / "tailscale_serve_snapshot.json"


def _snapshot_tailscale_serve(runner: Runner, run_dir: Path) -> Path:
    """Snapshot current `tailscale serve status --json` to the stable path.

    Only writes a NEW snapshot when one does not already exist for this run —
    so re-running deploy-candidate (which by then sees the CANDIDATE serve, not
    production) never clobbers the original production snapshot.
    """
    global _serve_snapshot_path
    snap = _serve_snapshot_stable_path()
    _serve_snapshot_path = snap
    if runner.dry_run:
        print(f"[dry-run] would snapshot tailscale serve → {snap}")
        return snap
    if snap.exists():
        # Preserve the first (production) snapshot; a redeploy would otherwise
        # capture the candidate mapping and lose the real restore target.
        return snap
    result = runner.run(["tailscale", "serve", "status", "--json"], timeout=30, capture=True)
    content = result.stdout if result and result.returncode == 0 else "{}"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(content, encoding="utf-8")
    return snap


def _load_serve_snapshot_path() -> None:
    """Point the module global at the on-disk snapshot from a prior deploy.

    Called by consuming commands (smoke/run/teardown) so their crash handlers
    and teardown restore have a real production snapshot to restore, even though
    THIS process never took it.
    """
    global _serve_snapshot_path
    if _serve_snapshot_path is None and _serve_snapshot_stable_path().exists():
        _serve_snapshot_path = _serve_snapshot_stable_path()


def _restore_tailscale_serve(runner: Runner) -> None:
    """Restore serve config from the snapshot. Idempotent; safe on every exit."""
    global _serve_restored
    if _serve_restored or _serve_snapshot_path is None:
        return
    _serve_restored = True
    # Reset first, then re-apply the snapshot if it was non-empty.
    runner.run(["tailscale", "serve", "reset"], timeout=30, check=False)
    if runner.dry_run:
        print("[dry-run] would re-apply tailscale serve snapshot if non-empty")
        return
    try:
        snap = json.loads(_serve_snapshot_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        snap = {}
    # A non-empty snapshot means serve was previously configured — re-apply the
    # exact mapping it recorded (best-effort; the common case is the operator's
    # own :443 → 127.0.0.1:8080 mapping).
    web = snap.get("Web") if isinstance(snap, dict) else None
    if web:
        # Re-point 443 to the operator's real nginx (host 8080) — the standing
        # production mapping. This is the documented restore target.
        runner.run(
            ["tailscale", "serve", "--bg", "--https=443", "http://127.0.0.1:8080"],
            timeout=30,
            check=False,
        )


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
        _restore_tailscale_serve(runner)
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

    # (3) candidate operator container — SAME image, worktree mounted read-only,
    # candidate state dir mounted rw, allowlisted env only.
    _remove_container_and_wait(runner, _CANDIDATE_CONTAINER)
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

    # (4) build the candidate frontend in the worktree cockpit dir, injecting
    # the production Clerk publishable key at build time. Runs cwd-scoped, so it
    # bypasses Runner (which has no cwd); dry-run just echoes the shape.
    cockpit = _WORKTREE / "cockpit"
    if runner.dry_run:
        print(f"[dry-run] (cwd={cockpit}) npm ci")
        print(
            f"[dry-run] (cwd={cockpit}) "
            "VITE_CLERK_PUBLISHABLE_KEY=<from fly.toml> npm run build:web"
        )
    else:
        # --legacy-peer-deps: the repo has a known capacitor peer-dep conflict
        # (@capacitor/android@8 vs core@7) that only affects the native mobile
        # target, never the web build. dist-web builds cleanly regardless.
        #
        # Skip `npm ci` when the lockfile is unchanged since the last install:
        # a full ci per redeploy cost ~90s of CPU on a 4-core orchestrator and
        # drove host load to ~1.6/core during repeated qualification cycles
        # (CPU Gate Law). The lock hash stamp makes the skip deterministic.
        lock_hash = _sha256_file(cockpit / "package-lock.json")
        stamp = cockpit / "node_modules" / ".wave2-lock-sha"
        if stamp.exists() and stamp.read_text(encoding="utf-8").strip() == lock_hash:
            print("[deploy] npm ci skipped — lockfile unchanged since last install")
        else:
            subprocess.run(
                ["npm", "ci", "--legacy-peer-deps"], cwd=str(cockpit), timeout=600, check=False
            )
            if (cockpit / "node_modules").is_dir():
                stamp.write_text(lock_hash, encoding="utf-8")
        subprocess.run(
            ["npm", "run", "build:web"],
            cwd=str(cockpit),
            timeout=600,
            check=False,
            env={**os.environ, "VITE_CLERK_PUBLISHABLE_KEY": clerk_key},
        )
    dist_web = cockpit / "dist-web"
    steps["dist_web"] = str(dist_web)

    # (5) render nginx.candidate.conf from the template and start nginx:alpine
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
    _remove_container_and_wait(runner, _CANDIDATE_NGINX_CONTAINER)
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
    _snapshot_tailscale_serve(runner, run_dir)
    _install_crash_handlers(runner)
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

    # (7) health checks — WAIT for the operator to finish its cold start
    # (event registry + goal selector + faster-whisper load take ~15-30s)
    # before probing, so the deploy report reflects the WARM state instead of
    # racing the boot and reporting a false-negative 502/connection-reset.
    readiness = _wait_candidate_ready(runner, timeout_s=180.0)
    steps["readiness"] = readiness
    checks = {
        "candidate_api_health": _http_ok(
            runner, f"http://127.0.0.1:{_CANDIDATE_API_HOST_PORT}/health"
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
    steps["deploy_ok"] = ready and not failed_checks
    if not steps["deploy_ok"]:
        steps["failure_reason"] = (
            f"readiness={'ok' if ready else 'NOT READY'}; failed_checks={failed_checks or 'none'}"
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
    """Block until the candidate answers THROUGH nginx, or the budget expires.

    Probes the same origin path the browser uses, so a ready verdict proves the
    whole chain (nginx -> operator) is warm — not merely that the container
    process exists. An auth-gated 401 is the ready signal (the API is reachable
    and enforcing auth); 502/503 means nginx has no live upstream yet.
    """
    if runner.dry_run:
        print("[dry-run] wait for candidate readiness via origin API")
        return {"planned": "candidate-ready"}
    url = f"{_candidate_origin()}/api/umh/objective-plan"
    deadline = time.time() + timeout_s
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = _http_ok(runner, url, expect_status={401, 200})
        if last.get("ok"):
            # Small settle so in-flight worker warm-up finishes before traffic.
            time.sleep(settle_s)
            return {"ready": True, "waited_s": round(timeout_s - (deadline - time.time()), 1)}
        time.sleep(2.0)
    return {"ready": False, "last": last}


# ─────────────────────────────────────────────────────────────────────────────
# preflight
# ─────────────────────────────────────────────────────────────────────────────
def preflight(runner: Runner) -> dict[str, Any]:
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
    out["schtasks_query"] = _mesh_read(runner, 'schtasks /query /tn "UMH Node Daemon" /v /fo LIST')
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
    start_shape = _build_start_command(
        run_id="RUNID", pass_num=1, scenario="full", url=_ORIGIN, candidate_commit="SHA"
    )
    out["start_command_shape"] = _SECRET_REDACT_RE.sub("<redacted>", start_shape)
    print("start-command shape (echo only):")
    print(f"  {out['start_command_shape']}")

    # PREFLIGHT VERDICT (finding SEC-C3): mesh relay, the executor daemon in an
    # interactive session, and Beast->origin reachability are all REQUIRED. A
    # preflight that records a failure must exit non-zero rather than reporting
    # a green shape. (beast_to_origin legitimately fails before deploy — it is
    # only asserted once an origin is expected to exist.)
    required = ("mesh_health", "schtasks_query", "query_session")
    failed = [k for k in required if isinstance(out.get(k), dict) and out[k].get("ok") is False]
    mesh = out.get("mesh_health") or {}
    if isinstance(mesh, dict) and mesh.get("returncode") not in (0, None):
        failed.append("mesh_health")
    out["ok"] = not failed
    if failed:
        out["failure_reason"] = f"preflight checks failed: {sorted(set(failed))}"
    return out


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


def _mesh_read(runner: Runner, command: str, *, max_len: int = 400) -> dict[str, Any]:
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
            f"[dry-run] mesh_dispatch(shell, signed verdict) node={_MESH_NODE_ID} cmd={command!r}"
        )
        return {"dry_run": True, "command": command}
    sys.path.insert(0, str(_ROOT))
    from substrate.sockets.mesh_dispatch_port import mesh_dispatch

    result = mesh_dispatch(
        node_id=_MESH_NODE_ID,
        capability="shell",
        params={"command": command, "timeout": 60},
        risk_class="reversible_write",  # mints the signed verdict the node validates
        timeout=90,
    )
    rd = result.get("result_data", {}) if isinstance(result, dict) else {}
    return {
        "ok": bool(result.get("ok")),
        "stdout": _SECRET_REDACT_RE.sub("<redacted>", str(rd.get("stdout", ""))[:max_len]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# collector dispatch (smoke / run)
# ─────────────────────────────────────────────────────────────────────────────
def _build_start_command(
    *, run_id: str, pass_num: int, scenario: str, url: str, candidate_commit: str
) -> str:
    """Assemble the detached powershell Start-Process → op run → collector cmd.

    The collector runs under `op run` on the executor so credentials never
    transit the mesh dispatch payload. Start-Process detaches it so the mesh
    call returns immediately; we then poll status.json read-only.
    """
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
    inner = f"/c md {_BEAST_EVIDENCE_DIR} 2>nul & {op_wrapped} 1> {launch_log} 2>&1"
    # Start-Process detaches; -WindowStyle Hidden keeps Session 1 clean.
    return (
        "powershell -NoProfile -Command "
        f"\"Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' "
        f"-ArgumentList '{inner}'\""
    )


def _poll_status(
    runner: Runner,
    run_id: str,
    pass_num: int,
    timeout_min: int = 30,
    max_mesh_failures: int = 5,
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
        if last.get("state") in ("passed", "failed"):
            return last
        time.sleep(30)
    last["timed_out"] = True
    return last


def dispatch_pass(
    runner: Runner, *, run_id: str, pass_num: int, scenario: str, sha: str
) -> dict[str, Any]:
    """Dispatch one collector pass (governed write-class) and poll to terminal."""
    command = _build_start_command(
        run_id=run_id,
        pass_num=pass_num,
        scenario=scenario,
        url=_ORIGIN,
        candidate_commit=sha,
    )
    if runner.dry_run:
        print(f"[dry-run] mesh_dispatch(shell, write-class) node={_MESH_NODE_ID}")
        print(f"[dry-run]   detached start: {_SECRET_REDACT_RE.sub('<redacted>', command)}")
        _poll_status(runner, run_id, pass_num)
        return {"dry_run": True, "run_id": run_id, "pass_num": pass_num}

    sys.path.insert(0, str(_ROOT))
    from substrate.sockets.mesh_dispatch_port import mesh_dispatch

    result = mesh_dispatch(
        node_id=_MESH_NODE_ID,
        capability="shell",
        params={"command": command, "timeout": 60},
        risk_class="reversible_write",
        timeout=90,
    )
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error"), "run_id": run_id, "pass_num": pass_num}
    terminal = _poll_status(runner, run_id, pass_num)
    return {"ok": terminal.get("state") == "passed", "terminal": terminal, "run_id": run_id}


def _verify_beast_collector_commit(runner: Runner, sha: str) -> dict[str, Any]:
    """Exact-commit binding for the collector CODE: the Beast worktree the
    collector runs from must be checked out at the candidate sha. Refuse to
    dispatch otherwise — a stale collector would qualify the wrong journey."""
    if runner.dry_run:
        print(f"[dry-run] would verify {_BEAST_WT} HEAD == {sha}")
        return {"ok": True, "dry_run": True}
    probe = _mesh_read(runner, rf"git -C {_BEAST_WT} rev-parse --short=12 HEAD")
    beast_head = (probe.get("stdout") or "").strip()
    ok = probe.get("ok", False) and beast_head.startswith(sha[:12])
    return {"ok": ok, "beast_worktree_head": beast_head, "candidate_sha": sha}


def run_passes(runner: Runner, *, sha: str, scenario: str, passes: int) -> dict[str, Any]:
    """Run N collector passes with fresh run-ids; restart candidate before pass 1."""
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
        results.append(dispatch_pass(runner, run_id=run_id, pass_num=i, scenario=scenario, sha=sha))
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
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if r.get("candidate_commit") == sha[:12] and r.get("scenario") == "full":
            candidate_passes.append(pass_dir)

    for pass_dir in candidate_passes:
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
        passed = score >= 0.90 and not orphan_5xx and all_gating_matched

        pass_result = {
            "pass_dir": str(pass_dir),
            "run_tag": run_tag,
            "total_api_requests": total_requests,
            "matched_requests": matched_requests,
            "asserted_transitions": asserted,
            "matched_transitions": matched_transitions,
            "transition_detail": transition_detail,
            "orphan_5xx": [n["url"] for n in orphan_5xx],
            "score": round(score, 3),
            "passed": passed,
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
    """Stop containers + runner, shred the run secret, restore serve. State kept.

    The run-scoped dispatch secret is DESTROYED here (Amendment v1 clause 3 /
    order step 4): it existed only for this run's spool and must not persist.
    """
    stopped = {}
    if run_id:
        stopped = stop_runner(runner, sha, run_id)
    _remove_container_and_wait(runner, _CANDIDATE_NGINX_CONTAINER)
    _remove_container_and_wait(runner, _CANDIDATE_CONTAINER)
    secret_shredded = _shred_run_secret(runner, sha) if sha else True
    _restore_tailscale_serve(runner)
    return {
        "torn_down": [_CANDIDATE_CONTAINER, _CANDIDATE_NGINX_CONTAINER],
        "runner": stopped,
        "run_secret_shredded": secret_shredded,
        "serve_restored": True,
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
    sys.path.insert(0, str(_ROOT))
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


def start_runner(runner: Runner, sha: str, run_id: str, max_iterations: int) -> dict[str, Any]:
    """Start the run-scoped host attempt runner over this run's signed spool.

    The runner verifies ENFORCED host isolation (bwrap) is available and refuses
    to run workers unconfined (Amendment v1 clause 4). It reads the run-scoped
    dispatch secret from the 0600 file (never a CLI arg, never logged). It is a
    RUN-SCOPED component — started here, stopped at teardown — NOT a persistent
    supervisor (that is Wave 3).

    On the VPS host the runner's OAuth token is resolved by the approved path
    (cc_sdk `_find_ancestor_oauth`) at worker-invocation time; this launcher just
    verifies isolation + spins the loop.
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
    isolation_ok = False
    if pre is not None and getattr(pre, "stdout", ""):
        try:
            isolation_ok = bool(json.loads(pre.stdout).get("isolation_ok", False))
        except (ValueError, AttributeError):
            isolation_ok = False
    if not isolation_ok and not runner.dry_run:
        return {
            "started": False,
            "isolation_ok": False,
            "reason": "enforced host isolation (bwrap) preflight failed — refusing "
            "to run workers unconfined (Amendment v1 clause 4)",
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
            if "runner up:" in head:
                announced = True
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


def write_scenario_map(runner: Runner, sha: str, run_id: str) -> dict[str, Any]:
    """Resolve + persist the run's scenario map from REAL materialized records.

    This is the field consumer of the scenario-map capability (finding C-3). It
    reads the candidate's live plan + WorkPacket records, resolves each semantic
    role to its exact canonical ``wp-*`` id through plan-node lineage, and writes
    a run+plan-bound ``scenario_map.json`` under the run's targets dir. WITHOUT
    this, ``inject-failure`` reads ``{}`` and the failure-qualification pass is
    unrunnable (exit 3 forever).

    Must run AFTER the plan materializes its WorkPackets (i.e. after the plan
    approval + activation the collector drives) and BEFORE inject-failure.
    """
    targets = _targets_dir(sha, run_id)
    if runner.dry_run:
        print(f"[dry-run] resolve + write scenario map for run {run_id} → {targets}")
        return {"written": True, "dry_run": True, "run_id": run_id}

    # Import the worktree substrate (not the stale /opt/OS one) — the candidate
    # source lives in this worktree, and _WORKTREE is where its modules resolve.
    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.field_scenario_map import (
        ScenarioMapError,
        build_from_records,
    )
    from substrate.execution.attempts.field_scenario_map import (
        write_scenario_map as _persist,
    )

    records = _read_state_records(sha)
    # Resolve the EXACT plan + authorization the run produced from the ONE ACTIVE
    # grant in candidate state — never "latest plan" or a run-tag substring.
    binding = _active_grant_binding(records)
    if binding is None:
        return {
            "written": False,
            "run_id": run_id,
            "error": "no single ACTIVE execution-authorization grant found in candidate state",
            "remediation": "drive the plan approval + execution authorization before writing the map",
        }
    try:
        payload = build_from_records(
            records,
            run_id=run_id,
            plan_record_id=binding["plan_record_id"],
            plan_version=binding["plan_version"],
            execution_authorization_ref=binding["decision_ref"],
        )
    except ScenarioMapError as exc:
        # FAIL CLOSED: no map is written, so inject-failure will refuse to arm.
        return {
            "written": False,
            "run_id": run_id,
            "error": str(exc),
            "remediation": "ensure the plan materialized its WorkPackets before writing the map",
        }
    path = _persist(targets, payload)
    return {
        "written": True,
        "run_id": run_id,
        "path": str(path),
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
    # scenario map validates against THIS run's LIVE plan + packets — correct run
    # binding, not stale, every role resolving to a real materialized packet
    # inside the authorized frontier. An armed injection that cannot target a real
    # authorized task must never be mistaken for a recovered one.
    sys.path.insert(0, str(_WORKTREE))
    from substrate.execution.attempts.field_failure_policy import (
        arming_is_valid_for_run,
        target_task_id,
    )

    records = _read_state_records(sha)
    binding = _active_grant_binding(records)
    if binding is None:
        return {
            "armed": False,
            "variant": variant,
            "marker": str(marker),
            "invalid_reason": "no single ACTIVE execution-authorization grant in candidate state",
            "remediation": "drive the execution-authorization decision, then re-arm",
        }
    ok, reason = arming_is_valid_for_run(
        str(targets),
        run_id=run_id,
        records=records,
        plan_record_id=binding["plan_record_id"],
        plan_version=binding["plan_version"],
        tenant_id=binding["tenant_id"],
    )
    if not ok:
        return {
            "armed": False,
            "variant": variant,
            "marker": str(marker),
            "invalid_reason": reason,
            "remediation": (
                "run `wave2_field_dispatch.py write-scenario-map` AFTER the plan "
                "materializes its WorkPackets, then re-arm"
            ),
        }
    return {
        "armed": True,
        "variant": variant,
        "marker": str(marker),
        "target_task_id": target_task_id(str(targets)),
        "arming": reason,
    }


def _active_grant_binding(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The EXACT plan + authorization binding from the ONE ACTIVE grant.

    The authorized frontier and plan version come from the single ACTIVE
    execution-authorization grant in candidate state — never from "latest plan"
    or an aggregation over all packets. Returns None (fail closed) when there is
    not exactly one ACTIVE grant, so the caller refuses to write/arm.
    """
    grants = [
        g
        for g in records
        if g.get("grant_id")
        and "task_frontier" in g
        and str(g.get("status", "")).lower() == "active"
    ]
    if len(grants) != 1:
        return None
    g = grants[0]
    return {
        "plan_record_id": str(g.get("plan_record_id", "")),
        "plan_version": int(g.get("plan_version", 0)),
        "tenant_id": str(g.get("tenant_id", "")),
        "decision_ref": str(g.get("decision_ref", "")),
    }


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
        return (r.stdout or "").strip()[:12] or "unknown"
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
        "inject-failure",
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
        out = preflight(runner)
    elif args.cmd == "deploy-candidate":
        out = deploy_candidate(runner, sha)
        write_manifest(runner, sha)
    elif args.cmd == "seed-fixture":
        out = seed_fixture(runner, sha, run_id, args.variant)
    elif args.cmd == "start-runner":
        out = start_runner(runner, sha, run_id, args.max_iterations)
    elif args.cmd == "smoke":
        _ensure_mesh_secrets()
        _load_serve_snapshot_path()
        _install_crash_handlers(runner, sha)
        out = run_passes(runner, sha=sha, scenario="smoke", passes=1)
    elif args.cmd == "run":
        _ensure_mesh_secrets()
        _load_serve_snapshot_path()
        _install_crash_handlers(runner, sha)
        out = run_passes(runner, sha=sha, scenario=args.scenario, passes=args.passes)
    elif args.cmd == "write-scenario-map":
        out = write_scenario_map(runner, sha, run_id)
    elif args.cmd == "inject-failure":
        out = inject_failure(runner, sha, run_id, args.variant)
    elif args.cmd == "reconcile":
        out = reconcile(runner, sha)
    elif args.cmd == "teardown":
        _load_serve_snapshot_path()
        out = teardown(runner, sha=sha, run_id=args.run_id)
    else:  # pragma: no cover — argparse enforces
        parser.error(f"unknown command {args.cmd}")
        return 2

    print(json.dumps({"command": args.cmd, "sha": sha, "result": out}, indent=2, default=str))

    # EXIT CODE REFLECTS THE VERDICT (finding SEC-C3). A readiness report that
    # records NOT READY but exits 0 is prohibited: it can silently green-light a
    # run against a dead candidate and burn worker quota. Any command whose
    # result declares failure exits non-zero so a caller (or an automated driver)
    # stops. Zero worker quota is consumed on this path — no dispatch has
    # happened yet at deploy/preflight time.
    if isinstance(out, dict) and _result_declares_failure(out):
        reason = (
            out.get("failure_reason")
            or out.get("reason")
            or out.get("refused")
            or out.get("invalid_reason")
            or "readiness/verdict failed"
        )
        print(f"[{args.cmd}] FAILED: {reason}", file=sys.stderr)
        return 3
    return 0


def _result_declares_failure(out: dict[str, Any]) -> bool:
    """True when a command result declares a failed verdict.

    Explicit-False verdict keys only — a missing key is not a failure, so
    commands that do not report a verdict keep exiting 0.
    """
    for key in ("deploy_ok", "started", "armed", "ok", "ready"):
        if out.get(key) is False:
            return True
    if out.get("refused") or out.get("invalid_reason"):
        return True
    # run_passes: any pass that did not reach a passed terminal state.
    results = out.get("results")
    if isinstance(results, list) and results:
        if any(isinstance(r, dict) and r.get("ok") is False for r in results):
            return True
    return False


if __name__ == "__main__":
    sys.exit(main())
