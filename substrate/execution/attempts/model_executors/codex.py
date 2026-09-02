"""Codex production adapter for governed model execution."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import signal
import stat
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from substrate.execution.attempts.model_executor_contract import (
    ModelExecutorIdentity,
    ModelExecutorReadiness,
    ModelInvocation,
    ModelTerminalResult,
    ModelWorkPacketInput,
)
from substrate.execution.attempts.model_executor_selection import selected_codex_model
from substrate.execution.cpu_gate import gated_popen, gated_subprocess_run

_ERROR_SIGNATURES = (
    "auth",
    "login",
    "permission denied",
    "rate limit",
    "quota",
    "billing",
    "invalid_request",
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(secret(?:[_-]?key)?\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(credential\s*[:=]\s*)[^\s]+"),
    re.compile(r"op" + r"://[^\s\"')]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)
_CODEX_METADATA_TIMEOUT_SECONDS = 10.0
_CODEX_READINESS_TIMEOUT_SECONDS = 20.0
_CODEX_TREE_TERMINATE_SECONDS = 3.0
_CODEX_GRACEFUL_DRAIN_SECONDS = 3.0
_CODEX_TREE_KILL_SECONDS = 3.0
_CODEX_FORCE_DRAIN_SECONDS = 3.0
_CODEX_PHASE_CALLBACK_SECONDS = 0.05
_CODEX_EXECUTABLE_POLICY_ENV = "UMH_CODEX_APPROVED_EXECUTABLES_JSON"
_CODEX_EXECUTABLE_POLICY_VERSION = "codex-executable-object-sha256-v2"
_CODEX_GOVERNED_LAUNCH_PATH = "/tmp/umh-codex-approved"
_CODEX_CLEANUP_MARGIN_SECONDS = (
    _CODEX_TREE_TERMINATE_SECONDS
    + _CODEX_GRACEFUL_DRAIN_SECONDS
    + _CODEX_TREE_KILL_SECONDS
    + _CODEX_FORCE_DRAIN_SECONDS
)


def _sealed_executable_memfd(source_fd: int) -> int:
    """Materialize approved bytes into an immutable attempt-private object."""

    if not hasattr(os, "memfd_create"):
        raise OSError("sealed executable objects require Linux memfd_create")
    import fcntl

    flags = getattr(os, "MFD_CLOEXEC", 0x0001) | getattr(os, "MFD_ALLOW_SEALING", 0x0002)
    target_fd = os.memfd_create("umh-codex-approved", flags=flags)
    try:
        os.lseek(source_fd, 0, os.SEEK_SET)
        while chunk := os.read(source_fd, 1024 * 1024):
            view = memoryview(chunk)
            while view:
                written = os.write(target_fd, view)
                if written <= 0:
                    raise OSError("failed to materialize approved Codex executable")
                view = view[written:]
        os.lseek(target_fd, 0, os.SEEK_SET)
        required_seals = (
            fcntl.F_SEAL_SEAL
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_WRITE
        )
        fcntl.fcntl(target_fd, fcntl.F_ADD_SEALS, required_seals)
        if fcntl.fcntl(target_fd, fcntl.F_GET_SEALS) & required_seals != required_seals:
            raise OSError("approved Codex executable memfd seals were not applied")
        return target_fd
    except Exception:
        os.close(target_fd)
        raise


def _resolve_codex() -> str:
    resolved = shutil.which("codex") or ""
    realpath = os.path.realpath(resolved) if resolved else ""
    if not realpath or not realpath.endswith("/bin/codex.js"):
        return realpath
    package_root = Path(realpath).parent.parent
    platform_targets = {
        ("linux", "x86_64"): (
            "codex-linux-x64",
            "x86_64-unknown-linux-musl",
        ),
        ("linux", "aarch64"): (
            "codex-linux-arm64",
            "aarch64-unknown-linux-musl",
        ),
    }
    machine = os.uname().machine if hasattr(os, "uname") else ""
    selected = platform_targets.get((os.sys.platform, machine))
    if selected is None:
        return realpath
    package_name, target = selected
    native = (
        package_root
        / "node_modules"
        / "@openai"
        / package_name
        / "vendor"
        / target
        / "bin"
        / "codex"
    )
    return os.path.realpath(native) if native.is_file() else realpath


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fd_sha256(fd: int) -> str:
    digest = hashlib.sha256()
    offset = os.lseek(fd, 0, os.SEEK_CUR)
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        while chunk := os.read(fd, 1024 * 1024):
            digest.update(chunk)
    finally:
        os.lseek(fd, offset, os.SEEK_SET)
    return digest.hexdigest()


def _approved_codex_executables() -> dict[str, str]:
    raw = os.environ.get(_CODEX_EXECUTABLE_POLICY_ENV, "")
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    approved: dict[str, str] = {}
    for path, digest in parsed.items():
        realpath = os.path.realpath(str(path))
        normalized_digest = str(digest).strip().lower()
        if (
            os.path.isabs(str(path))
            and realpath == str(path)
            and re.fullmatch(r"[0-9a-f]{64}", normalized_digest)
        ):
            approved[realpath] = normalized_digest
    return dict(sorted(approved.items()))


def _codex_executable_attestation(path: str, *, version: str) -> dict[str, object]:
    realpath = os.path.realpath(path) if path else ""
    try:
        executable_hash = _file_sha256(realpath) if realpath else ""
    except OSError:
        executable_hash = ""
    approved_executables = _approved_codex_executables()
    policy_identity = _json_digest(
        {
            "policy": _CODEX_EXECUTABLE_POLICY_VERSION,
            "approved_executables": approved_executables,
        }
    )
    return {
        "codex_executable_path": realpath,
        "codex_executable_sha256": executable_hash,
        "codex_executable_version": version,
        "codex_executable_policy": _CODEX_EXECUTABLE_POLICY_VERSION,
        "codex_executable_policy_identity": policy_identity,
        "codex_executable_approved": bool(
            executable_hash and approved_executables.get(realpath) == executable_hash
        ),
    }


def validate_codex_executable_attestation(evidence: dict[str, object]) -> str:
    """Validate the exact opened object against the governed policy snapshot."""

    path = str(evidence.get("codex_executable_path", "") or "")
    digest = str(evidence.get("codex_executable_sha256", "") or "").lower()
    executed_digest = str(evidence.get("codex_executed_object_sha256", "") or "").lower()
    approved = _approved_codex_executables()
    policy_identity = _json_digest(
        {
            "policy": _CODEX_EXECUTABLE_POLICY_VERSION,
            "approved_executables": approved,
        }
    )
    if os.path.realpath(path) != path or approved.get(path) != digest:
        return "Codex executable is not approved by realpath/hash policy"
    if evidence.get("codex_executable_policy") != _CODEX_EXECUTABLE_POLICY_VERSION:
        return "codex_executable_policy does not match the active Codex executable policy"
    if evidence.get("codex_executable_policy_identity") != policy_identity:
        return "codex_executable_policy_identity does not match the active policy"
    if evidence.get("codex_executable_approved") is not True:
        return "codex_executable_approved is not true"
    if executed_digest != digest:
        return "executed Codex object digest does not match approved executable digest"
    if evidence.get("codex_executable_binding") != "bwrap_ro_bind_data_sealed_memfd":
        return "Codex executable is not bound from a sealed read-only object"
    if evidence.get("codex_governed_launch_path") != _CODEX_GOVERNED_LAUNCH_PATH:
        return "Codex governed launch path is invalid"
    if not str(evidence.get("codex_executable_object_identity", "") or ""):
        return "Codex executable object identity is missing"
    if evidence.get("post_execution_executable_binding_verified") is not True:
        return "post-execution Codex object binding is not verified"
    if evidence.get("post_execution_executable_sha256") != digest:
        return "post-execution Codex object digest does not match approved digest"
    return ""


def _sanitize(text: str) -> str:
    redacted = []
    for line in (text or "").splitlines():
        lowered = line.lower()
        if any(
            marker in lowered
            for marker in (
                "authorization",
                "api_key",
                "apikey",
                "password",
                "secret",
                "credential",
                "op://",
            )
        ):
            redacted.append("[redacted credential-bearing line]")
        else:
            clean = line
            for pattern in _SECRET_PATTERNS:
                clean = pattern.sub(
                    lambda m: (m.group(1) if m.groups() else "") + "[redacted]", clean
                )
            redacted.append(clean)
    return "\n".join(redacted)


def _object_field(event: dict, key: str, line_no: int, errors: list[str]) -> dict:
    raw = event.get(key, {})
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        errors.append(f"line {line_no}: {key} is not an object")
        return {}
    return raw


def _classify_failure(*, timed_out: bool, returncode: int | None, stderr: str, stdout: str) -> str:
    if timed_out:
        return "external_transient"
    joined = f"{stderr}\n{stdout}".lower()
    if any(sig in joined for sig in _ERROR_SIGNATURES):
        return "owner_auth_or_provider"
    if returncode in (130, -2, -15):
        return "cancelled"
    if returncode not in (None, 0):
        return "adapter_or_worker"
    return "malformed_output"


def _argv_digest(argv: list[str]) -> str:
    payload = json.dumps(argv, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _explicit_model_argument(argv: list[str], expected_model: str) -> bool:
    for i, arg in enumerate(argv):
        if arg in ("-m", "--model") and i + 1 < len(argv) and argv[i + 1] == expected_model:
            return True
        if arg.startswith("--model=") and arg.split("=", 1)[1] == expected_model:
            return True
    return False


def _decode_timeout_stream(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _append_stream(base: str, extra: object) -> str:
    text = _decode_timeout_stream(extra)
    if not text:
        return base
    if not base:
        return text
    return "\n".join((base, text))


def _append_timeout_stream(base: str, extra: object) -> str:
    text = _decode_timeout_stream(extra)
    if not text:
        return base
    if not base:
        return text
    if text in base:
        return base
    return "\n".join((base, text))


def _taskkill_tree(pid: int, *, force: bool) -> subprocess.CompletedProcess[str]:
    cmd = ["taskkill", "/PID", str(pid), "/T"]
    if force:
        cmd.append("/F")
    result = gated_subprocess_run(
        cmd,
        caller="codex_executor_timeout_cleanup",
        capture_output=True,
        text=True,
        timeout=_CODEX_TREE_KILL_SECONDS if force else _CODEX_TREE_TERMINATE_SECONDS,
    )
    return result or subprocess.CompletedProcess(
        cmd,
        127,
        "",
        "cleanup command blocked by CPU gate or unavailable",
    )


def _posix_signal_tree(pid: int, *, force: bool) -> subprocess.CompletedProcess[str]:
    signum = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        return subprocess.CompletedProcess(
            ["killpg", str(pid)],
            0,
            "",
            "process group already absent",
        )
    except Exception as exc:  # noqa: BLE001
        return subprocess.CompletedProcess(
            ["killpg", str(pid)],
            1,
            "",
            f"process group signal failed: {type(exc).__name__}: {exc}",
        )
    return subprocess.CompletedProcess(
        ["killpg", str(pid)],
        0,
        f"sent {'SIGKILL' if force else 'SIGTERM'} to process group {pid}",
        "",
    )


def _owned_process_tree_pids(root_pid: int) -> list[int]:
    if root_pid <= 0:
        return []
    if os.name == "nt":
        script = (
            "$root="
            + str(root_pid)
            + ";"
            + "$procs=Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId;"
            + "$ids=New-Object 'System.Collections.Generic.HashSet[int]';"
            + "[void]$ids.Add([int]$root);"
            + "do{$changed=$false;foreach($p in $procs){"
            + "if($ids.Contains([int]$p.ParentProcessId) -and -not $ids.Contains([int]$p.ProcessId)){"
            + "[void]$ids.Add([int]$p.ProcessId);$changed=$true}}}while($changed);"
            + "$ids | Sort-Object"
        )
        result = gated_subprocess_run(
            ["powershell", "-NoProfile", "-Command", script],
            caller="codex_executor_tree_snapshot",
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result and result.returncode == 0:
            pids: list[int] = []
            for line in (result.stdout or "").splitlines():
                try:
                    pids.append(int(line.strip()))
                except ValueError:
                    continue
            return sorted(set(pids)) or [root_pid]
        return [root_pid]
    result = gated_subprocess_run(
        ["ps", "-o", "pid=", "-g", str(root_pid)],
        caller="codex_executor_tree_snapshot",
        capture_output=True,
        text=True,
        timeout=2,
    )
    if result and result.returncode == 0:
        pids = []
        for line in (result.stdout or "").splitlines():
            try:
                pids.append(int(line.strip()))
            except ValueError:
                continue
        return sorted(set(pids)) or [root_pid]
    return [root_pid]


def _alive_owned_pids(pids: list[int]) -> list[int]:
    alive: list[int] = []
    for pid in sorted(set(pids)):
        if pid <= 0:
            continue
        if os.name == "nt":
            result = gated_subprocess_run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                caller="codex_executor_tree_verify",
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result and result.returncode == 0 and str(pid) in (result.stdout or ""):
                alive.append(pid)
            continue
        try:
            os.kill(pid, 0)
            alive.append(pid)
        except ProcessLookupError:
            continue
        except PermissionError:
            alive.append(pid)
    return alive


def _force_exact_owned_pids(pids: list[int]) -> list[str]:
    lines: list[str] = []
    for pid in sorted(set(pids), reverse=True):
        if pid <= 0:
            continue
        if os.name == "nt":
            result = gated_subprocess_run(
                ["taskkill", "/PID", str(pid), "/F"],
                caller="codex_executor_exact_pid_cleanup",
                capture_output=True,
                text=True,
                timeout=_CODEX_TREE_KILL_SECONDS,
            )
            if result is None:
                lines.append(f"exact pid force cleanup blocked: {pid}")
            else:
                lines.append(
                    f"exact pid force cleanup pid={pid} rc={result.returncode}: "
                    f"{(result.stdout or result.stderr or '').strip()}"
                )
            continue
        try:
            os.kill(pid, signal.SIGKILL)
            lines.append(f"sent SIGKILL to owned pid {pid}")
        except ProcessLookupError:
            lines.append(f"owned pid already absent {pid}")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"exact pid force cleanup failed pid={pid}: {type(exc).__name__}: {exc}")
    return lines


def _extend_unique(lines: list[str], extra: str) -> None:
    seen = set(lines)
    for line in extra.splitlines():
        clean = line.strip()
        if clean and clean not in seen:
            lines.append(clean)
            seen.add(clean)


class _CodexTimeoutOwner:
    """Owns the single timeout decision for one Codex subprocess tree."""

    def __init__(self, proc: subprocess.Popen[str], *, deadline_at: float, timeout: float) -> None:
        self.proc = proc
        self.deadline_at = deadline_at
        self.timeout = timeout
        self._done = threading.Event()
        self._lock = threading.Lock()
        self._cleanup_lines: list[str] = []
        self._tree_pids: list[int] = [getattr(proc, "pid", 0)]
        self._timeout_enforced = False
        self._watchdog = threading.Thread(
            target=self._watch,
            name=f"codex-timeout-owner-{getattr(proc, 'pid', 'unknown')}",
            daemon=True,
        )
        self._watchdog.start()

    def remaining(self) -> float:
        return max(0.0, self.deadline_at - time.monotonic())

    @property
    def timeout_enforced(self) -> bool:
        return self._timeout_enforced

    def cleanup_text(self) -> str:
        with self._lock:
            return "\n".join(line.strip() for line in self._cleanup_lines if line.strip())

    def finish(self) -> None:
        self._done.set()

    def _watch(self) -> None:
        while not self._done.is_set():
            remaining = self.remaining()
            if remaining <= 0.0:
                self.enforce_timeout(source="watchdog")
                return
            self._done.wait(min(remaining, 0.05))

    def enforce_timeout(self, *, source: str) -> str:
        with self._lock:
            if self._timeout_enforced:
                return "\n".join(line.strip() for line in self._cleanup_lines if line.strip())
            self._timeout_enforced = True
            elapsed = max(0.0, self.timeout - self.remaining())
            self._cleanup_lines.append(
                "codex executor deadline expired "
                f"after {elapsed:.3f}s; timeout={self.timeout:.3f}s; owner={source}"
            )
            try:
                graceful = (
                    _taskkill_tree(self.proc.pid, force=False)
                    if os.name == "nt"
                    else _posix_signal_tree(self.proc.pid, force=False)
                )
                self._cleanup_lines.append(
                    f"graceful tree termination rc={graceful.returncode}: "
                    f"{(graceful.stdout or graceful.stderr or '').strip()}"
                )
            except Exception as cleanup_exc:  # noqa: BLE001
                self._cleanup_lines.append(f"graceful tree termination failed: {cleanup_exc}")
            self._tree_pids = _owned_process_tree_pids(self.proc.pid)
            self._cleanup_lines.append(
                "owned process tree pids=" + ",".join(str(pid) for pid in self._tree_pids)
            )
            return "\n".join(line.strip() for line in self._cleanup_lines if line.strip())

    def force_timeout(self, *, exact_pids: list[int] | None = None) -> str:
        with self._lock:
            try:
                forced = (
                    _taskkill_tree(self.proc.pid, force=True)
                    if os.name == "nt"
                    else _posix_signal_tree(self.proc.pid, force=True)
                )
                self._cleanup_lines.append(
                    f"forced tree termination rc={forced.returncode}: "
                    f"{(forced.stdout or forced.stderr or '').strip()}"
                )
            except Exception as cleanup_exc:  # noqa: BLE001
                self._cleanup_lines.append(f"forced tree termination failed: {cleanup_exc}")
            if exact_pids:
                self._cleanup_lines.extend(_force_exact_owned_pids(exact_pids))
            alive = _alive_owned_pids(self._tree_pids)
            if alive:
                self._cleanup_lines.append(
                    "owned process residue after force tree cleanup="
                    + ",".join(str(pid) for pid in alive)
                )
                self._cleanup_lines.extend(_force_exact_owned_pids(alive))
            return "\n".join(line.strip() for line in self._cleanup_lines if line.strip())

    def alive_owned_pids(self) -> list[int]:
        with self._lock:
            return _alive_owned_pids(self._tree_pids)


def _run_codex_process_tree(
    cmd: list[str],
    *,
    caller: str,
    timeout: float,
    phase_callback: Callable[[str, dict[str, object]], None] | None = None,
    **kwargs: object,
) -> subprocess.CompletedProcess[str] | None:
    """Run Codex with an owned timeout.

    On Windows, a direct subprocess timeout can hit the ``codex.cmd`` wrapper
    while a descendant still owns inherited stdio handles.
    The caller then waits past its own deadline until an outer transport kills
    the whole tree. Wave 2 needs the model-executor timeout to win first, so the
    Windows path owns the process tree explicitly.
    """

    timeout_value = float(timeout)
    if not math.isfinite(timeout_value) or timeout_value <= 0.0:
        raise ValueError("codex executor timeout must be finite and greater than zero")

    popen_kwargs = dict(kwargs)
    input_text = popen_kwargs.pop("input", None)
    if input_text is not None:
        popen_kwargs.setdefault("stdin", subprocess.PIPE)
    if popen_kwargs.pop("capture_output", False):
        popen_kwargs.setdefault("stdout", subprocess.PIPE)
        popen_kwargs.setdefault("stderr", subprocess.PIPE)
    popen_kwargs.setdefault("text", True)
    if os.name == "nt":
        creationflags = int(popen_kwargs.pop("creationflags", 0) or 0)
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        popen_kwargs["creationflags"] = creationflags
    else:
        popen_kwargs.setdefault("start_new_session", True)

    def _phase(phase: str, **extra: object) -> None:
        if phase_callback is None:
            return
        done = threading.Event()

        def _invoke() -> None:
            try:
                phase_callback(phase, extra)
            except Exception:
                pass
            finally:
                done.set()

        thread = threading.Thread(target=_invoke, name=f"codex-phase-{phase}", daemon=True)
        thread.start()
        done.wait(_CODEX_PHASE_CALLBACK_SECONDS)

    started_at = time.monotonic()
    deadline_at = started_at + timeout_value
    _phase(
        "codex_process_spawn_started",
        caller=caller,
        timeout_seconds=timeout_value,
        deadline_monotonic=deadline_at,
        argv_digest=_argv_digest(cmd),
    )
    proc = gated_popen(cmd, caller=caller, **popen_kwargs)
    if proc is None:
        return None
    timeout_owner = _CodexTimeoutOwner(proc, deadline_at=deadline_at, timeout=timeout_value)
    _phase(
        "codex_process_spawned",
        caller=caller,
        pid=getattr(proc, "pid", None),
        timeout_seconds=timeout_value,
        deadline_monotonic=deadline_at,
    )
    _phase(
        "inner_deadline_armed",
        caller=caller,
        timeout_seconds=timeout_value,
        deadline_monotonic=deadline_at,
    )
    try:
        remaining = timeout_owner.remaining()
        if remaining <= 0.0:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout_value, output="", stderr="")
        stdout, stderr = proc.communicate(input=input_text, timeout=remaining)
        if timeout_owner.timeout_enforced:
            stderr = _append_stream(stderr, timeout_owner.cleanup_text())
            raise subprocess.TimeoutExpired(
                cmd=cmd,
                timeout=timeout_value,
                output=stdout,
                stderr=stderr,
            )
        timeout_owner.finish()
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired as exc:
        _phase(
            "inner_timeout_fired",
            caller=caller,
            pid=getattr(proc, "pid", None),
            timeout_seconds=timeout_value,
            elapsed_seconds=time.monotonic() - started_at,
        )
        stdout = _decode_timeout_stream(getattr(exc, "output", ""))
        stderr = _decode_timeout_stream(getattr(exc, "stderr", ""))
        cleanup_lines: list[str] = []

        def _bounded_drain(label: str, drain_timeout: float) -> bool:
            nonlocal stdout, stderr
            _phase(
                "stream_drain_started",
                caller=caller,
                pid=getattr(proc, "pid", None),
                label=label,
                drain_timeout_seconds=drain_timeout,
            )
            try:
                more_out, more_err = proc.communicate(timeout=drain_timeout)
                stdout = _append_timeout_stream(stdout, more_out)
                stderr = _append_stream(stderr, more_err)
                cleanup_lines.append(f"{label} drain completed within {drain_timeout:.3f}s")
                _phase(
                    "stream_drain_completed",
                    caller=caller,
                    pid=getattr(proc, "pid", None),
                    label=label,
                    timed_out=False,
                )
                return True
            except subprocess.TimeoutExpired as drain_exc:
                stdout = _append_timeout_stream(stdout, getattr(drain_exc, "output", ""))
                stderr = _append_stream(stderr, getattr(drain_exc, "stderr", ""))
                cleanup_lines.append(f"{label} drain timed out after {drain_timeout:.3f}s")
                _phase(
                    "stream_drain_completed",
                    caller=caller,
                    pid=getattr(proc, "pid", None),
                    label=label,
                    timed_out=True,
                )
                return False

        _phase(
            "process_tree_termination_started",
            caller=caller,
            pid=getattr(proc, "pid", None),
            graceful=True,
        )
        cleanup = timeout_owner.enforce_timeout(source="communicate")
        _extend_unique(cleanup_lines, cleanup)
        _phase(
            "process_tree_termination_completed",
            caller=caller,
            pid=getattr(proc, "pid", None),
            graceful=True,
        )

        graceful_drain_completed = _bounded_drain("post-graceful", _CODEX_GRACEFUL_DRAIN_SECONDS)
        alive_after_graceful = timeout_owner.alive_owned_pids()
        if alive_after_graceful:
            cleanup_lines.append(
                "owned process residue after graceful cleanup="
                + ",".join(str(pid) for pid in alive_after_graceful)
            )
        if not graceful_drain_completed or alive_after_graceful:
            _phase(
                "process_tree_termination_started",
                caller=caller,
                pid=getattr(proc, "pid", None),
                graceful=False,
            )
            cleanup = timeout_owner.force_timeout(exact_pids=alive_after_graceful)
            _extend_unique(cleanup_lines, cleanup)
            _phase(
                "process_tree_termination_completed",
                caller=caller,
                pid=getattr(proc, "pid", None),
                graceful=False,
            )
            _bounded_drain("post-force", _CODEX_FORCE_DRAIN_SECONDS)
        if getattr(proc, "poll", lambda: None)() is None:
            cleanup_lines.append("codex process still alive after forced termination")
        cleanup = "\n".join(line.strip() for line in cleanup_lines if line.strip())
        if cleanup:
            stderr = "\n".join(x for x in [stderr, cleanup] if x)
        timeout_owner.finish()
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout, output=stdout, stderr=stderr)


def _run_codex_metadata_command(
    cmd: list[str],
    *,
    caller: str,
    timeout: float,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str] | None:
    """Run Codex metadata commands under the same owned timeout discipline."""

    return _run_codex_process_tree(
        cmd,
        caller=caller,
        timeout=timeout,
        capture_output=True,
        text=True,
        env=env,
    )


def _parse_jsonl(stdout: str) -> tuple[str, dict[str, int], str, list[str], dict[str, object]]:
    parts: list[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    model = ""
    errors: list[str] = []
    terminal_events = 0
    failed_events = 0
    error_events = 0
    terminal_status = "missing"
    usage_present = False
    event_types: list[str] = []
    for n, line in enumerate((stdout or "").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line {n}: malformed json")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {n}: json event is not an object")
            continue
        typ = str(event.get("type", ""))
        event_types.append(typ)
        if typ == "item.completed":
            item = _object_field(event, "item", n, errors)
            text = item.get("text", "")
            if text and not isinstance(text, str):
                errors.append(f"line {n}: item.text is not a string")
                continue
            if text:
                parts.append(_sanitize(text))
        elif typ == "turn.completed":
            terminal_events += 1
            terminal_status = "completed"
            raw = _object_field(event, "usage", n, errors)
            usage_present = "usage" in event and isinstance(raw, dict)
            try:
                usage["input_tokens"] = int(raw.get("input_tokens", 0) or 0)
                usage["output_tokens"] = int(raw.get("output_tokens", 0) or 0)
            except (TypeError, ValueError):
                errors.append(f"line {n}: usage token counts are not integers")
            model = str(event.get("model") or model)
        elif typ == "turn.failed":
            failed_events += 1
            terminal_status = "failed"
            errors.append(f"line {n}: turn.failed event")
        elif typ == "error":
            error_events += 1
            terminal_status = "error"
            errors.append(f"line {n}: error event")
        elif typ == "agent_message":
            msg = _object_field(event, "message", n, errors)
            text = msg.get("content", "")
            if text and not isinstance(text, str):
                errors.append(f"line {n}: message.content is not a string")
                continue
            if text:
                parts.append(_sanitize(text))
    if terminal_events == 0:
        errors.append("missing terminal turn.completed event")
    elif terminal_events > 1:
        errors.append("multiple terminal turn.completed events")
    meta = {
        "event_types": event_types,
        "terminal_status": terminal_status,
        "usage_present": usage_present,
        "terminal_completed_count": terminal_events,
        "turn_failed_count": failed_events,
        "error_event_count": error_events,
        "trusted_model_resolved": model,
        "trusted_model_resolution_source": "turn.completed.model" if model else "",
        "model_resolution_observable": bool(model),
    }
    return "\n".join(parts).strip(), usage, model, errors, meta


class CodexModelExecutor:
    def __init__(self, *, model: str | None = None, sandbox: str = "danger-full-access") -> None:
        # UMH's outer bwrap sandbox is the authoritative write/credential/process
        # boundary. Codex's nested workspace-write sandbox makes .git read-only,
        # which prevents legitimate attempt commits (`.git/index.lock`).
        self.model = model or selected_codex_model()
        self.sandbox = sandbox
        self._executable_path = _resolve_codex()
        prelaunch_attestation = _codex_executable_attestation(
            self._executable_path,
            version="",
        )
        self._prelaunch_trust_error = ""
        if self.model == "gpt-5.6-sol" and not prelaunch_attestation[
            "codex_executable_approved"
        ]:
            self._prelaunch_trust_error = (
                "Codex executable is not approved by realpath/hash policy before launch"
            )
        version = self._version() if not self._prelaunch_trust_error else ""
        self.identity = ModelExecutorIdentity(
            provider="codex",
            model=self.model,
            version=version,
            adapter=type(self).__name__,
        )
        self.executable_attestation = _codex_executable_attestation(
            self._executable_path,
            version=self.identity.version,
        )

    def _version(self) -> str:
        cli = self._executable_path
        if not cli:
            return ""
        try:
            r = _run_codex_metadata_command(
                [cli, "--version"],
                caller="codex_executor_version",
                timeout=_CODEX_METADATA_TIMEOUT_SECONDS,
            )
        except Exception:
            return ""
        return (r.stdout or r.stderr or "").strip() if r else ""

    def readiness(self, *, env: dict[str, str] | None = None) -> ModelExecutorReadiness:
        cli = self._executable_path
        if not cli:
            return ModelExecutorReadiness(False, self.identity, "codex CLI not found", False)
        trust_error = self._active_executable_trust_error()
        if trust_error:
            return ModelExecutorReadiness(False, self.identity, trust_error, False)
        try:
            status = _run_codex_metadata_command(
                [cli, "login", "status"],
                caller="codex_executor_readiness",
                timeout=_CODEX_READINESS_TIMEOUT_SECONDS,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            stderr = _sanitize(_decode_timeout_stream(getattr(exc, "stderr", "")) or str(exc))
            return ModelExecutorReadiness(
                False,
                self.identity,
                f"codex status timed out after {_CODEX_READINESS_TIMEOUT_SECONDS:.0f}s: {stderr[-240:]}",
                False,
            )
        except Exception as exc:  # noqa: BLE001
            return ModelExecutorReadiness(
                False, self.identity, f"codex status failed: {exc}", False
            )
        if status is None:
            return ModelExecutorReadiness(False, self.identity, "blocked by CPU gate", False)
        out = f"{status.stdout or ''}\n{status.stderr or ''}".lower()
        ok = status.returncode == 0 and ("not logged" not in out and "login" not in out)
        return ModelExecutorReadiness(
            ok=ok,
            authenticated=ok,
            identity=self.identity,
            reason="" if ok else _sanitize(out)[-300:],
        )

    def build_invocation(self, packet: ModelWorkPacketInput) -> ModelInvocation:
        cli = self._executable_path
        if not cli or self._active_executable_trust_error():
            return ModelInvocation(argv=[])
        try:
            source_fd = os.open(cli, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
            source_stat = os.fstat(source_fd)
            if not stat.S_ISREG(source_stat.st_mode) or not (source_stat.st_mode & 0o111):
                raise OSError("approved Codex object is not an executable regular file")
            source_digest = _fd_sha256(source_fd)
            if source_digest != self.executable_attestation.get("codex_executable_sha256"):
                raise OSError("approved Codex source object changed before materialization")
            fd = _sealed_executable_memfd(source_fd)
            opened = os.fstat(fd)
            opened_digest = _fd_sha256(fd)
        except OSError:
            if "fd" in locals():
                os.close(fd)
            if "source_fd" in locals():
                os.close(source_fd)
            return ModelInvocation(argv=[])
        os.close(source_fd)
        if opened_digest != self.executable_attestation.get("codex_executable_sha256"):
            os.close(fd)
            return ModelInvocation(argv=[])
        object_identity = _json_digest(
            {
                "device": opened.st_dev,
                "inode": opened.st_ino,
                "size": opened.st_size,
                "mtime_ns": opened.st_mtime_ns,
                "sha256": opened_digest,
            }
        )
        attestation = {
            **self.executable_attestation,
            "codex_executed_object_sha256": opened_digest,
            "codex_executable_object_identity": object_identity,
            "codex_executable_binding": "bwrap_ro_bind_data_sealed_memfd",
            "codex_governed_launch_path": _CODEX_GOVERNED_LAUNCH_PATH,
            "prelaunch_attestation_attempt_id": packet.attempt_id,
            "prelaunch_attestation_package_hash": packet.package_hash,
        }
        attestation["prelaunch_attestation_identity"] = _json_digest(
            attestation
        )
        return ModelInvocation(
            argv=[
                _CODEX_GOVERNED_LAUNCH_PATH,
                "exec",
                "--json",
                "--ephemeral",
                "--ignore-user-config",
                "--skip-git-repo-check",
                "--sandbox",
                self.sandbox,
                "--cd",
                packet.worktree_path,
                "-m",
                self.model,
                "-",
            ],
            stdin=packet.prompt,
            cwd=packet.worktree_path,
            inherited_fds=(fd,),
            readonly_fd_mounts=((fd, _CODEX_GOVERNED_LAUNCH_PATH),),
            execution_identity=attestation,
        )

    def finalize_invocation_attestation(
        self,
        invocation: ModelInvocation,
        packet: ModelWorkPacketInput,
    ) -> dict[str, object]:
        if not invocation.inherited_fds:
            return {"post_execution_executable_binding_verified": False}
        fd = invocation.inherited_fds[0]
        try:
            post_digest = _fd_sha256(fd)
        except OSError:
            return {"post_execution_executable_binding_verified": False}
        expected = str(
            invocation.execution_identity.get("codex_executed_object_sha256", "") or ""
        )
        return {
            "post_execution_executable_sha256": post_digest,
            "post_execution_executable_binding_verified": bool(
                post_digest == expected
                and invocation.execution_identity.get("prelaunch_attestation_attempt_id")
                == packet.attempt_id
            ),
        }

    def collect_result(
        self, packet: ModelWorkPacketInput, completed: object | None, *, duration_seconds: float
    ) -> ModelTerminalResult:
        if completed is None:
            return ModelTerminalResult(
                ok=False,
                status="failed",
                retry_class="host_backpressure",
                identity=self.identity,
                proof_binding=packet.proof_binding,
                duration_seconds=duration_seconds,
            )
        proc = completed
        argv = self._invocation_argv(packet)
        parsed, usage, model_seen, parse_errors, parse_meta = _parse_jsonl(
            getattr(proc, "stdout", "") or ""
        )
        explicit_model_argument_present = _explicit_model_argument(argv, self.model)
        if not explicit_model_argument_present:
            parse_errors.append("missing exact explicit Codex model argument")
        if not model_seen:
            parse_errors.append("missing trusted terminal model identity")
        elif model_seen != self.model:
            parse_errors.append(
                f"trusted terminal model identity mismatch: expected {self.model!r}, got {model_seen!r}"
            )
        stdout = parsed or _sanitize(getattr(proc, "stdout", "") or "")
        stderr = _sanitize(getattr(proc, "stderr", "") or "")
        if parse_errors:
            stderr = "\n".join([stderr, *parse_errors]).strip()
        returncode = getattr(proc, "returncode", None)
        usage_present = bool(parse_meta.get("usage_present"))
        if not usage_present:
            parse_errors.append("missing terminal usage metadata")
            stderr = "\n".join([stderr, "missing terminal usage metadata"]).strip()
        invocation_accepted = (
            returncode == 0
            and parse_meta.get("terminal_status") == "completed"
            and not parse_meta.get("turn_failed_count")
            and not parse_meta.get("error_event_count")
        )
        executable_attestation = dict(self.executable_attestation)
        if self.model == "gpt-5.6-sol" and not executable_attestation[
            "codex_executable_approved"
        ]:
            parse_errors.append(
                "Codex executable is not approved by realpath/hash policy"
            )
            stderr = "\n".join(
                [stderr, "Codex executable is not approved by realpath/hash policy"]
            ).strip()
        execution_identity = {
            "provider_requested": "codex",
            "provider_adapter": type(self).__name__,
            "model_requested": self.model,
            "model_selector_source": "explicit_argument",
            "executable_path": argv[0] if argv else "",
            "executable_version": self.identity.version,
            "invocation_argv_digest": _argv_digest(argv) if argv else "",
            "explicit_model_argument_present": explicit_model_argument_present,
            "user_config_ignored": "--ignore-user-config" in argv,
            "invocation_accepted": invocation_accepted,
            "terminal_status": str(parse_meta.get("terminal_status") or ""),
            "trusted_model_resolved": str(parse_meta.get("trusted_model_resolved") or ""),
            "trusted_model_resolution_source": str(
                parse_meta.get("trusted_model_resolution_source") or ""
            ),
            "model_resolution_observable": bool(parse_meta.get("model_resolution_observable")),
            "output_content_present": bool(parsed.strip()),
            "usage_present": usage_present,
            "credential_isolation_verified": False,
            "workspace_integrity_verified": False,
            "event_types": list(parse_meta.get("event_types") or []),
            "attempt_id": packet.attempt_id,
            "package_hash": packet.package_hash,
            "operation_identity_digest": _json_digest(packet.operation_identity),
            "proof_binding_digest": _json_digest(packet.proof_binding),
            **executable_attestation,
        }
        terminal = ModelTerminalResult(
            ok=returncode == 0 and bool(parsed.strip()) and not parse_errors,
            status="succeeded"
            if returncode == 0 and bool(parsed.strip()) and not parse_errors
            else "failed",
            stdout=stdout,
            stderr=stderr,
            summary=stdout[-500:],
            exit_code=returncode,
            duration_seconds=duration_seconds,
            retry_class="not_retryable",
            usage=usage,
            cost={"amount_usd": None, "status": "unavailable"},
            identity=ModelExecutorIdentity(
                provider="codex",
                model=self.model,
                version=self.identity.version,
                adapter=type(self).__name__,
            ),
            execution_identity=execution_identity,
            proof_binding=packet.proof_binding,
        )
        if not terminal.ok:
            terminal.retry_class = _classify_failure(
                timed_out=False, returncode=returncode, stderr=stderr, stdout=stdout
            )
        return terminal

    def invoke(self, packet: ModelWorkPacketInput, *, env: dict[str, str]) -> ModelTerminalResult:
        invocation = self.build_invocation(packet)
        if not invocation.argv:
            reason = self._active_executable_trust_error() or "codex CLI not found"
            return ModelTerminalResult(
                ok=False,
                status="failed",
                summary=reason,
                stderr=reason,
                retry_class="owner_auth_or_provider",
                identity=self.identity,
                execution_identity=dict(self.executable_attestation),
                proof_binding=packet.proof_binding,
            )
        try:
            start = time.monotonic()
            timed_out = False
            stdout = ""
            stderr = ""
            try:
                direct_argv = list(invocation.argv)
                if invocation.inherited_fds:
                    direct_argv[0] = f"/proc/self/fd/{invocation.inherited_fds[0]}"
                proc = _run_codex_process_tree(
                    direct_argv,
                    caller="wave2_model_executor_codex",
                    timeout=packet.timeout_seconds,
                    cwd=invocation.cwd,
                    env=env,
                    input=invocation.stdin,
                    capture_output=True,
                    text=True,
                    pass_fds=invocation.inherited_fds,
                )
            except subprocess.TimeoutExpired as exc:
                proc = None
                timed_out = True
                stdout = _sanitize(_decode_timeout_stream(getattr(exc, "output", "")))
                stderr = _sanitize(
                    _decode_timeout_stream(getattr(exc, "stderr", "")) or str(exc)
                )
            duration = time.monotonic() - start
            if proc is None:
                return ModelTerminalResult(
                    ok=False,
                    status="failed",
                    stdout=stdout if timed_out else "",
                    stderr=stderr if timed_out else "",
                    timed_out=timed_out,
                    duration_seconds=duration,
                    retry_class=("external_transient" if timed_out else "host_backpressure"),
                    identity=self.identity,
                    proof_binding=packet.proof_binding,
                )
            terminal = self.collect_result(packet, proc, duration_seconds=duration)
            terminal.execution_identity.update(invocation.execution_identity)
            terminal.execution_identity.update(
                self.finalize_invocation_attestation(invocation, packet)
            )
            return terminal
        finally:
            for fd in invocation.inherited_fds:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _active_executable_trust_error(self) -> str:
        if self._prelaunch_trust_error:
            return self._prelaunch_trust_error
        if self.model != "gpt-5.6-sol":
            return ""
        current = _codex_executable_attestation(
            self._executable_path,
            version=self.identity.version,
        )
        if current != self.executable_attestation:
            return "Codex executable identity changed after pre-launch approval"
        return "" if current.get("codex_executable_approved") is True else (
            "Codex executable is not approved by realpath/hash policy"
        )

    def _invocation_argv(self, packet: ModelWorkPacketInput) -> list[str]:
        return [
            _CODEX_GOVERNED_LAUNCH_PATH,
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox,
            "--cd",
            packet.worktree_path,
            "-m",
            self.model,
            "-",
        ] if self._executable_path else []


__all__ = ["CodexModelExecutor"]
