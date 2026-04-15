"""
environment.py — Execution environment model for the EOS AI OS sandbox layer.

Defines the boundary between PRODUCTION, SANDBOX, and PLAYGROUND modes so
the rest of the system can be told "run against this environment" without
touching module-level constants.

Principles
----------
1. **One path resolver.** Every component that writes files, logs, or state
   asks the environment for the path, never hardcodes `/opt/OS/data/...`.
2. **Copy-on-write workspace.** A sandbox environment has a workspace that
   starts empty. Reads fall through to the production tree; the first write
   to a file copies it into the workspace, and all subsequent reads and
   writes are against the workspace copy. Production is never mutated.
3. **Path guard.** Every path a sandbox env hands out is rooted under its
   own tree. Passing a production path to a sandbox env raises — the
   sandbox never writes outside its box.
4. **Ephemeral playgrounds.** A playground is a sandbox that lives in a
   temp directory and is cleaned up on exit. Same contract, smaller blast
   radius, no persistent logs.

Usage
-----
    from core.environment import Environment, EnvMode, make_sandbox

    prod = Environment.production()
    sbx  = make_sandbox(name="refactor-trial-1")
    with make_playground() as pg:
        ...  # auto-cleanup

    sbx.resolve("eos_ai/memory.py")    # → /opt/OS/data/sandboxes/.../workspace/eos_ai/memory.py
    sbx.ensure_copied("eos_ai/memory.py")  # copies from production on demand
    sbx.action_log_path                # → .../logs/action_log.jsonl
    sbx.is_production                  # → False

The Environment object is designed to be passed to ActionSystem, WorkflowEngine,
and the sandbox_runner. It encapsulates *all* path decisions.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterator

_REPO_ROOT = Path("/opt/OS")
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ─── Constants ──────────────────────────────────────────────────────────────

PRODUCTION_DATA = _REPO_ROOT / "data"
SANDBOX_ROOT = PRODUCTION_DATA / "sandboxes"
PLAYGROUND_ROOT = PRODUCTION_DATA / "playgrounds"

# Paths that sandbox environments are NEVER allowed to write to, even if
# someone tries to hand-craft a path. This is the last line of defense.
FORBIDDEN_WRITE_PREFIXES: tuple[str, ...] = (
    "/opt/OS/data/action_log.jsonl",
    "/opt/OS/data/workflow_log.jsonl",
    "/opt/OS/data/orchestrator_log.jsonl",
    "/opt/OS/data/harness_log.jsonl",
    "/opt/OS/data/persistent_agents_log.jsonl",
    "/opt/OS/data/optimizer_proposals.jsonl",
    "/opt/OS/data/optimizer_state.json",
    "/opt/OS/data/orchestrator_state.json",
    "/opt/OS/data/workflow_state",
    "/opt/OS/data/agent_state",
    "/opt/OS/data/action_snapshots",
    "/opt/OS/eos_ai",
    "/opt/OS/core",
    "/opt/OS/scripts",
    "/opt/OS/services",
)


# ─── Model ──────────────────────────────────────────────────────────────────


class EnvMode(str, Enum):
    PRODUCTION = "production"
    SANDBOX = "sandbox"
    PLAYGROUND = "playground"


@dataclass
class Environment:
    """Encapsulates all path + policy decisions for an execution context.

    The production environment is a singleton-ish object (call
    `Environment.production()` to get one). Sandbox and playground
    environments are instantiated per run via `make_sandbox()` /
    `make_playground()`.

    Fields:
        mode          — which environment mode (production|sandbox|playground)
        name          — human-readable label ("default", "refactor-trial-1")
        root          — tree root for this env. For PRODUCTION this is
                        /opt/OS; for a sandbox it's data/sandboxes/<name>.
        workspace     — where file edits land. For PRODUCTION this IS the
                        repo; for a sandbox it's root/workspace/ which
                        starts empty and is populated on-demand.
        data_dir      — where logs + state files live
        log_dir       — where append-only logs go
        state_dir     — where JSON state files go
        snapshot_dir  — where action rollback snapshots live
        ephemeral     — true for playgrounds; the whole tree is deleted on
                        __exit__ or cleanup()
        read_through  — if True (sandbox/playground), reads that miss the
                        workspace fall through to the production tree.
    """

    mode: EnvMode
    name: str
    root: Path
    workspace: Path
    data_dir: Path
    log_dir: Path
    state_dir: Path
    snapshot_dir: Path
    ephemeral: bool = False
    read_through: bool = True
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ── Classification helpers ─────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.mode == EnvMode.PRODUCTION

    @property
    def is_sandbox(self) -> bool:
        return self.mode in (EnvMode.SANDBOX, EnvMode.PLAYGROUND)

    @property
    def label(self) -> str:
        return f"{self.mode.value}:{self.name}"

    # ── Standard log/state paths ───────────────────────────────────────────

    @property
    def action_log_path(self) -> Path:
        return self.log_dir / "action_log.jsonl"

    @property
    def workflow_log_path(self) -> Path:
        return self.log_dir / "workflow_log.jsonl"

    @property
    def orchestrator_log_path(self) -> Path:
        return self.log_dir / "orchestrator_log.jsonl"

    @property
    def harness_log_path(self) -> Path:
        return self.log_dir / "harness_log.jsonl"

    @property
    def optimizer_proposals_path(self) -> Path:
        return self.log_dir / "optimizer_proposals.jsonl"

    @property
    def sandbox_manifest_path(self) -> Path:
        return self.state_dir / "sandbox_manifest.json"

    @property
    def workflow_state_dir(self) -> Path:
        return self.state_dir / "workflow_state"

    @property
    def agent_state_dir(self) -> Path:
        return self.state_dir / "agent_state"

    # ── Path resolution ────────────────────────────────────────────────────

    def resolve(self, target: str | Path) -> Path:
        """Translate a repo-relative or absolute path into this env's tree.

        Rules:
          * Production: resolves against the real repo root.
          * Sandbox/playground: always resolves inside `self.workspace`,
            regardless of whether the caller passed a relative path or an
            absolute path under /opt/OS.

        Absolute paths pointing OUTSIDE /opt/OS are rejected in sandbox
        mode — the sandbox must not touch /etc, /tmp, /var, etc.
        """
        p = Path(target)
        if self.is_production:
            if p.is_absolute():
                return p
            return (self.root / p).resolve()

        # Sandbox / playground path mapping
        rel = self._to_rel(p)
        mapped = (self.workspace / rel).resolve()
        # Final safety: must remain under workspace after resolve().
        try:
            mapped.relative_to(self.workspace.resolve())
        except ValueError as exc:
            raise PermissionError(
                f"sandbox path escape: {target!r} → {mapped!r}"
            ) from exc
        return mapped

    def _to_rel(self, p: Path) -> Path:
        """Convert any caller-supplied path into a repo-relative Path.

        * `/opt/OS/foo/bar.py` → `foo/bar.py`
        * `foo/bar.py`          → `foo/bar.py`
        * `/etc/passwd`         → PermissionError (sandbox escape)
        """
        if not p.is_absolute():
            return p
        try:
            return p.relative_to(_REPO_ROOT)
        except ValueError as exc:
            raise PermissionError(
                f"sandbox env {self.label} cannot resolve path outside "
                f"{_REPO_ROOT}: {p}"
            ) from exc

    def ensure_copied(self, target: str | Path) -> Path:
        """Copy-on-write: if a file exists in production but not yet in
        the workspace, copy it over so edits/snapshots have a baseline.

        Returns the mapped workspace path. Safe to call for files that
        don't exist — it simply does nothing in that case.
        """
        if self.is_production:
            return self.resolve(target)

        mapped = self.resolve(target)
        if mapped.exists():
            return mapped

        rel = self._to_rel(Path(target))
        prod_path = _REPO_ROOT / rel
        if prod_path.exists() and prod_path.is_file():
            mapped.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(prod_path, mapped)
        return mapped

    def read_file(self, target: str | Path) -> bytes:
        """Read with read-through: if the file isn't in the workspace,
        fall back to the production tree.

        Production env: just reads the file.
        Sandbox env: prefers workspace, falls back to production.
        Raises FileNotFoundError if neither exists.
        """
        mapped = self.resolve(target)
        if mapped.exists():
            return mapped.read_bytes()
        if self.read_through and not self.is_production:
            rel = self._to_rel(Path(target))
            prod_path = _REPO_ROOT / rel
            if prod_path.exists():
                return prod_path.read_bytes()
        raise FileNotFoundError(str(mapped))

    # ── Guard ──────────────────────────────────────────────────────────────

    def guard_write(self, target: str | Path) -> None:
        """Raise PermissionError if this environment is not allowed to
        write to `target`. Called by ActionSystem before any mutation."""
        if self.is_production:
            return  # production writes freely
        p = Path(target).resolve()
        p_str = str(p)
        # Sandbox writes must land inside our workspace.
        try:
            p.relative_to(self.workspace.resolve())
        except ValueError:
            # Not under workspace → check against forbidden list and raise.
            for forbid in FORBIDDEN_WRITE_PREFIXES:
                if p_str == forbid or p_str.startswith(forbid + "/"):
                    raise PermissionError(
                        f"sandbox {self.label} write blocked: {p_str} is "
                        f"a forbidden production path"
                    )
            raise PermissionError(
                f"sandbox {self.label} write blocked: {p_str} is outside "
                f"workspace {self.workspace}"
            )

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def provision(self) -> None:
        """Create the directory tree. Idempotent."""
        for d in (
            self.root,
            self.workspace,
            self.data_dir,
            self.log_dir,
            self.state_dir,
            self.snapshot_dir,
            self.workflow_state_dir,
            self.agent_state_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
        # Leave a marker so tools can tell "is this a sandbox?" without
        # relying on path conventions.
        marker = self.root / ".sandbox_marker"
        if not self.is_production and not marker.exists():
            marker.write_text(
                f"mode={self.mode.value}\n"
                f"name={self.name}\n"
                f"created_at={self.created_at}\n"
                f"workspace={self.workspace}\n"
            )

    def cleanup(self) -> None:
        """Remove the entire env tree. No-op for production.

        Only call on ephemeral envs or sandboxes you explicitly want gone.
        This is destructive — but it only ever touches the sandbox tree.
        """
        if self.is_production:
            return
        if not self.root.exists():
            return
        # Final safety: only remove trees under the configured sandbox root
        # or playground root. Never rm -rf anything else.
        root_str = str(self.root.resolve())
        allowed = (
            str(SANDBOX_ROOT.resolve()),
            str(PLAYGROUND_ROOT.resolve()),
            tempfile.gettempdir(),
        )
        if not any(root_str.startswith(a) for a in allowed):
            raise PermissionError(
                f"refusing to cleanup() env tree {root_str} — not under "
                f"a known sandbox/playground root"
            )
        shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self) -> "Environment":
        self.provision()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.ephemeral:
            self.cleanup()

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "name": self.name,
            "root": str(self.root),
            "workspace": str(self.workspace),
            "data_dir": str(self.data_dir),
            "log_dir": str(self.log_dir),
            "state_dir": str(self.state_dir),
            "snapshot_dir": str(self.snapshot_dir),
            "ephemeral": self.ephemeral,
            "read_through": self.read_through,
            "created_at": self.created_at,
        }

    # ── Constructors ───────────────────────────────────────────────────────

    @classmethod
    def production(cls) -> "Environment":
        """The real-thing environment. Writes land in /opt/OS."""
        return cls(
            mode=EnvMode.PRODUCTION,
            name="default",
            root=_REPO_ROOT,
            workspace=_REPO_ROOT,
            data_dir=PRODUCTION_DATA,
            log_dir=PRODUCTION_DATA,
            state_dir=PRODUCTION_DATA,
            snapshot_dir=PRODUCTION_DATA / "action_snapshots",
            ephemeral=False,
            read_through=False,
        )


# ─── Factory functions ──────────────────────────────────────────────────────


def _new_sandbox_name(prefix: str) -> str:
    """Timestamped name so concurrent sandboxes don't collide."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"{prefix}-{stamp}-{suffix}"


def make_sandbox(
    *,
    name: str | None = None,
    root: Path | None = None,
    read_through: bool = True,
    ephemeral: bool = False,
    provision: bool = True,
) -> Environment:
    """Create a named sandbox environment under data/sandboxes/<name>/.

    Args:
        name          — human-readable label; auto-generated if None.
        root          — override the tree location (tests use this).
        read_through  — if True, reads fall through to the production tree
                        when the workspace doesn't have the file yet.
        ephemeral     — if True, cleanup() runs on __exit__.
        provision     — if True, create the tree now.
    """
    env_name = name or _new_sandbox_name("sbx")
    base = root or (SANDBOX_ROOT / env_name)
    env = Environment(
        mode=EnvMode.SANDBOX,
        name=env_name,
        root=base,
        workspace=base / "workspace",
        data_dir=base / "data",
        log_dir=base / "logs",
        state_dir=base / "state",
        snapshot_dir=base / "snapshots",
        ephemeral=ephemeral,
        read_through=read_through,
    )
    if provision:
        env.provision()
    return env


def make_playground(
    *,
    name: str | None = None,
    root: Path | None = None,
) -> Environment:
    """Create a lightweight, ephemeral playground environment.

    Playgrounds:
      * live under data/playgrounds/<name>/ (or a tempdir if `root` is set)
      * auto-clean up on `with` exit
      * read-through is always enabled
      * minimal logging — still write logs, but the caller is expected to
        throw them away on exit

    Typical use:
        with make_playground() as pg:
            sys_ = ActionSystem(env=pg)
            ...
    """
    env_name = name or _new_sandbox_name("play")
    base = root or (PLAYGROUND_ROOT / env_name)
    env = Environment(
        mode=EnvMode.PLAYGROUND,
        name=env_name,
        root=base,
        workspace=base / "workspace",
        data_dir=base / "data",
        log_dir=base / "logs",
        state_dir=base / "state",
        snapshot_dir=base / "snapshots",
        ephemeral=True,
        read_through=True,
    )
    env.provision()
    return env


def current_environment() -> Environment:
    """Return the env selected via the EOS_ENV environment variable.

    Values:
      unset | "production" | "prod" → production environment
      "sandbox:<name>"               → named sandbox (created if missing)
      "playground:<name>"            → named playground (created if missing)

    This is the entry point for tools that don't know in advance whether
    they're running against production or a sandbox.
    """
    raw = (os.getenv("EOS_ENV") or "production").strip().lower()
    if raw in ("production", "prod", ""):
        return Environment.production()
    if raw.startswith("sandbox:"):
        return make_sandbox(name=raw.split(":", 1)[1] or None)
    if raw == "sandbox":
        return make_sandbox()
    if raw.startswith("playground:"):
        return make_playground(name=raw.split(":", 1)[1] or None)
    if raw == "playground":
        return make_playground()
    raise ValueError(f"unrecognized EOS_ENV={raw!r}")


@contextlib.contextmanager
def sandbox_scope(
    *,
    name: str | None = None,
    cleanup_on_exit: bool = False,
) -> Iterator[Environment]:
    """Context-manager wrapper around make_sandbox().

    If cleanup_on_exit is True, the sandbox tree is removed on exit —
    useful for one-shot verification runs. Default is to keep the tree
    so the operator can inspect it afterward.
    """
    env = make_sandbox(name=name, ephemeral=cleanup_on_exit)
    try:
        yield env
    finally:
        if cleanup_on_exit:
            env.cleanup()


# ─── Public API ─────────────────────────────────────────────────────────────

__all__ = [
    "EnvMode",
    "Environment",
    "make_sandbox",
    "make_playground",
    "current_environment",
    "sandbox_scope",
    "SANDBOX_ROOT",
    "PLAYGROUND_ROOT",
    "FORBIDDEN_WRITE_PREFIXES",
]
