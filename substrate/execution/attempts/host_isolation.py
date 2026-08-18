"""Enforced host isolation for real execution workers (Amendment v1 clause 4).

Before a real worker subprocess runs, it MUST be confined so it cannot read
/opt/OS, candidate runtime state, another run's files, or any SSH/1Password/
GitHub/Fly/Discord credentials. This module builds that confinement using
bubblewrap (``bwrap``) — a userspace sandbox that constructs a fresh mount
namespace exposing ONLY:

- the assigned writable worktree (read-write),
- required read-only runtime files (the CLI binary dir, minimal system libs),
- the selected provider's minimal credential path inside the worker's private HOME.

Everything else is absent from the namespace, so the confinement is by
construction, not by allowlist-checking. Post-hoc diff validation (in the
verifier) is ADDITIONAL — it is not the isolation.

``preflight_isolation()`` verifies a working sandbox primitive exists and that a
probe process genuinely cannot see a forbidden path. Field qualification calls it
first; without a passing preflight, Session 1 is INSUFFICIENT_EVIDENCE.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IsolationProfile:
    """The confinement for one worker invocation.

    ``worker_home`` MUST be an attempt-private home (see
    ``worker_credential_boundary.open_attempt_credential_home``). Binding a home
    shared between attempts would let one worker read another's credential, so
    only the single home is bound — never its parent ``worker-homes/`` directory,
    which would make sibling homes enumerable.
    """

    worktree_path: str  # the worktree root (writable EXCEPT the ro overlay below)
    worker_home: str  # attempt-PRIVATE HOME for this provider's credential/config
    ro_paths: list[str] = field(default_factory=list)  # read-only binds (bins, libs)
    allow_network: bool = True  # the model CLI needs network; egress bound is DECLARED
    primitive: str = "bwrap"
    tmp_path: str = ""  # attempt-private TMPDIR (bound rw when set)
    env_overrides: dict[str, str] = field(default_factory=dict)  # HOME/XDG/provider config dirs
    # ── Hard write-scope enforcement (worktree-relative, from the WorkPacket) ──
    # Every existing tracked path in the worktree that this Task may NOT modify,
    # re-bound READ-ONLY *inside* the writable worktree bind. bwrap applies binds
    # in order, so a later --ro-bind masks the earlier rw bind for that subtree.
    #
    # This is what makes ``writable_path_scope`` an actual CAPABILITY rather
    # than a request. Field run 20260803T191345Z-fail proved instruction text is
    # not enough: both workers received correct, distinct, self-sufficient
    # contracts naming their exact allowed AND forbidden paths, and both still
    # wrote the complete six-file objective. The declared scope existed only as
    # a prompt before the work and a ``diff_scope`` check after it, so nothing
    # stood between the worker and the file.
    #
    # The denial comes from the MOUNT, not from permissions: chmod would still
    # allow rename-over, delete-and-recreate, or parent-directory replacement.
    # An out-of-scope write fails with EROFS/EBUSY *before* the target changes.
    readonly_subpaths: list[str] = field(default_factory=list)
    # Paths re-opened WRITABLE on top of the read-only layer above (finding F-1).
    # The only member today is the attempt's private git ref namespace
    # (`.git/refs/attempt/<attempt_id>/`): `.git/refs` as a whole is read-only,
    # so a worker cannot touch `refs/heads`, a sibling attempt's ref, or
    # `packed-refs` — but it CAN create its own ref plus the `.lock` file git
    # requires beside it, which is what makes `git commit` possible at all.
    #
    # Ordering is load-bearing: these are applied LAST because bwrap resolves
    # binds left-to-right and the final bind on a path wins. Applying them before
    # readonly_subpaths would let `--ro-bind .git/refs` mask the attempt's own
    # namespace and break commits again.
    writable_subpaths: list[str] = field(default_factory=list)
    # True when readonly_subpaths was derived from a real declared scope. A
    # profile built without a scope must never silently run unconstrained.
    scope_enforced: bool = False


class IsolationUnavailable(RuntimeError):
    """Raised when no host-isolation primitive is available (fail closed)."""


def isolation_primitive() -> str | None:
    """Return the available isolation primitive name, or None."""
    for name, binary in (("bwrap", "bwrap"), ("nsjail", "nsjail")):
        if shutil.which(binary):
            return name
    # systemd-run gives cgroup/credential confinement but not a mount namespace
    # by default; treat it as a last-resort primitive.
    if shutil.which("systemd-run"):
        return "systemd-run"
    return None


def _default_ro_paths() -> list[str]:
    """Minimal read-only system paths a CLI worker needs to run."""
    candidates = ["/usr", "/bin", "/lib", "/lib64", "/etc/ssl", "/etc/resolv.conf", "/etc/hosts"]
    return [p for p in candidates if os.path.exists(p)]


def build_bwrap_command(inner_cmd: list[str], profile: IsolationProfile) -> list[str]:
    """Wrap ``inner_cmd`` in a bubblewrap sandbox per ``profile``.

    The namespace exposes ONLY the worktree (rw), the worker HOME (rw, holding
    the selected provider's minimal config), and the declared read-only system paths. /opt/OS, candidate
    state, and all other credential stores are simply not bound, so they do not
    exist inside the sandbox.
    """
    cmd: list[str] = [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
    ]
    if profile.allow_network:
        cmd += ["--share-net"]
    for ro in profile.ro_paths or _default_ro_paths():
        cmd += ["--ro-bind-try", ro, ro]
    # Writable worktree.
    cmd += ["--bind", profile.worktree_path, profile.worktree_path]
    # HARD WRITE-SCOPE ENFORCEMENT. Order matters: bwrap applies binds
    # left-to-right, so these read-only binds must come AFTER the rw worktree
    # bind to mask it. Each entry is an absolute path inside the worktree that
    # this Task's WorkPacket does not authorize it to modify.
    #
    # ``--ro-bind`` (not ``--ro-bind-try``): a listed path that cannot be bound
    # is a FAIL-CLOSED condition — bwrap aborts and the worker never starts,
    # rather than running with a forbidden path silently left writable.
    for ro_sub in profile.readonly_subpaths:
        cmd += ["--ro-bind", ro_sub, ro_sub]
    # RE-OPEN the narrow writable exceptions LAST so they win over the read-only
    # layer above (finding F-1). `--bind` (not `--bind-try`): if the attempt's
    # own ref namespace cannot be bound, bwrap must abort rather than start a
    # worker that will fail every commit for an invisible reason.
    for rw_sub in profile.writable_subpaths:
        cmd += ["--bind", rw_sub, rw_sub]
    # This attempt's PRIVATE home only. Binding the parent `worker-homes/` dir
    # would make every sibling attempt's credential enumerable from inside the
    # sandbox — bind the single home, never its parent (R1 / SEC-C2).
    cmd += ["--bind", profile.worker_home, profile.worker_home]
    # Attempt-private TMPDIR. Without this the worker inherits the sandbox's
    # shared /tmp tmpfs, which is a cross-worker channel for anything written
    # under a predictable name.
    if profile.tmp_path:
        cmd += ["--bind", profile.tmp_path, profile.tmp_path]
    # HOME plus every config/state path the selected CLI honours, so no lookup
    # escapes the attempt boundary (XDG_*, provider config dirs, TMPDIR).
    overrides = dict(profile.env_overrides or {})
    overrides.setdefault("HOME", profile.worker_home)
    for key in sorted(overrides):
        cmd += ["--setenv", key, overrides[key]]
    cmd += ["--chdir", profile.worktree_path]
    cmd += inner_cmd
    return cmd


def build_isolated_command(inner_cmd: list[str], profile: IsolationProfile) -> list[str]:
    """Build the fully isolated command. Raises IsolationUnavailable if no
    primitive exists (fail closed — never run a worker unconfined)."""
    prim = isolation_primitive()
    if prim is None:
        raise IsolationUnavailable(
            "no host-isolation primitive (bwrap/nsjail/systemd-run) available — "
            "refusing to run a worker unconfined (Amendment v1 clause 4)"
        )
    if prim == "bwrap":
        return build_bwrap_command(inner_cmd, profile)
    # NO SILENT DOWNGRADE OF THE WRITE BARRIER (independent review MEDIUM-1).
    #
    # Only the bwrap branch can express per-path binds. The systemd-run and
    # nsjail branches below ignore `readonly_subpaths` and `writable_subpaths`
    # entirely, so on a host without bwrap a profile carrying `scope_enforced=True`
    # would run with the flag set and NOTHING enforced — the worker unconfined
    # with respect to its Task scope while every record says otherwise.
    #
    # A coarser sandbox is an acceptable fallback for CREDENTIAL isolation, which
    # is what these branches were written for. It is not an acceptable fallback
    # for WRITE-SCOPE enforcement: a barrier that silently becomes advisory is
    # worse than one that is absent, because the absence is visible. Fail closed
    # and say exactly which primitive could not honor the binds.
    if profile.scope_enforced or profile.readonly_subpaths or profile.writable_subpaths:
        raise IsolationUnavailable(
            f"host-isolation primitive {prim!r} cannot enforce per-path write scope "
            f"({len(profile.readonly_subpaths)} read-only, "
            f"{len(profile.writable_subpaths)} writable binds required) — only bwrap "
            "can. Refusing to run a worker whose declared scope would be unenforced."
        )
    if prim == "systemd-run":
        # Transient unit with a private tmp + restricted home; a coarser fallback.
        return [
            "systemd-run",
            "--user",
            "--pipe",
            "--wait",
            "--collect",
            "--property=PrivateTmp=yes",
            f"--property=WorkingDirectory={profile.worktree_path}",
            f"--setenv=HOME={profile.worker_home}",
            *inner_cmd,
        ]
    # nsjail
    return [
        "nsjail",
        "--mode",
        "o",
        "--chroot",
        "/",
        "--cwd",
        profile.worktree_path,
        "--bindmount",
        f"{profile.worktree_path}:{profile.worktree_path}",
        "--",
        *inner_cmd,
    ]


@dataclass
class VerifierIsolationProfile:
    """Confinement for one VERIFIER invocation that runs worker-authored code.

    Distinct from ``IsolationProfile`` (the implementation worker) in the ways
    that matter for C-4:

    - ``source_ro_path`` is the integration source, bound READ-ONLY. There is NO
      writable worktree — the verifier must never mutate the source.
    - ``verifier_home`` is a CREDENTIAL-FREE private home (no ~/.claude token).
    - ``allow_network`` defaults False: worker-authored Python/tests run with the
      network unshared. Trusted harness HTTP/browser checks run on a SEPARATE
      path that never executes worker-tree code.
    - ``writable_paths`` are ONLY verifier-private tmpfs/dirs (HOME/XDG/TMP), never
      the source.
    """

    source_ro_path: str  # integration source, mounted READ-ONLY
    verifier_home: str  # credential-FREE private HOME
    tmp_path: str  # verifier-private TMPDIR (rw)
    ro_paths: list[str] = field(default_factory=list)
    allow_network: bool = False
    env_overrides: dict[str, str] = field(default_factory=dict)  # HOME/XDG/TMPDIR


def build_verifier_bwrap_command(
    inner_cmd: list[str], profile: VerifierIsolationProfile
) -> list[str]:
    """Wrap ``inner_cmd`` in a bwrap sandbox for VERIFICATION of worker code.

    The namespace exposes ONLY: the integration source (READ-ONLY), the
    credential-free verifier HOME (rw), the verifier-private TMPDIR (rw), and the
    declared read-only system paths. /opt/OS, /root/.claude, worker homes, the
    dispatch secret file, and candidate state are simply not bound. Network is
    unshared unless explicitly allowed (it never is for worker-authored code).
    """
    cmd: list[str] = [
        "bwrap",
        "--unshare-all",  # implies --unshare-net (no network for worker code)
        "--die-with-parent",
        "--new-session",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
    ]
    if profile.allow_network:
        # Deliberately NOT reached for worker-authored code — kept explicit so the
        # default (network unshared) is visibly the safe one.
        cmd += ["--share-net"]
    for ro in profile.ro_paths or _default_ro_paths():
        cmd += ["--ro-bind-try", ro, ro]
    # The integration source is mounted READ-ONLY — the verifier cannot mutate it.
    cmd += ["--ro-bind", profile.source_ro_path, profile.source_ro_path]
    # Credential-free private HOME (rw) + private TMPDIR (rw). These are the ONLY
    # writable mounts.
    cmd += ["--bind", profile.verifier_home, profile.verifier_home]
    if profile.tmp_path:
        cmd += ["--bind", profile.tmp_path, profile.tmp_path]
    overrides = dict(profile.env_overrides or {})
    overrides.setdefault("HOME", profile.verifier_home)
    for key in sorted(overrides):
        cmd += ["--setenv", key, overrides[key]]
    cmd += ["--chdir", profile.source_ro_path]
    cmd += inner_cmd
    return cmd


def build_isolated_verifier_command(
    inner_cmd: list[str], profile: VerifierIsolationProfile
) -> list[str]:
    """Build the fully isolated VERIFIER command. Raises IsolationUnavailable
    unless bwrap is present — never runs worker-authored code unconfined, and
    never falls back to a coarser primitive (nsjail --chroot / and systemd-run
    provide no mount namespace, so worker code would see /opt/OS + credentials)."""
    prim = isolation_primitive()
    if prim != "bwrap":
        raise IsolationUnavailable(
            f"verifier requires bwrap to run worker-authored code; primitive={prim!r} "
            f"— refusing to verify unconfined (C-4, Amendment v1 clause 4)"
        )
    return build_verifier_bwrap_command(inner_cmd, profile)


def preflight_isolation(forbidden_probe_path: str = "/opt/OS") -> tuple[bool, str]:
    """Prove a sandbox genuinely hides a forbidden path. Returns (ok, detail).

    Runs a trivial probe under the isolation primitive that lists the forbidden
    path; if the sandbox is real, the path is absent inside the namespace."""
    from substrate.execution.cpu_gate import gated_subprocess_run

    prim = isolation_primitive()
    if prim is None:
        return False, "no isolation primitive available"
    if prim != "bwrap":
        # FAIL CLOSED. These were previously accepted as "available but not
        # probe-verified", and both callers honoured that (`if not ok and prim ==
        # "bwrap"`), so a non-bwrap primitive could never fail the gate — while
        # providing NO isolation at all:
        #   * systemd-run creates no mount namespace: /opt/OS, every credential
        #     and every other run's state stay readable.
        #   * nsjail --chroot / is the whole filesystem.
        # Neither propagates CLAUDE_CONFIG_DIR/TMPDIR/XDG_*, so the per-attempt
        # credential boundary silently collapses back to the real ~/.claude —
        # reinstating the shared-home defect. Wave 2 hard-requires bwrap.
        return False, (
            f"{prim} cannot be probe-verified to hide {forbidden_probe_path} and does not "
            f"provide a mount namespace — refusing (Wave 2 requires bwrap)"
        )

    import tempfile

    with tempfile.TemporaryDirectory() as wt, tempfile.TemporaryDirectory() as home:
        profile = IsolationProfile(worktree_path=wt, worker_home=home)
        # Inside the sandbox, /opt/OS is NOT bound → `test -e` returns non-zero.
        inner = [
            "/bin/sh",
            "-c",
            f"if [ -e {forbidden_probe_path} ]; then echo LEAK; else echo OK; fi",
        ]
        cmd = build_bwrap_command(inner, profile)
        result = gated_subprocess_run(cmd, caller="isolation_preflight", timeout=30)
        if result is None:
            return False, "preflight skipped (CPU gate) — cannot confirm isolation"
        out = (result.stdout or "").strip()
        if "OK" in out and "LEAK" not in out:
            return True, f"bwrap confinement verified: {forbidden_probe_path} hidden"
        return False, f"isolation FAILED — probe saw {forbidden_probe_path}: {out!r}"


# Credential env keys a worker must NEVER receive (mirrors the candidate deny
# list). The worktree worker gets a scrubbed env with only these stripped.
FORBIDDEN_ENV_PREFIXES = (
    "UMH_MESH_",
    "DISCORD_",
    "FLY_",
    "GITHUB_",
    "GH_",
    "OP_",
    "ANTHROPIC_API_KEY",
    "CODEX_",
    "AWS_",
    "OPENAI_",
    "GOOGLE_",
    "TAILSCALE_",
    "SSH_",
    "NEON_",
    "DATABASE_URL",
)


def scrub_worker_env(
    base_env: dict[str, str], *, extra_allow: dict[str, str] | None = None
) -> dict[str, str]:
    """Build the minimal env a worker receives: strip every forbidden credential,
    keep only PATH/HOME/LANG/GIT identity + the injected model-credential token."""
    keep_keys = {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "TERM",
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "FIXTURE_VENV",
        "SystemRoot",
        "WINDIR",
        "ComSpec",
        "PATHEXT",
        "OS",
        "COMPUTERNAME",
        "USERDOMAIN",
        "USERNAME",
        "USERDOMAIN_ROAMINGPROFILE",
        "ALLUSERSPROFILE",
        "ProgramData",
        "ProgramFiles",
        "ProgramFiles(x86)",
        "ProgramW6432",
        "CommonProgramFiles",
        "CommonProgramFiles(x86)",
        "CommonProgramW6432",
        "PUBLIC",
        "SystemDrive",
        "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_ARCHITEW6432",
        "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL",
        "PROCESSOR_REVISION",
        "NUMBER_OF_PROCESSORS",
    }
    keep_keys_upper = {k.upper() for k in keep_keys}
    forbidden_upper = tuple(p.upper() for p in FORBIDDEN_ENV_PREFIXES)
    out: dict[str, str] = {}
    for k, v in base_env.items():
        key_upper = k.upper()
        if any(key_upper.startswith(p) or key_upper == p for p in forbidden_upper):
            continue
        if k in keep_keys or key_upper in keep_keys_upper:
            out[k] = v
    # Any allowed model credential is injected explicitly via extra_allow after
    # the denylist scrub. No provider credential prefix is inherited by default.
    if extra_allow:
        out.update(extra_allow)
    return out


def scrub_verifier_env(base_env: dict[str, str]) -> dict[str, str]:
    """The minimal env a VERIFIER subprocess receives — even stricter than the
    worker's. Strips every forbidden credential prefix AND the worker's model
    credential (``CLAUDE_CODE_OAUTH_TOKEN``), dispatch secret, and worker config
    dir. A mechanical pytest/diff verifier receives NO model credential.
    """
    forbidden_exact = {
        "CLAUDE_CODE_OAUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "UMH_W2_DISPATCH_SECRET",
        "CLAUDE_CONFIG_DIR",
    }
    keep_keys = {"PATH", "LANG", "LC_ALL", "TERM", "FIXTURE_VENV"}
    out: dict[str, str] = {}
    for k, v in base_env.items():
        if k in forbidden_exact:
            continue
        if any(k.startswith(p) or k == p for p in FORBIDDEN_ENV_PREFIXES):
            continue
        if k in keep_keys:
            out[k] = v
    # HOME/XDG/TMPDIR are set by the verifier profile's env_overrides, never
    # inherited — so they are deliberately NOT carried over here.
    return out


__all__ = [
    "IsolationProfile",
    "VerifierIsolationProfile",
    "IsolationUnavailable",
    "isolation_primitive",
    "build_isolated_command",
    "build_bwrap_command",
    "build_isolated_verifier_command",
    "build_verifier_bwrap_command",
    "preflight_isolation",
    "scrub_worker_env",
    "scrub_verifier_env",
    "FORBIDDEN_ENV_PREFIXES",
]
