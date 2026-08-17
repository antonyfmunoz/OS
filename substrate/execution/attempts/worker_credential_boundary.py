"""Per-attempt worker credential boundary (R1 — CRITICAL SEC-C2).

Every ExecutionAttempt gets its OWN private home. The previous derivation —
``dirname(worktree_path)`` — resolved to the SAME directory for every lease in a
run, so two concurrent workers shared one home, the real ``~/.claude`` credential
was copied into it, and nothing ever deleted it. That is prohibited.

This module is the single seam that owns the boundary:

    open_attempt_credential_home(attempt_id, run_root, ...) -> AttemptHome
        <run-root>/worker-homes/<attempt-id>/          0700, unique per attempt
        <run-root>/worker-homes/<attempt-id>/<provider config>/  0700
        ...<credential file>                            0600
        <run-root>/worker-homes/<attempt-id>/tmp/       0700, private TMPDIR

    close_attempt_credential_home(home)  -> destroyed on EVERY terminal path

Two authority domains, never joined
-----------------------------------
The candidate CONTROL PLANE holds its own service credentials. The host WORKER
holds only the selected model executor's credential material. They are separate
authority domains: a worker must never receive the control-plane API key merely
because both take part in the same run. ``scrub_worker_env`` is an allowlist and
credential-bearing prefixes are additionally denied; this module re-asserts the
boundary at the home level and the accompanying tests pin it adversarially.

Cleanup failure is a SECURITY FAILURE, not a warning: if credential material
cannot be destroyed, the caller is told so explicitly and the attempt is failed.
"""

from __future__ import annotations

import errno
import logging
import os
import shutil
import stat
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_HOME_MODE = 0o700
_CRED_MODE = 0o600

# Credential filenames copied from the operator's real ~/.claude into the
# attempt-private home. Deliberately minimal: the CLI needs its credentials file
# (and optionally its config); nothing else may cross the boundary.
_CLAUDE_CREDENTIAL_FILES = (".credentials.json", "config.json")
_CODEX_CREDENTIAL_FILES = ("auth.json", "config.toml")

# Never copied into an attempt home, even if present in the source directory —
# these belong to other authority domains or are unnecessary for a worker.
_NEVER_COPY = frozenset(
    {
        "settings.json",
        "settings.local.json",
        ".env",
        "history.jsonl",
        "projects",
        "todos",
        "statsig",
        "shell-snapshots",
    }
)


class CredentialBoundaryError(RuntimeError):
    """Raised when the per-attempt credential boundary cannot be established or
    destroyed. Always fail closed — never run a worker, and never report a clean
    teardown, when this is raised."""


@dataclass
class AttemptHome:
    """One attempt's private credential home. Bound to exactly one attempt_id."""

    attempt_id: str
    home_path: str
    tmp_path: str
    claude_dir: str
    codex_dir: str = ""
    credential_files: list[str] = field(default_factory=list)
    closed: bool = False

    def env_overrides(self) -> dict[str, str]:
        """Env the worker must receive so every config/state path is private.

        HOME alone is not sufficient: the CLI also honours XDG_CONFIG_HOME and
        CLAUDE_CONFIG_DIR, and a shared TMPDIR is a cross-worker channel.
        """
        return {
            "HOME": self.home_path,
            "XDG_CONFIG_HOME": os.path.join(self.home_path, ".config"),
            "XDG_CACHE_HOME": os.path.join(self.home_path, ".cache"),
            "XDG_DATA_HOME": os.path.join(self.home_path, ".local", "share"),
            "CLAUDE_CONFIG_DIR": self.claude_dir,
            "CODEX_HOME": self.codex_dir or os.path.join(self.home_path, ".codex"),
            "TMPDIR": self.tmp_path,
        }

    def to_dict(self) -> dict[str, Any]:
        """Auditable description — paths and booleans only, never contents."""
        return {
            "attempt_id": self.attempt_id,
            "home_path": self.home_path,
            "tmp_path": self.tmp_path,
            "credential_file_count": len(self.credential_files),
            "codex_dir": self.codex_dir,
            "closed": self.closed,
        }


def worker_homes_root(run_root: str) -> str:
    """The parent of all per-attempt homes for a run."""
    return os.path.join(run_root, "worker-homes")


def attempt_home_path(run_root: str, attempt_id: str) -> str:
    """The unique home path for one attempt.

    Derived from ``attempt_id`` — NEVER from ``dirname(worktree_path)``. A retry
    is a NEW attempt with a new attempt_id, so A2 provably gets a different home
    than A1.
    """
    safe = _safe_component(attempt_id)
    return os.path.join(worker_homes_root(run_root), safe)


def _safe_component(value: str) -> str:
    """Filesystem-safe single path component (no traversal, no separators)."""
    cleaned = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (value or ""))
    cleaned = cleaned.strip("-") or "unknown"
    return cleaned[:120]


def _mkdir_private(path: str) -> None:
    """Create a directory with 0700, tolerating an existing private dir."""
    os.makedirs(path, mode=_HOME_MODE, exist_ok=True)
    # makedirs applies the mode only on creation and is umask-subject — enforce.
    os.chmod(path, _HOME_MODE)


def open_attempt_credential_home(
    *,
    attempt_id: str,
    run_root: str,
    provider: str = "claude",
    source_claude_dir: str | None = None,
    source_codex_dir: str | None = None,
    copy_credentials: bool = True,
) -> AttemptHome:
    """Create this attempt's private home and place the minimum credential in it.

    Fail closed: any failure to create the home at the required mode, or to place
    the credential at 0600, raises :class:`CredentialBoundaryError`.
    """
    if not attempt_id:
        raise CredentialBoundaryError("attempt_id is required to bind a credential home")
    if not run_root:
        raise CredentialBoundaryError("run_root is required to place a credential home")

    home = attempt_home_path(run_root, attempt_id)
    claude_dir = os.path.join(home, ".claude")
    codex_dir = os.path.join(home, ".codex")
    tmp_dir = os.path.join(home, "tmp")

    provider_name = (provider or "").strip().lower()
    if provider_name not in {"claude", "codex", "none"}:
        raise CredentialBoundaryError(f"unsupported credential provider: {provider!r}")

    try:
        _mkdir_private(worker_homes_root(run_root))
        _mkdir_private(home)
        _mkdir_private(claude_dir)
        _mkdir_private(codex_dir)
        _mkdir_private(tmp_dir)
        _mkdir_private(os.path.join(home, ".config"))
        _mkdir_private(os.path.join(home, ".cache"))
    except OSError as exc:
        raise CredentialBoundaryError(f"cannot create private attempt home {home}: {exc}") from exc

    placed: list[str] = []
    if copy_credentials:
        if provider_name == "claude":
            src_dir = source_claude_dir or os.path.expanduser("~/.claude")
            placed.extend(_copy_provider_credentials(src_dir, claude_dir, _CLAUDE_CREDENTIAL_FILES))
        elif provider_name == "codex":
            src_dir = source_codex_dir or os.path.expanduser("~/.codex")
            placed.extend(_copy_provider_credentials(src_dir, codex_dir, _CODEX_CREDENTIAL_FILES))

    _assert_private(home)
    for dst in placed:
        _assert_credential_mode(dst)

    return AttemptHome(
        attempt_id=attempt_id,
        home_path=home,
        tmp_path=tmp_dir,
        claude_dir=claude_dir,
        codex_dir=codex_dir,
        credential_files=placed,
    )


def _copy_provider_credentials(
    src_dir: str, dst_dir: str, filenames: tuple[str, ...]
) -> list[str]:
    placed: list[str] = []
    for fname in filenames:
        if fname in _NEVER_COPY:
            continue
        src = os.path.join(src_dir, fname)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(dst_dir, fname)
        try:
            shutil.copyfile(src, dst)
            os.chmod(dst, _CRED_MODE)
        except OSError as exc:
            _best_effort_unlink(dst)
            raise CredentialBoundaryError(
                f"cannot place credential {fname} at 0600 in {dst_dir}: {exc}"
            ) from exc
        placed.append(dst)
    return placed


def verifier_homes_root(run_root: str) -> str:
    """Parent of all per-attempt VERIFIER homes for a run.

    Distinct directory from ``worker-homes/`` so a verifier home is never confused
    with (or reused from) a worker home.
    """
    return os.path.join(run_root, "verifier-homes")


def verifier_home_path(run_root: str, attempt_id: str) -> str:
    """Unique VERIFIER home path for one attempt (keyed by attempt_id)."""
    safe = _safe_component(attempt_id)
    return os.path.join(verifier_homes_root(run_root), safe)


def open_verifier_home(*, attempt_id: str, run_root: str) -> AttemptHome:
    """Create this attempt's CREDENTIAL-FREE private verifier home.

    Unlike ``open_attempt_credential_home``, NO credential is ever placed here: a
    mechanical pytest/diff verifier receives no model credential. The home is
    distinct from the worker home (``verifier-homes/`` not ``worker-homes/``), so
    there is zero worker-home reuse and zero credential reuse. Fail closed on any
    failure to create a directory at 0700.
    """
    if not attempt_id:
        raise CredentialBoundaryError("attempt_id is required to bind a verifier home")
    if not run_root:
        raise CredentialBoundaryError("run_root is required to place a verifier home")

    home = verifier_home_path(run_root, attempt_id)
    claude_dir = os.path.join(home, ".claude")  # present but EMPTY (no credential)
    codex_dir = os.path.join(home, ".codex")  # present but EMPTY (no credential)
    tmp_dir = os.path.join(home, "tmp")
    try:
        _mkdir_private(verifier_homes_root(run_root))
        _mkdir_private(home)
        _mkdir_private(claude_dir)
        _mkdir_private(codex_dir)
        _mkdir_private(tmp_dir)
        _mkdir_private(os.path.join(home, ".config"))
        _mkdir_private(os.path.join(home, ".cache"))
        _mkdir_private(os.path.join(home, ".local", "share"))
    except OSError as exc:
        raise CredentialBoundaryError(f"cannot create verifier home {home}: {exc}") from exc

    _assert_private(home)
    # credential_files is deliberately empty — nothing to overwrite on close.
    return AttemptHome(
        attempt_id=attempt_id,
        home_path=home,
        tmp_path=tmp_dir,
        claude_dir=claude_dir,
        codex_dir=codex_dir,
        credential_files=[],
    )


def assert_no_verifier_home_residue(run_root: str) -> list[str]:
    """Return any surviving verifier home directories (empty == clean)."""
    root = verifier_homes_root(run_root)
    if not os.path.isdir(root):
        return []
    return [os.path.join(root, name) for name in os.listdir(root)]


def _assert_private(path: str) -> None:
    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & 0o077:
        raise CredentialBoundaryError(
            f"attempt home {path} is group/world accessible (mode {mode:o})"
        )


def _assert_credential_mode(path: str) -> None:
    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & 0o177:
        raise CredentialBoundaryError(f"credential {path} is not 0600 (mode {mode:o})")


def _best_effort_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError as exc:  # pragma: no cover - diagnostics only
        if exc.errno != errno.ENOENT:
            logger.debug("could not unlink %s: %s", path, exc)


def close_attempt_credential_home(home: AttemptHome | None) -> None:
    """Destroy an attempt's private home and every credential inside it.

    Called on EVERY terminal path — success, failure, timeout, cancellation and
    forced teardown. Raises :class:`CredentialBoundaryError` if credential
    material survives: a cleanup failure is a SECURITY failure, never a warning.
    """
    if home is None or home.closed:
        return

    # Overwrite credential bytes before unlinking so a plain file recovery does
    # not yield the token. (Not a cryptographic erase on CoW/journaling
    # filesystems — the durable guarantee is the removal + the short lifetime.)
    for cred in home.credential_files:
        try:
            if os.path.isfile(cred):
                length = os.path.getsize(cred)
                with open(cred, "r+b", buffering=0) as fh:
                    fh.write(b"\0" * length)
                    fh.flush()
                    os.fsync(fh.fileno())
        except OSError as exc:
            logger.debug("credential overwrite failed for %s: %s", cred, exc)

    shutil.rmtree(home.home_path, ignore_errors=True)

    if os.path.exists(home.home_path):
        # Second attempt, then fail loudly — residue is a security failure.
        shutil.rmtree(home.home_path, ignore_errors=True)
        if os.path.exists(home.home_path):
            raise CredentialBoundaryError(
                f"attempt home {home.home_path} still exists after cleanup — "
                f"credential residue may remain (SECURITY FAILURE)"
            )
    home.closed = True


def assert_no_credential_residue(run_root: str) -> list[str]:
    """Return any surviving credential paths under a run root (empty == clean).

    Used by teardown and by the security self-check so 'cleaned up' is a verified
    claim rather than an assumption.
    """
    residue: list[str] = []
    root = worker_homes_root(run_root)
    if not os.path.isdir(root):
        return residue
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name in _CLAUDE_CREDENTIAL_FILES or name in _CODEX_CREDENTIAL_FILES:
                residue.append(os.path.join(dirpath, name))
    return residue


__all__ = [
    "AttemptHome",
    "CredentialBoundaryError",
    "assert_no_credential_residue",
    "assert_no_verifier_home_residue",
    "attempt_home_path",
    "close_attempt_credential_home",
    "open_attempt_credential_home",
    "open_verifier_home",
    "verifier_home_path",
    "verifier_homes_root",
    "worker_homes_root",
]
