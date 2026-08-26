"""Generate the candidate stack's env file by ALLOWLIST.

The Wave-1 candidate container must run with the SMALLEST env surface that lets
cockpit auth + planning-LLM enhancement work — and nothing else. Mesh secrets,
Discord tokens, Fly tokens, GitHub tokens, and every other credential in the
production `services/.env` are DELIBERATELY OMITTED so a candidate deploy can
never actuate a remote node, post to Discord, deploy, or push.

The allowlist was derived by reading:
  * transports/api/cockpit_auth.py — Clerk JWT server-side validation uses ONLY
    CLERK_JWKS_URL + ALLOWED_CLERK_USER_IDS (JWKS = public keys; no secret key
    needed server-side). Optional dev knobs: UMH_DEV_BYPASS, UMH_DOCKER_BRIDGE_IP
    (both omitted by default — candidate runs credential-first, no bypass).
  * adapters/models/model_router.py — planning LLM enhancement reads
    ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY (config.api_key_env). These
    let the deterministic plan be AI-enhanced; without them the deterministic
    spine still produces a plan (Deterministic-First Principle).

Everything else is omitted. UMH_* candidate vars are injected explicitly by the
dispatcher (UMH_STATE_DIR, UMH_BUILD_COMMIT, PYTHONDONTWRITEBYTECODE), not read
from production env.

Emits an audit JSON listing the INCLUDED KEY NAMES ONLY (never values) so a test
can assert no mesh / Discord / Fly / GitHub key leaked into the candidate stack.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Auth/readiness: exactly what cockpit_auth.py and services.operator_api read to
# validate protected routes and semantic readiness. The operator API key is a
# required runtime secret; it is materialized into candidate.env but never into
# artifacts or audit output.
_AUTH_KEYS = (
    "UMH_OPERATOR_API_KEY",
    "CLERK_JWKS_URL",
    "ALLOWED_CLERK_USER_IDS",
)

_REQUIRED_KEYS = ("UMH_OPERATOR_API_KEY",)

# Planning LLM enhancement: model_router.py api_key_env names in the fallback
# chain. Omitting them is safe (deterministic fallback) but degrades plan
# quality, so they are allowlisted.
_LLM_KEYS = (
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
)

# Instance identity envelope: substrate/contracts/principal_resolution.py
# derives tenant_id/membership_id from UMH_ORG_ID (EOS_ORG_ID legacy fallback)
# + UMH_USER_ID. These are IDENTITY VALUES, not credentials or mutation
# authority — without them every planning-rail work mutation fails closed
# ("missing tenant_id/membership_id", field run 20260722T165422Z). The legacy
# names mirror what the production compose stack actually injects
# (infra/docker/umh.env), so candidate identity behaves exactly like prod.
_IDENTITY_KEYS = (
    "UMH_ORG_ID",
    "UMH_USER_ID",
    "EOS_ORG_ID",
    "EOS_USER_ID",
)

# The full allowlist. A key is included ONLY if it is present (non-empty) in the
# source env — absent keys are silently skipped, never emitted blank.
ALLOWLIST: tuple[str, ...] = _AUTH_KEYS + _LLM_KEYS + _IDENTITY_KEYS

# Patterns that must NEVER appear in the candidate env (defense-in-depth: even
# if the allowlist were widened by mistake, these are hard-denied).
_DENY_SUBSTRINGS = (
    "MESH",
    "DISCORD",
    "FLY",
    "GITHUB",
    "GH_",
    "NOTION",
    "TELEGRAM",
    "APIFY",
    "DATABASE_URL",
    "SSH",
    "PRIVATE",
    "1PASSWORD",
    "OP_",
)


def _parse_env_file(path: Path) -> dict[str, str]:
    """Minimal .env parser — KEY=VALUE lines, ignores comments/blanks."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        # Strip surrounding quotes on the value only.
        val = val.strip().strip('"').strip("'")
        if key:
            env[key] = val
    return env


def _is_denied(key: str) -> bool:
    up = key.upper()
    return any(sub in up for sub in _DENY_SUBSTRINGS)


def _clean_env_value(key: str, value: str) -> str:
    cleaned = str(value).strip()
    if any(ch in cleaned for ch in ("\n", "\r", "\0")):
        raise ValueError(f"candidate env value for {key} contains forbidden control character")
    return cleaned


def _missing_required_keys(source: dict[str, str]) -> list[str]:
    missing: list[str] = []
    for key in _REQUIRED_KEYS:
        if not _clean_env_value(key, source.get(key, "")):
            missing.append(key)
    return missing


def build_candidate_env(
    source_env: Path | dict[str, str] | list[Path | dict[str, str]],
    *,
    extra_umh: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return (candidate_env, audit).

    candidate_env: the allowlisted KEY=VALUE map to write.
    audit: names/provenance only; never values.
    """
    # Multiple sources merge in order, later files winning — the same
    # precedence docker-compose applies to the production service's env_file
    # list (services/.env then infra/docker/umh.env).
    sources = source_env if isinstance(source_env, list) else [source_env]
    src: dict[str, str] = {}
    for one in sources:
        if isinstance(one, dict):
            src.update(one)
        else:
            src.update(_parse_env_file(one))
    included: dict[str, str] = {}
    audit: dict[str, list[str]] = {
        "included": [],
        "skipped_absent": [],
        "denied": [],
        "required_present": [],
        "required_missing": [],
    }

    for key in ALLOWLIST:
        if _is_denied(key):
            # Should never happen (allowlist is curated), but fail-closed.
            audit["denied"].append(key)
            continue
        val = _clean_env_value(key, src.get(key, ""))
        if val:
            included[key] = val
            audit["included"].append(key)
            if key in _REQUIRED_KEYS:
                audit["required_present"].append(key)
        else:
            audit["skipped_absent"].append(key)
            if key in _REQUIRED_KEYS:
                audit["required_missing"].append(key)

    # Explicit candidate-only UMH_* vars — provided by the dispatcher, not env.
    for k, v in (extra_umh or {}).items():
        if _is_denied(k):
            audit["denied"].append(k)
            continue
        included[k] = _clean_env_value(k, v)
        audit["included"].append(k)

    if audit["required_missing"]:
        missing = ", ".join(audit["required_missing"])
        raise ValueError(f"required candidate secret/config missing or empty: {missing}")

    return included, audit


def _parse_docker_container_env(container: str) -> dict[str, str]:
    """Read a live container env as a secret source without printing values."""
    if not container:
        return {}
    result = subprocess.run(
        ["docker", "inspect", container, "--format", "{{json .Config.Env}}"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"docker env source {container!r} is unavailable")
    raw = json.loads(result.stdout or "[]")
    env: dict[str, str] = {}
    if not isinstance(raw, list):
        return env
    for item in raw:
        if not isinstance(item, str) or "=" not in item:
            continue
        key, _, value = item.partition("=")
        if key:
            env[key] = value
    return env


def render_env_file(env: dict[str, str]) -> str:
    """Render KEY=VALUE lines with a provenance header (no values in comments)."""
    header = (
        "# Wave-1 candidate env — generated by infra/candidate/make_candidate_env.py\n"
        "# ALLOWLIST ONLY. Mesh/Discord/Fly/GitHub/DB secrets deliberately omitted.\n"
        "# Do not commit. Do not add keys here by hand — widen the allowlist with a\n"
        "# reason instead.\n"
    )
    lines: list[str] = []
    for k, v in env.items():
        if not k or any(ch in k for ch in ("=", "\n", "\r", "\0")):
            raise ValueError(f"candidate env key {k!r} is not a single env-file binding")
        value = _clean_env_value(k, v)
        lines.append(f"{k}={value}")
    body = "\n".join(lines)
    return header + body + "\n"


def _write_secret_env_file(path: Path, content: str) -> None:
    """Atomically write a candidate env file without exposing secret bytes.

    The file must be private before any secret material is written. A later
    chmod is too late under a permissive umask and a failed chmod must not be
    ignored.
    """
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(tmp, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        mode = os.fstat(fd).st_mode & 0o777
        if mode != 0o600:
            raise RuntimeError(f"candidate env temp file mode is {mode:o}, not 600")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fd = -1
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        final_mode = path.stat().st_mode & 0o777
        if final_mode != 0o600:
            try:
                path.unlink()
            finally:
                raise RuntimeError(f"candidate env file mode is {final_mode:o}, not 600")
    finally:
        if fd != -1:
            os.close(fd)
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Wave-1 candidate env by allowlist")
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Source production env file (repeatable; later files win, "
        "mirroring compose env_file precedence)",
    )
    parser.add_argument(
        "--source-container",
        action="append",
        default=None,
        help="Live Docker container env source (repeatable; values are allowlisted and never printed)",
    )
    parser.add_argument("--out", required=True, help="Output candidate.env path")
    parser.add_argument("--audit-out", default="", help="Optional audit JSON path")
    parser.add_argument("--state-dir", default="/state/umh")
    parser.add_argument("--build-commit", default="")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print audit + would-write path, write nothing"
    )
    args = parser.parse_args(argv)

    extra_umh = {
        "UMH_STATE_DIR": args.state_dir,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if args.build_commit:
        extra_umh["UMH_BUILD_COMMIT"] = args.build_commit

    umh_root = os.environ.get("UMH_ROOT", "/opt/OS")
    sources = [Path(s) for s in (args.source or [os.path.join(umh_root, "services", ".env")])]
    source_maps: list[Path | dict[str, str]] = [*sources]
    container_maps: list[dict[str, str]] = []
    for container in args.source_container or []:
        container_env = _parse_docker_container_env(container)
        container_maps.append(container_env)
        source_maps.append(container_env)
    try:
        if args.source_container:
            runtime_source: dict[str, str] = {}
            for one in container_maps:
                runtime_source.update(one)
            runtime_missing = _missing_required_keys(runtime_source)
            if runtime_missing:
                missing = ", ".join(runtime_missing)
                raise ValueError(
                    "required candidate secret/config missing or empty in authoritative "
                    f"runtime source: {missing}"
                )
        env, audit = build_candidate_env(source_maps, extra_umh=extra_umh)
    except ValueError as exc:
        audit = {
            "included": [],
            "skipped_absent": [],
            "denied": [],
            "required_present": [],
            "required_missing": list(_REQUIRED_KEYS),
            "error": [str(exc)],
        }
        if args.audit_out:
            Path(args.audit_out).write_text(json.dumps(audit, indent=2), encoding="utf-8")
        print(json.dumps({"written": "", "audit": audit}, indent=2))
        return 2

    if args.dry_run:
        print(json.dumps({"would_write": args.out, "audit": audit}, indent=2))
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_secret_env_file(out_path, render_env_file(env))

    if args.audit_out:
        Path(args.audit_out).write_text(json.dumps(audit, indent=2), encoding="utf-8")

    # Names only — never values.
    print(json.dumps({"written": str(out_path), "audit": audit}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
