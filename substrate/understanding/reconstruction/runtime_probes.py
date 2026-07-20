"""Runtime probe acquisition for the reconstruction subsystem.

Runs a SMALL, fixed allowlist of read-only, non-destructive shell probes to
gather conservative runtime evidence (git head, working-tree cleanliness,
running docker services, listening ports, importability of key modules). Every
probe runs through the CPU gate (``gated_subprocess_run``); an unavailable probe
(missing binary, gate returns None under CPU overload, timeout, or nonzero exit)
NEVER fails the collection — it produces an ``available=False`` result and an
explicit ``probe_unavailable`` observation.

Redaction is ABSOLUTE: all captured output passes through ``redact()`` before
storage — env-var secret assignments, bearer tokens, ``op://`` URIs, and long
hex/base64 runs become ``[REDACTED]``; output beyond a probe's byte budget is
truncated with an explicit ``[TRUNCATED]`` marker. We never capture environment
values, credentials, secret files, full process environments, unrestricted
command lines, container inspect dumps, or network payloads.

Facet mapping is conservative: a docker service reporting "Up" → a ``running``
observation for ``service:<name>``; listening ports → a single ``host`` /
``listening_ports`` observation at facet ``running`` (a bound port is NOT
evidence of reachability); a successful import → ``importable`` per module. We
never over-assert a facet.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.understanding.reconstruction.contracts import (
    ObservationRecord,
    SourceRecord,
    ValidTime,
    stable_id,
)
from substrate.understanding.reconstruction.provenance import content_hash

# ── Redaction ───────────────────────────────────────────────────────────────
# Secret-ish env var keys whose VALUE must never be stored.
_SECRET_KEY_RE = re.compile(
    r"\b([A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)[A-Z0-9_]*)"
    r"\s*[=:]\s*(\"[^\"]*\"|'[^']*'|\S+)",
    re.IGNORECASE,
)
# Bearer tokens.
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE)
# 1Password secret-reference URIs.
_OP_URI_RE = re.compile(r"op://[^\s\"']+")
# Long hex / base64-ish runs (>=32 chars) — likely tokens/hashes/keys.
_LONG_SECRET_RE = re.compile(r"[A-Za-z0-9+/=_\-]{32,}")

_REDACTED = "[REDACTED]"


def redact(text: str, *, redact_long_runs: bool = True) -> tuple[str, bool]:
    """Redact secret-ish substrings from captured probe output.

    Returns (redacted_text, redaction_applied). Order matters: structured
    patterns (bearer, op://, env assignments) run before the generic long-run
    sweep so a key name is preserved while only its value is masked.

    ``redact_long_runs`` gates ONLY the generic >=32-char sweep. It is set False
    for a probe whose entire legitimate output is a single opaque-but-nonsecret
    token (a git commit SHA) so that value survives; the structured secret
    patterns (bearer/op:///env) still always run.
    """
    if not text:
        return text, False

    applied = False

    def _sub(pattern: re.Pattern[str], repl: str, s: str) -> str:
        nonlocal applied
        new_s, n = pattern.subn(repl, s)
        if n:
            applied = True
        return new_s

    # Order matters: bearer + op:// run BEFORE the env-assignment sweep so a
    # header like "Authorization: Bearer <tok>" has its token masked rather than
    # being mis-read as an env assignment whose "value" is only the word Bearer.
    # The generic long-run sweep runs LAST so it never eats a structured match.
    out = text
    out = _sub(_BEARER_RE, f"Bearer {_REDACTED}", out)
    out = _sub(_OP_URI_RE, _REDACTED, out)
    out = _sub(_SECRET_KEY_RE, lambda m: f"{m.group(1)}={_REDACTED}", out)
    if redact_long_runs:
        out = _sub(_LONG_SECRET_RE, _REDACTED, out)
    return out, applied


def _bound(text: str, max_output_bytes: int) -> tuple[str, bool]:
    """Truncate text to a byte budget with an explicit marker. Returns
    (bounded_text, truncated)."""
    raw = text.encode("utf-8", errors="replace")
    if len(raw) <= max_output_bytes:
        return text, False
    marker = "\n[TRUNCATED]"
    keep = max(0, max_output_bytes - len(marker.encode("utf-8")))
    clipped = raw[:keep].decode("utf-8", errors="replace")
    return clipped + marker, True


# ── Probe specs ───────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ProbeSpec:
    """A single allowlisted, read-only runtime probe."""

    name: str
    command: tuple[str, ...]
    timeout_seconds: float
    max_output_bytes: int
    description: str
    # False only for probes whose ENTIRE legitimate output is a single opaque
    # but non-secret token (a git SHA). Structured secret redaction still runs;
    # only the generic >=32-char sweep is skipped so the token survives.
    redact_long_runs: bool = True


# The ONLY probes permitted. Each is read-only, non-destructive, and produces
# bounded output. Note: ``ss -tln`` (no -p) is used deliberately so process
# command lines are never captured; ``docker ps --format`` returns names+status
# ONLY (never ``docker inspect``).
PROBES: tuple[ProbeSpec, ...] = (
    ProbeSpec(
        name="git_head",
        command=("git", "rev-parse", "HEAD"),
        timeout_seconds=15.0,
        max_output_bytes=256,
        description="Current repository HEAD commit sha.",
        redact_long_runs=False,  # a bare commit SHA is opaque but not a secret
    ),
    ProbeSpec(
        name="git_status",
        command=("git", "status", "--porcelain"),
        timeout_seconds=15.0,
        max_output_bytes=64 * 1024,
        description="Working-tree cleanliness (porcelain, bounded).",
    ),
    ProbeSpec(
        name="docker_services",
        command=("docker", "ps", "--format", "{{.Names}}\t{{.Status}}"),
        timeout_seconds=20.0,
        max_output_bytes=32 * 1024,
        description="Running docker container names + status only.",
    ),
    ProbeSpec(
        name="listening_ports",
        command=("ss", "-tln"),
        timeout_seconds=15.0,
        max_output_bytes=64 * 1024,
        description="Listening TCP sockets (no process/cmdline capture).",
    ),
    ProbeSpec(
        name="python_import_check",
        command=(
            "python3",
            "-c",
            "import substrate.types, substrate.execution.cpu_gate; print('IMPORT_OK')",
        ),
        timeout_seconds=60.0,
        max_output_bytes=8 * 1024,
        description="Importability of key substrate modules.",
    ),
)


# Default execution seam — the gated wrapper. Injectable for tests so no real
# subprocess ever runs in the test suite.
def _default_runner(spec: ProbeSpec, repo_root: str) -> Optional[Any]:
    """Execute a probe through the CPU gate. Returns a CompletedProcess-like
    object or None (gate blocked / binary missing). Raises nothing but a
    subprocess timeout, which the caller handles."""
    cmd = list(spec.command)
    # git probes run against the repo root explicitly (no cwd reliance).
    if cmd and cmd[0] == "git":
        cmd = ["git", "-C", repo_root, *cmd[1:]]
    return gated_subprocess_run(
        cmd,
        caller="reconstruction.runtime_probes",
        timeout=spec.timeout_seconds,
    )


@dataclass(frozen=True)
class ProbeCollection:
    """Result of a runtime-probe collection pass."""

    sources: tuple[SourceRecord, ...]
    observations: tuple[ObservationRecord, ...]
    probe_results: tuple[dict, ...] = field(default_factory=tuple)


def _parse_docker(text: str) -> list[tuple[str, str]]:
    """Parse ``name\\tstatus`` lines → [(name, status)]. Tolerant of blanks."""
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        name, _, status = line.partition("\t")
        name, status = name.strip(), status.strip()
        if name:
            out.append((name, status))
    return out


def _parse_listening_ports(text: str) -> list[str]:
    """Extract Local Address:Port tokens from ``ss -tln`` output (bounded)."""
    ports: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("state"):
            continue
        cols = line.split()
        # ss -tln columns: State Recv-Q Send-Q Local:Port Peer:Port
        if len(cols) >= 4:
            local = cols[3]
            if ":" in local:
                ports.append(local)
    # De-duplicate deterministically.
    return sorted(set(ports))


def collect_runtime_observations(
    run_id: str,
    activity_id: str,
    repo_root: str = "/opt/OS",
    *,
    now: Optional[str] = None,
    runner: Optional[Callable[[ProbeSpec, str], Optional[Any]]] = None,
    probes: tuple[ProbeSpec, ...] = PROBES,
) -> ProbeCollection:
    """Collect conservative runtime observations via the allowlisted probes.

    FIXED SEAM: ``collect_runtime_observations(run_id, activity_id,
    repo_root="/opt/OS") -> ProbeCollection``. Keyword-only ``runner`` injects an
    execution seam (tests pass a fake so no real subprocess runs); ``now`` fixes
    timestamps for determinism; ``probes`` overrides the allowlist for tests.

    No probe failure ever raises out of this function: an unavailable probe
    yields ``available=False`` and an explicit ``probe_unavailable`` observation.
    """
    import subprocess as _subprocess  # for TimeoutExpired type only (not for spawning)

    run = runner or _default_runner

    sources: list[SourceRecord] = []
    observations: list[ObservationRecord] = []
    probe_results: list[dict] = []

    for spec in probes:
        observed_at = now
        available = False
        exit_status: Optional[int] = None
        error: Optional[str] = None
        redaction_applied = False
        truncated = False
        clean_out = ""

        try:
            proc = run(spec, repo_root)
        except _subprocess.TimeoutExpired:
            proc = None
            error = "timeout"
        except Exception as exc:  # never let a probe crash the collection
            proc = None
            error = f"runner_error:{type(exc).__name__}"

        if proc is None:
            if error is None:
                error = "unavailable:gate_blocked_or_binary_missing"
        else:
            exit_status = getattr(proc, "returncode", None)
            raw_out = getattr(proc, "stdout", "") or ""
            stderr = getattr(proc, "stderr", "") or ""
            if exit_status == 0:
                available = True
            else:
                error = f"nonzero_exit:{exit_status}"
            # Redact THEN bound (redaction must see full text first).
            redacted, redaction_applied = redact(raw_out, redact_long_runs=spec.redact_long_runs)
            clean_out, truncated = _bound(redacted, spec.max_output_bytes)
            # stderr is only inspected for an error note, never stored verbatim.
            if stderr and not available:
                _serr, _ = redact(stderr)
                _serr, _ = _bound(_serr, 512)
                error = (error or "error") + f" | stderr:{_serr.strip()[:200]}"

        probe_results.append(
            {
                "name": spec.name,
                "available": available,
                "exit_status": exit_status,
                "observed_at": observed_at,
                "error": error,
                "redaction_applied": redaction_applied,
                "truncated": truncated,
            }
        )

        # One SourceRecord per AVAILABLE probe (modality runtime_probe). An
        # unavailable probe produces no source (there is no acquired artifact),
        # only an explicit unavailable observation.
        source_id: Optional[str] = None
        if available:
            src = SourceRecord(
                subject_path=f"probe:{spec.name}",
                source_kind="runtime_probe",
                modality="runtime_probe",
                source_content_hash=content_hash(clean_out),
                activity_id=activity_id,
                run_id=run_id,
                probe_name=spec.name,
                acquisition_context="runtime_probe",
                redaction_status="partial" if redaction_applied else "none",
                acquired_at=observed_at,
                recorded_at=observed_at,
                metadata={
                    "description": spec.description,
                    "truncated": truncated,
                    "exit_status": exit_status,
                },
            )
            sources.append(src)
            source_id = src.id

        if not available:
            # Explicit unavailable observation — facet 'running' is NOT asserted.
            # The probe ATTEMPT is itself an acquired fact, so it gets a real
            # derived SourceRecord (keeps referential integrity: every
            # observation's source_id resolves).
            unavail_src = SourceRecord(
                subject_path=f"probe:{spec.name}",
                source_kind="runtime_probe",
                modality="runtime_probe",
                source_content_hash="",
                derivation_key=stable_id(
                    "probeattempt", {"name": spec.name, "run_id": run_id, "error": error}
                ),
                derivation_activity_id=activity_id,
                activity_id=activity_id,
                run_id=run_id,
                probe_name=spec.name,
                acquisition_context="runtime_probe_unavailable",
                redaction_status="none",
                acquired_at=observed_at,
                recorded_at=observed_at,
                metadata={"available": False, "error": error},
            )
            sources.append(unavail_src)
            observations.append(
                ObservationRecord(
                    subject=f"probe:{spec.name}",
                    predicate="probe_unavailable",
                    value={"error": error, "exit_status": exit_status},
                    observation_kind="probe_status",
                    maturity_facet=None,  # a probe failure asserts NOTHING about system maturity
                    source_id=unavail_src.id,
                    run_id=run_id,
                    scope="runtime",
                    valid_time=ValidTime(qualifier="instant"),
                    recorded_at=observed_at,
                    support={"available": False},
                )
            )
            continue

        # ── Available: map each probe to conservative facet observations ──────
        if source_id is None:  # structurally impossible for an available probe
            raise RuntimeError(f"available probe {spec.name} produced no source")
        if spec.name == "docker_services":
            for svc_name, status in _parse_docker(clean_out):
                running = status.lower().startswith("up")
                observations.append(
                    ObservationRecord(
                        subject=f"service:{svc_name}",
                        predicate="container_status",
                        value=status,
                        observation_kind="maturity",
                        maturity_facet="running" if running else "deployed",
                        source_id=source_id,
                        run_id=run_id,
                        scope="docker",
                        valid_time=ValidTime(qualifier="instant"),
                        recorded_at=observed_at,
                        support={"raw_status": status},
                    )
                )
        elif spec.name == "listening_ports":
            ports = _parse_listening_ports(clean_out)
            observations.append(
                ObservationRecord(
                    subject="host",
                    predicate="listening_ports",
                    value=ports,
                    observation_kind="maturity",
                    maturity_facet="running",  # ports bound (host process running) — NOT 'reachable'
                    source_id=source_id,
                    run_id=run_id,
                    scope="host",
                    valid_time=ValidTime(qualifier="instant"),
                    recorded_at=observed_at,
                    support={"count": len(ports)},
                )
            )
        elif spec.name == "python_import_check":
            ok = "IMPORT_OK" in clean_out
            observations.append(
                ObservationRecord(
                    subject="module:substrate.types",
                    predicate="import_check",
                    value=ok,
                    observation_kind="maturity",
                    maturity_facet="importable" if ok else "source_present",
                    source_id=source_id,
                    run_id=run_id,
                    scope="python",
                    valid_time=ValidTime(qualifier="instant"),
                    recorded_at=observed_at,
                    support={"probe": "python_import_check"},
                )
            )
        elif spec.name == "git_head":
            head = clean_out.strip()
            if head:
                observations.append(
                    ObservationRecord(
                        subject="repository",
                        predicate="head_commit",
                        value=head,
                        observation_kind="repository_state",
                        maturity_facet=None,
                        source_id=source_id,
                        run_id=run_id,
                        scope="git",
                        valid_time=ValidTime(qualifier="instant"),
                        recorded_at=observed_at,
                        support={"probe": "git_head"},
                    )
                )
        elif spec.name == "git_status":
            dirty = bool(clean_out.strip())
            observations.append(
                ObservationRecord(
                    subject="repository",
                    predicate="working_tree_dirty",
                    value=dirty,
                    observation_kind="repository_state",
                    maturity_facet=None,
                    source_id=source_id,
                    run_id=run_id,
                    scope="git",
                    valid_time=ValidTime(qualifier="instant"),
                    recorded_at=observed_at,
                    support={"probe": "git_status"},
                )
            )

    return ProbeCollection(
        sources=tuple(sources),
        observations=tuple(observations),
        probe_results=tuple(probe_results),
    )
